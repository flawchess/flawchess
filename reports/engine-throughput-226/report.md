# Browser engine throughput (Phase 226): report

**Contract:** `reports/engine-throughput-226/accept-rule.md`, committed 2026-09-29 before any gate
arm ran. Rendered mechanically by `scripts/engine_throughput_226_verdict.py gates`. Numbers are
copied from `reports/engine-throughput-226/verdict.json`; nothing is re-judged. Numbers not in
verdict.json (calibration for held items, grade CPU, nodes-at-stop, warm arm) are computed from
the committed data and labelled report-only. Disagreements go into dated override documents.
Three exist, and the owner ratified all three on 2026-10-02. `gates`: exit 0, status complete, missing [],
rerun_required [].

## Headline

| Item | Outcome | Deciding criterion |
|---|---|---|
| Item 2: round underfill fix (arm A2) | **hold** | Underfill throughput: t400-p2 wall ratio 1.1252 > 1.05 (other three configs pass; underfill MQ passes) |
| Item 1: root comparability guard (arm A21) | **hold** | Stacked rule: underfill held. Its own S1, S2, MQ all pass |
| Root grade split (arm A21S) | **hold** | Stacked rule: underfill held. Its own Clear-Hash content also fails (0.02092 > 0.01680); its other criteria pass |
| Candidate cap (A21SC) | not run | D-17 did not fire |
| Refit (D-11) | **no-refit** | No item shipped, so no shipped item shows a powered shift |

**Owner override (2026-10-02): all three items ship.** The table above is the mechanical,
pre-registered verdict, kept as the record. The owner ratified the three overrides and overrode
the hold after an interleaved re-test confirmed the root split's bot-move gain (0.82x of A21; see
`override-2026-10-02-owner-ship-decision.md` and the "Owner override and re-test" section below).
The 226-13 reverts are undone, and SEED-176/177/178 are closed.

"Measured, not worth shipping" applies to the root split as it stands. It passes the throughput,
determinism, warm-content and move-quality criteria, but fails the Clear-Hash content bound that
the prototype had already flagged (0.0209 vs 0.0168, design-inputs.md section 6). The underfill
fix and the guard are held by pre-registered criteria, not by a finding that they are harmful
(see the CPU-normalized section and Owner decisions).

## Arms

| Arm | SHA | Definition |
|---|---|---|
| A0 | 3fe340ce948f07646852d37eae2a42e6729c8894 | Baseline: accept-rule commit; engine code identical to main, tooling only |
| A2 | 756d2a4a1604b0ff050dcf62ce6b94e7b8f4cb76 | A0 + round underfill fix |
| A21 | 29f543f2730621f8567923c83c113e62f4f13519 | A2 + root comparability guard |
| A21S | f6c1f7a5452389d744d61e51f284a026d5cea5f4 | A21 + root grade split (gradeRoot) |
| A21SC | absent | D-17 not fired |

Attribution (D-12): item 2 = A2 vs step-0 A0a; item 1 = A21 vs A2; split = A21S vs A21.
Content assertions passed for every arm.

## Design inputs

EXPECTED_MQ_POSITIONS 60; MQ allowance off/on 1/1; CALIBRATION_THRESHOLD Maia 85.0, SF 53.5428;
ROOT_SPLIT_MAX_T50_WALL_RATIO 0.97; CONTENT_MAX clear 0.016804, warm 0.025206;
STOP_RULE_MAX_WALL_MS 12,100; CANDIDATE_CAP_ARM_ACTIVE false.

## Step 0

**Profile shares vs SEED-171's loaded-box table.** SEED-171 was measured at load 14-21; step 0
at load < 2.0, with 4 positions, c4, two runs.

| Quantity | SEED-171 | Step 0 (run 1 / run 2) |
|---|---|---|
| 50 nodes wall (4 pos) | 27.1 s | 13.8 s / 14.3 s |
| 50 nodes Maia share of wall | 27% | 26.8% / 26.9% |
| 50 nodes SF pool utilization | 48% | 46.7% / 46.8% |
| 50 nodes depth-14 share of grade time | 70% | 69.8% / 69.6% |
| 400 nodes wall | 43-98 s/position | 91.5 s / 91.9 s total (~23 s/position) |
| 400 nodes Maia share of wall | 59% | 55.4% / 55.6% |
| 400 nodes SF pool utilization | 37% | 36.9% / 37.1% |

