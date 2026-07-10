---
phase: 163-gem-moves-maia-findability-move-badges-on-analysis-seed-092
fixed_at: 2026-07-10T20:41:00Z
review_path: .planning/phases/163-gem-moves-maia-findability-move-badges-on-analysis-seed-092/163-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 163: Code Review Fix Report

**Fixed at:** 2026-07-10T20:41:00Z
**Source review:** 163-REVIEW.md (issues_found — 0 critical, 5 warning, 2 info)
**Iteration:** 1

**Summary:**
- Findings in scope: 7 (5 Warning mandatory + 2 Info applied as trivial/zero-risk)
- Fixed: 7
- Skipped: 0

**Verification:** `npx tsc -b` clean, `npm run lint` clean, `npm test -- --run` 1739/1739 passed (baseline 1732 + 7 new tests added by these fixes).

## Fixed Issues

### WR-01: `qualityBySanWithGem` hard-coded `playedIsBest: true`

**Files modified:** `frontend/src/pages/Analysis.tsx`
**Commit:** 4cc4d928
**Applied fix:** The memo now destructures `bestSan` from `summarizeForGem` and passes `playedIsBest: bestSan === reconciledBestSan`, mirroring the arrival-move path's existing check. When the summarize argmax diverges from the reconciled best (tie-break drift, partially graded map), no gem is painted.
**Tests:** The `playedIsBest: false → no gem` contract is covered by the existing `classifyGem` unit test; a wiring-level divergence assertion was not added — forcing `argmax(qualityBySan) !== reconciledBestSan` through the integration harness requires a contrived `sanToUci` resolution failure (the WR-02 phantom-argmax route to divergence is closed by the WR-02 fix itself). Flagged for human eyes at UAT if desired.

### WR-02: `summarizeForGem` counted null/null grades as expected score 0.5

**Files modified:** `frontend/src/lib/gemMove.ts`, `frontend/src/lib/__tests__/gemMove.test.ts`
**Commit:** cb6941b4
**Applied fix:** Ungraded entries (`evalCp === null && evalMate === null`) are skipped inside the reduction — no evidence, no contribution. Docstring updated.
**Tests added (3):** phantom 0.5 must not displace the real argmax in a lost position (D-01 protection); ungraded entry never becomes `secondBestEs` in a winning position (no spurious C2 gap); all-ungraded map reduces to all-null.

### WR-03: Per-FEN caches poisoned for one commit on every navigation

**Files modified:** `frontend/src/hooks/useMaiaEngine.ts`, `frontend/src/hooks/useStockfishGradingEngine.ts`, `frontend/src/pages/Analysis.tsx`, `frontend/src/pages/__tests__/Analysis.test.tsx`, `frontend/src/hooks/__tests__/useMaiaEngine.test.ts`, `frontend/src/hooks/__tests__/useStockfishGradingEngine.test.ts`
**Commit:** 08d98b3c
**Applied fix:** Took the review's primary suggestion — expose the FEN the data actually belongs to from both hooks and guard the cache writes on it:
- `useMaiaEngine` now returns `resultFen` (`MaiaResult` carries the fen it was built for; cached restores keep the correct attribution).
- `useStockfishGradingEngine` now returns `gradeMapFen` (set with every `commitDisplayedGradeMap`, cleared to null when the map clears on real navigation).
- Analysis.tsx's `maiaCurveByFen` write is guarded by `maia.resultFen === position`; the `gradeSummaryByFen` write by `grading.gradeMapFen === position` (both added to the effect deps). The one-commit window where `position` is the child but hook state is still the parent's can no longer write `childFen → parent data`.
- Analysis.test.tsx's hook mocks extended to carry the two new fields (attributed to the fen Analysis passes in, null while empty — matching the mocks' "data is for the position under test" convention).
**Tests added (2):** `resultFen` reports/clears with the held curve (useMaiaEngine.test.ts); `gradeMapFen` reports/clears with the displayed map on navigation (useStockfishGradingEngine.test.ts).
**Note:** the pre-existing `engineEvalByFen` cache shares this pattern (acknowledged by the review as degrading gracefully); it was left untouched — out of finding scope.

### WR-04: `gemByNode` one-way latch could persist a gem from a partial grading pass

**Files modified:** `frontend/src/pages/Analysis.tsx`, `frontend/src/pages/__tests__/Analysis.test.tsx`
**Commit:** 2392e382
**Applied fix:** The `gradeSummaryByFen` write is now additionally gated on `!grading.isGrading` — a completeness gate mirroring `liveFlawByNode`'s wait-for-complete pattern, per D-06 (no min-depth tunable reintroduced). A summary is only cached once the grading search finished (bestmove received) or was served entirely from the hook's cache (`isGrading` never flips true on a pure cache hit), so the latch can never fire off a mid-stream inflated `bestEs − secondBestEs` gap.
**Tests added (1):** with the grading mock reporting `isGrading: true`, a fully qualifying gem setup must paint neither the board marker nor the move-list badge (mock extended with a controllable `isGrading`).

### WR-05: Game mode could stack a backend severity badge and the gem badge on one square

**Files modified:** `frontend/src/pages/Analysis.tsx`, `frontend/src/pages/__tests__/Analysis.test.tsx`
**Commit:** 12c24307
**Applied fix:** The minimal deterministic rule from the fix constraints: `boardSquareMarkers` skips the gem append when the base already carries a severity marker on `lastMove.to` (`!base.some((m) => m.square === lastMove.to && m.severity != null)`) — severity wins, gem yields, one square never renders two badges. The now-inaccurate "mutually exclusive by construction, plain append is safe" comment was corrected to scope the exclusivity claim to the live pipeline only.
**Tests added (1):** mainline game node whose played move carries both a backend `mistake` marker and a qualifying live gem — the "?" glyph renders, the violet gem circle does not.

### IN-01: Gem popover copy over-claimed "at your rating"

**Files modified:** `frontend/src/components/analysis/UnifiedMovePopover.tsx`
**Commit:** c42ca679
**Applied fix:** Copy changed to "Gem — players at this rating almost never find this." (accurate under ELO-slider movement; the slider defaults to the user's rating so the common case reads the same).

### IN-02: `GemIcon` exposed an unnamed `role="img"` when `aria-hidden={false}`

**Files modified:** `frontend/src/components/icons/GemIcon.tsx`
**Commit:** 470bc5eb
**Applied fix:** Added `<title>Gem move</title>` inside the SVG so any future non-hidden usage is self-describing to screen readers.

## Skipped Issues

None.

---

_Fixed: 2026-07-10T20:41:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
