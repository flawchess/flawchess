"""Integration tests for the library API router.

Tests the HTTP layer for GET /api/library/games and GET /api/library/flaw-stats
and GET /api/library/flaws.
Uses httpx AsyncClient with ASGITransport to test the FastAPI app directly.

Coverage:
- GET /library/games: requires auth
- GET /library/games?color=white: accepted, returns only white games
- GET /library/games?color=black: accepted, returns only black games
- GET /library/flaw-stats: requires auth
- GET /library/flaw-stats?color=white: accepted, returns 200
- GET /library/flaws: pagination, ordering, severity/tag filter, IDOR isolation,
  phase-tag rejection (Plan 108-05)
- GET /library/games: eval_series/flaw_markers/phase_transitions payload (Plan 109-03)
  — analyzed games carry non-null eval fields, unanalyzed games carry null,
  single batched query (no N+1), IDOR scoping, gzipped payload below threshold.
"""

import datetime
import gzip
import json
import uuid
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import event as sa_event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.main import app

# ---------------------------------------------------------------------------
# Plan 109-03: payload threshold constant (D-05 — no magic number)
# ---------------------------------------------------------------------------
# Max acceptable gzipped bytes for the full GET /library/games response
# when the page contains up to 20 analyzed games with per-ply eval series.
# Research estimate: ~10-15 KB compressed for 20 full series. 40 KB is
# a conservative ceiling that still catches a catastrophic regression.
_EVAL_PAYLOAD_GZIP_CEILING_BYTES: int = 40_960  # 40 KB compressed


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def auth_headers() -> dict[str, str]:
    """Register a user once per module and return auth headers."""
    email = f"library_test_{uuid.uuid4().hex[:8]}@example.com"
    password = "testpassword123"

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.post("/api/auth/register", json={"email": email, "password": password})
        login_resp = await client.post(
            "/api/auth/jwt/login",
            data={"username": email, "password": password},
        )
        token = login_resp.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# GET /library/games
# ---------------------------------------------------------------------------


