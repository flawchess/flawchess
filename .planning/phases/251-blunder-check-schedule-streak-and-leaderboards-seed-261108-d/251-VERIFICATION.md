---
phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d
verified: 2026-11-19T06:00:00Z
status: passed
score: 25/25 must-haves verified
covered_files:
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-01-PLAN.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-01-SUMMARY.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-02-PLAN.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-02-SUMMARY.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-03-PLAN.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-03-SUMMARY.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-04-PLAN.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-04-SUMMARY.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-05-PLAN.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-05-SUMMARY.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-06-PLAN.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-06-SUMMARY.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-07-PLAN.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-07-SUMMARY.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-08-PLAN.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-08-SUMMARY.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-09-PLAN.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-09-SUMMARY.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-10-PLAN.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-10-SUMMARY.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-11-PLAN.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-11-SUMMARY.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-12-PLAN.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-12-SUMMARY.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-13-PLAN.md"
  - ".planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-13-SUMMARY.md"
  - "alembic/versions/20261118_202527_ccc5e4f91f6d_phase_251_two_mode_train.py"
  - "alembic/versions/20261118_210227_ed1ca360aec4_phase_251_blunder_check_boards.py"
  - "app/models/blunder_check.py"
  - "app/models/train_settings.py"
  - "app/models/train_weekly_standing.py"
  - "app/repositories/blunder_check_repository.py"
  - "app/repositories/train_leaderboard_repository.py"
  - "app/repositories/train_medals_repository.py"
  - "app/repositories/train_reminder_repository.py"
  - "app/repositories/train_repository.py"
  - "app/routers/blunder_check.py"
  - "app/routers/train.py"
  - "app/schemas/feature_route.py"
  - "app/schemas/train.py"
  - "app/services/blunder_check_selection.py"
  - "app/services/blunder_check_service.py"
  - "app/services/guest_cleanup_service.py"
  - "app/services/train_leaderboard.py"
  - "app/services/train_medals.py"
  - "app/services/train_reminder_service.py"
  - "app/services/train_scheduler.py"
  - "app/services/train_settings_service.py"
  - "frontend/src/App.tsx"
  - "frontend/src/api/client.ts"
  - "frontend/src/components/admin/LeaderboardMedalsDemo.tsx"
  - "frontend/src/components/train/TrainLeaderboardCard.tsx"
  - "frontend/src/components/train/TrainModeLauncherRow.tsx"
  - "frontend/src/components/train/TrainModeSettings.tsx"
  - "frontend/src/components/train/TrainScheduleSettings.tsx"
  - "frontend/src/components/train/TrainScoreScreen.tsx"
  - "frontend/src/components/train/TrainStartScreen.tsx"
  - "frontend/src/components/train/TrainStreakCard.tsx"
  - "frontend/src/components/train/TrainSubnav.tsx"
  - "frontend/src/components/train/blunder-check/BlunderCheckEndScreen.tsx"
  - "frontend/src/components/train/blunder-check/BlunderCheckLevelStep.tsx"
  - "frontend/src/components/train/blunder-check/BlunderCheckTab.tsx"
  - "frontend/src/components/train/medals/MedalClaimDialog.tsx"
  - "frontend/src/components/train/trainTodayActions.ts"
  - "frontend/src/components/train/useTrainReminderSlot.tsx"
  - "frontend/src/hooks/useBlunderCheckSession.ts"
  - "frontend/src/hooks/useTrainProgress.ts"
  - "frontend/src/hooks/useTrainSettings.ts"
  - "frontend/src/hooks/useTrainSettingsDraft.ts"
  - "frontend/src/lib/analytics.ts"
  - "frontend/src/lib/featureRoute.ts"
  - "frontend/src/lib/leaderboardMedalsDemoData.ts"
  - "frontend/src/lib/theme.ts"
  - "frontend/src/lib/trainLeaderboard.ts"
  - "frontend/src/lib/trainMedals.ts"
  - "frontend/src/lib/trainRoute.ts"
  - "frontend/src/lib/trainScoreDemoData.ts"
  - "frontend/src/pages/Train.tsx"
  - "frontend/src/types/train.ts"
  - "frontend/src/types/users.ts"
  - "scripts/reset_train_state.py"
covered_digest: "v4:sha256:b90f3db744b58cb7e1c3f90aa4b0ce9f1b54ff9152497c9c6c801034ee6bf16b"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 25/25
  gaps_closed:
    - "WR-01 cross-mode cooldown counted flaws that were composed but never shown"
    - "WR-02 guest purge left blunder-check sessions behind"
    - "WR-03 slider auto-save could complete a blunder-check session mid-drag"
    - "IN-01 streak explainer described the puzzle-only rule"
    - "W-05 flaky test_bc_compose_uses_settings_size (thin random supply)"
    - "All five previous human_verification items (251-UAT.md, 5/5 pass)"
  gaps_remaining: []
  regressions: []
