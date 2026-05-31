---
phase: 97-endgame-metrics-by-time-control
plan: 02
subsystem: api
tags: [fastapi, sqlalchemy, pydantic, endgame, per-tc, aggregation]

# Dependency graph
requires:
  - phase: 94-endgame-percentile-chips
    provides: "user_benchmark_percentiles_repository.fetch_for_user, per-(metric, TC) PercentileRow shape"
  - phase: 87-endgame-stats-card-redesign
    provides: "_classify_endgame_bucket, _compute_span_gap, _aggregate_bucket_counts, query_endgame_bucket_rows"
  - phase: 88-time-pressure-cards
    provides: "_compute_time_pressure_cards structural analog, MIN_GAMES_PER_TC_CARD constant, _TIME_CONTROL_ORDER"

provides:
  - "PerTcBucketStats, EndgameMetricsTcCard, EndgameMetricsCardsResponse Pydantic schemas on app/schemas/endgames.py"
  - "query_endgame_bucket_rows extended with time_control_bucket (col 6) + LEAD next-eval cols (7-8)"
  - "_MetricTcAccumulator dataclass + _compute_per_tc_metric_cards function"
  - "endgame_metrics_cards field on EndgameOverviewResponse (default_factory, B-2 lock preserved)"

affects:
  - "97-03 (Wave 2 frontend) — consumes endgame_metrics_cards from overview response"
  - "endgame_zones.py — Wave 1b adds TC_METRIC_BANDS used by gauge rendering"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-TC accumulator pattern: _MetricTcAccumulator dataclass with single-pass TC grouping, mirrors _ClockAggregate"
    - "Direct per-TC percentile lookup: _effective_rows.get(metric, {}).get(tc_bucket) bypassing blended helper"
    - "Terminal span semantics for bucket_rows: LEAD next-eval always NULL (one row per game), uses game result as exit score"
    - "Additive column extension: new cols appended to SELECT, safe because existing consumers use named attribute access"

key-files:
  created:
    - "tests/services/test_endgame_service.py — TDD tests for _compute_per_tc_metric_cards"
  modified:
    - "app/schemas/endgames.py — PerTcBucketStats, EndgameMetricsTcCard, EndgameMetricsCardsResponse, endgame_metrics_cards field"
    - "app/repositories/endgame_repository.py — query_endgame_bucket_rows extended to 9 columns"
    - "app/services/endgame_service.py — _MetricTcAccumulator, _build_per_tc_bucket_stats, _compute_per_tc_metric_cards, threading"
    - "tests/test_endgame_repository.py — fixed positional unpacking tests for new 9-column shape"

key-decisions:
  - "D-15 Sub-option A: extended query_endgame_bucket_rows with time_control_bucket + LEAD columns (one query, no second round-trip)"
  - "Terminal span semantics: bucket_rows groups by game_id (one row per game), so LEAD next-eval is always NULL; correct to use game result as exit score"
  - "Direct percentile lookup: _effective_rows.get(metric, {}).get(tc_bucket) bypasses _aggregate_per_tc_percentile (D-09/D-10)"
  - "Extracted _build_per_tc_bucket_stats helper to keep _compute_per_tc_metric_cards under depth-3 nesting limit"
  - "MIN_GAMES_PER_TC_CARD floor kept at 20 per RESEARCH D-12 validation (floor adequate for card gate)"

patterns-established:
  - "_MetricTcAccumulator dataclass: slot=True, per-bucket wins/draws/total + gap lists, mirrors _ClockAggregate"
  - "Fixed TC ordering via _TIME_CONTROL_ORDER: bullet->blitz->rapid->classical in card output"
  - "B-2 lock: endgame_metrics_cards uses Field(default_factory=...) to preserve existing constructor compatibility"

requirements-completed: [standalone]

# Metrics
duration: 17min
completed: 2026-05-29
---

# Phase 97 Plan 02: Per-TC Endgame Metric Cards Backend Summary

**Per-TC conversion/parity/recovery rate aggregation backend: query extension, Pydantic schemas, and single-pass accumulator threaded into EndgameOverviewResponse**

## Performance

- **Duration:** ~17 min
- **Started:** 2026-05-29T15:27:28Z
- **Completed:** 2026-05-29T15:44:13Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Extended `query_endgame_bucket_rows` to project `time_control_bucket` (col 6) and LEAD next-entry-eval columns (cols 7-8) via a second subquery wrap mirroring `query_endgame_entry_rows`
- Added `PerTcBucketStats`, `EndgameMetricsTcCard`, `EndgameMetricsCardsResponse` Pydantic schemas and `endgame_metrics_cards` field on `EndgameOverviewResponse` with default_factory (B-2 lock)
- Implemented `_compute_per_tc_metric_cards` with single-pass per-TC accumulation, conversion/parity/recovery rates, WDL pcts, ΔES span-gap stats, direct per-TC percentile lookup, and fixed bullet->blitz->rapid->classical ordering
- Threaded the new function into `get_endgame_overview` using already-fetched `bucket_rows` and `percentile_rows` (no new DB query, no asyncio.gather)

