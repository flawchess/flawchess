from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKeyConstraint,
    Index,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    Text,
    text,
)
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

# Phase 116 EVAL-03 / D-116-02: opening-region boundary for the full-ply drain's
# cross-user full_hash dedup lookup. Intentionally tighter than MAX_EXPLORER_PLY.
#
# COUPLING INVARIANT (WR-08): this constant MUST equal:
#   1. The partial-index WHERE predicate on ix_gp_full_hash_opening below
#      (postgresql_where=text(f"ply <= {DEDUP_MAX_PLY}")).
#   2. The drain-side boundary in app/services/eval_drain.py (which imports
#      this constant — _DEDUP_MAX_PLY is an alias, never a separate literal).
# If the drain boundary ever drifted above the index predicate, dedup lookups
# would silently stop using the partial index — the same failure mode the
# MAX_EXPLORER_PLY invariant above guards against.
DEDUP_MAX_PLY: int = 20


class GamePosition(Base):
    __tablename__ = "game_positions"
    __table_args__ = (
        # Explicit PK in the prod/migration column order (user_id, game_id, ply).
        # SEED-041 §B2: without this, SQLAlchemy infers PK order from the
        # mapped_column declaration order (game_id, user_id, ply), which drifts
        # from prod and any metadata-derived DDL / autogenerate diff.
        PrimaryKeyConstraint("user_id", "game_id", "ply", name="game_positions_pkey"),
        # SEED-041 §B1: composite FK (game_id, user_id) -> games(id, user_id)
        # replaces the former per-column FKs (game_id -> games.id,
        # user_id -> users.id). Halves per-row FK trigger work on COPY import and
        # enforces that a position's denormalized user_id matches the owning game.
        # The chain to users stays intact via games.user_id -> users.id.
        ForeignKeyConstraint(
            ["game_id", "user_id"],
            ["games.id", "games.user_id"],
            ondelete="CASCADE",
            name="game_positions_game_user_fkey",
        ),
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
        # Phase 116 EVAL-03: cross-user dedup index for opening-region full_hash lookups.
        # No user_id column — the drain's dedup query is cross-user (D-116-02).
        # Predicate interpolates DEDUP_MAX_PLY (WR-08 coupling invariant — see the
        # constant's docstring above); intentionally tighter than MAX_EXPLORER_PLY (28)
        # and distinct from the user-scoped indexes.
        Index(
            "ix_gp_full_hash_opening",
            "full_hash",
            postgresql_where=text(f"ply <= {DEDUP_MAX_PLY}"),
        ),
    )

    # Natural composite PK (SEED-035): (user_id, game_id, ply) replaces the former
    # surrogate `id` column. The key is provably unique (one row per user/game/half-move).
    # The SQLAlchemy identity map now keys rows on the 3-tuple instead of a single id.
    # PK + FK are declared at table level in __table_args__ (SEED-041 §B1/§B2);
    # index=True on game_id keeps ix_game_positions_game_id (backs the cascade).
    game_id: Mapped[int] = mapped_column(nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(nullable=False)  # denormalized for query perf
    ply: Mapped[int] = mapped_column(
        SmallInteger, nullable=False
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

    # D-117-01 + D-117-03: PV[0] UCI best move for every evaluated position.
    # 4 chars normal (e.g. "e2e4") / 5 chars promotion (e.g. "e7e8q").
    # Written by the full-ply drain alongside eval_cp/eval_mate (zero extra engine cost).
    # Transplanted via full_hash dedup in the opening region (ply <= DEDUP_MAX_PLY),
    # exactly like eval_cp — safe because best_move is a property of the pre-move position.
    best_move: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    # D-117-02: ~12-ply UCI refutation line (space-joined), stored only at the position
    # AFTER each flawed move (ply = flaw_ply + 1). This is the SEED-039 refutation line
    # consumed by the tactic-motif classifier. NULL for non-flaw positions.
    pv: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Endgame class: SmallInteger IntEnum (1-6), NULL for non-endgame positions.
    # 1=rook, 2=minor_piece, 3=pawn, 4=queen, 5=mixed, 6=pawnless.
    # Computed from material_signature at import time (see endgame_service.classify_endgame_class).
    # Per D-06: SmallInteger for fastest GROUP BY, 2 bytes per row.
    endgame_class: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    game: Mapped["Game"] = relationship(back_populates="positions")  # ty: ignore[unresolved-reference]
