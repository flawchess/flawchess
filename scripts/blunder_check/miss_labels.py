"""Blind stratified miss sampler for the facepalm refit (Phase 254 D-14, D-15, D-16).

The 180 labels of the Phase 250 fit hold 17 no-loss rows, too few to learn missed gains. This
operator script draws about 50 user blunders from the database (about 40 pure misses spread over
the missed size and over how findable the best move was, about 10 mixed rows that both lose and
miss material), computes both line facts and the best-move probability locally, and writes

* a blind labelling sheet like ``reports/blunder-check/facepalm-labels.tsv`` (columns
  ``BLIND_COLUMNS``: n, set, elo, move, link and an empty label; never a score or any input), and
* a key file with the hidden inputs and the stratum of every row, under gitignored ``temp/``.

Candidates are user-side blunders of all users whose mover was rated below ``MAX_MOVER_RATING``
at game time (the population of the 180 existing labels, so the sets pool) whose stored best
line (``game_positions.pv`` at the flaw ply) and refutation line (``pv`` at ply + 1) each have at
least ``MIN_STABLE_LINE_PLIES`` plies or end in mate, so Phase 252's repair of 1-2 ply lines never
changes their features. Games already in the existing labels are excluded and the new rows get
set id ``MISS_SET_ID`` so the two sets pool in one fit.

Everything here only reads (``make_readonly_engine``: read-only transactions, statement timeout,
one connection). The analysis URLs are written to the sheet and never printed.

Usage::

    # dev (local database, the smoke run; dev holds few users, so lift the rating cap)
    uv run --group maia-inference python scripts/blunder_check/miss_labels.py --db dev \
        --sample-percent 100 --pure-misses 8 --mixed 2 --max-rating 3000 \
        --out temp/blunder-check/miss-labels-dev.tsv \
        --key-out temp/blunder-check/miss-labels-dev-key.json

    # prod (needs the tunnel: bin/prod_db_tunnel.sh; run from the orchestrator, not an executor)
    uv run --group maia-inference python scripts/blunder_check/miss_labels.py --db prod \
        --out temp/blunder-check/miss-labels.tsv

The owner labels the sheet blind (``label`` 1 = unfair / facepalm, 0 = fair, as in the 250
sheets); the labelled TSV is then passed to ``facepalm_features.py --labels`` next to the
existing label file.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from bisect import bisect_right
from collections import Counter
from collections.abc import Collection, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import chess
from sqlalchemy import Float, case, func, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.orm import aliased

# Bootstrap project root so `app.*` imports resolve when running as a script.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app.core.config import db_url_for_target  # noqa: E402

# Game.user_id has a FK to users.id and User declares a relationship to OAuthAccount, so the
# mapped classes must all be imported before any select() against them compiles.
from app.models.game import Game  # noqa: E402
from app.models.game_flaw import GameFlaw  # noqa: E402
from app.models.game_position import GamePosition  # noqa: E402
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
from app.repositories.query_utils import is_opponent_expr  # noqa: E402
from app.schemas.normalization import Platform, TimeControlBucket  # noqa: E402
from app.services import maia_engine  # noqa: E402
from app.services.best_move_candidates import pinned_elo_for_mover  # noqa: E402
from app.services.blunder_check_rules import LINE_DEPTH  # noqa: E402
from app.services.line_material import LineFacts, best_line_facts, line_facts  # noqa: E402
from app.services.maia_flaw_scoring import best_move_uci, replay_flaw_boards  # noqa: E402
from app.services.maia_flaw_stats import pre_blunder_spread  # noqa: E402
from app.services.normalization import is_correspondence_time_control  # noqa: E402
from scripts.blunder_check.facepalm_features import (  # noqa: E402
    DB_TARGETS,
    DEFAULT_MAIA_THREADS,
    EXIT_MAIA_UNAVAILABLE,
    EXIT_OK,
    PV_SEPARATOR,
    PolicyFn,
    parse_labels,
)
from scripts.blunder_check.metrics import MaterialType, material_type  # noqa: E402
from scripts.blunder_check.sample import CALIBRATION_PLATFORMS, make_readonly_engine  # noqa: E402

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

# Set id of the new labels; the 180 existing labels use 1-6 (D-16: the sets pool in one fit).
MISS_SET_ID: str = "7"
# D-14: about 40 pure misses (no loss, a missed gain) and about 10 mixed rows (loses and misses).
PURE_MISS_TARGET: int = 40
MIXED_TARGET: int = 10
# Missed-size buckets (pawn units, inclusive; None = open ended): D-14's sizes 1, 3, 5 and 9+.
# A best line that mates within LINE_DEPTH counts in the last bucket.
MISSED_SIZE_BUCKETS: tuple[tuple[int, int | None], ...] = ((1, 2), (3, 4), (5, 8), (9, None))
# Best-move probability terciles, cut at the pool's own distribution (low = hard to find).
BEST_PROB_TERTILES: int = 3
TERTILE_NAMES: tuple[str, ...] = ("hard", "mid", "easy")
# D-15: the population of the 180 existing labels (the mover's raw rating at game time).
MAX_MOVER_RATING: int = 2000
# D-15: Phase 252 only re-searches 1-2 ply lines, so a line of at least this many plies (or one
# that ends in mate) never changes its features.
MIN_STABLE_LINE_PLIES: int = 3
# Percent of games read (TABLESAMPLE SYSTEM) and its REPEATABLE seed.
DEFAULT_SAMPLE_PERCENT: float = 0.5
DEFAULT_SAMPLE_SEED: int = 254
# game_flaws.severity of a blunder (game_flaws_repository._SEVERITY_INT).
BLUNDER_SEVERITY: int = 2

# The blind sheet: same leading columns as facepalm-labels.tsv, value columns left out.
BLIND_COLUMNS: tuple[str, ...] = ("n", "set", "elo", "move", "link", "label")
LINK_TEMPLATE: str = "https://flawchess.com/analysis?game_id={game_id}&ply={ply}"
DEFAULT_EXCLUDE_LABELS: Path = Path("reports/blunder-check/facepalm-labels.tsv")
DEFAULT_KEY_OUT: Path = Path("temp/blunder-check/miss-labels-key.json")

# Material types the sheet draws from: pure misses and rows that both lose and miss.
PURE_TYPE: MaterialType = "misses"
MIXED_TYPE: MaterialType = "loses_and_misses"
MIXED_STRATUM: str = "mixed"

DROP_EXCLUDED: str = "excluded_game"
DROP_RATING: str = "rating"
DROP_PLY_UNREACHED: str = "ply_not_reached"
DROP_UNSTABLE: str = "unstable_line"
DROP_NO_POLICY: str = "no_policy"
DROP_BEST_OUTSIDE_POLICY: str = "best_move_outside_policy"


# ---------------------------------------------------------------------------
# Rows
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RawCandidate:
    """One user-side blunder as read from the database (no derived values)."""

    game_id: int
    ply: int
    pgn: str
    platform: str
    time_control_bucket: str | None
    time_control_str: str | None
    # The user's (= the blunderer's) raw rating at game time.
    mover_rating: int
    # Stored best line at the flaw ply (best move first) and refutation line at ply + 1.
    best_pv: str | None
    best_move: str | None
    refutation_pv: str | None


@dataclass(frozen=True, slots=True)
class MissCandidate:
    """A candidate with every derived value, ready to stratify and write.

    `played_3` / `best_3` are the signed material (positive = the blunderer is up) after
    LINE_DEPTH plies of the played / best line; `missed` is the gain the best line has over what
    the played line kept (None when only a best-line mate makes it a miss).
    """

    game_id: int
    ply: int
    mover_rating: int
    move_san: str
    pinned_elo: float
    played_3: int | None
    best_3: int | None
    missed: int | None
    played_mate_ply: int | None
    best_mate_ply: int | None
    best_prob: float
    pre_spread: float
    material: MaterialType


@dataclass(frozen=True, slots=True)
class Selected:
    """A chosen row and the stratum it was drawn for."""

    candidate: MissCandidate
    stratum: str


@dataclass(frozen=True, slots=True)
class Stratified:
    """The chosen rows (shuffled, so the order does not reveal the stratum) and what fell short."""

    rows: list[Selected]
    # Cell label -> rows the cell's own supply could not give (borrowed or unfilled).
    shortfall: dict[str, int]
    unfilled_pure: int
    unfilled_mixed: int


@dataclass
class Tally:
    """What the pipeline saw, for the summary line."""

    read: int = 0
    stable: int = 0
    dropped: Counter[str] = field(default_factory=Counter)
    by_type: Counter[str] = field(default_factory=Counter)


# ---------------------------------------------------------------------------
# Filters (D-15, D-16)
# ---------------------------------------------------------------------------


def is_stable_line(pv: str | None, *, ends_in_mate: bool = False) -> bool:
    """Whether Phase 252 will never change a stored line: long enough, or ended by a mate.

    `pv` is the stored line as the space separated UCI tokens; `ends_in_mate` says the replayed
    line reaches a checkmate (a short mate-ended line is complete, not truncated).
    """
    if not pv:
        return False
    return ends_in_mate or len(pv.split(PV_SEPARATOR)) >= MIN_STABLE_LINE_PLIES


def _line_ends_in_mate(facts: LineFacts) -> bool:
    return facts.mate_ply is not None or facts.opponent_mate_ply is not None


def prefilter_reason(
    raw: RawCandidate, excluded_games: Collection[int], max_rating: int
) -> str | None:
    """Why `raw` is dropped before any replay (excluded game, mover rated too high), else None."""
    if raw.game_id in excluded_games:
        return DROP_EXCLUDED
    if raw.mover_rating >= max_rating:
        return DROP_RATING
    return None


# ---------------------------------------------------------------------------
# Pipeline: raw row -> MissCandidate
# ---------------------------------------------------------------------------


def _missed_gain(played_3: int | None, best_3: int | None) -> int | None:
    """What the best line gains beyond what the played line kept (None when either is unsettled)."""
    if played_3 is None or best_3 is None:
        return None
    return best_3 - max(0, played_3)


def _pinned_elo(raw: RawCandidate) -> float:
    return pinned_elo_for_mover(
        raw_rating=raw.mover_rating,
        platform=cast(Platform, raw.platform),
        time_control_bucket=cast(TimeControlBucket | None, raw.time_control_bucket),
        is_correspondence=is_correspondence_time_control(raw.time_control_str),
    )


def _pre_inputs(
    pre_board: chess.Board, best_uci: str | None, pinned_elo: float, policy_fn: PolicyFn
) -> tuple[float, float] | str:
    """(best_prob, pre_spread) from ONE policy call on the pre-blunder board, else a drop reason."""
    policy = policy_fn(pre_board.fen(), pinned_elo)
    if not policy:
        return DROP_NO_POLICY
    best_prob = policy.get(best_uci) if best_uci else None
    if best_prob is None:
        return DROP_BEST_OUTSIDE_POLICY
    return best_prob, pre_blunder_spread(policy)


def build_candidate(
    raw: RawCandidate,
    pre_board: chess.Board,
    played_uci: str,
    policy_fn: PolicyFn,
    tally: Tally,
) -> MissCandidate | None:
    """The derived values of one blunder, or None when it is dropped or not a sampled type.

    `pre_board` is the position before the blunder (never mutated) and `played_uci` the blunder.
    Both stored lines must be stable (D-15); the material type is counted in `tally`; only pure
    misses and mixed rows reach the Maia policy call.
    """
    facts = line_facts(pre_board, played_uci, raw.refutation_pv)
    best_facts = best_line_facts(pre_board, raw.best_pv)
    stable = is_stable_line(
        raw.refutation_pv, ends_in_mate=_line_ends_in_mate(facts)
    ) and is_stable_line(raw.best_pv, ends_in_mate=_line_ends_in_mate(best_facts))
    if not stable:
        tally.dropped[DROP_UNSTABLE] += 1
        return None
    tally.stable += 1
    played_3, best_3 = facts.material_at(LINE_DEPTH), best_facts.material_at(LINE_DEPTH)
    kind = material_type(played_3, facts.mate_ply, best_3, best_facts.opponent_mate_ply)
    tally.by_type[kind] += 1
    if kind not in (PURE_TYPE, MIXED_TYPE):
        return None
    pinned_elo = _pinned_elo(raw)
    inputs = _pre_inputs(
        pre_board, best_move_uci(raw.best_pv, raw.best_move), pinned_elo, policy_fn
    )
    if isinstance(inputs, str):
        tally.dropped[inputs] += 1
        return None
    return MissCandidate(
        game_id=raw.game_id,
        ply=raw.ply,
        mover_rating=raw.mover_rating,
        move_san=pre_board.san(chess.Move.from_uci(played_uci)),
        pinned_elo=pinned_elo,
        played_3=played_3,
        best_3=best_3,
        missed=_missed_gain(played_3, best_3),
        played_mate_ply=facts.mate_ply,
        best_mate_ply=best_facts.opponent_mate_ply,
        best_prob=inputs[0],
        pre_spread=inputs[1],
        material=kind,
    )


def collect_candidates(
    rows: Sequence[RawCandidate],
    *,
    excluded_games: Collection[int],
    max_rating: int,
    policy_fn: PolicyFn,
    tally: Tally,
) -> list[MissCandidate]:
    """Filter, replay and derive every raw row; the result is sorted by (game_id, ply)."""
    candidates: list[MissCandidate] = []
    for raw in rows:
        tally.read += 1
        reason = prefilter_reason(raw, excluded_games, max_rating)
        if reason is not None:
            tally.dropped[reason] += 1
            continue
        boards, _reason = replay_flaw_boards(raw.pgn, [raw.ply])
        if raw.ply not in boards:
            tally.dropped[DROP_PLY_UNREACHED] += 1
            continue
        pre_board, played_uci = boards[raw.ply]
        candidate = build_candidate(raw, pre_board, played_uci, policy_fn, tally)
        if candidate is not None:
            candidates.append(candidate)
    return sorted(candidates, key=lambda c: (c.game_id, c.ply))


# ---------------------------------------------------------------------------
# Stratification (D-14)
# ---------------------------------------------------------------------------


def missed_size_bucket(missed: int | None, best_mate_ply: int | None) -> int:
    """Index into MISSED_SIZE_BUCKETS; a best-line mate within LINE_DEPTH counts in the last one."""
    if best_mate_ply is not None and best_mate_ply <= LINE_DEPTH:
        return len(MISSED_SIZE_BUCKETS) - 1
    if missed is None:
        raise ValueError("a miss needs a missed gain or a best-line mate")
    for index, (low, high) in enumerate(MISSED_SIZE_BUCKETS):
        if missed >= low and (high is None or missed <= high):
            return index
    raise ValueError("missed gain below the smallest bucket")


def tertile_cuts(best_probs: Sequence[float]) -> tuple[float, ...]:
    """The BEST_PROB_TERTILES - 1 cut points of a best-move probability pool (empty pool: none)."""
    ordered = sorted(best_probs)
    if not ordered:
        return ()
    return tuple(
        ordered[len(ordered) * k // BEST_PROB_TERTILES] for k in range(1, BEST_PROB_TERTILES)
    )


def best_prob_tertile(best_prob: float, cuts: Sequence[float]) -> int:
    """0 = hard to find ... BEST_PROB_TERTILES - 1 = easy; a value on a cut goes to the upper one."""
    return bisect_right(cuts, best_prob)


Cell = tuple[int, int]  # (missed-size bucket index, best-move tertile)


def _bucket_text(bucket_index: int) -> str:
    low, high = MISSED_SIZE_BUCKETS[bucket_index]
    if high is None:
        return f"{low}+"
    return f"{low}-{high}"


def cell_label(cell: Cell) -> str:
    """Human readable stratum of a cell, e.g. "3-4 / hard"."""
    bucket_index, tertile = cell
    return f"{_bucket_text(bucket_index)} / {TERTILE_NAMES[tertile]}"


def _all_cells() -> list[Cell]:
    return [
        (bucket_index, tertile)
        for bucket_index in range(len(MISSED_SIZE_BUCKETS))
        for tertile in range(BEST_PROB_TERTILES)
    ]


def _group_cells(
    pure: Sequence[MissCandidate], rng: random.Random
) -> dict[Cell, list[MissCandidate]]:
    """The pure misses grouped by cell (every cell present), each cell's rows shuffled."""
    cuts = tertile_cuts([c.best_prob for c in pure])
    cells: dict[Cell, list[MissCandidate]] = {cell: [] for cell in _all_cells()}
    for candidate in pure:
        bucket_index = missed_size_bucket(candidate.missed, candidate.best_mate_ply)
        cells[(bucket_index, best_prob_tertile(candidate.best_prob, cuts))].append(candidate)
    for cell in cells:
        rng.shuffle(cells[cell])
    return cells


