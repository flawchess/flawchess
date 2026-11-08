---
phase: 243-out-of-the-opening-worse-better-rates
plan: 03
subsystem: backend
tags: [stage-b, percentiles, postgres, sqlalchemy, parity-test, sentry]

requires:
  - phase: 243-out-of-the-opening-worse-better-rates
    plan: 01
    provides: per_user_cte_opening_out_* builders, fetch_opening_out_counts, per-colour percentile PK, opening_out_seed helpers
provides:
  - STAGE_B_OPENING_FAMILIES and _compute_and_upsert_opening_cells wired into compute_stage_b
  - fetch_opening_out_rows keyed (metric, tc, colour) for the plan 04 read path
  - three-path parity test (CDF path vs Stage B vs on-read counts)
affects: [243-04 read path, 243-02 CDF regen consumers]

actuals:
  tokens: 21000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Opening family is a separate tuple so the 10-family Endgames Stage B contract is untouched"
    - "One counts query per anchored TC feeds both rates and both colours"

key-files:
  created: []
  modified:
    - app/services/user_benchmark_percentiles_service.py
    - app/repositories/user_benchmark_percentiles_repository.py
    - tests/services/test_opening_out_rates_parity.py
    - tests/services/test_user_benchmark_percentiles_service.py
    - tests/repositories/test_user_benchmark_percentiles_repository.py

key-decisions:
  - "Opening rows rank against cohort[(metric, rounded anchor, tc)] with no colour in the key (D-04); a colour under OPENING_OUT_MIN_GAMES_PER_COLOR gets no row (D-05)"
  - "Per-TC failures are captured with set_context(stage B, metric opening_out, tc) and never stop other TCs or the endgame families; CancelledError re-raises"

patterns-established:
  - "Benchmark-only tables in a test DB are created with create_all(tables=...) and dropped with raw DROP TABLE, never drop_all(tables=...) (drop_all also tries to drop shared ENUM types such as gameresult)"

requirements-completed: [D-04, D-05]

coverage:
  - id: D1
    description: "Stage B writes up to 4 per-colour opening rows per anchored TC, each ranked against the same colour-pooled cell, value = count / n_games, n_games = qualifying count; no 'all' opening row"
    requirement: "D-04"
    verification:
      - kind: integration
        ref: "tests/services/test_opening_out_rates_parity.py#test_stage_b_writes_color_rows"
        status: pass
    human_judgment: false
  - id: D2
    description: "A colour at 29 qualifying games gets no opening row, the other colour still does"
    requirement: "D-05"
    verification:
      - kind: integration
        ref: "tests/services/test_opening_out_rates_parity.py#test_stage_b_skips_color_below_floor"
        status: pass
      - kind: unit
        ref: "tests/services/test_user_benchmark_percentiles_service.py#test_compute_stage_b_opening_skips_color_below_floor"
        status: pass
    human_judgment: false
  - id: D3
    description: "CDF path (source='benchmark' via benchmark_selected_users), Stage B persisted rows and fetch_opening_out_counts give identical value and n per colour x metric"
    requirement: "D-05"
    verification:
      - kind: integration
        ref: "tests/services/test_opening_out_rates_parity.py#test_three_path_parity"
        status: pass
    human_judgment: false
  - id: D4
    description: "Endgames Stage B untouched: STAGE_B_METRIC_FAMILIES keeps 10 entries with no opening id; endgame fan-out still 10 x anchored TCs; test_endgame_ranked_parity passes unchanged"
    verification:
      - kind: unit
        ref: "tests/services/test_user_benchmark_percentiles_service.py#test_compute_stage_b_fans_out_across_families_and_anchored_tcs"
        status: pass
      - kind: integration
        ref: "tests/services/test_endgame_ranked_parity.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "Per-TC opening failure is Sentry-captured with stage B / metric opening_out / tc context, other TC still upserts, CancelledError propagates"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "tests/services/test_user_benchmark_percentiles_service.py#test_compute_stage_b_opening_failure_is_isolated_per_tc"
        status: pass
      - kind: unit
        ref: "tests/services/test_user_benchmark_percentiles_service.py#test_compute_stage_b_opening_cancellation_propagates"
        status: pass
    human_judgment: false
  - id: D6
    description: "fetch_opening_out_rows returns only white/black opening rows keyed (metric, tc, colour); 'all' and endgame rows excluded; user-scoped"
    verification:
      - kind: integration
        ref: "tests/repositories/test_user_benchmark_percentiles_repository.py#test_fetch_opening_out_rows_keyed_by_metric_tc_color"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-31
status: complete
plan_head_before: 3a3428122880db53a5d2c14677f9fb0bd141a105
plan_head_after: 066276a8995d7729dc7437864b4902bce4f4af35
commits: 2
---

# Phase 243 Plan 03: Stage B per-colour opening percentiles Summary

