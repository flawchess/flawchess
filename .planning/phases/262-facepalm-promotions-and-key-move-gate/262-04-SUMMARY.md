---
phase: 262-facepalm-promotions-and-key-move-gate
plan: 04
subsystem: operator-scripts
tags: [backfill, promotion, facepalm, material, dry-run, undo-log, float32]

requires:
  - phase: 262-facepalm-promotions-and-key-move-gate
    provides: plan 01 promotion rule in line_material (the single writer facepalm_material_inputs reads it)
provides:
  - scripts/backfill_promotion_material.py, the D-06 / D-07 row-scoped promotion pass (dry run, guarded real run, undo log, report)
  - public helpers for plan 05: as_real, promotion_candidate_filter, CandidateRow, replay_inputs
  - dev rehearsal numbers (dry run, real run, idempotent re-run) and the operator docs entry
affects: [262-05, 262-07, prod promotion pass after the deploy]

actuals:
  tokens: 14800
  tasks: 3
  commits: 3
plan_head_before: c8eb0ce0ac679c7ecd8319cbb4c7ca9b95fa8f3a
plan_head_after: ffef541beded5c81f9f8d2b8e6aae040cf9dc565

tech-stack:
  added: []
  patterns:
    - "Row-scoped in-place backfill: keyset pages on the PK, change-only guarded UPDATE, undo log of old and new values per applied row"
    - "REAL columns compared in 4-byte float form (as_real), never float64 at 1e-9"

key-files:
  created:
    - scripts/backfill_promotion_material.py
    - tests/scripts/test_backfill_promotion_material.py
  modified:
    - docs/dev-tooling.md

key-decisions:
  - "Dedicated row-scoped script instead of a mode of backfill_maia_flaws.py (RESEARCH Finding 5): line mode is game-scoped and cannot report would-change"
  - "The undo log file is created lazily (header plus rows) only when a page applies at least one row; a run that changes nothing leaves no undo file"
  - "The sample check lives in run_pass for dry runs only; exit code 3 is derived by exit_code_for, so tests and the CLI share it"

requirements-completed: [D-06, D-07]

status: complete
---

# Phase 262 Plan 04: Promotion pass Summary

A one-connection, re-runnable script recomputes the stored `material_loss` / `material_missed` of promotion-token blunders in place with the app's single writer, compares in 4-byte float form, writes only changed rows with a guarded UPDATE and logs every applied row for a replay-free rollback; proven on dev (799 candidates, 624 changed, re-run 0).

## Accomplishments

- Task 1 (tracer): the whole script plus three DB tests (real run, dry run, second run). Real run turns the stored (0.0, 0.0) of the `b1b3` / `c2c1q` row into (5.0, 0.0), the undo log holds the header and one line with old 0.0 / 0.0 and new 5.0 / 0.0, the dry run writes nothing and creates no undo file, the re-run changes 0.
- Task 2: 18 more tests (21 in the file): promotion in the best line, in `best_move` with `pv` NULL, as the played move (`a7a8q`, move_san `a8=Q`), a non-token blunder with a wrong stored pair stays untouched and is not a candidate, unstamped games and mistakes are out of scope, a stored-NULL row with the single-token line `c2c1q` becomes a value (`null_to_value` 1), a row already holding the new pair is unchanged, float32-only difference never written, `as_real` properties, type flips in both directions, a guard miss (concurrent rewrite between read and write keeps the concurrent value), the dry-run sample check (mismatch gives exit 3, no mismatch exit 0, token rows are not sampled), CLI flags (all eight) and `--db benchmark` rejected. Expected values come from `facepalm_material_inputs` in the test, not hand-typed numbers (except the pinned tracer pair 5.0 / 0.0 from plan 01).
- Task 3: dev rehearsal and the `docs/dev-tooling.md` bullet.

## Mutation check

`classify_change` changed to compare `new.loss, new.missed` without `as_real`: `test_float32_only_difference_is_never_written` and `test_float32_compare_in_classify_change_uses_the_4_byte_pair` fail (19 other tests pass). Reverted; 21 pass.

## Dev rehearsal (dev only, never prod)

Reports and the undo log are in the main checkout's gitignored temp dir (orchestrator-sanctioned write outside the worktree):

- Reports: `/home/aimfeld/Projects/Games/flawchess/temp/promotion-pass/promotion-pass-dev-dry-20261123T150949Z.md`, `.../promotion-pass-dev-run-20261123T151000Z.md`, `.../promotion-pass-dev-dry-20261123T151012Z.md`
- Undo log: `/home/aimfeld/Projects/Games/flawchess/temp/promotion-pass/undo-dev-rehearsal.tsv` (625 lines = 624 changed + header)

| Run | Candidates | Would change / changed | Loss up / down | Missed up / down | NULL to value | Type missed to allowed / reverse | Board failures | Guard misses | Sample checked / mismatches |
|---|---|---|---|---|---|---|---|---|---|
| 1. dry run | 799 | 624 would change | 354 / 53 | 241 / 102 | 0 | 243 / 44 | 0 | 0 | 437 / 0 |
| 2. real run | 799 | 624 changed | same | same | 0 | same | 0 | 0 | n/a (writes only) |
| 3. dry run after | 799 | 0 would change | 0 / 0 | 0 / 0 | 0 | 0 / 0 | 0 | 0 | 437 / 0 |

