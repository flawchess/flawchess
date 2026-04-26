"""ORM for the benchmark_selected_users table (benchmark DB only).

Phase 69 INGEST-02. Holds the per-cell username pool produced by the streaming
dump scan in scripts/select_benchmark_users.py. Created via Base.metadata.create_all()
against the benchmark engine -- NOT in the canonical Alembic chain (INFRA-02 isolates
the canonical schema; benchmark-only tables stay out of dev/prod/test).

The (lichess_username) unique constraint makes re-running selection idempotent:
the same username produced from a re-scan will not duplicate-insert.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base


class BenchmarkSelectedUser(Base):
    """A Lichess username selected from a monthly dump for benchmark ingestion.

    rating_bucket: 800/1200/1600/2000/2400 (REQUIREMENTS.md INGEST-02 400-wide grid).
    tc_bucket: bullet/blitz/rapid/classical (canonical FlawChess TC buckets).
    median_elo: median Elo across this player's snapshot-month games.
    eval_game_count: number of snapshot-month games carrying [%eval] annotations.
    dump_month: "YYYY-MM" of the source dump (e.g. "2026-02").
    """

    __tablename__ = "benchmark_selected_users"
    __table_args__ = (
        UniqueConstraint(
            "lichess_username", name="uq_benchmark_selected_users_username"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    lichess_username: Mapped[str] = mapped_column(String(100), nullable=False)
    rating_bucket: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tc_bucket: Mapped[str] = mapped_column(String(20), nullable=False)
    median_elo: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    eval_game_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    selected_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    dump_month: Mapped[str] = mapped_column(String(7), nullable=False)
