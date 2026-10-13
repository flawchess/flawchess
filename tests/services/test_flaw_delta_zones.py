"""Pure registry-integrity tests for app/services/flaw_delta_zones.py (Phase 239 D-07..D-09).

No DB. Covers the 12-metric registry, the per-zone-TC band structure, the 0.01
rounding grid, and the D-08 blitz/bullet -> rapid stopgap mapping.
"""

import pytest

from app.schemas.normalization import TimeControlBucket
from app.services.flaw_delta_zones import (
    FLAW_DELTA_METRICS,
    FLAW_DELTA_ZONES,
    ZONE_TC_FOR,
    FlawDeltaMetric,
    flaw_delta_zone,
)

_ALL_TCS: tuple[TimeControlBucket, ...] = ("bullet", "blitz", "rapid", "classical")
_GRID = 0.01
# Owner-accepted flaw bands (239-ZONE-PROPOSAL.md ## Accepted): the live values kept for both
# zone TCs, per 100 user moves. Pinned literally so a drift in the registry fails here.
_ACCEPTED_FLAW_BANDS: dict[FlawDeltaMetric, tuple[float, float]] = {
    "mistake": (-0.23, +0.20),
    "blunder": (-0.31, +0.25),
    "low_clock": (-0.08, +0.03),
    "hasty": (-0.28, +0.18),
    "unrushed": (-0.38, +0.36),
    "opening": (-0.15, +0.13),
    "middlegame": (-0.27, +0.23),
    "endgame_phase": (-0.12, +0.10),
    "miss": (-0.11, +0.11),
    "lucky": (-0.09, +0.09),
    "reversed": (-0.04, +0.04),
    "squandered": (-0.07, +0.08),
}
# Retired metrics (D-00e/D-00f) that must never reappear in the registry.
_RETIRED_METRICS = ("flaw_rate", "hasty_miss", "low_clock_miss")


def test_registry_has_exactly_the_12_metrics() -> None:
    assert len(FLAW_DELTA_METRICS) == 12
    assert list(FLAW_DELTA_ZONES.keys()) == list(FLAW_DELTA_METRICS)
    for retired in _RETIRED_METRICS:
        assert retired not in FLAW_DELTA_ZONES


def test_every_metric_has_both_zone_tcs_with_ordered_grid_bands() -> None:
    for metric in FLAW_DELTA_METRICS:
        per_tc = FLAW_DELTA_ZONES[metric]
        assert set(per_tc) == {"rapid", "classical"}, metric
        for zone_tc, band in per_tc.items():
            assert band.zone_lo < band.zone_hi, f"{metric}/{zone_tc}"
            for value in (band.zone_lo, band.zone_hi):
                assert round(value / _GRID) * _GRID == pytest.approx(value, abs=1e-9), (
                    f"{metric}/{zone_tc}: {value} is off the 0.01 grid"
                )


def test_zone_tc_mapping_is_the_d08_stopgap() -> None:
    assert ZONE_TC_FOR["bullet"] == "rapid"
    assert ZONE_TC_FOR["blitz"] == "rapid"
    assert ZONE_TC_FOR["rapid"] == "rapid"
    assert ZONE_TC_FOR["classical"] == "classical"
    assert set(ZONE_TC_FOR) == set(_ALL_TCS)


def test_flaw_delta_zone_applies_the_mapping() -> None:
    assert flaw_delta_zone("hasty", "bullet") is FLAW_DELTA_ZONES["hasty"]["rapid"]
    assert flaw_delta_zone("hasty", "blitz") is FLAW_DELTA_ZONES["hasty"]["rapid"]
    assert flaw_delta_zone("hasty", "rapid") is FLAW_DELTA_ZONES["hasty"]["rapid"]
    assert flaw_delta_zone("hasty", "classical") is FLAW_DELTA_ZONES["hasty"]["classical"]


def test_registry_values_equal_the_accepted_bands() -> None:
    """Every band equals the ## Accepted table, for both zone TCs (D-07, D-10)."""
    assert set(_ACCEPTED_FLAW_BANDS) == set(FLAW_DELTA_METRICS)
    for metric, (lo, hi) in _ACCEPTED_FLAW_BANDS.items():
        for zone_tc in ("rapid", "classical"):
            band = FLAW_DELTA_ZONES[metric][zone_tc]
            assert (band.zone_lo, band.zone_hi) == (lo, hi), f"{metric}/{zone_tc}"
