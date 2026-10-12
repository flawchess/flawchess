"""Tactic-motif delta zone registry: backend source for per-bullet tactic zone constants.

Sibling of flaw_delta_zones.py (Phase 239 D-11). The backend is the single source of truth:
get_tactic_comparison embeds zone_lo / zone_hi / has_zone in every TacticBullet and the
frontend renders exactly what the registry stores. No TS codegen.

Units: per 100 games (you minus opponent count per game, times 100), matching the tactic
rates the endpoint returns (D-00h). Sign convention: negative delta = fewer tactics than
the opponent = good; the registry stores raw Q1/Q3 with no sign flip.

A registry value of None means the (family, side) has no viable benchmark zone (degenerate
IQR or too few non-zero users, D-06): the bullet gets has_zone False, zone_lo == zone_hi ==
0.0, and the UI draws no band and gives no verdict (D-11).

Phase 239 D-08/D-09 stopgap: blitz and bullet have no finished full-analysis benchmark
sample, so they read the rapid zones until /benchmarks section 5 is re-run with those
tranches. The mapping is the SAME ZONE_TC_FOR the flaw registry uses (one stopgap mapping
for both registries), silent in the UI and documented in reports/benchmark/benchmarks-latest.md.

Values come from reports/benchmark/benchmarks-latest.md section 5 (plan 239-07 writes them).
Until then every entry is None, which is exactly what users see today (no tactic zones).

TACTIC_FAMILIES is spelled out here, not derived from library_repository.FAMILY_TO_MOTIF_INTS,
because the schemas import this module and the repository imports the schemas (a derived
tuple would be an import cycle). tests/services/test_tactic_delta_zones.py pins that the two
stay identical in content and order.

This module is pure Python with no DB or I/O.
"""

from collections.abc import Mapping
from typing import Final, Literal

from app.schemas.normalization import TimeControlBucket
from app.services.flaw_delta_zones import ZONE_TC_FOR, ZoneBand, ZoneTc

TacticFamily = Literal[
    "fork",
    "skewer",
    "pin",
    "x_ray",
    "double_check",
    "discovered_check",
    "discovered_attack",
    "trapped_piece",
    "hanging",
    "mate",
    "deflection",
    "intermezzo",
    "interference",
    "capturing_defender",
    "attraction",
    "sacrifice",
    "en_passant",
    "under_promotion",
    "promotion",
]

# Payload order of the 19 families (identical to FAMILY_TO_MOTIF_INTS).
TACTIC_FAMILIES: Final[tuple[TacticFamily, ...]] = (
    "fork",
    "skewer",
    "pin",
    "x_ray",
    "double_check",
    "discovered_check",
    "discovered_attack",
    "trapped_piece",
    "hanging",
    "mate",
    "deflection",
    "intermezzo",
    "interference",
    "capturing_defender",
    "attraction",
    "sacrifice",
    "en_passant",
    "under_promotion",
    "promotion",
)

# Missed: a tactic you had and did not play. Allowed: a tactic you let the opponent play.
TacticSide = Literal["missed", "allowed"]
TACTIC_SIDES: Final[tuple[TacticSide, TacticSide]] = ("missed", "allowed")

# 38 entries (19 families x 2 sides). None = unviable, see module docstring.
TACTIC_DELTA_ZONES: Final[
    Mapping[tuple[TacticFamily, TacticSide], Mapping[ZoneTc, ZoneBand] | None]
] = {(family, side): None for family in TACTIC_FAMILIES for side in TACTIC_SIDES}


def tactic_delta_zone(
    family: TacticFamily, side: TacticSide, tc: TimeControlBucket
) -> ZoneBand | None:
    """Return the typical-range band for a (family, side) in a time control, or None.

    None means the family-side is unviable (has_zone False). The D-08 stopgap is applied:
    blitz and bullet read the rapid band.
    """
    zones = TACTIC_DELTA_ZONES[(family, side)]
    if zones is None:
        return None
    return zones[ZONE_TC_FOR[tc]]
