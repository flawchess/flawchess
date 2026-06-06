---
phase: 107-games-subtab-frontend-card-archive-filters-flaw-stats-panel
plan: "02"
subsystem: frontend-types-hooks
tags: [library, theme, types, hooks, tanstack-query]
dependency_graph:
  requires: [107-01]
  provides: [theme-SEV-FAM-PHASE-constants, library-ts-types, libraryApi, useLibraryGames, useLibraryFlawStats]
  affects: [frontend/src/lib/theme.ts, frontend/src/types/library.ts, frontend/src/api/client.ts, frontend/src/hooks/useLibrary.ts]
tech_stack:
  added: []
  patterns: [tanstack-query-hooks, buildFilterParams-convention, literal-union-types, record-safe-access]
key_files:
  created:
    - frontend/src/types/library.ts
    - frontend/src/hooks/useLibrary.ts
  modified:
    - frontend/src/lib/theme.ts
    - frontend/src/api/client.ts
decisions:
  - "Wave-1 exports flagged by knip as unused are expected — downstream components (Wave 2+) consume them in the same phase branch before squash-merge to main"
  - "libraryApi passes severity as multi-value param via existing paramsSerializer indexes:null convention (same as time_control/platform arrays)"
  - "buildLibraryParams drops color/matchSide vs buildEndgameParams — Games subtab shows all colors by design"
  - "LIBRARY_STALE_TIME set to 5 minutes matching ENDGAME_STALE_TIME — same cost profile (aggregate queries)"
metrics:
  duration: "480s"
  completed_date: "2026-06-05"
  tasks_completed: 3
  files_changed: 4
---

# Phase 107 Plan 02: Frontend Foundations (Theme + Types + Hooks) Summary

Theme constants, TypeScript types, libraryApi client methods, and TanStack Query hooks serving as the shared leaf-dependency layer consumed by every Phase 107 component.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add severity/tag-family/phase color constants to theme.ts | 9c0bb021 | frontend/src/lib/theme.ts |
| 2 | Add library TypeScript types mirroring backend schemas | b131c8b7 | frontend/src/types/library.ts |
| 3 | Add libraryApi client methods and useLibrary TanStack Query hooks | bfa2495c | frontend/src/api/client.ts, frontend/src/hooks/useLibrary.ts |

## What Was Built

### frontend/src/lib/theme.ts (MODIFIED)

Twenty-seven new named constants added immediately after the `WDL_BORDER_*` block per PATTERNS.md:

- Severity palette: `SEV_BLUNDER` / `SEV_MISTAKE` / `SEV_INACCURACY` (oklch red/amber/yellow)
- Tempo family: `FAM_TEMPO` / `FAM_TEMPO_BG` / `FAM_TEMPO_LOW_CLOCK` / `FAM_TEMPO_IMPATIENT` / `FAM_TEMPO_CONSIDERED` / `FAM_TEMPO_UNMEASURED` (violet family, plus neutral gray for unmeasured remainder)
- Opportunity family: `FAM_OPPORTUNITY` / `FAM_OPPORTUNITY_BG` (cyan)
- Impact family: `FAM_IMPACT` / `FAM_IMPACT_BG` (magenta)
- Phase histogram: `PHASE_OPENING` / `PHASE_MIDDLEGAME` / `PHASE_ENDGAME` (warm/blue/purple)

All values match UI-SPEC §Color exactly. No pre-existing constant duplicated or redefined.

### frontend/src/types/library.ts (CREATED)

Full type mirror of the Phase 106 + D-01 backend contracts:

