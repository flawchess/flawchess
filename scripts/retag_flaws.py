"""Re-derive game_flaws tactic tags from stored MultiPV-2 JSONB blobs (engine-free).

This script is the offline re-tagger for Phase 143 (RETAG-01, RETAG-02). It recomputes
the 8 tactic columns (allowed_tactic_motif/piece/confidence/depth + missed_tactic_*) for
already-materialized flaws by replaying the tactic-detection kernel + forcing-line gate
against the stored PV blobs — with no engine pass.

Why this replaces the old "detector refresh" tool:
    Once the forcing-line gate was wired into the live classify path (D-02, Plan 02),
    a gate-free refresh would diverge from production: tags computed without the gate
    would not match what a fresh analysis run would produce. There is no longer a coherent
    gate-free refresh tool to keep separate — the re-tagger and the detector-refresh tool
    are the same operation. Keyset paging, the spawn-worker pool, change-only batched
    UPDATE, and all inherited CLI flags are reused verbatim; the only additions are blob
    loading (two deferred JSONB columns + flaw-ply eval_cp) and the --margin flag.

Why a dedicated script instead of backfill_flaws.py:
    backfill_flaws.py rebuilds EVERY flaw row from scratch: it scans all full-eval'd
    games, loads all of each game's positions, recomputes severity/tempo/phase/eval
    smoothing, then DELETEs and re-INSERTs the rows. When only the gate margin changed,
    that is wasteful. This script instead:
      * walks game_flaws directly in PK-ordered pages (a flaw with no detector input is
        the unit of work — games without flaws are never touched),
      * loads only the positions at each flaw's ply-1, ply and ply+1 (the exact PV / mate
        inputs the detector needs), one batched query per page, not per game,
      * loads each page's distinct games' PGNs in one batched query and recomputes a real
        full-FEN map per game (castling rights, en-passant target — Phase 221 TAGFIX-09;
        game_flaws.fen itself is piece-placement-only and is never used to build a map),
      * loads the stored allowed_pv_lines / missed_pv_lines JSONB blobs and flaw-ply
        eval_cp from game_positions in the same page query,
      * recomputes the tactic tags via _classify_tactic_gated (the SAME single classify
        path the live eval drain uses — SC4 no-drift guarantee),
      * UPDATEs only the 8 tactic columns, and only for rows whose tags actually changed
        (no-op rows are skipped, minimizing WAL).

--margin tuning (RETAG-01):
    The forcing-line gate applies a win-probability gap threshold (margin) at every solver
    node in the PV blob. Changing --margin is a seconds-fast re-derivation against stored
    blobs — no engine, no blob rebuild. Phase 144 uses --dry-run margin sweeps to pick
    the final threshold before committing it to ONLY_MOVE_WIN_PROB_MARGIN.

    A larger --margin suppresses more tags; a smaller margin keeps more. Default is the
    module constant ONLY_MOVE_WIN_PROB_MARGIN (0.35 provisional; Phase 144 commits final).

Constraining the work further (the more you constrain, the fewer rows are touched):
    --user-id N     Only this user's flaws.
    --only-tagged   Only flaws that ALREADY carry a tactic tag (allowed or missed motif
                    non-null). Use this for precision-tightening changes (removing
                    false positives within existing motifs). CAVEAT: it will NOT pick up
                    NEW detections — if your change makes a detector fire where it didn't
                    before, those currently-untagged rows are skipped. Omit it for a full
                    refresh after a recall-affecting change. Note: post-gate the goal is
                    also suppression of existing tags, so a full refresh (omit
                    --only-tagged) is the default for a margin sweep.
    --limit N       Process at most N flaw rows (smoke tests).

Batching is MANDATORY given the project's OOM history (CLAUDE.md): commit every
FLAWS_PER_BATCH rows; no asyncio.gather on the same session.

DB target host:port mapping (CLAUDE.md):
    dev:       localhost:5432  (Docker compose flawchess-dev)
    benchmark: localhost:5433  (Docker compose flawchess-benchmark)
    prod:      localhost:15432 (via bin/prod_db_tunnel.sh)

Parallelism & where to run (RECOMMENDED: on the server, NOT a laptop over the tunnel):
    --workers spreads detection across worker processes; the DB stays in the parent
    (one connection), so it never multiplies the connection count. Once detection is
    parallelized the job is DB-ROUND-TRIP-BOUND, not CPU-bound (measured: ~65% CPU at 8
    workers on a local DB — a third of wall time was spent waiting on per-page round-trips).

    => Run the prod backfill ON the prod server, where the DB is local (round-trip latency
       ~0). ~6 workers is plenty; more buys little because detection is not the bottleneck.
       Running from a laptop over the SSH tunnel pays WAN latency on every serial round-trip
       and is markedly slower while the extra cores sit idle — avoid it for the full prod run.
    => Prod is memory- and write-sensitive (OOM history; live checkpoint/autovacuum load):
       run off-peak, never during a large import, and use --throttle-ms if it overlaps live
       traffic. Remote Stockfish workers cover the analysis pool, so local CPU starvation
       during the run is acceptable.
    => T-143-05 UPDATE (Phase 220 precedent, D-14): writes over the local SSH tunnel
       (bin/prod_db_tunnel.sh) from the local box are proven at multi-million-row scale —
       Phase 220 screened 2.57M rows and wrote ~11k cells over the tunnel in ~10h48m
       (220-06-SUMMARY.md). The tunnel is NOT read-only; --db prod writes are no longer
       restricted to running on the prod server. The round-trip-latency argument above for
       preferring the prod server when convenient still stands and is unchanged by this —
       prefer it for a full-scale run, but a local-box tunnel run is a proven fallback.
       Prod remains memory- and write-sensitive regardless of where the script runs: use
       --throttle-ms and run off-peak either way.

    Scale reference (prod ~3.18M flaws, dev-extrapolated at ~950 flaws/s with 8 workers):
    a full refresh is ~55 min and writes ~1M rows (~32% carry a tag; the rest recompute to
    all-NULL and are skipped, no WAL). Numbers are approximate — re-measure after deploy.

Usage:
    uv run python scripts/retag_flaws.py --db dev --dry-run
    uv run python scripts/retag_flaws.py --db dev --dry-run --margin 0.35 --user-id 28
    uv run python scripts/retag_flaws.py --db dev --user-id 28
    uv run python scripts/retag_flaws.py --db dev --only-tagged
    # Full prod re-tag (run ON the server, off-peak):
    uv run python scripts/retag_flaws.py --db prod --workers 6 --throttle-ms 50
"""

