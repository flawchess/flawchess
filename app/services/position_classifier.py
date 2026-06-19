"""Position classification module for FlawChess.

Provides a pure function that accepts a ``chess.Board`` and returns a
``PositionClassification`` dataclass containing:

- ``material_signature`` — canonical string (white pieces _ black pieces)
- ``piece_count`` — count of major+minor pieces (Q+R+B+N) for both sides combined, excluding kings and pawns
- ``backrank_sparse`` — True when < 4 pieces on either side's back rank (Lichess middlegame detection)
- ``mixedness`` — Lichess Divider.scala mixedness score (0..~400)

These four values are computed in-memory to derive ``endgame_class`` (from
``material_signature``) and ``phase`` (from the other three); none of the four
is persisted to ``game_positions`` (SEED-055 dropped the columns).

Game phase is NOT a per-position attribute under Lichess Divider semantics —
it requires the full game ply timeline so the assignment is monotonic
(opening → middlegame → endgame, never back). Use ``assign_game_phases()``
on a per-ply predicate sequence to derive phase values.

Endgame class is derived at query time from material_signature, allowing
threshold tuning without data migration.

No I/O, no DB access, no async.  All computation is deterministic.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import chess

from app.repositories.endgame_repository import ENDGAME_PIECE_COUNT_THRESHOLD

# ---------------------------------------------------------------------------
# Named constants (no magic numbers in conditionals per CLAUDE.md)
# ---------------------------------------------------------------------------

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
    (_SMALL_SQUARE << (x_idx + 8 * y_idx), y_idx + 1) for y_idx in range(7) for x_idx in range(7)
]


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PositionClassification:
    """Classification output for a single chess position.

    All fields are read-only (frozen dataclass).
    """

    material_signature: str  # canonical piece string, white_black format
    piece_count: int  # count of Q+R+B+N for both sides combined (excludes kings and pawns)
    backrank_sparse: bool  # True when < 4 pieces on either side's back rank
    mixedness: int  # Lichess mixedness score (0..~400)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


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


def _compute_material_signature(board: chess.Board) -> str:
    """Return the material signature for *board*.

    Format: ``{white_pieces}_{black_pieces}``

    Always white first, black second — no normalization by material strength.
    This makes signatures directly interpretable in user-perspective queries
    (e.g. filter by played_as color to know which half is "your" pieces).
    """
    return f"{_side_string(board, chess.WHITE)}_{_side_string(board, chess.BLACK)}"


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
        A frozen ``PositionClassification`` dataclass with four fields:
        ``material_signature``, ``piece_count``, ``backrank_sparse``, and
        ``mixedness``. These feed ``endgame_class`` (from ``material_signature``)
        and ``phase`` (from the other three) at import time; none is persisted.

        Game phase (opening/middlegame/endgame) is NOT included — under
        Lichess Divider semantics it requires the full game's ply timeline.
        Pass per-ply ``(piece_count, backrank_sparse, mixedness)`` tuples to
        ``assign_game_phases()`` to derive monotonic phase values.
    """
    material_signature = _compute_material_signature(board)
    piece_count = _compute_piece_count(board)
    backrank_sparse = _compute_backrank_sparse(board)
    mixedness = _compute_mixedness(board)

    return PositionClassification(
        material_signature=material_signature,
        piece_count=piece_count,
        backrank_sparse=backrank_sparse,
        mixedness=mixedness,
    )


def assign_game_phases(
    predicates: Sequence[tuple[int, bool, int]],
) -> list[Literal[0, 1, 2]]:
    """Assign monotonic per-ply game phases per Lichess Divider.scala semantics.

    Reference: https://github.com/lichess-org/scalachess/blob/master/core/src/main/scala/Divider.scala

    Algorithm:
      1. Find ``mid_ply`` — the FIRST ply where the midgame predicate fires
         (piece_count <= 10 OR backrank_sparse OR mixedness > 150).
      2. If ``mid_ply`` is set, find ``end_ply`` — the FIRST ply where
         ``piece_count <= 6``. The endgame search starts from ply 0, NOT from
         ``mid_ply`` — Lichess searches from the beginning.
      3. If ``end_ply`` exists and ``end_ply <= mid_ply``, drop ``mid_ply``
         (Lichess: ``midGame.filter(m => endGame.fold(true)(m < _))``). The
         game then has no middlegame phase — it goes straight from opening
         to endgame.
      4. Assign phase per ply by ply-range membership:
           ``ply < mid_ply`` → 0 (opening)
           ``mid_ply <= ply < end_ply`` → 1 (middlegame)
           ``ply >= end_ply`` → 2 (endgame)
         Once a game enters middlegame it can never return to opening, even
         if pieces re-occupy the back rank or mixedness drops below 150.

    Args:
        predicates: per-ply ``(piece_count, backrank_sparse, mixedness)``
            tuples in ply order, starting from ply 0.

    Returns:
        A list of phase values (0/1/2), one per input tuple.
    """
    n = len(predicates)
    if n == 0:
        return []

    mid_ply: int | None = None
    for i, (piece_count, backrank_sparse, mixedness) in enumerate(predicates):
        if is_middlegame(piece_count, backrank_sparse, mixedness):
            mid_ply = i
            break

    end_ply: int | None = None
    if mid_ply is not None:
        for i, (piece_count, _, _) in enumerate(predicates):
            if is_endgame(piece_count):
                end_ply = i
                break
        # Lichess: midGame.filter(m => endGame.fold(true)(m < _))
        # If endgame fires at or before midgame, drop midgame entirely.
        if end_ply is not None and mid_ply >= end_ply:
            mid_ply = None

    phases: list[Literal[0, 1, 2]] = []
    for i in range(n):
        if end_ply is not None and i >= end_ply:
            phases.append(2)
        elif mid_ply is not None and i >= mid_ply:
            phases.append(1)
        else:
            phases.append(0)
    return phases
