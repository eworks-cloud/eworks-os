# STORY-13.5 — DeepInfra, Fireworks.ai & Together.ai Adapters

**Epic:** 13 — AI Provider Resilience Layer
**Status:** Ready
**Points:** 5

## Summary
Three structurally similar OpenAI-compatible-shaped fallback provider adapters — DeepInfra, Fireworks.ai, and Together.ai — each a thin `Provider` protocol implementation over `httpx`, delivered together since they share the same chat-completions request/response shape.

## Acceptance Criteria
- [ ] `eworks/core/ai_providers/deepinfra.py` implements a `DeepInfraProvider` conforming to the `Provider` protocol, configured via `DEEPINFRA_API_KEY` plus model slug, calling DeepInfra's OpenAI-compatible chat-completions endpoint with default model `meta-llama/Meta-Llama-3.1-70B-Instruct`, overridable via env (FR-1308, FR-1310)
- [ ] `eworks/core/ai_providers/fireworks.py` implements a `FireworksProvider` conforming to the `Provider` protocol, configured via `FIREWORKS_API_KEY` plus model, calling Fireworks' OpenAI-compatible chat-completions endpoint with default model `accounts/fireworks/models/llama-v3p1-70b-instruct`, overridable via env (FR-1308, FR-1311)
- [ ] `eworks/core/ai_providers/together.py` implements a `TogetherProvider` conforming to the `Provider` protocol, configured via `TOGETHER_API_KEY` plus model, calling Together's OpenAI-compatible chat-completions endpoint with default model `meta-llama/Llama-3.3-70B-Instruct-Turbo`, overridable via env (FR-1308, FR-1312)
- [ ] All three adapters translate the common `generate(...)` call into the shared OpenAI-compatible chat-completions request/response shape via `httpx`, supporting basic system/user/assistant roles only — no universal prompt translation beyond that (CON-1305, DEP-1303)
- [ ] All three adapters' credentials are sourced from environment/`.env` only, never committed, and never appear in logs or `AIResponse` metadata (NFR-1306, CON-1306)
- [ ] Each adapter is isolated behind the `Provider` protocol; each is independently addable/removable with no change to `AIClient` core or callers (NFR-1307)

## Dependencies
- STORY-13.2
- DEP-1303, DEP-1306, DEP-1307, DEP-1308

## Validation
- **Score:** 8/10
- **Verdict:** GO
- **Rationale:** Sensibly batches three structurally identical OpenAI-compatible adapters into one story, each with its own file target, env-overridable default model, secret-handling guard, and protocol isolation; the shared shape justifies the grouping and all four DEPs plus FR-1310/1311/1312 are mapped.
- **Validator:** @po
- **Date:** 2026-07-15
