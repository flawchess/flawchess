import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PositionBookmark(Base):
    __tablename__ = "position_bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    target_hash: Mapped[int] = mapped_column(BigInteger, nullable=False)  # Zobrist hash, needs 64-bit
    fen: Mapped[str] = mapped_column(String(200), nullable=False)
    moves: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded SAN array
    color: Mapped[str | None] = mapped_column(String(10))  # "white" | "black" | None
    match_side: Mapped[str] = mapped_column(String(10), nullable=False, default="full")
    is_flipped: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
