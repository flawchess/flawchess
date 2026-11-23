"""Recompute the stored facepalm material inputs of promotion rows in place (Phase 262 D-06, D-07).

Why a dedicated script instead of `backfill_maia_flaws.py --mode line`:
    Line mode is game-scoped, stamps games and its rows do not carry the stored material, so it
    cannot report "would change" and cannot be limited to the rows a rule change touches. D-07 is
    row-scoped: only blunders with a promotion in the lines the rule reads are recomputed, and the
    dry run must say which rows would change and prove that the other rows would not.

Scope (D-07): blunders (severity 2, both sides) of games the line pass already processed
(`facepalm_line_completed_at` set) with a promotion token in the refutation line
(`game_positions.pv` at ply + 1), the best line (`pv` or `best_move` at the flaw ply) or the played
move (`move_san` at the flaw ply contains "="). Stored-NULL rows are included: a short line that
ends on a promotion can now settle. Each row is rebuilt with the app's single writer
(`facepalm_material_inputs` on the replayed pre-blunder board, guarded by
`board_fen() == game_flaws.fen`). No engine and no Maia (259 D-05).

Float rule (Phase 262 research, correction c): `material_loss` / `material_missed` are REAL
(4-byte floats). A row counts as changed only when the recomputed pair, rounded to a 4-byte float,
differs from the stored pair, so a float32-only difference is never written (the discuss probe
compared float64 replays at 1e-9 and counted 710 dev changes where 624 were real).

Dry run: one read-only connection with a statement timeout, writes nothing, no undo log. It reports
the candidates and how many would change, then checks a deterministic sample of blunders WITHOUT a
promotion token: they must replay to their stored pair. Any mismatch exits 3 (the token filter
missed a place the rule reads, so do not run the real pass).

Real run (D-06): on ONE connection (`pool_size=1`, `max_overflow=0`; prod `max_connections` is 50),
page by page in keyset order of the primary key, one transaction per page. A row is written with a
guarded UPDATE (`material_loss` / `material_missed` IS NOT DISTINCT FROM the values read), so a
concurrent write by the go-forward hook is never clobbered (counted as a guard miss). Every applied
row is appended to the undo log, a TSV under gitignored `temp/promotion-pass/`
(`user_id game_id ply old_loss old_missed new_loss new_missed`). The pass overwrites the stored pair
in place, so the log is the way back: a rollback is a replay-free guarded UPDATE of each logged row
to its old pair (WHERE the current pair equals the logged new pair). The pass is idempotent: a
re-run recomputes the same values and changes 0 rows, which also makes the re-run the restart path
after an interruption (SIGINT / SIGTERM finish the current page).

Run on prod from the orchestrator right after the deploy, detached, never from a subagent:
    PYTHONUNBUFFERED=1 setsid nohup uv run python scripts/backfill_promotion_material.py --db prod &

Usage:
    uv run python scripts/backfill_promotion_material.py --db dev --dry-run
    uv run python scripts/backfill_promotion_material.py --db dev
    uv run python scripts/backfill_promotion_material.py --db dev --user-id 28 --limit 500
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import struct
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import sentry_sdk
from sqlalchemy import ColumnElement, Select, and_, func, literal, or_, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import aliased

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import db_url_for_target, settings  # noqa: E402
from app.models.game import Game  # noqa: E402
from app.models.game_flaw import GameFlaw  # noqa: E402
from app.models.game_position import GamePosition  # noqa: E402

# GameFlaw / GamePosition carry FKs to games -> users -> oauth_accounts; register the whole chain
# so select() compiles (same reason as scripts/retag_flaws.py).
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.services.facepalm_inputs import MaterialInputs, facepalm_material_inputs  # noqa: E402
from app.services.facepalm_score import facepalm_type_of  # noqa: E402
from app.services.maia_flaw_scoring import replay_flaw_boards  # noqa: E402
from scripts.blunder_check.sample import BLUNDER_SEVERITY, make_readonly_engine  # noqa: E402

# ---------------------------------------------------------------------------
# Named constants (no magic numbers)
# ---------------------------------------------------------------------------

# A promotion token in a stored UCI line: from-square on the 7th / 2nd rank, to-square on the
# 8th / 1st rank, a promotion letter, delimited by the line start / end or a space.
PROMOTION_IN_LINE_RE: str = r"(^| )[a-h][27][a-h][18][qrbn]( |$)"
# A promotion token as the whole stored `best_move` (5-char UCI).
PROMOTION_MOVE_RE: str = r"^[a-h][27][a-h][18][qrbn]$"
# The played move: SAN of a promotion carries "=" (for example "a8=Q").
PROMOTION_SAN_PATTERN: str = "%=%"
# Rows per page and per transaction (prod `max_connections` is 50, one connection).
FLAWS_PER_BATCH: int = 2000
# Dry-run sample of blunders WITHOUT a promotion token: deterministic by game id residue.
DEFAULT_SAMPLE_SIZE: int = 2000
SAMPLE_GAME_MODULUS: int = 50
SAMPLE_MISMATCHES_LISTED: int = 10
DEFAULT_REPORT_DIR: Path = Path("reports/maia-flaws-backfill")
DEFAULT_UNDO_DIR: Path = Path("temp/promotion-pass")
EXIT_OK: int = 0
EXIT_SAMPLE_MISMATCH: int = 3
UNDO_LOG_HEADER: str = "user_id\tgame_id\tply\told_loss\told_missed\tnew_loss\tnew_missed"
UNDO_NULL: str = "NULL"
REPORT_STAMP_FORMAT: str = "%Y%m%dT%H%M%SZ"
# `struct` format of a 4-byte float, the width of a REAL column.
FLOAT4_FORMAT: str = "f"

TargetDb = Literal["dev", "prod"]

# Set by the SIGTERM / SIGINT handler; run_pass stops after the current page.
_stop_requested: bool = False


def _log(msg: str = "") -> None:
    """Print a UTC-timestamped line, flushed (Python 3.14 block-buffers redirected stdout)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Float rule
