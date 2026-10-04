"""Weekly leaderboard medal snapshot reads and writes (Phase 231).

Finalization claims a week through the marker table, writes that week's standings,
and the board reads the previous week's podium rows back. Ranking, masking and
medal rules live in `app.services.train_leaderboard`; this module is SQL only.

Selects columns only, never the User entity (oauth_accounts is lazy="joined").
Sequential awaits only: never run concurrent queries on one AsyncSession
(root CLAUDE.md constraint).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import case, exists, false, func, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.train_weekly_standing import Medal, TrainWeeklyFinalization, TrainWeeklyStanding
from app.models.user import User
from app.schemas.train import LeaderboardBoardKind

_BOARD_BY_TEXT: dict[str, LeaderboardBoardKind] = {"points": "points", "accuracy": "accuracy"}


@dataclass(frozen=True)
class NewStanding:
    """One standings row to insert; the week comes from the call."""

    board: LeaderboardBoardKind
    user_id: int
    display_name: str
    final_rank: int
    value: int
    puzzles: int
    medal: Medal | None


@dataclass(frozen=True)
class StandingRow:
    """One previous-week row as read back for the podium and the viewer's own line."""

    board: LeaderboardBoardKind
    user_id: int | None  # None after account deletion
    display_name: str
    final_rank: int
    puzzles: int
    medal: Medal | None
    leaderboard_hidden: bool  # the user's CURRENT flag; False when user_id is None


@dataclass(frozen=True)
class UnclaimedRow:
    """One medal the caller has not celebrated yet (no row id, no user id)."""

    week_start: date
    board: LeaderboardBoardKind
    medal: Medal
    value: int
    shared: bool  # another row of the same week, board and medal exists (a tie)


@dataclass(frozen=True)
class TallyCount:
    """How many medals of one kind a user holds on one board (no row id)."""

    board: LeaderboardBoardKind
    user_id: int
    medal: Medal
    count: int


async def fetch_finalized_weeks(session: AsyncSession, *, since: date) -> set[date]:
    """Finalized week Mondays from `since` on (the fast path: one tiny SELECT)."""
    result = await session.execute(
        select(TrainWeeklyFinalization.week_start).where(
            TrainWeeklyFinalization.week_start >= since
        )
    )
    return {row[0] for row in result.all()}


