# Eworks OS — Analyst Brainstorming Output
**Role:** @analyst (Atlas)
**Date:** 2026-05-19
**Project:** Eworks Multi-Agent Company Operating System
**Status:** Pre-PRD Research & Brainstorming

---

## 1. Product Vision Statement

Eworks OS is a multi-agent operating system that transforms Eworks Labs from a manually-driven agency into a self-operating business — where specialized AI agents handle prospecting, content, proposals, project delivery, billing, and customer success in a coordinated, autonomous loop.

The system gives Cesar Schneider and the Eworks team a **CEO-level command layer**: define strategy once, and let the agents execute continuously — from first LinkedIn touchpoint to signed contract, delivered project, and paid invoice.

Where other automation tools handle single workflows, Eworks OS orchestrates an entire company's operations as a coherent, interconnected intelligence — making the agency itself the product.

---

## 2. Problem Statement — What Pain Does This Solve for Cesar?

### The Core Pain: Agency Founder's Trap
Cesar runs an AI agency/software house where *he* is simultaneously the salesperson, account manager, content creator, proposal writer, and delivery lead. This is the classic **agency founder's bottleneck** — revenue is capped by Cesar's personal hours, and every operational task he handles is time *not* spent on strategy, product, or high-value client work.

### Specific Pains Addressed

**Prospecting & Sales**
- Manual LinkedIn prospecting is time-consuming, inconsistent, and doesn't scale
- No systematic way to identify and warm up ideal prospects daily
- Personalized outreach at volume is practically impossible without automation
- Follow-up sequences fall through the cracks without a dedicated SDR

**Content & Brand**
- Content production requires creative energy that competes with delivery work
- Inconsistent posting leads to inconsistent pipeline
- No closed-loop between content performance and prospecting targeting

**Proposals**
- Writing custom proposals for every lead is repetitive and eats hours
- Proposal quality varies depending on Cesar's bandwidth that week
- Slow turnaround on proposals loses warm leads

**Project Delivery**
- Context-switching between management, delivery, and business development
- Manual status updates, task tracking, and client communications
- No automated early-warning system for at-risk projects

**Billing & Revenue**
- Invoice creation and follow-up is administrative friction
- No automated revenue forecasting or cash flow visibility
- Payment chasing is awkward and often delayed

**Customer Success**
- Post-delivery relationship maintenance is reactive, not proactive
- No systematic upsell/cross-sell triggers
- Client churn often detectable in hindsight, not real-time

### The Net Result
Eworks OS removes Cesar from the operational loop on repeatable tasks, compresses the sales cycle, and makes the agency capable of handling 3–5x the client volume without proportional headcount growth.

---

## 3. Target Users — Who Operates This OS?

### Primary Operator: Cesar Schneider (Founder / CEO)
- Sets strategy, ICP, offers, and agent parameters
- Reviews agent outputs before send (initially) or sets auto-approve thresholds
- Monitors dashboards and intervenes on edge cases
- The system works *for* him — not the other way around

### Secondary Operators (as team scales)
| Role | Interaction with OS |
|---|---|
| Account Manager | Reviews CS agent reports; approves upsell proposals |
| Sales / BD | Monitors prospecting queue; handles warm leads passed by agent |
| Content Lead | Reviews content drafts; sets brand guidelines fed into content agent |
| Finance | Reviews invoice logs; approves billing edge cases |

### The OS Persona Concept
Each agent has a defined persona (name, tone, role), so to external parties (prospects, clients), interactions feel human and on-brand — not bot-generated. The OS operates *behind* the Eworks brand identity.

---

## 4. ICP Definition — LinkedIn Prospecting Agent

### Who is the Ideal Customer for Eworks Labs?

Eworks Labs is an AI agency / software house. The ICP should reflect clients who:
1. Have a real business problem solvable with AI/automation/custom software
2. Have budget to engage an agency (not bootstrapped solopreneurs)
3. Have decision-making authority (or direct access to it)
4. Are in an industry where Eworks has case studies or credibility

### ICP Profile (Primary)

**Segment: Mid-Market Tech-Adjacent Company Leader**

