"""
Instagram engagement — auto-reply to comments + scheduled posting.
"""
from __future__ import annotations
import os
import asyncio
import aiohttp
import anthropic
import logging
from datetime import datetime

INSTAGRAM_API_BASE = 'https://graph.facebook.com/v19.0'


class IGEngagementManager:
    def __init__(self):
        self.access_token = os.environ.get('INSTAGRAM_ACCESS_TOKEN', '')
        self.ig_user_id = os.environ.get('INSTAGRAM_ACCOUNT_ID', '')
        self.claude = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY', ''))
        self.logger = logging.getLogger(self.__class__.__name__)

    async def get_comments(self, media_id: str) -> list[dict]:
        """Fetch comments for a post."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'{INSTAGRAM_API_BASE}/{media_id}/comments',
                params={
                    'access_token': self.access_token,
                    'fields': 'id,text,username,timestamp',
                }
            ) as resp:
                data = await resp.json()
                return data.get('data', [])

    async def reply_to_comment(self, media_id: str, comment_id: str, reply_text: str) -> dict:
        """Reply to a specific comment."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{INSTAGRAM_API_BASE}/{media_id}/replies',
                params={
                    'access_token': self.access_token,
                    'message': reply_text[:1000],
                    'comment_id': comment_id,
                }
            ) as resp:
                data = await resp.json()
                return {'reply_id': data.get('id', ''), 'status': 'replied'}

    def generate_reply(self, comment_text: str, post_topic: str, language: str = 'en') -> str:
        """Generate a personalized Claude reply to a comment."""
        prompt = f"""You are Cesar Schneider, founder of Eworks Labs.
Reply to this Instagram comment on a post about '{post_topic}':
Comment: "{comment_text}"

Rules:
- Max 150 characters
- Friendly, genuine, add value
- Language: {'Brazilian Portuguese' if language == 'pt' else 'English'}
- Never generic. Reference the comment specifically.
- No hashtags in replies
Return only the reply text."""
        msg = self.claude.messages.create(
            model='claude-haiku-4-5', max_tokens=100,
            messages=[{'role': 'user', 'content': prompt}]
        )
        return msg.content[0].text.strip()[:150]

    async def auto_reply_to_recent(self, media_id: str, post_topic: str,
                                    language: str = 'en', max_replies: int = 5) -> dict:
        """Auto-reply to recent unanswered comments on a post."""
        comments = await self.get_comments(media_id)
        replied = 0
        for comment in comments[:max_replies]:
            comment_id = comment.get('id')
            comment_text = comment.get('text', '')
            if not comment_text or not comment_id:
                continue
            reply = self.generate_reply(comment_text, post_topic, language)
            await self.reply_to_comment(media_id, comment_id, reply)
            replied += 1
            await asyncio.sleep(3)  # Rate limit
        return {'comments_found': len(comments), 'replies_sent': replied}

    async def post_with_location(self, image_path: str, caption: str,
                                  location_id: str, poster) -> dict:
        """
        Post image with location tag.
        location_id: Facebook Place ID (e.g. '110506755686796' for Sao Paulo)
        poster: InstagramPoster instance
        """
        image_url = await poster.upload_file_to_cdn(image_path)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{INSTAGRAM_API_BASE}/{self.ig_user_id}/media',
                params={
                    'access_token': self.access_token,
                    'image_url': image_url,
                    'caption': caption[:2200],
                    'location_id': location_id,
                }
            ) as resp:
                data = await resp.json()
                container_id = data.get('id')
            await poster._poll_container(session, container_id)
            async with session.post(
                f'{INSTAGRAM_API_BASE}/{self.ig_user_id}/media_publish',
                params={'access_token': self.access_token, 'creation_id': container_id}
            ) as resp:
                data = await resp.json()
                post_id = data.get('id', '')
        return {'post_id': post_id, 'status': 'posted', 'location_id': location_id}
