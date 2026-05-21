---
phase: 91-two-lane-import-defer-stockfish-eval-to-in-process-cold-drai
plan: "06"
subsystem: frontend
tags:
  - frontend
  - tanstack-query
  - header-bar
  - eval-coverage

dependency_graph:
  requires:
    - "91-01 (backend GET /imports/eval-coverage endpoint)"
  provides:
    - "useEvalCoverage hook (shared TanStack Query)"
    - "EvalCoverageHeader component (page-level header)"
    - "Mount points on Endgames + Openings/Stats"
  affects:
    - "frontend/src/pages/Endgames.tsx (statisticsContent)"
    - "frontend/src/pages/openings/StatsTab.tsx (return)"

tech_stack:
  added:
    - "useEvalCoverage TanStack Query hook with conditional refetchInterval"
  patterns:
    - "refetchInterval: (query) => pct === 100 ? false : interval (stop-at-complete)"
    - "Default pct=100/isPending=false pre-load (prevent caveat flash)"
    - "Shared queryKey across all consumers (one HTTP call per page)"
    - "vi.mock hook at page-level test boundary (no QueryClientProvider needed)"

key_files:
  created:
    - frontend/src/hooks/useEvalCoverage.ts
    - frontend/src/components/EvalCoverageHeader.tsx
    - frontend/src/hooks/__tests__/useEvalCoverage.test.tsx
    - frontend/src/components/__tests__/EvalCoverageHeader.test.tsx
  modified:
    - frontend/src/types/api.ts
    - frontend/src/pages/Endgames.tsx
    - frontend/src/pages/openings/StatsTab.tsx
    - frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx

decisions:
  - "statisticsContent mount point covers both desktop and mobile layouts simultaneously (shared variable used in both TabsContent renders)"
  - "EvalCoverageHeader returns null at 100% — self-managing, no props at mount sites"
  - "Rule 1 bug fix: existing Endgames page test lacked useEvalCoverage mock, broke after mount"

metrics:
  duration: "6 minutes"
  completed: "2026-05-21"
  tasks: 3
  files: 8
---

# Phase 91 Plan 06: Frontend Eval Coverage Header Summary

EvalCoverageResponse type + polling hook + page-level Stockfish progress header bar wired to Endgames and Openings/Stats pages.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 6.1 | Add EvalCoverageResponse type + useEvalCoverage hook + hook test | 0b58d8bf | api.ts, useEvalCoverage.ts, useEvalCoverage.test.tsx |
| 6.2 | Build EvalCoverageHeader component + component test | 82e4173a | EvalCoverageHeader.tsx, EvalCoverageHeader.test.tsx |
| 6.3 | Mount EvalCoverageHeader on Endgames + Openings/Stats | 51cc9de2 | Endgames.tsx, StatsTab.tsx |

## What Was Built

- `EvalCoverageResponse` interface added to `frontend/src/types/api.ts` (Imports section, lines 192-196)
- `useEvalCoverage` hook in `frontend/src/hooks/useEvalCoverage.ts`:
  - Polls `GET /imports/eval-coverage` every 10s while `pct_complete < 100`
  - Named constants: `EVAL_COVERAGE_POLL_INTERVAL_MS = 10_000`, `EVAL_COVERAGE_STALE_TIME_MS = 10_000`
  - QueryKey `['imports', 'eval-coverage']` — shared across all consumers (TanStack Query deduplication)
  - Default `pct: 100 / isPending: false` before first fetch resolves (prevents caveat flashing)
- `EvalCoverageHeader` component in `frontend/src/components/EvalCoverageHeader.tsx`:
  - `role="status"` ARIA live region, `data-testid="eval-coverage-header"`
  - `<Cpu className="h-3.5 w-3.5" aria-hidden="true" />` (matches existing convention)
  - Copy: "Stockfish analysis: N% complete (M games pending)" — plural-aware
  - Returns `null` at 100% — no layout gap
- Mount points:
  - `frontend/src/pages/Endgames.tsx` line ~359: top of `statisticsContent` (covers both desktop and mobile tabs)
  - `frontend/src/pages/openings/StatsTab.tsx` line ~193: top of return, before all sections

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing page test broke after mount**
- **Found during:** Task 6.3 (full test suite run)
- **Issue:** `Endgames.overallPerformance.test.tsx` renders `EndgamesPage` without a `QueryClientProvider`. After mounting `EvalCoverageHeader` inside `statisticsContent`, `useQuery` threw because no provider was available.
- **Fix:** Added `vi.mock('@/hooks/useEvalCoverage', ...)` returning `isPending: false` so the header renders nothing and the test infrastructure does not require a provider.
- **Files modified:** `frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx`
- **Commit:** 78ff7f19

**2. [Rule 1 - Bug] `vi.useFakeTimers()` + `runAllTimersAsync()` causes infinite loop in hook tests**
- **Found during:** Task 6.1 test iteration
- **Issue:** TanStack Query's `QueryObserver` sets up a `setInterval` for `refetchInterval`. Calling `vi.runAllTimersAsync()` fires the interval endlessly.
- **Fix:** Replaced `runAllTimersAsync` with `advanceTimersByTimeAsync` for bounded timer advancement plus `Promise.resolve()` flushes for microtask completion.
- **Files modified:** `frontend/src/hooks/__tests__/useEvalCoverage.test.tsx`
- **Commit:** 0b58d8bf (in initial commit)

## Mount Sites (exact)

| File | Line | Context |
|------|------|---------|
| `frontend/src/pages/Endgames.tsx` | ~359 | Top of `statisticsContent` — first child of `<div className="flex flex-col gap-4">` |
| `frontend/src/pages/openings/StatsTab.tsx` | ~193 | Top of `return`, first child of `<div className="flex flex-col gap-6">` |

**Mobile coverage:** `statisticsContent` is a shared variable used in both the desktop `SidebarLayout > TabsContent` and the mobile `Tabs > TabsContent`. A single mount covers both layouts. No separate mobile branch needed.

**Import page:** confirmed `grep -c EvalCoverageHeader frontend/src/pages/Import.tsx` returns 0. Global topbar/layout components checked — no mount.

## Test Coverage

| File | Tests | What is covered |
|------|-------|-----------------|
| `useEvalCoverage.test.tsx` | 3 | polls at interval when pending; stops polling at 100%; safe defaults pre-load |
| `EvalCoverageHeader.test.tsx` | 4 | hidden when not pending; plural label; singular label; role+testid |

Full test suite: 593 tests, 51 files — all pass.

## Known Stubs

None. All data is wired through the real TanStack Query hook against the backend endpoint.

## Self-Check: PASSED

- `frontend/src/hooks/useEvalCoverage.ts`: FOUND
- `frontend/src/components/EvalCoverageHeader.tsx`: FOUND
- `frontend/src/hooks/__tests__/useEvalCoverage.test.tsx`: FOUND
- `frontend/src/components/__tests__/EvalCoverageHeader.test.tsx`: FOUND
- Commits 0b58d8bf, 82e4173a, 51cc9de2, 78ff7f19: all present in git log
- `npm run lint`: exits 0
- `npm run build`: exits 0
- `npm run knip`: no EvalCoverageHeader orphan
- All 593 tests pass
