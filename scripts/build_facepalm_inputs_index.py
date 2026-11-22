"""Build and check the covering index ix_game_flaws_facepalm_inputs (Phase 259 D-17).

The facepalm score reads five stored scalars (maia_played_prob, material_loss, material_missed,
maia_best_prob, maia_best_reply_prob); this partial covering index over blunder rows keeps the
score queries index-only. On prod the operator builds it with CREATE INDEX CONCURRENTLY BEFORE the
release that ships the scalar switch, so the migration of the same index is a no-op there (it
rides in the migration for dev, the benchmark DB and the test template).

Why a script and not only the migration: CREATE INDEX CONCURRENTLY IF NOT EXISTS checks the NAME
only. A failed concurrent build leaves an INVALID index of that name (still costing every write,
and skipped by the planner), and a differently-defined index of the same name would be accepted
silently. This script builds from the compiled ORM declaration (never hand-typed SQL), then checks
pg_index.indisvalid and the exact pg_get_indexdef text against EXPECTED_INDEXDEF, the text the
migration produces.

Usage:
    uv run python scripts/build_facepalm_inputs_index.py --db dev
    uv run python scripts/build_facepalm_inputs_index.py --db prod --check-only
    uv run python scripts/build_facepalm_inputs_index.py --db prod --drop-invalid

--db prod needs bin/prod_db_tunnel.sh running. The database URL is never printed.

Exit codes:
    0  the index is valid and its definition equals EXPECTED_INDEXDEF
    3  the index exists but is INVALID (the DROP statement is printed; --drop-invalid runs it, then
       this still exits 3 so the operator re-runs the build)
    4  the index is valid but its definition differs from EXPECTED_INDEXDEF
    5  the index does not exist
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Literal, NamedTuple

from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
from sqlalchemy.schema import CreateIndex

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import db_url_for_target  # noqa: E402
from app.models.base import Base  # noqa: E402

# Importing the model module registers game_flaws (and, through its FKs, the tables it references).
from app.models.game_flaw import GameFlaw  # noqa: E402
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401

DbTarget = Literal["dev", "benchmark", "prod"]
ALLOWED_DB_TARGETS: tuple[DbTarget, ...] = ("dev", "benchmark", "prod")

INDEX_NAME: str = "ix_game_flaws_facepalm_inputs"

# pg_get_indexdef text of the index as the migration builds it (read on dev after the upgrade).
EXPECTED_INDEXDEF: str = (
    "CREATE INDEX ix_game_flaws_facepalm_inputs ON public.game_flaws USING btree "
    "(user_id, game_id) INCLUDE (ply, maia_played_prob, material_loss, material_missed, "
    "maia_best_prob, maia_best_reply_prob) WHERE (severity = 2)"
)

EXIT_OK: int = 0
EXIT_INVALID: int = 3
EXIT_MISMATCH: int = 4
EXIT_ABSENT: int = 5

DROP_INVALID_SQL: str = f"DROP INDEX CONCURRENTLY IF EXISTS {INDEX_NAME}"

# An index-only build over the largest table can run for minutes; the session statement timeout
# is lifted for this one session only (0 = no limit).
_NO_STATEMENT_TIMEOUT_SQL = "SET statement_timeout = 0"
_INDEX_STATE_SQL = text(
    "SELECT i.indisvalid AS is_valid, pg_get_indexdef(i.indexrelid) AS indexdef "
    "FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid "
    "WHERE c.relname = :name AND c.relnamespace = 'public'::regnamespace"
)


class IndexState(NamedTuple):
    """What the catalog says about the index: valid flag and the definition text."""

    is_valid: bool
    indexdef: str


def build_sql() -> str:
    """CREATE INDEX CONCURRENTLY IF NOT EXISTS, compiled from the ORM declaration of the index."""
    table = Base.metadata.tables[GameFlaw.__tablename__]
    index = next(i for i in table.indexes if i.name == INDEX_NAME)
    options = index.dialect_options["postgresql"]
    was_concurrent = options["concurrently"]
    options["concurrently"] = True
    try:
        return str(CreateIndex(index, if_not_exists=True).compile(dialect=postgresql.dialect()))
    finally:
        # The ORM metadata is shared by the whole process; leave the declaration as it was.
        options["concurrently"] = was_concurrent


def classify_index(state: IndexState | None) -> int:
    """Map the catalog state to an exit code (no output, no connection)."""
    if state is None:
        return EXIT_ABSENT
    if not state.is_valid:
        return EXIT_INVALID
    if state.indexdef != EXPECTED_INDEXDEF:
        return EXIT_MISMATCH
    return EXIT_OK


async def read_index_state(conn: AsyncConnection) -> IndexState | None:
    """The index's valid flag and definition, None when it does not exist."""
    row = (await conn.execute(_INDEX_STATE_SQL, {"name": INDEX_NAME})).one_or_none()
    if row is None:
        return None
    return IndexState(is_valid=bool(row.is_valid), indexdef=str(row.indexdef))


