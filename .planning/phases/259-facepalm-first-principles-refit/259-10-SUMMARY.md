---
phase: 259-facepalm-first-principles-refit
plan: 10
subsystem: database
tags: [postgres, covering-index, alembic, create-index-concurrently, operator-script, facepalm]

requires:
  - phase: 259-09
    provides: "scalar score twin reading maia_played_prob, material_loss, material_missed, maia_best_prob, maia_best_reply_prob; strict xfail on the old index coverage test"
provides:
  - "ix_game_flaws_facepalm_inputs: covering partial index (user_id, game_id) INCLUDE the five scalar score inputs plus ply WHERE severity = 2"
  - "migration e2f6a8b0d259: CIC IF NOT EXISTS in autocommit_block (no-op on prod after the operator build)"
  - "scripts/build_facepalm_inputs_index.py: operator build-and-check (indisvalid + exact pg_get_indexdef), exit codes 0/3/4/5"
  - "facepalm_material.py reduced to the Python write-time aggregation"
affects: [259-11, 259-12, 259-14]

actuals:
  tokens: 24000
  tasks: 2
  commits: 2
commits: 2
plan_head_before: aa1694f15edae5c0f283bff1116dd82a7afd27a5
plan_head_after: e1efb51731a4cfdee72b971e80661d0e29e6af6a

tech-stack:
  added: []
  patterns:
    - "index DDL for prod is compiled from the ORM declaration (CreateIndex, if_not_exists, concurrently), never hand-typed; a test pins migration literal == compiled text"
    - "operator script classifies catalog state with a pure function (classify_index) and wraps it in an async reader, so drift branches are unit-testable without a database"

key-files:
  created:
    - alembic/versions/20261124_120000_e2f6a8b0d259_phase_259_ix_game_flaws_facepalm_inputs.py
    - scripts/build_facepalm_inputs_index.py
    - tests/scripts/test_build_facepalm_inputs_index.py
  modified:
    - app/models/game_flaw.py
    - app/services/facepalm_material.py
    - tests/services/test_flaw_comparison.py
    - tests/services/test_facepalm_material.py
    - tests/services/test_facepalm_score.py
    - tests/scripts/test_blunder_check_calibration.py
    - tests/facepalm_seed.py

key-decisions:
  - "The old index ix_game_flaws_blunder_facts stays until plan 14; a rollback of the switch keeps a usable index"
  - "check_index reports through a pure classify_index(state) so the mismatch, invalid and absent branches are tested without a database"
  - "single_depth_material had two test callers outside its own tests; re-pointed them to a tests/facepalm_seed helper lone_depth_line instead of keeping it in app/"

requirements-completed: [D-05, D-17]

coverage:
  - id: D1
    description: "Covering partial index over every column the scalar score reads, declared in the ORM and built by the migration"
    requirement: "D-17"
    verification:
      - kind: unit
        ref: "tests/services/test_flaw_comparison.py#test_facepalm_inputs_index_covers_every_score_input"
        status: pass
      - kind: command
        ref: "uv run alembic current -> e2f6a8b0d259 (head); uv run alembic check -> No new upgrade operations detected"
        status: pass
    human_judgment: false
  - id: D2
    description: "Migration SQL equals the compiled ORM index; the migrated test DB index is valid and equals the script's expected definition"
    requirement: "D-17"
    verification:
      - kind: unit
        ref: "tests/scripts/test_build_facepalm_inputs_index.py#test_migration_sql_equals_the_compiled_orm_index"
        status: pass
      - kind: integration
        ref: "tests/scripts/test_build_facepalm_inputs_index.py#test_expected_indexdef_matches_the_migrated_test_db"
        status: pass
    human_judgment: false
  - id: D3
    description: "Operator script detects a drifted, invalid or absent index (exit 4, 3, 5) and passes a valid exact one (exit 0)"
    requirement: "D-17"
    verification:
      - kind: unit
        ref: "tests/scripts/test_build_facepalm_inputs_index.py#test_check_reports_a_mismatch"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_build_facepalm_inputs_index.py#test_check_reports_invalid_and_absent"
        status: pass
      - kind: command
        ref: "uv run python scripts/build_facepalm_inputs_index.py --db dev (build, exit 0) and --check-only (exit 0)"
        status: pass
    human_judgment: false
  - id: D4
    description: "SQL aggregation builders removed; no reference remains in app/, scripts/ or tests/; full suite green"
    requirement: "D-05"
    verification:
      - kind: integration
        ref: "uv run pytest -n auto -x: 6915 passed, 8 skipped"
        status: pass
    human_judgment: false
  - id: D5
    description: "The index definition on a real prod table (build time, validity, planner use) is established by the operator in plan 11"
    verification: []
    human_judgment: true
    rationale: "Needs the prod tunnel and a write connection to prod; the executor has no prod access"

