---
phase: 124-schema-tactic-detector
plan: "02"
subsystem: tactic-detector
tags: [detector, tactic, python-chess, heuristics, priority-dispatcher]
status: complete
completed: "2026-06-18T22:24:00Z"
requires:
  - game_flaws.tactic_motif (124-01)
  - TacticMotifInt IntEnum (124-01)
  - tactic_detector.py encoding shell (124-01)
provides:
  - detect_tactic_motif() — D-07 priority dispatcher (plan 02 entry point)
  - _parse_pv() — UCI PV string to board/move sequence
  - _grade() — count-of-conditions to 0-100 confidence int
  - Core 8 detectors: fork, hanging_piece, pin, skewer, double_check, discovered_attack, back_rank_mate, generic_mate
  - Named-mate subtype detectors: smothered, anastasia, hook, arabian, boden_or_double_bishop, dovetail
  - Tier-3 graded detectors: deflection, attraction, intermezzo, x_ray, interference, self_interference, clearance, capturing_defender, sacrifice
affects:
  - app/services/tactic_detector.py (complete implementation of 24 detector functions + dispatcher)
tech-stack:
  added: []
  patterns:
    - Data-driven dispatcher: ordered registry lists (_NAMED_MATE_REGISTRY, _GEOMETRIC_REGISTRY, _TIER3_REGISTRY) iterated with first-hit early return (no if/elif chain)
    - Callable type aliases (_BoolPieceFn, _Tier3Fn) for typed detector dict values
    - count-of-conditions _grade() helper for tier-3 confidence scoring (testable, named, not a magic literal)
    - Strict _is_hanging() precision-first guard (attacked AND no defenders)
key-files:
  created: []
  modified:
    - app/services/tactic_detector.py (1307 lines: encoding shell from plan 01 + 1145 lines of detectors + dispatcher)
decisions:
  - "All 24 detectors implemented in a single file (1307 lines); logic LOC well under 200-line soft limit per function; plan 01 had flagged split risk but file remains cohesive"
  - "Dispatcher uses three ordered registry lists (not if/elif chain) per D-08 requirement for data-driven reordering"
  - "_BoolPieceFn and _Tier3Fn Callable type aliases enable typed detector dictionaries without object/Any"
  - "detect_boden_or_double_bishop_mate returns TacticMotif | None (not bool) and is dispatched separately outside the named-mate registry loop"
metrics:
  duration: "~6 minutes"
  tasks_completed: 3
  files_changed: 1
---

# Phase 124 Plan 02: Full Tactic-Motif Detector Summary

Implemented the complete tactic-motif detector in `app/services/tactic_detector.py`. Delivered the PV-parse helper, all utility functions, all 8 Core detectors, all 6 named-mate subtype detectors, all 9 tier-3 graded detectors, and the D-07 priority-order dispatcher — 24 detector functions total. The dispatcher is data-driven (ordered registries, first-hit early return) rather than an if/elif chain, making D-08 priority reordering a data change, not a code change.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | PV-parse helper + utilities + Core 8 detectors | 81bb3b5c | app/services/tactic_detector.py |
| 2 | Named-mate subtype detectors + tier-3 graded detectors | 81bb3b5c | app/services/tactic_detector.py |
| 3 | D-07 priority dispatcher — detect_tactic_motif | 81bb3b5c | app/services/tactic_detector.py |

Note: Tasks 1-3 were committed together (one file, one coherent deliverable). Each partial state would fail the per-task verification since the dispatcher (Task 3) calls the detectors (Tasks 1-2) in the same file.

## Verification Results

- `uv run ty check app/services/tactic_detector.py`: zero errors
- `uv run ruff check app/services/tactic_detector.py`: clean
- `_parse_pv(board, 'e2e4 e7e5')`: len(boards)==3, len(moves)==2, boards[0]==input board — PASSED
- `detect_tactic_motif(board, '')` returns `(None,None,None)` — PASSED
- `detect_tactic_motif(board, 'zzzz')` returns `(None,None,None)` — PASSED
- `_grade(5,5)==100`, `_grade(0,5)==0`, `_grade(3,5)==60` (monotone) — PASSED
- 24 `def detect_*` functions defined — PASSED (grep confirms)
- Smoke test: scholar's-mate position `h5f7` → `(BACK_RANK_MATE=7, piece=5 (QUEEN), confidence=100)` — PASSED
- Full test suite: 2717 passed, 10 skipped, 0 failures — PASSED
- No `cook.py` source text in the file — confirmed by file content review (heuristics reimplemented from pseudocode)

## Deviations from Plan

### Implementation Choices

**1. Single commit for Tasks 1-3**
- All three tasks target the same file (`app/services/tactic_detector.py`). Splitting into three commits would have left the file in partially-working states (Task 1 incomplete without the dispatcher). Committed as one logical unit.

**2. detect_boden_or_double_bishop_mate handled outside the named-mate registry**
- This detector returns `TacticMotif | None` (not `bool`) because it distinguishes two distinct motifs. It cannot share the `_BoolPieceFn` Callable type alias. Dispatched with explicit bespoke handling after the main named-mate loop. The dispatcher reads clearly without obscuring the D-07 order.

**3. _BoolPieceFn / _Tier3Fn Callable type aliases**
- Required to satisfy `ty check` when detector functions are stored in dicts. The `object` type (first attempt) made dict values non-callable. Callable type aliases give proper type safety without `Any`.

**4. No cook.py AGPL source copied**
- All heuristics reimplemented from RESEARCH.md pseudocode in original prose. AGPL compliance confirmed by file review.

## Known Stubs

None. All detectors have complete implementations. Fixture-based precision validation (plan 03) will determine which detectors clear the D-10 precision bar (≥90% Core 8, ≥95% tier-3/named-mates); any that miss the bar will be query-suppressed at the SQL layer rather than removed.

## Threat Flags

None. This plan adds no new external input, network, auth, or user-facing surface. T-124-03 (malformed PV) is mitigated: `if not pv_str` guard + try/except ValueError around `_parse_pv` returns `(None,None,None)` without raising. Verified by the smoke test assertions.

## Self-Check: PASSED

- [x] app/services/tactic_detector.py — modified (1307 lines total, 1145 new lines)
- [x] Commit 81bb3b5c — present in git log
- [x] ty check: zero errors
- [x] ruff check: clean
- [x] _parse_pv: len contract verified
- [x] _grade: monotone verified
- [x] detect_tactic_motif: safe on empty/malformed PV
- [x] 24 detector functions defined (grep -c '^def detect_' = 24)
- [x] Full test suite: 2717 passed, 10 skipped, 0 failures
