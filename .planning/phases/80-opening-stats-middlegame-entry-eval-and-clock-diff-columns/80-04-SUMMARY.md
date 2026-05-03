---
phase: 80-opening-stats-middlegame-entry-eval-and-clock-diff-columns
plan: "04"
subsystem: frontend
tags: [frontend, layout, constants, calibration, tdd]
dependency_graph:
  requires: []
  provides:
    - openingStatsZones.ts (EVAL_NEUTRAL_MIN/MAX_PAWNS, EVAL_BULLET_DOMAIN_PAWNS, EVAL_ENDGAME_NEUTRAL_MIN/MAX_PAWNS, EVAL_ENDGAME_BULLET_DOMAIN_PAWNS)
    - openingsBoardLayout.ts (getBoardContainerClassName)
    - Openings.tsx board container hidden on Stats subtab desktop (lg:hidden)
  affects:
    - frontend/src/pages/Openings.tsx
tech_stack:
  added: []
  patterns:
    - Helper extraction to separate lib module to satisfy react-refresh/only-export-components ESLint rule
key_files:
  created:
    - frontend/src/lib/openingStatsZones.ts
    - frontend/src/lib/openingsBoardLayout.ts
    - frontend/src/lib/__tests__/openingStatsZones.test.ts
    - frontend/src/pages/__tests__/Openings.statsBoard.test.tsx
  modified:
    - frontend/src/pages/Openings.tsx (import + board container className + data-testid)
decisions:
  - "Helper getBoardContainerClassName extracted to openingsBoardLayout.ts (not inline in Openings.tsx) due to react-refresh/only-export-components ESLint rule"
  - "Test approach uses helper unit test (escape hatch per plan) rather than full-page render — full render would require mocking 15+ hooks"
  - "openingStatsZones.ts constants use float notation (0.20 not +0.20) per plan note on TypeScript literal syntax"
metrics:
  duration: "~8 minutes"
  completed: "2026-05-03T18:15:38Z"
  tasks_completed: 2
  files_changed: 5
---

# Phase 80 Plan 04: Zone calibration constants + board hide on Stats subtab Summary

Two independent frontend deliverables: (1) bullet-chart zone calibration constants for MG and EG eval pillars; (2) desktop board hidden on Stats subtab via CSS-only `lg:hidden` to free horizontal space.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | openingStatsZones.ts constants module (MG + EG pillars) + 11 unit tests | 8cc4f49 | openingStatsZones.ts, openingStatsZones.test.ts |
| 2 | Hide chess board container on Stats subtab desktop + 5 tests | 523161d | openingsBoardLayout.ts, Openings.tsx, Openings.statsBoard.test.tsx |

## Files Created / Modified

### Created

- `frontend/src/lib/openingStatsZones.ts` — Six named exports: `EVAL_NEUTRAL_MIN_PAWNS = -0.20`, `EVAL_NEUTRAL_MAX_PAWNS = 0.20`, `EVAL_BULLET_DOMAIN_PAWNS = 1.5` (MG-entry D-07); `EVAL_ENDGAME_NEUTRAL_MIN_PAWNS = -0.35`, `EVAL_ENDGAME_NEUTRAL_MAX_PAWNS = 0.35`, `EVAL_ENDGAME_BULLET_DOMAIN_PAWNS = 3.5` (EG-entry D-09). Header comment cites `reports/benchmarks-2026-05-03.md §3` with Cohen's d collapse verdicts.
- `frontend/src/lib/openingsBoardLayout.ts` — `getBoardContainerClassName(activeTab)` returns `flex flex-col gap-2 w-[400px] shrink-0` + ` lg:hidden` when `activeTab === 'stats'`.
- `frontend/src/lib/__tests__/openingStatsZones.test.ts` — 11 unit tests (5 MG + 5 EG + 1 cross-phase).
- `frontend/src/pages/__tests__/Openings.statsBoard.test.tsx` — 5 unit tests for `getBoardContainerClassName`.

