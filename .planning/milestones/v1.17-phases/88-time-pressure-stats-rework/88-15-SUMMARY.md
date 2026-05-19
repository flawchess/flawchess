---
phase: 88-time-pressure-stats-rework
plan: 15
subsystem: endgame-analytics
tags: [endgame-analytics, time-pressure, scope-amendment, schema-additive, line-chart, A-2]
requires: [88-13, 88-14]
provides:
  - clock-diff-timeline-payload-on-overview
  - average-clock-difference-over-time-line-chart
affects:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - frontend/src/types/endgames.ts
  - frontend/src/components/charts/EndgameClockDiffOverTimeChart.tsx
  - frontend/src/components/charts/__tests__/EndgameClockDiffOverTimeChart.test.tsx
  - frontend/src/pages/Endgames.tsx
  - tests/services/test_time_pressure_service.py
  - tests/test_endgame_service.py
  - tests/services/test_insights_service_series.py
  - CHANGELOG.md
tech-stack:
  added: []
  patterns:
    - "Two-phase single-pass aggregator (collect eligible + per-week counts, then rolling-window walk)"
    - "ISO-Monday bucketing with overwrite-on-week (last game of week wins)"
    - "PERCENT units end-to-end (backend × 100, chart Y in percent, NEUTRAL_PCT_THRESHOLD in percent — NO conversion at chart layer)"
    - "Volume-bar yAxisId trick (domain=[0, barMax*5]) pinning bars to bottom 20% of canvas"
key-files:
  created:
    - frontend/src/components/charts/EndgameClockDiffOverTimeChart.tsx
    - frontend/src/components/charts/__tests__/EndgameClockDiffOverTimeChart.test.tsx
  modified:
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - frontend/src/types/endgames.ts
    - frontend/src/pages/Endgames.tsx
    - tests/services/test_time_pressure_service.py
    - tests/test_endgame_service.py
    - tests/services/test_insights_service_series.py
    - CHANGELOG.md
decisions:
  - "Aggregator runs as a separate single-pass over clock_rows, NOT inside _iterate_clock_rows. Different filter semantics (pooled across TCs vs per-TC) and different output shape (chronological points vs TC buckets) make a shared pass awkward. Cost is one extra O(N) iteration over the same row stream — no new DB query."
  - "ISO Monday bucketing emits ONE point per week using the rolling-mean of the LAST eligible game of the week. Achieved cheaply by overwriting `week_to_rolling[monday]` on every eligible row — the last write wins because rows are sorted ASC by played_at."
  - "Unit lock (B-5): NEUTRAL_PCT_THRESHOLD = 5.0 (percent), chart Y-axis = [-30, 30] (percent), backend avg_clock_diff_pct = `(user-opp)/base * 100` (percent). All three in the same unit — no conversion at any layer. The plan explicitly called this out and the percent-units test (test_percent_units_not_fraction) pins it."
  - "Line color: MY_SCORE_COLOR from @/lib/theme (no new CLOCK_DIFF_LINE_COLOR constant). LOCKED per user decision 2026-05-17."
  - "Chart position: below cards grid, above SectionInsightSlot. LOCKED per user decision 2026-05-17."
  - "ClockStatsRow left alone — separate hygiene pass. LOCKED per user decision 2026-05-17."
metrics:
  duration_minutes: 18
  completed_date: 2026-05-17
---

# Phase 88 Plan 15: Restored Average Clock Difference over Time Line Chart Summary

Restored the line chart deleted by the Phase 88-07 cleanup, fulfilling the user-approved scope amendment in §2 of `88-CONTEXT.md` (A-2). The bullet-card grid from 88-01..88-12 stays the primary surface; this plan adds the line chart back alongside as a complementary trend view that the snapshot-only cards cannot show.

## What Shipped

**Backend schema (`app/schemas/endgames.py`):**

