"""phase 251 two mode train

Phase 251 Plan 01: the schema of the two-mode Train (puzzles + blunder check) in one revision.

train_settings:
- ``ck_train_settings_puzzles`` is widened to ``BETWEEN 0 AND 50`` (D-07: a user may run
  blunder check only). One-way for rows that hold 0 afterwards, see the downgrade.
- ``blunder_check_per_session`` SMALLINT NOT NULL, server default 6 (D-03). A constant default is a
  metadata-only ADD COLUMN, so every existing row reads 6 instantly. CHECK 0..30.
- ``ck_train_settings_some_mode_on`` refuses both session sizes at 0 (D-05 at the DB layer).
- ``blunder_check_level`` TEXT NULL + CHECK (D-17, TEXT + CHECK per CLAUDE.md, no native enum).
- ``blunder_check_notice_from`` TIMESTAMPTZ NULL, stamped now() for existing non-guest rows (D-21).
- ``blunder_check_streak_from`` DATE NULL, the row's local launch day (D-18): days before it are
  judged with blunder check not required, so pre-launch days stay as judged.
- ``streak_credited_on`` DATE NULL, the idempotency key of the eager day credit, backfilled from
  ``streak_settled_through`` so a user who completed today's puzzles before the deploy is not
  credited twice.

blunder_check_sessions:
- ``session_date`` / ``expires_on`` DATE NOT NULL (backfilled from ``started_at`` in the user's
  stored timezone, next day for the expiry), the same window model as ``drill_sessions``.
- status CHECK widened to include 'expired'. Index ``ix_blunder_check_sessions_user_date``.

blunder_check_windows:
- Partial index ``ix_blunder_check_windows_ended_at`` (feeds the weekly board aggregate, mirrors
  ``ix_drill_solves_solved_at``).

Both timezone conversions map a stored zone Postgres does not know (the app validates names with
zoneinfo, whose database can be newer than the server's) to 'UTC' via a join on
``pg_timezone_names``, so an exotic stored zone can never abort the migration.

Revision ID: ccc5e4f91f6d
Revises: d1a7b3c5e261
Create Date: 2026-11-18 20:25:27.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ccc5e4f91f6d"
down_revision: Union[str, Sequence[str], None] = "d1a7b3c5e261"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- train_settings ---
    op.drop_constraint("ck_train_settings_puzzles", "train_settings", type_="check")
    op.create_check_constraint(
        "ck_train_settings_puzzles", "train_settings", "puzzles_per_session BETWEEN 0 AND 50"
    )
    op.add_column(
        "train_settings",
        sa.Column(
            "blunder_check_per_session", sa.SmallInteger(), server_default="6", nullable=False
        ),
    )
    op.create_check_constraint(
        "ck_train_settings_blunder_check",
        "train_settings",
        "blunder_check_per_session BETWEEN 0 AND 30",
    )
    op.create_check_constraint(
        "ck_train_settings_some_mode_on",
        "train_settings",
        "puzzles_per_session > 0 OR blunder_check_per_session > 0",
    )
    op.add_column("train_settings", sa.Column("blunder_check_level", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_train_settings_blunder_check_level",
        "train_settings",
        "blunder_check_level IS NULL OR blunder_check_level IN "
        "('beginner', 'intermediate', 'advanced')",
    )
    op.add_column(
        "train_settings",
        sa.Column("blunder_check_notice_from", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "train_settings", sa.Column("blunder_check_streak_from", sa.Date(), nullable=True)
    )
    op.add_column("train_settings", sa.Column("streak_credited_on", sa.Date(), nullable=True))

    # D-21: the notice is for existing real users only; guests and later rows keep NULL.
    op.execute(
        """
        UPDATE train_settings AS ts
        SET blunder_check_notice_from = now()
        FROM users AS u
        WHERE u.id = ts.user_id AND u.is_guest IS NOT TRUE
        """
    )
    # D-18: the local launch day per row. A stored zone unknown to Postgres falls back to UTC.
    op.execute(
        """
        UPDATE train_settings AS ts
        SET blunder_check_streak_from = (
            now() AT TIME ZONE COALESCE(
                (SELECT z.name FROM pg_timezone_names AS z WHERE z.name = ts.timezone), 'UTC'
            )
        )::date
        """
    )
    op.execute("UPDATE train_settings SET streak_credited_on = streak_settled_through")

    # --- blunder_check_sessions ---
    op.add_column("blunder_check_sessions", sa.Column("session_date", sa.Date(), nullable=True))
    op.add_column("blunder_check_sessions", sa.Column("expires_on", sa.Date(), nullable=True))
    op.execute(
        """
        WITH tz AS MATERIALIZED (
            SELECT ts.user_id, z.name
            FROM train_settings AS ts
            JOIN pg_timezone_names AS z ON z.name = ts.timezone
        )
        UPDATE blunder_check_sessions AS s
        SET session_date = (s.started_at AT TIME ZONE tz.name)::date
        FROM tz
        WHERE tz.user_id = s.user_id
        """
    )
    # Users without a settings row (or with a zone Postgres does not know) fall back to UTC.
    op.execute(
        """
        UPDATE blunder_check_sessions
        SET session_date = (started_at AT TIME ZONE 'UTC')::date
        WHERE session_date IS NULL
        """
    )
    op.execute("UPDATE blunder_check_sessions SET expires_on = session_date + 1")
    op.alter_column("blunder_check_sessions", "session_date", nullable=False)
    op.alter_column("blunder_check_sessions", "expires_on", nullable=False)
    op.drop_constraint("ck_blunder_check_sessions_status", "blunder_check_sessions", type_="check")
    op.create_check_constraint(
        "ck_blunder_check_sessions_status",
        "blunder_check_sessions",
        "status IN ('open', 'completed', 'expired')",
    )
    op.create_index(
        "ix_blunder_check_sessions_user_date",
        "blunder_check_sessions",
        ["user_id", "session_date"],
        unique=False,
    )

    # --- blunder_check_windows ---
    op.create_index(
        "ix_blunder_check_windows_ended_at",
        "blunder_check_windows",
        ["ended_at"],
        unique=False,
        postgresql_where=sa.text("ended_at IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema.

    Not data-preserving where the narrower pre-251 CHECKs cannot hold a row, so those rows are
    rewritten first: a blunder-check-only user (puzzles_per_session = 0) goes back to the default
    6, and expired blunder-check sessions go back to 'completed' (the only non-open status the old
    CHECK allows).

    Why this is needed and not left to an operator: the migration round-trip suites share one
    database with the router tests in serial CI (see the phase 206 downgrade), so a row written by
    an earlier test would otherwise abort the downgrade with a CheckViolationError.
    """
    op.execute("UPDATE train_settings SET puzzles_per_session = 6 WHERE puzzles_per_session = 0")
    op.execute("UPDATE blunder_check_sessions SET status = 'completed' WHERE status = 'expired'")

    op.drop_index(
        "ix_blunder_check_windows_ended_at",
        table_name="blunder_check_windows",
        postgresql_where=sa.text("ended_at IS NOT NULL"),
    )

    op.drop_index("ix_blunder_check_sessions_user_date", table_name="blunder_check_sessions")
    op.drop_constraint("ck_blunder_check_sessions_status", "blunder_check_sessions", type_="check")
    op.create_check_constraint(
        "ck_blunder_check_sessions_status",
        "blunder_check_sessions",
        "status IN ('open', 'completed')",
    )
    op.drop_column("blunder_check_sessions", "expires_on")
    op.drop_column("blunder_check_sessions", "session_date")

    op.drop_column("train_settings", "streak_credited_on")
    op.drop_column("train_settings", "blunder_check_streak_from")
    op.drop_column("train_settings", "blunder_check_notice_from")
    op.drop_constraint("ck_train_settings_blunder_check_level", "train_settings", type_="check")
    op.drop_column("train_settings", "blunder_check_level")
    op.drop_constraint("ck_train_settings_some_mode_on", "train_settings", type_="check")
    op.drop_constraint("ck_train_settings_blunder_check", "train_settings", type_="check")
    op.drop_column("train_settings", "blunder_check_per_session")
    op.drop_constraint("ck_train_settings_puzzles", "train_settings", type_="check")
    op.create_check_constraint(
        "ck_train_settings_puzzles", "train_settings", "puzzles_per_session BETWEEN 1 AND 50"
    )
