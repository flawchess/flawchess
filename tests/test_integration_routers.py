"""Router-level integration tests (Phase 61).

Uses the shared seeded_user fixture to prove that the full stack
HTTP → router → service → repository → DB produces the expected numbers
for a known deterministic portfolio. Each test asserts exact integers
against the EXPECTED aggregate dict committed alongside the seed spec.
"""

import httpx
import pytest

from app.main import app
from tests.seed_fixtures import STARTING_POSITION_HASH, SeededUser
# seeded_user fixture is provided by tests.seed_fixtures via conftest.py's
# pytest_plugins registration — do NOT import the fixture name here or ruff
# F811 will flag it as a redefinition against the test function parameter.

_BASE = "http://test"


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
# TestClockPressureRouter — Phase 54 time-pressure table
# -----------------------------------------------------------------------------


class TestClockPressureRouter:
    """GET /api/endgames/overview → clock_pressure sub-payload.

    Only the `blitz` bucket meets MIN_GAMES_FOR_CLOCK_STATS=10 in the seeded
    portfolio (11 blitz endgame games carry clock_seconds; rapid has 3,
    classical has 1, bullet has 0). So `rows` must have length 1.
    """

    @pytest.mark.asyncio
    async def test_only_blitz_bucket_qualifies(self, seeded_user: SeededUser) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/overview", headers=seeded_user.auth_headers)
        data = resp.json()
        rows = data["clock_pressure"]["rows"]
        buckets = sorted(r["time_control"] for r in rows)
        assert buckets == seeded_user.expected["clock_pressure_qualifying_buckets"], (
            f"clock_pressure buckets={buckets} "
            f"expected={seeded_user.expected['clock_pressure_qualifying_buckets']}"
        )

    @pytest.mark.asyncio
    async def test_blitz_row_shape_and_counts(self, seeded_user: SeededUser) -> None:
        """The single blitz row carries the expected game counts and a
        well-formed average clock (between 0 and base_time_seconds=600).
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/overview", headers=seeded_user.auth_headers)
        data = resp.json()
        rows = data["clock_pressure"]["rows"]
        blitz = next((r for r in rows if r["time_control"] == "blitz"), None)
        assert blitz is not None, f"no blitz row in {rows}"
        assert blitz["label"] == "Blitz"
        assert blitz["total_endgame_games"] == seeded_user.expected["clock_pressure_blitz_games"]
        assert blitz["clock_games"] == seeded_user.expected["clock_pressure_blitz_games"]
        # Averages must be present (clocks are fully populated) and within
        # reasonable bounds — the 11 user/opp clocks all sit in [50, 400].
        assert blitz["user_avg_seconds"] is not None
        assert 0 < blitz["user_avg_seconds"] < 600
        assert blitz["opp_avg_seconds"] is not None
        assert 0 < blitz["opp_avg_seconds"] < 600
        assert blitz["user_avg_pct"] is not None
        assert 0 < blitz["user_avg_pct"] < 100

    @pytest.mark.asyncio
    async def test_net_timeout_rate_reflects_seeded_terminations(
        self, seeded_user: SeededUser
    ) -> None:
        """Seed has 2 timeout wins + 1 timeout loss in blitz → net rate = +1/11 ≈ 9.09%."""
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/overview", headers=seeded_user.auth_headers)
        data = resp.json()
        blitz = next(r for r in data["clock_pressure"]["rows"] if r["time_control"] == "blitz")
        wins = seeded_user.expected["clock_pressure_blitz_timeout_wins"]
        losses = seeded_user.expected["clock_pressure_blitz_timeout_losses"]
        games = seeded_user.expected["clock_pressure_blitz_games"]
        expected_rate = (wins - losses) / games * 100
        assert abs(blitz["net_timeout_rate"] - expected_rate) < 0.01, (
            f"net_timeout_rate={blitz['net_timeout_rate']} expected≈{expected_rate}"
        )


# -----------------------------------------------------------------------------
# TestTimePressureChartRouter — Phase 55 time-pressure performance chart
# -----------------------------------------------------------------------------


class TestTimePressureChartRouter:
    """GET /api/endgames/overview → time_pressure_chart sub-payload.

    Pooled across all time controls that passed MIN_GAMES_FOR_CLOCK_STATS —
    in the seed that is just blitz (11 games). Each of user_series and
    opp_series has 10 bucket points (0-10%, 10-20%, ..., 90-100%).
    """

    @pytest.mark.asyncio
    async def test_series_have_10_buckets(self, seeded_user: SeededUser) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/overview", headers=seeded_user.auth_headers)
        data = resp.json()
        chart = data["time_pressure_chart"]
        assert len(chart["user_series"]) == 10
        assert len(chart["opp_series"]) == 10

    @pytest.mark.asyncio
    async def test_total_endgame_games_matches_blitz_clock_games(
        self, seeded_user: SeededUser
    ) -> None:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/overview", headers=seeded_user.auth_headers)
        data = resp.json()
        chart = data["time_pressure_chart"]
        # Only blitz qualifies → the chart pools just those 11 games.
        assert chart["total_endgame_games"] == (seeded_user.expected["clock_pressure_blitz_games"])

    @pytest.mark.asyncio
    async def test_chart_game_counts_sum_to_total(self, seeded_user: SeededUser) -> None:
        """Sum of user_series bucket game_counts == total_endgame_games.

        Each qualifying game contributes exactly one data point to user_series
        (keyed by user's clock-remaining bucket) and one to opp_series (keyed
        by opponent's bucket).
        """
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            resp = await client.get("/api/endgames/overview", headers=seeded_user.auth_headers)
        data = resp.json()
        chart = data["time_pressure_chart"]
        user_sum = sum(pt["game_count"] for pt in chart["user_series"])
        opp_sum = sum(pt["game_count"] for pt in chart["opp_series"])
        assert user_sum == chart["total_endgame_games"]
        assert opp_sum == chart["total_endgame_games"]


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
# TestEndgameEloTimelineRouter — Phase 57 endgame_elo_timeline sub-payload
# -----------------------------------------------------------------------------


class TestEndgameEloTimelineRouter:
    """GET /api/endgames/overview -> endgame_elo_timeline sub-payload (Phase 57 ELO-05).

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
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url=_BASE
        ) as client:
            # recency=week narrows to the past 7 days; seed fixture uses historic
            # dates so nothing qualifies. If the seed is ever changed to use
            # current-date games, switch to a smaller recency window or add an
            # explicit "fresh user with 0 games" test path here.
            resp = await client.get(
                "/api/endgames/overview?recency=week",
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
                # Sanity: actual_elo is now an asof rating, must be a positive int.
                assert isinstance(point["actual_elo"], int) and point["actual_elo"] > 0
                assert isinstance(point["endgame_elo"], int) and point["endgame_elo"] > 0
