"""Selection rules for the blunder-check drill (SEED-261108-dk0, Phase 249, 250).

This module is the single home of the selection math that both the app and the Phase 248
calibration report (scripts/blunder_check/) use: the facepalm threshold and its fitted
coefficients (250 D-01, D-04), the eval band and window fit (249 D-03..D-05) and the window
mix draws (250 D-12, D-16). The app must not import from scripts/, so the pure functions live
here and the report re-exports them. The 249 findability rule (Maia probability of the
refutation or best move) was retired by the facepalm score. Everything here is pure (no DB, no
Maia, no I/O).

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
from typing import Final, Literal

from app.repositories.query_utils import mover_is_white_at_ply
from app.services.eval_utils import eval_cp_to_expected_score

# Private import by design: the threshold and the per-ply entry shape must be the classifier's
# own, never re-derived (precedent: scripts/remote_eval_worker.py imports _run_all_moves_pass).
from app.services.flaws_service import INACCURACY_DROP, _MoveEntry  # noqa: PLC2701
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

# 250 D-01 / D-04 facepalm score (app/services/facepalm_score.py). A user blunder qualifies when its
# score is at least FACEPALM_SCORE_MIN. 254 D-13: 0.50 is the owner's choice of 2026-11-15,
# deliberately below the labels' meaning (label 1 = "should score above 70%", D-23) so the drill
# collects answers over a wider difficulty range. 256 D-13: at the Phase 256 refit checkpoint of
# 2026-11-16 the owner kept 0.50 (reports/blunder-check/facepalm-fit-2026-11-16.md, "Owner
# section"); the orchestrator had recommended 0.70 to cut false alarms, the owner declined.
# 259 D-15: after the first-principles refit (reports/blunder-check/facepalm-fit-2026-11-22.md) the
# owner decided on 2026-11-22 to raise the drill cut to 0.70: among the label passers 98 are fair
# and 11 unfair at 0.70 (118 / 25 at 0.50), and the prod drill pool stays about 33% of user
# blunders (median 414 usable windows per user).
FACEPALM_SCORE_MIN: float = 0.7
# 257 D-01: the library stats cut, the label meaning of a facepalm blunder (253 D-23: "should
# score above 70%"). Separate from the drill's FACEPALM_SCORE_MIN on purpose. It equals the
# Facepalm filter's High preset bound (70 / 100.0 in library_repository), so a stats row counts
# exactly the blunders the High preset lists (257 research Pitfall 7).
FACEPALM_STATS_MIN: float = 0.7
# Added to the played move's Maia probability inside the log, so a probability of 0 stays finite.
PLAYED_PROB_OFFSET: float = 0.01
# 259 D-05 fitted facepalm model: the output of scripts/blunder_check/fit_facepalm.py on the Phase 259
# plan 11 table (a fit on label sets 1-8), confirmed by the owner at D-15 on 2026-11-22 and pasted
# as printed, never hand-adjusted:
# `fit_facepalm.py --features reports/blunder-check/facepalm-features-2026-11-22.tsv
# --labels reports/blunder-check/facepalm-labels.tsv --out reports/blunder-check/facepalm-fit-2026-11-22.md`
# ("## Constants" block);
# `--check-constants` proves they still equal the refit (tests/scripts/test_fit_facepalm.py).
# z = intercept + played_coef * ln(played_prob + PLAYED_PROB_OFFSET) + loss_coef * loss
#     + missed_coef * lam * missed
#     + (loss > 0 ? reply_prob_coef * ln(reply_prob + OFFSET) : best_prob_coef * ln(best_prob + OFFSET))
FACEPALM_INTERCEPT: float = -1.4308
FACEPALM_PLAYED_COEF: float = -0.6065
FACEPALM_LOSS_COEF: float = 0.8379
FACEPALM_MISSED_COEF: float = 0.4971
FACEPALM_BEST_PROB_COEF: float = 2.0786
FACEPALM_REPLY_PROB_COEF: float = 0.9133
# Write-time material rule (259 D-05). These constants decide what the write-time hook and the line
# pass STORE in game_flaws.material_loss / material_missed. Changing any of them changes the stored
# numbers, so it needs a prod line pass with a new cutoff before the score reads them.
# Plies of the stored refutation line the loss reads (one depth for all ratings).
LINE_DEPTH: int = 3
# Cap of the material-loss input (pawn units).
LOSS_CAP: int = 5
# Loss value of a mate within LINE_DEPTH plies.
MATE_LOSS: int = 5
# Lower clip of the loss (None = unclipped).
FACEPALM_LOSS_FLOOR: int | None = 0
# Lower clip of the missed term (None = unclipped: a best line behind at depth 3 gives a
# negative gain), the cap, and the value of a best-line mate within LINE_DEPTH (a missed mate
# must not score as nothing missed).
FACEPALM_MISSED_FLOOR: int | None = 0
FACEPALM_MISSED_CAP: int = 5
FACEPALM_MISSED_MATE: int = 5
# Weight ratio between consecutive odd depths of the stored material inputs: the loss and the missed
# gain are the decaying mean over the odd depths 1, 3, 5, 7, 9 (259 D-03). Fixed by the owner in
# SEED-261115-agg, not fitted.
MATERIAL_DECAY_RATIO: float = 0.5
# 254 D-03 / D-04 loss-aversion knob: lambda multiplies the missed term only (0 = the loss-only
# score). Two constants so the consumers can diverge: the blunder-check drill selection (D-03,
# symmetric while GM Noel Studer's answer is pending) and the library (D-04: chip, filter,
# analysis move list, eval chart tooltip).
FACEPALM_DRILL_LAMBDA: float = 1.0
FACEPALM_LIBRARY_LAMBDA: float = 1.0
# Valid range of any lambda, enforced by both score twins.
FACEPALM_LAMBDA_MIN: float = 0.0
FACEPALM_LAMBDA_MAX: float = 1.0
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
# 250 D-12 window source mix: every slot independently draws a red herring, an own blunder or a
# foreign blunder at these shares (one third each), never a fixed 1-1-1 per three windows.
HERRING_SHARE: float = 1 / 3
OWN_BLUNDER_SHARE: float = 1 / 3
FOREIGN_BLUNDER_SHARE: float = 1 - HERRING_SHARE - OWN_BLUNDER_SHARE
# 250 D-16: a herring's origin is own with the same own / foreign ratio as blunders, so recognising
# one's own game gives nothing away.
HERRING_OWN_SHARE: float = OWN_BLUNDER_SHARE / (OWN_BLUNDER_SHARE + FOREIGN_BLUNDER_SHARE)
# 250 D-13: half-width of the pinned-Elo band around the user's level for a foreign window's mover.
FOREIGN_RATING_BAND: int = 150
# 249 D-02 windows per session.
BLUNDER_CHECK_SESSION_WINDOWS: int = 6
# 249 D-14 points: 1 per correctly judged safe move, 3 for flagging the blunder, plus the better
# move graded like personalized puzzles (249 D-17), so its full value is the good tier's points.
SAFE_POINTS: int = 1
BLUNDER_POINTS: int = 3
# A timeout on a good move takes this many points out of the sequence's pot (never below 0).
SAFE_TIMEOUT_PENALTY_POINTS: int = 1
BETTER_MOVE_POINTS: int = MOVE_TIER_POINTS["good"]

MissCase = Literal["allowed", "pure_miss", "mixed", "unclassified"]
SlotOrigin = Literal["own", "foreign"]

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
class SlotPlan:
    """One session slot as drawn (250 D-12, D-16): whose game it comes from and the window shape."""

    origin: SlotOrigin
    shape: WindowShape


@dataclass(frozen=True)
class MoveJudgement:
    """One user move: Good (no severity at all, so inaccuracies are excluded) and its pre-move ES."""

    ply: int
    good: bool
    es_before: float | None


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


def blunder_position_weights(length: int, hazard: float = HAZARD) -> dict[int, float]:
    """P(blunder at position k | the hazard fires within `length` moves), k in 1..length.

    Proportional to h * (1 - h)^(k - 1) and normalised to sum to 1. This is the 249 D-03 anti-leak
    rule: the position is conditional on the blunder existing, so a late position stays as likely
    as the hazard model says and the window length alone never reveals whether a blunder follows.
    """
    raw = {k: hazard * (1.0 - hazard) ** (k - 1) for k in range(1, length + 1)}
    total = sum(raw.values())
    return {k: value / total for k, value in raw.items()}


def draw_herring_shape(rng: random.Random) -> WindowShape:
    """A herring window: length uniform over WINDOW_LENGTHS, no blunder (250 D-12)."""
    return WindowShape(rng.choice(WINDOW_LENGTHS), None)


def draw_blunder_shape(rng: random.Random) -> WindowShape:
    """A blunder window (250 D-12): length uniform over WINDOW_LENGTHS, as for a herring, and the
    position drawn from `blunder_position_weights(length)`. Composition choice with the 249 hazard
    model: the length draw is shared by both kinds so length carries no information (249 D-03)."""
    length = rng.choice(WINDOW_LENGTHS)
    weights = blunder_position_weights(length)
    positions = sorted(weights)
    position = rng.choices(positions, weights=[weights[k] for k in positions])[0]
    return WindowShape(length, position)


def draw_slot_plan(rng: random.Random) -> SlotPlan:
    """Draw one slot independently (250 D-12, D-16): one uniform picks herring / own blunder /
    foreign blunder at the D-12 shares; a herring then draws its origin at HERRING_OWN_SHARE."""
    roll = rng.random()
    if roll < HERRING_SHARE:
        origin: SlotOrigin = "own" if rng.random() < HERRING_OWN_SHARE else "foreign"
        return SlotPlan(origin, draw_herring_shape(rng))
    if roll < HERRING_SHARE + OWN_BLUNDER_SHARE:
        return SlotPlan("own", draw_blunder_shape(rng))
    return SlotPlan("foreign", draw_blunder_shape(rng))


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
