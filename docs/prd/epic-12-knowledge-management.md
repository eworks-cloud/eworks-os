# PRD — Epic 12: Knowledge Management Agent

**Product:** Eworks OS — Multi-Agent Company Operating System
**Epic:** Epic 12 — Knowledge Management Agent (gbrain integration)
**Version:** 1.0.0
**Status:** Draft
**Author:** Morgan (PM)
**Owner:** Cesar Schneider, Eworks Labs
**Last Updated:** 2026-07-12

---

> **Source of truth:** This PRD implements the "Knowledge Management Agent" epic recommended in [`autonomous-company-platform-analysis.md`](../architecture/autonomous-company-platform-analysis.md) §4 and §6 (referred to there by the original-roadmap backlog label "E11 — Knowledge Management Agent"). The real, final epic number is **Epic 12** to avoid collision with the existing `docs/stories/epic-7..epic-10` folders and with Epic 11 (Operator Console). No scope beyond that analysis is invented here (Constitution Article IV — No Invention).

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

The Knowledge Management Agent adds a **shared memory / knowledge-graph layer** across the seven existing Eworks OS agents. Today each agent reads and writes its own SQLite tables and there is **no synthesized, cross-agent view** of a client, deal, or conversation. The nurturer's client health notes, the closer's proposal research and discovery-call notes, and the connector's cross-platform conversation history all live in separate tables with no way to ask "what do we know about client X across everything the company has done?"

This epic implements that missing layer using **gbrain** (MIT-licensed) with its **PGLite embedded engine** — per the analysis doc's explicit decision (§4). PGLite means **zero new server and zero Docker container**: the knowledge store is embedded, matching the platform's stated bias against operational weight (`tech-stack.md`). gbrain is a memory/retrieval layer, **not** an agent-orchestration framework, so it does **not** conflict with the deliberate rejection of LangChain/CrewAI/AutoGen in `tech-stack.md`.

Existing agents write their durable, human-meaningful knowledge (health notes, proposal research, conversation history) into gbrain **in addition to** their SQLite tables. gbrain's self-wiring knowledge graph and its two query modes — `search` (fast hybrid retrieval, no LLM cost) and `think` (synthesized, cited answer) — then enable cross-agent queries. The flagship capability this unlocks is a future **`/client [name]`** Telegram command that returns a synthesized view of everything the company knows about a client — the "Client Knowledge Base" the Customer Success agent (E6) already describes as aspirational.

Embeddings default to **local / Ollama** (cost-conscious, zero cloud spend), with a cloud provider (OpenAI / Voyage) as an explicit opt-in upgrade. As a secondary benefit, gbrain is registered as an **MCP server** (`claude mcp add gbrain -- gbrain serve`) so Claude-Code-time development can query the same brain (e.g., "what do we know about client X?").

Critically, gbrain is **additive**: SQLite (`eworks/core/database.py`) remains the system of record for transactional agent state. gbrain is a knowledge/retrieval layer on top, never a replacement for the transactional store.

---

## 2. Business Objective

| Item | Detail |
|------|--------|
| **Problem** | Each agent's knowledge is siloed in its own SQLite tables. There is no synthesized, cross-agent answer to "what do we know about this client/deal/conversation?" |
| **Solution** | Integrate gbrain (PGLite, embedded, MIT-licensed) as a shared knowledge/memory layer that existing agents write into, enabling synthesized cross-agent queries and a `/client [name]` Telegram command. |
| **Primary KPI** | A `/client [name]` query returns a synthesized, cited answer drawing on nurturer, closer, and connector knowledge in a single response — where today it would require manually reading three separate tables. |
| **Secondary KPIs** | Zero new server/Docker infra (PGLite embedded); default embedding cost = $0 (local/Ollama); SQLite remains untouched as system of record; knowledge captured from ≥ 3 agents (nurturer, closer, connector). |
| **Strategic Value** | Turns scattered rows into institutional memory — the "Eworks brain." Delivers the roadmap's aspirational "Client Knowledge Base" and compounds in value as agents keep writing to it. |

---

## 3. Stakeholders

| Role | Name | Responsibility |
|------|------|---------------|
| Product Owner | Cesar Schneider | Approves embedding-provider policy (local vs. cloud), `/client` behavior, scope |
| PM | Morgan | PRD ownership, scope, sequencing |
| Architect | Aria | gbrain engine/embedding decisions, additive-layer boundary vs. SQLite |
| Data Engineer | Dara | Ingestion adapters from SQLite → gbrain; provenance/citation mapping |
| Dev | Dex | Agent write-hooks, CLI/Telegram integration |
| DevOps | Gage | gbrain MCP registration (`claude mcp add ...`) — @devops exclusive |
| QA | Quinn | Retrieval-quality checks, additive-safety (SQLite untouched) testing |