def _cell_quotas(
    cells: dict[Cell, list[MissCandidate]], target: int, rng: random.Random
) -> dict[Cell, int]:
    """target spread over the cells: the base share each, the remainder on cells with supply."""
    base, extra = divmod(target, len(cells))
    quotas = dict.fromkeys(cells, base)
    with_spare = [cell for cell, rows in cells.items() if len(rows) > base]
    others = [cell for cell in cells if cell not in with_spare]
    first = min(extra, len(with_spare))
    for cell in rng.sample(with_spare, first):
        quotas[cell] += 1
    for cell in rng.sample(others, extra - first):
        quotas[cell] += 1
    return quotas


def _borrow(cell: Cell, missing: int, spare: dict[Cell, list[MissCandidate]]) -> list[Selected]:
    """Up to `missing` rows from the other cells of the same size bucket, nearest tertile first."""
    bucket_index, tertile = cell
    neighbours = sorted(
        (other for other in spare if other[0] == bucket_index and other != cell),
        key=lambda other: (abs(other[1] - tertile), other[1]),
    )
    borrowed: list[Selected] = []
    for other in neighbours:
        while len(borrowed) < missing and spare[other]:
            borrowed.append(Selected(spare[other].pop(0), cell_label(other)))
    return borrowed


def _fill_cells(
    cells: dict[Cell, list[MissCandidate]], target: int, rng: random.Random
) -> tuple[list[Selected], dict[str, int], int]:
    """(chosen rows, shortfall per cell label, rows still unfilled) for the pure misses."""
    quotas = _cell_quotas(cells, target, rng)
    chosen: list[Selected] = []
    spare: dict[Cell, list[MissCandidate]] = {}
    missing: dict[Cell, int] = {}
    for cell, rows in cells.items():
        quota = quotas[cell]
        chosen.extend(Selected(candidate, cell_label(cell)) for candidate in rows[:quota])
        spare[cell] = rows[quota:]
        missing[cell] = max(0, quota - len(rows))
    shortfall = {cell_label(cell): count for cell, count in missing.items() if count}
    unfilled = 0
    for cell, count in missing.items():
        borrowed = _borrow(cell, count, spare)
        chosen.extend(borrowed)
        unfilled += count - len(borrowed)
    return chosen, shortfall, unfilled


