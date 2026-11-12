"""Repair truncated engine lines in game_positions.pv (Phase 252, SEED-261112-s4v).

Before the 2026-11-12 engine wrapper fix (release #471), about a quarter of the 1M-node
lines stored in `game_positions.pv` were cut to 1-2 plies by a final aspiration-window
bound line. This operator script re-searches those stored lines with the FIXED wrapper
(`EnginePool.evaluate_nodes_with_pv`) and writes the longer line back in place.

Subcommands:
    repair   Select short stored lines of flaw positions (S1) and empty `[]` opening
             sentinels without a usable pv (S3), re-search them and write the pv.
    feed     Just-in-time tier-4 re-walk feeder (D-11): NULLs repaired flaw lines newest first
             in small windows so the fleet's flaw-blob lane rebuilds them, judges the D-10
             8-week gate on the drain rate it measures and guards the evals (D-05/D-12).
    measure-flips  Read-only D-05 measurement: share of stored mistake/blunder classifications
             that flip under an exact re-search, next to an exact-vs-exact control.
    status   Read-only progress: work-list size, repair and feed cursors, in-flight games.

Rules the repair follows (CONTEXT D-01..D-13):
    * D-01 The re-search is PINNED to the stored best_move (python-chess `root_moves`),
      so the repaired pv starts with the stored best move and answer keys, best-move
      rows and gem badges stay valid. An existing legal best_move is never overwritten.
      Native Stockfish silently drops an illegal `searchmoves` move and searches freely,
      so legality is checked in Python before pinning and pv[0] is compared afterwards.
    * D-02 Where best_move is NULL or illegal in the position the line is searched
      freely and pv plus best_move (= first pv move) are written together.
    * D-04 Games are processed newest first (played_at DESC NULLS LAST, id DESC) from a
      work list frozen to a JSON file at the first run, resumable from a persisted cursor.
    * D-07 One operator script, no server endpoint, no worker release. Single DB
      connection (pool_size=1, max_overflow=0): prod keeps max_connections=50.
    * D-08 A local EnginePool sized by --engines (default os.cpu_count()); no worker state
      is read. Stop the worker on this box first.
    * D-13 Guest games are never selected.
    * No local undo log (owner declined): the state files under temp/line-repair/ hold only
      game ids and cursor positions, never a pv or best_move.

Gates (D-10): every run, dry or not, writes a report with each gate value next to its threshold.
`--pilot` processes the first ceil(1%) of the work list and exits 3 when a gate trips; a later
run without --pilot continues from the cursor. The work list is frozen at the FIRST run of a
(db, scope), dry runs included; delete temp/line-repair/<db>-<scope>-worklist.json to refreeze.
A failed batch, a row-count mismatch, a connection rise or a commit-latency climb stops a
writing run at once with exit 3. `--scope lane` (benchmark DB only) restricts the work list
to the armed classical + rapid full-analysis lane.

Long runs are launched by the orchestrator with `setsid nohup ... &` and watched with
Monitor, never from an executor subagent (the run dies with it).

DB target host:port mapping (CLAUDE.md):
    dev:       localhost:5432  (Docker compose flawchess-dev)
    benchmark: localhost:5433  (Docker compose flawchess-benchmark)
    prod:      localhost:15432 (via bin/prod_db_tunnel.sh)

Usage:
    uv run python scripts/repair_short_lines.py repair --db dev --dry-run --limit-games 20
    uv run python scripts/repair_short_lines.py repair --db prod --pilot --engines 8
    uv run python scripts/repair_short_lines.py repair --db prod --engines 8 --throttle-ms 50
    uv run python scripts/repair_short_lines.py repair --db benchmark --scope lane --pilot
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import math
import os
import signal
import statistics
import sys
import tempfile
import time
from collections.abc import Awaitable, Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol, TypedDict

import chess
import chess.pgn
import sentry_sdk
import sqlalchemy as sa
import sqlalchemy.exc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import db_url_for_target, settings  # noqa: E402

# Register the whole model chain (game_positions -> games -> users -> oauth_accounts) so
# no raw-SQL-only script trips NoReferencedTableError if it ever touches the ORM.
from app.models.game import Game  # noqa: E402, F401
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.models.game_position import DEDUP_MAX_PLY, GamePosition  # noqa: E402
from app.services.engine import PV_CAP_PLIES, EnginePool  # noqa: E402
from app.services.flaws_service import _run_all_moves_pass  # noqa: E402
from app.services.eval_apply import (  # noqa: E402
    CACHED_PV_MIN_PLIES,
    FlawBlobLine,
    _game_write_lock_key,
    _walk_pv_boards,
    pv_ply_count,
)

# FULL_ANALYSIS_TRANCHES is the lane definition (classical + rapid) shared with the §5 refresh.
from scripts.benchmarks.chapter5 import FULL_ANALYSIS_TRANCHES  # noqa: E402

# ─── Types ────────────────────────────────────────────────────────────────────

DbTarget = Literal["dev", "benchmark", "prod"]
Scope = Literal["all", "lane"]

# ─── Constants (CLAUDE.md: no magic numbers) ──────────────────────────────────

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
STATE_DIR: Path = REPO_ROOT / "temp" / "line-repair"
REPORT_DIR: Path = REPO_ROOT / "reports" / "line-repair"

# Wall-clock allowance for one 1M-node search on a loaded box (engines run SCHED_IDLE).
SEARCH_TIMEOUT_S: float = 30.0
# Games read, searched and written per batch (one committed write transaction each).
GAMES_PER_BATCH: int = 200

EXIT_OK: int = 0
EXIT_GATE_TRIPPED: int = 3

# D-10 stop conditions. A gate trips only when its value is STRICTLY above the threshold.
# More than ~3% of re-searched lines still 1-2 plies (mates and game endings excluded):
# the repair does not stick.
MAX_STILL_SHORT_SHARE: float = 0.03
# Measured throughput puts the prod line repair beyond this many days.
MAX_LINE_REPAIR_DAYS: float = 10.0
# Measured drain rate puts the re-walk beyond this many weeks (judged by the re-walk plans).
MAX_REWALK_WEEKS: float = 8.0
# The D-05 eval measurement: share of mistake/blunder classifications that flip (later plans).
MAX_CLASSIFICATION_FLIP_SHARE: float = 0.02
# The pilot processes the first ceil(PILOT_FRACTION x work list) games.
PILOT_FRACTION: float = 0.01
# pg_stat_activity connection count may rise this much above the baseline taken at run start.
MAX_CONNECTION_RISE: int = 10
# Rolling median commit latency may be this many times the baseline median.
MAX_COMMIT_LATENCY_RATIO: float = 3.0
# Commits in the baseline window and in the rolling window of the latency gate.
LATENCY_BASELINE_BATCHES: int = 5
# Full runs evaluate the throughput / still-short gates every this many batches.
GATE_CHECK_EVERY_BATCHES: int = 10
SECONDS_PER_DAY: float = 86_400.0
# Gate names that stop a writing run immediately (checked after every batch).
IMMEDIATE_GATES: frozenset[str] = frozenset(
    {"row_count_mismatch", "failed_batches", "connections", "commit_latency"}
)
Mode = Literal["pilot", "pilot-dryrun", "full", "full-dryrun"]

# ─── Feeder constants (D-03, D-10, D-11, D-15) ────────────────────────────────

# D-03: the longest blob a 1-2 ply pv yields. The lease walks a pv of n plies as 1 + n boards
# and leases only the even nodes, so a flaw line built from a 1-2 ply pv stores a blob of at
# most 2 * ((CACHED_PV_MIN_PLIES - 1) // 2) + 1 = 3 elements ([] when the line was sentineled).
# The feeder NULLs only lines at most this long, so a line that is longer for another reason
# (a node gap inside a long pv) is never touched and the flaw's other line is never read.
REWALK_MAX_OLD_BLOB_LEN: int = 2 * ((CACHED_PV_MIN_PLIES - 1) // 2) + 1
# D-15: only version-3 workers and the server-pool blob-only tick drain tier 4 (prod 2026-11-12:
# 2 of 6 active workers on version 3), so feed windows stay small to keep each fed game's NULL
# window short. The operator tunes them from the measured rate with --batch-games / --low-water.
FEED_BATCH_GAMES: int = 500
FEED_LOW_WATER: int = 150
# Seconds between feeder polls of the in-flight set.
FEED_POLL_S: float = 120.0
# The D-10 re-walk gate is judged only after this many hours of observed drain.
FEED_GATE_MIN_HOURS: float = 6.0
# Share of completed fed games whose eval or flaw-set fingerprint changed (D-05/D-12 guard).
FEED_MAX_EVAL_CHANGE_SHARE: float = 0.005
SECONDS_PER_HOUR: float = 3_600.0
HOURS_PER_WEEK: float = 168.0

# D-05 flip measurement: games sampled (engine-evaluated, non-guest, ordered by md5 of the id).
FLIP_SAMPLE_GAMES: int = 200

# ─── Protocols and records ────────────────────────────────────────────────────


class LineSearcher(Protocol):
    """The slice of EnginePool the repair needs; EnginePool satisfies it structurally."""

    async def evaluate_nodes_with_pv(
        self,
        board: chess.Board,
        *,
        timeout_s: float | None = None,
        root_moves: Sequence[chess.Move] | None = None,
    ) -> tuple[int | None, int | None, str | None, str | None]: ...


@dataclass(frozen=True)
class ShortLineRow:
    """One node0 game_positions row selected for repair (the pv/best_move as READ)."""

    user_id: int
    game_id: int
    ply: int
    pv: str | None
    best_move: str | None


@dataclass(frozen=True)
class SearchJob:
    row: ShortLineRow
    board: chess.Board
    pin: chess.Move | None


@dataclass(frozen=True)
class SearchOutcome:
    job: SearchJob
    eval_mate: int | None
    best_move: str | None
    pv: str | None


@dataclass(frozen=True)
class WriteItem:
    row: ShortLineRow
    new_pv: str
    new_best: str | None
    write_best: bool


@dataclass
class RepairStats:
    """Run counters. Counts only: never a user id, pv or best_move."""

    selected_a: int = 0  # short stored line at a flaw node0 (selector A)
    selected_b: int = 0  # `[]` sentinel at node0 ply <= DEDUP_MAX_PLY, not already in A (S3)
    sentinel_beyond_dedup_ply: int = 0  # `[]` sentinel without a usable pv past DEDUP_MAX_PLY
    legit_short: int = 0  # line already ends the game: never searched, never a denominator
    unreplayable: int = 0  # PGN would not replay to the node0 ply
    searched: int = 0  # rows submitted to the engine (the still-short denominator)
    written: int = 0
    would_write: int = 0  # dry-run: rows that would have been written
    unchanged: int = 0  # result not strictly longer than the stored pv
    still_short: int = 0  # result still shorter than CACHED_PV_MIN_PLIES, not a mate/game end
    mate_short: int = 0  # result short because it is a mate score or ends the game
    pin_mismatch: int = 0  # pinned search whose pv does not start with the pin: never written
    failed: int = 0  # no pv after the in-batch retry
    best_move_written_null: int = 0
    best_move_written_illegal: int = 0
    concurrently_changed: int = 0
    game_deleted: int = 0
    row_count_mismatch: int = 0  # UPDATE skipped a row for a reason we cannot explain
    failed_batches: int = 0  # a DB error aborted a batch: the run stopped there
    games_done: int = 0

    def counters(self) -> dict[str, int]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


@dataclass
class BatchInput:
    rows: list[ShortLineRow] = field(default_factory=list)
    pgns: dict[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class GateResult:
    name: str
    value: float
    threshold: float
    tripped: bool


@dataclass
class DbHealth:
    """Prod connection / commit-latency monitor (D-10). Disabled for injected test sessions."""

    enabled: bool = True
    baseline_connections: int | None = None
    peak_connections: int | None = None
    commit_latencies_s: list[float] = field(default_factory=list)

    def record_connections(self, count: int | None) -> None:
        if count is None:
            return
        if self.baseline_connections is None:
            self.baseline_connections = count
        self.peak_connections = max(self.peak_connections or count, count)

    def record_commit(self, seconds: float) -> None:
        self.commit_latencies_s.append(seconds)

    def latency_medians(self) -> tuple[float, float] | None:
        """(baseline, rolling) median commit latency, once the windows can be compared."""
        window = LATENCY_BASELINE_BATCHES
        if len(self.commit_latencies_s) <= window:
            return None
        baseline = statistics.median(self.commit_latencies_s[:window])
        return baseline, statistics.median(self.commit_latencies_s[-window:])


@dataclass(frozen=True)
class RunInfo:
    db: DbTarget
    scope: Scope
    mode: Mode
    engines: str
    started_at: datetime
    work_list_size: int
    cursor_before: int
    cursor_after: int
    elapsed_s: float


# ─── Pure helpers ─────────────────────────────────────────────────────────────


def pick_pin(board: chess.Board, stored_best_move: str | None) -> chess.Move | None:
    """D-01/D-02: the stored best move when it is legal in `board`, else None (free search).

    python-chess does not validate root moves and native Stockfish silently ignores an
    illegal `searchmoves` entry, so legality is decided here, before the search.
    """
    if not stored_best_move:
        return None
    try:
        move = chess.Move.from_uci(stored_best_move)
    except ValueError:
        return None
    return move if board.is_legal(move) else None


def replay_boards(pgn: str, plies: Collection[int]) -> dict[int, chess.Board]:
    """Boards at the wanted plies (position BEFORE the move at that ply), move stack kept.

    game_positions.ply k is the position before half-move k (ply 0 = start position), and
    ply == number of moves is the final position. Boards are copies that keep the move
    stack so repetition and the fifty-move counter stay visible to is_game_over().
    Returns {} for an unparseable PGN.
    """
    try:
        game = chess.pgn.read_game(io.StringIO(pgn))
    except ValueError, UnicodeDecodeError, AssertionError:
        return {}
    if game is None:
        return {}
    wanted = set(plies)
    boards: dict[int, chess.Board] = {}
    board = game.board()
    ply = 0
    for move in game.mainline_moves():
        if ply in wanted:
            boards[ply] = board.copy()
        board.push(move)
        ply += 1
    if ply in wanted:
        boards[ply] = board.copy()
    return boards


def _write_state(path: Path, payload: Mapping[str, int | list[int]]) -> None:
    """Atomically write a JSON state file (work list / cursor).

    The payload type admits only ints and int lists, so a pv or best_move string can never
    be persisted here: the owner declined a local undo log.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(payload, handle)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def _read_state(path: Path) -> dict[str, int | list[int]] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


