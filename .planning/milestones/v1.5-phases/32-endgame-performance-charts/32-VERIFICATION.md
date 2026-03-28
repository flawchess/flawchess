---
phase: 32-endgame-performance-charts
verified: 2026-03-26T20:08:08Z
status: human_needed
score: 11/11 automated must-haves verified
human_verification:
  - test: "Visual inspection of all five new chart sections on the Endgames Statistics sub-tab"
    expected: "Endgame Performance (WDL bars + gauges), Results by Endgame Type (existing), Conversion & Recovery (grouped bars), Win Rate Over Time (two lines), Win Rate by Endgame Type (six colored lines) appear in that order"
    why_human: "Chart rendering, layout correctness, gauge arc rendering, and mobile layout cannot be verified programmatically without a browser"
  - test: "Click-to-hide legend on Win Rate by Endgame Type chart"
    expected: "Clicking a legend item hides/shows the corresponding line"
    why_human: "Interactive state change requires browser interaction"
  - test: "Filter change propagation to all new charts"
    expected: "Changing time control or recency filter causes all five new sections to reload with filtered data"
    why_human: "React re-render triggered by state change cannot be verified statically"
  - test: "Mobile layout at 375px width"
    expected: "Charts are readable, gauges side by side, no overflow"
    why_human: "Responsive layout requires browser rendering at specific viewport"
---

# Phase 32: Endgame Performance Charts Verification Report

**Phase Goal:** Add endgame performance comparison charts: endgame vs non-endgame WDL, endgame strength gauge, and rolling-window timeline charts for overall and per-endgame-type win rates
**Verified:** 2026-03-26T20:08:08Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /api/endgames/performance returns endgame WDL, non-endgame WDL, gauge values, and aggregate conversion/recovery | VERIFIED | Router at line 93, service at line 449, all fields present in EndgamePerformanceResponse schema |
| 2 | GET /api/endgames/timeline returns rolling-window win rate series for overall and per-type | VERIFIED | Router at line 122, service at line 543, EndgameTimelineResponse schema confirmed |
| 3 | Both endpoints respect time_control, platform, recency, rated, opponent_type filters | VERIFIED | All 5 Query params present on both endpoints (lines 97-101, 126-130 in endgames.py); _apply_game_filters called in repository |
| 4 | Division by zero is handled gracefully (zero wins, zero games) | VERIFIED | `if overall_win_rate > 0 else 0.0` guard confirmed in service; 5 tests in TestGetEndgamePerformance including zero-games edge case; 47 unit tests pass |
| 5 | Endgame Performance section shows two side-by-side WDL comparison bars (endgame vs non-endgame) | VERIFIED | EndgamePerformanceSection.tsx WDLRow with data-testid="perf-wdl-endgame" and "perf-wdl-non-endgame" confirmed |
| 6 | Two semicircle gauge charts display Relative Endgame Strength and Endgame Skill | VERIFIED | EndgameGauge.tsx with strokeDasharray/strokeDashoffset; used in EndgamePerformanceSection with maxValue=150 and 100 |
| 7 | Grouped bar chart shows Conversion and Recovery percentages side by side for each endgame type | VERIFIED | EndgameConvRecovChart.tsx with ChartContainer, two Bar elements for conversion_pct and recovery_pct |
| 8 | All new sections appear in correct D-02 order on Statistics sub-tab | VERIFIED | Endgames.tsx line order: EndgamePerformanceSection (94) → EndgameWDLChart (97) → EndgameConvRecovChart (104) → EndgameTimelineChart (107) |
| 9 | Win Rate Over Time chart shows two lines: endgame and non-endgame rolling win rate | VERIFIED | EndgameTimelineChart.tsx Chart 1 with data-testid="timeline-overall-chart", two Line elements with connectNulls=true |
| 10 | Win Rate by Endgame Type chart shows up to 6 colored lines, one per endgame type | VERIFIED | EndgameTimelineChart.tsx Chart 2 with data-testid="timeline-per-type-chart", TYPE_COLORS mapping for all 6 types |
| 11 | Legend items are clickable to show/hide individual lines | VERIFIED | hiddenKeys state + handleLegendClick confirmed in EndgameTimelineChart.tsx lines 48, ChartLegendContent with hiddenKeys prop |

