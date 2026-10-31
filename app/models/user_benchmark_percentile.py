"""ORM model for user_benchmark_percentiles table.

``metric`` is TEXT with a CHECK constraint over the ``CdfMetricId`` Literal in
``app/services/global_percentile_cdf.py`` (13 ids since Phase 243). The CHECK is
generated from the ``CdfMetricId`` Literal's members, so the Literal stays the single
source of truth. Per-TC dimensionality lives in the ``time_control_bucket`` PK
column, not in the metric id. Until Phase 243 the column was the native
``benchmark_metric`` Postgres ENUM; migration ``b7e4c2a9f013`` converted it to
TEXT + CHECK (root CLAUDE.md: avoid native ENUMs) and deleted any row on a dead
legacy TC-suffixed label. Earlier history: the original
``20260524_000000_add_user_benchmark_percentiles.py`` created the table and ENUM;
``20260526_222651_1945ae56aa20_reshape_user_benchmark_percentiles.py`` reshaped
both.

Composite PK is (user_id, metric, time_control_bucket, color). At most one row per
user per metric per TC bucket per colour. ``color`` is ``'all'`` for the
colour-agnostic rows every Endgames family writes, and ``'white'`` / ``'black'`` for
the per-colour "out of the opening" rows (Phase 243); the peer CDF itself is
colour-pooled, so ``benchmark_cohort_cdf`` carries no colour.

Row existence implies above-floor. Below-floor (user, metric, tc[, colour]) triples
produce NO row — the chip suppresses naturally via an empty
fetch_for_user[metric][tc] entry.

The ``n_games`` column carries per-(metric × TC) semantics under the
peer-relative framing — see the class docstring.
"""

from __future__ import annotations

import datetime

import typing
from typing import Final, Literal

from sqlalchemy import CheckConstraint, Date, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base
from app.models.game import time_control_bucket_enum
from app.models.user_rating_anchors import TimeControlBucket
from app.services.global_percentile_cdf import CdfMetricId

# Row colour: 'all' = colour-agnostic (every Endgames family); 'white' / 'black' =
# the per-colour opening rows (Phase 243).
PercentileColor = Literal["all", "white", "black"]
PERCENTILE_COLORS: Final[tuple[PercentileColor, ...]] = typing.get_args(PercentileColor)

# The allowed metric ids, derived from the Literal so the CHECK cannot drift from it.
BENCHMARK_METRIC_VALUES: Final[tuple[str, ...]] = typing.get_args(CdfMetricId)


def _check_in_sql(column: str, values: tuple[str, ...]) -> str:
    """Render ``<column> IN ('a', 'b', ...)`` from constant, code-defined values."""
    return f"{column} IN (" + ", ".join(f"'{v}'" for v in values) + ")"


def benchmark_metric_check_sql() -> str:
    """CHECK expression restricting ``metric`` to the ``CdfMetricId`` values."""
    return _check_in_sql("metric", BENCHMARK_METRIC_VALUES)


class UserBenchmarkPercentile(Base):
    """One canonical-slice percentile row per (user_id, metric, time_control_bucket, color).

    Written by Stage A (score_gap) and Stage B (eval-dependent metrics)
    background tasks, and by the one-shot backfill script.

    Row existence implies above-floor: if a user has no above-floor games for
    a (metric, tc) cell, no row is written. The chip
    suppresses naturally when fetch_for_user returns no entry for that
    (metric, tc) pair.

    Composite PK is (user_id, metric, time_control_bucket, color). ``metric`` holds
    the 13 CdfMetricId values (per-TC dimensionality lives in the
    time_control_bucket PK column); ``color`` is 'all' for colour-agnostic rows and
    'white' / 'black' for the per-colour opening rows.

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
    - ``opening_worse_rate`` / ``opening_better_rate`` → count of qualifying games
      (reached the middlegame with an eval, or ended early by resignation, checkmate
      or timeout) for that colour on the TC's recent-3000 pool.
    """

    __tablename__ = "user_benchmark_percentiles"
    __table_args__ = (
        CheckConstraint(benchmark_metric_check_sql(), name="ck_user_benchmark_percentiles_metric"),
        CheckConstraint(
            _check_in_sql("color", PERCENTILE_COLORS), name="ck_user_benchmark_percentiles_color"
        ),
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    metric: Mapped[CdfMetricId] = mapped_column(Text, primary_key=True)
    time_control_bucket: Mapped[TimeControlBucket] = mapped_column(
        time_control_bucket_enum,
        primary_key=True,
        nullable=False,
    )
    color: Mapped[PercentileColor] = mapped_column(
        Text,
        primary_key=True,
        nullable=False,
        server_default="all",
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
