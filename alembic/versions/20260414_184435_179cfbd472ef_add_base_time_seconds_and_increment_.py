"""add base_time_seconds and increment_seconds to games

Revision ID: 179cfbd472ef
Revises: 78845c63e456
Create Date: 2026-04-14 18:44:35.344792+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "179cfbd472ef"
down_revision: Union[str, Sequence[str], None] = "78845c63e456"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _parse_base_inc(tc_str: str) -> tuple[int | None, int | None]:
    """Self-contained parser for time control string -> (base_seconds, increment_seconds).

    Inline copy of app.services.normalization.parse_base_and_increment so the migration
    stays self-contained against future code renames.

    Rules:
        '600'      -> (600, 0)
        '600+0'    -> (600, 0)
        '600+5'    -> (600, 5)
        '10+0.1'   -> (10, 0)   # fractional inc rounded to int
        '1/259200' -> (None, None)  # daily format
        ''         -> (None, None)
        '-'        -> (None, None)
    """
    if not tc_str or tc_str == "-":
        return None, None

    try:
        if "+" in tc_str:
            base_str, increment_str = tc_str.split("+", 1)
            base = float(base_str)
            increment = float(increment_str)
        elif "/" in tc_str:
            # Daily format like "1/259200" — no fixed base clock
            return None, None
        else:
            base = float(tc_str)
            increment = 0.0
    except (ValueError, AttributeError):
        return None, None

    return int(round(base)), int(round(increment))


def upgrade() -> None:
    """Add base_time_seconds and increment_seconds columns, backfill from time_control_str."""
    op.add_column("games", sa.Column("base_time_seconds", sa.SmallInteger(), nullable=True))
    op.add_column("games", sa.Column("increment_seconds", sa.SmallInteger(), nullable=True))

    # Backfill from time_control_str using the inline _parse_base_inc helper.
    # Processes in batches of 500 to avoid large single transactions.
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, time_control_str FROM games WHERE time_control_str IS NOT NULL "
            "AND base_time_seconds IS NULL"
        )
    ).fetchall()

    BATCH = 500
    updates: list[dict] = []
    for row in rows:
        tc = row.time_control_str
        base, inc = _parse_base_inc(tc)
        if base is None:
            continue
        updates.append({"id": row.id, "b": base, "i": inc or 0})
        if len(updates) >= BATCH:
            conn.execute(
                sa.text(
                    "UPDATE games SET base_time_seconds = :b, increment_seconds = :i WHERE id = :id"
                ),
                updates,
            )
            updates = []
    if updates:
        conn.execute(
            sa.text(
                "UPDATE games SET base_time_seconds = :b, increment_seconds = :i WHERE id = :id"
            ),
            updates,
        )


def downgrade() -> None:
    """Remove base_time_seconds and increment_seconds columns."""
    op.drop_column("games", "increment_seconds")
    op.drop_column("games", "base_time_seconds")
