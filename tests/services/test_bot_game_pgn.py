"""Unit tests for stamp_bot_game_headers (quick-260714-qaj).

Pure, no DB, no session — NormalizedGame fixtures are constructed directly.
Every assertion re-parses the returned PGN string with chess.pgn.read_game and
asserts on the PARSED headers, never by string-matching the raw PGN text.
"""

import datetime
import io
from typing import Literal

import chess.pgn
import pytest

from app.core.config import settings
from app.schemas.normalization import NormalizedGame
from app.services.bot_game_pgn import stamp_bot_game_headers

_TEST_GAME_ID = 693117
_TEST_UUID = "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"
_TEST_PLAYED_AT = datetime.datetime(2026, 7, 14, 16, 20, 42, tzinfo=datetime.UTC)

# Scholar's-Mate-with-[%clk] PGN, mirroring test_store_bot_game_service.py's
# _PGN_CHECKMATE fixture shape, so the clk-survival assertion has real clock
# comments to preserve.
_PGN_CHECKMATE = (
    '[Event "?"]\n[Result "1-0"]\n\n'
    "1. e4 {[%clk 0:03:00]} e5 {[%clk 0:03:00]} "
    "2. Bc4 {[%clk 0:02:58]} Nc6 {[%clk 0:02:58]} "
    "3. Qh5 {[%clk 0:02:56]} Nf6 {[%clk 0:02:56]} "
    "4. Qxf7# {[%clk 0:02:54]} 1-0\n"
)

# The exact D-03 order, for the happy-path anchored/user=white case.
_EXPECTED_ORDER_WHITE_ANCHORED = [
    "Event",
    "Site",
    "Date",
    "Round",
    "White",
    "Black",
    "Result",
    "GameId",
    "UTCDate",
    "UTCTime",
    "WhiteElo",
    "BlackElo",
    "BlackTitle",
    "Variant",
    "TimeControl",
    "ECO",
    "Opening",
    "Termination",
    "RatingSource",
    "PlayStyleBlend",
]


def _make_normalized(
    *,
    user_color: Literal["white", "black"] = "white",
    white_rating: int | None = 1788,
    black_rating: int | None = 1100,
    opening_eco: str | None = "A40",
    opening_name: str | None = "Englund Gambit",
    played_at: datetime.datetime | None = _TEST_PLAYED_AT,
    pgn: str = _PGN_CHECKMATE,
    white_username: str = "aimfeld",
    black_username: str = "FlawChess Bot",
) -> NormalizedGame:
    return NormalizedGame(
        user_id=1,
        platform="flawchess",
        platform_game_id=_TEST_UUID,
        platform_url=None,
        pgn=pgn,
        result="1-0",
        user_color=user_color,
        termination_raw="checkmate",
        termination="checkmate",
        time_control_str="600",
        time_control_bucket="rapid",
        time_control_seconds=600,
        rated=False,
        is_computer_game=True,
        white_username=white_username,
        black_username=black_username,
        white_rating=white_rating,
        black_rating=black_rating,
        opening_name=opening_name,
        opening_eco=opening_eco,
        white_accuracy=None,
        black_accuracy=None,
        played_at=played_at,
    )


def _reparse(pgn_text: str) -> chess.pgn.Game:
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    assert game is not None
    return game


class TestHappyPath:
    def test_full_d03_header_block(self) -> None:
        normalized = _make_normalized()
        pgn = stamp_bot_game_headers(
            normalized=normalized,
            game_id=_TEST_GAME_ID,
            tc_preset="600+0",
            rating_source="blended",
            play_style_blend=0.5,
        )
        headers = _reparse(pgn).headers

        assert headers["Event"] == "FlawChess bot game"
        assert headers["Site"] == f"{settings.FRONTEND_URL.rstrip('/')}/analysis?game_id=693117"
        assert headers["Date"] == "2026.07.14"
        assert headers["UTCDate"] == "2026.07.14"
        assert headers["UTCTime"] == "16:20:42"
        assert headers["Round"] == "-"
        assert headers["White"] == "aimfeld"
        assert headers["Black"] == "FlawChess Bot"
        assert headers["Result"] == "1-0"
        assert headers["GameId"] == _TEST_UUID
        assert headers["WhiteElo"] == "1788"
        assert headers["BlackElo"] == "1100"
        assert headers["BlackTitle"] == "BOT"
        assert "WhiteTitle" not in headers
        assert headers["Variant"] == "Standard"
        assert headers["TimeControl"] == "600+0"
        assert headers["ECO"] == "A40"
        assert headers["Opening"] == "Englund Gambit"
        assert headers["Termination"] == "checkmate"
        assert headers["RatingSource"] == "blended"
        assert headers["PlayStyleBlend"] == "0.50"

    def test_header_order_matches_d03_exactly(self) -> None:
        normalized = _make_normalized()
        pgn = stamp_bot_game_headers(
            normalized=normalized,
            game_id=_TEST_GAME_ID,
            tc_preset="600+0",
            rating_source="blended",
            play_style_blend=0.5,
        )
        reparsed = _reparse(pgn)
        keys = list(reparsed.headers.keys())
        assert keys == _EXPECTED_ORDER_WHITE_ANCHORED
        # D-06: non-standard tags emitted LAST.
        assert keys[-2:] == ["RatingSource", "PlayStyleBlend"]


