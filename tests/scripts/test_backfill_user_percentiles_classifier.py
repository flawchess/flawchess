"""Unit tests for `_compute_and_count` classifier in backfill_user_percentiles.

Phase 94.1 Plan 10 — closes VERIFICATION.md gap #3 / REVIEW.md IN-03.
Phase 94.1 Plan 13 — updated to reflect two-state classifier (False branch removed).
Phase 94.2 Plan 06 — renamed counter to ``skipped_below_pooled_floor`` to match
the pooled-per-user inclusion floor (RESEARCH §Pitfall 7).

The classifier maps the outcome of compute_stage_a / compute_stage_b into one of
two return values consumed by the per-user summary counter at ``_backfill_user``:

    True  → row written (user passed the ≥30 pooled inclusion floor)  →  summary.upserted += 1
    None  → no row written (user below the pooled inclusion floor)    →  summary.skipped_below_pooled_floor += 1

Plan 13 correctness fix: the ``False`` branch (row exists with NULL percentile)
is removed. Below-floor users no longer produce rows at all — the service uses
a single floor-respecting CTE which returns no rows for below-floor users.
Below-floor users are counted under ``skipped_below_pooled_floor``.

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


def _make_session_maker() -> MagicMock:
    """Return a fake ``async_sessionmaker`` for mocking."""
    fake_session = MagicMock()
    fake_session.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session.__aexit__ = AsyncMock(return_value=None)
    return MagicMock(return_value=fake_session)


# ---------------------------------------------------------------------------
# Tests — _compute_and_count classifier (two branches, Plan 13)
# ---------------------------------------------------------------------------


async def test_returns_true_when_row_written() -> None:
    """Row exists post-compute → True (upserted).

    Plan 13: the classifier returns True when _row_exists returns True.
    The percentile column inspection is no longer needed (no below-floor rows).
    """
    session_maker = _make_session_maker()

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


async def test_returns_none_when_no_row_written() -> None:
    """No row post-compute → None (zero floor-passing cells).

    Plan 13: below-floor users produce no row (same path as zero games).
    """
    session_maker = _make_session_maker()

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
    """Stage='B' calls compute_stage_b, not compute_stage_a."""
    session_maker = _make_session_maker()

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
# Tests — _backfill_user consumer maps None → skipped_below_pooled_floor counter
# ---------------------------------------------------------------------------


async def test_backfill_user_increments_upserted_when_classifier_returns_true() -> None:
    """End-to-end inside _backfill_user: classifier True → upserted counter."""
    all_metrics: tuple[CdfMetricId, ...] = (bup.STAGE_A_METRIC, *bup.STAGE_B_METRICS)
    summary: dict[CdfMetricId, bup._MetricSummary] = {m: bup._MetricSummary() for m in all_metrics}

    fake_session_maker = MagicMock()
    fake_session_maker.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
    fake_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

    target: Literal["dev", "prod"] = "dev"
    with (
        patch.object(bup, "count_pending_evals", AsyncMock(return_value=0)),
        patch.object(bup, "_compute_and_count", AsyncMock(return_value=True)),
    ):
        await bup._backfill_user(
            user_id=_TEST_USER_ID,
            target=target,
            metric_filter=None,
            backfill_session_maker=fake_session_maker,
            summary=summary,
        )

    # All 4 metrics are upserted (pending_evals=0, all metrics computed)
    for metric_id in all_metrics:
        assert summary[metric_id].upserted == 1, f"expected upserted=1 for {metric_id}"
        assert summary[metric_id].skipped_below_pooled_floor == 0


async def test_backfill_user_increments_skipped_below_pooled_floor_when_classifier_returns_none() -> (
    None
):
    """End-to-end inside _backfill_user: classifier None → skipped_below_pooled_floor counter.

    Phase 94.2: below-floor users (failing the pooled ≥30 inclusion floor) return
    None from the classifier (no row written), mapped to skipped_below_pooled_floor.
    """
    all_metrics: tuple[CdfMetricId, ...] = (bup.STAGE_A_METRIC, *bup.STAGE_B_METRICS)
    summary: dict[CdfMetricId, bup._MetricSummary] = {m: bup._MetricSummary() for m in all_metrics}

    fake_session_maker = MagicMock()
    fake_session_maker.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
    fake_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

    # Force classifier to return None (no row written) for Stage A.
    # Stage B is skipped because pending_evals > 0.
    target: Literal["dev", "prod"] = "dev"
    with (
        patch.object(bup, "count_pending_evals", AsyncMock(return_value=1)),
        patch.object(bup, "_compute_and_count", AsyncMock(return_value=None)),
    ):
        await bup._backfill_user(
            user_id=_TEST_USER_ID,
            target=target,
            metric_filter=None,
            backfill_session_maker=fake_session_maker,
            summary=summary,
        )

    assert summary[bup.STAGE_A_METRIC].skipped_below_pooled_floor == 1
    assert summary[bup.STAGE_A_METRIC].upserted == 0
    # Stage B skipped due to pending_evals > 0
    for metric_id in bup.STAGE_B_METRICS:
        assert summary[metric_id].skipped_no_eval == 1
