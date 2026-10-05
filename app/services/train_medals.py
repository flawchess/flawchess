"""Lazy weekly leaderboard finalization (Phase 231).

At or after a week's Sunday deadline plus `MEDALS_FINALIZE_GRACE`, the first request to
reach `finalize_due_weeks` freezes that week's public boards into
`train_weekly_standings` with explicit medals. No cron, scheduler hook or background
task: finalization is lazy, idempotent and global. The marker row
(`train_weekly_finalizations`, inserted first) is the lock and the memory: a concurrent
finalizer blocks on it and then skips the week, and a week with no eligible entrants
still gets a marker so it is never re-scanned.

Eligibility timing (accepted trade-off, review WR-02): `users.leaderboard_hidden` is read
live by `fetch_week_aggregates` when a week is finalized, i.e. on the first board or
unclaimed-medals request after the deadline plus `MEDALS_FINALIZE_GRACE`, not at the
deadline itself. With low Train traffic that gap can be hours, so a user who toggles
"Hide me from leaderboards" in between is excluded (or included) according to their
setting at finalization time, and the ranks below them shift accordingly. This was
accepted rather than adding a scheduler or background tick (unplanned scope); see the
"Weekly leaderboard medals" note in docs/production-runbook.md.

Time only ever arrives as the `now_utc` argument (the router injects it from the
`dev_now_utc` dependency), never the wall clock. The service does not commit; the
router commits so the marker and that week's rows land in one transaction.

Dev-clock caveat (Pitfall 5): shifting the dev clock past a deadline finalizes that
week permanently with whatever data it has. Dev cleanup is deleting the week from
`train_weekly_finalizations` (the FK cascades its standings rows).
"""

from __future__ import annotations

import datetime
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.train_leaderboard_repository import fetch_week_aggregates
from app.repositories.train_medals_repository import (
    NewStanding,
    claim_week,
    fetch_finalized_weeks,
    fetch_unclaimed,
    insert_standings,
    mark_celebrated,
)
from app.schemas.train import MEDAL_CLAIM_MAX_ITEMS, LeaderboardBoardKind, MedalKind
from app.services.train_leaderboard import (
    DAYS_PER_WEEK,
    MEDAL_KIND,
    final_standings,
    week_window,
)

# Locked: the first week that earns medals. Read at call time (a module global, never a
# default argument) so tests can monkeypatch it. Moved back from 2026-10-05 to 2026-09-28
# after launch so the launch week (the board went live Sunday 2026-10-04) awards medals
# too; finalization recomputes from drill_solves, so a past week finalizes exactly.
MEDALS_START_WEEK: Final = datetime.date(2026, 9, 28)
# Pitfall 1: `solved_at` is the request's start time but visibility is commit time, so a
# solve that started before the deadline can commit a moment after it. The grace keeps a
# permanent snapshot from missing it, at the cost of the podium appearing at 00:05 UTC.
MEDALS_FINALIZE_GRACE: Final = datetime.timedelta(minutes=5)

_BOARDS: Final[tuple[LeaderboardBoardKind, ...]] = ("points", "accuracy")


def due_weeks(
    now_utc: datetime.datetime, finalized: Collection[datetime.date], *, start: datetime.date
) -> list[datetime.date]:
    """Closed weeks from `start` not yet finalized, ascending (pure).

    A week is due once `now_utc >= week_end + MEDALS_FINALIZE_GRACE`. Ascending order
    in every finalizer avoids lock-order deadlocks between concurrent requests.
    """
    first_open = week_window(now_utc - MEDALS_FINALIZE_GRACE)[0].date()
    weeks: list[datetime.date] = []
    week = start
    while week < first_open:
        if week not in finalized:
            weeks.append(week)
        week += datetime.timedelta(days=DAYS_PER_WEEK)
    return weeks


async def finalize_due_weeks(session: AsyncSession, *, now_utc: datetime.datetime) -> int:
    """Finalize every due week in ascending order; return how many this call finalized."""
    start = MEDALS_START_WEEK
    finalized = await fetch_finalized_weeks(session, since=start)
    done = 0
    for week in due_weeks(now_utc, finalized, start=start):
        if not await claim_week(session, week_start=week):
            continue  # another request finalized it (PG made us wait for its commit)
        week_start = datetime.datetime.combine(week, datetime.time.min, tzinfo=datetime.UTC)
        week_end = week_start + datetime.timedelta(days=DAYS_PER_WEEK)
        aggregates = await fetch_week_aggregates(session, week_start=week_start, week_end=week_end)
        rows = [
            NewStanding(
                board=kind,
                user_id=standing.user_id,
                display_name=standing.display_name,
                final_rank=standing.final_rank,
                value=standing.value,
                puzzles=standing.puzzles,
                medal=standing.medal,
            )
            for kind in _BOARDS
            for standing in final_standings(kind, aggregates)
        ]
        await insert_standings(session, week_start=week, rows=rows)
        done += 1
    return done


@dataclass(frozen=True)
class UnclaimedMedalItem:
    """One unclaimed medal for the celebration dialog (no row id, no user id)."""

    week_start: datetime.date
    board: LeaderboardBoardKind
    medal: MedalKind
    value: int
    shared: bool


async def get_unclaimed_medals(session: AsyncSession, *, user_id: int) -> list[UnclaimedMedalItem]:
    """The caller's unclaimed medals, newest week first, capped at MEDAL_CLAIM_MAX_ITEMS.

    The cap equals the claim body's maximum, so a dialog's POST is always valid.
    """
    rows = await fetch_unclaimed(session, user_id=user_id, limit=MEDAL_CLAIM_MAX_ITEMS)
    return [
        UnclaimedMedalItem(
            week_start=row.week_start,
            board=row.board,
            medal=MEDAL_KIND[row.medal],
            value=row.value,
            shared=row.shared,
        )
        for row in rows
    ]


async def claim_medals(
    session: AsyncSession,
    *,
    user_id: int,
    keys: Sequence[tuple[datetime.date, LeaderboardBoardKind]],
    now_utc: datetime.datetime,
) -> int:
    """Mark the caller's own medals among `keys` as celebrated; return how many changed.

    `now_utc` comes from the router's dev_now_utc dependency, never the wall clock.
    The service does not commit; the router commits.
    """
    return await mark_celebrated(session, user_id=user_id, keys=keys, now_utc=now_utc)
