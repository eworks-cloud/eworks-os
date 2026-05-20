"""Conductor Orchestrator — daily health checks + weekly report generation."""
from __future__ import annotations

import logging
from typing import Any

from eworks.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class ConductorOrchestrator(BaseAgent):
    """Orchestrates daily checks and weekly report runs across all active projects."""

    async def run(self, campaign_id: int = 0) -> dict:  # type: ignore[override]
        return await self.run_daily_check()

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _get_tracker(self):
        from eworks.agents.conductor.tracker import ProjectTracker
        return ProjectTracker(db=self.db, config=self.config)

    def _get_reporter(self):
        from eworks.agents.conductor.status_reporter import StatusReporter
        return StatusReporter(db=self.db, config=self.config)

    # ──────────────────────────────────────────────────────────────────────────
    # Daily Check
    # ──────────────────────────────────────────────────────────────────────────

    async def run_daily_check(self) -> dict[str, Any]:
        """
        For every active project:
          1. Recalculate health score
          2. Check for blockers
          3. Alert if at risk (health < 60)

        Returns {projects_checked, alerts_sent, at_risk_count}
        """
        tracker = self._get_tracker()
        reporter = self._get_reporter()

        projects = tracker.get_all_active_projects()
        alerts_sent = 0
        at_risk_count = 0

        for project in projects:
            pid = project["id"]

            # 1. Recalculate health
            health = tracker.calculate_health_score(pid)
            logger.info("Project %d (%s) health=%d", pid, project["name"], health)

            # 2. Blockers
            blockers = await reporter.check_blockers(pid)
            if blockers:
                logger.warning("Project %d has %d blocker(s): %s", pid, len(blockers), blockers)

            # 3. Alert if at risk
            if health < 60:
                at_risk_count += 1
                sent = await reporter.alert_if_at_risk(pid)
                if sent:
                    alerts_sent += 1

        return {
            "projects_checked": len(projects),
            "alerts_sent": alerts_sent,
            "at_risk_count": at_risk_count,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Weekly Reports
    # ──────────────────────────────────────────────────────────────────────────

    async def run_weekly_reports(self) -> dict[str, Any]:
        """
        For every active project:
          1. Generate weekly report via Claude
          2. Send to client via Telegram

        Returns {projects_reported, updates_sent}
        """
        tracker = self._get_tracker()
        reporter = self._get_reporter()

        projects = tracker.get_all_active_projects()
        updates_sent = 0
        reports_generated = 0
        conn = self.db.get_connection()

        for project in projects:
            pid = project["id"]
            try:
                # Generate report (also saves to project_updates)
                await reporter.generate_weekly_report(pid)
                reports_generated += 1

                # Find the update we just saved (latest for this project)
                row = conn.execute(
                    """
                    SELECT id FROM project_updates
                    WHERE project_id=? AND update_type='weekly_report' AND sent_to_client=0
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (pid,),
                ).fetchone()

                if row:
                    sent = await reporter.send_update_to_client(row["id"])
                    if sent:
                        updates_sent += 1

            except Exception as exc:
                logger.error("Weekly report failed for project %d: %s", pid, exc)

        return {
            "projects_reported": reports_generated,
            "updates_sent": updates_sent,
        }
