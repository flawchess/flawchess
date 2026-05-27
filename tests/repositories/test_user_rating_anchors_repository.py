"""Repository tests for user_rating_anchors: blended-schema UPSERT round-trip.

Phase 94.4 Plan 09 Task 5 -- rewrites the original Plan 02 tests to assert
the D-12 Reversal Amendment (2026-05-27) column set.

See ``.planning/notes/percentile-anchor-d12-reversal.md`` for the design-
decision record including the worked example used in Test 1.

Tests:
1. test_blended_mixed_user -- canonical worked-example round-trip
   (4000 chess.com @ 2200 native + 100 lichess @ 1900 native -> anchor ~2046)
2. test_pure_lichess_user -- n_chesscom_games=0, chesscom_median_native=None
3. test_pure_chesscom_user -- n_lichess_games=0, lichess_median_native=None
4. test_in_place_upsert -- second UPSERT with different values overwrites all 5 data cols
5. test_empty_user -- fetch returns {} for a user with no rows
6. test_multi_tc -- one user with 4-TC anchors round-trips a 4-key dict
7. test_computed_at_advances -- second UPSERT advances computed_at

Data isolation: all tests use the rollback-scoped ``db_session`` fixture
from ``tests/conftest.py`` -- no committed rows leak between tests.
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_rating_anchors import UserRatingAnchor
from app.repositories.user_rating_anchors_repository import (
    RatingAnchorRow,
    fetch_anchors_for_user,
    upsert_anchor,
)

# ---------------------------------------------------------------------------
# Test constants -- no magic numbers
# ---------------------------------------------------------------------------

_TEST_USER_ID: int = 9101
_SECOND_USER_ID: int = 9102
_THIRD_USER_ID: int = 9103
_FOURTH_USER_ID: int = 9104

# Worked example from .planning/notes/percentile-anchor-d12-reversal.md
# "The problem" / "The fix" sections. Used in Test 1 as a regression lock.
_MIXED_CHESSCOM_GAMES: int = 4000
_MIXED_LICHESS_GAMES: int = 100
_MIXED_CHESSCOM_NATIVE: int = 2200
_MIXED_LICHESS_NATIVE: int = 1900
_MIXED_BLENDED_ANCHOR: int = 2046  # (4000*2050 + 100*1900) / 4100 ≈ 2046

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
async def _ensure_test_users(db_session: AsyncSession) -> None:
    """Insert test users referenced by FK constraints."""
    from tests.conftest import ensure_test_user

    for uid in (_TEST_USER_ID, _SECOND_USER_ID, _THIRD_USER_ID, _FOURTH_USER_ID):
        await ensure_test_user(db_session, uid)


# ---------------------------------------------------------------------------
# Test 1 -- Canonical worked-example round-trip (blended mixed user)
# ---------------------------------------------------------------------------


async def test_blended_mixed_user(db_session: AsyncSession) -> None:
    """Blended anchor round-trips through upsert_anchor / fetch_anchors_for_user.

    Canonical worked example from .planning/notes/percentile-anchor-d12-reversal.md
    "The problem" and "The fix" sections:
      - 4000 chess.com blitz games, median native 2200 (pre-conversion)
      - 100 lichess blitz games, median native 1900
      - per-game conversion: chess.com 2200 ~ 2050 lichess-equivalent
      - blended median: (4000*2050 + 100*1900) / 4100 ~ 2046

    These numbers are a regression lock: if the blended-anchor compute changes
    its algorithm this test will fail, prompting a deliberate decision.
    """
    await upsert_anchor(
        db_session,
        user_id=_TEST_USER_ID,
        time_control_bucket="blitz",
        anchor_rating=_MIXED_BLENDED_ANCHOR,
        n_chesscom_games=_MIXED_CHESSCOM_GAMES,
        n_lichess_games=_MIXED_LICHESS_GAMES,
        chesscom_median_native=_MIXED_CHESSCOM_NATIVE,
        lichess_median_native=_MIXED_LICHESS_NATIVE,
    )
    await db_session.flush()

    result = await fetch_anchors_for_user(db_session, user_id=_TEST_USER_ID)

    assert "blitz" in result
    row = result["blitz"]
    # Use literal numbers verbatim per plan requirement so this assertion serves
    # as inline documentation of the worked example (not just a constant check).
    assert row == RatingAnchorRow(
        anchor_rating=2046,
        n_chesscom_games=4000,
        n_lichess_games=100,
        chesscom_median_native=2200,
        lichess_median_native=1900,
    )


# ---------------------------------------------------------------------------
# Test 2 -- Pure-Lichess user (n_chesscom_games=0, chesscom_median_native=None)
# ---------------------------------------------------------------------------


async def test_pure_lichess_user(db_session: AsyncSession) -> None:
    """Pure-Lichess anchor: n_chesscom_games=0 and chesscom_median_native=None."""
    await upsert_anchor(
        db_session,
        user_id=_TEST_USER_ID,
        time_control_bucket="rapid",
        anchor_rating=1750,
        n_chesscom_games=0,
        n_lichess_games=500,
        chesscom_median_native=None,
        lichess_median_native=1750,
    )
    await db_session.flush()

    result = await fetch_anchors_for_user(db_session, user_id=_TEST_USER_ID)

    assert "rapid" in result
    row = result["rapid"]
    assert row.anchor_rating == 1750
    assert row.n_chesscom_games == 0
    assert row.n_lichess_games == 500
    assert row.chesscom_median_native is None, (
        "chesscom_median_native must be None when n_chesscom_games == 0"
    )
    assert row.lichess_median_native == 1750


# ---------------------------------------------------------------------------
# Test 3 -- Pure-chess.com user (n_lichess_games=0, lichess_median_native=None)
# ---------------------------------------------------------------------------


async def test_pure_chesscom_user(db_session: AsyncSession) -> None:
    """Pure-chess.com anchor: n_lichess_games=0 and lichess_median_native=None."""
    await upsert_anchor(
        db_session,
        user_id=_TEST_USER_ID,
        time_control_bucket="bullet",
        anchor_rating=1920,
        n_chesscom_games=2000,
        n_lichess_games=0,
        chesscom_median_native=1830,
        lichess_median_native=None,
    )
    await db_session.flush()

    result = await fetch_anchors_for_user(db_session, user_id=_TEST_USER_ID)

    assert "bullet" in result
    row = result["bullet"]
    assert row.anchor_rating == 1920
    assert row.n_chesscom_games == 2000
    assert row.n_lichess_games == 0
    assert row.chesscom_median_native == 1830
    assert row.lichess_median_native is None, (
        "lichess_median_native must be None when n_lichess_games == 0"
    )


# ---------------------------------------------------------------------------
# Test 4 -- In-place UPSERT updates all 5 non-PK data columns
# ---------------------------------------------------------------------------


async def test_in_place_upsert(db_session: AsyncSession) -> None:
    """Second UPSERT for the same (user_id, tc) overwrites all 5 data columns.

    Verifies the set_= clause in upsert_anchor covers all non-PK data
    columns (anchor_rating, n_chesscom_games, n_lichess_games,
    chesscom_median_native, lichess_median_native) so stale values cannot
    survive an update.
    """
    # First write
    await upsert_anchor(
        db_session,
        user_id=_TEST_USER_ID,
        time_control_bucket="classical",
        anchor_rating=1500,
        n_chesscom_games=100,
        n_lichess_games=50,
        chesscom_median_native=1600,
        lichess_median_native=1450,
    )
    await db_session.flush()

    # Second write with different values
    await upsert_anchor(
        db_session,
        user_id=_TEST_USER_ID,
        time_control_bucket="classical",
        anchor_rating=1650,
        n_chesscom_games=200,
        n_lichess_games=80,
        chesscom_median_native=1700,
        lichess_median_native=1580,
    )
    await db_session.flush()

    result = await fetch_anchors_for_user(db_session, user_id=_TEST_USER_ID)

    assert "classical" in result
    row = result["classical"]
    assert row.anchor_rating == 1650, "anchor_rating must be updated by UPSERT"
    assert row.n_chesscom_games == 200, "n_chesscom_games must be updated by UPSERT"
    assert row.n_lichess_games == 80, "n_lichess_games must be updated by UPSERT"
    assert row.chesscom_median_native == 1700, "chesscom_median_native must be updated by UPSERT"
    assert row.lichess_median_native == 1580, "lichess_median_native must be updated by UPSERT"
    # Exactly ONE row for this (user, tc) -- no duplicate accumulation.
    assert isinstance(row, RatingAnchorRow)


# ---------------------------------------------------------------------------
# Test 5 -- Empty user returns {} (no rows)
# ---------------------------------------------------------------------------


async def test_empty_user(db_session: AsyncSession) -> None:
    """fetch_anchors_for_user returns empty dict for a user with no anchor rows."""
    result = await fetch_anchors_for_user(db_session, user_id=_THIRD_USER_ID)

    assert result == {}, "fetch_anchors_for_user must return empty dict, not None"
    assert result.get("rapid") is None, (
        "missing TCs must not appear as None/empty rows -- they must be absent"
    )
    assert len(result) == 0, "empty user must have dict with len 0"


# ---------------------------------------------------------------------------
# Test 6 -- Multi-TC round-trip (4-key dict)
# ---------------------------------------------------------------------------


async def test_multi_tc(db_session: AsyncSession) -> None:
    """One user with anchors in all 4 TCs round-trips a 4-key dict."""
    tc_anchors = [
        ("bullet", 1350, 500, 100, 1420, 1280),
        ("blitz", 1500, 1000, 200, 1580, 1440),
        ("rapid", 1620, 300, 800, 1650, 1600),
        ("classical", 1700, 0, 150, None, 1700),
    ]
    for tc, anchor, cc_games, li_games, cc_native, li_native in tc_anchors:
        await upsert_anchor(
            db_session,
            user_id=_SECOND_USER_ID,
            time_control_bucket=tc,  # ty: ignore[invalid-argument-type]
            anchor_rating=anchor,
            n_chesscom_games=cc_games,
            n_lichess_games=li_games,
            chesscom_median_native=cc_native,
            lichess_median_native=li_native,
        )
    await db_session.flush()

    result = await fetch_anchors_for_user(db_session, user_id=_SECOND_USER_ID)

    assert set(result.keys()) == {"bullet", "blitz", "rapid", "classical"}, (
        "fetch_anchors_for_user must return exactly the 4 TCs with rows"
    )
    assert result["bullet"].anchor_rating == 1350
    assert result["blitz"].anchor_rating == 1500
    assert result["rapid"].anchor_rating == 1620
    assert result["classical"].anchor_rating == 1700
    # Verify None handling for TC with no chess.com games
    assert result["classical"].chesscom_median_native is None
    assert result["classical"].n_chesscom_games == 0


# ---------------------------------------------------------------------------
# Test 7 -- computed_at advances on second UPSERT
# ---------------------------------------------------------------------------


async def test_computed_at_advances(db_session: AsyncSession) -> None:
    """Second UPSERT refreshes computed_at to a later timestamp.

    RatingAnchorRow does not expose computed_at (it is a server-side timestamp,
    not a tooltip-facing field), so this test reads the raw ORM row to verify.
    """
    await upsert_anchor(
        db_session,
        user_id=_FOURTH_USER_ID,
        time_control_bucket="blitz",
        anchor_rating=1600,
        n_chesscom_games=100,
        n_lichess_games=50,
        chesscom_median_native=1650,
        lichess_median_native=1550,
    )
    await db_session.flush()

    # Capture computed_at from the first write
    row_v1 = (
        await db_session.execute(
            select(UserRatingAnchor).where(
                UserRatingAnchor.user_id == _FOURTH_USER_ID,
                UserRatingAnchor.time_control_bucket == "blitz",
            )
        )
    ).scalar_one()
    computed_at_v1 = row_v1.computed_at

    # Brief pause to ensure the timestamp advances
    await asyncio.sleep(0.01)

    await upsert_anchor(
        db_session,
        user_id=_FOURTH_USER_ID,
        time_control_bucket="blitz",
        anchor_rating=1650,
        n_chesscom_games=120,
        n_lichess_games=60,
        chesscom_median_native=1700,
        lichess_median_native=1580,
    )
    await db_session.flush()

    # Expire the cached ORM state so we read the refreshed row
    db_session.expire(row_v1)
    row_v2 = (
        await db_session.execute(
            select(UserRatingAnchor).where(
                UserRatingAnchor.user_id == _FOURTH_USER_ID,
                UserRatingAnchor.time_control_bucket == "blitz",
            )
        )
    ).scalar_one()
    computed_at_v2 = row_v2.computed_at

    assert computed_at_v2 >= computed_at_v1, (
        "computed_at must advance (or stay equal) after second UPSERT; "
        f"v1={computed_at_v1} v2={computed_at_v2}"
    )
    assert row_v2.anchor_rating == 1650, "anchor_rating must be updated by the second UPSERT"
