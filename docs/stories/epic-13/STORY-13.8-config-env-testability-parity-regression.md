# STORY-13.8 — Config, `.env.example` Additions, Testability & Parity Regression

**Epic:** 13 — AI Provider Resilience Layer
**Status:** Draft
**Points:** 5

## Summary
Closing story. Wires per-provider config blocks and `.env.example` documentation for all four fallback providers (unset by default), and delivers the mocked-failure test suite proving primary-failure classification, ordered fallback, and the circuit breaker are all deterministically testable with no real network calls — plus the parity regression test proving the 12 existing `import anthropic` call sites remain byte-for-byte unaffected by this epic.

## Acceptance Criteria
- [ ] `eworks/core/config.py` gains a per-provider config block for each of the four fallback providers (credentials, region/endpoint, env-overridable model default) plus `AI_FALLBACK_ENABLED` / `AI_FALLBACK_PROVIDERS`, reusing existing `config.py` patterns; no parallel config/secret system is introduced (FR-1316, CON-1306)
- [ ] `.env.example` is extended with commented, unset-by-default variables: `AWS_*` (credentials/region) + Bedrock model ID, `DEEPINFRA_API_KEY`, `FIREWORKS_API_KEY`, `TOGETHER_API_KEY`, `AI_FALLBACK_ENABLED`, `AI_FALLBACK_PROVIDERS` — each annotated with its sensible model default from A-1309 (FR-1316)
- [ ] Absence of all new `.env.example` variables is proven (by test) to yield exact zero-config parity with Story 13.1's Anthropic-only behavior (FR-1316, NFR-1301)
- [ ] `tests/test_ai.py` deterministically tests all defined primary-failure conditions (timeout, 429, 5xx, missing/invalid key), the ordered fallback chain, and circuit-breaker state transitions via injected/mocked provider failures — no real network call is made to Anthropic or any fallback provider (NFR-1309, FR-1305, FR-1306, FR-1307)
- [ ] `tests/test_ai.py` includes a parity regression test asserting the 12 existing `import anthropic` call sites (A-1301) are byte-for-byte unmodified by this epic — e.g. via file-hash or explicit import-site enumeration check — proving CON-1301/FR-1303 (CON-1301, FR-1303)
- [ ] `tests/test_ai.py` asserts that with fallback configured and a healthy fallback provider, a defined primary failure yields a successful fallback response rather than a hard failure (NFR-1304)

## Dependencies
- STORY-13.1 through STORY-13.7
