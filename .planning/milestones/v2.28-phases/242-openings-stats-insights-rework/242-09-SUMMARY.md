---
phase: 242-openings-stats-insights-rework
plan: 09
subsystem: ui
tags: [react, openings, repertoire-table, recharts, scorechart, umami, vitest, knip]

requires:
  - phase: 242-03
    provides: "TimeSeriesPoint.per_week_games (weekly points keyed by ISO-week Monday)"
  - phase: 242-06
    provides: "RepertoireTable, RepertoireRowModel, VerdictCompact, score/eval popovers"
  - phase: 242-07
    provides: "FindingCard patterns for VerdictBar + popovers"
  - phase: 242-08
    provides: "Three-tab Openings page, shared OpeningsTab union"
provides:
  - "RepertoireExpandedRow: 200px board, Moves / Games / Bookmark links, Score and Eval after opening VerdictBars, per-opening Score over time chart"
  - "Single-series ScoreChart({ series, showVolume?, testId? }) with grey weekly volume bars (tallest = bottom 20%)"
  - "useOpeningRowTimeSeries: lazy per-row series (bookmark rows reuse theirs)"
  - "timeSeriesFilterParams shared by the table-wide and per-row time-series requests"
  - "Umami panel target opening-row-expand"
affects: [verify-work]

requirements-completed: [D-00, D-14]

actuals:
  tokens: 40000
  tasks: 3
  commits: 3
plan_head_before: a0adb2e55903a619446556745d17a54a6ac65b51
plan_head_after: 09955d2a99b88d94e7f1d6faf5e916031f3fcda8

tech-stack:
  added: []
  patterns:
    - "Lazy-by-mounting: the expanded block only mounts while a row is open, so the per-row series request fires on expand (hook still takes an enabled flag)"
    - "Expanded detail row is a separate tr (max-md:block) below its row; expand state is a Set of row keys"
    - "Volume bars share the Endgame charts' hidden right axis [0, barMax * VOLUME_BAR_DOMAIN_FACTOR]"

key-files:
  created:
    - frontend/src/components/openings/stats/RepertoireExpandedRow.tsx
    - frontend/src/pages/openings/useOpeningRowTimeSeries.ts
  modified:
    - frontend/src/components/openings/stats/RepertoireTable.tsx
    - frontend/src/components/openings/__tests__/RepertoireTable.test.tsx
    - frontend/src/components/charts/ScoreChart.tsx
    - frontend/src/components/charts/__tests__/ScoreChart.test.tsx
    - frontend/src/pages/openings/StatsTab.tsx
    - frontend/src/pages/Openings.tsx
    - frontend/src/pages/openings/useOpeningsHandlers.ts
    - frontend/src/pages/openings/useOpeningsChartData.ts
    - frontend/src/lib/analytics.ts
    - frontend/src/lib/theme.ts
    - frontend/src/types/position_bookmarks.ts
    - CHANGELOG.md

key-decisions:
  - "Chevron column added as a 6th table column (sr-only header 'Details'); on phones it sits right of the WDL bar row instead of adding a row"
  - "The ScoreChart line colour lives in theme.ts as SCORE_OVER_TIME_LINE (frontend/CLAUDE.md theme rule), replacing the removed CHART_COLORS palette"
  - "Expand tracking fires on every collapsed->expanded transition (collapse never), matching the existing opening-stats-more pattern"
  - "Per-row chart sits in a third column from xl, below the board+bars from md, stacked on phones"

duration: ~45min
completed: 2026-10-17
status: complete

