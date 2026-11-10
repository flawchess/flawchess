"""Pure calibration metrics for the blunder-check feature (SEED-261108-dk0, Phase 248).

Every function here is pure (no DB, no Maia, no I/O) so the report pipeline can feed it
from sampled rows or a cache file and every number in the report is reproducible.

Expected-score (ES) conventions come from the flaw pipeline's own
``_run_all_moves_pass`` output ``{ply: (mover, severity, es_before, es_after)}``, all in
the mover's point of view:
  - pre-move ES of a judged move q          = all_moves[q][2]
  - ES the user actually reached with move p = all_moves[p][3]   (``es_played``)
  - ES reference for a miss at ply p         = 1 - all_moves[p - 1][2], the user's ES
    before the opponent's previous move (what the user would have had without the gift).
"""

from __future__ import annotations

import statistics
from bisect import bisect_left, bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, TypedDict

from app.repositories.game_flaws_repository import _SEVERITY_INT  # noqa: PLC2701
from app.repositories.query_utils import mover_is_white_at_ply

# Private import by design: the threshold and the per-ply entry shape must be the classifier's
# own, never re-derived (precedent: scripts/remote_eval_worker.py imports _run_all_moves_pass).
from app.services.flaws_service import INACCURACY_DROP, _MoveEntry  # noqa: PLC2701
from app.services.maia_flaw_stats import RANK_BASE

# ---------------------------------------------------------------------------
# Named constants (no magic numbers)
# ---------------------------------------------------------------------------

# D-16 hazard model: probability that a user blunders on any given move inside a window.
HAZARD: float = 0.265
# Candidate herring window lengths (user moves) the hazard model averages over.
WINDOW_LENGTHS: tuple[int, ...] = (3, 4, 5)
# Plies of lead-in the sampler prepends before the blunder position.
LEAD_IN_PLIES: int = 3
# Latest window position at which a blunder is modelled (matches max(WINDOW_LENGTHS)).
MAX_BLUNDER_POSITION: int = 5
# Upper bound on the share of pure misses among supplied blunders.
MAX_MISS_SHARE: float = 0.30
# Lower edges (inclusive) of the Elo buckets above the open-ended "<800" bucket.
ELO_BUCKET_EDGES: tuple[int, ...] = (800, 1200, 1600, 2000, 2400)

MissCase = Literal["allowed", "pure_miss", "mixed", "unclassified"]
EloBucket = Literal["<800", "800-1199", "1200-1599", "1600-1999", "2000-2399", "2400+"]
Provenance = Literal["engine", "lichess"]

ELO_BUCKETS: tuple[EloBucket, ...] = (
    "<800",
    "800-1199",
    "1200-1599",
    "1600-1999",
    "2000-2399",
    "2400+",
)


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


# ---------------------------------------------------------------------------
# Per-move judgement
# ---------------------------------------------------------------------------


def user_move_judgements(
    all_moves: Mapping[int, _MoveEntry],
    move_plies: Sequence[int],
    user_is_white: bool,
) -> list[MoveJudgement]:
    """Judge the user's moves among move_plies (D-15): Good iff classified with severity None."""
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
    """Return (pre-move ES, es_played, es_ref) for the user's blunder at ply, all user POV (D-13)."""
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


def blunder_fits_position(
    preceding: Sequence[MoveJudgement],
    blunder_es_before: float | None,
    position: int,
    band_low: float,
    band_high: float,
) -> bool:
    """D-16: a blunder fits window position k iff its pre-move ES is in band and the k-1 user
    moves immediately before it are all Good and in band. preceding is in game order."""
    if not in_band(blunder_es_before, band_low, band_high):
        return False
    needed = position - 1
    if needed == 0:
        return True
    if len(preceding) < needed:
        return False
    return all(j.good and in_band(j.es_before, band_low, band_high) for j in preceding[-needed:])


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


# ---------------------------------------------------------------------------
# Findability (D-14)
# ---------------------------------------------------------------------------


class FindabilityInputs(TypedDict):
    """Maia numbers for one blunder: refutation pair (allowed) and best-move pair (pure miss)."""

    refutation_prob: float | None
    refutation_rank: int | None
    best_prob: float | None
    best_rank: int | None


class SupplyRates(TypedDict):
    """Per-Elo-bucket rates feeding the per-user supply estimate (D-23)."""

    non_pure_rate: float
    pure_rate: float
    fit_share: float


def elo_bucket(elo: float) -> EloBucket:
    """Map a pinned Elo to its bucket (lower edge inclusive)."""
    index = sum(1 for edge in ELO_BUCKET_EDGES if elo >= edge)
    return ELO_BUCKETS[index]


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
    """D-14: allowed tests the refutation pair at R, pure miss the best pair at X', mixed passes if either does."""
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
# Herring windows and supply (D-16, D-23)
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


def capped_blunder_supply(
    non_pure: float,
    pure: float,
    max_miss_share: float = MAX_MISS_SHARE,
) -> float:
    """non_pure + pure, with pure capped so it is at most max_miss_share of the total."""
    pure_cap = max_miss_share / (1.0 - max_miss_share) * non_pure
    return non_pure + min(pure, pure_cap)


def weighted_fit_share(
    fit_by_position: Mapping[int, float],
    normalized_weights: Mapping[int, float],
) -> float:
    """Hazard-weighted average of the per-position fit shares."""
    return sum(normalized_weights[k] * fit_by_position.get(k, 0.0) for k in normalized_weights)


def estimated_user_windows(
    counts_by_bucket: Mapping[EloBucket, int],
    rates_by_bucket: Mapping[EloBucket, SupplyRates],
) -> float:
    """D-23: exact per-user counts x per-bucket rates; buckets without rates contribute 0."""
    total = 0.0
    for bucket, count in counts_by_bucket.items():
        rates = rates_by_bucket.get(bucket)
        if rates is None:
            continue
        supply = capped_blunder_supply(count * rates["non_pure_rate"], count * rates["pure_rate"])
        total += supply * rates["fit_share"]
    return total


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------


def auc(good: Sequence[float], blunder: Sequence[float]) -> float | None:
    """P(good > blunder) + 0.5 * P(tie), O(n log n) via sorting. None when either side is empty."""
    if not good or not blunder:
        return None
    sorted_blunder = sorted(blunder)
    wins = 0.0
    for value in good:
        below = bisect_left(sorted_blunder, value)
        at_or_below = bisect_right(sorted_blunder, value)
        wins += below + 0.5 * (at_or_below - below)
    return wins / (len(good) * len(blunder))


def quartiles(values: Sequence[float]) -> tuple[float, float, float] | None:
    """(q1, median, q3) with the inclusive method; None for fewer than 2 values."""
    if len(values) < 2:
        return None
    q1, median, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return q1, median, q3


def flaw_control(
    all_moves: Mapping[int, _MoveEntry],
    stored: Mapping[int, int],
) -> tuple[int, int]:
    """Stored-vs-recomputed control: (plies where severity agrees, plies carrying a mistake/blunder in either).

    `stored` maps ply to the game_flaws SMALLINT severity. Inaccuracies are not stored flaws, so they
    are ignored on the recomputed side.
    """
    recomputed = {
        ply: _SEVERITY_INT[entry[1]]
        for ply, entry in all_moves.items()
        if entry[1] in _SEVERITY_INT
    }
    plies = set(recomputed) | set(stored)
    agree = sum(1 for ply in plies if recomputed.get(ply) == stored.get(ply))
    return agree, len(plies)
