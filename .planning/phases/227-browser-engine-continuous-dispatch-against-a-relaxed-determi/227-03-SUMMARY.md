---
phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi
plan: 03
subsystem: testing
tags: [engine, verdict-twin, accept-rule, pre-registration, stdlib, pytest]

requires:
  - phase: 226
    provides: "engine_throughput_226_calibration powered_verdict, committed a21s round-mode MQ TSVs, move-quality-226 fixture, read_single_tsv"
provides:
  - "scripts/engine_dispatch_227_verdict.py: frozen-constant verdict twin with tripwire, mq, throughput, webgpu and gates subcommands"
  - "tests/scripts/test_engine_dispatch_227_verdict.py: 90 tests pinning constants, arithmetic, boundaries and invalid/incomplete exits"
affects: [227-04, 227-07, 227-08, 227-09, 227-11, 227-12]

actuals:
  tokens: 28800
  tasks: 2
  commits: 4
plan_head_before: 5747916856992a7422efac837c2ae69948edd1b3
plan_head_after: 349396f5cd62d4c512cb24b48794c591b2f4d8bd

tech-stack:
  added: []
  patterns:
    - "Frozen thresholds as module constants pinned by test_frozen_constants, never CLI/env reachable"
    - "Exit 0 whenever inputs are complete and valid (pass/fail read from printed lines and JSON), exit 1 invalid, exit 2 incomplete"
    - "Verdict JSON written only after every judged input was read and validated"

key-files:
  created:
    - scripts/engine_dispatch_227_verdict.py
    - tests/scripts/test_engine_dispatch_227_verdict.py
  modified: []

key-decisions:
  - "D-01 is judged as a point estimate D >= -0.02520619090909091 (inclusive), D = mean over positions of (mean over repeats continuous es_bot minus mean over repeats round es_bot); bootstrap LCB, K, unsigned |des|, McNemar and the analysis-selector D are report-only"
  - "D-03 net is computed exactly with fractions.Fraction (continuous regression count minus round regression count, over MQ_REPEATS), so a net equal to the allowance passes without float noise"
  - "gates requires the calibration verdict JSON (the verdict always carries refit_if_shipped), and does not itself run the tripwire (Plans 227-08 and 227-11 run it as the validity step)"
  - "Throughput is judged on the geometric mean of per-round (W_a1/P_a1)/(W_a0/P_a0); raw and grade-elapsed ratios are reported only"

patterns-established:
  - "Missing column, missing file, duplicate TSV, too few repeats/rounds map to IncompleteDataError (exit 2); mislabeled or leaking data maps to InvalidDataError (exit 1)"

requirements-completed: []

coverage:
  - id: D1
    description: "MQ verdict: D-01 signed point-estimate rule and D-03 net-regression allowance, frozen constants, report-only statistics inert"
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_dispatch_227_verdict.py#test_d01_exact_margin_passes"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_dispatch_227_verdict.py#test_d03_net_equal_to_allowance_passes_and_above_fails"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_dispatch_227_verdict.py#test_report_only_inputs_cannot_change_the_verdict"
        status: pass
    human_judgment: false
  - id: D2
    description: "Round-mode tripwire against the committed 226 a21s TSVs, proven on the real committed files"
    verification:
      - kind: other
        ref: "uv run python scripts/engine_dispatch_227_verdict.py tripwire --mq-dir reports/data/engine-throughput-226/gate/a21s (prints TRIPWIRE PASS)"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_dispatch_227_verdict.py#test_tripwire_committed_226_data_self_comparison"
        status: pass
    human_judgment: false
  - id: D3
    description: "Throughput ship bar, pool-2 noise rule, WebGPU point, calibration refit decision and the composed gates verdict"
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_dispatch_227_verdict.py#test_gates_all_passing_is_ship_eligible"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_dispatch_227_verdict.py#test_gates_missing_judged_input_is_incomplete_and_writes_nothing"
        status: pass
    human_judgment: false
  - id: D4
    description: "Whether the pre-registered numbers (margin 0.0252, 15%/3% ship bar, 3% WebGPU point) are the right ones is the owner's call at accept-rule commit time (Plan 227-09), not something this plan tests"
    verification: []
    human_judgment: true
    rationale: "The constants are transcribed from CONTEXT/RESEARCH decisions; their adequacy is a judgment, pinned here but not validated by data"

