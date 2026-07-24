"""ORM model for user_import_settings table.

Phase 186 Plan 01 (IMPORT-01): one settings row per user controlling which
time-control (TC) buckets are imported and the per-(platform, TC) backlog
game cap (D-01/D-02). Single shared setting across both platforms.

Columns:
  user_id (PK): FK to users.id with ON DELETE CASCADE. One row per user.
  tc_bullet / tc_blitz / tc_rapid / tc_classical: whether games in that TC
    bucket are imported (both forward-incremental sync and backward backfill,
    D-02). Correspondence games ride the classical bucket (D-14, no 5th
    toggle) -- normalization.py normalizes them there already.
  game_cap: per-(platform, TC) backlog budget in {1000, 3000, 5000} (D-01).
    Applies ONLY to pre-signup backlog (played_at < users.created_at, D-02);
    post-anchor games always import uncapped.
  chesscom_backfill_oldest_year / chesscom_backfill_oldest_month /
    lichess_backfill_oldest_ms: nullable backward-walk resume cursors, read and
    written by Plan 02's backward-fetch backfill path (shipped in this same
    phase -- see `import_service._run_chesscom_backward_pass` /
    `_run_lichess_backward_pass` and
    `user_import_settings_repository.get_chesscom_backfill_cursor` /
    `get_lichess_backfill_cursor` / `update_chesscom_backfill_cursor` /
    `update_lichess_backfill_cursor`). Persisted here (not derived from
    MIN(played_at)) per 186-RESEARCH.md Pitfall 1: a fetch attempt that yields
    zero TC-matching games must still advance the cursor, or Sync would
    re-fetch the same already-attempted period forever.

New users get product defaults (bullet=false, blitz/rapid/classical=true,
game_cap=1000) via `user_import_settings_repository.DEFAULT_IMPORT_SETTINGS`,
applied at the application layer on first GET/PATCH (create-on-first-touch,
D-16 guest/registered parity -- one code path). Existing users (at migration
time) are grandfathered to all four TCs enabled + game_cap=5000 by the
migration's one-time `INSERT ... SELECT` (D-13, confirmed locked decision).
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserImportSettings(Base):
    """One row per user: TC import toggles + backlog game cap.

    Phase 186 Plan 01. See module docstring for the full column contract and
    the D-01/D-02/D-13/D-14/D-15/D-16 decisions this schema encodes.
    """

    __tablename__ = "user_import_settings"
    __table_args__ = (
        CheckConstraint("game_cap IN (1000, 3000, 5000)", name="ck_user_import_settings_cap"),
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tc_bullet: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tc_blitz: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tc_rapid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tc_classical: Mapped[bool] = mapped_column(Boolean, nullable=False)
    game_cap: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Backward-fetch backfill resume cursors (Plan 02, shipped in this same phase).
    # Nullable: no cursor persisted yet == no backward walk has run for this
    # user+platform. See module docstring for the read/write call sites.
    chesscom_backfill_oldest_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    chesscom_backfill_oldest_month: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    lichess_backfill_oldest_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


__all__ = ["UserImportSettings"]
