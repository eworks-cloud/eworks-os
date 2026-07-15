# STORY-13.6 — Fallback Provenance Tagging & Structured Logging

**Epic:** 13 — AI Provider Resilience Layer
**Status:** Ready
**Points:** 3

## Summary
Ensures every fallback response is clearly, permanently distinguishable from a primary Claude response, and that provider selection, failure classification, fallback attempts, and circuit-breaker transitions are all observable via structured logs.

## Acceptance Criteria
- [ ] Every `AIResponse` produced by a fallback provider carries a provenance tag equal to `"generated via fallback: {provider}/{model}"`, set on a dedicated `AIResponse` field so it is never silently indistinguishable from a primary Claude response (FR-1313)
- [ ] Every fallback response's provenance tag is also emitted as a structured log entry via `structlog` (FR-1313, FR-1315, DEP-1304)
- [ ] `eworks/core/ai.py` emits structured logs for which provider served each call (primary or which fallback), each classified primary failure and its condition (Story 13.2), each fallback attempt and its outcome, and each circuit-breaker state transition (Story 13.3) (FR-1315)
- [ ] No provider secret (API key, AWS credential) ever appears in a log line or in `AIResponse` metadata (NFR-1306)
- [ ] The fallback tag is exposed on `AIResponse` in a form a future Telegram reporting story can consume directly (FR-1313, A-1308)

## Dependencies
- STORY-13.2
- STORY-13.3
- STORY-13.4
- STORY-13.5

## Validation
- **Score:** 8/10
- **Verdict:** GO
- **Rationale:** Observability story pins the exact provenance-tag string, mandates structured logging across provider selection/failure/fallback/circuit transitions, and enforces the no-secret-in-logs guard; dependency fan-in on 13.2–13.5 is correctly declared and FR-1313/1315/NFR-1306 are fully traced.
- **Validator:** @po
- **Date:** 2026-07-15
