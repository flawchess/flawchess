"""Tests for app/services/repertoire_recency.py (current/past repertoire cutoff, D-01..D-03).

Pure cases cover combine_cutoff / is_current; DB cases cover the cutoff query under
the active filters with an injected now_utc (never the wall clock).
"""

import datetime
import uuid
from collections.abc import Sequence
from typing import Literal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.services.repertoire_recency import (
    CURRENT_REPERTOIRE_MIN_DAYS,
    CURRENT_REPERTOIRE_RECENT_GAMES,
    combine_cutoff,
    is_current,
    resolve_current_cutoff,
    resolve_current_cutoffs,
)

# User ids 24201-24204 are reserved for this module.
_USER_200_PLUS = 24201
_USER_UNDER_200 = 24202
_USER_FILTERS = 24203
_USER_COLORS = 24204
_ALL_USER_IDS = [_USER_200_PLUS, _USER_UNDER_200, _USER_FILTERS, _USER_COLORS]

NOW = datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.UTC)


@pytest_asyncio.fixture(autouse=True)
async def _create_users(db_session: AsyncSession) -> None:
    from tests.conftest import ensure_test_user

    for uid in _ALL_USER_IDS:
        await ensure_test_user(db_session, uid)


async def _seed_games(
    session: AsyncSession,
    *,
    user_id: int,
    count: int,
    color: str = "white",
    time_control_bucket: str = "blitz",
    first_days_back: int = 1,
) -> list[datetime.datetime]:
    """Seed ``count`` games one per day, the newest ``first_days_back`` days before NOW.

    Returns the played_at values, newest first.
    """
    played: list[datetime.datetime] = []
    for i in range(count):
        played_at = NOW - datetime.timedelta(days=first_days_back + i)
        played.append(played_at)
        game = Game(
            user_id=user_id,
            platform="chess.com",
            platform_game_id=str(uuid.uuid4()),
            pgn="1. e4 e5 *",
            result="1-0",
            user_color=color,
            time_control_str="300+0",
            time_control_bucket=time_control_bucket,
            time_control_seconds=300,
            rated=True,
            white_username="me",
            black_username="opp",
            white_rating=1500,
            black_rating=1500,
        )
        game.played_at = played_at
        session.add(game)
    await session.flush()
    return played


async def _cutoff(
    session: AsyncSession,
    user_id: int,
    color: Literal["white", "black"] = "white",
    *,
    time_control: Sequence[str] | None = None,
) -> datetime.datetime | None:
    return await resolve_current_cutoff(
        session,
        user_id,
        color,
        now_utc=NOW,
        time_control=time_control,
        platform=None,
        rated=None,
        opponent_type="human",
        from_date=None,
        to_date=None,
        opponent_gap_min=None,
        opponent_gap_max=None,
    )


class TestCombineCutoff:
    def test_none_stays_none(self) -> None:
        assert combine_cutoff(None, NOW) is None

    def test_recent_nth_game_falls_back_to_the_day_floor(self) -> None:
        nth = NOW - datetime.timedelta(days=20)
        assert combine_cutoff(nth, NOW) == NOW - datetime.timedelta(
            days=CURRENT_REPERTOIRE_MIN_DAYS
        )

    def test_old_nth_game_wins_over_the_day_floor(self) -> None:
        nth = NOW - datetime.timedelta(days=400)
        assert combine_cutoff(nth, NOW) == nth


class TestIsCurrent:
    CUTOFF = NOW - datetime.timedelta(days=100)

    def test_no_cutoff_is_current(self) -> None:
        assert is_current(NOW - datetime.timedelta(days=9999), None) is True

    def test_unknown_last_played_is_current(self) -> None:
        assert is_current(None, self.CUTOFF) is True

    def test_equal_timestamp_is_current(self) -> None:
        assert is_current(self.CUTOFF, self.CUTOFF) is True

    def test_one_second_before_the_cutoff_is_past(self) -> None:
        assert is_current(self.CUTOFF - datetime.timedelta(seconds=1), self.CUTOFF) is False


class TestResolveCurrentCutoff:
    @pytest.mark.asyncio
    async def test_200_plus_games_cutoff_is_the_200th_date_or_the_floor(
        self, db_session: AsyncSession
    ) -> None:
        played = await _seed_games(db_session, user_id=_USER_200_PLUS, count=205)
        nth = played[CURRENT_REPERTOIRE_RECENT_GAMES - 1]

        cutoff = await _cutoff(db_session, _USER_200_PLUS)

        # One game per day: the 200th game is 200 days back, further than the 60-day floor.
        assert cutoff == nth

    @pytest.mark.asyncio
    async def test_dense_recent_games_use_the_day_floor(self, db_session: AsyncSession) -> None:
        """Many games within a few days: the 200th game is recent, so the 60-day floor wins."""
        user_id = _USER_COLORS
        for _ in range(10):
            await _seed_games(db_session, user_id=user_id, count=25, first_days_back=1)

        cutoff = await _cutoff(db_session, user_id)

        # 250 white games over the last 25 days: the 200th is 20 days back, so the floor applies.
        assert cutoff == NOW - datetime.timedelta(days=CURRENT_REPERTOIRE_MIN_DAYS)

    @pytest.mark.asyncio
    async def test_fewer_than_200_games_has_no_cutoff(self, db_session: AsyncSession) -> None:
        await _seed_games(db_session, user_id=_USER_UNDER_200, count=150)

        assert await _cutoff(db_session, _USER_UNDER_200) is None

    @pytest.mark.asyncio
    async def test_time_control_filter_is_respected(self, db_session: AsyncSession) -> None:
        """205 blitz + 10 rapid white games: a rapid-only filter leaves 10 games, no cutoff."""
        await _seed_games(db_session, user_id=_USER_FILTERS, count=205)
        await _seed_games(db_session, user_id=_USER_FILTERS, count=10, time_control_bucket="rapid")

        assert await _cutoff(db_session, _USER_FILTERS, time_control=["rapid"]) is None
        assert await _cutoff(db_session, _USER_FILTERS, time_control=["blitz"]) is not None

    @pytest.mark.asyncio
    async def test_other_colour_games_do_not_count(self, db_session: AsyncSession) -> None:
        await _seed_games(db_session, user_id=_USER_COLORS, count=150, color="white")
        await _seed_games(db_session, user_id=_USER_COLORS, count=150, color="black")

        assert await _cutoff(db_session, _USER_COLORS, "white") is None
        assert await _cutoff(db_session, _USER_COLORS, "black") is None

    @pytest.mark.asyncio
    async def test_resolve_current_cutoffs_maps_unrequested_colours_to_none(
        self, db_session: AsyncSession
    ) -> None:
        played = await _seed_games(db_session, user_id=_USER_200_PLUS, count=205)

        cutoffs = await resolve_current_cutoffs(
            db_session,
            _USER_200_PLUS,
            ["white"],
            now_utc=NOW,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="human",
            from_date=None,
            to_date=None,
            opponent_gap_min=None,
            opponent_gap_max=None,
        )

        assert cutoffs["white"] == played[CURRENT_REPERTOIRE_RECENT_GAMES - 1]
        assert cutoffs["black"] is None
