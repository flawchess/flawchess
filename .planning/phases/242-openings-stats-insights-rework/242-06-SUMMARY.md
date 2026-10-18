---
phase: 242-openings-stats-insights-rework
plan: 06
subsystem: ui
tags: [react, openings, repertoire-table, verdict, umami, knip]

requires:
  - phase: 242-01
    provides: "OpeningWDL score_*/is_current, eval_ci99_*, current_cutoff_*, server-side bookmark twin drop"
  - phase: 242-03
    provides: "BookmarkTimeSeries score_*/is_current"
  - phase: 242-04
    provides: "openingVerdict rules, VerdictBar, EvalVerdictPopover"
  - phase: 242-05
    provides: "sticky colour switch, StatsTab color/onColorChange"
provides:
  - "RepertoireTable: per-colour table with pinned bookmarks, most-played rows, collapsed 'Played before (n)', compact Score/Eval verdict cells, phone stacking, sticky header"
  - "useRepertoireRows: view-model merging bookmarks (time series + phase-entry) and most-played rows"
  - "VerdictCompact, ScoreVerdictPopover, score/eval-compact helpers in openingVerdict.ts"
  - "TS mirrors of the 242-01/03 backend fields"
  - "mostPlayedOpenings invalidation on bookmark create/delete/suggest-save"
affects: [242-07, 242-09]

requirements-completed: [D-00, D-00b, D-04, D-05, D-06, D-07, D-18]

actuals:
  tokens: 45000
  tasks: 3
  commits: 3
plan_head_before: d762afd3499dd7bf81704c4b9d751e941b345668
plan_head_after: 562f61ac7ea5405e6971d68ce10547afa256c387

tech-stack:
  added: []
  patterns:
    - "Repertoire row testids and React keys use the row key / numeric index, never the opening name (names repeat without ECO)"
    - "charcoal-texture + overflow-visible so the table's sticky header is not clipped"
    - "data-verdict attribute on VerdictCompact as the test hook (jsdom drops oklch colours)"

key-files:
  created:
    - frontend/src/components/openings/stats/RepertoireTable.tsx
    - frontend/src/pages/openings/useRepertoireRows.ts
    - frontend/src/components/openings/__tests__/RepertoireTable.test.tsx
    - frontend/src/hooks/__tests__/usePositionBookmarks.test.tsx
  modified:
    - frontend/src/types/stats.ts
    - frontend/src/types/position_bookmarks.ts
    - frontend/src/lib/openingVerdict.ts
    - frontend/src/lib/__tests__/openingVerdict.test.ts
    - frontend/src/lib/scoreConfidence.ts
    - frontend/src/components/openings/stats/VerdictBar.tsx
    - frontend/src/components/openings/stats/VerdictPopover.tsx
    - frontend/src/pages/openings/StatsTab.tsx
    - frontend/src/pages/Openings.tsx
    - frontend/src/pages/openings/useOpeningsChartData.ts
    - frontend/src/hooks/usePositionBookmarks.ts
    - frontend/src/hooks/useReadiness.ts
    - frontend/src/components/position-bookmarks/SuggestionsModal.tsx
    - frontend/src/components/stats/EvalCpuPlaceholder.tsx
    - frontend/src/components/stats/__tests__/EvalCpuPlaceholder.test.tsx
  deleted:
    - frontend/src/components/stats/OpeningStatsSection.tsx
    - frontend/src/components/stats/OpeningStatsCard.tsx
    - frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx

key-decisions:
  - "RepertoireTable takes an extra onOpenSuggestions prop (additive to the contract) so the footer carries the Suggest button; testid btn-suggest-bookmarks-footer to avoid the sidebar's btn-suggest-bookmarks"
  - "StatsTab dropped wdlStatsMap too (not only the three nav handlers): bookmark WDL now comes from the time series inside useRepertoireRows, so the map and WdlStatsRow became dead and were removed from useOpeningsChartData"
  - "Eval and score verdicts both gate on the row's total games (>= 20), matching the Moves/Games panel"
  - "The 'Most played' group header only renders when there are current rows; an empty colour shows a 'No {Colour} games match the current filters' row"

duration: ~35min
completed: 2026-10-17
status: complete
---

# Phase 242 Plan 06: Repertoire table Summary

**The Openings Stats tab now shows one repertoire table per colour (pinned bookmarks, current most-played rows, collapsed "Played before (n)") with compact Score and Eval verdict dots whose popovers carry the backend 99% CI, p-value with its reference, and n; the four old card sections and the client-side score CI are gone.**

## Accomplishments

