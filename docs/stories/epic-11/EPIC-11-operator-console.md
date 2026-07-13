# Epic 11 — Operator Console
**Agent Name:** Operator Console (dashboard — sits on top of all seven agents; not a new agent)
**Status:** Draft
**Goal:** Give Cesar a read-only web "single pane of glass" over the seven existing agents, reading real data from `eworks/core/database.py` (SQLite). Additive to Telegram, never a replacement for it.

> Full PRD: [`docs/prd/epic-11-operator-console.md`](../../prd/epic-11-operator-console.md). Implements the "Operator Console" epic from `docs/architecture/autonomous-company-platform-analysis.md` (§3, §6). Real epic number **11** (the analysis doc's "E7" was an old-roadmap placeholder label).

## Functional Requirements
- FR-1101: Read-only data layer over `eworks.db` via a thin read API (or read-only connection) — no new agent tables, no writes, no business-logic duplication
- FR-1102: Enforce read-only DB access (query_only / read-only open mode); no INSERT/UPDATE/DELETE
- FR-1103: Real-data-only rendering — no seed/placeholder data; explicit "no data yet / not configured" honesty states
- FR-1104: Auto-refresh each view on a configurable interval (default 30s) with visible last-refreshed timestamp
- FR-1105: Config-driven `eworks.db` path + read-API base URL (default `data/eworks.db`); no hardcoded paths
- FR-1106: Home / company overview — per-agent status tiles, headline KPIs, cross-agent "needs attention" list
- FR-1107: Agent Roster view — all seven agents with last-run info from `agent_runs`/`connector_runs`
- FR-1108: Agent run-history timeline from `agent_runs` (+ `connector_runs`) with counts and status
- FR-1109: Funnel view (prospector→closer) — `prospects` by status + `clients` by status + `proposals`
- FR-1110: Comms/Inbox view (connector) — `social_interactions` + `conversation_threads` by status/platform, escalations, leads
- FR-1111: Social/Content view (publisher) — `content_ideas/scripts/posts`, `social_posts`, `x_posts` + `social_analytics`/`x_analytics`
- FR-1112: Org/Pipeline view (conductor) — `projects`, `sprints`, `project_tasks`, `project_updates` with health scores
- FR-1113: Finances view (treasurer) — `invoices`, `invoice_items`, `payments`, `payment_reminders`; overdue highlighted
- FR-1114: Customer Success view (nurturer) — `client_health_scores`, `client_checkins`, `upsell_opportunities`, `onboarding_checklists`
- FR-1115: Brain view placeholder route reserved for Epic 12 — explicit "not configured — arriving in Epic 12" state, no fabricated data
- FR-1116: Navigation shell listing all views; each view directly addressable by URL (deep-linking)
- FR-1117: Record drill-down into individual prospect/interaction/project/invoice/client with related records
- FR-1118: Local single-user access control (Cesar only) via shared token / local-only binding
- FR-1119: Telegram control-plane cross-link — action items point to Telegram commands, never acted on in-console

## Non-Functional Requirements
- NFR-1101: Read-only safety — never modifies/locks `eworks.db`; agent writes unaffected (WAL reads); console crash cannot corrupt DB
- NFR-1102: Each view renders < 2s on LAN against realistic DB size, using existing indexes
- NFR-1103: No new backend services beyond, at most, one thin read API — no new datastore/broker/orchestration
- NFR-1104: Honesty of state — visually distinguish real data vs. "no data yet" vs. "source not configured"
- NFR-1105: Centralize all schema knowledge in one data-access module; no agent business-logic duplication
- NFR-1106: Structured logging of reads/errors + DB-connection health indicator (connected/not-found/read-error)
- NFR-1107: Localhost/authenticated binding by default; access token from env/config, never committed; no PII to unauthenticated requests
- NFR-1108: Runs alongside existing agents (local or same VPS), single documented start command, no change to Python deploy

## Constraints
- CON-1101: Read-only only — no write-actions (messages/runs/approvals/status changes) this epic; write-actions are a future stretch, out of scope
- CON-1102: Telegram remains the primary control plane — console must not weaken/replace/duplicate it
- CON-1103: No new standing infrastructure beyond one thin read API
- CON-1104: FounderOS-DEMO used as UI reference shape only — no code fork, no its data model
- CON-1105: Real data only — no seed/demo/placeholder data shipped or used as fallback
- CON-1106: `eworks/core/database.py` is the single system of record + schema owner; console defines/migrates no tables (SQLite-first)
- CON-1107: Additive and non-blocking — console up or down has zero effect on any agent
</content>
