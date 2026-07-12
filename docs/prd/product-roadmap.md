# Eworks OS — Product Roadmap
**Product:** Eworks OS — Multi-Agent Company Operating System
**Organization:** Eworks Labs AI Agency
**Version:** 1.0.0
**Status:** Living Document
**Author:** Morgan (PM)
**Last Updated:** 2026-05-19

---

> **See also:** [`autonomous-company-platform-analysis.md`](../architecture/autonomous-company-platform-analysis.md) — comparison against FounderOS-DEMO, gstack, and gbrain. Scoped into [Epic 11](./epic-11-operator-console.md) and [Epic 12](./epic-12-knowledge-management.md) below.

## Vision Statement

> **Eworks OS is the autonomous operating system of Eworks Labs** — a network of specialized AI agents that together handle prospecting, content, proposals, project management, billing, and customer success, freeing the team to focus exclusively on strategy and delivery.

The platform is built agent-by-agent. Each epic ships a fully functional, production-ready agent. Agents share a common infrastructure layer (database, auth, Telegram interface, scheduler) and progressively integrate with each other to create a fully automated agency operations loop.

---

## Roadmap Summary

| Epic | Agent | Theme | Status | Target Quarter |
|------|-------|-------|--------|---------------|
| E1 | LinkedIn Prospecting Agent | **Acquire** | 🟡 In Development | Q2 2026 |
| E2 | Content Pipeline Agent | **Attract** | 📋 Planned | Q3 2026 |
| E3 | Proposal Generation Agent | **Convert** | 📋 Planned | Q3 2026 |
| E4 | Project Management Agent | **Deliver** | 📋 Planned | Q4 2026 |
| E5 | Invoice & Billing Agent | **Monetize** | 📋 Planned | Q4 2026 |
| E6 | Customer Success Agent | **Retain** | 📋 Planned | Q1 2027 |

---

## Platform Architecture Principles

All agents share the following foundational platform services:

- **Eworks Core** — Shared Python library with base agent class, scheduler, database ORM, logging, and secrets management.
- **Eworks DB** — PostgreSQL database with schemas per agent; shared `prospects`, `clients`, `projects` tables.
- **Eworks Bot** — Telegram bot interface with command routing per agent; Cesar's single pane of glass.
- **Eworks AI** — Shared Claude API client with prompt library, token tracking, and cost reporting.
- **Eworks Auth** — Credential vault abstraction supporting env vars, Vault, and AWS Secrets Manager.

Each agent is a Docker container. The full platform runs via `docker-compose` locally or Kubernetes in production.

---

---

## Epic 1 — LinkedIn Prospecting Agent
**Theme:** Acquire
**Status:** 🟡 In Development
**Target:** Q2 2026 (Sprint 1–4)
**PRD:** [`epic-1-linkedin-agent.md`](./epic-1-linkedin-agent.md)

### Description
The LinkedIn Prospecting Agent is the first and most urgent agent in Eworks OS. It autonomously discovers, scores, and reaches out to potential clients on LinkedIn on behalf of Cesar Schneider, and reports pipeline activity via Telegram. This agent eliminates manual prospecting and creates a consistent, measurable top-of-funnel.

### Business Value
- Eliminates ~10 hrs/week of manual prospecting work
- Creates a repeatable, data-driven pipeline with measurable KPIs
- Proves the Eworks OS agent architecture pattern
- Itself becomes a productized offering to sell to other agencies

### Key Features
- **LinkedIn Authentication** — OAuth + Playwright session management
- **Multi-Source Prospect Discovery** — Connections, profile visitors, keyword search
- **ICP Scoring Engine** — Weighted 0–100 score against configurable Ideal Customer Profile
- **Claude-Powered Message Generation** — Personalized connection notes and InMails
- **Human Review Mode** — Optional Telegram-based approve/reject before sending
- **Safe Rate-Limited Sending** — Max 20/day, human-pattern delays, timezone-aware
- **Reply & Meeting Detection** — Polled inbox monitoring with instant Telegram alerts
- **Telegram Control Interface** — `/run`, `/pause`, `/resume`, `/report`, `/export`
- **Daily & Weekly Reports** — Funnel metrics, top prospects, conversion rates
- **CRM Export** — CSV download via Telegram + optional Google Sheets sync

