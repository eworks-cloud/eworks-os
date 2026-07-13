# STORY-13.1 — Core AIClient Interface + Anthropic Primary Adapter

**Epic:** 13 — AI Provider Resilience Layer
**Status:** Draft
**Points:** 5

## Summary
Foundation story. Introduces the new, standalone `eworks/core/ai.py` module exposing a single provider-agnostic `AIClient.generate(...) -> AIResponse` interface, with Anthropic Claude wired as the always-on primary provider. With zero new environment variables set, behavior is byte-for-byte identical to a direct Anthropic call — no fallback exists yet at this point in the epic, and none of the 12 existing `import anthropic` call sites are touched.

## Acceptance Criteria
- [ ] `eworks/core/ai.py` exposes `AIClient` with a `generate(prompt, system=None, max_tokens=..., temperature=...) -> AIResponse` method; `AIResponse` carries the generated text plus provider, model, token-usage, and primary-vs-fallback metadata (FR-1301)
- [ ] Anthropic Claude is the client's default primary provider, sourced from the existing `eworks/core/config.py` `anthropic_api_key` and `claude_model` — no new config keys are required for this path (FR-1302, DEP-1301, DEP-1302)
- [ ] With zero new environment variables set, `AIClient.generate(...)` produces a request/response byte-for-byte identical to a direct `anthropic` SDK call (same model, same request shape, same result) and never attempts fallback (FR-1302, NFR-1301, CON-1302)
- [ ] `eworks/core/ai.py` is a new, standalone module; none of the 12 existing `import anthropic` call sites (A-1301: `discovery_processor.py`, `proposal_generator.py`, `generator.py`, `reply_generator.py`, `upsell_detector.py`, `checkin_system.py`, `hashtag_researcher.py`, `ideation.py`, `x_content_generator.py`, `ig_engagement.py`, `thumbnail_generator.py`, `eworks/cli/main.py`) are modified, imported from, or wrapped by this story (FR-1303, CON-1301)
- [ ] `eworks/core/ai.py` reuses existing `httpx`/`structlog`/`config.py` conventions and introduces no new orchestration framework (NFR-1308)
- [ ] `eworks/core/ai.py` implements no embedding functionality — text generation only, with no overlap with Epic 12/gbrain (CON-1307)

## Dependencies
- DEP-1301, DEP-1302
