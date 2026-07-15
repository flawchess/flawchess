"""Tests for the bot_game_settings side table (Phase 167 Plan 01, D-16/STORE-04).

Covers: insert + read back; CHECK constraint rejects an out-of-vocabulary
rating_source (T-167-04); FK CASCADE removes the settings row when the parent
game is deleted.

Data isolation: uses the rollback-scoped ``db_session`` fixture from
``tests/conftest.py`` — no committed rows leak between tests.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot_game_settings import BotGameSettings
from app.models.game import Game
from tests.conftest import ensure_test_user

pytestmark = pytest.mark.asyncio

_TEST_USER_ID = 92400  # unique ID for this test module


async def _seed_game(db_session: AsyncSession, platform_game_id: str) -> int:
    await ensure_test_user(db_session, _TEST_USER_ID)
    game = Game(
        user_id=_TEST_USER_ID,
        platform="flawchess",
        platform_game_id=platform_game_id,
        pgn="1. e4 e5 1-0",
        result="1-0",
        user_color="white",
        rated=False,
        is_computer_game=True,
    )
    db_session.add(game)
    await db_session.flush()
    return game.id


class TestBotGameSettingsInsertAndRead:
    async def test_insert_and_read_back(self, db_session: AsyncSession) -> None:
        game_id = await _seed_game(db_session, "bgs-test-1")
        settings = BotGameSettings(
            game_id=game_id,
            nominal_elo=1400,
            play_style_blend=0.5,
            tc_preset="3+2",
            rating_source="blended",
        )
        db_session.add(settings)
        await db_session.flush()

        row = (
            await db_session.execute(
                select(BotGameSettings).where(BotGameSettings.game_id == game_id)
            )
        ).scalar_one()
        assert row.nominal_elo == 1400
        assert row.play_style_blend == pytest.approx(0.5)
        assert row.tc_preset == "3+2"
        assert row.rating_source == "blended"

    async def test_rating_source_nullable(self, db_session: AsyncSession) -> None:
        game_id = await _seed_game(db_session, "bgs-test-null")
        settings = BotGameSettings(
            game_id=game_id,
            nominal_elo=1000,
            play_style_blend=0.0,
            tc_preset="5+0",
            rating_source=None,
        )
        db_session.add(settings)
        await db_session.flush()

        row = (
            await db_session.execute(
                select(BotGameSettings).where(BotGameSettings.game_id == game_id)
            )
        ).scalar_one()
        assert row.rating_source is None


class TestBotGameSettingsCheckConstraint:
    async def test_bogus_rating_source_raises_integrity_error(
        self, db_session: AsyncSession
    ) -> None:
        game_id = await _seed_game(db_session, "bgs-test-bogus")
        settings = BotGameSettings(
            game_id=game_id,
            nominal_elo=1400,
            play_style_blend=0.5,
            tc_preset="3+2",
            rating_source="bogus",
        )
        db_session.add(settings)
        with pytest.raises(IntegrityError):
            await db_session.flush()


class TestBotGameSettingsCascadeDelete:
    async def test_deleting_game_cascades_settings_row(self, db_session: AsyncSession) -> None:
        game_id = await _seed_game(db_session, "bgs-test-cascade")
        settings = BotGameSettings(
            game_id=game_id,
            nominal_elo=1400,
            play_style_blend=0.5,
            tc_preset="3+2",
            rating_source="lichess",
        )
        db_session.add(settings)
        await db_session.flush()

        game = await db_session.get(Game, game_id)
        assert game is not None
        await db_session.delete(game)
        await db_session.flush()

        row = (
            await db_session.execute(
                select(BotGameSettings).where(BotGameSettings.game_id == game_id)
            )
        ).scalar_one_or_none()
        assert row is None
