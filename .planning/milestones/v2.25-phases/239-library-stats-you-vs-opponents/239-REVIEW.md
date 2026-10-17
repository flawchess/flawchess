---
phase: 239-library-stats-you-vs-opponents
reviewed: 2026-10-13T00:00:00Z
depth: standard
files_reviewed: 35
files_reviewed_list:
  - app/repositories/library_repository.py
  - app/routers/library.py
  - app/schemas/library.py
  - app/services/flaw_delta_zones.py
  - app/services/library_service.py
  - app/services/tactic_delta_zones.py
  - frontend/src/components/endgames/stats/RankedMetricPopover.tsx
  - frontend/src/components/endgames/stats/TcSwitch.tsx
  - frontend/src/components/icons/SeverityGlyphIcon.tsx
  - frontend/src/components/insights/ShellyQuote.tsx
  - frontend/src/components/library/stats/ContextTagCards.tsx
  - frontend/src/components/library/stats/FlawTiles.tsx
  - frontend/src/components/library/stats/GapBar.tsx
  - frontend/src/components/library/stats/GapPopover.tsx
  - frontend/src/components/library/stats/GapRow.tsx
  - frontend/src/components/library/stats/LibraryStatsSections.tsx
  - frontend/src/components/library/stats/LibraryTcSwitch.tsx
  - frontend/src/components/library/stats/TacticTables.tsx
  - frontend/src/components/library/stats/WhatStandsOut.tsx
  - frontend/src/components/stats/TcSwitchButtons.tsx
  - frontend/src/components/ui/metric-info-popover.tsx
  - frontend/src/hooks/tcSelectionStore.ts
  - frontend/src/hooks/useEndgameStatsTc.ts
  - frontend/src/hooks/useLibrary.ts
  - frontend/src/hooks/useLibraryStatsTc.ts
  - frontend/src/lib/analytics.ts
  - frontend/src/lib/flawComparisonMeta.ts
  - frontend/src/lib/gapBar.ts
  - frontend/src/lib/tacticComparisonMeta.ts
  - frontend/src/lib/theme.ts
  - frontend/src/pages/GlobalStats.tsx
  - frontend/src/pages/library/GamesTab.tsx
  - frontend/src/types/library.ts
  - scripts/benchmarks/chapter5.py
  - scripts/benchmarks/render.py
findings:
  critical: 0
  warning: 4
  info: 6
  total: 10
status: issues_found
---

# Phase 239: Code Review Report

**Reviewed:** 2026-10-13
**Depth:** standard
**Files Reviewed:** 35
**Status:** issues_found

## Summary

Reviewed the per-TC payload rework (repository, service, router, schemas), both zone registries, the Gap bar math and components, the TC selection store, and the §5 benchmark extension, each against `git diff origin/main` and the locked CONTEXT decisions.

Checked and found sound:
- **User scoping (IDOR):** every query is scoped by `user_id` from `current_active_user`; no request parameter reaches it.
- **Per-TC data mapping:** `tc` is selected, grouped and bucketed consistently. `LIBRARY_TC_ORDER` and `ZONE_TC_FOR` cannot KeyError because `tc` iterates the closed literal.
- **Registry values:** they match `239-ZONE-PROPOSAL.md ## Accepted` (12 flaw bands unchanged, 9 tactic bands).
- **Gap math:** `gapPosition`, `bandRange`, `gapVerdict` and the standout ranking are monotonic and mutually consistent. A zoneless dot cannot leave the inner 25% per side by design.
- **Gates and floors:** the `< GATE` and `< LOW_SAMPLE_MIN_FLAWS` comparisons are strict and correctly oriented. The benchmark `>= 20` floor and the app gate of 20 line up.
- **Store behaviour:** the TC store persists, validates and falls back as D-05 requires.
- **Benchmark SQL:** `_PLAYER_FILTER` / `_OPP_FILTER` agree with `is_opponent_expr`, and the tactic predicate is imported rather than copied.

