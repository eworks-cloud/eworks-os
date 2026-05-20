"""
Connector Agent Orchestrator.
Runs all platform listeners, generates replies, escalates to Slack.
"""
from __future__ import annotations
import asyncio
import logging
import os
from datetime import datetime
from eworks.agents.base import BaseAgent
from eworks.agents.connector.instagram_listener import InstagramListener
from eworks.agents.connector.x_listener import XListener
from eworks.agents.connector.linkedin_listener import LinkedInListener
from eworks.agents.connector.youtube_listener import YouTubeListener
from eworks.agents.connector.reply_generator import ReplyGenerator
from eworks.agents.connector.slack_notifier import SlackNotifier
from eworks.agents.connector.conversation_tracker import ConversationTracker, MAX_EXCHANGES
from eworks.agents.prospector.reporter import TelegramReporter

CONFIDENCE_THRESHOLD = 0.70  # Auto-reply above this, escalate below


class ConnectorOrchestrator(BaseAgent):
    """
    Monitors all social platforms, auto-replies or escalates to Slack.
    The human-in-the-loop is Cesar via Slack channels.
    """

    def __init__(self, db, config):
        super().__init__(db, config)
        self.instagram = InstagramListener()
        self.x = XListener()
        self.linkedin = LinkedInListener()
        self.youtube = YouTubeListener()
        self.generator = ReplyGenerator()
        self.slack = SlackNotifier()
        self.tracker = ConversationTracker(db)
        self.reporter = TelegramReporter(
            bot_token=os.environ.get('TELEGRAM_BOT_TOKEN', ''),
            chat_id=os.environ.get('TELEGRAM_CHAT_ID', ''),
        )

    def _log_run(self, run_type: str, stats: dict) -> None:
        try:
            with self.db.get_connection() as conn:
                conn.execute(
                    """INSERT INTO connector_runs
                    (run_type, started_at, completed_at, interactions_found,
                     replies_sent, escalations, leads_detected, errors)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        run_type,
                        stats.get('started_at', datetime.utcnow().isoformat()),
                        datetime.utcnow().isoformat(),
                        stats.get('found', 0),
                        stats.get('replied', 0),
                        stats.get('escalated', 0),
                        stats.get('leads', 0),
                        stats.get('errors', 0),
                    )
                )
        except Exception as e:
            self.logger.error('Failed to log run: %s', e)

    async def _process_interaction(self, interaction: dict) -> dict:
        """
        Core logic for a single interaction:
        1. Check if already seen / in cooldown
        2. Generate reply + analysis
        3. Auto-reply OR escalate to Slack
        """
        platform = interaction['platform']
        external_id = interaction['external_id']
        author_id = interaction.get('author_id', '')
        parent_id = interaction.get('parent_id', '')
        content = interaction['content']

        # Skip if already processed
        if self.tracker.is_already_seen(platform, external_id):
            return {'action': 'already_seen'}

        # Skip if in cooldown
        if author_id and self.tracker.is_in_cooldown(platform, author_id):
            return {'action': 'cooldown'}

        # Get thread context
        context = self.tracker.get_thread_context(platform, parent_id, author_id)
        exchange_count = self.tracker.get_exchange_count(platform, parent_id, author_id)

        # Generate reply + analysis
        analysis = self.generator.generate_reply(
            content=content,
            platform=platform,
            thread_context=context,
            author_name=interaction.get('author_name', ''),
        )

        # Save to DB
        interaction_id = self.tracker.save_interaction(interaction, analysis)
        if not interaction_id:
            return {'action': 'duplicate'}

        # Determine action
        is_lead = analysis.get('is_lead', False)
        should_escalate = (
            analysis.get('should_escalate', False)
            or analysis.get('confidence', 0) < CONFIDENCE_THRESHOLD
            or exchange_count >= MAX_EXCHANGES
        )
        escalate_reason = analysis.get('escalate_reason', '')
        if exchange_count >= MAX_EXCHANGES:
            should_escalate = True
            escalate_reason = f'Max exchanges ({MAX_EXCHANGES}) reached'

        draft_reply = analysis.get('reply', '')

        # HOT LEAD — notify Slack leads channel
        if is_lead:
            lead_opener = self.generator.generate_lead_opener(
                content=content,
                author_name=interaction.get('author_name', ''),
                platform=platform,
                language=analysis.get('language', 'en'),
            )
            slack_result = self.slack.notify_lead(
                platform=platform,
                interaction={**interaction, 'id': interaction_id},
                lead_signal=analysis.get('lead_signal', ''),
                draft_reply=lead_opener,
            )
            self.tracker.mark_escalated(
                interaction_id,
                slack_result.get('ts', ''),
                slack_result.get('channel', ''),
            )
            return {'action': 'lead_escalated', 'slack': slack_result, 'is_lead': True, 'platform': platform}

        # ESCALATE to platform channel (low confidence / negative / max exchanges)
        elif should_escalate:
            slack_result = self.slack.notify_interaction(
                platform=platform,
                interaction={**interaction, 'id': interaction_id},
                draft_reply=draft_reply,
                confidence=analysis.get('confidence', 0),
                reason=escalate_reason,
            )
            self.tracker.mark_escalated(
                interaction_id,
                slack_result.get('ts', ''),
                slack_result.get('channel', ''),
            )
            return {'action': 'escalated', 'slack': slack_result, 'is_lead': False, 'platform': platform}

        # AUTO-REPLY
        elif draft_reply:
            reply_result = await self._post_reply(platform, interaction, draft_reply)
            if reply_result.get('status') == 'replied':
                self.tracker.mark_replied(
                    interaction_id,
                    draft_reply,
                    reply_result.get('reply_id', ''),
                )
                return {'action': 'replied', 'reply': draft_reply, 'is_lead': False, 'platform': platform}
            else:
                # Reply failed — escalate
                slack_result = self.slack.notify_interaction(
                    platform=platform,
                    interaction={**interaction, 'id': interaction_id},
                    draft_reply=draft_reply,
                    confidence=analysis.get('confidence', 0),
                    reason=f'Auto-reply failed: {reply_result.get("error", "unknown")}',
                )
                self.tracker.mark_escalated(
                    interaction_id,
                    slack_result.get('ts', ''),
                    slack_result.get('channel', ''),
                )
                return {'action': 'reply_failed_escalated', 'is_lead': False, 'platform': platform}

        return {'action': 'no_reply_generated', 'is_lead': is_lead, 'platform': platform}

    async def _post_reply(self, platform: str, interaction: dict, text: str) -> dict:
        """Post a reply to the appropriate platform."""
        try:
            if platform == 'instagram':
                return await self.instagram.reply_to_comment(
                    interaction['parent_id'], interaction['external_id'], text
                )
            elif platform == 'x':
                return self.x.reply_to_tweet(interaction['external_id'], text)
            elif platform == 'linkedin':
                return self.linkedin.reply_to_comment(
                    interaction['parent_id'], interaction['external_id'], text
                )
            elif platform == 'youtube':
                return self.youtube.reply_to_comment(interaction['external_id'], text)
            return {'status': 'unsupported'}
        except Exception as e:
            self.logger.error('Reply post failed on %s: %s', platform, e)
            return {'status': 'error', 'error': str(e)}

    async def run(self, campaign_id: int = None) -> dict:
        """Default run — scan all platforms."""
        return await self.run_all()

    async def run_platform(self, platform: str, since_minutes: int = 60) -> dict:
        """Scan a single platform and process interactions."""
        started = datetime.utcnow().isoformat()
        stats = {
            'found': 0, 'replied': 0, 'escalated': 0, 'leads': 0, 'errors': 0,
            'started_at': started,
        }

        try:
            if platform == 'instagram':
                interactions = await self.instagram.scan(since_minutes=since_minutes)
            elif platform == 'x':
                interactions = self.x.scan()
            elif platform == 'linkedin':
                interactions = self.linkedin.scan()
            elif platform == 'youtube':
                interactions = self.youtube.scan()
            else:
                return stats

            stats['found'] = len(interactions)
            for interaction in interactions:
                try:
                    result = await self._process_interaction(interaction)
                    action = result.get('action', '')
                    if action == 'replied':
                        stats['replied'] += 1
                    elif action in ('escalated', 'reply_failed_escalated'):
                        stats['escalated'] += 1
                    elif action == 'lead_escalated':
                        stats['leads'] += 1
                        stats['escalated'] += 1
                    await asyncio.sleep(1)  # Rate limit
                except Exception as e:
                    self.logger.error('Interaction processing error: %s', e)
                    stats['errors'] += 1
        except Exception as e:
            self.logger.error('Platform scan error (%s): %s', platform, e)
            stats['errors'] += 1

        self._log_run(platform, stats)
        return stats

    async def run_all(self, since_minutes: int = 60) -> dict:
        """Scan all platforms concurrently."""
        started = datetime.utcnow().isoformat()
        platforms = ['instagram', 'x', 'linkedin', 'youtube']
        results = await asyncio.gather(
            *[self.run_platform(p, since_minutes) for p in platforms],
            return_exceptions=True,
        )
        totals = {
            'found': 0, 'replied': 0, 'escalated': 0, 'leads': 0, 'errors': 0,
            'by_platform': {}, 'started_at': started,
        }
        for platform, result in zip(platforms, results):
            if isinstance(result, Exception):
                totals['errors'] += 1
                totals['by_platform'][platform] = {
                    'found': 0, 'replied': 0, 'escalated': 0, 'error': str(result),
                }
            else:
                totals['found'] += result.get('found', 0)
                totals['replied'] += result.get('replied', 0)
                totals['escalated'] += result.get('escalated', 0)
                totals['leads'] += result.get('leads', 0)
                totals['errors'] += result.get('errors', 0)
                totals['by_platform'][platform] = {
                    'found': result.get('found', 0),
                    'replied': result.get('replied', 0),
                    'escalated': result.get('escalated', 0),
                }
        # Send daily summary to Slack if anything was found
        if totals['found'] > 0:
            self.slack.send_daily_summary(totals)
        self._log_run('all', totals)
        return totals

    def get_pending_interactions(self, platform: str = None) -> list[dict]:
        """Get all pending interactions for the unified inbox CLI."""
        return self.tracker.get_pending(platform=platform)