duration: 55min
completed: 2026-10-02
status: complete
---

# Phase 227 Plan 03: Verdict Twin Summary

**Stdlib verdict twin for the Phase 227 accept rule: frozen D-01/D-03/D-04/D-07/D-15/D-17 constants, a round-mode tripwire proven on the committed 226 a21s data, and a `gates` command that composes MQ, interleaved probe-normalized throughput, WebGPU and calibration into a mechanical ship-eligible/hold verdict.**

## Performance

- **Duration:** about 55 min
- **Tasks:** 2 (Task 1 tracer, Task 2 auto; both TDD)
- **Files:** 2 created (`scripts/engine_dispatch_227_verdict.py` 1500 lines, `tests/scripts/test_engine_dispatch_227_verdict.py` 90 tests)

## Accomplishments

- **Frozen accept rule in code.** Every constant the plan lists is a module constant and `test_frozen_constants` pins each literal value; `MQ_SIGNED_MARGIN == MQ_SIGNED_MARGIN_K * MQ_CONTENT_FLOOR` is asserted to 1e-12. A test confirms no threshold is reachable from the CLI (argparse rejects `--margin`, `--repeats`, `--ship-gain`, `--max-ratio`).
- **D-01 / D-03.** `d01_passes` is inclusive (`D >= -margin`, a better continuous mode passes). D-03 uses the continuous regression fraction minus the round fraction (a continuous fix lowers net), compared exactly via `Fraction` against `mq_allowance` = `max(1, ceil(max over repeat pairs |pass->reg minus reg->pass|))`, a signed net so two repeats that swap one regression for another do not widen it.
- **Tripwire.** `tripwire --mq-dir` compares every row of every repeat to the 226 baseline on `bot_move`, `analysis_move`, `nodes_evaluated`, `stop_reason`, and `es_bot` only when `grade_depth` matches; a candidate `dispatch_mode` must be `round`; a missing `repeat` column reads as repeat 1. Self-comparison of the committed `reports/data/engine-throughput-226/gate/a21s` prints `TRIPWIRE off rows=60 diffs=0`, `TRIPWIRE on rows=60 diffs=0`, `TRIPWIRE PASS`.
- **Throughput (D-17).** Manifest + step TSVs are validated (arm/mode labels, one-in-flight FIFO Maia, rc 0, exactly 16 positions, ladder rows only for depth-ab) and judged on the geometric mean of the per-round probe-normalized ratio. Ship bar: gain >= 0.15 on `stop-p4` or `t400-p4` and ratio <= 1.03 on both. Pool-2: `median(ratio) <= 1 + max(noise, 0.03)` with noise from the probe-normalized A0 walls. Raw and grade-elapsed-normalized ratios and load-gate warnings are report-only.
- **WebGPU (D-07), calibration (D-15), gates.** WebGPU requires `webgpu` backend rows whose observed mode equals the requested one, >= 3 rounds with both modes, and judges the median wall ratio against 1.03. Calibration imports 226's `powered_verdict` unchanged (85.0 / 53.542812708469995 / z 1.96) and maps to `refit` / `escalate` / `no-refit`. `gates` writes the verdict JSON only when everything is complete and valid.

## Task Commits

| Task | Phase | Commit | Description |
|------|-------|--------|-------------|
| 1 | RED | `7dacc05e7` | failing MQ twin tests plus constants/stub skeleton |
| 1 | GREEN | `484bdf1fa` | MQ twin: tripwire, D-01, D-03, report-only, CLI |
| 2 | RED | `1cd029cc4` | failing throughput / WebGPU / calibration / gates tests |
| 2 | GREEN | `349396f5c` | throughput, pool-2, WebGPU, calibration, gates |

## TDD Gate Compliance

RED and GREEN commits exist for both tasks (`test(227-03)` precedes `feat(227-03)`); no REFACTOR commits (none needed). Honest caveat on RED quality under the #3770 reading: Task 1's RED commit carried a skeleton module (constants plus `NotImplementedError` stubs), so its behavior tests failed on `NotImplementedError` rather than on an assertion; Task 2's RED tests failed on missing attributes and unknown argparse subcommands. The four constant/surface tests of Task 1 passed at RED by construction (the skeleton held the frozen constants). `gsd_run check tdd-red-evidence` was not run (plan type is `execute`, TDD is per task).