---

# Phase 251: Blunder-Check Schedule, Streak and Leaderboards Verification Report

**Phase Goal:** Turn the Phase 249 MVP into a full Train mode for everyone, guests included: a shared schedule and reminders with a per-mode session size, a session streak that needs both modes, a Today page with three cards (streak, personalized puzzles, blunder check) replacing the Blunder Check tab, a cross-mode cooldown with personalized puzzles, and Points and Score % leaderboards with medals per mode.
**Verified:** 2026-11-19
**Status:** passed
**Re-verification:** Yes, after the code review fixes (WR-01, WR-02, WR-03, IN-01, W-05) and the browser launch walk (251-UAT.md)

Note on the goal text: the ROADMAP goal mentions "three cards"; the locked decisions D-08 and D-09 (sketch 014 variant B: one Today card with two launcher rows next to the streak card) govern, and the code follows them. The browser walk confirmed the rendered layout.

## Method

No REQUIREMENTS.md exists, so the must-haves are the decisions D-01..D-25 in 251-CONTEXT.md (plus its "Post-execution owner decisions") merged with every plan's `must_haves.truths`. The previous report verified all 25 truths in code with a mutation check on the both-modes rule. In this pass the eight commits after `38c073375` were each read as a diff, the changed code paths were re-read, the touched test modules were re-run, and the previously human-only items were checked against 251-UAT.md. The diff since the last report touches 10 files outside `.planning/`: three backend repository/service files, `TrainModeSettings.tsx`, `TrainStreakCard.tsx`, and the four test files that go with them. No other covered file changed, so the 25-truth table below is carried forward and re-checked only where those files can affect it (D-02 explainer text, D-06 resize, D-16 cooldown, D-18 guests, D-24..D-25 untouched).

## Fix Confirmation

| Fix | Commit | Code evidence | Test evidence | Status |
|---|---|---|---|---|
| WR-01 cooldown counts only shown flaws | 9b454124b | `puzzle_cooled_pairs` adds `DrillSolve.solved_at.isnot(None)` (`blunder_check_repository.py`); `blunder_check_cooled_pairs` adds `BlunderCheckWindow.started_at.isnot(None)` (`train_repository.py`). Docstrings record the owner decision (CONTEXT "D-16 served means actually shown") | `tests/repositories/test_cross_mode_cooldown.py`: new `test_cooldown_unstarted_bc_window_does_not_cool_puzzle` (unstarted window leaves the flaw eligible, started one is cooled, waiting count agrees with composition) and a third parametrization `composed_never_attempted_inside_cooldown` (unattempted drill row does not hide the own blunder in blunder check). Both directions covered | VERIFIED |
| WR-02 guest purge deletes BC sessions | c6b438318 | `_purge_guest` in `guest_cleanup_service.py` runs `delete(BlunderCheckSession)` for the guest id; windows and child rows go via the ON DELETE CASCADE chain | `tests/test_guest_cleanup_service.py::test_purge_guest_deletes_blunder_check_sessions_and_windows` seeds a session plus window and asserts both counts reach 0 | VERIFIED |
| WR-03 slider saves on release | f188a23e2 | `SizeSlider` in `TrainModeSettings.tsx`: `onValueChange` only sets local `dragValue`; `onValueCommit` clears it, calls `onSizeChange(committed)` and `trackCommit`. The shared draft, and so the 600 ms debounced `PUT /train/settings`, never sees an intermediate position (D-06 post-execution decision) | `TrainModeSettings.test.tsx` gained 104 lines across the two commits; 67 tests across the settings and streak-card files pass | VERIFIED |
| WR-03 follow-up (keyboard commit regression found in the walk) | 98a51be76 | Adjust-state-on-prop-change (`prevSize`/`setPrevSize`) drops the local drag position whenever the saved size changes, so Turn on after a keyboard commit to Off shows the real size | Added test in `TrainModeSettings.test.tsx`; re-checked in the browser (UAT test 2: Off then Turn on shows 6) | VERIFIED |
| IN-01 streak explainer | 921e1c0ca | `STREAK_EXPLAINER` now opens with "A day counts when every mode you have switched on is done"; freeze copy says "every day you finish" | `TrainStreakCard.test.tsx` updated; browser walk confirmed the popover states the two-mode rule | VERIFIED |
| W-05 flaky settings-size test | 6f3a671fc | Test-only: `draw_slot_plan`, `draw_blunder_shape`, `draw_herring_shape` monkeypatched so supply is deterministic; assertion tightened from `0 < window_count <= size` to `== size` | `test_bc_compose_uses_settings_size` passes (25 passed across the three touched backend test modules, re-run in this pass) | VERIFIED |

