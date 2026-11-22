"""Backfill Maia per-flaw stats (game_flaws.maia_*) for games that predate go-forward scoring.

Phase 247 (D-06, D-10, D-11, D-13, D-16). Scores every flaw of every UNSTAMPED game that has
flaws, from boards replayed out of games.pgn (never from game_flaws.fen), through the same
shared scorer the live lanes use (app/services/maia_flaw_scoring.py), and stamps each game in
the same transaction as its column write (every mode but --mode opponent, which has no stamp).

Modes (Phase 250 D-08, D-18; Phase 254 D-08, D-09; the Phase 248 refutation mode was removed by D-11):
    --mode full        (default) games with maia_flaws_completed_at NULL; writes maia_played_prob,
                       the facepalm columns (the eight Phase 250 values plus the Phase 254 played
                       and best-line mate plies and the two stored material scalars), the two pre-blunder
                       keys, the best-reply probability and the five stamps.
    --mode spread      games that are base-stamped with facepalm_spread_completed_at NULL (the
                       Maia pass of the facepalm backfill, 250 D-08). One post-blunder inference
                       per user-side blunder yields the reply spread; the line facts are derived
                       with the hook's own scorer, reading the STORED maia_played_prob instead of
                       re-running the base inference. Writes exactly the facepalm fact columns
                       (the reply spread, both mate plies, the two material scalars; the score is computed
                       at query time, 254 D-01; never the two pre-blunder keys) and
                       stamps facepalm_spread_completed_at and facepalm_line_completed_at.
    --mode line --cutoff <ISO timestamp with offset>
                       the Maia-free, re-runnable line pass (250 D-18). Every spread-stamped game
                       whose facepalm_line_completed_at is NULL or older than the cutoff has the
                       line facts of its blunders of BOTH sides (user and opponent) recomputed from
                       the stored lines (the played line at ply + 1 and the best line at the flaw
                       ply): the two material scalars, line_mate_ply and
                       best_line_mate_ply, INCLUDING rows that already hold values and blunders that
                       had no line before. A cutoff at or after the deploy of the opponent line
                       facts (SEED-261114-iuv Part A step 4) re-selects every game, so opponent
                       rows get their line facts. Spread and pre modes stay user-side only. It never
                       starts Maia, never computes the spread and never exits 3 for a missing
                       Maia. --cutoff is required here and rejected for every other mode.

    --mode pre         games that are base-stamped with facepalm_pre_completed_at NULL (Phase 254 D-08,
                       the R1 pre-blunder inputs). ONE Maia inference at the pre-blunder position per
                       user-side blunder fills maia_best_prob and maia_pre_spread, exactly as the hook
                       derives them. Writes only those two columns and stamps only
                       facepalm_pre_completed_at: never maia_played_prob, the reply spread or the line
                       facts. Resumable (the stamp is the checkpoint, a second
                       run selects 0 games) and sharded by hash residue like the spread pass.

    --mode reply       (Phase 259 D-07, D-10) games that are base-stamped with facepalm_reply_completed_at
                       NULL. ONE post-blunder Maia inference per blunder of EITHER side that carries
                       a stored maia_played_prob fills maia_best_reply_prob, the probability of the
                       first token of the stored refutation line, exactly as the hook derives it
                       (no inference when the stored line has no first token). Writes only that
                       column and stamps only facepalm_reply_completed_at: never maia_played_prob,
                       the spread, the arrays, the scalars, the pre inputs or another stamp.
                       Resumable (the stamp is the checkpoint, a second run selects 0 games) and
                       sharded by hash residue. Needs Maia (exit 3 without it).

    --mode opponent    (SEED-261114-iuv Part A) selection BY ROW: games with an opponent blunder whose
                       maia_played_prob is set and maia_reply_spread is NULL (no base stamp
                       needed). ONE pre-blunder inference (maia_best_prob, maia_pre_spread) plus ONE
                       post-blunder inference (maia_reply_spread) per such blunder, at the mover's
                       (the opponent's) pinned Elo. Writes only those three columns: never
                       maia_played_prob, never the line facts (full mode and the line pass write
                       those for opponent blunders), never a user-side row, never a stamp. No stamp column exists for it, so the row predicate is the
                       checkpoint and a rerun resumes. Run it only against a DB whose lanes already
                       run the updated full-mode hook: a full re-score by the old hook would write
                       NULL Maia values on opponent rows and undo the backfill.
                       Residue: stalemating blunders (counted as no_legal_reply) and rows whose board
                       cannot be rebuilt (fen_mismatch, ply_beyond_mainline, ...) keep a NULL spread
                       and are selected again by every later run. One run never loops on them: each
                       shard selects one snapshot and iterates it once. `--status --mode opponent`
                       shows the residue as opponent_blunders_pending. Guests are handled like the
                       other modes (no filter). Needs Maia (exit 3 without it).

Two-pass design for the facepalm columns (250 D-08, D-18): the spread pass needs Maia and is run
once (about 2.3M user blunders on prod); the line pass needs only the DB, so it can be re-run
whenever the stored lines change (e.g. after the Phase 252 pv repair). The line pass writes the two
material scalars and both mate plies (played and best line) (254 D-09, 259 D-05), and never a Maia
value; the spread pass never writes the two pre-blunder keys. For the line pass the
CUTOFF is the checkpoint: re-run with the SAME cutoff to resume a crashed or stopped run (games
stamped at or after it are skipped); use a NEW (later) cutoff for a new full recompute.

The stamp of the chosen mode IS the checkpoint (opponent mode: its row predicate): a crash, a SIGTERM, or a D-09
unstamp (a reclassification that clears stamps) is caught by simply re-running. A second run
over the same scope selects zero games and writes nothing. Zero-flaw games are never selected
(the go-forward scorer stamps them), so there is no scan of all games.

Parallelism: the games are split into --workers shards by HASH RESIDUE of the game id, never by
rank windows (the table grows during a run, so rank-window shards silently double-scan and skip,
see scripts/engine_disagreement_study/seed153_scan_sample.py). Each shard is its own spawned
process with its own single-threaded ORT session (one thread measured faster per position than
the ORT default; throughput scales by processes) and a one-connection pool.

DB target host:port mapping (CLAUDE.md):
    dev:       localhost:5432  (Docker compose flawchess-dev)
    benchmark: localhost:5433  (Docker compose flawchess-benchmark)
    prod:      localhost:15432 (via bin/prod_db_tunnel.sh)

The URL for each target comes from the DATABASE_URL_{DEV,BENCHMARK,PROD} env vars (.env),
resolved via app.core.config.db_url_for_target. It is never printed.

Usage:
    uv run python scripts/backfill_maia_flaws.py --db dev --workers 1 --user-id 28 --limit 200
    uv run python scripts/backfill_maia_flaws.py --db benchmark --workers 1 --limit 50 --dry-run
    PYTHONUNBUFFERED=1 uv run python scripts/backfill_maia_flaws.py --db prod --workers 9
    uv run python scripts/backfill_maia_flaws.py --db prod --status
    uv run python scripts/backfill_maia_flaws.py --db dev --shard 2 --num-shards 9
    PYTHONUNBUFFERED=1 uv run --group maia-inference python scripts/backfill_maia_flaws.py --db prod --mode spread --workers 6 --throttle-ms 50
    uv run python scripts/backfill_maia_flaws.py --db prod --status --mode spread
    PYTHONUNBUFFERED=1 uv run python scripts/backfill_maia_flaws.py --db prod --mode line --cutoff <deploy time UTC> --workers 4 --throttle-ms 50
    uv run python scripts/backfill_maia_flaws.py --db prod --status --mode line --cutoff <same cutoff>
    (line pass over opponent blunders too: the cutoff must be at or after the deploy of this change;
     --status --mode line then also prints opponent_blunders_total / _with_material_inputs / _with_score)
    PYTHONUNBUFFERED=1 uv run --group maia-inference python scripts/backfill_maia_flaws.py --db prod --mode pre --workers 8 --throttle-ms 50
    uv run python scripts/backfill_maia_flaws.py --db prod --status --mode pre
    (pre mode, 254 D-20: 8 shards, one connection each; the stamp is the checkpoint, re-run to resume)
    PYTHONUNBUFFERED=1 uv run --group maia-inference python scripts/backfill_maia_flaws.py --db prod --mode opponent --workers 8 --throttle-ms 50
    uv run python scripts/backfill_maia_flaws.py --db prod --status --mode opponent
    (opponent mode: row predicate is the checkpoint, re-run to resume; run after the hook deploy)
    PYTHONUNBUFFERED=1 uv run --group maia-inference python scripts/backfill_maia_flaws.py --db prod --mode reply --workers 12 --throttle-ms 50
    uv run python scripts/backfill_maia_flaws.py --db prod --status --mode reply
    (reply mode, 259 D-07: 12 workers is the ceiling, one connection each: prod max_connections is 50,
     the app pool takes up to 20 and operator connections must stay under about 25. No other
     operator run may overlap. The stamp is the checkpoint, re-run to resume after the 02:15 UTC reboot)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import multiprocessing as mp
import signal
import sys
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import sentry_sdk
from sqlalchemy import ColumnElement, Select, func, literal_column, not_, select, text
from sqlalchemy.dialects.postgresql import asyncpg as asyncpg_dialect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so `app.*` imports resolve when running as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.core.config import db_url_for_target, settings  # noqa: E402

# Game.user_id has a FK to users.id and User declares a relationship to OAuthAccount, so the
# mapped classes must all be imported before any select() against them compiles.
from app.models.game import Game  # noqa: E402
from app.models.game_flaw import GameFlaw  # noqa: E402
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.repositories.game_flaws_repository import _SEVERITY_INT  # noqa: E402
from app.repositories.query_utils import is_opponent_expr  # noqa: E402
from app.services import maia_engine  # noqa: E402
from app.services.blunder_check_rules import (  # noqa: E402
    FACEPALM_DRILL_LAMBDA,
    FACEPALM_SCORE_MIN,
)
from app.services.facepalm_score import facepalm_expr  # noqa: E402
from app.services.maia_flaw_scoring import (  # noqa: E402
    MAX_GAMES_PER_WRITE_TXN,
    GameMaiaScore,
    MaiaInferenceUnavailableError,
    ScoringMode,
    load_game_maia_inputs,
    score_game,
    write_game_maia_scores,
)

# No magic numbers (CLAUDE.md rule).
DEFAULT_WORKERS: int = 9
# One write transaction holds one advisory lock per game; MAX_GAMES_PER_WRITE_TXN is the cap.
DEFAULT_BATCH_GAMES: int = MAX_GAMES_PER_WRITE_TXN
# One ORT thread per process measured faster per position than ORT's default (plan 01).
MAIA_THREADS_PER_PROCESS: int = 1
# A batch with a per-game write failure counts as failed; this many in a row end the shard.
MAX_CONSECUTIVE_BATCH_FAILURES: int = 5
EXIT_OK: int = 0
EXIT_MAIA_UNAVAILABLE: int = 3
EXIT_SHARD_FAILED: int = 4
DEFAULT_REPORT_DIR: Path = _REPO_ROOT / "reports" / "maia-flaws-backfill"
RUN_STAMP_FORMAT: str = "%Y%m%dT%H%M%SZ"
MS_PER_SECOND: int = 1000

BackfillDb = Literal["dev", "benchmark", "prod"]
BACKFILL_DB_CHOICES: tuple[str, ...] = ("dev", "benchmark", "prod")
AbortReason = Literal["maia_unavailable", "too_many_batch_failures"]
BackfillMode = ScoringMode
BACKFILL_MODE_CHOICES: tuple[str, ...] = ("full", "spread", "line", "pre", "opponent", "reply")
DEFAULT_MODE: BackfillMode = "full"

# Top 8 hex digits of md5(game id) as an unsigned 32-bit integer. Unseeded and pure, so a
# game's shard is stable across processes, runs and table growth.
SHARD_RESIDUE_SQL: str = "('x' || substr(md5(g.id::text), 1, 8))::bit(32)::bigint"

# Priority: most recently active users first, then their newest games (deterministic).
_SELECT_SHARD_SQL: str = f"""
SELECT g.id
FROM games g
JOIN users u ON u.id = g.user_id
WHERE {{stamp_clause}}
  AND EXISTS (SELECT 1 FROM game_flaws f WHERE f.game_id = g.id)
  AND {SHARD_RESIDUE_SQL} % CAST(:num_shards AS bigint) = CAST(:shard AS bigint)
  {{user_clause}}
