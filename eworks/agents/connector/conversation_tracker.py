"""
Tracks conversation threads to maintain context and enforce cooldowns.
"""
from __future__ import annotations
import logging
from datetime import datetime, timedelta

COOLDOWN_HOURS = 4   # Don't reply to same user within 4h
MAX_EXCHANGES = 3    # Escalate after 3 exchanges without resolution


class ConversationTracker:
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger(self.__class__.__name__)

    def is_already_seen(self, platform: str, external_id: str) -> bool:
        """Check if this interaction was already processed."""
        with self.db.get_connection() as conn:
            row = conn.execute(
                'SELECT id FROM social_interactions WHERE platform=? AND external_id=?',
                (platform, external_id)
            ).fetchone()
        return row is not None

    def is_in_cooldown(self, platform: str, author_id: str) -> bool:
        """Check if we replied to this user recently (within cooldown window)."""
        cutoff = (datetime.utcnow() - timedelta(hours=COOLDOWN_HOURS)).isoformat()
        with self.db.get_connection() as conn:
            row = conn.execute(
                """SELECT id FROM social_interactions
                WHERE platform=? AND author_id=? AND replied_at > ? AND status='replied'""",
                (platform, author_id, cutoff)
            ).fetchone()
        return row is not None

    def save_interaction(self, interaction: dict, analysis: dict) -> int:
        """Save a new interaction to DB. Returns interaction ID."""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """INSERT OR IGNORE INTO social_interactions
                (platform, interaction_type, external_id, parent_id,
                 author_username, author_id, author_name, content, url,
                 language, sentiment, is_lead, lead_signal, confidence, status, detected_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'pending',?)""",
                (
                    interaction['platform'],
                    interaction['interaction_type'],
                    interaction['external_id'],
                    interaction.get('parent_id', ''),
                    interaction.get('author_username', ''),
                    interaction.get('author_id', ''),
                    interaction.get('author_name', ''),
                    interaction['content'],
                    interaction.get('url', ''),
                    analysis.get('language', 'en'),
                    analysis.get('sentiment', 'unknown'),
                    1 if analysis.get('is_lead') else 0,
                    analysis.get('lead_signal', ''),
                    analysis.get('confidence', 0.0),
                    datetime.utcnow().isoformat(),
                )
            )
            return cursor.lastrowid or 0

    def mark_replied(self, interaction_id: int, reply_text: str, reply_id: str) -> None:
        """Mark interaction as replied."""
        with self.db.get_connection() as conn:
            conn.execute(
                """UPDATE social_interactions
                SET status='replied', reply_text=?, reply_id=?, replied_at=? WHERE id=?""",
                (reply_text, reply_id, datetime.utcnow().isoformat(), interaction_id)
            )

    def mark_escalated(self, interaction_id: int, slack_ts: str, slack_channel: str) -> None:
        """Mark interaction as escalated to Slack."""
        with self.db.get_connection() as conn:
            conn.execute(
                """UPDATE social_interactions
                SET status='escalated', escalated_to_slack=1,
                slack_message_ts=?, slack_channel=?, escalated_at=? WHERE id=?""",
                (slack_ts, slack_channel, datetime.utcnow().isoformat(), interaction_id)
            )

    def mark_ignored(self, interaction_id: int) -> None:
        """Mark interaction as ignored."""
        with self.db.get_connection() as conn:
            conn.execute(
                "UPDATE social_interactions SET status='ignored' WHERE id=?",
                (interaction_id,)
            )

    def get_thread_context(self, platform: str, thread_id: str, author_id: str) -> str:
        """Get recent conversation history for context."""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """SELECT content, reply_text FROM social_interactions
                WHERE platform=? AND parent_id=? AND author_id=?
                ORDER BY detected_at DESC LIMIT 5""",
                (platform, thread_id, author_id)
            ).fetchall()
        if not rows:
            return ''
        parts = []
        for content, reply in reversed(rows):
            parts.append(f'User: {content}')
            if reply:
                parts.append(f'Cesar: {reply}')
        return ' | '.join(parts[-6:])  # Last 3 exchanges

    def get_exchange_count(self, platform: str, thread_id: str, author_id: str) -> int:
        """Count how many times we've interacted with this user in this thread."""
        with self.db.get_connection() as conn:
            row = conn.execute(
                """SELECT COUNT(*) FROM social_interactions
                WHERE platform=? AND parent_id=? AND author_id=? AND status='replied'""",
                (platform, thread_id, author_id)
            ).fetchone()
        return row[0] if row else 0

    def get_pending(self, platform: str = None, limit: int = 50) -> list[dict]:
        """Get all pending (unhandled) interactions."""
        with self.db.get_connection() as conn:
            if platform:
                rows = conn.execute(
                    """SELECT * FROM social_interactions WHERE status='pending' AND platform=?
                    ORDER BY is_lead DESC, detected_at ASC LIMIT ?""",
                    (platform, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM social_interactions WHERE status='pending'
                    ORDER BY is_lead DESC, detected_at ASC LIMIT ?""",
                    (limit,)
                ).fetchall()
        cols = [
            'id', 'platform', 'interaction_type', 'external_id', 'parent_id',
            'author_username', 'author_id', 'author_name', 'content', 'url',
            'language', 'sentiment', 'icp_score', 'status', 'is_lead', 'lead_signal',
            'reply_text', 'reply_id', 'confidence', 'escalated_to_slack',
            'slack_message_ts', 'slack_channel', 'detected_at', 'replied_at', 'escalated_at',
        ]
        return [dict(zip(cols, r)) for r in rows]

    def get_stats(self) -> dict:
        """Return aggregated stats for the status command."""
        with self.db.get_connection() as conn:
            total = conn.execute(
                'SELECT COUNT(*) FROM social_interactions'
            ).fetchone()[0]
            pending = conn.execute(
                "SELECT COUNT(*) FROM social_interactions WHERE status='pending'"
            ).fetchone()[0]
            replied = conn.execute(
                "SELECT COUNT(*) FROM social_interactions WHERE status='replied'"
            ).fetchone()[0]
            escalated = conn.execute(
                "SELECT COUNT(*) FROM social_interactions WHERE status='escalated'"
            ).fetchone()[0]
            leads = conn.execute(
                'SELECT COUNT(*) FROM social_interactions WHERE is_lead=1'
            ).fetchone()[0]
        return {
            'total': total,
            'pending': pending,
            'replied': replied,
            'escalated': escalated,
            'leads': leads,
        }
