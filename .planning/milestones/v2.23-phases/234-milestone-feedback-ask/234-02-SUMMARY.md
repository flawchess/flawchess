---
phase: 234-milestone-feedback-ask
plan: 02
subsystem: frontend
tags: [feedback-ask, hilda, tanstack-query, umami, import-page]
requires:
  - "POST /api/users/me/feedback-ask and profile fields active_days / feedback_ask (plan 01, contract pinned in PLAN)"
provides:
  - "FeedbackAskBubble: shared Hilda ask (surface import | train-landing | bots)"
  - "useFeedbackAsk: scoped view/snooze/done mutation"
  - "feedbackAskCopy / feedbackAskDays shared helpers"
  - "FeedbackModal placeholder + source props; useFeedback invalidates the profile"
affects:
  - "plan 03 (app-level modal host, 'Sure!' modal opening)"
  - "plan 04 (Train landing and Bots roster reuse the bubble)"
tech-stack:
  added: []
  patterns:
    - "TanStack mutation with scope id to serialize calls, optimistic cache patch for snooze/done only"
key-files:
  created:
    - frontend/src/lib/feedbackAsk.ts
    - frontend/src/hooks/useFeedbackAsk.ts
    - frontend/src/components/feedback/FeedbackAskBubble.tsx
    - frontend/src/components/feedback/__tests__/FeedbackAskBubble.test.tsx
    - frontend/src/pages/__tests__/Import.feedbackAsk.test.tsx
    - frontend/src/hooks/__tests__/useFeedback.test.tsx
  modified:
    - frontend/src/types/users.ts
    - frontend/src/types/feedback.ts
    - frontend/src/lib/analytics.ts
    - frontend/src/hooks/useFeedback.ts
    - frontend/src/components/feedback/FeedbackModal.tsx
    - frontend/src/pages/Import.tsx
    - frontend/src/components/feedback/__tests__/FeedbackModal.test.tsx
key-decisions:
  - "A view response never patches the cached ask state, so it cannot resurrect a dismissed bubble"
  - "Umami click events kept for feedback-ask-sure/later (surface via page; round-1 click history survives only in Umami)"
requirements-completed: [FBASK-05, FBASK-06, FBASK-07, FBASK-10]
duration: ~25 min
completed: 2026-10-06
status: complete
actuals:
  tokens: 8800
  tasks: 2
  commits: 3
plan_head_before: e7a9d965a8fd0d443ed97ebe70ae6844fdb5e129
plan_head_after: cac9a521f1192651ea724098f2a4218270e9c0b0
---

# Phase 234 Plan 02: Hilda feedback ask on Import, FeedbackModal source/placeholder Summary

Shared Hilda feedback-ask bubble (TrainBotBubble reuse, scoped view/snooze/done mutation with optimistic hide) wired into the Import page in place of the ImportBotBubble, plus FeedbackModal source/placeholder props and profile invalidation on every submission.

## Accomplishments

- **Tracer (Task 1):** an eligible user's Import page (`profile.feedback_ask.active`) shows Hilda with "You've been with FlawChess for {N} days now, thanks! Got an idea that would make it better for you?" for both the welcome and explore variants (D-03). One `{action:'view'}` is POSTed when the bubble mounts, never on profile fetch. "Maybe later" fires the Umami action event, hides the bubble at once (cancelQueries + optimistic patch) and POSTs snooze; "Sure!" fires its event and POSTs done (plan 03 will open the modal from there).
- **Task 2 (TDD):** `FeedbackModal` takes optional `placeholder` and `source` (defaults: the floating-button placeholder via `DEFAULT_FEEDBACK_PLACEHOLDER`, `'floating_button'`); `useFeedback` invalidates `USER_PROFILE_QUERY_KEY` on success so any feedback ends the ask. RED commit (`d51cba6d8`) precedes GREEN (`cac9a521f`).
- Mutation check: reverting the "view never patches the cache" guard makes the "view resolves active after Maybe later" test fail (the test holds the snooze unresolved so only the view response can touch the cache).

## Umami rationale (FBASK-10, "track only what the browser knows")

The two click events (`feedback-ask-sure`, `feedback-ask-later`) are kept despite the DB holding the ask state, because they carry what `users.prompt_state` cannot:

1. **Surface:** `trackFeature` stamps the route's page ('library' for /library/import, 'train', 'bots'); `prompt_state` stores no surface, so the event answers which surface earns the feedback.
2. **Round-1 click history:** `prompt_state.feedback_v1` is overwritten in place, a round-2 view replaces the object and drops round 1's `status`/`snoozed_by`/`snoozed_at_days`, so a round-1 "Maybe later" click survives only in Umami.

No day count, round or free value is sent (D-04); `trackFeature` is called only from the two click handlers, never on mount.

## Task Commits

| Task | Commit | Description |
| ---- | ------ | ----------- |
| 1 (tracer) | c0e7a5c62 | Hilda ask on Import: bubble, hook, helpers, types, Umami targets, tests |
| 2 RED | d51cba6d8 | Tests for FeedbackModal source/placeholder and useFeedback invalidation |
| 2 GREEN | cac9a521f | FeedbackModal props, FeedbackSource type, useFeedback onSuccess invalidation |

## Deviations from Plan

None - plan executed exactly as written. (The FeedbackAskBubble props interface is not exported, per "export only the component"; the view-after-Later test was strengthened with a deferred snooze after a mutation check showed the first version could not detect the resurrect bug.)

## Verification

- `npx vitest run` on the plan's test files: green. Full `npm test -- --run`: 312 files / 5160 tests pass.
- `npm run lint`, `npm run build` (tsc -b), `npm run knip`: exit 0.
- Acceptance greps: `feedbackAskDays`/`feedbackAskCopy` exports, `scope: { id: FEEDBACK_ASK_MUTATION_SCOPE }`, `cancelQueries`, single `HILDA_ID` definition, `PERSONA_REGISTRY[HILDA_ID]`, both action targets once each, rationale comment, `surface="import"`, `importBotBubbleCopy.ts` unchanged, `DEFAULT_FEEDBACK_PLACEHOLDER` defined and used, `invalidateQueries({ queryKey: USER_PROFILE_QUERY_KEY })`: all pass.

## Known Stubs

None. Until plan 03 lands, "Sure!" records done and hides Hilda without opening the modal (documented in the plan; the phase merges as a whole).

## Threat Flags

None.

## Self-Check: PASSED

All created files exist and commits c0e7a5c62, d51cba6d8, cac9a521f are ancestors of HEAD.
