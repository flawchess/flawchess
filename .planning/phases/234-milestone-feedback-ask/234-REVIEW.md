---
phase: 234-milestone-feedback-ask
reviewed: 2026-10-06T00:00:00Z
depth: standard
files_reviewed: 39
files_reviewed_list:
  - alembic/versions/20261005_140000_f4b9d2c7e815_users_prompt_state_feedback_source.py
  - app/models/feedback.py
  - app/models/user_activity.py
  - app/models/user.py
  - app/repositories/feedback_ask_repository.py
  - app/repositories/feedback_repository.py
  - app/routers/users.py
  - app/schemas/feedback_ask.py
  - app/schemas/feedback.py
  - app/schemas/users.py
  - app/services/feedback_ask_service.py
  - app/services/feedback_service.py
  - CHANGELOG.md
  - frontend/src/App.tsx
  - frontend/src/components/bots/PersonaGrid.tsx
  - frontend/src/components/bots/__tests__/PersonaGrid.test.tsx
  - frontend/src/components/feedback/FeedbackAskBubble.tsx
  - frontend/src/components/feedback/FeedbackAskModalHost.tsx
  - frontend/src/components/feedback/FeedbackModal.tsx
  - frontend/src/components/feedback/__tests__/FeedbackAskBubble.test.tsx
  - frontend/src/components/feedback/__tests__/FeedbackModal.test.tsx
  - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
  - frontend/src/components/train/TrainStartScreen.tsx
  - frontend/src/hooks/__tests__/useFeedback.test.tsx
  - frontend/src/hooks/useFeedbackAsk.ts
  - frontend/src/hooks/useFeedback.ts
  - frontend/src/lib/analytics.ts
  - frontend/src/lib/feedbackAsk.ts
  - frontend/src/pages/Bots.tsx
  - frontend/src/pages/Import.tsx
  - frontend/src/pages/__tests__/Import.feedbackAsk.test.tsx
  - frontend/src/pages/Train.tsx
  - frontend/src/types/feedback.ts
  - frontend/src/types/users.ts
  - tests/repositories/test_feedback_ask_repository.py
  - tests/services/test_feedback_ask_service.py
  - tests/test_feedback_ask.py
  - tests/test_feedback_repository.py
  - tests/test_feedback_router.py
findings:
  critical: 0
  warning: 2
  info: 5
  total: 7
status: issues_found
---

# Phase 234: Code Review Report

**Reviewed:** 2026-10-06
**Depth:** standard
**Files Reviewed:** 39
**Status:** issues_found

## Summary

I read the phase diff (`e7a9d965a..HEAD`) for every listed file and hand-traced the three guarded transition statements in `feedback_ask_repository.py`. I traced these cases: view, view dedup, 3rd-view auto-snooze and its grace day, round-2 start, snooze upgrade on the grace day, and done. The SQL operator precedence, the NULL handling, and the claim that the guard re-evaluates after the row lock (READ COMMITTED) all hold. `resolve_feedback_ask` mirrors the SQL guards without drift.

Verification I ran:
- Backend: the five phase test modules pass (75 tests).
- `ruff`, `ty` and `check_function_size` are clean.
- `alembic heads` shows a single head, `f4b9d2c7e815`.
- Frontend: `tsc -b`, `knip` and the 7 phase test files (95 tests) are clean.

No blockers. I found two warnings, both robustness or consistency gaps with low blast radius, and five info items.

**Known side effect, `impersonation` now on the PUT response: evaluated, benign, and a net fix.**
- The previous behaviour returned `impersonation=None` from PUT.
- The frontend writes that response straight into the profile cache, so the `ImpersonationPill` vanished after any profile PUT made during impersonation. The shared builder removes this latent bug.
- The added dependency only runs `session.get(User, act_as)` and exposes the target email to the admin who already holds that session. No new data reaches anyone.
- I found no code that treats `profile.impersonation !== null` as a write-allowed or read-only signal.
- The mandated comment is present at the fix site.

## Warnings

### WR-01: `apply_feedback_ask_action` documents "always succeeds" but a corrupt stored state returns 500 on the write path

**File:** `app/services/feedback_ask_service.py:176-195` (raising site: `app/repositories/feedback_ask_repository.py:131-133`)
**Issue:**
- The docstring says "Always succeeds and is idempotent" and the router docstring says "no 4xx reaches Sentry". The snapshot path and the `get_state` no-op path both fail closed on a `ValidationError`: they capture to Sentry with context and return inactive.
- The main write path does not. `_transition` calls `_run_transition`, which calls `FeedbackAskState.model_validate(row[0])` on the RETURNING value.
- The UPDATE merges (`||`) into the existing object, so a stored state with an unknown key, or one that otherwise fails validation, makes the returned object invalid. The `ValidationError` is uncaught and surfaces as a 500, and the request rolls back.
- The profile path hides the bubble for such a user, so the normal UI never calls the endpoint. A stale open tab, or a tab that loaded the bubble before the state was repaired, still would.
- Each hit is a 500 with default Sentry grouping and no `feedback_ask` context.

