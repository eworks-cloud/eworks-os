"""Publisher orchestrator — full content pipeline."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from eworks.agents.publisher.base_publisher import BasePublisher
from eworks.agents.publisher.ideation import IdeationAgent
from eworks.agents.publisher.scripting import ScriptingAgent
from eworks.agents.publisher.tts import ElevenLabsAgent
from eworks.agents.publisher.video_generator import HeyGenAgent
from eworks.agents.publisher.social_poster import YouTubePoster, InstagramPoster
from eworks.agents.publisher.approval import TelegramApproval

logger = logging.getLogger(__name__)


class PublisherOrchestrator(BasePublisher):
    """Orchestrates the full content pipeline from idea to published post."""

    async def run(self, campaign_id: int = 0, language: str = "en", auto_approve: bool = False) -> dict[str, Any]:
        """Run the full content pipeline.

        Args:
            campaign_id: Optional campaign ID for tracking
            language: 'en' or 'pt'
            auto_approve: If True, skip Telegram approval step

        Returns:
            Summary dict with status and links
        """
        self.db.add_publisher_tables()
        logger.info("🚀 Starting Publisher pipeline (language=%s, auto_approve=%s)", language, auto_approve)

        # Step 1: Generate ideas
        ideation = IdeationAgent(self.db, self.config)
        logger.info("Step 1: Generating content ideas...")
        ideas = await ideation.generate_ideas(n=5, language=language)
        if not ideas:
            return {"status": "failed", "error": "No ideas generated"}

        # Pick the first idea (production: use scoring/ranking logic)
        best_idea = ideas[0]
        idea_id = best_idea["id"]
        logger.info("Selected idea #%d: %s", idea_id, best_idea["title"])

        # Step 2: Generate scripts
        scripting = ScriptingAgent(self.db, self.config)
        logger.info("Step 2: Generating scripts...")
        script = await scripting.generate_script(idea_id, language=language)
        script_id = script["id"]

        # Step 3: Create content_posts record
        conn = self._get_conn()
        cur = conn.execute(
            """INSERT INTO content_posts (script_id, platform, status) VALUES (?, 'both', 'generating')""",
            (script_id,),
        )
        conn.commit()
        post_id = cur.lastrowid
        logger.info("Created content_post #%d", post_id)

        result: dict[str, Any] = {
            "post_id": post_id,
            "idea_id": idea_id,
            "script_id": script_id,
            "title": best_idea["title"],
        }

        try:
            # Step 3: Generate audio via ElevenLabs
            tts = ElevenLabsAgent(self.db, self.config)
            logger.info("Step 3: Generating audio (ElevenLabs)...")
            audio_path = await tts.generate_audio(
                text=script["reel_script"],
                language=language,
            )
            self.db.update_content_post(post_id, {"audio_path": audio_path})
            result["audio_path"] = audio_path

            # Step 4: Upload audio to HeyGen
            heygen = HeyGenAgent(self.db, self.config)
            logger.info("Step 4: Uploading audio to HeyGen...")
            audio_asset_id = await heygen.upload_audio(audio_path)

            # Steps 5 & 6: Generate reel + YouTube videos in parallel
            logger.info("Steps 5-6: Generating videos in parallel...")
            reel_task = asyncio.create_task(
                heygen.generate_video(
                    script_text=script["reel_script"],
                    format="reel",
                    audio_asset_id=audio_asset_id,
                )
            )
            yt_task = asyncio.create_task(
                heygen.generate_video(
                    script_text=script["youtube_script"],
                    format="youtube",
                )
            )
            reel_result, yt_result = await asyncio.gather(reel_task, yt_task)

            self.db.update_content_post(
                post_id,
                {
                    "heygen_video_id": reel_result["video_id"],
                    "heygen_video_url": reel_result["video_url"],
                    "local_video_path": reel_result["local_path"],
                    "status": "ready",
                },
            )
            result.update(
                {
                    "reel_video": reel_result,
                    "youtube_video": yt_result,
                }
            )

            # Step 7: Approval
            if not auto_approve:
                logger.info("Step 7: Requesting Telegram approval...")
                approval = TelegramApproval(
                    bot_token=self.telegram_bot_token,
                    chat_id=self.telegram_chat_id,
                )
                decision = await approval.send_approval_request(
                    {
                        "title": best_idea["title"],
                        "reel_script": script["reel_script"],
                        "instagram_caption": script["instagram_caption"],
                        "post_id": post_id,
                    }
                )
            else:
                decision = "approved"
                logger.info("Step 7: Auto-approved")

            self.db.update_content_post(post_id, {"status": "approved" if decision == "approved" else "failed"})
            result["approval_decision"] = decision

            if decision != "approved":
                logger.info("Content not approved (%s) — skipping publish", decision)
                result["status"] = decision
                return result

            # Step 8: Upload to YouTube + post to Instagram
            self.db.update_content_post(post_id, {"status": "posting"})
            logger.info("Step 8: Publishing...")

            tags = json.loads(script.get("tags") or "[]")

            yt_poster = YouTubePoster()
            yt_result_post = yt_poster.upload_video(
                video_path=yt_result["local_path"],
                title=script["youtube_title"],
                description=script["youtube_description"],
                tags=tags,
                privacy="private",
            )

            ig_poster = InstagramPoster(
                access_token=self.instagram_access_token,
                ig_user_id=self.instagram_account_id,
            )
            # Upload reel to CDN for Instagram
            reel_cdn_url = await ig_poster.upload_to_cdn(reel_result["local_path"])
            ig_result = await ig_poster.post_reel(
                video_url=reel_cdn_url,
                caption=script["instagram_caption"],
            )

            now = datetime.utcnow().isoformat()
            self.db.update_content_post(
                post_id,
                {
                    "youtube_video_id": yt_result_post.get("video_id", ""),
                    "youtube_url": yt_result_post.get("youtube_url", ""),
                    "instagram_post_id": ig_result.get("post_id", ""),
                    "instagram_url": ig_result.get("instagram_url", ""),
                    "status": "posted",
                    "posted_at": now,
                },
            )

            result.update(
                {
                    "youtube": yt_result_post,
                    "instagram": ig_result,
                    "status": "posted",
                }
            )

            # Step 9: Send Telegram report
            approval_agent = TelegramApproval(
                bot_token=self.telegram_bot_token,
                chat_id=self.telegram_chat_id,
            )
            report_msg = (
                f"✅ *Content Published!*\n\n"
                f"*Title:* {best_idea['title']}\n"
                f"*YouTube:* {yt_result_post.get('youtube_url', 'N/A')}\n"
                f"*Instagram:* {ig_result.get('instagram_url', 'N/A')}\n"
                f"*Post ID:* `{post_id}`"
            )
            await approval_agent.send_message(report_msg)
            logger.info("✅ Pipeline complete for post #%d", post_id)

        except Exception as exc:
            logger.error("Pipeline error for post #%d: %s", post_id, exc, exc_info=True)
            self.db.update_content_post(post_id, {"status": "failed"})
            result["status"] = "failed"
            result["error"] = str(exc)

        return result
