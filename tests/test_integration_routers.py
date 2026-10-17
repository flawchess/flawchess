"""Router-level integration tests.

Uses the shared seeded_user fixture to prove that the full stack
HTTP → router → service → repository → DB produces the expected numbers
for a known deterministic portfolio. Each test asserts exact integers
against the EXPECTED aggregate dict committed alongside the seed spec.

Date-filter boundary tests (TestDateFilterBoundarySemantics) are
appended at the bottom. They use function-scoped fixtures so each test seeds
exactly one game at a controlled played_at timestamp, making matched_count
assertions unambiguous without requiring shared state across tests.
"""

import datetime
import uuid

import httpx
import pytest
import pytest_asyncio

from app.main import app
from tests.seed_fixtures import STARTING_POSITION_HASH, SeededUser
# seeded_user fixture is provided by tests.seed_fixtures via conftest.py's
# pytest_plugins registration — do NOT import the fixture name here or ruff
# F811 will flag it as a redefinition against the test function parameter.

_BASE = "http://test"

# Deterministic hash for the single position seeded per date-filter test game.
# Must be within PostgreSQL BIGINT range (signed int64: max 9223372036854775807).
# Using a distinct value from STARTING_POSITION_HASH to avoid cross-test
# collision if both fixture families share the same test DB session.
_DATE_TEST_HASH: int = 0x0DEADBEEFCAFE001  # 998684643807453185


def _find_by_label(items: list[dict], label: str) -> dict | None:
    """WDLByCategory rows expose a `label` field (title-case: 'White', 'Blitz')."""
    for c in items:
        if c.get("label") == label:
            return c
    return None


# -----------------------------------------------------------------------------
# TestGlobalStatsRouter
# -----------------------------------------------------------------------------


class TestGlobalStatsRouter:
    @pytest.mark.asyncio
    async def test_totals_match_expected_games(self, seeded_user: SeededUser) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/stats/global", headers=seeded_user.auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        total = sum(c["total"] for c in data["by_time_control"])
        assert total == seeded_user.expected["total_games"]

    @pytest.mark.asyncio
    async def test_by_time_control_buckets_have_expected_counts(
        self, seeded_user: SeededUser
    ) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/stats/global", headers=seeded_user.auth_headers)
        data = resp.json()
        for bucket, expected_total in seeded_user.expected["by_time_control"].items():
            row = _find_by_label(data["by_time_control"], bucket.title())
            assert row is not None, (
                f"missing bucket {bucket.title()!r} in response; "
                f"got labels={[c.get('label') for c in data['by_time_control']]}"
            )
            assert row["total"] == expected_total, (
                f"{bucket}: got {row['total']} expected {expected_total}"
            )

    @pytest.mark.asyncio
    async def test_by_color_black_perspective(self, seeded_user: SeededUser) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/stats/global", headers=seeded_user.auth_headers)
        data = resp.json()
        black = _find_by_label(data["by_color"], "Black")
        assert black is not None
        exp = seeded_user.expected["by_color"]["black"]
        assert black["total"] == exp["total"]
        assert black["wins"] == exp["wins"]
        assert black["draws"] == exp["draws"]
        assert black["losses"] == exp["losses"]

    @pytest.mark.asyncio
    async def test_by_color_white_perspective(self, seeded_user: SeededUser) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/stats/global", headers=seeded_user.auth_headers)
        data = resp.json()
        white = _find_by_label(data["by_color"], "White")
        assert white is not None
        exp = seeded_user.expected["by_color"]["white"]
        assert white["total"] == exp["total"]
        assert white["wins"] == exp["wins"]
        assert white["draws"] == exp["draws"]
        assert white["losses"] == exp["losses"]

    @pytest.mark.asyncio
    async def test_platform_filter_chess_com(self, seeded_user: SeededUser) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get(
                "/api/stats/global?platform=chess.com",
                headers=seeded_user.auth_headers,
            )
        data = resp.json()
        total = sum(c["total"] for c in data["by_time_control"])
        assert total == seeded_user.expected["by_platform"]["chess.com"]

    @pytest.mark.asyncio
    async def test_platform_filter_lichess(self, seeded_user: SeededUser) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get(
                "/api/stats/global?platform=lichess",
                headers=seeded_user.auth_headers,
            )
        data = resp.json()
        total = sum(c["total"] for c in data["by_time_control"])
        assert total == seeded_user.expected["by_platform"]["lichess"]


# -----------------------------------------------------------------------------
# TestEndgamesStatsRouter (filtered stats for the Games tab)
# -----------------------------------------------------------------------------


