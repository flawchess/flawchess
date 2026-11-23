---
phase: quick-261123-lb8
plan: 01
subsystem: blunder-check
tags: [blunder-check, scoring, migration, frontend]
requires: []
provides:
  - blunder-check point scale 1 / 2 / 1 (safe 1, catch 2, better move up to 1, timeout penalty 1)
  - a missed blunder keeps the pot; only a timeout on the blunder forfeits it
  - better-move task after a missed blunder (backend, resume, frontend)
  - Alembic data migration e5c1b7d3a9f2 recomputing points_possible of open sessions' unended blunder windows
affects: [blunder-check drill, blunder-check solution, Train leaderboard Points board]
tech-stack:
  added: []
  patterns:
    - "BETTER_MOVE_OUTCOMES as the single rule for which ended windows offer the better move"
    - "BETTER_MOVE_TIER_POINTS (blunder check) separate from train_score.MOVE_TIER_POINTS (puzzles)"
    - "migration SQL exposed as UPGRADE_STATEMENTS / DOWNGRADE_STATEMENTS and round-tripped in a rolled-back test transaction"
key-files:
  created:
    - alembic/versions/20261201_120000_e5c1b7d3a9f2_quick_261123_lb8_blunder_check_points_rescale.py
    - tests/routers/test_blunder_check_points_migration.py
  modified:
    - app/services/blunder_check_rules.py
    - app/services/blunder_check_candidates.py
    - app/services/blunder_check_grading.py
    - app/services/blunder_check_service.py
    - app/repositories/blunder_check_repository.py
    - app/models/blunder_check.py
    - app/schemas/blunder_check.py
    - app/routers/blunder_check.py
    - CHANGELOG.md
    - frontend/src/lib/blunderCheckDrill.ts
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/types/blunderCheck.ts
    - frontend/src/api/client.ts
    - frontend/src/components/train/blunder-check/BlunderCheckBetterMove.tsx
    - frontend/src/components/train/blunder-check/BlunderCheckDrill.tsx
    - frontend/src/components/train/blunder-check/BlunderCheckScore.tsx
    - frontend/src/components/train/blunder-check/BlunderCheckPointsFlash.tsx
decisions:
  - "Owner scale (overrides plan D-01): SAFE 1, BLUNDER 2, timeout penalty 1, better move good 1 / inaccuracy 1 / wrong 0. Not doubled."
  - "A 'safe' call on the blunder forfeits nothing; a timeout on it still forfeits the whole pot (D-02)."
  - "Conflict reason not_caught renamed no_better_move, since missed windows now offer the task too (D-03)."
  - "Solution reads blunder_points from the caught answer row, not the constant, so windows caught before the change (3 points) report correctly."
  - "The migration only recomputes points_possible of unended blunder windows in open sessions; points are on the right scale already (D-04)."
metrics:
  duration: "about 2h30m"
  completed: 2026-11-23
status: complete
actuals:
  tokens: 110000
  tasks: 3
  commits: 4
plan_head_before: abf153662
plan_head_after: cc0b2cc7c5b2866ffde2e2cf65ed8549805439e5
---

# Phase quick-261123-lb8 Plan 01: Blunder check scoring rebalance Summary

Blunder-check points are rebalanced to 1 / 2 / 1 (a correct Good call 1, catching the blunder 2, the better move at most 1, timeout penalty 1), a missed blunder keeps the sequence's pot, and the better-move step is offered after a miss as well as after a catch, with a small data migration for sessions still open at deploy.

## What changed

