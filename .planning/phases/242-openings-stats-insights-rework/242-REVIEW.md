---
phase: 242-openings-stats-insights-rework
reviewed: 2026-10-17T00:00:00Z
depth: standard
files_reviewed: 85
files_reviewed_list:
  - CHANGELOG.md
  - app/repositories/stats_repository.py
  - app/routers/insights.py
  - app/routers/openings.py
  - app/routers/stats.py
  - app/schemas/opening_insights.py
  - app/schemas/openings.py
  - app/schemas/stats.py
  - app/services/eval_confidence.py
  - app/services/opening_eval.py
  - app/services/opening_insights_constants.py
  - app/services/opening_insights_service.py
  - app/services/openings_service.py
  - app/services/repertoire_recency.py
  - app/services/score_confidence.py
  - app/services/stats_service.py
  - frontend/src/components/charts/PositionResultsPanel.tsx
  - frontend/src/components/charts/ScoreChart.tsx
  - frontend/src/components/openings/stats/FindingCard.tsx
  - frontend/src/components/openings/stats/OpeningColorSwitch.tsx
  - frontend/src/components/openings/stats/OpeningFindings.tsx
  - frontend/src/components/openings/stats/RepertoireExpandedRow.tsx
  - frontend/src/components/openings/stats/RepertoireTable.tsx
  - frontend/src/components/openings/stats/VerdictBar.tsx
  - frontend/src/components/openings/stats/VerdictPopover.tsx
  - frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
  - frontend/src/components/position-bookmarks/PositionBookmarkList.tsx
  - frontend/src/components/position-bookmarks/SuggestionsModal.tsx
  - frontend/src/components/stats/EvalCpuPlaceholder.tsx
  - frontend/src/hooks/usePositionBookmarks.ts
  - frontend/src/hooks/useReadiness.ts
  - frontend/src/lib/analytics.ts
  - frontend/src/lib/openingInsights.ts
  - frontend/src/lib/openingVerdict.ts
  - frontend/src/lib/openingsBoardLayout.ts
  - frontend/src/lib/retiredLocalStorage.ts
  - frontend/src/lib/scoreConfidence.ts
  - frontend/src/lib/theme.ts
  - frontend/src/pages/Openings.tsx
  - frontend/src/pages/openings/OpeningsDesktopSidebar.tsx
  - frontend/src/pages/openings/OpeningsMobileBoardPanel.tsx
  - frontend/src/pages/openings/OpeningsMobileDrawers.tsx
  - frontend/src/pages/openings/StatsTab.tsx
  - frontend/src/pages/openings/useDeepLinkHighlight.ts
  - frontend/src/pages/openings/useOpeningRowTimeSeries.ts
  - frontend/src/pages/openings/useOpeningsChartData.ts
  - frontend/src/pages/openings/useOpeningsHandlers.ts
  - frontend/src/pages/openings/useRepertoireRows.ts
  - frontend/src/pages/openings/useTabReset.ts
  - frontend/src/types/api.ts
  - frontend/src/types/insights.ts
  - frontend/src/types/openingsTab.ts
  - frontend/src/types/position_bookmarks.ts
  - frontend/src/types/stats.ts
  - frontend/src/components/charts/__tests__/PositionResultsPanel.test.tsx
  - frontend/src/components/charts/__tests__/ScoreChart.test.tsx
  - frontend/src/components/openings/__tests__/OpeningColorSwitch.test.tsx
  - frontend/src/components/openings/__tests__/OpeningFindings.test.tsx
  - frontend/src/components/openings/__tests__/RepertoireTable.test.tsx
  - frontend/src/components/openings/stats/__tests__/VerdictPopover.test.tsx
  - frontend/src/components/position-bookmarks/__tests__/PositionBookmarkCard.tracking.test.tsx
  - frontend/src/components/stats/__tests__/EvalCpuPlaceholder.test.tsx
  - frontend/src/hooks/__tests__/usePositionBookmarks.test.tsx
  - frontend/src/lib/__tests__/openingVerdict.test.ts
  - frontend/src/lib/__tests__/retiredLocalStorage.test.ts
  - frontend/src/pages/__tests__/Openings.render.test.tsx
  - frontend/src/pages/__tests__/Openings.statsBoard.test.tsx
  - tests/routers/test_insights_openings.py
  - tests/routers/test_openings_time_series_router.py
  - tests/services/test_opening_eval.py
  - tests/services/test_opening_insights_service.py
  - tests/services/test_score_confidence.py
  - tests/services/test_stats_service_phase_entry.py
  - tests/test_aggregation_sanity.py
  - tests/test_openings_service.py
  - tests/test_openings_time_series.py
  - tests/test_repertoire_recency.py
  - tests/test_stats_repository.py
  - tests/test_stats_router.py
  - tests/test_stats_schemas.py
  - tests/test_stats_service.py
