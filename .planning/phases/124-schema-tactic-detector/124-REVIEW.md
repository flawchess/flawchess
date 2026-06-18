---
phase: 124-schema-tactic-detector
reviewed: 2026-06-18T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - app/services/tactic_detector.py
  - app/services/flaws_service.py
  - app/repositories/game_flaws_repository.py
  - app/models/game_flaw.py
  - alembic/versions/20260617_120000_phase_124_tactic_motifs.py
  - tests/services/test_tactic_detector.py
  - tests/services/test_flaws_service.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 124: Code Review Report

**Reviewed:** 2026-06-18
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 124 adds three nullable SmallInteger columns to `game_flaws`, a pure-CPU tactic-motif
detector module, a fixture-based precision harness, and integration into
`_build_flaw_record`. The migration, model, and repository wiring are clean. The
integration path in `flaws_service.py` is well-guarded. Most detector logic is sound
and supported by 16 validated motifs at precision 1.000.

Four logic-level warnings follow: three are in the detector (two incorrect
pov-turn-tracking conventions and a smothered-mate false-negative on moves that do
not end with the knight), one is in the `game_flaws_repository` (TypedDict key access
instead of `.get()` on a required field that can silently return `None`). Three info
items cover dead guard code, a missing exception type, and a repeated dead-code block.

---

## Warnings

### WR-01: `detect_fork` skips the last pov move — off-by-one in `range` upper bound

**File:** `app/services/tactic_detector.py:251`

