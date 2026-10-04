"""Tests for the claim and tally reads of app.repositories.train_medals_repository (Phase 231, plan 02).

Real-row checks on the rollback-scoped ``db_session`` fixture (no committed rows leak).
Every test claims the week's marker (`claim_week`) before inserting standings, because
`train_weekly_standings.week_start` is a foreign key to the marker table.

Reservation (shared with Plan 06's tests/repositories/test_train_medals_finalization.py,
which holds user ids 93700-93719 and weeks k 0-19 from the same base Monday): this module
holds user ids 93720-93739 and weeks k 20-39, counted from Monday 2034-01-02. A k is
never reused in this module.

k table:
- k=20 test_fetch_unclaimed_orders_newest_week_first_and_flags_shared (older week)
- k=21 test_fetch_unclaimed_orders_newest_week_first_and_flags_shared (newer week)
- k=22 test_fetch_unclaimed_skips_celebrated_non_medal_and_foreign_rows
- k=23 test_fetch_unclaimed_respects_the_limit
- k=24 test_fetch_unclaimed_respects_the_limit
- k=25 test_fetch_unclaimed_respects_the_limit
- k=26 test_mark_celebrated_is_scoped_to_the_caller_and_idempotent
- k=27 test_tally_rows_group_by_board_user_and_medal
- k=28 test_tally_rows_group_by_board_user_and_medal
"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.train_weekly_standing import Medal, TrainWeeklyStanding
from app.repositories.train_medals_repository import (
    NewStanding,
    TallyCount,
    UnclaimedRow,
    claim_week,
    fetch_medal_tallies,
    fetch_unclaimed,
    insert_standings,
    mark_celebrated,
)
from app.schemas.train import LeaderboardBoardKind
from tests.conftest import ensure_test_user

# Monday of the k=0 week; every test adds its own k weeks.
BASE_MONDAY = datetime.date(2034, 1, 2)

_USER_A = 93720
_USER_B = 93721
_USER_C = 93722

_NOW = datetime.datetime(2034, 6, 1, 12, 0, tzinfo=datetime.UTC)


def _week(k: int) -> datetime.date:
    return BASE_MONDAY + datetime.timedelta(weeks=k)


def _standing(
    board: LeaderboardBoardKind,
    user_id: int,
    *,
    rank: int,
    value: int,
    medal: Medal | None,
) -> NewStanding:
    return NewStanding(
        board=board,
        user_id=user_id,
        display_name=f"u{user_id}",
        final_rank=rank,
        value=value,
        puzzles=20,
        medal=medal,
    )


async def _seed_week(db: AsyncSession, k: int, rows: list[NewStanding]) -> datetime.date:
    """Claim the week's marker, then insert its standings; return the Monday."""
    week = _week(k)
    assert await claim_week(db, week_start=week)
    await insert_standings(db, week_start=week, rows=rows)
    return week


async def _celebrated_at(
    db: AsyncSession, week: datetime.date, board: str, user_id: int
) -> datetime.datetime | None:
    result = await db.execute(
        select(TrainWeeklyStanding.celebrated_at).where(
            TrainWeeklyStanding.week_start == week,
            TrainWeeklyStanding.board == board,
            TrainWeeklyStanding.user_id == user_id,
        )
    )
    return result.scalar_one()


@pytest.mark.asyncio
async def test_fetch_unclaimed_orders_newest_week_first_and_flags_shared(
    db_session: AsyncSession,
) -> None:
    """D-11 (k=20, 21): newest week first, Points before Accuracy, shared only for the same medal."""
    await ensure_test_user(db_session, _USER_A)
    await ensure_test_user(db_session, _USER_B)
    older = await _seed_week(
        db_session,
        20,
        [
            _standing("points", _USER_A, rank=1, value=9, medal=Medal.GOLD),
            _standing("points", _USER_B, rank=1, value=9, medal=Medal.GOLD),
            _standing("accuracy", _USER_A, rank=1, value=80, medal=Medal.GOLD),
            # A different medal on the same board and week is not a tie with A's gold.
            _standing("accuracy", _USER_B, rank=2, value=70, medal=Medal.SILVER),
        ],
    )
    newer = await _seed_week(
        db_session,
        21,
        [
            _standing("points", _USER_B, rank=1, value=12, medal=Medal.GOLD),
            _standing("points", _USER_A, rank=2, value=6, medal=Medal.SILVER),
            _standing("accuracy", _USER_A, rank=3, value=60, medal=Medal.BRONZE),
        ],
    )

    rows = await fetch_unclaimed(db_session, user_id=_USER_A, limit=10)

    assert rows == [
        UnclaimedRow(newer, "points", Medal.SILVER, 6, False),
        UnclaimedRow(newer, "accuracy", Medal.BRONZE, 60, False),
        UnclaimedRow(older, "points", Medal.GOLD, 9, True),
        UnclaimedRow(older, "accuracy", Medal.GOLD, 80, False),
    ]


