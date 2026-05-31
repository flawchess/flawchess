"""SQLAlchemy model for the ``benchmark_cohort_cdf`` table.

LONG layout (CONTEXT D-01): one row per breakpoint.
Primary key: (metric, anchor_elo, tc, percentile).

Cell reconstruction: fetching the 99 rows for a given (metric, anchor_elo, tc)
cell with ``ORDER BY percentile`` rebuilds one CdfTable. The ``breakpoints``
tuple of the reconstructed CdfTable is indexed parallel to
``BREAKPOINT_PERCENTILES`` (p1..p99), so row order is load-bearing.

Audit columns:
  n_users: number of benchmark users contributing to this cell. NULLable
    because early seeds may lack this count.
  snapshot_month: the benchmark snapshot month that produced these breakpoints
    (e.g. "2026-05"). NULLable plain audit column, NOT part of any idempotency
    gate (CONTEXT note #1).

~123k rows total (11 metrics × ≤ 36 anchor_elo grid points × 4 TC buckets
× 99 percentiles, minus grid cells that lack the K=200 user floor).
"""

from __future__ import annotations

from sqlalchemy import Double, Index, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.game import time_control_bucket_enum
from app.models.user_benchmark_percentile import benchmark_metric_enum
from app.models.user_rating_anchors import TimeControlBucket
from app.services.global_percentile_cdf import CdfMetricId

__all__ = ["BenchmarkCohortCdf"]


class BenchmarkCohortCdf(Base):
    """One breakpoint row per (metric, anchor_elo, tc, percentile).

    See module docstring for the LONG layout description and cell-reconstruction
    notes.
    """

    __tablename__ = "benchmark_cohort_cdf"

    # The composite PK leads with ``metric``, but the only read path
    # (``load_cohort_cells``) filters on ``anchor_elo`` + ``tc`` and returns all
    # metrics, so the PK cannot serve that filter -- without this index Postgres
    # seq-scans the full ~123k-row table on every import. Index the filter
    # columns so the prefetch is an index scan over the user's anchor x TC grid.
    __table_args__ = (Index("ix_benchmark_cohort_cdf_anchor_tc", "anchor_elo", "tc"),)

    # --- composite primary key (metric, anchor_elo, tc, percentile) ----------

    metric: Mapped[CdfMetricId] = mapped_column(
        benchmark_metric_enum,
        primary_key=True,
    )
    anchor_elo: Mapped[int] = mapped_column(
        SmallInteger,
        primary_key=True,
    )
    tc: Mapped[TimeControlBucket] = mapped_column(
        time_control_bucket_enum,
        primary_key=True,
    )
    percentile: Mapped[int] = mapped_column(
        SmallInteger,
        primary_key=True,
    )

    # --- data column ----------------------------------------------------------

    value: Mapped[float] = mapped_column(
        Double,
        nullable=False,
    )

    # --- audit columns --------------------------------------------------------

    n_users: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    snapshot_month: Mapped[str | None] = mapped_column(
        String(length=7),
        nullable=True,
    )
