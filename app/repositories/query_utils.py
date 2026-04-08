"""Shared query utilities for repository filter operations."""

import datetime
from collections.abc import Sequence
from typing import Any, Literal

from sqlalchemy import case

from app.models.game import Game


def apply_game_filters(
    stmt: Any,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    color: str | None = None,
    *,
    opponent_strength: Literal["any", "stronger", "similar", "weaker"] = "any",
    elo_threshold: int = 100,
) -> Any:
    """Apply standard game filter WHERE clauses to a SELECT statement.

    Args:
        stmt: The base SELECT statement to add filters to.
        time_control: Filter by time control buckets (bullet, blitz, rapid, classical).
        platform: Filter by platform (chess.com, lichess).
        rated: Filter by rated/unrated. None = no filter.
        opponent_type: "human", "bot", or "all".
        recency_cutoff: Only include games played after this datetime. None = no filter.
        color: Filter by user's piece color ("white"/"black"). None = no color filter
               (used by endgame and stats repos where color is not applicable).
        opponent_strength: Filter by relative opponent strength: "any", "stronger",
                           "similar", or "weaker". Games with missing ratings are
                           excluded when any non-"any" option is selected.
        elo_threshold: Rating difference threshold for opponent_strength filter (default 100).

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
    if recency_cutoff is not None:
        stmt = stmt.where(Game.played_at >= recency_cutoff)
    if color is not None:
        stmt = stmt.where(Game.user_color == color)
    if opponent_strength != "any":
        user_rating = case(
            (Game.user_color == "white", Game.white_rating),
            else_=Game.black_rating,
        )
        opp_rating = case(
            (Game.user_color == "white", Game.black_rating),
            else_=Game.white_rating,
        )
        # Exclude games with missing ratings when filtering by opponent strength
        stmt = stmt.where(Game.white_rating.isnot(None), Game.black_rating.isnot(None))
        if opponent_strength == "stronger":
            stmt = stmt.where(opp_rating >= user_rating + elo_threshold)
        elif opponent_strength == "similar":
            stmt = stmt.where(
                opp_rating > user_rating - elo_threshold,
                opp_rating < user_rating + elo_threshold,
            )
        elif opponent_strength == "weaker":
            stmt = stmt.where(opp_rating <= user_rating - elo_threshold)
    return stmt
