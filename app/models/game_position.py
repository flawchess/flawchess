from typing import Optional

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Index, SmallInteger, String
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
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )  # denormalized for query perf
    ply: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # half-move number (0 = initial), max ~600

    # Zobrist hashes — explicit BIGINT for 64-bit values
    full_hash: Mapped[int] = mapped_column(BigInteger, nullable=False)
    white_hash: Mapped[int] = mapped_column(BigInteger, nullable=False)
    black_hash: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # SAN of the move played FROM this position (leading to ply+1); None on final position
    move_san: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Clock seconds remaining from %clk PGN annotation; None if not present or final position
    # Float(24) maps to REAL (4 bytes) instead of DOUBLE PRECISION (8 bytes)
    clock_seconds: Mapped[float | None] = mapped_column(Float(24), nullable=True)

    # Position metadata — computed by position_classifier.py, populated during import (Phase 27)
    material_count: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    material_signature: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    material_imbalance: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    has_opposite_color_bishops: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Lichess piece-count for endgame classification: count of Q+R+B+N for both sides combined.
    # Nullable because existing rows won't have it until the backfill migration.
    piece_count: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # Engine analysis: per-move eval from lichess %eval PGN annotations (NULL for chess.com and unanalyzed games)
    eval_cp: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    eval_mate: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    game: Mapped["Game"] = relationship(back_populates="positions")  # type: ignore[name-defined]
