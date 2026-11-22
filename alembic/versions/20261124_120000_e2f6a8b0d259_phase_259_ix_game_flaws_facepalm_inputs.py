"""Add ix_game_flaws_facepalm_inputs: covering partial index over the scalar facepalm inputs.

Phase 259 D-17. The facepalm score and type expressions read five stored scalars after the
scalar switch (maia_played_prob, material_loss, material_missed, maia_best_prob,
maia_best_reply_prob). This index carries exactly those columns plus ply, keyed
(user_id, game_id) and partial on severity = 2 (blunders), so scoring a user's blunders stays an
index-only scan. The older ix_game_flaws_blunder_facts stays until the drop plan, so a rollback
of the switch keeps a usable index.

CONCURRENTLY: CREATE / DROP INDEX CONCURRENTLY cannot run inside a transaction, so both run in
op.get_context().autocommit_block(). The index is built on prod by the operator before this
release (scripts/build_facepalm_inputs_index.py), so the statement is a no-op there; it rides in
the migration for dev, the benchmark DB and the test template. IF NOT EXISTS checks the NAME
only, so a failed CONCURRENTLY build that left an INVALID index, or an index with a different
definition, would be accepted silently: the operator script verifies indisvalid and the exact
pg_get_indexdef text, and the deploy is gated on its --check-only run.

CREATE_SQL is the exact text scripts/build_facepalm_inputs_index.py build_sql() compiles from the
ORM declaration; tests/scripts/test_build_facepalm_inputs_index.py pins the two equal. Literal
values only: migrations are version-pinned snapshots and must not import live app constants.

Revision ID: e2f6a8b0d259
Revises: d2a6c8e0f259
Create Date: 2026-11-24 12:00:00
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2f6a8b0d259"
down_revision: Union[str, None] = "d2a6c8e0f259"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CREATE_SQL: str = (
    "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_game_flaws_facepalm_inputs "
    "ON game_flaws (user_id, game_id) "
    "INCLUDE (ply, maia_played_prob, material_loss, material_missed, maia_best_prob, "
    "maia_best_reply_prob) "
    "WHERE severity = 2"
)

DROP_SQL: str = "DROP INDEX CONCURRENTLY IF EXISTS ix_game_flaws_facepalm_inputs"


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(CREATE_SQL)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(DROP_SQL)
