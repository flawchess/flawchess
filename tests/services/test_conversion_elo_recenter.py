"""Wave 0 unit tests for the Phase 87.4 affine recenter + Conversion ELO pipeline.

Tests cover:
- PIVOT invariant (conv_ΔES = PIVOT ⇒ s = 0.5 ⇒ Conversion ELO = actual ELO).
- α band (1.65 <= ALPHA <= 2.05 per SC#4).
- CALIBRATION_VERSION constant exposed (prefix "conv_delta_v").
- Calibrated band [-0.108, +0.002] maps to s ~ [0.40, 0.60].
- Clamp behavior at extreme inputs.
- Full pipeline: _conversion_elo_from_skill(_affine_recenter_conv_delta(PIVOT), x) == round(x).

These tests are written BEFORE the implementation (RED gate) and will pass after
Task 2 + Task 3 in plan 01 land the affine helper + Phase 57 rename.
"""

import pytest

from app.services.endgame_service import (
    ALPHA,
    CALIBRATION_VERSION,
    PIVOT,
    _affine_recenter_conv_delta,
    _conversion_elo_from_skill,
)


class TestAffineRecenter:
    """SC#3 / SC#4 / SC#5: affine recenter math (Phase 87.4 D-01)."""

    def test_pivot_yields_half(self) -> None:
        # SC#3 prerequisite + SC#5: PIVOT maps to s = 0.5 exactly.
        assert _affine_recenter_conv_delta(PIVOT) == pytest.approx(0.5)

    def test_alpha_within_spec(self) -> None:
        # SC#4: ALPHA must lie inside [1.65, 2.05].
        assert 1.65 <= ALPHA <= 2.05

    def test_calibration_version_exposed(self) -> None:
        # CALIBRATION_VERSION is a non-empty string with the conv_delta_v prefix.
        assert isinstance(CALIBRATION_VERSION, str)
        assert CALIBRATION_VERSION.startswith("conv_delta_v")
        assert len(CALIBRATION_VERSION) > len("conv_delta_v")

    def test_band_lower_maps_inside_target(self) -> None:
        # Calibrated band lower: -0.108 → s ~ 0.40. Tolerance ±0.02 (the band is
        # asymmetric around PIVOT so any single-α pin lands here within ±0.02).
        s = _affine_recenter_conv_delta(-0.108)
        assert 0.35 <= s <= 0.42

    def test_band_upper_maps_inside_target(self) -> None:
        # Calibrated band upper: +0.002 → s ~ 0.60 (pin-upper rule per
        # RESEARCH.md §α Calibration).
        s = _affine_recenter_conv_delta(+0.002)
        assert 0.58 <= s <= 0.62

    def test_clamp_lower(self) -> None:
        # Extreme low conv_ΔES → s clamped to 0.05.
        assert _affine_recenter_conv_delta(-10.0) == pytest.approx(0.05)

    def test_clamp_upper(self) -> None:
        # Extreme high conv_ΔES → s clamped to 0.95.
        assert _affine_recenter_conv_delta(+10.0) == pytest.approx(0.95)


class TestConversionEloInvariant:
    """SC#5: Phase 57 median-coincide invariant survives the affine recenter."""

    def test_pivot_pipeline_invariant_actual_elo_preserved(self) -> None:
        # Full pipeline at actual_elo = 1500 anchored at PIVOT.
        s = _affine_recenter_conv_delta(PIVOT)
        assert _conversion_elo_from_skill(s, 1500.0) == 1500

    def test_pivot_pipeline_invariant_actual_elo_preserved_2000(self) -> None:
        # Same invariant at a different rating anchor.
        s = _affine_recenter_conv_delta(PIVOT)
        assert _conversion_elo_from_skill(s, 2000.0) == 2000
