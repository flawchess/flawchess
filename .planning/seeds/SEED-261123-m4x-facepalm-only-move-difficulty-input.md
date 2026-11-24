---
id: SEED-261123-m4x
status: dormant
planted: 2026-11-23
planted_during: ad-hoc analysis of one blunder after the 2026-11-23 release (no active phase)
trigger_when: the blunder-check exploration arm (Phase 261, EXPLORATION_SHARE 0.2) has enough outcomes to carry one extra coefficient, or at the next facepalm refit, whichever comes first
scope: small analysis first (no code); medium phase only if the analysis says the input earns its place (new write-time input, prod line pass, refit)
---

# SEED-261123-m4x: Does the facepalm score need a "how likely was any mistake" input?

The facepalm score rates an only-move blunder as very careless when the refutation wins a lot of
material. Test whether a Maia-based difficulty input fixes that, once there is enough data to tell.

## Why This Matters

Prod game 1555615, ply 80 (https://flawchess.com/analysis?game_id=1555615&ply=80): White (1516,
blitz) plays `a4`, the only move was `Rd6` (a gem), every alternative is a blunder. The analysis
board shows a 68% Maia chance of blundering. The facepalm score is 83%.

| Term | Contribution to z |
|---|---|
| Intercept | -1.79 |
| Played prob 0.077 | +1.51 |
| Material loss 4.0 | +3.55 |
| Reply prob 0.119 (allowed loss, so the reply is the key move) | -1.65 |
| z | +1.63, score 0.836 |

Two things read the position wrong:

- The loss term cannot tell "walked into it" from "failed to find the only defence". The threat
  existed before the move and nearly every move loses the same material.
- The played-move term adds score for an unlikely move. In an only-move position every wrong move
  is individually unlikely while a wrong move overall is likely.

No stored column holds the Maia mass on losing moves. `maia_pre_spread` was tested on 2026-11-15
and dropped. Reading `maia_best_prob` on allowed-loss rows does not help either (it gives about
86% here, and its coefficient on allowed-loss label rows fits near zero).

## What Was Tested (2026-11-23)

Stockfish depth 14 over all legal moves plus the Maia policy at the pinned Elo, for every row of
`reports/blunder-check/facepalm-features-2026-11-23.tsv`. Each candidate was added as one extra
term to the shipped shape and refitted on the 268 usable labels (10-fold CV, 5 seeds):

| Extra term | CV AUC, all | CV AUC, allowed loss |
|---|---|---|
| None (shipped) | 0.891 | 0.852 |
| Maia mass on blunders (ES loss >= 0.15) | 0.891 | 0.848 |
| ln(1 - mass) | 0.890 | 0.845 |
| Maia-weighted expected ES loss | 0.889 | 0.848 |
| Played ES loss minus expected ES loss | 0.892 | 0.855 |
| Maia mass on moves as bad or worse than the played one | 0.898 | 0.866 |
| loss x mass | 0.888 | 0.842 |

Seed spread is about 0.005, so nothing is settled.

- Alone, blunder mass separates the labels (fair share 69% in the lowest quartile, 28% in the
  highest), but the shipped inputs already carry most of it.
- Expected ES loss is no better than plain mass.
- The relative form ("what share of peers would do as badly or worse", ES loss >= played loss
  minus 0.05) is the only one that helps on allowed-loss rows.
- Only 16 allowed-loss label rows have a blunder mass of 0.6 or more: 8 fair, 8 unfair, against
  71% fair for all allowed losses. Consistent with the intuition, far too few to fit.

For the position above the script gives a blunder mass of 0.72 with exactly one acceptable move.

## Decision (owner, 2026-11-23)

Do not act on 268 labels. Revisit when the exploration arm has collected enough data.

## What To Do When Triggered

1. Count first. Among exploration-arm blunders with an outcome, how many are allowed losses with a
   high blunder mass? That cell decides the question. As a rough bar (my suggestion, not an owner
   decision), wait for at least 100 of them.
2. Compute the candidates for those positions and compare against the shipped shape, with the
   catch outcome as the target instead of the owner's fair / unfair labels. Start with the relative
   form, then plain mass.
3. Judge by first principles and the only-move cell, not by a small overall AUC gain (the labels
   and outcomes are both noisy).
4. Only if an input earns its place: plan the phase. It needs per-move engine evals at the flaw
   position at write time, a stored scalar on `game_flaws`, a prod line pass and a refit of both
   score twins.

## Cost Notes

- The measurement took about 7 s per position at depth 14, multipv over all legal moves, 12 threads.
  A prod-wide backfill at that cost is not realistic; a write-time input needs a cheaper recipe
  (lower depth, or only the moves covering most of the Maia mass).
- The throwaway scripts and the per-row table are in gitignored `temp/blunder-check/maia-mass/`
  (`mass.py` computes, `fit2.py` compares). They may be gone; both are short to rewrite.

## Related

- SEED-261122-k7f (only-move gate drops real geometric tactics): a different only-move question.
- `app/services/facepalm_score.py`, `app/services/blunder_check_rules.py` (FACEPALM_* constants),
  `scripts/blunder_check/fit_facepalm.py`, `scripts/blunder_check/caught_rate.py`.
