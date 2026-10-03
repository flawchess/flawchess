---
phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
plan: 05
subsystem: testing
tags: [python, verdict-cli, stockfish, maia, calibration, throughput, pytest, ty]

# Dependency graph
requires:
  - phase: 226-03
    provides: "engine_throughput_226_calibration.py (null_check, powered_verdict, refit_decision, load_parity_verdict) and reports/engine-throughput-226/step0-protocol.md"
provides:
  - "scripts/engine_throughput_226_verdict.py — frozen constants, design-inputs / gates / reruns / cells-to-json subcommands, the machine-readable twin of the (not-yet-written) accept-rule.md"
affects: [226-06, 226-07, 226-08]

# Actuals (#2632)
actuals:
  tokens: 25349
  tasks: 3
  commits: 3
  plan_head_before: af18b25c15592f79bbfc6681dba736fef1652e47
  plan_head_after: 9320e495e2077dcd4f4f290f187613d53ea30f12

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Frozen-constants + design-input-constants split: every threshold from step0-protocol.md is a frozen module global at import time; the 10 design-input constants (EXPECTED_MQ_POSITIONS, MQ_ALLOWANCE_OFF/ON, CALIBRATION_THRESHOLD_MAIA/SF, ROOT_SPLIT_MAX_T50_WALL_RATIO, CONTENT_MAX_WARM/CLEAR_MEAN_ABS_DES, STOP_RULE_MAX_WALL_MS, CANDIDATE_CAP_ARM_ACTIVE) start None and `gates`/`reruns` refuse to run at all while any is unset, listing which ones (D-10, D-16)"
    - "Soft-skip-to-None over required-and-missing: every Task 2 gate criterion reads its directory with an `is_dir()` guard first and stores None (no `missing` entry) when the arm/mode/hash-mode subtree is simply absent — only a genuinely malformed present file becomes a `missing` entry. `decide_items` treats a None criterion as NOT passing (fail-closed), so `status` can reach `complete` long before every arm has run, while an item with unmeasured MQ still holds."
    - "RootSplitDataError (a ValueError subclass) is deliberately never caught by the same `read_soft` closure that catches ordinary missing-data ValueErrors — it propagates all the way to `main`, which maps it to EXIT_INVALID (1), distinct from EXIT_INCOMPLETE (2) for absent-but-not-yet-measured data"

key-files:
  created:
    - scripts/engine_throughput_226_verdict.py
    - tests/scripts/test_engine_throughput_226_verdict.py
  modified: []

key-decisions:
  - "A0's own throughput/MQ/stop baselines live under step0/ (never a gate/a0/ directory) — the underfill criterion is A2 vs step0 data; guard has no throughput criterion of its own (only S1/S2/MQ); root split and the candidate cap are each measured against their immediate stacked predecessor (A21S vs gate/a21, A21SC vs gate/a21s), mirroring the calibration verdict labels a2-vs-a0a/a21-vs-a2/a21s-vs-a21/a21sc-vs-a21s"
  - "validate_root_split_columns runs as a data-integrity pass over every stacked arm's present throughput data regardless of which criteria are implemented yet — a RootSplitDataError on an arm whose ship/hold decision isn't computed until a later task still halts `gates` with EXIT_INVALID, never silently ignored"
  - "STOP_RULE_MAX_WALL_MS is a design input (not the frozen STOP_RULE_225_CEILING_MS carried constant): `design-inputs` sets it to the 12,100ms ceiling only when the step-0 A0 idle-box max wall is below that ceiling, otherwise emits DESIGN-INPUT-ESCALATE stop-rule and the constant has no valid derived value"
  - "The D-17 candidate-cap share is read directly from profile_search.mjs's own totals.nonRootGt8Share JSON field (mean of the two runs per budget) rather than re-deriving it from the raw histogram rows — the upstream script already computes the exact D-17 formula, and re-deriving it in Python would be a second implementation of the same rule that could silently drift from the first"
  - "Root split's guard-independent criteria (determinism, T-50 gain bar, the other 3 throughput configs, both content bounds, MQ off) decide its ship/hold outcome on their own; S1@A21S and MQ(on)@A21S-vs-A21 become decisive ONLY when the guard also ships, otherwise they are computed and reported but do not block the split (must_haves, D-16)"

requirements-completed: []

