from typing import Optional

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class GamePosition(Base):
    __tablename__ = "game_positions"
    __table_args__ = (
        # Composite indexes for the three query patterns (Phase 3)
        Index("ix_gp_user_full_hash", "user_id", "full_hash"),
        Index("ix_gp_user_white_hash", "user_id", "white_hash"),
        Index("ix_gp_user_black_hash", "user_id", "black_hash"),
        # Covering index for Phase 12 next-moves aggregation queries
        Index("ix_gp_user_full_hash_move_san", "user_id", "full_hash", "move_san"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(nullable=False)  # denormalized for query perf
    ply: Mapped[int] = mapped_column(nullable=False)       # half-move number (0 = initial)

    # Zobrist hashes — all BIGINT via type_annotation_map
    full_hash: Mapped[int] = mapped_column(nullable=False)
    white_hash: Mapped[int] = mapped_column(nullable=False)
    black_hash: Mapped[int] = mapped_column(nullable=False)

    # SAN of the move played FROM this position (leading to ply+1); None on final position
    move_san: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    game: Mapped["Game"] = relationship(back_populates="positions")  # type: ignore[name-defined]
