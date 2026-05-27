"""Chip-decoupling tests for PCTL-07 / D-12.

Phase 94.1 Plan 07, Task 1 — implements tests originally scaffolded by Plan 02.

Tests cover the D-12 rewire: the 4 {metric}_percentile response fields read from
user_benchmark_percentiles (materialised at import time) instead of per-request
interpolate_percentile(filter_applied_value). This makes the chip filter-independent.

Security domain V4 (Information Disclosure):
- test_chip_percentile_scopes_by_authenticated_user_id: verifies the SELECT
  filters WHERE user_id = current_user.id; user_id is never accepted as a query param.

Plan 13 (gap-closure): ``n_cells_floor`` dropped from PercentileRow and all
upsert_percentile calls. Row existence now implies above-floor.
"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# ── Guard — skip module until repository module exists ─────────────────────────
user_benchmark_percentiles_repository = pytest.importorskip(
    "app.repositories.user_benchmark_percentiles_repository"
)

from app.models.user_rating_anchors import TimeControlBucket  # noqa: E402
from app.repositories.user_benchmark_percentiles_repository import (  # noqa: E402
    PercentileRow,
    fetch_for_user,
    upsert_percentile,
)
from app.schemas.endgames import EndgameWDLSummary  # noqa: E402
from app.services.endgame_service import (  # noqa: E402
    _compute_score_gap_material,
    _get_endgame_performance_from_rows,
)
from app.services.global_percentile_cdf import CdfMetricId  # noqa: E402

# ── Module-level constants (CLAUDE.md: no magic numbers) ─────────────────────
_TEST_USER_A_ID: int = 99204  # unique per module to avoid FK conflicts
_TEST_USER_B_ID: int = 99205
_KNOWN_SCORE_GAP_PERCENTILE: float = 72.5  # planted materialised value
_KNOWN_ACHIEVABLE_PERCENTILE: float = 55.0
_KNOWN_CONV_PERCENTILE: float = 41.0
_KNOWN_PARITY_PERCENTILE: float = 68.0
_CDF_SNAPSHOT: datetime.date = datetime.date(2026, 3, 31)
_SEED_VALUE: float = 0.05  # arbitrary canonical-slice metric value
_SEED_N_GAMES: int = 42  # Phase 94.4 D-08: pooled n_games per (metric, TC) cell
_SEED_TC: TimeControlBucket = "blitz"  # canonical-slice fixtures all use blitz

pytestmark = pytest.mark.asyncio


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_percentile_rows(
    score_gap: float | None = _KNOWN_SCORE_GAP_PERCENTILE,
    achievable: float | None = _KNOWN_ACHIEVABLE_PERCENTILE,
    conv: float | None = _KNOWN_CONV_PERCENTILE,
    parity: float | None = _KNOWN_PARITY_PERCENTILE,
) -> dict[CdfMetricId, dict[TimeControlBucket, PercentileRow]]:
    """Build a nested percentile_rows dict for direct injection into service
    functions.

    Phase 94.4 D-08: the shape is dict[CdfMetricId, dict[TimeControlBucket,
    PercentileRow]]; the page-level chip aggregator
    ``_aggregate_per_tc_percentile`` reduces the per-TC inner dict to a single
    weighted-mean scalar. A single-TC entry passes the percentile through
    unchanged, so seeding ``{_SEED_TC: PercentileRow(...)}`` per metric keeps
    the chip values byte-identical to the pre-94.4 single-row contract.
    """
    return {
        "score_gap": {
            _SEED_TC: PercentileRow(
                value=_SEED_VALUE,
                percentile=score_gap,
                cdf_snapshot=_CDF_SNAPSHOT,
                n_games=_SEED_N_GAMES,
            ),
        },
        "achievable_score_gap": {
            _SEED_TC: PercentileRow(
                value=_SEED_VALUE,
                percentile=achievable,
                cdf_snapshot=_CDF_SNAPSHOT,
                n_games=_SEED_N_GAMES,
            ),
        },
        "score_gap_conv": {
            _SEED_TC: PercentileRow(
                value=_SEED_VALUE,
                percentile=conv,
                cdf_snapshot=_CDF_SNAPSHOT,
                n_games=_SEED_N_GAMES,
            ),
        },
        "score_gap_parity": {
            _SEED_TC: PercentileRow(
                value=_SEED_VALUE,
                percentile=parity,
                cdf_snapshot=_CDF_SNAPSHOT,
                n_games=_SEED_N_GAMES,
            ),
        },
    }


def _zero_wdl() -> EndgameWDLSummary:
    """Return an empty WDL summary for tests that do not care about value math."""
    return EndgameWDLSummary(
        wins=0,
        draws=0,
        losses=0,
        total=0,
        win_pct=0.0,
        draw_pct=0.0,
        loss_pct=0.0,
    )


# ── Test 1 — filter-toggle invariance ─────────────────────────────────────────


async def test_chip_percentile_unchanged_across_filter_toggles(
    db_session: AsyncSession,
) -> None:
    """Toggling filter inputs (recency, time_control, etc.) does not change
    {metric}_percentile values in the API response.

    Seeds user_benchmark_percentiles with known (value, percentile) for the
    test user. Calls _compute_score_gap_material twice with different filter-
    derived WDL inputs but the SAME percentile_rows, asserting the chip value
    is invariant (D-12 / PCTL-07).

    The row's filter-applied score_difference WILL differ between calls (it
    still comes from per-request compute), but the percentile chip is locked
    to the materialised value.
    """
    percentile_rows = _make_percentile_rows()

    # Simulate two different "filter states" producing different WDL values.
    # Filter A: more games, higher endgame score
    wdl_endgame_a = EndgameWDLSummary(
        wins=30, draws=10, losses=10, total=50, win_pct=0.6, draw_pct=0.2, loss_pct=0.2
    )
    wdl_non_a = EndgameWDLSummary(
        wins=20, draws=10, losses=20, total=50, win_pct=0.4, draw_pct=0.2, loss_pct=0.4
    )
    # Filter B: fewer games, lower endgame score
    wdl_endgame_b = EndgameWDLSummary(
        wins=10, draws=5, losses=15, total=30, win_pct=0.33, draw_pct=0.17, loss_pct=0.5
    )
    wdl_non_b = EndgameWDLSummary(
        wins=8, draws=4, losses=18, total=30, win_pct=0.27, draw_pct=0.13, loss_pct=0.6
    )

    result_a = _compute_score_gap_material(
        wdl_endgame_a,
        wdl_non_a,
        entry_rows=[],
        percentile_rows=percentile_rows,
    )
    result_b = _compute_score_gap_material(
        wdl_endgame_b,
        wdl_non_b,
        entry_rows=[],
        percentile_rows=percentile_rows,
    )

    # score_difference WILL differ (it is still per-request computed)
    assert result_a.score_difference != result_b.score_difference, (
        "score_difference must vary with filter state (per-request compute)"
    )
    # But the chip is invariant (D-12 / PCTL-07)
    assert result_a.score_gap_percentile == _KNOWN_SCORE_GAP_PERCENTILE
    assert result_b.score_gap_percentile == _KNOWN_SCORE_GAP_PERCENTILE
    assert result_a.score_gap_conv_percentile == _KNOWN_CONV_PERCENTILE
    assert result_b.score_gap_conv_percentile == _KNOWN_CONV_PERCENTILE
    assert result_a.score_gap_parity_percentile == _KNOWN_PARITY_PERCENTILE
    assert result_b.score_gap_parity_percentile == _KNOWN_PARITY_PERCENTILE


# ── Test 2 — V4 cross-user scope ──────────────────────────────────────────────


async def test_chip_percentile_scopes_by_authenticated_user_id(
    db_session: AsyncSession,
) -> None:
    """V4 Information Disclosure guard: fetch_for_user returns the authenticated
    user's percentile, NOT another user's percentile.

    Seeds 2 users (A and B) with distinct materialised percentiles.
    Calls fetch_for_user for user A and verifies it returns user A's values only.
    The SELECT in fetch_for_user must carry WHERE user_id = user_id (V4 guard).
    user_id is derived server-side from the FastAPI-Users auth dependency — it is
    NEVER accepted as a query parameter (V4 Tampering guard).
    """
    from tests.conftest import ensure_test_user

    _USER_B_PERCENTILE: float = 11.0  # user B's planted value, must NOT appear in user A's result

    await ensure_test_user(db_session, _TEST_USER_A_ID)
    await ensure_test_user(db_session, _TEST_USER_B_ID)

    # Seed user A with the known value (Phase 94.4 D-01: PK widens to include
    # time_control_bucket; canonical-slice fixtures all use blitz).
    await upsert_percentile(
        db_session,
        user_id=_TEST_USER_A_ID,
        metric="score_gap",
        time_control_bucket=_SEED_TC,
        value=_SEED_VALUE,
        n_games=42,
        percentile=_KNOWN_SCORE_GAP_PERCENTILE,
        cdf_snapshot=_CDF_SNAPSHOT,
    )
    # Seed user B with a distinct value
    await upsert_percentile(
        db_session,
        user_id=_TEST_USER_B_ID,
        metric="score_gap",
        time_control_bucket=_SEED_TC,
        value=_SEED_VALUE,
        n_games=42,
        percentile=_USER_B_PERCENTILE,
        cdf_snapshot=_CDF_SNAPSHOT,
    )
    await db_session.flush()

    # Fetch as user A — must return user A's percentile, NOT user B's. Phase
    # 94.4 D-08 nested shape: result["score_gap"][_SEED_TC] is the
    # PercentileRow; the outer key holds the per-TC inner dict.
    rows_a = await fetch_for_user(db_session, user_id=_TEST_USER_A_ID)
    assert "score_gap" in rows_a, "user A must have a score_gap row"
    assert _SEED_TC in rows_a["score_gap"], "user A must have a blitz row"
    row_a = rows_a["score_gap"][_SEED_TC]
    assert row_a.percentile is not None
    assert abs(row_a.percentile - _KNOWN_SCORE_GAP_PERCENTILE) < 1e-9, (
        "user A's percentile must match the planted value (V4 guard)"
    )
    assert row_a.percentile != _USER_B_PERCENTILE, (
        "user A's fetch must not contain user B's percentile (V4 guard)"
    )

    # Fetch as user B — must return user B's percentile, NOT user A's
    rows_b = await fetch_for_user(db_session, user_id=_TEST_USER_B_ID)
    assert "score_gap" in rows_b, "user B must have a score_gap row"
    assert _SEED_TC in rows_b["score_gap"], "user B must have a blitz row"
    row_b = rows_b["score_gap"][_SEED_TC]
    assert row_b.percentile is not None
    assert abs(row_b.percentile - _USER_B_PERCENTILE) < 1e-9, (
        "user B's percentile must match their planted value (V4 guard)"
    )


# ── Test 3 — no row → None ────────────────────────────────────────────────────


async def test_chip_percentile_is_none_when_no_row_in_table(
    db_session: AsyncSession,
) -> None:
    """Graceful degradation: when user has no row in user_benchmark_percentiles,
    all 4 {metric}_percentile fields in the API response are None.

    Phase 94's chip renders nothing (chip absent on FE) when the field is None.
    This is the "not yet computed" state for new users who have not yet gone
    through Stage A / Stage B.
    """
    # Empty percentile_rows — user has no materialised rows yet (Phase 94.4
    # D-08 nested shape).
    empty_rows: dict[CdfMetricId, dict[TimeControlBucket, PercentileRow]] = {}

    result = _compute_score_gap_material(
        _zero_wdl(),
        _zero_wdl(),
        entry_rows=[],
        percentile_rows=empty_rows,
    )
    assert result.score_gap_percentile is None, (
        "score_gap_percentile must be None when no materialised row exists"
    )
    assert result.score_gap_conv_percentile is None, (
        "score_gap_conv_percentile must be None when no materialised row exists"
    )
    assert result.score_gap_parity_percentile is None, (
        "score_gap_parity_percentile must be None when no materialised row exists"
    )

    perf = _get_endgame_performance_from_rows([], [], [], percentile_rows=empty_rows)
    assert perf.achievable_score_gap_percentile is None, (
        "achievable_score_gap_percentile must be None when no materialised row exists"
    )

    # Also verify the None path when percentile_rows is omitted (default=None)
    perf_default = _get_endgame_performance_from_rows([], [], [])
    assert perf_default.achievable_score_gap_percentile is None, (
        "achievable_score_gap_percentile must be None when percentile_rows=None (default)"
    )


# ── Test 4 — NULL percentile column → None ────────────────────────────────────


async def test_chip_percentile_is_none_when_percentile_column_is_null(
    db_session: AsyncSession,
) -> None:
    """When a user_benchmark_percentiles row exists with value=X but percentile=NULL,
    the API response field is None.

    Plan 13: below-floor users no longer produce rows at all (the service skips
    the upsert when _compute_metric_for_user returns None). However, the
    percentile column can still be NULL if the CDF lookup returns None for an
    out-of-range value. This test verifies the API handles NULL percentile correctly.
    """
    # Phase 94.4 D-08: nested shape; below-floor or out-of-range cells
    # have ``percentile=None`` on the PercentileRow and the aggregator drops
    # them, so the page-level chip surfaces as None per D-08a.
    null_pct_rows: dict[CdfMetricId, dict[TimeControlBucket, PercentileRow]] = {
        "score_gap": {
            _SEED_TC: PercentileRow(
                value=0.01,
                percentile=None,
                cdf_snapshot=_CDF_SNAPSHOT,
                n_games=_SEED_N_GAMES,
            ),
        },
        "achievable_score_gap": {
            _SEED_TC: PercentileRow(
                value=0.02,
                percentile=None,
                cdf_snapshot=_CDF_SNAPSHOT,
                n_games=_SEED_N_GAMES,
            ),
        },
        "score_gap_conv": {
            _SEED_TC: PercentileRow(
                value=0.01,
                percentile=None,
                cdf_snapshot=_CDF_SNAPSHOT,
                n_games=_SEED_N_GAMES,
            ),
        },
        "score_gap_parity": {
            _SEED_TC: PercentileRow(
                value=0.01,
                percentile=None,
                cdf_snapshot=_CDF_SNAPSHOT,
                n_games=_SEED_N_GAMES,
            ),
        },
    }

    result = _compute_score_gap_material(
        _zero_wdl(),
        _zero_wdl(),
        entry_rows=[],
        percentile_rows=null_pct_rows,
    )
    assert result.score_gap_percentile is None, (
        "score_gap_percentile must be None when percentile column is NULL"
    )
    assert result.score_gap_conv_percentile is None, (
        "score_gap_conv_percentile must be None when percentile column is NULL"
    )
    assert result.score_gap_parity_percentile is None, (
        "score_gap_parity_percentile must be None when percentile column is NULL"
    )

    perf = _get_endgame_performance_from_rows([], [], [], percentile_rows=null_pct_rows)
    assert perf.achievable_score_gap_percentile is None, (
        "achievable_score_gap_percentile must be None when percentile column is NULL"
    )