- `RepertoireTable`: semantic table (`repertoire-table-{color}`), columns Opening (44px board, name without ECO, move line) / Games (count + relative last played) / Results (`MiniWDLBar`) / Score / Eval after opening. Rows under 20 games are faded (`UNRELIABLE_OPACITY`) and forced neutral by `openingVerdictReason`. Stale bookmarks keep their pinned place with a "not played recently" chip. "Played before (n)" is a collapsed toggle with a hint built from the backend cutoff date ("not played as White since 14 Feb 2026", no window length hard-coded); expanding fires `panel-open` / `opening-stats-more` once, collapsing fires nothing. Phones (below md) hide the thead and stack each row (name left, Score above Eval at top right, full-width WDL bar with "N games . last played"); from md the header is sticky at `REPERTOIRE_HEADER_STICKY_TOP_PX = 48`. Footer counts plus Suggest button and a verdict legend.
- `useRepertoireRows`: maps `mostPlayedData[color]` split by `is_current` (order and cap come from the backend), and bookmarks of the colour with games, sorted by games, with score fields from the time series (D-18) and eval fields from the phase-entry map. Colour-less bookmarks never reach either table; bookmarks are never capped.
- `VerdictCompact`, `ScoreVerdictPopover` (shares the reason sentences with `EvalVerdictPopover`), `SCORE_VERDICT_BAND`, `scoreDelta`, `formatScorePercent`, `formatEvalCompact`, `stripEcoSuffix`, `isFadedRow`.
- TS mirrors: `OpeningWDL.{score*, eval_ci99_*, is_current}`, `MostPlayedOpeningsResponse.current_cutoff_*`, `BookmarkPhaseEntryItem.eval_ci99_*`, `BookmarkTimeSeries.{score*, is_current}`.
- Creating or deleting a bookmark, and the Suggestions modal save, invalidate `['mostPlayedOpenings']` so the server-side twin drop shows immediately (D-06).
- Deleted `OpeningStatsSection`, `OpeningStatsCard` (+ test), `computeScoreConfidence`, `wilsonBounds`, `ScoreConfidence`; `scoreConfidence.ts` keeps `ConfidenceLevel`. The tier-2 placeholder tests now cover the new eval cell.

## Task Commits

1. **Task 1 (tracer): table, compact verdict cells, StatsTab body** - `0c158bcc1` (feat). Tracer gate: automated-only `<verify>` (build + openingVerdict/Openings.render tests) re-run end to end and passed before expansion; no checkpoint synthesized.
2. **Task 2: cache invalidation, table tests, helper tests** - `beed8d981` (feat)
3. **Task 3: delete old components and client-side score CI** - `562f61ac7` (refactor)

## Verification

- `npm test -- --run` (full frontend suite): 5685 passed.
- `npm run lint`, `npm run build` (tsc -b + vite), `npm run knip`: clean (knip prints the two pre-existing configuration hints only).
- Mutation check: removing `mostPlayedOpenings` from the create/delete invalidation made both `usePositionBookmarks` tests fail; restored.
- Acceptance greps all pass (`RepertoireTable` in StatsTab, no `OpeningStatsSection` there, `export function ScoreVerdictPopover` / `VerdictCompact`, `is_current: boolean`, toggle testid, `opening-stats-more`, "not played recently", `mostPlayedOpenings` in both bookmark files, deleted files gone, `computeScoreConfidence` count 0).
- Browser UAT (Queen's Gambit in "Played before", Caro-Kann Advance shown once, sticky header at 768 / 1280 px, stacking at 390 px) is left to `/gsd-verify-work`; not run here. The `<verify>` also did not exercise the sticky header in a real browser, so confirm no ancestor of the table in `Openings.tsx` clips it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Dead `wdlStatsMap` after the section removal**
- **Found during:** Task 1
- **Issue:** the plan names three handler props to drop but `StatsTab` also destructured `wdlStatsMap`; with `noUnusedLocals`/`noUnusedParameters` and the bookmark WDL now read from the time series, leaving it would be a build error or dead code.
- **Fix:** removed the prop, the `WdlStatsRow` type and the `wdlStatsMap` memo from `useOpeningsChartData`; `Openings.tsx` stops destructuring/passing it.
- **Files modified:** `StatsTab.tsx`, `Openings.tsx`, `useOpeningsChartData.ts`
- **Commit:** `0c158bcc1`

**2. [Additive] `onOpenSuggestions` prop on `RepertoireTable`**
- The plan lists a footer "plus the existing Suggest button" but the contract's prop list has no handler; added the prop (required) and passed `openSuggestions` from `StatsTab`.

**3. [Additive] New hook test**
- `src/hooks/__tests__/usePositionBookmarks.test.tsx` pins the cache invalidation (not in the plan's file list).

**Total deviations:** 1 auto-fixed (blocking), 2 additive. **Impact:** none on scope; `useOpeningsHandlers` still returns the three nav handlers for 242-09.

## Issues Encountered

The plan-commit ledger under the git dir could not be written (sandbox refuses git-dir paths); `commits:` was measured with `git rev-list --count d762afd34..HEAD` = 3 (before this SUMMARY commit).

## Known Stubs

None.

## Threat Flags

None. Bookmark labels render as React text nodes (T-242-15); popover testids are `repertoire-row-{index}-score-info` / `-eval-info` with numeric indices only, so the Umami targets become `repertoire-row-score-info` / `repertoire-row-eval-info` (T-242-16).

## Next Phase Readiness

242-07 (findings) can mount above `RepertoireTable` in `StatsTab`; 242-09 extends `RepertoireRow` with the expanded row and re-adds the open-moves / open-games / open-bookmark-games props from `useOpeningsHandlers`.

## Self-Check: PASSED

- Created files exist: RepertoireTable.tsx, useRepertoireRows.ts, RepertoireTable.test.tsx, usePositionBookmarks.test.tsx.
- Commits `0c158bcc1`, `beed8d981`, `562f61ac7` are ancestors of HEAD.
