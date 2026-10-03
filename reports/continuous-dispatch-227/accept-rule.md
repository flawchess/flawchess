# Phase 227 accept rule (continuous dispatch against a relaxed determinism target)

**Committed:** 2026-10-02, as the commit that adds this file. Find it with
`git log -1 --format=%H -- reports/continuous-dispatch-227/accept-rule.md`. That commit is the pre-registration point:
it comes after both design reviewers returned SOUND (`design.md`, round 2) and before any continuous-mode data exists.
`reports/data/continuous-dispatch-227/gate/` does not exist when this file is committed, and the first commit that adds
a file under it must descend from this one.

This is a decision contract, not a narrative. Every threshold is fixed in advance and is **not editable** once gate data
exists. Like `reports/engine-throughput-226/accept-rule.md`, it records constants that equal the frozen block of its
machine-readable twin, `scripts/engine_dispatch_227_verdict.py`. `test_accept_rule_matches_twin_constants` in
`tests/scripts/test_engine_dispatch_227_verdict.py` pins section 2 to that block by name. A deviation is a separate dated
override document, in the shape of `reports/engine-throughput-226/override-2026-10-02-owner-ship-decision.md`, never an
edit to this file.

It discharges CONTEXT decisions D-00 (round mode is a comparison arm), D-01 (non-inferiority margin), D-02 (R = 5,
warm hash), D-03 (net regressions), D-04 and D-17 (throughput ship bar, interleaved and probe-normalized), D-07 (WebGPU
point), D-08 (virtual-loss trigger), D-15 (calibration arms), D-20 (analysis-400 is report-only).

## 1. Arms

| Arm | Definition |
|---|---|
| `A0` | A21S in round mode: `--dispatch-mode round` on the gate scripts, `PRESET_SUPERVISOR_DISPATCH_MODE=round` on the calibration supervisor. |
| `A1` | The same code in continuous mode: `--dispatch-mode continuous`, `PRESET_SUPERVISOR_DISPATCH_MODE=continuous`. |

Both arms run from **one checkout**, the implementation commit `I` (the commit Plan 227-11 records at gate start, in
`run-meta.json` and its SUMMARY, never in this file). The arm is selected only by the flag. `FLAWCHESS_DISPATCH_MODE`
(`frontend/src/lib/engine/botBudget.ts`) stays `'round'` for the whole gate. Round mode is a comparison arm, not a
reference answer (D-00): divergence from it is information, and the ground truth for move quality is the d20 Stockfish
evaluation.

Commits this rule is written against:

| Name | Commit | What it is |
|---|---|---|
| `T` | `399780bf8` | Latest tooling fix: harness Maia FIFO honors abort, gates wait for Maia idle (design review round 1). |
| parity flag | `cef88fd87` | Adds `--maia-main-thread` to `scripts/engine-move-quality.mjs`, the D-18 parity reference (Plan 227-08). |
| twin relaxation | `012856e92` | Round-repeat agreement became report-only in the verdict twin (owner direction below). |
| reviewed design | `7bb93b943` | `design.md` with `REVIEW-A: SOUND (round 2)` and `REVIEW-B: SOUND (round 2)`. |

### Content assertions (run before any gate step; any failure makes the data invalid)

1. `git diff --name-only 399780bf8 R -- . ':!.planning' ':!reports'` lists only
   `scripts/engine_dispatch_227_verdict.py` and `tests/scripts/test_engine_dispatch_227_verdict.py` (`R` is this file's
   commit). No harness, pool, provider or frontend code changed between `T` and the rule.
