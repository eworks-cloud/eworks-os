"""
X.com (Twitter) mention and reply listener.
"""
from __future__ import annotations
import os
import logging


class XListener:
    def __init__(self):
        self.bearer_token = os.environ.get('X_BEARER_TOKEN', '')
        self.api_key = os.environ.get('X_API_KEY', '')
        self.api_secret = os.environ.get('X_API_SECRET', '')
        self.access_token = os.environ.get('X_ACCESS_TOKEN', '')
        self.access_token_secret = os.environ.get('X_ACCESS_TOKEN_SECRET', '')
        self.logger = logging.getLogger(self.__class__.__name__)
        self._client = None

    def _get_client(self):
        if self._client:
            return self._client
        try:
            import tweepy
            self._client = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                wait_on_rate_limit=True,
            )
            return self._client
        except ImportError:
            self.logger.error('tweepy not installed')
            return None

    def get_mentions(self, user_id: str = None, since_id: str = None) -> list[dict]:
        """Get recent mentions of the authenticated user."""
        if not self.bearer_token:
            return []
        client = self._get_client()
        if not client:
            return []
        try:
            # Get authenticated user ID
            if not user_id:
                me = client.get_me()
                user_id = str(me.data.id) if me.data else None
            if not user_id:
                return []
            kwargs = {
                'id': user_id,
                'tweet_fields': ['author_id', 'created_at', 'conversation_id', 'text'],
                'expansions': ['author_id'],
                'user_fields': ['username', 'name'],
                'max_results': 20,
            }
            if since_id:
                kwargs['since_id'] = since_id
            resp = client.get_users_mentions(**kwargs)
            if not resp.data:
                return []
            # Build user map
            users = {}
            if resp.includes and resp.includes.get('users'):
                for u in resp.includes['users']:
                    users[str(u.id)] = {'username': u.username, 'name': u.name}
            interactions = []
            for tweet in resp.data:
                author = users.get(str(tweet.author_id), {})
                interactions.append({
                    'platform': 'x',
                    'interaction_type': 'mention',
                    'external_id': str(tweet.id),
                    'parent_id': str(tweet.conversation_id) if tweet.conversation_id else str(tweet.id),
                    'author_id': str(tweet.author_id),
                    'author_username': author.get('username', ''),
                    'author_name': author.get('name', ''),
                    'content': tweet.text,
                    'url': f'https://x.com/i/web/status/{tweet.id}',
                })
            return interactions
        except Exception as e:
            self.logger.error('X mention scan failed: %s', e)
            return []

    def reply_to_tweet(self, tweet_id: str, text: str) -> dict:
        """Reply to a tweet."""
        if not self.api_key:
            return {'status': 'needs_auth'}
        client = self._get_client()
        if not client:
            return {'status': 'error'}
        try:
            resp = client.create_tweet(
                text=text[:280],
                in_reply_to_tweet_id=tweet_id,
            )
            reply_id = str(resp.data['id'])
            return {
                'reply_id': reply_id,
                'status': 'replied',
                'url': f'https://x.com/i/web/status/{reply_id}',
            }
        except Exception as e:
            self.logger.error('X reply failed: %s', e)
            return {'status': 'error', 'error': str(e)}

    def scan(self, user_id: str = None, since_id: str = None) -> list[dict]:
        """Full scan for mentions."""
        return self.get_mentions(user_id=user_id, since_id=since_id)