### Estimated Stories
| Story ID | Title | Points |
|----------|-------|--------|
| US-001 | ICP Configuration | 3 |
| US-002 | LinkedIn Authentication | 5 |
| US-003 | Prospect Discovery | 8 |
| US-004 | Prospect Scoring | 5 |
| US-005 | Message Generation | 8 |
| US-006 | Human Review Mode | 5 |
| US-007 | Message Sending | 8 |
| US-008 | Reply Monitoring | 5 |
| US-009 | Daily Telegram Report | 3 |
| US-010 | Pause/Resume Control | 2 |
| US-011 | On-Demand Run | 2 |
| US-012 | CRM Data Export | 3 |
| **Total** | | **57 pts** |

### Dependencies
- LinkedIn Premium or Sales Navigator account
- Anthropic Claude API key
- Telegram Bot token
- PostgreSQL database
- ICP definition from Cesar
- Message tone/persona brief from Cesar

### Success Metrics
- ≥ 50 qualified prospects contacted per week
- ≥ 15% reply rate at steady state
- ≥ 5% meeting booking rate
- < 2 hours/week human oversight required
- Zero LinkedIn account restrictions

---

---

## Epic 2 — Content Pipeline Agent
**Theme:** Attract
**Status:** 📋 Planned
**Target:** Q3 2026 (Sprint 5–8)
**Depends On:** E1 (Eworks Core, Eworks Bot, Eworks AI)

### Description
The Content Pipeline Agent manages Eworks Labs' LinkedIn and Twitter/X content strategy end-to-end. It researches trending topics in the AI agency space, drafts posts, schedules publishing, and tracks engagement — keeping Cesar's personal brand active and authority-building without requiring manual content creation.

### Business Value
- Maintains consistent brand presence (3–5 posts/week) without manual effort
- Increases inbound leads via thought leadership content
- Complements Epic 1 by warming up prospects before and after outreach
- Provides content performance data to optimize messaging strategy

### Key Features
- **Topic Research** — Monitors AI, automation, and agency news via RSS feeds, Reddit, LinkedIn trending, and Twitter/X trends.
- **Content Calendar Management** — Maintains a 2-week rolling content calendar with post ideas, drafts, and scheduled publish times.
- **Claude-Powered Drafting** — Generates LinkedIn posts (short-form and carousel), Twitter/X threads, and newsletter sections in Cesar's voice.
- **Content Type Variety** — Supports: insights/opinion, case study highlights, tool reviews, behind-the-scenes, client win announcements.
- **Multi-Platform Publishing** — Publishes to LinkedIn (personal profile + company page) and Twitter/X via official APIs.
- **Engagement Monitoring** — Tracks likes, comments, shares, impressions per post; surfaces high-performing content patterns.
- **Repurposing Engine** — Automatically adapts high-performing LinkedIn posts into Twitter threads and vice versa.
- **Human Approval Queue** — All drafts presented to Cesar via Telegram for approve/edit/reject before publishing.
- **Performance Reports** — Weekly Telegram digest with top posts, engagement rates, follower growth, and content recommendations.
- **Prospect Cross-Reference** — Tags content engagement by prospects in E1 database (e.g., "Prospect Jane Doe liked your post").