2. `git diff --name-only R I -- . ':!.planning'` lists only the files Plan 227-10 lists
   (`frontend/src/lib/engine/mctsSearch.ts`, `frontend/src/lib/engine/__tests__/mctsSearch.continuous.test.ts`,
   `frontend/src/lib/engine/__tests__/searchTestProviders.ts`, `frontend/src/lib/engine/__tests__/mctsSearch.test.ts`,
   `frontend/src/lib/engine/deadlineSearch.ts`, `frontend/src/lib/engine/__tests__/deadlineSearch.test.ts`) plus the
   comment-only rewording of `scripts/` comments made by the commit whose subject begins
   `docs(227-09): reword harness comments`. For that commit, `git diff -U0` shows only comment lines, and the four gate
   scripts' `--self-test` and `scripts/lib/stockfish-pool.check.mjs` pass at `I`.
3. At `I`, `FLAWCHESS_DISPATCH_MODE` is `'round'`, and `assertDispatchModeLive` passes for both modes (every gate script
   exits 3 before any engine starts if the requested mode is not the loop that ran).
4. **Harness-content evidence (D-18).** The round-mode content of the harness equals main-thread Maia at `--hash clear`:
   the committed clear-hash parity PASS (`cef88fd87`, `reports/data/continuous-dispatch-227/tripwire/parity-clear/`),
   re-verified on `T` (0 of 60 rows differ in each stop mode, recorded in commit `de86e31ec`), plus Plan 227-10's
   obligation to re-run that check after the `mctsSearch` helper extraction and before any continuous code lands: the
   `--hash clear` round-mode run in worker Maia, judged by the twin's strict subcommand against the committed
   `parity-clear/main` data, `tripwire --mq-dir <rerun>/worker --baseline-dir
   reports/data/continuous-dispatch-227/tripwire/parity-clear/main`, with 0 differing rows. Plan 227-11 refuses to start
   unless Plan 227-10's SUMMARY records that re-run as TRIPWIRE PASS.

## 2. Frozen constants

