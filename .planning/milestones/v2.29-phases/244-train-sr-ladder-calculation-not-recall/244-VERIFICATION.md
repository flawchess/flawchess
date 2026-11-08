---
phase: 244-train-sr-ladder-calculation-not-recall
verified: 2026-11-02T16:00:00Z
status: passed
score: 11/11 must-haves verified
covered_files:
  - .planning/phases/244-train-sr-ladder-calculation-not-recall/244-01-PLAN.md
  - .planning/phases/244-train-sr-ladder-calculation-not-recall/244-01-SUMMARY.md
  - .planning/phases/244-train-sr-ladder-calculation-not-recall/244-02-PLAN.md
  - .planning/phases/244-train-sr-ladder-calculation-not-recall/244-02-SUMMARY.md
  - CHANGELOG.md
  - README.md
  - alembic/versions/20261102_120000_e2a7c4f9b244_phase_244_sr_ladder_due_date_push.py
  - app/models/drill_item.py
  - app/repositories/train_repository.py
  - app/services/train_scheduler.py
  - frontend/src/components/train/TrainFlawFixedBanner.tsx
  - frontend/src/components/train/TrainStatsCard.tsx
  - frontend/src/lib/trainBotCopy.ts
  - frontend/src/pages/Home.tsx
  - tests/repositories/test_train_repository.py
  - tests/routers/test_train.py
  - tests/services/test_train_scheduler.py
  - tests/test_migration_244_sr_ladder_due_dates.py
covered_digest: "v4:sha256:e9a038a1a71dcc6836987a7a2916b6296f80f780d16b5ed005a0140fb33408b7"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 244: Train SR Ladder Rework, Calculation Not Recall: Verification Report

**Phase Goal:** Make Train's spaced-repetition repeats test calculation instead of recall of the previous attempt or the reveal screen (correct solve -> 10 days, wrong solve -> 4 days, mastered at 2 in a row, Door B 6 -> 4, in-flight migration).
**Verified:** 2026-11-02
**Status:** passed
**Re-verification:** No, initial verification

