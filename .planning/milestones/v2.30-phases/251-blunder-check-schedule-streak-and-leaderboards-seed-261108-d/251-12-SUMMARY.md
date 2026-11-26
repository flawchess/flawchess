---
phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d
plan: 12
subsystem: api
tags: [streak, train, blunder-check, fastapi, sqlalchemy, postgres]

requires:
  - phase: 251-01
    provides: train_settings blunder-check columns, dated blunder-check sessions, complete_session -> bool, get_session_date
provides:
  - "day_is_complete both-modes rule (D-02) feeding tick_days through complete_days_for"
  - "apply_day_completion: the single idempotent eager credit entry point (streak_credited_on key)"
  - "Blunder-check sessions sized from blunder_check_per_session, size 0 composes nothing, finish credits the day once"
  - "Launch-day test matrix (D-18 rehearsal substitute)"
affects: [251-06, 251-13]

plan_head_before: 0e4c3d5b49756f9fd23f27fc16239e1a7914cf4c
plan_head_after: 1b3cdca782959c3d8672e4de3c9c64766dabec36

actuals:
  tokens: 18900
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Pure tick machine untouched; only its input (the set of complete days) changed"
    - "Idempotency by a stored last-credited day plus IS DISTINCT FROM compare-and-set guards"

key-files:
  created:
    - tests/routers/test_train_two_mode_streak.py
    - tests/repositories/test_train_two_mode_streak.py
  modified:
    - app/services/train_scheduler.py
    - app/repositories/train_repository.py
    - app/services/blunder_check_service.py
    - app/services/blunder_check_selection.py
    - scripts/reset_train_state.py
    - tests/services/test_train_scheduler.py
    - tests/repositories/test_train_repository.py
    - tests/routers/test_train.py
    - tests/test_guest_auth.py
    - tests/scripts/test_reset_train_state.py

key-decisions:
  - "A mode at size 0 is not part of the day; at least one mode must be done (day_is_complete)"
  - "streak_credited_on, not a was_complete_before guard, is the idempotency key (covers puzzles -> credit -> raise blunder check -> finish)"
  - "Days before blunder_check_streak_from use blunder-check size 0, so pre-launch days stay as judged (D-18)"
  - "compose_or_resume returns None at size 0 before any write, even with an open session (router maps it to 409)"
  - "Eligibility ORs blunder_check_per_session > 0 into has_material at both stamp sites"

patterns-established:
  - "complete_days_for / day_complete_on share _bc_size_for_day so the lazy walk and the eager path apply one rule"

requirements-completed: []

coverage:
  - id: D1
    description: "Puzzles done with blunder check pending leaves the streak unchanged; with blunder check at 0 it ticks once (HTTP)"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_two_mode_streak.py#test_day_completion_puzzles_only_waits_for_blunder_check"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train_two_mode_streak.py#test_day_completion_blunder_check_off_ticks_on_puzzles"
        status: pass
    human_judgment: false
  - id: D2
    description: "day_is_complete truth table; tick_days and _judge_one_day untouched (SHIELD_CAP gate still passes)"
    verification:
      - kind: unit
        ref: "tests/services/test_train_scheduler.py#test_day_is_complete_truth_table"
        status: pass
    human_judgment: false
  - id: D3
    description: "Blunder-check size 0 answers 409 with no session row; compose passes the settings size; first finish credits the day once"
    verification:
      - kind: integration
        ref: "tests/routers/test_train_two_mode_streak.py#test_bc_size_zero_composes_nothing"
        status: pass
      - kind: integration
        ref: "tests/routers/test_train_two_mode_streak.py#test_bc_compose_uses_settings_size"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_train_two_mode_streak.py#test_day_completion_bc_finish_ticks_when_puzzles_done"
        status: pass
    human_judgment: false
  - id: D4
    description: "Launch-day matrix: double credit, pre-launch days, holder on launch day, off-day credit, no-puzzle-material eligibility"
    verification:
      - kind: integration
        ref: "tests/repositories/test_train_two_mode_streak.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "The reset tool clears streak_credited_on on the default path"
    verification:
      - kind: unit
        ref: "tests/scripts/test_reset_train_state.py#test_reset_clears_streak_snapshot_but_keeps_schedule"
        status: pass
    human_judgment: false

duration: 14min
completed: 2026-11-18
status: complete
---

# Phase 251 Plan 12: Both-modes streak rule Summary

**The session streak now requires every switched-on mode (D-02): a pure `day_is_complete` rule feeds `tick_days` through `complete_days_for`, and one idempotent `apply_day_completion` (keyed on `streak_credited_on`) is called by both a puzzle session's last solve and a blunder-check finish.**

