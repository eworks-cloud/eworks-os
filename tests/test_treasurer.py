"""Tests for Epic 5: Invoice & Billing Agent (Treasurer)."""
from __future__ import annotations

import re
import sqlite3
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary database with all required tables."""
    from eworks.core.database import DatabaseManager

    db_path = str(tmp_path / "test_treasurer.db")
    db = DatabaseManager(db_path=db_path)
    db.init_schema()
    db.add_closer_tables()
    db.add_conductor_tables()   # needed for projects FK reference
    db.add_treasurer_tables()
    return db


@pytest.fixture
def mock_config():
    """Minimal config stub."""
    cfg = MagicMock()
    cfg.telegram_bot_token = None
    cfg.telegram_chat_id = None
    return cfg


@pytest.fixture
def sample_client(tmp_db):
    """Insert a test client and return its ID."""
    conn = tmp_db.get_connection()
    cur = conn.execute(
        "INSERT INTO clients (name, company, email) VALUES (?, ?, ?)",
        ("Jane Doe", "Acme Corp", "jane@acme.com"),
    )
    conn.commit()
    return cur.lastrowid


@pytest.fixture
def generator(tmp_db, mock_config):
    from eworks.agents.treasurer.invoice_generator import InvoiceGenerator
    return InvoiceGenerator(db=tmp_db, config=mock_config)


@pytest.fixture
def tracker(tmp_db, mock_config):
    from eworks.agents.treasurer.payment_tracker import PaymentTracker
    return PaymentTracker(db=tmp_db, config=mock_config)


# ── STORY-5.2: Invoice number format ──────────────────────────────────────────

def test_invoice_number_format(generator):
    """Invoice number must match EW-YYYY-NNN pattern."""
    number = generator.generate_invoice_number()
    pattern = r"^EW-\d{4}-\d{3}$"
    assert re.match(pattern, number), f"Invoice number '{number}' doesn't match EW-YYYY-NNN"


def test_invoice_number_increments(generator, tmp_db, sample_client):
    """Each new invoice should get a higher sequence number."""
    items = [{"description": "Service A", "quantity": 1, "unit_price": 100.0}]
    id1 = generator.create_invoice(sample_client, None, items)
    id2 = generator.create_invoice(sample_client, None, items)

    conn = tmp_db.get_connection()
    inv1 = dict(conn.execute("SELECT invoice_number FROM invoices WHERE id=?", (id1,)).fetchone())
    inv2 = dict(conn.execute("SELECT invoice_number FROM invoices WHERE id=?", (id2,)).fetchone())

    seq1 = int(inv1["invoice_number"].split("-")[2])
    seq2 = int(inv2["invoice_number"].split("-")[2])
    assert seq2 == seq1 + 1, f"Expected seq {seq1 + 1} but got {seq2}"


# ── STORY-5.2: Invoice total calculation ──────────────────────────────────────

def test_invoice_total_calculation_no_tax(generator, tmp_db, sample_client):
    """subtotal should equal sum of items; total == subtotal when tax_rate=0."""
    items = [
        {"description": "Dev work", "quantity": 10, "unit_price": 150.0},
        {"description": "Design", "quantity": 5, "unit_price": 80.0},
    ]
    invoice_id = generator.create_invoice(sample_client, None, items, tax_rate=0.0)

    conn = tmp_db.get_connection()
    inv = dict(conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone())

    expected_subtotal = (10 * 150.0) + (5 * 80.0)  # 1900.0
    assert inv["subtotal"] == pytest.approx(expected_subtotal, rel=1e-4)
    assert inv["tax_amount"] == pytest.approx(0.0, abs=1e-4)
    assert inv["total"] == pytest.approx(expected_subtotal, rel=1e-4)


def test_invoice_total_calculation_with_tax(generator, tmp_db, sample_client):
    """subtotal + tax_amount should equal total."""
    items = [{"description": "Consulting", "quantity": 1, "unit_price": 1000.0}]
    invoice_id = generator.create_invoice(sample_client, None, items, tax_rate=10.0)

    conn = tmp_db.get_connection()
    inv = dict(conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone())

    assert inv["subtotal"] == pytest.approx(1000.0)
    assert inv["tax_amount"] == pytest.approx(100.0)
    assert inv["total"] == pytest.approx(1100.0)
    assert abs(inv["subtotal"] + inv["tax_amount"] - inv["total"]) < 0.01


# ── STORY-5.3: Payment marks invoice paid ─────────────────────────────────────

def test_payment_marks_invoice_paid(generator, tracker, tmp_db, sample_client):
    """Full payment should flip invoice status to 'paid'."""
    items = [{"description": "Website build", "quantity": 1, "unit_price": 5000.0}]
    invoice_id = generator.create_invoice(sample_client, None, items)

    # Mark as sent first
    conn = tmp_db.get_connection()
    conn.execute("UPDATE invoices SET status='sent' WHERE id=?", (invoice_id,))
    conn.commit()

    payment_id = tracker.record_payment(
        invoice_id=invoice_id,
        amount=5000.0,
        payment_date=date.today().isoformat(),
        method="wire",
    )

    assert payment_id is not None
    assert payment_id > 0

    inv = dict(conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone())
    assert inv["status"] == "paid"
    assert inv["paid_amount"] == pytest.approx(5000.0)
    assert inv["paid_at"] is not None


def test_partial_payment_does_not_mark_paid(generator, tracker, tmp_db, sample_client):
    """Partial payment should NOT mark invoice as 'paid'."""
    items = [{"description": "Retainer", "quantity": 1, "unit_price": 2000.0}]
    invoice_id = generator.create_invoice(sample_client, None, items)

    conn = tmp_db.get_connection()
    conn.execute("UPDATE invoices SET status='sent' WHERE id=?", (invoice_id,))
    conn.commit()

    tracker.record_payment(invoice_id=invoice_id, amount=999.0, payment_date=date.today().isoformat())

    inv = dict(conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone())
    assert inv["status"] == "sent"  # still sent, not paid


# ── STORY-5.3: Overdue detection ──────────────────────────────────────────────

def test_overdue_detection(generator, tracker, tmp_db, sample_client):
    """Invoices with due_date in the past (status=sent) should appear as overdue."""
    items = [{"description": "SEO services", "quantity": 1, "unit_price": 750.0}]
    invoice_id = generator.create_invoice(sample_client, None, items, due_days=30)

    # Backdate the due date to yesterday
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    conn = tmp_db.get_connection()
    conn.execute(
        "UPDATE invoices SET due_date=?, status='sent' WHERE id=?",
        (yesterday, invoice_id),
    )
    conn.commit()

    overdue = tracker.get_overdue_invoices()
    invoice_ids = [o["id"] for o in overdue]
    assert invoice_id in invoice_ids, f"Invoice {invoice_id} should be detected as overdue"


def test_mark_overdue_invoices(generator, tracker, tmp_db, sample_client):
    """mark_overdue_invoices() should update DB status to 'overdue'."""
    items = [{"description": "PM services", "quantity": 1, "unit_price": 500.0}]
    invoice_id = generator.create_invoice(sample_client, None, items)

    conn = tmp_db.get_connection()
    past_due = (date.today() - timedelta(days=5)).isoformat()
    conn.execute(
        "UPDATE invoices SET due_date=?, status='sent' WHERE id=?",
        (past_due, invoice_id),
    )
    conn.commit()

    count = tracker.mark_overdue_invoices()
    assert count >= 1

    inv = dict(conn.execute("SELECT status FROM invoices WHERE id=?", (invoice_id,)).fetchone())
    assert inv["status"] == "overdue"


# ── STORY-5.3: Revenue summary ────────────────────────────────────────────────

def test_revenue_summary_calculation(generator, tracker, tmp_db, sample_client):
    """Revenue summary should correctly compute totals and collection rate."""
    items_a = [{"description": "Sprint 1", "quantity": 1, "unit_price": 3000.0}]
    items_b = [{"description": "Sprint 2", "quantity": 1, "unit_price": 2000.0}]

    inv_a = generator.create_invoice(sample_client, None, items_a)
    inv_b = generator.create_invoice(sample_client, None, items_b)

    conn = tmp_db.get_connection()
    # Mark one as paid, one as sent
    conn.execute("UPDATE invoices SET status='paid', paid_at=CURRENT_TIMESTAMP, paid_amount=3000 WHERE id=?", (inv_a,))
    conn.execute("UPDATE invoices SET status='sent' WHERE id=?", (inv_b,))
    conn.commit()

    summary = tracker.get_revenue_summary(period="month")

    assert summary["total_invoiced"] >= 5000.0
    assert summary["total_paid"] >= 3000.0
    assert summary["paid_count"] >= 1
    assert summary["collection_rate_pct"] > 0
    assert "total_overdue" in summary
    assert "outstanding_count" in summary


def test_revenue_summary_empty(tracker):
    """Revenue summary on empty DB should return zeros without error."""
    summary = tracker.get_revenue_summary(period="month")
    assert summary["total_invoiced"] == 0.0
    assert summary["total_paid"] == 0.0
    assert summary["collection_rate_pct"] == 0.0


# ── STORY-5.2: Markdown generation ────────────────────────────────────────────

def test_markdown_contains_invoice_number(generator, tmp_db, sample_client):
    """Generated markdown should include the invoice number."""
    items = [{"description": "API integration", "quantity": 1, "unit_price": 1200.0}]
    invoice_id = generator.create_invoice(sample_client, None, items)

    conn = tmp_db.get_connection()
    inv = dict(conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone())

    assert inv["invoice_number"] in (inv.get("markdown_content") or "")
    assert "EWORKS LABS" in (inv.get("markdown_content") or "")
