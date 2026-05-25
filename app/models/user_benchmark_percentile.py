"""ORM model for user_benchmark_percentiles table.

This is FlawChess's first new Postgres ENUM type since the 2026-04-08
enum-conversion migration. The ``benchmark_metric_enum`` mirrors the
``CdfMetricId`` Literal in ``app/services/global_percentile_cdf.py``
(16-value set after Phase 94.3 widening: 4 Phase 94.x score-gap metrics
plus 12 per-(metric × TC) time-pressure entries). ``create_type=False``
means Alembic controls the type lifecycle — see
``alembic/versions/20260524_000000_add_user_benchmark_percentiles.py`` for
the initial CREATE TYPE and
``alembic/versions/20260524_170733_fd5b551f381c_extend_benchmark_metric_for_tc_pressure.py``
for the Phase 94.3 ADD VALUE extension.

Phase 94.1 D-05/D-08: persistent home for canonical-slice values + percentiles.
Composite PK (user_id, metric) — exactly one row per user per metric at any time.
Recompute is UPSERT (see ``app/repositories/user_benchmark_percentiles_repository.py``).

Phase 94.1 Plan 13 semantics (gap-closure):
  Row existence implies above-floor. Below-floor (user, metric) pairs produce
  NO row — the chip suppresses naturally via an empty fetch_for_user result.

The ``n_games`` column was added by Phase 94.2 (re-introduced after the
per-cell ``n_cells_floor`` was dropped in 94.1-13). Under the pooled-per-user
model, ``n_games`` carries per-metric semantics — see the class docstring.
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
    # Phase 94.3 per-(metric × TC) time-pressure additions (CONTEXT.md D-7).
    # Order mirrors STAGE_B_METRICS in user_benchmark_percentiles_service.py
    # and the _NEW_VALUES tuple in the 20260524_170733 migration.
    "time_pressure_score_gap_bullet",
    "time_pressure_score_gap_blitz",
    "time_pressure_score_gap_rapid",
    "time_pressure_score_gap_classical",
    "clock_gap_bullet",
    "clock_gap_blitz",
    "clock_gap_rapid",
    "clock_gap_classical",
    "net_flag_rate_bullet",
    "net_flag_rate_blitz",
    "net_flag_rate_rapid",
    "net_flag_rate_classical",
    name="benchmark_metric",
    create_type=False,
)


class UserBenchmarkPercentile(Base):
    """One canonical-slice percentile row per (user_id, metric).

    Written by Stage A (score_gap) and Stage B (3 eval-dependent metrics)
    background tasks, and by the one-shot backfill script.

    Row existence implies above-floor: if a user has zero floor-passing
    ``(elo_bucket, tc_bucket)`` cells for a metric, no row is written
    (Plan 13 gap-closure). The chip suppresses naturally when fetch_for_user
    returns an empty dict for that metric.

    Phase 94.2 (D-9-amend): the ``n_games`` column carries per-metric meaning
    under the pooled-per-user model.

    - ``score_gap`` → count of endgame games on the user's pool (the binding
      floor; paired non-endgame count is in the backfill log only, not the table).
    - ``achievable_score_gap`` → count of endgame-entry games with non-null
      ``d_i`` on the pool.
    - ``section2_score_gap_conv`` → count of spans classified into the
      conversion bucket on the pool.
    - ``section2_score_gap_parity`` → count of spans classified into the
      parity bucket on the pool.
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
