"""Router-level integration tests (Phase 61).

Uses the shared seeded_user fixture to prove that the full stack
HTTP → router → service → repository → DB produces the expected numbers
for a known deterministic portfolio. Each test asserts exact integers
against the EXPECTED aggregate dict committed alongside the seed spec.

Phase 92 date-filter boundary tests (TestDateFilterBoundarySemantics) are
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
# TestEndgamesOverviewRouter
# -----------------------------------------------------------------------------


class TestEndgamesOverviewRouter:
    @pytest.mark.asyncio
    async def test_endgame_wdl_total(self, seeded_user: SeededUser) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/overview", headers=seeded_user.auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert (
            data["performance"]["endgame_wdl"]["total"]
            == (seeded_user.expected["endgame_games_distinct"])
        )

    @pytest.mark.asyncio
    async def test_per_type_rook_count(self, seeded_user: SeededUser) -> None:
        """stats.categories contains a row per endgame_class with a total count."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/overview", headers=seeded_user.auth_headers)
        data = resp.json()
        by_class = {c["endgame_class"]: c["total"] for c in data["stats"]["categories"]}
        assert by_class.get("rook") == seeded_user.expected["endgame_rook_games"], (
            f"stats.categories={by_class}"
        )

    @pytest.mark.asyncio
    async def test_per_type_pawn_count(self, seeded_user: SeededUser) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/overview", headers=seeded_user.auth_headers)
        data = resp.json()
        by_class = {c["endgame_class"]: c["total"] for c in data["stats"]["categories"]}
        assert by_class.get("pawn") == seeded_user.expected["endgame_pawn_games"], (
            f"stats.categories={by_class}"
        )

    @pytest.mark.asyncio
    async def test_material_rows_sum_equals_endgame_total(self, seeded_user: SeededUser) -> None:
        """Phase 59 invariant verified at the router layer with real seeded data."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/overview", headers=seeded_user.auth_headers)
        data = resp.json()
        rows_sum = sum(r["games"] for r in data["score_gap_material"]["material_rows"])
        assert rows_sum == data["performance"]["endgame_wdl"]["total"]

    @pytest.mark.asyncio
    async def test_all_six_endgame_classes_present(self, seeded_user: SeededUser) -> None:
        """stats.categories includes every class from EXPECTED with the right totals."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/overview", headers=seeded_user.auth_headers)
        data = resp.json()
        by_class = {c["endgame_class"]: c["total"] for c in data["stats"]["categories"]}
        expected_by_class = seeded_user.expected["endgame_by_class"]
        for klass, expected_total in expected_by_class.items():
            assert by_class.get(klass) == expected_total, (
                f"class {klass!r}: got {by_class.get(klass)} expected {expected_total} "
                f"(full stats.categories={by_class})"
            )


# -----------------------------------------------------------------------------
# TestTimePressureCardsRouter — Phase 88 time-pressure cards
# -----------------------------------------------------------------------------


