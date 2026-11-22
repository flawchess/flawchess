"""facepalm_material.py - per-depth material series and the decaying mean of the facepalm inputs.

The material loss and the missed gain of a blunder are aggregated at WRITE time (259 D-05): the
writer reads the odd depths 1, 3, 5, 7, 9 of the two 9-slot signed lists built by
``LineFacts.material_array()`` (in-memory only, never stored; list index N - 1 = depth N; only odd
depths are read, 254 D-17: even slots are mid-exchange values) and stores the two scalars
(``game_flaws.material_loss`` / ``material_missed``). Query time reads only those scalars. This
module holds the pure Python aggregation:

- ``loss_by_depth``: the loss per odd depth of the played line;
- ``gain_by_depth``: the missed gain per odd depth (best vs played);
- ``decaying_mean``: the mean of a series weighted 1, 1/2, 1/4, ... (``MATERIAL_DECAY_RATIO``),
  renormalised over the depths that are known.

Pure, no I/O.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from app.services.blunder_check_rules import LOSS_CAP, MATE_LOSS, MATERIAL_DECAY_RATIO
from app.services.line_material import LINE_LOSS_DEPTHS, material_at_depth

__all__ = [
    "MATERIAL_DECAY_WEIGHTS",
    "MATERIAL_DEPTHS",
    "MaterialSeries",
    "decaying_mean",
    "gain_by_depth",
    "loss_by_depth",
]

# Odd depths only: even slots are mid-exchange values (254 D-17).
MATERIAL_DEPTHS: Final[tuple[int, ...]] = LINE_LOSS_DEPTHS
# Weight of each depth in the decaying mean: ratio ** index (1, 1/2, 1/4, 1/8, 1/16).
MATERIAL_DECAY_WEIGHTS: Final[tuple[float, ...]] = tuple(
    MATERIAL_DECAY_RATIO**index for index in range(len(MATERIAL_DEPTHS))
)

# One value per entry of MATERIAL_DEPTHS; None = the line does not settle that depth.
type MaterialSeries = tuple[float | None, ...]


def _loss_at_depth(
    played_material: Sequence[int | None] | None,
    mate_ply: int | None,
    depth: int,
    loss_floor: int | None,
) -> float | None:
    """Loss at one depth: MATE_LOSS from the mate ply on, else the capped net loss, floored."""
    if mate_ply is not None and mate_ply <= depth:
        return float(MATE_LOSS)
    played = material_at_depth(played_material, depth)
    if played is None:
        return None
    capped = min(-played, LOSS_CAP)
    if loss_floor is not None:
        capped = max(capped, loss_floor)
    return float(capped)


def loss_by_depth(
    played_material: Sequence[int | None] | None,
    mate_ply: int | None,
    *,
    loss_floor: int | None,
) -> MaterialSeries:
    """The loss per odd depth: capped net loss, floored, MATE_LOSS from the mate ply on."""
    return tuple(
        _loss_at_depth(played_material, mate_ply, depth, loss_floor) for depth in MATERIAL_DEPTHS
    )


def _gain_at_depth(
    played_material: Sequence[int | None] | None,
    best_material: Sequence[int | None] | None,
    best_mate_ply: int | None,
    depth: int,
    *,
    missed_floor: int | None,
    missed_cap: int,
    missed_mate: int,
) -> float | None:
    """Missed gain at one depth: `missed_mate` from the best-line mate ply on, else the swing rule."""
    if best_mate_ply is not None and best_mate_ply <= depth:
        return float(missed_mate)
    played = material_at_depth(played_material, depth)
    best = material_at_depth(best_material, depth)
    if played is None or best is None:
        return None
    raw = best - max(0, played)
    if missed_floor is not None:
        raw = max(raw, missed_floor)
    return float(min(raw, missed_cap))


def gain_by_depth(
    played_material: Sequence[int | None] | None,
    best_material: Sequence[int | None] | None,
    best_mate_ply: int | None,
    *,
    missed_floor: int | None,
    missed_cap: int,
    missed_mate: int,
) -> MaterialSeries:
    """The missed gain per odd depth: best minus played, floored and capped, ``missed_mate`` from the best-line mate ply on."""
    return tuple(
        _gain_at_depth(
            played_material,
            best_material,
            best_mate_ply,
            depth,
            missed_floor=missed_floor,
            missed_cap=missed_cap,
            missed_mate=missed_mate,
        )
        for depth in MATERIAL_DEPTHS
    )


def decaying_mean(series: MaterialSeries) -> float | None:
    """Weighted mean over the known depths (weights renormalised over them); None when none known."""
    total = 0.0
    weight_sum = 0.0
    for value, weight in zip(series, MATERIAL_DECAY_WEIGHTS, strict=True):
        if value is None:
            continue
        total += weight * value
        weight_sum += weight
    return None if weight_sum == 0.0 else total / weight_sum
