# Report-only analysis: CPU-normalized throughput (Phase 226 gate)

**Date:** 2026-10-01
**Status:** Report-only (accept-rule §5 lists "grade CPU ratios ... alongside every throughput
criterion" as report-only). This document does NOT change any criterion, threshold or verdict.
It exists so the owner can judge the mechanical verdict against what the data shows once
machine-speed drift is separated from code effects.
**Source:** the committed ladder rows under `reports/data/engine-throughput-226/{step0,gate/*}/throughput/`,
the same `_ladder_rows` selection `evaluate_throughput_pair` judges.

## Finding

Wall time in these runs tracks how fast the machine was during each run more than it tracks the
code. At a fixed node budget the arms do the same work: A0a, A2 and A21 issue identical grade
counts (800 or 6400 per config) at identical nodes, and A21S adds only the 1-45 extra shard
grades. Yet the Stockfish CPU cost of one grade varies run to run from 130 to 228 ms at t400-p4.
The root guard (A21) cannot cause that. It only changes when the bot's stop rule fires, which
these fixed-budget runs do not use. On the six t400-p4 positions where A21 was slow (sharp,
endgame, C50, C30, B50, B90), grade counts match A2 exactly and per-grade CPU is about 2.7x.
That is machine state (frequency scaling, thermals or background load below the load-average
gate), not engine work.

Dividing wall time by total grade CPU gives a pipeline-efficiency figure: how much wall time
the scheduler needs per unit of Stockfish work. That is the quantity the underfill fix and the
root split are meant to improve. It is stable across runs and moves only with the code.

| Config | Arm | Wall (s) | Wall vs A0a | CPU per grade (ms) | Wall / grade CPU | Normalized vs A0a |
|---|---|---|---|---|---|---|
| t50-p4 | A0a | 100 | 1.000 | 172 | 0.724 | 1.000 |
| t50-p4 | A2 | 103 | 1.038 | 188 | 0.688 | 0.950 |
| t50-p4 | A21 | 100 | 1.001 | 182 | 0.684 | 0.946 |
| t50-p4 | A21S | 97 | 0.970 | 174 | 0.658 | 0.909 |
| t400-p4 | A0a | 615 | 1.000 | 130 | 0.742 | 1.000 |
| t400-p4 | A2 | 610 | 0.992 | 139 | 0.684 | 0.922 |
| t400-p4 | A21 | 992 | 1.613 | 228 | 0.680 | 0.916 |
| t400-p4 | A21S | 630 | 1.024 | 144 | 0.680 | 0.916 |
| t50-p2 | A0a | 107 | 1.000 | 164 | 0.811 | 1.000 |
| t50-p2 | A2 | 105 | 0.983 | 169 | 0.777 | 0.958 |
| t50-p2 | A21 | 140 | 1.311 | 222 | 0.788 | 0.972 |
| t50-p2 | A21S | 105 | 0.986 | 170 | 0.757 | 0.934 |
| t400-p2 | A0a | 696 | 1.000 | 74 | 1.476 | 1.000 |
| t400-p2 | A2 | 783 | 1.125 | 84 | 1.462 | 0.991 |
| t400-p2 | A21 | 746 | 1.071 | 80 | 1.454 | 0.986 |
| t400-p2 | A21S | 708 | 1.017 | 76 | 1.461 | 0.990 |

## Reading

- **Underfill fix (A2 vs A0a):** 5-8% less wall per unit of work on the desktop pool (t50-p4,
  t400-p4), 4% at t50-p2, and about 1% at t400-p2. The gate's only failed underfill config,
  t400-p2 at 1.125, has the same pipeline efficiency as A0a (0.991). Its extra wall time matches
  its 13% higher per-grade CPU, so it is a slower machine on gate day (A0a was measured on
  2026-09-28, A2 on 2026-09-29), not slower code.
- **Root guard (A21 vs A2):** no throughput effect, as designed (0.99-1.02 normalized). The large
  raw wall ratios at t400-p4 (1.61) and t50-p2 (1.31) are entirely per-grade CPU drift.
- **Root split (A21S vs A21):** about 4% at t50-p4, where the round-1 root grade is the largest
  share of the search; 2-4% at t50-p2; nothing at 400 nodes. The gate's raw t400-p4 ratio of 0.63
  is the A21 drift reversing, not a split gain.
- **Whole stack (A21S vs A0a):** about 9% less wall time at t50-p4, 8% at t400-p4, 7% at t50-p2
  and 1% at t400-p2.

## Caveats

- Normalizing by grade CPU assumes per-grade CPU differences are machine drift. That holds for A2
  and A21, which change scheduling only, never what one grade computes. For A21S it is
  approximate: shard grades are MultiPV subsets and can cost less CPU than one full grade, so a
  real split saving could be partly hidden by the normalization.
- One run per arm per config. The run-to-run spread of the normalized figure is not measured
  here. The A2/A21 pair, two arms with identical scheduling at fixed nodes, agrees to within
  about 1-1.5%, which is a rough noise floor.
- The pre-registered criteria use raw wall time. Under them the verdict stands as `gates` computes
  it. Whether to act on this analysis is an owner decision, recorded as a dated override if taken.