---

## 4. Assumptions & Background

- **A-1201** — gbrain is MIT-licensed and installable, offering a PGLite embedded engine that needs **no separate server or Docker container** (`gbrain init --pglite`), per analysis §4.
- **A-1202** — gbrain provides two query modes: `search` (fast hybrid retrieval, no LLM cost) and `think` (synthesized, cited answer with gap analysis), plus a self-wiring knowledge graph extracted without extra LLM calls (analysis §4).
- **A-1203** — gbrain auto-detects an embedding provider from environment API keys (`OPENAI_API_KEY`, `ZEROENTROPY_API_KEY`, `VOYAGE_API_KEY`) and also supports a fully local **Ollama / llama.cpp** path — enabling a zero-cost default (analysis §4).
- **A-1204** — SQLite (`eworks/core/database.py`) remains the transactional system of record. gbrain is additive; agents continue writing their normal SQLite rows and *also* push durable knowledge into gbrain.
- **A-1205** — The knowledge worth capturing already exists in real tables: nurturer's `client_health_scores.notes` / `client_checkins`, closer's `discovery_calls` (raw_notes, extracted_requirements, pain_points) and `proposals`, and connector's `social_interactions` / `conversation_threads` (context_summary).
- **A-1206** — gbrain can run as an MCP server (stdio/HTTP) so Claude Code can query it during development; `claude mcp add gbrain -- gbrain serve` is the registration path (MCP add is @devops-exclusive per agent-authority rules).
- **A-1207** — The `/client [name]` Telegram command is the flagship user-facing query; Telegram remains the control plane (consistent with the platform).
- **A-1208** — PGLite's practical capacity (up to ~50K pages per analysis §4) comfortably exceeds Eworks Labs' near-term knowledge volume; a Postgres+pgvector upgrade is a future concern, not this epic.

---

## 5. Functional Requirements

### 5.1 Engine & Embedding Setup

**FR-1201 — gbrain PGLite Engine Initialization**
The system SHALL initialize gbrain with its embedded **PGLite** engine (`gbrain init --pglite`), requiring **no new server, database service, or Docker container**. The brain store SHALL live on the same host as the agents.

**FR-1202 — Local/Ollama Embeddings by Default**
The system SHALL default to a **local (Ollama / llama.cpp) embedding** path so that knowledge capture and retrieval incur **zero cloud cost** out of the box.

**FR-1203 — Opt-In Cloud Embedding Upgrade**
The system SHALL support switching to a cloud embedding provider (OpenAI / Voyage / ZeroEntropy) as an **explicit opt-in** via environment/config, using gbrain's env-key auto-detection. Switching providers SHALL be a configuration change, not a code change.

**FR-1204 — Embedding Provider Status & Auto-Detection**
The system SHALL detect and report the active embedding provider (local vs. which cloud provider) and expose it via a status command, so Cesar always knows whether the brain is running on free local embeddings or a paid provider.

### 5.2 Knowledge Ingestion (Existing Agents → gbrain)

**FR-1205 — Nurturer Knowledge Capture**
The system SHALL capture the nurturer's client knowledge into gbrain: client health notes and score context (`client_health_scores`), check-in summaries and NPS/sentiment (`client_checkins`), upsell opportunities (`upsell_opportunities`), and onboarding notes (`onboarding_checklists`) — associated with the client entity.

**FR-1206 — Closer Knowledge Capture**
The system SHALL capture the closer's proposal/deal knowledge into gbrain: discovery-call notes and extracted requirements/pain-points/budget/timeline (`discovery_calls`) and proposal content/summaries (`proposals`) — associated with the client and deal entities.

**FR-1207 — Connector Knowledge Capture**
The system SHALL capture the connector's cross-platform conversation history into gbrain: interactions and their content/sentiment/lead signals (`social_interactions`) and thread context summaries (`conversation_threads`) — associated with the author/contact and, where linked, the client entity.

**FR-1208 — Self-Wiring Knowledge Graph**
The system SHALL rely on gbrain's self-wiring knowledge graph to extract entity relationships (e.g., a contact `works_at` a company, a conversation `relates_to` a deal) from captured knowledge without additional LLM calls, so cross-agent connections form automatically.

**FR-1209 — Provenance / Citation Mapping**
Each knowledge item written to gbrain SHALL carry provenance back to its source SQLite row(s) (agent, table, row id), so synthesized answers can cite where a fact came from and remain auditable.

