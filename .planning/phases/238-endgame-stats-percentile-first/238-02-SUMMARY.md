---
phase: 238-endgame-stats-percentile-first
plan: 02
subsystem: api
tags: [fastapi, endgames, timelines, quintile-curve, ranked-sample, latency]

requires:
  - phase: 238-01
    provides: ranked payload contract, build_ranked_stats / get_ranked_stats, RankedInputs
provides:
  - "Per-TC Endgame Score Gap over Time and Endgame ELO Timeline combos on RankedTcStats (D-03)"
  - "Per-TC time-pressure quintile curve and Clock Gap timeline (D-06)"
  - "Per-TC Endgame Type categories (rook, minor piece, pawn, queen) (D-05)"
  - "Pure build_endgame_elo_combos shared by the filtered and ranked paths"
  - "GET /api/endgames/stats: filtered per-category stats for the Games tab (D-01)"
  - "Recorded on-read latency for dev users 7 and 14"
affects: [238-03, 238-04, 238-05, 238-08]

plan_head_before: 9b1a2fd4f4e7e7a5c13b55378cdf761487a82384
plan_head_after: 2578cf2faf5b3351c28b1dbea83a8f5ce5b2a41e
actuals:
  tokens: 14000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Reuse the legacy pure aggregators (timeline, quintile, type) on ranked rows instead of re-implementing them; only the peer-ranked metrics mirror the CTEs"
    - "since semantics split: scalars use rows on or after since, timelines receive the FULL ranked rows plus a cutoff (pre-fill, then trim)"

key-files:
  created: []
  modified:
    - app/services/endgame_service.py
    - app/services/endgame_ranked_service.py
    - app/routers/endgames.py
    - tests/services/test_endgame_ranked_service.py
    - tests/services/test_endgame_ranked_parity.py
    - tests/test_endgames_router.py

key-decisions:
  - "A TC with no usable clock row gets time_pressure.quintiles == [] rather than five empty bullets (the overview omits such a TC card entirely)"
  - "The three non-peer-ranked components keep the legacy semantics (2x base-clock clamp, NULL-eval-to-parity in the type aggregator); the ranked builders document this so nobody moves them toward the CTE definitions"
  - "Latency is above the 2 s flag threshold only on a single cold first call; medians are 0.5 s and 1.2 s, so no caching was added"

patterns-established:
  - "_build_tc_stats(tc, games, inputs, full, since): inputs drives scalars, full drives timelines"

requirements-completed: [D-01, D-03, D-05, D-06, D-00b]

coverage:
  - id: D1
    description: "Each ranked TC carries Score Gap over Time and ELO Timeline combos built only from that TC's ranked games; since pre-fills then trims"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "tests/services/test_endgame_ranked_parity.py#test_ranked_timelines_populated_for_seeded_tc"
        status: pass
      - kind: unit
        ref: "tests/services/test_endgame_ranked_service.py#test_since_trims_timeline_points"
        status: pass
      - kind: unit
        ref: "tests/services/test_endgame_ranked_service.py#test_build_endgame_elo_combos_matches_overview_path"
        status: pass
    human_judgment: false
  - id: D2
    description: "Each ranked TC carries a five-bullet pressure curve and a Clock Gap timeline from its own clock rows"
    requirement: "D-06"
    verification:
      - kind: unit
        ref: "tests/services/test_endgame_ranked_service.py#test_quintile_curve_from_ranked_clock_rows"
        status: pass
      - kind: unit
        ref: "tests/services/test_endgame_ranked_service.py#test_clock_diff_timeline_per_tc"
        status: pass
      - kind: integration
        ref: "tests/services/test_endgame_ranked_parity.py#test_ranked_curve_and_type_rows_for_seeded_tc"
        status: pass
    human_judgment: false
  - id: D3
    description: "Each ranked TC carries rook / minor piece / pawn / queen type rows; mixed and pawnless excluded; empty without endgames"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "tests/services/test_endgame_ranked_service.py#test_type_categories_per_tc"
        status: pass
      - kind: unit
        ref: "tests/services/test_endgame_ranked_service.py#test_type_categories_empty_without_endgames"
        status: pass
    human_judgment: false
  - id: D4
    description: "GET /api/endgames/stats honours the sidebar filters and rejects from_date > to_date"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "tests/test_endgames_router.py#TestEndgameStats"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-10-11
status: complete
---

# Phase 238 Plan 02: Ranked timelines, pressure curve, type rows and filtered /stats Summary

**Every `RankedTcStats` now carries its Score Gap and ELO timelines, five-quintile pressure curve, Clock Gap timeline and Endgame Type rows, all built from that TC's ranked games by reusing the existing pure helpers, plus a filtered `GET /api/endgames/stats` for the Games tab.**

## Performance

- **Duration:** about 45 min
- **Tasks:** 3 (1 tracer, 1 TDD, 1 auto)
- **Files modified:** 6 (0 created)

## Accomplishments

