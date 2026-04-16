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
