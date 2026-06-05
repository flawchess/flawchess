"""Shared query utilities for repository filter operations."""

import datetime
from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import case

from app.models.game import Game


def apply_game_filters(
    stmt: Any,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    from_date: datetime.date | None,
    to_date: datetime.date | None,
    color: str | None = None,
    *,
    opponent_gap_min: int | None = None,
    opponent_gap_max: int | None = None,
    flaw_severity: Sequence[str] | None = None,
    user_id: int | None = None,
) -> Any:
    """Apply standard game filter WHERE clauses to a SELECT statement.

    Args:
        stmt: The base SELECT statement to add filters to.
        time_control: Filter by time control buckets (bullet, blitz, rapid, classical).
        platform: Filter by platform (chess.com, lichess).
        rated: Filter by rated/unrated. None = no filter.
        opponent_type: "human", "bot", or "all".
        from_date: Include games played on or after this date (inclusive). None = no lower bound.
        to_date: Include games played on or before this date (inclusive, shifted +1 day
                 in SQL so ``played_at < to_date + 1 day`` covers the whole day).
                 None = no upper bound.
        color: Filter by user's piece color ("white"/"black"). None = no color filter
               (used by endgame and stats repos where color is not applicable).
        opponent_gap_min: Lower bound (inclusive) on opponent_rating - user_rating.
                         None = unbounded below.
        opponent_gap_max: Upper bound (inclusive) on opponent_rating - user_rating.
                         None = unbounded above.
        flaw_severity: When set (e.g. ["blunder"] or ["mistake"]), append a
                         user-color-scoped EXISTS so only games containing >=1 of
                         the user's OWN plies at that severity (or worse) match.
                         None (default) leaves the statement unchanged — all
                         existing callers are unaffected. Requires the statement
                         to select from / correlate the Game table (LIBG-08, B1).
        user_id: The authenticated user's id — required only when flaw_severity
                         is set, to scope the EXISTS subquery's game_positions read
                         (T-106-AC). Ignored otherwise.

    Notes:
        When either gap bound is set, games with missing white/black ratings
        are excluded.

        Date boundary fuzz: ``played_at`` is a TIMESTAMPTZ column stored in UTC;
        ``from_date`` / ``to_date`` are plain DATE values without timezone. The
        comparison uses the server's session timezone (UTC in production), which
        is correct for UTC-normalised timestamps. Games close to midnight in
        non-UTC timezones may straddle the boundary by up to ~24 h — this is an
        accepted trade-off per D-16 (no client_timezone param to avoid scope creep).

    Returns:
        The statement with WHERE clauses appended.
    """
    if time_control is not None:
        stmt = stmt.where(Game.time_control_bucket.in_(time_control))
    if platform is not None:
        stmt = stmt.where(Game.platform.in_(platform))
    if rated is not None:
        stmt = stmt.where(Game.rated == rated)  # noqa: E712
    if opponent_type == "human":
        stmt = stmt.where(Game.is_computer_game == False)  # noqa: E712
    elif opponent_type == "bot":
        stmt = stmt.where(Game.is_computer_game == True)  # noqa: E712
    # D-10: apply date bounds only when set. to_date is shifted +1 day so the
    # comparison ``played_at < to_date + 1 day`` covers the full to_date day.
    if from_date is not None:
        stmt = stmt.where(Game.played_at >= from_date)
    if to_date is not None:
        stmt = stmt.where(Game.played_at < to_date + datetime.timedelta(days=1))
    if color is not None:
        stmt = stmt.where(Game.user_color == color)
    if opponent_gap_min is not None or opponent_gap_max is not None:
        user_rating = case(
            (Game.user_color == "white", Game.white_rating),
            else_=Game.black_rating,
        )
        opp_rating = case(
            (Game.user_color == "white", Game.black_rating),
            else_=Game.white_rating,
        )
        # Exclude games with missing ratings when filtering by opponent gap.
        stmt = stmt.where(Game.white_rating.isnot(None), Game.black_rating.isnot(None))
        gap = opp_rating - user_rating
        if opponent_gap_min is not None:
            stmt = stmt.where(gap >= opponent_gap_min)
        if opponent_gap_max is not None:
            stmt = stmt.where(gap <= opponent_gap_max)
    if flaw_severity:
        if user_id is None:
            raise ValueError("flaw_severity filter requires user_id for EXISTS scoping")
        # Lazy import avoids a query_utils <-> library_repository import cycle
        # (mirrors endgame_repository's in-function import pattern).
        from app.repositories.library_repository import flaw_exists_subquery
        from app.services.flaws_service import FlawSeverity

        # Callers pass validated FlawSeverity values; cast narrows Sequence[str].
        severities = cast(Sequence[FlawSeverity], flaw_severity)
        stmt = stmt.where(flaw_exists_subquery(user_id=user_id, severities=severities))
    return stmt
