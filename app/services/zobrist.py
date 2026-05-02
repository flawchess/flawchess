"""Zobrist hash computation module for FlawChess.

Provides three deterministic 64-bit hashes for any chess position:

- ``white_hash`` — hash of white pieces only (ignores black piece placement)
- ``black_hash`` — hash of black pieces only (ignores white piece placement)
- ``full_hash`` — hash of the complete position (via python-chess polyglot)

All values are converted to signed 64-bit integers so they are safe to store
in PostgreSQL BIGINT columns.
"""

import ctypes
import io
from typing import TypedDict

import chess
import chess.pgn
import chess.polyglot
import sentry_sdk

from app.repositories.endgame_repository import ENDGAME_PIECE_COUNT_THRESHOLD
from app.services.endgame_service import _CLASS_TO_INT, classify_endgame_class
from app.services.position_classifier import classify_position


# ---------------------------------------------------------------------------
# TypedDicts for unified PGN processing
# ---------------------------------------------------------------------------


class PlyData(TypedDict):
    """Per-ply data returned by process_game_pgn.

    Contains all data needed for a single game_positions row, computed in
    a single PGN mainline walk (eliminates the triple-parse bottleneck D-01/D-02).
    """

    ply: int
    white_hash: int
    black_hash: int
    full_hash: int
    move_san: str | None
    clock_seconds: float | None
    eval_cp: int | None
    eval_mate: int | None
    material_count: int
    material_signature: str
    material_imbalance: int
    has_opposite_color_bishops: bool
    piece_count: int
    backrank_sparse: bool
    mixedness: int
    endgame_class: int | None
    phase: int  # 0=opening, 1=middlegame, 2=endgame; lichess Divider.scala (D-79-07)


class GameProcessingResult(TypedDict):
    """Game-level result returned by process_game_pgn.

    Contains the list of per-ply data plus game-level aggregates derived
    from the same single PGN parse.
    """

    plies: list[PlyData]
    result_fen: str | None
    move_count: int


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
# Eval plausibility bounds — values beyond these are clamped to the bound.
# Both columns are SMALLINT (±32767); the bounds are tighter than int16
# because evals beyond these magnitudes are never meaningful (the engine has
# already transitioned to mate scores). Clamping (vs nulling) preserves the
# sign so a corrupt-but-directionally-correct annotation still indicates
# which side was winning.
# ---------------------------------------------------------------------------

EVAL_CP_MAX_ABS = 10000  # ±100 pawns
EVAL_MATE_MAX_ABS = 200  # no realistic mate-in-N exceeds this


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


