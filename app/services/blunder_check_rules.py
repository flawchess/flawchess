"""Selection rules for the blunder-check drill (SEED-261108-dk0, Phase 249).

This module is the single home of the selection math (249 D-03..D-06) that both the app and the
Phase 248 calibration report (scripts/blunder_check/) use. The app must not import from
scripts/, so the pure functions moved here and the report re-exports them. Everything here is
pure (no DB, no Maia, no I/O).

Expected-score (ES) conventions come from the flaw pipeline's own
``_run_all_moves_pass`` output ``{ply: (mover, severity, es_before, es_after)}``, all in
the mover's point of view:
  - pre-move ES of a judged move q          = all_moves[q][2]
  - ES the user actually reached with move p = all_moves[p][3]   (``es_played``)
  - ES reference for a miss at ply p         = 1 - all_moves[p - 1][2], the user's ES
    before the opponent's previous move (what the user would have had without the gift).
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Literal, TypedDict

from app.repositories.query_utils import mover_is_white_at_ply
from app.services.eval_utils import eval_cp_to_expected_score

# Private import by design: the threshold and the per-ply entry shape must be the classifier's
# own, never re-derived (precedent: scripts/remote_eval_worker.py imports _run_all_moves_pass).
from app.services.flaws_service import INACCURACY_DROP, _MoveEntry  # noqa: PLC2701
from app.services.maia_flaw_stats import RANK_BASE
from app.services.train_pool import (
    HERRING_MIN_OPENING_PLY,
    HERRING_MIN_PLY,
    HERRING_OPENING_PHASE,
)
from app.services.train_score import MOVE_TIER_POINTS

# ---------------------------------------------------------------------------
# Named constants (no magic numbers)
# ---------------------------------------------------------------------------

# 248 D-16 hazard model: probability that a user blunders on any given move inside a window.
HAZARD: float = 0.265
# Candidate herring window lengths (user moves) the hazard model averages over.
WINDOW_LENGTHS: tuple[int, ...] = (3, 4, 5)
# Plies of lead-in the sampler prepends before the window: just the opponent's move, so the
# first question follows one reply (UAT: the 4-ply replay was too long).
LEAD_IN_PLIES: int = 1
# Latest window position at which a blunder is modelled (matches max(WINDOW_LENGTHS)).
MAX_BLUNDER_POSITION: int = 5

# 249 D-06 findability thresholds: a blunder is served only if Maia finds the refutation
# (allowed) or the best move (pure miss) with at least this probability, or ranks it first.
REFUTATION_PROB_MIN: float = 0.3
BEST_PROB_MIN: float = 0.2
# 249 D-05 eval band: every judged and herring move must have its pre-move ES inside [low, high].
ES_BAND_LOW: float = 0.10
ES_BAND_HIGH: float = 0.90
# Undecided-position rule (Phase 249 UAT): a blunder is served only if the game was not decided
# yet, a Stockfish eval within +/- BLUNDER_MAX_PRE_EVAL_CP. Tested on the classifier's own ES (the
# ES map is monotone in cp, so this is exactly the cp band); a mate maps to +/- MATE_CP_EQUIVALENT
# and always falls outside. An allowed blunder is tested on the position before it. A miss is
# tested on the position before the opponent's gift (owner: keep big missed gifts), since the
# position right before the miss is decided by the gift itself. Applies to the blunder only: the
# moves before it and the herrings keep the wider D-05 band.
BLUNDER_MAX_PRE_EVAL_CP: int = 300
BLUNDER_ES_LOW: float = eval_cp_to_expected_score(-BLUNDER_MAX_PRE_EVAL_CP, "white")
BLUNDER_ES_HIGH: float = eval_cp_to_expected_score(BLUNDER_MAX_PRE_EVAL_CP, "white")
# Early-ply floor for a served blunder (Phase 249 UAT): the same floors personalized puzzles use
# for their sampled positions, so an opening-theory slip is never the blunder to find. An
# opening-phase position needs the stricter floor (move 10+).
BLUNDER_MIN_PLY: int = HERRING_MIN_PLY
BLUNDER_MIN_OPENING_PLY: int = HERRING_MIN_OPENING_PLY
# 249 D-02 windows per session.
BLUNDER_CHECK_SESSION_WINDOWS: int = 6
# 249 D-14 points: 1 per correctly judged safe move, 3 for flagging the blunder, plus the better
# move graded like personalized puzzles (249 D-17), so its full value is the good tier's points.
SAFE_POINTS: int = 1
BLUNDER_POINTS: int = 3
BETTER_MOVE_POINTS: int = MOVE_TIER_POINTS["good"]

MissCase = Literal["allowed", "pure_miss", "mixed", "unclassified"]

_FIRST_POSITION: Final[int] = 1


def past_early_ply_floor(ply: int, phase: int | None) -> bool:
    """Whether a blunder at `ply` is late enough to serve; an unknown phase gets the base floor."""
    floor = BLUNDER_MIN_OPENING_PLY if phase == HERRING_OPENING_PHASE else BLUNDER_MIN_PLY
    return ply >= floor


@dataclass(frozen=True)
class WindowShape:
    """A drawn window: length in user moves and the blunder position (None for a herring)."""

    length: int
    blunder_position: int | None


@dataclass(frozen=True)
class MoveJudgement:
    """One user move: Good (no severity at all, so inaccuracies are excluded) and its pre-move ES."""

    ply: int
    good: bool
    es_before: float | None


class HazardWeights(TypedDict):
    """Hazard-model output: raw P(blunder at k), the herring (no-blunder) share, normalized weights."""

    raw: dict[int, float]
    herring_share: float
    normalized: dict[int, float]


class FindabilityInputs(TypedDict):
    """Maia numbers for one blunder: refutation pair (allowed) and best-move pair (pure miss)."""

    refutation_prob: float | None
    refutation_rank: int | None
    best_prob: float | None
    best_rank: int | None


# ---------------------------------------------------------------------------
# Per-move judgement
# ---------------------------------------------------------------------------


def user_move_judgements(
    all_moves: Mapping[int, _MoveEntry],
    move_plies: Sequence[int],
    user_is_white: bool,
) -> list[MoveJudgement]:
    """Judge the user's moves among move_plies (248 D-15): Good iff classified with severity None."""
    judgements: list[MoveJudgement] = []
    for ply in move_plies:
        if mover_is_white_at_ply(ply) != user_is_white:
            continue
        entry = all_moves.get(ply)
        if entry is None:
            judgements.append(MoveJudgement(ply, False, None))
        else:
            judgements.append(MoveJudgement(ply, entry[1] is None, entry[2]))
    return judgements


