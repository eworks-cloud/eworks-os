"""
LinkedIn posting via official API.
Supports text, image, video and carousel posts.
"""
from __future__ import annotations
import os
import json
import logging
import requests
import time
from pathlib import Path

LINKEDIN_API = "https://api.linkedin.com/v2"


class LinkedInPoster:
    """Posts content to LinkedIn via ugcPosts API."""

    def __init__(self):
        self.access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
        self.person_urn = os.environ.get("LINKEDIN_PERSON_URN", "")  # urn:li:person:{id}
        self.logger = logging.getLogger(self.__class__.__name__)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def get_person_urn(self) -> str:
        """Fetch and cache the authenticated user's URN."""
        resp = requests.get(f"{LINKEDIN_API}/me", headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        person_id = data.get("id", "")
        urn = f"urn:li:person:{person_id}"
        self.logger.info("Person URN: %s", urn)
        return urn

    def post_text(self, text: str, visibility: str = "PUBLIC") -> dict:
        """Post a text-only post to LinkedIn."""
        if not self.access_token:
            return {"status": "needs_auth"}
        author = self.person_urn or self.get_person_urn()
        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text[:3000]},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": visibility},
        }
        resp = requests.post(f"{LINKEDIN_API}/ugcPosts", json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        post_id = resp.headers.get("x-restli-id", "")
        post_url = f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else ""
        self.logger.info("LinkedIn text post: %s", post_url)
        return {"post_urn": post_id, "post_url": post_url, "status": "posted"}

    def _register_image_upload(self) -> tuple[str, str]:
        """Register image upload with LinkedIn. Returns (upload_url, asset_urn)."""
        author = self.person_urn or self.get_person_urn()
        payload = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": author,
                "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}],
            }
        }
        resp = requests.post(
            f"{LINKEDIN_API}/assets?action=registerUpload",
            json=payload, headers=self._headers(), timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        upload_url = data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_urn = data["value"]["asset"]
        return upload_url, asset_urn

    def _upload_image_binary(self, upload_url: str, image_path: str) -> None:
        """Upload image binary to LinkedIn upload URL."""
        with open(image_path, "rb") as f:
            image_data = f.read()
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/octet-stream",
        }
        resp = requests.put(upload_url, data=image_data, headers=headers, timeout=60)
        resp.raise_for_status()

    def post_image(self, text: str, image_path: str, visibility: str = "PUBLIC") -> dict:
        """Post image + caption to LinkedIn."""
        if not self.access_token:
            return {"status": "needs_auth"}
        author = self.person_urn or self.get_person_urn()
        # Register + upload
        upload_url, asset_urn = self._register_image_upload()
        self._upload_image_binary(upload_url, image_path)
        time.sleep(2)  # Allow LinkedIn to process
        # Post
        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text[:3000]},
                    "shareMediaCategory": "IMAGE",
                    "media": [{
                        "status": "READY",
                        "description": {"text": ""},
                        "media": asset_urn,
                        "title": {"text": ""},
                    }],
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": visibility},
        }
        resp = requests.post(f"{LINKEDIN_API}/ugcPosts", json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        post_id = resp.headers.get("x-restli-id", "")
        post_url = f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else ""
        return {"post_urn": post_id, "post_url": post_url, "asset_urn": asset_urn, "status": "posted"}

    def _register_video_upload(self) -> tuple[str, str]:
        """Register video upload. Returns (upload_url, asset_urn)."""
        author = self.person_urn or self.get_person_urn()
        payload = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-video"],
                "owner": author,
                "serviceRelationships": [{"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}],
                "supportedUploadMechanism": ["MULTIPART_UPLOAD"],
            }
        }
        resp = requests.post(
            f"{LINKEDIN_API}/assets?action=registerUpload",
            json=payload, headers=self._headers(), timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        upload_url = data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_urn = data["value"]["asset"]
        return upload_url, asset_urn

    def post_video(self, text: str, video_path: str, visibility: str = "PUBLIC") -> dict:
        """Post video to LinkedIn with native upload."""
        if not self.access_token:
            return {"status": "needs_auth"}
        author = self.person_urn or self.get_person_urn()
        upload_url, asset_urn = self._register_video_upload()
        # Upload video binary
        with open(video_path, "rb") as f:
            video_data = f.read()
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/octet-stream",
        }
        resp = requests.put(upload_url, data=video_data, headers=headers, timeout=300)
        resp.raise_for_status()
        time.sleep(3)
        # Post
        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text[:3000]},
                    "shareMediaCategory": "VIDEO",
                    "media": [{
                        "status": "READY",
                        "media": asset_urn,
                        "title": {"text": ""},
                    }],
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": visibility},
        }
        resp = requests.post(f"{LINKEDIN_API}/ugcPosts", json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        post_id = resp.headers.get("x-restli-id", "")
        post_url = f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else ""
        return {"post_urn": post_id, "post_url": post_url, "asset_urn": asset_urn, "status": "posted"}

    def post_carousel(self, text: str, image_paths: list[str], visibility: str = "PUBLIC") -> dict:
        """Post carousel (multi-image) to LinkedIn. Max 9 images."""
        if not self.access_token:
            return {"status": "needs_auth"}
        author = self.person_urn or self.get_person_urn()
        image_paths = image_paths[:9]  # LinkedIn max
        media_items = []
        for img_path in image_paths:
            upload_url, asset_urn = self._register_image_upload()
            self._upload_image_binary(upload_url, img_path)
            time.sleep(1)
            media_items.append({
                "status": "READY",
                "description": {"text": ""},
                "media": asset_urn,
                "title": {"text": ""},
            })
        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text[:3000]},
                    "shareMediaCategory": "IMAGE",
                    "media": media_items,
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": visibility},
        }
        resp = requests.post(f"{LINKEDIN_API}/ugcPosts", json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        post_id = resp.headers.get("x-restli-id", "")
        post_url = f"https://www.linkedin.com/feed/update/{post_id}/" if post_id else ""
        return {"post_urn": post_id, "post_url": post_url, "status": "posted", "images_count": len(image_paths)}

    def get_post_analytics(self, post_urn: str) -> dict:
        """Fetch analytics for a LinkedIn post."""
        encoded_urn = requests.utils.quote(post_urn, safe="")
        resp = requests.get(
            f"{LINKEDIN_API}/socialActions/{encoded_urn}",
            headers=self._headers(), timeout=30
        )
        if resp.status_code != 200:
            return {"status": "unavailable", "post_urn": post_urn}
        data = resp.json()
        return {
            "post_urn": post_urn,
            "likes": data.get("likesSummary", {}).get("totalLikes", 0),
            "comments": data.get("commentsSummary", {}).get("totalFirstLevelComments", 0),
            "shares": 0,  # Requires org analytics API
            "status": "ok",
        }
