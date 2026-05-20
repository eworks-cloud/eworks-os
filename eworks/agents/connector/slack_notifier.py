"""
Slack notifier for the Connector agent.
Sends interaction alerts to platform-specific channels.
Supports threaded replies for conversation continuity.
"""
from __future__ import annotations
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Channel mapping
CHANNEL_MAP = {
    'instagram': 'SLACK_INSTAGRAM_CHANNEL',
    'linkedin': 'SLACK_LINKEDIN_CHANNEL',
    'x': 'SLACK_X_CHANNEL',
    'youtube': 'SLACK_YOUTUBE_CHANNEL',
    'leads': 'SLACK_LEADS_CHANNEL',
}

PLATFORM_EMOJI = {
    'instagram': ':camera:',
    'linkedin': ':briefcase:',
    'x': ':bird:',
    'youtube': ':tv:',
}


class SlackNotifier:
    def __init__(self):
        self.token = os.environ.get('SLACK_BOT_TOKEN', '')
        self.channels = {
            k: os.environ.get(v, '') for k, v in CHANNEL_MAP.items()
        }
        self.logger = logging.getLogger(self.__class__.__name__)
        self._client = None

    def _get_client(self):
        if self._client:
            return self._client
        if not self.token:
            return None
        try:
            from slack_sdk import WebClient
            self._client = WebClient(token=self.token)
            return self._client
        except ImportError:
            self.logger.error('slack-sdk not installed')
            return None

    def _is_configured(self) -> bool:
        return bool(self.token)

    def notify_interaction(
        self,
        platform: str,
        interaction: dict,
        draft_reply: str = None,
        confidence: float = 0.0,
        reason: str = None,
    ) -> dict:
        """
        Send an interaction notification to the platform channel.
        Used when agent needs human review.
        Returns {'ts': slack_ts, 'channel': channel_id} or {'status': 'skipped'}.
        """
        client = self._get_client()
        channel = self.channels.get(platform, '')
        if not client or not channel:
            self.logger.warning('Slack not configured for platform: %s', platform)
            return {'status': 'skipped'}

        emoji = PLATFORM_EMOJI.get(platform, ':speech_balloon:')
        author = interaction.get('author_username') or interaction.get('author_name', 'Unknown')
        content = interaction.get('content', '')[:500]
        url = interaction.get('url', '')
        sentiment = interaction.get('sentiment', 'unknown')
        sentiment_emoji = {
            'positive': ':green_circle:',
            'negative': ':red_circle:',
            'neutral': ':white_circle:',
        }.get(sentiment, ':grey_question:')

        blocks = [
            {
                'type': 'header',
                'text': {'type': 'plain_text', 'text': f'{emoji} New {platform.capitalize()} Interaction'}
            },
            {
                'type': 'section',
                'fields': [
                    {'type': 'mrkdwn', 'text': f'*From:* @{author}'},
                    {'type': 'mrkdwn', 'text': f'*Sentiment:* {sentiment_emoji} {sentiment}'},
                    {'type': 'mrkdwn', 'text': f'*Confidence:* {int(confidence * 100)}%'},
                    {'type': 'mrkdwn', 'text': f'*Reason:* {reason or "Human review needed"}'},
                ]
            },
            {
                'type': 'section',
                'text': {'type': 'mrkdwn', 'text': f'*Message:*\n> {content}'}
            },
        ]

        if draft_reply:
            blocks.append({
                'type': 'section',
                'text': {'type': 'mrkdwn', 'text': f'*Draft reply:*\n```{draft_reply[:500]}```'}
            })

        if url:
            blocks.append({
                'type': 'actions',
                'elements': [{
                    'type': 'button',
                    'text': {'type': 'plain_text', 'text': 'View Post'},
                    'url': url,
                    'style': 'primary',
                }]
            })

        blocks.append({
            'type': 'context',
            'elements': [{
                'type': 'mrkdwn',
                'text': f'Interaction ID: {interaction.get("id", "?")} | {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}'
            }]
        })

        resp = client.chat_postMessage(
            channel=channel,
            text=f'New {platform} interaction from @{author}',
            blocks=blocks,
        )
        return {'ts': resp['ts'], 'channel': resp['channel'], 'status': 'sent'}

    def notify_lead(
        self,
        platform: str,
        interaction: dict,
        lead_signal: str,
        draft_reply: str = None,
    ) -> dict:
        """
        Send a HOT LEAD alert to #connector-leads channel.
        Used when meeting request or buying signal detected.
        """
        client = self._get_client()
        channel = self.channels.get('leads', '')
        if not client or not channel:
            return {'status': 'skipped'}

        emoji = PLATFORM_EMOJI.get(platform, ':speech_balloon:')
        author = interaction.get('author_username') or interaction.get('author_name', 'Unknown')
        content = interaction.get('content', '')[:500]
        url = interaction.get('url', '')

        blocks = [
            {
                'type': 'header',
                'text': {'type': 'plain_text', 'text': f':fire: HOT LEAD — {platform.capitalize()}'}
            },
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': f'*{emoji} @{author}* sent a signal on {platform.capitalize()}:\n> {content}'
                }
            },
            {
                'type': 'section',
                'fields': [
                    {'type': 'mrkdwn', 'text': f'*Signal:* :dart: {lead_signal}'},
                    {'type': 'mrkdwn', 'text': '*Action needed:* Jump in and close!'},
                ]
            },
        ]

        if draft_reply:
            blocks.append({
                'type': 'section',
                'text': {'type': 'mrkdwn', 'text': f'*Suggested opener:*\n```{draft_reply[:300]}```'}
            })

        if url:
            blocks.append({
                'type': 'actions',
                'elements': [{
                    'type': 'button',
                    'text': {'type': 'plain_text', 'text': ':rocket: Jump In'},
                    'url': url,
                    'style': 'danger',
                }]
            })

        resp = client.chat_postMessage(
            channel=channel,
            text=f':fire: Hot lead from @{author} on {platform}!',
            blocks=blocks,
        )
        return {'ts': resp['ts'], 'channel': resp['channel'], 'status': 'sent'}

    def send_daily_summary(self, stats: dict) -> dict:
        """
        Send daily summary to #connector-leads channel.
        stats: {interactions_found, replies_sent, escalations, leads_detected, by_platform}
        """
        client = self._get_client()
        channel = self.channels.get('leads', '')
        if not client or not channel:
            return {'status': 'skipped'}

        by_platform = stats.get('by_platform', {})
        platform_lines = '\n'.join(
            f'  {PLATFORM_EMOJI.get(p, "•")} *{p.capitalize()}*: {v.get("found", 0)} found, '
            f'{v.get("replied", 0)} replied, {v.get("escalated", 0)} escalated'
            for p, v in by_platform.items()
        )

        blocks = [
            {'type': 'header', 'text': {'type': 'plain_text', 'text': ':bar_chart: Connector Daily Summary'}},
            {
                'type': 'section',
                'fields': [
                    {'type': 'mrkdwn', 'text': f'*Total interactions:* {stats.get("interactions_found", 0)}'},
                    {'type': 'mrkdwn', 'text': f'*Auto-replied:* {stats.get("replies_sent", 0)}'},
                    {'type': 'mrkdwn', 'text': f'*Escalated to you:* {stats.get("escalations", 0)}'},
                    {'type': 'mrkdwn', 'text': f'*:fire: Leads detected:* {stats.get("leads_detected", 0)}'},
                ]
            },
            {'type': 'section', 'text': {'type': 'mrkdwn', 'text': f'*By platform:*\n{platform_lines}'}},
            {
                'type': 'context',
                'elements': [{
                    'type': 'mrkdwn',
                    'text': datetime.utcnow().strftime('%Y-%m-%d | Eworks OS Connector Agent')
                }]
            },
        ]

        resp = client.chat_postMessage(
            channel=channel,
            text='Connector daily summary',
            blocks=blocks,
        )
        return {'ts': resp['ts'], 'status': 'sent'}

    def reply_in_thread(self, channel: str, thread_ts: str, text: str) -> dict:
        """Reply to an existing Slack thread (for conversation continuity)."""
        client = self._get_client()
        if not client:
            return {'status': 'skipped'}
        resp = client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=text,
        )
        return {'ts': resp['ts'], 'status': 'sent'}
