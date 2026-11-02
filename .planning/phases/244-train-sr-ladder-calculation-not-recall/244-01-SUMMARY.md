---
phase: 244-train-sr-ladder-calculation-not-recall
plan: 01
subsystem: train
tags: [train, spaced-repetition, scheduler, alembic, data-migration]
requires: []
provides:
  - "CORRECT_RETRY_DAYS=10, FAIL_RETRY_DAYS=4, MASTERY_STREAK_THRESHOLD=2, LEECH_FAIL_THRESHOLD=4 in app/services/train_scheduler.py"
  - "apply_result(state, *, correct_move, today) with schedule-independent due dates"
  - "Alembic revision e2a7c4f9b244 (data-only due-date push)"
affects: [train, frontend copy (plan 244-02)]
tech-stack:
  added: []
  patterns:
    - "Migration test loads the revision by path and runs its public SQL constant (no mirror copy)"
key-files:
  created:
    - alembic/versions/20261102_120000_e2a7c4f9b244_phase_244_sr_ladder_due_date_push.py
    - tests/test_migration_244_sr_ladder_due_dates.py
  modified:
    - app/services/train_scheduler.py
    - app/repositories/train_repository.py
    - app/models/drill_item.py
    - tests/services/test_train_scheduler.py
    - tests/routers/test_train.py
    - tests/repositories/test_train_repository.py
key-decisions:
  - "D-02: weekday_mask removed from apply_result; due dates are exact +10 / +4 day offsets (overrides ROADMAP/SEED-207 snapping)"
  - "D-11: CORRECT_RETRY_DAYS = 10 (not SEED-207's 14)"
  - "D-06: no streak remap; migration writes only drill_items.due_date"
  - "Migration dates in UTC (AT TIME ZONE 'UTC'), never the stored IANA timezone, so a bad train_settings.timezone cannot abort a deploy"
  - "D-09 made literal: UPDATE requires floor > UTC today AND due_date < floor"
metrics:
  duration: "about 35 min"
  tasks: 3
  files: 8
status: complete
actuals:
  tokens: 15000
  tasks: 3
  commits: 3
plan_head_before: a5320f3553ff16e9c9358317ff12b8f6507d5434
plan_head_after: 2761d7a3083da74da82525b01d115b95972b248d
---

# Phase 244 Plan 01: Train SR Ladder Rework Summary

The Train SR ladder now retries a correct solve in exactly 10 days and a wrong solve in exactly 4 days, masters at 2 consecutive correct solves and parks leeches at 4 lifetime lapses. Due dates ignore the weekday schedule. A one-off Alembic data migration (`e2a7c4f9b244`) moves in-flight ACTIVE items onto the new spacing.

## What Was Built

- **Task 1 (tracer, `ef28456c6`)**: `train_scheduler.py` constants (`CORRECT_RETRY_DAYS=10`, `FAIL_RETRY_DAYS=4`, `MASTERY_STREAK_THRESHOLD=2`, `LEECH_FAIL_THRESHOLD=4`, Door A stays 3); the streak-to-offset dict is gone from the module and `__all__`. `apply_result` has no schedule parameter; `_advance_drill_item` calls `apply_result(state, correct_move=correct_move, today=today)`. Module, constant, `apply_result` and `next_scheduled_day` docstrings rewritten (SEED-207 leech-door math restated; no docstring calls a first attempt memory-free). Unit tests: constants pin, mastery at exactly 2, correct first attempt counts, fail then two correct masters, lapses below Door B then 2-in-a-row masters, exact offsets on all 7 weekdays, no weekday/mask parameter. Router tests: `test_solve_masters_item_at_two`, exact due dates in the two existing solve tests (midnight-guarded), and `test_solve_due_date_ignores_sparse_weekday_mask` (stored due dates land off the one scheduled weekday).
- **Task 2 (`c0a6b67c1`)**: `test_new_drill_items_are_due_immediately` (ACTIVE, streak 0, fail_count 0, ever_correct False, due == local today, every item served as an SR row). `drill_item.py` and `upsert_settings` docstrings updated.
- **Task 3 (`2761d7a30`)**: revision `e2a7c4f9b244` (down `b7e4c2a9f013`), public `PUSH_DUE_DATES_SQL`, logs the pushed rowcount, no-op downgrade (one-way, owner accepted per D-05). DB test seeds cases A, B, C, D, E, F, G, H (mastered + parked), I1, I2, K and runs the exact SQL loaded by path; plus a zero-row re-run test.

## Verification

- `tests/services/test_train_scheduler.py`: 63 passed. `tests/routers/test_train.py -k solve`: 36 passed. Broader `-k "train or drill"` run: 853 passed, 4 skipped. `tests/integration/test_alembic_migrations.py`: 2 passed.
- `ty check app/ tests/ scripts/`, `ruff check`, `check_function_size.py --fail-over-depth 4`: clean.
- Alembic round trip on dev (upgrade, downgrade -1, upgrade): ends at `e2a7c4f9b244 (head)`; first upgrade logged "pushed due_date on 4 active drill_items" on the dev DB, second run pushed 0. Dev DB was not reset.
- `grep LADDER_DAYS app/ tests/ scripts/` returns 0 (also none in analysis/ or frontend/src).
- D-08 check (no `train_settings`, no `weekday`, contains `set due_date`) passes.

## Mutation Checks (recorded as required)

- **New items due immediately**: temporarily changed the item-creation site in `train_repository.py` to `due_date=today + timedelta(days=1)`; `test_new_drill_items_are_due_immediately` failed (`date(2026, 1, 16) == date(2026, 1, 15)`). Reverted.
- **Migration, today predicate**: removed `f.floor_date > (now() AT TIME ZONE 'UTC')::date`; `test_push_due_dates_per_case` failed on case C ("D-09: floor already past keeps the overdue due_date"). Restored.
- **Migration, source filter**: replaced `source = 0` with `true`; the test failed on case G ("non-SR (herring) solves must be ignored"). Restored.

## Deviations from Plan

None to the plan's behavior. Notes:

- The migration test was not strictly RED-first (the SQL was written before the test run); correctness is proven instead by the two mutation checks above, each of which makes the test fail.
- My first blanket regex also stripped `weekday_mask=` from a `tick_days(...)` call in the scheduler test; caught by the first test run and restored (tick_days still requires it).
- `app/routers/train.py` PUT /settings docstring ("does NOT re-snap") is still accurate and was left unchanged.

## Known Stubs

None.

## Threat Flags

None. T-244-01 mitigations (status/source/solved_at/floor/due_date guards, SET only due_date) are each proven by the per-case test and mutation checks; T-244-02 mitigated by UTC-only conversion.

## Notes for Plan 244-02 / Deploy

- Frontend/README copy (Home.tsx ladder explainer, `MASTERED_TAIL`, `MASTERED_EXPLAINER`/`PARKED_EXPLAINER`, README.md:36) and the CHANGELOG entry are not part of this plan.
- On the prod deploy, compare the logged "Phase 244: pushed due_date on N active drill_items" count against the ~436 sizing in 244-CONTEXT.

## Self-Check: PASSED

- Files exist: migration, migration test, SUMMARY target dir (verified via test runs and git).
- Commits `ef28456c6`, `c0a6b67c1`, `2761d7a30` are on branch `gsd/phase-244-train-sr-ladder-calculation-not-recall`.
