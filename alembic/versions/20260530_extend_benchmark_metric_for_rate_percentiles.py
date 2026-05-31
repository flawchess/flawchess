"""extend benchmark_metric for rate percentiles

Phase 99 Plan 02 (Wave-1 contract layer). Extends the ``benchmark_metric``
Postgres ENUM with 12 new values for per-(rate metric × TC) percentile chips.
The 12 values are the cross product of the 3 new rate families and the 4
time-control buckets:

- ``conversion_rate_{bullet,blitz,rapid,classical}``
- ``parity_rate_{bullet,blitz,rapid,classical}``
- ``recovery_rate_{bullet,blitz,rapid,classical}``

99-CONTEXT.md D-09 — "12 new ENUM members via Alembic migration." The
row shape (``value, percentile, n_games, cdf_snapshot, computed_at``) is
reused verbatim from Phase 94.1/94.2. This migration ONLY adds ENUM values;
it writes NO data rows (Pitfall 2 — ENUM value visibility is deferred to a
new transaction; backfill runs in Plan 05 as a separate process).

Revision ID: 3981239fd391
Revises: c70f5d94b243
Create Date: 2026-05-30

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3981239fd391"
down_revision: str | Sequence[str] | None = "c70f5d94b243"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# The 12 new values, in family-then-TC ordering matching:
#   - app/models/user_benchmark_percentile.py:benchmark_metric_enum
#   - app/services/global_percentile_cdf.py:CdfMetricId (3 family names)
#   - scripts/gen_global_percentile_cdf.py:IN_SCOPE_METRICS (Plan 05)
# so any future widening of the ENUM follows the same canonical order.
_NEW_VALUES: tuple[str, ...] = (
    "conversion_rate_bullet",
    "conversion_rate_blitz",
    "conversion_rate_rapid",
    "conversion_rate_classical",
    "parity_rate_bullet",
    "parity_rate_blitz",
    "parity_rate_rapid",
    "parity_rate_classical",
    "recovery_rate_bullet",
    "recovery_rate_blitz",
    "recovery_rate_rapid",
    "recovery_rate_classical",
)


def upgrade() -> None:
    """Add 12 new ENUM values to ``benchmark_metric`` for Phase 99 rate-percentile chips.

    Postgres 12+ allows ``ALTER TYPE … ADD VALUE`` inside the migration
    transaction; Postgres 18 supports ``IF NOT EXISTS`` for idempotency, which
    lets us re-run this migration safely (e.g. after a partial application or
    in test environments that may already have applied a subset).

    REVERSIBILITY CAVEAT: Postgres cannot remove ENUM values without a table
    rewrite. The ``downgrade()`` below is an intentional no-op stub. If a true
    rollback is needed, prefer ``git revert`` of this upgrade migration BEFORE
    any prod row uses one of the new ENUM values. See 99-CONTEXT.md D-09.
    """
    for value in _NEW_VALUES:
        op.execute(f"ALTER TYPE benchmark_metric ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    """No-op stub. Postgres cannot remove ENUM values without a table rewrite.

    Rollback path is ``git revert`` of the upgrade migration BEFORE any prod row
    uses one of the new ENUM values. Once a row referencing a new ENUM value
    has been written, removing the value would require a full table rewrite
    (rename existing type, create new type without the value, ALTER COLUMN-
    rewrite the table, drop the old type).

    The Phase 99 design accepts that the migration is effectively forward-only
    (99-CONTEXT.md D-09) — git revert is the correct rollback path.
    """
    pass