# ---------------------------------------------------------------------------


def as_real(value: float | None) -> float | None:
    """Round a float to the 4-byte float a REAL column stores (None stays None).

    Bug-fix note: the Phase 262 discuss probe compared float64 replays to the stored REAL values at
    1e-9 and counted 710 changed dev rows where 624 were real. Decaying means such as
    1.4516129032258065 are not representable in 4 bytes, so the stored value differs from the
    replay by about 1e-8 although nothing changed. Compare in this representation.
    """
    if value is None:
        return None
    return struct.unpack(FLOAT4_FORMAT, struct.pack(FLOAT4_FORMAT, value))[0]


# ---------------------------------------------------------------------------
# Candidate query
# ---------------------------------------------------------------------------


def promotion_candidate_filter(
    p0: type[GamePosition], p1: type[GamePosition]
) -> ColumnElement[bool]:
    """D-07: a promotion token in a place the rule reads. Never NULL, so its negation is safe.

    `p0` is the position at the flaw ply (best line, best move, played move), `p1` the position at
    ply + 1 (the refutation line). The coalesce keeps every branch non-NULL, so `~filter` is exactly
    the rows without a token (the dry-run sample check relies on this).
    """
    return or_(
        func.coalesce(p1.pv, "").regexp_match(PROMOTION_IN_LINE_RE),
        func.coalesce(p0.pv, "").regexp_match(PROMOTION_IN_LINE_RE),
        func.coalesce(p0.best_move, "").regexp_match(PROMOTION_MOVE_RE),
        func.coalesce(p0.move_san, "").like(PROMOTION_SAN_PATTERN),
    )


