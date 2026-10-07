---
phase: 235-train-grading-server-answer-key
plan: 01
subsystem: api
tags: [train, answer-key, fastapi, sqlalchemy, python-chess, pydantic]

requires:
  - phase: 189-train
    provides: ComposedPuzzle/ComposedSession composition, classify_puzzle_type, herring_pool ladder
  - phase: 206-sharp-filler
    provides: SHARP_SET_BY_ID static sharp-filler set
provides:
  - "TrainPuzzle.key_move_uci / puzzle_type / runner_up_uci on every pre-attempt puzzle (fresh, resume, race-resume)"
  - "answer_key_for / legal_answer_key / PuzzleAnswerKey / TrainPuzzleType in app.services.train_pool (single derivation, reused by plan 03 at solve time)"
  - "_attach_answer_keys funnel and _answer_keys_by_position (one SELECT) in train_repository"
affects: [235-02, 235-03, 235-04, 235-05]

plan_head_before: e4897d1d0704cf6324a5cf20a0bd93f2d6a25d1b
plan_head_after: 7d500da591bf2bcb59a56f943ed6b1069a555e85

actuals:
  tokens: 21000
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "One post-composition funnel (_attach_answer_keys) covers every return path of compose_and_materialize_session"
    - "Source-gated outer joins: SR columns are passed to the pure derivation only for SR rows"

key-files:
  created: []
  modified:
    - app/services/train_pool.py
    - app/repositories/train_repository.py
    - app/schemas/train.py
    - app/routers/train.py
    - tests/routers/test_train.py
    - tests/services/test_train_pool.py
    - tests/repositories/test_train_repository.py

key-decisions:
  - "source not added to TrainPuzzle: puzzle_type (SR sharp and sharp filler both read 'sharp') is all the client needs for the D-10 re-check"
  - "runner_up_uci goes through the same legality check as the key (an illegal su can never be played, so dropping it cannot change the D-10 trigger)"
  - "Source gating lives in two layers: the repository passes SR columns only for SR rows AND answer_key_for returns the herring/filler branch before reading the blob"

requirements-completed: [D-05, D-06, D-07, D-19]

coverage:
  - id: D1
    description: "POST /api/train/sessions returns key_move_uci, puzzle_type and runner_up_uci on every unsolved puzzle; SR key = game_positions.best_move at the flaw ply, herring key = ladder[0].move_uci, sharp filler key = CSV solution_uci"
    requirement: "D-05, D-06"
    verification:
      - kind: integration
        ref: "tests/routers/test_train.py#test_pre_attempt_payload_carries_sr_answer_key"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_repository.py#test_compose_attaches_answer_keys_for_every_source"
        status: pass
    human_judgment: false
  - id: D2
    description: "Runner-up is the blob's su for a sharp SR item only; null for soft, herring, filler and the empty-string sentinel"
    requirement: "D-19"
    verification:
      - kind: unit
        ref: "tests/services/test_train_pool.py#TestAnswerKeyFor"
        status: pass
    human_judgment: false
  - id: D3
    description: "A missing best_move, or a key/runner-up illegal in the served FEN, degrades to null and the puzzle is still served"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "tests/services/test_train_pool.py#TestLegalAnswerKey"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_pre_attempt_payload_key_is_null_without_best_move"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_pre_attempt_payload_illegal_key_and_runner_up_are_null"
        status: pass
    human_judgment: false
  - id: D4
    description: "Docstrings (TrainPuzzle, schema module, PuzzleRevealResponse) record the D-05 rule and D-09"
    requirement: "D-05"
    verification: []
    human_judgment: true
    rationale: "Documentation wording; no test asserts docstring content"

duration: 38min
completed: 2026-10-07
status: complete
---

# Phase 235 Plan 01: Server answer key on the pre-attempt Train payload Summary

**Every unsolved Train puzzle now arrives with the server's key move, puzzle type (sharp/soft/herring) and, for sharp SR items, the runner-up, derived by one pure function and attached by one funnel that covers fresh, resumed and race-resumed sessions.**

## Performance

- **Duration:** ~38 min
- **Completed:** 2026-10-07
- **Tasks:** 2 (1 tracer, 1 auto/tdd)
- **Files modified:** 7

## Accomplishments
- `answer_key_for` (pure, never raises) maps the data the server owns to `(key, type, runner-up)` per source; `legal_answer_key` degrades any key not playable in the served FEN to null (D-07).
- `_attach_answer_keys` runs ONE query (`_answer_keys_by_position`) and is applied to the resolved (resume / completed) and freshly materialized return values of `compose_and_materialize_session`; the IntegrityError race-resume goes through the materialize return, so it is covered too.
- `TrainPuzzle` gained three optional fields; docstrings now state the Phase 235 rule (owner 2026-10-07: cheating is not a concern; the guess UI must still never display type or key before the attempt) and D-09 on `PuzzleRevealResponse`.
- 352 tests pass across the train service/repository/router trio; ruff, ty and the nesting gate are clean.

