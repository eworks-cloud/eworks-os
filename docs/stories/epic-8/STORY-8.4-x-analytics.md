# STORY-8.4: X Analytics Collector

**Status:** Done  
**Epic:** 8 — X.com Publisher  

---

## Story

As Eworks OS, I need to collect tweet analytics and persist them to DB so I can track performance and optimize content strategy.

---

## Acceptance Criteria

- [x] collect() fetches public_metrics and saves to x_analytics
- [x] engagement_rate = (likes+retweets+replies+quotes) / impressions × 100
- [x] get_summary() aggregates all metrics across posts
- [x] get_top_posts() returns top N by engagement_rate DESC
- [x] Empty DB returns zeroed dict not exception

---

## Tasks

- [x] Create eworks/agents/publisher/x_analytics.py
- [x] Implement XAnalyticsCollector with collect/summary/top_posts
- [x] SQL JOIN x_posts for text preview in top_posts

---

## Dev Notes

engagement_rate stored as REAL (0-100 scale).
fetched_at uses UTC ISO timestamp.
get_summary returns {} if no rows (not zeros) — callers should handle.

---

## Files

- eworks/agents/publisher/x_analytics.py (created)
