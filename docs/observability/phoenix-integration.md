# Arize Phoenix Integration Guide — Eworks OS Multi-Agent System

**Date:** May 2026  
**Project:** Eworks OS (`eos`) — Multi-Agent Company Operating System  
**Framework:** AIOX-Core (Python 3.12+)  
**Observability Platform:** Arize Phoenix  

---

## 1. Overview

This guide details the integration of **Arize Phoenix** for AI Observability & Evaluation across all **Eworks OS agents**:

1. **Prospector** — LinkedIn prospecting & outreach automation
2. **Publisher** — Content ideation, scripting, video generation
3. **Closer** — Proposal generation from discovery notes
4. **Conductor** — Project tracking & sprint management
5. **Treasurer** — Invoice generation & financial tracking
6. **Nurturer** — Customer success & health scoring
7. **Connector** — Social platform monitoring & engagement

---

## 2. Architecture

### 2.1 Setup Phase (Completed ✓)

- ✓ `arize-phoenix` package installed
- ✓ `.env` file updated with `PHOENIX_API_KEY` and `PHOENIX_BASE_URL`
- ✓ Phoenix initialization added to `eworks/cli/main.py` (runs on `eos` CLI startup)
- ✓ Instrumentation module created: `eworks/core/phoenix_instrumentation.py`

### 2.2 Integration Points (To Be Implemented)

Each agent will be instrumented at three levels:

1. **Agent Execution Level** → Trace the main `run()` / `execute()` method
2. **LLM Call Level** → Trace all interactions with LLM APIs (Claude, Gemini, GROQ)
3. **Tool Call Level** → Trace external tools (web search, file I/O, database queries)
4. **Workflow Step Level** → Trace business logic steps (generate idea → script → video)

---

## 3. Instrumentation by Agent

### 3.1 Prospector Agent

**Location:** `eworks/agents/prospector/`

**Key Files to Modify:**
- `eworks/agents/prospector/orchestrator.py` — Main agent orchestration
- `eworks/agents/prospector/executor.py` — Campaign execution logic
- `eworks/agents/prospector/discovery.py` — Prospect discovery & scoring
- `eworks/agents/prospector/outreach_generator.py` — Message generation (LLM call)

**Integration Points:**

```python
# In orchestrator.py
from eworks.core.phoenix_instrumentation import trace_agent_execution, trace_llm_call

class ProspectorOrchestrator:
    @trace_agent_execution("prospector")
    async def run(self, campaign_id: int, dry_run: bool = False):
        # Existing logic
        pass

# In outreach_generator.py
async def generate_outreach_message(prospect: dict) -> str:
    async with trace_llm_call("claude-3-sonnet", operation="generate_message") as span:
        response = await client.messages.create(...)
        if span:
            span.set_attribute("prospect_id", prospect.get("id"))
            span.set_attribute("tokens_used", response.usage.output_tokens)
        return response.content[0].text
```

**Metrics to Capture:**
- Campaign ID
- Prospect count
- Messages generated
- Outreach success rate
- LLM tokens used
- LinkedIn interaction response time

---

### 3.2 Publisher Agent

**Location:** `eworks/agents/publisher/`

**Key Files to Modify:**
- `eworks/agents/publisher/orchestrator.py` — Content pipeline orchestration
- `eworks/agents/publisher/ideation.py` — Idea generation (LLM call)
- `eworks/agents/publisher/scripting.py` — Script generation (LLM call)
- `eworks/agents/publisher/video_generator.py` — HeyGen video generation (tool call)
- `eworks/agents/publisher/social_orchestrator.py` — Multi-platform posting (tool call)

**Integration Points:**

```python
# In orchestrator.py
from eworks.core.phoenix_instrumentation import (
    trace_agent_execution,
    trace_llm_call,
    trace_tool_call,
    trace_workflow_step,
)

class PublisherOrchestrator:
    @trace_agent_execution("publisher")
    async def run(self, language: str = "en", auto_approve: bool = False):
        with trace_workflow_step("generate_ideas", agent="publisher") as span:
            ideas = await self.ideation.generate_ideas(n=5, language=language)
            if span:
                span.set_attribute("idea_count", len(ideas))
        
        with trace_workflow_step("create_scripts", agent="publisher") as span:
            scripts = await self.scripting.generate_scripts(ideas)
            if span:
                span.set_attribute("script_count", len(scripts))
        
        with trace_tool_call("heygen_video", operation="generate") as span:
            video_path = await self.video_generator.generate_video(scripts[0])
            if span:
                span.set_attribute("video_file", video_path)
        
        with trace_tool_call("social_post", operation="post_to_instagram_youtube") as span:
            result = await self.social.post_to_platforms(video_path, ideas[0])
            if span:
                span.set_attribute("platforms_posted", len(result.get("success", [])))

# In ideation.py
async def generate_ideas(self, n: int = 5, language: str = "en", niche: str = "AI automation"):
    async with trace_llm_call("claude-3-sonnet", operation="ideation") as span:
        response = await self.client.messages.create(...)
        if span:
            span.set_attribute("language", language)
            span.set_attribute("niche", niche)
            span.set_attribute("idea_count", n)
        return parse_ideas(response.content[0].text)
```

