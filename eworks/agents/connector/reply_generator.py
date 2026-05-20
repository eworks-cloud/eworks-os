"""
Claude AI reply generator for the Connector agent.
Generates platform-appropriate replies in Cesar Schneider's voice.
Includes lead detection, sentiment analysis, and confidence scoring.
"""
from __future__ import annotations
import os
import json
import logging
import anthropic

logger = logging.getLogger(__name__)

# Lead/buying signal keywords
LEAD_SIGNALS = [
    'meeting', 'reunião', 'call', 'ligação', 'demo', 'demonstração',
    'price', 'preço', 'pricing', 'quanto custa', 'how much', 'budget',
    'orçamento', 'proposal', 'proposta', 'hire', 'contratar', 'contract',
    'contrato', 'interested', 'interessado', 'schedule', 'agendar',
    'available', 'disponível', 'quote', 'cotação', 'work together',
    'trabalhar juntos', 'your services', 'seus serviços',
]

PLATFORM_TONE = {
    'instagram': 'casual, friendly, use 1-2 emojis, keep under 150 chars',
    'linkedin': 'professional, authoritative, no emojis, under 300 chars',
    'x': 'punchy, direct, conversational, under 250 chars',
    'youtube': 'helpful, educational, appreciative, under 200 chars',
}

CESAR_PERSONA = """You are Cesar Schneider, founder of Eworks Labs — an AI agency that helps businesses automate operations with AI.
You are: direct, technical but accessible, genuinely helpful, never salesy.
You build authority through value, not promotion.
Always reply as yourself — authentic, human, no corporate speak."""


