"""Clear the stale lichess provenance stamp on games whose lichess %evals were overwritten.

WHY THIS EXISTS (SEED-202 item 1)
    Until 4183e25fb the bundled tier-4 blob claim hard-coded
    ``is_lichess_eval_game=False``. The in-process server-pool drain trusts that
    flag, so for a lichess-eval game it ran the engine write path: the game's
    lichess ``%eval`` values in ``game_positions`` were replaced by our own
    Stockfish evals (correctly aligned, post-move), and flaws/accuracy were
    reclassified from them. ``games.lichess_evals_at`` stayed set, so the app
    still treats those games as lichess-eval games. On prod (2026-10-17) about
    4,000 non-guest games were affected.

    The stored evals are genuine engine evals, internally consistent with the
    stored best moves, PVs and flaws, so the fix is to make the provenance
    true rather than to restore the lichess evals: NULL ``lichess_evals_at``
    so the games count as analyzed by us. The lichess evals stay in the PGN.

DETECTION
    For each non-guest game with ``lichess_evals_at`` and
    ``full_evals_completed_at`` set, the n-th ``[%eval]`` in the PGN is compared
    with ``game_positions.eval_cp`` at ply n-1 (lichess storage is post-move)
    and, as a control, at ply n (the separate one-ply-shift defect, which still
    holds lichess values and must NOT be relabelled). A game is flagged when
    both match rates are below MAX_MATCH_RATIO and it has at least MIN_EVALS
    centipawn evals. Mate evals are skipped. Untouched games match ~100%.

SUBCOMMANDS
    scan     Find flagged games and write them (with their current
             lichess_evals_at, for restore) to a JSON file. Read-only.
    apply    Re-check the listed games and NULL lichess_evals_at on the ones
             still flagged. Dry run unless --execute.
    restore  Put the saved lichess_evals_at back on the listed games that are
             still NULL. Dry run unless --execute.

    --execute against prod asks for confirmation (or pass --yes).

Usage:
    bin/prod_db_tunnel.sh
    uv run python scripts/fix_lichess_eval_provenance.py scan --db prod
    uv run python scripts/fix_lichess_eval_provenance.py apply --db prod
    uv run python scripts/fix_lichess_eval_provenance.py apply --db prod --execute
    uv run python scripts/fix_lichess_eval_provenance.py restore --db prod --execute
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, TypedDict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import db_url_for_target  # noqa: E402

DbTarget = Literal["dev", "benchmark", "prod"]
ALLOWED_DB_TARGETS: tuple[DbTarget, ...] = ("dev", "benchmark", "prod")

# A game is flagged when fewer than this share of its %evals match the stored
# eval at either alignment. Measured on prod: untouched games sit at ~100%,
# overwritten ones mostly under 10%.
MAX_MATCH_RATIO = 0.5
# Too few evals make the ratio meaningless (a short game can match by chance).
MIN_EVALS = 10
# Candidate games are scanned in id windows of this width, for progress output
# and to keep each statement short over the prod tunnel.
SCAN_ID_WINDOW = 20_000
DEFAULT_IDS_FILE = Path("temp/lichess-provenance-fix/flagged-games.json")
CENTIPAWNS_PER_PAWN = 100

ScopeKind = Literal["window", "ids"]

_SCOPE_SQL: dict[ScopeKind, str] = {
    "window": "g.id >= :lo AND g.id < :hi",
    "ids": "g.id = ANY(CAST(:ids AS bigint[]))",
}


def _classify_sql(scope: ScopeKind) -> str:
    # Only the fixed scope fragment is interpolated; every value is a bind param.
    return f"""
    WITH cand AS (
      SELECT g.id, g.user_id, g.pgn, g.lichess_evals_at
      FROM games g JOIN users u ON u.id = g.user_id
      WHERE g.lichess_evals_at IS NOT NULL
        AND g.full_evals_completed_at IS NOT NULL
        AND NOT u.is_guest
        AND {_SCOPE_SQL[scope]}
    ), ev AS (
      SELECT c.id, c.user_id, m.n,
             round(CAST(m.v[1] AS numeric) * :cp_per_pawn) AS cp
      FROM cand c,
           regexp_matches(c.pgn, '\\[%eval (-?[0-9.]+)\\]', 'g') WITH ORDINALITY AS m(v, n)
    ), per AS (
      SELECT ev.id,
             count(*) AS n_evals,
             count(*) FILTER (WHERE post.eval_cp = ev.cp) AS post_matches,
             count(*) FILTER (WHERE shifted.eval_cp = ev.cp) AS shifted_matches
      FROM ev
      LEFT JOIN game_positions post
        ON post.game_id = ev.id AND post.user_id = ev.user_id AND post.ply = ev.n - 1
      LEFT JOIN game_positions shifted
        ON shifted.game_id = ev.id AND shifted.user_id = ev.user_id AND shifted.ply = ev.n
      GROUP BY ev.id
    )
    SELECT per.id, c.user_id, c.lichess_evals_at,
           per.n_evals, per.post_matches, per.shifted_matches
    FROM per JOIN cand c ON c.id = per.id
    WHERE per.n_evals >= :min_evals
      -- Explicit cast: asyncpg otherwise infers the param as bigint from n_evals.
      AND per.post_matches < CAST(:max_ratio AS double precision) * per.n_evals
      AND per.shifted_matches < CAST(:max_ratio AS double precision) * per.n_evals
    ORDER BY per.id
    """


class FlaggedGame(TypedDict):
    id: int
    user_id: int
    lichess_evals_at: str  # ISO 8601, the value to restore
    n_evals: int
    post_matches: int
    shifted_matches: int


def _classify_params() -> dict[str, float | int]:
    return {
        "cp_per_pawn": CENTIPAWNS_PER_PAWN,
        "min_evals": MIN_EVALS,
        "max_ratio": MAX_MATCH_RATIO,
    }


async def _classify(
    session: AsyncSession, scope: ScopeKind, scope_params: dict[str, object]
) -> list[FlaggedGame]:
    result = await session.execute(
        text(_classify_sql(scope)), {**_classify_params(), **scope_params}
    )
    return [
        FlaggedGame(
            id=row.id,
            user_id=row.user_id,
            lichess_evals_at=row.lichess_evals_at.isoformat(),
            n_evals=row.n_evals,
            post_matches=row.post_matches,
            shifted_matches=row.shifted_matches,
        )
        for row in result
    ]


async def scan(session: AsyncSession, *, verbose: bool = False) -> list[FlaggedGame]:
    """Return every flagged game, scanning candidate ids window by window."""
    bounds = (
        await session.execute(
            text(
                "SELECT min(id), max(id) FROM games "
                "WHERE lichess_evals_at IS NOT NULL AND full_evals_completed_at IS NOT NULL"
            )
        )
    ).one()
    lo, hi = bounds
    if lo is None:
        return []
    flagged: list[FlaggedGame] = []
    for window_lo in range(lo, hi + 1, SCAN_ID_WINDOW):
        window_hi = window_lo + SCAN_ID_WINDOW
        flagged += await _classify(session, "window", {"lo": window_lo, "hi": window_hi})
        if verbose:
            print(f"  ids < {window_hi:,} of {hi:,}: {len(flagged):,} flagged", flush=True)
    return flagged


async def apply_fix(session: AsyncSession, games: Sequence[FlaggedGame]) -> list[int]:
    """NULL lichess_evals_at on the listed games that are still flagged; return their ids.

    Re-checks the listed games first, so a game whose evals changed since the
    scan (or a doctored list) is never relabelled. Does not commit.
    """
    listed = [g["id"] for g in games]
    still_flagged = [g["id"] for g in await _classify(session, "ids", {"ids": listed})]
    if not still_flagged:
        return []
    result = await session.execute(
        text(
            "UPDATE games SET lichess_evals_at = NULL "
            "WHERE id = ANY(CAST(:ids AS bigint[])) AND lichess_evals_at IS NOT NULL "
            "RETURNING id"
        ),
        {"ids": still_flagged},
    )
    return sorted(result.scalars().all())


async def restore(session: AsyncSession, games: Sequence[FlaggedGame]) -> list[int]:
    """Put the saved lichess_evals_at back where it is still NULL; return those ids.

    Does not commit.
    """
    if not games:
        return []
    result = await session.execute(
        text(
            "UPDATE games g SET lichess_evals_at = v.ts "
            "FROM unnest(CAST(:ids AS bigint[]), CAST(:ts AS timestamptz[])) AS v(id, ts) "
            "WHERE g.id = v.id AND g.lichess_evals_at IS NULL "
            "RETURNING g.id"
        ),
        {
            "ids": [g["id"] for g in games],
            "ts": [datetime.datetime.fromisoformat(g["lichess_evals_at"]) for g in games],
        },
    )
    return sorted(result.scalars().all())


def _write_ids_file(path: Path, db: DbTarget, games: Sequence[FlaggedGame]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "db": db,
        "scanned_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "criteria": {"max_match_ratio": MAX_MATCH_RATIO, "min_evals": MIN_EVALS},
        "games": list(games),
    }
    path.write_text(json.dumps(payload, indent=1))


def _read_ids_file(path: Path, db: DbTarget) -> list[FlaggedGame]:
    payload = json.loads(path.read_text())
    if payload["db"] != db:
        raise SystemExit(f"{path} was scanned on --db {payload['db']}, not --db {db}")
    return payload["games"]


def _confirm_prod(args: argparse.Namespace, action: str, n: int) -> None:
    if args.db != "prod" or args.yes:
        return
    answer = input(f"{action} {n:,} games on PROD. Type 'prod' to continue: ")
    if answer.strip() != "prod":
        raise SystemExit("Aborted.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0] if __doc__ else None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("command", choices=("scan", "apply", "restore"))
    parser.add_argument("--db", choices=ALLOWED_DB_TARGETS, required=True)
    parser.add_argument("--ids-file", type=Path, default=DEFAULT_IDS_FILE)
    parser.add_argument(
        "--execute", action="store_true", help="Commit apply/restore (default: dry run)."
    )
    parser.add_argument("--yes", action="store_true", help="Skip the prod confirmation.")
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> None:
    engine = create_async_engine(db_url_for_target(args.db))
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_maker() as session:
            if args.command == "scan":
                flagged = await scan(session, verbose=True)
                _write_ids_file(args.ids_file, args.db, flagged)
                users = len({g["user_id"] for g in flagged})
                print(f"Flagged {len(flagged):,} games ({users:,} users) -> {args.ids_file}")
                return

            games = _read_ids_file(args.ids_file, args.db)
            if args.execute:
                _confirm_prod(args, args.command.capitalize(), len(games))
            changed = await (apply_fix if args.command == "apply" else restore)(session, games)
            if args.execute:
                await session.commit()
                print(f"{args.command}: {len(changed):,} of {len(games):,} listed games updated.")
            else:
                await session.rollback()
                print(
                    f"DRY RUN {args.command}: would update {len(changed):,} of "
                    f"{len(games):,} listed games. Re-run with --execute to commit."
                )
    finally:
        await engine.dispose()


def main() -> None:
    asyncio.run(_run(_parse_args()))


if __name__ == "__main__":
    main()
