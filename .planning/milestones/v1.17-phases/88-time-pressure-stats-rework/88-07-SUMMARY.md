---
phase: 88-time-pressure-stats-rework
plan: "07"
subsystem: frontend
tags:
  - react
  - typescript
  - time-pressure
  - endgames
  - vitest
  - cleanup
dependency_graph:
  requires:
    - 88-06  # EndgameTimePressureCard component + TimePressureCardsResponse types
  provides:
    - EndgameTimePressureSection (new card-grid orchestrator, replaces legacy line-chart)
    - Vitest suite for EndgameTimePressureSection (5 tests)
    - Endgames.tsx wired to time_pressure_cards
  affects:
    - frontend/src/pages/Endgames.tsx (clock_pressure + time_pressure_chart removed)
    - frontend/src/types/endgames.ts (ClockStatsRow + ClockPressureTimelinePoint removed)
    - frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx (stale mock removed)
    - app/services/endgame_service.py (orphaned imports removed)
    - tests/services/test_insights_service_series.py (dead fixture code removed)
    - tests/services/test_score_confidence.py (pre-existing unused import removed)
tech_stack:
  added: []
  patterns:
    - Section orchestrator pattern (mirrors EndgameTypeBreakdownSection): section wrapper + sub-question copy + responsive grid
    - xl:grid-cols-4 / lg:grid-cols-2 / grid-cols-1 responsive breakpoint layout
    - Empty-state with data-testid guard (time-pressure-cards-empty)
key_files:
  created:
    - frontend/src/components/charts/__tests__/EndgameTimePressureSection.test.tsx
  modified:
    - frontend/src/components/charts/EndgameTimePressureSection.tsx
    - frontend/src/pages/Endgames.tsx
    - frontend/src/types/endgames.ts
    - frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx
    - app/services/endgame_service.py
    - tests/services/test_insights_service_series.py
    - tests/services/test_score_confidence.py
  deleted:
    - frontend/src/components/charts/EndgameClockPressureSection.tsx
decisions:
  - "Removed JSX.Element explicit return type: project tsconfig lacks jsx namespace, implicit return inferred correctly"
  - "Created node_modules symlink in worktree frontend/ (same as Plan 06) to enable vitest run"
  - "Removed ClockStatsRow and ClockPressureTimelinePoint from endgames.ts: knip flagged them as unused after section deletion"
  - "Cleaned up orphaned backend imports in endgame_service.py and test fixtures: ruff flagged them as blocking the suite gate"
metrics:
  duration: "~30 minutes"
  completed_date: "2026-05-17"
  tasks_completed: 3
  tasks_total: 3
  files_created: 1
  files_modified: 7
  files_deleted: 1
---

# Phase 88 Plan 07: EndgameTimePressureSection Orchestrator Summary

Section orchestrator replacing two legacy sections with a responsive 4-TC card grid, plus full suite verification.

## What Was Built

**`frontend/src/components/charts/EndgameTimePressureSection.tsx`** (fully rewritten) -- new section orchestrator consuming `TimePressureCardsResponse` and rendering a responsive grid:
- `xl:grid-cols-4` (4 columns on extra-large screens)
- `lg:grid-cols-2` (2 columns on large screens)
- `grid-cols-1` (single column on mobile)
- Maps `data.cards` to `<EndgameTimePressureCard key={card.tc} card={card} />`
- Empty state: `data-testid="time-pressure-cards-empty"` when `cards.length === 0`
- Section wrapper: `data-testid="time-pressure-cards-section"` + `aria-labelledby="time-pressure-heading"`
- Sub-question copy: "How does your score change as your clock runs down?"

**`frontend/src/components/charts/__tests__/EndgameTimePressureSection.test.tsx`** (created) -- 5 Vitest tests:
1. Renders only the TC cards present in the payload (bullet + rapid, omits blitz + classical)
2. Renders empty-state when `cards` is empty
3. Renders all 4 TC cards when full payload supplied
4. Asserts legacy `data-testid="clock-pressure-section"` is absent (knip-clean proxy)
5. Section wrapper testid always present

**`frontend/src/pages/Endgames.tsx`** (updated):
- Removed `EndgameClockPressureSection` and `ClockDiffTimelineChart` imports
- Replaced `clockPressureData` + `timePressureChartData` with `timePressureCardsData`
- Replaced `showClockPressure` + `showTimePressureChart` with `showTimePressureCards`
- Single `<EndgameTimePressureSection data={timePressureCardsData} />` replaces the two legacy mounts