| Attribute | Definition |
|---|---|
| **Title** | Founder, CEO, COO, CTO, Head of Operations, VP of Product, Director of Digital |
| **Company Size** | 10–200 employees (SMB to mid-market) |
| **Industry** | SaaS, Fintech, Proptech, Healthtech, E-commerce, Professional Services, Logistics, EdTech |
| **Geography** | LATAM (primary: Brazil, Argentina, Colombia, Mexico), USA/Canada (secondary), EU (tertiary) |
| **Company Stage** | Series A–C startups, or established SMBs undergoing digital transformation |
| **Pain Signals** | Talking about automation, AI, digital transformation, scaling ops, cutting costs, process inefficiency |
| **Tech Stack Signals** | Uses tools like HubSpot, Salesforce, Notion, Monday, Zapier, Make — indicating operational maturity |
| **Budget Proxy** | Has raised funding, or >$2M ARR, or 15+ employees |
| **Decision Authority** | Is the buyer or has direct access to the buyer |

### ICP Profile (Secondary)

**Segment: Agency / Consultancy Owner**
- Other agency owners looking to white-label AI capabilities
- Marketing agencies wanting to add AI/automation services for their clients
- Management consultancies needing implementation muscle

### Negative ICP (Exclusions)
- Solo founders with no funding and <5 employees (low budget, slow decisions)
- Enterprise companies with long procurement cycles (>6 months to close)
- Non-technical businesses with no digital product (e.g., local retail, food service)
- Companies that have had bad AI project experiences (high objection overhead)

### ICP Signals to Detect on LinkedIn
- **Posts about**: AI, automation, digital transformation, scaling, ops challenges
- **Engages with**: AI thought leaders, SaaS tools, process content
- **Recent activity**: Has posted in last 30 days (indicating active presence)
- **Job changes**: Recently promoted or changed role (new broom effect = budget & initiative)
- **Company growth signals**: Hiring posts, product launches, funding announcements
- **Mutual connections**: Shared network with Cesar (trust amplification)

---

## 5. Full Agent Roster

### Agent 01 — LinkedIn Prospecting Agent (MVP)
| Field | Detail |
|---|---|
| **Codename** | `Prospector` |
| **Purpose** | Identify, qualify, and cold-outreach ideal prospects on LinkedIn |
| **Trigger** | Scheduled (daily, configurable time window) |
| **Inputs** | Cesar's LinkedIn session/cookies, ICP definition, offer templates, message templates, exclusion list |
| **Outputs** | Sent LinkedIn messages, prospect records (name, company, title, profile URL, message sent, timestamp), follow-up queue |
| **Handoff To** | Proposal Agent (when prospect responds positively) |

**Sub-tasks:**
1. Scan Cesar's connections and 2nd-degree network
2. Filter by ICP criteria (title, company size, industry, activity signals)
3. Score and rank prospects (priority queue)
4. Craft personalized message (name, company, specific pain, tailored offer)
5. Send LinkedIn DM
6. Log to CRM/database
7. Monitor responses and flag hot leads

---

### Agent 02 — Content Pipeline Agent (Partially Built)
| Field | Detail |
|---|---|
| **Codename** | `Publisher` |
| **Purpose** | Generate, schedule, and publish LinkedIn/social content for Cesar's personal brand and Eworks brand |
| **Trigger** | Scheduled (weekly content batch) + on-demand |
| **Inputs** | Content briefs, past top-performing posts, industry news feed, Cesar's voice/tone profile, ICP pain points |
| **Outputs** | Drafted posts (text + image prompts), scheduled publish queue, performance reports |
| **Handoff To** | Prospecting Agent (content engagement signals → warm audience list) |

**Sub-tasks:**
1. Research trending topics in target industries
2. Generate post drafts in Cesar's authentic voice
3. Create hook variations for A/B testing
4. Generate image/visual prompts for each post
5. Schedule across platforms (LinkedIn, Instagram, Twitter/X)
6. Track engagement metrics
7. Feed high-performing post themes back into ICP refinement

---

### Agent 03 — Proposal Generation Agent
| Field | Detail |
|---|---|
| **Codename** | `Closer` |
| **Purpose** | Automatically generate tailored project proposals when a prospect expresses interest |
| **Trigger** | Hot lead flagged by Prospector OR manual trigger by Cesar |
| **Inputs** | Prospect data (company, pain, budget signals), discovery call notes (if exists), service catalog, past proposal templates, pricing rules |
| **Outputs** | Branded PDF proposal, cover email draft, follow-up sequence |
| **Handoff To** | Project Management Agent (on proposal acceptance) |

