"""Tests for store_bot_game_service.store_bot_game (Phase 167 STORE-03/04/05/06).

Covers: rating derivation from user_rating_anchors (lichess-only / chess.com-only
/ blended / no-anchor), the games-row + bot_game_settings insert, and idempotency
on a duplicate game_uuid.

Data isolation: uses the rollback-scoped ``db_session`` fixture from
``tests/conftest.py`` (session.commit() inside store_bot_game only ends the
ORM-level unit of work — the outer connection-level transaction is rolled back
in the fixture's teardown, verified empirically for this phase).
"""

from __future__ import annotations

import uuid
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot_game_settings import BotGameSettings
from app.models.game import Game
from app.repositories.user_rating_anchors_repository import upsert_anchor
from app.repositories.user_repository import update_profile
from app.schemas.bots import StoreBotGameRequest
from app.services.normalization import FLAWCHESS_BOT_USERNAME, FLAWCHESS_PLAYER_FALLBACK_USERNAME
from app.services.store_bot_game_service import resolve_player_username, store_bot_game
from tests.conftest import ensure_test_user

# quick-260714-pnk: no module-level `pytestmark = pytest.mark.asyncio` —
# asyncio_mode = "auto" (pyproject.toml) picks up async tests automatically,
# and a module-level marker triggers a "marked async but not async" warning
# on TestResolvePlayerUsername's sync tests (mirrors
# test_user_benchmark_percentiles_service.py's established pattern).

_TEST_USER_ID = 92500  # unique ID for this test module
_TEST_BOT_ELO = 1400
_TC_STR = "180+2"  # parse_time_control("180+2") -> ("blitz", 260)
_TC_BUCKET = "blitz"

# Scholar's Mate PGN with per-move [%clk] on both colors (mirrors
# tests/services/test_normalization.py's fixture).
_PGN_CHECKMATE = (
    '[Event "FlawChess Bot Game"]\n[Result "1-0"]\n\n'
    "1. e4 {[%clk 0:03:00]} e5 {[%clk 0:03:00]} "
    "2. Bc4 {[%clk 0:02:58]} Nc6 {[%clk 0:02:58]} "
    "3. Qh5 {[%clk 0:02:56]} Nf6 {[%clk 0:02:56]} "
    "4. Qxf7# {[%clk 0:02:54]} 1-0\n"
)

# PGN missing black's [%clk] annotations — invalid input (STORE-02).
_PGN_MISSING_CLOCK = (
    '[Event "FlawChess Bot Game"]\n[Result "1-0"]\n\n'
    "1. e4 {[%clk 0:03:00]} e5 "
    "2. Bc4 {[%clk 0:02:58]} Nc6 "
    "3. Qh5 {[%clk 0:02:56]} Nf6 "
    "4. Qxf7# {[%clk 0:02:54]} 1-0\n"
)


def _make_request(
    *,
    game_uuid: str | None = None,
    pgn: str = _PGN_CHECKMATE,
    user_color: Literal["white", "black"] = "white",
) -> StoreBotGameRequest:
    return StoreBotGameRequest(
        game_uuid=game_uuid or str(uuid.uuid4()),
        pgn=pgn,
        user_color=user_color,
        bot_elo=_TEST_BOT_ELO,
        play_style_blend=0.5,
        tc_preset=_TC_STR,
    )


class TestRatingDerivation:
    """STORE-03: server-computed rating placement + rating_source provenance."""

    async def test_lichess_only_anchor(self, db_session: AsyncSession) -> None:
        await ensure_test_user(db_session, _TEST_USER_ID)
        await upsert_anchor(
            db_session,
            user_id=_TEST_USER_ID,
            time_control_bucket=_TC_BUCKET,
            anchor_rating=1550,
            n_chesscom_games=0,
            n_lichess_games=25,
            chesscom_median_native=None,
            lichess_median_native=1550,
        )
        await db_session.flush()

        response = await store_bot_game(db_session, _TEST_USER_ID, _make_request())
        assert response is not None
        assert response.created is True

        game = await db_session.get(Game, response.game_id)
        assert game is not None
        # D-08: player-color (white, this request) = anchor rating; opponent = bot ELO.
        assert game.white_rating == 1550
        assert game.black_rating == _TEST_BOT_ELO

        settings = (
            await db_session.execute(
                select(BotGameSettings).where(BotGameSettings.game_id == response.game_id)
            )
        ).scalar_one()
        assert settings.rating_source == "lichess"
        assert settings.nominal_elo == _TEST_BOT_ELO
        assert settings.tc_preset == _TC_STR

    async def test_no_anchor_null_rating(self, db_session: AsyncSession) -> None:
        """Guest / user with no anchor for the bucket -> NULL rating + NULL source (D-06)."""
        await ensure_test_user(db_session, _TEST_USER_ID + 1)

        response = await store_bot_game(db_session, _TEST_USER_ID + 1, _make_request())
        assert response is not None

        game = await db_session.get(Game, response.game_id)
        assert game is not None
        assert game.white_rating is None

        settings = (
            await db_session.execute(
                select(BotGameSettings).where(BotGameSettings.game_id == response.game_id)
            )
        ).scalar_one()
        assert settings.rating_source is None

    async def test_blended_anchor(self, db_session: AsyncSession) -> None:
        """Both n_lichess_games and n_chesscom_games > 0 -> rating_source='blended'."""
        user_id = _TEST_USER_ID + 2
        await ensure_test_user(db_session, user_id)
        await upsert_anchor(
            db_session,
            user_id=user_id,
            time_control_bucket=_TC_BUCKET,
            anchor_rating=1600,
            n_chesscom_games=10,
            n_lichess_games=15,
            chesscom_median_native=1580,
            lichess_median_native=1620,
        )
        await db_session.flush()

        response = await store_bot_game(db_session, user_id, _make_request())
        assert response is not None

        settings = (
            await db_session.execute(
                select(BotGameSettings).where(BotGameSettings.game_id == response.game_id)
            )
        ).scalar_one()
        assert settings.rating_source == "blended"


