---
phase: 225-engine-search-fixes-root-comparability-round-underfill-findability
plan: 02
subsystem: engine-tooling
tags: [engine-gate-verdict, calibration-parity, python, stdlib-only, d11-machine-readable-twin]

# Dependency graph
requires:
  - phase: 225-01
    provides: "scripts/engine-move-quality.mjs column contract (arm, stop_rule, id, bot_move, delta_bot, verdict_bot, analysis_move, delta_analysis, verdict_analysis) and scripts/engine-dispatch-stop-rule.mjs's --root-trace/--guard-window TSV shape, both consumed as-is by this plan's readers"
provides:
  - "scripts/engine_search_fixes_verdict.py: gates/reruns/branch/cells-to-json — the D-11 machine-readable twin of reports/engine-search-fixes-225/accept-rule.md (written by 225-03), evaluating every Phase 225 gate criterion mechanically from the pinned reports/data/engine-search-fixes-225/{arm}/... data layout"
  - "The frozen threshold constants (THROUGHPUT_MAX_WALL_RATIO 1.05, MQ_REGRESSION_MARGIN 0.05, STOP_RULE_MAX_WALL_MS 12_100, STOP_RULE_MIN_EARLY_STOP_RETENTION 0.5, CALIBRATION_NEAR_MISS_FRACTION 0.75) that 225-03's accept-rule.md must transcribe verbatim"
  - "The exact pinned data-layout directory names (per-arm stop/throughput-50/throughput-400/mq-off/mq-on/mq-off-rerun/mq-on-rerun, plus calibration/verdict-*.json) that every later measurement plan (225-03..225-08) must write into"
affects: [225-03, 225-04, 225-05, 225-06, 225-07, 225-08]