class TestEndgamesStatsRouter:
    @pytest.mark.asyncio
    async def test_endgame_games_total(self, seeded_user: SeededUser) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/stats", headers=seeded_user.auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["endgame_games"] == seeded_user.expected["endgame_games_distinct"]

    @pytest.mark.asyncio
    async def test_per_type_rook_count(self, seeded_user: SeededUser) -> None:
        """categories contains a row per endgame_class with a total count."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/stats", headers=seeded_user.auth_headers)
        data = resp.json()
        by_class = {c["endgame_class"]: c["total"] for c in data["categories"]}
        assert by_class.get("rook") == seeded_user.expected["endgame_rook_games"], (
            f"categories={by_class}"
        )

    @pytest.mark.asyncio
    async def test_per_type_pawn_count(self, seeded_user: SeededUser) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/stats", headers=seeded_user.auth_headers)
        data = resp.json()
        by_class = {c["endgame_class"]: c["total"] for c in data["categories"]}
        assert by_class.get("pawn") == seeded_user.expected["endgame_pawn_games"], (
            f"categories={by_class}"
        )

    @pytest.mark.asyncio
    async def test_all_six_endgame_classes_present(self, seeded_user: SeededUser) -> None:
        """categories includes every class from EXPECTED with the right totals."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/stats", headers=seeded_user.auth_headers)
        data = resp.json()
        by_class = {c["endgame_class"]: c["total"] for c in data["categories"]}
        expected_by_class = seeded_user.expected["endgame_by_class"]
        for klass, expected_total in expected_by_class.items():
            assert by_class.get(klass) == expected_total, (
                f"class {klass!r}: got {by_class.get(klass)} expected {expected_total} "
                f"(full categories={by_class})"
            )


# -----------------------------------------------------------------------------
# TestOpeningsNextMovesRouter
# -----------------------------------------------------------------------------


