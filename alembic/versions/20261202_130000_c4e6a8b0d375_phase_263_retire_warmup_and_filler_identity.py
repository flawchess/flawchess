"""phase 263 retire warmup and filler identity

Phase 263 replaced the lichess filler puzzles with other users' blunders, so two columns that only
served the old design go away, and the sessions still stuck on the old fillers are cleared.

One-way parts (the downgrade restores the schema, not the data):

- `drill_sessions.is_warmup` (D-04, owner-decided): a flag frozen at composition time, so it cannot
  be recomputed for past sessions. The downgrade re-adds it as `false` for every row.
- `drill_solves.sharp_puzzle_id` (owner-confirmed "drop", 2026-11-23): the lichess PuzzleId of a
  retired `source = 2` row, the only link from an old filler solve to its puzzle. The static puzzle
  set was deleted in the same phase. The downgrade re-adds the column empty.
- The data step deletes untouched open sessions (no solve yet) that still hold an unsolved
  `source = 2` row. Those rows can no longer be served, so the session recomposes with foreign
  fillers on the next visit; only its entered_at timestamps are lost. Touched sessions and every
  solved row stay (solved filler rows keep counting toward points, standings and streaks). The
  `drill_solves` rows cascade; the `drill_items` padding rows stay, they are valid items the next
  composition picks up. A downgrade cannot restore the deleted sessions.

UPGRADE_STATEMENTS / DOWNGRADE_STATEMENTS are module-level so a migration test can run exactly
what Alembic runs. Literal SQL only: migrations are version-pinned snapshots and must not import
live app constants (the `2` below is `DrillSource.LEGACY_SHARP_FILLER`).

No CHECK constraint references either dropped column, so none needs handling.

Revision ID: c4e6a8b0d375
Revises: b3d5f7a9c264
Create Date: 2026-12-02 13:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e6a8b0d375"
down_revision: Union[str, None] = "b3d5f7a9c264"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UPGRADE_STATEMENTS: tuple[str, ...] = (
    # (1) Data step: untouched open sessions holding an unsolved retired filler row.
    "DELETE FROM drill_sessions s "
    "WHERE s.status = 'open' "
    "AND NOT EXISTS ("
    "SELECT 1 FROM drill_solves d WHERE d.session_id = s.id AND d.solved_at IS NOT NULL) "
    "AND EXISTS ("
    "SELECT 1 FROM drill_solves d "
    "WHERE d.session_id = s.id AND d.source = 2 AND d.solved_at IS NULL)",
    # (2) D-04: the frozen warm-up flag.
    "ALTER TABLE drill_sessions DROP COLUMN is_warmup",
    # (3) The retired filler's puzzle id.
    "ALTER TABLE drill_solves DROP COLUMN sharp_puzzle_id",
)

DOWNGRADE_STATEMENTS: tuple[str, ...] = (
    "ALTER TABLE drill_sessions ADD COLUMN is_warmup BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE drill_solves ADD COLUMN sharp_puzzle_id TEXT NULL",
)


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(sa.text(statement))


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(statement))
