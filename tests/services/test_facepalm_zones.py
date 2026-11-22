"""Pure registry-integrity tests for app/services/facepalm_zones.py (quick 261121-ha7).

No DB. Covers the three facepalm rows, each keyed by all four time controls, the 0.01
rounding grid, symmetry around 0, the pinned half-widths and the direct per-TC lookup.
"""

import pytest

import app.schemas.library as library_schemas
from app.schemas.normalization import TimeControlBucket
from app.services import facepalm_zones
from app.services.facepalm_zones import (
    FACEPALM_METRICS,
    FACEPALM_ZONES,
    FacepalmMetric,
    facepalm_zone,
)
from app.services.flaw_delta_zones import ZoneBand

_ALL_TCS: tuple[TimeControlBucket, ...] = ("bullet", "blitz", "rapid", "classical")
_GRID = 0.01
# Served half-widths per (bullet, blitz, rapid, classical), per 100 user moves: symmetric_band
# of each TC's own prod Q1/Q3 (quick 261121-ha7, Phase 259 model). Pinned literally so registry drift fails here.
_HALF_WIDTHS: dict[FacepalmMetric, tuple[float, float, float, float]] = {
    "facepalm": (0.53, 0.30, 0.30, 0.52),
    "facepalm_missed_win": (0.14, 0.09, 0.08, 0.09),
    "facepalm_allowed_loss": (0.52, 0.30, 0.30, 0.54),
}


def _assert_on_grid(value: float, label: str) -> None:
    assert round(value / _GRID) * _GRID == pytest.approx(value, abs=1e-9), (
        f"{label}: {value} is off the 0.01 grid"
    )


def test_registry_keys_equal_the_three_facepalm_metrics_in_order() -> None:
    assert FACEPALM_METRICS == ("facepalm", "facepalm_missed_win", "facepalm_allowed_loss")
    assert list(FACEPALM_ZONES.keys()) == list(FACEPALM_METRICS)


def test_every_metric_has_all_four_tcs_with_symmetric_grid_bands() -> None:
    for metric in FACEPALM_METRICS:
        per_tc = FACEPALM_ZONES[metric]
        assert set(per_tc) == set(_ALL_TCS), metric
        for tc, band in per_tc.items():
            assert isinstance(band, ZoneBand), f"{metric}/{tc}"
            assert band.zone_lo < band.zone_hi, f"{metric}/{tc}"
            assert band.zone_lo == -band.zone_hi, f"{metric}/{tc}"
            _assert_on_grid(band.zone_lo, f"{metric}/{tc}")
            _assert_on_grid(band.zone_hi, f"{metric}/{tc}")


def test_registry_values_are_the_pinned_per_tc_bands() -> None:
    assert set(_HALF_WIDTHS) == set(FACEPALM_METRICS)
    for metric, halves in _HALF_WIDTHS.items():
        for tc, half in zip(_ALL_TCS, halves, strict=True):
            band = FACEPALM_ZONES[metric][tc]
            assert (band.zone_lo, band.zone_hi) == (-half, half), f"{metric}/{tc}"


def test_facepalm_zone_reads_the_tc_directly() -> None:
    for metric in FACEPALM_METRICS:
        for tc in _ALL_TCS:
            assert facepalm_zone(metric, tc) is FACEPALM_ZONES[metric][tc], (metric, tc)


def test_schema_reuses_the_registry_metric_type() -> None:
    assert library_schemas.FacepalmMetric is facepalm_zones.FacepalmMetric
