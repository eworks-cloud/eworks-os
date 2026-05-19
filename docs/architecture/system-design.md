# Eworks OS — System Design

**Version:** 1.0  
**Author:** Aria (Architect Agent)  
**Date:** 2026-05-19  
**Status:** Approved for MVP

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          EWORKS OS                                  │
│                                                                     │
│  ┌──────────────┐     ┌─────────────────────────────────────────┐  │
│  │   CLI (Typer)│────▶│            Dispatcher                   │  │
│  └──────────────┘     │   (APScheduler + Task Queue Poller)     │  │
│                        └────────────┬──────────────────────────┘  │
│  ┌──────────────┐                   │ dispatches Task rows         │
│  │  Config      │                   ▼                              │
│  │  YAML + .env │     ┌─────────────────────────────────────────┐  │
│  └──────────────┘     │           Agent Pool                    │  │
│                        │  ┌─────────────┐  ┌─────────────────┐  │  │
│                        │  │  LinkedIn   │  │    LinkedIn     │  │  │
│                        │  │  Searcher   │  │   Messenger     │  │  │
│                        │  └──────┬──────┘  └───────┬─────────┘  │  │
│                        │         │                  │            │  │
│                        │  ┌──────▼──────┐  ┌───────▼─────────┐  │  │
│                        │  │  Browser    │  │   Claude API    │  │  │
│                        │  │  Session    │  │  (Anthropic)    │  │  │
│                        │  │ (Playwright)│  └─────────────────┘  │  │
│                        │  └─────────────┘                       │  │
│                        └─────────────────────────────────────────┘  │
│                                   │                                 │
│                        ┌──────────▼──────────┐                     │
│                        │    SQLite Database  │                     │
│                        │  task_queue         │                     │
│                        │  prospects          │                     │
│                        │  campaigns          │                     │
│                        │  messages           │                     │
│                        │  agent_runs         │                     │
│                        └─────────────────────┘                     │
│                                   │                                 │
│                        ┌──────────▼──────────┐                     │
│                        │  Telegram Notifier  │                     │
│                        │  (run summaries,    │                     │
│                        │   error alerts)     │                     │
│                        └─────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent Execution Model

### 2.1 Agent Taxonomy (MVP)

| Agent | Class | Trigger | Frequency |
|-------|-------|---------|-----------|
| LinkedInSearchAgent | `agents/linkedin/searcher.py` | Scheduled | Daily or on-demand |
| LinkedInMessengerAgent | `agents/linkedin/messenger.py` | Scheduled | Daily (rate-limited) |
| LinkedInMonitorAgent | `agents/linkedin/monitor.py` | Scheduled | Every 4 hours |
| TelegramNotifyAgent | `agents/notifications/telegram.py` | Event-driven | On run complete/error |

### 2.2 Task Lifecycle

```
CLI / Scheduler
      │
      │  create_task(type, payload, campaign_id)
      ▼
┌─────────────────────────────────────────┐
│          task_queue table               │
│  status: pending                        │
└─────────────┬───────────────────────────┘
              │
              │  Dispatcher polls every 30s
              ▼
┌─────────────────────────────────────────┐
│  status: running                        │
│  started_at = NOW()                     │
│  worker_id = "main"                     │
└─────────────┬───────────────────────────┘
              │
              │  Agent.run(task) → Result
              ▼
        ┌─────┴─────┐
        │           │
     success      failure
        │           │
        ▼           ▼
   status:done  status:failed
   result_json  error_msg
   finished_at  retry_count++
                (if retry_count < 3: re-enqueue)
```

### 2.3 BaseAgent Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class Task:
    id: int
    type: str
    payload: dict[str, Any]
    campaign_id: int | None
    retry_count: int

@dataclass
class Result:
    success: bool
    data: dict[str, Any]
    error: str | None = None
    notify: bool = True

