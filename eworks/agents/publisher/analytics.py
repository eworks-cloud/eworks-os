"""
Analytics collector for LinkedIn and Instagram posts.
Fetches metrics and saves to social_analytics table.
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime
from eworks.agents.publisher.linkedin_poster import LinkedInPoster
from eworks.agents.publisher.social_poster import InstagramPoster


class AnalyticsCollector:
    """Collects and stores analytics for LinkedIn and Instagram posts."""

    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger(self.__class__.__name__)
        self.linkedin = LinkedInPoster()
        self.instagram = InstagramPoster()

    def collect_linkedin(self, post_id: int, post_urn: str) -> dict:
        """Fetch LinkedIn analytics and save to DB."""
        analytics = self.linkedin.get_post_analytics(post_urn)
        if analytics.get("status") == "ok":
            with self.db.get_connection() as conn:
                conn.execute(
                    """INSERT INTO social_analytics
                    (post_id, platform, impressions, likes, comments, shares, fetched_at)
                    VALUES (?, 'linkedin', ?, ?, ?, ?, ?)""",
                    (post_id, analytics.get("impressions", 0),
                     analytics.get("likes", 0), analytics.get("comments", 0),
                     analytics.get("shares", 0), datetime.utcnow().isoformat())
                )
        return analytics

    async def collect_instagram(self, post_id: int, ig_post_id: str) -> dict:
        """Fetch Instagram analytics and save to DB."""
        analytics = await self.instagram.get_post_analytics(ig_post_id)
        if analytics.get("status") == "ok":
            with self.db.get_connection() as conn:
                conn.execute(
                    """INSERT INTO social_analytics
                    (post_id, platform, impressions, reach, likes, comments, shares, fetched_at)
                    VALUES (?, 'instagram', ?, ?, ?, ?, ?, ?)""",
                    (post_id, analytics.get("impressions", 0), analytics.get("reach", 0),
                     analytics.get("likes", 0), analytics.get("comments", 0),
                     analytics.get("shares", 0), datetime.utcnow().isoformat())
                )
        return analytics

    def get_summary(self) -> dict:
        """Get analytics summary across all posts."""
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """SELECT platform,
                   SUM(impressions) as total_impressions,
                   SUM(likes) as total_likes,
                   SUM(comments) as total_comments,
                   SUM(shares) as total_shares,
                   COUNT(DISTINCT post_id) as posts_tracked
                   FROM social_analytics
                   GROUP BY platform"""
            ).fetchall()
        return {
            row[0]: {
                "total_impressions": row[1] or 0,
                "total_likes": row[2] or 0,
                "total_comments": row[3] or 0,
                "total_shares": row[4] or 0,
                "posts_tracked": row[5] or 0,
            } for row in rows
        }
