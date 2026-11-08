---
phase: 245-analysis-explain-bar
reviewed: 2026-11-05T11:10:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - frontend/src/lib/explainBar.ts
  - frontend/src/hooks/analysis/useExplainBar.ts
  - frontend/src/components/analysis/ExplainBar.tsx
  - frontend/src/components/analysis/AnalysisDesktopCards.tsx
  - frontend/src/components/analysis/AnalysisBoardStage.tsx
  - frontend/src/hooks/analysis/useAnalysisBoardArrows.ts
  - frontend/src/hooks/analysis/useAnalysisRouteSeeding.ts
  - frontend/src/hooks/useLibrary.ts
  - frontend/src/lib/analysisTactics.ts
  - frontend/src/lib/analytics.ts
  - frontend/src/lib/tacticOrientation.ts
  - frontend/src/pages/Analysis.tsx
  - frontend/src/components/analysis/__tests__/ExplainBar.test.tsx
  - frontend/src/hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts
  - frontend/src/hooks/analysis/__tests__/useExplainBar.test.ts
  - frontend/src/hooks/__tests__/useLibrary.test.ts
  - frontend/src/lib/__tests__/explainBar.test.ts
  - frontend/src/lib/__tests__/tacticOrientation.test.ts
  - frontend/src/pages/__tests__/Analysis.test.tsx
  - CHANGELOG.md
  - README.md
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 245: Code Review Report

**Reviewed:** 2026-11-05T11:10:00Z
**Depth:** standard
**Files Reviewed:** 20

## Summary

Reviewed the Explain bar: the pure rule module, the hook, the presentational component, the graft-effect `enter` flag, the 404-to-null change in `useTacticLines`, the no-motif overlay guard, the `currentMainlinePly` fix and the placement wiring. I confirmed the following.

- `tsc -b` is clean.
- ESLint is clean on the touched source files.
- The five new or changed unit-test files pass (67 tests).
- The graft ordering holds. `insertPvLine` and `goToNode` are chained functional updaters, so the new root node exists in the chained `prev` when `goToNode` runs.
- The `mainLine` index convention is consistent. `mainLine[p]` is the node after move `p`, so `MIN_MISSED_FORK_PLY = 1` is right.
- Decisions D-01 to D-11 are honored.

No security issues or crashes found. The two warnings are interaction and robustness gaps, not data loss.

## Warnings

### WR-01: An open adjacent-ply line makes a neighbouring flaw's Explain unreachable

**File:** `frontend/src/lib/explainBar.ts:120-123`
**Issue:** The got-it rule (1b) runs before the eligibility rule (3). A missed line for ply P forks at mainLine[P-1], so while it is open (D-07 deliberately keeps lines open) and the board sits on mainLine[P-1], the bar shows Got it for P. If P-1 is itself a mistake or blunder, that is the opponent's flaw whenever P is the user's, and consecutive flaws are common. Then P-1's own Explain is unreachable. The user must press Got it, which deletes P's line and jumps to P, and then press Back. The same happens whenever a chip-opened missed line for P is open and the user lands on P-1 by any route (move-list click, Jump, eval-chart scrub). The code comment calls this an "accepted precedence edge", but nothing in the locked decisions accepts it. It also contradicts D-03 ("shown when the current node is an eligible flaw ply"). The headline "Better than <SAN of P>" is also shown on a board that has not yet played that move.
**Fix:** When the got-it match comes only from fork equality (the board is on a main-line node, not inside the line's subtree) and that node is itself an eligible flaw ply that is not the line's own flaw ply, prefer the Explain state for the landing ply. `focusedFlaw` alone cannot tell the two cases apart, so the pure rule also needs a "board is inside the subtree" signal.
```ts
// resolveExplainBarState, before returning got-it:
const landingMarker = eligibleExplainMarker(flawMarkers, landingPly);
const onForkOnly = landingPly >= 0 && landingPly !== openLine.ply; // main-line node, not inside the subtree
if (openLine !== null && !(onForkOnly && landingMarker !== null)) { /* got-it */ }
```
Alternatively, document it in the UI-SPEC as owner-accepted. At minimum add a test that pins the chosen behaviour.

### WR-02: Mapping 404 to null removes the chip error signal and leaves `pendingFlaw` stuck, which hides the Explain bar on every other ply

**File:** `frontend/src/hooks/useLibrary.ts:307-322`, `frontend/src/lib/explainBar.ts:125`
**Issue:** `useTacticLines` is shared with the page's `fetchFlaw` query, which feeds `pvFetchError` (Analysis.tsx:517, 2208, 2356). Before this change a 404 for a chip-opened ply set `isError`, so the chip showed an error. Now it resolves to `null`, so there is no error and no spinner, and the chip click does nothing. The graft effect early-returns on `contextualTacticData == null` and never clears `pendingFlaw`. That was already true for errors, but rule (2) of the new bar now turns a stuck `pendingFlaw` for ply A into `hidden` on every other ply (`pendingFlaw.ply !== landingPly`). The only clearing paths are Reset and a successful graft. A single drifted or ungraftable chip click, or a deep-link `initialTactic` whose PV is empty or has no fork, therefore silently kills the Explain bar for the rest of the session.
**Fix:** Clear the pending flaw when the fetch settles with no graftable data. For example, in the graft effect (or `useExplainBar`), call `setPendingFlaw(null)` when `contextualTacticData === null`, or when the PV is empty or the fork is missing. Alternatively, have rule (2) ignore a `pendingFlaw` that is not fetching:
```ts
// useAnalysisRouteSeeding graft effect
if (pendingFlaw != null && contextualTacticData === null) { setPendingFlaw(null); return; }
```
Also keep `pvFetchError` truthy for the chip case, for example by exposing `data === null` as a "no lines" error state to VariationTree.

## Info

### IN-01: A cached 404 (`null`) hides Explain for 5 minutes even after `game_flaws` rows appear

**File:** `frontend/src/hooks/useLibrary.ts:320-326`
**Issue:** `flaw_markers` are computed live from evals while `game_flaws` rows are written at classify time, which the new comment itself acknowledges. A `null` result is cached under the same key with `staleTime` of 5 minutes and `refetchOnWindowFocus: false`. If a user lands on a flaw ply of a freshly analyzed game (live polling) before the rows exist, Explain stays hidden on that ply until the entry goes stale, with no manual refresh path.
**Fix:** Use a shorter `staleTime` for the null case. For example, `refetchOnMount: 'always'` for null results, or `retry`-free invalidation when `useLibraryGame` live polling observes completion. Alternatively, accept the limitation and note it in the phase summary.

### IN-02: The mobile ExplainBar is mounted unconditionally while the hook's landing prefetch also fires during Jump animation

**File:** `frontend/src/hooks/analysis/useExplainBar.ts:82-83`
**Issue:** The prefetch gate is `isGameMode && eligiblePly !== null` and ignores `fastForwardRunning`, even though the bar is hidden while a Jump runs. Each flaw ply the cursor lands on during a run, and every flaw crossed while scrubbing the eval chart, fires a tactic-lines GET whose result is not shown. This is performance only (out of v1 scope) and has no correctness impact, so it is listed for awareness.
**Fix:** Pass `enabled = isGameMode && eligiblePly !== null && !fastForwardRunning`.

---

_Reviewed: 2026-11-05T11:10:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