No blockers. Four warnings: one basis mismatch between the app's tactic population and the benchmark that calibrated its zones, one deviation from the D-12 scope, one gate/count denominator mismatch, and one benchmark-report summary that contradicts the shipped flaw registry.

## Warnings

### WR-01: Tactic comparison counts games whose tactic blobs are still pending as zero-tactic games (basis mismatch with the zones)

**File:** `app/repositories/library_repository.py:2190-2205` (anchor) and `:1661-1684` (`_analyzed_game_ids_subquery`), consumed by `app/services/library_service.py:1771-1812`
**Issue:** The tactic-zone bands (`tactic_delta_zones.py`) are calibrated in `scripts/benchmarks/chapter5.py:_base_games_cte` on games with `blobs_completed_at IS NOT NULL`. The docstring there says why: tactic motifs are suppressed to NULL while a flaw blob is pending, so a game without the blob "would contribute false zero tactic counts".

The app's tactic population is `_analyzed_game_ids_subquery`, which is only `full_evals_completed_at IS NOT NULL`. Per `.planning/notes/eval-completion-columns.md` this includes lichess-eval games, and per `eval_apply.py` the tier-4 blob pass is an opportunistic lottery, so those games can sit blob-pending indefinitely. For such a game:
- `fetch_tactic_comparison` emits a row with all-zero player and opponent counts.
- The game is added to `analyzed_n`, so it counts toward `TACTIC_COMPARISON_GATE` and the "N of 20" slot and can push a TC above the gate with no tactic data.
- The mean gap is diluted toward 0 for both Missed and Allowed, biasing verdicts toward "typical".

