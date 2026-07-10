---
phase: 158-flawchess-engine-displayed-eval-provenance-reconciliation-se
reviewed: 2026-07-07T18:08:59Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - frontend/src/components/analysis/FlawChessEngineLines.tsx
  - frontend/src/hooks/__tests__/useStockfishGradingEngine.test.ts
  - frontend/src/hooks/useStockfishGradingEngine.ts
  - frontend/src/lib/engineEvalLookup.test.ts
  - frontend/src/lib/engineEvalLookup.ts
  - frontend/src/pages/Analysis.tsx
  - frontend/src/pages/__tests__/Analysis.test.tsx
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 158: Code Review Report

**Reviewed:** 2026-07-07T18:08:59Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Reviewed the Phase 158 eval-provenance reconciliation: the new `engineEvalLookup` module, the grading hook's movetime-4000 / `searchmoves`-last change, the `Analysis.tsx` wiring (union candidate set, `gradingEnabled` OR-gating, `reconciledRankedLines`, reconciled `qualityBySan`), the `MAX_LINES` export, and the three test files.

Verification performed: all 31 tests in the three phase test files pass, `tsc -b` is clean, eslint is clean on the four source files, and no debug artifacts (console.log/debugger/TODO) exist in the changed files. **Scope fence verified:** `git diff` over the phase range touches only the 7 listed files — `frontend/src/lib/engine/` (including `types.ts`/`RankedLine` and the MCTS core), `useFlawChessEngine.ts`, and `workerPool.ts` are untouched. The `searchmoves`-must-be-last fix and the free-run-first precedence in `buildEvalLookup` are correct as implemented, and the SC4 claim ("FC pick grades higher than SF best is impossible by construction") holds because `engine.pvLines[0]`'s eval is by definition the lookup's precedence source for that UCI.

Four warnings: a behavioral regression in the verdict's D-10 lookup (truncated from all ranked lines to top-2), a stale cross-position grade-commit window in the grading hook that Phase 158 amplifies, an unenforced candidate-union size assumption behind the measured movetime-4000 budget, and a non-neutral null/null fallback in `qualityBySan` that can paint phantom severity colors during transients.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Verdict's D-10 "SF pick also FC-ranked" lookup silently truncated from all ranks to top-2

**File:** `frontend/src/pages/Analysis.tsx:1605` (also `752-759`)
**Issue:** `FlawChessAgreementVerdict` previously received the full `flawChessEngine.rankedLines` for its `flawChessRankedLines` prop. The engine emits **every root candidate** (`buildRankedLines` in `treeCommon.ts` pushes all root children), and the verdict's D-10 lookup is explicitly documented as "was the Stockfish pick ALSO ranked by FlawChess (**any rank, not just #1**)?" (`FlawChessAgreementVerdict.tsx:206-209`). Phase 158 swapped the prop to `reconciledRankedLines`, which is `.slice(0, FC_MAX_LINES)` = top 2. When Stockfish's pick sits at FC rank 3+ — the *typical* divergence case this verdict exists to explain — `matchedFlawChessLineForSf` is now `null` and the SF-pick popover silently drops its "FlawChess: X (practical)" line. The swap bought nothing for this prop: the matched line only reads `practicalScore` (`StockfishPickPopoverBody`), which reconciliation does not touch — only `objectiveEvalCp` is reconciled.
**Fix:** Pass the full list for the D-10 lookup while keeping the reconciled list for display:
```tsx
<FlawChessAgreementVerdict
  flawChessLine={reconciledRankedLines[0] ?? null}
  stockfishLine={engine.pvLines[0] ?? null}
  // D-10 needs ANY rank; only practicalScore is read from the match, which
  // reconciliation never modifies — safe to pass the raw full list.
  flawChessRankedLines={flawChessEngine.rankedLines}
  ...
/>
```
(If the truncation was intentional, the D-10 comment in `FlawChessAgreementVerdict.tsx:107-109` and `:206` must be updated — as written, code and contract now contradict each other.)

### WR-02: Grading info-handler commits the PREVIOUS position's grades to the displayed map during rapid navigation

**File:** `frontend/src/hooks/useStockfishGradingEngine.ts:326-364` (interacts with `268-299`)
**Issue:** On a FEN change the debounce effect clears `gradeMap` (D-05: "the displayed gradeMap must never show the PREVIOUS position's colors"), but in the rapid-step case (`sinceLast <= RAPID_STEP_DEBOUNCE_MS`, e.g. held arrow-key navigation) no `stop` is sent until the 150ms timer fires and `prepareSearch` runs. During that window `stateRef` is still `'thinking'` and `stopPendingRef` is false, so info lines from the superseded search pass the stale-eval guard at line 328 and reach `commitDisplayedGradeMap(gradingFenRef.current /* OLD fen */, candidateSansRef.current /* NEW sans */)` at line 364 — repopulating the just-cleared displayed map with the old position's grades for any SAN legal in both positions (common: `Nf3`, `O-O`, recaptures). Phase 158 widens the blast radius: this stale map now flows through `evalLookup` into the FC card's `objectiveEvalCp`, the verdict, and `qualityBySan` — the exact provenance surfaces this phase reconciles. (The handler logic itself predates 158 — only constants and the go command changed — but this file is the phase's core and the invariant is stated in this file's own comments.)
**Fix:** Guard the display commit on FEN identity (keep the cache write — it is correctly keyed to the old FEN and stays useful):
```ts
cache.set(san, { ... });
// Only refresh the DISPLAYED map when the search's FEN is still the current
// position — during a rapid-step window the old search keeps streaming after
// the fen changed but before the deferred stop lands (D-05).
if (fenKey === currentFenRef.current) {
  commitDisplayedGradeMap(fenKey, candidateSansRef.current);
}
```

