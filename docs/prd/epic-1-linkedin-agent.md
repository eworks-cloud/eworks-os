# PRD — Epic 1: LinkedIn Prospecting Agent
**Product:** Eworks OS — Multi-Agent Company Operating System
**Epic:** E1 — LinkedIn Prospecting Agent
**Version:** 1.0.0
**Status:** Draft
**Author:** Morgan (PM)
**Owner:** Cesar Schneider, Eworks Labs
**Last Updated:** 2026-05-19

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

The LinkedIn Prospecting Agent is the **first autonomous agent** in the Eworks OS platform. It replaces manual prospecting by continuously scanning LinkedIn for high-fit leads, scoring them against an Ideal Customer Profile (ICP), generating personalized outreach via Claude AI, sending messages on behalf of Cesar Schneider, and reporting pipeline activity to Cesar over Telegram.

This epic constitutes the **MVP** of the Eworks OS platform and serves as the foundation pattern (auth → ingest → score → act → track → report) for all subsequent agents.

---

## 2. Business Objective

| Item | Detail |
|------|--------|
| **Problem** | Cesar manually prospects on LinkedIn, which is time-consuming, inconsistent, and unscalable. |
| **Solution** | An autonomous agent that prospecting pipeline runs 24/7 without manual effort. |
| **Primary KPI** | 50+ qualified prospects contacted per week with < 2 hrs of human oversight. |
| **Secondary KPIs** | ≥ 15% reply rate; ≥ 5% conversion to discovery call booked; < $50/mo infrastructure cost at MVP. |
| **Strategic Value** | Proves the Eworks OS agent architecture, generates immediate revenue pipeline, and becomes a productized offering for agency clients. |

---

## 3. Stakeholders

| Role | Name | Responsibility |
|------|------|---------------|
| Product Owner | Cesar Schneider | Final approval on ICP, messages, scope |
| PM | Morgan | PRD ownership, sprint planning |
| Tech Lead | TBD | Architecture decisions |
| AI Engineer | TBD | Claude prompt engineering |
| QA | TBD | Acceptance testing |

---

## 4. Assumptions & Background

- **A-001** — Cesar has or can obtain a LinkedIn account in good standing.
- **A-002** — LinkedIn's official API (Campaign Manager / Marketing API) has limited access for messaging; browser automation via Playwright may be required as primary or fallback mechanism.
- **A-003** — Claude API (Anthropic) is available with sufficient rate limits for message generation.
- **A-004** — A Telegram Bot token is provisioned and Cesar is the sole recipient of reports.
- **A-005** — The ICP is defined by Cesar before development begins and is storable as structured JSON config.
- **A-006** — All data processed is publicly visible LinkedIn profile data; no scraping of private or hidden data.
- **A-007** — The agent runs on a cloud VPS or managed container platform (e.g., Railway, Fly.io, AWS EC2).
- **A-008** — A PostgreSQL database is available for state management and tracking.

---

## 5. Functional Requirements

### 5.1 Authentication & Session Management

**FR-001 — LinkedIn Authentication**
The system SHALL authenticate with LinkedIn using one of:
- (Primary) LinkedIn OAuth 2.0 via official API where endpoints are available.
- (Fallback) Browser automation (Playwright) with stored session cookies and 2FA handling support.
Session credentials SHALL be encrypted at rest and refreshed automatically before expiry.

**FR-002 — Session Persistence**
The system SHALL persist authenticated LinkedIn sessions across agent restarts without requiring re-login unless the session is explicitly invalidated by LinkedIn.

**FR-003 — Authentication Health Check**
The system SHALL perform a session validity check before every scheduled run and alert Cesar via Telegram if authentication fails, pausing all outreach activity until re-authenticated.

**FR-004 — Credential Vault Integration**
All credentials (LinkedIn password, API keys, Claude API key, Telegram token) SHALL be stored in an environment variable store or secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager, or a `.env` file gitignored locally). Credentials SHALL never be committed to version control.

---

### 5.2 Data Ingestion — Prospect Discovery

**FR-005 — Connections Reader**
The system SHALL retrieve a list of Cesar's 1st-degree LinkedIn connections, including:
- Full name, headline, current company, location, profile URL, profile picture URL, connection date, mutual connections count.

