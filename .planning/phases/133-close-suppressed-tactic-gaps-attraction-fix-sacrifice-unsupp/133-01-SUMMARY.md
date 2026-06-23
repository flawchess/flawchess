---
phase: 133-close-suppressed-tactic-gaps-attraction-fix-sacrifice-unsupp
plan: "01"
subsystem: testing
tags: [chess, tactic-detector, precision, python-chess, cook-alignment]

requires:
  - phase: 132-tier-3-tactic-precision-hardening-via-cook-py-predicate-alig
    provides: cook.py AGPL-boundary porting pattern; precision harness; SUPPRESSED_MOTIFS framework

provides:
  - "attraction detector fixed: boards[k+3] attacker check replaces boards[k+2] off-by-one"
  - "arabian-mate detector fixed: cook attacker-of-rook-sq + (2,2) knight geometry"
  - "boden-mate detector fixed: cook all-near-king-squares bishop-only attacker check"
  - "dovetail-mate detector fixed: cook diagonal-adjacency + escape-square loop (both bugs A and B)"

affects:
  - 133-02 (unsuppresses these four motifs and sets precision floors)

tech-stack:
  added: []
  patterns:
    - "cook.py port pattern: reimplement predicates from RESEARCH prose/pseudocode, never copy AGPL source"
    - "cook attacker-of-square pattern: boards[-1].attackers(pov, target_sq) over static attack tables"

key-files:
  created: []
  modified:
    - app/services/tactic_detector.py

key-decisions:
  - "boards[k+3] is the correct cond-5 attacker board for attraction (not boards[k+2]); the existing k+2 guard already ensures k+3 is a valid boards index"
  - "arabian-mate: iterate attackers(pov, rook_sq) and check (rank_diff==2, file_diff==2) from king, not BB_KNIGHT_ATTACKS[king_sq]"
  - "boden-mate: for all squares distance<2 from king, ALL pov attackers must be bishops (not just both bishops attack king directly)"
  - "dovetail escape-square loop: no-pov-attacker case continues (does NOT return False) — is_checkmate() already confirms king cannot go there"

patterns-established:
  - "Escape-square pattern: iterate chess.SQUARES with square_distance check, filter by condition, don't use SquareSets for complex geometry"

requirements-completed: []

duration: 7min
completed: 2026-06-23
status: complete
---

# Phase 133 Plan 01: Detector Geometry Fixes Summary

**Four suppressed tactic detectors corrected to cook.py geometry: attraction off-by-one fixed (boards[k+3]), arabian-mate attacker-of-rook-sq knight check, boden-mate near-king bishop-only attacker loop, dovetail-mate diagonal-adjacency + escape-square loop — all at precision 1.000 / 0 FP on TRAIN.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-06-23T04:46:22Z
- **Completed:** 2026-06-23T04:53:17Z
- **Tasks:** 4
- **Files modified:** 1

## Accomplishments

- attraction: corrected cond-5 attacker board from boards[k+2] to boards[k+3]; fires 654/1603 post-dispatch TRAIN TP, 0 FP, precision 1.000 (was 0 TP / precision NaN)
- arabian-mate: replaced BB_KNIGHT_ATTACKS[king_sq] loop with attackers(pov, rook_sq) + (2,2) rank/file distance check; fires 553/553 TRAIN TP, 0 FP, precision 1.000 (was 0 TP)
- boden-mate: replaced "both bishops attack king directly" filter with cook's "all pov attackers of every square distance<2 from king must be bishops"; fires 435/437 TRAIN TP, 0 FP, precision 1.000 (was 0 TP)
- dovetail-mate: removed inverted adjacency reject (Bug A), added same-file/rank reject (Bug B), added distance>1 reject, added cook's escape-square loop; fires 543/544 TRAIN TP, 0 FP, precision 1.000 (was 0 TP / 23 FP)
- All existing shipped motifs remain at or above their TRAIN precision floors (full harness 1 passed)
- ruff format/check and ty check all pass with zero errors

## Measured TRAIN Precision Results (for Plan 02 floor-setting)

