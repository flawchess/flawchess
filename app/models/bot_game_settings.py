"""One-to-one bot-settings side table for flawchess games (Phase 167, D-16).

Records the bot config that produced a stored `platform='flawchess'` game, so a
later milestone can curve-fit measured player ratings against bot settings
(CALX-01). TEXT + CHECK for rating_source per CLAUDE.md DB rules (no native
PostgreSQL ENUM for a low-cardinality domain column).
"""

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Text
from sqlalchemy.dialects.postgresql import REAL
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BotGameSettings(Base):
    """Bot config recorded alongside a stored flawchess game (D-16)."""

    __tablename__ = "bot_game_settings"
    __table_args__ = (
        CheckConstraint(
            "rating_source IN ('lichess', 'chesscom', 'blended')",
            name="ck_bot_game_settings_rating_source",
        ),
    )

    # PK == FK to games.id — one-to-one, cascades on game delete (mandatory FK/ondelete).
    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    nominal_elo: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # b in [0, 1] blend from Phase 166 D-01 — NOT a temperature.
    play_style_blend: Mapped[float] = mapped_column(REAL, nullable=False)
    # lichess TC preset string, e.g. "3+2"; base/inc already on games.base_time_seconds/increment_seconds.
    tc_preset: Mapped[str] = mapped_column(Text, nullable=False)
    # NULL when the user has no rating anchor for this TC bucket (D-06); otherwise
    # derived from anchor provenance (D-07).
    rating_source: Mapped[str | None] = mapped_column(Text, nullable=True)
