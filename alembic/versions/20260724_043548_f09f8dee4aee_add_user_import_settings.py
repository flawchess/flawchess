"""add user_import_settings

Phase 186 Plan 01 (IMPORT-01/IMPORT-02, D-13 confirmed via checkpoint 2026-07-24):
creates the per-user import-settings table (TC toggles + backlog game cap +
backward-walk cursor columns -- read/written by Plan 02's backward-fetch
backfill, shipped in this same phase) and grandfathers every EXISTING user
(as of this migration) to all four TCs enabled + game_cap=5000 via a one-time
`INSERT ... SELECT`. Existing users keep unchanged sync behavior; being over
budget only means no further backfill (D-13). New users (created after this
migration runs) get product defaults (bullet=false, blitz/rapid/classical=true,
game_cap=1000) from the application layer on first GET/PATCH
(`user_import_settings_repository.DEFAULT_IMPORT_SETTINGS`), NOT from this
migration.

D-13 is a locked, one-way decision -- confirmed via the checkpoint:decision
gate at the top of 186-01-PLAN.md before this file was written.

Revision ID: f09f8dee4aee
Revises: 411a8de89c4b
Create Date: 2026-07-24 04:35:48.604494+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f09f8dee4aee"
down_revision: Union[str, Sequence[str], None] = "411a8de89c4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create user_import_settings, then grandfather existing users (D-13)."""
    op.create_table(
        "user_import_settings",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tc_bullet", sa.Boolean(), nullable=False),
        sa.Column("tc_blitz", sa.Boolean(), nullable=False),
        sa.Column("tc_rapid", sa.Boolean(), nullable=False),
        sa.Column("tc_classical", sa.Boolean(), nullable=False),
        sa.Column("game_cap", sa.SmallInteger(), nullable=False),
        sa.Column("chesscom_backfill_oldest_year", sa.SmallInteger(), nullable=True),
        sa.Column("chesscom_backfill_oldest_month", sa.SmallInteger(), nullable=True),
        sa.Column("lichess_backfill_oldest_ms", sa.BigInteger(), nullable=True),
        sa.CheckConstraint("game_cap IN (1000, 3000, 5000)", name="ck_user_import_settings_cap"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    # D-13 (checkpoint-confirmed): grandfather every existing user to all four
    # TCs enabled + game_cap=5000. One-way -- only ever runs once, against the
    # users table as it exists at migration time. Users created AFTER this
    # migration runs get application-layer defaults instead (never touch this row).
    op.execute(
        sa.text(
            "INSERT INTO user_import_settings "
            "(user_id, tc_bullet, tc_blitz, tc_rapid, tc_classical, game_cap) "
            "SELECT id, true, true, true, true, 5000 FROM users"
        )
    )


def downgrade() -> None:
    """Drop user_import_settings."""
    op.drop_table("user_import_settings")
