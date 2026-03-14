"""Unit and integration tests for the analysis service.

Coverage:
- ANL-03: derive_user_result for all 6 result × color combinations
- recency_cutoff: None passthrough, "all", "week", "year" mappings
- ANL-03: W/D/L stats computed correctly from seeded data
- RES-01, RES-02: GameRecord includes opponent, result, date, time_control, platform_url
- RES-03: matched_count reflects total before pagination
- Zero-match edge case: all-zero stats, empty list, no error
"""

import datetime
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.game_position import GamePosition
from app.schemas.analysis import AnalysisRequest
from app.services.analysis_service import (
    analyze,
    derive_user_result,
    recency_cutoff,
)


# ---------------------------------------------------------------------------
# Seed helper (local — avoids coupling to repository test module)
# ---------------------------------------------------------------------------


def _unique_id() -> str:
    return str(uuid.uuid4())


async def _seed_game(
    session: AsyncSession,
    *,
    user_id: int = 1,
    platform: str = "chess.com",
    result: str = "1-0",
    user_color: str = "white",
    rated: bool = True,
    time_control_bucket: str = "blitz",
    played_at: datetime.datetime | None = None,
    white_username: str = "testuser",
    black_username: str = "opponent",
    platform_url: str | None = "https://www.chess.com/game/live/12345",
    full_hash: int = 11111111,
    white_hash: int = 22222222,
    black_hash: int = 33333333,
) -> Game:
    """Insert one Game + one GamePosition and return the Game."""
    if played_at is None:
        played_at = datetime.datetime.now(tz=datetime.timezone.utc)

    game = Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=_unique_id(),
        platform_url=platform_url,
        pgn="1. e4 e5 *",
        variant="Standard",
        result=result,
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket=time_control_bucket,
        time_control_seconds=600,
        rated=rated,
        white_username=white_username,
        black_username=black_username,
    )
    game.played_at = played_at
    session.add(game)
    await session.flush()

    pos = GamePosition(
        game_id=game.id,
        user_id=user_id,
        ply=1,
        full_hash=full_hash,
        white_hash=white_hash,
        black_hash=black_hash,
    )
    session.add(pos)
    await session.flush()

    return game


# ---------------------------------------------------------------------------
# TestDeriveUserResult — ANL-03 support
# ---------------------------------------------------------------------------


class TestDeriveUserResult:
    """Verify derive_user_result for all 6 result × color combinations."""

    def test_white_wins(self) -> None:
        assert derive_user_result("1-0", "white") == "win"

    def test_white_loses(self) -> None:
        assert derive_user_result("0-1", "white") == "loss"

    def test_black_wins(self) -> None:
        assert derive_user_result("0-1", "black") == "win"

    def test_black_loses(self) -> None:
        assert derive_user_result("1-0", "black") == "loss"

    def test_draw_white(self) -> None:
        assert derive_user_result("1/2-1/2", "white") == "draw"

    def test_draw_black(self) -> None:
        assert derive_user_result("1/2-1/2", "black") == "draw"


# ---------------------------------------------------------------------------
# TestRecencyCutoff
# ---------------------------------------------------------------------------


class TestRecencyCutoff:
    """Verify recency_cutoff returns correct datetime offsets."""

    def test_none_returns_none(self) -> None:
        assert recency_cutoff(None) is None

    def test_all_returns_none(self) -> None:
        assert recency_cutoff("all") is None

    def test_week_returns_recent(self) -> None:
        before = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=7)
        result = recency_cutoff("week")
        after = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=7)

        assert result is not None
        assert before <= result <= after

    def test_year_returns_past(self) -> None:
        before = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=365)
        result = recency_cutoff("year")
        after = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=365)

        assert result is not None
        assert before <= result <= after


# ---------------------------------------------------------------------------
# TestWDLStats — ANL-03
# ---------------------------------------------------------------------------

WDL_HASH = 44444444