def stratify(
    candidates: Sequence[MissCandidate], *, pure_target: int, mixed_target: int, seed: int
) -> Stratified:
    """Pick the rows of the sheet (D-14), deterministic given the seed and the pool.

    The pure misses fill MISSED_SIZE_BUCKETS x BEST_PROB_TERTILES cells (the tertile cuts come from
    the pool's own best-move probabilities, so easy and hard misses are both present) with
    `pure_target` // cells each, the remainder on cells that have supply. A cell that cannot fill
    its quota takes rows from the nearest other cell of its own size bucket; what it could not
    supply itself is reported in `shortfall` and what no cell of the bucket could give in
    `unfilled_pure`, never silently. `mixed_target` mixed rows are drawn without strata.
    """
    rng = random.Random(seed)
    # Sorted first so the draw depends on the pool, never on the order it arrived in.
    ordered = sorted(candidates, key=lambda c: (c.game_id, c.ply))
    pure = [c for c in ordered if c.material == PURE_TYPE]
    mixed = [c for c in ordered if c.material == MIXED_TYPE]
    rows, shortfall, unfilled_pure = _fill_cells(_group_cells(pure, rng), pure_target, rng)
    mixed_taken = rng.sample(mixed, min(mixed_target, len(mixed)))
    rows.extend(Selected(candidate, MIXED_STRATUM) for candidate in mixed_taken)
    # The sheet order must not reveal the stratum.
    rng.shuffle(rows)
    return Stratified(
        rows=rows,
        shortfall=shortfall,
        unfilled_pure=unfilled_pure,
        unfilled_mixed=mixed_target - len(mixed_taken),
    )


