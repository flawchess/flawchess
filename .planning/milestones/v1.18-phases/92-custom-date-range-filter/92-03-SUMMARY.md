---
phase: "92"
plan: "03"
subsystem: frontend
tags: [filters, hooks, date-range, migration, wire-format, tdd]
dependency_graph:
  requires: ["92-01", "92-02"]
  provides: ["filter-wire-format-frontend", "customRange-FilterState"]
  affects: ["useStats", "useOpenings", "useEndgames", "useEndgameInsights", "useNextMoves", "useOpeningInsights", "useStats.useBookmarkPhaseEntryMetrics"]
tech_stack:
  added: ["date-fns@4.2.1"]
  patterns: ["presetToDates memoization", "resolveDateRange dispatch", "dateRangeToWireParams serialization"]
key_files:
  created:
    - frontend/src/lib/recency.ts
    - frontend/src/lib/__tests__/recency.test.ts
  modified:
    - frontend/src/types/api.ts
    - frontend/src/components/filters/FilterPanel.tsx
    - frontend/src/api/client.ts
    - frontend/src/types/stats.ts
    - frontend/src/hooks/useStats.ts
    - frontend/src/hooks/useOpenings.ts
    - frontend/src/hooks/useEndgames.ts
    - frontend/src/hooks/useEndgameInsights.ts
    - frontend/src/hooks/useNextMoves.ts
    - frontend/src/hooks/useOpeningInsights.ts
    - frontend/src/pages/GlobalStats.tsx
    - frontend/src/pages/Openings.tsx
    - frontend/src/components/insights/OpeningInsightsBlock.tsx
    - frontend/src/hooks/__tests__/useEndgameInsights.test.tsx
    - frontend/src/hooks/__tests__/useOpeningInsights.test.tsx
    - frontend/src/components/insights/OpeningInsightsBlock.test.tsx
    - frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx
    - frontend/src/components/charts/__tests__/EndgameEloTimelineSection.test.tsx
    - frontend/knip.json
decisions:
  - "Made customRange optional in OpeningInsightsFilters interface (not required) to avoid breaking tests that pass only recency; hook already defaults to null via filters?.customRange ?? null"
  - "Added date-fns to knip.json ignoreDependencies because knip entry is src/prerender.tsx which cannot trace the main app import graph"
  - "Fixed pre-existing EndgameEloTimelineSection test (popover text mismatch: expected 'your endgame games', actual copy is 'your Endgame ELO') as a Rule 1 auto-fix"
metrics:
  duration: "~90 minutes (active execution; resumed across context boundary)"
  completed: "2026-05-22"
  tasks_completed: 2
  files_changed: 19
---

# Phase 92 Plan 03: Frontend Type + Hook Migration to from_date/to_date Summary

Frontend date-range wire format migration: renamed `Recency` to `RecencyPreset`, created `recency.ts` utility library with memoized preset-to-dates conversion, extended `FilterState` with `customRange`, and migrated all 7 API hooks to emit `from_date`/`to_date` ISO strings instead of a `recency` preset string.

## What Was Built

### Task 1 (TDD RED + GREEN)

- `frontend/src/lib/recency.ts` -- four exports:
  - `presetToDates(preset, now?)` -- converts a `RecencyPreset` to `{from?, to?}` Date objects; memoized per `${preset}|YYYY-MM-DD` key to keep TanStack Query keys stable within a calendar day
  - `dateToWire(d)` -- formats a `Date` to `'yyyy-MM-dd'` string or returns `undefined`
  - `dateRangeToWireParams(range)` -- converts `{from?, to?}` to `{from_date?, to_date?}` wire params
  - `resolveDateRange(filters)` -- dispatches to `customRange` when `recency === 'custom'`, otherwise delegates to `presetToDates`
- `frontend/src/lib/__tests__/recency.test.ts` -- 10 unit tests covering all 4 exports, cache hit/miss behavior, null/all preset handling
- `frontend/src/types/api.ts` -- renamed `Recency` to `RecencyPreset` with JSDoc noting it is a UI-only type (not sent to API)
- `frontend/package.json` -- added `date-fns@^4.2.1`

### Task 2 (Implementation)

- `FilterPanel.tsx` -- added `customRange: { from?: Date; to?: Date } | null` to `FilterState`, `DEFAULT_FILTERS`, `FILTER_DOT_FIELDS`, and `areFiltersEqual` deep-compare; `recency` field type extended with `'custom'` literal; reset button resets `customRange` too
- `api/client.ts` -- `buildFilterParams` drops `recency` param, emits `from_date`/`to_date`; `statsApi` and `endgameApi` signatures updated to accept date param objects
- `types/stats.ts` -- `BookmarkPhaseEntryRequest` replaces `recency?: string | null` with `from_date?/to_date?`
- All 7 hooks migrated:
  1. `useStats.useRatingHistory` -- accepts `FilterState` + resolves date range
  2. `useStats.useGlobalStats` -- same
  3. `useStats.useMostPlayedOpenings` -- resolves date range from `{recency, customRange, ...}`
  4. `useStats.useBookmarkPhaseEntryMetrics` -- the 7th (previously missed) hook; same pattern
  5. `useOpenings` -- uses `resolveDateRange` + `dateRangeToWireParams`
  6. `useEndgames` -- same
  7. `useEndgameInsights` -- same
  8. `useNextMoves` -- same
  9. `useOpeningInsights` -- same (POST body uses `...dateParams`)