Every row equals the verdict twin's value of the same name. Floats are the exact Python `repr`. The margin
`MQ_SIGNED_MARGIN = MQ_SIGNED_MARGIN_K * MQ_CONTENT_FLOOR` is about 3.3 net full-size flips over 60 positions (one flip
of size about 0.45 es moves the 60-position mean by about 0.0075). D-01 is a **point-estimate rule**: it judges the
signed mean D against the margin and never against a confidence bound. The anchor 0.0168 is an order-of-magnitude
figure (226's content-instrument floor between differently warmed single-call grades), not a measured SD of this
metric.

| NAME | value | decision |
|---|---|---|
| `ARM_MODE` | `{'a0': 'round', 'a1': 'continuous'}` | D-15: A0 is A21S in round mode, A1 is continuous |
| `ARM_SEED` | `1` | D-15: every calibration cell runs on seed 1 |
| `BOOTSTRAP_CONFIDENCE` | `0.95` | report-only bootstrap lower bound |
| `BOOTSTRAP_SAMPLES` | `10000` | report-only |
| `BOOTSTRAP_SEED` | `227` | report-only |
| `CALIBRATION_THRESHOLD_MAIA` | `85.0` | D-15: 226's powered Maia threshold, unchanged |
| `CALIBRATION_THRESHOLD_SF` | `53.542812708469995` | D-15: 226's powered Stockfish threshold, unchanged |
| `EXIT_INCOMPLETE` | `2` | data not present yet |
| `EXIT_INVALID` | `1` | data that cannot be trusted |
| `EXPECTED_MQ_POSITIONS` | `60` | the widened fixture (226 D-14) |
| `EXPECTED_THROUGHPUT_POSITIONS` | `16` | SEED-126's canonical positions |
| `GAMES_PER_CELL_ANCHOR` | `50` | D-15: games per (cell, anchor) |
| `JUDGED_MQ_CELLS` | `('off', 'on')` | D-01: stop rule off isolates search quality, on is the shipped bot path |
| `LOAD_GATE_MAX` | `2.0` | a step above this 1-minute load average is a report-only warning |
| `MQ_A400_NODES` | `400` | D-20: the report-only analysis-400 cell |
| `MQ_ALLOWANCE_FLOOR` | `1` | D-03: floor of the net-regression allowance |
| `MQ_CONTENT_FLOOR` | `0.016804127272727273` | D-01: 226's content-instrument floor |
| `MQ_GRADE_DEPTH` | `20` | D-01: the d20 ground truth |
| `MQ_NODES` | `50` | judged cells run the bot-move path at the bot budget |
| `MQ_REGRESSION_MARGIN` | `0.05` | D-03: 226's move-quality regression definition |
| `MQ_REPEATS` | `5` | D-02: R = 5 repeats per arm per judged cell |
| `MQ_SIGNED_MARGIN` | `0.02520619090909091` | D-01: k x floor, about 3.3 net full-size flips over 60 positions |
| `MQ_SIGNED_MARGIN_K` | `1.5` | D-01: k |
| `POOL2_CONFIGS` | `('t50-p2', 't400-p2')` | D-04: the Node pool-2 configs |
| `POOL2_MIN_TOLERANCE` | `0.03` | D-04: pool-2 tolerance is `1 + max(noise, this)` |
| `SHAPE_GUARD_Z` | `1.96` | D-15: 226's shape guard, unchanged |
| `SHIP_BAR_CONFIGS` | `('stop-p4', 't400-p4')` | D-04: the two ship-bar configs |
| `THROUGHPUT_MAX_RATIO` | `1.03` | D-04: neither ship-bar config may regress beyond this ratio |
| `THROUGHPUT_MIN_ROUNDS` | `3` | D-17: interleaved rounds per judged config |
| `THROUGHPUT_SHIP_GAIN` | `0.15` | D-04: gain on stop-p4 or t400-p4 |
| `WEBGPU_MAX_RATIO` | `1.03` | D-07: continuous over round bot-move wall on the WebGPU machine |
| `WEBGPU_MIN_ROUNDS` | `3` | D-07: interleaved rounds |
| `WEBGPU_SCHEMA` | `'engine-bench-227/v1'` | the dev bench page's JSON schema |

The twin also holds four path constants (`DEFAULT_DATA_DIR`, `DEFAULT_VERDICT_JSON`, `BASELINE_A21S_DIR`,
`FIXTURE_PATH`). They are locations, not thresholds, and the pin test excludes them. The twin has no CLI flag,
environment variable or config file that reaches any row above.

## 3. Run parameters

All commands run from the repository root, from the orchestrator, one at a time, never from a `gsd-executor` subagent and
never backgrounded inside one (Phase 197 wave 2). The fixture is `fixtures/engine/move-quality-226.tsv`.

### Judged move quality (D-01, D-02, D-03)

One command per (arm, stop mode), run in this order: round-off, continuous-off, continuous-on, round-on. `<mode>` is
`round` for A0 and `continuous` for A1, `<arm>` is `a0` or `a1`.

```bash
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-move-quality.mjs \
  --arm <arm> --stop-rule <off|on> --dispatch-mode <mode> \
  --repeats 5 --maia-fifo --hash warm --grade-depth 20 --nodes 50 --procs 4 --pool-size 4 \
  --fixture fixtures/engine/move-quality-226.tsv \
  --out-dir reports/data/continuous-dispatch-227/gate/mq/<mode>/mq-<off|on>
```

### Report-only Clear-Hash move quality (D-02)

Both stop cells, both modes, one repeat, same order as above.

```bash
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-move-quality.mjs \
  --arm <arm> --stop-rule <off|on> --dispatch-mode <mode> \
  --repeats 1 --maia-fifo --hash clear --grade-depth 20 --nodes 50 --procs 4 --pool-size 4 \
  --fixture fixtures/engine/move-quality-226.tsv \
  --out-dir reports/data/continuous-dispatch-227/gate/mq-clear/<mode>/mq-<off|on>
```

### Report-only analysis-400 move quality (D-20)

Stop rule off, one repeat, both modes (round first).

```bash
node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-move-quality.mjs \
  --arm <arm> --nodes 400 --stop-rule off --dispatch-mode <mode> \
  --repeats 1 --maia-fifo --hash warm --grade-depth 20 --procs 4 --pool-size 4 \
  --fixture fixtures/engine/move-quality-226.tsv \
  --out-dir reports/data/continuous-dispatch-227/gate/mq-a400/<mode>/mq-off
```

### Interleaved throughput (D-04, D-17)

One session, driven by the committed driver, never improvised:

```bash
setsid nohup uv run python scripts/engine_interleave_227.py run \
  --data-dir reports/data/continuous-dispatch-227/gate/throughput > <scratch>/interleave.log 2>&1 &
```

Defaults are the judged values: 3 rounds, configs `stop-p4`, `t400-p4`, `t50-p2`, `t400-p2` rotated each round, both
arms alternating and reversed on even rounds, 24 steps. Before every step the driver waits for a 1-minute load average
below `LOAD_GATE_MAX` (bounded wait, a timeout is logged and is a report-only warning) and runs
`scripts/engine-speed-probe.mjs`. Probe constants (frozen in the probe, measured about 13.1 s of timed work):
`PROBE_SF_NODES = 1_800_000` per FEN over 5 `PROBE_FENS`, `PROBE_MAIA_INFERENCES = 60`, `PROBE_MAIA_ELO = 1500`. The
judged quantity per config and round is `(W_a1 / P_a1) / (W_a0 / P_a0)` (raw wall `W` over probe time `P`); the config's
ratio is the geometric mean over rounds. Abort by SIGTERM of the node process, relaunch the identical command with
`--resume`. The twin checks it with `throughput --data-dir reports/data/continuous-dispatch-227`.

### WebGPU continuous leg (D-07)

The owner runs the dev engine bench page (`/dev/engine-bench`, Plan 227-06) on a machine with a WebGPU adapter, over a
secure context with cross-origin isolation, using the interleaved button for at least `WEBGPU_MIN_ROUNDS` rounds. The
output is `reports/data/continuous-dispatch-227/webgpu/continuous-leg.json` (schema `engine-bench-227/v1`, leg
`interleaved`). The round-only legs already committed (`webgpu/round-leg.json`, `webgpu/local-wasm-round-leg.json`) are
report-only.

### Calibration (D-15)

Five runbook cells (`reports/bot-parity-199/runbook.md` section 1) times two arms, at 50 games per (cell, anchor), seed
1, with the runbook's pinned anchors. Never omit `PRESET_SUPERVISOR_ANCHORS` and never use the bare
`calibration-harness.mjs` driver. Output directories are `reports/data/sweep-227-<a0|a1>-<cell>`.

| Cell | blend | elo | `PRESET_SUPERVISOR_ANCHORS` |
|---|---|---|---|
| `human1100` | 0 | 1100 | `maia700,maia1100,sf0,sf3` |
| `light1300` | 0.05 | 1300 | `maia1100,maia1500,sf3,sf5` |
| `light1900` | 0.05 | 1900 | `maia1100,maia1500,sf3,sf5` |
| `deep1500` | 0.5 | 1500 | `maia1500,maia1900,sf3,sf5` |
| `deep2300` | 0.5 | 2300 | `maia1500,maia1900,sf3,sf5` |

```bash
PRESET_SUPERVISOR_DIR=reports/data/sweep-227-<arm>-<cell> \
PRESET_SUPERVISOR_ANCHORS=<anchors> \
PRESET_SUPERVISOR_GAMES=50 \
PRESET_SUPERVISOR_DISPATCH_MODE=<round for a0 | continuous for a1> \
nohup bin/preset-supervisor.sh 227-<arm>-<cell> <blend> <elo> \
  >> reports/data/sweep-227-<arm>-<cell>/supervisor-launch.log 2>&1 &
disown
```

At most 6 harness processes run at once. Launch same-cell A0/A1 pairs so both arms see the same load, deep cells first:
the `deep2300`, `deep1500` and `light1900` pairs, then `light1300`, then `human1100` as earlier pairs finish. Then, per
arm:

```bash
uv run python scripts/engine_throughput_226_verdict.py cells-to-json \
  --cells-tsv reports/data/sweep-227-<arm>-human1100/*-cells.tsv \
  --cells-tsv reports/data/sweep-227-<arm>-light1300/*-cells.tsv \
  --cells-tsv reports/data/sweep-227-<arm>-light1900/*-cells.tsv \
  --cells-tsv reports/data/sweep-227-<arm>-deep1500/*-cells.tsv \
  --cells-tsv reports/data/sweep-227-<arm>-deep2300/*-cells.tsv \
  --out-json reports/data/continuous-dispatch-227/gate/calibration/<arm>-cells.json

uv run python scripts/calibration_parity_verdict.py \
  --old-json reports/data/continuous-dispatch-227/gate/calibration/a0-cells.json \
  --new-cells-tsv reports/data/sweep-227-a1-human1100/*-cells.tsv \
  --new-cells-tsv reports/data/sweep-227-a1-light1300/*-cells.tsv \
  --new-cells-tsv reports/data/sweep-227-a1-light1900/*-cells.tsv \
  --new-cells-tsv reports/data/sweep-227-a1-deep1500/*-cells.tsv \
  --new-cells-tsv reports/data/sweep-227-a1-deep2300/*-cells.tsv \
  --out-json reports/data/continuous-dispatch-227/gate/calibration/verdict-a1-vs-a0.json
```

### The composed verdict

```bash
uv run python scripts/engine_dispatch_227_verdict.py gates \
  --data-dir reports/data/continuous-dispatch-227 \
  --out-json reports/continuous-dispatch-227/verdict.json
```

Exit 0 means complete and valid data, whatever the outcome. Exit 1 is invalid data and exit 2 is incomplete data. Read
pass or fail from the printed lines and the verdict JSON, never from the exit code.

## 4. Data layout

Exactly the layout the twin reads, under `reports/data/continuous-dispatch-227/`:

```
tripwire/parity-clear/{worker,main}/mq-{off,on}/   # committed before this rule (Plan 227-08)
tripwire/mq-{off,on}/                              # committed before this rule: warm-hash similarity vs 226 a21s, report-only
webgpu/round-leg.json, webgpu/local-wasm-round-leg.json   # committed before this rule, report-only
gate/mq/{round,continuous}/mq-{off,on}/            # judged, one TSV each
gate/mq-clear/{round,continuous}/mq-{off,on}/      # report-only
gate/mq-a400/{round,continuous}/mq-off/            # report-only
gate/throughput/manifest.tsv                       # plus run-meta.json and step dirs r{round}/{config}/{arm}/
gate/calibration/{a0,a1}-cells.json
gate/calibration/verdict-a1-vs-a0.json
webgpu/continuous-leg.json                         # judged (owner)
```

The calibration ledgers live under `reports/data/sweep-227-<a0|a1>-<cell>/`. Logs are not committed; ledgers and TSVs
are.

## 5. Sequencing

1. The box is idle: 1-minute load average below 2.0, no `remote_eval_worker` (stop it only with the user's permission),
   no test suite, build or sweep.
2. Order: judged move quality, then the report-only move-quality cells, then the throughput session, then calibration.
   The WebGPU leg is the owner's and is independent of the box.
3. Judged move quality, the report-only move-quality cells and the throughput session never overlap anything, including
   each other and calibration. Continuous mode is timing-dependent (RESEARCH Pitfall 8), so a concurrent process changes
   its content. Calibration processes overlap only each other, as the same-cell A0/A1 pairs of section 3.
4. This file's commit precedes the first commit under `gate/`. Plan 227-11 asserts
   `git merge-base --is-ancestor R HEAD` before each gate-data commit.

## 6. Criteria, in evaluation order

This is `run_gates`'s own order. A criterion later in the list is still evaluated and printed when an earlier one fails.

1. **Validity.** Any failure is exit 1 or 2 and no verdict exists.
   - Content assertions of section 1 pass, including the harness-content evidence (clear-hash parity PASS on `T`, and
     Plan 227-10's post-extraction re-run).
   - Every judged MQ row carries the `dispatch_mode` of its arm, `maia_fifo` true, `hash_mode` warm and `grade_depth`
     20. Every id is in the fixture. Each arm has exactly `MQ_REPEATS` repeats numbered 1 to 5, each with all 60 ids.
     Each directory holds exactly one TSV with the required columns.
   - Throughput: every manifest row has `rc` 0 and a `dispatch_mode` that matches its arm, with no duplicate rows. Each
     step has 16 judged rows whose `dispatch_mode` matches, `maia_fifo` true and `maia_peak_inflight` at most 1. Each
     judged config has at least `THROUGHPUT_MIN_ROUNDS` rounds with both arms, and probe times are positive.
   - WebGPU: the schema matches, the leg is `interleaved`, every row has backend `webgpu` and `modeObserved` equal to its
     requested mode, and at least `WEBGPU_MIN_ROUNDS` rounds carry both modes.
   - Calibration: the parity verdict JSON exists and is well formed.
   - **Not a validity check (owner direction, 2026-10-02).** Bit-identical round-mode results are not required with
     concurrent (off-thread) Maia inference. Under `--hash warm` with worker-thread Maia, round repeats differ slightly
     run to run (Plan 227-04 measured the minority pick on `cBFTV` in 14 of 130 repeats), and the round arm is not
     compared to 226's a21s files for equality. Both facts are recorded in `227-08-SUMMARY.md` and
     `227-08-TRIPWIRE-DEBUG.md`. The twin's `_check_round_determinism` raise was removed (commit `012856e92`) and
     replaced by the report-only round-repeat disagreement rate of section 7. D already averages each position over
     repeats and the D-03 net is already fractional, so the decision math is unchanged. RESEARCH Pitfall 8's "round
     repeats must show 0 diffs" and Q3's "free determinism tripwire" are superseded by this paragraph.
2. **D-01, per judged cell (stop off, stop on).** `D` is the mean over positions of (mean over repeats of the A1 `es_bot`
   minus mean over repeats of the A0 `es_bot`). The cell passes iff `D >= -MQ_SIGNED_MARGIN`, inclusive. Any positive `D`
   passes (D-00). A point estimate, never a confidence bound.
3. **D-03, per judged cell.** A regression is a row whose `verdict_bot` is `regression` (`MQ_REGRESSION_MARGIN` 0.05).
   `net = (A1 regressions - A0 regressions summed over positions and repeats) / MQ_REPEATS`, compared exactly as a
   fraction. The allowance is `A = max(MQ_ALLOWANCE_FLOOR, ceil(max over A1 repeat pairs r < s of |N_rs|))`, where
   `N_rs` is the count of pass-to-regression flips minus regression-to-pass flips between repeats r and s. The cell passes
   iff `net <= A`. A position where A1 fixes an A0 regression counts in A1's favor.
4. **D-17 ship bar.** Per config, the ratio is the geometric mean over rounds of `(W_a1 / P_a1) / (W_a0 / P_a0)` and the
   gain is `1 - ratio`. The bar is met iff the gain is at least `THROUGHPUT_SHIP_GAIN` on `stop-p4` or on `t400-p4`, AND
   neither ratio exceeds `THROUGHPUT_MAX_RATIO`.
5. **Pool-2 no-regression.** For `t50-p2` and `t400-p2`, `noise = max over rounds |A0_r / median(A0) - 1|` on the
   probe-normalized A0 walls, and the config passes iff `median(ratio_r) <= 1 + max(noise, POOL2_MIN_TOLERANCE)`.
6. **D-07 WebGPU point.** The median over rounds of (sum of A1 bot-move wall over sum of A0 bot-move wall) on the WebGPU
   machine is at most `WEBGPU_MAX_RATIO`. This is the only blocking point of the WebGPU measurement.
7. **D-15 calibration decides `refit_if_shipped` only and never blocks.** A void null control (human1100) escalates to
   the user. A powered shift (`CALIBRATION_THRESHOLD_MAIA`, `CALIBRATION_THRESHOLD_SF`, or the `SHAPE_GUARD_Z` shape
   guard) means ship plus one refit of the strength curves and the blend>0 persona labels. No shift means no refit.

The mechanical outcome is `ship-eligible` iff criteria 2, 3, 4, 5 and 6 all pass, and `hold` otherwise. It is evidence
for the owner, not the decision.

## 7. Report-only (never decisive)

- Bootstrap lower bound of D (resampling positions, repeats kept together), `K` (positions whose A1 pick changed across
  repeats), unsigned divergence (mean `|des|` between the arms), McNemar one-sided exact p on the majority-vote
  regression pairs, the analysis-selector D, flip size and the margin expressed in flips.
- **Round-repeat disagreement rate** (new, owner direction 2026-10-02): per judged cell, the number of positions whose
  `bot_move` differs across the A0 repeats, and that number over 60. It is in each cell's `report` in the verdict JSON and
  on the `MQ-REPORT` line. It has no threshold. Warm-hash similarity of the round arm to 226's a21s files
  (`tripwire` against the default baseline) is likewise information.
- The Clear-Hash move-quality cells and the analysis-400 move-quality cells (D-20).
- Raw wall ratios and grade-elapsed-normalized ratios per config (the grade-elapsed form is biased toward continuous
  mode, D-17), per-round load readings and load-gate timeout warnings.
- The Maia latency table of the WebGPU legs (idle and Stockfish-busy, per backend), and the round-only legs.
- Root-split premise violations in the throughput and stop-rule TSVs.

## 8. Virtual-loss trigger (D-08)

The trigger fires iff D-01 or D-03 fails in any judged cell (`virtual_loss_trigger` in the verdict JSON). Hard pending
exclusion is the default and the shipped design (`design.md` section 2.10). When the trigger fires, a report-only trace
of the worst positions runs, and the owner decides whether a Leela-style virtual-loss arm is planned. That arm would be a
gap-closure phase judged on the same criteria. It is never built inside this gate.

## 9. Owner decision and overrides

The mechanical verdict is evidence. The owner makes the final ship or hold call from it (D-04, D-00), as in 226. Any
departure from this rule, including shipping on a `hold` or holding on a `ship-eligible`, is a **separate dated override
document** (shape of `reports/engine-throughput-226/override-2026-10-02-owner-ship-decision.md`). This file is never
edited after it is committed. Round mode is a comparison arm, not a reference answer: a pick that differs from round
mode is information, and the d20 ground truth decides whether it is worse.

## 10. What must not happen

- Editing this file, or the twin's frozen constants, after any gate data exists. Departures are override documents.
- Running or backgrounding any gate step from a `gsd-executor` subagent. Every step runs from the orchestrator
  (`setsid nohup` plus Monitor, or `bin/preset-supervisor.sh`'s own resume loop).
- Overlapping judged move quality, the report-only move-quality cells or the throughput session with each other or with
  calibration, or running any of them on a loaded box.
- Launching a calibration cell without `PRESET_SUPERVISOR_ANCHORS` or `PRESET_SUPERVISOR_DISPATCH_MODE`, outside
  `bin/preset-supervisor.sh`, or with more than 6 harness processes at once.
- Starting the gate before Plan 227-10's post-extraction clear-hash parity re-run is recorded as TRIPWIRE PASS, or from a
  checkout that fails the content assertions of section 1.
- Any refit before the verdict and the owner's ship decision.
- Changing `FLAWCHESS_DISPATCH_MODE` before the owner's decision (Plan 227-13 makes that flip).
- Treating a round-repeat disagreement as invalid data, or tuning any constant after seeing a result.

---

*Phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi*
*Plan: 227-09*