- Deleted orphan `ClockPressureTimelinePoint` and `ClockPressureResponse` after grep-confirming zero live consumers (the only remaining references are pure comments in `insights_service.py`, `insights_llm.py`, `test_insights_service_series.py`, and `test_endgame_service.py` — all documenting the historical migration).
- Added `ClockDiffTimelinePoint` (4 fields: `date`, `avg_clock_diff_pct`, `game_count`, `per_week_game_count`) and `ClockDiffTimelineResponse(points: list[ClockDiffTimelinePoint])`. Fresh names (vs the pre-88-07 timeline classes) make the design-pivot history obvious without bringing back the deleted class name.
- `EndgameOverviewResponse` gains `clock_diff_timeline: ClockDiffTimelineResponse` adjacent to `time_pressure_cards`. No Pydantic default — call sites must pass it (one external test fixture updated in this plan).

**Backend service (`app/services/endgame_service.py`):**

- Reintroduced `CLOCK_PRESSURE_TIMELINE_WINDOW: int = 100` (removed in 88-09 IN-01). Comment explicitly links back to that sweep and the 88-15 restore.
- New `_compute_clock_diff_timeline(clock_rows, window=100) -> ClockDiffTimelineResponse`. Two-phase single-pass aggregator:
  1. Phase 1: collect eligible `(played_at, clock_diff_pct)` tuples + per-week raw counts. Eligibility predicate mirrors `_iterate_clock_rows` exactly (TC bucket non-null, base_time_seconds > 0, both clocks present via `_extract_entry_clocks`, both clocks within `MAX_CLOCK_PCT_OF_BASE`, `played_at` non-null). `clock_diff_pct = (user_clock - opp_clock) / base_time_seconds * 100` — PERCENT units, locked by the dedicated test.
  2. Phase 2: sort ASC by `played_at`, then rolling-window walk. ISO Monday bucketing with overwrite-on-week (last game wins).
  3. Phase 3: emit chronologically.
- `compose_endgame_overview` calls `_compute_clock_diff_timeline(clock_rows)` after `_compute_time_pressure_cards` and threads the result into `EndgameOverviewResponse(...)`.

**Frontend types (`frontend/src/types/endgames.ts`):** TS mirrors the backend additions — `ClockDiffTimelinePoint`, `ClockDiffTimelineResponse`, and the new `clock_diff_timeline` field on `EndgameOverviewResponse`.

**Frontend chart component (`frontend/src/components/charts/EndgameClockDiffOverTimeChart.tsx`):** New file. Recharts `ComposedChart` with:

- **Line** for `avg_clock_diff_pct` (color `MY_SCORE_COLOR`, dots with radius 3).
- **Bar** for `per_week_game_count` on a hidden right Y axis (`yAxisId="bars"`, domain `[0, barMax * 5]` — pins bars to bottom 20% of canvas, same trick as `EndgameScoreOverTimeChart`).
- **Two ReferenceArea bands**: `[NEUTRAL_PCT_THRESHOLD, 30]` filled with `ZONE_SUCCESS` and `[-30, -NEUTRAL_PCT_THRESHOLD]` filled with `ZONE_DANGER`, both at 0.15 opacity. Neutral middle stays unshaded.
- **ReferenceLine** at `y=0` (dashed, 0.4 opacity).
- **Fixed Y domain** `[-30, 30]` with ticks at every 10 points, percent-formatted.
- **InfoPopover** with the chart explainer (rolling 100-game average, what the bars represent, sign convention).
- **ChartTooltip** showing the week, signed rolling avg with trailing-window size, and this-week game count.
- **Empty handling**: returns `null` if `timeline.length === 0` (belt-and-suspenders — page-level integration also guards).
- **Mobile**: `useIsMobile()` hook adjusts left margin on the chart container at the 768px breakpoint, mirroring `EndgameScoreOverTimeChart`.
- **Accessibility**: chart container has `role="img"` and `aria-label="Average clock difference over time"`.

**Endgames page integration (`frontend/src/pages/Endgames.tsx`):** Chart wired between `EndgameTimePressureSection` and `SectionInsightSlot`. Derived `clockDiffTimelineData` + `showClockDiffTimeline` guards on `points.length > 0`. Chart sits in its own `charcoal-texture rounded-md p-4` wrap, matching the per-component card chrome convention used by the score-over-time and ELO timeline charts elsewhere on the page.

**Tests:**

