---
id: SEED-261112-f7q
status: dormant
planted: 2026-11-12
planted_during: Phase 252 plan 06 (D-05 flip measurement on prod, before the line repair)
trigger_when: Before any work that treats a single mistake/blunder label as ground truth (calibration, per-flaw training selection, "you blundered here" copy that hinges on one borderline eval), or when users report labels that changed after a re-analysis
scope: investigation first (small, read-only). A fix, if one is warranted, is unsized
---

# SEED-261112-f7q: Mistake and blunder labels flip in about a quarter of cases between two fresh searches

## Why This Matters

Phase 252's D-05 check asked whether the stored evals had drifted far enough from an exact search to change
mistake/blunder labels. It found the stored evals are about as good as a re-search, but it also measured how often
two fresh searches of the same game disagree with each other, and that number is large.

## Evidence (prod, read-only, 2026-11-12)

Report: `reports/line-repair/flips-prod-20261112T2000Z.md`. 199 engine-evaluated non-guest games (md5 order),
12,864 plies per arm, 0 failed searches, classified with `flaws_service._run_all_moves_pass`.

| Comparison | Mistakes and blunders | Flips | Share |
|---|---|---|---|
| Stored evals vs fresh exact search | 1,410 | 365 (lost 117, gained 146, mistake<->blunder 102) | 25.9% |
| Fresh exact search vs a second fresh exact search | 1,439 | 355 (lost 109, gained 140, mistake<->blunder 106) | 24.7% |

A 3-game dev smoke gave the same picture (0.333 vs 0.308).

## What is not known

- How close the flipped cases sit to the classification thresholds. In the dev smoke nearly all were borderline;
  this was not checked on the prod sample.
- How much of the noise comes from the measurement setup: the searches ran on the owner's box, and the control arm
  ran on a freshly started engine pool (empty hash). Prod labels come from a mix of MultiPV-1 and MultiPV-2 lanes
  on other hardware.
- Whether the flips matter to users: a flaw that is a mistake in one run and an inaccuracy in the next may be
  harmless in aggregate stats and still matter for per-flaw features.

## Questions to answer first

1. Distribution of the eval-loss margin to the nearest threshold for flipped vs stable labels.
2. Flip share as a function of search budget (nodes) and of hash state (warm vs cleared).
3. Which features read a single label as fact (training pool selection, blunder-check, tactic tags, narration)
   and which only use counts over many games.

## Possible directions (not decided)

- A dead band around each threshold so borderline cases do not get a label.
- A larger search budget only for positions near a threshold.
- Accepting the noise for aggregate stats and guarding only the per-flaw features.

## Notes

- Phase 252 kept its scope (lines only); the owner judged the flip share not material to the line repair.
- The 2% gate in `scripts/repair_short_lines.py measure-flips` cannot pass while the control share is this high;
  a gate on the excess over the control arm would be the meaningful form.
