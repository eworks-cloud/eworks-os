"""Project Tracker — creates and monitors client projects."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from eworks.agents.base import BaseAgent
from eworks.core.phoenix_instrumentation import trace_workflow_step


class ProjectTracker(BaseAgent):
    """Tracks client projects, calculates health scores, logs hours."""

    # ProjectTracker doesn't need campaign_id in run(); override signature.
    async def run(self, campaign_id: int = 0) -> dict:  # type: ignore[override]
        """Run a health check across all active projects."""
        projects = self.get_all_active_projects()
        for p in projects:
            self.calculate_health_score(p["id"])
        return {"projects_checked": len(projects)}

    # ──────────────────────────────────────────────────────────────────────────
    # Project CRUD
    # ──────────────────────────────────────────────────────────────────────────

    @trace_workflow_step("create_project")
    def create_project(
        self,
        client_id: int,
        proposal_id: int | None,
        name: str,
        start_date: str,
        end_date: str,
        budget: float,
        description: str = "",
        hourly_rate: float = 150.0,
    ) -> int:
        """Insert a new project and return its ID."""
        conn = self.db.get_connection()
        cur = conn.execute(
            """
            INSERT INTO projects
                (client_id, proposal_id, name, description, status,
                 start_date, end_date, budget, hourly_rate)
            VALUES (?, ?, ?, ?, 'planning', ?, ?, ?, ?)
            """,
            (client_id, proposal_id, name, description,
             start_date, end_date, budget, hourly_rate),
        )
        conn.commit()
        project_id = cur.lastrowid
        self.logger.info("Created project %d: %s", project_id, name)
        return project_id

    def get_project(self, project_id: int) -> dict[str, Any] | None:
        """Return raw project row as dict, or None."""
        conn = self.db.get_connection()
        row = conn.execute(
            "SELECT * FROM projects WHERE id=?", (project_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_active_projects(self) -> list[dict[str, Any]]:
        """Return all projects with status='active'."""
        conn = self.db.get_connection()
        rows = conn.execute(
            "SELECT * FROM projects WHERE status='active' ORDER BY created_at"
        ).fetchall()
        return [dict(r) for r in rows]

    # ──────────────────────────────────────────────────────────────────────────
    # Health Score
    # ──────────────────────────────────────────────────────────────────────────

    @trace_workflow_step("calculate_health_score")
    def calculate_health_score(self, project_id: int) -> int:
        """
        Compute 0-100 health score for a project and persist it.

        Deductions:
          -10 per overdue task still in_progress / todo / review
          -20 if budget is overrun
          -15 if no task activity in last 7 days
        """
        project = self.get_project(project_id)
        if not project:
            return 0

        score = 100
        conn = self.db.get_connection()
        today = date.today().isoformat()

        # Overdue tasks (due_date < today AND not done/cancelled)
        overdue = conn.execute(
            """
            SELECT COUNT(*) as cnt FROM project_tasks
            WHERE project_id=?
              AND due_date IS NOT NULL
              AND due_date < ?
              AND status NOT IN ('done','cancelled')
            """,
            (project_id, today),
        ).fetchone()["cnt"]
        score -= overdue * 10

        # Budget overrun
        budget = project.get("budget") or 0
        hours_logged = project.get("hours_logged") or 0
        hourly_rate = project.get("hourly_rate") or 150
        cost = hours_logged * hourly_rate
        if budget > 0 and cost > budget:
            score -= 20

        # No activity in 7 days (only penalise if project has tasks and is older than 7 days)
        seven_days_ago = (date.today() - timedelta(days=7)).isoformat()
        task_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM project_tasks WHERE project_id=?",
            (project_id,),
        ).fetchone()["cnt"]
        project_created = str(project.get("created_at", ""))[:10]
        try:
            project_age_days = (date.today() - date.fromisoformat(project_created)).days
        except (ValueError, TypeError):
            project_age_days = 0

        if task_count > 0 and project_age_days >= 7:
            recent = conn.execute(
                """
                SELECT COUNT(*) as cnt FROM project_tasks
                WHERE project_id=?
                  AND (
                        (completed_at IS NOT NULL AND completed_at >= ?)
                     OR (status='in_progress')
                  )
                """,
                (project_id, seven_days_ago),
            ).fetchone()["cnt"]
            if recent == 0:
                score -= 15

        score = max(0, min(100, score))

        # Persist
        conn.execute(
            "UPDATE projects SET health_score=? WHERE id=?",
            (score, project_id),
        )
        conn.commit()
        return score

    # ──────────────────────────────────────────────────────────────────────────
    # Project Summary
    # ──────────────────────────────────────────────────────────────────────────

    def get_project_summary(self, project_id: int) -> dict[str, Any]:
        """Return a rich summary dict for a project."""
        project = self.get_project(project_id)
        if not project:
            return {}

        conn = self.db.get_connection()

        tasks_total = conn.execute(
            "SELECT COUNT(*) as cnt FROM project_tasks WHERE project_id=?",
            (project_id,),
        ).fetchone()["cnt"]

        tasks_done = conn.execute(
            "SELECT COUNT(*) as cnt FROM project_tasks WHERE project_id=? AND status='done'",
            (project_id,),
        ).fetchone()["cnt"]

        tasks_in_progress = conn.execute(
            "SELECT COUNT(*) as cnt FROM project_tasks WHERE project_id=? AND status='in_progress'",
            (project_id,),
        ).fetchone()["cnt"]

        budget = project.get("budget") or 0
        hourly_rate = project.get("hourly_rate") or 150
        hours_logged = project.get("hours_logged") or 0
        cost = hours_logged * hourly_rate
        budget_remaining = budget - cost

        # Days remaining
        days_remaining: int | None = None
        if project.get("end_date"):
            try:
                end = date.fromisoformat(str(project["end_date"]))
                days_remaining = (end - date.today()).days
            except ValueError:
                pass

        health_score = self.calculate_health_score(project_id)

        return {
            "id": project_id,
            "name": project["name"],
            "status": project["status"],
            "health_score": health_score,
            "tasks_total": tasks_total,
            "tasks_done": tasks_done,
            "tasks_in_progress": tasks_in_progress,
            "hours_logged": hours_logged,
            "budget": budget,
            "budget_remaining": round(budget_remaining, 2),
            "days_remaining": days_remaining,
            "start_date": project.get("start_date"),
            "end_date": project.get("end_date"),
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Hour Logging
    # ──────────────────────────────────────────────────────────────────────────

    def log_hours(
        self,
        project_id: int,
        task_id: int | None,
        hours: float,
        description: str = "",
    ) -> bool:
        """Add hours to the project (and optionally to the task)."""
        conn = self.db.get_connection()
        try:
            conn.execute(
                "UPDATE projects SET hours_logged = hours_logged + ? WHERE id=?",
                (hours, project_id),
            )
            if task_id:
                conn.execute(
                    "UPDATE project_tasks SET hours_logged = hours_logged + ? WHERE id=? AND project_id=?",
                    (hours, task_id, project_id),
                )
            conn.commit()
            self.logger.info(
                "Logged %.2f hours to project %d (task %s): %s",
                hours, project_id, task_id, description,
            )
            return True
        except Exception as exc:
            self.logger.error("log_hours failed: %s", exc)
            return False
