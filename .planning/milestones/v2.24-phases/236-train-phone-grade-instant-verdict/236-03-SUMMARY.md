---
phase: 236-train-phone-grade-instant-verdict
plan: 03
subsystem: api
tags: [train, server-graded-moves, seed-193, pydantic, parity]
requires:
  - phase: 235-train-recheck
    provides: answer_key_for, ServerGradedMove domain type, _resolve_grade path 1/2/3
  - phase: 236-01
    provides: phone_grade record (not consumed here)
provides:
  - "server_graded_moves_for / legal_server_graded_moves in train_pool (one shared derivation)"
  - "TrainPuzzle.server_graded_moves: list of wire ServerGradedMove(uci, tier) on every composed/resumed puzzle"
  - "PositionAnswerKey and ComposedPuzzle.server_graded_moves; HerringPool.mover_color in the composition select"
affects: [236-05 client instant path]
tech-stack:
  added: []
  patterns:
    - "one pure function shared by composition and the solve path so the pre-attempt list and the path-1 list cannot drift"
    - "wire twin with the same name as the domain dataclass (Phase 211 VettedMove precedent), tier-only"
key-files:
  created: []
  modified:
    - app/services/train_pool.py
    - app/repositories/train_repository.py
    - app/schemas/train.py
    - app/routers/train.py
    - tests/routers/test_train.py
    - tests/repositories/test_train_repository.py
    - tests/services/test_train_pool.py
key-decisions:
  - "server_graded_moves_for takes the RAW (pre-legality) key and never returns [] for a null key, because the solve path still grades a played su on a no-key soft puzzle (no grading change); the no-key and legality rules live in the composition-only legal_server_graded_moves"
  - "Herring color is the stored HerringPool.mover_color selected in the composition query; a herring row with no pool row gets no set"
requirements-completed: [D-03, D-08, D-10]
status: complete
commits: 2
plan_head_before: 730136d3e82012a14ca337d014aeb348c719fa87
plan_head_after: e032549cfc60c660fc163028db44a646cdc218b8
actuals:
  tokens: 45000
  tasks: 2
  commits: 2
---

# Phase 236 Plan 03: Server-graded move set on the pre-attempt payload Summary

Every unsolved puzzle from POST /api/train/sessions (fresh, resumed, IntegrityError-resumed) now carries `server_graded_moves`, a list of `{uci, tier}` composed by the same pure function the solve path uses, legal-filtered and empty when the puzzle has no legal key.

(`commits: 2` counts the two task commits; the SUMMARY commit follows them.)

## What was built

- **Task 1 (tracer)**, commit `3bb18d297`: `server_graded_moves_for` and `legal_server_graded_moves` in `train_pool`; `_position_answer_key` (source-gated, herring color from the stored column) and `PositionAnswerKey` in the repository; `_answer_keys_by_position` selects `HerringPool.mover_color`; `_attach_answer_keys` filters by legality and the no-key rule; wire `ServerGradedMove(uci, tier)` plus `TrainPuzzle.server_graded_moves`; router mapping; Phase 236 D-03/D-08 docstrings on the module, `TrainPuzzle` and `VettedMove`; contract test widened to the ten-key set; per-source router tests.
- **Task 2**, commit `e032549cf`: `_classify_sr_solve` and `_classify_herring_solve` derive `graded_moves` through `server_graded_moves_for` (they keep computing `vetted_moves` for display); the now-unused `graded_moves_from_vetted` / `sharp_runner_up_graded_move` imports were dropped from the repository. Tests: `TestServerGradedMovesFor`, `TestLegalServerGradedMoves`, `test_server_graded_moves_graded_parity_fresh_and_resumed`, `test_resolve_grade_instant_payload_tier_d10`.

## Verification

- `uv run pytest tests/services/test_train_pool.py tests/repositories/test_train_repository.py tests/routers/test_train.py -n auto -x`: 422 passed.
- ruff format/check, `ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: clean.
- Parity test is non-vacuous: soft == [(g1f3, good), (b1c3, good)], sharp == [(b1c3, wrong)], herring == [e2e4, d2d4, g1f3] all good, filler == [], asserted for fresh and resumed against `_classify_and_certify_solve` on each drill_solves row.
- Pre-existing `record_solve` / `_resolve_grade` / classification tests pass unmodified. The only pre-existing test lines removed are the three assertion lines in `test_answer_keys_ignore_own_game_flaw_for_herring` (`keys[0].puzzle_type`, `.runner_up_uci`, `.key_uci` became `keys[0].key.<attr>`, committed in Task 1).

## Mutation proofs (each reverted afterwards, tree clean)

| Mutation | Result |
| --- | --- |
| (a) `_position_answer_key` passes `herring_mover_color=None` | `test_server_graded_moves_graded_parity_fresh_and_resumed` FAILED on the herring row (`[] == [e2e4, d2d4, g1f3]`); `test_answer_keys_ignore_own_game_flaw_for_herring` also failed |
| (b) `_position_answer_key` passes `best_move=None` to `server_graded_moves_for` | parity test FAILED on the soft row (`[(b1c3, good)]` vs `[(g1f3, good), (b1c3, good)]`) |
| (c) `legal_server_graded_moves` drops the `legal_key_uci is None` early return | `test_pre_attempt_payload_no_key_sends_no_server_graded_moves` and `TestLegalServerGradedMoves::test_filter[null-key-gives-empty]` both FAILED |

## Deviations from Plan

None. Plan executed as written.

## Notes

- The per-plan commit ledger under `.git/worktrees/` is sandbox-blocked (as in plan 02), so `plan_head_before` is the dispatch base `730136d3e`; `git rev-list --count 730136d3e..HEAD` measured 2 before this SUMMARY commit.
- The harness refuses compound `git` Bash commands in the worktree; git was run as plain separate commands.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register (T-236-09..11): only uci and tier cross the wire (asserted by `set(ServerGradedMove.model_fields) == {"uci", "tier"}`); the composition select keeps `DrillSolve.user_id == user_id` and the user-scoped SR joins unchanged.

## Self-Check: PASSED

- FOUND: `server_graded_moves_for`, `legal_server_graded_moves` in app/services/train_pool.py and `__all__`; `HerringPool.mover_color` in `_answer_keys_by_position`; `server_graded_moves: list[ServerGradedMove]` in app/schemas/train.py; `server_graded_moves=` in app/routers/train.py
- FOUND commits: 3bb18d297, e032549cf