# ─── SQL ──────────────────────────────────────────────────────────────────────

_WORK_LIST_SQL = (
    "SELECT g.id FROM games g JOIN users u ON u.id = g.user_id"
    " WHERE u.is_guest = false"
    " AND (g.full_pv_completed_at IS NOT NULL OR g.full_evals_completed_at IS NOT NULL)"
    "{lane_filter}"
    " ORDER BY g.played_at DESC NULLS LAST, g.id DESC"
)
# --scope lane (benchmark DB only): the armed classical + rapid full-analysis lane. EXISTS rather
# than a JOIN so a game selected under two tranches is listed once.
_LANE_FILTER_SQL = (
    " AND EXISTS (SELECT 1 FROM benchmark_selection bs WHERE bs.game_id = g.id"
    " AND bs.armed AND bs.tc_tranche = ANY(CAST(:tranches AS text[])))"
)

# Selector A (RESEARCH Pattern 2): node0 rows of every flaw line (missed = flaw ply, allowed
# = flaw ply + 1) whose stored pv is shorter than CACHED_PV_MIN_PLIES, excluding a position
# whose own eval (row k-1, post-move shift) is a mate score. DISTINCT on the row so a row
# that is node0 of two lines is searched once.
_SELECT_SHORT_SQL = sa.text(
    "WITH node0 AS ("
    " SELECT DISTINCT f.user_id, f.game_id, n.node0_ply"
    " FROM game_flaws f"
    " CROSS JOIN LATERAL (VALUES (f.ply), (f.ply + 1)) AS n(node0_ply)"
    " WHERE f.game_id = ANY(CAST(:game_ids AS bigint[]))"
    ")"
    " SELECT n.user_id, n.game_id, n.node0_ply AS ply, gp.pv, gp.best_move"
    " FROM node0 n"
    " JOIN game_positions gp"
    "   ON gp.user_id = n.user_id AND gp.game_id = n.game_id AND gp.ply = n.node0_ply"
    " LEFT JOIN game_positions prev"
    "   ON prev.user_id = n.user_id AND prev.game_id = n.game_id AND prev.ply = n.node0_ply - 1"
    " WHERE gp.pv IS NOT NULL"
    "   AND COALESCE(array_length(string_to_array(gp.pv, ' '), 1), 0) < :min_plies"
    "   AND prev.eval_mate IS NULL"
    " ORDER BY n.game_id DESC, n.node0_ply"
)

# Selector B (S3): a flaw line whose blob is the `[]` sentinel (tier 4 treats it as done)
# but whose node0 position has no usable pv. Missed line node0 = flaw ply, allowed line
# node0 = flaw ply + 1. `within_dedup` marks ply <= DEDUP_MAX_PLY: only those are repaired
# (the opening region the sentinel is written for); the rest is counted in the report.
_SELECT_SENTINEL_SQL = sa.text(
    "WITH sentinel AS ("
    " SELECT f.user_id, f.game_id, f.ply AS node0_ply FROM game_flaws f"
    "  WHERE f.game_id = ANY(CAST(:game_ids AS bigint[]))"
    "    AND f.missed_pv_lines = CAST('[]' AS jsonb)"
    " UNION"
    " SELECT f.user_id, f.game_id, f.ply + 1 FROM game_flaws f"
    "  WHERE f.game_id = ANY(CAST(:game_ids AS bigint[]))"
    "    AND f.allowed_pv_lines = CAST('[]' AS jsonb)"
    ")"
    " SELECT s.user_id, s.game_id, s.node0_ply AS ply, gp.pv, gp.best_move,"
    "        (s.node0_ply <= CAST(:dedup_max_ply AS integer)) AS within_dedup"
    " FROM sentinel s"
    " JOIN game_positions gp"
    "   ON gp.user_id = s.user_id AND gp.game_id = s.game_id AND gp.ply = s.node0_ply"
    " LEFT JOIN game_positions prev"
    "   ON prev.user_id = s.user_id AND prev.game_id = s.game_id AND prev.ply = s.node0_ply - 1"
    " WHERE COALESCE(array_length(string_to_array(gp.pv, ' '), 1), 0) < :min_plies"
    "   AND prev.eval_mate IS NULL"
    " ORDER BY s.game_id DESC, s.node0_ply"
)

_SELECT_PGN_SQL = sa.text("SELECT id, pgn FROM games WHERE id = ANY(CAST(:game_ids AS bigint[]))")

_LOCK_SQL = sa.text("SELECT pg_advisory_xact_lock(:lock_key)")

# Guarded batched UPDATE: a row is written only while its pv (and, for write_best rows, its
# best_move) still equals the value this run READ. Every bind is CAST(... AS t): asyncpg
# cannot infer the type of a NULL array element on an IS NOT DISTINCT FROM comparison.
# Array binds (unnest) keep the statement at a fixed 8 parameters, so a large batch can never
# hit asyncpg's 32767-parameter limit.
_GUARDED_UPDATE_SQL = sa.text(
    "UPDATE game_positions gp"
    " SET pv = v.new_pv,"
    "     best_move = CASE WHEN v.write_best THEN v.new_best ELSE gp.best_move END"
    " FROM unnest("
    "   CAST(:user_ids AS integer[]), CAST(:game_ids AS bigint[]), CAST(:plies AS smallint[]),"
    "   CAST(:old_pvs AS text[]), CAST(:new_pvs AS text[]),"
    "   CAST(:old_bests AS text[]), CAST(:new_bests AS text[]), CAST(:write_bests AS boolean[])"
    " ) AS v(user_id, game_id, ply, old_pv, new_pv, old_best, new_best, write_best)"
    " WHERE gp.user_id = v.user_id AND gp.game_id = v.game_id AND gp.ply = v.ply"
    "   AND gp.pv IS NOT DISTINCT FROM v.old_pv"
    "   AND (NOT v.write_best OR gp.best_move IS NOT DISTINCT FROM v.old_best)"
    " RETURNING gp.game_id, gp.ply"
)

# Re-read of the rows the guarded UPDATE skipped, to say WHY (deleted / changed / unexplained).
_REREAD_SQL = sa.text(
    "SELECT gp.game_id, gp.ply, gp.pv, gp.best_move"
    " FROM game_positions gp"
    " JOIN unnest("
    "   CAST(:user_ids AS integer[]), CAST(:game_ids AS bigint[]), CAST(:plies AS smallint[])"
    " ) AS k(user_id, game_id, ply)"
    "   ON gp.user_id = k.user_id AND gp.game_id = k.game_id AND gp.ply = k.ply"
)


# ─── Work list and cursor (D-04) ──────────────────────────────────────────────


async def build_work_list(session: AsyncSession, scope: Scope) -> list[int]:
    """Every non-guest analysed game id, newest first (D-04, D-13); lane scope narrows it."""
    lane = scope == "lane"
    sql = sa.text(_WORK_LIST_SQL.format(lane_filter=_LANE_FILTER_SQL if lane else ""))
    result = await session.execute(sql, {"tranches": list(FULL_ANALYSIS_TRANCHES)} if lane else {})
    return [int(row[0]) for row in result]


def _state_path(state_dir: Path, db: DbTarget, scope: Scope, kind: str) -> Path:
    return state_dir / f"{db}-{scope}-{kind}.json"


async def load_or_freeze_work_list(
    session_maker: async_sessionmaker[AsyncSession], db: DbTarget, scope: Scope, state_dir: Path
) -> list[int]:
    """The frozen work list: written once at the first run, reused afterwards (D-04)."""
    path = _state_path(state_dir, db, scope, "worklist")
    stored = _read_state(path)
    if stored is not None:
        game_ids = stored["game_ids"]
        assert isinstance(game_ids, list)
        return game_ids
    async with session_maker() as session:
        game_ids = await build_work_list(session, scope)
    _write_state(path, {"game_ids": game_ids})
    return game_ids


def _load_cursor(state_dir: Path, db: DbTarget, scope: Scope) -> int:
    stored = _read_state(_state_path(state_dir, db, scope, "repair-cursor"))
    index = stored["index"] if stored is not None else 0
    assert isinstance(index, int)
    return index


def _save_cursor(state_dir: Path, db: DbTarget, scope: Scope, index: int) -> None:
    _write_state(_state_path(state_dir, db, scope, "repair-cursor"), {"index": index})


# ─── Batch pipeline: read -> classify -> search -> write ─────────────────────

_CONNECTION_COUNT_SQL = sa.text("SELECT count(*) FROM pg_stat_activity")


