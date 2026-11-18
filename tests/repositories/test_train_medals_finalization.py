"""Tests for the weekly medal snapshot repository and lazy finalizer.

Database-level proofs of the finalizer's guarantees: concurrent finalizers write one marker
and no duplicate rows, a repeat finalization is a no-op, an empty week is remembered,
the last-week read returns what the board needs, and deleting a user erases the stored
name through the trigger.

User ids 93700-93719 are reserved for this module (93720-93739 belong to the
tests/repositories/test_train_medals_repository.py module).

Isolation rule: finalization state is global, so every test owns ISO weeks counted from
Monday 2034-01-02 plus k weeks (this module k 0-19, the other module k 20-39). A k is
never reused. Every test except the concurrency test runs on the rollback-scoped
``db_session``; the concurrency test commits and cleans up after itself.

k table:
- k=0  test_claim_week_returns_true_once_then_false
- k=1  test_insert_standings_is_idempotent_on_the_unique_key
- k=2  test_fetch_finalized_weeks_filters_by_since (the excluded week)
- k=3  test_fetch_finalized_weeks_filters_by_since (the included week)
- k=4  test_fetch_last_week_rows_returns_medal_rows_and_the_viewer_row
- k=5  test_finalize_due_weeks_writes_rows_then_is_a_no_op (the finalized week)
- k=6  test_finalize_due_weeks_writes_rows_then_is_a_no_op (the "now" week)
- k=7  test_finalize_due_weeks_marks_an_empty_week (the empty week)
- k=8  test_finalize_due_weeks_marks_an_empty_week (the "now" week)
- k=9  test_deleted_user_row_has_its_display_name_erased
- k=10 test_concurrent_finalizers_write_one_marker_and_no_duplicates (the finalized week)
- k=11 test_concurrent_finalizers_write_one_marker_and_no_duplicates (the "now" week)
- test_erase_name_trigger_exists owns no week.
"""

from __future__ import annotations

import asyncio
import datetime

import pytest
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.blunder_check import (
    BlunderCheckSession,
    BlunderCheckWindow,
    WindowCase,
    WindowOutcome,
)
from app.models.drill_session import DrillSession
from app.models.drill_solve import DrillMoveQuality, DrillSolve, DrillSource
from app.models.train_weekly_standing import Medal, TrainWeeklyFinalization, TrainWeeklyStanding
from app.models.user import User
from app.repositories.train_medals_repository import (
    NewStanding,
    claim_week,
    fetch_finalized_weeks,
    fetch_last_week_rows,
    insert_standings,
)
from app.services import train_medals
from app.services.train_leaderboard import DELETED_USER_DISPLAY_NAME
from app.services.train_medals import finalize_due_weeks
from tests.conftest import ensure_test_user

UTC = datetime.UTC

# Monday of the k=0 week; every test adds its own k weeks.
BASE_MONDAY = datetime.date(2034, 1, 2)

_USER_A = 93700
_USER_B = 93701
_USER_C = 93702
_USER_D = 93703
_USER_E = 93704
_USER_CONCURRENT_A = 93710
_USER_CONCURRENT_B = 93711

_GOOD_SOLVE = (True, DrillMoveQuality.GOOD, DrillSource.SR_ITEM)


def _week(k: int) -> datetime.date:
    """Monday of this module's k-th owned week."""
    return BASE_MONDAY + datetime.timedelta(weeks=k)


def _mid_week(k: int) -> datetime.datetime:
    """Wednesday 12:00 UTC of week k: inside the week, past the previous week's grace."""
    monday = datetime.datetime.combine(_week(k), datetime.time.min, tzinfo=UTC)
    return monday + datetime.timedelta(days=2, hours=12)