def _blunder_stmt(
    user_id: int | None,
) -> tuple[Select[Any], type[GamePosition], type[GamePosition]]:
    """Blunders of line-stamped games with their flaw-ply and ply + 1 positions, unfiltered."""
    p0 = aliased(GamePosition)
    p1 = aliased(GamePosition)
    stmt = (
        select(
            GameFlaw.user_id,
            GameFlaw.game_id,
            GameFlaw.ply,
            GameFlaw.fen,
            GameFlaw.material_loss,
            GameFlaw.material_missed,
            p0.pv.label("best_pv"),
            p0.best_move.label("best_move"),
            p1.pv.label("refutation_pv"),
        )
        .join(Game, Game.id == GameFlaw.game_id)
        .join(
            p0,
            and_(
                p0.user_id == GameFlaw.user_id,
                p0.game_id == GameFlaw.game_id,
                p0.ply == GameFlaw.ply,
            ),
        )
        .outerjoin(
            p1,
            and_(
                p1.user_id == GameFlaw.user_id,
                p1.game_id == GameFlaw.game_id,
                p1.ply == GameFlaw.ply + 1,
            ),
        )
        .where(
            GameFlaw.severity == BLUNDER_SEVERITY,
            Game.facepalm_line_completed_at.is_not(None),
        )
    )
    if user_id is not None:
        stmt = stmt.where(GameFlaw.user_id == user_id)
    return stmt, p0, p1


def candidate_page_stmt(
    *, after: tuple[int, int, int] | None, limit: int, user_id: int | None
) -> Select[Any]:
    """One keyset page of candidate rows in primary-key order (user_id, game_id, ply)."""
    stmt, p0, p1 = _blunder_stmt(user_id)
    stmt = stmt.where(promotion_candidate_filter(p0, p1))
    if after is not None:
        stmt = stmt.where(
            tuple_(GameFlaw.user_id, GameFlaw.game_id, GameFlaw.ply)
            > tuple_(*(literal(v) for v in after))
        )
    return stmt.order_by(GameFlaw.user_id, GameFlaw.game_id, GameFlaw.ply).limit(limit)


def _sample_stmt(*, size: int, modulus: int, user_id: int | None) -> Select[Any]:
    """A deterministic sample of blunders WITHOUT a promotion token (game id residue 0)."""
    stmt, p0, p1 = _blunder_stmt(user_id)
    stmt = stmt.where(~promotion_candidate_filter(p0, p1), GameFlaw.game_id % modulus == 0)
    return stmt.order_by(GameFlaw.user_id, GameFlaw.game_id, GameFlaw.ply).limit(size)


@dataclass(frozen=True)
class CandidateRow:
    """One blunder as read: its key, the stored pair and the stored lines the rule reads."""

    user_id: int
    game_id: int
    ply: int
    fen: str
    stored_loss: float | None
    stored_missed: float | None
    best_pv: str | None
    best_move: str | None
    refutation_pv: str | None


@dataclass(frozen=True)
class RowChange:
    """A row whose stored pair differs from the recomputed pair (both in 4-byte float form)."""

    row: CandidateRow
    new_loss: float | None
    new_missed: float | None


# ---------------------------------------------------------------------------
# Replay and compare
# ---------------------------------------------------------------------------


def replay_inputs(pgn: str, rows: Sequence[CandidateRow]) -> tuple[dict[int, MaterialInputs], int]:
    """Recompute the stored pair of each row of ONE game with the app's single writer.

    Returns ({ply: inputs}, board_failures). A row whose ply the PGN never reaches, or whose replayed
    `board_fen()` differs from `game_flaws.fen`, is skipped and counted, never guessed.
    """
    boards, _reason = replay_flaw_boards(pgn, {r.ply for r in rows})
    inputs: dict[int, MaterialInputs] = {}
    failures = 0
    for row in rows:
        entry = boards.get(row.ply)
        if entry is None or entry[0].board_fen() != row.fen:
            failures += 1
            continue
        board, played_uci = entry
        inputs[row.ply] = facepalm_material_inputs(
            board, played_uci, row.refutation_pv, row.best_pv or row.best_move
        )
    return inputs, failures


def classify_change(row: CandidateRow, new: MaterialInputs) -> RowChange | None:
    """The change of a row, or None when the pair is equal in 4-byte float form."""
    new_loss, new_missed = as_real(new.loss), as_real(new.missed)
    if (new_loss, new_missed) == (row.stored_loss, row.stored_missed):
        return None
    return RowChange(row=row, new_loss=new_loss, new_missed=new_missed)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@dataclass