async def _sample_connections(session: AsyncSession) -> int | None:
    """Current pg_stat_activity row count, or None when the role cannot read it (A8)."""
    try:
        async with session.begin_nested():
            return int((await session.execute(_CONNECTION_COUNT_SQL)).scalar_one())
    except sqlalchemy.exc.DBAPIError:
        return None


# Hook type for the test-only seam between the read and the write (guard tests).
AfterReadHook = Callable[[], Awaitable[None]]


async def _read_batch(
    session_maker: async_sessionmaker[AsyncSession],
    game_ids: Sequence[int],
    stats: RepairStats,
    health: DbHealth,
) -> BatchInput:
    """One short read session: candidate rows and the games' PGNs. Closed before searching."""
    batch = BatchInput()
    params = {"game_ids": list(game_ids), "min_plies": CACHED_PV_MIN_PLIES}
    async with session_maker() as session:
        if health.enabled:
            health.record_connections(await _sample_connections(session))
        short = await session.execute(_SELECT_SHORT_SQL, params)
        seen: set[tuple[int, int]] = set()
        for r in short:
            batch.rows.append(
                ShortLineRow(int(r.user_id), int(r.game_id), int(r.ply), r.pv, r.best_move)
            )
            seen.add((int(r.game_id), int(r.ply)))
        stats.selected_a += len(batch.rows)
        sentinels = await session.execute(
            _SELECT_SENTINEL_SQL, {**params, "dedup_max_ply": DEDUP_MAX_PLY}
        )
        for r in sentinels:
            if not r.within_dedup:
                stats.sentinel_beyond_dedup_ply += 1
            elif (int(r.game_id), int(r.ply)) not in seen:
                batch.rows.append(
                    ShortLineRow(int(r.user_id), int(r.game_id), int(r.ply), r.pv, r.best_move)
                )
                stats.selected_b += 1
        if batch.rows:
            wanted = sorted({row.game_id for row in batch.rows})
            pgns = await session.execute(_SELECT_PGN_SQL, {"game_ids": wanted})
            batch.pgns = {int(r.id): str(r.pgn) for r in pgns}
    return batch


def _ends_game(board: chess.Board, pv: str | None) -> bool:
    """True when the position, or the position after walking `pv`, ends the game.

    `board` keeps the game's move stack, so a claimable threefold repetition or fifty-move
    draw counts too. Only an unfinished game can have a line that is legitimately short.
    """
    if board.is_game_over(claim_draw=True):
        return True
    end_board = _walk_pv_boards(board, pv, PV_CAP_PLIES)[-1]
    return end_board.is_game_over(claim_draw=True)


def _classify_batch(batch: BatchInput, stats: RepairStats) -> list[SearchJob]:
    """Replay each game once; drop legit-short lines; attach the node0 board and D-01 pin."""
    plies_by_game: dict[int, set[int]] = {}
    for row in batch.rows:
        plies_by_game.setdefault(row.game_id, set()).add(row.ply)
    boards = {
        game_id: replay_boards(batch.pgns.get(game_id, ""), plies)
        for game_id, plies in plies_by_game.items()
    }
    jobs: list[SearchJob] = []
    for row in batch.rows:
        board = boards[row.game_id].get(row.ply)
        if board is None:
            stats.unreplayable += 1
        elif _ends_game(board, row.pv):
            # A line that ends in mate/stalemate/insufficient material/a claimable draw is
            # short for a good reason: searching it again would only re-count it as damaged.
            stats.legit_short += 1
        else:
            # D-01: pin to a legal stored best move. D-02: otherwise (NULL or illegal) None.
            jobs.append(SearchJob(row, board, pick_pin(board, row.best_move)))
    return jobs


async def _search_one(searcher: LineSearcher, job: SearchJob, timeout_s: float) -> SearchOutcome:
    _cp, mate, best, pv = await searcher.evaluate_nodes_with_pv(
        job.board,
        timeout_s=timeout_s,
        root_moves=[job.pin] if job.pin is not None else None,
    )
    return SearchOutcome(job, mate, best, pv)


async def _search_batch(
    searcher: LineSearcher, jobs: Sequence[SearchJob], timeout_s: float
) -> list[SearchOutcome]:
    """One gather over the engine pool (NO database session is open), then one retry of
    the rows that came back empty (a timeout on a loaded box is not a failed batch)."""
    outcomes = list(await asyncio.gather(*(_search_one(searcher, job, timeout_s) for job in jobs)))
    empty = [i for i, outcome in enumerate(outcomes) if not outcome.pv]
    retried = await asyncio.gather(*(_search_one(searcher, jobs[i], timeout_s) for i in empty))
    for i, outcome in zip(empty, retried):
        outcomes[i] = outcome
    return outcomes


def _count_short_result(outcome: SearchOutcome, pv: str, stats: RepairStats) -> None:
    """Feed the D-10 numerator: a result still shorter than the usable minimum is
    `mate_short` when the engine scored a mate or the line ends the game, else `still_short`."""
    if pv_ply_count(pv) >= CACHED_PV_MIN_PLIES:
        return
    if outcome.eval_mate is not None or _ends_game(outcome.job.board, pv):
        stats.mate_short += 1
    else:
        stats.still_short += 1


def _to_write_item(outcome: SearchOutcome, stats: RepairStats) -> WriteItem | None:
    """Accept an outcome only when it is a pin-respecting, strictly longer line."""
    stats.searched += 1
    job, pv = outcome.job, outcome.pv
    if not pv:
        stats.failed += 1
        return None
    if job.pin is not None and pv.split()[0] != job.pin.uci():
        stats.pin_mismatch += 1  # the engine dropped the pin and searched freely
        return None
    _count_short_result(outcome, pv, stats)
    if pv_ply_count(pv) <= pv_ply_count(job.row.pv):
        stats.unchanged += 1
        return None
    write_best = job.pin is None  # D-02: NULL or illegal stored best_move gets the pv move
    return WriteItem(job.row, pv, pv.split()[0] if write_best else None, write_best)


def _array_params(
    items: Sequence[WriteItem],
) -> dict[str, list[int] | list[str | None] | list[bool]]:
    return {
        "user_ids": [i.row.user_id for i in items],
        "game_ids": [i.row.game_id for i in items],
        "plies": [i.row.ply for i in items],
        "old_pvs": [i.row.pv for i in items],
        "new_pvs": [i.new_pv for i in items],
        "old_bests": [i.row.best_move for i in items],
        "new_bests": [i.new_best for i in items],
        "write_bests": [i.write_best for i in items],
    }


async def _classify_skipped(
    session: AsyncSession, skipped: Sequence[WriteItem], stats: RepairStats
) -> None:
    """Explain every row the guarded UPDATE skipped (never lost silently).

    Row gone -> game_deleted; pv (or best_move of a write_best row) differs from what we
    read -> concurrently_changed; anything else is the D-10 row-count mismatch.
    """
    current = await session.execute(
        _REREAD_SQL,
        {
            "user_ids": [i.row.user_id for i in skipped],
            "game_ids": [i.row.game_id for i in skipped],
            "plies": [i.row.ply for i in skipped],
        },
    )
    now = {(int(r.game_id), int(r.ply)): (r.pv, r.best_move) for r in current}
    for item in skipped:
        found = now.get((item.row.game_id, item.row.ply))
        if found is None:
            stats.game_deleted += 1
        elif found[0] != item.row.pv or (item.write_best and found[1] != item.row.best_move):
            stats.concurrently_changed += 1
        else:
            stats.row_count_mismatch += 1


def _count_best_move_writes(written: Sequence[WriteItem], stats: RepairStats) -> None:
    for item in written:
        if item.write_best:
            if item.row.best_move is None:
                stats.best_move_written_null += 1
            else:
                stats.best_move_written_illegal += 1


async def _write_batch(
    session_maker: async_sessionmaker[AsyncSession],
    items: Sequence[WriteItem],
    stats: RepairStats,
    health: DbHealth,
    before_commit_hook: AfterReadHook | None = None,
) -> None:
    """One short write session: per-game advisory locks (ascending id), guarded UPDATE."""
    if not items:
        return
    async with session_maker() as session:
        for game_id in sorted({item.row.game_id for item in items}):
            await session.execute(_LOCK_SQL, {"lock_key": _game_write_lock_key(game_id)})
        result = await session.execute(_GUARDED_UPDATE_SQL, _array_params(items))
        written_keys = {(int(r.game_id), int(r.ply)) for r in result}
        written = [i for i in items if (i.row.game_id, i.row.ply) in written_keys]
        skipped = [i for i in items if (i.row.game_id, i.row.ply) not in written_keys]
        stats.written += len(written)
        _count_best_move_writes(written, stats)
        if skipped:
            await _classify_skipped(session, skipped, stats)
        if before_commit_hook is not None:
            await before_commit_hook()
        committing = time.monotonic()
        await session.commit()
        health.record_commit(time.monotonic() - committing)


async def _repair_batch(
    session_maker: async_sessionmaker[AsyncSession],
    searcher: LineSearcher,
    game_ids: Sequence[int],
    stats: RepairStats,
    *,
    health: DbHealth,
    search_timeout_s: float,
    dry_run: bool,
    after_read_hook: AfterReadHook | None,
    before_commit_hook: AfterReadHook | None,
) -> None:
    batch = await _read_batch(session_maker, game_ids, stats, health)
    if after_read_hook is not None:
        await after_read_hook()
    jobs = _classify_batch(batch, stats)
    outcomes = await _search_batch(searcher, jobs, search_timeout_s)
    items = [item for o in outcomes if (item := _to_write_item(o, stats)) is not None]
    if dry_run:
        stats.would_write += len(items)
    else:
        await _write_batch(session_maker, items, stats, health, before_commit_hook)
    stats.games_done += len(game_ids)


# ─── D-10 gates ───────────────────────────────────────────────────────────────


def _projected_days(
    searched: int, games_done: int, remaining_games: int, elapsed_s: float
) -> float:
    """remaining games x rows searched per game / rows searched per second, in days."""
    if searched == 0 or games_done == 0 or elapsed_s <= 0:
        return 0.0
    rows_per_game = searched / games_done
    return remaining_games * rows_per_game * elapsed_s / searched / SECONDS_PER_DAY


def _health_gates(health: DbHealth | None) -> list[GateResult]:
    """Connection and commit-latency gates; absent when the data is unavailable (dry runs)."""
    gates: list[GateResult] = []
    if health is None or not health.enabled:
        return gates
    if health.baseline_connections is not None and health.peak_connections is not None:
        limit = health.baseline_connections + MAX_CONNECTION_RISE
        gates.append(
            GateResult(
                "connections", health.peak_connections, limit, health.peak_connections > limit
            )
        )
    medians = health.latency_medians()
    if medians is not None:
        baseline, rolling = medians
        ratio = rolling / baseline if baseline > 0 else 0.0
        gates.append(
            GateResult(
                "commit_latency", ratio, MAX_COMMIT_LATENCY_RATIO, ratio > MAX_COMMIT_LATENCY_RATIO
            )
        )
    return gates


def evaluate_repair_gates(
    stats: RepairStats,
    *,
    remaining_games: int,
    games_done: int,
    elapsed_s: float,
    health: DbHealth | None = None,
) -> list[GateResult]:
    """Every D-10 gate with its value next to its threshold; strictly above trips."""
    share = stats.still_short / stats.searched if stats.searched else 0.0
    days = _projected_days(stats.searched, games_done, remaining_games, elapsed_s)
    gates = [
        GateResult(
            "still_short_share", share, MAX_STILL_SHORT_SHARE, share > MAX_STILL_SHORT_SHARE
        ),
        GateResult("projected_days", days, MAX_LINE_REPAIR_DAYS, days > MAX_LINE_REPAIR_DAYS),
        GateResult("row_count_mismatch", stats.row_count_mismatch, 0, stats.row_count_mismatch > 0),
        GateResult("failed_batches", stats.failed_batches, 0, stats.failed_batches > 0),
    ]
    return gates + _health_gates(health)


