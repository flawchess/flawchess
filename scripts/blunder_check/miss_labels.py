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

Line facts and the material type follow the quiet-point rule (Phase 259 D-02, D-03): the odd depths
come from ``quiet_line_facts`` / ``quiet_best_line_facts`` and the type is ``material_type_of`` on
the stored decaying-mean loss and missed gain (``material_inputs_from_facts``), the same inputs the
write-time hook stores. The sets labelled under the old depth-3 rule (7 and 8) are not redrawn.

Everything here only reads (``make_readonly_engine``: read-only transactions, statement timeout,
one connection). The analysis URLs are written to the sheet and never printed.

Set 8 (``--mode disagreement``, SEED-261115-agg, owner decision 2026-11-16)
---------------------------------------------------------------------------
The refit phase compares the shipped depth-3 input with a decaying mean over the odd depths
(1, 3, 5, 7, 9; weights 1, 1/2, 1/4, 1/8, 1/16; ``decaying_mean.py``), and only a few of the 199
labels sit where the two disagree. This mode draws about 60 blind rows for those cases:

* the loss group (23 rows): the depth-3 loss and the decaying mean of the loss series differ by at
  least ``DISAGREEMENT_MIN_PAWNS`` (0.5); stratified into spike (a depth 3, 5 or 7 peak),
  early (nonzero at depth 1, 0 at depth 3), late (0 at depths 1 and 3, the loss appears at depth 5
  or later) and other, with that precedence;
* the miss group (22 rows): the played line loses nothing at any known odd depth and the missed
  gain disagrees the same way, same four strata (a loss row whose only disagreement is the gain
  is not drawn);
* about 15 plain depth-3 pure misses over set 7's size x best-move-tertile cells.

A short stratum borrows from its own group (``*_other`` first), and shortfall and unfilled rows
are reported, never padded across groups. The "other" strata are planner discretion (the owner
named spike, recovered by depth 3 and appears at depth 5+).

What qualifies, with the cap 5 and threshold 0.5 (weights sum 1.9375): a loss or gain of v at
depth 1 only qualifies from 1 pawn (gap v / 1.9375 = 0.52); a spike at depth 3 from 1 pawn
(gap 0.74 v); a value held from depth 5 on (late) from 3 pawns (gap 0.2258 v: 0.68 for a piece,
0.45 for 2 pawns, which does not qualify); a spike at depth 5 alone only from 4 pawns (gap
0.129 v), and a value that appears only at depth 7 or 9 never (at most 0.32 at the cap). The
seed's queen-trade best line (gains 1, 1, 5 capped, 1, 1) has a gap of 0.52 and is drawn as a
miss spike. So late and depth-5 spike strata are the scarce ones; early and spike at depth 3 are
cheap.

Append contract: ``--append-to LABELFILE`` appends to the existing label TSV in append mode only
(never a rewrite), in the set 7 row shape (n, set, elo, move, link, then empty hidden columns and
an empty label, no comment cell), n continuing from the file's maximum. A second set-8 append is
refused (restore the file with git before a rerun), and ``--db dev`` can never append to
``reports/blunder-check/facepalm-labels.tsv`` (exit ``EXIT_APPEND_REFUSED``); both checks run
before Maia or the DB start. The key (arrays, depth-3 inputs, decaying means, group, stratum) goes
to gitignored ``temp/``.

Usage::

    # dev (local database, the smoke run; dev holds few users, so lift the rating cap)
    uv run --group maia-inference python scripts/blunder_check/miss_labels.py --db dev \
        --sample-percent 100 --pure-misses 8 --mixed 2 --max-rating 3000 \
        --out temp/blunder-check/miss-labels-dev.tsv \
        --key-out temp/blunder-check/miss-labels-dev-key.json

    # prod (needs the tunnel: bin/prod_db_tunnel.sh; run from the orchestrator, not an executor)
    uv run --group maia-inference python scripts/blunder_check/miss_labels.py --db prod \
        --out temp/blunder-check/miss-labels.tsv

    # set 8, dev smoke (append to a COPY of the label file under temp/, never the real one)
    uv run --group maia-inference python scripts/blunder_check/miss_labels.py --db dev \
        --mode disagreement --sample-percent 50 --max-rating 3000 \
        --append-to temp/blunder-check/set8-smoke-labels.tsv \
        --key-out temp/blunder-check/set8-smoke-key.json

    # set 8, prod (orchestrator, tunnel up)
    uv run --group maia-inference python scripts/blunder_check/miss_labels.py --db prod \
        --mode disagreement --append-to reports/blunder-check/facepalm-labels.tsv \
        --key-out temp/blunder-check/set8-key-2026-11-16.json

