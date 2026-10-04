---
phase: 230-weekly-train-leaderboards
reviewed: 2026-10-04T00:00:00Z
depth: standard
files_reviewed: 47
files_reviewed_list:
  - alembic/versions/20261003_120000_c4e7a91d2b58_users_leaderboard_hidden.py
  - app/models/drill_solve.py
  - app/models/user.py
  - app/repositories/train_leaderboard_repository.py
  - app/routers/train.py
  - app/routers/users.py
  - app/schemas/train.py
  - app/schemas/users.py
  - app/services/train_leaderboard.py
  - app/services/train_score.py
  - CHANGELOG.md
  - frontend/src/api/client.ts
  - frontend/src/App.test.tsx
  - frontend/src/components/settings/LeaderboardPrivacyCard.tsx
  - frontend/src/components/settings/SettingsPanel.tsx
  - frontend/src/components/settings/__tests__/LeaderboardPrivacyCard.test.tsx
  - frontend/src/components/settings/__tests__/SettingsDialogButton.test.tsx
  - frontend/src/components/settings/__tests__/SettingsPanel.test.tsx
  - frontend/src/components/settings/__tests__/SettingsSheetButton.test.tsx
  - frontend/src/components/train/SignupAskActions.tsx
  - frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx
  - frontend/src/components/train/__tests__/TrainScoreRankLines.test.tsx
  - frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx
  - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
  - frontend/src/components/train/TrainDevClock.tsx
  - frontend/src/components/train/TrainLeaderboardCard.tsx
  - frontend/src/components/train/TrainScoreRankLines.tsx
  - frontend/src/components/train/TrainScoreScreen.tsx
  - frontend/src/components/train/TrainStartScreen.tsx
  - frontend/src/hooks/useTrainLeaderboard.ts
  - frontend/src/hooks/useUserProfile.ts
  - frontend/src/lib/analytics.ts
  - frontend/src/lib/__tests__/analytics.test.ts
  - frontend/src/lib/__tests__/trainLeaderboard.test.ts
  - frontend/src/lib/trainLeaderboard.ts
  - frontend/src/lib/trainScore.ts
  - frontend/src/pages/Privacy.tsx
  - frontend/src/pages/__tests__/Bots.test.tsx
  - frontend/src/pages/__tests__/Train.solveLoop.test.tsx
  - frontend/src/pages/Train.tsx
  - frontend/src/types/train.ts
  - frontend/src/types/users.ts
  - tests/repositories/test_train_leaderboard_repository.py
  - tests/routers/test_train_leaderboard.py
  - tests/services/test_train_leaderboard.py
  - tests/services/test_train_score_parity.py
  - tests/test_users_router.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 230: Code Review Report

**Reviewed:** 2026-10-04
**Depth:** standard
**Files Reviewed:** 47
**Status:** issues_found

## Summary

Reviewed the weekly Train leaderboard stack end to end: the Alembic migration (single head, down_revision chain verified), the aggregate query, the pure ranking/slicing/visibility service, the router and schemas, the profile opt-out flag, and the frontend card, rank lines, privacy card and copy helpers.

The core ranking logic holds up under adversarial reading. Competition ranks, the `_slice_indices` gap handling (checked at viewer indices 3, 7 and 8), the D-13/D-14 visibility filtering (hidden users and guests are filtered before ranking and never reach rows, ranks or pass targets), the IDOR scoping of `fetch_session_contribution` and the absence of user ids on the wire are all correct. Verification run during review: `tests/services/test_train_leaderboard.py` and `test_train_score_parity.py` pass (61 tests), `ruff check`, `ty check` and `check_function_size.py` are clean on the touched backend files, and `tsc -b` is clean on the frontend.

No blockers. Three warnings: a leaderboard-integrity concern inherited from client-asserted move quality, an impersonation-pill regression introduced by the new profile mutation, and a rare stuck state in the week-rollover countdown.

## Warnings

### WR-01: Public rankings are built on a client-asserted `move_quality` (leaderboard can be gamed with direct API calls)

**File:** `app/repositories/train_leaderboard_repository.py:52-59` (consumer), `app/repositories/train_repository.py:2963-2977` (source)
**Issue:** `_MOVE_POINTS_EXPR` sums `drill_solves.move_quality`. In `record_solve`, `effective_quality = move_quality` is taken verbatim from the request body for any `played_move` that is not a server-certified key move (the Phase 211 D-04 "accepted residual"). That residual was harmless while the score was only a private per-session display. Phase 230 makes the same column drive two public, named rankings. A caller who skips the UI can POST `move_quality="good"` with an arbitrary 4-char `played_move` for every position of a session (up to `puzzles_per_session` = 50) and bank 2 of 3 points per puzzle with no engine work, plus 1 more whenever the server-computed guess happens to match (50/50 guess). Accuracy has the same exposure, and the Points board rewards volume on top of that. D-05 accepts impersonation as a risk; it does not accept score forgery, and the CONTEXT file does not mention this interaction.
**Fix:** Either record the exposure as an explicit accepted risk in 230-CONTEXT.md / the SEED (so the owner decides knowingly), or tighten the one input that matters: for a non-key `played_move`, clamp the server-recorded tier so an off-key move can never earn more than the tier the server can justify, for example cap at `"inaccuracy"` unless the server certified the move, or require the played move to be legal in the puzzle FEN and re-grade it from stored evals when available. A cheap mitigation that keeps D-04 intact is a per-session or per-day solve-rate sanity bound applied only to the leaderboard aggregate.

