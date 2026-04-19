---
phase: 55-time-pressure-performance-chart
verified: 2026-04-12T00:00:00Z
status: human_needed
score: 5/6 must-haves verified (6th requires visual confirmation)
overrides_applied: 0
human_verification:
  - test: "Open the Endgames page, navigate to the Stats tab, and scroll to the 'Time Pressure vs Performance' section"
    expected: "Two-line LineChart renders with a blue 'My score' line and a red 'Opponent's score' line across 10 time-remaining buckets (0%, 10%, …, 90% on X-axis), Y-axis from 0.0 to 1.0; tabs per time control appear when multiple time controls have data; hovering shows tooltip with bucket label, score (2 dp), and game counts; legend items toggle line visibility; dimmed dots appear on low-sample buckets"
    why_human: "Visual rendering, interactive behaviour (hover tooltip, legend toggle, tab switching), and responsive layout cannot be verified programmatically without a running browser"
---

# Phase 55: Time Pressure — Performance Chart Verification Report

**Phase Goal:** Users see a two-line comparison chart showing their score vs opponents' score across time pressure buckets at endgame entry, answering "do I crack under time pressure more than my opponents?" — tabbed by time control
**Verified:** 2026-04-12
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Line chart with X-axis = 10 equal-width time-remaining % buckets (0-10% through 90-100%), Y-axis = score (0.0 to 1.0) | VERIFIED | `EndgameTimePressureSection.tsx` L55-62: `XAxis dataKey="bucket_label"` with 10-bucket labels from `_build_bucket_series`; `YAxis domain={[0, 1]}` with ticks `[0, 0.2, 0.4, 0.6, 0.8, 1.0]` |
| 2 | Blue "My score" line = AVG(user_score) grouped by user's time bucket; Red "Opponent's score" line = AVG(1 - user_score) grouped by opponent's time bucket | VERIFIED | `_compute_time_pressure_chart` (endgame_service.py L809-896): separate `tc_user_buckets` and `tc_opp_buckets` accumulators; user_score `{win: 1.0, draw: 0.5, loss: 0.0}`; opp accumulates `1.0 - user_score`; `MY_SCORE_COLOR = 'oklch(0.55 0.18 260)'` (blue) and `OPP_SCORE_COLOR = WDL_LOSS` (red) in theme.ts |
| 3 | Chart is tabbed by time control; respects sidebar time control filter (single selection = no tabs, multiple = selected tabs only) | VERIFIED | Component: `data.rows.length === 1` → direct chart (L195), else Tabs (L209-227). Filter respected at DB level: `query_clock_stats_rows` calls `apply_game_filters` which filters `Game.time_control_bucket.in_(time_control)` — single filter → one row → no tabs |
| 4 | Individual data points backed by fewer than 10 games are dimmed; tabs with < 10 total endgame games are hidden | VERIFIED | Dot dimming: custom `dot` render prop on both Line components dims (`opacity=UNRELIABLE_OPACITY=0.5`) when `gameCount < MIN_GAMES_FOR_RELIABLE_STATS=10` (EndgameTimePressureSection.tsx L107-146). Tab hiding: `_compute_time_pressure_chart` filters `total_games < MIN_GAMES_FOR_CLOCK_STATS=10` (endgame_service.py L881) |
| 5 | Games without clock_seconds are excluded | VERIFIED | `_compute_time_pressure_chart` L859: `if time_control_seconds is None or time_control_seconds <= 0: continue`; also L855: `if user_clock is None or opp_clock is None: continue`. 12 unit tests in `TestComputeTimePressureChart` pass (including test_game_without_both_clocks_excluded, test_game_without_time_control_seconds_excluded) |
| 6 | Section appears in a new "Time Pressure vs Performance" container after the Clock Stats section | VERIFIED (code) / NEEDS HUMAN (visual) | Endgames.tsx L280-289: `timePressureChartData` block immediately follows `clockPressureData` block; single `statisticsContent` variable covers both desktop and mobile. Visual placement requires human confirmation. |

**Score:** 5/6 truths fully verifiable programmatically; 1 requires human visual confirmation

### Required Artifacts

