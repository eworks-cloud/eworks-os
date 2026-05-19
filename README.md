# Eworks OS

**Multi-Agent Company Operating System** — AI-powered LinkedIn outreach automation built on Python 3.12.

Eworks OS is a modular agent framework that automates B2B prospecting on LinkedIn: it discovers connections, scores them against your Ideal Customer Profile (ICP), generates hyper-personalized outreach messages with Claude AI, sends connection requests with human-like timing, and reports results to Telegram — all on autopilot.

---

## Architecture Overview

```
eworks-os/
├── eworks/
│   ├── agents/
│   │   ├── base.py                 # BaseAgent abstract class
│   │   └── prospector/
│   │       ├── auth.py             # LinkedIn Playwright session (stealth)
│   │       ├── discovery.py        # Connection scraper + ICP scorer
│   │       ├── generator.py        # Claude AI message generator
│   │       ├── executor.py         # Send messages + rate limiting
│   │       └── reporter.py         # Telegram reports + alerts
│   ├── core/
│   │   ├── database.py             # SQLite — 8 tables
│   │   ├── config.py               # Settings loader (.env + yaml)
│   │   ├── queue.py                # Persistent task queue
│   │   └── scheduler.py            # APScheduler background jobs
│   └── cli/
│       └── main.py                 # Click CLI (14 commands)
├── config/settings.yaml            # Default configuration
├── tests/                          # pytest test suite
└── docs/                           # Architecture, PRD, stories
```

### Tech Stack
| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Browser automation | Playwright (async, stealth) |
| AI | Anthropic Claude (claude-opus-4-5) |
| Database | SQLite (stdlib `sqlite3`) |
| Scheduler | APScheduler BackgroundScheduler |
| CLI | Click |
| Notifications | python-telegram-bot |
| Config | python-dotenv + PyYAML |

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/your-org/eworks-os.git
cd eworks-os
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and fill in your credentials
```

Required variables:
- `ANTHROPIC_API_KEY` — Anthropic API key
- `LINKEDIN_EMAIL` + `LINKEDIN_PASSWORD` — LinkedIn account
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` — Telegram bot

### 3. Install Playwright browsers

```bash
playwright install chromium
```

### 4. Log in to LinkedIn

```bash
eworks auth login --email you@example.com --password yourpass
```

### 5. Create and run a campaign

```bash
# Create campaign
eworks campaign create --name "Q3 Outreach" --daily-limit 20

# Start it
eworks campaign start 1

# Run the agent
eworks agent run --campaign 1
```

---

## CLI Reference

### Authentication
```bash
eworks auth login --email EMAIL --password PASSWORD   # Log in + save session
eworks auth status                                     # Check session validity
```

### Campaigns
```bash
eworks campaign create --name NAME --daily-limit N    # Create new campaign
eworks campaign list                                   # List all campaigns
eworks campaign start CAMPAIGN_ID                     # Activate campaign
eworks campaign pause CAMPAIGN_ID                     # Pause campaign
```

### Prospects
```bash
eworks prospect list --campaign CAMPAIGN_ID [--status STATUS]  # List prospects
eworks prospect score --campaign CAMPAIGN_ID                   # Re-score prospects
```

### Agent
```bash
eworks agent run --campaign CAMPAIGN_ID [--dry-run]   # Run outreach agent
eworks agent status                                    # Show recent runs
```

### Reporting
```bash
eworks report daily --campaign CAMPAIGN_ID            # Send Telegram daily report
```

### Configuration
```bash
eworks config set KEY VALUE                           # Store a config value
eworks config show                                    # Display all config
```

### Daemon
```bash
eworks daemon start                                   # Start background scheduler
eworks daemon stop                                    # Stop scheduler
eworks daemon status                                  # Check scheduler status
```

All commands support `--json` for machine-readable output.

---

## ICP Scoring

Prospects are scored 0–100 based on five weighted signals:

| Signal | Weight | Criteria |
|---|---|---|
| Title match | 30 pts | CEO/CTO/Founder/Director/VP = 30; Manager/Lead = 15 |
| Company size | 20 pts | Startup/scale-up signals = 20; small/boutique = 10 |
| Location | 15 pts | Brazil/LATAM/USA/Europe = 15; other = 5 |
| Industry | 20 pts | Tech/SaaS/Fintech/AI = 20; adjacent = 10 |
| Engagement | 15 pts | Any mutual connections = 15 |

Default threshold: 60 points (configurable via `ICP_SCORE_THRESHOLD`).

---

## Safety & Rate Limits

- **Hard limit:** 20 connection requests per day (LinkedIn safe zone)
- **Time windows:** 9:00–11:30 AM and 2:00–4:30 PM only
- **Between sends:** 30–90 second random delay
- **Page loads:** 1.5–4.0 second random delay
- **Restriction detection:** Stops immediately on any LinkedIn warning

---

## Running Tests

```bash
pytest tests/ -v
```

Expected output: **15 passed**.

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key | — |
| `LINKEDIN_EMAIL` | LinkedIn account email | — |
| `LINKEDIN_PASSWORD` | LinkedIn account password | — |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | — |
| `TELEGRAM_CHAT_ID` | Telegram chat/user ID | — |
| `DATABASE_PATH` | SQLite database path | `data/eworks.db` |
| `SESSION_DIR` | Browser session directory | `session/` |
| `DAILY_CONNECTION_LIMIT` | Max connections/day | `20` |
| `ICP_SCORE_THRESHOLD` | Min ICP score to contact | `60.0` |

---

## License

MIT © Cesar Schneider / Eworks Labs