Flaw/context metrics are unaffected (tags don't depend on blobs). This is a user-visible correctness gap for exactly the users with many imported lichess games, and it makes the zones not comparable to the users they are applied to.

**Fix:** Give the tactic comparison its own population: `Game.blobs_completed_at.isnot(None)` in the `fetch_tactic_comparison` anchor, and the same predicate in `count_analyzed_by_tc` when it is called for tactics, for example via a `require_blobs: bool = False` keyword:
```python
anchor_subq = select(...).where(
    ...,
    Game.blobs_completed_at.isnot(None),  # blob-pending games have NULL tactic motifs (false zeros)
)
```
If the owner prefers to keep the broad population, document the dilution in the tactic popover basis line and in `tactic_delta_zones.py`.

### WR-02: Blunder/Mistake tiles lose their verdict under the D-12 low-sample rule, contradicting the locked scope and the component's own comment

**File:** `app/services/library_service.py:1425` (the same `low_sample` flag is set for all 12 flaw bullets), consumed by `frontend/src/lib/gapBar.ts:62-66` (`effectiveVerdict`) via `frontend/src/components/library/stats/FlawTiles.tsx:36-39,69-85`
**Issue:** D-12 applies the 40-flaw floor to "tactic cells **and** context-tag rows". `239-RESEARCH.md` open question 4 recommended no fade on tiles ("blunders/mistakes are never rare at >=20 games"), and `FlawTiles.tsx:36` states "Tiles are never faded".

But the backend sets `low_sample` on the blunder and mistake bullets too, and `GapBar` calls `effectiveVerdict(cell)`, which returns null whenever `lowSample` is true. So a tile with fewer than 40 combined blunders (you plus opponents) draws a blue dot with no red/green, and its popover says "Too few flaws to call it."

At the 20-game gate the combined count is below 40 whenever each side blunders less than 1 per game. That is realistic for stronger players (the blunder band is about +/-0.3 per 100 moves). The tile therefore silently drops its verdict at exactly the sample sizes where D-03 says tiles must be shown. The row is not faded, so the comment is half-true and the behaviour is undocumented.

**Fix:** Pick one and make code and comments agree:
- If the decision stands (tiles are not subject to D-12), set `low_sample=False` for `blunder` and `mistake` in `_build_flaw_bullet`, or pass `{ ...cell, lowSample: false }` for the tiles.
- If suppressing the verdict is intended, update the `FlawTiles.tsx` comment, CONTEXT D-12 and the research note.

### WR-03: `count_analyzed_by_tc` and the per-game fetches use different game populations (`ply_count` gate), so `analyzed_n`, `below_gate` and the offered TCs can disagree with the aggregated rows

**File:** `app/repositories/library_repository.py:1772-1828` (count) versus `:1939-1943` (`fetch_flaw_comparison` anchor) and `:2198-2203` (`fetch_tactic_comparison` anchor)
**Issue:** `count_analyzed_by_tc` drives `analyzed_n`, `below_gate`, which TCs are offered (D-02) and the default TC (D-04). It filters only on `time_control_bucket IS NOT NULL`. Both fetches additionally require `ply_count IS NOT NULL AND ply_count > 0` (the divide-by-zero guard).

A TC whose analyzed games have NULL/0 `ply_count` (pasted PGNs are the likely source, per the Pitfall 8 comment) is offered with `analyzed_n >= 20` ("above the gate"), becomes a D-04 default candidate, and then renders all-zero "No flaws yet" bars. The same mismatch inflates the "(N of 20)" figures. D-02 says the switch offers TCs with at least one analyzed game; the aggregated set and the count should share one anchor.

**Fix:** Add `Game.ply_count.isnot(None), Game.ply_count > 0` to the `count_analyzed_by_tc` WHERE clause. Better, factor the shared anchor predicates into one helper used by the count and both fetches.

### WR-04: `benchmarks-latest.md` still recommends the widened flaw bands that the owner rejected, so the report and `flaw_delta_zones.py` disagree

**File:** `reports/benchmark/benchmarks-latest.md:19` and the registry-mapping rows at `:1567-1576` versus `app/services/flaw_delta_zones.py:125-160`
**Issue:** At the 239-06 checkpoint the owner accepted with one edit: the 12 flaw bands keep their live values (`239-ZONE-PROPOSAL.md ## Accepted`). The registry is correct. The report was spliced before that decision. Line 19 says §5 "replac[es] the old whole-cohort basis", and the mapping table (for example `mistake` `[-0.23, +0.20]` to `[-0.66, +0.39]`, "**change** (owner accepts at the 239-06 checkpoint)") describes values the code does not contain.

The project rule is "benchmarks are the source of truth for typical", and CONTEXT D-07 says one basis for all zones, so a reader verifying the app against the report will find the flaw bands wrong by 1.5x to 3.5x. The owner override is recorded only in the phase proposal doc, not in the report or CONTEXT.

**Fix:**
- Amend the report's §5 summary row and registry-mapping table: flaw rows read "kept at live values (owner edit, noise inflation of the 100-games-per-TC lane cap)".
- Add a one-line D-07 override note to CONTEXT.md or the SUMMARY.
- Note in `flaw_delta_zones.py` that the flaw basis is the legacy whole-cohort basis while the tactic basis is the full-analysis lane. The docstring partly does this but does not name D-07.

## Info

### IN-01: Pinned-default store can overwrite the pin from an unrelated, still-empty section and flip the TC without a user action

**File:** `frontend/src/hooks/tcSelectionStore.ts:130-139`
**Issue:** `useTcSelection` pins in an effect that depends on `[pinnedOffered, defaultTc]`. A section whose payload is empty (still loading) mounts or re-renders with `pinnedOffered=false` and `defaultTc=null`, and its effect then sets the shared `pinnedDefaultTc = null`. This happens when the flaw query is cached but the tactic query is not (Library Stats remount, then a cache miss for one endpoint). The sections that were rendering with the old pin recompute `pickDefault` on their next render. If the user has no stored choice and the freshest default differs from the old pin, the TC changes with no click.

This is narrow because `pickDefault` is stable over unchanged data, and it is the exact class of flip FE-IN-05 set out to prevent.

**Fix:** Only write the pin when it is non-null: `if (!pinnedOffered && defaultTc !== null) pinnedDefaultTc = defaultTc;`. Or reset the pin only on filter-key change.

### IN-02: "N of your flaws" can double-count a flaw that carries a tactic in both orientations

**File:** `frontend/src/components/library/stats/TacticTables.tsx:61-63,141`
**Issue:** `yourFlaws` sums `you_events` of the missed and allowed bullets. Both come from separate column sets on the same `game_flaws` row, so one flaw with, for example, an allowed fork and a missed fork is counted twice and the label overstates "N of your flaws".

**Fix:** Either relabel to what it is ("N missed and allowed"), or have the backend return a distinct per-family flaw count.

### IN-03: GapBar `aria-label` is ungrammatical for "same" and always says "flaws"

**File:** `frontend/src/components/library/stats/GapBar.tsx:56`
**Issue:** `${words} flaws than your opponents` yields "same flaws than your opponents". For tactic bars the unit is tactics per 100 games, not flaws.

**Fix:** Build the label from `gapWords` plus a noun prop, with the same-case sentence "same as your opponents".

### IN-04: `user_moves` denominator has floor/ceil swapped relative to the service helper (pre-existing, but this phase re-ships it into the zones)

**File:** `app/repositories/library_repository.py:1932` (`fetch_flaw_comparison` anchor) and `scripts/benchmarks/chapter5.py:_base_games_cte`, versus `app/services/library_service.py:1071-1081`
**Issue:** `ply_count` is the total half-move count (max `game_positions.ply`). White plays plies 0, 2, 4, ..., so white's move count is `ceil(ply_count/2)`; `_user_moves_from_ply_count` implements exactly that. The comparison query and the benchmark use `floor` for white and `ceil` for black, one move off whenever `ply_count` is odd. The effect is small (about 1 move in 40, roughly half of the games) and identical in app and benchmark, so the zones stay self-consistent, but the two code paths disagree about the same quantity.

**Fix:** Out of scope to change mid-phase because it would shift the calibrated bands. Verify the intended convention and record it as a follow-up. If it is a bug, fix app and benchmark together and re-run §5.

### IN-05: Viability diagnostic ignores the sparse-cell exclusion that the zone query applies

**File:** `scripts/benchmarks/chapter5.py:511-540` (`_viability_sql`) versus `:380-390` (`pu` CTE with `SPARSE_CELL_EXCLUSION`)
**Issue:** `users_total` and `pct_nonzero` are computed over all user-cells, including the excluded (2400, classical) sparse cell. The zone distributions drop it (2,006 cells versus 2,004 pooled). The `zone_viable` 50% threshold is therefore evaluated on a marginally different population than the band it gates. The effect is negligible today (2 cells), but the "one definition, two call sites" intent stated in `_base_games_cte` does not extend to the cell set.

**Fix:** Apply the same `SPARSE_CELL_EXCLUSION` in `_viability_sql`, or state the difference in the §5.14 note.

### IN-06: Type-only import cycle between `types/library.ts` and `lib/tacticComparisonMeta.ts`

**File:** `frontend/src/types/library.ts:11` and `frontend/src/lib/tacticComparisonMeta.ts:98-99`
**Issue:** `types/library.ts` imports `TacticFamily` from the meta module, and the meta module imports `TacticBullet` and `TacticSide` from `types/library.ts`. Both are type-only and erased, so there is no runtime hazard, but an API-types module depending on a UI meta module inverts the layering (the backend `TacticFamily` literal is the source of truth).

**Fix:** Define `TacticFamily` in `types/library.ts` (mirroring the backend literal) and have the meta module import it from there.

---

_Reviewed: 2026-10-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
