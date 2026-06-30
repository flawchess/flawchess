---
quick_id: 260630-jsr
slug: fix-bug-b-in-the-forcing-line-gate-make-
date: 2026-06-30
status: complete
---

# Quick Task 260630-jsr — Summary

## What changed

Made the forcing-line gate **depth-aware** so it no longer rejects legitimate
tactics whose follow-up conversion has multiple winning paths (Bug B).

- `app/services/forcing_line_gate.py`: `apply_forcing_line_filter` gained a
  `firing_depth: int | None = None` parameter. Only solver nodes at even index
  `<= firing_depth` (the firing node and the solver moves leading to it) must pass
  the only-move gate; the conversion tail is exempt. Added helper
  `_solver_nodes_through_firing_depth` and a guard that rejects when the firing node
  did not survive the still-winning-floor truncation. `firing_depth=None` preserves
  the legacy whole-line check (all existing unit tests unchanged). Updated module +
  function docstrings.
- `app/services/flaws_service.py`: `_classify_tactic_gated` passes
  `firing_depth=depth` (the detector's tactic depth) into the gate.
- `tests/services/test_forcing_line_gate.py`: added `TestDepthAwareForcedness`
  (5 cases) modeling report case 27.
- `tests/scripts/test_ab_validate_gate.py`: updated the gate spy wrapper signature
  for the new `firing_depth` argument.

## Verification

- `tests/services/test_forcing_line_gate.py` + `test_flaws_service.py` +
  `test_ab_validate_gate.py`: 193 passed. `test_retag_flaws.py` +
  `test_flaws_materialization.py`: 32 passed.
- ruff format/check + ty: clean on all changed files.
- Re-ran `ab_validate_gate.py --db dev --user-id 28 --neighbourhood`:
  - **Case 27 (game 681358 ply 16) now survives** (no longer a dropped case).
  - FORK/allowed suppression 97.6% → 83.1%; HANGING_PIECE/allowed 96.5% → 65.3%;
    allowed gated-survived 80 → ~175. No motif flooded to 0% (noise still filtered).

## Notes

- A MultiPV backfill is actively running on the dev DB (blob count rising), so the
  report's absolute ungated counts drift run-to-run. This is independent of the gate
  (the ungated arm never calls the gate); the qualitative Bug B result is stable.
- Production stored tags are unchanged until a re-tag/backfill runs (out of scope).
- Out of scope (unchanged): one-mover discard semantics; detector depth-convention
  quirks (the firing node at idx0 is always checked, so being slightly permissive on
  deeper k-1 quirks is safe).