ORDER BY u.last_activity DESC NULLS LAST, g.played_at DESC NULLS LAST, g.id DESC
{{limit_clause}}
"""

# Games the spread pass still has to do (base-stamped, spread stamp NULL). Shared by the selector
# and the status counts so the two can never disagree.
_SPREAD_PENDING_CLAUSE: str = (
    "g.facepalm_spread_completed_at IS NULL AND g.maia_flaws_completed_at IS NOT NULL"
)

# Games the pre pass (254 D-08) still has to do: base-stamped, pre stamp NULL. Shared by the selector
# and the status counts, a constant and never user input.
_PRE_PENDING_CLAUSE: str = (
    "g.facepalm_pre_completed_at IS NULL AND g.maia_flaws_completed_at IS NOT NULL"
)

# Games the reply pass (259 D-07) still has to do: base-stamped, reply stamp NULL. Shared by the
# selector and the status counts, a constant and never user input (T-259-10).
_REPLY_PENDING_CLAUSE: str = (
    "g.facepalm_reply_completed_at IS NULL AND g.maia_flaws_completed_at IS NOT NULL"
)

# Games whose line stamp predates the cutoff (or was never set): the line pass is re-runnable, so
# the stamp counts only at or after the cutoff (250 D-18). The cutoff is the ONLY bound parameter
# of the mode clauses. Shared by the selector and the status counts.
_LINE_STALE_CLAUSE: str = (
    "(g.facepalm_line_completed_at IS NULL"
    " OR g.facepalm_line_completed_at < CAST(:cutoff AS timestamptz))"
)

# SQL text of "the mover of ply `ob.ply` is the game's opponent", compiled from the shared
# is_opponent_expr so the parity rule lives in one place. Compiled with the asyncpg dialect (the
# generic postgresql dialect targets a pyformat driver and would double the `%`, which asyncpg
# passes to Postgres verbatim); literal binds, so the text is built from constants only.
_OPPONENT_IS_MOVER_SQL: str = str(
    is_opponent_expr(literal_column("ob.ply"), literal_column("g.user_color")).compile(
        dialect=asyncpg_dialect.dialect(), compile_kwargs={"literal_binds": True}
    )
)

# Games the opponent pass (SEED-261114-iuv Part A) still has to do, selected BY ROW: an opponent
# blunder whose played probability is stored and whose reply spread is not. No stamp and no
# base-stamp requirement (the row predicate is the checkpoint). Shared by the selector and the
# status counts, built only from constants (never a CLI value). No guest filter, as in every other
# mode (the selector's users join has none).
_OPPONENT_PENDING_CLAUSE: str = (
    "EXISTS (SELECT 1 FROM game_flaws ob WHERE ob.game_id = g.id"
    f" AND ob.severity = {_SEVERITY_INT['blunder']}"
    " AND ob.maia_played_prob IS NOT NULL AND ob.maia_reply_spread IS NULL"
    f" AND {_OPPONENT_IS_MOVER_SQL})"
)

# The only mode-dependent part of the selector: one of these constants, never user input. The
# "opponent" slot holds a row predicate rather than a stamp predicate.
_STAMP_CLAUSE_BY_MODE: dict[BackfillMode, str] = {
    "full": "g.maia_flaws_completed_at IS NULL",
    "spread": _SPREAD_PENDING_CLAUSE,
    "pre": _PRE_PENDING_CLAUSE,
    "reply": _REPLY_PENDING_CLAUSE,
    "opponent": _OPPONENT_PENDING_CLAUSE,
    "line": f"{_LINE_STALE_CLAUSE} AND g.facepalm_spread_completed_at IS NOT NULL",
}

# Set by the SIGTERM/SIGINT handler; run_shard stops after the current batch.
_stop_requested: bool = False


def _log(msg: str = "") -> None:
    """Print a UTC-timestamped line, flushed (Python 3.14 block-buffers redirected stdout)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Selector
