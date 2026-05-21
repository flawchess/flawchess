---
phase: 91-two-lane-import-defer-stockfish-eval-to-in-process-cold-drai
plan: "07"
subsystem: frontend
tags:
  - frontend
  - popover
  - eval-caveat
  - tanstack-query

dependency_graph:
  requires:
    - "91-06 (useEvalCoverage hook + EvalCoverageHeader)"
  provides:
    - "Per-metric pending caveat in EvalConfidenceTooltip body"
    - "Per-metric pending caveat in MetricStatTooltip body"
    - "isPending/pendingCount prop threading through BulletConfidencePopover + MetricStatPopover"
    - "useEvalCoverage callsites in all 7 Cpu-bearing consumer components"
  affects:
    - "frontend/src/components/insights/EvalConfidenceTooltip.tsx"
    - "frontend/src/components/popovers/MetricStatTooltip.tsx"
    - "frontend/src/components/popovers/MetricStatPopover.tsx"
    - "frontend/src/components/insights/BulletConfidencePopover.tsx"
    - "frontend/src/components/charts/PositionResultsPanel.tsx"
    - "frontend/src/components/insights/OpeningFindingCard.tsx"
    - "frontend/src/components/charts/EndgameOverallEntryCard.tsx"
    - "frontend/src/components/charts/EndgameOverallPerformanceSection.tsx"
    - "frontend/src/components/charts/EndgameMetricCard.tsx"
    - "frontend/src/components/charts/EndgameTypeCard.tsx"
    - "frontend/src/components/stats/OpeningStatsCard.tsx"

tech_stack:
  added: []
  patterns:
    - "isPending/pendingCount optional props with backwards-compatible defaults (false/0)"
    - "Conditional <p> removed from DOM (not just hidden) when isPending=false or pendingCount=0"
    - "vi.mock('@/hooks/useEvalCoverage') in component tests to avoid QueryClientProvider requirement"
    - "TanStack Query deduplication: all 7 consumers share queryKey ['imports', 'eval-coverage']"

key_files:
  created:
    - frontend/src/components/insights/__tests__/EvalConfidenceTooltip.test.tsx
    - frontend/src/components/popovers/__tests__/MetricStatTooltip.caveat.test.tsx
  modified:
    - frontend/src/components/insights/EvalConfidenceTooltip.tsx
    - frontend/src/components/popovers/MetricStatTooltip.tsx
    - frontend/src/components/popovers/MetricStatPopover.tsx
    - frontend/src/components/insights/BulletConfidencePopover.tsx
    - frontend/src/components/charts/PositionResultsPanel.tsx
    - frontend/src/components/insights/OpeningFindingCard.tsx
    - frontend/src/components/charts/EndgameOverallEntryCard.tsx
    - frontend/src/components/charts/EndgameOverallPerformanceSection.tsx
    - frontend/src/components/charts/EndgameMetricCard.tsx
    - frontend/src/components/charts/EndgameTypeCard.tsx
    - frontend/src/components/stats/OpeningStatsCard.tsx
    - frontend/src/components/charts/__tests__/EndgameMetricCard.test.tsx
    - frontend/src/components/charts/__tests__/EndgameMetricsSection.test.tsx
    - frontend/src/components/charts/__tests__/EndgameOverallPerformanceSection.test.tsx
    - frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx
    - frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx
    - frontend/src/components/insights/OpeningFindingCard.test.tsx
    - frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx
    - frontend/src/__tests__/noEndgameSkillString.test.tsx

decisions:
  - "Tasks 7.1 and 7.2 merged into one commit: separating them produced an unlintable intermediate state (unused isPending/pendingCount vars in function bodies)"
  - "MetricStatPopover.tsx needs only a comment mentioning isPending since props are inherited via extends MetricStatTooltipProps and passed via {...tooltipProps} spread"
  - "EndgameTypeCard receives isPending/pendingCount on both MetricStatPopover instances (Score + Score Gap rows) — both depend on Stockfish eval"
  - "D-07 honored: EndgameTimePressureCard explicitly excluded (imports Swords not Cpu; Clock Gap is not Stockfish-dependent)"

