---
phase: 102-endgame-llm-statistical-reasoning-rework-v1-23
plan: 01
subsystem: api
tags: [llm, insights, endgame, percentile, time-pressure, findings]

# Dependency graph
requires:
  - phase: 94-endgame-percentiles
    provides: "per-TC TPCTL percentile fields on TimePressureTcCard + rating_anchors on EndgameOverviewResponse"
  - phase: 88-endgame-llm-time-pressure-rework
    provides: "TimePressureTcCard with quintiles + net_timeout_rate fraction field"
provides:
  - "Real net_timeout_rate scalar finding (n-weighted ×100 from card fraction) replacing always-empty stub"
  - "EndgameTabFindings carries time_pressure_cards, metric_percentiles, and cohort_anchors"
  - "_format_time_pressure_score_gap_chart_block helper renders 5-quintile per-TC Score-Delta table"
  - "pctl= cohort-framed percentile annotations on summary window lines via _summary_window_line"
affects: [102-02-PLAN, insights_llm, insights_service]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Percentile-as-metadata: pctl= appended after quality= in summary lines; zone remains the sole emission gate (D-04)"
    - "Chart block helper pattern: _format_time_pressure_score_gap_chart_block modeled on _format_type_wdl_chart_block"
    - "Optional EndgameTabFindings fields: three new append-only optional fields preserve findings_hash stability"

key-files:
  created: []
  modified:
    - app/services/insights_service.py
    - app/schemas/insights.py
    - app/services/insights_llm.py
    - tests/services/test_insights_service.py
    - tests/services/test_insights_llm.py

key-decisions:
  - "net_timeout_rate fraction multiplied ×100 in insights_service (not insights_llm) to match avg_clock_diff_pct scale; PATTERNS.md §D-07.2 was wrong about no ×100"
  - "Use card.total (not clock_gap.n) as denominator for net_timeout_rate weighting — total is the correct game count for this per-TC timeout metric"
  - "metric_percentiles dict only carries keys whose source value is non-None; cohort_anchors empty dict → stored as None"
  - "Quintile skip gate: opp_score is None (not user_score — which does not exist as a field on PressureQuintileBullet)"

patterns-established:
  - "pctl= annotation: added as optional params to _summary_window_line, threaded via _render_summary_block and _render_subsection_block"

requirements-completed: [LLM-01, LLM-03, LLM-04, LLM-05, LLM-06]

# Metrics
duration: 30min
completed: 2026-06-01
---

# Phase 102 Plan 01: Endgame LLM Payload Statistical Enrichment Summary

**LLM payload enriched with real net_timeout_rate scalar, 5-quintile Score-Gap-by-time chart block, and pctl= cohort-framed percentile annotations on in-scope metric summary lines**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-06-01T17:20:00Z
- **Completed:** 2026-06-01T17:54:56Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Fixed `net_timeout_rate` from always-empty stub to real n-weighted scalar (card fraction ×100 to match avg_clock_diff_pct scale); zone assigned via ZONE_REGISTRY entry; headline eligible when sufficient games
- Added three optional fields to `EndgameTabFindings`: `time_pressure_cards`, `metric_percentiles`, `cohort_anchors` — populated from all_time EndgameOverviewResponse in compute_findings; backwards compatible (all default None)
- Added `_format_time_pressure_score_gap_chart_block` helper rendering 5-quintile per-TC Score-Delta table with typical_band from PRESSURE_BIN_SCORE_NEUTRAL_ZONES; wired into _SECTION_LAYOUT + chart_blocks dict
- Threaded `pctl=N (vs ~{anchor}-rated peers)` annotations into `_summary_window_line` via optional params; metric_percentiles lookup in `_render_summary_block`; zone remains the sole emission gate (D-04)

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix net_timeout_rate to a real n-weighted scalar finding** - `1d9ae9e6` (fix)
2. **Task 2: Plumb time_pressure_cards + percentile lookup onto EndgameTabFindings** - `58e2d6d3` (feat)
3. **Task 3: Render the Score-Gap-by-time block + inject pctl= into summary lines** - `cca26fa9` (feat)

