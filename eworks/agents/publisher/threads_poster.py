"""
Meta Threads publisher via the Threads API (graph.facebook.com/v1.0).
Supports text, image, video, and carousel posts with full retry logic
and local DB persistence.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import requests

from eworks.agents.publisher.base_publisher import BasePublisher

logger = logging.getLogger(__name__)

THREADS_API_BASE = 'https://graph.facebook.com/v1.0'
MAX_TEXT_LENGTH = 500       # Threads character limit per post
MAX_CAROUSEL_ITEMS = 10     # Maximum items in a single carousel post
MAX_RETRIES = 3             # Retry attempts for transient API failures
RETRY_DELAY = 2.0           # Base seconds between retries (multiplied by attempt)
RATE_LIMIT_DELAY = 60.0     # Seconds to wait after a 429 response


class ThreadsPoster(BasePublisher):
    """
    Posts content to Meta Threads via the Threads API.

    Requires the following environment variables:
        THREADS_ACCESS_TOKEN  — long-lived user access token with
                                threads_publish_content scope.
        THREADS_USER_ID       — numeric Threads / Instagram user ID.

    DB table managed by this class: ``threads_posts``
    Columns: id, threads_post_id, media_type, text_content, media_url,
             status, created_at, published_at, views, likes,
             replies_count, reposts, quotes.
    """

    def __init__(self, db, config):
        super().__init__(db, config)
        self.access_token = os.environ.get('THREADS_ACCESS_TOKEN', '')
        self.user_id = os.environ.get('THREADS_USER_ID', '')
        self.logger = logging.getLogger(self.__class__.__name__)
        self._base_url = THREADS_API_BASE

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def _is_configured(self) -> bool:
        """Return True if both the access token and user ID are set."""
        return bool(self.access_token and self.user_id)

    def _default_params(self) -> dict:
        """Return the base query-string params that every request needs."""
        return {'access_token': self.access_token}

    # ------------------------------------------------------------------
    # Low-level HTTP helpers with retry + rate-limit handling
    # ------------------------------------------------------------------

    def _post(self, url: str, params: dict = None) -> dict:
        """
        HTTP POST to the Threads API with automatic retry.

        Retries up to MAX_RETRIES times on transient network errors.
        On a 429 rate-limit response the method waits RATE_LIMIT_DELAY
        seconds before the next attempt (counts as one attempt).

        Args:
            url:    Full endpoint URL.
            params: Query-string parameters (access_token included here
                    because the Threads API accepts tokens via query param).

        Returns:
            Parsed JSON response as a dict.

        Raises:
            RuntimeError: When all retry attempts are exhausted.
        """
        params = params or {}
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.post(url, params=params, timeout=30)
                if resp.status_code == 429:
                    self.logger.warning(
                        'Rate limited by Threads API (attempt %d/%d). '
                        'Waiting %ss before retry.',
                        attempt, MAX_RETRIES, RATE_LIMIT_DELAY,
                    )
                    time.sleep(RATE_LIMIT_DELAY)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as exc:
                self.logger.warning(
                    'Threads API POST error (attempt %d/%d): %s',
                    attempt, MAX_RETRIES, exc,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                else:
                    raise RuntimeError(
                        f'Threads API POST failed after {MAX_RETRIES} attempts: {exc}'
                    ) from exc
        raise RuntimeError(
            f'Threads API POST failed after {MAX_RETRIES} attempts (rate limited)'
        )

    def _get(self, url: str, params: dict = None) -> dict:
        """
        HTTP GET from the Threads API with automatic retry.

        Follows the same retry / rate-limit strategy as :meth:`_post`.

        Args:
            url:    Full endpoint URL.
            params: Query-string parameters.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            RuntimeError: When all retry attempts are exhausted.
        """
        params = params or {}
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(url, params=params, timeout=30)
                if resp.status_code == 429:
                    self.logger.warning(
                        'Rate limited by Threads API (attempt %d/%d). '
                        'Waiting %ss before retry.',
                        attempt, MAX_RETRIES, RATE_LIMIT_DELAY,
                    )
                    time.sleep(RATE_LIMIT_DELAY)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as exc:
                self.logger.warning(
                    'Threads API GET error (attempt %d/%d): %s',
                    attempt, MAX_RETRIES, exc,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                else:
                    raise RuntimeError(
                        f'Threads API GET failed after {MAX_RETRIES} attempts: {exc}'
                    ) from exc
        raise RuntimeError(
            f'Threads API GET failed after {MAX_RETRIES} attempts (rate limited)'
        )

    # ------------------------------------------------------------------
    # Container lifecycle
    # ------------------------------------------------------------------

    def _create_container(self, media_type: str, **kwargs) -> str:
        """
        Create a Threads media container (first step of the two-step publish flow).

        Args:
            media_type: One of ``TEXT``, ``IMAGE``, ``VIDEO``, ``CAROUSEL``.
            **kwargs:   Additional API fields — e.g. ``text``, ``image_url``,
                        ``video_url``, ``children``, ``is_carousel_item``.

        Returns:
            Container ID string returned by the API.

        Raises:
            RuntimeError: If the API returns no container ID or an error.
        """
        url = f'{self._base_url}/{self.user_id}/threads'
        params = {**self._default_params(), 'media_type': media_type, **kwargs}
        self.logger.debug('Creating %s container for user %s', media_type, self.user_id)
        data = self._post(url, params=params)
        container_id = data.get('id')
        if not container_id:
            raise RuntimeError(f'No container ID returned from Threads API: {data}')
        self.logger.debug('Created %s container: %s', media_type, container_id)
        return container_id

    def _publish_container(self, container_id: str) -> str:
        """
        Publish a previously created Threads container (second step).

        Args:
            container_id: The container ID returned by :meth:`_create_container`.

        Returns:
            The published post ID string.

        Raises:
            RuntimeError: If the API returns no post ID or an error.
        """
        url = f'{self._base_url}/{self.user_id}/threads_publish'
        params = {**self._default_params(), 'creation_id': container_id}
        self.logger.debug('Publishing container %s', container_id)
        data = self._post(url, params=params)
        post_id = data.get('id')
        if not post_id:
            raise RuntimeError(f'No post ID returned from Threads publish API: {data}')
        self.logger.info('Threads container %s published as post %s', container_id, post_id)
        return post_id

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    def _ensure_table(self) -> None:
        """Create the ``threads_posts`` table if it does not already exist."""
        with self._get_conn() as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS threads_posts (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    threads_post_id TEXT    UNIQUE,
                    media_type      TEXT    NOT NULL,
                    text_content    TEXT,
                    media_url       TEXT,
                    status          TEXT    NOT NULL DEFAULT 'pending',
                    created_at      TEXT    NOT NULL,
                    published_at    TEXT,
                    views           INTEGER DEFAULT 0,
                    likes           INTEGER DEFAULT 0,
                    replies_count   INTEGER DEFAULT 0,
                    reposts         INTEGER DEFAULT 0,
                    quotes          INTEGER DEFAULT 0
                )
                '''
            )
            conn.commit()

    def _save_post(
        self,
        threads_post_id: str,
        media_type: str,
        text_content: str,
        media_url: str,
        status: str,
        published_at: Optional[str] = None,
    ) -> int:
        """
        Persist a new Threads post record to the local database.

        Args:
            threads_post_id: Post ID from the Threads API.
            media_type:      TEXT / IMAGE / VIDEO / CAROUSEL.
            text_content:    Caption or post text.
            media_url:       Primary media URL (comma-separated for carousel).
            status:          ``published``, ``pending``, or ``error``.
            published_at:    ISO-8601 UTC timestamp; defaults to now.

        Returns:
            Auto-incremented row ID of the inserted record.
        """
        self._ensure_table()
        now = datetime.now(timezone.utc).isoformat()
        with self._get_conn() as conn:
            cursor = conn.execute(
                '''
                INSERT INTO threads_posts
                    (threads_post_id, media_type, text_content, media_url,
                     status, created_at, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    threads_post_id, media_type, text_content, media_url,
                    status, now, published_at or now,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def _update_analytics(self, threads_post_id: str, metrics: dict) -> None:
        """
        Update analytics columns for an existing ``threads_posts`` row.

        Args:
            threads_post_id: The post ID to update.
            metrics:         Dict with keys views, likes, replies_count,
                             reposts, quotes.
        """
        self._ensure_table()
        with self._get_conn() as conn:
            conn.execute(
                '''
                UPDATE threads_posts
                SET views = ?, likes = ?, replies_count = ?,
                    reposts = ?, quotes = ?
                WHERE threads_post_id = ?
                ''',
                (
                    metrics.get('views', 0),
                    metrics.get('likes', 0),
                    metrics.get('replies_count', 0),
                    metrics.get('reposts', 0),
                    metrics.get('quotes', 0),
                    threads_post_id,
                ),
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Public posting methods
    # ------------------------------------------------------------------

    def post_text(self, text: str) -> dict:
        """
        Post a plain-text thread.

        Args:
            text: Post body (truncated to MAX_TEXT_LENGTH characters).

        Returns:
            Dict with keys: threads_post_id, threads_url, status.
            On failure: status is ``'error'`` or ``'needs_auth'``.
        """
        if not self._is_configured():
            return {'status': 'needs_auth'}
        text = text[:MAX_TEXT_LENGTH]
        try:
            container_id = self._create_container('TEXT', text=text)
            post_id = self._publish_container(container_id)
        except RuntimeError as exc:
            self.logger.error('post_text failed: %s', exc)
            return {'status': 'error', 'message': str(exc)}
        post_url = f'https://www.threads.net/t/{post_id}'
        published_at = datetime.now(timezone.utc).isoformat()
        self._save_post(post_id, 'TEXT', text, '', 'published', published_at)
        self.logger.info('Threads text post: %s', post_url)
        return {'threads_post_id': post_id, 'threads_url': post_url, 'status': 'posted'}

    def post_image(self, text: str, image_url: str) -> dict:
        """
        Post an image thread with an optional caption.

        The image must be publicly accessible (the Threads API fetches it
        directly — local paths are not accepted).

        Args:
            text:      Caption (truncated to MAX_TEXT_LENGTH characters).
            image_url: Publicly accessible URL of the image.

        Returns:
            Dict with keys: threads_post_id, threads_url, status.
        """
        if not self._is_configured():
            return {'status': 'needs_auth'}
        text = text[:MAX_TEXT_LENGTH]
        try:
            container_id = self._create_container('IMAGE', text=text, image_url=image_url)
            post_id = self._publish_container(container_id)
        except RuntimeError as exc:
            self.logger.error('post_image failed: %s', exc)
            return {'status': 'error', 'message': str(exc)}
        post_url = f'https://www.threads.net/t/{post_id}'
        published_at = datetime.now(timezone.utc).isoformat()
        self._save_post(post_id, 'IMAGE', text, image_url, 'published', published_at)
        self.logger.info('Threads image post: %s', post_url)
        return {'threads_post_id': post_id, 'threads_url': post_url, 'status': 'posted'}

    def post_video(self, text: str, video_url: str) -> dict:
        """
        Post a video thread with an optional caption.

        The video must be publicly accessible (MP4, MOV; max 5 min / 1 GB).

        Args:
            text:      Caption (truncated to MAX_TEXT_LENGTH characters).
            video_url: Publicly accessible URL of the video.

        Returns:
            Dict with keys: threads_post_id, threads_url, status.
        """
        if not self._is_configured():
            return {'status': 'needs_auth'}
        text = text[:MAX_TEXT_LENGTH]
        try:
            container_id = self._create_container('VIDEO', text=text, video_url=video_url)
            post_id = self._publish_container(container_id)
        except RuntimeError as exc:
            self.logger.error('post_video failed: %s', exc)
            return {'status': 'error', 'message': str(exc)}
        post_url = f'https://www.threads.net/t/{post_id}'
        published_at = datetime.now(timezone.utc).isoformat()
        self._save_post(post_id, 'VIDEO', text, video_url, 'published', published_at)
        self.logger.info('Threads video post: %s', post_url)
        return {'threads_post_id': post_id, 'threads_url': post_url, 'status': 'posted'}

    def post_carousel(self, text: str, media_urls: list[str]) -> dict:
        """
        Post a carousel thread containing multiple images and/or videos.

        The flow is:
            1. Create individual item containers (one per URL).
            2. Create a CAROUSEL container that references the item IDs.
            3. Publish the carousel container.

        Media type (IMAGE vs VIDEO) is inferred from the URL file extension.
        Items capped at MAX_CAROUSEL_ITEMS.

        Args:
            text:       Caption (truncated to MAX_TEXT_LENGTH characters).
            media_urls: Publicly accessible image or video URLs.

        Returns:
            Dict with keys: threads_post_id, threads_url, item_count, status.
        """
        if not self._is_configured():
            return {'status': 'needs_auth'}
        if not media_urls:
            return {'status': 'error', 'message': 'No media URLs provided'}
        text = text[:MAX_TEXT_LENGTH]
        media_urls = media_urls[:MAX_CAROUSEL_ITEMS]
        try:
            # Step 1 — create one container per item
            item_ids: list[str] = []
            for url in media_urls:
                lower_url = url.lower()
                if any(lower_url.endswith(ext) for ext in ('.mp4', '.mov', '.avi', '.webm')):
                    item_id = self._create_container(
                        'VIDEO', video_url=url, is_carousel_item='true'
                    )
                else:
                    item_id = self._create_container(
                        'IMAGE', image_url=url, is_carousel_item='true'
                    )
                item_ids.append(item_id)
                time.sleep(1)  # Brief pause between item creations
            # Step 2 — create the carousel container
            carousel_id = self._create_container(
                'CAROUSEL',
                text=text,
                children=','.join(item_ids),
            )
            # Step 3 — publish
            post_id = self._publish_container(carousel_id)
        except RuntimeError as exc:
            self.logger.error('post_carousel failed: %s', exc)
            return {'status': 'error', 'message': str(exc)}
        post_url = f'https://www.threads.net/t/{post_id}'
        published_at = datetime.now(timezone.utc).isoformat()
        self._save_post(
            post_id, 'CAROUSEL', text, ','.join(media_urls), 'published', published_at
        )
        self.logger.info('Threads carousel post (%d items): %s', len(item_ids), post_url)
        return {
            'threads_post_id': post_id,
            'threads_url': post_url,
            'item_count': len(item_ids),
            'status': 'posted',
        }

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_post_analytics(self, post_id: str) -> dict:
        """
        Fetch public metrics for a published Threads post.

        Calls the Threads Insights endpoint and returns views, likes,
        replies, reposts, and quotes.  Results are persisted back to the
        local ``threads_posts`` table.

        Args:
            post_id: The Threads post ID to query.

        Returns:
            Dict with keys: post_id, views, likes, replies_count,
            reposts, quotes, status.
        """
        if not self._is_configured():
            return {'status': 'needs_auth'}
        url = f'{self._base_url}/{post_id}/insights'
        params = {
            **self._default_params(),
            'metric': 'views,likes,replies,reposts,quotes',
        }
        try:
            data = self._get(url, params=params)
        except RuntimeError as exc:
            self.logger.error('get_post_analytics failed for post %s: %s', post_id, exc)
            return {'status': 'error', 'post_id': post_id, 'message': str(exc)}
        # Parse the insights data array returned by the API
        metrics: dict[str, int] = {
            'views': 0,
            'likes': 0,
            'replies_count': 0,
            'reposts': 0,
            'quotes': 0,
        }
        for item in data.get('data', []):
            name = item.get('name', '')
            # The API may return values as a list or a direct scalar
            if item.get('values'):
                value = item['values'][0].get('value', 0)
            else:
                value = item.get('value', 0)
            if name == 'views':
                metrics['views'] = int(value)
            elif name == 'likes':
                metrics['likes'] = int(value)
            elif name == 'replies':
                metrics['replies_count'] = int(value)
            elif name == 'reposts':
                metrics['reposts'] = int(value)
            elif name == 'quotes':
                metrics['quotes'] = int(value)
        self._update_analytics(post_id, metrics)
        return {'post_id': post_id, **metrics, 'status': 'ok'}

    # ------------------------------------------------------------------
    # Feed / reply helpers
    # ------------------------------------------------------------------

    def list_posts(self, limit: int = 10) -> dict:
        """
        Retrieve the most recent posts for the authenticated Threads user.

        Args:
            limit: Maximum number of posts to return (default 10).

        Returns:
            Dict with keys: posts (list), status.
        """
        if not self._is_configured():
            return {'status': 'needs_auth'}
        url = f'{self._base_url}/{self.user_id}/threads'
        params = {
            **self._default_params(),
            'fields': 'id,media_type,text,timestamp,permalink',
            'limit': limit,
        }
        try:
            data = self._get(url, params=params)
        except RuntimeError as exc:
            self.logger.error('list_posts failed: %s', exc)
            return {'status': 'error', 'message': str(exc)}
        return {'posts': data.get('data', []), 'status': 'ok'}

    def get_replies(self, thread_id: str) -> dict:
        """
        Retrieve replies to a specific Threads post.

        Args:
            thread_id: The Threads post ID to fetch replies for.

        Returns:
            Dict with keys: replies (list), status.
        """
        if not self._is_configured():
            return {'status': 'needs_auth'}
        url = f'{self._base_url}/{thread_id}/replies'
        params = {
            **self._default_params(),
            'fields': 'id,text,timestamp,username',
        }
        try:
            data = self._get(url, params=params)
        except RuntimeError as exc:
            self.logger.error('get_replies failed for thread %s: %s', thread_id, exc)
            return {'status': 'error', 'message': str(exc)}
        return {'replies': data.get('data', []), 'status': 'ok'}

    # ------------------------------------------------------------------
    # BasePublisher required override
    # ------------------------------------------------------------------

    async def run(self, campaign_id: int) -> dict:
        """
        Pipeline entry point — override or call the post_* methods directly.

        Args:
            campaign_id: Campaign row ID from the database.

        Returns:
            Dict with status and campaign_id.
        """
        self.logger.info('ThreadsPoster.run called for campaign %d', campaign_id)
        return {'status': 'ok', 'campaign_id': campaign_id}
