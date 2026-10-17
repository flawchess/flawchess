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
        # Unique index on (id, user_id) is the target of the
        # game_positions composite FK (game_id, user_id) -> games(id, user_id).
        # Built CONCURRENTLY in the migration; declared here as a unique index
        # (not a constraint) to match the migration and keep metadata in sync.
        Index("uq_games_id_user_id", "id", "user_id", unique=True),
        # (user_id, played_at DESC) lets the recent-games WindowAgg
        # run-condition early-terminate instead of scanning the user's full game
        # history. Replaces the former index=True on user_id (ix_games_user_id) —
        # this index's user_id prefix serves every user_id-only lookup too.
        Index("ix_games_user_played_at", "user_id", sa.text("played_at DESC")),
        # Partial index for the per-import-batch pending-evals gate
        # (users_with_no_pending_evals_or_imports). Near-zero size at steady state. Keep
        # ix_games_evals_pending (on id) for the id-ordered drain poll.
        Index(
            "ix_games_user_evals_pending",
            "user_id",
            postgresql_where=sa.text("evals_completed_at IS NULL"),
        ),
        # ix_games_needs_engine_full_evals (full_evals_completed_at IS NULL AND
        # lichess_evals_at IS NULL, the tier-3 recency-lottery pool) is created in
        # migration 20260614_150000 only; it has no Index() declaration here.
        # Partial index backing the tier-3 residual-fallback pick in
        # eval_queue_service._claim_tier3_derived (best-move-backfill-only lichess-eval
        # games). Without it every remote-worker idle poll seq-scanned all of games
        # (~300 ms, the dominant query by total time). Originally created (predicate
        # full_evals_completed_at IS NULL AND lichess_evals_at IS NOT NULL) in migration
        # 20260623210000; broadened to full_pv_completed_at IS NULL (the residual
        # fallback now also covers eval-complete-but-PV-incomplete lichess games) and
        # renamed in migration 20260716171823.
        Index(
            "ix_games_lichess_pv_backfill_pending",
            "user_id",
            postgresql_where=sa.text(
                "lichess_evals_at IS NOT NULL AND full_pv_completed_at IS NULL"
            ),
        ),
        # Partial index backing the tier-4b
        # best-move-backfill lottery predicate in
        # eval_queue_service._claim_tier4_bestmove — mirrors
        # ix_games_lichess_pv_backfill_pending's shape (single user_id column,
        # partial WHERE). postgresql_where text MUST stay byte-identical to the
        # migration's create_index call, or alembic check reports drift.
        # Predicate mirrors _claim_tier4_bestmove's live predicate exactly.
        Index(
            "ix_games_bestmove_backfill_pending",
            "user_id",
            postgresql_where=sa.text(
                "full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL"
            ),
        ),
        # Partial index backing the tier-4 blob-backfill lottery predicate
        # in eval_queue_service._claim_tier4_blob — mirrors
        # ix_games_bestmove_backfill_pending's shape (single user_id column, partial
        # WHERE). postgresql_where text MUST stay byte-identical to the migration's
        # create_index call, or alembic check reports drift.
        Index(
            "ix_games_blob_backfill_pending",
            "user_id",
            postgresql_where=sa.text(
                "full_evals_completed_at IS NOT NULL AND blobs_completed_at IS NULL"
            ),
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
    # The game's starting position when it is NOT the
    # standard one. NULL means the standard start, so `initial_fen IS NULL` is
    # the canonical "safe to replay from chess.Board()" predicate — that is what
    # query_opening_transitions filters its sample representative on, and what
    # /analysis game mode reads to seed a custom-start game's board.
    # Populated by normalization.extract_initial_fen (chess.com/lichess, from the
    # [SetUp "1"][FEN ...] header pair) and by normalize_pasted_game (from the
    # already-derived root). Deliberately NOT indexed: the IS NULL predicate
    # matches ~99.95% of rows and Game is already joined in its only reader.
    initial_fen: Mapped[str | None] = mapped_column(Text)

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
    # starting clock in seconds. SMALLINT is safe for live chess (prod max
    # 10,800; daily/correspondence games store NULL) but would overflow the
    # 32,767 ceiling if daily base times were ever stored here.
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

    # Exact half-move count
    ply_count: Mapped[int | None] = mapped_column(nullable=True)

    # Final position FEN (piece placement only, from board.board_fen())
    result_fen: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Our uniform lichess-formula computed game-level accuracy
    # (percent, 0-100), populated by the compute path (live hook + backfill) for
    # every analyzed game regardless of source platform. NULL until computed.
    white_accuracy: Mapped[float | None] = mapped_column(REAL, nullable=True)
    black_accuracy: Mapped[float | None] = mapped_column(REAL, nullable=True)

    # Our uniform lichess-formula computed game-level ACPL
    # (average centipawn loss), populated by the compute path for every
    # analyzed game regardless of source platform. NULL until computed.
    white_acpl: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    black_acpl: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # Platform-reported values preserved at import (chess.com
    # accuracy for chess.com games, lichess accuracy+ACPL for lichess games) —
    # sparse, validation/comparison signal only, no longer the canonical values.
    white_accuracy_imported: Mapped[float | None] = mapped_column(REAL, nullable=True)
    black_accuracy_imported: Mapped[float | None] = mapped_column(REAL, nullable=True)
    white_acpl_imported: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    black_acpl_imported: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # Client-supplied persona identifier for bot games
    # played against a named persona (e.g. "attacker-1200"). NULL for custom-mode
    # bot games and for every pre-existing row (no backfill, no retroactive
    # persona identity). No FK/CHECK — the persona roster is a frontend-only,
    # milestone-evolving TS module, not a DB-tracked entity.
    persona_id: Mapped[str | None] = mapped_column(String(30), nullable=True)

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
    # Tracks per-game Stockfish eval completion. NULL = pending (the entry-ply lane
    # will process), non-NULL = completed. Set by the entry-ply lane after evaluating
    # entry plies, or immediately by the hot lane for games whose entry plies need no engine work
    # (e.g. lichess games with pre-supplied evals, or engine returned (None, None) for every ply).
    evals_completed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    # Full-game (all-ply) analysis completion marker.
    # Mirrors evals_completed_at exactly. NULL = pending for the full-ply drain.
    # The pending-pick partial index (WHERE NULL, on id) lives in the migration only,
    # matching the ix_games_evals_pending pattern.
    full_evals_completed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    # Provenance — set ONLY at import when lichess %evals are ingested;
    # NULL = engine-written, transplant-safe. This is the "these evals are lichess
    # post-move %evals" durable signal, decoupled from the flaw count columns so
    # engine-filled games don't blur it.
    lichess_evals_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    # PV/best_move completion dimension, parallel to full_evals_completed_at.
    # A game can be eval-complete but PV-missing (games analyzed before best_move was
    # stored lack it).
    # Set after best_move is written for all plies in a game. NULL = PV not yet captured.
    # The ix_games_full_pv_pending partial index (WHERE NULL) lives in the migration.
    full_pv_completed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    # Completion marker for the best-move pass (game_best_moves candidate
    # rows). Stamped by apply_completion_decision
    # on BOTH the go-forward path and the tier-4b backfill path, ONLY when
    # maia_engine.is_maia_available() is True at stamp time (guardrail: a
    # Maia-absent backend must never stamp this, or affected games would be
    # permanently locked out of the tier-4b lottery with zero best-move rows).
    # NULL = best-move pass not yet attempted (or attempted with Maia absent).
    # Self-termination predicate: full_pv_completed_at IS NOT NULL AND
    # best_moves_completed_at IS NULL (the tier-4b lottery covers lichess-eval
    # games too; the stamp itself is source-agnostic, mirroring
    # full_pv_completed_at).
    best_moves_completed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    # Per-GAME rollup of a per-FLAW-PLY condition — unlike the four
    # completion columns above (naturally per-game), this one summarizes
    # `game_flaws.allowed_pv_lines`. The authoritative predicate is "no
    # `game_flaws` row for this game has `allowed_pv_lines IS NULL`". Maintained
    # BIDIRECTIONALLY by `_refresh_blobs_completed` (eval_apply.py): stamped
    # `now()` when every flaw ply's blob is written, cleared back to NULL when a
    # reclassification (the diff/upsert in _classify_and_fill_oracle) inserts a
    # fresh NULL-blob ply on an already-stamped game. NULL means the tier-4
    # blob-backfill lottery (_claim_tier4_blob) may claim this game.
    blobs_completed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    # Per-game counter of full-drain ticks that left a non-terminal
    # hole (eval_cp IS NULL AND eval_mate IS NULL on a non-terminal ply). The drain
    # withholds full_evals_completed_at until holes fill or this counter reaches
    # MAX_EVAL_ATTEMPTS (eval_drain.py). Server default '0' backfills existing rows.
    full_eval_attempts: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0"
    )
    # Entry-ply (import-time) lease for remote-worker fan-out.
    # Both are NULL = unclaimed (correct default; no backfill needed).
    # ix_games_evals_pending (WHERE evals_completed_at IS NULL) backs the claim and
    # its pending probe.
    # Partial indexes for these columns live in the migration only (per ix_games_evals_pending
    # convention above — declared in migration, not in __table_args__).
    entry_eval_lease_expiry: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    entry_eval_leased_by: Mapped[str | None] = mapped_column(
        sa.String(16),
        nullable=True,  # Worker-id label; VARCHAR(16) not TEXT
    )

    positions: Mapped[list["GamePosition"]] = relationship(  # ty: ignore[unresolved-reference]
        back_populates="game", cascade="all, delete-orphan"
    )

    @hybrid_property
    def is_analyzed(self) -> bool:
        """True when this game has full-game move-quality analysis (flaw counts populated).

        Cheap detector: `white_blunders` is non-NULL when per-color move-quality counts
        are present — either ingested from Lichess at import time (lichess_evals_at IS NOT
        NULL) or computed by the full-ply eval drain. Chess.com
        games without per-game analysis return False. Used as the analyzed/total
        denominator for the flaw-stats coverage badge and the you-vs-opponent comparison.

        Note: this property returns True for engine-analyzed games as well as Lichess
        games with computer analysis — it is not Lichess-only.
        """
        return self.white_blunders is not None

    @is_analyzed.inplace.expression
    @classmethod
    def _is_analyzed_expression(cls) -> sa.ColumnElement[bool]:
        return cls.white_blunders.isnot(None)

    @hybrid_property
    def has_engine_full_evals(self) -> bool:
        """True when all-ply evals were written by OUR engine, not ingested from Lichess.

        `full_evals_completed_at` marks all-ply eval completion from ANY source, so it is
        also set for Lichess games imported with %evals (a migration
        backfill mirrored `evals_completed_at` into it). `lichess_evals_at IS NULL` is the
        provenance gate: NULL = engine-written. This is the canonical predicate
        for "games analyzed by our Stockfish" — distinct from `is_analyzed`, which is also
        True for Lichess freebies. Eval and PV are written in the same drain pass, so this
        does not separately gate `full_pv_completed_at`.
        """
        return self.full_evals_completed_at is not None and self.lichess_evals_at is None

    @has_engine_full_evals.inplace.expression
    @classmethod
    def _has_engine_full_evals_expression(cls) -> sa.ColumnElement[bool]:
        return sa.and_(
            cls.full_evals_completed_at.isnot(None),
            cls.lichess_evals_at.is_(None),
        )