## Files Created/Modified

- `app/services/insights_service.py` - Fixed net_timeout_rate aggregation; added metric_percentiles + cohort_anchors + time_pressure_cards population in compute_findings
- `app/schemas/insights.py` - Added three optional fields to EndgameTabFindings; imported TimePressureCardsResponse
- `app/services/insights_llm.py` - Added _format_time_pressure_score_gap_chart_block; updated _SECTION_LAYOUT; threaded pctl= params through _summary_window_line / _render_summary_block / _render_subsection_block
- `tests/services/test_insights_service.py` - Added TestNetTimeoutRateFinding (5 tests); updated _stub_endgame_overview_response with new required fields
- `tests/services/test_insights_llm.py` - Added TestTimePressureScoreGapChartBlock (7 tests) and TestPercentileAnnotation (4 tests)

## Decisions Made

- **net_timeout_rate denominator**: used `card.total` (total endgame games per TC) as the n-weight denominator, not `clock_gap.n` (games with clock data). Rationale: `net_timeout_rate` is normalized by total games, not clock-available games; using `total` keeps the weighting consistent with the metric's definition.
- **PATTERNS.md §D-07.2 correction**: plan's `read_first` correctly flagged that PATTERNS.md was wrong; the docstring on `TimePressureTcCard.net_timeout_rate` confirms it is a fraction ("0.005 = 0.5%") requiring ×100, identical to `avg_clock_diff_pct`.
- **Quintile skip gate**: `opp_score is None` is the correct n-gate check (plan said `user_score is None` but `PressureQuintileBullet` has no `user_score` field — it stores `delta` and `opp_score`; `opp_score` is None when the n-gate is unmet).
- **Cohort framing for page-level metrics**: use first available anchor from `cohort_anchors` when no TC dimension on the finding; produces "vs ~{anchor}-rated peers" (no TC suffix).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stub test missing new fields needed by updated compute_findings**
- **Found during:** Task 2 (compute_findings new field population)
- **Issue:** `_stub_endgame_overview_response` used `model_construct` without `score_gap_material`, `time_pressure_cards`, `rating_anchors` — AttributeError on the new code path
- **Fix:** Updated `_stub_endgame_overview_response` to include `ScoreGapMaterialResponse(minimal)`, `TimePressureCardsResponse(cards=[])`, `rating_anchors={}`
- **Files modified:** `tests/services/test_insights_service.py`
- **Verification:** All TestComputeFindingsReturnContract tests pass
- **Committed in:** `58e2d6d3` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Fix was necessary to keep existing test suite passing. No scope creep.

## Issues Encountered

None beyond the deviation above.

## Known Stubs

None — all three plan objectives fully implemented.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes at trust boundaries. All new payload fields derive from existing server-computed `EndgameOverviewResponse` (per T-102-01 / T-102-02 in the plan's threat model, disposition: accept).

## Next Phase Readiness

- Plan 02 can now teach the LLM prompt about the new payload fields: `net_timeout_rate` real scalar, `### Chart: time_pressure_score_gap_by_time` chart block, and `pctl=` cohort-framed annotations
- `_PROMPT_VERSION` bump (`endgame_v35` → `endgame_v36`) is intentionally deferred to Plan 02 so the cache invalidates only once the prompt actually teaches these fields

## Self-Check: PASSED

- `app/services/insights_service.py`: FOUND
- `app/schemas/insights.py`: FOUND
- `app/services/insights_llm.py`: FOUND
- Commits `1d9ae9e6`, `58e2d6d3`, `cca26fa9`: FOUND in git log
- `uv run pytest tests/services/test_insights_service.py tests/services/test_insights_llm.py -x -q`: 177 passed
- `uv run ty check app/ tests/`: All checks passed
- `uv run ruff check app/ tests/`: All checks passed

---
*Phase: 102-endgame-llm-statistical-reasoning-rework-v1-23*
*Completed: 2026-06-01*
