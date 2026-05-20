"""Treasurer orchestrator — daily finance run + Telegram report."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from eworks.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class TreasurerOrchestrator(BaseAgent):
    """Coordinates the daily invoice/billing workflow."""

    async def run(self, campaign_id: int = 0) -> dict:
        """Alias for run_daily."""
        return await self.run_daily()

    async def run_daily(self) -> dict[str, Any]:
        """
        Execute daily treasurer tasks:
            1. Mark overdue invoices
            2. Send payment reminders
            3. Compile revenue summary
            4. Send Telegram finance report

        Returns:
            Summary dict.
        """
        from eworks.agents.treasurer.payment_tracker import PaymentTracker
        from eworks.agents.treasurer.reminder_system import ReminderSystem

        self.logger.info("=== Treasurer Daily Run — %s ===", datetime.utcnow().date())

        # 1. Mark overdue
        tracker = PaymentTracker(db=self.db, config=self.config)
        overdue_updated = tracker.mark_overdue_invoices()
        self.logger.info("Marked %d invoices as overdue", overdue_updated)

        # 2. Send reminders
        reminders = ReminderSystem(db=self.db, config=self.config)
        reminder_result = await reminders.run_daily_reminders()

        # 3. Revenue summary
        summary = tracker.get_revenue_summary(period="month")

        # 4. Build full result
        result = {
            "date": datetime.utcnow().date().isoformat(),
            "overdue_updated": overdue_updated,
            "reminders_sent": reminder_result["reminders_sent"],
            "invoices_checked": reminder_result["invoices_checked"],
            "revenue": summary,
        }

        # 5. Send Telegram report
        await self._send_telegram_report(result)

        return result

    async def _send_telegram_report(self, result: dict[str, Any]) -> None:
        """Send the daily finance report to Telegram."""
        try:
            from eworks.agents.prospector.reporter import TelegramReporter
            reporter = TelegramReporter(
                bot_token=getattr(self.config, "telegram_bot_token", None),
                chat_id=getattr(self.config, "telegram_chat_id", None),
            )

            rev = result["revenue"]
            message = (
                "💰 <b>Eworks Labs — Daily Finance Report</b>\n"
                f"📅 Date: {result['date']}\n"
                "─────────────────\n"
                f"📊 <b>Monthly Revenue ({rev['period'].title()})</b>\n"
                f"  Total Invoiced:   <b>${rev['total_invoiced']:,.2f}</b>\n"
                f"  Total Paid:       <b>${rev['total_paid']:,.2f}</b>\n"
                f"  Total Overdue:    <b>${rev['total_overdue']:,.2f}</b>\n"
                f"  Collection Rate:  <b>{rev['collection_rate_pct']}%</b>\n"
                "─────────────────\n"
                f"🔴 Overdue Invoices:  {rev['overdue_count']}\n"
                f"⏳ Outstanding:       {rev['outstanding_count']}\n"
                f"✅ Paid This Period: {rev['paid_count']}\n"
                "─────────────────\n"
                f"📬 Reminders Sent:    {result['reminders_sent']}\n"
                f"🔍 Invoices Checked: {result['invoices_checked']}\n"
                f"⚠️ Newly Overdue:    {result['overdue_updated']}"
            )
            await reporter.send(message)
            self.logger.info("Daily finance report sent via Telegram")
        except Exception as exc:
            self.logger.error("Failed to send Telegram finance report: %s", exc)