@pytest.mark.asyncio
async def test_fetch_unclaimed_skips_celebrated_non_medal_and_foreign_rows(
    db_session: AsyncSession,
) -> None:
    """Filters (k=22): celebrated and no-medal rows are skipped; another user's rows never leak."""
    await ensure_test_user(db_session, _USER_A)
    await ensure_test_user(db_session, _USER_B)
    week = await _seed_week(
        db_session,
        22,
        [
            _standing("points", _USER_A, rank=1, value=9, medal=Medal.GOLD),
            _standing("accuracy", _USER_A, rank=4, value=50, medal=None),
            _standing("points", _USER_B, rank=1, value=9, medal=Medal.GOLD),
        ],
    )
    await db_session.execute(
        update(TrainWeeklyStanding)
        .where(TrainWeeklyStanding.user_id == _USER_A, TrainWeeklyStanding.board == "points")
        .values(celebrated_at=_NOW)
    )

    assert await fetch_unclaimed(db_session, user_id=_USER_A, limit=10) == []
    # B's list is B's own row only; the tie with A's already-celebrated gold still counts.
    assert await fetch_unclaimed(db_session, user_id=_USER_B, limit=10) == [
        UnclaimedRow(week, "points", Medal.GOLD, 9, True)
    ]


@pytest.mark.asyncio
async def test_fetch_unclaimed_respects_the_limit(db_session: AsyncSession) -> None:
    """Limit (k=23, 24, 25): at most `limit` rows, newest weeks kept."""
    await ensure_test_user(db_session, _USER_A)
    weeks = [
        await _seed_week(
            db_session, k, [_standing("points", _USER_A, rank=1, value=k, medal=Medal.GOLD)]
        )
        for k in (23, 24, 25)
    ]

    rows = await fetch_unclaimed(db_session, user_id=_USER_A, limit=2)

    assert [r.week_start for r in rows] == [weeks[2], weeks[1]]


@pytest.mark.asyncio
async def test_mark_celebrated_is_scoped_to_the_caller_and_idempotent(
    db_session: AsyncSession,
) -> None:
    """Claim (k=26): caller-only, a second call changes nothing, empty keys issue no write."""
    await ensure_test_user(db_session, _USER_A)
    await ensure_test_user(db_session, _USER_B)
    week = await _seed_week(
        db_session,
        26,
        [
            _standing("points", _USER_A, rank=1, value=9, medal=Medal.GOLD),
            _standing("points", _USER_B, rank=1, value=9, medal=Medal.GOLD),
        ],
    )
    key: tuple[datetime.date, LeaderboardBoardKind] = (week, "points")
    later = _NOW + datetime.timedelta(hours=1)

    assert await mark_celebrated(db_session, user_id=_USER_A, keys=[], now_utc=_NOW) == 0
    first = await mark_celebrated(db_session, user_id=_USER_A, keys=[key], now_utc=_NOW)
    second = await mark_celebrated(db_session, user_id=_USER_A, keys=[key], now_utc=later)

    assert (first, second) == (1, 0)
    assert await _celebrated_at(db_session, week, "points", _USER_A) == _NOW  # first stamp kept
    assert (
        await _celebrated_at(db_session, week, "points", _USER_B) is None
    )  # foreign row untouched


@pytest.mark.asyncio
async def test_tally_rows_group_by_board_user_and_medal(db_session: AsyncSession) -> None:
    """Tally (k=27, 28): grouped per board, user and medal; no-medal, celebrated and foreign rows."""
    for user_id in (_USER_A, _USER_B, _USER_C):
        await ensure_test_user(db_session, user_id)
    week_a = await _seed_week(
        db_session,
        27,
        [
            _standing("points", _USER_A, rank=1, value=9, medal=Medal.GOLD),
            _standing("points", _USER_B, rank=2, value=6, medal=Medal.SILVER),
            _standing("points", _USER_C, rank=3, value=3, medal=Medal.BRONZE),  # not asked for
            _standing("accuracy", _USER_B, rank=4, value=50, medal=None),  # never counted
        ],
    )
    await _seed_week(
        db_session,
        28,
        [
            _standing("points", _USER_A, rank=1, value=12, medal=Medal.GOLD),
            _standing("accuracy", _USER_A, rank=3, value=60, medal=Medal.BRONZE),
        ],
    )
    # Celebrated medals still count towards the lifetime tally.
    await db_session.execute(
        update(TrainWeeklyStanding)
        .where(TrainWeeklyStanding.week_start == week_a, TrainWeeklyStanding.user_id == _USER_A)
        .values(celebrated_at=_NOW)
    )

    rows = await fetch_medal_tallies(db_session, user_ids=[_USER_A, _USER_B])

    assert sorted(rows, key=lambda r: (r.board, r.user_id, int(r.medal))) == [
        TallyCount("accuracy", _USER_A, Medal.BRONZE, 1),
        TallyCount("points", _USER_A, Medal.GOLD, 2),
        TallyCount("points", _USER_B, Medal.SILVER, 1),
    ]
    assert await fetch_medal_tallies(db_session, user_ids=[]) == []