coverage:
  - id: D1
    description: "engine_throughput_226_verdict.py transcribes every step0-protocol.md frozen constant verbatim, keeps the 10 design-input constants None until the A0 commit sets them, and gates/reruns refuse to run (EXIT_INCOMPLETE, listing names) while any design input is unset"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_gates_with_every_design_input_unset_exits_incomplete_and_lists_names"
        status: pass
      - kind: other
        ref: "grep -n \"GAMES_PER_CELL_ANCHOR = 50\" scripts/engine_throughput_226_verdict.py; grep add_argument for threshold/ratio substrings (plan's acceptance criteria)"
        status: pass
    human_judgment: false
  - id: D2
    description: "evaluate_throughput_pair and validate_root_split_columns render the underfill (A2-vs-A0) throughput criterion across all four configs and reject mislabeled root-split-activity data as invalid (EXIT_INVALID), never a silent pass (RESEARCH Pitfall 1, D-08)"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_underfill_throughput_passes_when_a2_is_95_percent_of_a0_in_all_configs"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_underfill_throughput_fails_when_one_config_is_106_percent"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_a21s_throughput_row_with_zero_root_split_calls_is_invalid_exit_1"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_a2_throughput_row_with_nonzero_root_split_calls_is_invalid_exit_1"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_a21s_root_split_premise_violation_is_invalid_exit_1"
        status: pass
    human_judgment: false
  - id: D3
    description: "evaluate_move_quality_paired implements the D-14 paired MQ rule (rerun-confirmed pass-to-regression flips only, net = counted p-to-r minus r-to-p, hold iff net > allowance) and required_reruns/`reruns` drive the rerun loop"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_paired_mq_three_reproduced_flips_and_one_regression_to_pass_holds"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_paired_mq_only_one_reproduced_flip_gives_net_zero_passes"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_reruns_lists_a2_off_for_unreproduced_flip_and_clears_once_rerun_exists"
        status: pass
    human_judgment: false
  - id: D4
    description: "evaluate_stop_rule_s1/s2 implement the S1 per-arm wall ceiling and S2 A21-vs-A2 early-stop retention rule with a trivial pass on zero A2 early stops"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_s1_fails_when_a21_max_wall_exceeds_ceiling"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_s2_fails_when_a21_early_stops_below_half_of_a2"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_s2_passes_trivially_when_a2_has_zero_early_stops"
        status: pass
    human_judgment: false
  - id: D5
    description: "decide_items implements the full D-12/D-15/D-16/D-17 stacked-arm ship/hold rules, including underfill cascading holds and root split's guard-independent-vs-decisive criterion split"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_full_passing_layout_ships_underfill_guard_and_root_split"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_root_split_holds_when_t50_ratio_exceeds_bound"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_root_split_holds_when_warm_content_mean_exceeds_bound"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_root_split_holds_when_determinism_pass_line_missing"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_guard_held_root_split_ships_with_s1_and_mq_on_report_only"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_underfill_held_cascades_to_guard_root_split_and_cap_all_held"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_candidate_cap_inactive_requires_no_a21sc_data_and_is_absent_from_items"
        status: pass
    human_judgment: false
  - id: D6
    description: "Calibration integration (powered_verdict + refit_decision over shipped items only) reproduces refit / no-refit / escalate exactly as D-10/D-11 require"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_calibration_real_shift_on_shipped_underfill_gives_refit"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_calibration_real_shift_on_held_guard_alone_gives_no_refit"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_calibration_void_verdict_for_shipped_item_gives_escalate"
        status: pass
    human_judgment: false
  - id: D7
    description: "design_inputs computes every D-16 section 7 formula (EXPECTED_MQ_POSITIONS, MQ_ALLOWANCE_OFF/ON, calibration thresholds, ROOT_SPLIT_MAX_T50_WALL_RATIO with its 0.01 floor rounding, content bounds from the warm noise floor, D-17 candidate-cap activation, STOP_RULE_MAX_WALL_MS with escalation) mechanically from step-0 data and exits EXIT_INCOMPLETE listing missing paths on an empty data dir"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_expected_mq_positions_equals_fixture_data_row_count"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_mq_allowance_is_max_1_and_run_to_run_flip_count"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_calibration_thresholds_follow_null_check_and_escalate_prints"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_root_split_ratio_p_012_gives_g_006_ratio_094"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_root_split_ratio_p_004_floors_g_at_003_ratio_097"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_content_bounds_warm_noise_floor_002_gives_warm_003_clear_002"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_d17_shares_055_045_at_50_nodes_mean_050_fires_cap"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_d17_shares_below_half_at_both_budgets_do_not_fire_cap"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_stop_rule_max_wall_ms_is_12100_when_a0_max_is_below_it"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_stop_rule_escalates_when_a0_max_meets_or_exceeds_ceiling"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_design_inputs_on_empty_dir_exits_incomplete"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_verdict.py#test_cells_to_json_round_trips_through_load_old_cells"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-28
