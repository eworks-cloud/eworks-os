"""Prospect discovery (LinkedIn scraper) and ICP scoring.

ProspectDiscovery: scrapes LinkedIn connections and profiles via Playwright.
ICPScorer: assigns a 0–100 score based on configurable signals.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from eworks.agents.prospector.auth import LinkedInAuth, random_delay

logger = logging.getLogger(__name__)

CONNECTIONS_URL = "https://www.linkedin.com/mynetwork/invite-connect/connections/"

# ─── ICP Scoring weights ──────────────────────────────────────────────────────

TITLE_SENIOR = {
    "ceo", "cto", "coo", "cfo", "cpo", "founder", "co-founder",
    "director", "vp", "vice president", "head of", "president",
    "chief",
}
TITLE_MID = {"manager", "lead", "principal", "staff", "senior manager"}

LOCATION_PRIME = {
    "brazil", "brasil", "são paulo", "sao paulo", "rio de janeiro",
    "belo horizonte", "curitiba", "brasilia", "porto alegre",
    "united states", "usa", "us", "california", "new york",
    "canada", "mexico", "argentina", "chile", "colombia",
    "united kingdom", "uk", "germany", "france", "netherlands",
    "europe", "latam", "latin america",
}

INDUSTRY_PRIME = {
    "software", "saas", "fintech", "ai", "artificial intelligence",
    "machine learning", "tech", "technology", "cloud", "platform",
    "data", "cybersecurity", "blockchain", "startup",
}
INDUSTRY_ADJACENT = {
    "consulting", "agency", "digital", "e-commerce", "ecommerce",
    "media", "marketing", "analytics", "automation", "erp", "crm",
}

STARTUP_SIGNALS = {
    "startup", "scale-up", "scaleup", "seed", "series a", "series b",
    "early stage", "growth stage", "venture", "bootstrapped",
}
COMPANY_SIZE_SIGNALS = {
    "small", "boutique", "independent", "freelance",
}


class ICPScorer:
    """Weighted ideal customer profile scorer."""

    def score(
        self,
        prospect_data: dict[str, Any],
        icp_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Score a prospect 0–100 and return score + breakdown."""
        breakdown: dict[str, float] = {}

        # 1. Title match (30 pts)
        breakdown["title_match"] = self._score_title(prospect_data)

        # 2. Company size signal (20 pts)
        breakdown["company_size_signal"] = self._score_company_size(prospect_data)

        # 3. Location match (15 pts)
        breakdown["location_match"] = self._score_location(prospect_data)

        # 4. Industry match (20 pts)
        breakdown["industry_match"] = self._score_industry(prospect_data)

        # 5. Engagement signal (15 pts)
        breakdown["engagement_signal"] = self._score_engagement(prospect_data)

        total = sum(breakdown.values())
        total = min(100.0, max(0.0, total))

        return {"score": round(total, 2), "breakdown": breakdown}

    # ─── Sub-scorers ──────────────────────────────────────────────────────────

    def _normalize(self, text: str) -> str:
        return text.lower().strip() if text else ""

    def _score_title(self, data: dict[str, Any]) -> float:
        headline = self._normalize(data.get("headline", ""))
        for kw in TITLE_SENIOR:
            if kw in headline:
                return 30.0
        for kw in TITLE_MID:
            if kw in headline:
                return 15.0
        return 0.0

    def _score_company_size(self, data: dict[str, Any]) -> float:
        combined = " ".join([
            self._normalize(data.get("headline", "")),
            self._normalize(data.get("about", "")),
            self._normalize(data.get("company", "")),
        ])
        for signal in STARTUP_SIGNALS:
            if signal in combined:
                return 20.0
        for signal in COMPANY_SIZE_SIGNALS:
            if signal in combined:
                return 10.0
        # Default partial — most companies could be a fit
        return 5.0

    def _score_location(self, data: dict[str, Any]) -> float:
        location = self._normalize(data.get("location", ""))
        for loc in LOCATION_PRIME:
            if loc in location:
                return 15.0
        return 5.0

    def _score_industry(self, data: dict[str, Any]) -> float:
        combined = " ".join([
            self._normalize(data.get("headline", "")),
            self._normalize(data.get("about", "")),
            self._normalize(data.get("company", "")),
        ])
        for kw in INDUSTRY_PRIME:
            if kw in combined:
                return 20.0
        for kw in INDUSTRY_ADJACENT:
            if kw in combined:
                return 10.0
        return 0.0

    def _score_engagement(self, data: dict[str, Any]) -> float:
        mutual = data.get("mutual_connections", 0) or 0
        return 15.0 if mutual > 0 else 0.0