# ---------------------------------------------------------------------------


async def select_shard_game_ids(
    session: AsyncSession,
    *,
    shard: int,
    num_shards: int,
    user_id: int | None,
    limit: int | None,
    mode: BackfillMode = DEFAULT_MODE,
    cutoff: datetime | None = None,
) -> list[int]:
    """Ids of this shard's games still needing the mode's stamp that have flaws, in priority order.

    One snapshot at shard start; batches iterate it. Bound parameters only (the line mode's
    cutoff included); the mode picks one of a few constant predicates.
    """
    params: dict[str, Any] = {"shard": shard, "num_shards": num_shards}
    if mode == "line":
        if cutoff is None:
            raise ValueError("line mode needs a cutoff")
        params["cutoff"] = cutoff
    user_clause = ""
    if user_id is not None:
        user_clause = "AND g.user_id = :user_id"
        params["user_id"] = user_id
    limit_clause = ""
    if limit is not None:
        limit_clause = "LIMIT :limit"
        params["limit"] = limit
    sql = _SELECT_SHARD_SQL.format(
        stamp_clause=_STAMP_CLAUSE_BY_MODE[mode],
        user_clause=user_clause,
        limit_clause=limit_clause,
    )
    result = await session.execute(text(sql), params)
    return [row[0] for row in result.all()]


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@dataclass
class ShardReport:
    db: str
    shard: int
    num_shards: int
    run_stamp: str
    dry_run: bool
    mode: str = DEFAULT_MODE
    # The line pass's checkpoint, ISO 8601 with offset; None in every other mode.
    cutoff: str | None = None
    games_selected: int = 0
    games_scored: int = 0
    games_stamped: int = 0
    games_already_stamped: int = 0
    games_fingerprint_changed: int = 0
    games_missing: int = 0
    games_write_failed: int = 0
    games_score_failed: int = 0
    # Flaw rows that received Maia values / that were written all-NULL (reason in `reasons`).
    flaws_scored: int = 0
    flaws_null: int = 0
    # User-side blunders whose reply spread / facepalm score was written non-NULL / left NULL
    # (reason in `reasons`). The spread counters cover the modes that compute it (full, spread),
    # the score counters every mode that writes the score (full, spread, line).
    spreads_scored: int = 0
    spreads_null: int = 0
    scores_set: int = 0
    scores_null: int = 0
    # User-side blunders whose pre-blunder spread was written non-NULL / left NULL (modes full, pre;
    # 254 D-08, reason in `reasons`).
    pre_scored: int = 0
    pre_null: int = 0
    # Opponent blunders whose reply spread / pre-blunder spread was written non-NULL / left NULL
    # (modes full and opponent; SEED-261114-iuv Part A, reason in `reasons`).
    opponent_spreads_scored: int = 0
    opponent_spreads_null: int = 0
    opponent_pre_scored: int = 0
    opponent_pre_null: int = 0
    # Opponent blunders whose facts score non-NULL in memory / not (modes full and line;
    # SEED-261114-iuv Part A step 4). The user counterpart is scores_set / scores_null.
    opponent_scores_set: int = 0
    opponent_scores_null: int = 0
    # Blunders of either side whose best-reply probability was written non-NULL / left NULL (modes
    # full and reply; 259 D-07, reason in `reasons`).
    reply_probs_set: int = 0
    reply_probs_null: int = 0
    reasons: dict[str, int] = field(default_factory=dict)
    aborted_reason: str | None = None
    elapsed_s: float = 0.0
    flaws_per_s: float = 0.0

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True)


def _write_report(report: ShardReport, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{report.db}-{report.mode}-{report.run_stamp}-shard{report.shard}.json"
    path.write_text(report.to_json() + "\n")
    return path


# ---------------------------------------------------------------------------
# Shard run
# ---------------------------------------------------------------------------


def _install_signal_handlers() -> None:
    """Cooperative SIGINT/SIGTERM: finish the current batch, write the report, exit."""
    global _stop_requested
    _stop_requested = False

    def _request_stop(signum: int, _frame: object) -> None:
        global _stop_requested
        _log(f"signal {signum} received, stopping after this batch")
        _stop_requested = True

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)


