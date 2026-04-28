---
phase: 76-frontend-score-coloring-confidence-badges-label-reframe
plan: 04
subsystem: ui
tags: [typescript, types, opening-insights, move-explorer, react]

# Dependency graph
requires:
  - phase: 76-02
    provides: "NextMoveEntry backend schema with score/confidence/p_value fields"
  - phase: 75-backend-score-metric-confidence-annotation
    provides: "OpeningInsightFinding backend schema with confidence/p_value, removal of loss_rate/win_rate"
provides:
  - "OpeningInsightFinding TS interface aligned with Phase 75 backend contract (confidence, p_value; no loss_rate/win_rate)"
  - "NextMoveEntry TS interface extended with score/confidence/p_value mirroring Plan 02 backend schema"
affects:
  - 76-05 (MoveExplorer.tsx reads NextMoveEntry.score and NextMoveEntry.confidence)
  - 76-06 (OpeningFindingCard.tsx reads OpeningInsightFinding.confidence and .p_value)
  - 76-07 (OpeningInsightsBlock.tsx unchanged, but type correctness depends on this plan)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hand-mirrored TS interfaces track Python Pydantic schemas; must be updated when backend schema changes"

key-files:
  created: []
  modified:
    - frontend/src/types/insights.ts
    - frontend/src/types/api.ts

key-decisions:
  - "OpeningInsightFinding: removed loss_rate and win_rate (dropped Phase 75 D-09), added confidence and p_value"
  - "NextMoveEntry: appended score/confidence/p_value; all existing fields preserved unchanged"
  - "tsc --noEmit errors at OpeningFindingCard.tsx:26 and MoveExplorer.tsx:228 are expected and left for Wave 4 plans 05/06 to fix"

patterns-established: []

requirements-completed: [INSIGHT-UI-05, INSIGHT-UI-03]

# Metrics
duration: 8min
completed: 2026-04-28
---

# Phase 76 Plan 04: Frontend Type Catch-Up for score/confidence/p_value Summary

**TS interfaces for OpeningInsightFinding and NextMoveEntry brought in sync with Phase 75 and Plan 02 backend schemas, adding confidence/p_value and removing stale loss_rate/win_rate**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-28T14:22:00Z
- **Completed:** 2026-04-28T14:30:04Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Updated `OpeningInsightFinding` TS interface: removed `loss_rate` and `win_rate` fields (both dropped by Phase 75 backend D-09), added `confidence: 'low' | 'medium' | 'high'` and `p_value: number`
- Extended `NextMoveEntry` TS interface: appended `score: number`, `confidence: 'low' | 'medium' | 'high'`, and `p_value: number` to mirror Plan 02's backend schema extension
- Frontend ESLint passes with no issues; tsc errors at consumer sites are expected and scoped to Wave 4

## Task Commits

Each task was committed atomically:

1. **Task 1: Update OpeningInsightFinding TS interface** - `44cf36e` (feat)
2. **Task 2: Extend NextMoveEntry TS interface** - `d68d72a` (feat)

**Plan metadata:** (see below)

## Files Created/Modified
- `frontend/src/types/insights.ts` - `OpeningInsightFinding` interface: removed `win_rate`/`loss_rate`, added `confidence`/`p_value`
- `frontend/src/types/api.ts` - `NextMoveEntry` interface: appended `score`, `confidence`, `p_value`

## Decisions Made
None beyond plan spec. Both edits were mechanical field additions/removals exactly as specified.

## Deviations from Plan

None - plan executed exactly as written.

The plan correctly predicted that `tsc --noEmit --project tsconfig.app.json` would surface errors at:
- `src/components/insights/OpeningFindingCard.tsx:26` — accesses `finding.loss_rate` / `finding.win_rate` (both now removed)
- `src/components/move-explorer/MoveExplorer.tsx:228` — `getArrowColor` call with 4 args after Plan 03 changed signature to 3 args
- `src/pages/Openings.tsx:407` — same `getArrowColor` call-site issue

All three will be resolved by Wave 4 plans (05 and 06). Frontend ESLint passes cleanly. The root `tsconfig.json` with `"files": []` and composite references means `npx tsc --noEmit` exits 0 (uses incremental build info); the errors appear when using `--project tsconfig.app.json` explicitly.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Wave 4 type files are ready: Plans 05/06/07 can now read `NextMoveEntry.score`, `NextMoveEntry.confidence`, `OpeningInsightFinding.confidence`, and `OpeningInsightFinding.p_value` from the type system
- Consumer sites `OpeningFindingCard.tsx` and `MoveExplorer.tsx` still reference removed/changed fields and will not compile until Plans 05 and 06 fix them

## Known Stubs
None. Pure type definition changes; no UI rendering logic in this plan.

## Self-Check

Files exist:
- `frontend/src/types/insights.ts` - FOUND
- `frontend/src/types/api.ts` - FOUND

Commits exist:
- `44cf36e` - FOUND (Task 1: OpeningInsightFinding update)
- `d68d72a` - FOUND (Task 2: NextMoveEntry extension)

## Self-Check: PASSED

---
*Phase: 76-frontend-score-coloring-confidence-badges-label-reframe*
*Completed: 2026-04-28*
