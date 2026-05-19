# Eworks OS — Data Model

**Version:** 1.0  
**Author:** Aria (Architect Agent)  
**Date:** 2026-05-19  
**Status:** Approved for MVP

---

## 1. Entity Relationship Overview

```
campaigns ──────────────┐
     │                  │
     │ 1:N              │ 1:N
     ▼                  ▼
task_queue          messages ──── prospects
                        │              │
                        │ N:1          │ 1:N
                        └──────────────┘
                                       │
                                       │ 1:N
                                       ▼
                                 agent_runs
```

**Entities:**
- `campaigns` — a prospecting campaign (search criteria + persona + limits)
- `prospects` — individual LinkedIn profiles found and tracked
- `messages` — outbound messages sent to prospects
- `task_queue` — pending/running/completed agent tasks
- `agent_runs` — log of every agent execution (audit trail)
- `settings_store` — key-value store for runtime config and encrypted credentials

---

## 2. Full Table Definitions

### 2.1 `campaigns`

Defines a prospecting effort: who to target, what persona to use, rate limits.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | |
| name | TEXT | NOT NULL, UNIQUE | Human label, e.g. "SaaS CTOs Q3" |
| status | TEXT | NOT NULL, DEFAULT 'active' | `active`, `paused`, `completed`, `archived` |
| search_query | TEXT | NOT NULL | LinkedIn search keywords |
| search_filters | TEXT | — | JSON: `{location, industry, company_size, title_keywords}` |
| persona_id | INTEGER | FK → personas.id | Which AI persona to use |
| message_template | TEXT | — | Base template; Claude fills in personalisation |
| daily_search_limit | INTEGER | NOT NULL, DEFAULT 50 | Max profiles to visit per day |
| daily_message_limit | INTEGER | NOT NULL, DEFAULT 20 | Max messages to send per day |
| total_prospect_target | INTEGER | — | Stop searching after N prospects |
| linkedin_account_id | INTEGER | FK → linkedin_accounts.id | Which LinkedIn account to use |
| created_at | DATETIME | NOT NULL, DEFAULT NOW | |
| updated_at | DATETIME | NOT NULL, DEFAULT NOW | |
| notes | TEXT | — | Free-text operator notes |

### 2.2 `prospects`

One row per LinkedIn profile ever seen by the system.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | |
| campaign_id | INTEGER | FK → campaigns.id, NOT NULL | |
| linkedin_url | TEXT | NOT NULL, UNIQUE | Canonical profile URL (normalized) |
| linkedin_urn | TEXT | — | LinkedIn internal URN if extracted |
| first_name | TEXT | NOT NULL | |
| last_name | TEXT | NOT NULL | |
| headline | TEXT | — | Profile headline |
| current_company | TEXT | — | |
| current_title | TEXT | — | |
| location | TEXT | — | |
| about | TEXT | — | Profile summary/about section |
| experience_json | TEXT | — | JSON array of experience entries |
| education_json | TEXT | — | JSON array of education entries |
| connection_degree | INTEGER | — | 1, 2, or 3 (LinkedIn connection degree) |
| is_connected | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether we are 1st-degree connected |
| status | TEXT | NOT NULL, DEFAULT 'discovered' | See status enum below |
| disqualified_reason | TEXT | — | If status='disqualified', why |
| tags | TEXT | — | JSON array of string tags |
| created_at | DATETIME | NOT NULL, DEFAULT NOW | |
| updated_at | DATETIME | NOT NULL, DEFAULT NOW | |
| last_viewed_at | DATETIME | — | Last time we visited their profile |

**Prospect Status Enum:**
```
discovered      → profile found in search, not yet processed
queued          → message task created, awaiting send
connection_sent → connection request sent, awaiting acceptance
messaged        → direct message sent (already connected)
replied         → prospect replied to our message
interested      → AI classified reply as interested
not_interested  → AI classified reply as not interested / opt-out
disqualified    → manually or automatically removed from campaign
do_not_contact  → permanent opt-out (survives campaign deletion)
```

### 2.3 `messages`

