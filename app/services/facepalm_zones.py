"""Facepalm zone registry: provisional per-TC typical bands for the three facepalm rows.

Backend is the single source of truth. The endpoint embeds zone_lo / zone_hi / has_zone in
every FacepalmBullet response so the frontend renders exactly what the registry stores. No TS
codegen.

PROVISIONAL and prod-derived, not benchmark-derived: the benchmark DB carries line material on
only 18% of blunders until the Phase 252 re-walk, prod on about 94%. SEED-261120-bzq replaces
these bands with benchmark-DB zones per Elo x TC. Regenerate after a facepalm refit, a change
of the stored material rule or a stats-cut change. Current numbers: the Phase 259 model
(FACEPALM_MODEL on the stored scalar inputs), measured 2026-11-22. Phase 262 (D-08) changed the
score (promotions count as material, the key-move gate is the type rule, refitted constants).
These bands were deliberately not re-derived: they stay the Phase 259 model's until Phase 252
concludes and the benchmark zones of SEED-261120-bzq replace them.

Basis: prod, non-guest users, human opponents, chess.com + lichess, the most recent 1000
games per user x TC within 36 months (RECENT_GAMES_PER_TC_CAP, RECENCY_WINDOW_MONTHS, the
Phase 258 snapshot window), analyzed games only (full_evals_completed_at), stats cut
FACEPALM_STATS_MIN 0.7, FACEPALM_LIBRARY_LAMBDA, the 257 type rule. Per user x TC the mean of
per-game paired deltas per 100 user moves (the _paired_series rule). A user x TC is kept with
at least 20 analyzed games (FLAW_COMPARISON_GATE) and at least 0.8 scored coverage on both
sides (FACEPALM_MIN_SCORED_COVERAGE). Users per TC: 88 / 395 / 486 / 125 (bullet / blitz /
rapid / classical). Each band is symmetric_band(q1, q3) of that TC's own quartiles: per TC, no
Elo keying, centred on 0 because the significance gate tests the gap against 0. Evidence:
.planning/quick/261121-ha7-preliminary-facepalm-iqr-bands-from-prod/261121-ha7-prod-quartiles.sql

Sign convention: negative delta = fewer facepalm blunders than the opponents = good. No sign
flip is stored; the UI draws lower (better) values on the LEFT.

The three types are never compared with each other: each type row has its own band from its
own distribution.

This module is pure Python with no DB or I/O. It must not import app.schemas.library (which
imports this module for FacepalmMetric).
"""

from collections.abc import Mapping
from typing import Final, Literal

from app.schemas.normalization import TimeControlBucket
from app.services.flaw_delta_zones import ZoneBand, symmetric_band

# The three facepalm rows of FlawComparisonTc.facepalm_bullets (257 D-12): the total and one row
# per type (D-04: a type is only ever paired with the same type of the opponents). Deliberately
# NOT part of FlawDeltaMetric / FLAW_DELTA_METRICS, which drive the 12-metric zone registry and
# the benchmark generator.
FacepalmMetric = Literal["facepalm", "facepalm_missed_win", "facepalm_allowed_loss"]
FACEPALM_METRICS: Final[tuple[FacepalmMetric, ...]] = (
    "facepalm",
    "facepalm_missed_win",
    "facepalm_allowed_loss",
)

# Per-TC prod quartiles (per 100 user moves, 3 dp), made symmetric by symmetric_band.
# Generated, not hand-tuned: re-derive from a new run.
FACEPALM_ZONES: Final[Mapping[FacepalmMetric, Mapping[TimeControlBucket, ZoneBand]]] = {
    "facepalm": {
        "bullet": symmetric_band(-0.320, +0.721),
        "blitz": symmetric_band(-0.216, +0.368),
        "rapid": symmetric_band(-0.311, +0.284),
        "classical": symmetric_band(-0.907, +0.130),
    },
    "facepalm_missed_win": {
        "bullet": symmetric_band(-0.104, +0.162),
        "blitz": symmetric_band(-0.098, +0.064),
        "rapid": symmetric_band(-0.078, +0.080),
        "classical": symmetric_band(-0.064, +0.097),
    },
    "facepalm_allowed_loss": {
        "bullet": symmetric_band(-0.325, +0.700),
        "blitz": symmetric_band(-0.195, +0.386),
        "rapid": symmetric_band(-0.317, +0.274),
        "classical": symmetric_band(-1.026, +0.041),
    },
}


def facepalm_zone(metric: FacepalmMetric, tc: TimeControlBucket) -> ZoneBand:
    """The provisional typical band of one facepalm row in one time control."""
    return FACEPALM_ZONES[metric][tc]
