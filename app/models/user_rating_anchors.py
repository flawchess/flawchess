"""ORM model for user_rating_anchors table.

Phase 94.4 D-04: per-(user, TC) median rating anchor used by the peer-relative
percentile chip lookup. Composite PK ``(user_id, time_control_bucket)`` — at
most one row per user per TC at all times. Recompute is UPSERT (see
``app/repositories/user_rating_anchors_repository.py``).

Write path (Stage A — wired in Plan 05): the per-user anchor compute service
calls ``per_user_cte_median_anchor`` (this plan, Task 5) over the user's
recent-3000-per-TC × 36-month pool, evaluates the median anchor per
``time_control_bucket``, and UPSERTs into this table. The live chip lookup
later joins ``user_rating_anchors`` to the cohort CDF artifact via
``(anchor_rating, time_control_bucket)`` to read the percentile.

Suppression semantics: no row → no anchor → chip suppresses naturally. A user
who has not yet reached the per-TC inclusion floor (``MEDIAN_ANCHOR_MIN_GAMES =
30`` games on the recent-3000 pool) produces no row for that TC, and the chip
disappears for that (user, TC) without any null-handling at the API layer.

Lichess-precedence rule (D-12): when a user has games on both platforms, the
Python wrapper in Plan 05 (``user_benchmark_percentiles_service.py``) computes
the Lichess-only median first and writes ``source_platform='lichess'`` /
``chesscom_raw_rating=NULL``. If the user has fewer than 30 Lichess games on a
TC, the wrapper falls back to chess.com, converts the raw chess.com rating to
the equivalent Lichess rating via ``app/services/chesscom_to_lichess.py``
(ChessGoals snapshot), and writes ``source_platform='chesscom'`` with the
pre-conversion rating preserved in ``chesscom_raw_rating`` so the tooltip can
disclose the conversion provenance (D-07 bullet 4). The precedence rule lives
in the Python wrapper, NOT in the SQL builder — the builder takes
``platform`` as a parameter so both call paths (Plan 04 benchmark-side + Plan
05 single-user-side) reuse the same builder.

Daily-classical suppression (RESEARCH Pitfall 11): chess.com Daily games
(``time_control_str LIKE '1/%'``) are bucketed as ``classical`` by the import
pipeline but the median-anchor builder drops them with an unconditional WHERE
clause. As a result, classical anchors may be absent for users who play only
chess.com Daily — the chip suppresses for that (user, ``classical``) cell.

``anchor_source`` Postgres ENUM has exactly two values (``lichess`` /
``chesscom``); ``create_type=False`` because Alembic owns the lifecycle (see
``alembic/versions/{TS}_add_user_rating_anchors.py``).
"""

from __future__ import annotations

import datetime
from typing import Literal

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.game import time_control_bucket_enum

# ---------------------------------------------------------------------------
# anchor_source Postgres ENUM type descriptor.
# create_type=False: Alembic owns the lifecycle; SQLAlchemy must never attempt
# to CREATE or DROP this type itself. Project precedent:
# app/models/user_benchmark_percentile.py:38-63 and app/models/game.py:20-40.
# ---------------------------------------------------------------------------

AnchorSource = Literal["lichess", "chesscom"]

anchor_source_enum = SAEnum(
    "lichess",
    "chesscom",
    name="anchor_source",
    create_type=False,
)


# Re-export the TC bucket type for callers that only import from this module.
TimeControlBucket = Literal["bullet", "blitz", "rapid", "classical"]


class UserRatingAnchor(Base):
    """One median-rating-anchor row per (user_id, time_control_bucket).

    Phase 94.4 D-04: substrate for the peer-relative percentile chip lookup.
    Written by Stage A at import time (Plan 05) and by the one-shot backfill.

    See module docstring for write path, suppression semantics,
    Lichess-precedence rule (D-12), Daily-classical suppression (RESEARCH
    Pitfall 11), and the chesscom_raw_rating tooltip-disclosure source
    (D-07 bullet 4).

    Columns:
      user_id (PK): FK to users.id with ON DELETE CASCADE.
      time_control_bucket (PK): one of bullet/blitz/rapid/classical.
      anchor_rating: median rating over the user's recent-3000-per-TC pool;
        for source_platform='chesscom' this is the POST-conversion
        (Lichess-equivalent) rating produced by app.services.chesscom_to_lichess.
      source_platform: 'lichess' wins per D-12 precedence; 'chesscom' only
        when the user has fewer than MEDIAN_ANCHOR_MIN_GAMES on Lichess for
        that TC.
      chesscom_raw_rating: nullable. Populated only when source_platform =
        'chesscom' — holds the user's pre-conversion chess.com rating so
        the tooltip can disclose conversion provenance (D-07 bullet 4).
        NULL when source_platform = 'lichess'.
      n_games: count of games used to compute the median anchor; floor is
        MEDIAN_ANCHOR_MIN_GAMES (30) per D-04 / RESEARCH Pattern 6.
      computed_at: server-default NOW() on insert; refreshed by UPSERT.
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
    source_platform: Mapped[AnchorSource] = mapped_column(
        anchor_source_enum,
        nullable=False,
    )
    chesscom_raw_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    n_games: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


__all__ = ["UserRatingAnchor", "AnchorSource", "anchor_source_enum", "TimeControlBucket"]
