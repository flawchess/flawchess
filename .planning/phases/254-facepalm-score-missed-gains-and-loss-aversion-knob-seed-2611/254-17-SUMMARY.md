---
phase: 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611
plan: 17
subsystem: database
tags: [facepalm-score, game_flaws, alembic, drop-column, cleanup]
requires:
  - phase: 254-13
    provides: "Writers stop, legacy line-loss mapping removed from line_material"
provides:
  - "No reader or writer of facepalm_score or the five legacy line-loss columns in app/, scripts/ or tests/ (gates G1 and G2 at 0)"
  - "Copy tool for the R1 to R2 transition deleted with its test"
  - "Migration c9f4e1a3d254 dropping facepalm_score and line_loss_1/3/5/7/9 from game_flaws; downgrade re-adds them empty"
  - "GameFlaw no longer maps the six columns"
affects: [254-14]
plan_head_before: a093179d3608be593d047ebdfd98968391633ae8
plan_head_after: e16f3e52e910d7f8b38e511b2e2f86e2f5456134
commits: 3
actuals:
  tokens: 13600
  tasks: 2
  commits: 3
tech-stack:
  added: []
  patterns:
    - "Drop migration in the f9c4d7e3a250 style: catalog-only DROP COLUMN, deploy rule in the docstring, downgrade re-adds the columns empty"
key-files:
  created:
    - alembic/versions/20261116_120000_c9f4e1a3d254_phase_254_drop_stored_score.py
  modified:
    - app/models/game_flaw.py
    - app/schemas/library.py
    - scripts/backfill_maia_flaws.py
    - tests/scripts/test_backfill_maia_flaws.py
    - tests/scripts/test_blunder_check_calibration.py
    - tests/services/test_maia_flaw_scoring.py
    - tests/test_library_repository.py
    - tests/test_query_utils.py
  deleted:
    - scripts/copy_line_material.py
    - tests/scripts/test_copy_line_material.py
key-decisions:
  - "The migration chains onto the current head c3f8e2a6d255 (Phase 255 feature-route seed), not a7d2c9e1b254 as the plan text said"
  - "line_mate_ply stays mapped: facepalm_expr still reads it"
requirements-completed: [D-01, D-02, D-19]
status: complete
coverage:
  - id: D1
    description: "No reader or writer of the dropped columns remains in app, scripts or tests"
    requirement: "D-19"
    verification:
      - kind: other
        ref: "G1 and G2 grep gates, both print 0"
        status: pass
  - id: D2
    description: "Drop migration round-trips on dev and the ORM no longer maps the six columns"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head"
        status: pass
      - kind: integration
        ref: "uv run pytest -n auto -x (6627 passed, 19 skipped)"
        status: pass
  - id: D3
    description: "Operator scripts run on the dropped schema"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "backfill_maia_flaws.py --db dev --status --mode spread --user-id 28; facepalm_features.py --db dev --extra 817357:24"
        status: pass
duration: 75min
completed: 2026-11-16
---

# Phase 254 Plan 17: Drop the stored score and the legacy line-loss columns Summary

The stored facepalm score and the five legacy line-loss columns are gone from the code, the ORM model and (via migration `c9f4e1a3d254`) the dev schema, after the transition-only copy tool was deleted and every remaining reader and writer was removed or moved onto the fact columns.

## Accomplishments

- **Task 1 (tracer, `989698612`, separate executor run).** Deleted `scripts/copy_line_material.py` and `tests/scripts/test_copy_line_material.py`. Reworded the two comments in `app/schemas/library.py` to name the query-time expression `facepalm_expr(FACEPALM_LIBRARY_LAMBDA)` (D-01). Updated the backfill module docstring so no mode mentions a stored score or line-loss columns. Removed the stored-column assertions from `tests/scripts/test_backfill_maia_flaws.py` and `tests/services/test_maia_flaw_scoring.py`. The negative SQL assertions in `tests/test_library_repository.py` and `tests/test_query_utils.py` now check for the bare token `facepalm_score`. Suite at that point: 6600 passed, 19 skipped.
  - Gate G1 (ORM attribute and SQL alias reads): before 8 lines, after 0.
  - Gate G2 (line-loss token outside the three legacy-TSV readers): before 5 files, after 1 file (`app/models/game_flaw.py`, removed in Task 2).
- **Task 2 (`e16f3e52e`, released by the owner after Task 1).** New migration `alembic/versions/20261116_120000_c9f4e1a3d254_phase_254_drop_stored_score.py` (revision `c9f4e1a3d254`, `down_revision = "c3f8e2a6d255"`) with six `drop_column` calls; the downgrade re-adds the six columns empty (REAL / SMALLINT, nullable). The docstring states what is dropped and why (score computed at query time, 254 D-01; arrays replace the loss columns, 254 D-09), what is kept, that DROP COLUMN is catalog-only, and the deploy rule (no operator script may run during the migration). `app/models/game_flaw.py` lost the six attributes and the comment lines naming them (kept: `line_mate_ply`, `maia_reply_spread`, the Phase 254 fact columns); the comment block now describes the dropped columns in words. Gates after Task 2: G1 0, G2 0.

