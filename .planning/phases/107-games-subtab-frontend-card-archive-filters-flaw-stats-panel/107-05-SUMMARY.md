---
phase: 107-games-subtab-frontend-card-archive-filters-flaw-stats-panel
plan: 05
subsystem: ui
tags: [react, typescript, recharts, tailwind, library-page, flaw-stats]

# Dependency graph
requires:
  - phase: 107-01
    provides: D-01 backend (miss_rate/lucky_escape_rate/while_ahead_rate on TagDistribution)
  - phase: 107-02
    provides: theme.ts SEV_*/FAM_*/PHASE_* constants; TagChip/SeverityBadge primitives
provides:
  - FlawStatsBand: four severity-rate cells (B/M/I per-game/per-100 toggle + Result-changing)
  - FlawTrendChart: Recharts blunders/game rolling trend with empty fallback
  - FlawTagDistribution: tempo stacked bar (with unmeasured remainder) + phase histogram + Opportunity/Impact bars from D-01 rate fields
  - FlawStatsPanel: panel shell composing all three zones with toggle, denominator pill, isError branch
affects:
  - 107-07 (GamesTab wires useLibraryFlawStats into FlawStatsPanel)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Recharts AreaChart on charcoal: SEV_BLUNDER stroke 2.5 + linearGradient 32%->0, no CartesianGrid, isAnimationActive=false"
    - "Normalization toggle as local React state (no re-fetch) driving only display values"
    - "Honest unmeasured remainder in stacked bar: totalMbFlaws - sum(tempo counts), omit only when zero"
    - "D-01 rate fields rendered directly (miss_rate/lucky_escape_rate/while_ahead_rate) — no client-side derivation"

key-files:
  created:
    - frontend/src/components/library/FlawStatsBand.tsx
    - frontend/src/components/library/FlawTrendChart.tsx
    - frontend/src/components/library/FlawTagDistribution.tsx
    - frontend/src/components/library/FlawStatsPanel.tsx
  modified: []

key-decisions:
  - "Placed data-testid=flaw-trend-chart on the outer container div (always visible), not on ChartContainer (only shown with >=2 points)"
  - "Tempo unmeasured segment: width = totalMbFlaws - sum(tempo counts); omitted only when zero (not normalized to 100%)"
  - "FlawStatsPanel uses IIFE pattern for content block to avoid repeated isError/isLoading guards"
  - "windowSize derived from first trend point (all share same window_size); falls back to 20 when trend is empty"

patterns-established:
  - "Rate bar row: 3-col grid [label | track | value] with oklch(1 0 0 / 7%) bg track"
  - "Sub-columns: flex-col mobile (no sm: prefix) → grid-cols-3 desktop (sm:grid sm:grid-cols-3)"

requirements-completed: [LIBG-03]

# Metrics
duration: 4min
completed: 2026-06-06
---

# Phase 107 Plan 05: Flaw-Stats Panel Summary

**Four-component Flaw-Stats panel: per-severity band with per-game/per-100 toggle, Recharts blunders/game trend, tempo stacked bar with honest unmeasured remainder, and Opportunity/Impact bars rendered directly from D-01 TagDistribution rate fields**

## Performance