findings:
  critical: 0
  warning: 3
  info: 7
  total: 10
status: issues_found
---

# Phase 242: Code Review Report

**Reviewed:** 2026-10-17
**Depth:** standard
**Files Reviewed:** 85 (the changed hunks vs `70f536a1a`, with callers read for context)
**Status:** issues_found

## Summary

The phase is in good shape. Gates run during review: `uv run ty check app/` passes, `uv run ruff check app/` passes, `scripts/check_function_size.py app/ --fail-over-depth 4` reports no breaches, and in `frontend/` `npx tsc -b`, `npm run lint` and `npm run knip` are clean.

The areas the task flagged check out:

- **Cutoff arithmetic** (`repertoire_recency.combine_cutoff`): `min(nth_played_at, now - 60d)` is "whichever reaches further back". `is_current` uses `>=`, so the Nth game itself is current. The cutoff is computed through `apply_game_filters` with the active filters and anchored on `dev_now_utc`.
- **ISO-week keying** (`openings_service._iso_week_monday`): matches the endgame timeline convention. The last in-window game of a week wins the rolling score, and `per_week_games` is counted from in-window games only.
- **Colour baseline sign**: White +0.25, Black -0.25, user-perspective eval. `finalize_opening_eval` centres only the p-value and confidence; `avg_eval_pawns` and the CIs stay raw. The endgame path still uses the `baseline_cp=0` default.
- **Cache invalidation**: the `['mostPlayedOpenings']` key matches `useStats.ts:73`. Create, delete and the Suggestions save all invalidate it.
- **Stale props after the Insights removal**: no dangling references (tsc and knip are clean).
- **Security**: no new endpoints and no injection surface. Every new query goes through `apply_game_filters` and is scoped by `user_id`.

There are no blockers. Three warnings concern correctness of the "duplicate collapse" promise and of the verdict colouring at edges. The rest are maintainability items.

## Warnings

### WR-01: Bookmark-twin drop runs after the deeper-line dedupe, so a deeper twin of a shallower bookmark survives

**File:** `app/services/stats_service.py:370-386` (also `:348-367`)
**Issue:** `_prepare_candidates` runs `_dedupe_identical_sets` first, then `_drop_bookmark_twins`. The twin drop compares only `full_hash`.

Take a bookmark on the shallower position A and a most-played pair A (shallow) / B (deeper) with an identical game set:
1. The dedupe keeps the deeper line B and removes A.
2. The twin drop finds no hash match for B, because B is not the bookmarked position.
3. The pinned bookmark A and the "Most played" row B are then shown with identical games, WDL and score. This is the Caro-Kann Advance duplicate that D-06 and the owner UAT reference were meant to remove.

The reverse case, where the bookmark is on the deeper position, works. `test_bookmark_twin_row_is_dropped_from_most_played` only covers a same-hash twin, so the gap is untested.

