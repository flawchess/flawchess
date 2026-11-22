---
phase: 260-facepalm-first-class-move-quality
reviewed: 2026-11-22T15:50:00Z
depth: standard
files_reviewed: 30
files_reviewed_list:
  - app/repositories/library_repository.py
  - app/repositories/query_utils.py
  - app/routers/library.py
  - app/services/blunder_check_rules.py
  - app/services/library_service.py
  - frontend/src/api/client.ts
  - frontend/src/components/analysis/AnalysisTagsPanel.tsx
  - frontend/src/components/filters/FlawFilterControl.tsx
  - frontend/src/components/library/EvalChart.tsx
  - frontend/src/components/library/MoveStats.tsx
  - frontend/src/components/library/SeverityBadge.tsx
  - frontend/src/components/results/LibraryGameCard.tsx
  - frontend/src/hooks/useFlawFilterStore.ts
  - frontend/src/hooks/useLibrary.ts
  - frontend/src/lib/analytics.ts
  - frontend/src/lib/facepalm.ts
  - frontend/src/lib/flawDotColor.ts
  - frontend/src/lib/flawSeverityFilter.ts
  - frontend/src/lib/gameCardGeometry.ts
  - frontend/src/lib/moveStatsCounts.ts
  - frontend/src/lib/theme.ts
  - frontend/src/pages/library/FlawsTab.tsx
  - frontend/src/pages/library/GamesTab.tsx
  - frontend/src/types/library.ts
  - tests/repositories/test_library_repository.py
  - tests/services/test_facepalm_score.py
  - tests/services/test_library_service.py
  - tests/test_library_repository.py
  - tests/test_library_router.py
  - tests/test_query_utils.py
findings:
  critical: 0
  warning: 2
  info: 6
  total: 8
status: issues_found
---

# Phase 260: Code Review Report

**Reviewed:** 2026-11-22T15:50:00Z
**Depth:** standard
**Files Reviewed:** 30
**Status:** issues_found

## Summary

Reviewed the diff `3b3d7d394..HEAD` for the listed files and re-ran the gates myself: `ruff check`, `ty check app/ tests/ scripts/`, `check_function_size.py` (depth 4), `knip`, `tsc -b`, eslint on the touched trees, the 7 backend test files (372 passed) and the frontend vitest trees (4601 passed). All green; I did not find a defect that breaks the headline behaviour.

Claims checked against the code:

1. **Severity semantics (holds).** `_severity_clause` compiles correctly for every subset. I compiled it with the asyncpg dialect: Facepalm is `CAST(expr AS FLOAT) >= $FLOAT`, Blunder is `coalesce(CAST(expr AS FLOAT), 0.0) < $FLOAT`, so a NULL score is a Blunder and never a Facepalm. The cut is inclusive on both the SQL side (`>= FACEPALM_STATS_MIN`) and the frontend side (`floor(score*100) >= 70`). I probed the 6 doubles either side of 0.7 in Node: `f >= 0.7` and `floor(f*100) >= 70` agree on all of them, so the table count and the filtered list cannot disagree at the boundary. The score expression renders once for a lone Blunder or Facepalm and never for the rest (pinned by a compile test).
2. **Empty vs all-three (holds on the frontend, not on the backend, see WR-01).** `isSeverityNarrowed` gates `useLibraryGames`, the FlawsTab URL writer, `isFlawFilterNonDefault` and the ring. `useLibraryFlaws` sends all three, which the backend treats identically to the service default. The store is module-level and never persisted, so there is no stale persisted shape; the only stale-meaning paths are old URLs and cached PWA bundles (IN-01).
3. **Owner gate removal (holds).** The only two callers (`get_game_card` path at library_service.py:864 and the games page at :1058) feed display markers. Both still filter on `GameFlaw.user_id == user_id` (IDOR), the Flaws list, the Games EXISTS and drill selection keep their own `player_only_gate`. Nothing leaks that the user's own game did not already own.
4. **Filter ring (holds).** `outlinedCellRefs` is empty when `userColor == null`, only emits the player-side ref, only for selected tags while narrowed, plus Gem/Great independently. `AnalysisTagsPanel` never passes `outlinedRefs`, so `/analysis` rings nothing. `ownFilterTag` / `SeverityBadge` are correct, the Train card passes `showActiveFilterRing={false}`.
5. **Eval chart (holds).** `FLAW_CATEGORY_COLOR` is a `Record<FlawMoveCategory, string>`, so `tsc` enforces exhaustiveness; colour feeds the normal, highlighted and dimmed states through the single `color` variable in `buildDotRenderer`.
6. **Removed params (holds).** Unknown query params are ignored by FastAPI; `test_removed_facepalm_range_params_are_ignored` asserts 200 and an unchanged `matched_count` on both `/flaws` and `/games`. A repo-wide grep finds no remaining `min_facepalm_pct`, `_facepalm_clause`, `FACEPALM_PCT_*`, `FacepalmPreset`, `facepalmMin/Max`, `FacepalmFilter` or `filter-facepalm` outside the intentional stale-client test and its fixtures.
7. **Test pins.** Most deleted tests moved with a stronger equivalent. Two pins were lost rather than moved (WR-02).

