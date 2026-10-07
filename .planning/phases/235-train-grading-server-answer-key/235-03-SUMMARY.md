---
phase: 235-train-grading-server-answer-key
plan: 03
subsystem: api
tags: [train, grading, alembic, jsonb, pydantic, fastapi, sqlalchemy]

requires:
  - phase: 235-train-grading-server-answer-key
    provides: "answer_key_for / PuzzleAnswerKey (plan 01) reused at solve time"
provides:
  - "drill_solves.recheck JSONB nullable column (migration c5e8a2d7b914)"
  - "SolveRecheck boundary model + SolveRequest.recheck (drop-to-None) + SolveResponse.disagreement"
  - "ServerGradedMove / graded_moves_from_vetted / sharp_runner_up_graded_move in train_pool"
  - "Pure _disagreement_accepted and _resolve_grade in train_repository; record_solve(recheck=...)"
affects: [235-04, 235-05]

plan_head_before: 344eaec30eb29220a166ebca96bcd7a90fe4b990
plan_head_after: 43624c016daa0ba946607a9bb5b1776497ad0a91

actuals:
  tokens: 60000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "One pure grading decision (_resolve_grade) instead of an inline override block in record_solve"
    - "Source-split classification helpers (_classify_herring_solve / _classify_filler_solve / _classify_sr_solve) behind a thin dispatcher"
    - "Wrap-validator drop-to-None for a grading-adjacent optional payload (same contract as telemetry)"

key-files:
  created:
    - alembic/versions/20261007_120000_c5e8a2d7b914_drill_solves_recheck.py
    - tests/schemas/test_train_recheck_schema.py
  modified:
    - app/models/drill_solve.py
    - app/schemas/train.py
    - app/services/train_pool.py
    - app/repositories/train_repository.py
    - app/routers/train.py
    - tests/routers/test_train.py
    - tests/repositories/test_train_repository.py
    - tests/services/test_train_pool.py

key-decisions:
  - "ES-pair consistency lives in _disagreement_accepted, not the schema: an inconsistent record is still stored (accepted false) for review (D-17)"
  - "A claim on a non-sharp or changed puzzle is recorded and grants nothing, never a 422 (Pitfall 4)"
  - "No server override for played == key on sharp/filler: treated as 'not a disagreement'"
  - "_classify_and_certify_solve split by source to keep it shallow; SR branch now reads best_move whenever the row has a game_id so the solve-time key uses exactly the composition-time inputs"

requirements-completed: [D-02, D-04, D-13, D-14, D-17, D-18, D-20]

coverage:
  - id: D1
    description: "drill_solves.recheck JSONB column exists, upgrade/downgrade round-trips, a solve without a recheck leaves it SQL NULL"
    requirement: "D-18"
    verification:
      - kind: integration
        ref: "tests/routers/test_train.py#test_solve_without_recheck_stays_sql_null_and_grades_as_before"
        status: pass
    human_judgment: false
  - id: D2
    description: "A confirmed re-check on a live sharp puzzle credits either guess (tier good, disagreement true) and is stored with accepted true"
    requirement: "D-14, D-17"
    verification:
      - kind: integration
        ref: "tests/routers/test_train.py#test_recheck_confirmed_on_sharp_credits_either_guess"
        status: pass
      - kind: unit
        ref: "tests/repositories/test_train_repository.py#test_resolve_grade_accepts_a_confirmed_sharp_disagreement"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every D-14 sanity reject (soft/herring live type, played==key, played==runner-up, client tier, resolved outcome, no recheck, no key, inconsistent ES pair) stores the claim unaccepted and grades as without it"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "tests/repositories/test_train_repository.py#test_resolve_grade_rejects_every_failed_sanity_check"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_recheck_confirmed_on_soft_puzzle_grants_nothing"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_recheck_resolved_is_stored_unaccepted"
        status: pass
    human_judgment: false
  - id: D4
    description: "Played sharp runner-up is graded server-side from the blob b/s evals; vetted_moves stays empty; the key keeps the client tier"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_repository.py#test_record_solve_grades_sharp_runner_up_server_side"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_repository.py#test_record_solve_sharp_key_keeps_client_tier"
        status: pass
      - kind: unit
        ref: "tests/services/test_train_pool.py#TestSharpRunnerUpGradedMove"
        status: pass
    human_judgment: false
  - id: D5
    description: "Malformed recheck is dropped to None without costing the solve; unknown top-level keys still validate; first recorded re-check wins on resubmit"
    requirement: "D-18, D-20"
    verification:
      - kind: unit
        ref: "tests/schemas/test_train_recheck_schema.py"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_recheck_resubmit_keeps_first_record"
        status: pass
    human_judgment: false
  - id: D6
    description: "D-04: classify_puzzle_type, SHARP_GAP_ES and the server engine budget untouched"
    requirement: "D-04"
    verification: []
    human_judgment: true
    rationale: "Negative guarantee; checked by grep (SHARP_GAP_ES: float = MISTAKE_DROP unchanged) and by the unchanged classify tests passing, no test asserts 'not modified'"

duration: 70min
completed: 2026-10-07
status: complete
---

# Phase 235 Plan 03: Server half of key-anchored grading Summary

**Server grades a played sharp runner-up from its own blob (D-02), credits a sanity-checked confirmed phone disagreement for either guess (D-14), and stores every re-check in a new `drill_solves.recheck` JSONB column (D-17/D-18) through one pure `_resolve_grade`.**

## Performance

- **Duration:** ~70 min
- **Completed:** 2026-10-07
- **Tasks:** 2 (1 tracer, 1 auto/tdd)
- **Files modified:** 10 (2 created)

