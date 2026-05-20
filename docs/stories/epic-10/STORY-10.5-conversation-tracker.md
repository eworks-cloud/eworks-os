# STORY-10.5 — Conversation Tracker

**Epic:** 10 — Connector Agent
**Status:** Done
**Points:** 3

## Summary
DB-backed conversation tracking: deduplication, cooldown enforcement, thread context, pending queue.

## Acceptance Criteria
- [ ] eworks/agents/connector/conversation_tracker.py created
- [ ] is_already_seen() checks for duplicate external_id
- [ ] is_in_cooldown() enforces 4h per-user cooldown
- [ ] save_interaction() persists to social_interactions table
- [ ] mark_replied() / mark_escalated() update status
- [ ] get_thread_context() returns last 3 exchanges
- [ ] get_pending() returns prioritized pending queue
