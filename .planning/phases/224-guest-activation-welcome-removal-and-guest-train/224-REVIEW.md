---
phase: 224-guest-activation-welcome-removal-and-guest-train
reviewed: 2026-09-18T00:00:00Z
depth: standard
files_reviewed: 37
files_reviewed_list:
  - app/repositories/train_reminder_repository.py
  - app/routers/train.py
  - app/services/activity_queries.py
  - app/services/activity_stats.py
  - app/services/guest_cleanup_service.py
  - CHANGELOG.md
  - frontend/src/App.test.tsx
  - frontend/src/App.tsx
  - frontend/src/components/import/ImportGuestPromoBubble.tsx
  - frontend/src/components/import/__tests__/ImportGuestPromoBubble.test.tsx
  - frontend/src/components/train/SignupAskActions.tsx
  - frontend/src/components/train/__tests__/SignupAskActions.test.tsx
  - frontend/src/components/train/__tests__/TrainScheduleSettings.test.tsx
  - frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx
  - frontend/src/components/train/__tests__/TrainSolveScreen.restoredGameArrow.test.tsx
  - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
  - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
  - frontend/src/components/train/TrainScheduleSettings.tsx
  - frontend/src/components/train/TrainScoreScreen.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/train/TrainStartScreen.tsx
  - frontend/src/hooks/useUserProfile.ts
  - frontend/src/lib/botGameSnapshot.ts
  - frontend/src/lib/__tests__/trainBotCopy.test.ts
  - frontend/src/lib/trainBotCopy.ts
  - frontend/src/pages/activity/ActivityPage.tsx
  - frontend/src/pages/activity/render.js
  - frontend/src/pages/Home.tsx
  - frontend/src/pages/Import.tsx
  - frontend/src/pages/__tests__/Home.redirect.test.tsx
  - frontend/src/pages/__tests__/Train.solveLoop.test.tsx
  - frontend/src/pages/__tests__/Welcome.test.tsx
  - frontend/src/pages/Train.tsx
  - frontend/src/pages/Welcome.tsx
  - reports/growth/guest-activation-baseline-2026-09-17.md
  - tests/routers/test_train.py
  - tests/test_admin_activity_stats.py
  - tests/test_guest_auth.py
  - tests/test_guest_cleanup_service.py
findings:
  critical: 0
  warning: 1
  info: 1
  total: 2
status: issues_found
---

# Phase 224: Code Review Report

**Reviewed:** 2026-09-18T00:00:00Z
**Depth:** standard
**Files Reviewed:** 37
**Status:** issues_found

## Summary

