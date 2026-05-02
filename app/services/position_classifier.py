"""Position classification module for FlawChess.

Provides a pure function that accepts a ``chess.Board`` and returns a
``PositionClassification`` dataclass containing:

- ``material_count`` — total centipawns both sides (white + black, including pawns)
- ``material_signature`` — canonical string (white pieces _ black pieces)
- ``material_imbalance`` — signed centipawns (white minus black)
- ``has_opposite_color_bishops`` — True if each side has exactly 1 bishop on different square colors
- ``piece_count`` — count of major+minor pieces (Q+R+B+N) for both sides combined, excluding kings and pawns
- ``backrank_sparse`` — True when < 4 pieces on either side's back rank (Lichess middlegame detection)
- ``mixedness`` — Lichess Divider.scala mixedness score (0..~400)
- ``phase`` — game phase per lichess Divider.scala (0=opening, 1=middlegame, 2=endgame)

Game phase (opening/middlegame/endgame) is derived at classification time from
piece_count, backrank_sparse, and mixedness via the lichess Divider.scala predicates.
Endgame class is derived at query time from material_signature, allowing threshold
tuning without data migration.

No I/O, no DB access, no async.  All computation is deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import chess

from app.repositories.endgame_repository import ENDGAME_PIECE_COUNT_THRESHOLD

# ---------------------------------------------------------------------------
# Named constants (no magic numbers in conditionals per CLAUDE.md)
# ---------------------------------------------------------------------------

# Centipawn piece values for material_count and imbalance computation
# (includes pawns — material_count is total material on both sides)

# Centipawn piece values for material imbalance and signature ordering
_MATERIAL_VALUE_CP: dict[int, int] = {
    chess.PAWN: 100,
    chess.KNIGHT: 300,
    chess.BISHOP: 300,
    chess.ROOK: 500,
    chess.QUEEN: 900,
}

# Piece order within a side's signature string (descending value, standard notation)
_SIGNATURE_ORDER: list[int] = [
    chess.QUEEN,
    chess.ROOK,
    chess.BISHOP,
    chess.KNIGHT,
    chess.PAWN,
]

# Single-letter abbreviations for signature strings
_SIGNATURE_LETTER: dict[int, str] = {
    chess.QUEEN: "Q",
    chess.ROOK: "R",
    chess.BISHOP: "B",
    chess.KNIGHT: "N",
    chess.PAWN: "P",
}

# Backrank sparseness threshold: if either side has fewer than this many pieces
# on their back rank, the position is considered "backrank sparse".
BACKRANK_SPARSE_THRESHOLD = 4

# Lichess Divider.scala default: middlegame iff majors+minors piece_count <= 10.
MIDGAME_MAJORS_AND_MINORS_THRESHOLD = 10

# Lichess Divider.scala default: middlegame iff mixedness > 150.
MIDGAME_MIXEDNESS_THRESHOLD = 150

# ---------------------------------------------------------------------------
# Mixedness precomputed tables (Lichess Divider.scala algorithm)
# ---------------------------------------------------------------------------

# 2x2 sliding window anchor bitboard (a1-b1-a2-b2 square mask)
_SMALL_SQUARE = 0x0303

# 49 overlapping 2x2 regions: list of (mask, y) where y is the 1-based rank of
# the bottom-left corner of the region (1..7). Used by _compute_mixedness.
_MIXEDNESS_REGIONS: list[tuple[int, int]] = [
    (_SMALL_SQUARE << (x_idx + 8 * y_idx), y_idx + 1)
    for y_idx in range(7)
    for x_idx in range(7)
]


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PositionClassification:
    """Classification output for a single chess position.

    All fields are read-only (frozen dataclass).
    """

    material_count: int  # total centipawns both sides (white + black, including pawns)
    material_signature: str  # canonical piece string, white_black format
    material_imbalance: int  # white_material - black_material in centipawns
    has_opposite_color_bishops: bool
    piece_count: int  # count of Q+R+B+N for both sides combined (excludes kings and pawns)
    backrank_sparse: bool  # True when < 4 pieces on either side's back rank
    mixedness: int  # Lichess mixedness score (0..~400)
    phase: Literal[0, 1, 2]  # 0=opening, 1=middlegame, 2=endgame; lichess Divider.scala


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_material_count(board: chess.Board) -> int:
    """Return total material in centipawns for both sides combined (including pawns).

    Starting position: each side has 8P+2N+2B+2R+Q = 800+600+600+1000+900 = 3900,
    so the combined starting count is 7800.

    This raw value is stored in the DB. Game phase labels (opening/middlegame/endgame)
    are derived at query time from material_count + ply, allowing threshold tuning
    without data migration.
    """
    return _side_material(board, chess.WHITE) + _side_material(board, chess.BLACK)


def _side_string(board: chess.Board, color: chess.Color) -> str:
    """Build the piece string for one side in signature format.

    Always starts with 'K', followed by piece letters in ``_SIGNATURE_ORDER``,
    each repeated once per piece count.  Example: 'KQRRBBNNPPPPPPPP'.
    """
    parts = ["K"]
    for piece_type in _SIGNATURE_ORDER:
        count = len(board.pieces(piece_type, color))
        letter = _SIGNATURE_LETTER[piece_type]
        parts.append(letter * count)
    return "".join(parts)


def _side_material(board: chess.Board, color: chess.Color) -> int:
    """Return total centipawn material for *color* (excludes king).

    Uses ``_MATERIAL_VALUE_CP`` for piece values.
    """
    total = 0
    for piece_type, value in _MATERIAL_VALUE_CP.items():
        count = len(board.pieces(piece_type, color))
        total += count * value
    return total


def _compute_material_signature(board: chess.Board) -> str:
    """Return the material signature for *board*.

    Format: ``{white_pieces}_{black_pieces}``

    Always white first, black second — no normalization by material strength.
    This makes signatures directly interpretable in user-perspective queries
    (e.g. filter by played_as color to know which half is "your" pieces).
    """
    return f"{_side_string(board, chess.WHITE)}_{_side_string(board, chess.BLACK)}"


def _compute_material_imbalance(board: chess.Board) -> int:
    """Return signed material imbalance in centipawns.

    Positive: white has more material.
    Negative: black has more material.
    """
    return _side_material(board, chess.WHITE) - _side_material(board, chess.BLACK)


def _compute_piece_count(board: chess.Board) -> int:
    """Return the count of major and minor pieces (Q+R+B+N) for both sides combined.

    Kings and pawns are excluded from the count. This is the Lichess endgame definition:
    a position is an endgame when piece_count <= ENDGAME_PIECE_COUNT_THRESHOLD.

    Starting position has 7 major+minor pieces per side (Q+R+R+B+B+N+N), total = 14.
    K vs K = 0. KR vs KR = 2.
    """
    # Piece types that count toward endgame classification (excludes KING and PAWN)
    _COUNTED_PIECE_TYPES = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]

    total = 0
    for piece_type in _COUNTED_PIECE_TYPES:
        total += len(board.pieces(piece_type, chess.WHITE))
        total += len(board.pieces(piece_type, chess.BLACK))
    return total


def _compute_opposite_color_bishops(board: chess.Board) -> bool:
    """Return True if each side has exactly one bishop on different square colors.

    Uses ``chess.BB_DARK_SQUARES`` to determine which squares are dark.
    Bishops on light squares occupy squares NOT in BB_DARK_SQUARES.
    """
    white_bishops = list(board.pieces(chess.BISHOP, chess.WHITE))
    black_bishops = list(board.pieces(chess.BISHOP, chess.BLACK))

    # Both sides must have exactly one bishop
    if len(white_bishops) != 1 or len(black_bishops) != 1:
        return False

    white_sq = white_bishops[0]
    black_sq = black_bishops[0]

    # Determine bishop colors using dark-square bitboard
    white_on_dark = bool(chess.BB_DARK_SQUARES & chess.BB_SQUARES[white_sq])
    black_on_dark = bool(chess.BB_DARK_SQUARES & chess.BB_SQUARES[black_sq])

    # Opposite colors: one is on dark, the other on light
    return white_on_dark != black_on_dark


def _compute_backrank_sparse(board: chess.Board) -> bool:
    """Return True if either side has fewer than BACKRANK_SPARSE_THRESHOLD pieces on their back rank.

    White's back rank is rank 1 (BB_RANK_1); black's back rank is rank 8 (BB_RANK_8).
    A position is backrank sparse when a side has evacuated most of their back rank —
    one component of the Lichess middlegame phase detection algorithm.
    """
    white_backrank_count = bin(board.occupied_co[chess.WHITE] & chess.BB_RANK_1).count("1")
    black_backrank_count = bin(board.occupied_co[chess.BLACK] & chess.BB_RANK_8).count("1")
    return (
        white_backrank_count < BACKRANK_SPARSE_THRESHOLD
        or black_backrank_count < BACKRANK_SPARSE_THRESHOLD
    )


def is_endgame(piece_count: int) -> bool:
    """Lichess Divider.scala isEndGame predicate.

    True iff piece_count <= ENDGAME_PIECE_COUNT_THRESHOLD (default 6).
    """
    return piece_count <= ENDGAME_PIECE_COUNT_THRESHOLD


def is_middlegame(piece_count: int, backrank_sparse: bool, mixedness: int) -> bool:
    """Lichess Divider.scala isMidGame predicate.

    True iff piece_count <= MIDGAME_MAJORS_AND_MINORS_THRESHOLD (default 10)
    OR backrank_sparse OR mixedness > MIDGAME_MIXEDNESS_THRESHOLD (default 150).

    Note: caller must check is_endgame FIRST so the endgame case wins when both fire.
    """
    return (
        piece_count <= MIDGAME_MAJORS_AND_MINORS_THRESHOLD
        or backrank_sparse
        or mixedness > MIDGAME_MIXEDNESS_THRESHOLD
    )


def _mixedness_score(y: int, white: int, black: int) -> int:
    """Return the mixedness contribution for a 2x2 region.

    Transcribed from Lichess Divider.scala. y is the 1-based rank of the
    bottom-left corner of the region. white and black are piece counts (0..4)
    of each color within the 2x2 region.
    """
    match (white, black):
        case (0, 0):
            return 0
        case (1, 0):
            return 1 + (8 - y)
        case (2, 0):
            return (2 + (y - 2)) if y > 2 else 0
        case (3, 0):
            return (3 + (y - 1)) if y > 1 else 0
        case (4, 0):
            return (3 + (y - 1)) if y > 1 else 0
        case (0, 1):
            return 1 + y
        case (1, 1):
            return 5 + abs(4 - y)
        case (2, 1):
            return 4 + (y - 1)
        case (3, 1):
            return 5 + (y - 1)
        case (0, 2):
            return (2 + (6 - y)) if y < 6 else 0
        case (1, 2):
            return 4 + (7 - y)
        case (2, 2):
            return 7
        case (0, 3):
            return (3 + (7 - y)) if y < 7 else 0
        case (1, 3):
            return 5 + (7 - y)
        case (0, 4):
            return (3 + (7 - y)) if y < 7 else 0
        case _:
            return 0


def _compute_mixedness(board: chess.Board) -> int:
    """Return the Lichess mixedness score for *board*.

    Iterates over 49 overlapping 2x2 regions (precomputed in _MIXEDNESS_REGIONS),
    computing white_count and black_count of pieces within each region and
    accumulating the score from _mixedness_score.

    Uses bin(bb).count('1') for popcount — portable across python-chess versions.
    """
    score = 0
    white_occ = board.occupied_co[chess.WHITE]
    black_occ = board.occupied_co[chess.BLACK]
    for mask, y in _MIXEDNESS_REGIONS:
        white_count = bin(white_occ & mask).count("1")
        black_count = bin(black_occ & mask).count("1")
        score += _mixedness_score(y, white_count, black_count)
    return score


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_position(board: chess.Board) -> PositionClassification:
    """Classify *board* and return metadata about the chess position.

    This is a pure synchronous function with no I/O, no DB access, and no
    async machinery.  It does not modify *board*.

    Args:
        board: Any ``chess.Board`` instance.

    Returns:
        A frozen ``PositionClassification`` dataclass with eight fields:
        ``material_count``, ``material_signature``, ``material_imbalance``,
        ``has_opposite_color_bishops``, ``piece_count``,
        ``backrank_sparse``, ``mixedness``, and ``phase``
        (0=opening, 1=middlegame, 2=endgame per lichess Divider.scala).
    """
    material_count = _compute_material_count(board)
    material_signature = _compute_material_signature(board)
    material_imbalance = _compute_material_imbalance(board)
    has_opposite_color_bishops = _compute_opposite_color_bishops(board)
    piece_count = _compute_piece_count(board)
    backrank_sparse = _compute_backrank_sparse(board)
    mixedness = _compute_mixedness(board)

    # Phase 79 CLASS-02: derive phase from already-computed inputs (no second board scan).
    # is_endgame is checked first so PHASE-INV-01 (phase=2 ⟺ endgame_class IS NOT NULL)
    # holds by construction (per D-79-06).
    phase: Literal[0, 1, 2]
    if is_endgame(piece_count):
        phase = 2
    elif is_middlegame(piece_count, backrank_sparse, mixedness):
        phase = 1
    else:
        phase = 0

    return PositionClassification(
        material_count=material_count,
        material_signature=material_signature,
        material_imbalance=material_imbalance,
        has_opposite_color_bishops=has_opposite_color_bishops,
        piece_count=piece_count,
        backrank_sparse=backrank_sparse,
        mixedness=mixedness,
        phase=phase,
    )
