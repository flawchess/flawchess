"""Router contract tests for GET /api/openings/out-of-opening-stats (Phase 243).

URL: GET /api/openings/out-of-opening-stats
     (openings router prefix="/openings" + @router.get("/out-of-opening-stats"),
     mounted under /api)

The endpoint is authenticated, takes no parameters (any query string yields the same
body) and reads ``user_id`` only from the authenticated user.
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.main import app
from app.models.benchmark_cohort_cdf import BenchmarkCohortCdf
from app.repositories.user_benchmark_percentiles_repository import upsert_percentile
from app.schemas.normalization import Color
from app.services.canonical_slice_sql import OPENING_OUT_MIN_GAMES_PER_COLOR
from app.services.global_percentile_cdf import (
    BREAKPOINT_PERCENTILES,
    OPENING_OUT_METRICS,
    OpeningOutMetricId,
    round_anchor_to_grid,
)
from app.services.user_benchmark_percentiles_service import compute_anchors_for_user
from tests.services.opening_out_seed import (
    SEED_TC,
    OpeningSpec,
    delete_users,
    expected_counts,
    main_block_specs,
    seed_opening_specs,
)

ENDPOINT = "/api/openings/out-of-opening-stats"
_PASSWORD = "testpassword123"
_CYCLES = 3
_SYNTHETIC_N_USERS = 200
_SYNTHETIC_SNAPSHOT_MONTH = "2026-10"
# Per-metric CDF scale: breakpoint p = p / 100 * scale (monotone, strictly inside 0..1).
_CDF_SCALE: dict[OpeningOutMetricId, float] = {
    "opening_worse_rate": 0.9,
    "opening_better_rate": 0.5,
}
_P25, _P50, _P75 = 25, 50, 75
_RAW_WORSE_PERCENTILE_WHITE = 30.0
_FAVORABLE_WORSE_WHITE = 70.0  # 100 - 30
_RAW_BETTER_PERCENTILE_WHITE = 80.0
_RAW_WORSE_PERCENTILE_BLACK = 60.0
_RAW_BETTER_PERCENTILE_BLACK = 40.0
_HTTP_UNAUTHORIZED = 401


@pytest_asyncio.fixture
async def registered(test_engine: AsyncEngine) -> AsyncIterator[tuple[dict[str, str], int]]:
    """Register a fresh user; yield (auth headers, user id); delete the user afterwards."""
    email = f"openings_out_test_{uuid.uuid4().hex[:8]}@example.com"
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        reg = await client.post("/api/auth/register", json={"email": email, "password": _PASSWORD})
        user_id = int(reg.json()["id"])
        login = await client.post(
            "/api/auth/jwt/login", data={"username": email, "password": _PASSWORD}
        )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    try:
        yield headers, user_id
    finally:
        await delete_users(async_sessionmaker(test_engine, expire_on_commit=False), [user_id])


async def _get(headers: dict[str, str] | None = None, params: dict[str, str] | None = None) -> Any:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.get(ENDPOINT, headers=headers, params=params)


async def _insert_cells(session_maker: async_sessionmaker, anchor: int) -> None:
    async with session_maker() as session:
        await _delete_cells(session_maker, anchor)
        session.add_all(
            [
                BenchmarkCohortCdf(
                    metric=metric,
                    anchor_elo=anchor,
                    tc=SEED_TC,
                    percentile=int(pct),
                    value=pct / 100.0 * _CDF_SCALE[metric],
                    n_users=_SYNTHETIC_N_USERS,
                    snapshot_month=_SYNTHETIC_SNAPSHOT_MONTH,
                )
                for metric in OPENING_OUT_METRICS
                for pct in BREAKPOINT_PERCENTILES
            ]
        )
        await session.commit()


async def _delete_cells(session_maker: async_sessionmaker, anchor: int) -> None:
    async with session_maker() as session:
        await session.execute(
            delete(BenchmarkCohortCdf).where(
                BenchmarkCohortCdf.metric.in_(OPENING_OUT_METRICS),
                BenchmarkCohortCdf.anchor_elo == anchor,
                BenchmarkCohortCdf.tc == SEED_TC,
            )
        )
        await session.commit()


async def _plant_percentiles(
    session_maker: async_sessionmaker, user_id: int, specs: list[OpeningSpec]
) -> None:
    raw: dict[tuple[OpeningOutMetricId, Color], float] = {
        ("opening_worse_rate", "white"): _RAW_WORSE_PERCENTILE_WHITE,
        ("opening_better_rate", "white"): _RAW_BETTER_PERCENTILE_WHITE,
        ("opening_worse_rate", "black"): _RAW_WORSE_PERCENTILE_BLACK,
        ("opening_better_rate", "black"): _RAW_BETTER_PERCENTILE_BLACK,
    }
    counts = expected_counts(specs)
    async with session_maker() as session:
        for (metric, color), percentile in raw.items():
            c = counts[color]
            await upsert_percentile(
                session,
                user_id=user_id,
                metric=metric,
                time_control_bucket=SEED_TC,
                value=c.count_for(metric) / c.n_games,
                n_games=c.n_games,
                percentile=percentile,
                cdf_snapshot=datetime.date.today(),
                color=color,
            )
        await session.commit()


@pytest.mark.asyncio
async def test_requires_auth_returns_401() -> None:
    """Unauthenticated request returns 401."""
    response = await _get()
    assert response.status_code == _HTTP_UNAUTHORIZED


@pytest.mark.asyncio
async def test_user_without_games_is_below_floor_everywhere(
    registered: tuple[dict[str, str], int],
) -> None:
    """No games: both colours, both rates below_floor with an empty TC list."""
    headers, _ = registered
    response = await _get(headers)
    assert response.status_code == 200
    body = response.json()
    for color in ("white", "black"):
        for side in ("worse", "better"):
            card = body[color][side]
            assert card["status"] == "below_floor"
            assert card["floor_n"] == 0
            assert card["floor_required"] == OPENING_OUT_MIN_GAMES_PER_COLOR
            assert card["rate"] is None
            assert card["tcs"] == []
            assert card["significant"] is False


@pytest.mark.asyncio
async def test_seeded_user_gets_ranked_collapsed_stats(
    test_engine: AsyncEngine, registered: tuple[dict[str, str], int]
) -> None:
    """Seeded counts + anchor + synthetic CDF cells + planted rows -> ranked, oriented card."""
    headers, user_id = registered
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    specs = [
        spec for _ in range(_CYCLES) for c in ("white", "black") for spec in main_block_specs(c)
    ]
    await seed_opening_specs(session_maker, user_id, specs, "router")
    async with session_maker() as session:
        anchors = await compute_anchors_for_user(session, user_id)
        await session.commit()
    anchor = round_anchor_to_grid(anchors[SEED_TC].anchor_rating)
    await _insert_cells(session_maker, anchor)
    try:
        await _plant_percentiles(session_maker, user_id, specs)
        response = await _get(headers)
        filtered = await _get(
            headers, {"time_control": "bullet", "color": "black", "platform": "lichess"}
        )
    finally:
        await _delete_cells(session_maker, anchor)

    assert response.status_code == 200
    assert filtered.json() == response.json()  # filter-independent
    expected = expected_counts(specs)
    white_worse = response.json()["white"]["worse"]
    assert white_worse["status"] == "ranked"
    assert white_worse["percentile_favorable"] == pytest.approx(_FAVORABLE_WORSE_WHITE)
    assert white_worse["k"] == expected["white"].worse_n
    assert white_worse["n"] == expected["white"].n_games
    assert len(white_worse["tcs"]) == 1
    tc_entry = white_worse["tcs"][0]
    assert tc_entry["tc"] == SEED_TC
    assert tc_entry["status"] == "ranked"
    assert (tc_entry["k"], tc_entry["n"]) == (white_worse["k"], white_worse["n"])
    assert tc_entry["percentile_favorable"] == pytest.approx(_FAVORABLE_WORSE_WHITE)
    assert white_worse["ci_low"] < white_worse["rate"] < white_worse["ci_high"]
    # The better rate is not inverted.
    white_better = response.json()["white"]["better"]
    assert white_better["percentile_favorable"] == pytest.approx(_RAW_BETTER_PERCENTILE_WHITE)
    # Peer band comes from the synthetic cell (p = pct / 100 * scale).
    scale = _CDF_SCALE["opening_worse_rate"]
    assert white_worse["peer_p25"] == pytest.approx(_P25 / 100 * scale)
    assert white_worse["peer_p50"] == pytest.approx(_P50 / 100 * scale)
    assert white_worse["peer_p75"] == pytest.approx(_P75 / 100 * scale)
