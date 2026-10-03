---
phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
plan: 03
subsystem: testing
tags: [python, calibration, statistics, pytest, ty, stockfish, maia]

# Dependency graph
requires: []
provides:
  - "scripts/engine_throughput_226_calibration.py — null_check, powered_verdict, refit_decision, maia_anchor_identity, load_parity_verdict (pure, typed, stdlib-only)"
  - "reports/engine-throughput-226/step0-protocol.md — pre-registered step-0 parameters and design-input derivation rules, committed with no step-0 data present"
affects: [226-05, 226-06, 226-07, 226-08]

# Actuals (#2632)
actuals:
  tokens: 10593
  tasks: 3
  commits: 3
  plan_head_before: 75a9cf50a49744e6d6e9a2e3ed2e3295a2a09b45
  plan_head_after: ff665a9fbdc2540b873ece9fbfb5d8152b7e1640

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Threshold-as-parameter calibration module: engine_throughput_226_calibration.py holds no frozen constants — mirrors calibration_anchor_fit.py's parametric convention while engine_throughput_226_verdict.py (Plan 226-05) carries the frozen twin, per calibration_parity_verdict.py's established split"
    - "z-based shape guard (|shift|/se_shift > 1.96 in both families) replaces the Phase 199 CI-overlap shape guard, which fired at a rate independent of sample size"

key-files:
  created:
    - scripts/engine_throughput_226_calibration.py
    - tests/scripts/test_engine_throughput_226_calibration.py
    - reports/engine-throughput-226/step0-protocol.md
  modified: []

key-decisions:
  - "load_parity_verdict and null_check import Family/ParityVerdictResult/FamilyResult/ExposedCellResult directly from calibration_parity_verdict.py rather than redefining them, mirroring engine_search_fixes_verdict.py's own import convention"
  - "refit_decision's escalate branch also fires when a shipped item's verdict is entirely absent from the verdicts mapping, not only when it is void — a missing attribution is exactly as dangerous as a void one for D-11's ship-and-refit contract"
  - "maia_anchor_identity compares result/plies/reason/cp_loss_sum as exact string equality (ledger rows come from csv.DictReader, every field a string) rather than parsing numerics, since RESEARCH F-7 established byte-identical replay reproduces the string representation exactly"

requirements-completed: []

coverage:
  - id: D1
    description: "null_check derives a powered per-family threshold from an in-session A0b-vs-A0a null comparison, with model-check inflation and escalation (D-09, D-10)"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_null_check_within_threshold_se_floor_below_base"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_null_check_se_floor_wins_over_base_threshold"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_null_check_model_check_fires_without_escalating"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_null_check_escalates_beyond_double_base"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_null_check_raises_on_nan_pooled_se"
        status: pass
    human_judgment: false
  - id: D2
    description: "load_parity_verdict reads a calibration_parity_verdict.py-shaped JSON verdict file, raising ValueError on a missing family key"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_load_parity_verdict_reads_committed_a2_vs_a0"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_load_parity_verdict_raises_on_missing_family_key"
        status: pass
    human_judgment: false
  - id: D3
    description: "powered_verdict renders validity, per-family beyond-threshold, and the z-based shape guard (D-10) into one real_shift verdict"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_powered_verdict_void_when_null_control_outside_threshold"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_powered_verdict_beyond_threshold_gives_real_shift"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_powered_verdict_z_guard_fires_in_both_families"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_powered_verdict_z_guard_does_not_fire_on_single_family"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_powered_verdict_raises_on_zero_se_shift"
        status: pass
    human_judgment: false
  - id: D4
    description: "refit_decision reduces the set of shipped items' powered verdicts to one refit/no-refit/escalate decision (D-11)"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_refit_decision_shipped_real_shift_gives_refit"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_refit_decision_held_item_real_shift_alone_gives_no_refit"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_refit_decision_void_on_shipped_item_gives_escalate"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_refit_decision_missing_verdict_for_shipped_item_gives_escalate"
        status: pass
    human_judgment: false
  - id: D5
    description: "maia_anchor_identity implements the report-only Maia-anchor reproducibility cross-check (RESEARCH F-7)"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/scripts/test_engine_throughput_226_calibration.py#test_maia_anchor_identity_counts_matched_identical_and_differing"
        status: pass
    human_judgment: false
  - id: D6
    description: "step0-protocol.md pre-registers every step-0 run, the calibration/MQ/candidate-cap/bug-signature rules, and every design-input derivation formula, committed with no step-0 data present"
    requirement: null
    verification:
      - kind: other
        ref: "grep -F check of 8 required constant strings + test ! -e reports/data/engine-throughput-226 (plan's <verify> block)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-28
status: complete
---

# Phase 226 Plan 03: Calibration statistics and step-0 protocol Summary

**Powered per-family calibration thresholds derived from an in-session A0a/A0b null, a z-based shape guard replacing Phase 199's CI-overlap guard, a shipped-items-only refit decision, and the committed step-0 pre-registration document — all before any step-0 data exists.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-09-28
- **Tasks:** 3 completed
- **Files modified:** 3 (all new)

## Accomplishments

- `null_check` turns an A0b-vs-A0a `ParityVerdictResult` into a per-family powered threshold
  (`max(base, 1.96 × pooled se)`), with model-check inflation when the null's own shift exceeds
  the threshold, and escalation when it exceeds twice the base threshold (D-09, D-10).
