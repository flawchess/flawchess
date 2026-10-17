"""Flaw-delta zone registry: authoritative backend source for per-bullet zone constants.

Backend is the single source of truth. The endpoint embeds
zone_lo / zone_hi / has_zone in every FlawBullet response so the frontend renders
exactly what the registry stores. No TS codegen: the frontend does not commit
these constants locally.

The registry is keyed metric -> time control -> band, with its own band for each of
bullet, blitz, rapid and classical. The values are on a 0.01 grid
(the grid keeps a visible neutral band on the rare tags whose IQR is below 0.05; a
coarser grid snapped those bands to zero width).

Basis: the section 5 whole-cohort run of 2026-10-14T18:22Z (every eval'd game of a
selected user, all four TCs, up to 1000 games per user per TC, at least 20 games per
user x (ELO, TC) cell; per 100 user moves, per-user paired delta). Each band is
symmetric_band() of that TC's own Q1/Q3: +-IQR/2 around 0, the half-width rounded up to
the 0.01 grid. Per-TC everywhere is an owner decision (2026-10-14): the
Cohen's-d verdict tests a shift of the MEAN between TCs (every flaw TC d is
below 0.5), but a band is a SPREAD, and the per-TC IQRs differ 3x to 15x (bullet
narrowest, classical widest). A thin or degenerate TC level would fall back to the pooled
band; none did. No Elo keying. The full-analysis lane is not used for flaws (its
100-games-per-user cap makes the per-user means mostly sampling noise);
tactic_delta_zones.py does use the lane. Bands are centred on 0 because the
significance gate tests the gap against 0. Evidence: reports/benchmark/benchmarks-latest.md
section 5.

Sign convention: negative delta = fewer flaws than the opponent = good. No sign flip
is stored; the UI draws lower (better) values on the LEFT (direction flip).

The module also holds the crossed tempo x phase registry (TEMPO_PHASE_ZONES) for the
3x3 heatmap cells, kept apart from the 12 bullets.

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

# Tempo x phase crossed cells. Same spellings as the FlawDeltaMetric
# tags so the frontend reuses its FLAW_GAP_META labels. Defined here (not in
# app.schemas.library) because app.schemas.library imports this module.
FlawTempoMetric = Literal["low_clock", "hasty", "unrushed"]
FlawPhaseMetric = Literal["opening", "middlegame", "endgame_phase"]

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

# Time controls that own a TACTIC zone band (tactic_delta_zones.py). Blitz and bullet are
# not here: their full-analysis lane tranches are unfinished. The flaw and
# tempo x phase registries below are keyed by all four TCs and do not use these two names.
ZoneTc = Literal["rapid", "classical"]

# Stopgap for the tactic registry only: blitz and bullet read the rapid zones.
ZONE_TC_FOR: Final[Mapping[TimeControlBucket, ZoneTc]] = {
    "bullet": "rapid",
    "blitz": "rapid",
    "rapid": "rapid",
    "classical": "classical",
}


@dataclass(frozen=True)
class ZoneBand:
    """Typical-range bounds of one zone band, in the owning registry's unit (per 100 user
    moves for flaws, per 100 games for tactics).

    zone_lo / zone_hi: -h / +h with h = IQR / 2 of the per-user paired delta, rounded up
    to the 0.01 grid (symmetric_band).
    """

    zone_lo: float
    zone_hi: float


# Grid the band half-width is rounded up to (hundredths).
_BAND_GRID_STEPS_PER_UNIT: Final[int] = 100
# Rounds away float noise such as 28.000000000000004 before the ceiling.
_BAND_GRID_FLOAT_DIGITS: Final[int] = 6


def symmetric_band(q1: float, q3: float) -> ZoneBand:
    """+-IQR/2 around 0 from the measured quartiles, half-width rounded up to 0.01."""
    half_steps = math.ceil(
        round((q3 - q1) / 2 * _BAND_GRID_STEPS_PER_UNIT, _BAND_GRID_FLOAT_DIGITS)
    )
    half = half_steps / _BAND_GRID_STEPS_PER_UNIT
    return ZoneBand(zone_lo=-half, zone_hi=half)


# Per-TC quartiles (per 100 user moves, 3 dp) from the 2026-10-14 section 5 run, made
# symmetric by symmetric_band. Generated, not hand-tuned: re-derive from a new run.
FLAW_DELTA_ZONES: Final[Mapping[FlawDeltaMetric, Mapping[TimeControlBucket, ZoneBand]]] = {
    # Severity family
    "mistake": {
        "bullet": symmetric_band(-0.089, +0.102),
        "blitz": symmetric_band(-0.234, +0.173),
        "rapid": symmetric_band(-0.357, +0.217),
        "classical": symmetric_band(-0.539, +0.410),
    },
    "blunder": {
        "bullet": symmetric_band(-0.104, +0.153),
        "blitz": symmetric_band(-0.261, +0.227),
        "rapid": symmetric_band(-0.420, +0.254),
        "classical": symmetric_band(-0.617, +0.443),
    },
    # Tempo family
    "low_clock": {
        "bullet": symmetric_band(-0.034, +0.026),
        "blitz": symmetric_band(-0.120, +0.072),
        "rapid": symmetric_band(-0.091, +0.038),
        "classical": symmetric_band(-0.068, +0.000),
    },
    "hasty": {
        "bullet": symmetric_band(-0.088, +0.063),
        "blitz": symmetric_band(-0.195, +0.171),
        "rapid": symmetric_band(-0.575, +0.284),
        "classical": symmetric_band(-1.278, +0.525),
    },
    "unrushed": {
        "bullet": symmetric_band(-0.142, +0.186),
        "blitz": symmetric_band(-0.406, +0.305),
        "rapid": symmetric_band(-0.546, +0.477),
        "classical": symmetric_band(-0.873, +0.888),
    },
    # Phase family
    "opening": {
        "bullet": symmetric_band(-0.069, +0.066),
        "blitz": symmetric_band(-0.152, +0.134),
        "rapid": symmetric_band(-0.227, +0.168),
        "classical": symmetric_band(-0.524, +0.283),
    },
    "middlegame": {
        "bullet": symmetric_band(-0.098, +0.125),
        "blitz": symmetric_band(-0.238, +0.215),
        "rapid": symmetric_band(-0.366, +0.223),
        "classical": symmetric_band(-0.421, +0.408),
    },
    "endgame_phase": {
        "bullet": symmetric_band(-0.040, +0.052),
        "blitz": symmetric_band(-0.124, +0.085),
        "rapid": symmetric_band(-0.159, +0.117),
        "classical": symmetric_band(-0.175, +0.198),
    },
    # Opportunity family
    "miss": {
        "bullet": symmetric_band(-0.056, +0.062),
        "blitz": symmetric_band(-0.127, +0.094),
        "rapid": symmetric_band(-0.150, +0.133),
        "classical": symmetric_band(-0.260, +0.239),
    },
    "lucky": {
        "bullet": symmetric_band(-0.044, +0.044),
        "blitz": symmetric_band(-0.085, +0.099),
        "rapid": symmetric_band(-0.113, +0.119),
        "classical": symmetric_band(-0.187, +0.211),
    },
    # Impact family
    "reversed": {
        "bullet": symmetric_band(-0.023, +0.019),
        "blitz": symmetric_band(-0.042, +0.044),
        "rapid": symmetric_band(-0.060, +0.056),
        "classical": symmetric_band(-0.071, +0.095),
    },
    "squandered": {
        "bullet": symmetric_band(-0.038, +0.038),
        "blitz": symmetric_band(-0.073, +0.073),
        "rapid": symmetric_band(-0.092, +0.091),
        "classical": symmetric_band(-0.147, +0.158),
    },
}


def flaw_delta_zone(metric: FlawDeltaMetric, tc: TimeControlBucket) -> ZoneBand:
    """Return the typical-range band for a metric in a time control."""
    return FLAW_DELTA_ZONES[metric][tc]


# Benchmark bands for the crossed tempo x phase heatmap cells.
#
# Basis and rule: the same section 5 whole-cohort run and per-TC rule as FLAW_DELTA_ZONES,
# measured by chapter5 section 5.16. Viability
# rule from chapter5 (pooled IQR not degenerate AND at least 50% of user-cells with a player
# event): 7 of 9 cells pass. low_clock x opening (1.7% nonzero, degenerate) and low_clock x
# middlegame (46.5% nonzero) have no band (None).
#
# Deliberately separate from FLAW_DELTA_METRICS / FLAW_DELTA_ZONES, which drive the 12
# bullets. Keys are (tempo, phase), phase-major.
_UNBANDED: Final[Mapping[TimeControlBucket, ZoneBand | None]] = {
    "bullet": None,
    "blitz": None,
    "rapid": None,
    "classical": None,
}

TEMPO_PHASE_ZONES: Final[
    Mapping[tuple[FlawTempoMetric, FlawPhaseMetric], Mapping[TimeControlBucket, ZoneBand | None]]
] = {
    # Opening
    ("low_clock", "opening"): _UNBANDED,
    ("hasty", "opening"): {
        "bullet": symmetric_band(-0.049, +0.030),
        "blitz": symmetric_band(-0.095, +0.060),
        "rapid": symmetric_band(-0.205, +0.109),
        "classical": symmetric_band(-0.627, +0.203),
    },
    ("unrushed", "opening"): {
        "bullet": symmetric_band(-0.057, +0.062),
        "blitz": symmetric_band(-0.107, +0.125),
        "rapid": symmetric_band(-0.168, +0.189),
        "classical": symmetric_band(-0.325, +0.378),
    },
    # Middlegame
    ("low_clock", "middlegame"): _UNBANDED,
    ("hasty", "middlegame"): {
        "bullet": symmetric_band(-0.034, +0.031),
        "blitz": symmetric_band(-0.096, +0.086),
        "rapid": symmetric_band(-0.287, +0.146),
        "classical": symmetric_band(-0.579, +0.378),
    },
    ("unrushed", "middlegame"): {
        "bullet": symmetric_band(-0.094, +0.120),
        "blitz": symmetric_band(-0.259, +0.178),
        "rapid": symmetric_band(-0.331, +0.261),
        "classical": symmetric_band(-0.499, +0.583),
    },
    # Endgame
    ("low_clock", "endgame_phase"): {
        "bullet": symmetric_band(-0.021, +0.019),
        "blitz": symmetric_band(-0.077, +0.055),
        "rapid": symmetric_band(-0.069, +0.037),
        "classical": symmetric_band(-0.045, +0.000),
    },
    ("hasty", "endgame_phase"): {
        "bullet": symmetric_band(-0.020, +0.021),
        "blitz": symmetric_band(-0.058, +0.054),
        "rapid": symmetric_band(-0.141, +0.088),
        "classical": symmetric_band(-0.193, +0.146),
    },
    ("unrushed", "endgame_phase"): {
        "bullet": symmetric_band(-0.040, +0.045),
        "blitz": symmetric_band(-0.118, +0.081),
        "rapid": symmetric_band(-0.121, +0.112),
        "classical": symmetric_band(-0.134, +0.181),
    },
}


def tempo_phase_zone(
    tempo: FlawTempoMetric, phase: FlawPhaseMetric, tc: TimeControlBucket
) -> ZoneBand | None:
    """Typical-range band of a crossed cell in a time control, None if unbanded."""
    return TEMPO_PHASE_ZONES[(tempo, phase)][tc]
