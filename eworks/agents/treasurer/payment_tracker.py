"""Payment tracker — record payments, detect overdue, revenue summaries."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from eworks.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class PaymentTracker(BaseAgent):
    """Tracks payments against invoices and computes revenue summaries."""

    async def run(self, campaign_id: int) -> dict:
        """Satisfies BaseAgent interface; not used directly."""
        return {"status": "ok", "agent": "PaymentTracker"}

    # ── Record payment ─────────────────────────────────────────────────────────

    def record_payment(
        self,
        invoice_id: int,
        amount: float,
        payment_date: str | date,
        method: str | None = None,
        reference: str | None = None,
        notes: str | None = None,
    ) -> int:
        """
        Record a payment against an invoice.

        If the paid amount >= invoice total, marks invoice as 'paid'.

        Returns:
            payment_id (int)
        """
        if isinstance(payment_date, date):
            payment_date = payment_date.isoformat()

        conn = self.db.get_connection()

        # Fetch invoice
        inv = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if not inv:
            raise ValueError(f"Invoice {invoice_id} not found")
        inv = dict(inv)

        # Insert payment record
        cur = conn.execute(
            """
            INSERT INTO payments (invoice_id, amount, payment_date, payment_method, reference, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (invoice_id, amount, payment_date, method, reference, notes),
        )
        payment_id = cur.lastrowid

        # Check if fully paid
        if amount >= inv["total"]:
            now = datetime.utcnow().isoformat()
            conn.execute(
                "UPDATE invoices SET status='paid', paid_at=?, paid_amount=? WHERE id=?",
                (now, amount, invoice_id),
            )
            self.logger.info(
                "Invoice %s marked as PAID (amount=%.2f, total=%.2f)",
                inv["invoice_number"], amount, inv["total"],
            )
        else:
            self.logger.info(
                "Partial payment %.2f recorded for invoice %s (total=%.2f)",
                amount, inv["invoice_number"], inv["total"],
            )

        conn.commit()
        return payment_id

    # ── Overdue detection ──────────────────────────────────────────────────────

    def get_overdue_invoices(self) -> list[dict[str, Any]]:
        """Return invoices that are sent/overdue and past their due date."""
        today = date.today().isoformat()
        conn = self.db.get_connection()
        rows = conn.execute(
            """
            SELECT i.*, c.name as client_name, c.company, c.email
            FROM invoices i
            LEFT JOIN clients c ON c.id = i.client_id
            WHERE i.status IN ('sent', 'viewed', 'overdue')
              AND i.due_date < ?
            ORDER BY i.due_date ASC
            """,
            (today,),
        ).fetchall()
        return [dict(r) for r in rows]

    def mark_overdue_invoices(self) -> int:
        """
        Update status to 'overdue' for any sent/viewed invoices past their due date.

        Returns:
            Number of invoices updated.
        """
        today = date.today().isoformat()
        conn = self.db.get_connection()
        cur = conn.execute(
            """
            UPDATE invoices
            SET status = 'overdue'
            WHERE status IN ('sent', 'viewed')
              AND due_date < ?
            """,
            (today,),
        )
        conn.commit()
        count = cur.rowcount
        if count:
            self.logger.info("Marked %d invoice(s) as overdue", count)
        return count

    # ── Revenue summary ────────────────────────────────────────────────────────

    def get_revenue_summary(self, period: str = "month") -> dict[str, Any]:
        """
        Return a revenue summary for the given period.

        Args:
            period: 'month', 'quarter', or 'year'

        Returns:
            dict with keys:
                total_invoiced, total_paid, total_overdue,
                outstanding_count, paid_count, collection_rate_pct
        """
        today = date.today()
        if period == "month":
            start_date = today.replace(day=1).isoformat()
        elif period == "quarter":
            quarter_start_month = ((today.month - 1) // 3) * 3 + 1
            start_date = today.replace(month=quarter_start_month, day=1).isoformat()
        elif period == "year":
            start_date = today.replace(month=1, day=1).isoformat()
        else:
            start_date = today.replace(day=1).isoformat()

        conn = self.db.get_connection()

        # Total invoiced in period
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(total), 0) as total_invoiced,
                COUNT(*) as total_count
            FROM invoices
            WHERE status != 'cancelled'
              AND issue_date >= ?
            """,
            (start_date,),
        ).fetchone()
        total_invoiced = row["total_invoiced"] if row else 0.0
        total_count = row["total_count"] if row else 0

        # Total paid in period
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(total), 0) as total_paid,
                COUNT(*) as paid_count
            FROM invoices
            WHERE status = 'paid'
              AND issue_date >= ?
            """,
            (start_date,),
        ).fetchone()
        total_paid = row["total_paid"] if row else 0.0
        paid_count = row["paid_count"] if row else 0

        # Total overdue
        today_str = today.isoformat()
        row = conn.execute(
            """
            SELECT COALESCE(SUM(total), 0) as total_overdue, COUNT(*) as overdue_count
            FROM invoices
            WHERE status IN ('sent', 'viewed', 'overdue')
              AND due_date < ?
            """,
            (today_str,),
        ).fetchone()
        total_overdue = row["total_overdue"] if row else 0.0
        overdue_count = row["overdue_count"] if row else 0

        # Outstanding (sent/viewed not yet overdue)
        row = conn.execute(
            """
            SELECT COUNT(*) as outstanding_count
            FROM invoices
            WHERE status IN ('sent', 'viewed', 'overdue')
              AND issue_date >= ?
            """,
            (start_date,),
        ).fetchone()
        outstanding_count = row["outstanding_count"] if row else 0

        collection_rate_pct = round((total_paid / total_invoiced * 100), 1) if total_invoiced > 0 else 0.0

        return {
            "period": period,
            "start_date": start_date,
            "total_invoiced": round(total_invoiced, 2),
            "total_paid": round(total_paid, 2),
            "total_overdue": round(total_overdue, 2),
            "outstanding_count": outstanding_count,
            "paid_count": paid_count,
            "overdue_count": overdue_count,
            "collection_rate_pct": collection_rate_pct,
        }
