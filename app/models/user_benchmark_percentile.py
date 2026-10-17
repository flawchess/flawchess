"""ORM model for user_benchmark_percentiles table.

The ``benchmark_metric_enum`` mirrors the ``CdfMetricId`` Literal in
``app/services/global_percentile_cdf.py``. The ENUM holds the 11 CdfMetricId
family names (per-TC dimensionality lives in the ``time_control_bucket`` PK
column, not in the ENUM) plus 12 legacy TC-suffixed rate values (3 rate-metric
families × 4 TCs), 23 values in total. The 12 TC-suffixed values remain for
forward compatibility. The bare family names (conversion_rate, parity_rate,
recovery_rate) are what the upsert_percentile write path stores, with
time_control_bucket providing the per-TC dimensionality (PK column, not ENUM
suffix).

``create_type=False`` means Alembic controls the ENUM lifecycle — see
``alembic/versions/20260526_222651_1945ae56aa20_reshape_user_benchmark_percentiles.py``
for the destructive reshape (drop/recreate of both the table and the ENUM).
Earlier ENUM/table history: the original
``20260524_000000_add_user_benchmark_percentiles.py`` created the table and
ENUM (4-value); ``20260524_170733_fd5b551f381c_extend_benchmark_metric_for_tc_pressure.py``
extended to 16 values (now superseded by the destructive reshape).

Composite PK is (user_id, metric, time_control_bucket).
At most one row per user per metric per TC bucket.

Row existence implies above-floor. Below-floor (user, metric, tc) triples
produce NO row — the chip suppresses naturally via an empty
fetch_for_user[metric][tc] entry.

The ``n_games`` column carries per-(metric × TC) semantics under the
peer-relative framing — see the class docstring.
"""

from __future__ import annotations

import datetime

from sqlalchemy import Date, DateTime, Enum as SAEnum, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.game import time_control_bucket_enum
from app.models.user_rating_anchors import TimeControlBucket
from app.services.global_percentile_cdf import CdfMetricId

# Postgres ENUM type descriptor.
# create_type=False: Alembic owns the lifecycle; SQLAlchemy must never attempt to
# CREATE or DROP this type itself. Project precedent: app/models/game.py:20-40.
#
# The 8 family-level values come first; per-TC dimensionality is carried by the
# time_control_bucket PK column. Their order matches the destructive reshape
# migration verbatim.
#
# Then 12 TC-suffixed values (conversion_rate, parity_rate,
# recovery_rate × bullet, blitz, rapid, classical). These ride in the
# existing per-(user, metric, time_control_bucket) PK structure — the TC-suffix
# in the ENUM value is redundant with the PK column but is required for the
# ``user_benchmark_percentiles`` ORM write path.
# Order: family-then-TC, matching the migration's _NEW_VALUES tuple and
# gen_global_percentile_cdf.py IN_SCOPE_METRICS ordering.
benchmark_metric_enum = SAEnum(
    "score_gap",
    "achievable_score_gap",
    "score_gap_conv",
    "score_gap_parity",
    "recovery_score_gap",
    "time_pressure_score_gap",
    "clock_gap",
    "net_flag_rate",
    # Rate families (TC-suffixed for the benchmark_metric Postgres ENUM).
    "conversion_rate_bullet",
    "conversion_rate_blitz",
    "conversion_rate_rapid",
    "conversion_rate_classical",
    "parity_rate_bullet",
    "parity_rate_blitz",
    "parity_rate_rapid",
    "parity_rate_classical",
    "recovery_rate_bullet",
    "recovery_rate_blitz",
    "recovery_rate_rapid",
    "recovery_rate_classical",
    # Bare family names required by upsert_percentile
    # write path (CdfMetricId is used as the metric column value; TC-suffix in
    # ENUM is redundant with time_control_bucket PK column — migration 52c928794fe7).
    "conversion_rate",
    "parity_rate",
    "recovery_rate",
    name="benchmark_metric",
    create_type=False,
)


class UserBenchmarkPercentile(Base):
    """One canonical-slice percentile row per (user_id, metric, time_control_bucket).

    Written by Stage A (score_gap) and Stage B (eval-dependent metrics)
    background tasks, and by the one-shot backfill script.

    Row existence implies above-floor: if a user has no above-floor games for
    a (metric, tc) cell, no row is written. The chip
    suppresses naturally when fetch_for_user returns no entry for that
    (metric, tc) pair.

    Composite PK is (user_id, metric, time_control_bucket). The ENUM holds the
    11 CdfMetricId family names (per-TC dimensionality lives in the
    time_control_bucket PK column) plus 12 legacy TC-suffixed rate values
    (23 total).

    ``recovery_score_gap`` is included under the peer-relative framing.

    Per-metric ``n_games`` semantics:

    - ``score_gap`` → count of endgame games on the user's pool (the binding
      floor; paired non-endgame count is in the backfill log only, not the
      table).
    - ``achievable_score_gap`` → count of endgame-entry games with non-null
      ``d_i`` on the pool.
    - ``score_gap_conv`` → count of spans classified into the
      conversion bucket on the pool.
    - ``score_gap_parity`` → count of spans classified into the
      parity bucket on the pool.
    - ``recovery_score_gap`` → count of spans classified into the recovery
      bucket on the pool.
    - ``time_pressure_score_gap`` / ``clock_gap`` / ``net_flag_rate`` →
      count of games in the TC's recent-3000 pool used to compute the
      time-pressure metric.
    """

    __tablename__ = "user_benchmark_percentiles"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    metric: Mapped[CdfMetricId] = mapped_column(benchmark_metric_enum, primary_key=True)
    time_control_bucket: Mapped[TimeControlBucket] = mapped_column(
        time_control_bucket_enum,
        primary_key=True,
        nullable=False,
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    percentile: Mapped[float | None] = mapped_column(Float, nullable=True)
    n_games: Mapped[int] = mapped_column(Integer, nullable=False)
    cdf_snapshot: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    computed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
