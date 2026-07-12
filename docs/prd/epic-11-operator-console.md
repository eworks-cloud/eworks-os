# PRD — Epic 11: Operator Console

**Product:** Eworks OS — Multi-Agent Company Operating System
**Epic:** Epic 11 — Operator Console (Dashboard)
**Version:** 1.0.0
**Status:** Draft
**Author:** Morgan (PM)
**Owner:** Cesar Schneider, Eworks Labs
**Last Updated:** 2026-07-12

---

> **Source of truth:** This PRD implements the "Operator Console" epic recommended in [`autonomous-company-platform-analysis.md`](../architecture/autonomous-company-platform-analysis.md) §3 and §6 (referred to there by the original-roadmap placeholder label "E7 — Operator Console"). The real, final epic number is **Epic 11** to avoid collision with the existing `docs/stories/epic-7..epic-10` folders (publisher / X publisher / extended media / connector). No scope beyond that analysis is invented here (Constitution Article IV — No Invention).

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

The Operator Console is a **read-only web dashboard** that gives Cesar a visual "single pane of glass" over the seven autonomous agents already shipped in Eworks OS (prospector, publisher, connector, closer, conductor, treasurer, nurturer). Today the platform is CLI + Telegram only — there is no human-facing UI, no `web/` directory, and no way to *see* the state of the company at a glance without querying the database or reading Telegram digests.