class TestWDLStats:
    """Verify W/D/L stats computed correctly via analyze()."""

    @pytest.mark.asyncio
    async def test_wdl_computation(self, db_session: AsyncSession) -> None:
        """1 win + 1 draw + 1 loss yields correct counts and percentages."""
        await _seed_game(db_session, result="1-0", user_color="white", full_hash=WDL_HASH)
        await _seed_game(db_session, result="1/2-1/2", user_color="white", full_hash=WDL_HASH)
        await _seed_game(db_session, result="0-1", user_color="white", full_hash=WDL_HASH)

        request = AnalysisRequest(target_hash=WDL_HASH, match_side="full")
        response = await analyze(db_session, user_id=1, request=request)

        assert response.stats.wins == 1
        assert response.stats.draws == 1
        assert response.stats.losses == 1
        assert response.stats.total == 3
        assert response.stats.win_pct == pytest.approx(33.3, abs=0.1)
        assert response.stats.draw_pct == pytest.approx(33.3, abs=0.1)
        assert response.stats.loss_pct == pytest.approx(33.3, abs=0.1)

    @pytest.mark.asyncio
    async def test_zero_matches(self, db_session: AsyncSession) -> None:
        """Hash that matches no games returns all-zero stats and empty list."""
        request = AnalysisRequest(target_hash=999999999, match_side="full")
        response = await analyze(db_session, user_id=1, request=request)

        assert response.stats.wins == 0
        assert response.stats.draws == 0
        assert response.stats.losses == 0
        assert response.stats.total == 0
        assert response.stats.win_pct == 0.0
        assert response.stats.draw_pct == 0.0
        assert response.stats.loss_pct == 0.0
        assert response.games == []
        assert response.matched_count == 0


# ---------------------------------------------------------------------------
# TestGameRecord — RES-01, RES-02
# ---------------------------------------------------------------------------

RECORD_HASH = 55555555


class TestGameRecord:
    """Verify GameRecord contains all required display fields."""

    @pytest.mark.asyncio
    async def test_game_record_fields(self, db_session: AsyncSession) -> None:
        """GameRecord exposes players, result, date, time_control, platform_url."""
        played = datetime.datetime(2024, 6, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        await _seed_game(
            db_session,
            result="1-0",
            user_color="white",
            white_username="testuser",
            black_username="grandmaster_bot",
            played_at=played,
            time_control_bucket="rapid",
            platform="chess.com",
            platform_url="https://www.chess.com/game/live/99999",
            full_hash=RECORD_HASH,
        )

        request = AnalysisRequest(target_hash=RECORD_HASH, match_side="full")
        response = await analyze(db_session, user_id=1, request=request)

        assert len(response.games) == 1
        rec = response.games[0]

        # User is white, opponent is black
        assert rec.white_username == "testuser"
        assert rec.black_username == "grandmaster_bot"
        assert rec.user_color == "white"
        assert rec.user_result == "win"
        assert rec.played_at == played
        assert rec.time_control_bucket == "rapid"
        assert rec.platform == "chess.com"
        assert rec.platform_url == "https://www.chess.com/game/live/99999"

    @pytest.mark.asyncio
    async def test_platform_url_present(self, db_session: AsyncSession) -> None:
        """RES-02: platform_url is populated on every GameRecord."""
        url = "https://www.chess.com/game/live/77777"
        await _seed_game(db_session, platform_url=url, full_hash=RECORD_HASH)

        request = AnalysisRequest(target_hash=RECORD_HASH, match_side="full")
        response = await analyze(db_session, user_id=1, request=request)

        for rec in response.games:
            assert rec.platform_url is not None


# ---------------------------------------------------------------------------
# TestPaginationResponse — RES-03
# ---------------------------------------------------------------------------

PAGINATION_HASH = 66666666


class TestPaginationResponse:
    """Verify matched_count reflects total before pagination."""

    @pytest.mark.asyncio
    async def test_matched_count_reflects_total(self, db_session: AsyncSession) -> None:
        """Seed 10 games, request limit=3 — matched_count=10, len(games)=3."""
        for _ in range(10):
            await _seed_game(db_session, full_hash=PAGINATION_HASH)

        request = AnalysisRequest(target_hash=PAGINATION_HASH, match_side="full", limit=3, offset=0)
        response = await analyze(db_session, user_id=1, request=request)

        assert response.matched_count == 10
        assert len(response.games) == 3
        assert response.limit == 3
        assert response.offset == 0
