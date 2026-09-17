"""User model for FastAPI-Users with integer primary key and OAuth accounts."""

from datetime import datetime
from typing import List

from fastapi_users.db import SQLAlchemyBaseUserTable
from sqlalchemy import Boolean, DateTime, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Platform usernames (auto-saved on import, user-editable via profile)
    chess_com_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lichess_username: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Account timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Guest session flag — True for anonymous users created via POST /auth/guest/create
    is_guest: Mapped[bool] = mapped_column(default=False, server_default=text("false"))

    # Beta feature flag — controls access to experimental features (e.g. Endgame Insights in v1.11).
    # Default false; flipped via direct DB operation for a hand-picked cohort per BETA-01.
    beta_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        default=False,
    )

    # Records WHEN a row that began life as a guest session was promoted in place
    # to a full account. NULL means never promoted. Set by
    # app/services/guest_service.py on both promotion paths (Google and
    # email/password), so the activity dashboard can count guest conversions
    # (and, unlike a boolean, chart conversion timing) without inspecting
    # credential state.
    promoted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # --- Retained facts (QTE-01..04) ---
    # These three columns deliberately SURVIVE the games/import_jobs purge performed by
    # guest_cleanup_service._purge_guest (30-day guest inactivity sweep) and
    # DELETE /api/games. Both purge paths intentionally delete `games` and `import_jobs`
    # rows while keeping the `users` row (D-05, Phase 187), so without a retained fact the
    # Activity dashboard cannot distinguish "never imported" from "imported, then purged".

    # Timestamp of the FIRST successful `POST /api/imports` for this user. First-write-wins
    # (never overwritten by a later import) so it survives any number of subsequent purges.
    first_import_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Lifetime count of games ever imported for this user, incremented in the same
    # transaction as each import batch persist. Never decremented by a purge, so it
    # survives `DELETE /api/games` and guest cleanup deleting the live `games` rows.
    lifetime_games_imported: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
        default=0,
    )

    # Set when this user's `games` and `import_jobs` rows are purged (guest 30-day
    # cleanup, or the user calling `DELETE /api/games`). NULL means never purged. Lets
    # the Activity dashboard exclude purged users from "never imported" cohorts instead
    # of miscounting them.
    games_purged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    oauth_accounts: Mapped[List["OAuthAccount"]] = relationship(  # ty: ignore[unresolved-reference]
        "OAuthAccount", lazy="joined"
    )
