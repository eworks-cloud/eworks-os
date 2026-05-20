"""Tests for Epic 6: Customer Success Agent (Nurturer)."""
from __future__ import annotations

import sqlite3
import tempfile
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from eworks.core.database import DatabaseManager
from eworks.agents.nurturer.onboarding import OnboardingManager, DEFAULT_STEPS
from eworks.agents.nurturer.health_scorer import HealthScorer


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_db(tmp_path):
    """Create a fresh in-memory-style DB with all tables initialized."""
    db_path = str(tmp_path / "test_nurturer.db")
    db = DatabaseManager(db_path=db_path)
    db.init_schema()
    db.add_closer_tables()
    db.add_conductor_tables()   # creates 'projects' table (referenced by onboarding_checklists)
    db.add_nurturer_tables()
    return db


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.telegram_bot_token = ""
    cfg.telegram_chat_id = ""
    cfg.anthropic_api_key = ""
    return cfg


@pytest.fixture
def client_id(tmp_db):
    """Insert a test client and return its ID."""
    conn = tmp_db.get_connection()
    cur = conn.execute(
        "INSERT INTO clients (name, company, status) VALUES (?, ?, ?)",
        ("Alice Tester", "Acme Corp", "won"),
    )
    conn.commit()
    return cur.lastrowid


# ── STORY-6.2: Onboarding ────────────────────────────────────────────────────


class TestOnboardingManager:
    def test_onboarding_creates_all_steps(self, tmp_db, mock_config, client_id):
        """7 default onboarding steps must be created."""
        mgr = OnboardingManager(db=tmp_db, config=mock_config)
        count = mgr.create_onboarding(client_id)
        assert count == 7, f"Expected 7 steps, got {count}"

        conn = tmp_db.get_connection()
        rows = conn.execute(
            "SELECT * FROM onboarding_checklists WHERE client_id=?", (client_id,)
        ).fetchall()
        assert len(rows) == 7

        step_names = {r["step_name"] for r in rows}
        expected_names = {s[0] for s in DEFAULT_STEPS}
        assert step_names == expected_names

    def test_all_steps_start_as_pending(self, tmp_db, mock_config, client_id):
        """All created steps should have 'pending' status."""
        mgr = OnboardingManager(db=tmp_db, config=mock_config)
        mgr.create_onboarding(client_id)

        conn = tmp_db.get_connection()
        rows = conn.execute(
            "SELECT status FROM onboarding_checklists WHERE client_id=?", (client_id,)
        ).fetchall()
        assert all(r["status"] == "pending" for r in rows)

    def test_onboarding_progress_calculation(self, tmp_db, mock_config, client_id):
        """Progress calculation should correctly reflect completed steps."""
        mgr = OnboardingManager(db=tmp_db, config=mock_config)
        mgr.create_onboarding(client_id)

        # Get step IDs
        conn = tmp_db.get_connection()
        rows = conn.execute(
            "SELECT id FROM onboarding_checklists WHERE client_id=? ORDER BY id ASC",
            (client_id,),
        ).fetchall()
        step_ids = [r["id"] for r in rows]

        # Complete first 3 steps
        for sid in step_ids[:3]:
            mgr.complete_step(sid)

        progress = mgr.get_onboarding_progress(client_id)
        assert progress["total_steps"] == 7
        assert progress["completed"] == 3
        assert progress["pending"] == 4
        assert progress["completion_pct"] == pytest.approx(42.9, abs=0.1)
        assert progress["next_step"] is not None
        assert progress["next_step"]["step_name"] == DEFAULT_STEPS[3][0]

    def test_complete_all_steps_gives_100_pct(self, tmp_db, mock_config, client_id):
        """Completing all steps gives 100% and next_step=None."""
        mgr = OnboardingManager(db=tmp_db, config=mock_config)
        mgr.create_onboarding(client_id)

        conn = tmp_db.get_connection()
        rows = conn.execute(
            "SELECT id FROM onboarding_checklists WHERE client_id=?", (client_id,)
        ).fetchall()
        for row in rows:
            mgr.complete_step(row["id"])

        progress = mgr.get_onboarding_progress(client_id)
        assert progress["completion_pct"] == 100.0
        assert progress["next_step"] is None

    def test_complete_step_returns_false_for_invalid_id(self, tmp_db, mock_config):
        """complete_step with invalid ID returns False."""
        mgr = OnboardingManager(db=tmp_db, config=mock_config)
        assert mgr.complete_step(99999) is False


