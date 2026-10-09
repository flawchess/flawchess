---
phase: 233-train-puzzle-timing-telemetry
plan: 01
subsystem: api
tags: [fastapi, pydantic, postgres, jsonb, alembic, telemetry]

requires:
  - phase: 189-train
    provides: drill_solves pre-materialized rows and record_solve claim UPDATE
provides:
  - drill_solves.telemetry nullable JSONB (none_as_null) column and migration a7c3e9d41f02
  - SolveTelemetry / ReviewTelemetry closed Pydantic boundary models with named caps
  - record_solve telemetry merge inside the claim UPDATE (column omitted when absent)
  - POST /api/train/sessions/{session_id}/solves/{position}/review (204) review-flush route
affects: [233-02, 233-03, frontend telemetry client, leaderboard-effect analysis]

actuals:
  tokens: 8600
  tasks: 2
  commits: 2
plan_head_before: f492f2b0a471f1e093e6bc2c731bdb319f761629
plan_head_after: 6941be22cf82da244d984f5c29cf3f7e3cfe56de

tech-stack:
  added: []
  patterns:
    - "JSONB merge via coalesce(col, '{}') || patch, column omitted from the statement for SQL NULL"
    - "Wrap field_validator drops invalid optional sub-object to None instead of 422"
    - "BeforeValidator clamp factory + strict Field for clamp-not-reject numeric telemetry"

key-files:
  created:
    - alembic/versions/20261005_120000_a7c3e9d41f02_drill_solves_telemetry.py
    - tests/schemas/test_train_telemetry_schema.py
  modified:
    - app/models/drill_solve.py
    - app/schemas/train.py
    - app/repositories/train_repository.py
    - app/routers/train.py
    - tests/routers/test_train.py

key-decisions:
  - "D-04 refinement: hidden time stored as think_hidden_ms (solve patch) and review_hidden_ms (review patch) so the per-key merge cannot overwrite one with the other"
  - "Invalid solve telemetry is dropped silently (no log, no Sentry); the review route returns a normal 422"
  - "exit enum stays next | pagehide; pagehide means left the reveal without pressing Next"
  - "Lost-claim branch of record_solve stays write-free: first recorded telemetry wins"

patterns-established:
  - "Telemetry caps are module-level Final constants in app/schemas/train.py, mirrored by the frontend in plan 02"

requirements-completed: [D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-09, D-14]

coverage:
  - id: D1
    description: "Solve POST with telemetry stores exactly the sent keys as a JSON object; no telemetry stays SQL NULL"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "tests/routers/test_train.py#test_telemetry_solve_without_telemetry_stays_sql_null"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_telemetry_solve_with_telemetry_stores_object"
        status: pass
    human_judgment: false
  - id: D2
    description: "Malformed solve telemetry never costs the solve; durations rounded and clamped to the 30 min cap"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "tests/routers/test_train.py#test_telemetry_invalid_telemetry_still_solves"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_telemetry_solve_clamps_and_rounds"
        status: pass
    human_judgment: false
  - id: D3
    description: "Grading, SolveResponse and the SR ladder are identical with and without telemetry"
    requirement: "D-05"
    verification:
      - kind: integration
        ref: "tests/routers/test_train.py#test_telemetry_does_not_change_grading"
        status: pass
    human_judgment: false
  - id: D4
    description: "Review-flush route merges per key into the caller's own solved row, any session status, 404/422 otherwise"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "tests/routers/test_train.py#test_review_flush_merges_into_solved_row"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_review_flush_rejects_other_users_row"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_review_flush_accepts_completed_and_expired_session"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train.py#test_review_flush_path_bounds"
        status: pass
    human_judgment: false
  - id: D5
    description: "Closed key set: extra=forbid, client Literal, exit required, strict bool/int"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "tests/schemas/test_train_telemetry_schema.py"
        status: pass
    human_judgment: false

duration: 14min
completed: 2026-10-05
status: complete
---

# Phase 233 Plan 01: Server-side per-puzzle telemetry Summary

**Nullable JSONB `drill_solves.telemetry` written by a `coalesce || patch` merge inside the existing solve claim UPDATE, plus a Bearer-authenticated review-flush route, behind closed clamp-not-reject Pydantic models.**

## Performance

- **Duration:** ~14 min
- **Completed:** 2026-10-05
- **Tasks:** 2 (1 tracer, 1 auto/tdd)
- **Files:** 7 (2 created, 5 modified)

## Accomplishments

- Tracer (Task 1): a solve POST's telemetry lands in the column end to end; an old client that sends nothing leaves the column SQL NULL (the column is omitted from the UPDATE, never a JSON null). Migration applied to the dev DB, `a7c3e9d41f02` is the single head.
- `SolveTelemetry` (v, client Literal, guess_ms, move_ms, think_hidden_ms, resumed) rides on `SolveRequest.telemetry` with a wrap validator that drops invalid telemetry to None so the solve is still recorded.
- Task 2: `ReviewTelemetry` (closed key set, required `exit`), `merge_solve_telemetry` (single UPDATE, owner-scoped, `solved_at IS NOT NULL`, no session-status check), and the `.../solves/{position}/review` 204 route with `Path` bounds (`_SESSION_ID_MAX`, new `_DRILL_POSITION_MAX`).
- 24 router tests (`-k "telemetry or review_flush"`) and 24 pure-schema tests pass; the wider train router, schema and train repository suites pass (317 tests).

## Mutation proof (red before revert)

- **a.** `merge_solve_telemetry` writing the bare patch (`literal(patch, JSONB)`) instead of `_merged_telemetry(patch)`: `test_review_flush_merges_into_solved_row` FAILED (stored dict lost the solve keys). Reverted.
- **b.** Deleting the `_drop_invalid_telemetry` wrap validator: `test_telemetry_invalid_telemetry_still_solves` FAILED (422 instead of 200). Reverted; full telemetry/review suites green again afterwards.

## Task Commits

1. **Task 1 (tracer): solve telemetry lands in drill_solves.telemetry** - `03dcf0d2b` (feat)
2. **Task 2: review-flush route** - `6941be22c` (feat)

## Deviations from Plan

None - plan executed exactly as written. (Only in-task cleanups: ty required typing the grading-test cases as `list[tuple[str, dict[str, object] | None]]`; `_clamp_to` also leaves non-finite floats unchanged so strict validation rejects them instead of `round()` raising.)

## Known Stubs

None.

## Threat Flags

None beyond the plan's `<threat_model>`: the one new route is the planned T-233-01/03 surface and is mitigated (owner-scoped UPDATE, constant 404 detail, path bounds).

## Self-Check: PASSED

- Created files present: migration, `tests/schemas/test_train_telemetry_schema.py`.
- Commits `03dcf0d2b`, `6941be22c` exist; `commits:` measured from the plan ledger (2).
- Plan verification: alembic head `a7c3e9d41f02`, router and schema tests green, `ruff format --check`, `ruff check .`, `ty check app/ tests/ scripts/`, `check_function_size.py --fail-over-depth 4` all exit 0, GRADING-UNTOUCHED grep clean.
