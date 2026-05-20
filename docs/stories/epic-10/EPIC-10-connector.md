# Epic 10 — Connector Agent
**Agent Name:** Connector
**Status:** In Progress
**Goal:** Monitor all social platforms, reply in Cesar's voice, escalate to Slack when human needed

## Functional Requirements
- FR-1001: Monitor Instagram comments + mentions every 15 min
- FR-1002: Monitor LinkedIn post comments every 15 min  
- FR-1003: Monitor X.com replies + mentions every 10 min
- FR-1004: Monitor YouTube video comments every 30 min
- FR-1005: Generate Claude AI reply for each interaction
- FR-1006: Post reply automatically when confidence >= 70%
- FR-1007: Send to Slack for human review when confidence < 70%
- FR-1008: Escalate to Slack #connector-leads when meeting/pricing detected
- FR-1009: Track full conversation thread context per user per platform
- FR-1010: Detect language (EN/PT) and reply in same language
- FR-1011: Cooldown: never reply to same user twice within 4h
- FR-1012: Fire Closer agent when meeting explicitly requested
- FR-1013: Unified inbox CLI command showing all pending interactions
- FR-1014: Mark interaction as handled/ignored/escalated
- FR-1015: Daily Slack summary: interactions handled, escalated, leads detected

## Non-Functional Requirements
- NFR-1001: Max 50 API calls/hour per platform (rate limit safety)
- NFR-1002: Reply latency < 5 min from comment to response
- NFR-1003: All interactions stored in DB for audit trail
- NFR-1004: Slack notifications delivered < 30s from detection
- NFR-1005: Agent runs as daemon, restarts on crash

## Constraints
- CON-1001: Instagram DMs require approved Messenger API access
- CON-1002: LinkedIn messaging API requires partner approval (use comment replies only for MVP)
- CON-1003: X DMs require Basic tier API ($100/mo) — use mentions/replies for MVP
- CON-1004: YouTube comments require OAuth (same token as upload)
