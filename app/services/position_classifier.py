"""Position classification module for FlawChess.

Provides a pure function that accepts a ``chess.Board`` and returns a
``PositionClassification`` dataclass containing:

- ``material_count`` — total centipawns both sides (white + black, including pawns)
- ``material_signature`` — canonical string (white pieces _ black pieces)
- ``material_imbalance`` — signed centipawns (white minus black)
- ``has_opposite_color_bishops`` — True if each side has exactly 1 bishop on different square colors
- ``piece_count`` — count of major+minor pieces (Q+R+B+N) for both sides combined, excluding kings and pawns

Game phase (opening/middlegame/endgame) and endgame class are derived at query
time from material_count + ply + material_signature + piece_count, allowing
threshold tuning without data migration.

No I/O, no DB access, no async.  All computation is deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass

import chess

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
        A frozen ``PositionClassification`` dataclass with five fields:
        ``material_count``, ``material_signature``, ``material_imbalance``,
        ``has_opposite_color_bishops``, and ``piece_count``.
    """
    return PositionClassification(
        material_count=_compute_material_count(board),
        material_signature=_compute_material_signature(board),
        material_imbalance=_compute_material_imbalance(board),
        has_opposite_color_bishops=_compute_opposite_color_bishops(board),
        piece_count=_compute_piece_count(board),
    )
