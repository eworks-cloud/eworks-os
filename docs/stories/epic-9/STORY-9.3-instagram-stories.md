# STORY-9.3: Instagram Stories

**Epic:** 9 — YouTube + Instagram Extended Features
**Status:** Done
**Points:** 3

## Summary
Add Instagram Stories (image + video) and Reel with custom cover image to `InstagramPoster`.

## Acceptance Criteria
- [x] `post_story_image()` posts 24h ephemeral image Story
- [x] `post_story_video()` posts video Story with longer poll wait
- [x] `post_reel_with_cover()` posts Reel with optional cover_url
- [x] All return `{status: 'needs_auth'}` when credentials missing

## Files
- `eworks/agents/publisher/social_poster.py` (InstagramPoster extended)

## Commit
`feat(epic-9): Instagram Stories (image + video) + Reel cover image`
