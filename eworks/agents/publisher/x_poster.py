"""
X.com (Twitter) publisher via Twitter API v2 + tweepy.
Supports text tweets, threads, image tweets, video tweets.
"""
from __future__ import annotations
import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MAX_TWEET_LENGTH = 280
MAX_TWEETS_PER_DAY = 5  # Safety limit (API allows 17 free / 100 basic)


class XPoster:
    """
    Posts content to X.com (Twitter) via API v2.
    Uses tweepy for OAuth handling.
    """

    def __init__(self):
        self.api_key = os.environ.get('X_API_KEY', '')
        self.api_secret = os.environ.get('X_API_SECRET', '')
        self.access_token = os.environ.get('X_ACCESS_TOKEN', '')
        self.access_token_secret = os.environ.get('X_ACCESS_TOKEN_SECRET', '')
        self.bearer_token = os.environ.get('X_BEARER_TOKEN', '')
        self.logger = logging.getLogger(self.__class__.__name__)
        self._client = None
        self._api_v1 = None

    def _is_configured(self) -> bool:
        return all([
            self.api_key, self.api_secret,
            self.access_token, self.access_token_secret
        ])

    def _get_client(self):
        """Get tweepy Client (API v2) with OAuth1."""
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
            raise RuntimeError('tweepy not installed. Run: pip install tweepy')

    def _get_api_v1(self):
        """Get tweepy API v1.1 (needed for media upload)."""
        if self._api_v1:
            return self._api_v1
        try:
            import tweepy
            auth = tweepy.OAuth1UserHandler(
                self.api_key, self.api_secret,
                self.access_token, self.access_token_secret
            )
            self._api_v1 = tweepy.API(auth)
            return self._api_v1
        except ImportError:
            raise RuntimeError('tweepy not installed')

    def post_tweet(
        self,
        text: str,
        media_ids: list = None,
        reply_to_id: str = None,
        quote_tweet_id: str = None,
    ) -> dict:
        """Post a single tweet."""
        if not self._is_configured():
            return {'status': 'needs_auth'}
        client = self._get_client()
        # Truncate if needed
        text = text[:MAX_TWEET_LENGTH]
        kwargs = {'text': text}
        if media_ids:
            kwargs['media_ids'] = media_ids
        if reply_to_id:
            kwargs['in_reply_to_tweet_id'] = reply_to_id
        if quote_tweet_id:
            kwargs['quote_tweet_id'] = quote_tweet_id
        response = client.create_tweet(**kwargs)
        tweet_id = str(response.data['id'])
        tweet_url = f'https://x.com/i/web/status/{tweet_id}'
        self.logger.info('Tweet posted: %s', tweet_url)
        return {'tweet_id': tweet_id, 'tweet_url': tweet_url, 'status': 'posted'}

    def post_thread(self, texts: list[str]) -> dict:
        """
        Post a thread of tweets.
        Each text is one tweet. Automatically links them.
        Returns list of tweet IDs.
        """
        if not self._is_configured():
            return {'status': 'needs_auth'}
        if not texts:
            return {'status': 'error', 'message': 'No texts provided'}
        tweet_ids = []
        reply_to_id = None
        for i, text in enumerate(texts):
            # Add thread indicator
            truncated = text[:MAX_TWEET_LENGTH - 8]  # Leave room for counter
            if len(texts) > 1:
                truncated = f'{truncated} ({i+1}/{len(texts)})'
            result = self.post_tweet(truncated, reply_to_id=reply_to_id)
            if result.get('status') != 'posted':
                break
            tweet_ids.append(result['tweet_id'])
            reply_to_id = result['tweet_id']
            if i < len(texts) - 1:
                time.sleep(2)  # Small delay between tweets
        first_url = f'https://x.com/i/web/status/{tweet_ids[0]}' if tweet_ids else ''
        return {
            'tweet_ids': tweet_ids,
            'tweet_url': first_url,
            'thread_length': len(tweet_ids),
            'status': 'posted',
        }

    def compose_thread(self, long_text: str, max_length: int = 270) -> list[str]:
        """
        Split long text into thread-ready chunks.
        Splits on sentence boundaries where possible.
        """
        if len(long_text) <= max_length:
            return [long_text]
        chunks = []
        sentences = long_text.replace('\n\n', ' || ').replace('\n', ' ').split('. ')
        current = ''
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            test = f'{current}. {sentence}' if current else sentence
            if len(test) <= max_length:
                current = test
            else:
                if current:
                    chunks.append(current.strip())
                # If single sentence is too long, split by words
                if len(sentence) > max_length:
                    words = sentence.split()
                    current = ''
                    for word in words:
                        test_word = f'{current} {word}' if current else word
                        if len(test_word) <= max_length:
                            current = test_word
                        else:
                            if current:
                                chunks.append(current.strip())
                            current = word
                else:
                    current = sentence
        if current:
            chunks.append(current.strip())
        return [c for c in chunks if c]

    def upload_image(self, image_path: str, alt_text: str = '') -> str:
        """Upload image to Twitter and return media_id."""
        api = self._get_api_v1()
        media = api.media_upload(filename=image_path)
        media_id = str(media.media_id)
        # Add alt text for accessibility
        if alt_text:
            try:
                api.create_media_metadata(media_id, alt_text[:1000])
            except Exception as e:
                self.logger.warning('Alt text failed: %s', e)
        return media_id

    def upload_video(self, video_path: str) -> str:
        """Upload video to Twitter (chunked) and return media_id."""
        api = self._get_api_v1()
        # Chunked upload for video
        media = api.media_upload(
            filename=video_path,
            media_category='tweet_video',
            chunked=True,
        )
        media_id = str(media.media_id)
        # Wait for processing
        max_wait = 120
        elapsed = 0
        while elapsed < max_wait:
            status = api.get_media_upload_status(media_id)
            state = (
                status.processing_info.get('state')
                if hasattr(status, 'processing_info')
                else 'succeeded'
            )
            if state == 'succeeded':
                break
            elif state == 'failed':
                raise RuntimeError('Video processing failed on Twitter')
            time.sleep(5)
            elapsed += 5
        return media_id

    def post_image_tweet(self, text: str, image_path: str, alt_text: str = '') -> dict:
        """Post tweet with AI-generated image."""
        if not self._is_configured():
            return {'status': 'needs_auth'}
        media_id = self.upload_image(image_path, alt_text=alt_text)
        return self.post_tweet(text, media_ids=[media_id])

    def post_video_tweet(self, text: str, video_path: str) -> dict:
        """Post tweet with video attachment."""
        if not self._is_configured():
            return {'status': 'needs_auth'}
        media_id = self.upload_video(video_path)
        return self.post_tweet(text, media_ids=[media_id])

    def get_tweet_analytics(self, tweet_id: str) -> dict:
        """Fetch public metrics for a tweet."""
        if not self.bearer_token:
            return {'status': 'needs_auth'}
        client = self._get_client()
        response = client.get_tweet(
            tweet_id,
            tweet_fields=['public_metrics', 'created_at'],
        )
        if not response.data:
            return {'status': 'not_found', 'tweet_id': tweet_id}
        metrics = response.data.public_metrics or {}
        return {
            'tweet_id': tweet_id,
            'impressions': metrics.get('impression_count', 0),
            'likes': metrics.get('like_count', 0),
            'retweets': metrics.get('retweet_count', 0),
            'replies': metrics.get('reply_count', 0),
            'quotes': metrics.get('quote_count', 0),
            'bookmarks': metrics.get('bookmark_count', 0),
            'status': 'ok',
        }

    def delete_tweet(self, tweet_id: str) -> bool:
        """Delete a tweet by ID."""
        if not self._is_configured():
            return False
        client = self._get_client()
        response = client.delete_tweet(tweet_id)
        return bool(response.data and response.data.get('deleted'))
