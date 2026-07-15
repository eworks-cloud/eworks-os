# STORY-11.1 — Project Scaffold

**Epic:** 11 — Operator Console
**Status:** Ready
**Points:** 3

## Summary
Initialize the Next.js/TypeScript operator console app skeleton under `web/`, with config-driven `eworks.db` path resolution and access-token scaffolding, following the active `nextjs-react` tech preset.

## Acceptance Criteria
- [ ] `web/package.json`, `web/tsconfig.json`, `web/next.config.ts` created with Next.js 16+ App Router, TypeScript, Tailwind (active `nextjs-react` preset) (CON-1104 — no fork of FounderOS-DEMO, reference shape only)
- [ ] `web/.env.example` documents `EWORKS_DB_PATH` (default `data/eworks.db`) and `OPERATOR_CONSOLE_ACCESS_TOKEN` with no hardcoded absolute paths (FR-1105, NFR-1107)
- [ ] `web/lib/config.ts` resolves the DB path + access token from env/config at startup, failing loudly if `EWORKS_DB_PATH` is unset, with no fallback to a hardcoded path (FR-1105)
- [ ] `web/README.md` documents the single documented start command (e.g. `npm run dev` / `npm run build && npm start`) to run the console alongside the existing Python agents without changing their deployment (NFR-1108)
- [ ] `web/README.md` records that the console introduces no new backend services beyond, at most, one thin read API co-located with the app — no new datastore/broker introduced (CON-1103, NFR-1103)
- [ ] `web/app/layout.tsx` root layout stub created (empty shell, no data yet) as the foundation for Story 11.3's navigation shell

## Dependencies
- DEP-1109 (Next.js/TypeScript toolchain), DEP-1110 (local access token/config)

## Validation
- **Score:** 9/10
- **Verdict:** GO
- **Rationale:** Clear scaffold scope with crisp file-path ACs, config-driven path resolution traced to FR-1105/NFR-1107/NFR-1108, deps mapped, and points estimated; only per-story risk notes are absent (covered by epic §11).
- **Validator:** @po (Pax)
- **Date:** 2026-07-15