## Mutation Checks (acceptance criteria)

All reverted afterwards; 90 tests green on the restored module.

| Mutation | Result |
|----------|--------|
| D-01 comparison `>=` flipped to strict `>` | `test_d01_exact_margin_passes` fails |
| Round-repeat validity check removed (`_check_round_determinism`) | `test_invalid_round_repeats_differ` fails |
| Throughput judged on arithmetic mean of raw walls instead of the probe-normalized geometric mean | `test_throughput_probe_normalization_cancels_machine_speed` and `test_throughput_uses_the_geometric_mean_over_rounds` fail |
| WebGPU backend check removed | `test_webgpu_wasm_backend_row_is_invalid` and `test_gates_invalid_input_writes_nothing` fail |

## Verification

- `uv run pytest tests/scripts/test_engine_dispatch_227_verdict.py -q`: 90 passed (82 `def test_`, parametrized to 90); together with the 226 verdict and calibration tests, 142 passed.
- `uv run python scripts/engine_dispatch_227_verdict.py tripwire --mq-dir reports/data/engine-throughput-226/gate/a21s`: `TRIPWIRE PASS`.
- `gates --data-dir <empty dir>`: exit 2, no verdict JSON.
- `ruff check`, `ruff format --check` clean; `uv run ty check scripts/ tests/scripts/`: all checks passed (after `uv sync --group maia-inference`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fresh worktree lacked the maia-inference group**
- **Found during:** Task 2 verification (`ty check scripts/`)
- **Issue:** plain `uv sync` leaves 3 phantom `unresolved-import` errors (numpy, onnxruntime) in unrelated `scripts/maia_parity_spike.py` and `scripts/engine_disagreement_study/gate0_null_baselines.py`.
- **Fix:** `uv sync --group maia-inference` (environment only, no tracked file changed). ty is then clean.

### Interpretation choices (no plan text changed)

- **Regression flag.** The plan text writes `verdict_bot == "regression"` with `delta_bot < -MARGIN`, while the harness (`engine-move-quality.mjs`) emits `regression` for `delta_bot <= -MARGIN`. The twin trusts the `verdict_bot` column (single source with the harness, rejecting any other value as invalid), so there is no second implementation to disagree at the 0.05 boundary.
- **Gates inputs.** `gates` requires `gate/calibration/verdict-a1-vs-a0.json` because the verdict JSON always carries `refit_if_shipped` (Plan 227-12 asserts the key). It does not run the tripwire itself; Plans 227-08 and 227-11 run it as the validity step before judging. Say so in the accept rule (Plan 227-09) if the owner wants the tripwire folded into `gates`.
- **Exit mapping.** `IncompleteDataError` (missing directory/file/column, duplicate TSV, too few repeats/rounds) maps to exit 2; `InvalidDataError` and any other `ValueError` (unparseable numbers) map to exit 1. An id that is not in the fixture is invalid even when another id is missing (checked before completeness).
- **Row-count rule for MQ.** Exactly `MQ_REPEATS` repeats numbered 1..5; fewer is incomplete, more or odd numbering is invalid.
- **Report-only specifics.** McNemar uses position-level majority classification (more than half of the repeats regress); the flip-unit reading is `margin / mean |es_cont - es_round|` over changed picks, times the position count for `margin_flips`; the bootstrap is a seeded 10000-sample resample of per-position differences (5th percentile as the one-sided 95% LCB). Clear-Hash and analysis-400 cells that are present but malformed are reported as `unreadable` and never raise.

**Total deviations:** 1 auto-fixed (environment), 0 plan-file edits. **Impact:** none on scope.

## Known Stubs

None.

## Threat Flags

None. Stdlib-only, no endpoints, no network, no package installed (T-227-SC mitigated). T-227-05 (frozen thresholds) and T-227-06 (missing/mislabeled data) are covered by `test_frozen_constants`, the invalid/incomplete exit tests and the no-JSON-unless-complete test; Plan 227-09 adds the accept-rule pin test.

## Self-Check: PASSED

- `scripts/engine_dispatch_227_verdict.py` and `tests/scripts/test_engine_dispatch_227_verdict.py` exist.
- Commits `7dacc05e7`, `484bdf1fa`, `1cd029cc4`, `349396f5c` exist on the worktree branch.
- All task `<automated>` verify commands and acceptance criteria re-run and pass (see Verification).