class BaseAgent(ABC):
    def __init__(self, settings: Settings, db: Database):
        self.settings = settings
        self.db = db
        self.log = structlog.get_logger(agent=self.__class__.__name__)

    @abstractmethod
    async def run(self, task: Task) -> Result:
        ...
```

### 2.4 Dispatcher Loop

```python
async def dispatcher_loop(interval_seconds: int = 30):
    while True:
        task = db.claim_next_task()      # SELECT ... FOR UPDATE equivalent (SQLite: BEGIN IMMEDIATE)
        if task:
            agent = AGENT_REGISTRY[task.type](settings, db)
            try:
                result = await agent.run(task)
                db.complete_task(task.id, result)
                if result.notify:
                    await notify_telegram(result)
            except Exception as e:
                db.fail_task(task.id, str(e), retry=task.retry_count < 3)
        await asyncio.sleep(interval_seconds)
```

---

## 3. LinkedIn Automation Approach

### 3.1 Why Browser Automation

LinkedIn's official API gates nearly all useful functionality behind partner agreements:
- People Search API: Restricted (requires LinkedIn partner approval)
- Messaging API: Only available to approved ISVs
- Profile Viewer: Restricted

Playwright browser automation mimics a real user session and is the only viable approach for an MVP.

### 3.2 Session Architecture

```
~/.eworks/browser/
└── linkedin_session/       ← Playwright persistent context
    ├── Default/
    │   ├── Cookies          ← LinkedIn session cookies
    │   ├── Local Storage    ← Auth tokens
    │   └── ...
    └── ...
```

- **One persistent browser context** per LinkedIn account
- Context is stored on disk between runs (avoids re-login every session)
- Login is performed once manually via `eworks auth linkedin` (interactive)
- Subsequent runs reuse the stored session

### 3.3 Anti-Detection Strategy

LinkedIn actively detects and bans automation. Mitigations:

#### Fingerprint Randomisation
```python
# stealth.py
VIEWPORT_SIZES = [(1366, 768), (1440, 900), (1920, 1080), (1280, 800)]
USER_AGENTS = [...]  # Pool of real Chrome UA strings, rotated per session

async def apply_stealth(page: Page):
    await page.set_viewport_size(random.choice(VIEWPORT_SIZES))
    # Playwright by default uses a fixed UA — override it
```

#### Human-Like Timing
```python
# All actions use randomised delays
async def human_delay(min_ms=800, max_ms=2500):
    await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)

async def human_type(page, selector, text):
    await page.click(selector)
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.15))
```

#### Daily Rate Limits (Hardcoded Ceiling)
| Action | Daily Limit | Notes |
|--------|-------------|-------|
| Profile views | 80 | LinkedIn soft-limits at ~100 |
| Connection requests | 20 | LinkedIn flags >30/day aggressively |
| Messages (connections) | 30 | To existing connections only |
| Search pages visited | 15 | Spread across the day |

#### Session Hygiene
- **Run windows:** 9:00–11:30 AM and 2:00–4:30 PM (local time) — mirrors human patterns
- **No weekends** by default (configurable)
- **Randomised start time** within window: ±15 minutes jitter
- **Headless: false in dev, true in prod** (headless browsers are easier to detect on some bot systems; we use `channel="chrome"` to leverage real Chrome)
- **IP consistency:** Run from a fixed residential/VPS IP — avoid VPNs that rotate IPs

#### Detection Recovery
- If LinkedIn shows CAPTCHA or verification page: agent stops, sends Telegram alert, marks session as `requires_verification`
- Re-auth flow: `eworks auth linkedin --reauth` opens browser for manual intervention

### 3.4 LinkedIn Search Flow

```
LinkedInSearchAgent.run(task)
│
├── 1. Load persistent browser context
├── 2. Navigate to LinkedIn People Search
│        URL: https://www.linkedin.com/search/results/people/
│        Params: keywords, location, industry, etc.
│
├── 3. For each result page (max: settings.max_pages):
│        ├── Extract profile URLs from DOM
│        ├── human_delay()
│        └── paginate → next
│
├── 4. For each profile URL:
│        ├── Navigate to profile
│        ├── Extract: name, headline, company, location, about, experience
│        ├── human_delay()
│        └── Upsert into `prospects` table
│
└── 5. Enqueue MessengerTasks for qualified prospects
```

### 3.5 LinkedIn Messaging Flow

```
LinkedInMessengerAgent.run(task)
│
├── 1. Load prospect from DB
├── 2. Load campaign persona + template from DB
├── 3. Call Claude API → generate personalised message
│        Input: prospect profile JSON + persona + template
│        Output: message text (≤300 chars for connection req note)
│
├── 4. Navigate to prospect's LinkedIn profile
├── 5. Decision: connected vs not-connected
│        ├── Not connected: click Connect → Add Note → paste message
│        └── Connected: click Message → paste message
│
├── 6. human_delay() between 1500–4000ms before send
├── 7. Click Send
├── 8. Record in `messages` table
└── 9. Update prospect status
```

---

## 4. Data Flow Diagrams

### 4.1 New Campaign Flow

```
User → CLI: eworks campaign create --name "SaaS CTOs Q3"
             --search-query "CTO software startup"
             --persona "cesar_intro"
             --daily-limit 15

