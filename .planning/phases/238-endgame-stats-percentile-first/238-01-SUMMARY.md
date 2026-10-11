---
phase: 238-endgame-stats-percentile-first
plan: 01
subsystem: api
tags: [fastapi, postgres, sqlalchemy, canonical-slice, percentiles, endgames, parity-test]

requires:
  - phase: 94.4
    provides: canonical_slice_sql per-TC builders, persisted Stage A/B percentiles (user_benchmark_percentiles), user_rating_anchors
provides:
  - "GET /api/endgames/ranked-stats: filter-free per-TC ranked-sample payload with all 11 peer-ranked metrics computed on read"
  - "ranked_games_sql(tc) composing the unchanged Stage A/B prelude; fetch_ranked_games repository"
  - "game_ids bound-array ANY seam in apply_game_filters and the four endgame row queries"
  - "Ranked response contract (RankedMetricOut ... EndgameRankedStatsResponse) that plans 238-02/03/04/05 build against"
  - "Rank status matrix (ranked / below_floor / unranked / pending) and popover CI/p statistics"
  - "DB-backed numeric parity gate (on-read == Stage A/B CTE for all 11 families) and golden SHA-256 guard for the canonical builders"
affects: [238-02, 238-03, 238-04, 238-05, 238-08]

plan_head_before: 31b79c999783071d6f4d985daa79b35dba80e42b
plan_head_after: cafa4e5e74c1e59af9786c54b6398ce50f75ffe3
actuals:
  tokens: 26000
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Compose, never edit, canonical SQL builders (ranked_games_sql reuses selected_users + recent_capped); guard with golden SHA-256"
    - "Canonical-mode Python helpers that mirror each Stage A/B CTE line for line, gated by a seeded DB parity test against _compute_metric_for_user_per_tc"
    - "Bound int[] = ANY(:ids) predicate (game_ids_any_predicate) pushed into inner GamePosition aggregations, never IN (subquery)"

key-files:
  created:
    - app/repositories/endgame_ranked_repository.py
    - app/services/endgame_ranked_service.py
    - tests/services/test_endgame_ranked_parity.py
    - tests/services/test_endgame_ranked_service.py
  modified:
    - app/services/canonical_slice_sql.py
    - app/repositories/query_utils.py
    - app/repositories/endgame_repository.py
    - app/schemas/endgames.py
    - app/routers/endgames.py
    - tests/services/test_canonical_slice_sql.py
    - tests/repositories/test_query_utils.py
    - tests/test_endgames_router.py

key-decisions:
  - "Tracer-first: GET /ranked-stats shipped end to end with score_gap only, verified against the Stage A CTE before expanding to the other 10 families"
  - "Reused endgame_service._compute_span_gap and _extract_entry_clocks (verified equal to the CTEs by the parity test); wrote own classifier/achievable/rate/clock helpers where the legacy Python path diverges (NULL-eval routing, sub-800 floor, 2x clock clamp, net-flag denominator)"
  - "entry_eval_mean_pawns trims |cp| >= EVAL_OUTLIER_TRIM_CP, matching the existing per-category entry-eval convention (plan text said only 'cp-only non-null rows')"
  - "Anchor-eligible count mirrors the anchor CTE exactly, including NOT(chess.com AND NULL str) dropping chess.com games with a NULL time_control_str"
  - "Percentile is exposed only when status == ranked (a stale stored percentile is never shown on a cell the fresh value puts below its floor); no drift handling (D-08)"

patterns-established:
  - "Rank status is backend-owned: _rank_status(...) -> (status, floor_n, floor_required), applied in the fixed D-09/D-11 order"
  - "Popover footer statistics per metric live on the metric (ci_low/ci_high/p_value), assumption A3"

requirements-completed: [D-00b, D-01, D-07, D-09, D-10, D-11, D-14]

coverage:
  - id: D1
    description: "GET /api/endgames/ranked-stats returns, per TC with at least one ranked game, the 11 metric values computed on read from the canonical ranked slice, filter-free and auth-scoped"
    requirement: "D-07"
    verification:
      - kind: integration
        ref: "tests/test_endgames_router.py#TestRankedStats"
        status: pass
      - kind: integration
        ref: "tests/services/test_endgame_ranked_parity.py#test_ranked_stats_two_user_isolation"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every on-read value and n equals the Stage A/B CTE (_compute_metric_for_user_per_tc) for all 11 families incl. NULL-eval, sub-800, over-2x-clock, NULL base time, multi-class span edge cases"
    requirement: "D-00b"
    verification:
      - kind: integration
        ref: "tests/services/test_endgame_ranked_parity.py#test_on_read_value_matches_canonical_cte"
        status: pass
    human_judgment: false
  - id: D3
    description: "Existing canonical builders emit byte-identical SQL"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "tests/services/test_canonical_slice_sql.py#test_existing_builders_golden_sha256"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_gen_global_percentile_cdf_unchanged.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "Rank status matrix (below_floor with binding count and 30 floor, pending, unranked, ranked), TC listing and empty-sample behaviour"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "tests/services/test_endgame_ranked_service.py#test_status_*"
        status: pass
      - kind: unit
        ref: "tests/services/test_endgame_ranked_service.py#test_tcs_listed_order_and_omission"
        status: pass
    human_judgment: false
  - id: D5
    description: "Conversion / parity / recovery WDL counts come from the same games as the rate"
    requirement: "D-00b"
    verification:
      - kind: integration
        ref: "tests/services/test_endgame_ranked_parity.py#test_bucket_wdl_consistent_with_rates"
        status: pass
      - kind: unit
        ref: "tests/services/test_endgame_ranked_service.py#test_bucket_rate_consistency"
        status: pass
    human_judgment: false

