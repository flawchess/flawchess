---
quick_id: 260619-phr
title: Implement SEED-057 — pin gate parity + depth-index fix
status: in-progress
date: 2026-06-19
source_seed: .planning/seeds/SEED-057-pin-gate-parity-and-depth-index-bug.md
---

# Quick Task 260619-phr: SEED-057 pin gate parity + depth-index fix

Two isolated bugs in `app/services/tactic_detector.py` (`detect_pin` /
`_pin_wins_material`), found by the Phase 127 advisory review. Fix both, re-validate
through the offline CC0 precision harness, re-set the pin precision floor from the
new measured number.

## Tasks

### Task 1 — Fix the pin relevance-gate parity bug (WR-01)
- **files:** `app/services/tactic_detector.py`
- **action:** In `_pin_wins_material` Check 1, the loop `range(pin_board_idx + 1, len(moves), 2)`
  iterates the *opponent's* moves whenever the pin is found at an even board index
  (the common case, incl. the start position), because pov's moves sit at even move
  indices. Start the scan at the first pov (even-index) move at/after the pin board:
  `first_pov_move = pin_board_idx + (pin_board_idx % 2)`. Add a SEED-057 fix comment.
- **verify:** offline CC0 harness re-run; pin FP drops / precision rises vs baseline
  (TRAIN P=0.413, TP=336, FP=478).
- **done:** Check 1 iterates pov's moves for all pin board indices.

### Task 2 — Fix pin `depth` to be a move index (IN-01)
- **files:** `app/services/tactic_detector.py`
- **action:** `detect_pin` returns board index `k` as depth; every other motif returns
  a move index (0 = first PV move). Return `max(0, k - 1)` (board `k` follows move `k-1`;
  clamp for `k==0` where the pin predates the PV window). Update the docstring. Add a
  SEED-057 fix comment.
- **verify:** harness depth-vs-Rating correlation still computes; pin depth on the same
  scale as other motifs.
- **done:** pin `tactic_depth` is a move index consistent with the other 23 motifs.

### Task 3 — Re-set the pin precision floor from the new measurement (D-09)
- **files:** `tests/scripts/tagger/precision_floors.py`
- **action:** Re-run the harness post-fix; update the pin row in the measurement-summary
  docstring and re-set `PRECISION_FLOOR["pin"]` to ~5-8pp below the new measured TRAIN
  precision (rounded to 0.05). Update the SEED-057 note in the floor-comment block.
- **verify:** `uv run pytest tests/scripts/tagger/test_detector_precision.py -s -o addopts=""` passes.
- **done:** pin floor reflects the post-fix measured number; gate green.

## Out of scope / deferred
- Dev re-backfill (`scripts/backfill_flaws.py --db dev --full-evald-only`) to confirm the
  6,312 → lower pin-count drop: DB-heavy, multi-minute, requires the drain worker. The
  offline CC0 harness is the authoritative precision signal (D-09); the re-backfill is a
  population-level sanity check. Flagged for a follow-up if pin count matters operationally.
- WR-02 (Sentry capture nit in flaws_service.py) and IN-02 (dead-code guards) are explicitly
  not part of SEED-057.