def blunder_es(
    all_moves: Mapping[int, _MoveEntry],
    ply: int,
) -> tuple[float | None, float | None, float | None]:
    """Return (pre-move ES, es_played, es_ref) for the user's blunder at ply, all user POV (248 D-13)."""
    entry = all_moves.get(ply)
    previous = all_moves.get(ply - 1)
    es_before = entry[2] if entry is not None else None
    es_played = entry[3] if entry is not None else None
    # previous[2] is the opponent's pre-move ES; flip to the user's point of view.
    es_ref = 1.0 - previous[2] if previous is not None else None
    return es_before, es_played, es_ref


def miss_case(is_miss: bool, es_ref: float | None, es_played: float | None) -> MissCase:
    """Classify a blunder: allowed (not a miss), pure_miss (gift only returned), mixed, or unclassified."""
    if not is_miss:
        return "allowed"
    if es_ref is None or es_played is None:
        return "unclassified"
    if es_played >= es_ref - INACCURACY_DROP:
        return "pure_miss"
    return "mixed"


# ---------------------------------------------------------------------------
# Eval band and window fit
# ---------------------------------------------------------------------------


def in_band(es: float | None, band_low: float, band_high: float) -> bool:
    """True iff es is known and band_low <= es <= band_high."""
    return es is not None and band_low <= es <= band_high


def blunder_position_undecided(
    is_miss: bool, es_before: float | None, es_ref: float | None
) -> bool:
    """Whether the game was undecided (eval within +/- BLUNDER_MAX_PRE_EVAL_CP, no mate) before
    the blunder, or, for a miss, before the opponent's gift (es_ref)."""
    es = es_ref if is_miss else es_before
    return in_band(es, BLUNDER_ES_LOW, BLUNDER_ES_HIGH)


