import datetime

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ImportJob(Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        # Phase 149 PRUNE-05: partial unique — at most one active (pending or
        # in_progress) job per (user_id, platform). Declared here for
        # model/DB parity (keeps `alembic revision --autogenerate` a no-op);
        # the actual DDL is created/dropped by the dedicated migration.
        # Predicate MUST stay textually identical to
        # import_job_repository.get_active_job_for_user_platform's WHERE
        # clause (drift-prevention, mirrors eval_jobs.py's convention).
        Index(
            "uq_import_jobs_user_platform_active",
            "user_id",
            "platform",
            unique=True,
            postgresql_where=sa.text("status IN ('pending', 'in_progress')"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # pending/in_progress/completed/failed
    games_fetched: Mapped[int] = mapped_column(nullable=False, default=0)
    games_imported: Mapped[int] = mapped_column(nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    last_synced_at: Mapped[datetime.datetime | None]  # for incremental sync
    started_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime.datetime | None]
