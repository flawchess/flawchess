---
phase: 76-frontend-score-coloring-confidence-badges-label-reframe
plan: 07
subsystem: ui
tags: [react, typescript, vitest, info-popover, opening-insights]

# Dependency graph
requires:
  - phase: 76-03
    provides: OpeningFindingCard confidence field support (D-21 type update)
  - phase: 76-04
    provides: InfoPopover component already available in info-popover.tsx
provides:
  - Four InfoPopover triggers (one per section header) in OpeningInsightsBlock
  - OPENING_INSIGHTS_POPOVER_COPY shared constant (D-17 score+effect+confidence framing)
  - Updated test fixture removing stale win_rate/loss_rate fields
affects: [76-VALIDATION]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Co-locate JSX ReactNode constants with their consuming component to avoid renaming .ts to .tsx

key-files:
  created: []
  modified:
    - frontend/src/components/insights/OpeningInsightsBlock.tsx
    - frontend/src/components/insights/OpeningInsightsBlock.test.tsx

key-decisions:
  - "D-17: OPENING_INSIGHTS_POPOVER_COPY lives as a local constant in OpeningInsightsBlock.tsx (not in openingInsights.ts), keeping openingInsights.ts as a pure .ts module per RESEARCH.md Open Question 3"
  - "D-18: No block-level Opening Insights h2 title added (consistency with other Stats tabs)"
  - "Test fix: toHaveAttribute not available (no @testing-library/jest-dom) — replaced with .getAttribute() + .toContain() native Vitest assertions"

patterns-established:
  - "InfoPopover in section h3: <h3 flex items-center gap-1.5><swatch/>{title}<InfoPopover ariaLabel testId side=bottom>{copy}</InfoPopover></h3>"

requirements-completed: [INSIGHT-UI-06, INSIGHT-UI-07]

# Metrics
duration: 8min
completed: 2026-04-28
---

# Phase 76 Plan 07: OpeningInsightsBlock InfoPopover Section Triggers Summary

**Four InfoPopover icons added to OpeningInsightsBlock section headers sharing a single OPENING_INSIGHTS_POPOVER_COPY constant with score/effect-size/confidence framing copy (D-16, D-17)**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-28T14:29:00Z
- **Completed:** 2026-04-28T14:37:38Z
- **Tasks:** 2 (TDD: combined feat + test in one commit)
- **Files modified:** 2

## Accomplishments
- Added `OPENING_INSIGHTS_POPOVER_COPY` constant (ReactNode, three paragraphs) co-located in `OpeningInsightsBlock.tsx`
- Added `InfoPopover` trigger inside each of the four section `<h3>` headers with `side="bottom"`, unique `testId`, and `ariaLabel`
- Updated `makeFinding` fixture to drop stale `win_rate`/`loss_rate` fields and add `confidence`/`p_value` (aligning with D-21 type update from plan 76-03)
- Added three new Phase 76 tests: 4-trigger count, ARIA label verification, absence of block-level h2 title

## Task Commits

1. **Task 1+2: Add InfoPopover triggers + extend test** - `cbf1bd5` (feat)

## Files Created/Modified
- `frontend/src/components/insights/OpeningInsightsBlock.tsx` - Added `ReactNode` + `InfoPopover` imports, `OPENING_INSIGHTS_POPOVER_COPY` constant, InfoPopover inside each section h3
- `frontend/src/components/insights/OpeningInsightsBlock.test.tsx` - Fixed `makeFinding` fixture (drop win_rate/loss_rate, add confidence/p_value), added Phase 76 popover describe block with 3 tests

## Decisions Made
- Co-located `OPENING_INSIGHTS_POPOVER_COPY` in `OpeningInsightsBlock.tsx` rather than `openingInsights.ts` to avoid renaming that file from `.ts` to `.tsx` (RESEARCH.md Open Question 3).
- Used `getAttribute('aria-label')` + `.toContain()` instead of `toHaveAttribute()` because `@testing-library/jest-dom` is not installed in this project.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assertion adapted: toHaveAttribute not available**
- **Found during:** Task 2 (test execution)
- **Issue:** Plan template used `toHaveAttribute()` which requires `@testing-library/jest-dom`, not installed in this project
- **Fix:** Replaced with `.getAttribute('aria-label')` + `.toContain()` which uses native Vitest/chai assertions
- **Files modified:** `frontend/src/components/insights/OpeningInsightsBlock.test.tsx`
- **Verification:** All 10 tests pass with the adapted assertions
- **Committed in:** `cbf1bd5`

---

**Total deviations:** 1 auto-fixed (Rule 1 - assertion API adaptation)
**Impact on plan:** Trivial assertion style change; same semantic coverage. No scope creep.

## Issues Encountered
None beyond the `toHaveAttribute` API adaptation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- OpeningInsightsBlock section headers now each have an InfoPopover trigger satisfying INSIGHT-UI-06 and INSIGHT-UI-07
- The `makeFinding` fixture in `OpeningInsightsBlock.test.tsx` is now aligned with the Phase 75 API contract (no win_rate/loss_rate)
- Ready for validation pass

## Self-Check: PASSED

- `frontend/src/components/insights/OpeningInsightsBlock.tsx` - FOUND
- `frontend/src/components/insights/OpeningInsightsBlock.test.tsx` - FOUND
- Commit `cbf1bd5` - FOUND
- 10/10 tests pass
- Lint: 0 errors

---
*Phase: 76-frontend-score-coloring-confidence-badges-label-reframe*
*Completed: 2026-04-28*
