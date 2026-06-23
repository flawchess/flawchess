---
phase: 134-trapped-piece-fixture-expansion-option-b-cook-predicate-reim
plan: "03"
subsystem: tactic-detector
tags: [tactic-detector, trapped-piece, precision-floor, ship-branch]
dependency_graph:
  requires: [134-02]
  provides: []
  affects: [tests/scripts/tagger/precision_floors.py, CHANGELOG.md]
tech_stack:
  added: []
  patterns:
    - precision-floor-gate (PRECISION_FLOOR["trapped-piece"] = 0.92 added to CI gate)
key_files:
  created: []
  modified:
    - tests/scripts/tagger/precision_floors.py
    - CHANGELOG.md
decisions:
  - "SHIP branch applied: P(train)=1.000 / P(test)=1.000 clears D-EXP-03 ≥0.80 bar decisively"
  - "PRECISION_FLOOR[\"trapped-piece\"] = 0.92 (~8pp below TRAIN 1.000, rounded to 0.01)"
  - "Family/chip wiring confirmed-present (not re-added): FAMILY_TO_MOTIF_INTS[trapped_piece] at library_repository.py:137 + frontend tacticComparisonMeta.ts:260"
metrics:
  duration_minutes: 3
  completed: 2026-06-23
  tasks_completed: 2
  tasks_total: 2
status: complete
---

# Phase 134 Plan 03: D-EXP-03 Ship Branch Summary

## One-liner

SHIP branch applied: trapped-piece removed from SUPPRESSED_MOTIFS, PRECISION_FLOOR 0.92 added; full pre-merge gate green with 2872 tests passing.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Apply D-EXP-03 SHIP branch to precision_floors.py | 5aeb909d | tests/scripts/tagger/precision_floors.py |
| 2 | Run full pre-merge gate and update CHANGELOG | 97ea0a2a | CHANGELOG.md |

## Branch Decision

**Branch chosen: SHIP**

Deciding numbers from 134-02-SUMMARY.md (Plan 02 post-dispatch measurement on the ~1065-row expanded fixture):

| Set | Precision | Recall | TP | FP | FN | n_gt |
|-----|-----------|--------|----|----|----|------|
| TRAIN | **1.000** | 0.755 | 565 | 0 | 183 | 748 |
| TEST | **1.000** | 0.754 | 239 | 0 | 78 | 317 |
| ΔP | 0.000 | | | | | |

Bar (D-EXP-03): P(train) ≥ 0.80 AND TEST holds (ΔP within 0.10). Result: 1.000 ≥ 0.80, ΔP = 0.000. SHIP branch is unambiguous.

## What Was Changed

### precision_floors.py

1. **Removed `"trapped-piece"` from `SUPPRESSED_MOTIFS`** — the motif is no longer suppressed from the floor gate.
2. **Added `PRECISION_FLOOR["trapped-piece"] = 0.92`** — floor set at ~8pp below TRAIN 1.000, rounded to 0.01. Comment: `train 1.000 / test 1.000 (565 TP, 0 FP; phase 134 cook trapped-piece port)`.
3. **Refreshed docstring measurement note (L142-148)** — replaced the stale "P(train)=0.249, still below ship bar" note with the actual post-rewrite numbers: P(train)=1.000 (565 TP, 0 FP) / P(test)=1.000 (239 TP, 0 FP), deltaP=0.000. Noted "Shipped phase 134".
4. **Updated SUPPRESSED_MOTIFS comment block** — replaced the old "detector rewrite = Plan 02, unsuppress = Plan 03" note with a "trapped-piece is NO LONGER suppressed" historical note.

### CHANGELOG.md

Added under `## [Unreleased]`:
- `### Added`: Trapped-piece tactic chip now ships (precision 1.000). (Phase 134)
- `### Fixed`: Eliminated trapped-piece false-positive source (was 153 FP / 0 TP). (Phase 134)

## Family/Chip Wiring Verification

Confirmed present (not re-added — Phase 129 already wired them):
- `app/repositories/library_repository.py` L137: `FAMILY_TO_MOTIF_INTS["trapped_piece"]` — FOUND
- `frontend/src/lib/tacticComparisonMeta.ts` L260: `family: 'trapped_piece'` with `chipLabel: 'trapped-piece'` — FOUND

No edits were made to either file.

## Verification

All gate items green:

| Check | Result |
|-------|--------|
| `uv run pytest tests/scripts/tagger/test_detector_precision.py -x -q` | 1 passed (trapped-piece floor-gated, 1.000 ≥ 0.92) |
| `uv run ruff format app/ tests/ scripts/` | 295 files unchanged |
| `uv run ruff check app/ tests/ scripts/ --fix` | All checks passed |
| `uv run ty check app/ tests/` | All checks passed (0 errors) |
| `uv run pytest -n auto -x` | 2872 passed, 18 skipped |
| Frontend gate | N/A — no frontend/ files changed across Phase 134 Plans 01-03 |

## Deviations from Plan

None. Plan executed exactly as specified: SHIP branch applied based on Plan-02 precision, family/chip wiring verified-present, gate green.

## Known Stubs

None. trapped-piece precision is real (measured on 1065 CC0 puzzle rows, 0 FP).

## Self-Check: PASSED

Files present:
- [FOUND] tests/scripts/tagger/precision_floors.py (contains PRECISION_FLOOR["trapped-piece"]=0.92, "trapped-piece" absent from SUPPRESSED_MOTIFS)
- [FOUND] CHANGELOG.md (contains Phase 134 Added + Fixed bullets under [Unreleased])

Commits present:
- [FOUND] 5aeb909d — feat(134-03): ship trapped-piece
- [FOUND] 97ea0a2a — chore(134-03): update CHANGELOG for Phase 134 ship
