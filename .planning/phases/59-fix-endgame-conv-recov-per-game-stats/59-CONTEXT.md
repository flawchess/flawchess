# Phase 59: Fix Endgame Conv/Even/Recov per-game stats - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning
**Mode:** Discuss (user delegated all gray-area calls to Claude)

<domain>
## Phase Boundary

The "Endgame Score Gap & Material Breakdown" section must account for every Games-with-Endgame game exactly once across the three buckets (Conversion / Even / Recovery), so the sum of per-row game counts equals `performance.endgame_wdl.total` for any filter combination. In parallel, the obsolete admin-gated "Conversion and Recovery" section (aggregate gauges + rolling-window conv/recov timeline) is removed end-to-end — frontend components, their dedicated backend query path, and the now-unused fields on `EndgamePerformanceResponse`.

In scope:
- `_compute_score_gap_material` (app/services/endgame_service.py:499) logic correction
- Backend cleanup of orphaned aggregates/timeline query after UI removal
- Removal of `EndgameGaugesSection.tsx` and `EndgameConvRecovTimelineChart.tsx` + their wiring in `Endgames.tsx`
- One backend unit test asserting the invariant

Out of scope (belongs in other phases):
- Changes to the "Results by Endgame Type" table (`EndgameConvRecovChart`) — stays 6-ply sequence-based with per-category `categories[i].conversion` aggregates
- Bucket semantics (thresholds, 4-ply persistence, labels) — already locked by Phase 53 + quick task 260413-pwv
- Any new UI for endgame analytics
</domain>

<decisions>
## Implementation Decisions

### 1. Null-imbalance handling → bucket into "even"

Games where `user_material_imbalance` is NULL at endgame entry (rare, but possible from old rows or edge cases) are assigned to the **"even"** bucket instead of being dropped. Same applies when only `user_material_imbalance_after` is NULL (non-contiguous 4-ply span): the game cannot satisfy the conversion/recovery persistence check, so it logically belongs in "even".

**Why:** "Even" semantically means "no persistent advantage or disadvantage" — an undetermined imbalance cleanly fits that bucket. Adding a fourth "unknown" bucket would defeat the invariant goal (three buckets summing to total) and complicate the table UI. Dropping (current behavior) is the actual invariant-breaker.

**Effect on invariant:** Combined with decision #2, every game in `endgame_wdl.total` is now accounted for exactly once.

### 2. Multi-class dedupe → group-then-pick (prefer non-null, deterministic tiebreak)

Games can appear multiple times in `entry_rows` (once per endgame_class span that meets the 6-ply threshold). The current dedupe picks the first row seen, which is non-deterministic relative to SQL ordering AND can lose a game entirely when the first span has NULL imbalance but another span doesn't.

New rule: group `entry_rows` by `game_id`, then for each game select one span using this priority:
1. Rows where **both** `user_material_imbalance` and `user_material_imbalance_after` meet the conversion OR recovery threshold — these are the rows that would move the game out of "even".
2. If no row qualifies (i.e. no span satisfies the persistence check in either direction), any row for that game will bucket to "even" anyway — pick the one with the lowest `endgame_class` integer for deterministic selection.

Result: a game is classified as Conversion or Recovery if **any** of its qualifying class spans shows that persistent imbalance; otherwise it's Even.

**Why:** Aligns with the chess-native reading of the metric ("did the user face a conversion situation at some point during their endgames?"), makes the output deterministic regardless of SQL row order, and naturally absorbs NULL-imbalance rows into Even without code-path asymmetry.

**Edge case:** If a game has spans qualifying as BOTH conversion (one class) AND recovery (another class), the first rule doesn't disambiguate. This is rare but real (e.g., user was +200 in KRP vs KP then traded into equal KP endgame that drifted to -200). Tiebreaker: prefer **Conversion** over Recovery, since reaching a winning position first is the earlier causal event. Planner should document this explicitly in code.

### 3. Backend removal scope → delete everything orphaned by the UI removal

Full removal list (researcher to verify no other consumers before planner writes tasks):