Coverage contract: CONTEXT D-01..D-11 plus each plan's must_haves (no REQUIREMENTS.md for this phase). CONTEXT D-02 (no weekday snapping) deliberately overrides the ROADMAP/SEED-207 snapping line and is treated as decided.

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | D-01/D-11: correct solve below threshold gives ACTIVE, `due_date = today + 10`; the solve reaching streak 2 masters with `due_date` untouched; a correct first attempt counts | VERIFIED | `train_scheduler.py`: `CORRECT_RETRY_DAYS=10`, `MASTERY_STREAK_THRESHOLD=2`; `apply_result` (lines 324-346) returns MASTERED with `state.due_date` at `new_streak >= 2`, else `today + timedelta(days=CORRECT_RETRY_DAYS)`. No first-attempt special case, so fresh + 2 correct = MASTERED. Unit tests (65 passed with the migration tests) cover it. |
| 2  | D-01: wrong solve resets streak, increments lifetime `fail_count`, `due_date = today + 4`; Door A at 3 (never solved), Door B at 4 | VERIFIED | `FAIL_RETRY_DAYS=4`, `PARK_FAIL_THRESHOLD=3`, `LEECH_FAIL_THRESHOLD=4`; wrong branch (lines 350+) evaluates `door_a_never_solved or door_b_leech` before setting the date; `ever_correct` propagated from the incoming state. |
| 3  | D-02: `apply_result` takes no schedule argument, due dates are exact offsets; solve under a sparse weekday mask stores today+10 / today+4 | VERIFIED | Signature is `apply_result(state, *, correct_move, today)`. The single call site `train_repository.py:3126` is `apply_result(state, correct_move=correct_move, today=today)`. Router test `test_solve_due_date_ignores_sparse_weekday_mask` and unit tests `test_due_dates_are_exact_offsets_on_every_weekday` / `test_signature_has_no_weekday_mask_parameter` pass (76 passed in the router/repo run). |
| 4  | D-01: old `LADDER_DAYS` constant gone from `__all__` and every import site; new constants exported | VERIFIED | `grep -rn LADDER_DAYS app tests scripts frontend/src` returns nothing. `__all__` lists `CORRECT_RETRY_DAYS` and `FAIL_RETRY_DAYS`. |
| 5  | D-04: docstrings/comments describe 2-in-a-row, Door B at 4, schedule-independent due dates; no "memory-free first attempt" claim | VERIFIED | Module docstring, constant comments (leech-door math, owner correction on first attempts), `apply_result` and `next_scheduled_day` docstrings, `drill_item.py` docstring, `upsert_settings` note all updated. `dev_clock.py` mention ("ladder spaces repeats out") remains accurate. Review IN-01/IN-03 wording fixes in 80843391c confirmed in source. |
| 6  | Brand-new items are created ACTIVE, streak 0, due today (never today+4) | VERIFIED | `test_new_drill_items_are_due_immediately` exists in `tests/repositories/test_train_repository.py` and passes. |
| 7  | D-05/D-07/D-08: migration e2a7c4f9b244 pushes ACTIVE items to last SR correct + 10 (streak >= 1) or last SR fail + 4 (streak 0) only when the floor is later than the current date; never-attempted, MASTERED, PARKED, non-SR and unsolved rows untouched; no weekday snapping | VERIFIED | `PUSH_DUE_DATES_SQL` read directly: filters `source=0`, `game_id IS NOT NULL`, `solved_at IS NOT NULL`, joins `status=0` items, `CASE WHEN streak>=1 ... ELSE ...`, UPDATE guarded by `status=0`, `floor > today_utc`, `due_date < floor`, SET only `due_date`. No `train_settings` or weekday reference. NULL floor fails comparisons (never-attempted untouched). Per-case test (cases A-L) passes. |
| 8  | D-09: overdue items whose floor is already past keep their exact due date | VERIFIED | `floor_date > (now() AT TIME ZONE 'UTC')::date` predicate; cases C and I1 (floor == today boundary) assert unchanged and pass. |
| 9  | D-06/D-10: only `due_date` written; streak/status/fail_count/ever_correct unchanged; open session and unsolved `drill_solves` row untouched | VERIFIED | SQL SETs `due_date` only; test asserts `after[ply][:4] == before[:4]` for all cases and the open-session/unsolved-row invariants (case K). |
| 10 | D-05: downgrade is a documented no-op; second run updates zero rows; single alembic head | VERIFIED | `downgrade()` is `pass` with explanatory docstring; `test_push_due_dates_rerun_is_noop` passes; `alembic heads` prints exactly `e2a7c4f9b244 (head)` (down_revision `b7e4c2a9f013`); `tests/integration/test_alembic_migrations.py` 2 passed. |
| 11 | Copy (Plan 244-02): Home, README, `MASTERED_TAIL`, stats-card explainers describe the new ladder; D-03 `returnPhrase`/`NEXT_SESSION_TAIL` unchanged; CHANGELOG bullet present; STATE re-check reminder present | VERIFIED | Diff shows Home "a missed position back a few days later and a solved one after ten days ... twice in a row", README updated, `MASTERED_TAIL = 'Two in a row, so this one is retired.'`, `MASTERED_EXPLAINER` "twice in a row", `PARKED_EXPLAINER` "Missed 4 times in total, or 3 times ...". `trainBotCopy.ts` diff is a single line. Grep for "three solves / three times / Missed 6 / until solved three" in `frontend/src`, `README.md`, `app/` finds no stale Train ladder copy. CHANGELOG bullet under `[Unreleased]` and STATE.md line 38 present. Frontend tests for the two files: 99 passed. |

