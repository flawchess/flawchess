# Phase 124: Schema + Tactic Detector - Research

**Researched:** 2026-06-17
**Domain:** Chess tactic motif detection (python-chess heuristics), SQLAlchemy ORM schema extension, Alembic migration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01: Three-column migration**
Adds `tactic_motif` (SmallInteger enum), `tactic_piece` (SmallInteger, PieceType 1-6), and `tactic_confidence` (SmallInteger 0-100) — all nullable — to `game_flaws`. Existing rows carry NULL.

**D-02: Single-enum encoding**
`tactic_motif` = one IntEnum per flaw (not bitmask, not join table). Follow `EndgameClassInt` precedent: `IntEnum` subclass + `_INT_TO_MOTIF` / `_MOTIF_TO_INT` dicts + `Literal[...]` type alias.

**D-03: Fine-grained named-mate subtypes**
Store specific mate: `smothered-mate`, `anastasia-mate`, `hook-mate`, `arabian-mate`, `boden-mate`, `double-bishop-mate`, `dovetail-mate`, `back-rank-mate`, generic `mate`. Coarsening is free at query time (`WHERE tactic_motif IN (MATE_MOTIFS)`).

**D-04: Full motif set in Phase 124**
Implements AND validates ALL motifs: Core 8 (`fork`, `hanging-piece`, `pin`, `skewer`, `double-check`, `discovered-attack`, `back-rank-mate`, generic `mate`) + tier-3 8 (`deflection`, `intermezzo`, `x-ray`, `interference`, `self-interference`, `clearance`, `attraction`, `capturing-defender`, `sacrifice`) + named-mate subtypes.

**D-05: Severity gate = mistakes + blunders**
Tunable constant, not a hardcoded literal.

**D-06: Excluded motifs**
`overloading` (stub in cook — unavailable), move-type descriptors, positional tags, puzzle metadata, endgame-type tags.

**D-07: Priority order (tiebreak)**
1. Mates: named subtype > `back-rank-mate` > generic `mate` (always dominates)
2. Geometric: `fork` > `skewer` > `pin` > `discovered-attack` > `double-check`
3. Tier-3: `deflection` > `attraction` > `intermezzo` > `x-ray` > `interference` / `self-interference` > `clearance` > `capturing-defender` > `sacrifice`
4. `hanging-piece` (always last, catch-all)

**D-08: Intra-tier order is provisional**
Can be tuned after real co-occurrence data is sampled.

**D-09: Hand-labeled fixture set from own prod flaws**
10-15 positives per motif from `game_flaws` + `game_positions.pv`. NOT from cook.py output. Plus a shared hard-negative set.

**D-10: Tiered precision bar (precision-first; recall NOT gated)**
Core 8: ≥90% precision. Tier-3 + named-mate: ≥95%. A motif that misses its bar is query-suppressed (stored but never surfaced).

**D-11: Always write, suppress at query time**
When any detector fires: store `tactic_motif` + `tactic_confidence`. `tactic_motif = NULL` means no detector fired. Low-confidence suppression is `AND tactic_confidence >= :t` at query time.

**D-12: tactic_piece semantics**
- `fork` → forking piece (highest-value attacker)
- `hanging-piece` → victim (hung piece)
- `pin` / `skewer` → line piece (B/R/Q only)
- all mates → mating piece
- `discovered-attack` → unveiled attacking piece
- `sacrifice` → sacrificed piece
- `capturing-defender` → captured defender
- `deflection` / `attraction` → target piece (deflected/attracted)
- NULL: `double-check`, `x-ray`, `interference`/`self-interference`, `clearance`, `intermezzo`, and ambiguous cases

### Claude's Discretion
- Detector module layout
- PV-parsing helper that builds `(board, line, pov)`
- Fixture file format and location
- Exact int values assigned to each motif in the enum
- Precise graded scoring function per tier-3 motif (constrained by D-10 bar)

### Deferred Ideas (OUT OF SCOPE)
- Piece-level you-vs-opponent UI (TACPIECE-01)
- Surfacing named-mate subtypes in v1 (stored-but-unsurfaced)
- True standalone `missed-X` detection (TACMISS-01)
- Backfill over prod (Phase 125)
- `/api/library/tactic-comparison` endpoint (Phase 126)
- Motif chips and MiniBulletChart grid (Phase 126)

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TACSCH-01 | `game_flaws` gains nullable `tactic_motif` SmallInteger enum column | §Schema/migration mechanics, §IntEnum precedent |
| TACSCH-02 | `game_flaws` gains nullable `tactic_piece` SmallInteger column (PieceType 1-6) | §Schema/migration mechanics, §tactic_piece semantics |
| TACDET-01 | Detector names motif from `game_positions.pv` at `flaw_ply+1`, reimplementing cook heuristics in original code | §Cook heuristics algorithms, §PV data shape and parsing |
| TACDET-02 | At most one motif per flaw via fixed priority order tiebreak | §Priority order implementation, §detector module layout |
| TACDET-03 | Precision-first: NULL when confidence low; hand-labeled fixtures pass accuracy bar | §Fixture validation approach, §Confidence scoring |
| TACDET-04 | Runs inside `classify_game_flaws` (both colors) and `backfill_flaws.py`, no new Stockfish call | §Integration point in flaws_service.py, §backfill confirmation |

</phase_requirements>

---

## Summary

Phase 124 is a pure-Python detector phase. The data foundation is complete: `game_positions.pv` stores a space-joined UCI refutation line (up to 12 plies) at `flaw_ply+1` for both colors' flaws, and `game_flaws` already materializes both sides' mistakes and blunders. The detector's job is to read that stored PV, reconstruct the board sequence, apply cook-style boolean heuristics, apply the D-07 priority tiebreak, and write three nullable columns.

The schema work is mechanical: three `nullable SmallInteger` column additions mirroring the `tempo` column precedent, encoded via an `IntEnum` following the `EndgameClassInt` pattern from `endgame_service.py:108`. The `flaw_record_to_row` mapping in `game_flaws_repository.py` must be extended to emit the three new fields.

The implementation challenge is the tier-3 detectors. Cook's tier-3 heuristics (`deflection`, `attraction`, `intermezzo`, `x-ray`, `interference`, `clearance`, `capturing-defender`, `sacrifice`) all require 3-4 ply lookback across the board sequence and involve subtle position comparisons. Each must be re-implemented from the described algorithm in original code (AGPL source text not copied) and validated against hand-labeled fixtures.

