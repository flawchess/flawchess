---
phase: 71-frontend-stats-subtab-openinginsightsblock
plan: "05"
subsystem: frontend
tags: [react, typescript, component, opening-insights, tdd, stats-subtab]
dependency_graph:
  requires:
    - frontend/src/hooks/useOpeningInsights.ts (plan 03)
    - frontend/src/lib/openingInsights.ts (plan 03 — INSIGHT_THRESHOLD_COPY)
    - frontend/src/types/insights.ts (plan 03)
    - frontend/src/components/insights/OpeningFindingCard.tsx (plan 04, stub present)
  provides:
    - frontend/src/components/insights/OpeningInsightsBlock.tsx (OpeningInsightsBlock)
  affects:
    - Plan 06 (wires OpeningInsightsBlock into Openings.tsx)
tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN cycle with vitest + @testing-library/react
    - Four-state ternary chain (loading, error, empty, populated)
    - Parallel worktree stub pattern (OpeningFindingCard stub for Plan 04)
key_files:
  created:
    - frontend/src/components/insights/OpeningInsightsBlock.tsx
    - frontend/src/components/insights/OpeningInsightsBlock.test.tsx
    - frontend/src/components/insights/OpeningFindingCard.tsx (stub for Plan 04)
  modified: []
decisions:
  - "Used reduce to compute per-section start indices (globally unique card idx) instead of mutable counter inside render, to satisfy react-hooks/immutability lint rule"
  - "afterEach cleanup() required in vitest 4 — DOM does not auto-cleanup between tests, matching EndgameInsightsBlock.test.tsx pattern"
  - "OpeningFindingCard stub created for parallel Plan 04 execution; stub is minimal but functional (click delegation works)"
metrics:
  duration: "~6 minutes"
  completed: "2026-04-27"
  tasks_completed: 2
  files_created: 3
  files_modified: 0
---

# Phase 71 Plan 05: OpeningInsightsBlock Component Summary

`OpeningInsightsBlock` outer Stats-subtab component — charcoal-texture card with four-state rendering (loading skeleton, error, empty block, populated sections), composing `OpeningFindingCard` lists for four categories (white/black weaknesses, white/black strengths).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Write failing tests for OpeningInsightsBlock | 8a59885 | OpeningInsightsBlock.test.tsx, OpeningFindingCard.tsx (stub) |
| 2 (GREEN) | Implement OpeningInsightsBlock component | a8e45ea | OpeningInsightsBlock.tsx, OpeningInsightsBlock.test.tsx |
| 2 (fix) | Fix unused TS parameter to pass build | 9a25af4 | OpeningInsightsBlock.tsx |

## What Was Built

### OpeningInsightsBlock (`frontend/src/components/insights/OpeningInsightsBlock.tsx`)

Outer block component with:

- Outer wrapper: `<div data-testid="opening-insights-block" className="charcoal-texture rounded-md p-4">`
- Heading: `<h2>` "Opening Insights" with `<Lightbulb>` icon + `<InfoPopover testId="opening-insights-info">` (D-20)
- InfoPopover content: `INSIGHT_THRESHOLD_COPY` plus color-filter-scope sentence
- Loading: `animate-pulse` skeleton with 4 section placeholders + 2 card placeholders each (D-11)
- Error: `role="alert"` block with fixed copy + `Try again` button (`variant="brand-outline"`) calling `query.refetch()` (D-12); no Sentry per CLAUDE.md
- All-empty: single muted message referencing the threshold (D-10)
- Populated: 4 sections in fixed order (white-weaknesses, black-weaknesses, white-strengths, black-strengths) (D-01)
- Per-section header: `<h3>` with AlertTriangle/Star icon + piece-color swatch + section title
- Per-section empty: muted "No {weakness|strength} findings cleared the threshold..." (D-09)
- Card stack: `<div className="space-y-3">` with `OpeningFindingCard` per finding
- All D-21 data-testids locked: `opening-insights-block`, `opening-insights-section-{key}`

### OpeningFindingCard stub

Minimal functional stub created to unblock Plan 05 compilation while Plan 04 runs in parallel. Renders `data-testid="opening-finding-card-{idx}"` and correctly delegates `onClick` to `onFindingClick` prop. Will be replaced by the full Plan 04 implementation at wave merge.