The owner labels the sheet blind (``label`` 1 = unfair / facepalm, 0 = fair, as in the 250
sheets); the labelled TSV is then passed to ``facepalm_features.py --labels`` next to the
existing label file.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import random
import sys
from bisect import bisect_right
from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Literal, cast, get_args

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
from app.services.facepalm_inputs import material_inputs_from_facts  # noqa: E402
from app.services.line_material import (  # noqa: E402
    LineFacts,
    quiet_best_line_facts,
    quiet_line_facts,
)
from app.services.maia_flaw_scoring import best_move_uci, replay_flaw_boards  # noqa: E402
from app.services.maia_flaw_stats import pre_blunder_spread  # noqa: E402
from app.services.normalization import is_correspondence_time_control  # noqa: E402
from scripts.blunder_check.decaying_mean import (  # noqa: E402
    decaying_mean,
    gain_series,
    loss_series,
)
from scripts.blunder_check.facepalm_features import (  # noqa: E402
    DB_TARGETS,
    DEFAULT_MAIA_THREADS,
    EXIT_MAIA_UNAVAILABLE,
    EXIT_OK,
    PV_SEPARATOR,
    PolicyFn,
    parse_labels,
)
from scripts.blunder_check.metrics import MaterialType, material_type_of  # noqa: E402
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
# Set 8 draws from a different TABLESAMPLE than set 7 (seed 254) and keeps its own key file.
DISAGREEMENT_SAMPLE_SEED: int = 261116
DEFAULT_DISAGREEMENT_KEY_OUT: Path = Path("temp/blunder-check/set8-key.json")

# Material types the sheet draws from: pure misses and rows that both lose and miss.
PURE_TYPE: MaterialType = "misses"
MIXED_TYPE: MaterialType = "loses_and_misses"
MIXED_STRATUM: str = "mixed"

# --- Set 8: the disagreement draw (SEED-261115-agg, owner decision 2026-11-16) ---
DrawMode = Literal["misses", "disagreement"]
DisagreementGroup = Literal["loss", "miss"]
DrawGroup = Literal["loss", "miss", "plain"]
Shape = Literal["spike", "early", "late", "other"]
LossStratum = Literal["loss_spike", "loss_early", "loss_late", "loss_other"]
MissStratum = Literal["miss_spike", "miss_early", "miss_late", "miss_other"]
DisagreementStratum = LossStratum | MissStratum

DISAGREEMENT_SET_ID: str = "8"
# A row is drawn when the depth-3 value and the decaying mean differ by at least this (pawns).
DISAGREEMENT_MIN_PAWNS: float = 0.5
# A spike: an interior odd depth (3, 5, 7) that exceeds both odd neighbours by at least this.
SPIKE_MIN_PAWNS: int = 1
SPIKE_DEPTHS: tuple[int, ...] = (3, 5, 7)
# Odd depths are two plies apart in the series.
DEPTH_STEP: int = 2
# Quotas per stratum, in borrowing order (the "other" stratum is the first lender, see below).
LOSS_STRATUM_QUOTAS: dict[LossStratum, int] = {
    "loss_spike": 6,
    "loss_early": 6,
    "loss_late": 6,
    "loss_other": 5,
}
MISS_STRATUM_QUOTAS: dict[MissStratum, int] = {
    "miss_spike": 6,
    "miss_early": 5,
    "miss_late": 6,
    "miss_other": 5,
}
PLAIN_MISS_TARGET: int = 15
LOSS_STRATUM_BY_SHAPE: dict[Shape, LossStratum] = {
    "spike": "loss_spike",
    "early": "loss_early",
    "late": "loss_late",
    "other": "loss_other",
}
MISS_STRATUM_BY_SHAPE: dict[Shape, MissStratum] = {
    "spike": "miss_spike",
    "early": "miss_early",
    "late": "miss_late",
    "other": "miss_other",
}

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
    # Signed 9-slot material lists of the played and the best line (LineFacts.material_array);
    # empty when not recorded (the set-7 test helpers).
    played_material: tuple[int | None, ...] = ()
    best_material: tuple[int | None, ...] = ()