The shares reproduce on an idle box, and absolute time roughly halves. Maia and most SF workers
sit idle much of the time. The losses are in scheduling, not in TypeScript glue.

**D-17:** the non-root >8-candidate share of grade time is 0.4626 at 50 nodes (0.4659, 0.4593)
and 0.3595 at 400 nodes. Both are below 0.5, so there is no A21SC.

**Root-split content and gain (prototype):**
- Clear Hash mean |Δes| 0.0209, p95 0.0785. Warm 0.0149. Warm single-vs-single noise floor 0.0168.
- P = 0.05856, so G = 0.03 (the floor) and the T-50 bar is 0.97.
- Shard CPU was 92.3% of single-call CPU.

**D-09 answer: was Phase 225's A0 drift noise?**
- The in-session null (A0b vs A0a) read Maia +0.35 ± 26.14 and SF +11.48 ± 27.32 pooled, with
  null controls within thresholds (Maia +12.3, SF +86.9 vs 165/149). It holds, so same-session
  replicate noise is small.
- Phase 225's SF −81.4 vs July-21 is about 3.0 se of that null, so ordinary same-session
  sampling noise does not explain it.
- The same-session A0a vs July-21 comparison is void. Its SF null-control cell (blend 0, untouched
  by these changes) moved −177.4 against a 149 threshold, with no engine change.
- Phase 225's drift is therefore best attributed to cross-session non-comparability with the
  July-21 curves, not to a real strength effect of the underfill fix. This explains why
  July-vs-arm comparisons cannot be trusted. It does not prove that −81.4 was pure sampling noise
  (design-inputs.md section 3).
- Every calibration criterion here compares against same-session A0a only.

**Maia-anchor identity cross-check (report-only).** `maia_anchor_identity` compares A0a ledgers
with sweep-225-a0 ledgers, keyed on (pass, anchor, game_index), per cell. Cells are not
concatenated because their keys collide.

| Cell | Matched | Identical |
|---|---|---|
| human1100 | 8 | 8 |
| light1300 | 10 | 10 |
| light1900 | 0 | n/a |
| deep1500 | 8 | 8 |
| deep2300 | 24 | 24 |
| Total | 50 | 50 |

Every matched Maia-anchor game is byte-identical between Phase 225's A0 and this phase's A0a. The
overlap is small: Phase 225 ran 24 games per anchor and this phase 50, which shifts the
game_index ranges, so only the `locate` rows and some `measure` rows share keys. The check
supports Maia-side reproducibility, which places the cross-session component on the SF-anchor
side. At 50 keys it is a weak check.

## Criteria in accept-rule order

1. **Validity:** passed; `missing` is empty. 16 positions per compared throughput pair.
2. **Underfill throughput (A2 vs A0a): FAIL.**

   | Config | A0a wall ms | A2 wall ms | Ratio | Bound |
   |---|---|---|---|---|
   | t50-p4 | 99,597 | 103,346 | 1.0376 | pass |
   | t400-p4 | 615,023 | 609,962 | 0.9918 | pass |
   | t50-p2 | 106,521 | 104,739 | 0.9833 | pass |
   | t400-p2 | 696,260 | 783,424 | **1.1252** | **fail** (> 1.05) |

3. **Underfill MQ (A2 vs A0a, stop off): PASS.** Net 1 vs allowance 1, McNemar p 0.5
   (report-only). One pass-to-regression flip, cBFTV, reproduced by the fresh-process rerun
   (gate/a2/mq-off-rerun). No regression-to-pass.
4. **Guard S1 (A21): PASS.** Max wall 8,321 ms vs 12,100.
5. **Guard S2: PASS.** A21 10 early stops, A2 10.
6. **Guard MQ (stop on): PASS.** Net 0, allowance 1.
7. **Root-split determinism: PASS** (`PASS: calibration determinism`).
8. **Root-split T-50: PASS.** t50-p4 96,623 vs 99,675 ms = 0.9694 (bound 0.97, margin 0.0006).
9. **Root-split other configs: PASS** (bound 1.05).
   - t400-p4: 992,145 → 629,684 = 0.6347.
   - t50-p2: 139,608 → 104,979 = 0.7520.
   - t400-p2: 745,599 → 708,357 = 0.9501.

   The raw t400-p4 and t50-p2 ratios are dominated by drift in A21's own runs (see the
   CPU-normalized section).