**Score:** 11/11 truths verified (0 present, behavior-unverified; the state-transition truths all have exercising tests that I re-ran).

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `app/services/train_scheduler.py` | VERIFIED | Constants, new signature, `__all__`; wired from `train_repository._advance_drill_item`. |
| `alembic/versions/20261102_120000_e2a7c4f9b244_...push.py` | VERIFIED | `PUSH_DUE_DATES_SQL`, `upgrade()` executes it and logs rowcount, no-op `downgrade()`. |
| `tests/test_migration_244_sr_ladder_due_dates.py` | VERIFIED | Loads the revision module by path and runs the exact SQL (no mirror copy); cases A-L plus re-run no-op. |
| `tests/routers/test_train.py`, `tests/services/test_train_scheduler.py`, `tests/repositories/test_train_repository.py` | VERIFIED | Named tests from the plan exist and pass. |
| Frontend copy files, README, CHANGELOG, STATE.md | VERIFIED | Content confirmed from the diff against `main`. |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `train_repository._advance_drill_item` | `train_scheduler.apply_result` | `apply_result(state, correct_move=correct_move, today=today)` (line 3126) | WIRED |
| migration test | revision module | importlib path load, executes `migration.PUSH_DUE_DATES_SQL` | WIRED |
| stats-card / bot-copy tests | component / `MASTERED_TAIL` | popover text and `returnPhrase` assertions | WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real Data | Status |
|----------|------|--------|-----------|--------|
| `drill_items.due_date` on solve | `new_state.due_date` | `apply_result` written by `update(DrillItem)` in `_advance_drill_item`; router test reads the stored row | Yes | FLOWING |
| Verdict tail "Back in N days" | raw `due_date` | unchanged `returnPhrase` (D-03 accepted trade-off) | Yes | FLOWING |

### Behavioral Spot-Checks (re-run by verifier)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Migration SQL per-case and re-run | `uv run pytest tests/test_migration_244_sr_ladder_due_dates.py tests/services/test_train_scheduler.py` | 65 passed | PASS |
| Solve path, new items due immediately | `uv run pytest tests/routers/test_train.py tests/repositories/test_train_repository.py -n auto -k "solve or due_immediately or padding"` | 76 passed | PASS |
| Alembic chain | `uv run pytest tests/integration/test_alembic_migrations.py`; `uv run alembic heads` | 2 passed; single head `e2a7c4f9b244` | PASS |
| Frontend copy tests | vitest on `trainBotCopy.test.ts` and `TrainStatsCard.test.tsx` | 99 passed | PASS |
| Static gates | `ruff check app tests scripts`; `ty check app/ tests/ scripts/`; `check_function_size.py app/ --fail-over-depth 4` | all clean; 1279 functions, no breaches | PASS |

The orchestrator's full runs (backend 5668 passed, frontend build ok and 5706 passed) were not repeated. The two mutation checks recorded in 244-01-SUMMARY (remove the `floor > today` predicate, remove the source filter) were not re-run, since source files must not be modified; instead I read the SQL and the case table, and each guard has a dedicated case (C and I1 for the today predicate, G for the source filter, L for the streak/fail floor fallback, F for never-attempted, H for MASTERED/PARKED).

### Probe Execution

Step 7c: SKIPPED (the phase declares no probes).

### Requirements Coverage

No REQUIREMENTS.md IDs. CONTEXT D-01 through D-11 all map to the truths above. D-03 is verified by an unchanged `returnPhrase` and `NEXT_SESSION_TAIL`. D-10 is verified by the case K assertions. Nothing is orphaned.

### Anti-Patterns Found

None blocking. No TBD/FIXME/XXX markers introduced in the changed files, no stubs, no leftover `LADDER_DAYS` or `weekday_mask` argument to `apply_result`. The code review (244-REVIEW.md: 3 info findings) is dispositioned as fixed in 80843391c and I confirmed those edits in source.

### Human Verification Required

None. The ladder logic is pure and test-exercised, and the migration SQL is covered by a DB-backed per-case test. The remaining product question (whether 10 days is the right interval) is the planned post-ship SEED-207 re-check (out of scope, recorded in STATE.md).

### Gaps Summary

No gaps. Notes for the release step (informational):
- The migration logs the pushed-row count at deploy. Expect about 436 on prod (it drifts by deploy day), as a sanity check.
- The migration uses UTC dates, so it can be off by one day for non-UTC users. This is documented and allowed by CONTEXT.
- The "Back in N days" tail can understate the real wait under a sparse schedule. This is the accepted D-03 trade-off.

---

_Verified: 2026-11-02_
_Verifier: Claude (gsd-verifier)_
