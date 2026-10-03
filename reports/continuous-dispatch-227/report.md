# Browser engine continuous dispatch (Phase 227): report

**Contract:** `reports/continuous-dispatch-227/accept-rule.md` (commit `7fb704a65`), committed before any gate data.
Rendered mechanically by `scripts/engine_dispatch_227_verdict.py gates`: exit 0, status `complete`. Numbers in the
criteria table are copied from `reports/continuous-dispatch-227/verdict.json`. Numbers outside it are computed from the
committed data and labelled report-only. Both arms ran from one checkout, implementation commit
`f3d9ea2fe6d2da928243b61eed049ac4f29f49f5`, selected only by `--dispatch-mode` / `PRESET_SUPERVISOR_DISPATCH_MODE`.
`FLAWCHESS_DISPATCH_MODE` stayed `'round'` throughout.

## Headline

**Mechanical outcome: `ship-eligible`. Refit if shipped: `no-refit`. Virtual-loss trigger: false.**

Continuous dispatch is faster and plays as well as round mode against the d20 ground truth.

- Move quality: the signed mean difference is -0.0045 (stop off) and -0.0012 (stop on) against a margin of 0.0252.
  Net regressions are 0.0 and 0.4 against an allowance of 1.
- Throughput (Node, interleaved, probe-normalized): the bot path (`stop-p4`) is 19.0 percent faster, analysis at 400
  nodes (`t400-p4`) 14.2 percent. The pool-2 configs are 18.0 and 18.9 percent faster.
