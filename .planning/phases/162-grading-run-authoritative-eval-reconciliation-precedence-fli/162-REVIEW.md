---
phase: 162-grading-run-authoritative-eval-reconciliation-precedence-fli
reviewed: 2026-07-10T11:04:56Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - frontend/src/hooks/__tests__/useGameOverlay.test.ts
  - frontend/src/lib/engineEvalLookup.test.ts
  - frontend/src/lib/engineEvalLookup.ts
  - frontend/src/pages/Analysis.tsx
  - frontend/src/pages/__tests__/Analysis.test.tsx
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 162: Code Review Report

**Reviewed:** 2026-07-10T11:04:56Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

Reviewed the grading-first precedence flip in `buildEvalLookup`, the new `resolveReconciledBest` argmax, and the threading of `reconciledBestUci` / `reconciledBestEval` / `reconciledStockfishLine` / `reconciledPvLines` through Analysis.tsx's display consumers, plus the three test files. Verification performed as part of the review: all 43 tests in the three changed test files pass, `npx tsc -b` is clean, and eslint reports no issues on the five files.

The core precedence flip is correct and well-tested: gradeMap entries are inserted first, free-run entries fill gaps only (`!lookup.has(uci)`), and the argmax compares like-for-like grading values because `candidateUcis` is restricted to `grading.gradeMap`'s keyspace (Pitfall 3 honored). The tie-break logic in `resolveReconciledBest` handles both orderings of the tieBreak candidate correctly. Lifecycle edge cases I traced and found sound: gradeMap is cleared when `gradingEnabled` flips false (fen prop → null triggers the `fenChanged` clear, so no stale-grade argmax persists with Maia/FC off), `engine.pvLines` is cleared when `engineEnabled` flips false (so `freeRunCommitted` cannot latch stale PVs), and the array-identity churn of `unionSans` during free-run streaming is absorbed by the grading hook's `candidatesKey` string memo. Mobile/desktop parity for `reconciledPvLines` is respected (both `EngineLines` call sites updated).

Two warnings: a transient window in the Maia-off/FC-on configuration where the "reconciled argmax" is computed over a candidate set that cannot contain Stockfish's actual best move, letting the agreement verdict transiently mislabel or falsely align; and the Maia chart's emphasis stroke still keyed to the raw free-run `bestSan`, contradicting the reconciled Best designation on the same chart in exactly the mirror-image scenario this phase fixed.

## Warnings

### WR-01: Verdict/arrow/eval-bar can transiently present a non-Stockfish-best move as "Stockfish's pick" when Maia is off (candidate set excludes the free-run best)

**File:** `frontend/src/pages/Analysis.tsx:864-894` (also `809-820`, `1406`, `2000`)
**Issue:** `reconciledBestUci` is an argmax over `grading.gradeMap`'s keyspace only. With Maia **on**, the union always contains the free run's live `bestSan` (via `selectCandidatesByMass`'s union), so the true Stockfish pick is always a graded candidate. With Maia **off** and FlawChess **on**, the grading union is FC's top-3 SANs only until `freeRunCommitted` becomes true (~1.5s free-run movetime) *and* the grading run re-runs on the widened union (debounce + up to 4000ms `GRADING_MOVETIME_SAFETY_CAP_MS`). In that multi-second window per navigation, grading results land for the FC-only candidate set, `reconciledBestUci` becomes non-null, and:
- `reconciledStockfishLine` names the best *FC candidate* as Stockfish's objective #1 in `FlawChessAgreementVerdict` — the verdict can claim **aligned** ("they agree") when the real `engine.pvLines[0]` (already streaming) is a different move. Pre-162, `stockfishLine={engine.pvLines[0]}` got the move identity right as soon as the PV streamed, so this is a regression in that configuration, distinct from the accepted D-12 edge case (argmax outside the card's top-2 among *fully covered* candidates).
- The green SF board arrow (line 1406) and the eval bar (`reconciledBestEval`) follow the same possibly-wrong move.

**Fix:** Treat the argmax as unresolved while the free run's committed best is not yet a graded candidate, e.g.:
```tsx
// In the reconciledBestUci memo, after computing candidateUcis:
const freeRunBestUci = freeRunCommitted ? (engine.pvLines[0]?.moves[0] ?? null) : null;
if (freeRunBestUci !== null && !candidateUcis.includes(freeRunBestUci)) {
  // Grading hasn't covered the free run's own best yet — the argmax would be
  // computed over a candidate set that cannot contain the true SF pick.
  return null; // callers fall back to raw engine.pvLines[0] (existing first-paint path)
}
```
This keeps depth parity (never mixes the free-run eval into the argmax) and reuses the existing null fallbacks at every consumer.