**Frontend (delete entirely):**
- `frontend/src/components/charts/EndgameGaugesSection.tsx`
- `frontend/src/components/charts/EndgameConvRecovTimelineChart.tsx`
- The `{isAdmin && (showPerfSection || showConvRecovTimeline) && (...)}` block in `Endgames.tsx` (lines 263-278 as of 2026-04-13) and its associated data hooks/queries.

**Backend schema (`app/schemas/endgames.py`) — remove fields from `EndgamePerformanceResponse`:**
- `aggregate_conversion_pct`, `aggregate_conversion_wins`, `aggregate_conversion_games`
- `aggregate_recovery_pct`, `aggregate_recovery_saves`, `aggregate_recovery_games`
- `endgame_skill`, `relative_strength`, `overall_win_rate`

Keep `endgame_wdl`, `non_endgame_wdl`, `endgame_win_rate` — these are still consumed by the main endgame section.

**Backend service (`app/services/endgame_service.py`):**
- Simplify `_get_endgame_performance_from_rows` by removing the orphaned aggregate computations.
- Keep `_aggregate_endgame_stats` for per-category output; only the top-level sums over categories go away.
- Remove the conv/recov rolling-window timeline function(s) and any router endpoint exposing only that data.

**Backend repository (`app/repositories/endgame_repository.py`):**
- Keep `query_endgame_timeline_rows` at its current 3-tuple return shape (`endgame_rows`, `non_endgame_rows`, `per_type_rows`). The per-type rows feed the surviving `EndgameTimelineChart` (per-class breakdown) and must NOT be dropped — this was corrected during planning after grepping the frontend.
- Remove `query_conv_recov_timeline_rows` (or whatever the conv/recov-only timeline function is named) and the rolling-window helpers it feeds, since those exclusively backed the removed admin section.

