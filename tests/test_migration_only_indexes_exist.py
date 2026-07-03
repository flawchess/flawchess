"""Drift-detection guard for migration-only partial indexes (code-review 2026-07-02, #3).

Several partial indexes are created by Alembic migrations but cannot be declared on the
ORM models (SQLAlchemy has no partial-index representation on `Index`). Because they are
invisible to the ORM, they are listed in `alembic/env.py::_AUTOGEN_INDEX_IGNORELIST` so
`--autogenerate` neither drops nor recreates them.

This test is the safety net: it asserts every such index actually exists in the migrated
schema. It runs against this run's per-run test database (built via `alembic upgrade head`,
see conftest.py), so a green run proves the migrations really create these indexes. It
would have caught the `ix_game_flaws_blob_backfill` gap (the index existed in prod but was
missing from the ignorelist, one `--autogenerate` away from an accidental drop of prod's
most-scanned game_flaws index) and it surfaces dev/prod index drift going forward.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.asyncio

# Partial indexes owned by migrations (not ORM-declared) that MUST exist in the schema.
# Keep in sync with the migration-only entries of _AUTOGEN_INDEX_IGNORELIST in env.py.
MIGRATION_ONLY_INDEXES: tuple[str, ...] = (
    "ix_games_evals_pending",
    "ix_games_full_evals_pending",
    "ix_games_full_pv_pending",
    "ix_games_needs_engine_full_evals",
    "ix_game_flaws_blob_backfill",
)


async def test_migration_only_partial_indexes_exist(test_engine) -> None:
    """All migration-only partial indexes must be present in pg_indexes."""
    async with test_engine.connect() as conn:
        result = await conn.execute(
            text("SELECT indexname FROM pg_indexes WHERE indexname = ANY(:names)"),
            {"names": list(MIGRATION_ONLY_INDEXES)},
        )
        present = {row[0] for row in result}

    missing = set(MIGRATION_ONLY_INDEXES) - present
    assert not missing, (
        f"Migration-only partial indexes missing from the schema: {sorted(missing)}. "
        "Either a migration failed to create them or they were dropped/renamed — this is "
        "the drift the ignorelist assumes cannot happen (code-review 2026-07-02, #3)."
    )
