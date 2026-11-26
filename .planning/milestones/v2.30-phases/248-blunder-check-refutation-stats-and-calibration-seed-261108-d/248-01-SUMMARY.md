---
phase: 248-blunder-check-refutation-stats-and-calibration-seed-261108-d
plan: 01
subsystem: database
tags: [maia, game_flaws, alembic, scoring, refutation, python-chess]
status: complete

requires:
  - phase: 247-maia-stats-on-game-flaws
    provides: shared post-commit scorer (score_game_flaws_after_apply), maia_* columns, maia_flaws_completed_at stamp
provides:
  - game_flaws.maia_refutation_prob / maia_refutation_rank and games.maia_refutation_completed_at (migration c4e9b1d7f248)
  - go-forward refutation scoring on every lane (drain, /atomic-submit, /flaw-blob-submit, backfill full mode)
  - clear_maia_flaws_completed clearing both stamps
affects: [248-03 backfill refutation mode, 248 calibration report, prod deploy of phase 248]

actuals:
  tokens: 17400
  tasks: 3
  commits: 3
plan_head_before: 1ebbaa883
plan_head_after: 8c327c0e95ef553508c160ed149f7835a969e13a

tech-stack:
  added: []
  patterns:
    - "Refutation = COALESCE(game_positions.best_move, first pv token) at ply + 1, outer-joined on an aliased GamePosition inside the shared fingerprint SELECT"
    - "Post-blunder board = pre-push board .copy(stack=False) + played move; Elo from the PRE-push board's mover"
    - "Full-mode rows carry all ten Maia keys for every flaw so a re-score clears stale pairs"

key-files:
  created:
    - alembic/versions/20261109_120000_c4e9b1d7f248_phase_248_maia_refutation.py
  modified:
    - app/models/game_flaw.py
    - app/models/game.py
    - app/repositories/game_flaws_repository.py
    - app/services/maia_flaw_stats.py
    - app/services/maia_flaw_scoring.py
    - tests/services/test_maia_flaw_scoring.py
    - tests/services/test_maia_flaw_stats.py
    - tests/services/maia_fakes.py
    - tests/services/test_full_eval_drain.py
    - tests/test_eval_worker_endpoints.py

key-decisions:
  - "Separate stamp column games.maia_refutation_completed_at (no stamp version, no index); both stamps written together in full mode"
  - "Played-not-legal base failures skip the refutation pass without a second counted reason"
  - "refutations_from_pv counts scored in-scope pairs whose reply came from the pv fallback"
  - "Shared lane-assertion helper lives in tests/services/maia_fakes.py"

requirements-completed: [D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-20, D-22]