def _tally_stamped(report: ShardReport, score: GameMaiaScore) -> None:
    """Count one scored game's flaws and reasons (stamped, or would-be in a dry run)."""
    if score.mode == "full":
        scored = sum(1 for row in score.rows if row["maia_played_prob"] is not None)
        report.flaws_scored += scored
        report.flaws_null += len(score.rows) - scored
    if score.mode in ("full", "spread"):
        report.spreads_scored += score.spreads_scored
        report.spreads_null += score.user_blunders - score.spreads_scored
    if score.mode in ("full", "spread", "line"):
        report.scores_set += score.scores_set
        report.scores_null += score.user_blunders - score.scores_set
    if score.mode in ("full", "pre"):
        report.pre_scored += score.pre_scored
        report.pre_null += score.user_blunders - score.pre_scored
    if score.mode in ("full", "line"):
        report.opponent_scores_set += score.opponent_scores_set
        report.opponent_scores_null += score.opponent_blunders - score.opponent_scores_set
    if score.mode in ("full", "opponent"):
        report.opponent_spreads_scored += score.opponent_spreads_scored
        report.opponent_spreads_null += score.opponent_blunders - score.opponent_spreads_scored
        report.opponent_pre_scored += score.opponent_pre_scored
        report.opponent_pre_null += score.opponent_blunders - score.opponent_pre_scored
    if score.mode in ("full", "reply"):
        reply_blunders = score.user_blunders + score.opponent_blunders
        report.reply_probs_set += score.reply_probs_set
        report.reply_probs_null += reply_blunders - score.reply_probs_set
    for reason, n in score.reasons.items():
        report.reasons[reason] = report.reasons.get(reason, 0) + n


def _score_batch(
    inputs_by_game: dict[int, Any],
    batch_ids: list[int],
    report: ShardReport,
    mode: BackfillMode = DEFAULT_MODE,
) -> list[GameMaiaScore]:
    """Score each loaded game from a PGN replay (D-06). MaiaInferenceUnavailableError aborts."""
    scores: list[GameMaiaScore] = []
    for game_id in batch_ids:
        inputs = inputs_by_game.get(game_id)
        if inputs is None:
            report.games_missing += 1
            continue
        try:
            scores.append(score_game(inputs, None, mode))
        except MaiaInferenceUnavailableError:
            raise
        except Exception:
            # One unscorable game must not kill the shard; it stays unstamped for the next run.
            sentry_sdk.set_context("maia_flaws_backfill", {"game_id": game_id})
            sentry_sdk.capture_exception()
            report.games_score_failed += 1
    return scores


def _tally_outcomes(
    report: ShardReport, scores: list[GameMaiaScore], outcomes: dict[int, str]
) -> None:
    by_game = {s.game_id: s for s in scores}
    for game_id, outcome in outcomes.items():
        if outcome == "stamped":
            report.games_stamped += 1
            _tally_stamped(report, by_game[game_id])
        elif outcome == "already_stamped":
            report.games_already_stamped += 1
        elif outcome == "fingerprint_changed":
            report.games_fingerprint_changed += 1
        elif outcome == "game_missing":
            report.games_missing += 1


async def _write_scores(
    session_maker: async_sessionmaker[AsyncSession],
    scores: list[GameMaiaScore],
    cutoff: datetime | None,
) -> dict[int, str]:
    # The mode rides on the scores; write_game_maia_scores checks that mode's own stamp (line
    # mode against the cutoff).
    async with session_maker() as session:
        outcomes = await write_game_maia_scores(
            session, scores, require_unstamped=True, line_cutoff=cutoff
        )
        await session.commit()
    return dict(outcomes)


async def _write_one_by_one(
    session_maker: async_sessionmaker[AsyncSession],
    scores: list[GameMaiaScore],
    report: ShardReport,
    shard: int,
    cutoff: datetime | None,
) -> dict[int, str]:
    """Retry a failed batch game by game so one poison game cannot sink the other 49."""
    outcomes: dict[int, str] = {}
    for score in scores:
        try:
            outcomes.update(await _write_scores(session_maker, [score], cutoff))
        except Exception:
            sentry_sdk.set_context(
                "maia_flaws_backfill", {"game_id": score.game_id, "shard": shard}
            )
            sentry_sdk.capture_exception()
            report.games_write_failed += 1
    return outcomes


async def _write_batch(
    session_maker: async_sessionmaker[AsyncSession],
    scores: list[GameMaiaScore],
    report: ShardReport,
    shard: int,
    cutoff: datetime | None,
) -> dict[int, str]:
    try:
        return await _write_scores(session_maker, scores, cutoff)
    except Exception:
        # The failed transaction rolled back with its session; nothing of it is stamped.
        return await _write_one_by_one(session_maker, scores, report, shard, cutoff)


async def _process_batch(
    session_maker: async_sessionmaker[AsyncSession],
    batch_ids: list[int],
    report: ShardReport,
    *,
    shard: int,
    dry_run: bool,
    mode: BackfillMode,
    cutoff: datetime | None,
) -> None:
    async with session_maker() as read_session:
        inputs_by_game = await load_game_maia_inputs(read_session, batch_ids)
    scores = _score_batch(inputs_by_game, batch_ids, report, mode)
    report.games_scored += len(scores)
    if dry_run:
        for score in scores:
            _tally_stamped(report, score)
        return
    if not scores:
        return
    outcomes = await _write_batch(session_maker, scores, report, shard, cutoff)
    _tally_outcomes(report, scores, outcomes)


def _finish_report(report: ShardReport, started: float) -> None:
    report.elapsed_s = round(time.monotonic() - started, 2)
    report.flaws_per_s = (
        round(report.flaws_scored / report.elapsed_s, 2) if report.elapsed_s else 0.0
    )


def _progress_line(report: ShardReport, done: int, started: float) -> str:
    elapsed = max(time.monotonic() - started, 1e-9)
    return (
        f"shard {report.shard}/{report.num_shards}: {done}/{report.games_selected} games, "
        f"stamped={report.games_stamped} flaws_scored={report.flaws_scored} "
        f"({report.flaws_scored / elapsed:.1f} flaws/s) "
        f"spreads_scored={report.spreads_scored} scores_set={report.scores_set} "
        f"pre_scored={report.pre_scored} "
        f"opponent_spreads_scored={report.opponent_spreads_scored} "
        f"reply_probs_set={report.reply_probs_set}"
        + (f" cutoff={report.cutoff}" if report.cutoff else "")
    )


async def _run_batches(
    session_maker: async_sessionmaker[AsyncSession],
    game_ids: list[int],
    report: ShardReport,
    *,
    batch_games: int,
    dry_run: bool,
    throttle_ms: int,
    started: float,
    mode: BackfillMode,
    cutoff: datetime | None,
) -> None:
    consecutive_failures = 0
    for start in range(0, len(game_ids), batch_games):
        if _stop_requested:
            _log(f"shard {report.shard}: stop requested, ending before batch at {start}")
            return
        write_failed_before = report.games_write_failed
        try:
            await _process_batch(
                session_maker,
                game_ids[start : start + batch_games],
                report,
                shard=report.shard,
                dry_run=dry_run,
                mode=mode,
                cutoff=cutoff,
            )
        except MaiaInferenceUnavailableError:
            report.aborted_reason = "maia_unavailable"
            return
        except Exception:
            # Read-side failure (DB unreachable): counts as a failed batch.
            sentry_sdk.set_context("maia_flaws_backfill", {"shard": report.shard})
            sentry_sdk.capture_exception()
            report.games_write_failed += batch_games
        failed = report.games_write_failed > write_failed_before
        consecutive_failures = consecutive_failures + 1 if failed else 0
        if consecutive_failures >= MAX_CONSECUTIVE_BATCH_FAILURES:
            report.aborted_reason = "too_many_batch_failures"
            return
        _log(_progress_line(report, min(start + batch_games, len(game_ids)), started))
        if throttle_ms > 0:
            await asyncio.sleep(throttle_ms / MS_PER_SECOND)


