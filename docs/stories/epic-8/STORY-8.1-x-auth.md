# STORY-8.1: X Auth + DB Tables

**Status:** Done  
**Epic:** 8 — X.com Publisher  

---

## Story

As Eworks OS, I need X API credentials wired into env vars and DB tables for x_posts and x_analytics so I can store tweet history and metrics.

---

## Acceptance Criteria

- [x] docs/stories/epic-8/ directory created with EPIC + all story files
- [x] x_posts table created via add_x_publisher_tables()
- [x] x_analytics table created with FK to x_posts
- [x] tweepy>=4.14.0 added to requirements.txt
- [x] .env.example updated with X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET, X_BEARER_TOKEN

---

## Tasks

- [x] Create docs/stories/epic-8/ with all .md files
- [x] Add add_x_publisher_tables() to DatabaseManager
- [x] Add tweepy to requirements.txt
- [x] Add X env vars to .env.example

---

## Dev Notes

Tables use CHECK constraints for content_type and status columns.
thread_texts and thread_tweet_ids stored as JSON strings.
content_ideas FK is nullable (post may be standalone).

---

## Files Modified

- docs/stories/epic-8/*.md (created)
- eworks/core/database.py
- requirements.txt
- .env.example