duration: 37min
completed: 2026-10-11
status: complete
---

# Phase 238 Plan 01: Backend ranked payload Summary

**Filter-free `GET /api/endgames/ranked-stats` that computes all 11 peer-ranked Endgame metrics on read from the canonical ranked slice, proven numerically equal (abs 1e-9) to the persisted Stage A/B CTEs, with a rank-status matrix and popover CI/p statistics.**

## Performance

- **Duration:** about 37 min
- **Started:** 2026-10-11T12:03Z (approx)
- **Completed:** 2026-10-11T12:41Z
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 12 (4 created, 8 modified)

## Accomplishments

- `ranked_games_sql(tc)` composes the unchanged `selected_users` + `_recent_capped_per_tc_cte` prelude, so the on-read ranked games are exactly the games Stage A/B rank. A golden SHA-256 test (captured from HEAD before any edit) proves the 50 existing builder outputs (selected_users, recent_capped, every per-TC `per_user_cte_*`, blended median anchor) are byte-identical.
- `apply_game_filters(game_ids=...)` and the four endgame row queries take a single bound `int[]` `= ANY(:ids)` predicate, also pushed into the inner `GamePosition` aggregations so only ranked games' positions are scanned (never the `IN (subquery)` form that hangs the planner).
- `endgame_ranked_service` computes the 11 families with canonical-mode helpers that deliberately differ from the legacy Python path where the CTEs differ: NULL entry eval excluded (not routed to parity), sub-800 games excluded from rates and bucket gaps (but not achievable), per-(game, class) span gaps with LEAD and no 2000 cp clip, no 2x clock clamp, net-flag denominator over every endgame game.
- Rank status is backend-owned and applied in order: anchor floor ("18 of 30", Daily excluded from the anchor count) -> pending (eval-dependent, no value, evals pending) -> metric floor (binding count) -> ranked -> unranked. Percentile is exposed only for ranked cells. Footer statistics per metric: Wilson CI for rates, two-sample CI+p for score_gap and time pressure (with `shared_n`), paired CI+p for achievable / bucket gaps / clock_gap, none for net_flag_rate.
- Full response contract (`RankedMetricOut` ... `EndgameRankedStatsResponse`) in `app/schemas/endgames.py`; time_pressure curve, timelines and type_categories carry their empty form for plan 238-02.

## Task Commits

1. **Golden hashes (Task 1 step 0, before any canonical_slice_sql edit)** - `20c183816` (test)
2. **Task 1: End-to-end ranked Endgame Score Gap through GET /endgames/ranked-stats** - `c314be91a` (feat, tracer)
3. **Task 2 RED: failing parity tests for the 11 families** - `18591479a` (test)
4. **Task 2 GREEN: all 11 canonical families on read** - `d8a694aaf` (feat)
5. **Task 3 RED: failing status / bucket / popover-stat tests** - `ecf0e6103` (test)
6. **Task 3 GREEN: rank status matrix, CI/p statistics, TC listing** - `cafa4e5e7` (feat)

**Plan metadata:** committed separately (docs: complete plan).

## TDD Gate Compliance

Tasks 2 and 3 followed RED then GREEN. RED evidence: Task 2 failed with `KeyError` on the 10 metric keys the service did not emit yet (oracle `is not None` assertions had already passed, so the seed clears every floor); Task 3 failed on assertions for below_floor-anchor, Daily-excluded anchor count, pending status and the CI/p shapes (8 of 12 passed against the interim status, as intended). No REFACTOR commit was needed. Mutation checks on the parity gate (reverted afterwards): removing the sub-800 floor failed `score_gap_conv` and `conversion_rate`; routing NULL evals to parity failed `parity_rate`; clamping clocks above 2x base failed `clock_gap` and `time_pressure_score_gap`; removing LEAD failed `score_gap_conv`; restricting the net-flag pool to base>0 failed `net_flag_rate`.

