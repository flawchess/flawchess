"""Serve-time selection record on blunder_check_windows.

Phase 261 (SEED-261121-t50, CONTEXT "Claude's Discretion"). A composed blunder window now carries
what was served and why: the arm that drew it (main = 0, exploration = 1) and P(arm) at serve time,
a snapshot of the facepalm score and its five inputs, and the type-line facts (the deepest settled
swing and a mate flag on the facepalm-type side). The score is a query-time expression that changes
with every refit and a deleted foreign game NULLs game_id, so the solution feedback and the later
calibration must read a serve-time snapshot rather than recompute it.

Ten nullable columns and eight CHECKs. Herring windows and windows composed before this phase keep
NULL everywhere (a separate legacy population, no backfill to "main"). No native ENUM: the arm is a
SMALLINT with a CHECK (CLAUDE.md database design rules).

The CHECKs are added validated: blunder_check_windows holds a few hundred rows per day since
2026-11-19, and every row has NULL in all ten new columns, so validating them is a short scan.

Literal values only: migrations are version-pinned snapshots and must not import live app
constants.

Revision ID: a7c3e5f9b261
Revises: f3a7b9c1e259
Create Date: 2026-11-30 12:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c3e5f9b261"
down_revision: Union[str, None] = "f3a7b9c1e259"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "blunder_check_windows"

# (column, type) in creation order; the downgrade drops them in reverse.
_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("selection_arm", sa.SmallInteger()),
    ("arm_probability", sa.REAL()),
    ("facepalm_score", sa.REAL()),
    ("facepalm_played_prob", sa.REAL()),
    ("facepalm_loss", sa.REAL()),
    ("facepalm_missed", sa.REAL()),
    ("facepalm_best_prob", sa.REAL()),
    ("facepalm_reply_prob", sa.REAL()),
    ("type_swing", sa.SmallInteger()),
    ("type_mate", sa.Boolean()),
)

# (constraint name, predicate) in creation order; the downgrade drops them in reverse.
_CHECKS: tuple[tuple[str, str], ...] = (
    (
        "ck_blunder_check_windows_selection_arm",
        "selection_arm IS NULL OR selection_arm IN (0, 1)",
    ),
    (
        "ck_blunder_check_windows_arm_probability",
        "(selection_arm IS NULL) = (arm_probability IS NULL) "
        "AND (arm_probability IS NULL OR (arm_probability > 0 AND arm_probability <= 1))",
    ),
    (
        "ck_blunder_check_windows_arm_snapshot",
        "(selection_arm IS NULL) = (facepalm_score IS NULL)",
    ),
    (
        "ck_blunder_check_windows_arm_herring",
        "window_case <> 0 OR selection_arm IS NULL",
    ),
    (
        "ck_blunder_check_windows_facepalm_score",
        "facepalm_score IS NULL OR (facepalm_score >= 0 AND facepalm_score <= 1)",
    ),
    (
        "ck_blunder_check_windows_snapshot_inputs",
        "facepalm_score IS NULL OR (facepalm_played_prob IS NOT NULL "
        "AND facepalm_loss IS NOT NULL AND facepalm_missed IS NOT NULL)",
    ),
    (
        "ck_blunder_check_windows_type_mate",
        "(facepalm_score IS NULL) = (type_mate IS NULL)",
    ),
    (
        "ck_blunder_check_windows_type_swing",
        "type_swing IS NULL OR type_swing >= 0",
    ),
)


def upgrade() -> None:
    """Add the ten nullable columns, then the eight CHECKs that tie them together."""
    for name, column_type in _COLUMNS:
        op.add_column(_TABLE, sa.Column(name, column_type, nullable=True))
    for name, predicate in _CHECKS:
        op.create_check_constraint(name, _TABLE, predicate)


def downgrade() -> None:
    """Drop the eight CHECKs, then the ten columns, in reverse order (the snapshot values are lost)."""
    for name, _ in reversed(_CHECKS):
        op.drop_constraint(name, _TABLE, type_="check")
    for name, _ in reversed(_COLUMNS):
        op.drop_column(_TABLE, name)