async def run_shard(
    *,
    db: BackfillDb,
    shard: int,
    num_shards: int,
    user_id: int | None,
    limit: int | None,
    batch_games: int,
    dry_run: bool,
    throttle_ms: int,
    report_dir: Path,
    run_stamp: str,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
    mode: BackfillMode = DEFAULT_MODE,
    cutoff: datetime | None = None,
) -> ShardReport:
    """Select, score and stamp one shard's games. Always writes the shard report."""
    engine = None
    if session_maker is None:
        engine = create_async_engine(
            db_url_for_target(db), pool_size=1, max_overflow=0, pool_pre_ping=True
        )
        session_maker = async_sessionmaker(engine, expire_on_commit=False)
    report = ShardReport(
        db=db,
        shard=shard,
        num_shards=num_shards,
        run_stamp=run_stamp,
        dry_run=dry_run,
        mode=mode,
        cutoff=cutoff.isoformat() if cutoff is not None else None,
    )
    started = time.monotonic()
    try:
        async with session_maker() as session:
            game_ids = await select_shard_game_ids(
                session,
                shard=shard,
                num_shards=num_shards,
                user_id=user_id,
                limit=limit,
                mode=mode,
                cutoff=cutoff,
            )
        report.games_selected = len(game_ids)
        _log(
            f"shard {shard}/{num_shards}: {len(game_ids)} games selected "
            f"(mode={mode}, dry_run={dry_run}, cutoff={report.cutoff})"
        )
        await _run_batches(
            session_maker,
            game_ids,
            report,
            batch_games=batch_games,
            dry_run=dry_run,
            throttle_ms=throttle_ms,
            started=started,
            mode=mode,
            cutoff=cutoff,
        )
    finally:
        _finish_report(report, started)
        path = _write_report(report, report_dir)
        _log(f"shard {shard}: report written to {path}")
        if engine is not None:
            await engine.dispose()
    return report


# ---------------------------------------------------------------------------
# Process entry, CLI
# ---------------------------------------------------------------------------


async def _start_maia_and_run(**shard_kwargs: Any) -> int:
    # The line pass is Maia-free (250 D-18): it never starts a session and a missing Maia is not
    # an error there, so it runs on boxes without onnxruntime or the model. Every other mode, the
    # pre pass (254 D-08) included, needs Maia and exits 3 without it.
    if shard_kwargs.get("mode") != "line":
        await maia_engine.start_maia(intra_op_num_threads=MAIA_THREADS_PER_PROCESS)
        if not maia_engine.is_maia_available():
            _log("Maia is unavailable in this process (onnxruntime or model missing); nothing done")
            return EXIT_MAIA_UNAVAILABLE
    report = await run_shard(**shard_kwargs)
    if report.aborted_reason == "maia_unavailable":
        return EXIT_MAIA_UNAVAILABLE
    return EXIT_SHARD_FAILED if report.aborted_reason is not None else EXIT_OK


def _shard_process_entry(
    *,
    db: BackfillDb,
    shard: int,
    num_shards: int,
    user_id: int | None,
    limit: int | None,
    batch_games: int,
    dry_run: bool,
    throttle_ms: int,
    report_dir: str,
    run_stamp: str,
    mode: BackfillMode = DEFAULT_MODE,
    cutoff: datetime | None = None,
) -> int:
    """One shard process: own Sentry, own single-threaded Maia session (none in line mode), own
    DB engine."""
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
    _install_signal_handlers()
    return asyncio.run(
        _start_maia_and_run(
            db=db,
            shard=shard,
            num_shards=num_shards,
            user_id=user_id,
            limit=limit,
            batch_games=batch_games,
            dry_run=dry_run,
            throttle_ms=throttle_ms,
            report_dir=Path(report_dir),
            run_stamp=run_stamp,
            mode=mode,
            cutoff=cutoff,
        )
    )


def _shard_process_target(**kwargs: Any) -> None:
    """mp.Process target: the child's exit code is the shard's exit code."""
    raise SystemExit(_shard_process_entry(**kwargs))


def _parse_cutoff(value: str) -> datetime:
    """argparse type for --cutoff: an ISO 8601 timestamp that carries a UTC offset.

    A naive timestamp is rejected: the server would read it in its own zone and the checkpoint
    would silently shift between operator machines.
    """
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("--cutoff must be an ISO 8601 timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise argparse.ArgumentTypeError("--cutoff needs a timezone offset, e.g. +00:00")
    return parsed


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sharded, resumable Maia flaw-stats backfill (stamp = checkpoint)"
    )
    parser.add_argument(
        "--db",
        choices=list(BACKFILL_DB_CHOICES),
        required=True,
        help="DB target: dev (5432), benchmark (5433), prod (via bin/prod_db_tunnel.sh).",
    )
    parser.add_argument(
        "--workers", type=int, default=DEFAULT_WORKERS, help="Shard processes to spawn."
    )
    parser.add_argument(
        "--num-shards",
        type=int,
        default=None,
        dest="num_shards",
        help="Total shards (default: --workers). Must equal --workers unless --shard is given.",
    )
    parser.add_argument(
        "--shard",
        type=int,
        default=None,
        help="Run exactly this one shard in-process (no spawn).",
    )
    parser.add_argument(
        "--mode",
        choices=list(BACKFILL_MODE_CHOICES),
        default=DEFAULT_MODE,
        help="full: all values + the stamps. spread: the facepalm columns of user-side "
        "blunders, on base-stamped games (Phase 250). line: the Maia-free line pass (needs "
        "--cutoff). pre: the two pre-blunder Maia inputs of user-side blunders, on "
        "base-stamped games (Phase 254). opponent: the three Maia columns of opponent blunders, "
        "selected by row, no stamp (SEED-261114-iuv Part A). reply: the best-reply probability "
        "of blunders of both sides, on base-stamped games (Phase 259).",
    )
    parser.add_argument(
        "--cutoff",
        type=_parse_cutoff,
        default=None,
        help="Line mode only (required there): ISO 8601 timestamp WITH offset, e.g. "
        "2026-11-10T12:00:00+00:00. Games whose line stamp is NULL or older than it are "
        "recomputed; re-run with the SAME value to resume, use a new one for a new recompute.",
    )
    parser.add_argument("--user-id", type=int, default=None, dest="user_id")
    parser.add_argument("--limit", type=int, default=None, help="Max games per shard.")
    parser.add_argument(
        "--batch-games",
        type=int,
        default=DEFAULT_BATCH_GAMES,
        dest="batch_games",
        help=f"Games per write transaction (max {MAX_GAMES_PER_WRITE_TXN}).",
    )
    parser.add_argument(
        "--throttle-ms", type=int, default=0, dest="throttle_ms", help="Sleep between batches."
    )
    parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR, dest="report_dir")
    parser.add_argument(
        "--status", action="store_true", help="Print progress counts (SELECT only) and exit."
    )
    args = parser.parse_args(argv)
    if args.mode == "line" and args.cutoff is None:
        parser.error("--mode line requires --cutoff")
    if args.mode != "line" and args.cutoff is not None:
        parser.error("--cutoff is only valid with --mode line")
    if args.num_shards is None:
        args.num_shards = args.workers
    if not 1 <= args.batch_games <= MAX_GAMES_PER_WRITE_TXN:
        parser.error(f"--batch-games must be between 1 and {MAX_GAMES_PER_WRITE_TXN}")
    if args.workers < 1 or args.num_shards < 1:
        parser.error("--workers and --num-shards must be at least 1")
    if args.shard is not None and not 0 <= args.shard < args.num_shards:
        parser.error("--shard must be in [0, --num-shards)")
    if args.shard is None and args.num_shards != args.workers and not args.status:
        parser.error("--num-shards must equal --workers unless --shard is given")
    return args