### Estimated Stories
| Area | Stories | Estimated Points |
|------|---------|-----------------|
| Topic Research & RSS ingestion | 3 stories | 13 pts |
| Content Calendar & Draft Queue | 4 stories | 16 pts |
| Claude Post Generation | 3 stories | 13 pts |
| LinkedIn Publishing API | 3 stories | 11 pts |
| Twitter/X Publishing API | 2 stories | 8 pts |
| Engagement Tracking | 3 stories | 10 pts |
| Repurposing Engine | 2 stories | 8 pts |
| Telegram Approval Flow | 2 stories | 6 pts |
| Reports & Analytics | 2 stories | 7 pts |
| **Total** | **24 stories** | **~92 pts** |

### Dependencies
- E1 Eworks Core, Eworks Bot, Eworks AI (platform)
- LinkedIn API Developer App with content publishing permissions
- Twitter/X API v2 Developer App
- Content persona/voice guide from Cesar
- Initial content topic categories from Cesar

### Success Metrics
- 4+ posts published per week consistently
- Average post engagement rate ≥ 3%
- Inbound LinkedIn connection requests from content ≥ 10/week
- < 30 min/week human content review time

---

---

## Epic 3 — Proposal Generation Agent
**Theme:** Convert
**Status:** 📋 Planned
**Target:** Q3 2026 (Sprint 7–10)
**Depends On:** E1 (prospect/client data), E2 (content performance context)

### Description
The Proposal Generation Agent accelerates deal conversion by automatically drafting bespoke proposals for qualified prospects who have expressed interest. When Cesar flags a prospect as ready for a proposal, the agent researches the prospect's company, selects relevant Eworks case studies and service packages, and generates a polished, branded proposal document — ready for Cesar's review in minutes rather than hours.

### Business Value
- Reduces proposal creation time from 3–4 hours to 15 minutes
- Enables Cesar to respond to opportunities faster, improving close rates
- Standardizes proposal quality and structure
- Creates a reusable proposal knowledge base over time

### Key Features
- **Prospect Context Ingestion** — Pulls prospect profile, company info, and conversation history from E1 database.
- **Company Research** — Enriches proposal context by researching the prospect's company via web search (Perplexity API or similar), extracting pain points, recent news, company size, tech stack signals.
- **Service Package Matcher** — Maps prospect needs to Eworks Labs service packages (defined in config: AI automation, agent development, consulting, etc.).
- **Case Study Library** — Maintains a searchable library of Eworks case studies; auto-selects 2–3 most relevant for the prospect's industry and pain points.
- **Claude Proposal Drafting** — Generates a full multi-section proposal: executive summary, problem statement, proposed solution, deliverables, timeline, investment, why Eworks, social proof, next steps.
- **Branded Document Output** — Renders the proposal to a PDF using a branded template (WeasyPrint or Pandoc + CSS), or populates a Google Docs template.
- **Proposal Delivery** — Sends the PDF to Cesar via Telegram for review; on approval, optionally emails directly to the prospect.
- **Proposal Tracking** — Tracks proposal status: drafted, reviewed, sent, opened (if using email tracking), accepted, declined.
- **Pricing Engine** — Applies configurable pricing rules and discount tiers based on deal size and service type.
- **Follow-up Scheduling** — After proposal is sent, schedules a polite follow-up message (via E1 LinkedIn agent) if no response after N days.

### Estimated Stories
| Area | Stories | Estimated Points |
|------|---------|-----------------|
| Prospect context ingestion | 2 stories | 8 pts |
| Company research enrichment | 3 stories | 13 pts |
| Service package matcher | 2 stories | 8 pts |
| Case study library & selector | 3 stories | 11 pts |
| Claude proposal drafting | 4 stories | 18 pts |
| Document rendering (PDF/Docs) | 3 stories | 13 pts |
| Telegram review + delivery | 2 stories | 7 pts |
| Proposal tracking | 2 stories | 8 pts |
| Pricing engine | 2 stories | 8 pts |
| Follow-up scheduling | 2 stories | 6 pts |
| **Total** | **25 stories** | **~100 pts** |