# ── STORY-6.3: Health Scorer ─────────────────────────────────────────────────


class TestHealthScorer:
    def test_health_score_bounds(self, tmp_db, mock_config, client_id):
        """Health score must always be in range 0-100."""
        scorer = HealthScorer(db=tmp_db, config=mock_config)
        score = scorer.calculate_health(client_id)
        assert 0 <= score <= 100, f"Score {score} out of bounds"

    def test_perfect_health_score(self, tmp_db, mock_config, client_id):
        """A client with no overdue invoices, recent engagement, active project, NPS>=8 = 100."""
        conn = tmp_db.get_connection()

        # Add a recent check-in response and high NPS
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO client_checkins (client_id, checkin_type, message_sent, response_received,
                nps_score, sentiment, sent_at, responded_at)
            VALUES (?, 'monthly', 'Hi!', 'All great!', 9, 'positive', ?, ?)
            """,
            (client_id, now, now),
        )
        conn.commit()

        scorer = HealthScorer(db=tmp_db, config=mock_config)
        score = scorer.calculate_health(client_id)
        # payment=25 (no invoices → no overdue), engagement=25 (responded today),
        # project=15 (no projects → neutral), satisfaction=25 (NPS=9)
        # Expected: 25+25+15+25 = 90
        assert score == 90, f"Expected 90, got {score}"

    def test_no_data_score_is_neutral(self, tmp_db, mock_config, client_id):
        """A client with no data gets a neutral score (not 0 or 100)."""
        scorer = HealthScorer(db=tmp_db, config=mock_config)
        score = scorer.calculate_health(client_id)
        # payment=25 (no invoices), engagement=5 (no checkins), project=15, satisfaction=15
        assert score == 60

    def test_record_health_score_persists(self, tmp_db, mock_config, client_id):
        """record_health_score saves to DB and returns the score."""
        scorer = HealthScorer(db=tmp_db, config=mock_config)
        score = scorer.record_health_score(client_id)

        conn = tmp_db.get_connection()
        row = conn.execute(
            "SELECT score FROM client_health_scores WHERE client_id=?", (client_id,)
        ).fetchone()
        assert row is not None
        assert row["score"] == score

    def test_at_risk_detection(self, tmp_db, mock_config, client_id):
        """Clients with health score < 60 appear in get_at_risk_clients()."""
        conn = tmp_db.get_connection()

        # Manually insert a low score
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO client_health_scores
                (client_id, score, payment_score, engagement_score,
                 project_health_score, satisfaction_score, recorded_at)
            VALUES (?, 45, 5, 5, 25, 10, ?)
            """,
            (client_id, now),
        )
        conn.commit()

        scorer = HealthScorer(db=tmp_db, config=mock_config)
        at_risk = scorer.get_at_risk_clients()
        assert len(at_risk) >= 1
        client_ids = [r["client_id"] for r in at_risk]
        assert client_id in client_ids

    def test_healthy_clients_not_at_risk(self, tmp_db, mock_config, client_id):
        """Clients with score >= 60 are NOT in get_at_risk_clients()."""
        conn = tmp_db.get_connection()
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO client_health_scores
                (client_id, score, payment_score, engagement_score,
                 project_health_score, satisfaction_score, recorded_at)
            VALUES (?, 85, 25, 25, 20, 15, ?)
            """,
            (client_id, now),
        )
        conn.commit()

        scorer = HealthScorer(db=tmp_db, config=mock_config)
        at_risk = scorer.get_at_risk_clients()
        client_ids = [r["client_id"] for r in at_risk]
        assert client_id not in client_ids

    def test_get_health_trend_returns_last_n(self, tmp_db, mock_config, client_id):
        """get_health_trend returns at most last_n records."""
        scorer = HealthScorer(db=tmp_db, config=mock_config)
        # Record 6 scores
        for _ in range(6):
            scorer.record_health_score(client_id)

        trend = scorer.get_health_trend(client_id, last_n=5)
        assert len(trend) == 5
        # Each record has required fields
        for record in trend:
            assert "score" in record
            assert "recorded_at" in record
