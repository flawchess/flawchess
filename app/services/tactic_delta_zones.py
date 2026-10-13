"""Tactic-motif delta zone registry: backend source for per-bullet tactic zone constants.

Sibling of flaw_delta_zones.py (Phase 239 D-11). The backend is the single source of truth:
get_tactic_comparison embeds zone_lo / zone_hi / has_zone in every TacticBullet and the
frontend renders exactly what the registry stores. No TS codegen.

Units: per 100 games (you minus opponent count per game, times 100), matching the tactic
rates the endpoint returns (D-00h). Sign convention: negative delta = fewer tactics than
the opponent = good.

A registry value of None means the (family, side) has no viable benchmark zone (degenerate
IQR or too few non-zero users, D-06): the bullet gets has_zone False, zone_lo == zone_hi ==
0.0, and the UI draws no band (D-11); the cell is coloured only on its 99% significance (D-16).

Phase 239 D-08/D-09 stopgap: blitz and bullet have no finished full-analysis benchmark
sample, so they read the rapid zones until /benchmarks section 5 is re-run with those
tranches. The mapping is the SAME ZONE_TC_FOR the flaw registry uses (one stopgap mapping
for both registries), silent in the UI and documented in reports/benchmark/benchmarks-latest.md.

Basis: each band is symmetric_band() applied to the section 5 full-analysis-lane Q1/Q3
kept in the source (reports/benchmark/benchmarks-latest.md, classical + rapid games with
full evals, PVs and blobs, at most 100 games per user per TC, per-user mean over at least
20 games, snapshot run 2026-10-12): +-IQR/2 around 0, the half-width rounded up to the
0.01 grid (D-15). One pooled band per metric, identical for rapid and classical; blitz and
bullet read rapid (the D-08 stopgap above).

has_zone rule: a (family, side) gets a band only when the pooled IQR is not degenerate (p25 <
p75) AND at least 50% of user-cells are non-zero. Exactly 9 of 38 pass; the owner accepted that
set as proposed at the plan 239-06 checkpoint (see 239-ZONE-PROPOSAL.md ## Accepted). The other
29 stay None.

TACTIC_FAMILIES is spelled out here, not derived from library_repository.FAMILY_TO_MOTIF_INTS,
because the schemas import this module and the repository imports the schemas (a derived
tuple would be an import cycle). tests/services/test_tactic_delta_zones.py pins that the two
stay identical in content and order.

This module is pure Python with no DB or I/O.
"""

from collections.abc import Mapping
from typing import Final, Literal

from app.schemas.normalization import TimeControlBucket
from app.services.flaw_delta_zones import ZONE_TC_FOR, ZoneBand, ZoneTc, symmetric_band

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


def _both_tcs(q1: float, q3: float) -> Mapping[ZoneTc, ZoneBand]:
    """One pooled symmetric band shared by both zone TCs (the TC axis collapsed, D-15)."""
    band = symmetric_band(q1, q3)
    return {"rapid": band, "classical": band}


# Accepted viable bands (per 100 games), copied from 239-ZONE-PROPOSAL.md ## Accepted.
_VIABLE_TACTIC_ZONES: Final[Mapping[tuple[TacticFamily, TacticSide], Mapping[ZoneTc, ZoneBand]]] = {
    ("fork", "missed"): _both_tcs(-2.21, +2.13),
    ("fork", "allowed"): _both_tcs(-4.12, +3.23),
    ("pin", "missed"): _both_tcs(-1.42, +1.89),
    ("pin", "allowed"): _both_tcs(-2.86, +2.05),
    ("discovered_attack", "allowed"): _both_tcs(-1.24, +1.06),
    ("hanging", "missed"): _both_tcs(-1.13, +1.48),
    ("hanging", "allowed"): _both_tcs(-5.11, +3.04),
    ("mate", "missed"): _both_tcs(-2.18, +2.90),
    ("mate", "allowed"): _both_tcs(-7.00, +4.09),
}

# 38 entries (19 families x 2 sides). None = unviable, see module docstring.
TACTIC_DELTA_ZONES: Final[
    Mapping[tuple[TacticFamily, TacticSide], Mapping[ZoneTc, ZoneBand] | None]
] = {
    (family, side): _VIABLE_TACTIC_ZONES.get((family, side))
    for family in TACTIC_FAMILIES
    for side in TACTIC_SIDES
}


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
