"""Deterministic Maia fakes shared by the Phase 247 tests (helper, not a test module).

Plans 02-05 monkeypatch ``maia_flaw_scoring.full_policy`` with ``fake_full_policy``
when a test sets ``maia_engine._session`` to an ``object()`` sentinel, so DB-backed
tests exercise the scorer without a real ORT session.
"""

from __future__ import annotations

import io

import chess
import chess.pgn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.repositories.game_flaws_repository import FACEPALM_COLUMNS
from app.repositories.query_utils import mover_is_white_at_ply

# game_flaws.severity value of a blunder (game_flaws_repository._SEVERITY_INT).
_BLUNDER_SEVERITY = 2


def fake_full_policy(fen: str, elo: float) -> dict[str, float]:
    """Deterministic stand-in for ``maia_engine.full_policy``.

    Covers exactly the position's legal moves, sorted by UCI, with weights
    n, n-1, ..., 1 normalized to sum 1: every legal move gets a distinct value
    (distinct ranks) and the result is independent of ``elo``.
    """
    ucis = sorted(move.uci() for move in chess.Board(fen).legal_moves)
    n = len(ucis)
    total = n * (n + 1) / 2
    return {uci: (n - i) / total for i, uci in enumerate(ucis)}


async def assert_refutation_lane_state(
    maker: async_sessionmaker[AsyncSession], game_id: int, *, expect_stamped: bool = True
) -> int:
    """Phase 248 lane assertions shared by the drain and endpoint tests (D-07).

    Phase 250 D-07: the same post-apply hook scores the facepalm values in every lane, so this
    helper also proves them. Reads the game back and checks: all four completion stamps (the
    two Maia stamps and the two facepalm stamps) set, or all NULL when ``expect_stamped`` is
    False and nothing was written; every user-side blunder whose ply+1 row carries a reply
    (best_move or first pv token) has a refutation pair, and every other flaw has a NULL pair;
    every user-side blunder whose post-blunder position has a legal move has a non-NULL
    ``maia_reply_spread`` (reply or not: the spread does not need it), and every other flaw has
    all eight facepalm columns NULL. User-side is computed with ``mover_is_white_at_ply`` and
    the game's user_color. Returns the number of scored user-side blunders (those with a
    refutation pair); callers assert it is at least 1 when their seed guarantees a user-side
    blunder with a reply.
    """
    async with maker() as session:
        game = (await session.execute(select(Game).where(Game.id == game_id))).scalar_one()
        flaws = (
            (await session.execute(select(GameFlaw).where(GameFlaw.game_id == game_id)))
            .scalars()
            .all()
        )
        position_rows = (
            await session.execute(
                select(GamePosition.ply, GamePosition.best_move, GamePosition.pv).where(
                    GamePosition.game_id == game_id
                )
            )
        ).all()
    # Refutation source (D-20): best_move, else the first pv token, at ply + 1.
    reply_by_ply = {
        ply: best_move or (pv.split(" ")[0] if pv else None) for ply, best_move, pv in position_rows
    }
    stamps = (
        game.maia_flaws_completed_at,
        game.maia_refutation_completed_at,
        game.facepalm_spread_completed_at,
        game.facepalm_line_completed_at,
    )
    if expect_stamped:
        assert all(stamp is not None for stamp in stamps)
    else:
        assert all(stamp is None for stamp in stamps)
    pgn_boards = _boards_by_ply(game.pgn)
    scored = 0
    for flaw in flaws:
        user_blunder = flaw.severity == _BLUNDER_SEVERITY and mover_is_white_at_ply(flaw.ply) == (
            game.user_color == "white"
        )
        expect_pair = expect_stamped and user_blunder and reply_by_ply.get(flaw.ply + 1) is not None
        if expect_pair:
            assert flaw.maia_refutation_prob is not None, flaw.ply
            assert flaw.maia_refutation_rank is not None, flaw.ply
            scored += 1
        else:
            assert flaw.maia_refutation_prob is None, flaw.ply
            assert flaw.maia_refutation_rank is None, flaw.ply
        if expect_stamped and user_blunder and _has_legal_reply(pgn_boards, flaw.ply):
            assert flaw.maia_reply_spread is not None, flaw.ply
        elif not (expect_stamped and user_blunder):
            for column in FACEPALM_COLUMNS:
                assert getattr(flaw, column) is None, (flaw.ply, column)
    return scored


def _boards_by_ply(pgn: str) -> dict[int, tuple[chess.Board, str]]:
    """ply -> (pre-push board, played UCI), replayed from the game's own PGN."""
    game = chess.pgn.read_game(io.StringIO(pgn))
    assert game is not None
    board = game.board()
    out: dict[int, tuple[chess.Board, str]] = {}
    for ply, node in enumerate(game.mainline()):
        out[ply] = (board.copy(), node.move.uci())
        board.push(node.move)
    return out


def _has_legal_reply(boards: dict[int, tuple[chess.Board, str]], ply: int) -> bool:
    """True when the opponent has a legal move after the move played at `ply`."""
    board, played = boards[ply]
    post = board.copy()
    post.push_uci(played)
    return any(post.legal_moves)
