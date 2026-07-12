# PRD — Epic 13: AI Provider Resilience Layer

**Product:** Eworks OS — Multi-Agent Company Operating System
**Epic:** Epic 13 — AI Provider Resilience Layer (`eworks/core/ai.py`)
**Version:** 1.0.0
**Status:** Draft
**Author:** Morgan (PM)
**Owner:** Cesar Schneider, Eworks Labs
**Last Updated:** 2026-07-12

---

> **Source of truth:** This PRD closes a real, documented gap. `docs/prd/product-roadmap.md` §"Platform Architecture Principles" promises **"Eworks AI — Shared Claude API client with prompt library, token tracking, and cost reporting."** In reality **no shared AI client module exists** today: 12 files across the codebase each do `import anthropic` and instantiate their own client ad hoc. This epic introduces `eworks/core/ai.py` as a new, **standalone, opt-in** provider-agnostic AI client whose primary purpose is **resilience/fallback** (open-source models as automatic backup when Anthropic Claude is unavailable) — and, as a side effect, delivers the roadmap's long-promised token-tracking / cost-reporting hooks for the **first time**. No scope beyond the confirmed investigation and Cesar's explicit decisions is invented here (Constitution Article IV — No Invention).

---

## Table of Contents
1. [Epic Overview](#1-epic-overview)
2. [Business Objective](#2-business-objective)
3. [Stakeholders](#3-stakeholders)
4. [Assumptions & Background](#4-assumptions--background)
5. [Functional Requirements](#5-functional-requirements)
6. [Non-Functional Requirements](#6-non-functional-requirements)
7. [Constraints](#7-constraints)
8. [User Stories & Acceptance Criteria](#8-user-stories--acceptance-criteria)
9. [Out of Scope](#9-out-of-scope)
10. [Dependencies](#10-dependencies)
11. [Risks](#11-risks)
12. [Glossary](#12-glossary)

---

## 1. Epic Overview

Eworks OS runs entirely on **one** LLM vendor. Twelve files — across the closer, prospector, connector, nurturer, and publisher agents plus the CLI — each `import anthropic` directly and instantiate their own client. If Anthropic is rate-limited (429), erroring (5xx / timeout), or the API key is missing/invalid, every AI-dependent agent path fails at once with no backstop. There is no shared client, no shared failure handling, and no shared cost visibility — despite the roadmap explicitly promising an "Eworks AI" shared client.

This epic builds `eworks/core/ai.py`: a **new, provider-agnostic AI client** exposing a single `AIClient` interface with a `generate(prompt, system=None, max_tokens=..., temperature=...) -> AIResponse` method. **Anthropic Claude is always the primary/default provider.** With zero new environment variables configured, the client's behavior is byte-for-byte identical to a direct Anthropic call — there are **no silent fallback surprises** for anyone who does not opt in.

When (and only when) fallback is **explicitly configured**, the client adds automatic resilience: on a genuine primary-provider failure (timeout, 429, 5xx, missing/invalid key), it fails over — in a configured provider order — to one of four open-source-model providers: **AWS Bedrock, DeepInfra, Fireworks.ai, and Together.ai**. These serve open-source models (Llama, Mixtral, DeepSeek, Qwen, etc.) as a **resilience backstop**, not as a cost-optimization router. A successful primary call **never** touches a fallback provider. A **circuit breaker** prevents hammering a failing primary: after N consecutive Anthropic failures within a window, the client short-circuits straight to fallback for a cooldown period, then retries primary.

Because open-source model quality/tone can differ from Claude, every fallback response is **tagged and logged** as "generated via fallback: {provider}/{model}" — never silently indistinguishable from a primary Claude response, and surfaced to callers for future Telegram reporting. Per-call **token/cost tracking hooks** fulfill the roadmap's "cost reporting" promise for the first time.

Critically, this module is **standalone and opt-in**. It does **not** migrate any of the 12 existing `import anthropic` call sites — they keep working completely unchanged. Migration is a future epic/story, explicitly not started here. The module requires **no new standing infrastructure** (no new database, no Docker) beyond the four providers' outbound HTTPS APIs/SDKs — respecting the SQLite-first, lightweight bias in `docs/architecture/tech-stack.md`.

---

## 2. Business Objective

| Item | Detail |
|------|--------|
| **Problem** | Eworks OS has a single point of failure on Anthropic. 12 ad-hoc `import anthropic` call sites mean that an Anthropic outage, rate-limit, or bad key breaks every AI agent path at once — with no backstop, no shared failure handling, and no cost visibility. The roadmap's promised "Eworks AI" shared client does not exist. |
| **Solution** | Build `eworks/core/ai.py`: a standalone, opt-in, provider-agnostic `AIClient` with Anthropic as primary and automatic, explicitly-configured fallback to four open-source-model providers (AWS Bedrock, DeepInfra, Fireworks.ai, Together.ai), a circuit breaker, fallback provenance tagging, and per-call token/cost tracking hooks. |
| **Primary KPI** | When Anthropic returns a defined failure (429/5xx/timeout/invalid key) **and** fallback is configured, an AI request completes successfully via a fallback provider — where today the same request would hard-fail. Successful primary calls are byte-for-byte unchanged. |
| **Secondary KPIs** | Zero behavioral change for non-adopters (zero-config parity); zero new standing infra; every AI call's provider/model/token-cost is observable for the first time; a future migration of the 12 call sites has a single, tested target to adopt. |
| **Strategic Value** | Removes the platform's single-vendor LLM risk, closes the documented "Eworks AI — cost reporting" roadmap gap, and gives Eworks OS an insurance policy: the company keeps running (on open-source models) even when its primary LLM vendor is down. |

---

## 3. Stakeholders

| Role | Name | Responsibility |
|------|------|---------------|
| Product Owner | Cesar Schneider | Approves fallback policy (which providers, order), model defaults, opt-in scope |
| PM | Morgan | PRD ownership, scope, sequencing, roadmap-gap tracking |
| Architect | Aria | `AIClient` interface, `Provider` protocol, circuit-breaker design, adapter boundary |
| Dev | Dex | `eworks/core/ai.py`, per-provider adapters, config wiring, tracking hooks |
| DevOps | Gage | Provider credential/secret provisioning guidance (env/.env); AWS IAM setup guidance |
| QA | Quinn | Failure-injection tests (429/5xx/timeout/bad key), circuit-breaker + parity testing |

---

## 4. Assumptions & Background

- **A-1301** — No shared AI client exists today. Investigation confirmed **12** files each `import anthropic` directly and build their own client: `eworks/agents/closer/discovery_processor.py`, `proposal_generator.py`; `eworks/agents/prospector/generator.py`; `eworks/agents/connector/reply_generator.py`; `eworks/agents/nurturer/upsell_detector.py`, `checkin_system.py`; `eworks/agents/publisher/hashtag_researcher.py`, `ideation.py`, `x_content_generator.py`, `ig_engagement.py`, `thumbnail_generator.py`; and `eworks/cli/main.py`.
- **A-1302** — `eworks/core/config.py` already exposes `anthropic_api_key` (from `ANTHROPIC_API_KEY`) and `claude_model` (default `claude-opus-4-5`, overridable via `CLAUDE_MODEL`). The new module reuses these config patterns rather than inventing a parallel config system.
- **A-1303** — `.env.example` currently contains only `ANTHROPIC_API_KEY` for AI providers. No AWS / DeepInfra / Fireworks / Together keys exist yet; this epic adds them (documented, opt-in, unset by default).
- **A-1304** — Three of the four fallback providers (DeepInfra, Fireworks.ai, Together.ai) expose an **OpenAI-compatible chat-completions** API. **AWS Bedrock** uses its own `invoke_model` API shape. A thin per-provider adapter layer — not a universal translator — is sufficient.
- **A-1305** — The platform already uses `httpx` (per `tech-stack.md`) for HTTP calls; fallback providers can be reached over outbound HTTPS (OpenAI-compatible providers via httpx or their SDK; Bedrock via `boto3`/`aws-sdk`). No new standing infrastructure is required.
- **A-1306** — Open-source model quality/tone can differ materially from Claude; a Llama/Mixtral/DeepSeek answer must be **distinguishable** from a Claude answer so Cesar can judge reliability, especially for customer-facing copy.
- **A-1307** — The roadmap's "Eworks AI — Shared Claude API client with prompt library, token tracking, and cost reporting" is an unfulfilled promise. Token-tracking / cost-reporting hooks in this module close that gap for the first time.
- **A-1308** — Telegram remains the control plane. Fallback events and cost data are produced in a form that a **future** Telegram reporting story can surface; this epic exposes them but does not build the Telegram command itself.
- **A-1309** — Sensible open-source model defaults per provider are: Bedrock `meta.llama3-1-70b-instruct-v1:0`, DeepInfra `meta-llama/Meta-Llama-3.1-70B-Instruct`, Fireworks.ai `accounts/fireworks/models/llama-v3p1-70b-instruct`, Together.ai `meta-llama/Llama-3.3-70B-Instruct-Turbo` — all env-overridable.

---

## 5. Functional Requirements

### 5.1 Core Client Interface & Default Behavior

**FR-1301 — Provider-Agnostic `AIClient` Interface**
The system SHALL provide `eworks/core/ai.py` exposing a single `AIClient` with a `generate(prompt, system=None, max_tokens=..., temperature=...) -> AIResponse` method. `AIResponse` SHALL carry the generated text plus metadata (provider used, model used, token usage, and whether the response came from primary or fallback). The interface SHALL be provider-agnostic so callers never depend on a specific vendor SDK.

**FR-1302 — Anthropic Primary with Zero-Config Parity**
Anthropic Claude SHALL always be the primary/default provider, using the existing `config.py` `anthropic_api_key` and `claude_model`. With **zero** new environment variables configured, `AIClient.generate(...)` SHALL behave byte-for-byte identically to a direct Anthropic call — same model, same request shape, same result — with **no fallback attempted** and no silent behavioral change.

**FR-1303 — Standalone, Opt-In Module (No Migration)**
The module SHALL be standalone and opt-in for **future** use. This epic SHALL NOT migrate, alter, or wrap any of the 12 existing `import anthropic` call sites (A-1301); they continue working completely unchanged. Callers adopt `AIClient` explicitly, one at a time, in a separate future epic/story.

### 5.2 Fallback Activation & Resilience

**FR-1304 — Explicit Fallback Configuration**
Fallback SHALL activate **only** when explicitly configured via environment/config — an enable flag plus an **ordered** list of fallback providers (e.g., `AI_FALLBACK_ENABLED=true`, `AI_FALLBACK_PROVIDERS=deepinfra,fireworks,together,bedrock`). Absent this configuration, fallback SHALL be entirely inert (FR-1302).

**FR-1305 — Defined Primary Failure Conditions**
The system SHALL define the exact conditions that count as a primary-provider failure eligible for fallback: request **timeout**, HTTP **429** (rate limit), HTTP **5xx** / server error, and **missing or invalid API key** (authentication failure). Conditions outside this set (e.g., a well-formed 400 from a malformed prompt) SHALL NOT trigger fallback.

**FR-1306 — Ordered Fallback Chain; Primary Success Never Falls Back**
On a defined primary failure with fallback configured, the system SHALL attempt fallback providers in the configured order until one succeeds or the chain is exhausted. A **successful** primary call SHALL NEVER touch any fallback provider. If the whole chain is exhausted, the system SHALL surface a clear, aggregated error indicating primary + each fallback attempt outcome.

**FR-1307 — Circuit Breaker with Cooldown**
The system SHALL implement a circuit breaker: after **N consecutive** Anthropic failures within a configured window, it SHALL short-circuit straight to fallback (skipping the primary attempt) for a configured cooldown period, then retry primary once the cooldown elapses. Circuit-breaker state transitions (closed → open → half-open → closed) SHALL be observable (FR-1315).

### 5.3 Provider Adapters

**FR-1308 — `Provider` Protocol + Per-Provider Adapter Layer**
The system SHALL define a `Provider` protocol/interface and implement **one adapter class per provider**. Adapters SHALL be thin: they translate the common `generate(...)` call into each provider's request/response shape (OpenAI-compatible chat-completions for DeepInfra/Fireworks/Together; the `invoke_model` shape for Bedrock) supporting **basic system/user/assistant roles only**. This SHALL NOT be a universal magic translator.

**FR-1309 — AWS Bedrock Adapter**
The system SHALL provide an AWS Bedrock adapter configured via AWS credentials / IAM role + region + model ID. Default model ID SHALL be `meta.llama3-1-70b-instruct-v1:0`, env-overridable. It SHALL use Bedrock's `invoke_model` API shape (not OpenAI-compatible).

**FR-1310 — DeepInfra Adapter**
The system SHALL provide a DeepInfra adapter configured via `DEEPINFRA_API_KEY` + model slug, using DeepInfra's OpenAI-compatible endpoint. Default model SHALL be `meta-llama/Meta-Llama-3.1-70B-Instruct`, env-overridable.

**FR-1311 — Fireworks.ai Adapter**
The system SHALL provide a Fireworks.ai adapter configured via `FIREWORKS_API_KEY` + model, using Fireworks' OpenAI-compatible endpoint. Default model SHALL be `accounts/fireworks/models/llama-v3p1-70b-instruct`, env-overridable.

**FR-1312 — Together.ai Adapter**
The system SHALL provide a Together.ai adapter configured via `TOGETHER_API_KEY` + model, using Together's OpenAI-compatible endpoint. Default model SHALL be `meta-llama/Llama-3.3-70B-Instruct-Turbo`, env-overridable.

### 5.4 Observability, Provenance & Cost

**FR-1313 — Fallback Provenance Tagging**
Every fallback response SHALL be tagged on the returned `AIResponse` and logged as `"generated via fallback: {provider}/{model}"`. A fallback response SHALL NEVER be silently indistinguishable from a primary Claude response. The tag SHALL be surfaced to whatever calls the client, so a future Telegram reporting story can display it and Cesar can judge quality/tone differences.

**FR-1314 — Per-Call Token / Cost Tracking Hooks**
Every provider call (primary or fallback) SHALL emit token-usage and cost-tracking data (provider, model, prompt/completion tokens, and cost where derivable). This SHALL be exposed via a hook/callback and on `AIResponse` metadata. This requirement **fulfills the roadmap's long-standing "Eworks AI — token tracking, and cost reporting" promise for the first time** and SHALL be documented as closing that gap.

**FR-1315 — Structured Logging of Provider Selection & Circuit State**
The system SHALL emit structured logs (via the platform's `structlog`) for: which provider served each call, each primary failure and its classified condition (FR-1305), each fallback attempt and outcome, and each circuit-breaker state transition (FR-1307).

### 5.5 Configuration

**FR-1316 — Per-Provider Config Blocks & `.env.example` Additions**
The system SHALL provide a per-provider config block for each of the four fallback providers (credentials + region/endpoint + env-overridable model default) reusing `eworks/core/config.py` patterns. `.env.example` SHALL be extended with the new, **commented/unset-by-default** variables (`AWS_*` / region + Bedrock model ID, `DEEPINFRA_API_KEY`, `FIREWORKS_API_KEY`, `TOGETHER_API_KEY`, plus `AI_FALLBACK_ENABLED` / `AI_FALLBACK_PROVIDERS`), documenting the sensible model defaults from A-1309. Absence of these variables SHALL yield the zero-config parity behavior of FR-1302.

---

## 6. Non-Functional Requirements

**NFR-1301 — Zero-Config Parity (No Behavioral Change for Non-Adopters)**
With no new env vars set and no call site migrated, the platform SHALL behave exactly as it does today. Adding `eworks/core/ai.py` SHALL introduce **no** behavioral change for the 12 existing call sites or any other code path (hard requirement).

**NFR-1302 — No New Standing Infrastructure**
The module SHALL introduce **no new database, no Docker container, and no standing server** — only outbound HTTPS calls to the four providers' APIs/SDKs. This aligns with the SQLite-first, lightweight bias in `tech-stack.md`.

**NFR-1303 — Bounded Fallback Overhead**
A successful primary call SHALL incur negligible overhead versus a direct Anthropic call. Fallback SHALL only add latency after a defined primary failure, and the circuit breaker SHALL prevent repeated slow primary timeouts from compounding across calls.

**NFR-1304 — Resilience Effectiveness**
Where fallback is configured and the primary returns a defined failure condition, an AI request SHALL succeed via a fallback provider rather than hard-failing, for as long as at least one configured fallback provider is healthy.

**NFR-1305 — Observability**
Every AI call's provider, model, primary-vs-fallback status, and token/cost data SHALL be observable via logs and `AIResponse` metadata — including the first-ever cost-reporting surface for AI usage in Eworks OS.

**NFR-1306 — Security**
All provider secrets (Anthropic key, AWS credentials, DeepInfra/Fireworks/Together keys) SHALL be sourced from environment/`.env` and never committed. AWS access SHALL support IAM roles/credentials. No secret SHALL appear in logs or in `AIResponse` metadata.

**NFR-1307 — Maintainability**
Per-provider logic SHALL be isolated in its own adapter class behind the `Provider` protocol. Adding a fifth provider in the future SHALL require only a new adapter class + config block, with no change to the `AIClient` core or to callers.

**NFR-1308 — Compatibility with Existing Stack**
The module SHALL reuse existing platform building blocks where practical (`httpx` for HTTP, `structlog` for logging, `config.py` patterns) and SHALL NOT introduce a heavy orchestration framework (LangChain/CrewAI/AutoGen are rejected in `tech-stack.md`).

**NFR-1309 — Testability**
Primary failure conditions (timeout, 429, 5xx, invalid key), the ordered fallback chain, and the circuit breaker SHALL be deterministically testable via injected/mocked provider failures, without real network calls to any provider.

---

## 7. Constraints

**CON-1301 — No Migration of Existing Call Sites**
This epic MUST NOT migrate, wrap, or modify any of the 12 existing `import anthropic` call sites (A-1301). They keep working unchanged. Migration is a future epic/story, explicitly not started here.

**CON-1302 — Anthropic Always Primary; No Silent Fallback**
Anthropic MUST always be the primary/default provider. Fallback MUST be off by default and MUST activate only when explicitly configured (FR-1304). There MUST be no silent fallback for anyone who has not opted in.

**CON-1303 — No New Standing Infrastructure**
The module MUST NOT introduce a new database, Docker container, or standing server beyond the four providers' outbound HTTPS APIs/SDKs (NFR-1302).

**CON-1304 — Resilience, Not Cost-Routing**
The four fallback providers exist for **resilience/fallback**, not default cost optimization. The client MUST NOT route successful traffic to cheaper open-source models to save money by default. Fallback is a failure backstop only.

**CON-1305 — Thin Adapters, Basic Roles Only**
Per-provider adapters MUST be thin (a `Provider` protocol + one adapter per provider), MUST NOT attempt universal prompt translation, and MUST support only basic system/user/assistant roles. Automatic prompt-template rewriting for open-source chat formats beyond that is out of scope.

**CON-1306 — Reuse Config Patterns; Secrets in Env Only**
Configuration MUST reuse `eworks/core/config.py` patterns and MUST source all secrets from environment/`.env` (never committed). No parallel config/secret system is permitted.

**CON-1307 — Embeddings Excluded (No Overlap with Epic 12)**
This epic MUST NOT implement embeddings. Embeddings are Epic 12 / gbrain's separately-scoped concern; duplicating them here is prohibited.

**CON-1308 — Fallback Only on Genuine Primary Failure**
Fallback MUST trigger only on the defined failure conditions (FR-1305). A successful primary call MUST NEVER be re-routed to a fallback provider (FR-1306).

---

## 8. User Stories & Acceptance Criteria

> Story files (STORY-13.x) are created separately by @sm. The stories below define the acceptance surface for that work.

### US-13.1 — Provider-Agnostic Client with Zero-Config Parity
**As** the platform, **I want** a single `AIClient.generate(...)` that defaults to Anthropic and behaves identically to a direct Anthropic call when nothing is configured, **so that** adopting it is risk-free.

**Acceptance Criteria:**
- [ ] `eworks/core/ai.py` exposes `AIClient.generate(prompt, system=None, max_tokens=..., temperature=...) -> AIResponse`.
- [ ] With no new env vars set, the result is byte-for-byte equivalent to a direct Anthropic call (same model from `config.py`, no fallback attempted).
- [ ] `AIResponse` reports provider, model, token usage, and primary-vs-fallback status.
- [ ] None of the 12 existing `import anthropic` call sites are modified by this epic.

### US-13.2 — Explicitly-Configured Automatic Fallback
**As** Cesar, **I want** the client to fail over to an open-source provider when Anthropic is down — but only when I turn it on — **so that** the company keeps running during an Anthropic outage without surprises when I haven't opted in.

**Acceptance Criteria:**
- [ ] Fallback activates only when `AI_FALLBACK_ENABLED=true` and an ordered `AI_FALLBACK_PROVIDERS` list is set.
- [ ] Fallback triggers on timeout, 429, 5xx, or missing/invalid key — and on nothing else (e.g., a valid 400 does not trigger it).
- [ ] Providers are attempted in the configured order until one succeeds or the chain is exhausted.
- [ ] A successful primary call never touches any fallback provider.
- [ ] Exhausting the chain returns a clear aggregated error listing primary + each fallback outcome.

### US-13.3 — Four Provider Adapters
**As** Dex, **I want** thin adapters for AWS Bedrock, DeepInfra, Fireworks.ai, and Together.ai with sensible env-overridable model defaults, **so that** each open-source provider can serve a `generate` call.

**Acceptance Criteria:**
- [ ] A `Provider` protocol exists with exactly one adapter class per provider.
- [ ] Bedrock uses the `invoke_model` shape, region + IAM/credentials, default `meta.llama3-1-70b-instruct-v1:0`.
- [ ] DeepInfra/Fireworks/Together use their OpenAI-compatible endpoints with defaults `meta-llama/Meta-Llama-3.1-70B-Instruct`, `accounts/fireworks/models/llama-v3p1-70b-instruct`, `meta-llama/Llama-3.3-70B-Instruct-Turbo` respectively.
- [ ] Every model default is env-overridable; adapters support basic system/user/assistant roles only.

### US-13.4 — Circuit Breaker
**As** the platform, **I want** the client to stop hammering a failing Anthropic endpoint, **so that** repeated timeouts don't compound latency across calls.

**Acceptance Criteria:**
- [ ] After N consecutive Anthropic failures within the window, the client short-circuits straight to fallback for the cooldown period.
- [ ] After cooldown, the client retries primary (half-open) and closes the circuit on success.
- [ ] Circuit-breaker state transitions are emitted in structured logs.

### US-13.5 — Fallback Provenance & Cost Tracking
**As** Cesar, **I want** every fallback answer clearly tagged and every AI call's token/cost tracked, **so that** I can tell open-source answers from Claude and finally see AI spend.

**Acceptance Criteria:**
- [ ] Fallback responses are tagged/logged as `"generated via fallback: {provider}/{model}"` and are never indistinguishable from a Claude response.
- [ ] The fallback tag is surfaced on `AIResponse` for future Telegram reporting.
- [ ] Every call (primary and fallback) emits token-usage / cost data via hook and `AIResponse` metadata.
- [ ] The PRD/roadmap gap for "Eworks AI — token tracking and cost reporting" is documented as closed by this capability.

### US-13.6 — Configuration & Env Documentation
**As** Cesar, **I want** the new provider settings documented in `.env.example` but unset by default, **so that** opting in is a clear config change and doing nothing changes nothing.

**Acceptance Criteria:**
- [ ] `.env.example` documents `AWS_*`/region + Bedrock model ID, `DEEPINFRA_API_KEY`, `FIREWORKS_API_KEY`, `TOGETHER_API_KEY`, `AI_FALLBACK_ENABLED`, `AI_FALLBACK_PROVIDERS` — commented/unset by default with the model defaults noted.
- [ ] Per-provider config blocks reuse `config.py` patterns; no parallel config/secret system is introduced.
- [ ] Absence of these variables yields exact zero-config parity (US-13.1).

---

## 9. Out of Scope (Epic 13)

- **Migrating the 12 existing `import anthropic` call sites** — they keep working unchanged; adoption is a future epic/story, not started here (CON-1301).
- **Embeddings** — Epic 12 / gbrain's separately-scoped concern; must not be duplicated here (CON-1307).
- **Fine-tuning** — no model fine-tuning of any provider.
- **Automatic prompt-template rewriting** for open-source chat formats beyond basic system/user/assistant roles (CON-1305).
- **Cost-optimization routing** — routing successful traffic to cheaper models to save money is explicitly not this epic's purpose (CON-1304).
- **Prompt library** — the roadmap's "prompt library" sub-promise is not part of this resilience-focused epic (this epic delivers the client + token/cost tracking; a shared prompt library is a separate follow-on).
- **Telegram reporting UI** — this epic exposes fallback/cost data; building the Telegram command that displays it is a future story.
- **New standing infrastructure** — no new DB, Docker, or server (CON-1303).

---

## 10. Dependencies

| ID | Dependency | Type | Owner | Required By |
|----|-----------|------|-------|-------------|
| DEP-1301 | `eworks/core/config.py` (`anthropic_api_key`, `claude_model`) config patterns | Internal | Engineering | Client core |
| DEP-1302 | `anthropic` SDK (already in use across 12 call sites) | External | Engineering | Primary provider |
| DEP-1303 | `httpx` (existing) for OpenAI-compatible provider calls | Internal | Engineering | DeepInfra/Fireworks/Together |
| DEP-1304 | `structlog` (existing) for structured provider/circuit logging | Internal | Engineering | Observability |
| DEP-1305 | AWS Bedrock access (credentials/IAM role + region + model enablement) + `boto3`/AWS SDK | External | Cesar / @devops | Bedrock adapter — optional/opt-in |
| DEP-1306 | DeepInfra account + `DEEPINFRA_API_KEY` | External | Cesar | DeepInfra adapter — optional/opt-in |
| DEP-1307 | Fireworks.ai account + `FIREWORKS_API_KEY` | External | Cesar | Fireworks adapter — optional/opt-in |
| DEP-1308 | Together.ai account + `TOGETHER_API_KEY` | External | Cesar | Together adapter — optional/opt-in |
| DEP-1309 | Provider credential/secret provisioning guidance (env/.env, AWS IAM) | Internal | @devops | Opt-in setup |

---

## 11. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|-----------|
| R-1301 | Silent fallback surprises a user who never intended to leave Claude | Low | High | Fallback strictly opt-in + off by default (FR-1304 / CON-1302); zero-config parity (FR-1302 / NFR-1301) |
| R-1302 | Open-source model quality/tone diverges from Claude on customer-facing copy | Medium | Medium | Mandatory provenance tagging (FR-1313) so fallback answers are always distinguishable and reviewable |
| R-1303 | Four new provider SDKs/APIs add maintenance and version-drift surface | Medium | Medium | Thin, isolated per-provider adapters behind a `Provider` protocol (NFR-1307); adding/removing a provider is localized |
| R-1304 | Scope creep into cost-routing, migration, embeddings, or a prompt library | Medium | Medium | Explicit Out-of-Scope (§9) + constraints CON-1301/1304/1307; resilience-only mandate |
| R-1305 | A failing/slow primary compounds latency across many calls | Medium | Medium | Circuit breaker with cooldown (FR-1307); bounded fallback overhead (NFR-1303) |
| R-1306 | Provider secrets leak via logs or response metadata | Low | High | Secrets from env/.env only, never logged, never in `AIResponse` (NFR-1306) |
| R-1307 | Bedrock's non-OpenAI `invoke_model` shape complicates the "one interface" abstraction | Medium | Low | Per-provider adapter isolates the shape difference (FR-1308/1309); common interface unaffected |
| R-1308 | New module accidentally changes behavior of the 12 existing call sites | Low | High | Standalone/opt-in constraint (CON-1301); parity tested (NFR-1301/1309); no call site touched |

---

## 12. Glossary

| Term | Definition |
|------|-----------|
| **`eworks/core/ai.py`** | The new, standalone, opt-in provider-agnostic AI client module this epic delivers |
| **`AIClient`** | The single client class exposing `generate(prompt, system, max_tokens, temperature) -> AIResponse` |
| **`AIResponse`** | Return object carrying generated text + metadata (provider, model, token/cost, primary-vs-fallback, fallback tag) |
| **`Provider` protocol** | The interface each provider adapter implements; enables one thin adapter class per provider |
| **Primary provider** | Anthropic Claude — always the default; used unless it fails per defined conditions with fallback configured |
| **Fallback provider** | One of AWS Bedrock, DeepInfra, Fireworks.ai, Together.ai — serves open-source models as a resilience backstop only |
| **Defined failure condition** | Timeout, HTTP 429, HTTP 5xx, or missing/invalid API key — the only conditions that trigger fallback |
| **Circuit breaker** | Mechanism that short-circuits to fallback after N consecutive primary failures for a cooldown, then retries primary |
| **Fallback provenance tag** | `"generated via fallback: {provider}/{model}"` marker ensuring fallback answers are never indistinguishable from Claude |
| **Zero-config parity** | With no new env vars set, `AIClient` behaves byte-for-byte like a direct Anthropic call |
| **Cost-routing** | Routing successful traffic to cheaper models to save money — explicitly NOT this epic's purpose |
| **Eworks AI** | The roadmap's promised shared Claude client with token tracking + cost reporting; this epic delivers the client + tracking hooks for the first time |
| **Eworks OS** | The multi-agent company operating system platform this resilience layer serves |