metrics:
  duration: "14 minutes"
  completed: "2026-05-21"
  tasks: 3
  files: 19
---

# Phase 91 Plan 07: Per-Metric Pending Caveat Injection Summary

Injected the Stockfish-pending caveat into both tooltip body components and threaded `isPending`/`pendingCount` through all 7 Cpu-bearing consumer components via the shared `useEvalCoverage()` hook.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 7.1 + 7.2 | Props + caveat injection + RTL tests | a29dc32e | EvalConfidenceTooltip.tsx, MetricStatTooltip.tsx, BulletConfidencePopover.tsx, MetricStatPopover.tsx, 2 test files |
| 7.3 | Thread useEvalCoverage through 7 consumer components | 03b2977a | 7 component files, 7 test files updated with vi.mock |
| 7.3 fix | Add useEvalCoverage mock to noEndgameSkillString integration test | 2e566421 | noEndgameSkillString.test.tsx |

## What Was Built

### Tooltip Body Changes

- `EvalConfidenceTooltip.tsx`: Added `isPending?: boolean` and `pendingCount?: number` to `EvalConfidenceTooltipProps`. Conditional `<p className="opacity-70">` injected after the methodology footer, rendered only when `isPending === true && pendingCount > 0`. Caveat is removed from DOM (not just hidden) when conditions not met.

- `MetricStatTooltip.tsx`: Same props and conditional `<p>` after `<p className="opacity-70 italic">{methodology}</p>`.

- Caveat copy (verbatim, D-06 locked): `"Based on currently-evaluated games. {N} more being analysed — refresh in a few minutes for updated values."` Single em-dash, `toLocaleString()` for comma-separated thousands.

### Popover Wrapper Changes

- `BulletConfidencePopover.tsx`: Added `isPending?` and `pendingCount?` to interface; forwarded explicitly to `<EvalConfidenceTooltip>`.

- `MetricStatPopover.tsx`: No code change needed — `MetricStatPopoverProps extends MetricStatTooltipProps` inherits the new optional fields; `{...tooltipProps}` spread forwards them to `<MetricStatTooltip>`. Added JSDoc comment to document the inheritance.

### Consumer Components (7 files)

All 7 Cpu-bearing components now call `const { isPending, pendingCount } = useEvalCoverage()` and pass the values to their popover children:

| Component | Popover Type | Instances |
|---|---|---|
| PositionResultsPanel | BulletConfidencePopover | 1 |
| OpeningFindingCard | BulletConfidencePopover | 1 |
| EndgameOverallEntryCard | MetricStatPopover | 2 (Endgame Entry Eval + Achievable Score) |
| EndgameOverallPerformanceSection | MetricStatPopover | 2 (Achievable Score Gap + Endgame Score Gap) |
| EndgameMetricCard | MetricStatPopover | 1 (Score Gap) |
| EndgameTypeCard | MetricStatPopover | 2 (Endgame Score + Score Gap) |
| OpeningStatsCard | BulletConfidencePopover | 1 |

Total: 10 popover instances receiving `isPending`/`pendingCount` props.

`EndgameTimePressureCard` was confirmed NOT modified (imports `Swords` not `Cpu`; Clock Gap is not Stockfish-dependent per RESEARCH OQ-1).

### Tests

RTL tests for caveat behavior:

| File | Tests | Coverage |
|---|---|---|
| `EvalConfidenceTooltip.test.tsx` | 4 | shown when pending, absent when not pending, absent when zero count, absent by default |
| `MetricStatTooltip.caveat.test.tsx` | 4 | same three-way coverage |

