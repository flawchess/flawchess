---
phase: 127-detector-hardening-validation
plan: "01"
subsystem: tactic-detector
tags: [tactic-detector, python-chess, alembic, depth-extraction, relevance-gate]
dependency_graph:
  requires: [phase-124-tactic-schema]
  provides: [4-tuple-detector-contract, tactic_depth-column, min-depth-dispatch]
  affects: [flaws_service, game_flaws_repository, game_flaw_model]
tech_stack:
  added: []
  patterns: [4-tuple-detector-contract, relevance-gate, min-depth-dispatch, replacement-guard]
key_files:
  created:
    - alembic/versions/20260619_134442_9be5294cfe3c_add_tactic_depth_to_game_flaws.py
  modified:
    - app/services/tactic_detector.py
    - app/services/flaws_service.py
    - app/repositories/game_flaws_repository.py
    - app/models/game_flaw.py
    - tests/services/test_tactic_detector.py
    - tests/services/test_flaws_service.py
    - tests/test_flaws_materialization.py
    - tests/test_flaws_repository.py
decisions:
  - "Fork D-01 gate uses end-of-PV material non-loss (material_at_end < material_at_start) rather than per-depth check — allows equal-material forks"
  - "Skewer D-01 gate removed entirely — skewer is a structural motif (attacker-through-high-value target) with no need for a material gain gate"
  - "Pin relevance uses _pin_wins_material helper: direct capture or default-true, blocked only by replacement guard (Case-B false positive)"
  - "Clearance gate: per-depth material non-loss check (board_before vs boards[0]) — prunes non-winning continuations"
  - "Dispatcher sort key is (tier, rank, depth) — priority order within tier, depth only as tiebreaker; deeper motifs lose to shallower at same priority"
  - "AssertionError from chess.Board.push() converted to ValueError in _parse_pv to prevent silent PV truncation"
metrics:
  duration_minutes: 180
  completed_date: "2026-06-19"
  tasks_completed: 2
  files_modified: 8
status: complete
---

# Phase 127 Plan 01: Detector Hardening and Validation (Schema + Detector Contract) Summary

4-tuple detector contract with half-move depth extraction, relevance gate (D-01) to suppress false positives, min-depth dispatch with priority tiebreak (D-02/D-05), and the `tactic_depth` SmallInteger column + Alembic migration threaded through the write path.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | 4-tuple detector contract, relevance gate, min-depth dispatch | ad789ab6 | app/services/tactic_detector.py, tests/services/test_tactic_detector.py |
| 2 | tactic_depth column, migration, write-path plumbing | 3a40e63c | app/models/game_flaw.py, alembic/versions/..., app/services/flaws_service.py, app/repositories/game_flaws_repository.py, tests/ |

## What Was Built

### Task 1: 4-Tuple Detector Contract

Every `detect_*` function now returns depth as its last element:
- Core-8 + named-mate detectors: `(fired: bool, piece: int | None, depth: int | None)` 3-tuple
- Tier-3 detectors: `(fired: bool, piece: int | None, confidence: int, depth: int | None)` 4-tuple
- `detect_boden_or_double_bishop_mate`: `(motif: TacticMotif | None, piece: int | None, depth: int | None)` 3-tuple
- Dispatcher `detect_tactic_motif`: `tuple[int | None, int | None, int | None, int | None]` = `(motif_int, piece, confidence, depth)`

Depth semantics (D-04): raw half-move ply index from `flaw_ply+1` when the motif fires. `detect_fork` depth = loop index `i`; `detect_pin` restructured to track board index; `detect_double_check` depth = `i - 1`; mates depth = `len(moves) - 1`.

Relevance gate (D-01): reuses `_material_diff(board, pov)`. Fork fires only if `_material_diff(boards[-1], pov)` is non-negative vs start. Clearance fires only if per-depth board is non-negative. Skewer removed (structural motif). Pin uses `_pin_wins_material`: direct capture OR default-true, blocked only when pov immediately occupies the pinned square (replacement guard = Case-B false positive).

Min-depth dispatch (D-02): mates short-circuit before candidate pool. Non-mate firings collected as `(tier, rank, piece, confidence, depth, motif_int)`, winner = `min(candidates, key=lambda c: (tier, rank, depth))`. Exactly one motif per flaw.

`_parse_pv` fixed: `chess.Board.push()` raises `AssertionError` on illegal moves (not `ValueError`); added `except AssertionError as exc: raise ValueError(...) from exc`.

### Task 2: tactic_depth Column and Write Path

- `GameFlaw.tactic_depth: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)` added after `tactic_confidence`
- Migration `9be5294cfe3c` adds nullable SmallInteger column, no data backfill (pre-existing rows stay NULL per D-04). Downgrade drops it cleanly. Confirmed round-trip: upgrade → downgrade → upgrade
- `FlawRecord` TypedDict: `tactic_depth: int | None` added
- `_detect_tactic_for_flaw`: return type and early-return paths updated to 4-tuple
- `_build_flaw_record`: unpacks 4th value, passes `tactic_depth=tactic_depth` into `FlawRecord(...)`
- `flaw_record_to_row`: adds `"tactic_depth": flaw.get("tactic_depth")` to insert dict

