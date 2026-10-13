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
    symmetric_band,
)

_ALL_TCS: tuple[TimeControlBucket, ...] = ("bullet", "blitz", "rapid", "classical")
_GRID = 0.01
# Owner-accepted flaw quartiles (239-ZONE-PROPOSAL.md ## Accepted): the live values kept for
# both zone TCs, per 100 user moves. Pinned literally so a drift in the registry fails here.
# Phase 239 D-15: the accepted quartiles (-0.23 / +0.20 for mistake, ...) become symmetric
# bands +-h, h = IQR / 2 rounded up to 0.01. Hand-computed, so the test pins the rounding.
_SYMMETRIC_HALF_WIDTHS: dict[FlawDeltaMetric, float] = {
    "mistake": 0.22,  # (-0.23, +0.20)
    "blunder": 0.28,  # (-0.31, +0.25)
    "low_clock": 0.06,  # (-0.08, +0.03): IQR/2 = 0.055, rounded up
    "hasty": 0.23,  # (-0.28, +0.18)
    "unrushed": 0.37,  # (-0.38, +0.36)
    "opening": 0.14,  # (-0.15, +0.13)
    "middlegame": 0.25,  # (-0.27, +0.23)
    "endgame_phase": 0.11,  # (-0.12, +0.10)
    "miss": 0.11,  # (-0.11, +0.11)
    "lucky": 0.09,  # (-0.09, +0.09)
    "reversed": 0.04,  # (-0.04, +0.04)
    "squandered": 0.08,  # (-0.07, +0.08): IQR/2 = 0.075, rounded up
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


def test_registry_values_are_the_symmetric_accepted_bands() -> None:
    """Every band is +-IQR/2 of the ## Accepted quartiles, for both zone TCs (D-15)."""
    assert set(_SYMMETRIC_HALF_WIDTHS) == set(FLAW_DELTA_METRICS)
    for metric, half in _SYMMETRIC_HALF_WIDTHS.items():
        for zone_tc in ("rapid", "classical"):
            band = FLAW_DELTA_ZONES[metric][zone_tc]
            assert (band.zone_lo, band.zone_hi) == (-half, half), f"{metric}/{zone_tc}"


@pytest.mark.parametrize(
    ("q1", "q3", "half"),
    [(-0.08, 0.03, 0.06), (-0.31, 0.25, 0.28), (-0.11, 0.11, 0.11), (-7.00, 4.09, 5.55)],
)
def test_symmetric_band_rounds_the_half_iqr_up_to_the_grid(
    q1: float, q3: float, half: float
) -> None:
    band = symmetric_band(q1, q3)
    assert (band.zone_lo, band.zone_hi) == (-half, half)
