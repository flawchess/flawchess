---
phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
reviewed: 2026-10-01T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - bin/preset-supervisor.sh
  - scripts/build-move-quality-fixture.mjs
  - scripts/calibration-harness.mjs
  - scripts/engine-dispatch-stop-rule.mjs
  - scripts/engine-grading-depth-ab.mjs
  - scripts/engine-move-quality.mjs
  - scripts/engine-root-split-content.mjs
  - scripts/engine-search-trace.mjs
  - scripts/engine_throughput_226_calibration.py
  - scripts/engine_throughput_226_verdict.py
  - scripts/lib/calibration-determinism.check.mjs
  - scripts/lib/calibration-providers.mjs
  - scripts/lib/node-engine-providers.mjs
  - scripts/lib/stockfish-pool.check.mjs
  - scripts/lib/stockfish-pool.mjs
  - tests/scripts/test_engine_throughput_226_calibration.py
  - tests/scripts/test_engine_throughput_226_verdict.py
findings:
  critical: 0
  warning: 7
  info: 4
  total: 11
status: issues_found
---

# Phase 226: Code Review Report

**Reviewed:** 2026-10-01
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

This is measurement tooling only: benchmark harnesses, a Stockfish process pool, a verdict reducer and its tests. I found no defect that, on the committed data, flips a threshold comparison or silently drops rows. The verdict arithmetic is correct: the throughput ratio, the paired MQ net/allowance, the candidate-weighted content mean, the null_check threshold inflation and the shipped-only refit reduction all hold up.

The recurring weakness is that the verdict's "never reports a pass on mislabeled data" guarantee is enforced for only one input class (throughput root-split columns). The other inputs trust the directory name. They are MQ TSVs, stop-rule TSVs (for S2), content TSVs, and the throughput config and pool size. The `reruns` subcommand also crashes when later-arm data does not exist yet. The mjs tools have a few diagnostic or provenance defects. The stockfish-pool split logic, the pool respawn config propagation and the `sendObserver` wrapper are sound.

No findings in `bin/preset-supervisor.sh`, `calibration-providers.mjs`, `node-engine-providers.mjs`, `calibration-harness.mjs`, `engine-dispatch-stop-rule.mjs`, `engine-grading-depth-ab.mjs` or `engine-move-quality.mjs` beyond what is noted below. Their changes are correctly threaded: `gradeRootFn` is conditional, `clearHash` and `sendObserver` are pinned on the pool for respawns, and `--pool-size` defaults after the parse loop.

## Warnings

### WR-01: `reruns` subcommand fails with EXIT_INVALID whenever any later arm has no MQ data yet

**File:** `scripts/engine_throughput_226_verdict.py:620-637` (caller at 1542-1546)
**Issue:** `required_reruns` iterates every spec from `_mq_pair_specs` and calls `read_single_tsv` on `base_dir` and `arm_dir` unconditionally. `run_gates` guards the same loop with `spec["base_dir"].is_dir()` / `spec["arm_dir"].is_dir()`, but `required_reruns` does not. The gate arms are produced in stacked order (A2, then A21, then A21S). After A2 is measured, the `a21-vs-a2` spec has no `gate/a21/mq-on`, so `read_single_tsv` raises `ValueError`. `main` maps that to `ERROR: ...` and `EXIT_INVALID` (a "data-integrity violation"). The operator therefore cannot ask which A2 reruns are required until every downstream arm has data. That defeats the point of the Pitfall-8 rerun-confirmation workflow, which has to run mid-ladder. The tests only exercise a full layout, so this is not caught.
**Fix:** Mirror `run_gates`' soft skip.
```python
for spec in _mq_pair_specs(data_dir):
    if not (spec["base_dir"].is_dir() and spec["arm_dir"].is_dir()):
        continue
    ...
```
Add a test with only the A2 layout present that expects the A2 rerun to be listed and exit 0.

### WR-02: S2 trivially passes on an A2 stop-rule TSV that was never validated as `stop_rule == "on"`

**File:** `scripts/engine_throughput_226_verdict.py:687-705`
**Issue:** `evaluate_stop_rule_s1` rejects rows whose `stop_rule != "on"`, but `evaluate_stop_rule_s2` checks only the row count of its two inputs. If `gate/a2/stop/` holds a `--no-stop-rule` run, whether through a mislabeled directory or a wrong flag, no row can have `stop_reason == "early-stop"`. `a2_early == 0`, so `trivial = True` and `passed = True`, regardless of what A21 does. This is the one verdict path where bad input produces an automatic pass on the guard item. It contradicts the module's stated contract ("never reports a pass on ... mislabeled data").
**Fix:** Validate both sides.
```python
for label, rows in (("a2", a2_rows), ("a21", a21_rows)):
    ...
    for row in rows:
        if row["stop_rule"] != "on":
            raise ValueError(f"evaluate_stop_rule_s2: {label} row {row['position']!r} has stop_rule={row['stop_rule']!r}, expected 'on'")
```
Also consider treating `trivial` (A2 has zero early stops) as a reported warning rather than a silent pass.

