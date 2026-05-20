"""
Instagram comment and mention listener.
"""
from __future__ import annotations
import os
import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta

IG_API = 'https://graph.facebook.com/v19.0'


class InstagramListener:
    def __init__(self):
        self.access_token = os.environ.get('INSTAGRAM_ACCESS_TOKEN', '')
        self.ig_user_id = os.environ.get('INSTAGRAM_ACCOUNT_ID', '')
        self.logger = logging.getLogger(self.__class__.__name__)

    async def get_recent_media(self, limit: int = 10) -> list[dict]:
        """Get recent posts/reels to check for new comments."""
        if not self.access_token:
            return []
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'{IG_API}/{self.ig_user_id}/media',
                params={
                    'access_token': self.access_token,
                    'fields': 'id,caption,media_type,timestamp,permalink',
                    'limit': limit,
                }
            ) as resp:
                data = await resp.json()
                return data.get('data', [])

    async def get_comments(self, media_id: str, since_minutes: int = 60) -> list[dict]:
        """Get new comments on a post since N minutes ago."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'{IG_API}/{media_id}/comments',
                params={
                    'access_token': self.access_token,
                    'fields': 'id,text,username,timestamp',
                }
            ) as resp:
                data = await resp.json()
                comments = data.get('data', [])
                # Filter recent
                cutoff = datetime.utcnow() - timedelta(minutes=since_minutes)
                recent = []
                for c in comments:
                    try:
                        ts = datetime.fromisoformat(c['timestamp'].replace('Z', '+00:00'))
                        if ts.replace(tzinfo=None) > cutoff:
                            recent.append(c)
                    except Exception:
                        recent.append(c)
                return recent

    async def reply_to_comment(self, media_id: str, comment_id: str, text: str) -> dict:
        """Post a reply to a comment."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{IG_API}/{media_id}/replies',
                params={
                    'access_token': self.access_token,
                    'message': text[:1000],
                    'comment_id': comment_id,
                }
            ) as resp:
                data = await resp.json()
                return {'reply_id': data.get('id', ''), 'status': 'replied'}

    async def scan(self, since_minutes: int = 60) -> list[dict]:
        """Full scan: get all recent comments across recent posts."""
        if not self.access_token or not self.ig_user_id:
            self.logger.warning('Instagram not configured')
            return []
        media_list = await self.get_recent_media(limit=10)
        interactions = []
        for media in media_list:
            media_id = media['id']
            permalink = media.get('permalink', '')
            try:
                comments = await self.get_comments(media_id, since_minutes)
            except Exception as e:
                self.logger.error('Failed to get comments for %s: %s', media_id, e)
                continue
            for comment in comments:
                interactions.append({
                    'platform': 'instagram',
                    'interaction_type': 'comment',
                    'external_id': comment['id'],
                    'parent_id': media_id,
                    'author_username': comment.get('username', ''),
                    'author_id': comment.get('username', ''),
                    'author_name': comment.get('username', ''),
                    'content': comment.get('text', ''),
                    'url': permalink,
                    'raw': comment,
                })
            await asyncio.sleep(0.5)  # Rate limit
        return interactions
