---
phase: 260411-ni2
plan: 01
subsystem: frontend/filters
tags: [ui, filters, refactor, mobile, quick]
requires: [260411-fcs]
provides: [global-reset-semantics, FILTER_DOT_FIELDS]
affects:
  - frontend/src/components/filters/FilterPanel.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/pages/Endgames.tsx
  - frontend/src/pages/GlobalStats.tsx
tech_stack_added: []
patterns:
  - FILTER_DOT_FIELDS — single source of truth for "which FilterState keys count as modified" used by all three pages
  - Global-reset-except-color via `onChange({ ...DEFAULT_FILTERS, color: filters.color })`
key_files_created: []
key_files_modified:
  - frontend/src/components/filters/FilterPanel.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/pages/Endgames.tsx
  - frontend/src/pages/GlobalStats.tsx
decisions:
  - Reset button variant: outline -> secondary
  - Modified-dot ignores `color` across all three pages (uniform semantics)
  - GlobalStats dot drops its restricted `['platforms','recency']` subset and now reflects the shared store
  - Mobile drawer Played-as row removed — color remains accessible via btn-toggle-played-as in sticky mobile header
requirements: [QUICK-260411-ni2]
metrics:
  tasks_completed: 3
  commits: 3
  duration_minutes: ~15
  completed_date: 2026-04-11
---

# Phase 260411-ni2 Plan 01: Global Reset Filters + MatchSide Exempt-from-Dot Summary

Revision of quick task 260411-fcs — make Reset globally restore FilterState to defaults (except `color`/Played-as), make the modified-dot ignore `color` uniformly on all three pages, switch the Reset button to `secondary` variant, and clean up the Openings mobile drawer by removing the redundant Played-as row.

## Changes

### Task 1: FilterPanel.tsx (commit `53de85a`)

- Added exported `FILTER_DOT_FIELDS: ReadonlyArray<keyof FilterState>` containing 7 keys: `matchSide`, `timeControls`, `platforms`, `rated`, `opponentType`, `opponentStrength`, `recency`. Excludes `color` by design.
- Removed the `onReset` prop from `FilterPanelProps` interface and the component destructuring.
- Rewrote the Reset button onClick to global-reset-except-color:
  ```tsx
  onClick={() => { onChange({ ...DEFAULT_FILTERS, color: filters.color }); }}
  ```
  (Replaced the ~40-line panel-scoped patch assembly.)
- Changed Reset button `variant="outline"` → `variant="secondary"`.
- Preserved `data-testid="btn-reset-filters"` and `showDeferredApplyHint` rendering.
- Comment above the Reset block updated to describe the global-reset-except-color semantics.

### Task 2: Openings.tsx (commit `3aa9400`)

- Imported `FILTER_DOT_FIELDS` from FilterPanel.
- `isFiltersModified` useMemo passes `FILTER_DOT_FIELDS` as the third arg to `areFiltersEqual` — changing only `filters.color` no longer lights the dot.
- Deleted the `<div className="flex flex-wrap gap-x-4 gap-y-3">` container in the mobile filter drawer that held both the Played-as and Piece filter ToggleGroups.
- Replaced it with a standalone full-width Piece filter block:
  - ToggleGroup has `className="w-full"`.
  - Each ToggleGroupItem has `className="flex-1 min-h-11"` so Mine/Opponent/Both each take one-third of the drawer width.
  - Label row (`Piece filter` + InfoPopover) preserved verbatim with existing `piece-filter-info-sidebar` test-id.
- All four Piece filter test-ids unchanged: `filter-piece-filter-sidebar`, `filter-piece-filter-mine-sidebar`, `filter-piece-filter-opponent-sidebar`, `filter-piece-filter-both-sidebar`.
- `btn-toggle-played-as` in the sticky mobile header (Openings.tsx line 1253) is untouched — mobile users retain color-toggle access.
- Pulse-on-commit logic (`prevFiltersRef`, `justCommittedFromDrawerRef`, the useEffect) unchanged.
- Line 531's `areFiltersEqual(localFilters, filters)` commit-detection call unchanged.

