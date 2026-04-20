"""create llm_logs

Revision ID: 85dfef624a19
Revises: 179cfbd472ef
Create Date: 2026-04-20 21:14:50.701262+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "85dfef624a19"
down_revision: Union[str, Sequence[str], None] = "179cfbd472ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "llm_logs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("endpoint", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("findings_hash", sa.String(length=64), nullable=False),
        sa.Column("filter_context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt", sa.Text(), nullable=False),
        sa.Column("response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "cache_hit",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_logs_created_at", "llm_logs", ["created_at"], unique=False)
    op.create_index(
        "ix_llm_logs_user_id_created_at",
        "llm_logs",
        ["user_id", "created_at"],
        unique=False,
        postgresql_ops={"created_at": "DESC"},
    )
    op.create_index("ix_llm_logs_findings_hash", "llm_logs", ["findings_hash"], unique=False)
    op.create_index(
        "ix_llm_logs_endpoint_created_at",
        "llm_logs",
        ["endpoint", "created_at"],
        unique=False,
        postgresql_ops={"created_at": "DESC"},
    )
    op.create_index(
        "ix_llm_logs_model_created_at",
        "llm_logs",
        ["model", "created_at"],
        unique=False,
        postgresql_ops={"created_at": "DESC"},
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_llm_logs_model_created_at",
        table_name="llm_logs",
        postgresql_ops={"created_at": "DESC"},
    )
    op.drop_index(
        "ix_llm_logs_endpoint_created_at",
        table_name="llm_logs",
        postgresql_ops={"created_at": "DESC"},
    )
    op.drop_index("ix_llm_logs_findings_hash", table_name="llm_logs")
    op.drop_index(
        "ix_llm_logs_user_id_created_at",
        table_name="llm_logs",
        postgresql_ops={"created_at": "DESC"},
    )
    op.drop_index("ix_llm_logs_created_at", table_name="llm_logs")
    op.drop_table("llm_logs")
