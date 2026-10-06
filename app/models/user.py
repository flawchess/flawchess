"""User model for FastAPI-Users with integer primary key and OAuth accounts."""

from datetime import datetime
from typing import Any, List

from fastapi_users.db import SQLAlchemyBaseUserTable
from sqlalchemy import Boolean, DateTime, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
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

    # Phase 230 D-16: opt-out from the weekly Train leaderboards. Server-persisted,
    # written only through PUT /users/me/profile. Default false: every registered
    # user appears on the boards until they opt out.
    leaderboard_hidden: Mapped[bool] = mapped_column(
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

    # --- First-touch acquisition attribution (growth report 2026-09-15, item 16) ---
    # Where this user's browser first arrived from, captured client-side on the first
    # page load (lib/firstTouch.ts) and submitted once right after the account is
    # created (guest, email or Google). Guest promotion keeps the row, so a promoted
    # guest keeps the source of the original guest visit. Keys (all optional strings):
    # referrer_host (external host only, never a full URL), utm_source, utm_medium,
    # utm_campaign, landing_path (pathname, no query or fragment).
    # SQL NULL = never recorded (pre-feature accounts, storage blocked); an object with
    # no referrer_host/utm_* keys = recorded, arrived direct.
    # none_as_null: without it a Python None is written as JSON null, which an
    # `IS NULL` predicate does not match (the first-write-wins guard would break).
    first_touch: Mapped[dict[str, str] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True, default=None
    )

    # --- Per-ask prompt state (Phase 234, SEED-191) ---
    # One JSON object keyed by ask id (feedback ask = "feedback_v1"). The shape of
    # each entry is validated by FeedbackAskState in app/schemas/feedback_ask.py
    # instead of a DB CHECK. Written ONLY by the atomic guarded UPDATEs in
    # app/repositories/feedback_ask_repository.py (never read-modify-write in
    # Python). NOT NULL with a '{}' default, deliberately without none_as_null: a
    # None must fail loudly instead of becoming a JSON null. `default=dict` covers
    # ORM inserts (registration, guest creation, test fixtures).
    prompt_state: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb"), default=dict
    )

    oauth_accounts: Mapped[List["OAuthAccount"]] = relationship(  # ty: ignore[unresolved-reference]
        "OAuthAccount", lazy="joined"
    )
