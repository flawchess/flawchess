---
phase: 245-analysis-explain-bar
plan: 01
subsystem: ui
tags: [react, typescript, analysis-board, tanstack-query, umami]
status: complete

requires:
  - phase: 244-analysis-board
    provides: tactic-chip line machinery (openLines, pendingFlaw, graft effect, useTacticLines)
provides:
  - Pure Explain bar rules (eligibility, usable lines, orientation, hidden/explain/got-it state)
  - useExplainBar hook (D-11 prefetch observer, onExplain, onGotIt)
  - ExplainBar presentational component mounted as the desktop MovesCard footer
  - PendingFlaw.enter flag consumed by the graft effect (Explain lands on the first grafted move)
  - findFocusedFlaw relocated to lib/analysisTactics.ts
affects: [245-02 mobile and mid mounts, 404-to-null mapping in useTacticLines]

actuals:
  tokens: 13240
  tasks: 3
  commits: 4
plan_head_before: 39fb40b236af82ce2a3005d523ffafa5c0cda2a8
plan_head_after: 91a492871a79713eb03a34f57b7021c585e29387
commits: 4

tech-stack:
  added: []
  patterns:
    - "Bar state is a pure ordered-early-return resolver called from useMemo (React Compiler lint, max-depth)"
    - "Second useTacticLines observer with the shared query key for prefetch, so the click is a cache hit"
    - "Test harness mirrors the page wiring with the real board, seeding hook and findFocusedFlaw"

key-files:
  created:
    - frontend/src/lib/explainBar.ts
    - frontend/src/lib/__tests__/explainBar.test.ts
    - frontend/src/hooks/analysis/useExplainBar.ts
    - frontend/src/hooks/analysis/__tests__/useExplainBar.test.ts
    - frontend/src/components/analysis/ExplainBar.tsx
  modified:
    - frontend/src/lib/analysisTactics.ts
    - frontend/src/lib/analytics.ts
    - frontend/src/hooks/analysis/useAnalysisRouteSeeding.ts
    - frontend/src/components/analysis/AnalysisDesktopCards.tsx
    - frontend/src/pages/Analysis.tsx
    - frontend/src/pages/__tests__/Analysis.test.tsx

key-decisions:
  - "Explain sets pendingFlaw with enter: true and does not navigate to the fork first, so the graft lands on the first move in one commit"
  - "Got it state is driven by the page's existing focusedFlaw memo, never a second containment walk"
  - "Umami targets explain-open / explain-close ride the existing board-tool verb"
  - "currentMainlinePly now uses mainLine.indexOf directly (stale stateRef bug fix)"

patterns-established:
  - "Bar shell shared by Explain and Got it so the swap never shifts row height"

requirements-completed: [D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-10, D-11]

coverage:
  - id: C1
    description: "Explain on a mistake or blunder (either side) grafts the stored line and lands on its first move (missed_moves[0] / allowed_moves[1])"
    requirement: "D-05"
    verification:
      - kind: integration
        ref: "frontend/src/hooks/analysis/__tests__/useExplainBar.test.ts#D-05 missed / D-05 allowed"
        status: pass
      - kind: integration
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#Explain bar"
        status: pass
    human_judgment: false
  - id: C2
    description: "Direction rule, fallback and hide rules (D-04, D-08, D-09, D-10, D-11)"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/explainBar.test.ts"
        status: pass
    human_judgment: false
  - id: C3
    description: "Got it closes the line and returns to the flaw move; leaving and re-entering never duplicates a sideline; chips unchanged"
    requirement: "D-06"
    verification:
      - kind: integration
        ref: "frontend/src/hooks/analysis/__tests__/useExplainBar.test.ts#D-06 / D-07"
        status: pass
    human_judgment: false
  - id: C4
    description: "Explain bar placement and look in the desktop 3-column layout (footer row under the move list)"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#Explain bar (DOM placement only; jsdom has no layout)"
        status: pass
    human_judgment: true
    rationale: "Visual fit, row height stability and dark-theme appearance need a browser; jsdom does no layout"

