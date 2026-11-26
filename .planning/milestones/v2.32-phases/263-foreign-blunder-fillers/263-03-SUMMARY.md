---
phase: 263-foreign-blunder-fillers
plan: 03
subsystem: api
tags: [train, sqlalchemy, tdd, owner-keyed-reads]

requires:
  - phase: 263-foreign-blunder-fillers
    provides: "263-01 tracer: DrillSource.FOREIGN_BLUNDER, the draw seam, _wire_game_id, owner-keyed answer keys"
provides:
  - "owner-keyed load_session_puzzles, _mark_session_complete_if_done and _composition_puzzle_types"
  - "_AssembledSessionItems.first_ever wired into the foreign draw as want_sharp (D-16)"
  - "tests/services/test_train_foreign.py (pure pick and sizing tests)"
  - "integration tests for resume, deletion, vanished flaw, D-01, D-02, D-05, D-06, D-16, D-17 and the herring collision"
affects: [263-04, 263-05, 263-06, 263-07, 263-08, 263-09, 263-10]

actuals:
  tokens: 12200
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "One `_OWNER_KEYED_SOURCES` tuple (SR_ITEM, FOREIGN_BLUNDER) shared by resume, completion and composition types"
    - "Flaw reads for these sources join Game on Game.user_id == GameFlaw.user_id instead of keying on the solver"

key-files:
  created:
    - tests/services/test_train_foreign.py
  modified:
    - app/repositories/train_repository.py
    - tests/repositories/test_train_foreign.py
    - tests/train_foreign_seed.py

key-decisions:
  - "first_ever is computed at the start of _assemble_session_items (one EXISTS query per composition, replacing the one in _order_first_ever_session), after _resolve_existing_session already ran"
  - "D-16 binds only where there is a foreign shortfall; a full own session is unchanged (research A5 interpretation)"
  - "_composition_puzzle_types lost its user_id parameter: the (game_id, ply) pairs come from the composition itself, the owner join replaces the solver filter"

patterns-established:
  - "Draw-seam spy (`_DrawSpy`) for tests that assert how often and with what level the foreign draw is called"

requirements-completed: [D-01, D-02, D-05, D-06, D-07, D-08, D-14, D-15, D-16, D-17]

coverage:
  - id: D1
    description: "Resume serves an unsolved foreign puzzle with its FEN rebuilt from the stranger's PGN, the key read from the owner's flaw row and wire game_id None"
    requirement: "D-07"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_foreign.py#test_resume_serves_foreign_puzzle_with_owner_key"
        status: pass
    human_judgment: false
  - id: D2
    description: "A deleted foreign game or a vanished owner flaw drops the puzzle on resume and never pins the session open"
    requirement: "D-08"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_foreign.py#test_deleted_foreign_game_dropped_and_session_completes"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_foreign.py#test_vanished_foreign_flaw_dropped_and_never_pins_session"
        status: pass
    human_judgment: false
  - id: D3
    description: "A first-ever session with a foreign shortfall prefers a sharp foreign blunder and opens on it"
    requirement: "D-16"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_foreign.py#test_first_ever_session_opens_on_sharp_foreign_blunder"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_foreign.py#test_composition_types_read_foreign_owner_blob"
        status: pass
    human_judgment: false
  - id: D4
    description: "Draw decisions: guests and own games excluded, level, six pool predicates, served positions, herring game, full own supply, nearest step"
    requirement: "D-01, D-02, D-05, D-06, D-17"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_foreign.py#test_draw_excludes_guest_and_solver_games"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_foreign.py#test_level_passed_to_draw"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_foreign.py#test_foreign_candidate_rejects_each_pool_predicate"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_foreign.py#test_foreign_never_served_twice_across_sessions"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_foreign.py#test_herring_game_excluded_from_foreign_pick"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_foreign.py#test_full_own_supply_draws_no_foreign"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_foreign.py#test_nearest_step_runs_only_on_short_band_step"
        status: pass
    human_judgment: false
  - id: D5
    description: "Pick rules: band first then nearest, served and excluded games, one per game, sharp only when wanted, no time-control input, seeded"
    requirement: "D-05, D-14, D-15, D-17"
    verification:
      - kind: unit
        ref: "tests/services/test_train_foreign.py"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-11-23
