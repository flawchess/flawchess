import datetime

import sqlalchemy as sa
from sqlalchemy import BigInteger, ForeignKey, Index, SmallInteger, String
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# Tier meanings (no magic numbers in consumers — use these constants):
#   TIER_EXPLICIT = 1   — explicit user request (highest priority)
#   TIER_AUTO_WINDOW = 2 — automatic window (e.g. recent activity)
#   TIER_IDLE_BACKLOG = 3 — idle-backlog drain (lowest priority)
TIER_EXPLICIT: int = 1
TIER_AUTO_WINDOW: int = 2
TIER_IDLE_BACKLOG: int = 3


class EvalJob(Base):
    """Priority queue / lease table for the full-ply eval drain (QUEUE-01, QUEUE-06).

    Tier ordering: 1 (explicit request) > 2 (auto-window) > 3 (idle backlog).
    Status lifecycle: pending -> leased -> completed | failed.
    Expired leases are requeued to 'pending' by a sweep at the top of each drain tick.

    The partial unique index uq_eval_jobs_game_active enforces at most one active
    (pending or leased) job per game, while allowing re-enqueue after completion.
    RESEARCH Open Question 1 / Pitfall 6.
    """

    __tablename__ = "eval_jobs"
    __table_args__ = (
        # Partial unique: only one active (pending or leased) job per game.
        # Completed/failed jobs don't block re-enqueue.
        # SQLAlchemy UniqueConstraint cannot express a partial where-clause so
        # this is expressed as a unique Index with postgresql_where.
        Index(
            "uq_eval_jobs_game_active",
            "game_id",
            unique=True,
            postgresql_where=sa.text("status IN ('pending', 'leased')"),
        ),
        # Pick index: tier-ordered, per-user, recency-ordered (QUEUE-01 / QUEUE-02).
        Index(
            "ix_eval_jobs_pick",
            "tier",
            "user_id",
            "created_at",
            postgresql_where=sa.text("status = 'pending'"),
        ),
        # Lease-expiry sweep index (requeue expired leases).
        Index(
            "ix_eval_jobs_leased",
            "lease_expiry",
            postgresql_where=sa.text("status = 'leased'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Tier 1=explicit, 2=auto-window, 3=idle-backlog (see TIER_* constants above)
    tier: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # QUEUE-08: guest users are never enqueued — user_id references a real account.
    # CASCADE: deleted user's queued jobs vanish automatically (no orphan rows).
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # CASCADE: deleted game's job vanishes automatically.
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False)

    # Status string: pending | leased | completed | failed.
    # Literal-typed at the service layer; stored as varchar(20) in DB.
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")

    # Worker identity that holds the lease (e.g. "server-pool", future "browser-abc").
    # NULL when status is 'pending'.
    leased_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Absolute expiry time for the current lease; NULL when not leased.
    lease_expiry: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
