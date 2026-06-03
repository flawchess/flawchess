"""Reindex the two bloated ``game_positions`` indexes the SEED-035 migration leaves untouched.

PROD-ONLY, HUMAN-run index-bloat reclaim (SEED-035 "Separate, lower-risk quick win").
This is a MANUAL ops step. It is NEVER run by automation, CI, the GSD executor, or
``deploy/entrypoint.sh``. A human runs it at deploy time.

WHY THIS IS AN OPS SCRIPT, NOT AN ALEMBIC MIGRATION
    REINDEX is a maintenance operation, not a schema change. Alembic migrations run
    automatically on every backend container start and against the tiny dev/test DB on
    every test run, where a REINDEX would be pure wasted work (no bloat there). Keeping
    this as a standalone ``scripts/`` tool, alongside ``backfill_eval.py`` /
    ``backfill_user_percentiles.py``, matches the repo convention and keeps it firmly
    human-gated.

SCOPE — exactly TWO indexes (and the reasoning)
    SEED-035's quick win listed four bloated indexes, but the SEED-035 migration
    (``f4d88c3659c6``) drops or rebuilds two of them, so they need NO reindex:
      - ``game_positions_pkey``  -> re-created fresh by the migration's CONCURRENTLY
                                    unique-index build => not bloated => EXCLUDED.
      - ``ix_gp_user_game_ply``  -> dropped entirely by the migration => EXCLUDED.
    The two the migration leaves UNTOUCHED, and that therefore still carry the bloat
    accrued since the 2026-05-31 hash-only reindex, are:
      - ``ix_gp_user_endgame_game``   (~622 MB, never touched by the migration)
      - ``ix_game_positions_game_id`` (~452 MB, explicitly KEPT-not-rebuilt; backs the
                                       ON DELETE CASCADE FK)
    This script reindexes precisely these two and nothing else.

EXPECTED RECLAIM
    Combined with the migration's PK shrink (~1.45 GB), this reindex pass should reclaim
    on the order of ~1 GB more from the ``game_positions`` index set.

ONLINE / NON-BLOCKING
    ``REINDEX INDEX CONCURRENTLY`` runs ONLINE — no table lock-out, no maintenance window
    needed. It rebuilds one index at a time. It is still a real prod maintenance op (extra
    I/O + a transient duplicate index per rebuild), so the run path is gated behind an
    explicit confirmation prompt.

TRANSACTION CONSTRAINT
    ``REINDEX ... CONCURRENTLY`` cannot run inside a transaction block. Each statement is
    issued on a raw autocommit connection (no implicit ``BEGIN``), one at a time.

DB target (per CLAUDE.md), selected with ``--db``:
    dev:       localhost:5432   (flawchess-dev Docker compose)       — moot (tiny, no bloat)
    benchmark: localhost:5433   (flawchess-benchmark Docker compose) — only if it has bloat
    prod:      localhost:15432  (SSH tunnel via bin/prod_db_tunnel.sh) — the intended target

The connection URL is derived from ``settings.DATABASE_URL`` by swapping the host:port to
``localhost:<target-port>``. The app DB role is the ``game_positions`` table owner and CAN
reindex; the read-only MCP/prod role CANNOT. Because the prod password differs from the dev
password baked into ``settings.DATABASE_URL``, set ``REINDEX_PROD_DB_URL`` to a full libpq
URL with the prod credentials (host MUST be localhost — the tunnel). No password is
committed here.

Usage:
    # Inspect sizes only (read-only), no rebuild:
    uv run python scripts/reindex_game_positions.py --db prod --verify

    # Print the exact statements without connecting or executing anything:
    uv run python scripts/reindex_game_positions.py --db prod --dry-run

    # Reindex (prompts for confirmation; tunnel must be up for --db prod):
    bin/prod_db_tunnel.sh
    REINDEX_PROD_DB_URL='postgresql+asyncpg://flawchess:<PASSWORD>@localhost:15432/flawchess' \
        uv run python scripts/reindex_game_positions.py --db prod
    bin/prod_db_tunnel.sh stop

Sequencing:
    This pass is INDEPENDENT of the migration and may run any time. Prefer running it
    POST-deploy: right after the SEED-035 migration ships, only these two indexes remain
    bloated. Running it before the migration would reindex these two correctly but leave
    the soon-to-be-dropped indexes alone — harmless but wasteful.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
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

# The two (and only two) indexes this script reindexes. See SCOPE in the module docstring.
INDEXES: tuple[str, ...] = (
    "ix_gp_user_endgame_game",
    "ix_game_positions_game_id",
)

# A defensive guard: index names are interpolated into DDL (REINDEX takes no bind params),
# so confirm they are plain identifiers before building any statement.
_IDENT_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


def _log(msg: str = "") -> None:
    """Print to stderr so piped stdout stays clean (mirrors the other scripts)."""
    print(msg, file=sys.stderr, flush=True)


def _validate_indexes(indexes: tuple[str, ...]) -> None:
    for idx in indexes:
        if not _IDENT_RE.match(idx):
            raise ValueError(f"Refusing to reindex non-identifier index name: {idx!r}")


def _db_url(target: DbTarget) -> str:
    """Build the asyncpg URL for the chosen --db target.

    Derives the URL from ``settings.DATABASE_URL`` by replacing host:port with
    ``localhost:<target-port>``. ``REINDEX_{TARGET}_DB_URL`` overrides this for operators
    who use non-default credentials — typically only needed for prod, whose password
    differs from the dev DB. Override hosts MUST be local (the tunnel/Docker reach the DB
    via localhost).
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