class ProspectDiscovery:
    """Scrapes LinkedIn connections and individual profiles."""

    def __init__(self, db=None):
        self.db = db
        self.scorer = ICPScorer()

    async def scrape_connections(
        self,
        auth: LinkedInAuth,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Scrape connections from the LinkedIn connections page."""
        if auth.page is None:
            raise RuntimeError("Browser not started — call auth.login() first")

        page = auth.page
        prospects: list[dict[str, Any]] = []

        logger.info("Navigating to connections page…")
        await page.goto(CONNECTIONS_URL, wait_until="domcontentloaded")
        await random_delay(2.0, 4.0)

        scraped = 0
        while scraped < limit:
            # LinkedIn connections list cards
            cards = await page.query_selector_all(
                "ul.mn-connections__list li.mn-connection-card"
            )
            if not cards:
                # Fallback selector
                cards = await page.query_selector_all(
                    "[data-view-name='member-connections-list'] li"
                )

            for card in cards:
                if scraped >= limit:
                    break
                try:
                    prospect = await self._parse_connection_card(card)
                    if prospect and prospect.get("linkedin_url"):
                        prospects.append(prospect)
                        scraped += 1
                except Exception as exc:
                    logger.debug("Failed to parse card: %s", exc)

            # Scroll and try to load more
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await random_delay(1.5, 3.0)

            # Check for more items
            new_cards = await page.query_selector_all(
                "ul.mn-connections__list li.mn-connection-card"
            )
            if len(new_cards) <= len(cards):
                logger.info("No more connections to load (got %d)", scraped)
                break

        logger.info("Scraped %d connections", len(prospects))
        return prospects

    async def _parse_connection_card(
        self, card
    ) -> dict[str, Any] | None:
        """Extract data from a single connection card element."""
        try:
            # Try to get name
            name_el = await card.query_selector(
                ".mn-connection-card__name, [data-field='name'], .entity-result__title-text"
            )
            full_name = (await name_el.inner_text()).strip() if name_el else ""

            # Headline / occupation
            headline_el = await card.query_selector(
                ".mn-connection-card__occupation, [data-field='occupation']"
            )
            headline = (await headline_el.inner_text()).strip() if headline_el else ""

            # LinkedIn URL
            link_el = await card.query_selector("a[href*='/in/']")
            linkedin_url = ""
            if link_el:
                href = await link_el.get_attribute("href")
                if href:
                    # Normalise — keep only /in/handle part
                    match = re.search(r"(https://www\.linkedin\.com/in/[^/?]+)", href)
                    if match:
                        linkedin_url = match.group(1)
                    elif href.startswith("/in/"):
                        linkedin_url = f"https://www.linkedin.com{href.split('?')[0]}"

            if not linkedin_url:
                return None

            return {
                "linkedin_url": linkedin_url,
                "full_name": full_name,
                "headline": headline,
                "status": "discovered",
            }
        except Exception as exc:
            logger.debug("Card parse error: %s", exc)
            return None

    async def scrape_profile(
        self,
        auth: LinkedInAuth,
        linkedin_url: str,
    ) -> dict[str, Any]:
        """Visit a LinkedIn profile page and extract detailed information."""
        if auth.page is None:
            raise RuntimeError("Browser not started")

        page = auth.page
        logger.debug("Visiting profile: %s", linkedin_url)
        await page.goto(linkedin_url, wait_until="domcontentloaded")
        await random_delay(2.0, 4.0)

        profile: dict[str, Any] = {"linkedin_url": linkedin_url}

        # Full name
        try:
            el = await page.query_selector("h1.text-heading-xlarge, h1[data-field='name']")
            if el:
                profile["full_name"] = (await el.inner_text()).strip()
        except Exception:
            pass

        # Headline
        try:
            el = await page.query_selector(".text-body-medium.break-words, [data-field='headline']")
            if el:
                profile["headline"] = (await el.inner_text()).strip()
        except Exception:
            pass

        # Location
        try:
            el = await page.query_selector(".text-body-small.inline.t-black--light.break-words")
            if el:
                profile["location"] = (await el.inner_text()).strip()
        except Exception:
            pass

        # Company (current)
        try:
            el = await page.query_selector("[aria-label='Current company'] span.visually-hidden")
            if not el:
                el = await page.query_selector(".pv-text-details__right-panel-item-text")
            if el:
                profile["company"] = (await el.inner_text()).strip()
        except Exception:
            pass

        # Connections count
        try:
            el = await page.query_selector(".pv-top-card--list-bullet .t-bold")
            if el:
                text = (await el.inner_text()).strip()
                match = re.search(r"[\d,]+", text)
                if match:
                    profile["connections_count"] = int(match.group().replace(",", ""))
        except Exception:
            pass

        # About section
        try:
            el = await page.query_selector("#about ~ div .full-width .visually-hidden, #about ~ .pvs-list__outer-container")
            if el:
                profile["about"] = (await el.inner_text()).strip()[:2000]
        except Exception:
            pass

        # Experience (simplified — just text of first few items)
        try:
            exp_items = await page.query_selector_all(
                "#experience ~ div .pvs-list__item--line-separated"
            )
            experience = []
            for item in exp_items[:5]:
                experience.append((await item.inner_text()).strip()[:300])
            profile["experience"] = experience
        except Exception:
            profile["experience"] = []

        # Education
        try:
            edu_items = await page.query_selector_all(
                "#education ~ div .pvs-list__item--line-separated"
            )
            education = []
            for item in edu_items[:3]:
                education.append((await item.inner_text()).strip()[:200])
            profile["education"] = education
        except Exception:
            profile["education"] = []

        logger.debug("Profile scraped: %s — %s", profile.get("full_name"), profile.get("headline"))
        return profile

    async def discover_prospects(
        self,
        auth: LinkedInAuth,
        campaign_id: int,
        limit: int = 50,
        icp_config: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Full discovery pipeline: scrape → score → save to DB."""
        connections = await self.scrape_connections(auth, limit=limit)
        results = []

        for conn_data in connections:
            linkedin_url = conn_data.get("linkedin_url", "")
            if not linkedin_url:
                continue

            # Score with available data (may be enriched later)
            score_result = self.scorer.score(conn_data, icp_config)
            conn_data["icp_score"] = score_result["score"]
            conn_data["icp_breakdown"] = json.dumps(score_result["breakdown"])
            conn_data["campaign_id"] = campaign_id
            conn_data["status"] = "scored"

            if self.db:
                try:
                    self.db.upsert_prospect(conn_data)
                except Exception as exc:
                    logger.error("Failed to save prospect %s: %s", linkedin_url, exc)

            results.append(conn_data)
            await random_delay(0.5, 1.5)

        logger.info(
            "Discovery complete: %d prospects found for campaign %d",
            len(results),
            campaign_id,
        )
        return results