### Tests (`frontend/src/components/insights/OpeningInsightsBlock.test.tsx`)

7 test cases:
1. Renders skeleton while loading (animate-pulse present)
2. Renders error state with `role=alert` and retry button
3. Renders empty-block message when all four sections empty
4. Renders four sections when at least one has findings
5. Renders per-section empty message when only some sections have findings
6. Delegates card click to `onFindingClick` prop
7. Shows InfoPopover on the heading

## Deviations from Plan

### [Rule 1 - Bug] Added afterEach cleanup() to test file

- **Found during:** Task 1 / first test run (GREEN phase)
- **Issue:** Vitest 4 does not auto-cleanup RTL mounts. DOM from previous tests bled into subsequent tests causing "Found multiple elements by testid" failures.
- **Fix:** Added `afterEach(() => { cleanup(); })` import and call — matching the pattern in `EndgameInsightsBlock.test.tsx`.
- **Files modified:** `OpeningInsightsBlock.test.tsx`
- **Commit:** a8e45ea

### [Rule 1 - Bug] Fixed TypeScript TS6133 unused variable in reduce

- **Found during:** Task 2 build verification (`npm run build`)
- **Issue:** `section` param in `sectionStartIdxs.reduce((acc, section, i) => ...)` was unused (only `i` and `acc` used). TypeScript strict mode raised TS6133.
- **Fix:** Renamed to `_section` to signal intentional non-use — standard TS/ESLint convention.
- **Files modified:** `OpeningInsightsBlock.tsx`
- **Commit:** 9a25af4

### [Rule 1 - Bug] Refactored mutable cardIdx to pure reduce-based indices

- **Found during:** Task 2 lint check
- **Issue:** Original plan had `let cardIdx = 0; cardIdx += 1` inside render function — triggered `react-hooks/immutability` lint error ("Reassigning cardIdx after render has completed can cause inconsistent behavior on subsequent renders").
- **Fix:** Pre-computed per-section start indices using `reduce` before the JSX return. Each section's cards use `startIdx + i` for the globally unique idx.
- **Files modified:** `OpeningInsightsBlock.tsx`
- **Commit:** a8e45ea

## TDD Gate Compliance

- RED gate: `test(71-05)` commit 8a59885 — tests failed with import error (component not yet created)
- GREEN gate: `feat(71-05)` commit a8e45ea — all 7 tests pass

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| OpeningFindingCard | `frontend/src/components/insights/OpeningFindingCard.tsx` | Minimal compilation stub for Plan 04 (running in parallel). Renders `data-testid` and click handler correctly. Full implementation from Plan 04 will replace at wave merge. |

The stub does not prevent the plan's goal (block component + tests) from being achieved. Plan 06 integration requires the full Plan 04 implementation.

## Knip Note

`OpeningInsightsBlock` export is consumed only by the stub test file (imported in `OpeningInsightsBlock.test.tsx`). Plan 06 will import it from `Openings.tsx`, eliminating the knip pending status. Knip currently passes (exit 0) because the test file imports it.

## Threat Flags

None — no new network endpoints (hook was created in Plan 03), no auth paths, no file access, no schema changes.

## Self-Check

### Files exist:

- [x] `frontend/src/components/insights/OpeningInsightsBlock.tsx` — named export `OpeningInsightsBlock`
- [x] `frontend/src/components/insights/OpeningInsightsBlock.test.tsx` — 7 test cases
- [x] `frontend/src/components/insights/OpeningFindingCard.tsx` — stub export

### data-testids present:

- [x] `opening-insights-block` (outer card)
- [x] `opening-insights-section-${section.key}` (4 sections)
- [x] `btn-opening-insights-retry` (error state)
- [x] `opening-insights-info` (InfoPopover)

### Commits exist:

- [x] 8a59885 — test(71-05): add failing tests for OpeningInsightsBlock (TDD red)
- [x] a8e45ea — feat(71-05): implement OpeningInsightsBlock component (TDD green)
- [x] 9a25af4 — fix(71-05): rename unused reduce param to _section to fix TS6133 build error

### Verification:

- [x] All 134 frontend tests pass (7 new ones included)
- [x] `npm run lint` passes (0 errors, 3 warnings in unrelated coverage files)
- [x] `npm run build` passes
- [x] `npm run knip` passes (exit 0)

## Self-Check: PASSED