async def check_index(conn: AsyncConnection, *, drop_invalid: bool = False) -> int:
    """Verify the index and report; returns EXIT_OK / EXIT_INVALID / EXIT_MISMATCH / EXIT_ABSENT."""
    state = await read_index_state(conn)
    code = classify_index(state)
    if code == EXIT_OK:
        print(f"{INDEX_NAME}: valid, definition equals the expected text.")
    elif code == EXIT_ABSENT:
        print(f"{INDEX_NAME}: absent.")
    elif code == EXIT_INVALID:
        print(f"{INDEX_NAME}: INVALID (a failed concurrent build). Drop it, then build again:")
        print(f"  {DROP_INVALID_SQL}")
        if drop_invalid:
            await conn.execute(text(DROP_INVALID_SQL))
            print("  dropped (--drop-invalid); re-run the build.")
    else:
        assert state is not None
        print(f"{INDEX_NAME}: valid but the definition differs.")
        print(f"  expected: {EXPECTED_INDEXDEF}")
        print(f"  actual:   {state.indexdef}")
    return code


async def _print_session_settings(conn: AsyncConnection) -> None:
    """Print the settings that decide how the build behaves (never the URL)."""
    statement_timeout = (await conn.execute(text("SHOW statement_timeout"))).scalar_one()
    work_mem = (await conn.execute(text("SHOW maintenance_work_mem"))).scalar_one()
    sessions = (
        await conn.execute(
            text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
        )
    ).scalar_one()
    print(f"statement_timeout (server default): {statement_timeout}")
    print(f"maintenance_work_mem: {work_mem}")
    print(f"sessions on this database: {sessions}")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and check the covering index ix_game_flaws_facepalm_inputs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db",
        choices=ALLOWED_DB_TARGETS,
        default="dev",
        help="DB target (default: dev). 'prod' needs bin/prod_db_tunnel.sh running.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only verify the index (valid, exact definition); build nothing.",
    )
    parser.add_argument(
        "--drop-invalid",
        action="store_true",
        help="If the index is INVALID, drop it concurrently (then exit 3, re-run the build).",
    )
    return parser.parse_args(argv)


async def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    # ONE autocommit connection: CREATE INDEX CONCURRENTLY cannot run inside a transaction, and a
    # single session keeps the footprint on a shared server to one backend.
    engine = create_async_engine(
        db_url_for_target(args.db),
        isolation_level="AUTOCOMMIT",
        pool_size=1,
        max_overflow=0,
    )
    try:
        async with engine.connect() as conn:
            await _print_session_settings(conn)
            if not args.check_only:
                await conn.execute(text(_NO_STATEMENT_TIMEOUT_SQL))
                print("building (CREATE INDEX CONCURRENTLY IF NOT EXISTS) ...")
                await conn.execute(text(build_sql()))
            return await check_index(conn, drop_invalid=args.drop_invalid)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
