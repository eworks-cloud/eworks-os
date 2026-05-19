# Eworks OS — API & CLI Design

**Version:** 1.0  
**Author:** Aria (Architect Agent)  
**Date:** 2026-05-19  
**Status:** Approved for MVP

---

## 1. CLI Overview

The CLI is the primary human interface to Eworks OS. It is built with **Typer** and installed as the `eworks` command.

```
eworks [OPTIONS] COMMAND [ARGS]...

Options:
  --config PATH   Config file path [default: ./config/settings.yaml]
  --db PATH       Database path [default: ./eworks.db]
  --verbose       Enable verbose logging
  --version       Show version and exit
  --help

Commands:
  auth        Manage LinkedIn authentication
  campaign    Manage prospecting campaigns
  prospect    View and manage prospects
  message     Message management and generation
  agent       Directly run agent tasks
  monitor     View system status and logs
  config      Configuration management
  daemon      Run the background dispatcher
  export      Export data to CSV/JSON
```

---

## 2. Command Reference

### 2.1 `eworks auth`

```
eworks auth COMMAND

Commands:
  linkedin        Authenticate LinkedIn account(s)
  status          Show current auth status for all accounts
  test            Test that a stored session is valid
```

#### `eworks auth linkedin`

```
eworks auth linkedin [OPTIONS]

  Authenticate a LinkedIn account interactively (opens browser).
  Stores session in Playwright persistent context.

Options:
  --account SLUG   Account slug to create/update [required]
  --email TEXT     LinkedIn email address [required]
  --reauth         Force re-authentication even if session exists
  --headless       Run browser headlessly (default: False for auth)
  --help
```

**Example:**
```bash
eworks auth linkedin --account cesar_main --email cesar@example.com
# Opens Chromium, user logs in manually
# Session saved to ~/.eworks/browser/cesar_main/
# ✅ Session stored for cesar_main (expires ~30 days)
```

#### `eworks auth status`

```
eworks auth status

Output:
  Account: cesar_main
  Email:   cesar@example.com
  Status:  ✅ active
  Last activity: 2026-05-19 14:32:11
  Daily limits:  search=23/80  messages=8/20  connections=5/20
```

---

### 2.2 `eworks campaign`

```
eworks campaign COMMAND

Commands:
  create     Create a new campaign
  list       List all campaigns
  show       Show campaign details and stats
  pause      Pause a running campaign
  resume     Resume a paused campaign
  archive    Archive a completed campaign
  edit       Edit campaign settings
```

#### `eworks campaign create`

```
eworks campaign create [OPTIONS]

Options:
  --name TEXT                 Campaign name [required]
  --search-query TEXT         LinkedIn search keywords [required]
  --persona SLUG              Persona slug to use [required]
  --account SLUG              LinkedIn account slug [default: first active]
  --location TEXT             Location filter (e.g. "San Francisco Bay Area")
  --industry TEXT             Industry filter
  --title-keywords TEXT       Title must contain these keywords (comma-separated)
  --daily-search-limit INT    Max profiles to visit per day [default: 50]
  --daily-message-limit INT   Max messages per day [default: 20]
  --prospect-target INT       Stop after N prospects found
  --message-template TEXT     Optional override template (use quotes)
  --notes TEXT                Operator notes
  --help
```

**Example:**
```bash
eworks campaign create \
  --name "SaaS CTOs Q3 2026" \
  --search-query "Chief Technology Officer SaaS startup" \
  --persona cesar_intro \
  --location "United States" \
  --title-keywords "CTO,Chief Technology Officer,VP Engineering" \
  --daily-search-limit 40 \
  --daily-message-limit 15 \
  --prospect-target 200

# Output:
# ✅ Campaign created: SaaS CTOs Q3 2026 (id=3)
# Search will run at ~09:15 AM daily
# Messages will be sent at ~02:10 PM daily
# To start: eworks campaign resume --name "SaaS CTOs Q3 2026"
```

#### `eworks campaign list`

