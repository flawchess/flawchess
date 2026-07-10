---
phase: 163-gem-moves-maia-findability-move-badges-on-analysis-seed-092
reviewed: 2026-07-10T18:25:09Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - frontend/src/components/analysis/MaiaMoveQualityBar.tsx
  - frontend/src/components/analysis/MovesByRatingChart.tsx
  - frontend/src/components/analysis/UnifiedMovePopover.tsx
  - frontend/src/components/analysis/VariationTree.tsx
  - frontend/src/components/board/boardMarkers.tsx
  - frontend/src/components/board/__tests__/boardMarkers.test.tsx
  - frontend/src/components/icons/GemIcon.tsx
  - frontend/src/lib/gemGlyph.ts
  - frontend/src/lib/gemMove.ts
  - frontend/src/lib/moveQuality.ts
  - frontend/src/lib/__tests__/gemMove.test.ts
  - frontend/src/lib/__tests__/moveQuality.test.ts
  - frontend/src/pages/Analysis.tsx
  - frontend/src/pages/__tests__/Analysis.test.tsx
findings:
  critical: 0
  warning: 5
  info: 2
  total: 7
status: issues_found
---

# Phase 163: Code Review Report

**Reviewed:** 2026-07-10T18:25:09Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Reviewed the Phase 163 gem-move delta (detection library, glyph/icon primitives, board marker, chart/popover surfaces, and the Analysis.tsx wiring). Mechanical gates are clean: `npx tsc -b` passes, `eslint` on all 14 files passes, `npm run knip` is clean, and all 4 phase test files pass (74 tests). The pure library (`gemMove.ts`), glyph primitives, and VariationTree/popover surfaces are solid, with good boundary-condition test coverage and mobile/desktop parity (`resolveMarkerIcon` applied to `DesktopTree`, `MobileTree`, and `siblingBlockToChips`; both `MaiaHumanPanel` call sites receive `qualityBySanWithGem`).

The findings concentrate in the Analysis.tsx wiring, where the gem classifier is fed from asynchronously-updating hook state: (1) the current-position gem memo bypasses classifyGem's own `playedIsBest` defense; (2) `summarizeForGem` fabricates a 0.5 expected score for null grades, which both suppresses D-01 lost-position gems and enables spurious C2 passes; (3) the two new per-FEN caches can be poisoned for one commit on every navigation because the source hooks clear their state one render later than `position` changes; (4) the sticky `gemByNode` latch can permanently persist a gem derived from a partial (still-streaming) parent grading pass; (5) in game mode a backend severity badge and the live gem badge can be drawn on the same square corner.

No security-relevant surface is touched (no user input, no network, no secrets). No `text-xs` violations outside the sanctioned popover exception; theme colors come from `theme.ts` via `MAIA_ACCENT`; no magic numbers (all new geometry/threshold values are named constants).

## Warnings

### WR-01: `qualityBySanWithGem` hard-codes `playedIsBest: true`, bypassing classifyGem's C2 identity check

**File:** `frontend/src/pages/Analysis.tsx:1050-1055`
**Issue:** The current-position gem memo computes `bestEs`/`secondBestEs` via `summarizeForGem(qualityBySan, …)` but never verifies that the summarized argmax (`summary.bestSan`) is actually `reconciledBestSan` — it passes `playedIsBest: true` unconditionally. `classifyGem`'s documented C2 contract is "the played move IS the graded best AND beats the runner-up". Whenever the summarize argmax diverges from `reconciledBestSan` (tie-break divergence, or — concretely — a null/null grade reading as a phantom 0.5 argmax in a lost position, see WR-02), the memo evaluates the argmax pair's gap but recolors a *different* move (`reconciledBestSan`) violet. The parallel arrival-move path gets this right (`playedIsBest: summary?.bestSan === playedSanForGem`, line 1380); this path silently dropped the check.
**Fix:**
```ts
const { bestSan, bestEs, secondBestEs } = summarizeForGem(qualityBySan, sideToMoveFromFen(position));
const isGem = classifyGem({
  maiaProbability: maiaProb,
  playedIsBest: bestSan === reconciledBestSan,
  bestEs,
  secondBestEs,
});
```

### WR-02: `summarizeForGem` counts null/null grades as expected score 0.5 — fabricated data both suppresses and creates gems