This phase (1) opens `/train/*` to guest and zero-game accounts by deleting the
`_reject_guest` gate, (2) replaces the old value-comparison `/welcome` page and
its localStorage dismissal mechanism with a four-bullet explainer reachable
only via a "Why?" button, (3) adds a bot-voiced sign-up ask
(`SignupAskActions`) to the Train score screen and the Import page, (4)
threads a `hasGames`/`isGuest` audience pair through the Train copy layer so
zero-game and guest accounts get honest copy instead of "we're analyzing your
games", (5) hides the reminder/QR block from guests on `TrainScheduleSettings`
(the backend fan-out filters guests out, so an enabled toggle would be a
promise the backend can't keep), (6) makes the 30-day guest purge delete
`drill_sessions`/`train_settings` (cascading to `drill_solves`) alongside
games, reversing the Phase 189 "Train rows survive" invariant for guests only,
and (7) adds a `fetch_guest_train` query + activity-dashboard card for the new
guest-Train cohort.

I traced the backend gate removal against the FK cascade chain
(`drill_solves.session_id` is `ON DELETE CASCADE` to `drill_sessions`, and
`drill_items` has no FK to `drill_sessions` at all — it CASCADEs only through
`games`), confirmed the WR-01 re-eligibility re-check inside `_purge_guest`
still gates the new deletes on `User.is_guest.is_(True)` so a registered
user's Phase 189 D-04 preservation is untouched, and cross-checked every new
SQL query (`fetch_guest_train`) for parameterization (bound `:first`, no
string-interpolated user input) and cohort-definition consistency with its
sibling queries (`_GUEST_COHORT`/`_PROMOTED_GUEST`). Test coverage is
unusually thorough for this phase: every behavior change I could construct an
edge case for (promotion-day boundary, purged-guest exclusion, warm-up vs.
cold-start vs. zero-game vs. zero-game-guest copy branching, nav-lock
exemption, `showPhoneSection`/`showReminderBlock` guest gating) already has a
dedicated test that would fail if the logic regressed.

I found no Critical/Blocker issues. One stale-comment Warning (a security-gate
rationale comment still names a function this same phase deleted, which could
mislead a future reader auditing that gate) and one Info-level dead-string
observation.

## Warnings

### WR-01: Stale security-gate comment still references the deleted `_reject_guest` function

**File:** `frontend/src/App.tsx:652-658`
**Issue:** The comment on `ProtectedLayout`'s `useReminderResurfaceRedirect`/`useDevicePushResync` calls still says:

```
// CR-01 FIX (203-REVIEW.md): this runs on EVERY protected route for EVERY
// account. Gate its underlying GET /train/settings off for guests (and
// while `profile` hasn't resolved yet) — guests get a guaranteed 403 from
// `_reject_guest` that the global QueryCache.onError reporter was
// capturing to Sentry on every page view and window refocus, ...
```

`_reject_guest` was deleted from `app/routers/train.py` in this same phase
(`git diff` shows the whole function removed, and `GET /train/settings` now
returns 200 for a guest — proven by `test_guest_settings_round_trip_200`).
The `enabled: profile != null && !profile.is_guest` gate on both hooks is
still functionally correct (a guest still shouldn't get push-reminder
resurface/resync — Phase 224 D-13's "no reminder slot for guests" rule), but
the comment's rationale ("a guaranteed 403") is now false. Every other file
in this phase that referenced `_reject_guest` (`train.py`,
`train_reminder_repository.py`, `guest_cleanup_service.py`,
`TrainScheduleSettings.tsx`) was updated to reflect the removal; this one
comment block was missed. A future engineer investigating why these hooks are
gated off for guests, and finding the cited function no longer exists, is
likely to conclude the gate is now dead code and remove it — silently
reintroducing the reminder-resurface/push-resync 200-but-irrelevant traffic
for guests (not a regression today, since the gate is still correct, but a
plausible future one caused directly by this stale citation).

**Fix:**
```tsx
// Gate its underlying GET /train/settings off for guests (and while
// `profile` hasn't resolved yet): reminders and push-resync are for
// signed-up accounts only (Phase 224 D-13 — the backend fan-out in
// train_reminder_repository.py filters is_guest, so nothing a guest could
// resync would ever be used). `/train/settings` itself no longer 403s
// guests (Phase 224 removed `_reject_guest`), but there's still nothing
// useful for these two hooks to do on a guest account.
```

## Info

### IN-01: `growth-recommendations-2026-09-15.md` "post-2026-09-17-correction" cross-reference predates the note it's quoted in

**File:** `reports/growth/guest-activation-baseline-2026-09-17.md:55`
**Issue:** Line 55 cites `growth-recommendations-2026-09-15.md` as reporting a number "(post-2026-09-17-correction)" — i.e. a correction dated two days after the cited report's own filename date, referenced from a note dated the same day as the correction. This is very likely accurate (the correction was presumably appended to the 09-15 file on 09-17), but as written it reads as an internal contradiction (a file named `-09-15` described as containing a `-09-17` correction) that could confuse a reader trying to locate the correction. Not a code defect — purely a documentation clarity nit in a growth report, included for completeness since the file was in the required-reading set.
**Fix:** Either confirm and note explicitly ("...`growth-recommendations-2026-09-15.md`, amended 2026-09-17...") or drop the parenthetical if it's not load-bearing for the after-reading comparison.

---

_Reviewed: 2026-09-18T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