async def _print_banner(db: BackfillDb) -> None:
    """Show which database this run targets, never its URL."""
    engine = create_async_engine(db_url_for_target(db), pool_size=1, max_overflow=0)
    try:
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    text("SELECT current_database(), inet_server_addr(), inet_server_port()")
                )
            ).one()
    finally:
        await engine.dispose()
    _log(f"target: --db {db} -> database={row[0]} server={row[1]}:{row[2]}")


_STATUS_QUERIES: dict[str, str] = {
    "stamped_games": "SELECT count(*) FROM games g WHERE g.maia_flaws_completed_at IS NOT NULL{u}",
    "unstamped_games_with_flaws": (
        "SELECT count(*) FROM games g WHERE g.maia_flaws_completed_at IS NULL"
        " AND EXISTS (SELECT 1 FROM game_flaws f WHERE f.game_id = g.id){u}"
    ),
    "flaws_with_maia": (
        "SELECT count(*) FROM game_flaws g WHERE g.maia_played_prob IS NOT NULL{u}"
    ),
    "flaws_total": "SELECT count(*) FROM game_flaws g WHERE true{u}",
}


def _user_blunder_count_stmt(
    user_id: int | None,
    *,
    extra_where: Sequence[ColumnElement[bool]] = (),
) -> Select[Any]:
    """Count of user-side blunders (severity blunder AND NOT is_opponent_expr, D-03).

    `extra_where` narrows the count (e.g. blunders that carry a spread or a score).
    """
    stmt = (
        select(func.count())
        .select_from(GameFlaw)
        .join(Game, Game.id == GameFlaw.game_id)
        .where(
            GameFlaw.severity == _SEVERITY_INT["blunder"],
            not_(is_opponent_expr(GameFlaw.ply, Game.user_color)),
        )
    )
    if extra_where:
        stmt = stmt.where(*extra_where)
    if user_id is not None:
        stmt = stmt.where(Game.user_id == user_id)
    return stmt


def _blunder_count_stmt(
    user_id: int | None,
    *,
    extra_where: Sequence[ColumnElement[bool]] = (),
) -> Select[Any]:
    """Count of blunders of BOTH sides (severity blunder, no side filter; 259 D-10), joined to games
    for the user filter. `extra_where` narrows the count."""
    stmt = (
        select(func.count())
        .select_from(GameFlaw)
        .join(Game, Game.id == GameFlaw.game_id)
        .where(GameFlaw.severity == _SEVERITY_INT["blunder"])
    )
    if extra_where:
        stmt = stmt.where(*extra_where)
    if user_id is not None:
        stmt = stmt.where(Game.user_id == user_id)
    return stmt


_SPREAD_STATUS_QUERIES: dict[str, str] = {
    "spread_stamped_games": (
        "SELECT count(*) FROM games g WHERE g.facepalm_spread_completed_at IS NOT NULL{u}"
    ),
    "spread_pending_games": (
        f"SELECT count(*) FROM games g WHERE {_SPREAD_PENDING_CLAUSE}"
        " AND EXISTS (SELECT 1 FROM game_flaws f WHERE f.game_id = g.id){u}"
    ),
}


async def _scalar_count(session: AsyncSession, stmt: Select[Any]) -> int:
    return int((await session.execute(stmt)).scalar_one())


async def _fetch_facepalm_value_counts(
    session: AsyncSession, user_id: int | None, *, with_spread: bool
) -> dict[str, int]:
    """User-side blunder counts the operator plans read: total, with spread (spread mode only),
    with a score, and qualifying at FACEPALM_SCORE_MIN (D-06: severity blunder, not opponent).

    The score and qualifying counts use facepalm_expr(FACEPALM_DRILL_LAMBDA), the expression the
    drill selects with (254 D-01, D-12), never the stored column: the counts then say how many
    blunders the drill can actually draw, and they follow a refit without a rewrite.
    """
    score = facepalm_expr(FACEPALM_DRILL_LAMBDA)
    counts = {
        "user_blunders_total": await _scalar_count(session, _user_blunder_count_stmt(user_id))
    }
    if with_spread:
        counts["user_blunders_with_spread"] = await _scalar_count(
            session,
            _user_blunder_count_stmt(
                user_id, extra_where=[GameFlaw.maia_reply_spread.is_not(None)]
            ),
        )
    counts["user_blunders_with_score"] = await _scalar_count(
        session,
        _user_blunder_count_stmt(user_id, extra_where=[score.is_not(None)]),
    )
    counts["user_blunders_qualifying"] = await _scalar_count(
        session,
        _user_blunder_count_stmt(user_id, extra_where=[score >= FACEPALM_SCORE_MIN]),
    )
    return counts


# Line pass progress against a cutoff: done = spread-stamped games whose line stamp is at or after
# it, pending = the selector's own predicate (same constant, so they cannot drift apart).
_LINE_STATUS_QUERIES: dict[str, str] = {
    "line_done_since_cutoff": (
        "SELECT count(*) FROM games g WHERE g.facepalm_spread_completed_at IS NOT NULL"
        f" AND NOT {_LINE_STALE_CLAUSE}"
        " AND EXISTS (SELECT 1 FROM game_flaws f WHERE f.game_id = g.id){u}"
    ),
    "line_pending_games": (
        f"SELECT count(*) FROM games g WHERE {_LINE_STALE_CLAUSE}"
        " AND g.facepalm_spread_completed_at IS NOT NULL"
        " AND EXISTS (SELECT 1 FROM game_flaws f WHERE f.game_id = g.id){u}"
    ),
}


_PRE_STATUS_QUERIES: dict[str, str] = {
    "pre_stamped_games": (
        "SELECT count(*) FROM games g WHERE g.facepalm_pre_completed_at IS NOT NULL{u}"
    ),
    "pre_pending_games": (
        f"SELECT count(*) FROM games g WHERE {_PRE_PENDING_CLAUSE}"
        " AND EXISTS (SELECT 1 FROM game_flaws f WHERE f.game_id = g.id){u}"
    ),
}