- Backend: `TestComputeClockDiffTimeline` (6 tests: empty rows, single-game, multi-week rolling window, ineligibility filter, ISO-week last-game emission, percent units unit-lock). `TestGetEndgameOverview.test_overview_composes_all_payloads` extended to assert `clock_diff_timeline` is a `ClockDiffTimelineResponse` instance with `points == []`.
- Frontend: `EndgameClockDiffOverTimeChart.test.tsx` (6 tests: empty timeline returns null, container/title render, one bar per timeline entry, Y-axis ticks at −30/0/+30, InfoPopover trigger ARIA label, two ReferenceArea band rects).

**CHANGELOG.md:** One bullet under `[Unreleased] → Added` reflecting the honest "restored after deletion" framing.

## Units Decision (Documented per Plan)

The plan explicitly called out the units conundrum as a B-5 lock. Pinned values:

| Layer | Units | Value |
|---|---|---|
| Backend `avg_clock_diff_pct` | percent | `(user_clock - opp_clock) / base_time_seconds * 100` (e.g. 50.0) |
| `NEUTRAL_PCT_THRESHOLD` (codegen) | percent | 5.0 |
| Chart Y axis | percent | `[-30, 30]` |
| ReferenceArea bands | percent | `y1=NEUTRAL_PCT_THRESHOLD`, `y2=30` (and mirrored on the negative side) |

All four in the same unit — **NO conversion at any layer**. Multiplying or dividing by 100 anywhere would render the band invisible (at y=0.05) or off-chart (at y=500). The dedicated `test_percent_units_not_fraction` test pins this with a fixture computing 50.0 (PERCENT) from a `user=600s, opp=300s, base=600s` input.

## Orphan Schemas Deleted

`grep -rnE "ClockPressureTimelinePoint|ClockPressureResponse" app/ frontend/src/ tests/` confirmed zero non-comment consumers before deletion. Surviving references are all comments documenting the migration (in `insights_service.py`, `insights_llm.py`, `test_insights_service_series.py`, `test_endgame_service.py`, `frontend/src/types/endgames.ts`). After deletion, `grep -c "ClockPressureTimelinePoint\|ClockPressureResponse" app/schemas/endgames.py` returns 0.

`ClockStatsRow` (lines 436-458 of `app/schemas/endgames.py`) was left alone per the plan and the user's LOCKED decision (2026-05-17, Q3) — separate hygiene pass.

## Deviations from Plan

None of substance. Two minor in-stride adjustments:

- The plan said "extend the existing `tests/test_endgame_service.py` `compose_endgame_overview` test(s)". I extended `test_overview_composes_all_payloads` only (the other compose test, `test_overview_passes_window_to_timeline`, doesn't read response fields so the additive change wasn't needed there).
- The plan said "update any existing `EndgameOverviewResponse(...)` test fixtures that construct the response by hand". Only one external constructor exists (in `tests/services/test_insights_service_series.py`); I updated it. The plan's `from app.schemas.endgames import (...)` block grew a `ClockDiffTimelineResponse` import there for consistency.

The plan called for "5 new frontend tests" — I shipped 6 (the 5 specified plus a sanity assertion that the chart container renders with its title for non-empty input; without it, the other 4 assertions all depend on the not-null-rendering precondition without proving it). All 6 are green.

## HUMAN-UAT Items Introduced

This plan adds 3 new human-UAT items for Phase 88 re-verification:

1. **Real-data render correctness at various data densities** — sparse 5-week history, dense year-long history, recency-cutoff edges. Verify the chart hides cleanly when no clock-eligible game exists in the filtered set (e.g. on a fresh import with no endgames yet).
2. **Tooltip readability on mobile (375px viewport)** — confirm the chart tooltip doesn't overflow horizontally and the volume-bar density at the bottom 20% of canvas stays legible on small screens.
3. **ARIA accessible-name on screen reader** — confirm a screen reader announces "Average clock difference over time" when focus enters the chart region (via the `role="img"` + `aria-label` on the chart container).

The 4 prior human-UAT items in `88-HUMAN-UAT.md` (responsive grid, sparse-bin rendering, popover at 375px, screen reader on cards) remain valid.

## Phase 88 §2 Status After This Plan

