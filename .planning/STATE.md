---
gsd_state_version: 1.0
milestone: v1.7
milestone_name: Consolidation, Tooling & Refactoring
status: verifying
last_updated: "2026-04-03T00:00:00.000Z"
last_activity: 2026-04-03
progress:
  total_phases: 9
  completed_phases: 2
  total_plans: 6
  completed_plans: 6
  percent: 100
---

# Project State: FlawChess

## Current Position

Phase: 41.1
Plan: Not started
Status: Phase complete — ready for verification
Last activity: 2026-04-02

Progress: [██████████] 100%

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)
Core value: Users can determine their success rate for any opening position they specify
Current focus: v1.7 Consolidation, Tooling & Refactoring

## Key Context

- Stack: FastAPI + React/TS/Vite + PostgreSQL + python-chess
- ORM: SQLAlchemy 2.x async + Alembic
- Auth: FastAPI-Users 15.0.4 (JWT, integer user IDs)
- Core algorithm: Zobrist hashes (white_hash, black_hash, full_hash) precomputed at import
- Deployment: Docker Compose on Hetzner CX32 (2 vCPUs, 3.7 GB RAM + 2 GB swap)

## Accumulated Context

### Pending Todos

- **Human-like engine analysis** (general) — v2+ engine eval filtered by human move plausibility at target Elo
- **Bitboard storage for partial-position queries** (database) — 12 BIGINT bitboard columns on game_positions

### Roadmap Evolution

- Phase 41.1 inserted after Phase 41: Import Speed Optimization (URGENT)

### Blockers/Concerns

- Backfill batch_size MUST be 10 games (~400 rows) per commit — prior OOM at batch_size=50 (production incident)
- bulk_insert_positions chunk_size tuning required when adding columns — asyncpg 32767 arg limit

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260402-psb | Fix frontend cache-busting so deployed updates reach users without manual refresh | 2026-04-02 | 85e7657 | [260402-psb-fix-frontend-cache-busting-so-deployed-u](./quick/260402-psb-fix-frontend-cache-busting-so-deployed-u/) |
| 260402-qms | Document Sentry access in CLAUDE.md and add error fingerprinting hooks for DB and HTTP errors | 2026-04-02 | d3bbe5f | [260402-qms-document-sentry-access-in-claude-md-and-](./quick/260402-qms-document-sentry-access-in-claude-md-and-/) |
| 260403-c83 | Rename /api/analysis to /api/openings for consistency with /api/endgames | 2026-04-03 | 52851c0 | [260403-c83-rename-api-analysis-to-api-openings-for-](./quick/260403-c83-rename-api-analysis-to-api-openings-for-/) |
| 260403-ci9 | Full rename of analysis modules to openings — files, imports, comments, variables, parameters | 2026-04-03 | c81612d | [260403-ci9-full-rename-of-analysis-modules-to-openi](./quick/260403-ci9-full-rename-of-analysis-modules-to-openi/) |

### Decisions Made (Phase 40)

- **Row[Any] return types in repositories** — Service layer will adopt TypedDicts/named tuples in Plan 02
- **isinstance(PositionBookmark) over hasattr()** — Type-safe ORM detection in model_validator
- **ty: ignore suppressions for FastAPI-Users** — Generic typing not resolved by ty beta; D-07 decision
- **cast() for API dict values to Literal types** — Narrow values from external API dicts without runtime overhead
- **NormalizedGame model_dump() in _flush_batch** — isinstance check maintains dict compat for test mocks

### Decisions Made (Phase 41, Plan 01)

- **Minimal knip.json config** — Vite/Vitest plugins auto-activate from devDependencies; no explicit plugin config needed
- **CI step ordering: eslint -> build -> test -> knip** — type errors caught before test failures, dead code last
- **Knip exit 1 acceptable during Plan 01** — existing dead code will be cleaned up in Plan 03; CI gate enforces no new dead code after cleanup

### Decisions Made (Phase 41, Plan 02)

- **Router prefix= in APIRouter() constructor** — Not duplicated in each route path decorator; consistent with imports.py and users.py pattern
- **/games/count moved to users router** — It is a user account stat, not an analysis result; accessible at /api/users/games/count
- **apply_game_filters uses Any for stmt parameter** — Matches existing repository pattern; avoids ty errors with SQLAlchemy Select generics

### Decisions Made (Phase 41, Plan 03)

- **Delete entire dead files vs. just removing exports** — Dashboard.tsx and its exclusive dependencies (ImportModal, ImportProgress, GameTable, WDLBar) deleted; table.tsx and tooltip.tsx also deleted
- **ignoreDependencies for CSS-imported packages** — clsx, tailwind-merge, shadcn, tw-animate-css, tailwindcss-safe-area added to knip.json ignoreDependencies; knip doesn't scan CSS files
- **Add @dnd-kit/core and @dnd-kit/utilities as direct deps** — Were being imported directly but only listed as transitive deps of @dnd-kit/sortable

### Decisions Made (Phase 41, Plan 04)

- **flatMap over filter+map for Record access narrowing in Openings.tsx** — TypeScript cannot narrow computed property access through separate filter/map chain; flatMap combines both into a single pass
- **Non-null assertion ! preferred over as T cast** — Narrower and more explicit about safety invariant; used only when index is provably in bounds
- **Remove unused local functions after Plan 03 export removals** — With noUnusedLocals: true, functions that lost their exports (CardAction, ChartTooltipContent, etc.) become TS6133 errors; removing them is correct

---
Last activity: 2026-04-03 - Completed quick/260403-ci9: Full rename of analysis modules to openings (all internal identifiers aligned)