## Task Commits

1. **Task 1 (tracer): SR key, type and runner-up end to end** - `9d57f7dc3` (feat)
2. **Task 2: every source, legality, resume, own-game herring guard** - `1935b63c8` (test)
3. **D-09 docstring fix (see Deviations)** - `7d500da59` (docs)

## Files Created/Modified
- `app/services/train_pool.py` - `TrainPuzzleType`, `PuzzleAnswerKey`, `answer_key_for`, `legal_answer_key`
- `app/repositories/train_repository.py` - `ComposedPuzzle` key fields, `_answer_keys_by_position`, `_attach_answer_keys`, funnel wiring
- `app/schemas/train.py` - `TrainPuzzle` fields + rewritten module/class docstrings, D-09 on `PuzzleRevealResponse`
- `app/routers/train.py` - maps the three fields
- `tests/routers/test_train.py` - nine-key payload, SR key, null key, illegal key; `_seed_flaw_best_move` helper (plan 03 reuses it)
- `tests/services/test_train_pool.py` - `TestAnswerKeyFor`, `TestLegalAnswerKey`
- `tests/repositories/test_train_repository.py` - every-source fresh+resume test, own-game herring test

## Decisions Made
See `key-decisions` in the frontmatter. Notably: `source` is not on the wire; `runner_up_uci` is legality-checked like the key.

## Mutation proofs (reverted after observing)

- **b. `legal_answer_key` returns the key unchanged:** `TestLegalAnswerKey` went RED on 4 of 6 rows (illegal key, malformed UCI, illegal runner-up, unparseable FEN). Reverted.
- **a. Repository passes `missed_pv_lines`/`best_move` for every source (the plan's stated mutation):** stayed GREEN (2 passed). Reason: `answer_key_for` returns the herring branch before it ever reads the blob, so the repository gate is defense in depth, not the sole guard. Reported honestly rather than claiming red.
- **a'. Strengthened mutation (repository ungated AND `answer_key_for`'s herring branch only taken when no blob is passed):** `test_answer_keys_ignore_own_game_flaw_for_herring` and `TestAnswerKeyFor::test_herring_ignores_a_sharp_sr_blob` both went RED. Reverted. This proves the own-game guard bites once both layers are removed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] D-09 docstring paragraph silently missed its anchor**
- **Found during:** Task 2 acceptance check
- **Issue:** The scripted docstring edit for `PuzzleRevealResponse` matched no text (whitespace differed), so Task 1's commit lacked the D-09 paragraph while the module/TrainPuzzle docstrings were rewritten.
- **Fix:** Added the paragraph with the Edit tool and committed it separately.
- **Files modified:** app/schemas/train.py
- **Commit:** `7d500da59`

**2. [Deviation - plan assertion] Mutation (a) as written does not turn red**
- See "Mutation proofs": the plan expected the repository-only mutation to fail the own-game test; `answer_key_for`'s source-first branching makes that mutation harmless. Strengthened mutation a' verified the test.

**3. [Rule 2 - extra coverage] Added `test_pre_attempt_payload_illegal_key_and_runner_up_are_null`**
- The funnel's call to `legal_answer_key` was otherwise untested end to end (only the pure function was).

**Total deviations:** 3 (1 bug in my own edit, 1 plan-assertion correction, 1 added test). **Impact:** none on scope or contract.

## Issues Encountered
- The harness refused large heredoc-style Bash commands in the worktree ("too complex to verify"); test and docstring edits were applied with the Edit tool instead.

## Known Stubs
None.

## Threat Flags
None. T-235-02 (IDOR) mitigated: `_answer_keys_by_position` filters `DrillSolve.user_id == user_id` plus the server-composed `session_id`, and the SR joins match on `DrillSolve.user_id`.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 02 (client grading against the key) can read `key_move_uci`, `puzzle_type`, `runner_up_uci` from `TrainPuzzle`; an old SPA ignores the new keys.
- Plan 03 should reuse `answer_key_for` at solve time and the `_seed_flaw_best_move` router-test helper.

## Self-Check: PASSED

- Files present: all 7 modified files exist; `def answer_key_for`, `def legal_answer_key`, `class PuzzleAnswerKey`, `async def _attach_answer_keys` found by grep.
- Commits `9d57f7dc3`, `1935b63c8`, `7d500da59` are ancestors of HEAD; `git rev-list --count e4897d1d0..7d500da59` = 3.
- `uv run pytest tests/services/test_train_pool.py tests/repositories/test_train_repository.py tests/routers/test_train.py -n auto` = 352 passed; ruff format/check, ty and `check_function_size.py --fail-over-depth 4` exit 0.

---
*Phase: 235-train-grading-server-answer-key*
*Completed: 2026-10-07*
