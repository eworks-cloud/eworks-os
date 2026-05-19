"""Task queue utilities — wraps the task_queue table in the database."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class TaskQueue:
    """Simple persistent task queue backed by SQLite."""

    def __init__(self, db):
        self.db = db

    def enqueue(
        self,
        task_type: str,
        payload: dict[str, Any] | None = None,
        priority: int = 5,
    ) -> int:
        """Add a task to the queue and return its ID."""
        conn = self.db.get_connection()
        cur = conn.execute(
            """
            INSERT INTO task_queue (task_type, payload, priority)
            VALUES (?, ?, ?)
            """,
            (task_type, json.dumps(payload or {}), priority),
        )
        conn.commit()
        task_id = cur.lastrowid
        logger.debug("Enqueued task %s id=%d", task_type, task_id)
        return task_id

    def dequeue(self) -> dict[str, Any] | None:
        """Fetch and claim the next pending task."""
        conn = self.db.get_connection()
        row = conn.execute(
            """
            SELECT id, task_type, payload, priority, attempts, max_attempts
            FROM task_queue
            WHERE status = 'pending' AND attempts < max_attempts
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
            """,
        ).fetchone()
        if not row:
            return None
        task = dict(row)
        conn.execute(
            "UPDATE task_queue SET status='running', started_at=?, attempts=attempts+1 WHERE id=?",
            (datetime.utcnow().isoformat(), task["id"]),
        )
        conn.commit()
        task["payload"] = json.loads(task.get("payload") or "{}")
        return task

    def complete(self, task_id: int) -> None:
        """Mark a task as done."""
        conn = self.db.get_connection()
        conn.execute(
            "UPDATE task_queue SET status='done', completed_at=? WHERE id=?",
            (datetime.utcnow().isoformat(), task_id),
        )
        conn.commit()

    def fail(self, task_id: int, error: str) -> None:
        """Mark a task as failed with an error message."""
        conn = self.db.get_connection()
        conn.execute(
            "UPDATE task_queue SET status='failed', completed_at=?, error_message=? WHERE id=?",
            (datetime.utcnow().isoformat(), error, task_id),
        )
        conn.commit()
