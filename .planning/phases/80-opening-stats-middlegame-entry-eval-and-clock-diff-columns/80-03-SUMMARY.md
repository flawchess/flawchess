---
phase: 80-opening-stats-middlegame-entry-eval-and-clock-diff-columns
plan: "03"
subsystem: frontend-charts
tags: [frontend, charts, additive, whisker, tdd]
requirements: [D-02]

dependency_graph:
  requires: []
  provides:
    - MiniBulletChart.ciLow/ciHigh props for CI whisker overlay
  affects:
    - frontend/src/components/charts/MiniBulletChart.tsx
    - Plan 05 (MostPlayedOpeningsTable — consumes the new props)

tech_stack:
  added: []
  patterns:
    - Additive optional props with both-required guard (ciLow !== undefined && ciHigh !== undefined)
    - Open-ended CI whisker suppresses end cap when CI extends past chart domain
    - IIFE pattern inside JSX for scoped whisker computation

key_files:
  modified:
    - frontend/src/components/charts/MiniBulletChart.tsx
  created:
    - frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx

decisions:
  - Whisker uses Tailwind bg-foreground/70 (slightly stronger than the bg-foreground/50 zero line); no new theme.ts constant needed since this is a utility class, not a semantic color value.
  - IIFE pattern used inside JSX to scope the clamped/open-ended calculations without polluting the component's top-level scope.
  - afterEach cleanup added to test file (Vitest 4 does not auto-cleanup RTL mounts).
  - "@ts-expect-error" used in two partial-prop tests (only ciLow / only ciHigh) to intentionally test the TypeScript interface while exercising the both-required guard.

metrics:
  duration: "~12 minutes"
  completed: "2026-05-03"
  tasks_completed: 1
  files_changed: 2
---

# Phase 80 Plan 03: MiniBulletChart CI Whisker Props Summary

MiniBulletChart extended with optional ciLow/ciHigh props that draw a 95% CI horizontal whisker with end caps over the value bar, with open-ended cap suppression when the CI extends past the chart domain.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED | Add failing tests for CI whisker | 52df5cb | frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx (created) |
| 1 GREEN | Implement ciLow/ciHigh props + whisker JSX | e265421 | MiniBulletChart.tsx (modified), MiniBulletChart.test.tsx (cleanup fix) |

## New Props Added

| Prop | Type | Description |
|------|------|-------------|
| `ciLow?` | `number` | 95% CI lower bound in domain units (signed). Whisker renders only when both provided. |
| `ciHigh?` | `number` | 95% CI upper bound in domain units (signed). Whisker renders only when both provided. |

## New data-testid Attributes

| testid | Element | Visibility |
|--------|---------|------------|
| `mini-bullet-whisker` | Horizontal whisker line | Always when both props provided |
| `mini-bullet-whisker-cap-low` | Left end cap | Suppressed when ciLow < -domain |
| `mini-bullet-whisker-cap-high` | Right end cap | Suppressed when ciHigh > +domain |

## Tests

9 tests pass (1 backward compat + 8 CI whisker behavior):

1. Renders unchanged when ciLow and ciHigh are omitted (backward compat)
2. Renders whisker line when both ciLow and ciHigh provided
3. Whisker has both end caps when CI fits within domain
4. Left cap suppressed when ciLow < -domain
5. Right cap suppressed when ciHigh > +domain
6. Whisker positions clamp to domain edges when CI exceeds domain
7. Whisker only renders if BOTH props provided (only ciLow)
8. Whisker only renders if BOTH props provided (only ciHigh)
9. Does not affect existing aria-label or value bar (regression guard)

## Verification Results

- `npm test -- MiniBulletChart`: 9/9 passed
- `npm test --run` (full suite): 220/220 passed (no regressions)
- `npm run lint`: passed (no warnings)
- `npm run knip`: passed
- `npx tsc --noEmit`: 0 errors
- Existing call sites (EndgameScoreGapSection, EndgameWDLChart, EndgamePerformanceSection): verified no ciLow/ciHigh passed, backward compat confirmed

## Visual Verification

Visual quality at extreme domain edges (open-ended whisker rendering) is in Plan 06 manual verification per VALIDATION.md.

## Deviations from Plan

None. Plan executed exactly as written.

## Known Stubs

None. This is a purely presentational primitive change with no data wiring.

## Threat Flags

None. Pure presentational component — no I/O, no auth surface, no new network endpoints.

## Self-Check: PASSED

- `frontend/src/components/charts/MiniBulletChart.tsx`: FOUND
- `frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx`: FOUND
- Commit `52df5cb` (RED): FOUND
- Commit `e265421` (GREEN): FOUND