**FR-006 — Profile Visitors Reader**
The system SHALL retrieve the list of LinkedIn members who viewed Cesar's profile within the past 7 days (subject to LinkedIn API/visibility limits), capturing available fields (full name, headline, company, profile URL).

**FR-007 — Search-Based Prospect Discovery**
The system SHALL execute configurable LinkedIn search queries (keywords, job titles, industries, geographies, company sizes) to discover new prospects beyond Cesar's existing network.

**FR-008 — Deduplication**
The system SHALL maintain a prospect registry in the database. Before processing any profile, it SHALL check for an existing record by LinkedIn profile URL and skip re-processing profiles that have been contacted within a configurable cooldown window (default: 90 days).

**FR-009 — Profile Detail Enrichment**
For each candidate prospect, the system SHALL fetch full profile details including:
- Work history (last 3 positions), education, skills, about section, recent activity/posts, shared connections, and company info.

---

### 5.3 ICP Scoring & Filtering

**FR-010 — ICP Configuration**
The system SHALL load an ICP definition from a structured configuration file (JSON/YAML) that specifies:
- Target job titles (include/exclude lists)
- Target industries
- Company size range (employee count)
- Geographic targets
- Seniority levels
- Keywords to match in headline or about section
- Negative signals (e.g., competitor companies, specific titles to exclude)

**FR-011 — Prospect Scoring Engine**
The system SHALL score each prospect against the ICP using a weighted scoring model (0–100 scale). Scoring components SHALL include:
- Job title match (weight: 30%)
- Industry match (weight: 20%)
- Company size fit (weight: 15%)
- Geography match (weight: 10%)
- Keyword presence in profile (weight: 15%)
- Engagement signals (viewed profile, mutual connections) (weight: 10%)

**FR-012 — Score Threshold Filtering**
The system SHALL only advance prospects with a score ≥ configurable threshold (default: 65/100) to the outreach queue. Prospects below threshold SHALL be stored with status `FILTERED_OUT` and their score recorded for reporting.

**FR-013 — Priority Queue**
Qualified prospects SHALL be inserted into an outreach queue ordered by score descending, with profile visitors prioritized over search results, and search results prioritized over passive connections.

---

### 5.4 Message Generation

**FR-014 — Claude AI Message Generation**
For each prospect in the outreach queue, the system SHALL call the Claude API with:
- A system prompt defining Cesar's persona, value proposition, and tone guidelines.
- A user prompt containing the prospect's structured profile data.
- Instructions to generate a personalized connection request message (≤ 300 characters) or InMail message (≤ 1,900 characters).

**FR-015 — Message Variants**
The system SHALL generate two message variants per prospect (A and B) to support future A/B testing. The variant used for initial send SHALL be configurable (default: A).

**FR-016 — Message Quality Gate**
Before queuing a message for send, the system SHALL validate:
- Message length is within LinkedIn limits.
- Message contains the prospect's name.
- Message does not contain placeholder text (e.g., `[NAME]`, `{{company}}`).
- Message does not contain prohibited content (spam signals, excessive links).
If validation fails, the message SHALL be regenerated (up to 3 retries before escalating to Cesar).

**FR-017 — Human Review Mode**
The system SHALL support an optional `REVIEW_BEFORE_SEND` mode (configurable per-run) where generated messages are sent to Cesar via Telegram for approval/rejection before being dispatched. Cesar SHALL be able to reply `approve`, `reject`, or `edit [new message]` within a 2-hour window before the agent auto-skips.

---

### 5.5 Outreach Execution

**FR-018 — Connection Request Sending**
The system SHALL send LinkedIn connection requests with personalized note text to prospects who are not 1st-degree connections, respecting LinkedIn's weekly invite limits (max ~100–150/week enforced via internal counter).

**FR-019 — InMail Sending**
The system SHALL send LinkedIn InMail messages to Open Profiles or existing connections, tracking InMail credit consumption and pausing when credits fall below a configurable minimum (default: 5 remaining).