- `pages/GlobalStats.tsx` -- passes full `filters` to `useRatingHistory`/`useGlobalStats`
- `pages/Openings.tsx` -- adds `customRange` to `useMostPlayedOpenings` and `useBookmarkPhaseEntryMetrics`; removes stale `recency` field from `timeSeriesRequest` (D-19 cleanup, TimeSeriesRequest.recency removed in Plan 02 backend)
- `OpeningInsightsBlock.tsx` -- passes `customRange` to `useOpeningInsights`
- `knip.json` -- adds `date-fns` to `ignoreDependencies` (knip entry is `prerender.tsx`, cannot trace main app import graph)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-existing broken test in EndgameEloTimelineSection.test.tsx**
- **Found during:** Task 2 test suite run
- **Issue:** Test at line 656 expected `/your endgame games/i` in the info popover but the component copy said "your Endgame ELO (dashed line)". The phrase "your endgame games" was never in the component -- a stale assertion from before the popover copy was rewritten in Phase 87.6.
- **Fix:** Updated assertion to `/your Endgame ELO/i`
- **Files modified:** `frontend/src/components/charts/__tests__/EndgameEloTimelineSection.test.tsx`
- **Commit:** f4729ff5

**2. [Rule 2 - Missing critical functionality] knip.json needs date-fns in ignoreDependencies**
- **Found during:** Task 2 verification (npm run knip)
- **Issue:** knip entry point is `src/prerender.tsx` which does not traverse the main app's import graph. `date-fns` is imported by `src/lib/recency.ts` (reachable from main app) but knip cannot see this chain.
- **Fix:** Added `"date-fns"` to `ignoreDependencies` in `knip.json` so CI does not fail
- **Files modified:** `frontend/knip.json`
- **Commit:** f4729ff5

**3. [Rule 2 - API compatibility] Made customRange optional in OpeningInsightsFilters**
- **Found during:** Task 2 (test type-checking)
- **Issue:** The `OpeningInsightsFilters` interface had `customRange` as required, but the hook itself defaults to `null` via `filters?.customRange ?? null`. Tests pass inline filter objects without `customRange`, which would be a TypeScript error.
- **Fix:** Changed `customRange` to `customRange?` (optional) in the interface
- **Files modified:** `frontend/src/hooks/useOpeningInsights.ts`
- **Commit:** f4729ff5

**4. [Rule 1 - Bug] Exhaustive switch TypeScript error in recency.ts**
- **Found during:** Task 1 type checking
- **Issue:** Original `_subForPreset` accepted `RecencyPreset` with a `case 'all': { const _exhaustive: never = preset }` branch, but TypeScript errored because `'all'` cannot be assigned to `never` (it's a valid `RecencyPreset` value, not unreachable)
- **Fix:** Created `type RangedPreset = Exclude<RecencyPreset, 'all'>` and changed the function signature to `_subForPreset(preset: RangedPreset, ...)` with a `default:` branch for exhaustiveness
- **Files modified:** `frontend/src/lib/recency.ts`
- **Commit:** a1c4b1f4

## TDD Gate Compliance

- RED commit: `a4d6d45d` -- `test(92-03): add failing tests for presetToDates, dateToWire, dateRangeToWireParams`
- GREEN commit: `a1c4b1f4` -- `feat(92-03): create recency.ts utility + rename Recency -> RecencyPreset`
- Task 2 commit: `f4729ff5` -- `feat(92-03): extend FilterState with customRange + migrate 7 hooks to from_date/to_date`

Both RED and GREEN gates committed. TDD gate compliance: PASSED.

## Verification

- `npm run lint`: passed (0 ESLint errors)
- `npm run knip`: passed (0 dead exports or unused dependencies)
- `npx tsc -p tsconfig.app.json --noEmit`: passed (0 TypeScript errors)
- `npm test -- --run`: 611/611 tests passing (54 test files)

## Known Stubs

None. The `customRange` field is wired through the full stack (FilterState -> resolveDateRange -> dateRangeToWireParams -> API params). The date picker UI (plan 92-04) will populate it; until then it is `null` by default, which falls back to preset behavior transparently.

## Threat Flags

No new security-relevant surface introduced. This plan performs a purely frontend refactor: wire format migration from string-enum `recency` param to `from_date`/`to_date` ISO date strings. No new network endpoints, auth paths, or trust boundary changes.

## Self-Check

Checking created files exist:
- `frontend/src/lib/recency.ts` -- YES
- `frontend/src/lib/__tests__/recency.test.ts` -- YES

Checking commits exist:
- `a4d6d45d` (RED): YES
- `a1c4b1f4` (GREEN): YES
- `f4729ff5` (Task 2 feat): YES

## Self-Check: PASSED
