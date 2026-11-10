"""Blunder-check calibration report (SEED-261108-dk0, Phase 248, D-13..D-16, D-23).

Read-only: samples fully evaluated games deterministically, rebuilds per-ply severities and
expected scores through the flaw classifier's own pass, and writes a dated markdown report of
the findability, eval-band, window-fit and supply statistics the blunder-check selection will
be built on. Every database session opens with default_transaction_read_only = on and a named
statement timeout (T-248-08, T-248-09); the script contains no write statement.

DB target host:port mapping (CLAUDE.md):
    dev:  localhost:5432  (Docker compose flawchess-dev)
    prod: localhost:15432 (via bin/prod_db_tunnel.sh)
The URL comes from DATABASE_URL_{DEV,PROD} (.env) via app.core.config.db_url_for_target and is
never printed. The benchmark DB is out of scope (D-19). On prod run it only when no backfill is
running.

Usage:
    uv run python scripts/blunder_check_calibration.py --db dev --sample-permille 1000 \\
        --limit-games 500 --out-dir temp/blunder-check --overwrite
    uv run python scripts/blunder_check_calibration.py --db dev --cache temp/blunder-check/dev-cache.json
    uv run python scripts/blunder_check_calibration.py --from-cache temp/blunder-check/dev-cache.json

Maia (D-17): unless --oddness-sample 0 or --from-cache, the script starts one single-threaded
ORT session (needs `uv sync --group maia-inference`) and exits 3 when it is unavailable. The
spot-check (D-18) is written next to the report as spot-check-{date}.md.
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

# Bootstrap project root so `app.*` imports resolve when running as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.core.config import db_url_for_target  # noqa: E402

# Game.user_id has a FK to users.id and User declares a relationship to OAuthAccount, so the
# mapped classes must all be imported before any select() against them compiles.
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.services import maia_engine  # noqa: E402
from scripts.blunder_check.oddness import (  # noqa: E402
    DEFAULT_SEED,
    ODDNESS_GOOD_MOVES_PER_BUCKET,
    score_good_moves,
    select_good_moves,
)
from scripts.blunder_check.render import (  # noqa: E402
    DEFAULT_BAND,
    DEFAULT_MISS_THRESHOLD,
    DEFAULT_REFUTATION_THRESHOLD,
    MIN_USER_WINDOWS,
    ReportParams,
    render_report,
)
from scripts.blunder_check.spot_check import (  # noqa: E402
    DEFAULT_SPOT_CHECK_PER_BUCKET,
    SpotCheckParams,
    fetch_window_details,
    pick_windows,
    render_spot_check,
)
from scripts.blunder_check.sample import (  # noqa: E402
    DEFAULT_BATCH_GAMES,
    PERMILLE_BASE,
    Collection,
    RunMeta,
    collect_sample,
    fetch_user_groups,
    make_readonly_engine,
    read_cache,
    select_sample_game_ids,
    write_cache,
)

DEFAULT_SAMPLE_PERMILLE: int = 25
DEFAULT_OUT_DIR: Path = Path("reports") / "blunder-check"
DATE_FORMAT: str = "%Y-%m-%d"
REPORT_FILE_TEMPLATE: str = "blunder-check-calibration-{date}.md"
SPOT_CHECK_FILE_TEMPLATE: str = "spot-check-{date}.md"
EXIT_OK: int = 0
# Same value as scripts/backfill_maia_flaws.py EXIT_MAIA_UNAVAILABLE.
EXIT_MAIA_UNAVAILABLE: int = 3
EXIT_EXISTS: int = 4
EXIT_NOTHING_COLLECTED: int = 5

DB_CHOICES: tuple[str, ...] = ("dev", "prod")


def _log(msg: str = "") -> None:
    """Print a UTC-timestamped line, flushed (Python 3.14 block-buffers redirected stdout)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only blunder-check calibration report")
    parser.add_argument(
        "--db",
        choices=list(DB_CHOICES),
        default=None,
        help="DB target: dev (5432) or prod (via bin/prod_db_tunnel.sh). Required unless --from-cache.",
    )
    parser.add_argument(
        "--sample-permille",
        type=int,
        default=DEFAULT_SAMPLE_PERMILLE,
        dest="sample_permille",
        help=f"Games sampled, in permille of the population (1..{PERMILLE_BASE}).",
    )
    parser.add_argument("--limit-games", type=int, default=None, dest="limit_games")
    parser.add_argument("--batch-games", type=int, default=DEFAULT_BATCH_GAMES, dest="batch_games")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, dest="out_dir")
    parser.add_argument(
        "--date",
        default=None,
        help="Report date YYYY-MM-DD (default: today, UTC). Names the output file.",
    )
    parser.add_argument("--cache", type=Path, default=None, help="Also write the collection here.")
    parser.add_argument(
        "--from-cache",
        type=Path,
        default=None,
        dest="from_cache",
        help="Render from a cache file without opening the database.",
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--oddness-sample",
        type=int,
        default=ODDNESS_GOOD_MOVES_PER_BUCKET,
        dest="oddness_sample",
        help="Judged Good user moves scored with Maia per Elo bucket (0 skips Maia entirely).",
    )
    parser.add_argument(
        "--spot-check-per-bucket",
        type=int,
        default=DEFAULT_SPOT_CHECK_PER_BUCKET,
        dest="spot_check_per_bucket",
        help="Hazard-model windows per Elo bucket in the spot-check file (0 skips it).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Seed for the Good-move sample and the spot-check draws.",
    )
    parser.add_argument(
        "--refutation-threshold",
        type=float,
        default=DEFAULT_REFUTATION_THRESHOLD,
        dest="refutation_threshold",
    )
    parser.add_argument(
        "--miss-threshold", type=float, default=DEFAULT_MISS_THRESHOLD, dest="miss_threshold"
    )
    parser.add_argument("--band-low", type=float, default=DEFAULT_BAND[0], dest="band_low")
    parser.add_argument("--band-high", type=float, default=DEFAULT_BAND[1], dest="band_high")
    parser.add_argument(
        "--min-user-windows", type=int, default=MIN_USER_WINDOWS, dest="min_user_windows"
    )
    args = parser.parse_args(argv)
    if args.from_cache is None and args.db is None:
        parser.error("--db is required unless --from-cache is given")
    if args.from_cache is not None and args.cache is not None:
        parser.error("--cache and --from-cache are mutually exclusive")
    if not 1 <= args.sample_permille <= PERMILLE_BASE:
        parser.error(f"--sample-permille must be between 1 and {PERMILLE_BASE}")
    if args.oddness_sample < 0 or args.spot_check_per_bucket < 0:
        parser.error("--oddness-sample and --spot-check-per-bucket must be >= 0")
    if args.batch_games < 1:
        parser.error("--batch-games must be at least 1")
    if not 0.0 <= args.band_low < args.band_high <= 1.0:
        parser.error("need 0 <= --band-low < --band-high <= 1")
    return args


