"""Validate computed accuracy/ACPL against the preserved *_imported values (D-07).

Why this script exists
-----------------------
Phase 178 repurposed `games.white_accuracy` / `black_accuracy` / `white_acpl` /
`black_acpl` to hold OUR uniform lichess-formula computation
(`app.services.accuracy_acpl.compute_game_accuracy_acpl`), preserving the
platform-reported values in the new `*_imported` columns (Plan 01). This is a
read-mostly, operator-run comparison confirming our computed numbers track
lichess's own values for lichess games — the empirical correctness check
called for by D-07.

Three signals (178-RESEARCH.md SS "Validation Script (D-07)"):
  1. PRIMARY -- computed ACPL vs `*_acpl_imported` (lichess-only, sparse; same
     formula, so this is the strongest signal). Expect near-exact match
     (+/- 1-2 from rounding).
  2. SECONDARY -- computed accuracy vs `*_accuracy_imported` for LICHESS-
     provenance rows only (`lichess_evals_at IS NOT NULL`) -- lichess computed
     this with the exact formula we ported, so it should track closely too
     (+/- 1-3).
  3. DIVERGENT-BY-DESIGN -- `*_accuracy_imported` for chess.com-provenance rows
     (`lichess_evals_at IS NULL`) uses chess.com's OWN (different) accuracy
     formula. A systematic offset here is EXPECTED and is reported separately,
     never as a failure (178-RESEARCH.md SS "Provenance correction").

This is a manual-inspection tool (VALIDATION.md Manual-Only), not a pass/fail
gate -- it always exits 0. Any lichess game whose ACPL delta exceeds tolerance
is printed by (game_id, color, delta) for manual follow-up (likely a holed /
mate edge case the Complete-Sequence Gate let through as hole-free but whose
result still diverges).

DB target host:port mapping (CLAUDE.md):
    dev:       localhost:5432  (Docker compose flawchess-dev)
    benchmark: localhost:5433  (Docker compose flawchess-benchmark)
    prod:      localhost:15432 (via bin/prod_db_tunnel.sh)

Usage:
    uv run python scripts/validate_accuracy_acpl.py --db dev
    uv run python scripts/validate_accuracy_acpl.py --db dev --user-id 13
    bin/prod_db_tunnel.sh
    uv run python scripts/validate_accuracy_acpl.py --db prod
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import db_url_for_target  # noqa: E402
from app.models.game import Game  # noqa: E402

# Joining/selecting Game forces SQLAlchemy to configure the mapper chain, and
# User in turn declares a relationship to OAuthAccount, so both must be
# imported/registered or mapper configuration fails at query time (pattern
# from backfill_full_evals.py / backfill_best_move_pv.py).
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401

# Rounding-only divergence tolerance (RESEARCH.md § "Validation Script (D-07)"):
# the primary ACPL signal should match near-exactly since both sides used the
# same formula; the secondary accuracy signal tolerates a bit more drift from
# the windowed-aggregation's floating-point path.
ACPL_TOLERANCE = 2
ACCURACY_TOLERANCE = 3

# Cap on the number of outlier rows printed per section, to keep output
# readable on a large corpus while still surfacing enough for manual triage.
MAX_OUTLIERS_PRINTED = 20

Color = str  # "white" | "black" -- kept a plain str (not Literal) here since it
# only ever flows into an f-string label, never a branch.


def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def _db_url(target: str) -> str:
    """Resolve the asyncpg URL for the chosen --db target (via .env)."""
    return db_url_for_target(target)


@dataclass(frozen=True)
class DeltaStats:
    """Summary statistics for one comparison's absolute-delta distribution."""

    n: int
    mean: float
    median: float
    p95: float
    exceeding_tolerance: int


def _delta_stats(deltas: Sequence[float], tolerance: float) -> DeltaStats | None:
    """Compute mean/median/p95 + tolerance-exceedance count. None if no rows."""
    if not deltas:
        return None
    ordered = sorted(deltas)
    n = len(ordered)
    p95_index = min(n - 1, round(0.95 * (n - 1)))
    return DeltaStats(
        n=n,
        mean=statistics.mean(ordered),
        median=statistics.median(ordered),
        p95=ordered[p95_index],
        exceeding_tolerance=sum(1 for d in ordered if d > tolerance),
    )


def _print_stats(label: str, stats: DeltaStats | None, tolerance: float) -> None:
    """Log a one-line summary for a DeltaStats result (or a no-rows note)."""
    if stats is None:
        _log(f"{label}: no rows to compare.")
        return
    _log(
        f"{label}: n={stats.n} mean={stats.mean:.2f} median={stats.median:.2f} "
        f"p95={stats.p95:.2f} exceeding_tolerance(>{tolerance})={stats.exceeding_tolerance}"
    )


def _print_outliers(label: str, outliers: Sequence[tuple[int, Color, float]]) -> None:
    """Log up to MAX_OUTLIERS_PRINTED (game_id, color, delta) rows for triage."""
    if not outliers:
        return
    shown = outliers[:MAX_OUTLIERS_PRINTED]
    _log(f"{label}: {len(outliers)} outlier(s), showing up to {MAX_OUTLIERS_PRINTED}:")
    for game_id, color, delta in shown:
        _log(f"    game_id={game_id} color={color} delta={delta:.2f}")


