"""rename game_flaws.is_lucky_escape -> is_lucky

Revision ID: e1a7c93b6f02
Revises: b3c5e9f2a104
Create Date: 2026-06-08

Renames the opportunity-family boolean column to match the shortened `lucky`
flaw tag (was `lucky-escape`). A plain column rename preserves existing data, so
no backfill is needed (unlike the impact-column swap in b3c5e9f2a104).

Literal column names only — migrations are version-pinned snapshots and must NOT
import live app constants (project rule, same as a7e0b4796501).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1a7c93b6f02"
down_revision: str = "b3c5e9f2a104"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.alter_column("game_flaws", "is_lucky_escape", new_column_name="is_lucky")


def downgrade() -> None:
    op.alter_column("game_flaws", "is_lucky", new_column_name="is_lucky_escape")