class PassReport:
    """Counters of one run. `changed` is would-change in a dry run, applied rows in a real run."""

    db: str
    dry_run: bool
    candidates: int = 0
    changed: int = 0
    loss_up: int = 0
    loss_down: int = 0
    missed_up: int = 0
    missed_down: int = 0
    null_to_value: int = 0
    value_to_null: int = 0
    type_missed_to_allowed: int = 0
    type_allowed_to_missed: int = 0
    board_failures: int = 0
    guard_misses: int = 0
    sample_checked: int = 0
    sample_mismatches: int = 0
    sample_mismatch_rows: list[tuple[int, int]] = field(default_factory=list)
    pages: int = 0
    elapsed_s: float = 0.0
    stopped_early: bool = False
    undo_log: Path | None = None
    report_path: Path | None = None


def exit_code_for(report: PassReport, *, dry_run: bool) -> int:
    """3 when a dry run found a non-token row that does not replay to its stored pair."""
    if dry_run and report.sample_mismatches > 0:
        return EXIT_SAMPLE_MISMATCH
    return EXIT_OK


def _direction(old: float | None, new: float | None) -> Literal["up", "down", "same"]:
    if old is None or new is None or old == new:
        return "same"
    return "up" if new > old else "down"


def _type_flip(change: RowChange) -> Literal["missed_to_allowed", "allowed_to_missed"] | None:
    """The type flip of a change, from the old and the new pair (None when the type is unchanged)."""
    row = change.row
    if row.stored_loss is None or change.new_loss is None:
        return None
    old_type = facepalm_type_of(row.stored_loss, row.stored_missed or 0.0)
    new_type = facepalm_type_of(change.new_loss, change.new_missed or 0.0)
    if old_type == "missed_win" and new_type == "allowed_loss":
        return "missed_to_allowed"
    if old_type == "allowed_loss" and new_type == "missed_win":
        return "allowed_to_missed"
    return None


def _tally(report: PassReport, change: RowChange) -> None:
    """Add one change to the direction, NULL and type-flip counters."""
    row = change.row
    report.changed += 1
    loss_dir = _direction(row.stored_loss, change.new_loss)
    missed_dir = _direction(row.stored_missed, change.new_missed)
    report.loss_up += loss_dir == "up"
    report.loss_down += loss_dir == "down"
    report.missed_up += missed_dir == "up"
    report.missed_down += missed_dir == "down"
    report.null_to_value += row.stored_loss is None and change.new_loss is not None
    report.value_to_null += row.stored_loss is not None and change.new_loss is None
    flip = _type_flip(change)
    report.type_missed_to_allowed += flip == "missed_to_allowed"
    report.type_allowed_to_missed += flip == "allowed_to_missed"


