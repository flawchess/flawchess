---
phase: 132-tier-3-tactic-precision-hardening-via-cook-py-predicate-alig
plan: "02"
subsystem: tactic-detection
tags: [tactic-tagger, cook-py, deflection, clearance, precision-hardening, and-chain]
requires: [phase-132-goals-dict, phase-132-baseline-snapshot]
provides: [deflection-cook-and-chain, clearance-cook-and-chain, phase-132-02-floors]
affects:
  - app/services/tactic_detector.py
  - tests/services/test_tactic_detector.py
  - tests/scripts/tagger/precision_floors.py
  - reports/tactic-tagger/tactic-tagger-2026-06-22.md
  - CHANGELOG.md
tech_stack:
  added: []
  patterns: [cook-and-chain, tdd-red-green, precision-floor-gate]
key_files:
  modified:
    - app/services/tactic_detector.py
    - tests/services/test_tactic_detector.py
    - tests/scripts/tagger/precision_floors.py
    - reports/tactic-tagger/tactic-tagger-2026-06-22.md
    - CHANGELOG.md
decisions:
  - "deflection rewritten to 11-condition AND-chain (cook lines ~399-441); returns TACTIC_CONFIDENCE_HIGH; helper _deflection_fires_at extracts the per-k logic"
  - "clearance rewritten to 9-condition AND-chain; condition 8 uses chess.SquareSet.between() for ray geometry; condition 9 uses _is_in_bad_spot()"
  - "_VALUES_NO_KING used throughout deflection (Pitfall 3 from RESEARCH); init_board=boards[k-2] is the grandparent board (Pitfall 2)"
  - "Fixture label updates: 4 cross-motif reclassifications invalidated by new AND-chains; updated comments to document Phase 132 reason"
  - "deflection SHIPS: P(test)=1.000 > 0.90 bar; floor raised 0.10 -> 0.93"
  - "clearance SHIPS: P(test)=0.952 > 0.90 bar; floor raised 0.30 -> 0.87"
metrics:
  duration: "~2 hours"
  completed: "2026-06-23"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 5
status: complete
---

# Phase 132 Plan 02: Deflection + Clearance Cook AND-Chain Rewrites Summary

Rewrote `detect_deflection` (11-condition AND-chain) and `detect_clearance` (9-condition AND-chain) to exactly match cook.py's geometry, replacing the old graded `_grade(met, total)` voting. TEST precision jumped from 0.210/0.371 to 1.000/0.952. Both motifs now ship with raised precision floors.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1+2 | Rewrite detect_deflection + detect_clearance to cook AND-chains | 0712440a | app/services/tactic_detector.py, tests/services/test_tactic_detector.py |
| 3 | Ship deflection + clearance with measured precision floors | ea2ae95f | tests/scripts/tagger/precision_floors.py, reports/tactic-tagger/ |
| — | CHANGELOG update | 5528b33a | CHANGELOG.md |

## Precision Results

| Motif | P(train) before | P(train) after | P(test) before | P(test) after | Decision |
|-------|----------------|----------------|----------------|---------------|----------|
| deflection | 0.235 | 0.994 | 0.210 | 1.000 | SHIPPED (floor 0.10 -> 0.93) |
| clearance | 0.348 | 0.913 | 0.371 | 0.952 | SHIPPED (floor 0.30 -> 0.87) |

Measurement: 11,855 TRAIN / 5,164 TEST rows (CC0 lichess puzzles, deterministic 70/30 split).

## Implementation Details

### detect_deflection — 11-condition AND-chain

New structure: `_deflection_fires_at(boards, moves, pov, k)` helper + thin
`detect_deflection` loop over even k values.

Key conditions:
- Condition 1: capture OR promotion
- Condition 2: value guard using `_VALUES_NO_KING` (Pitfall 3 — not `_PIECE_VALUES`)
- Condition 7: prior pov move quality gate (not a winning capture)
- Condition 8: square collision guards (not landing where opp or prior pov just moved)
- Condition 9: deflection geometry — opp captured pov's prior piece OR was in check
- Condition 10: square was reachable from deflected piece's ORIGINAL position
- Condition 11: KEY guard — deflected piece no longer covers capture square

Index convention (Pitfall 2): `boards[k-2]` = board before prior pov move (cook's
`grandpa.board()`), `boards[k-1]` = after prior pov move, `boards[k]` = before current
pov move.

