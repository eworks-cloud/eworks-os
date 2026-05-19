"""Social media posting — YouTube + Instagram Reels."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

INSTAGRAM_API_BASE = "https://graph.facebook.com/v19.0"


class YouTubePoster:
    """Posts videos to YouTube using OAuth2 + Google API client."""

    def __init__(self, token_path: str = "config/youtube_token.json"):
        self.token_path = Path(token_path)
        self.logger = logging.getLogger(self.__class__.__name__)

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list[str] | None = None,
        privacy: str = "private",
    ) -> dict[str, Any]:
        """Upload a video to YouTube.

        Args:
            video_path: Local path to the MP4 file
            title: Video title
            description: Video description
            tags: List of tags
            privacy: 'private', 'unlisted', or 'public'

        Returns:
            Dict with video_id, youtube_url, status
        """
        if not self.token_path.exists():
            self.logger.warning("YouTube token not found at %s — skipping upload", self.token_path)
            return {"status": "needs_auth", "token_path": str(self.token_path)}

        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
        except ImportError:
            self.logger.error("google-api-python-client not installed")
            return {"status": "missing_dependency", "package": "google-api-python-client"}

        token_data = json.loads(self.token_path.read_text())
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/youtube.upload"]),
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Persist refreshed token
            token_data["token"] = creds.token
            self.token_path.write_text(json.dumps(token_data, indent=2))

        youtube = build("youtube", "v3", credentials=creds)

        video_file = Path(video_path)
        if not video_file.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        body = {
            "snippet": {
                "title": title[:100],
                "description": description,
                "tags": tags or [],
                "categoryId": "28",  # Science & Technology
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            str(video_file),
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 8,  # 8MB chunks
        )

        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media,
        )

        response = None
        self.logger.info("Uploading to YouTube: %s", title)
        while response is None:
            _, response = request.next_chunk()

        video_id = response.get("id", "")
        youtube_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
        self.logger.info("YouTube upload complete: %s", youtube_url)
        return {"video_id": video_id, "youtube_url": youtube_url, "status": "posted"}


class InstagramPoster:
    """Posts Reels to Instagram via Meta Graph API."""

    def __init__(self, access_token: str = "", ig_user_id: str = ""):
        self.access_token = access_token or os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
        self.ig_user_id = ig_user_id or os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
        self.logger = logging.getLogger(self.__class__.__name__)

    async def upload_to_cdn(self, local_path: str) -> str:
        """Upload a local file to file.io and return the public URL.

        Args:
            local_path: Local path to the video file

        Returns:
            Public URL of the uploaded file
        """
        file_path = Path(local_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {local_path}")

        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            form.add_field(
                "file",
                open(local_path, "rb"),
                filename=file_path.name,
                content_type="video/mp4",
            )
            async with session.post("https://file.io", data=form) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    raise RuntimeError(f"file.io upload failed ({resp.status}): {text}")
                data = await resp.json()
                link = data.get("link", "")
                if not link:
                    raise RuntimeError(f"No link in file.io response: {data}")
                self.logger.info("Uploaded to CDN: %s", link)
                return link

    async def post_reel(self, video_url: str, caption: str) -> dict[str, Any]:
        """Post a Reel to Instagram.

        Args:
            video_url: Public URL of the video (must be accessible by Meta)
            caption: Instagram caption (max 2200 chars, up to 30 hashtags)

        Returns:
            Dict with post_id, instagram_url, status
        """
        if not self.access_token or not self.ig_user_id:
            self.logger.warning("Instagram credentials not set — skipping post")
            return {"status": "needs_auth"}

        async with aiohttp.ClientSession() as session:
            # Step 1: Create media container
            self.logger.info("Creating Instagram Reel container...")
            async with session.post(
                f"{INSTAGRAM_API_BASE}/{self.ig_user_id}/media",
                params={
                    "access_token": self.access_token,
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": caption[:2200],
                    "share_to_feed": "true",
                },
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Instagram create container failed ({resp.status}): {text}")
                data = await resp.json()
                container_id = data.get("id")
                if not container_id:
                    raise RuntimeError(f"No container id in response: {data}")

            # Step 2: Poll until container is FINISHED
            self.logger.info("Waiting for container %s to be ready...", container_id)
            container_id = await self._poll_container(session, container_id)

            # Step 3: Publish
            self.logger.info("Publishing Reel container %s...", container_id)
            async with session.post(
                f"{INSTAGRAM_API_BASE}/{self.ig_user_id}/media_publish",
                params={
                    "access_token": self.access_token,
                    "creation_id": container_id,
                },
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Instagram publish failed ({resp.status}): {text}")
                data = await resp.json()
                post_id = data.get("id", "")

        instagram_url = (
            f"https://www.instagram.com/reel/{post_id}/" if post_id else ""
        )
        self.logger.info("Instagram Reel posted: %s", instagram_url)
        return {"post_id": post_id, "instagram_url": instagram_url, "status": "posted"}

    async def _poll_container(
        self,
        session: aiohttp.ClientSession,
        container_id: str,
        poll_interval: int = 15,
        max_wait: int = 600,  # 10 minutes
    ) -> str:
        """Poll Instagram container until status is FINISHED."""
        elapsed = 0
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            async with session.get(
                f"{INSTAGRAM_API_BASE}/{container_id}",
                params={
                    "access_token": self.access_token,
                    "fields": "status_code,status",
                },
            ) as resp:
                if resp.status != 200:
                    self.logger.warning("Container poll failed (%s), retrying...", resp.status)
                    continue
                data = await resp.json()
                status_code = data.get("status_code", "")
                self.logger.debug("Container %s status: %s (elapsed=%ds)", container_id, status_code, elapsed)
                if status_code == "FINISHED":
                    return container_id
                elif status_code in ("ERROR", "EXPIRED"):
                    raise RuntimeError(f"Instagram container {container_id} failed: {data}")

        raise TimeoutError(f"Instagram container {container_id} not ready after {max_wait}s")
