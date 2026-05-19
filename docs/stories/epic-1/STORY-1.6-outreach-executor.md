# STORY-1.6 — Outreach Executor + Rate Limiting

**Status:** ✅ Done
**Epic:** Epic 1 — LinkedIn Prospector Agent
**Agent:** @dev (Dex)

## Description
Execute LinkedIn connection request outreach with strict rate limiting and anti-detection measures.

## Acceptance Criteria
- [x] `OutreachExecutor.send_connection_request()` — navigates profile, clicks Connect, types note, sends
- [x] Handles already-connected, pending, and profile-not-found states
- [x] Human-like message typing with per-character random delays
- [x] `run_campaign()` — fetches queued prospects, enforces daily limit, updates DB
- [x] Hard limit: max 20 connection requests/day
- [x] Time window enforcement: 9–11:30 AM and 2–4:30 PM only
- [x] Random 30–90 second delay between sends
- [x] Immediate stop on LinkedIn restriction detection

## Commit
`feat(executor): outreach executor with hard rate limits + anti-detection delays`
