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
