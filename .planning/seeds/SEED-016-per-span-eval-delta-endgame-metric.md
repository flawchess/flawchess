---
id: SEED-016
status: scheduled
planted: 2026-05-15
scheduled_into: Phase 87.1 in v1.17 (INSERTED 2026-05-15) — see `.planning/milestones/v1.17-ROADMAP.md`
planted_during: /gsd-explore session on tightening per-endgame-type performance measurement (the conversation that motivated this seed lives in chat; key design points distilled below)
trigger_when: SCHEDULED — Phase 87.1 follows Phase 87 (per-type card layout). May still be deferred to v1.18 if scope-creep concerns dominate at plan-phase.
scope: phase (single, ~5-7 plans) — backend metric + repo query + per-type display alongside Conversion/Recovery + LLM payload + benchmark calibration of zones
depends_on: existing Stockfish eval backfill (Phase 81/82 — eval_cp / eval_mate at span-entry plies already populated), existing Lichess sigmoid utility (`app/services/eval_utils.py`), Phase 87 (per-type card layout)
related: [[SEED-015-predicted-vs-achieved-endgame-gap-as-first-class-metric]] (game-level analog of this idea), [[lichess-sigmoid-endgame-calibration]] (known caveat with the chosen sigmoid)
---

# SEED-016: Per-span expected-score delta as a per-endgame-type performance metric

## Why This Matters

Today the per-type tables on the Endgames page rely on three game-result-derived rates:

- **W/D/L** — game outcome, completely independent of where the span entered.
- **Conversion** — win rate in games where the user entered an endgame sequence of this type with eval ≥ +1.0.
- **Recovery** — save rate (W+D) in games where the user entered with eval ≤ −1.0.

These are useful aggregate rates but have three known weaknesses:

1. **Cohort thinning.** Conversion/Recovery condition on ±1.0 at entry, so for endgame types that are mostly "parity" entries (eval between ±1.0) the per-type cohort can be small. Many users see Conversion/Recovery for only 2-3 of the 6 endgame classes.
2. **Outcome noise.** Game result is a noisy proxy for how well the user actually played *during* that span. A user who enters a rook endgame at +1.0, drifts to +0.2 over 25 plies of inaccuracies, then re-emerges to win because the opponent blunders in a later phase, gets full Conversion credit for that rook span. The metric is correct as defined ("did you win the won game?") but it doesn't isolate per-span quality.
3. **Threshold cliff.** A user entering at +1.05 is in Conversion, at +0.95 is not — for a difference that's well inside Stockfish's noise floor.

A **per-span expected-score delta (ΔES)** addresses all three. It uses every span (not just ones crossing the ±1.0 threshold), measures eval movement *within* the span (not game outcome), and is continuous (no threshold cliff).

## The Metric

For each endgame sequence (span of ≥6 plies in one endgame_class, as already defined):

```
ΔES_span = ES_sigmoid(entry_eval, user_perspective) − exit_score
```

where:

- **`entry_eval`** — eval_cp / eval_mate at the first ply of the span (already in `game_positions`, surfaced by `query_endgame_entry_rows`).
- **`ES_sigmoid`** — Lichess winning-chances sigmoid, already imported via `app/services/eval_utils.py`.
- **`exit_score`** — defined by whether the span is transitory or terminal:
  - **Transitory** (followed by another span in the same game): `exit_score = ES_sigmoid(entry_eval_of_next_span, user_perspective)`. The transitioning move (e.g., the trade that ends the rook endgame and begins the pawn endgame) is attributed to the source span — which is correct, that move was a rook-endgame decision.
  - **Terminal** (last span in the game, ends with the game itself): `exit_score = game_result_score`, mapped from user-perspective W/D/L as 1.0 / 0.5 / 0.0.

The terminal case unifies cleanly with the transitory case: Stockfish eval at a terminal position (checkmate, stalemate, resignation) is effectively ±∞ or 0, which sigmoids to 1 / 0 / 0.5 — i.e., the game result score. **Same formula, different lookup.**

### Aggregation

Per (user, endgame_type): `mean(ΔES_span)` across all spans of that type.

- Positive mean = user gives back expected score over spans of this type (conversion failures, mistakes during defense).
- Negative mean = user gains expected score over spans of this type (good defense in losing positions, decisive conversion).
- Zero = user plays at Stockfish-baseline expectations.

### Properties worth noting

- **Drawn fortress at +1.0** → `ΔES ≈ +0.10–0.15` (penalty: should have converted). **Lost it** → much bigger penalty. **Won it** → bonus.
- **Recovered from −1.0 to draw** → `ΔES ≈ −0.10–0.15` (bonus: outperformed eval expectation).
- **Sigmoid saturation works in our favour**: at +5.0 the ES is ≈0.95, so converting +5 → +10 yields nearly 0 ΔES. The metric stops rewarding piling on a winning position — which is the correct property for a performance metric.
- **No threshold cliff**: a +0.95 entry and a +1.05 entry are treated nearly identically. Conversion/Recovery's discontinuity at ±1.0 is gone.
- **Conversion/Recovery are not replaced.** They answer the distinct "did you win the won game?" question and remain a useful outcome rate alongside ΔES. The two metrics complement each other.

## Known Caveat: Lichess Sigmoid Calibration

See [[lichess-sigmoid-endgame-calibration]] for the full discussion. Short version: the Lichess sigmoid was fitted across all analyzed positions (mostly middlegame); in the endgame, +1.0 is genuinely worth more winning chance than the sigmoid says. This means ΔES values are honest-as-defined but understated as a guide.

