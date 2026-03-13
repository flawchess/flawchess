import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    target_hash: Mapped[int] = mapped_column(nullable=False)  # BIGINT via type_annotation_map
    fen: Mapped[str] = mapped_column(String(200), nullable=False)
    moves: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded SAN array
    color: Mapped[str | None] = mapped_column(String(10))  # "white" | "black" | None
    match_side: Mapped[str] = mapped_column(String(10), nullable=False, default="full")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