async def claim_week(session: AsyncSession, *, week_start: date) -> bool:
    """Insert the week's marker; True when this call claimed it.

    A concurrent claimer blocks on the primary key until the first transaction
    commits and then gets no row, so exactly one finalizer does the work per week.
    If the first transaction aborts, the blocked insert succeeds and takes over.
    """
    stmt = (
        pg_insert(TrainWeeklyFinalization)
        .values(week_start=week_start)
        .on_conflict_do_nothing(index_elements=["week_start"])
        .returning(TrainWeeklyFinalization.week_start)
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def insert_standings(
    session: AsyncSession, *, week_start: date, rows: Sequence[NewStanding]
) -> None:
    """Insert a week's standings; the unique key makes a repeat a no-op."""
    if not rows:
        return
    stmt = (
        pg_insert(TrainWeeklyStanding)
        .values(
            [
                {
                    "week_start": week_start,
                    "board": row.board,
                    "user_id": row.user_id,
                    "display_name": row.display_name,
                    "final_rank": row.final_rank,
                    "value": row.value,
                    "puzzles": row.puzzles,
                    "medal": int(row.medal) if row.medal is not None else None,
                }
                for row in rows
            ]
        )
        .on_conflict_do_nothing(constraint="uq_train_weekly_standings_week_board_user")
    )
    await session.execute(stmt)


async def fetch_last_week_rows(
    session: AsyncSession, *, week_start: date, viewer_id: int
) -> list[StandingRow]:
    """Medal rows of one week plus the viewer's own rows (any medal state).

    LEFT JOIN users so a deleted account (user_id NULL) still reads back. The
    viewer's own rows are included so the "You finished #N" line can be built.
    """
    stmt = (
        select(
            TrainWeeklyStanding.board,
            TrainWeeklyStanding.user_id,
            TrainWeeklyStanding.display_name,
            TrainWeeklyStanding.final_rank,
            TrainWeeklyStanding.puzzles,
            TrainWeeklyStanding.medal,
            func.coalesce(User.leaderboard_hidden, false()),
        )
        .outerjoin(User, User.id == TrainWeeklyStanding.user_id)
        .where(
            TrainWeeklyStanding.week_start == week_start,
            (TrainWeeklyStanding.medal.is_not(None)) | (TrainWeeklyStanding.user_id == viewer_id),
        )
    )
    result = await session.execute(stmt)
    return [
        StandingRow(
            board=_BOARD_BY_TEXT[row[0]],  # the CHECK constraint guarantees both values
            user_id=row[1],
            display_name=row[2],
            final_rank=int(row[3]),
            puzzles=int(row[4]),
            medal=Medal(row[5]) if row[5] is not None else None,
            leaderboard_hidden=bool(row[6]),
        )
        for row in result.all()
    ]


async def fetch_unclaimed(session: AsyncSession, *, user_id: int, limit: int) -> list[UnclaimedRow]:
    """The caller's medals with `celebrated_at` NULL, newest week first, Points before Accuracy.

    Scoping by the caller's user id is the IDOR guard (T-231-10): the endpoint takes no
    user parameter, so nobody can read another user's medals. `leaderboard_hidden` is
    deliberately not consulted (D-04): a user who opted out after the week still sees
    and claims their own medals. `shared` is true when another row of the same week,
    board and medal exists, i.e. the medal was tied.
    """
    other = aliased(TrainWeeklyStanding)
    shared = exists().where(
        other.week_start == TrainWeeklyStanding.week_start,
        other.board == TrainWeeklyStanding.board,
        other.medal == TrainWeeklyStanding.medal,
        other.id != TrainWeeklyStanding.id,
    )
    # Alphabetical order would put 'accuracy' first; the Points board leads (D-11).
    board_order = case((TrainWeeklyStanding.board == "points", 0), else_=1)
    stmt = (
        select(
            TrainWeeklyStanding.week_start,
            TrainWeeklyStanding.board,
            TrainWeeklyStanding.medal,
            TrainWeeklyStanding.value,
            shared,
        )
        .where(
            TrainWeeklyStanding.user_id == user_id,
            TrainWeeklyStanding.medal.is_not(None),
            TrainWeeklyStanding.celebrated_at.is_(None),
        )
        .order_by(TrainWeeklyStanding.week_start.desc(), board_order)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [
        UnclaimedRow(
            week_start=row[0],
            board=_BOARD_BY_TEXT[row[1]],  # the CHECK constraint guarantees both values
            medal=Medal(row[2]),
            value=int(row[3]),
            shared=bool(row[4]),
        )
        for row in result.all()
    ]


async def mark_celebrated(
    session: AsyncSession,
    *,
    user_id: int,
    keys: Sequence[tuple[date, LeaderboardBoardKind]],
    now_utc: datetime,
) -> int:
    """Stamp `celebrated_at` on the caller's own unclaimed medals among `keys`.

    The WHERE clause is the IDOR guard (T-231-09): rows are matched by the caller's
    user id AND the posted (week_start, board) pairs, so a foreign or unknown key
    matches nothing. `celebrated_at IS NULL` makes a replay a no-op and keeps the
    first stamp (T-231-13). Only the posted keys are claimed, never "all unclaimed".
    Returns the number of rows stamped; an empty `keys` issues no SQL.
    """
    if not keys:
        return 0
    result = await session.execute(
        update(TrainWeeklyStanding)
        .where(
            TrainWeeklyStanding.user_id == user_id,
            TrainWeeklyStanding.medal.is_not(None),
            TrainWeeklyStanding.celebrated_at.is_(None),
            tuple_(TrainWeeklyStanding.week_start, TrainWeeklyStanding.board).in_(list(keys)),
        )
        .values(celebrated_at=now_utc)
    )
    return int(result.rowcount)  # ty: ignore[unresolved-attribute]  # SQLAlchemy DML result carries rowcount


async def fetch_medal_tallies(
    session: AsyncSession, *, user_ids: Sequence[int]
) -> list[TallyCount]:
    """Lifetime medal counts per (board, user, medal) for the given users, one grouped query.

    The caller passes only ids already visible to the viewer (T-231-12), and nothing but
    counts leaves the service. Celebrated medals count too. The user_id index serves the
    IN filter. An empty `user_ids` issues no SQL.
    """
    if not user_ids:
        return []
    stmt = (
        select(
            TrainWeeklyStanding.board,
            TrainWeeklyStanding.user_id,
            TrainWeeklyStanding.medal,
            func.count(),
        )
        .where(
            TrainWeeklyStanding.user_id.in_(list(user_ids)),
            TrainWeeklyStanding.medal.is_not(None),
        )
        .group_by(TrainWeeklyStanding.board, TrainWeeklyStanding.user_id, TrainWeeklyStanding.medal)
    )
    result = await session.execute(stmt)
    return [
        TallyCount(
            board=_BOARD_BY_TEXT[row[0]],  # the CHECK constraint guarantees both values
            user_id=int(row[1]),
            medal=Medal(row[2]),
            count=int(row[3]),
        )
        for row in result.all()
    ]


__all__ = [
    "NewStanding",
    "StandingRow",
    "TallyCount",
    "UnclaimedRow",
    "claim_week",
    "fetch_finalized_weeks",
    "fetch_last_week_rows",
    "fetch_medal_tallies",
    "fetch_unclaimed",
    "insert_standings",
    "mark_celebrated",
]