**`frontend/src/components/charts/EndgameClockPressureSection.tsx`** (deleted via `git rm`)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 0348e642 | feat(88-07): rewrite EndgameTimePressureSection as card-grid orchestrator |
| 2 | 619a4a00 | test(88-07): add Vitest suite for EndgameTimePressureSection |
| 3 | 5706ed09 | feat(88-07): wire Endgames.tsx to new section, delete EndgameClockPressureSection, full suite green |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed explicit JSX.Element return type**
- **Found during:** Task 1 tsc verification
- **Issue:** `): JSX.Element` caused `TS2503: Cannot find namespace 'JSX'` -- project tsconfig does not expose the global JSX namespace
- **Fix:** Removed explicit return type; TypeScript infers it correctly as `JSX.Element` from the returned JSX
- **Files modified:** `frontend/src/components/charts/EndgameTimePressureSection.tsx`
- **Commit:** 0348e642

**2. [Rule 3 - Blocking] Knip failure: ClockStatsRow + ClockPressureTimelinePoint unused exports**
- **Found during:** Task 3 knip check
- **Issue:** After deleting `EndgameClockPressureSection.tsx`, two types in `endgames.ts` had no remaining consumers
- **Fix:** Removed `ClockStatsRow` and `ClockPressureTimelinePoint` interfaces from `endgames.ts`
- **Files modified:** `frontend/src/types/endgames.ts`
- **Commit:** 5706ed09

**3. [Rule 3 - Blocking] ruff failure: orphaned imports in backend files**
- **Found during:** Task 3 ruff check
- **Issue:** `endgame_service.py` still imported `ClockPressureResponse`, `ClockPressureTimelinePoint`, `ClockStatsRow`, `TimePressureBucketPoint`, `TimePressureChartResponse` (removed from the active codebase in Phase 88 Plans 04-06). `test_insights_service_series.py` had dead `clock_pressure` and `time_pressure_chart` fixture variables. `test_score_confidence.py` had a pre-existing unused `CONFIDENCE_MIN_N` import.
- **Fix:** Removed all orphaned imports and dead fixture variables
- **Files modified:** `app/services/endgame_service.py`, `tests/services/test_insights_service_series.py`, `tests/services/test_score_confidence.py`
- **Commit:** 5706ed09

**4. [Rule 3 - Infrastructure] node_modules symlink in worktree**
- **Found during:** Task 2 vitest run
- **Issue:** Worktree `frontend/` has no `node_modules` (worktrees share git history but not symlinks)
- **Fix:** `ln -s /home/aimfeld/Projects/Python/flawchess/frontend/node_modules frontend/node_modules` (same fix as Plan 06; not tracked in git)
- **Commit:** N/A (infrastructure only)

### Out-of-Scope Pre-existing Issue

**ruff format --check .** reports 51 files would be reformatted, all in alembic migrations and unrelated test files. None of the files modified in Phase 88 Plan 07 are in this list. This is a pre-existing project-wide formatting debt not introduced by this plan. Logged to deferred items; not fixed.

## Known Stubs

None. The section orchestrator is fully wired to `overviewData.time_pressure_cards` and delegates all rendering to `EndgameTimePressureCard` (built in Plan 06).

## Threat Flags

None. All mitigations from the threat register were applied:
- T-88-07-01: Stale import of deleted section -- resolved by grep assertion + knip + tsc + lint all passing
- T-88-07-02: Empty cards array -- resolved by empty-state UI with `data-testid="time-pressure-cards-empty"` + test coverage
- T-88-07-03: API error path -- resolved by reusing page-level `overviewError` guard in `Endgames.tsx`

## Self-Check: PASSED

- `frontend/src/components/charts/EndgameTimePressureSection.tsx` -- FOUND (rewritten)
- `frontend/src/components/charts/__tests__/EndgameTimePressureSection.test.tsx` -- FOUND (created)
- `frontend/src/pages/Endgames.tsx` -- FOUND (updated)
- `frontend/src/components/charts/EndgameClockPressureSection.tsx` -- DELETED (confirmed)
- Commit 0348e642 -- FOUND
- Commit 619a4a00 -- FOUND
- Commit 5706ed09 -- FOUND
- `npx tsc --noEmit -p tsconfig.app.json` -- exits 0
- `npm run lint` -- exits 0
- `npm run knip` -- exits 0
- `npm test -- --run` -- 490/490 tests pass
- `uv run ty check app/ tests/` -- exits 0
- `uv run pytest -x -q` -- 1533 passed, 6 skipped
- Codegen drift gate -- CLEAN
