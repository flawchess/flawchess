"""Flaw-delta zone registry: authoritative backend source for per-bullet zone constants.

Backend is the single source of truth per Phase 115 D-07. The endpoint embeds
zone_lo / zone_hi / has_zone in every FlawBullet response so the frontend renders
exactly what the registry stores. No TS codegen: the frontend does not commit
these constants locally.

Phase 239 D-08/D-09 stopgap: blitz and bullet have no finished full-analysis
benchmark sample, so they read the rapid zones until the /benchmarks section 5
is re-run with those tranches. The mapping lives in ZONE_TC_FOR, is silent in
the UI, and is documented in reports/benchmark/benchmarks-latest.md section 5.

The registry is keyed metric -> zone TC -> band. A collapsed TC axis is just
identical values under both zone TCs. The values are hand-authored on a 0.01 grid
(the grid keeps a visible neutral band on the rare tags whose IQR is below 0.05; a
coarser grid snapped those bands to zero width).

Basis: each band is symmetric_band() applied to the live whole-cohort Q1/Q3 kept in
the source (per 100 user moves, per-user paired delta): +-IQR/2 around 0, the
half-width rounded up to the 0.01 grid (Phase 239 D-15). One pooled band per metric,
identical for rapid and classical. The section 5 full-analysis-lane values were not
adopted for flaws because the lane's 100-games-per-user-per-TC cap makes them mostly
sampling noise (239-ZONE-PROPOSAL.md ## Accepted); tactic_delta_zones.py does use the
lane. Bands are centred on 0 because the D-14 significance gate tests the gap against 0.

Sign convention: negative delta = fewer flaws than the opponent = good. No sign flip
is stored; the UI draws lower (better) values on the LEFT (D-14 direction flip).

This module is pure Python with no DB or I/O. All functions are synchronous
and side-effect free.
"""

from collections.abc import Mapping
import math
from dataclasses import dataclass
from typing import Final, Literal

from app.schemas.normalization import TimeControlBucket

FlawDeltaMetric = Literal[
    "mistake",
    "blunder",
    "low_clock",
    "hasty",
    "unrushed",
    "opening",
    "middlegame",
    "endgame_phase",
    "miss",
    "lucky",
    "reversed",
    "squandered",
]

# Display / payload order of the 12 metrics: severity, tempo, phase, opportunity, impact.
FLAW_DELTA_METRICS: Final[tuple[FlawDeltaMetric, ...]] = (
    "mistake",
    "blunder",
    "low_clock",
    "hasty",
    "unrushed",
    "opening",
    "middlegame",
    "endgame_phase",
    "miss",
    "lucky",
    "reversed",
    "squandered",
)

# Time controls that own a zone band. Blitz and bullet are not here (D-08).
ZoneTc = Literal["rapid", "classical"]

# D-08/D-09 stopgap: blitz and bullet read the rapid zones.
ZONE_TC_FOR: Final[Mapping[TimeControlBucket, ZoneTc]] = {
    "bullet": "rapid",
    "blitz": "rapid",
    "rapid": "rapid",
    "classical": "classical",
}


@dataclass(frozen=True)
class ZoneBand:
    """Typical-range bounds of one flaw-delta bullet, per 100 user moves.

    zone_lo / zone_hi: -h / +h with h = IQR / 2 of the per-user paired delta, rounded up
    to the 0.01 grid (D-15, symmetric_band).
    """

    zone_lo: float
    zone_hi: float


# Grid the band half-width is rounded up to (hundredths).
_BAND_GRID_STEPS_PER_UNIT: Final[int] = 100
# Rounds away float noise such as 28.000000000000004 before the ceiling.
_BAND_GRID_FLOAT_DIGITS: Final[int] = 6


def symmetric_band(q1: float, q3: float) -> ZoneBand:
    """+-IQR/2 around 0 from the measured quartiles, half-width rounded up to 0.01 (D-15)."""
    half_steps = math.ceil(
        round((q3 - q1) / 2 * _BAND_GRID_STEPS_PER_UNIT, _BAND_GRID_FLOAT_DIGITS)
    )
    half = half_steps / _BAND_GRID_STEPS_PER_UNIT
    return ZoneBand(zone_lo=-half, zone_hi=half)


# Phase 239 owner-accepted quartiles (239-ZONE-PROPOSAL.md ## Accepted): the live pooled
# Q1 / Q3, identical for both zone TCs, made symmetric by symmetric_band (D-15).
FLAW_DELTA_ZONES: Final[Mapping[FlawDeltaMetric, Mapping[ZoneTc, ZoneBand]]] = {
    # Severity family
    "mistake": {
        "rapid": symmetric_band(-0.23, +0.20),
        "classical": symmetric_band(-0.23, +0.20),
    },
    "blunder": {
        "rapid": symmetric_band(-0.31, +0.25),
        "classical": symmetric_band(-0.31, +0.25),
    },
    # Tempo family
    "low_clock": {
        "rapid": symmetric_band(-0.08, +0.03),
        "classical": symmetric_band(-0.08, +0.03),
    },
    "hasty": {
        "rapid": symmetric_band(-0.28, +0.18),
        "classical": symmetric_band(-0.28, +0.18),
    },
    "unrushed": {
        "rapid": symmetric_band(-0.38, +0.36),
        "classical": symmetric_band(-0.38, +0.36),
    },
    # Phase family
    "opening": {
        "rapid": symmetric_band(-0.15, +0.13),
        "classical": symmetric_band(-0.15, +0.13),
    },
    "middlegame": {
        "rapid": symmetric_band(-0.27, +0.23),
        "classical": symmetric_band(-0.27, +0.23),
    },
    "endgame_phase": {
        "rapid": symmetric_band(-0.12, +0.10),
        "classical": symmetric_band(-0.12, +0.10),
    },
    # Opportunity family
    "miss": {
        "rapid": symmetric_band(-0.11, +0.11),
        "classical": symmetric_band(-0.11, +0.11),
    },
    "lucky": {
        "rapid": symmetric_band(-0.09, +0.09),
        "classical": symmetric_band(-0.09, +0.09),
    },
    # Impact family
    "reversed": {
        "rapid": symmetric_band(-0.04, +0.04),
        "classical": symmetric_band(-0.04, +0.04),
    },
    "squandered": {
        "rapid": symmetric_band(-0.07, +0.08),
        "classical": symmetric_band(-0.07, +0.08),
    },
}


def flaw_delta_zone(metric: FlawDeltaMetric, tc: TimeControlBucket) -> ZoneBand:
    """Return the typical-range band for a metric in a time control (D-08 stopgap applied)."""
    return FLAW_DELTA_ZONES[metric][ZONE_TC_FOR[tc]]
