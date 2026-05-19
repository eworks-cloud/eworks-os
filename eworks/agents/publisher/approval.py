"""Telegram approval flow for content before publishing."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot"


class TelegramApproval:
    """Sends content previews to Telegram and waits for human approval."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"{TELEGRAM_API_BASE}{bot_token}"

    async def send_approval_request(self, content_package: dict[str, Any]) -> str:
        """Send a formatted content preview and wait for approval.

        Args:
            content_package: Dict with keys: title, reel_script, instagram_caption,
                             youtube_title (optional), post_id (optional)

        Returns:
            'approved', 'rejected', or 'timeout'
        """
        title = content_package.get("title", "Untitled")
        reel_script = content_package.get("reel_script", "")
        instagram_caption = content_package.get("instagram_caption", "")
        post_id = content_package.get("post_id", "")

        # Truncate reel script for preview
        reel_preview = reel_script[:300] + "..." if len(reel_script) > 300 else reel_script

        message = (
            f"🎬 *Content Approval Request*\n\n"
            f"*Title:* {title}\n\n"
            f"*Reel Script Preview:*\n_{reel_preview}_\n\n"
            f"*Instagram Caption:*\n{instagram_caption[:200]}"
            f"{'...' if len(instagram_caption) > 200 else ''}"
        )

        if post_id:
            message += f"\n\n*Post ID:* `{post_id}`"

        callback_prefix = f"pub_{post_id}" if post_id else f"pub_{int(time.time())}"
        inline_keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Approve", "callback_data": f"{callback_prefix}_approve"},
                    {"text": "❌ Reject", "callback_data": f"{callback_prefix}_reject"},
                ]
            ]
        }

        import json as _json

        async with aiohttp.ClientSession() as session:
            # Send the message
            async with session.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "reply_markup": inline_keyboard,
                },
            ) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    logger.error("Failed to send Telegram approval: %s", data)
                    return "timeout"
                message_id = data["result"]["message_id"]
                logger.info("Sent approval request (msg_id=%s)", message_id)

            # Poll for callback response — up to 24 hours
            decision = await self._wait_for_decision(
                session, callback_prefix, max_wait=86400
            )

        return decision

    async def _wait_for_decision(
        self,
        session: aiohttp.ClientSession,
        callback_prefix: str,
        poll_interval: int = 15,
        max_wait: int = 86400,
    ) -> str:
        """Poll getUpdates for the callback query matching our prefix."""
        elapsed = 0
        offset = None

        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            params = {"timeout": poll_interval, "allowed_updates": ["callback_query"]}
            if offset is not None:
                params["offset"] = offset

            try:
                async with session.get(
                    f"{self.base_url}/getUpdates", params=params
                ) as resp:
                    data = await resp.json()
                    if not data.get("ok"):
                        continue

                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        cb = update.get("callback_query", {})
                        cb_data = cb.get("data", "")

                        if cb_data.startswith(callback_prefix):
                            # Answer the callback to remove loading state
                            await session.post(
                                f"{self.base_url}/answerCallbackQuery",
                                json={"callback_query_id": cb["id"]},
                            )
                            if cb_data.endswith("_approve"):
                                logger.info("Content APPROVED via Telegram")
                                return "approved"
                            elif cb_data.endswith("_reject"):
                                logger.info("Content REJECTED via Telegram")
                                return "rejected"

            except Exception as exc:
                logger.warning("Telegram poll error: %s", exc)

        logger.warning("Approval timeout after %ds", max_wait)
        return "timeout"

    async def send_message(self, text: str) -> dict[str, Any]:
        """Send a plain text message to the configured chat."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                },
            ) as resp:
                data = await resp.json()
                return data
