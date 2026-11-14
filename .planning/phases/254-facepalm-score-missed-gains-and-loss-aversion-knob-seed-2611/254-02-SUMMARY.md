---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 02
subsystem: database
tags: [alembic, postgres, sqlalchemy, facepalm-score, check-constraint, not-valid, test-seeding]
requires:
  - phase: 254-01
    provides: "signed line-material facts (LineFacts.material_at, material_at_depth) that the new array columns will store"
  - phase: 254-15
    provides: "facepalm_score_sql / FacepalmColumns / FACEPALM_MODEL, the SQL twin facepalm_expr binds to the table"
provides:
  - "R1 migration a7d2c9e1b254: five nullable game_flaws columns, two NOT VALID array-shape CHECKs, games.facepalm_pre_completed_at"
  - "GameFlaw and Game ORM columns, with the CHECKs mirrored via postgresql_not_valid"
  - "facepalm_expr(lam, model): the single query-time facepalm score expression over the stored facts"
  - "tests/facepalm_seed.py: facepalm_fact_columns, seed_flaw_rows, SEED_FACEPALM_TOLERANCE / MARGIN"
affects: [254-16, 254-03, facepalm-readers, facepalm-fit]
tech-stack:
  added: []
  patterns:
    - "Instant migration: nullable ADD COLUMN without default plus CHECKs added NOT VALID via op.execute, no data UPDATE"
    - "Reader tests seed facts (closed-form played probability), never the stored score"
key-files:
  created:
    - alembic/versions/20261115_120000_a7d2c9e1b254_phase_254_facepalm_facts.py
    - tests/facepalm_seed.py
    - tests/services/test_facepalm_seed.py
  modified:
    - app/models/game_flaw.py
    - app/models/game.py
    - app/services/facepalm_score.py
    - tests/services/test_facepalm_score.py
    - tests/services/test_maia_flaw_scoring.py
key-decisions:
  - "facepalm_expr reads the GameFlaw columns directly and delegates every term rule to facepalm_score_sql, so the Python twin stays the single source of the formula"
  - "facepalm_fact_columns reads the rest of the linear predictor off the Python twin at a probe probability, then solves maia_played_prob in closed form; it is valid for any model shape without duplicating term rules"
  - "SEED_SPREADS widened to (1, 2, 4, 8, 16): the plan's (1, 4, 16) cannot reach a target near 0.05 under the shipped model"
requirements-completed: [D-01, D-09, D-12, D-17]
coverage:
  - id: D1
    description: "R1 migration is instant (nullable ADD COLUMN, NOT VALID CHECKs, no data UPDATE) and round-trips upgrade/downgrade/upgrade"
    requirement: "D-09"
    verification:
      - kind: other
        ref: "uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head (exit 0); uv run alembic check: No new upgrade operations detected"
        status: pass
    human_judgment: false
  - id: D2
    description: "Stored arrays must be NULL or one-dimensional 9-slot from index 1: empty, 3-slot, [0:8] and 2-D arrays are rejected, NULL / 9-slot / NULL-even-slot arrays pass, for both columns"
    requirement: "D-17"
    verification:
      - kind: integration
        ref: "tests/services/test_facepalm_score.py#test_shape_check_rejects_malformed_arrays"
        status: pass
      - kind: integration
        ref: "tests/services/test_facepalm_score.py#test_shape_check_accepts_null_and_nine_slot_arrays"
        status: pass
    human_judgment: false
  - id: D3
    description: "facepalm_expr over seeded game_flaws facts equals the Python twin for lam 0 and 1, across pre-refit, split, combined and best_prob_for_misses models, with NULL even slots, a NULL best array and a best mate at ply 0"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "tests/services/test_facepalm_score.py#test_expr_matches_python_twin_over_stored_facts"
        status: pass
      - kind: integration
        ref: "tests/services/test_facepalm_score.py#test_expr_reads_the_missed_term_from_the_stored_best_array"
        status: pass
    human_judgment: false
  - id: D4
    description: "Reader tests can seed facts for any reachable target score (band-edge targets within SEED_FACEPALM_TOLERANCE); a None target reads back NULL; an unreachable target raises"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "tests/services/test_facepalm_seed.py#test_seeded_facts_hit_the_target"
        status: pass
      - kind: integration
        ref: "tests/services/test_facepalm_seed.py#test_none_target_is_unscored"
        status: pass
      - kind: unit
        ref: "tests/services/test_facepalm_seed.py#test_unreachable_target_raises"
        status: pass
    human_judgment: false
  - id: D5
    description: "Behaviour unchanged (D-12): no reader moved to the expression, the hook is untouched, and the full backend suite is green on the new schema"
    requirement: "D-12"
    verification:
      - kind: integration
        ref: "uv run pytest -n auto -q (6462 passed, 19 skipped)"
        status: pass
    human_judgment: false
