---
phase: 231-weekly-leaderboard-medals
plan: 06
subsystem: testing
tags: [postgres, pytest, concurrency, trigger, medals, finalization]

requires:
  - phase: 231-weekly-leaderboard-medals
    provides: "Plan 01 marker table, standings table, erase-name trigger, lazy finalizer"
provides:
  - "Database-level proofs of finalization guarantees (concurrency, idempotency, empty weeks, read contracts, erasure trigger)"
  - "Runbook note that account deletion anonymizes weekly standings automatically"
affects: [231-weekly-leaderboard-medals]

actuals:
  tokens: 6500
  tasks: 2
  commits: 2
plan_head_before: ec72ee5ef1279aaf73611b82975013d23682ba3c
plan_head_after: 230f3e58ec9606352ad05d9cf77366e6a0d2a5df

tech-stack:
  added: []
  patterns:
    - "Force a DB race deterministically: wrap the pre-claim read with an asyncio.Barrier so both finalizers pass it before either claims"

key-files:
  created:
    - tests/repositories/test_train_medals_finalization.py
  modified:
    - docs/production-runbook.md

key-decisions:
  - "Concurrency test uses an asyncio.Barrier after fetch_finalized_weeks: without it the first coroutine finished before the second started and the test passed even with the claim removed"

requirements-completed: []

coverage:
  - id: D1
    description: "Two concurrent finalizers on separate sessions leave one marker and one row per (board, user)"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_medals_finalization.py#test_concurrent_finalizers_write_one_marker_and_no_duplicates"
        status: pass
    human_judgment: false
  - id: D2
    description: "Repeat finalization is a no-op, claim_week is once-only, insert_standings is idempotent, empty weeks are remembered"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_medals_finalization.py#test_finalize_due_weeks_writes_rows_then_is_a_no_op"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_medals_finalization.py#test_finalize_due_weeks_marks_an_empty_week"
        status: pass
    human_judgment: false
  - id: D3
    description: "Account deletion nulls user_id and erases display_name via trg_train_weekly_standings_erase_name; trigger existence guarded"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_medals_finalization.py#test_deleted_user_row_has_its_display_name_erased"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_medals_finalization.py#test_erase_name_trigger_exists"
        status: pass
    human_judgment: false
  - id: D4
    description: "fetch_last_week_rows and fetch_finalized_weeks read contracts"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_medals_finalization.py#test_fetch_last_week_rows_returns_medal_rows_and_the_viewer_row"
        status: pass
    human_judgment: false
  - id: D5
    description: "Runbook account-deletion paragraph names the trigger"
    verification: []
    human_judgment: true
    rationale: "Documentation wording; grep confirms presence only"

duration: 25min
completed: 2026-10-04
status: complete
---

# Phase 231 Plan 06: Finalization guarantees Summary

**Nine real-database tests prove the lazy weekly finalizer: forced-interleaving concurrent finalizers leave one marker and no duplicates, repeats and empty weeks are no-ops, and the erase-name trigger anonymizes deleted users; plus a runbook line.**

## Accomplishments
- `tests/repositories/test_train_medals_finalization.py` (9 tests, ids 93700-93719 / weeks 2034-01-02 + k 0-11): claim_week once-only, insert_standings idempotency, fetch_finalized_weeks `since` filter, fetch_last_week_rows (medals + viewer row only, live `leaderboard_hidden`), finalize no-op, empty-week marker, deleted-user erasure pinned to `DELETED_USER_DISPLAY_NAME`, pg_trigger existence, concurrency.
- Mutation proof: removing the `claim_week` skip in `finalize_due_weeks` makes the concurrency test fail (`[1, 1] == [0, 1]`); production file restored byte-identical.
- Runbook: one sentence naming `trg_train_weekly_standings_erase_name`.

## Task Commits
1. **Task 1 (tracer) and Task 2 tests** - `4f7e660ce` (test) — both tasks live in one file and were committed together once the module was final
2. **Task 2 runbook line** - `230f3e58e` (docs)

## Deviations from Plan

**1. [Rule 1 - Bug in test design] Concurrency test did not actually race**
- **Found during:** Task 1 mutation check
- **Issue:** As specified (plain `asyncio.gather` of two finalizers), the first coroutine finished before the second reached its finalized-weeks read, so the test stayed green with the claim removed.
- **Fix:** Monkeypatched `train_medals.fetch_finalized_weeks` to wait on an `asyncio.Barrier(2)` after the read, so both finalizers see the week unfinalized and then race on the marker insert.
- **Files modified:** tests/repositories/test_train_medals_finalization.py
- **Verification:** with the claim skip disabled the test fails; with real code it passes.

Task 1 and Task 2 test commits were merged into one commit (single file, written together). No production code changed.

**Total deviations:** 1 auto-fixed (test strengthening). **Impact:** none on scope.

## Verification
- `uv run pytest tests/repositories/test_train_medals_finalization.py -x`: 9 passed, run 3 times consecutively (clean reruns).
- `uv run pytest tests/routers/test_train_leaderboard.py tests/repositories/test_train_medals_finalization.py -x`: 22 passed (serial).
- `uv run pytest -n auto -k "leaderboard or medal"`: 153 passed, 4 skipped.
- ruff format/check and `uv run ty check app/ tests/ scripts/`: clean.
- `grep -c trg_train_weekly_standings_erase_name docs/production-runbook.md`: 1.

## Known Stubs
None.

## Issues Encountered
None.

## Self-Check: PASSED
- tests/repositories/test_train_medals_finalization.py exists; commits 4f7e660ce and 230f3e58e exist.
