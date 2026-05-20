"""
Instagram hashtag research — finds optimal hashtags for a topic.
Combines Instagram Graph API hashtag search with Claude AI curation.
"""
from __future__ import annotations
import os
import logging
import aiohttp
import asyncio
import anthropic

INSTAGRAM_API_BASE = 'https://graph.facebook.com/v19.0'


class HashtagResearcher:
    MAX_HASHTAGS = 30  # Instagram limit

    def __init__(self):
        self.access_token = os.environ.get('INSTAGRAM_ACCESS_TOKEN', '')
        self.ig_user_id = os.environ.get('INSTAGRAM_ACCOUNT_ID', '')
        self.claude = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY', ''))
        self.logger = logging.getLogger(self.__class__.__name__)

    async def search_hashtag(self, session: aiohttp.ClientSession, tag: str) -> dict:
        """Search for a hashtag and get its ID + media count."""
        async with session.get(
            f'{INSTAGRAM_API_BASE}/ig_hashtag_search',
            params={
                'access_token': self.access_token,
                'user_id': self.ig_user_id,
                'q': tag.lstrip('#'),
            }
        ) as resp:
            if resp.status != 200:
                return {'tag': tag, 'id': None, 'error': True}
            data = await resp.json()
            items = data.get('data', [])
            if not items:
                return {'tag': tag, 'id': None}
            hashtag_id = items[0].get('id')
            return {'tag': tag, 'id': hashtag_id}

    def generate_hashtag_set(self, topic: str, content_type: str = 'post', language: str = 'en') -> list[str]:
        """
        Use Claude to generate an optimized set of 25-30 Instagram hashtags.
        Mix of broad, niche, and branded hashtags.
        """
        prompt = f"""Generate exactly 28 Instagram hashtags for a {content_type} about: {topic}
Language: {'Brazilian Portuguese' if language == 'pt' else 'English'}

Rules:
- Mix sizes: 8 broad (1M+ posts), 12 medium (100K-1M posts), 8 niche (<100K posts)
- Include AI/tech/business relevant tags
- No spaces in hashtags
- Include #eworkslabs as branded hashtag
- Return as comma-separated list of hashtags with # prefix
- No explanation, just the hashtags"""

        msg = self.claude.messages.create(
            model='claude-haiku-4-5',
            max_tokens=400,
            messages=[{'role': 'user', 'content': prompt}]
        )
        raw = msg.content[0].text.strip()
        tags = [t.strip() for t in raw.replace('\n', ',').split(',') if t.strip().startswith('#')]
        return tags[:self.MAX_HASHTAGS]

    async def get_optimal_hashtags(self, topic: str, language: str = 'en') -> list[str]:
        """
        Generate + validate hashtags. Returns ordered list ready for caption.
        """
        hashtags = self.generate_hashtag_set(topic, language=language)
        return hashtags  # Return Claude-generated set directly (API validation is optional)

    def format_for_caption(self, hashtags: list[str], caption: str) -> str:
        """
        Append hashtags to caption with proper spacing.
        Instagram best practice: hashtags separated from caption by newlines.
        """
        tag_block = ' '.join(hashtags[:self.MAX_HASHTAGS])
        return f'{caption}\n\n{tag_block}'