## Verification

- `uv run alembic heads` before the migration: `c3f8e2a6d255 (head)`. After: `c9f4e1a3d254 (head)`, exactly one head.
- `uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` on dev: exit 0, upgrade c3f8e2a6d255 -> c9f4e1a3d254, downgrade, upgrade again; no traceback.
- Model column check (no `facepalm_score` / `line_loss_*` in `GameFlaw.__table__`): exit 0.
- `uv run ty check app/ tests/ scripts/`: all checks passed, exit 0. `uv run ruff check .`: passed. `uv run ruff format --check app/ tests/ scripts/ analysis/`: 617 files already formatted. `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`: OK, 1555 functions, no breaches.
- `uv run pytest -n auto -x`: 6627 passed, 19 skipped, exit 0 (after the one test fix below).
- `uv run python scripts/backfill_maia_flaws.py --db dev --status --mode spread --user-id 28`: exit 0, `spread_stamped_games=2880 spread_pending_games=0 user_blunders_total=5396 user_blunders_with_spread=5396 user_blunders_with_score=4557 user_blunders_qualifying=1883`.
- `uv run --group maia-inference python scripts/blunder_check/facepalm_features.py --db dev --extra 817357:24 --out temp/blunder-check/features-dev-254-17.tsv`: exit 0, `rows 1; pv_source: db 1; cache mismatches 0; rows with a NULL score input 0; rows with a NULL best line 0`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Migration chains onto `c3f8e2a6d255`, not `a7d2c9e1b254`**
- **Found during:** Task 2 start
- **Issue:** Phase 255 merged a migration (`c3f8e2a6d255`, feature-route seed) after the plan was written, so `a7d2c9e1b254` is no longer the head; chaining onto it would have created two heads.
- **Fix:** `down_revision = "c3f8e2a6d255"`, the single head `alembic heads` printed before the migration was added. The acceptance criterion became "down_revision equals the head printed before the migration, and `alembic heads` prints exactly one head after" (verified: `c9f4e1a3d254 (head)` only). Owner-directed, recorded here.
- **Files modified:** the new migration
- **Commit:** `e16f3e52e`

**2. [Rule 1 - Bug, gate miss] A keyword seed of the dropped column in `tests/scripts/test_blunder_check_calibration.py`**
- **Found during:** Task 2, first full-suite run (2 failures, `TypeError: 'facepalm_score' is an invalid keyword argument for GameFlaw`)
- **Issue:** The `make_game` fixture seeded a "stored decoy score" via `facepalm_score=STORED_DECOY_SCORE`, a keyword form that gates G1 and G2 do not match (neither pattern covers a bare keyword argument). The plan anticipated this case ("this would mean Task 1's gates missed a keyword seed, so record it").
- **Fix:** Removed the decoy constant, the keyword seed and the `!= approx(STORED_DECOY_SCORE)` assertion (the decoy only proved the report ignored a stored column that no longer exists); the surrounding comment now says the score is computed from the facts. The test still asserts the score equals the Python twin of the seeded facts.
- **Files modified:** `tests/scripts/test_blunder_check_calibration.py`
- **Commit:** `e16f3e52e`

**3. Interleaved commit.** `commits: 3` is the measured `git rev-list --count a093179d3..HEAD`; it includes `43c844511` (`docs(254-12)`, the one-hour Sentry check), which landed between Task 1 and Task 2 when the drop cycle branch was rebased onto origin/main. Plan 17's own code commits are `989698612` and `e16f3e52e`. No `.planning/STATE.md`, `ROADMAP.md` or `state.json` edits were made (owner instruction).

## Known Stubs

None.

## Threat Flags

None. T-254-37 mitigated by gates G1 and G2 before the migration, the model column check, the full suite on the dropped dev schema and both operator-script smoke runs. T-254-38: the work stays on the drop cycle branch; nothing was pushed or merged.

## Notes for plan 14

- The dev database schema is now at `c9f4e1a3d254` (round trip run on purpose, owner-approved). Any other checkout whose code still maps the dropped columns will fail against dev until it is rebased onto this branch.
- The migration is destructive on prod: the downgrade restores empty columns only. Deploy rule: no operator script may run while it executes.

## Self-Check: PASSED

- Migration file, `app/models/game_flaw.py`, this SUMMARY exist; `scripts/copy_line_material.py` and `tests/scripts/test_copy_line_material.py` are absent from `git ls-files`.
- Commits `989698612` and `e16f3e52e` are ancestors of HEAD on `gsd/phase-254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611`.
