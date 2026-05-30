"""ORM model for user_benchmark_percentiles table.

The ``benchmark_metric_enum`` mirrors the ``CdfMetricId`` Literal in
``app/services/global_percentile_cdf.py``. Phase 94.4 reshapes this from
the 16-value 94.3 form (4 page-level metrics + 12 per-(metric × TC)
time-pressure entries) to the 8-value form per CONTEXT D-13. The 12 composite
TC-suffixed values are deleted: per-TC dimensionality now lives in the
``time_control_bucket`` PK column, not in the ENUM. See CONTEXT D-01
(PK widening) + D-13 (8-value ENUM) + D-05a (Recovery Score Gap rescued
from the v1 drop list under peer-relative framing).

Phase 99 extends the ENUM with 12 new values (3 rate-metric families × 4 TCs),
bringing the initial total to 11 metric families represented across 20 SAEnum values
(8 family-level + 12 TC-suffixed rate values). Phase 99 Plan 05 (Rule 1) adds
3 more bare family names (conversion_rate, parity_rate, recovery_rate) needed
by the upsert_percentile write path, bringing the SAEnum total to 23 values.
The 12 TC-suffixed values remain for forward compatibility. The bare family
names match the CdfMetricId entries and are stored with time_control_bucket
providing the per-TC dimensionality (PK column, not ENUM suffix).

``create_type=False`` means Alembic controls the ENUM lifecycle — see
``alembic/versions/20260526_222651_1945ae56aa20_reshape_user_benchmark_percentiles.py``
for the destructive reshape (drop/recreate of both the table and the ENUM).
Earlier ENUM/table history: the original
``20260524_000000_add_user_benchmark_percentiles.py`` created the table and
ENUM (4-value); ``20260524_170733_fd5b551f381c_extend_benchmark_metric_for_tc_pressure.py``
extended to 16 values for Phase 94.3 (now superseded by the destructive
94.4 reshape).

Phase 94.4 D-01: composite PK widens to (user_id, metric, time_control_bucket).
At most one row per user per metric per TC bucket.

Phase 94.1 Plan 13 semantics (gap-closure) preserved:
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
# Phase 94.4 D-13: exactly 8 values. The 12 per-(metric × TC) composite values
# from Phase 94.3 are deleted; per-TC dimensionality is now carried by the
# time_control_bucket PK column. Order matches the destructive reshape
# migration verbatim.
#
# Phase 99: 12 new TC-suffixed values added (conversion_rate, parity_rate,
# recovery_rate × bullet, blitz, rapid, classical). These ride in the
# existing per-(user, metric, time_control_bucket) PK structure — the TC-suffix
# in the ENUM value is redundant with the PK column but is required for the
# ``user_benchmark_percentiles`` ORM write path (Pitfall 3 mitigation).
# Order: family-then-TC, matching the Phase 99 migration _NEW_VALUES tuple and
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
    # Phase 99 rate families (TC-suffixed for the benchmark_metric Postgres ENUM).
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
    # Phase 99 Plan 05 Rule 1 fix: bare family names required by upsert_percentile
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
    background tasks, and by the one-shot backfill script (Plan 06).

    Row existence implies above-floor: if a user has no above-floor games for
    a (metric, tc) cell, no row is written (Plan 13 gap-closure). The chip
    suppresses naturally when fetch_for_user returns no entry for that
    (metric, tc) pair.

    Phase 94.4 D-01: composite PK widens to
    (user_id, metric, time_control_bucket). Phase 94.4 D-13: ENUM collapses
    to exactly 8 values; per-TC dimensionality moves out of the ENUM into the
    new PK column.

    Phase 94.4 D-05a: ``recovery_score_gap`` is rescued from the v1 drop list
    under the peer-relative framing — it is one of the 8 ENUM values.

    Per-metric ``n_games`` semantics (Phase 94.2 D-9-amend, preserved):

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