### WR-02: Maia chart emphasis stroke still keyed to the raw free-run `bestSan`, contradicting the reconciled Best on the same chart

**File:** `frontend/src/pages/Analysis.tsx:2038, 2306` (consumer: `frontend/src/components/analysis/MovesByRatingChart.tsx:576`)
**Issue:** `MovesByRatingChart` receives `bestSan={bestSan}` (raw free-run pick) and draws the *emphasized* (thick) stroke on `san === bestSan`, while the same chart's quality color/label/verdict-prose "Best" is now the reconciled argmax (`designatedBestSan` inside `qualityBySan`). In the exact mirror-image scenario this phase's own test pins (free-run best `e4` at +0.2, reconciled best `Nf3` at +3.0), the chart renders a thick "SF-best-emphasized" line for `e4` while `Nf3` carries the best-quality color and the position verdict names `Nf3` as the accurate move — two different moves getting "best" treatments on one surface. The phase goal was threading the *single* canonical reconciled-best into all display consumers (labels included); this consumer was missed. Note `bestSan` must keep feeding `selectCandidatesByMass` (raw pick must stay plotted), so only the chart's emphasis prop should change.
**Fix:** Hoist the reconciled SAN (already computed inside the `qualityBySan` memo as `designatedBestSan`) into its own memo and pass it to both chart call sites:
```tsx
const reconciledBestSan = useMemo(
  () => (reconciledBestUci !== null ? bestSanFromPv(position, reconciledBestUci) : null),
  [reconciledBestUci, position],
);
// ...
<MovesByRatingChart bestSan={reconciledBestSan ?? bestSan} ... />
```
Apply to both the desktop and mobile call sites (CLAUDE.md mobile-parity rule).

## Info

### IN-01: Tie-break comment claims "standalone Stockfish pick" but `bestSan` falls back to the FlawChess pick when the engine is off

**File:** `frontend/src/pages/Analysis.tsx:860-870`
**Issue:** The `reconciledBestUci` comment says ties prefer "the standalone Stockfish pick", but `bestSan` (line 750) falls back to `flawChessEngine.rankedLines[0]?.rootMove` when `engineEnabled` is false — so with the engine off, ties in the chart's Best designation resolve toward the FC practical pick instead. Behavior is arguably fine; the comment is inaccurate for that configuration.
**Fix:** Either derive `tieBreakUci` from `engineEnabled ? engine.pvLines[0]?.moves[0] ?? null : null` directly (skipping the SAN round-trip through `bestSanFromPv`/`sanToUci`), or amend the comment to note the FC fallback.

### IN-02: Redundant defensive copy in `reconciledPvLines`

**File:** `frontend/src/pages/Analysis.tsx:943`
**Issue:** `[...withReconciledEval].sort(...)` copies an array that `.map()` already returned fresh on line 938 — the spread protects nothing.
**Fix:** `return withReconciledEval.sort(...)`.

### IN-03: Stockfish card lines can swap order repeatedly mid-search

**File:** `frontend/src/pages/Analysis.tsx:936-947`
**Issue:** `reconciledPvLines` re-sorts on every free-run info tick. A graded root holds a static grading eval while an ungraded root's free-run eval streams, so the two rows can flip-flop across the crossover during the ~1.5s search — badge colors and click targets swap under the cursor. Pre-162 the order was pinned by multipv. Inherent to D-04's re-sort; worth a UAT look, and if it flickers in practice, sort only once `!engine.isAnalyzing`.
**Fix:** Optional: `engine.isAnalyzing ? withReconciledEval : withReconciledEval.sort(...)` (evals still reconciled mid-search, order stabilized at commit).

### IN-04: `resolveReconciledBest` tests cover only white-mover cp evals

**File:** `frontend/src/lib/engineEvalLookup.test.ts:108-166`
**Issue:** All five `resolveReconciledBest` tests use `mover: 'white'` and pure-cp grades. A sign regression (e.g. dropping the `mover` pass-through into `evalToExpectedScore`) or a mate-handling regression (`evalMate` candidate vs cp candidate) would pass the suite green. Also minor: the "not-yet-graded" test (line 42) is named for the free-run-only direction but its primary fixture is an overlap pair; the non-overlap assertion is bolted on via a second lookup inside the same `it`.
**Fix:** Add a black-mover case (lowest white-POV cp must win) and a mate-vs-cp case (`#3` beats `+5.0` for the mover); optionally split the dual-assertion test into two `it`s.

---

_Reviewed: 2026-07-10T11:04:56Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