**Primary recommendation:** Implement `detect_tactic_motif(board_after_flaw: chess.Board, pv: str) -> tuple[TacticMotif | None, int | None, int]` as a pure function in a new `app/services/tactic_detector.py` module. This function parses the PV, builds the board sequence, runs all detectors in priority order, returns `(motif_literal, piece_type_int, confidence)`. Wire it into `_build_flaw_record` (flaws_service.py:351) by adding the three fields to `FlawRecord` and passing `positions[n+1].pv` and the board.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Tactic motif detection | Backend service | — | Pure Python/CPU transform over stored data; no I/O, mirrors `classify_game_flaws` design |
| Schema columns | Database | Backend ORM | Three nullable SmallInteger on `game_flaws`; SQLAlchemy model + Alembic migration |
| Encoding (enum) | Backend service | — | IntEnum in service layer, plain integer in DB, Literal type for API/serialization |
| Fixture validation | Backend test | — | No-DB unit tests; chess.Board in-memory, same pattern as `test_position_classifier.py` |
| Backfill recompute | Script (backfill_flaws.py) | — | Zero new wiring — calls same `classify_game_flaws` path |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-chess | 1.11.x | Board reconstruction, attack/defender queries, piece map inspection | Project standard; all cook heuristics use its API |
| SQLAlchemy 2.x async | 2.x | ORM model extension + Alembic autogenerate | Project standard, `game_flaw.py` already uses it |
| Alembic | Current | Migration for three new columns | Project migration tool |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| chess.SquareSet | (part of python-chess) | Between-square ray detection (pin/skewer/x-ray/interference) | Tier-3 detectors that need to check if a square is between two others |
| chess.BB_ALL | (part of python-chess) | Pin detection: `board.pin(color, sq) == chess.BB_ALL` means unpinned | Pin/skewer detectors |

**Installation:** All already installed; no new packages.

---

## Package Legitimacy Audit

No new packages are installed in this phase.

---

## Architecture Patterns

### System Architecture Diagram

```
game_positions.pv (stored at flaw_ply+1, space-joined UCI)
         |
         v
detect_tactic_motif(board_after_flaw, pv_str)
   |
   +-- parse_pv(board, pv_str) -> (board_seq, move_list)
   |     [board_after_flaw + push each UCI move]
   |
   +-- run all detectors in priority order
   |     [Core 8: boolean, HIGH confidence (100)]
   |     [Tier-3: graded confidence]
   |     [Named mates: boolean, HIGH confidence (100)]
   |
   +-- apply D-07 priority order -> single winner
   |
   v
(TacticMotif | None, piece_type_int | None, confidence_int)
         |
         v
FlawRecord fields: tactic_motif, tactic_piece, tactic_confidence
         |
         v
flaw_record_to_row() -> game_flaws INSERT dict
```

### Recommended Project Structure

```
app/
├── services/
│   ├── flaws_service.py          # Integration point: _build_flaw_record + classify_game_flaws
│   └── tactic_detector.py        # NEW: detect_tactic_motif() + all detector functions
├── models/
│   └── game_flaw.py              # Add 3 nullable SmallInteger columns
├── repositories/
│   └── game_flaws_repository.py  # Extend flaw_record_to_row() to emit 3 new fields
alembic/versions/
│   └── <timestamp>_phase_124_tactic_motifs.py   # Migration: 3 ADD COLUMN
tests/
│   └── services/
│       └── test_tactic_detector.py               # NEW: fixture-based precision tests
```

### Pattern 1: IntEnum + Literal type + bidirectional dicts (copy EndgameClassInt exactly)

**What:** Define `TacticMotifInt(IntEnum)` in `tactic_detector.py`; define `TacticMotif = Literal[...]` type alias; define `_INT_TO_MOTIF: dict[int, TacticMotif]` and `_MOTIF_TO_INT: dict[TacticMotif, int]`.

**When to use:** Wherever a `tactic_motif` integer must be converted to/from a string literal for API/serialization. The repository layer uses ints; the service layer uses `TacticMotif` literals.

**Example (describe, not copy):**
```python
# Source: app/services/endgame_service.py:108
class TacticMotifInt(IntEnum):
    FORK = 1
    HANGING_PIECE = 2
    PIN = 3
    SKEWER = 4
    DOUBLE_CHECK = 5
    DISCOVERED_ATTACK = 6
    BACK_RANK_MATE = 7
    MATE = 8
    # tier-3
    DEFLECTION = 9
    ATTRACTION = 10
    INTERMEZZO = 11
    X_RAY = 12
    INTERFERENCE = 13
    SELF_INTERFERENCE = 14
    CLEARANCE = 15
    CAPTURING_DEFENDER = 16
    SACRIFICE = 17
    # named mates
    SMOTHERED_MATE = 18
    ANASTASIA_MATE = 19
    HOOK_MATE = 20
    ARABIAN_MATE = 21
    BODEN_MATE = 22
    DOUBLE_BISHOP_MATE = 23
    DOVETAIL_MATE = 24

TacticMotif = Literal[
    "fork", "hanging-piece", "pin", "skewer", "double-check", "discovered-attack",
    "back-rank-mate", "mate",
    "deflection", "attraction", "intermezzo", "x-ray", "interference",
    "self-interference", "clearance", "capturing-defender", "sacrifice",
    "smothered-mate", "anastasia-mate", "hook-mate", "arabian-mate",
    "boden-mate", "double-bishop-mate", "dovetail-mate",
]
```

**Confidence note:** Core 8 + named mates store `tactic_confidence = TACTIC_CONFIDENCE_HIGH = 100` (cook is boolean). Tier-3 store a graded value — each tier-3 detector must return an int, not just a bool. The graded value should be a stable monotone signal (e.g. number of qualifying conditions met out of possible total, scaled 0-100).

### Pattern 2: PV parsing + board sequence construction

**What:** A helper that takes `board_after_flaw: chess.Board` (position after the flawed move was played) and `pv_str: str` (space-joined UCI string from `game_positions.pv`) and returns a list of boards and a list of moves.

