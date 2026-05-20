"""
X.com content generator using Claude AI.
Generates tweets, threads, and image prompts optimized for X.
"""
from __future__ import annotations
import os
import json
import logging
import anthropic

logger = logging.getLogger(__name__)

X_SYSTEM_PROMPT = """You are Cesar Schneider, founder of Eworks Labs AI Agency.
You write X.com (Twitter) content that builds authority in AI automation for business.
Your style: direct, insightful, data-driven, conversational but authoritative.
You write for CTOs, founders, and business leaders who want to leverage AI.
No buzzwords. No cringe. No self-promotion without value. Always lead with insight."""


class XContentGenerator:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY', ''))
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_tweet(self, topic: str, language: str = 'en', style: str = 'insight') -> str:
        """
        Generate a single tweet (max 280 chars).
        Styles: insight, tip, question, stat, announcement
        """
        style_guides = {
            'insight': 'Share a counterintuitive insight about the topic. Start strong.',
            'tip': 'Share 1 actionable tip. Use a numbered format if helpful.',
            'question': 'Ask a thought-provoking question that sparks engagement.',
            'stat': 'Lead with a surprising stat or fact, then explain why it matters.',
            'announcement': 'Announce something exciting concisely. Build curiosity.',
        }
        prompt = f"""
Write a single tweet about: {topic}
Style: {style_guides.get(style, style_guides['insight'])}
Language: {'Brazilian Portuguese' if language == 'pt' else 'English'}

Rules:
- Max 270 characters (leave room for links/hashtags)
- No hashtags in the tweet body (add max 2 at end if truly relevant)
- No emojis unless they add meaning
- No generic openers like 'Did you know' or 'Hot take'
- End with a hook that makes people want to reply or click

Return ONLY the tweet text, nothing else."""

        msg = self.client.messages.create(
            model='claude-opus-4-5',
            max_tokens=300,
            system=X_SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': prompt}]
        )
        tweet = msg.content[0].text.strip()
        # Enforce 280 char limit
        return tweet[:280]

    def generate_thread(self, topic: str, language: str = 'en', num_tweets: int = 5) -> list[str]:
        """
        Generate a numbered thread about a topic.
        Returns list of tweet texts.
        """
        prompt = f"""
Write a {num_tweets}-tweet thread about: {topic}
Language: {'Brazilian Portuguese' if language == 'pt' else 'English'}

Format:
- Tweet 1: Hook — the most compelling reason to read this thread
- Tweets 2-{num_tweets-1}: One key insight or tip per tweet
- Last tweet: Call to action or summary + invite to follow/reply

Rules:
- Each tweet max 260 characters
- Number them: 1/{num_tweets}, 2/{num_tweets}, etc.
- Each tweet must standalone but also flow as a thread
- No filler. Every tweet must deliver value.
- Max 1 relevant hashtag per tweet

Return as JSON array of strings: ["tweet1", "tweet2", ...]"""

        msg = self.client.messages.create(
            model='claude-opus-4-5',
            max_tokens=2000,
            system=X_SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': prompt}]
        )
        raw = msg.content[0].text.strip()
        # Parse JSON
        try:
            if '```' in raw:
                raw = raw.split('```')[1].replace('json', '').strip()
            tweets = json.loads(raw)
            return [t[:280] for t in tweets[:num_tweets]]
        except Exception:
            # Fallback: split by newlines
            lines = [l.strip() for l in raw.split('\n') if l.strip()]
            return [l[:280] for l in lines[:num_tweets]]

    def generate_image_prompt(self, topic: str, tweet_text: str) -> str:
        """Generate an image prompt optimized for X posts (16:9 landscape)."""
        prompt = f"""Generate a DALL-E/FAL.ai image prompt for an X.com post about: {topic}
Tweet: {tweet_text}

The image should be:
- Landscape 16:9 format
- Professional, minimal, modern
- Tech/AI aesthetic
- Text-free (no words in the image)
- High contrast, eye-catching in a feed

Return ONLY the image generation prompt, nothing else."""
        msg = self.client.messages.create(
            model='claude-haiku-4-5',
            max_tokens=200,
            messages=[{'role': 'user', 'content': prompt}]
        )
        return msg.content[0].text.strip()

    def adapt_from_linkedin(self, linkedin_text: str, language: str = 'en') -> list[str]:
        """
        Adapt existing LinkedIn post to X thread format.
        Useful for cross-posting with platform-appropriate tone.
        """
        prompt = f"""Adapt this LinkedIn post into a 4-5 tweet X.com thread.
LinkedIn post: {linkedin_text[:2000]}
Language: {'Brazilian Portuguese' if language == 'pt' else 'English'}

Rules:
- Shorter, punchier sentences
- X audience is more casual and tech-savvy
- Keep the core insights, strip the corporate tone
- Each tweet max 260 chars
- Return as JSON array: ["tweet1", "tweet2", ...]"""
        msg = self.client.messages.create(
            model='claude-opus-4-5',
            max_tokens=1500,
            system=X_SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': prompt}]
        )
        raw = msg.content[0].text.strip()
        try:
            if '```' in raw:
                raw = raw.split('```')[1].replace('json', '').strip()
            tweets = json.loads(raw)
            return [t[:280] for t in tweets]
        except Exception:
            lines = [l.strip() for l in raw.split('\n') if l.strip()]
            return [l[:280] for l in lines]
