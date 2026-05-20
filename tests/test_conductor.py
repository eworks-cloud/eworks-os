"""Tests for the Conductor (Project Management Agent)."""
from __future__ import annotations

import asyncio
import sqlite3
import tempfile
from pathlib import Path
from datetime import date, timedelta

import pytest

from eworks.core.database import DatabaseManager


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


class FakeConfig:
    telegram_bot_token = ""
    telegram_chat_id = ""
    database_path = ":memory:"


@pytest.fixture
def db(tmp_path):
    """Provide an in-memory DatabaseManager with all schemas initialised."""
    db_path = str(tmp_path / "test.db")
    manager = DatabaseManager(db_path=db_path)
    manager.init_schema()
    manager.add_closer_tables()
    manager.add_conductor_tables()
    return manager


@pytest.fixture
def tracker(db):
    from eworks.agents.conductor.tracker import ProjectTracker
    return ProjectTracker(db=db, config=FakeConfig())


@pytest.fixture
def sprint_mgr(db):
    from eworks.agents.conductor.sprint_manager import SprintManager
    return SprintManager(db=db, config=FakeConfig())


@pytest.fixture
def sample_project(db, tracker):
    """Create a simple project and return its ID."""
    # Add a client first (closer tables)
    conn = db.get_connection()
    cur = conn.execute(
        "INSERT INTO clients (name, company, status) VALUES ('Test Client', 'ACME', 'won')"
    )
    conn.commit()
    client_id = cur.lastrowid

    today = date.today().isoformat()
    end = (date.today() + timedelta(days=30)).isoformat()
    pid = tracker.create_project(
        client_id=client_id,
        proposal_id=None,
        name="Test Project",
        start_date=today,
        end_date=end,
        budget=10_000.0,
        hourly_rate=150.0,
    )
    # Make it active
    conn.execute("UPDATE projects SET status='active' WHERE id=?", (pid,))
    conn.commit()
    return pid


# ──────────────────────────────────────────────────────────────────────────────
# Story 4.2 Tests
# ──────────────────────────────────────────────────────────────────────────────


def test_project_creation(db, tracker):
    """Project is inserted with correct defaults."""
    conn = db.get_connection()
    cur = conn.execute("INSERT INTO clients (name, status) VALUES ('Alice', 'won')")
    conn.commit()
    client_id = cur.lastrowid

    pid = tracker.create_project(
        client_id=client_id,
        proposal_id=None,
        name="My Project",
        start_date="2026-01-01",
        end_date="2026-06-30",
        budget=5000.0,
    )
    assert isinstance(pid, int)
    assert pid > 0

    project = tracker.get_project(pid)
    assert project["name"] == "My Project"
    assert project["budget"] == 5000.0
    assert project["status"] == "planning"
    assert project["health_score"] == 100


def test_health_score_perfect(db, tracker, sample_project):
    """A brand-new active project with no issues should score 100."""
    score = tracker.calculate_health_score(sample_project)
    assert score == 100


def test_health_score_degraded(db, tracker, sprint_mgr, sample_project):
    """Overdue in_progress tasks reduce the health score."""
    pid = sample_project

    # Create a sprint
    sid = sprint_mgr.create_sprint(pid, "Sprint 1", start_date="2026-01-01", end_date="2026-01-14")

    # Add tasks that are overdue (due_date in the past) and still in_progress
    past_due = (date.today() - timedelta(days=5)).isoformat()
    for i in range(3):
        tid = sprint_mgr.add_task(sid, f"Overdue Task {i}", due_date=past_due)
        sprint_mgr.update_task_status(tid, "in_progress")

    score = tracker.calculate_health_score(pid)
    # 3 overdue tasks × -10 = -30, plus -15 (no completed activity in 7d) = 55
    assert score < 100
    assert score <= 70  # at least 3 × 10 deducted


def test_health_score_no_activity(db, tracker, sample_project):
    """Project with no activity in 7 days loses 15 points."""
    # No tasks at all = no activity => -15
    score = tracker.calculate_health_score(sample_project)
    assert score == 85  # 100 - 15


# ──────────────────────────────────────────────────────────────────────────────
# Story 4.3 Tests
# ──────────────────────────────────────────────────────────────────────────────


def test_sprint_board_grouping(db, tracker, sprint_mgr, sample_project):
    """Tasks are grouped correctly by status on the Kanban board."""
    pid = sample_project
    sid = sprint_mgr.create_sprint(pid, "Sprint 1")

    # Add tasks with different statuses
    t1 = sprint_mgr.add_task(sid, "Backlog Task")
    t2 = sprint_mgr.add_task(sid, "Todo Task")
    t3 = sprint_mgr.add_task(sid, "In Progress Task")
    t4 = sprint_mgr.add_task(sid, "Review Task")
    t5 = sprint_mgr.add_task(sid, "Done Task")

    sprint_mgr.update_task_status(t2, "todo")
    sprint_mgr.update_task_status(t3, "in_progress")
    sprint_mgr.update_task_status(t4, "review")
    sprint_mgr.update_task_status(t5, "done")

    board = sprint_mgr.get_sprint_board(sid)

    assert len(board["backlog"]) == 1
    assert len(board["todo"]) == 1
    assert len(board["in_progress"]) == 1
    assert len(board["review"]) == 1
    assert len(board["done"]) == 1

    assert board["backlog"][0]["title"] == "Backlog Task"
    assert board["done"][0]["title"] == "Done Task"


def test_velocity_calculation(db, tracker, sprint_mgr, sample_project):
    """Velocity equals sum of story_points for done tasks only."""
    pid = sample_project
    sid = sprint_mgr.create_sprint(pid, "Velocity Sprint")

    # Done tasks (story points: 3 + 5 = 8)
    t1 = sprint_mgr.add_task(sid, "Done A", story_points=3)
    t2 = sprint_mgr.add_task(sid, "Done B", story_points=5)
    sprint_mgr.update_task_status(t1, "done")
    sprint_mgr.update_task_status(t2, "done")

    # Not done (should not count)
    t3 = sprint_mgr.add_task(sid, "In Progress C", story_points=8)
    sprint_mgr.update_task_status(t3, "in_progress")

    velocity = sprint_mgr.get_sprint_velocity(sid)
    assert velocity == 8


def test_complete_sprint_summary(db, tracker, sprint_mgr, sample_project):
    """complete_sprint returns correct counts and marks sprint completed."""
    pid = sample_project
    sid = sprint_mgr.create_sprint(pid, "Finish Sprint")

    t1 = sprint_mgr.add_task(sid, "Task Done", story_points=2)
    t2 = sprint_mgr.add_task(sid, "Task Undone", story_points=3)
    sprint_mgr.update_task_status(t1, "done")
    sprint_mgr.update_task_status(t2, "in_progress")

    summary = sprint_mgr.complete_sprint(sid)

    assert summary["velocity"] == 2
    assert len(summary["completed_tasks"]) == 1
    assert len(summary["incomplete_tasks"]) == 1

    sprint = sprint_mgr.get_sprint(sid)
    assert sprint["status"] == "completed"