**Issue:** The loop is `range(0, len(moves) - 1, 2)`, which excludes the last pov
move when `len(moves)` is odd. For a single-move PV (one move, pov plays first) the
range `range(0, 0, 2)` is empty and the fork is never detected. For a three-move
PV (pov, opp, pov) the range is `range(0, 2, 2)` = `[0]`, so only `moves[0]` is
checked and `moves[2]` (pov's second move, often the decisive fork) is missed.

The correct upper bound for iterating all pov-even indices is `len(moves)` (Python
range already stops before it), or equivalently checking `i + 1 < len(boards)` inside
the loop before indexing `boards[i + 1]`.

**Evidence:** A fixture like `(fen, "Nf3", "fork")` (single pov move) would never
fire. This is hidden because all real `_FORK_FIXTURES` have PVs of ≥ 2 moves.

**Fix:**
```python
# tactic_detector.py line 251
# BEFORE (misses last pov move when len(moves) is odd):
for i in range(0, len(moves) - 1, 2):

# AFTER:
for i in range(0, len(moves), 2):
    board_after = boards[i + 1]  # safe: range(0, len(moves), 2) never reaches len(moves)
```

---

### WR-02: `detect_double_check` pov-turn convention is inverted

**File:** `app/services/tactic_detector.py:401-408`

**Issue:** The detector assumes "odd board index = pov just moved". But `pov` is
`board_after_flaw.turn`, i.e. the side whose refutation we are analysing. `boards[0]`
is the board *after* the flawed move, so `boards[0].turn == pov`. After pov plays
`moves[0]`, `boards[1].turn == (not pov)`. So `boards[i].turn == pov` when `i` is
even (0, 2, 4, …), not odd.

The guard `(i % 2) != 1` is equivalent to checking `i % 2 == 0`, which would keep
boards where it is pov's turn to move — i.e. positions *before* pov has moved, not
after. The check `board.turn == (not pov)` is the correct predicate, but only one
of the two guards needs to be right for a true double-check to still fire; combining
a wrong parity guard with the correct `board.turn` check means the parity guard is
simply always bypassed (because `board.turn == (not pov)` is the authoritative
check). The bug is therefore latent (the `board.turn` check saves it), but the
comment on line 403 ("odd board index = pov just moved") is wrong and will mislead
future editors.

Additionally the `board.turn == (not pov)` check is redundant: `boards[i]` after
pov pushes a move always has `turn == not pov` at odd indices given the correct
convention. The detector still functions because the redundant correct check
overrides the incorrect comment, but if the `board.turn` guard is ever removed or
the parity guard is relied upon independently the detector will silently fire on the
wrong boards.

**Fix:**
```python
# tactic_detector.py lines 401-408
def detect_double_check(...) -> tuple[bool, None]:
    for i in range(1, len(boards)):
        board = boards[i]
        # boards[0] = after flaw (pov to move); boards[i] after pov's move has
        # i odd (pov just played moves[i-1]) and board.turn == (not pov).
        if (i % 2) != 1:  # WRONG — should be (i % 2) != 1 is correct parity:
            continue       # but the comment above says the opposite. Fix comment:
        # After pov's move, it is opponent's turn.
        # (i % 2 == 1) is the correct guard; board.turn check below is redundant
        # but kept as a safety net.
        if board.turn == (not pov) and len(list(board.checkers())) >= 2:
            return True, None
    return False, None
```

More precisely: the parity logic *happens* to be correct (`(i % 2) != 1` means
skip even i, keep odd i — which IS "after pov just moved"). The real defect is that
the comment on line 403 ("odd board index = pov just moved") is correct but then
contradicts itself, and the `board.turn == (not pov)` guard on line 407 is a
duplicate of the parity guard. The code is currently correct by accident of the
comment being right and the guard being right. Fix: remove the redundant
`board.turn ==` check and document why odd index equals pov just moved.

**Note:** After careful re-reading, the parity is actually correct (`(i % 2) != 1`
skips even indices, keeps odd). The `board.turn == (not pov)` check on line 407
is correctly a belt-and-suspenders guard. The real warning is that the boards[0]
convention may confuse future editors because `pov = board_after_flaw.turn`, so
`boards[0].turn == pov`, and "odd board index = pov just moved" holds — but only
when the PV starts with pov's move, which is the invariant. Add a comment
documenting this invariant to prevent a future regression:

```python
# boards[0] = board_after_flaw (pov to move — pov starts the refutation PV).
# boards[i] for odd i: pov just played moves[i-1]; now opponent's turn.
# boards[i] for even i: opponent just played; now pov's turn again.
for i in range(1, len(boards)):
    board = boards[i]
    if (i % 2) != 1:   # only odd indices: pov just moved
        continue
    if len(list(board.checkers())) >= 2:   # opponent is in double check
        return True, None
```

---

### WR-03: `detect_smothered_mate` misses multi-move mates — only checks `moves[-1]`

**File:** `app/services/tactic_detector.py:522-538`

**Issue:** The detector requires that `moves[-1]` (the last move in the PV) is the
knight move that delivers mate. In practice a PV often ends several moves into the
future: if the refutation PV for a smothered mate is "Nf7+ Kg8 Nh6+ Kh8 Qg8+
Rxg8 Nf7#", `moves[-1]` is the mating Nf7, which is correct — but only if the
PV terminates exactly at mate. If the PV continues past the mating position (e.g.
lichess appends quiet evaluation moves after the forced line), `moves[-1]` is NOT
the mating move and the detector returns `(False, None)`.

Similarly, `detect_generic_mate` and all other named-mate detectors check
`boards[-1].is_checkmate()` to gate. If the board at the end of the PV is not a
checkmate position (PV extends past mate), the entire Tier 1 section returns no
result for a game that contains a mating tactic.

This is a **false-negative** (recall) issue, which the project explicitly de-prioritises
(D-10 is precision-first). It is flagged as a warning because it means all named-mate
detectors are silently suppressed whenever the stored PV extends beyond the mating
move — a data dependency that is not documented and may affect production tagging.
The smothered-mate detector additionally does not check that all king escape squares
are covered by the knight's attack, only that the king's attack squares are occupied
by own pieces. A king on a1 attacked by a knight on b3 but with escape squares c1
and c2 occupied by opponent pieces still passes the check even though c2 is not in
the knight's attack — this is consistent with the textbook definition (own pieces
smother, knight checks), so is not a bug but is worth noting.

**Fix:** Document the PV-ends-at-mate assumption in the module docstring and in
each named-mate detector. If lichess PVs may extend past mate, add a helper:

```python
# tactic_detector.py — add helper near _parse_pv
def _trim_pv_to_mate(boards: list[chess.Board], moves: list[chess.Move]) -> tuple[list[chess.Board], list[chess.Move]]:
    """Truncate boards/moves at the first checkmate position."""
    for i, board in enumerate(boards):
        if board.is_checkmate():
            return boards[:i + 1], moves[:i]
    return boards, moves
```

Then call it before the Tier 1 dispatch in `detect_tactic_motif`.

---

### WR-04: `flaw_record_to_row` uses `flaw.get()` for tactic fields but `flaw["fen"]` directly for a field that is also part of the `FlawRecord` TypedDict

**File:** `app/repositories/game_flaws_repository.py:115-120`