**Fix:** Drop twins first and remember the game-set fingerprints they carried. Then dedupe, and also drop any candidate whose fingerprint equals a dropped twin's:
```python
def _prepare_candidates(rows, position_wdl, cutoff, bookmark_hashes):
    candidates = _build_candidates(rows, position_wdl, cutoff)
    twin_prints = {
        fp for c in candidates
        if c.full_hash in bookmark_hashes and (fp := _game_set_fingerprint(c)) is not None
    }
    candidates = [
        c for c in candidates
        if c.full_hash not in bookmark_hashes
        and _game_set_fingerprint(c) not in twin_prints
    ]
    return _dedupe_identical_sets(candidates)
```
Add a test with a bookmark at a shallow hash and a deeper row with the same `game_id_sum`.

### WR-02: Eval verdict applies the 20-game floor to `games`, not to the eval sample size

**File:** `frontend/src/components/openings/stats/RepertoireTable.tsx:173-178`, `frontend/src/components/openings/stats/FindingCard.tsx:131-136`, `frontend/src/components/openings/stats/RepertoireExpandedRow.tsx:105-110`, `frontend/src/components/charts/PositionResultsPanel.tsx:222`
**Issue:** The eval `OpeningVerdictInput.games` is `row.games` (or `finding.n_games`, or `stats.total`). The eval mean is built from `eval_n` games only, because mate and NULL evals are excluded and the SQL trims outliers. Backend confidence requires only `EVAL_CONFIDENCE_MIN_N` (about 10).

A 40-game opening with `eval_n = 11` therefore gets a green or red eval dot from 11 samples. The popover footer beside it says `n = 11`, and the same eval on an 11-game opening would read "Too few games to call it". The faded-row and "too-few" rules are meant to stop this kind of call from thin data.

**Fix:** Pass the eval sample size for eval inputs, for example `games: row.evalN` in `EvalValue` and `EvalBar`, `finding.eval_n ?? 0` in `EvalLine`, and `stats.eval_n` in `OpeningEvalVerdictRow`. Row fading can keep using the game count.

### WR-03: A finding classified as a weakness at exactly 45% score renders as "typical" because of float arithmetic

**File:** `frontend/src/lib/openingVerdict.ts:57-62` (band check at line 59), reached from `FindingCard.tsx:76-82`
**Issue:** The backend classifies with direct comparison (`score <= 0.45` is a weakness) and documents why in `_classify_row`, because `0.45 - 0.50` is `-0.04999…` in IEEE-754. The frontend computes `delta = score - 0.5` and tests `Math.abs(delta) <= band`, which reintroduces that artifact:
- `0.45 - 0.5 = -0.04999999999999999`, which is `<= 0.05`, so the verdict is "typical" (grey).
- `0.55 - 0.5 = 0.050000000000000044`, which is `> 0.05`, so a card at exactly 55% is coloured.

A card at exactly 45.0% with n of about 1000 (p < 0.01) sits under "Moves that cost you" with a grey dot and the "That is typical" popover text. The same score on the strength side gets the colour, so the result is asymmetric. The unit test uses a clean `0.3` band edge and does not exercise computed deltas.

**Fix:** Compare on a rounded scale, or compare the raw value to the band edges. For example, round `delta` to a fixed number of decimals (`Math.round(delta * 1e6) / 1e6`) inside `openingVerdictReason`, or have `scoreDelta` return a rounded value. Add a test with `scoreDelta(0.45)` and `scoreDelta(0.55)`.

## Info

### IN-01: "Either colour" requests test eval against the White baseline

**File:** `app/services/opening_eval.py:45-49`, `app/services/openings_service.py` (`analyze`)
**Issue:** `resolve_eval_baseline_pawns(None)` returns +0.25. For a colour-less request (`OpeningsRequest.color` is `Literal["white","black"] | None`), the MG-entry eval mixes White-user and Black-user perspectives, so the right H0 is about 0, not +0.25. Before this phase the H0 was 0 and the baseline was only a tick, so this is a new bias in the p-value and confidence for API callers that omit `color`. The UI always sends a colour, so it is not reachable from the app. Colour-less bookmarks are also never shown in the table. Consider returning 0.0 for `None` in the z-test path, or rejecting `None` at the schema level.