def _tripped(gates: Sequence[GateResult], names: Collection[str] | None = None) -> list[GateResult]:
    return [g for g in gates if g.tripped and (names is None or g.name in names)]


def _gate_summary(gates: Sequence[GateResult]) -> str:
    verdict = "STOP" if _tripped(gates) else "PASS"
    detail = ", ".join(f"{g.name}={g.value:g}/{g.threshold:g}" for g in gates)
    return f"gates: {verdict} ({detail})"


# ─── Report ───────────────────────────────────────────────────────────────────


def _report_counters_section(stats: RepairStats) -> list[str]:
    return ["## Counters", ""] + [f"- {name}: {value}" for name, value in stats.counters().items()]


def _report_throughput_section(
    stats: RepairStats, info: RunInfo, gates: Sequence[GateResult]
) -> list[str]:
    elapsed = max(info.elapsed_s, 1e-9)
    days = next((g.value for g in gates if g.name == "projected_days"), 0.0)
    return [
        "## Throughput",
        "",
        f"- rows searched per second: {stats.searched / elapsed:.2f}",
        f"- games per second: {stats.games_done / elapsed:.2f}",
        f"- projected days for the remaining work list: {days:.2f}",
    ]


def _report_health_section(health: DbHealth | None) -> list[str]:
    lines = ["## DB health", ""]
    if health is None or not health.enabled:
        return lines + ["- connections and commit latency: not monitored in this run"]
    if health.baseline_connections is None:
        lines.append("- connections: unavailable")
    else:
        lines.append(
            f"- connections baseline {health.baseline_connections}, peak {health.peak_connections}"
        )
    medians = health.latency_medians()
    if medians is None:
        lines.append(
            f"- commit latency: {len(health.commit_latencies_s)} commits, too few to compare"
        )
    else:
        lines.append(
            f"- commit latency median baseline {medians[0]:.4f}s, rolling {medians[1]:.4f}s"
        )
    return lines


def write_repair_report(
    stats: RepairStats,
    gates: Sequence[GateResult],
    info: RunInfo,
    health: DbHealth | None,
    report_dir: Path,
) -> Path:
    """Write the run report (counts only, no user ids or names) and return its path."""
    ended = datetime.now(timezone.utc)
    stamp = ended.strftime("%Y%m%dT%H%MZ")
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"repair-{info.db}-{info.scope}-{info.mode}-{stamp}.md"
    verdict = "STOP" if _tripped(gates) else "PASS"
    lines = [
        f"# Line repair report: {info.db} / {info.scope} / {info.mode}",
        "",
        f"- target: {info.db}",
        f"- mode: {info.mode}",
        f"- engines: {info.engines}",
        f"- started: {info.started_at.isoformat(timespec='seconds')}",
        f"- ended: {ended.isoformat(timespec='seconds')}",
        f"- work list size: {info.work_list_size}",
        f"- cursor before: {info.cursor_before}, after: {info.cursor_after}",
        "",
        *_report_counters_section(stats),
        "",
        *_report_throughput_section(stats, info, gates),
        "",
        *_report_health_section(health),
        "",
        "## Gates",
        "",
        "| gate | value | threshold | verdict |",
        "|---|---|---|---|",
        *(
            f"| {g.name} | {g.value:g} | {g.threshold:g} | {'STOP' if g.tripped else 'PASS'} |"
            for g in gates
        ),
        "",
        f"## Verdict: {verdict}",
    ]
    path.write_text("\n".join(lines) + "\n")
    return path


# ─── Entry point ──────────────────────────────────────────────────────────────

# Cooperative SIGINT/SIGTERM flag (opening_cache_repair precedent): checked BETWEEN batch
# commits, never inside one, so a `kill -TERM` finishes the current batch and exits cleanly.
_stop_requested: bool = False


def _install_signal_handlers() -> None:
    global _stop_requested
    _stop_requested = False

    def _request_stop(signum: int, _frame: object) -> None:
        global _stop_requested
        print(
            f"repair_short_lines: signal {signum} received, stopping after this batch.", flush=True
        )
        _stop_requested = True

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)


@dataclass(frozen=True)
class RunOptions:
    db: DbTarget
    scope: Scope
    pilot: bool
    dry_run: bool
    limit_games: int | None
    throttle_ms: int
    search_timeout_s: float
    state_dir: Path
    after_read_hook: AfterReadHook | None = None
    before_commit_hook: AfterReadHook | None = None


def _run_end(options: RunOptions, work_size: int, index: int) -> int:
    """Exclusive end index of this run: the pilot slice and --limit-games both cap it."""
    end = work_size
    if options.pilot:
        end = min(end, math.ceil(PILOT_FRACTION * work_size))
    if options.limit_games is not None:
        end = min(end, index + options.limit_games)
    return end


def _report_failed_batch(exc: Exception, options: RunOptions, game_ids: Sequence[int]) -> None:
    """A DB error aborted the batch (rolled back by its session). Capture once, grouped."""
    sentry_sdk.set_tag("source", "line_repair")
    sentry_sdk.set_context(
        "line_repair", {"db": options.db, "first_game_id": game_ids[0], "games": len(game_ids)}
    )
    sentry_sdk.capture_exception(exc)
    print(f"repair_short_lines: batch failed ({type(exc).__name__}); stopping.", flush=True)


async def _process_work_list(
    options: RunOptions,
    session_maker: async_sessionmaker[AsyncSession],
    searcher: LineSearcher,
    work_list: Sequence[int],
    stats: RepairStats,
    health: DbHealth,
) -> int:
    """Batch loop. Returns the cursor after the last COMMITTED batch."""
    index = _load_cursor(options.state_dir, options.db, options.scope)
    end = _run_end(options, len(work_list), index)
    started = time.monotonic()
    batches = 0
    while index < end and not _stop_requested:
        game_ids = work_list[index : min(index + GAMES_PER_BATCH, end)]
        try:
            await _repair_batch(
                session_maker,
                searcher,
                game_ids,
                stats,
                health=health,
                search_timeout_s=options.search_timeout_s,
                dry_run=options.dry_run,
                after_read_hook=options.after_read_hook,
                before_commit_hook=options.before_commit_hook,
            )
        except Exception as exc:
            stats.failed_batches += 1
            _report_failed_batch(exc, options, game_ids)
            break
        index += len(game_ids)
        batches += 1
        if not options.dry_run:
            _save_cursor(options.state_dir, options.db, options.scope, index)
            if options.throttle_ms:
                await asyncio.sleep(options.throttle_ms / 1000)
        gates = evaluate_repair_gates(
            stats,
            remaining_games=len(work_list) - index,
            games_done=stats.games_done,
            elapsed_s=time.monotonic() - started,
            health=None if options.dry_run else health,
        )
        checkpoint = batches % GATE_CHECK_EVERY_BATCHES == 0
        if _tripped(gates, None if checkpoint else IMMEDIATE_GATES):
            break
    return index


def _mode(options: RunOptions) -> Mode:
    if options.pilot:
        return "pilot-dryrun" if options.dry_run else "pilot"
    return "full-dryrun" if options.dry_run else "full"


async def run_repair(
    *,
    db: DbTarget,
    scope: Scope = "all",
    pilot: bool = False,
    dry_run: bool = False,
    limit_games: int | None = None,
    engines: int | None = None,
    throttle_ms: int = 0,
    search_timeout_s: float = SEARCH_TIMEOUT_S,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
    pool: LineSearcher | None = None,
    report_dir: Path | None = None,
    state_dir: Path | None = None,
    stats_out: RepairStats | None = None,
    _after_read_hook: AfterReadHook | None = None,
    _before_commit_hook: AfterReadHook | None = None,
) -> int:
    """Re-search and write short lines for the frozen work list. Returns the exit code
    (EXIT_OK, or EXIT_GATE_TRIPPED when a D-10 gate tripped or a batch failed)."""
    if scope == "lane" and db != "benchmark":
        raise ValueError("--scope lane is only valid with --db benchmark")
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
    options = RunOptions(
        db=db,
        scope=scope,
        pilot=pilot,
        dry_run=dry_run,
        limit_games=limit_games,
        throttle_ms=throttle_ms,
        search_timeout_s=search_timeout_s,
        state_dir=state_dir if state_dir is not None else STATE_DIR,
        after_read_hook=_after_read_hook,
        before_commit_hook=_before_commit_hook,
    )
    owned_engine = None
    if session_maker is None:
        # Single connection (D-07): prod keeps max_connections=50, so no pool growth.
        owned_engine = create_async_engine(
            db_url_for_target(db), pool_size=1, max_overflow=0, pool_pre_ping=True
        )
        print(
            f"Target: {owned_engine.url.host}:{owned_engine.url.port}/"
            f"{owned_engine.url.database} ({db})",
            flush=True,
        )
        session_maker = async_sessionmaker(owned_engine, expire_on_commit=False)
    owned_pool: EnginePool | None = None
    searcher = pool
    if searcher is None:
        owned_pool = EnginePool(engines or os.cpu_count() or 1)
        await owned_pool.start()
        searcher = owned_pool
    stats = stats_out if stats_out is not None else RepairStats()
    # Connection / latency monitoring only against a real target: an injected test session
    # shares its Postgres with other workers, whose connections would trip the gate.
    health = DbHealth(enabled=owned_engine is not None and not dry_run)
    started_at = datetime.now(timezone.utc)
    started = time.monotonic()
    try:
        work_list = await load_or_freeze_work_list(session_maker, db, scope, options.state_dir)
        cursor_before = _load_cursor(options.state_dir, db, scope)
        cursor_after = await _process_work_list(
            options, session_maker, searcher, work_list, stats, health
        )
    finally:
        if owned_pool is not None:
            await owned_pool.stop()
        if owned_engine is not None:
            await owned_engine.dispose()
    elapsed = time.monotonic() - started
    gates = evaluate_repair_gates(
        stats,
        remaining_games=len(work_list) - cursor_after,
        games_done=stats.games_done,
        elapsed_s=elapsed,
        health=health,
    )
    info = RunInfo(
        db=db,
        scope=scope,
        mode=_mode(options),
        engines="injected" if pool is not None else str(engines or os.cpu_count() or 1),
        started_at=started_at,
        work_list_size=len(work_list),
        cursor_before=cursor_before,
        cursor_after=cursor_after,
        elapsed_s=elapsed,
    )
    path = write_repair_report(
        stats, gates, info, health, report_dir if report_dir is not None else REPORT_DIR
    )
    print(f"report: {path}", flush=True)
    print(_gate_summary(gates), flush=True)
    return EXIT_GATE_TRIPPED if _tripped(gates) else EXIT_OK


# ─── Feeder: just-in-time tier-4 re-walk (D-03, D-11) ─────────────────────────


@dataclass(frozen=True)
class RewalkLine:
    """One flaw line whose stored blob is shorter than its (repaired) node0 pv now allows."""

    game_id: int
    user_id: int
    ply: int  # the FLAW ply (missed node0 = ply, allowed node0 = ply + 1)
    line: FlawBlobLine


@dataclass(frozen=True)
class FeedWindowResult:
    lines_nulled_missed: int
    lines_nulled_allowed: int
    games_fed: list[int]
    lines_by_game: dict[int, int]
    # (eval fingerprint, flaw-set fingerprint) per locked game, taken BEFORE the NULL write.
    fingerprints: dict[int, tuple[str, str]] = field(default_factory=dict)


