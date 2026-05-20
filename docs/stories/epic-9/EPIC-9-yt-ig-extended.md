# Epic 9: YouTube + Instagram Extended Features

**Status:** Done
**Epic Owner:** Dex (AI Dev Agent)
**Created:** 2026-05-19

---

## Overview

Extend existing YouTube and Instagram publishers with high-value missing features including Shorts, thumbnails, captions, playlists, scheduled publishing, analytics, Stories, hashtag research, and engagement automation.

---

## Functional Requirements

### YouTube Extended

| ID | Requirement |
|----|-------------|
| FR-901 | Upload YouTube Shorts (vertical 9:16, max 60s) with #Shorts auto-tagging |
| FR-902 | Set AI-generated custom thumbnails via `thumbnails.set` OAuth scope |
| FR-903 | Add videos to playlists (create playlist if missing) |
| FR-904 | Schedule video publish at specific ISO8601 datetime |
| FR-905 | Upload SRT captions/subtitles to YouTube videos |
| FR-906 | Fetch video analytics: views, likes, comments, watch_time via YouTube Analytics v2 |
| FR-907 | Generate SRT caption files from script text (no external API, pace-based) |
| FR-908 | Generate YouTube thumbnail images via FAL.ai (1280x720, 16:9) |

### Instagram Extended

| ID | Requirement |
|----|-------------|
| FR-909 | Post image Stories (24h ephemeral) to Instagram |
| FR-910 | Post video Stories to Instagram |
| FR-911 | Post Reels with custom cover image |
| FR-912 | Research and generate 28 optimal Instagram hashtags via Claude AI |
| FR-913 | Format hashtag sets for caption (proper spacing/newlines) |
| FR-914 | Auto-reply to recent Instagram comments using Claude-generated responses |
| FR-915 | Fetch and store Instagram comments per post |
| FR-916 | Post images with location tagging (Facebook Place ID) |

---

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-901 | All new methods gracefully return `{status: 'needs_auth'}` when credentials missing |
| NFR-902 | YouTube Analytics fallback if API not authorized (no crash) |
| NFR-903 | Auto-reply rate-limited to 3s between replies (Instagram ToS) |
| NFR-904 | Caption generator works offline — no external APIs needed |
| NFR-905 | All new DB tables use `CREATE TABLE IF NOT EXISTS` (idempotent) |
| NFR-906 | SRT timestamps must be monotonically increasing |
| NFR-907 | Hashtag generation capped at 30 (Instagram hard limit) |

---

## Constraints

- CON-901: Thumbnail upload requires `https://www.googleapis.com/auth/youtube.force-ssl` scope
- CON-902: Instagram Stories media expires after 24h — track in `ig_stories.expires_at`
- CON-903: Instagram hashtag limit is 30 per post — enforced in `HashtagResearcher.MAX_HASHTAGS`
- CON-904: YouTube Shorts must be ≤60s and vertical (9:16) — enforced by caller convention
- CON-905: Caption generator uses ~2.3 words/second pace estimation

---

## Stories

| Story | Title | Status |
|-------|-------|--------|
| STORY-9.1 | AIOX Story Files | Done |
| STORY-9.2 | YouTube Extended Features | Done |
| STORY-9.3 | Instagram Stories | Done |
| STORY-9.4 | Instagram Hashtag Research | Done |
| STORY-9.5 | Instagram Auto-Reply + Location | Done |
| STORY-9.6 | Extended CLI Commands | Done |
| STORY-9.7 | Extended DB Tables | Done |
| STORY-9.8 | Test Suite | Done |
