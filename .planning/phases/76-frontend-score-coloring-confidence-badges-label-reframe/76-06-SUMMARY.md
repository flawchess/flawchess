---
phase: 76-frontend-score-coloring-confidence-badges-label-reframe
plan: 06
subsystem: ui
tags: [react, typescript, insights, opening-insights, tailwind, vitest]

# Dependency graph
requires:
  - phase: 76-04
    provides: "OpeningInsightFinding TS type updated: win_rate/loss_rate removed, confidence/p_value added"
  - phase: 75-backend-score-metric-confidence-annotation
    provides: "score/confidence/p_value fields on OpeningInsightFinding API response"
provides:
  - "OpeningFindingCard renders score-based prose 'You score X% as <Color> after <san>'"
  - "Confidence indicator line with level-specific tooltip on both mobile and desktop branches"
  - "UNRELIABLE_OPACITY applied to card when n_games < 10 OR confidence === 'low'"
  - ".toFixed(1) fallback for edge case where rounded percent contradicts section title"
affects:
  - "76-07 through 76-08 (same phase, later plans that extend OpeningInsightsBlock/MoveExplorer)"
  - "future plans reading OpeningFindingCard test patterns"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dual mobile/desktop branch rendering — same data-testid appears twice; tests use getAllByTestId or card.textContent"
    - "CONFIDENCE_TOOLTIP as Record<Literal, string> satisfies noUncheckedIndexedAccess without narrowing"
    - "UNRELIABLE_OPACITY spread into cardStyle via conditional spread pattern"

key-files:
  created: []
  modified:
    - "frontend/src/components/insights/OpeningFindingCard.tsx"
    - "frontend/src/components/insights/OpeningFindingCard.test.tsx"

key-decisions:
  - "Tests use textContent and getAllByTestId rather than getByText/toBeInTheDocument (no jest-dom in test setup)"
  - "CONFIDENCE_TOOLTIP defined as module-level const outside component (no re-render allocation)"
  - "scoreDisplay edge-case uses wouldContradict guard to call .toFixed(1) when rounded % contradicts section classification"

patterns-established:
  - "Card confidence line: Tooltip wraps a <p> with data-testid — no separate icon trigger"
  - "Mute via cardStyle spread: ...(isUnreliable ? { opacity: UNRELIABLE_OPACITY } : {}) merged with borderLeftColor"

requirements-completed: [INSIGHT-UI-05, INSIGHT-UI-07]

# Metrics
duration: 15min
completed: 2026-04-28
---

# Phase 76 Plan 06: OpeningFindingCard Prose Migration + Confidence Indicator Summary

**Score-based "You score X%" prose replacing broken win_rate/loss_rate reads, plus Confidence line with level-specific tooltip and UNRELIABLE_OPACITY mute in both mobile and desktop branches**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-28T16:30:00Z
- **Completed:** 2026-04-28T16:39:24Z
- **Tasks:** 2 (TDD: RED commit + GREEN commit)
- **Files modified:** 2

## Accomplishments

- Repaired broken card component: replaced `finding.loss_rate` / `finding.win_rate` reads (removed by Phase 75) with `finding.score * 100` (D-02)
- Added "Confidence: low/medium/high" line with level-specific hover tooltip in both mobile and desktop layout branches (D-09/D-10, D-25 parity)
- Applied UNRELIABLE_OPACITY (0.5) to card when `n_games < 10` OR `confidence === 'low'` (D-11)
- Added edge-case guard: score = 0.499 with weakness classification falls back to "49.9%" instead of misleading "50%" (Claude's Discretion from CONTEXT.md)
- Full TDD cycle: RED (8 failing tests) then GREEN (19 passing tests)

## Task Commits

1. **RED — Failing tests for new behavior** - `fb6dafb` (test)
2. **GREEN — Implementation + updated tests** - `5d82b9f` (feat)

## Files Created/Modified

- `frontend/src/components/insights/OpeningFindingCard.tsx` - Migrated prose to score-based form; added CONFIDENCE_TOOLTIP map, confidenceLine JSX, mute logic with UNRELIABLE_OPACITY
- `frontend/src/components/insights/OpeningFindingCard.test.tsx` - Rewrote makeFinding fixture (dropped win_rate/loss_rate, added confidence/p_value); rewrote prose tests; added Phase 76 confidence + mute describe block (5 new tests)

## Decisions Made

- Used `getAllByTestId` instead of `getByText` in tests because both mobile and desktop branches render identical elements; `getByText` throws "Found multiple elements"
- `CONFIDENCE_TOOLTIP` is defined as a module-level constant outside the component function to avoid per-render re-allocation
- Tests use `card.textContent` pattern (consistent with pre-existing tests in the file) rather than `toBeInTheDocument` (which requires `@testing-library/jest-dom`, not installed)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test approach adapted for dual mobile/desktop rendering without jest-dom**

- **Found during:** Task 2 (test update — GREEN phase)
- **Issue:** Plan's test templates used `getByText(/You score/)` and `.toBeInTheDocument()`. Both fail because: (a) both mobile and desktop branches render the same text, causing "Found multiple elements"; (b) `@testing-library/jest-dom` is not installed, so `toBeInTheDocument` doesn't exist
- **Fix:** Used `card.textContent.toMatch(...)` pattern (consistent with existing tests in the file) and `getAllByTestId` for confidence line assertions
- **Files modified:** `frontend/src/components/insights/OpeningFindingCard.test.tsx`
- **Verification:** All 19 tests pass with `npx vitest run`
- **Committed in:** `5d82b9f` (GREEN commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — Bug)
**Impact on plan:** Required adapting test assertions to match the test environment setup. No behavioral changes to the component. No scope creep.

## Issues Encountered

Frontend `node_modules` not present in the worktree — ran `npm install` in the worktree before running tests. This is expected for git worktree setup.

## Known Stubs

None. The component now reads live data from `finding.score`, `finding.confidence`, and `finding.n_games` — all fields supplied by the Phase 75 backend API.

## Threat Flags

None. The CONFIDENCE_TOOLTIP Record is a hardcoded string map over a Pydantic Literal type. No user input flows into tooltip content. Consistent with T-76-06-01 (mitigated).

## Self-Check

Files exist:
- `frontend/src/components/insights/OpeningFindingCard.tsx` — FOUND
- `frontend/src/components/insights/OpeningFindingCard.test.tsx` — FOUND

Commits exist:
- `fb6dafb` (test RED) — FOUND
- `5d82b9f` (feat GREEN) — FOUND

## Self-Check: PASSED

## Next Phase Readiness

- OpeningFindingCard is fully repaired and delivers INSIGHT-UI-05 confidence indicator
- INSIGHT-UI-07 mobile parity satisfied: confidenceLine renders in both `sm:hidden` mobile branch and `hidden sm:flex` desktop branch
- Remaining Phase 76 plans (07, 08) can proceed: OpeningInsightsBlock InfoPopover icons and MoveExplorer Conf column

---
*Phase: 76-frontend-score-coloring-confidence-badges-label-reframe*
*Completed: 2026-04-28*