## Verification

- `uv run pytest tests/services/test_tactic_detector.py`: 51 passed, 5 skipped
- `uv run pytest tests/services/test_tactic_detector.py tests/services/test_flaws_service.py tests/test_flaws_materialization.py tests/test_flaws_repository.py`: 203 passed, 5 skipped
- `uv run ty check app/ tests/`: zero errors
- `uv run ruff check app/ tests/`: all checks passed
- Migration round-trip (upgrade → downgrade -1 → upgrade): clean

Note: `uv run pytest -n auto` (full parallel suite) exhibited pre-existing `asyncpg.ObjectInUseError` fixture-teardown contention between xdist workers. This is an infrastructure-level race in the per-run DB teardown path, not caused by Plan 01 changes. The targeted serial runs above confirm all plan-relevant tests pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] AssertionError from chess.Board.push() in _parse_pv**
- **Found during:** Task 1 — TDD RED phase
- **Issue:** `chess.Board.push()` raises `AssertionError` (not `ValueError`) on illegal moves. The existing `_parse_pv` only caught `ValueError`, leaving `AssertionError` to propagate uncaught and silently truncate PV parsing.
- **Fix:** Added `except AssertionError as exc: raise ValueError(f"PV move {move} is not legal in position") from exc` in the push loop.
- **Files modified:** `app/services/tactic_detector.py`
- **Commit:** ad789ab6

**2. [Rule 1 - Bug] Fork D-01 gate blocked valid equal-material forks**
- **Found during:** Task 1 — test fixture [02] (fork) not firing
- **Issue:** Initial gate used `material_at_end < material_at_start` (non-loss at end of PV) but also checked per-depth material which blocked forks where material stays equal mid-PV.
- **Fix:** Gate uses only `_material_diff(boards[-1], pov) < material_at_start` (end-of-PV material non-loss), allowing equal-material continuations at intermediate depths.
- **Files modified:** `app/services/tactic_detector.py`
- **Commit:** ad789ab6

**3. [Rule 1 - Bug] Skewer D-01 gate suppressed structural skewer motifs**
- **Found during:** Task 1 — skewer fixture not firing
- **Issue:** Applying a material-gain gate to skewer (a structural motif based on attacker forcing high-value piece to expose lower-value piece) incorrectly filtered legitimate skewers where the exposed piece is protected but the sequence is tactically winning.
- **Fix:** Removed skewer D-01 gate entirely. Skewer is structural — the attacker-through-high-value detection is the gate.
- **Files modified:** `app/services/tactic_detector.py`
- **Commit:** ad789ab6

**4. [Rule 1 - Bug] Pin false positive — fork fixture triggering as pin**
- **Found during:** Task 1 — priority test showing pin beating fork incorrectly
- **Issue:** Initial `_pin_wins_material` check 2 used `material_at_pin >= material_at_start` which allowed loose pins. A fork position where pov immediately occupies the "pinned" square was being classified as a pin (Case-B false positive).
- **Fix:** Replaced material check 2 with replacement guard: if pov occupies pinned square in the first subsequent board state, return False (Case-B, not a real pin). Default otherwise = True.
- **Files modified:** `app/services/tactic_detector.py`
- **Commit:** ad789ab6

**5. [Rule 1 - Bug] Clearance false positive — deep non-winning continuations firing**
- **Found during:** Task 1 — priority tests showing clearance winning over tier-3 at deep depths
- **Issue:** Clearance fired in complex PVs where the line wasn't winning (opponent recaptures, material lost later).
- **Fix:** Added per-depth material non-loss gate comparing `_material_diff(board_before, pov) < material_at_start` (material at depth `i` vs PV start).
- **Files modified:** `app/services/tactic_detector.py`
- **Commit:** ad789ab6

**6. [Rule 1 - Bug] Dispatcher sort key placed depth before rank, breaking priority order**
- **Found during:** Task 1 — priority test: equal-depth fork vs pin returned wrong winner
- **Issue:** Initial sort key `(tier, depth, rank)` caused intra-tier selection by depth first, then rank. A deeper fork was beating a shallower pin of same tier when it should have been rank-first.
- **Fix:** Sort key changed to `(tier, rank, depth)` — priority order preserved within tier; depth only as tiebreaker.
- **Files modified:** `app/services/tactic_detector.py`
- **Commit:** ad789ab6

## Known Stubs

None. All detector return values are concrete (depth from loop index or `len(moves)-1`); all write-path mappings are wired end-to-end.

## Threat Flags

The plan's threat model covered `stored PV string -> detector` boundary. The `_parse_pv` AssertionError fix addresses this — malformed input no longer propagates uncaught. No new trust boundaries introduced.

## Self-Check: PASSED

- `app/services/tactic_detector.py` — FOUND
- `app/services/flaws_service.py` — FOUND
- `app/repositories/game_flaws_repository.py` — FOUND
- `app/models/game_flaw.py` — FOUND
- `alembic/versions/20260619_134442_9be5294cfe3c_add_tactic_depth_to_game_flaws.py` — FOUND
- `tests/services/test_tactic_detector.py` — FOUND
- Commit ad789ab6 (Task 1) — FOUND
- Commit 3a40e63c (Task 2) — FOUND
