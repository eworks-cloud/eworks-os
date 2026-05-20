# STORY-7.7 — Social Publisher Orchestrator
**Status:** Done
**Epic:** 7
**Agent:** @dev (Dex)
**Story:** As Cesar, I want a SocialOrchestrator that coordinates the full content pipeline (idea → script → media → approve → post) across LinkedIn and Instagram so that I can run one command to publish content everywhere.

## Acceptance Criteria
- [x] AC1. SocialOrchestrator extends BaseAgent
- [x] AC2. post_content() supports all 4 content types × 2 platforms
- [x] AC3. Telegram approval step before posting
- [x] AC4. All posts saved to social_posts DB table
- [x] AC5. Final Telegram report sent with URLs
- [x] AC6. dry_run mode generates content without posting
- [x] AC7. auto_approve mode skips Telegram approval

## Tasks
- [x] Task 1: Create eworks/agents/publisher/social_orchestrator.py
- [x] Task 2: Implement SocialOrchestrator class with all dependencies
- [x] Task 3: Implement _save_post() and _update_post_status()
- [x] Task 4: Implement post_content() full pipeline
- [x] Task 5: Add optimal scheduling constants
- [x] Task 6: Git commit

## Dev Notes
Optimal posting: Tue-Thu (days 1-3), 8-10 AM.
Routes to LinkedInPoster or InstagramPoster based on platform param.
IdeationAgent + ScriptingAgent used for content generation.

## File List
- eworks/agents/publisher/social_orchestrator.py (new)
