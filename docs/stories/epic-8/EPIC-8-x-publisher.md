# Epic 8: X.com (Twitter) Publisher

**Status:** Done  
**Owner:** Dex (AI Dev Agent)  
**Sprint:** 8  
**Created:** 2026-05-19  

---

## Overview

Build a full X.com (Twitter API v2) publisher integrated into Eworks OS.
Enables Cesar Schneider / Eworks Labs to build authority on X through automated, AI-generated content — tweets, threads, image tweets, video tweets — with Claude-powered generation, analytics tracking, and Telegram approval flow.

---

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-801 | Post text tweets (up to 280 chars) via Twitter API v2 |
| FR-802 | Compose and post numbered threads (long content split on sentence boundaries) |
| FR-803 | Post image tweets (FAL.ai generated image, 16:9 landscape) |
| FR-804 | Post video tweets (HeyGen video, chunked upload) |
| FR-805 | Support quote tweet and reply tweet |
| FR-806 | Fetch tweet analytics (impressions, likes, retweets, replies, quotes, bookmarks) |
| FR-807 | Save analytics to x_analytics DB table with engagement_rate |
| FR-808 | Claude-powered tweet generation (styles: insight, tip, question, stat, announcement) |
| FR-809 | Claude-powered thread generation (configurable length, JSON output) |
| FR-810 | Cross-post LinkedIn posts → X thread (adapt tone, strip corporate language) |
| FR-811 | CLI `eos x` command group (tweet, thread, image, video, cross-post, analytics, list, schedule) |
| FR-812 | Scheduling at optimal times (Mon-Fri, 9/10/12/17h), max 5 posts/day safety limit |

---

## Non-Functional Requirements

- **Auth:** OAuth 1.0a for write (tweepy.Client with all 4 tokens), Bearer Token for read
- **Rate limits:** Never exceed 5 posts/day (free tier: 17/day, basic: 100/day)
- **Resilience:** Graceful degradation when tokens not configured (`needs_auth` status)
- **Media:** Image upload via v1.1 API with alt text; video chunked upload with processing wait
- **Thread delay:** 2s between thread tweets to avoid rate limit errors
- **Engagement rate:** (likes+retweets+replies+quotes) / impressions × 100

---

## Constraints

- Twitter API v2 for tweets; v1.1 endpoint for media upload (no v2 media yet)
- tweepy>=4.14.0 handles OAuth complexity
- Video processing can take up to 120s; polling with 5s intervals
- Free tier: 17 write ops/24h — enforce MAX_PER_DAY=5 in orchestrator

---

## Stories

| Story | Title | Status |
|-------|-------|--------|
| 8.1 | AIOX story files + DB tables | Done |
| 8.2 | X Poster core (tweet, thread, image, video) | Done |
| 8.3 | X Content Generator (Claude-powered) | Done |
| 8.4 | X Analytics Collector | Done |
| 8.5 | X Orchestrator (full pipeline) | Done |
| 8.6 | CLI `eos x` command group | Done |
| 8.7 | Test suite (10 tests) | Done |

---

## File Map

```
eworks/agents/publisher/
  x_poster.py            # Core Twitter API v2 poster
  x_content_generator.py # Claude tweet/thread generator
  x_analytics.py         # Analytics collector + DB writer
  x_orchestrator.py      # Full pipeline orchestrator
eworks/cli/main.py       # Extended with `x` group
eworks/core/database.py  # add_x_publisher_tables()
tests/test_x_publisher.py
docs/stories/epic-8/
  EPIC-8-x-publisher.md
  STORY-8.1-x-auth.md ... STORY-8.7-tests.md
```
