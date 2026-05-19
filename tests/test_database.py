"""Tests for DatabaseManager — schema creation and CRUD operations."""
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from eworks.core.database import DatabaseManager


@pytest.fixture
def db(tmp_path):
    """Provide a fresh DatabaseManager backed by a temp file."""
    db_path = str(tmp_path / "test_eworks.db")
    mgr = DatabaseManager(db_path=db_path)
    mgr.init_schema()
    yield mgr
    mgr.close()


def test_init_schema(db):
    """All 8 required tables must be created by init_schema()."""
    expected_tables = {
        "campaigns",
        "prospects",
        "messages",
        "task_queue",
        "agent_runs",
        "personas",
        "linkedin_accounts",
        "settings_store",
    }
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    found = {row["name"] for row in rows}
    assert expected_tables.issubset(found), f"Missing tables: {expected_tables - found}"


def test_upsert_prospect(db):
    """Inserting a prospect then upserting with updated data should update the row."""
    prospect = {
        "linkedin_url": "https://www.linkedin.com/in/test-user",
        "full_name": "Test User",
        "headline": "CEO at TestCo",
        "company": "TestCo",
        "location": "São Paulo, Brazil",
    }
    # Insert
    pid = db.upsert_prospect(prospect)
    assert isinstance(pid, int) and pid > 0

    # Update
    db.upsert_prospect({
        "linkedin_url": "https://www.linkedin.com/in/test-user",
        "full_name": "Test User Updated",
        "headline": "Founder & CEO at TestCo",
    })

    row = db.get_prospect_by_linkedin_url("https://www.linkedin.com/in/test-user")
    assert row is not None
    assert row["full_name"] == "Test User Updated"
    assert row["headline"] == "Founder & CEO at TestCo"
    assert row["location"] == "São Paulo, Brazil"  # Original preserved


def test_get_pending_tasks(db):
    """Tasks inserted as pending should be returned by get_pending_tasks()."""
    conn = db.get_connection()
    conn.execute(
        "INSERT INTO task_queue (task_type, payload, priority) VALUES (?, ?, ?)",
        ("discover_prospects", json.dumps({"campaign_id": 1}), 3),
    )
    conn.execute(
        "INSERT INTO task_queue (task_type, payload, priority) VALUES (?, ?, ?)",
        ("send_messages", json.dumps({"campaign_id": 1}), 5),
    )
    # Insert a 'done' task that should NOT be returned
    conn.execute(
        "INSERT INTO task_queue (task_type, status) VALUES (?, 'done')",
        ("old_task",),
    )
    conn.commit()

    tasks = db.get_pending_tasks()
    assert len(tasks) == 2
    # Should be ordered by priority (lower first)
    assert tasks[0]["task_type"] == "discover_prospects"
    assert tasks[0]["priority"] == 3


def test_campaign_crud(db):
    """Create, read and update a campaign."""
    # Create
    cid = db.create_campaign({
        "name": "Q3 Outreach",
        "daily_limit": 15,
        "status": "draft",
    })
    assert isinstance(cid, int) and cid > 0

    # Read
    c = db.get_campaign(cid)
    assert c is not None
    assert c["name"] == "Q3 Outreach"
    assert c["daily_limit"] == 15
    assert c["status"] == "draft"

    # Update
    db.update_campaign(cid, {"status": "active", "daily_limit": 20})
    c2 = db.get_campaign(cid)
    assert c2["status"] == "active"
    assert c2["daily_limit"] == 20

    # List
    campaigns = db.list_campaigns()
    assert any(c["id"] == cid for c in campaigns)
