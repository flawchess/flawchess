"""ORM model for user_rating_anchors table.

D-12 Reversal Amendment (2026-05-27) -- see CONTEXT.md §Amendment and
``.planning/notes/percentile-anchor-d12-reversal.md`` for the standalone
design-decision record.

The original D-12 rule (Lichess-precedence: "any Lichess games in TC =>
Lichess source") is SUPERSEDED. The new algorithm is game-weighted blended
anchor (CONTEXT §Amendment §"Schema reshape" + §"Risk profile"):

  1. For each game in the canonical slice (per-TC, recent-3000-capped,
     36-month window, status=completed, ±100 opp filter):
       - Lichess game -> use rating_at_game_time as-is (native Lichess).
       - Chess.com game (non-Daily) -> convert rating_at_game_time to
         Lichess-equivalent via the per-TC ChessGoals snapshot
         (``app/services/rating_conversion.py``).
       - Chess.com Daily -> contributes weight 0 (conversion undefined).
  2. Pool the converted chess.com ratings with the native Lichess ratings.
  3. Take the median of the pool -> that is ``anchor_rating``.

Per-game conversion (not per-user) handles within-window rating drift
naturally. ``anchor_rating`` is always Lichess-equivalent regardless of
the user's platform mix.

Tooltip-disclosure columns (CONTEXT §Amendment §"Tooltip disclosure update"):
  - ``n_chesscom_games`` / ``chesscom_median_native``: number of non-Daily
    chess.com games used and their median RAW (pre-conversion) chess.com rating.
  - ``n_lichess_games`` / ``lichess_median_native``: number of Lichess games
    used and their median native Lichess rating.
These are surfaced in the percentile-chip tooltip (D-07 bullet 4, amended) so
the user can see what the blended anchor blends.

Suppression rule (CONTEXT §Amendment §"Suppression rule"): a user with
``n_chesscom_games == 0`` AND ``n_lichess_games == 0`` has no anchor row for
that TC and the chip suppresses naturally. This is rare (chess.com-Daily-only
users) and matches existing chip-suppression behavior.

Risk profile by user type (CONTEXT §Amendment §"Risk profile"):
  - Pure-Lichess users: unchanged (no conversion in play).
  - Pure-chess.com users: nearly identical anchors (median commutes with the
    ChessGoals monotonic mapping within a single piecewise segment).
  - Mixed-platform users: anchor shifts toward the platform contributing more
    games -- the surgical fix the amendment targets.

``time_control_bucket_enum`` is cross-imported from ``app/models/game.py`` to
keep the Postgres ENUM single-source-of-truth. ``create_type=False`` on both
sides ensures Alembic (not SQLAlchemy) owns the type lifecycle.
"""

from __future__ import annotations

import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from typing import Literal

from app.models.base import Base
from app.models.game import time_control_bucket_enum


# Re-export the TC bucket type for callers that only import from this module.
TimeControlBucket = Literal["bullet", "blitz", "rapid", "classical"]


class UserRatingAnchor(Base):
    """One blended-anchor row per (user_id, time_control_bucket).

    Phase 94.4 D-12 Reversal Amendment (2026-05-27): game-weighted blended
    anchor replaces the original Lichess-precedence rule. See module docstring
    for the full algorithm description and risk profile.

    Written by Stage A at import time (Plan 10) and by the one-shot backfill
    (Plan 12). Read by the percentile chip service and the tooltip payload.

    Columns:
      user_id (PK): FK to users.id with ON DELETE CASCADE.
      time_control_bucket (PK): one of bullet/blitz/rapid/classical.
      anchor_rating: median of the pooled converted-chess.com + native-Lichess
        ratings; Lichess-equivalent regardless of the user's platform mix.
        >= MEDIAN_ANCHOR_MIN_GAMES games required; no row produced otherwise.
      n_chesscom_games: count of non-Daily chess.com games used. >= 0.
        A user with no chess.com games in this TC gets 0, not NULL.
      n_lichess_games: count of Lichess games used. >= 0.
        A user with no Lichess games in this TC gets 0, not NULL.
      chesscom_median_native: median of the user's RAW chess.com ratings in
        this TC BEFORE ChessGoals conversion. None when n_chesscom_games == 0.
        Tooltip-disclosure source (D-07 bullet 4, amendment-revised).
      lichess_median_native: median of the user's native Lichess ratings in
        this TC. None when n_lichess_games == 0. Tooltip-disclosure source.
      computed_at: server-default NOW() on insert; refreshed by UPSERT.
        Not exposed via RatingAnchorRow; readable via raw SELECT for tests.
    """

    __tablename__ = "user_rating_anchors"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    time_control_bucket: Mapped[TimeControlBucket] = mapped_column(
        time_control_bucket_enum,
        primary_key=True,
    )
    anchor_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    n_chesscom_games: Mapped[int] = mapped_column(Integer, nullable=False)
    n_lichess_games: Mapped[int] = mapped_column(Integer, nullable=False)
    chesscom_median_native: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lichess_median_native: Mapped[int | None] = mapped_column(Integer, nullable=True)
    computed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


__all__ = ["UserRatingAnchor", "TimeControlBucket"]