Every outbound message attempt.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | |
| prospect_id | INTEGER | FK → prospects.id, NOT NULL | |
| campaign_id | INTEGER | FK → campaigns.id, NOT NULL | |
| type | TEXT | NOT NULL | `connection_note`, `direct_message`, `follow_up` |
| content | TEXT | NOT NULL | Final message text sent |
| generated_by | TEXT | NOT NULL | `claude-opus-4-5`, `human`, `template` |
| prompt_tokens | INTEGER | — | Tokens used for generation |
| completion_tokens | INTEGER | — | Tokens in generated message |
| sent_at | DATETIME | — | NULL if not yet sent |
| send_status | TEXT | NOT NULL, DEFAULT 'pending' | `pending`, `sent`, `failed`, `skipped` |
| send_error | TEXT | — | Error message if failed |
| linkedin_thread_id | TEXT | — | LinkedIn thread identifier (for reply tracking) |
| replied_at | DATETIME | — | When prospect replied |
| reply_text | TEXT | — | Raw reply text |
| reply_intent | TEXT | — | Claude classification: `interested`, `not_interested`, `question`, `other` |
| reply_sentiment | REAL | — | Sentiment score -1.0 to 1.0 |
| created_at | DATETIME | NOT NULL, DEFAULT NOW | |
| updated_at | DATETIME | NOT NULL, DEFAULT NOW | |

### 2.4 `task_queue`

Durable task queue backing the dispatcher.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | |
| type | TEXT | NOT NULL | `search`, `message`, `monitor`, `notify`, `cleanup` |
| status | TEXT | NOT NULL, DEFAULT 'pending' | `pending`, `running`, `done`, `failed`, `cancelled` |
| priority | INTEGER | NOT NULL, DEFAULT 5 | 1 (highest) – 10 (lowest) |
| payload | TEXT | NOT NULL | JSON task parameters |
| campaign_id | INTEGER | FK → campaigns.id | Associated campaign (nullable) |
| prospect_id | INTEGER | FK → prospects.id | Associated prospect (nullable) |
| worker_id | TEXT | — | Dispatcher instance ID |
| retry_count | INTEGER | NOT NULL, DEFAULT 0 | |
| max_retries | INTEGER | NOT NULL, DEFAULT 3 | |
| error_message | TEXT | — | Last failure message |
| result_json | TEXT | — | Agent Result JSON on success |
| scheduled_for | DATETIME | NOT NULL, DEFAULT NOW | Earliest execution time |
| started_at | DATETIME | — | |
| finished_at | DATETIME | — | |
| created_at | DATETIME | NOT NULL, DEFAULT NOW | |

### 2.5 `agent_runs`

Audit log of every agent execution. Immutable append-only.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | |
| run_id | TEXT | NOT NULL, UNIQUE | UUID v4 |
| agent_type | TEXT | NOT NULL | `LinkedInSearchAgent`, etc. |
| task_id | INTEGER | FK → task_queue.id | |
| campaign_id | INTEGER | FK → campaigns.id | |
| status | TEXT | NOT NULL | `started`, `completed`, `failed` |
| duration_seconds | REAL | — | Wall clock time |
| metrics_json | TEXT | — | JSON: `{profiles_visited, messages_sent, errors, ...}` |
| error_traceback | TEXT | — | Full traceback if failed |
| started_at | DATETIME | NOT NULL | |
| finished_at | DATETIME | — | |

### 2.6 `personas`

AI persona definitions. Determines tone and context of generated messages.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | |
| slug | TEXT | NOT NULL, UNIQUE | e.g. `cesar_intro` |
| name | TEXT | NOT NULL | Display name |
| sender_name | TEXT | NOT NULL | Name used in messages |
| sender_title | TEXT | NOT NULL | Title/role in messages |
| sender_company | TEXT | NOT NULL | Company name |
| system_prompt | TEXT | NOT NULL | Claude system prompt defining persona |
| value_proposition | TEXT | NOT NULL | Core value prop injected into prompts |
| tone | TEXT | NOT NULL, DEFAULT 'professional' | `professional`, `casual`, `direct` |
| max_message_length | INTEGER | NOT NULL, DEFAULT 300 | Chars limit for connection notes |
| created_at | DATETIME | NOT NULL, DEFAULT NOW | |
| updated_at | DATETIME | NOT NULL, DEFAULT NOW | |