```python
def _parse_pv(
    board_after_flaw: chess.Board, pv_str: str
) -> tuple[list[chess.Board], list[chess.Move]]:
    """Parse space-joined UCI PV string into board sequence.

    Returns (boards, moves) where boards[0] = board_after_flaw,
    boards[i+1] = board after moves[i]. Length: len(moves) = len(boards)-1.
    """
    moves = [chess.Move.from_uci(uci) for uci in pv_str.split()]
    boards: list[chess.Board] = [board_after_flaw.copy()]
    for move in moves:
        b = boards[-1].copy()
        b.push(move)
        boards.append(b)
    return boards, moves
```

`pov = board_after_flaw.turn` — the refuting side's color (Black if White blundered, White if Black blundered).

### Pattern 3: Board reconstruction at the detect integration point

**What:** In `_build_flaw_record` (flaws_service.py:351) the caller already has `fen_map[n]` (board before flaw at ply n) and `positions[n].move_san` (the flawed move in SAN). The board after the flaw is reconstructed by:

```python
board_before = chess.Board(fen_map.get(n, ""))
flawed_move = board_before.parse_san(positions[n].move_san)
board_after_flaw = board_before.copy()
board_after_flaw.push(flawed_move)
```

Then `positions[n + 1].pv` is the stored refutation line. If `pv` is None or `board_before` can't be constructed (empty fen_map entry), the detector returns `(None, None, 0)`.

**Note:** `positions[n+1].pv` is None for lichess-eval-only flaws (those lack `full_evals_completed_at`). The detector must handle `pv is None` gracefully by returning all three as None/0.

**Critical detail on flaw_ply indexing:** `positions` list is 0-indexed by list position, where `positions[k].ply == k` for a complete game. The flaw at ply `n` has its PV at `positions[n+1]`. Confirm that `n + 1 < len(positions)` before indexing.

### Pattern 4: flaw_record_to_row extension

**What:** `flaw_record_to_row` in `game_flaws_repository.py` already maps every `FlawRecord` field to an insert dict. The three new fields follow the same pattern as `tempo`:

```python
return {
    ...existing fields...,
    "tactic_motif": flaw.get("tactic_motif_int"),   # int or None (from TacticMotifInt)
    "tactic_piece": flaw.get("tactic_piece"),         # int (chess.PieceType) or None
    "tactic_confidence": flaw.get("tactic_confidence"),  # int 0-100 or None
}
```

`FlawRecord` (TypedDict) must gain three new optional fields: `tactic_motif_int: int | None`, `tactic_piece: int | None`, `tactic_confidence: int | None`. Storing the int (not the string) avoids a dict lookup in the hot path.

### Anti-Patterns to Avoid

- **Don't copy AGPL source text from cook.py.** Describe heuristics in your own words; reimplement from algorithm description.
- **Don't call detect_tactic_motif when pv is None.** Guard at the integration point, not inside the detector.
- **Don't add `is_opponent` column.** It is derived at query time via `is_opponent_expr()`. The CONTEXT.md is explicit.
- **Don't call Stockfish from the detector.** The detector is pure CPU; positions[n+1].pv is the only data source.
- **Don't store confidence as float.** SmallInteger 0-100 (integer percent); avoids float precision issues and matches the column type.
- **Don't add a separate confidence column per motif.** D-11 explicitly rejects storing all-motif confidences — only the priority winner's confidence is stored.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Attack/defender lookup | Custom piece-attacks dict | `board.attackers(color, square)` | python-chess is optimized with bitboards |
| Pin detection | Custom ray-trace | `board.pin(color, square)` returns `BB_ALL` if unpinned; otherwise a bitboard of the pin ray | One API call |
| Between-square squares | Custom rank/file/diagonal math | `chess.SquareSet.between(sq1, sq2)` | Returns squares strictly between two squares on the same rank/file/diagonal |
| Piece value table | Custom dict | Define `_PIECE_VALUES: dict[int, int] = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}` at module top | Same values cook.py uses; named constant, not magic number |
| Finding mate | Custom checkmate check | `board.is_checkmate()` | Built-in |
| Finding checkers | Scan all squares | `board.checkers()` | Returns SquareSet of checking pieces |
| Check detection | Custom | `board.is_check()` | Built-in |
| Piece location | Iterate all squares | `board.king(color)` for king; `board.pieces(piece_type, color)` for others | O(1) or O(pieces) |

**Key insight:** All cook.py heuristics reduce to combinations of `attackers`, `attacks`, `pin`, `pieces`, `piece_at`, `king`, `checkers`, `is_check`, `is_checkmate`, `SquareSet.between`, and `square_rank`/`square_file`. No custom geometry needed.

---

## Cook Heuristic Algorithms (Plain-English Pseudocode)

This section describes the detection logic per motif. All assume the input is a board sequence (`boards`, `moves`, `pov`) where `boards[0]` is the position after the flawed move and `pov = boards[0].turn` is the refuting side.

### Utility functions to implement

**`_piece_value(piece_type: int) -> int`**
Returns: PAWN=1, KNIGHT=3, BISHOP=3, ROOK=5, QUEEN=9, KING=99. Used by hanging/fork/skewer/capturing-defender.

**`_is_hanging(board: chess.Board, sq: int, color: chess.Color) -> bool`**
A piece at `sq` of `color` is hanging if: `board.attackers(not color, sq)` is non-empty AND `board.attackers(color, sq)` is empty. Note: `not color` in python-chess is `chess.BLACK if color == chess.WHITE else chess.WHITE`. A simplified version: no defenders of the same color. The real cook version has a nuance — ray pieces defending through a capturer count as defenders — but for our precision-first approach a strict `len(attackers(color, sq)) == 0` is safer.

**`_material_diff(board: chess.Board, pov: chess.Color) -> int`**
Sum of piece values for `pov` minus sum for opponent. Excludes kings. Used by sacrifice.

### Core 8 Detectors

**`detect_fork(boards, moves, pov) -> bool`**

Scan refuter's moves (boards[0], boards[2], boards[4]... i.e. pov's turns — plies 0, 2, 4 in 0-indexed boards). For each pov-move at boards[i] → boards[i+1]: find the destination square `dest`. Query `boards[i+1].attacks(dest)` — squares the moved piece attacks from dest. Filter to squares containing opponent pieces. If ≥2 opponent pieces are attacked and each is either (a) higher value than the moving piece, or (b) hanging on `boards[i+1]`, return True. Cook excludes the final move of the line and king-moves. Returns False if all boards in line are exhausted.

