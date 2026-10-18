---
phase: 242-openings-stats-insights-rework
plan: 08
subsystem: ui
tags: [react, react-router, typescript, vitest, knip]

requires:
  - phase: 242-openings-stats-insights-rework
    provides: "Findings section on the Stats tab (242-07), colour switch on Stats (242-05)"
provides:
  - "Three-tab Openings page (Moves, Games, Stats) on desktop and mobile"
  - "/openings/insights replace redirect to /openings/stats"
  - "Shared OpeningsTab union (types/openingsTab.ts)"
affects: [242-09, verify-work]

actuals:
  tokens: 9000
  tasks: 3
  commits: 3
plan_head_before: c4488db82b2e3339b2502158ee1602a5a6a6cfeb
plan_head_after: 93fd570c72db57c39e153eacec9067ef44ba099a

tech-stack:
  added: []
  patterns: ["One OpeningsTab union imported by the page, its hooks and the board layout helper"]

key-files:
  created:
    - frontend/src/types/openingsTab.ts
  modified:
    - frontend/src/pages/Openings.tsx
    - frontend/src/pages/__tests__/Openings.render.test.tsx
    - frontend/src/pages/__tests__/Openings.statsBoard.test.tsx
    - frontend/src/pages/openings/useDeepLinkHighlight.ts
    - frontend/src/pages/openings/useTabReset.ts
    - frontend/src/pages/openings/useOpeningsHandlers.ts
    - frontend/src/pages/openings/OpeningsMobileBoardPanel.tsx
    - frontend/src/lib/openingsBoardLayout.ts
  deleted:
    - frontend/src/pages/openings/InsightsTab.tsx
    - frontend/src/components/insights/OpeningInsightsBlock.tsx
    - frontend/src/components/insights/OpeningInsightsBlock.test.tsx
    - frontend/src/components/insights/OpeningFindingCard.tsx
    - frontend/src/components/insights/OpeningFindingCard.test.tsx

key-decisions:
  - "Reused the existing needsLegacyRedirect path for /insights instead of a new Route, so the redirect stays a single fixed-destination Navigate replace (T-242-18)"
  - "Mobile sticky row on Stats now always renders the colour switch (the Insights spacer branch is gone)"

patterns-established:
  - "Tab union lives in types/openingsTab.ts; getBoardContainerClassName takes OpeningsTab instead of string"

requirements-completed: [D-00, D-15]

coverage:
  - id: D1
    description: "Openings page shows Moves, Games, Stats only on desktop and mobile; Insights triggers, content and info popovers are gone"
    requirement: D-00
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Openings.render.test.tsx#renders the page shell and both tab strips (desktop + mobile)"
        status: pass
    human_judgment: false
  - id: D2
    description: "/openings/insights replace-redirects to /openings/stats and the Stats tab becomes active"
    requirement: D-15
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Openings.render.test.tsx#redirects the legacy /openings/insights URL to the Stats tab with a replace (D-15)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Finding-card deep links (Moves pulse highlight, Games) still work after the union change"
    requirement: D-15
    verification: []
    human_judgment: true
    rationale: "Pulse highlight and tab navigation from a finding card need a browser check; types and hooks compile and the existing page tests pass, but no test drives the click path"
  - id: D4
    description: "Old Insights tab, block and finding card deleted, knip clean"
    requirement: D-00
    verification:
      - kind: other
        ref: "npm run knip (exit 0), npm run lint, npm run build, npm test -- --run (5661 passed)"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-10-17
status: complete
---

# Phase 242 Plan 08: Remove the Insights subtab Summary

**Insights subtab, mobile tab and route removed with a replace redirect from /openings/insights to /openings/stats, one shared OpeningsTab union, and the old Insights tab/block/finding card deleted with knip clean**

## Performance

- **Duration:** 8 min
- **Started:** 2026-10-17T17:27:00Z
- **Completed:** 2026-10-17T17:35:00Z
- **Tasks:** 3
- **Files modified:** 8 modified, 1 created, 5 deleted

## Accomplishments
- /openings/insights now lands on /openings/stats through the existing legacy Navigate replace; the redirect test fails when the `/insights` match is removed (mutation-checked).
- Desktop and mobile tab strips show Moves, Games and Stats only. TAB_INFO.stats now describes the merged page (clearest opening moves for and against you, then bookmarked and most played openings with results, score and the engine evaluation after the opening).
- types/openingsTab.ts replaces six duplicated unions; the board stays hidden on lg for Stats only.
- Five dead files deleted; knip, lint, build and the full vitest suite (5661 tests) pass.

## Task Commits

1. **Task 1: Tracer, redirect and Insights subtab removal** - `b4cd7989b` (feat)
2. **Task 2: Shared OpeningsTab union** - `be7b1e597` (refactor)
3. **Task 3: Delete old Insights components** - `93fd570c7` (chore)

## Files Created/Modified
- `frontend/src/types/openingsTab.ts` - OpeningsTab union
- `frontend/src/pages/Openings.tsx` - three tabs, /insights redirect, Stats info text, removed hasOpenings and Insights tab element
- `frontend/src/pages/__tests__/Openings.render.test.tsx` - tab-strip assertions and /openings/insights redirect case (LocationProbe)
- `frontend/src/pages/__tests__/Openings.statsBoard.test.tsx` - dropped the Insights board-hidden case
- `frontend/src/pages/openings/useDeepLinkHighlight.ts`, `useTabReset.ts`, `useOpeningsHandlers.ts`, `OpeningsMobileBoardPanel.tsx`, `frontend/src/lib/openingsBoardLayout.ts` - use OpeningsTab

## Decisions Made
None beyond the plan; see key-decisions.

## Deviations from Plan

None - plan executed exactly as written. No file outside the plan's list needed editing for knip (it reported no unused files or exports; its two configuration hints are pre-existing and unrelated).

## Issues Encountered
None.

## Known Stubs
None.

## Follow-ups for /simplify (not edited here, per plan)

Comment-only mentions of the deleted components remain in files outside this plan:
- `frontend/src/index.css:303` (OpeningInsightsBlock -> MoveExplorer)
- `frontend/src/hooks/useReadiness.ts:42` (OpeningFindingCard.tsx)
- `frontend/src/lib/sanToSquares.ts:15, 44` (OpeningFindingCard)
- `frontend/src/components/stats/EvalCpuPlaceholder.tsx:6` (OpeningFindingCard)
- `frontend/src/components/insights/ScoreConfidenceTooltip.tsx:77` (OpeningFindingCard)
- `frontend/src/components/insights/__tests__/ScoreConfidenceTooltip.test.tsx:5` (OpeningFindingCard)
- `frontend/src/components/board/ChessBoard.tsx:30` (OpeningInsightsBlock -> MoveExplorer)

Uncalled branches knip cannot see: after 242-04, 242-06 and this plan, the opening-end branches of `components/insights/EvalConfidencePopover.tsx` and `EvalConfidenceTooltip.tsx` have no callers left. The `evalContext` prop is still used by Endgames with "endgame-entry". The follow-up removes those branches and narrows the prop.

## Threat Flags
None. T-242-18 is mitigated: the redirect destination is the fixed internal path /openings/stats.

## Next Phase Readiness
Browser UAT for /gsd-verify-work: /openings/insights lands on Stats with the findings on top, desktop and phone tab strips show Moves, Games, Stats only, and a finding card's Moves link still pulses the candidate move (D3, human_judgment).

---
*Phase: 242-openings-stats-insights-rework*
*Completed: 2026-10-17*

## Self-Check: PASSED
