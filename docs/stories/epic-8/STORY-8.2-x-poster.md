# STORY-8.2: X Poster Core

**Status:** Done  
**Epic:** 8 — X.com Publisher  

---

## Story

As Eworks OS, I need a core XPoster class that can post tweets, threads, images, and videos to X.com via Twitter API v2 + tweepy.

---

## Acceptance Criteria

- [x] XPoster._is_configured() checks all 4 OAuth tokens
- [x] post_tweet() returns needs_auth when unconfigured
- [x] post_tweet() truncates to 280 chars
- [x] post_thread() links tweets via in_reply_to_tweet_id
- [x] compose_thread() splits long text on sentence boundaries
- [x] upload_image() uploads to v1.1 API with alt text
- [x] upload_video() uses chunked upload + processing wait
- [x] get_tweet_analytics() returns public_metrics dict
- [x] delete_tweet() returns False when unconfigured

---

## Tasks

- [x] Create eworks/agents/publisher/x_poster.py
- [x] Implement all XPoster methods
- [x] Add 2s delay between thread tweets

---

## Dev Notes

Media upload uses v1.1 endpoint (Twitter hasn't migrated to v2 yet for media).
Video polling waits up to 120s for `processing_info.state == 'succeeded'`.
Thread counter format: `(1/5)` appended to each tweet.

---

## Files

- eworks/agents/publisher/x_poster.py (created)
