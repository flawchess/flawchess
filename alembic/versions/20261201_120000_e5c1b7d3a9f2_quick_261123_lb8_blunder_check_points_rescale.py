"""Recompute points_possible of blunder-check windows still being played (quick 261123-lb8).

Quick 261123-lb8 rebalanced the blunder-check points: catching the blunder 3 -> 2 and the better
move at most 2 -> 1; a correct Good call (1) and the timeout penalty (1) are unchanged. The
points_possible formula of a blunder window changes from (blunder_position - 1) + 3 + 2 to
(blunder_position - 1) + 2 + 1; a herring window stays at its length. Windows composed after the
deploy already carry the new formula; this data migration brings the windows that are still being
played at deploy time onto it, so a window never scores against a stale maximum.

Scope: blunder_check_windows rows with outcome IS NULL (not ended) whose session has status 'open'.
Only points_possible is written. An unended window holds only correct_safe and timeout_safe
answers, worth 1 and 1 under both rule sets, so its points_scored and its answer rows are already
on the right scale and stay as they are. Ended windows keep their old-scale values: their
points_scored and points_possible are consistent with each other, and rescaling history is out of
scope (D-07, the Points board simply follows the new values from the deploy on). Windows of
completed or expired sessions are never written.

Accepted transient: a missed window that ended before the deploy inside a still-open session is
offered its better move after the deploy (quick 261123-lb8 D-03). It is not touched here: its old
points_possible already counted the better move.

The downgrade restores the old formula on the same selection (windows still unended and open).

UPGRADE_STATEMENTS / DOWNGRADE_STATEMENTS are module-level so the migration test runs exactly what
Alembic runs.

Literal values only: migrations are version-pinned snapshots and must not import live app
constants.

Revision ID: e5c1b7d3a9f2
Revises: a7c3e5f9b261
Create Date: 2026-12-01 12:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5c1b7d3a9f2"
down_revision: Union[str, None] = "a7c3e5f9b261"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The windows both directions touch: not ended, in a session that is still open.
_UNENDED_OPEN_WINDOWS = (
    "SELECT w.id FROM blunder_check_windows w "
    "JOIN blunder_check_sessions s ON s.id = w.session_id "
    "WHERE w.outcome IS NULL AND s.status = 'open'"
)

# A herring window's maximum is its length under both rule sets, so only blunder windows change.
UPGRADE_STATEMENTS: tuple[str, ...] = (
    "UPDATE blunder_check_windows w "
    "SET points_possible = (w.blunder_position - 1) + 3 "
    f"WHERE w.blunder_position IS NOT NULL AND w.id IN ({_UNENDED_OPEN_WINDOWS})",
)

DOWNGRADE_STATEMENTS: tuple[str, ...] = (
    "UPDATE blunder_check_windows w "
    "SET points_possible = (w.blunder_position - 1) + 5 "
    f"WHERE w.blunder_position IS NOT NULL AND w.id IN ({_UNENDED_OPEN_WINDOWS})",
)


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(sa.text(statement))


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(statement))