### 2.7 `linkedin_accounts`

LinkedIn accounts used for automation. Credentials stored encrypted.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PK, AUTOINCREMENT | |
| slug | TEXT | NOT NULL, UNIQUE | e.g. `cesar_main` |
| email | TEXT | NOT NULL | LinkedIn login email |
| encrypted_password | TEXT | NOT NULL | Fernet-encrypted password |
| browser_profile_path | TEXT | NOT NULL | Path to Playwright persistent context |
| session_status | TEXT | NOT NULL, DEFAULT 'active' | `active`, `requires_verification`, `banned` |
| daily_search_count | INTEGER | NOT NULL, DEFAULT 0 | Resets at midnight |
| daily_message_count | INTEGER | NOT NULL, DEFAULT 0 | Resets at midnight |
| daily_connection_count | INTEGER | NOT NULL, DEFAULT 0 | Resets at midnight |
| last_reset_date | DATE | — | Date of last daily counter reset |
| last_activity_at | DATETIME | — | |
| created_at | DATETIME | NOT NULL, DEFAULT NOW | |

### 2.8 `settings_store`

Runtime key-value config store (encrypted for sensitive values).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| key | TEXT | PK | Setting key |
| value | TEXT | NOT NULL | Setting value |
| encrypted | BOOLEAN | NOT NULL, DEFAULT FALSE | If TRUE, value is Fernet-encrypted |
| description | TEXT | — | Human-readable description |
| updated_at | DATETIME | NOT NULL, DEFAULT NOW | |

---

## 3. SQLite Schema (CREATE TABLE Statements)

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA synchronous = NORMAL;

-- ─────────────────────────────────────────────────────────
-- personas
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS personas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    slug                TEXT    NOT NULL UNIQUE,
    name                TEXT    NOT NULL,
    sender_name         TEXT    NOT NULL,
    sender_title        TEXT    NOT NULL,
    sender_company      TEXT    NOT NULL,
    system_prompt       TEXT    NOT NULL,
    value_proposition   TEXT    NOT NULL,
    tone                TEXT    NOT NULL DEFAULT 'professional'
                                CHECK(tone IN ('professional','casual','direct')),
    max_message_length  INTEGER NOT NULL DEFAULT 300,
    created_at          DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at          DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────
