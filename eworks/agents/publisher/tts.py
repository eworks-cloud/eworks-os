"""ElevenLabs TTS agent — EN/PT-BR voice generation."""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

import aiohttp

from eworks.agents.publisher.base_publisher import BasePublisher

logger = logging.getLogger(__name__)

ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"


class ElevenLabsAgent(BasePublisher):
    """Generates text-to-speech audio via ElevenLabs API."""

    VOICES = {
        "en": "ZBvlJFESc5elgHcPVn6l",
        "pt": "r1j1T6R42hIVOIE1SoEr",
    }

    async def generate_audio(
        self,
        text: str,
        language: str = "en",
        output_path: str | None = None,
    ) -> str:
        """Generate audio from text using ElevenLabs.

        Args:
            text: Text to convert to speech
            language: 'en' or 'pt' — selects the voice
            output_path: Optional custom output path; defaults to data/audio/{timestamp}.mp3

        Returns:
            Local file path to the generated MP3
        """
        voice_id = self.VOICES.get(language, self.VOICES["en"])

        if output_path:
            out = Path(output_path)
        else:
            timestamp = int(time.time())
            out = self.audio_dir / f"{timestamp}.mp3"
        out.parent.mkdir(parents=True, exist_ok=True)

        headers = {
            "xi-api-key": self.elevenlabs_api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }

        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.85,
            },
        }

        url = f"{ELEVENLABS_API_BASE}/text-to-speech/{voice_id}"
        await self._generate_with_retry(url, headers, payload, out)
        logger.info("Generated audio: %s (%d chars)", out, len(text))
        return str(out)

    async def _generate_with_retry(
        self,
        url: str,
        headers: dict,
        payload: dict,
        output_path: Path,
        max_attempts: int = 3,
    ) -> None:
        """POST to ElevenLabs with exponential backoff on 429."""
        delay = 2.0
        async with aiohttp.ClientSession() as session:
            for attempt in range(1, max_attempts + 1):
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        audio_bytes = await resp.read()
                        output_path.write_bytes(audio_bytes)
                        return
                    elif resp.status == 429:
                        if attempt == max_attempts:
                            text = await resp.text()
                            raise RuntimeError(
                                f"ElevenLabs rate limit exceeded after {max_attempts} attempts: {text}"
                            )
                        logger.warning(
                            "ElevenLabs 429 rate limit — retrying in %.1fs (attempt %d/%d)",
                            delay,
                            attempt,
                            max_attempts,
                        )
                        await asyncio.sleep(delay)
                        delay *= 2
                    else:
                        text = await resp.text()
                        raise RuntimeError(
                            f"ElevenLabs TTS failed (HTTP {resp.status}): {text}"
                        )

    async def run(self, campaign_id: int) -> dict:
        """Placeholder run — TTS is invoked by orchestrator."""
        return {"status": "ok", "campaign_id": campaign_id}