duration: 25min
completed: 2026-11-21
status: complete
---

# Phase 259 Plan 10: Covering Index for the Scalar Facepalm Inputs Summary

**A covering partial index ix_game_flaws_facepalm_inputs over the five scalar score inputs, built by a CIC IF NOT EXISTS migration and by a reproducible operator script that verifies validity and the exact definition, plus removal of the dead SQL aggregation builders.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-11-21T20:16:00Z
- **Completed:** 2026-11-21T20:41:00Z
- **Tasks:** 2/2
- **Files modified:** 10 (3 created)

## Accomplishments

- ORM declaration `Index("ix_game_flaws_facepalm_inputs", "user_id", "game_id", postgresql_include=[ply, maia_played_prob, material_loss, material_missed, maia_best_prob, maia_best_reply_prob], postgresql_where=text("severity = 2"))` next to the old index, with the keep-in-step comment. The old index is untouched.
- Migration `e2f6a8b0d259` (down `d2a6c8e0f259`): module constant `CREATE_SQL` runs inside `autocommit_block()`, downgrade runs `DROP INDEX CONCURRENTLY IF EXISTS`. Applied to dev; `alembic current` prints `e2f6a8b0d259 (head)` and `alembic check` finds no drift.
- `scripts/build_facepalm_inputs_index.py`: `build_sql()` compiles `CreateIndex(<ORM index>, if_not_exists=True)` with `concurrently` set for the compile only (restored in a `finally`, pinned by a test); `check_index(conn, drop_invalid=...)` reads `pg_index.indisvalid` and `pg_get_indexdef`; one autocommit connection (pool 1, no overflow); prints `statement_timeout`, `maintenance_work_mem` and the session count, sets `statement_timeout = 0` for its own session only; never prints the URL. Exit codes 0 ok, 3 invalid (prints the DROP, `--drop-invalid` runs it, still exit 3), 4 mismatch, 5 absent.
- Dev verification: the script's build is idempotent (second run exit 0), `--check-only` exit 0.
- SQL aggregation builders (`loss_by_depth_sql`, `gain_by_depth_sql`, `decaying_mean_sql`, `first_stable_sql`, `aggregate_sql`, `loses_sql`), `loses`, `single_depth_material` and the private SQL helpers removed; the module docstring now describes the write-time Python aggregation. Seven tests of the removed code dropped; the other tests keep every assertion.

### The dev `pg_get_indexdef` text (pasted into `EXPECTED_INDEXDEF`; plan 11 compares prod against it)

```
CREATE INDEX ix_game_flaws_facepalm_inputs ON public.game_flaws USING btree (user_id, game_id) INCLUDE (ply, maia_played_prob, material_loss, material_missed, maia_best_prob, maia_best_reply_prob) WHERE (severity = 2)
```

