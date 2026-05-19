# Lichess sigmoid — endgame calibration caveat

Source: /gsd-explore session 2026-05-15 on per-span ΔES as a per-endgame-type performance metric ([[SEED-016-per-span-eval-delta-endgame-metric]]).

Captured separately so the caveat surfaces independently when anyone searches for sigmoid-related calibration questions — not buried inside SEED-016.

## The Issue

The Lichess winning-chances sigmoid (currently used by `app/services/eval_utils.py` and the `entry_expected_score` metric from Phase 81/82) was fitted across the full distribution of Lichess-analyzed positions. That distribution is dominated by middlegame positions, where tactical counter-chances and complexity mean +1.0 is a moderate edge.

In the **endgame**, a +1.0 advantage is genuinely worth more winning chance:

- Lichess sigmoid: `ES(+1.0)` ≈ 0.60
- True endgame win rate at +1.0 entry (from our benchmark DB): rook ≈ 0.70+, queen ≈ 0.80+ (rough — confirm in research).

The sigmoid **systematically under-weights endgame eval advantages**.

## Where The Distortion Bites

| Use of the sigmoid | Distorted? | Severity |
|---|---|---|
| Ranking users by mean ΔES | No — same sigmoid both endpoints; ordering preserved | None |
| Percentile-based zone bands (calibrated from benchmark distribution of the metric itself) | No — distortion is in the metric definition, not the zone calibration | None |
| Absolute interpretation ("you gave back 0.15 expected-score points this span") | Yes — true cost in endgame-conditional win-probability terms is larger | Moderate |
| Cross-metric comparisons (e.g. `entry_expected_score` vs ΔES "should add to game-level outcome") | Yes — both use the same biased sigmoid so the bias cancels in differences, but absolute levels are off | Low |

## Mitigation In V1

- Calibrate zones from benchmark percentiles (matches `entry_expected_score` pattern).
- Display zones, not raw values, on the primary surface.
- If raw values appear (tooltip, drill-down), frame as "expected score points lost" — honest-as-defined, even if scale-compressed.

## Refit Option (Follow-up)

We have the data to do better. The benchmark DB (`flawchess-benchmark-db`) holds millions of Lichess games with per-position Stockfish evals (`backfill_eval.py --db benchmark`). We can:

1. Filter to positions inside endgame spans (`endgame_class IS NOT NULL`).
2. Pair each such position with the eventual game outcome from the user's perspective.
3. Fit a logistic regression of `outcome ∈ {1, 0.5, 0}` on `eval_cp` (clipped at ±2000 cp like the existing `EVAL_CLIP_MAX_CP`).
4. Optionally fit per `endgame_class` (rook / minor_piece / pawn / queen / mixed / pawnless) — the per-class calibration would matter most for queen (very steep) vs pawn (very flat).

Modest effort. Real win if zone placement starts disagreeing with player intuition. Tracked as a research question in `.planning/research/questions.md`.

## Glossary Implications

If/when we adopt an endgame-specific sigmoid, the user-facing definitions of `entry_expected_score`, `ΔES`, and any other ES-derived metric should switch atomically. Half-converted state ("entry uses Lichess sigmoid, ΔES uses endgame sigmoid") would silently break the property that `ΔES + outcome_delta ≈ 0` at the population level. Keep the cutover in lockstep across backend metric, frontend tile, LLM glossary entry, and prompt version bump.
