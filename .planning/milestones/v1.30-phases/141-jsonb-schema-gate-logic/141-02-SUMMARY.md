---
phase: 141-jsonb-schema-gate-logic
plan: 02
subsystem: services
tags: [pure-math, gate-logic, forcing-line, tactic, eval_utils, game_flaws, pv_lines]

# Dependency graph
requires:
  - phase: 141
    plan: 01
    provides: "allowed_pv_lines and missed_pv_lines JSONB columns on game_flaws (this plan reads blob shape)"
provides:
  - "app/services/forcing_line_gate.py — apply_forcing_line_filter(), is_solver_node_forced(), PvNode TypedDict, three named constants"
  - "tests/services/test_forcing_line_gate.py — 42 pure unit tests, zero DB/engine fixtures (SC #2)"
affects:
  - "Phase 142 (engine pass that fills the blobs calls these gate constants for reference)"
  - "Phase 143 (offline re-tagger CLI calls apply_forcing_line_filter directly)"
  - "Phase 144 (A/B validation adjusts ONLY_MOVE_WIN_PROB_MARGIN, tracked here)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TypedDict for structured blob node (PvNode) — preferred over dict[str, Any] for internal typed blobs"
    - "eval_mate_to_expected_score reused in mate-priority hierarchy (no new sigmoid per D-07)"
    - "Sequence[PvNode] parameter type (covariant) per CLAUDE.md ty rules"

key-files:
  created:
    - "app/services/forcing_line_gate.py"
    - "tests/services/test_forcing_line_gate.py"
  modified: []

key-decisions:
  - "Mate-priority hierarchy (D-01) pulled fully into this module: only-best-is-mate forced; both-mates shorter-distance forced; mate-in-1 never suppressed; fall through to win-prob margin"
  - "ONLY_MOVE_WIN_PROB_MARGIN=0.35, ALREADY_WINNING_CP_THRESHOLD=300, STILL_WINNING_FLOOR_CP=200 as named constants (D-07..D-09)"
  - "PvNode uses b/bm/s/sm/su keys with white-perspective cp convention; gate converts at read time (D-05)"
  - "_resolve_mate_priority calls eval_mate_to_expected_score to check which side benefits from each mate (T-141-04)"
  - "Trailing-only-move stripping treats 'no second legal move' (s=None and sm=None) as the only-move signal; does NOT strip mate nodes that have a cp-scored second-best (corrected in tests)"

requirements-completed: [GATE-01, GATE-02]

coverage:
  - id: D1
    description: "apply_forcing_line_filter() credits motif only when firing node AND every solver node pass only-move margin (GATE-01)"
    requirement: "GATE-01"
    verification:
      - kind: unit
        ref: "tests/services/test_forcing_line_gate.py::TestOnlyMoveMargin::test_all_solver_nodes_required_for_apply_filter"
        status: pass
      - kind: unit
        ref: "tests/services/test_forcing_line_gate.py::TestOnlyMoveMargin::test_all_solver_nodes_pass_apply_filter"
        status: pass
    human_judgment: false
  - id: D2
    description: "Mate-priority hierarchy (D-01): only-best-is-mate forced; both-mates shorter-distance; mate-in-1 never suppressed; fall-through"
    verification:
      - kind: unit
        ref: "tests/services/test_forcing_line_gate.py::TestMatePriority (14 tests, both colors)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Already-winning reject >300cp (D-08, GATE-02)"
    requirement: "GATE-02"
    verification:
      - kind: unit
        ref: "tests/services/test_forcing_line_gate.py::TestAlreadyWinning (6 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Still-winning floor <200cp stops line extension (D-09, GATE-02)"
    requirement: "GATE-02"
    verification:
      - kind: unit
        ref: "tests/services/test_forcing_line_gate.py::TestStillWinningFloor (4 tests)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Trailing-only-move strip and one-mover discard (D-10, GATE-02); defender re-convergence does not kill the line"
    requirement: "GATE-02"
    verification:
      - kind: unit
        ref: "tests/services/test_forcing_line_gate.py::TestLineStripping (7 tests)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Zero DB/engine fixtures: module imports and tests run with no database or Stockfish process"
    verification:
      - kind: unit
        ref: "grep -nE 'db_session|pytest_asyncio|AsyncSession|engine' tests/services/test_forcing_line_gate.py -- returns nothing"
        status: pass
      - kind: unit
        ref: "uv run pytest tests/services/test_forcing_line_gate.py -x -- 42 passed"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-06-29
status: complete
---

# Phase 141 Plan 02: Forcing-Line Gate Logic Summary

**Pure-math forcing-line gate module with 42 zero-fixture unit tests: apply_forcing_line_filter() implements the only-move margin (GATE-01), mate-priority hierarchy (D-01), already-winning reject, still-winning floor, trailing-only-move strip, and one-mover discard (GATE-02)**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-06-29
- **Tasks:** 2
- **Files created:** 2

## Accomplishments

