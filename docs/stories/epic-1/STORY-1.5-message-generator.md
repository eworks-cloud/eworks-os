# STORY-1.5 — Claude AI Message Generator

**Status:** ✅ Done
**Epic:** Epic 1 — LinkedIn Prospector Agent
**Agent:** @dev (Dex)

## Description
Generate highly personalized LinkedIn connection request messages using Claude, validated to LinkedIn's 300-character limit.

## Acceptance Criteria
- [x] `MessageGenerator.__init__(api_key, model='claude-opus-4-5')`
- [x] `generate(prospect, persona, campaign)` — builds rich prompt, calls Claude, returns message
- [x] System prompt: Cesar Schneider persona, 300-char limit, no generic lines
- [x] `generate_batch()` — batch generation with 1-2s inter-request delay
- [x] `validate_message()` — checks length ≤ 300 and forbidden patterns
- [x] Persists generation_model + generation_prompt to messages table

## Commit
`feat(generator): Claude AI personalized message generator with 300-char validation`
