"""Reindex all indexes of one or more tables, online, to reclaim index bloat.

PROD-ONLY, HUMAN-run index-bloat reclaim. This is a MANUAL ops step. It is NEVER run by
automation, CI, the GSD executor, or ``deploy/entrypoint.sh``. A human runs it at deploy
time.

ORIGIN (SEED-035 "Separate, lower-risk quick win")
    The motivating case is ``game_positions``: only its three Zobrist-hash indexes were
    reindexed on 2026-05-31, so the rest of its index set carries accrued bloat. This script
    generalises that into a reusable "reindex a table's indexes" tool — pass ``--table`` to
    target any table(s). It defaults to ``game_positions``, the biggest lever on DB size
    (85% of prod, ~3.7 GB of indexes).

WHY THIS IS AN OPS SCRIPT, NOT AN ALEMBIC MIGRATION
    REINDEX is a maintenance operation, not a schema change. Alembic migrations run
    automatically on every backend container start and against the tiny dev/test DB on every
    test run, where a REINDEX would be pure wasted work (no bloat there). Keeping this as a
    standalone ``scripts/`` tool, alongside ``backfill_eval.py`` /
    ``backfill_user_percentiles.py``, matches the repo convention and keeps it human-gated.

WHAT IT REINDEXES
    ``REINDEX TABLE CONCURRENTLY <table>`` rebuilds EVERY index on the table (PK + all
    secondary indexes), one at a time, online. REINDEX only touches indexes — it does NOT
    rewrite heap or TOAST data, so it reclaims index bloat only.

ONLINE / NON-BLOCKING
    ``REINDEX ... CONCURRENTLY`` runs ONLINE — no table lock-out, no maintenance window
    needed. It is still a real maintenance op (extra I/O + a transient duplicate of each
    index while it rebuilds), so the run path is gated behind an explicit confirmation prompt.

TRANSACTION CONSTRAINT
    ``REINDEX ... CONCURRENTLY`` cannot run inside a transaction block. Each statement is
    issued on a raw autocommit connection (no implicit ``BEGIN``), one table at a time.

DB target (per CLAUDE.md), selected with ``--db``:
    dev:       localhost:5432   (flawchess-dev Docker compose)       — moot (tiny, no bloat)
    benchmark: localhost:5433   (flawchess-benchmark Docker compose) — only if it has bloat
    prod:      localhost:15432  (SSH tunnel via bin/prod_db_tunnel.sh) — the intended target

The connection URL is derived from ``settings.DATABASE_URL`` by swapping the host:port to
``localhost:<target-port>``. The app DB role owns the tables and CAN reindex; the read-only
MCP/prod role CANNOT. Because the prod password differs from the dev password baked into
``settings.DATABASE_URL``, set ``REINDEX_PROD_DB_URL`` to a full libpq URL with the prod
credentials (host MUST be localhost — the tunnel). No password is committed here.

Usage:
    # Inspect index sizes only (read-only), no rebuild:
    uv run python scripts/reindex_game_positions.py --db prod --verify

    # Print the exact statements without connecting or executing anything:
    uv run python scripts/reindex_game_positions.py --db prod --dry-run

    # Reindex game_positions (default table; prompts for confirmation):
    bin/prod_db_tunnel.sh
    REINDEX_PROD_DB_URL='postgresql+asyncpg://flawchess:<PASSWORD>@localhost:15432/flawchess' \
        uv run python scripts/reindex_game_positions.py --db prod
    bin/prod_db_tunnel.sh stop

    # Reindex several tables in one run:
    uv run python scripts/reindex_game_positions.py --db prod --table game_positions games

Sequencing (game_positions, post-SEED-035):
    This pass is independent of the SEED-035 migration and may run any time. Prefer running
    it POST-deploy, once the migration has shrunk the PK and dropped ``ix_gp_user_game_ply``.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import socket
import sys
from pathlib import Path
from typing import Literal, get_args
from urllib.parse import urlparse, urlunparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402

DbTarget = Literal["dev", "benchmark", "prod"]

# Port map for --db targets per CLAUDE.md.
_TARGET_PORT: dict[DbTarget, int] = {
    "dev": 5432,
    "benchmark": 5433,
    "prod": 15432,
}

_LOCAL_HOSTS: frozenset[str] = frozenset({"localhost", "127.0.0.1", "::1"})
_PROD_TUNNEL_HINT = "Run `bin/prod_db_tunnel.sh` first."

# Seconds to wait when probing whether the prod SSH tunnel is up.
_TUNNEL_PROBE_TIMEOUT_S = 2

# Type the operator must enter to authorize a live reindex.
_CONFIRM_TOKEN = "REINDEX"

# Default table when --table is omitted: the SEED-035 motivating case.
DEFAULT_TABLES: tuple[str, ...] = ("game_positions",)


def _log(msg: str = "") -> None:
    """Print to stderr so piped stdout stays clean (mirrors the other scripts)."""
    print(msg, file=sys.stderr, flush=True)


def _db_url(target: DbTarget) -> str:
    """Build the asyncpg URL for the chosen --db target.

    Derives the URL from ``settings.DATABASE_URL`` by replacing host:port with
    ``localhost:<target-port>``. ``REINDEX_{TARGET}_DB_URL`` overrides this for operators
    who use non-default credentials — typically only needed for prod, whose password differs
    from the dev DB. Override hosts MUST be local (the tunnel/Docker reach the DB via
    localhost).
    """
    if target not in _TARGET_PORT:
        raise ValueError(f"Unknown --db target: {target!r}. Must be one of: {list(_TARGET_PORT)}")

    override_var = f"REINDEX_{target.upper()}_DB_URL"
    override = os.environ.get(override_var)
    if override:
        host = urlparse(override).hostname
        if host not in _LOCAL_HOSTS:
            raise ValueError(
                f"{override_var} host is {host!r}, but this script always reaches the "
                f"database via localhost (dev/benchmark via Docker, prod via the SSH tunnel "
                f"from bin/prod_db_tunnel.sh). Update the override to use "
                f"localhost:{_TARGET_PORT[target]} (keeping the credentials)."
            )
        return override

    port = _TARGET_PORT[target]
    parsed = urlparse(settings.DATABASE_URL)
    new_netloc = f"{parsed.username}:{parsed.password}@localhost:{port}"
    return urlunparse(parsed._replace(netloc=new_netloc))


def _assert_target_safe(url: str, target: DbTarget) -> None:
    """Refuse to run if the URL port does not match the target, or the prod tunnel is down.

    Raises SystemExit with a descriptive message if the safety check fails.
    """
    port = _TARGET_PORT[target]
    if f":{port}" not in url:
        raise SystemExit(
            f"Refusing to run: connection URL does not contain ':{port}' "
            f"(expected for --db {target}). Check REINDEX_{target.upper()}_DB_URL "
            f"or settings.DATABASE_URL."
        )
    if target == "prod":
        try:
            socket.create_connection(("localhost", port), timeout=_TUNNEL_PROBE_TIMEOUT_S).close()
        except OSError:
            raise SystemExit(
                f"Refusing to run: localhost:{port} is not reachable. "
                f"The prod DB tunnel is not up. {_PROD_TUNNEL_HINT}"
            )


def _reindex_sql(table: str) -> str:
    return f"REINDEX TABLE CONCURRENTLY {table};"


def _print_dry_run(target: DbTarget, tables: tuple[str, ...]) -> None:
    _log(f"--dry-run (--db {target}): the following statements WOULD run; no DB connection made:")
    _log()
    for table in tables:
        _log(f"  {_reindex_sql(table)}")
    _log()
    _log("Run without --dry-run to execute (prod requires the tunnel + prod credentials).")


def _confirm(target: DbTarget, tables: tuple[str, ...]) -> bool:
    banner = (
        "=============================================================================\n"
        f" MAINTENANCE: REINDEX TABLE (--db {target})\n"
        f"   Target : {target} DB on localhost:{_TARGET_PORT[target]}\n"
        f"   Tables : {', '.join(tables)}\n"
        "   Mode   : REINDEX TABLE CONCURRENTLY (ONLINE, non-blocking, all indexes)\n"
        " This is online and does NOT lock the tables, but it is still a real maintenance\n"
        " op (extra I/O + a transient duplicate of each index while it rebuilds).\n"
        "============================================================================="
    )
    _log(banner)
    answer = input(f"Type {_CONFIRM_TOKEN} to proceed (anything else aborts): ").strip()
    return answer == _CONFIRM_TOKEN


async def _run_verify(url: str, tables: tuple[str, ...]) -> None:
    """Print every index and its on-disk size for each table (read-only; no rebuild)."""
    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            _log(f"Index sizes ({urlparse(url).hostname}:{urlparse(url).port}):")
            for table in tables:
                _log(f"  {table}:")
                result = await conn.execute(
                    text(
                        "SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid)) "
                        "FROM pg_stat_user_indexes WHERE relname = :table "
                        "ORDER BY pg_relation_size(indexrelid) DESC"
                    ),
                    {"table": table},
                )
                rows = result.all()
                if not rows:
                    _log("    (no indexes found — does the table exist?)")
                for name, size in rows:
                    _log(f"    {name}: {size}")
    finally:
        await engine.dispose()
    _log()
    _log("Compare these before vs after a reindex run to confirm the reclaim, or cross-check")
    _log("against the db-report skill (reports/db-stats/).")


async def _run_reindex(url: str, tables: tuple[str, ...]) -> None:
    """REINDEX each table CONCURRENTLY, one at a time, each on its own autocommit connection.

    CONCURRENTLY cannot run inside a transaction block, so we go through the raw asyncpg
    connection (``driver_connection.execute`` with no params uses the simple-query protocol
    and never opens an implicit transaction) instead of a SQLAlchemy ``begin()`` block.
    """
    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        for table in tables:
            _log()
            _log(f">>> Reindexing all indexes of {table} (CONCURRENTLY)...")
            # Fresh connection per table keeps each REINDEX independent: if one fails the
            # others have already committed (CONCURRENTLY auto-commits on success).
            async with engine.connect() as conn:
                raw = await conn.get_raw_connection()
                driver_conn = raw.driver_connection
                if driver_conn is None:
                    raise RuntimeError("No raw asyncpg connection available for REINDEX.")
                await driver_conn.execute(_reindex_sql(table))
            _log(f">>> Done: {table}")
    finally:
        await engine.dispose()
    _log()
    _log("All reindexes complete. Verify the reclaim with: --verify")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "PROD-ONLY, HUMAN-run REINDEX TABLE CONCURRENTLY for one or more tables "
            "(defaults to game_positions, the SEED-035 case). Reclaims index bloat online."
        )
    )
    parser.add_argument(
        "--db",
        choices=list(get_args(DbTarget)),
        required=True,
        help=(
            "Target DB: dev=localhost:5432, benchmark=localhost:5433, "
            "prod=localhost:15432 (via bin/prod_db_tunnel.sh). prod is the intended target; "
            "dev/benchmark carry no bloat and are effectively no-ops."
        ),
    )
    parser.add_argument(
        "--table",
        nargs="+",
        default=list(DEFAULT_TABLES),
        metavar="TABLE",
        help="Table(s) to reindex. Default: game_positions. All indexes of each are rebuilt.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the exact REINDEX statements without connecting to or touching any DB.",
    )
    mode.add_argument(
        "--verify",
        action="store_true",
        help="Print every index and its on-disk size for each table (read-only; no rebuild).",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    target: DbTarget = args.db
    tables: tuple[str, ...] = tuple(args.table)

    if args.dry_run:
        _print_dry_run(target, tables)
        return

    url = _db_url(target)
    _assert_target_safe(url, target)

    if args.verify:
        await _run_verify(url, tables)
        return

    if not _confirm(target, tables):
        _log("Aborted — no changes made.")
        raise SystemExit(1)

    await _run_reindex(url, tables)


if __name__ == "__main__":
    asyncio.run(main())