def write_report(report: PassReport, *, report_dir: Path, run_stamp: str) -> Path:
    """Write the counters of a run as markdown (no user ids). Returns the path."""
    mode = "dry" if report.dry_run else "run"
    path = report_dir / f"promotion-pass-{report.db}-{mode}-{run_stamp}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    changed_label = "Would change" if report.dry_run else "Changed"
    listed = ", ".join(f"({g}, {p})" for g, p in report.sample_mismatch_rows) or "none"
    undo = str(report.undo_log) if report.undo_log is not None else "none (dry run)"
    lines = [
        f"# Promotion pass ({mode}) on {report.db}",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Stopped early:** {report.stopped_early}",
        "",
        "## Counters",
        "",
        f"- Candidates: {report.candidates}",
        f"- {changed_label}: {report.changed}",
        f"- Loss up / down: {report.loss_up} / {report.loss_down}",
        f"- Missed up / down: {report.missed_up} / {report.missed_down}",
        f"- NULL to value / value to NULL: {report.null_to_value} / {report.value_to_null}",
        f"- Type missed win to allowed loss: {report.type_missed_to_allowed}",
        f"- Type allowed loss to missed win: {report.type_allowed_to_missed}",
        f"- Board failures (ply not reached or fen mismatch): {report.board_failures}",
        f"- Guard misses (row rewritten between read and write): {report.guard_misses}",
        f"- Sample checked / mismatches: {report.sample_checked} / {report.sample_mismatches}",
        f"- Sample mismatches listed (game_id, ply): {listed}",
        f"- Pages: {report.pages}",
        f"- Elapsed: {report.elapsed_s:.1f} s",
        "",
        "## Rule",
        "",
        "D-01: a promotion credits the promoting side with the promoted piece minus the pawn "
        "(queen 8, rook 4, bishop or knight 2), a promotion with capture adds the captured piece; "
        "per-depth caps unchanged (D-02).",
        "",
        "## Filter",
        "",
        "D-07: blunders (severity 2, both sides) of line-stamped games with a promotion token in "
        "the refutation line (pv at ply + 1), the best line (pv or best_move at the flaw ply) or "
        "the played move (move_san contains '='). Stored-NULL rows included.",
        "",
        "## Comparison",
        "",
        "A row changes only when the recomputed pair, rounded to a 4-byte float, differs from the "
        "stored REAL pair. The write is a guarded UPDATE on the values read.",
        "",
        f"Undo log: {undo}",
        "",
    ]
    path.write_text("\n".join(lines))
    return path


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


async def _fetch_page(
    session: AsyncSession, *, after: tuple[int, int, int] | None, limit: int, user_id: int | None
) -> list[CandidateRow]:
    result = await session.execute(candidate_page_stmt(after=after, limit=limit, user_id=user_id))
    return [CandidateRow(*row) for row in result.all()]


async def _recompute_page(
    session: AsyncSession, rows: Sequence[CandidateRow]
) -> tuple[list[RowChange], int]:
    """Replay the rows' games (one PGN query per page) and return the changes and board failures."""
    game_ids = {r.game_id for r in rows}
    pgn_by_game = {
        game_id: pgn
        for game_id, pgn in (
            await session.execute(select(Game.id, Game.pgn).where(Game.id.in_(game_ids)))
        ).all()
    }
    rows_by_game: dict[int, list[CandidateRow]] = {}
    for row in rows:
        rows_by_game.setdefault(row.game_id, []).append(row)
    changes: list[RowChange] = []
    failures = 0
    for game_id, game_rows in rows_by_game.items():
        inputs, game_failures = replay_inputs(pgn_by_game[game_id], game_rows)
        failures += game_failures
        for row in game_rows:
            change = classify_change(row, inputs[row.ply]) if row.ply in inputs else None
            if change is not None:
                changes.append(change)
    changes.sort(key=lambda c: (c.row.user_id, c.row.game_id, c.row.ply))
    return changes, failures


async def _write_page(
    session: AsyncSession, changes: Sequence[RowChange]
) -> tuple[list[RowChange], int]:
    """Guarded UPDATE of each change. Returns (applied, guard_misses); the caller commits."""
    applied: list[RowChange] = []
    misses = 0
    for change in changes:
        row = change.row
        result = await session.execute(
            update(GameFlaw)
            .where(
                GameFlaw.user_id == row.user_id,
                GameFlaw.game_id == row.game_id,
                GameFlaw.ply == row.ply,
                GameFlaw.material_loss.is_not_distinct_from(row.stored_loss),
                GameFlaw.material_missed.is_not_distinct_from(row.stored_missed),
            )
            .values(material_loss=change.new_loss, material_missed=change.new_missed)
        )
        if result.rowcount == 0:  # ty: ignore[unresolved-attribute]  # CursorResult at runtime
            misses += 1
        else:
            applied.append(change)
    return applied, misses


def _format_undo_value(value: float | None) -> str:
    return UNDO_NULL if value is None else repr(value)


