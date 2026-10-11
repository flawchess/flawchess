"""Repository for the on-read ranked Endgame Stats sample (Phase 238).

Executes the canonical ranked-games SQL (``ranked_games_sql``) for one user and
one time control. The SQL composes the unchanged Stage A/B prelude
(``selected_users`` + ``recent_capped``), so the returned games are exactly the
games the persisted percentiles rank (D-07).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.query_utils import AnalyticsPlatform
from app.services.canonical_slice_sql import TimeControlBucket, ranked_games_sql


@dataclass(frozen=True)
class RankedGameRow:
    """One game of the per-TC ranked sample, with the display columns the service needs.

    ``user_elo`` is the user's rating at game time (the canonical slice requires
    both ratings non-null). ``eval_pending`` is True while the game's entry evals
    are not yet completed (D-11 "analyzing" state).
    """

    game_id: int
    played_at: datetime.datetime
    platform: AnalyticsPlatform
    time_control_str: str | None
    user_elo: int
    eval_pending: bool


async def fetch_ranked_games(
    session: AsyncSession,
    *,
    user_id: int,
    tc: TimeControlBucket,
) -> list[RankedGameRow]:
    """Return the user's ranked sample for one time control, oldest game first.

    V4 Information Disclosure mitigation: the caller MUST pass the authenticated
    user's ID (from the FastAPI-Users dependency ``current_active_user.id``);
    never accept ``user_id`` as a query parameter from the client. ``user_id`` is
    bound via ``.bindparams()`` only, never f-stringed into the SQL (V5).
    """
    result = await session.execute(text(ranked_games_sql(tc)).bindparams(user_id=user_id))
    return [
        RankedGameRow(
            game_id=int(row.game_id),
            played_at=row.played_at,
            platform=row.platform,
            time_control_str=row.time_control_str,
            user_elo=int(row.user_elo),
            eval_pending=bool(row.eval_pending),
        )
        for row in result.fetchall()
    ]
