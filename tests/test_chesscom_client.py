"""Tests for the chess.com API client.

Uses unittest.mock to patch httpx.AsyncClient.get to avoid real HTTP calls.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.chesscom_client import fetch_chesscom_games, _archive_before_timestamp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_game(
    uuid: str = "game-uuid-1",
    rules: str = "chess",
    username: str = "testuser",
    white_username: str = "testuser",
    black_username: str = "opponent",
    time_control: str = "600+0",
    rated: bool = True,
) -> dict:
    """Build a minimal chess.com game dict."""
    return {
        "uuid": uuid,
        "url": f"https://www.chess.com/game/live/{uuid}",
        "pgn": "[White \"testuser\"]\n1. e4 e5 *",
        "time_control": time_control,
        "rated": rated,
        "rules": rules,
        "white": {
            "username": white_username,
            "rating": 1200,
            "result": "win" if white_username == username else "checkmated",
        },
        "black": {
            "username": black_username,
            "rating": 1100,
            "result": "checkmated" if white_username == username else "win",
        },
        "end_time": 1700000000,
        "eco": "https://www.chess.com/openings/C50",
    }


def _make_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Build a mock httpx response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# _archive_before_timestamp helper
# ---------------------------------------------------------------------------

class TestArchiveBeforeTimestamp:
    def test_old_archive_is_before(self):
        """An archive from 2020/01 should be before a 2024 timestamp."""
        since = datetime(2024, 1, 1, tzinfo=timezone.utc)
        url = "https://api.chess.com/pub/player/testuser/games/2020/01"
        assert _archive_before_timestamp(url, since) is True

    def test_current_archive_is_not_before(self):
        """An archive from the same month as since should NOT be skipped."""
        since = datetime(2024, 3, 15, tzinfo=timezone.utc)
        url = "https://api.chess.com/pub/player/testuser/games/2024/03"
        assert _archive_before_timestamp(url, since) is False

    def test_future_archive_is_not_before(self):
        """A future archive is not before since."""
        since = datetime(2023, 6, 1, tzinfo=timezone.utc)
        url = "https://api.chess.com/pub/player/testuser/games/2024/01"
        assert _archive_before_timestamp(url, since) is False

    def test_previous_month_is_before(self):
        """An archive from the month before since should be skipped."""
        since = datetime(2024, 4, 1, tzinfo=timezone.utc)
        url = "https://api.chess.com/pub/player/testuser/games/2024/03"
        assert _archive_before_timestamp(url, since) is True


# ---------------------------------------------------------------------------
# fetch_chesscom_games
# ---------------------------------------------------------------------------

class TestFetchChesscomGames:

    @pytest.mark.asyncio
    async def test_valid_username_yields_normalized_games(self):
        """Should yield a normalized game dict for a standard chess game."""
        archives_resp = _make_response(
            {"archives": ["https://api.chess.com/pub/player/testuser/games/2024/03"]}
        )
        games_resp = _make_response({"games": [_make_game()]})

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[archives_resp, games_resp])

        with patch("app.services.chesscom_client.asyncio.sleep", new=AsyncMock()):
            results = []
            async for game in fetch_chesscom_games(mock_client, "testuser", user_id=1):
                results.append(game)

        assert len(results) == 1
        assert results[0]["platform"] == "chess.com"
        assert results[0]["platform_game_id"] == "game-uuid-1"
        assert results[0]["user_id"] == 1

    @pytest.mark.asyncio
    async def test_404_raises_value_error(self):
        """Should raise ValueError when the chess.com user is not found."""
        not_found_resp = _make_response({}, status_code=404)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=not_found_resp)

        with pytest.raises(ValueError, match="chess.com user 'unknown_user' not found"):
            async for _ in fetch_chesscom_games(mock_client, "unknown_user", user_id=1):
                pass

    @pytest.mark.asyncio
    async def test_user_agent_header_sent(self):
        """Should include the User-Agent header on every request."""
        archives_resp = _make_response({"archives": []})

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=archives_resp)

        with patch("app.services.chesscom_client.asyncio.sleep", new=AsyncMock()):
            async for _ in fetch_chesscom_games(mock_client, "testuser", user_id=1):
                pass

        call_kwargs = mock_client.get.call_args_list[0][1]
        headers = call_kwargs.get("headers", {})
        assert "User-Agent" in headers
        assert "FlawChess" in headers["User-Agent"]

    @pytest.mark.asyncio
    async def test_incremental_sync_skips_old_months(self):
        """Should skip archive months that end before since_timestamp."""
        # Two archives: one old (should be skipped), one current (should be fetched)
        archives_resp = _make_response(
            {
                "archives": [
                    "https://api.chess.com/pub/player/testuser/games/2020/01",  # old
                    "https://api.chess.com/pub/player/testuser/games/2024/03",  # current
                ]
            }
        )
        games_resp = _make_response({"games": [_make_game()]})

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[archives_resp, games_resp])

        since = datetime(2024, 1, 1, tzinfo=timezone.utc)

        with patch("app.services.chesscom_client.asyncio.sleep", new=AsyncMock()):
            results = []
            async for game in fetch_chesscom_games(
                mock_client, "testuser", user_id=1, since_timestamp=since
            ):
                results.append(game)

        # Only the 2024/03 archive should have been fetched (1 game)
        # The archives call + 1 game archive call = 2 total calls (not 3)
        assert mock_client.get.call_count == 2
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_non_standard_variant_games_skipped(self):
        """Games with rules != 'chess' should be filtered out."""
        archives_resp = _make_response(
            {"archives": ["https://api.chess.com/pub/player/testuser/games/2024/03"]}
        )
        games_resp = _make_response(
            {
                "games": [
                    _make_game(uuid="chess960-game", rules="chess960"),
                    _make_game(uuid="standard-game", rules="chess"),
                ]
            }
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[archives_resp, games_resp])

        with patch("app.services.chesscom_client.asyncio.sleep", new=AsyncMock()):
            results = []
            async for game in fetch_chesscom_games(mock_client, "testuser", user_id=1):
                results.append(game)

        assert len(results) == 1
        assert results[0]["platform_game_id"] == "standard-game"

    @pytest.mark.asyncio
    async def test_on_game_fetched_callback_called(self):
        """on_game_fetched should be called once for each yielded game."""
        archives_resp = _make_response(
            {"archives": ["https://api.chess.com/pub/player/testuser/games/2024/03"]}
        )
        games_resp = _make_response(
            {"games": [_make_game(uuid="g1"), _make_game(uuid="g2")]}
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[archives_resp, games_resp])

        callback = MagicMock()

        with patch("app.services.chesscom_client.asyncio.sleep", new=AsyncMock()):
            async for _ in fetch_chesscom_games(
                mock_client, "testuser", user_id=1, on_game_fetched=callback
            ):
                pass

        assert callback.call_count == 2

    @pytest.mark.asyncio
    async def test_429_backs_off_and_retries(self):
        """On 429 response, should sleep 60s then retry once."""
        archives_resp = _make_response(
            {"archives": ["https://api.chess.com/pub/player/testuser/games/2024/03"]}
        )
        rate_limited_resp = _make_response({}, status_code=429)
        games_resp = _make_response({"games": [_make_game()]})

        mock_client = AsyncMock()
        # archives OK, first archive call → 429, retry → success
        mock_client.get = AsyncMock(
            side_effect=[archives_resp, rate_limited_resp, games_resp]
        )

        sleep_mock = AsyncMock()
        with patch("app.services.chesscom_client.asyncio.sleep", new=sleep_mock):
            results = []
            async for game in fetch_chesscom_games(mock_client, "testuser", user_id=1):
                results.append(game)

        # Should have slept at least once for 60 seconds (backoff)
        sleep_calls = [call.args[0] for call in sleep_mock.call_args_list]
        assert 60 in sleep_calls
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_empty_archives_yields_nothing(self):
        """A user with no archives should yield nothing."""
        archives_resp = _make_response({"archives": []})

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=archives_resp)

        with patch("app.services.chesscom_client.asyncio.sleep", new=AsyncMock()):
            results = []
            async for game in fetch_chesscom_games(mock_client, "testuser", user_id=1):
                results.append(game)

        assert results == []

    @pytest.mark.asyncio
    async def test_410_on_archives_raises_value_error(self):
        """410 on archives endpoint (e.g. email-format username) should raise ValueError."""
        gone_resp = _make_response({}, status_code=410)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=gone_resp)

        with patch("app.services.chesscom_client.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(ValueError, match="chess.com request failed"):
                async for _ in fetch_chesscom_games(
                    mock_client, "user@domain.com", user_id=1
                ):
                    pass

    @pytest.mark.asyncio
    async def test_403_on_archives_raises_value_error(self):
        """403 on archives endpoint should raise ValueError."""
        forbidden_resp = _make_response({}, status_code=403)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=forbidden_resp)

        with patch("app.services.chesscom_client.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(ValueError, match="chess.com request failed"):
                async for _ in fetch_chesscom_games(
                    mock_client, "testuser", user_id=1
                ):
                    pass

    @pytest.mark.asyncio
    async def test_500_on_archives_raises_value_error(self):
        """500 on archives endpoint should raise ValueError."""
        server_error_resp = _make_response({}, status_code=500)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=server_error_resp)

        with patch("app.services.chesscom_client.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(ValueError, match="chess.com request failed"):
                async for _ in fetch_chesscom_games(
                    mock_client, "testuser", user_id=1
                ):
                    pass

    @pytest.mark.asyncio
    async def test_500_on_archive_fetch_skips_archive(self):
        """500 on a per-archive fetch should skip that archive, not raise."""
        archives_resp = _make_response(
            {"archives": ["https://api.chess.com/pub/player/testuser/games/2024/03"]}
        )
        server_error_resp = _make_response({}, status_code=500)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[archives_resp, server_error_resp])

        with patch("app.services.chesscom_client.asyncio.sleep", new=AsyncMock()):
            results = []
            async for game in fetch_chesscom_games(mock_client, "testuser", user_id=1):
                results.append(game)

        assert results == []

    @pytest.mark.asyncio
    async def test_410_on_archive_fetch_skips_archive(self):
        """410 on a per-archive fetch should skip that archive gracefully."""
        archives_resp = _make_response(
            {"archives": ["https://api.chess.com/pub/player/testuser/games/2024/03"]}
        )
        gone_resp = _make_response({}, status_code=410)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[archives_resp, gone_resp])

        with patch("app.services.chesscom_client.asyncio.sleep", new=AsyncMock()):
            results = []
            async for game in fetch_chesscom_games(mock_client, "testuser", user_id=1):
                results.append(game)

        assert results == []