- WebGPU (owner's machine): continuous bot moves take 0.676 of round-mode wall (median of 3 rounds); the limit is 1.03.
- Calibration: no powered strength shift (Maia pooled +33.1 +- 28.1 against 85, Stockfish -3.6 +- 28.7 against 53.5).

The owner decides ship or hold from this evidence (D-00, D-04). See "Decision" at the end.

## Criteria in accept-rule order

| # | Criterion | Value | Bar | Result |
|---|---|---|---|---|
| 1 | Validity | MQ, throughput, WebGPU and calibration inputs complete and valid | exit 0 | pass |
| 2 | D-01 stop off: signed mean D | -0.00452 | >= -0.02521 | pass |
| 2 | D-01 stop on: signed mean D | -0.00117 | >= -0.02521 | pass |
| 3 | D-03 stop off: net regressions | 0.0 | <= 1 | pass |
| 3 | D-03 stop on: net regressions | 0.4 | <= 1 | pass |
| 4 | D-17 ship bar: gain on `stop-p4` or `t400-p4` | 0.1905 / 0.1418 | >= 0.15 on either | pass (`stop-p4`) |
| 4 | D-17 no regression: ratio `stop-p4`, `t400-p4` | 0.8095 / 0.8582 | <= 1.03 | pass |
| 5 | Pool-2 `t50-p2`: median ratio | 0.8192 (noise 0.0051) | <= 1.03 | pass |
| 5 | Pool-2 `t400-p2`: median ratio | 0.8155 (noise 0.0150) | <= 1.03 | pass |
| 6 | D-07 WebGPU: median continuous/round bot-move wall | 0.6761 | <= 1.03 | pass |
| 7 | D-15 calibration (decides refit only) | valid, no real shift | thresholds 85.0 / 53.54 | `no-refit` |

`t400-p4` alone would miss the 15 percent bar (14.2 percent). The bar is met on `stop-p4`, as the rule allows.

## Move quality (D-01, D-03)

60-position fixture, bot budget 50 nodes, c4, pool 4, warm hash, Maia FIFO, grade depth 20, R = 5 repeats per arm.
D is continuous minus round, in d20 expected score (es). Positive favors continuous.

| Cell | D (es) | Margin (es) | Margin in flips | Net regressions | Allowance | Result |
|---|---|---|---|---|---|---|
| stop off | -0.00452 | 0.02521 | 5.58 | 0.0 | 1 | pass |
| stop on | -0.00117 | 0.02521 | 5.68 | 0.4 | 1 | pass |

One full-size flip moves D by about 0.0045 es (mean flip size 0.271 off, 0.266 on). D in stop off is about one flip in
continuous mode's disfavor out of 60 positions; D in stop on is a quarter of one.

Report-only:

| Cell | Bootstrap LCB of D | K (unstable A1 picks) | Mean abs des | McNemar p | Round regressions | Continuous regressions | Round-repeat disagreement |
|---|---|---|---|---|---|---|---|
| stop off | -0.01355 | 1 | 0.00452 | n/a (0 vs 0 discordant) | 12.0 | 12.0 | 0 of 60 |
| stop on | -0.01690 | 1 | 0.01596 | 0.75 (1 vs 1) | 11.0 | 11.4 | 0 of 60 |

Round repeats agreed on every position in both cells (owner direction 2026-10-02 made this report-only; it held anyway).

Report-only cells (1 repeat each):

| Cell | D (es) | Round regressions | Continuous regressions | Net |
|---|---|---|---|---|
| Clear-Hash stop off | -0.00072 | 10 | 10 | 0 |
| Clear-Hash stop on | -0.00260 | 11 | 12 | 1 |
| analysis-400 stop off (D-20) | 0.00000 | 11 | 11 | 0 |

The virtual-loss trigger (D-08) did not fire: no D-01 or D-03 failure. No diagnostic trace was run, and
`gate/trace/` is empty by design.

## Throughput (D-04, D-17)

Committed driver `scripts/engine_interleave_227.py`, 3 rounds, configs rotated each round, arm order reversed on even
rounds, a load gate (1-minute load below 2.0) and a 13 s machine-speed probe before every step. 24 steps, all rc 0, no
load-gate timeouts. Judged ratio = geometric mean over rounds of `(W_a1 / P_a1) / (W_a0 / P_a0)`.

| Config | Round 1 | Round 2 | Round 3 | Judged ratio | Gain | Raw ratio (report-only) | Grade-elapsed ratio (report-only) |
|---|---|---|---|---|---|---|---|
| stop-p4 | 0.8071 | 0.8100 | 0.8115 | 0.8095 | 19.0% | 0.8061 | 0.7852 |
| t400-p4 | 0.8601 | 0.8639 | 0.8508 | 0.8582 | 14.2% | 0.8505 | 0.8228 |
| t50-p2 | 0.8141 | 0.8272 | 0.8192 | 0.8201 | 18.0% | 0.8160 | 0.7923 |
| t400-p2 | 0.8180 | 0.8155 | 0.7983 | 0.8106 | 18.9% | 0.8076 | 0.7835 |

Rounds agree within about 1.5 points per config, so machine drift (226 measured about +-12 percent run to run) does not
explain the gain. The grade-elapsed ratio flatters continuous mode, as predicted (Pitfall 5), and is not judged.

Measured gain against the design's model (`design.md` section 4, model output):

| Config | Nominal model | Measured-wall ceiling | Measured gain |
|---|---|---|---|
| stop-p4 (bot path) | 30.7% (finite-N, section 4.4) | n/a | 19.0% |
| t400-p4 | 29.7% | 21.5% | 14.2% |
| t50-p2 | 32.9% (model only) | 33.9% | 18.0% |
| t400-p2 | 31.2% | 32.1% | 18.9% |

Continuous realized about 53 to 66 percent of the ideal pipeline ceiling, below the roughly 70 percent the design said
`t400-p4` needed to clear 15 percent on its own. The bot path clears the bar with room.

## WebGPU (D-06, D-07)

**Judged leg (owner).** Edge 154 on Windows, 32 threads, pool 4, shader-f16, webgpu backend, served over the tailnet.
`webgpu/continuous-leg.json`, 3 interleaved rounds, every row's observed mode equals its requested mode.

| Round | Continuous / round bot-move wall |
|---|---|
| 1 | 0.6112 |
| 2 | 0.8416 |
| 3 | 0.6761 |
| **D-07 median** | **0.6761 (bar <= 1.03, pass)** |

Report-only reading of the same rows: continuous stopped early more often (stop rule on). Summed over the leg, round
mode searched 633 nodes in 43.9 s (69.3 ms per node) and continuous 563 nodes in 31.1 s (55.3 ms per node). About 20
percent of the 32 percent wall gain is per-node speed and the rest is earlier stops. The design predicted 21.8 to 26.1
percent for WebGPU at node G (14 to 18 percent at the implied browser G), so the per-node speedup sits inside that range.

Maia batch-1 latency, owner machine (report-only):

| Backend | Condition | Round leg (227-08) median / p90 ms | Interleaved leg (227-12) median / p90 ms |
|---|---|---|---|
| webgpu | idle | 17.8 / 28.2 | 17.1 / 19.5 |
| webgpu | Stockfish busy | 23.2 / 25.9 | 23.4 / 26.5 |
| wasm (4 threads) | idle | 46.2 / 46.6 | 25.0 / 26.7 |
| wasm (4 threads) | Stockfish busy | 32.0 / 40.6 | 27.9 / 30.4 |

**Local wasm leg (Claude, report-only).** Linux Chrome 154, wasm (no WebGPU adapter on this box),
`webgpu/local-wasm-interleaved-leg.json`. Per-round ratios 0.724, 0.600, 0.637 (median 0.637); 115.4 ms per node round,
76.9 ms per node continuous. The tab was hidden during the run, so these timings are background-throttled and weaker
than the owner's leg. The leg does confirm the bench tool now runs continuous mode end to end (observed mode
`continuous` on every continuous row).

