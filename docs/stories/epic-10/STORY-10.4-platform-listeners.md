# STORY-10.4 — Platform Listeners

**Epic:** 10 — Connector Agent
**Status:** Done
**Points:** 5

## Summary
Four platform listener modules: Instagram, X.com, LinkedIn, YouTube.

## Acceptance Criteria
- [ ] instagram_listener.py: scan(), get_recent_media(), get_comments(), reply_to_comment()
- [ ] x_listener.py: scan(), get_mentions(), reply_to_tweet()
- [ ] linkedin_listener.py: scan(), get_recent_posts(), get_comments(), reply_to_comment()
- [ ] youtube_listener.py: scan(), get_recent_videos(), get_comments(), reply_to_comment()
- [ ] All return empty list when credentials not configured
- [ ] All errors handled gracefully
