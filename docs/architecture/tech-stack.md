     1|# Eworks OS — Tech Stack
     2|
     3|**Version:** 1.0  
     4|**Author:** Aria (Architect Agent)  
     5|**Date:** 2026-05-19  
     6|**Status:** Approved for MVP
     7|
     8|---
     9|
    10|## Stack Summary
    11|
    12|| Layer | Technology | Version |
    13||-------|-----------|---------|
    14|| Runtime | Python | 3.12 |
    15|| Agent Framework | Custom task queue | — |
    16|| Browser Automation | Playwright | 1.44+ |
    17|| AI / LLM | Anthropic Claude API | claude-opus-4-5 |
    18|| Database | SQLite (MVP) → PostgreSQL | 3.x / 16.x |
    19|| Task Queue | SQLite-backed queue (custom) | — |
    20|| Scheduler | APScheduler | 3.10+ |
    21|| Notifications | Telegram Bot API | — |
    22|| Config | YAML + python-dotenv | — |
    23|| CLI | Typer | 0.12+ |
    24|| HTTP Client | httpx | 0.27+ |
    25|| Async Runtime | asyncio (stdlib) | — |
    26|| Logging | structlog | 24.x |
    27|| Testing | pytest + pytest-asyncio | — |
    28|| Packaging | uv | 0.2+ |
    29|
    30|---
    31|
    32|## Rationale — Every Decision
    33|
    34|### Python 3.12
    35|**Chosen.** The ecosystem for AI agents, Playwright, and async I/O is best-in-class in Python. 3.12 specifically adds per-interpreter GIL, improved error messages, and performance improvements over 3.11. All target libraries support it.
    36|
    37|### Agent Framework: Custom SQLite-backed task queue
    38|**Chosen over LangChain, CrewAI, AutoGen.**
    39|
    40|LangChain is rejected because:
    41|- Heavy dependency tree (200+ transitive deps)
    42|- Abstractions fight you when you need precise control over browser sessions
    43|- Prompt management is opaque — bad for compliance/auditability
    44|- Version instability
    45|
    46|CrewAI / AutoGen rejected: same class of problem, plus they assume stateless agents; LinkedIn automation requires persistent browser state.
    47|
    48|**Our approach:** Each agent is a plain Python class with an `async def run(task: Task) -> Result` interface. Tasks are rows in a SQLite `task_queue` table. A single dispatcher loop polls the queue and dispatches to the correct agent class. Dead simple, fully auditable, zero magic.
    49|
    50|### LinkedIn: Playwright Browser Automation
    51|**Chosen over LinkedIn Official API.**
    52|
    53|LinkedIn's official API is heavily restricted:
    54|- Partner program required for most endpoints
    55|- No programmatic messaging via API (only via approved ISVs)
    56|- Search/people data locked behind expensive tier
    57|- Approval takes months
    58|
    59|Playwright is chosen over Selenium because:
    60|- Built-in async support (async with async_playwright())
    61|- Better stealth characteristics (less fingerprinting than Selenium)
    62|- First-class Chromium/Firefox support
    63|- Context persistence (saves cookies/session between runs)
    64|- Network interception for request inspection
    65|
    66|Anti-detection strategy documented in system-design.md.
    67|
    68|### AI: Anthropic Claude API (claude-opus-4-5)
    69|**Chosen.** claude-opus-4-5 is the current best-in-class model for nuanced, personalised sales copy. Rationale:
    70|- Superior instruction-following for persona/tone constraints
    71|- Long context window handles full LinkedIn profile + conversation history
    72|- Structured output (JSON mode) reliable for message templates
    73|- Cesar already has API access
    74|
    75|For cost optimisation: claude-haiku-3-5 used for classification tasks (is this a real prospect? is this a reply?), claude-opus-4-5 only for message generation.
    76|
    77|### Database: SQLite → PostgreSQL
    78|**SQLite for MVP.** Rationale:
    79|- Zero infrastructure — single file, works on a laptop or VPS
    80|- WAL mode enables concurrent reads with one writer (sufficient for our throughput: <100 tasks/day)
    81|- Direct migration path: SQLAlchemy ORM abstracts the dialect
    82|- Full schema defined in data-model.md with PostgreSQL-compatible types
    83|
    84|**PostgreSQL migration trigger:** When concurrent agents > 3 or when running on a shared server with multiple users.
    85|
    86|Migration path: swap `DATABASE_URL=sqlite:///./eworks.db` → `DATABASE_URL=postgresql://...` in `.env`. SQLAlchemy handles the rest. One migration script via Alembic.
    87|
    88|### Task Queue: SQLite-backed (custom, not Redis/RQ)
    89|**Chosen over python-rq.**
    90|
    91|python-rq requires Redis. Redis adds infrastructure complexity for MVP. Our task volume is low (dozens of tasks/day, not millions). A `task_queue` table with `status ∈ {pending, running, done, failed}` and a polling loop is sufficient.
    92|
    93|When to switch to RQ + Redis: if we need distributed workers (multiple machines) or sub-second latency on task pickup.
    94|
    95|### Scheduler: APScheduler
    96|**Chosen over system cron.**
    97|
    98|- Cron is fine but couples the schedule to the OS; APScheduler keeps it in-process and configurable via YAML
    99|- Supports interval, cron, and one-shot triggers
   100|- Job state persisted to SQLite (same DB)
   101|- Easier to pause/resume campaigns programmatically
   102|
   103|### Notifications: Telegram Bot API
   104|**Chosen.** Already integrated for Cesar. Used for:
   105|- Agent run summaries (N prospects searched, M messages sent)
   106|- Error alerts (browser crashed, login required)
   107|- Daily digest
   108|
   109|### Config: YAML + .env
   110|**Chosen.** 
   111|- `.env` for secrets (API keys, credentials) — never committed
   112|- `config/settings.yaml` for operational config (schedules, limits, personas) — committed
   113|- `pydantic-settings` parses both into typed `Settings` objects
   114|- Separation enforces the principle: secrets ≠ config
   115|
   116|### CLI: Typer
   117|**Chosen over Click or argparse.**
   118|- Typer wraps Click but adds type hints → automatic help generation
   119|- Supports async commands via `asyncio.run()`
   120|- Clean subcommand structure: `eos agent run`, `eos campaign create`, etc.
   121|
   122|### HTTP Client: httpx
   123|**Chosen over requests.**
   124|- Native async support (same client for both sync and async)
   125|- HTTP/2 support
   126|- Used for Anthropic API calls and Telegram Bot API
   127|
   128|### Logging: structlog
   129|**Chosen over stdlib logging.**
   130|- JSON-structured logs for later ELK/Loki ingestion
   131|- Each agent run tagged with `run_id`, `campaign_id`, `agent_type`
   132|- Console renderer in dev, JSON renderer in prod
   133|
   134|---
   135|
   136|## Dependency Pinning Strategy
   137|
   138|```
   139|uv pip compile requirements.in → requirements.txt   # pinned
   140|uv pip compile requirements-dev.in → requirements-dev.txt
   141|```
   142|
   143|All deps pinned to exact versions in `requirements.txt`. `requirements.in` tracks intentional direct deps.
   144|
   145|---
   146|
   147|## Python Package Layout
   148|
   149|```
   150|eworks_os/
   151|├── agents/
   152|│   ├── base.py          # BaseAgent ABC
   153|│   ├── linkedin/
   154|│   │   ├── searcher.py  # LinkedInSearchAgent
   155|│   │   ├── messenger.py # LinkedInMessengerAgent
   156|│   │   └── monitor.py   # LinkedInMonitorAgent
   157|│   └── notifications/
   158|│       └── telegram.py  # TelegramNotifyAgent
   159|├── browser/
   160|│   ├── session.py       # BrowserSession (Playwright wrapper)
   161|│   ├── linkedin.py      # LinkedIn page actions
   162|│   └── stealth.py       # Anti-detection helpers
   163|├── ai/
   164|│   ├── client.py        # Anthropic API wrapper
   165|│   └── prompts/         # Prompt templates (YAML)
   166|├── db/
   167|│   ├── models.py        # SQLAlchemy ORM models
   168|│   ├── migrations/      # Alembic migrations
   169|│   └── queue.py         # Task queue operations
   170|├── scheduler/
   171|│   └── jobs.py          # APScheduler job definitions
   172|├── cli/
   173|│   └── main.py          # Typer CLI entrypoint
   174|├── config/
   175|│   ├── settings.py      # pydantic-settings Settings class
   176|│   └── settings.yaml    # Default config
   177|└── utils/
   178|    ├── retry.py         # Exponential backoff decorator
   179|    └── crypto.py        # Fernet encryption for stored creds
   180|```
   181|