**`detect_hanging_piece(boards, moves, pov) -> bool`**

Check that `moves[0]` is a capture (on `boards[0]`, check if `boards[0].is_capture(moves[0])`). The captured piece must be non-pawn. Verify the target square was not defended on `boards[0]` before the capture (`_is_hanging` on the target before capture). If line is short (≤ 2 moves total), return True. Otherwise verify that after `boards[2]` (refuter's second move), material has not deteriorated vs `boards[1]`. This guards against "hanging but recaptured" cases.

**`detect_pin(boards, moves, pov) -> bool`**

Scan all plies. For each board in sequence, for each piece `p` of opponent color on the board: compute pin direction = `boards[i].pin(not pov, sq_of_p)`. If pin direction ≠ `chess.BB_ALL` (piece is pinned), check:
- Variant 1 (pin prevents attack): the pinned piece attacks a pov piece of higher value that is off the pin ray.
- Variant 2 (pin prevents escape): the pinned piece is attacked by a pov piece of lower value, and the pinned piece has pseudo-legal moves that go off the pin ray.
Returns True on either variant.

**`detect_skewer(boards, moves, pov) -> bool`**

Scan captures in moves (skip moves[0]). For each capture at boards[i] by a ray piece (QUEEN/ROOK/BISHOP): the captured piece must be on the opposite end of a line from the moving piece through a higher-value opponent piece. Specifically: (1) `moves[i]` is a capture, (2) the moved piece is R/B/Q, (3) the opponent piece that WAS on the capture square before the move (in `boards[i-1]`) was higher value than the capturing piece, (4) after the capture (`boards[i+1]`), there is another opponent piece further along the same ray. Returns True.

**`detect_double_check(boards, moves, pov) -> bool`**

Scan all boards. At any board where it is the opponent's turn (i.e. board resulted from pov's move), check `len(list(boards[i].checkers())) >= 2`. If yes, return True.

**`detect_discovered_attack(boards, moves, pov) -> bool`**