**Why this doesn't block V1:**

- The same sigmoid is applied to both endpoints — sign and ranking are preserved.
- Zone bands are percentile-based (sourced from the benchmark DB distribution of the metric itself, same pattern as `entry_expected_score` zones). If everyone's ΔES is compressed by ~30%, percentile placement is unchanged.
- The user-facing surface should be zones, not raw values. Raw value can appear in a tooltip with appropriate framing.

**Refit-on-endgame-data is a follow-up** (research question already filed): fit a logistic regression of game outcome on entry_eval *conditioned on being inside an endgame span* using benchmark data, possibly per endgame_class. Modest effort, real win if zones disagree with intuition.

## Open Details

- **Sub-threshold spans.** `ENDGAME_PLY_THRESHOLD = 6`. Spans shorter than 6 plies aren't surfaced as classifiable spans today. Stockfish evals exist for every position (eval is per-position, not per-span), so we could trivially lower the threshold for ΔES purposes if we wanted to capture short spans. Probably leave the threshold alone for V1 to keep the cohort definition consistent across metrics.
- **Span definition: codebase vs strict contiguous-run.** The existing `query_endgame_entry_rows` groups by `(game_id, endgame_class)`, collapsing all positions of the same class within a game into one logical span — even if the player exited the class and re-entered it later. A stricter "endgame sequence" definition (contiguous runs of the same `endgame_class`, computed via `ply - ROW_NUMBER() OVER (PARTITION BY game_id, user_id, endgame_class ORDER BY ply)` gaps-and-islands) yields ~5% more sequences (see eval-coverage check below). For ΔES this matters: under the strict definition, two consecutive sequences in the same game could share an `endgame_class`, making "next sequence entry eval" ambiguous as a performance signal (the player exited and re-entered the same type). V1 decision deferred — recommend defaulting to the codebase span definition for consistency with Conversion/Recovery, but flag at plan time.
- **NULL evals.** If `entry_eval` or `next_entry_eval` is NULL (engine error, not yet backfilled), exclude the span from the ΔES cohort. The Conversion/Recovery code routes NULLs to "parity"; ΔES has no equivalent fallback bucket. **In practice this is a non-issue** (see coverage check below).
- **Mate scores.** A mate score at either endpoint sigmoids to a saturated value via `eval_utils._signed_pawns_from_mate`-style handling. Use the existing convention (1_000_000 cp magnitude for sign-only) and let the sigmoid clamp.
- **Per-span vs per-move normalisation.** Considered and rejected for V1 (decision: keep per-span ΔES, simpler interpretation, matches game-level `entry_expected_score`). Revisit if zones look misleading on very short or very long spans.

## Eval Coverage Check (prod DB, 2026-05-15)

Confirmed eval availability is not a blocker. Snapshot of `game_positions` in prod:

| Definition | Length | Total sequences | With entry eval | Without | % covered |
|---|---|---:|---:|---:|---:|
| Codebase span (game × endgame_class collapsed) | ≥6 plies | 337,350 | 337,345 | 5 | 100.0% |
| | <6 plies | 69,348 | 66,507 | 2,841 | 95.9% |
| Strict contiguous run (gaps-and-islands) | ≥6 plies | 353,065 | 353,060 | 5 | 100.0% |
| | <6 plies | 89,676 | 86,199 | 3,477 | 96.1% |

Takeaways:

- **≥6-ply cohort is effectively 100% covered** under either definition (5 missing entries out of ~340k–350k; rounding noise from engine errors that didn't backfill).
- **Sub-6-ply sequences are also well-covered (~96%)**, so lowering `ENDGAME_PLY_THRESHOLD` for ΔES is feasible if desired.
- **Strict contiguous-run definition yields ~5% more spans** (~16k more ≥6-ply, ~20k more <6-ply). Whether to adopt it for ΔES is the open design call above.

## V1 Scope Sketch (when this trigger fires)

1. **Repo query**: extend `query_endgame_entry_rows` (or add a sibling) to include the *next* span's entry_eval per game, computed via window function over (game_id, span ply ASC). Terminal spans return NULL for `next_entry_eval`, and the service layer falls back to `game.result`.
2. **Service layer**: compute ΔES per span, aggregate per (user, endgame_class). Add to `EndgameCategoryStats` alongside Conversion/Recovery fields.
3. **Benchmark calibration**: regenerate per-class zones from `/benchmarks` (already supports per-endgame-class metrics).
4. **Frontend**: add a per-class ΔES gauge or column to the Endgame Type Breakdown table. Reuse existing zone-tile patterns.
5. **LLM payload**: wire into `insights_llm.py` under the `type_breakdown` section so endgame insights can reference per-type quality directly, not just game-result rates.
6. **Tests**: invariant — sum of W/D/L by terminal-span class should still equal endgame_games per type; ΔES on synthetic spans should match hand-computed values.

## Discarded Alternatives

- **Per-move CPL** (chess.com / lichess style): not unit-compatible with terminal spans (game result has no centipawn). Adds a parallel scale.
- **Raw centipawn delta** instead of expected-score delta: same problem at terminal spans, plus sigmoid-free numbers exaggerate large evals (going from +5 to +10 looks like a huge delta even though both are winning).
- **Replace Conversion/Recovery**: they measure a distinct question (outcome rate when ahead/behind) and remain valuable. Complement, don't replace.