async def _seed_solves(db: AsyncSession, user_id: int, week_k: int, count: int) -> None:
    """Insert one completed session with `count` solved rows inside week k (flush only)."""
    solved_at = _mid_week(week_k)
    day = solved_at.date()
    drill_session = DrillSession(
        user_id=user_id,
        session_date=day,
        status="completed",
        puzzle_count=count,
        expires_on=day + datetime.timedelta(days=1),
    )
    db.add(drill_session)
    await db.flush()
    correct_guess, quality, source = _GOOD_SOLVE
    for position in range(count):
        db.add(
            DrillSolve(
                session_id=drill_session.id,
                position=position,
                user_id=user_id,
                game_id=None,
                ply=0,
                source=int(source),
                sharp_puzzle_id=None,
                correct_guess=correct_guess,
                correct_move=True,
                move_quality=int(quality),
                solved_at=solved_at,
            )
        )
    await db.flush()


def _standing(user_id: int, rank: int, medal: Medal | None, *, name: str = "player") -> NewStanding:
    return NewStanding(
        board="points",
        user_id=user_id,
        display_name=name,
        final_rank=rank,
        value=100 - rank,
        puzzles=5,
        medal=medal,
    )


async def _count(db: AsyncSession, model: type[TrainWeeklyStanding], week: datetime.date) -> int:
    result = await db.execute(
        select(func.count()).select_from(model).where(model.week_start == week)
    )
    return int(result.scalar_one())


@pytest.mark.asyncio
async def test_claim_week_returns_true_once_then_false(db_session: AsyncSession) -> None:
    """The first claim of a Monday wins; the second claim of the same Monday loses."""
    week = _week(0)
    assert await claim_week(db_session, week_start=week) is True
    assert await claim_week(db_session, week_start=week) is False


@pytest.mark.asyncio
async def test_insert_standings_is_idempotent_on_the_unique_key(db_session: AsyncSession) -> None:
    """Inserting the same NewStanding twice leaves exactly one row."""
    week = _week(1)
    await ensure_test_user(db_session, _USER_A)
    assert await claim_week(db_session, week_start=week) is True
    row = _standing(_USER_A, 1, Medal.GOLD)
    await insert_standings(db_session, week_start=week, rows=[row])
    await insert_standings(db_session, week_start=week, rows=[row])
    assert await _count(db_session, TrainWeeklyStanding, week) == 1


@pytest.mark.asyncio
async def test_fetch_finalized_weeks_filters_by_since(db_session: AsyncSession) -> None:
    """Only markers on or after `since` come back."""
    older, newer = _week(2), _week(3)
    assert await claim_week(db_session, week_start=older) is True
    assert await claim_week(db_session, week_start=newer) is True
    assert await fetch_finalized_weeks(db_session, since=newer) >= {newer}
    assert older not in await fetch_finalized_weeks(db_session, since=newer)
    both = await fetch_finalized_weeks(db_session, since=older)
    assert {older, newer} <= both


@pytest.mark.asyncio
async def test_fetch_last_week_rows_returns_medal_rows_and_the_viewer_row(
    db_session: AsyncSession,
) -> None:
    """Medal rows plus the viewer's own non-medal row; never a stranger's non-medal row.

    Each row carries the user's CURRENT leaderboard_hidden (read live, the
    masking input): hiding the silver medallist after finalization shows up on read.
    """
    week = _week(4)
    for user_id in (_USER_A, _USER_B, _USER_C, _USER_D):
        await ensure_test_user(db_session, user_id)
    assert await claim_week(db_session, week_start=week) is True
    await insert_standings(
        db_session,
        week_start=week,
        rows=[
            _standing(_USER_A, 1, Medal.GOLD),
            _standing(_USER_B, 2, Medal.SILVER),
            _standing(_USER_C, 4, None),  # the viewer, no medal
            _standing(_USER_D, 5, None),  # a stranger, no medal
        ],
    )
    await db_session.execute(update(User).where(User.id == _USER_B).values(leaderboard_hidden=True))

    rows = await fetch_last_week_rows(db_session, week_start=week, viewer_id=_USER_C)

    by_user = {row.user_id: row for row in rows}
    assert set(by_user) == {_USER_A, _USER_B, _USER_C}
    assert by_user[_USER_A].medal == Medal.GOLD
    assert by_user[_USER_B].medal == Medal.SILVER
    assert by_user[_USER_C].medal is None
    assert by_user[_USER_A].leaderboard_hidden is False
    assert by_user[_USER_B].leaderboard_hidden is True