duration: 55 min
completed: 2026-11-14
status: complete
plan_head_before: c998a256e5cbbd5f52be51dfd72b70f1f86d4d2a
plan_head_after: b63689f605fa791716b61ec8cffd162d5d18bf35
commits: 5
actuals:
  tokens: 8100
  tasks: 2
  commits: 5
---

# Phase 254 Plan 02: Facepalm facts storage and the query-time expression Summary

**Instant R1 migration for the missed-gains facepalm facts (five nullable game_flaws columns plus two NOT VALID array-shape CHECKs), the single `facepalm_expr(lam)` SQL expression bound to them, and a facts-based seeding helper for reader tests.**

## Performance

- **Duration:** about 55 min (estimate; the start time was not captured)
- **Completed:** 2026-11-14
- **Tasks:** 2 (a tracer and a TDD task)
- **Files modified:** 8 (3 created, 5 modified)

## Accomplishments

- Migration `a7d2c9e1b254` (down revision `f9c4d7e3a250`) adds `played_line_material` and `best_line_material` (`SMALLINT[]`), `best_line_mate_ply` (`SMALLINT`), `maia_best_prob` and `maia_pre_spread` (`REAL`) to `game_flaws` and `facepalm_pre_completed_at` to `games`. Both array CHECKs (`cardinality = 9 AND array_lower = 1 AND array_ndims = 1`, NULL allowed) are added `NOT VALID` through `op.execute`; there is no data UPDATE. `alembic check` reports no drift between the models and the migration.
- `facepalm_expr(lam, model=FACEPALM_MODEL)` builds `FacepalmColumns` from the GameFlaw fact columns and returns `facepalm_score_sql`; the docstring states the D-01 contract (own lambda constant per reader, bind once, same object in SELECT and WHERE).
- `tests/facepalm_seed.py`: `facepalm_fact_columns(target, *, lam, model)` returns GameFlaw keyword values whose expression equals the target (or an unscored fact set for `None`), and `seed_flaw_rows` inserts a rollback-scoped game with one blunder flaw per fact row.
- Shape CHECK tests cover all four bad shapes and three good shapes on both columns; the expression test compares SQL and the Python twin on stored rows with NULL even slots, a NULL best array and a best mate at ply 0, for lam 0 and 1 over four model shapes.

## Task Commits

1. **Task 1 (tracer): migration, model columns, facepalm_expr** - `530509ab5` (feat)
2. **Task 2 (TDD RED): failing seeding tests** - `609c3b1da` (test)
3. **Task 2 (TDD GREEN): facts-based seeding helper** - `f5d5d87c2` (feat)
4. **Task 2 (refactor): stored-facts tests use the shared seed helper** - `b388044d8` (refactor)
5. **Schema test update for the new maia_ columns** - `b63689f60` (fix)