**FR-1210 — Incremental Sync Job**
The system SHALL provide an incremental sync (schedulable via the existing APScheduler) that pushes new/updated durable knowledge from SQLite into gbrain, without re-embedding unchanged content. gbrain SHALL never be the primary write target for transactional state — SQLite writes happen first, sync follows.

### 5.3 Query & Retrieval

**FR-1211 — Fast Search (No LLM Cost)**
The system SHALL expose gbrain `search` (fast hybrid retrieval, no LLM cost) for raw knowledge lookup across all captured agent knowledge.

**FR-1212 — Synthesized Think Query**
The system SHALL expose gbrain `think` (synthesized, cited answer with gap analysis) for questions requiring a composed cross-agent answer (e.g., "what's the status and history of client X?").

**FR-1213 — `/client [name]` Telegram Command**
The system SHALL provide a `/client [name]` Telegram command that runs a synthesized `think` query and returns a cross-agent client summary (drawing on nurturer, closer, and connector knowledge) with citations, delivered in Cesar's Telegram control plane.

**FR-1214 — Brain CLI Commands**
The system SHALL provide CLI commands (e.g., `eos brain sync`, `eos brain search`, `eos brain think`, `eos brain status`) for manual capture, query, and health inspection, consistent with the platform's Typer CLI.

### 5.4 MCP & Operations

**FR-1215 — gbrain MCP Server Registration**
gbrain SHALL be registered as an MCP server for Claude-Code-time use via `claude mcp add gbrain -- gbrain serve`, so development sessions can query the same brain (e.g., "what do we know about client X?"). *MCP registration is executed by @devops (exclusive authority).*

**FR-1216 — Graceful Fallback (Additive, Non-Blocking)**
If gbrain is unavailable (not initialized, engine error), the agents SHALL continue operating normally against SQLite; knowledge capture SHALL be best-effort and non-blocking, and queries SHALL degrade to an explicit "brain unavailable" state rather than failing an agent run.

---

## 6. Non-Functional Requirements

**NFR-1201 — Zero New Server Infrastructure**
The knowledge layer SHALL introduce **no new standing server, database service, or Docker container** (PGLite embedded). This is a hard requirement aligned with `tech-stack.md`'s operational-weight bias.

**NFR-1202 — SQLite Untouched as System of Record**
Integration SHALL NOT alter, migrate, or take ownership of any `eworks/core/database.py` schema. gbrain reads from / is fed by SQLite but never replaces it. Removing gbrain SHALL leave all transactional agent state fully intact.

**NFR-1203 — Cost Efficiency**
The default configuration SHALL cost **$0** for embeddings (local/Ollama). Where a cloud provider is opted in, embedding token usage SHALL be tracked and reportable so Cesar can see the spend.

**NFR-1204 — Retrieval Quality Transparency**
`think` answers SHALL include citations and gap analysis (per gbrain capabilities), so Cesar can judge answer reliability and see when the brain lacks information rather than receiving a confident but unsupported answer.

**NFR-1205 — Non-Blocking Capture**
Knowledge capture SHALL be asynchronous/best-effort relative to the agents' primary work; a gbrain write failure SHALL never fail or delay an agent's SQLite transaction or run.

**NFR-1206 — Auditability**
Every synthesized answer SHALL be traceable to source SQLite rows via provenance (FR-1209). No fact SHALL appear in a `/client` answer that cannot be traced to captured, real agent data.

**NFR-1207 — Maintainability**
Ingestion adapters SHALL be isolated per agent (nurturer / closer / connector) so a schema change in one agent affects only that adapter. No agent's core logic SHALL be entangled with gbrain internals.

**NFR-1208 — Privacy**
Client PII captured into gbrain SHALL inherit the same access controls as the underlying data (single-operator, local). The brain store SHALL not be exposed to unauthenticated network access by default.

---

## 7. Constraints

**CON-1201 — SQLite Remains the System of Record**
gbrain MUST NOT replace SQLite as the system of record for transactional agent state. It is an **additive knowledge layer only**. All transactional writes go to SQLite first.

**CON-1202 — PGLite Embedded, No New Infra**
The integration MUST use gbrain's PGLite embedded engine. It MUST NOT introduce a Postgres server, pgvector service, Docker container, or any other standing infrastructure in this epic.

**CON-1203 — Not an Agent-Orchestration Framework**
gbrain MUST be used strictly as a memory/retrieval layer. It MUST NOT be turned into (or paired with) a LangChain/CrewAI/AutoGen-style agent-orchestration framework — that class of dependency is explicitly rejected in `tech-stack.md`.

