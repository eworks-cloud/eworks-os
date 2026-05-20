     1|# Eworks OS — API & CLI Design
     2|
     3|**Version:** 1.0  
     4|**Author:** Aria (Architect Agent)  
     5|**Date:** 2026-05-19  
     6|**Status:** Approved for MVP
     7|
     8|---
     9|
    10|## 1. CLI Overview
    11|
    12|The CLI is the primary human interface to Eworks OS. It is built with **Typer** and installed as the `eos` command.
    13|
    14|```
    15|eworks [OPTIONS] COMMAND [ARGS]...
    16|
    17|Options:
    18|  --config PATH   Config file path [default: ./config/settings.yaml]
    19|  --db PATH       Database path [default: ./eworks.db]
    20|  --verbose       Enable verbose logging
    21|  --version       Show version and exit
    22|  --help
    23|
    24|Commands:
    25|  auth        Manage LinkedIn authentication
    26|  campaign    Manage prospecting campaigns
    27|  prospect    View and manage prospects
    28|  message     Message management and generation
    29|  agent       Directly run agent tasks
    30|  monitor     View system status and logs
    31|  config      Configuration management
    32|  daemon      Run the background dispatcher
    33|  export      Export data to CSV/JSON
    34|```
    35|
    36|---
    37|
    38|## 2. Command Reference
    39|
    40|### 2.1 `eos auth`
    41|
    42|```
    43|eworks auth COMMAND
    44|
    45|Commands:
    46|  linkedin        Authenticate LinkedIn account(s)
    47|  status          Show current auth status for all accounts
    48|  test            Test that a stored session is valid
    49|```
    50|
    51|#### `eos auth linkedin`
    52|
    53|```
    54|eworks auth linkedin [OPTIONS]
    55|
    56|  Authenticate a LinkedIn account interactively (opens browser).
    57|  Stores session in Playwright persistent context.
    58|
    59|Options:
    60|  --account SLUG   Account slug to create/update [required]
    61|  --email TEXT     LinkedIn email address [required]
    62|  --reauth         Force re-authentication even if session exists
    63|  --headless       Run browser headlessly (default: False for auth)
    64|  --help
    65|```
    66|
    67|**Example:**
    68|```bash
    69|eworks auth linkedin --account cesar_main --email cesar@example.com
    70|# Opens Chromium, user logs in manually
    71|# Session saved to ~/.eworks/browser/cesar_main/
    72|# ✅ Session stored for cesar_main (expires ~30 days)
    73|```
    74|
    75|#### `eos auth status`
    76|
    77|```
    78|eworks auth status
    79|
    80|Output:
    81|  Account: cesar_main
    82|  Email:   cesar@example.com
    83|  Status:  ✅ active
    84|  Last activity: 2026-05-19 14:32:11
    85|  Daily limits:  search=23/80  messages=8/20  connections=5/20
    86|```
    87|
    88|---
    89|
    90|### 2.2 `eos campaign`
    91|
    92|```
    93|eworks campaign COMMAND
    94|
    95|Commands:
    96|  create     Create a new campaign
    97|  list       List all campaigns
    98|  show       Show campaign details and stats
    99|  pause      Pause a running campaign
   100|  resume     Resume a paused campaign
   101|  archive    Archive a completed campaign
   102|  edit       Edit campaign settings
   103|```
   104|
   105|#### `eos campaign create`
   106|
   107|```
   108|eworks campaign create [OPTIONS]
   109|
   110|Options:
   111|  --name TEXT                 Campaign name [required]
   112|  --search-query TEXT         LinkedIn search keywords [required]
   113|  --persona SLUG              Persona slug to use [required]
   114|  --account SLUG              LinkedIn account slug [default: first active]
   115|  --location TEXT             Location filter (e.g. "San Francisco Bay Area")
   116|  --industry TEXT             Industry filter
   117|  --title-keywords TEXT       Title must contain these keywords (comma-separated)
   118|  --daily-search-limit INT    Max profiles to visit per day [default: 50]
   119|  --daily-message-limit INT   Max messages per day [default: 20]
   120|  --prospect-target INT       Stop after N prospects found
   121|  --message-template TEXT     Optional override template (use quotes)
   122|  --notes TEXT                Operator notes
   123|  --help
   124|```
   125|
   126|**Example:**
   127|```bash
   128|eworks campaign create \
   129|  --name "SaaS CTOs Q3 2026" \
   130|  --search-query "Chief Technology Officer SaaS startup" \
   131|  --persona cesar_intro \
   132|  --location "United States" \
   133|  --title-keywords "CTO,Chief Technology Officer,VP Engineering" \
   134|  --daily-search-limit 40 \
   135|  --daily-message-limit 15 \
   136|  --prospect-target 200
   137|
   138|# Output:
   139|# ✅ Campaign created: SaaS CTOs Q3 2026 (id=3)
   140|# Search will run at ~09:15 AM daily
   141|# Messages will be sent at ~02:10 PM daily
   142|# To start: eworks campaign resume --name "SaaS CTOs Q3 2026"
   143|```
   144|
   145|#### `eos campaign list`
   146|
   147|```
   148|eworks campaign list [OPTIONS]
   149|
   150|Options:
   151|  --status TEXT    Filter by status [active|paused|completed|archived|all]
   152|  --format TEXT    Output format [table|json|csv] [default: table]
   153|  --help
   154|
   155|Output (table):
   156|  ID  Name                    Status   Prospects  Messaged  Replied  Rate
   157|  1   SaaS CTOs Q3 2026      active   87         34        6        17.6%
   158|  2   FinTech Founders        paused   200        140       18       12.9%
   159|```
   160|
   161|#### `eos campaign show`
   162|
   163|```
   164|eworks campaign show --name "SaaS CTOs Q3 2026"
   165|
   166|Output:
   167|  Campaign: SaaS CTOs Q3 2026 (id=3)
   168|  Status:   active
   169|  Account:  cesar_main
   170|
   171|  Search Config:
   172|    Query:   Chief Technology Officer SaaS startup
   173|    Filters: location=United States, title=CTO|VP Engineering
   174|    Daily search limit: 40
   175|    Prospect target:    200
   176|
   177|  Progress:
   178|    Prospects discovered: 87 / 200
   179|    Queued for message:   12
   180|    Messages sent:        34
   181|    Replied:              6  (17.6% reply rate)
   182|    Interested:           2
   183|    Disqualified:         8
   184|
   185|  Recent Activity:
   186|    2026-05-19 14:32  Sent message to Jane Smith (VP Eng @ Acme)
   187|    2026-05-19 09:22  Found 18 new prospects
   188|    2026-05-18 14:28  Reply from Bob Jones (CTO @ Widget Co) — 💬 interested
   189|```
   190|
   191|---
   192|
   193|### 2.3 `eos prospect`
   194|
   195|```
   196|eworks prospect COMMAND
   197|
   198|Commands:
   199|  list         List prospects for a campaign
   200|  show         Show full prospect details
   201|  disqualify   Mark prospect as disqualified
   202|  dnc          Add to do-not-contact list
   203|  tag          Add tags to a prospect
   204|```
   205|
   206|#### `eos prospect list`
   207|
   208|```
   209|eworks prospect list [OPTIONS]
   210|
   211|Options:
   212|  --campaign TEXT   Campaign name or ID [required]
   213|  --status TEXT     Filter by status [default: all]
   214|  --limit INT       Number of results [default: 50]
   215|  --offset INT      Pagination offset [default: 0]
   216|  --format TEXT     [table|json|csv] [default: table]
   217|  --help
   218|
   219|Output:
   220|  ID    Name              Title                  Company           Status
   221|  1021  Jane Smith        VP Engineering         Acme Corp         messaged
   222|  1022  Bob Jones         CTO                    Widget Co         replied
   223|  1023  Alice Lee         Chief Technology Off.  StartupXYZ        queued
   224|```
   225|
   226|#### `eos prospect show`
   227|
   228|```
   229|eworks prospect show --id 1022
   230|
   231|Output:
   232|  Prospect: Bob Jones
   233|  Title:    CTO at Widget Co
   234|  Location: Austin, TX
   235|  LinkedIn: https://linkedin.com/in/bobjones
   236|
   237|  Status: replied ✅
   238|  
   239|  Messages:
   240|    [2026-05-15] connection_note — SENT
   241|      "Hi Bob, I noticed Widget Co is scaling its eng team..."
   242|    [2026-05-17] Reply received:
   243|      "Thanks! Happy to chat. When works for you?"
   244|    
   245|  Tags: saas, seed-stage, austin
   246|```
   247|
   248|#### `eos prospect disqualify`
   249|
   250|```
   251|eworks prospect disqualify --id 1023 --reason "not a decision maker"
   252|# ✅ Prospect Alice Lee marked as disqualified
   253|```
   254|
   255|#### `eos prospect dnc`
   256|
   257|```
   258|eworks prospect dnc --id 1023
   259|# ✅ Alice Lee added to do-not-contact list (permanent)
   260|```
   261|
   262|---
   263|
   264|### 2.4 `eos message`
   265|
   266|```
   267|eworks message COMMAND
   268|
   269|Commands:
   270|  preview      Generate a preview message for a prospect (no send)
   271|  send         Send a message to a specific prospect (manual override)
   272|  list         List messages for a campaign or prospect
   273|  stats        Message statistics
   274|```
   275|
   276|#### `eos message preview`
   277|
   278|```
   279|eworks message preview [OPTIONS]
   280|
   281|Options:
   282|  --prospect-id INT   Prospect ID [required]
   283|  --campaign TEXT     Campaign name [required]
   284|  --type TEXT         [connection_note|direct_message|follow_up] [default: connection_note]
   285|  --help
   286|
   287|Output:
   288|  Generating message for: Bob Jones (CTO @ Widget Co)
   289|  Persona: cesar_intro
   290|  Type: connection_note (max 300 chars)
   291|
   292|  ─────────────────────────────────────
   293|  Hi Bob — I help SaaS CTOs reduce
   294|  infrastructure costs by 40% without
   295|  a rewrite. Thought it might be
   296|  worth a quick chat. Open to connect?
   297|  ─────────────────────────────────────
   298|  Length: 167 chars ✅
   299|  Tokens used: 312 (prompt) + 48 (completion)
   300|  
   301|  [P]review another  [S]end this  [E]dit  [Q]uit
   302|```
   303|
   304|#### `eos message stats`
   305|
   306|```
   307|eworks message stats [OPTIONS]
   308|
   309|Options:
   310|  --campaign TEXT   Campaign name (omit for global stats)
   311|  --days INT        Lookback period [default: 30]
   312|  --help
   313|
   314|Output:
   315|  Message Statistics (last 30 days)
   316|  Campaign: SaaS CTOs Q3 2026
   317|
   318|  Sent:           34
   319|  Delivered:      34  (100%)
   320|  Failed:         0
   321|  Replies:        6   (17.6%)
   322|  Interested:     2   (5.9%)
   323|  Avg tokens/msg: 287
   324|
   325|  By type:
   326|    connection_note: 28 sent, 5 replied (17.9%)
   327|    direct_message:  6 sent,  1 replied (16.7%)
   328|```
   329|
   330|---
   331|
   332|### 2.5 `eos agent`
   333|
   334|```
   335|eworks agent COMMAND
   336|
   337|Commands:
   338|  run       Run an agent task immediately
   339|  status    Show running agents
   340|  history   Show agent run history
   341|```
   342|
   343|#### `eos agent run`
   344|
   345|```
   346|eworks agent run [OPTIONS]
   347|
   348|Options:
   349|  --type TEXT       Agent type [search|message|monitor] [required]
   350|  --campaign TEXT   Campaign name
   351|  --prospect-id INT Prospect ID (for message type)
   352|  --dry-run         Simulate without sending/saving
   353|  --headless BOOL   Run browser headlessly [default: True]
   354|  --help
   355|```
   356|
   357|**Example:**
   358|```bash
   359|# Run search immediately for a campaign
   360|eworks agent run --type search --campaign "SaaS CTOs Q3 2026"
   361|
   362|# Output (streaming):
   363|# 🤖 LinkedInSearchAgent starting...
   364|# 📋 Campaign: SaaS CTOs Q3 2026
   365|# 🌐 Loading browser session (cesar_main)
   366|# 🔍 Searching: "Chief Technology Officer SaaS startup"
   367|# ─ Page 1: found 10 profiles
   368|# ─ Page 2: found 10 profiles  
   369|# ─ Page 3: found 8 profiles (3 already known, 5 new)
   370|# ─ Page 4: rate limit pause (22s)...
   371|# ─ Page 5: found 9 profiles
   372|# ✅ Run complete: 37 profiles visited, 22 new prospects added
   373|# ⏱  Duration: 4m 12s
   374|# 📱 Telegram notification sent
   375|```
   376|
   377|#### `eos agent history`
   378|
   379|```
   380|eworks agent history [OPTIONS]
   381|
   382|Options:
   383|  --type TEXT     Filter by agent type
   384|  --days INT      Lookback [default: 7]
   385|  --limit INT     Max results [default: 20]
   386|  --format TEXT   [table|json] [default: table]
   387|
   388|Output:
   389|  Run ID        Agent               Status     Duration  Prospects  Messages
   390|  f3a1b2...     LinkedInSearchAgent completed  4m12s     22         —
   391|  9c2d11...     LinkedInMessenger   completed  8m44s     —          15
   392|  7e4f33...     LinkedInMonitor     completed  2m01s     —          —
   393|  2b9a12...     LinkedInMessenger   failed     0m12s     —          —
   394|    └─ Error: Browser session requires verification
   395|```
   396|
   397|---
   398|
   399|### 2.6 `eos monitor`
   400|
   401|```
   402|eworks monitor COMMAND
   403|
   404|Commands:
   405|  status    Show system health and queue depth
   406|  logs      Tail agent logs
   407|  queue     Show task queue
   408|```
   409|
   410|#### `eos monitor status`
   411|
   412|```
   413|eworks monitor status
   414|
   415|Eworks OS — System Status
   416|─────────────────────────────────────────────
   417|Daemon:          ✅ running (pid 12345)
   418|Database:        ✅ healthy (eworks.db — 4.2 MB)
   419|Scheduler:       ✅ 3 jobs active
   420|
   421|LinkedIn Accounts:
   422|  cesar_main:    ✅ active
   423|    Today:       search=23/80  messages=8/20  connections=3/20
   424|    Next run:    14:12 (message tasks)
   425|
   426|Task Queue:
   427|  pending:   5
   428|  running:   1
   429|  done:      84 (today)
   430|  failed:    1
   431|
   432|Campaigns:
   433|  active:    2
   434|  paused:    1
   435|```
   436|
   437|#### `eos monitor queue`
   438|
   439|```
   440|eworks monitor queue [OPTIONS]
   441|
   442|Options:
   443|  --status TEXT   [pending|running|done|failed|all] [default: pending]
   444|  --limit INT     [default: 20]
   445|
   446|Output:
   447|  ID    Type       Status   Priority  Campaign            Scheduled
   448|  101   message    pending  5         SaaS CTOs Q3 2026   14:10:00
   449|  102   message    pending  5         SaaS CTOs Q3 2026   14:10:00
   450|  103   monitor    pending  3         —                   16:00:00
   451|```
   452|
   453|---
   454|
   455|### 2.7 `eos config`
   456|
   457|```
   458|eworks config COMMAND
   459|
   460|Commands:
   461|  show        Show current configuration
   462|  set         Set a configuration value
   463|  persona     Manage AI personas
   464|  validate    Validate config files
   465|```
   466|
   467|#### `eos config persona create`
   468|
   469|```
   470|eworks config persona create [OPTIONS]
   471|
   472|Options:
   473|  --slug TEXT              Unique slug [required]
   474|  --name TEXT              Display name [required]
   475|  --sender-name TEXT       Name in messages [required]
   476|  --sender-title TEXT      Title in messages [required]
   477|  --sender-company TEXT    Company [required]
   478|  --value-prop TEXT        Core value proposition [required]
   479|  --tone TEXT              [professional|casual|direct] [default: professional]
   480|  --system-prompt-file PATH  Path to .txt file with full system prompt
   481|  --help
   482|```
   483|
   484|---
   485|
   486|### 2.8 `eos daemon`
   487|
   488|```
   489|eworks daemon [OPTIONS]
   490|
   491|  Start the background dispatcher and scheduler.
   492|  Intended for use as a systemd service.
   493|
   494|Options:
   495|  --workers INT    Number of concurrent task workers [default: 1]
   496|  --poll-interval INT  Queue poll interval in seconds [default: 30]
   497|  --no-scheduler   Disable APScheduler (manual task dispatch only)
   498|  --help
   499|
   500|Output:
   501|