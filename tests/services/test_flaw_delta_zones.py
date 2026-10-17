"""Pure registry-integrity tests for app/services/flaw_delta_zones.py.

No DB. Covers the 12-metric registry and the 9 tempo x phase cells, each keyed by all four
time controls, the 0.01 rounding grid, and the direct per-TC lookups (no ZONE_TC_FOR: that
stopgap now serves only the tactic registry, pinned in test_tactic_delta_zones.py).
"""

import pytest

from app.schemas.library import TEMPO_PHASE_PHASES, TEMPO_PHASE_TEMPOS
from app.schemas.normalization import TimeControlBucket
from app.services.flaw_delta_zones import (
    FLAW_DELTA_METRICS,
    FLAW_DELTA_ZONES,
    TEMPO_PHASE_ZONES,
    FlawDeltaMetric,
    FlawPhaseMetric,
    FlawTempoMetric,
    flaw_delta_zone,
    symmetric_band,
    tempo_phase_zone,
)

_ALL_TCS: tuple[TimeControlBucket, ...] = ("bullet", "blitz", "rapid", "classical")
_GRID = 0.01
# Served half-widths per (bullet, blitz, rapid, classical), per 100 user moves: symmetric_band
# of each TC's own Q1/Q3 from the 2026-10-14 section 5 whole-cohort run.
# Generated from that run's chapter5.json; pinned literally so registry drift fails here.
_HALF_WIDTHS: dict[FlawDeltaMetric, tuple[float, float, float, float]] = {
    "mistake": (0.1, 0.21, 0.29, 0.48),
    "blunder": (0.13, 0.25, 0.34, 0.53),
    "low_clock": (0.03, 0.1, 0.07, 0.04),
    "hasty": (0.08, 0.19, 0.43, 0.91),
    "unrushed": (0.17, 0.36, 0.52, 0.89),
    "opening": (0.07, 0.15, 0.2, 0.41),
    "middlegame": (0.12, 0.23, 0.3, 0.42),
    "endgame_phase": (0.05, 0.11, 0.14, 0.19),
    "miss": (0.06, 0.12, 0.15, 0.25),
    "lucky": (0.05, 0.1, 0.12, 0.2),
    "reversed": (0.03, 0.05, 0.06, 0.09),
    "squandered": (0.04, 0.08, 0.1, 0.16),
}
# The 7 viable crossed cells, same run (chapter5 section 5.16) and rule.
_TEMPO_PHASE_HALF_WIDTHS: dict[
    tuple[FlawTempoMetric, FlawPhaseMetric], tuple[float, float, float, float]
] = {
    ("hasty", "opening"): (0.04, 0.08, 0.16, 0.42),
    ("unrushed", "opening"): (0.06, 0.12, 0.18, 0.36),
    ("hasty", "middlegame"): (0.04, 0.1, 0.22, 0.48),
    ("unrushed", "middlegame"): (0.11, 0.22, 0.3, 0.55),
    ("low_clock", "endgame_phase"): (0.02, 0.07, 0.06, 0.03),
    ("hasty", "endgame_phase"): (0.03, 0.06, 0.12, 0.17),
    ("unrushed", "endgame_phase"): (0.05, 0.1, 0.12, 0.16),
}
# Not zone_viable in the run: low_clock x opening is degenerate (1.7% nonzero) and
# low_clock x middlegame is below the 50% nonzero floor (46.5%).
_ZONELESS_CELLS: frozenset[tuple[FlawTempoMetric, FlawPhaseMetric]] = frozenset(
    {("low_clock", "opening"), ("low_clock", "middlegame")}
)
# Retired metrics that must never reappear in the registry.
_RETIRED_METRICS = ("flaw_rate", "hasty_miss", "low_clock_miss")


def _assert_on_grid(value: float, label: str) -> None:
    assert round(value / _GRID) * _GRID == pytest.approx(value, abs=1e-9), (
        f"{label}: {value} is off the 0.01 grid"
    )


def test_registry_has_exactly_the_12_metrics() -> None:
    assert len(FLAW_DELTA_METRICS) == 12
    assert list(FLAW_DELTA_ZONES.keys()) == list(FLAW_DELTA_METRICS)
    for retired in _RETIRED_METRICS:
        assert retired not in FLAW_DELTA_ZONES