CLI → DB: INSERT INTO campaigns (...)
CLI → DB: INSERT INTO task_queue (type='search', campaign_id=X, payload={...})

APScheduler (9:15 AM) → Dispatcher → LinkedInSearchAgent
  → Browser: search LinkedIn
  → DB: INSERT INTO prospects (...)
  → DB: INSERT INTO task_queue (type='message', prospect_id=Y, campaign_id=X)

APScheduler (2:05 PM) → Dispatcher → LinkedInMessengerAgent
  → DB: SELECT prospect + campaign
  → Anthropic API: generate message
  → Browser: send LinkedIn message
  → DB: INSERT INTO messages (...)
  → DB: UPDATE prospects SET status='messaged'

Event → TelegramNotifyAgent
  → Telegram API: "✅ Campaign SaaS CTOs Q3: 12 prospects found, 8 messages sent"
```

### 4.2 Monitor Flow (Reply Detection)

```
APScheduler (every 4h) → LinkedInMonitorAgent
  → Browser: navigate to LinkedIn Messaging inbox
  → Extract: all conversation threads with new messages
  → For each thread:
      → DB: SELECT message WHERE linkedin_thread_id = X
      → If reply found: UPDATE messages SET replied_at = NOW(), reply_text = ...
      → UPDATE prospects SET status = 'replied'
      → Enqueue TelegramAlert: "💬 Reply from [Name] at [Company]"
