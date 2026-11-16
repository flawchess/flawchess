---
phase: 255-feature-discovery-dot-route
plan: 05
subsystem: ui
tags: [react, feature-route, openings, library, vitest]
requires:
  - phase: 255-feature-discovery-dot-route
    provides: "route arbiter, useRouteDot, useRecordFeatureRoute, RouteDot (255-02), clock and seed (255-04)"
provides:
  - "Route dots on the Library Import and Stats subtabs and the Openings Stats subtab, desktop and mobile"
  - "Route-driven played-as and filters dots on the desktop strip and every mobile site, with completion writes on use"
  - "OpeningColorSwitch onAnyClick prop; useSidebarState reduced to open state"
affects: [255-06, 255-07]
tech-stack:
  added: []
  patterns:
    - "controls record their route step in the existing handler, independent of where the dot is (D-15)"
key-files:
  created: []
  modified:
    - frontend/src/pages/library/LibraryPage.tsx
    - frontend/src/pages/library/__tests__/LibraryPage.reroute.test.tsx
    - frontend/src/pages/Openings.tsx
    - frontend/src/pages/openings/useSidebarState.ts
    - frontend/src/pages/openings/OpeningsDesktopSidebar.tsx
    - frontend/src/pages/openings/OpeningsMobileBoardPanel.tsx
    - frontend/src/components/openings/stats/OpeningColorSwitch.tsx
    - frontend/src/pages/__tests__/Openings.render.test.tsx
key-decisions:
  - "Openings.tsx no longer reads the profile (hasGames fed only the retired hints), so its useUserProfile import was removed"
  - "The mobile Stats colour switch is wrapped in a relative span that carries the played-as dot; onAnyClick records the step even on the already selected colour"
  - "A real colour change on the mobile switch records twice in one click (onAnyClick plus handleStatsColorChange); left as is, the server DONE guard makes the second a no-op"
requirements-completed: [D-02, D-03, D-07, D-13, D-15, D-20, D-23]
duration: 25 min
completed: 2026-11-15
status: complete
commits: 4
plan_head_before: da27b77036cb39af95999e1fe088b2bba7992876
plan_head_after: 350af653ecf7587797303ac40ec5d7a9ebc0ef73
actuals:
  tokens: 14000
  tasks: 2
  commits: 4
coverage:
  - deliverable: "D-03 / D-20 / D-23: Import, Library Stats and Openings Stats subtab dots on desktop and mobile; none on the target page; none when the locked step pauses the route or feature_route is missing"
    human_judgment: false
    verification:
      - kind: test
        ref: "frontend/src/pages/library/__tests__/LibraryPage.reroute.test.tsx#LibraryPage route dot"
        status: pass
      - kind: test
        ref: "frontend/src/pages/__tests__/Openings.render.test.tsx#OpeningsPage route dot on the Stats subtab"
        status: pass
  - deliverable: "D-07 / D-13 / D-15: played-as and filters dots on every site, completion on use (including the selected colour and Apply without change), recorded off-route, no write without feature_route"
    human_judgment: false
    verification:
      - kind: test
        ref: "frontend/src/pages/__tests__/Openings.render.test.tsx#OpeningsPage played-as route step"
        status: pass
      - kind: test
        ref: "frontend/src/pages/__tests__/Openings.render.test.tsx#OpeningsPage filters route step"
        status: pass
  - deliverable: "D-07: bookmarks dot and localStorage hint chain gone"
    human_judgment: false
    verification:
      - kind: test
        ref: "frontend/src/pages/__tests__/Openings.render.test.tsx#OpeningsPage bookmarks dot is gone (D-07)"
        status: pass
---

# Phase 255 Plan 05: Library and Openings Route Sites Summary

Inside Library and Openings the one route dot now lands on the Import, Library Stats or Openings Stats subtab, or on the played-as and filters controls, and using a control records its step server-side; the localStorage hint chain and the bookmarks dot are gone.

## Accomplishments

