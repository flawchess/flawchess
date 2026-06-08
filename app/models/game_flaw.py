"""GameFlaw ORM model — derived materialization table for M+B flaws (SEED-038).

Stores one row per user mistake or blunder, keyed by (user_id, game_id, ply).
Inaccuracies are never stored here (D-03).  The display payload (es_before,
es_after, move_san, fen) is persisted at classify time so the Flaws-tab
miniboard renders without replaying PGN per request.
"""

from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Index, SmallInteger, String
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

    # Display payload (SEED-038: stored at classify time to avoid O(page × game_length)
    # PGN replay per request).
    es_before: Mapped[float] = mapped_column(Float, nullable=False)
    es_after: Mapped[float] = mapped_column(Float, nullable=False)
    move_san: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    fen: Mapped[str] = mapped_column(
        String, nullable=False
    )  # board_fen() BEFORE the flawed move (miniboard decision point + arrow source)
