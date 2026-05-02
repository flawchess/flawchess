"""Backfill script tests (FILL-01, FILL-02 relaxed). Phase 78 Wave 0.

Tests cover:
- dry-run: no writes, no engine calls
- idempotency: second run performs zero engine calls
- lichess eval preservation: rows with eval_cp already set are not overwritten
- limit: --limit N caps evaluations at N rows
- user filter: --user-id scopes rows to a single user
"""
from __future__ import annotations

import datetime
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.repositories.endgame_repository import ENDGAME_PLY_THRESHOLD

# Public API of the script — run_backfill is the callable exposed for testability.
# CLI is parsed in main(); run_backfill takes explicit kwargs.
# This import will fail (RED phase) until Task 2 creates scripts/backfill_eval.py.
from scripts.backfill_eval import run_backfill


pytestmark = pytest.mark.asyncio

_SPAN_START_PLY = 10  # arbitrary span entry ply for tests


def _unique_game_id() -> str:
    return str(uuid.uuid4())


async def _seed_game(
    session: AsyncSession,
    *,
    user_id: int,
    pgn: str = "1. e4 e5 *",
) -> Game:
    """Insert a minimal Game row and flush to get an ID."""
    import datetime as dt
    game = Game(
        user_id=user_id,
        platform="chess.com",
        platform_game_id=_unique_game_id(),
        platform_url="https://chess.com/game/test",
        pgn=pgn,
        result="1-0",
        user_color="white",
        time_control_str="600+0",
        time_control_bucket="blitz",
        time_control_seconds=600,
        rated=True,
        is_computer_game=False,
    )
    game.played_at = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    session.add(game)
    await session.flush()
    return game


async def _seed_span(
    session: AsyncSession,
    *,
    user_id: int,
    game: Game,
    span_start_ply: int = _SPAN_START_PLY,
    endgame_class: int = 1,
    eval_cp_for_entry: int | None = None,
    eval_mate_for_entry: int | None = None,
) -> None:
    """Seed ENDGAME_PLY_THRESHOLD consecutive positions forming a valid endgame span.

    The first ply (span_start_ply) is the span entry. Its eval_cp / eval_mate
    are set from the kwargs so callers can test the lichess-preservation path.
    Subsequent plies always have NULL eval so they don't count as span entries.
    """
    for offset in range(ENDGAME_PLY_THRESHOLD):
        is_entry = offset == 0
        pos = GamePosition(
            game_id=game.id,
            user_id=user_id,
            ply=span_start_ply + offset,
            full_hash=hash(f"{game.id}-{span_start_ply + offset}"),
            white_hash=hash(f"w-{game.id}-{span_start_ply + offset}"),
            black_hash=hash(f"b-{game.id}-{span_start_ply + offset}"),
            piece_count=2,
            material_count=1000,
            material_signature="KR_KR",
            material_imbalance=0,
            endgame_class=endgame_class,
            eval_cp=eval_cp_for_entry if is_entry else None,
            eval_mate=eval_mate_for_entry if is_entry else None,
        )
        session.add(pos)
    await session.flush()


async def _get_entry_eval(session: AsyncSession, game_id: int, ply: int) -> tuple[int | None, int | None]:
    """Fetch (eval_cp, eval_mate) for a specific game_id + ply."""
    from sqlalchemy import select
    row = (
        await session.execute(
            select(GamePosition.eval_cp, GamePosition.eval_mate)
            .where(GamePosition.game_id == game_id, GamePosition.ply == ply)
        )
    ).one()
    return row.eval_cp, row.eval_mate


# ---------------------------------------------------------------------------
# TestDryRun
# ---------------------------------------------------------------------------


class TestDryRun:
    async def test_dry_run_writes_nothing(
        self, db_session: AsyncSession, test_engine
    ) -> None:
        """Dry-run counts rows but performs zero engine calls and zero DB writes."""
        from tests.conftest import ensure_test_user

        user_id = 90001
        await ensure_test_user(db_session, user_id)
        game = await _seed_game(db_session, user_id=user_id)
        await _seed_span(db_session, user_id=user_id, game=game)
        await db_session.flush()

        with patch("scripts.backfill_eval.evaluate", new=AsyncMock(return_value=(150, None))) as mock_eval:
            await run_backfill(db="dev", user_id=user_id, dry_run=True, limit=None)

        assert mock_eval.call_count == 0

        # Entry row must still have NULL eval (nothing written)
        eval_cp, eval_mate = await _get_entry_eval(db_session, game.id, _SPAN_START_PLY)
        assert eval_cp is None
        assert eval_mate is None