# Actuals (#2632)
actuals:
  tokens: 15751
  tasks: 2
  commits: 3
  plan_head_before: f76e5b71c7e3c9c0214423e9d091ae9ff4698530
  plan_head_after: 4f19109c9b532033e39a344e9e346524cc695d1b

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Frozen-constants block with a one-line provenance comment per constant (mirrors scripts/calibration_parity_verdict.py's D-03 convention) — no threshold is reachable from argparse, env vars, or config (D-11)"
    - "`missing: list[str]` accumulator pattern: every input reader/evaluator failure is caught and appended rather than raised, so `gates` can render a complete picture of every gap in one run instead of failing at the first one"
    - "RESEARCH Pitfall 8's rerun-confirmation rule: a pass->regression flip with no rerun data makes the criterion `rerun-required` (passed=None), never a silent pass or fail; a rerun counts a flip only if it regresses again"
    - "Calibration fail-branch classification (`calibration_branch`) is a pure function over pooled shift/threshold read from a `calibration_parity_verdict.py`-shaped verdict JSON — sibling-imports that module's TypedDicts (`ParityVerdictResult`, `CellStats`, `CellKey`) rather than re-declaring them"

key-files:
  created:
    - scripts/engine_search_fixes_verdict.py
    - tests/scripts/test_engine_search_fixes_verdict.py
  modified: []

key-decisions:
  - "Task 1 (tracer) implemented only the calibration 'holds, not a near miss' success path inline in `run_gates`, marking every other branch as `missing` — Task 2 (tdd=\"true\") then replaced that stub with the full `calibration_item_decisions` decision table via a genuine RED (7 new tests failing on ImportError/argparse-invalid-choice) then GREEN (all 26 tests passing) cycle, per the plan's own task split."
  - "Test-file symbols for not-yet-implemented Task 2 functions were imported LOCALLY inside each test body (not at module scope) during the RED phase, so only the 7 tests exercising unimplemented behavior failed — the 19 already-passing Task 1 tests (plus 5 new `calibration_branch` boundary tests, already correct from Task 1) kept collecting and passing throughout. Moved to module-level imports once GREEN."
  - "`decide_items`'s `status: complete` vs `incomplete` is orthogonal to ship/hold: a fully-computed HOLD (e.g. a genuine throughput regression) is `status: complete` with `exit 0` — only missing/duplicate/unrerun data drives `status: incomplete` and `EXIT_INCOMPLETE` (T-225-03). A hold is a valid mechanical verdict, not an error."

requirements-completed: []

coverage:
  - id: D1
    description: "`scripts/engine_search_fixes_verdict.py gates` mechanically renders T-50/T-400 throughput, MQ-2/MQ-1 move quality (with rerun confirmation), S1/S2 stop rule, and the calibration fail-branch/decision table, mapping to D-14 item ship/hold outcomes, from the pinned reports/data/engine-search-fixes-225/ layout"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_search_fixes_verdict.py (26 tests over a synthetic arm layout, one per <behavior> bullet across both tasks)"
        status: pass
      - kind: other
        ref: "uv run python scripts/engine_search_fixes_verdict.py --help lists gates, reruns, branch, cells-to-json"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every frozen threshold constant carries a one-line provenance comment and is unreachable from any CLI flag/env var/config file (D-11); no threshold-shaped argparse flag exists"
    verification:
      - kind: other
        ref: "grep -E constants-and-values check (5/5 present) + grep -cE 'add_argument\\(.--(margin|threshold|ratio|ceiling)' == 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "gates/reruns never report a pass on missing, duplicate, or unconfirmed data (T-225-03) — status incomplete + exit 2 on any gap"
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_search_fixes_verdict.py::test_mq2_flip_without_rerun_is_incomplete_and_reruns_lists_a2_off, test_inadmissible_ladder_row_*, test_position_label_mismatch_*, test_duplicate_tsv_*, test_no_tsv_*, test_delta_verdict_disagreement_*, test_gates_decision_branch_missing_secondary_file_*"
        status: pass
    human_judgment: false
  - id: D4
    description: "cells_to_payload fits an arm's *-cells.tsv files into a {\"cells\": [...]} payload that calibration_parity_verdict.load_old_cells reads back unchanged, giving RESEARCH C-6's pre-registered fail branch an A0 comparison target"
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_search_fixes_verdict.py::test_cells_to_payload_round_trips_through_load_old_cells"
        status: pass
    human_judgment: false
  - id: D5
    description: "No change to frontend/src/ or scripts/calibration_parity_verdict.py; calibration_parity_verdict.py's own self-test still passes unmodified"
    verification:
      - kind: other
        ref: "git diff --name-only $(git merge-base main HEAD) HEAD -- frontend/src scripts/calibration_parity_verdict.py scripts/calibration_anchor_fit.py -> empty; uv run python scripts/calibration_parity_verdict.py --self-test -> OK"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-27
status: complete
---

# Phase 225 Plan 02: Engine Search Fixes Verdict Script Summary

**`scripts/engine_search_fixes_verdict.py` — a stdlib-only `gates`/`reruns`/`branch`/`cells-to-json` CLI that mechanically renders every Phase 225 accept-rule criterion (throughput, move quality, stop rule, the calibration fail-branch decision table) from a pinned per-arm data layout, and never reports a pass on missing or unconfirmed data.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-27 (see commit timestamps)
- **Completed:** 2026-09-27
- **Tasks:** 2
- **Files modified:** 2 (both created)

## Accomplishments

- **Task 1 (tracer):** `scripts/engine_search_fixes_verdict.py`'s `gates` and `reruns` subcommands — TSV readers (`read_single_tsv`), `evaluate_throughput` (T-50/T-400, with the continuous-dispatch admissibility check on `maia_peak_inflight`/`maia_fifo`), `evaluate_move_quality` (MQ-2/MQ-1, implementing RESEARCH Pitfall 8's rerun-confirmation rule), `evaluate_stop_rule` (S1 inclusive-ceiling / S2 early-stop-retention, plus report-only median/p90/D-04 exposure), `required_reruns`, and `decide_items` (D-14's exact ship/hold mapping). Calibration handling covered only the "holds, not a near miss" success path.
- **Task 2 (tdd, RED→GREEN):** `calibration_item_decisions` — the pre-registered D-13 amended / RESEARCH C-6 decision table for the "report-only" and "decision" branches (baseline-drift detection via `a0_vs_july`, item2/item1 pass conditions, void-counts-as-not-holds, attribution recording) — and `cells_to_payload`, the A0-cells converter that round-trips through `calibration_parity_verdict.load_old_cells`. Wired into `run_gates` (replacing Task 1's inline stub) and exposed via new `branch`/`cells-to-json` CLI subcommands.
- 26 pytest cases over a synthetic 16-position/12-position arm layout, one per `<behavior>` bullet across both tasks, driven entirely through `main(argv)` — never by calling the `evaluate_*` helpers directly — so the tests exercise the exact CLI path a real gate run takes.

## Task Commits

Each task was committed atomically (Task 2 added a genuine TDD RED→GREEN pair):

1. **Task 1: End-to-end gates verdict over a synthetic arm layout** - `40239a0ff` (feat)
2. **Task 2 RED: failing tests for calibration fail branch and cells converter** - `7e29d634a` (test)
3. **Task 2 GREEN: implement calibration fail branch, cells converter, branch subcommand** - `4f19109c9` (feat)

**Plan metadata:** committed alongside this SUMMARY.

_No REFACTOR commit — the GREEN implementation matched the plan's `<action>` spec directly with no follow-up cleanup needed._

## Files Created/Modified

- `scripts/engine_search_fixes_verdict.py` - the D-11 machine-readable twin: frozen constants, TSV readers, throughput/move-quality/stop-rule evaluators, calibration fail-branch classification + decision table, A0-cells converter, `gates`/`reruns`/`branch`/`cells-to-json` CLI
- `tests/scripts/test_engine_search_fixes_verdict.py` - 26 tests over a synthetic arm layout, one per `<behavior>` bullet

## Decisions Made

- Task 1's calibration handling deliberately covers only the "none" branch (holds, not a near miss) inline in `run_gates`, with every other branch marked `missing` — an intentional "delegation stub" per the plan's own task split, replaced in Task 2.
- Task 2's RED-phase test imports for not-yet-implemented symbols (`calibration_item_decisions`, `cells_to_payload`) were placed as LOCAL imports inside each new test function, not module-level, so only those 7 tests failed during RED while the 19 Task-1 tests (and 5 new `calibration_branch` boundary tests, already correct since `calibration_branch` was built in Task 1) kept passing — avoiding an INVALID_RED collection-error failure across the whole file.
- `status: complete`/`incomplete` is orthogonal to item ship/hold outcomes: a fully-computed hold (e.g., a genuine throughput regression) is `status: complete`, `exit 0` — only missing/duplicate/unrerun data drives `status: incomplete` / `EXIT_INCOMPLETE` (T-225-03).
- `write_calibration`'s test-helper parameter type was changed from `dict[str, object]` to `Mapping[str, object]` — `ty` treats a `TypedDict` as not assignable to a mutable `dict[...]` parameter (destructive-op safety), so the looser `Mapping` type was the correct fix rather than a cast.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<action>` and `<behavior>`/`<acceptance_criteria>` blocks were implemented as specified. All `ty` type-annotation adjustments during implementation (using `Mapping` instead of `dict` for read-only TypedDict parameters, explicitly typing test fixture return values, pre-declaring `attribution: CalibrationAttribution` before an if/else assignment) were straightforward `ty`-compliance fixes with no behavior change — not deviations from the plan's specified logic.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. No packages were installed.

## Next Phase Readiness

- **For 225-03 (writes `reports/engine-search-fixes-225/accept-rule.md`):** the accept rule's numbers MUST match this script's frozen constants verbatim — `THROUGHPUT_MAX_WALL_RATIO = 1.05`, `MQ_REGRESSION_MARGIN = 0.05`, `STOP_RULE_MAX_WALL_MS = 12_100`, `STOP_RULE_MIN_EARLY_STOP_RETENTION = 0.5`, `CALIBRATION_NEAR_MISS_FRACTION = 0.75` — and the accept rule's run-parameter section should reference this script by name as its machine-readable twin (D-11), the same relationship `reports/bot-parity-199/accept-rule.md` has with `scripts/calibration_parity_verdict.py`.
- **Pinned data layout every later plan (225-03..225-08) must write into**, relative to `reports/data/engine-search-fixes-225/`: `{arm}/stop/`, `{arm}/throughput-50/`, `{arm}/throughput-400/`, `{arm}/mq-off/`, `{arm}/mq-on/`, `{arm}/mq-off-rerun/` (only if MQ-2 flips), `{arm}/mq-on-rerun/` (only if MQ-1 flips) — each holding exactly ONE matching TSV — plus `calibration/verdict-a21-vs-july.json` (always required), `calibration/verdict-a0-vs-july.json`, `calibration/verdict-a2-vs-july.json`, `calibration/verdict-a2-vs-a0.json`, `calibration/verdict-a21-vs-a2.json`, `calibration/a0-cells.json`, `calibration/a2-cells.json` (all conditionally required depending on `calibration_branch`'s classification). Arms are `a0`, `a2`, `a21`, `final`.
- `scripts/engine_search_fixes_verdict.py gates --data-dir reports/data/engine-search-fixes-225 --out-json reports/engine-search-fixes-225/verdict.json` is ready to run the instant that layout exists — no further tooling work needed before real measurement passes begin.
- No blockers. `git diff --name-only $(git merge-base main HEAD) HEAD -- frontend/src` remains empty — confirmed no engine code has moved yet.

---
*Phase: 225-engine-search-fixes-root-comparability-round-underfill-findability*
*Completed: 2026-09-27*

## Self-Check: PASSED

- All 3 key files found on disk (`scripts/engine_search_fixes_verdict.py`, `tests/scripts/test_engine_search_fixes_verdict.py`, this SUMMARY).
- All 3 task commits (`40239a0ff`, `7e29d634a`, `4f19109c9`) found in git log.
- Re-ran plan-level `<verification>`: `uv run pytest tests/scripts/test_engine_search_fixes_verdict.py` 26/26 PASSED, `uv run ty check app/ tests/ scripts/` all checks passed, `uv run ruff check`/`ruff format --check` clean, `uv run python scripts/calibration_parity_verdict.py --self-test` PASSED.
- `git diff --name-only $(git merge-base main HEAD) HEAD -- frontend/src scripts/calibration_parity_verdict.py scripts/calibration_anchor_fit.py` empty — confirmed.
