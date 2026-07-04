"""import jobs partial unique index

Revision ID: 12d3df9c5373
Revises: b4ea823c85be
Create Date: 2026-07-04 12:30:13.540861+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "12d3df9c5373"
down_revision: Union[str, Sequence[str], None] = "b4ea823c85be"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Phase 149 PRUNE-05: partial unique index enforcing at most one active
    (pending or in_progress) import_jobs row per (user_id, platform). This is
    the DB-level guarantee that closes the TOCTOU race the in-memory
    find_active_job registry cannot survive across process restarts or
    multi-worker deploys. The predicate MUST stay textually identical to the
    one used by get_active_job_for_user_platform (drift-prevention).
    """
    op.create_index(
        "uq_import_jobs_user_platform_active",
        "import_jobs",
        ["user_id", "platform"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'in_progress')"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_import_jobs_user_platform_active",
        table_name="import_jobs",
        postgresql_where=sa.text("status IN ('pending', 'in_progress')"),
    )
