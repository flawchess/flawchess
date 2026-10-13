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

Sign convention: negative delta = fewer flaws than the opponent = good. The
registry stores raw Q1/Q3 values with no sign flip; the UI draws better to the
right.

This module is pure Python with no DB or I/O. All functions are synchronous
and side-effect free.
"""

from collections.abc import Mapping
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

    zone_lo: Q1 of the per-user paired delta (rounded to the 0.01 grid).
    zone_hi: Q3 of the per-user paired delta (rounded to the 0.01 grid).
    """

    zone_lo: float
    zone_hi: float


# Phase 239 owner-accepted values (239-ZONE-PROPOSAL.md ## Accepted): the live pooled
# bands, kept unchanged for both zone TCs. The tests pin them against that table.
FLAW_DELTA_ZONES: Final[Mapping[FlawDeltaMetric, Mapping[ZoneTc, ZoneBand]]] = {
    # Severity family
    "mistake": {
        "rapid": ZoneBand(zone_lo=-0.23, zone_hi=+0.20),
        "classical": ZoneBand(zone_lo=-0.23, zone_hi=+0.20),
    },
    "blunder": {
        "rapid": ZoneBand(zone_lo=-0.31, zone_hi=+0.25),
        "classical": ZoneBand(zone_lo=-0.31, zone_hi=+0.25),
    },
    # Tempo family
    "low_clock": {
        "rapid": ZoneBand(zone_lo=-0.08, zone_hi=+0.03),
        "classical": ZoneBand(zone_lo=-0.08, zone_hi=+0.03),
    },
    "hasty": {
        "rapid": ZoneBand(zone_lo=-0.28, zone_hi=+0.18),
        "classical": ZoneBand(zone_lo=-0.28, zone_hi=+0.18),
    },
    "unrushed": {
        "rapid": ZoneBand(zone_lo=-0.38, zone_hi=+0.36),
        "classical": ZoneBand(zone_lo=-0.38, zone_hi=+0.36),
    },
    # Phase family
    "opening": {
        "rapid": ZoneBand(zone_lo=-0.15, zone_hi=+0.13),
        "classical": ZoneBand(zone_lo=-0.15, zone_hi=+0.13),
    },
    "middlegame": {
        "rapid": ZoneBand(zone_lo=-0.27, zone_hi=+0.23),
        "classical": ZoneBand(zone_lo=-0.27, zone_hi=+0.23),
    },
    "endgame_phase": {
        "rapid": ZoneBand(zone_lo=-0.12, zone_hi=+0.10),
        "classical": ZoneBand(zone_lo=-0.12, zone_hi=+0.10),
    },
    # Opportunity family
    "miss": {
        "rapid": ZoneBand(zone_lo=-0.11, zone_hi=+0.11),
        "classical": ZoneBand(zone_lo=-0.11, zone_hi=+0.11),
    },
    "lucky": {
        "rapid": ZoneBand(zone_lo=-0.09, zone_hi=+0.09),
        "classical": ZoneBand(zone_lo=-0.09, zone_hi=+0.09),
    },
    # Impact family
    "reversed": {
        "rapid": ZoneBand(zone_lo=-0.04, zone_hi=+0.04),
        "classical": ZoneBand(zone_lo=-0.04, zone_hi=+0.04),
    },
    "squandered": {
        "rapid": ZoneBand(zone_lo=-0.07, zone_hi=+0.08),
        "classical": ZoneBand(zone_lo=-0.07, zone_hi=+0.08),
    },
}


def flaw_delta_zone(metric: FlawDeltaMetric, tc: TimeControlBucket) -> ZoneBand:
    """Return the typical-range band for a metric in a time control (D-08 stopgap applied)."""
    return FLAW_DELTA_ZONES[metric][ZONE_TC_FOR[tc]]