## Task Commits

1. **Task 1: Schemas + repository extension** - `202b53c4` (feat)
2. **Task 2: RED tests** - `8f924a86` (test)
3. **Task 2: GREEN implementation** - `77323a9f` (feat)

## Files Created/Modified

- `/app/schemas/endgames.py` - New PerTcBucketStats, EndgameMetricsTcCard, EndgameMetricsCardsResponse; endgame_metrics_cards on EndgameOverviewResponse
- `/app/repositories/endgame_repository.py` - query_endgame_bucket_rows extended to 9 columns (TC + LEAD next-eval)
- `/app/services/endgame_service.py` - _MetricTcAccumulator, _build_per_tc_bucket_stats, _compute_per_tc_metric_cards; threading into get_endgame_overview
- `/tests/services/test_endgame_service.py` - TDD tests for _compute_per_tc_metric_cards (23 tests)
- `/tests/test_endgame_repository.py` - Fixed positional tuple unpacking tests to use named attribute access

## Decisions Made

- **Terminal span semantics for bucket_rows:** Since `query_endgame_bucket_rows` groups by `game_id` (one row per game), the LEAD window partition always has one row. `next_entry_eval_*` is always NULL, making every row a "terminal span" using game result as exit score. This is semantically correct for the per-game bucket aggregation.
- **Helper extraction:** `_build_per_tc_bucket_stats` extracted to keep `_compute_per_tc_metric_cards` under the depth-3 nesting limit from CLAUDE.md.
- **Repository test fix:** Two repository tests using positional 6-tuple unpacking (`_game_id, ..., eval_mate = rows[0]`) failed with `too many values to unpack (expected 6)` after the 9-column extension. Fixed to use named attribute access (`rows[0].eval_cp`) — forward-compatible and reflects how service code already accesses these rows.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Repository tests broke on positional 6-tuple unpacking**
- **Found during:** Task 2 (running full test suite after GREEN implementation)
- **Issue:** `tests/test_endgame_repository.py::TestQueryEndgameBucketRows` used `_game_id, _endgame_class, _result, user_color, eval_cp, eval_mate = rows[0]` which threw `ValueError: too many values to unpack (expected 6)` after the 9-column extension in Task 1
- **Fix:** Updated both unpacking assertions to use `rows[0].eval_cp` and `rows[0].eval_mate` named attribute access (same pattern as service layer)
- **Files modified:** `tests/test_endgame_repository.py`
- **Verification:** `uv run pytest tests/test_endgame_repository.py::TestQueryEndgameBucketRows -q` passes (7/7)
- **Committed in:** `77323a9f` (GREEN task commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug: positional tuple unpacking after additive column extension)
**Impact on plan:** Minimal — additive column extension broke positional unpacking in existing tests; fixed to named access which is the correct pattern for SQLAlchemy rows.

## Issues Encountered

None beyond the auto-fixed repository test breakage above.

## Known Stubs

None — all computed values derive from real data in bucket_rows. The `endgame_metrics_cards` field defaults to `cards=[]` for backward compatibility with existing test fixtures that build `EndgameOverviewResponse` without the new field, but this is an intentional default_factory (B-2 lock), not a data stub.

## Threat Flags

No new threat surface beyond what was modeled in the plan's threat register (T-97-03, T-97-04, T-97-05). `_compute_per_tc_metric_cards` receives pre-fetched `bucket_rows` scoped to the authenticated `user_id` — T-97-03 mitigation preserved.

## Next Phase Readiness

- Wave 2 frontend (`97-03`) can consume `endgame_metrics_cards.cards` from the overview response
- Wave 1b (`97-01.b`) can add TC-keyed zone bands to `endgame_zones.py` independently
- All existing endgame tests (323) and new per-TC tests (23) pass; ty/ruff clean

## Self-Check: PASSED

Files verified:
- `app/schemas/endgames.py` — FOUND
- `app/repositories/endgame_repository.py` — FOUND
- `app/services/endgame_service.py` — FOUND
- `tests/services/test_endgame_service.py` — FOUND
- `tests/test_endgame_repository.py` — FOUND

Commits verified:
- `202b53c4` — FOUND (feat(97-02): add per-TC metric schemas)
- `8f924a86` — FOUND (test(97-02): RED tests)
- `77323a9f` — FOUND (feat(97-02): GREEN implementation)

---
*Phase: 97-endgame-metrics-by-time-control*
*Completed: 2026-05-29*
