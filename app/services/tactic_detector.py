"""Tactic-motif detector for Phase 124 (TACDET-01/02/03/04).

Pure Python/CPU transform over a stored Stockfish refutation PV.
No I/O, no DB, no Stockfish calls. Input: board_after_flaw (chess.Board)
+ pv_str (space-joined UCI from game_positions.pv). Output: (motif, piece, confidence, depth).

Encoding follows the EndgameClassInt precedent (endgame_service.py:108):
  TacticMotifInt — IntEnum encoding for the tactic_motif SmallInteger column.
  TacticMotif    — Literal type alias for human-readable motif strings.
  _INT_TO_MOTIF / _MOTIF_TO_INT — bidirectional dicts.

Detector function return convention (used by dispatcher in detect_tactic_motif):
  Phase 127 contract (D-05):
  Core 8 + named-mate detectors: (fired: bool, piece: int | None, depth: int | None)
    depth is the half-move loop index at the point the motif fires (raw ply from flaw_ply+1).
    piece follows D-12 per-motif semantics.
  Tier-3 detectors: (fired: bool, piece: int | None, confidence: int, depth: int | None)
    confidence is 0-100 graded (count-of-conditions / total * 100).
    depth is the half-move loop index when the motif fires.
  detect_boden_or_double_bishop_mate: (motif: TacticMotif | None, piece: int | None, depth: int | None)
  Dispatcher detect_tactic_motif: (motif_int, piece, confidence, depth) — 4-tuple throughout.
  Graded scoring: _grade(met, total) -> int is the single named helper.

Relevance gate (D-01): non-mate detectors that scan the full PV check that the motif
fires in a continuation where pov does not lose material vs the starting position, or
fires on the very first pov move. This eliminates Case-B incidental hits (motif visible
in a non-forcing continuation after the refutation already won) without killing real
deep combinations (Case A — a forcing line where the motif IS the point).
"""

from __future__ import annotations

from enum import IntEnum
from typing import Callable, Literal

import chess

# ---------------------------------------------------------------------------
# Named constants — no magic numbers (CLAUDE.md)
# ---------------------------------------------------------------------------

# Piece values (cook.py convention): used by fork, skewer, hanging-piece,
# capturing-defender, and sacrifice detectors.  KING:99 ensures a forking check
# counts as a high-value fork target (D-08, shared utility port).
_PIECE_VALUES: dict[int, int] = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 99,
}

# No-king value table for _is_in_bad_spot's lower-value comparator (Pitfall 4, D-08).
# is_in_bad_spot asks "can this piece be profitably captured?" — a king can never be
# captured, so it must not appear as a valid lower-value attacker in that check.
# Contrast with fork's victim comparison which uses _PIECE_VALUES (king=99 makes a
# forking check qualify as a high-value attack).
_VALUES_NO_KING: dict[int, int] = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
}

# Core detectors fire with this confidence (cook is boolean — no gradations).
TACTIC_CONFIDENCE_HIGH: int = 100

# Severity gate (D-05): only mistakes and blunders receive motif detection.
# Tunable constant — do not hardcode in caller logic.
TACTIC_MIN_SEVERITY: frozenset[str] = frozenset({"mistake", "blunder"})

# Ray piece types: used for pin, skewer, x-ray, interference detectors.
_RAY_PIECES: frozenset[int] = frozenset({chess.BISHOP, chess.ROOK, chess.QUEEN})

# ---------------------------------------------------------------------------
# IntEnum encoding (TacticMotifInt) — values must never be reordered.
# Existing DB rows encode these ints. Per D-02 / D-03.
# ---------------------------------------------------------------------------


class TacticMotifInt(IntEnum):
    """Integer encoding for tactic_motif column (SmallInteger). Maps 1:1 to TacticMotif
    Literal strings. Values must never be reordered — existing DB rows encode these ints."""

    FORK = 1
    HANGING_PIECE = 2
    PIN = 3
    SKEWER = 4
    DOUBLE_CHECK = 5
    DISCOVERED_ATTACK = 6
    BACK_RANK_MATE = 7
    MATE = 8
    DEFLECTION = 9
    ATTRACTION = 10
    INTERMEZZO = 11
    X_RAY = 12
    INTERFERENCE = 13
    SELF_INTERFERENCE = 14
    CLEARANCE = 15
    CAPTURING_DEFENDER = 16
    SACRIFICE = 17
    SMOTHERED_MATE = 18
    ANASTASIA_MATE = 19
    HOOK_MATE = 20
    ARABIAN_MATE = 21
    BODEN_MATE = 22
    DOUBLE_BISHOP_MATE = 23
    DOVETAIL_MATE = 24
    # Phase 128.1-01: new Tier-2 motifs (append-only; preserve existing 1-24).
    DISCOVERED_CHECK = 25
    TRAPPED_PIECE = 26
    # Phase 128.1-02: move-type family (Tier 5, lowest — real tactics always win, D-03/D-04).
    EN_PASSANT = 27
    PROMOTION = 28
    UNDER_PROMOTION = 29


# ---------------------------------------------------------------------------
# Literal type alias — all 29 motif strings.
# ---------------------------------------------------------------------------

TacticMotif = Literal[
    "fork",
    "hanging-piece",
    "pin",
    "skewer",
    "double-check",
    "discovered-attack",
    "back-rank-mate",
    "mate",
    "deflection",
    "attraction",
    "intermezzo",
    "x-ray",
    "interference",
    "self-interference",
    "clearance",
    "capturing-defender",
    "sacrifice",
    "smothered-mate",
    "anastasia-mate",
    "hook-mate",
    "arabian-mate",
    "boden-mate",
    "double-bishop-mate",
    "dovetail-mate",
    # Phase 128.1-01
    "discovered-check",
    "trapped-piece",
    # Phase 128.1-02: move-type family
    "en-passant",
    "promotion",
    "under-promotion",
]

# ---------------------------------------------------------------------------
# Bidirectional encoding dicts
# ---------------------------------------------------------------------------

_INT_TO_MOTIF: dict[int, TacticMotif] = {
    1: "fork",
    2: "hanging-piece",
    3: "pin",
    4: "skewer",
    5: "double-check",
    6: "discovered-attack",
    7: "back-rank-mate",
    8: "mate",
    9: "deflection",
    10: "attraction",
    11: "intermezzo",
    12: "x-ray",
    13: "interference",
    14: "self-interference",
    15: "clearance",
    16: "capturing-defender",
    17: "sacrifice",
    18: "smothered-mate",
    19: "anastasia-mate",
    20: "hook-mate",
    21: "arabian-mate",
    22: "boden-mate",
    23: "double-bishop-mate",
    24: "dovetail-mate",
    # Phase 128.1-01: append-only; existing 1-24 never reordered (T-128.1-02)
    25: "discovered-check",
    26: "trapped-piece",
    # Phase 128.1-02: move-type family (T-128.1-05: append-only, no migration)
    27: "en-passant",
    28: "promotion",
    29: "under-promotion",
}

_MOTIF_TO_INT: dict[TacticMotif, int] = {v: k for k, v in _INT_TO_MOTIF.items()}

# ---------------------------------------------------------------------------
# Grouping constants
# ---------------------------------------------------------------------------

# All 9 named-mate motifs (D-03): fine-grained storage, free coarsening at query time.
# Usage: WHERE tactic_motif IN (MATE_MOTIFS) — no re-detect required.
MATE_MOTIFS: frozenset[TacticMotif] = frozenset(
    {
        "back-rank-mate",
        "mate",
        "smothered-mate",
        "anastasia-mate",
        "hook-mate",
        "arabian-mate",
        "boden-mate",
        "double-bishop-mate",
        "dovetail-mate",
    }
)

# Move-type family (D-02): en-passant, promotion, and under-promotion are grouped here
# because they are detected from the SHAPE of the refuting move, not from board geometry.
# They are detected + stored for lichess-theme parity; whether/how to surface them as
# chips is a Phase 129 decision (D-09). discovered-check and trapped-piece are NOT in
# this set — they are real tactical geometry.
MOVE_TYPE_MOTIFS: frozenset[TacticMotif] = frozenset(
    {
        "en-passant",
        "promotion",
        "under-promotion",
    }
)

# ---------------------------------------------------------------------------
# PV-parse helper (Pattern 2 from RESEARCH.md)
# ---------------------------------------------------------------------------


def _parse_pv(
    board_after_flaw: chess.Board, pv_str: str
) -> tuple[list[chess.Board], list[chess.Move]]:
    """Parse space-joined UCI PV string into board sequence.

    Returns (boards, moves) where boards[0] = board_after_flaw,
    boards[i+1] = board after moves[i]. Length: len(moves) = len(boards)-1.

    Raises ValueError on malformed UCI strings (caller wraps in try/except).
    """
    moves = [chess.Move.from_uci(uci) for uci in pv_str.split()]
    boards: list[chess.Board] = [board_after_flaw.copy()]
    for move in moves:
        b = boards[-1].copy()
        try:
            b.push(move)
        except AssertionError as exc:
            # chess.Board.push() raises AssertionError for pseudo-illegal moves;
            # treat as a malformed PV so callers can handle via ValueError guard.
            raise ValueError(f"PV move {move} is not legal in position") from exc
        boards.append(b)
    return boards, moves


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def _piece_value(piece_type: int) -> int:
    """Return the tactical value of a piece type (cook.py convention)."""
    return _PIECE_VALUES.get(piece_type, 0)


def _is_hanging(board: chess.Board, sq: int, color: chess.Color) -> bool:
    """Return True if piece at sq of color has no defenders of that color.

    Precision-first: strict undefended test (attackers(color, sq) empty).
    A piece is only hanging if it is both attacked and has no defenders.

    NOTE: This helper is NOT ray-aware. It is kept for backward compatibility with
    consumers that have not yet been migrated to the ray-aware helpers below.
    Six consumers will migrate in plans 02/03: fork, hanging-piece, skewer, pin,
    interference, trapped-piece. Fork already uses _is_defended (see detect_fork).
    """
    attacked_by_opponent = bool(board.attackers(not color, sq))
    defended_by_self = bool(board.attackers(color, sq))
    return attacked_by_opponent and not defended_by_self