async def _stamp_counts(
    session: AsyncSession,
    user_id: int | None,
    queries: dict[str, str],
    cutoff: datetime | None = None,
) -> dict[str, int]:
    """Run the stamp-count queries (`queries`, each with a `{u}` user clause slot)."""
    user_clause = " AND g.user_id = :user_id" if user_id is not None else ""
    params: dict[str, Any] = {"user_id": user_id} if user_id is not None else {}
    if cutoff is not None:
        params["cutoff"] = cutoff
    counts: dict[str, int] = {}
    for key, sql in queries.items():
        counts[key] = int(
            (await session.execute(text(sql.format(u=user_clause)), params)).scalar_one()
        )
    return counts


async def _fetch_facepalm_status(
    session: AsyncSession,
    user_id: int | None,
    queries: dict[str, str],
    *,
    cutoff: datetime | None = None,
    with_spread: bool,
) -> dict[str, int]:
    """Stamp-count queries (`queries`) followed by the user-blunder value counts."""
    counts = await _stamp_counts(session, user_id, queries, cutoff)
    counts.update(await _fetch_facepalm_value_counts(session, user_id, with_spread=with_spread))
    return counts


async def _fetch_pre_status(session: AsyncSession, user_id: int | None) -> dict[str, int]:
    """Pre pass progress (254 D-08): the stamp counts, then the user-side blunders in total and
    with a best-move probability / a pre-blunder spread."""
    counts = await _stamp_counts(session, user_id, _PRE_STATUS_QUERIES)
    counts["user_blunders_total"] = await _scalar_count(session, _user_blunder_count_stmt(user_id))
    counts["user_blunders_with_best_prob"] = await _scalar_count(
        session,
        _user_blunder_count_stmt(user_id, extra_where=[GameFlaw.maia_best_prob.is_not(None)]),
    )
    counts["user_blunders_with_pre_spread"] = await _scalar_count(
        session,
        _user_blunder_count_stmt(user_id, extra_where=[GameFlaw.maia_pre_spread.is_not(None)]),
    )
    return counts


_REPLY_STATUS_QUERIES: dict[str, str] = {
    "reply_stamped_games": (
        "SELECT count(*) FROM games g WHERE g.facepalm_reply_completed_at IS NOT NULL{u}"
    ),
    "reply_pending_games": (
        f"SELECT count(*) FROM games g WHERE {_REPLY_PENDING_CLAUSE}"
        " AND EXISTS (SELECT 1 FROM game_flaws f WHERE f.game_id = g.id){u}"
    ),
}


async def _fetch_reply_status(session: AsyncSession, user_id: int | None) -> dict[str, int]:
    """Reply pass progress (259 D-07), the counts the readiness gate before the switch reads.

    The stamp counts, then blunders of both sides in total and with a best-reply probability, then
    the residues a finished pass leaves (each restricted to rows the hook scored, played probability
    set): `reply_residue_losing` (a losing blunder, material_loss > 0, still without a reply
    probability: no refutation line or a reply outside the policy), `unscored_pure_miss_no_best`
    (no material loss and no best-move probability: the score cannot be computed) and
    `blunders_without_material_inputs` (the line pass has not filled the scalars).
    """
    counts = await _stamp_counts(session, user_id, _REPLY_STATUS_QUERIES)
    scored = GameFlaw.maia_played_prob.is_not(None)
    value_filters: dict[str, Sequence[ColumnElement[bool]]] = {
        "blunders_total": (),
        "blunders_with_reply_prob": [GameFlaw.maia_best_reply_prob.is_not(None)],
        "reply_residue_losing": [
            scored,
            GameFlaw.material_loss > 0,
            GameFlaw.maia_best_reply_prob.is_(None),
        ],
        "unscored_pure_miss_no_best": [
            scored,
            GameFlaw.material_loss <= 0,
            GameFlaw.maia_best_prob.is_(None),
        ],
        "blunders_without_material_inputs": [scored, GameFlaw.material_loss.is_(None)],
    }
    for key, extra_where in value_filters.items():
        counts[key] = await _scalar_count(
            session, _blunder_count_stmt(user_id, extra_where=extra_where)
        )
    return counts


async def _fetch_material_input_counts(
    session: AsyncSession, user_id: int | None
) -> dict[str, int]:
    """Line pass progress on the stored material inputs (259 D-05): blunders of each side whose
    material_loss is written, the counts the readiness gate compares with the blunder totals."""
    has_loss = [GameFlaw.material_loss.is_not(None)]
    return {
        "user_blunders_with_material_inputs": await _scalar_count(
            session, _user_blunder_count_stmt(user_id, extra_where=has_loss)
        ),
        "opponent_blunders_with_material_inputs": await _scalar_count(
            session, _opponent_blunder_count_stmt(user_id, extra_where=has_loss)
        ),
    }


# Opponent pass progress (SEED-261114-iuv Part A): the games the selector would pick, from its own
# constant so the two cannot drift apart.
_OPPONENT_STATUS_QUERIES: dict[str, str] = {
    "opponent_pending_games": (
        f"SELECT count(*) FROM games g WHERE {_OPPONENT_PENDING_CLAUSE}"
        " AND EXISTS (SELECT 1 FROM game_flaws f WHERE f.game_id = g.id){u}"
    ),
}


def _opponent_blunder_count_stmt(
    user_id: int | None,
    *,
    extra_where: Sequence[ColumnElement[bool]] = (),
) -> Select[Any]:
    """Count of opponent blunders (severity blunder AND is_opponent_expr); the mirror image of
    `_user_blunder_count_stmt`. `extra_where` narrows the count."""
    stmt = (
        select(func.count())
        .select_from(GameFlaw)
        .join(Game, Game.id == GameFlaw.game_id)
        .where(
            GameFlaw.severity == _SEVERITY_INT["blunder"],
            is_opponent_expr(GameFlaw.ply, Game.user_color),
        )
    )
    if extra_where:
        stmt = stmt.where(*extra_where)
    if user_id is not None:
        stmt = stmt.where(Game.user_id == user_id)
    return stmt


async def _fetch_opponent_status(session: AsyncSession, user_id: int | None) -> dict[str, int]:
    """Opponent pass progress: the pending games, then the opponent blunders in total and per
    filled column. `opponent_blunders_pending` (played prob set, reply spread NULL) is what a
    finished run leaves: the residue the pass cannot score (stalemating blunders, boards that
    cannot be rebuilt)."""
    counts = await _stamp_counts(session, user_id, _OPPONENT_STATUS_QUERIES)
    value_filters: dict[str, Sequence[ColumnElement[bool]]] = {
        "opponent_blunders_total": (),
        "opponent_blunders_with_played_prob": [GameFlaw.maia_played_prob.is_not(None)],
        "opponent_blunders_with_spread": [GameFlaw.maia_reply_spread.is_not(None)],
        "opponent_blunders_with_pre_spread": [GameFlaw.maia_pre_spread.is_not(None)],
        "opponent_blunders_with_best_prob": [GameFlaw.maia_best_prob.is_not(None)],
        "opponent_blunders_pending": [
            GameFlaw.maia_played_prob.is_not(None),
            GameFlaw.maia_reply_spread.is_(None),
        ],
    }
    for key, extra_where in value_filters.items():
        counts[key] = await _scalar_count(
            session, _opponent_blunder_count_stmt(user_id, extra_where=extra_where)
        )
    return counts


