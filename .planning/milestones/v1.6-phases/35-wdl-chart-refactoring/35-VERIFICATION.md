---
phase: 35-wdl-chart-refactoring
verified: 2026-03-28T14:36:00Z
status: passed
score: 8/8 must-haves verified
re_verification: false
---

# Phase 35: WDL Chart Refactoring — Verification Report

**Phase Goal:** All WDL charts (except move list) use a single shared component, eliminating inconsistent custom and Recharts implementations
**Verified:** 2026-03-28T14:36:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                          | Status     | Evidence                                                                        |
|----|-----------------------------------------------------------------------------------------------|------------|---------------------------------------------------------------------------------|
| 1  | A shared WDL chart row component exists with stacked bar, optional label, optional game count bar, optional games link, and WDL legend text | ✓ VERIFIED | `WDLChartRow.tsx` (159 lines) implements all features per spec                  |
| 2  | WDLBar is reimplemented as a thin wrapper over WDLChartRow                                    | ✓ VERIFIED | `WDLBar.tsx` is 10 lines; imports WDLChartRow and passes `barHeight="h-6"`      |
| 3  | Results by Time Control and Results by Color use WDLChartRow rows, not Recharts               | ✓ VERIFIED | `GlobalStatsCharts.tsx` has no recharts/ChartContainer/BarChart; uses WDLChartRow with maxTotal |
| 4  | Results by Opening uses WDLChartRow rows with game count bars and WDL legend text             | ✓ VERIFIED | `Openings.tsx` imports WDLChartRow; Statistics tab renders inline WDLChartRow rows with colorPrefix labels |
| 5  | EndgameWDLChart uses WDLChartRow for its per-category bars                                    | ✓ VERIFIED | `EndgameWDLChart.tsx` delegates to WDLChartRow in `EndgameCategoryRow`; no WDL_WIN/DRAW/LOSS/GLASS_OVERLAY usage |
| 6  | Endgame Performance WDL rows use WDLChartRow                                                  | ✓ VERIFIED | `EndgamePerformanceSection.tsx` uses two WDLChartRow calls; no internal WDLRow function |
| 7  | WDLBarChart.tsx is deleted                                                                    | ✓ VERIFIED | File does not exist; `grep -r "WDLBarChart" src/` returns no results            |
| 8  | No Recharts BarChart imports remain in WDL-related files                                      | ✓ VERIFIED | GlobalStatsCharts.tsx has no recharts import; remaining recharts usage is in non-WDL charts (line charts, gauge) |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/types/charts.ts` | WDLRowData interface | ✓ VERIFIED | Exports `WDLRowData` with all 7 fields (wins, draws, losses, total, win_pct, draw_pct, loss_pct) |
| `frontend/src/components/charts/WDLChartRow.tsx` | Shared WDL chart row component | ✓ VERIFIED | 159 lines; exports `WDLChartRow`; all optional features implemented |
| `frontend/src/components/results/WDLBar.tsx` | WDLBar reimplemented via WDLChartRow | ✓ VERIFIED | 10 lines; thin wrapper with `barHeight="h-6"` |
| `frontend/src/components/stats/GlobalStatsCharts.tsx` | WDLChartRow for Time Control and Color | ✓ VERIFIED | Contains WDLChartRow, maxTotal computation, data-testid on rows container |
| `frontend/src/pages/Openings.tsx` | WDLChartRow for Results by Opening | ✓ VERIFIED | Imports WDLChartRow; contains colorPrefix label computation; "Results by Opening" heading |
| `frontend/src/components/charts/EndgameWDLChart.tsx` | WDLChartRow for endgame type rows | ✓ VERIFIED | EndgameCategoryRow delegates to WDLChartRow; no WDL_WIN/DRAW/LOSS inline |
| `frontend/src/components/charts/EndgamePerformanceSection.tsx` | WDLChartRow for endgame/non-endgame WDL rows | ✓ VERIFIED | Two WDLChartRow usages; no internal WDLRow function |
| `frontend/src/components/charts/WDLBarChart.tsx` | Must NOT exist (deleted) | ✓ VERIFIED | File confirmed deleted; no references remain |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `WDLChartRow.tsx` | `types/charts.ts` | `import WDLRowData` | ✓ WIRED | Line 13: `import type { WDLRowData } from '@/types/charts'` |
| `WDLChartRow.tsx` | `lib/theme.ts` | `import WDL_WIN, WDL_DRAW, WDL_LOSS, GLASS_OVERLAY, MIN_GAMES_FOR_RELIABLE_STATS, UNRELIABLE_OPACITY` | ✓ WIRED | Lines 5–12: all 6 constants imported and used |
| `WDLBar.tsx` | `WDLChartRow.tsx` | `import WDLChartRow` | ✓ WIRED | Line 1: `import { WDLChartRow } from '@/components/charts/WDLChartRow'`; used on line 9 |
| `GlobalStatsCharts.tsx` | `WDLChartRow.tsx` | `import WDLChartRow` | ✓ WIRED | Line 2: `import { WDLChartRow }`; used in WDLCategoryChart render |
| `Openings.tsx` | `WDLChartRow.tsx` | `import WDLChartRow` | ✓ WIRED | Line 42: `import { WDLChartRow }`; used in Statistics tab rows render |
| `EndgameWDLChart.tsx` | `WDLChartRow.tsx` | `import WDLChartRow` | ✓ WIRED | Line 2: `import { WDLChartRow }`; used in EndgameCategoryRow |
| `EndgamePerformanceSection.tsx` | `WDLChartRow.tsx` | `import WDLChartRow` | ✓ WIRED | Line 9: `import { WDLChartRow }`; used twice for endgame/non-endgame WDL bars |

### Data-Flow Trace (Level 4)

All WDL chart consumers receive data from parent components that source from API queries. No consumers hardcode empty arrays or static WDL values at call sites.

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `GlobalStatsCharts.tsx` | `byTimeControl`, `byColor` | Props from parent (GlobalStats page, API-sourced) | Yes — passed from TanStack Query results | ✓ FLOWING |
| `Openings.tsx` (Statistics tab) | `wdlStatsMap`, `bookmarks` | API queries in component | Yes — computed from fetched stats; pct computed inline | ✓ FLOWING |
| `EndgameWDLChart.tsx` | `categories` | Props from Endgames page (API-sourced) | Yes — EndgameCategoryStats from backend | ✓ FLOWING |
| `EndgamePerformanceSection.tsx` | `data.endgame_wdl`, `data.non_endgame_wdl` | Props from Endgames page (API-sourced) | Yes — EndgamePerformanceResponse from backend | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| TypeScript compiles with no errors | `npx tsc --noEmit` | No output (clean) | ✓ PASS |
| Production build succeeds | `npm run build` | Build completes, PWA assets generated | ✓ PASS |
| Lint passes | `npm run lint` | 0 errors; 1 pre-existing unrelated warning in SuggestionsModal.tsx | ✓ PASS |
| All tests pass | `npm test` | 38/38 tests passing | ✓ PASS |
| WDLBarChart fully removed | `grep -r "WDLBarChart" src/` | No results | ✓ PASS |
| GlobalStatsCharts has no recharts | `grep "from 'recharts'" GlobalStatsCharts.tsx` | No results | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| WDL-01 | 35-01 | A shared WDL chart component exists with configurable title, games link, and optional game count bar | ✓ SATISFIED | `WDLChartRow.tsx` implements all these features with `label`, `gamesLink`, `maxTotal` props |
| WDL-02 | 35-02 | All WDL charts across the app (Results by Time Control, Results by Color, Results by Opening, endgame type charts) use the shared component — except the moves list in the Moves tab | ✓ SATISFIED | All 5 chart locations (Time Control, Color, Opening, Endgame Type, Endgame Performance) use WDLChartRow |
| WDL-03 | 35-02 | No unused WDL-related constants, CSS classes, or Recharts bar chart code remains | ✓ SATISFIED | WDLBarChart.tsx deleted; Recharts BarChart removed from GlobalStatsCharts.tsx; WDL_WIN/DRAW/LOSS/GLASS_OVERLAY removed from all consumers (only in WDLChartRow itself) |
| WDL-04 | 35-01, 35-02 | Visual appearance of all WDL charts matches the current endgame type WDL charts (glass overlay, inline legend, game count bars) | ✓ SATISFIED | WDLChartRow uses GLASS_OVERLAY backgroundImage, inline WDL legend text with color spans, grey-outlined proportional game count bar |

All 4 requirement IDs from plans are accounted for. No orphaned requirements found.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `SuggestionsModal.tsx` | 26 | Pre-existing `useEffect` dependency warning | ℹ️ Info | Pre-existing, out of phase scope; no impact on WDL charts |

No anti-patterns found in phase 35 modified files. No TODO/FIXME/placeholder comments in new or modified files. No hardcoded empty return values in WDL rendering paths.

### Human Verification Required

#### 1. Visual Consistency — All Charts Match Endgame Reference

**Test:** Visit the live app. Navigate to Global Stats page (Results by Time Control, Results by Color), Openings Statistics tab (Results by Opening), and Endgames page (Results by Endgame Type, Endgame Performance). Compare all WDL chart rows visually.
**Expected:** All 5 chart locations show identical row style: glass-overlay stacked bar, proportional grey game count bar, inline colored W/D/L legend text. Charts with small samples show dimmed bars and "(low)" warning.
**Why human:** Visual consistency and glass overlay rendering cannot be verified programmatically from source code alone.

#### 2. WDLBar in Dashboard and Openings Explorer — Unchanged Appearance

**Test:** Navigate to the Dashboard (overall stats card) and the Openings Explorer (move candidate list). Verify WDLBar rows still render correctly with h-6 height.
**Expected:** WDL bars in the dashboard stats card and move explorer look the same as before the refactoring.
**Why human:** The h-6 vs h-5 height difference and visual regression from the WDLBar wrapper change can only be confirmed by looking at the rendered UI.

### Gaps Summary

No gaps found. All phase goals are achieved.

---

_Verified: 2026-03-28T14:36:00Z_
_Verifier: Claude (gsd-verifier)_
