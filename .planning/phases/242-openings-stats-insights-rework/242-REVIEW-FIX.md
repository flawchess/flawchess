---
phase: 242-openings-stats-insights-rework
fixed_at: 2026-10-17T21:00:00Z
review_path: .planning/phases/242-openings-stats-insights-rework/242-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 242: Code Review Fix Report

**Fixed at:** 2026-10-17
**Source review:** .planning/phases/242-openings-stats-insights-rework/242-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

Verification ran in the main checkout on branch `gsd/phase-242-openings-stats-insights-rework`, not in an isolated worktree. The orchestrator asked for in-place work, and a fresh worktree has no `node_modules` or `.venv`. No recovery sentinel or temp branch was created.

## Fixed Issues

### WR-01: Bookmark-twin drop runs after the deeper-line dedupe, so a deeper twin of a shallower bookmark survives

**Files modified:** `app/services/stats_service.py`, `tests/test_stats_service.py`
**Commit:** 6307dc980
**Applied fix:** `_prepare_candidates` now drops bookmark twins before `_dedupe_identical_sets`. `_drop_bookmark_twins` also drops any candidate whose game-set fingerprint equals that of a bookmarked-hash candidate, so a deeper row with the same games as a shallow bookmark no longer survives. Added a unit test for the fingerprint rule and a `_prepare_candidates` pipeline test (shallow bookmark, deeper twin, unrelated row). An existing twin test used two candidates with accidentally identical fingerprints, so its "other" row now has a distinct `game_id_sum`. Gates: `uv run pytest tests/test_stats_service.py` (34 passed), `ruff check`, `ty check app/ tests/test_stats_service.py`.
**Status note:** logic fix, requires human verification. The fix only collapses when the bookmarked position is itself a most-played candidate (it needs a fingerprint to compare against).

### WR-02: Eval verdict applies the 20-game floor to `games`, not to the eval sample size

**Files modified:** `frontend/src/components/openings/stats/RepertoireTable.tsx`, `frontend/src/components/openings/stats/FindingCard.tsx`, `frontend/src/components/openings/stats/RepertoireExpandedRow.tsx`, `frontend/src/components/charts/PositionResultsPanel.tsx`, `frontend/src/components/charts/__tests__/PositionResultsPanel.test.tsx`, `frontend/src/components/openings/__tests__/RepertoireTable.test.tsx`
**Commit:** 8f3f4ca1b
**Applied fix:** The eval `OpeningVerdictInput.games` is now the eval sample (`row.evalN` in `EvalValue` and `EvalBar`, `evalN` in `EvalLine`, `stats.eval_n` in `OpeningEvalVerdictRow`). Score inputs, row fading and popover game counts still use the game count. Two existing low-sample tests set a small game count but left `evalN` at 90 (or `eval_n` at 38), so they now set the eval sample too. Added regression tests for 100 games with 11 evals (the eval dot stays neutral; in the table the score dot still colours). Gates: vitest on `src/components`, `src/pages`, `src/lib` (all passed), `npm run lint`, `npm run build`.
**Status note:** logic fix, requires human verification.

### WR-03: A finding classified as a weakness at exactly 45% score renders as "typical" because of float arithmetic

**Files modified:** `frontend/src/lib/openingVerdict.ts`, `frontend/src/lib/__tests__/openingVerdict.test.ts`
**Commit:** ad76675c0
**Applied fix:** `openingVerdictReason` rounds the delta to 6 decimals (named constants `BAND_COMPARE_DECIMALS` and `BAND_COMPARE_SCALE`) before the band test, with a comment at the fix site. Both 45% and 55% now land exactly on the band edge and read as typical, so the two edges are symmetric. The new test uses `scoreDelta(0.45)` and `scoreDelta(0.55)`. Reverting the fix makes it fail. Gates: openingVerdict vitest (20 passed), `npm run lint`, `npm run build`.
**Status note:** logic fix, requires human verification. This follows the review's suggested fix, which keeps the band edge inclusive. The backend `_classify_row` still lists a score of exactly 45% or 55% as a finding, so a card at an exact edge is listed but grey. Making the frontend edge strict would colour it instead, but it would also contradict the popover text "Typical: 45% to 55%" and the existing "exactly on the band edge is typical" test. That is an owner call, so it was not changed.

---

_Fixed: 2026-10-17_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
