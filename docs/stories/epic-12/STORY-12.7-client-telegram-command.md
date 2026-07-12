# STORY-12.7 — `/client [name]` Telegram Command

**Epic:** 12 — Knowledge Management Agent
**Status:** Draft
**Points:** 5

## Summary
Telegram command returning a synthesized, cited cross-agent client summary via a gbrain `think` query.

## Acceptance Criteria
- [ ] A Telegram bot handler for `/client [name]` is added (`eworks/core/telegram_bot.py` command registration) that runs a gbrain `think` query scoped to the named client (FR-1213)
- [ ] The returned summary draws on nurturer, closer, and connector knowledge where it exists, with citations to source rows and explicit flags for gaps where knowledge is missing (FR-1213, NFR-1204, NFR-1206)
- [ ] The command runs entirely within the existing Telegram control plane — no new control interface or channel is introduced (CON-1205)
- [ ] When the brain is unavailable, `/client [name]` returns an explicit "brain unavailable" message rather than an error or a fabricated answer (FR-1216)

## Dependencies
- Story 12.5, Story 12.6; DEP-1207
