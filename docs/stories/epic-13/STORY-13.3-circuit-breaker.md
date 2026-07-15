# STORY-13.3 — Circuit Breaker

**Epic:** 13 — AI Provider Resilience Layer
**Status:** Ready
**Points:** 3

## Summary
Adds a circuit breaker around the Anthropic primary provider so repeated primary failures short-circuit straight to the configured fallback chain instead of compounding latency, with a cooldown-driven retry back to primary.

## Acceptance Criteria
- [ ] `eworks/core/ai.py` implements a circuit breaker around the Anthropic primary provider with a configurable consecutive-failure threshold (N) and failure window (FR-1307)
- [ ] After N consecutive Anthropic failures within the configured window, `AIClient` short-circuits straight to the configured fallback chain (skipping the primary attempt entirely) for a configured cooldown period (FR-1307)
- [ ] After the cooldown period elapses, `AIClient` retries the primary provider (half-open state); a successful retry closes the circuit and resumes normal primary-first behavior (FR-1307)
- [ ] Circuit-breaker state transitions (closed → open → half-open → closed) are emitted as structured log events (FR-1307)
- [ ] A successful primary call continues to incur negligible overhead versus a direct Anthropic call; the circuit breaker prevents repeated slow primary timeouts from compounding latency across sequential calls (NFR-1303)

## Dependencies
- STORY-13.2

## Validation
- **Score:** 8/10
- **Verdict:** GO
- **Rationale:** Well-scoped incremental story with clear closed/open/half-open/closed state semantics, observable transitions, and bounded-overhead NFR coverage; per-story risk/OUT-scope callouts are implicit but the FR-1307/NFR-1303 traceability is complete.
- **Validator:** @po
- **Date:** 2026-07-15
