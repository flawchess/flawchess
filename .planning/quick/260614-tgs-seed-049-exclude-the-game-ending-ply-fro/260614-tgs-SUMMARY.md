---
phase: quick-260614-tgs
plan: 01
subsystem: eval-drain
tags: [seed-049, eval-drain, resweep, hole-definition, tdd]
dependency_graph:
  requires: [SEED-045, SEED-044]
  provides: [correct-hole-definition, clean-checkmate-stamping]
  affects: [eval_drain.py, resweep_holed_games, full_eval_attempts]
tech_stack:
  added: []
  patterns: [ends_game-flag-threading, SQL-positional-guard]
key_files:
  created: []
  modified:
    - app/services/eval_drain.py
    - tests/services/test_full_eval_drain.py
decisions:
  - id: D-049-01
    text: "Positional guard ply < max_ply - 1 is exact and sufficient for both live drain and resweep; move_san '%#%' proxy is redundant. No board replay needed."
metrics:
  duration: ~30min
  completed: 2026-06-14T19:25:49Z
  tasks_completed: 3
  files_modified: 2
---

# Phase quick-260614-tgs Plan 01: SEED-049 Exclude Game-Ending Ply Summary

Corrected the SEED-045 hole definition to exclude the game-ending move ply from
`failed_ply_count` (live drain) and from `resweep_holed_games` (SQL predicate).
~99.9% of prod "holes" were this structural artifact; after the fix, checkmate-ending
engine games stamp complete on attempt 1 with `failed_ply_count == 0`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| RED | Failing SEED-049 regression tests | 3b62fc8e | tests/services/test_full_eval_drain.py |
| 1 + 2 | SEED-049 drain fix + resweep predicate | be29c8bd | app/services/eval_drain.py |
| 3 | Update resweep tests for new predicate | 4c571b47 | tests/services/test_full_eval_drain.py |
| style | Ruff formatting | ab7c74f2 | tests/services/test_full_eval_drain.py |

## What Was Built

**Task 1 (live drain -- `_apply_full_eval_results`):**

- Added `ends_game: bool = False` field to `_FullPlyEvalTarget` dataclass with
  docstring explaining the SEED-049 semantic.
- In `_collect_full_ply_targets`: when `include_terminal=True` and the final board
  `is_game_over()`, the existing path skips the terminal donor. The new `elif` branch
  sets `ends_game=True` on the last real target (`ply = ply_count - 1`) via a reverse
  scan. No change when the game ends by resignation/timeout (board not game-over).
- In `_apply_full_eval_results`: added a guard so `failed_ply_count` is NOT incremented
  when `target.ends_game is True`. Row is still written normally; only the count changes.
  Games that were previously going through the retry/cap path (3x churn) now stamp
  complete on attempt 1 (Path A).

**Task 2 (resweep predicate -- `resweep_holed_games`):**

- Added module-level constant `_GAME_ENDING_PLY_OFFSET: int = 1` so the `- 1` in
  the SQL predicate is not a bare magic number (CLAUDE.md).
- Updated `WHERE` clause from `ply < max_ply_per_game.c.max_ply` to
  `ply < max_ply_per_game.c.max_ply - _GAME_ENDING_PLY_OFFSET`. This single change
  covers checkmate, stalemate, and insufficient-material endings (all game-over
  terminal states) without board replay or move_san LIKE proxies.
- Updated docstring to explain the SEED-049 game-ending-move exclusion.

**Task 3 (regression tests -- `tests/services/test_full_eval_drain.py`):**

Three new tests in `TestSeed049GameEndingPly`:
1. `test_checkmate_game_stamps_complete_first_tick` -- Scholar's mate (7 plies):
   tick reports processed=True, `full_evals_completed_at IS NOT NULL`,
   `full_eval_attempts == 0`, ply 6 eval stays NULL, no cap Sentry event.
2. `test_midgame_null_still_retries` -- `_TWO_MOVE_PGN` with `*` result (board NOT
   game-over): terminal engine call returns `(None, None)` -- row 1 is a genuine hole
   -- tick reports `processed=False`, `full_eval_attempts` incremented to 1. (Path B unchanged.)
3. `test_resweep_skips_game_ending_ply` -- Game E (only hole at ply=max_ply-1) stays
   stamped; Game F (hole at ply < max_ply-1) is swept. Proves both sides of the predicate.

Also updated three existing `TestResweepHoledGames` tests that used 3-row fixtures
(hole at ply 1 = max_ply-1): changed to 4-row fixtures with the hole at ply 1 < max_ply-1=2.

## Decision Record

### D-049-01: Positional guard vs move_san proxy (decided)

**Decision:** Use `ply < max_ply - _GAME_ENDING_PLY_OFFSET` (positional guard only) in the
resweep SQL predicate. Do NOT add `move_san LIKE '%#%'` or a board-replay path.

**Rationale:** Under post-move storage, every game's last played move sits at
`ply = max_ply - 1` regardless of how it ended (checkmate, stalemate, insufficient
material, resignation, timeout). For games that end by resignation/timeout, the last
move's after-position is a normal, evaluable board -- so those rows would have a real
eval (not NULL), and the positional guard never fires on them. The `move_san '%#%'`
proxy covers only checkmate (1,333/1,379 observed false holes) and would miss stalemate
and insufficient-material endings. The positional guard alone covers all three game-over
terminal types exactly. No board replay is needed.

## Deviations from Plan

**[Rule 1 - Bug] Updated three existing resweep tests for SEED-049 predicate change**

- **Found during:** Task 2 implementation (running `TestResweepHoledGames` after predicate change)
- **Issue:** `test_sweeps_non_terminal_hole_only`, `test_dry_run_counts_but_does_not_update`,
  and `test_swept_game_has_attempts_reset` all used 3-row fixtures with a NULL hole at
  ply 1 = max_ply - 1 = 1. After SEED-049, that ply is the game-ending move ply --
  correctly excluded. The tests were testing the old behavior.
- **Fix:** Updated all three fixtures to 4-row setups (plies 0..3 with `_SIMPLE_PGN`)
  where the genuine hole is at ply 1 < max_ply - 1 = 2. The tests now correctly exercise
  the updated predicate semantics.
- **Files modified:** `tests/services/test_full_eval_drain.py`
- **Commit:** 4c571b47

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED
