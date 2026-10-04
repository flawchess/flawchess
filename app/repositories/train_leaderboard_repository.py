"""Weekly Train leaderboard aggregate query (Phase 230).

One `GROUP BY user_id` over the week window returns a few hundred rows at most.
Ranking, slicing and visibility live in `app.services.train_leaderboard`.

Sequential awaits only: never run concurrent queries on one AsyncSession
(root CLAUDE.md constraint).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drill_solve import DrillSolve, DrillSource
from app.models.user import User
from app.services.train_score import GUESS_POINTS, MOVE_QUALITY_TIER, MOVE_TIER_POINTS


@dataclass(frozen=True)
class SolveTotals:
    """Summed points and puzzle counts, all solves and non-filler solves."""

    points: int
    puzzles: int
    nf_points: int  # non-filler (source != SHARP_FILLER)
    nf_puzzles: int


@dataclass(frozen=True)
class WeeklyAggregate:
    """One user's weekly totals plus the fields the visibility policy needs."""

    user_id: int
    totals: SolveTotals
    lichess_username: str | None
    chess_com_username: str | None
    is_guest: bool
    leaderboard_hidden: bool


# Per-row points: 1 for a correct guess plus the move tier points. The move CASE is
# built from MOVE_QUALITY_TIER / MOVE_TIER_POINTS (guarded by the parity test), not
# from the raw move_quality value. A NULL move_quality is a pre-SEED-119 legacy row
# and scores 0 move points (else branch).
_GUESS_POINTS_EXPR: ColumnElement[int] = case(
    (DrillSolve.correct_guess.is_(True), GUESS_POINTS), else_=0
)
_MOVE_POINTS_EXPR: ColumnElement[int] = case(
    *[
        (DrillSolve.move_quality == int(quality), MOVE_TIER_POINTS[tier])
        for quality, tier in MOVE_QUALITY_TIER.items()
    ],
    else_=0,
)
_POINTS_EXPR: ColumnElement[int] = _GUESS_POINTS_EXPR + _MOVE_POINTS_EXPR
_NON_FILLER: ColumnElement[bool] = DrillSolve.source != int(DrillSource.SHARP_FILLER)


async def fetch_week_aggregates(
    session: AsyncSession, *, week_start: datetime, week_end: datetime
) -> list[WeeklyAggregate]:
    """Per-user totals for solves in the half-open window [week_start, week_end).

    The range predicate also excludes unsolved rows (solved_at NULL). Selects
    columns only, never the User entity (oauth_accounts is lazy="joined").
    """
    stmt = (
        select(
            DrillSolve.user_id,
            func.coalesce(func.sum(_POINTS_EXPR), 0),
            func.count(),
            func.coalesce(func.sum(_POINTS_EXPR).filter(_NON_FILLER), 0),
            func.count().filter(_NON_FILLER),
            User.lichess_username,
            User.chess_com_username,
            User.is_guest,
            User.leaderboard_hidden,
        )
        .join(User, User.id == DrillSolve.user_id)
        .where(DrillSolve.solved_at >= week_start, DrillSolve.solved_at < week_end)
        .group_by(DrillSolve.user_id, User.id)
    )
    result = await session.execute(stmt)
    return [
        WeeklyAggregate(
            user_id=int(row[0]),
            totals=SolveTotals(
                points=int(row[1]),
                puzzles=int(row[2]),
                nf_points=int(row[3]),
                nf_puzzles=int(row[4]),
            ),
            lichess_username=row[5],
            chess_com_username=row[6],
            is_guest=bool(row[7]),
            leaderboard_hidden=bool(row[8]),
        )
        for row in result.all()
    ]


async def fetch_session_contribution(
    session: AsyncSession,
    *,
    user_id: int,
    session_id: int,
    week_start: datetime,
    week_end: datetime,
) -> SolveTotals:
    """One session's in-window totals for one user (D-12 session delta).

    Scoping by the caller's user id is the IDOR guard (T-230-04): a session id the
    caller does not own matches no rows, contributes SolveTotals(0, 0, 0, 0) and
    reveals nothing about that session. A session spanning the Sunday deadline only
    contributes its in-window solves, matching what the weekly aggregate counted.
    """
    stmt = select(
        func.coalesce(func.sum(_POINTS_EXPR), 0),
        func.count(),
        func.coalesce(func.sum(_POINTS_EXPR).filter(_NON_FILLER), 0),
        func.count().filter(_NON_FILLER),
    ).where(
        DrillSolve.user_id == user_id,
        DrillSolve.session_id == session_id,
        DrillSolve.solved_at >= week_start,
        DrillSolve.solved_at < week_end,
    )
    row = (await session.execute(stmt)).one()
    return SolveTotals(
        points=int(row[0]), puzzles=int(row[1]), nf_points=int(row[2]), nf_puzzles=int(row[3])
    )


__all__ = [
    "SolveTotals",
    "WeeklyAggregate",
    "fetch_session_contribution",
    "fetch_week_aggregates",
]
