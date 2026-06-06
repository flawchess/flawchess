"""add game_flaws table

Revision ID: a7e0b4796501
Revises: f4d88c3659c6
Create Date: 2026-06-06 15:14:39.545667+00:00

SEED-038: create the game_flaws materialization table. Stores one row per
user mistake or blunder (M+B only — inaccuracies are never stored, D-03).

Composite PK (user_id, game_id, ply) mirrors game_positions (SEED-035).
Both FKs carry ondelete=CASCADE so reimport / user-delete auto-removes rows.

The display payload (es_before, es_after, move_san, fen) is persisted at
classify time so the Flaws-tab miniboard renders without PGN replay per request.

Secondary index ix_game_flaws_user_severity on (user_id, severity) built
CONCURRENTLY (cannot run inside a transaction — uses autocommit_block).
The game_id column carries a plain btree index (ix_game_flaws_game_id)
that backs the ON DELETE CASCADE FK walk on games.id.

Note: autogenerate also emitted a spurious drop of the pre-existing
ix_games_evals_pending partial index (a model-vs-DB reflection mismatch).
That drop has been removed from this migration intentionally — same pattern
as 02099d78ce65.

Literal column types only — migrations are version-pinned snapshots and
must NOT import live app constants (project rule).
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7e0b4796501"
down_revision: str | None = "f4d88c3659c6"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "game_flaws",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("ply", sa.SmallInteger(), nullable=False),
        sa.Column("severity", sa.SmallInteger(), nullable=False),
        sa.Column("tempo", sa.SmallInteger(), nullable=True),
        sa.Column("phase", sa.SmallInteger(), nullable=False),
        sa.Column("is_miss", sa.Boolean(), nullable=False),
        sa.Column("is_lucky_escape", sa.Boolean(), nullable=False),
        sa.Column("is_while_ahead", sa.Boolean(), nullable=False),
        sa.Column("is_result_changing", sa.Boolean(), nullable=False),
        sa.Column("es_before", sa.Float(), nullable=False),
        sa.Column("es_after", sa.Float(), nullable=False),
        sa.Column("move_san", sa.String(), nullable=True),
        sa.Column("fen", sa.String(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "game_id", "ply"),
    )
    # Plain btree index on game_id backs the ON DELETE CASCADE FK walk.
    op.create_index("ix_game_flaws_game_id", "game_flaws", ["game_id"], unique=False)
    # CONCURRENTLY cannot run inside a transaction — use autocommit_block.
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_game_flaws_user_severity",
            "game_flaws",
            ["user_id", "severity"],
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    op.drop_table("game_flaws")
