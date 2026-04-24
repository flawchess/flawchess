"""Tests for endgame_zones.py: assign_zone direction handling, NaN guard,
boundary semantics, bucketed-metric lookup (D-10 recovery band), and
registry sanity.
"""

from app.services.endgame_zones import (
    BUCKETED_ZONE_REGISTRY,
    NEUTRAL_TIMEOUT_THRESHOLD,
    ZONE_REGISTRY,
    assign_bucketed_zone,
    assign_zone,
    sample_quality,
)


class TestAssignZone:
    """Unit tests for assign_zone direction handling and NaN guard."""

    def test_higher_is_better_above_upper_is_strong(self) -> None:
        assert assign_zone("endgame_skill", 0.61) == "strong"

    def test_higher_is_better_at_upper_boundary_is_strong(self) -> None:
        """Upper boundary is inclusive on the strong side (>= typical_upper)."""
        assert assign_zone("endgame_skill", 0.55) == "strong"

    def test_higher_is_better_in_typical_band_is_typical(self) -> None:
        assert assign_zone("endgame_skill", 0.50) == "typical"

    def test_higher_is_better_at_lower_boundary_is_typical(self) -> None:
        """Lower boundary is inclusive on the typical side (>= typical_lower)."""
        assert assign_zone("endgame_skill", 0.45) == "typical"

    def test_higher_is_better_below_lower_is_weak(self) -> None:
        assert assign_zone("endgame_skill", 0.30) == "weak"

    def test_signed_metric_centered_band(self) -> None:
        """Score Gap uses a centered typical band (-0.10, +0.10)."""
        assert assign_zone("score_gap", 0.0) == "typical"
        assert assign_zone("score_gap", 0.15) == "strong"
        assert assign_zone("score_gap", -0.15) == "weak"

    def test_net_timeout_rate_positive_is_strong(self) -> None:
        """Net timeout rate is higher_is_better: positive = user flags opponents more."""
        assert assign_zone("net_timeout_rate", 8.0) == "strong"

    def test_net_timeout_rate_in_band_is_typical(self) -> None:
        assert assign_zone("net_timeout_rate", 0.0) == "typical"

    def test_net_timeout_rate_negative_is_weak(self) -> None:
        """Negative net timeout rate = user gets flagged more than they flag."""
        assert assign_zone("net_timeout_rate", -8.0) == "weak"

    def test_nan_returns_typical(self) -> None:
        """NaN must not raise. Plan 03 findings use is_headline_eligible=False
        to signal missing data, not zone="weak"."""
        assert assign_zone("score_gap", float("nan")) == "typical"
        assert assign_zone("endgame_skill", float("nan")) == "typical"
        assert assign_zone("net_timeout_rate", float("nan")) == "typical"


class TestAssignBucketedZone:
    """Unit tests for per-bucket zone lookup (FIXED_GAUGE_ZONES equivalent)."""

    def test_recovery_band_after_d10(self) -> None:
        """D-10 re-centered recovery band to [0.25, 0.35]. 0.30 is now typical."""
        assert (
            assign_bucketed_zone("recovery_save_pct", "recovery", 0.30) == "typical"
        )

    def test_recovery_below_band_is_weak(self) -> None:
        assert (
            assign_bucketed_zone("recovery_save_pct", "recovery", 0.20) == "weak"
        )

    def test_recovery_above_band_is_strong(self) -> None:
        assert (
            assign_bucketed_zone("recovery_save_pct", "recovery", 0.40) == "strong"
        )

    def test_conversion_band_unchanged(self) -> None:
        """Conversion band stays [0.65, 0.75] per D-11 (only recovery changed)."""
        assert (
            assign_bucketed_zone("conversion_win_pct", "conversion", 0.70)
            == "typical"
        )
        assert (
            assign_bucketed_zone("conversion_win_pct", "conversion", 0.80)
            == "strong"
        )
        assert (
            assign_bucketed_zone("conversion_win_pct", "conversion", 0.50)
            == "weak"
        )

    def test_nan_returns_typical(self) -> None:
        assert (
            assign_bucketed_zone("recovery_save_pct", "recovery", float("nan"))
            == "typical"
        )


class TestSampleQuality:
    """Unit tests for sample_quality band lookup."""

    def test_thin_below_thin_max(self) -> None:
        assert sample_quality("overall", 40) == "thin"

    def test_adequate_between(self) -> None:
        assert sample_quality("overall", 100) == "adequate"

    def test_rich_above_adequate_max(self) -> None:
        assert sample_quality("overall", 500) == "rich"

    def test_results_by_endgame_type_smaller_bands(self) -> None:
        """Per-type bands are 5x smaller than overall (D-16 rationale):
        5-way split keeps denominators honest."""
        assert sample_quality("results_by_endgame_type", 5) == "thin"
        assert sample_quality("results_by_endgame_type", 20) == "adequate"
        assert sample_quality("results_by_endgame_type", 50) == "rich"


class TestRegistrySanity:
    """Sanity checks on registry shape and constants."""

    def test_all_scalar_metrics_have_entries(self) -> None:
        """ZONE_REGISTRY covers exactly the scalar metrics (bucketed metrics
        live in BUCKETED_ZONE_REGISTRY).

        Phase 68 v14 (260424-pc6) added `endgame_score` / `non_endgame_score`
        entries with a full-range `[0, 1]` typical band (no calibrated cohort
        band for per-part absolute scores — assign_zone always returns
        "typical" for these). See `_format_zone_bounds` in insights_llm.py
        for the matching bounds-suppression guard.
        """
        assert set(ZONE_REGISTRY.keys()) == {
            "score_gap",
            "endgame_score",
            "non_endgame_score",
            "endgame_skill",
            "avg_clock_diff_pct",
            "net_timeout_rate",
            "endgame_elo_gap",
            "win_rate",
        }

    def test_net_timeout_rate_uses_threshold_constant(self) -> None:
        """higher_is_better (positive = good); bounds reference NEUTRAL_TIMEOUT_THRESHOLD."""
        spec = ZONE_REGISTRY["net_timeout_rate"]
        assert spec.direction == "higher_is_better"
        assert spec.typical_upper == NEUTRAL_TIMEOUT_THRESHOLD
        assert spec.typical_lower == -NEUTRAL_TIMEOUT_THRESHOLD

    def test_bucketed_recovery_matches_d10(self) -> None:
        """D-10 locked: recovery typical band is [0.25, 0.35] in both FE
        and registry. All three buckets share the same band per metric."""
        for bucket in ("conversion", "parity", "recovery"):
            spec = BUCKETED_ZONE_REGISTRY["recovery_save_pct"][bucket]
            assert spec.typical_lower == 0.25
            assert spec.typical_upper == 0.35
            assert spec.direction == "higher_is_better"
