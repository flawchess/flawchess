# Phase 254: Facepalm Score Missed Gains and Loss-Aversion Knob (SEED-261114-mg7) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-14
**Phase:** 254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-261114-mg7
**Areas discussed:** Where lambda lives, Model form for misses, Refit sequencing, Miss labels

---

## Where lambda lives

| Option | Description | Selected |
|--------|-------------|----------|
| Query-time expression | Store only facts; every consumer calls the SQL score with its lambda; refit is a constants deploy | ✓ |
| Two stored scores | Symmetric column for the library plus a second column at the drill's lambda | |
| Stored endpoints, blend at read | Store lambda=0 and lambda=1 scores, interpolate | |

**User's choice:** Query-time expression.

| Option | Description | Selected |
|--------|-------------|----------|
| Drop the stored column in this phase | Last human-gated plan, like 250-11 | ✓ |
| Keep it, stop reading it | Rollback path, drifts after the refit | |
| Keep it as the symmetric score | Library reads stored, drill uses the expression | |

**User's choice:** Drop it in this phase.

| Option | Description | Selected |
|--------|-------------|----------|
| Drill lambda 1.0 symmetric | Misses are valid drill items; lower if Noel says loss-averse | ✓ |
| 0 until Noel answers | Drill unchanged | |
| 0.5 in between | A guess | |

| Option | Description | Selected |
|--------|-------------|----------|
| Library lambda 1.0, own constant | Separate from the drill constant | ✓ |
| Same constant as the drill | One lambda for everything | |

**Notes:** The owner later asked whether dropping the stored score hurts the library filter. Measured on dev (user
28): stored column 38 ms, expression 25 ms, same plan.

---

## Model form for misses

| Option | Description | Selected |
|--------|-------------|----------|
| Fit script compares both | One material coefficient vs separate loss and missed coefficients, pick by CV AUC and fair share | ✓ |
| One coefficient on loss + lambda*missed | Symmetric by construction | |
| Separate loss and missed coefficients | Labels decide the weight | |

| Option | Description | Selected |
|--------|-------------|----------|
| Let the fit decide among named forms | Spread as today; only when loss > 0; replaced by best-move probability for misses | ✓ |
| Spread only counts when there is a loss | Hard rule | |
| Keep spread as is | No special case | |

| Option | Description | Selected |
|--------|-------------|----------|
| Store both Maia inputs, each must earn its coefficient | Best-move probability and pre-blunder spread | ✓ |
| Store both, both in the score | Always fitted | |
| Best-move probability only | One column | |

**Line facts storage** (asked as: mirror the five loss columns / depth 3 only / you decide). The owner asked
whether two columns (a depth and a signed material change) would do, then asked for symmetric storage with fewer
columns than six per side.

| Option | Description | Selected |
|--------|-------------|----------|
| Arrays, depths 1 to 9 | One SMALLINT[] per side plus a mate ply per side | ✓ |
| Arrays, the five current depths | Same shape, smaller | |
| Scalar, depth 3 only on both sides | Drop the other depths | |

**User's choice:** Arrays with depths 1 to 9.
**Notes:** One signed number cannot work because loss and missed come from two different lines and lambda weights
them separately. The owner confirmed the reading: one array for the best line from the pre-blunder position, one
for the opponent's best reply line after the blunder. Sign convention proposed by Claude (positive = blunderer up),
not objected to. The owner also asked whether forcing matters as in tactic tagging: answer was no flag now, with a
named fallback.

---

## Refit sequencing

| Option | Description | Selected |
|--------|-------------|----------|
| Fold 250-10 into 254 | One refit on repaired lines | ✓ |
| Keep 250-10 separate, run it first | Two refits | |

| Option | Description | Selected |
|--------|-------------|----------|
| Build all, behaviour unchanged until the refit | Maia pass can run now; line pass, refit, column drop wait for 252 | ✓ |
| Also ship an interim fit on unrepaired lines | Two refits | |
| Wait: only discuss and plan now | No code until 252 finishes | |

| Option | Description | Selected |
|--------|-------------|----------|
| Owner checkpoint, same policy | Cut picked by the owner from the fit report, below the precision-optimal cut | ✓ |
| Match today's precision | Planner picks | |
| Match today's pool size | Keep supply constant | |

---

## Miss labels

| Option | Description | Selected |
|--------|-------------|----------|
| Mostly pure misses, stratified | About 40 pure misses over missed size and best-move probability, about 10 mixed | ✓ |
| Pure misses only | Random above a minimum gain | |
| Around the cut | Scores 0.4 to 0.9 | |

| Option | Description | Selected |
|--------|-------------|----------|
| Prod, all users, movers below 2000 | Same population as the 180 labels; repaired or never-short lines only | ✓ |
| Own games (user 28) | Dev, one player | |
| Prod, including 2000+ | No strong-player labels | |

| Option | Description | Selected |
|--------|-------------|----------|
| Old labels stay in the fit, on top of the 50 | About 230 labels | ✓ |
| The 17 no-loss rows count toward the 50 | About 33 new rows | |

---

## Claude's Discretion

- Column names, the missed-mate value, whether the missed term has its own cap, the minimum gain defining a miss
  for sampling, backfill shards and pacing, API shape, extent of the calibration and spot-check re-run.

## Deferred Ideas

- Drill lambda below 1.0 (pending GM Noel Studer), forcing flag, rating-dependent depth and labels above 2000,
  refit from drill answers, facepalm rate in stats (SEED-261114-iuv).

## Todo matches

- Four keyword matches from `todo.match-phase` (172 deferred review findings, bitboard storage, WR-01 Tailwind
  class, variation-tree nested button) were unrelated to the phase and not presented for folding.
