"""add llm_logs thinking_tokens

Revision ID: d57b635e50bb
Revises: 24baa961e5cf
Create Date: 2026-04-22 15:59:57.750222+00:00

Adds nullable `thinking_tokens` column to `llm_logs`. Populated by the
insights service when the underlying model (e.g. `gemini-3-flash-preview`)
surfaces thought tokens via `usage.details["thoughts_tokens"]`. Null for
providers that don't report thinking tokens (Anthropic, OpenAI, test provider).

Autogenerate noise (type drift REAL→Float, existing index order quirks on
unrelated tables) intentionally omitted — only the thinking_tokens add is in
scope for this migration.
"""

from alembic import op
import sqlalchemy as sa


revision: str = "d57b635e50bb"
down_revision: str | None = "24baa961e5cf"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "llm_logs",
        sa.Column("thinking_tokens", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("llm_logs", "thinking_tokens")
