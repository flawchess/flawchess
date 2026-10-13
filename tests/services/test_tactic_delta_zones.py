"""Tests for the tactic zone registry (Phase 239 D-06/D-08/D-09/D-11).

Pure unit tests, no DB. Registry values are monkeypatched where a band is needed so the
tests stay valid after plan 239-07 writes the real section-5 values.
"""

from collections.abc import Mapping

import pytest

from app.repositories.library_repository import FAMILY_TO_MOTIF_INTS
from app.services import tactic_delta_zones
from app.schemas.normalization import TimeControlBucket
from app.services.flaw_delta_zones import ZONE_TC_FOR, ZoneBand, ZoneTc
from app.services.tactic_delta_zones import (
    TACTIC_DELTA_ZONES,
    TACTIC_FAMILIES,
    TACTIC_SIDES,
    TacticFamily,
    TacticSide,
    tactic_delta_zone,
)

_RAPID = ZoneBand(zone_lo=-2.0, zone_hi=3.0)
_CLASSICAL = ZoneBand(zone_lo=-1.0, zone_hi=1.5)


def test_tactic_families_match_repository_order() -> None:
    """TACTIC_FAMILIES is spelled out (import cycle) and must equal FAMILY_TO_MOTIF_INTS keys in order."""
    assert list(TACTIC_FAMILIES) == list(FAMILY_TO_MOTIF_INTS)
    assert len(TACTIC_FAMILIES) == 19


def test_sides_order_is_missed_before_allowed() -> None:
    assert TACTIC_SIDES == ("missed", "allowed")


def test_registry_has_exactly_38_keys() -> None:
    assert len(TACTIC_DELTA_ZONES) == 38
    assert set(TACTIC_DELTA_ZONES) == {(f, s) for f in TACTIC_FAMILIES for s in TACTIC_SIDES}


def test_registry_values_are_none_or_cover_both_zone_tcs() -> None:
    """None = unviable; otherwise a band per zone TC (rapid and classical)."""
    for value in TACTIC_DELTA_ZONES.values():
        if value is not None:
            assert set(value) == {"rapid", "classical"}


# The owner-accepted viable set (239-ZONE-PROPOSAL.md ## Accepted): has_zone true for exactly
# these 9 (family, side) pairs; the other 29 stay None. Pinned literally on purpose.
_ACCEPTED_VIABLE: frozenset[tuple[TacticFamily, TacticSide]] = frozenset(
    {
        ("fork", "missed"),
        ("fork", "allowed"),
        ("pin", "missed"),
        ("pin", "allowed"),
        ("discovered_attack", "allowed"),
        ("hanging", "missed"),
        ("hanging", "allowed"),
        ("mate", "missed"),
        ("mate", "allowed"),
    }
)

# Accepted bands (per 100 games), identical for rapid and classical.
_ACCEPTED_BANDS: dict[tuple[TacticFamily, TacticSide], tuple[float, float]] = {
    ("fork", "missed"): (-2.21, +2.13),
    ("fork", "allowed"): (-4.12, +3.23),
    ("pin", "missed"): (-1.42, +1.89),
    ("pin", "allowed"): (-2.86, +2.05),
    ("discovered_attack", "allowed"): (-1.24, +1.06),
    ("hanging", "missed"): (-1.13, +1.48),
    ("hanging", "allowed"): (-5.11, +3.04),
    ("mate", "missed"): (-2.18, +2.90),
    ("mate", "allowed"): (-7.00, +4.09),
}


def test_viable_set_is_exactly_the_accepted_nine() -> None:
    viable = {key for key, value in TACTIC_DELTA_ZONES.items() if value is not None}
    assert viable == _ACCEPTED_VIABLE
    assert len(viable) == 9


def test_viable_bands_equal_the_accepted_values() -> None:
    assert set(_ACCEPTED_BANDS) == _ACCEPTED_VIABLE
    for key, (lo, hi) in _ACCEPTED_BANDS.items():
        zones = TACTIC_DELTA_ZONES[key]
        assert zones is not None, key
        for zone_tc in ("rapid", "classical"):
            band = zones[zone_tc]
            assert (band.zone_lo, band.zone_hi) == (lo, hi), f"{key}/{zone_tc}"
            assert band.zone_lo < band.zone_hi


def test_viable_bands_are_on_the_grid() -> None:
    for zones in TACTIC_DELTA_ZONES.values():
        if zones is None:
            continue
        for band in zones.values():
            for value in (band.zone_lo, band.zone_hi):
                assert round(value * 100) / 100 == pytest.approx(value, abs=1e-9)


def _patch_fork_missed(
    monkeypatch: pytest.MonkeyPatch, value: Mapping[ZoneTc, ZoneBand] | None
) -> None:
    """Replace the ("fork", "missed") registry entry for the duration of one test."""
    patched = {**TACTIC_DELTA_ZONES, ("fork", "missed"): value}
    monkeypatch.setattr(tactic_delta_zones, "TACTIC_DELTA_ZONES", patched)


@pytest.mark.parametrize("tc", ["bullet", "blitz", "rapid", "classical"])
def test_unviable_entry_returns_none(
    monkeypatch: pytest.MonkeyPatch, tc: TimeControlBucket
) -> None:
    _patch_fork_missed(monkeypatch, None)
    assert tactic_delta_zone("fork", "missed", tc) is None


@pytest.mark.parametrize("tc", ["bullet", "blitz", "rapid"])
def test_fast_tcs_read_the_rapid_band(
    monkeypatch: pytest.MonkeyPatch, tc: TimeControlBucket
) -> None:
    """D-08 stopgap: bullet and blitz fall back to the rapid band, silently."""
    _patch_fork_missed(monkeypatch, {"rapid": _RAPID, "classical": _CLASSICAL})
    assert tactic_delta_zone("fork", "missed", tc) == _RAPID


def test_classical_reads_the_classical_band(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_fork_missed(monkeypatch, {"rapid": _RAPID, "classical": _CLASSICAL})
    assert tactic_delta_zone("fork", "missed", "classical") == _CLASSICAL


def test_stopgap_mapping_is_the_shared_flaw_registry_mapping() -> None:
    """One stopgap mapping for both registries (no second copy)."""
    assert tactic_delta_zones.ZONE_TC_FOR is ZONE_TC_FOR
    assert ZONE_TC_FOR["blitz"] == "rapid"
    assert ZONE_TC_FOR["bullet"] == "rapid"
