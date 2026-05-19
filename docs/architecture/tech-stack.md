# Eworks OS — Tech Stack

**Version:** 1.0  
**Author:** Aria (Architect Agent)  
**Date:** 2026-05-19  
**Status:** Approved for MVP

---

## Stack Summary

| Layer | Technology | Version |
|-------|-----------|---------|
| Runtime | Python | 3.12 |
| Agent Framework | Custom task queue | — |
| Browser Automation | Playwright | 1.44+ |
| AI / LLM | Anthropic Claude API | claude-opus-4-5 |
| Database | SQLite (MVP) → PostgreSQL | 3.x / 16.x |
| Task Queue | SQLite-backed queue (custom) | — |
| Scheduler | APScheduler | 3.10+ |
| Notifications | Telegram Bot API | — |
| Config | YAML + python-dotenv | — |
| CLI | Typer | 0.12+ |
| HTTP Client | httpx | 0.27+ |
| Async Runtime | asyncio (stdlib) | — |
| Logging | structlog | 24.x |
| Testing | pytest + pytest-asyncio | — |
| Packaging | uv | 0.2+ |

---

## Rationale — Every Decision

### Python 3.12
**Chosen.** The ecosystem for AI agents, Playwright, and async I/O is best-in-class in Python. 3.12 specifically adds per-interpreter GIL, improved error messages, and performance improvements over 3.11. All target libraries support it.

### Agent Framework: Custom SQLite-backed task queue
**Chosen over LangChain, CrewAI, AutoGen.**

LangChain is rejected because:
- Heavy dependency tree (200+ transitive deps)
- Abstractions fight you when you need precise control over browser sessions
- Prompt management is opaque — bad for compliance/auditability
- Version instability

CrewAI / AutoGen rejected: same class of problem, plus they assume stateless agents; LinkedIn automation requires persistent browser state.

**Our approach:** Each agent is a plain Python class with an `async def run(task: Task) -> Result` interface. Tasks are rows in a SQLite `task_queue` table. A single dispatcher loop polls the queue and dispatches to the correct agent class. Dead simple, fully auditable, zero magic.

### LinkedIn: Playwright Browser Automation
**Chosen over LinkedIn Official API.**

LinkedIn's official API is heavily restricted:
- Partner program required for most endpoints
- No programmatic messaging via API (only via approved ISVs)
- Search/people data locked behind expensive tier
- Approval takes months

Playwright is chosen over Selenium because:
- Built-in async support (async with async_playwright())
- Better stealth characteristics (less fingerprinting than Selenium)
- First-class Chromium/Firefox support
- Context persistence (saves cookies/session between runs)
- Network interception for request inspection

Anti-detection strategy documented in system-design.md.

### AI: Anthropic Claude API (claude-opus-4-5)
**Chosen.** claude-opus-4-5 is the current best-in-class model for nuanced, personalised sales copy. Rationale:
- Superior instruction-following for persona/tone constraints
- Long context window handles full LinkedIn profile + conversation history
- Structured output (JSON mode) reliable for message templates
- Cesar already has API access

For cost optimisation: claude-haiku-3-5 used for classification tasks (is this a real prospect? is this a reply?), claude-opus-4-5 only for message generation.

### Database: SQLite → PostgreSQL
**SQLite for MVP.** Rationale:
- Zero infrastructure — single file, works on a laptop or VPS
- WAL mode enables concurrent reads with one writer (sufficient for our throughput: <100 tasks/day)
- Direct migration path: SQLAlchemy ORM abstracts the dialect
- Full schema defined in data-model.md with PostgreSQL-compatible types

**PostgreSQL migration trigger:** When concurrent agents > 3 or when running on a shared server with multiple users.

Migration path: swap `DATABASE_URL=sqlite:///./eworks.db` → `DATABASE_URL=postgresql://...` in `.env`. SQLAlchemy handles the rest. One migration script via Alembic.

### Task Queue: SQLite-backed (custom, not Redis/RQ)
**Chosen over python-rq.**

python-rq requires Redis. Redis adds infrastructure complexity for MVP. Our task volume is low (dozens of tasks/day, not millions). A `task_queue` table with `status ∈ {pending, running, done, failed}` and a polling loop is sufficient.

When to switch to RQ + Redis: if we need distributed workers (multiple machines) or sub-second latency on task pickup.

### Scheduler: APScheduler
**Chosen over system cron.**

- Cron is fine but couples the schedule to the OS; APScheduler keeps it in-process and configurable via YAML
- Supports interval, cron, and one-shot triggers
- Job state persisted to SQLite (same DB)
- Easier to pause/resume campaigns programmatically

### Notifications: Telegram Bot API
**Chosen.** Already integrated for Cesar. Used for:
- Agent run summaries (N prospects searched, M messages sent)
- Error alerts (browser crashed, login required)
- Daily digest

### Config: YAML + .env
**Chosen.** 
- `.env` for secrets (API keys, credentials) — never committed
- `config/settings.yaml` for operational config (schedules, limits, personas) — committed
- `pydantic-settings` parses both into typed `Settings` objects
- Separation enforces the principle: secrets ≠ config

### CLI: Typer
**Chosen over Click or argparse.**
- Typer wraps Click but adds type hints → automatic help generation
- Supports async commands via `asyncio.run()`
- Clean subcommand structure: `eworks agent run`, `eworks campaign create`, etc.

### HTTP Client: httpx
**Chosen over requests.**
- Native async support (same client for both sync and async)
- HTTP/2 support
- Used for Anthropic API calls and Telegram Bot API

### Logging: structlog
**Chosen over stdlib logging.**
- JSON-structured logs for later ELK/Loki ingestion
- Each agent run tagged with `run_id`, `campaign_id`, `agent_type`
- Console renderer in dev, JSON renderer in prod

---

## Dependency Pinning Strategy

```
uv pip compile requirements.in → requirements.txt   # pinned
uv pip compile requirements-dev.in → requirements-dev.txt
```

All deps pinned to exact versions in `requirements.txt`. `requirements.in` tracks intentional direct deps.

---

## Python Package Layout

```
eworks_os/
├── agents/
│   ├── base.py          # BaseAgent ABC
│   ├── linkedin/
│   │   ├── searcher.py  # LinkedInSearchAgent
│   │   ├── messenger.py # LinkedInMessengerAgent
│   │   └── monitor.py   # LinkedInMonitorAgent
│   └── notifications/
│       └── telegram.py  # TelegramNotifyAgent
├── browser/
│   ├── session.py       # BrowserSession (Playwright wrapper)
│   ├── linkedin.py      # LinkedIn page actions
│   └── stealth.py       # Anti-detection helpers
├── ai/
│   ├── client.py        # Anthropic API wrapper
│   └── prompts/         # Prompt templates (YAML)
├── db/
│   ├── models.py        # SQLAlchemy ORM models
│   ├── migrations/      # Alembic migrations
│   └── queue.py         # Task queue operations
├── scheduler/
│   └── jobs.py          # APScheduler job definitions
├── cli/
│   └── main.py          # Typer CLI entrypoint
├── config/
│   ├── settings.py      # pydantic-settings Settings class
│   └── settings.yaml    # Default config
└── utils/
    ├── retry.py         # Exponential backoff decorator
    └── crypto.py        # Fernet encryption for stored creds
```