### Dependencies
- E1 prospect database and client data
- Eworks Labs service catalog document (from Cesar)
- Case study library (at least 5 case studies from Cesar)
- Branded proposal template (design asset)
- Pricing model document (from Cesar)
- Web search API (Perplexity, Serper, or Tavily)
- Email sending capability (SendGrid or similar)

### Success Metrics
- Proposal draft generation time < 15 minutes from trigger
- Cesar review + approval time < 30 minutes
- Proposal acceptance rate ≥ 30%
- 100% of accepted proposals tracked in database

---

---

## Epic 4 — Project Management Agent
**Theme:** Deliver
**Status:** 📋 Planned
**Target:** Q4 2026 (Sprint 11–14)
**Depends On:** E3 (accepted proposals/contracts), E1 (client records)

### Description
The Project Management Agent automates the operational overhead of running client projects at Eworks Labs. Once a proposal is accepted, this agent creates the project structure, assigns tasks, monitors progress, identifies blockers, and keeps clients and Cesar informed — acting as an autonomous project coordinator.

### Business Value
- Eliminates manual project setup and status update tasks
- Reduces risk of missed deadlines or deliverables
- Improves client experience with proactive communication
- Provides real-time project health visibility to Cesar via Telegram

### Key Features
- **Project Initialization** — On contract acceptance, auto-creates project in the chosen PM tool (Linear, Notion, ClickUp, or internal) with templated tasks based on the service type from the proposal.
- **Task Template Library** — Maintains service-type task templates (e.g., "AI Agent Build" template, "Consulting Engagement" template) that are cloned per project.
- **Milestone Tracking** — Defines and monitors key milestones; alerts Cesar when milestones are at risk (> 2 days behind schedule).
- **Client Status Updates** — Generates and sends weekly client status update emails/messages (Claude-drafted, Cesar-approved) with progress, completed items, next steps.
- **Blocker Detection** — Scans task statuses daily; identifies tasks overdue > 1 day and pings the responsible team member via Telegram.
- **Time Tracking Integration** — Integrates with Toggl or similar for time-vs-estimate tracking per project and task.
- **Deliverable Review Queue** — When a deliverable is marked complete, agent notifies Cesar for review before client delivery.
- **Project Health Dashboard** — Daily Telegram summary showing: active projects, on-track/at-risk/delayed counts, upcoming milestones, hours burned vs. budget.
- **Retrospective Prompts** — On project closure, generates a retrospective questionnaire and summarizes learnings for the Eworks knowledge base.
- **Capacity Planning** — Tracks Cesar's and team members' project load; alerts when capacity is near 100%.

### Estimated Stories
| Area | Stories | Estimated Points |
|------|---------|-----------------|
| Project initialization & templates | 4 stories | 16 pts |
| PM tool integration (Linear/ClickUp) | 3 stories | 13 pts |
| Milestone & deadline tracking | 3 stories | 11 pts |
| Client status update generation | 3 stories | 12 pts |
| Blocker detection & alerts | 2 stories | 8 pts |
| Time tracking integration | 2 stories | 8 pts |
| Deliverable review queue | 2 stories | 7 pts |
| Health dashboard & reports | 3 stories | 10 pts |
| Retrospective & knowledge base | 2 stories | 8 pts |
| Capacity planning | 2 stories | 8 pts |
| **Total** | **26 stories** | **~101 pts** |

### Dependencies
- E3 accepted proposal/contract data
- E1 client database records
- Chosen PM tool API access (Linear, ClickUp, Notion, or custom)
- Toggl or similar time tracking API
- Service delivery process documentation from Cesar
- Task templates per service type (from Cesar)

### Success Metrics
- Project setup time after contract signing < 30 minutes (automated)
- 100% of at-risk milestones surfaced to Cesar ≥ 24 hrs before deadline
- Client satisfaction score ≥ 4.5/5 on project communication
- < 1 hr/week of manual PM overhead per active project

---

---

## Epic 5 — Invoice & Billing Agent
**Theme:** Monetize
**Status:** 📋 Planned
**Target:** Q4 2026 (Sprint 13–15)
**Depends On:** E4 (project milestones, time tracking), E3 (pricing/contract data)

