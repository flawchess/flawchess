---
phase: 246-train-subnav-split
plan: 08
subsystem: ui
tags: [react, react-router, tanstack-query, vitest]

requires:
  - phase: 246-train-subnav-split
    provides: "246-02 layout (train-today-panel, train-leaderboard-panel, useTrainLoop immersive/todayVisited)"
provides:
  - "TrainStartScreenProps.isVisible: gates TrainLandingHost and TrainStreakCard so a hidden landing records nothing"
  - "TrainMedalDialogHost mounted in the Train layout outside immersive views"
  - "Today landing without TrainLeaderboardCard (Leaderboard tab only)"
affects: [246-03, 246-06]

actuals:
  tokens: 14000
  tasks: 3
  commits: 3
plan_head_before: 8ef44c82e10da7c069817efa68732c2706fa2d49
plan_head_after: 41f30c5e1293cdc9bd79d7d098dfc21dd68a3862

key-files:
  created: []
  modified:
    - frontend/src/pages/Train.tsx
    - frontend/src/components/train/TrainStartScreen.tsx
    - frontend/src/pages/__tests__/Train.subnav.test.tsx
    - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
    - frontend/src/pages/__tests__/Train.solveLoop.test.tsx
    - frontend/src/components/train/TrainLeaderboardCard.tsx
    - frontend/src/components/train/medals/TrainMedalDialogHost.tsx
    - frontend/src/hooks/useTrainSession.ts
    - frontend/src/App.tsx

key-decisions:
  - "isVisible conditional children (never an early return) so TrainScheduleSettings keeps its child position and pending debounce"
  - "Medal host sits at a stable position in the layout, gated by !immersive"

requirements-completed: [D-03, D-06, D-16]

status: complete
---

# Phase 246 Plan 08: Hidden landing records nothing, medal host in the layout Summary

**`TrainStartScreen` takes `isVisible` so a Today panel hidden behind another tab counts no feedback-ask view and consumes no streak arrival; the medal dialog host moves to the Train layout; Today loses the leaderboard card.**

## Accomplishments

- `TrainLandingHost` and `TrainStreakCard` (fresh/resume, completed and exhausted landings) mount only while `isVisible` (`isToday`). `TrainScheduleSettings` stays at a stable child position, so a pending debounced save survives a flip (pinned by a same-DOM-node test).
- `TrainMedalDialogHost` renders from `Train.tsx` as `{!immersive && ...}` right after the subnav: it opens on a Leaderboard deep link, is absent in the loop, and does not reopen after dismissal and a tab round trip.
- `TrainLeaderboardCard`, the medal host and `TrainEmptyBody`'s `isGuest` prop are gone from `TrainStartScreen`; `LANDING_CONTAINER_CLASS` drops its top padding (the panel's `mt-4` supplies the gap).
- Tank's landing intro and the intro stepper outcomes (D-16) are stated and tested: the same Tank copy returns after a tab switch; Back out of the stepper stamps nothing and the next Start replays step one.
- Docstrings and the `/train/*` Suspense fallback ("Loading…", `train-loading` testid kept) now match the layout.

## Task Commits

1. Task 1 (tracer): `acb42e299` feat(246-08): a hidden Today landing records no feedback-ask view or streak arrival
2. Task 2: `bbee6929e` feat(246-08): medal host moves to the Train layout, Today loses the leaderboard card
3. Task 3: `41f30c5e1` docs(246-08): comments and Suspense copy catch up with the Train layout

## Mutation checks (each reverted before commit)

| Mutation | Failing tests (first failing assertion) |
|----------|-----------------------------------------|
| `TrainStreakCard` rendered unconditionally | page "first Today visit left for Leaderboard ... no view, no snapshot" fails on `readStreakLastSeen` expected null (snapshot written); also "Back out of the loop first-mounts the landing while hidden" and the four component `isVisible` tests |
| `TrainLandingHost` rendered unconditionally | same page test fails on `feedbackAskMutate` called 1 time, expected 0; also the Back-out page test, the Tank intro test and the component tests |
| Early return rendering only `TrainScheduleSettings` while hidden | component test "flipping isVisible keeps the schedule card on the same DOM node" (only failure) |
| `TrainMedalDialogHost` rendered unconditionally | page test "shows no dialog once the loop is entered, even when the medals arrive after Start" (dialog present) |

The page-level hidden-landing test asserts the mutate count and the snapshot before the DOM absence checks, so each gate's mutation fails on the effect it guards.

## Verification

- Full frontend suite: 350 files, 5890 tests pass. Targeted run of the five plan files: 141 pass.
- `npm run lint`, `npm run build`, `npm run knip`: clean (knip prints its two pre-existing configuration hints).

## Deviations from Plan

None - plan executed as written. Small notes:

- The Task 2 acceptance line about a zero-game guest on `/train/leaderboard` is met by not touching `TrainLeaderboardCard`: no new empty state was added, and its existing guest CTA/empty copy is covered by `TrainLeaderboardCard.test.tsx`. I did not add a page-level guest test (the page test's profile mock is a fixed non-guest).
- I also updated one stale `Train.tsx` reference in `useTrainSession.ts`'s top docstring (`showLoop` gate now lives in `useTrainLoop`), beyond the four comment sites the plan listed.

## Known Stubs

None.

## Threat Flags

None. T-246-20 is mitigated by `isVisible` and pinned by the mutation checks above.

## Self-Check: PASSED

- FOUND commits: acb42e299, bbee6929e, 41f30c5e1
- FOUND: frontend/src/components/train/TrainStartScreen.tsx (no TrainMedalDialogHost JSX, no TrainLeaderboardCard JSX), frontend/src/pages/Train.tsx (`!immersive && <TrainMedalDialogHost`), frontend/src/pages/__tests__/Train.subnav.test.tsx (`train-landing-host`)