### IN-02: Popover baseline copy duplicates the constants

**File:** `frontend/src/components/openings/stats/VerdictPopover.tsx:27-28`
**Issue:** `COPY_BASELINE` hard-codes "+0.25 for White and −0.25 for Black", while `evalBaselinePawns()` and the backend constants already own those values. If the benchmark baseline is refit, the popover silently drifts. Build the sentence from `evalBaselinePawns('white'|'black')` with `formatSignedGap`.

### IN-03: Stale docstrings and comments left over from the rework

**File:** `app/services/eval_confidence.py:35-38`, `frontend/src/types/insights.ts:131`, `frontend/src/lib/sanToSquares.ts`, `frontend/src/components/stats/EvalCpuPlaceholder.tsx:6`
**Issue:**
- `eval_confidence.py` says `openings_service` and `opening_insights_service` still call the primitive "until their Phase 242 plans land". Both now call `finalize_opening_eval`.
- `insights.ts:131` still describes the baseline as "a reference tick on the finding card's eval bullet chart", which is now the bar centre.
- `sanToSquares.ts` and `EvalCpuPlaceholder.tsx` still name the deleted `OpeningFindingCard` and `OpeningStatsCard`.
- `EvalConfidencePopover`'s `'opening-end'` branch is now unreachable from `PositionResultsPanel`, which only passes `endgame-entry` or the no-data fallback.

CLAUDE.md asks for comments to describe current behaviour. Update them and prune the dead popover branch.

### IN-04: Expansion state and the "Played before" toggle survive a colour switch

**File:** `frontend/src/components/openings/stats/RepertoireTable.tsx:408-409`, `frontend/src/pages/openings/useRepertoireRows.ts:76`
**Issue:** `pastExpanded` and `expandedKeys` live in `RepertoireTable`, which is not re-keyed per colour. Row keys are `mpo-${full_hash}`. When the user flips White to Black, the "Played before" group stays open. A position that appears in both colour lists (for example a "vs." row) is auto-expanded and fires a lazy time-series request. Pass `key={color}` to `RepertoireTable`, or reset both states when `color` changes.

### IN-05: Suggestions pool can include "past" openings

**File:** `frontend/src/components/position-bookmarks/SuggestionsModal.tsx:41-52`
**Issue:** `mostPlayedData.white` is now current rows first, then past rows. The modal slices the first 10, so a user with fewer than 10 current rows is offered stale openings as suggestions. The `bookmarkedHashes` filter is also largely redundant now that the server drops bookmark twins. Filter with `o.is_current` before slicing, or document the intent.

### IN-06: Minor UI/theme nits

**File:** `frontend/src/components/openings/stats/RepertoireTable.tsx:369`, `frontend/src/components/openings/stats/OpeningColorSwitch.tsx:6-9`
**Issue:**
- The footer prints "1 bookmarks". Pluralise it.
- The colour switch hard-codes `bg-white` and `bg-zinc-900` for the piece swatches. `SIDE_SWATCH_WHITE` and `SIDE_SWATCH_BLACK` already exist in `theme.ts` and are used by `VerdictBar`. frontend/CLAUDE.md asks for semantic colours to come from `theme.ts`.

### IN-07: The `NowUtc` dependency alias is copy-pasted into four routers

**File:** `app/routers/insights.py:50`, `app/routers/openings.py:29`, `app/routers/stats.py:27` (existing in `app/routers/train.py:65`)
**Issue:** The same `Annotated[datetime.datetime, Depends(dev_now_utc)]` alias is declared in each router. It follows the existing `train.py` pattern, so it is not a bug. Exporting one alias from `app/core/dev_clock.py` would remove the duplication.

---

_Reviewed: 2026-10-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
