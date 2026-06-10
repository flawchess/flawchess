---
phase: quick-260606-io6
plan: 01
subsystem: library-frontend, stats-frontend, stats-backend, library-backend
tags: [library, filter, flaw-tags, played-as, rating-chart, color-filter]
dependency_graph:
  requires: []
  provides:
    - flawThresholds.ts (frontend threshold constants)
    - tagDefinitions.ts (FlawTag definitions + labels)
    - TagChip hover/tap definition popover
    - FilterState.playedAs tri-state field
    - color param on /stats/global + /library/games + /library/flaw-stats
    - enabledTimeControls prop on RatingChart
  affects:
    - FilterPanel.tsx
    - LibraryFilterPanel.tsx
    - GlobalStats.tsx
    - useLibrary.ts / useStats.ts / client.ts
    - stats_repository.py / stats_service.py / stats.py router
    - library_repository.py / library_service.py / library.py router
tech_stack:
  added:
    - radix-ui Popover (reused from info-popover.tsx pattern) in TagChip
  patterns:
    - hover-in delay + mouseleave close for desktop tooltips (100ms, clearTimeout on enter)
    - Chip-as-trigger (no separate HelpCircle icon) for inline popovers
    - tri-state playedAs mapped to color param (either -> omit, white/black -> pass)
    - apply_game_filters color= reuse for all three new filter paths
key_files:
  created:
    - frontend/src/lib/flawThresholds.ts
    - frontend/src/lib/tagDefinitions.ts
    - tests/test_library_router.py
  modified:
    - frontend/src/components/library/TagChip.tsx
    - frontend/src/components/filters/FilterPanel.tsx
    - frontend/src/components/filters/LibraryFilterPanel.tsx
    - frontend/src/pages/GlobalStats.tsx
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/hooks/useStats.ts
    - frontend/src/api/client.ts
    - frontend/src/components/stats/RatingChart.tsx
    - app/repositories/stats_repository.py
    - app/services/stats_service.py
    - app/routers/stats.py
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - app/routers/library.py
    - tests/test_stats_router.py
decisions:
  - "playedAs uses 'either'|'white'|'black' tri-state, NOT reusing binary color field"
  - "Severity drop constants omitted from flawThresholds.ts (knip dead-export, no consumers yet)"
  - "Chip-is-trigger pattern per design_decisions — no separate HelpCircle"
  - "visibleTcs computed inline in yDomain useMemo with enabledTimeControls in dep array"
metrics:
  duration: ~60 minutes
  completed: 2026-06-06
  tasks_completed: 4
  files_changed: 16
---

# Phase quick-260606-io6 Plan 01: Tag popovers, Played-as filter, TC-aware rating charts

One-liner: Flaw tag chips now show hover/tap definition popovers; a tri-state "Played as" filter wires through Games, FlawStatsPanel, and WDL stats (excluding rating charts); rating charts now render only enabled TC series.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Tag definition popovers on flaw chips | 1c437a97 | flawThresholds.ts, tagDefinitions.ts, TagChip.tsx |
| 1-fix | Remove unexported severity constants (knip) | ae495978 | flawThresholds.ts |
| 2 | Played as tri-state filter — frontend wiring | e435ff31 | FilterPanel.tsx, LibraryFilterPanel.tsx, GlobalStats.tsx, useLibrary.ts, useStats.ts, client.ts |
| 3 | Backend color param on /stats/global + library | c7bacb15 | stats_repository.py, stats_service.py, stats.py, library_repository.py, library_service.py, library.py, test_stats_router.py, test_library_router.py |
| 4 | Rating charts honour the TC filter | da91ca66 | RatingChart.tsx, GlobalStats.tsx |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Knip dead-export failure on severity drop constants**
- **Found during:** Full gate (knip step)
- **Issue:** Plan specified exporting INACCURACY_DROP/MISTAKE_DROP/BLUNDER_DROP "for completeness"; these are not used by any frontend consumer and knip CI blocks on dead exports.
- **Fix:** Removed them from exports; added a comment inside the JSDoc block documenting their values and directing future engineers to export them when first consumed.
- **Files modified:** frontend/src/lib/flawThresholds.ts
- **Commit:** ae495978

**2. [Rule 2 - Missing critical functionality] useStats resolvedFilters construction sites needed playedAs**
- **Found during:** Task 2 tsc check
- **Issue:** `useMostPlayedOpenings` and `useBookmarkPhaseEntryMetrics` construct `FilterState` objects inline; the new required field `playedAs` was missing.
- **Fix:** Added `playedAs: 'either'` to both `resolvedFilters` construction sites in useStats.ts.
- **Files modified:** frontend/src/hooks/useStats.ts
- **Commit:** e435ff31 (included in Task 2)

## Known Caveats

### "Results by Color" degenerate case under Played as = White

When the user sets "Played as = White", the `/stats/global?color=white` call filters all statistics including the "Results by Color" card (`by_color`). This causes that card to degenerate to a single row (White only). Per the locked design decision in the plan, this is intentional: "filter all statistics except rating charts." No special-casing was added. The SUMMARY notes this for future product consideration — if the card is confusing in this state, a possible future improvement is to hide or annotate the by_color card when a color filter is active.

### Manual sync coupling between frontend and backend threshold constants

`frontend/src/lib/flawThresholds.ts` mirrors the numeric constants defined in `app/services/flaws_service.py` (lines 39-65). These two files must be kept in sync manually whenever thresholds are changed. The header comment in `flawThresholds.ts` names the backend file as the source of truth. There is no automated check for drift — this is a known maintenance coupling.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced. The `color` query param added to three existing GET endpoints follows the existing pattern of `apply_game_filters` and cannot be used to access another user's data (all queries are scoped by `user_id` from the JWT).

## Self-Check: PASSED

### Created files exist:
- `frontend/src/lib/flawThresholds.ts` — exists
- `frontend/src/lib/tagDefinitions.ts` — exists
- `tests/test_library_router.py` — exists

### Commits exist:
- 1c437a97 — feat(quick-260606-io6): tag definition hover/tap popovers on flaw chips
- e435ff31 — feat(quick-260606-io6): Played as tri-state filter, frontend store + wiring
- c7bacb15 — feat(quick-260606-io6): color param on /stats/global + library endpoints
- da91ca66 — feat(quick-260606-io6): rating charts honour the TC filter
- ae495978 — fix(quick-260606-io6): remove unexported severity constants from flawThresholds.ts

### Final gate: PASSED
- Backend: ruff format/check + ty check + pytest -n auto -x = 2340 passed, 10 skipped
- Frontend: lint + knip + vitest (746 passed) + tsc --noEmit = all clean
