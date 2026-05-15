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
        """Lower boundary is inclusive on the typical side (>= typical_lower).
        260503: lower bound shifted 0.45 -> 0.47 to better center on pooled p25."""
        assert assign_zone("endgame_skill", 0.47) == "typical"

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
        assert assign_bucketed_zone("recovery_save_pct", "recovery", 0.30) == "typical"

    def test_recovery_below_band_is_weak(self) -> None:
        assert assign_bucketed_zone("recovery_save_pct", "recovery", 0.20) == "weak"

    def test_recovery_above_band_is_strong(self) -> None:
        assert assign_bucketed_zone("recovery_save_pct", "recovery", 0.40) == "strong"

    def test_conversion_band_unchanged(self) -> None:
        """Conversion band stays [0.65, 0.75] per D-11 (only recovery changed)."""
        assert assign_bucketed_zone("conversion_win_pct", "conversion", 0.70) == "typical"
        assert assign_bucketed_zone("conversion_win_pct", "conversion", 0.80) == "strong"
        assert assign_bucketed_zone("conversion_win_pct", "conversion", 0.50) == "weak"

    def test_nan_returns_typical(self) -> None:
        assert assign_bucketed_zone("recovery_save_pct", "recovery", float("nan")) == "typical"


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


class TestNewMetricZones:
    """Boundary tests for Phase 82 D-08/D-10 new ZoneSpec entries.

    entry_eval_pawns: typical = [-0.75, +0.75], higher_is_better.
    endgame_score: typical = [0.45, 0.55], higher_is_better.
    Both replace old score-timeline no-op entries (D-01/D-02 rename) and
    register the new endgame_start_vs_end subsection metrics (D-03/D-04).
    """

    # --- entry_eval_pawns boundaries ---

    def test_entry_eval_above_band_is_strong(self) -> None:
        assert assign_zone("entry_eval_pawns", 1.0) == "strong"

    def test_entry_eval_at_upper_boundary_is_strong(self) -> None:
        """Upper boundary is inclusive on the strong side (>= typical_upper)."""
        assert assign_zone("entry_eval_pawns", 0.75) == "strong"

    def test_entry_eval_inside_band_is_typical(self) -> None:
        assert assign_zone("entry_eval_pawns", 0.74) == "typical"

    def test_entry_eval_zero_is_typical(self) -> None:
        assert assign_zone("entry_eval_pawns", 0.0) == "typical"

    def test_entry_eval_at_lower_boundary_is_typical(self) -> None:
        """Lower boundary is inclusive on the typical side (>= typical_lower)."""
        assert assign_zone("entry_eval_pawns", -0.75) == "typical"

    def test_entry_eval_below_band_is_weak(self) -> None:
        assert assign_zone("entry_eval_pawns", -1.0) == "weak"

    def test_entry_eval_nan_is_typical(self) -> None:
        assert assign_zone("entry_eval_pawns", float("nan")) == "typical"

    # --- endgame_score boundaries ---

    def test_endgame_score_above_band_is_strong(self) -> None:
        assert assign_zone("endgame_score", 0.60) == "strong"

    def test_endgame_score_at_upper_boundary_is_strong(self) -> None:
        """Upper boundary 0.55 inclusive on strong side."""
        assert assign_zone("endgame_score", 0.55) == "strong"

    def test_endgame_score_inside_band_is_typical(self) -> None:
        assert assign_zone("endgame_score", 0.50) == "typical"

    def test_endgame_score_at_lower_boundary_is_typical(self) -> None:
        """Lower boundary 0.45 inclusive on typical side."""
        assert assign_zone("endgame_score", 0.45) == "typical"

    def test_endgame_score_below_band_is_weak(self) -> None:
        assert assign_zone("endgame_score", 0.40) == "weak"

    def test_endgame_score_nan_is_typical(self) -> None:
        assert assign_zone("endgame_score", float("nan")) == "typical"

    # --- endgame_start_vs_end sample_quality bands ---

    def test_endgame_start_vs_end_thin_below_10(self) -> None:
        assert sample_quality("endgame_start_vs_end", 9) == "thin"

    def test_endgame_start_vs_end_adequate_at_10(self) -> None:
        """Boundary: n=10 is the strict-`<` floor for thin; must be `adequate`.

        Phase 82 IN-03: paired with test_tile1_at_n_eval_10_is_populated_adequate
        in test_insights_service.py — both pin the off-by-one between the
        emitter's `< 10` empty gate and the band classifier so a future band
        shift cannot produce an emitted finding (n=10 not empty) that is then
        classified as `thin` and suppressed at headline-eligibility time.
        """
        assert sample_quality("endgame_start_vs_end", 10) == "adequate"

    def test_endgame_start_vs_end_adequate_between(self) -> None:
        assert sample_quality("endgame_start_vs_end", 25) == "adequate"

    def test_endgame_start_vs_end_adequate_at_49(self) -> None:
        """Boundary: n=49 just below the rich threshold (50) is still adequate."""
        assert sample_quality("endgame_start_vs_end", 49) == "adequate"

    def test_endgame_start_vs_end_rich_at_50(self) -> None:
        """Boundary: n=50 is the strict-`<` floor for adequate; must be `rich`."""
        assert sample_quality("endgame_start_vs_end", 50) == "rich"

    def test_endgame_start_vs_end_rich_above_50(self) -> None:
        assert sample_quality("endgame_start_vs_end", 60) == "rich"


