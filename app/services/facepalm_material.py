"""facepalm_material.py - per-depth material series and aggregates of the facepalm inputs.

The material loss and the missed gain of a blunder are aggregated at WRITE time (259 D-05): the
writer reads the odd depths 1, 3, 5, 7, 9 of both stored 9-slot arrays (odd depths only, 254 D-17:
even slots are mid-exchange values) and stores the two scalars; query time never touches the
arrays. This module holds the pure Python aggregation:

- ``loss_by_depth``: the loss per odd depth of the played line;
- ``gain_by_depth``: the missed gain per odd depth (best vs played);
- ``decaying_mean``: the mean of a series weighted 1, 1/2, 1/4, ... (``MATERIAL_DECAY_RATIO``),
  renormalised over the depths that are known;
- ``first_stable``: the first value the next odd depth confirms, discounted by its onset index
  (``aggregate`` picks the aggregate of a material input).

The Python arrays are 0-based (``material_at_depth``). Pure, no I/O.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final, Literal, assert_never

from app.services.blunder_check_rules import LOSS_CAP, MATE_LOSS, MATERIAL_DECAY_RATIO
from app.services.line_material import LINE_LOSS_DEPTHS, material_at_depth

__all__ = [
    "MATERIAL_DECAY_WEIGHTS",
    "MATERIAL_DEPTHS",
    "AggregateInput",
    "MaterialSeries",
    "aggregate",
    "decaying_mean",
    "first_stable",
    "gain_by_depth",
    "loss_by_depth",
]

# Odd depths only: even slots are mid-exchange values (254 D-17).
MATERIAL_DEPTHS: Final[tuple[int, ...]] = LINE_LOSS_DEPTHS
# Weight of each depth in the decaying mean: ratio ** index (1, 1/2, 1/4, 1/8, 1/16).
MATERIAL_DECAY_WEIGHTS: Final[tuple[float, ...]] = tuple(
    MATERIAL_DECAY_RATIO**index for index in range(len(MATERIAL_DEPTHS))
)

# The material inputs that aggregate a per-depth series (every MaterialInput but "depth_3").
type AggregateInput = Literal["decaying_mean", "first_stable"]

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
    """The loss per odd depth: the depth-3 rule of ``loss_feature`` applied at every depth."""
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
    """The missed gain per odd depth: the depth-3 rule of ``missed_feature`` applied at every depth."""
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


def first_stable(series: MaterialSeries) -> float | None:
    """The first odd-depth value that the next odd depth confirms, discounted by its onset (A1).

    The first index i whose value and the value at i + 1 are both known and equal gives
    ``series[i] * MATERIAL_DECAY_WEIGHTS[i]``: onset depth 1 counts in full, depth 3 half, and so
    on. With no such pair the last known value counts, discounted by its own index. None when no
    depth is known. A None next to a value never forms a stable pair.
    """
    for index in range(len(series) - 1):
        value = series[index]
        if value is not None and value == series[index + 1]:
            return value * MATERIAL_DECAY_WEIGHTS[index]
    for index in reversed(range(len(series))):
        value = series[index]
        if value is not None:
            return value * MATERIAL_DECAY_WEIGHTS[index]
    return None


def aggregate(material_input: AggregateInput, series: MaterialSeries) -> float | None:
    """The aggregate of a per-depth series under an aggregate material input (never depth_3)."""
    match material_input:
        case "decaying_mean":
            return decaying_mean(series)
        case "first_stable":
            return first_stable(series)
        case _:
            assert_never(material_input)
