"""users.prompt_state and feedback.source

Revision ID: f4b9d2c7e815
Revises: a7c3e9d41f02
Create Date: 2026-10-05 14:00:00+00:00

SEED-191 / Phase 234 (milestone feedback ask):

* ``users.prompt_state`` is one generic JSONB column keyed by ask id (the
  feedback ask lives under ``feedback_v1``), so a future ask adds a key, not a
  migration. It is NOT NULL with a ``'{}'`` default so a Python ``None`` can
  never turn into a JSON ``null`` (the asyncpg JSON-null trap); existing rows
  read ``{}``. This is a deliberate exception to the TEXT + CHECK rule: the
  stored shape is validated per ask by a Pydantic model
  (``app.schemas.feedback_ask.FeedbackAskState``) instead of a DB CHECK.
* ``feedback.source`` records which entry point produced a feedback row
  (``floating_button`` or ``milestone_ask``) so the ask's yield is queryable in
  Postgres. Every existing row came from the floating button, so the default
  backfills truthfully.

A non-volatile ADD COLUMN default is metadata-only in Postgres (no table
rewrite), and the CHECK scan touches ~14 feedback rows, so this is instant.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f4b9d2c7e815'
down_revision: Union[str, Sequence[str], None] = 'a7c3e9d41f02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column(
            'prompt_state',
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        'feedback',
        sa.Column(
            'source',
            sa.Text(),
            server_default=sa.text("'floating_button'"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        'ck_feedback_source',
        'feedback',
        "source IN ('floating_button', 'milestone_ask')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_feedback_source', 'feedback', type_='check')
    op.drop_column('feedback', 'source')
    op.drop_column('users', 'prompt_state')
