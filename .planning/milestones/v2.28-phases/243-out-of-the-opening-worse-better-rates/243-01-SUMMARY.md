---
phase: 243-out-of-the-opening-worse-better-rates
plan: 01
subsystem: database
tags: [postgres, sqlalchemy, alembic, canonical-slice, percentiles, sql-builder]

requires:
  - phase: 242-openings-stats-tab
    provides: EVAL_BASELINE_PAWNS_* colour baselines and OPENING_INSIGHTS_CI_Z_95 constants
provides:
  - per_user_cte_opening_out_counts / per_user_cte_opening_out_rate shared SQL builders (D-01, D-02, D-05)
  - fetch_opening_out_counts repository (single per-user counts query for Stage B and the read path)
  - opening_worse_rate / opening_better_rate CdfMetricId values and OPENING_OUT_METRICS tuple (D-04)
  - user_benchmark_percentiles.color column in a 4-column PK; metric as TEXT + CHECK on both percentile tables
  - tests/services/opening_out_seed.py shared seed helpers (reused by plans 03 and 04)
affects: [243-02 CDF regen, 243-03 Stage B, 243-04 read path, endgames percentile storage]

actuals:
  tokens: 23000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "One classification SQL body composed by CDF script, Stage B and the on-read path (byte-identical across sources)"
    - "Native Postgres ENUM replaced by TEXT + CHECK generated from typing.get_args of the Literal"

key-files:
  created:
    - app/repositories/opening_out_repository.py
    - alembic/versions/20261031_120000_b7e4c2a9f013_opening_out_metrics_and_percentile_color.py
    - tests/services/opening_out_seed.py
    - tests/services/test_opening_out_rates_parity.py
    - tests/integration/test_benchmark_metric_check.py
  modified:
    - app/services/canonical_slice_sql.py
    - app/services/global_percentile_cdf.py
    - app/services/opening_insights_constants.py
    - app/models/user_benchmark_percentile.py
    - app/models/benchmark_cohort_cdf.py
    - app/repositories/user_benchmark_percentiles_repository.py
    - tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py
    - tests/integration/test_alembic_migrations.py
    - tests/models/test_user_benchmark_percentile.py
    - tests/scripts/test_backfill_user_percentiles.py
    - tests/repositories/test_user_benchmark_percentiles_repository.py

key-decisions:
  - "ENUM alignment folded in: benchmark_metric becomes TEXT + CHECK in this phase's migration (rated costly, downgrade recreates the ENUM and casts back)"
  - "Storage shape: a color column ('all'|'white'|'black') in the PK, not per-colour metric ids, so the CDF and user rows share the two ids"
  - "Sub-800 games are dropped by the builder (A1), matching fetch_sweep.py and the other rate builders"
  - "A game with no phase = 1 ply is treated as ended before the middlegame (A9), as fetch_sweep.py does"

patterns-established:
  - "Baselines rendered parenthesised in SQL so a negative literal after a minus never forms a -- comment"
  - "Counts builder has no floor; the rate builder adds OPENING_OUT_MIN_GAMES_PER_COLOR on top of the same chain"

requirements-completed: [D-01, D-02, D-04, D-05]

coverage:
  - id: D1
    description: "Per-colour worse/better classification reproduces every D-01/D-02 edge case (cut boundaries, mate sign, first MG ply, early-ending result rule) against a real DB"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "tests/services/test_opening_out_rates_parity.py#test_counts_match_spec_per_color"
        status: pass
    human_judgment: false
  - id: D2
    description: "Canonical slice (37 months, +150 opponent, unrated, computer, other TC, sub-800) never counts; 30-game per-colour floor boundary (30 passes, 29 does not)"
    requirement: "D-05"
    verification:
      - kind: integration
        ref: "tests/services/test_opening_out_rates_parity.py#test_rate_builder_floor_boundary"
        status: pass
    human_judgment: false
  - id: D3
    description: "One builder body serves both sources (byte-identical, whitespace-normalised), counts builder has no floor, rate builder emits user_color/metric_value/n_games"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "tests/services/test_canonical_slice_per_user_vs_benchmark_parity.py#test_opening_out_rate_body_byte_identical_across_sources"
        status: pass
    human_judgment: false
  - id: D4
    description: "CdfMetricId gains exactly opening_worse_rate and opening_better_rate; DB CHECK equals the Literal (13 ids)"
    requirement: "D-04"
    verification:
      - kind: integration
        ref: "tests/integration/test_benchmark_metric_check.py#test_metric_check_equals_cdf_metric_id_literal"
        status: pass
    human_judgment: false
  - id: D5
    description: "Per-colour percentile rows coexist with the 'all' row; fetch_for_user returns only 'all'; Endgames upserts and reads unchanged"
    verification:
      - kind: integration
        ref: "tests/repositories/test_user_benchmark_percentiles_repository.py#test_fetch_for_user_returns_only_the_all_color_row"
        status: pass
      - kind: integration
        ref: "tests/services/test_endgame_ranked_parity.py"
        status: pass
    human_judgment: false
  - id: D6
    description: "Migration b7e4c2a9f013 upgrades, downgrades and re-upgrades on the dev DB with row counts preserved and no benchmark_metric type left"
    verification:
      - kind: other
        ref: "uv run alembic upgrade head && alembic downgrade -1 && alembic upgrade head; alembic check -> No new upgrade operations detected"
        status: pass
    human_judgment: false