| Ask | Plan | Status |
|---|---|---|
| A-1 (separate per-TC containers) | 88-13 | Done |
| A-2 (restored line chart) | **88-15** | **Done (this plan)** |
| A-3 (card top-zone summary stats) | 88-14 | Done |
| A-4 (qualitative quintile labels + Q4 hidden) | 88-13 | Done |
| A-5 (±30% quintile bullet axis) | 88-13 | Done |

All five §2 asks shipped. Phase 88 re-verification can now run.

## Self-Check: PASSED

**Files claimed:**

- `app/schemas/endgames.py` — FOUND; `ClockDiffTimelinePoint` + `ClockDiffTimelineResponse` defined; `clock_diff_timeline` field on `EndgameOverviewResponse`; orphans deleted (`grep -c "ClockPressureTimelinePoint\|ClockPressureResponse" app/schemas/endgames.py` = 0).
- `app/services/endgame_service.py` — FOUND; `_compute_clock_diff_timeline` defined (`grep -c "_compute_clock_diff_timeline" app/services/endgame_service.py` = 2); `CLOCK_PRESSURE_TIMELINE_WINDOW` reintroduced (`grep -c` = 3); composition wired.
- `frontend/src/types/endgames.ts` — FOUND; `ClockDiffTimelinePoint` (`grep -c` = 2); new field on `EndgameOverviewResponse`.
- `frontend/src/components/charts/EndgameClockDiffOverTimeChart.tsx` — FOUND; `EndgameClockDiffOverTimeChart` exported; `data-testid="clock-diff-over-time-chart"` present.
- `frontend/src/components/charts/__tests__/EndgameClockDiffOverTimeChart.test.tsx` — FOUND; 6 tests.
- `frontend/src/pages/Endgames.tsx` — FOUND; chart imported + rendered conditionally (`grep -c "EndgameClockDiffOverTimeChart"` = 2; `grep -c "clock_diff_timeline"` = 1).
- `tests/services/test_time_pressure_service.py` — FOUND; `TestComputeClockDiffTimeline` class with 6 tests.
- `tests/test_endgame_service.py` — FOUND; `test_overview_composes_all_payloads` asserts new field.
- `tests/services/test_insights_service_series.py` — FOUND; fixture updated with `clock_diff_timeline=`.
- `CHANGELOG.md` — FOUND; bullet under `[Unreleased] → Added` (`grep -c "Average Clock Difference over Time"` = 1).

**Commits present in git log:**

- `62ea4744` test(88-15): add failing tests for clock-diff timeline aggregator (RED) — FOUND.
- `4e8a3e27` feat(88-15): restore clock-diff timeline aggregator + schema (GREEN) — FOUND.
- `59432725` test(88-15): add failing tests for clock-diff line chart + TS types (RED) — FOUND.
- `3b51edc7` feat(88-15): add EndgameClockDiffOverTimeChart component (GREEN) — FOUND.
- `d6ade7a6` feat(88-15): wire clock-diff line chart into Endgames page + CHANGELOG — FOUND.

**Verification commands (run during execution):**

- `uv run pytest tests/services/test_time_pressure_service.py tests/test_endgame_service.py tests/test_endgame_repository.py tests/services/test_insights_service_series.py -q` → **369 passed**.
- `uv run ruff check .` → All checks passed!
- `uv run ty check app/ tests/` → All checks passed!
- `uv run python scripts/gen_endgame_zones_ts.py --check` → up to date.
- `cd frontend && npm test -- --run` → **513 passed** (44 test files).
- `cd frontend && npx tsc --noEmit -p tsconfig.app.json` → exit 0.
- `cd frontend && npm run lint` → exit 0.
- `cd frontend && npm run knip` → exit 0.
- `cd frontend && npm run build` → exit 0.

## TDD Gate Compliance

Both behavior-adding tasks followed RED → GREEN. Git log shows:

- `test(88-15): … (RED)` at `62ea4744`, then `feat(88-15): … (GREEN)` at `4e8a3e27` (Task 1, backend).
- `test(88-15): … (RED)` at `59432725`, then `feat(88-15): … (GREEN)` at `3b51edc7` (Task 2, frontend).

Task 3 was a wiring task (no new behavior — just renders the existing component in the existing page). No separate RED commit needed; the page test suite still passes against the changed render tree.
