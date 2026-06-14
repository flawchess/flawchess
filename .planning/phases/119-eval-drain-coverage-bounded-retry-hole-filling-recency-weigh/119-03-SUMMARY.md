---
phase: 119-eval-drain-coverage
plan: "03"
subsystem: frontend-ux + backend-api
tags:
  - eval-coverage
  - badge
  - cleanup
  - in-flight-removal
dependency_graph:
  requires:
    - 119-01 (ix_eval_jobs_user_active index DROP applied in migration)
  provides:
    - pulsing EvalCoverageBadge CPU icon (analyzedN < totalN gate)
    - in_flight_count / count_in_flight_evals / inFlightCount fully removed end-to-end
    - GamesTab/FlawsTab refresh repointed to analyzedCount transition
  affects:
    - GET /imports/eval-coverage response shape (field removed)
    - EvalCoverageResponse schema (field removed)
    - EvalCoverageBadge (animate-pulse added, inFlightCount prop removed)
    - useEvalCoverage hook (inFlightCount return field removed)
    - GamesTab/FlawsTab invalidation effects (repointed)
tech_stack:
  added: []
  patterns:
    - "conditional animate-pulse on SVG icon gated on data condition"
    - "repoint invalidation effect from >0→0 transition to rising-value transition"
key_files:
  created: []
  modified:
    - app/schemas/imports.py
    - app/routers/imports.py
    - app/repositories/game_repository.py
    - tests/test_game_repository.py
    - tests/routers/test_imports_eval_coverage.py
    - frontend/src/types/api.ts
    - frontend/src/hooks/useEvalCoverage.ts
    - frontend/src/components/library/EvalCoverageBadge.tsx
    - frontend/src/components/results/LibraryGameCardList.tsx
    - frontend/src/components/library/NoEngineAnalysisFlawsState.tsx
    - frontend/src/pages/library/GamesTab.tsx
    - frontend/src/pages/library/FlawsTab.tsx
    - frontend/src/pages/GlobalStats.tsx
    - frontend/src/hooks/__tests__/useEvalCoverage.test.tsx
    - frontend/src/components/library/__tests__/EvalCoverageBadge.test.tsx
    - CHANGELOG.md
decisions:
  - "CPU icon pulses on analyzedN < totalN (not inFlightCount), matching EvalCoverageHeader/EvalCpuPlaceholder sibling pattern"
  - "NoEngineAnalysisFlawsState inFlightCount>0 branch dropped; pulsing badge + per-card NoAnalysisState cover the in-progress signal"
  - "GamesTab/FlawsTab repointed from prevInFlightRef (>0→0) to prevAnalyzedRef (rising) for query invalidation"
  - "SVG className in jsdom is SVGAnimatedString — tests use getAttribute('class') not .className"
metrics:
  duration: "~35 minutes"
  completed: "2026-06-14"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 16
---

# Phase 119 Plan 03: Badge Pulse + in_flight_count Removal Summary

JWT auth with refresh rotation using jose library is NOT what this plan does.
One-liner: Pulsing EvalCoverageBadge CPU icon gated on analyzedN < totalN; in_flight_count / count_in_flight_evals / inFlightCount removed end-to-end (backend schema, router, repository, hook, badge, callers, tests); GamesTab/FlawsTab refresh repointed from inFlightCount transition to analyzedCount-increase transition.

## What Was Built

### Task 1: Backend — remove in_flight_count (commit `0cdc32c6`)

- Deleted `count_in_flight_evals()` from `app/repositories/game_repository.py` (the function that queried eval_jobs for pending|leased rows — the sole reader of the `ix_eval_jobs_user_active` index dropped by the 119-01 migration).
- Removed `in_flight_count: int` field from `EvalCoverageResponse` in `app/schemas/imports.py`; updated docstring to explain the Phase 119-03 rationale.
- Removed the `in_flight = await game_repository.count_in_flight_evals(...)` call and `in_flight_count=in_flight` kwarg from `get_eval_coverage` in `app/routers/imports.py`.
- Deleted `TestCountInFlightEvals` test class from `tests/test_game_repository.py`.
- Updated `tests/routers/test_imports_eval_coverage.py`: removed `in_flight_count` assertions, added `"in_flight_count" not in body` assertions, removed the `_seed_eval_job` helper and the two in-flight-specific tests, removed the `EvalJob / TIER_EXPLICIT` import.

### Task 2: Frontend — pulse badge + remove inFlightCount (commit `6ac64276`)