**Stage B now persists each user's per-colour worse/better opening rates and their percentiles against the colour-pooled CDF, and a three-path DB test proves the CDF path, the persisted row and the on-read counts agree exactly.**

## Accomplishments

- `compute_stage_b` gains a second loop after the Endgames product loop: `_compute_and_upsert_opening_cells` makes one `fetch_opening_out_counts` call per anchored TC and, via `itertools.product` (depth-4 gate), upserts one row per (colour, metric) that passes `OPENING_OUT_MIN_GAMES_PER_COLOR`. Value is `count_for(metric) / n_games`, `n_games` is the qualifying count, the cohort key is `(metric, round_anchor_to_grid(anchor), tc)` with no colour (D-04). The race note and both docstrings now describe the 4-column PK.
- `STAGE_B_OPENING_FAMILIES` (= `OPENING_OUT_METRICS`) is a separate tuple. `STAGE_B_METRIC_FAMILIES` is still 10 entries and `test_endgame_ranked_parity.py` passes unchanged.
- `fetch_opening_out_rows(session, *, user_id)` returns `dict[(metric, tc, colour), PercentileRow]` for white/black opening rows only (ready for plan 04).
- `test_three_path_parity` seeds a user, creates `benchmark_selected_users` and `benchmark_ingest_checkpoints` inside the test DB, and compares (a) `selected_users_cte(source="benchmark")` + `per_user_cte_opening_out_rate(..., source="benchmark", snapshot_date=today)`, (b) the persisted Stage B rows and (c) `fetch_opening_out_counts`: exact float equality of value and n per colour x metric. No fallback to the single_user prelude was needed.
- Mutation checks (reverted each time): removing the floor skip fails `test_stage_b_skips_color_below_floor`; computing the better rate from `worse_n` fails `test_stage_b_writes_color_rows` and `test_three_path_parity`.

## Task Commits

1. **Task 1 (tracer):** `6e234cf37` feat(243-03): Stage B persists per-colour opening worse/better percentile rows
2. **Task 2:** `066276a89` test(243-03): three-path parity and Stage B opening fan-out tests

Tracer gate: `<verify>` re-run end-to-end after the tracer commit (opening parity + Endgames ranked parity + ty/ruff/depth gate), passed, so expansion proceeded.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test cleanup via `drop_all(tables=...)` tried to DROP TYPE gameresult**
- **Found during:** Task 2
- **Issue:** `Base.metadata.drop_all(sync_conn, tables=[...])` also drops shared native ENUM types that the real `games` table still uses (`DependentObjectsStillExistError`); the plan said "drop_all with the same table list".
- **Fix:** Create with `create_all(tables=...)`, drop with raw `DROP TABLE IF EXISTS benchmark_ingest_checkpoints, benchmark_selected_users`.
- **Files modified:** tests/services/test_opening_out_rates_parity.py
- **Commit:** 066276a89

**2. [Rule 1 - Type] ty rejected `__table__` as `FromClause` for `create_all(tables=...)`**
- **Fix:** `cast(Table, ...)` on both model tables. Commit 066276a89.

**Total deviations:** 2 auto-fixed, no scope impact.

## Issues Encountered

None beyond the above. The orchestrator's concurrent CDF regen did not interfere (tests run on cloned per-session DBs).

## Verification

- `uv run pytest -n auto -x`: 5628 passed, 19 skipped.
- Serial run of the touched files (parity, service, repository, Endgames ranked parity): 61 passed.
- `uv run ty check app/ tests/ scripts/`, `ruff check`, `ruff format`: clean. `check_function_size.py app/ --fail-over-depth 4`: no breaches.
- Acceptance greps: `STAGE_B_OPENING_FAMILIES` >= 2, `def fetch_opening_out_rows` 1, `def test_three_path_parity` 1, `fetch_opening_out_counts` in the service test 3, `STAGE_B_METRIC_FAMILIES` len 10 with no `opening_` id.

## Known Stubs

None.

## Threat Flags

None. T-243-08..10 mitigated as planned: `user_id` only via `.bindparams()` (existing counts repo), 4-column PK upsert, one counts query per TC, per-TC try/except with `CancelledError` re-raise, keyword-only `user_id` on `fetch_opening_out_rows`.

## Next Phase Readiness

Plan 04 can read the persisted rows with `fetch_opening_out_rows` and the on-read counts with `fetch_opening_out_counts`. Prod rows appear only after the CDF regen from plan 02 is loaded and Stage B reruns per user.

## Self-Check: PASSED

- FOUND commits: 6e234cf37, 066276a89
- FOUND: tests/services/test_opening_out_rates_parity.py::test_three_path_parity, app/repositories/user_benchmark_percentiles_repository.py::fetch_opening_out_rows, STAGE_B_OPENING_FAMILIES in the service
