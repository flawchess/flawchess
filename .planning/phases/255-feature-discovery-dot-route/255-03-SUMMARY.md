---
phase: 255-feature-discovery-dot-route
plan: 03
subsystem: ui
tags: [react, feature-route, nav, vitest, localstorage]
requires:
  - phase: 255-feature-discovery-dot-route
    provides: "route dot placement hooks, RouteDot, FeatureRouteRecorder (plan 255-02)"
provides:
  - "MobileMoreDrawer on useNavIndicators: same lock, same placement, same D-17 badge rule as the header and bottom bar"
  - "removeRetiredDotKeys sweep mounted once per load in ProtectedLayout"
  - "describe('Feature route dot') cross-surface tests in App.test.tsx"
  - "feature_route on the three fully typed UserProfile test fixtures"
affects: [255-04, 255-05, 255-06]
tech-stack:
  added: []
  patterns:
    - "all three nav surfaces consume one hook (useNavIndicators); App.tsx holds no hand-written dot markup"
key-files:
  created: []
  modified:
    - frontend/src/App.tsx
    - frontend/src/App.test.tsx
    - frontend/src/lib/retiredLocalStorage.ts
    - frontend/src/lib/__tests__/retiredLocalStorage.test.ts
    - frontend/src/lib/impersonation.test.ts
    - frontend/src/components/settings/__tests__/LeaderboardPrivacyCard.test.tsx
    - frontend/src/components/feedback/__tests__/FeedbackAskBubble.test.tsx
key-decisions:
  - "The drawer dot testid is built from the row's route (`${to.slice(1)}-notification-dot-drawer`); the Train row drops its dot while the waiting badge shows (D-17), the drawer itself renders no badge"
  - "RETIRED_DOT_FLAG_KEY_PREFIX and RETIRED_DOT_HINT_KEYS are exported as the plan lists; knip accepts them (same-file use)"
requirements-completed: [D-02, D-03, D-04, D-12, D-17, D-23]
duration: 12 min
completed: 2026-11-15
status: complete
commits: 4
plan_head_before: 77b01ff80548f8d803ac2393579013d61bcfd036
plan_head_after: b2bc0e10481620176c80dcf6ee8e39eb0748486d
actuals:
  tokens: 7000
  tasks: 2
  commits: 4
coverage:
  - deliverable: "The More drawer carries the same nav-level route dot as the bottom bar, with the D-17 badge rule, D-23 pause and D-12 order"
    human_judgment: false
    verification:
      - kind: test
        ref: "frontend/src/App.test.tsx#Feature route dot"
        status: pass
  - deliverable: "Retired per-device dot keys are swept once per load; unrelated keys survive; storage errors are swallowed"
    human_judgment: false
    verification:
      - kind: test
        ref: "frontend/src/lib/__tests__/retiredLocalStorage.test.ts#removeRetiredDotKeys"
        status: pass
---

# Phase 255 Plan 03: More Drawer on the Route and Retired Key Sweep Summary

The More drawer now takes its route dot, its unlock rule and its Train badge rule from `useNavIndicators`, the same hook the desktop header and the bottom bar use, so the three nav surfaces can no longer disagree; the retired per-device dot keys are swept once per app load.

## Accomplishments

- `MobileMoreDrawer` dropped its inline game count, `noGames`, `tier1` and unlock expression and the hand-copied Library dot. It reads `navUnlocked`, `routeNav` and `trainBadgeLabel` from `useNavIndicators()` and renders `<RouteDot variant="corner">` on the row whose `to` equals `routeNav`, except on `/train` while the waiting badge shows (D-17). `App.tsx` has zero `animate-ping` and zero hand-written dot markup.
- `describe('Feature route dot')` (11 cases): Library dot on all three surfaces and gone after import; D-17 badge plus Bots dot together and the drawer Bots dot; no Train dot in the drawer while the badge shows; at most one header dot and a drawer dot on the same nav item across seven route states (D-02); D-23 pause on a zero-game account and the Openings dot once unlocked; D-12 Endgames dot with every other step resolved; null `feature_route` fails closed; no Train dot inside the Train section (D-03). All states use `current: null`, so the clock added in plan 255-04 cannot expire them.
- `removeRetiredDotKeys` (plus the two key constants) removes every `user_flag:` key and `played-as-hint-dismissed` / `filters-hint-dismissed`, mirrors `removeRetiredBookmarkChartKeys`, and is called from one `ProtectedLayout` mount effect.
- `feature_route: { steps: {}, current: null }` added to the three typed fixtures (`base`, `PROFILE`, `makeProfile`).

## Task Commits

| Task | Commit | Type |
| ---- | ------ | ---- |
| 1 RED (cross-surface tests, 8 failing) | 32990810d | test |
| 1 GREEN (drawer on useNavIndicators) | baefea3fd | feat |
| 2 RED (sweep tests, 4 failing) | dca32bbd5 | test |
| 2 GREEN (sweep, mount effect, fixtures) | b2bc0e104 | feat |

## Deviations from Plan

None - plan executed exactly as written.

Verification: vitest on App.test.tsx, retiredLocalStorage.test.ts, impersonation.test.ts, LeaderboardPrivacyCard.test.tsx and FeedbackAskBubble.test.tsx (117 passed); `npm run lint`, `npm run build` and `npm run knip` clean (knip prints two pre-existing configuration hints, exit 0). Acceptance greps: `animate-ping` in App.tsx 0, drawer testid literal 0, `removeRetiredDotKeys` in App.tsx 2.

## Known Stubs

None.

## Threat Flags

None. T-255-15 is mitigated: the sweep matches only the exact `user_flag:` prefix and two exact hint keys, a test pins that unrelated keys survive, and storage errors return 0.

## Next Phase Readiness

Plans 255-04 (clock, `current` stamp), 255-05 (Library/Openings sites) and 255-06 (Train) can proceed; the nav surfaces are final and need no further change from them.

## Self-Check: PASSED

All modified files exist; commits 32990810d, baefea3fd, dca32bbd5 and b2bc0e104 are ancestors of HEAD.
