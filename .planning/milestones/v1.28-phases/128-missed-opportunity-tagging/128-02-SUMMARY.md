---
phase: 128-missed-opportunity-tagging
plan: "02"
subsystem: flaws_service tactic detection
tags: [tactic, detection, orientation, missed, allowed, flaws_service]
status: complete

dependency_graph:
  requires:
    - 128-01 (FlawRecord 8-tuple keys + game_flaws 8 inline columns)
  provides:
    - orientation-parametrized _detect_tactic_for_flaw(orientation: Literal["allowed","missed"])
    - missed_* 4-tuple populated by second detector pass in _build_flaw_record
    - FlawRecord neither/one/both matrix unit-tested
  affects:
    - app/services/flaws_service.py (_detect_tactic_for_flaw, _build_flaw_record)
    - tests/services/test_flaws_service.py (3 new test classes)

tech_stack:
  added: []
  patterns:
    - Orientation-parametrized dispatcher: single detect_tactic_motif entry point called
      twice per flaw with different board/PV/pov for allowed vs missed pass (D-03/D-06)
    - Literal["allowed","missed"] orientation param per CLAUDE.md typing convention
    - TDD RED/GREEN: 3 failing tests -> implementation -> 3 passing tests per task

key_files:
  created: []
  modified:
    - app/services/flaws_service.py
    - tests/services/test_flaws_service.py

decisions:
  - D-03: detect_tactic_motif is orientation-agnostic; missed pass calls it with
    board_before (pov=mover) + flaw_ply PV; no new harness or detector function
  - D-04: 127 relevance gate and confidence floor reused unchanged for both orientations
  - D-06: _detect_tactic_for_flaw parametrized by Literal["allowed","missed"];
    _build_flaw_record calls it twice (once per orientation)

metrics:
  duration: "~10 minutes"
  completed: "2026-06-19"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 2
---

# Phase 128 Plan 02: Missed-Opportunity Detector Pass Summary

Implemented the second detector pass in `flaws_service.py`: `_detect_tactic_for_flaw` is now orientation-parametrized (`Literal["allowed","missed"]`), and `_build_flaw_record` calls it twice to fill both the `allowed_*` and `missed_*` 4-tuples on every `FlawRecord`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for orientation param | 80e7feed | tests/services/test_flaws_service.py |
| 1 (GREEN) | Parametrize _detect_tactic_for_flaw by orientation | ea075c5d | app/services/flaws_service.py |
| 2 (RED) | Failing tests for both-orientation matrix | 5a43d756 | tests/services/test_flaws_service.py |
| 2 (GREEN) | Wire both passes in _build_flaw_record | e7851048 | app/services/flaws_service.py |

## Key Implementation

### _detect_tactic_for_flaw Refactor

Added `orientation: Literal["allowed", "missed"] = "allowed"` parameter with explicit return type `tuple[int | None, int | None, int | None, int | None]`.

**orientation="allowed" (default):** Unchanged behavior — selects `pv_by_ply.get(n+1)` or `positions[n+1].pv`, pushes the flaw move onto `board_before` to get `board_after_flaw`, calls `detect_tactic_motif(board_after_flaw, pv)` with `pov = refuting side`.

**orientation="missed":** Selects `pv_by_ply.get(n)` or `positions[n].pv` (the SEED-054 "instead-of" line), calls `detect_tactic_motif(board_before, pv)` WITHOUT pushing the flaw move. `pov = board_before.turn = the mover`. No new relevance gate or harness — the same dispatcher reused for both orientations (D-04).

### _build_flaw_record

Replaced single detection call + hardcoded `missed_*=None` stubs with two calls:
```python
allowed_motif_int, allowed_piece, allowed_confidence, allowed_depth = _detect_tactic_for_flaw(
    n, fen_map, positions, pv_by_ply, orientation="allowed"
)
missed_motif_int, missed_piece, missed_confidence, missed_depth = _detect_tactic_for_flaw(
    n, fen_map, positions, pv_by_ply, orientation="missed"
)
```

Both 4-tuples now flow to `FlawRecord`. `missed_*` stays `None` when `flaw_ply` PV is absent (honest NULL, same posture as 127 depth, D-13).

### Test Coverage Added