Residual note on WR-03: a size change on release can still complete an open session when the committed size is at or below the ended-window count. That is the intended D-06 rule (completion is irreversible by design) and is now the user's deliberate release action, not a drag artifact.

## Goal Achievement

### Observable Truths

| # | Truth (decision) | Status | Evidence |
|---|---|---|---|
| 1 | D-01 serve-once: shown windows never re-served; resize and expiry delete only never-started windows | VERIFIED | `expire_stale_sessions`, `resize_open_session` (`_delete_unstarted_windows`), `compose_windows`. UAT test 2 confirmed in the browser: Off expired the open session keeping its one shown window |
| 2 | D-02 streak ticks only when every mode with size > 0 is complete | VERIFIED | `day_is_complete` (`train_scheduler.py`) used by `complete_days_for` and `day_complete_on`. Earlier mutation (forcing `bc_ok = True`) failed 7 tests. UAT test 1: streak ticked once, only after the second mode |
| 3 | D-03 default blunder-check size 6 for all users | VERIFIED | Migration `ccc5e4f91f6d` `SMALLINT NOT NULL server_default 6`; UAT showed both rows pending with 6 |
| 4 | D-04 per-mode size changeable anytime, 0 allowed | VERIFIED | `apply_settings_update`; puzzles CHECK 0..50, BC 0..30. UAT test 2: slider to Off (one PUT) and Turn on |
| 5 | D-05 never both modes 0 | VERIFIED | DB CHECK `ck_train_settings_some_mode_on`, router 422, frontend `bothModesOff` guard (unchanged) |
| 6 | D-06 resize rules; slider saves on release | VERIFIED | `resize_open_session` branches covered by 7 resize tests; release-only save now in code (WR-03 fix above) with tests |
| 7 | D-07 schema: CHECK relaxed, own BC column, nullable level column | VERIFIED | Migration and models unchanged since last report; single head `ed1ca360aec4` |
| 8 | D-08 Today page layout (sketch 014 B) | VERIFIED | Components exist and are wired; UAT tests 1 and 4 checked phone (390 px, board fits at 388 px, no overflow) and desktop (card left, settings right) in a real browser |
| 9 | D-09 four row states | VERIFIED | `modes.*.state` + `TrainModeLauncherRow`; UAT saw pending, done ("Done today, 11 points"), and Off with Turn on |
| 10 | D-10 "How it works" collapses after first completed session | VERIFIED | `first_session_done`; UAT test 3 saw it collapsed after the first session |
| 11 | D-11 subnav Today / Leaderboard / Archive; old BC path lands on Today | VERIFIED | `TrainSubnav.tsx`, `trainRoute.ts` unchanged |
| 12 | D-12 score-screen hand-off | VERIFIED | `useContinueAction`; UAT test 1: score screen offered "Continue with Puzzles" above Done |
| 13 | D-13 nav badge = sum of both pending counts | VERIFIED | `pending_count`; UAT test 1: 12 = 6 + 6, then 6, then gone |
| 14 | D-14 separate boards per mode, four board keys | VERIFIED | `LeaderboardBoardKind`, CHECK widened by `ed1ca360aec4`, finalization over all keys (unchanged) |
| 15 | D-15 one medal dialog per week | VERIFIED | UAT test 4: one dialog, "Week of Sep 28" above "Week of Sep 21", mode-labelled board names |
| 16 | D-16 cross-mode cooldown, both directions, 7 days, served = shown | VERIFIED | The WR-01 over-reach noted last time is closed in both repository filters with tests both ways |
| 17 | D-17 guests foreign-only; level handling | VERIFIED | `LEVEL_ELO`, `user_level_elo(fallback=...)`; UAT test 3 |
| 18 | D-18 beta gate removed for registered users and guests | VERIFIED | `routers/blunder_check.py` uses `current_active_user`; guests now also purged (WR-02) |
| 19 | D-19 pitch under Blunder Check row until first session | VERIFIED | UAT test 1 saw the pitch line before the first session |
| 20 | D-20 one-time level step; Phase 249 start screen retired | VERIFIED | UAT test 3: "Pick your level", Intermediate preselected, labels only, shown once, level saved before compose |
| 21 | D-21 launch notice, 14-day cap, dismissal; discovery step | VERIFIED | UAT test 2: notice above the rows, Dismiss posts once (204), stays gone after reload |
| 22 | D-22 Score % board needs 18 windows | VERIFIED | `BLUNDER_CHECK_SCORE_QUALIFY_MIN_WINDOWS = 18` mirrored in `trainLeaderboard.ts`; UAT saw "Not yet qualified (18+ sequences)" |
| 23 | D-23 medal tally per mode | VERIFIED | `fetch_medal_tallies` / `fold_medal_tallies` unchanged; `test_bc_medal_tally_isolated` |
| 24 | D-24 card opens on last viewed mode; score screen links to BC boards | VERIFIED | UAT test 3: "See the leaderboard" opened Blunder check / Points |
| 25 | D-25 guests see public standings plus private would-be row and sign-up ask | VERIFIED | UAT test 3: private "You (guest)" row with the sign-up ask |