@pytest.mark.asyncio
async def test_finalize_due_weeks_writes_rows_then_is_a_no_op(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A closed week is frozen once with ranks and medals; a repeat call writes nothing."""
    monkeypatch.setattr(train_medals, "MEDALS_START_WEEK", _week(5))
    await ensure_test_user(db_session, _USER_A)
    await ensure_test_user(db_session, _USER_B)
    await _seed_solves(db_session, _USER_A, 5, 3)
    await _seed_solves(db_session, _USER_B, 5, 1)
    now = _mid_week(6)

    assert await finalize_due_weeks(db_session, now_utc=now) == 1

    result = await db_session.execute(
        select(
            TrainWeeklyStanding.user_id,
            TrainWeeklyStanding.board,
            TrainWeeklyStanding.final_rank,
            TrainWeeklyStanding.medal,
        )
        .where(TrainWeeklyStanding.week_start == _week(5))
        .order_by(TrainWeeklyStanding.final_rank)
    )
    assert [tuple(row) for row in result.all()] == [
        (_USER_A, "points", 1, int(Medal.GOLD)),
        (_USER_B, "points", 2, int(Medal.SILVER)),
    ]

    assert await finalize_due_weeks(db_session, now_utc=now) == 0
    assert await _count(db_session, TrainWeeklyStanding, _week(5)) == 2


@pytest.mark.asyncio
async def test_finalize_due_weeks_marks_an_empty_week(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A due week with no entrants gets a marker and no rows, and is never recomputed."""
    monkeypatch.setattr(train_medals, "MEDALS_START_WEEK", _week(7))
    now = _mid_week(8)

    assert await finalize_due_weeks(db_session, now_utc=now) == 1

    assert await _count(db_session, TrainWeeklyStanding, _week(7)) == 0
    assert _week(7) in await fetch_finalized_weeks(db_session, since=_week(7))
    assert await finalize_due_weeks(db_session, now_utc=now) == 0


@pytest.mark.asyncio
async def test_deleted_user_row_has_its_display_name_erased(db_session: AsyncSession) -> None:
    """Deleting the users row nulls user_id and the trigger rewrites the stored name.

    Also pins the migration's SQL literal to the service constant.
    """
    week = _week(9)
    await ensure_test_user(db_session, _USER_E)
    assert await claim_week(db_session, week_start=week) is True
    await insert_standings(
        db_session,
        week_start=week,
        rows=[_standing(_USER_E, 1, Medal.GOLD, name="RealName")],
    )

    await db_session.execute(delete(User).where(User.id == _USER_E))

    result = await db_session.execute(
        select(TrainWeeklyStanding.user_id, TrainWeeklyStanding.display_name).where(
            TrainWeeklyStanding.week_start == week
        )
    )
    assert [tuple(row) for row in result.all()] == [(None, DELETED_USER_DISPLAY_NAME)]


@pytest.mark.asyncio
async def test_erase_name_trigger_exists(test_engine) -> None:
    """The erasure trigger is a user trigger on train_weekly_standings (drift guard)."""
    async with test_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT count(*) FROM pg_trigger "
                "WHERE tgname = 'trg_train_weekly_standings_erase_name' AND NOT tgisinternal"
            )
        )
        assert result.scalar_one() == 1


async def _cleanup_concurrency_rows(session_maker: async_sessionmaker[AsyncSession]) -> None:
    """Remove this test's committed rows: markers (cascading standings), then users."""
    async with session_maker() as session:
        await session.execute(
            delete(TrainWeeklyFinalization).where(
                TrainWeeklyFinalization.week_start.in_([_week(10), _week(11)])
            )
        )
        await session.execute(
            delete(User).where(User.id.in_([_USER_CONCURRENT_A, _USER_CONCURRENT_B]))
        )
        await session.commit()