Tracer gate: the tracer `<verify>` is automated-only, so it was re-run end to end (alembic round trip, then 23 selected tests and the file's full 95) before the expansion task.

## TDD Gate Compliance

- **RED:** `tests/services/test_facepalm_seed.py` (6 tests) failed on the target behaviour: `facepalm_fact_columns` was a stub raising `NotImplementedError`, so every target test failed on the planned function, and `test_unreachable_target_raises` failed because ValueError was not raised. The `gsd_run check tdd-red-evidence` classifier was not run (no supported TAP/JUnit record was captured; the pytest console output was inspected by hand). Semantic assessment: the target tests executed and failed for the intended reason (feature missing), not for an import, fixture or collection fault; `seed_flaw_rows` was already real so the DB fixture path ran.
- **GREEN:** 6 passed.
- **REFACTOR:** the Task 1 test-local insert helper moved onto `seed_flaw_rows`; tests still pass.

## Files Created/Modified

- `alembic/versions/20261115_120000_a7d2c9e1b254_phase_254_facepalm_facts.py` - R1 migration with docstring on column meaning and why it is instant
- `app/models/game_flaw.py` - five ORM columns, both CHECKs with `postgresql_not_valid=True`
- `app/models/game.py` - `facepalm_pre_completed_at`
- `app/services/facepalm_score.py` - `facepalm_expr`
- `tests/facepalm_seed.py` - facts-based seeding helper and DB insert helper
- `tests/services/test_facepalm_seed.py` - seeding round-trip tests
- `tests/services/test_facepalm_score.py` - expression-over-stored-facts and shape CHECK tests
- `tests/services/test_maia_flaw_scoring.py` - schema test expects the two new maia_ columns

## Decisions Made

See key-decisions. The seed probes the Python twin at a fixed played probability and reads the remaining linear predictor off it, so the helper keeps working if a refit changes the model shape (spread form, material form) without a second copy of the term rules.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SEED_SPREADS (1, 4, 16) cannot reach a 0.05 target**
- **Found during:** Task 2 (working the closed-form solve by hand before implementing)
- **Issue:** under the shipped model a loss-0 row with spread 4 scores at least 0.060 (at played_prob 1.0) and with spread 16 at most 0.025, so the plan's required target 0.05 had no grid point whose solved probability lies in [SEED_PROB_MIN, 1.0].
- **Fix:** `SEED_SPREADS = (1.0, 2.0, 4.0, 8.0, 16.0)`; spread 8 reaches 0.05 at played_prob about 0.17.
- **Files modified:** tests/facepalm_seed.py
- **Verification:** `test_seeded_facts_hit_the_target` passes for all six targets under the shipped and a combined-form model.
- **Committed in:** `f5d5d87c2`

**2. [Rule 3 - Blocking] Schema test pinned the exact maia_ column set**
- **Found during:** Task 2 (full-suite run)
- **Issue:** `tests/services/test_maia_flaw_scoring.py::test_schema_maia_columns_typed_nullable` asserts `game_flaws` has exactly `maia_played_prob` and `maia_reply_spread` among its `maia_` columns; the migration adds `maia_best_prob` and `maia_pre_spread`.
- **Fix:** added both REAL columns to the expected set and updated the assertion message.
- **Files modified:** tests/services/test_maia_flaw_scoring.py
- **Verification:** 58 passed in that file; full suite green.
- **Committed in:** `b63689f60`

---

**Total deviations:** 2 auto-fixed (1 bug in a plan constant, 1 blocking test expectation)
**Impact on plan:** both necessary; no scope change.

## Issues Encountered

- The per-plan commit ledger could not be used from the worktree; `plan_head_before` is the dispatch base SHA and `commits: 5` was measured with `git rev-list --count` against it.
- The CLAUDE.md `ty` command reports zero errors after `uv sync --locked --group maia-inference`.
- Dev database Alembic revision on return: `a7d2c9e1b254` (head). The migration was applied to the shared dev database (round-tripped down and up again); it is additive and nullable.

## Known Stubs

None.

## Threat Flags

None. T-254-04 mitigated (nullable ADD COLUMN without default, CHECKs NOT VALID, no data UPDATE); T-254-07 mitigated (each bad array shape is inserted in a test and rejected by the named constraint).

## Next Phase Readiness

Plan 16 can write the new facts from the hook (`played_line_material`, `best_line_material`, `best_line_mate_ply`, `maia_best_prob`, `maia_pre_spread`, `games.facepalm_pre_completed_at`); the CHECKs reject anything but NULL or a one-dimensional 9-slot array starting at index 1. Reader plans can call `facepalm_expr(<own lambda>)` and seed with `facepalm_fact_columns` / `seed_flaw_rows`. The sign-flipped copy of `line_loss_*` into `played_line_material` is an operator tool, still to be built.

## Self-Check: PASSED

Files exist (migration, `tests/facepalm_seed.py`, `tests/services/test_facepalm_seed.py`); commits `530509ab5`, `609c3b1da`, `f5d5d87c2`, `b388044d8`, `b63689f60` are on HEAD. Verified: alembic upgrade/downgrade/upgrade exits 0, `alembic check` clean, `uv run pytest -n auto -q` 6462 passed / 19 skipped, `uv run ty check app/ tests/ scripts/` clean, `ruff check .` clean, `check_function_size.py app/ --fail-over-depth 4` clean.
