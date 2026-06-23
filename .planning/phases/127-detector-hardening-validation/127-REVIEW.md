---
phase: 127-detector-hardening-validation
reviewed: 2026-06-19T16:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - app/services/tactic_detector.py
  - app/services/flaws_service.py
  - app/repositories/game_flaws_repository.py
  - app/models/game_flaw.py
  - alembic/versions/20260619_134442_9be5294cfe3c_add_tactic_depth_to_game_flaws.py
  - scripts/select_tagger_fixtures.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 127: Code Review Report

**Reviewed:** 2026-06-19T16:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

This review covers the phase-127 detector hardening changes: the 4-tuple contract (added `depth`), the relevance/forcing gates for `detect_fork`, `detect_pin`, `detect_discovered_attack`, and `detect_clearance`, the min-depth priority dispatcher rewrite, the `tactic_depth` column (model, migration, repository, service), and the `select_tagger_fixtures.py` script.

Overall the implementation is structurally sound. The tuple-arity contract is consistent across all 24 detectors. The dispatcher `Candidate` tuple indexing and sort key are correct. The migration `down_revision` chain is accurate. The `tactic_depth` column plumbing is consistent across model, migration, repository, and service layers.

Two issues need attention: a parity bug in `_pin_wins_material` Check 1 that causes it to scan opponent moves instead of pov moves when the pin is found at an even board index (the majority case), and a silent swallow of `chess.IllegalMoveError` without Sentry capture in `_detect_tactic_for_flaw`.

---

## Warnings

### WR-01: `_pin_wins_material` Check 1 iterates opponent moves, not pov moves, for even-k pins

**File:** `app/services/tactic_detector.py:367`

**Issue:** The relevance gate loop `for j in range(pin_board_idx + 1, len(moves), 2):` is intended to find later pov moves that directly capture the pinned piece. However, pov's moves are at **even** move indices (0, 2, 4...) because pov has the first move in the PV. When `pin_board_idx` is even (board 0, 2, 4 — the most common case, including the starting position), `pin_board_idx + 1` is odd, so the loop iterates **opponent** moves (1, 3, 5...). The check `moves[j].to_square == pinned_sq` against opponent moves almost never fires (the opponent would not capture their own pinned piece). Only when `pin_board_idx` is odd does the loop correctly iterate pov moves.

Practical consequence: Check 1 is a no-op for pins found at even board indices, meaning more pins fall through to the default `return True` path. This makes the relevance gate less effective for even-k pins (more permissive than designed), slightly worsening pin false-positive suppression. It does not affect recall.

**Fix:**

```python
def _pin_wins_material(
    boards: list[chess.Board],
    moves: list[chess.Move],
    pov: chess.Color,
    pin_board_idx: int,
    pinned_sq: int,
) -> bool:
    # Check 1: pov directly captures the pinned piece in a later pov move.
    # Pov's moves are at even move indices. The first pov move index >= pin_board_idx
    # is pin_board_idx if it is even (pov's turn at that board), else pin_board_idx + 1.
    first_pov_move = pin_board_idx if pin_board_idx % 2 == 0 else pin_board_idx + 1
    for j in range(first_pov_move, len(moves), 2):
        if moves[j].to_square == pinned_sq:
            return True  # direct capture of the pinned piece

    # Check 2: replacement guard (unchanged) ...
```

Note: since `detect_pin` passes `k` (board index) as `pin_board_idx`, at even k the intended "later pov moves" are at move indices k, k+2, ... whereas the bug iterates k+1, k+3, .... For k=0 (pin at starting position), Check 1 should search move indices 0, 2, 4... but instead searches 1, 3, 5...

---

### WR-02: `_detect_tactic_for_flaw` swallows `chess.IllegalMoveError` without Sentry capture

**File:** `app/services/flaws_service.py:406`

**Issue:** The except block silently discards `chess.IllegalMoveError` without calling `sentry_sdk.capture_exception()`. By the time this code runs, `fen_before_flaw`, `pv`, and `move_san_of_flaw` are all confirmed non-empty (line 393 guard). A non-empty `move_san_of_flaw` that fails `board.parse_san()` on a board reconstructed from stored FEN represents a genuine data inconsistency (the SAN was valid at import time, so a parse failure here implies FEN/SAN drift), not expected user-input noise. CLAUDE.md requires `sentry_sdk.capture_exception()` in every non-trivial `except` block in `app/services/`.

