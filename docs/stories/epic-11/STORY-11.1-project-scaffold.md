# STORY-11.1 — Project Scaffold

**Epic:** 11 — Operator Console
**Status:** Done
**Points:** 3

## Summary
Initialize the Next.js/TypeScript operator console app skeleton under `web/`, with config-driven `eworks.db` path resolution and access-token scaffolding, following the active `nextjs-react` tech preset.

## Acceptance Criteria
- [x] `web/package.json`, `web/tsconfig.json`, `web/next.config.ts` created with Next.js 16+ App Router, TypeScript, Tailwind (active `nextjs-react` preset) (CON-1104 — no fork of FounderOS-DEMO, reference shape only)
- [x] `web/.env.example` documents `EWORKS_DB_PATH` (default `data/eworks.db`) and `OPERATOR_CONSOLE_ACCESS_TOKEN` with no hardcoded absolute paths (FR-1105, NFR-1107)
- [x] `web/lib/config.ts` resolves the DB path + access token from env/config at startup, failing loudly if `EWORKS_DB_PATH` is unset, with no fallback to a hardcoded path (FR-1105)
- [x] `web/README.md` documents the single documented start command (e.g. `npm run dev` / `npm run build && npm start`) to run the console alongside the existing Python agents without changing their deployment (NFR-1108)
- [x] `web/README.md` records that the console introduces no new backend services beyond, at most, one thin read API co-located with the app — no new datastore/broker introduced (CON-1103, NFR-1103)
- [x] `web/app/layout.tsx` root layout stub created (empty shell, no data yet) as the foundation for Story 11.3's navigation shell

## Dependencies
- DEP-1109 (Next.js/TypeScript toolchain), DEP-1110 (local access token/config)

## Validation
- **Score:** 9/10
- **Verdict:** GO
- **Rationale:** Clear scaffold scope with crisp file-path ACs, config-driven path resolution traced to FR-1105/NFR-1107/NFR-1108, deps mapped, and points estimated; only per-story risk notes are absent (covered by epic §11).
- **Validator:** @po (Pax)
- **Date:** 2026-07-15

## Dev Agent Record

### Agent Model Used
claude-sonnet-5 (aiox-dev fallback: general-purpose execution of `.claude/agents/aiox-dev.md` + `.aiox-core/development/tasks/dev-develop-story.md`, YOLO mode)

### Completion Notes
- Scaffolded `web/` as a standalone Next.js 16 (App Router, Turbopack) + TypeScript + Tailwind app; no fork of FounderOS-DEMO, reference shape only (CON-1104).
- `web/lib/config.ts` throws a descriptive `MissingConfigError` for either `EWORKS_DB_PATH` or `OPERATOR_CONSOLE_ACCESS_TOKEN` when unset — no hardcoded fallback path; covered by `web/tests/config.test.ts` (4 tests).
- `web/README.md` documents `npm run dev` and `npm run build && npm start` as the single documented start path, and records the no-new-backend-services / no-new-datastore constraint (CON-1103, NFR-1103).
- `web/app/layout.tsx` is an empty shell (no data fetching, no nav) — foundation for Story 11.3.
- ESLint: `eslint-config-next`'s legacy shareable config crashes under `@eslint/eslintrc`'s `FlatCompat` with ESLint 9.x/typescript-eslint 8.x (`TypeError: Converting circular structure to JSON` in `config-validator.js`, reproduced with both eslint@9.17 and eslint@8.57, and after pinning `eslint-plugin-react` down — the crash persists across `next/core-web-vitals` and `next/typescript`). Worked around by writing `web/eslint.config.mjs` as a native flat config using `@next/eslint-plugin-next`'s built-in `configs['core-web-vitals']` and `typescript-eslint`'s flat `configs.recommended` directly, bypassing `eslint-config-next`'s legacy wrapper entirely. `eslint-config-next` was dropped from `devDependencies` since it's unused.
- Verified locally: `npm run lint`, `npm run typecheck`, `npm test` (4/4 passing), `npm run build` all green in `web/`; full Python regression suite (`pytest tests/`, 229 tests) still passes unaffected.

### File List
- `web/package.json` (created)
- `web/package-lock.json` (created)
- `web/tsconfig.json` (created)
- `web/next.config.ts` (created)
- `web/.env.example` (created)
- `web/.gitignore` (created)
- `web/eslint.config.mjs` (created)
- `web/postcss.config.mjs` (created)
- `web/tailwind.config.ts` (created)
- `web/lib/config.ts` (created)
- `web/app/layout.tsx` (created)
- `web/app/globals.css` (created)
- `web/README.md` (created)
- `web/vitest.config.ts` (created)
- `web/tests/config.test.ts` (created)

## QA Results

### Review Date: 2026-07-15

### Reviewed By: Quinn (Test Architect)

All 6 acceptance criteria verified directly against the implementation in `web/`:
- Next.js 16 App Router + TypeScript + Tailwind scaffold present (`package.json`, `tsconfig.json`, `next.config.ts`, `tailwind.config.ts`), no fork of FounderOS-DEMO (CON-1104).
- `.env.example` documents `EWORKS_DB_PATH` (default `data/eworks.db`) and `OPERATOR_CONSOLE_ACCESS_TOKEN`, no hardcoded absolute paths (FR-1105, NFR-1107).
- `lib/config.ts` throws `MissingConfigError` for either unset var, no hardcoded fallback path (FR-1105); covered by 4/4 passing tests in `tests/config.test.ts`, including explicit "does not fall back to a hardcoded path" coverage.
- `README.md` documents a single start path (`npm run dev` / `npm run build && npm start`) and records no new backend services beyond a co-located thin read API, no new datastore (NFR-1108, CON-1103, NFR-1103).
- `app/layout.tsx` is an empty shell (no data fetching, no nav) — correct foundation for Story 11.3.

Independently re-ran verification in `web/`: `npm run lint` (clean), `npm run typecheck` (clean), `npm test` (4/4 passing), `npm run build` (succeeds). Also re-ran the full Python regression suite (`pytest tests/`, 229/229 passing) to confirm the new `web/` scaffold introduces no regressions to the existing agents. No security issues (no hardcoded secrets, `.env*` correctly gitignored). No high-severity issues found.

### Gate Status

Gate: PASS → docs/qa/gates/11.1-project-scaffold.yml

## Change Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-07-15 | 0.1.0 | Development started (YOLO mode) — Status: Ready → InProgress | @dev |
| 2026-07-15 | 0.1.0 | Development complete — Status: InProgress → InReview | @dev |
| 2026-07-15 | 0.1.1 | QA Gate PASS — Status: InReview → Done | @qa |
