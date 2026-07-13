# Epic 13 — AI Provider Resilience Layer
**Agent Name:** AI Provider Resilience Layer (`eworks/core/ai.py` — a shared, opt-in, provider-agnostic AI client with automatic fallback; not a net-new business agent)
**Status:** Draft
**Goal:** Build `eworks/core/ai.py`, a standalone, opt-in, provider-agnostic `AIClient` (`generate(prompt, system, max_tokens, temperature) -> AIResponse`). Anthropic Claude is always primary — with zero new env vars, behavior is byte-for-byte identical to a direct Anthropic call. When explicitly configured, it fails over automatically to four open-source-model providers (AWS Bedrock, DeepInfra, Fireworks.ai, Together.ai) on defined primary failures (timeout, 429, 5xx, missing/invalid key), with a circuit breaker, fallback provenance tagging, and per-call token/cost tracking. Resilience-focused, not cost-routing. Does NOT migrate the 12 existing `import anthropic` call sites (future epic). No new DB/Docker.

> Full PRD: [`docs/prd/epic-13-ai-provider-resilience.md`](../../prd/epic-13-ai-provider-resilience.md). Closes the documented gap where `docs/prd/product-roadmap.md` promises "Eworks AI — Shared Claude API client with prompt library, token tracking, and cost reporting" but no shared AI client exists — 12 files each `import anthropic` ad hoc. Delivers the token-tracking / cost-reporting hooks for the first time. Real epic number **13** (next free after epic-7…epic-12).

## Functional Requirements
- FR-1301: Provider-agnostic `AIClient` in `eworks/core/ai.py` — `generate(prompt, system=None, max_tokens=..., temperature=...) -> AIResponse`; `AIResponse` carries text + provider/model/token-usage/primary-vs-fallback metadata
- FR-1302: Anthropic primary with zero-config parity — with no new env vars, byte-for-byte identical to a direct Anthropic call (existing `config.py` `anthropic_api_key`/`claude_model`), no fallback attempted
- FR-1303: Standalone, opt-in module — this epic does NOT migrate/wrap/modify any of the 12 existing `import anthropic` call sites; adoption is a future epic/story
- FR-1304: Explicit fallback configuration — activates only via `AI_FALLBACK_ENABLED=true` + ordered `AI_FALLBACK_PROVIDERS`; otherwise entirely inert
- FR-1305: Defined primary failure conditions — timeout, 429, 5xx, missing/invalid key (and nothing else, e.g. not a valid 400)
- FR-1306: Ordered fallback chain — attempt providers in configured order until one succeeds or chain exhausted; successful primary NEVER touches fallback; exhaustion returns aggregated error
- FR-1307: Circuit breaker — after N consecutive Anthropic failures in a window, short-circuit to fallback for a cooldown, then retry primary (closed→open→half-open→closed)
- FR-1308: `Provider` protocol + one thin adapter class per provider — OpenAI-compatible chat-completions for DeepInfra/Fireworks/Together, `invoke_model` shape for Bedrock; basic system/user/assistant roles only, not a universal translator
- FR-1309: AWS Bedrock adapter — AWS creds/IAM + region + model ID, default `meta.llama3-1-70b-instruct-v1:0` (env-overridable), `invoke_model` API shape
- FR-1310: DeepInfra adapter — `DEEPINFRA_API_KEY` + model slug, OpenAI-compatible, default `meta-llama/Meta-Llama-3.1-70B-Instruct` (env-overridable)
- FR-1311: Fireworks.ai adapter — `FIREWORKS_API_KEY` + model, OpenAI-compatible, default `accounts/fireworks/models/llama-v3p1-70b-instruct` (env-overridable)
- FR-1312: Together.ai adapter — `TOGETHER_API_KEY` + model, OpenAI-compatible, default `meta-llama/Llama-3.3-70B-Instruct-Turbo` (env-overridable)
- FR-1313: Fallback provenance tagging — every fallback response tagged/logged `"generated via fallback: {provider}/{model}"`, surfaced on `AIResponse` for future Telegram reporting; never silently indistinguishable from a Claude response
- FR-1314: Per-call token/cost tracking hooks — every primary and fallback call emits token-usage/cost via hook + `AIResponse` metadata; fulfills the roadmap's "token tracking, and cost reporting" promise for the first time
- FR-1315: Structured logging (structlog) — provider selection per call, classified primary failures, fallback attempts/outcomes, circuit-breaker state transitions
- FR-1316: Per-provider config blocks + `.env.example` additions — reuse `config.py` patterns; add commented/unset-by-default `AWS_*`/region + Bedrock model ID, `DEEPINFRA_API_KEY`, `FIREWORKS_API_KEY`, `TOGETHER_API_KEY`, `AI_FALLBACK_ENABLED`, `AI_FALLBACK_PROVIDERS`; absence yields zero-config parity

## Non-Functional Requirements
- NFR-1301: Zero-config parity — no new env vars + no call site migrated = zero behavioral change for the 12 existing call sites or any code path (hard requirement)
- NFR-1302: No new standing infrastructure — no new DB, no Docker, no server; only outbound HTTPS to provider APIs/SDKs (SQLite-first/lightweight bias in `tech-stack.md`)
- NFR-1303: Bounded fallback overhead — successful primary ≈ direct Anthropic cost; fallback latency only after a defined failure; circuit breaker prevents compounding slow timeouts
- NFR-1304: Resilience effectiveness — with fallback configured, a defined primary failure yields a successful fallback call while ≥1 fallback provider is healthy
- NFR-1305: Observability — every call's provider/model/primary-vs-fallback/token-cost observable via logs + `AIResponse`; first-ever AI cost-reporting surface
- NFR-1306: Security — all secrets from env/.env, never committed, never logged, never in `AIResponse`; AWS via IAM roles/credentials
- NFR-1307: Maintainability — per-provider logic isolated behind `Provider` protocol; adding a 5th provider = new adapter + config block, no `AIClient`/caller changes
- NFR-1308: Compatibility — reuse `httpx`, `structlog`, `config.py` patterns; no LangChain/CrewAI/AutoGen (rejected in `tech-stack.md`)
- NFR-1309: Testability — failure conditions, ordered chain, and circuit breaker deterministically testable via injected/mocked failures, no real network calls

## Constraints
- CON-1301: No migration of the 12 existing `import anthropic` call sites this epic — they stay unchanged; migration is a future epic/story
- CON-1302: Anthropic always primary; fallback off by default and opt-in only; no silent fallback for non-adopters
- CON-1303: No new standing infrastructure (no DB, no Docker, no server) beyond providers' outbound HTTPS APIs/SDKs
- CON-1304: Resilience, not cost-routing — never route successful traffic to cheaper open-source models to save money by default
- CON-1305: Thin adapters (`Provider` protocol + one per provider), basic system/user/assistant roles only, no universal prompt translation
- CON-1306: Reuse `config.py` patterns; all secrets from env/.env only; no parallel config/secret system
- CON-1307: Embeddings excluded — Epic 12/gbrain's separately-scoped concern; no duplication
- CON-1308: Fallback only on genuine primary failure (FR-1305); a successful primary call is never re-routed to fallback