**File:** `frontend/src/lib/gemMove.ts:60-82` (interacts with `frontend/src/pages/Analysis.tsx:1008-1015`)
**Issue:** `evalToExpectedScore(null, null, mover)` returns `0.5` (liveFlaw.ts:100), and `summarizeForGem` feeds every map entry through it without filtering ungraded entries. The `qualityBySan` memo *explicitly* produces `{ evalCp: null, evalMate: null }` entries for unresolved SANs ("an unresolved SAN maps to a null/null grade", Analysis.tsx:1006-1013), and the WR-03 navigation window produces whole maps of them. Consequences: (a) in a lost position (all real ES < 0.5) a phantom 0.5 entry becomes the argmax, so `summary.bestSan` is the phantom SAN and `playedIsBest` fails for the genuinely best try — directly undermining D-01 ("lost-position best-try still qualifies"); (b) in a winning position a phantom 0.5 can become `secondBestEs` and inflate the gap past `MISTAKE_DROP`, a spurious C2 pass (a false gem via WR-01's unconditional `playedIsBest`, or via the arrival path if the phantom happens to be the runner-up). The unit tests only exercise fully-graded maps, so this contract hole is untested.
**Fix:** Skip ungraded entries inside the reduction:
```ts
for (const [san, grade] of gradeBySan) {
  if (grade.evalCp === null && grade.evalMate === null) continue; // ungraded — no evidence
  const es = evalToExpectedScore(grade.evalCp, grade.evalMate, mover);
  ...
}
```

### WR-03: Per-FEN caches are poisoned for one commit on every navigation — `position` is paired with hook state that clears one render later

**File:** `frontend/src/pages/Analysis.tsx:1240-1253` and `frontend/src/pages/Analysis.tsx:1262-1283`
**Issue:** Both cache effects write `next.set(position, <hook output>)`. But `useMaiaEngine` clears `latestResult` (hence `perElo`) in a `useEffect` keyed on `fen` (useMaiaEngine.ts:197-213), and `useStockfishGradingEngine` clears `gradeMap` in its own effect (useStockfishGradingEngine.ts:269-276). So on the commit where `position` becomes the child, `maia.perElo` still holds the PARENT's curve and `grading.gradeMap` the parent's grades — and the Analysis effects, running in that same commit, write `childFen → parent data` into both caches. The entries self-heal once the child's own results land, but a rapid two-step navigation (parent → child → grandchild before the child's Maia inference completes, which can take seconds) makes `gemCandidate` classify the grandchild-arrival move against the parent's policy map keyed under the child's FEN. Usually the wrong-side SAN lookup returns `undefined → null` (silent gem suppression), but SAN strings can collide across the two positions (e.g. "Qe2"/"O-O" legal for either side in successive positions), yielding an arbitrary wrong probability that — via the one-way `gemByNode` latch (WR-05) — can persist a false gem badge permanently. The pre-existing `engineEvalByFen` shares this pattern, but that consumer (a scalar eval) degrades far more gracefully than a policy-map keyed by SAN.
**Fix:** Key the cache write on the FEN the data actually belongs to, not on `position`. `MaiaResult` already carries `msg.fen` internally (useMaiaEngine.ts:249) — expose it (e.g. `resultFen`) from both hooks and write `next.set(resultFen, data)`; alternatively, guard the write with `if (hookFen !== position) return;`.

### WR-04: `gemByNode` one-way latch can permanently persist a gem classified from a partial parent grading pass

**File:** `frontend/src/pages/Analysis.tsx:1390-1403` (source data frozen at `frontend/src/pages/Analysis.tsx:1262-1283`)
**Issue:** `gradeSummaryByFen` is updated while a position is current, from the *streaming* `qualityBySan` (grades arrive progressively per candidate). If the user plays a move before the parent's grading pass finishes, the parent's cached summary is frozen mid-stream — e.g. the best move plus one weak candidate graded, the real second-best still pending — showing an inflated `bestEs − secondBestEs` gap. `gemCandidate` then latches `true` into `gemByNode`, which by design never takes negative writes ("only ever inserts on an affirmatively-true classification"), so the false move-list gem badge survives all later navigation. Unlike the analogous `liveFlawByNode`, which waits for *both* parent and child evals to complete before writing (its severity is empty "until both parent and child evals complete", line 1340-1341), the gem latch has no completeness gate at all.
**Fix:** Only write `gradeSummaryByFen` (or only latch `gemByNode`) once the grading pass for that FEN is complete — e.g. gate on `!grading.isAnalyzing` / all `candidateSans` present in `gradeMap` — or require `secondBestEs` to be derived from ≥ N graded candidates before latching.

### WR-05: Game mode can stack a backend severity badge and the live gem badge on the same square corner

**File:** `frontend/src/pages/Analysis.tsx:1888-1897` (interacts with `frontend/src/hooks/useGameOverlay.ts:274-284`)
**Issue:** `boardSquareMarkers` appends `{ square: lastMove.to, gem: true }` onto `gameOverlay.squareMarkers`, which in game mode already contains a backend-precomputed severity marker at the *same* `lastMove.to` whenever the played mainline move was flagged. The "mutually exclusive by construction" claim in the comment only holds within the live pipeline: the backend severity comes from server-side Stockfish, the gem's C2 from the frontend WASM grading pass, and these evals diverge by design (documented eval non-determinism across machines). A move the backend graded "inaccuracy" that the live pass grades as clear-best produces two badges drawn in the same top-right corner (the gem overprinting the "?!" glyph). `SquareMarker`'s own docstring admits no runtime assertion enforces the exclusivity.
**Fix:** Skip the gem append when the base already carries a severity marker for that square:
```ts
if (gemCandidate && lastMove != null && !base.some((m) => m.square === lastMove.to && m.severity)) {
  return [...base, { square: lastMove.to, gem: true }];
}
```

## Info

### IN-01: Gem popover copy "players at your rating" actually reflects the ELO slider, not the account rating

**File:** `frontend/src/components/analysis/UnifiedMovePopover.tsx:66-75`
**Issue:** The C1 probability that triggered the gem line is evaluated at `selectedElo` (the draggable slider), which the user may have moved far from their own rating; the copy then over-claims ("at your rating"). Minor copy-accuracy nit since the slider defaults to the user's rating.
**Fix:** Consider "players at this rating almost never find this." to stay accurate under slider movement.

### IN-02: `GemIcon` sets `role="img"` with no accessible name when `aria-hidden={false}` is passed

**File:** `frontend/src/components/icons/GemIcon.tsx:38-51`
**Issue:** `aria-hidden` defaults to `true` (fine for the current decorative call sites), but the prop allows `false`, in which case the SVG exposes `role="img"` with no `<title>`/`aria-label` — an unnamed image to screen readers. `SeverityGlyphIcon` call sites pair the glyph with visible SAN text, and the gem badge conveys meaning only via color/shape.
**Fix:** Add `<title>Gem move</title>` inside the SVG (or an `aria-label`) so a future non-hidden usage is self-describing.

---

_Reviewed: 2026-07-10T18:25:09Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
