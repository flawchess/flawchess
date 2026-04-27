---
phase: 71-frontend-stats-subtab-openinginsightsblock
plan: "03"
subsystem: frontend
tags: [typescript, react, tanstack-query, vitest, opening-insights]
dependency_graph:
  requires: []
  provides:
    - frontend/src/types/insights.ts (OpeningInsightFinding, OpeningInsightsResponse)
    - frontend/src/lib/openingInsights.ts (trimMoveSequence, getSeverityBorderColor, threshold constants)
    - frontend/src/hooks/useOpeningInsights.ts (useOpeningInsights)
  affects:
    - Plans 04 and 05 (consume helpers and hook)
tech_stack:
  added: []
  patterns:
    - TanStack Query useQuery with POST body (hybrid pattern — not present in other hooks)
    - Pure function module with exported constants (arrowColor.ts style)
    - TDD: RED/GREEN/REFACTOR cycle with vitest
key_files:
  created:
    - frontend/src/lib/openingInsights.ts
    - frontend/src/lib/openingInsights.test.ts
    - frontend/src/hooks/useOpeningInsights.ts
    - frontend/src/hooks/__tests__/useOpeningInsights.test.tsx
  modified:
    - frontend/src/types/insights.ts
decisions:
  - "Import filter types from @/types/api (not FilterPanel) — all five filter types live there, consistent with useStats.ts"
  - "D-05 orphan-black-ply rule: when last-2 entry plys start mid-move on a Black ply, drop the orphan so render starts on White; matches all 6 table examples"
metrics:
  duration: "~4 minutes"
  completed: "2026-04-27"
  tasks_completed: 3
  files_created: 4
  files_modified: 1
---

# Phase 71 Plan 03: Opening Insights — Helper Foundations Summary

TypeScript types, pure helpers, and TanStack Query hook wired up; all 17 new unit/integration tests pass.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Extend types/insights.ts with Phase 71 wire types | 9652148 | frontend/src/types/insights.ts |
| 2 | Build openingInsights.ts helpers + unit tests (TDD) | e67b607 | frontend/src/lib/openingInsights.ts, openingInsights.test.ts |
| 3 | Build useOpeningInsights hook + integration test | e6e194c | frontend/src/hooks/useOpeningInsights.ts, useOpeningInsights.test.tsx |

## What Was Built

### Types (Task 1)

Appended `OpeningInsightFinding` and `OpeningInsightsResponse` to `frontend/src/types/insights.ts`. Both mirror `app/schemas/opening_insights.py` exactly with snake_case field names. Includes `entry_san_sequence: string[]` added by the Phase 71 backend amendment (Plan 01, D-13).

### Pure Helpers (Task 2)

`frontend/src/lib/openingInsights.ts` exports:

- `trimMoveSequence(entrySanSequence, candidateMoveSan)` — D-05 algorithm: renders the last 2 entry plys + candidate move as a compact PGN string with ellipsis prefix. Drops orphan leading Black plies so the render always starts on a White ply, matching all 6 user-facing examples in the spec.
- `getSeverityBorderColor(classification, severity)` — maps the four `(classification, severity)` combinations to the exact hex constants from `arrowColor.ts` (DARK_RED / LIGHT_RED / DARK_GREEN / LIGHT_GREEN).
- `MIN_GAMES_FOR_INSIGHT = 20` and `INSIGHT_RATE_THRESHOLD = 55` — mirror backend constants.
- `INSIGHT_THRESHOLD_COPY` — single shared string used by InfoPopover (D-20) and empty-state copy.

All 13 unit tests pass covering 6 trim edge cases, 4 severity color mappings, and 3 constant assertions.

### Hook (Task 3)

`frontend/src/hooks/useOpeningInsights.ts` exports `useOpeningInsights`:

- Uses `useQuery` (not `useMutation`) — filter-driven auto-fetch on change (D-16).
- Always sends `color: 'all'` regardless of input filters (D-02).
- Normalizes filter fields identically to `useMostPlayedOpenings` in `useStats.ts`.
- Uses snake_case POST body keys matching the Pydantic schema.
- Query key includes all 6 filter fields for correct cache invalidation.
- No per-component Sentry calls — global `QueryCache.onError` handles errors per CLAUDE.md.

All 4 integration tests pass: POST body correctness, recency normalization, query key reactivity, response data passthrough.

## Deviations from Plan

### [Rule 3 - Blocker] Corrected filter type import path

The plan template specified `import from '@/components/filters/FilterPanel'` for `Recency`, `TimeControl`, `Platform`, `OpponentType`, `OpponentStrength`. However, `FilterPanel.tsx` only exports `FilterState` (interface) — all five filter types live in `@/types/api`, consistent with the existing `useStats.ts` hook pattern. Corrected the import to `@/types/api` to match the actual codebase structure.

## Known Stubs

None — this plan creates helper infrastructure only (no UI rendering that could contain stub data).

## Knip Note

At the end of this plan (wave 1), the following exports are not yet consumed by production code:

- `INSIGHT_THRESHOLD_COPY` — consumed by Plan 05 (OpeningInsightsBlock InfoPopover)
- `getSeverityBorderColor` and `trimMoveSequence` — consumed by Plan 04 (OpeningFindingCard)
- `MIN_GAMES_FOR_INSIGHT` and `INSIGHT_RATE_THRESHOLD` — may be consumed by Plans 04/05/06
- `useOpeningInsights` — consumed by Plan 05 (OpeningInsightsBlock)

Knip currently passes because each export is imported by its companion test file. Plans 04/05/06 will wire them into production components.

## Self-Check

### Files exist:

- [x] `frontend/src/types/insights.ts` — contains OpeningInsightFinding, OpeningInsightsResponse
- [x] `frontend/src/lib/openingInsights.ts` — exports trimMoveSequence, getSeverityBorderColor, constants
- [x] `frontend/src/lib/openingInsights.test.ts` — 13 unit tests
- [x] `frontend/src/hooks/useOpeningInsights.ts` — exports useOpeningInsights
- [x] `frontend/src/hooks/__tests__/useOpeningInsights.test.tsx` — 4 integration tests

### Commits exist:

- [x] 9652148 — feat(71-03): add OpeningInsightFinding and OpeningInsightsResponse TS types
- [x] e67b607 — feat(71-03): implement openingInsights helpers and unit tests
- [x] e6e194c — feat(71-03): implement useOpeningInsights hook and integration tests

### Verification:

- [x] All 123 frontend tests pass (including 17 new ones)
- [x] `npm run lint` passes
- [x] `npm run build` passes
- [x] `npm run knip` passes
- [x] `npx tsc --noEmit` produces no errors

## Self-Check: PASSED