### Task 3: Endgames.tsx + GlobalStats.tsx (commit `595bd3b`)

- **Endgames.tsx**: imported `FILTER_DOT_FIELDS`, updated `isModified` useMemo to pass it to `areFiltersEqual`. Pure refactor — Endgames never mutates `color` so behavior is identical, but the source is now uniform with the other two pages.
- **GlobalStats.tsx**: imported `FILTER_DOT_FIELDS`, replaced the old restricted `['platforms', 'recency'] as const` comparison with `FILTER_DOT_FIELDS`. Variable renamed `isGlobalStatsFiltersModified` → `isFiltersModified` for source symmetry across the three pages. Both JSX references (notificationDot at ~line 182, mobile dot at ~line 218) updated. Test-ids (`filters-modified-dot`, `filters-modified-dot-mobile`) unchanged.
- Behavioral change on GlobalStats: if the user sets e.g. `timeControls = ['blitz']` on Openings, the GlobalStats dot now lights up even though GlobalStats only exposes platform+recency. Clicking Reset on GlobalStats also clears those hidden-from-UI fields (global reset semantics). This is intentional per the plan.

## Verification

Full verification suite run at the end of Task 3 — all green:

| Check | Result |
|-------|--------|
| `npm run lint` | passed (0 errors, 0 warnings) |
| `npx tsc --noEmit` | passed (0 errors) |
| `npm run knip` | passed (0 dead exports, 0 unused deps) |
| `npm run build` | succeeded (vite build + PWA) |
| `npm test` | 73/73 passed |

## Cross-file grep invariants (post-change)

- `FILTER_DOT_FIELDS` in frontend/src/: 1 declaration + 3 imports + 3 uses in pages + 1 comment reference.
- `onReset` in frontend/src/components/filters/: zero matches (fully removed).
- `filter-played-as-sidebar` / `filter-played-as-white-sidebar` / `filter-played-as-black-sidebar` in frontend/src/: zero matches.
- `isGlobalStatsFiltersModified` in frontend/: zero matches (fully renamed).
- `btn-toggle-played-as` at Openings.tsx:1253: still present and functional.

## Deviations from Plan

None — plan executed exactly as written. The plan was very precise about line numbers, test-ids, and expected grep results.

One minor non-behavioral cleanup was needed: after adding the `FILTER_DOT_FIELDS` export, an `eslint-disable-next-line react-refresh/only-export-components` directive I initially included was flagged as unused (the linter only flags component exports, not plain constants). Removed the redundant directive — the other existing directives on `DEFAULT_FILTERS` and `areFiltersEqual` remain untouched.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1 | `53de85a` | feat(260411-ni2-01): global reset + FILTER_DOT_FIELDS in FilterPanel |
| 2 | `3aa9400` | feat(260411-ni2-02): uniform modified-dot + clean mobile drawer on Openings |
| 3 | `595bd3b` | feat(260411-ni2-03): uniform modified-dot on Endgames and GlobalStats |

## Manual Smoke Test (deferred to user)

The execution agent did not run a dev server. Recommended manual checks:

1. Openings: change Played-as to black, time control to blitz — dot lights up. Click Reset. Expected: timeControls cleared, Played-as still black, dot gone.
2. Endgames: change recency to "1 year". Dot lights. Click Reset. Dot gone.
3. GlobalStats: set platform to chess.com. Dot lights. Click Reset. Dot gone.
4. Mobile viewport on Openings: open filter drawer, verify no "Played as" row; Piece filter spans full width with three equal-width buttons; close drawer; tap the sticky color button (`btn-toggle-played-as`) to toggle color — works.

## Self-Check: PASSED

- File existence:
  - FOUND: frontend/src/components/filters/FilterPanel.tsx
  - FOUND: frontend/src/pages/Openings.tsx
  - FOUND: frontend/src/pages/Endgames.tsx
  - FOUND: frontend/src/pages/GlobalStats.tsx
- Commit existence:
  - FOUND: 53de85a (Task 1)
  - FOUND: 3aa9400 (Task 2)
  - FOUND: 595bd3b (Task 3)
- Full verification suite (lint + tsc + knip + build + test): all green.
