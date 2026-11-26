---
id: SEED-261121-tau
status: closed. Milestone v2.31.
closed: 2026-11-22
closed_reason: shipped as Phase 259 (quiet-point material rule, reply probability on losing rows, refit; releases #497, #498, #499; drill cut 0.70). Successor: SEED-261122-s0j (promotions as material)
promoted_to: Phase 259 (2026-11-21)
planted: 2026-11-21
planted_during: owner review of one facepalm score on prod (game 2883555, ply 47), outside any phase
trigger_when: the next facepalm score refit, or any phase that touches the stored line material or the Maia facepalm columns. Best after the Phase 252 short-line repair has finished, since the material recompute reads the same lines
scope: medium. One new game_flaws column with a re-inference backfill, a recompute of the stored line material, a new material input, one refit
---

# SEED-261121-tau: Facepalm score refit on first principles (best-reply probability, quiet-point material)

Two changes to the facepalm score model that need the same refit.

**Promoted 2026-11-21 to Phase 259** (`.planning/ROADMAP.md`, Active Phases).

## Part 1: Maia probability of the best reply

Add a stored `maia_best_reply_prob` column on `game_flaws`: Maia's probability, at the blunderer's
pinned Elo, of the engine's best reply to the blunder (the first move of `game_positions.pv` at
flaw ply + 1).

- Missed wins already have two inputs for "how findable was it": `maia_best_prob` and
  `maia_pre_spread`. Allowed losses only have `maia_reply_spread`. The new column makes the two
  types symmetric.
- The reply spread is a proxy. It measures how spread out Maia's replies are, not how likely the
  punishing move is.
- Cost: the reply-spread inference (`_derive_reply_spread` in `app/services/maia_flaw_scoring.py`)
  already computes the full policy on the post-blunder board, so the value is free going forward.
  Existing rows need a re-inference backfill, because the policy is not stored.
- Let the fit decide whether the reply spread stays. The pre-blunder spread fitted to a coefficient
  of exactly 0 once the best-move probability was in the model.

## Part 2: Quiet-point material input

Replace the `decaying_mean` material input with one that reads material only at quiet points.

- Defect of the current input: each odd-depth slot is a snapshot after the opponent's ply plus one
  recapture by the blunderer. That settles a two-capture exchange, not a longer chain. Any weighted
  mean of snapshots carries the transient spike, whatever the weights. (The decay already steps in
  ply-pairs: only the odd depths 1, 3, 5, 7, 9 are read.)
- First-principles requirement (owner): an equal exchange of any length is exactly neutral, and a
  recapture is not weighted less because it comes a ply later.
- Proposed shape: split the two things the decaying mean mixes.
  1. Settled value: material of the played and the best line at quiet points only (the next line
     move is not a capture).
  2. Onset: how many plies until the settled value appears, as a discount. A loss that materialises
     at ply 7 is harder to see than one at ply 1.
- The stored 9-slot arrays do not record which plies are captures, so this needs a recompute of the
  stored line material (`app/services/line_material.py`).
- The existing `first_stable` input is a rough version (first odd-depth value the next odd depth
  confirms). It gives a missed gain of 0 on the motivating row but lost the Phase 256 refit.
- Cheap fallback from the stored arrays, if the recompute is too costly: gain at depth d = minimum
  of depths d and d + 2. A patch on the snapshot model, not a clean rule.

## Owner decision (2026-11-21)

Choose the material input that makes the most sense from first principles. Only require the AUC to
stay in a similar range as the current fit (decaying_mean: cross-validated AUC 0.902, set-8 AUC
0.821; `reports/blunder-check/facepalm-fit-2026-11-16.md`). Do not pick by small AUC differences:
the 261 labels are the owner's own and very subjective.

Later, once enough user blunder-check answers exist, consider a data-driven fit. Known limit: the
drill serves scores of 0.50 and above (`FACEPALM_SCORE_MIN`) while the facepalm definition is 0.70
and above (`FACEPALM_STATS_MIN`), so answers straddle the cut, but nothing below 0.50 is observed.

## Motivating case

Prod game 2883555, ply 47 (24...Kd7), rapid, about 1775 Elo. Score 0.918.

| Term | Input | Contribution to z |
|---|---|---|
| Intercept | | -1.22 |
| Played-move probability | Maia 3.0% for Kd7 | +1.96 |
| Reply spread | 7.35 effective replies (91st percentile of user 28's blunders, median 3.26) | -2.66 |
| Material loss | 2.94 | +3.42 |
| Missed gain | 2.58 | +0.91 |

- The best move was Bxf4, and Bxf4 Qxf4 Qxf4 Rxf4 is an even trade, but `best_line_material` is
  `[9, 9, 0, 0, ...]`: depth 1 counts the blunderer's Qxf4 and not White's Rxf4. The missed gain of
  2.58 is spurious; the score is 0.82 without it.
- The punishing move Nxe6 has a Maia probability of 21% and is marked as a gem.
- About 5.6% of user 28's scored blunders (n = 21,121) show a depth-1 best-line gain of 3 or more
  that is gone by depth 3.

## Breadcrumbs

- `app/services/facepalm_score.py`, `app/services/facepalm_material.py` (score twins, aggregates)
- `app/services/blunder_check_rules.py` (FACEPALM_* constants, `MATERIAL_DECAY_RATIO`)
- `app/services/line_material.py` (9-slot arrays, recapture lookahead rule)
- `app/services/maia_flaw_scoring.py`, `app/services/maia_flaw_stats.py` (reply spread inference)
- `scripts/blunder_check/fit_facepalm.py`, `reports/blunder-check/facepalm-fit-2026-11-16.md`
- Related seeds: SEED-261120-bzq (facepalm benchmark zones), SEED-261112-s4v (Phase 252 line repair)

## Related gap, not part of this refit

The same row has no allowed tactic tag. `detect_sacrifice` (`app/services/tactic_detector.py`) only
follows material along the engine line, where Black declines the knight (Nxe6 f4 Nxc7 Kxc7), so an
offered sacrifice the engine declines is invisible to it. A new condition would need checking
against the precision fixtures.
