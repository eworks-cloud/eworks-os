"""
X.com orchestrator — full pipeline from idea generation to posting.
"""
from __future__ import annotations
import asyncio
import json
import logging
import os
from datetime import datetime
from eworks.agents.base import BaseAgent
from eworks.agents.publisher.x_poster import XPoster
from eworks.agents.publisher.x_content_generator import XContentGenerator
from eworks.agents.publisher.x_analytics import XAnalyticsCollector
from eworks.agents.publisher.image_generator import ImageGenerator
from eworks.agents.publisher.video_generator import HeyGenAgent
from eworks.agents.publisher.tts import ElevenLabsAgent
from eworks.agents.publisher.approval import TelegramApproval
from eworks.agents.prospector.reporter import TelegramReporter


class XOrchestrator(BaseAgent):
    """
    Orchestrates X.com content creation and posting.
    Pipeline: generate → approve → post → track analytics
    """

    OPTIMAL_HOURS = [9, 10, 12, 17]  # 9 AM, 10 AM, noon, 5 PM
    OPTIMAL_DAYS = [0, 1, 2, 3, 4]   # Mon-Fri
    MAX_PER_DAY = 5

    def __init__(self, db, config):
        super().__init__(db, config)
        self.poster = XPoster()
        self.generator = XContentGenerator()
        self.analytics = XAnalyticsCollector(db)
        self.image_gen = ImageGenerator()
        self.video_gen = HeyGenAgent(db, config)
        self.tts = ElevenLabsAgent(db, config)
        self.approval = TelegramApproval()
        self.reporter = TelegramReporter(
            bot_token=os.environ.get('TELEGRAM_BOT_TOKEN', ''),
            chat_id=os.environ.get('TELEGRAM_CHAT_ID', ''),
        )

    def _save_post(
        self,
        content_type: str,
        text: str,
        thread_texts: list = None,
        image_path: str = None,
        video_path: str = None,
        image_prompt: str = None,
        idea_id: int = None,
    ) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO x_posts
                (content_type, text_content, thread_texts, image_path,
                 video_path, image_prompt, idea_id, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'draft', ?)""",
                (
                    content_type, text,
                    json.dumps(thread_texts or []),
                    image_path, video_path, image_prompt,
                    idea_id, datetime.utcnow().isoformat(),
                ),
            )
            return cursor.lastrowid

    def _update_post(
        self,
        post_id: int,
        tweet_id: str = None,
        tweet_url: str = None,
        thread_ids: list = None,
        status: str = 'posted',
    ) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                """UPDATE x_posts SET status=?, tweet_id=?, tweet_url=?,
                thread_tweet_ids=?, posted_at=? WHERE id=?""",
                (
                    status, tweet_id, tweet_url,
                    json.dumps(thread_ids or []),
                    datetime.utcnow().isoformat() if status == 'posted' else None,
                    post_id,
                ),
            )

    async def run(self, campaign_id: int = None) -> dict:
        return await self.post(
            content_type='tweet', topic='AI automation for business'
        )

    async def post(
        self,
        content_type: str = 'tweet',
        topic: str = None,
        language: str = 'en',
        style: str = 'insight',
        thread_length: int = 5,
        auto_approve: bool = False,
        dry_run: bool = False,
        cross_post_from_linkedin: str = None,
    ) -> dict:
        """
        Full pipeline: generate → [approve] → post → analytics.
        content_type: tweet | thread | image_tweet | video_tweet
        """
        topic = topic or 'AI automation for business leaders'

        # Step 1: Generate content
        self.logger.info('Generating X content: %s (%s)', content_type, topic)
        image_path = None
        video_path = None
        image_prompt = None
        thread_texts = []

        if cross_post_from_linkedin:
            thread_texts = self.generator.adapt_from_linkedin(
                cross_post_from_linkedin, language
            )
            text = thread_texts[0] if thread_texts else topic
            content_type = 'thread'
        elif content_type == 'thread':
            thread_texts = self.generator.generate_thread(topic, language, thread_length)
            text = thread_texts[0] if thread_texts else topic
        elif content_type == 'image_tweet':
            text = self.generator.generate_tweet(topic, language, style)
            image_prompt = self.generator.generate_image_prompt(topic, text)
            if not dry_run:
                image_path = self.image_gen.generate(
                    image_prompt,
                    size='landscape_16_9',
                    filename=f'x_img_{int(datetime.utcnow().timestamp())}',
                )
        elif content_type == 'video_tweet':
            text = self.generator.generate_tweet(topic, language, style)
            if not dry_run:
                audio = await self.tts.generate_audio(text, language=language)
                asset_id = await self.video_gen.upload_audio(audio)
                vid = await self.video_gen.generate_video(
                    text, format='reel', audio_asset_id=asset_id
                )
                video_path = vid.get('local_path')
        else:
            text = self.generator.generate_tweet(topic, language, style)

        # Step 2: Save draft
        post_id = self._save_post(
            content_type, text, thread_texts,
            image_path, video_path, image_prompt,
        )

        # Step 3: Approval
        if not auto_approve and not dry_run:
            preview = thread_texts[:2] if thread_texts else [text]
            package = {
                'title': f'X.com {content_type}: {topic[:60]}',
                'reel_script': '\n---\n'.join(preview),
                'instagram_caption': text,
                'youtube_title': f'X {content_type}',
                'post_id': post_id,
            }
            decision = await self.approval.send_approval_request(package)
            if decision != 'approved':
                self._update_post(post_id, status='failed')
                return {'status': 'rejected', 'post_id': post_id}

        if dry_run:
            return {
                'status': 'dry_run',
                'post_id': post_id,
                'text_preview': text[:200],
                'thread_preview': thread_texts[:2] if thread_texts else [],
                'content_type': content_type,
            }

        # Step 4: Post
        self._update_post(post_id, status='posting')
        try:
            if content_type == 'thread':
                result = self.poster.post_thread(thread_texts)
                tweet_id = result.get('tweet_ids', [''])[0]
                thread_ids = result.get('tweet_ids', [])
            elif content_type == 'image_tweet' and image_path:
                result = self.poster.post_image_tweet(text, image_path, alt_text=topic)
                tweet_id = result.get('tweet_id', '')
                thread_ids = []
            elif content_type == 'video_tweet' and video_path:
                result = self.poster.post_video_tweet(text, video_path)
                tweet_id = result.get('tweet_id', '')
                thread_ids = []
            else:
                result = self.poster.post_tweet(text)
                tweet_id = result.get('tweet_id', '')
                thread_ids = []

            tweet_url = result.get('tweet_url', '')
            self._update_post(post_id, tweet_id, tweet_url, thread_ids, 'posted')

            # Step 5: Report
            msg = (
                f'🐦 *X.com Post Published!*\n'
                f'📝 Topic: {topic[:60]}\n'
                f'📊 Type: {content_type}\n'
                f'🔗 URL: {tweet_url}\n'
            )
            await self.reporter.send(msg)

            return {
                'status': 'posted',
                'post_id': post_id,
                'tweet_id': tweet_id,
                'tweet_url': tweet_url,
                'content_type': content_type,
                'result': result,
            }
        except Exception as e:
            self.logger.error('X post failed: %s', e)
            self._update_post(post_id, status='failed')
            return {'status': 'failed', 'error': str(e), 'post_id': post_id}

    async def cross_post_from_linkedin(
        self,
        linkedin_text: str,
        language: str = 'en',
        auto_approve: bool = False,
    ) -> dict:
        """Adapt a LinkedIn post and publish as X thread."""
        return await self.post(
            content_type='thread',
            language=language,
            auto_approve=auto_approve,
            cross_post_from_linkedin=linkedin_text,
        )