def blunder_fits_position(
    preceding: Sequence[MoveJudgement],
    blunder_es_before: float | None,
    position: int,
    band_low: float,
    band_high: float,
) -> bool:
    """248 D-16: a blunder fits window position k iff its pre-move ES is in band and the k-1 user
    moves immediately before it are all Good and in band. preceding is in game order."""
    if not in_band(blunder_es_before, band_low, band_high):
        return False
    needed = position - 1
    if needed == 0:
        return True
    if len(preceding) < needed:
        return False
    return all(j.good and in_band(j.es_before, band_low, band_high) for j in preceding[-needed:])


def max_fit_position(
    preceding: Sequence[MoveJudgement],
    es_before: float | None,
    band_low: float = ES_BAND_LOW,
    band_high: float = ES_BAND_HIGH,
) -> int:
    """Largest window position k in 1..MAX_BLUNDER_POSITION the blunder fits, 0 when none (249 D-03).

    Fit is monotone in k: position k checks a superset of the moves position k-1 checks, so the
    scan stops at the first k that fails.
    """
    best = 0
    for position in range(_FIRST_POSITION, MAX_BLUNDER_POSITION + 1):
        if not blunder_fits_position(preceding, es_before, position, band_low, band_high):
            break
        best = position
    return best


def hazard_position_weights(
    hazard: float = HAZARD,
    lengths: Sequence[int] = WINDOW_LENGTHS,
) -> HazardWeights:
    """Raw P(blunder at position k) = P(L >= k) * h * (1 - h)^(k-1), herring share = 1 - sum."""
    max_position = max(lengths)
    raw: dict[int, float] = {}
    for k in range(1, max_position + 1):
        reach = sum(1 for length in lengths if length >= k) / len(lengths)
        raw[k] = reach * hazard * (1.0 - hazard) ** (k - 1)
    total = sum(raw.values())
    return HazardWeights(
        raw=raw,
        herring_share=1.0 - total,
        normalized={k: v / total for k, v in raw.items()},
    )


def draw_window_shape(rng: random.Random) -> WindowShape:
    """L uniform over WINDOW_LENGTHS; the blunder sits at the first position whose hazard fires."""
    length = rng.choice(WINDOW_LENGTHS)
    for position in range(1, length + 1):
        if rng.random() < HAZARD:
            return WindowShape(length, position)
    return WindowShape(length, None)


# ---------------------------------------------------------------------------
# Findability (248 D-14, 249 D-06)
# ---------------------------------------------------------------------------


def _pair_passes(prob: float | None, rank: int | None, threshold: float) -> bool:
    """A (prob, rank) pair passes on prob >= threshold or being the top-ranked move; NULL never passes."""
    if prob is None or rank is None:
        return False
    return prob >= threshold or rank == RANK_BASE


def findable(
    case: MissCase,
    row: FindabilityInputs,
    refutation_threshold: float,
    miss_threshold: float,
) -> bool:
    """248 D-14: allowed tests the refutation pair at R, pure miss the best pair at X', mixed passes if either does."""
    refutation_ok = _pair_passes(
        row["refutation_prob"], row["refutation_rank"], refutation_threshold
    )
    best_ok = _pair_passes(row["best_prob"], row["best_rank"], miss_threshold)
    if case == "allowed":
        return refutation_ok
    if case == "pure_miss":
        return best_ok
    if case == "mixed":
        return refutation_ok or best_ok
    return False


# ---------------------------------------------------------------------------
# Herring windows (248 D-16, D-23)
# ---------------------------------------------------------------------------


def herring_flags(
    judgements: Sequence[MoveJudgement],
    band_low: float,
    band_high: float,
) -> list[bool]:
    """Per user move: Good and in the eval band."""
    return [j.good and in_band(j.es_before, band_low, band_high) for j in judgements]


def count_herring_windows(flags: Sequence[bool], length: int) -> int:
    """Disjoint windows of `length`: sum over maximal runs of True of floor(run / length)."""
    windows = 0
    run = 0
    for flag in flags:
        if flag:
            run += 1
            continue
        windows += run // length
        run = 0
    return windows + run // length