**Score:** 25/25 truths verified, 0 present-but-behavior-unverified. The behavior-dependent truths (D-01, D-02, D-06, D-16) each have a passing behavioral test, not presence evidence alone.

### Required Artifacts and Key Links

All artifacts and key links from the previous report still hold; the only modified files are `blunder_check_repository.py`, `train_repository.py`, `guest_cleanup_service.py`, `TrainModeSettings.tsx` and `TrainStreakCard.tsx`, all re-read and still substantive and wired (`_purge_guest` is called by the guest cleanup loop; `SizeSlider` is rendered by `TrainModeSettings`, which `TrainStartScreen` mounts with the shared draft). Wiring of the cooled-pairs functions into `_select_candidates` / `compose_windows` was not altered.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Cross-mode cooldown both directions, guest purge, two-mode streak router tests | `uv run pytest tests/repositories/test_cross_mode_cooldown.py tests/test_guest_cleanup_service.py tests/routers/test_train_two_mode_streak.py` | 25 passed | PASS |
| Slider and streak card components | `npx vitest run` on `TrainModeSettings.test.tsx`, `TrainStreakCard.test.tsx` | 2 files, 67 tests passed | PASS |
| Lint of touched backend files | `ruff check` | all checks passed | PASS |
| Debt markers in lines added since the last report | grep TBD/FIXME/XXX/TODO on the diff | none | PASS |
| Orchestrator full runs (not repeated here) | backend `-n auto` after the fixes: 7097 passed; frontend 373 files / 6608 tests, lint, build, knip clean after 98a51be76 | reported by orchestrator | accepted |

The orchestrator's serial `uv run pytest` was still running when this report was written and was deliberately not duplicated; its result should be read before the squash-merge (a `-n auto` pass does not prove serial CI, per project history).

### Probe Execution

No probes declared. SKIPPED.

### Requirements Coverage

No REQUIREMENTS.md and no requirement IDs. D-01..D-25 are covered in the table above. No orphans.

### Anti-Patterns Found

None blocking. No debt markers in lines changed since the last report; ruff is clean on the touched backend files.

### Human Verification

The five items from the previous report were satisfied by 251-UAT.md (browser launch walk by the orchestrator on the local dev stack with dev clock, 5/5 pass, with per-test evidence: phone-width walk, day rollover with freeze drain, fresh guest path, desktop medal dialog and leaderboard switch, and the WR-03 owner decision). The walk also surfaced and fixed one real regression (98a51be76). The evidence is specific (counts, status codes, testids' visible text, widths) rather than a bare assertion, and the orchestrator's note that the launch-notice check used registered user 28 with the notice stamp moved and restored is accepted. No human verification remains.

### Remaining Warnings (non-blocking, owner-accepted or follow-up)

| ID | Item | Disposition |
|---|---|---|
| WR-04 | Tapping Start within the 600 ms debounce window drops the pending settings save (`TrainStartScreen` unmounts before flush). With release-only slider commits the window is now one release plus 600 ms | Deferred by owner in 251-REVIEW-DISPOSITION.md |
| IN-02 | Level options duplicated in three components | Deferred by owner |
| IN-03 | Stale comment on `MEDAL_CLAIM_MAX_ITEMS` | Deferred by owner |
| W-06 | Puzzles with no puzzle material still require a warm-up session for the day (RESEARCH Pitfall 3, plan 12 A6); accepted planner call, surface to the owner at launch | Documented |
| UAT obs. | Launch notice copy says "Change the amount on the card" but the size is changed in the settings row beside or below the card; dev StrictMode fires the compose POST twice (idempotent) | Copy tweak for the owner, no behavior defect |

251-VALIDATION.md frontmatter reads `nyquist_compliant: true` while its sign-off checkboxes were unticked at the previous check; documentation inconsistency only. 251-SECURITY.md reports `threats_open: 0` and the changed lines (two query filters, one scoped delete by `user_id`, frontend copy and local state) introduce no new surface.

### Gaps Summary

No gaps. The previous report's only reasons for `human_needed` were the browser-only checks and an owner decision, and 251-UAT.md closes all five with evidence. The three actionable review warnings and the info item (WR-01, WR-02, WR-03, IN-01) are fixed in code with tests that exercise the corrected behavior, and no must-have regressed. The one outstanding precondition for merging is outside this verification: read the orchestrator's serial pytest result before the squash-merge.

---

_Verified: 2026-11-19_
_Verifier: Claude (gsd-verifier)_
