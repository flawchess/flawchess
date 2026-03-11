import datetime

from sqlalchemy import String, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # pending/in_progress/completed/failed
    games_fetched: Mapped[int] = mapped_column(nullable=False, default=0)
    games_imported: Mapped[int] = mapped_column(nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    last_synced_at: Mapped[datetime.datetime | None]  # for incremental sync
    started_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime.datetime | None]
