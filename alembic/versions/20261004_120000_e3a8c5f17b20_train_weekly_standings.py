"""train weekly standings

Revision ID: e3a8c5f17b20
Revises: c4e7a91d2b58
Create Date: 2026-10-04 12:00:00+00:00

Phase 231 weekly leaderboard medals: persisted final standings so opt-outs and
account deletions never change past winners. The marker table
(train_weekly_finalizations) remembers finalized weeks, including empty ones, and its
primary-key insert serializes concurrent finalizers.

Also creates the first trigger in the repo: when an account is deleted, the FK
ON DELETE SET NULL on train_weekly_standings.user_id fires
trg_train_weekly_standings_erase_name, which rewrites display_name to 'Deleted user'
in the same statement (GDPR erasure; there is no application deletion path).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3a8c5f17b20'
down_revision: Union[str, Sequence[str], None] = 'c4e7a91d2b58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'train_weekly_finalizations',
        sa.Column('week_start', sa.Date(), nullable=False),
        sa.Column(
            'finalized_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('week_start'),
    )
    op.create_table(
        'train_weekly_standings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('week_start', sa.Date(), nullable=False),
        sa.Column('board', sa.Text(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('display_name', sa.Text(), nullable=False),
        sa.Column('final_rank', sa.Integer(), nullable=False),
        sa.Column('value', sa.Integer(), nullable=False),
        sa.Column('puzzles', sa.Integer(), nullable=False),
        sa.Column('medal', sa.SmallInteger(), nullable=True),
        sa.Column('celebrated_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("board IN ('points', 'accuracy')", name='ck_train_weekly_standings_board'),
        sa.CheckConstraint('medal IS NULL OR medal IN (1, 2, 3)', name='ck_train_weekly_standings_medal'),
        sa.ForeignKeyConstraint(
            ['week_start'], ['train_weekly_finalizations.week_start'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'week_start', 'board', 'user_id', name='uq_train_weekly_standings_week_board_user'
        ),
    )
    op.create_index(
        'ix_train_weekly_standings_user_id', 'train_weekly_standings', ['user_id'], unique=False
    )
    # The literal 'Deleted user' must stay equal to
    # app.services.train_leaderboard.DELETED_USER_DISPLAY_NAME (pinned by tests).
    op.execute(
        """
        CREATE FUNCTION train_weekly_standings_erase_name() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          NEW.display_name := 'Deleted user';
          RETURN NEW;
        END $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_train_weekly_standings_erase_name
        BEFORE UPDATE OF user_id ON train_weekly_standings
        FOR EACH ROW WHEN (OLD.user_id IS NOT NULL AND NEW.user_id IS NULL)
        EXECUTE FUNCTION train_weekly_standings_erase_name();
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('DROP TRIGGER trg_train_weekly_standings_erase_name ON train_weekly_standings')
    op.execute('DROP FUNCTION train_weekly_standings_erase_name()')
    op.drop_index('ix_train_weekly_standings_user_id', table_name='train_weekly_standings')
    op.drop_table('train_weekly_standings')
    op.drop_table('train_weekly_finalizations')