### detect_clearance — 9-condition AND-chain

Key conditions:
- Condition 1: pov moves to EMPTY square (no capture)
- Condition 2: moved piece is a ray piece (Q/R/B) of pov's color after move
- Condition 3: prior pov move NOT a promotion
- Conditions 4-5: prior pov move didn't land on clearing from/to-square
- Condition 6: opponent NOT in check before pov's clearing move
- Condition 7: after clearing, no check OR opponent king didn't respond
- Condition 8: prior pov came FROM clearing destination OR from a between-square
  (via `chess.SquareSet.between()`)
- Condition 9: prior pov destination was "bad" (empty dest OR `_is_in_bad_spot()`)

## Cross-Fixture Label Updates

Four cross-motif reclassification labels were invalidated by the new AND-chains:

| Fixture list | FEN (abbreviated) | Old label | New label | Reason |
|---|---|---|---|---|
| `_ATTRACTION_FIXTURES` | `4r2k/7p/8/...` | clearance | attraction | New cook clearance no longer fires; attraction wins at depth 4 |
| `_ATTRACTION_FIXTURES` | `r1bq1rk1/pppp1ppp/...` | clearance | attraction | New cook clearance no longer fires; attraction wins at depth 8 |
| `_FORK_FIXTURES` | `r3r1k1/ppp2ppp/...` | clearance | intermezzo | New cook clearance no longer fires; intermezzo fires at depth 10 |
| `_INTERMEZZO_FIXTURES` | `r4b1r/pp2pkp1/...` | intermezzo | clearance | New cook clearance fires at depth 2 before intermezzo |

These reflect genuine dispatch changes from the new AND-chains, not bugs. All updated
with inline comments explaining the reclassification and phase number.

## AGPL Boundary

Both detectors rewritten from RESEARCH.md plain-English pseudocode. No source code from
`/home/aimfeld/Projects/Python/lichess-puzzler/tagger/cook.py` was copied or adapted.
The research document's pseudocode was the sole reference for condition semantics.

## Deviations from Plan

**[Rule 1 - Bug] Removed unused `pre_board` variable in `_deflection_fires_at`**
- Found during: ruff check (pre-merge gate)
- Issue: `pre_board = boards[k - 1]` was assigned but never referenced in any condition
- Fix: removed the assignment
- Files modified: app/services/tactic_detector.py
- Commit: included in 0712440a (pre-merge ruff fix, no separate commit needed)

**[Rule 2 - Fixture updates] Old fixtures were FPs under cook AND-chains**
- Found during: Tasks 1+2 (RED phase — all 16 deflection + 13 clearance fixtures failed
  the new AND-chain during the RED phase)
- Issue: Old fixtures were labeled by the old `met >= N` voting detector and genuinely
  do not satisfy cook's strict geometry. They were false positives under old voting, not
  true positives under cook.
- Fix: Replaced all 29 fixtures (16 deflection + 13 clearance) with verified TPs from
  CC0 training corpus. Added 4 cross-motif reclassification label updates.
- Files modified: tests/services/test_tactic_detector.py

## Known Stubs

None. Both detectors are fully wired into `detect_tactic_motif` and surfaced via existing
dispatch infrastructure.

## Threat Flags

None. Pure algorithm change to existing tactic detector logic; no new network endpoints,
auth paths, or schema changes.

## Self-Check

### Created/modified files exist:
- `app/services/tactic_detector.py` — FOUND (modified)
- `tests/services/test_tactic_detector.py` — FOUND (modified)
- `tests/scripts/tagger/precision_floors.py` — FOUND (modified)
- `reports/tactic-tagger/tactic-tagger-2026-06-22.md` — FOUND (modified)
- `CHANGELOG.md` — FOUND (modified)

### Commits exist:
- 0712440a: feat(132-02): rewrite detect_deflection + detect_clearance to cook AND-chains — FOUND
- ea2ae95f: feat(132-02): ship deflection + clearance with new cook-aligned floors — FOUND
- 5528b33a: chore(132-02): update CHANGELOG for deflection + clearance ship — FOUND

### Full test suite:
- `uv run pytest -n auto -q`: 2856 passed, 16 skipped
- `uv run ruff format app/ tests/ && uv run ruff check app/ tests/ --fix`: All checks passed
- `uv run ty check app/ tests/`: All checks passed
- Frontend lint + tests: 0 errors, 1088 tests passed

## Self-Check: PASSED