No Critical findings.

## Warnings

### WR-01: Backend treats "all three tags" differently from "no tags" on the Games EXISTS and every stats endpoint

**File:** `app/repositories/query_utils.py:406` (gate), `app/repositories/library_repository.py:365-383` (clause)
**Issue:** The requirement is that an empty selection and all three tags both mean "no narrowing". On `/library/flaws` this holds because the service substitutes the all-three default. On every other consumer of `apply_game_filters` (`/library/games`, flaw-stats, flaw-comparison, facepalm-comparison, tactic-comparison) it does not: `if flaw_severity or ...` is true for a three-element list, so `flaw_exists_from_table` adds an EXISTS "game has at least one of the user's own mistakes/blunders". No severity param returns the plain archive. The two requests therefore differ for unanalysed games, flawless games and opponent-only-flaw games. The new test pins this divergence instead of catching it: in `test_games_severity_tags_follow_d08` the all-three row expects `{"facepalm","below","unscored","mistake"}` while the no-tag row expects those plus `"opponent"`. The `_severity_clause` docstring ("all three tags compile to mistake OR blunder, the full M+B set") also describes the clause, not the no-filter contract. The frontend masks this only on `useLibraryGames` (via `isSeverityNarrowed`); any other client, a stale PWA bundle, or a future caller of the stats hooks with a raw store value gets the narrower result. Before this phase the same hazard existed for `[blunder, mistake]`, so this is a preserved inconsistency, but the phase redefined "all" as three tags and the stated contract is that it equals none.
**Fix:** Normalise once at the shared gate so every endpoint agrees, and update the test row.
```python
# query_utils.apply_game_filters, before the truthiness gate
if flaw_severity and set(flaw_severity) >= set(FLAW_SEVERITY_FILTER_VALUES):
    flaw_severity = None  # all three tags = no severity narrowing (260 D-08)
```
(or do the same inside `build_flaw_filter_clauses`/`flaw_exists_from_table` and drop the severity clause for a full selection). Change the all-three expectation in `test_games_severity_tags_follow_d08` to include `"opponent"`.

### WR-02: Two behaviour pins were deleted without a replacement

**File:** `tests/repositories/test_library_repository.py` (deleted `test_chip_and_filter_agree_on_facts_grid`), `tests/test_query_utils.py` (deleted `TestFacepalmGate.test_narrowed_range_requires_user_id`)
**Issue:**
- The facts-grid test was the only test that swept facts across every whole-percent boundary and asserted the chip value and the filter selected the same rows (the D-01 shared-expression invariant). The new `TestFlawSeverityTags` rows each sit one `SEED_FACEPALM_MARGIN` either side of the cut and only compare ply sets; none asserts `facepalm_score >= cut` for items returned under Facepalm or `< cut`/`None` for items returned under Blunder. If `_severity_clause` ever built its own expression instead of the bound chip (the `score` parameter), nothing would fail until a REAL-precision edge row appears in production. The same-cut agreement between the SQL cut and the frontend `toFacepalmPct` floor is likewise tested only on the Python side (`test_facepalm_stats_min_is_the_frontend_facepalm_cut` pins the constant, not the boundary behaviour).
- The `ValueError("flaw/tactic filter requires user_id for EXISTS scoping")` guard in `apply_game_filters` is now unpinned: the only test that exercised it did so through the removed facepalm range, and no other test in `test_query_utils.py` calls with `user_id=None` and an active flaw/tactic filter.

**Fix:** Add to `TestFlawSeverityTags` an assertion over the returned items, e.g. for the Facepalm case `assert all(i.facepalm_score is not None and i.facepalm_score >= FACEPALM_STATS_MIN for i in items)` and for the Blunder case `all(i.facepalm_score is None or i.facepalm_score < FACEPALM_STATS_MIN ...)`, and re-add a parametrised `pytest.raises(ValueError)` test for `flaw_severity=["facepalm"]` / `["blunder"]` with `user_id=None`.

## Info

### IN-01: Old URLs and cached bundles silently change meaning

