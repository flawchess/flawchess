---
phase: 131-tactic-precision-hardening-cook-alignment
plan: "02"
subsystem: tactic-detector
tags:
  - tactic-detector
  - cook-alignment
  - precision-harness
  - fork
  - skewer
  - pin
  - discovered-attack
dependency_graph:
  requires:
    - _is_defended (ray-aware) from plan 01
    - _is_in_bad_spot from plan 01
    - _VALUES_NO_KING from plan 01
    - depth-primary dispatch from plan 01
  provides:
    - detect_skewer rebuilt to cook relational predicate (1.000/1.000 train/test)
    - detect_discovered_attack rebuilt to cook relational predicate (0.995/1.000)
    - detect_fork rebuilt to cook predicate (1.000/0.998)
    - detect_pin rebuilt to cook two-sub-test port (0.752/0.819 — suppressed)
    - precision floors raised for fork/skewer/discovered-attack to 0.93
    - pin added to SUPPRESSED_MOTIFS (CI gate dropped)
  affects:
    - app/services/tactic_detector.py
    - tests/services/test_tactic_detector.py
    - tests/scripts/tagger/precision_floors.py
    - app/repositories/library_repository.py
    - reports/tactic-tagger/tactic-tagger-2026-06-22.md
tech_stack:
  added: []
  patterns:
    - cook relational skewer (op.from_square in between + is_in_bad_spot accept)
    - cook relational discovered-attack (prev.from_square in between + recapture short-circuit)
    - cook fork (is_in_bad_spot prune + skip pawns + not-attacker clause + [:-1] scan)
    - cook pin two-sub-tests (pin_prevents_attack + pin_prevents_escape via board.pin)
    - chess.SquareSet.between for between-square geometry in skewer and DA
    - board.pin(pinned_color, sq) returning BB_ALL for not-pinned (Pitfall 7)
key_files:
  created: []
  modified:
    - app/services/tactic_detector.py
    - tests/services/test_tactic_detector.py
    - tests/scripts/tagger/precision_floors.py
    - app/repositories/library_repository.py
decisions:
  - "Fork: cook scan excludes last pov move (range(0,len-2,2) = cook [:-1]); precision 0.451 -> 0.998 TEST"
  - "Skewer: op.from_square in between + is_in_bad_spot accept; precision 0.210 -> 1.000 TEST"
  - "DA: prev.from_square in between + recapture short-circuit; precision 0.217 -> 1.000 TEST"
  - "Pin: two-sub-test port (pin_prevents_attack + pin_prevents_escape); precision 0.474 -> 0.819 TEST"
  - "Pin suppressed (CI gate): below 0.90 TEST bar (D-02/D-11); stays in FAMILY_TO_MOTIF_INTS to preserve G-01 10-family contract"
  - "Floors raised: fork 0.35->0.93, skewer 0.10->0.93, discovered-attack 0.15->0.93"
metrics:
  duration: "~80 minutes"
  completed: "2026-06-22"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 4
status: complete
---

# Phase 131 Plan 02: Cook Predicate Alignment for Fork, Skewer, Pin, Discovered-Attack Summary

Rebuilt four geometric tactic detectors to cook's exact relational predicates, eliminating the large false-positive pools that kept volume-weighted precision at ~0.31. Skewer, fork, and discovered-attack now each exceed 0.990 TEST precision. Pin reached 0.819 TEST at full cook fidelity — the best achievable with the current cook model — and is suppressed from the CI floor gate per D-02/D-11.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Rebuild detect_skewer and detect_discovered_attack | 29cc8929 | tactic_detector.py, test_tactic_detector.py, tactic-tagger-2026-06-22.md |
| 2 | Rebuild detect_fork and detect_pin | 1d7d6b19 | tactic_detector.py, test_tactic_detector.py, tactic-tagger-2026-06-22.md |
| 3 | Ship/suppress decisions; update precision floors | 8f55488f | precision_floors.py, library_repository.py, tactic-tagger-2026-06-22.md |
| 3 fix | Restore pin to FAMILY_TO_MOTIF_INTS (G-01 contract) | df2b3be1 | library_repository.py, precision_floors.py |