### Modified

- `frontend/src/pages/Openings.tsx`:
  - Line 64: added `import { getBoardContainerClassName } from '@/lib/openingsBoardLayout';`
  - Line 1278: board container `<div>` className changed from static string to `{getBoardContainerClassName(activeTab)}`, and `data-testid="openings-board-container"` added.
  - `<ChessBoard>` JSX element NOT removed (chess.js state preserved, Pitfall 7).

## Conditional Class Location

File: `frontend/src/lib/openingsBoardLayout.ts`, line 17:
```ts
return `flex flex-col gap-2 w-[400px] shrink-0${activeTab === 'stats' ? ' lg:hidden' : ''}`;
```

Applied in `Openings.tsx` line 1278 via `className={getBoardContainerClassName(activeTab)}`.

## Named Constants Exported

### MG-entry pillar (D-07)
- `EVAL_NEUTRAL_MIN_PAWNS = -0.20`
- `EVAL_NEUTRAL_MAX_PAWNS = 0.20`
- `EVAL_BULLET_DOMAIN_PAWNS = 1.5`

### EG-entry pillar (D-09)
- `EVAL_ENDGAME_NEUTRAL_MIN_PAWNS = -0.35`
- `EVAL_ENDGAME_NEUTRAL_MAX_PAWNS = 0.35`
- `EVAL_ENDGAME_BULLET_DOMAIN_PAWNS = 3.5`

## Test Counts

- Zone calibration (openingStatsZones.test.ts): 11 tests (5 MG + 5 EG + 1 cross-phase)
- Board hide (Openings.statsBoard.test.tsx): 5 tests (stats tab has lg:hidden, explorer/games/insights do not, base classes always present)
- Full suite: 227/227 tests pass

## Mobile Responsiveness

The `lg:hidden` class is Tailwind's responsive prefix -- it applies `display: none` only at the `lg` breakpoint and above. On mobile, the board container (which is already inside the desktop-only layout) is not rendered. The mobile board is in a separate `lg:hidden` section (line 1336) and was already conditionally rendered only on `explorer` and `games` tabs (line 1392) -- unchanged by this plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Extracted helper to separate module due to ESLint react-refresh rule**

- **Found during:** Task 2 lint check
- **Issue:** The plan's primary approach (export `getBoardContainerClassName` from `Openings.tsx`) violated the `react-refresh/only-export-components` ESLint rule. ESLint error: "Fast refresh only works when a file only exports components."
- **Fix:** Extracted `getBoardContainerClassName` to `frontend/src/lib/openingsBoardLayout.ts`. This also aligns with CLAUDE.md "no magic numbers" and single-responsibility principles.
- **Test approach:** Used the plan's documented escape hatch: the helper is unit-tested directly, without full-page render. Full-page render would require mocking 15+ hooks and is not practical here.
- **Files modified:** openingsBoardLayout.ts (new), Openings.tsx (import), Openings.statsBoard.test.tsx (import path)
- **Commits:** 523161d

## Known Stubs

None. Both deliverables are complete and self-contained. The constants module exports values that Plan 05 will import; the board hide logic is immediately active.

## Threat Flags

None. Pure presentational + constants changes. No new I/O, auth surface, or trust boundaries.

## Self-Check: PASSED

- [x] `frontend/src/lib/openingStatsZones.ts` exists
- [x] `frontend/src/lib/openingsBoardLayout.ts` exists
- [x] `frontend/src/lib/__tests__/openingStatsZones.test.ts` exists
- [x] `frontend/src/pages/__tests__/Openings.statsBoard.test.tsx` exists
- [x] Commit 8cc4f49 exists (Task 1)
- [x] Commit 523161d exists (Task 2)
- [x] 227/227 tests pass
- [x] lint, knip, tsc --noEmit all clean
- [x] npm run build succeeds