**FR-020 — Rate Limiting & Human-Pattern Simulation**
The system SHALL enforce safe sending rates to avoid LinkedIn account restrictions:
- Maximum 20 outreach actions per day.
- Random delay of 30–180 seconds between actions.
- No sending between 11 PM – 7 AM in Cesar's local timezone (America/Sao_Paulo or configurable).
- Weekend sending disabled by default (configurable).

**FR-021 — Send Failure Handling**
If a send action fails (network error, LinkedIn rejection, CAPTCHA), the system SHALL:
- Log the failure with error type.
- Retry up to 2 times with exponential backoff.
- On persistent failure, move the prospect to `SEND_FAILED` status and notify Cesar via Telegram.

---

### 5.6 Tracking & CRM

**FR-022 — Prospect State Machine**
Each prospect SHALL progress through a defined state machine:
```
DISCOVERED → SCORED → FILTERED_OUT
                    ↘
                  QUEUED → PENDING_REVIEW → REJECTED
                         ↘
                        SENT → ACCEPTED / REPLIED / MEETING_BOOKED / NO_RESPONSE
```

**FR-023 — Reply Detection**
The system SHALL poll LinkedIn messages at a configurable interval (default: every 4 hours) and detect new replies from contacted prospects. On reply detection, the prospect's status SHALL be updated to `REPLIED` and Cesar SHALL be notified via Telegram with the reply content.

**FR-024 — Meeting Booking Detection**
The system SHALL scan reply content for meeting signals (calendar links such as Calendly/Cal.com URLs, phrases like "let's schedule", "book a call") and update the prospect's status to `MEETING_BOOKED`, triggering a Telegram notification.

**FR-025 — CRM Data Export**
The system SHALL provide a daily CSV/JSON export of all prospect records (with status, scores, messages sent, replies) to a configurable destination (Google Sheets via API, email attachment, or local file), enabling Cesar to maintain an external CRM view.

---

### 5.7 Reporting

