"""alter game_flaws impact columns: is_while_ahead/is_result_changing -> is_reversed/is_squandered

Revision ID: b3c5e9f2a104
Revises: a7e0b4796501
Create Date: 2026-06-07

Phase 110 Plan 02: rename the two impact-family boolean columns to match the
new FlawTag taxonomy (reversed/squandered ladder, outcome-independent).

D-01 (planner decision): existing rows cannot be SQL-computed at migration time
because the correct values require replaying PGN + eval — that backfill runs in
Plan 03. The add-NOT-NULL-with-server_default-then-drop-default pattern gives
existing rows a safe `false` placeholder while preserving the no-server_default
convention that sibling columns is_miss / is_lucky_escape follow in the model.

Literal column types only — migrations are version-pinned snapshots and must NOT
import live app constants (project rule, same as a7e0b4796501).
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c5e9f2a104"
down_revision: str = "a7e0b4796501"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Drop the old impact columns.
    op.drop_column("game_flaws", "is_while_ahead")
    op.drop_column("game_flaws", "is_result_changing")

    # Add new impact columns as NOT NULL with a transient server_default=false so
    # existing rows receive a valid boolean placeholder (add-NOT-NULL pattern,
    # precedent 24baa961e5cf). D-01: correct values come from the Plan 03 backfill.
    op.add_column(
        "game_flaws",
        sa.Column("is_reversed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "game_flaws",
        sa.Column("is_squandered", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # Drop the transient server_defaults so new cols match the sibling no-default
    # convention (is_miss / is_lucky_escape carry no server_default in the model).
    op.alter_column("game_flaws", "is_reversed", server_default=None)
    op.alter_column("game_flaws", "is_squandered", server_default=None)


def downgrade() -> None:
    # Drop the new impact columns.
    op.drop_column("game_flaws", "is_squandered")
    op.drop_column("game_flaws", "is_reversed")

    # Re-add the original impact columns with the same transient server_default
    # pattern so existing rows receive a valid placeholder on rollback.
    op.add_column(
        "game_flaws",
        sa.Column(
            "is_result_changing", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "game_flaws",
        sa.Column(
            "is_while_ahead", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )

    # Drop the transient server_defaults to match original create-migration convention.
    op.alter_column("game_flaws", "is_result_changing", server_default=None)
    op.alter_column("game_flaws", "is_while_ahead", server_default=None)
