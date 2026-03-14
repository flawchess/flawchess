import datetime

from sqlalchemy import Boolean, String, Text, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        UniqueConstraint("platform", "platform_game_id", name="uq_games_platform_game_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)  # FK to users in Phase 4

    # Platform identity
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # "chess.com" | "lichess"
    platform_game_id: Mapped[str] = mapped_column(String(100), nullable=False)
    platform_url: Mapped[str | None] = mapped_column(String(500))

    # Game content
    pgn: Mapped[str] = mapped_column(Text, nullable=False)
    variant: Mapped[str] = mapped_column(String(50), nullable=False, default="Standard")

    # Result
    result: Mapped[str] = mapped_column(String(10), nullable=False)    # "1-0" | "0-1" | "1/2-1/2"
    user_color: Mapped[str] = mapped_column(String(5), nullable=False)  # "white" | "black"

    # Time control
    time_control_str: Mapped[str | None] = mapped_column(String(50))   # raw string e.g. "600+0"
    time_control_bucket: Mapped[str | None] = mapped_column(String(20))  # "bullet"|"blitz"|"rapid"|"classical"
    time_control_seconds: Mapped[int | None]                             # estimated duration in seconds

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

    # Move count (total full moves in the game)
    move_count: Mapped[int | None] = mapped_column(nullable=True)

    # Timestamps
    played_at: Mapped[datetime.datetime | None]
    imported_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )

    positions: Mapped[list["GamePosition"]] = relationship(  # type: ignore[name-defined]
        back_populates="game", cascade="all, delete-orphan"
    )
