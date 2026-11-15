---
phase: 255-feature-discovery-dot-route
plan: 02
subsystem: ui
tags: [react, tanstack-query, feature-route, nav, vitest]
requires:
  - phase: 255-feature-discovery-dot-route
    provides: "POST /users/me/feature-route and profile.feature_route (plan 255-01)"
provides:
  - "FEATURE_ROUTE registry and pure arbiter (resolveRouteDot, planRouteWrites, applyRouteWrite, findCandidate)"
  - "read hooks useNavUnlocked, useRouteCtx, useRouteDotPlacement, useRouteDot"
  - "useRecordFeatureRoute scoped mutation with optimistic profile patch"
  - "RouteDot component and FeatureRouteRecorder mounted in ProtectedLayout"
  - "header and bottom-bar route dot driven by one placement; per-device dot flags retired from the nav"
affects: [255-03, 255-04, 255-05, 255-06]
tech-stack:
  added: []
  patterns:
    - "pure registry plus arbiter in lib/, read-only hooks at render sites, mutation only in the recorder (no QueryClient in nav render path)"
    - "locked first unresolved step pauses the route (D-23): findCandidate returns null instead of passing over"
key-files:
  created:
    - frontend/src/lib/featureRoute.ts
    - frontend/src/hooks/useFeatureRoute.ts
    - frontend/src/hooks/useRecordFeatureRoute.ts
    - frontend/src/components/feature-route/RouteDot.tsx
    - frontend/src/components/feature-route/FeatureRouteRecorder.tsx
    - frontend/src/components/feature-route/__tests__/FeatureRouteRecorder.test.tsx
    - frontend/src/lib/__tests__/featureRoute.test.ts
  modified:
    - frontend/src/App.tsx
    - frontend/src/App.test.tsx
    - frontend/src/types/users.ts
    - frontend/src/lib/theme.ts
  deleted:
    - frontend/src/hooks/useUserFlag.ts
key-decisions:
  - "isNavActive moved verbatim from App.tsx into lib/featureRoute.ts so the nav and the arbiter share one copy"
  - "useRecordFeatureRoute.onSuccess writes the server state (including null for a corrupt state) only when it is the last pending feature-route mutation"
  - "FeatureRouteRecorder is mounted in the main ProtectedLayout tree only; the /analysis branch has no route step to record"
requirements-completed: [D-01, D-02, D-03, D-05, D-06, D-08, D-09, D-12, D-14, D-15, D-17, D-18, D-21, D-23]
duration: 25 min
completed: 2026-11-15
status: complete
commits: 3
plan_head_before: ef46485cabc8b4f7678481be5995163ca8804000
plan_head_after: 03d623cb38765cf949d41b1742ed7a9347ee04f3
actuals:
  tokens: 12000
  tasks: 2
  commits: 3
coverage:
  - deliverable: "A zero-game signup's Import visit is stored through POST /users/me/feature-route and the route dot hops to Train"
    human_judgment: false
    verification:
      - kind: test
        ref: "frontend/src/components/feature-route/__tests__/FeatureRouteRecorder.test.tsx#(a) a zero-game signup opening /library/import stores import done and the dot hops to Train"
        status: pass
  - deliverable: "Train completes on use, impersonation and corrupt state never write, a locked target records nothing"
    human_judgment: false
    verification:
      - kind: test
        ref: "frontend/src/components/feature-route/__tests__/FeatureRouteRecorder.test.tsx#(b)-(e)"
        status: pass
  - deliverable: "Header and bottom bar render one route dot; the Train badge replaces only the Train nav dot (D-17)"
    human_judgment: false
    verification:
      - kind: test
        ref: "frontend/src/App.test.tsx#Train waiting badge"
        status: pass
  - deliverable: "Step list pinned in D-06 order; locked first step pauses the route (D-23); write planning and applyRouteWrite rules"
    human_judgment: false
    verification:
      - kind: test
        ref: "frontend/src/lib/__tests__/featureRoute.test.ts"
        status: pass
---

# Phase 255 Plan 02: Route Dot Tracer and Arbiter Summary