from __future__ import annotations

import argparse
import asyncio
import multiprocessing as mp
import os
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

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
from app.services.forcing_line_gate import ONLY_MOVE_WIN_PROB_MARGIN  # noqa: E402
from app.services.tactic_detector import TacticMotifInt  # noqa: E402

# _classify_tactic_gated is the single tactic classify path shared with the live eval
# drain (app/services/flaws_service.py, D-02). Importing it here — rather than calling
# _detect_tactic_for_flaw directly — guarantees the re-tagged columns match exactly what
# a fresh analysis pass would produce at the same --margin (SC4 no-drift posture).
# _recompute_fen_map is the ONE sanctioned full-FEN producer (Phase 148 D-02): it replays
# a game's PGN and returns {ply: full FEN} (side-to-move, castling rights, en-passant
# target). Importing it here — rather than re-implementing PGN replay — keeps the retag
# on the same code path eval_remote.py's live per-game retag already uses (Phase 221
# TAGFIX-09, Pitfall 2).
from app.services.flaws_service import _classify_tactic_gated, _recompute_fen_map  # noqa: E402

# No magic numbers (CLAUDE.md rule).
# Commit every N flaw rows to keep memory bounded (OOM history — see CLAUDE.md).
FLAWS_PER_BATCH = 2000


@dataclass(frozen=True)
class _PosRow:
    """Minimal position view the tactic kernel reads (move_san / pv / eval_mate / eval_cp).

    _classify_tactic_gated only touches these attributes plus integer indexing
    and len() on the positions list, so a full GamePosition load is unnecessary.
    eval_cp is the white-perspective centipawn eval at the flaw ply — used by the
    forcing-line gate's already-winning reject (ALREADY_WINNING_CP_THRESHOLD check).
    """

    move_san: str | None
    pv: str | None
    eval_mate: int | None
    eval_cp: (
        int | None
    )  # new — white-perspective cp at this ply (for gate's already-winning reject)


# Placeholder for plies we never loaded (the gaps before a flaw's ply in its per-flaw view).
# The kernel only indexes the flaw ply and flaw_ply+1; a None-valued placeholder elsewhere is
# never read for a meaningful result (pv=None → the kernel returns no tag), but must exist so
# integer indexing and the `n + 1 < len(positions)` guard behave.
_EMPTY_POS = _PosRow(move_san=None, pv=None, eval_mate=None, eval_cp=None)