# ---------------------------------------------------------------------------
# Output: the blind sheet and the key file
# ---------------------------------------------------------------------------


def blind_row(n: int, row: Selected) -> list[str]:
    """The cells of one sheet row in BLIND_COLUMNS order (the label cell is empty)."""
    candidate = row.candidate
    return [
        str(n),
        MISS_SET_ID,
        str(candidate.mover_rating),
        candidate.move_san,
        LINK_TEMPLATE.format(game_id=candidate.game_id, ply=candidate.ply),
        "",
    ]


def write_blind_tsv(rows: Sequence[Selected], path: Path) -> None:
    """Write the blind sheet: header, then one line per row numbered 1..N in the given order."""
    lines = ["\t".join(BLIND_COLUMNS)]
    lines.extend("\t".join(blind_row(n, row)) for n, row in enumerate(rows, start=1))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def write_key(rows: Sequence[Selected], path: Path) -> None:
    """Write the key file: n -> the hidden inputs, the material type and the stratum."""
    key = {
        str(n): {
            "game_id": row.candidate.game_id,
            "ply": row.candidate.ply,
            "played_3": row.candidate.played_3,
            "best_3": row.candidate.best_3,
            "missed": row.candidate.missed,
            "best_prob": row.candidate.best_prob,
            "pre_spread": row.candidate.pre_spread,
            "material_type": row.candidate.material,
            "stratum": row.stratum,
        }
        for n, row in enumerate(rows, start=1)
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(key, indent=2) + "\n")


