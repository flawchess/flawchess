---
id: SEED-057
status: resolved
resolved: 2026-06-19
resolved_by: .planning/quick/260619-phr-implement-seed-057-pin-gate-parity-depth/
resolution_note: >
  Both bugs fixed. KEY FINDING: the parity fix ALONE regressed pin precision (0.413 ->
  0.393) because Check 1 is an accept-path, not a prune-path — fixing it short-circuits
  the only reject path (the replacement guard). Real fix = parity fix + reorder the gate
  so the replacement-guard REJECT runs before the direct-capture ACCEPT. Net on CC0 TRAIN:
  pin precision 0.413 -> 0.440, FP 478 -> 428, TP/recall flat; floor re-set 0.35 -> 0.40.
  Depth now returns max(0, k-1) (move index). Dev re-backfill (count drop) deferred — the
  offline CC0 harness is the authoritative precision signal (D-09).
planted: 2026-06-19
planted_during: v1.28 Tactic Tagging (Phase 127 — Detector Hardening & Validation)
trigger_when: before relying on pin tactic-tag precision or on pin's depth-vs-Rating signal — e.g. when Phase 129's always-on depth filter ships (pin depth is mis-scaled), or whenever pin false-positive rate matters. Re-measure precision via the Phase 127 CC0 harness after fixing.
scope: small
source: .planning/phases/127-detector-hardening-validation/127-REVIEW.md (WR-01, IN-01)
---

# SEED-057: Pin relevance-gate parity bug + pin `depth` is a board index, not a move index

Found by the Phase 127 advisory code review (`127-REVIEW.md`). Both bugs are isolated to
`detect_pin` / `_pin_wins_material` in `app/services/tactic_detector.py`. Phase 127 verified
5/5 SCs and shipped with these as accepted advisory findings — they explain why the pin gate
underperformed (pin precision regressed −4.7pp on the CC0 fixture; pin count stayed ~flat at
+13 on the dev re-backfill instead of dropping like fork's −7.6%).

## Bug 1 (WARNING WR-01) — parity bug makes the pin replacement-guard Check 1 a no-op

`_pin_wins_material` Check 1 (`tactic_detector.py:~367`) loops:

```python
for j in range(pin_board_idx + 1, len(moves), 2):
    ...  # intends to find a LATER pov move that captures the pinned piece
```

`pin_board_idx` is a **board** index (0 = starting position). pov's moves sit at **even** move
indices. When the pin is found at an even board index (`k = 0, 2, 4, …` — the common case,
including the starting position), `pin_board_idx + 1` is **odd**, so the loop iterates the
**opponent's** moves, not pov's. Check 1 therefore never finds pov's material-winning recapture
for even-`k` pins and the gate falls through to the default "accept" path — i.e. the relevance
gate (D-01) that was supposed to prune incidental pins barely fires. This is the mechanism
behind the flat pin count in the Phase 127 dev re-backfill.

**Fix sketch:** derive the correct move-index parity from the side to move at the pin board
(or iterate `range(first_pov_move_idx, len(moves), 2)` using pov's move parity), not from
`pin_board_idx + 1`. Mirror the working parity logic used by `detect_fork`'s gate.

## Bug 2 (INFO IN-01) — pin returns a board index as `depth`; every other motif returns a move index

`detect_pin` returns `k` from `enumerate(boards)` as the depth (`tactic_detector.py:~422`).
`k` is a **board** index (0 = start position) while every other detector returns a **move**
index (0 = first PV move). It does not affect dispatcher winner selection (depth is only a
same-tier/same-rank tiebreak and pin has a unique rank), but stored `tactic_depth` for pin is
off-by-one-ish and on a different scale than all other motifs. That **skews the depth-vs-Rating
correlation (D-06)** for the pin motif specifically, and Phase 129's always-on depth filter
treats stored depth as a difficulty proxy — so pin would be mis-bucketed.

**Fix sketch:** return the corresponding move index (e.g. `k - 1`, or the pov-move index that
established the pin) so pin depth shares the same semantics as the other 23 motifs.

## Why deferred (not fixed in Phase 127)

Fixing either bug changes the measured pin precision/recall, so it must be re-validated through
the Phase 127 CC0 harness (`tests/scripts/tagger/test_detector_precision.py`) and re-run through
the dev re-backfill (`scripts/backfill_flaws.py --db dev --full-evald-only`) to confirm pin
false positives actually drop without collapsing the motif. That re-opens the 127-03/127-04
validation loop, which is out of scope for a phase already verified complete. Phase 127's floors
were set from measurement (D-09), so the gate passes as-is; this seed is the path to making the
pin gate actually effective.

## Acceptance when picked up

- `_pin_wins_material` Check 1 iterates pov's moves for all pin board indices (parity fixed).
- Pin `tactic_depth` is a move index consistent with the other 23 motifs.
- Re-run the CC0 precision harness: pin precision improves (no longer regressed) and the
  pin floor in `precision_floors.py` is re-set from the new measured number.
- Dev re-backfill: pin count drops measurably vs the post-127 baseline (6,312) without
  collapsing, and pin depth-vs-Rating no longer looks anomalous.

(Unrelated minor finding from the same review — WR-02: a `chess.IllegalMoveError` swallowed
without `sentry_sdk.capture_exception()` in `flaws_service.py:~406` — is a CLAUDE.md Sentry-rule
nit, not part of this seed. IN-02 dead-code `if k < 2: continue` guards are pre-existing.)