-- linkedin_accounts
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS linkedin_accounts (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    slug                    TEXT    NOT NULL UNIQUE,
    email                   TEXT    NOT NULL,
    encrypted_password      TEXT    NOT NULL,
    browser_profile_path    TEXT    NOT NULL,
    session_status          TEXT    NOT NULL DEFAULT 'active'
                                    CHECK(session_status IN ('active','requires_verification','banned')),
    daily_search_count      INTEGER NOT NULL DEFAULT 0,
    daily_message_count     INTEGER NOT NULL DEFAULT 0,
    daily_connection_count  INTEGER NOT NULL DEFAULT 0,
    last_reset_date         DATE,
    last_activity_at        DATETIME,
    created_at              DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────
-- campaigns
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS campaigns (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    name                    TEXT    NOT NULL UNIQUE,
    status                  TEXT    NOT NULL DEFAULT 'active'
                                    CHECK(status IN ('active','paused','completed','archived')),
    search_query            TEXT    NOT NULL,
    search_filters          TEXT,   -- JSON
    persona_id              INTEGER NOT NULL REFERENCES personas(id),
    message_template        TEXT,
    daily_search_limit      INTEGER NOT NULL DEFAULT 50,
    daily_message_limit     INTEGER NOT NULL DEFAULT 20,
    total_prospect_target   INTEGER,
    linkedin_account_id     INTEGER NOT NULL REFERENCES linkedin_accounts(id),
    notes                   TEXT,
    created_at              DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at              DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────
-- prospects
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS prospects (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id         INTEGER NOT NULL REFERENCES campaigns(id),
    linkedin_url        TEXT    NOT NULL UNIQUE,
    linkedin_urn        TEXT,
    first_name          TEXT    NOT NULL,
    last_name           TEXT    NOT NULL,
    headline            TEXT,
    current_company     TEXT,
    current_title       TEXT,
    location            TEXT,
    about               TEXT,
    experience_json     TEXT,   -- JSON array
    education_json      TEXT,   -- JSON array
    connection_degree   INTEGER CHECK(connection_degree IN (1,2,3)),
    is_connected        BOOLEAN NOT NULL DEFAULT FALSE,
    status              TEXT    NOT NULL DEFAULT 'discovered'
                                CHECK(status IN (
                                    'discovered','queued','connection_sent',
                                    'messaged','replied','interested',
                                    'not_interested','disqualified','do_not_contact'
                                )),
    disqualified_reason TEXT,
    tags                TEXT,   -- JSON array
    created_at          DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at          DATETIME NOT NULL DEFAULT (datetime('now')),
    last_viewed_at      DATETIME
);

CREATE INDEX IF NOT EXISTS idx_prospects_campaign ON prospects(campaign_id);
CREATE INDEX IF NOT EXISTS idx_prospects_status ON prospects(status);
CREATE INDEX IF NOT EXISTS idx_prospects_company ON prospects(current_company);

-- ─────────────────────────────────────────────────────────
-- messages
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS messages (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    prospect_id         INTEGER NOT NULL REFERENCES prospects(id),
    campaign_id         INTEGER NOT NULL REFERENCES campaigns(id),
    type                TEXT    NOT NULL
                                CHECK(type IN ('connection_note','direct_message','follow_up')),
    content             TEXT    NOT NULL,
    generated_by        TEXT    NOT NULL DEFAULT 'claude-opus-4-5',
    prompt_tokens       INTEGER,
    completion_tokens   INTEGER,
    sent_at             DATETIME,
    send_status         TEXT    NOT NULL DEFAULT 'pending'
                                CHECK(send_status IN ('pending','sent','failed','skipped')),
    send_error          TEXT,
    linkedin_thread_id  TEXT,
    replied_at          DATETIME,
    reply_text          TEXT,
    reply_intent        TEXT    CHECK(reply_intent IN ('interested','not_interested','question','other')),
    reply_sentiment     REAL    CHECK(reply_sentiment BETWEEN -1.0 AND 1.0),
    created_at          DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at          DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_messages_prospect ON messages(prospect_id);
CREATE INDEX IF NOT EXISTS idx_messages_campaign ON messages(campaign_id);
CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(send_status);
CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(linkedin_thread_id);

-- ─────────────────────────────────────────────────────────
-- task_queue
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS task_queue (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    type            TEXT    NOT NULL
                            CHECK(type IN ('search','message','monitor','notify','cleanup')),
    status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending','running','done','failed','cancelled')),
    priority        INTEGER NOT NULL DEFAULT 5 CHECK(priority BETWEEN 1 AND 10),
    payload         TEXT    NOT NULL,   -- JSON
    campaign_id     INTEGER REFERENCES campaigns(id),
    prospect_id     INTEGER REFERENCES prospects(id),
    worker_id       TEXT,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    max_retries     INTEGER NOT NULL DEFAULT 3,
    error_message   TEXT,
    result_json     TEXT,
    scheduled_for   DATETIME NOT NULL DEFAULT (datetime('now')),
    started_at      DATETIME,
    finished_at     DATETIME,
    created_at      DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tasks_status_scheduled
    ON task_queue(status, scheduled_for)
    WHERE status = 'pending';

-- ─────────────────────────────────────────────────────────
-- agent_runs
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_runs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id              TEXT    NOT NULL UNIQUE,
    agent_type          TEXT    NOT NULL,
    task_id             INTEGER REFERENCES task_queue(id),
    campaign_id         INTEGER REFERENCES campaigns(id),
    status              TEXT    NOT NULL
                                CHECK(status IN ('started','completed','failed')),
    duration_seconds    REAL,
    metrics_json        TEXT,   -- JSON
    error_traceback     TEXT,
    started_at          DATETIME NOT NULL,
    finished_at         DATETIME
);

CREATE INDEX IF NOT EXISTS idx_runs_campaign ON agent_runs(campaign_id);
CREATE INDEX IF NOT EXISTS idx_runs_agent ON agent_runs(agent_type);
CREATE INDEX IF NOT EXISTS idx_runs_started ON agent_runs(started_at);

-- ─────────────────────────────────────────────────────────
-- settings_store
-- ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings_store (
    key         TEXT    PRIMARY KEY,
    value       TEXT    NOT NULL,
    encrypted   BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    updated_at  DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────
-- Triggers: auto-update updated_at
-- ─────────────────────────────────────────────────────────
CREATE TRIGGER IF NOT EXISTS campaigns_updated_at
    AFTER UPDATE ON campaigns
    BEGIN UPDATE campaigns SET updated_at = datetime('now') WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS prospects_updated_at
    AFTER UPDATE ON prospects
    BEGIN UPDATE prospects SET updated_at = datetime('now') WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS messages_updated_at
    AFTER UPDATE ON messages
    BEGIN UPDATE messages SET updated_at = datetime('now') WHERE id = NEW.id; END;

CREATE TRIGGER IF NOT EXISTS personas_updated_at
    AFTER UPDATE ON personas
    BEGIN UPDATE personas SET updated_at = datetime('now') WHERE id = NEW.id; END;
```

---

## 4. Key Relationships

- **campaigns → prospects:** 1:N. A campaign discovers many prospects.
- **campaigns → messages:** 1:N. Campaign tracks all outreach.
- **prospects → messages:** 1:N. A prospect may receive multiple messages over time (connection note, then follow-up).
- **campaigns → persona:** N:1. Multiple campaigns can share a persona.
- **campaigns → linkedin_account:** N:1. Multiple campaigns can share an account (subject to daily limits).
- **task_queue → campaign:** N:1. Tasks are scoped to campaigns.
- **task_queue → prospect:** N:1. Message/monitor tasks scoped to one prospect.
- **agent_runs → task_queue:** 1:1. Each run corresponds to one task.

---

## 5. PostgreSQL Migration Path

### Step 1: Install psycopg2
```bash
uv pip install psycopg2-binary alembic
```

### Step 2: Update environment variable
```bash
# .env
DATABASE_URL=postgresql://eworks:password@localhost:5432/eworks_os
# was: DATABASE_URL=sqlite:///./eworks.db
```

### Step 3: SQLAlchemy dialect differences to handle

| SQLite | PostgreSQL | Notes |
|--------|-----------|-------|
| `INTEGER AUTOINCREMENT` | `SERIAL` / `BIGSERIAL` | SQLAlchemy `Integer` + `autoincrement=True` handles this |
| `BOOLEAN` stored as 0/1 | Native `BOOLEAN` | SQLAlchemy `Boolean` type handles this |
| `DATETIME` text | `TIMESTAMP WITH TIME ZONE` | Use `TIMESTAMP(timezone=True)` |
| `PRAGMA` statements | N/A | Remove in PostgreSQL |
| WAL mode | N/A | PostgreSQL has its own WAL |
| `BEGIN IMMEDIATE` | `SELECT ... FOR UPDATE SKIP LOCKED` | Task queue claim query needs update |
| JSON stored as TEXT | Native `JSONB` | Change `Text` → `JSONB` column type for performance |

### Step 4: Task queue claim query update
```python
# SQLite version
"BEGIN IMMEDIATE; SELECT ... WHERE status='pending' ... LIMIT 1"

# PostgreSQL version  
"SELECT ... WHERE status='pending' ... FOR UPDATE SKIP LOCKED LIMIT 1"
```

### Step 5: Generate and run Alembic migration
```bash
alembic init alembic
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

### Step 6: Add PostgreSQL-specific optimisations
```sql
-- After migration
CREATE INDEX CONCURRENTLY idx_prospects_full_text 
    ON prospects USING gin(to_tsvector('english', coalesce(first_name,'') || ' ' || coalesce(last_name,'') || ' ' || coalesce(current_company,'')));

-- Partial index for task queue hot path
CREATE INDEX idx_tasks_pending 
    ON task_queue(priority, scheduled_for) 
    WHERE status = 'pending';
```