**Metrics to Capture:**
- Ideas generated
- Scripts created
- Video generation time
- Platform posting success
- Approval status (approved/rejected)
- Engagement metrics (likes, shares, comments)

---

### 3.3 Closer Agent

**Location:** `eworks/agents/closer/`

**Key Files to Modify:**
- `eworks/agents/closer/orchestrator.py` — Proposal generation orchestration
- `eworks/agents/closer/proposal_generator.py` — Proposal generation (LLM call)
- `eworks/agents/closer/delivery.py` — Telegram delivery (tool call)

**Integration Points:**

```python
# In orchestrator.py
from eworks.core.phoenix_instrumentation import (
    trace_agent_execution,
    trace_llm_call,
    trace_tool_call,
    trace_workflow_step,
)

class CloserOrchestrator:
    @trace_agent_execution("closer")
    async def run_from_notes(self, client_name: str, company: str, notes: str, deliver: bool = True):
        with trace_workflow_step("analyze_discovery_notes", agent="closer") as span:
            analysis = await self.analyze_notes(notes)
            if span:
                span.set_attribute("client_name", client_name)
                span.set_attribute("company", company)
        
        async with trace_llm_call("claude-3-sonnet", operation="proposal_generation") as span:
            proposal = await self.generator.generate_proposal(analysis)
            if span:
                span.set_attribute("proposal_length", len(proposal))
        
        if deliver:
            with trace_tool_call("telegram_delivery", operation="send_proposal") as span:
                result = await self.delivery.deliver_via_telegram(proposal)
                if span:
                    span.set_attribute("delivery_status", result.get("status"))

# In proposal_generator.py
async def generate_proposal(self, analysis: dict) -> str:
    async with trace_llm_call("claude-3-sonnet", operation="proposal_creation") as span:
        response = await self.client.messages.create(...)
        if span:
            span.set_attribute("analysis_keys", list(analysis.keys()))
        return response.content[0].text
```

**Metrics to Capture:**
- Client name
- Company name
- Discovery notes length
- Proposal length & sections
- Generation time
- Delivery status

---

### 3.4 Conductor Agent

**Location:** `eworks/agents/conductor/`

**Key Files to Modify:**
- `eworks/agents/conductor/orchestrator.py` — Daily checks & health monitoring
- `eworks/agents/conductor/tracker.py` — Project tracking (database operations)
- `eworks/agents/conductor/sprint_manager.py` — Sprint & task management

**Integration Points:**

```python
# In orchestrator.py
from eworks.core.phoenix_instrumentation import (
    trace_agent_execution,
    trace_tool_call,
    trace_workflow_step,
)

class ConductorOrchestrator:
    @trace_agent_execution("conductor")
    async def run_daily_check(self):
        with trace_workflow_step("health_check_all_projects", agent="conductor") as span:
            projects = self.db.list_projects(status="active")
            if span:
                span.set_attribute("project_count", len(projects))
            
            results = []
            for project in projects:
                with trace_tool_call("database_query", operation="get_project_health") as tool_span:
                    health = self.tracker.get_project_summary(project["id"])
                    if tool_span:
                        tool_span.set_attribute("project_id", project["id"])
                        tool_span.set_attribute("health_score", health.get("health_score"))
                results.append(health)
            
            return results

# In sprint_manager.py
def update_task_status(self, task_id: int, status: str):
    with trace_tool_call("database_update", operation="task_status_update") as span:
        ok = self.db.update_task(task_id, {"status": status})
        if span:
            span.set_attribute("task_id", task_id)
            span.set_attribute("new_status", status)
            span.set_attribute("success", ok)
        return ok
```

**Metrics to Capture:**
- Number of active projects
- Health scores
- Task status changes
- Sprint velocity
- Burndown rate

---

### 3.5 Treasurer Agent

**Location:** `eworks/agents/treasurer/`