async def _banner(session: AsyncSession, db: str) -> str:
    """Show which database this run targets (name and server address), never its URL."""
    row = (
        await session.execute(
            text("SELECT current_database(), inet_server_addr(), inet_server_port()")
        )
    ).one()
    _log(f"target: --db {db} -> database={row[0]} server={row[1]}:{row[2]}")
    return str(row[0])


async def _collect(args: argparse.Namespace, date: str) -> Collection:
    """Sample the target DB through one read-only connection; the engine is disposed in finally."""
    engine = make_readonly_engine(db_url_for_target(args.db))
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            db_name = await _banner(session, args.db)
            game_ids = await select_sample_game_ids(
                session, permille=args.sample_permille, limit=args.limit_games
            )
            _log(f"sampled {len(game_ids)} game ids at {args.sample_permille} permille")
            meta = RunMeta(
                db_name=db_name,
                db_target=args.db,
                date=date,
                permille=args.sample_permille,
                limit_games=args.limit_games,
                seed=args.seed,
                oddness_sample=args.oddness_sample,
            )
            collection = await collect_sample(session, game_ids, args.batch_games, meta)
            collection.user_groups = await fetch_user_groups(session)
            _log(f"aggregated {len(collection.user_groups)} per-user groups")
        # The session is closed here: Maia inference below holds no database session (the engine
        # has a pool of one, and PGN batches reopen it briefly).
        if args.oddness_sample > 0:
            await _score_oddness(engine, collection, args)
        return collection
    finally:
        await engine.dispose()