**Sub-tasks:**
1. Pull prospect context from CRM
2. Map prospect pain to relevant Eworks service packages
3. Generate executive summary, scope, timeline, pricing
4. Apply brand template and formatting
5. Draft personalized cover email
6. Send via email or LinkedIn
7. Track open/read status; trigger follow-up if no response in 48h

---

### Agent 04 — Project Management Agent
| Field | Detail |
|---|---|
| **Codename** | `Conductor` |
| **Purpose** | Orchestrate project delivery — tasks, timelines, team coordination, client updates |
| **Trigger** | Proposal accepted / contract signed |
| **Inputs** | Signed proposal/SOW, team availability, tool integrations (Linear, Notion, Jira), client contact info |
| **Outputs** | Project plan, task assignments, status reports, client update emails, risk alerts |
| **Handoff To** | Billing Agent (on milestone/project completion) |

**Sub-tasks:**
1. Parse accepted proposal to extract deliverables and timeline
2. Create project in PM tool (Linear/Notion) with milestones and tasks
3. Send project kickoff email to client
4. Send weekly status updates automatically
5. Monitor task completion and flag delays
6. Trigger re-scoping alerts if scope creep detected
7. Generate final delivery report

---

### Agent 05 — Invoice & Billing Agent
| Field | Detail |
|---|---|
| **Codename** | `Treasurer` |
| **Purpose** | Generate invoices, track payments, send reminders, report on revenue |
| **Trigger** | Milestone completion event from PM Agent OR recurring date |
| **Inputs** | Project data, pricing from proposal, payment terms, client billing info, accounting tool integration |
| **Outputs** | PDF invoices, payment reminders, revenue reports, overdue alerts |
| **Handoff To** | Customer Success Agent (on payment received → project closed) |

**Sub-tasks:**
1. Generate invoice from project/milestone data
2. Send invoice via email with payment link
3. Track payment status (paid/pending/overdue)
4. Send automated reminders at 3, 7, 14 days overdue
5. Escalate to Cesar if invoice >30 days overdue
6. Generate monthly revenue summary and cash flow forecast
7. Sync with accounting software (QuickBooks, Conta Azul, Xero)

---

### Agent 06 — Customer Success Agent
| Field | Detail |
|---|---|
| **Codename** | `Nurturer` |
| **Purpose** | Maintain post-delivery client relationships, detect churn signals, trigger upsells |
| **Trigger** | Project closed + scheduled check-ins + response to client communications |
| **Inputs** | Client history, project outcomes, satisfaction signals, communication logs, upsell opportunities catalog |
| **Outputs** | Check-in messages, NPS/CSAT surveys, upsell proposals (sent to Proposal Agent), churn risk alerts |
| **Handoff To** | Proposal Agent (for upsell) or Prospector context list (for referrals) |

**Sub-tasks:**
1. Send post-delivery satisfaction check (day 7, day 30)
2. Conduct NPS survey (automated)
3. Monitor client communication sentiment (email/LinkedIn)
4. Flag churn risk signals to Cesar
5. Identify upsell/expansion opportunities based on usage and growth
6. Request referrals from satisfied clients
7. Maintain relationship warmth with monthly value-add touchpoints

---

### Agent 00 — Orchestrator (Meta-Agent)
| Field | Detail |
|---|---|
| **Codename** | `Command` |
| **Purpose** | Central coordinator — routes events between agents, manages state, handles escalations |
| **Trigger** | Always-on event listener |
| **Inputs** | Events from all agents, Cesar's strategy inputs, override commands |
| **Outputs** | Routing decisions, agent task queues, dashboard state, alert notifications to Cesar |

---

## 6. Key Capabilities Per Agent (Functional Requirements)

### Prospector (LinkedIn Agent) — Functional Requirements

**FR-P01: Profile Scanning**
- Scan Cesar's 1st-degree connections (full list)
- Scan 2nd-degree connections visible via LinkedIn
- Extract: name, title, company, location, headline, recent posts, mutual connections

**FR-P02: ICP Scoring**
- Score each prospect against ICP criteria (weighted scoring model)
- Filter out exclusion list (already contacted, existing clients, explicit exclusions)
- Rank top N prospects per day (configurable, e.g. 10–20/day)

**FR-P03: Message Personalization**
- Pull prospect name, company, role, and 1 specific signal (recent post, job change, etc.)
- Inject into message template with dynamic fields
- Generate 2–3 message variants per day (A/B rotation)
- Ensure no duplicate messages to same person