**File:** `frontend/src/pages/library/FlawsTab.tsx:101-110`
**Issue:** The store is module-level and never persisted, so no stored shape can go stale. Two external paths still change meaning: a bookmarked `/library/flaws?severity=blunder` (the old writer only emitted a param when one tier was selected) used to list all blunders and now lists only non-facepalm blunders; a PWA bundle cached from before the deploy that has both tiers selected sends `severity=blunder&severity=mistake`, which the new backend answers without facepalms. Inherent to D-09, and the old bundle case is transient, so no code change is required. Consider a one-line CHANGELOG note ("Blunder now excludes Facepalm in the Flaws filter") and, optionally, a short hint in the Flaws filter section (D-discretion item), since a user who selects only Blunder expecting the Lichess count sees fewer rows with no explanation.
**Fix:** CHANGELOG sentence; optional `InfoPopover` or helper text under the Flaws row saying Blunder excludes Facepalm.

### IN-02: Stale comments still describe owner-only facepalm scoring and the removed filter

**File:** `app/services/library_service.py:213`, `app/schemas/library.py:96-98`, `app/routers/library.py:97-98`, `frontend/src/lib/tacticDepth.ts:101`, `frontend/src/lib/facepalm.ts:61-62`, `frontend/src/hooks/useLibrary.ts:136`, `frontend/src/components/results/LibraryGameCard.tsx:182,643`, `frontend/src/components/analysis/AnalysisTagsPanel.tsx:258`
**Issue:** After D-24 these comments mislead: `facepalm_by_ply` is documented as "scored owner-side rows only" and `FlawMarker.facepalm_score` as "today only the user's own blunders are scored"; the router `severity` docstring still says "at that severity (or worse)"; `tacticDepth.ts` cites "the Facepalm filter's" bands; `toFacepalmPct` says it matches "the backend comparison against k/100" (the backend now compares to `FACEPALM_STATS_MIN` as a double); several comments still say "7 Move Stats rows" / "7-row table" (now 8) and `useLibrary.ts` says "both tiers selected".
**Fix:** Update the comments to the D-24 / 8-row / three-tag wording.

### IN-03: The facepalm classifier is re-inlined in two places instead of using `flawMoveCategory`

**File:** `frontend/src/hooks/useGameOverlay.ts:134`, `frontend/src/lib/explainBar.ts:140`
**Issue:** Both still spell `severity === 'blunder' && isFacepalmBlunder(score)` while `moveStatsCounts.ts` documents `flawMoveCategory` as the single place the split lives (D-07). They agree today, but a change to the split (for example when 259-12 moves the cut or a fourth tier is added) must now be applied in three places for the board badge, the Explain bar and the table to stay consistent.
**Fix:** Use `flawMoveCategory(fm) === 'facepalm'` in both (as `LibraryGameCard` already does at line 308).

### IN-04: Desktop card geometry is verified only against itself

**File:** `frontend/src/lib/gameCardGeometry.ts:23-54`, `frontend/src/lib/__tests__/gameCardGeometry.test.ts`
**Issue:** The test pins `DESKTOP_EVAL_CHART_HEIGHT_CLASS` to the computed `h-[127px]`, but jsdom cannot confirm the part constants (24px row, 37px strip, 97px tags card, 1px borders) against real layout; the file's own comment names inline-baseline slack as a known risk. Board 248 vs table 247 relies on `flex-1` stretching to hide the 1px gap. This needs the browser UAT that D-22 already defers to the merge; flagging so it is not marked verified by the unit test alone.
**Fix:** Confirm in a real browser at `lg` (analysed and unanalysed cards, with and without the tags card) before merge.

### IN-05: `SEV_FACEPALM_BG` duplicates the colour literal instead of deriving it

**File:** `frontend/src/lib/theme.ts:529`
**Issue:** `'oklch(0.42 0.17 25 / 0.14)'` repeats the `FACEPALM_BAND_SWATCH` value. This follows the existing `SEV_*_BG` convention (the neighbouring constants do the same), but if the swatch is retuned the pill background silently drifts from the dot colour.
**Fix:** Optional: build it from the swatch (a small `withAlpha` helper) or add a theme test pinning the shared hue/lightness.

### IN-06: The Facepalm cut is still a literal in the backend parity test

**File:** `tests/services/test_facepalm_score.py` (`STATS_MIN_VALUE = 0.7`)
**Issue:** D-21 says this phase never states the cut as a literal in tests. The new frontend-file parse is good, but `assert stats_min == STATS_MIN_VALUE` still hard-codes 0.7, so plan 259-12 has to edit two places (the constant and this literal) for a cut move. Pre-existing literal, kept rather than introduced.
**Fix:** Drop the literal assertion and keep only the frontend-parity assertion plus the existence check.

---

_Reviewed: 2026-11-22T15:50:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