coverage:
  - id: D1
    description: "Repertoire rows expand to a 200px board, Moves / Games / Bookmark links, Score and Eval verdict bars; first expand tracked, collapse not"
    requirement: "D-00"
    verification:
      - kind: unit
        ref: "frontend/src/components/openings/__tests__/RepertoireTable.test.tsx#RepertoireTable expanded row shows the 200px board, both verdict bars and the chart block, tracking the expand once"
        status: pass
    human_judgment: false
  - id: D2
    description: "ScoreChart takes one series plus optional weekly volume bars (tallest in the bottom 20%); inactivity-gap palm tree and empty state preserved; multi-bookmark mode and Stats multi-line chart removed"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "frontend/src/components/charts/__tests__/ScoreChart.test.tsx"
        status: pass
    human_judgment: false
  - id: D3
    description: "Most-played rows fetch their series only when expanded; bookmark rows reuse theirs"
    requirement: "D-00"
    verification:
      - kind: unit
        ref: "frontend/src/components/openings/__tests__/RepertoireTable.test.tsx#useOpeningRowTimeSeries"
        status: pass
    human_judgment: false
  - id: D4
    description: "Bookmark link creates a bookmark (label without ECO, match side both); Remove bookmark deletes it"
    requirement: "D-00"
    verification:
      - kind: unit
        ref: "frontend/src/components/openings/__tests__/RepertoireTable.test.tsx#creates a bookmark from a most-played row without the ECO code and with both sides"
        status: pass
      - kind: unit
        ref: "frontend/src/components/openings/__tests__/RepertoireTable.test.tsx#shows Remove bookmark on a bookmark row, deletes it and opens its Games via the bookmark"
        status: pass
    human_judgment: false
  - id: D5
    description: "Visual layout of the expanded row (phone link stacking beside the board, tablet/desktop columns, chart sizing, sticky header unclipped) in a real browser at 390 / 768 / 1280 px"
    verification: []
    human_judgment: true
    rationale: "jsdom cannot assess layout, chart rendering at real widths or sticky behaviour; planned for /gsd-verify-work browser UAT"
---

# Phase 242 Plan 09: Expanded repertoire row Summary

**Repertoire rows now expand to a 200px board, Moves / Games / Bookmark links, Score and Eval-after-opening verdict bars and a per-opening Score over time chart (rolling-50 line plus grey weekly game bars), and ScoreChart is a single-series component with the multi-bookmark mode and Stats multi-line chart retired.**

## Accomplishments

- `RepertoireExpandedRow`: 200px board (flipped for black), `brand-outline` Moves / Games / Bookmark buttons (stacked right of the board on phones), a Score `VerdictBar` (centre 50%, `SCORE_VERDICT_BAND`) and an Eval after opening `VerdictBar` centred on the colour baseline with the faint zero tick and colour swatch, each with its popover (`repertoire-row-{i}-score-bar-info` / `-eval-bar-info`); em dash without eval, `EvalCpuPlaceholder` until tier 2.
- `RepertoireTable`: chevron column plus a name button, both `aria-expanded` toggles over a `Set` of row keys; the expanded detail row is a separate `tr`; expanding tracks `panel-open` / `opening-row-expand`, collapsing tracks nothing.
- `ScoreChart({ series, showVolume?, testId? })`: `ComposedChart`, rolling score line on `niceWinRateAxis` (50% always inside the domain), dashed 50% reference line, palm-tree gap markers, optional `Bar` on a hidden right axis `[0, barMax * VOLUME_BAR_DOMAIN_FACTOR]` (= 5, tallest bar fills the bottom 20%), tooltip with week, score, "past N games" and "N games that week". Legend, hide toggles, card header, `CHART_COLORS` and the bookmark prop are gone. The Stats tab's multi-line chart block and its "Loading chart data..." branch are deleted.
- `useOpeningRowTimeSeries`: bookmark rows return their loaded series with no request; most-played rows request one `match_side: 'full'` series (`MOST_PLAYED_ROW_SERIES_ID = 0`) only while expanded. Loading and error branches render in the chart block (`LoadError` "the score chart").
- `Bookmark` / `Remove bookmark` link wired to the existing create / delete mutations (payload: ECO-free label, `match_side: 'both'`, `is_flipped` for black); disabled while pending; no Umami event (DB-known).
- `handleOpenMoves` now takes `(pgn, color)`; `Openings.tsx` and `StatsTab` re-wire `onOpenMoves`, `onOpenGames`, `onOpenBookmarkGames` (carry-over from 242-06).
- CHANGELOG `[Unreleased]` gets a "### Changed" group describing the reworked Openings Stats page.

## Task Commits

