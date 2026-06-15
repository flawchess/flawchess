"""phase 122 feedback table

Revision ID: 60160718b3b3
Revises: 20260614150000
Create Date: 2026-06-15 19:20:47.120530+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '60160718b3b3'
down_revision: Union[str, Sequence[str], None] = '20260614150000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the feedback table with FK (ondelete=CASCADE) and user_id index (D-05 / CLAUDE.md DB rules).
    # Note: autogenerate also detected unrelated index drift (partial indexes managed by prior
    # migrations, not reflected in ORM declarations). Those changes are intentionally excluded —
    # ix_games_evals_pending, ix_games_full_evals_pending, ix_games_full_pv_pending, and
    # ix_games_needs_engine_full_evals are owned by Phase 116/119 migrations; ix_eval_jobs_user_id
    # is already present in the DB via the EvalJob model index=True on user_id. Only the
    # feedback table is new in this revision.
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("page_url", sa.String(length=500), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("sentiment", sa.String(length=16), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feedback_user_id"), "feedback", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_feedback_user_id"), table_name="feedback")
    op.drop_table("feedback")