Component tests updated with `vi.mock('@/hooks/useEvalCoverage')` to suppress `QueryClientProvider` requirement in 8 test files:
- 7 existing component tests (EndgameMetricCard, EndgameMetricsSection, EndgameOverallPerformanceSection, EndgameTypeBreakdownSection, EndgameTypeCard, OpeningFindingCard, OpeningStatsCard)
- 1 integration test (noEndgameSkillString)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Tasks 7.1 and 7.2 could not be committed separately**
- **Found during:** Task 7.1 prop plumbing
- **Issue:** Adding `isPending`/`pendingCount` to function signature without using them triggered `@typescript-eslint/no-unused-vars` errors. The plan's TDD approach (Task 7.1 = props only, Task 7.2 = render) creates an unlintable intermediate state. Underscore prefixes (`_isPending`) also failed the linter.
- **Fix:** Merged Tasks 7.1 and 7.2 into a single commit (wrote tests first for RED phase, then implemented props + caveat together for GREEN phase).
- **Files modified:** EvalConfidenceTooltip.tsx, MetricStatTooltip.tsx
- **Commit:** a29dc32e

**2. [Rule 1 - Bug] 8 component/integration tests broke after adding useEvalCoverage calls**
- **Found during:** Task 7.3 verification
- **Issue:** Components rendered in tests now call `useEvalCoverage()` which internally calls `useQuery`. Without a `QueryClientProvider` wrapper, React throws "No QueryClient set". Same pattern as the Plan 91-06 Rule 1 fix for `Endgames.overallPerformance.test.tsx`.
- **Fix:** Added `vi.mock('@/hooks/useEvalCoverage', () => ({ useEvalCoverage: () => ({ isPending: false, ... }) }))` to all affected test files. The `noEndgameSkillString.test.tsx` fix was committed separately (03b2977a) from the main Task 7.3 commit.
- **Files modified:** 8 test files across charts, insights, stats, and root `__tests__` directories
- **Commits:** 03b2977a (7 files), 2e566421 (1 file)

## useEvalCoverage Callsite Count

- 7 new `useEvalCoverage()` callsites added to consumer components
- All share `queryKey: ['imports', 'eval-coverage']` — TanStack Query deduplicates to 1 HTTP call per page per polling interval regardless of N popovers on the page

## Popover Instance Count

- 5 `BulletConfidencePopover` instances in 3 components → forward to `EvalConfidenceTooltip`
- 5 `MetricStatPopover` instances in 4 components (direct props via extends + spread)
- Total: 10 popover instances now receive `isPending`/`pendingCount`

## Known Stubs

None. All data is wired through the real `useEvalCoverage` hook, which in turn queries the real `GET /imports/eval-coverage` backend endpoint (implemented in Plan 91-01).

## Threat Flags

None. Prop drilling within the React component tree is a trusted boundary. The caveat copy renders `pendingCount.toLocaleString()` on an integer — no XSS surface.

## Self-Check: PASSED

- `frontend/src/components/insights/__tests__/EvalConfidenceTooltip.test.tsx`: FOUND
- `frontend/src/components/popovers/__tests__/MetricStatTooltip.caveat.test.tsx`: FOUND
- `grep -c "isPending" frontend/src/components/insights/EvalConfidenceTooltip.tsx` returns 3 (interface + destructure + conditional)
- `grep -c "isPending" frontend/src/components/popovers/MetricStatTooltip.tsx` returns 3
- `grep -c "isPending" frontend/src/components/popovers/MetricStatPopover.tsx` returns 1 (comment)
- `grep -c "isPending" frontend/src/components/insights/BulletConfidencePopover.tsx` returns 3
- `grep -c "Based on currently-evaluated games" EvalConfidenceTooltip.tsx` returns 1
- `grep -c "Based on currently-evaluated games" MetricStatTooltip.tsx` returns 1
- `grep -c "useEvalCoverage" EndgameTimePressureCard.tsx` returns 0
- All 7 consumer files have `useEvalCoverage` import + call (2 grep matches each)
- Commits a29dc32e, 03b2977a, 2e566421 all present in git log
- `npm run lint`: exits 0
- `npm run build`: exits 0
- `npm test -- --run`: 601 tests, 53 files — all pass
- `npm run knip`: clean