### WR-03: Mislabel validation covers only throughput root-split columns; MQ, content and config columns are trusted from the directory name

**File:** `scripts/engine_throughput_226_verdict.py:321-351, 399-411, 428-429, 457-461, 754-769`
**Issue:** Several related gaps weaken the "mislabeled data never passes" guarantee.
- `_MQ_REQUIRED_COLUMNS` is `("id", "delta_bot", "verdict_bot")`. The MQ TSV also carries `arm`, `stop_rule`, `root_split_calls` and `pool_size`, none of which are checked. A `mq-on` directory holding an off-mode run, or an `a21s` MQ directory whose `root_split_calls` is 0 on every row (a vacuous A21S measurement), is evaluated normally. The throughput side is checked for exactly this (D-08), the MQ side is not.
- `evaluate_content(rows, hash_mode, bound)` never compares `row["hash_mode"]` to `hash_mode`. A warm TSV dropped in `content/clear` is judged against the clear bound. The design-inputs path does filter on `hash_mode`, so the two readers disagree.
- Throughput validation reads `root_split_calls` and `root_split_premise_violations` but not `root_split_splits` (the column that proves a split actually ran). `splitAcrossFreeEngines` increments `calls` before the `k <= 1` / single-candidate early return, so `calls >= 1` does not prove a split. `pool_size` is also not compared across base/arm or against the config name (`p4` vs `p2`).
**Fix:** Add column checks. In the MQ reader, require `stop_rule` to equal the pair's mode, and for the `a21s`/`a21sc` arms require `root_split_calls >= 1` on every row. In `evaluate_content`, require `all(row["hash_mode"] == hash_mode)`. In `validate_root_split_columns`, also check `root_split_splits` for split arms. Compare `pool_size` to the value implied by the config.

### WR-04: `gates` reports `status: complete` and exits 0 when entire arms have no data

**File:** `scripts/engine_throughput_226_verdict.py:909-937, 985-1013, 1222, 1531`
**Issue:** `_throughput_pair_or_none`, the MQ loop, the stop-rule reads, the content reads, the determinism read and the calibration-verdict reads all skip silently (no `missing` entry) when the directory or file is absent. `status` is `complete` iff `missing` and `rerun_required` are empty, and the process exits 0. With only A2 data present, `gates` prints `STATUS complete` and `GUARD: hold / ROOT_SPLIT: hold`, and the process exits 0. The only trace of the absent data is the hold reason text ("failed or is missing"). A caller scripting on exit code or `status` cannot tell "held on evidence" from "held because never measured". Docs and tests show this is deliberate (tests comment "soft-skips to None"), but the exit code is then a misleading signal for a gate meant to be machine-readable.
**Fix:** Record each soft-skipped required criterion in a separate `absent` list, and make `status` `incomplete` (exit `EXIT_INCOMPLETE`) when any criterion required for a final verdict is absent. Alternatively add an explicit `--partial` flag for mid-ladder runs.

### WR-05: NaN `se_shift` / pooled shift silently fail to trigger a real shift

**File:** `scripts/engine_throughput_226_calibration.py:162-195, 233-235`
**Issue:** `null_check` raises on a NaN pooled SE, which shows awareness of the degenerate-SE case, but `_z_guard_cells` only guards `se_shift == 0`. With a NaN `se_shift` or `shift`, `z = nan`, `nan > z_guard` is `False`, and the cell is silently excluded from the shape guard. Likewise `_family_powered` gives `abs(nan) > threshold == False`. A degenerate comparison can therefore return `valid` with `real_shift = False`, which `refit_decision` reads as "no shift", whereas the module's stated policy is that a void or non-value result must never read as a silent no-refit.
**Fix:** In `_z_guard_cells` and `_family_powered`, `raise ValueError` (or return a void verdict) when `math.isnan(...)` for `shift` or `se_shift`, matching `null_check`.

### WR-06: Fixture builder stamps `depth-20` / `PER_BAND_QUOTA` into the header regardless of `--depth` / `--per-band`, and the default `--out` is the committed fixture

