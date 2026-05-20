"""
LinkedIn post comment listener.
"""
from __future__ import annotations
import os
import requests
import logging

LI_API = 'https://api.linkedin.com/v2'


class LinkedInListener:
    def __init__(self):
        self.access_token = os.environ.get('LINKEDIN_ACCESS_TOKEN', '')
        self.person_urn = os.environ.get('LINKEDIN_PERSON_URN', '')
        self.logger = logging.getLogger(self.__class__.__name__)

    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self.access_token}',
            'X-Restli-Protocol-Version': '2.0.0',
        }

    def get_recent_posts(self, count: int = 10) -> list[dict]:
        """Get recent UGC posts by the authenticated user."""
        if not self.access_token or not self.person_urn:
            return []
        try:
            resp = requests.get(
                f'{LI_API}/ugcPosts',
                headers=self._headers(),
                params={
                    'q': 'authors',
                    'authors': f'List({self.person_urn})',
                    'count': count,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get('elements', [])
        except Exception as e:
            self.logger.error('LinkedIn posts fetch failed: %s', e)
            return []

    def get_comments(self, post_urn: str) -> list[dict]:
        """Get comments on a LinkedIn post."""
        try:
            encoded = requests.utils.quote(post_urn, safe='')
            resp = requests.get(
                f'{LI_API}/socialActions/{encoded}/comments',
                headers=self._headers(),
                params={'count': 50},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get('elements', [])
        except Exception as e:
            self.logger.error('LinkedIn comments fetch failed: %s', e)
            return []

    def reply_to_comment(self, post_urn: str, comment_urn: str, text: str) -> dict:
        """Reply to a LinkedIn comment."""
        try:
            encoded_post = requests.utils.quote(post_urn, safe='')
            payload = {
                'actor': self.person_urn,
                'message': {'text': text[:1250]},
                'parentComment': comment_urn,
            }
            resp = requests.post(
                f'{LI_API}/socialActions/{encoded_post}/comments',
                headers={**self._headers(), 'Content-Type': 'application/json'},
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            return {'reply_id': resp.headers.get('x-restli-id', ''), 'status': 'replied'}
        except Exception as e:
            self.logger.error('LinkedIn reply failed: %s', e)
            return {'status': 'error', 'error': str(e)}

    def scan(self) -> list[dict]:
        """Full scan: get all recent comments on recent posts."""
        if not self.access_token:
            return []
        posts = self.get_recent_posts(count=5)
        interactions = []
        for post in posts:
            post_urn = post.get('id', '')
            if not post_urn:
                continue
            post_url = f'https://www.linkedin.com/feed/update/{post_urn}/'
            comments = self.get_comments(post_urn)
            for comment in comments:
                actor = comment.get('actor', '')
                if actor == self.person_urn:
                    continue  # Skip own comments
                message = comment.get('message', {}).get('text', '')
                comment_urn = comment.get('id', '')
                interactions.append({
                    'platform': 'linkedin',
                    'interaction_type': 'comment',
                    'external_id': comment_urn,
                    'parent_id': post_urn,
                    'author_id': actor,
                    'author_username': actor,
                    'author_name': actor,
                    'content': message,
                    'url': post_url,
                })
        return interactions
