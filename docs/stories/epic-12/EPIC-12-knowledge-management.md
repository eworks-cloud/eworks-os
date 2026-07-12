# Epic 12 — Knowledge Management Agent
**Agent Name:** Knowledge Management (gbrain integration — shared memory layer across the existing seven agents; not a net-new business agent)
**Status:** Draft
**Goal:** Add a shared, cross-agent knowledge/memory layer using gbrain (PGLite embedded, MIT-licensed, zero new server/Docker). Existing agents (nurturer, closer, connector) write durable knowledge into it, enabling synthesized cross-agent queries and a `/client [name]` Telegram command. Additive only — SQLite stays the system of record.

> Full PRD: [`docs/prd/epic-12-knowledge-management.md`](../../prd/epic-12-knowledge-management.md). Implements the "Knowledge Management Agent" epic from `docs/architecture/autonomous-company-platform-analysis.md` (§4, §6). Real epic number **12** (the analysis doc's "E11" was an old-roadmap backlog placeholder label).

## Functional Requirements
- FR-1201: Initialize gbrain PGLite embedded engine (`gbrain init --pglite`) — no new server/database service/Docker container
- FR-1202: Local/Ollama embeddings by default — zero cloud cost out of the box
- FR-1203: Opt-in cloud embedding upgrade (OpenAI/Voyage/ZeroEntropy) via env/config, no code change
- FR-1204: Detect + report active embedding provider (local vs. cloud) via status command
- FR-1205: Capture nurturer knowledge (`client_health_scores`, `client_checkins`, `upsell_opportunities`, `onboarding_checklists`) → gbrain, per client
- FR-1206: Capture closer knowledge (`discovery_calls`, `proposals`) → gbrain, per client/deal
- FR-1207: Capture connector knowledge (`social_interactions`, `conversation_threads`) → gbrain, per contact/client
- FR-1208: Rely on gbrain self-wiring knowledge graph (entity relationships, no extra LLM calls)
- FR-1209: Provenance/citation mapping — each knowledge item links back to its source SQLite row(s)
- FR-1210: Incremental sync job (via existing APScheduler) SQLite → gbrain; SQLite written first, sync follows; no re-embedding unchanged content
- FR-1211: Fast `search` (hybrid retrieval, no LLM cost) across all captured knowledge
- FR-1212: Synthesized `think` query (cited answer + gap analysis) for cross-agent questions
- FR-1213: `/client [name]` Telegram command — synthesized cross-agent client summary with citations
- FR-1214: Brain CLI commands (`eos brain sync/search/think/status`)
- FR-1215: Register gbrain as MCP server (`claude mcp add gbrain -- gbrain serve`) for Claude-Code-time queries — executed by @devops (exclusive)
- FR-1216: Graceful fallback — brain unavailable degrades to explicit "brain unavailable" state; agents keep running on SQLite; capture is best-effort/non-blocking

## Non-Functional Requirements
- NFR-1201: Zero new server infrastructure (PGLite embedded) — no standing server/DB service/Docker container
- NFR-1202: SQLite untouched as system of record; no schema alteration/migration/ownership; removing gbrain leaves all state intact
- NFR-1203: Cost efficiency — default $0 embeddings (local); cloud token usage tracked + reportable when opted in
- NFR-1204: Retrieval-quality transparency — `think` answers carry citations + gap analysis
- NFR-1205: Non-blocking capture — a gbrain write failure never fails/delays an agent's SQLite transaction or run
- NFR-1206: Auditability — every synthesized fact traceable to real source SQLite rows via provenance
- NFR-1207: Maintainability — per-agent ingestion adapters isolated; agent core logic not entangled with gbrain internals
- NFR-1208: Privacy — captured PII inherits single-operator/local access controls; no default network exposure

## Constraints
- CON-1201: SQLite remains the system of record; gbrain is an additive knowledge layer only — transactional writes go to SQLite first
- CON-1202: PGLite embedded only — no Postgres/pgvector server, no Docker, no new standing infra this epic
- CON-1203: gbrain used strictly as a memory/retrieval layer — never a LangChain/CrewAI/AutoGen-style orchestration framework (rejected in `tech-stack.md`)
- CON-1204: Local embeddings by default; any cloud provider is explicit opt-in, never the default
- CON-1205: Telegram remains the control plane — `/client` and all brain interaction flow through it; no competing control interface
- CON-1206: Non-blocking to agents — capture/query best-effort; a brain failure must not break any agent
- CON-1207: MCP registration performed by @devops only (per MCP-governance / agent-authority rules)
</content>