@pytest.mark.asyncio
async def test_concurrent_finalizers_write_one_marker_and_no_duplicates(
    test_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two finalizers racing on separate sessions: one wins the week, no duplicate rows.

    The marker's primary-key insert is the only lock: the
    second claimer blocks until the first commits, then gets no row and skips the week.
    """
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    monkeypatch.setattr(train_medals, "MEDALS_START_WEEK", _week(10))
    now = _mid_week(11)
    await _cleanup_concurrency_rows(session_maker)
    try:
        async with session_maker() as seed:
            await ensure_test_user(seed, _USER_CONCURRENT_A)
            await ensure_test_user(seed, _USER_CONCURRENT_B)
            await _seed_solves(seed, _USER_CONCURRENT_A, 10, 3)
            await _seed_solves(seed, _USER_CONCURRENT_B, 10, 1)
            await seed.commit()

        # Force the race: both finalizers read "week 10 not finalized" before either
        # claims it. Without the barrier the first coroutine can finish before the
        # second starts, and the test would pass even with no claim at all.
        both_read_finalized = asyncio.Barrier(2)
        real_fetch_finalized_weeks = train_medals.fetch_finalized_weeks

        async def fetch_then_wait(
            session: AsyncSession, *, since: datetime.date
        ) -> set[datetime.date]:
            finalized = await real_fetch_finalized_weeks(session, since=since)
            await both_read_finalized.wait()
            return finalized

        monkeypatch.setattr(train_medals, "fetch_finalized_weeks", fetch_then_wait)

        async def finalize_on_own_session() -> int:
            async with session_maker() as session:
                done = await finalize_due_weeks(session, now_utc=now)
                await session.commit()
                return done

        # Two sessions on two connections may run concurrently; root CLAUDE.md forbids
        # gather on ONE shared AsyncSession, which this test never does (the second
        # claimer blocks on the marker primary key until the first commits, then its
        # ON CONFLICT DO NOTHING returns no row).
        results = await asyncio.gather(finalize_on_own_session(), finalize_on_own_session())

        assert sorted(results) == [0, 1]
        async with session_maker() as check:
            markers = await check.execute(
                select(func.count())
                .select_from(TrainWeeklyFinalization)
                .where(TrainWeeklyFinalization.week_start == _week(10))
            )
            assert markers.scalar_one() == 1
            standings = await check.execute(
                select(TrainWeeklyStanding.board, TrainWeeklyStanding.user_id).where(
                    TrainWeeklyStanding.week_start == _week(10)
                )
            )
            rows = sorted(tuple(row) for row in standings.all())
            assert rows == [
                ("points", _USER_CONCURRENT_A),
                ("points", _USER_CONCURRENT_B),
            ]
    finally:
        await _cleanup_concurrency_rows(session_maker)


# --- blunder-check boards (Phase 251, D-14) -----------------------------------
#
# k table, blunder-check finalization tests (k 12-19 were reserved for later additions):
# - k=12 test_finalize_writes_four_boards (the finalized week)
# - k=13 test_finalize_writes_four_boards (the "now" week)
# - k=14 test_finalize_bc_score_skips_tentative (the finalized week)
# - k=15 test_finalize_bc_score_skips_tentative (the "now" week)

_BC_START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
_BC_WINDOWS_TO_QUALIFY = 18  # BLUNDER_CHECK_SCORE_QUALIFY_MIN_WINDOWS, pinned in the service tests


async def _seed_bc_windows(
    db: AsyncSession, user_id: int, week_k: int, count: int, *, scored: int, possible: int
) -> None:
    """Insert one completed blunder-check session with `count` ended windows in week k (flush only)."""
    ended_at = _mid_week(week_k)
    day = ended_at.date()
    header = BlunderCheckSession(
        user_id=user_id,
        status="completed",
        window_count=count,
        started_at=ended_at,
        completed_at=ended_at,
        session_date=day,
        expires_on=day + datetime.timedelta(days=1),
    )
    db.add(header)
    await db.flush()
    for position in range(count):
        db.add(
            BlunderCheckWindow(
                session_id=header.id,
                position=position,
                user_id=user_id,
                game_id=None,
                is_own=True,
                window_length=3,
                blunder_position=None,
                first_ply=10,
                blunder_ply=None,
                window_case=int(WindowCase.HERRING),
                start_fen=_BC_START_FEN,
                move_ucis="e2e4 e7e5 g1f3",
                lead_in_plies=0,
                points_possible=possible,
                points_scored=scored,
                outcome=int(WindowOutcome.CLEARED),
                started_at=ended_at,
                ended_at=ended_at,
            )
        )
    await db.flush()


async def _standings_by_board(
    db: AsyncSession, week: datetime.date
) -> dict[str, list[tuple[int | None, int, int | None]]]:
    """Stored rows of a week grouped by board: (user_id, final_rank, medal) in rank order."""
    result = await db.execute(
        select(
            TrainWeeklyStanding.board,
            TrainWeeklyStanding.user_id,
            TrainWeeklyStanding.final_rank,
            TrainWeeklyStanding.medal,
        )
        .where(TrainWeeklyStanding.week_start == week)
        .order_by(TrainWeeklyStanding.board, TrainWeeklyStanding.final_rank)
    )
    grouped: dict[str, list[tuple[int | None, int, int | None]]] = {}
    for board, user_id, rank, medal in result.all():
        grouped.setdefault(board, []).append((user_id, rank, medal))
    return grouped


@pytest.mark.asyncio
async def test_finalize_writes_four_boards(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A closed week with puzzle solves and ended windows freezes all four boards under one marker."""
    monkeypatch.setattr(train_medals, "MEDALS_START_WEEK", _week(12))
    await ensure_test_user(db_session, _USER_A)
    await ensure_test_user(db_session, _USER_B)
    # A qualifies on both puzzle boards (20 non-filler solves) and both blunder-check boards.
    await _seed_solves(db_session, _USER_A, 12, 20)
    await _seed_bc_windows(db_session, _USER_A, 12, _BC_WINDOWS_TO_QUALIFY, scored=3, possible=4)
    # B only plays blunder check, with more points but a lower score percent.
    await _seed_bc_windows(db_session, _USER_B, 12, _BC_WINDOWS_TO_QUALIFY, scored=4, possible=8)
    now = _mid_week(13)

    assert await finalize_due_weeks(db_session, now_utc=now) == 1

    grouped = await _standings_by_board(db_session, _week(12))
    gold, silver = int(Medal.GOLD), int(Medal.SILVER)
    assert grouped == {
        "accuracy": [(_USER_A, 1, gold)],
        "blunder_check_points": [(_USER_B, 1, gold), (_USER_A, 2, silver)],
        "blunder_check_score": [(_USER_A, 1, gold), (_USER_B, 2, silver)],
        "points": [(_USER_A, 1, gold)],
    }
    # One marker for the week, and a repeat call writes nothing more.
    assert await finalize_due_weeks(db_session, now_utc=now) == 0
    assert (
        sum(len(rows) for rows in (await _standings_by_board(db_session, _week(12))).values()) == 6
    )


@pytest.mark.asyncio
async def test_finalize_bc_score_skips_tentative(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """17 ended windows is tentative on Score %: no standing row there, but a Points row."""
    monkeypatch.setattr(train_medals, "MEDALS_START_WEEK", _week(14))
    await ensure_test_user(db_session, _USER_A)
    await ensure_test_user(db_session, _USER_B)
    await _seed_bc_windows(db_session, _USER_A, 14, _BC_WINDOWS_TO_QUALIFY, scored=2, possible=4)
    await _seed_bc_windows(
        db_session, _USER_B, 14, _BC_WINDOWS_TO_QUALIFY - 1, scored=4, possible=4
    )

    assert await finalize_due_weeks(db_session, now_utc=_mid_week(15)) == 1

    grouped = await _standings_by_board(db_session, _week(14))
    gold, silver = int(Medal.GOLD), int(Medal.SILVER)
    # B scores 100 percent but over 17 windows: unranked, no row. A is alone on Score %.
    assert grouped["blunder_check_score"] == [(_USER_A, 1, gold)]
    assert grouped["blunder_check_points"] == [(_USER_B, 1, gold), (_USER_A, 2, silver)]
