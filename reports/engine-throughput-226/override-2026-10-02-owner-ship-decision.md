# Owner override: ratify the three overrides, ship underfill + guard, re-test the root split

**Date:** 2026-10-02
**Decided by:** the owner, after reading the report and the CPU-normalized analysis. The owner's
words: "let's ship the change and approve the exceptions. Feel free to repeat the speed test."
They also set the principle that the pre-226 engine is not a gold standard. Playing a little
differently is acceptable for substantial performance gains.
**Rule file:** NOT edited. `verdict.json` stays the mechanical record of the pre-registered gate.
This document supersedes its ship/hold outcome.

## 1. Ratified overrides

- `override-2026-09-29-d13-trace-anomaly.md`: ratified. The code review's WR-07 (trace edges keyed
  by child FEN, so transpositions read as duplicate expansions) independently supports it.
- `override-2026-09-29-content-tool-single-candidate.md`: ratified.
- `override-2026-10-01-pitfall1-blend0-cell.md`: ratified.

## 2. Ship decision

| Item | Mechanical verdict | Owner decision | Basis |
|---|---|---|---|
| Round underfill fix (A2) | hold (t400-p2 1.125) | **ship** | The failing config shows unchanged pipeline efficiency (0.991) with a 13% per-grade CPU rise, which is machine drift (analysis-2026-10-01). It passes move quality and shows no powered calibration shift. Re-tested interleaved below |
| Root comparability guard (A21) | hold (stacked only) | **ship** | Passes its own S1, S2 and MQ. It was held only because underfill was held. No powered calibration shift |
| Root grade split (A21S) | hold (stacked + Clear-Hash content) | **conditional**: ship iff the interleaved bot-move re-test confirms a substantial gain | It plays slightly differently (content 0.0209 vs 0.0168), which the owner accepts in principle for a substantial gain. Its MQ improved and calibration shows no powered shift. The 19% bot-move gain came from one 16-position run |

No refit: the report-only powered verdicts show no real shift for any item (report.md criterion 15).

## 3. Re-test (owner-permitted, report-only evidence for this override)

The data lives in `reports/data/engine-throughput-226/retest-2026-10-02/`. The arms are interleaved
(order rotated per round) so that machine-speed drift hits every arm equally. Each step waits for a
1-minute load average below 2.0, which is logged in `driver.log`.

- Bot move path (stop rule on, accept-rule §3 command): A0, A21 and A21S, 3 rounds each.
- t400-p2 (the underfill's failing config): A0 and A2, 2 rounds each, in ABBA order.

Results and the final root-split decision are appended below once the runs finish.

## 4. Re-test results: bot move path (2026-10-02, interleaved, stop rule on, 16 positions)

| Arm | Round 1 (s) | Round 2 (s) | Round 3 (s) | Mean (s) | Mean nodes at stop | Early stops |
|---|---|---|---|---|---|---|
| A0 (main) | 71.4 | 68.5 | 68.7 | 69.5 | 29.06 | 9 |
| A21 (underfill + guard) | 70.4 | 67.6 | 67.6 | 68.5 | 28.88 | 10 |
| A21S (+ root split) | 57.0 | 56.8 | 55.4 | 56.4 | 24.25 | 11 |

- A21S/A21 per round: 0.809, 0.841, 0.819 (mean 0.823). A21/A0: 0.986, 0.988, 0.983. Node counts
  are deterministic across rounds, and the round-to-round wall spread is about 4%.
- The root split's gain has two parts:
  - **Pure speed, about 8%.** It covers the 11 positions where A21 and A21S stop at the same node
    count: 48.6 s → 44.8 s in round 1, 5-20% per position.
  - **Earlier confidence, about 10%.** On 5 positions the stop fires at a different node count:
    italian 31→13, C42 24→8, C25 50→15, B90 16→8, and C60 25→28 (later). This is the
    "plays slightly differently" part. Move quality (MQ on: one regression-to-pass, none the other
    way) and calibration (no powered shift) show no cost.
- **Conclusion:** the 19% single-run figure is confirmed (≈18% over three interleaved rounds). The
  root split meets the owner's "substantial gain" condition.

## 5. Final decision on the root split

The owner explicitly approved shipping the root split after the bot-move re-test ("yes, ship the
parallel first look too", 2026-10-02). It is re-applied in `feat(226): ship root grade split (owner
override)`. All three items now ship, and `frontend/src` equals arm A21S (`f6c1f7a54`).

## 6. Re-test results: t400-p2 (underfill's failing config, A0 then A2 back to back)

The plan was ABBA. It was cut to one AB pair, because each run took about 50 min and the ship
decision was already made.

| Arm | Ladder wall (s) | CPU per grade (ms) | Grades | Wall / grade CPU |
|---|---|---|---|---|
| A0 | 805 | 86.5 | 6,400 | 1.455 |
| A2 | 708 | 76.1 | 6,400 | 1.453 |

- Raw A2/A0 is **0.879** here, against **1.125** on gate day. The sign flipped, and the size
  matches the per-grade CPU swing in each run.
- CPU-normalized A2/A0 is **0.998** here, against 0.991 on gate day: no code effect at this config,
  either way.
- This confirms the analysis-2026-10-01 reading. The gate's underfill failure was machine-speed
  drift between runs, not slower code. Raw wall on this machine swings about ±12% run to run at
  t400-p2.