@dataclass(frozen=True, slots=True)
class Selected:
    """A chosen row and the stratum it was drawn for (and the set-8 group, None for set 7)."""

    candidate: MissCandidate
    stratum: str
    group: DrawGroup | None = None


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


def _candidate_missed(depth_3_gain: int | None, stored_missed: float | None) -> int | None:
    """The missed gain a candidate is bucketed on.

    Bug fix (259 review WR-01): the material type comes from the stored decaying-mean inputs, the
    bucket used the depth-3 gain alone. A row typed as a miss whose gain only shows after depth 3
    (depth-3 gain None or below the smallest bucket) made `missed_size_bucket` raise and stopped
    the sampler run. Such a row now takes the stored gain, rounded and floored at the smallest
    bucket; a usable depth-3 gain is kept as before.
    """
    smallest = MISSED_SIZE_BUCKETS[0][0]
    if depth_3_gain is not None and depth_3_gain >= smallest:
        return depth_3_gain
    if stored_missed is not None and stored_missed >= smallest:
        return max(smallest, round(stored_missed))
    return depth_3_gain


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


# ---------------------------------------------------------------------------
# Disagreement classification (set 8, SEED-261115-agg)
# ---------------------------------------------------------------------------


def _has_spike(series: Mapping[int, int | None]) -> bool:
    """Whether an interior odd depth exceeds both odd neighbours by at least SPIKE_MIN_PAWNS."""
    for depth in SPIKE_DEPTHS:
        before, here, after = (
            series.get(depth - DEPTH_STEP),
            series.get(depth),
            series.get(depth + DEPTH_STEP),
        )
        if before is None or here is None or after is None:
            continue
        if here - max(before, after) >= SPIKE_MIN_PAWNS:
            return True
    return False


def series_shape(series: Mapping[int, int | None]) -> Shape:
    """The shape of a per-depth series, in this precedence.

    spike: an interior odd depth (3, 5, 7) peaks over both neighbours; early: nonzero at depth 1
    and 0 at depth 3 (recovered, or the gain is gone, by depth 3); late: 0 at depths 1 and 3 (the
    value only appears at depth 5 or later); other: everything else. The owner named spike,
    recovered-by-3 and appears-at-5+; "other" and the symmetric miss strata are planner discretion.
    """
    if _has_spike(series):
        return "spike"
    first, third = series.get(1), series.get(LINE_DEPTH)
    if first is not None and first > 0 and third == 0:
        return "early"
    if first == 0 and third == 0:
        return "late"
    return "other"


def _depth3_gap(series: Mapping[int, int | None]) -> float | None:
    """|depth-3 value - decaying mean|, None when depth 3 or every depth is unknown."""
    third, mean = series.get(LINE_DEPTH), decaying_mean(series)
    if third is None or mean is None:
        return None
    return abs(third - mean)


def disagreement_group(
    played_material: Sequence[int | None],
    played_mate_ply: int | None,
    best_material: Sequence[int | None],
    best_mate_ply: int | None,
) -> tuple[DisagreementGroup, DisagreementStratum] | None:
    """(group, stratum) when the depth-3 input and the decaying mean disagree, else None.

    The loss group: the depth-3 loss and the decaying mean of the loss series differ by at least
    DISAGREEMENT_MIN_PAWNS. The miss group: the played line loses nothing at any known odd depth
    and the depth-3 gain and the decaying mean of the gain series differ by that much. A row that
    loses and whose only disagreement is the gain is not drawn.
    """
    losses = loss_series(played_material, played_mate_ply)
    loss_gap = _depth3_gap(losses)
    if loss_gap is not None and loss_gap >= DISAGREEMENT_MIN_PAWNS:
        return "loss", LOSS_STRATUM_BY_SHAPE[series_shape(losses)]
    if any(value for value in losses.values() if value is not None):
        return None
    gains = gain_series(played_material, best_material, best_mate_ply)
    gain_gap = _depth3_gap(gains)
    if gain_gap is not None and gain_gap >= DISAGREEMENT_MIN_PAWNS:
        return "miss", MISS_STRATUM_BY_SHAPE[series_shape(gains)]
    return None