- `FlawTag` — exact literal union of the 10 final tag strings (post-rename: `low-clock`, `impatient`, `considered`, `miss`, `lucky-escape`, `while-ahead`, `result-changing`, `opening`, `middlegame`, `endgame`)
- `FlawSeverity` — `'inaccuracy' | 'mistake' | 'blunder'`
- `TempoTag` — `'low-clock' | 'impatient' | 'considered'`
- `AnalysisState` — `'analyzed' | 'no_engine_analysis'`
- `SeverityCountsData` — mirrors backend `SeverityCounts` TypedDict
- `GameFlawCard` — full per-game card shape incl. `analysis_state`, nullable `severity_counts`, `chips: FlawTag[]`
- `LibraryGamesResponse` — paginated archive response
- `SeverityRates` — `per_game` / `per_100_moves` keyed by `FlawSeverity`
- `TagDistribution` — `tempo` dict, `result_changing_rate`, `phase_histogram`, plus D-01 fields: `miss_rate`, `lucky_escape_rate`, `while_ahead_rate`
- `FlawTrendPoint` — rolling-window trend datapoint
- `FlawStatsResponse` — full stats panel response

`UserResult` imported from `types/api.ts`, not re-declared. All dict types use `Record<K, V>` (noUncheckedIndexedAccess-safe).

### frontend/src/api/client.ts (MODIFIED)

`libraryApi` object added following the `endgameApi` style:

- `getGames(params)` calls `GET /api/library/games` — passes `severity` as multi-value param using the existing `paramsSerializer: { indexes: null }` convention (same as `time_control` / `platform`)
- `getFlawStats(params)` calls `GET /library/flaw-stats` (never `mistake-stats`)
- Both methods import `LibraryGamesResponse` / `FlawStatsResponse` from `types/library.ts`

### frontend/src/hooks/useLibrary.ts (CREATED)

Two TanStack Query hooks:

- `useLibraryGames(filters, severity, offset, limit)` — key `['library-games', params, offset, limit]`, both offset and limit in key to trigger re-fetch on page changes
- `useLibraryFlawStats(filters, severity)` — key `['library-flaw-stats', params]`, no offset (stats are page-independent)

Shared `buildLibraryParams(filters, severity)` mirrors `buildEndgameParams` minus `color`/`matchSide` (Games subtab shows all colors). `severity` is omitted from params when empty — the API treats missing severity as "no filter". Both hooks use `LIBRARY_STALE_TIME = 5 * 60 * 1000` and `refetchOnWindowFocus: false` matching the endgame precedent.

## Verification

- `cd frontend && npx tsc --noEmit` — 0 errors
- `cd frontend && npm run lint` — 0 issues
- `cd frontend && npm test -- --run` — 744 tests passed (63 test files)
- `grep -c "FAM_OPPORTUNITY|FAM_IMPACT|PHASE_OPENING|SEV_BLUNDER|FAM_TEMPO_UNMEASURED" src/lib/theme.ts` — 7 matches (all required constants present)

## Deviations from Plan

None — plan executed exactly as written.

Note: `npm run knip` reports the new exports as unused. This is expected for Wave 1 foundation work: the downstream components (SeverityBadge, TagChip, FlawStatsPanel, GamesTab, etc.) that consume these exports are built in Wave 2+ plans on the same phase branch. Knip will be clean at the squash-merge point when all 7 plans are complete. CLAUDE.md: "The full-suite gate runs once, right before the squash-merge."

## Known Stubs

None. All types fully mirror the backend contract including D-01 fields. The hooks call real API endpoints.

## Threat Flags

None. Pure type/client/hook plumbing over existing authenticated endpoints — no new network surface, no auth change, no `dangerouslySetInnerHTML`, no new dependency.

## Self-Check: PASSED

- `/home/aimfeld/Projects/Python/flawchess/frontend/src/lib/theme.ts` — exists, modified
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/types/library.ts` — exists, created
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/api/client.ts` — exists, modified
- `/home/aimfeld/Projects/Python/flawchess/frontend/src/hooks/useLibrary.ts` — exists, created
- Commit 9c0bb021 — Task 1 (feat: theme.ts constants)
- Commit b131c8b7 — Task 2 (feat: library.ts types)
- Commit bfa2495c — Task 3 (feat: libraryApi + hooks)
