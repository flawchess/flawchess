---
phase: 251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d
reviewed: 2026-11-19T00:00:00Z
depth: standard
files_reviewed: 54
files_reviewed_list:
  - alembic/versions/20261118_202527_ccc5e4f91f6d_phase_251_two_mode_train.py
  - alembic/versions/20261118_210227_ed1ca360aec4_phase_251_blunder_check_boards.py
  - app/models/blunder_check.py
  - app/models/train_settings.py
  - app/models/train_weekly_standing.py
  - app/repositories/blunder_check_repository.py
  - app/repositories/train_leaderboard_repository.py
  - app/repositories/train_medals_repository.py
  - app/repositories/train_reminder_repository.py
  - app/repositories/train_repository.py
  - app/routers/blunder_check.py
  - app/routers/train.py
  - app/schemas/feature_route.py
  - app/schemas/train.py
  - app/services/blunder_check_selection.py
  - app/services/blunder_check_service.py
  - app/services/train_leaderboard.py
  - app/services/train_medals.py
  - app/services/train_reminder_service.py
  - app/services/train_scheduler.py
  - app/services/train_settings_service.py
  - scripts/reset_train_state.py
  - frontend/src/api/client.ts
  - frontend/src/App.tsx
  - frontend/src/components/admin/LeaderboardMedalsDemo.tsx
  - frontend/src/components/train/blunder-check/BlunderCheckEndScreen.tsx
  - frontend/src/components/train/blunder-check/BlunderCheckLevelStep.tsx
  - frontend/src/components/train/blunder-check/BlunderCheckTab.tsx
  - frontend/src/components/train/medals/MedalClaimDialog.tsx
  - frontend/src/components/train/TrainLeaderboardCard.tsx
  - frontend/src/components/train/TrainModeLauncherRow.tsx
  - frontend/src/components/train/TrainModeSettings.tsx
  - frontend/src/components/train/TrainScheduleSettings.tsx
  - frontend/src/components/train/TrainScoreScreen.tsx
  - frontend/src/components/train/TrainStartScreen.tsx
  - frontend/src/components/train/TrainStreakCard.tsx
  - frontend/src/components/train/TrainSubnav.tsx
  - frontend/src/components/train/trainTodayActions.ts
  - frontend/src/components/train/useTrainReminderSlot.tsx
  - frontend/src/hooks/useBlunderCheckSession.ts
  - frontend/src/hooks/useTrainProgress.ts
  - frontend/src/hooks/useTrainSettingsDraft.ts
  - frontend/src/hooks/useTrainSettings.ts
  - frontend/src/lib/analytics.ts
  - frontend/src/lib/featureRoute.ts
  - frontend/src/lib/leaderboardMedalsDemoData.ts
  - frontend/src/lib/theme.ts
  - frontend/src/lib/trainLeaderboard.ts
  - frontend/src/lib/trainMedals.ts
  - frontend/src/lib/trainRoute.ts
  - frontend/src/lib/trainScoreDemoData.ts
  - frontend/src/pages/Train.tsx
  - frontend/src/types/train.ts
  - frontend/src/types/users.ts
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 251: Code Review Report

**Reviewed:** 2026-11-19
**Depth:** standard
**Files Reviewed:** 54
**Status:** issues_found

## Summary

Reviewed the phase diff (`c56374ff6..HEAD`) of the two migrations, the streak/day-completion path
(`apply_day_completion`, `complete_days_for`, `day_complete_on`, `settle_streak_snapshot`), the settings
service and resize rules, the cross-mode cooldown, the leaderboard/medal board generalisation, and the
Today-page frontend (settings draft, launcher rows, drill host, leaderboard card, medal dialog).

Checked and found sound: the `streak_credited_on` idempotency key (UPDATEs are guarded with
`IS DISTINCT FROM`, a failed compare-and-set leaves the key unset so a retry works, and the lazy walk and
eager path both go through `_judge_one_day`); the `blunder_check_notice_from` CASE in the upsert (SET
expressions read the pre-update row); session-day handling (every day comes from `local_today` with the
settings timezone, never `.date()` on a UTC instant); the board key derivation (`get_args` on the Literal
feeds finalization, tallies and the medal order); the migrations (the one-way CHECK widening, backfills
guarded against unknown timezones, a single alembic head); `check_function_size.py --fail-over-depth 4`
and `ruff check` both pass; no `asyncio.gather` on a session; the new routers capture to Sentry or map
expected errors. The accepted assumption A8 and the documented D-19 scan exemptions were not re-reported.

