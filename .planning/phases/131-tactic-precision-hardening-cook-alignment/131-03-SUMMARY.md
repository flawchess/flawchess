---
phase: 131-tactic-precision-hardening-cook-alignment
plan: "03"
subsystem: tactic-detector
tags:
  - tactic-detector
  - cook-alignment
  - precision-harness
  - back-rank-mate
  - anastasia-mate
  - hook-mate
  - named-mates
dependency_graph:
  requires:
    - has_forced_mate gate from plan 01
    - depth-primary dispatch from plan 01
    - precision harness floors from plan 02
  provides:
    - detect_back_rank_mate hardened with cook's own-blocker test (1.000/1.000 train/test)
    - detect_anastasia_mate hardened with king+1 blocker + king+3 knight geometry (1.000/1.000)
    - detect_hook_mate hardened with knight-adjacent-to-king constraint (1.000/1.000)
    - D-09 never-regress floors locked: discovered-check ≥0.85, double-check 0.93,
      smothered-mate 0.93, back-rank/anastasia/hook each 0.93
  affects:
    - app/services/tactic_detector.py
    - tests/services/test_tactic_detector.py
    - tests/scripts/tagger/precision_floors.py
    - reports/tactic-tagger/tactic-tagger-2026-06-22.md
tech_stack:
  added: []
  patterns:
    - cook back-rank-mate own-blocker test (3 forward squares must all be defender's own pieces)
    - back-rank-checker requirement (at least one pov checker on the back rank)
    - relative-rank arithmetic for forward squares (Pitfall 3: pov=WHITE offset=-8, pov=BLACK offset=+8)
    - anastasia-mate file-normalized geometry (a-file king+1/+3, h-file king-1/-3)
    - anastasia-mate file-on-king gate (mating piece must land on king's file)
    - hook-mate knight-adjacent-to-king constraint (Chebyshev distance ≤1)
    - chess.square_distance for Chebyshev distance in cook chain validation
key_files:
  created: []
  modified:
    - app/services/tactic_detector.py
    - tests/services/test_tactic_detector.py
    - tests/scripts/tagger/precision_floors.py
    - reports/tactic-tagger/tactic-tagger-2026-06-22.md
decisions:
  - "back-rank-mate: own-blocker test uses per-pov forward_offset (-8 for pov=WHITE, +8 for pov=BLACK)"
  - "back-rank-mate: back-rank-checker test requires checker ON back rank (chess.square_rank(checker_sq) == back_rank)"
  - "anastasia-mate: file-normalized geometry uses center_sign (1 for a-file, -1 for h-file) instead of board.apply_transform"
  - "hook-mate: knight-adjacent-to-king check (chess.square_distance <= 1) eliminates arabian-mate FPs"
  - "D-09 floors: discovered-check raised 0.80 -> 0.85 (D-09 lock); double-check 0.80 -> 0.93; smothered-mate 0.90 -> 0.93"
  - "D-09 floors: back-rank/anastasia/hook each raised to 0.93 (7pp below 1.000 TRAIN)"
  - "hanging-piece floor confirmed at 0.90 (train 0.909; depth-primary dispatch reduced from 0.990 baseline)"
metrics:
  duration: "~22 minutes"
  completed: "2026-06-22"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 4
status: complete
---

# Phase 131 Plan 03: Named-Mate Cook Alignment (back-rank, anastasia, hook) Summary

Hardened the three named-mate detectors that fell short of the 0.90 precision bar by porting
cook's exact geometry for each, then locked the D-09 never-regress precision floors. All three
mate motifs reached 1.000 TRAIN / 1.000 TEST precision.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Harden detect_back_rank_mate | de0df122 | tactic_detector.py, test_tactic_detector.py, report |
| 2 | Lift detect_anastasia_mate and detect_hook_mate | 0aaf9c23 | tactic_detector.py, test_tactic_detector.py, report |
| 3 | Lock never-regress floors for D-09 motifs | e63b7afb | precision_floors.py, report |

## Precision Lift Summary (TEST set, 5164 rows held out)

| Motif | P(train) before | P(test) before | P(train) after | P(test) after | Decision |
|-------|----------------|----------------|----------------|---------------|----------|
| back-rank-mate | 0.281 | 0.271 | 1.000 | 1.000 | SHIPPED — floor raised 0.20 -> 0.93 |
| anastasia-mate | 0.822 | 0.857 | 1.000 | 1.000 | SHIPPED — floor raised 0.75 -> 0.93 |
| hook-mate | 0.840 | 0.841 | 1.000 | 1.000 | SHIPPED — floor raised 0.80 -> 0.93 |

## Cook Predicates Implemented (D-10, no source copy)

### detect_back_rank_mate (Task 1)

Three-gate cook logic (from prose):
1. Board is checkmate AND opponent king on its back rank (already in prior code).
2. Own-blocker test: build the king's three forward squares (straight + two diagonals, clipped at a/h files). For each square: if empty, OR holds a pov piece, OR attacked by pov → return False. All three must be the defender's OWN pieces.
3. Back-rank-checker requirement: at least one checker must sit on the back rank (not just any pov checker).

Relative-rank arithmetic (Pitfall 3):
- `pov=WHITE` → opponent BLACK king on rank 7, forward_offset = -8.
- `pov=BLACK` → opponent WHITE king on rank 0, forward_offset = +8.

Named constants extracted: `_FORWARD_OFFSET_WHITE_POV = -8`, `_FORWARD_OFFSET_BLACK_POV = 8`, `_MIN_FILE = 0`, `_MAX_FILE = 7`.

**Root cause of 0.271 FP rate:** the old code accepted ANY checkmate with a back-rank king and at least one pov checker. This fired on corner mates (king on a8/h8/a1/h1 with empty or pov-controlled forward squares) where cook's own-blocker gate returns False.

### detect_anastasia_mate (Task 2)

Cook geometry (file-normalized, from prose):
- Mating piece lands on the king's file (new gate — previously absent).
- Normalize to a-file: a-file king uses +1/+3 toward center; h-file king uses -1/-3.
- Require opponent blocker at `king + center_sign * 1` (one step toward center).
- Require pov knight at `king + center_sign * 3` (three steps toward center).

Named constants: `_ANASTASIA_BLOCKER_OFFSET = 1`, `_ANASTASIA_KNIGHT_OFFSET = 3`.

**Root cause of 0.857 FP rate (99 FPs in train):** the old code accepted any pov knight anywhere on the board. The tight geometry requires the specific knight at king+3 in the normalized position; unrelated knights from other side-of-board positions were satisfying the loose check.

### detect_hook_mate (Task 2)

Cook's critical additional constraint: the knight defending the rook must ALSO be adjacent to the king (`chess.square_distance(knight_sq, opp_king_sq) == 1`), not merely any pov knight that geometrically attacks the rook square.

Named constant: `_HOOK_KNIGHT_MAX_DIST = 1`.

**Root cause of 0.841 FP rate (103 FPs in train):** arabian-mate positions (king in corner h8/h1) were satisfying the hook-mate chain. An f6/f3 knight is at Chebyshev distance 2 from h8/h1 but geometrically attacks g8/g1 via knight-move (L-shape). Without the distance-1 constraint, these arabian-mate positions fired as hook-mates. Cook's discriminator is that the knight in hook-mate must be adjacent to (next to) the king.

## D-09 Never-Regress Floor Update (Task 3)

| Motif | Floor before | Floor after | Reason |
|-------|-------------|-------------|--------|
| discovered-check | 0.80 | 0.85 | D-09 lock ≥0.85; train 0.913 / test 0.884 |
| double-check | 0.80 | 0.93 | train 1.000 / test 1.000; reflects measured value |
| smothered-mate | 0.90 | 0.93 | train 1.000 / test 1.000; reflects measured value |
| back-rank-mate | 0.20 | 0.93 | train 1.000 / test 1.000; phase 131-03 cook port |
| anastasia-mate | 0.75 | 0.93 | train 1.000 / test 1.000; phase 131-03 cook port |
| hook-mate | 0.80 | 0.93 | train 1.000 / test 1.000; phase 131-03 cook port |
| mate | 0.95 | 0.95 | unchanged (train 1.000 / test 1.000) |
| hanging-piece | 0.90 | 0.90 | confirmed; train 0.909 (depth-primary dispatch effect from plan-01) |

hanging-piece floor note: the D-09 "0.95 puzzle precision" referred to the Phase 127/128 baseline measurement (train 0.990 / test 0.952). Depth-primary dispatch from plan-01 correctly promoted hanging-piece for depth-0 positions but also changed which motif wins when geometrics are shallower, reducing overall train to 0.909. Floor at 0.90 still passes (margin = 0.009). A future phase can tune hanging-piece's dispatch priority if needed.

## D-09 Final Per-Motif TEST Precision Audit

All in-scope motifs measured on held-out TEST split (5164 rows, 2026-06-22 after plan 03):

| Motif | P(test) | GOAL | Status |
|-------|---------|------|--------|
| back-rank-mate | 1.000 | 0.90 | CLEARED (+0.729 from 0.271) |
| anastasia-mate | 1.000 | 0.90 | CLEARED (+0.143 from 0.857) |
| hook-mate | 1.000 | 0.90 | CLEARED (+0.159 from 0.841) |
| discovered-check | 0.884 | ≥0.85 | ABOVE FLOOR (+0.034) |
| smothered-mate | 1.000 | 1.00 | HOLDS |
| double-check | 1.000 | 1.00 | HOLDS |
| mate | 1.000 | 1.00 | HOLDS |
| hanging-piece | 0.884 | ≥0.90 | STILL BELOW (−0.016 gap; out of plan-03 scope) |

Motifs from prior plans (for reference):
| Motif | P(test) |
|-------|---------|
| fork | 0.998 |
| skewer | 1.000 |
| discovered-attack | 1.000 |
| pin | 0.819 (suppressed) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 13 back-rank-mate test fixtures failed under the new cook predicate (Task 1)**
- **Found during:** Task 1 test run
- **Issue:** Existing fixtures were True Positives under the old broken detector (any back-rank checkmate with any pov checker). The new own-blocker gate correctly rejects all 13 positions (corner mates, or positions with empty/pov-attacked forward squares).
- **Fix:** Replaced all 13 with new CC0 TPs from the precision harness where cook's own-blocker test passes.
- **Files modified:** tests/services/test_tactic_detector.py
- **Commit:** de0df122

**2. [Rule 1 - Bug] 12 of 13 anastasia-mate fixtures failed under the new cook predicate (Task 2)**
- **Found during:** Task 2 test run
- **Issue:** Old fixtures satisfied the loose "any pov knight anywhere" check. The tightened king+1/king+3 geometry test correctly rejects positions where the knight is not at the normalized position.
- **Fix:** Replaced all 12 failing fixtures with new CC0 TPs from the precision harness.
- **Files modified:** tests/services/test_tactic_detector.py
- **Commit:** 0aaf9c23

**3. [Rule 1 - Bug] 2 of 10 hook-mate fixtures failed under the new cook predicate (Task 2)**
- **Found during:** Task 2 test run
- **Issue:** 2 fixtures had knights at Chebyshev distance 2 from the king. Cook requires the knight to be adjacent to the king (distance 1). These were valid-looking hook-mate patterns but did not satisfy cook's exact geometry.
- **Fix:** Replaced 2 fixtures with CC0 TPs where the knight is adjacent to the king.
- **Files modified:** tests/services/test_tactic_detector.py
- **Commit:** 0aaf9c23

## Threat Flags

None. This plan makes no network, DB schema, or auth changes; detectors read stored PV data only.

## Self-Check: PASSED
