---
phase: 255-feature-discovery-dot-route
plan: 06
subsystem: ui
tags: [react, feature-route, train, vitest]
requires:
  - phase: 255-feature-discovery-dot-route
    provides: "route arbiter, useRouteDot, useRecordFeatureRoute, RouteDot (255-02), clock and seed (255-04)"
provides:
  - "Train step completes on Start or Resume (D-21), never on opening Train"
  - "Route dot inside the start button on Train, Today, and on the Today tab from other Train tabs"
affects: [255-07]
tech-stack:
  added: []
  patterns:
    - "route dots reach hook-free train components as boolean props decided by Train.tsx"
key-files:
  created: []
  modified:
    - frontend/src/pages/Train.tsx
    - frontend/src/components/train/TrainStartScreen.tsx
    - frontend/src/components/train/TrainSubnav.tsx
    - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
    - frontend/src/pages/__tests__/Train.subnav.test.tsx
key-decisions:
  - "handleEnterLoop in Train.tsx records done for train then calls loop.enterLoop(); useTrainLoop stays route-agnostic and no Umami event is added"
  - "Train.solveLoop.test.tsx needed no change: its profile has no feature_route, so nothing is posted and no readiness noise appeared"
requirements-completed: [D-03, D-13, D-17, D-21]
duration: 20 min
completed: 2026-11-15
status: complete
commits: 4
plan_head_before: 545f7f6384cf04b34a4b02e7f543a111f08c5ea2
plan_head_after: 2190649aec029a4b0057b7b26a7a73886b3d7fa4
actuals:
  tokens: 9000
  tasks: 2
  commits: 4
coverage:
  - deliverable: "D-21: Start and Resume post done for train, opening Train posts nothing, no feature_route posts nothing"
    human_judgment: false
    verification:
      - kind: test
        ref: "frontend/src/pages/__tests__/Train.subnav.test.tsx#Train layout: D-21 the Train step completes on Start or Resume"
        status: pass
  - deliverable: "D-03 / D-17: dot inside btn-train-start and btn-train-resume (also with the waiting badge), on the Today tab from Leaderboard and Archive, one place at a time, none once train is done"
    human_judgment: false
    verification:
      - kind: test
        ref: "frontend/src/pages/__tests__/Train.subnav.test.tsx#Train layout: D-03 one Train dot at a time"
        status: pass
      - kind: test
        ref: "frontend/src/components/train/__tests__/TrainStartScreen.test.tsx#TrainStartScreen route dot"
        status: pass
---

# Phase 255 Plan 06: Train Completes on Use Summary

Train is now done when the user presses Start or Resume on Train, Today; the route dot sits inside that button on Today and on the Today tab from the other Train tabs.

## Accomplishments

- `Train.tsx`: `useRecordFeatureRoute` and two `useRouteDot` calls (`control:train-start`, `subtab:train-today`) above the early returns; `handleEnterLoop` records `{ action: 'done', step: 'train' }` then `loop.enterLoop()` (fresh, warmup and resume share it).
- `TrainStartScreen`: required `showRouteDot` prop; the start button is `relative` and renders `train-start-notification-dot` for all three states. The component stays hook-free.
- `TrainSubnav`: required `showTodayRouteDot` prop; `train-today-notification-dot` is the last child of the Today trigger. The Blunder check tab gets none (D-09).
- `Train.subnav.test.tsx`: the `useUserProfile` mock is now partial (keeps `USER_PROFILE_QUERY_KEY`) with a per-(beta, route) stable profile, `useReadiness` is stubbed with `tier1: true`, and the feature-route POST is a `vi.spyOn(apiClient, 'post')` stub restored after each test.

## Task Commits

| Task | Commit | Type |
| ---- | ------ | ---- |
| 1 RED | 2d1a2fa97 | test |
| 1 GREEN | 630af3dce | feat |
| 2 RED | 1ca6bd33c | test |
| 2 GREEN | 2190649ae | feat |

## Mutation check

Removing the `recordRouteStep` call in `handleEnterLoop` failed the Start and Resume post tests (2 failed, 39 passed). The call was restored.

## Deviations from Plan

None. The plan was executed as written; `Train.solveLoop.test.tsx` was left untouched as the plan allowed, since its run is clean without a readiness stub.

## Known Stubs

None.

## Threat Flags

None. T-255-12 holds: the handler goes through `useRecordFeatureRoute`, which no-ops during impersonation.

## Verification Run

- `npx vitest run` on TrainStartScreen.test.tsx, Train.subnav.test.tsx, Train.solveLoop.test.tsx: 106 passed.
- `npm run lint`, `npm run build` clean; `npm run knip` prints only the two pre-existing configuration hints.
- Acceptance greps: `step: 'train'` present in Train.tsx, both dot testids present, no route-hook import in TrainStartScreen.tsx or TrainSubnav.tsx.

## Self-Check: PASSED

Modified files exist; commits 2d1a2fa97, 630af3dce, 1ca6bd33c and 2190649ae are ancestors of HEAD.