- `build_endgame_elo_combos` extracted from `get_endgame_elo_timeline` (behavior-preserving; the existing endgame service tests pass unedited). The ranked path calls it with the TC's ranked rows and an asof map built from the TC's `RankedGameRow` list grouped by platform, so Actual ELO comes from the same games as the score series.
- `since` semantics: `_build_tc_stats(tc, games, inputs, full, since)`. Scalars use the restricted `inputs`; Score Gap, ELO and Clock Gap timelines take the FULL ranked rows with `cutoff = since`, so rolling windows pre-fill and only emitted points before `since` are dropped.
- Quintile curve, Clock Gap timeline and type rows call `_iterate_clock_rows` + `_build_quintile_bullets`, `_compute_clock_diff_timeline` and `_aggregate_endgame_stats_by_tc` directly; no body is copied. A block comment in the ranked service records that these three are not peer-ranked and intentionally keep the legacy semantics.
- `GET /api/endgames/stats` copies the overview filter parameters and the 422 check; `user_id` comes only from `current_active_user`.

## Task Commits

1. **Task 1 (tracer): per-TC Score Gap / ELO timelines** - `04c220b37` (feat)
2. **Task 2 RED: failing curve / clock gap / type tests** - `5b55a3429` (test)
3. **Task 2 GREEN: curve, Clock Gap timeline, type categories** - `08f310028` (feat)
4. **Task 3: filtered GET /endgames/stats + TestEndgameStats** - `2578cf2fa` (feat)

## Latency

Probe: `temp/238-perf/probe_ranked_stats.py` (untracked, gitignored), run in the foreground against the dev DB, 3 timed runs of `get_ranked_stats` per user, then one staged run with `perf_counter` inside the probe only.

```
user=7 runs_ms=666,365,526 median_ms=526
user=14 runs_ms=2232,1099,1214 median_ms=1214
```

Stage breakdown (single run, ms):

```
user=7  ranked_games_sql_x4=158 performance_rows=41 entry_rows=28 bucket_rows=42 clock_rows=47 percentiles_anchors=5 fetch_total=320 build_pure_python=148 n_ranked_games=1119
user=14 ranked_games_sql_x4=83 performance_rows=96 entry_rows=84 bucket_rows=107 clock_rows=134 percentiles_anchors=5 fetch_total=452 build_pure_python=644 n_ranked_games=4620
```

Both medians are under the 2 s threshold, so there is no "Latency flag" per the plan. Two observations for the owner: (a) the very first call for user 14 took 2232 ms (cold connection / plan cache; the next two were about 1.1 to 1.2 s); (b) for the heaviest account the pure-Python build (644 ms for 4620 ranked games) now dominates the DB fetch (452 ms), so any later optimization belongs in the Python aggregators, not the repository queries. No caching was added.

## Deviations from Plan

### Auto-fixed Issues

None. Execution-detail notes:

**1. [Test design] Legitimate filter for the "excludes seeded games" test**
- The plan suggested a `time_control` filter excluding the seeded games, but the seeded portfolio covers all four TCs and `time_control` is a native PG enum (an unknown value such as `daily` is a DB error, not an empty result). The test uses `time_control=bullet&platform=chess.com`, which matches none of the seeded games (bullet games are lichess only) and yields `total_games == 0`.

**2. [Behavior choice] Empty pressure curve for a TC without clock rows**
- `_build_quintile_bullets` always returns five bullets; for a TC with no usable clock row the ranked payload returns `quintiles == []` (the overview omits such a card). A TC with clock rows returns exactly five.

**Total deviations:** 0 auto-fixed bugs, 2 execution notes. **Impact:** none on scope.

## TDD Gate Compliance

Task 2 followed RED then GREEN. RED (`5b55a3429`): 4 of 5 new tests failed on assertions against the empty contract values (`assert []`); `test_type_categories_empty_without_endgames` passed already because the empty form was the contract default (it guards against a regression, not a new behavior). GREEN (`08f310028`): all pass.

## Issues Encountered

- Pre-existing, out of scope (logged, not fixed): an unknown `time_control` string on `/endgames/overview` and now `/endgames/stats` reaches Postgres and raises a 500 instead of a 422, because the column is a native enum and the Query parameter is an untyped `list[str]`. It predates this plan and applies to every filtered endgame route.
- Full backend suite `uv run pytest -n auto -x`: 5496 passed, 19 skipped. `ruff format --check`, `ruff check .`, `ty check app/ tests/ scripts/` and the depth-4 gate are clean.

## Known Stubs

None. Every `RankedTcStats` field is computed.

## Threat Flags

None. `/stats` is the surface in the plan's threat model (T-238-05): filter parameters flow only into `apply_game_filters` bound expressions, `from_date > to_date` returns 422, `user_id` comes only from the auth dependency. Latency (T-238-06) is measured above.

## Next Phase Readiness

Plan 238-03 (frontend) can consume the completed `RankedTcStats` and switch the Games tab to `GET /api/endgames/stats`. Plan 238-04 can call `build_ranked_stats(inputs, since=...)` with the corrected timeline semantics.

## Self-Check: PASSED

- Modified files exist: endgame_service.py, endgame_ranked_service.py, endgames.py router, the three test files
- Commits `04c220b37`, `5b55a3429`, `08f310028`, `2578cf2fa` are ancestors of HEAD
- `git status --porcelain temp/` is empty (probe untracked and ignored)