These match the research numbers (about 799 candidates, 624 would change; loss up 354, missed up 241, type flips 243 / 44). The first dry run ran from the worktree directly (`--db dev` credentials resolved), so no main-checkout cwd workaround was needed. The whole pass takes about 3 to 5 seconds on dev.

NOTE for later plans: dev `game_flaws` now holds the new-rule values for those 624 rows (the undo log can restore the old pair). Anything on dev that compares stored pairs against the old rule (for example a spike probe) will see them as already changed.

## Decisions and facts for plan 05 and plan 07

- Public and stable for plan 05's `refit_shift.py`: `as_real`, `promotion_candidate_filter(p0, p1)`, `CandidateRow(user_id, game_id, ply, fen, stored_loss, stored_missed, best_pv, best_move, refutation_pv)`, `replay_inputs(pgn, rows) -> (dict[ply, MaterialInputs], board_failures)`. Also available: `candidate_page_stmt`, `classify_change`, `RowChange`, `PassReport`, `exit_code_for`, `run_pass`, `write_report`, `main`.
- Prod run (plan 07): from the orchestrator, after the deploy, `PYTHONUNBUFFERED=1 setsid nohup uv run python scripts/backfill_promotion_material.py --db prod ...` over `bin/prod_db_tunnel.sh`, first `--dry-run` (exit 3 means do not run the real pass). The undo log defaults to `temp/promotion-pass/undo-prod-<stamp>.tsv` relative to the cwd; report to `reports/maia-flaws-backfill/`. The sample check is 2000 blunders at most with `game_id % 50 == 0` (437 rows on dev), deterministic by primary key order. The `--sample-size` flag is the only sample knob; the modulus is the constant `SAMPLE_GAME_MODULUS`.
- Sentry is initialised in `main` only when `settings.SENTRY_DSN` is set; a page error sets context `promotion_pass` (page, last game_id, last ply), captures and re-raises before the commit.

## Deviations from Plan

**1. [Rule 1 - Bug] Empty undo log file for a page with no applied rows**
- **Found during:** Task 2 (tests `test_row_already_holding_the_new_pair_is_unchanged`, `test_guard_miss_keeps_the_concurrent_write`)
- **Issue:** `_append_undo` wrote the header even when nothing was applied, leaving a header-only file for a no-op run.
- **Fix:** early return on an empty applied list; the undo log exists only when a row was applied.
- **Commit:** ce87bc4a7

**2. [Rule 1 - Bug] Test fixture built illegal PGN moves**
- **Found during:** Task 2, the default fixture and three others used the UCI `c2c1` without the promotion letter, which python-chess exports as an unparseable SAN.
- **Fix:** fixtures use `c2c1q`.
- **Commit:** ce87bc4a7

**3. Tracer scope.** The Task 1 commit contains the whole script, not only the tracer slice (the script is one file and its Task 2 behaviours were written together with it); Task 2's tests were written after the implementation rather than red first. They were verified non-vacuous by the float32 mutation check above and by asserting in each test that the expected pair differs from the stored wrong pair.

Otherwise the plan was executed as written.

## Verification

- `uv run pytest tests/scripts/test_backfill_promotion_material.py`: 21 passed.
- `ruff check scripts/ tests/`, `ruff format --check scripts/ tests/scripts`, `ty check app/ tests/ scripts/`, `check_function_size.py scripts/backfill_promotion_material.py --fail-over-depth 4` (27 functions, no breaches): all clean.
- `--help` lists `--db`, `--dry-run`, `--user-id`, `--limit`, `--throttle-ms`, `--sample-size`, `--report-dir`, `--undo-log`.
- Acceptance greps: `def promotion_candidate_filter` 1, `is_not_distinct_from` 2, `pool_size=1` 2, `backfill_promotion_material` in docs 1.
- The full backend suite was not run (no app code changed; the plan adds one script, its test and a docs line).

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. Mitigations in place: token filter scope (T-262-07), 4-byte compare, `board_fen()` guard, guarded UPDATE, undo log, sample check with exit 3; one connection, batched pages, throttle flag, read-only statement-timeout engine for dry runs (T-262-08); the DB URL is never printed, reports hold counters and at most 10 (game_id, ply) pairs, the undo log is in gitignored `temp/` (T-262-09); a page error is captured with context and re-raised before commit (T-262-10).

## Self-Check: PASSED

- scripts/backfill_promotion_material.py, tests/scripts/test_backfill_promotion_material.py, docs/dev-tooling.md (FOUND)
- commits 3952fd1be, ce87bc4a7, ffef541be reachable from HEAD (FOUND)
- undo log line count 625 = 624 + 1 (FOUND); `git status --porcelain` clean for temp/ (nothing from the rehearsal is in the worktree)
