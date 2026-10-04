"""ORM models for the weekly Train leaderboard medal snapshot (Phase 231).

`train_weekly_standings` freezes each closed ISO week's PUBLIC final standings, one
row per (week, board, user), so a later opt-out or account deletion never changes who
won a past week (D-01). A row exists for the public board exactly: Points rows for
every registered, non-hidden user with at least one solve; Accuracy rows only for
qualified users (20+ non-filler solves). Hidden users, guests and tentative Accuracy
users get no row.

The `medal` column is written explicitly from the competition rank and is the ONLY
medal source. Never derive a medal from `final_rank` at read time: a zero-value entry
keeps its rank but earns no medal (D-05), which `final_rank <= 3` would get wrong.

`train_weekly_finalizations` holds one marker row per finalized week, including weeks
with no eligible entrants (those write no standings rows, so "finalized" cannot be
inferred from the standings table). Inserting the marker `ON CONFLICT DO NOTHING
RETURNING` is also the lock that serializes concurrent finalizers.

Deletion semantics (locked, GDPR): `train_weekly_standings.user_id` is
`ON DELETE SET NULL`, and a database trigger, `trg_train_weekly_standings_erase_name`
(created by migration e3a8c5f17b20, invisible to the ORM), rewrites `display_name` to
"Deleted user" in the same statement. No application code path deletes a registered
account (it is a manual operator `DELETE FROM users`), so only the database can erase
the stored name reliably. PostgreSQL treats NULL user_ids as distinct in the unique
constraint, so two deleted users' rows in one week never collide.
"""

from __future__ import annotations

import datetime
from enum import IntEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Medal(IntEnum):
    """Stored medal. The value is the competition rank that earns it."""

    GOLD = 1
    SILVER = 2
    BRONZE = 3


class TrainWeeklyFinalization(Base):
    """One row per finalized ISO week (the Monday, UTC), empty weeks included."""

    __tablename__ = "train_weekly_finalizations"

    week_start: Mapped[datetime.date] = mapped_column(Date, primary_key=True)
    finalized_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TrainWeeklyStanding(Base):
    """One public final-standings row per (week, board, user)."""

    __tablename__ = "train_weekly_standings"
    __table_args__ = (
        CheckConstraint("board IN ('points', 'accuracy')", name="ck_train_weekly_standings_board"),
        CheckConstraint(
            "medal IS NULL OR medal IN (1, 2, 3)", name="ck_train_weekly_standings_medal"
        ),
        UniqueConstraint(
            "week_start", "board", "user_id", name="uq_train_weekly_standings_week_board_user"
        ),
        Index("ix_train_weekly_standings_user_id", "user_id"),
    )

    # user_id is nullable (SET NULL on account deletion), so it cannot be in the PK.
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # The marker FK means a week's rows can never exist without its marker, and
    # deleting a marker clears the week.
    week_start: Mapped[datetime.date] = mapped_column(
        Date,
        ForeignKey("train_weekly_finalizations.week_start", ondelete="CASCADE"),
        nullable=False,
    )
    # TEXT + CHECK per CLAUDE.md DB rules (low-volume domain column, no native ENUM);
    # typed as LeaderboardBoardKind at the service boundary.
    board: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False)  # as of finalization
    final_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)  # points, or floored accuracy %
    puzzles: Mapped[int] = mapped_column(Integer, nullable=False)
    medal: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    celebrated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