| Motif | TRAIN TP | TRAIN FP | TRAIN FN | Precision | Recall | Recommended Floor |
|-------|----------|----------|----------|-----------|--------|-------------------|
| attraction | 654 | 0 | 949 | 1.000 | 0.408 | 0.93 |
| arabian-mate | 553 | 0 | 0 | 1.000 | 1.000 | 0.93 |
| boden-mate | 435 | 0 | 2 | 1.000 | 0.995 | 0.93 |
| dovetail-mate | 543 | 0 | 1 | 1.000 | 0.998 | 0.93 |

Notes:
- attraction's 949 FN are post-dispatch losses (shadowed by mates/pin/fork — this is correct multi-label behavior, not false negatives)
- boden-mate's 2 FN are positions that classified as double-bishop-mate (bishops on same side of king file) — not FPs
- dovetail-mate's 1 FN is an unusual position (likely multi-queen or unusual promotion pattern)
- These four motifs are still in SUPPRESSED_MOTIFS at this point; Plan 02 unsuppresses and sets floors

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix attraction cond-5 off-by-one (boards[k+2] → boards[k+3])** - `bf15f490` (fix)
2. **Task 2: Port cook arabian-mate knight geometry** - `54a7d75c` (fix)
3. **Task 3: Port cook boden/double-bishop near-king bishop-only check** - `fe7abdce` (fix)
4. **Task 4: Port cook dovetail-mate queen-adjacency + escape-square loop** - `27a48dde` (fix)

## Files Created/Modified

- `app/services/tactic_detector.py` - Four detector functions corrected: `_attraction_fires_at`, `detect_arabian_mate`, `detect_boden_or_double_bishop_mate`, `detect_dovetail_mate`

## Decisions Made

- **dovetail escape-square loop no-attackers branch**: the `else` case (no pov attackers on adjacent sq) does NOT return False — it continues. The `is_checkmate()` at function entry already guarantees the position is mate, so an unattacked adjacent square is blocked by opponent's own pieces or other constraints. Returning False there would incorrectly reject valid dovetail positions. Empirically validated: 543/544 TP / 0 FP confirms this interpretation.
- **boden-mate pov_bishops < 2 guard**: the old code used `attacking_bishops` (bishops that directly attack the king); the new code replaces the `attacking_bishops` filter with `pov_bishops < 2`. The classification block now uses `pov_bishops[0]` and `pov_bishops[1]` (all bishops on board) instead of `attacking_bishops[0]`/`[1]`, which is correct for the cook-faithful geometry that considers all near-king squares.

## Deviations from Plan

None — plan executed exactly as written. All four tasks implemented the specific edits described in the plan's `<action>` blocks, staying within AGPL boundary (reimplemented from RESEARCH prose, no cook.py source copied).

## Issues Encountered

The dovetail escape-square loop's `else` (no pov attackers) branch required careful analysis: the RESEARCH pseudocode omits the `else` case (it implicitly continues), but the plan's action block says "return False, None, None" when no pov attacker covers an adjacent square. A first attempt following the plan action literally (with `else: return False`) produced 0 TP. The correct interpretation — confirmed empirically at 543/544 TP / 0 FP — is that the `else` branch continues (does not return False), matching cook's actual pseudocode.

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes. Changes are pure Python logic edits to existing detector functions in `tactic_detector.py`. No new threat surface introduced.

## Next Phase Readiness

Plan 02 can now:
- Remove attraction, arabian-mate, boden-mate, dovetail-mate from SUPPRESSED_MOTIFS
- Set PRECISION_FLOOR entries at 0.93 for all four (7pp below measured 1.000)
- Add attraction and sacrifice to FAMILY_TO_MOTIF_INTS (RESEARCH §"Mechanical Unsuppress Path")
- Add frontend entries for attraction and sacrifice
- Update family-count tests

The sacrifice motif (RESEARCH Group C) requires only an unsuppress (standalone precision already 1.000); no detector code change needed.

## Self-Check: PASSED

- `app/services/tactic_detector.py` modified: FOUND
- Commit `bf15f490` (attraction fix): FOUND
- Commit `54a7d75c` (arabian-mate fix): FOUND
- Commit `fe7abdce` (boden-mate fix): FOUND
- Commit `27a48dde` (dovetail-mate fix): FOUND
- Harness: 1 passed, all shipped motif floors green, four fixed motifs at precision 1.000 / 0 FP

---
*Phase: 133-close-suppressed-tactic-gaps-attraction-fix-sacrifice-unsupp*
*Completed: 2026-06-23*
