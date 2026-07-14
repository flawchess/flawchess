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

import io
import uuid
from typing import Literal

import chess.pgn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
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

# A materially different mainline (Termination differs from _PGN_CHECKMATE too)
# for D-11's duplicate-re-submit-does-not-rewrite test.
_PGN_CHECKMATE_ALT = (
    '[Event "FlawChess Bot Game"]\n[Result "0-1"]\n\n'
    "1. d4 {[%clk 0:03:00]} d5 {[%clk 0:03:00]} "
    "2. c4 {[%clk 0:02:58]} e6 {[%clk 0:02:58]} 0-1\n"
)


def _make_request(
    *,
    game_uuid: str | None = None,
    pgn: str = _PGN_CHECKMATE,
    user_color: Literal["white", "black"] = "white",
    bot_elo: int = _TEST_BOT_ELO,
) -> StoreBotGameRequest:
    return StoreBotGameRequest(
        game_uuid=game_uuid or str(uuid.uuid4()),
        pgn=pgn,
        user_color=user_color,
        bot_elo=bot_elo,
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


def _reparse_stored_pgn(pgn_text: str) -> chess.pgn.Headers:
    """Re-parse a stored games.pgn column and return its headers.

    Every TestPgnHeaders assertion goes through this — never asserts on the
    in-memory NormalizedGame/StoreBotGameResponse (quick-260714-qaj).
    """
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    assert game is not None
    return game.headers


class TestPgnHeaders:
    """quick-260714-qaj: the full D-03 header block, stamped end-to-end.

    Every assertion re-reads games.pgn FROM THE DB and re-parses it.
    """

    async def test_anchored_white_full_header_block(self, db_session: AsyncSession) -> None:
        user_id = _TEST_USER_ID + 10
        await ensure_test_user(db_session, user_id)
        await upsert_anchor(
            db_session,
            user_id=user_id,
            time_control_bucket=_TC_BUCKET,
            anchor_rating=1550,
            n_chesscom_games=0,
            n_lichess_games=25,
            chesscom_median_native=None,
            lichess_median_native=1550,
        )
        await db_session.flush()

        response = await store_bot_game(db_session, user_id, _make_request())
        assert response is not None

        game = await db_session.get(Game, response.game_id)
        assert game is not None
        headers = _reparse_stored_pgn(game.pgn)

        # D-07: the Site deep link carries the REAL post-INSERT game_id.
        assert (
            headers["Site"]
            == f"{settings.FRONTEND_URL.rstrip('/')}/analysis?game_id={response.game_id}"
        )
        assert headers["TimeControl"] == _TC_STR
        assert headers["Termination"] == "checkmate"
        assert headers["PlayStyleBlend"] == "0.50"
        assert headers["Event"] == "FlawChess bot game"
        assert headers["Round"] == "-"
        assert headers["Variant"] == "Standard"

    async def test_column_header_consistency(self, db_session: AsyncSession) -> None:
        """D-01 one-source-of-truth invariant: header values equal their column."""
        user_id = _TEST_USER_ID + 11
        await ensure_test_user(db_session, user_id)
        await upsert_anchor(
            db_session,
            user_id=user_id,
            time_control_bucket=_TC_BUCKET,
            anchor_rating=1550,
            n_chesscom_games=0,
            n_lichess_games=25,
            chesscom_median_native=None,
            lichess_median_native=1550,
        )
        await db_session.flush()

        response = await store_bot_game(db_session, user_id, _make_request())
        assert response is not None

        game = await db_session.get(Game, response.game_id)
        assert game is not None
        headers = _reparse_stored_pgn(game.pgn)

        assert headers["White"] == game.white_username
        assert headers["Black"] == game.black_username
        assert game.white_rating is not None
        assert int(headers["WhiteElo"]) == game.white_rating
        assert game.black_rating is not None
        assert int(headers["BlackElo"]) == game.black_rating
        assert game.opening_eco is not None
        assert headers["ECO"] == game.opening_eco
        assert game.opening_name is not None
        assert headers["Opening"] == game.opening_name
        assert headers["Result"] == game.result
        assert headers["Termination"] == game.termination

    async def test_no_anchor_omits_white_elo_and_rating_source(
        self, db_session: AsyncSession
    ) -> None:
        user_id = _TEST_USER_ID + 12
        await ensure_test_user(db_session, user_id)

        response = await store_bot_game(db_session, user_id, _make_request())
        assert response is not None

        game = await db_session.get(Game, response.game_id)
        assert game is not None
        assert game.white_rating is None
        headers = _reparse_stored_pgn(game.pgn)

        assert "WhiteElo" not in headers
        assert "RatingSource" not in headers
        assert headers["BlackElo"] == str(_TEST_BOT_ELO)

    async def test_user_plays_black_gets_white_title_on_bot(self, db_session: AsyncSession) -> None:
        user_id = _TEST_USER_ID + 13
        await ensure_test_user(db_session, user_id)

        response = await store_bot_game(db_session, user_id, _make_request(user_color="black"))
        assert response is not None

        game = await db_session.get(Game, response.game_id)
        assert game is not None
        headers = _reparse_stored_pgn(game.pgn)

        assert headers["WhiteTitle"] == "BOT"
        assert "BlackTitle" not in headers

    async def test_clk_survives_end_to_end(self, db_session: AsyncSession) -> None:
        user_id = _TEST_USER_ID + 14
        await ensure_test_user(db_session, user_id)

        response = await store_bot_game(db_session, user_id, _make_request())
        assert response is not None

        game = await db_session.get(Game, response.game_id)
        assert game is not None
        reparsed = chess.pgn.read_game(io.StringIO(game.pgn))
        assert reparsed is not None
        nodes = list(reparsed.mainline())
        assert nodes
        white_to_move = reparsed.board().turn
        white_clocks = [n.clock() for i, n in enumerate(nodes) if (i % 2 == 0) == white_to_move]
        black_clocks = [n.clock() for i, n in enumerate(nodes) if (i % 2 == 0) != white_to_move]
        assert white_clocks and all(c is not None for c in white_clocks)
        assert black_clocks and all(c is not None for c in black_clocks)

    async def test_duplicate_resubmit_does_not_rewrite_pgn(self, db_session: AsyncSession) -> None:
        """D-11: a re-submit with a forged PGN + different bot_elo must not
        overwrite the stored row's PGN (T-qaj-03).
        """
        user_id = _TEST_USER_ID + 15
        await ensure_test_user(db_session, user_id)
        game_uuid = str(uuid.uuid4())

        first_request = _make_request(game_uuid=game_uuid)
        first = await store_bot_game(db_session, user_id, first_request)
        assert first is not None
        assert first.created is True

        first_game = await db_session.get(Game, first.game_id)
        assert first_game is not None
        first_pgn = first_game.pgn

        second_request = _make_request(
            game_uuid=game_uuid, pgn=_PGN_CHECKMATE_ALT, bot_elo=_TEST_BOT_ELO + 200
        )
        second = await store_bot_game(db_session, user_id, second_request)
        assert second is not None
        assert second.created is False
        assert second.game_id == first.game_id

        # Refresh/expire the ORM identity map so the re-read hits the DB, not
        # a cached in-memory instance.
        db_session.expire_all()
        reread_game = await db_session.get(Game, first.game_id)
        assert reread_game is not None
        assert reread_game.pgn == first_pgn
