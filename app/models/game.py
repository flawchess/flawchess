import datetime

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import REAL
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

# PostgreSQL enum type objects (create_type=False: Alembic controls the type lifecycle)
game_result_enum = SAEnum("1-0", "0-1", "1/2-1/2", name="gameresult", create_type=False)
color_enum = SAEnum("white", "black", name="color", create_type=False)
termination_enum = SAEnum(
    "checkmate",
    "resignation",
    "timeout",
    "draw",
    "abandoned",
    "unknown",
    name="termination",
    create_type=False,
)
time_control_bucket_enum = SAEnum(
    "bullet",
    "blitz",
    "rapid",
    "classical",
    name="timecontrolbucket",
    create_type=False,
)


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "platform", "platform_game_id", name="uq_games_user_platform_game_id"
        ),
        # SEED-041 §B1: unique index on (id, user_id) is the target of the
        # game_positions composite FK (game_id, user_id) -> games(id, user_id).
        # Built CONCURRENTLY in the migration; declared here as a unique index
        # (not a constraint) to match the migration and keep metadata in sync.
        Index("uq_games_id_user_id", "id", "user_id", unique=True),
        # SEED-041 §A2: (user_id, played_at DESC) lets the recent-games WindowAgg
        # run-condition early-terminate instead of scanning the user's full game
        # history. Replaces the former index=True on user_id (ix_games_user_id) —
        # this index's user_id prefix serves every user_id-only lookup too.
        Index("ix_games_user_played_at", "user_id", sa.text("played_at DESC")),
        # SEED-041 §A3: partial index for the per-import-batch pending-evals gate
        # (users_with_zero_pending). Near-zero size at steady state. Keep
        # ix_games_evals_pending (on id) for the id-ordered drain poll.
        Index(
            "ix_games_user_evals_pending",
            "user_id",
            postgresql_where=sa.text("evals_completed_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Platform identity
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # "chess.com" | "lichess"
    platform_game_id: Mapped[str] = mapped_column(String(100), nullable=False)
    platform_url: Mapped[str | None] = mapped_column(String(500))

    # Game content
    pgn: Mapped[str] = mapped_column(Text, nullable=False)

    # Result — PostgreSQL ENUM types enforce valid values at the DB level
    result: Mapped[str] = mapped_column(
        game_result_enum, nullable=False
    )  # "1-0" | "0-1" | "1/2-1/2"
    user_color: Mapped[str] = mapped_column(color_enum, nullable=False)  # "white" | "black"
    termination_raw: Mapped[str | None] = mapped_column(String(50))  # platform's original string
    termination: Mapped[str | None] = mapped_column(
        termination_enum
    )  # normalized: checkmate|resignation|timeout|draw|abandoned|unknown

    # Time control
    time_control_str: Mapped[str | None] = mapped_column(String(50))  # raw string e.g. "600+0"
    time_control_bucket: Mapped[str | None] = mapped_column(
        time_control_bucket_enum
    )  # "bullet"|"blitz"|"rapid"|"classical"
    time_control_seconds: Mapped[int | None]  # estimated duration in seconds (base + inc*40)
    # starting clock in seconds. SMALLINT is safe for live chess (SEED-041 §B3:
    # prod max 10,800; daily/correspondence games store NULL) but would overflow
    # the 32,767 ceiling if daily base times were ever stored here.
    base_time_seconds: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    increment_seconds: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # increment per move in seconds (Float: chess.com emits fractional values like 0.1s)

    # Flags
    rated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_computer_game: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Player info (absolute, not user-relative)
    white_username: Mapped[str | None] = mapped_column(String(100))
    black_username: Mapped[str | None] = mapped_column(String(100))
    white_rating: Mapped[int | None]
    black_rating: Mapped[int | None]

    # Opening info (from platform, display only — not used for position matching)
    opening_name: Mapped[str | None] = mapped_column(String(200))
    opening_eco: Mapped[str | None] = mapped_column(String(10))

    # Exact half-move count (replaces move_count, Phase 114.1)
    ply_count: Mapped[int | None] = mapped_column(nullable=True)

    # Final position FEN (piece placement only, from board.board_fen())
    result_fen: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Engine analysis: game-level accuracy from chess.com (NULL for lichess and unanalyzed games)
    white_accuracy: Mapped[float | None] = mapped_column(REAL, nullable=True)
    black_accuracy: Mapped[float | None] = mapped_column(REAL, nullable=True)

    # Lichess analysis metrics: ACPL and move quality counts per color
    # (NULL for chess.com games and unanalyzed lichess games)
    white_acpl: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    black_acpl: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    white_inaccuracies: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    black_inaccuracies: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    white_mistakes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    black_mistakes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    white_blunders: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    black_blunders: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # Timestamps
    played_at: Mapped[datetime.datetime | None]
    imported_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
    # Phase 91: tracks per-game Stockfish eval completion. NULL = pending (cold drain
    # will process), non-NULL = completed. Set by the cold drain after evaluating entry
    # plies, or immediately by the hot lane for games whose entry plies need no engine work
    # (e.g. lichess games with pre-supplied evals, or engine returned (None, None) for every ply).
    evals_completed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    # Phase 116 EVAL-05 / D-116-05: full-game (all-ply) analysis completion marker.
    # Mirrors evals_completed_at exactly. NULL = pending for the full-ply drain.
    # The pending-pick partial index (WHERE NULL, on id) lives in the migration only,
    # matching the ix_games_evals_pending pattern (Critical Constraint 5).
    full_evals_completed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    # D-117-06: provenance — set ONLY at import when lichess %evals are ingested;
    # NULL = engine-written, transplant-safe for WR-02 (repointed from white_blunders
    # by D-117-07). This is the "these evals are lichess post-move %evals" durable signal,
    # decoupled from the oracle count columns so engine-filled games don't blur it.
    lichess_evals_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    # D-117-12: PV/best_move completion dimension, parallel to full_evals_completed_at.
    # A game can be eval-complete but PV-missing (pre-117-analyzed games lack best_move).
    # Set after best_move is written for all plies in a game. NULL = PV not yet captured.
    # The ix_games_full_pv_pending partial index (WHERE NULL) lives in the migration.
    full_pv_completed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    positions: Mapped[list["GamePosition"]] = relationship(  # ty: ignore[unresolved-reference]
        back_populates="game", cascade="all, delete-orphan"
    )

    @hybrid_property
    def is_analyzed(self) -> bool:
        """True when this game has full-game move-quality analysis (flaw counts populated).

        Cheap detector: `white_blunders` is non-NULL when per-color move-quality counts
        are present — either ingested from Lichess at import time (lichess_evals_at IS NOT
        NULL) or computed by the full-ply eval drain (Phase 117+, D-117-09). Chess.com
        games without per-game analysis return False. Used as the analyzed/total
        denominator for the flaw-stats coverage badge and the you-vs-opponent comparison.

        Note (D-117-09): after Phase 117 this property returns True for engine-analyzed
        games as well as Lichess games with computer analysis — it is no longer
        Lichess-only.
        """
        return self.white_blunders is not None

    @is_analyzed.inplace.expression
    @classmethod
    def _is_analyzed_expression(cls) -> sa.ColumnElement[bool]:
        return cls.white_blunders.isnot(None)