**FR-P04: Message Dispatch**
- Send LinkedIn DM via LinkedIn session automation (Puppeteer/Playwright or API)
- Respect daily send limits (max 20–25 connection requests OR messages/day)
- Add randomized human-like delay between sends (30–120 seconds)
- Log send status, timestamp, message text

**FR-P05: Response Monitoring**
- Check LinkedIn inbox for replies from prospected leads
- Classify response sentiment (interested / not interested / question / unsubscribe)
- Flag "interested" responses as hot leads in CRM
- Notify Cesar on Telegram/Slack for hot leads

**FR-P06: Data Persistence**
- Log all prospect interactions to database (Supabase/Airtable/Notion)
- Never re-contact a prospect within configurable cooldown (default: 90 days)
- Export prospect log as CSV on demand

---

### Publisher (Content Agent) — Functional Requirements

**FR-C01:** Generate minimum 3 posts/week across formats (text, carousel hook, poll)
**FR-C02:** Maintain consistent Cesar voice profile (trained on past posts)
**FR-C03:** Track post performance metrics (impressions, engagement, comments)
**FR-C04:** Feed top-performing topics back to Prospector as signal data
**FR-C05:** Support multi-language content (PT-BR and EN)

---

### Closer (Proposal Agent) — Functional Requirements

**FR-PR01:** Generate full proposal document in <5 minutes from trigger
**FR-PR02:** Support service catalog with pricing tiers (fixed, hourly, retainer)
**FR-PR03:** Brand-consistent PDF output (Eworks template)
**FR-PR04:** Track proposal open/read events (email tracking pixel or DocSend)
**FR-PR05:** Auto-follow-up if no response in 48h (configurable)
**FR-PR06:** Proposal versioning — track which version was accepted

---

### Conductor (PM Agent) — Functional Requirements

**FR-PM01:** Parse proposal to extract deliverables, milestones, timeline automatically
**FR-PM02:** Create project structure in Linear/Notion via API
**FR-PM03:** Send branded client-facing status updates weekly (email)
**FR-PM04:** Detect milestone slippage and alert Cesar + client proactively
**FR-PM05:** Generate end-of-project delivery report

---

### Treasurer (Billing Agent) — Functional Requirements

**FR-B01:** Generate invoice from project data (line items, amounts, due date)
**FR-B02:** Support BRL and USD invoicing (multi-currency)
**FR-B03:** Integrate with payment processors (Stripe, PIX, bank transfer)
**FR-B04:** Auto-reminder cadence: 3 / 7 / 14 days after due date
**FR-B05:** Monthly P&L and cash flow summary report
**FR-B06:** Sync with accounting tool (Conta Azul, QuickBooks, or Xero)

---

### Nurturer (CS Agent) — Functional Requirements

**FR-CS01:** Automated check-in messages at day 7, 30, 90 post-project
**FR-CS02:** NPS survey dispatch and result logging
**FR-CS03:** Sentiment analysis on incoming client emails
**FR-CS04:** Upsell trigger when client signals growth or new pain
**FR-CS05:** Referral request at NPS score ≥8

---

## 7. Non-Functional Requirements

### Security & Privacy
- **NFR-S01:** LinkedIn credentials stored encrypted (never in plaintext); use environment secrets manager (AWS Secrets Manager, Doppler, or Vault)
- **NFR-S02:** Prospect personal data (PII) stored with LGPD/GDPR compliance; data minimization principle applied
- **NFR-S03:** All agent actions logged with immutable audit trail
- **NFR-S04:** Role-based access: Cesar has full control; any future staff access scoped to their domain only
- **NFR-S05:** No prospect data sold or shared externally; data retention policy defined (e.g., 12 months)

### Scalability & Performance
- **NFR-SC01:** System must handle concurrent operation of all 6 agents without performance degradation
- **NFR-SC02:** LinkedIn agent must operate within safe rate limits even as prospecting volume increases
- **NFR-SC03:** Proposal generation must complete in <5 minutes end-to-end
- **NFR-SC04:** Orchestrator must handle event backlog without message loss (persistent queue)
- **NFR-SC05:** Architecture must support adding new agents without re-engineering core