async def _fetch_primary_acpl_deltas(
    session: AsyncSession, user_id: int | None
) -> tuple[list[float], list[tuple[int, Color, float]]]:
    """PRIMARY signal: computed ACPL vs lichess's own `*_acpl_imported`.

    Scope: rows where `white_acpl_imported IS NOT NULL` (the lichess-only,
    sparse provenance gate for this column — RESEARCH.md's provenance table)
    AND the canonical `white_acpl`/`black_acpl` are already populated (this
    backfill/hook has run for the game).
    """
    stmt = select(
        Game.id,
        Game.white_acpl,
        Game.black_acpl,
        Game.white_acpl_imported,
        Game.black_acpl_imported,
    ).where(Game.white_acpl_imported.isnot(None), Game.white_acpl.isnot(None))
    if user_id is not None:
        stmt = stmt.where(Game.user_id == user_id)

    rows = (await session.execute(stmt)).all()
    deltas: list[float] = []
    outliers: list[tuple[int, Color, float]] = []
    for row in rows:
        for color, computed, imported in (
            ("white", row.white_acpl, row.white_acpl_imported),
            ("black", row.black_acpl, row.black_acpl_imported),
        ):
            if computed is None or imported is None:
                continue
            delta = float(abs(computed - imported))
            deltas.append(delta)
            if delta > ACPL_TOLERANCE:
                outliers.append((row.id, color, delta))
    return deltas, outliers


async def _fetch_accuracy_deltas(
    session: AsyncSession, user_id: int | None, *, lichess_provenance: bool
) -> list[float]:
    """SECONDARY (lichess_provenance=True) / DIVERGENT-BY-DESIGN (=False).

    Scope: rows where `white_accuracy_imported IS NOT NULL` AND the canonical
    `white_accuracy`/`black_accuracy` are populated, split by
    `lichess_evals_at` provenance (RESEARCH.md's mixed-provenance
    `*_accuracy_imported` table — chess.com formula when NULL, lichess formula
    (same as ours) when NOT NULL).
    """
    stmt = select(
        Game.id,
        Game.white_accuracy,
        Game.black_accuracy,
        Game.white_accuracy_imported,
        Game.black_accuracy_imported,
    ).where(Game.white_accuracy_imported.isnot(None), Game.white_accuracy.isnot(None))
    if lichess_provenance:
        stmt = stmt.where(Game.lichess_evals_at.isnot(None))
    else:
        stmt = stmt.where(Game.lichess_evals_at.is_(None))
    if user_id is not None:
        stmt = stmt.where(Game.user_id == user_id)

    rows = (await session.execute(stmt)).all()
    deltas: list[float] = []
    for row in rows:
        for computed, imported in (
            (row.white_accuracy, row.white_accuracy_imported),
            (row.black_accuracy, row.black_accuracy_imported),
        ):
            if computed is None or imported is None:
                continue
            deltas.append(abs(computed - imported))
    return deltas


async def run_validation(
    *,
    db: str,
    user_id: int | None,
    _session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Read-mostly D-07 comparison driver. Public callable for testability.

    `_session_maker` is an internal test hook; production callers omit it.
    Always completes normally (exit 0) -- this is a manual-inspection report,
    not a pass/fail gate.
    """
    dispose_engine = _session_maker is None
    if _session_maker is None:
        async_engine = create_async_engine(_db_url(db), pool_pre_ping=True)
        session_maker = async_sessionmaker(async_engine, expire_on_commit=False)
    else:
        async_engine = None  # type: ignore[assignment]  # not created here; nothing to dispose
        session_maker = _session_maker

    async with session_maker() as session:
        primary_deltas, primary_outliers = await _fetch_primary_acpl_deltas(session, user_id)
        secondary_deltas = await _fetch_accuracy_deltas(session, user_id, lichess_provenance=True)
        divergent_deltas = await _fetch_accuracy_deltas(session, user_id, lichess_provenance=False)

    _log("=" * 72)
    _log("PRIMARY -- computed ACPL vs lichess *_acpl_imported (expect +/- 1-2)")
    _log("=" * 72)
    _print_stats("ACPL delta", _delta_stats(primary_deltas, ACPL_TOLERANCE), ACPL_TOLERANCE)
    _print_outliers("ACPL outliers (likely holed/mate edge cases)", primary_outliers)

    _log("")
    _log("=" * 72)
    _log("SECONDARY -- computed accuracy vs lichess *_accuracy_imported (expect +/- 1-3)")
    _log("=" * 72)
    _print_stats(
        "Accuracy delta (lichess provenance)",
        _delta_stats(secondary_deltas, ACCURACY_TOLERANCE),
        ACCURACY_TOLERANCE,
    )

    _log("")
    _log("=" * 72)
    _log(
        "DIVERGENT-BY-DESIGN -- computed accuracy vs chess.com *_accuracy_imported "
        "(chess.com's own formula -- a systematic offset here is EXPECTED, NOT a failure)"
    )
    _log("=" * 72)
    _print_stats(
        "Accuracy delta (chess.com provenance)",
        _delta_stats(divergent_deltas, ACCURACY_TOLERANCE),
        ACCURACY_TOLERANCE,
    )

    if dispose_engine and async_engine is not None:
        await async_engine.dispose()


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Compare computed accuracy/ACPL against the preserved *_imported "
            "values (Phase 178 D-07). Read-mostly, always exits 0."
        )
    )
    parser.add_argument(
        "--db",
        choices=["dev", "benchmark", "prod"],
        required=True,
        help=(
            "Database target. dev=localhost:5432, benchmark=localhost:5433, "
            "prod=localhost:15432 (via bin/prod_db_tunnel.sh). REQUIRED."
        ),
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=None,
        dest="user_id",
        metavar="N",
        help="Limit the comparison to a single user ID. Default: all users.",
    )
    return parser.parse_args()


async def main() -> None:
    """Entry point: parse CLI args, run the validation report."""
    args = parse_args()
    _log(f"Starting accuracy/ACPL validation: db={args.db} user_id={args.user_id}")
    await run_validation(db=args.db, user_id=args.user_id)
    _log("Done.")


if __name__ == "__main__":
    asyncio.run(main())
