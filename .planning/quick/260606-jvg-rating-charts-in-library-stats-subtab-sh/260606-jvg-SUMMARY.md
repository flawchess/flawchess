---
quick_id: 260606-jvg
status: complete
date: 2026-06-06
---

# Quick Task 260606-jvg — Summary

## Task

Two frontend bugs in the Library > Stats subtab:

1. **Rating charts showed series with no data.** A user who never played bullet
   still saw a "Bullet" line/legend entry.
2. **"Results by Time Control" showed rows for disabled TCs.** Unchecking a TC in
   the filters did not remove its row.

## What changed (all frontend, client-side)

- **`frontend/src/components/stats/RatingChart.tsx`** — added a `tcsWithData` memo
  (TCs with ≥1 data point) and made `visibleTcs` the intersection of the
  enabled-TC filter and `tcsWithData`. `visibleTcs` drives the `<Line>` series, so
  the recharts legend payload (derived from rendered `<Line>` children) drops empty
  series automatically. The chart `config` is narrowed to `legendConfig` (visible
  series only) so the legend and generated `--color-*` CSS vars stay in sync. The
  Y-axis domain now derives from `visibleTcs` minus legend-hidden keys.
- **`frontend/src/components/stats/GlobalStatsCharts.tsx`** — added an
  `enabledTimeControls?: TimeControl[] | null` prop. The by-TC panel filters rows
  whose (lowercased) backend-title-cased label is not in the enabled set. `null`/
  `undefined` = all enabled. By-color panel untouched.
- **`frontend/src/pages/GlobalStats.tsx`** — passes
  `enabledTimeControls={filters.timeControls}` to `GlobalStatsCharts` (it already
  passed it to `RatingChart`).
- Tests: extended `RatingChart.test.tsx` (5 cases) and added
  `GlobalStatsCharts.test.tsx` (5 cases).

The backend `get_global_stats` still aggregates `by_time_control` across all
played TCs and never receives the `timeControls` filter, so the gating is
deliberately client-side (consistent with how `RatingChart` already handled the TC
filter in `da91ca66`).

## Gates

- `npm run lint` clean
- `npm test -- --run` — 756/756 (65 files); 15/15 in the two touched files
- `npm run build` clean
- `npm run knip` clean

## Orchestration note (important)

Claude Code's `isolation="worktree"` rooted the executor's worktree on a **stale
ancestor** (`9f5d5d37`, pre-`glq/hfy/io6`), missing `FlawStatsPanel`, the full
Stats-tab filter set, and `da91ca66`'s `enabledTimeControls` work. The bounded
cleanup helper correctly blocked with `base_mismatch`, and a cherry-pick
conflicted. Rather than merge the stale tree (which would have **deleted**
`FlawStatsPanel` and the recent filters from `GlobalStats.tsx`), the fixes were
**re-applied directly to current HEAD**, harvesting the executor's verified logic
and tests. The stale worktree and its branch were removed without merging. This is
the same CC worktree base-mismatch that bit 260606-hfy; consider
`workflow.use_worktrees=false` for quick tasks on this fast-moving phase branch.

## Commits (on `gsd/phase-107-...`, not pushed)

- `1c4aec92` fix: omit empty TC series and legend entries in RatingChart
- `48c72c1e` fix: gate Results-by-TC rows on the enabled-TC filter
- `06edac39` test: regression tests for TC-series omission and row filtering

## HUMAN-UAT pending

- Stats tab with a profile that never played a TC: that series absent from rating
  chart line + legend.
- Uncheck a TC in the Stats filter: its row disappears from "Results by Time
  Control" (and the rating-chart series too).
