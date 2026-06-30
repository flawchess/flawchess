---
phase: 143-offline-re-tagger
plan: "01"
subsystem: backend
tags: [gate, testing, margin, tdd, forcing-line]
dependency_graph:
  requires: [141-forcing-line-gate, 142-multipv-engine-pass]
  provides: [margin-param-on-gate, sc3-defender-coverage, d03-margin-tests]
  affects: [app/services/forcing_line_gate.py, tests/services/test_forcing_line_gate.py]
tech_stack:
  added: []
  patterns: [tdd-audit-and-fill, default-param-threading, worker-pool-safe-margin]
key_files:
  modified:
    - app/services/forcing_line_gate.py
    - tests/services/test_forcing_line_gate.py
decisions:
  - "D-03 implemented: margin parameter threaded via function args only — no global mutation"
  - "D-05 confirmed: SC2 fully covered by 11 TestMatePriority tests; zero new mate tests added"
  - "SC3 gap filled: 5-node branch-then-reconverge defender test added (TestDefenderBranching)"
  - "TDD gate: test commit (b2286c2c) follows feat commit (acc41898)"
metrics:
  duration: "~15min"
  completed: "2026-06-30"
  tasks: 2
  files: 2
status: complete
---

# Phase 143 Plan 01: Gate Margin Parameterization + Test Coverage Summary

Add `margin: float = ONLY_MOVE_WIN_PROB_MARGIN` to both public gate functions and fill the SC3 multi-ply defender gap + D-03 margin-param tests.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add margin param to is_solver_node_forced and apply_forcing_line_filter | acc41898 | app/services/forcing_line_gate.py |
| 2 | Audit SC2 (no gaps) + fill SC3 gap + add D-03 margin-param tests | b2286c2c | tests/services/test_forcing_line_gate.py |

## What Was Built

### Task 1 — Margin parameter on gate functions (D-03)

`is_solver_node_forced` and `apply_forcing_line_filter` now both accept `margin: float = ONLY_MOVE_WIN_PROB_MARGIN` as their last parameter. The single win-prob comparison in `is_solver_node_forced` (previously `> ONLY_MOVE_WIN_PROB_MARGIN`) now reads `> margin`. `apply_forcing_line_filter` forwards `margin` to every `is_solver_node_forced` call.

The module-level constant `ONLY_MOVE_WIN_PROB_MARGIN = 0.35` is unchanged and serves as the default. No global mutation — spawn workers re-import the module with the original constant; overrides flow via function arguments only (worker-pool-safe per D-03).

Private functions `_resolve_mate_priority`, `_truncate_at_still_winning_floor`, `_strip_trailing_only_moves`, and `_is_already_winning` are untouched (they do not use the margin).

### Task 2 — Audit and fill unit coverage (D-05)

**SC2 audit (GATE-03 — mate-priority):** All 5 SC2 clauses were already covered by 11 tests in `TestMatePriority` (both colors). Audit verdict: FULLY SATISFIED. Zero new mate tests added per D-05.

**SC3 fill (GATE-04 — defender branch-then-reconverge):** Added `TestDefenderBranching.test_multi_ply_defender_ambiguity_does_not_kill_line`. The 5-node line `[S0_forced, D0_ambiguous, S1_forced, D1_ambiguous, S2_forced]` passes `apply_forcing_line_filter`. The existing Phase 141 defender tests covered only a single ambiguous node; this proves the gate is correct across multiple ambiguous defender nodes.

**D-03 margin-param tests:** Added `TestMarginParam` with two tests:
- `test_margin_param_is_respected_by_is_solver_node_forced`: node with delta ~0.122 (p(400,"white") - p(200,"white")) is forced at `margin=0.1` and not forced at `margin=0.5`.
- `test_apply_filter_margin_param_is_respected`: same delta applied across a 3-node line passes at `margin=0.1` and fails at `margin=0.5`.

## Verification Results

```
uv run ty check app/services/forcing_line_gate.py  → All checks passed!
uv run pytest tests/services/test_forcing_line_gate.py -v  → 45 passed (0 failures)
grep for ONLY_MOVE_WIN_PROB_MARGIN assignments  → No assignments outside line 52 (constant definition only)
```

## Deviations from Plan

None — plan executed exactly as written.

**SC2 audit verdict:** Confirmed all 5 SC2 clauses covered (see RESEARCH.md §5 for the original audit). No logic gap found in forcing_line_gate.py for GATE-03.

## GATE-03 / SC2 Audit Outcome (D-05 requirement)

| SC2 clause | Covered by | Verdict |
|-----------|-----------|---------|
| only-best-is-mate → forced | test_only_best_is_mate_white/black_solver | COVERED |
| both-mates → shorter forced | test_both_mates_shorter_wins_white/black_solver | COVERED |
| both-mates → longer NOT forced | test_both_mates_longer_not_forced_white/black_solver | COVERED |
| mate-in-1 never suppressed | test_mate_in_1_never_suppressed_white/black + vs_second_cp | COVERED (4 tests) |
| else fall through to sigmoid | test_no_mate_falls_through_to_cp_margin | COVERED |

**No new GATE-03 tests required.** The 11 existing `TestMatePriority` tests fully satisfy SC2.

## Known Stubs

None — this plan modifies pure-math gate logic and unit tests only, no UI or data rendering.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes. The `margin` parameter flows via function arguments only — no module globals mutated (T-143-01 mitigated as designed).

## Self-Check: PASSED

- FOUND: 143-01-SUMMARY.md
- FOUND: commit acc41898 (Task 1 — feat)
- FOUND: commit b2286c2c (Task 2 — test)
- FOUND: app/services/forcing_line_gate.py (modified)
- FOUND: tests/services/test_forcing_line_gate.py (modified)