## Accomplishments
- Migration `c5e8a2d7b914` (down_revision `f4b9d2c7e815`) adds `drill_solves.recheck JSONB(none_as_null=True)`; applied to the dev DB, downgrade/upgrade round trip verified, single head.
- `SolveRecheck` (extra forbid, Literal v/outcome, strict bounded ES floats, depths clamped to 255) rides on `SolveRequest.recheck`; a malformed object is dropped to None via a wrap validator, and `SolveRequest` still ignores unknown top-level keys (stale bundles).
- `_disagreement_accepted` (pure) checks outcome confirmed, both ES pairs in the good band, LIVE type sharp, server key present, played != key, played != runner-up, client tier good. `_resolve_grade` orders: server-graded move (vetted entry or sharp runner-up) beats a confirmed claim beats the client tier.
- `SolveClassification` now carries `key_uci`, `runner_up_uci`, `graded_moves` derived through `answer_key_for` (same function as composition). `vetted_moves` stays the display list, so a sharp runner-up is never shown as "also fine".
- `SolveResponse.disagreement` is true when the claim was accepted; on a lost-claim re-submit it is read back from the stored `recheck.accepted` (first recorded outcome wins).
- `_classify_and_certify_solve` split into three source helpers plus a dispatcher (shallower, and the SR read of `best_move` no longer depends on a non-empty blob).

## Task Commits

1. **Task 1 (tracer): confirmed re-check stored and credits either guess** - `2c5976058` (feat)
2. **Task 2: runner-up, D-14 rejects, schema drops, resubmit, mutation tests** - `43624c016` (test)

Tracer gate: the Task 1 `<verify>` set (migration at head, round trip, `-k "recheck or wire_contract"`, ruff/ty/nesting gate) was re-run green before expansion.

## Mutation proofs (each applied, observed red, reverted; `git diff -- app/ alembic/` empty afterwards)

- **a. drop `puzzle_type == "sharp"`:** `test_resolve_grade_rejects_every_failed_sanity_check[live-type-soft]`, `[live-type-herring]`, and both parametrizations of `test_recheck_confirmed_on_soft_puzzle_grants_nothing` went RED. See Deviations 1: the router test only went red after I gave its soft puzzle a stored best move.
- **b. drop `played_move != key_uci`:** `[played-equals-key]` RED.
- **c. drop `client_tier == "good"`:** `[client-tier-inaccuracy]` and `[client-tier-wrong]` RED.
- **d. write a JSON null when no recheck arrived (`text("'null'::jsonb")`):** `test_solve_without_recheck_stays_sql_null_and_grades_as_before` RED (`assert False is True` on `recheck IS NULL`).
- **e. stop appending the sharp runner-up entry:** `test_record_solve_grades_sharp_runner_up_server_side` RED (`'good' == 'wrong'`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in my own test] Soft-puzzle router test did not bite on mutation (a)**
- **Found during:** Task 2 mutation proof (a)
- **Issue:** The seeded soft puzzle had no `game_positions.best_move`, so `key_uci` was None and the `key_uci is not None` check rejected the claim on its own; dropping the sharp-type check left the test green, so it did not actually prove the live-type guard.
- **Fix:** The test now seeds a best move (`d2d4`) so the only thing blocking acceptance is the live soft type. Re-ran mutation (a): both parametrizations RED.
- **Files modified:** tests/routers/test_train.py
- **Commit:** `43624c016`

**2. [Process] Heredoc/compound Bash commands were refused in the worktree**
- Test appends and multi-statement scripts were done through the Edit/Write tools (or a script file written with Write) instead. No effect on scope.

**Total deviations:** 1 auto-fixed (test strengthened) + 1 tooling note. **Impact:** none on scope or contract.

## Issues Encountered
- A mutation-revert Edit once removed a newline and produced a syntax error (`claim_result` glued to the previous line); caught immediately by the next pytest run and fixed before any commit.

## Known Stubs
None.

## Threat Flags
None beyond the plan's register. T-235-07..T-235-11 mitigated as planned: acceptance checks are server-side, `SolveRecheck` is strict/bounded, the column is written only when a recheck arrived, the IDOR scoping of the row lookup and claim UPDATE is unchanged.

## User Setup Required
None. The dev DB already carries the column (`uv run alembic upgrade head` applied); production needs the normal deploy migration step.

## Next Phase Readiness
- Plan 04's client can send `recheck` and read `SolveResponse.disagreement`; plan 05's reveal can read `disagreement` too. The Phase 230 leaderboards pick D-14 up through `correct_guess` with no change.
- Orchestrator read-only check available: `SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name='drill_solves' AND column_name='recheck'` should return jsonb / YES.

## Self-Check: PASSED

- Files present: migration, `tests/schemas/test_train_recheck_schema.py`, and all 8 modified files; greps found `class SolveRecheck`, `def _drop_invalid_recheck`, `disagreement: bool`, `def _resolve_grade`, `def _disagreement_accepted`, `recheck=body.recheck`, `class ServerGradedMove`, `graded_moves: list[ServerGradedMove]`, `SHARP_GAP_ES: float = MISTAKE_DROP`.
- Commits `2c5976058`, `43624c016` are ancestors of HEAD; `git rev-list --count 344eaec30..HEAD` = 2 before this SUMMARY.
- `uv run pytest tests/schemas tests/services/test_train_pool.py tests/repositories/test_train_repository.py tests/routers/test_train.py -n auto` = 495 passed; ruff format/check, ty (app/ tests/ scripts/) and the nesting gate exit 0; MIGRATION-AT-HEAD and round trip verified.

---
*Phase: 235-train-grading-server-answer-key*
*Completed: 2026-10-07*
