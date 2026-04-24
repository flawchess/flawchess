"""drop llm_logs system_prompt

Revision ID: c72eeee6a61a
Revises: d57b635e50bb
Create Date: 2026-04-23 05:22:28.148429+00:00

Drops `system_prompt` column from `llm_logs`. `prompt_version` already
identifies which system prompt was in effect — the actual text lives in
`app/prompts/endgame_insights.md` under version control, so duplicating
kilobytes of it per row adds no recoverable information.
"""

from alembic import op
import sqlalchemy as sa


revision: str = "c72eeee6a61a"
down_revision: str | None = "d57b635e50bb"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_column("llm_logs", "system_prompt")


def downgrade() -> None:
    op.add_column(
        "llm_logs",
        sa.Column("system_prompt", sa.Text(), nullable=False, server_default=""),
    )
    op.alter_column("llm_logs", "system_prompt", server_default=None)