- Library: `useRouteDot('subtab:library-import')` and `('subtab:library-stats')` run before the redirect early return; `RouteDot` is the last child of the four tab triggers (desktop and mobile). Testids are section-prefixed because Library and Openings both use `tab-stats`.
- Openings Stats subtab: `useRouteDot('subtab:openings-stats')` on `tab-stats` and `tab-stats-mobile`.
- Played-as and filters: `showPlayedAsDot` / `showFiltersDot` replace the three hint props. The desktop strip colour button, the mobile Moves/Games toggle and the mobile Stats colour switch carry the played-as dot; the desktop strip Filters button and both mobile Filters buttons carry the filters dot, and the red dot wins over the brown modified-filters dot.
- Completion writes: `recordRouteStep({ action: 'done', step })` in the played-as handlers (`handleStatsColorChange`, desktop `onToggleColor`, mobile `onTogglePlayedAs`) and in both Apply handlers. Umami `trackFeature` calls are unchanged.
- `OpeningColorSwitch` gained optional `onAnyClick`, called before the selected-colour early return; the mobile Stats switch passes the played-as recorder. This closes the checker's info item: a click on the already selected colour completes the step and leaves the colour unchanged.
- `useSidebarState` keeps only sidebar and drawer open state; the bookmarks dot, its props and its panel entry are deleted. No hand-written dot markup remains in the three Openings files.

## Task Commits

| Task | Commit | Type |
| ---- | ------ | ---- |
| 1 RED (subtab dots) | 067bdce70 | test |
| 1 GREEN | 7aba0bc74 | feat |
| 2 RED (played-as, filters, bookmarks) | 4fbff177f | test |
| 2 GREEN | 350af653e | feat |

## Mutation check

Removing the `onAnyClick?.()` call in `OpeningColorSwitch` made `records done on a click of the already selected colour and leaves the colour alone` fail (1 failed, 24 passed). The call was restored.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Openings.render.test.tsx POST mock needed endpoint-specific bodies**
- **Found during:** Task 2 RED
- **Issue:** The generic `post` body made the Stats tab's insights response lack its four lists, so `FindingsSections` threw whenever the response resolved before a test ended (a latent race, exposed once the tests rendered more). The feature-route mutation also needs a valid `FeatureRouteState` body.
- **Fix:** `post` answers by URL: `/users/me/feature-route` returns an empty route state, `/insights/openings` returns the four empty lists, everything else keeps the old `{}`.
- **Files modified:** frontend/src/pages/__tests__/Openings.render.test.tsx
- **Commit:** 4fbff177f

**2. [Rule 1 - Cleanup] Removed the now-unused `hasGames` and `useUserProfile` import from Openings.tsx**
- **Issue:** `hasGames` only fed the retired hint derivations; leaving it would fail lint.
- **Commit:** 350af653e

Otherwise the plan was executed as written. `OpeningColorSwitch.test.tsx` was not extended (not in `files_modified`); the `onAnyClick` behaviour is covered through the page tests and the mutation check above.

## Known Stubs

None.

## Threat Flags

None. T-255-10 holds because the handlers go through `useRecordFeatureRoute` (no-op during impersonation); T-255-11: the retired hint keys are no longer read.

## Verification Run

- `npx vitest run` on `src/pages/library`, `src/pages/__tests__` and `src/components/openings`: 28 files, 418 tests passed.
- `npm run lint`, `npm run build` and `npm run knip` clean (knip prints the two pre-existing configuration hints).
- Acceptance greps: `bg-red-500` 0 in all three Openings files, `hint-dismissed` 0 in useSidebarState.ts, no `bookmarks-notification-dot` outside the absence assertions, `onAnyClick` present in OpeningColorSwitch.tsx and Openings.tsx.

## Next Phase Readiness

Plan 255-06 (Train) and plan 255-07 (full gate) are unaffected by these files.

## Self-Check: PASSED

All modified files exist; commits 067bdce70, 7aba0bc74, 4fbff177f and 350af653e are ancestors of HEAD.