- `powered_verdict` turns any arm-vs-A0a `ParityVerdictResult` into a `real_shift` verdict:
  void when either family's null control fails, else true iff a family's pooled shift beats its
  powered threshold or the z-based shape guard fires on a cell in both families at once (D-10,
  replacing the Phase 199 CI-overlap guard per RESEARCH Pattern 6).
- `refit_decision` reduces a mapping of shipped items' powered verdicts to one `refit` /
  `no-refit` / `escalate` decision — escalate wins on any void or missing shipped-item verdict,
  refit wins on any shipped-item real shift, a held item never contributes (D-11).
- `maia_anchor_identity` implements the report-only Maia-anchor ledger reproducibility
  cross-check from RESEARCH F-7.
- `reports/engine-throughput-226/step0-protocol.md` commits every step-0 run and parameter (the
  five Phase 199 cells with their pinned anchors, 50 games per cell/anchor, `PRESET_SUPERVISOR_SEED`
  for A0b's seed 2), the calibration/MQ/candidate-cap/bug-signature rules, and every design-input
  derivation formula the Plan 226-05 verdict CLI will compute — committed with
  `reports/data/engine-throughput-226/` absent, verified by the plan's own `<verify>` grep block.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end null check** — `4164133fe` (test) — `load_parity_verdict`, `null_check`,
   7 tests.
2. **Task 2: Powered verdict, z-guard, refit decision, Maia-anchor identity** — `ebd438184`
   (feat) — `powered_verdict`, `refit_decision`, `maia_anchor_identity`, 10 more tests (17 total).
3. **Task 3: Commit the step-0 protocol** — `ff665a9fb` (docs) — `step0-protocol.md`.

## Files Created/Modified

- `scripts/engine_throughput_226_calibration.py` — null_check, powered_verdict, refit_decision,
  maia_anchor_identity, load_parity_verdict; stdlib-only, no frozen constants (those land in
  Plan 226-05's `engine_throughput_226_verdict.py`).
- `tests/scripts/test_engine_throughput_226_calibration.py` — 17 tests covering both plan
  `<behavior>` blocks.
- `reports/engine-throughput-226/step0-protocol.md` — the pre-registered step-0 decision
  contract (D-09..D-17, D-19).

## Decisions Made

- `load_parity_verdict`/`null_check`/`powered_verdict` import `Family`, `ParityVerdictResult`,
  `FamilyResult`, `ExposedCellResult` directly from `calibration_parity_verdict.py` rather than
  redefining them — the same convention `engine_search_fixes_verdict.py` uses for `CellKey`,
  `CellStats`, `Verdict`.
- `refit_decision` treats a shipped item with NO verdict entry in `verdicts` the same as a void
  verdict (escalate), not as a silent pass-through — D-11 explicitly requires a void comparison
  on a shipped item to never yield a silent no-refit, and a missing entry is the same failure
  mode by a different path.
- `maia_anchor_identity` compares the four identity fields as exact strings (the ledger rows are
  `csv.DictReader` output), matching how RESEARCH F-7 established the byte-identical-replay
  evidence from the committed TSVs.

## Deviations from Plan

None — plan executed exactly as written. Both `<behavior>` blocks and the mutation check were
implemented and verified as specified; the executor split the two-task module/test-file build
into two atomic commits (Task 1's `load_parity_verdict`/`null_check` first, Task 2's
`powered_verdict`/`refit_decision`/`maia_anchor_identity` second) to match the plan's per-task
commit granularity, since both tasks touch the same two files.

### Mutation check (Task 2 acceptance criterion)

Temporarily changed `_z_guard_cells`' guard condition from `z_maia > z_guard and z_sf > z_guard`
to `z_maia > z_guard` only (requiring just the Maia family). Confirmed
`test_powered_verdict_z_guard_does_not_fire_on_single_family` (the "z 2.5 in maia but 1.2 in sf"
case) then FAILED:

```
AssertionError: assert [(1500, 0.5)] == []
```

Restored the two-family `and` condition and reconfirmed all 17 tests pass, `ty check` and
`ruff check`/`ruff format --check` clean.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `engine_throughput_226_calibration.py`'s five functions are ready for Plan 226-05's verdict
  CLI (`engine_throughput_226_verdict.py`) to import and wrap with frozen constants.
- `step0-protocol.md` is committed and locked — any later plan that needs to deviate from it
  must write a separate dated override document, never edit this file.
- No blockers for the step-0 measurement runs (orchestrator-inline, per the protocol's §8).

---
*Phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: scripts/engine_throughput_226_calibration.py
- FOUND: tests/scripts/test_engine_throughput_226_calibration.py
- FOUND: reports/engine-throughput-226/step0-protocol.md
- FOUND commit: 4164133fe (Task 1)
- FOUND commit: ebd438184 (Task 2)
- FOUND commit: ff665a9fb (Task 3)
- `uv run pytest tests/scripts/test_engine_throughput_226_calibration.py -x` — 17 passed
- `uv run ty check scripts/engine_throughput_226_calibration.py tests/scripts/test_engine_throughput_226_calibration.py` — All checks passed
- `uv run ruff check` / `uv run ruff format --check` on both files — All checks passed
- step0-protocol.md verify grep block (8 required strings) — all present; `reports/data/engine-throughput-226/` absent