duration: 40 min
completed: 2026-11-05
---

# Phase 245 Plan 01: Analysis Explain Bar (desktop) Summary

**Contextual Explain bar on the desktop Analysis layout: one click on any mistake or blunder (either side) grafts the stored engine line and plays its first move, Back/Forward step through it, and Got it closes it and returns to the flaw move.**

## Accomplishments

- `lib/explainBar.ts`: pure rules. `eligibleExplainMarker` (M/B only, both sides), `usableExplainLines` (guards ply 0 missed, empty and length-1 allowed lines so a graft can never leave `pendingFlaw` stuck), `chooseExplainOrientation` (D-04 direction, D-09 fallback, D-10 null), and `resolveExplainBarState` with hidden / explain / got-it.
- `PendingFlaw.enter`: the graft effect calls `goToNode(rootNodeId)` right after `insertPvLine` when the flag is set, so Explain lands on the first grafted move in one commit; chips and the deep-link auto-open omit it and still park at the fork.
- `useExplainBar`: a second `useTacticLines` observer on the landing ply (same query key, so the click is a cache hit and the bar stays hidden until the data resolves), `onExplain` (re-enters an already-open line of the same key instead of grafting a duplicate) and `onGotIt` (deleteSubtree, drop the openLines key, return to `mainLine[ply]`).
- `ExplainBar` component (single button, static copy, shared shell for both states) mounted through a new `MovesCard` `footer` slot; `explain-open` / `explain-close` registered as `board-tool` targets, sent only from the click handlers.
- `findFocusedFlaw` moved to `lib/analysisTactics.ts` so the integration harness uses the page's exact focus rule.

## Task Commits

1. Task 1 (tracer): `00bccf966` feat, end-to-end Explain on the desktop layout
2. Task 2 RED: `b8a0db09d` test, Got it unit and page tests (5 failing as expected)
3. Task 2 GREEN: `cdee9d2e5` feat, Got it state and handler plus the `currentMainlinePly` fix
4. Task 3: `91a492871` test, real-board harness (8 cases) and the `findFocusedFlaw` relocation

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `currentMainlinePly` cached -1 on a deep link to the last ply**
- **Found during:** Task 2 (page test for the opponent mistake at `ply=3`, the last ply of the fixture game)
- **Issue:** the memo gated on `isOnMainLine(currentNodeId)`, which reads the board's `stateRef`. That ref is synced after render, so on the commit where `loadMainLine` lands it still held the empty tree; the memo cached -1 and, with the cursor already on the target node, never recomputed. The bar (and every other `currentMainlinePly` reader) saw "off the main line".
- **Fix:** `mainLine.indexOf(currentNodeId)` on the render's own `mainLine` (same semantics, -1 when absent), with a comment at the fix site.
- **Files modified:** `frontend/src/pages/Analysis.tsx`
- **Verification:** the full frontend suite (344 files, 5770 tests) passes.
- **Commit:** `cdee9d2e5`

**Total deviations:** 1 auto-fixed (1 bug). **Impact:** small, strictly more correct; no other reader of `currentMainlinePly` regressed.

The RED commit `b8a0db09d` does not pass `tsc` (the test inputs name fields the GREEN commit adds); this is inherent to a test-first commit and was resolved by the next commit.

## Known Stubs

None.

## Threat Flags

None. No new endpoints or trust boundaries; SAN is rendered as React text, event payloads are enumerated literals only.

## Verification

- `explainBar.test.ts`, `useExplainBar.test.ts`, `Analysis.test.tsx`, `analytics.test.ts`, `useAnalysisBoard.test.ts`: pass.
- Full frontend suite: 344 files, 5770 tests pass.
- `npm run lint`, `npm run build` (tsc -b) and `npm run knip`: clean (two knip configuration hints were already present).
- Backend untouched: `git diff --name-only main...HEAD -- app tests alembic` prints nothing.

## Next

Ready for 245-02 (mobile and mid-width mounts, 404 mapped to null in `useTacticLines`, motif gate for non-motif lines).

## Self-Check: PASSED