def test_every_metric_has_all_four_tcs_with_ordered_grid_bands() -> None:
    for metric in FLAW_DELTA_METRICS:
        per_tc = FLAW_DELTA_ZONES[metric]
        assert set(per_tc) == set(_ALL_TCS), metric
        for tc, band in per_tc.items():
            assert band.zone_lo < band.zone_hi, f"{metric}/{tc}"
            _assert_on_grid(band.zone_lo, f"{metric}/{tc}")
            _assert_on_grid(band.zone_hi, f"{metric}/{tc}")


def test_flaw_delta_zone_reads_the_tc_directly() -> None:
    for metric in FLAW_DELTA_METRICS:
        for tc in _ALL_TCS:
            assert flaw_delta_zone(metric, tc) is FLAW_DELTA_ZONES[metric][tc], (metric, tc)


def test_registry_values_are_the_pinned_per_tc_bands() -> None:
    """Every band is +-h, h = that TC's IQR / 2 rounded up to 0.01."""
    assert set(_HALF_WIDTHS) == set(FLAW_DELTA_METRICS)
    for metric, halves in _HALF_WIDTHS.items():
        for tc, half in zip(_ALL_TCS, halves, strict=True):
            band = FLAW_DELTA_ZONES[metric][tc]
            assert (band.zone_lo, band.zone_hi) == (-half, half), f"{metric}/{tc}"


def test_bullet_hasty_band_is_narrower_than_classical() -> None:
    # The reason for per-TC bands: the spread of the gap grows with the time control.
    hasty = FLAW_DELTA_ZONES["hasty"]
    assert hasty["bullet"].zone_hi < hasty["classical"].zone_hi


@pytest.mark.parametrize(
    ("q1", "q3", "half"),
    [(-0.08, 0.03, 0.06), (-0.31, 0.25, 0.28), (-0.11, 0.11, 0.11), (-7.00, 4.09, 5.55)],
)
def test_symmetric_band_rounds_the_half_iqr_up_to_the_grid(
    q1: float, q3: float, half: float
) -> None:
    band = symmetric_band(q1, q3)
    assert (band.zone_lo, band.zone_hi) == (-half, half)


def test_tempo_phase_registry_covers_the_nine_cells_and_four_tcs() -> None:
    expected = {(t, p) for t in TEMPO_PHASE_TEMPOS for p in TEMPO_PHASE_PHASES}
    assert set(TEMPO_PHASE_ZONES) == expected
    assert len(expected) == 9
    assert set(_TEMPO_PHASE_HALF_WIDTHS) | _ZONELESS_CELLS == expected
    for key, per_tc in TEMPO_PHASE_ZONES.items():
        assert set(per_tc) == set(_ALL_TCS), key


def test_tempo_phase_registry_pins_the_per_tc_half_widths() -> None:
    """The viable cells are +-h on the 0.01 grid per TC; the non-viable ones have none."""
    for key, halves in _TEMPO_PHASE_HALF_WIDTHS.items():
        for tc, half in zip(_ALL_TCS, halves, strict=True):
            band = TEMPO_PHASE_ZONES[key][tc]
            assert band is not None, f"{key}/{tc}"
            assert (band.zone_lo, band.zone_hi) == (-half, half), f"{key}/{tc}"
            _assert_on_grid(band.zone_hi, f"{key}/{tc}")
    for key in _ZONELESS_CELLS:
        assert all(band is None for band in TEMPO_PHASE_ZONES[key].values()), key


def test_tempo_phase_zone_reads_the_tc_directly() -> None:
    for tc in _ALL_TCS:
        for key, per_tc in TEMPO_PHASE_ZONES.items():
            assert tempo_phase_zone(key[0], key[1], tc) is per_tc[tc], (key, tc)
        for tempo, phase in _ZONELESS_CELLS:
            assert tempo_phase_zone(tempo, phase, tc) is None


def test_tempo_phase_registry_is_separate_from_the_12_bullets() -> None:
    assert len(FLAW_DELTA_METRICS) == 12
    assert list(FLAW_DELTA_ZONES.keys()) == list(FLAW_DELTA_METRICS)
