---
phase: 131-tactic-precision-hardening-cook-alignment
plan: "04"
subsystem: tactic-detector
tags:
  - tactic-detector
  - cook-alignment
  - workstream-b
  - missed-pass
  - false-alarm-gate

dependency_graph:
  requires:
    - phase: 131-01
      provides: "has_forced_mate threading in flaws_service.py; _detect_tactic_for_flaw signature"
  provides:
    - _same_dest_as_best_line helper (dest-square gate)
    - D-03 suppression in missed branch of _detect_tactic_for_flaw
    - test_missed_dest_sq_gate (D-04 suppression fixture)
    - test_missed_no_suppression (D-04 non-suppression fixture)
  affects:
    - app/services/flaws_service.py

tech_stack:
  added: []
  patterns:
    - "Workstream B dest-square gate: _same_dest_as_best_line extracts the to_square comparison with try/except guard, keeping missed-branch nesting shallow"
    - "SimpleNamespace duck-types GamePosition for unit fixtures that don't need a DB session (D-04)"
    - "pv_by_ply injection lets unit tests supply the PV without touching positions[n].pv"

key_files:
  created: []
  modified:
    - app/services/flaws_service.py
    - tests/services/test_tactic_detector.py

key-decisions:
  - "D-03: dest-square equality only — no captured-piece-value check (deferred until a unit fixture surfaces false suppression)"
  - "D-04: Workstream B validated by hand-built (flaw_move, best_line) unit fixtures, not the CC0 puzzle harness (which has no 'player actually played' concept)"
  - "_same_dest_as_best_line extracted as helper to keep missed-branch nesting at depth 2 (function body depth) — inline try/except inside orientation guard would have been depth 4"
  - "ty: ignore[invalid-argument-type] used at SimpleNamespace call sites — duck-typing is intentional for unit test fixtures"

requirements-completed: []

duration: "~15 minutes"
completed: "2026-06-22"
tasks_completed: 2
tasks_total: 2
files_modified: 2
status: complete
---

# Phase 131 Plan 04: Workstream B Missed Dest-Square Gate Summary

**Dest-square gate in `_detect_tactic_for_flaw` suppresses wrong-recapture false alarms on the missed pass via `_same_dest_as_best_line`, validated by two hand-built (flaw_move, best_line) unit fixtures (D-03/D-04)**

## Performance

- **Duration:** ~15 minutes
- **Started:** 2026-06-22T17:00:00Z
- **Completed:** 2026-06-22T17:15:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `_same_dest_as_best_line(board_before, flaw_san, pv) -> bool` helper to `flaws_service.py`: parses the flaw move SAN and the best PV first move (UCI), returns True if their destination squares are equal, with `try/except (ValueError, chess.IllegalMoveError)` fallthrough on parse errors (Security Domain V5 consistency).
- Added the D-03 dest-square gate to the `orientation="missed"` branch of `_detect_tactic_for_flaw`: when the flaw move and the best-line first move share the same target square, returns `(None, None, None, None)` — the player captured the same piece with the wrong piece type (saw it), so the "missed tactic" label would be a false alarm.
- Added `test_missed_dest_sq_gate` (suppression) and `test_missed_no_suppression` (non-suppression) to `tests/services/test_tactic_detector.py` using `SimpleNamespace` mock positions and `pv_by_ply` injection — no DB session required (D-04 hand-built fixture requirement).
- Both tests pass GREEN; full 65-test detector suite green; `ty check app/ tests/` exits 0.

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Write failing (flaw_move, best_line) unit fixtures for missed dest-square gate | c9e099f1 | tests/services/test_tactic_detector.py |
| 2 (GREEN) | Add the dest-square gate to the missed branch of _detect_tactic_for_flaw | 2d93aa3a | app/services/flaws_service.py |

## Files Created/Modified

- `app/services/flaws_service.py` — Added `_same_dest_as_best_line` helper before `_detect_tactic_for_flaw`; added gate call + `flaw_san_missed` fetch inside the `orientation="missed"` branch (after PV fetch, before `detect_tactic_motif`). Bug-fix comment at fix site explains the wrong-recapture false alarm.
- `tests/services/test_tactic_detector.py` — Added `test_missed_dest_sq_gate` and `test_missed_no_suppression` (lines 1808 and 1864) with `ty: ignore[invalid-argument-type]` at SimpleNamespace call sites.

## Gate Design

```
_same_dest_as_best_line(board_before, flaw_san, pv):
  flaw_move = board_before.parse_san(flaw_san)
  best_first_move = chess.Move.from_uci(pv.split()[0])
  return flaw_move.to_square == best_first_move.to_square
  # on ValueError / chess.IllegalMoveError → return False (fall through)
```

In the missed branch (after `if not pv: return`):
```
flaw_san_missed = positions[n].move_san if 0 <= n < len(positions) else None
if flaw_san_missed and _same_dest_as_best_line(board_before, flaw_san_missed, pv):
    return None, None, None, None
```

## Test Fixtures

**Suppression fixture** (`test_missed_dest_sq_gate`):
- Position: `6k1/8/8/3Rr3/8/5N2/8/5K2` — White Rook d5, White Knight f3, Black Rook e5 (unprotected), Kings
- Flaw SAN: `Rxe5` (White Rook captures e5 — right target, wrong piece)
- Best PV: `f3e5` (Knight captures e5)
- Both to_square = e5 → suppress → `(None, None, None, None)`

**Non-suppression fixture** (`test_missed_no_suppression`):
- Position: `6k1/8/8/4r3/8/5N2/8/5K2` — White Knight f3, Black Rook e5 (unprotected), Kings
- Flaw SAN: `Nd4` (Knight goes to d4)
- Best PV: `f3e5` (Knight captures e5)
- Flaw dest d4 ≠ best dest e5 → no suppression → hanging-piece fires `(2, 4, 100, 0)`

## TDD Gate Compliance

1. `test(131-04)` RED commit (c9e099f1) — suppression test fails as expected (gate absent, returns `(2, 4, 100, 0)` not all-None); non-suppression test already green.
2. `feat(131-04)` GREEN commit (2d93aa3a) — both tests pass; no regression.

## Deviations from Plan

None — plan executed exactly as written.

The `_same_dest_as_best_line` helper extraction was called for in the plan ("extract a small helper if the branch grows past soft nesting depth 3"), and indeed adding the `try/except` inside the orientation block would have hit depth 4. Helper extraction was applied as specified.

## Known Stubs

None. The gate is fully wired and validated.

## Threat Flags

No new threat surface. The new parse calls are inside `_same_dest_as_best_line` with `try/except (ValueError, chess.IllegalMoveError)` fallthrough — consistent with the existing malformed-PV guard posture (T-131-06 accepted per threat model). No new endpoints, auth, network, or schema changes.

## Self-Check: PASSED

- c9e099f1 exists in git log: FOUND
- 2d93aa3a exists in git log: FOUND
- `grep -n "to_square" app/services/flaws_service.py` returns 1 match in missed branch: FOUND
- `grep -n "def _same_dest_as_best_line" app/services/flaws_service.py` returns 1 match: FOUND
- `grep -n "def test_missed_dest_sq_gate\|def test_missed_no_suppression" tests/services/test_tactic_detector.py` returns 2 matches: FOUND
- `uv run pytest tests/services/test_tactic_detector.py -x` 65 passed, 5 skipped: PASSED
- `uv run ty check app/ tests/` exits 0: PASSED
- No captured-piece-value check in gate (D-03): CONFIRMED
