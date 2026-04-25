import datetime

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    Float,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
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
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

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
    base_time_seconds: Mapped[int | None] = mapped_column(
        SmallInteger, nullable=True
    )  # starting clock in seconds
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

    # Move count (total full moves in the game)
    move_count: Mapped[int | None] = mapped_column(nullable=True)

    # Final position FEN (piece placement only, from board.board_fen())
    result_fen: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Engine analysis: game-level accuracy from chess.com (NULL for lichess and unanalyzed games)
    white_accuracy: Mapped[float | None] = mapped_column(Float(24), nullable=True)
    black_accuracy: Mapped[float | None] = mapped_column(Float(24), nullable=True)

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

    # Eval metadata, populated for Lichess imports; NULL for chess.com (Phase 69 INGEST-06).
    # eval_depth is NULL for all current Lichess API imports: the /api/games/user
    # endpoint does not expose depth in the NDJSON JSON object (evals=true only adds
    # [%eval] PGN annotations). Column is ready if the API surfaces depth in future.
    # eval_source_version is the constant "lichess-pgn" for Lichess imports, NULL otherwise.
    eval_depth: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    eval_source_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Timestamps
    played_at: Mapped[datetime.datetime | None]
    imported_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )

    positions: Mapped[list["GamePosition"]] = relationship(  # ty: ignore[unresolved-reference]
        back_populates="game", cascade="all, delete-orphan"
    )