No blockers. The four warnings are: a cooldown rule that cools flaws the user was never shown, a guest
data-retention gap opened by removing the beta gate, and two frontend edge cases around the auto-saving
settings draft.

Necessity (#4100): no necessity findings were raised for this scope.

## Warnings

### WR-01: Cross-mode cooldown cools flaws that were composed but never shown

**File:** `app/repositories/train_repository.py:1787` (`blunder_check_cooled_pairs`) and
`app/repositories/blunder_check_repository.py:322` (`puzzle_cooled_pairs`)
**Issue:** D-16 says a flaw *served* in either mode is ineligible in the other. Both cooled-pair queries
count every pre-materialised row instead of the rows the user actually saw:
- `puzzle_cooled_pairs` selects `DrillSolve` rows of `source = SR_ITEM` with no `solved_at IS NOT NULL` /
  `entered_at` condition. `POST /train/sessions` runs as a status read on every Today mount and
  pre-inserts `drill_solves` rows (`solved_at = NULL`) for the whole session, so a user who only plays
  blunder check still has up to `puzzles_per_session` own flaws per day marked "served as puzzles". Over
  the 7-day window that is about 42 flaws at the default size, taken out of the blunder-check own-blunder
  pool (`pick_own_game_ids(require_facepalm)` and `served_for_games`) for no pedagogical reason.
- `blunder_check_cooled_pairs` counts every window of a session including `started_at IS NULL` windows.
  `expire_stale_sessions` and the resize path later delete exactly those windows ("a blunder the user was
  never shown goes back to the pool", A9), so until that delete runs the puzzle side hides a flaw the user
  never saw, and the two rules disagree about what "served" means.
**Fix:** Cool only what was shown. Puzzle side: add `DrillSolve.solved_at.isnot(None)` (or join on
`DrillSession.entered_at.isnot(None)`) to `puzzle_cooled_pairs`. Blunder-check side: add
`BlunderCheckWindow.started_at.isnot(None)` to `blunder_check_cooled_pairs`.
```python
.where(
    DrillSession.user_id == user_id,
    DrillSession.session_date >= since,
    DrillSolve.source == DrillSource.SR_ITEM,
    DrillSolve.game_id.isnot(None),
    DrillSolve.solved_at.isnot(None),  # shown/answered only, not merely pre-materialised
)
```

### WR-02: Guest purge leaves blunder-check sessions and windows behind

**File:** `app/services/guest_cleanup_service.py:130` (not in the scoped list; a consequence of
`app/routers/blunder_check.py` dropping the beta gate for guests, D-18)
**Issue:** The 30-day guest purge deletes games, `drill_sessions` and `train_settings`, with a comment
that this keeps the `/welcome` promise "nothing is deleted after 30 days of inactivity" an honest sign-up
delta. Before this phase guests could not reach blunder check (beta-gated). Now guests start sessions, so
`blunder_check_sessions` / `blunder_check_windows` rows (FEN, move lists, outcomes, points) accumulate for
guests and are never purged: the purge keeps the user row (stamps `games_purged_at`), so the `users`
CASCADE never fires. A returning purged guest also keeps a served-set that references now-deleted games,
and its stale completed sessions are still read by `complete_days_for` / `completed_session_in_window`.
**Fix:** In the purge transaction add the same explicit delete next to `DrillSession`; windows go through
the session FK CASCADE (verify the FK is `ondelete="CASCADE"`):
```python
await session.execute(delete(BlunderCheckSession).where(BlunderCheckSession.user_id == guest_id))
```
and add the matching assertion to `tests/test_guest_cleanup_service.py::test_purge_guest_cascades_drill_rows`.

### WR-03: A debounced settings save can complete a blunder-check session irreversibly mid-drag

**File:** `frontend/src/hooks/useTrainSettingsDraft.ts:106` with
`frontend/src/components/train/TrainModeSettings.tsx:167`; backend rule in
`app/repositories/blunder_check_repository.py:1018` (`resize_open_session`)
**Issue:** The session-size slider writes every `onValueChange` position into the draft, and the draft
auto-saves 600 ms after the last edit. D-06 makes a resize to `<= ended windows` complete the session
immediately, credit the streak day (`apply_day_completion`), and never reopen. A slow drag or keyboard
stepping that rests on an intermediate value for more than 600 ms (for example 12 down to 6 resting at 3
with three windows already ended) persists that intermediate size, and the open session is completed and
credited for a value the user was only passing through. Raising the slider afterwards cannot undo it. The
same path is the D-04 loophole, but there the user chose 0; here the trigger is a hesitation.
**Fix:** Save the slider only on commit instead of on every move: keep the drag position in local
component state and call `update(...)` from `onValueCommit` (Radix fires it on pointer release and once
per key step). If a per-keystroke commit is a concern, keep the existing `useDebouncedTrackFeature` for
analytics but gate the draft write on commit.

### WR-04: Tapping Start within the debounce window silently drops the pending settings save

**File:** `frontend/src/pages/Train.tsx:228` (`loop.todayVisited && landingActive`) and
`frontend/src/components/train/TrainStartScreen.tsx:373` (owner of `useTrainSettingsDraft`)
**Issue:** The shared settings draft lives in `TrainStartScreen`, and `TrainStartScreen` is unmounted
whenever `landingActive` is false (puzzle loop, score screen, or the blunder-check host). The header
comment in `TrainStartScreen` promises a pending save "survives a tab switch", which holds only for
hiding. If a user changes the blunder-check size (or level, or a weekday chip) and taps Start in the same
600 ms, the unmount cancels the debounce timer: the displayed "N per session" is never persisted, and the
drill composes with the previous size (`compose_or_resume` reads the stored value). The user sees the new
size in the row and plays the old one, with no error or indicator.
**Fix:** Flush the pending draft before navigating into a session: expose a `flush()` from
`useTrainSettingsDraft` (mutate immediately when `hasEditedRef` is set and the draft differs from the
server) and call it from the `onTurnOn` / Start handlers before `startBlunderCheck` / `startPuzzles`, or
hoist the draft above `landingActive` so it stays mounted (as `TrainScheduleSettings` was meant to).

## Info

### IN-01: Streak explainer popover still describes the puzzle-only rule

**File:** `frontend/src/components/train/TrainStreakCard.tsx:60`
**Issue:** `STREAK_EXPLAINER` says "Complete a session on a scheduled training day and your streak goes up
by 1." After D-02 the day only ticks when every mode with a size above 0 is complete, and the doc comment
above it still reads as the pre-251 arithmetic. The launch notice says the streak now includes blunder
check, but the persistent help text, which new users and guests read, contradicts it.
**Fix:** Reword to "Complete every mode you have switched on (a mode set to Off does not count) on a
scheduled training day and your streak goes up by 1."

### IN-02: Level options and default level are duplicated in three components

**File:** `frontend/src/components/train/TrainModeSettings.tsx:121`,
`frontend/src/components/train/blunder-check/BlunderCheckLevelStep.tsx:21`,
`frontend/src/components/train/blunder-check/BlunderCheckTab.tsx:47`
**Issue:** `LEVEL_OPTIONS` (labels) is declared twice and `DEFAULT_LEVEL = 'intermediate'` is declared in
both `TrainModeSettings` and `BlunderCheckTab`. The preselected level and the three labels must agree
between the one-time step and the settings picker (D-17, D-20); a future change to one copy would silently
desync them. The backend equivalent is already single-sourced in `LEVEL_ELO` / `BLUNDER_CHECK_LEVELS`.
**Fix:** Export one `BLUNDER_CHECK_LEVEL_OPTIONS` and `DEFAULT_BLUNDER_CHECK_LEVEL` from
`frontend/src/types/train.ts` (or a small `lib/blunderCheckLevel.ts`) and import them in all three places.

### IN-03: Stale comment on the medal claim cap

**File:** `app/schemas/train.py:1083`
**Issue:** The comment says `MEDAL_CLAIM_MAX_ITEMS = 100` is "About a year of both boards". With four boards
per week the cap is about 25 weeks of full podiums. Behaviour is consistent (the unclaimed read and the
claim body share the constant, so the POST built from the GET is valid), only the stated rationale is wrong.
**Fix:** Update the comment to "About 25 weeks of all four boards", or raise the constant if a year of
four-board medals is the intent.

---

_Reviewed: 2026-11-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