- **Backend.** `SAFE_POINTS 1`, `BLUNDER_POINTS 2`, `SAFE_TIMEOUT_PENALTY_POINTS 1`, new `BETTER_MOVE_TIER_POINTS = {good: 1, inaccuracy: 1, wrong: 0}` (commented: an inaccuracy gets full credit to keep points integer at a 1:2:1 ratio) and `BETTER_MOVE_POINTS = 1` in `app/services/blunder_check_rules.py`; `train_score.MOVE_TIER_POINTS` (puzzles 2/1/0) is untouched. `points_possible` follows the constants (herring = length, blunder window = (position - 1) + 2 + 1). `submit_better_move` and the solution's `better_move_points` use `BETTER_MOVE_TIER_POINTS`. `_grade_blunder_move`: a "safe" call on the blunder returns `AnswerGrade("missed", 0, 0, True, "missed", True)`, a timeout forfeits the pot, both offer the better move. `BETTER_MOVE_OUTCOMES` (CAUGHT, MISSED) in `app/models/blunder_check.py` is the single rule read by the service and repository. Resume (`_resume_better_move`, `_resume_after_settle`) reports the real outcome and attaches the task after a stale timeout on the blunder. `_blunder_solution` reads the catch points from the caught answer row. Conflict reason `not_caught` is now `no_better_move`.
- **Migration** `e5c1b7d3a9f2` (down_revision `a7c3e5f9b261`): for windows with `outcome IS NULL` in sessions with `status = 'open'` that have a blunder position, set `points_possible = (blunder_position - 1) + 3`; no answer row or points_scored is touched. Downgrade restores `(blunder_position - 1) + 5`. SQL lives in `UPGRADE_STATEMENTS` / `DOWNGRADE_STATEMENTS`, round-tripped in a rolled-back transaction by `tests/routers/test_blunder_check_points_migration.py` (also proves an ended window of an open session and an unended blunder window of a completed session are untouched).
- **Frontend.** `windowFromServer` uses `response.outcome ?? 'caught'`; `BlunderCheckBetterMove` shows "That was a blunder. Now find a better move." / "Time's up, and that was a blunder. Now find a better move." for a miss (no catch pill) and keeps the caught copy; `flashFor` returns a neutral +0 for a miss that forfeits nothing; `BLUNDER_CHECK_RULES` and the intro steps use module-private constants (1 / 2 / 1) pinned to the backend by `test_frontend_rules_copy_matches_the_point_constants`. The solution is requested only after the better move is graded (existing `answerFeedbackDone` / `betterMoveFeedbackDone` routing, covered by new reducer and tab tests).
- **CHANGELOG** `[Unreleased] ### Changed` has the `Blunder check scoring:` bullet.

## Mutation proof (D-02)

In `app/services/blunder_check_grading.py` the "safe" branch of `_grade_blunder_move` was temporarily changed back to forfeit `window_points`. Result (run on the final 1 / 2 / 1 code): `tests/routers/test_blunder_check_drill.py::test_missed_blunder_keeps_the_pot_and_offers_the_better_move` and `tests/services/test_blunder_check_grading.py::test_grade_missed_keeps_the_pot_and_offers_the_better_move` FAILED (2 failed). The D-02 code was restored from a backup copy; `git status` showed the file clean.

## Deviations from Plan

### Owner decision overriding D-01 and D-04 (mid-execution, from the coordinator)

The plan's doubled scale (2 / 4 / 2, better move 2 / 1 / 0, migration doubling points) was first implemented and committed (5dd74b390, 94c114b38, 8a647f305), then superseded by the owner's scale in follow-up commit cc0b2cc7c: points are NOT doubled; SAFE 1, SAFE_TIMEOUT_PENALTY 1, BLUNDER 2, better move 1 / 1 / 0 via a new `BETTER_MOVE_TIER_POINTS`; `points_possible` = length (herring) or (position - 1) + 2 + 1; the migration only recomputes `points_possible`. The three earlier commits therefore describe a doubled scale in their messages, but the tree at HEAD is on the owner scale (all constants, copy, tests, migration and CHANGELOG updated). D-02, D-03, D-05, D-06, D-07 are unchanged.

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing frontend test asserted the old rules copy**
- **Found during:** Task 3
- **Issue:** `frontend/src/components/train/__tests__/TrainModeSettings.test.tsx` asserted the exact text "A false alarm ends the sequence, but you keep the pot.".
- **Fix:** updated to the new wording and added a check for the timeout sentence.
- **Commit:** 8a647f305

**2. [Rule 1 - Bug] Older CHANGELOG Added bullet described the old rules**
- **Found during:** Task 2
- **Issue:** the `[Unreleased] ### Added` blunder-check bullet said "a points pot you lose on a missed blunder, a better-move follow-up when you catch one".
- **Fix:** reworded to "when the timer runs out on a blunder ... after a caught or missed blunder".
- **Commit:** 94c114b38

**3. [Test design] A miss's better move does not block later windows**
- `GET /open` keeps `current_position` on a window waiting for its better move (asserted), but `start` of a later window is not blocked by it (existing behaviour, unchanged). `test_stale_ended_window_lets_the_session_move_on` asserts current_position 0, plays the better move, asserts 1, then starts the next window.

`app/services/train_leaderboard.py` and `app/services/blunder_check_feedback.py` were not touched. Alembic files outside the new migration were not modified (an accidental `ruff format alembic/` was reverted with `git checkout -- alembic/versions` before committing).

## Accepted transient (migration)

A missed window that ended before the deploy inside a still-open session is offered its better move after the deploy; its old `points_possible` already counted the better move, so it stays consistent. Documented in the migration docstring. Windows ended before the deploy keep their old-scale points and possible values.

## Known Stubs

None.

## Threat Flags

None. The better-move claim guard (T-lb8-01), reply_uci hiding after a miss (T-lb8-02) and server-only grading (T-lb8-03) are covered by tests; the migration (T-lb8-04) by the round-trip test.

## Self-Check: PASSED

- Created files present: migration, migration test, this summary.
- Commits present: 5dd74b390, 94c114b38, 8a647f305, cc0b2cc7c (ancestors of HEAD).
