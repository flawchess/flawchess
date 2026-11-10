"""Deterministic Maia fakes shared by the Phase 247 tests (helper, not a test module).

Plans 02-05 monkeypatch ``maia_flaw_scoring.full_policy`` with ``fake_full_policy``
when a test sets ``maia_engine._session`` to an ``object()`` sentinel, so DB-backed
tests exercise the scorer without a real ORT session.
"""

from __future__ import annotations

import chess
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
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

    Reads the game back and checks: both completion stamps set (or both NULL when
    ``expect_stamped`` is False and no pair was written), every user-side blunder whose
    ply+1 row carries a reply (best_move or first pv token) has a refutation pair, and every other flaw has a NULL
    pair. User-side is computed with ``mover_is_white_at_ply`` and the game's user_color.
    Returns the number of scored user-side blunders; callers assert it is at least 1 when
    their seed guarantees a user-side blunder with a reply.
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
    if expect_stamped:
        assert game.maia_flaws_completed_at is not None
        assert game.maia_refutation_completed_at is not None
    else:
        assert game.maia_flaws_completed_at is None
        assert game.maia_refutation_completed_at is None
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
    return scored