```
eworks campaign list [OPTIONS]

Options:
  --status TEXT    Filter by status [active|paused|completed|archived|all]
  --format TEXT    Output format [table|json|csv] [default: table]
  --help

Output (table):
  ID  Name                    Status   Prospects  Messaged  Replied  Rate
  1   SaaS CTOs Q3 2026      active   87         34        6        17.6%
  2   FinTech Founders        paused   200        140       18       12.9%
```

#### `eworks campaign show`

```
eworks campaign show --name "SaaS CTOs Q3 2026"

Output:
  Campaign: SaaS CTOs Q3 2026 (id=3)
  Status:   active
  Account:  cesar_main

  Search Config:
    Query:   Chief Technology Officer SaaS startup
    Filters: location=United States, title=CTO|VP Engineering
    Daily search limit: 40
    Prospect target:    200

  Progress:
    Prospects discovered: 87 / 200
    Queued for message:   12
    Messages sent:        34
    Replied:              6  (17.6% reply rate)
    Interested:           2
    Disqualified:         8

  Recent Activity:
    2026-05-19 14:32  Sent message to Jane Smith (VP Eng @ Acme)
    2026-05-19 09:22  Found 18 new prospects
    2026-05-18 14:28  Reply from Bob Jones (CTO @ Widget Co) — 💬 interested
```

---

### 2.3 `eworks prospect`

```
eworks prospect COMMAND

Commands:
  list         List prospects for a campaign
  show         Show full prospect details
  disqualify   Mark prospect as disqualified
  dnc          Add to do-not-contact list
  tag          Add tags to a prospect
```

#### `eworks prospect list`

```
eworks prospect list [OPTIONS]

Options:
  --campaign TEXT   Campaign name or ID [required]
  --status TEXT     Filter by status [default: all]
  --limit INT       Number of results [default: 50]
  --offset INT      Pagination offset [default: 0]
  --format TEXT     [table|json|csv] [default: table]
  --help

Output:
  ID    Name              Title                  Company           Status
  1021  Jane Smith        VP Engineering         Acme Corp         messaged
  1022  Bob Jones         CTO                    Widget Co         replied
  1023  Alice Lee         Chief Technology Off.  StartupXYZ        queued
```

#### `eworks prospect show`

```
eworks prospect show --id 1022

Output:
  Prospect: Bob Jones
  Title:    CTO at Widget Co
  Location: Austin, TX
  LinkedIn: https://linkedin.com/in/bobjones

  Status: replied ✅
  
  Messages:
    [2026-05-15] connection_note — SENT
      "Hi Bob, I noticed Widget Co is scaling its eng team..."
    [2026-05-17] Reply received:
      "Thanks! Happy to chat. When works for you?"
    
  Tags: saas, seed-stage, austin
```

#### `eworks prospect disqualify`

```
eworks prospect disqualify --id 1023 --reason "not a decision maker"
# ✅ Prospect Alice Lee marked as disqualified
```

#### `eworks prospect dnc`

```
eworks prospect dnc --id 1023
# ✅ Alice Lee added to do-not-contact list (permanent)
```

---

### 2.4 `eworks message`

```
eworks message COMMAND

Commands:
  preview      Generate a preview message for a prospect (no send)
  send         Send a message to a specific prospect (manual override)
  list         List messages for a campaign or prospect
  stats        Message statistics
```

#### `eworks message preview`

```
eworks message preview [OPTIONS]

Options:
  --prospect-id INT   Prospect ID [required]
  --campaign TEXT     Campaign name [required]
  --type TEXT         [connection_note|direct_message|follow_up] [default: connection_note]
  --help

Output:
  Generating message for: Bob Jones (CTO @ Widget Co)
  Persona: cesar_intro
  Type: connection_note (max 300 chars)

  ─────────────────────────────────────
  Hi Bob — I help SaaS CTOs reduce
  infrastructure costs by 40% without
  a rewrite. Thought it might be
  worth a quick chat. Open to connect?
  ─────────────────────────────────────
  Length: 167 chars ✅
  Tokens used: 312 (prompt) + 48 (completion)
  
  [P]review another  [S]end this  [E]dit  [Q]uit
```

#### `eworks message stats`

