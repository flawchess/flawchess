"""Phase 262 owner checkpoint: what the refit does to a prod sample (read-only).

Scores a deterministic sample of games (``games.id % mod == 0``) under two versions of the
facepalm score and reports the shift:

* shipped (Phase 259): the stored material inputs, the loss gate (the reply term on any loss above
  zero), the Phase 259 coefficients (``PHASE_259_COEFS``);
* candidate (Phase 262): promotion rows recomputed with the app's own material rule, the type gate
  (the reply term on an allowed loss only, ``is_allowed_loss``) and the app's current FACEPALM_*
  constants (at the checkpoint the orchestrator pastes the candidate constants into the working
  tree first, ``candidate_coefs``).

Successor of the discuss-phase spike probes, without their monkeypatch of the line rule (the rule is
in the app now, so the recompute uses it as it is) and with the 4-byte-float comparison of the
promotion pass (``as_real``): a row counts as recomputed only when its pair differs from the stored
REAL pair. The candidate rows are selected and replayed with the pass's own filter and replay
(``scripts.backfill_promotion_material``), so the checkpoint and the pass see the same rows.

The report holds aggregates and at most ``--spot-check`` game links for the spot check; user ids and
usernames are never selected into a report row or printed.

Read-only: one connection with a statement timeout (``make_readonly_engine``); for prod open the
tunnel with ``bin/prod_db_tunnel.sh`` first. The script holds exactly one connection because prod
``max_connections`` is 50.

Usage::

    uv run python scripts/blunder_check/refit_shift.py --db dev --mod 1 --out temp/promotion-pass/refit-shift-dev.md
    uv run python scripts/blunder_check/refit_shift.py --db prod --mod 10 --out <report.md>
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection

# Bootstrap project root so `app.*` and `scripts.*` imports resolve when running as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.core.config import db_url_for_target  # noqa: E402
from app.models.game import Game  # noqa: E402
from app.models.game_flaw import GameFlaw  # noqa: E402

# GameFlaw / Game carry FKs to users -> oauth_accounts; register the chain so select() compiles.
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.repositories.query_utils import mover_is_white_at_ply  # noqa: E402
from app.services import blunder_check_rules as rules  # noqa: E402
from app.services.facepalm_score import FacepalmType, facepalm_type_of  # noqa: E402
from scripts.backfill_promotion_material import (  # noqa: E402
    FLAWS_PER_BATCH,
    CandidateRow,
    as_real,
    candidate_page_stmt,
    replay_inputs,
)
from scripts.blunder_check.fit_facepalm import (  # noqa: E402
    D15_CUTS,
    FIT_SELECTION_THRESHOLD,
    GateName,
    ScalarCoefs,
    ScalarFitRow,
    scalar_score,
)
from scripts.blunder_check.sample import BLUNDER_SEVERITY, make_readonly_engine  # noqa: E402

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

# The model live on prod until the Phase 262 release (reports/blunder-check/facepalm-fit-2026-11-22.md),
# scored with the loss gate.
PHASE_259_COEFS: Final[ScalarCoefs] = ScalarCoefs(-1.4308, -0.6065, 0.8379, 0.4971, 2.0786, 0.9133)
SHIPPED_GATE: Final[GateName] = "loss"
CANDIDATE_GATE: Final[GateName] = "type"

DEFAULT_MOD: int = 10
DEFAULT_SPOT_CHECK: int = 20
DEFAULT_SEED: int = 262
DB_TARGETS: tuple[str, ...] = ("dev", "prod")
EXIT_OK: int = 0

# FlawChess analysis board; `?game_id=G&ply=N` opens game G at the flaw ply (as miss_labels.py).
ANALYSIS_URL_BASE: str = "https://flawchess.com/analysis"
TYPE_UNKNOWN: str = "unknown"
TYPE_KEYS: tuple[str, ...] = ("allowed_loss", "missed_win", TYPE_UNKNOWN)

RowKey = tuple[int, int]


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SampledBlunder:
    """One sampled blunder as stored: its key, the Maia probabilities and the stored material pair."""

    game_id: int
    ply: int
    is_own: bool
    played_prob: float | None
    best_prob: float | None
    reply_prob: float | None
    stored_loss: float | None
    stored_missed: float | None


@dataclass(frozen=True)
class ShiftRow:
    """One blunder scored under both versions. The pairs are the inputs each version reads."""

    game_id: int
    ply: int
    is_own: bool
    old_loss: float | None
    old_missed: float | None
    new_loss: float | None
    new_missed: float | None
    old_score: float | None
    new_score: float | None
    old_type: FacepalmType | None
    new_type: FacepalmType | None
    inputs_changed: bool


@dataclass(frozen=True)
class ShiftSummary:
    """Counts over the sample (raw; the report also shows them times `mod`)."""

    mod: int
    sampled: int
    passers_old: dict[float, int]
    passers_new: dict[float, int]
    enter_by_new_type: dict[str, int]
    enter_by_old_type: dict[str, int]
    leave_by_new_type: dict[str, int]
    leave_by_old_type: dict[str, int]
    own_passers_old: int
    own_passers_new: int
    lose_score: int
    gain_score: int
    gate_unscored: int
    inputs_changed: int


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def candidate_coefs() -> ScalarCoefs:
    """The coefficients the app holds now (the FACEPALM_* constants of blunder_check_rules)."""
    return ScalarCoefs(
        rules.FACEPALM_INTERCEPT,
        rules.FACEPALM_PLAYED_COEF,
        rules.FACEPALM_LOSS_COEF,
        rules.FACEPALM_MISSED_COEF,
        rules.FACEPALM_BEST_PROB_COEF,
        rules.FACEPALM_REPLY_PROB_COEF,
    )


def _fit_row(blunder: SampledBlunder, loss: float | None, missed: float | None) -> ScalarFitRow:
    """The features-table row of a blunder under the pair (loss, missed); NULL missed reads as 0."""
    return ScalarFitRow(
        n="",
        set_id="",
        label=None,
        played_prob=blunder.played_prob,
        reply_spread=None,
        best_prob=blunder.best_prob,
        reply_prob=blunder.reply_prob,
        loss=loss,
        missed=0.0 if missed is None else missed,
    )


def score_versions(
    blunder: SampledBlunder, recomputed: tuple[float | None, float | None] | None
) -> ShiftRow:
    """Score one blunder under the shipped and the candidate version.

    `recomputed` is the promotion-recomputed pair of a candidate row, or None for a row the pass
    does not touch (D-07: it replays to its stored pair). A recomputed pair equal to the stored pair
    in 4-byte float form is not a change (`as_real`).
    """
    stored = (blunder.stored_loss, blunder.stored_missed)
    new_pair = stored
    if recomputed is not None:
        candidate_pair = (as_real(recomputed[0]), as_real(recomputed[1]))
        if candidate_pair != stored:
            new_pair = candidate_pair
    old_row = _fit_row(blunder, *stored)
    new_row = _fit_row(blunder, *new_pair)
    return ShiftRow(
        game_id=blunder.game_id,
        ply=blunder.ply,
        is_own=blunder.is_own,
        old_loss=stored[0],
        old_missed=stored[1],
        new_loss=new_pair[0],
        new_missed=new_pair[1],
        old_score=scalar_score(old_row, PHASE_259_COEFS, SHIPPED_GATE),
        new_score=scalar_score(new_row, candidate_coefs(), CANDIDATE_GATE),
        old_type=facepalm_type_of(stored[0], old_row.missed),
        new_type=facepalm_type_of(new_pair[0], new_row.missed),
        inputs_changed=new_pair != stored,
    )


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def _passes(score: float | None, cut: float) -> bool:
    return score is not None and score >= cut


def _type_key(kind: FacepalmType | None) -> str:
    return TYPE_UNKNOWN if kind is None else kind


def _gate_unscored(row: ShiftRow) -> bool:
    """The candidate leaves a row with a settled loss unscored (its key-move probability is NULL)."""
    return row.new_loss is not None and row.new_score is None


def _cuts() -> tuple[float, ...]:
    return tuple(sorted({*D15_CUTS, FIT_SELECTION_THRESHOLD}))


def summarize(rows: Sequence[ShiftRow], *, mod: int) -> ShiftSummary:
    """Count passers per cut and version, enter / leave at the selection cut, own passers, score shifts."""
    cut = FIT_SELECTION_THRESHOLD
    enter_new = dict.fromkeys(TYPE_KEYS, 0)
    enter_old = dict.fromkeys(TYPE_KEYS, 0)
    leave_new = dict.fromkeys(TYPE_KEYS, 0)
    leave_old = dict.fromkeys(TYPE_KEYS, 0)
    for row in rows:
        old_pass, new_pass = _passes(row.old_score, cut), _passes(row.new_score, cut)
        if new_pass and not old_pass:
            enter_new[_type_key(row.new_type)] += 1
            enter_old[_type_key(row.old_type)] += 1
        elif old_pass and not new_pass:
            leave_new[_type_key(row.new_type)] += 1
            leave_old[_type_key(row.old_type)] += 1
    return ShiftSummary(
        mod=mod,
        sampled=len(rows),
        passers_old={c: sum(_passes(r.old_score, c) for r in rows) for c in _cuts()},
        passers_new={c: sum(_passes(r.new_score, c) for r in rows) for c in _cuts()},
        enter_by_new_type=enter_new,
        enter_by_old_type=enter_old,
        leave_by_new_type=leave_new,
        leave_by_old_type=leave_old,
        own_passers_old=sum(r.is_own and _passes(r.old_score, cut) for r in rows),
        own_passers_new=sum(r.is_own and _passes(r.new_score, cut) for r in rows),
        lose_score=sum(r.old_score is not None and r.new_score is None for r in rows),
        gain_score=sum(r.old_score is None and r.new_score is not None for r in rows),
        gate_unscored=sum(_gate_unscored(r) for r in rows),
        inputs_changed=sum(r.inputs_changed for r in rows),
    )


def pick_newly_passing(rows: Sequence[ShiftRow], n: int, seed: int) -> list[ShiftRow]:
    """A seeded sample of at most n rows that cross the selection cut upward (old below it or unscored)."""
    crossing = sorted(
        (
            r
            for r in rows
            if _passes(r.new_score, FIT_SELECTION_THRESHOLD)
            and not _passes(r.old_score, FIT_SELECTION_THRESHOLD)
        ),
        key=lambda r: (r.game_id, r.ply),
    )
    picked = random.Random(seed).sample(crossing, min(n, len(crossing)))
    return sorted(picked, key=lambda r: (r.game_id, r.ply))


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _scaled(count: int, mod: int) -> str:
    return f"{count} (x{mod} = {count * mod})"


def _coefs_line(coefs: ScalarCoefs) -> str:
    return ", ".join(
        f"{name.removeprefix('FACEPALM_')} {value:.4f}" for name, value in coefs.by_name().items()
    )


def _passer_lines(summary: ShiftSummary) -> list[str]:
    lines = ["| cut | shipped | candidate |", "|---|---|---|"]
    for cut in _cuts():
        lines.append(
            f"| {cut:.2f} | {_scaled(summary.passers_old[cut], summary.mod)} "
            f"| {_scaled(summary.passers_new[cut], summary.mod)} |"
        )
    return lines


def _movement_lines(summary: ShiftSummary) -> list[str]:
    lines = [
        "| type | enter (by candidate type) | enter (by shipped type) "
        "| leave (by candidate type) | leave (by shipped type) |",
        "|---|---|---|---|---|",
    ]
    for kind in TYPE_KEYS:
        lines.append(
            f"| {kind} | {_scaled(summary.enter_by_new_type[kind], summary.mod)} "
            f"| {_scaled(summary.enter_by_old_type[kind], summary.mod)} "
            f"| {_scaled(summary.leave_by_new_type[kind], summary.mod)} "
            f"| {_scaled(summary.leave_by_old_type[kind], summary.mod)} |"
        )
    total_enter = sum(summary.enter_by_new_type.values())
    total_leave = sum(summary.leave_by_new_type.values())
    lines.append(
        f"| total | {_scaled(total_enter, summary.mod)} | {_scaled(total_enter, summary.mod)} "
        f"| {_scaled(total_leave, summary.mod)} | {_scaled(total_leave, summary.mod)} |"
    )
    return lines


def _picked_lines(picked: Sequence[ShiftRow]) -> list[str]:
    if not picked:
        return ["No sampled row newly passes the cut."]
    lines = [
        "| link | own | type shipped / candidate | pair shipped | pair candidate "
        "| score shipped / candidate | moved by |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in picked:
        link = f"{ANALYSIS_URL_BASE}?game_id={row.game_id}&ply={row.ply}"
        moved_by = "promotion (inputs changed)" if row.inputs_changed else "gate and coefficients"
        lines.append(
            f"| {link} | {'yes' if row.is_own else 'no'} "
            f"| {_type_key(row.old_type)} / {_type_key(row.new_type)} "
            f"| {_fmt(row.old_loss)} / {_fmt(row.old_missed)} "
            f"| {_fmt(row.new_loss)} / {_fmt(row.new_missed)} "
            f"| {_fmt(row.old_score)} / {_fmt(row.new_score)} | {moved_by} |"
        )
    return lines


def render_report(
    summary: ShiftSummary, picked: Sequence[ShiftRow], *, target: str, seed: int, spot_check: int
) -> str:
    """The markdown report (aggregates and the spot-check links; no user ids or usernames)."""
    mod = summary.mod
    return "\n".join(
        [
            "# Facepalm refit shift (Phase 262 owner checkpoint)",
            "",
            f"Target: {target}. Sample: games with id % {mod} == 0, {summary.sampled} blunders "
            f"of line-stamped games with a played-move probability. Counts are raw sample counts "
            f"followed by the count times {mod}.",
            "",
            "## Versions",
            "",
            f"- shipped (Phase 259): {_coefs_line(PHASE_259_COEFS)}; gate {SHIPPED_GATE} "
            "(reply term on any loss above zero); stored inputs.",
            f"- candidate (Phase 262): {_coefs_line(candidate_coefs())}; gate {CANDIDATE_GATE} "
            "(reply term on an allowed loss); promotion rows recomputed with the app rule.",
            "",
            "## Passers at the D-15 cuts",
            "",
            *_passer_lines(summary),
            "",
            f"## Enter and leave at {FIT_SELECTION_THRESHOLD:.2f} by type",
            "",
            "A row enters when the candidate passes the cut and the shipped score did not; it "
            "leaves in the opposite case.",
            "",
            *_movement_lines(summary),
            "",
            f"## Own blunders at {FIT_SELECTION_THRESHOLD:.2f} (drill-pool proxy)",
            "",
            f"- shipped: {_scaled(summary.own_passers_old, mod)}",
            f"- candidate: {_scaled(summary.own_passers_new, mod)}",
            "",
            "## Scored and unscored rows",
            "",
            f"- rows whose inputs changed (a promotion): {_scaled(summary.inputs_changed, mod)}",
            f"- rows that lose a score (shipped scored, candidate not): {_scaled(summary.lose_score, mod)}",
            f"- rows that gain a score (shipped unscored, candidate scored): {_scaled(summary.gain_score, mod)}",
            "- rows the candidate gate leaves unscored with a settled loss (a NULL key-move "
            f"probability, D-04): {_scaled(summary.gate_unscored, mod)}",
            "",
            f"## Newly passing {FIT_SELECTION_THRESHOLD:.2f}",
            "",
            f"Seeded sample (seed {seed}) of at most {spot_check} rows that pass under the candidate "
            "and did not under the shipped version.",
            "",
            *_picked_lines(picked),
            "",
        ]
    )


# ---------------------------------------------------------------------------
# Database access (read-only)
# ---------------------------------------------------------------------------


async def _fetch_sampled(conn: AsyncConnection, mod: int) -> dict[RowKey, SampledBlunder]:
    """Every blunder of the sampled, line-stamped games that has a played-move probability."""
    result = await conn.execute(
        select(
            GameFlaw.game_id,
            GameFlaw.ply,
            GameFlaw.maia_played_prob,
            GameFlaw.material_loss,
            GameFlaw.material_missed,
            GameFlaw.maia_best_prob,
            GameFlaw.maia_best_reply_prob,
            Game.user_color,
        )
        .join(Game, Game.id == GameFlaw.game_id)
        .where(
            GameFlaw.severity == BLUNDER_SEVERITY,
            Game.facepalm_line_completed_at.is_not(None),
            GameFlaw.maia_played_prob.is_not(None),
            Game.id % mod == 0,
        )
        .order_by(GameFlaw.game_id, GameFlaw.ply)
    )
    sampled: dict[RowKey, SampledBlunder] = {}
    for game_id, ply, played, loss, missed, best, reply, user_color in result.all():
        sampled[(game_id, ply)] = SampledBlunder(
            game_id=game_id,
            ply=ply,
            is_own=mover_is_white_at_ply(ply) == (user_color == "white"),
            played_prob=played,
            best_prob=best,
            reply_prob=reply,
            stored_loss=loss,
            stored_missed=missed,
        )
    return sampled


async def _recompute_page(
    conn: AsyncConnection, rows: Sequence[CandidateRow]
) -> dict[RowKey, tuple[float | None, float | None]]:
    """Replay the rows' games (one PGN query per page) with the app rule; the recomputed pairs."""
    game_ids = {r.game_id for r in rows}
    pgn_by_game = {
        game_id: pgn
        for game_id, pgn in (
            await conn.execute(select(Game.id, Game.pgn).where(Game.id.in_(game_ids)))
        ).all()
    }
    rows_by_game: dict[int, list[CandidateRow]] = {}
    for row in rows:
        rows_by_game.setdefault(row.game_id, []).append(row)
    recomputed: dict[RowKey, tuple[float | None, float | None]] = {}
    for game_id, game_rows in rows_by_game.items():
        inputs, _failures = replay_inputs(pgn_by_game[game_id], game_rows)
        for ply, pair in inputs.items():
            recomputed[(game_id, ply)] = (pair.loss, pair.missed)
    return recomputed