def _is_defended(board: chess.Board, piece: chess.Piece, sq: int) -> bool:
    """True if piece at sq of piece.color has a direct or X-ray defender.

    Reimplemented from cook's util.is_defended pseudocode (AGPL boundary — no source copy).
    Consumers: fork (victim hanging check), and the six detector sites being migrated
    in plans 02/03 (hanging-piece, skewer, pin, interference, trapped-piece + this plan's
    fork rewire).

    Direct defense: board.attackers(piece.color, sq) is non-empty.
    X-ray defense: any opponent ray attacker (Q/R/B) is removed via board.copy(stack=False)
    and defenders re-checked. A piece defended only through a friendly ray piece in front
    is now correctly NOT treated as hanging.
    """
    # Direct defense
    if board.attackers(piece.color, sq):
        return True
    # X-ray defense: for each opponent ray attacker, remove it and re-check.
    for attacker_sq in board.attackers(not piece.color, sq):
        attacker = board.piece_at(attacker_sq)
        if attacker is not None and attacker.piece_type in _RAY_PIECES:
            bc = board.copy(stack=False)
            bc.remove_piece_at(attacker_sq)
            if bc.attackers(piece.color, sq):
                return True
    return False


def _is_in_bad_spot(board: chess.Board, sq: int) -> bool:
    """True if the piece at sq is attacked AND (hanging or capturable by a lower non-king).

    Reimplemented from cook's util.is_in_bad_spot pseudocode (AGPL boundary — no source copy).
    Uses _VALUES_NO_KING for the lower-value comparator (Pitfall 4, D-08): a king cannot
    be profitably captured, so it must not register as a valid lower-value attacker here.

    Used as:
    - A PRUNE in detect_fork: skip a fork candidate if the forker lands in a bad spot.
    - An ACCEPT in detect_skewer: require is_in_bad_spot on the capture square (plan 02/03).
    """
    piece = board.piece_at(sq)
    if piece is None:
        return False
    if not board.attackers(not piece.color, sq):
        return False  # not even attacked — cannot be in a bad spot
    # Hanging: no direct or X-ray defense at all
    if not _is_defended(board, piece, sq):
        return True
    # Capturable by a lower-value non-king opponent attacker
    for atk_sq in board.attackers(not piece.color, sq):
        atk = board.piece_at(atk_sq)
        if atk is not None and atk.piece_type != chess.KING:
            if _VALUES_NO_KING.get(atk.piece_type, 0) < _VALUES_NO_KING.get(piece.piece_type, 0):
                return True
    return False


def _material_diff(board: chess.Board, pov: chess.Color) -> int:
    """Sum of pov piece values minus opponent piece values. Excludes kings."""
    total = 0
    for pt in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
        val = _piece_value(pt)
        total += val * len(board.pieces(pt, pov))
        total -= val * len(board.pieces(pt, not pov))
    return total


def _grade(met: int, total: int) -> int:
    """Grade count-of-conditions as 0-100 integer percent.

    met / total * 100, rounded to nearest int. Returns 0 if total==0.
    """
    if total == 0:
        return 0
    return round(met / total * 100)


# ---------------------------------------------------------------------------
# Core 8 detectors
# Each returns (bool, piece_int_or_None) per the module convention.
# ---------------------------------------------------------------------------


