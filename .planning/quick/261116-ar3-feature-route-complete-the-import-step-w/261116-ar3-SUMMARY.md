---
phase: quick-261116-ar3
plan: 01
subsystem: frontend/feature-route
tags: [feature-route, onboarding, import]
status: complete
requires: []
provides:
  - "Import route step completes on hasGames (third completion kind 'games')"
affects:
  - frontend/src/lib/featureRoute.ts
  - frontend/src/hooks/useFeatureRoute.ts
  - frontend/src/components/feature-route/FeatureRouteRecorder.tsx
key-files:
  modified:
    - frontend/src/lib/featureRoute.ts
    - frontend/src/hooks/useFeatureRoute.ts
    - frontend/src/components/feature-route/FeatureRouteRecorder.tsx
    - frontend/src/lib/__tests__/featureRoute.test.ts
    - frontend/src/components/feature-route/__tests__/FeatureRouteRecorder.test.tsx
    - frontend/src/App.test.tsx
    - .planning/phases/255-feature-discovery-dot-route/255-CONTEXT.md
decisions:
  - "Import completes on hasImportedGames(profile), not navUnlocked, so the dot may move to Train while an import runs"
  - "No Import-button-click completion; deleting all games does not un-complete"
metrics:
  tasks: 3
  commits: 3
plan_head_before: 7e6c09c5e58ff7b293c082b255917667bd94dd63
plan_head_after: 2722064818999eb8ba074a29ff26887c14747441
commits: 3
actuals:
  tasks: 3
  commits: 3
---

# Quick 261116-ar3: Import step completes when games exist

The feature-discovery route's Import step is now completed by imported games (`RouteCtx.hasGames`, fed by `hasImportedGames(profile)`) instead of a visit to /library/import, overruling Phase 255 D-14. A zero-game account on the Import page is only stamped current (D-10 clock) and sees no dot; once games exist the recorder posts `done:import` from any page and the dot moves to Train.

## Commits

- 1ce283385: feat, registry kind `games`, `RouteCtx.hasGames`, hook, recorder wiring, tracer recorder test
- bcc18f995: test, arbiter, recorder and nav cases pinning the rule
- 272206481: docs(255), dated overrule note on D-14, Import removed from D-13's visit list

## Verification

- Mutation check: making the `games` branch return false failed 6 new/rewritten tests (4 arbiter, recorder (a) and (n)); restored, green.
- lint, build, knip exit 0; full `npm test -- --run`: 6462 passed.
- CHANGELOG.md untouched (the Phase 255 bullet does not claim Import completes on visit).

## Deviations from Plan

None. The plan executed as written.

## Known Stubs

None.

## Self-Check: PASSED
