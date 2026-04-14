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


def _parse_base_inc(tc_str: str) -> tuple[int | None, float | None]:
    """Self-contained parser for time control string -> (base_seconds, increment_seconds).

    Inline copy of app.services.normalization.parse_base_and_increment so the migration
    stays self-contained against future code renames.

    Rules:
        '600'      -> (600, 0.0)
        '600+0'    -> (600, 0.0)
        '600+5'    -> (600, 5.0)
        '10+0.1'   -> (10, 0.1)   # chess.com fractional increment preserved
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

    return int(round(base)), increment


def _derive_bucket(base: int, increment: float) -> str:
    """Derive time_control_bucket using the same thresholds as
    app.services.normalization.parse_time_control (estimated = base + increment * 40)."""
    estimated = int(base + increment * 40)
    if estimated < 180:
        return "bullet"
    elif estimated < 600:
        return "blitz"
    elif estimated <= 1800:
        return "rapid"
    else:
        return "classical"


def upgrade() -> None:
    """Add base_time_seconds and increment_seconds columns, backfill from time_control_str.

    Also repairs legacy rows where time_control_bucket is NULL but time_control_str is
    parseable — e.g. chess.com '10+0.1' games imported before the fractional-increment
    parse fix in app/services/normalization.py.
    """
    op.add_column("games", sa.Column("base_time_seconds", sa.SmallInteger(), nullable=True))
    # Float: chess.com emits fractional increments like "10+0.1" (0.1s bonus).
    # SmallInteger would silently round these to 0.
    op.add_column("games", sa.Column("increment_seconds", sa.Float(), nullable=True))

    # Backfill from time_control_str using the inline _parse_base_inc helper.
    # Also repair time_control_bucket for legacy NULL rows where tc_str parses.
    # Processes in batches of 500 to avoid large single transactions.
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, time_control_str, time_control_bucket FROM games "
            "WHERE time_control_str IS NOT NULL "
            "AND (base_time_seconds IS NULL OR time_control_bucket IS NULL)"
        )
    ).fetchall()

    BATCH = 500
    updates: list[dict] = []
    for row in rows:
        tc = row.time_control_str
        base, inc = _parse_base_inc(tc)
        if base is None:
            continue
        inc_val = inc if inc is not None else 0.0
        # Only fill bucket when it's currently NULL — never overwrite a stored value.
        bucket = row.time_control_bucket or _derive_bucket(base, inc_val)
        updates.append({"id": row.id, "b": base, "i": inc_val, "bk": bucket})
        if len(updates) >= BATCH:
            conn.execute(
                sa.text(
                    "UPDATE games SET base_time_seconds = :b, increment_seconds = :i, "
                    "time_control_bucket = :bk WHERE id = :id"
                ),
                updates,
            )
            updates = []
    if updates:
        conn.execute(
            sa.text(
                "UPDATE games SET base_time_seconds = :b, increment_seconds = :i, "
                "time_control_bucket = :bk WHERE id = :id"
            ),
            updates,
        )


def downgrade() -> None:
    """Remove base_time_seconds and increment_seconds columns."""
    op.drop_column("games", "increment_seconds")
    op.drop_column("games", "base_time_seconds")
