---
quick_id: 260630-jsr
slug: fix-bug-b-in-the-forcing-line-gate-make-
date: 2026-06-30
status: planned
---

# Quick Task 260630-jsr: Fix Bug B — depth-aware forcing-line gate

## Problem

`apply_forcing_line_filter` requires **every** solver node in the full stored PV
line to pass the only-move gate
(`all(is_solver_node_forced(node) for node in solver_nodes)`). Once the solver is
winning, the deep "keep converting" nodes have many near-equal good moves and fail
the only-move test, so a legitimate tactic that fired and won material at the
firing node is rejected. The still-winning floor (D-09) doesn't help: a flatly
winning line never drops below +200 cp, so it never truncates and the whole line
stays in scope.

Diagnosed in UAT (`reports/retag/ab-validation-2026-06-30.md`, case 27: game
681358 ply 16 — a real allowed fork `...e5` forking Bf4+Nd4, still suppressed even
after the Bug A fix). Its firing node (index 0) is a unique only-move, but deep
nodes idx2–idx12 fail, so `all(...)` rejects it.

## Fix

Make the gate **depth-aware**: only require forcedness for solver nodes up to and
including the tactic's **firing depth** (the firing solver node and any solver
moves leading to it). The conversion after the tactic fires need not be unique.

The detector already returns a `depth` per motif (half-moves from the firing
position; node index i corresponds to depth i, solver nodes at even indices). Thread
that depth into the gate.

### Changes

1. **`app/services/forcing_line_gate.py`** — `apply_forcing_line_filter`:
   - Add param `firing_depth: int | None = None` (inserted before `margin`).
   - `firing_depth=None` preserves the legacy whole-line check (backward compatible —
     keeps every existing gate unit test valid).
   - When set: after still-winning-floor truncation + trailing strip, require only
     solver nodes at even index `i <= firing_depth` to be forced.
   - Guard: if `firing_depth >= len(stripped)` the firing node was truncated away
     (tactic fizzled before firing) → return False.
   - Keep already-winning reject, floor truncation, trailing strip, and the
     one-mover discard (`len(solver_nodes) < 2`) unchanged — Bug B is strictly about
     the forcedness `all(...)` scope.
   - Add a small helper `_solver_nodes_through_firing_depth(line, firing_depth)`.
   - Update the module docstring (D-07 / GATE-01 description) to note depth-awareness.

2. **`app/services/flaws_service.py`** — `_classify_tactic_gated` (line ~558):
   pass `firing_depth=depth` (the detector depth) into the gate call.

3. **`tests/services/test_forcing_line_gate.py`**:
   - Keep all existing tests (they use `firing_depth=None` default → unchanged).
   - Add a `TestDepthAwareForcedness` class: a case-27-shaped line (forced firing
     node at idx0, non-forced deep nodes) → rejected with `firing_depth=None`,
     **passes** with `firing_depth=0`; a depth-2 case requiring idx0 & idx2 forced;
     the truncated-firing-node guard.

4. **`tests/scripts/test_ab_validate_gate.py`** — update the `_spy_gate` wrapper
   signature to accept `firing_depth` (the gate is now called with that keyword).

## Verification

- `uv run pytest tests/services/test_forcing_line_gate.py tests/services/test_flaws_service.py tests/scripts/test_ab_validate_gate.py -n auto`
- `uv run ruff format/check` + `uv run ty check` on changed files.
- Re-run `uv run python scripts/ab_validate_gate.py --db dev --user-id 28 --neighbourhood`;
  confirm case 27 (game 681358 ply 16) survives and FORK/allowed suppression drops
  meaningfully without admitting obvious noise.

## Out of scope

- One-mover discard semantics (kept as-is).
- Re-tagging stored production flaws (separate backfill).
- Detector depth-convention quirks (k-1 adjustments) — being slightly permissive is
  safe since the firing node at idx0 is always checked.
