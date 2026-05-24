"""extend benchmark_metric for TC pressure

Phase 94.3 Plan 04 (Wave-1 atomic cutover B + C + D). Extends the
``benchmark_metric`` Postgres ENUM with 12 new values for per-(metric × TC)
time-pressure percentile chips. The 12 values are the cross product of the
3 new metric families and the 4 time-control buckets:

- ``time_pressure_score_gap_{bullet,blitz,rapid,classical}``
- ``clock_gap_{bullet,blitz,rapid,classical}``
- ``net_flag_rate_{bullet,blitz,rapid,classical}``

CONTEXT.md D-7 — "12 new ENUM values via reversible Alembic migration; no other
schema change." The row shape (``value, percentile, n_games, cdf_snapshot,
computed_at``) is reused verbatim from Phase 94.1/94.2.

Revision ID: fd5b551f381c
Revises: b8f4d92c1e25
Create Date: 2026-05-24 17:07:33.011450+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fd5b551f381c"
down_revision: str | Sequence[str] | None = "b8f4d92c1e25"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# The 12 new values, in Plan C ``IN_SCOPE_METRICS`` grouping order
# (time_pressure_score_gap × 4 TCs, then clock_gap × 4, then net_flag_rate × 4).
# This order mirrors:
#   - ``app/services/global_percentile_cdf.py:CdfMetricId`` (post-Plan-C)
#   - ``scripts/gen_global_percentile_cdf.py:IN_SCOPE_METRICS``
#   - ``app/services/user_benchmark_percentiles_service.py:STAGE_B_METRICS``
#     (post-Plan-D)
# so any future widening of the ENUM follows the same canonical order.
_NEW_VALUES: tuple[str, ...] = (
    "time_pressure_score_gap_bullet",
    "time_pressure_score_gap_blitz",
    "time_pressure_score_gap_rapid",
    "time_pressure_score_gap_classical",
    "clock_gap_bullet",
    "clock_gap_blitz",
    "clock_gap_rapid",
    "clock_gap_classical",
    "net_flag_rate_bullet",
    "net_flag_rate_blitz",
    "net_flag_rate_rapid",
    "net_flag_rate_classical",
)


def upgrade() -> None:
    """Add 12 new ENUM values to ``benchmark_metric`` for Phase 94.3 per-TC chips.

    Postgres 12+ allows ``ALTER TYPE … ADD VALUE`` inside the migration
    transaction; Postgres 18 supports ``IF NOT EXISTS`` for idempotency, which
    lets us re-run this migration safely (e.g. after a partial application or
    in test environments that may already have applied a subset).

    REVERSIBILITY CAVEAT: Postgres cannot remove ENUM values without a table
    rewrite. The ``downgrade()`` below is an intentional no-op stub. If a true
    rollback is needed, prefer ``git revert`` of this upgrade migration BEFORE
    any prod row uses one of the new ENUM values. See CONTEXT.md D-7.
    """
    for value in _NEW_VALUES:
        op.execute(f"ALTER TYPE benchmark_metric ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    """No-op stub. Postgres cannot remove ENUM values without a table rewrite.

    Rollback path is ``git revert`` of the upgrade migration BEFORE any prod row
    uses one of the new ENUM values. Once a row referencing a new ENUM value
    has been written, removing the value would require:

    1. Updating or deleting all rows that reference the value.
    2. Renaming the existing ``benchmark_metric`` type.
    3. Creating a new ``benchmark_metric`` type without the removed value.
    4. ALTER COLUMN-rewriting every column that uses the type to use the new type.
    5. Dropping the old type.

    The Phase 94.3 design accepts that the migration is effectively forward-only
    (CONTEXT.md D-7) — the cost of removing a value is high enough that the
    correct rollback is to ``git revert`` the upgrade BEFORE any prod row uses
    one of the new ENUM values, rather than attempting an in-place table rewrite.
    """
    pass