The frontend side of the feature-discovery route: an ordered registry with a pure arbiter, a scoped mutation and a recorder, and one red dot that moves from the Library nav item to Train on the desktop header and mobile bottom bar once a new signup opens Library Import.

## Accomplishments

- `frontend/src/lib/featureRoute.ts`: the nine D-06 steps as `FEATURE_ROUTE`, `resolveRouteDot` (one placement: nav, subtab or control slot), `findCandidate` with the D-23 stop rule (a locked first unresolved step gives no dot and no later step), `planRouteWrites` (D-15 recording of visit steps, nothing for a locked target per A-2, nothing for Train which completes on use), `applyRouteWrite`, `isRouteWriteNeeded`, `isNavActive`.
- Read hooks (`useNavUnlocked`, `useRouteCtx`, `useRouteDotPlacement`, `useRouteDot`) that touch only `useUserProfile`, `useReadiness` and `useLocation`, so `App.test.tsx` still renders the nav without a QueryClient.
- `useRecordFeatureRoute`: scoped mutation, no-ops on missing or corrupt state, impersonation and already-done steps; optimistic patch in `onMutate`; server state applied only when it is the last pending mutation.
- `FeatureRouteRecorder` (sent-key ref guards against POST loops), `RouteDot` (corner and mobile-nav geometry, `ROUTE_DOT_COLOR_CLASS` in `theme.ts`), `FeatureRouteState` types on `UserProfile.feature_route`.
- `App.tsx`: `useNavIndicators` now exposes `routeNav` from the placement and `useNavUnlocked`; `NavDot`, the three visited-flag constants and effects and `isActive` are gone; `useUserFlag.ts` deleted. The Train badge branch is untouched and replaces only the Train nav dot.

## Task Commits

| Task | Commit | Type |
| ---- | ------ | ---- |
| 1 RED (recorder test) | a7d1cafbb | test |
| 1 GREEN (registry, hooks, recorder, nav) | faccb8412 | feat |
| 2 (arbiter unit tests) | 03d623cb3 | test |

## Deviations from Plan

None - plan executed exactly as written.

Task 2 verification detail: the D-23 case is load-bearing. Temporarily changing `findCandidate` to `continue` past an unavailable entry (the withdrawn pass-over rule) made `a games-free step after a locked one stays hidden until the locked step unlocks and is resolved` fail (1 failed, 24 passed); the change was reverted and all 25 pass. The launch-route locked cases alone would not catch the regression because no available step follows the locked ones there, which is why the reordered-route case exists.

Verification run: `uv run pytest tests/test_feature_route.py -x` (10 passed), vitest for the recorder test, `featureRoute.test.ts` and `App.test.tsx` (106 passed), `npm run lint`, `npm run build` and `npm run knip` clean. Acceptance greps: App.tsx flag/NavDot references 0, `FeatureRouteRecorder` 2, `useUserFlag.ts` deleted, `ROUTE_DOT_COLOR_CLASS` present in theme.ts.

## Known Stubs

None. `MobileMoreDrawer` still derives its own unlock and renders the hand-copied Library `noGames` dot (`library-notification-dot-drawer`); this is intentional per the plan and moves onto the route in plan 255-03, together with the localStorage key sweep and the three fully typed `UserProfile` test fixtures (they are outside `tsc -b`).

## Threat Flags

None. The only new surface is the client call to the endpoint already modelled in plan 255-01; T-255-05 (sent-key ref plus `isRouteWriteNeeded`) and T-255-14 (impersonation no-op, recorder test case c) are mitigated.

## Next Phase Readiness

Plan 255-03 can move the More drawer onto the route (`useNavUnlocked`, `useRouteDotPlacement`), add the retired-key sweep and fix the three typed `UserProfile` fixtures. Plans 255-05 and 255-06 call `useRouteDot` at the subtab and control sites and `useRecordFeatureRoute` from the control handlers; the `current` stamp and skip clock arrive in plan 255-04, which reuses `findCandidate` and the `REORDERED_ROUTE` test constant.

## Self-Check: PASSED

All created files exist, `useUserFlag.ts` is gone, and commits a7d1cafbb, faccb8412 and 03d623cb3 are ancestors of HEAD.
