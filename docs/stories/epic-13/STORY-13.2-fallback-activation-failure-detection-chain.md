# STORY-13.2 — Fallback Activation, Failure Detection & Ordered Chain Logic

**Epic:** 13 — AI Provider Resilience Layer
**Status:** Draft
**Points:** 5

## Summary
Introduces the `Provider` protocol that all adapters (primary and fallback) implement, plus the explicit opt-in fallback configuration, defined primary-failure classification, and ordered fallback-chain execution logic in `eworks/core/ai.py`. No concrete fallback provider adapters exist yet — this story wires the mechanism; Stories 13.4/13.5 supply the adapters that plug into it.

## Acceptance Criteria
- [ ] `eworks/core/ai.py` defines a `Provider` protocol/interface that every adapter (primary Anthropic and future fallback providers) implements, isolating per-provider request/response translation behind a common `generate`-style method (FR-1308)
- [ ] Fallback is entirely inert unless explicitly configured via `AI_FALLBACK_ENABLED=true` plus an ordered `AI_FALLBACK_PROVIDERS` list (e.g. `deepinfra,fireworks,together,bedrock`); absent this configuration, `AIClient.generate(...)` behavior is unchanged from Story 13.1 (FR-1304, CON-1302)
- [ ] `eworks/core/ai.py` classifies primary-provider outcomes into the defined failure conditions eligible for fallback — request **timeout**, HTTP **429**, HTTP **5xx**, and **missing/invalid API key** — and explicitly excludes other outcomes (e.g. a well-formed 400 from a malformed prompt) from triggering fallback (FR-1305)
- [ ] On a classified primary failure with fallback configured, `AIClient` attempts the configured fallback providers in the exact configured order until one succeeds or the chain is exhausted (FR-1306)
- [ ] A successful primary call never invokes any fallback provider — verified for both the zero-config path and the fallback-configured path (FR-1306, CON-1308)
- [ ] If the entire fallback chain is exhausted without success, `AIClient.generate(...)` raises/returns a clear, aggregated error describing the primary outcome and each fallback attempt's outcome (FR-1306)
- [ ] The fallback chain never reroutes a successful primary response to a fallback provider to save cost — fallback activates strictly on the defined failure conditions, never as a cost-optimization router (CON-1304, CON-1308)

## Dependencies
- STORY-13.1