### LinkedIn-Specific Constraints (Critical)
- **NFR-LI01:** Maximum **20 connection requests/day** on free LinkedIn; up to 100/week on Sales Navigator
- **NFR-LI02:** Maximum **~150 messages/day** on LinkedIn (practical safe limit: 50/day for longevity)
- **NFR-LI03:** Human-like behavior patterns required: randomized delays, non-uniform timing, varied message length
- **NFR-LI04:** No bulk same-template blasting — each message must have personalization variance
- **NFR-LI05:** Session management must handle LinkedIn's bot detection (no datacenter IPs; use residential proxy or local machine)
- **NFR-LI06:** LinkedIn Sales Navigator API is preferred over browser automation where possible (significantly safer)

### Reliability
- **NFR-R01:** If LinkedIn session expires, agent pauses and alerts Cesar rather than failing silently
- **NFR-R02:** All agent runs produce a structured log (success/fail/error per action)
- **NFR-R03:** Retry logic with exponential backoff on transient failures
- **NFR-R04:** System operates on scheduled windows; no 24/7 LinkedIn automation (unnatural pattern)

### Observability
- **NFR-O01:** Real-time dashboard showing: messages sent today, responses received, hot leads flagged, proposals in flight, projects active, invoices outstanding
- **NFR-O02:** Cesar receives daily digest via Telegram bot
- **NFR-O03:** Critical alerts (hot lead, overdue invoice, at-risk project) sent immediately

---

## 8. Risks & Constraints

### LinkedIn ToS & Account Safety (HIGH RISK)

| Risk | Severity | Mitigation |
|---|---|---|
| LinkedIn account restriction/ban | **Critical** | Stay under rate limits, use human-like patterns, avoid datacenter IPs, consider Sales Navigator |
| LinkedIn detecting automation via browser fingerprinting | High | Use Playwright with stealth plugins; run on local machine or residential proxy |
| LinkedIn API access revoked | High | Build abstraction layer so browser automation and API can be swapped |
| Connection request spam complaints | High | Highly personalized messages, low daily volume, warm targeting (2nd degree + mutual connections first) |
| LinkedIn changing DOM/UI (breaking browser automation) | Medium | Automated UI tests to detect breakage; rapid response SLA |

**Key Principle:** Start conservative (10 messages/day), scale slowly over 30–60 days to build account trust before hitting higher limits. **Never start at max volume.**

### API & Technical Constraints

| Risk | Severity | Mitigation |
|---|---|---|
| LinkedIn has no official public API for messaging | High | Use Sales Navigator API (partner program) OR Playwright/Puppeteer with stealth |
| OpenAI/LLM API rate limits | Low | Implement queuing; use multiple API keys if needed |
| Data quality — incomplete LinkedIn profiles | Medium | ICP scoring handles partial data; skip if too many fields missing |
| Proxy IP blocking by LinkedIn | Medium | Use residential proxies; preferred: run on Cesar's own machine/network |

### Data Privacy

| Risk | Severity | Mitigation |
|---|---|---|
| LGPD (Brazil) compliance for prospect data collection | High | Only collect publicly visible LinkedIn data; clear data retention; provide opt-out |
| GDPR compliance for EU prospects | Medium | Same as LGPD; add EU-specific data handling if EU targeting expands |
| Storing prospect PII in database | Medium | Encrypt at rest; minimal data retention; documented data policy |

### Business & Operational Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Low reply rate making ROI unclear | Medium | Continuous A/B testing of messages; ICP refinement; 2–5% reply rate is realistic baseline |
| Personalization quality not good enough (generic-feeling) | Medium | Use strong prompt engineering + real prospect signals (recent post, mutual connection) |
| Cesar's voice/brand not reflected in agent outputs | Medium | Voice training dataset from Cesar's existing content; human review in early phase |
| Agent generates and sends inappropriate message | High | Human-in-the-loop review for first 30 days before full autonomy; hard content filters |
| Over-automation damaging Eworks reputation | High | Gradual autonomy unlock; Cesar reviews before full auto-send initially |

---

## 9. Competitive Landscape

### Market Context
The LinkedIn automation and sales intelligence space is crowded, but most tools are **single-function point solutions**. None operate as a full company OS.

### Direct LinkedIn Outreach Competitors

| Tool | What It Does | Weakness vs Eworks OS |
|---|---|---|
| **Expandi** | LinkedIn automation — connection requests, messaging sequences | No AI personalization; no company OS layer; single function |
| **Lemlist** | Email + LinkedIn outreach with personalization | No deep LinkedIn scanning; no agent ecosystem; manual ICP setup |
| **Dux-Soup** | LinkedIn browser automation | Outdated; basic; high ban risk; no AI |
| **PhantomBuster** | LinkedIn scraping + automation phantoms | Tool-based, not AI-native; no intelligent agent layer; complex setup |
| **MeetAlfred** | LinkedIn + email sequences | Template-based, not AI-personalized; no OS concept |
| **Waalaxy** | LinkedIn + email multichannel | EU-focused; no AI generation; no company OS |