**File:** `scripts/build-move-quality-fixture.mjs:471-497, 509-540, 566-570`
**Issue:** `fixtureHeaderComment()` hard-codes `GROUND_TRUTH_DEPTH` (20) and "first PER_BAND_QUOTA keepers". The documented smoke override (`--depth 10 --per-band 1`) produces rows verified at depth 10 but with a header asserting depth-20 verification. `DEFAULT_OUT` is `fixtures/engine/move-quality-226.tsv`, the committed gate fixture, so an operator who runs the documented smoke command without `--out` silently overwrites the fixture with a falsely-labeled, 18-row, depth-10 file. `--check` would then reject it (fewer than 50 rows), but only if it is run. A fixture whose provenance header misstates how it was verified is a measurement-integrity problem.
**Fix:** Pass `args.depth` and `args.perBand` into `fixtureHeaderComment`. Refuse to write to `DEFAULT_OUT` when either override differs from its frozen default, or require an explicit `--out` for overrides.

### WR-07: Search-trace edge map is keyed by child FEN, so transpositions yield false `duplicate-expansion` anomalies

**File:** `scripts/engine-search-trace.mjs:253-262, 309-317`
**Issue:** `sink.edges` maps `childFen -> {parentFen, uci}` and keeps only the first edge (`!sink.edges.has(childFen)`). When two root-to-leaf paths reach the same position (a transposition, common in opening trees), both leaves reconstruct to the first path's UCI string. `detectAnomalies` then sees the same `leafPath` twice and emits `TRACE-ANOMALY kind=duplicate-expansion`. That is exactly the "same leaf graded twice" signature the tool exists to detect for the cBFTV D-13 diagnosis, so a legitimate transposition is indistinguishable from the D-08 bug. `leaf_fen` is also the only identifier written to the TSV, so the cBFTV comparison can't separate them after the fact.
**Fix:** Detect duplicates by `(leafFen, leafPath-derived-depth)` only when the FEN occurs at the same ply and the search treats nodes by path, or have the tracer record the real parent node identity. At minimum, downgrade the label to `duplicate-leaf-fen (may be a transposition)` and document the false-positive case.

## Info

### IN-01: `math.floor(g * 100) / 100` mis-floors some values

**File:** `scripts/engine_throughput_226_verdict.py:1340`
**Issue:** Binary floating point makes `g * 100` land just below an integer for some `g`. For example `0.29 * 100 = 28.999999999999996` (floor gives 0.28), and `0.57` and `0.58` likewise drop 0.01. The committed `ROOT_SPLIT_MAX_T50_WALL_RATIO = 0.97` is unaffected (`g = 0.03`), so there is no impact on the frozen constant, but the "floored DOWN to the nearest 0.01" rule is mis-implemented for P of about 0.58 or higher.
**Fix:** `g_floored = math.floor(round(g * 100, 9)) / 100`.

### IN-02: MQ regression classification is re-derived from a 6-decimal rounded `delta_bot`

**File:** `scripts/engine_throughput_226_verdict.py:446-449`; `scripts/engine-move-quality.mjs:501, 526`
**Issue:** The harness classifies `verdict_bot` on the unrounded `deltaBot <= -0.05` but writes `delta_bot.toFixed(6)`. The verdict re-classifies from the rounded string, deliberately ignoring `verdict_bot`. A raw delta such as -0.0499996 is `pass` in the harness and `regression` after rounding to -0.050000. The window is about 1e-6 wide, so it is practically negligible, but the two classifications can disagree on a boundary row.
**Fix:** Write more digits (or the raw `repr`) for `delta_bot`, or treat `verdict_bot` as an assertion and raise on disagreement.

### IN-03: `maia_anchor_identity` keys ignore `bot_elo` / `bot_blend`

**File:** `scripts/engine_throughput_226_calibration.py:287-320`
**Issue:** The ledger key is `(pass, anchor, game_index)`. The ledger also has `bot_elo` and `bot_blend` columns, and the harness accepts `--blends`/`--elo` lists. This is safe only if `game_index` is globally unique within a ledger and both ledgers cover the same cells. If either ledger spans several cells, rows from different cells collapse into one key (last wins) and the matched/identical counts are wrong. It is report-only and so low severity.
**Fix:** Include `bot_elo` and `bot_blend` in `_ledger_key`.

### IN-04: Fixture ground truth can mix search depths across MultiPV ranks

**File:** `scripts/build-move-quality-fixture.mjs:275-294`
**Issue:** `collected` is keyed by MultiPV rank and overwritten on every exact info line without recording depth. If the final-depth iteration emits a rank-1 exact line but no rank-2 exact line (it was bound-only and filtered), the rank-2 entry stays from an earlier depth. `mateAwareGapCp(top, second)` then mixes depths. Stockfish normally prints exact lines for the last completed iteration, so this is rare. Also `toCpEquivalent` returns `entry.cp` unvalidated, so a `null` cp with a `null` mate yields `NaN`, and `NaN < MIN_GAP_CP` is false, which makes the candidate "keep".
**Fix:** Store `depth` per rank and discard ranks whose depth is below the final `go depth`. Treat a `NaN` gap as `skip`.

---

_Reviewed: 2026-10-01_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