def candidate_group(
    candidate: MissCandidate,
) -> tuple[DisagreementGroup, DisagreementStratum] | None:
    """`disagreement_group` of a derived candidate."""
    return disagreement_group(
        candidate.played_material,
        candidate.played_mate_ply,
        candidate.best_material,
        candidate.best_mate_ply,
    )


def build_candidate(
    raw: RawCandidate,
    pre_board: chess.Board,
    played_uci: str,
    policy_fn: PolicyFn,
    tally: Tally,
    *,
    mode: DrawMode = "misses",
) -> MissCandidate | None:
    """The derived values of one blunder, or None when it is dropped or not a sampled type.

    `pre_board` is the position before the blunder (never mutated) and `played_uci` the blunder.
    Both stored lines must be stable (D-15); the material type (quiet rule, 259 D-03) is counted
    in `tally`. In "misses"
    mode only pure misses and mixed rows reach the Maia policy call; in "disagreement" mode pure
    misses and rows where depth 3 and the decaying mean disagree do.
    """
    facts = quiet_line_facts(pre_board, played_uci, raw.refutation_pv)
    best_facts = quiet_best_line_facts(pre_board, raw.best_pv)
    stable = is_stable_line(
        raw.refutation_pv, ends_in_mate=_line_ends_in_mate(facts)
    ) and is_stable_line(raw.best_pv, ends_in_mate=_line_ends_in_mate(best_facts))
    if not stable:
        tally.dropped[DROP_UNSTABLE] += 1
        return None
    tally.stable += 1
    played_3, best_3 = facts.material_at(LINE_DEPTH), best_facts.material_at(LINE_DEPTH)
    inputs = material_inputs_from_facts(facts, best_facts)
    kind = material_type_of(inputs.loss, 0.0 if inputs.missed is None else inputs.missed)
    tally.by_type[kind] += 1
    played_material = tuple(facts.material_array())
    best_material = tuple(best_facts.material_array())
    if mode == "disagreement":
        keep = kind == PURE_TYPE or (
            disagreement_group(
                played_material, facts.mate_ply, best_material, best_facts.opponent_mate_ply
            )
            is not None
        )
    else:
        keep = kind in (PURE_TYPE, MIXED_TYPE)
    if not keep:
        return None
    pinned_elo = _pinned_elo(raw)
    pre = _pre_inputs(pre_board, best_move_uci(raw.best_pv, raw.best_move), pinned_elo, policy_fn)
    if isinstance(pre, str):
        tally.dropped[pre] += 1
        return None
    return MissCandidate(
        game_id=raw.game_id,
        ply=raw.ply,
        mover_rating=raw.mover_rating,
        move_san=pre_board.san(chess.Move.from_uci(played_uci)),
        pinned_elo=pinned_elo,
        played_3=played_3,
        best_3=best_3,
        missed=_candidate_missed(_missed_gain(played_3, best_3), inputs.missed),
        played_mate_ply=facts.mate_ply,
        best_mate_ply=best_facts.opponent_mate_ply,
        best_prob=pre[0],
        pre_spread=pre[1],
        material=kind,
        played_material=played_material,
        best_material=best_material,
    )


