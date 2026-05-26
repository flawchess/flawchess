"""Repository tests for user_rating_anchors: UPSERT round-trip + ENUM serialization.

Phase 94.4 Plan 02 Task 4.

Tests:
- test_upsert_inserts_when_no_row_exists
- test_upsert_overwrites_existing_row_in_place
- test_upsert_round_trip_source_platform_lichess
- test_upsert_round_trip_source_platform_chesscom
- test_fetch_anchors_for_user_returns_multi_tc_dict
- test_fetch_anchors_for_user_returns_empty_dict_when_no_rows
- test_upsert_changes_source_platform_via_conflict
- test_chesscom_raw_rating_round_trip

Guarded by ``pytest.importorskip`` so CI stays green before the table /
repository land.

Data isolation: all tests use the rollback-scoped ``db_session`` fixture
from ``tests/conftest.py`` — no committed rows leak between tests.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Guard — skip module until Plan 02 creates the repository
# ---------------------------------------------------------------------------

user_rating_anchors_repository = pytest.importorskip(
    "app.repositories.user_rating_anchors_repository",
    reason=(
        "user_rating_anchors_repository not implemented yet; will pass after Phase 94.4 Plan 02"
    ),
)

upsert_anchor = user_rating_anchors_repository.upsert_anchor
fetch_anchors_for_user = user_rating_anchors_repository.fetch_anchors_for_user
RatingAnchorRow = user_rating_anchors_repository.RatingAnchorRow

# ---------------------------------------------------------------------------
# Test constants — no magic numbers
# ---------------------------------------------------------------------------

_TEST_USER_ID: int = 9101
_SECOND_USER_ID: int = 9102
_THIRD_USER_ID: int = 9103

_DEFAULT_ANCHOR: int = 1600
_DEFAULT_N_GAMES: int = 250
_DEFAULT_CHESSCOM_RAW: int = 1830

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def _ensure_test_users(db_session: AsyncSession) -> None:
    """Insert test users referenced by FK constraints."""
    from tests.conftest import ensure_test_user

    for uid in (_TEST_USER_ID, _SECOND_USER_ID, _THIRD_USER_ID):
        await ensure_test_user(db_session, uid)


# ---------------------------------------------------------------------------
# Test 1 — UPSERT inserts a new row
# ---------------------------------------------------------------------------


async def test_upsert_inserts_when_no_row_exists(db_session: AsyncSession) -> None:
    """upsert_anchor creates a row that fetch_anchors_for_user retrieves."""
    await upsert_anchor(
        db_session,
        user_id=_TEST_USER_ID,
        time_control_bucket="rapid",
        anchor_rating=_DEFAULT_ANCHOR,
        source_platform="lichess",
        chesscom_raw_rating=None,
        n_games=_DEFAULT_N_GAMES,
    )
    await db_session.flush()

    result = await fetch_anchors_for_user(db_session, user_id=_TEST_USER_ID)

    assert "rapid" in result
    row = result["rapid"]
    assert row.anchor_rating == _DEFAULT_ANCHOR
    assert row.source_platform == "lichess"
    assert row.chesscom_raw_rating is None
    assert row.n_games == _DEFAULT_N_GAMES


# ---------------------------------------------------------------------------
# Test 2 — Second UPSERT updates in-place (PK widening works)
# ---------------------------------------------------------------------------


async def test_upsert_overwrites_existing_row_in_place(db_session: AsyncSession) -> None:
    """Second upsert_anchor for the same (user_id, tc) updates all columns."""
    await upsert_anchor(
        db_session,
        user_id=_TEST_USER_ID,
        time_control_bucket="blitz",
        anchor_rating=1500,
        source_platform="lichess",
        chesscom_raw_rating=None,
        n_games=80,
    )
    await db_session.flush()

    new_anchor = 1720
    new_n = 300
    await upsert_anchor(
        db_session,
        user_id=_TEST_USER_ID,
        time_control_bucket="blitz",
        anchor_rating=new_anchor,
        source_platform="lichess",
        chesscom_raw_rating=None,
        n_games=new_n,
    )
    await db_session.flush()

    result = await fetch_anchors_for_user(db_session, user_id=_TEST_USER_ID)

    assert "blitz" in result
    row = result["blitz"]
    assert row.anchor_rating == new_anchor, "anchor_rating must be updated by UPSERT"
    assert row.n_games == new_n, "n_games must be updated by UPSERT"
    # Only ONE row for this (user, tc) — no duplicate accumulation.
    assert isinstance(row, RatingAnchorRow)


# ---------------------------------------------------------------------------
# Test 3 — ENUM round-trip: 'lichess'
# ---------------------------------------------------------------------------


async def test_upsert_round_trip_source_platform_lichess(db_session: AsyncSession) -> None:
    """source_platform='lichess' round-trips correctly via anchor_source ENUM."""
    await upsert_anchor(
        db_session,
        user_id=_TEST_USER_ID,
        time_control_bucket="bullet",
        anchor_rating=1450,
        source_platform="lichess",
        chesscom_raw_rating=None,
        n_games=120,
    )
    await db_session.flush()

    result = await fetch_anchors_for_user(db_session, user_id=_TEST_USER_ID)

    assert result["bullet"].source_platform == "lichess"


# ---------------------------------------------------------------------------
# Test 4 — ENUM round-trip: 'chesscom'
# ---------------------------------------------------------------------------


async def test_upsert_round_trip_source_platform_chesscom(db_session: AsyncSession) -> None:
    """source_platform='chesscom' round-trips correctly via anchor_source ENUM."""
    await upsert_anchor(
        db_session,
        user_id=_TEST_USER_ID,
        time_control_bucket="classical",
        anchor_rating=1900,
        source_platform="chesscom",
        chesscom_raw_rating=_DEFAULT_CHESSCOM_RAW,
        n_games=60,
    )
    await db_session.flush()

    result = await fetch_anchors_for_user(db_session, user_id=_TEST_USER_ID)

    assert result["classical"].source_platform == "chesscom"


# ---------------------------------------------------------------------------
# Test 5 — fetch returns multi-TC dict; missing TCs absent
# ---------------------------------------------------------------------------


async def test_fetch_anchors_for_user_returns_multi_tc_dict(db_session: AsyncSession) -> None:
    """fetch returns up to 4 rows in a single dict keyed by TC; missing TCs absent."""
    # Insert 3 of 4 TCs for _SECOND_USER_ID (classical intentionally omitted)
    for tc, rating in [("bullet", 1400), ("blitz", 1500), ("rapid", 1600)]:
        await upsert_anchor(
            db_session,
            user_id=_SECOND_USER_ID,
            time_control_bucket=tc,
            anchor_rating=rating,
            source_platform="lichess",
            chesscom_raw_rating=None,
            n_games=_DEFAULT_N_GAMES,
        )
    await db_session.flush()

    result = await fetch_anchors_for_user(db_session, user_id=_SECOND_USER_ID)

    assert set(result.keys()) == {"bullet", "blitz", "rapid"}, (
        "fetch_anchors_for_user must return exactly the TCs with rows; "
        "missing TCs must not appear as None/empty rows"
    )
    assert result["bullet"].anchor_rating == 1400
    assert result["blitz"].anchor_rating == 1500
    assert result["rapid"].anchor_rating == 1600


# ---------------------------------------------------------------------------
# Test 6 — fetch returns empty dict when no rows
# ---------------------------------------------------------------------------


async def test_fetch_anchors_for_user_returns_empty_dict_when_no_rows(
    db_session: AsyncSession,
) -> None:
    """fetch_anchors_for_user returns {} for a user with no anchors."""
    result = await fetch_anchors_for_user(db_session, user_id=_THIRD_USER_ID)

    assert result == {}, "fetch_anchors_for_user must return empty dict, not None"


# ---------------------------------------------------------------------------
# Test 7 — UPSERT can switch source_platform on conflict
# ---------------------------------------------------------------------------


async def test_upsert_changes_source_platform_via_conflict(db_session: AsyncSession) -> None:
    """Inserting (user_id, tc) with 'lichess' then 'chesscom' updates source_platform.

    Mirrors the Lichess→chess.com fallback path (D-12): if Lichess fails the
    inclusion floor on later recompute, the wrapper writes a chess.com row
    via UPSERT and the source_platform flips.
    """
    # First write: Lichess
    await upsert_anchor(
        db_session,
        user_id=_TEST_USER_ID,
        time_control_bucket="rapid",
        anchor_rating=1700,
        source_platform="lichess",
        chesscom_raw_rating=None,
        n_games=200,
    )
    await db_session.flush()

    # Second write: chess.com (with raw rating preserved)
    await upsert_anchor(
        db_session,
        user_id=_TEST_USER_ID,
        time_control_bucket="rapid",
        anchor_rating=1750,
        source_platform="chesscom",
        chesscom_raw_rating=1980,
        n_games=80,
    )
    await db_session.flush()

    result = await fetch_anchors_for_user(db_session, user_id=_TEST_USER_ID)

    row = result["rapid"]
    assert row.source_platform == "chesscom"
    assert row.anchor_rating == 1750
    assert row.chesscom_raw_rating == 1980


# ---------------------------------------------------------------------------
# Test 8 — chesscom_raw_rating round-trip (D-07 bullet 4)
# ---------------------------------------------------------------------------


async def test_chesscom_raw_rating_round_trip(db_session: AsyncSession) -> None:
    """chesscom_raw_rating=1830 round-trips when source_platform='chesscom';
    chesscom_raw_rating=None round-trips when source_platform='lichess'.
    """
    # chesscom row carries the raw rating
    await upsert_anchor(
        db_session,
        user_id=_TEST_USER_ID,
        time_control_bucket="bullet",
        anchor_rating=1500,
        source_platform="chesscom",
        chesscom_raw_rating=_DEFAULT_CHESSCOM_RAW,
        n_games=70,
    )
    # lichess row carries None for raw
    await upsert_anchor(
        db_session,
        user_id=_TEST_USER_ID,
        time_control_bucket="blitz",
        anchor_rating=1600,
        source_platform="lichess",
        chesscom_raw_rating=None,
        n_games=90,
    )
    await db_session.flush()

    result = await fetch_anchors_for_user(db_session, user_id=_TEST_USER_ID)

    assert result["bullet"].chesscom_raw_rating == _DEFAULT_CHESSCOM_RAW
    assert result["blitz"].chesscom_raw_rating is None
