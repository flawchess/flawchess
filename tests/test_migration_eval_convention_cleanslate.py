"""Data-correctness test for the Phase 117.1 clean-slate migration (SEED-044).

Proves the gating of the engine-eval/flaw wipe WITHOUT depending on live prod data:
seed one ENGINE game and one LICHESS game (each with positions, a game_flaws row, and
the engine one with an eval_jobs row), run the migration's gated statements, then
assert engine eval/flaw data is cleared, eval_jobs is emptied, and ALL lichess data is
preserved (the over-touch guard).

The test DB is already at head, so we exercise the migration's data statements directly
against seeded rows (the plan's recommended approach) rather than re-running
`alembic upgrade`. The SQL mirrors the four statements in
`alembic/versions/20260614_120000_phase_117_1_eval_convention_cleanslate.py::upgrade`;
keep them in sync (the load-bearing invariant is the `lichess_evals_at IS NULL` gate).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.eval_jobs import EvalJob
from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.user import User

_TEST_USER_ID = 99477  # unique to this module to avoid FK conflicts

# The migration's gated statements (mirror of upgrade()). Engine games only
# (lichess_evals_at IS NULL) that went through the buggy full drain.
_DELETE_FLAWS = """
    DELETE FROM game_flaws gf USING games g
    WHERE gf.game_id = g.id
      AND g.lichess_evals_at IS NULL AND g.full_evals_completed_at IS NOT NULL
"""
_NULL_POSITIONS = """
    UPDATE game_positions gp
    SET eval_cp = NULL, eval_mate = NULL, best_move = NULL, pv = NULL
    FROM games g
    WHERE gp.game_id = g.id
      AND g.lichess_evals_at IS NULL AND g.full_evals_completed_at IS NOT NULL
"""
_CLEAR_MARKERS = """
    UPDATE games g
    SET full_evals_completed_at = NULL, full_pv_completed_at = NULL
    WHERE g.lichess_evals_at IS NULL AND g.full_evals_completed_at IS NOT NULL
"""
_TRUNCATE_JOBS = "TRUNCATE TABLE eval_jobs RESTART IDENTITY"


async def _seed_game(
    session: AsyncSession,
    *,
    lichess_evals_at: datetime | None,
) -> int:
    """Seed one game + two eval'd positions + one game_flaws row. Returns game_id."""
    now = datetime.now(timezone.utc)
    game = Game(
        user_id=_TEST_USER_ID,
        platform="chess.com" if lichess_evals_at is None else "lichess",
        platform_game_id=f"cleanslate-{uuid.uuid4().hex}",
        pgn="1. e4 e5 2. Nf3 Nc6 *",
        result="1-0",
        user_color="white",
        rated=True,
        is_computer_game=False,
        evals_completed_at=now,
        full_evals_completed_at=now,
        full_pv_completed_at=now,
        lichess_evals_at=lichess_evals_at,
    )
    session.add(game)
    await session.flush()
    game_id = game.id

    for ply in (0, 1):
        session.add(
            GamePosition(
                user_id=_TEST_USER_ID,
                game_id=game_id,
                ply=ply,
                full_hash=0x1000 + ply,
                white_hash=0,
                black_hash=0,
                move_san="e4",
                phase=0,
                endgame_class=None,
                eval_cp=50,
                eval_mate=None,
                best_move="e2e4",
                pv="e2e4 e7e5",
            )
        )
    session.add(
        GameFlaw(
            user_id=_TEST_USER_ID,
            game_id=game_id,
            ply=1,
            severity=2,
            tempo=None,
            phase=0,
            is_miss=False,
            is_lucky=False,
            is_reversed=False,
            is_squandered=False,
            fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
        )
    )
    await session.flush()
    return game_id


async def test_cleanslate_clears_engine_preserves_lichess(db_session: AsyncSession) -> None:
    """Engine eval/flaw data cleared + eval_jobs emptied; lichess data untouched."""
    # User (FK target) — lives inside the rolled-back transaction.
    db_session.add(
        User(id=_TEST_USER_ID, email=f"cleanslate-{_TEST_USER_ID}@example.com", hashed_password="x")
    )
    await db_session.flush()

    engine_game_id = await _seed_game(db_session, lichess_evals_at=None)
    lichess_game_id = await _seed_game(db_session, lichess_evals_at=datetime.now(timezone.utc))
    db_session.add(EvalJob(tier=3, user_id=_TEST_USER_ID, game_id=engine_game_id))
    await db_session.flush()

    # Run the migration's data statements (order: flaws, positions, markers, then truncate).
    await db_session.execute(text(_DELETE_FLAWS))
    await db_session.execute(text(_NULL_POSITIONS))
    await db_session.execute(text(_CLEAR_MARKERS))
    await db_session.execute(text(_TRUNCATE_JOBS))

    # --- Engine game: everything wiped ---
    eng_positions = (
        await db_session.execute(
            select(
                GamePosition.eval_cp,
                GamePosition.eval_mate,
                GamePosition.best_move,
                GamePosition.pv,
            ).where(GamePosition.game_id == engine_game_id)
        )
    ).all()
    assert eng_positions, "engine positions should still exist (rows kept, values NULLed)"
    for cp, mate, bm, pv in eng_positions:
        assert (cp, mate, bm, pv) == (None, None, None, None), (
            "engine game_positions eval/best_move/pv must be NULLed"
        )

    eng_markers = (
        await db_session.execute(
            select(Game.full_evals_completed_at, Game.full_pv_completed_at).where(
                Game.id == engine_game_id
            )
        )
    ).one()
    assert eng_markers == (None, None), "engine completion markers must be cleared"

    eng_flaws = await db_session.scalar(select(GameFlaw).where(GameFlaw.game_id == engine_game_id))
    assert eng_flaws is None, "engine game_flaws must be deleted"

    # --- Lichess game: fully preserved (over-touch guard) ---
    lich_positions = (
        await db_session.execute(
            select(GamePosition.eval_cp).where(GamePosition.game_id == lichess_game_id)
        )
    ).all()
    assert lich_positions and all(cp == 50 for (cp,) in lich_positions), (
        "lichess game_positions eval_cp must be untouched"
    )
    lich_markers = (
        await db_session.execute(
            select(Game.full_evals_completed_at, Game.lichess_evals_at).where(
                Game.id == lichess_game_id
            )
        )
    ).one()
    assert lich_markers[0] is not None and lich_markers[1] is not None, (
        "lichess completion + provenance markers must be preserved"
    )
    lich_flaw = await db_session.scalar(select(GameFlaw).where(GameFlaw.game_id == lichess_game_id))
    assert lich_flaw is not None, "lichess game_flaws must be preserved"

    # --- eval_jobs emptied ---
    job_count = await db_session.scalar(select(text("count(*)")).select_from(EvalJob))
    assert job_count == 0, "eval_jobs must be truncated"
