"""The set-8 sampler's view of the per-depth loss / missed-gain series (SEED-261115-agg).

The shipped implementation lives in ``app/services/facepalm_material.py``: the depths, the decay
ratio and weights and the weighted mean are imported from there, so the app, the fit and the
sampler share one decaying mean (Phase 256 D-06). This module stays as the set-8 draw used it
(``miss_labels.py --mode disagreement``, quick task 261116-mco): ``loss_series`` and
``gain_series`` keep the sampler's owner-spec integer series, with the per-depth gain floored at 0,
and ``decaying_mean`` takes a depth-keyed mapping. ``tests/scripts/test_decaying_mean.py`` pins
both series to the app's ``loss_by_depth`` / ``gain_by_depth`` (floor 0).

Only odd depths are used: even slots of the material arrays are mid-exchange values (Phase 254
D-17, ``app.services.line_material``). The decay ratio is fixed by the owner, not fitted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.services.blunder_check_rules import (
    FACEPALM_MISSED_CAP,
    FACEPALM_MISSED_MATE,
    LOSS_CAP,
    MATE_LOSS,
    MATERIAL_DECAY_RATIO,
)
from app.services.facepalm_material import (
    MATERIAL_DECAY_WEIGHTS,
    MATERIAL_DEPTHS,
)
from app.services.facepalm_material import decaying_mean as _app_decaying_mean
from app.services.line_material import material_at_depth

# Odd depths only: even slots are mid-exchange values (Phase 254 D-17).
DECAY_DEPTHS: tuple[int, ...] = MATERIAL_DEPTHS
# Weight ratio between consecutive odd depths, fixed by the owner (not fitted).
DECAY_RATIO: float = MATERIAL_DECAY_RATIO
DECAY_WEIGHTS: tuple[float, ...] = MATERIAL_DECAY_WEIGHTS


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
    """Weighted mean over the known depths (the app's `decaying_mean`); None when none known."""
    return _app_decaying_mean(tuple(series.get(depth) for depth in DECAY_DEPTHS))
