---
phase: 247-maia-stats-on-game-flaws
plan: 02
subsystem: maia-flaw-scoring
tags: [maia, game_flaws, alembic, advisory-lock, eval-drain]
requires: ["247-01"]
provides:
  - "game_flaws.maia_* (8 nullable columns) and games.maia_flaws_completed_at, migration a7d3f1c9e247"
  - "app/services/maia_flaw_scoring.py: shared post-commit scorer (score_game_flaws_after_apply, load_game_maia_inputs, score_game, write_game_maia_scores, replay_flaw_boards, boards_from_targets, format_maia_backfill_reminder)"
  - "game_flaws_repository: MAIA_FLAW_COLUMNS, bulk_update_flaw_maia_stats, mark_maia_flaws_completed"
  - "eval_drain post-commit hook (local drain lane scores and stamps)"
affects: [247-03, 247-04, 247-05]
status: complete
commits: 3
plan_head_before: 617b4df0bfa29b014d9752e9dd53045e346a377f
plan_head_after: 60068187b9a660b00fc9ec9bb2ef78efb09c8f34
actuals:
  tokens: 15800
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns:
    - "post-commit scorer: short read session, asyncio.to_thread inference with no session open, short write session with ascending advisory locks plus an in-lock fingerprint re-read"
    - "stamp decided from maia_engine.is_maia_available() and pass completion, never from row counts"
key-files:
  created:
    - alembic/versions/20261108_120000_a7d3f1c9e247_phase_247_maia_flaw_stats.py
    - app/services/maia_flaw_scoring.py
    - tests/services/test_maia_flaw_scoring.py
  modified:
    - app/models/game_flaw.py
    - app/models/game.py
    - app/repositories/game_flaws_repository.py
    - app/services/eval_drain.py
    - tests/services/test_full_eval_drain.py
key-decisions:
  - "Scorer module imports full_policy by bare name so tests patch maia_flaw_scoring.full_policy (the drain tests and the new module tests both do)"
  - "Lock statement uses unnest WITH ORDINALITY ... ORDER BY ord OFFSET 0 over the Python-sorted key array, so lock acquisition order is explicit rather than incidental"
  - "Outcome precedence in write_game_maia_scores: game_missing, already_stamped (require_unstamped only), fingerprint_changed, stamped"
  - "replay_flaw_boards returns a game-level reason (pgn_unparseable, invalid_root) instead of capturing to Sentry; score_game counts it once per flaw"
requirements-completed: [D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-13, D-15]
---

# Phase 247 Plan 02: Scoring core Summary

Migration `a7d3f1c9e247` (eight nullable Maia columns on `game_flaws`, `games.maia_flaws_completed_at`), the shared post-commit scorer `app/services/maia_flaw_scoring.py` with advisory-locked, fingerprint-guarded writes, its repository helpers, and the local-drain hook in `_full_drain_tick`. A Maia-loaded drain apply now writes all eight values for every flaw of the game and stamps it; a Maia-absent apply writes and stamps nothing.

## Accomplishments

- Schema: nine columns added metadata-only (no default, CHECK, index or data UPDATE). `alembic upgrade head` applied to the dev DB; `alembic check` reports no drift; dev DB shows 9 `maia_%` columns across `game_flaws` and `games`. No `maia_elo` column.
- Scorer (D-13): read session, closed; `score_game` in `asyncio.to_thread` with no session open; write session locks every game in ascending key order, re-reads the fingerprint `(ply, fen, best_move, raw su)`, writes the eight columns plus stamp only on a match. Every flaw of the game is rewritten on each call (D-08), unscorable flaws as all-NULL rows with a counted `MaiaReason`.
- PGN replay path (D-06): `replay_flaw_boards` keeps castling and en-passant state; `fen_mismatch`, `invalid_root`, `pgn_unparseable`, `ply_beyond_mainline` are counted buckets and the game is still stamped.
- Drain hook: `score_game_flaws_after_apply(async_session_maker, game_id, targets=targets, source="full_eval_drain")` placed after `commit_unless_game_deleted` and before the `if not stamp_complete` Path-B return (so incomplete applies are scored too, literal D-08).
- Exceptions: `StaleDataError` (game deleted mid-write) logs at info and returns False; anything else goes to Sentry with `set_context("maia_flaws", {game_id, lane})`, tag `source=maia_flaws`, and never stamps.

