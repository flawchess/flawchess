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

Basis (plan 239-06/07): benchmarks-latest.md section 5 on the full-analysis lane
(classical + rapid, snapshot run 2026-10-12) was recomputed and proposed, bands are
per 100 user moves, p25 / p75 of the per-user paired delta rounded outward (lo down,
hi up) to the 0.01 grid, one pooled band per metric (no metric reached keep-separate
on the TC or ELO axis, so no Elo keying). The owner accepted the proposal with ONE
edit (239-ZONE-PROPOSAL.md ## Accepted): the 12 flaw bands keep the previous live
values instead of the proposed 1.5x to 3.5x wider ones, because the widening was
mostly sampling noise from the lane's 100-games-per-user-per-TC cap (noise-only IQR
70% to 142% of the observed IQR). The values below are therefore the live
whole-cohort bands, identical for rapid and classical, while tactic_delta_zones.py
holds the full-analysis section 5 bands.

Phase 239 D-15 (UAT, 2026-10-13): every band is symmetric around 0, built by
symmetric_band() from the measured Q1/Q3 kept in the source: +-IQR/2, the half-width
rounded up to the 0.01 grid. The off-centre quartiles (e.g. low_clock -0.08 / +0.03)
came from rare, discrete per-user values and cohort selection, not a real typical
offset, and the D-14 significance gate tests the gap against 0.

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