### Description
The Invoice & Billing Agent automates the entire revenue collection cycle for Eworks Labs — from generating invoices at the right time based on project milestones or retainer schedules, to chasing overdue payments with polite automated follow-ups, to reconciling payments and reporting revenue to Cesar.

### Business Value
- Eliminates manual invoice creation and tracking
- Reduces days-sales-outstanding (DSO) via automated reminders
- Provides real-time revenue visibility to Cesar
- Ensures no billable milestone is ever missed or invoiced late

### Key Features
- **Invoice Generation** — Auto-generates invoices at project milestones or on retainer billing dates, using data from E3 (pricing) and E4 (time tracking). Renders professional PDF invoices using a branded template.
- **Billing Integration** — Integrates with Stripe (one-time and recurring payments) and/or sends invoices via Conta Azul, FreshBooks, or QuickBooks.
- **Automated Sending** — Emails invoices to client billing contacts with personalized cover note (Claude-drafted).
- **Payment Tracking** — Monitors invoice status: draft, sent, viewed, partially paid, paid, overdue.
- **Overdue Follow-ups** — Sends automated, polite payment reminder emails at: 3 days before due, day of due, 3 days overdue, 7 days overdue (escalating tone). Cesar is notified at 7-day overdue mark.
- **Revenue Dashboard** — Daily Telegram report showing: monthly recurring revenue (MRR), outstanding invoices, overdue amounts, payments received this week/month.
- **Expense Tracking** — Records known operating expenses (API costs, tools, subcontractors) from config and actual receipts (via email parsing or manual input).
- **Profitability Reports** — Monthly P&L summary per project and overall: revenue, COGS (API costs, contractor time), gross margin.
- **Tax Preparation Export** — Quarterly export of income/expense data in formats compatible with Brazilian tax requirements (or configurable jurisdiction).
- **Retainer Management** — Manages monthly retainer clients: auto-renews invoices, tracks hours used vs. retainer cap, alerts when a client is near or over their retainer hours.

### Estimated Stories
| Area | Stories | Estimated Points |
|------|---------|-----------------|
| Invoice generation & PDF rendering | 4 stories | 16 pts |
| Stripe / billing platform integration | 3 stories | 13 pts |
| Automated invoice sending | 2 stories | 7 pts |
| Payment tracking & status | 3 stories | 11 pts |
| Overdue follow-up sequences | 3 stories | 11 pts |
| Revenue dashboard & Telegram reports | 3 stories | 10 pts |
| Expense tracking | 2 stories | 8 pts |
| Profitability reports | 2 stories | 8 pts |
| Tax export | 2 stories | 7 pts |
| Retainer management | 3 stories | 11 pts |
| **Total** | **27 stories** | **~102 pts** |

### Dependencies
- E3 contract/pricing data
- E4 milestone completion signals and time tracking data
- Stripe account (or chosen payment processor)
- Client billing contact data
- Invoice branding/template design assets
- Accountant input on Brazilian tax export format

### Success Metrics
- 100% of milestone-based invoices generated within 24 hours of milestone completion
- Days Sales Outstanding (DSO) reduced to < 15 days
- Zero missed billable milestones
- Monthly revenue report delivered to Cesar by 1st of each month
- < 30 min/month of manual billing administration

---

---

## Epic 6 — Customer Success Agent
**Theme:** Retain
**Status:** 📋 Planned
**Target:** Q1 2027 (Sprint 16–19)
**Depends On:** E4 (project data), E5 (billing/payment data), E1 (client records)

### Description
The Customer Success Agent ensures every Eworks Labs client remains satisfied, engaged, and expanding their relationship with the agency. It monitors client health signals, automates check-in communications, surfaces upsell opportunities, manages renewal conversations, and builds client loyalty — transforming one-time project clients into long-term retainer partners.

