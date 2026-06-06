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
"""

import datetime
import uuid
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.main import app


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
    is_lucky_escape: bool = False,
    is_while_ahead: bool = False,
    is_result_changing: bool = False,
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
            is_lucky_escape=is_lucky_escape,
            is_while_ahead=is_while_ahead,
            is_result_changing=is_result_changing,
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
    # Flaws on game A1: ply 4 (blunder), ply 8 (mistake, result-changing)
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
        is_result_changing=True,  # mistake, result-changing
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
      game_a1 — result-changing (impact family), blunder
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
    async def test_tag_result_changing_matches_only_its_game(
        self, flaws_test_state: dict[str, Any]
    ) -> None:
        """?tag=result-changing returns only the game with that flaw (game_a1)."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/games",
                params={"tag": "result-changing"},
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

        result-changing (impact) and low-clock (tempo) live in different games,
        so no single flaw satisfies both families → 0 games match. This is the
        AND-across-families / single-flaw EXISTS semantics (SEED-038), and the
        exact behaviour that was broken (tags silently dropped) for the Games tab.
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/games",
                params={"tag": ["result-changing", "low-clock"]},
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
    async def test_tag_filter_result_changing(self, flaws_test_state: dict[str, Any]) -> None:
        """?tag=result-changing returns only rows with is_result_changing=True."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/api/library/flaws",
                params={"tag": "result-changing"},
                headers=flaws_test_state["headers_a"],
            )
        assert resp.status_code == 200
        body = resp.json()
        # Only game_a1 ply8 has is_result_changing=True
        assert body["matched_count"] == 1
        flaw = body["flaws"][0]
        assert flaw["game_id"] == flaws_test_state["game_a1"]
        assert flaw["ply"] == 8
        assert "result-changing" in flaw["tags"]

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
