"""phase 249 blunder check tables

Phase 249 (D-15, D-10, D-16): the blunder-check persistence.

- ``blunder_check_sessions``: one header row per composed session. At most one OPEN
  session per user via the partial unique index ``uq_blunder_check_sessions_user_open``.
- ``blunder_check_windows``: the frozen, pre-inserted windows of a session. Each window
  snapshots its start FEN and move list, so a foreign owner deleting the source game
  (FK SET NULL) never breaks another user's session (no VOID outcome needed). The
  ``(user_id, game_id)`` index backs the D-10 no-repeat lookups.
- ``blunder_check_answers``: one row per prompted move (composite PK window_id +
  move_index).
- ``ix_games_user_full_evals``: partial index on ``games(user_id, id)`` for fully
  evaluated games, backing the per-session random pick as an index-only scan.

Enum columns follow the project rule: SMALLINT backed by a Python IntEnum + CHECK for
the high-cardinality tables, TEXT + CHECK for the session status. No native ENUM.

The games index is created non-concurrently like the project's other partial-index
migrations: migrations run against a quiescent backend at container start, and a
CONCURRENTLY build cannot run inside the migration transaction (a few seconds of SHARE
lock on ~1.1M rows).

Revision ID: d5b8e2f1a249
Revises: c4e9b1d7f248
Create Date: 2026-11-10 12:00:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5b8e2f1a249"
down_revision: Union[str, Sequence[str], None] = "c4e9b1d7f248"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "blunder_check_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), server_default="open", nullable=False),
        sa.Column("window_count", sa.SmallInteger(), nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('open', 'completed')", name="ck_blunder_check_sessions_status"
        ),
        sa.CheckConstraint("window_count >= 1", name="ck_blunder_check_sessions_window_count"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_blunder_check_sessions_user_open",
        "blunder_check_sessions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )

    op.create_table(
        "blunder_check_windows",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=True),
        sa.Column("is_own", sa.Boolean(), nullable=False),
        sa.Column("window_length", sa.SmallInteger(), nullable=False),
        sa.Column("blunder_position", sa.SmallInteger(), nullable=True),
        sa.Column("first_ply", sa.SmallInteger(), nullable=False),
        sa.Column("blunder_ply", sa.SmallInteger(), nullable=True),
        sa.Column("window_case", sa.SmallInteger(), nullable=False),
        sa.Column("mover_elo", sa.SmallInteger(), nullable=True),
        sa.Column("start_fen", sa.Text(), nullable=False),
        sa.Column("move_ucis", sa.Text(), nullable=False),
        sa.Column("lead_in_plies", sa.SmallInteger(), nullable=False),
        sa.Column("key_uci", sa.String(length=5), nullable=True),
        sa.Column("refutation_uci", sa.String(length=5), nullable=True),
        sa.Column("points_possible", sa.SmallInteger(), nullable=False),
        sa.Column("points_scored", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("outcome", sa.SmallInteger(), nullable=True),
        sa.Column("better_move_uci", sa.String(length=5), nullable=True),
        sa.Column("better_move_tier", sa.SmallInteger(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("better_move_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "window_length BETWEEN 3 AND 5", name="ck_blunder_check_windows_window_length"
        ),
        sa.CheckConstraint(
            "blunder_position IS NULL OR blunder_position BETWEEN 1 AND window_length",
            name="ck_blunder_check_windows_blunder_position",
        ),
        sa.CheckConstraint(
            "(blunder_position IS NULL) = (blunder_ply IS NULL)",
            name="ck_blunder_check_windows_blunder_ply",
        ),
        sa.CheckConstraint(
            "window_case IN (0, 1, 2, 3)", name="ck_blunder_check_windows_window_case"
        ),
        sa.CheckConstraint(
            "(window_case = 0) = (blunder_ply IS NULL)",
            name="ck_blunder_check_windows_case_herring",
        ),
        sa.CheckConstraint(
            "lead_in_plies BETWEEN 0 AND 4", name="ck_blunder_check_windows_lead_in_plies"
        ),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN (0, 1, 2, 3)", name="ck_blunder_check_windows_outcome"
        ),
        sa.CheckConstraint(
            "better_move_tier IS NULL OR better_move_tier IN (0, 1, 2)",
            name="ck_blunder_check_windows_better_move_tier",
        ),
        sa.ForeignKeyConstraint(["session_id"], ["blunder_check_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id", "position", name="uq_blunder_check_windows_session_position"
        ),
    )
    op.create_index(
        "ix_blunder_check_windows_user_game",
        "blunder_check_windows",
        ["user_id", "game_id"],
        unique=False,
    )

    op.create_table(
        "blunder_check_answers",
        sa.Column("window_id", sa.BigInteger(), nullable=False),
        sa.Column("move_index", sa.SmallInteger(), nullable=False),
        sa.Column("ply", sa.SmallInteger(), nullable=False),
        sa.Column("prompted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("answer", sa.SmallInteger(), nullable=True),
        sa.Column("result", sa.SmallInteger(), nullable=True),
        sa.Column("points_awarded", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("points_forfeited", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_elapsed_ms", sa.Integer(), nullable=True),
        sa.Column("server_elapsed_ms", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "move_index BETWEEN 1 AND 5", name="ck_blunder_check_answers_move_index"
        ),
        sa.CheckConstraint(
            "answer IS NULL OR answer IN (0, 1, 2)", name="ck_blunder_check_answers_answer"
        ),
        sa.CheckConstraint(
            "result IS NULL OR result IN (0, 1, 2, 3, 4, 5)",
            name="ck_blunder_check_answers_result",
        ),
        sa.CheckConstraint(
            "(answered_at IS NULL) = (result IS NULL)", name="ck_blunder_check_answers_answered_at"
        ),
        sa.ForeignKeyConstraint(["window_id"], ["blunder_check_windows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("window_id", "move_index"),
    )

    op.create_index(
        "ix_games_user_full_evals",
        "games",
        ["user_id", "id"],
        unique=False,
        postgresql_where=sa.text("full_evals_completed_at IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_games_user_full_evals",
        table_name="games",
        postgresql_where=sa.text("full_evals_completed_at IS NOT NULL"),
    )
    op.drop_table("blunder_check_answers")
    op.drop_index("ix_blunder_check_windows_user_game", table_name="blunder_check_windows")
    op.drop_table("blunder_check_windows")
    op.drop_index(
        "uq_blunder_check_sessions_user_open",
        table_name="blunder_check_sessions",
        postgresql_where=sa.text("status = 'open'"),
    )
    op.drop_table("blunder_check_sessions")