def summary_line(tally: Tally, result: Stratified) -> str:
    """One line: rows read, dropped and stable, per material type, rows written, shortfall."""
    by_type = ", ".join(f"{name} {count}" for name, count in sorted(tally.by_type.items()))
    dropped = ", ".join(f"{name} {count}" for name, count in sorted(tally.dropped.items()))
    written = Counter(row.stratum for row in result.rows)
    per_stratum = ", ".join(f"{name} {count}" for name, count in sorted(written.items()))
    shortfall = ", ".join(f"{name} {count}" for name, count in sorted(result.shortfall.items()))
    return (
        f"candidates read {tally.read}; dropped: {dropped or 'none'}; stable {tally.stable}; "
        f"by material type: {by_type or 'none'}; rows written {len(result.rows)} "
        f"({per_stratum or 'none'}); shortfall: {shortfall or 'none'}; "
        f"unfilled pure {result.unfilled_pure}, mixed {result.unfilled_mixed}"
    )


# ---------------------------------------------------------------------------
# Database (read-only)
# ---------------------------------------------------------------------------


async def read_raw_candidates(
    conn: AsyncConnection, *, sample_percent: float, seed: int, max_rating: int
) -> list[RawCandidate]:
    """User-side blunders of a TABLESAMPLE of games, with both stored lines and the mover rating.

    The mover is the user (user-side blunders only), so the rating is the user's rating of the
    game. Rows without a stored best line or refutation line are left out in SQL; every other
    filter (stability, excluded games) runs in Python where it can be tested.
    """
    sampled = aliased(
        Game,
        Game.__table__.tablesample(
            func.system(sql_cast(sample_percent, Float)), seed=sql_cast(seed, Float)
        ),
    )
    best = aliased(GamePosition)
    refutation = aliased(GamePosition)
    mover_rating = case(
        (sampled.user_color == "white", sampled.white_rating), else_=sampled.black_rating
    )
    stmt = (
        select(
            sampled.id,
            GameFlaw.ply,
            sampled.pgn,
            sampled.platform,
            sampled.time_control_bucket,
            sampled.time_control_str,
            mover_rating,
            best.pv,
            best.best_move,
            refutation.pv,
        )
        .select_from(sampled)
        .join(
            GameFlaw,
            (GameFlaw.game_id == sampled.id) & (GameFlaw.user_id == sampled.user_id),
        )
        .join(
            best,
            (best.user_id == GameFlaw.user_id)
            & (best.game_id == GameFlaw.game_id)
            & (best.ply == GameFlaw.ply),
        )
        .join(
            refutation,
            (refutation.user_id == GameFlaw.user_id)
            & (refutation.game_id == GameFlaw.game_id)
            & (refutation.ply == GameFlaw.ply + 1),
        )
        .where(
            GameFlaw.severity == BLUNDER_SEVERITY,
            ~is_opponent_expr(GameFlaw.ply, sampled.user_color),
            sampled.platform.in_(CALIBRATION_PLATFORMS),
            best.pv.isnot(None),
            refutation.pv.isnot(None),
            mover_rating < max_rating,
        )
        .order_by(sampled.id, GameFlaw.ply)
    )
    return [
        RawCandidate(
            game_id=row[0],
            ply=row[1],
            pgn=row[2],
            platform=row[3],
            time_control_bucket=row[4],
            time_control_str=row[5],
            mover_rating=row[6],
            best_pv=row[7],
            best_move=row[8],
            refutation_pv=row[9],
        )
        for row in (await conn.execute(stmt)).all()
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Blind stratified miss sampler (D-14, D-15).")
    parser.add_argument("--db", choices=DB_TARGETS, required=True, help="read-only source database")
    parser.add_argument(
        "--out", type=Path, required=True, help="blind labelling sheet TSV to write"
    )
    parser.add_argument(
        "--key-out",
        type=Path,
        default=DEFAULT_KEY_OUT,
        help="key file with the hidden inputs (keep under gitignored temp/)",
    )
    parser.add_argument(
        "--exclude-labels",
        type=Path,
        action="append",
        default=None,
        help="label TSV whose games are excluded; repeatable (default: the 180 existing labels)",
    )
    parser.add_argument("--sample-percent", type=float, default=DEFAULT_SAMPLE_PERCENT)
    parser.add_argument("--seed", type=int, default=DEFAULT_SAMPLE_SEED)
    parser.add_argument("--pure-misses", type=int, default=PURE_MISS_TARGET)
    parser.add_argument("--mixed", type=int, default=MIXED_TARGET)
    parser.add_argument("--max-rating", type=int, default=MAX_MOVER_RATING)
    parser.add_argument("--maia-threads", type=int, default=DEFAULT_MAIA_THREADS)
    return parser.parse_args(argv)


def excluded_game_ids(paths: Sequence[Path]) -> set[int]:
    """The game ids of every label TSV in `paths` (D-16: games already labelled are excluded)."""
    return {row.game_id for path in paths for row in parse_labels(path)}


async def _run(args: argparse.Namespace) -> int:
    excluded = excluded_game_ids(args.exclude_labels or [DEFAULT_EXCLUDE_LABELS])
    await maia_engine.start_maia(intra_op_num_threads=args.maia_threads)
    if not maia_engine.is_maia_available():
        print("Maia is unavailable (uv sync --group maia-inference?)", file=sys.stderr)
        return EXIT_MAIA_UNAVAILABLE
    engine = make_readonly_engine(db_url_for_target(args.db))
    try:
        async with engine.connect() as conn:
            raw_rows = await read_raw_candidates(
                conn,
                sample_percent=args.sample_percent,
                seed=args.seed,
                max_rating=args.max_rating,
            )
    finally:
        await engine.dispose()
    tally = Tally()
    candidates = collect_candidates(
        raw_rows,
        excluded_games=excluded,
        max_rating=args.max_rating,
        policy_fn=maia_engine.full_policy,
        tally=tally,
    )
    result = stratify(
        candidates, pure_target=args.pure_misses, mixed_target=args.mixed, seed=args.seed
    )
    write_blind_tsv(result.rows, args.out)
    write_key(result.rows, args.key_out)
    print(summary_line(tally, result))
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(_run(_parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
