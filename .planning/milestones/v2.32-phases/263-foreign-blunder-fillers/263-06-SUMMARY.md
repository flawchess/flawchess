---
phase: 263-foreign-blunder-fillers
plan: 06
subsystem: api
tags: [train, reveal, privacy, owner-keyed-reads]

requires:
  - phase: 263-foreign-blunder-fillers
    provides: "263-01/03 owner-keyed helpers, _wire_game_id, _OWNER_KEYED_SOURCES, real_foreign_draw fixture, seed helpers"
provides:
  - "reveal_for_puzzle FOREIGN branch: owner's move, owner's flaw for type and facepalm, neutral game_info, no game id"
  - "PuzzleRevealResponse.game_info (GameInfo | None)"
  - "_game_move_is_facepalm(flaw_owner_id=...)"
  - "tests/routers/test_train_foreign.py (5 router tests, mutation-proven)"
affects: [263-07, 263-08, 263-09, 263-10]

actuals:
  tokens: 18000
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "GameInfo / TimeControlBucketWire now live in app.schemas.train (blunder_check imports them), the shared neutral-facts wire model"

key-files:
  created:
    - tests/routers/test_train_foreign.py
  modified:
    - app/repositories/train_repository.py
    - app/schemas/train.py
    - app/schemas/blunder_check.py
    - app/routers/train.py
    - app/routers/blunder_check.py
    - tests/routers/test_train.py

key-decisions:
  - "has_tactic_lines is False for a foreign blunder (the pointer would need the withheld game id; the tactic-lines endpoint reads the signed-in user's flaws)"
  - "The herring / own ownership gate on 'played in game' is untouched; a separate elif on FOREIGN_BLUNDER reads the owner's move_san"
  - "The reveal's not_found gate uses _OWNER_KEYED_SOURCES, so a solved foreign puzzle whose game is deleted answers 404 while drill_solves keeps the outcome (D-09)"

requirements-completed: [D-09, D-10, D-20, D-21]

duration: 30min
completed: 2026-11-23
status: complete
plan_head_before: 2114410dd9ecf71d69a5eb1a5e9d14e12526aedb
plan_head_after: 041bcff69
commits: 3
---

# Phase 263 Plan 06: Foreign reveal server side Summary

**The reveal of a solved foreign blunder now returns the stranger's move and the owner's puzzle type from the owner's rows, plus game_info with only time control, bucket, date and the mover's rating; game_id is null everywhere on the wire, and a deleted stranger game answers 404 while the solve's outcome stays.**

## Accomplishments

- Task 1 `d7ed429a7`: `RevealedPuzzle.game_info` (reuses `blunder_check_repository.GameInfoRow`), `_owner_move_san` and `_foreign_game_info` helpers (game info built from the already-loaded `Game` row, no second query), `reveal_for_puzzle` FOREIGN branch (owner move via a separate `elif`, owner-keyed flaw, `has_tactic_lines = False`, `_wire_game_id` on the returned `game_id`), the not_found gate widened to `_OWNER_KEYED_SOURCES`, `_game_move_is_facepalm(flaw_owner_id=...)` (SR call passes the solver, FOREIGN the game owner). Docstrings updated (D-09, D-20, D-21, why the herring gate stays).
- Task 2 `7febd768a`: `PuzzleRevealResponse.game_info`, `_game_info_schema` in the Train router, five router tests. `TrainPuzzle` / `PuzzleRevealResponse` docstrings state `game_id` is null for a foreign puzzle on purpose.
- Follow-up `041bcff69`: the two existing exact-key-set reveal tests in `tests/routers/test_train.py` now include `game_info` and assert it is null for an own puzzle and a cross-user herring.

## Mutation checks (each reverted, tests restored green; `tests/routers/test_train_foreign.py`)

| Mutation | Result |
| --- | --- |
| reveal `game_id=solve.game_id` instead of `_wire_game_id` | `test_foreign_puzzle_wire_has_no_game_id`, `test_reveal_foreign_game_info_names_nobody` fail |
| facepalm read keyed on the solver | `test_reveal_foreign_facepalm_reads_owner_flaw` fails |
| not_found gate left SR-only | `test_reveal_foreign_deleted_game_404_and_outcome_kept` fails |
| `game_info = None` for foreign | `test_reveal_foreign_game_info_names_nobody` fails |
| `_wire_game_id` returns the real id (compose wire) | `test_foreign_puzzle_wire_has_no_game_id`, `..._names_nobody` fail |
| flaw (type, facepalm) keyed on the solver | `test_reveal_foreign_reports_owner_game_move_and_type`, `..._facepalm_reads_owner_flaw` fail |
| owner SAN branch removed | `test_reveal_foreign_reports_owner_game_move_and_type` fails |

## Verification observed

- `uv run pytest -n auto -q` (full backend suite, after the last edit): 7099 passed, 9 skipped.
- `tests/routers/test_train_foreign.py`: 5 passed; `tests/routers/test_train.py`: 148 passed.
- `uv run ruff check .` clean, `ruff format` unchanged, `uv run ty check app/ tests/ scripts/` clean, `check_function_size.py app/ --fail-over-depth 4`: 1705 functions, no breaches.
- Acceptance greps: `GameInfoRow` 3 in train_repository.py, `game_info` in schemas/train.py present, `_game_info_schema` 2 in routers/train.py.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] GameInfo moved to app.schemas.train**
- **Found during:** Task 2. `app/schemas/blunder_check.py` already imports `ServerGradedMove` from `app.schemas.train`, so importing `GameInfo` the other way (as the plan says) is a circular import.
- **Fix:** defined `TimeControlBucketWire` and `GameInfo` in `app/schemas/train.py`; `blunder_check` imports `GameInfo` from there and the blunder check router imports `TimeControlBucketWire` from `app.schemas.train`. Wire shape and OpenAPI name unchanged.
- **Files modified:** app/schemas/train.py, app/schemas/blunder_check.py, app/routers/blunder_check.py
- **Commit:** 7febd768a

**2. [Rule 1 - Test breakage] Two existing reveal key-set tests**
- The new `game_info` key broke `test_reveal_key_set_excludes_stored_answer_key_fields` and `test_reveal_cross_user_herring_hides_game_move_and_no_owner_scope_leak`. Updated their expected key sets and added `game_info is None` assertions. Commit `041bcff69`.

**3. [Structure] Router tests seed the stranger email via a User select**
- The test needs the stranger's email to assert it is absent from the body; `add_stranger` returns only the id, so the scene helper reads it back. No change to `tests/train_foreign_seed.py` was needed (listed in the plan's files, left untouched).

## Known Stubs

None.

## Threat Flags

None. T-263-16 (disclosure): `game_info` carries four neutral fields, asserted by exact key set, no owner-identifying key anywhere in the body, and the stranger's email, its local part and label absent from the text. T-263-17: the `drill_solves` lookup keeps `user_id` and `session_id`; the owner reads follow only the row's own `(game_id, ply)`; existing foreign-session 404 test green. T-263-18: `has_tactic_lines` is False for a foreign puzzle (asserted).

## Left for later plans

- `motif` stays on the reveal response until 263-08 removes it with the CSV.
- Foreign tactic line pointer intentionally not offered (see key-decisions).

## Self-Check: PASSED

- FOUND: tests/routers/test_train_foreign.py, app/repositories/train_repository.py, app/schemas/train.py, app/routers/train.py
- FOUND commits d7ed429a7, 7febd768a, 041bcff69 on gsd/phase-263-foreign-blunder-fillers
