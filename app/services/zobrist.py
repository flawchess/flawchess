"""Zobrist hash computation module for Chessalytics.

Provides three deterministic 64-bit hashes for any chess position:

- ``white_hash`` — hash of white pieces only (ignores black piece placement)
- ``black_hash`` — hash of black pieces only (ignores white piece placement)
- ``full_hash`` — hash of the complete position (via python-chess polyglot)

All values are converted to signed 64-bit integers so they are safe to store
in PostgreSQL BIGINT columns.
"""

import ctypes
import io

import chess
import chess.pgn
import chess.polyglot

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _color_hash(board: chess.Board, color: chess.Color) -> int:
    """Compute a Zobrist hash for the pieces of a single color.

    Uses the same POLYGLOT_RANDOM_ARRAY as the built-in polyglot hasher so
    that individual color hashes combine compatibly with ``full_hash``.

    The indexing scheme mirrors the polyglot standard::

        index = 64 * ((piece_type - 1) * 2 + color_pivot) + square

    where ``color_pivot`` is 0 for WHITE and 1 for BLACK (i.e. white pieces
    occupy the even entries for each piece type, black the odd ones).

    The XOR result is an unsigned 64-bit integer; we convert to a signed
    Python int via ``ctypes.c_int64`` so the value fits in BIGINT.
    """
    color_pivot = 0 if color == chess.WHITE else 1
    h: int = 0
    for square in chess.scan_forward(board.occupied_co[color]):
        piece = board.piece_at(square)
        if piece is None:
            continue
        # piece_type is 1-6 (PAWN … KING)
        index = 64 * ((piece.piece_type - 1) * 2 + color_pivot) + square
        h ^= chess.polyglot.POLYGLOT_RANDOM_ARRAY[index]
    return ctypes.c_int64(h).value


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_hashes(board: chess.Board) -> tuple[int, int, int]:
    """Return ``(white_hash, black_hash, full_hash)`` for *board*.

    All three values are signed 64-bit integers compatible with PostgreSQL
    BIGINT storage.  The computation is deterministic: identical board states
    always yield identical hashes.

    Args:
        board: Any ``chess.Board`` instance (starting position, mid-game, etc.)

    Returns:
        A 3-tuple ``(white_hash, black_hash, full_hash)``.
    """
    white_hash = _color_hash(board, chess.WHITE)
    black_hash = _color_hash(board, chess.BLACK)
    full_hash = ctypes.c_int64(chess.polyglot.zobrist_hash(board)).value
    return white_hash, black_hash, full_hash


def hashes_for_game(pgn_text: str) -> list[tuple[int, int, int, int]]:
    """Parse *pgn_text* and return hashes for every half-move including ply 0.

    Each entry is a 4-tuple ``(ply, white_hash, black_hash, full_hash)`` where
    ``ply`` starts at 0 (the initial position before any move is played).

    For PGN ``"1. e4 e5 2. Nf3 *"`` the function returns 5 entries (ply 0-4).

    Args:
        pgn_text: A PGN-formatted string.  May contain a single game.

    Returns:
        A list of ``(ply, white_hash, black_hash, full_hash)`` tuples, or an
        empty list when *pgn_text* is empty, unparseable, or contains no moves.
    """
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        return []

    if game is None:
        return []

    moves = list(game.mainline_moves())
    if not moves:
        return []

    results: list[tuple[int, int, int, int]] = []
    board = game.board()

    # ply 0 — initial position (before any move is played)
    wh, bh, fh = compute_hashes(board)
    results.append((0, wh, bh, fh))

    for ply, move in enumerate(moves, start=1):
        board.push(move)
        wh, bh, fh = compute_hashes(board)
        results.append((ply, wh, bh, fh))

    return results
