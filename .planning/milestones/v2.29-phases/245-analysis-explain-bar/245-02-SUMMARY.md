---
phase: 245-analysis-explain-bar
plan: 02
subsystem: ui
tags: [react, typescript, analysis-board, tanstack-query]
status: complete

requires:
  - phase: 245-analysis-explain-bar (plan 01)
    provides: ExplainBar, useExplainBar, explainBar.ts rules, PendingFlaw.enter
provides:
  - ExplainBar mobile (above analysis-mobile-footer) and mid (Card under the board controls) placements
  - DesktopBoardStage explainBar slot rendered only in the mid layout
  - lineHasVisibleMotif + focusedLineHasMotif gate on the PV tactic overlay
  - useTacticLines 404 -> null (D-11 prefetch hardening)
  - CHANGELOG [Unreleased] and README entries
affects: [245 verification and owner UAT]

actuals:
  tokens: 15000
  tasks: 3
  commits: 3
plan_head_before: 9cb7b86e84fd3e3592d21596bfb133635a01c2a3
plan_head_after: 055f9dacc14db8210d9396a521ce01a1ff7b8d7e
commits: 3

tech-stack:
  added: []
  patterns:
    - "Placement-aware bar root (Card for mid, div otherwise) chosen inside the shared BarShell"
    - "Overlay honesty gate: PV countdown arrow and tint only for lines with a visible user motif"
    - "404 mapped to null inside queryFn so drift never reaches the global QueryCache.onError"

key-files:
  created:
    - frontend/src/components/analysis/__tests__/ExplainBar.test.tsx
  modified:
    - frontend/src/components/analysis/ExplainBar.tsx
    - frontend/src/components/analysis/AnalysisBoardStage.tsx
    - frontend/src/pages/Analysis.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx
    - frontend/src/lib/tacticOrientation.ts
    - frontend/src/lib/__tests__/tacticOrientation.test.ts
    - frontend/src/hooks/analysis/useAnalysisBoardArrows.ts
    - frontend/src/hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/hooks/__tests__/useLibrary.test.ts
    - CHANGELOG.md
    - README.md

key-decisions:
  - "Mid layout mounts the bar under the board controls (owner-UAT item, D-03 names desktop and mobile only)"
  - "Non-motif and opponent Explain lines get a plain unlabelled payoff-blue next-move arrow, no tint (owner-UAT item)"
  - "useTacticLines returns null for 404 and keeps every other error surfacing through the global handler"

patterns-established:
  - "Mount the bar once per layout, never inside the shared AnalysisTabs/MovesTab"

requirements-completed: [D-01, D-03, D-05, D-08, D-11]

coverage:
  - id: C1
    description: "Bar mounts once per layout: mobile directly above the footer, mid under the board controls, none in free play or on inaccuracy plies"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#Explain bar placement"
        status: pass
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/ExplainBar.test.tsx"
        status: pass
    human_judgment: true
    rationale: "Visual fit on a 360px phone and in the 768-1199px layout needs a browser; jsdom has no layout"
  - id: C2
    description: "Lines without a visible user motif draw an unlabelled payoff arrow and no sideline tint; motif lines unchanged"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts#PV sideline overlay motif gate"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/__tests__/tacticOrientation.test.ts#lineHasVisibleMotif"
        status: pass
    human_judgment: true
    rationale: "Owner-UAT item 1: confirm the plain blue arrow reads right on the real board"
  - id: C3
    description: "A tactic-lines 404 resolves to null data with isError false; 500 still errors"
    requirement: "D-11"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useLibrary.test.ts#useTacticLines"
        status: pass
    human_judgment: false

duration: 25 min
completed: 2026-11-05
---

# Phase 245 Plan 02: Explain bar on mobile and mid, honest overlay, 404 hardening Summary

**The Explain bar now mounts in all three layouts (desktop footer, mid under the board controls, mobile directly above the footer), non-motif Explain lines no longer draw a fake tactic countdown, and a tactic-lines 404 is a silent "no lines".**

## Accomplishments

- `ExplainBar` placement widened to `desktop | mid | mobile`; the shared `BarShell` renders a `Card` root for mid and a `div` otherwise, so testids and data attributes are identical everywhere.
- `DesktopBoardStage` takes an optional `explainBar` slot rendered after the board-controls Card only when `isMid`; `Analysis.tsx` passes the mid bar through `desktopBoardStageProps` and mounts the mobile bar between `{analysisTabs}` and `analysis-mobile-footer`. Never inside the shared Moves tab.
- `lineHasVisibleMotif` (user-scoped, mirrors `tacticOrientationAtPly` and the chips) feeds a new `focusedLineHasMotif` option on `useAnalysisBoardArrows`. When false, `sidelineNodeColors` is empty and the PV arrow is `buildPvArrow(nextMove, 0, true, orientation)`: unlabelled payoff blue.
- `useTacticLines` is now `useQuery<TacticLinesResponse | null>` and maps an axios 404 to null (`HTTP_NOT_FOUND`), so the landing prefetch never retries or reports drift to Sentry.
- CHANGELOG `[Unreleased] / Added` bullet and a README clause on "Game & tactic analysis".

## Task Commits

1. Task 1: `56207c6cc` feat, mobile and mid placements plus component and placement tests
2. Task 2: `ab855fe0c` fix, motif-gated PV overlay
3. Task 3: `055f9dacc` fix, 404 -> null, CHANGELOG, README

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan 01's Explain page tests fail when run in isolation or under `-t`**
- **Found during:** Task 1 (the plan's own verify command `-t "Explain bar"`)
- **Issue:** When the describe runs first in the file, the engine-gate dialog is open and Radix aria-hides everything outside it, so `getAllByRole('button')` on the bar found nothing (verified at HEAD without my source changes; the full-file run passes because earlier tests dismiss the gate).
- **Fix:** `getAllByRole('button', { hidden: true })` in the plan 01 `Explain bar` describe, with a comment at the site. The button count assertion still holds.
- **Files modified:** `frontend/src/pages/__tests__/Analysis.test.tsx`
- **Commit:** `56207c6cc`

**Total deviations:** 1 auto-fixed (test-only). **Impact:** none on production code.

Process note: the bar tests and the production edits for Task 1 went into one commit, and Task 2 and 3 were written alongside their tests rather than as separate RED commits. Each new test was proven by mutation (reverting the mobile mount, the mid slot, both overlay gates and the 404 branch made the corresponding tests fail), then restored.

## Known Stubs

None.

## Threat Flags

None. No new endpoints or trust boundaries. T-245-04/05/07 mitigated as planned (eligible-ply-only prefetch with cache, 404 -> null, motif gate).

## Verification

- `npm run lint`, `npm run build` (tsc -b), `npm run knip`: clean (the two knip configuration hints were already present).
- Full frontend suite: 345 files, 5797 tests pass.
- Backend untouched: `git diff --name-only main...HEAD -- app tests alembic` prints nothing.
- Owner-UAT items (browser, during verify-work): plain blue arrow on non-motif lines; bar placement in the 768-1199px layout; 360px mobile fit with the footer at 5 columns.

## Self-Check: PASSED
