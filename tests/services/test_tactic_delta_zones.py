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