### Business Value
- Increases client retention rate and reduces churn
- Identifies upsell/cross-sell opportunities without manual monitoring
- Automates post-project follow-ups that are often neglected
- Builds systematic client relationship management at scale
- Closes the full agency operations loop when combined with E1–E5

### Key Features
- **Client Health Scoring** — Calculates a health score (0–100) per client based on: project delivery quality, invoice payment behavior, communication responsiveness, NPS survey scores, and usage/engagement signals. Alerts Cesar when a client's score drops below threshold.
- **Automated Check-ins** — Schedules and sends periodic check-in messages to active clients (monthly for retainers, quarterly for past project clients) via LinkedIn or email, Claude-drafted and Cesar-approved.
- **NPS Survey Automation** — Sends Net Promoter Score surveys at project completion and at 90-day intervals for retainer clients. Parses responses and updates client health score.
- **Upsell Opportunity Detection** — Scans client interactions, project types, and LinkedIn activity to identify upsell signals (e.g., client is hiring for roles the agent could automate, client shared a content pain point). Surfaces opportunities to Cesar via Telegram.
- **Renewal Management** — For retainer clients, initiates renewal conversation 30 days before contract end date. Generates a renewal proposal (via E3 integration) with updated pricing if applicable.
- **Client Knowledge Base** — Maintains a per-client profile with: all projects, communications, preferences, key stakeholders, pain points, and relationship notes. Accessible via Telegram query (`/client [name]`).
- **Testimonial & Case Study Pipeline** — At project close and on positive NPS score, automatically requests a testimonial or LinkedIn recommendation. Stores and tracks testimonials for use in E3 proposals.
- **Referral Program Management** — Tracks client referrals; sends thank-you messages and referral incentives automatically when a referred client signs.
- **Client Anniversary Alerts** — Notifies Cesar of client relationship anniversaries and long-term engagement milestones; generates a personalized thank-you message.
- **Churn Risk Intervention** — When health score drops to red zone, triggers an immediate Cesar alert with AI-suggested intervention actions and talking points.
- **Lifetime Value Dashboard** — Weekly Telegram report showing: active clients, churn risk clients, upsell pipeline, MRR breakdown by client, projected annual contract value.

### Estimated Stories
| Area | Stories | Estimated Points |
|------|---------|-----------------|
| Client health scoring | 4 stories | 16 pts |
| Automated check-in messages | 3 stories | 11 pts |
| NPS survey automation | 3 stories | 12 pts |
| Upsell opportunity detection | 4 stories | 16 pts |
| Renewal management + proposals | 3 stories | 12 pts |
| Client knowledge base & query | 3 stories | 13 pts |
| Testimonial & case study pipeline | 2 stories | 8 pts |
| Referral program management | 2 stories | 8 pts |
| Client anniversary & relationship | 2 stories | 6 pts |
| Churn risk detection & intervention | 3 stories | 12 pts |
| LTV dashboard & reports | 2 stories | 8 pts |
| **Total** | **31 stories** | **~122 pts** |

### Dependencies
- E1 client records and LinkedIn messaging capability
- E4 project delivery and milestone data
- E5 payment history and billing status
- E3 proposal generation for renewal documents
- Email sending capability
- NPS survey tooling (Typeform API or custom)
- Client contract/agreement data

### Success Metrics
- Client retention rate ≥ 85% month-over-month
- NPS score ≥ 50 (world-class)
- Upsell revenue ≥ 20% of total MRR
- 100% of at-risk clients (health score < 40) flagged to Cesar within 24 hours
- Testimonial collected from ≥ 60% of completed projects

---

---

## Platform Roadmap Summary

### Cumulative Story Estimates