### WR-03: Measured movetime-4000 budget assumes 6-8 candidates, but the per-FEN search union grows without bound

**File:** `frontend/src/hooks/useStockfishGradingEngine.ts:230-241` (constant at `39-52`)
**Issue:** `GRADING_MOVETIME_SAFETY_CAP_MS = 4000` was calibrated (per its own doc comment) so that "the grading run's depth **for a candidate-union size of 6-8** reaches parity with the free run's depth". But `prepareSearch` unions every previously-cached SAN for the FEN with the new request (`allSans = [...cache.keys(), ...sans]`) and sets `MultiPV = candidateUcis.length` with no cap. A user dragging the ELO slider across its range on one position accumulates each rung's distinct 0.95-mass candidates into the union — MultiPV can reach 15-20, splitting the fixed 4000ms across far more lines than the calibration assumed. Depth then falls back below the free run's, re-introducing the cross-card eval-magnitude skew this phase was measured to eliminate (precedence still guarantees per-move *consistency*, but grading-only moves get materially shallower, lower-quality evals than the calibration promises). Nothing enforces the 6-8 assumption.
**Fix:** Cap the search union at a named constant near the calibrated size, preferring the currently-requested sans and dropping the oldest cached extras (their grades stay served from cache):
```ts
/** Calibration bound for GRADING_MOVETIME_SAFETY_CAP_MS (158-01-SUMMARY: depth parity measured at 6-8 lines). */
const GRADING_UNION_MAX = 8;
const allSans = Array.from(new Set([...sans, ...(cache?.keys() ?? [])])).slice(0, GRADING_UNION_MAX);
```

### WR-04: `qualityBySan`'s null/null fallback grade is not neutral — it classifies as a real 0.5 expected score

**File:** `frontend/src/pages/Analysis.tsx:769-790` (fallback at `774`)
**Issue:** For a SAN in `grading.gradeMap` whose `getBySan` resolution fails (only possible when the grade map is transiently stale relative to `position` — at steady state the SAN↔UCI round-trip at the same FEN always succeeds), the code inserts `{ evalCp: null, evalMate: null, depth: 0 }` into `reconciledGradeMap`. But `evalToExpectedScore(null, null, mover)` returns **0.5** (`liveFlaw.ts:64-65`), so `classifyMoveQuality` treats the unknown grade as a genuine even-position score: in a winning position (best ES ~0.9) the 0.4 drop labels the move **"blunder"**; if *all* SANs fail conversion (fully stale map right after navigation), they all score 0.5 and one gets labeled "best". Either way the chart lines / quality-bar segments briefly paint confident severity colors backed by no eval at all. Omitting the SAN would equally satisfy the "never the raw pool grade" constraint without inventing a score.
**Fix:** Skip unresolvable SANs instead of inserting a sentinel:
```ts
for (const san of grading.gradeMap.keys()) {
  const reconciled = getBySan(evalLookup, position, san);
  // A conversion failure means the grade map is stale for this position —
  // drop the SAN (uncolored) rather than classify a fabricated 0.5 ES.
  if (reconciled !== null) reconciledGradeMap.set(san, reconciled);
}
```

## Info

### IN-01: Stale POOL-04 comment and now-unnecessary toggle click in the engine-loading test

**File:** `frontend/src/pages/__tests__/Analysis.test.tsx:244-250`
**Issue:** The comment claims "the FlawChess Engine suppresses the standalone Stockfish search while it is enabled (POOL-04 mutual exclusion)" and the test clicks the FC toggle before asserting the Stockfish loading skeleton. The 155 UAT un-merge reversed that handoff: `engineLoading = engineEnabled && !engine.isReady` is FC-independent (Analysis.tsx:645), so the skeleton shows regardless and the click is dead weight. The test still passes, but the comment documents behavior that no longer exists — the next reader will draw wrong conclusions about the gating.
**Fix:** Delete the `fireEvent.click(...flawchess-toggle...)` line and rewrite the comment to reflect the un-merged (independent) Stockfish search.

### IN-02: `document.visibilityState` stub never restored — leaks `'hidden'` into any test added after it

**File:** `frontend/src/hooks/__tests__/useStockfishGradingEngine.test.ts:295-301`
**Issue:** The visibility test redefines `document.visibilityState` to `'hidden'` via `Object.defineProperty` and never restores it. vitest reuses one jsdom instance per file, so the override persists for the remainder of the file. It is currently the last test, but any test appended later runs with a hidden document — and the hook's bestmove handler silently skips its deferred re-go when `document.visibilityState === 'hidden'` (hook line 377), which would produce a confusing "go never re-sent" failure.
**Fix:** Restore in `afterEach`: `Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true, writable: true });` (or capture and reassign the original descriptor).

### IN-03: Two inaccurate invariant comments in FlawChessEngineLines

**File:** `frontend/src/components/analysis/FlawChessEngineLines.tsx:117-133`
**Issue:** (a) Line 130 claims "SHADES has MAX_LINES entries" — `FLAWCHESS_ENGINE_BADGE_SHADES` has 3 entries while `MAX_LINES` is 2 (harmless today since 3 ≥ 2, but the stated invariant is false and the `?? last-shade` narrowing is justified by the wrong reason). (b) Lines 118-120 claim expanded state resets because "a fresh search remounts the list" — rows are keyed by `key={lineIndex}` (line 276), which never changes across searches or positions, so a row's `expanded` state actually persists across board navigation. Neither is phase-158 code (the diff only exported `MAX_LINES`), but both comments describe invariants the code does not hold.
**Fix:** Correct both comments; if expand-reset on a new position is actually desired, key the rows by `${baseFen}-${lineIndex}` (or the line's `rootMove`).

---

_Reviewed: 2026-07-07T18:08:59Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
