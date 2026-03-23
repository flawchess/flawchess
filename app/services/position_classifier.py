"""Position classification module for FlawChess.

Provides a pure function that accepts a ``chess.Board`` and returns a
``PositionClassification`` dataclass containing:

- ``game_phase`` — 'opening', 'middlegame', or 'endgame'
- ``material_signature`` — canonical string (stronger side first)
- ``material_imbalance`` — signed centipawns (white minus black)
- ``endgame_class`` — category string or None for non-endgame positions
- ``has_bishop_pair_white`` — True if white has 2+ bishops
- ``has_bishop_pair_black`` — True if black has 2+ bishops
- ``has_opposite_color_bishops`` — True if each side has exactly 1 bishop on different square colors

No I/O, no DB access, no async.  All computation is deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import chess

# ---------------------------------------------------------------------------
# Named constants (no magic numbers in conditionals per CLAUDE.md)
# ---------------------------------------------------------------------------

# Phase score weights — non-pawn, non-king pieces only (standard engine values)
_PHASE_WEIGHT: dict[int, int] = {
    chess.QUEEN: 9,
    chess.ROOK: 5,
    chess.BISHOP: 3,
    chess.KNIGHT: 3,
}

# Phase thresholds
_OPENING_THRESHOLD = 50  # phase_score >= 50  -> opening
_ENDGAME_THRESHOLD = 25  # phase_score < 25   -> endgame  (25 <= score < 50 -> middlegame)

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

    game_phase: str  # 'opening' | 'middlegame' | 'endgame'
    material_signature: str  # canonical piece string, stronger side first
    material_imbalance: int  # white_material - black_material in centipawns
    endgame_class: Optional[str]  # None for non-endgame; else category string
    has_bishop_pair_white: bool
    has_bishop_pair_black: bool
    has_opposite_color_bishops: bool


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_phase_score(board: chess.Board) -> int:
    """Return the phase score for *board*.

    The phase score is the sum of non-pawn, non-king piece weights for BOTH
    sides combined.  Uses ``_PHASE_WEIGHT`` to weight each piece type.

    Starting position: each side contributes 2N+2B+2R+Q = 6+6+10+9 = 31,
    so the combined starting score is 62.
    """
    score = 0
    for color in (chess.WHITE, chess.BLACK):
        for piece_type, weight in _PHASE_WEIGHT.items():
            count = len(board.pieces(piece_type, color))
            score += count * weight
    return score


def _compute_game_phase(board: chess.Board) -> str:
    """Classify the board into 'opening', 'middlegame', or 'endgame'.

    Thresholds (based on material-weight scoring, per D-01):
    - phase_score >= _OPENING_THRESHOLD (50) -> 'opening'
    - phase_score >= _ENDGAME_THRESHOLD (25) -> 'middlegame'
    - phase_score <  _ENDGAME_THRESHOLD (25) -> 'endgame'
    """
    phase_score = _compute_phase_score(board)
    if phase_score >= _OPENING_THRESHOLD:
        return "opening"
    if phase_score >= _ENDGAME_THRESHOLD:
        return "middlegame"
    return "endgame"


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
    """Return the canonical material signature for *board*.

    Format: ``{stronger_side_string}_{weaker_side_string}``

    Canonical ordering rules (per D-02):
    1. The side with more total material goes first.
    2. If material is equal, the lexicographically smaller string goes first.

    This ensures the same physical position always produces the same signature
    regardless of which side happens to be white or black.
    """
    white_str = _side_string(board, chess.WHITE)
    black_str = _side_string(board, chess.BLACK)
    white_mat = _side_material(board, chess.WHITE)
    black_mat = _side_material(board, chess.BLACK)

    if white_mat > black_mat:
        return f"{white_str}_{black_str}"
    if black_mat > white_mat:
        return f"{black_str}_{white_str}"
    # Equal material: lexicographic tie-break (smaller string first)
    if white_str <= black_str:
        return f"{white_str}_{black_str}"
    return f"{black_str}_{white_str}"


def _compute_material_imbalance(board: chess.Board) -> int:
    """Return signed material imbalance in centipawns.

    Positive: white has more material.
    Negative: black has more material.
    """
    return _side_material(board, chess.WHITE) - _side_material(board, chess.BLACK)


def _compute_endgame_class(board: chess.Board) -> str:
    """Classify the endgame type using a priority chain (per D-04).

    Priority order:
    1. pawn       — only kings and pawns (no pieces at all)
    2. pawnless   — no pawns for either side (any piece combination)
    3. rook       — rook(s) + possibly pawns, no queens/bishops/knights
    4. minor_piece — bishop(s)/knight(s) + possibly pawns, no rooks/queens
    5. queen      — queen(s) + possibly pawns, no rooks/bishops/knights
    6. mixed      — catch-all (multiple piece types)

    Called only when game_phase == 'endgame'.
    """
    has_white_queen = len(board.pieces(chess.QUEEN, chess.WHITE)) > 0
    has_black_queen = len(board.pieces(chess.QUEEN, chess.BLACK)) > 0
    has_white_rook = len(board.pieces(chess.ROOK, chess.WHITE)) > 0
    has_black_rook = len(board.pieces(chess.ROOK, chess.BLACK)) > 0
    has_white_bishop = len(board.pieces(chess.BISHOP, chess.WHITE)) > 0
    has_black_bishop = len(board.pieces(chess.BISHOP, chess.BLACK)) > 0
    has_white_knight = len(board.pieces(chess.KNIGHT, chess.WHITE)) > 0
    has_black_knight = len(board.pieces(chess.KNIGHT, chess.BLACK)) > 0
    has_white_pawn = len(board.pieces(chess.PAWN, chess.WHITE)) > 0
    has_black_pawn = len(board.pieces(chess.PAWN, chess.BLACK)) > 0

    has_any_queen = has_white_queen or has_black_queen
    has_any_rook = has_white_rook or has_black_rook
    has_any_bishop = has_white_bishop or has_black_bishop
    has_any_knight = has_white_knight or has_black_knight
    has_any_pawn = has_white_pawn or has_black_pawn
    has_any_minor = has_any_bishop or has_any_knight
    has_any_piece = has_any_queen or has_any_rook or has_any_minor

    # Priority 1: only kings and pawns (no pieces of any kind, at least one pawn)
    # Note: bare kings (K vs K) falls through to priority 2 (pawnless)
    if not has_any_piece and has_any_pawn:
        return "pawn"

    # Priority 2: no pawns at all (any piece combination is pawnless, including bare kings)
    if not has_any_pawn:
        return "pawnless"

    # Priority 3: rooks (+ possibly pawns), no queens/bishops/knights
    if has_any_rook and not has_any_queen and not has_any_minor:
        return "rook"

    # Priority 4: minor pieces (+ possibly pawns), no rooks/queens
    if has_any_minor and not has_any_rook and not has_any_queen:
        return "minor_piece"

    # Priority 5: queens (+ possibly pawns), no rooks/bishops/knights
    if has_any_queen and not has_any_rook and not has_any_minor:
        return "queen"

    # Priority 6: catch-all
    return "mixed"


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
        A frozen ``PositionClassification`` dataclass with seven fields:
        ``game_phase``, ``material_signature``, ``material_imbalance``,
        ``endgame_class``, ``has_bishop_pair_white``, ``has_bishop_pair_black``,
        and ``has_opposite_color_bishops``.
    """
    game_phase = _compute_game_phase(board)

    # endgame_class is only meaningful in endgame positions
    endgame_class: Optional[str] = (
        _compute_endgame_class(board) if game_phase == "endgame" else None
    )

    return PositionClassification(
        game_phase=game_phase,
        material_signature=_compute_material_signature(board),
        material_imbalance=_compute_material_imbalance(board),
        endgame_class=endgame_class,
        has_bishop_pair_white=len(board.pieces(chess.BISHOP, chess.WHITE)) >= 2,
        has_bishop_pair_black=len(board.pieces(chess.BISHOP, chess.BLACK)) >= 2,
        has_opposite_color_bishops=_compute_opposite_color_bishops(board),
    )
