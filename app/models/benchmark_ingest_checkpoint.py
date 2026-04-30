"""ORM for the benchmark_ingest_checkpoints table (benchmark DB only).

Phase 69 INGEST-04. Per-(user, TC) outer-loop checkpoint for the ingestion
orchestrator. Created via Base.metadata.create_all() against the benchmark
engine -- NOT in the canonical Alembic chain (preserves INFRA-02).

Status lifecycle:
    pending -> completed   (run_import succeeded with games_imported >= min)
    pending -> skipped     (run_import succeeded but games_imported < min)
    pending -> failed      (terminal exception captured to Sentry at outer boundary)

The orchestrator distinguishes two terminal-status sets:
  - "filled" (status='completed'): counts toward --per-cell target.
  - "attempted" (status in {completed, skipped, failed}): blocks re-attempt on
    resume but doesn't necessarily fill a slot. A 404 or low-yield user is
    checkpointed so we don't retry, but the orchestrator pulls a replacement
    from the candidate pool until the cell hits its useful-user target.

The 'skipped' status is now used for low-yield users (< min_useful_games);
historically it also marked users with >=20k games (D-14), now superseded by
lichess server-side ``max=`` truncation. Both meanings coexist as
"checkpointed but not useful for benchmarks."

The (lichess_username, tc_bucket) compound unique constraint allows one user to
have one checkpoint per TC where they qualified. Per-game
(user_id, platform, platform_game_id) unique constraint makes
interrupted-then-resumed users no-op on already-imported games.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BenchmarkIngestCheckpoint(Base):
    """Per-user outer-loop checkpoint for the benchmark ingestion orchestrator."""

    __tablename__ = "benchmark_ingest_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "lichess_username",
            "tc_bucket",
            name="uq_benchmark_ingest_checkpoints_username_tc",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lichess_username: Mapped[str] = mapped_column(String(100), nullable=False)
    rating_bucket: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tc_bucket: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    games_imported: Mapped[int] = mapped_column(nullable=False, default=0)
    skip_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # SET NULL (not CASCADE) -- deleting a stub user should not destroy the audit row
    benchmark_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
