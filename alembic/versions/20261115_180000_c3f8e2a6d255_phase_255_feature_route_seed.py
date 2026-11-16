"""phase 255 feature route seed

Phase 255 (D-16, D-22): data-only seed (no DDL) of the feature-discovery route. Every ``users``
row that exists when this runs (guests and superusers included) gets the nine launch step IDs
as ``{status: 'done', date: <migration UTC day>, with_dot: false}`` under
``prompt_state.feature_route.steps`` and no ``current`` key (absent, never a JSON null), so
the route only walks new signups. Rows created afterwards keep ``{}`` and walk the route.

The step IDs are hard-coded on purpose: a migration must never import the live registry, which
grows, and a step added after launch has to stay absent for the seeded users so it can announce
itself (D-22).

Idempotent: the ``WHERE prompt_state->'feature_route' IS NULL`` guard skips rows that already
hold a route. Only the ``feature_route`` key is added (``||``), so ``feedback_v1`` survives.

The downgrade removes ``feature_route`` from every row, which also drops completions recorded
after the upgrade (accepted).

Revision ID: c3f8e2a6d255
Revises: a7d2c9e1b254
Create Date: 2026-11-15 18:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "c3f8e2a6d255"
down_revision: Union[str, Sequence[str], None] = "a7d2c9e1b254"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The nine launch steps, D-06 order. Frozen here: never import the live registry.
_LAUNCH_STEP_IDS: tuple[str, ...] = (
    "import",
    "train",
    "bots",
    "openings",
    "openings-played-as",
    "openings-filters",
    "openings-stats",
    "endgames",
    "library-stats",
)

_SEED_SQL = """
UPDATE users SET prompt_state = prompt_state || jsonb_build_object('feature_route',
    jsonb_build_object('steps', (
        SELECT jsonb_object_agg(step_id, jsonb_build_object(
            'status', 'done',
            'date', to_char((now() AT TIME ZONE 'UTC')::date, 'YYYY-MM-DD'),
            'with_dot', false))
        FROM unnest(CAST(:ids AS text[])) AS step_id)))
WHERE prompt_state->'feature_route' IS NULL
"""


def upgrade() -> None:
    statement = sa.text(_SEED_SQL).bindparams(
        sa.bindparam("ids", value=list(_LAUNCH_STEP_IDS), type_=postgresql.ARRAY(sa.Text()))
    )
    op.execute(statement)


def downgrade() -> None:
    op.execute("UPDATE users SET prompt_state = prompt_state - 'feature_route'")
