---
quick_id: 261122-jsf
slug: fix-mate-tie-rule-in-forcing-line-gate
mode: quick
date: 2026-11-22
---

# Quick 261122-jsf: Fix the mate tie rule in the forcing-line gate

## Problem

Prod game 1461616, ply 76 (`Kf2`) has no allowed tactic tag. The refutation is a forced mate whose stored
line is capped at 12 plies, so the detector tags generic MATE at depth 11 (truncated-mate fallback). The
forcing-line gate then requires every solver node through depth 11 to be an only-move.
`_resolve_mate_priority` treats a node where both the best and the second-best move mate as forced only when
the best mate is strictly shorter (`abs(bm) < abs(sm)`). Node 10 has two mates in 2, so the gate rejects the
tag, and because the mate tier short-circuits the detector, nothing else is tagged.

Not a Phase 252 truncation case: the line is the full 12 plies. The discovered-attack detector is correct and
is not touched.

## Decision (owner, 2026-11-22)

The correct tag is the allowed checkmate. When two moves both mate, the quicker one is tagged, or either on a
tie. "You allowed a checkmate" is true whichever mating move is chosen.

Scope: mate motifs only. A non-mate motif (a fork whose firing node has two equally fast mates) keeps the
strict rule.

## Tasks

1. `app/services/tactic_detector.py`: add public `is_mate_motif(motif_int)` next to `floor_cp_for_motif`
   (reads `_MATE_MOTIF_INTS`).
   `app/services/forcing_line_gate.py`: thread a `mate_motif` flag from `apply_forcing_line_filter` through
   `is_solver_node_forced` into `_resolve_mate_priority`; when set, a node where both moves mate for the
   solver passes. Default False keeps every existing call site strict. Bug-fix comment at the fix site;
   module docstring updated.
2. `tests/services/test_forcing_line_gate.py`: regression test on the real blob (rejected before, credited
   after), a non-mate motif on a tied-mate node still rejected, node-level tests for both colors.
   Verify: `uv run pytest tests/services/test_forcing_line_gate.py tests/services/test_flaws_service.py`,
   ruff, ty. Mutation check: revert the fix and watch the regression test fail.
3. Measure (read-only, prod, user 28) how many untagged flaws gain a mate tag. `CHANGELOG.md` bullet under
   `[Unreleased]`. Note in SUMMARY that a prod retag is needed afterwards (not run here).

## Out of scope

The discovered-attack detector, the mate-tier short-circuit, the truncated-mate depth approximation, the
prod retag run.
