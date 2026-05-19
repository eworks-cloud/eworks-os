"""Invoice generator — numbering, Markdown, and PDF export."""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from eworks.agents.base import BaseAgent

logger = logging.getLogger(__name__)

INVOICES_DIR = Path("data/invoices")


class InvoiceGenerator(BaseAgent):
    """Generates professional invoices, exports to Markdown and PDF."""

    def __init__(self, db, config):
        super().__init__(db, config)
        INVOICES_DIR.mkdir(parents=True, exist_ok=True)

    # ── Abstract method fulfillment ────────────────────────────────────────────

    async def run(self, campaign_id: int) -> dict:
        """Not used for invoice generation; satisfies BaseAgent interface."""
        return {"status": "ok", "agent": "InvoiceGenerator"}

    # ── Invoice number generation ──────────────────────────────────────────────

    def generate_invoice_number(self) -> str:
        """Generate next sequential invoice number in EW-YYYY-NNN format."""
        year = datetime.utcnow().year
        conn = self.db.get_connection()
        # Count invoices for current year
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM invoices WHERE invoice_number LIKE ?",
            (f"EW-{year}-%",),
        ).fetchone()
        seq = (row["cnt"] if row else 0) + 1
        return f"EW-{year}-{seq:03d}"

    # ── Create invoice ─────────────────────────────────────────────────────────

    def create_invoice(
        self,
        client_id: int,
        project_id: int | None,
        items: list[dict],
        due_days: int = 30,
        notes: str | None = None,
        tax_rate: float = 0.0,
    ) -> int:
        """
        Create an invoice with line items.

        Args:
            client_id: ID of the client in the clients table.
            project_id: Optional project ID.
            items: List of dicts with keys: description, quantity, unit_price.
            due_days: Number of days until invoice is due.
            notes: Optional notes / payment instructions.
            tax_rate: Tax percentage (e.g. 10.0 for 10%).

        Returns:
            invoice_id (int)
        """
        today = date.today()
        due_date = today + timedelta(days=due_days)

        # Calculate totals
        subtotal = sum(
            float(item["quantity"]) * float(item["unit_price"]) for item in items
        )
        tax_amount = round(subtotal * (tax_rate / 100.0), 2)
        total = round(subtotal + tax_amount, 2)
        subtotal = round(subtotal, 2)

        invoice_number = self.generate_invoice_number()
        payment_terms = f"Net {due_days}"

        conn = self.db.get_connection()
        cur = conn.execute(
            """
            INSERT INTO invoices (
                client_id, project_id, invoice_number, issue_date, due_date,
                status, subtotal, tax_rate, tax_amount, total,
                notes, payment_terms
            ) VALUES (?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?, ?)
            """,
            (
                client_id, project_id, invoice_number,
                today.isoformat(), due_date.isoformat(),
                subtotal, tax_rate, tax_amount, total,
                notes, payment_terms,
            ),
        )
        invoice_id = cur.lastrowid

        # Insert line items
        for item in items:
            qty = float(item["quantity"])
            unit_price = float(item["unit_price"])
            item_total = round(qty * unit_price, 2)
            conn.execute(
                """
                INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total)
                VALUES (?, ?, ?, ?, ?)
                """,
                (invoice_id, item["description"], qty, unit_price, item_total),
            )

        conn.commit()
        self.logger.info("Created invoice %s (id=%d) for client_id=%d", invoice_number, invoice_id, client_id)

        # Auto-generate markdown content
        self.generate_markdown(invoice_id)

        return invoice_id

    # ── Markdown generation ────────────────────────────────────────────────────

    def generate_markdown(self, invoice_id: int) -> str:
        """Generate professional Markdown invoice. Saves to DB. Returns markdown string."""
        conn = self.db.get_connection()
        inv = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if not inv:
            raise ValueError(f"Invoice {invoice_id} not found")
        inv = dict(inv)

        # Fetch client
        client = conn.execute(
            "SELECT * FROM clients WHERE id=?", (inv["client_id"],)
        ).fetchone()
        client = dict(client) if client else {"name": "Unknown", "company": "", "email": ""}

        # Fetch line items
        items = conn.execute(
            "SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id", (invoice_id,)
        ).fetchall()
        items = [dict(i) for i in items]

        # Build markdown
        lines = []
        lines.append("# EWORKS LABS")
        lines.append("")
        lines.append(f"**Invoice #{inv['invoice_number']}**")
        lines.append("")
        lines.append(f"| | |")
        lines.append(f"|---|---|")
        lines.append(f"| **Issue Date** | {inv['issue_date']} |")
        lines.append(f"| **Due Date** | {inv['due_date']} |")
        lines.append(f"| **Payment Terms** | {inv['payment_terms']} |")
        lines.append(f"| **Currency** | {inv['currency']} |")
        lines.append(f"| **Status** | {inv['status'].upper()} |")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Bill To")
        lines.append("")
        lines.append(f"**{client['name']}**")
        if client.get("company"):
            lines.append(f"{client['company']}")
        if client.get("email"):
            lines.append(f"{client['email']}")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Services")
        lines.append("")
        lines.append("| Description | Qty | Unit Price | Total |")
        lines.append("|---|---|---|---|")
        for item in items:
            lines.append(
                f"| {item['description']} | {item['quantity']:.2f} | "
                f"${item['unit_price']:,.2f} | ${item['total']:,.2f} |"
            )
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append(f"| | |")
        lines.append(f"|---|---|")
        lines.append(f"| **Subtotal** | ${inv['subtotal']:,.2f} |")
        if inv.get("tax_rate") and inv["tax_rate"] > 0:
            lines.append(f"| **Tax ({inv['tax_rate']:.1f}%)** | ${inv['tax_amount']:,.2f} |")
        lines.append(f"| **TOTAL DUE** | **${inv['total']:,.2f} {inv['currency']}** |")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Payment Instructions")
        lines.append("")
        lines.append("Please remit payment by the due date listed above.")
        lines.append("For wire transfers, ACH, or other payment methods, please contact us at:")
        lines.append("billing@eworkslabs.com")
        lines.append("")
        if inv.get("notes"):
            lines.append("## Notes")
            lines.append("")
            lines.append(inv["notes"])
            lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*Thank you for your business!*")
        lines.append("")
        lines.append("**Eworks Labs** | billing@eworkslabs.com | eworkslabs.com")

        markdown = "\n".join(lines)

        # Save to DB
        conn.execute(
            "UPDATE invoices SET markdown_content=? WHERE id=?",
            (markdown, invoice_id),
        )
        conn.commit()
        self.logger.debug("Generated markdown for invoice %d", invoice_id)
        return markdown

    # ── PDF export ─────────────────────────────────────────────────────────────

    def export_pdf(self, invoice_id: int) -> str:
        """Export invoice to PDF (falls back to .txt if weasyprint unavailable). Returns file path."""
        conn = self.db.get_connection()
        inv = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
        if not inv:
            raise ValueError(f"Invoice {invoice_id} not found")
        inv = dict(inv)

        content = inv.get("markdown_content") or self.generate_markdown(invoice_id)
        invoice_number = inv["invoice_number"].replace("/", "-")
        title = f"Invoice {invoice_number}"

        pdf_path = self._try_pdf_export(invoice_id, invoice_number, title, content)

        conn.execute("UPDATE invoices SET pdf_path=? WHERE id=?", (pdf_path, invoice_id))
        conn.commit()
        self.logger.info("Exported invoice PDF: %s", pdf_path)
        return pdf_path

    def _try_pdf_export(self, invoice_id: int, slug: str, title: str, content: str) -> str:
        """Attempt PDF via weasyprint, fallback to styled .txt."""
        try:
            import markdown2  # type: ignore
            from weasyprint import HTML  # type: ignore

            html_body = markdown2.markdown(content, extras=["tables", "fenced-code-blocks"])
            html_full = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: Georgia, serif; max-width: 800px; margin: 40px auto; color: #222; line-height: 1.6; }}
  h1 {{ color: #1a1a2e; border-bottom: 3px solid #4a90d9; padding-bottom: 8px; }}
  h2 {{ color: #16213e; margin-top: 2em; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
  th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
  th {{ background: #4a90d9; color: white; }}
  code {{ background: #f4f4f4; padding: 2px 5px; border-radius: 3px; }}
  hr {{ border: 1px solid #eee; margin: 2em 0; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""
            pdf_file = INVOICES_DIR / f"{invoice_id}-{slug}.pdf"
            HTML(string=html_full).write_pdf(str(pdf_file))
            return str(pdf_file)

        except ImportError as exc:
            logger.warning("PDF library not available (%s), falling back to .txt", exc)
            return self._export_txt(invoice_id, slug, title, content)
        except Exception as exc:
            logger.error("PDF generation failed (%s), falling back to .txt", exc)
            return self._export_txt(invoice_id, slug, title, content)

    def _export_txt(self, invoice_id: int, slug: str, title: str, content: str) -> str:
        """Fallback: export as formatted plain text file."""
        txt_file = INVOICES_DIR / f"{invoice_id}-{slug}.txt"
        header = f"{'=' * 70}\n{title.upper()}\n{'=' * 70}\n\n"
        plain = re.sub(r"^#{1,6}\s+", "", content, flags=re.MULTILINE)
        txt_file.write_text(header + plain, encoding="utf-8")
        return str(txt_file)
