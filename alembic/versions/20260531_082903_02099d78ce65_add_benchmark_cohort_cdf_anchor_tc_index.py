"""add benchmark_cohort_cdf anchor_tc index

Adds a B-tree index on ``benchmark_cohort_cdf (anchor_elo, tc)``. The composite
PK leads with ``metric``, but the only read path (``load_cohort_cells``) filters
on ``anchor_elo`` + ``tc`` and returns all metrics, so the PK cannot serve that
filter -- without this index Postgres seq-scans the full ~123k-row table on every
import. This index makes the batched prefetch an index scan over the user's
anchor x TC grid (closes code-review finding WR-03 for Phase 99.1).

Note: the autogenerate diff also reported a spurious drop of the unrelated
``ix_games_evals_pending`` partial index (a pre-existing model-vs-DB reflection
mismatch, NOT introduced here); that drop was intentionally removed from this
migration so it touches only the Phase 99.1 table.

Revision ID: 02099d78ce65
Revises: d0a962b51c68
Create Date: 2026-05-31 08:29:03.582423+00:00

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "02099d78ce65"
down_revision: Union[str, Sequence[str], None] = "d0a962b51c68"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_benchmark_cohort_cdf_anchor_tc",
        "benchmark_cohort_cdf",
        ["anchor_elo", "tc"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_benchmark_cohort_cdf_anchor_tc",
        table_name="benchmark_cohort_cdf",
    )