**FR-026 — Daily Telegram Summary Report**
At a configurable time each day (default: 8:00 AM Cesar's timezone), the system SHALL send a Telegram message to Cesar containing:
- Prospects discovered (today / this week / all-time)
- Prospects scored and qualified
- Messages sent today / this week
- Replies received today / this week
- Meetings booked today / this week
- InMail credits remaining
- Any errors or alerts requiring attention

**FR-027 — Weekly Digest Report**
Every Monday at 9:00 AM, the system SHALL send a richer weekly Telegram digest with:
- Top 5 prospects by score who haven't been contacted yet
- Conversion funnel metrics (discover → qualify → send → reply → meeting)
- Running 30-day reply rate and meeting rate
- Suggested ICP tuning based on which scores correlated with replies

**FR-028 — On-Demand Report**
Cesar SHALL be able to send `/report` to the Telegram bot at any time to receive the latest daily summary immediately.

**FR-029 — Error Alerting**
The system SHALL send an immediate Telegram alert (not batched) for any critical errors: auth failure, > 5 consecutive send failures, service downtime > 15 minutes.

---

### 5.8 Scheduling & Orchestration

**FR-030 — Scheduled Execution**
The agent SHALL run on a configurable cron schedule (default: daily at 9:00 AM Cesar's timezone) using an internal scheduler (APScheduler or system cron). Each run SHALL:
1. Validate authentication.
2. Ingest new prospects.
3. Score and enqueue qualified prospects.
4. Send messages up to daily limit.
5. Check replies and update statuses.
6. Generate and send daily report.

**FR-031 — Manual Trigger**
Cesar SHALL be able to trigger an immediate agent run by sending `/run` to the Telegram bot.

**FR-032 — Pause / Resume Control**
Cesar SHALL be able to send `/pause` and `/resume` to the Telegram bot to temporarily halt all outreach activity (e.g., during vacation). Pause state SHALL persist across agent restarts.

---

## 6. Non-Functional Requirements

**NFR-001 — Reliability**
The agent SHALL achieve ≥ 99% successful scheduled run completion rate, measured weekly. Failed runs SHALL auto-retry once after a 10-minute delay.

**NFR-002 — Performance**
A full prospecting run (ingest + score + send + report) SHALL complete within 30 minutes for batches of up to 50 prospects.

**NFR-003 — Security**
- All secrets SHALL be stored encrypted (env secrets manager); never in plaintext files or logs.
- LinkedIn session cookies SHALL be encrypted at rest using AES-256.
- The Telegram bot SHALL only respond to commands from Cesar's verified Telegram user ID (whitelist).
- Database connections SHALL use TLS.
- No prospect PII SHALL be logged at DEBUG level.

**NFR-004 — Scalability**
The architecture SHALL support processing up to 500 prospects per day without redesign, achieved by batching and async processing.

**NFR-005 — Maintainability**
- Code SHALL follow PEP 8 (Python) or equivalent style guide for the chosen language.
- All agent modules SHALL have ≥ 80% unit test coverage.
- ICP configuration, scoring weights, message templates, and rate limits SHALL all be externalized as configuration (no hardcoded business logic).

**NFR-006 — Observability**
- All agent runs SHALL emit structured JSON logs (timestamp, run_id, step, status, duration_ms, error).
- Logs SHALL be shipped to a centralized log store (e.g., Loki, CloudWatch, or Papertrail).
- A health check HTTP endpoint (`GET /health`) SHALL return agent status, last run time, and queue depth.

**NFR-007 — Resilience**
- The agent SHALL be stateless between runs (all state in database), enabling restart/redeploy without data loss.
- All external API calls (LinkedIn, Claude, Telegram) SHALL have configurable timeout (default: 30s) and retry logic (3 retries, exponential backoff).

**NFR-008 — Cost Efficiency**
- Claude API costs per message generation SHALL be minimized by caching profile data and using concise prompts.
- Infrastructure cost SHALL remain under $50/month at MVP scale.
- Claude token usage SHALL be tracked per run and reported in the weekly digest.

**NFR-009 — Privacy & Compliance**
- The agent SHALL only access LinkedIn data that is publicly visible or accessible to Cesar's account.
- No bulk export or storage of profile data beyond what is necessary for prospecting workflow.
- Prospect data SHALL be purgeable on request (right to erasure compliance pattern).
- The agent SHALL comply with LinkedIn's Terms of Service to the maximum extent possible given the use case.

**NFR-010 — Auditability**
- Every message sent SHALL be stored with full content, timestamp, and method (API/automation) in the database.
- Every state transition for every prospect SHALL be logged with timestamp and trigger reason.
- A full audit trail SHALL be queryable via the CRM export.

**NFR-011 — Portability**
- The agent SHALL be containerized (Docker) with a `docker-compose.yml` for local development.
- Deployment SHALL be repeatable via a single command or CI/CD pipeline (GitHub Actions).

---

## 7. Constraints

**CON-001 — LinkedIn Terms of Service**
The agent MUST NOT violate LinkedIn's User Agreement or Professional Community Policies. Specifically:
- No mass automated scraping beyond what is permitted.
- Connection request volume must stay within LinkedIn's published safe limits (~100/week).
- No impersonation or misleading content in messages.
*Risk: LinkedIn may update its ToS. The team must monitor LinkedIn developer policy updates quarterly.*

**CON-002 — LinkedIn API Limitations**
LinkedIn's official API does not expose all required data (e.g., profile visitor list requires LinkedIn Premium; InMail requires Sales Navigator API). Browser automation (Playwright) is required as a complement, adding maintenance overhead and fragility risk when LinkedIn updates its front-end.

**CON-003 — Claude API Rate Limits**
Claude API calls for message generation are subject to Anthropic's rate limits. The agent MUST queue generation requests and implement backoff to avoid 429 errors. Budget for API costs must be approved before launch.

**CON-004 — Single LinkedIn Account Scope**
MVP operates on Cesar's single LinkedIn account only. Multi-account support is out of scope for Epic 1.

**CON-005 — No Real-Time Interaction**
The agent is asynchronous and schedule-driven. It does NOT conduct real-time conversation threading (auto-reply to prospect responses). Reply detection is read-only; human response is always Cesar's responsibility.

**CON-006 — Data Residency**
All prospect data must be stored in a database within a jurisdiction acceptable to Cesar and Eworks Labs. Default: cloud region in the Americas. GDPR considerations apply if EU prospects are targeted.

**CON-007 — Telegram as Sole UI**
The MVP has no web dashboard. All control, reporting, and alerting is delivered exclusively through the Telegram bot interface. This limits the richness of data visualization but minimizes build complexity.

---

## 8. User Stories & Acceptance Criteria

---

### US-001 — ICP Configuration
**As** Cesar,
**I want** to define my Ideal Customer Profile in a config file,
**So that** the agent targets only the types of leads most likely to convert to Eworks clients.

**Acceptance Criteria:**
- [ ] A `icp_config.json` (or `.yaml`) file exists and is documented with all available fields.
- [ ] The agent loads and validates the ICP config on startup; invalid config causes a startup error with a descriptive message.
- [ ] Changing the ICP config and restarting the agent causes new runs to use the updated ICP without any code changes.
- [ ] The config supports title include/exclude lists, industry list, company size range, geography list, seniority level list, and keyword list.

---

### US-002 — LinkedIn Authentication
**As** Cesar,
**I want** the agent to authenticate with my LinkedIn account securely and maintain that session automatically,
**So that** I don't have to manually log in or babysit the agent.

**Acceptance Criteria:**
- [ ] The agent successfully authenticates with LinkedIn on first setup via an initialization script.
- [ ] Session is persisted and reused across 5 consecutive agent runs without re-prompting for credentials.
- [ ] If the session expires, the agent sends a Telegram alert: *"LinkedIn session expired. Please run `/reauth` to re-authenticate."*
- [ ] Credentials are not present in any log file or the Git repository.

---

### US-003 — Prospect Discovery
**As** Cesar,
**I want** the agent to automatically discover potential prospects from my LinkedIn connections, profile visitors, and search results,
**So that** I have a continuous flow of new leads without manual searching.

**Acceptance Criteria:**
- [ ] Each daily run discovers at least 10 new candidate profiles from at least 2 sources (connections, visitors, search).
- [ ] Duplicate profiles (same LinkedIn URL) are not re-added to the discovery queue.
- [ ] Previously contacted profiles (within 90-day cooldown) are skipped and logged.
- [ ] Discovered prospects appear in the database within 5 minutes of run completion.

---

### US-004 — Prospect Scoring
**As** Cesar,
**I want** prospects to be automatically scored against my ICP,
**So that** I only invest outreach effort on the highest-fit leads.

**Acceptance Criteria:**
- [ ] Every discovered prospect receives a numeric score (0–100).
- [ ] Score breakdown by component (title, industry, company size, geography, keywords, engagement) is stored in the database.
- [ ] Prospects with score < 65 are marked `FILTERED_OUT` and excluded from the outreach queue.
- [ ] The top-10 highest-scoring uncontacted prospects appear in the weekly Telegram digest.
- [ ] Score calculation completes in < 1 second per prospect.

---

### US-005 — Personalized Message Generation
**As** Cesar,
**I want** the agent to generate a personalized LinkedIn outreach message for each qualified prospect using Claude AI,
**So that** my outreach feels human and relevant, not spammy.

**Acceptance Criteria:**
- [ ] Each message references at least one specific detail from the prospect's profile (title, company, recent post, or shared connection).
- [ ] Connection request notes are ≤ 300 characters; InMail messages are ≤ 1,900 characters.
- [ ] No message contains un-replaced template placeholders.
- [ ] Messages are generated in the same language as the prospect's profile (English default; Spanish if profile is in Spanish).
- [ ] 3 regeneration retries occur before escalation; escalation sends a Telegram alert to Cesar.

---

### US-006 — Human Review Before Send
**As** Cesar,
**I want** the option to review and approve messages before they are sent,
**So that** I maintain quality control during the early agent rollout phase.

**Acceptance Criteria:**
- [ ] When `REVIEW_BEFORE_SEND=true`, each generated message is sent to Cesar's Telegram with options: `approve`, `reject`, `edit [text]`.
- [ ] Approving sends the message within 60 seconds.
- [ ] Rejecting marks the prospect as `REJECTED` and logs the reason.
- [ ] Editing replaces the message content with Cesar's provided text and sends it.
- [ ] If no response within 2 hours, the prospect is skipped and re-queued for the next run with a Telegram reminder.

---

### US-007 — Message Sending
**As** Cesar,
**I want** the agent to send LinkedIn connection requests and InMail messages on my behalf,
**So that** prospecting happens automatically without me being online.

**Acceptance Criteria:**
- [ ] Connection requests are sent with the personalized note attached.
- [ ] The agent respects a maximum of 20 outreach actions per day.
- [ ] No messages are sent between 11 PM and 7 AM Cesar's local time.
- [ ] Each send action is logged with timestamp, prospect ID, message content, and method.
- [ ] A test mode (`DRY_RUN=true`) sends no real messages but logs what would have been sent.

---

### US-008 — Reply Monitoring
**As** Cesar,
**I want** to be notified on Telegram when a prospect replies to my LinkedIn message,
**So that** I can follow up quickly and not miss sales opportunities.

**Acceptance Criteria:**
- [ ] The agent checks for new replies every 4 hours.
- [ ] On detecting a new reply, Cesar receives a Telegram notification within 15 minutes containing: prospect name, company, their message text, and a direct link to the LinkedIn conversation.
- [ ] The prospect's status is updated to `REPLIED` in the database.
- [ ] If a reply contains a Calendly/Cal.com link or "schedule" keyword, status updates to `MEETING_BOOKED` and a separate Telegram alert is sent.

---

### US-009 — Daily Telegram Report
**As** Cesar,
**I want** to receive a daily summary report on Telegram each morning,
**So that** I can track the agent's performance at a glance without logging into any system.

**Acceptance Criteria:**
- [ ] Report is sent daily at 8:00 AM Cesar's timezone (configurable).
- [ ] Report includes: prospects discovered, qualified, messages sent, replies received, meetings booked — all for today and rolling 7 days.
- [ ] Report includes InMail credits remaining and any error alerts.
- [ ] Sending `/report` at any time triggers an immediate copy of the report.
- [ ] Report delivery failure triggers a retry within 5 minutes.

---

### US-010 — Agent Pause/Resume Control
**As** Cesar,
**I want** to pause and resume all agent outreach activity via Telegram commands,
**So that** I can stop the agent during vacations or sensitive periods without redeploying.

**Acceptance Criteria:**
- [ ] `/pause` command halts all outreach and confirms: *"Agent paused. No messages will be sent until you send /resume."*
- [ ] `/resume` re-enables outreach and confirms: *"Agent resumed. Next run scheduled for [time]."*
- [ ] Paused state persists if the agent container restarts.
- [ ] While paused, discovery and scoring still run but messages are not sent.
- [ ] Daily reports still send during pause, showing "Outreach paused" in the send section.

---

### US-011 — On-Demand Agent Run
**As** Cesar,
**I want** to trigger an immediate agent run via Telegram,
**So that** I can test the agent or process fresh prospects outside the regular schedule.

**Acceptance Criteria:**
- [ ] `/run` command triggers a full agent run immediately.
- [ ] Cesar receives a Telegram confirmation: *"Run started. I'll report back when done."*
- [ ] On completion, Cesar receives a run summary (prospects found, scored, messages sent, errors).
- [ ] If a run is already in progress, the command responds: *"A run is already in progress. I'll notify you when it completes."*

---

### US-012 — CRM Data Export
**As** Cesar,
**I want** to export all prospect data as a CSV or to Google Sheets,
**So that** I can share pipeline data with my team and do custom analysis.

**Acceptance Criteria:**
- [ ] `/export` command generates a CSV file and sends it as a Telegram document attachment within 60 seconds.
- [ ] CSV contains: prospect name, company, title, LinkedIn URL, ICP score, status, date contacted, message sent, reply text, meeting booked date.
- [ ] Google Sheets integration (if configured) auto-syncs daily after each run.
- [ ] Export contains all prospects, not just those contacted.

---

## 9. Out of Scope (Epic 1)

The following items are explicitly excluded from Epic 1 and will be addressed in future epics or iterations:

- **Multi-account support** — Agent operates on Cesar's account only. No team/agency-wide multi-seat prospecting.
- **Automated reply threading** — The agent detects replies but does NOT auto-respond. All conversational replies are human-driven by Cesar.
- **Email outreach** — Outreach is LinkedIn-only. Email sequences are out of scope.
- **CRM integrations** — No native HubSpot, Pipedrive, or Salesforce sync in MVP. CSV/Sheets export is the integration mechanism.
- **Web dashboard** — No browser-based UI. Telegram is the sole interface.
- **A/B test analytics** — Messages have A/B variants stored, but automated split testing analytics are not implemented in MVP.
- **Prospect company research** — The agent uses profile data only; no deep company enrichment via Clearbit, Apollo, or similar.
- **Calendar booking automation** — The agent detects meeting signals but does not auto-send calendar invites.
- **LinkedIn Ads integration** — No connection to LinkedIn paid advertising workflows.
- **Content publishing** — No posting to LinkedIn on Cesar's behalf (Epic 2 scope).
- **Proposal generation** — Out of scope; addressed in Epic 3.
- **Multi-language ICP config** — MVP ICP config is English-only (messages can be in Spanish per prospect language detection).

---

## 10. Dependencies

| ID | Dependency | Type | Owner | Required By |
|----|-----------|------|-------|-------------|
| DEP-001 | LinkedIn account (Premium or Sales Navigator recommended) | External | Cesar | Sprint 1 |
| DEP-002 | Claude API key (Anthropic) | External | Engineering | Sprint 1 |
| DEP-003 | Telegram Bot Token + Cesar's Telegram User ID whitelisted | External | Cesar | Sprint 1 |
| DEP-004 | PostgreSQL database provisioned | Infrastructure | Engineering | Sprint 1 |
| DEP-005 | Cloud hosting environment (Docker-capable) | Infrastructure | Engineering | Sprint 1 |
| DEP-006 | ICP definition document from Cesar | Business | Cesar | Sprint 1 — before scoring dev |
| DEP-007 | Message tone/persona brief from Cesar | Business | Cesar | Sprint 2 — before Claude prompt dev |
| DEP-008 | LinkedIn Developer App (OAuth) — optional; for API access | External | Engineering | Sprint 2 |
| DEP-009 | Google Sheets API credentials — optional; for CRM sync | External | Engineering | Sprint 3 |
| DEP-010 | Calendly/Cal.com webhook or URL pattern — for meeting detection | Business | Cesar | Sprint 3 |

---

## 11. Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|-----------|
| R-001 | LinkedIn detects automation and restricts Cesar's account | Medium | High | Rate limiting, human-pattern delays, using official API where possible, starting with low volumes |
| R-002 | LinkedIn changes front-end; Playwright scripts break | High | Medium | Abstract selectors into config; monitor LinkedIn changelog; allocate 1 day/sprint for maintenance |
| R-003 | Claude API quality insufficient for personalization | Low | Medium | Invest in prompt engineering; implement human review mode as safety net |
| R-004 | ICP definition is too broad or too narrow | Medium | Medium | Start with conservative ICP; iterate based on reply rate data after 2 weeks |
| R-005 | GDPR / data privacy concern if EU prospects are included | Low | High | Implement data purge endpoint; document lawful basis; exclude EU prospects in MVP if needed |
| R-006 | Telegram Bot becomes unreachable (network/token issue) | Low | Medium | Health check monitors Telegram connectivity; fallback to email alert for critical failures |

---

## 12. Glossary

| Term | Definition |
|------|-----------|
| **ICP** | Ideal Customer Profile — a description of the company/individual who would get maximum value from Eworks Labs services |
| **InMail** | LinkedIn's paid direct messaging system allowing messages to non-connections |
| **Prospect** | A LinkedIn member identified as a potential Eworks client |
| **Score** | A numeric 0–100 value representing how well a prospect matches the ICP |
| **State Machine** | The defined set of statuses a prospect can hold and the rules governing transitions |
| **Dry Run** | An agent execution mode that simulates all actions without sending real messages |
| **Connection Request** | A LinkedIn invitation to connect, optionally including a note (≤ 300 chars) |
| **Profile Visitor** | A LinkedIn user who viewed Cesar's profile (visible with Premium account) |
| **Playwright** | A browser automation framework used for web scraping and UI interaction |
| **Claude** | Anthropic's AI model used for personalized message generation |
| **Eworks OS** | The overarching multi-agent operating system platform of which this agent is Epic 1 |