class TestD05Omission:
    def test_no_anchor_omits_white_elo_and_rating_source(self) -> None:
        normalized = _make_normalized(white_rating=None)
        pgn = stamp_bot_game_headers(
            normalized=normalized,
            game_id=_TEST_GAME_ID,
            tc_preset="600+0",
            rating_source=None,
            play_style_blend=0.5,
        )
        headers = _reparse(pgn).headers
        assert "WhiteElo" not in headers
        assert "RatingSource" not in headers
        assert headers["BlackElo"] == "1100"

    def test_opening_none_omits_eco_and_opening(self) -> None:
        normalized = _make_normalized(opening_eco=None, opening_name=None)
        pgn = stamp_bot_game_headers(
            normalized=normalized,
            game_id=_TEST_GAME_ID,
            tc_preset="600+0",
            rating_source="blended",
            play_style_blend=0.5,
        )
        headers = _reparse(pgn).headers
        assert "ECO" not in headers
        assert "Opening" not in headers


class TestUserColorBlack:
    def test_black_user_gets_white_title_on_bot(self) -> None:
        normalized = _make_normalized(
            user_color="black",
            white_username="FlawChess Bot",
            black_username="aimfeld",
            white_rating=1100,
            black_rating=1788,
        )
        pgn = stamp_bot_game_headers(
            normalized=normalized,
            game_id=_TEST_GAME_ID,
            tc_preset="600+0",
            rating_source="blended",
            play_style_blend=0.5,
        )
        headers = _reparse(pgn).headers
        assert headers["WhiteTitle"] == "BOT"
        assert "BlackTitle" not in headers
        assert headers["WhiteElo"] == "1100"
        assert headers["BlackElo"] == "1788"


class TestClockSurvival:
    def test_clk_survives_on_both_colors(self) -> None:
        normalized = _make_normalized()
        pgn = stamp_bot_game_headers(
            normalized=normalized,
            game_id=_TEST_GAME_ID,
            tc_preset="600+0",
            rating_source="blended",
            play_style_blend=0.5,
        )
        reparsed = _reparse(pgn)
        nodes = list(reparsed.mainline())
        assert nodes  # sanity: moves survived
        white_to_move = reparsed.board().turn
        for i, node in enumerate(nodes):
            assert node.clock() is not None, f"ply {i} lost its [%clk]"
        # Explicit both-colors check (parity vs starting side).
        white_clocks = [
            node.clock() for i, node in enumerate(nodes) if (i % 2 == 0) == white_to_move
        ]
        black_clocks = [
            node.clock() for i, node in enumerate(nodes) if (i % 2 == 0) != white_to_move
        ]
        assert all(c is not None for c in white_clocks)
        assert all(c is not None for c in black_clocks)


class TestPlayStyleBlendFormatting:
    def test_formats_to_two_decimals(self) -> None:
        for value, expected in [(0.5, "0.50"), (1.0, "1.00"), (0.0, "0.00")]:
            normalized = _make_normalized()
            pgn = stamp_bot_game_headers(
                normalized=normalized,
                game_id=_TEST_GAME_ID,
                tc_preset="600+0",
                rating_source="blended",
                play_style_blend=value,
            )
            headers = _reparse(pgn).headers
            assert headers["PlayStyleBlend"] == expected


class TestFrontendUrlTrailingSlash:
    def test_no_double_slash_with_trailing_slash(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(settings, "FRONTEND_URL", "https://flawchess.com/")
        normalized = _make_normalized()
        pgn = stamp_bot_game_headers(
            normalized=normalized,
            game_id=_TEST_GAME_ID,
            tc_preset="600+0",
            rating_source="blended",
            play_style_blend=0.5,
        )
        headers = _reparse(pgn).headers
        assert headers["Site"] == "https://flawchess.com/analysis?game_id=693117"
        assert "//analysis" not in headers["Site"]