```
eworks message stats [OPTIONS]

Options:
  --campaign TEXT   Campaign name (omit for global stats)
  --days INT        Lookback period [default: 30]
  --help

Output:
  Message Statistics (last 30 days)
  Campaign: SaaS CTOs Q3 2026

  Sent:           34
  Delivered:      34  (100%)
  Failed:         0
  Replies:        6   (17.6%)
  Interested:     2   (5.9%)
  Avg tokens/msg: 287

  By type:
    connection_note: 28 sent, 5 replied (17.9%)
    direct_message:  6 sent,  1 replied (16.7%)
```

---

### 2.5 `eworks agent`

```
eworks agent COMMAND

Commands:
  run       Run an agent task immediately
  status    Show running agents
  history   Show agent run history
```

#### `eworks agent run`

```
eworks agent run [OPTIONS]

Options:
  --type TEXT       Agent type [search|message|monitor] [required]
  --campaign TEXT   Campaign name
  --prospect-id INT Prospect ID (for message type)
  --dry-run         Simulate without sending/saving
  --headless BOOL   Run browser headlessly [default: True]
  --help
```

**Example:**
```bash
# Run search immediately for a campaign
eworks agent run --type search --campaign "SaaS CTOs Q3 2026"

# Output (streaming):
# 🤖 LinkedInSearchAgent starting...
# 📋 Campaign: SaaS CTOs Q3 2026
# 🌐 Loading browser session (cesar_main)
# 🔍 Searching: "Chief Technology Officer SaaS startup"
# ─ Page 1: found 10 profiles
# ─ Page 2: found 10 profiles  
# ─ Page 3: found 8 profiles (3 already known, 5 new)
# ─ Page 4: rate limit pause (22s)...
# ─ Page 5: found 9 profiles
# ✅ Run complete: 37 profiles visited, 22 new prospects added
# ⏱  Duration: 4m 12s
# 📱 Telegram notification sent
```

#### `eworks agent history`

```
eworks agent history [OPTIONS]

Options:
  --type TEXT     Filter by agent type
  --days INT      Lookback [default: 7]
  --limit INT     Max results [default: 20]
  --format TEXT   [table|json] [default: table]

Output:
  Run ID        Agent               Status     Duration  Prospects  Messages
  f3a1b2...     LinkedInSearchAgent completed  4m12s     22         —
  9c2d11...     LinkedInMessenger   completed  8m44s     —          15
  7e4f33...     LinkedInMonitor     completed  2m01s     —          —
  2b9a12...     LinkedInMessenger   failed     0m12s     —          —
    └─ Error: Browser session requires verification
```

---

### 2.6 `eworks monitor`

```
eworks monitor COMMAND

Commands:
  status    Show system health and queue depth
  logs      Tail agent logs
  queue     Show task queue
```

#### `eworks monitor status`

```
eworks monitor status

Eworks OS — System Status
─────────────────────────────────────────────
Daemon:          ✅ running (pid 12345)
Database:        ✅ healthy (eworks.db — 4.2 MB)
Scheduler:       ✅ 3 jobs active

LinkedIn Accounts:
  cesar_main:    ✅ active
    Today:       search=23/80  messages=8/20  connections=3/20
    Next run:    14:12 (message tasks)

Task Queue:
  pending:   5
  running:   1
  done:      84 (today)
  failed:    1

Campaigns:
  active:    2
  paused:    1
```

#### `eworks monitor queue`

```
eworks monitor queue [OPTIONS]

Options:
  --status TEXT   [pending|running|done|failed|all] [default: pending]
  --limit INT     [default: 20]

Output:
  ID    Type       Status   Priority  Campaign            Scheduled
  101   message    pending  5         SaaS CTOs Q3 2026   14:10:00
  102   message    pending  5         SaaS CTOs Q3 2026   14:10:00
  103   monitor    pending  3         —                   16:00:00
```

---

### 2.7 `eworks config`

```
eworks config COMMAND

Commands:
  show        Show current configuration
  set         Set a configuration value
  persona     Manage AI personas
  validate    Validate config files
```

#### `eworks config persona create`