def _reindex_sql(idx: str) -> str:
    return f"REINDEX INDEX CONCURRENTLY {idx};"


def _print_dry_run(target: DbTarget, indexes: tuple[str, ...]) -> None:
    _log(f"--dry-run (--db {target}): the following statements WOULD run; no DB connection made:")
    _log()
    for idx in indexes:
        _log(f"  {_reindex_sql(idx)}")
    _log()
    _log("Run without --dry-run to execute (prod requires the tunnel + prod credentials).")


def _confirm(target: DbTarget, indexes: tuple[str, ...]) -> bool:
    banner = (
        "=============================================================================\n"
        f" MAINTENANCE: REINDEX game_positions indexes (--db {target})\n"
        f"   Target : {target} DB on localhost:{_TARGET_PORT[target]}\n"
        f"   Indexes: {', '.join(indexes)}\n"
        "   Mode   : REINDEX INDEX CONCURRENTLY (ONLINE, non-blocking, one at a time)\n"
        " This is online and does NOT lock the table, but it is still a real maintenance\n"
        " op (extra I/O + a transient duplicate index per rebuild).\n"
        "============================================================================="
    )
    _log(banner)
    answer = input(f"Type {_CONFIRM_TOKEN} to proceed (anything else aborts): ").strip()
    return answer == _CONFIRM_TOKEN


async def _run_verify(url: str, indexes: tuple[str, ...]) -> None:
    """Print each index's current on-disk size (read-only; no rebuild)."""
    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            _log(f"Current index sizes ({urlparse(url).hostname}:{urlparse(url).port}):")
            for idx in indexes:
                result = await conn.execute(
                    text("SELECT pg_size_pretty(pg_relation_size((:idx)::regclass))"),
                    {"idx": idx},
                )
                _log(f"  {idx}: {result.scalar_one()}")
    finally:
        await engine.dispose()
    _log()
    _log("Compare these before vs after a reindex run to confirm the reclaim, or cross-check")
    _log("against the db-report skill (reports/db-stats/).")


async def _run_reindex(url: str, indexes: tuple[str, ...]) -> None:
    """REINDEX each index CONCURRENTLY, one at a time, each on its own autocommit connection.

    CONCURRENTLY cannot run inside a transaction block, so we go through the raw asyncpg
    connection (``driver_connection.execute`` with no params uses the simple-query protocol
    and never opens an implicit transaction) instead of a SQLAlchemy ``begin()`` block.
    """
    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        for idx in indexes:
            _log()
            _log(f">>> Reindexing {idx} (CONCURRENTLY)...")
            # Fresh connection per index keeps each REINDEX fully independent: if one fails
            # the others have already committed (CONCURRENTLY auto-commits on success).
            async with engine.connect() as conn:
                raw = await conn.get_raw_connection()
                await raw.driver_connection.execute(_reindex_sql(idx))
            _log(f">>> Done: {idx}")
    finally:
        await engine.dispose()
    _log()
    _log("All reindexes complete. Verify the reclaim with: --verify")
    _log("Expected: combined with the SEED-035 PK shrink (~1.45 GB), the game_positions")
    _log("index set reclaims on the order of ~1 GB from this pass.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "PROD-ONLY, HUMAN-run REINDEX of the two game_positions indexes the SEED-035 "
            "migration leaves bloated (ix_gp_user_endgame_game, ix_game_positions_game_id)."
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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the exact REINDEX statements without connecting to or touching any DB.",
    )
    mode.add_argument(
        "--verify",
        action="store_true",
        help="Print the current on-disk size of each index (read-only; no rebuild).",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    target: DbTarget = args.db
    _validate_indexes(INDEXES)

    if args.dry_run:
        _print_dry_run(target, INDEXES)
        return

    url = _db_url(target)
    _assert_target_safe(url, target)

    if args.verify:
        await _run_verify(url, INDEXES)
        return

    if not _confirm(target, INDEXES):
        _log("Aborted — no changes made.")
        raise SystemExit(1)

    await _run_reindex(url, INDEXES)


if __name__ == "__main__":
    asyncio.run(main())