- `frontend/src/types/api.ts`: removed `in_flight_count` field from `EvalCoverageResponse` interface.
- `frontend/src/hooks/useEvalCoverage.ts`: removed `inFlightCount` from return object; removed `|| inFlight > 0` from the poll branch (now simply `pct_complete < 100`); updated docstring.
- `frontend/src/components/library/EvalCoverageBadge.tsx`: new `isIncomplete = analyzedN < totalN` gate; `<Cpu className={cn('h-4 w-4 shrink-0', isIncomplete && 'animate-pulse')}` added conditional pulse; removed `inFlightCount` prop, `hasInFlight`, "· K in progress" `<span>`; simplified ariaLabel to always `"${analyzedN} of ${totalN} games analyzed"`; simplified guest CTA gate to `isGuest && isBelowThreshold` (removed `!hasInFlight`); updated docstring.
- `frontend/src/components/results/LibraryGameCardList.tsx`: removed `inFlightCount` prop from interface, destructure, and badge pass-through.
- `frontend/src/components/library/NoEngineAnalysisFlawsState.tsx`: removed `inFlightCount` prop; dropped the `inFlightCount > 0` "Analyzing your games…" branch; simplified to two branches (guest CTA | non-guest passive explainer). Documented in component JSDoc why: pulsing badge + per-card NoAnalysisState are the real-time progress signals.
- `frontend/src/pages/library/GamesTab.tsx`: stopped destructuring `inFlightCount`; repointed games-list poll gate from `inFlightCount > 0` to `analyzedCount < totalCount`; renamed `prevInFlightRef` to `prevAnalyzedRef`; repointed effect to fire `invalidateQueries(['library-games'])` when `analyzedCount > prev` (rising, not draining).
- `frontend/src/pages/library/FlawsTab.tsx`: same repoint for flaw-view invalidation (`invalidateQueries(['library-flaws', 'library-flaw-stats', 'library-flaw-comparison'])` on analyzedCount increase).
- `frontend/src/pages/GlobalStats.tsx`: stopped destructuring `inFlightCount`; removed `inFlightCount` from badge prop.
- `frontend/src/hooks/__tests__/useEvalCoverage.test.tsx`: removed `inFlightCount`-returning and in_flight poll-keep tests; updated `analyzedCount`/`inFlightCount` test to confirm `inFlightCount` not in return; removed in_flight_count from mock data shapes.
- `frontend/src/components/library/__tests__/EvalCoverageBadge.test.tsx`: replaced "shows in progress text" case with animate-pulse className tests for incomplete/complete states; removed `inFlightCount` from `defaultProps`; used `getAttribute('class')` not `.className` (SVGAnimatedString in jsdom).

## Verification Results

All gates passed:

- `uv run pytest -n auto tests/test_game_repository.py tests/routers/test_imports_eval_coverage.py`: 23/23 passed
- `uv run ruff format app/ tests/` + `ruff check --fix` + `ty check app/ tests/`: all clean
- `npm run lint`: clean
- `npm run knip`: clean (no dead exports)
- `npm test -- --run`: 924/924 passed
- `grep -rn count_in_flight_evals app/ tests/`: zero matches
- `grep -rn in_flight_count app/`: zero matches (docstring mentions only)
- `grep -rn inFlightCount frontend/src`: only comments/docstrings and one negation test assertion

## Deviations from Plan

### Auto-fixed Issues

None.

### Clarifications Applied

**1. [SVGAnimatedString className in jsdom]**
- **Found during:** Task 2 (test writing)
- **Issue:** `badge.querySelector('svg').className` returns an `SVGAnimatedString` object in jsdom (not a string), so `expect(...).toContain('animate-pulse')` always failed.
- **Fix:** Used `cpuIcon.getAttribute('class')` instead of `.className` in both animate-pulse assertions. Added comment in test explaining the jsdom SVGAnimatedString behavior.
- **Files:** `frontend/src/components/library/__tests__/EvalCoverageBadge.test.tsx`

**2. [NoEngineAnalysisFlawsState quotes in JSX]**
- **Found during:** Task 2
- **Issue:** The word `"Analyze"` in JSX text required HTML entity escaping (`&ldquo;`/`&rdquo;`) to avoid ESLint `no-unescaped-entities` error.
- **Fix:** Replaced straight quotes with `&ldquo;`/`&rdquo;` HTML entities.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced. The response surface SHRANK (field removed from GET /imports/eval-coverage). No new threat flags.

## Known Stubs

None. All changes are clean removals and behavior additions; no placeholder values.

## Self-Check: PASSED

- app/schemas/imports.py: FOUND
- EvalCoverageBadge.tsx: FOUND (animate-pulse present)
- 119-03-SUMMARY.md: FOUND
- Commit 0cdc32c6 (task 1): FOUND
- Commit 6ac64276 (task 2): FOUND
- count_in_flight_evals in app/ tests/: ZERO MATCHES