## Performance

- **Duration:** about 14 min
- **Started:** 2026-11-18T20:37Z
- **Completed:** 2026-11-18T20:52Z
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 12 (2 created, 10 modified)
- **Commits:** 5 production/test commits measured from `plan_head_before`

## Accomplishments

- `day_is_complete(puzzles_done, bc_done, puzzles_size, bc_size)` in `train_scheduler.py`; `tick_days` and `_judge_one_day` are untouched and the single SHIELD_CAP clamp gate still passes.
- `train_repository`: `TrainSettingsRow` carries the five Phase 251 columns (defaults at the end, every reader passes all five), `complete_days_for`, `day_complete_on`, `apply_day_completion` (replaces `_apply_completion_tick`, same settle-first order and `_judge_one_day` outcome choice, plus the `streak_credited_on` guard), `settle_streak_snapshot` now reads complete days, and `get_or_create_settings` writes `blunder_check_per_session = 6` (D-03).
- Blunder-check sessions: `compose_windows(count=...)`, `compose_or_resume` returns None at size 0 before any write and composes with the settings size, `finish_session` calls `apply_day_completion` only when `complete_session` moved the row (day read scoped by session id and user id, T-251-32).
- Eligibility: both `_stamp_pool_eligibility` call sites OR in `blunder_check_per_session > 0`.
- `scripts/reset_train_state.py` default path also clears `streak_credited_on`.

## Task Commits

1. **Task 1 (tracer): both-modes rule and eager credit** - `7e71b6ce0` (feat)
2. **Task 2 RED** - `b5a8d8f8b` (test); **GREEN** - `db5f13c7b` (feat)
3. **Task 3 RED** - `52af72e23` (test); **GREEN** - `1b3cdca78` (feat)

## TDD notes

- **Task 2 RED**: three target tests failed on the planned assertions: `200 == 409` (size 0 composed a session), `4 <= 3` (window_count ignored the size; the first draft passed by coincidence on thin supply, so the test also captures the `count` handed to the composer), and `streak_count 3 == 3 + 1` (finish did not credit). Semantic assessment: each failed on the planned behaviour, not on a collection or fixture fault. `gsd_run check tdd-red-evidence` was not run (pytest report format is unsupported; plan is `type: execute`).
- **Task 3 RED**: two target tests failed on the planned assertions (`pool_eligible_since None == 2026-11-10`, `streak_credited_on 2026-07-20 is None`). The four launch-day matrix cases passed immediately because Task 1 already implemented the behaviour they pin; they are regression guards, proven to bite by mutation: removing the `streak_credited_on` guard fails `test_double_credit_raise_bc_after_puzzles_done`, and removing the `blunder_check_streak_from` branch fails `test_settled_before_launch_day_stays_judged`. Mutating `_bc_size_for_day` to ignore blunder check fails the Task 1 tracer.
- No REFACTOR commit.

## Launch-day behaviours pinned (D-18 rehearsal substitute)

All in `tests/repositories/test_train_two_mode_streak.py` unless noted:

- Streak holder, `blunder_check_streak_from` = today, puzzles only: no credit, and once the window closes the lazy walk judges the day missed (shield -1, count kept while shield > 0).
- A day before the launch day stays judged under the old puzzle-only rule and still counts in `current_week_completed`; a puzzle-only day on or after it does not.
- A mode at size 0 is not part of the day (puzzles alone tick at blunder check 0, HTTP test in the router file; blunder check alone completes the day at puzzles 0 via the truth table).
- Puzzles done with blunder check at 0 (credited), blunder check raised to 6 and finished the same day: no second freeze (`streak_credited_on`).
- Off-day: puzzles alone credit nothing at blunder check 6; the blunder-check finish then credits exactly one freeze and leaves count and `settled_through` alone.
- A user with no puzzle material and blunder check on gets `pool_eligible_since` stamped; with it off it stays NULL.
- A repeated blunder-check finish never credits again.

## Accepted assumptions (carried from the planning notes)

- **A8**: blunder-check sessions are dated `local_today` like a fresh puzzle session. Prod measurement (2026-11-18): 23 of 635 rows (3.6%) have a sparse weekday mask; a sparse-mask user who splits the two modes across two days can lose that day. Accepted for launch, to be surfaced to the owner.
- **A6** (deviation from the orchestrator default, reason in RESEARCH Pitfall 3): puzzles are required whenever their size is above 0. `pool_state` is not treated as "nothing to serve", because sharp fillers always compose a warm-up.