status: complete
---

# Phase 226 Plan 05: Verdict CLI — frozen constants, gate criteria, design-inputs Summary

**`engine_throughput_226_verdict.py`, the machine-readable twin of the (not-yet-written) accept-rule: 20 frozen constants transcribed from step0-protocol.md, 10 design-input constants derivable only from committed step-0 data, and `gates`/`reruns`/`design-inputs`/`cells-to-json` subcommands rendering every Phase 226 ship/hold decision plus the shipped-items-only refit call as a pure function of committed TSV/JSON data.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-09-28
- **Completed:** 2026-09-28
- **Tasks:** 3 completed
- **Files modified:** 2 (both new)

## Accomplishments

- `scripts/engine_throughput_226_verdict.py` transcribes every frozen constant from `step0-protocol.md` verbatim and declares the 10 design-input constants `None`, refusing to run `gates`/`reruns` at all while any is unset (D-10, D-16) — no threshold is reachable from any CLI flag, env var, or config file.
- `evaluate_throughput_pair` + `validate_root_split_columns` render the underfill throughput criterion (A2 vs the step-0 A0 baseline) across all four throughput configs and reject a root-split-activity mismatch on ANY stacked arm's data as invalid (`EXIT_INVALID`), independent of which task last touched that arm's ship/hold criteria.
- `evaluate_move_quality_paired` implements the D-14 paired MQ rule exactly (rerun-confirmed flips only, `net = counted pass-to-regression - regression-to-pass`, hold iff `net > allowance`), plus a report-only McNemar exact one-sided p-value; `required_reruns`/`reruns` drive the "repeat until NO RERUNS REQUIRED" loop.
- `evaluate_stop_rule_s1/s2`, `evaluate_content`, and `evaluate_determinism` render the stop-rule wall ceiling, early-stop retention, root-split content bound (candidate-weighted mean `|delta es|` over `split_source=pool` rows), and the D-08 `"PASS: calibration determinism"` check.
- `decide_items` implements the full D-12/D-15/D-16/D-17 stacked-arm rules: underfill gates guard and root split (a held underfill cascades to hold everything downstream); root split's own guard-independent criteria decide its ship/hold outcome on their own, with `S1@A21S` and `MQ(on)@A21S-vs-A21` becoming decisive only when the guard ALSO ships; the candidate cap requires root split to ship first.
- Calibration integrates `engine_throughput_226_calibration.powered_verdict`/`refit_decision` over the shipped items only, reproducing `refit`/`no-refit`/`escalate` exactly per D-10/D-11.
- `design_inputs` computes every D-16 section 7 formula mechanically from committed step-0 data — `EXPECTED_MQ_POSITIONS`, `MQ_ALLOWANCE_OFF/ON`, the powered calibration thresholds (with `DESIGN-INPUT-ESCALATE` on a large null drift), `ROOT_SPLIT_MAX_T50_WALL_RATIO` (with its `0.03` gain floor and `0.01` floor-rounding), the content bounds (both derived from the SAME warm noise floor), `CANDIDATE_CAP_ARM_ACTIVE` (D-17, reading `profile_search.mjs`'s own `totals.nonRootGt8Share`), and `STOP_RULE_MAX_WALL_MS` (with its own escalation branch) — and exits `EXIT_INCOMPLETE` listing every missing step-0 path on an empty `--data-dir`.
- `cells-to-json` delegates unchanged to the Phase 225 twin's `cells_to_payload`/`fit_new_cells`.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end gate slice — frozen constants, data layout, underfill throughput** — `1fb0c4127` (feat)
2. **Task 2: All criteria, item decisions, reruns, calibration and refit** — `172dfdb6e` (feat)
3. **Task 3: `design-inputs` and `cells-to-json`** — `9320e495e` (feat)

**Plan metadata:** committed with this SUMMARY (docs commit follows).

## Files Created/Modified

- `scripts/engine_throughput_226_verdict.py` — frozen constants, design-input constants, data-layout path helpers, `evaluate_throughput_pair`, `validate_root_split_columns`, `evaluate_move_quality_paired`, `evaluate_stop_rule_s1/s2`, `evaluate_content`, `evaluate_determinism`, `decide_items`, `design_inputs`, and the `gates`/`reruns`/`design-inputs`/`cells-to-json` CLI subcommands.
- `tests/scripts/test_engine_throughput_226_verdict.py` — 34 tests covering every `<behavior>` bullet across all three tasks, driven exclusively through `main(argv)`.

## Decisions Made

- A0's own throughput/MQ/stop baselines live under `step0/` (never a `gate/a0/` directory); underfill is A2-vs-step0-A0, guard has no throughput criterion of its own, and root split/cap are each measured against their immediate stacked predecessor — mirroring the calibration verdict labels exactly (`a2-vs-a0a`, `a21-vs-a2`, `a21s-vs-a21`, `a21sc-vs-a21s`).
- Every Task 2 criterion soft-skips to `None` (no `missing` entry) when its subtree is simply absent, rather than blocking on incomplete-but-not-yet-run arms; `decide_items` treats `None` as NOT passing, so a genuinely malformed present file is the only thing that keeps `status` at `incomplete`.
- `RootSplitDataError` is a distinct `ValueError` subclass that is never caught by the "soft" missing-data closure — it always propagates to `EXIT_INVALID`, keeping "wrong data" and "not-yet-measured data" as two different, never-conflated exit codes.
- D-17's candidate-cap share is read directly from `profile_search.mjs`'s own `totals.nonRootGt8Share` JSON field rather than re-derived from the raw histogram in Python, avoiding a second implementation of the same formula that could silently drift from the first.

## Deviations from Plan

None — plan executed exactly as written. All three `<behavior>` blocks are covered by dedicated tests, the Task 2 mutation check was performed and reverted (see below), and nesting depth was kept <= 4 throughout (one refactor: `_throughput_pair_or_none` was extracted from `run_gates` when the root-split and candidate-cap throughput loops initially hit depth 5 — `scripts/check_function_size.py` confirms 50 functions scanned, no breaches after the extraction).

### Mutation check (Task 2 acceptance criterion)

Temporarily changed `evaluate_move_quality_paired`'s `net` calculation from `len(reproduced) - len(regression_to_pass)` (only rerun-confirmed flips count) to `len(pass_to_regression) - len(regression_to_pass)` (every flip counts, confirmed or not). Confirmed `test_paired_mq_only_one_reproduced_flip_gives_net_zero_passes` then FAILED:

```
AssertionError: assert 2 == 0
```

Restored the reproduced-only calculation and reconfirmed all 22 tests (34 after Task 3) pass, `ty check`/`ruff check`/`ruff format --check` clean.

---

**Total deviations:** 0. **Impact:** None — plan executed as written; the one mid-task refactor (depth-5 fix) is implementation detail, not a scope or behavior change.

## Issues Encountered

None. The `bash` sandbox's git-safety heuristic occasionally rejected multi-line heredoc commands as "too complex to verify" inside this worktree; worked around by writing commit messages to a scratchpad file and using `git commit -F <file>` instead.

## User Setup Required

None — no external service configuration required. No `fixtures/engine/move-quality-226.tsv` exists yet (a later plan's D-14 deliverable); `design-inputs` correctly reports it as missing rather than inventing a default.

## Next Phase Readiness

- `scripts/engine_throughput_226_verdict.py` is ready for Plan 226-08 (the A0 commit): run `design-inputs` against the real step-0 data once it exists, transcribe every `DESIGN-INPUT`/`DESIGN-INPUT-ESCALATE` line verbatim into the frozen design-input constants and `reports/engine-throughput-226/accept-rule.md`.
- The `gates` subcommand is fully wired for all four stacked arms (A2/A21/A21S/A21SC) and the shipped-items-only refit decision; nothing further needs to change in this file once real data lands, only the design-input constants themselves (set once, in the A0 commit).
- No blockers for Plan 226-06 (the content-instrument harness landing the `split-root-content-*.tsv` contract this plan already reads) or Plan 226-07/226-08 (step-0 runs and the A0 commit).

---
*Phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: scripts/engine_throughput_226_verdict.py
- FOUND: tests/scripts/test_engine_throughput_226_verdict.py
- FOUND commit: 1fb0c4127 (Task 1)
- FOUND commit: 172dfdb6e (Task 2)
- FOUND commit: 9320e495e (Task 3)
- `uv run pytest tests/scripts/test_engine_throughput_226_verdict.py -x` — 34 passed
- `uv run ty check scripts/engine_throughput_226_verdict.py tests/scripts/test_engine_throughput_226_verdict.py` — All checks passed
- `uv run ruff check` / `uv run ruff format --check` on both files — All checks passed
- `uv run python scripts/check_function_size.py scripts/engine_throughput_226_verdict.py --fail-over-depth 4` — OK: 50 functions scanned, no breaches
- `uv run python scripts/engine_throughput_226_verdict.py design-inputs --data-dir <empty tmp dir>` — exits 2, lists all missing step-0 paths
- `grep -n "GAMES_PER_CELL_ANCHOR = 50" scripts/engine_throughput_226_verdict.py` — found; no argparse option name contains "threshold" or "ratio"