class TestRegistrySanity:
    """Sanity checks on registry shape and constants."""

    def test_all_scalar_metrics_have_entries(self) -> None:
        """ZONE_REGISTRY covers exactly the scalar metrics (bucketed metrics
        live in BUCKETED_ZONE_REGISTRY).

        Phase 82 (D-01..D-04, D-08, D-10): `endgame_score` / `non_endgame_score`
        are renamed to `endgame_score_timeline` / `non_endgame_score_timeline`
        (no-op [0, 1] band preserved). Two new entries added:
        `entry_eval_pawns` (±0.75 band) and `endgame_score` (repurposed, [0.45,
        0.55] band). See `_format_zone_bounds` in insights_llm.py for the
        matching bounds-suppression guard on timeline metrics.

        Phase 83 (D-14..D-17): `entry_expected_score` ([0.45, 0.55] band)
        added — Lichess-sigmoid expected score at endgame entry over the user's
        cohort, surfaced as the "achievable score" row of the new Tile 1 (Plan
        83-03). Source: reports/benchmarks-2026-05-11.md §7.

        260514-kei: `achievable_score_gap` (±0.05 band) added — dedicated band
        for the Card 3 Achievable row so it can tighten to ±5pp without
        affecting the Endgame Score Gap row (which stays on `score_gap` at
        ±10pp). Source: reports/benchmarks-latest.md §3.1.5.

        Phase 87.1 (SEED-016 D-02/D-04): `endgame_type_achievable_score_gap`
        (placeholder ±0.05 band) added — per-span, per-type version of
        achievable_score_gap, surfaced on every EndgameTypeCard "Score Gap"
        row (Plan 03) and through the LLM type_breakdown payload (Plan 04).
        Bands calibrate from benchmarks SKILL.md §3.4.2.
        """
        assert set(ZONE_REGISTRY.keys()) == {
            "score_gap",
            "achievable_score_gap",
            "endgame_type_achievable_score_gap",
            "entry_eval_pawns",
            "entry_expected_score",
            "endgame_score",
            "endgame_score_timeline",
            "non_endgame_score_timeline",
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

    def test_bucketed_recovery_matches_benchmark(self) -> None:
        """260503: recovery typical band tightened to [0.24, 0.36] — pooled
        p25/p75 = [0.243, 0.364] from reports/benchmarks-2026-05-03.md (was
        [0.25, 0.40], 260501-s0u). All three buckets share the same band."""
        for bucket in ("conversion", "parity", "recovery"):
            spec = BUCKETED_ZONE_REGISTRY["recovery_save_pct"][bucket]
            assert spec.typical_lower == 0.24
            assert spec.typical_upper == 0.36
            assert spec.direction == "higher_is_better"
