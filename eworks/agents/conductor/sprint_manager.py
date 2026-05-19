"""Sprint Manager — Kanban board, velocity tracking, task lifecycle."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from eworks.agents.base import BaseAgent


class SprintManager(BaseAgent):
    """Manages sprints and tasks for projects."""

    async def run(self, campaign_id: int = 0) -> dict:  # type: ignore[override]
        return {"status": "SprintManager ready"}

    # ──────────────────────────────────────────────────────────────────────────
    # Sprint CRUD
    # ──────────────────────────────────────────────────────────────────────────

    def create_sprint(
        self,
        project_id: int,
        name: str,
        goal: str = "",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> int:
        """Create a sprint for a project and return its ID."""
        conn = self.db.get_connection()
        cur = conn.execute(
            """
            INSERT INTO sprints (project_id, name, goal, start_date, end_date, status)
            VALUES (?, ?, ?, ?, ?, 'planning')
            """,
            (project_id, name, goal, start_date, end_date),
        )
        conn.commit()
        sprint_id = cur.lastrowid
        self.logger.info("Created sprint %d: %s (project %d)", sprint_id, name, project_id)
        return sprint_id

    def get_sprint(self, sprint_id: int) -> dict[str, Any] | None:
        """Return a sprint row as dict, or None."""
        conn = self.db.get_connection()
        row = conn.execute("SELECT * FROM sprints WHERE id=?", (sprint_id,)).fetchone()
        return dict(row) if row else None

    # ──────────────────────────────────────────────────────────────────────────
    # Task CRUD
    # ──────────────────────────────────────────────────────────────────────────

    def add_task(
        self,
        sprint_id: int,
        title: str,
        description: str = "",
        priority: str = "medium",
        story_points: int = 1,
        assignee: str = "AI Agent",
        due_date: str | None = None,
    ) -> int:
        """Add a task to a sprint and return its ID."""
        sprint = self.get_sprint(sprint_id)
        if not sprint:
            raise ValueError(f"Sprint {sprint_id} not found")

        conn = self.db.get_connection()
        cur = conn.execute(
            """
            INSERT INTO project_tasks
                (project_id, sprint_id, title, description, priority,
                 story_points, assignee, due_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'backlog')
            """,
            (
                sprint["project_id"], sprint_id, title, description,
                priority, story_points, assignee, due_date,
            ),
        )
        conn.commit()
        task_id = cur.lastrowid
        self.logger.info("Added task %d: %s to sprint %d", task_id, title, sprint_id)
        return task_id

    def update_task_status(self, task_id: int, new_status: str) -> bool:
        """Update task status, set completed_at when done."""
        valid = {"backlog", "todo", "in_progress", "review", "done", "cancelled"}
        if new_status not in valid:
            self.logger.error("Invalid status: %s", new_status)
            return False

        conn = self.db.get_connection()
        try:
            if new_status == "done":
                completed_at = datetime.utcnow().isoformat()
                conn.execute(
                    "UPDATE project_tasks SET status=?, completed_at=? WHERE id=?",
                    (new_status, completed_at, task_id),
                )
            else:
                conn.execute(
                    "UPDATE project_tasks SET status=?, completed_at=NULL WHERE id=?",
                    (new_status, task_id),
                )
            conn.commit()
            return True
        except Exception as exc:
            self.logger.error("update_task_status failed: %s", exc)
            return False

    # ──────────────────────────────────────────────────────────────────────────
    # Sprint Board
    # ──────────────────────────────────────────────────────────────────────────

    def get_sprint_board(self, sprint_id: int) -> dict[str, list[dict]]:
        """Return tasks grouped by status (Kanban board view)."""
        conn = self.db.get_connection()
        rows = conn.execute(
            """
            SELECT * FROM project_tasks
            WHERE sprint_id=? AND status != 'cancelled'
            ORDER BY priority DESC, created_at ASC
            """,
            (sprint_id,),
        ).fetchall()

        board: dict[str, list[dict]] = {
            "backlog": [],
            "todo": [],
            "in_progress": [],
            "review": [],
            "done": [],
        }
        for row in rows:
            task = dict(row)
            status = task["status"]
            if status in board:
                board[status].append(task)

        return board

    # ──────────────────────────────────────────────────────────────────────────
    # Velocity
    # ──────────────────────────────────────────────────────────────────────────

    def get_sprint_velocity(self, sprint_id: int) -> int:
        """Return total story points for completed tasks in this sprint."""
        conn = self.db.get_connection()
        row = conn.execute(
            """
            SELECT COALESCE(SUM(story_points), 0) as total
            FROM project_tasks
            WHERE sprint_id=? AND status='done'
            """,
            (sprint_id,),
        ).fetchone()
        return int(row["total"])

    # ──────────────────────────────────────────────────────────────────────────
    # Complete Sprint
    # ──────────────────────────────────────────────────────────────────────────

    def complete_sprint(self, sprint_id: int) -> dict[str, Any]:
        """
        Mark sprint completed. Returns summary with velocity,
        completed tasks, and any incomplete tasks.
        """
        sprint = self.get_sprint(sprint_id)
        if not sprint:
            return {"error": f"Sprint {sprint_id} not found"}

        conn = self.db.get_connection()

        velocity = self.get_sprint_velocity(sprint_id)

        completed_rows = conn.execute(
            "SELECT * FROM project_tasks WHERE sprint_id=? AND status='done'",
            (sprint_id,),
        ).fetchall()
        completed_tasks = [dict(r) for r in completed_rows]

        incomplete_rows = conn.execute(
            """
            SELECT * FROM project_tasks
            WHERE sprint_id=? AND status NOT IN ('done','cancelled')
            """,
            (sprint_id,),
        ).fetchall()
        incomplete_tasks = [dict(r) for r in incomplete_rows]

        # Mark sprint completed + save velocity
        conn.execute(
            "UPDATE sprints SET status='completed', velocity=? WHERE id=?",
            (velocity, sprint_id),
        )
        conn.commit()

        self.logger.info(
            "Sprint %d completed — velocity=%d, done=%d, incomplete=%d",
            sprint_id, velocity, len(completed_tasks), len(incomplete_tasks),
        )

        return {
            "sprint_id": sprint_id,
            "sprint_name": sprint["name"],
            "velocity": velocity,
            "completed_tasks": completed_tasks,
            "incomplete_tasks": incomplete_tasks,
        }
