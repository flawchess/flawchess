---
phase: 244-train-sr-ladder-calculation-not-recall
reviewed: 2026-11-02T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - alembic/versions/20261102_120000_e2a7c4f9b244_phase_244_sr_ladder_due_date_push.py
  - app/models/drill_item.py
  - app/repositories/train_repository.py
  - app/services/train_scheduler.py
  - frontend/src/components/train/TrainFlawFixedBanner.tsx
  - frontend/src/components/train/TrainStatsCard.tsx
  - frontend/src/components/train/__tests__/TrainStatsCard.test.tsx
  - frontend/src/lib/__tests__/trainBotCopy.test.ts
  - frontend/src/lib/trainBotCopy.ts
  - frontend/src/pages/Home.tsx
  - tests/repositories/test_train_repository.py
  - tests/routers/test_train.py
  - tests/services/test_train_scheduler.py
  - tests/test_migration_244_sr_ladder_due_dates.py
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: issues_found
---

# Phase 244: Code Review Report

**Reviewed:** 2026-11-02
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found (info only)

## Summary

The migration SQL and `apply_result` change were traced against D-01 to D-11. No bugs or security issues found. Only three non-blocking quality items remain.

Migration (`e2a7c4f9b244`):
- `down_revision` `b7e4c2a9f013` is the previous head, and `alembic heads` reports a single head.
- Latest-solve selection is correct. `max(solved_at) FILTER (WHERE correct_move)` and `FILTER (WHERE correct_move = false)` ignore NULL `correct_move`. For a `streak >= 1` item the latest SR solve is the latest correct one, because any fail resets the streak. For a `streak = 0` item with `fail_count > 0` it is the latest fail.
- NULL handling is correct. A missing floor makes both `>` and `<` comparisons NULL, so never-attempted items are untouched. Unsolved rows (`solved_at IS NULL`, open sessions) and non-SR sources are excluded by the CTE `WHERE`.
- UTC handling is correct. `solved_at` is `timestamptz`, so `AT TIME ZONE 'UTC'` yields a UTC wall time and `::date` is the UTC day. `now() AT TIME ZONE 'UTC'` is the matching "today". The residual one-day skew for non-UTC users is documented and acceptable per the CONTEXT discretion note.
- The `floor > today AND due_date < floor` guard gives "never pulled earlier" (D-07) and "overdue keeps its past due_date" (D-09). Only `due_date` is written, so streak, status, fail_count and ever_correct are untouched (D-06).
- It is idempotent: after the update `due_date == floor`, so a re-run matches 0 rows. The test asserts this.
- Only ACTIVE rows are touched. The join is on `(user_id, game_id, ply)`, matching the `_advance_drill_item` keys. The `drill_solves` column types (`timestamptz`, boolean) were confirmed.
- The downgrade is a no-op and documented.

Scheduler (`apply_result`):
- Mastery fires at `streak + 1 >= 2` with `due_date` untouched. A correct first attempt counts.
- The correct path is exactly `today + 10`, the fail path exactly `today + 4`, and neither depends on `weekday_mask`.
- Door A is `not ever_correct and new_fail >= 3`. Door B is `new_fail >= 4`, regardless of `ever_correct`. Park keeps `due_date` and propagates `ever_correct`.
- The `weekday_mask` parameter is gone, and the only caller (`_advance_drill_item`) was updated. No `LADDER_DAYS` references remain in `app/`, `tests/`, `scripts/` or `frontend/` (only stale `.pyc` files).
- `next_scheduled_day` is still used by `session_window` and `tick_days`, and its docstring cross-reference is fixed.
- Streak can now reach 3 for old-ladder streak-2 items. The DB check is only `streak >= 0`, and nothing in the UI renders `n/3`, so this is safe.

Copy:
- `Home.tsx`, `README.md`, `MASTERED_TAIL`, `MASTERED_EXPLAINER`, `PARKED_EXPLAINER`, the `TrainFlawFixedBanner` doc comment and the CHANGELOG entry are all consistent with the new ladder. Tests were updated to match.
- `returnPhrase`'s "Back in N days" understating the wait under a sparse schedule is the accepted D-03 trade-off.

Verification run: `ruff check` is clean on the touched backend files. `tests/services/test_train_scheduler.py` and `tests/test_migration_244_sr_ladder_due_dates.py` give 65 passed.

## Info

### IN-01: Door B rationale comment overstates how rarely the door fires

**File:** `app/services/train_scheduler.py:75-76`
**Issue:** The comment's own math shows a coin-flip item (p = 0.5) retires with about 18% probability at k = 6. That contradicts the closing sentence "At 6 the door would almost never fire under 2-in-a-row mastery". It only holds for strong items, for example 0.36^6 ≈ 0.2% at p = 0.8. The 4-vs-6 rationale is still correct; only the wording is loose.
**Fix:** Reword the last sentence of the comment, for example: "At 6 the door would retire only ~18% of coin-flip items and almost no strong ones, which is too lenient a leech filter under 2-in-a-row mastery."

### IN-02: Migration test covers the SQL constant but not `upgrade()`, and misses the `streak >= 1` with no correct solve case

**File:** `tests/test_migration_244_sr_ladder_due_dates.py:223-300`
**Issue:**
- The tests execute `PUSH_DUE_DATES_SQL` directly. `upgrade()` itself (the `sa.text` wrap, the `result.rowcount` logging) is never run. The file's docstring says it "runs the exact SQL `upgrade()` executes", which is true of the constant but not of the revision function.
- The NULL-floor guard (comment at migration lines 73-74, "never-attempted items are untouched structurally") is only tested for `streak = 0` (case F). There is no case for an ACTIVE `streak >= 1` item with no matching correct SR solve. That case occurs when only a fail exists, or when history was lost. It is the branch where `last_correct_at` is NULL. A future refactor to `COALESCE` would pass the whole suite.
**Fix:** Add one case, an ACTIVE `streak = 1` item whose only SR solve is a fail or which has no solves, asserting its `due_date` is unchanged. Optionally call `migration.upgrade()` through an `op` context in one test, or accept the current coverage given how simple `upgrade()` is.

### IN-03: Constant comment slightly overstates the mastering interval

**File:** `app/services/train_scheduler.py:60-62`
**Issue:** "the mastering solve always comes CORRECT_RETRY_DAYS after the previous correct one" is a lower bound, not an exact interval. `due_date` is only the earliest the item is served. Composition serves any `due_date <= today`, so the real gap is at least 10 days and often longer. Not a behavioral issue.
**Fix:** Say "at least CORRECT_RETRY_DAYS after the previous correct one".

---

_Reviewed: 2026-11-02_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
