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
from typing import Literal, TypedDict

from app.repositories.game_flaws_repository import _SEVERITY_INT  # noqa: PLC2701

# Private import by design: the per-ply entry shape must be the classifier's own, never re-derived.
from app.services.flaws_service import _MoveEntry  # noqa: PLC2701

# Phase 249: the selection rules live in the app (one implementation shared with the drill). They
# are re-exported here so the calibration report keeps importing them from this module.
from app.services.blunder_check_rules import (
    HAZARD,
    LEAD_IN_PLIES,
    MAX_BLUNDER_POSITION,
    WINDOW_LENGTHS,
    FindabilityInputs,
    HazardWeights,
    MissCase,
    MoveJudgement,
    blunder_es,
    blunder_fits_position,
    count_herring_windows,
    findable,
    hazard_position_weights,
    herring_flags,
    in_band,
    miss_case,
    user_move_judgements,
)

__all__ = [
    "ELO_BUCKETS",
    "ELO_BUCKET_EDGES",
    "HAZARD",
    "LEAD_IN_PLIES",
    "MAX_BLUNDER_POSITION",
    "MAX_MISS_SHARE",
    "WINDOW_LENGTHS",
    "EloBucket",
    "FindabilityInputs",
    "HazardWeights",
    "MissCase",
    "MoveJudgement",
    "Provenance",
    "SupplyRates",
    "auc",
    "blunder_es",
    "blunder_fits_position",
    "capped_blunder_supply",
    "count_herring_windows",
    "elo_bucket",
    "estimated_user_windows",
    "findable",
    "flaw_control",
    "hazard_position_weights",
    "herring_flags",
    "in_band",
    "miss_case",
    "quartiles",
    "user_move_judgements",
    "weighted_fit_share",
]

# ---------------------------------------------------------------------------
# Named constants (no magic numbers)
# ---------------------------------------------------------------------------

# Upper bound on the share of pure misses among supplied blunders (report-only, D-07 keeps it out of the app).
MAX_MISS_SHARE: float = 0.30
# Lower edges (inclusive) of the Elo buckets above the open-ended "<800" bucket.
ELO_BUCKET_EDGES: tuple[int, ...] = (800, 1200, 1600, 2000, 2400)

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


# ---------------------------------------------------------------------------
# Supply and bucket helpers (report only)
# ---------------------------------------------------------------------------


class SupplyRates(TypedDict):
    """Per-Elo-bucket rates feeding the per-user supply estimate (D-23)."""

    non_pure_rate: float
    pure_rate: float
    fit_share: float


def elo_bucket(elo: float) -> EloBucket:
    """Map a pinned Elo to its bucket (lower edge inclusive)."""
    index = sum(1 for edge in ELO_BUCKET_EDGES if elo >= edge)
    return ELO_BUCKETS[index]


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
