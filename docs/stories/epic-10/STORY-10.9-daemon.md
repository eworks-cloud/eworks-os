# STORY-10.9 — Daemon Mode

**Epic:** 10 — Connector Agent
**Status:** Done
**Points:** 2

## Summary
Daemon mode runs connector on configurable polling schedule with auto-restart on crash.

## Acceptance Criteria
- [ ] connector daemon --interval command works
- [ ] Polls all platforms on schedule
- [ ] Catches and logs exceptions without crashing daemon loop
