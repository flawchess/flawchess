---
quick_id: 261122-jsf
slug: fix-mate-tie-rule-in-forcing-line-gate
status: complete
date: 2026-11-22
commit: 4fe187674
---

# Quick 261122-jsf: Fix the mate tie rule in the forcing-line gate

## What changed

- `app/services/tactic_detector.py`: new public `is_mate_motif(motif_int)`.
- `app/services/forcing_line_gate.py`: `apply_forcing_line_filter` passes `mate_motif` through
  `is_solver_node_forced` into `_resolve_mate_priority`. For a mate motif, a solver node where both moves
  mate for the solver passes whatever the two distances are. The default (`mate_motif=False`) keeps the
  strict shorter-mate rule, so non-mate motifs and every direct caller are unchanged.
- `tests/services/test_forcing_line_gate.py`: `TestMateTieRule` (7 tests) on the real allowed blob of prod
  game 1461616 ply 76.
- `CHANGELOG.md`: bullet under `[Unreleased]` / Fixed.

The discovered-attack detector and the mate-tier short-circuit were not touched.

## Verification

- Gate test file: 93 passed. Related suites (flaws service, retag, ab-validate, eval drain, tactic detector):
  439 passed, 7 skipped.
- Mutation check: with the fix disabled, 3 of the new tests fail (node-level tie, real blob MATE, named mate).
- `ruff format`, `ruff check`, `ty check app/ tests/ scripts/`, nesting-depth gate: clean.
- The full pre-merge gate was not run (direct commit on `main`, relevant tests only).

## Impact measurement (prod, user 28, read-only)

`scripts/retag_flaws.py --db prod --user-id 28 --dry-run`, 36,087 flaws examined:

| Run | Rows that would change |
|-----|------------------------|
| Without the fix (existing drift) | 49 |
| With the fix | 1,202 |

So 1,153 rows (3.2% of the flaws) change because of the tie rule. No existing tag is removed or shifted in
either run, so every change is a tag added on a row whose allowed or missed tag is NULL today. The report
does not split additions by orientation or motif. For scale: the account carries 1,467 allowed generic MATE
tags today.

The dry-run report files were not kept (`reports/retag/retag-2026-11-22.md` was removed after the runs).

## Follow-ups

- A prod retag (`scripts/retag_flaws.py --db prod`) is needed for existing rows to pick the tag up. Not run.
- The benchmark DB needs the same retag, and the tactic zones in `app/services/tactic_delta_zones.py` may
  move with it (more mate tags on both sides).
- The size of the effect (1,153 added tags) was not spot-checked by hand. Many of these are likely deep
  mates with several mating paths; a sample review before the prod retag is advisable.
- Unchanged by design: a capped 12-ply mate line is tagged generic MATE at depth 11, also where a shallow
  material win (here a queen lost in two moves) sits in the same line.
