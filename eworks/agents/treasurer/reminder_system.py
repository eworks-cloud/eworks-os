"""Payment reminder system — escalating automated reminders via Telegram."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from eworks.agents.base import BaseAgent

logger = logging.getLogger(__name__)

# Reminder message templates
REMINDER_TEMPLATES = {
    "upcoming": (
        "📅 <b>Payment Reminder — Invoice Due Soon</b>\n\n"
        "Hi {client_name},\n\n"
        "This is a friendly reminder that invoice <b>#{invoice_number}</b> "
        "for <b>${total:,.2f} {currency}</b> is due on <b>{due_date}</b>.\n\n"
        "Please ensure payment is arranged before the due date.\n\n"
        "Thank you for your business! 🙏\n"
        "<i>— Eworks Labs Billing Team</i>"
    ),
    "due_today": (
        "⏰ <b>Invoice Due Today</b>\n\n"
        "Hi {client_name},\n\n"
        "Invoice <b>#{invoice_number}</b> for <b>${total:,.2f} {currency}</b> "
        "is due <b>today</b>.\n\n"
        "Please process payment at your earliest convenience.\n\n"
        "<i>— Eworks Labs Billing Team</i>"
    ),
    "overdue_3d": (
        "⚠️ <b>Overdue Invoice — 3 Days Past Due</b>\n\n"
        "Hi {client_name},\n\n"
        "Invoice <b>#{invoice_number}</b> for <b>${total:,.2f} {currency}</b> "
        "was due on <b>{due_date}</b> and is now <b>3 days overdue</b>.\n\n"
        "Please arrange payment immediately to avoid any disruption to services.\n\n"
        "If you have any questions, please contact us at billing@eworkslabs.com.\n\n"
        "<i>— Eworks Labs Billing Team</i>"
    ),
    "overdue_7d": (
        "🚨 <b>Urgent: Invoice 7 Days Overdue</b>\n\n"
        "Hi {client_name},\n\n"
        "Invoice <b>#{invoice_number}</b> for <b>${total:,.2f} {currency}</b> "
        "is now <b>7 days past due</b> (due date: {due_date}).\n\n"
        "Immediate payment is required. Continued non-payment may affect your "
        "account standing and access to our services.\n\n"
        "Please contact us immediately at billing@eworkslabs.com or call us "
        "to discuss payment arrangements.\n\n"
        "<i>— Eworks Labs Billing Team</i>"
    ),
    "overdue_14d": (
        "🔴 <b>FINAL NOTICE — Invoice 14 Days Overdue</b>\n\n"
        "Hi {client_name},\n\n"
        "This is a <b>FINAL NOTICE</b> regarding invoice <b>#{invoice_number}</b> "
        "for <b>${total:,.2f} {currency}</b> which is <b>14 days past due</b>.\n\n"
        "If payment is not received within 48 hours, this account may be referred "
        "to our collections department.\n\n"
        "To resolve this matter immediately, please contact:\n"
        "📧 billing@eworkslabs.com\n\n"
        "<b>Outstanding Balance: ${total:,.2f} {currency}</b>\n\n"
        "<i>— Eworks Labs Billing Team</i>"
    ),
    "final_notice": (
        "🔴 <b>FINAL NOTICE — Collections Referral Pending</b>\n\n"
        "Hi {client_name},\n\n"
        "Invoice <b>#{invoice_number}</b> for <b>${total:,.2f} {currency}</b> "
        "remains unpaid.\n\n"
        "This is your final opportunity to resolve this matter before referral "
        "to our collections department.\n\n"
        "<b>Please contact billing@eworkslabs.com within 24 hours.</b>\n\n"
        "<i>— Eworks Labs Billing Team</i>"
    ),
}


class ReminderSystem(BaseAgent):
    """Sends escalating payment reminders for unpaid invoices via Telegram."""

    async def run(self, campaign_id: int) -> dict:
        """Satisfies BaseAgent interface."""
        return await self.run_daily_reminders()

    def _get_reporter(self):
        """Lazily create a TelegramReporter."""
        from eworks.agents.prospector.reporter import TelegramReporter
        return TelegramReporter(
            bot_token=getattr(self.config, "telegram_bot_token", None),
            chat_id=getattr(self.config, "telegram_chat_id", None),
        )

    async def send_reminder(self, invoice_id: int, reminder_type: str) -> bool:
        """
        Format and send a reminder message for the given invoice.

        Args:
            invoice_id: Invoice to send reminder for.
            reminder_type: One of upcoming/due_today/overdue_3d/overdue_7d/overdue_14d/final_notice

        Returns:
            True if sent successfully, False otherwise.
        """
        conn = self.db.get_connection()
        inv = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if not inv:
            self.logger.error("Invoice %d not found for reminder", invoice_id)
            return False
        inv = dict(inv)

        client = conn.execute(
            "SELECT * FROM clients WHERE id=?", (inv["client_id"],)
        ).fetchone()
        client = dict(client) if client else {"name": "Valued Client", "company": ""}
        client_name = client.get("name", "Valued Client")

        template = REMINDER_TEMPLATES.get(reminder_type, REMINDER_TEMPLATES["upcoming"])
        message = template.format(
            client_name=client_name,
            invoice_number=inv["invoice_number"],
            total=inv["total"],
            currency=inv.get("currency", "USD"),
            due_date=inv["due_date"],
        )

        try:
            reporter = self._get_reporter()
            success = await reporter.send(message)
        except Exception as exc:
            self.logger.error("Failed to send Telegram reminder: %s", exc)
            success = False

        # Log reminder regardless of send success
        conn.execute(
            """
            INSERT INTO payment_reminders (invoice_id, reminder_type, sent_via)
            VALUES (?, ?, 'telegram')
            """,
            (invoice_id, reminder_type),
        )
        conn.commit()

        self.logger.info(
            "Reminder '%s' sent for invoice %s (success=%s)",
            reminder_type, inv["invoice_number"], success,
        )
        return success

    async def run_daily_reminders(self) -> dict[str, Any]:
        """
        Check all unpaid invoices and send appropriate reminders.

        Logic:
            - Due in <= 3 days -> 'upcoming' (if not sent today)
            - 3 days overdue -> 'overdue_3d'
            - 7 days overdue -> 'overdue_7d'
            - 14+ days overdue -> 'overdue_14d'

        Returns:
            dict: {reminders_sent, invoices_checked}
        """
        today = date.today()
        conn = self.db.get_connection()

        # Get all unpaid invoices (draft excluded — only sent/viewed/overdue)
        rows = conn.execute(
            """
            SELECT i.*, c.name as client_name
            FROM invoices i
            LEFT JOIN clients c ON c.id = i.client_id
            WHERE i.status IN ('sent', 'viewed', 'overdue')
            ORDER BY i.due_date ASC
            """,
        ).fetchall()

        invoices = [dict(r) for r in rows]
        reminders_sent = 0
        invoices_checked = len(invoices)

        for inv in invoices:
            invoice_id = inv["id"]
            due_date = date.fromisoformat(inv["due_date"])
            days_until_due = (due_date - today).days  # negative = overdue

            # Determine which reminder type to send
            reminder_type = None
            if days_until_due >= 0 and days_until_due <= 3:
                reminder_type = "upcoming"
            elif days_until_due < 0:
                days_overdue = abs(days_until_due)
                if days_overdue >= 14:
                    reminder_type = "overdue_14d"
                elif days_overdue >= 7:
                    reminder_type = "overdue_7d"
                elif days_overdue >= 3:
                    reminder_type = "overdue_3d"

            if not reminder_type:
                continue

            # Check if already sent this reminder type today
            today_str = today.isoformat()
            already_sent = conn.execute(
                """
                SELECT 1 FROM payment_reminders
                WHERE invoice_id=? AND reminder_type=?
                  AND DATE(sent_at) = ?
                LIMIT 1
                """,
                (invoice_id, reminder_type, today_str),
            ).fetchone()

            if already_sent:
                self.logger.debug(
                    "Reminder '%s' already sent today for invoice %d — skipping",
                    reminder_type, invoice_id,
                )
                continue

            sent = await self.send_reminder(invoice_id, reminder_type)
            if sent:
                reminders_sent += 1

        self.logger.info(
            "Daily reminders complete: %d sent, %d invoices checked",
            reminders_sent, invoices_checked,
        )
        return {"reminders_sent": reminders_sent, "invoices_checked": invoices_checked}
