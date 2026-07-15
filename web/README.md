# Eworks Operator Console

Read-only Next.js dashboard over `eworks.db`. Lets Cesar see how the seven
Eworks OS agents are doing without scrolling through Telegram.

## Prerequisites

- Node.js 20+
- A running Eworks OS install with `data/eworks.db` present (the same
  database the Python agents read and write)

## Setup

```bash
cd web
cp .env.example .env.local
# edit .env.local: set EWORKS_DB_PATH and OPERATOR_CONSOLE_ACCESS_TOKEN
npm install
```

## Running

**Single documented start command** — pick one, both run the console
alongside the existing Python agents without changing their deployment:

```bash
npm run dev              # local development, http://localhost:3000
```

```bash
npm run build && npm start   # production build
```

The console is a separate Node.js process from the Python agents. Starting
or stopping it has no effect on `closer`, `conductor`, `treasurer`,
`nurturer`, or any other agent process — they keep running independently.

## Architecture notes

- No new backend services are introduced by this app beyond, at most, one
  thin read API co-located with the Next.js app itself (a Route Handler
  reading `eworks.db`). No new datastore, queue, or broker is introduced.
- All database access is read-only against the same `eworks.db` SQLite file
  the agents use (WAL mode) — the console never writes to it.
- `lib/config.ts` resolves `EWORKS_DB_PATH` and
  `OPERATOR_CONSOLE_ACCESS_TOKEN` from the environment at startup and fails
  loudly if either is unset; there is no hardcoded fallback path.

## Testing

```bash
npm test
```