## Pre-existing tests restated with an explicit blunder-check size of 0

Assertions unchanged, only setup lines added:

- `tests/repositories/test_train_repository.py`: helpers `_seed_pool_eligible_since` and `_seed_tick_state` take kw-only `blunder_check_per_session` defaulting to the new module constant `_PUZZLES_ONLY_BC_SIZE = 0`, which covers every caller (the `TestCompletionTick` tests, `test_first_settlement_replays_pre_existing_history`, `test_settled_day_survives_mask_change`, `test_settings_update_settles_with_old_mask_first`, `test_settings_update_after_progress_read_does_not_resettle` and the rest); `TestStampPoolEligibility::test_null_watermark_with_no_material_stays_null` and `::test_null_watermark_produces_no_shield_change_across_elapsed_scheduled_days` call the new `_set_blunder_check_size(db_session, user_id, size)`; the section comment now names `apply_day_completion`.
- `tests/routers/test_train.py`: `_seed_pool_eligible_since_router` takes the same parameter (covers `test_put_settings_settles_elapsed_days_with_old_mask_before_get`); new `_set_blunder_check_size_router` is called in `test_guest_zero_game_warmup_end_to_end`, whose docstring now names `apply_day_completion`.
- `tests/test_guest_auth.py::TestGuestPromotion::test_train_state_preserved_after_promotion`: sets the guest's `blunder_check_per_session` to 0 after compose.
- `tests/scripts/test_reset_train_state.py`: seed and assertions extended for `streak_credited_on`.

## Deviations from Plan

**1. [Rule 3 - Blocking] Eligibility change deferred from Task 1 to Task 3 inside the working tree**
- **Found during:** Task 1 verify (the two `TestStampPoolEligibility` tests fail once blunder check counts as material, a change the plan assigns to Task 3).
- **Fix:** I had written the eligibility change early; I took it out of the Task 1 commit and re-applied it in Task 3 after its RED tests, so each commit is self-consistent and Task 3's tests are genuinely RED first.
- **Commits:** `7e71b6ce0`, `1b3cdca78`.

**2. [Rule 2 - Test strength] `test_bc_compose_uses_settings_size` also captures the composer's `count`**
- **Issue:** On thin test supply the composer returned at most 3 windows regardless of size, so `window_count <= 3` alone could not detect a regression that ignored the settings row.
- **Fix:** the test spies `compose_windows` and asserts it received `count == 3`, in addition to the planned `window_count` bound.
- **Commit:** `b5a8d8f8b`.

**Total deviations:** 2 (1 blocking-order, 1 test strengthening). **Impact:** none on scope or behaviour.

## Issues Encountered

None. Full backend suite `uv run pytest -n auto`: 7017 passed, 19 skipped. `ruff format`, `ruff check`, `ty check app/ tests/ scripts/` and `check_function_size.py app/ --fail-over-depth 4` are clean. The frontend was not touched.

## Known Stubs

None.

## Threat Flags

None. No new endpoint or trust boundary. T-251-01 is mitigated by the `streak_credited_on` key with `IS DISTINCT FROM` compare-and-set guards on both UPDATEs (tests: double credit, repeated finish). T-251-32 is mitigated by `get_session_date` scoped by session id and user id; `finish_session` additionally reads the windows scoped to the user first, so a foreign id raises not-found before any credit.

## Behaviour notes for later plans

- `compose_or_resume` now returns None at size 0 even when an open session exists (the user switched blunder check off), so GET `/open` remains the way to see a leftover session; plan 03/04 UI should not offer Start at size 0.
- `has_completed_session_on` is still used by the reminder service (plan 06 replaces it with the day-complete rule).
- `PUT /train/settings` does not yet write `blunder_check_per_session` (upsert RETURNING reads it back); plan 02 owns that write.

## Self-Check: PASSED

- Created files exist: both new test files and this SUMMARY.
- Commits `7e71b6ce0`, `b5a8d8f8b`, `db5f13c7b`, `52af72e23`, `1b3cdca78` are ancestors of HEAD.
- Acceptance greps: one `def day_is_complete`, one `async def apply_day_completion`, no `_apply_completion_tick`, `complete_days_for` x5, `_PUZZLES_ONLY_BC_SIZE` x3, two `blunder_check_per_session > 0` stamp sites, one `apply_day_completion` call in `blunder_check_service.py` (inside `finish_session`), `count=` passed to `compose_windows`, `streak_credited_on` in the reset script, ty clean.

---
*Phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d*
*Completed: 2026-11-18*