def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def _parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Re-derive game_flaws tactic tags from stored MultiPV-2 JSONB blobs "
            "(engine-free, gate-gated, tunable via --margin)."
        )
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
        help="Re-tag only this user's flaws (omit to refresh all users).",
    )
    parser.add_argument(
        "--only-tagged",
        action="store_true",
        dest="only_tagged",
        help=(
            "Only re-tag flaws that already carry a tactic tag. Faster for precision "
            "tightening, but will NOT discover new detections — omit for a full refresh. "
            "Note: --only-tagged cannot discover newly-gated-in tags (D-01a)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help=(
            "Recompute and count changed rows without writing to the database. "
            "A per-motif tag-delta report is written to "
            "reports/retag/retag-YYYY-MM-DD.md on every run, dry-run or not."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Process at most this many flaw rows (useful for smoke tests).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help=(
            "Parallel detection worker processes (default: CPU count). 1 = serial, no pool. "
            "Workers do pure-CPU detection only; ALL DB access stays in the parent process "
            "(one connection), so this never multiplies the DB connection count."
        ),
    )
    parser.add_argument(
        "--throttle-ms",
        type=int,
        default=0,
        dest="throttle_ms",
        help=(
            "Sleep this many milliseconds after each page commit to cap the sustained UPDATE "
            "rate on a live DB (parallelism concentrates writes — use on a busy prod, off-peak)."
        ),
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=ONLY_MOVE_WIN_PROB_MARGIN,
        help=(
            f"Forcing-line gate win-prob margin (default: ONLY_MOVE_WIN_PROB_MARGIN="
            f"{ONLY_MOVE_WIN_PROB_MARGIN}). A larger value suppresses more tags; "
            "use --dry-run to preview before writing. Phase 144 commits the final value."
        ),
    )
    return parser.parse_args()


def _tactic_tuple(row: object) -> tuple[int | None, ...]:
    """Extract the 8 tactic-column values from an object in TACTIC_TAG_COLUMNS order."""
    return tuple(getattr(row, col) for col in TACTIC_TAG_COLUMNS)


@dataclass(frozen=True)
class _FlawWork:
    """Picklable, DB-free unit of detection work handed to a pool worker.

    Carries only what the classify kernel reads — the flaw's ply, the two positions
    it indexes (ply-1, ply and ply+1), a real full-FEN slice (fen_map), the stored PV
    blobs for both orientations, and the margin — plus the current tactic tuple so the
    worker can return the no-op signal (None) without the parent re-reading anything.
    ORM rows and full position lists never cross the process boundary: the IPC payload
    is a handful of scalars + small JSONB blobs + three short FEN strings per flaw, so
    spawn workers stay tiny and pickling stays cheap.

    margin rides on the work unit (not the module global) so spawn workers re-import
    the module with the original constant and never see a mutated global (worker-pool-safe,
    D-03 / RETAG-01).
    """

    user_id: int
    game_id: int
    ply: int
    # game_flaws.fen (NOT NULL) — piece-placement only (board_fen_only), retained ONLY for
    # report/context/logging. It is NOT used to build fen_map (Phase 221 TAGFIX-09 fix):
    # chess.Board() on a piece-placement-only string has no castling rights and no
    # en-passant target, so a castling flaw SAN is unparseable and an en-passant PV move
    # is illegal — the exact bug class the Phase-148 D-02 fix removed from the live path
    # (app.services.flaws_service._recompute_fen_map), still present here until this fix.
    fen: str
    prv: _PosRow | None  # position at ply-1 (board BEFORE the flaw move — pre_flaw_eval_cp source)
    cur: _PosRow | None  # position at ply (missed pass reads this)
    nxt: _PosRow | None  # position at ply+1 (allowed pass reads this)
    # Real full-FEN slice from _recompute_fen_map(game.pgn), sliced to only the plies the
    # kernel can read: ply-1 (when ply >= 1), ply, and ply+1. Replaces the old synthetic
    # single-entry `{ply: work.fen}` map (Phase 221 TAGFIX-09 / RESEARCH.md Pitfall 2).
    fen_map: dict[int, str]
    old_tuple: tuple[int | None, ...]
    allowed_pv_blob: list[Any] | None  # allowed_pv_lines JSONB (list[dict] | None)
    missed_pv_blob: list[Any] | None  # missed_pv_lines JSONB (list[dict] | None)
    margin: float  # forcing-line gate threshold, passed from --margin CLI flag


def _worker_recompute(work: _FlawWork) -> tuple[int | None, ...] | None:
    """Pure-CPU classify kernel (no DB) — runs inline or in a pool worker.

    Rebuilds the sparse ply-indexed positions list the kernel expects. The list now
    carries THREE plies (Phase 221 TAGFIX-09, RESEARCH.md Pitfall 2): `ply-1`, `ply` and
    `ply+1`; the rest are _EMPTY_POS so integer indexing and the `ply + 1 < len(positions)`
    guard behave (length ply + 2 keeps positions[ply + 1] valid). `ply-1` is required
    because the gate's pre-flaw eval reads it (the existing Bug-A fix, below) and because
    the missed-orientation board build reads `positions[n-1].move_san` and `fen_map[n-1]`
    (a future D-09 change; this task only threads the input through so that change has
    something real to read instead of _EMPTY_POS / a synthetic single-entry fen_map).

    Runs the allowed + missed passes through _classify_tactic_gated (the single gated
    classify path, SC4) using work.fen_map — the real full-FEN slice from
    _recompute_fen_map(game.pgn), NOT the placement-only game_flaws.fen — and returns the
    new 8-tuple, or None when it equals the stored tuple (the no-op fast path that skips a
    needless WAL-writing UPDATE).

    pre_flaw_eval_cp is derived from work.prv.eval_cp (the position BEFORE the flaw move,
    ply-1), used by the gate's already-winning reject. Bug A fix: this previously read
    work.cur.eval_cp (the eval AFTER the flaw move), which made the already-winning reject
    fire on the post-blunder eval — mirrors the flaws_service._build_flaw_record fix. None
    when ply-1 was not loaded (ply 0, pre-Phase-142 rows, or missing DB rows) — gate is
    skipped for that flaw.
    """
    ply = work.ply
    # _PosRow is a structural stand-in for GamePosition: the kernel only reads .move_san,
    # .pv, .eval_mate, .eval_cp plus integer indexing / len(). Annotating list[Any] satisfies
    # the kernel's nominal list[GamePosition] param without loading full ORM rows we don't need.
    positions: list[Any] = [_EMPTY_POS] * (ply + 2)
    if work.cur is not None:
        positions[ply] = work.cur
    if work.nxt is not None:
        positions[ply + 1] = work.nxt
    # Fill positions[ply-1] from work.prv (Phase 221 TAGFIX-09 fix): the gate's pre-flaw
    # eval read and the missed-orientation board build both need the SAME game_positions
    # row the live drain sees — a sparse list that skips ply-1 silently diverges from a
    # fresh analysis (RESEARCH.md Pitfall 2, "positions gap").
    if ply >= 1 and work.prv is not None:
        positions[ply - 1] = work.prv
    fen_map = work.fen_map
    # pre_flaw_eval_cp: white-perspective eval_cp at ply-1 (the board BEFORE the flaw move),
    # used by the gate's already-winning reject (Bug A fix — was work.cur.eval_cp at the flaw ply).
    pre_flaw_eval_cp = work.prv.eval_cp if work.prv is not None else None
    # Replace direct _detect_tactic_for_flaw calls with _classify_tactic_gated (D-02, SC4):
    # the gated wrapper runs detection then applies apply_forcing_line_filter at work.margin.
    allowed = _classify_tactic_gated(
        ply,
        fen_map,
        positions,
        "allowed",
        pv_blob=work.allowed_pv_blob,
        pre_flaw_eval_cp=pre_flaw_eval_cp,
        margin=work.margin,
    )
    missed = _classify_tactic_gated(
        ply,
        fen_map,
        positions,
        "missed",
        pv_blob=work.missed_pv_blob,
        pre_flaw_eval_cp=pre_flaw_eval_cp,
        margin=work.margin,
    )
    new_tuple = (*allowed, *missed)
    return None if new_tuple == work.old_tuple else new_tuple


def _make_works(
    flaws: list[Row[Any]],
    pos_by_key: dict[tuple[int, int, int], _PosRow],
    fen_maps_by_game: dict[int, dict[int, str]],
    margin: float,
) -> list[_FlawWork]:
    """Build picklable work units for a page, pre-extracting each flaw's positions + FENs.

    Each flaw's fen_map is a slice of its game's full fen_map (from
    _load_fen_maps_for_page), carrying only the plies the kernel can read: ply-1 (when
    ply >= 1), ply, and ply+1. Three short strings per flaw keeps the IPC payload small —
    the dataclass's own documented property (Phase 221 TAGFIX-09).
    """
    works: list[_FlawWork] = []
    for flaw in flaws:
        ply = flaw.ply
        game_fen_map = fen_maps_by_game.get(flaw.game_id, {})
        flaw_fen_map: dict[int, str] = {}
        if ply >= 1 and (prev_fen := game_fen_map.get(ply - 1)) is not None:
            flaw_fen_map[ply - 1] = prev_fen
        if (cur_fen := game_fen_map.get(ply)) is not None:
            flaw_fen_map[ply] = cur_fen
        if (nxt_fen := game_fen_map.get(ply + 1)) is not None:
            flaw_fen_map[ply + 1] = nxt_fen
        works.append(
            _FlawWork(
                user_id=flaw.user_id,
                game_id=flaw.game_id,
                ply=ply,
                fen=flaw.fen,
                prv=pos_by_key.get((flaw.user_id, flaw.game_id, ply - 1)),
                cur=pos_by_key.get((flaw.user_id, flaw.game_id, ply)),
                nxt=pos_by_key.get((flaw.user_id, flaw.game_id, ply + 1)),
                fen_map=flaw_fen_map,
                old_tuple=_tactic_tuple(flaw),
                allowed_pv_blob=flaw.allowed_pv_lines,  # JSONB list[dict] | None
                missed_pv_blob=flaw.missed_pv_lines,  # JSONB list[dict] | None
                margin=margin,
            )
        )
    return works


async def _fetch_flaw_page(
    session: AsyncSession,
    *,
    user_id: int | None,
    only_tagged: bool,
    after: tuple[int, int, int] | None,
    limit: int,
) -> list[Row[Any]]:
    """Fetch the next PK-ordered page of flaws after the `after` keyset cursor.

    Selects only the columns we read (PK + fen + current tactic cols + JSONB blobs) as a
    column tuple, not full ORM entities — skips identity-map registration and attribute
    instrumentation on every row. The kernel needs no ORM objects, only scalars. Row
    attribute access (`row.ply`, `getattr(row, col)`) is identical to entity access.

    allowed_pv_lines and missed_pv_lines are deferred on the ORM entity (deferred=True
    is the STORE-02 leak guard), but selecting them explicitly here as column attributes
    bypasses deferred loading entirely — asyncpg auto-deserializes JSONB to list[dict].
    """
    stmt = select(
        GameFlaw.user_id,
        GameFlaw.game_id,
        GameFlaw.ply,
        GameFlaw.fen,
        *(getattr(GameFlaw, col) for col in TACTIC_TAG_COLUMNS),
        GameFlaw.allowed_pv_lines,  # JSONB blob — deferred on entity but OK in explicit select
        GameFlaw.missed_pv_lines,  # JSONB blob
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
    """Load the positions (ply-1, ply, ply+1) needed by every flaw in the page, in one query.

    Also loads eval_cp at ply-1 (the board before the flaw move) for the gate's
    already-winning reject (Bug A fix — see _worker_recompute).
    """
    # The missed pass reads positions[ply]; the allowed pass reads positions[ply+1];
    # the gate's pre_flaw_eval_cp reads eval_cp at ply-1 (board before the flaw move).
    keys: set[tuple[int, int, int]] = set()
    for flaw in flaws:
        if flaw.ply >= 1:
            keys.add((flaw.user_id, flaw.game_id, flaw.ply - 1))
        keys.add((flaw.user_id, flaw.game_id, flaw.ply))
        keys.add((flaw.user_id, flaw.game_id, flaw.ply + 1))
    stmt = select(
        GamePosition.user_id,
        GamePosition.game_id,
        GamePosition.ply,
        GamePosition.move_san,
        GamePosition.pv,
        GamePosition.eval_mate,
        GamePosition.eval_cp,  # white-perspective cp at this ply (gate already-winning reject)
    ).where(tuple_(GamePosition.user_id, GamePosition.game_id, GamePosition.ply).in_(keys))
    result = await session.execute(stmt)
    return {
        (uid, gid, ply): _PosRow(move_san=move_san, pv=pv, eval_mate=eval_mate, eval_cp=eval_cp)
        for uid, gid, ply, move_san, pv, eval_mate, eval_cp in result.all()
    }


async def _load_fen_maps_for_page(
    session: AsyncSession,
    flaws: list[Row[Any]],
) -> dict[int, dict[int, str]]:
    """Load {game_id: {ply: full FEN}} for every distinct game in a page, in one query.

    Phase 221 TAGFIX-09 fix (RESEARCH.md Pitfall 2 / Open Question 1): the retag used to
    build a single-entry, placement-only fen_map from game_flaws.fen. That map cannot
    supply the kernel a board with castling rights or an en-passant target — the exact
    bug class the Phase-148 D-02 fix removed from the live path
    (app.services.flaws_service._recompute_fen_map). This function instead loads each
    page's distinct games' PGNs in ONE query and recomputes a real full-FEN map per game
    by replaying it — the ONE sanctioned full-FEN source (game_flaws.fen stays
    piece-placement-only by contract; see _recompute_fen_map's own docstring). A game
    whose PGN fails to replay yields an empty or partial map (capped to Sentry by
    _recompute_fen_map itself); a flaw with no usable FEN entry recomputes to all-NULL,
    exactly the pre-existing behaviour for a missing FEN. This makes the retag
    structurally identical to app/routers/eval_remote.py's per-game gated retag.
    """
    game_ids = {flaw.game_id for flaw in flaws}
    if not game_ids:
        return {}
    stmt = select(Game.id, Game.pgn).where(Game.id.in_(game_ids))
    result = await session.execute(stmt)
    return {game_id: _recompute_fen_map(pgn) for game_id, pgn in result.all()}


def _updates_from_results(
    flaws: list[Row[Any]],
    results: list[tuple[int | None, ...] | None],
) -> list[dict[str, object]]:
    """Turn per-flaw worker results into bulk-update dicts for CHANGED rows only.

    `results` is positionally aligned with `flaws` — both the serial list comprehension and
    ProcessPoolExecutor.map preserve input order. A None result is a no-op flaw, skipped so it
    never writes WAL.
    """
    updates: list[dict[str, object]] = []
    for flaw, new_tuple in zip(flaws, results, strict=True):
        if new_tuple is None:
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


def _bucket_motif_change(
    old_motif: int | None,
    new_motif: int | None,
    old_depth: int | None,
    new_depth: int | None,
    removed: Counter[str],
    survived: Counter[str],
    motif_shifted: Counter[str],
    depth_shifted: Counter[str],
) -> None:
    """Classify one flaw's one orientation into exactly one of four buckets.

    - new motif is None -> removed (gate-suppressed)
    - new motif differs from old -> motif_shifted
    - new motif equals old AND new depth differs from old depth -> depth_shifted
    - otherwise (motif and depth both unchanged) -> survived

    An if/elif chain (not four independent ifs) makes "exactly one bucket per row" a
    structural property, not an invariant the caller must maintain by hand — this is
    the adjacency truth TAGFIX-09's must_haves pins.

    D-11 (Phase 221, plan 02): discovered-attack's depth changes for every surviving
    row without changing motif. A motif-only removed/survived split would silently fold
    that into "survived", masking exactly the depth claim TAGFIX-09's acceptance
    criterion checks ("zero rows with an odd stored depth for motif 6") — depth_shifted
    exists so that claim has a counter to point at.
    """
    if old_motif is None:
        return
    try:
        name = TacticMotifInt(old_motif).name
    except ValueError:
        name = str(old_motif)
    if new_motif is None:
        removed[name] += 1
    elif new_motif != old_motif:
        motif_shifted[name] += 1
    elif new_depth != old_depth:
        depth_shifted[name] += 1
    else:
        survived[name] += 1


def _accumulate_motif_counts(
    flaws: list[Row[Any]],
    results: list[tuple[int | None, ...] | None],
    motif_removed_allowed: Counter[str],
    motif_survived_allowed: Counter[str],
    motif_shifted_allowed: Counter[str],
    depth_shifted_allowed: Counter[str],
    motif_removed_missed: Counter[str],
    motif_survived_missed: Counter[str],
    motif_shifted_missed: Counter[str],
    depth_shifted_missed: Counter[str],
) -> None:
    """Accumulate per-motif removed/survived/motif-shifted/depth-shifted counts.

    Decodes tactic motif integers to names via TacticMotifInt. Delegates the
    exactly-one-bucket-per-row classification to _bucket_motif_change, once per
    orientation (Phase 221 TAGFIX-09 — removed/survived/shifted, D-11's depth-shift
    bucket added on top).

    old_tuple layout (TACTIC_TAG_COLUMNS order):
        [0] allowed_tactic_motif, [1] allowed_tactic_piece, [2] allowed_tactic_confidence,
        [3] allowed_tactic_depth, [4] missed_tactic_motif, [5] missed_tactic_piece,
        [6] missed_tactic_confidence, [7] missed_tactic_depth
    """
    for flaw, new_tuple in zip(flaws, results, strict=True):
        old_tuple = _tactic_tuple(flaw)
        # Effective new tuple: if worker returned None (no-op), old tuple is unchanged.
        effective_new = new_tuple if new_tuple is not None else old_tuple

        _bucket_motif_change(
            old_tuple[0],  # allowed_tactic_motif
            effective_new[0],
            old_tuple[3],  # allowed_tactic_depth
            effective_new[3],
            motif_removed_allowed,
            motif_survived_allowed,
            motif_shifted_allowed,
            depth_shifted_allowed,
        )
        _bucket_motif_change(
            old_tuple[4],  # missed_tactic_motif
            effective_new[4],
            old_tuple[7],  # missed_tactic_depth
            effective_new[7],
            motif_removed_missed,
            motif_survived_missed,
            motif_shifted_missed,
            depth_shifted_missed,
        )


def _write_retag_report(
    margin: float,
    user_id: int | None,
    total_examined: int,
    total_changed: int,
    motif_removed_allowed: Counter[str],
    motif_survived_allowed: Counter[str],
    motif_shifted_allowed: Counter[str],
    depth_shifted_allowed: Counter[str],
    motif_removed_missed: Counter[str],
    motif_survived_missed: Counter[str],
    motif_shifted_missed: Counter[str],
    depth_shifted_missed: Counter[str],
    dry_run: bool,
    report_dir: Path | None = None,
) -> None:
    """Write a per-motif tag-delta report to reports/retag/retag-YYYY-MM-DD.md.

    Called on EVERY run now — dry-run AND a real writing run (Phase 221 TAGFIX-09;
    previously dry-run only). The report is re-runnable so a --margin sweep or /loop
    regenerates it (feeds Phase 144's A/B analysis and TAGFIX-09's acceptance queries).

    Args:
        dry_run: Whether the run that produced these counts wrote to the DB. Only
            changes the report's own **Mode:**/provenance text — the counters
            themselves are gathered identically either way.
        report_dir: Output directory for the report. Defaults to the committed
            reports/retag/ path. Tests inject a tmp dir so the suite never writes
            into the version-controlled tree. The directory is created if missing.
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    ts_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    scope = f"user-ID {user_id}" if user_id is not None else "all users"

    if report_dir is None:
        report_dir = Path(__file__).resolve().parent.parent / "reports" / "retag"
    report_path = report_dir / f"retag-{date_str}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    def _motif_table(
        removed: Counter[str],
        survived: Counter[str],
        motif_shifted: Counter[str],
        depth_shifted: Counter[str],
    ) -> str:
        """Build a per-motif pipe table from the four bucket counters.

        D-11 (Phase 221): the report needs a depth-only bucket separate from
        motif-shifted because discovered-attack's depth changes for every surviving
        row without changing motif — "zero rows with an odd stored depth for motif 6"
        is a depth claim a motif-only split cannot support.
        """
        all_motifs = sorted(set(removed) | set(survived) | set(motif_shifted) | set(depth_shifted))
        if not all_motifs:
            return "_No previously-tagged flaws in this scope._\n"
        lines = [
            "| Motif | Previously tagged | Gate suppressed | Survived | "
            "Motif shifted | Depth shifted | Suppression % |",
            "|-------|------------------|-----------------|----------|"
            "---------------|---------------|---------------|",
        ]
        for motif in all_motifs:
            r = removed[motif]
            s = survived[motif]
            ms = motif_shifted[motif]
            ds = depth_shifted[motif]
            total = r + s + ms + ds
            pct = f"{100 * r / total:.1f}%" if total > 0 else "n/a"
            lines.append(f"| {motif} | {total} | {r} | {s} | {ms} | {ds} | {pct} |")
        return "\n".join(lines) + "\n"

    allowed_table = _motif_table(
        motif_removed_allowed, motif_survived_allowed, motif_shifted_allowed, depth_shifted_allowed
    )
    missed_table = _motif_table(
        motif_removed_missed, motif_survived_missed, motif_shifted_missed, depth_shifted_missed
    )

    total_allowed_tagged = (
        sum(motif_removed_allowed.values())
        + sum(motif_survived_allowed.values())
        + sum(motif_shifted_allowed.values())
        + sum(depth_shifted_allowed.values())
    )
    total_allowed_removed = sum(motif_removed_allowed.values())
    total_missed_tagged = (
        sum(motif_removed_missed.values())
        + sum(motif_survived_missed.values())
        + sum(motif_shifted_missed.values())
        + sum(depth_shifted_missed.values())
    )
    total_missed_removed = sum(motif_removed_missed.values())

    pct_allowed = (
        f"{100 * total_allowed_removed / total_allowed_tagged:.1f}%"
        if total_allowed_tagged > 0
        else "n/a"
    )
    pct_missed = (
        f"{100 * total_missed_removed / total_missed_tagged:.1f}%"
        if total_missed_tagged > 0
        else "n/a"
    )

    mode_line = "dry-run (no writes to DB)" if dry_run else f"write ({total_changed} rows changed)"
    changed_label = "would change" if dry_run else "changed"
    invocation = f"--dry-run --margin {margin}" if dry_run else f"--margin {margin}"

    content = f"""# FlawChess Re-tagger Report

**Generated:** {ts_str}
**Margin:** {margin} (ONLY_MOVE_WIN_PROB_MARGIN default: {ONLY_MOVE_WIN_PROB_MARGIN})
**Scope:** {scope}
**Mode:** {mode_line}
**Flaws examined:** {total_examined}
**Flaw rows that {changed_label}:** {total_changed}

## Allowed-orientation tag changes

{allowed_table}
## Missed-orientation tag changes

{missed_table}
## Summary

**Total allowed tags suppressed:** {total_allowed_removed} / {total_allowed_tagged} ({pct_allowed})
**Total missed tags suppressed:** {total_missed_removed} / {total_missed_tagged} ({pct_missed})

*Generated by `scripts/retag_flaws.py {invocation}`. Re-run to regenerate.*
*Feeds Phase 144 A/B sweep and Phase 221 TAGFIX-09 acceptance.*
"""

    report_path.write_text(content)
    _log(f"Retag report written to {report_path}")


async def _process_page(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    user_id: int | None,
    only_tagged: bool,
    after: tuple[int, int, int] | None,
    page_size: int,
    margin: float,
    executor: ProcessPoolExecutor | None,
    worker_count: int,
    dry_run: bool,
    page_num: int,
    motif_counters: tuple[Counter[str], ...],
) -> tuple[list[Row[Any]], list[dict[str, object]]]:
    """Fetch, detect, and (if not dry_run) write one keyset-paged page of flaws.

    Extracted from run_backfill (Phase 221 TAGFIX-09 refactor — the added counter
    plumbing pushed the function past the nesting-depth-4 hard cap; CLAUDE.md requires
    refactoring bloated code encountered while editing a file, not adding to it). Returns
    (flaws, updates); an empty `flaws` list is the caller's "no more pages" signal.

    Raises on any page failure after recording Sentry context (WR-01) — a whole-page DB
    error is not recoverable mid-stream, so the caller's while-loop simply propagates it.

    motif_counters is the 8 Counters in the exact positional order
    _accumulate_motif_counts expects (removed/survived/motif-shifted/depth-shifted, per
    orientation) — passed as a tuple rather than 8 named parameters since every one of
    them flows straight through unchanged; this is an accumulator group, not unrelated
    state bundled to fit a signature.
    """
    async with session_maker() as session:
        # flaws is bound to [] up front so the except handler below can build Sentry
        # context even if _fetch_flaw_page itself is what raised (WR-01).
        flaws: list[Row[Any]] = []
        try:
            flaws = await _fetch_flaw_page(
                session,
                user_id=user_id,
                only_tagged=only_tagged,
                after=after,
                limit=page_size,
            )
            if not flaws:
                return [], []

            pos_by_key = await _load_positions_for_page(session, flaws)
            fen_maps_by_game = await _load_fen_maps_for_page(session, flaws)
            # Detection is pure CPU and DB-free: fan it out to the worker pool (or run
            # inline when serial). The DB stays here in the parent, one connection.
            works = _make_works(flaws, pos_by_key, fen_maps_by_game, margin)
            if executor is None:
                results = [_worker_recompute(w) for w in works]
            else:
                # chunksize amortizes per-task IPC: a worker grabs a slice, not 1 flaw.
                chunksize = max(1, len(works) // (worker_count * 4))
                results = list(executor.map(_worker_recompute, works, chunksize=chunksize))
            updates = _updates_from_results(flaws, results)
            # Accumulate motif counts for the tag-delta report (D-04). Gathered
            # unconditionally now (Phase 221 TAGFIX-09) — a writing run reports its own
            # delta too, not just a --dry-run preview.
            _accumulate_motif_counts(flaws, results, *motif_counters)
            if not dry_run:
                await bulk_update_tactic_tags(session, updates)
                await session.commit()
            return flaws, updates
        except Exception as exc:
            # A page failure (fetch, position load, or update) must not silently
            # corrupt the run. IDs go to Sentry context, never the message, to preserve
            # issue grouping (CLAUDE.md). Re-raise: a whole-page DB error is not
            # recoverable mid-stream. flaws may be empty if the fetch itself raised
            # (WR-01), so guard the last-row context.
            ctx: dict[str, int] = {"page": page_num}
            if flaws:
                last = flaws[-1]
                ctx["last_game_id"] = last.game_id
                ctx["last_ply"] = last.ply
            sentry_sdk.set_context("retag_flaws", ctx)
            sentry_sdk.capture_exception(exc)
            raise


async def run_backfill(
    *,
    db: str,
    user_id: int | None,
    only_tagged: bool,
    dry_run: bool,
    limit: int | None,
    workers: int | None = None,
    throttle_ms: int = 0,
    margin: float = ONLY_MOVE_WIN_PROB_MARGIN,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
    report_dir: Path | None = None,
) -> None:
    """Re-derive the tactic-tag columns on existing game_flaws rows via stored JSONB blobs.

    Args:
        db: DB target string ("dev", "benchmark", "prod").
        user_id: Scope to this user's flaws (None = all users).
        only_tagged: Only refresh flaws that already carry a tactic tag (see module docstring).
        dry_run: If True, recompute and count changed rows but do NOT write or commit.
        limit: Maximum number of flaw rows to process (None = no limit).
        workers: Parallel detection worker processes (None = CPU count, 1 = serial). Workers
            run pure-CPU detection only; DB access stays in the parent (one connection).
        throttle_ms: Sleep after each page commit to cap the UPDATE rate on a live DB.
        margin: Forcing-line gate win-prob margin (default: ONLY_MOVE_WIN_PROB_MARGIN).
            Flows via _FlawWork.margin into every worker — no global mutation (D-03).
        session_maker: Injectable session factory for testing. When None, a real engine
            is created from db_url_for_target(db).
        report_dir: Injectable output dir for the per-motif tag-delta report. When None,
            defaults to the committed reports/retag/ path; tests pass a tmp dir to avoid
            writing into the version-controlled tree. Written on EVERY run — dry-run AND
            a real writing run (Phase 221 TAGFIX-09; previously dry-run only).
    """
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    if session_maker is None:
        url = db_url_for_target(db)
        engine = create_async_engine(url, pool_pre_ping=True)
        session_maker = async_sessionmaker(engine, expire_on_commit=False)

    worker_count = max(1, workers if workers is not None else (os.cpu_count() or 1))

    target_label = f"user {user_id}" if user_id is not None else "all users"
    _log(f"Tactic re-tagger target: {target_label}")
    _log(f"Mode: {'--dry-run (no writes)' if dry_run else 'write'}")
    _log(f"Margin: {margin} (ONLY_MOVE_WIN_PROB_MARGIN default: {ONLY_MOVE_WIN_PROB_MARGIN})")
    _log(f"Scope: {'already-tagged flaws only' if only_tagged else 'all flaws'}")
    _log(f"Batch size: {FLAWS_PER_BATCH} flaw rows per commit")
    _log(f"Detection workers: {worker_count}{' (serial)' if worker_count == 1 else ''}")
    if throttle_ms:
        _log(f"Throttle: {throttle_ms} ms/page after commit")
    if limit:
        _log(f"Limit: {limit} flaw rows")

    total_examined = 0
    total_changed = 0
    after: tuple[int, int, int] | None = None
    page_num = 0

    # Per-motif counters for the tag-delta report (D-04; four buckets per orientation
    # since Phase 221 TAGFIX-09 — removed/survived/motif-shifted/depth-shifted).
    # Gathered on EVERY run now, not just --dry-run (previously guarded by `if dry_run:`).
    motif_removed_allowed: Counter[str] = Counter()
    motif_survived_allowed: Counter[str] = Counter()
    motif_shifted_allowed: Counter[str] = Counter()
    depth_shifted_allowed: Counter[str] = Counter()
    motif_removed_missed: Counter[str] = Counter()
    motif_survived_missed: Counter[str] = Counter()
    motif_shifted_missed: Counter[str] = Counter()
    depth_shifted_missed: Counter[str] = Counter()

    # Pool of pure-CPU detection workers. "spawn" (not fork) keeps children from inheriting
    # this process's asyncio loop and open DB connections — workers never touch the DB, so a
    # fresh interpreter is the correct, safe choice. None = serial (no pool process spawned).
    executor: ProcessPoolExecutor | None = None
    if worker_count > 1:
        executor = ProcessPoolExecutor(max_workers=worker_count, mp_context=mp.get_context("spawn"))

    try:
        while True:
            page_size = FLAWS_PER_BATCH
            if limit is not None:
                remaining = limit - total_examined
                if remaining <= 0:
                    break
                page_size = min(page_size, remaining)

            flaws, updates = await _process_page(
                session_maker,
                user_id=user_id,
                only_tagged=only_tagged,
                after=after,
                page_size=page_size,
                margin=margin,
                executor=executor,
                worker_count=worker_count,
                dry_run=dry_run,
                page_num=page_num,
                motif_counters=(
                    motif_removed_allowed,
                    motif_survived_allowed,
                    motif_shifted_allowed,
                    depth_shifted_allowed,
                    motif_removed_missed,
                    motif_survived_missed,
                    motif_shifted_missed,
                    depth_shifted_missed,
                ),
            )
            if not flaws:
                break

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
            # Parallelism concentrates writes into a shorter window; pace pages to spare a
            # live DB its checkpoint/autovacuum load. No-op when throttle_ms is 0 or dry-run.
            if throttle_ms and not dry_run:
                await asyncio.sleep(throttle_ms / 1000)
    finally:
        if executor is not None:
            executor.shutdown(wait=True)

    _log("")
    _log("Tactic re-tagger complete:")
    _log(f"  Flaw rows examined: {total_examined}")
    _log(f"  Flaw rows {'that would change' if dry_run else 'changed'}: {total_changed}")

    # Written on every run now (Phase 221 TAGFIX-09) — previously guarded by `if dry_run:`.
    _write_retag_report(
        margin,
        user_id,
        total_examined,
        total_changed,
        motif_removed_allowed,
        motif_survived_allowed,
        motif_shifted_allowed,
        depth_shifted_allowed,
        motif_removed_missed,
        motif_survived_missed,
        motif_shifted_missed,
        depth_shifted_missed,
        dry_run=dry_run,
        report_dir=report_dir,
    )


if __name__ == "__main__":
    args = _parse_args()
    db: Literal["dev", "benchmark", "prod"] = args.db
    asyncio.run(
        run_backfill(
            db=db,
            user_id=args.user_id,
            only_tagged=args.only_tagged,
            dry_run=args.dry_run,
            limit=args.limit,
            workers=args.workers,
            throttle_ms=args.throttle_ms,
            margin=args.margin,
        )
    )