The sibling code at line 309–315 in the same file demonstrates the correct pattern: the FEN-recompute `except` block explicitly captures the exception with `sentry_sdk.set_context(...)` + `sentry_sdk.capture_exception(exc)` precisely because "this PGN already parsed cleanly at import time" and a failure here is a data inconsistency.

**Fix:**

```python
    except (ValueError, chess.IllegalMoveError) as exc:
        # Malformed move_san or FEN — leave all four as None (Pitfall 6).
        # ValueError from parse_san on user-provided SAN is expected.
        # IllegalMoveError when fen_before_flaw/move_san_of_flaw are both non-empty
        # indicates stored data inconsistency — capture it for investigation.
        if isinstance(exc, chess.IllegalMoveError):
            sentry_sdk.set_context(
                "tactic_detect",
                {"ply": n, "move_san": move_san_of_flaw, "fen": fen_before_flaw},
            )
            sentry_sdk.capture_exception(exc)
        return None, None, None, None
```

---

## Info

### IN-01: `detect_pin` returns a board index as `depth`, while all other detectors return a move index

**File:** `app/services/tactic_detector.py:422`

**Issue:** `detect_pin` returns `True, pinner.piece_type, k` where `k` is from `enumerate(boards)` — a board index (0..N). All other detectors return a **move index** as depth:

- `detect_fork`: `i` from `range(0, len(moves), 2)` (move index).
- `detect_skewer`: `i` from `range(1, len(moves))` (move index).
- `detect_double_check`: `i - 1` (board index minus 1 = move index).
- `detect_discovered_attack`: `0` or `k` from `range(2, len(moves), 2)` (move index).
- Tier-3 detectors: `k` from `range(2, len(moves), 2)` (move index).
- Mate detectors: `len(moves) - 1` (move index).

The model comment and D-04 spec say "raw half-move ply index from flaw_ply+1." Board index `k=0` is before any PV move (the flaw_ply+1 position), so `k` and move index differ by 0 only for k=0. For `k=2` (pin found after opponent's first response), depth is stored as 2, but the move that delivered the pin was move index 0 (pov's first move). This inconsistency will cause depth comparisons and the depth-vs-Rating correlation (D-06) to be slightly off for the pin motif.

The dispatcher sort key uses depth only as a tiebreaker within the same tier+rank, and since each detector occupies a unique rank, this does not affect winner selection. But the stored `tactic_depth` value for pins is semantically different from all other motifs.

**Fix:** Subtract 1 from the returned depth to align with move index semantics, or document the special semantics clearly. The simplest fix: return `max(k - 1, 0)` since board index 0 (pin at starting position) should map to move depth 0 (flaw move is move 0 in context):

```python
# In detect_pin, change:
return True, pinner.piece_type, k
# To (board index k → move index; starting position pin fires at depth 0):
return True, pinner.piece_type, max(k - 1, 0) if k > 0 else 0
```

Actually the cleanest fix is to unify on board-index semantics everywhere, but that requires touching all detectors. The alternative is to document that pin depth is a board index in the `detect_pin` docstring (already partially done: "depth = board index k where the pin is found") but also note the inconsistency with other detectors.

---

### IN-02: Dead-code `if k < 2: continue` inside `range(2, ...)` loops in three detectors

**File:** `app/services/tactic_detector.py:975, 1054, 1103`

**Issue:** Three tier-3 detectors (`detect_intermezzo`, `detect_interference`, `detect_self_interference`) contain a redundant guard `if k < 2: continue` inside a loop that starts at `k=2` (`range(2, len(moves), 2)`). Since `k` starts at 2, `k < 2` is never True. This is dead code that survived from a prior refactor where the loop previously started at a smaller index.

These are pre-existing (not introduced in phase 127), but they appear in the diff context and reduce code clarity.

**Fix:** Remove the dead guard lines (975, 1054, 1103):

```python
# Remove these three lines (one per detector):
if k < 2:
    continue
```

---

_Reviewed: 2026-06-19T16:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