class TestTimePressureCardsRouter:
    """GET /api/endgames/overview → time_pressure_cards sub-payload (Phase 88).

    The seed has 11 blitz endgame games, which is below MIN_GAMES_PER_TC_CARD=20,
    so no TC card qualifies. The response must have a cards list (possibly empty).
    """

    @pytest.mark.asyncio
    async def test_time_pressure_cards_present_in_response(self, seeded_user: SeededUser) -> None:
        """time_pressure_cards key must be present in the overview response."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/overview", headers=seeded_user.auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "time_pressure_cards" in data, f"missing time_pressure_cards key; keys={list(data)}"
        assert "cards" in data["time_pressure_cards"], (
            f"missing cards key; time_pressure_cards={data['time_pressure_cards']}"
        )

    @pytest.mark.asyncio
    async def test_no_cards_below_threshold(self, seeded_user: SeededUser) -> None:
        """Seed has 11 blitz endgame games, below MIN_GAMES_PER_TC_CARD=20, so cards is empty."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/overview", headers=seeded_user.auth_headers)
        data = resp.json()
        cards = data["time_pressure_cards"]["cards"]
        assert isinstance(cards, list), f"cards must be a list, got {type(cards)}"
        # Blitz is the only TC with clock data, but it only has 11 endgame games
        # (below MIN_GAMES_PER_TC_CARD=20), so no card should be emitted.
        assert cards == [], (
            f"expected no cards (all TCs below threshold), got {len(cards)} card(s): "
            f"{[c.get('tc') for c in cards]}"
        )

    @pytest.mark.asyncio
    async def test_legacy_clock_pressure_field_absent(self, seeded_user: SeededUser) -> None:
        """Phase 88: clock_pressure and time_pressure_chart fields removed from overview."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/overview", headers=seeded_user.auth_headers)
        data = resp.json()
        assert "clock_pressure" not in data, (
            "clock_pressure should no longer be in the overview response (Phase 88)"
        )
        assert "time_pressure_chart" not in data, (
            "time_pressure_chart should no longer be in the overview response (Phase 88)"
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
# TestEndgameEloTimelineRouter — Phase 57 endgame_elo_timeline sub-payload (Phase 87.5 D-06 restore)
# -----------------------------------------------------------------------------


class TestEndgameEloTimelineRouter:
    """GET /api/endgames/overview -> endgame_elo_timeline sub-payload (Phase 57 ELO-05; Phase 87.5 D-06).

    Covers SC-2 (filter responsiveness via platform=chess.com narrowing) and
    SC-3 (cold-start: no qualifying combos yields empty `combos: []`).

    The 25-game seeded portfolio distributes endgame games across both platforms
    and multiple time controls; per-combo counts may fall below
    MIN_GAMES_FOR_TIMELINE=10 so the qualifying combos list can legitimately be
    empty. Assertions below are phrased to tolerate either outcome while still
    proving the contract holds.
    """

    @pytest.mark.asyncio
    async def test_endgame_overview_elo_timeline_respects_filters(
        self, seeded_user: SeededUser
    ) -> None:
        """SC-2: platform=chess.com filter excludes lichess combos from the response."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get(
                "/api/endgames/overview?platform=chess.com",
                headers=seeded_user.auth_headers,
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        elo_timeline = data["endgame_elo_timeline"]
        assert elo_timeline["timeline_window"] == 100
        # Every returned combo must have platform="chess.com" — zero lichess leakage.
        for combo in elo_timeline["combos"]:
            assert combo["platform"] == "chess.com", (
                f"lichess combo leaked through platform=chess.com filter: {combo}"
            )

    @pytest.mark.asyncio
    async def test_endgame_overview_elo_timeline_cold_start_returns_empty_combos(
        self, seeded_user: SeededUser
    ) -> None:
        """SC-3: narrow recency filter drops every combo below MIN_GAMES_FOR_TIMELINE=10.

        The seeded portfolio's games are dated far in the past relative to the
        recency filter applied here, so no combo has >=10 endgame games within
        the filter window. Response must be `combos: []` with the window constant
        still present.
        """
        import datetime as _dt

        from_date_str = (_dt.date.today() - _dt.timedelta(days=7)).isoformat()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            # from_date narrows to the past 7 days; seed fixture uses historic
            # dates so nothing qualifies. If the seed is ever changed to use
            # current-date games, switch to a smaller date window or add an
            # explicit "fresh user with 0 games" test path here.
            resp = await client.get(
                f"/api/endgames/overview?from_date={from_date_str}",
                headers=seeded_user.auth_headers,
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        elo_timeline = data["endgame_elo_timeline"]
        assert elo_timeline["timeline_window"] == 100
        assert elo_timeline["combos"] == [], (
            f"expected empty combos for cold-start / narrow-recency seed, "
            f"got {len(elo_timeline['combos'])}: {elo_timeline['combos']}"
        )

    @pytest.mark.asyncio
    async def test_endgame_overview_elo_timeline_includes_per_week_count(
        self, seeded_user: SeededUser
    ) -> None:
        """Phase 57.1 D-19: every emitted point exposes per_week_endgame_games as an int >= 0.

        The seeded portfolio's per-combo counts may not all clear MIN_GAMES_FOR_TIMELINE,
        so the assertion is shape-only: when a point is emitted, the new field is
        present and non-negative. Math correctness is covered by the unit tests in
        tests/test_endgame_service.py::TestEndgameEloTimeline.
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get(
                "/api/endgames/overview",
                headers=seeded_user.auth_headers,
            )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        elo_timeline = data["endgame_elo_timeline"]
        for combo in elo_timeline["combos"]:
            for point in combo["points"]:
                assert "per_week_endgame_games" in point, (
                    f"missing per_week_endgame_games on point: {point}"
                )
                assert isinstance(point["per_week_endgame_games"], int), (
                    f"per_week_endgame_games must be int, got {type(point['per_week_endgame_games'])}"
                )
                assert point["per_week_endgame_games"] >= 0
                # UAT 2026-05-17: per_week_total_games (endgame + non-endgame)
                # carries through to the ELO Timeline so its volume bars reflect
                # total weekly activity (both PR lines), not endgame-only games.
                assert "per_week_total_games" in point, (
                    f"missing per_week_total_games on point: {point}"
                )
                assert isinstance(point["per_week_total_games"], int), (
                    f"per_week_total_games must be int, got {type(point['per_week_total_games'])}"
                )
                assert point["per_week_total_games"] >= point["per_week_endgame_games"]
                # Sanity: actual_elo is now an asof rating, must be a positive int.
                assert isinstance(point["actual_elo"], int) and point["actual_elo"] > 0
                assert isinstance(point["endgame_elo"], int) and point["endgame_elo"] > 0


# -----------------------------------------------------------------------------
# TestDateFilterBoundarySemantics — Phase 92 from_date / to_date boundary tests
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
    """Integration tests for from_date / to_date boundary semantics (Phase 92 D-10).

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
        """D-10: a game played exactly at from_date midnight UTC must match.

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
        """D-10: a game played at 23:59 on to_date must still match.

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
        """D-10: a game played at midnight of to_date + 1 day must NOT match.

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
        """D-10: both from_date and to_date omitted means no date filtering.

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
        """D-15: POST /openings/positions returns 422 when from_date > to_date.

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
        """D-15: GET /stats/global returns 422 when from_date > to_date.

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