**Fix:** Wrap the `_transition` call in the same handling as the `get_state` branch:
```python
try:
    state = await _transition(
        session, action, user_id=user.id, today=today, active_days=active_days
    )
    if state is None:
        state = await feedback_ask_repository.get_state(session, user_id=user.id)
except ValidationError as exc:
    _capture_corrupt_state(user.id, exc)
    return _INACTIVE
```
Note that returning `_INACTIVE` after a failed RETURNING validation leaves the in-flight UPDATE in the session. It is rolled back only if you raise. Either `await session.rollback()` before returning, or accept the 500 and correct the docstrings. Rolling back and failing closed is more consistent with the rest of the module.

### WR-02: snooze and done are not gated on eligibility, so an ineligible user or one who already gave feedback can write ask state

**File:** `app/services/feedback_ask_service.py:176-190`, `app/repositories/feedback_ask_repository.py:79-107`
**Issue:**
- Only `view` is gated by `_base_eligible`. `snooze` and `done` run unconditionally for any non-guest, non-impersonated user.
- Their SQL guards test only the ask's own status, not the active-day threshold or `has_feedback`.
- A user with 2 active days who sends `snooze` (stale tab, buggy client) gets `snoozed_at_days=2, snoozed_by='click'`. The re-ask then becomes due at 12 active days instead of one gap after the real milestone. A user with `done` written early is never asked at all.
- It is only self-inflicted state and cannot affect other users, so I rate it a warning rather than a blocker. It does contradict the stated eligibility rule (SEED-191 #1) and leaves the state machine writable outside its defined entry conditions.

**Fix:** Apply the same eligibility gate to all non-`done` actions, or at least to `snooze`:
```python
if action != "done" and not _base_eligible(active_days=active_days, has_feedback=has_feedback):
    return _INACTIVE
```
`done` can stay unconditional because it only ever shrinks exposure.

## Info

### IN-01: Optimistic snooze/done hide has no rollback on failure

**File:** `frontend/src/hooks/useFeedbackAsk.ts:38-52`
**Issue:**
- `onMutate` patches the cache to inactive, but there is no `onError` rollback. If the POST fails, the bubble is hidden locally while the server still considers the ask active, and it reappears on the next focus refetch.
- For `snooze`, there is an extra wrinkle on a pending round-2 re-ask whose `view` POST also failed. The snooze guard requires the status to be NULL or the 3rd-view grace day. A snoozed-by-click state therefore no-ops, and the ask stays snoozed with `resolve` returning true.
- The case is rare and self-heals, because the next bubble mount fires `view` again. The global `MutationCache.onError` already reports the failure.

**Fix:** Optional. Return the previous `feedback_ask` from `onMutate` as context and restore it in `onError`, or invalidate the profile query in `onSettled` for non-view actions.

### IN-02: Stale plan-reference comment

**File:** `frontend/src/components/feedback/FeedbackAskBubble.tsx:2-4`
**Issue:** The header says "Import now; Train landing and Bots roster in plan 04". Plan 04 has shipped, and all three surfaces are wired (`surface: 'import' | 'train-landing' | 'bots'`). Plan-relative wording rots.
**Fix:** Say "Import, Train landing and Bots roster".

### IN-03: Inconsistent indentation in the second `TrainHeader` call

**File:** `frontend/src/components/train/TrainStartScreen.tsx:445-450`
**Issue:** The `<TrainHeader ... />` props are indented 4 spaces deeper than the sibling call at lines 410-415. ESLint does not catch it because there is no Prettier, but it reads as a mis-edit.
**Fix:** Align it with the first call.

### IN-04: Redundant `profile_row` parameter in `_build_profile_response`

**File:** `app/routers/users.py:80-124`
**Issue:**
- `user_repository.get_profile` and `update_profile` both return a `select(User)` row for the same primary key as `user`. Within one session the identity map yields the same instance, so `profile_row` and `user` are the same object.
- The refactor also silently switched GET from `user.beta_enabled` / `user.leaderboard_hidden` to `profile_row.*`. The values are identical in practice, but the two-object signature suggests they might differ and invites future drift.

**Fix:** Optional. Drop the parameter, or document that it is the freshly re-fetched row.

### IN-05: `Sure!` marks the ask done before any feedback is submitted

**File:** `frontend/src/components/feedback/FeedbackAskBubble.tsx:91-95`
**Issue:**
- `handleSure` calls `mutate('done')` immediately. If the user opens the modal and closes it without submitting, they are never asked again and no feedback row exists.
- This is deliberate and matches SEED-191 #5 ("even if the modal is closed without submitting"), so it is not a defect. I am noting it only so the owner can confirm the yield trade-off, since round 2 could otherwise recover those users.

**Fix:** None required. If the owner wants the recovery, set done on submit success and snooze on a dismissed modal.

---

_Reviewed: 2026-10-06_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