**CON-1204 — Local Embeddings by Default**
The default embedding path MUST be local (Ollama/llama.cpp), incurring zero cloud cost. Any cloud provider MUST be an explicit opt-in, never the default.

**CON-1205 — Telegram Remains the Control Plane**
The `/client` command and any brain interaction MUST flow through the existing Telegram control plane; this epic MUST NOT introduce a competing control interface.

**CON-1206 — Non-Blocking to Agents**
Knowledge capture and query MUST be non-blocking and best-effort with respect to agent runs. A brain failure MUST NOT break any agent (FR-1216 / NFR-1205).

**CON-1207 — MCP Registration via @devops**
Registering gbrain as an MCP server MUST be performed by @devops (`claude mcp add gbrain -- gbrain serve`), per the MCP-governance / agent-authority rules; other agents are MCP consumers, not administrators.

---

## 8. User Stories & Acceptance Criteria

> Story files (STORY-12.x) are created separately by @sm. The stories below define the acceptance surface for that work.

### US-12.1 — Initialize the Embedded Brain
**As** Cesar, **I want** gbrain running on the embedded PGLite engine with local embeddings, **so that** I get a knowledge layer with no new servers and no cloud cost.

**Acceptance Criteria:**
- [ ] `gbrain init --pglite` initializes the brain with no separate server/Docker container.
- [ ] Default embedding provider is local (Ollama/llama.cpp); status command reports "local, $0."
- [ ] A cloud provider can be enabled purely via env/config, with no code change.

### US-12.2 — Capture Nurturer, Closer, Connector Knowledge
**As** the platform, **I want** existing agents to write durable knowledge into gbrain, **so that** cross-agent memory accumulates automatically.

**Acceptance Criteria:**
- [ ] Nurturer health notes/check-ins/upsell/onboarding are captured and associated with the client entity.
- [ ] Closer discovery-call notes and proposals are captured and associated with client/deal entities.
- [ ] Connector interactions and thread summaries are captured and associated with the contact (and client where linked).
- [ ] Each captured item carries provenance back to its source SQLite row.

### US-12.3 — Cross-Agent `/client` Query
**As** Cesar, **I want** `/client [name]` in Telegram to return a synthesized, cited summary, **so that** I get everything the company knows about a client in one message.

**Acceptance Criteria:**
- [ ] `/client [name]` runs a gbrain `think` query and returns a synthesized answer.
- [ ] The answer draws on nurturer + closer + connector knowledge where it exists.
- [ ] The answer includes citations to source rows and flags gaps where knowledge is missing.
- [ ] The command runs entirely within the existing Telegram control plane.

### US-12.4 — Fast Search & CLI
**As** Cesar, **I want** fast search and CLI access to the brain, **so that** I can look things up cheaply without an LLM call.

**Acceptance Criteria:**
- [ ] `eos brain search "<query>"` returns hybrid-retrieval results with no LLM cost.
- [ ] `eos brain think "<question>"` returns a synthesized, cited answer.
- [ ] `eos brain status` reports engine, provider, item count, and last sync.

### US-12.5 — MCP Registration for Dev-Time Queries
**As** a developer using Claude Code, **I want** gbrain registered as an MCP server, **so that** I can query the company brain during development.

**Acceptance Criteria:**
- [ ] @devops registers gbrain via `claude mcp add gbrain -- gbrain serve`.
- [ ] A Claude Code session can query the brain and get cited answers.
- [ ] Registration follows MCP-governance rules (executed by @devops only).

### US-12.6 — Additive & Non-Blocking Safety
**As** Cesar, **I want** the brain to be strictly additive, **so that** it never endangers transactional agent state.

**Acceptance Criteria:**
- [ ] SQLite schema is unchanged; removing gbrain leaves all agent state intact.
- [ ] A gbrain write failure does not fail or delay any agent's SQLite transaction or run.
- [ ] When the brain is unavailable, queries return an explicit "brain unavailable" state, not an error that breaks an agent.

---

## 9. Out of Scope (Epic 12)

