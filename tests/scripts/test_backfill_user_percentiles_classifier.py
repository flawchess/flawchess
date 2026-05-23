"""Unit tests for `_compute_and_count` classifier in backfill_user_percentiles.

Phase 94.1 Plan 10 — closes VERIFICATION.md gap #3 / REVIEW.md IN-03.

The classifier maps the outcome of compute_stage_a / compute_stage_b into one of
three return values consumed by the per-user summary counter at
``_backfill_user`` (lines 373-378 / 393-398):

    True   → row written with non-null percentile  →  summary.upserted += 1
    False  → row exists but percentile IS NULL     →  summary.skipped_below_floor += 1
    None   → no row written (zero canonical-slice games) → summary.skipped_no_canonical_games += 1

Prior to this plan the classifier never returned False, so below-floor users were
mis-counted as upserted. These tests pin all three branches.

Pure unit tests — no real DB. The compute service and the row-existence helper
are mocked. Real-DB end-to-end coverage already lands via the integration test
added in Plan 09 + the backfill HUMAN-UAT.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── Bootstrap scripts/ on sys.path ───────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts import backfill_user_percentiles as bup  # noqa: E402 — after sys.path bootstrap
from app.services.global_percentile_cdf import CdfMetricId  # noqa: E402 — after sys.path bootstrap

pytestmark = pytest.mark.asyncio

# ── Module-level constants (CLAUDE.md: no magic numbers) ─────────────────────
_TEST_USER_ID: int = 99410
_NON_NULL_PERCENTILE: float = 42.0
_STAGE_A_METRIC: CdfMetricId = "score_gap"
_STAGE_B_METRIC: CdfMetricId = "achievable_score_gap"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_maker_returning_percentile(percentile: float | None) -> MagicMock:
    """Return a fake `async_sessionmaker` whose session.execute() returns a row
    with the given `percentile` value when the inline SELECT runs.

    The fake session also supports `async with` so the classifier's
    ``async with backfill_session_maker() as session`` block works.
    """
    fake_row = MagicMock()
    fake_row.percentile = percentile

    fake_result = MagicMock()
    fake_result.fetchone = MagicMock(return_value=fake_row)

    fake_session = MagicMock()
    fake_session.execute = AsyncMock(return_value=fake_result)
    fake_session.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session.__aexit__ = AsyncMock(return_value=None)

    session_maker = MagicMock(return_value=fake_session)
    return session_maker


# ---------------------------------------------------------------------------
# Tests — _compute_and_count classifier (three branches)
# ---------------------------------------------------------------------------


async def test_returns_true_when_row_written_with_non_null_percentile() -> None:
    """Row exists post-compute, percentile is non-null → True (upserted)."""
    session_maker = _make_session_maker_returning_percentile(_NON_NULL_PERCENTILE)

    with (
        patch.object(bup, "_row_exists", AsyncMock(return_value=True)) as mock_exists,
        patch.object(bup, "compute_stage_a", AsyncMock(return_value=None)) as mock_stage_a,
    ):
        result = await bup._compute_and_count(
            user_id=_TEST_USER_ID,
            metric=_STAGE_A_METRIC,
            stage="A",
            backfill_session_maker=session_maker,
        )

    assert result is True
    mock_stage_a.assert_awaited_once()
    # Post-compute row_exists probe must have been called at least once.
    assert mock_exists.await_count >= 1


async def test_returns_false_when_row_written_with_null_percentile() -> None:
    """Row exists post-compute, percentile IS NULL (below floor) → False."""
    session_maker = _make_session_maker_returning_percentile(None)

    with (
        patch.object(bup, "_row_exists", AsyncMock(return_value=True)),
        patch.object(bup, "compute_stage_a", AsyncMock(return_value=None)),
    ):
        result = await bup._compute_and_count(
            user_id=_TEST_USER_ID,
            metric=_STAGE_A_METRIC,
            stage="A",
            backfill_session_maker=session_maker,
        )

    assert result is False, (
        "Below-floor users must produce a False classifier outcome "
        "so summary.skipped_below_floor is reachable (IN-03 fix)."
    )


async def test_returns_none_when_no_row_written() -> None:
    """No row post-compute → None (zero canonical-slice games)."""
    # session_maker isn't consulted on the None path (early return), but pass a
    # benign one anyway to mirror the real call shape.
    session_maker = _make_session_maker_returning_percentile(_NON_NULL_PERCENTILE)

    with (
        patch.object(bup, "_row_exists", AsyncMock(return_value=False)),
        patch.object(bup, "compute_stage_a", AsyncMock(return_value=None)) as mock_stage_a,
    ):
        result = await bup._compute_and_count(
            user_id=_TEST_USER_ID,
            metric=_STAGE_A_METRIC,
            stage="A",
            backfill_session_maker=session_maker,
        )

    assert result is None
    mock_stage_a.assert_awaited_once()


async def test_stage_b_routes_to_compute_stage_b() -> None:
    """Stage='B' calls compute_stage_b, not compute_stage_a (smoke-check
    that the stage-routing arm is unaffected by the IN-03 fix)."""
    session_maker = _make_session_maker_returning_percentile(_NON_NULL_PERCENTILE)

    with (
        patch.object(bup, "_row_exists", AsyncMock(return_value=True)),
        patch.object(bup, "compute_stage_a", AsyncMock(return_value=None)) as mock_a,
        patch.object(bup, "compute_stage_b", AsyncMock(return_value=None)) as mock_b,
    ):
        result = await bup._compute_and_count(
            user_id=_TEST_USER_ID,
            metric=_STAGE_B_METRIC,
            stage="B",
            backfill_session_maker=session_maker,
        )

    assert result is True
    mock_b.assert_awaited_once()
    mock_a.assert_not_awaited()


# ---------------------------------------------------------------------------
# Tests — _backfill_user consumer maps False → skipped_below_floor
# ---------------------------------------------------------------------------


async def test_backfill_user_increments_skipped_below_floor_when_classifier_returns_false() -> None:
    """End-to-end inside _backfill_user: classifier False → skipped_below_floor counter."""
    all_metrics: tuple[CdfMetricId, ...] = (bup.STAGE_A_METRIC, *bup.STAGE_B_METRICS)
    summary: dict[CdfMetricId, bup._MetricSummary] = {m: bup._MetricSummary() for m in all_metrics}

    # session_maker is consulted by count_pending_evals; mock that helper.
    fake_session_maker = MagicMock()
    fake_session_maker.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
    fake_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

    # Force classifier to return False (below-floor) for Stage A.
    # Stage B is skipped because pending_evals > 0.
    target: Literal["dev", "prod"] = "dev"
    with (
        patch.object(bup, "count_pending_evals", AsyncMock(return_value=1)),
        patch.object(bup, "_compute_and_count", AsyncMock(return_value=False)),
    ):
        await bup._backfill_user(
            user_id=_TEST_USER_ID,
            target=target,
            metric_filter=None,
            backfill_session_maker=fake_session_maker,
            summary=summary,
        )

    assert summary[bup.STAGE_A_METRIC].skipped_below_floor == 1
    assert summary[bup.STAGE_A_METRIC].upserted == 0
    assert summary[bup.STAGE_A_METRIC].skipped_no_canonical_games == 0
