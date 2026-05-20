     1|# Eworks OS — System Design
     2|
     3|**Version:** 1.0  
     4|**Author:** Aria (Architect Agent)  
     5|**Date:** 2026-05-19  
     6|**Status:** Approved for MVP
     7|
     8|---
     9|
    10|## 1. High-Level Architecture
    11|
    12|```
    13|┌─────────────────────────────────────────────────────────────────────┐
    14|│                          EWORKS OS                                  │
    15|│                                                                     │
    16|│  ┌──────────────┐     ┌─────────────────────────────────────────┐  │
    17|│  │   CLI (Typer)│────▶│            Dispatcher                   │  │
    18|│  └──────────────┘     │   (APScheduler + Task Queue Poller)     │  │
    19|│                        └────────────┬──────────────────────────┘  │
    20|│  ┌──────────────┐                   │ dispatches Task rows         │
    21|│  │  Config      │                   ▼                              │
    22|│  │  YAML + .env │     ┌─────────────────────────────────────────┐  │
    23|│  └──────────────┘     │           Agent Pool                    │  │
    24|│                        │  ┌─────────────┐  ┌─────────────────┐  │  │
    25|│                        │  │  LinkedIn   │  │    LinkedIn     │  │  │
    26|│                        │  │  Searcher   │  │   Messenger     │  │  │
    27|│                        │  └──────┬──────┘  └───────┬─────────┘  │  │
    28|│                        │         │                  │            │  │
    29|│                        │  ┌──────▼──────┐  ┌───────▼─────────┐  │  │
    30|│                        │  │  Browser    │  │   Claude API    │  │  │
    31|│                        │  │  Session    │  │  (Anthropic)    │  │  │
    32|│                        │  │ (Playwright)│  └─────────────────┘  │  │
    33|│                        │  └─────────────┘                       │  │
    34|│                        └─────────────────────────────────────────┘  │
    35|│                                   │                                 │
    36|│                        ┌──────────▼──────────┐                     │
    37|│                        │    SQLite Database  │                     │
    38|│                        │  task_queue         │                     │
    39|│                        │  prospects          │                     │
    40|│                        │  campaigns          │                     │
    41|│                        │  messages           │                     │
    42|│                        │  agent_runs         │                     │
    43|│                        └─────────────────────┘                     │
    44|│                                   │                                 │
    45|│                        ┌──────────▼──────────┐                     │
    46|│                        │  Telegram Notifier  │                     │
    47|│                        │  (run summaries,    │                     │
    48|│                        │   error alerts)     │                     │
    49|│                        └─────────────────────┘                     │
    50|└─────────────────────────────────────────────────────────────────────┘
    51|```
    52|
    53|---
    54|
    55|## 2. Agent Execution Model
    56|
    57|### 2.1 Agent Taxonomy (MVP)
    58|
    59|| Agent | Class | Trigger | Frequency |
    60||-------|-------|---------|-----------|
    61|| LinkedInSearchAgent | `agents/linkedin/searcher.py` | Scheduled | Daily or on-demand |
    62|| LinkedInMessengerAgent | `agents/linkedin/messenger.py` | Scheduled | Daily (rate-limited) |
    63|| LinkedInMonitorAgent | `agents/linkedin/monitor.py` | Scheduled | Every 4 hours |
    64|| TelegramNotifyAgent | `agents/notifications/telegram.py` | Event-driven | On run complete/error |
    65|
    66|### 2.2 Task Lifecycle
    67|
    68|```
    69|CLI / Scheduler
    70|      │
    71|      │  create_task(type, payload, campaign_id)
    72|      ▼
    73|┌─────────────────────────────────────────┐
    74|│          task_queue table               │
    75|│  status: pending                        │
    76|└─────────────┬───────────────────────────┘
    77|              │
    78|              │  Dispatcher polls every 30s
    79|              ▼
    80|┌─────────────────────────────────────────┐
    81|│  status: running                        │
    82|│  started_at = NOW()                     │
    83|│  worker_id = "main"                     │
    84|└─────────────┬───────────────────────────┘
    85|              │
    86|              │  Agent.run(task) → Result
    87|              ▼
    88|        ┌─────┴─────┐
    89|        │           │
    90|     success      failure
    91|        │           │
    92|        ▼           ▼
    93|   status:done  status:failed
    94|   result_json  error_msg
    95|   finished_at  retry_count++
    96|                (if retry_count < 3: re-enqueue)
    97|```
    98|
    99|### 2.3 BaseAgent Interface
   100|
   101|```python
   102|from abc import ABC, abstractmethod
   103|from dataclasses import dataclass
   104|from typing import Any
   105|
   106|@dataclass
   107|class Task:
   108|    id: int
   109|    type: str
   110|    payload: dict[str, Any]
   111|    campaign_id: int | None
   112|    retry_count: int
   113|
   114|@dataclass
   115|class Result:
   116|    success: bool
   117|    data: dict[str, Any]
   118|    error: str | None = None
   119|    notify: bool = True
   120|
   121|class BaseAgent(ABC):
   122|    def __init__(self, settings: Settings, db: Database):
   123|        self.settings = settings
   124|        self.db = db
   125|        self.log = structlog.get_logger(agent=self.__class__.__name__)
   126|
   127|    @abstractmethod
   128|    async def run(self, task: Task) -> Result:
   129|        ...
   130|```
   131|
   132|### 2.4 Dispatcher Loop
   133|
   134|```python
   135|async def dispatcher_loop(interval_seconds: int = 30):
   136|    while True:
   137|        task = db.claim_next_task()      # SELECT ... FOR UPDATE equivalent (SQLite: BEGIN IMMEDIATE)
   138|        if task:
   139|            agent = AGENT_REGISTRY[task.type](settings, db)
   140|            try:
   141|                result = await agent.run(task)
   142|                db.complete_task(task.id, result)
   143|                if result.notify:
   144|                    await notify_telegram(result)
   145|            except Exception as e:
   146|                db.fail_task(task.id, str(e), retry=task.retry_count < 3)
   147|        await asyncio.sleep(interval_seconds)
   148|```
   149|
   150|---
   151|
   152|## 3. LinkedIn Automation Approach
   153|
   154|### 3.1 Why Browser Automation
   155|
   156|LinkedIn's official API gates nearly all useful functionality behind partner agreements:
   157|- People Search API: Restricted (requires LinkedIn partner approval)
   158|- Messaging API: Only available to approved ISVs
   159|- Profile Viewer: Restricted
   160|
   161|Playwright browser automation mimics a real user session and is the only viable approach for an MVP.
   162|
   163|### 3.2 Session Architecture
   164|
   165|```
   166|~/.eworks/browser/
   167|└── linkedin_session/       ← Playwright persistent context
   168|    ├── Default/
   169|    │   ├── Cookies          ← LinkedIn session cookies
   170|    │   ├── Local Storage    ← Auth tokens
   171|    │   └── ...
   172|    └── ...
   173|```
   174|
   175|- **One persistent browser context** per LinkedIn account
   176|- Context is stored on disk between runs (avoids re-login every session)
   177|- Login is performed once manually via `eos auth linkedin` (interactive)
   178|- Subsequent runs reuse the stored session
   179|
   180|### 3.3 Anti-Detection Strategy
   181|
   182|LinkedIn actively detects and bans automation. Mitigations:
   183|
   184|#### Fingerprint Randomisation
   185|```python
   186|# stealth.py
   187|VIEWPORT_SIZES = [(1366, 768), (1440, 900), (1920, 1080), (1280, 800)]
   188|USER_AGENTS = [...]  # Pool of real Chrome UA strings, rotated per session
   189|
   190|async def apply_stealth(page: Page):
   191|    await page.set_viewport_size(random.choice(VIEWPORT_SIZES))
   192|    # Playwright by default uses a fixed UA — override it
   193|```
   194|
   195|#### Human-Like Timing
   196|```python
   197|# All actions use randomised delays
   198|async def human_delay(min_ms=800, max_ms=2500):
   199|    await asyncio.sleep(random.uniform(min_ms, max_ms) / 1000)
   200|
   201|async def human_type(page, selector, text):
   202|    await page.click(selector)
   203|    for char in text:
   204|        await page.keyboard.type(char)
   205|        await asyncio.sleep(random.uniform(0.05, 0.15))
   206|```
   207|
   208|#### Daily Rate Limits (Hardcoded Ceiling)
   209|| Action | Daily Limit | Notes |
   210||--------|-------------|-------|
   211|| Profile views | 80 | LinkedIn soft-limits at ~100 |
   212|| Connection requests | 20 | LinkedIn flags >30/day aggressively |
   213|| Messages (connections) | 30 | To existing connections only |
   214|| Search pages visited | 15 | Spread across the day |
   215|
   216|#### Session Hygiene
   217|- **Run windows:** 9:00–11:30 AM and 2:00–4:30 PM (local time) — mirrors human patterns
   218|- **No weekends** by default (configurable)
   219|- **Randomised start time** within window: ±15 minutes jitter
   220|- **Headless: false in dev, true in prod** (headless browsers are easier to detect on some bot systems; we use `channel="chrome"` to leverage real Chrome)
   221|- **IP consistency:** Run from a fixed residential/VPS IP — avoid VPNs that rotate IPs
   222|
   223|#### Detection Recovery
   224|- If LinkedIn shows CAPTCHA or verification page: agent stops, sends Telegram alert, marks session as `requires_verification`
   225|- Re-auth flow: `eos auth linkedin --reauth` opens browser for manual intervention
   226|
   227|### 3.4 LinkedIn Search Flow
   228|
   229|```
   230|LinkedInSearchAgent.run(task)
   231|│
   232|├── 1. Load persistent browser context
   233|├── 2. Navigate to LinkedIn People Search
   234|│        URL: https://www.linkedin.com/search/results/people/
   235|│        Params: keywords, location, industry, etc.
   236|│
   237|├── 3. For each result page (max: settings.max_pages):
   238|│        ├── Extract profile URLs from DOM
   239|│        ├── human_delay()
   240|│        └── paginate → next
   241|│
   242|├── 4. For each profile URL:
   243|│        ├── Navigate to profile
   244|│        ├── Extract: name, headline, company, location, about, experience
   245|│        ├── human_delay()
   246|│        └── Upsert into `prospects` table
   247|│
   248|└── 5. Enqueue MessengerTasks for qualified prospects
   249|```
   250|
   251|### 3.5 LinkedIn Messaging Flow
   252|
   253|```
   254|LinkedInMessengerAgent.run(task)
   255|│
   256|├── 1. Load prospect from DB
   257|├── 2. Load campaign persona + template from DB
   258|├── 3. Call Claude API → generate personalised message
   259|│        Input: prospect profile JSON + persona + template
   260|│        Output: message text (≤300 chars for connection req note)
   261|│
   262|├── 4. Navigate to prospect's LinkedIn profile
   263|├── 5. Decision: connected vs not-connected
   264|│        ├── Not connected: click Connect → Add Note → paste message
   265|│        └── Connected: click Message → paste message
   266|│
   267|├── 6. human_delay() between 1500–4000ms before send
   268|├── 7. Click Send
   269|├── 8. Record in `messages` table
   270|└── 9. Update prospect status
   271|```
   272|
   273|---
   274|
   275|## 4. Data Flow Diagrams
   276|
   277|### 4.1 New Campaign Flow
   278|
   279|```
   280|User → CLI: eworks campaign create --name "SaaS CTOs Q3"
   281|             --search-query "CTO software startup"
   282|             --persona "cesar_intro"
   283|             --daily-limit 15
   284|
   285|CLI → DB: INSERT INTO campaigns (...)
   286|CLI → DB: INSERT INTO task_queue (type='search', campaign_id=X, payload={...})
   287|
   288|APScheduler (9:15 AM) → Dispatcher → LinkedInSearchAgent
   289|  → Browser: search LinkedIn
   290|  → DB: INSERT INTO prospects (...)
   291|  → DB: INSERT INTO task_queue (type='message', prospect_id=Y, campaign_id=X)
   292|
   293|APScheduler (2:05 PM) → Dispatcher → LinkedInMessengerAgent
   294|  → DB: SELECT prospect + campaign
   295|  → Anthropic API: generate message
   296|  → Browser: send LinkedIn message
   297|  → DB: INSERT INTO messages (...)
   298|  → DB: UPDATE prospects SET status='messaged'
   299|
   300|Event → TelegramNotifyAgent
   301|  → Telegram API: "✅ Campaign SaaS CTOs Q3: 12 prospects found, 8 messages sent"
   302|```
   303|
   304|### 4.2 Monitor Flow (Reply Detection)
   305|
   306|```
   307|APScheduler (every 4h) → LinkedInMonitorAgent
   308|  → Browser: navigate to LinkedIn Messaging inbox
   309|  → Extract: all conversation threads with new messages
   310|  → For each thread:
   311|      → DB: SELECT message WHERE linkedin_thread_id = X
   312|      → If reply found: UPDATE messages SET replied_at = NOW(), reply_text = ...
   313|      → UPDATE prospects SET status = 'replied'
   314|      → Enqueue TelegramAlert: "💬 Reply from [Name] at [Company]"
   315|```
   316|
   317|---
   318|
   319|## 5. Component Descriptions
   320|
   321|### 5.1 BrowserSession (`browser/session.py`)
   322|
   323|Manages the Playwright persistent context lifecycle.
   324|
   325|**Responsibilities:**
   326|- Create/load persistent context from `~/.eworks/browser/{account_slug}/`
   327|- Apply stealth configuration (UA, viewport, locale)
   328|- Provide `async with BrowserSession() as session` context manager
   329|- Handle CDP (Chrome DevTools Protocol) session for advanced stealth
   330|- Detect and raise `LinkedInAuthRequired` if session is invalid
   331|
   332|**Key methods:**
   333|- `async def get_page() -> Page` — returns a page within the persistent context
   334|- `async def close()` — gracefully closes without destroying the profile
   335|
   336|### 5.2 LinkedInActions (`browser/linkedin.py`)
   337|
   338|Pure page-interaction functions. No business logic.
   339|
   340|**Key functions:**
   341|- `search_people(page, query, filters) -> list[str]` — returns profile URLs
   342|- `extract_profile(page, url) -> ProspectProfile` — scrapes profile data
   343|- `send_connection_request(page, url, note) -> bool`
   344|- `send_message(page, url, text) -> bool`
   345|- `get_inbox_threads(page) -> list[Thread]`
   346|
   347|### 5.3 AI Client (`ai/client.py`)
   348|
   349|Thin wrapper around Anthropic SDK.
   350|
   351|**Key methods:**
   352|- `async def generate_message(prospect: ProspectProfile, campaign: Campaign) -> str`
   353|  - Uses claude-opus-4-5
   354|  - System prompt: persona definition from campaign
   355|  - User prompt: structured prospect data
   356|  - Returns: message text, validated for length
   357|- `async def classify_reply(thread: Thread) -> ReplyClassification`
   358|  - Uses claude-haiku-3-5 (cheaper)
   359|  - Returns: `{intent: "interested|not_interested|question|other", sentiment: float}`
   360|
   361|### 5.4 Task Queue (`db/queue.py`)
   362|
   363|SQLite-backed FIFO with priority support.
   364|
   365|**Key operations:**
   366|- `create_task(type, payload, campaign_id, priority=5) -> int`
   367|- `claim_next_task() -> Task | None` — atomic SELECT + UPDATE using SQLite IMMEDIATE transaction
   368|- `complete_task(id, result_json)`
   369|- `fail_task(id, error, retry: bool)`
   370|- `list_tasks(status, limit) -> list[Task]`
   371|
   372|### 5.5 Scheduler (`scheduler/jobs.py`)
   373|
   374|APScheduler configuration. Jobs defined here, persisted to SQLite.
   375|
   376|**Default jobs:**
   377|```python
   378|scheduler.add_job(
   379|    run_search_tasks,
   380|    CronTrigger(hour=9, minute='0-30', jitter=900),  # 9:00–9:15 AM with jitter
   381|    id='morning_search'
   382|)
   383|scheduler.add_job(
   384|    run_message_tasks,
   385|    CronTrigger(hour=14, minute='0-30', jitter=900),  # 2:00–2:15 PM
   386|    id='afternoon_messages'
   387|)
   388|scheduler.add_job(
   389|    run_monitor_tasks,
   390|    IntervalTrigger(hours=4, jitter=600),
   391|    id='inbox_monitor'
   392|)
   393|```
   394|
   395|### 5.6 Telegram Notifier (`agents/notifications/telegram.py`)
   396|
   397|Sends formatted messages to Cesar's Telegram chat.
   398|
   399|**Message types:**
   400|- `RunSummary`: after each agent run
   401|- `ErrorAlert`: on agent failure (includes traceback snippet)
   402|- `ReplyAlert`: when a prospect replies
   403|- `DailyDigest`: end-of-day summary (scheduled 6 PM)
   404|
   405|---
   406|
   407|## 6. Deployment Architecture
   408|
   409|### 6.1 MVP: Single VPS or Mac Mini
   410|
   411|```
   412|Ubuntu 22.04 VPS (2 vCPU, 4 GB RAM)  OR  Cesar's Mac Mini
   413|
   414|systemd service: eworks-dispatcher.service
   415|  → Runs: python -m eworks_os.cli daemon
   416|  → Starts the dispatcher loop + APScheduler
   417|  → Restarts on failure (Restart=always)
   418|
   419|Directory layout:
   420|/opt/eworks-os/
   421|├── .env                    ← secrets (chmod 600)
   422|├── config/settings.yaml    ← operational config
   423|├── eworks.db               ← SQLite database
   424|└── venv/                   ← Python virtualenv
   425|~/.eworks/
   426|└── browser/
   427|    └── linkedin_default/   ← Playwright profile
   428|```
   429|
   430|### 6.2 systemd Unit File
   431|
   432|```ini
   433|[Unit]
   434|Description=Eworks OS Dispatcher
   435|After=network.target
   436|
   437|[Service]
   438|Type=simple
   439|User=eworks
   440|WorkingDirectory=/opt/eworks-os
   441|ExecStart=/opt/eworks-os/venv/bin/python -m eworks_os.cli daemon
   442|Restart=always
   443|RestartSec=10
   444|EnvironmentFile=/opt/eworks-os/.env
   445|StandardOutput=journal
   446|StandardError=journal
   447|
   448|[Install]
   449|WantedBy=multi-user.target
   450|```
   451|
   452|### 6.3 Resource Requirements
   453|
   454|| Resource | Requirement | Notes |
   455||----------|------------|-------|
   456|| RAM | 2 GB min, 4 GB recommended | Playwright Chromium ~1 GB peak |
   457|| CPU | 1–2 vCPU | Not CPU-bound |
   458|| Disk | 10 GB | Browser profile + DB |
   459|| Network | Residential or static VPS IP | Avoid Tor/VPN rotation |
   460|| OS | Ubuntu 22.04 LTS or macOS 13+ | |
   461|
   462|### 6.4 Scale-Up Path
   463|
   464|When > 3 LinkedIn accounts or > 500 prospects/day:
   465|1. Swap SQLite → PostgreSQL (connection string change + Alembic migration)
   466|2. Add Redis + python-rq (swap `db/queue.py` implementation)
   467|3. Separate worker processes per LinkedIn account (one Playwright context each)
   468|4. Deploy on Kubernetes or Docker Compose with one container per account
   469|