**Key Files to Modify:**
- `eworks/agents/treasurer/orchestrator.py` — Daily financial workflow
- `eworks/agents/treasurer/invoice_generator.py` — Invoice creation
- `eworks/agents/treasurer/payment_tracker.py` — Payment recording

**Integration Points:**

```python
# In orchestrator.py
from eworks.core.phoenix_instrumentation import (
    trace_agent_execution,
    trace_tool_call,
    trace_workflow_step,
)

class TreasurerOrchestrator:
    @trace_agent_execution("treasurer")
    async def run_daily(self):
        with trace_workflow_step("process_invoices", agent="treasurer") as span:
            invoices = self.db.list_invoices(status="sent")
            if span:
                span.set_attribute("invoice_count", len(invoices))
            
            overdue = [inv for inv in invoices if self.is_overdue(inv)]
            if span:
                span.set_attribute("overdue_count", len(overdue))

# In payment_tracker.py
def record_payment(self, invoice_id: int, amount: float, payment_date: str):
    with trace_tool_call("database_write", operation="record_payment") as span:
        payment_id = self.db.insert_payment(...)
        if span:
            span.set_attribute("invoice_id", invoice_id)
            span.set_attribute("amount", amount)
            span.set_attribute("payment_id", payment_id)
        return payment_id
```

**Metrics to Capture:**
- Invoice count
- Overdue invoices
- Payment amounts
- Payment date
- Revenue by period
- Collection rate

---

### 3.6 Nurturer Agent

**Location:** `eworks/agents/nurturer/`

**Key Files to Modify:**
- `eworks/agents/nurturer/orchestrator.py` — Customer success workflow
- `eworks/agents/nurturer/health_scorer.py` — Health scoring (LLM call optional)
- `eworks/agents/nurturer/checkin_system.py` — Check-in generation (LLM call)

**Integration Points:**

```python
# In orchestrator.py
from eworks.core.phoenix_instrumentation import (
    trace_agent_execution,
    trace_llm_call,
    trace_workflow_step,
)

class NurturerOrchestrator:
    @trace_agent_execution("nurturer")
    async def run_daily(self):
        with trace_workflow_step("score_customer_health", agent="nurturer") as span:
            at_risk = self.scorer.get_at_risk_clients()
            if span:
                span.set_attribute("at_risk_count", len(at_risk))
        
        with trace_workflow_step("send_checkins", agent="nurturer") as span:
            for client in at_risk:
                async with trace_llm_call("claude-3-sonnet", operation="checkin_generation") as llm_span:
                    checkin = await self.checkin.generate_checkin(client)
                    if llm_span:
                        llm_span.set_attribute("client_id", client["id"])
                if span:
                    span.set_attribute("checkins_sent", "increment")

# In checkin_system.py
async def generate_checkin(self, client: dict) -> str:
    async with trace_llm_call("claude-3-sonnet", operation="personalized_checkin") as span:
        response = await self.client.messages.create(...)
        if span:
            span.set_attribute("client_id", client["id"])
            span.set_attribute("client_health", client.get("health_score"))
        return response.content[0].text
```

**Metrics to Capture:**
- At-risk client count
- Health scores
- Check-ins sent
- Upsell opportunities detected
- Onboarding progress

---

### 3.7 Connector Agent (NEW)

**Location:** `eworks/agents/connector/`

**Key Files to Modify:**
- `eworks/agents/connector/orchestrator.py` — Multi-platform monitoring
- `eworks/agents/connector/reply_generator.py` — Reply generation (LLM call)
- `eworks/agents/connector/conversation_tracker.py` — Interaction tracking

**Integration Points:**

```python
# In orchestrator.py
from eworks.core.phoenix_instrumentation import (
    trace_agent_execution,
    trace_llm_call,
    trace_tool_call,
    trace_workflow_step,
)

class ConnectorOrchestrator:
    @trace_agent_execution("connector")
    async def run_all(self, since_minutes: int = 60):
        with trace_workflow_step("scan_all_platforms", agent="connector") as span:
            platforms = ["instagram", "linkedin", "x", "youtube"]
            results = {}
            for platform in platforms:
                with trace_tool_call(f"{platform}_listener", operation="fetch_interactions") as tool_span:
                    interactions = await self.listeners[platform].fetch_recent(since_minutes)
                    if tool_span:
                        tool_span.set_attribute("interaction_count", len(interactions))
                results[platform] = interactions
            if span:
                span.set_attribute("total_interactions", sum(len(r) for r in results.values()))

# In reply_generator.py
async def generate_reply(self, interaction: dict) -> str:
    async with trace_llm_call("claude-3-sonnet", operation="reply_generation") as span:
        response = await self.client.messages.create(...)
        if span:
            span.set_attribute("platform", interaction.get("platform"))
            span.set_attribute("sentiment", interaction.get("sentiment"))
            span.set_attribute("is_lead", interaction.get("is_lead"))
        return response.content[0].text
```

