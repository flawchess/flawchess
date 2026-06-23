---
quick_id: 260623-r7a
slug: implement-the-three-precision-safe-move-
date: 2026-06-23
status: complete
---

# Summary: Move-type recall wins + discovered-check/attack recall

## What changed

Closed the addressable tactic-detector recall gaps identified in the recall analysis
(cross-checked against `lichess-puzzler/tagger/cook.py`). Root cause: lichess tags
promotion / under-promotion / en-passant / discovered-check by scanning **every** solver
move (`mainline[1::2]`); our detectors only inspected `moves[0]`.

`app/services/tactic_detector.py`:
- Added `_solver_move_indices()` helper (even move indices = the pov side's own moves).
- `detect_en_passant`, `detect_promotion`, `detect_under_promotion`: scan all solver moves,
  return the firing move index as `depth`. Replicated cook's under-promotion checkmate→knight
  rule.
- `detect_discovered_check`: scan all solver moves (was first-move only); return the first
  discovered check with its move index as `depth`.
- Dispatcher: gated the Tier-5 move-type collection behind `if not candidates` so move-type
  is a **strict residual fallback** — any tier 1-4 tactic now always wins the chip. This also
  fixed a pre-existing leak where a first-move promotion/en-passant at depth 0 could steal the
  chip from a real tactic at a deeper ply.

`tests/services/test_tactic_detector.py`: dropped an impure promotion fixture whose line
actually contains a skewer (it only tagged "promotion" via the now-removed depth-0 leak);
added a fixture guarding the new whole-line promotion scan (promotion on the 2nd pov move).

`tests/scripts/tagger/precision_floors.py`: refreshed the documented measurements for the
five affected motifs (floors unchanged; all clear). `CHANGELOG.md`: Changed bullet.
Regenerated `reports/tactic-tagger/tactic-tagger-2026-06-23.md`.

## Results (TRAIN / TEST recall, precision in parens — all precision floors PASS)

| Motif | Recall before | Recall after | Precision after |
|---|---|---|---|
| promotion | 0.047 | **0.487 / 0.481** | 1.000 / 1.000 |
| en-passant | 0.301 | **0.622 / 0.626** | 1.000 / 1.000 |
| under-promotion | 0.117 | **0.324 / 0.349** | 1.000 / 1.000 |
| discovered-check | 0.162 | **0.337 / 0.322** | 0.953 / 0.936 |
| discovered-attack | 0.235 | **0.260 / 0.257** | 0.990 / 0.982 |

Discovered-check precision dipped ~1pp on train (0.964→0.953, still far above the 0.85
floor) while recall doubled — within the "don't suffer considerably" bar, so kept. As a
bonus, making move-type residual restored/raised several real-tactic recalls (fork 1150→1168,
pin 952→967, deflection 478→490, x-ray 265→269 on train) with precision held.

## Verification

- `uv run pytest tests/scripts/tagger/test_detector_precision.py` — PASS (all floors hold).
- `uv run pytest tests/services/test_tactic_detector.py` — 79 passed, 7 skipped.
- `uv run pytest -n auto tests/ -k "tactic or flaw"` — 423 passed, 11 skipped.
- `uv run ruff format/check` + `uv run ty check app/ tests/` — clean.

## Out of scope (flagged, not done)

deflection-via-promotion branch and the trapped-piece predicate-fidelity gap — small,
precision-risky, left for a future pass.
