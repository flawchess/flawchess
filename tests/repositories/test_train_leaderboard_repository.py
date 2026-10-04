"""Tests for app.repositories.train_leaderboard_repository (Phase 230, plan 02).

Real-row checks of the weekly aggregate and the caller-scoped session contribution,
on the rollback-scoped ``db_session`` fixture (no committed rows leak).

User ids 93600-93619 are reserved for this module (others in use: 92400-92650,
93100-93400, 99120+).

Isolation rule: the aggregate is global, so every test owns an ISO week counted from
Monday 2031-01-06 plus k weeks, and a test whose deliberately out-of-window rows land
in a neighbouring week owns that week too. A k is never reused in this module.

k table:
- k=0  test_contribution_returns_the_callers_in_window_session_totals
- k=1  owned by the contribution test (its out-of-window solve)
- k=2  test_points_follow_the_guess_and_tier_scoring_including_legacy_null_tier
- k=3  test_unsolved_rows_are_not_counted
- k=4  test_filler_solves_count_on_points_but_not_in_non_filler_totals
- k=5  owned by the window test (its week_start minus 1 microsecond row)
- k=6  test_window_is_half_open_on_solved_at
- k=7  owned by the window test (its week_end row)
- k=8  test_deadline_splits_one_session_across_two_weeks (the ending week)
- k=9  owned by the deadline test (the new week)
- k=10 test_flags_and_usernames_come_through_on_the_aggregate
"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drill_session import DrillSession
from app.models.drill_solve import DrillMoveQuality, DrillSolve, DrillSource
from app.models.user import User
from app.repositories.train_leaderboard_repository import (
    SolveTotals,
    WeeklyAggregate,
    fetch_session_contribution,
    fetch_week_aggregates,
)
from tests.conftest import ensure_test_user

UTC = datetime.UTC

# Monday of the k=0 week; every test adds its own k weeks.
BASE_MONDAY = datetime.datetime(2031, 1, 6, tzinfo=UTC)

_USER_A = 93600
_USER_B = 93601
_USER_C = 93602

Solve = tuple[datetime.datetime | None, bool, DrillMoveQuality | None, DrillSource]


def _week(k: int) -> tuple[datetime.datetime, datetime.datetime]:
    start = BASE_MONDAY + datetime.timedelta(weeks=k)
    return start, start + datetime.timedelta(weeks=1)


async def _seed_session(
    db: AsyncSession,
    user_id: int,
    solves: list[Solve],
) -> int:
    """Insert one completed session with one solved row per tuple; return its id."""
    first = solves[0][0]
    day = first.date() if first is not None else BASE_MONDAY.date()
    drill_session = DrillSession(
        user_id=user_id,
        session_date=day,
        status="completed",
        puzzle_count=len(solves),
        expires_on=day + datetime.timedelta(days=1),
    )
    db.add(drill_session)
    await db.flush()
    for position, (solved_at, correct_guess, quality, source) in enumerate(solves):
        db.add(
            DrillSolve(
                session_id=drill_session.id,
                position=position,
                user_id=user_id,
                game_id=None,
                ply=0,
                source=int(source),
                sharp_puzzle_id=f"lbr{position}" if source == DrillSource.SHARP_FILLER else None,
                correct_guess=correct_guess,
                correct_move=quality != DrillMoveQuality.WRONG,
                move_quality=None if quality is None else int(quality),
                solved_at=solved_at,
            )
        )
    await db.flush()
    return drill_session.id


@pytest.mark.asyncio
async def test_contribution_returns_the_callers_in_window_session_totals(
    db_session: AsyncSession,
) -> None:
    """Contribution (k=0, owning k=1): own session in window, foreign id inert, week 1 excluded."""
    await ensure_test_user(db_session, _USER_A)
    await ensure_test_user(db_session, _USER_B)
    start, end = _week(0)
    session_a = await _seed_session(
        db_session,
        _USER_A,
        [
            (start + datetime.timedelta(hours=1), True, DrillMoveQuality.GOOD, DrillSource.SR_ITEM),
            (
                start + datetime.timedelta(hours=2),
                False,
                DrillMoveQuality.GOOD,
                DrillSource.SHARP_FILLER,
            ),
            # Same session, but solved in week 1: outside this week's window.
            (end + datetime.timedelta(hours=1), True, DrillMoveQuality.GOOD, DrillSource.SR_ITEM),
        ],
    )

    own = await fetch_session_contribution(
        db_session, user_id=_USER_A, session_id=session_a, week_start=start, week_end=end
    )
    foreign = await fetch_session_contribution(
        db_session, user_id=_USER_B, session_id=session_a, week_start=start, week_end=end
    )
    next_week = await fetch_session_contribution(
        db_session, user_id=_USER_A, session_id=session_a, week_start=end, week_end=_week(1)[1]
    )

    # 3 points (True, GOOD) + 2 points (False, GOOD, filler): 5 points, 2 puzzles, of
    # which only the SR solve is non-filler.
    assert own == SolveTotals(points=5, puzzles=2, nf_points=3, nf_puzzles=1)
    # Another user's session id contributes nothing (IDOR guard).
    assert foreign == SolveTotals(0, 0, 0, 0)
    # The week-1 solve belongs to week 1 only.
    assert next_week == SolveTotals(points=3, puzzles=1, nf_points=3, nf_puzzles=1)


async def _aggregates_for(db: AsyncSession, k: int, *user_ids: int) -> dict[int, WeeklyAggregate]:
    """The week-k aggregates of the given users, keyed by user id."""
    start, end = _week(k)
    rows = await fetch_week_aggregates(db, week_start=start, week_end=end)
    return {row.user_id: row for row in rows if row.user_id in user_ids}


@pytest.mark.asyncio
async def test_points_follow_the_guess_and_tier_scoring_including_legacy_null_tier(
    db_session: AsyncSession,
) -> None:
    """Points (k=2): D-01 on real rows, a NULL legacy tier scores only the guess point."""
    await ensure_test_user(db_session, _USER_A)
    at = _week(2)[0] + datetime.timedelta(hours=1)
    sr = DrillSource.SR_ITEM
    await _seed_session(
        db_session,
        _USER_A,
        [
            (at, True, DrillMoveQuality.GOOD, sr),  # 3
            (at, False, DrillMoveQuality.GOOD, sr),  # 2
            (at, True, DrillMoveQuality.INACCURACY, sr),  # 2
            (at, True, DrillMoveQuality.WRONG, sr),  # 1
            (at, False, DrillMoveQuality.WRONG, sr),  # 0
            (at, True, None, sr),  # legacy: 1
        ],
    )

    aggregates = await _aggregates_for(db_session, 2, _USER_A)

    assert aggregates[_USER_A].totals == SolveTotals(points=9, puzzles=6, nf_points=9, nf_puzzles=6)


@pytest.mark.asyncio
async def test_unsolved_rows_are_not_counted(db_session: AsyncSession) -> None:
    """Unsolved (k=3): rows with solved_at NULL never reach the aggregate."""
    await ensure_test_user(db_session, _USER_A)
    at = _week(3)[0] + datetime.timedelta(hours=1)
    sr = DrillSource.SR_ITEM
    await _seed_session(
        db_session,
        _USER_A,
        [
            (at, True, DrillMoveQuality.GOOD, sr),
            (None, False, DrillMoveQuality.GOOD, sr),
            (None, True, DrillMoveQuality.GOOD, sr),
        ],
    )

    aggregates = await _aggregates_for(db_session, 3, _USER_A)

    assert aggregates[_USER_A].totals == SolveTotals(points=3, puzzles=1, nf_points=3, nf_puzzles=1)


@pytest.mark.asyncio
async def test_filler_solves_count_on_points_but_not_in_non_filler_totals(
    db_session: AsyncSession,
) -> None:
    """Filler (k=4): SHARP_FILLER adds to points and puzzles, not to nf_points / nf_puzzles."""
    await ensure_test_user(db_session, _USER_A)
    at = _week(4)[0] + datetime.timedelta(hours=1)
    await _seed_session(
        db_session,
        _USER_A,
        [
            (at, True, DrillMoveQuality.GOOD, DrillSource.SR_ITEM),
            (at, True, DrillMoveQuality.GOOD, DrillSource.SHARP_FILLER),
            (at, True, DrillMoveQuality.GOOD, DrillSource.SHARP_FILLER),
        ],
    )

    aggregates = await _aggregates_for(db_session, 4, _USER_A)

    assert aggregates[_USER_A].totals == SolveTotals(points=9, puzzles=3, nf_points=3, nf_puzzles=1)


@pytest.mark.asyncio
async def test_window_is_half_open_on_solved_at(db_session: AsyncSession) -> None:
    """Window (k=6, owning k=5 and k=7): week_start in, week_start - 1us and week_end out."""
    await ensure_test_user(db_session, _USER_A)
    start, end = _week(6)
    good = DrillMoveQuality.GOOD
    sr = DrillSource.SR_ITEM
    await _seed_session(
        db_session,
        _USER_A,
        [
            (start, True, good, sr),
            (start - datetime.timedelta(microseconds=1), True, good, sr),
            (end, True, good, sr),
        ],
    )

    aggregates = await _aggregates_for(db_session, 6, _USER_A)

    assert aggregates[_USER_A].totals == SolveTotals(points=3, puzzles=1, nf_points=3, nf_puzzles=1)


@pytest.mark.asyncio
async def test_deadline_splits_one_session_across_two_weeks(db_session: AsyncSession) -> None:
    """Deadline (k=8 and k=9): a session over Sunday 24:00 UTC counts one solve per week."""
    await ensure_test_user(db_session, _USER_A)
    sunday_late = _week(9)[0] - datetime.timedelta(minutes=1)  # Sunday 23:59 UTC of week 8
    monday_early = _week(9)[0] + datetime.timedelta(minutes=1)  # Monday 00:01 UTC of week 9
    good = DrillMoveQuality.GOOD
    sr = DrillSource.SR_ITEM
    await _seed_session(
        db_session, _USER_A, [(sunday_late, True, good, sr), (monday_early, True, good, sr)]
    )

    ending = await _aggregates_for(db_session, 8, _USER_A)
    starting = await _aggregates_for(db_session, 9, _USER_A)

    one_solve = SolveTotals(points=3, puzzles=1, nf_points=3, nf_puzzles=1)
    assert ending[_USER_A].totals == one_solve
    assert starting[_USER_A].totals == one_solve


@pytest.mark.asyncio
async def test_flags_and_usernames_come_through_on_the_aggregate(
    db_session: AsyncSession,
) -> None:
    """Flags (k=10): is_guest, leaderboard_hidden and both usernames reach the aggregate."""
    await ensure_test_user(db_session, _USER_A)
    await ensure_test_user(db_session, _USER_B)
    await ensure_test_user(db_session, _USER_C)
    user_a = await db_session.get(User, _USER_A)
    user_b = await db_session.get(User, _USER_B)
    assert user_a is not None and user_b is not None
    user_a.is_guest = True
    user_a.lichess_username = "flags_li"
    user_b.leaderboard_hidden = True
    user_b.chess_com_username = "flags_cc"
    await db_session.flush()
    at = _week(10)[0] + datetime.timedelta(hours=1)
    one: list[Solve] = [(at, True, DrillMoveQuality.GOOD, DrillSource.SR_ITEM)]
    for user_id in (_USER_A, _USER_B, _USER_C):
        await _seed_session(db_session, user_id, one)

    aggregates = await _aggregates_for(db_session, 10, _USER_A, _USER_B, _USER_C)

    guest, hidden, plain = aggregates[_USER_A], aggregates[_USER_B], aggregates[_USER_C]
    assert (guest.is_guest, guest.leaderboard_hidden, guest.lichess_username) == (
        True,
        False,
        "flags_li",
    )
    assert (hidden.is_guest, hidden.leaderboard_hidden, hidden.chess_com_username) == (
        False,
        True,
        "flags_cc",
    )
    assert (plain.is_guest, plain.leaderboard_hidden) == (False, False)
    assert plain.lichess_username is None and plain.chess_com_username is None