def _append_undo(path: Path, applied: Sequence[RowChange]) -> None:
    """Append the applied rows to the undo log (header on a new file) and flush to disk.

    Nothing applied means nothing to undo: the file is not created for an empty page.
    """
    if not applied:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists() or path.stat().st_size == 0
    with path.open("a") as handle:
        if is_new:
            handle.write(UNDO_LOG_HEADER + "\n")
        for change in applied:
            row = change.row
            fields = (
                str(row.user_id),
                str(row.game_id),
                str(row.ply),
                _format_undo_value(row.stored_loss),
                _format_undo_value(row.stored_missed),
                _format_undo_value(change.new_loss),
                _format_undo_value(change.new_missed),
            )
            handle.write("\t".join(fields) + "\n")
        handle.flush()


async def _process_page(
    session_maker: async_sessionmaker[AsyncSession],
    report: PassReport,
    *,
    after: tuple[int, int, int] | None,
    limit: int,
    user_id: int | None,
    undo_log: Path | None,
) -> list[CandidateRow]:
    """Fetch, recompute and (real run) write one page. An empty list means no more pages.

    A page is all or nothing: an error is captured with context and re-raised before the commit,
    so the re-run resumes from the stored state.
    """
    rows: list[CandidateRow] = []
    async with session_maker() as session:
        try:
            rows = await _fetch_page(session, after=after, limit=limit, user_id=user_id)
            if not rows:
                return []
            changes, failures = await _recompute_page(session, rows)
            report.candidates += len(rows)
            report.board_failures += failures
            if undo_log is None:
                for change in changes:
                    _tally(report, change)
                return rows
            applied, misses = await _write_page(session, changes)
            await session.commit()
            report.guard_misses += misses
            _append_undo(undo_log, applied)
            for change in applied:
                _tally(report, change)
            return rows
        except Exception as exc:
            # Ids go to Sentry context, never the message (grouping, CLAUDE.md).
            context: dict[str, int] = {"page": report.pages + 1}
            if rows:
                context["last_game_id"] = rows[-1].game_id
                context["last_ply"] = rows[-1].ply
            sentry_sdk.set_context("promotion_pass", context)
            sentry_sdk.capture_exception(exc)
            raise


async def _sample_check(
    session_maker: async_sessionmaker[AsyncSession],
    report: PassReport,
    *,
    size: int,
    modulus: int,
    user_id: int | None,
) -> None:
    """D-07: blunders without a promotion token must replay to their stored pair."""
    async with session_maker() as session:
        result = await session.execute(_sample_stmt(size=size, modulus=modulus, user_id=user_id))
        rows = [CandidateRow(*row) for row in result.all()]
        if not rows:
            return
        changes, failures = await _recompute_page(session, rows)
    report.sample_checked = len(rows) - failures
    report.sample_mismatches = len(changes)
    report.sample_mismatch_rows = [
        (c.row.game_id, c.row.ply) for c in changes[:SAMPLE_MISMATCHES_LISTED]
    ]


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def _install_signal_handlers() -> None:
    """Cooperative SIGINT / SIGTERM: finish the current page, write the report, exit."""
    global _stop_requested
    _stop_requested = False

    def _request_stop(signum: int, _frame: object) -> None:
        global _stop_requested
        _log(f"signal {signum} received, stopping after this page")
        _stop_requested = True

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)


def _page_limit(limit: int | None, seen: int) -> int:
    """Rows to fetch for the next page (0 when the --limit is used up)."""
    if limit is None:
        return FLAWS_PER_BATCH
    return max(0, min(FLAWS_PER_BATCH, limit - seen))


async def _run_pages(
    session_maker: async_sessionmaker[AsyncSession],
    report: PassReport,
    *,
    user_id: int | None,
    limit: int | None,
    throttle_ms: int,
) -> None:
    after: tuple[int, int, int] | None = None
    while not _stop_requested:
        page_limit = _page_limit(limit, report.candidates)
        if page_limit == 0:
            break
        rows = await _process_page(
            session_maker,
            report,
            after=after,
            limit=page_limit,
            user_id=user_id,
            undo_log=report.undo_log,
        )
        if not rows:
            break
        report.pages += 1
        after = (rows[-1].user_id, rows[-1].game_id, rows[-1].ply)
        label = "would change" if report.dry_run else "changed"
        _log(
            f"Page {report.pages}: {len(rows)} candidates, {report.changed} {label} so far, "
            f"{report.guard_misses} guard misses, {report.board_failures} board failures"
        )
        # Pace the writes on a live DB; a dry run only reads.
        if throttle_ms and not report.dry_run:
            await asyncio.sleep(throttle_ms / 1000)
    report.stopped_early = _stop_requested