class TestGetLibraryGames:
    """Tests for GET /library/games."""

    @pytest.mark.asyncio
    async def test_returns_401_without_auth(self) -> None:
        """Request without auth token returns 401."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/library/games")

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_200_with_auth(self, auth_headers: dict[str, str]) -> None:
        """Request with valid auth returns 200 for a new user with no games."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/library/games", headers=auth_headers)

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_structure(self, auth_headers: dict[str, str]) -> None:
        """Response contains games, matched_count, offset, limit keys."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/library/games", headers=auth_headers)

        body = resp.json()
        assert "games" in body
        assert "matched_count" in body
        assert "offset" in body
        assert "limit" in body
        assert isinstance(body["games"], list)
        assert isinstance(body["matched_count"], int)

    @pytest.mark.asyncio
    async def test_color_white_accepted(self, auth_headers: dict[str, str]) -> None:
        """?color=white is accepted and returns the standard games structure."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/games",
                params={"color": "white"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "games" in body
        assert "matched_count" in body
        # For a new user without games, matched_count must be 0 under white filter.
        assert body["matched_count"] == 0

    @pytest.mark.asyncio
    async def test_color_black_accepted(self, auth_headers: dict[str, str]) -> None:
        """?color=black is accepted and returns the standard games structure."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/games",
                params={"color": "black"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "games" in body
        assert body["matched_count"] == 0

    @pytest.mark.asyncio
    async def test_color_white_and_black_counts_match_total(
        self, auth_headers: dict[str, str]
    ) -> None:
        """matched_count(white) + matched_count(black) <= matched_count(unfiltered).

        For a fresh test user with no games all three are 0. The assertion is
        direction-invariant so it stays valid when games are seeded in future.
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp_all = await client.get("/api/library/games", headers=auth_headers)
            resp_white = await client.get(
                "/api/library/games", params={"color": "white"}, headers=auth_headers
            )
            resp_black = await client.get(
                "/api/library/games", params={"color": "black"}, headers=auth_headers
            )

        total = resp_all.json()["matched_count"]
        white_n = resp_white.json()["matched_count"]
        black_n = resp_black.json()["matched_count"]

        assert white_n + black_n <= total


# ---------------------------------------------------------------------------
# GET /library/flaw-stats
# ---------------------------------------------------------------------------


class TestGetFlawStats:
    """Tests for GET /library/flaw-stats."""

    @pytest.mark.asyncio
    async def test_returns_401_without_auth(self) -> None:
        """Request without auth token returns 401."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/library/flaw-stats")

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_200_with_auth(self, auth_headers: dict[str, str]) -> None:
        """Request with valid auth returns 200."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/library/flaw-stats", headers=auth_headers)

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_structure(self, auth_headers: dict[str, str]) -> None:
        """Response has the flaw-stats structure keys."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/library/flaw-stats", headers=auth_headers)

        body = resp.json()
        required = {
            "per_severity_counts",
            "rates",
            "tag_distribution",
            "trend",
            "analyzed_pct",
            "analyzed_n",
            "total_n",
        }
        for field in required:
            assert field in body, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_color_white_accepted(self, auth_headers: dict[str, str]) -> None:
        """?color=white is accepted and returns 200 with the standard flaw-stats structure."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/flaw-stats",
                params={"color": "white"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "total_n" in body
        # For a new user without games, total_n must be 0 under white filter.
        assert body["total_n"] == 0

    @pytest.mark.asyncio
    async def test_color_black_accepted(self, auth_headers: dict[str, str]) -> None:
        """?color=black is accepted and returns 200 with the standard flaw-stats structure."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/flaw-stats",
                params={"color": "black"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_n"] == 0

    @pytest.mark.asyncio
    async def test_color_white_and_black_total_n_sum_matches_unfiltered(
        self, auth_headers: dict[str, str]
    ) -> None:
        """total_n(white) + total_n(black) <= total_n(unfiltered).

        The inequality holds because unfiltered includes any games with NULL
        user_color (rare but possible). For a new user all three are 0.
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp_all = await client.get("/api/library/flaw-stats", headers=auth_headers)
            resp_white = await client.get(
                "/api/library/flaw-stats", params={"color": "white"}, headers=auth_headers
            )
            resp_black = await client.get(
                "/api/library/flaw-stats", params={"color": "black"}, headers=auth_headers
            )

        total = resp_all.json()["total_n"]
        white_n = resp_white.json()["total_n"]
        black_n = resp_black.json()["total_n"]

        assert white_n + black_n <= total


# ---------------------------------------------------------------------------
# Helpers for GET /library/flaws test seeding (committed sessions)
# ---------------------------------------------------------------------------


async def _register_and_login(
    email: str, password: str = "testpassword123"
) -> tuple[dict[str, str], int]:
    """Register a user and return (auth_headers, user_id)."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        reg_resp = await client.post(
            "/api/auth/register", json={"email": email, "password": password}
        )
        user_id = int(reg_resp.json()["id"])
        login_resp = await client.post(
            "/api/auth/jwt/login",
            data={"username": email, "password": password},
        )
        token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, user_id


async def _seed_game_committed(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    user_id: int,
    played_at: datetime.datetime,
    result: str = "1-0",
    user_color: str = "white",
    platform: str = "lichess",
) -> int:
    """Insert and commit a Game row, returning its ID."""
    from app.models.game import Game

    async with session_maker() as session:
        game = Game(
            user_id=user_id,
            platform=platform,
            platform_game_id=str(uuid.uuid4()),
            platform_url="https://lichess.org/test",
            pgn="1. e4 e5 *",
            result=result,
            user_color=user_color,
            time_control_str="600+0",
            time_control_bucket="blitz",
            time_control_seconds=600,
            base_time_seconds=600,
            increment_seconds=0.0,
            rated=True,
            is_computer_game=False,
            played_at=played_at,
        )
        session.add(game)
        await session.commit()
        await session.refresh(game)
        return game.id


async def _seed_flaw_committed(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    user_id: int,
    game_id: int,
    ply: int,
    severity: int = 2,  # 2=blunder
    tempo: int | None = None,
    phase: int = 1,  # 1=middlegame
    is_miss: bool = False,
    is_lucky: bool = False,
    is_reversed: bool = False,
    is_squandered: bool = False,
    fen: str = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1",
    move_san: str | None = "e4",
    es_before: float = 0.9,
    es_after: float = 0.3,
) -> None:
    """Insert and commit a GameFlaw row."""
    from app.models.game_flaw import GameFlaw

    async with session_maker() as session:
        flaw = GameFlaw(
            user_id=user_id,
            game_id=game_id,
            ply=ply,
            severity=severity,
            tempo=tempo,
            phase=phase,
            is_miss=is_miss,
            is_lucky=is_lucky,
            is_reversed=is_reversed,
            is_squandered=is_squandered,
            es_before=es_before,
            es_after=es_after,
            move_san=move_san,
            fen=fen,
        )
        session.add(flaw)
        await session.commit()


# ---------------------------------------------------------------------------
# GET /library/flaws — pagination, ordering, filtering, IDOR (Plan 108-05)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def flaws_test_state(test_engine: Any) -> dict[str, Any]:
    """Seed two users with committed game_flaws rows for GET /library/flaws tests.

    User A has 3 games (with distinct played_at) and several flaws per game.
    User B has 1 game + 1 flaw — used for IDOR isolation test.

    Committed to DB (not rolled back) so the ASGI client's sessions see the data.
    Returns: headers_a, headers_b, user_a_id, user_b_id, game_ids_a (list[int]).
    """
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

    suffix = uuid.uuid4().hex[:8]
    headers_a, user_a_id = await _register_and_login(f"flaws_a_{suffix}@example.com")
    headers_b, user_b_id = await _register_and_login(f"flaws_b_{suffix}@example.com")

    # Game A1 — oldest (played_at Jan 1)
    game_a1 = await _seed_game_committed(
        session_maker,
        user_id=user_a_id,
        played_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
        result="0-1",
        user_color="black",
    )
    # Flaws on game A1: ply 4 (blunder), ply 8 (mistake, reversed)
    await _seed_flaw_committed(
        session_maker,
        user_id=user_a_id,
        game_id=game_a1,
        ply=4,
        severity=2,
        phase=0,  # blunder, opening
    )
    await _seed_flaw_committed(
        session_maker,
        user_id=user_a_id,
        game_id=game_a1,
        ply=8,
        severity=1,
        phase=1,
        is_reversed=True,  # mistake, reversed
    )

    # Game A2 — middle (played_at Feb 1)
    game_a2 = await _seed_game_committed(
        session_maker,
        user_id=user_a_id,
        played_at=datetime.datetime(2026, 2, 1, tzinfo=datetime.timezone.utc),
        result="1-0",
        user_color="white",
    )
    # Flaws on game A2: ply 2 (blunder, miss), ply 6 (blunder, low-clock)
    await _seed_flaw_committed(
        session_maker,
        user_id=user_a_id,
        game_id=game_a2,
        ply=2,
        severity=2,
        phase=1,
        is_miss=True,
    )
    await _seed_flaw_committed(
        session_maker,
        user_id=user_a_id,
        game_id=game_a2,
        ply=6,
        severity=2,
        phase=1,
        tempo=0,  # low-clock
    )

    # Game A3 — newest (played_at Mar 1)
    game_a3 = await _seed_game_committed(
        session_maker,
        user_id=user_a_id,
        played_at=datetime.datetime(2026, 3, 1, tzinfo=datetime.timezone.utc),
        result="1-0",
        user_color="white",
    )
    # Flaws on game A3: ply 10 (mistake)
    await _seed_flaw_committed(
        session_maker,
        user_id=user_a_id,
        game_id=game_a3,
        ply=10,
        severity=1,
        phase=2,  # mistake, endgame
    )

    # User B: one game + one flaw (used for IDOR test)
    game_b1 = await _seed_game_committed(
        session_maker,
        user_id=user_b_id,
        played_at=datetime.datetime(2026, 3, 15, tzinfo=datetime.timezone.utc),
        result="0-1",
        user_color="black",
    )
    await _seed_flaw_committed(
        session_maker,
        user_id=user_b_id,
        game_id=game_b1,
        ply=5,
        severity=2,
    )

    return {
        "headers_a": headers_a,
        "headers_b": headers_b,
        "user_a_id": user_a_id,
        "user_b_id": user_b_id,
        "game_a1": game_a1,
        "game_a2": game_a2,
        "game_a3": game_a3,
        "game_b1": game_b1,
    }


class TestGetLibraryGamesTagFilter:
    """Tests for tag filtering on GET /library/games.

    The Games subtab must restrict to games containing >=1 flaw matching the
    combined tag filter (single-flaw EXISTS: OR within family, AND across
    families, SEED-038) — the same semantics the Flaws subtab uses. Reuses the
    flaws_test_state fixture, whose user A has 3 games:
      game_a1 — reversed (impact family), blunder
      game_a2 — miss (opportunity family), low-clock (tempo family)
      game_a3 — mistake only (no curated tags)
    """

    @pytest.mark.asyncio
    async def test_no_tag_returns_all_user_games(self, flaws_test_state: dict[str, Any]) -> None:
        """Without a tag filter, all 3 of user A's games match."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/library/games", headers=flaws_test_state["headers_a"])
        assert resp.status_code == 200
        assert resp.json()["matched_count"] == 3

    @pytest.mark.asyncio
    async def test_tag_reversed_matches_only_its_game(
        self, flaws_test_state: dict[str, Any]
    ) -> None:
        """?tag=reversed returns only the game with that flaw (game_a1)."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/games",
                params={"tag": "reversed"},
                headers=flaws_test_state["headers_a"],
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["matched_count"] == 1
        assert body["games"][0]["game_id"] == flaws_test_state["game_a1"]

    @pytest.mark.asyncio
    async def test_tag_low_clock_matches_only_its_game(
        self, flaws_test_state: dict[str, Any]
    ) -> None:
        """?tag=low-clock returns only the game with that flaw (game_a2)."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/games",
                params={"tag": "low-clock"},
                headers=flaws_test_state["headers_a"],
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["matched_count"] == 1
        assert body["games"][0]["game_id"] == flaws_test_state["game_a2"]

    @pytest.mark.asyncio
    async def test_cross_family_tags_require_single_flaw_match(
        self, flaws_test_state: dict[str, Any]
    ) -> None:
        """Combining tags from different families needs ONE flaw with both.

        reversed (impact) and low-clock (tempo) live in different games,
        so no single flaw satisfies both families → 0 games match. This is the
        AND-across-families / single-flaw EXISTS semantics (SEED-038), and the
        exact behaviour that was broken (tags silently dropped) for the Games tab.
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/games",
                params={"tag": ["reversed", "low-clock"]},
                headers=flaws_test_state["headers_a"],
            )
        assert resp.status_code == 200
        assert resp.json()["matched_count"] == 0

    @pytest.mark.asyncio
    async def test_phase_tag_rejected_422(self, flaws_test_state: dict[str, Any]) -> None:
        """Phase tags (display-only) in ?tag= are rejected, matching /flaws."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/games",
                params={"tag": "opening"},
                headers=flaws_test_state["headers_a"],
            )
        assert resp.status_code == 422