### Sales Intelligence / Data Enrichment

| Tool | What It Does | Weakness vs Eworks OS |
|---|---|---|
| **Apollo.io** | Contact database + email outreach + sequencing | Email-first; LinkedIn is secondary; no company OS; not built for agencies |
| **Clay** | Data enrichment + waterfall enrichment + AI messaging | Powerful but complex; no LinkedIn sending; no company OS; expensive |
| **Lusha / ZoomInfo** | Contact data enrichment | Data only; no outreach; no agent ecosystem |
| **Hunter.io** | Email finding | Single function; no LinkedIn |

### AI Agent / Automation Platforms

| Tool | What It Does | Weakness vs Eworks OS |
|---|---|---|
| **n8n / Make / Zapier** | Workflow automation building blocks | Tools to build with, not a product; no AI intelligence; requires manual setup |
| **HubSpot Sequences** | CRM + outreach sequences | Template-based; no AI; expensive; not LinkedIn-native |
| **Salesforce Einstein** | Enterprise AI CRM | Enterprise-only; no LinkedIn automation; not SMB/agency-relevant |
| **Artisan AI** | AI SDR agent (Ava) | Closest competitor; email-first; not full company OS; not customizable |
| **11x.ai** | AI sales rep | Early stage; email-focused; no company OS |

### How Eworks OS Differs (Competitive Differentiation)

1. **Full Company OS, not a point tool** — Eworks OS connects prospecting → proposal → delivery → billing → CS in one coordinated system. No competitor does this end-to-end.

2. **Built for agency operations specifically** — The agent design reflects the actual workflow of an AI agency: project-based, proposal-driven, relationship-heavy. Generic tools don't understand this context.

3. **Founder-first design** — Designed so a solo founder (Cesar) can operate like a team of 10. The OS *replaces* hires, not just tools.

4. **AI-native from day 1** — Not a template automation system with AI bolted on. Every agent is intelligence-first: reasoning about context, generating unique outputs, learning from feedback.

5. **Eworks-specific training** — Voice model, ICP model, and service catalog are trained on Eworks' actual history — not generic. This is the moat.

6. **White-label potential** — Once proven internally, Eworks OS can be productized and sold to other agencies — making it both an internal tool and a future product revenue stream.

---

## 10. Success Metrics — LinkedIn Prospecting Agent

### Primary KPIs (North Star: Pipeline Generated)

| Metric | Target (Month 1) | Target (Month 3) | Notes |
|---|---|---|---|
| **Messages sent/day** | 10 | 20–25 | Conservative start to protect account |
| **Connection request acceptance rate** | >20% | >30% | Benchmark: 20–30% is strong |
| **Reply rate** | >5% | >10% | Industry average: 2–5%; AI personalization target: 8–12% |
| **Hot leads flagged/month** | 5 | 15 | Prospect with positive intent signal |
| **Discovery calls booked/month** | 2 | 6 | Conversion from hot lead to call |
| **Pipeline value generated ($)** | $20K | $60K | Based on avg deal size |

### Secondary KPIs (Quality & Safety)

| Metric | Target | Notes |
|---|---|---|
| **LinkedIn account health** | No warnings/restrictions | Account safety is paramount |
| **Unsubscribe / "stop messaging me" rate** | <2% | Indicates ICP quality and message relevance |
| **Duplicate message incidents** | 0 | System should never re-contact same person |
| **Message personalization score** (internal QA) | >8/10 | Random sample review by Cesar |
| **ICP match accuracy** | >80% | % of contacted prospects who actually match ICP |
| **Response classification accuracy** | >90% | Hot/cold/neutral classification |

### Funnel Metrics (Full Sales Funnel Attribution)

```
LinkedIn Scanned Profiles
        ↓ ICP Filter
Qualified Prospects
        ↓ Message Sent
Replies Received
        ↓ Interested Flag
Hot Leads
        ↓ Discovery Call Booked
Calls Held
        ↓ Proposal Sent (by Closer agent)
Proposals Sent
        ↓ Accepted
Clients Won
```