**Score:** 11/11 automated truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/schemas/endgames.py` | EndgamePerformanceResponse, EndgameTimelineResponse, EndgameWDLSummary, EndgameTimelinePoint, EndgameOverallPoint | VERIFIED | All 5 Pydantic models present at lines 85, 101, 119, 131, 146 |
| `app/repositories/endgame_repository.py` | query_endgame_performance_rows, query_endgame_timeline_rows | VERIFIED | Both async functions at lines 243, 309; asyncio.gather for concurrency |
| `app/services/endgame_service.py` | get_endgame_performance, get_endgame_timeline, _compute_rolling_series | VERIFIED | All three functions present at lines 449, 543, 414; named weight constants at lines 381-382 |
| `app/routers/endgames.py` | /endgames/performance and /endgames/timeline endpoints | VERIFIED | Both GET routes at lines 93, 122; window Query param with ge=5, le=200 |
| `tests/test_endgame_service.py` | TestGetEndgamePerformance, TestEndgameGaugeCalculations, TestGetEndgameTimeline | VERIFIED | All 5 test classes confirmed; 47 tests pass |
| `frontend/src/types/endgames.ts` | EndgamePerformanceResponse, EndgameWDLSummary, EndgameTimelineResponse, EndgameOverallPoint, EndgameTimelinePoint | VERIFIED | All 5 interfaces at lines 48, 58, 85, 76, 69 |
| `frontend/src/api/client.ts` | getPerformance, getTimeline methods | VERIFIED | getPerformance at line 147, getTimeline at line 164 |
| `frontend/src/hooks/useEndgames.ts` | useEndgamePerformance, useEndgameTimeline | VERIFIED | useEndgameTimeline at line 25, useEndgamePerformance at line 52 |
| `frontend/src/components/charts/EndgameGauge.tsx` | SVG semicircle gauge | VERIFIED | function EndgameGauge with strokeDasharray, Math.min(value/maxValue, 1) clamp, data-testid |
| `frontend/src/components/charts/EndgamePerformanceSection.tsx` | WDL bars + gauge charts | VERIFIED | WDLRow component, perf-wdl-endgame/perf-wdl-non-endgame/perf-gauges testids, EndgameGauge usage |
| `frontend/src/components/charts/EndgameConvRecovChart.tsx` | Grouped bar chart | VERIFIED | ChartContainer, two Bar elements, data-testid="conv-recov-chart", empty state |
| `frontend/src/components/charts/EndgameTimelineChart.tsx` | Two stacked timeline LineCharts | VERIFIED | timeline-overall-chart, timeline-per-type-chart testids, connectNulls, hiddenKeys |
| `frontend/src/pages/Endgames.tsx` | All sections wired in correct order | VERIFIED | All imports present, correct D-02 section order confirmed |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/routers/endgames.py` | `app/services/endgame_service.py` | get_endgame_performance, get_endgame_timeline | WIRED | Lines 111, 141 call service functions directly |
| `app/services/endgame_service.py` | `app/repositories/endgame_repository.py` | query_endgame_performance_rows, query_endgame_timeline_rows | WIRED | Lines 471, 564 call repo functions; results used to build response |
| `frontend/src/components/charts/EndgamePerformanceSection.tsx` | `/api/endgames/performance` | useEndgamePerformance hook | WIRED | Endgames.tsx uses hook at line 45 and passes data to component at line 95 |
| `frontend/src/components/charts/EndgameTimelineChart.tsx` | `/api/endgames/timeline` | useEndgameTimeline hook | WIRED | Endgames.tsx uses hook at line 46 and passes data to component at line 107 |
| `frontend/src/pages/Endgames.tsx` | EndgameConvRecovChart | import and render in statisticsContent | WIRED | Imported line 10, rendered line 104 with statsData.categories |
| `app/routers/endgames.py` | `app/main.py` | include_router | WIRED | main.py line 48: app.include_router(endgames_router, prefix="/api") |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| EndgamePerformanceSection | perfData (EndgamePerformanceResponse) | query_endgame_performance_rows → session.execute → fetchall() (repository line 302-306) | Yes — DB query with HAVING clause against game_positions | FLOWING |
| EndgameConvRecovChart | categories (EndgameCategoryStats[]) | Existing get_endgame_stats query (pre-existing, not new) | Yes — pre-existing DB query | FLOWING |
| EndgameTimelineChart | timelineData (EndgameTimelineResponse) | query_endgame_timeline_rows → asyncio.gather(8 queries) → fetchall() (repository line 386-399) | Yes — 8 concurrent DB queries with rolling window computation | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All schemas importable | `uv run python -c "from app.schemas.endgames import EndgamePerformanceResponse, EndgameTimelineResponse..."` | All imports OK | PASS |
| All endgame service tests pass | `uv run pytest tests/test_endgame_service.py -x -q` | 47 passed in 0.40s | PASS |
| Full backend test suite | `uv run pytest -x -q` | 446 passed, 32 warnings | PASS |
| Backend ruff lint | `uv run ruff check app/schemas/endgames.py app/repositories/endgame_repository.py app/services/endgame_service.py app/routers/endgames.py` | All checks passed! | PASS |
| TypeScript compilation | `cd frontend && npx tsc --noEmit` | No errors (exit 0) | PASS |
| Frontend production build | `cd frontend && npm run build` | Build succeeded, no errors | PASS |
| Frontend lint | `cd frontend && npm run lint` | 0 errors, 1 pre-existing warning (SuggestionsModal.tsx, unrelated) | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PERF-01 | 32-01, 32-02 | User can see side-by-side WDL comparison of endgame games vs non-endgame games | SATISFIED | EndgamePerformanceSection WDL bars wired to /api/endgames/performance; perf-wdl-endgame and perf-wdl-non-endgame testids confirmed |
| PERF-02 | 32-01, 32-02 | User can see a Relative Endgame Strength gauge (endgame win rate / overall win rate * 100) | SATISFIED | EndgameGauge with relative_strength value, maxValue=150; formula `endgame_win_rate / overall_win_rate * 100` in service |
| PERF-03 | 32-01, 32-02 | User can see an Endgame Skill gauge (0.6 * conversion_pct + 0.4 * recovery_pct) | SATISFIED | endgame_skill = 0.6 * conversion + 0.4 * recovery in service; rendered via EndgameGauge in EndgamePerformanceSection |
| PERF-04 | 32-02 | User can see conversion and recovery percentages side by side for each endgame type in a grouped bar chart | SATISFIED | EndgameConvRecovChart with two grouped Bars (conversion_pct, recovery_pct) per category, wired to statsData.categories |
| PERF-05 | 32-01, 32-03 | User can see rolling 50-game win rate timeline for endgame vs non-endgame games | SATISFIED | EndgameTimelineChart Chart 1 (timeline-overall-chart) with two connectNulls lines; window=50 default in service |
| PERF-06 | 32-01, 32-03 | User can see rolling 50-game win rate timeline broken down by endgame type | SATISFIED | EndgameTimelineChart Chart 2 (timeline-per-type-chart) with up to 6 colored lines from per_type data |
| PERF-07 | 32-01, 32-03 | All endgame performance charts respect existing filters (time control, platform, recency, rated, opponent) | SATISFIED | All 5 Query params on both backend endpoints; buildEndgameParams used in both frontend hooks |