## Calibration (D-15)

Five runbook cells times two arms, 50 games per (cell, anchor), seed 1, pinned anchors, under the crash supervisor,
same-cell pairs, at most 6 harnesses (2000 ledger rows, every `dispatch_mode` matches its arm, no crash relaunches).
`calibration_parity_verdict.py`, A1 (continuous) against same-session A0 (round):

| Family | Pooled shift | se | Threshold | Beyond threshold |
|---|---|---|---|---|
| Maia | +33.1 | 28.1 | 85.0 | no |
| Stockfish | -3.6 | 28.7 | 53.54 | no |

Null control (human1100, blend 0, which continuous dispatch should not touch): Maia shift 0.0 +- 59.0 (within 165),
Stockfish +24.4 +- 57.3 (within 149). Valid.

Per exposed cell (report-only): one cell, Maia deep2300, sits outside its CI at +188.0 +- 89.3. Every other cell, in
both families, is inside (Maia light1300 +46.2, deep1500 -40.0, light1900 +41.7; Stockfish light1300 +29.7, deep1500
-46.9, light1900 +13.7, deep2300 -28.9). The twin's powered verdict, including the shape guard, finds no real shift.

**`refit_if_shipped`: `no-refit`.** Shipping keeps the committed strength curves and persona labels.

## What shipping changes

- Bot moves and the analysis board use continuous dispatch: about 19 percent less wall on the bot path on desktop
  (Node), a 32 percent median on the owner's WebGPU machine (about 20 percent per node), and 14 to 19 percent on
  analysis.
- Same-seed games stop being byte-reproducible (expected, D-05 relaxed target). Move quality against d20 is unchanged
  within the margin.
- Rollback is the one-line flip of `FLAWCHESS_DISPATCH_MODE` back to `'round'`.

## Outcome

The owner's ship decision is executed. Commit `e9fc9a079` (`feat(227): ship continuous dispatch`) flips
`FLAWCHESS_DISPATCH_MODE` in `frontend/src/lib/engine/botBudget.ts` to `'continuous'`. Both app callers (bot moves and
the analysis board) and every harness default now use continuous dispatch. The engine unit tests (34 files, 777 tests)
and the production build pass after the flip, and the dispatch-mode probe observes the requested loop in both modes.
Rollback is flipping the constant back to `'round'`.

## Refit

Skipped. `refit_if_shipped` is `no-refit`: the powered A1-vs-A0 calibration found no real shift (Maia pooled +33.1 +-
28.1 against 85.0, Stockfish -3.6 +- 28.7 against 53.54, null control valid). The committed strength curves and persona
labels stay as they are; regenerating them produces no diff.

## Smoke test and device UAT

From `.planning/phases/227-browser-engine-continuous-dispatch-against-a-relaxed-determi/227-UAT.md`: **smoke pass** in
the dev build after the flip, with the page reporting `FLAWCHESS_DISPATCH_MODE = "continuous"`.

- Analysis board, middlegame FEN, 400 nodes: ranked lines rendered (Ng5 +1.1, h3 +0.6), console clean.
- Bot game against Tank the Ox (~1500): 7 bot moves (`1. e4 e5 2. Nc3 Nf6 3. Bc4 Bc5 4. d3 d6 5. a3 O-O 6. Na4 Bb6
  7. Nf3`), every reply prompt, console clean.
- Real phone: deferred to the owner, report-only (226 D-04).

## Dev tool

The dev engine bench (`frontend/src/dev/engineBench/`, its tests and the DEV-gated `/dev/engine-bench` route in
`App.tsx`) is removed (D-06). knip and eslint are clean, and the production build contains neither the
`engine-bench-227` schema marker nor the page component.

## Decision

The owner decided to **ship** on 2026-10-03, following the mechanical outcome (`ship-eligible`, `no-refit`) with no
override. The record is `reports/continuous-dispatch-227/owner-decision.md`. Plan 227-13 flips
`FLAWCHESS_DISPATCH_MODE` to `'continuous'` without a refit.