# ---------------------------------------------------------------------------
# TestIdempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    async def test_second_run_zero_engine_calls(
        self, db_session: AsyncSession, test_engine
    ) -> None:
        """Second run performs zero engine calls (row-level idempotency check)."""
        from tests.conftest import ensure_test_user

        user_id = 90002
        await ensure_test_user(db_session, user_id)
        game = await _seed_game(db_session, user_id=user_id)
        await _seed_span(db_session, user_id=user_id, game=game)
        await db_session.flush()

        with patch("scripts.backfill_eval.evaluate", new=AsyncMock(return_value=(150, None))) as mock_eval:
            await run_backfill(db="dev", user_id=user_id, dry_run=False, limit=None)
            first_run_calls = mock_eval.call_count
            assert first_run_calls == 1  # one span entry to evaluate

            mock_eval.reset_mock()
            await run_backfill(db="dev", user_id=user_id, dry_run=False, limit=None)
            assert mock_eval.call_count == 0  # idempotent: already populated


# ---------------------------------------------------------------------------
# TestLichessPreservation
# ---------------------------------------------------------------------------


class TestLichessPreservation:
    async def test_lichess_eval_not_overwritten(
        self, db_session: AsyncSession, test_engine
    ) -> None:
        """Rows with eval_cp already set (e.g. from lichess) are NOT overwritten."""
        from tests.conftest import ensure_test_user

        user_id = 90003
        await ensure_test_user(db_session, user_id)
        game = await _seed_game(db_session, user_id=user_id)
        await _seed_span(
            db_session,
            user_id=user_id,
            game=game,
            eval_cp_for_entry=-42,  # lichess pre-populated
        )
        await db_session.flush()

        with patch("scripts.backfill_eval.evaluate", new=AsyncMock(return_value=(999, None))) as mock_eval:
            await run_backfill(db="dev", user_id=user_id, dry_run=False, limit=None)

        # The row had eval_cp set → skipped by WHERE eval_cp IS NULL AND eval_mate IS NULL
        assert mock_eval.call_count == 0

        # Original value preserved byte-for-byte (FILL-04 invariant)
        eval_cp, eval_mate = await _get_entry_eval(db_session, game.id, _SPAN_START_PLY)
        assert eval_cp == -42
        assert eval_mate is None


# ---------------------------------------------------------------------------
# TestLimit
# ---------------------------------------------------------------------------


class TestLimit:
    async def test_limit_caps_evaluations(
        self, db_session: AsyncSession, test_engine
    ) -> None:
        """--limit N processes at most N span-entry rows."""
        from tests.conftest import ensure_test_user

        user_id = 90004
        await ensure_test_user(db_session, user_id)

        # Seed 3 games, each with one NULL-eval span entry
        games = []
        for i in range(3):
            game = await _seed_game(db_session, user_id=user_id)
            await _seed_span(
                db_session,
                user_id=user_id,
                game=game,
                # Stagger span start so each game has a distinct ply — still valid
                span_start_ply=_SPAN_START_PLY + i * ENDGAME_PLY_THRESHOLD,
            )
            games.append(game)
        await db_session.flush()

        with patch("scripts.backfill_eval.evaluate", new=AsyncMock(return_value=(100, None))) as mock_eval:
            await run_backfill(db="dev", user_id=user_id, dry_run=False, limit=2)

        assert mock_eval.call_count == 2


# ---------------------------------------------------------------------------
# TestUserFilter
# ---------------------------------------------------------------------------


class TestUserFilter:
    async def test_user_id_scopes_rows(
        self, db_session: AsyncSession, test_engine
    ) -> None:
        """--user-id X only processes rows belonging to user X."""
        from tests.conftest import ensure_test_user

        user_a = 90005
        user_b = 90006
        await ensure_test_user(db_session, user_a)
        await ensure_test_user(db_session, user_b)

        game_a = await _seed_game(db_session, user_id=user_a)
        game_b = await _seed_game(db_session, user_id=user_b)
        await _seed_span(db_session, user_id=user_a, game=game_a)
        await _seed_span(db_session, user_id=user_b, game=game_b)
        await db_session.flush()

        with patch("scripts.backfill_eval.evaluate", new=AsyncMock(return_value=(50, None))) as mock_eval:
            await run_backfill(db="dev", user_id=user_a, dry_run=False, limit=None)

        # Only user A's row was processed
        assert mock_eval.call_count == 1

        # User B's entry still NULL
        eval_cp_b, eval_mate_b = await _get_entry_eval(db_session, game_b.id, _SPAN_START_PLY)
        assert eval_cp_b is None
        assert eval_mate_b is None

        # User A's entry was populated
        eval_cp_a, eval_mate_a = await _get_entry_eval(db_session, game_a.id, _SPAN_START_PLY)
        assert eval_cp_a == 50
        assert eval_mate_a is None
