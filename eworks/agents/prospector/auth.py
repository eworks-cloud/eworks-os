"""LinkedIn authentication and Playwright session management.

Stealth approach:
- Realistic Chrome/120 user agent
- Real viewport (1366×768)
- Disable webdriver flag via JS
- Random human-like delays between actions
- Cookie-based session persistence in session/ directory
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

LINKEDIN_HOME = "https://www.linkedin.com"
LINKEDIN_LOGIN = "https://www.linkedin.com/login"
LINKEDIN_FEED = "https://www.linkedin.com/feed/"


async def random_delay(min_sec: float = 1.5, max_sec: float = 4.0) -> None:
    """Pause for a random duration to simulate human behaviour."""
    delay = random.uniform(min_sec, max_sec)
    logger.debug("Sleeping %.2fs", delay)
    await asyncio.sleep(delay)


class LinkedInAuth:
    """Manages a Playwright browser session authenticated to LinkedIn."""

    def __init__(
        self,
        session_dir: str = "session/",
        headless: bool = True,
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport: dict | None = None,
    ):
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.user_agent = user_agent
        self.viewport = viewport or {"width": 1366, "height": 768}

        self._playwright = None
        self._browser = None
        self._context = None
        self.page = None

    async def _launch(self) -> None:
        """Launch the Playwright browser with stealth settings."""
        try:
            from playwright.async_api import async_playwright  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "playwright is not installed. Run: pip install playwright"
            ) from exc

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        self._context = await self._browser.new_context(
            viewport=self.viewport,
            user_agent=self.user_agent,
            locale="en-US",
            timezone_id="America/Sao_Paulo",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
            },
        )
        # Disable webdriver detection
        await self._context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = {runtime: {}};
            """
        )
        self.page = await self._context.new_page()
        logger.info("Browser launched (headless=%s)", self.headless)

    async def login(self, email: str, password: str) -> bool:
        """Log in to LinkedIn using email/password. Returns True on success."""
        if self._browser is None:
            await self._launch()

        logger.info("Navigating to LinkedIn login page…")
        await self.page.goto(LINKEDIN_LOGIN, wait_until="domcontentloaded")
        await random_delay(2.0, 4.0)

        # Fill email
        await self.page.fill("#username", email)
        await random_delay(0.5, 1.5)

        # Fill password with human-like typing
        await self.page.fill("#password", password)
        await random_delay(0.8, 2.0)

        # Click Sign in
        await self.page.click('[data-litms-control-urn="login-submit"]')
        await random_delay(3.0, 6.0)

        # Check if login succeeded
        logged_in = await self.is_logged_in()
        if logged_in:
            logger.info("LinkedIn login successful for %s", email)
        else:
            logger.warning("LinkedIn login may have failed for %s", email)
        return logged_in

    async def load_session(self, session_file: str) -> bool:
        """Load saved cookies from a JSON file. Returns True if loaded OK."""
        session_path = self.session_dir / session_file
        if not session_path.exists():
            logger.warning("Session file not found: %s", session_path)
            return False

        if self._browser is None:
            await self._launch()

        with session_path.open() as f:
            cookies: list[dict[str, Any]] = json.load(f)

        await self._context.add_cookies(cookies)
        logger.info("Session loaded from %s (%d cookies)", session_path, len(cookies))
        return True

    async def save_session(self, session_file: str) -> None:
        """Persist the current browser cookies to a JSON file."""
        if self._context is None:
            raise RuntimeError("Browser context not initialised — call login() first")

        session_path = self.session_dir / session_file
        cookies = await self._context.cookies()
        with session_path.open("w") as f:
            json.dump(cookies, f, indent=2)
        logger.info("Session saved to %s (%d cookies)", session_path, len(cookies))

    async def is_logged_in(self) -> bool:
        """Check whether the current session is authenticated."""
        if self.page is None:
            return False
        try:
            current_url = self.page.url
            # If we're on feed or a profile page we're logged in
            if "linkedin.com/feed" in current_url or "linkedin.com/in/" in current_url:
                return True

            await self.page.goto(LINKEDIN_FEED, wait_until="domcontentloaded")
            await random_delay(1.5, 3.0)
            url_after = self.page.url
            is_logged = "linkedin.com/feed" in url_after
            logger.debug("is_logged_in=%s (url=%s)", is_logged, url_after)
            return is_logged
        except Exception as exc:
            logger.error("Error checking login status: %s", exc)
            return False

    async def close(self) -> None:
        """Shut down the browser cleanly."""
        try:
            if self.page:
                await self.page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            logger.info("Browser closed")
        except Exception as exc:
            logger.warning("Error during browser shutdown: %s", exc)
        finally:
            self.page = None
            self._context = None
            self._browser = None
            self._playwright = None