coverage:
  - id: D1
    description: "Metadata-only migration adds the three nullable columns; alembic check clean on dev"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py#test_schema_maia_columns_typed_nullable"
        status: pass
    human_judgment: false
  - id: D2
    description: "A user-side blunder gets Maia's probability and strict-greater rank for Stockfish's best reply in the exact post-blunder board at the blunderer's Elo, plus both stamps"
    requirement: "D-02"
    verification:
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py#test_refutation_tracer_user_blunder_scored_and_both_stamps"
        status: pass
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py#test_refutation_elo_is_the_blunderers_for_both_colors"
        status: pass
    human_judgment: false
  - id: D3
    description: "Scope is user-side blunders only for both colors; edge cases (pv fallback, missing/illegal/malformed reply, stalemate, en passant, castling, target-board immutability, fingerprint) are pinned"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py -k refutation (22 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Reclassify without Maia keeps surviving pairs, inserts NULL for new rows and clears both stamps; all three live lanes write the pair and both stamps"
    requirement: "D-08"
    verification:
      - kind: integration
        ref: "tests/services/test_maia_flaw_scoring.py -k reclassify; tests/services/test_full_eval_drain.py -k maia_flaw; tests/test_eval_worker_endpoints.py -k maia"
        status: pass
    human_judgment: false
---

# Phase 248 Plan 01: Go-forward refutation scoring Summary

**Maia probability and rank for Stockfish's best reply after each user-side blunder, written by the shared Phase 247 scorer on every lane (pair plus both stamps), with reclassification keeping or clearing it correctly.**

## Performance

- **Duration:** about 1h 20m (wall clock, dev box CPU loaded by the 247-07 backfill)
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files:** 1 created, 10 modified

## Accomplishments

- Migration `c4e9b1d7f248` (head on dev, `alembic check` clean): `game_flaws.maia_refutation_prob` REAL, `maia_refutation_rank` SMALLINT, `games.maia_refutation_completed_at` TIMESTAMPTZ, all nullable, no default, no CHECK, no index.
- Pure stats: `MaiaRefutationStats`, `null_refutation_stats`, `compute_refutation_stats` (reuses `_rank`), plus `no_legal_reply`, `refutation_missing`, `refutation_not_legal` reasons.
- Scorer: the fingerprint SELECT outer-joins an aliased `GamePosition` at `ply + 1` with `COALESCE(best_move, nullif(split_part(pv, ' ', 1), ''))`; the fingerprint widened with severity and the refutation UCI; `_mover_elo`, `_is_user_blunder` (via `mover_is_white_at_ply`), `_derive_refutation` (copy of the pre-push board, legality and malformed-UCI guards, zero inference for unusable replies), `_derive_flaw_values` replacing `_derive_flaw_stats`. Every flaw row carries all ten keys, so a full re-score writes NULL on rows downgraded from blunder.
- `write_game_maia_scores` stamps `maia_flaws_completed_at` and `maia_refutation_completed_at` together; `clear_maia_flaws_completed` clears both in one UPDATE (True when either was set).
- No call-site change in `eval_drain.py`, `eval_remote.py`, `eval_apply.py` (D-07).

## Task Commits

1. **Task 1 (tracer): schema, repository, pure stats, scorer, both stamps** - `036b50a65`
2. **Task 2: scope, Elo side, exact board, refutation source, fingerprint edges + mutation proofs** - `cd7da2530`
3. **Task 3: reclassify keeps or clears the pair; all lanes write it + mutation proofs** - `8c327c0e9`

The tracer feedback gate (auto-verified, `HUMAN_VERIFY_MODE` end-of-phase, automated-only verify): `alembic upgrade head && alembic check` clean and `pytest -k "refutation_tracer or schema"` green; expansion proceeded.

## Mutation Proofs (each reverted; tree equals the commit afterwards)

Task 2 (`tests/services/test_maia_flaw_scoring.py`):
- (a) `_is_user_blunder` returns True for opponent side: `test_refutation_scope_black_user_scores_only_own_blunders`, `test_refutation_scope_mistakes_and_opponent_stay_null[white...]`, `[black...]` failed.
- (b) Elo taken from the post-push board's mover: `test_refutation_elo_is_the_blunderers_for_both_colors[white-2-3-b8c6]` and `[black-3-4-f1b5]` failed.
- (c) `refutation_uci` dropped from `fingerprint_of`: `test_refutation_fingerprint_changed_skips_write[ply_plus_one_best_move]` failed.
- (d) played move pushed onto the given board: `test_refutation_target_boards_are_never_mutated` failed.
- (e) pv fallback removed from the COALESCE: `test_refutation_pv_fallback_when_best_move_null` and `test_refutation_unusable_reply_leaves_null_without_inference[None-a1a8 e2e4-refutation_not_legal]` failed.

Task 3:
- (a) `"maia_refutation_prob": None` added to `flaw_record_to_row`: `test_reclassify_without_maia_keeps_survivors_nulls_new_unstamps` and `test_reclassify_freshly_blobbed_survivor_keeps_values` failed.
- (b) `clear_maia_flaws_completed` clears only the base stamp: the same two reclassify tests plus `test_reclassify_clear_helper_clears_both_stamps[True-True-True]` and `[False-True-True]` failed.
- (c) `mark_maia_refutation_completed` call removed from `write_game_maia_scores`: `test_full_drain_tick_maia_flaw_scores_and_stamps`, `test_atomic_submit_maia_flaw_scores_and_stamps` and `test_blob_submit_maia_flaw_rescore_fills_second` failed.

The first run of Task 2 mutation (a) showed the white-user opponent case was not discriminating (the opponent's reply ply had no row, so it was NULL anyway); the test was strengthened with a legal reply at ply 6 and re-proven.

## Verification

- `uv run alembic upgrade head && uv run alembic check`: head `c4e9b1d7f248`, no drift.
- `uv run pytest -n auto -x`: 5823 passed, 20 skipped.
- `uv run ruff check .`, `ruff format --check app/ tests/`, `uv run ty check app/ tests/ scripts/`: clean. `check_function_size.py app/ --fail-over-depth 4`: no breaches.
- Acceptance greps: `maia_refutation_completed_at` appears in the migration, `compute_refutation_stats` and `mark_maia_refutation_completed` defined once each, `mover_is_white_at_ply` and `aliased(GamePosition)` present in the scorer.

## Decisions Made

- Separate stamp column (research option A) kept; stamped together with the 247 stamp in full mode only (no refutation-only mode in this plan).
- If the base `compute_maia_flaw_stats` fails with `played_not_legal` for an in-scope blunder, the refutation pass is skipped with no second reason, so one flaw never counts two reasons for the same defect.
- `refutations_from_pv` counts in-scope flaws whose pair was scored from the pv fallback (not NULL-reason bookkeeping).

## Deviations from Plan

### Auto-fixed / scope notes

**1. [Rule 3 - Blocking] Shared lane-assertion helper added to `tests/services/maia_fakes.py`**
- **Found during:** Task 3
- **Issue:** the drain and endpoint lane tests need the same user-side-blunder assertion; duplicating ~40 lines in two modules was worse, and `maia_fakes.py` is the shared 247 test helper module.
- **Fix:** added `assert_refutation_lane_state` there (not in the plan's `files_modified`).
- **Commit:** `8c327c0e9`

**2. [Task ordering] `clear_maia_flaws_completed` change landed in the Task 1 commit**
- The plan placed it in Task 3; it was written alongside the repository helpers in Task 1 because the models and stamp helper changed together. Its tests and mutation proof (b) are in Task 3.

**Total deviations:** 2 (one Rule 3, one ordering note). **Impact:** none on behavior; both are test/commit-structure only.

## Issues Encountered

- The first Task 2 test pass was green immediately; a review of the mutation results showed one non-discriminating case (see Mutation Proofs) which was fixed.
- `commits: 3` and `plan_head_before` are measured from the first plan commit's parent. Commits of plan 248-02 interleave in the same range (concurrent executor), so `rev-list` over the range would over-count; the 3 listed commits are this plan's own.

## Known Stubs

None.

## Threat Flags

None. T-248-01 (malformed/illegal worker-supplied reply) is mitigated by the `chess.Move.from_uci` ValueError guard and the `post.legal_moves` membership check before inference (tested). T-248-02 is mitigated by the widened fingerprint (tested, mutation proof (c)).

## Next Phase Readiness

Ready for the backfill refutation mode (plan 03) and deploy sequencing: the migration must only reach prod after Phase 247-07's backfill ends; no `alembic` command was run from the main checkout. `GameMaiaScore.user_blunders` and `refutations_from_pv` are available for the backfill report.

## Self-Check: PASSED

- Files exist: migration, `app/services/maia_flaw_stats.py`, `app/services/maia_flaw_scoring.py`, `app/repositories/game_flaws_repository.py`, `tests/services/test_maia_flaw_scoring.py`.
- Commits `036b50a65`, `cd7da2530`, `8c327c0e9` are ancestors of HEAD.