### WR-02: Toggling "Hide me from leaderboards" while impersonating wipes the impersonation pill from the profile cache

**File:** `frontend/src/hooks/useUserProfile.ts:35-38` (consumer), `app/routers/users.py:148` (source)
**Issue:** `useSetLeaderboardHidden.onSuccess` does `queryClient.setQueryData(USER_PROFILE_QUERY_KEY, profile)` with the PUT response. `update_profile` hard-codes `impersonation=None` (users.py:148), unlike `get_profile` which computes it from the JWT. For a superuser impersonating a registered user, the Privacy card is reachable in the Settings overlay (it only hides for `is_guest`), so one toggle replaces the cached profile with `impersonation: null`. `App.tsx:371` and `:409` render the `ImpersonationPill` from `profile?.impersonation`, so the admin silently loses the indicator (and the pill's end-session button) while still acting as the target, until the 5-minute stale time elapses. It also lets an admin change the target user's privacy choice with no visual warning that they are impersonating.
**Fix:** Do not overwrite the cached profile with the PUT response wholesale. Preserve the field the PUT cannot compute:
```ts
onSuccess: (profile) => {
  queryClient.setQueryData<UserProfile>(USER_PROFILE_QUERY_KEY, (old) => ({
    ...profile,
    impersonation: old?.impersonation ?? profile.impersonation,
  }));
  void queryClient.invalidateQueries({ queryKey: TRAIN_LEADERBOARD_QUERY_KEY });
},
```
Alternatively make the PUT handler reuse `_get_impersonation_context`, as the GET does, so both handlers return the same shape.

### WR-03: Week-rollover refetch can fire up to a second early and then never retry, leaving last week's board stuck on "ending now"

**File:** `frontend/src/components/train/TrainLeaderboardCard.tsx:218-245` with `frontend/src/lib/trainLeaderboard.ts:138-145` and `app/services/train_leaderboard.py:309`
**Issue:** The server sends `seconds_remaining = max(0, int((week_end - now).total_seconds()))` (truncated), and the client computes `remaining = server - floor(elapsedSeconds)`. Both truncations round the remainder down, so `remaining` can reach 0 while up to ~1 second of the real week is left. The effect then invalidates the query once and records `rolledOverWeekEnd.current = weekEnd`. If that refetch lands before the true Monday 00:00 UTC, the response again has the old `week_end` and `seconds_remaining` of 0. The guard `rolledOverWeekEnd.current === weekEnd` then blocks every further invalidation, so the card keeps showing last week's standings under "ending now" until a remount or window-focus refetch. The window is narrow (the 60 s tick has to land in the final second), but it is deterministic when it happens and the failure state is visible.
**Fix:** Only mark the week as rolled over once the refetched payload actually carries a new `week_end`, or retry while the refetched `week_end` is unchanged and `remaining` is 0:
```ts
useEffect(() => {
  if (remaining !== 0 || weekEnd === null) return;
  const id = setTimeout(
    () => void queryClient.invalidateQueries({ queryKey: TRAIN_LEADERBOARD_QUERY_KEY }),
    ROLLOVER_RETRY_MS, // e.g. 2_000
  );
  return () => clearTimeout(id);
}, [remaining, weekEnd, dataUpdatedAt, queryClient]);
```
This self-terminates as soon as a response with a later `week_end` makes `remaining` non-zero, so it cannot loop. Round `seconds_remaining` up with `math.ceil` server-side as a second guard.

## Info

### IN-01: Parameter `viewer_visibility` shadows the module-level function of the same name

**File:** `app/services/train_leaderboard.py:136, 247, 300`
**Issue:** `viewer_visibility()` is defined as a function at line 136, and `build_board` and `build_leaderboard` take a parameter with the same name. It works only because those two bodies never call the function (`get_weekly_leaderboard` at line 356 does, and has no such parameter); a future edit that calls it inside `build_board` would hit the string value and raise `TypeError`. Shadowing a function with a same-named variable is a latent trap.
**Fix:** Rename the function to `resolve_viewer_visibility` (update the call at line 356 and the tests), or rename the parameters to `visibility`.

### IN-02: The "Hidden from others" marker is the first thing to be truncated on narrow screens

**File:** `frontend/src/components/train/TrainLeaderboardCard.tsx:88-94`
**Issue:** The name, the "Hidden from others" label and the "(tentative)" label share one `truncate` span, with the name first. With a long username (up to 100 characters are accepted) at 320 to 360 px width, the ellipsis eats the privacy label, which is the only cue telling the viewer that the row is private (D-13). The same applies to "(tentative)" on the Accuracy board.
**Fix:** Give the markers their own non-shrinking element, for example render the name in the `min-w-0 flex-1 truncate` span and put the `Hidden from others` / `(tentative)` text in a sibling `shrink-0` span, or move the marker to a second line under the name for `visibility !== 'public'` rows.

---

_Reviewed: 2026-10-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