class TestInvalidPgn:
    """STORE-02: invalid PGN input surfaces as None (router maps to 422)."""

    async def test_missing_clock_returns_none(self, db_session: AsyncSession) -> None:
        await ensure_test_user(db_session, _TEST_USER_ID + 3)
        response = await store_bot_game(
            db_session, _TEST_USER_ID + 3, _make_request(pgn=_PGN_MISSING_CLOCK)
        )
        assert response is None


class TestIdempotency:
    """STORE-05: re-submitting the same game_uuid is a no-op success, not a duplicate row."""

    async def test_duplicate_game_uuid_returns_existing_id(self, db_session: AsyncSession) -> None:
        user_id = _TEST_USER_ID + 4
        await ensure_test_user(db_session, user_id)
        game_uuid = str(uuid.uuid4())
        request = _make_request(game_uuid=game_uuid)

        first = await store_bot_game(db_session, user_id, request)
        assert first is not None
        assert first.created is True

        second = await store_bot_game(db_session, user_id, request)
        assert second is not None
        assert second.created is False
        assert second.game_id == first.game_id

        games = (
            (
                await db_session.execute(
                    select(Game).where(
                        Game.user_id == user_id,
                        Game.platform == "flawchess",
                        Game.platform_game_id == game_uuid,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(games) == 1

        settings_rows = (
            (
                await db_session.execute(
                    select(BotGameSettings).where(BotGameSettings.game_id == first.game_id)
                )
            )
            .scalars()
            .all()
        )
        assert len(settings_rows) == 1


class TestResolvePlayerUsername:
    """Pure precedence-chain coverage for resolve_player_username (no DB;
    quick-260714-pnk): lichess -> chess.com -> FLAWCHESS_PLAYER_FALLBACK_USERNAME.
    """

    def test_lichess_wins_when_both_set(self) -> None:
        assert resolve_player_username("magnus", "hikaru") == "magnus"

    def test_falls_back_to_chesscom_when_lichess_none(self) -> None:
        assert resolve_player_username(None, "hikaru") == "hikaru"

    def test_falls_back_to_fallback_when_both_none(self) -> None:
        assert resolve_player_username(None, None) == FLAWCHESS_PLAYER_FALLBACK_USERNAME

    def test_blank_lichess_falls_through_to_chesscom(self) -> None:
        assert resolve_player_username("   ", "hikaru") == "hikaru"

    def test_blank_both_falls_back_to_fallback(self) -> None:
        assert resolve_player_username("  ", "") == FLAWCHESS_PLAYER_FALLBACK_USERNAME


class TestPlayerUsername:
    """DB-backed coverage (quick-260714-pnk): the resolved player_username
    lands in the games row's player-color username column; the bot-color
    column always stays FLAWCHESS_BOT_USERNAME.
    """

    async def test_lichess_username_white(self, db_session: AsyncSession) -> None:
        user_id = _TEST_USER_ID + 5
        await ensure_test_user(db_session, user_id)
        await update_profile(db_session, user_id, {"lichess_username": "magnus"})

        response = await store_bot_game(db_session, user_id, _make_request())
        assert response is not None

        game = await db_session.get(Game, response.game_id)
        assert game is not None
        assert game.white_username == "magnus"
        assert game.black_username == FLAWCHESS_BOT_USERNAME

    async def test_lichess_username_black(self, db_session: AsyncSession) -> None:
        user_id = _TEST_USER_ID + 6
        await ensure_test_user(db_session, user_id)
        await update_profile(db_session, user_id, {"lichess_username": "magnus"})

        response = await store_bot_game(db_session, user_id, _make_request(user_color="black"))
        assert response is not None

        game = await db_session.get(Game, response.game_id)
        assert game is not None
        assert game.black_username == "magnus"
        assert game.white_username == FLAWCHESS_BOT_USERNAME

    async def test_chesscom_only_username(self, db_session: AsyncSession) -> None:
        user_id = _TEST_USER_ID + 7
        await ensure_test_user(db_session, user_id)
        await update_profile(db_session, user_id, {"chess_com_username": "hikaru"})

        response = await store_bot_game(db_session, user_id, _make_request())
        assert response is not None

        game = await db_session.get(Game, response.game_id)
        assert game is not None
        assert game.white_username == "hikaru"

    async def test_no_platform_username_falls_back_to_you(self, db_session: AsyncSession) -> None:
        user_id = _TEST_USER_ID + 8
        await ensure_test_user(db_session, user_id)

        response = await store_bot_game(db_session, user_id, _make_request())
        assert response is not None

        game = await db_session.get(Game, response.game_id)
        assert game is not None
        assert game.white_username == FLAWCHESS_PLAYER_FALLBACK_USERNAME