class TestGetLibraryFlaws:
    """Tests for GET /library/flaws (Plan 108-05: pagination, ordering, filters, IDOR)."""

    @pytest.mark.asyncio
    async def test_returns_401_without_auth(self) -> None:
        """Request without auth token returns 401."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/library/flaws")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_200_with_auth(self, flaws_test_state: dict[str, Any]) -> None:
        """Authenticated request returns 200 with the LibraryFlawsResponse structure."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/library/flaws", headers=flaws_test_state["headers_a"])
        assert resp.status_code == 200
        body = resp.json()
        assert "flaws" in body
        assert "matched_count" in body
        assert "offset" in body
        assert "limit" in body
        assert isinstance(body["flaws"], list)
        assert isinstance(body["matched_count"], int)

    @pytest.mark.asyncio
    async def test_default_limit_is_20(self, flaws_test_state: dict[str, Any]) -> None:
        """Default limit in the response is 20 per D-08."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/library/flaws", headers=flaws_test_state["headers_a"])
        assert resp.status_code == 200
        assert resp.json()["limit"] == 20

    @pytest.mark.asyncio
    async def test_ordering_recent_first_then_ply_asc(
        self, flaws_test_state: dict[str, Any]
    ) -> None:
        """Flaws are ordered played_at DESC then ply ASC (D-07).

        User A has flaws across 3 games (Jan, Feb, Mar). Expected order:
          game_a3 ply 10 → game_a2 ply 2 → game_a2 ply 6 → game_a1 ply 4 → game_a1 ply 8
        (newest game first; within a game, lower ply first).
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/flaws",
                params={"limit": 10},
                headers=flaws_test_state["headers_a"],
            )
        assert resp.status_code == 200
        body = resp.json()
        flaws = body["flaws"]

        # matched_count must include all 5 user A flaws
        assert body["matched_count"] == 5
        assert len(flaws) == 5

        # Check game_id + ply order
        game_a3 = flaws_test_state["game_a3"]
        game_a2 = flaws_test_state["game_a2"]
        game_a1 = flaws_test_state["game_a1"]

        expected = [
            (game_a3, 10),
            (game_a2, 2),
            (game_a2, 6),
            (game_a1, 4),
            (game_a1, 8),
        ]
        actual = [(f["game_id"], f["ply"]) for f in flaws]
        assert actual == expected, f"Expected order {expected}, got {actual}"

    @pytest.mark.asyncio
    async def test_pagination_offset_returns_next_rows(
        self, flaws_test_state: dict[str, Any]
    ) -> None:
        """Offset-based pagination returns the correct next page of rows."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp_p1 = await client.get(
                "/api/library/flaws",
                params={"limit": 3, "offset": 0},
                headers=flaws_test_state["headers_a"],
            )
            resp_p2 = await client.get(
                "/api/library/flaws",
                params={"limit": 3, "offset": 3},
                headers=flaws_test_state["headers_a"],
            )

        assert resp_p1.status_code == 200
        assert resp_p2.status_code == 200
        body1 = resp_p1.json()
        body2 = resp_p2.json()

        # Both pages report the same total
        assert body1["matched_count"] == 5
        assert body2["matched_count"] == 5

        # Page 1: first 3 rows; page 2: remaining 2 rows
        assert len(body1["flaws"]) == 3
        assert len(body2["flaws"]) == 2

        # No overlap between pages
        p1_keys = {(f["game_id"], f["ply"]) for f in body1["flaws"]}
        p2_keys = {(f["game_id"], f["ply"]) for f in body2["flaws"]}
        assert p1_keys.isdisjoint(p2_keys)

    @pytest.mark.asyncio
    async def test_severity_filter_blunder_only(self, flaws_test_state: dict[str, Any]) -> None:
        """?severity=blunder returns only blunder rows (severity int == 2)."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/flaws",
                params={"severity": "blunder"},
                headers=flaws_test_state["headers_a"],
            )
        assert resp.status_code == 200
        body = resp.json()
        flaws = body["flaws"]
        # User A has 3 blunders (game_a1 ply4, game_a2 ply2, game_a2 ply6)
        assert body["matched_count"] == 3
        for flaw in flaws:
            assert flaw["severity"] == "blunder", f"Expected blunder, got {flaw['severity']}"

    @pytest.mark.asyncio
    async def test_severity_filter_mistake_only(self, flaws_test_state: dict[str, Any]) -> None:
        """?severity=mistake uses set-membership: returns mistakes ONLY (not blunders).

        The shared build_flaw_filter_clauses uses set-membership semantics: the UI
        exposes Blunders/Mistakes as independent toggles, so selecting 'mistake'
        matches mistakes only and 'blunder' matches blunders only. (A prior
        MIN-threshold leaked blunders into a mistakes-only selection.)
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp_m = await client.get(
                "/api/library/flaws",
                params={"severity": "mistake"},
                headers=flaws_test_state["headers_a"],
            )
            resp_b = await client.get(
                "/api/library/flaws",
                params={"severity": "blunder"},
                headers=flaws_test_state["headers_a"],
            )
        # "mistake" only → 2 mistakes (game_a1 ply8, game_a3 ply10)
        assert resp_m.status_code == 200
        assert resp_m.json()["matched_count"] == 2
        for flaw in resp_m.json()["flaws"]:
            assert flaw["severity"] == "mistake"
        # "blunder" only → 3 blunders
        assert resp_b.status_code == 200
        assert resp_b.json()["matched_count"] == 3
        for flaw in resp_b.json()["flaws"]:
            assert flaw["severity"] == "blunder"

    @pytest.mark.asyncio
    async def test_tag_filter_reversed(self, flaws_test_state: dict[str, Any]) -> None:
        """?tag=reversed returns only rows with is_reversed=True."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/flaws",
                params={"tag": "reversed"},
                headers=flaws_test_state["headers_a"],
            )
        assert resp.status_code == 200
        body = resp.json()
        # Only game_a1 ply8 has is_reversed=True
        assert body["matched_count"] == 1
        flaw = body["flaws"][0]
        assert flaw["game_id"] == flaws_test_state["game_a1"]
        assert flaw["ply"] == 8
        assert "reversed" in flaw["tags"]

    @pytest.mark.asyncio
    async def test_flaw_list_item_fields(self, flaws_test_state: dict[str, Any]) -> None:
        """Each FlawListItem carries all required display payload fields."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/flaws",
                params={"limit": 1},
                headers=flaws_test_state["headers_a"],
            )
        assert resp.status_code == 200
        flaw = resp.json()["flaws"][0]
        required_fields = {
            "game_id",
            "ply",
            "fen",
            "move_san",
            "severity",
            "tags",
            "es_before",
            "es_after",
            "user_result",
            "played_at",
            "time_control_bucket",
            "platform",
            "platform_url",
            "white_username",
            "black_username",
            "user_color",
        }
        for field in required_fields:
            assert field in flaw, f"Missing field: {field}"
        # Ensure no hash fields leak (CLAUDE.md V5 / T-108-10)
        for key in flaw:
            assert not key.endswith("_hash"), f"Hash field exposed in response: {key}"

    @pytest.mark.asyncio
    async def test_idor_user_a_cannot_see_user_b_flaws(
        self, flaws_test_state: dict[str, Any]
    ) -> None:
        """User A requesting /library/flaws NEVER sees user B's flaws (T-108-10).

        User B has one game (game_b1) with one flaw. User A's request must
        return only user A's 5 flaws; user B's game_id must not appear.
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/flaws",
                params={"limit": 100},
                headers=flaws_test_state["headers_a"],
            )
        assert resp.status_code == 200
        body = resp.json()
        game_b1 = flaws_test_state["game_b1"]
        for flaw in body["flaws"]:
            assert flaw["game_id"] != game_b1, f"User A can see user B's flaw from game {game_b1}"
        # All returned flaws belong to games user_a_id owns
        # (verified indirectly: matched_count == 5, no B game_id)
        assert body["matched_count"] == 5

    @pytest.mark.asyncio
    async def test_phase_tag_in_query_rejected_422(self, flaws_test_state: dict[str, Any]) -> None:
        """Phase tags (opening/middlegame/endgame) in ?tag= are rejected with 422.

        FlawTagFilter excludes phase tags so FastAPI validates and rejects them
        (T-108-11 mitigation — phase tags are display-only, not filter predicates).
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            for phase_tag in ("opening", "middlegame", "endgame"):
                resp = await client.get(
                    "/api/library/flaws",
                    params={"tag": phase_tag},
                    headers=flaws_test_state["headers_a"],
                )
                assert resp.status_code == 422, (
                    f"Expected 422 for phase tag '{phase_tag}', got {resp.status_code}"
                )

    @pytest.mark.asyncio
    async def test_invalid_severity_rejected_422(self, flaws_test_state: dict[str, Any]) -> None:
        """Inaccuracy or unknown severity values in ?severity= are rejected with 422."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            for bad_sev in ("inaccuracy", "fatal", ""):
                resp = await client.get(
                    "/api/library/flaws",
                    params={"severity": bad_sev},
                    headers=flaws_test_state["headers_a"],
                )
                assert resp.status_code == 422, (
                    f"Expected 422 for severity '{bad_sev}', got {resp.status_code}"
                )

    @pytest.mark.asyncio
    async def test_limit_bounds_enforced(self, flaws_test_state: dict[str, Any]) -> None:
        """limit=0 or limit=101 are rejected with 422 (ge=1 le=100 constraints, T-108-12)."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            for bad_limit in (0, 101, -1):
                resp = await client.get(
                    "/api/library/flaws",
                    params={"limit": bad_limit},
                    headers=flaws_test_state["headers_a"],
                )
                assert resp.status_code == 422, (
                    f"Expected 422 for limit={bad_limit}, got {resp.status_code}"
                )

    @pytest.mark.asyncio
    async def test_tags_reconstructed_in_flaw_item(self, flaws_test_state: dict[str, Any]) -> None:
        """tags list in FlawListItem includes expected tags from typed columns.

        game_a2 ply 2 has is_miss=True → tags must include 'miss'.
        game_a2 ply 6 has tempo=0 (low-clock) → tags must include 'low-clock'.
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/flaws",
                params={"limit": 10},
                headers=flaws_test_state["headers_a"],
            )
        assert resp.status_code == 200
        game_a2 = flaws_test_state["game_a2"]
        flaw_map = {(f["game_id"], f["ply"]): f for f in resp.json()["flaws"]}

        miss_flaw = flaw_map.get((game_a2, 2))
        assert miss_flaw is not None, "game_a2 ply 2 flaw not found"
        assert "miss" in miss_flaw["tags"], f"Expected 'miss' in tags: {miss_flaw['tags']}"

        lc_flaw = flaw_map.get((game_a2, 6))
        assert lc_flaw is not None, "game_a2 ply 6 flaw not found"
        assert "low-clock" in lc_flaw["tags"], f"Expected 'low-clock' in tags: {lc_flaw['tags']}"


