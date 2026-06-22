"""Refresh ONLY the tactic-tag columns on existing game_flaws rows.

Run this after changing the tactic detector (app/services/tactic_detector.py) or the
tactic-tagging logic in flaws_service.py. It recomputes the 8 tactic columns
(allowed_tactic_motif/piece/confidence/depth + missed_tactic_*) for already-materialized
flaws and writes them back with a targeted UPDATE — no delete-and-reinsert.

Why a dedicated script instead of backfill_flaws.py:
    backfill_flaws.py rebuilds EVERY flaw row from scratch: it scans all full-eval'd
    games, loads all of each game's positions, recomputes severity/tempo/phase/eval
    smoothing, then DELETEs and re-INSERTs the rows. When only the tactic detector
    changed, that is wasteful. This script instead:
      * walks game_flaws directly in PK-ordered pages (a flaw with no detector input is
        the unit of work — games without flaws are never touched),
      * loads only the positions at each flaw's ply and ply+1 (the exact PV / mate inputs
        the detector needs), one batched query per page, not per game,
      * recomputes the tactic tags via the SAME _detect_tactic_for_flaw kernel the live
        eval drain uses (parity guaranteed — no drift),
      * UPDATEs only the 8 tactic columns, and only for rows whose tags actually changed
        (no-op rows are skipped, minimizing WAL).

Constraining the work further (the more you constrain, the fewer rows are touched):
    --user-id N     Only this user's flaws.
    --only-tagged   Only flaws that ALREADY carry a tactic tag (allowed or missed motif
                    non-null). Use this for precision-tightening detector changes (removing
                    false positives within existing motifs). CAVEAT: it will NOT pick up
                    NEW detections — if your change makes a detector fire where it didn't
                    before, those currently-untagged rows are skipped. Omit it for a full
                    refresh after a recall-affecting change.
    --limit N       Process at most N flaw rows (smoke tests).

Batching is MANDATORY given the project's OOM history (CLAUDE.md): commit every
FLAWS_PER_BATCH rows; no asyncio.gather on the same session.

DB target host:port mapping (CLAUDE.md):
    dev:       localhost:5432  (Docker compose flawchess-dev)
    benchmark: localhost:5433  (Docker compose flawchess-benchmark)
    prod:      localhost:15432 (via bin/prod_db_tunnel.sh)

Usage:
    uv run python scripts/backfill_tactic_tags.py --db dev --dry-run
    uv run python scripts/backfill_tactic_tags.py --db dev --user-id 28
    uv run python scripts/backfill_tactic_tags.py --db dev --only-tagged
    uv run python scripts/backfill_tactic_tags.py --db prod --user-id 28
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sentry_sdk
from sqlalchemy import Row, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import db_url_for_target, settings  # noqa: E402
from app.models.game_flaw import GameFlaw  # noqa: E402
from app.models.game_position import GamePosition  # noqa: E402

# GameFlaw/GamePosition carry FKs to games → users → oauth_accounts. Importing only the
# queried models leaves those parent tables unregistered and select() raises
# NoReferencedTableError at compile time, so register the whole chain.
from app.models.game import Game  # noqa: E402, F401
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.repositories.game_flaws_repository import (  # noqa: E402
    TACTIC_TAG_COLUMNS,
    bulk_update_tactic_tags,
)

# _detect_tactic_for_flaw is the single tactic-detection kernel shared with the live eval
# drain (app/services/flaws_service.py). Importing it here — rather than reimplementing the
# allowed/missed PV + dest-square + forced-mate logic — guarantees the backfilled tags match
# exactly what a fresh classify would produce (D-10 no-drift posture).
from app.services.flaws_service import _detect_tactic_for_flaw  # noqa: E402

# No magic numbers (CLAUDE.md rule).
# Commit every N flaw rows to keep memory bounded (OOM history — see CLAUDE.md).
FLAWS_PER_BATCH = 2000


@dataclass(frozen=True)
class _PosRow:
    """Minimal position view the tactic kernel reads (move_san / pv / eval_mate).

    _detect_tactic_for_flaw only touches these three attributes plus integer indexing
    and len() on the positions list, so a full GamePosition load is unnecessary.
    """

    move_san: str | None
    pv: str | None
    eval_mate: int | None


# Placeholder for plies we never loaded (the gaps before a flaw's ply in its per-flaw view).
# The kernel only indexes the flaw ply and flaw_ply+1; a None-valued placeholder elsewhere is
# never read for a meaningful result (pv=None → the kernel returns no tag), but must exist so
# integer indexing and the `n + 1 < len(positions)` guard behave.
_EMPTY_POS = _PosRow(move_san=None, pv=None, eval_mate=None)


def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def _parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Refresh only the tactic-tag columns on existing game_flaws rows."
    )
    parser.add_argument(
        "--db",
        choices=["dev", "benchmark", "prod"],
        required=True,
        help="DB target: dev (localhost:5432), benchmark (localhost:5433), prod (SSH tunnel).",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=None,
        dest="user_id",
        help="Refresh only this user's flaws (omit to refresh all users).",
    )
    parser.add_argument(
        "--only-tagged",
        action="store_true",
        dest="only_tagged",
        help=(
            "Only refresh flaws that already carry a tactic tag. Faster for precision "
            "tightening, but will NOT discover new detections — omit for a full refresh."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Recompute and count changed rows without writing to the database.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most this many flaw rows (useful for smoke tests).",
    )
    return parser.parse_args()


def _tactic_tuple(row: object) -> tuple[int | None, ...]:
    """Extract the 8 tactic-column values from an object in TACTIC_TAG_COLUMNS order."""
    return tuple(getattr(row, col) for col in TACTIC_TAG_COLUMNS)


def _positions_for_flaw(
    user_id: int,
    game_id: int,
    ply: int,
    pos_by_key: dict[tuple[int, int, int], _PosRow],
) -> list[_PosRow]:
    """Build the ply-indexed positions list the kernel expects for a single flaw.

    Only indices `ply` and `ply + 1` carry real data; the rest are _EMPTY_POS so the
    kernel's integer indexing and `ply + 1 < len(positions)` guard behave. Length is
    ply + 2 so positions[ply + 1] is always valid.
    """
    positions = [_EMPTY_POS] * (ply + 2)
    cur = pos_by_key.get((user_id, game_id, ply))
    if cur is not None:
        positions[ply] = cur
    nxt = pos_by_key.get((user_id, game_id, ply + 1))
    if nxt is not None:
        positions[ply + 1] = nxt
    return positions


def _recompute_tactic_tuple(
    flaw: Row[Any],
    pos_by_key: dict[tuple[int, int, int], _PosRow],
) -> tuple[int | None, ...]:
    """Recompute the 8 tactic values for one flaw using the shared kernel.

    Returns (allowed_motif, allowed_piece, allowed_confidence, allowed_depth,
             missed_motif, missed_piece, missed_confidence, missed_depth).
    """
    ply = flaw.ply
    # _PosRow is a structural stand-in for GamePosition: the kernel only reads .move_san,
    # .pv, .eval_mate plus integer indexing / len(). Annotating list[Any] satisfies the
    # kernel's nominal list[GamePosition] param without loading full ORM rows we don't need.
    positions: list[Any] = _positions_for_flaw(flaw.user_id, flaw.game_id, ply, pos_by_key)
    # fen_map only needs the flaw's own ply — the kernel reads fen_map.get(ply).
    fen_map = {ply: flaw.fen}
    allowed = _detect_tactic_for_flaw(ply, fen_map, positions, None, orientation="allowed")
    missed = _detect_tactic_for_flaw(ply, fen_map, positions, None, orientation="missed")
    return (*allowed, *missed)


async def _fetch_flaw_page(
    session: AsyncSession,
    *,
    user_id: int | None,
    only_tagged: bool,
    after: tuple[int, int, int] | None,
    limit: int,
) -> list[Row[Any]]:
    """Fetch the next PK-ordered page of flaws after the `after` keyset cursor.

    Selects only the columns we read (PK + fen + current tactic cols) as a column tuple,
    not full ORM entities — skips identity-map registration and attribute instrumentation
    on every row. The kernel needs no ORM objects, only scalars. Row attribute access
    (`row.ply`, `getattr(row, col)`) is identical to entity access for these labels.
    """
    stmt = select(
        GameFlaw.user_id,
        GameFlaw.game_id,
        GameFlaw.ply,
        GameFlaw.fen,
        *(getattr(GameFlaw, col) for col in TACTIC_TAG_COLUMNS),
    )
    if user_id is not None:
        stmt = stmt.where(GameFlaw.user_id == user_id)
    if only_tagged:
        stmt = stmt.where(
            or_(
                GameFlaw.allowed_tactic_motif.isnot(None),
                GameFlaw.missed_tactic_motif.isnot(None),
            )
        )
    if after is not None:
        # Keyset pagination on the (user_id, game_id, ply) PK — uses the PK index and is
        # resumable, unlike OFFSET which degrades on large tables (prod has millions).
        stmt = stmt.where(tuple_(GameFlaw.user_id, GameFlaw.game_id, GameFlaw.ply) > after)
    stmt = stmt.order_by(GameFlaw.user_id, GameFlaw.game_id, GameFlaw.ply).limit(limit)
    result = await session.execute(stmt)
    return list(result.all())


async def _load_positions_for_page(
    session: AsyncSession,
    flaws: list[Row[Any]],
) -> dict[tuple[int, int, int], _PosRow]:
    """Load the positions (ply and ply+1) needed by every flaw in the page, in one query."""
    # The missed pass reads positions[ply]; the allowed pass reads positions[ply+1].
    keys: set[tuple[int, int, int]] = set()
    for flaw in flaws:
        keys.add((flaw.user_id, flaw.game_id, flaw.ply))
        keys.add((flaw.user_id, flaw.game_id, flaw.ply + 1))
    stmt = select(
        GamePosition.user_id,
        GamePosition.game_id,
        GamePosition.ply,
        GamePosition.move_san,
        GamePosition.pv,
        GamePosition.eval_mate,
    ).where(tuple_(GamePosition.user_id, GamePosition.game_id, GamePosition.ply).in_(keys))
    result = await session.execute(stmt)
    return {
        (uid, gid, ply): _PosRow(move_san=move_san, pv=pv, eval_mate=eval_mate)
        for uid, gid, ply, move_san, pv, eval_mate in result.all()
    }


def _build_updates(
    flaws: list[Row[Any]],
    pos_by_key: dict[tuple[int, int, int], _PosRow],
) -> list[dict[str, object]]:
    """Recompute tactic tags for each flaw; return bulk-update dicts for CHANGED rows only."""
    updates: list[dict[str, object]] = []
    for flaw in flaws:
        new_tuple = _recompute_tactic_tuple(flaw, pos_by_key)
        if new_tuple == _tactic_tuple(flaw):
            continue  # no-op — skip to avoid needless WAL
        # Full PK + the 8 tactic values: bulk_update_tactic_tags uses ORM bulk-update-by-PK,
        # which derives the WHERE from the PK keys and SETs the remaining columns.
        update_row: dict[str, object] = {
            "user_id": flaw.user_id,
            "game_id": flaw.game_id,
            "ply": flaw.ply,
        }
        update_row.update(dict(zip(TACTIC_TAG_COLUMNS, new_tuple, strict=True)))
        updates.append(update_row)
    return updates


async def run_backfill(
    *,
    db: str,
    user_id: int | None,
    only_tagged: bool,
    dry_run: bool,
    limit: int | None,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Refresh the tactic-tag columns on existing game_flaws rows.

    Args:
        db: DB target string ("dev", "benchmark", "prod").
        user_id: Scope to this user's flaws (None = all users).
        only_tagged: Only refresh flaws that already carry a tactic tag (see module docstring).
        dry_run: If True, recompute and count changed rows but do NOT write or commit.
        limit: Maximum number of flaw rows to process (None = no limit).
        session_maker: Injectable session factory for testing. When None, a real engine
            is created from db_url_for_target(db).
    """
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    if session_maker is None:
        url = db_url_for_target(db)
        engine = create_async_engine(url, pool_pre_ping=True)
        session_maker = async_sessionmaker(engine, expire_on_commit=False)

    target_label = f"user {user_id}" if user_id is not None else "all users"
    _log(f"Tactic-tag refresh target: {target_label}")
    _log(f"Mode: {'--dry-run (no writes)' if dry_run else 'write'}")
    _log(f"Scope: {'already-tagged flaws only' if only_tagged else 'all flaws'}")
    _log(f"Batch size: {FLAWS_PER_BATCH} flaw rows per commit")
    if limit:
        _log(f"Limit: {limit} flaw rows")

    total_examined = 0
    total_changed = 0
    after: tuple[int, int, int] | None = None
    page_num = 0

    while True:
        page_size = FLAWS_PER_BATCH
        if limit is not None:
            remaining = limit - total_examined
            if remaining <= 0:
                break
            page_size = min(page_size, remaining)

        async with session_maker() as session:
            flaws = await _fetch_flaw_page(
                session,
                user_id=user_id,
                only_tagged=only_tagged,
                after=after,
                limit=page_size,
            )
            if not flaws:
                break

            try:
                pos_by_key = await _load_positions_for_page(session, flaws)
                updates = _build_updates(flaws, pos_by_key)
                if not dry_run:
                    await bulk_update_tactic_tags(session, updates)
                    await session.commit()
            except Exception as exc:
                # A page failure must not silently corrupt the run. IDs go to Sentry context,
                # never the message, to preserve issue grouping (CLAUDE.md). Re-raise: a
                # whole-page DB error is not recoverable mid-stream, unlike a per-game skip.
                last = flaws[-1]
                sentry_sdk.set_context(
                    "tactic_tag_backfill",
                    {"page": page_num, "last_game_id": last.game_id, "last_ply": last.ply},
                )
                sentry_sdk.capture_exception(exc)
                raise

        page_num += 1
        total_examined += len(flaws)
        total_changed += len(updates)
        last = flaws[-1]
        after = (last.user_id, last.game_id, last.ply)
        _log(
            f"Page {page_num}: {len(flaws)} flaws examined, "
            f"{len(updates)} {'would change' if dry_run else 'changed'} "
            f"(running total examined: {total_examined})"
        )

    _log("")
    _log("Tactic-tag refresh complete:")
    _log(f"  Flaw rows examined: {total_examined}")
    _log(f"  Flaw rows {'that would change' if dry_run else 'changed'}: {total_changed}")


if __name__ == "__main__":
    asyncio.run(run_backfill(**vars(_parse_args())))