## Tests

- `tests/services/test_maia_flaw_scoring.py` (22 tests): schema, castling/ep FEN, fen_mismatch, invalid root and unparseable, overwrite of stale and new rows, idempotency, fingerprint_changed, require_unstamped, game_missing, mixed batch, per-game advisory locks (pg_locks), oversized batch, Maia-absent no stamp, zero-flaw stamp, no_rating, board.turn Elo pinning, reminder, REAL precision, exception leaves unstamped, one `full_policy` call per scorable flaw, played_not_legal all-NULL row, D-15 second pair from the DB.
- `tests/services/test_full_eval_drain.py`: `test_full_drain_tick_maia_flaw_scores_and_stamps` (tracer), `test_full_drain_tick_maia_flaw_absent_leaves_unstamped`; `test_non_tier4b_claim_still_takes_full_path` now patches `maia_flaw_scoring.full_policy`. The tier-4b minimal-path sentinel tests pass unchanged.

## Mutation proofs

- Task 2: removing the fingerprint comparison failed `test_fingerprint_changed_skips_write` and `test_batch_mixed_outcomes`; removing the `is_maia_available()` guard failed `test_stamp_maia_absent_never_stamps`. Restored: 22 passed.
- Task 3: catching the inference exception and writing an all-NULL score plus stamp failed `test_scorer_exception_leaves_unstamped`; calling `full_policy` twice per flaw failed `test_one_full_policy_call_per_flaw` (and `test_replay_castling_and_ep_fen`). Restored: 90 passed across the scoring and drain test files.

## Verification

- `uv run pytest -n auto -q`: 5735 passed, 20 skipped (second run). The first `-x` run stopped on one failure in `tests/test_eval_worker_endpoints.py::test_lease_lifo`, which passes alone and in a serial run after the new module and did not recur in two further full runs; treated as a pre-existing flake, not investigated further.
- `uv run ty check app/ tests/ scripts/`: All checks passed. `uv run ruff check .` and `ruff format` clean. `check_function_size.py app/ --fail-over-depth 4`: no breaches.

## Deviations from Plan

None - plan executed as written. Notes:

- The plan's Task 1 listed `require_unstamped` handling as a Task 2 item; the `_outcome_for` helper already carried the `already_stamped` branch in Task 1's commit (the parameter had to exist for the signature). Task 2 added tests for it.
- A garbage (non-empty, non-PGN) string parses to an empty game in python-chess, so it surfaces as `ply_beyond_mainline` rather than `pgn_unparseable`; `pgn_unparseable` is reached for an empty string or a parser exception, and the tests cover both. All three buckets leave the flaws NULL and the game stamped.

## Follow-up notes

- `_full_drain_tick` is about 286 lines with cognitive complexity 23 (pre-existing, over the soft guidance of ~100 lines / 15). This plan only inserted one call; a split along its pipeline stages (claim, load, gather, write, post-commit) is a candidate for a scoped refactor.
- `format_maia_backfill_reminder` is defined but not yet called; plan 05 wires it into the reclassification scripts.

## Known Stubs

None.

## Threat Flags

None. T-247-02 (concurrent writers) is mitigated by the per-game advisory lock plus in-lock fingerprint re-read; T-247-03 (event loop starvation) by off-thread inference with no session held.

## Self-Check: PASSED

Files verified present: migration, `app/services/maia_flaw_scoring.py`, `tests/services/test_maia_flaw_scoring.py`. Commits 62a62d16f, 00a833a0c, 60068187b verified on the branch.