1. **Task 1 (tracer): expanding a row shows board, links and both verdict bars** - `c7a0a9b5c` (feat). Tracer gate: automated-only `<verify>` (openings tests, Openings.render, analytics tests, `npm run build`) passed before expansion; no checkpoint synthesized.
2. **Task 2: single-series ScoreChart with volume bars, lazy series hook** - `a976fa818` (feat)
3. **Task 3: Bookmark link, expansion tests, CHANGELOG** - `09955d2a9` (feat)

## Verification

- `npm run lint`, `npm run build` (tsc -b + vite), `npm run knip` (only the two pre-existing configuration hints), `npm test -- --run`: 338 files, 5673 tests pass.
- Mutation checks (revert the fix, confirm a test fails): `VOLUME_BAR_DOMAIN_FACTOR` 5 -> 2 fails the volume-bar test; dropping the `enabled` gate fails "does not fetch a most-played row's series until enabled"; `match_side: 'both'` -> `'mine'` fails the create-bookmark payload test.
- Acceptance greps all pass (`opening-row-expand` in analytics and table, `RepertoireExpandedRow` and `aria-expanded` in the table, `showVolume`, `VOLUME_BAR_DOMAIN_FACTOR = 5`, `CHART_COLORS` 0, `ScoreChart` in StatsTab 0, `useTimeSeries` in the hook, "Played before" in the Unreleased changelog).
- Browser UAT (phone 390 / tablet 768 / desktop 1280, sticky header unclipped, chart at real widths) is left to `/gsd-verify-work`; not run here.

## Deviations from Plan

### Auto-fixed / additive

**1. [Rule 3 - Blocking] Shared request-param builder instead of a copy**
- **Found during:** Task 2
- **Issue:** the plan asks for "the same filter params as useOpeningsChartData"; copying the block would duplicate the recency/opponent-strength wiring.
- **Fix:** extracted `timeSeriesFilterParams(filters)` in `useOpeningsChartData.ts` and used it in both places.
- **Files modified:** `frontend/src/pages/openings/useOpeningsChartData.ts` (not in the plan's file list)
- **Commit:** `a976fa818`

**2. [Additive] `SCORE_OVER_TIME_LINE` in theme.ts**
- frontend/CLAUDE.md requires semantic colours in `theme.ts`; the removed `CHART_COLORS` palette had no single-series replacement. Added one constant (`frontend/src/lib/theme.ts`, not in the plan's file list).

**3. [Additive] `debouncedFilters` prop on `RepertoireTable`**
- The lazy per-row request needs the sidebar filters; the table and expanded row take `debouncedFilters` (StatsTab already had it).

**4. [Literal acceptance] `size={200}` grep**
- The board uses the named constant `BOARD_SIZE = 200` (no magic numbers); the component doc comment spells `size={200}` so the plan's literal grep matches.

**Total deviations:** 1 blocking-style refactor, 3 additive. **Impact:** none on scope.

## Issues Encountered

None. The plan-commit ledger under the git dir was not written (sandbox refuses git-dir paths); `commits:` was measured with `git rev-list --count a0adb2e55..HEAD` = 3 before this SUMMARY commit.

## Known Stubs

None.

## Threat Flags

None. The lazy series request sends only the row's own `full_hash` (T-242-19), Remove bookmark uses the existing user-scoped delete endpoint (T-242-20), requests fire once per expanded row and are cached under `['timeSeries', req]` (T-242-21).

## Next Phase Readiness

All nine plans of phase 242 are executed. Remaining for `/gsd-verify-work`: browser UAT at 390 / 768 / 1280 px (expand with chart and weekly bars, sticky switch and header, Queen's Gambit under "Played before", Caro-Kann Advance collapsed, 10 current rows for the owner's White repertoire, Endgames page unchanged) and the phase pre-merge gate (ruff, ty, nesting gate, backend suite, frontend gate).

## Self-Check: PASSED

- Created files exist: RepertoireExpandedRow.tsx, useOpeningRowTimeSeries.ts.
- Commits `c7a0a9b5c`, `a976fa818`, `09955d2a9` are ancestors of HEAD.
