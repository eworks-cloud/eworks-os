"""Tests for the Closer Agent — Proposal Generation Pipeline."""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from eworks.core.database import DatabaseManager


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_db(tmp_path):
    """Create an in-memory-like DatabaseManager with a temp file DB."""
    db_path = str(tmp_path / "test_eworks.db")
    db = DatabaseManager(db_path=db_path)
    db.init_schema()
    db.add_closer_tables()
    return db


@pytest.fixture
def mock_config():
    """Return a minimal mock config object."""
    cfg = MagicMock()
    cfg.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "test-key")
    cfg.telegram_bot_token = ""
    cfg.telegram_chat_id = ""
    return cfg


def _create_client(db, name="Test Client", company="ACME Corp"):
    """Helper: insert a client row and return its ID."""
    conn = db.get_connection()
    cur = conn.execute(
        "INSERT INTO clients (name, company, status) VALUES (?, ?, 'lead')",
        (name, company),
    )
    conn.commit()
    return cur.lastrowid


# ─── STORY-3.2 Tests ──────────────────────────────────────────────────────────


def test_discovery_call_creation(tmp_db, mock_config):
    """Test that we can create a discovery call and retrieve it."""
    import asyncio
    from eworks.agents.closer.discovery_processor import DiscoveryProcessor

    client_id = _create_client(tmp_db)
    processor = DiscoveryProcessor(db=tmp_db, config=mock_config)

    notes = "Client needs AI automation. Budget around $50k. Timeline 3 months. CTO is the decision maker."
    call_id = asyncio.run(processor.create_call(client_id, notes))

    assert isinstance(call_id, int)
    assert call_id > 0

    conn = tmp_db.get_connection()
    row = conn.execute("SELECT * FROM discovery_calls WHERE id=?", (call_id,)).fetchone()
    assert row is not None
    assert row["raw_notes"] == notes
    assert row["client_id"] == client_id
    assert row["status"] == "notes_taken"


# ─── STORY-3.3 Tests ──────────────────────────────────────────────────────────


def test_pricing_calculation():
    """Test format_pricing_table with 5 deliverables at $150/hr."""
    from eworks.agents.closer.proposal_generator import ProposalGenerator, HOURLY_RATE

    db = MagicMock()
    db.get_setting.return_value = None  # use default rate
    cfg = MagicMock()
    generator = ProposalGenerator(db=db, config=cfg)

    deliverables = [
        "AI Data Pipeline",
        "LLM Integration",
        "API Gateway",
        "Dashboard UI",
        "Testing & QA",
    ]
    pricing = generator.format_pricing_table(deliverables)

    assert pricing["currency"] == "USD"
    assert len(pricing["items"]) == 5
    assert pricing["total"] > 0

    # Each item has required fields
    for item in pricing["items"]:
        assert "name" in item
        assert "hours" in item
        assert "price" in item
        assert item["hours"] > 0
        assert item["price"] == item["hours"] * HOURLY_RATE

    # Total should equal sum of all item prices
    expected_total = sum(item["price"] for item in pricing["items"])
    assert pricing["total"] == pytest.approx(expected_total)

    # With 5 deliverables at default rates, total should be significant
    assert pricing["total"] >= 5 * 40 * HOURLY_RATE  # at minimum 5 * 40h * $150


def test_proposal_markdown_has_sections(tmp_db, mock_config):
    """Test that generated proposal markdown contains required sections."""
    import asyncio
    from eworks.agents.closer.proposal_generator import ProposalGenerator

    # Seed: client + discovery call with already-processed data
    client_id = _create_client(tmp_db)
    conn = tmp_db.get_connection()
    cur = conn.execute(
        """
        INSERT INTO discovery_calls
        (client_id, raw_notes, extracted_requirements, pain_points,
         budget_range, timeline, tech_stack, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'processed')
        """,
        (
            client_id,
            "Client needs AI chatbot for customer support.",
            json.dumps(["Natural language processing", "API integration", "Chat widget"]),
            json.dumps(["High support ticket volume", "Slow response times"]),
            "$30,000 - $50,000",
            "3 months",
            "Python, React, PostgreSQL",
        ),
    )
    conn.commit()
    call_id = cur.lastrowid

    generator = ProposalGenerator(db=tmp_db, config=mock_config)

    # Mock Claude to return a proposal with required sections
    mock_proposal = """# Executive Summary

This proposal outlines our approach to building an AI chatbot solution.

# Problem Understanding

High support ticket volume is causing slow response times.

# Proposed Solution

We will build an NLP-powered chatbot integrated with your existing systems.

# Scope of Work

1. Requirements & Architecture Design
2. NLP Model Integration
3. Chat Widget Development
4. API Integration
5. Testing & QA
6. Deployment & Training

# Technical Approach

Using Claude AI and modern web technologies.

# Timeline

- Week 1-2: Discovery & Architecture
- Week 3-8: Core Development
- Week 9-10: Testing & Deployment

# Investment

Total Investment: $45,000 USD

# Why Eworks Labs

We specialize in AI solutions that deliver measurable results.

# Next Steps

1. Sign engagement letter
2. 50% deposit
3. Project kick-off

# Terms & Conditions

30-day payment terms. All IP transferred upon final payment.
"""

    with patch.object(generator, "_generate_with_claude", new=AsyncMock(return_value=mock_proposal)):
        proposal_id = asyncio.run(generator.generate(call_id))

    assert isinstance(proposal_id, int)
    assert proposal_id > 0

    # Check the proposal in DB
    row = conn.execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
    assert row is not None

    markdown = row["markdown_content"]
    # Required sections must be present
    assert "Executive Summary" in markdown
    assert "Scope of Work" in markdown or "Scope" in markdown
    assert "Investment" in markdown or "Pricing" in markdown
    assert row["total_price"] > 0
    assert row["timeline_weeks"] > 0


# ─── STORY-3.5 Tests ──────────────────────────────────────────────────────────


def test_pipeline_summary_counts(tmp_db, mock_config):
    """Test pipeline summary returns correct status counts."""
    import asyncio
    from eworks.agents.closer.delivery import ProposalDelivery

    # Seed clients and proposals with various statuses
    client_id = _create_client(tmp_db)
    conn = tmp_db.get_connection()

    statuses_and_prices = [
        ("draft", 10000),
        ("draft", 15000),
        ("sent", 25000),
        ("accepted", 50000),
        ("rejected", 5000),
    ]

    for status, price in statuses_and_prices:
        conn.execute(
            """
            INSERT INTO proposals (client_id, title, total_price, status)
            VALUES (?, ?, ?, ?)
            """,
            (client_id, f"Test Proposal ({status})", price, status),
        )
    conn.commit()

    delivery = ProposalDelivery(db=tmp_db, config=mock_config)
    summary = asyncio.run(delivery.get_pipeline_summary())

    assert summary["draft"] == 2
    assert summary["sent"] == 1
    assert summary["accepted"] == 1
    assert summary["rejected"] == 1
    # Pipeline value = sent + viewed + accepted
    assert summary["total_value_pipeline"] == pytest.approx(25000 + 50000)
    assert summary["total_value_won"] == pytest.approx(50000)