```
eworks config persona create [OPTIONS]

Options:
  --slug TEXT              Unique slug [required]
  --name TEXT              Display name [required]
  --sender-name TEXT       Name in messages [required]
  --sender-title TEXT      Title in messages [required]
  --sender-company TEXT    Company [required]
  --value-prop TEXT        Core value proposition [required]
  --tone TEXT              [professional|casual|direct] [default: professional]
  --system-prompt-file PATH  Path to .txt file with full system prompt
  --help
```

---

### 2.8 `eworks daemon`

```
eworks daemon [OPTIONS]

  Start the background dispatcher and scheduler.
  Intended for use as a systemd service.

Options:
  --workers INT    Number of concurrent task workers [default: 1]
  --poll-interval INT  Queue poll interval in seconds [default: 30]
  --no-scheduler   Disable APScheduler (manual task dispatch only)
  --help

Output:
  2026-05-19 09:00:01 INFO  Eworks OS daemon starting
  2026-05-19 09:00:01 INFO  Database: ./eworks.db
  2026-05-19 09:00:01 INFO  Scheduler: 3 jobs loaded
  2026-05-19 09:00:01 INFO  Dispatcher polling every 30s
  2026-05-19 09:15:03 INFO  Task claimed: search (campaign_id=3)
  2026-05-19 09:15:03 INFO  Agent LinkedInSearchAgent started (run_id=f3a1b2)
  ...
```

---

### 2.9 `eworks export`

```
eworks export COMMAND

Commands:
  prospects   Export prospects to CSV/JSON
  messages    Export message history
  report      Generate campaign summary report
```

#### `eworks export prospects`

```
eworks export prospects [OPTIONS]

Options:
  --campaign TEXT   Campaign name [required]
  --status TEXT     Filter by status [default: all]
  --format TEXT     [csv|json] [default: csv]
  --output PATH     Output file [default: stdout]
  --help

CSV columns:
  id, first_name, last_name, current_title, current_company, location,
  linkedin_url, status, created_at, last_message_date, reply_text
```

---

## 3. Configuration Schema

### 3.1 `.env` (Secrets — never committed)

```dotenv
# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Telegram
TELEGRAM_BOT_TOKEN=7123456789:AAF...
TELEGRAM_CHAT_ID=123456789

# Database
DATABASE_URL=sqlite:///./eworks.db

# Encryption key for stored credentials (generate with: eworks config generate-key)
EWORKS_ENCRYPTION_KEY=...

# Environment
EWORKS_ENV=production    # development | production
LOG_LEVEL=INFO
```

### 3.2 `config/settings.yaml` (Operational config — committed)

```yaml
# ─────────────────────────────────────────────────────────
# Eworks OS Settings
# ─────────────────────────────────────────────────────────

app:
  name: Eworks OS
  version: "0.1.0"
  timezone: "America/New_York"

database:
  # Overridden by DATABASE_URL env var
  path: ./eworks.db
  wal_mode: true

browser:
  profiles_dir: ~/.eworks/browser
  headless: true
  slow_mo: 0              # Extra ms delay between Playwright actions (0 = off)
  timeout_ms: 30000       # Page load timeout
  viewport:
    width: 1440
    height: 900
  locale: en-US

linkedin:
  base_url: https://www.linkedin.com
  
  # Daily hard limits per account (cannot exceed even if campaign allows more)
  hard_limits:
    search_pages: 15
    profile_views: 80
    connection_requests: 20
    messages: 30
  
  # Run windows (local time)
  run_windows:
    morning:
      enabled: true
      start: "09:00"
      end: "11:30"
      jitter_minutes: 15
    afternoon:
      enabled: true
      start: "14:00"
      end: "16:30"
      jitter_minutes: 15
  
  # Days to run
  run_days: [monday, tuesday, wednesday, thursday, friday]
  
  # Delays between actions (milliseconds)
  delays:
    between_profile_views:
      min: 8000
      max: 25000
    between_pages:
      min: 3000
      max: 8000
    before_message_send:
      min: 1500
      max: 4000
    typing_speed_ms_per_char:
      min: 50
      max: 150

ai:
  message_model: claude-opus-4-5
  classification_model: claude-haiku-3-5
  max_retries: 3
  timeout_seconds: 30
  
  message_generation:
    max_connection_note_chars: 300
    max_direct_message_chars: 1500
    temperature: 0.7

scheduler:
  search_jobs:
    - cron: "0 9 * * 1-5"      # Weekdays 9 AM
      jitter_seconds: 900       # ± 15 min
  message_jobs:
    - cron: "0 14 * * 1-5"     # Weekdays 2 PM
      jitter_seconds: 900
  monitor_jobs:
    - interval_hours: 4
      jitter_seconds: 600
  digest_jobs:
    - cron: "0 18 * * 1-5"     # Daily 6 PM digest

dispatcher:
  poll_interval_seconds: 30
  max_concurrent_tasks: 1       # One at a time for MVP (browser constraint)
  task_timeout_seconds: 1800    # Kill task after 30 min

notifications:
  telegram:
    enabled: true
    notify_on:
      - run_complete
      - run_failed
      - prospect_replied
      - session_requires_auth
      - daily_digest
    quiet_hours:
      start: "22:00"
      end: "08:00"

logging:
  level: INFO
  format: json          # json | console
  output: ./logs/eworks.log
  max_bytes: 10485760   # 10 MB
  backup_count: 5
```