No orphaned requirements — all PERF-01 through PERF-07 are accounted for in plan frontmatter and implemented.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| frontend/src/components/charts/EndgameConvRecovChart.tsx | 59 | `return null` in tooltip callback | Info | Standard Recharts tooltip guard — not a stub |
| frontend/src/components/charts/EndgameTimelineChart.tsx | 140, 205 | `return null` in tooltip callback | Info | Standard Recharts tooltip guard — not a stub |

No blockers or warnings. The `return null` occurrences are tooltip render guards — the surrounding code checks `!active || !payload?.length` which is the standard Recharts pattern for hiding empty tooltips.

### Human Verification Required

#### 1. Visual inspection of all five new chart sections

**Test:** Start dev servers (`uv run uvicorn app.main:app --reload` and `npm run dev`), log in, navigate to Endgames → Statistics tab. Verify five sections appear top-to-bottom in this order: "Endgame Performance" (WDL bars + gauges), "Results by Endgame Type" (existing chart, unchanged), "Conversion & Recovery by Endgame Type" (new grouped bars), "Win Rate Over Time" (two lines), "Win Rate by Endgame Type" (colored lines per type).
**Expected:** All five sections render with visible chart content (not blank) when the user has endgame game data. WDL bars show green/grey/red segments. Gauges show semicircle arcs with percentage labels. Grouped bars show two bars per endgame type. Timeline charts show lines over a date X-axis.
**Why human:** Chart rendering, SVG arc geometry, responsive layout, and Recharts rendering cannot be verified programmatically.

#### 2. Click-to-hide legend on per-type timeline

**Test:** On the "Win Rate by Endgame Type" chart, click a legend item (e.g. "Rook").
**Expected:** The corresponding line disappears from the chart. Click again — the line reappears.
**Why human:** Interactive state change triggered by click event requires browser interaction.

#### 3. Filter change propagation

**Test:** With all five new sections visible, change a filter (e.g., set time control to "Blitz only").
**Expected:** All new chart sections reload and update to show Blitz-only data. No sections remain stale.
**Why human:** React query invalidation on filter change cannot be verified without browser interaction.

#### 4. Mobile layout at 375px width

**Test:** Open browser dev tools, set viewport to 375px width, inspect all five new sections.
**Expected:** Gauge charts appear side by side (grid-cols-2), bar and line charts fill available width without horizontal overflow, text is legible.
**Why human:** Responsive rendering requires browser at specific viewport width.

### Gaps Summary

No gaps found. All automated checks pass: 446 backend tests, TypeScript compilation, production build, and lint all succeed. All 12 new backend/frontend artifacts exist, are substantive, are properly wired, and have real data flowing through the chain.

The only remaining items require human visual verification of chart rendering and interactive behavior in a browser.

---

_Verified: 2026-03-26T20:08:08Z_
_Verifier: Claude (gsd-verifier)_