**Metrics to Capture:**
- Interactions detected per platform
- Reply generation count
- Sentiment distribution
- Lead detection rate
- Response time

---

## 4. Implementation Roadmap

### Phase 1: Core Instrumentation (Week 1)
- [ ] Prospector agent — instrument `orchestrator.py` & `outreach_generator.py`
- [ ] Publisher agent — instrument `orchestrator.py` & workflow steps
- [ ] Closer agent — instrument proposal generation
- Commit: "Add Phoenix instrumentation to Prospector, Publisher, Closer agents"

### Phase 2: Financial & Project Management (Week 2)
- [ ] Conductor agent — instrument daily checks & project tracking
- [ ] Treasurer agent — instrument invoice & payment workflows
- Commit: "Add Phoenix instrumentation to Conductor, Treasurer agents"

### Phase 3: Customer Success & Engagement (Week 3)
- [ ] Nurturer agent — instrument health scoring & check-ins
- [ ] Connector agent — instrument platform monitoring & replies
- Commit: "Add Phoenix instrumentation to Nurturer, Connector agents"

### Phase 4: Evaluation & Dashboards (Week 4)
- [ ] Create evaluation metrics (proposal quality, engagement rate, health score accuracy)
- [ ] Build Phoenix dashboard queries
- [ ] Document observability best practices
- Commit: "Add Phoenix evaluation metrics and dashboard configs"

---

## 5. Environment Configuration

### .env Setup

```bash
# Arize Phoenix credentials
PHOENIX_API_KEY=your_actual_phoenix_api_key_here
PHOENIX_BASE_URL=https://app.arize.com/api/phoenix/v1
```

### Accessing Phoenix Dashboard

Once an agent runs with tracing enabled:

1. Go to **https://app.arize.com** and log in
2. Select your **Eworks OS** project (or create one)
3. Navigate to **Traces** to see agent execution traces
4. Use **Annotations** to mark spans as "good" or "bad" for model evaluation
5. Query **Analytics** to track metrics over time

---

## 6. Verification & Testing

### Local Testing

```bash
# Set Phoenix API key (test key or real key)
export PHOENIX_API_KEY=your_key

# Run an agent with tracing enabled
eos prospector run --campaign 1

# Check logs for Phoenix initialization message
# Expected: "✓ Phoenix AI Observability initialized for Eworks OS agents."
```

### Production Checks

- [ ] All agents initialize Phoenix on startup (no errors)
- [ ] Agent execution spans appear in Phoenix dashboard within 5 seconds
- [ ] LLM call spans capture token counts
- [ ] Tool call spans capture result counts
- [ ] Workflow step spans track business metrics

---

## 7. Best Practices

### Span Naming Convention

```
agent_execution_<agent_name>_<method_name>
llm_<model_name>_<operation>
tool_<tool_name>_<operation>
workflow_<step_name>
```

### Attribute Naming Convention

```
snake_case for all attribute keys
Primitives (str, int, float, bool) for values
Avoid PII: don't log email, phone, SSN, etc.
Limit string values to 1000 chars max
```

### Error Handling

- Always catch exceptions in instrumentation code
- Log errors to logger, never crash the agent
- Attach error type and message to spans
- Continue agent execution even if tracing fails

---

## 8. References

- **Arize Phoenix Docs:** https://docs.arize.com/phoenix
- **AIOX-Core Framework:** ~/projects/aiox-core
- **Eworks OS Project:** ~/projects/eworks-os
- **Skills:** See `aiox-framework` skill in Claude Code

---

## 9. FAQ

**Q: What if Phoenix API key is missing?**  
A: Tracing is disabled gracefully; agent runs without observability.

**Q: How do I test tracing locally?**  
A: Set `PHOENIX_API_KEY` to a test key and run an agent. Check Phoenix UI for traces.

**Q: Can I trace database queries?**  
A: Yes, wrap `db.execute()` calls with `trace_tool_call("database", "query")`.

**Q: How do I measure agent quality?**  
A: Use Phoenix **Annotations** to mark traces as "good" / "bad" after review.

---

**Document Version:** 1.0  
**Last Updated:** May 21, 2026  
**Status:** Ready for Implementation  