duration: 11min
completed: 2026-10-31
status: complete
plan_head_before: a407bf766e3d8fb82050b49fd1ed335d4dd70adb
plan_head_after: ece18135114dc23791f82e1e52c91f15c6bb71e9
commits: 4
---

# Phase 243 Plan 01: Shared worse/better builder and percentile storage Summary

**One shared canonical-slice SQL builder classifies each game as worse/even/better out of the opening per colour (identical for the benchmark CDF and a single user), backed by TEXT + CHECK metric storage and a per-colour percentile PK.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-10-31T16:41:40Z
- **Tasks:** 3 (1 tracer, 2 auto)
- **Commits:** 4 (RED test, tracer GREEN, migration/models, storage tests)
- **Files:** 17 changed (5 created, 12 modified/renamed)

## Accomplishments

- `per_user_cte_opening_out_counts` / `per_user_cte_opening_out_rate` in `canonical_slice_sql.py`: first middlegame ply (`min(ply)` with `phase = 1`), user-POV eval minus the colour baseline against `OPENING_OUT_THRESHOLD_PAWNS` (White cut at eval_cp <= -75 / >= +125, Black mirrored), mate by sign, early-ending result rule (resignation, checkmate, timeout, decisive only), sub-800 drop, 30-game per-colour floor on the rate builder only. `_recent_capped_per_tc_cte` is untouched, so the 44 golden fixtures still pass.
- `fetch_opening_out_counts` repository returning `dict[Color, OpeningOutCounts]` from the single-user chain.
- Edge-case DB test: three cycles per colour of every boundary case (-75/-74/+125/+124 cp, mate +3/-2/0, NULL-eval entry, later MG ply ignored, six early-ending variants) plus six out-of-slice rows, floor boundary at 30/29, and eval-source independence across lichess / local-full / entry-lane flags. The oracle is each spec's `expected_side`.
- Mutation check on the tracer: removing the sub-800 drop, reversing the MG ply order, and moving the cut to 99 each make `test_opening_out_rates_parity.py` fail.
- Migration `b7e4c2a9f013`: `metric` ENUM to TEXT + CHECK on both tables, `color` column with CHECK, 4-column PK, reversible downgrade. Verified on dev with an upgrade/downgrade/upgrade round trip (122,661 CDF rows and 242 percentile rows preserved, `benchmark_metric` type count 0) and `alembic check` reports no drift.
- Storage tests: CHECK equals `CdfMetricId` (13 ids), colour CHECK, PK and default, per-colour upserts, `fetch_for_user` returns only `'all'` rows.

## Task Commits

1. **Task 1 RED:** `3b305e63f` test(243-01): failing opening-out builder tests
2. **Task 1 GREEN (tracer):** `8f44725ae` feat(243-01): shared out-of-the-opening worse/better SQL builder
3. **Task 2:** `222d1e952` feat(243-01): TEXT+CHECK metric column and per-colour percentile rows
4. **Task 3:** `ece181351` test(243-01): pin metric CHECK, colour PK and colour-agnostic Endgames read

Tracer gate: `<verify>` re-run end-to-end after the tracer commit (builder + parity tests + golden fixtures + ty/ruff/depth gate), passed, so expansion proceeded.

## Decisions Made

