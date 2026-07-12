# STORY-11.6 — Comms / Inbox View (Connector)

**Epic:** 11 — Operator Console
**Status:** Draft
**Points:** 5

## Summary
Unified inbox across platforms from `social_interactions` and `conversation_threads`, surfacing escalations and leads.

## Acceptance Criteria
- [ ] `web/app/inbox/page.tsx` renders `social_interactions` by status (pending / replied / escalated / ignored) and platform (instagram, linkedin, x, youtube) with author, content, sentiment, lead flag, and confidence (FR-1110)
- [ ] Interactions escalated to Slack and those flagged `is_lead` are clearly surfaced (visually distinct) (FR-1110)
- [ ] `web/app/inbox/[id]/page.tsx` drill-down shows conversation-thread context from `conversation_threads` for the selected interaction (FR-1117)
- [ ] Action-requiring items (e.g. reply/escalate) link to the corresponding Telegram command rather than performing the action in-console (FR-1119, CON-1101)

## Dependencies
- Story 11.2, Story 11.3; DEP-1104