async def _score_oddness(
    engine: AsyncEngine, collection: Collection, args: argparse.Namespace
) -> None:
    """D-17: score the seeded Good-move sample with Maia and store it in the collection."""
    targets = select_good_moves(collection, args.oddness_sample, args.seed)
    pinned = {g.game_id: g.elo for g in collection.games if g.elo is not None}
    _log(f"scoring {len(targets)} Good moves with Maia")
    maker = async_sessionmaker(engine, expire_on_commit=False)
    scored = await score_good_moves(maker, targets, pinned)
    collection.oddness = scored.records
    collection.meta.oddness_skipped = scored.skipped
    _log(f"scored {len(scored.records)} Good moves ({scored.skipped} not scorable)")


def _output_path(args: argparse.Namespace, date: str) -> Path:
    return args.out_dir / REPORT_FILE_TEMPLATE.format(date=date)


async def _start_maia() -> bool:
    """Start one single-threaded ORT session (D-17); False when Maia cannot be served here."""
    await maia_engine.start_maia(intra_op_num_threads=1)
    if maia_engine.is_maia_available():
        return True
    _log(
        "Maia unavailable: install the isolated group (`uv sync --group maia-inference`) and "
        "make sure the ONNX model file is present; or pass --oddness-sample 0 / --from-cache"
    )
    return False


async def _collect_and_cache(args: argparse.Namespace, date: str) -> Collection | None:
    collection = await _collect(args, date)
    if not collection.games:
        _log("nothing collected: no sampled game produced a record")
        return None
    if args.cache is not None:
        write_cache(collection, args.cache)
        _log(f"wrote cache {args.cache}")
    return collection


def _spot_check_path(args: argparse.Namespace, date: str) -> Path:
    return args.out_dir / SPOT_CHECK_FILE_TEMPLATE.format(date=date)


async def _write_spot_check(
    target: str, collection: Collection, params: ReportParams, args: argparse.Namespace, path: Path
) -> None:
    """Draw the hazard-model windows and resolve them through one read-only connection (D-18)."""
    spot_params = SpotCheckParams(params, args.spot_check_per_bucket)
    windows = pick_windows(collection, spot_params, random.Random(args.seed))
    engine = make_readonly_engine(db_url_for_target(target))
    try:
        details = await fetch_window_details(
            async_sessionmaker(engine, expire_on_commit=False), windows
        )
    finally:
        await engine.dispose()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_spot_check(details, spot_params))
    _log(f"wrote spot-check {path} ({len(details)} windows)")


async def _run(args: argparse.Namespace) -> int:
    date = args.date or datetime.now(timezone.utc).strftime(DATE_FORMAT)
    out_path = _output_path(args, date)
    spot_path = _spot_check_path(args, date)
    for existing in (out_path, spot_path):
        if existing.exists() and not args.overwrite:
            _log(f"refusing to overwrite {existing} (pass --overwrite)")
            return EXIT_EXISTS
    collection: Collection | None
    if args.from_cache is not None:
        collection = read_cache(args.from_cache)
    else:
        need_maia = args.oddness_sample > 0
        if need_maia and not await _start_maia():
            return EXIT_MAIA_UNAVAILABLE
        try:
            collection = await _collect_and_cache(args, date)
        finally:
            if need_maia:
                await maia_engine.stop_maia()
        if collection is None:
            return EXIT_NOTHING_COLLECTED
    # The spot-check needs a database for PGNs and refutation moves: --db wins, else the cache's.
    target = args.db or collection.meta.db_target
    want_spot_check = args.spot_check_per_bucket > 0
    if want_spot_check and not target:
        _log("skipping the spot-check: the cache has no db target; pass --db")
        want_spot_check = False
    params = ReportParams(
        refutation_threshold=args.refutation_threshold,
        miss_threshold=args.miss_threshold,
        band_low=args.band_low,
        band_high=args.band_high,
        min_user_windows=args.min_user_windows,
        spot_check_file=spot_path.name if want_spot_check else None,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_report(collection, params))
    _log(f"wrote report {out_path}")
    if want_spot_check:
        await _write_spot_check(target, collection, params, args, spot_path)
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