class ReplyGenerator:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY', ''))
        self.logger = logging.getLogger(self.__class__.__name__)

    def detect_lead_signal(self, text: str) -> tuple[bool, str]:
        """
        Check if text contains buying/meeting signals.
        Returns (is_lead, signal_phrase).
        """
        text_lower = text.lower()
        for signal in LEAD_SIGNALS:
            if signal in text_lower:
                return True, signal
        return False, ''

    def detect_language(self, text: str) -> str:
        """Simple language detection: 'pt' or 'en'."""
        pt_indicators = [
            'você', 'que', 'não', 'com', 'uma', 'para', 'como',
            'obrigado', 'oi', 'olá', 'por', 'isso', 'muito',
        ]
        text_lower = text.lower()
        pt_count = sum(1 for w in pt_indicators if f' {w} ' in f' {text_lower} ')
        return 'pt' if pt_count >= 2 else 'en'

    def analyze_sentiment(self, text: str) -> str:
        """Simple keyword-based sentiment analysis."""
        positive = [
            'great', 'amazing', 'love', 'excellent', 'helpful', 'thanks',
            'thank', 'awesome', 'good', 'interesting', 'ótimo', 'incrível',
            'obrigado', 'excelente', 'adorei', 'gostei',
        ]
        negative = [
            'bad', 'terrible', 'hate', 'useless', 'spam', 'stop',
            'awful', 'worst', 'horrible', 'ruim', 'péssimo', 'odeio',
        ]
        text_lower = text.lower()
        pos = sum(1 for w in positive if w in text_lower)
        neg = sum(1 for w in negative if w in text_lower)
        if neg > 0:
            return 'negative'
        if pos > 0:
            return 'positive'
        return 'neutral'

    def generate_reply(
        self,
        content: str,
        platform: str,
        language: str = 'en',
        thread_context: str = None,
        post_topic: str = None,
        author_name: str = None,
    ) -> dict:
        """
        Generate a reply using Claude.
        Returns {
            reply: str,
            confidence: float (0.0-1.0),
            is_lead: bool,
            lead_signal: str,
            sentiment: str,
            language: str,
            should_escalate: bool,
            escalate_reason: str
        }
        """
        # Auto-detect language
        detected_lang = self.detect_language(content)
        language = detected_lang

        # Detect lead signals
        is_lead, lead_signal = self.detect_lead_signal(content)

        # Analyze sentiment
        sentiment = self.analyze_sentiment(content)

        tone = PLATFORM_TONE.get(platform, 'professional, helpful')
        lang_instruction = 'Brazilian Portuguese (PT-BR)' if language == 'pt' else 'English'
        context_block = f'\nConversation context: {thread_context}' if thread_context else ''
        topic_block = f'\nPost topic: {post_topic}' if post_topic else ''
        author_block = f'\nAuthor name: {author_name}' if author_name else ''

        prompt = f"""Reply to this {platform} comment/message.

Comment: "{content}"
{context_block}{topic_block}{author_block}

Tone: {tone}
Language: {lang_instruction}

Rules:
- Reply as Cesar Schneider naturally
- Add value, don't just acknowledge
- If they ask about AI/automation, give a quick insight
- If they ask about services/pricing, express interest in learning more about their needs (don't quote prices)
- If negative, de-escalate calmly
- Never use: 'Great question!', 'Absolutely!', 'Certainly!'
- Do NOT mention Eworks Labs unless directly asked

Return JSON:
{{
  "reply": "<the reply text>",
  "confidence": <0.0-1.0>,
  "escalate": <true/false>,
  "escalate_reason": "<reason if escalate=true, else empty string>"
}}"""

        try:
            msg = self.client.messages.create(
                model='claude-opus-4-5',
                max_tokens=500,
                system=CESAR_PERSONA,
                messages=[{'role': 'user', 'content': prompt}]
            )
            raw = msg.content[0].text.strip()
            if '```' in raw:
                raw = raw.split('```')[1].replace('json', '').strip()
            data = json.loads(raw)

            reply = data.get('reply', '')[:500]
            confidence = float(data.get('confidence', 0.7))
            should_escalate = bool(data.get('escalate', False))
            escalate_reason = data.get('escalate_reason', '')

            # Override: always escalate leads
            if is_lead:
                should_escalate = True
                escalate_reason = f'Lead signal detected: "{lead_signal}"'

            # Override: always escalate negative sentiment
            if sentiment == 'negative':
                should_escalate = True
                escalate_reason = escalate_reason or 'Negative sentiment detected'

            return {
                'reply': reply,
                'confidence': confidence,
                'is_lead': is_lead,
                'lead_signal': lead_signal,
                'sentiment': sentiment,
                'language': language,
                'should_escalate': should_escalate,
                'escalate_reason': escalate_reason,
            }

        except Exception as e:
            self.logger.error('Reply generation failed: %s', e)
            return {
                'reply': '',
                'confidence': 0.0,
                'is_lead': is_lead,
                'lead_signal': lead_signal,
                'sentiment': sentiment,
                'language': language,
                'should_escalate': True,
                'escalate_reason': f'Generation error: {e}',
            }

    def generate_lead_opener(
        self, content: str, author_name: str, platform: str, language: str = 'en'
    ) -> str:
        """Generate a suggested opener for Cesar to use when jumping into a lead conversation."""
        lang_instruction = 'Brazilian Portuguese' if language == 'pt' else 'English'
        prompt = (
            f'Generate a short, natural message opener for Cesar Schneider to personally\n'
            f'follow up with {author_name} on {platform} who wrote: "{content[:200]}"\n\n'
            f'Language: {lang_instruction}\n'
            f'Style: Personal, warm, direct. Acknowledge their message. Invite to a quick call.\n'
            f'Max 200 characters. Return ONLY the message text.'
        )
        try:
            msg = self.client.messages.create(
                model='claude-haiku-4-5',
                max_tokens=150,
                messages=[{'role': 'user', 'content': prompt}]
            )
            return msg.content[0].text.strip()[:200]
        except Exception:
            return (
                f'Hi {author_name}, thanks for reaching out! '
                f'Would love to connect and learn more about your needs.'
            )
