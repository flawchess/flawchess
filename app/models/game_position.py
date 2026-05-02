from typing import Optional

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Index, SmallInteger, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class GamePosition(Base):
    __tablename__ = "game_positions"
    __table_args__ = (
        # Composite indexes for "my pieces only" queries (Phase 3)
        Index("ix_gp_user_white_hash", "user_id", "white_hash"),
        Index("ix_gp_user_black_hash", "user_id", "black_hash"),
        # Covering index for Phase 12 next-moves aggregation queries.
        # Also serves (user_id, full_hash) prefix lookups — the narrower
        # ix_gp_user_full_hash was dropped as redundant (prod stats showed
        # this wider index handled the GROUP BY move_san aggregation via
        # index-only scans, while the narrow one's 132 scans/period could
        # safely fall back to the prefix of this index).
        Index("ix_gp_user_full_hash_move_san", "user_id", "full_hash", "move_san"),
        # Covering index for endgame GROUP BY queries — enables index-only scans for:
        # 1. Span aggregation: GROUP BY game_id, endgame_class HAVING COUNT(ply) >= threshold
        # 2. Entry-ply eval lookup: array_agg(eval_cp ORDER BY ply)[1], array_agg(eval_mate ORDER BY ply)[1]
        # INCLUDE(eval_cp, eval_mate) avoids a 5M+ row seq scan for the entry-ply eval lookup (REFAC-02).
        Index(
            "ix_gp_user_endgame_game",
            "user_id", "game_id", "endgame_class", "ply",
            postgresql_where=text("endgame_class IS NOT NULL"),
            postgresql_include=["eval_cp", "eval_mate"],
        ),
        # Phase 70 (v1.13): partial composite covering index for the
        # opening_insights_service transition aggregation. COLUMN ORDER
        # (user_id, game_id, ply) is LOAD-BEARING — matches the window
        # function's PARTITION BY game_id ORDER BY ply, so PostgreSQL streams
        # rows from the index without a re-sort (Index Only Scan, Heap
        # Fetches: 0). Do NOT reorder for symmetry with sibling ix_gp_user_*
        # indexes. Phase 71 hotfix expanded the predicate to include ply 0:
        # the SQL needs ply 0's move_san row in the partition so the very
        # first move of each game is part of entry_san_sequence (otherwise
        # `_replay_san_sequence` fails with chess.IllegalMoveError).
        # See alembic migration 20260426_201533_80e22b38993a_add_gp_user_game_ply_index.py
        # for the original rationale and verified perf numbers
        # (Hikaru 65k games -> 816 ms).
        Index(
            "ix_gp_user_game_ply",
            "user_id", "game_id", "ply",
            postgresql_where=text("ply BETWEEN 0 AND 17"),
            postgresql_include=["full_hash", "move_san"],
        ),
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
    material_signature: Mapped[Optional[str]] = mapped_column(String(65), nullable=True)
    material_imbalance: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    has_opposite_color_bishops: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Lichess piece-count for endgame classification: count of Q+R+B+N for both sides combined.
    # Nullable because existing rows won't have it until the backfill migration.
    piece_count: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # Lichess middlegame detection columns (nullable — existing rows backfilled via reimport)
    # True when < 4 pieces on either side's back rank
    backrank_sparse: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    # Lichess mixedness score: measures how interleaved white/black pieces are (0-~400)
    mixedness: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # Engine analysis: per-move eval from lichess %eval PGN annotations (NULL for chess.com and unanalyzed games)
    eval_cp: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    eval_mate: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # Endgame class: SmallInteger IntEnum (1-6), NULL for non-endgame positions.
    # 1=rook, 2=minor_piece, 3=pawn, 4=queen, 5=mixed, 6=pawnless.
    # Computed from material_signature at import time (see endgame_service.classify_endgame_class).
    # Per D-06: SmallInteger for fastest GROUP BY, 2 bytes per row.
    endgame_class: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    game: Mapped["Game"] = relationship(back_populates="positions")  # ty: ignore[unresolved-reference]