status: complete
plan_head_before: c928f1922c68a854700a63b90854e892482d5240
plan_head_after: 0f487f9fa6bb1a9437584009c8ffc00aecb8568a
commits: 2
---

# Phase 263 Plan 03: Owner-keyed resume, completion and composition types, D-16 and the draw tests Summary

**Resume, completion and the composition puzzle types now read the game owner's flaw rows, a deleted foreign game or vanished flaw never pins a session open, a first-ever session with a foreign shortfall opens on a sharp stranger blunder, and every draw decision has a test that fails without it.**

## Accomplishments

- Task 1 `49df64eb6`: `load_session_puzzles` collects the game ids of SR and foreign rows and reads flaw existence through `_existing_owner_flaw_keys` (join `Game.id == GameFlaw.game_id AND Game.user_id == GameFlaw.user_id`). A foreign row shares the SR reconstruction arm (game missing means dropped, flaw key missing means dropped, FEN not reconstructing means dropped) and uses `_wire_game_id`, so the wire `game_id` stays None. `_mark_session_complete_if_done` joins the flaw on `Game.user_id` and both orphan clauses use `source NOT IN (SR_ITEM, FOREIGN_BLUNDER)`; docstrings extended for D-08.
- Task 2 `0f487f9fa`: `_AssembledSessionItems.first_ever` (computed once in `_assemble_session_items`), passed as `want_sharp=first_ever` to `_backfill_foreign_blunders`, read by `_order_first_ever_session`. `_composition_puzzle_types` loads the blobs of SR and foreign puzzles through the owner join.
- Pure pick and sizing tests moved from `tests/repositories/test_train_foreign.py` into the new `tests/services/test_train_foreign.py` (8 tests, fixed seeds); the repository test file gained 4 new areas (resume and deletion, D-01, D-05, D-06 parametrized, D-16, D-17, D-02 and draw steps, herring collision).

## Counts and checks

- `grep -c "FOREIGN_BLUNDER" app/repositories/train_repository.py`: 9 after 263-01, 13 after this plan (the new arms use the shared `_OWNER_KEYED_SOURCES` tuple, so the literal count understates the sites converted).
- `grep -c "want_sharp=first_ever"`: 1. `grep -c "def test_" tests/services/test_train_foreign.py`: 8.

## Mutation checks (each reverted, tests restored green)

Task 1:

- Resume flaw-existence keyed on the solver (`GameFlaw.user_id == solver`): 3 failed, 14 passed. Failing assertions: `assert 0 == 2` (`len(resumed.puzzles)` in the resume test, session `puzzles=[]`) and `assert [] == [1]` / `assert [] == [0]` in the two drop tests.
- Completion orphan clauses left SR-only: 2 failed, 15 passed, `assert recorded.session_complete is True` fails (`session_complete=False`) in both the deleted-game and the vanished-flaw test.

Task 2 (each mutation run against `tests/repositories/test_train_foreign.py` and `tests/services/test_train_foreign.py`):

