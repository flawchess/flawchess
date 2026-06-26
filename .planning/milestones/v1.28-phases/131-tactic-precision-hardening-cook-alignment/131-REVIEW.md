---
phase: 131-tactic-precision-hardening-cook-alignment
reviewed: 2026-06-22T12:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - app/services/tactic_detector.py
  - app/services/flaws_service.py
  - app/repositories/library_repository.py
  - scripts/tactic_tagger_report.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 131: Code Review Report

**Reviewed:** 2026-06-22
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Phase 131 ships the cook.py predicate alignment (Workstream A), the depth-primary dispatch
rework (D-05), and the missed-pass dest-square gate (Workstream B / D-03). The overall
structure is sound: the new shared utilities (`_is_defended`, `_is_in_bad_spot`,
`_VALUES_NO_KING`) are correctly designed and their consumers (fork, skewer) wire them up
properly. The dispatcher sort key, Candidate tuple indexing, and `has_forced_mate` threading
in `flaws_service.py` are all correct. Two bugs were found that affect correctness: one in
`detect_discovered_attack` (wrong board passed to `is_castling`) and one depth off-by-one
also in `detect_discovered_attack`. Two informational issues round out the review.

---

## Warnings

### WR-01: `detect_discovered_attack` uses wrong board state to check for castling

**File:** `app/services/tactic_detector.py:797`

**Issue:** The castling guard is meant to skip `prev` (the k-2 pov move) when `prev` was
castling, because castling cannot unblock a ray. The guard calls
`board_before.is_castling(prev)` where `board_before = boards[k]` — the board state TWO
half-moves AFTER `prev` was played.

`chess.Board.is_castling(move)` is board-state-aware: it checks whether `self.kings &
BB_SQUARES[move.from_square]` is non-zero (i.e., is the king still on its original square?).
After a castling move the king has left its original square (e.g. e1 → g1). At `boards[k]`,
the king is already at g1, so `BB_SQUARES[e1] & self.kings == 0` and `is_castling` returns
`False` — silently defeating the guard.

**Failure path:** If pov castled at k-2 AND the capturer-to-target ray passes through the
original king square (e.g. a rook on a-file capturing on h-file with the e-file between
them), the guard fails and a false-positive discovered-attack fires. Rare geometrically, but
not impossible in practical PVs.

**Fix:** Use the board state from BEFORE `prev` was played:

```python
# Wrong: uses boards[k] (two half-moves after prev)
if board_before.is_castling(prev):
    continue

# Correct: use boards[k-2] (the board prev was played from)
if boards[k - 2].is_castling(prev):
    continue
```

---

### WR-02: `detect_discovered_attack` depth return is off by one (k vs k-1)

**File:** `app/services/tactic_detector.py:819`

**Issue:** The loop variable `k` in `detect_discovered_attack` is the MOVE index (from
`range(2, len(moves), 2)`). The docstring at line 767 explicitly states `depth = k
(half-moves from flaw_ply+1, per Pitfall 6 / SEED-057 convention)`. The return statement
at line 819 is:

```python
return True, capturer.piece_type, max(0, k - 1)
```

This returns `k - 1` instead of `k`. The pattern `max(0, k-1)` was copied from
`detect_pin` (line 609), where `k` is the BOARD index and `k-1` correctly converts to the
move index. In `detect_discovered_attack`, `k` is already the move index, so
`max(0, k-1) = k-1` underreports depth by 1. The minimum firing depth is k=2 (loop starts
at 2), so the minimum stored depth would be 1 instead of 2.

Compare with `detect_skewer` (line 681), which uses the identical loop convention and
correctly returns `k` as depth.

**Impact:** `discovered_attack` depth is stored systematically one ply too shallow in
`tactic_depth`. This affects the difficulty filter in `library_repository.py` (the
depth-range filter) and the depth-vs-rating Pearson correlation computed in the harness
(`scripts/tactic_tagger_report.py`). Discovered-attack flaws will appear one difficulty
level shallower than they truly are.

**Fix:**

```python
# Wrong — copies detect_pin's k-is-board-index convention but k here is move index
return True, capturer.piece_type, max(0, k - 1)

# Correct — consistent with detect_skewer and the docstring
return True, capturer.piece_type, k
```

---

## Info

### IN-01: Pin surfaces in UI at 0.819 TEST precision with no suppression mechanism

**File:** `app/repositories/library_repository.py:116-122`

**Issue:** Pin is in `SUPPRESSED_MOTIFS` in `precision_floors.py` (below the 0.90 ship
bar), but it remains in `FAMILY_TO_MOTIF_INTS` to satisfy the 10-family G-01 contract.
The comment acknowledges that the `_TACTIC_CHIP_CONFIDENCE_MIN = 70` lever cannot suppress
Tier-2 motifs because they always emit `TACTIC_CONFIDENCE_HIGH = 100` — above the 70
threshold. The result is that pin chips will appear in the comparison UI at 0.819 precision.

This is documented as an intentional trade-off, but the inability of the suppression lever
to gate Tier-2 motifs is a structural gap that will affect any future motif that fails the
ship bar but cannot be removed from `FAMILY_TO_MOTIF_INTS`. No code fix is required for
this phase, but the gap should be tracked for the next tactic precision phase.

**Suggestion:** When a Tier-2 motif misses the 0.90 bar, removing it from
`FAMILY_TO_MOTIF_INTS` is the only reliable suppression path. The G-01 10-family contract
test would need updating, which is the known blocker. Document this explicitly in the next
phase's CONTEXT rather than leaving it as a comment.

---

### IN-02: GOALS table in `tactic_tagger_report.py` now understates achieved precision for skewer

**File:** `scripts/tactic_tagger_report.py:129`

**Issue:** The GOALS entry for skewer is `{"precision": 0.90, "recall": 0.30}`. The Phase
131 cook port achieved 1.000 TEST precision and 1.000 TEST recall (432 TP, 0 FP, as
recorded in `precision_floors.py:57`). The GOALS entry predates the cook port and now
describes a threshold well below what is actually locked in via the precision floor (0.93).

The `/loop` self-improvement driver will trivially clear the skewer goal on its first
evaluation, which is not harmful but misleads about how much headroom remains. The
precision floor (0.93) is the real regression guard; the GOALS entry should reflect
ambition, not a stale baseline.

**Suggestion:** Raise the skewer goal to match or exceed the floor, e.g.:
```python
"skewer": {"precision": 0.95, "recall": 0.60},
```

---

_Reviewed: 2026-06-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