- Implemented `app/services/forcing_line_gate.py`: a zero-I/O, zero-DB pure-math module with the full forcing-line gate logic. Imports `LICHESS_K`, `eval_cp_to_expected_score`, and `eval_mate_to_expected_score` from `eval_utils`; defines no new sigmoid.
- `PvNode` TypedDict with keys `b/bm/s/sm/su` (D-05 blob shape, white-perspective cp).
- Three named constants with decision-ID comments: `ONLY_MOVE_WIN_PROB_MARGIN=0.35` (D-07), `ALREADY_WINNING_CP_THRESHOLD=300` (D-08), `STILL_WINNING_FLOOR_CP=200` (D-09).
- `apply_forcing_line_filter()` orchestrator delegates each rule to its own predicate helper (CLAUDE.md function-size discipline, nesting hard-cap 4). Helper chain: `_is_already_winning` -> `_truncate_at_still_winning_floor` -> `_strip_trailing_only_moves` -> solver-node `all(is_solver_node_forced(...))`.
- `is_solver_node_forced()` applies the mate-priority hierarchy (D-01) via `eval_mate_to_expected_score` before falling through to the win-prob delta margin.
- `_resolve_mate_priority()` calls `eval_mate_to_expected_score(bm, solver_color)` to verify which side benefits from the mate (guards T-141-04 asymmetric-sign bug class), then compares `abs(bm)` vs `abs(sm)` for the both-mates case.
- Added 42 pure unit tests in `tests/services/test_forcing_line_gate.py` with no database or Stockfish fixtures (SC #2 guarantee confirmed by grep). Classes: `TestConstants`, `TestOnlyMoveMargin`, `TestMatePriority`, `TestAlreadyWinning`, `TestStillWinningFloor`, `TestLineStripping`.
- `ty check` and `ruff check` both clean.

## Task Commits

1. **Task 1: Implement the pure forcing_line_gate module** - `7f3b7722` (feat)
2. **Task 2: Unit-test the gate with no engine and no DB fixtures** - `f0d3f731` (test)

## Files Created

- `app/services/forcing_line_gate.py` — gate module: `PvNode`, three constants, `apply_forcing_line_filter()`, `is_solver_node_forced()`, four private helpers (`_is_already_winning`, `_resolve_mate_priority`, `_truncate_at_still_winning_floor`, `_strip_trailing_only_moves`)
- `tests/services/test_forcing_line_gate.py` — 42 pure unit tests across 6 test classes

## Decisions Made

- `_resolve_mate_priority` uses `eval_mate_to_expected_score` (not raw sign arithmetic) to determine which side a mate benefits, so the perspective conversion is identical to the rest of eval_utils (T-141-04 guard)
- Mate nodes with a cp-scored second-best (`s` is not None, `sm` is None) are NOT treated as trailing only-moves; only nodes with BOTH `s=None AND sm=None` are stripped. This distinction matters: a mate-in-3 where the second-best is a losing cp move (common in practice) should NOT be stripped.
- `_strip_trailing_only_moves` takes no `solver_color` argument -- the only-move signal (`s is None and sm is None`) is perspective-independent (it's about move count, not eval sign).
- `LICHESS_K` imported with `# noqa: F401` to document the eval_utils dependency without defining a new sigmoid (D-07 requirement); ty and ruff both accept this.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test data used white-winning cp values for black solver tests**

- **Found during:** Task 2 first run
- **Issue:** `_valid_two_move_line()` helper had `b=800` (white winning) but was used in `test_pre_flaw_at_threshold_black_solver_not_rejected` with `solver_color="black"`. The still-winning floor check computes `solver_cp = -800 < 200` and truncates the line immediately, returning False instead of True.
- **Fix:** Split into `_valid_two_move_line_white()` (positive cp) and `_valid_two_move_line_black()` (negative cp = black winning). Updated both test methods accordingly.
- **Files modified:** `tests/services/test_forcing_line_gate.py`
- **Commit:** `f0d3f731`

**2. [Rule 1 - Bug] Test for mate-node floor bypass used only-move mate nodes (stripped, not bypassed)**

- **Found during:** Task 2 first run
- **Issue:** `_mate_node(bm=3)` creates `PvNode(b=None, bm=3, s=None, sm=None, su="")` with no second move. These nodes pass the floor check correctly (mate bypasses the cp floor), but then get stripped by `_strip_trailing_only_moves` since `s=None and sm=None`. The test expected True but got False.
- **Fix:** Used realistic blob data where mate nodes also have a cp-scored second-best (`s=200`, `sm=None`), reflecting that MultiPV=2 returns the second-legal-move's cp even when the best is a forced mate. `_resolve_mate_priority` returns True (only-best-is-mate), so `is_solver_node_forced` passes without stripping.
- **Files modified:** `tests/services/test_forcing_line_gate.py`
- **Commit:** `f0d3f731`

## Known Stubs

None — this is a pure-math module. No data sources wired, no placeholders. The module's constants are provisional starting values (tuned in Phase 144), which is by design and documented in the constant comments.

## Threat Flags

None — this module has no new API endpoint, no network I/O, no database access, no user input surface, and no third-party packages. T-141-04 (perspective-sign asymmetry) and T-141-05 (no disclosure surface) are addressed as designed.

---

## Self-Check

**Files created:**
- `app/services/forcing_line_gate.py` — FOUND
- `tests/services/test_forcing_line_gate.py` — FOUND

**Commits:**
- `7f3b7722` (feat: forcing_line_gate module) — FOUND
- `f0d3f731` (test: unit tests for forcing_line_gate) — FOUND

**Test run:** `uv run pytest tests/services/test_forcing_line_gate.py -x` — 42 passed

**Grep gate:** `grep -nE 'db_session|pytest_asyncio|AsyncSession|engine'` — CLEAN

**ty check:** All checks passed

**ruff check:** All checks passed

## Self-Check: PASSED
