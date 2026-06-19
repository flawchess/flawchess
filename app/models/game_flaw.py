"""GameFlaw ORM model — derived materialization table for M+B flaws (SEED-038).

Stores one row per user mistake or blunder, keyed by (user_id, game_id, ply).
Inaccuracies are never stored here (D-03).

Phase 112 (D-07): dropped es_before, es_after, move_san — those display values
are now sourced at query time from a game_positions join (D-08). The fen column
is retained: game_positions stores only Zobrist hashes (no FEN column), so fen
is the one denormalized display column that cannot be recovered without PGN replay.
"""

from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GameFlaw(Base):
    __tablename__ = "game_flaws"
    __table_args__ = (
        # Secondary index for severity scans (SEED-038 indexing guidance).
        # Covers: filter by user_id + severity (set-membership) for Games-tab EXISTS
        # and Flaws-tab SELECT queries without a full table scan per user.
        Index("ix_game_flaws_user_severity", "user_id", "severity"),
    )

    # Natural composite PK: (user_id, game_id, ply) — mirrors game_positions PK (SEED-035).
    # The key is provably unique (one row per user/game/half-move for M+B only).
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, primary_key=True
    )
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
        index=True,
    )
    ply: Mapped[int] = mapped_column(SmallInteger, nullable=False, primary_key=True)

    # Severity: 1=mistake, 2=blunder. Filtered via set-membership (severity IN (...)).
    # 0=inaccuracy is NEVER stored here per D-03 — game_flaws is M+B only.
    severity: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Tempo family: 0=low-clock, 1=hasty, 2=unrushed; NULL when no clock data.
    tempo: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)

    # Phase family: 0=opening, 1=middlegame, 2=endgame (denormalized from game_positions.phase).
    phase: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Opportunity family (boolean typed columns — OR-within-family semantics per SEED-038).
    is_miss: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_lucky: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Impact family
    is_reversed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_squandered: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # fen: board_fen() BEFORE the flawed move — the one denormalized display column
    # that cannot be recovered without PGN replay (game_positions stores only Zobrist
    # hashes, no FEN; see Pitfall 4 in 112-CONTEXT.md). Used by the miniboard to render
    # the decision-point position and compute move_san → arrow squares.
    # Dropped in Phase 112 (D-07): es_before, es_after, move_san — now sourced from
    # a game_positions join in query_flaws (D-08, library_repository.py).
    fen: Mapped[str] = mapped_column(String, nullable=False)

    # Tactic family (Phase 124 — D-01): all nullable SmallInteger.
    # Two orientations, each a 4-tuple:
    #   allowed_* — the refutation from the flaw_ply+1 PV (the move the *opponent* played
    #               to punish the flaw); pov = board_after_flaw.turn (Phase 124/125/127 tags).
    #   missed_*  — the "instead-of" tag from the flaw_ply PV (the engine's best continuation
    #               for the flaw-maker at the decision position); pov = board_before.turn.
    #               NULL on pre-Phase-128 rows until the missed-pass backfill runs (Phase 128 D-11).
    #
    # Per D-05: allowed_tactic_depth is the loop index within the flaw_ply+1 PV;
    # missed_tactic_depth is the loop index within the flaw_ply PV (one ply earlier,
    # at the decision position). Both are detector-loop indices within their own PV —
    # neither is an absolute game ply. The Phase 129 depth slider must treat them
    # consistently (same unit, different PV source).
    #
    # tactic_motif: TacticMotifInt enum (1-24); NULL = no detector fired.
    # tactic_piece: python-chess PieceType (1=PAWN,2=KNIGHT,3=BISHOP,4=ROOK,5=QUEEN,6=KING)
    #               per-motif semantic per D-12; NULL for ambiguous cases.
    # tactic_confidence: winner-confidence 0-100; NULL when tactic_motif is NULL.
    # tactic_depth: loop index within the PV when the motif fires; NULL when tactic_motif is NULL.
    allowed_tactic_motif: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    allowed_tactic_piece: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    allowed_tactic_confidence: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    allowed_tactic_depth: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    missed_tactic_motif: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    missed_tactic_piece: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    missed_tactic_confidence: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    missed_tactic_depth: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
