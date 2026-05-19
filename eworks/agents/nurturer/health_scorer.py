"""Health Scorer — 4-component 100-point client health scoring system."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from eworks.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class HealthScorer(BaseAgent):
    """Calculates and records client health scores (0-100)."""

    async def run(self, campaign_id: int) -> dict:
        """Not used directly."""
        return {"status": "health_scorer"}

    # ── Score calculation ────────────────────────────────────────────────────

    def calculate_health(self, client_id: int) -> int:
        """
        Calculate a 0-100 health score for the given client.

        Components (25 pts each):
          1. payment_score   — invoice payment history
          2. engagement_score — check-in response recency
          3. project_health_score — average active project health
          4. satisfaction_score — last NPS score
        """
        conn = self.db.get_connection()

        # 1. Payment score — check overdue invoices (using invoices table if available)
        payment_score = self._calc_payment_score(conn, client_id)

        # 2. Engagement score — last responded check-in
        engagement_score = self._calc_engagement_score(conn, client_id)

        # 3. Project health score — average of active projects
        project_health_score = self._calc_project_health_score(conn, client_id)

        # 4. Satisfaction score — last NPS
        satisfaction_score = self._calc_satisfaction_score(conn, client_id)

        total = payment_score + engagement_score + project_health_score + satisfaction_score
        # Clamp to 0-100
        total = max(0, min(100, total))

        self.logger.debug(
            "Health for client %d: payment=%d engagement=%d project=%d satisfaction=%d total=%d",
            client_id, payment_score, engagement_score, project_health_score, satisfaction_score, total,
        )
        return total

    def _calc_payment_score(self, conn, client_id: int) -> int:
        """25=all on time, 15=1 overdue, 5=2+ overdue."""
        try:
            rows = conn.execute(
                """
                SELECT status FROM invoices
                 WHERE client_id=? AND status IN ('overdue','unpaid')
                """,
                (client_id,),
            ).fetchall()
            overdue_count = len(rows)
        except Exception:
            # invoices table may not exist yet
            overdue_count = 0

        if overdue_count == 0:
            return 25
        elif overdue_count == 1:
            return 15
        else:
            return 5

    def _calc_engagement_score(self, conn, client_id: int) -> int:
        """25=responded in last 30d, 15=within 60d, 5=90d+."""
        try:
            row = conn.execute(
                """
                SELECT responded_at FROM client_checkins
                 WHERE client_id=? AND responded_at IS NOT NULL
                 ORDER BY responded_at DESC LIMIT 1
                """,
                (client_id,),
            ).fetchone()
        except Exception:
            row = None

        if not row or not row["responded_at"]:
            return 5  # No engagement data

        try:
            last_response = datetime.fromisoformat(row["responded_at"])
            if last_response.tzinfo is None:
                last_response = last_response.replace(tzinfo=timezone.utc)
            days_ago = (datetime.now(timezone.utc) - last_response).days
        except (ValueError, TypeError):
            return 5

        if days_ago <= 30:
            return 25
        elif days_ago <= 60:
            return 15
        else:
            return 5

    def _calc_project_health_score(self, conn, client_id: int) -> int:
        """Average of active project health_scores, scaled to 25 pts."""
        try:
            rows = conn.execute(
                """
                SELECT health_score FROM projects
                 WHERE client_id=? AND status='active' AND health_score IS NOT NULL
                """,
                (client_id,),
            ).fetchall()
        except Exception:
            rows = []

        if not rows:
            return 15  # Neutral if no project data

        avg = sum(r["health_score"] for r in rows) / len(rows)
        # Scale from 0-100 project score to 0-25 component
        return max(0, min(25, round(avg * 25 / 100)))

    def _calc_satisfaction_score(self, conn, client_id: int) -> int:
        """25=NPS>=8, 15=6-7 or no score, 5=NPS<6."""
        try:
            row = conn.execute(
                """
                SELECT nps_score FROM client_checkins
                 WHERE client_id=? AND nps_score IS NOT NULL
                 ORDER BY sent_at DESC LIMIT 1
                """,
                (client_id,),
            ).fetchone()
        except Exception:
            row = None

        if not row or row["nps_score"] is None:
            return 15  # Neutral

        nps = row["nps_score"]
        if nps >= 8:
            return 25
        elif nps >= 6:
            return 15
        else:
            return 5

    # ── Persistence ──────────────────────────────────────────────────────────

    def record_health_score(self, client_id: int) -> int:
        """Calculate health, save to DB, and return the score."""
        conn = self.db.get_connection()

        payment_score = self._calc_payment_score(conn, client_id)
        engagement_score = self._calc_engagement_score(conn, client_id)
        project_health_score = self._calc_project_health_score(conn, client_id)
        satisfaction_score = self._calc_satisfaction_score(conn, client_id)

        total = max(0, min(100, payment_score + engagement_score + project_health_score + satisfaction_score))
        now = datetime.now(timezone.utc).isoformat()

        conn.execute(
            """
            INSERT INTO client_health_scores
                (client_id, score, payment_score, engagement_score, project_health_score,
                 satisfaction_score, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (client_id, total, payment_score, engagement_score, project_health_score, satisfaction_score, now),
        )
        conn.commit()
        self.logger.info("Recorded health score %d for client %d", total, client_id)
        return total

    # ── Trends & risk ────────────────────────────────────────────────────────

    def get_health_trend(self, client_id: int, last_n: int = 5) -> list[dict[str, Any]]:
        """Return the last N health score records for a client."""
        conn = self.db.get_connection()
        rows = conn.execute(
            """
            SELECT score, payment_score, engagement_score, project_health_score,
                   satisfaction_score, notes, recorded_at
              FROM client_health_scores
             WHERE client_id=?
             ORDER BY recorded_at DESC
             LIMIT ?
            """,
            (client_id, last_n),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_at_risk_clients(self) -> list[dict[str, Any]]:
        """Return clients whose most recent health score is below 60."""
        conn = self.db.get_connection()
        rows = conn.execute(
            """
            SELECT chs.client_id, chs.score, chs.recorded_at,
                   c.name as client_name, c.company
              FROM client_health_scores chs
              JOIN clients c ON c.id = chs.client_id
             WHERE chs.id IN (
                   SELECT MAX(id) FROM client_health_scores GROUP BY client_id
             )
               AND chs.score < 60
             ORDER BY chs.score ASC
            """,
        ).fetchall()
        return [dict(r) for r in rows]
