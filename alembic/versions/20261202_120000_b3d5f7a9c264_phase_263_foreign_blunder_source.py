"""phase 263 foreign blunder source

Phase 263 adds `DrillSource.FOREIGN_BLUNDER = 3`: a short Train session is filled with a servable
blunder from another non-guest user's game. The only schema change is the CHECK on
`drill_solves.source`, widened additively from (0, 1, 2) to (0, 1, 2, 3), so no existing row can
violate it.

The downgrade is schema-reversible but not data-preserving: a `source = 3` row has no legal value
under the narrower CHECK, so those rows are deleted first. Same lesson as e5f71b11fa51 (Phase 206):
narrowing a CHECK under committed rows aborts the downgrade with a CheckViolationError, and serial
CI shares one database between the migration round-trip suites and the Train router tests that
commit such rows. Deleting before narrowing is the fix at the fix site.

UPGRADE_STATEMENTS / DOWNGRADE_STATEMENTS are module-level so a migration test can run exactly
what Alembic runs. Literal SQL only: migrations are version-pinned snapshots and must not import
live app constants.

Revision ID: b3d5f7a9c264
Revises: e5c1b7d3a9f2
Create Date: 2026-12-02 12:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3d5f7a9c264"
down_revision: Union[str, None] = "e5c1b7d3a9f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UPGRADE_STATEMENTS: tuple[str, ...] = (
    "ALTER TABLE drill_solves DROP CONSTRAINT ck_drill_solves_source",
    "ALTER TABLE drill_solves ADD CONSTRAINT ck_drill_solves_source CHECK (source IN (0, 1, 2, 3))",
)

# The DELETE comes first: a source = 3 row would violate the narrower CHECK.
DOWNGRADE_STATEMENTS: tuple[str, ...] = (
    "DELETE FROM drill_solves WHERE source = 3",
    "ALTER TABLE drill_solves DROP CONSTRAINT ck_drill_solves_source",
    "ALTER TABLE drill_solves ADD CONSTRAINT ck_drill_solves_source CHECK (source IN (0, 1, 2))",
)


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(sa.text(statement))


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(statement))