See `key-decisions` above. The ENUM-to-TEXT conversion is rated costly, and only rows on the 12 dead TC-suffixed labels are unrecoverable (dev had 0 such rows; the upgrade deletes them if present and logs the count at WARNING).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Drop the implicit varchar-to-benchmark_metric cast before dropping the type**
- **Found during:** Task 2
- **Issue:** The dev DB carries `CAST (varchar AS benchmark_metric) ... IMPLICIT` (created by the 1945ae56aa20 reshape for asyncpg). `DROP TYPE` cannot proceed while the cast depends on the type, and the plan's migration steps did not mention it.
- **Fix:** Upgrade runs `DROP CAST IF EXISTS (varchar AS benchmark_metric)` before `DROP TYPE`; downgrade recreates the cast after recreating the ENUM. A TEXT column needs no cast.
- **Files modified:** alembic/versions/20261031_120000_b7e4c2a9f013_opening_out_metrics_and_percentile_color.py
- **Commit:** 222d1e952

**2. [Rule 3 - Blocking] Reworded model docstring to keep the acceptance grep at 1**
- **Found during:** Task 2
- **Issue:** The docstring named `typing.get_args(CdfMetricId)` a second time, which would make `grep -c "get_args(CdfMetricId)"` return 2 instead of the required 1.
- **Fix:** Docstring refers to "the CdfMetricId Literal's members".
- **Commit:** 222d1e952

**Total deviations:** 2 auto-fixed (both Rule 3). **Impact:** none on scope.

## Issues Encountered

- `tests/scripts/test_backfill_user_percentiles.py` is skipped on import (`scripts.backfill_user_percentiles` was archived to `scripts/archive/`), so the removed enum cast in that test is edited but not executed. The archived script itself does `metric::text`, which is valid on a TEXT column, and was not touched.
- Wave-1 interim state: after commit 222d1e952 and before ece181351, `tests/models/test_user_benchmark_percentile.py` still imported the removed `benchmark_metric_enum`. Fixed in the next commit; the full suite is green at HEAD.

## Owner Follow-ups (not run by this phase)

- Pre-deploy on prod through the `flawchess-prod-db` MCP: `SELECT metric::text, count(*) FROM user_benchmark_percentiles GROUP BY 1` and the same for `benchmark_cohort_cdf`; expect only the 11 live labels. The migration deletes any other row and logs the count.
- The native `time_control_bucket` ENUM inside the widened PK is shared with `games` (a huge table); converting it stays out of scope.

## Known Stubs

None.

## Threat Flags

None. The new SQL surface is covered by the plan's T-243-01..04: only `TimeControlBucket` / `OpeningOutMetricId` Literals and int constants are interpolated, `user_id` flows through `CAST(:user_id AS int)` and `.bindparams()`, and the baselines render parenthesised.

## Verification

- `uv run pytest -n auto -x`: 5594 passed, 19 skipped.
- `uv run ty check app/ tests/ scripts/`, `uv run ruff check app tests`, `uv run ruff format`: clean.
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: no breaches.
- `tests/scripts/test_gen_global_percentile_cdf_unchanged.py`: passes (44 goldens untouched).
- `uv run alembic heads`: `b7e4c2a9f013 (head)`; dev `alembic current` is `b7e4c2a9f013`.
- Acceptance greps: builders 2, `opening_worse_rate` in the CDF module 3, `OPENING_OUT_THRESHOLD_PAWNS` 3, `"color"` in the repository 1, `get_args(CdfMetricId)` 1, `AS benchmark_metric` in the backfill test 0, whole-word `benchmark_metric_enum` 0, old enum test file gone.

## Next Phase Readiness

Ready for 243-02 (CDF regen over the new ids, using `per_user_cte_opening_out_rate(..., source="benchmark")` and the colour-aware peer rows) and 243-03 (Stage B colour rows via `upsert_percentile(..., color=...)`). `tests/services/opening_out_seed.py` is importable for both.

## Self-Check: PASSED

- FOUND: app/repositories/opening_out_repository.py, alembic/versions/20261031_120000_b7e4c2a9f013_opening_out_metrics_and_percentile_color.py, tests/services/opening_out_seed.py, tests/services/test_opening_out_rates_parity.py, tests/integration/test_benchmark_metric_check.py
- FOUND commits: 3b305e63f, 8f44725ae, 222d1e952, ece181351