# ---------------------------------------------------------------------------
# Helpers for Plan 109-03 eval-series integration tests (committed sessions)
# ---------------------------------------------------------------------------


async def _seed_positions_committed(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    user_id: int,
    game_id: int,
    positions: list[dict[str, Any]],
) -> None:
    """Insert and commit GamePosition rows for a game.

    Each dict in `positions` must include at least: ply, eval_cp (optional),
    eval_mate (optional), phase (optional). Zobrist hash columns are filled with
    dummy values since the chart builder does not use them.
    """
    from app.models.game_position import GamePosition

    async with session_maker() as session:
        for p in positions:
            pos = GamePosition(
                game_id=game_id,
                user_id=user_id,
                ply=p["ply"],
                full_hash=0,
                white_hash=0,
                black_hash=0,
                eval_cp=p.get("eval_cp"),
                eval_mate=p.get("eval_mate"),
                phase=p.get("phase"),
                clock_seconds=p.get("clock_seconds"),
                move_san=p.get("move_san"),
            )
            session.add(pos)
        await session.commit()


def _make_analyzed_positions(n_plies: int = 10) -> list[dict[str, Any]]:
    """Build a list of per-ply position dicts with eval_cp set on all but the last ply.

    Coverage: (n_plies - 1) / n_plies >= 0.90 requires n_plies >= 10.
    All plies except the final one carry eval_cp, so coverage = (n-1)/n.
    For n=10: 9/10 = 90% exactly — meets the EVAL_COVERAGE_MIN=0.90 gate.

    Includes a deliberate blunder at ply 2 (white mover, n=2 → "white"):
      - positions[1].eval_cp = 100  (es_before for white ≈ 0.591)
      - positions[2].eval_cp = -500 (es_after for white ≈ 0.155)
      - drop ≈ 0.436 ≥ BLUNDER_DROP=0.15 → severity="blunder", is_user=True for white user
    Phase transitions:
      - ply 3: phase=1 (middlegame)
      - ply 6: phase=2 (endgame)
    """
    result: list[dict[str, Any]] = []
    for i in range(n_plies):
        ply = i
        is_final = i == n_plies - 1
        # move_san is set on every position except the terminal one (real-import
        # convention) so the card's `moves` mainline aligns with eval_series minus
        # the final entry. The string itself is arbitrary here — only the backend
        # passthrough is exercised; the frontend replays real SANs in production.
        move_san = None if is_final else f"m{ply}"
        # Annotate once before the branch chain so every reassignment keeps the
        # dict[str, Any] type (else ty narrows a branch to dict[str, int] and the
        # move_san assignment below — a str|None value — becomes invalid).
        entry: dict[str, Any]
        if i == 0:
            # Initial position — eval_cp set to maintain coverage (ply 0 counts toward total).
            # Convention: only the final ply is null in a fully-analyzed lichess game.
            entry = {"ply": ply, "eval_cp": 25, "phase": 0}
        elif i == 1:
            # Before the blunder: white slightly ahead
            entry = {"ply": ply, "eval_cp": 100, "phase": 0}
        elif i == 2:
            # After the blunder: black crushes (white mover, n=2 → "white")
            entry = {"ply": ply, "eval_cp": -500, "phase": 0}
        elif i == 3:
            entry = {"ply": ply, "eval_cp": -450, "phase": 1}  # middlegame start
        elif i == 6:
            entry = {"ply": ply, "eval_cp": -400, "phase": 2}  # endgame start
        elif is_final:
            # Final ply: no eval (standard convention — sole null keeps coverage = (n-1)/n >= 0.90)
            entry = {"ply": ply, "phase": 2}
        else:
            entry = {"ply": ply, "eval_cp": -350, "phase": 1 if i < 6 else 2}
        entry["move_san"] = move_san
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Plan 109-03: fixture for eval-series integration tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="module")
async def eval_series_test_state(test_engine: Any) -> dict[str, Any]:
    """Seed two users for Plan 109-03 eval-series integration tests.

    User A:
      - game_analyzed: game with eval_cp on >=90% of plies (10 plies, 9 with eval).
        Includes a blunder at ply 2 (white mover, is_user=True for white user).
        Phase transitions: ply 3 = middlegame, ply 6 = endgame.
      - game_unanalyzed: game with NO eval_cp/eval_mate rows (no positions at all).
    User B:
      - game_b_analyzed: identical analyzed positions as game_analyzed, but owned
        by user_b. Used to verify IDOR: user_a's fetch_page_eval_positions call
        must NOT return user_b's positions even if given game_b_analyzed's ID.

    All rows are committed (not rolled back) so ASGI client sessions see them.
    """
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    suffix = uuid.uuid4().hex[:8]

    headers_a, user_a_id = await _register_and_login(f"eval_a_{suffix}@example.com")
    headers_b, user_b_id = await _register_and_login(f"eval_b_{suffix}@example.com")

    # User A: analyzed game (white user) with >90% eval coverage
    game_analyzed = await _seed_game_committed(
        session_maker,
        user_id=user_a_id,
        played_at=datetime.datetime(2026, 4, 1, tzinfo=datetime.timezone.utc),
        result="0-1",
        user_color="white",
    )
    positions = _make_analyzed_positions(n_plies=10)
    await _seed_positions_committed(
        session_maker,
        user_id=user_a_id,
        game_id=game_analyzed,
        positions=positions,
    )

    # User A: unanalyzed game — no positions at all (0% eval coverage)
    game_unanalyzed = await _seed_game_committed(
        session_maker,
        user_id=user_a_id,
        played_at=datetime.datetime(2026, 3, 1, tzinfo=datetime.timezone.utc),
        result="1-0",
        user_color="white",
    )

    # User B: analyzed positions for a different game (IDOR target)
    # We seed positions under user_b_id; the IDOR test confirms user_a_id's
    # fetch_page_eval_positions call does NOT return these rows.
    game_b_analyzed = await _seed_game_committed(
        session_maker,
        user_id=user_b_id,
        played_at=datetime.datetime(2026, 4, 1, tzinfo=datetime.timezone.utc),
        result="1-0",
        user_color="black",
    )
    await _seed_positions_committed(
        session_maker,
        user_id=user_b_id,
        game_id=game_b_analyzed,
        positions=_make_analyzed_positions(n_plies=10),
    )

    return {
        "headers_a": headers_a,
        "headers_b": headers_b,
        "user_a_id": user_a_id,
        "user_b_id": user_b_id,
        "game_analyzed": game_analyzed,
        "game_unanalyzed": game_unanalyzed,
        "game_b_analyzed": game_b_analyzed,
    }


