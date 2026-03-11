"""Tests for the lichess API client.

Uses unittest.mock to simulate httpx streaming responses without real HTTP calls.
"""

import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.lichess_client import fetch_lichess_games


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_lichess_game(
    game_id: str = "abcd1234",
    variant_key: str = "standard",
    username: str = "testuser",
    white_username: str = "testuser",
    black_username: str = "opponent",
    time_control: tuple[int, int] = (600, 0),
    rated: bool = True,
    winner: str | None = "white",
) -> dict:
    """Build a minimal lichess NDJSON game dict."""
    return {
        "id": game_id,
        "variant": {"key": variant_key, "name": "Standard"},
        "players": {
            "white": {
                "user": {"name": white_username},
                "rating": 1200,
            },
            "black": {
                "user": {"name": black_username},
                "rating": 1100,
            },
        },
        "rated": rated,
        "winner": winner,
        "clock": {
            "initial": time_control[0],
            "increment": time_control[1],
            "totalTime": time_control[0],
        },
        "createdAt": 1700000000000,
        "opening": {"eco": "C20", "name": "King's Pawn Game"},
        "pgn": "1. e4 e5 *",
    }


async def _aiter_lines(lines: list[str]) -> AsyncIterator[str]:
    """Async generator that yields lines one by one."""
    for line in lines:
        yield line


def _make_streaming_response(
    lines: list[str],
    status_code: int = 200,
) -> MagicMock:
    """Build a mock streaming response context manager.

    Simulates ``async with client.stream(...) as response:``
    then ``async for line in response.aiter_lines():``.
    """
    response = MagicMock()
    response.status_code = status_code
    response.aiter_lines = MagicMock(return_value=_aiter_lines(lines))

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# fetch_lichess_games tests
# ---------------------------------------------------------------------------


class TestFetchLichessGames:

    @pytest.mark.asyncio
    async def test_valid_username_yields_normalized_games(self):
        """Should yield a normalized game dict from a valid NDJSON line."""
        game = _make_lichess_game()
        lines = [json.dumps(game), ""]  # trailing empty line is common

        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=_make_streaming_response(lines))

        results = []
        async for g in fetch_lichess_games(mock_client, "testuser", user_id=1):
            results.append(g)

        assert len(results) == 1
        assert results[0]["platform"] == "lichess"
        assert results[0]["platform_game_id"] == "abcd1234"
        assert results[0]["user_id"] == 1

    @pytest.mark.asyncio
    async def test_404_raises_value_error(self):
        """Should raise ValueError when the lichess user is not found."""
        mock_client = MagicMock()
        mock_client.stream = MagicMock(
            return_value=_make_streaming_response([], status_code=404)
        )

        with pytest.raises(ValueError, match="lichess user 'unknown_user' not found"):
            async for _ in fetch_lichess_games(mock_client, "unknown_user", user_id=1):
                pass

    @pytest.mark.asyncio
    async def test_since_ms_passed_in_params(self):
        """Should include since= in request params when since_ms is provided."""
        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=_make_streaming_response([]))

        async for _ in fetch_lichess_games(
            mock_client, "testuser", user_id=1, since_ms=1700000000000
        ):
            pass

        call_kwargs = mock_client.stream.call_args[1]
        params = call_kwargs.get("params", {})
        assert "since" in params
        assert params["since"] == "1700000000000"

    @pytest.mark.asyncio
    async def test_pgn_in_json_param_included(self):
        """Should always include pgnInJson=true in request params."""
        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=_make_streaming_response([]))

        async for _ in fetch_lichess_games(mock_client, "testuser", user_id=1):
            pass

        call_kwargs = mock_client.stream.call_args[1]
        params = call_kwargs.get("params", {})
        assert params.get("pgnInJson") is True

    @pytest.mark.asyncio
    async def test_non_standard_variant_lines_filtered(self):
        """Games with variant.key != 'standard' should be skipped."""
        standard_game = _make_lichess_game(game_id="std1", variant_key="standard")
        chess960_game = _make_lichess_game(game_id="960", variant_key="chess960")
        lines = [json.dumps(chess960_game), json.dumps(standard_game)]

        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=_make_streaming_response(lines))

        results = []
        async for g in fetch_lichess_games(mock_client, "testuser", user_id=1):
            results.append(g)

        assert len(results) == 1
        assert results[0]["platform_game_id"] == "std1"

    @pytest.mark.asyncio
    async def test_malformed_json_lines_skipped(self):
        """Lines with invalid JSON should be silently skipped."""
        valid_game = _make_lichess_game()
        lines = [
            "not-valid-json{{{{",
            json.dumps(valid_game),
            '{"incomplete":',
        ]

        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=_make_streaming_response(lines))

        results = []
        async for g in fetch_lichess_games(mock_client, "testuser", user_id=1):
            results.append(g)

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_on_game_fetched_callback_called(self):
        """on_game_fetched should be called once per yielded game."""
        games = [
            _make_lichess_game(game_id="g1"),
            _make_lichess_game(game_id="g2"),
        ]
        lines = [json.dumps(g) for g in games]

        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=_make_streaming_response(lines))

        callback = MagicMock()

        async for _ in fetch_lichess_games(
            mock_client, "testuser", user_id=1, on_game_fetched=callback
        ):
            pass

        assert callback.call_count == 2

    @pytest.mark.asyncio
    async def test_since_ms_absent_when_not_provided(self):
        """When since_ms is None, the 'since' key should not appear in params."""
        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=_make_streaming_response([]))

        async for _ in fetch_lichess_games(mock_client, "testuser", user_id=1):
            pass

        call_kwargs = mock_client.stream.call_args[1]
        params = call_kwargs.get("params", {})
        assert "since" not in params

    @pytest.mark.asyncio
    async def test_accept_ndjson_header(self):
        """Should include Accept: application/x-ndjson header in the request."""
        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=_make_streaming_response([]))

        async for _ in fetch_lichess_games(mock_client, "testuser", user_id=1):
            pass

        call_kwargs = mock_client.stream.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert headers.get("Accept") == "application/x-ndjson"