| Mutation | Failing test |
| --- | --- |
| D-16: composition types keyed on the solver (returns soft) | `test_first_ever_session_opens_on_sharp_foreign_blunder` |
| D-16: `want_sharp=False` | `test_first_ever_session_opens_on_sharp_foreign_blunder` |
| `_order_first_ever_session` ignores `first_ever` | `test_first_session_gate_blocks_an_expired_earlier_session`, `test_first_session_gate_blocks_an_earlier_completed_session` (existing tests) |
| D-17: served set empty | `test_foreign_never_served_twice_across_sessions` |
| herring game not excluded | `test_herring_game_excluded_from_foreign_pick` |
| D-02: draw called with shortfall 0 | `test_full_own_supply_draws_no_foreign` |
| D-02: no early break between steps | `test_band_step_covering_the_shortfall_skips_nearest` |
| D-05: level constant 1500 | `test_level_passed_to_draw[stored-level-beginner]` |
| D-01: guests allowed | `test_draw_skips_guest_strangers` |
| D-06: severity, mover, dead band, second best, winnability dropped | the matching `test_foreign_candidate_rejects_each_pool_predicate[...]` case each |
| D-06: `answer_key_present` dropped | none (see below) |

`answer_key_present` is subsumed in the draw statement by `dead_band_admissible` and `second_best_not_winning_admissible`, which already exclude a NULL or empty blob; both `no-blob` and `empty-blob` cases stay as regression guards but no test can distinguish that one predicate. The `D-01` own-game exclusion (`user_id != solver_id`) is covered by `test_draw_excludes_guest_and_solver_games` but was not mutated separately.

## Verification observed

- `uv run pytest -n auto -q` (full backend suite, after the last code and test edit): 7093 passed, 9 skipped.
- Targeted: `tests/repositories/test_train_repository.py tests/routers/test_train.py tests/repositories/test_train_foreign.py tests/services/test_train_foreign.py`: 374 passed.
- `uv run ruff check .` clean, `ruff format` unchanged, `uv run ty check app/ tests/ scripts/` clean, `check_function_size.py app/ --fail-over-depth 4`: 1702 functions, no breaches.

## Deviations from Plan

### Auto-fixed Issues

**1. [Structure] Pure tests moved, not duplicated**
- 263-01 had put `TestPickForeignCandidates` and `TestForeignDrawSizing` in `tests/repositories/test_train_foreign.py`. The plan names a new `tests/services/test_train_foreign.py` with eight specific tests, so the pure tests moved there (rewritten under the plan's names, extended with the time-control and seed cases) and were removed from the repository file. No coverage lost.

**2. [Structure] `_composition_puzzle_types` dropped its `user_id` parameter**
- With the owner join there is no solver filter left, so the parameter was dead. The only caller (`_order_first_ever_session`) was updated.

**3. [Rule 2 - Test seam] `test_pick_ignores_time_control` uses `platform="flawchess"` candidates**
- The pinned Elo of a lichess or chess.com rating legitimately depends on the time control (lichess 1500 pins to 1583 bullet, 1500 blitz, 1317 rapid). That is rating comparability, not a time-control preference. A flawchess rating is already blitz-equivalent, so only the time control differs between the variants.

**4. [Extra test] `test_later_session_draw_does_not_prefer_sharp`, `test_band_step_covering_the_shortfall_skips_nearest`, `test_empty_foreign_pool_composes_no_foreign_puzzle`**
- Beyond the named list: the first proves D-16 binds only to a first-ever session, the second the "called once" branch of the draw steps, the third the two-step cap on an empty pool.

## Known Stubs

None.

## Threat Flags

None. T-263-08 (owner-keyed reads): the game ids come from this solver's own drill_solves rows, only flaw keys and blobs are read, and the wire game id stays None (asserted in the resume test). T-263-09 (denial of service): the deletion and vanished-flaw tests prove completion. T-263-10 (guests, own games): proved by `test_draw_excludes_guest_and_solver_games`.

## Left for later plans

- Reveal and facepalm badge owner keying (263-06), removal of the transitional lichess sharp-filler stage and widening of the sharp-filler completion clause (263-07, 263-08), prod EXPLAIN of the draw (263-10).

## Self-Check: PASSED

- FOUND: tests/services/test_train_foreign.py, tests/repositories/test_train_foreign.py, tests/train_foreign_seed.py, app/repositories/train_repository.py
- FOUND commits 49df64eb6, 0f487f9fa on gsd/phase-263-foreign-blunder-fillers
