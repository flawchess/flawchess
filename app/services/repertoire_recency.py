"""Current-repertoire cutoff shared by the Openings Stats and Insights endpoints.

An opening is "current" when it was last played within the user's most recent
``CURRENT_REPERTOIRE_RECENT_GAMES`` games of that colour OR within the last
``CURRENT_REPERTOIRE_MIN_DAYS`` days, whichever reaches further back. Everything
older is "past" (D-01). The cutoff is computed under the active sidebar filters
(D-02) and anchored on ``now_utc`` from the ``dev_now_utc`` dependency, never on
``datetime.now()`` (D-03).

Lives in its own neutral module so ``stats_service``, ``opening_insights_service``
and ``openings_service`` can share it without importing each other.
"""

import datetime
from collections.abc import Sequence
from typing import Literal, TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.stats_repository import query_nth_recent_played_at

# Window size by game count. With fewer games than this for a colour (under the
# active filters) every opening of that colour is current (D-01).
CURRENT_REPERTOIRE_RECENT_GAMES: int = 200

# Day floor on the window. Prod distribution (CONTEXT specifics, 2026-10-17): for users
# with 1000+ games per colour the last-200-games window is only ~61-68 days median and
# ~15-17 days at p10, so a pure game-count rule would call an opening played three weeks
# ago "past". The floor keeps those openings current and leaves light users unchanged.
CURRENT_REPERTOIRE_MIN_DAYS: int = 60


class CurrentCutoffs(TypedDict):
    """Per-colour cutoff; None means every opening of that colour is current."""

    white: datetime.datetime | None
    black: datetime.datetime | None


def combine_cutoff(
    nth_played_at: datetime.datetime | None, now_utc: datetime.datetime
) -> datetime.datetime | None:
    """Merge the Nth-most-recent game date with the day floor.

    ``nth_played_at`` is None when the colour has fewer than
    CURRENT_REPERTOIRE_RECENT_GAMES games under the active filters: then everything
    is current and there is no cutoff. Otherwise the cutoff is whichever of the Nth
    game date and ``now_utc - CURRENT_REPERTOIRE_MIN_DAYS`` reaches further back.
    """
    if nth_played_at is None:
        return None
    day_floor = now_utc - datetime.timedelta(days=CURRENT_REPERTOIRE_MIN_DAYS)
    return min(nth_played_at, day_floor)


def is_current(last_played_at: datetime.datetime | None, cutoff: datetime.datetime | None) -> bool:
    """True when the opening counts as current for the given cutoff.

    No cutoff or an unknown last-played date reads as current (nothing to compare).
    """
    if cutoff is None or last_played_at is None:
        return True
    return last_played_at >= cutoff


async def resolve_current_cutoff(
    session: AsyncSession,
    user_id: int,
    color: Literal["white", "black"],
    *,
    now_utc: datetime.datetime,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    opponent_gap_min: int | None,
    opponent_gap_max: int | None,
) -> datetime.datetime | None:
    """Cutoff for one colour under the active filters (None = everything current)."""
    nth_played_at = await query_nth_recent_played_at(
        session,
        user_id,
        color,
        CURRENT_REPERTOIRE_RECENT_GAMES,
        time_control=time_control,
        platform=platform,
        rated=rated,
        opponent_type=opponent_type,
        from_date=from_date,
        to_date=to_date,
        opponent_gap_min=opponent_gap_min,
        opponent_gap_max=opponent_gap_max,
    )
    return combine_cutoff(nth_played_at, now_utc)


async def resolve_current_cutoffs(
    session: AsyncSession,
    user_id: int,
    colors: Sequence[Literal["white", "black"]],
    *,
    now_utc: datetime.datetime,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    opponent_gap_min: int | None,
    opponent_gap_max: int | None,
) -> CurrentCutoffs:
    """Cutoffs for the requested colours; colours not requested map to None.

    Awaited sequentially: an AsyncSession is not safe for concurrent use.
    """
    cutoffs = CurrentCutoffs(white=None, black=None)
    for color in colors:
        cutoffs[color] = await resolve_current_cutoff(
            session,
            user_id,
            color,
            now_utc=now_utc,
            time_control=time_control,
            platform=platform,
            rated=rated,
            opponent_type=opponent_type,
            from_date=from_date,
            to_date=to_date,
            opponent_gap_min=opponent_gap_min,
            opponent_gap_max=opponent_gap_max,
        )
    return cutoffs
