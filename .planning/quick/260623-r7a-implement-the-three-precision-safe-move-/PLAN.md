---
quick_id: 260623-r7a
slug: implement-the-three-precision-safe-move-
date: 2026-06-23
---

# Quick Task: Move-type recall wins + discovered-check/attack recall attempt

## Description

Increase tactic-detector recall **without** losing precision, based on the recall-gap
analysis cross-checked against `lichess-puzzler/tagger/cook.py`. Root cause for the
addressable gaps: lichess tags promotion / under-promotion / en-passant / discovered-check
by scanning **every solver move** (`mainline[1::2]`), while our detectors only inspect
`moves[0]` (the first refuting move).

## Scope

1. **promotion / en-passant / under-promotion (precision-safe wins).** Extend the three
   Tier-5 move-type detectors to scan all solver move indices (0, 2, 4, …) instead of only
   `moves[0]`. Return `depth = k` (the solver-move index where the move occurs) so the
   depth-primary dispatcher keeps real shallow tactics winning — a deep promotion must NOT
   out-rank a shallower real tactic. Replicate lichess's under-promotion checkmate→knight
   rule for fidelity. Simulated standalone result: **0 FP on both splits**, recall
   en-passant 0.30→~0.75, promotion 0.05→~0.55, under-promotion 0.12→~0.38 (dispatched).

2. **discovered-check / discovered-attack (try, keep only if precision holds).** Extend
   `detect_discovered_check` to scan all solver moves (lichess-faithful) instead of only
   the first. discovered-attack already scans the line and lichess defines it as
   `discovered_check OR capture-geometry`, so most discovered-attack "nothing" misses are
   resolved via the discovered-check fix (multi-label). **Acceptance gate:** keep ONLY if
   dispatched discovered-check TRAIN precision stays well above its 0.85 floor and does not
   drop considerably from the current ~0.96; otherwise revert this part.

## Verification

- `uv run pytest tests/scripts/tagger/test_detector_precision.py -s` — precision floors hold
  on TRAIN for every shipped motif.
- `uv run pytest tests/services/test_tactic_detector.py` — fast per-commit regression guards.
- Regenerate the tagger report; confirm recall rises for the targeted motifs and no shipped
  motif's precision regresses.
- `uv run ruff format/check` + `uv run ty check app/ tests/`.

## Out of scope

deflection-via-promotion branch and trapped-piece predicate-fidelity gap (small, precision-risky).