| Artifact | Expected | Status | Details |
|---------|---------|--------|---------|
| `app/schemas/endgames.py` | TimePressureBucketPoint, TimePressureChartRow, TimePressureChartResponse schemas | VERIFIED | All 3 classes present (L260, L275, L292); `time_pressure_chart: TimePressureChartResponse` field added to EndgameOverviewResponse (L315) |
| `app/services/endgame_service.py` | `_compute_time_pressure_chart` pure function + `_build_bucket_series` helper | VERIFIED | Both functions present; NUM_BUCKETS=10, BUCKET_WIDTH_PCT=10 constants at L619-620; wired into `get_endgame_overview` at L1393 + L1402 |
| `tests/test_endgame_service.py` | Unit tests for bucket assignment, score averaging, edge cases | VERIFIED | `TestComputeTimePressureChart` class at L1331; 12 tests pass in 0.32s |
| `frontend/src/types/endgames.ts` | TimePressureBucketPoint, TimePressureChartRow, TimePressureChartResponse TS interfaces | VERIFIED | All 3 interfaces present (L149, L156, L164); `time_pressure_chart: TimePressureChartResponse` added to EndgameOverviewResponse (L175) |
| `frontend/src/lib/theme.ts` | MY_SCORE_COLOR and OPP_SCORE_COLOR constants | VERIFIED | `MY_SCORE_COLOR = 'oklch(0.55 0.18 260)'` (L58) and `OPP_SCORE_COLOR = WDL_LOSS` (L60) |
| `frontend/src/components/charts/EndgameTimePressureSection.tsx` | Chart component with tabs, Recharts LineChart, dim dots | VERIFIED | 229-line component; full LineChart with two Lines, custom dot render prop, ChartLegend toggle, InfoPopover header, tabs by time control, single-chart fallback, `connectNulls={true}` |
| `frontend/src/pages/Endgames.tsx` | Wiring of time_pressure_chart data to EndgameTimePressureSection | VERIFIED | Import at L26; `timePressureChartData = overviewData?.time_pressure_chart` at L138; render block at L285-289 with rows-length guard |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/services/endgame_service.py` | `app/schemas/endgames.py` | `TimePressureChartResponse` import | VERIFIED | L54-56: `TimePressureBucketPoint`, `TimePressureChartResponse`, `TimePressureChartRow` all imported |
| `endgame_service.py:get_endgame_overview` | `endgame_service.py:_compute_time_pressure_chart` | clock_rows passed directly | VERIFIED | L1393: `time_pressure_chart = _compute_time_pressure_chart(clock_rows)` |
| `frontend/src/pages/Endgames.tsx` | `EndgameTimePressureSection.tsx` | import and render with overviewData.time_pressure_chart | VERIFIED | L26: import; L138: data extraction; L287: `<EndgameTimePressureSection data={timePressureChartData} />` |
| `EndgameTimePressureSection.tsx` | `frontend/src/lib/theme.ts` | MY_SCORE_COLOR and OPP_SCORE_COLOR imports | VERIFIED | L13: `import { MIN_GAMES_FOR_RELIABLE_STATS, UNRELIABLE_OPACITY, MY_SCORE_COLOR, OPP_SCORE_COLOR } from '@/lib/theme'` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---------|--------------|--------|-------------------|--------|
| `EndgameTimePressureSection.tsx` | `data: TimePressureChartResponse` | `overviewData.time_pressure_chart` from `/api/endgames/overview` | Yes — `_compute_time_pressure_chart(clock_rows)` processes real DB-fetched clock rows from `query_clock_stats_rows`; each bucket score is AVG of real game results | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---------|---------|--------|--------|
| 12 unit tests for `_compute_time_pressure_chart` pass | `uv run pytest tests/test_endgame_service.py::TestComputeTimePressureChart -x -q` | 12 passed in 0.32s | PASS |
| ty check on backend files | `uv run ty check app/schemas/endgames.py app/services/endgame_service.py` | All checks passed | PASS |
| TypeScript compilation | `npx tsc --noEmit` | Zero errors | PASS |
| ESLint | `npm run lint` | No issues | PASS |
| Knip dead-export check | `npm run knip` | No dead exports | PASS |

### Requirements Coverage

No requirement IDs were declared for this phase (N/A per phase spec).

### Anti-Patterns Found

No blockers or stubs detected. The full implementation is substantive:

- No TODO/FIXME/placeholder comments in phase-55 files
- No empty returns (`return null` guarded by `data.rows.length === 0` is correct behaviour, not a stub)
- Initial `useState<Set<string>>(new Set())` for `hiddenKeys` is correct initial state, overwritten by user interaction
- Data flows from real DB query through service function to component

### Human Verification Required

#### 1. Visual and interactive verification of Time Pressure vs Performance chart

**Test:** Start the dev servers (`bin/run_local.sh`), log in with an account that has imported games, navigate to Endgames > Stats tab, scroll to "Time Pressure vs Performance" section.

**Expected:**
- Section header "Time Pressure vs Performance" with InfoPopover icon appears immediately after the Clock Stats section
- Two lines render: blue "My score" and red "Opponent's score"
- X-axis shows 10 bucket labels (0%, 10%, 20%, ..., 90%)
- Y-axis shows 0.0 to 1.0 with 0.2 tick intervals
- If multiple time controls have data: tabs (Bullet, Blitz, Rapid, Classical) appear above chart; switching tabs changes the data
- If only one time control has data: no tabs, chart renders directly
- Hovering a data point shows tooltip with bucket label (e.g. "30-40%"), score to 2 decimal places, and game count for each line
- Clicking legend items toggles line visibility
- Buckets with fewer than 10 games have dimmer/faded dots
- Responsive layout works at mobile viewport widths

**Why human:** Visual rendering, interactive hover/click behaviour, and responsive layout cannot be verified programmatically without a browser.

### Gaps Summary

No gaps blocking goal achievement. All code artifacts exist, are substantive, are wired correctly, and data flows through the full pipeline from DB query to chart rendering. The sole outstanding item is human visual confirmation of the rendered chart.

---

_Verified: 2026-04-12T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