## Precision Lift Summary (TEST set, 5164 rows held out)

| Motif | P(test) before | P(test) after | Decision |
|-------|---------------|---------------|----------|
| skewer | 0.210 | 1.000 | SHIPPED — floor raised 0.10 -> 0.93 |
| discovered-attack | 0.217 | 1.000 | SHIPPED — floor raised 0.15 -> 0.93 |
| fork | 0.451 | 0.998 | SHIPPED — floor raised 0.35 -> 0.93 |
| pin | 0.474 | 0.819 | SUPPRESSED — below 0.90 bar, CI gate dropped |
| discovered-check | 0.902 | 0.884 | Not regressed (above 0.85 guard, D-03) |

## Cook Predicates Implemented (D-10, no source copy)

### detect_skewer (Task 1)

Scan pov moves from 2nd+ (`range(2, len(moves), 2)` — cook's `mainline[1::2][1:]`). For a pov capture with a ray piece (Q/R/B) that is not checkmate:
- `between = chess.SquareSet.between(move.from_square, capture_sq)`
- Require `op.to_square != capture_sq` (not a recapture)
- Require `op.from_square in between` (opponent moved ACROSS the skewer line)
- Require `_PIECE_VALUES[op_moved_piece] > _PIECE_VALUES[captured]` (higher-value piece was in front)
- Require `_is_in_bad_spot(board_before, capture_sq)` (the piece we capture is loose)

### detect_discovered_attack (Task 1)

Scan pov moves from 2nd+ (k in `range(2, len(moves), 2)`):
- Require a capture (`board_before.piece_at(capture_sq)` not None and opponent color)
- `op.to_square == capture_sq` → short-circuit to False (recapture)
- `prev = moves[k-2]`; require `prev.from_square in between` (earlier pov move vacated a between-square)
- Require `capture_sq != prev.to_square` (not capturing the just-unblocked square)
- Require `move.from_square != prev.to_square` (capturer didn't just come from prev's destination)
- Require `prev` not castling

Loop starts at k=2 (Pitfall 1: discovered-check at index 0 is not re-claimed).

### detect_fork (Task 2)

Scan pov moves EXCEPT the last (`range(0, len(moves) - 2, 2)` — cook's `[:-1]`):
- Skip king forkers
- `_is_in_bad_spot(board_after, dest)` prune (forker lands in bad spot → skip)
- Count victims among `board_after.attacks(dest)`, skipping pawns
- Victim qualifies if `_PIECE_VALUES[victim] > _PIECE_VALUES[forker]` (king=99 so forking checks count) OR (`not _is_defended` AND `victim_sq not in board_after.attackers(not pov, dest)` — hanging victim not itself defending the fork square)
- Fire if victims >= 2

### detect_pin (Task 2)

Two-sub-test cook port; scan all board positions:
- `board.pin(piece.color, sq)` with the PINNED piece's color (Pitfall 7); `BB_ALL` = not pinned
- Find pov pinner (ray piece on the pin ray)
- **pin_prevents_attack**: pinned piece attacks a pov piece on a square OUTSIDE the pin ray, where the pov piece is worth more than the pinned piece OR is hanging
- **pin_prevents_escape**: pov attacker INSIDE the pin ray attacks the pinned piece; fire if pinned > attacker value, OR pinned is hanging AND cannot legally step off the pin ray

Depth = `max(0, k-1)` per SEED-057 IN-01 (board index to move index).

## Ship/Suppress Decisions (D-11 Audit Trail)

| Motif | P(train) | P(test) | Decision | Rationale |
|-------|----------|---------|----------|-----------|
| fork | 1.000 | 0.998 | SHIPPED | Exceeds 0.90 TEST bar; floor 0.35 → 0.93 |
| skewer | 1.000 | 1.000 | SHIPPED | Exceeds 0.90 TEST bar; floor 0.10 → 0.93 |
| discovered-attack | 0.995 | 1.000 | SHIPPED | Exceeds 0.90 TEST bar; floor 0.15 → 0.93 |
| pin | 0.752 | 0.819 | SUPPRESSED | Below 0.90 bar at full cook fidelity (D-02/D-11); CI gate dropped (added to SUPPRESSED_MOTIFS). UI: kept in FAMILY_TO_MOTIF_INTS to preserve G-01 10-family contract |

### Pin suppression notes

Pin at 0.819 TEST is a 72% improvement from the 0.474 baseline. Full cook fidelity was achieved but the precision ceiling is below 0.90. The CI floor gate is removed (pin added to `SUPPRESSED_MOTIFS`). Pin chips still surface in the UI at 0.819 precision because:
1. `_TACTIC_CHIP_CONFIDENCE_MIN=70` cannot suppress confidence=100 Tier-2 motifs
2. Removing "pin" from `FAMILY_TO_MOTIF_INTS` would break the G-01 10-family contract asserted in `test_family_mapping_ten_families` — out of scope for this plan

A future phase can drive pin precision above 0.90 and restore the floor.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Type error in detect_discovered_attack**
- **Found during:** Task 1 ty check
- **Issue:** Double call to `board_before.piece_at(capture_sq)` — first call used in `is None` check, second call not narrowed by ty
- **Fix:** Extracted to local variable `captured_piece`
- **Files modified:** app/services/tactic_detector.py
- **Commit:** 29cc8929

**2. [Rule 1 - Bug] Multiple fixture reclassifications (Tasks 1-2)**
- **Found during:** Task 1, Task 2 verification
- **Issue:** New strict cook predicates changed dispatch for ~20 prod fixtures (fork/skewer/DA/deflection); old fixtures validated against old broad predicates
- **Fix:** Replaced all `_SKEWER_FIXTURES` (12) and `_DISCOVERED_ATTACK_FIXTURES` (12) with new CC0 TPs from the precision harness. Replaced `_FORK_FIXTURES` (12 TPs) and `_PIN_FIXTURES` (12 TPs). Updated 5 cross-motif fixture labels in `_FORK_FIXTURES`, `_DEFLECTION_FIXTURES`, `_SKEWER_FIXTURES`
- **Files modified:** tests/services/test_tactic_detector.py
- **Commits:** 29cc8929, 1d7d6b19

**3. [Rule 3 - Blocking] G-01 contract broken by pin removal from FAMILY_TO_MOTIF_INTS**
- **Found during:** Task 3 full test suite run
- **Issue:** `test_family_mapping_ten_families` asserts exactly 10 family keys; removing "pin" left 9, causing failure
- **Fix:** Restored "pin" to `FAMILY_TO_MOTIF_INTS` with an explanatory comment; documented suppression mechanism in module docstring (CI gate only, not UI)
- **Files modified:** app/repositories/library_repository.py, tests/scripts/tagger/precision_floors.py
- **Commit:** df2b3be1

## Threat Flags

None. This plan makes no network, DB schema, or auth changes; detectors read stored PV data only.

## Self-Check: PASSED

- 29cc8929 exists in git log: FOUND
- 1d7d6b19 exists in git log: FOUND
- 8f55488f exists in git log: FOUND
- df2b3be1 exists in git log: FOUND
- `uv run pytest -n auto -x` 2854 passed, 16 skipped: PASSED
- `uv run ty check app/ tests/` exits 0: PASSED
- `uv run pytest tests/scripts/tagger/test_detector_precision.py` passes: PASSED
- `uv run pytest tests/services/test_tactic_detector.py` 63 passed, 5 skipped: PASSED
- `grep -n "op.from_square in between\|prev.from_square in between" app/services/tactic_detector.py` returns matches: FOUND
- `grep -n "pin_prevents_attack\|pin_prevents_escape" app/services/tactic_detector.py` returns 4 matches: FOUND
- `grep -n "\"fork\": 0.93\|\"skewer\": 0.93\|\"discovered-attack\": 0.93" tests/scripts/tagger/precision_floors.py` returns 3 matches: FOUND
- `grep -n '"pin"' tests/scripts/tagger/precision_floors.py` — pin in SUPPRESSED_MOTIFS: FOUND