def _rewalk_predicate(blob: str, pv: str) -> str:
    """SQL predicate: this flaw line's blob is a short-pv-shaped blob shorter than its pv allows.

    A complete blob has 2 * floor(min(n, PV_CAP_PLIES) / 2) + 1 elements (RESEARCH Pattern 4).
    The old-shape bound (D-03) keeps a node-gap blob of a long pv out. A pv shorter than
    CACHED_PV_MIN_PLIES is not usable, so re-walking it could only rebuild the same blob. The
    CASE shields jsonb_array_length from a JSON-null scalar (it raises on a non-array).
    """
    length = f"(CASE WHEN jsonb_typeof({blob}) = 'array' THEN jsonb_array_length({blob}) END)"
    plies = f"array_length(string_to_array({pv}, ' '), 1)"
    return (
        f"{blob} IS NOT NULL AND {pv} IS NOT NULL"
        f" AND {plies} >= CAST(:min_plies AS integer)"
        f" AND {length} <= CAST(:max_old_len AS integer)"
        f" AND {length} < 2 * (LEAST({plies}, CAST(:cap AS integer)) / 2) + 1"
    )


# (line, blob column, node0 offset from the flaw ply). Missed node0 = flaw ply, allowed = +1.
_REWALK_LINE_COLUMNS: tuple[tuple[FlawBlobLine, str, int], ...] = (
    ("missed", "missed_pv_lines", 0),
    ("allowed", "allowed_pv_lines", 1),
)
# Only claimable (full_evals_completed_at set) non-guest games: tier 4 never serves the rest (D-13).
_REWALK_ELIGIBLE_JOINS = (
    " JOIN games g ON g.id = f.game_id AND g.full_evals_completed_at IS NOT NULL"
    " JOIN users u ON u.id = g.user_id AND NOT u.is_guest"
)


def _rewalk_params(game_ids: Sequence[int]) -> dict[str, list[int] | int]:
    return {
        "game_ids": list(game_ids),
        "min_plies": CACHED_PV_MIN_PLIES,
        "max_old_len": REWALK_MAX_OLD_BLOB_LEN,
        "cap": PV_CAP_PLIES,
    }


def _select_rewalk_sql() -> sa.TextClause:
    parts = [
        f"SELECT f.game_id, f.user_id, f.ply, '{line}' AS line FROM game_flaws f"
        f"{_REWALK_ELIGIBLE_JOINS}"
        " JOIN game_positions gp ON gp.user_id = f.user_id AND gp.game_id = f.game_id"
        f" AND gp.ply = f.ply + {offset}"
        f" WHERE f.game_id = ANY(CAST(:game_ids AS bigint[])) AND"
        f" {_rewalk_predicate(f'f.{column}', 'gp.pv')}"
        for line, column, offset in _REWALK_LINE_COLUMNS
    ]
    return sa.text(" UNION ALL ".join(parts) + " ORDER BY game_id, ply, line")


def _null_line_sql(column: str, offset: int) -> sa.TextClause:
    """UPDATE ... SET <col> = NULL (a SQL literal, never a bound None: Pitfall 6) for the
    lines matching the predicate, re-evaluated here so a repeat feed is idempotent."""
    return sa.text(
        f"UPDATE game_flaws f SET {column} = NULL"
        " FROM games g, users u, game_positions gp"
        " WHERE f.game_id = ANY(CAST(:game_ids AS bigint[]))"
        " AND g.id = f.game_id AND g.full_evals_completed_at IS NOT NULL"
        " AND u.id = g.user_id AND NOT u.is_guest"
        " AND gp.user_id = f.user_id AND gp.game_id = f.game_id"
        f" AND gp.ply = f.ply + {offset}"
        f" AND {_rewalk_predicate(f'f.{column}', 'gp.pv')}"
        " RETURNING f.game_id"
    )


_CLEAR_BLOBS_COMPLETED_SQL = sa.text(
    "UPDATE games SET blobs_completed_at = NULL WHERE id = ANY(CAST(:game_ids AS bigint[]))"
)


async def select_rewalk_lines(session: AsyncSession, game_ids: Sequence[int]) -> list[RewalkLine]:
    """Lines of `game_ids` that need a re-walk (D-03 predicate), missed and allowed."""
    if not game_ids:
        return []
    result = await session.execute(_select_rewalk_sql(), _rewalk_params(game_ids))
    lines: list[RewalkLine] = []
    for r in result:
        line: FlawBlobLine = "missed" if r.line == "missed" else "allowed"
        lines.append(RewalkLine(int(r.game_id), int(r.user_id), int(r.ply), line))
    return lines


# D-12 / D-05 guard: md5 over every ply's eval and over the flaw set (ply, severity). The
# tier-4 lane never writes either (plan 02/03), so a changed fingerprint means some lane
# re-evaluated a fed game and the feeder must stop.
_FINGERPRINT_SQL = sa.text(
    "SELECT g.id AS game_id,"
    " COALESCE((SELECT md5(string_agg("
    "   CAST(gp.ply AS text) || ':' || COALESCE(CAST(gp.eval_cp AS text), '')"
    "   || ':' || COALESCE(CAST(gp.eval_mate AS text), ''), ',' ORDER BY gp.ply))"
    "  FROM game_positions gp WHERE gp.user_id = g.user_id AND gp.game_id = g.id), '') AS eval_fp,"
    " COALESCE((SELECT md5(string_agg("
    "   CAST(f.ply AS text) || ':' || CAST(f.severity AS text), ',' ORDER BY f.ply))"
    "  FROM game_flaws f WHERE f.user_id = g.user_id AND f.game_id = g.id), '') AS flaw_fp"
    " FROM games g WHERE g.id = ANY(CAST(:game_ids AS bigint[]))"
)


async def game_fingerprints(
    session: AsyncSession, game_ids: Sequence[int]
) -> dict[int, tuple[str, str]]:
    """{game_id: (eval fingerprint, flaw-set fingerprint)} as md5 hex strings."""
    if not game_ids:
        return {}
    result = await session.execute(_FINGERPRINT_SQL, {"game_ids": list(game_ids)})
    return {int(r.game_id): (str(r.eval_fp), str(r.flaw_fp)) for r in result}


async def feed_window(
    session: AsyncSession, game_ids: Sequence[int], *, dry_run: bool
) -> FeedWindowResult:
    """NULL the repaired lines of one window of games in ONE transaction (D-11).

    Per-game advisory locks (ascending id, only games that have a candidate line) are taken
    before the UPDATEs, the same key the submit path takes, so a worker submit and the
    feeder serialise per game. Raw SQL NULL, never an ORM None (that writes `null::jsonb`,
    which tier 4 cannot see). games.blobs_completed_at is cleared only for games that got a
    line NULLed. `dry_run` runs the selection only and writes nothing.
    """
    candidates = await select_rewalk_lines(session, game_ids)
    by_game: dict[int, int] = {}
    counts: dict[FlawBlobLine, int] = {"missed": 0, "allowed": 0}
    if dry_run or not candidates:
        for cand in candidates:
            by_game[cand.game_id] = by_game.get(cand.game_id, 0) + 1
            counts[cand.line] += 1
        return FeedWindowResult(counts["missed"], counts["allowed"], sorted(by_game), by_game)
    locked = sorted({cand.game_id for cand in candidates})
    for game_id in locked:
        await session.execute(_LOCK_SQL, {"lock_key": _game_write_lock_key(game_id)})
    # Under the lock (a submit takes the same one) and before the write: the pre-feed truth.
    fingerprints = await game_fingerprints(session, locked)
    params = _rewalk_params(locked)
    for line, column, offset in _REWALK_LINE_COLUMNS:
        for r in await session.execute(_null_line_sql(column, offset), params):
            by_game[int(r.game_id)] = by_game.get(int(r.game_id), 0) + 1
            counts[line] += 1
    if by_game:
        await session.execute(_CLEAR_BLOBS_COMPLETED_SQL, {"game_ids": sorted(by_game)})
    await session.commit()
    return FeedWindowResult(
        counts["missed"], counts["allowed"], sorted(by_game), by_game, fingerprints
    )


class InFlightGame(TypedDict):
    """A fed game the fleet has not yet drained. Strings are md5 fingerprints only."""

    game_id: int
    fed_at: float  # clock() seconds when the feeder NULLed its lines
    lines: int  # lines NULLed in this game
    eval_fp: str
    flaw_fp: str


class FeedState(TypedDict):
    """Persisted feeder state. String fields are only md5 fingerprints, never pv/best_move."""

    index: int  # next work-list index to scan (every game before it was scanned)
    windows_fed: int
    lines_nulled_missed: int
    lines_nulled_allowed: int
    games_fed: int
    games_completed: int
    lines_drained: int  # lines of completed fed games
    eval_changed: int  # completed fed games whose eval or flaw-set fingerprint changed
    first_fed_at: float | None
    in_flight: list[InFlightGame]


def _new_feed_state() -> FeedState:
    return FeedState(
        index=0,
        windows_fed=0,
        lines_nulled_missed=0,
        lines_nulled_allowed=0,
        games_fed=0,
        games_completed=0,
        lines_drained=0,
        eval_changed=0,
        first_fed_at=None,
        in_flight=[],
    )


