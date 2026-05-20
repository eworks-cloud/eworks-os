"""
Social media orchestrator — coordinates content generation and posting
across LinkedIn, Instagram, Threads, and Substack for all content types.
"""
from __future__ import annotations
import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
import os

from eworks.agents.base import BaseAgent
from eworks.agents.publisher.ideation import IdeationAgent
from eworks.agents.publisher.scripting import ScriptingAgent
from eworks.agents.publisher.image_generator import ImageGenerator
from eworks.agents.publisher.video_generator import HeyGenAgent
from eworks.agents.publisher.tts import ElevenLabsAgent
from eworks.agents.publisher.linkedin_poster import LinkedInPoster
from eworks.agents.publisher.social_poster import InstagramPoster
from eworks.agents.publisher.threads_poster import ThreadsPoster
from eworks.agents.publisher.substack_poster import SubstackPoster
from eworks.agents.publisher.analytics import AnalyticsCollector
from eworks.agents.publisher.approval import TelegramApproval
from eworks.agents.prospector.reporter import TelegramReporter


class SocialOrchestrator(BaseAgent):
    """
    Orchestrates full social media content creation and posting.
    Supports: LinkedIn (text/image/video/carousel) + Instagram (image/video/carousel/reel)
              + Threads (text/image/video/carousel) + Substack (article)
    """

    OPTIMAL_HOURS = [8, 9, 10]   # Post 8-10 AM
    OPTIMAL_DAYS = [1, 2, 3]     # Mon, Tue, Wed (0=Mon)
    MAX_LINKEDIN_PER_DAY = 3
    MAX_INSTAGRAM_PER_DAY = 5
    MAX_THREADS_PER_DAY = 5
    MAX_SUBSTACK_PER_WEEK = 3

    def __init__(self, db, config):
        super().__init__(db, config)
        self.ideation = IdeationAgent(db, config)
        self.scripting = ScriptingAgent(db, config)
        self.image_gen = ImageGenerator()
        self.video_gen = HeyGenAgent(db, config)
        self.tts = ElevenLabsAgent(db, config)
        self.linkedin = LinkedInPoster()
        self.instagram = InstagramPoster()
        self.threads = ThreadsPoster()
        self.substack = SubstackPoster()
        self.analytics = AnalyticsCollector(db)
        self.approval = TelegramApproval()
        self.reporter = TelegramReporter(
            bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
        )

    def _save_post(
        self,
        platform: str,
        content_type: str,
        text: str,
        image_path: str = None,
        video_path: str = None,
        carousel_paths: list = None,
        idea_id: int = None,
        script_id: int = None,
    ) -> int:
        """Save a post record to DB and return its ID."""
        conn = self.db.get_connection()
        cursor = conn.execute(
            """INSERT INTO social_posts
            (platform, content_type, text_content, image_path, video_path,
             carousel_paths, idea_id, script_id, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?)""",
            (
                platform,
                content_type,
                text,
                image_path,
                video_path,
                json.dumps(carousel_paths or []),
                idea_id,
                script_id,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        return cursor.lastrowid

    def _update_post_status(
        self,
        post_id: int,
        status: str,
        linkedin_urn: str = None,
        linkedin_url: str = None,
        instagram_id: str = None,
        instagram_url: str = None,
    ) -> None:
        """Update post status and platform-specific IDs."""
        conn = self.db.get_connection()
        conn.execute(
            """UPDATE social_posts SET
            status=?, linkedin_post_urn=?, linkedin_post_url=?,
            instagram_post_id=?, instagram_media_url=?,
            posted_at=? WHERE id=?""",
            (
                status,
                linkedin_urn,
                linkedin_url,
                instagram_id,
                instagram_url,
                datetime.utcnow().isoformat() if status == "posted" else None,
                post_id,
            ),
        )
        conn.commit()

    async def run(self, campaign_id: int = None) -> dict:
        """Default run — generate and post content to all platforms."""
        return await self.post_content(
            platforms=["linkedin", "instagram", "threads", "substack"],
            content_type="image",
        )

    async def post_content(
        self,
        platforms: list[str] = None,
        content_type: str = "image",  # text, image, video, carousel
        language: str = "en",
        topic: str = None,
        auto_approve: bool = False,
        dry_run: bool = False,
    ) -> dict:
        """
        Full pipeline: generate content → approve → post to all requested platforms.

        Args:
            platforms: ["linkedin", "instagram"] or subset
            content_type: text|image|video|carousel
            language: en|pt
            topic: optional specific topic (if None, generates ideas)
            auto_approve: skip Telegram approval
            dry_run: generate content but don't post
        """
        platforms = platforms or ["linkedin", "instagram"]
        # Honour config-level platform toggles
        enabled = {
            "linkedin":  self.config.get("enable_linkedin",  True),
            "instagram": self.config.get("enable_instagram", True),
            "threads":   self.config.get("enable_threads",   False),
            "substack":  self.config.get("enable_substack",  False),
        }
        platforms = [p for p in platforms if enabled.get(p, True)]
        results = {"platforms": platforms, "content_type": content_type, "posts": {}}

        # Step 1: Generate idea + script
        self.logger.info("Generating content idea...")
        if topic:
            idea = {
                "id": None,
                "title": topic,
                "hook": "",
                "angle": "",
                "keywords": [],
                "format": "both",
            }
        else:
            ideas = await self.ideation.generate_ideas(n=3, language=language)
            idea = (
                next((i for i in ideas if i.get("format") in ("long-form", "both")), ideas[0])
                if ideas
                else {
                    "id": None,
                    "title": "AI automation for business",
                    "hook": "",
                    "angle": "",
                    "keywords": [],
                    "format": "both",
                }
            )

        script = None
        if idea.get("id"):
            script = await self.scripting.generate_script(idea["id"], language=language)

        post_text = (
            script.get("instagram_caption", idea["title"])
            if script
            else f"{idea['title']}\n\n{idea.get('hook', '')}"
        )
        linkedin_text = (
            (script.get("youtube_script", "")[:3000] if script else post_text)
            if content_type == "text"
            else post_text
        )

        # Step 2: Generate media based on content_type
        image_path = None
        video_path = None
        carousel_paths = []

        if content_type == "image":
            self.logger.info("Generating AI image...")
            if not dry_run:
                for platform in platforms:
                    img = self.image_gen.generate_for_post(
                        idea["title"], platform=platform, content_type="image"
                    )
                    if not image_path:
                        image_path = img

        elif content_type == "video":
            self.logger.info("Generating HeyGen video...")
            if not dry_run and script:
                reel_script = script.get("reel_script", idea["title"])
                audio_path = await self.tts.generate_audio(reel_script, language=language)
                asset_id = await self.video_gen.upload_audio(audio_path)
                vid_result = await self.video_gen.generate_video(
                    reel_script, format="reel", audio_asset_id=asset_id
                )
                video_path = vid_result.get("local_path")

        elif content_type == "carousel":
            self.logger.info("Generating carousel images...")
            if not dry_run:
                prompts = [
                    f"Slide {i+1}: {idea['title']} — key point {i+1}" for i in range(4)
                ]
                carousel_paths = self.image_gen.generate_batch(prompts, size="square_hd")

        # Step 3: Save draft post
        post_id = self._save_post(
            platform=",".join(platforms),
            content_type=content_type,
            text=linkedin_text if "linkedin" in platforms else post_text,
            image_path=image_path,
            video_path=video_path,
            carousel_paths=carousel_paths,
            idea_id=idea.get("id"),
            script_id=script.get("id") if script else None,
        )

        # Step 4: Approval
        if not auto_approve and not dry_run:
            content_package = {
                "title": idea["title"],
                "reel_script": post_text[:300],
                "instagram_caption": post_text,
                "youtube_title": idea["title"],
                "content_type": content_type,
                "platforms": ", ".join(platforms),
                "post_id": post_id,
            }
            decision = await self.approval.send_approval_request(content_package)
            if decision != "approved":
                self._update_post_status(post_id, "failed")
                return {**results, "status": "rejected", "post_id": post_id}

        if dry_run:
            return {
                **results,
                "status": "dry_run",
                "post_id": post_id,
                "text_preview": post_text[:200],
                "idea": idea["title"],
            }

        # Step 5: Post to each platform
        self._update_post_status(post_id, "posting")
        posted_urls = {}

        if "linkedin" in platforms:
            try:
                if content_type == "text":
                    res = self.linkedin.post_text(linkedin_text)
                elif content_type == "image" and image_path:
                    res = self.linkedin.post_image(linkedin_text, image_path)
                elif content_type == "video" and video_path:
                    res = self.linkedin.post_video(linkedin_text, video_path)
                elif content_type == "carousel" and carousel_paths:
                    res = self.linkedin.post_carousel(linkedin_text, carousel_paths)
                else:
                    res = self.linkedin.post_text(linkedin_text)
                posted_urls["linkedin"] = res.get("post_url", "")
                results["posts"]["linkedin"] = res
            except Exception as e:
                self.logger.error("LinkedIn post failed: %s", e)
                results["posts"]["linkedin"] = {"status": "failed", "error": str(e)}

        if "instagram" in platforms:
            try:
                if content_type == "image" and image_path:
                    res = await self.instagram.post_image(image_path, post_text)
                elif content_type == "video" and video_path:
                    video_url = await self.instagram.upload_file_to_cdn(video_path)
                    res = await self.instagram.post_reel(video_url, post_text)
                elif content_type == "carousel" and carousel_paths:
                    res = await self.instagram.post_carousel(carousel_paths, post_text)
                else:
                    # Fallback: generate image for Instagram text content
                    img = self.image_gen.generate_for_post(idea["title"], "instagram", "image")
                    res = await self.instagram.post_image(img, post_text)
                posted_urls["instagram"] = res.get("instagram_url", "")
                results["posts"]["instagram"] = res
            except Exception as e:
                self.logger.error("Instagram post failed: %s", e)
                results["posts"]["instagram"] = {"status": "failed", "error": str(e)}

        if "threads" in platforms:
            try:
                th_res = await self.post_to_threads(idea, content_type=content_type)
                posted_urls["threads"] = th_res.get("threads_url", "")
                results["posts"]["threads"] = th_res
            except Exception as e:
                self.logger.error("Threads post failed: %s", e)
                results["posts"]["threads"] = {"status": "failed", "error": str(e)}

        if "substack" in platforms:
            try:
                sb_res = await self.publish_to_substack(idea)
                posted_urls["substack"] = sb_res.get("post_url", "")
                results["posts"]["substack"] = sb_res
            except Exception as e:
                self.logger.error("Substack publish failed: %s", e)
                results["posts"]["substack"] = {"status": "failed", "error": str(e)}

        # Step 6: Update DB + send report
        li_result = results["posts"].get("linkedin", {})
        ig_result = results["posts"].get("instagram", {})
        self._update_post_status(
            post_id,
            "posted",
            linkedin_urn=li_result.get("post_urn"),
            linkedin_url=li_result.get("post_url"),
            instagram_id=ig_result.get("post_id"),
            instagram_url=ig_result.get("instagram_url"),
        )

        report = (
            f"🎉 *Content Posted!*\n"
            f"📝 Topic: {idea['title']}\n"
            f"📊 Type: {content_type}\n"
            f"🔗 LinkedIn: {posted_urls.get('linkedin', 'N/A')}\n"
            f"📸 Instagram: {posted_urls.get('instagram', 'N/A')}\n"
            f"🧵 Threads: {posted_urls.get('threads', 'N/A')}\n"
            f"📰 Substack: {posted_urls.get('substack', 'N/A')}\n"
        )
        await self.reporter.send(report)

        return {**results, "status": "posted", "post_id": post_id, "urls": posted_urls}

    # ------------------------------------------------------------------ #
    # Threads                                                              #
    # ------------------------------------------------------------------ #

    async def post_to_threads(self, idea: dict, content_type: str = "text") -> dict:
        """
        Generate content for Threads and publish it.

        Args:
            idea: idea dict with at least 'id' and 'title'.
            content_type: text | image | video | carousel
        Returns:
            dict with posting result from ThreadsPoster.
        """
        self.logger.info("Posting to Threads: %s (type=%s)", idea.get("title"), content_type)

        # Generate script (reuse existing scripting agent)
        script = None
        if idea.get("id"):
            script = await self.scripting.generate_script(idea["id"])

        post_text = (
            script.get("instagram_caption", idea["title"])
            if script
            else f"{idea['title']}\n\n{idea.get('hook', '')}"
        )

        # Choose the correct ThreadsPoster method based on content type
        if content_type == "image":
            image_path = self.image_gen.generate_for_post(
                idea["title"], platform="threads", content_type="image"
            )
            res = await self.threads.post_image(post_text, image_path)
        elif content_type == "video":
            res = await self.threads.post_video(post_text)
        elif content_type == "carousel":
            prompts = [
                f"Slide {i+1}: {idea['title']} — key point {i+1}" for i in range(4)
            ]
            carousel_paths = self.image_gen.generate_batch(prompts, size="square_hd")
            res = await self.threads.post_carousel(post_text, carousel_paths)
        else:  # default: text
            res = await self.threads.post_text(post_text)

        # Persist to DB
        post_id = self._save_post(
            platform="threads",
            content_type=content_type,
            text=post_text,
            idea_id=idea.get("id"),
            script_id=script.get("id") if script else None,
        )
        self._update_post_status(post_id, "posted")

        # Telegram notification
        threads_url = res.get("threads_url", "")
        await self.reporter.send(
            f"🧵 *Threads Post Published!*\n"
            f"📝 Topic: {idea['title']}\n"
            f"📊 Type: {content_type}\n"
            f"🔗 URL: {threads_url or 'N/A'}\n"
        )

        return {**res, "post_id": post_id}

    # ------------------------------------------------------------------ #
    # Substack                                                             #
    # ------------------------------------------------------------------ #

    async def publish_to_substack(self, idea: dict, send_email: bool = True) -> dict:
        """
        Generate a long-form article and publish it to Substack.

        Args:
            idea: idea dict with at least 'id' and 'title'.
            send_email: whether to send the post as an email to subscribers.
        Returns:
            dict with posting result from SubstackPoster (includes 'post_url').
        """
        self.logger.info("Publishing to Substack: %s", idea.get("title"))

        # Generate long-form article script
        script = None
        if idea.get("id"):
            script = await self.scripting.generate_script(idea["id"], content_type="article")

        title = idea["title"]
        body_text = (
            script.get("article_body", script.get("youtube_script", idea.get("hook", "")))
            if script
            else idea.get("hook", "")
        )

        # Build HTML body: h1 title + paragraphs
        paragraphs_html = "".join(
            f"<p>{para.strip()}</p>"
            for para in body_text.split("\n\n")
            if para.strip()
        )
        html_body = f"<h1>{title}</h1>\n{paragraphs_html}"

        # Publish via SubstackPoster
        res = await self.substack.create_and_publish(
            title=title,
            body_html=html_body,
            send_email=send_email,
        )

        post_url = res.get("post_url", "")

        # Persist to DB
        post_id = self._save_post(
            platform="substack",
            content_type="article",
            text=body_text[:5000],
            idea_id=idea.get("id"),
            script_id=script.get("id") if script else None,
        )
        self._update_post_status(post_id, "posted")

        # Telegram notification
        await self.reporter.send(
            f"📰 *Substack Article Published!*\n"
            f"📝 Title: {title}\n"
            f"📧 Email sent: {'Yes' if send_email else 'No'}\n"
            f"🔗 URL: {post_url or 'N/A'}\n"
        )

        return {**res, "post_id": post_id}