## Files Created/Modified

- `app/services/canonical_slice_sql.py` - `ranked_games_sql(tc)` and public `SUB_800_FLOOR` alias (new names only; no builder body changed)
- `app/repositories/endgame_ranked_repository.py` - `RankedGameRow`, `fetch_ranked_games` (bindparam-only user_id)
- `app/repositories/query_utils.py` - `game_ids_any_predicate`, `apply_game_filters(game_ids=...)`
- `app/repositories/endgame_repository.py` - `game_ids` threaded through performance / entry / bucket / clock row queries and inner aggregations
- `app/schemas/endgames.py` - ranked response contract
- `app/services/endgame_ranked_service.py` - `RankedInputs`, `fetch_ranked_inputs`, `build_ranked_stats`, `get_ranked_stats`, canonical-mode helpers, `_rank_status`, `EVAL_DEPENDENT_METRICS`
- `app/routers/endgames.py` - `GET /ranked-stats` (no Query params; documents the SQL `NOW()` vs `dev_now_utc` exception)
- `tests/services/test_endgame_ranked_parity.py` - seeded DB parity gate (15 tests) incl. `test_ranked_stats_two_user_isolation` (T-238-02)
- `tests/services/test_endgame_ranked_service.py` - pure status / bucket / TC-listing / CI-p tests (12)
- `tests/services/test_canonical_slice_sql.py`, `tests/repositories/test_query_utils.py`, `tests/test_endgames_router.py` - golden hashes, `ranked_games_sql`, `game_ids`, `TestRankedStats`

## Decisions Made

See `key-decisions` above. The SQL `NOW()` window is kept (planner assumption A2): dev-clock testing of the 36-month edge is not possible by design.

## Deviations from Plan

### Auto-fixed Issues

None of Rules 1-3 triggered against shipped code. Small execution-detail departures:

**1. [Scaffold] `EVAL_DEPENDENT_METRICS` added in the Task 3 RED commit**
- **Found during:** Task 3 RED
- **Issue:** the new test module imports the constant; without it pytest hit a collection error, which is an INVALID_RED (not an assertion failure).
- **Fix:** committed the pure constant together with the failing tests so RED fails on assertions.
- **Files modified:** `app/services/endgame_ranked_service.py`
- **Commit:** `ecf0e6103`

**2. [Test design] Over-2x clock pairs with a pressured opponent**
- **Found during:** Task 2 mutation check
- **Issue:** with the opponent comfortable, a mutant that clamped clocks above 2x base did not change `time_pressure_score_gap`, so the parity test could not prove the no-clamp rule for that family.
- **Fix:** `_clock_pair` returns `(400s, 40s)` for the over-2x games; the mutant is now caught for both clock_gap and time_pressure_score_gap.
- **Files modified:** `tests/services/test_endgame_ranked_parity.py`
- **Commit:** `d8a694aaf`

**3. [Plan wording] Task 2 "extend the seed"**
- The Task 1 seed was a simple spec-based helper (`_GameSpec` / `_PosSpec`); Task 2 replaced the endgame block builders in place with the full edge-case blocks, keeping `endgame_games` / `endgame_result` knobs and the exact in-slice id list. `endgame_games` sizes the parity-ish plain block; `endgame_result` is the dominant user-perspective outcome of the whole endgame population.

**Total deviations:** 0 auto-fixed bugs, 3 minor execution notes. **Impact:** none on scope or contract.

## Authentication Gates

None.

## Issues Encountered

- Latency on heavy accounts (T-238-03) is not measured in this plan; plan 238-02 owns the perf probe on dev users 7 and 14.
- Full backend suite `uv run pytest -n auto -x`: 5485 passed, 19 skipped. ruff format/check, `ty check app/ tests/ scripts/` and the depth-4 function-size gate are clean.

## Known Stubs

None. `time_pressure.quintiles`, `score_gap_timeline`, `clock_diff_timeline`, `elo_timeline` and `type_categories` are empty lists by contract until plan 238-02 computes them (that empty form is also the correct value for a TC without data).

## Threat Flags

None. The new endpoint and the `game_ids` seam are exactly the surfaces in the plan's threat model (T-238-01..04); `user_id` is bindparam-only and the two-user isolation test proves no cross-user leakage.

## Next Phase Readiness

Ready for 238-02 (timelines, quintile curve, type categories, filtered `/stats`, perf probe) and for 238-04 (insights over `build_ranked_stats(inputs, since=...)`).

## Self-Check: PASSED

- Created files exist: endgame_ranked_repository.py, endgame_ranked_service.py, test_endgame_ranked_parity.py, test_endgame_ranked_service.py
- Commits `20c183816`, `c314be91a`, `18591479a`, `d8a694aaf`, `ecf0e6103`, `cafa4e5e7` are ancestors of HEAD
