"""drop llm_logs flags

Revision ID: 2af113f4790f
Revises: c72eeee6a61a
Create Date: 2026-04-24 12:12:49.157775+00:00

Drops `flags` column from `llm_logs`. The field was planned as a forward-compat
extension point in Phase 64 but never wired up — always written as `[]` at a
single call site and never read anywhere. Same rationale as the earlier
`drop_llm_logs_system_prompt` migration: removing unused columns keeps the
debug/audit table lean.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "2af113f4790f"
down_revision: str | None = "c72eeee6a61a"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_column("llm_logs", "flags")


def downgrade() -> None:
    op.add_column(
        "llm_logs",
        sa.Column("flags", JSONB(), nullable=False, server_default="[]"),
    )
    op.alter_column("llm_logs", "flags", server_default=None)
