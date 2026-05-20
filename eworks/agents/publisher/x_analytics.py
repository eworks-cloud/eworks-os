"""
X.com analytics collector — fetches tweet metrics and saves to DB.
"""
from __future__ import annotations
import logging
from datetime import datetime
from eworks.agents.publisher.x_poster import XPoster


class XAnalyticsCollector:
    def __init__(self, db):
        self.db = db
        self.poster = XPoster()
        self.logger = logging.getLogger(self.__class__.__name__)

    def collect(self, x_post_id: int, tweet_id: str) -> dict:
        """Fetch analytics for a tweet and save to DB."""
        analytics = self.poster.get_tweet_analytics(tweet_id)
        if analytics.get('status') == 'ok':
            total = (
                analytics.get('likes', 0)
                + analytics.get('retweets', 0)
                + analytics.get('replies', 0)
                + analytics.get('quotes', 0)
            )
            impressions = analytics.get('impressions', 0)
            engagement_rate = (total / impressions * 100) if impressions > 0 else 0.0
            with self.db.get_connection() as conn:
                conn.execute(
                    """INSERT INTO x_analytics
                    (x_post_id, tweet_id, impressions, likes, retweets,
                     replies, quotes, bookmarks, engagement_rate, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        x_post_id, tweet_id,
                        impressions,
                        analytics.get('likes', 0),
                        analytics.get('retweets', 0),
                        analytics.get('replies', 0),
                        analytics.get('quotes', 0),
                        analytics.get('bookmarks', 0),
                        round(engagement_rate, 4),
                        datetime.utcnow().isoformat(),
                    ),
                )
        return analytics

    def get_summary(self) -> dict:
        """Aggregate X analytics across all posts."""
        with self.db.get_connection() as conn:
            row = conn.execute(
                """SELECT
                   COUNT(DISTINCT x_post_id) as posts_tracked,
                   SUM(impressions) as total_impressions,
                   SUM(likes) as total_likes,
                   SUM(retweets) as total_retweets,
                   SUM(replies) as total_replies,
                   AVG(engagement_rate) as avg_engagement_rate
                   FROM x_analytics"""
            ).fetchone()
        if not row or row[0] is None:
            return {
                'posts_tracked': 0,
                'total_impressions': 0,
                'total_likes': 0,
                'total_retweets': 0,
                'total_replies': 0,
                'avg_engagement_rate': 0.0,
            }
        return {
            'posts_tracked': row[0] or 0,
            'total_impressions': row[1] or 0,
            'total_likes': row[2] or 0,
            'total_retweets': row[3] or 0,
            'total_replies': row[4] or 0,
            'avg_engagement_rate': round(row[5] or 0.0, 2),
        }

    def get_top_posts(self, limit: int = 5) -> list[dict]:
        """Get top performing posts by engagement."""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """SELECT xa.tweet_id, xp.text_content, xa.impressions,
                   xa.likes, xa.retweets, xa.engagement_rate
                   FROM x_analytics xa
                   JOIN x_posts xp ON xp.id = xa.x_post_id
                   ORDER BY xa.engagement_rate DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        return [
            {
                'tweet_id': r[0],
                'text': r[1][:80],
                'impressions': r[2],
                'likes': r[3],
                'retweets': r[4],
                'engagement_rate': r[5],
            }
            for r in rows
        ]
