"""ORM model for user_benchmark_percentiles table.

This is FlawChess's first new Postgres ENUM type since the 2026-04-08
enum-conversion migration. The ``benchmark_metric_enum`` mirrors the
``CdfMetricId`` Literal in ``app/services/global_percentile_cdf.py``
(4-value tight set). ``create_type=False`` means Alembic controls the
type lifecycle (see ``alembic/versions/20260524_000000_add_user_benchmark_percentiles.py``).

Phase 94.1 D-05/D-08: persistent home for canonical-slice values + percentiles.
Composite PK (user_id, metric) — exactly one row per user per metric at any time.
Recompute is UPSERT (see ``app/repositories/user_benchmark_percentiles_repository.py``).
"""

from __future__ import annotations

import datetime

from sqlalchemy import Date, DateTime, Enum as SAEnum, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base
from app.services.global_percentile_cdf import CdfMetricId

# Postgres ENUM type descriptor.
# create_type=False: Alembic owns the lifecycle; SQLAlchemy must never attempt to
# CREATE or DROP this type itself. Project precedent: app/models/game.py:20-40.
benchmark_metric_enum = SAEnum(
    "score_gap",
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
    name="benchmark_metric",
    create_type=False,
)


class UserBenchmarkPercentile(Base):
    """One canonical-slice percentile row per (user_id, metric).

    Written by Stage A (score_gap) and Stage B (3 eval-dependent metrics)
    background tasks, and by the one-shot backfill script.

    The ``percentile`` column is NULL when the user's canonical-slice game count
    is below the per-metric inclusion floor (D-06/D-10) — they have a computable
    ``value`` but no chip is shown.
    """

    __tablename__ = "user_benchmark_percentiles"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    metric: Mapped[CdfMetricId] = mapped_column(benchmark_metric_enum, primary_key=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    percentile: Mapped[float | None] = mapped_column(Float, nullable=True)
    n_games: Mapped[int] = mapped_column(Integer, nullable=False)
    cdf_snapshot: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    computed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