**Target funnel conversion (Month 3):**
- Scanned → Qualified: 15%
- Qualified → Message Sent: 100% (of daily quota)
- Message Sent → Reply: 10%
- Reply → Hot Lead: 40%
- Hot Lead → Call Booked: 60%
- Call → Proposal: 70%
- Proposal → Won: 30%

**Net result:** ~1,000 scanned → 150 qualified → 150 messaged → 15 replies → 6 hot leads → 3.6 calls → 2.5 proposals → **~0.75 clients/month per 1,000 scans** at modest volumes.

At 20 messages/day × 22 working days = 440 messages/month → **~1–2 new clients/month** from LinkedIn alone.

### Leading Indicators (Weekly Review)
- Messages sent (actual vs target)
- Reply rate trend (improving or declining)
- ICP score distribution (are we targeting the right people?)
- Response sentiment trend (positive/negative ratio)

### Lagging Indicators (Monthly Review)
- Clients acquired via LinkedIn channel
- Revenue attributed to LinkedIn prospecting
- CAC (Customer Acquisition Cost) via this channel
- Time from first message to signed contract

---

## Appendix A: Recommended Tech Stack (Initial Thinking)

| Layer | Option A | Option B | Notes |
|---|---|---|---|
| **LinkedIn automation** | Playwright + stealth plugins | LinkedIn Sales Navigator API | Start with Playwright; migrate to API if partner access available |
| **AI/LLM** | OpenAI GPT-4o | Anthropic Claude | Claude strong for long-form; GPT-4o for speed |
| **Orchestration** | n8n (self-hosted) | Custom Python service | n8n for rapid MVP; custom for production control |
| **Database** | Supabase (PostgreSQL) | Airtable | Supabase preferred for relational data + real-time |
| **CRM** | HubSpot Free → Pipedrive | Custom in Supabase | Keep simple at MVP stage |
| **Queue** | Redis + BullMQ | AWS SQS | Redis for self-hosted simplicity |
| **Notifications** | Telegram Bot API | Slack | Cesar uses Telegram; native integration |
| **Document generation** | Puppeteer (HTML→PDF) | Docmosis | Custom templates preferred |
| **Hosting** | Railway / Render | AWS | Railway for simplicity at MVP |

---

## Appendix B: Agent Development Roadmap

```
Phase 1 (Month 1–2): Foundation
  └── LinkedIn Prospecting Agent (Prospector) — MVP
  └── Orchestrator shell (Command) — basic event routing
  └── Telegram notification layer
  └── Prospect database (Supabase)

Phase 2 (Month 3–4): Sales Loop
  └── Content Pipeline Agent (Publisher) — complete existing build
  └── Proposal Generation Agent (Closer)
  └── CRM integration layer

Phase 3 (Month 5–6): Delivery Loop
  └── Project Management Agent (Conductor)
  └── Invoice & Billing Agent (Treasurer)
  └── PM tool integrations (Linear/Notion)

Phase 4 (Month 7–8): Retention Loop
  └── Customer Success Agent (Nurturer)
  └── Full pipeline analytics dashboard
  └── Agent performance feedback loops

Phase 5 (Month 9+): Productization
  └── White-label packaging for other agencies
  └── Multi-tenant architecture
  └── SaaS pricing model
```

---

## Appendix C: Open Questions for PRD Phase

1. **LinkedIn access method:** Does Cesar have Sales Navigator? If not, is he willing to invest (~$80–100/month)? This significantly changes the automation approach and safety profile.

2. **Approval workflow:** Does Cesar want to review + approve every message before send (MVP), or is full auto-send from day 1 the goal? Recommendation: review-first for 30 days.

3. **Offer definition:** What is the specific offer the Prospecting Agent will lead with? (e.g., "free AI audit," "discovery call," "pilot project offer") — this is the most critical message variable.

4. **Geographic focus:** LATAM-first or USA-first? Language of outreach (PT-BR, ES, EN)?

5. **Team size:** Is Cesar operating fully solo right now, or are there contractors who might use the OS?

6. **Existing tools:** What's the current tool stack? (CRM, PM tool, accounting) — integration targets need to be confirmed.

7. **Data storage jurisdiction:** Where should prospect data be stored? (Brazil → LGPD implications)

8. **Productization intent:** Is the end goal to use this internally only, or to package and sell it to other agencies? This affects architecture decisions significantly.

---

*End of Analyst Brainstorming Output — Ready for PRD handoff.*
*Prepared by: @analyst (Atlas) | Eworks OS Project*
