"""Unit tests for app.services.score_confidence.compute_confidence_bucket.

Lifted from tests/services/test_opening_insights_service.py:201-272 (Phase 75
boundary suite). Migrated to the new shared helper module per Phase 76 D-06.
The exact half-width = 0.10 / 0.20 boundary cases are un-hittable with integer
(w, d, l, n) inputs — the closest-integer cases below stay just inside the
medium / high buckets.
"""

import pytest

from app.services.score_confidence import compute_confidence_bucket


def test_high_at_large_n() -> None:
    confidence, p_value = compute_confidence_bucket(w=80, d=80, l=240, n=400)
    assert confidence == "high"
    assert 0.0 <= p_value < 1.0


def test_medium_at_moderate_n() -> None:
    confidence, _p_value = compute_confidence_bucket(w=6, d=6, l=18, n=30)
    assert confidence == "medium"


def test_low_at_n10_extreme_score() -> None:
    confidence, _p_value = compute_confidence_bucket(w=2, d=2, l=6, n=10)
    assert confidence == "low"


def test_just_inside_medium_boundary() -> None:
    # half_width is just inside 0.20; integer (w, d, l, n) cannot hit 0.20 exactly.
    confidence, _p_value = compute_confidence_bucket(w=5, d=5, l=15, n=25)
    assert confidence == "medium"


def test_p_value_at_score_050_is_one() -> None:
    _confidence, p_value = compute_confidence_bucket(w=8, d=4, l=8, n=20)
    assert p_value == pytest.approx(1.0, abs=1e-9)


def test_se_zero_all_draws() -> None:
    confidence, p_value = compute_confidence_bucket(w=0, d=10, l=0, n=10)
    assert confidence == "high"
    assert p_value == 1.0


def test_se_zero_all_wins() -> None:
    confidence, p_value = compute_confidence_bucket(w=10, d=0, l=0, n=10)
    assert confidence == "high"
    assert p_value == 0.0


def test_se_zero_all_losses() -> None:
    """D-22 boundary: SE = 0 case mirroring all-wins, but on the loss side."""
    confidence, p_value = compute_confidence_bucket(w=0, d=0, l=10, n=10)
    assert confidence == "high"
    assert p_value == 0.0


def test_n10_floor_balanced() -> None:
    """D-22 boundary: smallest legal n; balanced score sits exactly at pivot.

    Rule 1 fix: the plan specified confidence == "low" but the Wald formula
    gives half_width = 1.96 * sqrt(0.10/10) = 0.196 <= 0.20 → "medium".
    The assertion is corrected to match the formula. p_value = erfc(0) = 1.0
    because score == pivot (z = 0).
    """
    confidence, p_value = compute_confidence_bucket(w=2, d=6, l=2, n=10)
    assert confidence == "medium"  # half_width=0.196 falls in (0.10, 0.20] → medium
    assert p_value == pytest.approx(1.0, abs=1e-9)