Two sub-cases:
1. Discovered check: at `boards[1]` (after pov's first move), `boards[1].is_check()` is True, and `moves[0].to_square` is NOT in `boards[1].checkers()` (a different piece is checking — the moving piece unblocked the check).
2. Discovered capture: scan moves[2], moves[4]... (pov's later moves). If `moves[k]` is a capture, and `moves[k].from_square` is different from `moves[0].to_square`, and `moves[k-1].from_square` was between `moves[0].from_square` and `moves[k].to_square` (the opponent's intervening move un-interposed a piece) → return True.

**`detect_back_rank_mate(boards, moves, pov) -> bool`**

Final board `boards[-1]` must be checkmate. Opponent king must be on rank 0 (black king on rank 0) or rank 7 (white king on rank 7) — i.e. on its back rank. `boards[-1].king(not pov)` gives the king square; `chess.square_rank(king_sq)` gives 0-7. At least one checker must be on the same rank. King's escape squares must all be either occupied by own pieces or attacked by pov pieces.

**`detect_generic_mate(boards, moves, pov) -> bool`**

`boards[-1].is_checkmate()`. Falls back when no named-mate subtype fires.

### Named-Mate Subtype Detectors (check final board position)

All named-mate detectors require `boards[-1].is_checkmate()` as a precondition.

**`detect_smothered_mate(boards, moves, pov) -> bool`**

Final position: mate delivered by a knight. Opponent king is surrounded on all escape squares by its own pieces (smothered). Check: `moves[-1]` moves a knight to the mating square. All king escape squares are occupied by opponent's own pieces (not pov pieces attacking them — actually smothered). The classic smothered-mate pattern: Qa6-a1 sac, Nd7-f6 smothers.

**`detect_anastasia_mate(boards, moves, pov) -> bool`**

Final position: opponent king on an edge file (file 0 or 7, i.e. `chess.square_file(king_sq) in (0, 7)`), not in the corner. Final move is a queen or rook landing on the king's rank or adjacent, with a knight blocking the king's lateral escape, and the rook/queen cutting off the file. Cook mirrors the board if king is on queenside to normalize to kingside.

**`detect_hook_mate(boards, moves, pov) -> bool`**

Final position: last move is a rook landing adjacent to the king. A pov knight defends the rook from an adjacent square. A pov pawn defends the knight.

**`detect_arabian_mate(boards, moves, pov) -> bool`**

Final position: opponent king in a corner (`square_file` in (0,7) AND `square_rank` in (0,7)). Last move is a rook adjacent to the king. A pov knight at knight's-move distance from the king defends the rook.

**`detect_boden_or_double_bishop_mate(boards, moves, pov) -> TacticMotif | None`**

Final position: ≥2 pov bishops are in `boards[-1].pieces(chess.BISHOP, pov)`. Both attack the opponent king (via `board.attackers(pov, king_sq)` filtered to bishops). If bishops are on opposite sides of the king's file → `boden-mate`. If same side → `double-bishop-mate`. Returns the specific string or None.

**`detect_dovetail_mate(boards, moves, pov) -> bool`**

Final position: last move is a queen, not adjacent to king, not on king's rank or file. King is not on edge. All king escape squares are controlled only by the queen (no pov piece other than queen attacks them, and occupied squares have pov pieces). Creates a "Y-shaped" control pattern.

### Tier-3 Detectors (3+ ply lookback, graded confidence)

Tier-3 detectors must return `(bool, confidence_int)` where `confidence_int` is 0-100 for the graded scoring. Simple grading approach: count how many of the detector's conditions are met and scale linearly.

**`detect_deflection(boards, moves, pov) -> tuple[bool, int]`**

Scan captures at index ≥2 (i.e. moves[2], moves[4]...). For each pov capture `moves[k]` at `boards[k]`:
- The capture target must be non-pawn and lower/equal value to capturer
- The capture square must differ from `moves[k-1].to_square` (opponent's last destination)
- Before the capture (`boards[k-1]`), the captured square was defended by the piece that just moved away (`moves[k-1].from_square` was attacking it)
- The opponent's last move (`moves[k-1]`) was forced: either (a) it captured on `moves[k-2].to_square` (pov forced the capture), or (b) the opponent was responding to check
- The capture square is NOT currently protected from `moves[k-1].to_square` (the moved piece no longer defends it from its new position)
If all conditions met → True. Confidence: count conditions met / 5 * 100 (all five = 100).

**`detect_intermezzo(boards, moves, pov) -> tuple[bool, int]`**

An intermezzo (zwischenzug) is an intermediate move before the expected recapture. Scan captures at index ≥2. For each pov capture `moves[k]` at `boards[k]`: the capture square `moves[k].to_square` was NOT attacked from `moves[k-2].to_square` in `boards[k-2]` (opponent's expected recapture square), but it WAS captured there 2 moves earlier (`moves[k-4]` captured that square — i.e. the recapture was "expected" but pov inserted a move). Verify `boards[k-1]` (after opponent's interlude) legally allows the recapture. High confidence if the board is in check before pov's intermezzo (the check forces the issue).

**`detect_x_ray(boards, moves, pov) -> tuple[bool, int]`**

Scan captures at index ≥2. For each pov capture `moves[k]`: verify that:
- `moves[k-1]` (opponent's move) was also a capture on the same square as `moves[k].to_square`
- `moves[k-2]` (pov's prior move) attacked that same square with same piece type
- `moves[k-1].from_square` lies between `moves[k].from_square` and `moves[k].to_square` (i.e. opponent captured a piece that was in the x-ray line)
X-ray: pov piece attacks through an intermediate piece that trades off, maintaining the threat. Confidence: all three conditions met = 100; two met = 60.

**`detect_interference(boards, moves, pov) -> tuple[bool, int]`**

Scan captures at index ≥2. For each pov capture `moves[k]`:
- Target is hanging on `boards[k]`
- Before pov's interference move (`boards[k-4]`), that target was defended by a defender `D`
- `D` is a ray piece (Q/R/B) at `defender_sq`
- The opponent's last move `moves[k-1]` landed on a square between `defender_sq` and the target (blocking the ray defense)
Interference: opponent's piece wanders into the ray, cutting off the defender.

**`detect_self_interference(boards, moves, pov) -> tuple[bool, int]`**

Same structure as interference, but the piece that blocks the ray is the OPPONENT's own piece blocking another opponent piece's defense. Specifically: before `moves[k-1]`, a defender `D` of color `not pov` defended the capture target. The opponent moved a DIFFERENT piece of color `not pov` onto the line between `D` and the target, blocking `D`'s protection. The target became hanging as a result.

**`detect_clearance(boards, moves, pov) -> tuple[bool, int]`**

Scan non-capturing pov moves (moves[2], moves[4]...) by ray pieces (Q/R/B). For each such move `moves[k]`:
- Move is not a capture
- Destination was empty before the move
- Opponent's prior move `moves[k-1]` was not a check-escape and not a promotion
- `moves[k-1].from_square` matches `moves[k].to_square` (opponent was on the square being cleared) OR lies between `moves[k].from_square` and `moves[k].to_square`
- After clearing, pov attacks along the cleared line
Clearance: pov's piece vacates a square so another pov piece can use the line.

**`detect_attraction(boards, moves, pov) -> tuple[bool, int]`**

Scan pov's moves. For each pov move `moves[k]`: if the opponent captures on `moves[k].to_square` with a high-value piece (king/queen/rook) at `moves[k+1]`, and pov then attacks that square at `moves[k+2]` (the attracted piece is now vulnerable). OR: if after the opponent capture, pov checks from a new direction. High confidence if the attracted piece is a king (force-check pattern).

**`detect_capturing_defender(boards, moves, pov) -> tuple[bool, int]`**

Scan captures at index ≥2. For each pov capture `moves[k]`:
- NOT the final position being checkmate (or IS checkmate — both can qualify)
- The captured piece is non-pawn
- On `boards[k-2]` (before the opponent's defending move `moves[k-1]`), the captured piece's square was defended by a pov piece, and the capture target (two moves later) was defended by the piece now captured
- `moves[k-1]` (opponent's move) captured or moved to defend some threat, but by doing so, the defender of the eventual capture target was captured or moved away
This is the pattern: pov captures the piece that was defending the real target.

**`detect_sacrifice(boards, moves, pov) -> tuple[bool, int]`**

Scan pov's moves for a move where pov suffers material loss ≥2 points (computed via `_material_diff` comparing boards before/after pov's move). Exclude promotions. At least one such move must appear in the sequence. Confidence = material sacrificed (capped at 9 for queen) / 9 * 100. High sacrifice → high confidence it's intentional.

---

## Integration Point in flaws_service.py

### `_build_flaw_record` (line 351-377)

Current signature:
```python
def _build_flaw_record(
    n: int,
    mover: Literal["white", "black"],
    severity: FlawSeverity,
    es_before: float,
    es_after: float,
    fen_map: dict[int, str],
    positions: list[GamePosition],
) -> FlawRecord:
```

The detector should be called here, after constructing the FEN-based board. The integration adds:

```python
# Tactic detection (Phase 124): read pv from positions[n+1], detect motif
tactic_motif_int: int | None = None
tactic_piece: int | None = None
tactic_confidence: int | None = None

fen_before_flaw = fen_map.get(n, "")
pv: str | None = positions[n + 1].pv if n + 1 < len(positions) else None
move_san_of_flaw: str | None = positions[n].move_san

if fen_before_flaw and pv and move_san_of_flaw:
    board_before = chess.Board(fen_before_flaw)
    try:
        flaw_move = board_before.parse_san(move_san_of_flaw)
        board_after_flaw = board_before.copy()
        board_after_flaw.push(flaw_move)
        tactic_motif_int, tactic_piece, tactic_confidence = detect_tactic_motif(
            board_after_flaw, pv
        )
    except (ValueError, chess.IllegalMoveError):
        pass  # malformed move_san or FEN — leave all three as None
```

Then `FlawRecord` must include `tactic_motif_int`, `tactic_piece`, `tactic_confidence` as optional fields.

### `classify_game_flaws` (line 615-682)

No changes to the loop structure needed. The change to `_build_flaw_record` flows through automatically. Both colors' flaws are already covered because the loop iterates `all_moves` which includes both colors (Phase 113).

### Severity gate constant

D-05 requires a tunable constant. In `flaws_service.py` (or `tactic_detector.py`):

```python
# Severity gate for tactic detection (D-05): mistakes AND blunders are eligible.
# Only flaws at this level or above get motif detection. Tunable constant.
TACTIC_MIN_SEVERITY: frozenset[str] = frozenset({"mistake", "blunder"})
```

The loop in `classify_game_flaws` already gates on `severity not in ("mistake", "blunder")`, so this constant can be used in `_build_flaw_record` to skip detection for inaccuracies (which are never stored anyway — but making it explicit future-proofs it).

### Confirmed: `backfill_flaws.py` requires zero new wiring

`scripts/backfill_flaws.py` calls `classify_game_flaws(game_obj, positions)` at line 210, then `flaw_record_to_row(user_id, game_id, flaw)` at line 246. Both of these will be extended in Phase 124. The script itself is untouched. [VERIFIED: codebase grep]

---

## Schema / Migration Mechanics

### Column pattern (from `game_flaw.py:44-50`)

```python
# Current nullable SmallInteger pattern:
tempo: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
```

Three new columns follow this exact pattern:

```python
# Tactic family (Phase 124 — D-01): all nullable SmallInteger.
# tactic_motif: TacticMotifInt enum (1-N); NULL = no detector fired.
# tactic_piece: python-chess PieceType (1=PAWN,2=KNIGHT,3=BISHOP,4=ROOK,5=QUEEN,6=KING)
#               per-motif semantic per D-12; NULL for ambiguous cases.
# tactic_confidence: winner-confidence 0-100; NULL when tactic_motif is NULL.
tactic_motif: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
tactic_piece: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
tactic_confidence: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
```

### Migration structure (follows `20260613_120000_phase_117_queue_pv.py` pattern)

```python
"""Phase 124: Add tactic_motif, tactic_piece, tactic_confidence to game_flaws.

Three nullable SmallInteger columns. Adding nullable columns to PostgreSQL 18
is a pure catalog update — no table rewrite, no extended lock (confirmed in
Phase 117 migration comment). Safe to run inline at deploy time.
"""

def upgrade() -> None:
    op.add_column("game_flaws", sa.Column("tactic_motif", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("tactic_piece", sa.SmallInteger(), nullable=True))
    op.add_column("game_flaws", sa.Column("tactic_confidence", sa.SmallInteger(), nullable=True))

def downgrade() -> None:
    op.drop_column("game_flaws", "tactic_confidence")
    op.drop_column("game_flaws", "tactic_piece")
    op.drop_column("game_flaws", "tactic_motif")
```

**No index needed:** `tactic_motif` queries will GROUP BY (aggregate scan) or use the existing `ix_game_flaws_user_severity` index as the leading predicate — the tactic columns are filter refinements, not primary lookup columns. Per Phase 126 (out of scope here), a covering index may be added when the comparison query is known.

**Migration note (from `a7e0b4796501` pattern):** Migrations must NOT import live app constants; use literal `sa.SmallInteger()` not symbolic references.

### python-chess PieceType integer values

PAWN=1, KNIGHT=2, BISHOP=3, ROOK=4, QUEEN=5, KING=6. [VERIFIED: codebase check `python3 -c "import chess; print(chess.PAWN, chess.KNIGHT, ...)"` returns `1 2 3 4 5 6`]

`tactic_piece` stores one of these 1-6 values or NULL. `chess.KING (=6)` can appear for mate motifs (mating piece is king only in rare endgame stalemate — not a real case in practice, but the schema accepts it). In practice, `tactic_piece` for mates will be the mating piece type (R/Q/N for smothered/back-rank etc.).

---

## PV Data Shape

### On-disk format (`game_positions.pv`)

- Column type: `Text` (nullable) — see `game_position.py:183`
- Format: space-joined UCI move strings, e.g. `"g1f3 b8c6 b1c3 a6b4"`
- Cap: `PV_CAP_PLIES = 12` from `app/services/engine.py:99`
- Stored only at positions where `ply == flaw_ply + 1` (D-117-02); NULL at all other plies
- Represents the **refutation line** from the position after the flawed move

### How pv is written

`_pv_to_uci_string(info, cap=PV_CAP_PLIES)` in `engine.py:279-288` builds it: `" ".join(m.uci() for m in pv[:cap])`. Returns None when PV is absent.

### How to parse it back

```python
moves = [chess.Move.from_uci(uci) for uci in pv_str.split()]
```

`chess.Move.from_uci` never raises for valid 4-5 char UCI strings. Promotion moves are 5-char (e.g. `"e7e8q"`).

### pov (refuting side)

`board_after_flaw.turn` is the refuting side's color. If white blundered (odd ply), `board_after_flaw.turn == chess.BLACK`. The refuter's moves appear at boards[0]→boards[1], boards[2]→boards[3], etc. (every other board transition).

---

## EndgameClassInt Precedent (Exact Pattern)

From `app/services/endgame_service.py:108` and `app/schemas/endgames.py:16`:

1. **Type alias in schemas** (or a separate `schemas/tactics.py`):
   ```python
   TacticMotif = Literal["fork", "hanging-piece", "pin", ...]
   ```

2. **IntEnum in service**:
   ```python
   class TacticMotifInt(IntEnum):
       FORK = 1
       HANGING_PIECE = 2
       ...
   ```

3. **Bidirectional dicts in service**:
   ```python
   _INT_TO_MOTIF: dict[int, TacticMotif] = {1: "fork", 2: "hanging-piece", ...}
   _MOTIF_TO_INT: dict[TacticMotif, int] = {v: k for k, v in _INT_TO_MOTIF.items()}
   ```

4. **Repository uses int** (pass `TacticMotifInt.FORK.value` or just the integer from the detector).

5. **Service/API uses string** (convert via `_INT_TO_MOTIF[row.tactic_motif]`).

The `EndgameClass` Literal is defined in `app/schemas/endgames.py` (separate from the service). Either follow the same pattern (define `TacticMotif` in `app/schemas/tactics.py`) or define it at the top of `tactic_detector.py` since Phase 126 is out of scope here. Claude's discretion.

---

## Fixture Validation Approach

### Test file structure

Follow `tests/services/test_position_classifier.py` — the closest precedent:
- File: `tests/services/test_tactic_detector.py`
- No DB required — all tests use `chess.Board` in-memory
- Each motif class has positives (10-15) and the shared hard-negative set

### Fixture format

Each fixture: a `(board_fen_before_flaw, move_san_of_flaw, pv_str, expected_motif)` tuple. The test:
1. Constructs `board_before = chess.Board(fen)`
2. Pushes `board_before.parse_san(move_san)` to get `board_after_flaw`
3. Calls `detect_tactic_motif(board_after_flaw, pv_str)`
4. Asserts the returned motif matches `expected_motif`

### Labeling source

Fixtures are labeled by human inspection of prod flaws from the dev DB (or from the architecture note's verified example: game 975197, user 44). NOT labeled by running cook.py.

### Precision measurement harness

```python
def compute_precision(results: list[tuple[TacticMotif | None, TacticMotif | None]]) -> float:
    """(predicted, expected) pairs. Returns TP / (TP + FP)."""
    tp = sum(1 for pred, exp in results if pred == exp and exp is not None)
    fp = sum(1 for pred, exp in results if pred is not None and pred != exp)
    return tp / (tp + fp) if (tp + fp) > 0 else 1.0
```

Per-motif: only count predictions for that motif class. Precision = `true_positives / (true_positives + false_positives)`.

### Hard-negative set

Positions where the refutation line triggers no tactic (e.g. a quiet positional error, or a simple recapture). The detector should return `None` for all of them. These validate the hanging-piece catch-all doesn't over-fire.

### `_make_pos` extension

The existing `_make_pos` helper in `test_flaws_service.py` constructs GamePosition objects without DB. The new test file needs the same pattern plus a `pv` field:

```python
def _make_pos_with_pv(ply: int, pv: str | None = None, ...) -> GamePosition:
    pos = GamePosition()
    pos.ply = ply
    pos.pv = pv
    ...
    return pos
```

---

## Common Pitfalls

### Pitfall 1: Off-by-one on `positions[n+1]` indexing
**What goes wrong:** `n+1` falls off the end of `positions` for the last move in a game.
**Why it happens:** The positions list length equals the number of half-moves + 1 (includes the terminal position with no move). The last position is `positions[-1]` with `move_san = None`. A flaw at the second-to-last ply has `n+1 == len(positions) - 1` which is fine, but if somehow `n == len(positions) - 1`, indexing `positions[n+1]` raises.
**How to avoid:** Guard `if n + 1 < len(positions)` before accessing `positions[n+1].pv`.
**Warning signs:** IndexError in `_build_flaw_record` during backfill.

### Pitfall 2: `board.pin()` returns `BB_ALL` for unpinned, not `None`
**What goes wrong:** Checking `if board.pin(color, sq)` returns True for unpinned pieces (since `BB_ALL` is truthy/non-zero).
**Why it happens:** python-chess returns the full bitboard `chess.BB_ALL` when the piece is free to move in all directions. This is truthy.
**How to avoid:** Check `board.pin(color, sq) != chess.BB_ALL` to identify pinned pieces.

### Pitfall 3: pov confusion in attackers calls
**What goes wrong:** `board.attackers(pov, sq)` finds pov's attackers of `sq`, but in the board sequence after the flaw, `pov` is the REFUTER (not the flawed player). Calling `attackers(chess.WHITE, sq)` when the flawed player is white finds WHITE's attackers — but white is the one who erred, so pov might be `chess.BLACK`.
**How to avoid:** Always derive `pov = board_after_flaw.turn` (the refuter's color) and use that consistently.

### Pitfall 4: Boards list indexing vs moves list indexing
**What goes wrong:** `boards[k]` is the board BEFORE `moves[k]` is played; `boards[k+1]` is after. Accessing `boards[k].is_capture(moves[k])` requires the board BEFORE the move.
**Why it happens:** The `_parse_pv` helper returns `boards` with `len(moves)+1` entries; `boards[0]` = initial, `boards[-1]` = final.
**How to avoid:** Keep consistent naming: `boards[k]` = board from which `moves[k]` is played.

### Pitfall 5: `is_capture` detection on `chess.Board`
**What goes wrong:** `board.is_capture(move)` requires the move to be legal on `board`. For cook-style detection, use `board.piece_at(move.to_square)` is not None (any piece on the target square means capture, for normal moves) OR `board.is_en_passant(move)`.
**Why it happens:** python-chess's `is_capture` does the same check internally; but calling it on an already-pushed board (wrong state) silently returns wrong results.
**How to avoid:** Use `boards[k].piece_at(moves[k].to_square) is not None` for capture detection, checking the board BEFORE the move.

### Pitfall 6: SAN parsing can fail for rare moves
**What goes wrong:** `board.parse_san(move_san)` raises `chess.IllegalMoveError` or `ValueError` for ambiguous or malformed SANs in edge cases (en passant, castling in unusual encodings).
**Why it happens:** SAN encoding can be source-dependent (chess.com vs lichess normalize differently).
**How to avoid:** Wrap the parse in a try/except in `_build_flaw_record`. On failure, leave all three tactic fields as None and continue.

### Pitfall 7: Tier-3 detectors firing on Core 8 positions
**What goes wrong:** `sacrifice` fires on almost every position where pov wins material (by definition). `hanging-piece` fires whenever a piece is undefended. Without the D-07 priority order, these catch-alls dominate.
**Why it happens:** Tier-3 detectors have broad, non-exclusive conditions.
**How to avoid:** Enforce the D-07 priority order strictly: run in order, return the first motif that fires. `hanging-piece` must be last.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No tactic labeling | Cook-style heuristic detection on stored PV | Phase 124 (this phase) | First cause-of-error tagging |
| Both-color PV required separate pass | PV stored at flaw_ply+1 for BOTH colors by v1.27 eval worker | Phase 117 / v1.27 | No new engine pass needed |
| Opponent flaws needed separate materialization | game_flaws already covers both colors (Phase 113) | Phase 113 | No schema re-design needed |

**Deprecated/outdated:**
- SEED-039 premise "no pv column exists": stale as of v1.27. PV is already stored.
- SEED-039 premise "opponent flaw materialization needed": already done in Phase 113.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Adding nullable SmallInteger columns to PostgreSQL 18 is a pure catalog update (no table rewrite) | Schema/Migration | Phase 117 migration comment confirms this for PG 11+; risk is negligible |
| A2 | `positions[n].move_san` is always non-null for flawed positions (not the terminal position) | Integration point | Terminal positions have null move_san; the guard `if move_san_of_flaw` handles this |
| A3 | Named-mate detector priority (smothered > anastasia > hook > arabian > boden > double-bishop > dovetail) is provisional and tunable | Cook algorithms section | Intra-mate priority is Claude's discretion (D-07 only fixes inter-tier order) |
| A4 | Tier-3 graded confidence: count-of-conditions / total-conditions * 100 is a sufficient scoring approach | Tier-3 detectors | May not be monotone enough to serve as a useful threshold; can be tuned post-backfill via SQL without re-backfilling |

---

## Open Questions (RESOLVED)

1. **Where to define `TacticMotif` Literal type** — RESOLVED: Claude's Discretion per CONTEXT.md (define in `tactic_detector.py` for now; move to a schema file in Phase 126 if the API needs it).
   - What we know: `EndgameClass` lives in `app/schemas/endgames.py`; `EndgameClassInt` lives in `app/services/endgame_service.py`
   - What's unclear: Phase 126 will need the Literal for API responses; is it better to define it now in a new `app/schemas/tactics.py` or inside `tactic_detector.py` (simpler, less ceremony for a service-internal type)?
   - Recommendation: Define in `tactic_detector.py` for now (Claude's discretion); if Phase 126 needs it in a schema file, move it then. Import from `tactic_detector` in the meantime.

2. **How many tier-3 detectors can realistically clear the ≥95% precision bar** — RESOLVED: handled by D-04 + D-10 (build all, leave sub-bar detectors query-suppressed at confidence=0 after fixture validation).
   - What we know: tier-3 heuristics have 3+ ply lookback and multiple conditions
   - What's unclear: without running against real prod data, some may produce 0% precision on the first attempt
   - Recommendation: Build all tier-3 per D-04, but plan for some to be query-suppressed (confidence=0) after fixture validation. The D-10 approach handles this gracefully.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python-chess | Tactic detector | Yes | 1.11.x | — |
| PostgreSQL (dev) | Migration test | Yes | 18 (Docker) | — |
| uv/pytest | Test suite | Yes | Current | — |

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pyproject.toml` (existing) |
| Quick run command | `uv run pytest tests/services/test_tactic_detector.py -x` |
| Full suite command | `uv run pytest -n auto -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TACSCH-01 | Migration adds tactic_motif column | integration (migration test) | `uv run pytest tests/test_migrations.py -x` or `uv run alembic upgrade head` | Migration file: Wave 0 |
| TACSCH-02 | tactic_piece stores PieceType int or NULL | unit | `uv run pytest tests/services/test_tactic_detector.py -k tactic_piece -x` | Wave 0 |
| TACDET-01 | detect_tactic_motif returns correct motif from PV | unit (per-motif fixture set) | `uv run pytest tests/services/test_tactic_detector.py -x` | Wave 0 |
| TACDET-02 | Priority order: fork wins over hanging-piece on same PV | unit | `uv run pytest tests/services/test_tactic_detector.py -k priority -x` | Wave 0 |
| TACDET-03 | Precision bars: Core ≥90%, tier-3 ≥95% | unit (precision harness) | `uv run pytest tests/services/test_tactic_detector.py -k precision -x` | Wave 0 |
| TACDET-04 | classify_game_flaws wires detector for both colors | unit + backfill smoke | `uv run pytest tests/services/test_flaws_service.py -k tactic -x` | Wave 0 (extend existing) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/services/test_tactic_detector.py -x`
- **Per wave merge:** `uv run pytest -n auto -x`
- **Phase gate:** Full suite green (`uv run pytest -n auto -x` + `uv run ty check app/ tests/` + `uv run ruff check app/ tests/`) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/services/test_tactic_detector.py` — all motif fixture tests + precision harness
- [ ] `app/services/tactic_detector.py` — new detector module
- [ ] `alembic/versions/<timestamp>_phase_124_tactic_motifs.py` — migration file
- [ ] Three column additions to `app/models/game_flaw.py`
- [ ] Three field additions to `FlawRecord` TypedDict in `flaws_service.py`
- [ ] Extended `flaw_record_to_row` in `game_flaws_repository.py`

---

## Security Domain

This phase adds no authentication, session management, or user-facing input validation. ASVS categories V2/V3/V4 do not apply. V5 (Input Validation): the PV string is sourced from our own engine output (stored in `game_positions.pv` by the eval worker) — not user-supplied. No injection risk. No security section needed.

---

## Sources

### Primary (HIGH confidence)
- `app/services/flaws_service.py` (local codebase) — `classify_game_flaws` integration point, `_build_flaw_record`, `_run_all_moves_pass`, `FlawRecord` TypedDict
- `app/services/endgame_service.py:108` (local codebase) — `EndgameClassInt` IntEnum precedent
- `app/models/game_flaw.py` (local codebase) — column pattern
- `app/models/game_position.py` (local codebase) — `pv`, `best_move`, `move_san` columns
- `app/services/engine.py:99` (local codebase) — `PV_CAP_PLIES = 12`, `_pv_to_uci_string`
- `app/repositories/game_flaws_repository.py` (local codebase) — `flaw_record_to_row`, `_SEVERITY_INT` pattern
- `scripts/backfill_flaws.py` (local codebase) — `classify_game_flaws` call at line 210 (zero new wiring needed)
- python-chess runtime verification — `chess.PAWN=1, KNIGHT=2, BISHOP=3, ROOK=4, QUEEN=5, KING=6`
- `alembic/versions/20260613_120000_phase_117_queue_pv.py` — migration pattern for nullable column additions

### Secondary (MEDIUM confidence)
- WebFetch: `github.com/ornicar/lichess-puzzler/blob/master/tagger/cook.py` — algorithm descriptions (AGPL source, not copied; heuristics described in own words)
- WebFetch: `github.com/ornicar/lichess-puzzler/blob/master/tagger/util.py` — helper function descriptions

### Tertiary (LOW confidence)
- N/A: all critical claims are verified from local codebase

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — python-chess, SQLAlchemy, Alembic all in use; no new packages
- Architecture: HIGH — integration point confirmed by reading actual source files
- Pitfalls: HIGH — derived from reading actual code paths + python-chess API behavior verified at runtime
- Detector algorithms: MEDIUM — described from WebFetch of cook.py; not executed; may have nuances in edge cases

**Research date:** 2026-06-17
**Valid until:** 2026-07-17 (stable domain — python-chess API and internal codebase don't change frequently)