10. **Root-split Clear-Hash content: FAIL.** Mean |Δes| over 76 pool rows is 0.020923 vs 0.016804.
    Argmax flip rate 7.89% (report-only). The real pool implementation reproduces the prototype's
    0.0209.
11. **Root-split warm content: PASS.** 0.015479 vs 0.025206. Argmax flip rate 5.26%.
12. **Root-split MQ off: PASS.** Net −1 (regression-to-pass: cBFTV), allowance 1, p 0.5.
13. **Root-split S1 and MQ on (report-only, guard held):** MQ on net −1 (regression-to-pass:
    Dj8iG), p 0.5. A21S max stop wall 8,423 ms (from the stop TSV, not verdict.json).
14. **Candidate cap:** absent.
15. **Calibration and refit.** verdict.json has no calibration block because no item ships. For
    attribution, the gates' own `powered_verdict` was applied to the committed parity verdicts
    (report-only). Thresholds: Maia 85.0, SF 53.5428. Seed 1, 50 games per (cell, anchor).

    | Comparison | Maia pooled | SF pooled | Null controls (Maia/SF shift, within 165/149) | Parity verdict | Powered verdict |
    |---|---|---|---|---|---|
    | A2 vs A0a | +18.7 ± 27.1 | +12.6 ± 27.2 | 0.0 / +34.7 | holds | valid, no real shift |
    | A21 vs A2 | −22.2 ± 27.0 | −46.7 ± 27.1 | 0.0 / +5.5 | holds | valid, no real shift |
    | A21S vs A21 | +15.2 ± 27.4 | +30.7 ± 27.2 | 0.0 / +31.6 | fails (shape guard at 1500/0.5) | valid, no real shift |

    - All six pooled shifts are inside their thresholds.
    - The pre-registered z-guard (|shift|/se > 1.96 in both families on the same cell) fires on no
      cell.
    - A21S vs A21, cell (1500, 0.5): Maia +75.4 (z 1.58), SF −101.8 (z 2.03), opposite signs. The
      Phase 199 CI-overlap guard fires there, hence the "fails" string.
    - Other A21S cells, Maia / SF: (1300, 0.05) −54.2 / +134.1 (SF z 2.63); (1900, 0.05)
      +60.3 / +83.3; (2300, 0.5) −28.9 / −29.0.
    - A21 vs A2, largest cell: (1300, 0.05) SF −111.8 (z 2.24), Maia 0.0.

    **Pitfall-1 root-split log check:**
    - Every a2 and a21 cell: splits=0.
    - a21s: light1300 2,472, light1900 2,118, deep1500 1,167 and deep2300 970 splits, all with
      0 premise violations.
    - a21s human1100: calls=0. This is the blend-0 null control, so it is structural
      (override-2026-10-01-pitfall1-blend0-cell.md).

    **Refit: no-refit.** Reason: "no shipped item shows a real (powered) shift". The D-20 scope is
    not triggered, so Plan 226-14 has nothing to run.

## D-13: why cBFTV flips

Classified as a side effect, not a bug (design-inputs.md section 4;
override-2026-09-29-d13-trace-anomaly.md).
- cBFTV has no duplicate-leaf TRACE-ANOMALY in any trace. The anomalies belong to three
  repetition-heavy control positions and appear identically at A0.
- In the A2 tree the same leaf expansion lands at round 9 instead of 12 (14 rounds instead of 17),
  with the same grades. e4c6 drops below e2g4 at that expansion in both trees.
- At the gate, the underfill MQ shows cBFTV as a pass-to-regression flip, reproduced by the
  fresh-process rerun (net 1, inside the allowance).
- MQ improved for the other items: root split MQ off cBFTV regression-to-pass, MQ on Dj8iG
  regression-to-pass. The guard produced no flips.

## D-04: mobile pool-of-2 (Node harness, gating)