- **Federated / multi-user brain** — no OAuth 2.1 team/federated deployment; single-operator (Cesar) only.
- **Cloud Postgres + pgvector deployment** — the Postgres/Supabase engine is a *future* scaling upgrade, not this epic. PGLite embedded only.
- **Replacing SQLite** — gbrain never becomes the transactional system of record.
- **Cloud embeddings as default** — cloud providers are opt-in only; not enabled by default.
- **Capturing every agent** — this epic targets nurturer, closer, and connector knowledge (the analysis-named sources). Deeper capture from prospector/publisher/conductor/treasurer is a future extension.
- **Autonomous write-back** — the brain does not autonomously modify agent tables or take actions; it is read/query + best-effort capture.
- **New control interface** — no web/knowledge UI here (the Operator Console's Brain view is an Epic 11 placeholder; wiring it to gbrain is a later follow-on).
- **gstack-style dev tooling** — unrelated; explicitly excluded per analysis §5.

---

## 10. Dependencies

| ID | Dependency | Type | Owner | Required By |
|----|-----------|------|-------|-------------|
| DEP-1201 | gbrain (MIT-licensed) installed with PGLite engine | External | Engineering | Sprint 1 |
| DEP-1202 | Local embedding runtime (Ollama / llama.cpp) for the default path | External | Engineering | Sprint 1 |
| DEP-1203 | Nurturer schema (`client_health_scores`, `client_checkins`, `upsell_opportunities`, `onboarding_checklists`) | Internal | nurturer | Nurturer capture |
| DEP-1204 | Closer schema (`discovery_calls`, `proposals`, `clients`) | Internal | closer | Closer capture |
| DEP-1205 | Connector schema (`social_interactions`, `conversation_threads`) | Internal | connector | Connector capture |
| DEP-1206 | APScheduler (existing) for the incremental sync job | Internal | Engineering | Sync job |
| DEP-1207 | Telegram bot (existing) for the `/client` command | Internal | Engineering | `/client` command |
| DEP-1208 | @devops for MCP registration (`claude mcp add gbrain -- gbrain serve`) | Internal | @devops | MCP use |
| DEP-1209 | Optional cloud embedding key (OpenAI/Voyage/ZeroEntropy) — only if opt-in upgrade chosen | External | Cesar | Optional |

---

## 11. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|-----------|
| R-1201 | New external dependency (gbrain) adds maintenance/version-drift risk | Medium | Medium | Isolate behind per-agent adapters + a single brain-client module (NFR-1207); pin version; additive so it can be removed without data loss (CON-1201) |
| R-1202 | Local/Ollama embedding quality insufficient for good `think` answers | Medium | Medium | Ship with citations + gap analysis (NFR-1204) so weak answers are visible; cloud provider available as opt-in upgrade (FR-1203) |
| R-1203 | Temptation to make gbrain the system of record, undermining SQLite | Low | High | Hard constraint CON-1201/NFR-1202; SQLite-first capture order (FR-1210); test that removing gbrain leaves state intact |
| R-1204 | Scope creep toward Postgres/pgvector or federated multi-user | Medium | Medium | Explicit Out-of-Scope (§9); PGLite-only constraint (CON-1202) |
| R-1205 | gbrain failure blocks or slows an agent run | Low | High | Non-blocking best-effort capture (FR-1216 / NFR-1205); "brain unavailable" degrade state |
| R-1206 | PII captured into the brain widens exposure surface | Low | Medium | Inherit single-operator/local access controls (NFR-1208); no default network exposure |
| R-1207 | Reintroducing a heavy orchestration framework under the "knowledge" banner | Low | High | CON-1203 — gbrain is memory/retrieval only, never an orchestration framework (consistent with `tech-stack.md`) |

---

## 12. Glossary

| Term | Definition |
|------|-----------|
| **gbrain** | MIT-licensed MCP-based knowledge/memory layer with a self-wiring knowledge graph and synthesized answers (analysis §4) |
| **PGLite** | gbrain's embedded database engine — zero-config, no separate server or Docker container |
| **`search` (mode)** | gbrain's fast hybrid retrieval mode; returns raw results with no LLM cost |
| **`think` (mode)** | gbrain's synthesized, cited-answer mode with gap analysis |
| **Self-wiring knowledge graph** | Entity relationships (e.g., `works_at`) gbrain extracts automatically without extra LLM calls |
| **Provenance** | The link from a knowledge item back to its source SQLite row(s), enabling citations and audit |
| **Local/Ollama embeddings** | A fully local, zero-cost embedding path (default for this epic) |
| **MCP server** | Model Context Protocol server; gbrain registered via `claude mcp add gbrain -- gbrain serve` for dev-time queries |
| **System of record** | The authoritative transactional store — remains SQLite (`eworks/core/database.py`); gbrain is additive only |
| **`/client [name]`** | Telegram command returning a synthesized cross-agent client summary (the flagship capability of this epic) |
| **Eworks OS** | The multi-agent company operating system platform this knowledge layer serves |
</content>
