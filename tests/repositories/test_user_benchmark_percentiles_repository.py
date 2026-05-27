"""Repository tests for user_benchmark_percentiles: UPSERT, NULL, FK CASCADE.

Phase 94.1 Plan 01 Wave 0.

Tests:
- test_upsert_inserts_when_no_row_exists
- test_upsert_overwrites_existing_row
- test_upsert_handles_percentile_null
- test_fk_cascade_on_user_delete  (ON DELETE CASCADE from users)
- test_pk_rejects_duplicate_metric_for_same_user_via_plain_insert
- test_fetch_for_user_returns_dict_keyed_by_metric_id

Guarded by ``pytest.importorskip`` so CI stays green until Plan 04 ships
``app.repositories.user_benchmark_percentiles_repository``.

Data isolation: all tests use the rollback-scoped ``db_session`` fixture from
``tests/conftest.py`` — no committed rows leak between tests.

Plan 13 (gap-closure): ``n_cells_floor`` column dropped from the table and
from all test fixtures / assertions. Row existence implies above-floor.
"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Guard — skip module until Plan 04 creates the repository
# ---------------------------------------------------------------------------

user_benchmark_percentiles_repository = pytest.importorskip(
    "app.repositories.user_benchmark_percentiles_repository",
    reason=("user_benchmark_percentiles_repository not implemented yet; will pass after Plan 04"),
)

# Convenience aliases to functions we'll call once the module exists.
upsert_percentile = user_benchmark_percentiles_repository.upsert_percentile
fetch_for_user = user_benchmark_percentiles_repository.fetch_for_user

# ---------------------------------------------------------------------------
# Test constants — no magic numbers
# ---------------------------------------------------------------------------

_TEST_USER_ID: int = 9001
_SECOND_USER_ID: int = 9002
_METRIC_SCORE_GAP: str = "score_gap"
_METRIC_ACHIEVABLE: str = "achievable_score_gap"
_METRIC_CONV: str = "score_gap_conv"
_METRIC_PARITY: str = "score_gap_parity"
_ALL_METRICS: tuple[str, ...] = (
    _METRIC_SCORE_GAP,
    _METRIC_ACHIEVABLE,
    _METRIC_CONV,
    _METRIC_PARITY,
)

_DEFAULT_VALUE: float = 0.05
_DEFAULT_PERCENTILE: float = 62.3
_DEFAULT_CDF_SNAPSHOT: datetime.date = datetime.date(2026, 3, 31)
_DEFAULT_N_GAMES: int = 42  # arbitrary pooled count — n_games is required (Phase 94.2)
# Phase 94.4 D-01: PK widens to include time_control_bucket. Tests use a
# single canonical TC unless they exercise the per-TC dimensionality
# directly. ``blitz`` mirrors the canonical-slice test seeds elsewhere.
from app.models.user_rating_anchors import TimeControlBucket as _TimeControlBucket  # noqa: E402

_DEFAULT_TC: _TimeControlBucket = "blitz"

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def _ensure_test_users(db_session: AsyncSession) -> None:
    """Insert test users referenced by FK constraints.

    Uses conftest.ensure_test_user which is idempotent (no-op if user exists).
    """
    from tests.conftest import ensure_test_user

    for uid in (_TEST_USER_ID, _SECOND_USER_ID):
        await ensure_test_user(db_session, uid)


# ---------------------------------------------------------------------------
# Test 1 — UPSERT inserts a new row when none exists
# ---------------------------------------------------------------------------


async def test_upsert_inserts_when_no_row_exists(db_session: AsyncSession) -> None:
    """upsert_percentile creates a row that SELECT can retrieve."""
    # Phase 94.4 D-01 / D-08: PK widens to (user_id, metric,
    # time_control_bucket); fetch_for_user returns nested dict
    # dict[CdfMetricId, dict[TimeControlBucket, PercentileRow]].
    await upsert_percentile(
        db_session,
        user_id=_TEST_USER_ID,
        metric=_METRIC_SCORE_GAP,
        time_control_bucket=_DEFAULT_TC,
        value=_DEFAULT_VALUE,
        n_games=_DEFAULT_N_GAMES,
        percentile=_DEFAULT_PERCENTILE,
        cdf_snapshot=_DEFAULT_CDF_SNAPSHOT,
    )
    await db_session.flush()

    rows = fetch_for_user(db_session, user_id=_TEST_USER_ID)
    # fetch_for_user may be sync or async — handle both
    if hasattr(rows, "__await__"):
        result = await rows
    else:
        result = rows

    assert _METRIC_SCORE_GAP in result, "upserted metric must appear in fetch_for_user result"
    assert _DEFAULT_TC in result[_METRIC_SCORE_GAP], (
        "upserted (metric, tc) cell must appear in the nested dict"
    )
    row = result[_METRIC_SCORE_GAP][_DEFAULT_TC]
    assert abs(row.value - _DEFAULT_VALUE) < 1e-9
    assert row.percentile is not None
    assert abs(row.percentile - _DEFAULT_PERCENTILE) < 1e-9


# ---------------------------------------------------------------------------
# Test 2 — UPSERT overwrites all mutable columns on conflict
# ---------------------------------------------------------------------------


async def test_upsert_overwrites_existing_row(db_session: AsyncSession) -> None:
    """Second upsert with new value/percentile/cdf_snapshot overwrites all."""
    # Initial insert
    await upsert_percentile(
        db_session,
        user_id=_TEST_USER_ID,
        metric=_METRIC_ACHIEVABLE,
        time_control_bucket=_DEFAULT_TC,
        value=0.10,
        n_games=35,
        percentile=45.0,
        cdf_snapshot=datetime.date(2026, 1, 1),
    )
    await db_session.flush()

    # Second upsert with new values
    new_value = 0.25
    new_percentile = 78.5
    new_snapshot = datetime.date(2026, 3, 31)
    new_n_games = 90

    await upsert_percentile(
        db_session,
        user_id=_TEST_USER_ID,
        metric=_METRIC_ACHIEVABLE,
        time_control_bucket=_DEFAULT_TC,
        value=new_value,
        n_games=new_n_games,
        percentile=new_percentile,
        cdf_snapshot=new_snapshot,
    )
    await db_session.flush()

    rows = fetch_for_user(db_session, user_id=_TEST_USER_ID)
    if hasattr(rows, "__await__"):
        result = await rows
    else:
        result = rows

    assert _METRIC_ACHIEVABLE in result
    assert _DEFAULT_TC in result[_METRIC_ACHIEVABLE]
    row = result[_METRIC_ACHIEVABLE][_DEFAULT_TC]
    assert abs(row.value - new_value) < 1e-9, "value must be updated by UPSERT"
    assert row.percentile is not None
    assert abs(row.percentile - new_percentile) < 1e-9, "percentile must be updated"
    assert row.cdf_snapshot == new_snapshot, "cdf_snapshot must be updated"


# ---------------------------------------------------------------------------
# Test 3 — UPSERT stores percentile=NULL and returns Python None
# ---------------------------------------------------------------------------


async def test_upsert_handles_percentile_null(db_session: AsyncSession) -> None:
    """upsert_percentile with percentile=None stores NULL; fetch returns None.

    This path may occur when the CDF lookup produces None (e.g., value out of
    range). The row is still written — the caller controls whether to write.
    Plan 13: below-floor users no longer produce rows at all; this test covers
    the case where a value is computed but the percentile lookup returns None.
    """
    await upsert_percentile(
        db_session,
        user_id=_TEST_USER_ID,
        metric=_METRIC_CONV,
        time_control_bucket=_DEFAULT_TC,
        value=0.08,
        n_games=_DEFAULT_N_GAMES,
        percentile=None,
        cdf_snapshot=_DEFAULT_CDF_SNAPSHOT,
    )
    await db_session.flush()

    rows = fetch_for_user(db_session, user_id=_TEST_USER_ID)
    if hasattr(rows, "__await__"):
        result = await rows
    else:
        result = rows

    assert _METRIC_CONV in result, "row must be present even with NULL percentile"
    assert _DEFAULT_TC in result[_METRIC_CONV]
    row = result[_METRIC_CONV][_DEFAULT_TC]
    assert row.percentile is None, "percentile must be Python None when stored as SQL NULL (D-06)"
    assert abs(row.value - 0.08) < 1e-9, "value must be stored correctly"


# ---------------------------------------------------------------------------
# Test 4 — FK CASCADE: deleting user removes all percentile rows
# ---------------------------------------------------------------------------


async def test_fk_cascade_on_user_delete(db_session: AsyncSession) -> None:
    """Deleting the user cascades to remove all user_benchmark_percentiles rows.

    ON DELETE CASCADE from users.id ensures referential integrity — no orphan
    percentile rows survive after the user is removed (D-08 schema spec).
    """
    from sqlalchemy import delete, text

    from app.models.user import User

    # Insert all 4 metric rows for _SECOND_USER_ID
    for metric in _ALL_METRICS:
        await upsert_percentile(
            db_session,
            user_id=_SECOND_USER_ID,
            metric=metric,
            time_control_bucket=_DEFAULT_TC,
            value=0.05,
            n_games=_DEFAULT_N_GAMES,
            percentile=50.0,
            cdf_snapshot=_DEFAULT_CDF_SNAPSHOT,
        )
    await db_session.flush()

    # Verify 4 rows exist
    count_before = await db_session.execute(
        text("SELECT COUNT(*) FROM user_benchmark_percentiles WHERE user_id = :uid").bindparams(
            uid=_SECOND_USER_ID
        )
    )
    assert count_before.scalar_one() == 4, "must have 4 rows before delete"

    # Delete the user — ON DELETE CASCADE must remove all 4 percentile rows
    await db_session.execute(delete(User).where(User.id == _SECOND_USER_ID))
    await db_session.flush()

    count_after = await db_session.execute(
        text("SELECT COUNT(*) FROM user_benchmark_percentiles WHERE user_id = :uid").bindparams(
            uid=_SECOND_USER_ID
        )
    )
    cascade_count = count_after.scalar_one()
    assert cascade_count == 0, (
        "ON DELETE CASCADE must remove all user_benchmark_percentiles rows "
        "when the referenced user is deleted"
    )


# ---------------------------------------------------------------------------
# Test 5 — plain INSERT duplicate raises IntegrityError (PK constraint)
# ---------------------------------------------------------------------------


async def test_pk_rejects_duplicate_metric_for_same_user_via_plain_insert(
    db_session: AsyncSession,
) -> None:
    """A plain INSERT without ON CONFLICT fails with IntegrityError on duplicate PK.

    Phase 94.4 D-01: the PK widens to (user_id, metric, time_control_bucket).
    A duplicate (user, metric, tc) plain INSERT/INSERT still violates the
    PK; a SAME (user, metric) on a DIFFERENT tc is now legal (each TC has
    its own row).

    This confirms that UPSERT via ``on_conflict_do_update`` is the ONLY safe
    write path — naive INSERT/INSERT will violate the 3-column PK.
    """
    from sqlalchemy import text

    # First insert — should succeed
    await db_session.execute(
        text(
            "INSERT INTO user_benchmark_percentiles "
            "(user_id, metric, time_control_bucket, value, n_games, cdf_snapshot) "
            "VALUES (:uid, :metric, CAST(:tc AS timecontrolbucket), :value, :n, :snapshot)"
        ).bindparams(
            uid=_TEST_USER_ID,
            metric=_METRIC_PARITY,
            tc=_DEFAULT_TC,
            value=0.03,
            n=_DEFAULT_N_GAMES,
            snapshot=_DEFAULT_CDF_SNAPSHOT,
        )
    )
    await db_session.flush()

    # Second plain INSERT on SAME (user, metric, tc) must fail with IntegrityError
    with pytest.raises(IntegrityError):
        await db_session.execute(
            text(
                "INSERT INTO user_benchmark_percentiles "
                "(user_id, metric, time_control_bucket, value, n_games, cdf_snapshot) "
                "VALUES (:uid, :metric, CAST(:tc AS timecontrolbucket), :value, :n, :snapshot)"
            ).bindparams(
                uid=_TEST_USER_ID,
                metric=_METRIC_PARITY,
                tc=_DEFAULT_TC,
                value=0.07,
                n=_DEFAULT_N_GAMES,
                snapshot=_DEFAULT_CDF_SNAPSHOT,
            )
        )
        await db_session.flush()


# ---------------------------------------------------------------------------
# Test 6 — fetch_for_user returns dict keyed by metric_id (partial fill)
# ---------------------------------------------------------------------------


async def test_fetch_for_user_returns_dict_keyed_by_metric_id(
    db_session: AsyncSession,
) -> None:
    """fetch_for_user returns a dict keyed by metric_id with only inserted metrics.

    When only 2 of the 4 metrics have been computed for a user (e.g. Stage A
    has fired but Stage B has not), fetch_for_user must return exactly those
    2 keys and not fabricate rows for the missing metrics.
    """
    # Insert only 2 of 4 metrics
    await upsert_percentile(
        db_session,
        user_id=_TEST_USER_ID,
        metric=_METRIC_SCORE_GAP,
        time_control_bucket=_DEFAULT_TC,
        value=0.04,
        n_games=_DEFAULT_N_GAMES,
        percentile=55.0,
        cdf_snapshot=_DEFAULT_CDF_SNAPSHOT,
    )
    await upsert_percentile(
        db_session,
        user_id=_TEST_USER_ID,
        metric=_METRIC_PARITY,
        time_control_bucket=_DEFAULT_TC,
        value=-0.02,
        n_games=_DEFAULT_N_GAMES,
        percentile=38.0,
        cdf_snapshot=_DEFAULT_CDF_SNAPSHOT,
    )
    await db_session.flush()

    rows = fetch_for_user(db_session, user_id=_TEST_USER_ID)
    if hasattr(rows, "__await__"):
        result = await rows
    else:
        result = rows

    assert set(result.keys()) == {_METRIC_SCORE_GAP, _METRIC_PARITY}, (
        "fetch_for_user must return exactly the metric IDs that have rows; "
        "missing metrics must not appear as None/empty rows"
    )

    sg = result[_METRIC_SCORE_GAP][_DEFAULT_TC]
    assert abs(sg.value - 0.04) < 1e-9
    assert sg.percentile is not None
    assert abs(sg.percentile - 55.0) < 1e-9

    par = result[_METRIC_PARITY][_DEFAULT_TC]
    assert abs(par.value - (-0.02)) < 1e-9
    assert par.percentile is not None
    assert abs(par.percentile - 38.0) < 1e-9