| Config | Underfill (A2/A0a) | Root split (A21S/A21) |
|---|---|---|
| t50-p2 (c4, pool 2) | 0.9833 | 0.7520 |
| t400-p2 (c2, pool 2) | **1.1252** | 0.9501 |

The real-phone dev-build run is owner-deferred and report-only. It was not run.

## Report-only: CPU-normalized throughput

Source: `analysis-2026-10-01-cpu-normalized-throughput.md`. It does not change the verdict.

Raw wall time tracks per-grade SF CPU, which drifted up to 1.75x between runs of identical work
(A21 t400-p4 228 ms/grade vs A2's 139 at the same 6,400 grades). The guard cannot cause that: it
only changes when the stop rule fires, and the fixed-budget runs do not use the stop rule.
Wall time per unit of grade CPU is a pipeline-efficiency figure that moves only with the code.
Normalized:

- **Underfill (A2 vs A0a):** ~5-8% less wall per unit of work on the desktop pool, ~4% at
  t50-p2, ~1% at t400-p2. The failing t400-p2 ratio (1.125) matches a 13% per-grade CPU rise
  (74 → 84 ms) with unchanged efficiency (0.991).
- **Guard:** no throughput effect (0.99-1.02 normalized).
- **Root split:** ~4% at t50-p4, 2-4% at t50-p2, ~0 at 400 nodes. The raw 0.63 at t400-p4 is
  A21's drift reversing.
- **Full stack (A21S vs A0a):** ~7-9% on desktop and at t50-p2, ~1% at t400-p2.

Caveats: one run per arm per config. The normalization is approximate for A21S, because shard
grades can cost less CPU. The pre-registered criteria use raw wall time.

## Other report-only measurements

**Grade CPU ratios** (arm/base):

| Config | A2/A0a | A21/A2 | A21S/A21 |
|---|---|---|---|
| t50-p4 | 1.092 | 0.969 | 1.009 |
| t400-p4 | 1.075 | 1.637 | 0.635 |
| t50-p2 | 1.026 | 1.315 | 0.782 |
| t400-p2 | 1.136 | 0.957 | 0.946 |

Grade counts are identical at A0a, A2 and A21 (800 or 6,400 per config). A21S adds split grades
(845, 6,445, 816 and 6,416; 16 splits per config).

**Stop rule** (16 positions, 50 nodes, the bot's real move path):

| Arm | Mean nodes at stop | Early stops | Total wall (ms) |
|---|---|---|---|
| A0 | 29.06 | 9 | 68,078 |
| A2 | 28.88 | 10 | 67,051 |
| A21 | 28.88 | 10 | 68,236 |
| A21S | 24.25 | 11 | 55,373 |

A0's max wall is 8,253 ms. With the root split, the clear-winner stop fires earlier on average:
24.25 vs 28.88 nodes, and 19% less total wall than A21. Wall per evaluated node is close
(about 143 vs 148 ms), so most of that bot-move latency gain comes from stopping sooner, not
from faster nodes. This is one run of 16 positions, and the stop-rule run carries no grade-CPU
column to normalize against.

**Warm arm** (`--no-clear-hash --games 4`, 60 plies): 0 plies differing at step-0 A0, A21 and A21S.

## Phase 227 hand-off

- **D-02 WebGPU prerequisite:** desktop WebGPU Maia performance is unmeasured (this Linux Chrome
  has no adapter). Measure it on another machine before sizing continuous dispatch (SEED-171
  item 3, L-6).
- **D-05 contract:** expected score within a tolerance over a fixture (the picked move's d20
  expected score vs the round-mode baseline, plus no increase in MQ regressions). Recorded, not
  implemented.
- **D-06 noise floor:**
  - Round-mode warm-hash floor from the D-03 arm: 0 of 60 plies differing (mean |Δes| 0.0) at
    A0, A21 and A21S.
  - Separate content-instrument floor (single-vs-single, differently warmed engines): mean
    |Δes| 0.0168.
  - 227's accept rule fixes k and the tolerance before data.
- **D-07 round-mode flag:** round mode is retained behind a budget flag (227's A0 arm and
  rollback). Not built.
- **Branch state:** nothing ships, so 227's baseline is main's engine content unless the owner
  overrides.
- The no-Clear-Hash warm arm in `calibration-determinism.check.mjs` is built and reusable (D-03).

## Owner decisions (as posed before the override; resolved 2026-10-02, see "Owner override and re-test")

1. **Ratify or reject three overrides** (orchestrator-authored under the autonomy instruction):
   `override-2026-09-29-d13-trace-anomaly.md`, `override-2026-09-29-content-tool-single-candidate.md`
   and `override-2026-10-01-pitfall1-blend0-cell.md`.
2. **Accept the mechanical hold-everything verdict, or record an override.**
   - Underfill fails exactly one of four throughput configs (t400-p2) and passes MQ.
   - The guard passes all three of its own criteria and is held only by stacking.
   - The root split fails exactly one of its own criteria (Clear-Hash content, which is not a
     wall-time measurement), plus the stacking rule.
   - CPU normalization bears only on the raw-wall criteria. Overriding the underfill hold would
     let the guard ship on its own passing criteria. The split would still need a second override
     for the content failure.
   - Powered calibration shows no real shift for any item, so no refit would be indicated.
3. **A21S vs A21 shape-guard cell** (1500/0.5: Maia +75, SF −102, opposite signs). The pooled
   shifts (Maia +15.2 ± 27.4, SF +30.7 ± 27.2) are within thresholds. The z-guard does not fire;
   the Phase 199 CI-overlap guard does. This is moot for the current verdict and matters only if
   the owner overrides toward shipping the split.

## Refit

**Decision: no-refit** (unchanged by the owner override: the powered verdicts show no real shift for any shipped item) (verdict.json: "no shipped item shows a real (powered) shift"). Nothing
ran. No curve cell or persona label changed, and regenerating `botStrengthCurves.ts`,
`personaCalibration.ts` and `bot-strength-lookup.json` leaves no diff (Plan 226-14 Task 1
verify). For reference, the report-only powered verdicts in criterion 15 show no real shift for
any item. An owner override toward shipping would therefore not, on this data, require a refit.

## Smoke test and device UAT

- **Smoke: pass (2026-10-02, after the owner override shipped all three items).**
  - Analysis board: a 400-node FlawChess search ranked lines and agreed with Stockfish on a4.
  - Bot game: 9 bot moves against Sly the Coyote (~1600, a searching persona), each reply within a
    few seconds.
  - No console errors on either page. Details in `226-UAT.md`.
  - The earlier "skipped" entry (frontend identical to main) applied only while nothing shipped.
- **Real-phone run:** owner-deferred and report-only (D-04). Not run.

## Owner override and re-test (2026-10-02)

The owner's decisions, recorded in `override-2026-10-02-owner-ship-decision.md`:
- Ratified all three overrides.
- Shipped the underfill fix and the guard. The underfill's only failing config is explained by
  machine drift, and the guard was held only by stacking.
- Shipped the root split after the re-test confirmed a substantial gain. The owner accepts the
  slight content difference (0.0209 vs 0.0168).

The re-test interleaved the arms (rotated order, idle-box gate logged in
`reports/data/engine-throughput-226/retest-2026-10-02/driver.log`).

**Bot move path** (stop rule on, 16 positions, 3 rounds):

| Arm | Mean total wall (s) | Range (s) | Mean nodes at stop | Early stops |
|---|---|---|---|---|
| A0 (main) | 69.5 | 68.5-71.4 | 29.06 | 9 |
| A21 | 68.5 | 67.6-70.4 | 28.88 | 10 |
| A21S | 56.4 | 55.4-57.0 | 24.25 | 11 |

A21S/A21 per round was 0.809, 0.841 and 0.819. The gain splits into two parts:
- About 8% pure speed, on the 11 positions with identical node counts.
- About 10% from the stop firing at different node counts on 5 positions (4 earlier, 1 later).

**t400-p2 (underfill's failing config, one A0-then-A2 pair; the planned ABBA was cut because each run took ~50 min):** raw A2/A0 0.879 (gate day 1.125), CPU-normalized 0.998. Decision document §6.

## Follow-ups

SEED-176/177/178 were planted for the held items and closed by the owner override. SEED-171 carries
the Phase 226 outcome and the override note. Phase 227's baseline is A21S.
