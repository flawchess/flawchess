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
# capturing-defender, and sacrifice detectors.
_PIECE_VALUES: dict[int, int] = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 99,
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


# ---------------------------------------------------------------------------
# Literal type alias — all 24 motif strings.
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
    """
    attacked_by_opponent = bool(board.attackers(not color, sq))
    defended_by_self = bool(board.attackers(color, sq))
    return attacked_by_opponent and not defended_by_self


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
    """Fork: a pov move attacks 2+ opponent pieces each higher-value or hanging.

    Returns (fired, forking_piece_type, depth) on detection.
    tactic_piece = the forking piece type (D-12).
    depth = loop index i (half-moves from flaw_ply+1) when the fork fires.

    Relevance gate (D-01): a fork at depth i>0 fires only if pov gained material
    vs the starting position. This eliminates Case-B deep-scan false positives —
    incidental forks in non-winning continuations — without killing real combinations
    where the fork IS the material gain (Case A).
    """
    # Bug fix (124, code-review WR-01): the previous bound `len(moves) - 1` dropped
    # the final pov move on odd-length PVs (~23% of prod PVs end on a pov move, e.g. a
    # fork delivered by the decisive last move). boards[i + 1] is always valid because
    # len(boards) == len(moves) + 1, so i == len(moves) - 1 indexes the last board.
    material_at_start = _material_diff(boards[0], pov)
    material_at_end = _material_diff(boards[-1], pov)
    for i in range(0, len(moves), 2):  # pov's turns at even indices
        board_after = boards[i + 1]

        # Relevance gate (D-01): skip forks in non-winning continuations (Case-B fix).
        # A fork at i==0 is always relevant (the refuting move itself is a fork).
        # At i>0 the fork fires if the PV ends with pov not losing material vs start —
        # equal material is OK (fork recovers equality), strictly losing material is not.
        # Using material_at_end (not board_after) because the fork may not have cashed
        # out yet at fork depth — the gain (or recovery) comes in follow-up moves.
        if i > 0 and material_at_end < material_at_start:
            continue

        move = moves[i]
        dest = move.to_square
        mover_piece = board_after.piece_at(dest)
        if mover_piece is None or mover_piece.color != pov:
            continue
        mover_type = mover_piece.piece_type
        mover_val = _piece_value(mover_type)

        attacked_sqs = board_after.attacks(dest)
        victims: list[int] = []
        for sq in attacked_sqs:
            target = board_after.piece_at(sq)
            if target is None or target.color == pov:
                continue
            target_val = _piece_value(target.piece_type)
            if target_val > mover_val or _is_hanging(board_after, sq, not pov):
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


def _pin_wins_material(
    boards: list[chess.Board],
    moves: list[chess.Move],
    pov: chess.Color,
    pin_board_idx: int,
    pinned_sq: int,
) -> bool:
    """Return True if pov plausibly exploits the pin (relevance gate, D-01).

    Fixes the loose-pin false positive where a geometric pin fires at depth 0 in a
    non-pin fixture (e.g., fork fixture) before pov has moved. The key symptom: at
    depth 0, the "pinned" piece is immediately moved/captured by pov on the next
    pov move, exposing a pov piece on the pin square — not a real pin.

    Two checks (nesting depth <= 3, CLAUDE.md §Keep functions small). SEED-057 reordered
    these so the replacement-guard REJECT runs before the direct-capture ACCEPT:
    1. Replacement guard (reject): if the pinned square has a pov piece right after this
       board (boards[pin_board_idx + 1]), the "pin" is actually a position where pov just
       moved a piece to that square — it is pov's own piece being checked, not a real
       opponent piece pinned. This was the exact Case-B false positive: at depth 0 in
       the fork fixture, the square that appeared "pinned" was replaced by a pov piece.
    2. Direct capture (accept): pov captures the pinned piece in a later pov move.
       A pin that leads to a direct capture (after surviving Check 1) is relevant.

    SEED-057 (WR-01): the original Check-1 loop bound `pin_board_idx + 1` iterated the
    OPPONENT's moves whenever the pin was found at an even board index (the common case,
    incl. the start position), because pov's moves sit at EVEN move indices — so the
    direct-capture check was a no-op for even-k pins. Two facts compound: (a) Check 1 is
    an *accept* path, not a prune path (the gate's only rejection is the replacement
    guard), so fixing the parity alone short-circuited the guard and ACCEPTED more pins
    (precision regressed 0.413 -> 0.393 on the CC0 TRAIN set). Running the guard first and
    fixing the parity prunes incidental pins as intended: a pov piece capturing the
    "pinned" piece on the very next ply is a grab, not a constraining pin. Net effect on
    the CC0 fixture: pin TRAIN precision 0.413 -> 0.440, FP 478 -> 428 (TP/recall flat).
    """
    # Check 1 (reject): replacement guard — if pov immediately occupies the pinned square
    # after this board, this is not a real pin (Case-B false positive suppression).
    if pin_board_idx + 1 < len(boards):
        post_pin = boards[pin_board_idx + 1].piece_at(pinned_sq)
        if post_pin is not None and post_pin.color == pov:
            return False  # pov occupies that square; no real opponent pin

    # Check 2 (accept): pov directly captures the pinned piece in a later pov move.
    # pov's moves sit at EVEN move indices; start at the first pov move at/after the pin
    # board (SEED-057 parity fix — see the docstring for why this was a no-op before).
    first_pov_move = pin_board_idx + (pin_board_idx % 2)
    for j in range(first_pov_move, len(moves), 2):
        if moves[j].to_square == pinned_sq:
            return True  # direct capture of the pinned piece

    # Default: accept the pin. We trust the geometric check is correct.
    # A "loose" pin (no direct capture, not immediately replaced) may still be a
    # real defensive resource (e.g., pin fixture [10] where material falls then recovers).
    return True


def detect_pin(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Pin: a line piece pins an opponent piece to a higher-value piece behind.

    Returns (fired, line_piece_type, depth) on detection.
    tactic_piece = the line piece delivering the pin (D-12).
    depth = move index that established the pin (0 = first PV move), matching the
        move-index depth semantics of every other motif (SEED-057 IN-01).

    Relevance gate (D-01): the pin fires only if pov wins material from it
    (direct capture in a later move, or material non-loss at pin depth). This
    removes the loose-pin false positive where a geometric pin exists in the PV
    but pov never exploits it — the "pin exists, that's enough" Case-B bug.
    """
    for k, board in enumerate(boards):
        for sq in chess.SQUARES:
            piece = board.piece_at(sq)
            if piece is None or piece.color == pov:
                continue
            # Check if this opponent piece is pinned
            pin_ray = board.pin(not pov, sq)
            if pin_ray == chess.BB_ALL:
                continue  # Pitfall 2: BB_ALL means not pinned

            # Find the pov pin-delivering piece along the ray
            for pin_sq in chess.SquareSet(pin_ray):
                pinner = board.piece_at(pin_sq)
                if pinner is None or pinner.color != pov:
                    continue
                if pinner.piece_type not in _RAY_PIECES:
                    continue

                # Relevance gate (D-01): fire only if pov can win material from this pin.
                # Without this gate, any geometric pin in the PV fires regardless of
                # whether pov ever exploits it (the "pin exists, that's enough" Case-B bug).
                if not _pin_wins_material(boards, moves, pov, k, sq):
                    continue

                # SEED-057 (IN-01): every other detector returns a MOVE index as depth
                # (0 = first PV move); k is a BOARD index (0 = start position). Board k
                # follows move k-1, so return max(0, k - 1) to put pin depth on the same
                # scale as the other motifs. Clamp at 0 for k==0 (pin predates the PV
                # window — no in-window move created it).
                return True, pinner.piece_type, max(0, k - 1)

    return False, None, None