---

## 4. Output Formats

### 4.1 Structured JSON Output

All commands support `--format json` for pipeline integration:

```bash
eworks campaign list --format json
```

```json
[
  {
    "id": 3,
    "name": "SaaS CTOs Q3 2026",
    "status": "active",
    "stats": {
      "prospects_total": 87,
      "prospects_messaged": 34,
      "prospects_replied": 6,
      "reply_rate": 0.176
    },
    "created_at": "2026-05-01T09:00:00Z"
  }
]
```

### 4.2 Agent Run Result JSON (stored in `task_queue.result_json`)

```json
{
  "agent": "LinkedInSearchAgent",
  "run_id": "f3a1b2c4-...",
  "campaign_id": 3,
  "success": true,
  "metrics": {
    "pages_visited": 5,
    "profiles_scraped": 37,
    "prospects_new": 22,
    "prospects_existing": 15,
    "errors": 0,
    "duration_seconds": 252
  }
}
```

```json
{
  "agent": "LinkedInMessengerAgent",
  "run_id": "9c2d1145-...",
  "campaign_id": 3,
  "success": true,
  "metrics": {
    "prospects_attempted": 15,
    "messages_sent": 15,
    "messages_failed": 0,
    "connection_notes": 11,
    "direct_messages": 4,
    "total_tokens_used": 4301,
    "duration_seconds": 524
  }
}
```

### 4.3 Telegram Notification Format

**Run Complete:**
```
✅ Search Complete — SaaS CTOs Q3 2026
📊 22 new prospects found (37 profiles visited)
⏱ Duration: 4m 12s
📅 Next run: Tomorrow 09:15 AM
```

**Message Run Complete:**
```
📨 Messages Sent — SaaS CTOs Q3 2026
✉️ 15 messages sent (0 failed)
💰 Tokens used: 4,301
⏱ Duration: 8m 44s
```

**Reply Alert:**
```
💬 New Reply!
👤 Bob Jones — CTO @ Widget Co
🏷 Campaign: SaaS CTOs Q3 2026
💬 "Thanks! Happy to chat. When works for you?"
🤖 Intent: interested 🟢
🔗 https://linkedin.com/in/bobjones
```

**Error Alert:**
```
🚨 Agent Failed — LinkedInMessengerAgent
❌ Error: Browser session requires verification
📋 Task ID: 45
🔧 Action required: eworks auth linkedin --account cesar_main --reauth
```

**Daily Digest (6 PM):**
```
📊 Eworks OS Daily Digest — Mon May 19

Campaigns:
  SaaS CTOs Q3 2026    → 22 found | 15 messaged | 2 replied
  FinTech Founders      → paused

Today's totals:
  Profiles visited:  37
  Messages sent:     15
  Replies received:  2
  New interested:    1

🔋 Account limits:
  cesar_main: search=37/80 | msgs=15/20 | conn=11/20
```

---

## 5. Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Authentication required |
| 4 | Rate limit reached |
| 5 | Database error |
| 6 | LinkedIn session error |
| 7 | API error (Anthropic/Telegram) |
