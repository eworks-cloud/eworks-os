"""Telegram reporter for Eworks OS — sends daily reports, alerts and notifications."""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class TelegramReporter:
    """Sends Eworks OS status reports to a Telegram chat."""

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
    ):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
        self._bot = None

    def _get_bot(self):
        """Lazily initialise the python-telegram-bot Application."""
        if self._bot is None:
            try:
                from telegram import Bot  # type: ignore
                self._bot = Bot(token=self.bot_token)
            except ImportError as exc:
                raise RuntimeError(
                    "python-telegram-bot is not installed. Run: pip install python-telegram-bot"
                ) from exc
        return self._bot

    async def send(self, message: str) -> bool:
        """Send a plain text message to the configured Telegram chat."""
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not configured — skipping send")
            return False
        try:
            bot = self._get_bot()
            await bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML",
            )
            logger.debug("Telegram message sent (%d chars)", len(message))
            return True
        except Exception as exc:
            logger.error("Failed to send Telegram message: %s", exc)
            return False

    async def send_daily_report(
        self,
        agent_run: dict[str, Any],
        campaign: dict[str, Any],
    ) -> bool:
        """Format and send the daily campaign report."""
        total_sent = campaign.get("total_sent", 0) or 0
        total_replies = campaign.get("total_replies", 0) or 0
        replies_today = agent_run.get("replies_today", 0) or 0
        meetings_today = agent_run.get("meetings_today", 0) or 0
        rate = round((total_replies / total_sent * 100), 1) if total_sent else 0.0

        message = (
            "📊 <b>Eworks OS — Daily Report</b>\n"
            f"Campaign: <b>{campaign.get('name', 'N/A')}</b>\n"
            "─────────────────\n"
            f"🔍 Scanned: {agent_run.get('prospects_scanned', 0)}\n"
            f"📤 Messages sent: {agent_run.get('messages_sent', 0)}\n"
            f"💬 Replies received: {replies_today}\n"
            f"📅 Meetings booked: {meetings_today}\n"
            "─────────────────\n"
            f"📈 Campaign total: {total_sent} sent / {total_replies} replies\n"
            f"Reply rate: {rate}%"
        )
        return await self.send(message)

    async def send_error_alert(self, error: str, context: str = "") -> bool:
        """Send an error alert to Telegram."""
        message = (
            "🚨 <b>Eworks OS — Error Alert</b>\n\n"
            f"<b>Error:</b> {error}\n"
        )
        if context:
            message += f"<b>Context:</b> {context}"
        return await self.send(message)

    async def send_prospect_reply(
        self,
        prospect_name: str,
        reply_text: str,
    ) -> bool:
        """Notify about a prospect reply."""
        message = (
            "💬 <b>New Reply from Prospect</b>\n\n"
            f"<b>Name:</b> {prospect_name}\n\n"
            f"<b>Reply:</b>\n{reply_text[:500]}"
        )
        return await self.send(message)

    async def send_start_notification(self, campaign_name: str) -> bool:
        """Notify that a campaign run has started."""
        message = (
            "🚀 <b>Eworks OS — Campaign Started</b>\n\n"
            f"Campaign <b>{campaign_name}</b> is now running.\n"
            "I'll send a report when the session is complete."
        )
        return await self.send(message)
