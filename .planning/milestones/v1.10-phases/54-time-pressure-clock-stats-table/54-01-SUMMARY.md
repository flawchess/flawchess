---
phase: 54-time-pressure-clock-stats-table
plan: "01"
subsystem: api
tags: [fastapi, sqlalchemy, postgresql, pydantic, endgames, clock, time-pressure]

requires:
  - phase: 53-endgame-score-gap-material-breakdown
    provides: EndgameOverviewResponse schema, endgame_repository patterns, endgame_service helpers

provides:
  - ClockStatsRow and ClockPressureResponse Pydantic schemas
  - query_clock_stats_rows repository function (full ply/clock array aggregation)
  - _extract_entry_clocks service helper (ply-parity clock extraction)
  - _compute_clock_pressure service function (per-time-control aggregation)
  - clock_pressure field on EndgameOverviewResponse
  - Unit tests: TestExtractEntryClocks (9 tests), TestComputeClockPressure (9 tests)

affects:
  - 54-02: frontend plan will consume clock_pressure from the overview endpoint

tech-stack:
  added: []
  patterns:
    - "Full array_agg pattern (ARRAY(FloatType())) for service-side ply-parity extraction rather than SQL[1] indexing"
    - "defaultdict(set) accumulators for game_id deduplication in service layer"
    - "cast(Literal[...], value) for ty-clean Literal assignment from iterated str keys"

key-files:
  created: []
  modified:
    - app/schemas/endgames.py
    - app/repositories/endgame_repository.py
    - app/services/endgame_service.py
    - tests/test_endgame_service.py

key-decisions:
  - "Full array_agg over all span plies (not [1] indexed) — necessary so service can walk by parity to find first user-ply and first opp-ply independently"
  - "Both clocks required for clock_games counting — single-clock spans excluded from averages; counted in total_endgame_games for net timeout rate"
  - "Response-level totals (total_clock_games, total_endgame_games) computed pre-filter across all time controls so 'Based on X of Y' note is accurate even when some rows are hidden"
  - "MIN_GAMES_FOR_CLOCK_STATS = 10 (reuses same value as MIN_GAMES_FOR_TIMELINE) defined as module-level constant"

patterns-established:
  - "Phase 54 TDD: RED (ImportError on missing functions) -> GREEN (18 clock tests pass) -> confirmed with full 92-test suite"

requirements-completed: ["SC-1", "SC-2", "SC-3", "SC-4", "SC-5"]

duration: 30min
completed: 2026-04-12
---

# Phase 54 Plan 01: Time Pressure Clock Stats — Backend Summary

**Per-time-control clock stats at endgame entry via full ply/clock array aggregation, ply-parity extraction, and ClockPressureResponse wired into the overview endpoint**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-04-12T16:24:00Z
- **Completed:** 2026-04-12T16:54:23Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- New `ClockStatsRow` and `ClockPressureResponse` Pydantic schemas with all 10 required fields
- `query_clock_stats_rows` repository function aggregates full `ply_array` and `clock_array` per (game, endgame_class) span using `ARRAY(FloatType())` type_coerce pattern
- `_extract_entry_clocks` walks interleaved ply/clock arrays by parity: even plies for white user, odd plies for black user; skips None entries to find first non-None clock per player
- `_compute_clock_pressure` groups spans by time_control_bucket, deduplicates game_ids for net timeout rate, filters rows below 10 games, computes response-level totals pre-filter
- `get_endgame_overview` extended with sixth payload `clock_pressure`
- 18 new unit tests across `TestExtractEntryClocks` and `TestComputeClockPressure`; all 643 tests pass

## Task Commits

1. **Task 1: Schemas and repository query** - `ed6ae07` (feat)
2. **Task 2: Service logic and unit tests** - `a0c562e` (feat)

## Files Created/Modified

- `app/schemas/endgames.py` — Added `ClockStatsRow`, `ClockPressureResponse`; added `clock_pressure` field to `EndgameOverviewResponse`
- `app/repositories/endgame_repository.py` — Added `query_clock_stats_rows` with full array aggregation and `Float as FloatType` import
- `app/services/endgame_service.py` — Added `_extract_entry_clocks`, `_compute_clock_pressure`, `MIN_GAMES_FOR_CLOCK_STATS`, `_TIME_CONTROL_LABELS`, `_TIME_CONTROL_ORDER`; wired into `get_endgame_overview`
- `tests/test_endgame_service.py` — Added `TestExtractEntryClocks` (9 tests), `TestComputeClockPressure` (9 tests), `_make_clock_row` helper; updated `TestGetEndgameOverview` to mock `query_clock_stats_rows`

## Decisions Made

- Full `array_agg` over all span plies rather than SQL `[1]` indexing: required because the first span ply might be None for one player but non-None for the other — need to scan by parity independently.
- Both clocks (user AND opp) required for a span to contribute to clock averages; single-clock spans still count toward `total_endgame_games` for net timeout rate computation.
- Response-level `total_clock_games` and `total_endgame_games` are computed pre-filter (before the MIN_GAMES_FOR_CLOCK_STATS threshold is applied) so the frontend "Based on X of Y" note reflects all data.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

Two `ty` errors fixed inline during Task 2:
1. `ClockStatsRow.time_control` expects `Literal[...]` but `tc` is `str` — resolved with `cast(Literal[...], tc)`.
2. `_make_blitz_rows` test helper had `time_control_seconds: int` — needed `int | None` to accept `None` in test.

Neither was a logic bug, both were straightforward type annotation fixes caught by ty check.

## Next Phase Readiness

- `GET /api/endgames/overview` now returns `clock_pressure` with typed `ClockPressureResponse`
- Ready for Phase 54-02: frontend `ClockPressureSection` component consuming the new field
- No blockers

## Self-Check: PASSED

- All 4 modified files exist on disk
- Both task commits (`ed6ae07`, `a0c562e`) verified in git log
- 643 tests pass, ty check clean, ruff clean

---
*Phase: 54-time-pressure-clock-stats-table*
*Completed: 2026-04-12*