def collect_candidates(
    rows: Sequence[RawCandidate],
    *,
    excluded_games: Collection[int],
    max_rating: int,
    policy_fn: PolicyFn,
    tally: Tally,
    mode: DrawMode = "misses",
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
        candidate = build_candidate(raw, pre_board, played_uci, policy_fn, tally, mode=mode)
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
# Stratification of the disagreement draw (set 8)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DisagreementDraw:
    """The set-8 rows (shuffled) and what fell short, per stratum and per group."""

    rows: list[Selected]
    # Stratum -> rows its own supply could not give.
    shortfall: dict[str, int]
    # Group ("loss", "miss", "plain") -> rows no stratum of the group could give.
    unfilled: dict[str, int]
    # Stratum -> how many candidates the pool offered it.
    supply: dict[str, int]


def _disagreement_pools(
    ordered: Sequence[MissCandidate],
) -> dict[DisagreementStratum, list[MissCandidate]]:
    """The candidates by disagreement stratum (every stratum present), in `ordered` order."""
    pools: dict[DisagreementStratum, list[MissCandidate]] = {
        **{stratum: [] for stratum in LOSS_STRATUM_QUOTAS},
        **{stratum: [] for stratum in MISS_STRATUM_QUOTAS},
    }
    for candidate in ordered:
        hit = candidate_group(candidate)
        if hit is not None:
            pools[hit[1]].append(candidate)
    return pools


def _borrow_from_group(
    stratum: DisagreementStratum,
    missing: int,
    group: DisagreementGroup,
    quotas: Sequence[tuple[DisagreementStratum, int]],
    spare: dict[DisagreementStratum, list[MissCandidate]],
) -> list[Selected]:
    """Up to `missing` spare rows from the other strata of the same group.

    The group's `*_other` stratum lends first, then the rest in quota-declaration order; every
    borrowed row keeps the stratum it was drawn from (as set 7's `_borrow` does).
    """
    lenders = sorted((name for name, _ in quotas if name != stratum), key=_is_not_other)
    borrowed: list[Selected] = []
    for lender in lenders:
        while len(borrowed) < missing and spare[lender]:
            borrowed.append(Selected(spare[lender].pop(0), lender, group))
    return borrowed


def _is_not_other(stratum: str) -> bool:
    """Sort key putting the `*_other` stratum first (sorted is stable, so quota order is kept)."""
    return not stratum.endswith("_other")


def _draw_group(
    group: DisagreementGroup,
    quotas: Sequence[tuple[DisagreementStratum, int]],
    pools: Mapping[DisagreementStratum, list[MissCandidate]],
    rng: random.Random,
) -> tuple[list[Selected], dict[DisagreementStratum, int], int]:
    """(rows, shortfall per stratum, rows unfilled) for one group.

    A stratum that cannot fill its quota borrows from the group's other strata; rows no stratum
    of the group can give are `unfilled` (never padded from another group).
    """
    rows: list[Selected] = []
    spare: dict[DisagreementStratum, list[MissCandidate]] = {}
    shortfall: dict[DisagreementStratum, int] = {}
    for stratum, quota in quotas:
        pool = pools[stratum]
        rng.shuffle(pool)
        rows.extend(Selected(candidate, stratum, group) for candidate in pool[:quota])
        spare[stratum] = pool[quota:]
        if len(pool) < quota:
            shortfall[stratum] = quota - len(pool)
    unfilled = 0
    for stratum, missing in shortfall.items():
        borrowed = _borrow_from_group(stratum, missing, group, quotas, spare)
        rows.extend(borrowed)
        unfilled += missing - len(borrowed)
    return rows, shortfall, unfilled


def stratify_disagreement(
    candidates: Sequence[MissCandidate], *, plain_target: int, seed: int
) -> DisagreementDraw:
    """Pick the set-8 rows: the loss group, the miss group and plain depth-3 pure misses.

    Deterministic given the seed and the pool. Each disagreement stratum takes its quota from its
    shuffled pool; the plain pure misses (the depth-3 PURE_TYPE candidates not already chosen) are
    spread over set 7's size x best-move-tertile cells. All rows are shuffled so the order never
    reveals a stratum.
    """
    rng = random.Random(seed)
    # Sorted first so the draw depends on the pool, never on the order it arrived in.
    ordered = sorted(candidates, key=lambda c: (c.game_id, c.ply))
    pools = _disagreement_pools(ordered)
    supply: dict[str, int] = {stratum: len(pool) for stratum, pool in pools.items()}
    loss_quotas = list(LOSS_STRATUM_QUOTAS.items())
    miss_quotas = list(MISS_STRATUM_QUOTAS.items())
    loss_rows, loss_short, loss_unfilled = _draw_group("loss", loss_quotas, pools, rng)
    miss_rows, miss_short, miss_unfilled = _draw_group("miss", miss_quotas, pools, rng)
    rows = loss_rows + miss_rows
    taken = {(row.candidate.game_id, row.candidate.ply) for row in rows}
    plain_pool = [c for c in ordered if c.material == PURE_TYPE and (c.game_id, c.ply) not in taken]
    plain, plain_short, plain_unfilled = _fill_cells(
        _group_cells(plain_pool, rng), plain_target, rng
    )
    rows.extend(replace(selected, group="plain") for selected in plain)
    rng.shuffle(rows)
    return DisagreementDraw(
        rows=rows,
        shortfall={**loss_short, **miss_short, **plain_short},
        unfilled={"loss": loss_unfilled, "miss": miss_unfilled, "plain": plain_unfilled},
        supply=supply,
    )


# ---------------------------------------------------------------------------
# Output: the blind sheet and the key file
# ---------------------------------------------------------------------------


def blind_row(n: int, row: Selected, *, set_id: str = MISS_SET_ID) -> list[str]:
    """The cells of one sheet row in BLIND_COLUMNS order (the label cell is empty)."""
    candidate = row.candidate
    return [
        str(n),
        set_id,
        str(candidate.mover_rating),
        candidate.move_san,
        LINK_TEMPLATE.format(game_id=candidate.game_id, ply=candidate.ply),
        "",
    ]


def write_blind_tsv(rows: Sequence[Selected], path: Path, *, set_id: str = MISS_SET_ID) -> None:
    """Write the blind sheet: header, then one line per row numbered 1..N in the given order."""
    lines = ["\t".join(BLIND_COLUMNS)]
    lines.extend("\t".join(blind_row(n, row, set_id=set_id)) for n, row in enumerate(rows, start=1))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def _key_entry(row: Selected) -> dict[str, object]:
    """The set-7 key entry of a row: the hidden inputs, the material type and the stratum."""
    candidate = row.candidate
    return {
        "game_id": candidate.game_id,
        "ply": candidate.ply,
        "played_3": candidate.played_3,
        "best_3": candidate.best_3,
        "missed": candidate.missed,
        "best_prob": candidate.best_prob,
        "pre_spread": candidate.pre_spread,
        "material_type": candidate.material,
        "stratum": row.stratum,
    }


def _disagreement_key_entry(row: Selected, set_id: str) -> dict[str, object]:
    """The set-8 key entry: the set-7 keys plus the arrays, the depth-3 inputs and decaying means."""
    candidate = row.candidate
    losses = loss_series(candidate.played_material, candidate.played_mate_ply)
    gains = gain_series(candidate.played_material, candidate.best_material, candidate.best_mate_ply)
    return {
        **_key_entry(row),
        "set": set_id,
        "group": row.group,
        "played_material": list(candidate.played_material),
        "best_material": list(candidate.best_material),
        "played_mate_ply": candidate.played_mate_ply,
        "best_mate_ply": candidate.best_mate_ply,
        "loss_3": losses.get(LINE_DEPTH),
        "loss_decay": decaying_mean(losses),
        "gain_3": gains.get(LINE_DEPTH),
        "gain_decay": decaying_mean(gains),
    }


def write_key(
    rows: Sequence[Selected],
    path: Path,
    *,
    numbers: Sequence[int] | None = None,
    set_id: str = MISS_SET_ID,
) -> None:
    """Write the key file: n -> the hidden inputs, the material type and the stratum.

    `numbers` are the n values the rows carry in the label file (default 1..N, set 7's sheet);
    rows drawn for a group (set 8) get the extended entry.
    """
    keys = list(numbers) if numbers is not None else list(range(1, len(rows) + 1))
    key = {
        str(n): _key_entry(row) if row.group is None else _disagreement_key_entry(row, set_id)
        for n, row in zip(keys, rows, strict=True)
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(key, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Appending to an existing label file (set 8)
# ---------------------------------------------------------------------------

EXIT_APPEND_REFUSED: int = 7
APPEND_REQUIRED_COLUMNS: tuple[str, ...] = ("n", "set", "elo", "move", "link", "label")


class AppendRefused(ValueError):
    """The append target cannot take the rows (bad header, set already present, no file)."""


def _target_header_and_next_n(path: Path, set_id: str) -> tuple[list[str], int]:
    """The target's header columns and the n of the next row, or raise AppendRefused."""
    try:
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            header = list(reader.fieldnames or [])
            records = list(reader)
    except OSError as error:
        raise AppendRefused("the append target cannot be read") from error
    missing = [name for name in APPEND_REQUIRED_COLUMNS if name not in header]
    if missing or header.index("link") > header.index("label"):
        raise AppendRefused("the append target header lacks the label file columns")
    if any(record["set"] == set_id for record in records):
        raise AppendRefused("the append target already holds rows of this set")
    return header, max((int(record["n"]) for record in records), default=0) + 1


def check_append_target(path: Path, set_id: str) -> None:
    """Raise AppendRefused unless `path` is a label file that can take a new `set_id` set."""
    _target_header_and_next_n(path, set_id)


def _append_line(header: Sequence[str], values: Mapping[str, str]) -> str:
    """One row up to and including `label`: given cells filled, every other cell empty.

    Columns after `label` (comment) are omitted, which is the set 7 row shape.
    """
    return "\t".join(values.get(name, "") for name in header[: header.index("label") + 1])


def append_blind_rows(rows: Sequence[Selected], path: Path, *, set_id: str) -> list[int]:
    """Append the blind rows to the label file `path` without touching an existing byte.

    n continues from the file's maximum; the hidden input columns and the label stay empty and
    there is no comment cell. Opened in append mode only. Returns the n values assigned.
    """
    header, first_n = _target_header_and_next_n(path, set_id)
    if not rows:
        return []
    numbers = list(range(first_n, first_n + len(rows)))
    lines = [
        _append_line(
            header,
            dict(zip(BLIND_COLUMNS, blind_row(n, row, set_id=set_id), strict=True)),
        )
        for n, row in zip(numbers, rows, strict=True)
    ]
    with path.open("rb") as handle:
        handle.seek(-1, 2)
        needs_newline = handle.read(1) != b"\n"
    with path.open("ab") as handle:
        handle.write((("\n" if needs_newline else "") + "\n".join(lines) + "\n").encode())
    return numbers


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


def _counts_text(counts: Mapping[str, int]) -> str:
    return ", ".join(f"{name} {count}" for name, count in counts.items())


def disagreement_summary_line(tally: Tally, draw: DisagreementDraw) -> str:
    """One line for a set-8 draw: counts only, never an analysis link.

    Rows read, dropped, stable, per material type, the supply per stratum, rows written per
    stratum, the shortfall per stratum and the unfilled rows per group.
    """
    dropped = _counts_text(dict(sorted(tally.dropped.items())))
    by_type = _counts_text(dict(sorted(tally.by_type.items())))
    written = Counter(row.stratum for row in draw.rows)
    shortfall = _counts_text(dict(sorted(draw.shortfall.items())))
    return (
        f"candidates read {tally.read}; dropped: {dropped or 'none'}; stable {tally.stable}; "
        f"by material type: {by_type or 'none'}; supply per stratum: "
        f"{_counts_text(draw.supply)}; rows written {len(draw.rows)} "
        f"({_counts_text(dict(sorted(written.items()))) or 'none'}); "
        f"shortfall: {shortfall or 'none'}; unfilled {_counts_text(draw.unfilled)}"
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
        "--mode",
        choices=get_args(DrawMode),
        default="misses",
        help="misses: set 7's draw; disagreement: set 8 (depth 3 vs decaying mean disagree)",
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--out", type=Path, help="blind labelling sheet TSV to write")
    target.add_argument(
        "--append-to",
        type=Path,
        help="existing label TSV to append the blind rows to (disagreement mode; append only)",
    )
    parser.add_argument(
        "--key-out",
        type=Path,
        default=None,
        help="key file with the hidden inputs (keep under gitignored temp/); "
        "default depends on --mode",
    )
    parser.add_argument(
        "--exclude-labels",
        type=Path,
        action="append",
        default=None,
        help="label TSV whose games are excluded; repeatable (default: the 180 existing labels)",
    )
    parser.add_argument("--sample-percent", type=float, default=DEFAULT_SAMPLE_PERCENT)
    parser.add_argument(
        "--seed", type=int, default=None, help="TABLESAMPLE seed; default depends on --mode"
    )
    parser.add_argument(
        "--pure-misses",
        type=int,
        default=None,
        help="pure misses (misses mode, default 40) or plain pure misses (disagreement, default 15)",
    )
    parser.add_argument(
        "--mixed", type=int, default=MIXED_TARGET, help="mixed rows (misses mode only)"
    )
    parser.add_argument("--max-rating", type=int, default=MAX_MOVER_RATING)
    parser.add_argument("--maia-threads", type=int, default=DEFAULT_MAIA_THREADS)
    return _resolve_mode_defaults(parser.parse_args(argv))


def _resolve_mode_defaults(args: argparse.Namespace) -> argparse.Namespace:
    """Fill the options whose default depends on --mode (set 8 must not reuse set 7's draw)."""
    disagreement = args.mode == "disagreement"
    if args.seed is None:
        args.seed = DISAGREEMENT_SAMPLE_SEED if disagreement else DEFAULT_SAMPLE_SEED
    if args.pure_misses is None:
        args.pure_misses = PLAIN_MISS_TARGET if disagreement else PURE_MISS_TARGET
    if args.key_out is None:
        args.key_out = DEFAULT_DISAGREEMENT_KEY_OUT if disagreement else DEFAULT_KEY_OUT
    return args


def excluded_game_ids(paths: Sequence[Path]) -> set[int]:
    """The game ids of every label TSV in `paths` (D-16: games already labelled are excluded)."""
    return {row.game_id for path in paths for row in parse_labels(path)}


async def _load_candidates(
    args: argparse.Namespace, excluded: Collection[int], tally: Tally
) -> list[MissCandidate] | None:
    """Read the sampled blunders (read-only) and derive the candidates; None when Maia is missing."""
    await maia_engine.start_maia(intra_op_num_threads=args.maia_threads)
    if not maia_engine.is_maia_available():
        print("Maia is unavailable (uv sync --group maia-inference?)", file=sys.stderr)
        return None
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
    return collect_candidates(
        raw_rows,
        excluded_games=excluded,
        max_rating=args.max_rating,
        policy_fn=maia_engine.full_policy,
        tally=tally,
        mode=args.mode,
    )


def _append_refusal(args: argparse.Namespace) -> str | None:
    """Why the set-8 output target is refused (checked before Maia or the DB start), else None.

    Dev rows must never land in the committed label file, the target must be a label file, and a
    set can only be appended once (restore the file with git before a rerun).
    """
    if args.append_to is None:
        return None
    if args.mode != "disagreement":
        return "--append-to needs --mode disagreement"
    real_labels = (_REPO_ROOT / DEFAULT_EXCLUDE_LABELS).resolve()
    if args.db == "dev" and args.append_to.resolve() == real_labels:
        return "dev rows must not be appended to the real label file"
    try:
        check_append_target(args.append_to, DISAGREEMENT_SET_ID)
    except AppendRefused as error:
        return str(error)
    return None


def _write_disagreement(args: argparse.Namespace, draw: DisagreementDraw) -> int:
    """Append the set-8 rows (or write the sheet for --out) and the key file."""
    if args.append_to is None:
        write_blind_tsv(draw.rows, args.out, set_id=DISAGREEMENT_SET_ID)
        numbers = list(range(1, len(draw.rows) + 1))
    else:
        try:
            numbers = append_blind_rows(draw.rows, args.append_to, set_id=DISAGREEMENT_SET_ID)
        except AppendRefused as error:
            print(f"append refused: {error}", file=sys.stderr)
            return EXIT_APPEND_REFUSED
    write_key(draw.rows, args.key_out, numbers=numbers, set_id=DISAGREEMENT_SET_ID)
    return EXIT_OK


def _excluded_label_files(args: argparse.Namespace) -> list[Path]:
    """The label TSVs whose games are never redrawn: the given (or default) ones and the target."""
    paths = list(args.exclude_labels or [_REPO_ROOT / DEFAULT_EXCLUDE_LABELS])
    if args.append_to is not None:
        paths.append(args.append_to)
    return paths


async def _run(args: argparse.Namespace) -> int:
    refusal = _append_refusal(args)
    if refusal is not None:
        print(f"append refused: {refusal}", file=sys.stderr)
        return EXIT_APPEND_REFUSED
    excluded = excluded_game_ids(_excluded_label_files(args))
    tally = Tally()
    candidates = await _load_candidates(args, excluded, tally)
    if candidates is None:
        return EXIT_MAIA_UNAVAILABLE
    if args.mode == "disagreement":
        draw = stratify_disagreement(candidates, plain_target=args.pure_misses, seed=args.seed)
        code = _write_disagreement(args, draw)
        print(disagreement_summary_line(tally, draw))
        return code
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