This epic delivers a **Next.js** application (per the analysis doc's recommendation) modeled on the UI *shape* of the FounderOS-DEMO operator console, but reading **real data** from `eworks/core/database.py` (the SQLite `eworks.db`) rather than the placeholder/seed rows that reference project ships with. It renders the existing agents' real state across a roster view, a sales funnel view, a comms/inbox view, a content/social view, a project/org view, a finances view, and a customer-success view — plus an explicit placeholder route reserved for the future Epic 12 "brain" (Knowledge Management) view.

The console is **additive**: it does not replace Telegram as the control plane. Telegram remains the primary command-and-control interface (per `tech-stack.md` and Epic 1 CON-007). The console is a *window*, not a *steering wheel* — read-first, with write-actions explicitly out of scope for this epic (a possible future stretch, at most).

---

## 2. Business Objective

| Item | Detail |
|------|--------|
| **Problem** | Eworks OS runs seven agents, but Cesar has no visual overview. State lives in `eworks.db` and scrolls past in Telegram. There is no "how is the whole company doing right now?" view. |
| **Solution** | A read-only Next.js operator console that renders every agent's real state from the existing SQLite database — one screen for the whole autonomous company. |
| **Primary KPI** | Cesar can answer "what is every agent doing and what needs my attention?" in < 60 seconds from a single URL, without opening a terminal or scrolling Telegram history. |
| **Secondary KPIs** | 100% of dashboard data traces to real `eworks.db` rows (zero seed/placeholder data); all seven agents represented; page load < 2s on local network; zero new backend services beyond a thin read API. |
| **Strategic Value** | Turns the invisible agent fleet into a legible, demoable product surface — useful for Cesar's own operations and as a future productized/white-label offering (Epic 10 backlog). |

---

## 3. Stakeholders

| Role | Name | Responsibility |
|------|------|---------------|
| Product Owner | Cesar Schneider | Sole dashboard user; final approval on views, layout, priorities |
| PM | Morgan | PRD ownership, scope, sequencing |
| Architect | Aria | Read-API vs. direct-SQLite decision, Next.js app boundary |
| UX Design | Uma | Console layout, information hierarchy, honesty-state design |
| Dev | Dex | Next.js app + read layer implementation |
| QA | Quinn | Real-data verification, no-seed-data acceptance testing |

---

## 4. Assumptions & Background

- **A-1101** — The seven agents (prospector, publisher, connector, closer, conductor, treasurer, nurturer) are already committed and their SQLite schemas exist in `eworks/core/database.py` (verified: `campaigns`, `prospects`, `messages`, `agent_runs`, `content_ideas/scripts/posts`, `social_posts`, `x_posts`, `social_interactions`, `conversation_threads`, `connector_runs`, `clients`, `discovery_calls`, `proposals`, `projects`, `sprints`, `project_tasks`, `invoices`, `payments`, `client_health_scores`, `client_checkins`, `upsell_opportunities`, etc.).
- **A-1102** — The database is SQLite (`data/eworks.db`) in WAL mode, enabling concurrent reads while agents write. A read-only connection from a separate process is safe.
- **A-1103** — Cesar runs the console locally or on the same VPS as the agents; it is single-user (Cesar only) with no multi-tenant requirement.
- **A-1104** — FounderOS-DEMO is used only as a **UI reference shape**, not as a code fork; its data model, placeholder-first design, and auth story are not adopted (per analysis §3).
- **A-1105** — Telegram remains the control plane. The console does not need to send commands, send messages, or mutate agent state to be valuable.
- **A-1106** — The future Epic 12 (Knowledge Management / gbrain) "brain" view does not exist yet; the console must reserve a route for it and render an honest "not configured" state until Epic 12 ships.
- **A-1107** — The team accepts Next.js/TypeScript as the console stack even though the agent runtime is Python; the console is a separate, additive frontend and does not change the Python agent stack or the `tech-stack.md` rejection of heavy Python agent frameworks.

---

## 5. Functional Requirements

### 5.1 Data Access Layer

**FR-1101 — Read-Only Data Layer over `eworks.db`**
The console SHALL read agent state exclusively from the existing SQLite database managed by `eworks/core/database.py`, via a **thin read API** (recommended) or a read-only DB connection. It SHALL NOT create new agent tables, mutate existing rows, or duplicate agent business logic.

**FR-1102 — Read-Only Enforcement**
All database access from the console SHALL be read-only (e.g., `PRAGMA query_only=ON` or a read-only SQLite open mode / API layer that exposes only `SELECT`-derived endpoints). No console code path SHALL issue `INSERT`, `UPDATE`, or `DELETE` against `eworks.db`.

**FR-1103 — Real-Data-Only Rendering (Honesty Principle)**
The console SHALL render only real rows from `eworks.db`. It SHALL NOT ship, seed, or fall back to placeholder/demo data. Where an agent has produced no data yet, or a data source is unavailable, the console SHALL display an explicit **"not configured / no data yet"** state (carried over from FounderOS-DEMO's honesty principle, analysis §3) rather than fabricating rows.

**FR-1104 — Auto-Refresh**
Each view SHALL refresh its data on a configurable interval (default: 30s) and/or on manual refresh, so the console reflects near-current agent state without a full page reload. Last-refreshed timestamp SHALL be visible.

**FR-1105 — Config-Driven Database Location**
The console SHALL resolve the `eworks.db` path (and, if used, the read-API base URL) from configuration/environment, defaulting to the same `data/eworks.db` used by the agents. No hardcoded absolute paths.

### 5.2 Global Overview

**FR-1106 — Home / Company Overview**
The console SHALL provide a home view summarizing the whole company at a glance: per-agent status tiles, headline KPIs (e.g., prospects in pipeline, pending comms interactions, active projects, outstanding invoices, at-risk clients), and a "needs attention" list aggregated across agents (e.g., escalated interactions, overdue invoices, red-zone client health scores).

**FR-1107 — Agent Roster View**
The console SHALL render a roster of all seven agents (prospector, publisher, connector, closer, conductor, treasurer, nurturer), each showing: agent name/theme, last run time and outcome, and a lightweight activity indicator, sourced from `agent_runs`, `connector_runs`, and each agent's own tables. Agents with no recorded runs SHALL show an honest "no runs yet" state.

**FR-1108 — Agent Run History / Timeline**
The console SHALL expose a run-history timeline drawn from `agent_runs` (and `connector_runs`), showing recent runs with agent name, start/complete time, counts (e.g., prospects scanned, messages sent, errors), and status.

### 5.3 Agent-Specific Views

**FR-1109 — Funnel View (Prospector → Closer)**
The console SHALL render the acquisition-to-conversion funnel by joining prospector and closer data: `prospects` grouped by `status` (discovered → scored → queued → contacted → replied → meeting_booked / not_interested / dnc) and `clients` grouped by `status` (lead → discovery → proposal_sent → negotiating → won / lost / churned), with `proposals` status where present. It SHALL show conversion counts across the funnel stages.

**FR-1110 — Comms / Inbox View (Connector)**
The console SHALL render a unified inbox from `social_interactions` and `conversation_threads`: pending / replied / escalated / ignored interactions across platforms (instagram, linkedin, x, youtube), with author, content, sentiment, lead flag, confidence, and escalation status. It SHALL surface interactions escalated to Slack and those flagged `is_lead`.

**FR-1111 — Social / Content View (Publisher)**
The console SHALL render the content pipeline from the publisher tables: `content_ideas`, `content_scripts`, `content_posts`, `social_posts`, and `x_posts` by status, plus engagement metrics from `social_analytics` and `x_analytics` (impressions, likes, comments, shares, engagement rate). It SHALL show what is drafted, scheduled, posted, and how published content is performing.

**FR-1112 — Org / Pipeline View (Conductor)**
The console SHALL render project delivery state from `projects`, `sprints`, `project_tasks`, and `project_updates`: active projects with health score, sprint status, task board counts by status, and recent project updates/blockers. This is the "org/delivery hierarchy" analog of FounderOS-DEMO's `/org` route.

**FR-1113 — Finances View (Treasurer)**
The console SHALL render financial state from `invoices`, `invoice_items`, `payments`, and `payment_reminders`: invoices by status (draft/sent/viewed/paid/overdue/cancelled), outstanding and overdue totals, payments received, and reminder activity. It SHALL highlight overdue invoices in a "needs attention" treatment.

**FR-1114 — Customer Success View (Nurturer)**
The console SHALL render client-health state from `client_health_scores`, `client_checkins`, `upsell_opportunities`, and `onboarding_checklists`: current health score per client with component breakdown, recent check-ins and NPS/sentiment, open upsell opportunities, and onboarding progress. It SHALL highlight red-zone (low health-score) clients.

**FR-1115 — Brain View Placeholder (Reserved for Epic 12)**
The console SHALL include a navigable "Brain / Knowledge" route reserved for the future Epic 12 (Knowledge Management / gbrain) view. Until Epic 12 ships, this route SHALL render an explicit "not configured — arriving in Epic 12" honesty state and SHALL NOT fabricate knowledge-graph data. This is the FounderOS-DEMO `/brain` gap identified in analysis §3.

### 5.4 Navigation, Drill-Down & Access

**FR-1116 — Navigation Shell & Deep-Linking**
The console SHALL provide a persistent navigation shell listing all views (Home, Roster, Funnel, Comms, Social, Projects, Finances, Customer Success, Brain-placeholder). Each view SHALL be directly addressable by URL for bookmarking/deep-linking.

**FR-1117 — Record Drill-Down**
From list/summary views, the console SHALL allow drilling into an individual record (e.g., a single prospect, interaction, project, invoice, or client) to view its detail read from the underlying row(s), including relevant related records (e.g., a client's proposals, projects, invoices, health scores).

**FR-1118 — Local Single-User Access Control**
The console SHALL restrict access to Cesar only via a simple local mechanism (e.g., a single shared access token / local-only binding), consistent with the platform's single-operator model. Full multi-user auth is out of scope (see §9).

**FR-1119 — Telegram Control-Plane Cross-Link**
The console SHALL reinforce Telegram as the control plane: where a view surfaces an item that requires an action (e.g., approve a message, pause an agent, chase an invoice), it SHALL direct Cesar to the corresponding Telegram command rather than performing the action itself. The console SHALL NOT weaken or replace any existing Telegram command.

---

## 6. Non-Functional Requirements

**NFR-1101 — Read-Only Safety**
The console SHALL never modify `eworks.db`. Concurrent agent writes SHALL not be blocked by console reads (WAL-mode read connection). A console crash or misbehavior SHALL NOT be able to corrupt or lock the agents' database.

**NFR-1102 — Performance**
Each view SHALL render within 2 seconds on a local/LAN connection against a database of realistic size (thousands of prospects/interactions/invoices), using indexed queries where indexes exist (e.g., `idx_prospects_status`, `idx_invoices_status`).

**NFR-1103 — No New Backend Services**
The console SHALL NOT require standing up new infrastructure beyond, at most, a single thin read API co-located with the existing app. No new database, message broker, or orchestration service SHALL be introduced (consistent with `tech-stack.md`'s bias against operational weight).

**NFR-1104 — Honesty of State**
Every view SHALL visually distinguish "real data," "no data yet," and "source not configured" so Cesar is never misled into thinking a fabricated or empty state is real activity.

**NFR-1105 — Maintainability**
The console SHALL keep all schema knowledge in a single read/data-access module so that schema changes in `eworks/core/database.py` require updates in one place. It SHALL NOT re-implement agent business logic.

**NFR-1106 — Observability**
The console SHALL log its own read requests/errors (structured) and surface a health indicator for its connection to `eworks.db` (connected / db-not-found / read-error).

**NFR-1107 — Security**
The console SHALL bind to localhost or an authenticated endpoint by default; the access token SHALL be provided via environment/config and never committed. No prospect/client PII SHALL be exposed to unauthenticated requests.

**NFR-1108 — Portability**
The console SHALL run alongside the existing agents (locally or on the same VPS) and be startable via a single documented command, without changing how the Python agents are deployed.

---

## 7. Constraints

**CON-1101 — Read-Only, No Write-Actions**
The console MUST be read-only in this epic. It MUST NOT send messages, trigger agent runs, approve content, mutate statuses, or otherwise write to `eworks.db`. Write-actions are a possible future stretch, explicitly out of scope here (§9).

**CON-1102 — Telegram Remains the Primary Control Plane**
The console MUST NOT weaken, replace, or duplicate Telegram as the command-and-control interface. Telegram stays the steering wheel; the console is the dashboard. (Consistent with Epic 1 CON-007 and `tech-stack.md`.)

**CON-1103 — No New Backend Services Beyond a Thin Read API**
The console MUST NOT introduce new standing infrastructure. At most, a single thin read API layer is permitted; no new datastore, broker, or heavy backend framework.

**CON-1104 — No Fork of FounderOS-DEMO Code**
FounderOS-DEMO MUST be used only as a UI reference shape. Its code, data model, and placeholder-first design MUST NOT be forked into this repo (analysis §3).

**CON-1105 — Real Data Only**
The console MUST render only real `eworks.db` rows. Seed/demo/placeholder data MUST NOT be shipped or used as a fallback (honesty principle).

**CON-1106 — SQLite-First, No Schema Ownership**
The console MUST treat `eworks/core/database.py` as the single system of record and schema owner. It MUST NOT define or migrate agent tables. This respects the SQLite-first decision in `tech-stack.md`.

**CON-1107 — Additive, Non-Blocking**
The console MUST be additive to the running platform. Whether the console is up or down MUST have no effect on any agent's operation.

---

## 8. User Stories & Acceptance Criteria

> Story files (STORY-11.x) are created separately by @sm. The stories below define the acceptance surface for that work.

### US-11.1 — Company Overview at a Glance
**As** Cesar, **I want** a single home screen summarizing all seven agents and what needs my attention, **so that** I can assess the whole company in under a minute.

**Acceptance Criteria:**
- [ ] Home view shows a status tile for each of the seven agents with last-run info from real data.
- [ ] A cross-agent "needs attention" list aggregates escalated interactions, overdue invoices, and red-zone client health scores.
- [ ] All figures trace to real `eworks.db` rows; empty agents show an honest "no data yet" state.
- [ ] Last-refreshed timestamp is visible and updates on the configured interval.

### US-11.2 — Agent Roster & Run History
**As** Cesar, **I want** to see every agent's roster entry and recent run history, **so that** I know which agents are active and healthy.

**Acceptance Criteria:**
- [ ] Roster lists all seven agents; each shows last run time/outcome from `agent_runs`/`connector_runs`.
- [ ] A run-history timeline shows recent runs with counts (scanned/sent/errors) and status.
- [ ] Agents with no runs show "no runs yet," not a fabricated run.

### US-11.3 — Sales Funnel View
**As** Cesar, **I want** to see the prospector→closer funnel, **so that** I understand pipeline health from lead to won deal.

**Acceptance Criteria:**
- [ ] Prospects are grouped by their real `status` values; clients grouped by their real `status` values.
- [ ] Funnel-stage counts are shown and match a direct DB query.
- [ ] Drill-down opens an individual prospect/client with related proposals.

### US-11.4 — Comms / Inbox View
**As** Cesar, **I want** a unified inbox of all social interactions, **so that** I can see what the connector handled and what escalated.

**Acceptance Criteria:**
- [ ] `social_interactions` are shown by status and platform with author, content, sentiment, lead flag.
- [ ] Escalated-to-Slack and `is_lead` interactions are clearly surfaced.
- [ ] Conversation-thread context is viewable on drill-down.

### US-11.5 — Social / Content View
**As** Cesar, **I want** to see the content pipeline and post performance, **so that** I can track what the publisher is producing.

**Acceptance Criteria:**
- [ ] Content ideas/scripts/posts and social/x posts are shown by status.
- [ ] Engagement metrics from `social_analytics`/`x_analytics` are displayed for posted content.
- [ ] Content with no analytics yet shows "no metrics yet," not zeros presented as real performance where none was fetched.

### US-11.6 — Projects / Org View
**As** Cesar, **I want** to see active projects, sprints, and tasks, **so that** I can gauge delivery health.

**Acceptance Criteria:**
- [ ] Active projects show health score, sprint status, and task counts by status.
- [ ] Recent project updates/blockers are listed.
- [ ] Drill-down opens a project with its sprints and tasks.

### US-11.7 — Finances View
**As** Cesar, **I want** to see invoices, payments, and overdue amounts, **so that** I can watch cash without opening the database.

**Acceptance Criteria:**
- [ ] Invoices are grouped by status; outstanding and overdue totals are computed from real rows.
- [ ] Overdue invoices are highlighted in a "needs attention" treatment.
- [ ] Payments received are reconciled against invoices on drill-down.

### US-11.8 — Customer Success View
**As** Cesar, **I want** to see client health, check-ins, and upsell opportunities, **so that** I can protect and grow relationships.

**Acceptance Criteria:**
- [ ] Each client shows current health score with component breakdown.
- [ ] Recent check-ins with NPS/sentiment and open upsell opportunities are listed.
- [ ] Red-zone (low-score) clients are highlighted.

### US-11.9 — Brain Placeholder Route
**As** Cesar, **I want** a reserved Brain view, **so that** the console is ready for Epic 12 without faking knowledge data.

**Acceptance Criteria:**
- [ ] A "Brain / Knowledge" nav item exists and routes to a placeholder page.
- [ ] The page renders an explicit "not configured — arriving in Epic 12" state.
- [ ] No fabricated knowledge-graph/query data is shown.

### US-11.10 — Read-Only & Telegram-Preserving
**As** Cesar, **I want** the console to be strictly read-only and to point me to Telegram for actions, **so that** my control plane stays consistent and safe.

**Acceptance Criteria:**
- [ ] No console code path writes to `eworks.db` (verified by read-only connection/API and test).
- [ ] Action-requiring items link to the relevant Telegram command instead of acting.
- [ ] Bringing the console down has no effect on any running agent.

---

## 9. Out of Scope (Epic 11)

- **Write-actions from the dashboard** — no sending messages, triggering runs, approving content, pausing agents, or mutating any status. (Possible future stretch, explicitly excluded here.)
- **Multi-tenant / multi-user authentication** — single-operator (Cesar) access only; no org accounts, roles, or SSO.
- **Mobile app / native app** — responsive web is acceptable but no dedicated mobile application.
- **Replacing Telegram** — the console never becomes the control plane.
- **New analytics/BI warehouse** — no ETL into a separate analytics store; reads come from `eworks.db`.
- **Forking FounderOS-DEMO** — reference shape only; no code fork, no its data model.
- **The Brain view's real functionality** — only the placeholder route is in scope; real knowledge features are Epic 12.
- **Historical/BI time-series charts beyond what current rows support** — no new metric collection pipeline.

---

## 10. Dependencies

| ID | Dependency | Type | Owner | Required By |
|----|-----------|------|-------|-------------|
| DEP-1101 | `eworks/core/database.py` schema (all seven agents' tables) as system of record | Internal | Engineering | Sprint 1 |
| DEP-1102 | Prospector schema (`campaigns`, `prospects`, `messages`, `agent_runs`, `personas`) | Internal | prospector | Funnel/Roster views |
| DEP-1103 | Closer schema (`clients`, `discovery_calls`, `proposals`) | Internal | closer | Funnel view |
| DEP-1104 | Connector schema (`social_interactions`, `conversation_threads`, `connector_runs`) | Internal | connector | Comms view |
| DEP-1105 | Publisher schema (`content_ideas`, `content_scripts`, `content_posts`, `social_posts`, `x_posts`, `social_analytics`, `x_analytics`) | Internal | publisher | Social view |
| DEP-1106 | Conductor schema (`projects`, `sprints`, `project_tasks`, `project_updates`) | Internal | conductor | Projects view |
| DEP-1107 | Treasurer schema (`invoices`, `invoice_items`, `payments`, `payment_reminders`) | Internal | treasurer | Finances view |
| DEP-1108 | Nurturer schema (`client_health_scores`, `client_checkins`, `upsell_opportunities`, `onboarding_checklists`) | Internal | nurturer | Customer Success view |
| DEP-1109 | Next.js / TypeScript toolchain for the `web/` app | External | Engineering | Sprint 1 |
| DEP-1110 | Local access token / config for single-user auth | Business | Cesar | Sprint 1 |
| DEP-1111 | Epic 12 (Knowledge Management) — for the eventual real Brain view (placeholder only in this epic) | Internal | Epic 12 | Future |

---

## 11. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|-----------|
| R-1101 | Console writes/locks `eworks.db` and disrupts agents | Low | High | Enforce read-only connection/API (FR-1102, NFR-1101); WAL-mode reads; test that agents run unaffected while console is up |
| R-1102 | Schema drift — agent tables change and views silently break | Medium | Medium | Centralize schema knowledge in one data module (NFR-1105); QA verifies views against live schema; treat `database.py` as owner |
| R-1103 | Temptation to add write-actions mid-epic, weakening Telegram control plane | Medium | Medium | Hard constraint CON-1101/CON-1102; write-actions gated to a separate future epic with explicit sign-off |
| R-1104 | Placeholder/seed data creeps in to "make the demo look good" | Medium | Medium | CON-1105 + NFR-1104 honesty states; QA acceptance test explicitly checks for zero seed data |
| R-1105 | Stack split (Python agents + TS console) increases maintenance surface | Medium | Low | Keep console thin and read-only; single data module; no business logic duplication |
| R-1106 | Performance degradation on large DBs | Low | Medium | Use existing indexes; paginate lists; cap query result sizes (NFR-1102) |
| R-1107 | Brain placeholder mistaken for a broken feature | Low | Low | Explicit "arriving in Epic 12" copy (FR-1115) |

---

## 12. Glossary

| Term | Definition |
|------|-----------|
| **Operator Console** | The read-only web dashboard delivered by this epic; a single pane of glass over all seven agents |
| **Single pane of glass** | One screen/URL from which the whole autonomous company's state is legible |
| **Control plane** | The command-and-control interface — Telegram — through which Cesar drives the agents; the console is deliberately *not* this |
| **Honesty state** | An explicit "no data yet" or "not configured" UI state shown instead of fabricated/placeholder data (from FounderOS-DEMO) |
| **Thin read API** | A minimal read-only endpoint layer over `eworks.db`; the only new backend surface permitted |
| **Brain view** | The knowledge-graph view reserved for Epic 12; a placeholder route in this epic |
| **FounderOS-DEMO** | External Next.js operator-console reference project used for UI shape only, not forked (analysis §3) |
| **eworks.db** | The shared SQLite database (`data/eworks.db`) owned by `eworks/core/database.py` |
| **Eworks OS** | The multi-agent company operating system platform this console sits on top of |
</content>
</invoke>