def _write_feed_state(path: Path, state: FeedState) -> None:
    """Atomically write the feed state file (same temp-file + rename as _write_state)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(state, handle)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def _read_feed_state(path: Path) -> FeedState:
    if not path.exists():
        return _new_feed_state()
    raw = json.loads(path.read_text())
    first_fed_at = raw.get("first_fed_at")
    return FeedState(
        index=int(raw.get("index", 0)),
        windows_fed=int(raw.get("windows_fed", 0)),
        lines_nulled_missed=int(raw.get("lines_nulled_missed", 0)),
        lines_nulled_allowed=int(raw.get("lines_nulled_allowed", 0)),
        games_fed=int(raw.get("games_fed", 0)),
        games_completed=int(raw.get("games_completed", 0)),
        lines_drained=int(raw.get("lines_drained", 0)),
        eval_changed=int(raw.get("eval_changed", 0)),
        first_fed_at=float(first_fed_at) if first_fed_at is not None else None,
        in_flight=[
            InFlightGame(
                game_id=int(g["game_id"]),
                fed_at=float(g["fed_at"]),
                lines=int(g["lines"]),
                eval_fp=str(g["eval_fp"]),
                flaw_fp=str(g["flaw_fp"]),
            )
            for g in raw.get("in_flight", [])
        ],
    )


# ─── Feeder gates (D-10, D-15) ────────────────────────────────────────────────


def _projected_rewalk_weeks(
    *,
    lines_fed_per_game: float,
    remaining_games: int,
    lines_drained: int,
    elapsed_h: float,
    min_hours: float,
) -> float:
    """Weeks the remaining re-walk needs at the drain rate measured so far.

    0.0 until `min_hours` of drain have been observed (the rate is not trustworthy before
    that); once observed, a zero drain is an infinite projection and trips the gate.
    """
    remaining_lines = remaining_games * lines_fed_per_game
    if remaining_lines <= 0 or elapsed_h < min_hours:
        return 0.0
    if lines_drained <= 0:
        return math.inf
    if elapsed_h <= 0:
        return 0.0
    return remaining_lines / (lines_drained / elapsed_h) / HOURS_PER_WEEK


def evaluate_feed_gates(
    *,
    lines_fed_per_game: float,
    remaining_games: int,
    lines_drained: int,
    elapsed_h: float,
    completed_games: int,
    eval_changed: int,
    min_hours: float = FEED_GATE_MIN_HOURS,
) -> list[GateResult]:
    """D-10 re-walk gates: projected weeks (judged on the drain rate measured with the fleet as
    it is, D-15) and the D-12/D-05 eval-fingerprint guard. Strictly above trips."""
    weeks = _projected_rewalk_weeks(
        lines_fed_per_game=lines_fed_per_game,
        remaining_games=remaining_games,
        lines_drained=lines_drained,
        elapsed_h=elapsed_h,
        min_hours=min_hours,
    )
    change_share = eval_changed / completed_games if completed_games else 0.0
    return [
        GateResult("projected_weeks", weeks, MAX_REWALK_WEEKS, weeks > MAX_REWALK_WEEKS),
        GateResult(
            "eval_change_share",
            change_share,
            FEED_MAX_EVAL_CHANGE_SHARE,
            change_share > FEED_MAX_EVAL_CHANGE_SHARE,
        ),
    ]


def _percentile(sorted_values: Sequence[float], pct: float) -> float:
    """Nearest-rank percentile of an ascending list (0.0 for an empty one)."""
    if not sorted_values:
        return 0.0
    rank = max(math.ceil(pct / 100 * len(sorted_values)), 1)
    return sorted_values[rank - 1]


# ─── Feeder loop (D-11) ───────────────────────────────────────────────────────

PollHook = Callable[[int], Awaitable[None]]
# SIGTERM is honoured within this many seconds even in the middle of a long poll sleep.
SLEEP_SLICE_S: float = 1.0
NULL_WINDOW_P50: float = 50.0
NULL_WINDOW_P95: float = 95.0

_FED_STATUS_SQL = sa.text(
    "SELECT id, (blobs_completed_at IS NOT NULL) AS done FROM games"
    " WHERE id = ANY(CAST(:game_ids AS bigint[]))"
)


@dataclass(frozen=True)
class FeedOptions:
    db: DbTarget
    scope: Scope
    pilot: bool
    windows: int | None
    dry_run: bool
    batch_games: int
    low_water: int
    poll_s: float
    clock: Callable[[], float]
    state_dir: Path
    after_poll_hook: PollHook | None = None
    max_polls: int | None = None


@dataclass
class FeedRunStats:
    """What THIS run observed (the persisted FeedState holds the cumulative counters)."""

    windows_fed: int = 0
    polls: int = 0
    null_window_hours: list[float] = field(default_factory=list)
    stop_reason: str = "drained"


def _feed_limit(options: FeedOptions, work_size: int) -> int:
    """Exclusive end index of the games this feeder may ever feed (pilot: first ceil(1%))."""
    if options.pilot:
        return min(work_size, math.ceil(PILOT_FRACTION * work_size))
    return work_size


async def _poll_in_flight(
    session_maker: async_sessionmaker[AsyncSession],
    options: FeedOptions,
    state: FeedState,
    run: FeedRunStats,
) -> None:
    """Move drained games (blobs_completed_at set) out of the in-flight set and re-check their
    fingerprints. A deleted game just leaves the set."""
    ids = [g["game_id"] for g in state["in_flight"]]
    if not ids:
        return
    async with session_maker() as session:
        done = {
            int(r.id): bool(r.done)
            for r in await session.execute(_FED_STATUS_SQL, {"game_ids": ids})
        }
        finished = [i for i in ids if done.get(i)]
        fingerprints = await game_fingerprints(session, finished)
    now = options.clock()
    still_pending: list[InFlightGame] = []
    for game in state["in_flight"]:
        game_id = game["game_id"]
        if game_id not in done:
            continue
        if not done[game_id]:
            still_pending.append(game)
            continue
        state["games_completed"] += 1
        state["lines_drained"] += game["lines"]
        if fingerprints.get(game_id) != (game["eval_fp"], game["flaw_fp"]):
            state["eval_changed"] += 1
        run.null_window_hours.append((now - game["fed_at"]) / SECONDS_PER_HOUR)
    state["in_flight"] = still_pending


async def _feed_next_window(
    session_maker: async_sessionmaker[AsyncSession],
    options: FeedOptions,
    state: FeedState,
    run: FeedRunStats,
    window: Sequence[int],
) -> None:
    async with session_maker() as session:
        result = await feed_window(session, window, dry_run=False)
    now = options.clock()
    if state["first_fed_at"] is None and result.games_fed:
        state["first_fed_at"] = now
    state["index"] += len(window)
    state["windows_fed"] += 1
    run.windows_fed += 1
    state["lines_nulled_missed"] += result.lines_nulled_missed
    state["lines_nulled_allowed"] += result.lines_nulled_allowed
    state["games_fed"] += len(result.games_fed)
    for game_id in result.games_fed:
        eval_fp, flaw_fp = result.fingerprints.get(game_id, ("", ""))
        state["in_flight"].append(
            InFlightGame(
                game_id=game_id,
                fed_at=now,
                lines=result.lines_by_game[game_id],
                eval_fp=eval_fp,
                flaw_fp=flaw_fp,
            )
        )


def _feed_gates(
    options: FeedOptions, state: FeedState, work_size: int, *, final: bool
) -> list[GateResult]:
    """Gate values from the persisted counters. `final` (a pilot that has drained) judges the
    projection at once instead of waiting FEED_GATE_MIN_HOURS."""
    first = state["first_fed_at"]
    elapsed_h = (options.clock() - first) / SECONDS_PER_HOUR if first is not None else 0.0
    scanned = state["index"]
    return evaluate_feed_gates(
        lines_fed_per_game=(
            (state["lines_nulled_missed"] + state["lines_nulled_allowed"]) / scanned
            if scanned
            else 0.0
        ),
        remaining_games=work_size - scanned,
        lines_drained=state["lines_drained"],
        elapsed_h=elapsed_h,
        completed_games=state["games_completed"],
        eval_changed=state["eval_changed"],
        min_hours=0.0 if final else FEED_GATE_MIN_HOURS,
    )


def _next_window(
    options: FeedOptions,
    state: FeedState,
    run: FeedRunStats,
    work_list: Sequence[int],
    fence: int,
) -> Sequence[int] | None:
    """The next window to feed, or None when nothing should be fed right now: the window cap
    is reached, enough fed games are still pending (low water), or the feeder reached the
    repair cursor (D-11: never feed a game the repair has not reached)."""
    if options.windows is not None and run.windows_fed >= options.windows:
        return None
    if len(state["in_flight"]) >= options.low_water or state["index"] >= fence:
        return None
    return work_list[state["index"] : min(state["index"] + options.batch_games, fence)]


def _is_drained(options: FeedOptions, state: FeedState, run: FeedRunStats, limit: int) -> bool:
    """Nothing in flight and nothing left to feed (list/pilot exhausted or window cap hit)."""
    if state["in_flight"]:
        return False
    capped = options.windows is not None and run.windows_fed >= options.windows
    return capped or state["index"] >= limit


async def _interruptible_sleep(seconds: float) -> None:
    """Sleep in short slices so a SIGTERM stops the feeder within SLEEP_SLICE_S."""
    deadline = time.monotonic() + seconds
    await asyncio.sleep(0)
    while not _stop_requested and (left := deadline - time.monotonic()) > 0:
        await asyncio.sleep(min(SLEEP_SLICE_S, left))


async def _feed_loop(
    session_maker: async_sessionmaker[AsyncSession],
    options: FeedOptions,
    state: FeedState,
    run: FeedRunStats,
    work_list: Sequence[int],
) -> list[GateResult]:
    """Poll, check the gates, top up the pending window, wait. Returns the final gates."""
    state_path = _state_path(options.state_dir, options.db, options.scope, "feed-state")
    limit = _feed_limit(options, len(work_list))
    gates: list[GateResult] = []
    while not _stop_requested:
        await _poll_in_flight(session_maker, options, state, run)
        _write_feed_state(state_path, state)
        gates = _feed_gates(options, state, len(work_list), final=False)
        if _tripped(gates):
            run.stop_reason = "gate tripped"
            return gates
        fence = min(limit, _load_cursor(options.state_dir, options.db, options.scope))
        window = _next_window(options, state, run, work_list, fence)
        if window is not None:
            await _feed_next_window(session_maker, options, state, run, window)
            _write_feed_state(state_path, state)
            continue
        if _is_drained(options, state, run, limit):
            return _feed_gates(options, state, len(work_list), final=options.pilot)
        run.polls += 1
        if options.max_polls is not None and run.polls >= options.max_polls:
            run.stop_reason = "max polls"
            return gates
        if options.after_poll_hook is not None:
            await options.after_poll_hook(run.polls)
        await _interruptible_sleep(options.poll_s)
    run.stop_reason = "stop requested"
    return gates


async def _feed_dry_run(
    session_maker: async_sessionmaker[AsyncSession],
    options: FeedOptions,
    state: FeedState,
    work_list: Sequence[int],
) -> FeedState:
    """Preview: walk the windows from the feed cursor up to the fence without writing, polling
    or persisting anything. Returns a throwaway state carrying the would-NULL counts."""
    preview = _new_feed_state()
    preview["index"] = state["index"]
    fence = min(
        _feed_limit(options, len(work_list)),
        _load_cursor(options.state_dir, options.db, options.scope),
    )
    windows = 0
    while preview["index"] < fence and (options.windows is None or windows < options.windows):
        window = work_list[preview["index"] : min(preview["index"] + options.batch_games, fence)]
        async with session_maker() as session:
            result = await feed_window(session, window, dry_run=True)
        preview["index"] += len(window)
        preview["lines_nulled_missed"] += result.lines_nulled_missed
        preview["lines_nulled_allowed"] += result.lines_nulled_allowed
        preview["games_fed"] += len(result.games_fed)
        preview["windows_fed"] += 1
        windows += 1
    return preview


def _report_failed_feed(exc: Exception, options: FeedOptions) -> None:
    """A DB error aborted a feed step (rolled back by its session). Capture once, grouped."""
    sentry_sdk.set_tag("source", "line_repair")
    sentry_sdk.set_context("line_repair_feed", {"db": options.db, "scope": options.scope})
    sentry_sdk.capture_exception(exc)
    print(f"repair_short_lines: feed step failed ({type(exc).__name__}); stopping.", flush=True)


def _feed_mode(options: FeedOptions) -> str:
    if options.dry_run:
        return "dryrun"
    return "pilot" if options.pilot else "full"


def write_feed_report(
    *,
    options: FeedOptions,
    state: FeedState,
    run: FeedRunStats,
    gates: Sequence[GateResult],
    work_size: int,
    report_dir: Path,
    started_at: datetime,
) -> Path:
    """Write the feed report (counts only, no user ids or game ids) and return its path."""
    ended = datetime.now(timezone.utc)
    report_dir.mkdir(parents=True, exist_ok=True)
    mode = _feed_mode(options)
    path = (
        report_dir / f"feed-{options.db}-{options.scope}-{mode}-{ended.strftime('%Y%m%dT%H%MZ')}.md"
    )
    first = state["first_fed_at"]
    elapsed_h = (options.clock() - first) / SECONDS_PER_HOUR if first is not None else 0.0
    lines_drained = state["lines_drained"]
    hours = max(elapsed_h, 1e-9)
    windows_h = sorted(run.null_window_hours)
    weeks = next((g.value for g in gates if g.name == "projected_weeks"), 0.0)
    verdict = "STOP" if _tripped(gates) else "PASS"
    lines = [
        f"# Feed report: {options.db} / {options.scope} / {mode}",
        "",
        f"- started: {started_at.isoformat(timespec='seconds')}",
        f"- ended: {ended.isoformat(timespec='seconds')}",
        f"- stopped because: {run.stop_reason}",
        f"- window size {options.batch_games} games, low water {options.low_water} games",
        f"- work list size: {work_size}, feed cursor: {state['index']}",
        f"- windows fed (this run): {run.windows_fed}, (total): {state['windows_fed']}",
        f"- lines NULLed, missed: {state['lines_nulled_missed']}, "
        f"allowed: {state['lines_nulled_allowed']}",
        f"- games fed: {state['games_fed']}, completed: {state['games_completed']}, "
        f"pending: {len(state['in_flight'])}",
        f"- eval or flaw-set changed (fingerprint mismatch): {state['eval_changed']}",
        "",
        "## Drain rate measured with the fleet as it is",
        "",
        f"- observed for {elapsed_h:.2f} h since the first fed game",
        f"- games per hour: {state['games_completed'] / hours:.2f}",
        f"- lines per hour: {lines_drained / hours:.2f}",
        f"- projected weeks for the remaining work list: {weeks:g}",
        "",
        "## User-visible NULL window per completed game (this run)",
        "",
        "Hours from the feed to the poll that saw blobs_completed_at set, so each value is "
        "rounded up to the poll interval.",
        "",
        f"- completed games measured: {len(windows_h)}",
        f"- p50: {_percentile(windows_h, NULL_WINDOW_P50):.2f} h, "
        f"p95: {_percentile(windows_h, NULL_WINDOW_P95):.2f} h, "
        f"max: {max(windows_h, default=0.0):.2f} h",
        "",
        "## Gates",
        "",
        "| gate | value | threshold | verdict |",
        "|---|---|---|---|",
        *(
            f"| {g.name} | {g.value:g} | {g.threshold:g} | {'STOP' if g.tripped else 'PASS'} |"
            for g in gates
        ),
        "",
        f"## Verdict: {verdict}",
    ]
    path.write_text("\n".join(lines) + "\n")
    return path


async def run_feed(
    *,
    db: DbTarget,
    scope: Scope = "all",
    pilot: bool = False,
    windows: int | None = None,
    dry_run: bool = False,
    batch_games: int = FEED_BATCH_GAMES,
    low_water: int = FEED_LOW_WATER,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
    report_dir: Path | None = None,
    state_dir: Path | None = None,
    poll_s: float = FEED_POLL_S,
    clock: Callable[[], float] = time.time,
    _after_poll_hook: PollHook | None = None,
    _max_polls: int | None = None,
) -> int:
    """The just-in-time tier-4 re-walk feeder (D-11). Returns EXIT_OK, or EXIT_GATE_TRIPPED
    when the re-walk gate or the eval-fingerprint guard tripped or a DB step failed.

    `clock` is wall-clock seconds (not monotonic): fed_at is persisted and compared across
    feeder restarts. `_after_poll_hook` and `_max_polls` are test seams.
    """
    if scope == "lane" and db != "benchmark":
        raise ValueError("--scope lane is only valid with --db benchmark")
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
    options = FeedOptions(
        db=db,
        scope=scope,
        pilot=pilot,
        windows=windows,
        dry_run=dry_run,
        batch_games=batch_games,
        low_water=low_water,
        poll_s=poll_s,
        clock=clock,
        state_dir=state_dir if state_dir is not None else STATE_DIR,
        after_poll_hook=_after_poll_hook,
        max_polls=_max_polls,
    )
    owned_engine = None
    if session_maker is None:
        # Single connection (D-07 / Pitfall 9): prod keeps max_connections=50.
        owned_engine = create_async_engine(
            db_url_for_target(db), pool_size=1, max_overflow=0, pool_pre_ping=True
        )
        print(
            f"Target: {owned_engine.url.host}:{owned_engine.url.port}/"
            f"{owned_engine.url.database} ({db})",
            flush=True,
        )
        session_maker = async_sessionmaker(owned_engine, expire_on_commit=False)
    started_at = datetime.now(timezone.utc)
    run = FeedRunStats()
    state_path = _state_path(options.state_dir, db, scope, "feed-state")
    try:
        work_list = await load_or_freeze_work_list(session_maker, db, scope, options.state_dir)
        state = _read_feed_state(state_path)
        try:
            if dry_run:
                state = await _feed_dry_run(session_maker, options, state, work_list)
                run.stop_reason = "dry run, nothing written"
                gates: list[GateResult] = []
            else:
                gates = await _feed_loop(session_maker, options, state, run, work_list)
        except Exception as exc:
            _report_failed_feed(exc, options)
            run.stop_reason = "failed step"
            gates = [GateResult("failed_batches", 1, 0, True)]
        if not dry_run:
            _write_feed_state(state_path, state)
    finally:
        if owned_engine is not None:
            await owned_engine.dispose()
    path = write_feed_report(
        options=options,
        state=state,
        run=run,
        gates=gates,
        work_size=len(work_list),
        report_dir=report_dir if report_dir is not None else REPORT_DIR,
        started_at=started_at,
    )
    print(f"report: {path}", flush=True)
    print(_gate_summary(gates), flush=True)
    return EXIT_GATE_TRIPPED if _tripped(gates) else EXIT_OK


# ─── measure-flips: the D-05 classification flip measurement ──────────────────

# (eval_cp, eval_mate) of one position, white's point of view (the stored convention).
EvalPair = tuple[int | None, int | None]


@dataclass(frozen=True)
class FlipCounts:
    """Mistake/blunder classification flips between two evaluations of the same games.

    `stored_mb` is the denominator: moves that are a mistake or blunder on the reference
    side. A flip is any move where either side is a mistake or blunder and the severities
    differ, split into moves lost (reference M/B, other side below mistake), gained (other
    side M/B, reference below mistake) and mistake <-> blunder changes.
    """

    stored_mb: int = 0
    flips: int = 0
    lost_mb: int = 0
    exact_only_mb: int = 0
    changed_mb_severity: int = 0

    def __add__(self, other: "FlipCounts") -> "FlipCounts":
        return FlipCounts(
            self.stored_mb + other.stored_mb,
            self.flips + other.flips,
            self.lost_mb + other.lost_mb,
            self.exact_only_mb + other.exact_only_mb,
            self.changed_mb_severity + other.changed_mb_severity,
        )

    @property
    def share(self) -> float:
        return self.flips / self.stored_mb if self.stored_mb else 0.0


_MISTAKE_OR_BLUNDER: frozenset[str | None] = frozenset({"mistake", "blunder"})


def count_classification_flips(stored: list[GamePosition], exact: list[GamePosition]) -> FlipCounts:
    """Classify every move on both row lists with the production pass and count the flips.

    `_run_all_moves_pass` is reused as is (drop math, mate ladder, interior-null skips), so
    nothing here re-implements a severity rule. A move missing from one side's map (an
    interior null eval) counts as unclassified on that side.
    """
    stored_moves = _run_all_moves_pass(stored)
    exact_moves = _run_all_moves_pass(exact)
    counts = FlipCounts()
    for ply in sorted(stored_moves.keys() | exact_moves.keys()):
        old = stored_moves[ply][1] if ply in stored_moves else None
        new = exact_moves[ply][1] if ply in exact_moves else None
        old_mb, new_mb = old in _MISTAKE_OR_BLUNDER, new in _MISTAKE_OR_BLUNDER
        flipped = (old_mb or new_mb) and old != new
        counts += FlipCounts(
            stored_mb=int(old_mb),
            flips=int(flipped),
            lost_mb=int(old_mb and not new_mb),
            exact_only_mb=int(new_mb and not old_mb),
            changed_mb_severity=int(old_mb and new_mb and old != new),
        )
    return counts


def _positions_from_evals(evals: Sequence[EvalPair]) -> list[GamePosition]:
    """Transient, session-less rows carrying only what the classification pass reads."""
    return [GamePosition(ply=i, eval_cp=cp, eval_mate=mate) for i, (cp, mate) in enumerate(evals)]


_FLIP_SAMPLE_SQL = sa.text(
    "SELECT g.id, g.pgn FROM games g JOIN users u ON u.id = g.user_id AND NOT u.is_guest"
    " WHERE g.full_evals_completed_at IS NOT NULL AND g.lichess_evals_at IS NULL"
    " ORDER BY md5(CAST(g.id AS text)) LIMIT :sample_games"
)
_FLIP_EVALS_SQL = sa.text(
    "SELECT game_id, ply, eval_cp, eval_mate FROM game_positions"
    " WHERE game_id = ANY(CAST(:game_ids AS bigint[])) ORDER BY game_id, ply"
)


@dataclass(frozen=True)
class FlipGame:
    """One sampled game: its stored evals by row ply and the boards to re-search.

    Row ply n holds the eval AFTER move n (the post-move shift), i.e. of the position with
    n + 1 moves played, so `boards[n]` is that post-move board. A terminal post-move board is
    not searched: the stored row stays.
    """

    stored: list[EvalPair]
    boards: dict[int, chess.Board]


def post_move_boards(pgn: str) -> dict[int, chess.Board]:
    """{row ply n: non-terminal board after move n}, move stacks kept. {} for a bad PGN."""
    try:
        game = chess.pgn.read_game(io.StringIO(pgn))
    except ValueError, UnicodeDecodeError, AssertionError:
        return {}
    if game is None:
        return {}
    board = game.board()
    boards: dict[int, chess.Board] = {}
    for ply, move in enumerate(game.mainline_moves()):
        board.push(move)
        if not board.is_game_over():
            boards[ply] = board.copy()
    return boards


async def _read_flip_sample(
    session_maker: async_sessionmaker[AsyncSession], sample_games: int
) -> list[FlipGame]:
    """One read session (closed before any search): the sample, its PGNs and stored evals."""
    async with session_maker() as session:
        games = {
            int(r.id): str(r.pgn)
            for r in await session.execute(_FLIP_SAMPLE_SQL, {"sample_games": sample_games})
        }
        evals: dict[int, dict[int, EvalPair]] = {game_id: {} for game_id in games}
        rows = await session.execute(_FLIP_EVALS_SQL, {"game_ids": list(games)})
        for r in rows:
            evals[int(r.game_id)][int(r.ply)] = (r.eval_cp, r.eval_mate)
    sample: list[FlipGame] = []
    for game_id, pgn in games.items():
        by_ply = evals[game_id]
        boards = post_move_boards(pgn)
        if not by_ply or not boards:
            continue
        stored = [by_ply.get(ply, (None, None)) for ply in range(max(by_ply) + 1)]
        sample.append(FlipGame(stored, boards))
    return sample


@dataclass
class ArmResult:
    """One search arm: the re-searched evals per game plus its search counters."""

    games: list[list[EvalPair]] = field(default_factory=list)
    searched: int = 0
    failed: int = 0


async def _search_arm(
    searcher: LineSearcher, sample: Sequence[FlipGame], timeout_s: float, label: str
) -> ArmResult:
    """Re-search every non-terminal post-move board of every sampled game, unpinned.

    Gather per game over the engine pool (NO database session is open). A failed search keeps
    the stored eval on that row and is counted.
    """
    arm = ArmResult()
    for done, game in enumerate(sample, start=1):
        plies = sorted(game.boards)
        results = await asyncio.gather(
            *(
                searcher.evaluate_nodes_with_pv(game.boards[ply], timeout_s=timeout_s)
                for ply in plies
            )
        )
        evals = list(game.stored)
        for ply, (cp, mate, _best, _pv) in zip(plies, results):
            arm.searched += 1
            if cp is None and mate is None:
                arm.failed += 1
            elif ply < len(evals):
                evals[ply] = (cp, mate)
        arm.games.append(evals)
        print(f"measure-flips: {label} arm {done}/{len(sample)} games", flush=True)
    return arm


def _count_arm_flips(
    reference: Sequence[Sequence[EvalPair]], other: Sequence[Sequence[EvalPair]]
) -> FlipCounts:
    total = FlipCounts()
    for ref_evals, other_evals in zip(reference, other):
        total += count_classification_flips(
            _positions_from_evals(ref_evals), _positions_from_evals(other_evals)
        )
    return total


def write_flip_report(
    *,
    db: DbTarget,
    sample_size: int,
    exact: ArmResult,
    control: ArmResult,
    stored_vs_exact: FlipCounts,
    control_counts: FlipCounts,
    gates: Sequence[GateResult],
    report_dir: Path,
) -> Path:
    """Write the flip report (counts only) and return its path."""
    ended = datetime.now(timezone.utc)
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"flips-{db}-{ended.strftime('%Y%m%dT%H%MZ')}.md"
    verdict = "STOP" if _tripped(gates) else "PASS"
    lines = [
        f"# Classification flip report: {db}",
        "",
        f"- ended: {ended.isoformat(timespec='seconds')}",
        f"- sampled games (engine-evaluated, non-guest, md5 order): {sample_size}",
        f"- plies searched, exact arm: {exact.searched}, control arm: {control.searched}",
        f"- failed searches, exact arm: {exact.failed}, control arm: {control.failed}",
        "",
        "## Stored vs exact (the D-05 number)",
        "",
        f"- stored mistakes and blunders: {stored_vs_exact.stored_mb}",
        f"- flips: {stored_vs_exact.flips} "
        f"(lost {stored_vs_exact.lost_mb}, gained {stored_vs_exact.exact_only_mb}, "
        f"mistake<->blunder {stored_vs_exact.changed_mb_severity})",
        f"- flip share: {stored_vs_exact.share:.4f}",
        "",
        "## Exact vs exact control (search noise floor)",
        "",
        f"- exact-arm mistakes and blunders: {control_counts.stored_mb}",
        f"- flips: {control_counts.flips} "
        f"(lost {control_counts.lost_mb}, gained {control_counts.exact_only_mb}, "
        f"mistake<->blunder {control_counts.changed_mb_severity})",
        f"- flip share: {control_counts.share:.4f}",
        "",
        "Stored evals came from mixed MultiPV-1 and MultiPV-2 lanes, so part of the stored vs "
        "exact difference is search noise; the control share bounds it. Terminal positions and "
        "failed searches keep their stored eval.",
        "",
        "## Gate",
        "",
        "| gate | value | threshold | verdict |",
        "|---|---|---|---|",
        *(
            f"| {g.name} | {g.value:g} | {g.threshold:g} | {'STOP' if g.tripped else 'PASS'} |"
            for g in gates
        ),
        "",
        f"## Verdict: {verdict}",
    ]
    path.write_text("\n".join(lines) + "\n")
    return path


async def run_measure_flips(
    *,
    db: DbTarget,
    sample_games: int = FLIP_SAMPLE_GAMES,
    engines: int | None = None,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
    pool: LineSearcher | None = None,
    control_pool: LineSearcher | None = None,
    report_dir: Path | None = None,
    search_timeout_s: float = SEARCH_TIMEOUT_S,
) -> int:
    """D-05: how many stored mistake/blunder classifications flip under an exact re-search.

    SELECTs and local engine searches only; nothing is written to the database. The exact arm
    and a control arm (a freshly started pool, clean hash) search the same boards, so the
    exact-vs-control share shows how much of the stored-vs-exact share is search noise alone.
    Exits EXIT_GATE_TRIPPED when the stored-vs-exact share exceeds MAX_CLASSIFICATION_FLIP_SHARE.
    """
    owned_engine = None
    if session_maker is None:
        owned_engine = create_async_engine(
            db_url_for_target(db), pool_size=1, max_overflow=0, pool_pre_ping=True
        )
        print(
            f"Target: {owned_engine.url.host}:{owned_engine.url.port}/"
            f"{owned_engine.url.database} ({db})",
            flush=True,
        )
        session_maker = async_sessionmaker(owned_engine, expire_on_commit=False)
    try:
        sample = await _read_flip_sample(session_maker, sample_games)
    finally:
        if owned_engine is not None:
            await owned_engine.dispose()
    size = engines or os.cpu_count() or 1
    exact = await _search_with(pool, size, sample, search_timeout_s, "exact")
    control = await _search_with(control_pool, size, sample, search_timeout_s, "control")
    stored_vs_exact = _count_arm_flips([g.stored for g in sample], exact.games)
    control_counts = _count_arm_flips(exact.games, control.games)
    share = stored_vs_exact.share
    gates = [
        GateResult(
            "classification_flip_share",
            share,
            MAX_CLASSIFICATION_FLIP_SHARE,
            share > MAX_CLASSIFICATION_FLIP_SHARE,
        )
    ]
    path = write_flip_report(
        db=db,
        sample_size=len(sample),
        exact=exact,
        control=control,
        stored_vs_exact=stored_vs_exact,
        control_counts=control_counts,
        gates=gates,
        report_dir=report_dir if report_dir is not None else REPORT_DIR,
    )
    print(f"report: {path}", flush=True)
    print(_gate_summary(gates), flush=True)
    return EXIT_GATE_TRIPPED if _tripped(gates) else EXIT_OK


async def _search_with(
    searcher: LineSearcher | None,
    engines: int,
    sample: Sequence[FlipGame],
    timeout_s: float,
    label: str,
) -> ArmResult:
    """Run one arm on the injected searcher, or on an EnginePool started (and stopped) here.

    The two arms never share an owned pool: the control starts on a fresh one so its hash
    holds nothing from the exact arm.
    """
    if searcher is not None:
        return await _search_arm(searcher, sample, timeout_s, label)
    owned = EnginePool(engines)
    await owned.start()
    try:
        return await _search_arm(owned, sample, timeout_s, label)
    finally:
        await owned.stop()


# ─── Status (read-only) ───────────────────────────────────────────────────────

STATUS_REPORTS_SHOWN: int = 5


async def run_status(
    *,
    db: DbTarget,
    scope: Scope = "all",
    session_maker: async_sessionmaker[AsyncSession] | None = None,
    state_dir: Path | None = None,
    report_dir: Path | None = None,
) -> int:
    """Print the repair and feed progress. SELECTs only; never freezes a work list."""
    state_root = state_dir if state_dir is not None else STATE_DIR
    work = _read_state(_state_path(state_root, db, scope, "worklist"))
    if work is None:
        print(f"work list size: not frozen yet ({db}/{scope}: run repair or feed first)")
    else:
        game_ids = work["game_ids"]
        assert isinstance(game_ids, list)
        print(f"work list size: {len(game_ids)}")
    print(f"repair cursor: {_load_cursor(state_root, db, scope)}")
    feed = _read_feed_state(_state_path(state_root, db, scope, "feed-state"))
    print(f"feed cursor: {feed['index']}")
    in_flight = [g["game_id"] for g in feed["in_flight"]]
    print(f"in flight: {len(in_flight)}")
    pending = 0
    if in_flight:
        owned_engine = None
        if session_maker is None:
            owned_engine = create_async_engine(
                db_url_for_target(db), pool_size=1, max_overflow=0, pool_pre_ping=True
            )
            session_maker = async_sessionmaker(owned_engine, expire_on_commit=False)
        try:
            async with session_maker() as session:
                rows = await session.execute(_FED_STATUS_SQL, {"game_ids": in_flight})
                pending = sum(1 for r in rows if not r.done)
        finally:
            if owned_engine is not None:
                await owned_engine.dispose()
    print(f"pending (blobs_completed_at still NULL): {pending}")
    reports = report_dir if report_dir is not None else REPORT_DIR
    newest = sorted(reports.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in newest[:STATUS_REPORTS_SHOWN]:
        print(f"report: {path}")
    return EXIT_OK


# ─── CLI ──────────────────────────────────────────────────────────────────────


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    sub = parser.add_subparsers(dest="command", required=True)
    repair = sub.add_parser("repair", help="re-search short stored lines and write the pv")
    repair.add_argument("--db", required=True, choices=["dev", "benchmark", "prod"])
    repair.add_argument("--scope", choices=["all", "lane"], default="all")
    repair.add_argument(
        "--pilot",
        action="store_true",
        help="process only the first PILOT_FRACTION of the work list, evaluate the gates, exit 3 on a trip",
    )
    repair.add_argument(
        "--dry-run", action="store_true", dest="dry_run", help="search, never write"
    )
    repair.add_argument("--limit-games", type=int, default=None, dest="limit_games")
    repair.add_argument(
        "--engines", type=int, default=None, help="engine pool size (default: CPUs)"
    )
    repair.add_argument("--throttle-ms", type=int, default=0, dest="throttle_ms")
    repair.add_argument("--report-dir", type=Path, default=None, dest="report_dir")
    feed = sub.add_parser("feed", help="NULL repaired lines newest-first for the tier-4 re-walk")
    feed.add_argument("--db", required=True, choices=["dev", "benchmark", "prod"])
    feed.add_argument("--scope", choices=["all", "lane"], default="all")
    feed.add_argument(
        "--pilot",
        action="store_true",
        help="feed only the first PILOT_FRACTION of the work list, wait until it drains, judge the gate",
    )
    feed.add_argument("--windows", type=int, default=None)
    feed.add_argument("--batch-games", type=int, default=FEED_BATCH_GAMES, dest="batch_games")
    feed.add_argument("--low-water", type=int, default=FEED_LOW_WATER, dest="low_water")
    feed.add_argument("--dry-run", action="store_true", dest="dry_run", help="select, never write")
    feed.add_argument("--report-dir", type=Path, default=None, dest="report_dir")
    flips = sub.add_parser(
        "measure-flips", help="measure the stored-vs-exact classification flip share (read-only)"
    )
    flips.add_argument("--db", required=True, choices=["dev", "benchmark", "prod"])
    flips.add_argument("--sample-games", type=int, default=FLIP_SAMPLE_GAMES, dest="sample_games")
    flips.add_argument("--engines", type=int, default=None, help="engine pool size (default: CPUs)")
    flips.add_argument("--report-dir", type=Path, default=None, dest="report_dir")
    status = sub.add_parser("status", help="print repair and feed progress (read-only)")
    status.add_argument("--db", required=True, choices=["dev", "benchmark", "prod"])
    status.add_argument("--scope", choices=["all", "lane"], default="all")
    args = parser.parse_args(argv)
    # measure-flips has no --scope (it samples the whole DB), so read it defensively.
    if getattr(args, "scope", "all") == "lane" and args.db != "benchmark":
        parser.error("--scope lane is only valid with --db benchmark")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    _install_signal_handlers()
    if args.command == "feed":
        return asyncio.run(
            run_feed(
                db=args.db,
                scope=args.scope,
                pilot=args.pilot,
                windows=args.windows,
                dry_run=args.dry_run,
                batch_games=args.batch_games,
                low_water=args.low_water,
                report_dir=args.report_dir,
            )
        )
    if args.command == "status":
        return asyncio.run(run_status(db=args.db, scope=args.scope))
    if args.command == "measure-flips":
        return asyncio.run(
            run_measure_flips(
                db=args.db,
                sample_games=args.sample_games,
                engines=args.engines,
                report_dir=args.report_dir,
            )
        )
    return asyncio.run(
        run_repair(
            db=args.db,
            scope=args.scope,
            pilot=args.pilot,
            dry_run=args.dry_run,
            limit_games=args.limit_games,
            engines=args.engines,
            throttle_ms=args.throttle_ms,
            report_dir=args.report_dir,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