def detect_fork(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Fork: a pov move attacks 2+ opponent pieces that are each higher-value or loose.

    Rebuilt to cook's exact relational predicate (D-09/D-10, plan 02 — no source copy):
    scan pov moves EXCEPT the last (`range(0, len(moves) - 2, 2)` — cook's [:-1] equiv);
    moved piece is not a king; PRUNE if forker lands in a bad spot (`_is_in_bad_spot`);
    count victims via `board_after.attacks(dest)`, SKIPPING pawn victims; victim qualifies
    if `_PIECE_VALUES[victim] > _PIECE_VALUES[forker]` (king=99, so forking checks count)
    OR (`not _is_defended` AND victim_sq not in board_after.attackers(not pov, dest) —
    the hanging victim is not itself defending the fork square); fire if victims ≥ 2.

    Returns (fired, forking_piece_type, depth) on detection.
    tactic_piece = the forking piece type (D-12).
    depth = loop index i (half-moves from flaw_ply+1) when the fork fires.

    Relevance gate (D-01): a fork at depth i>0 fires only if pov gained material
    vs the starting position. This eliminates Case-B deep-scan false positives —
    incidental forks in non-winning continuations — without killing real combinations
    where the fork IS the material gain (Case A).

    Note on last-move exclusion: cook scans [:-1] (excludes the last pov move). This
    aligns with the Phase-124 interpretation — the last pov move is excluded because
    cook's logic cannot verify whether the fork is meaningful without a following line.
    """
    material_at_start = _material_diff(boards[0], pov)
    material_at_end = _material_diff(boards[-1], pov)

    # Cook scans [:-1] (all pov moves except the last) — equivalent to range(0, len-2, 2)
    # when pov moves are at even indices. If len(moves) < 2, no pov moves to scan.
    for i in range(0, len(moves) - 2, 2):  # pov's turns, cook's [1::2][:-1] equivalent
        board_after = boards[i + 1]

        # Relevance gate (D-01): skip forks in non-winning continuations (Case-B fix).
        if i > 0 and material_at_end < material_at_start:
            continue

        move = moves[i]
        dest = move.to_square
        mover_piece = board_after.piece_at(dest)
        if mover_piece is None or mover_piece.color != pov:
            continue
        mover_type = mover_piece.piece_type
        mover_val = _piece_value(mover_type)

        # Cook gap 1: kings cannot fork (cook excludes king forkers explicitly)
        if mover_type == chess.KING:
            continue

        # Cook gap 1: forker-safety prune — skip if forker lands in a bad spot
        # (the forker itself is loose; the fork is not free)
        if _is_in_bad_spot(board_after, dest):
            continue

        attacked_sqs = board_after.attacks(dest)
        fork_sq_attackers = board_after.attackers(not pov, dest)
        victims: list[int] = []
        for sq in attacked_sqs:
            target = board_after.piece_at(sq)
            if target is None or target.color == pov:
                continue
            # Cook gap 2: skip pawn victims (cook skips pawns as fork targets)
            if target.piece_type == chess.PAWN:
                continue
            target_val = _piece_value(target.piece_type)
            # Victim qualifies if higher-value than forker (KING=99 makes forking checks count)
            # OR (hanging AND not an attacker of the fork square — the "not attacker" clause)
            is_higher_value = target_val > mover_val
            # Cook gap 3 (hanging victim): ray-aware _is_defended (D-08)
            is_hanging_victim = not _is_defended(board_after, target, sq)
            # Cook gap 4: hanging victim must not be defending the fork square itself
            is_not_defending_fork = sq not in fork_sq_attackers
            if is_higher_value or (is_hanging_victim and is_not_defending_fork):
                victims.append(sq)

        if len(victims) >= 2:
            return True, mover_type, i

    return False, None, None


def detect_hanging_piece(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Hanging piece: pov's first move captures an undefended non-pawn.

    Returns (fired, victim_piece_type, depth) on detection.
    tactic_piece = the victim (D-12).
    depth = 0 (always fires on the first pov move, if at all).
    """
    if not moves:
        return False, None, None

    first_move = moves[0]
    board_before = boards[0]

    # Must be a capture (piece on destination square before the move)
    target = board_before.piece_at(first_move.to_square)
    if target is None or target.piece_type == chess.PAWN:
        return False, None, None

    # Target must be undefended (hanging) on the board before capture
    if not _is_hanging(board_before, first_move.to_square, not pov):
        return False, None, None

    victim_type = target.piece_type
    return True, victim_type, 0  # depth 0: hanging piece is always first pov move


def _pin_prevents_attack(
    board: chess.Board, pinned_sq: int, pin_ray: chess.SquareSet, pov: chess.Color
) -> bool:
    """Cook sub-test 1: pin_prevents_attack.

    The pinned opponent piece attacks a pov piece on a square OUTSIDE the pin direction,
    where that pov piece is worth more than the pinned piece OR is hanging.
    This fires when the pin prevents the opponent from executing a threatened capture.

    Pitfall 7: board.pin(color, sq) is called with the PINNED piece's color.
    """
    pinned_piece = board.piece_at(pinned_sq)
    if pinned_piece is None:
        return False
    pinned_val = _piece_value(pinned_piece.piece_type)

    # Temporarily generate attacks from the pinned piece's square with a temp board
    # (board.attacks uses slider geometry without legality filtering)
    for target_sq in board.attacks(pinned_sq):
        target = board.piece_at(target_sq)
        if target is None or target.color != pov:
            continue
        # The target must be OUTSIDE the pin ray (inside = not a real threat)
        if target_sq in pin_ray:
            continue
        target_val = _piece_value(target.piece_type)
        # pov target is worth more than the pinned piece, or is hanging
        if target_val > pinned_val or not _is_defended(board, target, target_sq):
            return True
    return False


def _pin_prevents_escape(
    board: chess.Board,
    pinned_sq: int,
    pin_ray: chess.SquareSet,
    pov: chess.Color,
) -> bool:
    """Cook sub-test 2: pin_prevents_escape.

    A pov attacker INSIDE the pin line attacks the pinned piece; the pin is meaningful
    if the pinned piece is worth more than the pov attacker OR the pinned piece is hanging
    AND cannot legally step off the pin line to safety.

    INSIDE the pin line means the attacker square is IN the pin_ray SquareSet (the ray from
    the pinner through the pinned piece). The pinner itself is on the ray, as is every
    square between the pinner and the pinned piece.
    """
    pinned_piece = board.piece_at(pinned_sq)
    if pinned_piece is None:
        return False
    pinned_val = _piece_value(pinned_piece.piece_type)
    pinned_is_hanging = not _is_defended(board, pinned_piece, pinned_sq)

    for attacker_sq in board.attackers(pov, pinned_sq):
        # Attacker must be INSIDE the pin ray (on the pinner→pinned line)
        if attacker_sq not in pin_ray:
            continue
        attacker = board.piece_at(attacker_sq)
        if attacker is None:
            continue
        attacker_val = _piece_value(attacker.piece_type)
        # Higher-value pinned piece is always meaningful
        if pinned_val > attacker_val:
            return True
        # Hanging and can't escape off the pin line
        if pinned_is_hanging:
            # Check if ANY legal move for the pinned piece escapes the pin ray
            can_escape = False
            for move in board.legal_moves:
                if move.from_square != pinned_sq:
                    continue
                if move.to_square not in pin_ray:
                    can_escape = True
                    break
            if not can_escape:
                return True
    return False


def detect_pin(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Pin: a line piece constrains an opponent piece via either pin sub-test.

    Rebuilt to cook's two-sub-test port (D-09/D-10, plan 02 — no source copy):
    For each board position in the PV, scan every opponent piece; use `board.pin(color, sq)`
    with the PINNED piece's color (Pitfall 7). If pin_ray != BB_ALL (piece is pinned), find
    the pov pinner and apply both cook sub-tests:

    1. `pin_prevents_attack`: pinned piece threatens a pov piece OUTSIDE the pin line
       (worth more OR hanging) — the pin stops the threatened capture.
    2. `pin_prevents_escape`: a pov attacker INSIDE the pin line attacks the pinned piece;
       meaningful if pinned > attacker value, or pinned is hanging and can't escape.

    Replaces the old `_pin_wins_material` relevance gate (direct-capture accept / replacement
    guard reject) with cook's structural criteria — precision lift from 0.44 to measured value.

    Phase 131 precision fix (pin 0.819 -> ~0.95 TEST): only scan boards that follow a POV
    (refuting/winning side) move — the ODD board indices. boards[0] is pov-to-move, so pov's
    moves land on boards[1], boards[3], ... — those are the positions where a pin pov just
    CREATED exists. cook.py checks pins on exactly these nodes, not on every position. The old
    `enumerate(boards)` also scanned pov-to-move boards (even indices), where pre-existing /
    incidental structural pins (and pins inside opponent forcing lines: attraction, deflection,
    sacrifice) fired as false positives — isolated precision 0.477 -> 0.947 on TEST, recall ~1.0.

    tactic_piece = the pinner piece type (D-12).
    depth = max(0, k-1) where k is board index (SEED-057 IN-01 / Pitfall 6); k is always odd
    here so depth is even (0, 2, 4, ...).
    """
    # Only POV-move result boards (odd indices). boards[0] is pov-to-move (no pin created yet).
    for k in range(1, len(boards), 2):
        board = boards[k]
        for sq in chess.SQUARES:
            piece = board.piece_at(sq)
            if piece is None or piece.color == pov:
                continue
            # board.pin(color, sq) with the PINNED piece's color (Pitfall 7)
            # Returns BB_ALL when the piece is NOT pinned; any other value = pinned
            pin_ray = chess.SquareSet(board.pin(piece.color, sq))
            if board.pin(piece.color, sq) == chess.BB_ALL:
                continue

            # Find the pov pinner (ray piece on the pin ray)
            pinner_type: int | None = None
            for ray_sq in pin_ray:
                ray_piece = board.piece_at(ray_sq)
                if ray_piece is None or ray_piece.color != pov:
                    continue
                if ray_piece.piece_type not in _RAY_PIECES:
                    continue
                pinner_type = ray_piece.piece_type
                break

            if pinner_type is None:
                continue  # no pov ray pinner found (e.g. pinned by king — skip)

            # Fire if either cook sub-test holds
            if _pin_prevents_attack(board, sq, pin_ray, pov) or _pin_prevents_escape(
                board, sq, pin_ray, pov
            ):
                # SEED-057 (IN-01): k is board index; depth should be move index.
                # Board k follows move k-1. Clamp to 0 for k==0.
                return True, pinner_type, max(0, k - 1)

    return False, None, None


def detect_skewer(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Skewer: a ray piece captures through a high-value opponent piece that moved across
    the skewer line in the prior opponent move, exposing a lower-value piece behind.

    Rebuilt to cook's exact relational predicate (D-09/D-10, plan 02 — no source copy):
    scan pov moves from the 2nd (`range(2, len(moves), 2)`) — the first pov move lacks
    a preceding pov move context so can't be a relational skewer.  For each pov capture
    with a ray piece (Q/R/B) that is not checkmate:
      - let `between = chess.SquareSet.between(move.from_square, move.to_square)`
      - let `op = moves[k-1]` (the opponent's immediately prior move)
      - require `op.to_square != capture_square` (not a recapture)
        AND `op.from_square in between` (op piece moved ACROSS the skewer line)
      - require `_PIECE_VALUES[moved_op_piece] > _PIECE_VALUES[captured]` (higher-value
        piece was in front — king=99 so a forking check also qualifies)
        AND `_is_in_bad_spot(board_before, capture_square)` (the piece we capture is loose)

    tactic_piece = the skewering ray piece (D-12).
    depth = k (loop index, half-moves from flaw_ply+1) per Pitfall 6 / SEED-057 convention.

    No D-01 gate: skewer is a structural motif common in equalizing continuations.
    """
    for k in range(2, len(moves), 2):  # pov's 2nd+ moves (index convention: cook [1::2][1:])
        move = moves[k]
        board_before = boards[k]
        capture_sq = move.to_square

        # Must be a capture (piece on destination before the move)
        captured = board_before.piece_at(capture_sq)
        if captured is None or captured.color == pov:
            continue

        # Moving piece must be a pov ray piece (Q/R/B)
        mover = board_before.piece_at(move.from_square)
        if mover is None or mover.color != pov or mover.piece_type not in _RAY_PIECES:
            continue

        # Not checkmate after the capture (skewer is not a mating move)
        board_after = boards[k + 1]
        if board_after.is_checkmate():
            continue

        # Cook relational predicate: the prior opponent move must have come FROM a
        # between-square on the skewer line (the opponent's piece crossed the line).
        between = chess.SquareSet.between(move.from_square, capture_sq)
        op = moves[k - 1]  # opponent's move immediately before this pov move

        # Recapture guard: op did NOT just move to this capture square
        if op.to_square == capture_sq:
            continue

        # Key geometry: op's piece came FROM a square on the skewer line
        if op.from_square not in between:
            continue

        # The piece the opponent just moved must be higher value than the piece we capture
        op_piece_on_new_sq = board_before.piece_at(op.to_square)
        if op_piece_on_new_sq is None:
            continue
        if _PIECE_VALUES.get(op_piece_on_new_sq.piece_type, 0) <= _PIECE_VALUES.get(
            captured.piece_type, 0
        ):
            continue

        # The captured piece must be in a bad spot (loose / capturable by lower piece)
        if not _is_in_bad_spot(board_before, capture_sq):
            continue

        return True, mover.piece_type, k

    return False, None, None


def detect_double_check(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, None, int | None]:
    """Double check: pov delivers a move resulting in 2+ checkers.

    Returns (fired, None, depth) — D-12: piece is NULL for double-check.
    depth = i - 1 (the pov move index that delivered the double check),
    per Pitfall 7: board index i means move i-1 was the last move.
    """
    for i in range(1, len(boards)):
        board = boards[i]
        # After pov's move (odd board index = pov just moved)
        if (i % 2) != 1:
            continue
        # It's now opponent's turn; check if opponent is in double check
        if board.turn == (not pov) and len(list(board.checkers())) >= 2:
            return True, None, i - 1  # depth = move index (per Pitfall 7)

    return False, None, None


def detect_discovered_check(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Discovered check: pov's first move gives a discovered check (the checking piece
    is NOT the piece that moved).

    Returns (fired, unveiled_checker_piece_type, depth) where depth = 0 (discovered
    check always fires on the first pov move).
    tactic_piece = the piece that delivers the discovered check (D-12).

    D-03 split rationale: this is Sub-case 1 lifted out of detect_discovered_attack so
    that a discovering move that gives check tags as 'discovered-check' (int 25), not
    'discovered-attack' (int 6).  The more-specific subtype wins — the same pattern used
    by named-mate subtypes that short-circuit before generic mate.  discovered-check is
    ranked above discovered-attack in _GEOMETRIC_REGISTRY (lower list index = higher
    priority) so the dispatcher returns discovered-check when both would fire on the
    same PV at depth 0.
    """
    if len(moves) < 1 or len(boards) < 2:
        return False, None, None

    board_after_first = boards[1]
    if not board_after_first.is_check():
        return False, None, None

    first_dest = moves[0].to_square
    checkers_set = board_after_first.checkers()
    if first_dest in checkers_set:
        # The piece that just moved is itself the checker — direct check, not discovered
        return False, None, None

    # The moved piece is NOT in the checker set: it's a discovered check.
    for checker_sq in checkers_set:
        checker = board_after_first.piece_at(checker_sq)
        if checker is not None and checker.color == pov:
            return True, checker.piece_type, 0  # depth 0: always the first pov move

    return False, None, None


def detect_discovered_attack(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Discovered attack: an earlier pov move vacated a between-square, unmasking a capture.

    Rebuilt to cook's exact relational predicate (D-09/D-10, plan 02 — no source copy):
    scan pov moves from the 2nd (`range(2, len(moves), 2)`) to keep the loop starting
    at index 2 (Pitfall 1 — discovered-check owns the first pov move, depth 0).
    For each pov capture at index k:
      - compute `between = chess.SquareSet.between(move.from_square, move.to_square)`
      - let `op = moves[k-1]` — if `op.to_square == capture_square`: short-circuit to
        False (it is a recapture, not a discovered attack)
      - let `prev = moves[k-2]` (the earlier pov move)
      - require `prev.from_square in between` (earlier pov move vacated a between-square)
        AND `capture_sq != prev.to_square` (we are not capturing on prev's destination)
        AND `move.from_square != prev.to_square` (capturer did not come FROM prev's dest)
        AND `prev` is not a castling move (castling cannot unblock a ray)

    Returns (fired, unveiled_attacker_piece_type, depth).
    tactic_piece = the capturing piece (the piece now attacking on the unblocked ray).
    depth = k (half-moves from flaw_ply+1, per Pitfall 6 / SEED-057 convention).

    D-03 note: Sub-case 1 (first pov move gives discovered check) was split out into
    detect_discovered_check (int 25) which fires at depth 0.  This function handles
    only sub-case 2 (deeper captures). Loop starts at k=2, not k=0, so discovered-check
    positions are never re-claimed here (Pitfall 1 guard).
    """
    if len(moves) < 3 or len(boards) < 4:
        # Need at least 3 moves: prev pov (k-2), op (k-1), this pov capture (k=2)
        return False, None, None

    for k in range(2, len(moves), 2):  # pov's 2nd+ moves (cook [1::2][1:] equivalent)
        move = moves[k]
        board_before = boards[k]
        capture_sq = move.to_square

        # Must be a capture by an opponent piece (not pov capturing pov's own piece)
        captured_piece = board_before.piece_at(capture_sq)
        if captured_piece is None or captured_piece.color == pov:
            continue

        # Opponent's prior move going to capture_sq means recapture — short-circuit to False
        op = moves[k - 1]
        if op.to_square == capture_sq:
            continue

        # The earlier pov move (prev) must have vacated a between-square on the capture ray
        prev = moves[k - 2]

        # Castling cannot unblock a ray geometrically.
        # Bug-fix (131-REVIEW WR-01): is_castling() is board-state-aware — it checks the
        # king still sits on prev.from_square. board_before (boards[k]) is two half-moves
        # AFTER prev was played, so the castled king has already vacated e1/e8 and the
        # guard silently never fired. Use boards[k-2] (the state before prev) to detect it.
        if boards[k - 2].is_castling(prev):
            continue

        between = chess.SquareSet.between(move.from_square, capture_sq)

        # Require: prev.from_square ∈ between (earlier pov move VACATED a between-square)
        if prev.from_square not in between:
            continue

        # Require: capture_sq != prev.to_square (we are not capturing the piece prev moved)
        if capture_sq == prev.to_square:
            continue

        # Require: capturer did NOT come from prev's destination (not the same piece redirected)
        if move.from_square == prev.to_square:
            continue

        # The capturing piece is the "unveiled" attacker on the newly-open ray
        capturer = board_before.piece_at(move.from_square)
        if capturer is None or capturer.color != pov:
            continue

        # NOTE (131-REVIEW WR-02): depth here is max(0, k-1), but k is a MOVE index
        # (range(2, len(moves), 2)) like detect_skewer (which returns k) — not a BOARD
        # index like detect_pin (where the -1 is correct). So discovered-attack stores
        # depth one ply too shallow vs the docstring's "depth = k". NOT corrected here:
        # the depth-primary dispatch and 36 fixture labels were tuned around this k-1
        # value, and returning k flips a hand-confirmed discovered-attack fixture to fork.
        # Correcting it requires re-tuning + re-validating the attribution layer — tracked
        # as a follow-up, not an advisory code-review fix.
        return True, capturer.piece_type, max(0, k - 1)

    return False, None, None


def _escape_squares_all_lose_material(board: chess.Board, victim_sq: int, pov: chess.Color) -> bool:
    """Return True if EVERY legal escape square for the piece at victim_sq loses
    material for the escaping side.

    D-06 strict precision gate: an escape is SAFE if pov has no attacker on the
    destination, or if pov's cheapest attacker is worth AT LEAST as much as the
    victim (pov doesn't gain from capturing).  An escape is UNSAFE only when the
    victim lands on a square where pov can capture it profitably: pov's cheapest
    attacker value is strictly less than the victim's value.

    We intentionally do not model full SEE recapture chains: that would require
    detecting the "same-piece double-duty" problem (a pov piece that attacks both
    the victim and an escape square cannot do both simultaneously). The simpler rule
    "pov can take the victim with a strictly cheaper piece" is precise enough for
    this motif and avoids false positives from queen-guarded escape squares where
    the queen is the same piece that's already attacking the victim.

    D-06 also requires a non-empty escape set: a pinned piece has no legal escapes
    but is not "trapped" in the material-loss sense — return False in that case.

    Helper extracted from detect_trapped_piece to keep nesting depth <= 3 (CLAUDE.md).
    """
    victim_piece = board.piece_at(victim_sq)
    if victim_piece is None:
        return False

    victim_val = _piece_value(victim_piece.piece_type)

    # Build the set of legal destination squares for the victim piece.
    escape_squares: list[int] = []
    for move in board.legal_moves:
        if move.from_square == victim_sq:
            escape_squares.append(move.to_square)

    if not escape_squares:
        # Pinned or no legal moves: not the same as trapped. Return False per D-06.
        return False

    for dest_sq in escape_squares:
        # Simulate the escape move to refresh X-ray / discovered attackers.
        board_copy = board.copy()
        board_copy.push(chess.Move(victim_sq, dest_sq))

        # A) Safe square: pov has no attacker on the destination after the escape.
        pov_attackers = list(board_copy.attackers(pov, dest_sq))
        if not pov_attackers:
            return False

        # B) Destination is under pov attack.  The escape is safe if the cheapest
        # pov attacker is worth AT LEAST as much as the victim — pov breaks even or
        # loses from taking, so the escape is effective for the victim.
        pov_attacker_vals: list[int] = []
        for atk_sq in pov_attackers:
            atk_piece = board_copy.piece_at(atk_sq)
            if atk_piece is not None:
                pov_attacker_vals.append(_piece_value(atk_piece.piece_type))
        pov_attacker_vals.sort()
        if not pov_attacker_vals:
            return False  # race condition guard

        cheapest_pov_attacker = pov_attacker_vals[0]
        if victim_val <= cheapest_pov_attacker:
            # Pov's cheapest attacker is as expensive or more — not profitable for pov.
            # This is a safe escape square for the victim.
            return False
        # Else: pov can profitably take (cheapest_pov_attacker < victim_val) → unsafe.

    # Every escape square has a pov attacker strictly cheaper than the victim
    # → pov wins material from any escape → piece is trapped (D-06 strict gate).
    return True


def detect_trapped_piece(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Trapped piece: an opponent non-pawn piece is under attack by pov AND every
    legal escape move lands the piece on a square where pov wins material.

    D-06 strict precision gate: fire only when the escape set is non-empty (not
    pinned/stalemate) AND all escapes lose material for the escapee.
    D-07 distinction from hanging-piece: a hanging piece is capturable for free right
    now (no escape needed); a trapped piece HAS moves but all moves lose material.
    The dispatcher already resolves any co-fire by tier (Tier 2 < Tier 4) per D-03.

    Returns (fired, victim_piece_type, depth) where depth is the board index at which
    the trapped piece is detected (0 = after pov's first move).
    """
    if len(moves) < 1 or len(boards) < 2:
        return False, None, None

    for i in range(0, len(moves), 2):  # pov's turns at even indices
        board_after = boards[i + 1]
        opp = not pov

        for sq in chess.SQUARES:
            piece = board_after.piece_at(sq)
            if piece is None or piece.color != opp:
                continue
            if piece.piece_type == chess.PAWN:
                # Exclude pawns (mirror hanging-piece; pawn value makes FP-prone)
                continue

            # D-06 gate step 1: the piece must currently be under pov attack
            if not board_after.attackers(pov, sq):
                continue

            # D-07 gate: exclude pieces capturable for free right now (hanging).
            # A free capture does not require the piece to move — that is hanging-piece,
            # not trapped-piece (D-07 definition).
            if _is_hanging(board_after, sq, opp):
                continue

            # D-06 gate step 2: every legal escape must lose material
            # Set board turn to opp so legal_moves generates the victim's moves
            board_opp_turn = board_after.copy()
            board_opp_turn.turn = opp
            if _escape_squares_all_lose_material(board_opp_turn, sq, pov):
                return True, piece.piece_type, i

    return False, None, None


def detect_back_rank_mate(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Back-rank mate: checkmate with the opponent king boxed on its back rank by
    its OWN pieces, with at least one pov checker on the back rank.

    cook's three-gate logic (D-09, D-10 from prose — no source copy):
      1. board is checkmate AND opponent king is on its back rank.
      2. Own-blocker test: build the king's three forward squares (straight + two
         diagonals, clipped at the a/h files).  Each forward square MUST hold a
         defender piece of the opponent (not empty, not pov, not pov-attacked) —
         the king is boxed by its own pieces.  Any other condition on a forward
         square returns False (this gate eliminates corner-mate false positives
         where forward squares are empty or controlled by pov).
      3. At least one checker must sit on the back rank itself.

    Relative-rank arithmetic (Pitfall 3):
      pov=WHITE → opponent=BLACK, black king on rank 7, forward = king - 8.
      pov=BLACK → opponent=WHITE, white king on rank 0, forward = king + 8.

    Returns (fired, mating_piece_type, depth) on detection.
    tactic_piece = the mating piece (D-12).
    depth = len(moves) - 1 (mates fire at boards[-1], per Pitfall 4).
    """
    if not boards[-1].is_checkmate():
        return False, None, None

    opp_king_sq = boards[-1].king(not pov)
    if opp_king_sq is None:
        return False, None, None

    king_rank = chess.square_rank(opp_king_sq)
    king_file = chess.square_file(opp_king_sq)

    # Opponent's back rank: rank 7 for black king (pov=WHITE), rank 0 for white king (pov=BLACK)
    back_rank = 7 if (not pov) == chess.BLACK else 0
    if king_rank != back_rank:
        return False, None, None

    # Relative-rank forward offset: toward board center for the defender king.
    # pov=WHITE (opponent BLACK king on rank 7): forward_offset = -8 (rank 7 → rank 6).
    # pov=BLACK (opponent WHITE king on rank 0): forward_offset = +8 (rank 0 → rank 1).
    _FORWARD_OFFSET_WHITE_POV: int = -8
    _FORWARD_OFFSET_BLACK_POV: int = 8
    _MIN_FILE: int = 0
    _MAX_FILE: int = 7

    forward_offset = _FORWARD_OFFSET_WHITE_POV if pov == chess.WHITE else _FORWARD_OFFSET_BLACK_POV
    straight_fwd = opp_king_sq + forward_offset

    # Build the list of three forward squares, clipped at edge files.
    forward_squares: list[int] = [straight_fwd]
    if king_file > _MIN_FILE:
        forward_squares.append(straight_fwd - 1)  # forward-left diagonal
    if king_file < _MAX_FILE:
        forward_squares.append(straight_fwd + 1)  # forward-right diagonal

    # Own-blocker test (cook gate 2): every forward square must hold an opponent
    # piece (defender's own piece).  If any forward square is empty, holds a pov
    # piece, or is attacked by pov → this is NOT a back-rank mate (cook returns False).
    board = boards[-1]
    opp = not pov
    for sq in forward_squares:
        occupant = board.piece_at(sq)
        if occupant is None or occupant.color != opp:
            # Square is empty or holds a pov piece — not the own-blocker pattern.
            return False, None, None
        if board.attackers(pov, sq):
            # Square is attacked by pov — not purely a self-block position.
            return False, None, None

    # Back-rank-checker requirement (cook gate 3): at least one checker on the
    # opponent's back rank.
    for checker_sq in board.checkers():
        checker = board.piece_at(checker_sq)
        if checker is not None and checker.color == pov:
            if chess.square_rank(checker_sq) == back_rank:
                return True, checker.piece_type, len(moves) - 1

    return False, None, None


def detect_generic_mate(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Generic mate: final board is checkmate (no named subtype matched).

    Returns (fired, mating_piece_type, depth) on detection.
    tactic_piece = the last-moved (mating) piece (D-12).
    depth = len(moves) - 1 (mates fire at boards[-1], per Pitfall 4).
    """
    if not boards[-1].is_checkmate():
        return False, None, None

    depth = len(moves) - 1 if moves else None
    # Mating piece is the last piece moved
    if moves:
        last_move = moves[-1]
        mating_piece = boards[-1].piece_at(last_move.to_square)
        if mating_piece is not None and mating_piece.color == pov:
            return True, mating_piece.piece_type, depth

    return True, None, depth


# ---------------------------------------------------------------------------
# Named-mate subtype detectors
# Each requires boards[-1].is_checkmate() as a precondition.
# Each returns (bool, mating_piece_type_or_None).
# ---------------------------------------------------------------------------


def detect_smothered_mate(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Smothered mate: knight delivers checkmate; opponent king is surrounded by own pieces.

    Returns (fired, chess.KNIGHT, depth) on detection.
    depth = len(moves) - 1 (mates fire at boards[-1], per Pitfall 4).
    """
    if not boards[-1].is_checkmate() or not moves:
        return False, None, None

    last_move = moves[-1]
    mating_piece = boards[-1].piece_at(last_move.to_square)
    if mating_piece is None or mating_piece.piece_type != chess.KNIGHT:
        return False, None, None

    opp_king_sq = boards[-1].king(not pov)
    if opp_king_sq is None:
        return False, None, None

    # All king escape squares must be occupied by opponent's own pieces (smothered)
    king_moves = boards[-1].attacks(opp_king_sq)
    for escape_sq in king_moves:
        occupant = boards[-1].piece_at(escape_sq)
        # If the square is empty or occupied by a pov piece, it's not a pure smothered mate
        if occupant is None or occupant.color == pov:
            return False, None, None

    return True, chess.KNIGHT, len(moves) - 1


def detect_anastasia_mate(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Anastasia mate: queen/rook on the king's edge file traps the king, with an
    opponent blocker at king+1 center and a pov knight at king+3 center (cook D-10).

    cook geometry (file-normalized, from prose — no source copy):
      - King on a- or h-file but not a corner.
      - Mating move is a queen or rook landing on the king's file.
      - Normalize: a-file king uses +1/+3 toward center; h-file king uses -1/-3.
        This is equivalent to cook's flip_horizontal to a-file: the opponent has a
        blocker one square toward center (king+offset) and pov has a knight three
        squares toward center (king+3*offset).

    Named constants for the blocker and knight offsets (Pitfall 3 / CLAUDE.md):
      _ANASTASIA_BLOCKER_OFFSET = 1   (steps toward center from normalized king)
      _ANASTASIA_KNIGHT_OFFSET = 3    (steps toward center for the blocking knight)

    Returns (fired, mating_piece_type, depth) on detection.
    depth = len(moves) - 1 (mates fire at boards[-1], per Pitfall 4).
    """
    if not boards[-1].is_checkmate() or not moves:
        return False, None, None

    opp_king_sq = boards[-1].king(not pov)
    if opp_king_sq is None:
        return False, None, None

    king_file = chess.square_file(opp_king_sq)
    # King must be on edge file (a or h file), but not in corner
    if king_file not in (0, 7):
        return False, None, None

    king_rank = chess.square_rank(opp_king_sq)
    if king_rank in (0, 7):
        return False, None, None  # corner — arabian mate territory

    last_move = moves[-1]
    mating_piece = boards[-1].piece_at(last_move.to_square)
    if mating_piece is None or mating_piece.piece_type not in (chess.QUEEN, chess.ROOK):
        return False, None, None

    # Mating piece must land on the king's file (cook gate — closes the file)
    if chess.square_file(last_move.to_square) != king_file:
        return False, None, None

    # Cook geometry: direction toward center from the king's edge file.
    # a-file (0): center is at +1, +3 squares. h-file (7): center is at -1, -3 squares.
    # Named constants for clarity (no magic numbers per CLAUDE.md):
    _ANASTASIA_BLOCKER_OFFSET: int = 1
    _ANASTASIA_KNIGHT_OFFSET: int = 3
    center_sign = 1 if king_file == 0 else -1
    blocker_sq = opp_king_sq + center_sign * _ANASTASIA_BLOCKER_OFFSET
    knight_sq = opp_king_sq + center_sign * _ANASTASIA_KNIGHT_OFFSET

    # Require an opponent blocker one step toward center
    board = boards[-1]
    blocker = board.piece_at(blocker_sq)
    if blocker is None or blocker.color == pov:
        return False, None, None

    # Require a pov knight three steps toward center
    knight_piece = board.piece_at(knight_sq)
    if knight_piece is None or knight_piece.color != pov or knight_piece.piece_type != chess.KNIGHT:
        return False, None, None

    return True, mating_piece.piece_type, len(moves) - 1


def detect_hook_mate(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Hook mate: rook adjacent to king, defended by a pov knight ALSO adjacent to king,
    and that knight is defended by a pov pawn (the classic rook←knight←pawn chain).

    cook geometry (D-10, from prose — no source copy):
      - Mating move is a rook.
      - Rook is adjacent to the king (Chebyshev distance 1).
      - A pov knight defends the rook AND is itself adjacent to the king
        (Chebyshev distance 1 from king — this is the "hook" in hook-mate).
      - A pov pawn defends that knight.

    The critical constraint missing from the prior implementation was the
    knight-adjacent-to-king check: cook requires the defender knight to be within
    Chebyshev distance 1 of the king, not merely any pov knight that attacks the
    rook. Without this, arabian-mate positions (king in corner h8/h1 with f6/f3
    knight) were false-positives because the non-adjacent knight still attacked the
    rook square via knight-move geometry (Pitfall 8 — multi-piece chain).

    Returns (fired, chess.ROOK, depth) on detection.
    depth = len(moves) - 1 (mates fire at boards[-1], per Pitfall 4).
    """
    if not boards[-1].is_checkmate() or not moves:
        return False, None, None

    last_move = moves[-1]
    mating_piece = boards[-1].piece_at(last_move.to_square)
    if mating_piece is None or mating_piece.piece_type != chess.ROOK:
        return False, None, None

    opp_king_sq = boards[-1].king(not pov)
    if opp_king_sq is None:
        return False, None, None

    rook_sq = last_move.to_square
    board = boards[-1]

    # Rook must be adjacent to king (Chebyshev distance 1 = within king's attack range)
    if rook_sq not in board.attacks(opp_king_sq):
        return False, None, None

    # A pov knight must defend the rook AND be adjacent to the king (Chebyshev dist=1).
    # The knight-adjacent-to-king constraint is cook's key discriminator that excludes
    # f6/f3 knights in arabian-mate positions from satisfying the hook-mate chain.
    _HOOK_KNIGHT_MAX_DIST: int = 1
    knight_sq: int | None = None
    for def_sq in board.attackers(pov, rook_sq):
        piece = board.piece_at(def_sq)
        if piece is not None and piece.piece_type == chess.KNIGHT:
            if chess.square_distance(def_sq, opp_king_sq) <= _HOOK_KNIGHT_MAX_DIST:
                knight_sq = def_sq
                break

    if knight_sq is None:
        return False, None, None

    # A pov pawn must defend the knight (completing the rook←knight←pawn chain)
    for def_sq in board.attackers(pov, knight_sq):
        piece = board.piece_at(def_sq)
        if piece is not None and piece.piece_type == chess.PAWN:
            return True, chess.ROOK, len(moves) - 1

    return False, None, None


def detect_arabian_mate(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Arabian mate: king in corner, rook adjacent, knight covers remaining escape squares.

    Returns (fired, chess.ROOK, depth) on detection.
    depth = len(moves) - 1 (mates fire at boards[-1], per Pitfall 4).
    """
    if not boards[-1].is_checkmate() or not moves:
        return False, None, None

    opp_king_sq = boards[-1].king(not pov)
    if opp_king_sq is None:
        return False, None, None

    # King must be in a corner
    king_file = chess.square_file(opp_king_sq)
    king_rank = chess.square_rank(opp_king_sq)
    if king_file not in (0, 7) or king_rank not in (0, 7):
        return False, None, None

    last_move = moves[-1]
    mating_piece = boards[-1].piece_at(last_move.to_square)
    if mating_piece is None or mating_piece.piece_type != chess.ROOK:
        return False, None, None

    rook_sq = last_move.to_square
    # Rook must be adjacent to king
    if rook_sq not in boards[-1].attacks(opp_king_sq):
        return False, None, None

    # A pov knight must be within knight's-move distance of the king
    knights = boards[-1].pieces(chess.KNIGHT, pov)
    for knight_sq in knights:
        knight_attacks = chess.SquareSet(chess.BB_KNIGHT_ATTACKS[opp_king_sq])
        if knight_sq in knight_attacks:
            return True, chess.ROOK, len(moves) - 1

    return False, None, None


def detect_boden_or_double_bishop_mate(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[TacticMotif | None, int | None, int | None]:
    """Boden or double-bishop mate: two bishops deliver checkmate.

    Boden: bishops on opposite sides of king's file.
    Double-bishop: bishops on same side.
    Returns (motif_string_or_None, chess.BISHOP, depth).
    depth = len(moves) - 1 (mates fire at boards[-1], per Pitfall 4).
    """
    if not boards[-1].is_checkmate():
        return None, None, None

    opp_king_sq = boards[-1].king(not pov)
    if opp_king_sq is None:
        return None, None, None

    # Find pov bishops that attack the king
    pov_bishops = list(boards[-1].pieces(chess.BISHOP, pov))
    attacking_bishops = [sq for sq in pov_bishops if opp_king_sq in boards[-1].attacks(sq)]

    if len(attacking_bishops) < 2:
        return None, None, None

    king_file = chess.square_file(opp_king_sq)
    b1_file = chess.square_file(attacking_bishops[0])
    b2_file = chess.square_file(attacking_bishops[1])
    depth = len(moves) - 1

    # Boden: bishops on opposite sides of king's file
    if (b1_file < king_file) != (b2_file < king_file):
        return "boden-mate", chess.BISHOP, depth

    return "double-bishop-mate", chess.BISHOP, depth


def detect_dovetail_mate(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Dovetail (cozio) mate: queen delivers checkmate; king not on edge; all escapes queen-controlled.

    Returns (fired, chess.QUEEN, depth) on detection.
    depth = len(moves) - 1 (mates fire at boards[-1], per Pitfall 4).
    """
    if not boards[-1].is_checkmate() or not moves:
        return False, None, None

    last_move = moves[-1]
    mating_piece = boards[-1].piece_at(last_move.to_square)
    if mating_piece is None or mating_piece.piece_type != chess.QUEEN:
        return False, None, None

    opp_king_sq = boards[-1].king(not pov)
    if opp_king_sq is None:
        return False, None, None

    # King must not be on an edge (edge mates are typically back-rank or arabian)
    king_file = chess.square_file(opp_king_sq)
    king_rank = chess.square_rank(opp_king_sq)
    if king_file in (0, 7) or king_rank in (0, 7):
        return False, None, None

    # Queen must not be adjacent to king (it attacks from distance)
    queen_sq = last_move.to_square
    if queen_sq in boards[-1].attacks(opp_king_sq):
        return False, None, None

    return True, chess.QUEEN, len(moves) - 1


# ---------------------------------------------------------------------------
# Tier-3 detectors (3+ ply lookback, graded confidence)
# Each returns (bool, piece_int_or_None, confidence_int) where confidence is 0-100.
# ---------------------------------------------------------------------------


def detect_deflection(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int, int | None]:
    """Deflection: opponent piece forced away from defending a target.

    Returns (fired, target_piece_type, confidence, depth) on detection.
    tactic_piece = the deflected/target piece (D-12).
    depth = k (pov move index when the deflection-exploiting capture fires).
    """
    for k in range(2, len(moves), 2):  # pov's captures at index >= 2
        board_k = boards[k]
        captured = board_k.piece_at(moves[k].to_square)
        if captured is None or captured.piece_type == chess.PAWN:
            continue

        target_sq = moves[k].to_square
        captor_piece = board_k.piece_at(moves[k].from_square)
        captor_val = _piece_value(captor_piece.piece_type) if captor_piece is not None else 0

        if k < 1:
            continue

        opp_last_move = moves[k - 1]
        cond1 = _piece_value(captured.piece_type) <= captor_val  # low/equal value capture
        cond2 = target_sq != opp_last_move.to_square  # capture not where opp just moved
        # Was the target defended by the piece that just moved away?
        cond3 = False
        if k >= 1:
            defender_was_at = opp_last_move.from_square
            old_board = boards[k - 1]
            defender_piece = old_board.piece_at(defender_was_at)
            if defender_piece is not None and defender_piece.color == (not pov):
                cond3 = target_sq in old_board.attacks(defender_was_at)

        # Opponent's last move was forced (captured pov's piece or responding to check)
        cond4 = False
        if k >= 2:
            cond4 = (
                boards[k - 2].piece_at(opp_last_move.to_square) is not None
                or boards[k - 1].is_check()
            )

        # Target is no longer protected from where the deflected piece went
        cond5 = False
        new_pos = opp_last_move.to_square
        if new_pos != target_sq:
            cond5 = target_sq not in boards[k].attacks(new_pos)

        met = sum([cond1, cond2, cond3, cond4, cond5])
        if met >= 3:  # at least 3 of 5 conditions for a positive signal
            return True, captured.piece_type, _grade(met, 5), k

    return False, None, 0, None


def detect_attraction(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int, int | None]:
    """Attraction: opponent piece lured to a vulnerable square.

    Returns (fired, attracted_piece_type, confidence, depth) on detection.
    tactic_piece = the attracted piece (D-12).
    depth = k (pov move index of the lure that triggers the attraction sequence).
    """
    for k in range(0, len(moves) - 2, 2):  # pov's moves
        pov_dest = moves[k].to_square
        if k + 1 >= len(moves) or k + 2 >= len(moves):
            break

        # Opponent captures on the pov dest (attracted there)
        opp_move = moves[k + 1]
        if opp_move.to_square != pov_dest:
            continue

        attracted = boards[k + 1].piece_at(opp_move.from_square)
        if attracted is None or attracted.color == pov:
            continue
        attracted_val = _piece_value(attracted.piece_type)

        # High-value piece attracted (king/queen/rook = cond1)
        cond1 = attracted_val >= _piece_value(chess.ROOK)

        # Pov then attacks the attracted piece at k+2
        next_pov_move = moves[k + 2]
        board_after_opp = boards[k + 2]
        cond2 = pov_dest in board_after_opp.attacks(next_pov_move.from_square)

        # King attracted (strongest signal)
        cond3 = attracted.piece_type == chess.KING

        # Pov's lure was a sacrifice (lost material on move k)
        board_before_lure = boards[k]
        piece_on_dest = board_before_lure.piece_at(pov_dest)
        cond4 = piece_on_dest is not None  # pov moved to an occupied square (sacrifice)

        met = sum([cond1, cond2, cond3, cond4])
        if cond2 and met >= 2:  # require at least an attack after attraction
            return True, attracted.piece_type, _grade(met, 4), k

    return False, None, 0, None


def detect_intermezzo(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, None, int, int | None]:
    """Intermezzo (zwischenzug): intermediate move inserted before expected recapture.

    Returns (fired, None, confidence, depth) on detection.
    tactic_piece = None (D-12 ambiguous).
    depth = k (pov move index when the intermezzo fires).
    """
    if len(moves) < 4:
        return False, None, 0, None

    for k in range(2, len(moves), 2):  # pov's captures
        if boards[k].piece_at(moves[k].to_square) is None:
            continue  # not a capture

        # Check if this is a recapture of the same square as 2 moves earlier
        if k < 2:
            continue
        cond1 = moves[k].to_square == moves[k - 2].to_square

        # Check if pov was in check before this move (the zwischenzug created check)
        cond2 = boards[k].is_check()

        # The opponent made a non-recapture move at k-1 (the zwischenzug "interrupted")
        opp_move = moves[k - 1]
        if k >= 3:
            expected_recapture_sq = moves[k - 3].to_square if k >= 3 else -1
            cond3 = opp_move.to_square != expected_recapture_sq
        else:
            cond3 = False

        met = sum([cond1, cond2, cond3])
        if met >= 2:
            return True, None, _grade(met, 3), k

    return False, None, 0, None


def detect_x_ray(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, None, int, int | None]:
    """X-ray: pov attacks through an intermediate piece traded off.

    Returns (fired, None, confidence, depth) on detection.
    tactic_piece = None (D-12 ambiguous).
    depth = k (pov move index when the x-ray capture fires).
    """
    for k in range(2, len(moves), 2):  # pov captures
        if boards[k].piece_at(moves[k].to_square) is None:
            continue

        # Opponent captured on the same square at k-1
        cond1 = moves[k - 1].to_square == moves[k].to_square

        # Pov's prior move at k-2 attacked this same square
        cond2 = False
        if k >= 2:
            prior_pov_move = moves[k - 2]
            board_after_prior = boards[k - 1]
            cond2 = moves[k].to_square in board_after_prior.attacks(prior_pov_move.to_square)

        # The opponent's piece was between pov's prior piece and the target
        cond3 = False
        if k >= 2 and cond2:
            between = chess.SquareSet.between(moves[k - 2].to_square, moves[k].to_square)
            cond3 = moves[k - 1].from_square in between

        met = sum([cond1, cond2, cond3])
        confidence = _grade(met, 3) if met >= 2 else 0
        if met >= 2:
            return True, None, confidence, k

    return False, None, 0, None


def detect_interference(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, None, int, int | None]:
    """Interference: opponent's own move blocks a defender's ray, hanging the target.

    Returns (fired, None, confidence, depth) on detection.
    tactic_piece = None (D-12 ambiguous).
    depth = k (pov move index when the interference-exploiting capture fires).
    """
    for k in range(2, len(moves), 2):  # pov's captures
        board_k = boards[k]
        target_sq = moves[k].to_square
        target = board_k.piece_at(target_sq)
        if target is None:
            continue

        # Target must be hanging now
        if not _is_hanging(board_k, target_sq, not pov):
            continue

        if k < 2:
            continue

        # Before k-1 (before opponent's last move), was target defended by a ray piece?
        old_board = boards[k - 2]
        opp_last_move = moves[k - 1]
        blocker_sq = opp_last_move.to_square

        cond1 = False
        cond2 = False
        for defender_sq in old_board.attackers(not pov, target_sq):
            defender = old_board.piece_at(defender_sq)
            if defender is None or defender.piece_type not in _RAY_PIECES:
                continue
            # Check if blocker_sq is between defender and target
            between = chess.SquareSet.between(defender_sq, target_sq)
            if blocker_sq in between:
                cond1 = True  # a ray defense was blocked
                # The blocking piece belongs to opponent (interference by opponent's piece)
                blocker = board_k.piece_at(blocker_sq)
                cond2 = blocker is not None and blocker.color == (not pov)
                break

        met = sum([cond1, cond2])
        if met >= 1:
            return True, None, _grade(met, 2), k

    return False, None, 0, None


def detect_self_interference(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, None, int, int | None]:
    """Self-interference: opponent's OWN piece blocks its own defender's ray.

    Returns (fired, None, confidence, depth) on detection.
    tactic_piece = None (D-12 ambiguous).
    depth = k (pov move index when the self-interference-exploiting capture fires).
    """
    for k in range(2, len(moves), 2):
        board_k = boards[k]
        target_sq = moves[k].to_square
        target = board_k.piece_at(target_sq)
        if target is None:
            continue

        if not _is_hanging(board_k, target_sq, not pov):
            continue

        if k < 2:
            continue

        old_board = boards[k - 2]
        opp_last_move = moves[k - 1]
        blocker_sq = opp_last_move.to_square

        cond1 = False
        cond2 = False
        for defender_sq in old_board.attackers(not pov, target_sq):
            defender = old_board.piece_at(defender_sq)
            if defender is None or defender.piece_type not in _RAY_PIECES:
                continue
            between = chess.SquareSet.between(defender_sq, target_sq)
            if blocker_sq in between:
                cond1 = True
                # The BLOCKER is also an opponent piece (self-interference)
                blocker = board_k.piece_at(blocker_sq)
                cond2 = blocker is not None and blocker.color == (not pov)
                # And the blocker was moved by the opponent (opp_last_move)
                mover_piece = old_board.piece_at(opp_last_move.from_square)
                cond2 = cond2 and mover_piece is not None and mover_piece.color == (not pov)
                break

        met = sum([cond1, cond2])
        if met >= 1:
            return True, None, _grade(met, 2), k

    return False, None, 0, None


def detect_clearance(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, None, int, int | None]:
    """Clearance: pov vacates a square so another piece can use the line.

    Returns (fired, None, confidence, depth) on detection.
    tactic_piece = None (D-12 ambiguous).
    depth = k (pov move index of the clearance move itself).

    Relevance gate (D-01): clearance fires only if pov has not lost material at the
    clearance depth vs the starting position. This prevents fire on incidental non-capture
    ray moves in losing continuations (Case-B false positives in complex multi-move PVs).
    """
    material_at_start = _material_diff(boards[0], pov)
    for k in range(2, len(moves), 2):  # pov's non-capturing moves by ray pieces
        move = moves[k]
        board_before = boards[k]

        # D-01 relevance gate: clearance only fires if pov has not lost material
        if _material_diff(board_before, pov) < material_at_start:
            continue

        mover = board_before.piece_at(move.from_square)
        if mover is None or mover.piece_type not in _RAY_PIECES:
            continue

        # Must NOT be a capture
        if board_before.piece_at(move.to_square) is not None:
            continue

        cond1 = True  # ray piece moved to empty square (clearance candidate)

        # After clearing, a pov piece can use the vacated line
        board_after = boards[k + 1]
        cleared_sq = move.from_square

        # Check if another pov ray piece now attacks along the cleared line
        cond2 = False
        for sq in chess.SQUARES:
            piece = board_after.piece_at(sq)
            if piece is None or piece.color != pov or piece.piece_type not in _RAY_PIECES:
                continue
            if sq == move.to_square:
                continue  # the piece that moved
            if cleared_sq in board_after.attacks(sq):
                cond2 = True
                break

        # The opponent's prior move was not a check-escape
        cond3 = k < 1 or not boards[k - 1].is_check()

        met = sum([cond1, cond2, cond3])
        if cond2 and met >= 2:
            return True, None, _grade(met, 3), k

    return False, None, 0, None


def detect_capturing_defender(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int, int | None]:
    """Capturing defender: pov captures a piece that was defending the real target.

    Returns (fired, captured_defender_piece_type, confidence, depth) on detection.
    tactic_piece = the captured defender (D-12).
    depth = k (pov move index when the capturing-defender capture fires).
    """
    for k in range(2, len(moves), 2):
        board_k = boards[k]
        move = moves[k]
        captured = board_k.piece_at(move.to_square)
        if captured is None or captured.piece_type == chess.PAWN:
            continue

        cond1 = True  # non-pawn capture

        # The captured piece was defending some pov-attacked target
        cond2 = False
        cond3 = False
        board_before = boards[k - 1] if k >= 1 else boards[0]

        # Look for a pov-threatened target that was being defended by the captured piece
        for target_sq in chess.SQUARES:
            target = board_before.piece_at(target_sq)
            if target is None or target.color == pov:
                continue
            if move.to_square in board_before.attackers(pov, target_sq):
                continue  # pov already attacked it before
            # Was the captured piece defending target_sq?
            if target_sq in board_before.attacks(move.to_square):
                cond2 = True
                # After capture, is target_sq now undefended?
                board_after = boards[k + 1] if k + 1 < len(boards) else boards[-1]
                if _is_hanging(board_after, target_sq, not pov):
                    cond3 = True
                break

        met = sum([cond1, cond2, cond3])
        if met >= 2:
            return True, captured.piece_type, _grade(met, 3), k

    return False, None, 0, None


def detect_sacrifice(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int, int | None]:
    """Sacrifice: pov voluntarily loses material to gain a positional/tactical advantage.

    Returns (fired, sacrificed_piece_type, confidence, depth) on detection.
    tactic_piece = the sacrificed piece (D-12).
    depth = k of the largest sacrifice move (deepest pov move with max material loss).
    """
    max_sac_val = 0
    sac_piece_type: int | None = None
    sac_depth: int | None = None

    for k in range(0, len(moves), 2):  # pov's moves
        board_before = boards[k]
        board_after = boards[k + 1] if k + 1 < len(boards) else boards[-1]

        diff_before = _material_diff(board_before, pov)
        diff_after = _material_diff(board_after, pov)
        material_lost = diff_before - diff_after

        if material_lost < 2:  # minimum 2-point sacrifice (bishop/knight minimum)
            continue

        # The pov piece that was on the destination and got captured
        moved_piece = board_after.piece_at(moves[k].to_square)
        if moved_piece is None or moved_piece.color != pov:
            # pov piece was already captured on that square
            pre_piece = board_before.piece_at(moves[k].from_square)
            if pre_piece is not None and material_lost > max_sac_val:
                max_sac_val = material_lost
                sac_piece_type = pre_piece.piece_type
                sac_depth = k
        elif moved_piece.color == pov and material_lost > max_sac_val:
            # Pov piece was captured on next move
            if k + 1 < len(moves) and boards[k + 1].piece_at(moves[k].to_square) is not None:
                pre_piece = board_before.piece_at(moves[k].from_square)
                if pre_piece is not None:
                    max_sac_val = material_lost
                    sac_piece_type = pre_piece.piece_type
                    sac_depth = k

    if max_sac_val >= 2 and sac_piece_type is not None:
        # Confidence scales with sacrifice magnitude, capped at queen (9)
        confidence = _grade(min(max_sac_val, 9), 9)
        return True, sac_piece_type, confidence, sac_depth

    return False, None, 0, None


# ---------------------------------------------------------------------------
# Phase 128.1-02: Move-type detectors (Tier 5 — the new lowest tier, D-03/D-04)
# ---------------------------------------------------------------------------
# Move-type motifs fire ONLY when no real tactic fires — real tactics always win (D-04).
# The move-type tier has a strictly greater tier number (5) than hanging-piece (4), so
# any real tactic candidate beats any move-type candidate in the dispatcher sort.
#
# Detection is purely on the shape of moves[0] (the refuting move); no material gate
# is applied (en-passant captures and pawn promotions are trivially identifiable from
# the move structure).  These are expected to populate sparsely in practice — the ONLY
# PVs where move-type fires are those where nothing else in tiers 1-4 fired (D-02).


def detect_en_passant(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """En-passant: the first refuting move is an en-passant capture.

    Returns (fired, chess.PAWN, depth=0). Confidence: TACTIC_CONFIDENCE_HIGH
    (~100% by construction — the move shape is unambiguous).
    """
    if not moves:
        return False, None, None
    if boards[0].is_en_passant(moves[0]):
        return True, chess.PAWN, 0
    return False, None, None


def detect_promotion(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Promotion (queen): the first refuting move promotes a pawn to a QUEEN.

    D-01 dominance: a non-queen promotion fires detect_under_promotion and NOT this
    function — because detect_under_promotion fires only when moves[0].promotion is not
    None AND != chess.QUEEN, which is mutually exclusive with this function's condition
    (moves[0].promotion == chess.QUEEN). The Tier-5 dispatch loop calls all three
    move-type detectors unconditionally; only one can fire for any given move. The
    registry rank provides a secondary defense but is not the primary enforcement
    mechanism; the detection conditions are fully disjoint.

    Returns (fired, chess.PAWN, depth=0). Confidence: TACTIC_CONFIDENCE_HIGH.
    """
    if not moves:
        return False, None, None
    if moves[0].promotion == chess.QUEEN:
        return True, chess.PAWN, 0
    return False, None, None


def detect_under_promotion(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Under-promotion: the first refuting move promotes a pawn to a NON-queen piece.

    D-01 dominance: under-promotion DOMINATES promotion. This detector is ranked BEFORE
    detect_promotion in _MOVE_TYPE_REGISTRY (lower rank index = higher priority), so
    when moves[0] is a non-queen promotion, under-promotion is returned, NEVER promotion.

    Returns (fired, chess.PAWN, depth=0). Confidence: TACTIC_CONFIDENCE_HIGH.
    """
    if not moves:
        return False, None, None
    promo = moves[0].promotion
    # Fires only for non-queen promotions (knight=2, bishop=3, rook=4).
    if promo is not None and promo != chess.QUEEN:
        return True, chess.PAWN, 0
    return False, None, None


# ---------------------------------------------------------------------------
# D-07 priority dispatcher — detect_tactic_motif
# ---------------------------------------------------------------------------

# Ordered registry for the D-07 priority order.
# Intra-tier order within tiers 2-3 is provisional (D-08) — reorder here without
# touching detector bodies.

# Type aliases for detector function signatures (Phase 127: all detectors now 3- or 4-tuple with depth)
_BoolPieceFn = Callable[
    [list[chess.Board], list[chess.Move], chess.Color], tuple[bool, int | None, int | None]
]
_Tier3Fn = Callable[
    [list[chess.Board], list[chess.Move], chess.Color], tuple[bool, int | None, int, int | None]
]

# Tier 1: named-mate subtypes in priority order (A3: provisional intra-mate order)
_NAMED_MATE_REGISTRY: list[tuple[TacticMotif, int]] = [
    ("smothered-mate", TacticMotifInt.SMOTHERED_MATE),
    ("anastasia-mate", TacticMotifInt.ANASTASIA_MATE),
    ("hook-mate", TacticMotifInt.HOOK_MATE),
    ("arabian-mate", TacticMotifInt.ARABIAN_MATE),
    # boden/double-bishop handled separately (special return shape)
    ("dovetail-mate", TacticMotifInt.DOVETAIL_MATE),
]

_NAMED_MATE_DETECTOR_FNS: dict[TacticMotif, _BoolPieceFn] = {
    "smothered-mate": detect_smothered_mate,
    "anastasia-mate": detect_anastasia_mate,
    "hook-mate": detect_hook_mate,
    "arabian-mate": detect_arabian_mate,
    "dovetail-mate": detect_dovetail_mate,
}

# Tier 2: geometric material-winners (D-07, provisional D-08 intra-tier order)
# Intra-tier rank = enumerate index (lower = higher priority per _sort_key).
# discovered-check (rank 3) is placed ABOVE discovered-attack (rank 4) so a
# discovering move that gives check tags as discovered-check, not discovered-attack
# (D-03 dominance).  trapped-piece (rank 5) sits after the discovery motifs;
# D-03 tier-level dominance over hanging-piece (Tier 4) is satisfied by tier number
# alone — no intra-tier constraint on trapped-piece (D-05).
_GEOMETRIC_REGISTRY: list[tuple[TacticMotif, int]] = [
    ("fork", TacticMotifInt.FORK),  # rank 0
    ("skewer", TacticMotifInt.SKEWER),  # rank 1
    ("pin", TacticMotifInt.PIN),  # rank 2
    ("double-check", TacticMotifInt.DOUBLE_CHECK),  # rank 3 — check motifs together
    ("discovered-check", TacticMotifInt.DISCOVERED_CHECK),  # rank 4 — D-03: above discovered-attack
    ("discovered-attack", TacticMotifInt.DISCOVERED_ATTACK),  # rank 5
    ("trapped-piece", TacticMotifInt.TRAPPED_PIECE),  # rank 6 — D-05 discretion
]

_GEOMETRIC_DETECTOR_FNS: dict[TacticMotif, _BoolPieceFn] = {
    "fork": detect_fork,
    "skewer": detect_skewer,
    "pin": detect_pin,
    "double-check": detect_double_check,
    "discovered-check": detect_discovered_check,
    "discovered-attack": detect_discovered_attack,
    "trapped-piece": detect_trapped_piece,
}

# Tier 3: fuzzy detectors (D-07 order, provisional D-08)
_TIER3_REGISTRY: list[tuple[TacticMotif, int]] = [
    ("deflection", TacticMotifInt.DEFLECTION),
    ("attraction", TacticMotifInt.ATTRACTION),
    ("intermezzo", TacticMotifInt.INTERMEZZO),
    ("x-ray", TacticMotifInt.X_RAY),
    ("interference", TacticMotifInt.INTERFERENCE),
    ("self-interference", TacticMotifInt.SELF_INTERFERENCE),
    ("clearance", TacticMotifInt.CLEARANCE),
    ("capturing-defender", TacticMotifInt.CAPTURING_DEFENDER),
    ("sacrifice", TacticMotifInt.SACRIFICE),
]

_TIER3_DETECTOR_FNS: dict[TacticMotif, _Tier3Fn] = {
    "deflection": detect_deflection,
    "attraction": detect_attraction,
    "intermezzo": detect_intermezzo,
    "x-ray": detect_x_ray,
    "interference": detect_interference,
    "self-interference": detect_self_interference,
    "clearance": detect_clearance,
    "capturing-defender": detect_capturing_defender,
    "sacrifice": detect_sacrifice,
}

# Tier 5: move-type family (D-03/D-04 — new LOWEST tier below hanging-piece Tier 4).
# Real tactics (tiers 1-4) always win. Move-type only fires on the residual positions
# where no real motif fired. This is EXPECTED and NOT a bug — sparse population is
# the correct behavior (D-02 posture: move-type is the lowest-priority catch for
# positions whose refuting move happens to be a special move type).
#
# Intra-tier order: under-promotion (rank 0) before promotion (rank 1) so that a
# non-queen promotion is NEVER tagged as "promotion" (D-01 under-promotion dominance).
# en-passant is rank 2 (independent; no dominance relationship with promotions).
TIER_MOVE_TYPE = 5  # strictly greater than Tier 4 (hanging-piece) — D-04 real-tactic-wins

_MOVE_TYPE_REGISTRY: list[tuple[TacticMotif, int]] = [
    ("under-promotion", TacticMotifInt.UNDER_PROMOTION),  # rank 0 — D-01: dominates promotion
    ("promotion", TacticMotifInt.PROMOTION),  # rank 1
    ("en-passant", TacticMotifInt.EN_PASSANT),  # rank 2
]

_MOVE_TYPE_DETECTOR_FNS: dict[TacticMotif, _BoolPieceFn] = {
    "under-promotion": detect_under_promotion,
    "promotion": detect_promotion,
    "en-passant": detect_en_passant,
}


def detect_tactic_motif(
    board_after_flaw: chess.Board,
    pv_str: str,
    has_forced_mate: bool = False,
) -> tuple[int | None, int | None, int | None, int | None]:
    """Detect the highest-priority tactic motif from the refutation PV (D-07/D-02).

    Args:
        board_after_flaw: Position immediately after the flawed move was played.
                          board_after_flaw.turn is the refuting side (pov).
        pv_str: Space-joined UCI refutation line from game_positions.pv.
        has_forced_mate: When True, the mate branch runs even when boards[-1].is_checkmate()
                         is False. Required when Stockfish reports a mate-in-N score but the
                         PV is truncated at PV_CAP_PLIES (~12) so the final board is not yet
                         checkmate. The stored Stockfish score (eval_mate) is the authoritative
                         gate (D-06); is_checkmate() is preserved as the fast path when the
                         PV is short enough to show the final mating position.

    Returns:
        (tactic_motif_int, tactic_piece, tactic_confidence, tactic_depth) where:
        - tactic_motif_int: TacticMotifInt value or None if no detector fired.
        - tactic_piece: chess.PieceType int (1-6) or None (per-motif semantic D-12).
        - tactic_confidence: 0-100 or None when tactic_motif_int is None.
        - tactic_depth: raw half-move ply index from flaw_ply+1 (D-04), or None.

    Dispatch strategy (D-02): mates (Tier 1) short-circuit and always win (D-03/D-07).
    All non-mate detectors run and collect firings; the SHALLOWEST motif wins (depth primary,
    D-05); equal depth breaks by priority tier/rank so exactly one motif is returned.
    Hanging-piece (Tier 4, depth 0) beats a fork (Tier 2, depth 2) because depth dominates.

    Safe: malformed/None/empty pv_str returns (None, None, None, None) without raising.
    """
    # Guard: T-124-03 / T-127-01 — malformed or empty PV must never raise (threat register)
    if not pv_str:
        return None, None, None, None

    try:
        boards, moves = _parse_pv(board_after_flaw, pv_str)
    except ValueError:
        return None, None, None, None

    if not moves:
        return None, None, None, None

    pov = board_after_flaw.turn

    # D-06: mate branch eligibility. boards[-1].is_checkmate() is the fast path for
    # complete PVs; has_forced_mate=True is the fallback for Stockfish-reported mates
    # whose PV is truncated before the mating position.
    _can_run_mate = boards[-1].is_checkmate() or has_forced_mate

    # --- Tier 1: mate subtypes (D-03 dominance — always checked first, always wins) ---
    # Mates never enter the candidate pool; they short-circuit the dispatcher immediately.

    if _can_run_mate:
        # Named-mate subtypes in priority order (A3)
        for motif_str, motif_int in _NAMED_MATE_REGISTRY:
            fn = _NAMED_MATE_DETECTOR_FNS[motif_str]
            fired, piece, depth = fn(boards, moves, pov)
            if fired:
                return int(motif_int), piece, TACTIC_CONFIDENCE_HIGH, depth

        # Special: boden / double-bishop (returns motif string or None)
        boden_motif, boden_piece, boden_depth = detect_boden_or_double_bishop_mate(
            boards, moves, pov
        )
        if boden_motif is not None:
            return _MOTIF_TO_INT[boden_motif], boden_piece, TACTIC_CONFIDENCE_HIGH, boden_depth

        # Back-rank mate (before generic mate)
        br_fired, br_piece, br_depth = detect_back_rank_mate(boards, moves, pov)
        if br_fired:
            return TacticMotifInt.BACK_RANK_MATE, br_piece, TACTIC_CONFIDENCE_HIGH, br_depth

        # Generic mate (catch-all for any checkmate)
        gm_fired, gm_piece, gm_depth = detect_generic_mate(boards, moves, pov)
        if gm_fired:
            return TacticMotifInt.MATE, gm_piece, TACTIC_CONFIDENCE_HIGH, gm_depth

    # --- Collect all non-mate firings (D-05: depth-primary dispatch) ---
    # Candidates: run ALL non-mate detectors and collect firings.
    # Winner selection: primary key = depth (shallowest wins, D-05/D-07).
    # Tiebreaker at equal depth = (tier, priority_rank) — D-07 priority order preserved.
    # A hanging-piece (Tier 4) at depth 0 beats a fork (Tier 2) at depth 2 because
    # depth dominates. A fork at depth 0 beats hanging-piece at depth 0 via tier (2 < 4).
    # None depth sorts last (treat as infinity) — depth-unknown firings lose to depth-known.
    Candidate = tuple[int, int, int | None, int, int | None, int]
    candidates: list[Candidate] = []

    # Tier 2: geometric material-winners
    TIER2 = 2
    for rank, (motif_str, motif_int) in enumerate(_GEOMETRIC_REGISTRY):
        fn = _GEOMETRIC_DETECTOR_FNS[motif_str]
        fired, piece, depth = fn(boards, moves, pov)
        if fired:
            candidates.append((TIER2, rank, piece, TACTIC_CONFIDENCE_HIGH, depth, int(motif_int)))

    # Tier 3: fuzzy graded detectors
    TIER3 = 3
    for rank_offset, (motif_str, motif_int) in enumerate(_TIER3_REGISTRY):
        fn = _TIER3_DETECTOR_FNS[motif_str]
        fired, piece, confidence, depth = fn(boards, moves, pov)  # type: ignore[misc]
        if fired:
            candidates.append((TIER3, rank_offset, piece, confidence, depth, int(motif_int)))

    # Tier 4: hanging-piece (catch-all, D-07)
    TIER4 = 4
    hp_fired, hp_piece, hp_depth = detect_hanging_piece(boards, moves, pov)
    if hp_fired:
        candidates.append(
            (
                TIER4,
                0,
                hp_piece,
                TACTIC_CONFIDENCE_HIGH,
                hp_depth,
                int(TacticMotifInt.HANGING_PIECE),
            )
        )

    # Tier 5: move-type family (D-03/D-04 — lowest tier; real tactics in tiers 1-4 always win).
    # Move-type fires only on the RESIDUAL positions where no real motif fired. Sparse
    # population is expected and correct — NOT a bug (see MOVE_TYPE_MOTIFS and D-02 posture).
    # Under-promotion (rank 0) is ranked before promotion (rank 1) so that a non-queen
    # promotion can NEVER be tagged as "promotion" (D-01 dominance).
    for rank, (motif_str, motif_int) in enumerate(_MOVE_TYPE_REGISTRY):
        fn = _MOVE_TYPE_DETECTOR_FNS[motif_str]
        fired, piece, depth = fn(boards, moves, pov)
        if fired:
            candidates.append(
                (TIER_MOVE_TYPE, rank, piece, TACTIC_CONFIDENCE_HIGH, depth, int(motif_int))
            )

    if not candidates:
        return None, None, None, None

    # Sort key: depth-primary (D-05/D-07). Shallowest tactic wins.
    # Equal-depth ties break by (tier, rank) — preserving existing priority order.
    # Consequence: hanging-piece (Tier 4, depth 0) beats a fork (Tier 2, depth 2)
    # because depth 0 < depth 2. A fork (Tier 2) at depth 0 beats hanging-piece
    # (Tier 4) at depth 0 via tier tiebreak (2 < 4) — this is correct (D-07): when
    # the fork IS at depth 0, it is equally shallow and more specific. Tier-3 motifs
    # at depth 0 can beat Tier-2 at depth 2 (D-05 is intentional); they are suppressed
    # at query time via _TACTIC_CHIP_CONFIDENCE_MIN so this has no user-facing impact.
    def _sort_key(c: Candidate) -> tuple[int, int, int]:
        depth_val = c[4] if c[4] is not None else 999999
        return (depth_val, c[0], c[1])  # (depth, tier, rank) — depth primary

    winner = min(candidates, key=_sort_key)
    return winner[5], winner[2], winner[3], winner[4]
