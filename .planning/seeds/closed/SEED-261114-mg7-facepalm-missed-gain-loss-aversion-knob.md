---
id: SEED-261114-mg7
status: closed
closed: 2026-11-18
closed_reason: shipped as Phase 254 (missed gains and the lambda knob, releases up to #485); the material input was refitted again in Phase 256 (#486). Left open: the drill's loss-aversion weight (`FACEPALM_DRILL_LAMBDA` = 1.0, symmetric) waits for GM Noel Studer's answer; a constant change, no phase (254-CONTEXT D-03)
promoted_to: Phase 254
planted: 2026-11-14
planted_during: after Phase 253 (facepalm score in the library UI); owner review of low-scoring own blunders
trigger_when: when the facepalm score or blunder-check selection is next worked on, or once the owner has GM Noel Studer's view on loss aversion in blunder-check training. Not before Phase 252 (line repair) concludes, since the new feature reads the stored best line
scope: medium. New material feature from stored lines (no engine), pre-blunder Maia inputs with a backfill about the size of Phase 250's, about 50 new miss labels, a refit, and a selection weight
---

# SEED-261114-mg7: Facepalm score ignores missed gains; add a loss-aversion knob

The facepalm score is predictive when high but not when low: obvious missed wins of material score near 0. Add
missed gain to the score, with a weight (the "loss-aversion knob") that each consumer can set.

## Why This Matters

The score's three inputs all describe what the played move gives away. A move that loses nothing but passes up
a free piece gets loss 0 and a high reply spread (no forced punishment exists), so it scores low however
obvious the better move was. Owner examples (dev DB, user 28), both scored 2%:

- game 817357 ply 24: Ba3 instead of Qxg7, which wins the h8 rook.
- game 820181 ply 65: Rxf5 (wins 5) instead of Qxh1 (wins 10).

## Evidence (2026-11-14)

Missed vs allowed hanging pieces, user-side blunders, tactic depth <= 2:

| | n | median score | >= 0.70 | loss at depth 3 | best-line gain at depth 3 | swing | median spread |
|---|---|---|---|---|---|---|---|
| Allowed (dev, user 28) | 169 | 0.97 | 86% | 3.65 | 0.68 | 4.12 | 1.85 |
| Missed (dev, user 28) | 39 | 0.34 | 18% | 0.56 | 4.36 | 4.46 | 3.39 |

Prod, all users: 132k allowed at 88% >= 0.70 vs 27.7k missed at 21%.

- The material at stake is the same; the model only sees the loss half.
- Maia played probability is similar (0.05 vs 0.08), so it is not the cause.
- Reply spread penalises misses: with no forced punishment, many replies are plausible.
- Swing in place of loss with the current coefficients (no refit): missed >= 0.70 goes from 18% to 79%, allowed
  stays at 87%, all blunders go from 27% to 40%. Direction only; the coefficients and cut need a refit.

Gain was computed by running `line_facts` on the stored best line (`game_positions.pv` at the flaw ply: first
token as the move, the rest as the line). No engine, no Maia.

## Decisions (owner, 2026-11-14)

1. **The knob is wanted regardless** of how the loss-aversion question is answered.
2. **Whether blunder-check training should be loss-averse is open.** The owner will ask GM Noel Studer. The
   drill now asks "Good move or blunder?" (not "is the move safe?") so that the player also looks for gains;
   missed gains are therefore valid drill items.
3. **Add Maia inputs for the pre-blunder position** (owner: "we probably should").

## Proposed Shape (not decided)

- **Two material numbers instead of one:** `loss` as today (played line, depth 3, floored at 0) and `missed`
  (swing minus loss: what the best line wins on top). Score input `loss + lambda * missed`; lambda = 0 is
  today's score, lambda = 1 the symmetric swing. Swing = material after the best line minus material after the
  played line, both at depth 3.
- **Lambda per consumer** through the SQL score expression: symmetric for the library chip and filter, the
  owner's choice for blunder-check selection.
- **Pre-blunder Maia inputs:** Maia's probability of the best move (how findable the gain was; the counterpart
  of reply spread for misses; this is the `maia_best_prob` dropped in Phase 250 D-11) and the pre-blunder
  policy spread. Both come from the policy call that yields `maia_played_prob`; verify the hook still has the
  full policy at that point. Existing rows need a backfill.
- **Labels and refit:** the 180 labels of 2026-11-13 are mostly loss-type (17 no-loss rows labelled fair, no
  input to separate them). Label about 50 misses, including the two examples above, then refit and recheck
  `FACEPALM_SCORE_MIN` and the drill pool size. The labelled games are not in the dev DB; pull their best lines
  from prod.

## Open Questions

- Loss-aversion weight for blunder-check selection (pending GM Noel Studer).
- Whether best-move probability and pre-blunder spread each earn a coefficient, or swing alone is enough.
- Whether reply spread should be dropped or down-weighted for pure misses.

## Related

- Phase 250 (facepalm score, D-01, D-11), Phase 253 (library UI), SEED-261114-iuv (facepalm rate in stats).
