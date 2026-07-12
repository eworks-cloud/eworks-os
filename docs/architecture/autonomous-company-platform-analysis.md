# Eworks OS — Autonomous Company Platform Analysis

**Version:** 1.0
**Author:** Aria (Architect Agent)
**Date:** 2026-07-12
**Status:** For PM (Morgan) and PO (Cesar) sign-off

---

## Purpose

Compare Eworks OS against three external reference projects the team wants to draw on to push toward a fuller "autonomous AI company":

| Repo | What it is |
|---|---|
| [Bennettxai/FounderOS-DEMO](https://github.com/Bennettxai/FounderOS-DEMO) | Next.js "operator console" dashboard for a solo AI-run business (org chart, agent roster, brain, comms, finances) — placeholder data |
| [garrytan/gstack](https://github.com/garrytan/gstack) | Claude-Code dev-tooling factory — role-based slash commands (CEO, eng manager, QA lead, release engineer) over a 7-phase "Sprint" framework |
| [garrytan/gbrain](https://github.com/garrytan/gbrain) | MCP-based knowledge/memory layer — self-wiring knowledge graph, synthesized ("think") answers, PGLite or Postgres+pgvector engines |

This document is analysis only. It proposes no code changes and authorizes no work; it is input to a future PM/PO roadmap decision.

---

## 1. Executive Summary

Eworks OS is **further along than the current README suggests**. The README describes a single LinkedIn prospecting tool, but the codebase already implements **all six agents** from the platform vision in `docs/prd/product-roadmap.md` ("Eworks OS — Multi-Agent Company Operating System"): prospecting, content/social publishing, cross-platform listening, proposal generation, project management, billing, and customer success are all committed code, not just planned epics.

Given that, the three reference repos matter less as "things to catch up to" and more as **targeted fixes for three specific, real gaps**:

1. **No human-facing dashboard.** Everything today is CLI + Telegram. FounderOS-DEMO is a ready-made reference for the UI shape of an "operator console" that would sit on top of the existing agents.
2. **No shared memory/knowledge layer across agents.** Each agent reads/writes its own SQLite tables; there's no synthesized, cross-agent view of a client, deal, or conversation. gbrain is a close off-the-shelf fit for this — and it's already an unstaffed backlog item (E11) in the roadmap.
3. **Stale roadmap documentation.** `product-roadmap.md` marks E2–E6 as "📋 Planned," but the code exists and is committed. This isn't fixed by adopting any of the three repos — it's a documentation-hygiene item surfaced by this analysis.

gstack, by contrast, is **dev-tooling, not product** — and this repo already has dev-tooling doing the same job (AIOX). Section 5 gives it a full side-by-side rather than a hand-wave.

**Recommendation at a glance:**

| Repo | Recommendation |
|---|---|
| FounderOS-DEMO | Adopt as UI reference shape for a new **E7 — Operator Console** epic; do not fork its code, build against real data |
| gbrain | Adopt as the implementation of the already-backlogged **E11 — Knowledge Management Agent**, PGLite engine, local/Ollama embeddings by default |
| gstack | Skip full adoption (redundant with AIOX); cherry-pick 2 specific capabilities (`/canary`, `/codex`-style second opinion) as candidate future additions to `@devops`/`@qa`, not adopted now |

---

## 2. Current State of Eworks OS

### 2.1 Agent-by-agent status

| Agent | Roadmap epic / theme | Code location | Story/PRD docs |
|---|---|---|---|
| **prospector** | E1 — LinkedIn Prospecting (Acquire) | `eworks/agents/prospector/` | `docs/prd/epic-1-linkedin-agent.md`, `docs/stories/epic-1/` — full coverage |
| **publisher** | E2 — Content Pipeline (Attract) | `eworks/agents/publisher/` | `docs/stories/epic-7/` (social publisher), `epic-8/` (X publisher), `epic-9/` (YT/IG extended) — covered, but under different epic numbers than the roadmap's "E2" |
| **connector** | Not explicitly in original E1–E6 roadmap | `eworks/agents/connector/` | `docs/stories/epic-10/` — covered |
| **closer** | E3 — Proposal Generation (Convert) | `eworks/agents/closer/` | **None found** — code exists, no PRD/story docs |
| **conductor** | E4 — Project Management (Deliver) | `eworks/agents/conductor/` | **None found** — code exists, no PRD/story docs |
| **treasurer** | E5 — Invoice & Billing (Monetize) | `eworks/agents/treasurer/` | **None found** — code exists, no PRD/story docs |
| **nurturer** | E6 — Customer Success (Retain) | `eworks/agents/nurturer/` | **None found** — code exists, no PRD/story docs |

Four of seven shipped agents (closer, conductor, treasurer, nurturer) have real, multi-file, tested implementations (git history shows granular `feat(...)` commits, e.g. `feat(treasurer): invoice generator`, `feat(conductor): sprint manager`) but no corresponding entries in `docs/prd/` or `docs/stories/`. This is a traceability gap against AIOX's own Article IV ("No Invention") principle — the docs should exist even though the code is real. See Section 6.

### 2.2 Platform primitives already in place

- `eworks/core/database.py` — SQLite schema/ORM shared across agents
- `eworks/core/config.py` — `.env` + YAML settings loader
- `eworks/core/queue.py` — persistent SQLite-backed task queue
- `eworks/core/scheduler.py` — APScheduler background jobs
- `eworks/agents/base.py` — `BaseAgent` abstract class (`async def run(campaign_id) -> dict`, `report_status()`)
- Telegram bot — the sole human control-plane interface today (no web UI, no `.mcp.json`, no frontend directory anywhere in the repo)

### 2.3 Constraints to respect

`docs/architecture/tech-stack.md` records a deliberate, reasoned rejection of LangChain/CrewAI/AutoGen in favor of a plain-Python, SQLite-backed task queue, citing dependency weight, opaque abstractions, and auditability. Any recommendation in this document that would reintroduce a heavy framework or an opaque orchestration layer conflicts with that decision and is flagged as such below.

---

## 3. FounderOS-DEMO Comparison → Dashboard Recommendation

FounderOS-DEMO is a Next.js 14 / TypeScript / Tailwind / better-sqlite3 dashboard styled as a "personal operator OS and AI-agent command center." Its routes map almost one-to-one onto agents that already exist in Eworks OS:

| FounderOS-DEMO route | Eworks OS equivalent |
|---|---|
| `/agents` (agent roster) | All seven agents in `eworks/agents/` |
| `/comms` (unified inbox) | `connector` (cross-platform listener/reply) |
| `/social` (growth/marketing analytics) | `publisher` |
| `/funnel` (client journey) | `prospector` → `closer` |
| `/org` (org hierarchy) | `conductor` |
| `/finances` | `treasurer` |
| `/brain` (knowledge graph) | **Nothing today** — this is the gbrain gap (Section 4) |

FounderOS-DEMO's own honesty principle is worth carrying over: it reports integrations as "not configured" rather than faking connections. Any Eworks OS dashboard should do the same against real `eworks.db` data rather than seed/placeholder rows.

**Recommendation:** Do not fork FounderOS-DEMO's code (different data model, placeholder-first design, no auth story for Cesar's real credentials). Instead, use it as a **reference UI shape** for a new `web/` Next.js app that reads from `eworks/core/database.py` (directly or via a thin read API) and renders the existing seven agents' real state. Sequence this as a new **E7 — Operator Console** epic, additive on top of the current six/seven agents — not a blocker for any of them, since Telegram already serves as the functional control plane.

Explicitly out of scope for this document: no dashboard code, no `web/` scaffold, no new dependencies.

---

## 4. gbrain Comparison → Memory Layer Recommendation

gbrain's stated value proposition — "Search gives you raw pages. GBrain gives you the answer" — targets exactly the gap identified in Section 2: agents accumulate raw SQLite rows (conversations, health scores, proposal research, invoices) with no synthesized cross-agent view.

Concretely, gbrain offers:
- A **self-wiring knowledge graph** (entity relationships like `works_at`, `founded`, `advises`) extracted without extra LLM calls, benchmarked at 49.1% P@5 / 97.9% R@5, +31.4pt P@5 over graph-disabled retrieval
- Two query modes: `gbrain search` (fast hybrid retrieval, no LLM cost) and `gbrain think` (synthesized, cited answer with gap analysis)
- Two engines: **PGLite** (embedded, zero-config, up to ~50K pages) or Postgres+pgvector (Supabase/self-hosted, for larger/shared deployments)
- MCP server transport (stdio or HTTP, OAuth 2.1 for federated/team use)
- 43 curated `skills/` (capture, enrichment, brain ops/cron, voice, schema authoring)

**Engine choice — PGLite**, per the user's decision: `gbrain init --pglite` needs no separate server or Docker container, which matches Eworks OS's own stated bias against operational weight (Section 2.3). This does not reintroduce the kind of heavy orchestration framework that `tech-stack.md` rejected — gbrain is a memory/retrieval layer, not an agent-orchestration framework, so it doesn't conflict with the existing "plain Python class + SQLite task queue" decision.

**MCP registration** (for Claude-Code-time use, e.g. answering "what do we know about client X" during development):
```
claude mcp add gbrain -- gbrain serve
```

**Embedding provider:** gbrain auto-detects from environment API keys (`OPENAI_API_KEY`, `ZEROENTROPY_API_KEY`, `VOYAGE_API_KEY`), but also supports **Ollama/llama.cpp for a fully local, zero-cost path**. Given Eworks OS's existing cost-consciousness (Telegram-first control plane, hard rate limits, an `.env`-driven config with no cloud infra beyond Anthropic/Telegram today), recommend defaulting to local/Ollama embeddings, with a cloud provider as an explicit opt-in upgrade later.

**Runtime integration (future, not now):** the natural fit is agents writing into gbrain instead of — or in addition to — scattered SQLite tables: `nurturer`'s client health notes, `closer`'s proposal research, `connector`'s cross-platform conversation history. This would deliver, essentially for free, the `/client [name]` unified-query capability that `EPIC-6` (Customer Success Agent) already describes as aspirational in the roadmap's "Client Knowledge Base" feature.

**Recommendation:** Formalize this as the implementation of **E11 — Knowledge Management Agent**, which is already listed in `product-roadmap.md`'s "Beyond the Roadmap" backlog ("Captures and organizes institutional knowledge from projects, meetings, and client interactions into a searchable Eworks brain"). gbrain is a strong existing-tool fit for that backlog item rather than a new concept to evaluate separately.

---

## 5. gstack Deep Comparison → AIOX SDC

This section gives the deeper side-by-side requested before making a recommendation.

### 5.1 Structural comparison

| Dimension | gstack | AIOX (this repo) |
|---|---|---|
| Core loop | 7-phase Sprint: Think → Plan → Build → Review → Test → Ship → Reflect | 4-phase Story Development Cycle: Create (@sm) → Validate (@po) → Implement (@dev) → QA Gate (@qa), plus a separate QA Loop and Spec Pipeline |
| Roles | 8 personas as slash commands (CEO, Eng Manager, Designer, Staff Engineer, QA Lead, Release Engineer, CSO, DevEx Lead) — "distinct Claude instances with specific system prompts," invoked ad hoc | Fixed agent roster (`@dev`, `@qa`, `@architect`, `@pm`, `@po`, `@sm`, `@analyst`, `@data-engineer`, `@ux-design-expert`, `@devops`) with an explicit delegation matrix and exclusive-authority rules (e.g. only `@devops` can `git push` or open PRs) |
| Traceability | Design docs and specs (`/spec`) persist per-project; no constitutional "no invention" gate found | Constitutional Article IV: every spec statement must trace to FR-\*/NFR-\*/CON-\* or research finding; enforced via critique verdicts (APPROVED/NEEDS_REVISION/BLOCKED) in the Spec Pipeline |
| Framework/project boundary | Global install (`~/.claude/skills/gstack`) symlinked into `.claude/` in team mode; explicit "no vendored files, no version drift" design | Explicit L1–L4 layer model (`.aiox-core/core` never-modify → `docs/stories`/`packages` always-modify) enforced via deny/allow rules in `.claude/settings.json` |
| Multi-model review | `/codex` — independent OpenAI review with pass/fail gate or adversarial mode; cross-model finding overlap reporting | Not present — AIOX's QA Gate and QA Loop use only the Claude-based `@qa` agent |
| Post-deploy monitoring | `/canary` — post-deploy console-error/regression monitoring | Not present — AIOX has no equivalent step after `@devops` ships |
| Design iteration | `/design-shotgun` — 4–6 AI mockup variants with taste-memory decay | AIOX has `@ux-design-expert` with a 5-phase process, but no equivalent multi-variant generation + taste-tracking tool |
| Session memory | `/learn` — persistent cross-session learnings per project; `checkpoint_mode` auto-commits WIP state for crash recovery | AIOX has agent `MEMORY.md` files and the handoff-consolidation rule (`RUN-LOG.md`), which serve a similar "don't lose context across sessions" purpose but via a different mechanism (structured handoff YAML vs. free-form learnings + WIP commits) |
| Business-domain scope | Engineering-only roles (product/eng/design/QA/release) | Squad system (`squad-chief`, `copy-chief`, `data-chief`, `design-chief`, `legal-chief`, `traffic-masters-chief`, etc.) extends the same agent-authority pattern to arbitrary business domains, not just software engineering |
| Git/release control | `/ship`, `/land-and-deploy` — any Claude session can invoke | Exclusive to `@devops` (Gage) by rule — `git push`, PR create/merge, MCP management, CI/CD, releases are all blocked for every other agent |

### 5.2 Where they overlap

Both systems encode the same underlying idea — role-based personas enforcing quality gates before code ships — and both use an auto-fix-then-flag pattern (gstack's `/review` marks `[ASK]` items for human approval; AIOX's QA Gate produces PASS/CONCERNS/FAIL/WAIVED verdicts) plus a retrospective/reflect step (`/retro` vs. AIOX's handoff/consolidation rules).

### 5.3 Recommendation

**Skip full adoption of gstack.** Running two parallel orchestration systems for the same "story → build → review → ship" loop is a maintenance and confusion risk (which agent owns a given review step? which framework's state file is authoritative?), and AIOX already has the stronger traceability and authority-boundary model for this repo's needs (constitutional gates, L1–L4 protection, exclusive `@devops` git control) — properties gstack doesn't claim to provide.

**Cherry-pick two specific capabilities as candidate future additions**, each as its own small, separately-proposed change — not implemented in this pass:
1. **`/canary`-style post-deploy monitoring** as a new step after `@devops`'s push/release flow — AIOX currently has no equivalent.
2. **`/codex`-style cross-model second opinion** as an optional addition to `@qa`'s QA Gate — a second, independently-modeled review pass before a PASS verdict, without replacing AIOX's own gate.

Both require explicit user/PM sign-off before implementation, since they'd add new tooling surface to `@devops` and `@qa`'s exclusive authority areas.

---

## 6. Consolidated Recommendations & Sequencing

| Item | Type | Status |
|---|---|---|
| **E7 — Operator Console** | New epic (dashboard, FounderOS-DEMO-inspired) | Proposed, not started |
| **E11 — Knowledge Management Agent** | New epic (gbrain, PGLite + local embeddings) | Proposed, not started — already a named backlog item in `product-roadmap.md` |
| Backfill PRD/story docs for closer, conductor, treasurer, nurturer | Documentation hygiene | Proposed, not started |
| `/canary`-style post-deploy monitoring for `@devops` | Candidate tooling addition (from gstack) | Proposed, needs separate sign-off |
| `/codex`-style second-opinion review for `@qa` | Candidate tooling addition (from gstack) | Proposed, needs separate sign-off |

**Explicit non-goals:**
- No LangChain/CrewAI/AutoGen-style framework swap for the agent runtime (conflicts with the documented decision in `tech-stack.md`)
- No full adoption of gstack as a parallel dev-orchestration system
- No dashboard or gbrain code written in this pass — this document is analysis only

---

## 7. Open Questions for Cesar/PM Sign-off

1. Should **E7 — Operator Console** be prioritized ahead of, or after, the currently-undocumented E2–E6 agents get their PRD/story docs backfilled?
2. For **E11 — Knowledge Management Agent**, is a fully local/Ollama embedding pipeline acceptable for launch, or is a cloud embedding provider (OpenAI/Voyage) preferred for quality from day one?
3. Should the two gstack-derived candidates (`/canary`, `/codex`-style review) be scoped as formal AIOX rule/task additions owned by `@devops`/`@qa`, or left out entirely for now?
4. Should `product-roadmap.md`'s epic numbering (E1–E6) be reconciled with the actual `docs/stories/epic-7` through `epic-10` numbering already in use for publisher/connector, to avoid future confusion?

*All roadmap changes require PM (Morgan) and PO (Cesar) sign-off, per `product-roadmap.md`.*