def process_game_pgn(pgn_text: str) -> GameProcessingResult | None:
    """Parse pgn_text and return all per-ply data from a single mainline walk.

    Replaces the triple-PGN-parse pattern (D-01). Walks the mainline once,
    computing hashes, classification, eval, clock, and move SAN for each ply.
    Also derives move_count and result_fen (D-02).

    Returns None for empty, unparseable, or moveless PGNs.

    Args:
        pgn_text: A PGN-formatted string. May contain a single game.

    Returns:
        A ``GameProcessingResult`` TypedDict with ``plies`` (list of ``PlyData``),
        ``result_fen``, and ``move_count``. Returns ``None`` when *pgn_text* is
        empty, unparseable, or contains no moves.
    """
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except Exception:
        sentry_sdk.capture_exception()
        return None

    if game is None:
        return None

    nodes = list(game.mainline())
    if not nodes:
        return None

    board = game.board()
    plies: list[PlyData] = []

    for ply, node in enumerate(nodes):
        # 1. Pre-push: hashes from current board state
        wh, bh, fh = compute_hashes(board)
        # 2. Pre-push: classification from current board state
        classification = classify_position(board)
        # 3. Pre-push: move SAN (board must be in pre-move state)
        move_san: str = board.san(node.move)
        # 4. On node: clock annotation
        clock_seconds: float | None = node.clock()
        # 5. On node: eval annotation (eval of position AFTER this move, stored on the move node)
        eval_cp: int | None = None
        eval_mate: int | None = None
        pov = node.eval()
        if pov is not None:
            w = pov.white()
            eval_cp = w.score(mate_score=None)
            eval_mate = w.mate()
            # Corrupt PGNs occasionally annotate evals with implausibly large
            # values (e.g. eval_mate=-1002411246) which overflow the SMALLINT
            # column and crash the whole batch INSERT. Clamp to plausible
            # bounds so a single bad annotation cannot poison ingest, while
            # preserving the sign (which side was winning).
            if eval_cp is not None:
                eval_cp = max(-EVAL_CP_MAX_ABS, min(EVAL_CP_MAX_ABS, eval_cp))
            if eval_mate is not None:
                eval_mate = max(-EVAL_MATE_MAX_ABS, min(EVAL_MATE_MAX_ABS, eval_mate))

        # Compute endgame_class for endgame positions (piece_count <= threshold)
        endgame_class: int | None = None
        if classification.piece_count <= ENDGAME_PIECE_COUNT_THRESHOLD:
            ec_str = classify_endgame_class(classification.material_signature)
            endgame_class = _CLASS_TO_INT[ec_str]

        # 6. Advance board to next ply
        board.push(node.move)

        plies.append(
            PlyData(
                ply=ply,
                white_hash=wh,
                black_hash=bh,
                full_hash=fh,
                move_san=move_san,
                clock_seconds=clock_seconds,
                eval_cp=eval_cp,
                eval_mate=eval_mate,
                material_count=classification.material_count,
                material_signature=classification.material_signature,
                material_imbalance=classification.material_imbalance,
                has_opposite_color_bishops=classification.has_opposite_color_bishops,
                piece_count=classification.piece_count,
                backrank_sparse=classification.backrank_sparse,
                mixedness=classification.mixedness,
                endgame_class=endgame_class,
                phase=classification.phase,
            )
        )

    # Final position: no move is played from here
    wh, bh, fh = compute_hashes(board)
    classification = classify_position(board)
    endgame_class_final: int | None = None
    if classification.piece_count <= ENDGAME_PIECE_COUNT_THRESHOLD:
        ec_str_final = classify_endgame_class(classification.material_signature)
        endgame_class_final = _CLASS_TO_INT[ec_str_final]

    plies.append(
        PlyData(
            ply=len(nodes),
            white_hash=wh,
            black_hash=bh,
            full_hash=fh,
            move_san=None,
            clock_seconds=None,
            eval_cp=None,
            eval_mate=None,
            material_count=classification.material_count,
            material_signature=classification.material_signature,
            material_imbalance=classification.material_imbalance,
            has_opposite_color_bishops=classification.has_opposite_color_bishops,
            piece_count=classification.piece_count,
            backrank_sparse=classification.backrank_sparse,
            mixedness=classification.mixedness,
            endgame_class=endgame_class_final,
            phase=classification.phase,
        )
    )

    result_fen = board.board_fen()
    move_count = (len(nodes) + 1) // 2

    return GameProcessingResult(
        plies=plies,
        result_fen=result_fen,
        move_count=move_count,
    )


def hashes_for_game(
    pgn_text: str,
) -> tuple[list[tuple[int, int, int, int, str | None, float | None]], str | None]:
    """Parse *pgn_text* and return hashes for every half-move including ply 0.

    Each entry is a 6-tuple ``(ply, white_hash, black_hash, full_hash, move_san, clock_seconds)``
    where ``ply`` starts at 0 (the initial position before any move is played).

    ``move_san`` is the SAN of the move played FROM position at ``ply`` (leading
    to ply+1).  The final position row always has ``move_san=None`` because no
    move is played from it.  Ply-0 has the SAN of the first move for games with moves.

    ``clock_seconds`` is the clock time remaining (in seconds) extracted from
    ``%clk`` PGN annotations on the move node, or ``None`` if not present.
    The final position row always has ``clock_seconds=None``.

    For PGN ``"1. e4 e5 2. Nf3 *"`` the function returns 4 entries (ply 0-3):
        - (0, wh, bh, fh, "e4", None)
        - (1, wh, bh, fh, "e5", None)
        - (2, wh, bh, fh, "Nf3", None)
        - (3, wh, bh, fh, None, None)

    Args:
        pgn_text: A PGN-formatted string.  May contain a single game.

    Returns:
        A 2-tuple ``(hash_tuples, result_fen)`` where ``hash_tuples`` is a list of
        ``(ply, white_hash, black_hash, full_hash, move_san, clock_seconds)`` tuples
        and ``result_fen`` is the piece-placement FEN of the final position
        (``board.board_fen()``).  Both are ``([], None)`` when *pgn_text* is empty,
        unparseable, or contains no moves.
    """
    result = process_game_pgn(pgn_text)
    if result is None:
        return [], None
    hash_tuples: list[tuple[int, int, int, int, str | None, float | None]] = [
        (
            p["ply"],
            p["white_hash"],
            p["black_hash"],
            p["full_hash"],
            p["move_san"],
            p["clock_seconds"],
        )
        for p in result["plies"]
    ]
    return hash_tuples, result["result_fen"]