**TestDetectTacticForFlawOrientation** (Task 1 — direct `_detect_tactic_for_flaw` unit tests):
- `test_allowed_orientation_unchanged`: orientation="allowed" is byte-identical to today, fires HANGING_PIECE on white's ply-4 flaw
- `test_missed_orientation_fires_hanging_piece`: orientation="missed" fires HANGING_PIECE — black at ply 5 could capture white's undefended Bc4 with dxc4 (FEN after 3.f3, `d5c4` PV)
- `test_missed_orientation_returns_none_when_flaw_ply_pv_absent`: missing flaw_ply PV → all-None without raising

**TestBuildFlawRecordBothOrientations** (Task 2 — integration via `classify_game_flaws`):
- `test_both_pvs_present_fills_both_orientations`: both 4-tuples non-None when both PVs supplied
- `test_allowed_pv_only_sets_allowed_clears_missed`: allowed_* set, missed_* all None
- `test_missed_pv_only_sets_missed_clears_allowed`: missed_* set, allowed_* all None
- `test_neither_pv_leaves_both_orientations_none`: both 4-tuples all None

Test fixture: PGN `"1. e4 e5 2. Bc4 d5 3. f3 Bg4 *"` (6 half-moves). After 3.f3 (ply 5, black to move), white's Bc4 is undefended — black's missed PV `d5c4` fires HANGING_PIECE; white's allowed PV `f3g4` fires HANGING_PIECE.

## Threat Mitigation Verification

**T-128-03 (DoS — malformed PV):** Covered. The missed pass calls `detect_tactic_motif` which already guards malformed/empty PV with `if not pv_str: return None, None, None, None` + `try/except ValueError`. Additionally, the early-return guard `if not pv: return None, None, None, None` in the missed branch prevents reaching the detector with an empty string.

**T-128-04 (false tag):** Accepted. Precision is the detector's property (unchanged, D-04). NULL on absent PV is honest — never fabricated.

## Acceptance Criteria Check

- `_detect_tactic_for_flaw` has `orientation: Literal["allowed", "missed"]` param and explicit return type: YES
- `orientation="allowed"` is byte-identical to today (existing tactic tests pass): YES (5 original tactic tests still pass)
- `orientation="missed"` fires HANGING_PIECE on board_before + flaw_ply PV: YES (test_missed_orientation_fires_hanging_piece)
- Missed pass returns (None,None,None,None) when flaw_ply PV absent: YES (test_missed_orientation_returns_none_when_flaw_ply_pv_absent)
- No new relevance gate/confidence floor/harness: YES (`grep -c "detect_tactic_motif" app/services/flaws_service.py` = 4, no new function)
- `_build_flaw_record` calls `_detect_tactic_for_flaw` twice: YES (`grep -c "_detect_tactic_for_flaw"` = 3 = def + 2 calls)
- `uv run ty check app/ tests/`: PASSED
- `uv run ruff check app/ tests/`: PASSED
- `uv run pytest tests/services/test_flaws_service.py -x`: 129 passed
- `uv run pytest -n auto -x`: 2809 passed, 15 skipped

## Deviations from Plan

None. Plan executed exactly as written. The TDD cycle (RED → GREEN) was followed for both tasks, using the `_detect_tactic_for_flaw` direct call path for Task 1 and `classify_game_flaws` integration path for Task 2.

## Known Stubs

None. All `missed_tactic_*` fields in `_build_flaw_record` are now wired to the second detector pass. The fields return `None` when the `flaw_ply` PV is absent, which is honest absence (not a stub).

## Threat Flags

None. No new network endpoints, auth paths, or file access patterns introduced. The missed-pass PV input flows through the same trust boundary as the existing allowed pass (stored UCI string from `game_positions.pv` → `detect_tactic_motif` dispatcher, guarded at T-128-03).

## Self-Check: PASSED

- `app/services/flaws_service.py` exists: FOUND
- `tests/services/test_flaws_service.py` exists: FOUND
- Commits exist: 80e7feed, ea075c5d, 5a43d756, e7851048 — all verified in git log
- `ty check app/ tests/`: All checks passed
- `ruff check app/ tests/`: All checks passed
- `pytest -n auto`: 2809 passed, 15 skipped