class TestOpeningsNextMovesRouter:
    @pytest.mark.asyncio
    async def test_starting_position_matches_all_seeded_games(
        self, seeded_user: SeededUser
    ) -> None:
        """Every seeded game has a ply=0 GamePosition at STARTING_POSITION_HASH."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.post(
                "/api/openings/next-moves",
                headers=seeded_user.auth_headers,
                json={"target_hash": str(STARTING_POSITION_HASH)},
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert (
            data["position_stats"]["total"]
            == (seeded_user.expected["starting_position_game_count"])
        )


# -----------------------------------------------------------------------------
# TestDateFilterBoundarySemantics — from_date / to_date boundary tests
# -----------------------------------------------------------------------------


async def _register_date_filter_user() -> tuple[int, dict[str, str]]:
    """Register a fresh user and return (user_id, auth_headers).

    Uses a random email so multiple function-scoped fixtures don't collide.
    """
    email = f"date-filter-{uuid.uuid4().hex[:8]}@example.com"
    password = "datefiltertestpw"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=_BASE) as client:
        reg = await client.post(
            "/api/auth/register",
            json={"email": email, "password": password},
        )
        user_id = int(reg.json()["id"])
        login = await client.post(
            "/api/auth/jwt/login",
            data={"username": email, "password": password},
        )
        token = login.json()["access_token"]
    return user_id, {"Authorization": f"Bearer {token}"}


async def _seed_one_game(user_id: int, played_at: datetime.datetime) -> None:
    """Commit one Game + one GamePosition at _DATE_TEST_HASH for the given user.

    The GamePosition at ply=0 uses _DATE_TEST_HASH so
    POST /api/openings/positions with target_hash=None (all-games) will match.
    platform_game_id is randomised to avoid the unique-constraint on
    (user_id, platform, platform_game_id) when multiple test games exist.
    """
    from app.core.database import async_session_maker
    from app.models.game import Game
    from app.models.game_position import GamePosition

    async with async_session_maker() as session:
        game = Game(
            user_id=user_id,
            platform="chess.com",
            platform_game_id=f"date-test-{uuid.uuid4().hex[:8]}",
            pgn="1. e4 e5 *",
            result="1-0",
            user_color="white",
            time_control_str="600+0",
            time_control_bucket="blitz",
            time_control_seconds=600,
            base_time_seconds=600,
            rated=True,
            is_computer_game=False,
            white_username="tester",
            black_username="opponent",
            white_rating=1500,
            black_rating=1500,
        )
        game.played_at = played_at
        session.add(game)
        await session.flush()
        session.add(
            GamePosition(
                game_id=game.id,
                user_id=user_id,
                ply=0,
                full_hash=_DATE_TEST_HASH,
                white_hash=_DATE_TEST_HASH + 1,
                black_hash=_DATE_TEST_HASH + 2,
                move_san="e4",
            )
        )
        await session.commit()


@pytest_asyncio.fixture
async def _from_date_inclusive_user() -> tuple[dict[str, str], int]:
    """User with one game played at 2026-03-01 00:00 UTC (from_date boundary)."""
    user_id, headers = await _register_date_filter_user()
    played_at = datetime.datetime(2026, 3, 1, 0, 0, tzinfo=datetime.timezone.utc)
    await _seed_one_game(user_id, played_at)
    return headers, user_id


@pytest_asyncio.fixture
async def _to_date_end_of_day_user() -> tuple[dict[str, str], int]:
    """User with one game played at 2026-04-01 23:59 UTC (to_date late in day)."""
    user_id, headers = await _register_date_filter_user()
    played_at = datetime.datetime(2026, 4, 1, 23, 59, tzinfo=datetime.timezone.utc)
    await _seed_one_game(user_id, played_at)
    return headers, user_id


@pytest_asyncio.fixture
async def _after_to_date_user() -> tuple[dict[str, str], int]:
    """User with one game played at 2026-04-02 00:00 UTC (one day past to_date)."""
    user_id, headers = await _register_date_filter_user()
    played_at = datetime.datetime(2026, 4, 2, 0, 0, tzinfo=datetime.timezone.utc)
    await _seed_one_game(user_id, played_at)
    return headers, user_id


@pytest_asyncio.fixture
async def _no_filter_user() -> tuple[dict[str, str], int]:
    """User with one game at an arbitrary past date for the no-filter test."""
    user_id, headers = await _register_date_filter_user()
    played_at = datetime.datetime(2025, 6, 15, 10, 0, tzinfo=datetime.timezone.utc)
    await _seed_one_game(user_id, played_at)
    return headers, user_id


class TestDateFilterBoundarySemantics:
    """Integration tests for from_date / to_date boundary semantics.

    Boundary contract (apply_game_filters):
      - from_date is INCLUSIVE: played_at >= from_date
      - to_date is INCLUSIVE of the full day: played_at < to_date + 1 day

    Each test registers a fresh user and seeds exactly one game at a specific
    played_at timestamp so matched_count is unambiguous (0 or 1).
    """

    @pytest.mark.asyncio
    async def test_openings_request_from_date_inclusive(
        self,
        _from_date_inclusive_user: tuple[dict[str, str], int],
    ) -> None:
        """A game played exactly at from_date midnight UTC must match.

        Seed: played_at = 2026-03-01 00:00 UTC. Filter: from_date=2026-03-01.
        Expected: matched_count == 1 (inclusive lower bound).
        """
        headers, _ = _from_date_inclusive_user
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.post(
                "/api/openings/positions",
                headers=headers,
                json={"from_date": "2026-03-01"},
            )
        assert resp.status_code == 200, resp.text
        assert resp.json()["matched_count"] == 1

    @pytest.mark.asyncio
    async def test_openings_request_to_date_end_of_day(
        self,
        _to_date_end_of_day_user: tuple[dict[str, str], int],
    ) -> None:
        """A game played at 23:59 on to_date must still match.

        Seed: played_at = 2026-04-01 23:59 UTC. Filter: to_date=2026-04-01.
        Expected: matched_count == 1 (pred is played_at < 2026-04-02 00:00).
        """
        headers, _ = _to_date_end_of_day_user
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.post(
                "/api/openings/positions",
                headers=headers,
                json={"to_date": "2026-04-01"},
            )
        assert resp.status_code == 200, resp.text
        assert resp.json()["matched_count"] == 1

    @pytest.mark.asyncio
    async def test_openings_request_excludes_after_to_date(
        self,
        _after_to_date_user: tuple[dict[str, str], int],
    ) -> None:
        """A game played at midnight of to_date + 1 day must NOT match.

        Seed: played_at = 2026-04-02 00:00 UTC. Filter: to_date=2026-04-01.
        Expected: matched_count == 0 (2026-04-02 00:00 is not < 2026-04-02 00:00).
        """
        headers, _ = _after_to_date_user
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.post(
                "/api/openings/positions",
                headers=headers,
                json={"to_date": "2026-04-01"},
            )
        assert resp.status_code == 200, resp.text
        assert resp.json()["matched_count"] == 0

    @pytest.mark.asyncio
    async def test_openings_request_no_date_filter(
        self,
        _no_filter_user: tuple[dict[str, str], int],
    ) -> None:
        """Both from_date and to_date omitted means no date filtering.

        Seed: one game at an arbitrary past date. Filter: neither date param.
        Expected: matched_count == 1 (game is not filtered out).
        """
        headers, _ = _no_filter_user
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.post(
                "/api/openings/positions",
                headers=headers,
                json={},
            )
        assert resp.status_code == 200, resp.text
        assert resp.json()["matched_count"] == 1

    @pytest.mark.asyncio
    async def test_openings_request_422_on_from_after_to(
        self,
        _no_filter_user: tuple[dict[str, str], int],
    ) -> None:
        """POST /openings/positions returns 422 when from_date > to_date.

        The OpeningsRequest model_validator raises ValueError which FastAPI
        surfaces as HTTP 422. The error detail must mention from_date.
        """
        headers, _ = _no_filter_user
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.post(
                "/api/openings/positions",
                headers=headers,
                json={"from_date": "2026-04-01", "to_date": "2026-03-01"},
            )
        assert resp.status_code == 422
        detail_text = str(resp.json())
        assert "from_date" in detail_text

    @pytest.mark.asyncio
    async def test_stats_get_422_on_from_after_to(
        self,
        _no_filter_user: tuple[dict[str, str], int],
    ) -> None:
        """GET /stats/global returns 422 when from_date > to_date.

        This exercises the inline HTTPException path in app/routers/stats.py
        (Query params, not a Pydantic body) — distinct code path from the
        model_validator used by POST /openings/positions.
        """
        headers, _ = _no_filter_user
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get(
                "/api/stats/global?from_date=2026-04-01&to_date=2026-03-01",
                headers=headers,
            )
        assert resp.status_code == 422
