"""ORM for the benchmark_ingest_checkpoints table (benchmark DB only).

Phase 69 INGEST-04. Per-user outer-loop checkpoint for the ingestion orchestrator.
Created via Base.metadata.create_all() against the benchmark engine -- NOT in the
canonical Alembic chain (preserves INFRA-02).

Status lifecycle:
    pending -> completed   (run_import succeeded)
    pending -> skipped     (hard-skip per D-14: >20k window-bounded games)
    pending -> failed      (terminal exception captured to Sentry at outer boundary)

Resume rule: orchestrator skips usernames with status in {completed, skipped, failed}
and processes pending/missing usernames. Per-game (user_id, platform, platform_game_id)
unique constraint makes interrupted-then-resumed users no-op on already-imported games.
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
            "lichess_username", name="uq_benchmark_ingest_checkpoints_username"
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
