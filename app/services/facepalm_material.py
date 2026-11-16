"""facepalm_material.py - per-depth material series and aggregates of the facepalm score (Phase 256).

The facepalm score reads the material of the played and the best line. Depth 3 alone is the
Phase 254 input; the aggregate inputs read the odd depths 1, 3, 5, 7, 9 of both stored 9-slot
arrays (odd depths only, 254 D-17: even slots are mid-exchange values). This module holds, for
each series and aggregate, one Python function and one SQL builder:

- ``loss_by_depth`` / ``loss_by_depth_sql``: the loss per odd depth of the played line;
- ``gain_by_depth`` / ``gain_by_depth_sql``: the missed gain per odd depth (best vs played);
- ``decaying_mean`` / ``decaying_mean_sql``: the mean of a series weighted 1, 1/2, 1/4, ...
  (``MATERIAL_DECAY_RATIO``), renormalised over the depths that are known;
- ``first_stable`` / ``first_stable_sql``: the first value the next odd depth confirms, discounted
  by its onset index (``aggregate`` / ``aggregate_sql`` pick the aggregate of a material input);
- ``loses`` / ``loses_sql``: the "loses material" test of the gated spread forms (D-11).

The SQL builders are unrolled over the depths (no ``unnest``, no subquery), so a reader binds the
expression once and uses it in SELECT and WHERE. Operands are typed Float so PostgreSQL divides in
double precision like Python, and an ``IS NULL`` CASE branch always precedes ``least`` /
``greatest`` because PostgreSQL skips NULLs there. PostgreSQL arrays are 1-based, so ``played[d]``
is depth d; the Python arrays are 0-based (``material_at_depth``).

Python and SQL are kept in step by ``tests/services/test_facepalm_score.py``: if either side
changes, update the other. Pure, no I/O.
"""

from __future__ import annotations

import operator
from collections.abc import Sequence
from functools import reduce
from typing import Any, Final, Literal, assert_never

from sqlalchemy import ColumnElement, Float, and_, case, cast, func, literal, null, or_

from app.services.blunder_check_rules import (
    LINE_DEPTH,
    LOSS_CAP,
    MATE_LOSS,
    MATERIAL_DECAY_RATIO,
)
from app.services.line_material import LINE_LOSS_DEPTHS, LINE_MATERIAL_SLOTS, material_at_depth