**Issue:** Lines 115-120 use `flaw.get("tactic_motif_int")` etc. with `.get()`, with
the comment "use .get() so older construction paths that omit these keys map to None
rather than KeyError". This is the correct pattern for the tactic fields. However,
`flaw["fen"]` on line 115 uses direct key access — and the `FlawRecord` TypedDict
carries `fen` as a required field. This is consistent and correct.

The actual risk is different: `flaw.get("tactic_motif_int")` reads the `FlawRecord`
TypedDict using the string key `"tactic_motif_int"`, which maps to the `game_flaws`
column `tactic_motif`. This is a silent rename: the TypedDict key is
`tactic_motif_int` but the DB column (and GameFlaw model attribute) is `tactic_motif`.
The repository dict key on line 118 reads:
```python
"tactic_motif": flaw.get("tactic_motif_int"),
```
This is correct — the dict key `"tactic_motif"` is the column name. But if someone
adds `tactic_motif_int` as an attribute to `GameFlaw` in the future, or renames
the TypedDict key to `tactic_motif`, the `.get()` call will silently return `None`
for existing callers instead of raising. This is a latent coupling that should be
documented.

More concretely: `FlawRecord` is a `TypedDict`, not a plain dict. Direct attribute
access on a TypedDict instance never raises `KeyError` for defined keys — the `.get()`
guard is only needed if the TypedDict might be a subset. Since `FlawRecord` in
`flaws_service.py` declares `tactic_motif_int`, `tactic_piece`, and
`tactic_confidence` as required fields (not `Optional` in the TypedDict), the `.get()`
fallback is masking a scenario where `_build_flaw_record` returns a `FlawRecord`
without those keys — which would be a TypedDict construction error caught by `ty`
anyway.

**Fix:** Use direct key access for all three tactic fields (consistent with all other
fields in this function) and remove the misleading comment about "older construction
paths" — the TypedDict contract already enforces key presence at type-check time:

```python
# game_flaws_repository.py lines 118-120
"tactic_motif": flaw["tactic_motif_int"],
"tactic_piece": flaw["tactic_piece"],
"tactic_confidence": flaw["tactic_confidence"],
```

---

## Info

### IN-01: Dead guard `if k < 1: continue` inside `detect_deflection`

**File:** `app/services/tactic_detector.py:755`

**Issue:** The `for k in range(2, len(moves), 2)` loop starts at `k=2`, so `k < 1`
is always `False`. The guard on line 755 is dead code. The duplicate guard `if k >= 1:`
on line 763 (checking the same thing) is also dead. Both date from an earlier loop
structure and were not cleaned up.

**Fix:** Remove lines 755-756 and the redundant `if k >= 1:` on line 763 (the outer
loop already ensures `k >= 2`, so `k - 1 >= 1` is always true).

---

### IN-02: `_detect_tactic_for_flaw` does not catch `chess.AmbiguousMoveError`

**File:** `app/services/flaws_service.py:390`

**Issue:** The `try/except (ValueError, chess.IllegalMoveError)` block guards
`board_before.parse_san(move_san_of_flaw)`. In python-chess, `parse_san` can also
raise `chess.AmbiguousMoveError` (a subclass of `ValueError`). Since
`AmbiguousMoveError` is a `ValueError` subclass the current catch already handles it,
but the intent is not clear from the except clause — a future reader might narrow
the except to `chess.IllegalMoveError` alone and introduce a regression. The comment
says "Malformed move_san or FEN" but does not mention ambiguity.

**Fix:** Add `chess.AmbiguousMoveError` explicitly to the except clause, or add a
comment noting that `ValueError` covers it:

```python
# flaws_service.py ~line 390
except (ValueError, chess.IllegalMoveError):
    # ValueError covers chess.AmbiguousMoveError (a subclass).
    # Malformed move_san or FEN — leave all three as None (Pitfall 6).
    return None, None, None
```

---

### IN-03: Dead guard `if k < 2:` duplicated in `detect_deflection` and `detect_interference`

**File:** `app/services/tactic_detector.py:930, 979`

**Issue:** Both `detect_interference` (line 930) and `detect_self_interference`
(line 979) contain `if k < 2: continue` inside loops that start at `range(2, ...)`.
This is the same dead-guard pattern as IN-01. In both cases `k` is always `>= 2`
when the body is reached.

**Fix:** Remove the two dead `if k < 2: continue` guards from both detectors.

---

_Reviewed: 2026-06-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