- **Duration:** 4 min
- **Started:** 2026-06-05T22:17:50Z
- **Completed:** 2026-06-06T00:21:54Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- `FlawStatsBand`: Four flex cells (Blunders/Mistakes/Inaccuracies in SEV_* colors + Result-changing in FAM_IMPACT). Per-game/per-100 toggle switches displayed values and label suffix from one response object — no re-fetch. `analyzedEmpty` prop renders "—" for all rate cells.
- `FlawTrendChart`: Recharts `AreaChart` with SEV_BLUNDER stroke (2.5) + linearGradient fill (32%→0 opacity), no CartesianGrid, `isAnimationActive={false}`. Fewer than 2 trend points shows "Not enough games to show a trend" fallback inside the same charcoal container.
- `FlawTagDistribution`: Tempo stacked bar with `low-clock`/`impatient`/`considered` segments plus an `FAM_TEMPO_UNMEASURED` remainder (`totalMbFlaws − sum(tempo counts)`), omitted only when zero (honest gap, never normalized). Phase histogram uses PHASE_* fills. Opportunity column reads `miss_rate` + `lucky_escape_rate` from D-01 fields; Impact column reads `while_ahead_rate` + `result_changing_rate` — all from real backend fields, no placeholders (D-03).
- `FlawStatsPanel`: `<section aria-label="Flaw statistics">` shell composing all three zones. Local normalization state drives the band with no re-fetch. Denominator pill shows `{pct}% analyzed · N = {n}` with brand-brown-highlight values; `analyzed_n === 0` shows "No analyzed games in the current filter". `isError` renders the exact CLAUDE.md error copy without falling through to empty state.

## Task Commits

1. **Task 1: FlawStatsBand + FlawTrendChart (Zone 1 + Zone 2)** - `ba6fb246` (feat)
2. **Task 2: FlawTagDistribution — tempo bar, phase histogram, Opportunity/Impact (D-03)** - `bf334cbc` (feat)
3. **Task 3: FlawStatsPanel shell — toggle + denominator + isError + three zones** - `5a2e7bfd` (feat)

## Files Created/Modified

- `frontend/src/components/library/FlawStatsBand.tsx` — Zone 1: four severity-rate cells with normalization toggle support
- `frontend/src/components/library/FlawTrendChart.tsx` — Zone 2: Recharts AreaChart trend with SEV_BLUNDER gradient + empty fallback
- `frontend/src/components/library/FlawTagDistribution.tsx` — Zone 3: tempo stacked bar + phase histogram + D-01 Opportunity/Impact bars
- `frontend/src/components/library/FlawStatsPanel.tsx` — Panel shell composing all three zones; toggle/denominator/isError/loading states

## Decisions Made

- `data-testid="flaw-trend-chart"` placed on the outer `<div>` container (always rendered), not on `ChartContainer` which is conditionally rendered only for 2+ trend points. This ensures test selectors work in all states.
- Tempo unmeasured remainder computed as `totalMbFlaws - sum(tempo counts)` and included as a distinct segment rather than normalizing measured segments to 100%. This makes the bar honest about clock-data gaps.
- `windowSize` derived from `stats.trend[0]?.window_size` with a fallback of 20 when trend is empty — avoids a separate prop while handling the zero-analyzed-games case gracefully.
- Sub-column responsive layout: `flex flex-col gap-3 mt-3 sm:grid sm:grid-cols-3 sm:gap-2` — mobile stacks, desktop grids, no conflicting utility classes.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. TypeScript and ESLint both clean after initial write. All 744 existing frontend tests pass.

## Known Stubs

None. All four D-01 rate fields (`miss_rate`, `lucky_escape_rate`, `while_ahead_rate`, `result_changing_rate`) are rendered directly from real backend data. No placeholder copy or "coming soon" text.

## Threat Flags

None. All values render as React children (auto-escaped). No `dangerouslySetInnerHTML`. Division-by-zero guard on `totalMbFlaws` and `phaseTotal` prevents T-107-08. No new network endpoints.

## Next Phase Readiness

`FlawStatsPanel` is the public export. GamesTab (Plan 07) imports it and wires `useLibraryFlawStats` — knip will clear its "unused file" warning once that wiring is in place (expected, per plan verification note).

## Self-Check: PASSED

- FlawStatsBand.tsx: FOUND
- FlawTrendChart.tsx: FOUND
- FlawTagDistribution.tsx: FOUND
- FlawStatsPanel.tsx: FOUND
- Commit ba6fb246: FOUND
- Commit bf334cbc: FOUND
- Commit 5a2e7bfd: FOUND

---
*Phase: 107-games-subtab-frontend-card-archive-filters-flaw-stats-panel*
*Completed: 2026-06-06*
