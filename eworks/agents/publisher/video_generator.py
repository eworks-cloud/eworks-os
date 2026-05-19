"""HeyGen video generation agent."""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

import aiohttp

from eworks.agents.publisher.base_publisher import BasePublisher

logger = logging.getLogger(__name__)

AVATAR_ID = "494ce8a1dbe64573a4cb1684ad0e0e14"
VOICE_ID = "c0a044792fc64b3fa7dfc0700da93016"

HEYGEN_API_BASE = "https://api.heygen.com"
HEYGEN_UPLOAD_BASE = "https://upload.heygen.com"


class HeyGenAgent(BasePublisher):
    """Generates videos via HeyGen API using avatar and optional audio assets."""

    AVATAR_ID = AVATAR_ID
    VOICE_ID = VOICE_ID

    def _headers(self) -> dict[str, str]:
        return {
            "X-Api-Key": self.heygen_api_key,
            "Content-Type": "application/json",
        }

    def _get_dimensions(self, fmt: str) -> tuple[int, int]:
        """Return (width, height) for the given format."""
        if fmt == "reel":
            return (1080, 1920)
        return (1920, 1080)  # youtube

    async def generate_video(
        self,
        script_text: str,
        format: str = "reel",
        audio_asset_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate a HeyGen video from script text.

        Args:
            script_text: The script/text for the avatar to speak
            format: 'reel' (1080x1920) or 'youtube' (1920x1080)
            audio_asset_id: Optional ElevenLabs audio asset ID uploaded to HeyGen

        Returns:
            Dict with video_id, video_url, local_path, format
        """
        width, height = self._get_dimensions(format)

        if audio_asset_id:
            voice_config = {
                "type": "audio",
                "audio_asset_id": audio_asset_id,
            }
        else:
            voice_config = {
                "type": "text",
                "voice_id": self.VOICE_ID,
                "input_text": script_text,
            }

        payload = {
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": self.AVATAR_ID,
                        "avatar_style": "normal",
                    },
                    "voice": voice_config,
                    "background": {
                        "type": "color",
                        "value": "#1a1a2e",
                    },
                }
            ],
            "dimension": {"width": width, "height": height},
            "aspect_ratio": None,
            "test": False,
        }

        async with aiohttp.ClientSession() as session:
            # Submit video generation
            async with session.post(
                f"{HEYGEN_API_BASE}/v2/video/generate",
                json=payload,
                headers=self._headers(),
            ) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    raise RuntimeError(f"HeyGen generate failed ({resp.status}): {text}")
                data = await resp.json()
                video_id = data.get("data", {}).get("video_id") or data.get("video_id")
                if not video_id:
                    raise RuntimeError(f"No video_id in HeyGen response: {data}")

            logger.info("HeyGen video submitted: %s (format=%s)", video_id, format)

            # Poll for completion
            video_url = await self._poll_video(session, video_id)

            # Download the video
            local_path = await self._download_video(session, video_id, video_url)

        return {
            "video_id": video_id,
            "video_url": video_url,
            "local_path": str(local_path),
            "format": format,
            "width": width,
            "height": height,
        }

    async def _poll_video(
        self,
        session: aiohttp.ClientSession,
        video_id: str,
        poll_interval: int = 10,
        max_wait: int = 1200,  # 20 minutes
    ) -> str:
        """Poll HeyGen until video is complete. Returns video URL."""
        elapsed = 0
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            async with session.get(
                f"{HEYGEN_API_BASE}/v1/video_status.get",
                params={"video_id": video_id},
                headers=self._headers(),
            ) as resp:
                if resp.status != 200:
                    logger.warning("HeyGen status check failed (%s), retrying...", resp.status)
                    continue
                data = await resp.json()
                video_data = data.get("data", {})
                status = video_data.get("status", "")
                logger.debug("HeyGen video %s status: %s (elapsed=%ds)", video_id, status, elapsed)

                if status == "completed":
                    video_url = video_data.get("video_url", "")
                    if not video_url:
                        raise RuntimeError(f"HeyGen completed but no video_url: {data}")
                    logger.info("HeyGen video %s completed: %s", video_id, video_url)
                    return video_url
                elif status == "failed":
                    error = video_data.get("error", "Unknown error")
                    raise RuntimeError(f"HeyGen video generation failed: {error}")

        raise TimeoutError(f"HeyGen video {video_id} did not complete within {max_wait}s")

    async def _download_video(
        self,
        session: aiohttp.ClientSession,
        video_id: str,
        video_url: str,
    ) -> Path:
        """Download the completed video to data/videos/{video_id}.mp4."""
        local_path = self.videos_dir / f"{video_id}.mp4"
        async with session.get(video_url) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Failed to download video: HTTP {resp.status}")
            with open(local_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(8192):
                    f.write(chunk)
        logger.info("Downloaded video to %s", local_path)
        return local_path

    async def upload_audio(self, audio_path: str) -> str:
        """Upload an audio file to HeyGen as an asset.

        Args:
            audio_path: Local path to the MP3 audio file

        Returns:
            HeyGen asset_id string
        """
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        with open(audio_file, "rb") as f:
            audio_bytes = f.read()

        headers = {
            "X-Api-Key": self.heygen_api_key,
            "Content-Type": "audio/mpeg",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{HEYGEN_UPLOAD_BASE}/v1/asset",
                data=audio_bytes,
                headers=headers,
            ) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    raise RuntimeError(f"HeyGen audio upload failed ({resp.status}): {text}")
                data = await resp.json()
                asset_id = data.get("data", {}).get("id") or data.get("id")
                if not asset_id:
                    raise RuntimeError(f"No asset_id in HeyGen upload response: {data}")
                logger.info("Uploaded audio to HeyGen: asset_id=%s", asset_id)
                return asset_id

    async def check_credits(self) -> dict[str, Any]:
        """Check remaining HeyGen credits/quota."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{HEYGEN_API_BASE}/v2/user/remaining_quota",
                headers=self._headers(),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"HeyGen credits check failed ({resp.status}): {text}")
                data = await resp.json()
                return data.get("data", data)

    async def run(self, campaign_id: int) -> dict:
        """Run video generation for pending posts."""
        credits = await self.check_credits()
        return {"status": "ok", "credits": credits, "campaign_id": campaign_id}
