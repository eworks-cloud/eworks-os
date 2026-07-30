     1|# Eworks OS
     2|
     3|**Multi-Agent Company Operating System** — AI-powered LinkedIn outreach automation built on Python 3.12.
     4|
     5|Eworks OS is a modular agent framework that automates B2B prospecting on LinkedIn: it discovers connections, scores them against your Ideal Customer Profile (ICP), generates hyper-personalized outreach messages with Claude AI, sends connection requests with human-like timing, and reports results to Telegram — all on autopilot.
     6|
     7|---
     8|
     9|## Architecture Overview
    10|
    11|```
    12|eworks-os/
    13|├── eworks/
    14|│   ├── agents/
    15|│   │   ├── base.py                 # BaseAgent abstract class
    16|│   │   └── prospector/
    17|│   │       ├── auth.py             # LinkedIn Playwright session (stealth)
    18|│   │       ├── discovery.py        # Connection scraper + ICP scorer
    19|│   │       ├── generator.py        # Claude AI message generator
    20|│   │       ├── executor.py         # Send messages + rate limiting
    21|│   │       └── reporter.py         # Telegram reports + alerts
    22|│   ├── core/
    23|│   │   ├── database.py             # SQLite — 8 tables
    24|│   │   ├── config.py               # Settings loader (.env + yaml)
    25|│   │   ├── queue.py                # Persistent task queue
    26|│   │   └── scheduler.py            # APScheduler background jobs
    27|│   └── cli/
    28|│       └── main.py                 # Click CLI (40+ commands)
    31|    31|├── config/settings.yaml            # Default configuration
    32|    32|├── knowledge-base/                 # Curated knowledge for Marketing & Sales
    33|    33|├── tests/                          # pytest test suite
    34|    34|└── docs/                           # Architecture, PRD, stories
    35|    35|```
    33|
    34|### Tech Stack
    35|| Layer | Technology |
    36||---|---|
    37|| Language | Python 3.12 |
    38|| Browser automation | Playwright (async, stealth) |
    39|| AI | Anthropic Claude (claude-opus-4-5) |
    40|| Database | SQLite (stdlib `sqlite3`) |
    41|| Scheduler | APScheduler BackgroundScheduler |
    42|| CLI | Click |
    43|| Notifications | python-telegram-bot |
    44|| Config | python-dotenv + PyYAML |
    45|
    46|---
    47|
    48|## Quick Start
    49|
    50|### 1. Clone and install
    51|
    52|```bash
    53|git clone https://github.com/your-org/eworks-os.git
    54|cd eworks-os
    55|pip install -e .
    56|```
    57|
    58|### 2. Configure
    59|
    60|```bash
    61|cp .env.example .env
    62|# Edit .env and fill in your credentials
    63|```
    64|
    65|Required variables:
    66|- `ANTHROPIC_API_KEY` — Anthropic API key
    67|- `LINKEDIN_EMAIL` + `LINKEDIN_PASSWORD` — LinkedIn account
    68|- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` — Telegram bot
    69|
    70|### 3. Install Playwright browsers
    71|
    72|```bash
    73|playwright install chromium
    74|```
    75|
    76|### 4. Log in to LinkedIn
    77|
    78|```bash
    79|eworks auth login --email you@example.com --password yourpass
    80|```
    81|
    82|### 5. Create and run a campaign
    83|
    84|```bash
    85|# Create campaign
    86|eworks campaign create --name "Q3 Outreach" --daily-limit 20
    87|
    88|# Start it
    89|eworks campaign start 1
    90|
    91|# Run the agent
    92|eworks agent run --campaign 1
    93|```
    94|
    95|---
    96|
    97|## CLI Reference
    98|
    99|### Authentication
   100|```bash
   101|eworks auth login --email EMAIL --password PASSWORD   # Log in + save session
   102|eworks auth status                                     # Check session validity
   103|```
   104|
   105|### Campaigns
   106|```bash
   107|eworks campaign create --name NAME --daily-limit N    # Create new campaign
   108|eworks campaign list                                   # List all campaigns
   109|eworks campaign start CAMPAIGN_ID                     # Activate campaign
   110|eworks campaign pause CAMPAIGN_ID                     # Pause campaign
   111|```
   112|
   113|### Prospects
   114|```bash
   115|eworks prospect list --campaign CAMPAIGN_ID [--status STATUS]  # List prospects
   116|eworks prospect score --campaign CAMPAIGN_ID                   # Re-score prospects
   117|```
   118|
   119|### Agent
   120|```bash
   121|eworks agent run --campaign CAMPAIGN_ID [--dry-run]   # Run outreach agent
   122|eworks agent status                                    # Show recent runs
   123|```
   124|
   125|### Reporting
   126|```bash
   127|eworks report daily --campaign CAMPAIGN_ID            # Send Telegram daily report
   128|```
   129|
   130|### Configuration
   131|```bash
   132|eworks config set KEY VALUE                           # Store a config value
   133|eworks config show                                    # Display all config
   134|```
   135|
   136|### Daemon
   137|```bash
   138|eworks daemon start                                   # Start background scheduler
   139|eworks daemon stop                                    # Stop scheduler
   140|eworks daemon status                                  # Check scheduler status
   141|```
   142|
   143|All commands support `--json` for machine-readable output.
   144|
   145|---
   146|
   147|## ICP Scoring
   148|
   149|Prospects are scored 0–100 based on five weighted signals:
   150|
   151|| Signal | Weight | Criteria |
   152||---|---|---|
   153|| Title match | 30 pts | CEO/CTO/Founder/Director/VP = 30; Manager/Lead = 15 |
   154|| Company size | 20 pts | Startup/scale-up signals = 20; small/boutique = 10 |
   155|| Location | 15 pts | Brazil/LATAM/USA/Europe = 15; other = 5 |
   156|| Industry | 20 pts | Tech/SaaS/Fintech/AI = 20; adjacent = 10 |
   157|| Engagement | 15 pts | Any mutual connections = 15 |
   158|
   159|Default threshold: 60 points (configurable via `ICP_SCORE_THRESHOLD`).
   160|
   161|---
   162|
   163|## Safety & Rate Limits
   164|
   165|- **Hard limit:** 20 connection requests per day (LinkedIn safe zone)
   166|- **Time windows:** 9:00–11:30 AM and 2:00–4:30 PM only
   167|- **Between sends:** 30–90 second random delay
   168|- **Page loads:** 1.5–4.0 second random delay
   169|- **Restriction detection:** Stops immediately on any LinkedIn warning
   170|
   171|---
   172|
   173|## Running Tests
   174|
   175|```bash
   176|pytest tests/ -v
   177|```
   178|
   179|Expected output: **15 passed**.
   180|
   181|---
   182|
   183|## Environment Variables
   184|
   185|| Variable | Description | Default |
   186||---|---|---|
   187|| `ANTHROPIC_API_KEY` | Anthropic API key | — |
   188|| `LINKEDIN_EMAIL` | LinkedIn account email | — |
   189|| `LINKEDIN_PASSWORD` | LinkedIn account password | — |
   190|| `TELEGRAM_BOT_TOKEN` | Telegram bot token | — |
   191|| `TELEGRAM_CHAT_ID` | Telegram chat/user ID | — |
   192|| `DATABASE_PATH` | SQLite database path | `data/eworks.db` |
   193|| `SESSION_DIR` | Browser session directory | `session/` |
   194|| `DAILY_CONNECTION_LIMIT` | Max connections/day | `20` |
   195|| `ICP_SCORE_THRESHOLD` | Min ICP score to contact | `60.0` |
   196|
   197|---
   198|
   199|## License
   200|
   201|MIT © Cesar Schneider / Eworks Labs
   202|