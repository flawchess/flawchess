"""Per-depth loss / missed-gain series and their decaying mean (SEED-261115-agg).

The shipped facepalm score reads the material of the played and the best line at depth 3 only.
The seed asks whether a mean over the stored depths 1, 3, 5, 7 and 9, weighted 1, 1/2, 1/4, 1/8,
1/16 (normalised over the depths that are known), tracks the owner's labels better. This module
holds that arithmetic once, pure (no I/O, no DB, no Maia), so the set-8 sampler
(``miss_labels.py --mode disagreement``) can find the rows where depth 3 and the decaying mean
disagree. The later refit phase may reuse or move it.

Only odd depths are used: even slots of the material arrays are mid-exchange values (Phase 254
D-17, ``app.services.line_material``). The decay ratio is fixed by the owner, not fitted.

Deliberate difference from the shipped score: the per-depth gain is floored at 0 per the owner's
spec, while the shipped missed term has ``FACEPALM_MISSED_FLOOR`` None (a best line behind the
played one gives a negative raw value). Settling that is the refit's job; the shipped constants
and ``app/services/facepalm_score.py`` are untouched.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.services.blunder_check_rules import (
    FACEPALM_MISSED_CAP,
    FACEPALM_MISSED_MATE,
    LOSS_CAP,
    MATE_LOSS,
)
from app.services.line_material import LINE_LOSS_DEPTHS, material_at_depth

# Odd depths only: even slots are mid-exchange values (Phase 254 D-17).
DECAY_DEPTHS: tuple[int, ...] = LINE_LOSS_DEPTHS
# Weight ratio between consecutive odd depths, fixed by the owner (not fitted).
DECAY_RATIO: float = 0.5
DECAY_WEIGHTS: tuple[float, ...] = tuple(DECAY_RATIO**index for index in range(len(DECAY_DEPTHS)))


def loss_series(
    played_material: Sequence[int | None] | None, played_mate_ply: int | None
) -> dict[int, int | None]:
    """Loss per odd depth: MATE_LOSS from the played-line mate ply on, else -material capped.

    `played_material` is the signed 9-slot array of the played line (positive = blunderer up).
    A depth the stored line does not settle is None.
    """
    series: dict[int, int | None] = {}
    for depth in DECAY_DEPTHS:
        if played_mate_ply is not None and played_mate_ply <= depth:
            series[depth] = MATE_LOSS
            continue
        material = material_at_depth(played_material, depth)
        series[depth] = None if material is None else min(LOSS_CAP, max(0, -material))
    return series


def gain_series(
    played_material: Sequence[int | None] | None,
    best_material: Sequence[int | None] | None,
    best_mate_ply: int | None,
) -> dict[int, int | None]:
    """Missed gain per odd depth: best - max(0, played), floored at 0 and capped.

    A best-line mate (ply after which the opponent is mated, best move = ply 0) counts
    FACEPALM_MISSED_MATE from that ply on. None when either slot is unknown at a depth.
    """
    series: dict[int, int | None] = {}
    for depth in DECAY_DEPTHS:
        if best_mate_ply is not None and best_mate_ply <= depth:
            series[depth] = FACEPALM_MISSED_MATE
            continue
        played = material_at_depth(played_material, depth)
        best = material_at_depth(best_material, depth)
        if played is None or best is None:
            series[depth] = None
            continue
        series[depth] = min(FACEPALM_MISSED_CAP, max(0, best - max(0, played)))
    return series


def decaying_mean(series: Mapping[int, int | None]) -> float | None:
    """Weighted mean over the known depths (weights renormalised over them); None when none known."""
    total = 0.0
    weight_sum = 0.0
    for depth, weight in zip(DECAY_DEPTHS, DECAY_WEIGHTS, strict=True):
        value = series.get(depth)
        if value is None:
            continue
        total += weight * value
        weight_sum += weight
    return None if weight_sum == 0.0 else total / weight_sum