**Tests:** update/remove any tests asserting the deleted fields/columns. Add the new invariant test (decision #4).

**Planner responsibility:** before writing delete tasks, confirm via grep that no surviving component reads a field being removed. If a surviving consumer exists, flag it — do not silently keep the field.

### 4. Invariant test → unit test on `_compute_score_gap_material`

Add a test in `tests/test_endgame_service.py` with this shape:

- Construct synthetic `entry_rows` tuples + paired `endgame_wdl` / `non_endgame_wdl` `EndgameWDLSummary` objects covering:
  - Single-class-span games with clear conversion / even / recovery imbalances
  - Multi-class-span games where spans disagree (tests decision #2 priority rule including conversion-over-recovery tiebreak)
  - Games with NULL `user_material_imbalance` and NULL `user_material_imbalance_after` (tests decision #1)
  - Empty input (zero endgame games) — ensures no divide-by-zero and `sum == total == 0`
- Assert `sum(row.games for row in response.material_rows) == endgame_wdl.total` in each case.

**Why unit test over integration:** matches existing style in `tests/test_endgame_service.py` (101 tests there today), runs in milliseconds, and targets exactly the function whose invariant is being fixed. An integration test would add DB fixture overhead without catching anything the unit test misses — the bug is pure service-layer arithmetic.

### Folded todos

None — no pending todos matched this phase's scope.
</decisions>

<code_context>
## Existing Code Insights

- **Invariant-breaker today:** `_compute_score_gap_material` line 546-547 does `if user_material_imbalance is None: continue` inside the `seen_game_ids` loop. The combination of "skip null" + "dedupe by first-seen" means a game whose first SQL row has NULL imbalance is dropped entirely — even if another span for the same game has a valid imbalance. This is the root cause of `sum(material_rows.games) < endgame_wdl.total`.
- **Denominator is already well-defined:** `endgame_wdl` is built from `query_endgame_performance_rows`, which uses the same 6-ply threshold on `GamePosition.endgame_class IS NOT NULL`. Both sides of the invariant draw from the same game universe — no definitional mismatch to reconcile, just a per-game accounting bug.
- **Per-game dedupe pattern** was introduced in Phase 53 and kept by quick task 260413-pwv. The bucketing rule (4-ply persistence, conversion/even/recovery labels, `_MATERIAL_ADVANTAGE_THRESHOLD`) is settled. This phase only changes how NULL rows and multi-span games are resolved, not the thresholds.
- **`_aggregate_endgame_stats`** returns per-category conversion/recovery aggregates consumed by the surviving `EndgameConvRecovChart`. Only the top-level sums-of-sums currently computed in `_get_endgame_performance_from_rows` (lines 976-996) become orphaned by this phase.
- **`query_endgame_timeline_rows`** is dual-purpose: it returns both overall endgame rows (kept — fuels the main endgame timeline) and per-class `per_type_rows` (fed the removed conv/recov timeline). Trim in place rather than deleting the whole function.
- **Frontend `Endgames.tsx`** already has a clear `isAdmin` gate wrapping the section to remove (lines 263-278). Deletion is localized; no cross-cutting refactor needed.
</code_context>

<specifics>
## Specific Ideas

- **Dedupe implementation sketch** (decision #2): build `dict[game_id, list[row]]` from entry_rows, then iterate each game's rows looking for the first row satisfying the conversion OR recovery persistence condition; if none found, fall back to any row (which will bucket to "even"). This keeps O(N) time and avoids sort costs.
- **Conversion-over-recovery tiebreak** (decision #2 edge case): implement by scanning a game's rows conversion-first, then recovery-first, then fallback. Worth a code comment explaining the "earlier causal event" reasoning so a future reader doesn't invert it.
- **Schema deprecation risk** (decision #3): removing fields from `EndgamePerformanceResponse` is a breaking API change for any frontend component still reading them. Grep across `frontend/src/` before deletion — not just for literal field names but also for `data.aggregate_conversion`, `data.endgame_skill`, etc. Safer to do the deletion in one commit after confirming no other consumers remain.
- **Test fixture shape** (decision #4): existing tests in `tests/test_endgame_service.py` already construct synthetic `Row`-shaped tuples — reuse that pattern, don't invent a new builder.
- **Router / response-model updates** (decision #3): removing fields from `EndgamePerformanceResponse` will require corresponding updates in `tests/test_endgames_router.py` response-shape assertions. Planner should include this as part of the removal task rather than as a separate follow-up.
</specifics>

<deferred>
## Deferred Ideas

None surfaced during discussion. If research uncovers that additional endgame stats need the Conv/Even/Recov invariant enforcement (e.g., per-time-control breakdowns gain material buckets), those would be separate phases.
</deferred>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 59 definition (goal + 4 success criteria)
- `.planning/phases/53-endgame-score-gap-material-breakdown/53-CONTEXT.md` — origin of dedupe-per-game rule and material-stratified table design
- `.planning/quick/260413-pwv-implement-conversion-even-recovery-label/260413-pwv-SUMMARY.md` — locks in conversion/even/recovery labels, 4-ply persistence rule, and calls out the pending overlap this phase resolves
- `docs/endgame-analysis-v2.md` sections 1-2 — formulas and layout specs for Score Difference + Material Breakdown (still authoritative for the surviving section)
- `app/services/endgame_service.py:499` (`_compute_score_gap_material`) — primary edit site for decisions #1 and #2
- `app/repositories/endgame_repository.py:123` (`query_endgame_entry_rows`) — source of entry_rows, including NULL imbalance cases; no changes required here but researcher should read it
- `app/repositories/endgame_repository.py:480` (`query_endgame_timeline_rows`) — trim per_type_rows branch per decision #3
- `app/schemas/endgames.py` — `EndgamePerformanceResponse` field removals per decision #3
- `frontend/src/pages/Endgames.tsx:263-278` — admin-gated section to delete
- `frontend/src/components/charts/EndgameGaugesSection.tsx`, `EndgameConvRecovTimelineChart.tsx` — files to delete
- `tests/test_endgame_service.py`, `tests/test_endgames_router.py` — test files to update + where the new invariant test lands
</canonical_refs>