```

---

## 5. Component Descriptions

### 5.1 BrowserSession (`browser/session.py`)

Manages the Playwright persistent context lifecycle.

**Responsibilities:**
- Create/load persistent context from `~/.eworks/browser/{account_slug}/`
- Apply stealth configuration (UA, viewport, locale)
- Provide `async with BrowserSession() as session` context manager
- Handle CDP (Chrome DevTools Protocol) session for advanced stealth
- Detect and raise `LinkedInAuthRequired` if session is invalid

**Key methods:**
- `async def get_page() -> Page` — returns a page within the persistent context
- `async def close()` — gracefully closes without destroying the profile

### 5.2 LinkedInActions (`browser/linkedin.py`)

Pure page-interaction functions. No business logic.

**Key functions:**
- `search_people(page, query, filters) -> list[str]` — returns profile URLs
- `extract_profile(page, url) -> ProspectProfile` — scrapes profile data
- `send_connection_request(page, url, note) -> bool`
- `send_message(page, url, text) -> bool`
- `get_inbox_threads(page) -> list[Thread]`

### 5.3 AI Client (`ai/client.py`)

Thin wrapper around Anthropic SDK.

**Key methods:**
- `async def generate_message(prospect: ProspectProfile, campaign: Campaign) -> str`
  - Uses claude-opus-4-5
  - System prompt: persona definition from campaign
  - User prompt: structured prospect data
  - Returns: message text, validated for length
- `async def classify_reply(thread: Thread) -> ReplyClassification`
  - Uses claude-haiku-3-5 (cheaper)
  - Returns: `{intent: "interested|not_interested|question|other", sentiment: float}`

### 5.4 Task Queue (`db/queue.py`)

SQLite-backed FIFO with priority support.

**Key operations:**
- `create_task(type, payload, campaign_id, priority=5) -> int`
- `claim_next_task() -> Task | None` — atomic SELECT + UPDATE using SQLite IMMEDIATE transaction
- `complete_task(id, result_json)`
- `fail_task(id, error, retry: bool)`
- `list_tasks(status, limit) -> list[Task]`

### 5.5 Scheduler (`scheduler/jobs.py`)

APScheduler configuration. Jobs defined here, persisted to SQLite.

**Default jobs:**
```python
scheduler.add_job(
    run_search_tasks,
    CronTrigger(hour=9, minute='0-30', jitter=900),  # 9:00–9:15 AM with jitter
    id='morning_search'
)
scheduler.add_job(
    run_message_tasks,
    CronTrigger(hour=14, minute='0-30', jitter=900),  # 2:00–2:15 PM
    id='afternoon_messages'
)
scheduler.add_job(
    run_monitor_tasks,
    IntervalTrigger(hours=4, jitter=600),
    id='inbox_monitor'
)
```

### 5.6 Telegram Notifier (`agents/notifications/telegram.py`)

Sends formatted messages to Cesar's Telegram chat.

**Message types:**
- `RunSummary`: after each agent run
- `ErrorAlert`: on agent failure (includes traceback snippet)
- `ReplyAlert`: when a prospect replies
- `DailyDigest`: end-of-day summary (scheduled 6 PM)

---

## 6. Deployment Architecture

### 6.1 MVP: Single VPS or Mac Mini

```
Ubuntu 22.04 VPS (2 vCPU, 4 GB RAM)  OR  Cesar's Mac Mini

systemd service: eworks-dispatcher.service
  → Runs: python -m eworks_os.cli daemon
  → Starts the dispatcher loop + APScheduler
  → Restarts on failure (Restart=always)

Directory layout:
/opt/eworks-os/
├── .env                    ← secrets (chmod 600)
├── config/settings.yaml    ← operational config
├── eworks.db               ← SQLite database
└── venv/                   ← Python virtualenv
~/.eworks/
└── browser/
    └── linkedin_default/   ← Playwright profile
```

### 6.2 systemd Unit File

```ini
[Unit]
Description=Eworks OS Dispatcher
After=network.target

[Service]
Type=simple
User=eworks
WorkingDirectory=/opt/eworks-os
ExecStart=/opt/eworks-os/venv/bin/python -m eworks_os.cli daemon
Restart=always
RestartSec=10
EnvironmentFile=/opt/eworks-os/.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 6.3 Resource Requirements

| Resource | Requirement | Notes |
|----------|------------|-------|
| RAM | 2 GB min, 4 GB recommended | Playwright Chromium ~1 GB peak |
| CPU | 1–2 vCPU | Not CPU-bound |
| Disk | 10 GB | Browser profile + DB |
| Network | Residential or static VPS IP | Avoid Tor/VPN rotation |
| OS | Ubuntu 22.04 LTS or macOS 13+ | |

### 6.4 Scale-Up Path

When > 3 LinkedIn accounts or > 500 prospects/day:
1. Swap SQLite → PostgreSQL (connection string change + Alembic migration)
2. Add Redis + python-rq (swap `db/queue.py` implementation)
3. Separate worker processes per LinkedIn account (one Playwright context each)
4. Deploy on Kubernetes or Docker Compose with one container per account