async def run_pass(
    *,
    db: TargetDb,
    dry_run: bool,
    user_id: int | None = None,
    limit: int | None = None,
    throttle_ms: int = 0,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    sample_game_modulus: int = SAMPLE_GAME_MODULUS,
    report_dir: Path = DEFAULT_REPORT_DIR,
    undo_log: Path | None = None,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> PassReport:
    """One pass over the promotion candidates. A dry run reads only and also checks the sample.

    `session_maker` is injectable for tests; otherwise the engine comes from `db_url_for_target`
    (one connection; read-only with a statement timeout for a dry run). The URL is never printed.
    """
    started = time.monotonic()
    run_stamp = datetime.now(timezone.utc).strftime(REPORT_STAMP_FORMAT)
    report = PassReport(db=db, dry_run=dry_run)
    if not dry_run:
        report.undo_log = undo_log or DEFAULT_UNDO_DIR / f"undo-{db}-{run_stamp}.tsv"
    engine = None
    if session_maker is None:
        url = db_url_for_target(db)
        engine = (
            make_readonly_engine(url)
            if dry_run
            else create_async_engine(url, pool_size=1, max_overflow=0, pool_pre_ping=True)
        )
        session_maker = async_sessionmaker(engine, expire_on_commit=False)
    _log(f"Promotion pass on {db}: {'dry run (read-only)' if dry_run else 'write'}")
    try:
        await _run_pages(
            session_maker, report, user_id=user_id, limit=limit, throttle_ms=throttle_ms
        )
        if dry_run:
            await _sample_check(
                session_maker,
                report,
                size=sample_size,
                modulus=sample_game_modulus,
                user_id=user_id,
            )
    finally:
        if engine is not None:
            await engine.dispose()
    report.elapsed_s = time.monotonic() - started
    report.report_path = write_report(report, report_dir=report_dir, run_stamp=run_stamp)
    _log(
        f"Done: {report.candidates} candidates, {report.changed} "
        f"{'would change' if dry_run else 'changed'}, sample mismatches {report.sample_mismatches}"
    )
    _log(f"Report: {report.report_path}")
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recompute the stored facepalm material inputs of promotion rows (262 D-06, D-07)."
    )
    parser.add_argument("--db", choices=["dev", "prod"], required=True, help="DB target.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Read only: report the rows that would change and check a non-token sample (exit 3 on a mismatch).",
    )
    parser.add_argument(
        "--user-id", type=int, default=None, dest="user_id", help="Only this user's flaws."
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Process at most this many candidate rows."
    )
    parser.add_argument(
        "--throttle-ms",
        type=int,
        default=0,
        dest="throttle_ms",
        help="Sleep this long after each page commit (writes only).",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        dest="sample_size",
        help="Dry-run sample of blunders without a promotion token.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        dest="report_dir",
        help=f"Report directory (default {DEFAULT_REPORT_DIR}).",
    )
    parser.add_argument(
        "--undo-log",
        type=Path,
        default=None,
        dest="undo_log",
        help=f"Undo log TSV for a real run (default {DEFAULT_UNDO_DIR}/undo-<db>-<stamp>.tsv).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the pass; returns the process exit code (3 = a dry run found a sample mismatch)."""
    args = _parse_args(argv)
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
    _install_signal_handlers()
    db: TargetDb = args.db
    report = asyncio.run(
        run_pass(
            db=db,
            dry_run=args.dry_run,
            user_id=args.user_id,
            limit=args.limit,
            throttle_ms=args.throttle_ms,
            sample_size=args.sample_size,
            report_dir=args.report_dir,
            undo_log=args.undo_log,
        )
    )
    return exit_code_for(report, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