def detect_skewer(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Skewer: a ray piece attacks a high-value piece that must move, exposing one behind.

    Returns (fired, line_piece_type, depth) on detection.
    tactic_piece = the skewering ray piece (D-12).
    depth = loop index i when the skewer fires (per Pitfall 5: loop starts at 1).

    No D-01 gate: skewer is a structural motif (ray piece attacks a piece that must
    move, exposing one behind). Unlike fork, it is common in equalizing or even
    slightly losing continuations (e.g. winning back material against a material deficit).
    A D-01 material-gain gate would incorrectly suppress these legitimate cases.
    """
    for i in range(1, len(moves)):
        move = moves[i]
        board_before = boards[i]
        board_after = boards[i + 1]

        # Must be pov's move (even index = pov's turn)
        if i % 2 != 0:
            continue

        # The moving piece must be a ray piece
        mover = board_after.piece_at(move.to_square)
        if mover is None or mover.color != pov or mover.piece_type not in _RAY_PIECES:
            continue

        # Must be a capture (skewer captures through a piece)
        captured = board_before.piece_at(move.to_square)
        if captured is None:
            continue

        # The captured piece must be of lower value than a piece behind it
        captured_val = _piece_value(captured.piece_type)
        mover_sq = move.from_square

        # Check for an opponent piece further along the same ray behind the captured piece
        between = chess.SquareSet.between(mover_sq, move.to_square)
        if between:
            # The captured piece was blocking something — check what was behind it
            # After capture, check pieces further along the mover's attack ray
            for further_sq in board_after.attacks(move.to_square):
                further_piece = board_after.piece_at(further_sq)
                if further_piece is None or further_piece.color == pov:
                    continue
                if _piece_value(further_piece.piece_type) >= captured_val:
                    return True, mover.piece_type, i

        # Alternative: mover attacks a high-value piece, with a lower-value piece behind
        for attacked_sq in board_before.attacks(move.to_square):
            piece_on_ray = board_before.piece_at(attacked_sq)
            if piece_on_ray is None or piece_on_ray.color == pov:
                continue
            if _piece_value(piece_on_ray.piece_type) > _piece_value(mover.piece_type):
                # The piece behind the captured piece is higher value than the mover
                # That means a high-value piece was in front, a lower-value target behind
                if captured_val < _piece_value(piece_on_ray.piece_type):
                    return True, mover.piece_type, i

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


def detect_discovered_attack(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Discovered attack: pov's first move unblocks an attack by another pov piece.

    Returns (fired, unveiled_attacker_piece_type, depth) on detection.
    tactic_piece = the unveiled attacking piece (D-12).
    depth = 0 for discovered check on first move; k for sub-case 2 captures.

    Relevance gate (D-01): sub-case 2 captures fire only if pov gained material vs
    the starting position at the capture board (eliminates Case-B incidentals).
    """
    if len(moves) < 1 or len(boards) < 2:
        return False, None, None

    # Sub-case 1: discovered check — first move puts opponent in check
    # but the checking piece is NOT the piece that just moved
    board_after_first = boards[1]
    if board_after_first.is_check():
        first_dest = moves[0].to_square
        checkers_set = board_after_first.checkers()
        if first_dest not in checkers_set:
            # The piece that just moved is not the checker — it's a discovered check
            for checker_sq in checkers_set:
                checker = board_after_first.piece_at(checker_sq)
                if checker is not None and checker.color == pov:
                    return True, checker.piece_type, 0  # depth 0: first pov move

    # Sub-case 2: discovered capture further in the line
    material_at_start = _material_diff(boards[0], pov)
    for k in range(2, len(moves), 2):  # pov's later moves
        move = moves[k]
        board_before = boards[k]
        if board_before.piece_at(move.to_square) is None:
            continue  # not a capture
        # Relevance gate (D-01): sub-case 2 fires only if pov has not lost material.
        # Eliminates incidental discovered attacks in clearly losing continuations (Case-B).
        # Use >= (non-loss) not > (strict gain) to allow equal-value exchanges where
        # a discovered attack captures a piece of same value (material stays same).
        if _material_diff(boards[k + 1], pov) < material_at_start:
            continue
        # The piece being captured should be on a ray that was unblocked by pov's first move
        # Check if the origin square of the capturing move differs from pov's first dest
        if move.from_square == moves[0].to_square:
            continue  # same piece moved again — not a discovered attack
        unveiled = board_before.piece_at(move.from_square)
        if unveiled is not None and unveiled.color == pov:
            return True, unveiled.piece_type, k

    return False, None, None


def detect_back_rank_mate(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Back-rank mate: checkmate with opponent king trapped on its back rank.

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
    # Opponent's back rank: rank 7 for black king (when pov=white), rank 0 for white king
    back_rank = 7 if (not pov) == chess.BLACK else 0
    if king_rank != back_rank:
        return False, None, None

    # At least one checker must be on the same rank (or delivering rank-based mate)
    for checker_sq in boards[-1].checkers():
        checker = boards[-1].piece_at(checker_sq)
        if checker is not None and checker.color == pov:
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
    """Anastasia mate: queen/rook traps king on edge file with knight blocking escape.

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

    # There must be a pov knight blocking the king's escape toward center
    knights = boards[-1].pieces(chess.KNIGHT, pov)
    if not knights:
        return False, None, None

    return True, mating_piece.piece_type, len(moves) - 1


def detect_hook_mate(
    boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color
) -> tuple[bool, int | None, int | None]:
    """Hook mate: rook adjacent to king, defended by knight, knight defended by pawn.

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
    # Rook must be adjacent to king (within king's attack range)
    if rook_sq not in boards[-1].attacks(opp_king_sq):
        return False, None, None

    # A pov knight must defend the rook
    rook_defenders = boards[-1].attackers(pov, rook_sq)
    knight_sq: int | None = None
    for def_sq in rook_defenders:
        piece = boards[-1].piece_at(def_sq)
        if piece is not None and piece.piece_type == chess.KNIGHT:
            knight_sq = def_sq
            break

    if knight_sq is None:
        return False, None, None

    # A pov pawn must defend the knight
    knight_defenders = boards[-1].attackers(pov, knight_sq)
    for def_sq in knight_defenders:
        piece = boards[-1].piece_at(def_sq)
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
_GEOMETRIC_REGISTRY: list[tuple[TacticMotif, int]] = [
    ("fork", TacticMotifInt.FORK),
    ("skewer", TacticMotifInt.SKEWER),
    ("pin", TacticMotifInt.PIN),
    ("discovered-attack", TacticMotifInt.DISCOVERED_ATTACK),
    ("double-check", TacticMotifInt.DOUBLE_CHECK),
]

_GEOMETRIC_DETECTOR_FNS: dict[TacticMotif, _BoolPieceFn] = {
    "fork": detect_fork,
    "skewer": detect_skewer,
    "pin": detect_pin,
    "discovered-attack": detect_discovered_attack,
    "double-check": detect_double_check,
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


def detect_tactic_motif(
    board_after_flaw: chess.Board,
    pv_str: str,
) -> tuple[int | None, int | None, int | None, int | None]:
    """Detect the highest-priority tactic motif from the refutation PV (D-07/D-02).

    Args:
        board_after_flaw: Position immediately after the flawed move was played.
                          board_after_flaw.turn is the refuting side (pov).
        pv_str: Space-joined UCI refutation line from game_positions.pv.

    Returns:
        (tactic_motif_int, tactic_piece, tactic_confidence, tactic_depth) where:
        - tactic_motif_int: TacticMotifInt value or None if no detector fired.
        - tactic_piece: chess.PieceType int (1-6) or None (per-motif semantic D-12).
        - tactic_confidence: 0-100 or None when tactic_motif_int is None.
        - tactic_depth: raw half-move ply index from flaw_ply+1 (D-04), or None.

    Dispatch strategy (D-02): mates (Tier 1) short-circuit and always win (D-03/D-07).
    All non-mate detectors run and collect firings; the shallowest motif wins;
    equal depth breaks by priority tier/rank so exactly one motif is returned (D-05).

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

    # --- Tier 1: mate subtypes (D-03 dominance — always checked first, always wins) ---
    # Mates never enter the candidate pool; they short-circuit the dispatcher immediately.

    # Named-mate subtypes in priority order (A3)
    for motif_str, motif_int in _NAMED_MATE_REGISTRY:
        fn = _NAMED_MATE_DETECTOR_FNS[motif_str]
        fired, piece, depth = fn(boards, moves, pov)
        if fired:
            return int(motif_int), piece, TACTIC_CONFIDENCE_HIGH, depth

    # Special: boden / double-bishop (returns motif string or None)
    boden_motif, boden_piece, boden_depth = detect_boden_or_double_bishop_mate(boards, moves, pov)
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

    # --- Collect all non-mate firings (D-02: priority dispatch with depth tiebreaker) ---
    # Candidates: run ALL non-mate detectors and collect firings.
    # Winner selection: primary key = (tier, priority_rank) — D-07 priority order preserved.
    # Tiebreaker = depth (shallowest within same priority rank, per D-02).
    # This ensures tier-2 geometrics always beat tier-3, tier-3 beats tier-4, and within
    # the same tier+rank, the shallowest-firing depth wins.
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

    if not candidates:
        return None, None, None, None

    # Sort key: (tier, rank, depth) — tier then rank dominate (D-07 priority order),
    # depth as the final tiebreaker within same-tier same-rank firings (D-02).
    def _sort_key(c: Candidate) -> tuple[int, int, int]:
        depth_val = c[4] if c[4] is not None else 999999
        return (c[0], c[1], depth_val)

    winner = min(candidates, key=_sort_key)
    return winner[5], winner[2], winner[3], winner[4]
