from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import REAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# Opening-phase explorer depth cap (SEED-033).
#
# Value 28: ECO's named-position ceiling is 28 plies; only elite forcing lines
# (Najdorf Poisoned Pawn, Botvinnik Semi-Slav, Marshall) run deeper, and those
# live at ply 40-80 so no practical cutoff catches them. FlawChess openings.ply_count
# max = 36, but 28 covers the full ECO ceiling with headroom. See SEED-033 §2.
#
# COUPLING INVARIANT (SEED-033 §3): this constant MUST equal:
#   1. The partial-index WHERE predicate on the three Zobrist hash indexes below
#      (postgresql_where=text(f"ply <= {MAX_EXPLORER_PLY}")).
#   2. The frontend explorer cap in frontend/src/lib/explorer.ts.
# If the explorer cap ever exceeds the index boundary, hash lookups for positions
# past the boundary silently miss the partial index.
MAX_EXPLORER_PLY: int = 28


class GamePosition(Base):
    __tablename__ = "game_positions"
    __table_args__ = (
        # Composite indexes for "my pieces only" queries (Phase 3).
        # Partial WHERE ply <= MAX_EXPLORER_PLY (SEED-033): the explorer is hard-capped
        # at that depth, so no hash lookup ever targets a position past the boundary —
        # making the win unconditional. Migration: partial_index_hash_columns_at_ply28.
        Index(
            "ix_gp_user_white_hash",
            "user_id",
            "white_hash",
            postgresql_where=text(f"ply <= {MAX_EXPLORER_PLY}"),
        ),
        Index(
            "ix_gp_user_black_hash",
            "user_id",
            "black_hash",
            postgresql_where=text(f"ply <= {MAX_EXPLORER_PLY}"),
        ),
        # Covering index for Phase 12 next-moves aggregation queries.
        # Also serves (user_id, full_hash) prefix lookups — the narrower
        # ix_gp_user_full_hash was dropped as redundant (prod stats showed
        # this wider index handled the GROUP BY move_san aggregation via
        # index-only scans, while the narrow one's 132 scans/period could
        # safely fall back to the prefix of this index).
        # Partial WHERE ply <= MAX_EXPLORER_PLY (SEED-033) — same rationale as above.
        Index(
            "ix_gp_user_full_hash_move_san",
            "user_id",
            "full_hash",
            "move_san",
            postgresql_where=text(f"ply <= {MAX_EXPLORER_PLY}"),
        ),
        # Covering index for endgame GROUP BY queries — enables index-only scans for:
        # 1. Span aggregation: GROUP BY game_id, endgame_class HAVING COUNT(ply) >= threshold
        # 2. Entry-ply eval lookup: array_agg(eval_cp ORDER BY ply)[1], array_agg(eval_mate ORDER BY ply)[1]
        # INCLUDE(eval_cp, eval_mate) avoids a 5M+ row seq scan for the entry-ply eval lookup (REFAC-02).
        Index(
            "ix_gp_user_endgame_game",
            "user_id",
            "game_id",
            "endgame_class",
            "ply",
            postgresql_where=text("endgame_class IS NOT NULL"),
            postgresql_include=["eval_cp", "eval_mate"],
        ),
        # ix_gp_user_game_ply removed in SEED-035 — its (user_id, game_id, ply) key is
        # absorbed by the composite PK below (the partial ply BETWEEN 0 AND 17 /
        # INCLUDE(full_hash, move_san) specialization was acceptable to retire).
    )

    # Natural composite PK (SEED-035): (user_id, game_id, ply) replaces the former
    # surrogate `id` column. The key is provably unique (one row per user/game/half-move).
    # The SQLAlchemy identity map now keys rows on the 3-tuple instead of a single id.
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), nullable=False, primary_key=True, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, primary_key=True
    )  # denormalized for query perf
    ply: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, primary_key=True
    )  # half-move number (0 = initial), max ~600

    # Zobrist hashes — explicit BIGINT for 64-bit values
    full_hash: Mapped[int] = mapped_column(BigInteger, nullable=False)
    white_hash: Mapped[int] = mapped_column(BigInteger, nullable=False)
    black_hash: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # SAN of the move played FROM this position (leading to ply+1); None on final position
    move_san: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Clock seconds remaining from %clk PGN annotation; None if not present or final position
    # REAL (4 bytes) instead of DOUBLE PRECISION (8 bytes)
    clock_seconds: Mapped[float | None] = mapped_column(REAL, nullable=True)

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

    # Lichess Divider.scala phase classification: 0=opening, 1=middlegame, 2=endgame.
    # Nullable column — populated by import-path code from import time forward; existing
    # rows are populated by scripts/backfill_eval.py (PHASE-FILL-01). Nullability is
    # transient and closes out post-backfill. PHASE-INV-01: phase=2 ⟺ endgame_class IS NOT NULL.
    phase: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # Engine analysis: per-move eval from lichess %eval PGN annotations (NULL for chess.com and unanalyzed games)
    eval_cp: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    eval_mate: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # Endgame class: SmallInteger IntEnum (1-6), NULL for non-endgame positions.
    # 1=rook, 2=minor_piece, 3=pawn, 4=queen, 5=mixed, 6=pawnless.
    # Computed from material_signature at import time (see endgame_service.classify_endgame_class).
    # Per D-06: SmallInteger for fastest GROUP BY, 2 bytes per row.
    endgame_class: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    game: Mapped["Game"] = relationship(back_populates="positions")  # ty: ignore[unresolved-reference]