| Epic | Stories | Points | Quarter |
|------|---------|--------|---------|
| E1 — LinkedIn Prospecting Agent | 12 | 57 | Q2 2026 |
| E2 — Content Pipeline Agent | 24 | ~92 | Q3 2026 |
| E3 — Proposal Generation Agent | 25 | ~100 | Q3 2026 |
| E4 — Project Management Agent | 26 | ~101 | Q4 2026 |
| E5 — Invoice & Billing Agent | 27 | ~102 | Q4 2026 |
| E6 — Customer Success Agent | 31 | ~122 | Q1 2027 |
| **Platform Total** | **145** | **~574** | **Q1 2027** |

### Integration Map

```
E1 LinkedIn Prospecting
    │ (prospect → client conversion)
    ▼
E3 Proposal Generation ◄──── E2 Content Pipeline
    │ (accepted proposal)         (brand awareness)
    ▼
E4 Project Management
    │ (milestone completions)
    ▼
E5 Invoice & Billing
    │ (payment history, contract data)
    ▼
E6 Customer Success ◄──────── E1 (re-engagement)
         │
         └──► E3 (renewal proposals)
```

### Agent Communication Protocols

All agents communicate through:
1. **Shared Database** — Primary state exchange mechanism
2. **Internal Events** — PostgreSQL NOTIFY/LISTEN or Redis pub/sub for real-time triggers
3. **Telegram Bot** — Cesar's unified command-and-control interface
4. **Scheduled Jobs** — APScheduler with configurable cron expressions per agent

---

## Beyond the Roadmap — Future Epics (Backlog)

The following epics are candidates for the Eworks OS backlog post-Q1 2027:

- **E7 — Recruiting & HR Agent** — Automates job posting, applicant screening, and interview scheduling for Eworks Labs team growth.
- **E8 — Financial Intelligence Agent** — Deep financial modeling, cashflow forecasting, and tax optimization recommendations.
- **E9 — Partnership & Referral Agent** — Manages agency partner relationships, co-marketing, and referral tracking.
- **E10 — White-Label Client Deployments** — Packages Eworks OS as a productized SaaS offering for other agencies.

### Scoped Follow-On Epics (from platform analysis)

Two additive-integration epics have been scoped from [`autonomous-company-platform-analysis.md`](../architecture/autonomous-company-platform-analysis.md). These build on top of the already-shipped agents rather than adding new business agents. They take the next free epic folder numbers (**11** and **12**) to avoid collision with the existing `epic-7`…`epic-10` folders; the analysis doc referred to them by the old-roadmap placeholder labels "E7"/"E11", which are **not** their real numbers.

- **Epic 11 — Operator Console** — A read-only Next.js web dashboard giving Cesar a "single pane of glass" over all seven existing agents, reading real data from `eworks/core/database.py` (SQLite). Additive to Telegram, never a replacement. PRD: [`epic-11-operator-console.md`](./epic-11-operator-console.md).
- **Epic 12 — Knowledge Management Agent** — Integrates gbrain (PGLite embedded, MIT-licensed, zero new server/Docker) as a shared cross-agent memory/knowledge layer that nurturer, closer, and connector write into, enabling synthesized `/client [name]` queries. SQLite stays the system of record. PRD: [`epic-12-knowledge-management.md`](./epic-12-knowledge-management.md).
- **Epic 13 — AI Provider Resilience Layer** — Adds `eworks/core/ai.py`, a standalone, opt-in, provider-agnostic AI client with Anthropic as primary and automatic, explicitly-configured fallback to four open-source-model providers (AWS Bedrock, DeepInfra, Fireworks.ai, Together.ai) on primary failure — plus a circuit breaker, fallback provenance tagging, and the first token/cost-tracking hooks. Fulfills the "Eworks AI" shared-client promise above; does not migrate the 12 existing `import anthropic` call sites (future epic). PRD: [`epic-13-ai-provider-resilience.md`](./epic-13-ai-provider-resilience.md).

---

*This roadmap is a living document. Priorities may shift based on revenue impact, technical learnings from E1, and market feedback. All roadmap changes require PM (Morgan) and PO (Cesar) sign-off.*
