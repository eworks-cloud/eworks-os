# STORY-13.7 — Token / Cost Tracking Hooks

**Epic:** 13 — AI Provider Resilience Layer
**Status:** Draft
**Points:** 3

## Summary
Adds per-call token-usage and cost-tracking data to every provider call (primary or fallback), exposed via both a hook/callback and `AIResponse` metadata — closing the roadmap's long-standing, previously-unfulfilled "Eworks AI — token tracking, and cost reporting" promise for the first time.

## Acceptance Criteria
- [ ] Every `AIClient.generate(...)` call (primary Anthropic or any fallback provider) emits token-usage data (prompt tokens, completion tokens) and cost data where derivable, via both an `AIResponse` metadata field and a callable hook/callback (FR-1314)
- [ ] Token/cost tracking data includes provider and model identifiers alongside token counts, distinguishing which provider actually served the call (FR-1314, FR-1301)
- [ ] Token/cost tracking hooks are documented (in module docstring/README note) as fulfilling the product-roadmap's previously-unfulfilled "Eworks AI — token tracking, and cost reporting" promise (FR-1314, A-1307)
- [ ] No provider secret appears in the token/cost tracking hook payload or in `AIResponse` metadata (NFR-1306)
- [ ] Every call's provider, model, primary-vs-fallback status, and token/cost data is observable end-to-end via logs and `AIResponse` metadata (NFR-1305)

## Dependencies
- STORY-13.1
- STORY-13.4
- STORY-13.5
