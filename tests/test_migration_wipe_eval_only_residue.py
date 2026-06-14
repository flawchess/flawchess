"""Data-correctness test for the Phase 117.2 eval-only residue wipe (SEED-044 follow-up).

Seeds three games and runs the migration's gated UPDATE:
  - DENSE engine game (lichess_evals_at NULL, full_evals_completed_at NULL, ~100% eval
    coverage, no best_move) -> evals must be NULLed.
  - SPARSE engine game (same gates but <90% coverage — entry-ply evals) -> must be
    PRESERVED (endgame-analytics evals are spared by the coverage gate).
  - DENSE lichess game (lichess_evals_at SET) -> must be PRESERVED (engine-source guard).

Mirrors the gated SQL in
`alembic/versions/20260614_130000_wipe_eval_only_residue.py::upgrade`; keep in sync.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.models.user import User

_TEST_USER_ID = 99478

# Mirror of the migration's gated UPDATE (>= 0.90 coverage, engine games only).
_WIPE_SQL = """
WITH dense_engine_games AS (
    SELECT gp.game_id
    FROM game_positions gp JOIN games g ON g.id = gp.game_id
    WHERE g.lichess_evals_at IS NULL AND g.full_evals_completed_at IS NULL
    GROUP BY gp.game_id
    HAVING (SUM(CASE WHEN gp.eval_cp IS NOT NULL OR gp.eval_mate IS NOT NULL THEN 1 ELSE 0 END)::float
            / COUNT(*)) >= 0.90
)
UPDATE game_positions SET eval_cp=NULL, eval_mate=NULL, best_move=NULL, pv=NULL
WHERE game_id IN (SELECT game_id FROM dense_engine_games)
"""


async def _seed_game(
    session: AsyncSession, *, lichess: bool, evald_plies: int, total_plies: int
) -> int:
    now = datetime.now(timezone.utc)
    game = Game(
        user_id=_TEST_USER_ID,
        platform="lichess" if lichess else "chess.com",
        platform_game_id=f"residue-{uuid.uuid4().hex}",
        pgn="1. e4 e5 2. Nf3 Nc6 *",
        result="1-0",
        user_color="white",
        rated=True,
        is_computer_game=False,
        evals_completed_at=now,
        full_evals_completed_at=None,  # not through the full pipeline
        lichess_evals_at=now if lichess else None,
    )
    session.add(game)
    await session.flush()
    for ply in range(total_plies):
        session.add(
            GamePosition(
                user_id=_TEST_USER_ID,
                game_id=game.id,
                ply=ply,
                full_hash=0x4000 + ply,
                white_hash=0,
                black_hash=0,
                phase=0,
                endgame_class=None,
                eval_cp=50 if ply < evald_plies else None,
                eval_mate=None,
            )
        )
    await session.flush()
    return game.id


async def _coverage_nonnull(session: AsyncSession, game_id: int) -> int:
    result = await session.scalar(
        select(text("count(*)"))
        .select_from(GamePosition)
        .where(GamePosition.game_id == game_id, GamePosition.eval_cp.isnot(None))
    )
    return int(result or 0)


async def test_wipe_dense_engine_spares_sparse_and_lichess(db_session: AsyncSession) -> None:
    db_session.add(
        User(id=_TEST_USER_ID, email=f"residue-{_TEST_USER_ID}@example.com", hashed_password="x")
    )
    await db_session.flush()

    dense_engine = await _seed_game(db_session, lichess=False, evald_plies=10, total_plies=10)
    sparse_engine = await _seed_game(db_session, lichess=False, evald_plies=2, total_plies=20)
    dense_lichess = await _seed_game(db_session, lichess=True, evald_plies=10, total_plies=10)

    await db_session.execute(text(_WIPE_SQL))

    assert await _coverage_nonnull(db_session, dense_engine) == 0, (
        "dense eval-only engine game (>=90% coverage) must be wiped"
    )
    assert await _coverage_nonnull(db_session, sparse_engine) == 2, (
        "sparse engine game (<90% coverage) must be preserved — entry-ply evals spared"
    )
    assert await _coverage_nonnull(db_session, dense_lichess) == 10, (
        "lichess game must be preserved (engine-source guard)"
    )