# ---------------------------------------------------------------------------
# Plan 109-03 test class: eval_series / flaw_markers / phase_transitions
# ---------------------------------------------------------------------------


class TestEvalSeriesPayload:
    """Integration tests for the Plan 109-03 eval-chart payload extension.

    Covers:
    - eval_series: analyzed game has non-null eval fields; unanalyzed game has null.
    - flaw_markers: analyzed game has is_user field; markers include at least one blunder.
    - phase_transitions: analyzed game has non-null transitions.
    - No N+1: fetch_page_eval_positions is a single batched query (query count invariant).
    - IDOR: user_a's fetch_page_eval_positions call does NOT return user_b's positions.
    - Payload size: gzipped response is below the documented threshold (D-05).
    """

    @pytest.mark.asyncio
    async def test_eval_series_analyzed_game_has_non_null_fields(
        self, eval_series_test_state: dict[str, Any]
    ) -> None:
        """Analyzed game card exposes non-null eval_series, flaw_markers, phase_transitions.

        Checks:
        - eval_series is a non-empty list of EvalPoints, each with a ply field.
        - At least one EvalPoint has a non-null es (white-perspective ES).
        - flaw_markers is a list; at least one marker has is_user=True (player blunder).
        - phase_transitions is a non-null object with middlegame_ply and endgame_ply.
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/games",
                params={"limit": 20},
                headers=eval_series_test_state["headers_a"],
            )

        assert resp.status_code == 200
        games = resp.json()["games"]
        game_analyzed_id = eval_series_test_state["game_analyzed"]
        card = next((g for g in games if g["game_id"] == game_analyzed_id), None)
        assert card is not None, f"Analyzed game {game_analyzed_id} not found in response"

        # eval_series: non-null, non-empty list
        eval_series = card["eval_series"]
        assert eval_series is not None, "eval_series is None for analyzed game"
        assert isinstance(eval_series, list), "eval_series must be a list"
        assert len(eval_series) > 0, "eval_series is empty for analyzed game"

        # Each EvalPoint has the required fields
        ep = eval_series[0]
        assert "ply" in ep, "EvalPoint missing 'ply' field"
        assert "es" in ep, "EvalPoint missing 'es' field"

        # At least one EvalPoint has a non-null es (positions 1-8 have eval_cp set)
        non_null_es = [pt for pt in eval_series if pt["es"] is not None]
        assert len(non_null_es) > 0, "No EvalPoint with non-null es in analyzed game"

        # flaw_markers: non-null list with is_user field
        flaw_markers = card["flaw_markers"]
        assert flaw_markers is not None, "flaw_markers is None for analyzed game"
        assert isinstance(flaw_markers, list), "flaw_markers must be a list"
        assert len(flaw_markers) > 0, "flaw_markers is empty — expected blunder at ply 2"
        marker = flaw_markers[0]
        assert "is_user" in marker, "FlawMarker missing 'is_user' field"
        assert "severity" in marker, "FlawMarker missing 'severity' field"
        assert "ply" in marker, "FlawMarker missing 'ply' field"

        # There should be at least one player blunder (white user, ply 2 drop was seeded)
        user_blunders = [m for m in flaw_markers if m["is_user"] and m["severity"] == "blunder"]
        assert len(user_blunders) > 0, f"No player blunder found in flaw_markers: {flaw_markers}"

        # phase_transitions: non-null with middlegame_ply and endgame_ply
        phase_transitions = card["phase_transitions"]
        assert phase_transitions is not None, "phase_transitions is None for analyzed game"
        assert "middlegame_ply" in phase_transitions, "phase_transitions missing 'middlegame_ply'"
        assert "endgame_ply" in phase_transitions, "phase_transitions missing 'endgame_ply'"
        assert phase_transitions["middlegame_ply"] == 3, (
            f"Expected middlegame_ply=3, got {phase_transitions['middlegame_ply']}"
        )
        assert phase_transitions["endgame_ply"] == 6, (
            f"Expected endgame_ply=6, got {phase_transitions['endgame_ply']}"
        )

        # moves: SAN mainline for client-side board reconstruction. One entry per
        # ply except the terminal position (move_san=None), so it aligns with
        # eval_series minus that final entry.
        moves = card["moves"]
        assert moves is not None, "moves is None for analyzed game"
        assert isinstance(moves, list) and all(isinstance(m, str) for m in moves), (
            "moves must be a list of SAN strings"
        )
        assert len(moves) == len(eval_series) - 1, (
            f"Expected moves to align with eval_series minus terminal: "
            f"{len(moves)} vs {len(eval_series)}"
        )

    @pytest.mark.asyncio
    async def test_unanalyzed_game_has_null_eval_fields(
        self, eval_series_test_state: dict[str, Any]
    ) -> None:
        """Unanalyzed game card exposes null eval_series, flaw_markers, phase_transitions.

        A game with no game_positions rows has 0% eval coverage — below the 90% gate.
        Its GameFlawCard must carry null for all three eval fields.
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/games",
                params={"limit": 20},
                headers=eval_series_test_state["headers_a"],
            )

        assert resp.status_code == 200
        games = resp.json()["games"]
        game_unanalyzed_id = eval_series_test_state["game_unanalyzed"]
        card = next((g for g in games if g["game_id"] == game_unanalyzed_id), None)
        assert card is not None, f"Unanalyzed game {game_unanalyzed_id} not found in response"

        assert card["eval_series"] is None, (
            f"eval_series must be null for unanalyzed game, got {card['eval_series']}"
        )
        assert card["flaw_markers"] is None, (
            f"flaw_markers must be null for unanalyzed game, got {card['flaw_markers']}"
        )
        assert card["phase_transitions"] is None, (
            f"phase_transitions must be null for unanalyzed game, got {card['phase_transitions']}"
        )
        assert card["moves"] is None, f"moves must be null for unanalyzed game, got {card['moves']}"
        # Confirm the analysis_state is 'no_engine_analysis' for documentation
        assert card["analysis_state"] == "no_engine_analysis", (
            f"Expected 'no_engine_analysis', got {card['analysis_state']}"
        )

    @pytest.mark.asyncio
    async def test_no_n_plus_1_query_count(
        self, eval_series_test_state: dict[str, Any], test_engine: Any
    ) -> None:
        """fetch_page_eval_positions is a single batched query — query count does not scale.

        Seeds 1 analyzed game and 5 analyzed games for a fresh user, measures the
        SQL SELECT count for each page request, and asserts the count is the same
        (proving the positions load is O(1) queries, not O(N) games).

        Uses a SQLAlchemy before_cursor_execute event listener on the sync engine
        — the same pattern as test_game_repository_zero_pending.py.
        """
        from app.repositories.library_repository import fetch_page_eval_positions
        from sqlalchemy.ext.asyncio import async_sessionmaker as asm

        session_maker = asm(test_engine, expire_on_commit=False)
        suffix = uuid.uuid4().hex[:8]

        # Seed a fresh user with 1 analyzed game and capture positions query count
        _, user_c_id = await _register_and_login(f"eval_c_{suffix}@example.com")
        game_1 = await _seed_game_committed(
            session_maker,
            user_id=user_c_id,
            played_at=datetime.datetime(2026, 5, 1, tzinfo=datetime.timezone.utc),
            result="1-0",
            user_color="white",
        )
        await _seed_positions_committed(
            session_maker,
            user_id=user_c_id,
            game_id=game_1,
            positions=_make_analyzed_positions(n_plies=10),
        )

        statements_1: list[str] = []

        def _on_exec_1(
            conn: Any, cursor: Any, statement: str, parameters: Any, context: Any, executemany: Any
        ) -> None:  # noqa: ANN401
            statements_1.append(statement)

        sync_engine = test_engine.sync_engine
        sa_event.listen(sync_engine, "before_cursor_execute", _on_exec_1)
        try:
            async with session_maker() as session:
                await fetch_page_eval_positions(session, user_c_id, [game_1])
        finally:
            sa_event.remove(sync_engine, "before_cursor_execute", _on_exec_1)

        queries_1 = sum(1 for s in statements_1 if "FROM" in s.upper())

        # Now seed 4 more analyzed games (total 5) and re-measure
        for i in range(4):
            g = await _seed_game_committed(
                session_maker,
                user_id=user_c_id,
                played_at=datetime.datetime(2026, 5, i + 2, tzinfo=datetime.timezone.utc),
                result="1-0",
                user_color="white",
            )
            await _seed_positions_committed(
                session_maker,
                user_id=user_c_id,
                game_id=g,
                positions=_make_analyzed_positions(n_plies=10),
            )

        # Collect all 5 game IDs
        statements_5: list[str] = []

        def _on_exec_5(
            conn: Any, cursor: Any, statement: str, parameters: Any, context: Any, executemany: Any
        ) -> None:  # noqa: ANN401
            statements_5.append(statement)

        # Re-query the games list to get all 5 IDs
        async with session_maker() as session:
            from app.models.game import Game
            from sqlalchemy import select as sa_select

            result = await session.execute(
                sa_select(Game.id).where(Game.user_id == user_c_id).order_by(Game.id)
            )
            all_game_ids = list(result.scalars().all())

        sa_event.listen(sync_engine, "before_cursor_execute", _on_exec_5)
        try:
            async with session_maker() as session:
                await fetch_page_eval_positions(session, user_c_id, all_game_ids)
        finally:
            sa_event.remove(sync_engine, "before_cursor_execute", _on_exec_5)

        queries_5 = sum(1 for s in statements_5 if "FROM" in s.upper())

        assert queries_1 == queries_5, (
            f"N+1 detected: 1-game page used {queries_1} SELECT(s), "
            f"5-game page used {queries_5} SELECT(s) — should be equal (single IN query)."
        )
        assert queries_1 == 1, (
            f"fetch_page_eval_positions should issue exactly 1 SELECT, got {queries_1}. "
            f"Statements: {statements_1}"
        )

    @pytest.mark.asyncio
    async def test_idor_eval_positions_user_scoped(
        self, eval_series_test_state: dict[str, Any], test_engine: Any
    ) -> None:
        """fetch_page_eval_positions returns no positions for a game owned by another user.

        User A tries to load positions for user B's game. The WHERE user_id == user_a_id
        clause in fetch_page_eval_positions must return 0 rows (T-109-01 control).
        """
        from app.repositories.library_repository import fetch_page_eval_positions

        session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
        user_a_id = eval_series_test_state["user_a_id"]
        game_b_analyzed = eval_series_test_state["game_b_analyzed"]

        async with session_maker() as session:
            positions_map = await fetch_page_eval_positions(session, user_a_id, [game_b_analyzed])

        # user_a must see zero positions for a game owned by user_b
        positions = positions_map.get(game_b_analyzed, [])
        assert len(positions) == 0, (
            f"IDOR breach: user_a_id={user_a_id} retrieved {len(positions)} positions "
            f"for game_b_analyzed={game_b_analyzed} (owned by user_b)."
        )

    @pytest.mark.asyncio
    async def test_payload_gzip_size_below_threshold(
        self, eval_series_test_state: dict[str, Any]
    ) -> None:
        """Gzipped GET /library/games response is below the D-05 ceiling constant.

        Serializes the response JSON to bytes and compresses with gzip (same as
        HTTP Content-Encoding: gzip). Asserts the compressed size is below
        _EVAL_PAYLOAD_GZIP_CEILING_BYTES (40 KB). This bounds the payload
        regression introduced by adding per-ply eval_series to each card.

        The actual measured size is asserted here; the concrete byte count is
        recorded in the plan SUMMARY for D-05 documentation.
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/games",
                params={"limit": 20},
                headers=eval_series_test_state["headers_a"],
            )

        assert resp.status_code == 200
        json_bytes = json.dumps(resp.json()).encode("utf-8")
        compressed = gzip.compress(json_bytes)
        compressed_size = len(compressed)

        assert compressed_size < _EVAL_PAYLOAD_GZIP_CEILING_BYTES, (
            f"Gzipped payload {compressed_size} bytes exceeds ceiling "
            f"{_EVAL_PAYLOAD_GZIP_CEILING_BYTES} bytes. "
            "Review columnar encoding per D-05 if this persists with a full page."
        )