async def _fetch_recomputed(
    conn: AsyncConnection, mod: int, sampled: dict[RowKey, SampledBlunder]
) -> dict[RowKey, tuple[float | None, float | None]]:
    """Recompute the promotion candidates of the sample, paged in the pass's keyset order."""
    recomputed: dict[RowKey, tuple[float | None, float | None]] = {}
    after: tuple[int, int, int] | None = None
    while True:
        stmt = candidate_page_stmt(after=after, limit=FLAWS_PER_BATCH, user_id=None).where(
            Game.id % mod == 0
        )
        page = [CandidateRow(*row) for row in (await conn.execute(stmt)).all()]
        if not page:
            return recomputed
        after = (page[-1].user_id, page[-1].game_id, page[-1].ply)
        wanted = [r for r in page if (r.game_id, r.ply) in sampled]
        if wanted:
            recomputed.update(await _recompute_page(conn, wanted))


async def fetch_rows(conn: AsyncConnection, mod: int) -> list[ShiftRow]:
    """The sample scored under both versions; ids stay internal to the rows, never to the report."""
    sampled = await _fetch_sampled(conn, mod)
    recomputed = await _fetch_recomputed(conn, mod, sampled)
    return [score_versions(blunder, recomputed.get(key)) for key, blunder in sampled.items()]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read-only comparison of the Phase 259 and the Phase 262 facepalm score."
    )
    parser.add_argument("--db", choices=DB_TARGETS, required=True, help="read-only source database")
    parser.add_argument(
        "--mod",
        type=int,
        default=DEFAULT_MOD,
        help=f"sample the games with id %% mod == 0 (default {DEFAULT_MOD}; 1 reads every game)",
    )
    parser.add_argument(
        "--spot-check",
        type=int,
        default=DEFAULT_SPOT_CHECK,
        dest="spot_check",
        help=f"rows listed in the newly-passing section (default {DEFAULT_SPOT_CHECK})",
    )
    parser.add_argument(
        "--seed", type=int, default=DEFAULT_SEED, help="seed of the spot-check pick"
    )
    parser.add_argument("--out", type=Path, default=None, help="also write the report here")
    args = parser.parse_args(argv)
    if args.mod < 1:
        parser.error("--mod must be at least 1")
    return args


async def _run(args: argparse.Namespace) -> int:
    engine = make_readonly_engine(db_url_for_target(args.db))
    try:
        async with engine.connect() as conn:
            rows = await fetch_rows(conn, args.mod)
    finally:
        await engine.dispose()
    summary = summarize(rows, mod=args.mod)
    picked = pick_newly_passing(rows, args.spot_check, args.seed)
    report = render_report(
        summary, picked, target=args.db, seed=args.seed, spot_check=args.spot_check
    )
    print(report)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report)
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(_run(_parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
