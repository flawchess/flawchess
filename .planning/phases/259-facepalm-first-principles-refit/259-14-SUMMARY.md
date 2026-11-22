---
phase: 259-facepalm-first-principles-refit
plan: 14
subsystem: facepalm
tags: [facepalm, drop-release, migration, d-05, d-06, d-17, d-18]

requires:
  - phase: 259-13
    provides: "writers store the quiet scalars only; nothing outside the model and one shape-check test names the 9-slot arrays"
provides:
  - "Migration f3a7b9c1e259: DROP INDEX CONCURRENTLY of ix_game_flaws_blunder_facts, then the two shape CHECKs, then both array columns; downgrade re-adds them empty"
  - "GameFlaw model without the arrays, _material_array_shape, the shape CHECKs and the old index"
  - "D-18 outcome: keep; disable_jit_for_transaction stays with a docstring citing the measured numbers"
affects: [259-15]

actuals:
  tokens: 9000
  tasks: 2
  commits: 3
commits: 3
plan_head_before: 282c31aad2ef148ebebf8c785009d9142358ebc0
plan_head_after: c0ada4c5ca9c9fcc35c0970a2ab175c48cd9c943

tech-stack:
  added: []
  patterns:
    - "Autocommit-block DROP INDEX CONCURRENTLY IF EXISTS first, catalog-only column drops after"

key-files:
  created:
    - alembic/versions/20261128_120000_f3a7b9c1e259_phase_259_drop_material_arrays.py
  modified:
    - app/models/game_flaw.py
    - app/repositories/library_repository.py
    - tests/services/test_facepalm_score.py
    - tests/services/test_maia_flaw_scoring.py
    - tests/services/test_line_material.py

key-decisions:
  - "D-18 branch run: keep. The report's decision line is 'decision: keep' (comparison ratio 1.13 > 1.05), so no JIT code or tests were removed"
  - "The negative array-name assertions in test_maia_flaw_scoring.py use the shared suffix _line_material instead of the two column names, so the plan's no-reference gate stays at 0 without weakening the checks"

requirements-completed: [D-05, D-06, D-17, D-18]

duration: 15min
completed: 2026-11-22
status: complete
---

# Phase 259 Plan 14: Drop Release Code, Part Two Summary

**One-way migration f3a7b9c1e259 drops the two 9-slot material arrays, their NOT VALID shape CHECKs and the 741 MB old covering index (CONCURRENTLY, first), the model matches, and the JIT helper stays per the measurement.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-11-22T12:28:00Z
- **Completed:** 2026-11-22T12:44:00Z
- **Tasks:** 2
- **Files modified:** 5 modified, 1 created

## Accomplishments

- Task 1 (tracer): migration `f3a7b9c1e259` (down `e2f6a8b0d259`). Upgrade: `DROP INDEX CONCURRENTLY IF EXISTS ix_game_flaws_blunder_facts` in an autocommit block, then `DROP CONSTRAINT IF EXISTS` for both shape CHECKs, then `drop_column` for both arrays. Downgrade re-adds both columns (nullable `ARRAY(SmallInteger)`), the two NOT VALID CHECKs as a7d2c9e1b254 wrote them and the old index with b7e4a1c9d257's literal definition; values are not restored. The docstring states one-way in practice (D-06), ships only behind plan 15's decision, and that no operator script may run during the deploy.
- Model: both array columns, `_material_array_shape`, the two shape CheckConstraints and the old Index are gone; the old index's comment block moved onto `ix_game_flaws_facepalm_inputs`; the `ARRAY` import is dropped.
- Tests: `test_shape_check_rejects_malformed_arrays`, `test_shape_check_accepts_null_and_nine_slot_arrays` and their literal tables removed; `test_writers_store_no_material_array` now asserts no row key and no `GameFlaw` table column ends in `_line_material` (the old per-row `getattr` on a dropped column could no longer run); the scalar-only expression test checks the same suffix; `test_best_line_material_array_nine_slots` renamed to `test_best_line_nine_slot_material_values`.
- Task 2: the decision line of `reports/blunder-check/facepalm-jit-259.md` is `decision: keep`, so no code was removed. The `disable_jit_for_transaction` docstring now cites the report path and the measured numbers (comparison 287.2 ms JIT on vs 253.1 ms off, ratio 1.13, about 69 ms of JIT time; counts 195.6 vs 188.4, ratio 1.04). The two docstrings and one comment in `library_repository.py` that named the old index now name `ix_game_flaws_facepalm_inputs`.

## Task Commits

1. **Task 1: drop the arrays, CHECKs and old index** - `17b44836a` (refactor)
2. **Task 2: D-18 keep, docstring with measured numbers** - `c0ada4c5c` (docs)

The measured `commits: 3` over `plan_head_before..plan_head_after` includes `24f356735` ("docs: plant seed", an unrelated seed commit that landed on the branch between the two task commits); the plan itself made 2.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Tests and docstrings that named the dropped columns / index**
- **Found during:** Task 1
- **Issue:** `test_maia_flaw_scoring.py` read the dropped columns through `getattr` (would raise AttributeError) and named them in two negative literals; `test_line_material.py` had a test named after the array; `library_repository.py` named the old index in two docstrings and a comment. All hit the plan's zero-reference gates.
- **Fix:** suffix-based assertions, a rename, and the index name updated in the docstrings.
- **Files modified:** tests/services/test_maia_flaw_scoring.py, tests/services/test_line_material.py, app/repositories/library_repository.py
- **Committed in:** 17b44836a

**Total deviations:** 1 auto-fixed (blocking). **Impact:** no behavior change.

## Issues Encountered

`uv run ruff format app tests alembic` also reformatted ~85 historic alembic revisions (alembic is outside the project's format scope). Reverted them file by file; only the new migration is in the diff.

## Verification

- `uv run alembic upgrade head` on dev: `f3a7b9c1e259 (head)`; `downgrade -1` then `upgrade head` both ran cleanly and ended at head; `alembic check`: no new upgrade operations (model and schema agree).
- `uv run pytest tests/services/test_maia_flaw_scoring.py tests/test_library_router.py -k "material_inputs_and_reply_prob or facepalm" -x`: 45 passed.
- `uv run pytest -n auto -q`: 6861 passed, 8 skipped (count drops by the removed shape-check tests).
- `uv run ruff check .`, `ruff format --check app tests scripts analysis`, `uv run ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: clean.
- Gates: `_material_array_shape` in the model 0; `played_line_material|best_line_material` over app, scripts, tests (non-comment) 0; `ix_game_flaws_blunder_facts` over app, tests, scripts (non-comment) 0; `disable_jit_for_transaction` still 4 (keep branch).

## Known Stubs

None.

## Threat Flags

None. T-259-35 and T-259-36 mitigations are in the migration as planned (CONCURRENTLY first; downgrade re-adds columns and CHECKs).

## Next Phase Readiness

Plan 15 can put the one-way drop in front of the owner. Prod stays at `e2f6a8b0d259` until then; only dev has `f3a7b9c1e259`. The array values are not recoverable after the prod drop except by a line pass with the previous rule from git history.

## Self-Check: PASSED

- Commits `17b44836a` and `c0ada4c5c` are ancestors of HEAD.
- `alembic/versions/20261128_120000_f3a7b9c1e259_phase_259_drop_material_arrays.py` exists and contains `DROP INDEX CONCURRENTLY IF EXISTS ix_game_flaws_blunder_facts`.

---
*Phase: 259-facepalm-first-principles-refit*
*Completed: 2026-11-22*