async def _fetch_opponent_line_counts(session: AsyncSession, user_id: int | None) -> dict[str, int]:
    """Line pass progress on the opponent side: operator counts of opponent blunders in total, with
    stored material inputs and with a drill score (SEED-261114-iuv Part A step 4). Never user-facing."""
    score = facepalm_expr(FACEPALM_DRILL_LAMBDA)
    value_filters: dict[str, Sequence[ColumnElement[bool]]] = {
        "opponent_blunders_total": (),
        "opponent_blunders_with_material_inputs": [GameFlaw.material_loss.is_not(None)],
        "opponent_blunders_with_score": [score.is_not(None)],
    }
    return {
        key: await _scalar_count(
            session, _opponent_blunder_count_stmt(user_id, extra_where=extra_where)
        )
        for key, extra_where in value_filters.items()
    }


async def fetch_status(
    session_maker: async_sessionmaker[AsyncSession],
    user_id: int | None,
    mode: BackfillMode = DEFAULT_MODE,
    cutoff: datetime | None = None,
) -> dict[str, int]:
    """The progress counts, SELECT-only, optionally for one user.

    Full mode keeps the four 247 counts (the 247-07 monitor greps that line); spread mode
    returns the Phase 250 stamp and value counts; pre mode the 254 stamp and pre-input counts;
    opponent mode (SEED-261114-iuv Part A) the pending games, the opponent-blunder counts per
    filled column and the residue (`opponent_blunders_pending`); reply mode (259 D-07) the stamp
    counts, the both-sides blunder counts and the readiness residues; line mode (needs `cutoff`)
    the games done / pending against it plus the user score counts, then the opponent line counts
    and the material-input counts of both sides.
    """
    if mode == "spread":
        async with session_maker() as session:
            return await _fetch_facepalm_status(
                session, user_id, _SPREAD_STATUS_QUERIES, with_spread=True
            )
    if mode == "pre":
        async with session_maker() as session:
            return await _fetch_pre_status(session, user_id)
    if mode == "opponent":
        async with session_maker() as session:
            return await _fetch_opponent_status(session, user_id)
    if mode == "reply":
        async with session_maker() as session:
            return await _fetch_reply_status(session, user_id)
    if mode == "line":
        if cutoff is None:
            raise ValueError("line mode status needs a cutoff")
        async with session_maker() as session:
            counts = await _fetch_facepalm_status(
                session, user_id, _LINE_STATUS_QUERIES, cutoff=cutoff, with_spread=False
            )
            # The unchanged user keys come first, then the opponent counts (line facts of both sides).
            counts.update(await _fetch_opponent_line_counts(session, user_id))
            counts.update(await _fetch_material_input_counts(session, user_id))
            return counts
    user_clause = " AND g.user_id = :user_id" if user_id is not None else ""
    params: dict[str, Any] = {"user_id": user_id} if user_id is not None else {}
    counts: dict[str, int] = {}
    async with session_maker() as session:
        for key, sql in _STATUS_QUERIES.items():
            result = await session.execute(text(sql.format(u=user_clause)), params)
            counts[key] = int(result.scalar_one())
    return counts


async def _print_status(
    db: BackfillDb,
    user_id: int | None,
    mode: BackfillMode = DEFAULT_MODE,
    cutoff: datetime | None = None,
) -> None:
    engine = create_async_engine(db_url_for_target(db), pool_size=1, max_overflow=0)
    try:
        counts = await fetch_status(
            async_sessionmaker(engine, expire_on_commit=False), user_id, mode, cutoff
        )
    finally:
        await engine.dispose()
    print(" ".join(f"{k}={v}" for k, v in counts.items()), flush=True)


def _shard_kwargs(args: argparse.Namespace, run_stamp: str, shard: int) -> dict[str, Any]:
    return {
        "db": args.db,
        "shard": shard,
        "num_shards": args.num_shards,
        "user_id": args.user_id,
        "limit": args.limit,
        "batch_games": args.batch_games,
        "dry_run": args.dry_run,
        "throttle_ms": args.throttle_ms,
        "report_dir": str(args.report_dir),
        "run_stamp": run_stamp,
        "mode": args.mode,
        "cutoff": args.cutoff,
    }


def _combined_total_line(reports: list[dict[str, Any]]) -> str:
    keys = (
        "games_selected",
        "games_scored",
        "games_stamped",
        "games_already_stamped",
        "games_fingerprint_changed",
        "games_missing",
        "games_write_failed",
        "games_score_failed",
        "flaws_scored",
        "flaws_null",
        "spreads_scored",
        "spreads_null",
        "scores_set",
        "scores_null",
        "pre_scored",
        "pre_null",
        "opponent_spreads_scored",
        "opponent_spreads_null",
        "opponent_pre_scored",
        "opponent_pre_null",
        "opponent_scores_set",
        "opponent_scores_null",
    )
    totals = {k: sum(int(r.get(k, 0)) for r in reports) for k in keys}
    reasons: Counter[str] = Counter()
    for r in reports:
        reasons.update(r.get("reasons", {}))
    pairs = [f"{k}={v}" for k, v in totals.items()]
    pairs += [f"reason_{name}={n}" for name, n in sorted(reasons.items()) if n]
    return "total: " + " ".join(pairs)


def _run_spawned_shards(args: argparse.Namespace, run_stamp: str) -> int:
    ctx = mp.get_context("spawn")
    procs = [
        ctx.Process(target=_shard_process_target, kwargs=_shard_kwargs(args, run_stamp, shard))
        for shard in range(args.num_shards)
    ]
    forwarded = False

    def _on_signal(signum: int, _frame: object) -> None:
        # Forward to the children (they finish their batch and write their report) and
        # keep joining: the parent must outlive them to print the combined line.
        nonlocal forwarded
        if not forwarded:
            forwarded = True
            _log(f"signal {signum} received, asking shards to stop after their batch")
            for p in procs:
                if p.is_alive():
                    p.terminate()

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    for p in procs:
        p.start()
    for p in procs:
        p.join()
    reports = _read_reports(args, run_stamp, range(args.num_shards))
    print(_combined_total_line(reports), flush=True)
    return max((p.exitcode or 0) for p in procs)


def _read_reports(
    args: argparse.Namespace, run_stamp: str, shards: Sequence[int]
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for shard in shards:
        path = args.report_dir / f"{args.db}-{args.mode}-{run_stamp}-shard{shard}.json"
        if path.exists():
            reports.append(json.loads(path.read_text()))
        else:
            _log(f"shard {shard}: no report found at {path}")
    return reports


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    asyncio.run(_print_banner(args.db))
    if args.status:
        asyncio.run(_print_status(args.db, args.user_id, args.mode, args.cutoff))
        return EXIT_OK
    run_stamp = datetime.now(timezone.utc).strftime(RUN_STAMP_FORMAT)
    if args.shard is not None:
        code = _shard_process_entry(**_shard_kwargs(args, run_stamp, args.shard))
        reports = _read_reports(args, run_stamp, [args.shard])
        print(_combined_total_line(reports), flush=True)
        return code
    return _run_spawned_shards(args, run_stamp)


if __name__ == "__main__":
    raise SystemExit(main())
