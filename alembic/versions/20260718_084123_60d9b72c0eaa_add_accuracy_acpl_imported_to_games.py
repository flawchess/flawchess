"""add accuracy acpl imported to games

Phase 178 Plan 01 (D-01..D-04): repurposes the canonical `games` accuracy/acpl
columns to hold our uniform lichess-formula computed values (populated later by
the phase's compute path — Plans 02/03/04), while preserving the current
platform-provided values in new `*_imported` columns as a comparison/validation
signal.

Steps:
1. Add four new nullable columns: white_accuracy_imported / black_accuracy_imported
   (REAL, matching white_accuracy/black_accuracy) and white_acpl_imported /
   black_acpl_imported (SmallInteger, matching white_acpl/black_acpl).
2. Copy the current canonical values into the new `*_imported` columns.
3. NULL the canonical columns so the compute path (live hook + backfill) can
   refill them with our uniform values.

Copy MUST precede NULL — order enforced within a single UPDATE statement backed
by SELECT semantics (all SET expressions read the pre-UPDATE row), but for
clarity/auditability this is written as two sequential UPDATE statements with the
copy first (T-178-01-D).

D-04 guardrail: this migration references ONLY the accuracy and acpl columns —
never the oracle per-color severity-count columns (which back the
`is_analyzed` sentinel), which stay completely untouched.

Note (Pitfall 4): this is a full-table rewrite on `games` (~718k rows on prod).
Runs automatically on backend startup via deploy/entrypoint.sh — single
statement, no batching needed (prod max_wal_size=8GB handles it).

Revision ID: 60d9b72c0eaa
Revises: 939c3d99868d
Create Date: 2026-07-18 08:41:23.166509+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import REAL


# revision identifiers, used by Alembic.
revision: str = "60d9b72c0eaa"
down_revision: Union[str, Sequence[str], None] = "939c3d99868d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add *_imported columns, copy platform values in, NULL canonical."""
    op.add_column("games", sa.Column("white_accuracy_imported", REAL, nullable=True))
    op.add_column("games", sa.Column("black_accuracy_imported", REAL, nullable=True))
    op.add_column("games", sa.Column("white_acpl_imported", sa.SmallInteger(), nullable=True))
    op.add_column("games", sa.Column("black_acpl_imported", sa.SmallInteger(), nullable=True))

    # Copy platform-provided values into the preserved *_imported columns BEFORE
    # nulling the canonical columns — order matters (T-178-01-D, no data loss).
    op.execute(
        "UPDATE games SET "
        "white_accuracy_imported = white_accuracy, "
        "black_accuracy_imported = black_accuracy, "
        "white_acpl_imported = white_acpl, "
        "black_acpl_imported = black_acpl"
    )

    # NULL the canonical columns so the phase's compute path (live hook +
    # backfill) can refill them with our uniform lichess-formula values.
    op.execute(
        "UPDATE games SET "
        "white_accuracy = NULL, "
        "black_accuracy = NULL, "
        "white_acpl = NULL, "
        "black_acpl = NULL"
    )


def downgrade() -> None:
    """Copy *_imported back into canonical columns, then drop the *_imported columns."""
    op.execute(
        "UPDATE games SET "
        "white_accuracy = white_accuracy_imported, "
        "black_accuracy = black_accuracy_imported, "
        "white_acpl = white_acpl_imported, "
        "black_acpl = black_acpl_imported"
    )

    op.drop_column("games", "black_acpl_imported")
    op.drop_column("games", "white_acpl_imported")
    op.drop_column("games", "black_accuracy_imported")
    op.drop_column("games", "white_accuracy_imported")
