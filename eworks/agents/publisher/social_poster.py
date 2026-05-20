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

    def _build_youtube_service(self):
        """Build and return authenticated YouTube API service."""
        if not self.token_path.exists():
            return None
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
        except ImportError:
            self.logger.error("google-api-python-client not installed")
            return None
        import json as _json
        token_data = _json.loads(self.token_path.read_text())
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/youtube"]),
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_data["token"] = creds.token
            self.token_path.write_text(_json.dumps(token_data, indent=2))
        return build("youtube", "v3", credentials=creds)

    def set_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        """
        Set a custom AI-generated thumbnail for a YouTube video.
        Requires thumbnails.set OAuth scope.
        """
        youtube = self._build_youtube_service()
        if not youtube:
            self.logger.warning("YouTube service unavailable — skipping thumbnail set")
            return False
        try:
            from googleapiclient.http import MediaFileUpload
        except ImportError:
            self.logger.error("google-api-python-client not installed")
            return False
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path),
            ).execute()
            self.logger.info("Thumbnail set for video %s", video_id)
            return True
        except Exception as exc:
            self.logger.error("set_thumbnail failed: %s", exc)
            return False

    def add_to_playlist(self, video_id: str, playlist_id: str = None, playlist_title: str = "Eworks Labs") -> dict:
        """
        Add a video to a playlist. Creates playlist if it doesn't exist.
        Returns {playlist_id, playlist_title, status}
        """
        youtube = self._build_youtube_service()
        if not youtube:
            return {"status": "needs_auth"}
        try:
            # Find or create playlist
            if not playlist_id:
                # Search existing playlists
                resp = youtube.playlists().list(part="snippet", mine=True, maxResults=50).execute()
                for item in resp.get("items", []):
                    if item["snippet"]["title"] == playlist_title:
                        playlist_id = item["id"]
                        break
                # Create if not found
                if not playlist_id:
                    new_pl = youtube.playlists().insert(
                        part="snippet,status",
                        body={
                            "snippet": {"title": playlist_title, "description": f"Playlist: {playlist_title}"},
                            "status": {"privacyStatus": "public"},
                        },
                    ).execute()
                    playlist_id = new_pl["id"]
                    self.logger.info("Created YouTube playlist: %s (%s)", playlist_title, playlist_id)
            # Add video to playlist
            youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id},
                    }
                },
            ).execute()
            self.logger.info("Added video %s to playlist %s", video_id, playlist_id)
            return {"playlist_id": playlist_id, "playlist_title": playlist_title, "status": "added"}
        except Exception as exc:
            self.logger.error("add_to_playlist failed: %s", exc)
            return {"playlist_id": playlist_id, "playlist_title": playlist_title, "status": "error", "error": str(exc)}

    def set_scheduled_publish(self, video_id: str, publish_at: str) -> bool:
        """
        Schedule a video to go public at a specific time.
        publish_at: ISO8601 datetime string e.g. '2026-06-01T09:00:00Z'
        Updates video status to publishAt=publish_at, privacyStatus=private
        Returns True on success
        """
        youtube = self._build_youtube_service()
        if not youtube:
            return False
        try:
            youtube.videos().update(
                part="status",
                body={
                    "id": video_id,
                    "status": {
                        "privacyStatus": "private",
                        "publishAt": publish_at,
                    },
                },
            ).execute()
            self.logger.info("Scheduled video %s to publish at %s", video_id, publish_at)
            return True
        except Exception as exc:
            self.logger.error("set_scheduled_publish failed: %s", exc)
            return False

    def upload_captions(self, video_id: str, srt_content: str, language: str = "en", name: str = "Auto-generated") -> dict:
        """
        Upload SRT captions/subtitles to a YouTube video.
        Returns {caption_id, status}
        """
        youtube = self._build_youtube_service()
        if not youtube:
            return {"status": "needs_auth"}
        try:
            import io
            from googleapiclient.http import MediaIoBaseUpload
            srt_bytes = srt_content.encode("utf-8")
            media = MediaIoBaseUpload(io.BytesIO(srt_bytes), mimetype="text/plain", resumable=False)
            resp = youtube.captions().insert(
                part="snippet",
                body={
                    "snippet": {
                        "videoId": video_id,
                        "language": language,
                        "name": name,
                        "isDraft": False,
                    }
                },
                media_body=media,
            ).execute()
            caption_id = resp.get("id", "")
            self.logger.info("Captions uploaded for video %s: %s", video_id, caption_id)
            return {"caption_id": caption_id, "status": "uploaded"}
        except Exception as exc:
            self.logger.error("upload_captions failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    def get_video_analytics(self, video_id: str) -> dict:
        """
        Fetch video analytics: views, likes, comments, watch_time.
        Uses YouTube Analytics API (youtubeAnalytics v2).
        Returns {views, likes, comments, average_view_duration, status}
        Note: Graceful fallback if Analytics API not authorized.
        """
        youtube = self._build_youtube_service()
        if not youtube:
            return {"status": "needs_auth"}
        try:
            # First get basic stats from videos.list
            resp = youtube.videos().list(part="statistics", id=video_id).execute()
            items = resp.get("items", [])
            if not items:
                return {"status": "not_found", "video_id": video_id}
            stats = items[0].get("statistics", {})
            result = {
                "video_id": video_id,
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "average_view_duration": 0,
                "status": "ok",
            }
            # Try YouTube Analytics API for watch time
            try:
                from googleapiclient.discovery import build as _build
                import json as _json
                token_data = _json.loads(self.token_path.read_text())
                from google.oauth2.credentials import Credentials
                creds = Credentials(
                    token=token_data.get("token"),
                    refresh_token=token_data.get("refresh_token"),
                    token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                    client_id=token_data.get("client_id"),
                    client_secret=token_data.get("client_secret"),
                    scopes=token_data.get("scopes", []),
                )
                analytics = _build("youtubeAnalytics", "v2", credentials=creds)
                from datetime import date, timedelta
                end_date = date.today().isoformat()
                start_date = (date.today() - timedelta(days=90)).isoformat()
                a_resp = analytics.reports().query(
                    ids=f"channel==MINE",
                    startDate=start_date,
                    endDate=end_date,
                    metrics="estimatedMinutesWatched,averageViewDuration",
                    filters=f"video=={video_id}",
                ).execute()
                rows = a_resp.get("rows", [])
                if rows:
                    result["watch_time_minutes"] = rows[0][0]
                    result["average_view_duration"] = rows[0][1]
            except Exception as analytics_exc:
                self.logger.debug("Analytics API unavailable (graceful): %s", analytics_exc)
            return result
        except Exception as exc:
            self.logger.error("get_video_analytics failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    def make_youtube_short(self, video_path: str, title: str, description: str, tags: list = None) -> dict:
        """
        Upload a Shorts video (vertical 9:16, max 60s).
        Adds #Shorts to title and description automatically.
        Returns same as upload_video.
        """
        short_title = f"{title[:90]} #Shorts"
        short_desc = f"#Shorts\n\n{description}"
        return self.upload_video(
            video_path, short_title, short_desc,
            tags=(tags or []) + ["Shorts", "YouTubeShorts"],
            privacy="public",
        )


class InstagramPoster:
    """Posts Reels to Instagram via Meta Graph API."""

    def __init__(self, access_token: str = "", ig_user_id: str = ""):
        self.access_token = access_token or os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
        self.ig_user_id = ig_user_id or os.environ.get("INSTAGRAM_ACCOUNT_ID", "")
        self.logger = logging.getLogger(self.__class__.__name__)

    async def upload_to_cdn(self, local_path: str) -> str:
        """Upload a local file to file.io and return the public URL. (video alias for backward compat)"""
        return await self.upload_video_to_cdn(local_path)

    async def upload_video_to_cdn(self, local_path: str) -> str:
        """Upload a local video file to file.io and return the public URL.

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

    async def upload_file_to_cdn(self, local_path: str) -> str:
        """Upload any file (image or video) to file.io CDN."""
        file_path = Path(local_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {local_path}")
        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            content_type = "image/jpeg" if local_path.endswith((".jpg", ".jpeg", ".png")) else "video/mp4"
            form.add_field("file", open(local_path, "rb"), filename=file_path.name, content_type=content_type)
            async with session.post("https://file.io", data=form) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    raise RuntimeError(f"file.io upload failed ({resp.status}): {text}")
                data = await resp.json()
                link = data.get("link", "")
                if not link:
                    raise RuntimeError(f"CDN upload failed: {data}")
                self.logger.info("Uploaded to CDN: %s", link)
                return link

    async def post_image(self, image_path: str, caption: str) -> dict:
        """Post a single image to Instagram feed.
        Uploads to file.io CDN first, then posts via Graph API.
        """
        if not self.access_token or not self.ig_user_id:
            return {"status": "needs_auth"}
        # Upload to CDN
        image_url = await self.upload_file_to_cdn(image_path)
        async with aiohttp.ClientSession() as session:
            # Step 1: Create container
            async with session.post(
                f"{INSTAGRAM_API_BASE}/{self.ig_user_id}/media",
                params={
                    "access_token": self.access_token,
                    "image_url": image_url,
                    "caption": caption[:2200],
                },
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Instagram image container failed ({resp.status}): {text}")
                data = await resp.json()
                container_id = data.get("id")
                if not container_id:
                    raise RuntimeError(f"Instagram image container failed: {data}")
            # Step 2: Poll
            await self._poll_container(session, container_id)
            # Step 3: Publish
            async with session.post(
                f"{INSTAGRAM_API_BASE}/{self.ig_user_id}/media_publish",
                params={"access_token": self.access_token, "creation_id": container_id},
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Instagram publish failed ({resp.status}): {text}")
                data = await resp.json()
                post_id = data.get("id", "")
        post_url = f"https://www.instagram.com/p/{post_id}/" if post_id else ""
        self.logger.info("Instagram image posted: %s", post_url)
        return {"post_id": post_id, "instagram_url": post_url, "status": "posted", "type": "image"}

    async def post_carousel(self, image_paths: list[str], caption: str) -> dict:
        """Post a carousel (album) of images to Instagram. Max 10 images."""
        if not self.access_token or not self.ig_user_id:
            return {"status": "needs_auth"}
        image_paths = image_paths[:10]  # Instagram max
        async with aiohttp.ClientSession() as session:
            # Step 1: Create individual item containers
            item_ids = []
            for img_path in image_paths:
                image_url = await self.upload_file_to_cdn(img_path)
                async with session.post(
                    f"{INSTAGRAM_API_BASE}/{self.ig_user_id}/media",
                    params={
                        "access_token": self.access_token,
                        "image_url": image_url,
                        "is_carousel_item": "true",
                    },
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        item_id = data.get("id")
                        if item_id:
                            item_ids.append(item_id)
                await asyncio.sleep(1)
            # Step 2: Create carousel container
            async with session.post(
                f"{INSTAGRAM_API_BASE}/{self.ig_user_id}/media",
                params={
                    "access_token": self.access_token,
                    "media_type": "CAROUSEL",
                    "children": ",".join(item_ids),
                    "caption": caption[:2200],
                },
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Carousel container failed ({resp.status}): {text}")
                data = await resp.json()
                carousel_id = data.get("id")
                if not carousel_id:
                    raise RuntimeError(f"Carousel container failed: {data}")
            # Step 3: Poll + publish
            await self._poll_container(session, carousel_id)
            async with session.post(
                f"{INSTAGRAM_API_BASE}/{self.ig_user_id}/media_publish",
                params={"access_token": self.access_token, "creation_id": carousel_id},
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Instagram carousel publish failed ({resp.status}): {text}")
                data = await resp.json()
                post_id = data.get("id", "")
        post_url = f"https://www.instagram.com/p/{post_id}/" if post_id else ""
        self.logger.info("Instagram carousel posted: %s", post_url)
        return {"post_id": post_id, "instagram_url": post_url, "status": "posted", "type": "carousel", "images_count": len(item_ids)}

    async def get_post_analytics(self, post_id: str) -> dict:
        """Fetch analytics for an Instagram post."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{INSTAGRAM_API_BASE}/{post_id}/insights",
                params={
                    "access_token": self.access_token,
                    "metric": "impressions,reach,likes,comments,shares,saved",
                },
            ) as resp:
                if resp.status != 200:
                    return {"status": "unavailable", "post_id": post_id}
                data = await resp.json()
                metrics = {item["name"]: item.get("values", [{}])[0].get("value", 0) for item in data.get("data", [])}
                return {
                    "post_id": post_id,
                    "impressions": metrics.get("impressions", 0),
                    "reach": metrics.get("reach", 0),
                    "likes": metrics.get("likes", 0),
                    "comments": metrics.get("comments", 0),
                    "shares": metrics.get("shares", 0),
                    "saved": metrics.get("saved", 0),
                    "status": "ok",
                }

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
