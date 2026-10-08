---
phase: 236-train-phone-grade-instant-verdict
plan: 01
subsystem: api
tags: [train, drill_solves, jsonb, alembic, pydantic, audit-data]
requires:
  - phase: 235-train-recheck
    provides: SolveRecheck boundary model, RecheckExpectedScore/RecheckDepth types, drill_solves.recheck (alembic head c5e8a2d7b914)
provides:
  - drill_solves.phone_grade nullable JSONB column (alembic d3a7f1c9e246)
  - PhoneGrade boundary model + PHONE_GRADE_SCHEMA_VERSION
  - SolveRequest.phone_grade and ReviewRequest(ReviewTelemetry).phone_grade, both drop-to-None on malformed
  - record_solve claim-UPDATE write (first write wins) and merge_solve_telemetry coalesce write-once
affects: [236-02 client solve POST, 236-05 client review flush]
tech-stack:
  added: []
  patterns:
    - "write-once JSONB via coalesce(col, new) inside the same UPDATE (not a WHERE guard, which would 404 a second flush and drop its telemetry)"
key-files:
  created:
    - alembic/versions/20261008_120000_d3a7f1c9e246_drill_solves_phone_grade.py
    - tests/schemas/test_train_phone_grade_schema.py
  modified:
    - app/models/drill_solve.py
    - app/schemas/train.py
    - app/repositories/train_repository.py
    - app/routers/train.py
    - tests/routers/test_train.py
key-decisions:
  - "ReviewRequest is a flat subclass of ReviewTelemetry; ReviewTelemetry itself is untouched and extra=forbid is inherited, so unknown top-level review keys still 422"
  - "phone_grade is never passed to _resolve_grade (D-02); move_quality stays the effective tier"
  - "Review route patch excludes phone_grade; the record goes through a separate argument to its own column (D-12)"
patterns-established:
  - "Audit-only JSONB record: separate column, omitted from the claim values when absent so it stays SQL NULL"
requirements-completed: [D-01, D-02, D-07, D-12, D-13]
duration: ~35min
completed: 2026-10-08
status: complete
commits: 2
plan_head_before: 4c0c4997abf2917d1efca21500f8ad23fc9c354a
plan_head_after: 660d89a09
actuals:
  tokens: 40000
  tasks: 2
  commits: 2
---

# Phase 236 Plan 01: Phone Grade Record, Server Half Summary

**Nullable JSONB `drill_solves.phone_grade` written once by the solve claim UPDATE or the review-route coalesce, validated by a six-key `PhoneGrade` model, and never a grading input.**

(`commits: 2` counts the two task commits; the SUMMARY commit follows them.)

## Accomplishments
- Alembic `d3a7f1c9e246` (down_revision `c5e8a2d7b914`) applied to the dev DB; downgrade -1 / upgrade head round trip verified; single head.
- `PhoneGrade` (extra forbid, `v` Literal[1], tier Literal, strict bounded ES, clamped depths) mirrors `SolveRecheck`; exactly six keys, no device hint (D-07).
- `SolveRequest.phone_grade` and `ReviewRequest.phone_grade` drop malformed records to None via wrap validators, so a bad record never costs a solve or a flush.
- `record_solve(..., phone_grade=None)` sets `claim_values["phone_grade"]` only when a record arrived (SQL NULL otherwise); the `solved_at IS NULL` guard makes the first write win (D-13).
- `merge_solve_telemetry(..., phone_grade=None)` adds `coalesce(phone_grade, new)` to the same UPDATE as the telemetry merge (D-12); the router excludes `phone_grade` from the telemetry patch.
- D-04/D-05/D-06 recorded on the `PhoneGrade` and `DrillSolve.phone_grade` docstrings.

## Task Commits
1. Task 1 (tracer): migration, model, schemas (incl. `ReviewRequest`), claim write, solve router wiring, 4 router tests - `601238836`
2. Task 2: review-route coalesce write-once, router passes `ReviewRequest`, schema test file, 6 router tests - `660d89a09`

## Mutation proofs (each reverted afterwards)
- a. `record_solve` writes a non-NULL value when no record arrived: `test_solve_without_phone_grade_stays_sql_null` FAILED (red).
- b. coalesce replaced by a plain set: `test_review_flush_phone_grade_is_write_once` and `test_review_flush_never_overwrites_solve_time_phone_grade` both FAILED (red).
- c. `exclude={"phone_grade"}` dropped from the router patch: `test_review_flush_writes_phone_grade_column_not_telemetry` FAILED (red).
- d. `ReviewRequest` wrap validator removed: `test_review_flush_malformed_phone_grade_keeps_telemetry` FAILED with `422 != 204` (red).

## Verification
- `uv run pytest tests/schemas tests/routers/test_train.py -n auto`: 282 passed.
- ruff format/check, `ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: all clean.

## Deviations from Plan

None in behavior. One sequencing note: the `ReviewRequest` schema class (plan Task 2 step 1) was written alongside the Task 1 schema edits and so landed in the Task 1 commit; the repository/router/test halves of Task 2 are in its own commit. Mutation a used a non-NULL JSON-string write rather than a literal JSON null (both make `phone_grade IS NULL` false, which is what the test asserts).

## Known Stubs
None.

## Threat Flags
None beyond the plan's threat model (T-236-01..05 mitigated and test-covered).

## Issues Encountered
- The execution harness refused compound `git`/heredoc Bash commands in the worktree; test additions were done with the Edit tool and git commands run separately. No effect on the result.

## Self-Check: PASSED