The compiled build statement (`build_sql()`, identical to the migration's `CREATE_SQL`):

```
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_game_flaws_facepalm_inputs ON game_flaws (user_id, game_id) INCLUDE (ply, maia_played_prob, material_loss, material_missed, maia_best_prob, maia_best_reply_prob) WHERE severity = 2
```

I wrote `EXPECTED_INDEXDEF` from the PostgreSQL text format before reading it on dev; the dev check then returned exit 0, so the pasted value equals what the migration built. Mutation check: changing `severity = 2` to `severity = 3` in `EXPECTED_INDEXDEF` fails `test_expected_indexdef_matches_the_migrated_test_db`; reverted.

## Task Commits

1. **Task 1: tracer, covering index from the ORM declaration through the migration to the operator check on dev** - `8b22755f9` (feat)
2. **Task 2: SQL aggregation builders and their tests removed** - `e1efb5173` (refactor)

**Plan metadata:** the commit that carries this SUMMARY (docs: complete plan)

## Decisions Made

- The old covering index stays until plan 14, as planned.
- `classify_index` is a pure function over an `IndexState | None`; `check_index` only reads the catalog and prints. This makes the mismatch, invalid and absent branches unit-testable without a fake connection.
- The tracer gate: Task 1's `<verify>` (alembic upgrade, `--check-only`, the index tests) was re-run after the commit-ready state and passed before Task 2 started.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `single_depth_material` had two callers outside its own tests**
- **Found during:** Task 2
- **Issue:** `tests/services/test_facepalm_score.py` and `tests/scripts/test_blunder_check_calibration.py` built lone-depth 9-slot arrays with it; the plan's acceptance grep requires no reference to it anywhere, and the Python functions the plan offers as re-point targets do not build such an array.
- **Fix:** Added `lone_depth_line` to `tests/facepalm_seed.py` (same body, test-only) and re-pointed both files to it. The function no longer exists in `app/`.
- **Files modified:** tests/facepalm_seed.py, tests/services/test_facepalm_score.py, tests/scripts/test_blunder_check_calibration.py
- **Verification:** both files pass in the full suite
- **Committed in:** `e1efb5173`

**2. [Rule 1 - Bug] Plan 09's strict xfail removed**
- **Found during:** Task 1
- **Issue:** `test_blunder_facts_index_covers_every_score_input` carried a strict xfail that would turn into XPASS(strict) once the new index covers the inputs (the context from plan 09 flagged this).
- **Fix:** Renamed and repointed to `test_facepalm_inputs_index_covers_every_score_input`; marker and comment removed.
- **Files modified:** tests/services/test_flaw_comparison.py
- **Committed in:** `8b22755f9`

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 expected cleanup)
**Impact on plan:** Both necessary to meet the plan's own acceptance greps and keep the suite green. No scope creep.

## Issues Encountered

- The full suite ran in 2:54 (`uv run pytest -n auto -x`: 6915 passed, 8 skipped), not the 14 minutes plan 09 saw; the prod operator job was apparently not starving the machine at this point (load average about 14). No flake this time.
- The task's TDD flag does not fit a pure deletion (no behavior added, so no meaningful RED); the gate was the unchanged Python tests plus the grep acceptance checks. No `TDD Gate Compliance` section applies (the plan type is `execute`).

## Known Stubs

None.

## Threat Flags

None. T-259-23 (an invalid or drifted index accepted by IF NOT EXISTS): `check_index` verifies `indisvalid` and the exact definition, `--drop-invalid` exists, and tests pin migration SQL == compiled ORM and the migrated test DB index == `EXPECTED_INDEXDEF`. T-259-24 (index build under a lock at container start): CONCURRENTLY IF NOT EXISTS inside `autocommit_block`; the prod build and the `--check-only` gate belong to plan 11 / the orchestrator. T-259-25 (URL disclosure): the URL comes from `db_url_for_target` and is never printed.

## Next Phase Readiness

- Plan 11 / the orchestrator builds the index on prod with `uv run python scripts/build_facepalm_inputs_index.py --db prod` (needs `bin/prod_db_tunnel.sh`), then gates the deploy on `--check-only` exit 0. Prod has about 4.7M `game_flaws` rows; the script lifts `statement_timeout` for its own session and prints `maintenance_work_mem` first so a low value is visible before a long build.
- Prod was not touched by this plan.

## Self-Check: PASSED

- Created files exist: the migration, `scripts/build_facepalm_inputs_index.py`, `tests/scripts/test_build_facepalm_inputs_index.py`.
- Commits `8b22755f9`, `e1efb5173` are ancestors of HEAD; `git rev-list --count aa1694f15..HEAD` = 2 at SUMMARY time.
- Acceptance: `grep -c ix_game_flaws_facepalm_inputs app/models/game_flaw.py` = 1 (>= 1); `alembic current` = `e2f6a8b0d259 (head)`; the removed-builder grep prints 0; `grep -c "_sql(" app/services/facepalm_material.py` = 0.
- Gates: `uv run ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`, `uv run ruff check .`, `uv run ruff format` (590 files unchanged) all clean; full suite 6915 passed.

---
*Phase: 259-facepalm-first-principles-refit*
*Completed: 2026-11-21*