__all__ = [
    "MATERIAL_DECAY_WEIGHTS",
    "MATERIAL_DEPTHS",
    "AggregateInput",
    "MaterialSeries",
    "aggregate",
    "aggregate_sql",
    "decaying_mean",
    "decaying_mean_sql",
    "first_stable",
    "first_stable_sql",
    "gain_by_depth",
    "gain_by_depth_sql",
    "loses",
    "loses_sql",
    "loss_by_depth",
    "loss_by_depth_sql",
    "single_depth_material",
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


def single_depth_material(value: int | None, depth: int = LINE_DEPTH) -> tuple[int | None, ...]:
    """A 9-slot array that knows only `depth` (legacy depth-3 rows and test inputs).

    Every other slot is None, so "depth_3" and "decaying_mean" read exactly `value` at `depth` and
    score like the depth-3 scalar (as long as no mate lies beyond LINE_DEPTH, which would add
    per-depth mate values to the aggregate inputs). "first_stable" has no stable pair on a lone
    slot and discounts it by its onset index (depth 3: half).
    """
    return tuple(value if slot == depth else None for slot in range(1, LINE_MATERIAL_SLOTS + 1))


def loses(loss: float, gate: float | None) -> bool:
    """The "loses material" test of the gated spread forms (D-11).

    `gate` None: any loss above 0. A number g: loss >= g (`>=`, so a one-pawn loss at every depth,
    which averages exactly 1.0, counts as losing under g = 1.0).
    """
    return loss > 0 if gate is None else loss >= gate


def _loss_at_depth_sql(
    played: Any, mate_ply: Any, depth: int, loss_floor: int | None
) -> ColumnElement[Any]:
    slot = played[depth]
    capped = func.least(-cast(slot, Float), literal(float(LOSS_CAP), Float))
    if loss_floor is not None:
        capped = func.greatest(capped, literal(float(loss_floor), Float))
    # IS NULL before least/greatest: PostgreSQL skips NULLs there.
    return case(
        (mate_ply <= depth, literal(float(MATE_LOSS), Float)),
        (slot.is_(None), null()),
        else_=capped,
    )


def loss_by_depth_sql(
    played: Any, mate_ply: Any, *, loss_floor: int | None
) -> tuple[ColumnElement[Any], ...]:
    """SQL twin of `loss_by_depth`: one expression per odd depth (NULL = not settled)."""
    return tuple(
        _loss_at_depth_sql(played, mate_ply, depth, loss_floor) for depth in MATERIAL_DEPTHS
    )


def _gain_at_depth_sql(
    played: Any,
    best: Any,
    best_mate_ply: Any,
    depth: int,
    *,
    missed_floor: int | None,
    missed_cap: int,
    missed_mate: int,
) -> ColumnElement[Any]:
    played_slot = played[depth]
    best_slot = best[depth]
    played_value = cast(played_slot, Float)
    played_positive = case((played_value > 0, played_value), else_=literal(0.0, Float))
    raw = cast(best_slot, Float) - played_positive
    if missed_floor is not None:
        raw = func.greatest(raw, literal(float(missed_floor), Float))
    return case(
        (best_mate_ply <= depth, literal(float(missed_mate), Float)),
        (or_(played_slot.is_(None), best_slot.is_(None)), null()),
        else_=func.least(raw, literal(float(missed_cap), Float)),
    )


def gain_by_depth_sql(
    played: Any,
    best: Any,
    best_mate_ply: Any,
    *,
    missed_floor: int | None,
    missed_cap: int,
    missed_mate: int,
) -> tuple[ColumnElement[Any], ...]:
    """SQL twin of `gain_by_depth`: one expression per odd depth (NULL = not settled)."""
    return tuple(
        _gain_at_depth_sql(
            played,
            best,
            best_mate_ply,
            depth,
            missed_floor=missed_floor,
            missed_cap=missed_cap,
            missed_mate=missed_mate,
        )
        for depth in MATERIAL_DEPTHS
    )


def decaying_mean_sql(series: Sequence[ColumnElement[Any]]) -> ColumnElement[Any]:
    """SQL twin of `decaying_mean`: NULL when no depth is known (the denominator is 0.0)."""
    weighted = [
        literal(weight, Float) * func.coalesce(value, literal(0.0, Float))
        for value, weight in zip(series, MATERIAL_DECAY_WEIGHTS, strict=True)
    ]
    known_weights = [
        case((value.is_(None), literal(0.0, Float)), else_=literal(weight, Float))
        for value, weight in zip(series, MATERIAL_DECAY_WEIGHTS, strict=True)
    ]
    numerator = reduce(operator.add, weighted)
    denominator = reduce(operator.add, known_weights)
    return case((denominator == 0.0, null()), else_=numerator / denominator)


def first_stable_sql(series: Sequence[ColumnElement[Any]]) -> ColumnElement[Any]:
    """SQL twin of `first_stable`: one CASE, stable pairs in order, then the fallbacks.

    The first four branches are the pairs ``value IS NOT NULL AND value = next`` (a NULL next
    value makes the comparison NULL, so it never forms a pair); the next five are the fallbacks
    from the last depth backwards. Weights are powers of two over small integers, so both twins
    are exact. NULL when no depth is known.
    """
    last = len(series) - 1
    stable = [
        (
            and_(series[index].isnot(None), series[index] == series[index + 1]),
            series[index] * literal(MATERIAL_DECAY_WEIGHTS[index], Float),
        )
        for index in range(last)
    ]
    fallback = [
        (series[index].isnot(None), series[index] * literal(MATERIAL_DECAY_WEIGHTS[index], Float))
        for index in reversed(range(last + 1))
    ]
    return case(*stable, *fallback, else_=null())


def aggregate_sql(
    material_input: AggregateInput, series: Sequence[ColumnElement[Any]]
) -> ColumnElement[Any]:
    """SQL twin of `aggregate`."""
    match material_input:
        case "decaying_mean":
            return decaying_mean_sql(series)
        case "first_stable":
            return first_stable_sql(series)
        case _:
            assert_never(material_input)


def loses_sql(loss: ColumnElement[Any], gate: float | None) -> ColumnElement[bool]:
    """SQL twin of `loses`."""
    return loss > 0 if gate is None else loss >= gate
