---
id: SEED-203
status: dormant
planted: 2026-10-17
planted_during: sketch 012 (Openings Stats redesign). The "After the opening" column was dropped from Openings; the refit it needed moves here
trigger_when: next Endgames milestone, or whenever the "Do you keep your entry advantage?" card or the Eval Score Gap narration is touched
scope: medium; one phase (benchmark table generator + app/benchmark SQL twins in lockstep + zone recalibration + prompt rewrite)
---

# SEED-203: Elo × TC refit of the eval → expected-score curve for Endgames

## Problem

Every "actual vs expected score" metric on the Endgames page converts the entry eval with the Lichess
sigmoid `1 / (1 + exp(-0.00368208 * cp))` (`LICHESS_K`, `app/services/eval_utils.py`). Lichess fitted
that K on 75k positions from **2300+ rated rapid games** (lila PR #11148). Club players convert far less
of an advantage, and bullet players much less than classical players at the same Elo. So the Eval Score Gap
is mostly a rating and TC tilt, not a skill signal. The LLM prompt (`app/prompts/endgame_insights.md`)
spends a lot of words working around this ("vs the 2300+ baseline", "rating-tilt for sub-2300 users",
a list of forbidden framings like "underperformance").

The comparison is worth more at endgame entry than at the opening exit, since the entry is close to the
end of the game and the eval predicts the result better (higher fitted K, see below). That is why the
refit lives here and not on Openings.

## Evidence (benchmark DB, 2026-10-17)

10% sample of the benchmark DB (`games.id % 10 = 0`, 276k games, Lichess only), first `phase = 2` ply
with a cp eval (no mate), `|cp| < 1000`, `|elo diff| <= 400`. Fractional-logit MLE without an intercept:
`logit E[score] = K·cp_user + D·(user_elo − opp_elo)`. Scripts and outputs (gitignored, rerun to
reproduce): `temp/opening-redesign/fit_k.py` (K only, opponents within ±100), `fit_kd.py` (K and D),
`fit_check.py` (calibration by cp bucket), `kd_table.json`, `bench_sample.csv`.

**K at endgame entry** (from `fit_kd.py`; n per cell 822 to 25,264 in the 10% sample):

| Elo | Bullet | Blitz | Rapid | Classical |
|---|---|---|---|---|
| <1200 | 0.00104 | 0.00208 | 0.00253 | 0.00271 |
| 1200–1600 | 0.00127 | 0.00271 | 0.00307 | 0.00322 |
| 1600–2000 | 0.00157 | 0.00297 | 0.00385 | 0.00395 |
| 2000+ | 0.00217 | 0.00364 | 0.00424 | 0.00501 |

D (per Elo point of rating gap) is 0.0021 to 0.0042, below the pure Elo rate of 0.00576 because the eval
already captures part of the strength gap.

- **Method check:** the 2000+ rapid cell at middlegame entry fits 0.0038, next to Lichess's 0.0037
  for 2300+ rapid.
- **Size of the error:** at +3.5, Lichess predicts 78%; 1200–1600 blitz actually scores about 72% at
  endgame entry, and under-1200 bullet about 59%.
- **TC matters more than Elo:** bullet K is about 40–50% of rapid K at the same Elo (the
  time-pressure effect).
- **Phase matters:** in blitz, rapid and classical, K at endgame entry is 15–30% higher than at
  middlegame entry (same cells); in bullet it is about the same. The two phases need separate tables.
- **Fit quality:** a one-parameter logistic per cell tracks actual scores within about 3 points across
  the eval range (`fit_check.py`, checked at middlegame entry). Some S-shape misfit remains in the tails.

## Proposed approach

1. **Generated table.** A `scripts/gen_*` step (or a benchmark chapter) fits K (and D if needed) per Elo
   bracket × TC at endgame entry on the full benchmark DB and writes a committed constants module. It is
   refreshed with the benchmarks. Shard by `md5(id) % n`, not by rank windows (the benchmark DB grows
   during backfills).
2. **Rating scale.** The benchmark is Lichess only. Convert chess.com ratings with
   `app/services/chesscom_to_lichess.convert_chesscom_to_lichess` before picking a bracket. Interpolate
   K between bracket centres so 1590 and 1610 do not jump.
3. **Per game, not per mean.** Evaluate the curve with each game's own Elo, TC and rating gap, then
   average. The ranked endgame sample is already within ±100 Elo, so D may be droppable there (decide
   from data: fit with and without, compare calibration).
4. **Twins in lockstep.** The expected score exists in both the app and the benchmark SQL:
   - `app/services/endgame_ranked_service.py` `_achievable_expected` (the card's entry flow,
     `d_i` = score − expected).
   - `scripts/benchmarks/sql.py` `LICHESS_WIN_CHANCES_K` and the `per_user_cte_achievable_tc` CTE.
   - `app/services/canonical_slice_sql.py`, `app/services/user_benchmark_percentiles_service.py`.
   - The per-span "Endgame Type Score Gap" (`endgame_type_achievable_score_gap`), which uses the same
     sigmoid.
   Then recalibrate the zone bands and percentiles that are built on these numbers (benchmark §5).
5. **Prompt.** Rewrite the Eval Score Gap and Entry Eval Score sections of
   `app/prompts/endgame_insights.md`. With a peer baseline, the "2300+ baseline / rating-tilt" caveats
   and the forbidden-framing list largely go away, and a negative gap becomes a real signal.

## Out of scope / guardrails

- **Move-quality uses of `LICHESS_K` stay on Lichess.** These are flaw classification
  (`gen_flaw_thresholds_ts.py`), `train_pool`, `best_move_candidates`, `forcing_line_gate` and
  `eval_drain`. They measure drops in win chance, and changing them would reclassify stored data.
- **Mate handling unchanged** (1.0 / 0.0). The current |cp| clip at 2000 vs the fit's 1000: decide
  whether the fit range needs widening.
- **Openings does not use this** (sketch 012 dropped "After the opening"). The middlegame-entry K table
  from the same scripts is there if Openings ever wants it.
- **Eval ply convention.** Some benchmark eval_cp rows are lichess post-move and others are aligned to
  the entry ply (see the eval_cp ply-convention memory). Check that the fit is not sensitive to it
  before trusting cell-level differences.
