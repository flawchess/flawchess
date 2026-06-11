"""Flaw-delta zone registry: authoritative backend source for per-bullet zone constants.

Backend is the single source of truth per Phase 115 D-07. The endpoint embeds
zone_lo / zone_hi / domain in every FlawBullet response so the frontend renders
exactly what the registry stores. No TS codegen — the frontend does not commit
these constants locally.

This module is pure Python with no DB or I/O. All functions are synchronous
and side-effect free.
"""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class FlawDeltaZoneSpec:
    """Zone bounds and axis domain for one flaw-delta bullet.

    zone_lo: Q1 in pp (§5 pooled benchmark, rounded to a 0.01 grid).
    zone_hi: Q3 in pp (§5 pooled benchmark, rounded to a 0.01 grid).
    domain: axis half-width in pp (hand-set from p05/p95 per D-04).

    The 0.01 rounding grid keeps a visible neutral band on the rare tags
    (reversed, low_clock_miss) whose IQR is below 0.05 pp; a coarser 0.1 grid
    snapped those bands to zero width.

    Sign convention (D-08): negative delta = fewer flaws than opponent = good.
    The MiniBulletChart invertColors mode handles color inversion; the registry
    stores raw Q1/Q3 values with no sign flip.
    """

    zone_lo: float
    zone_hi: float
    domain: float


FLAW_DELTA_ZONES: Mapping[str, FlawDeltaZoneSpec] = {
    # Severity family
    "flaw_rate": FlawDeltaZoneSpec(zone_lo=-0.48, zone_hi=+0.36, domain=2.0),
    "mistake": FlawDeltaZoneSpec(zone_lo=-0.23, zone_hi=+0.20, domain=1.0),
    "blunder": FlawDeltaZoneSpec(zone_lo=-0.31, zone_hi=+0.25, domain=1.4),
    # Tempo family
    "low_clock": FlawDeltaZoneSpec(zone_lo=-0.08, zone_hi=+0.03, domain=0.5),
    "hasty": FlawDeltaZoneSpec(zone_lo=-0.28, zone_hi=+0.18, domain=1.2),
    "unrushed": FlawDeltaZoneSpec(zone_lo=-0.38, zone_hi=+0.36, domain=1.7),
    # Phase family
    "opening": FlawDeltaZoneSpec(zone_lo=-0.15, zone_hi=+0.13, domain=0.8),
    "middlegame": FlawDeltaZoneSpec(zone_lo=-0.27, zone_hi=+0.23, domain=1.3),
    "endgame_phase": FlawDeltaZoneSpec(zone_lo=-0.12, zone_hi=+0.10, domain=0.5),
    # Opportunity family
    "miss": FlawDeltaZoneSpec(zone_lo=-0.11, zone_hi=+0.11, domain=0.5),
    "lucky": FlawDeltaZoneSpec(zone_lo=-0.09, zone_hi=+0.09, domain=0.5),
    # Impact family
    "reversed": FlawDeltaZoneSpec(zone_lo=-0.04, zone_hi=+0.04, domain=0.3),
    "squandered": FlawDeltaZoneSpec(zone_lo=-0.07, zone_hi=+0.08, domain=0.4),
    # Combo family
    "hasty_miss": FlawDeltaZoneSpec(zone_lo=-0.09, zone_hi=+0.06, domain=0.4),
    "low_clock_miss": FlawDeltaZoneSpec(zone_lo=-0.02, zone_hi=+0.01, domain=0.2),
}
