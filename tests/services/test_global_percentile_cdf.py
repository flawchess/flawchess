"""Tests for global_percentile_cdf.py: structural invariants of the
GLOBAL_PERCENTILE_CDF registry and behavior of interpolate_percentile.

Phase 93 Plan 02 Task 1 (TDD). The module is pure (no DB / no I/O) per
sibling `app/services/endgame_zones.py` purity invariant — tests must
not require asyncpg or a running benchmark DB.
"""

from __future__ import annotations

import math

from app.services.global_percentile_cdf import (
    BENCHMARK_DB_SNAPSHOT_MONTH,
    BREAKPOINT_LABELS,
    BREAKPOINT_PERCENTILES,
    GLOBAL_PERCENTILE_CDF,
    CdfTable,
    _interpolate_with_table,
    interpolate_percentile,
)

# In-scope MetricId literals for Phase 94.3 (D-02 / D-03 + per-TC time-pressure
# widening to 16 entries: 4 existing + 12 new per-(metric × TC) cells).
EXPECTED_METRIC_KEYS: frozenset[str] = frozenset(
    {
        # Phase 93 / 94.1 / 94.2 — original 4.
        "score_gap",
        "achievable_score_gap",
        "section2_score_gap_conv",
        "section2_score_gap_parity",
        # Phase 94.3 — 12 new per-TC time-pressure metric cells.
        "time_pressure_score_gap_bullet",
        "time_pressure_score_gap_blitz",
        "time_pressure_score_gap_rapid",
        "time_pressure_score_gap_classical",
        "clock_gap_bullet",
        "clock_gap_blitz",
        "clock_gap_rapid",
        "clock_gap_classical",
        "net_flag_rate_bullet",
        "net_flag_rate_blitz",
        "net_flag_rate_rapid",
        "net_flag_rate_classical",
    }
)

EXPECTED_BREAKPOINT_COUNT: int = 99


# ---------------------------------------------------------------------------
# Test 1 — audit-trail constant
# ---------------------------------------------------------------------------


def test_benchmark_db_snapshot_month_constant() -> None:
    """BENCHMARK_DB_SNAPSHOT_MONTH is the locked '2026-03' snapshot tag (D-04)."""
    assert BENCHMARK_DB_SNAPSHOT_MONTH == "2026-03"


# ---------------------------------------------------------------------------
# Test 2 — breakpoint labels are p1..p99
# ---------------------------------------------------------------------------


def test_breakpoint_labels_are_p1_through_p99() -> None:
    """BREAKPOINT_LABELS is exactly the 99 integer percentiles p1..p99 in order.

    ROADMAP success criterion #5 (no sub-percent steps, every integer percentile).
    """
    assert isinstance(BREAKPOINT_LABELS, tuple)
    assert len(BREAKPOINT_LABELS) == EXPECTED_BREAKPOINT_COUNT
    assert BREAKPOINT_LABELS[0] == "p1"
    assert BREAKPOINT_LABELS[-1] == "p99"
    assert BREAKPOINT_LABELS == tuple(f"p{i}" for i in range(1, 100))


# ---------------------------------------------------------------------------
# Test 3 — registry covers the 4 in-scope metrics exactly
# ---------------------------------------------------------------------------


def test_global_percentile_cdf_keys_match_in_scope_metrics() -> None:
    """GLOBAL_PERCENTILE_CDF is keyed by a subset of the 16 chip-eligible MetricIds.

    Phase 94.3 Plan 03 widens ``CdfMetricId`` and ``IN_SCOPE_METRICS`` to 16 entries
    in Task 1, then Task 2 regenerates the registry against the benchmark DB.
    Between Task 1 and Task 2 the registry may contain a strict subset (the
    pre-94.3 four). After Task 2 the registry equals ``EXPECTED_METRIC_KEYS``.
    Both states are valid; the equality check happens in
    ``test_global_percentile_cdf_registry_filled_with_16_entries`` below, which
    is enabled once the regen has run.
    """
    assert set(GLOBAL_PERCENTILE_CDF.keys()).issubset(set(EXPECTED_METRIC_KEYS))


def test_global_percentile_cdf_registry_filled_with_16_entries() -> None:
    """After Task 2 regen, the registry MUST be populated with all 16 in-scope metrics.

    Until Task 2 of Plan 94.3-03 runs the regeneration script, the committed
    registry still has 4 entries from Phase 94.2 — this test is EXPECTED RED in
    that intermediate state and turns GREEN once the regen commit lands.
    """
    assert set(GLOBAL_PERCENTILE_CDF.keys()) == set(EXPECTED_METRIC_KEYS)


# ---------------------------------------------------------------------------
# Test 4 — every CdfTable has 99 breakpoints aligned with labels/percentiles
# ---------------------------------------------------------------------------


def test_each_cdf_table_has_99_aligned_breakpoints() -> None:
    """Every CdfTable carries 99 breakpoints; the three parallel tuples align positionally."""
    assert len(BREAKPOINT_PERCENTILES) == EXPECTED_BREAKPOINT_COUNT
    assert len(BREAKPOINT_LABELS) == EXPECTED_BREAKPOINT_COUNT
    for metric_id, cdf in GLOBAL_PERCENTILE_CDF.items():
        assert len(cdf.breakpoints) == EXPECTED_BREAKPOINT_COUNT, (
            f"{metric_id} has {len(cdf.breakpoints)} breakpoints (expected 99)"
        )
        # Index i in each tuple represents the same percentile.
        for i, label in enumerate(BREAKPOINT_LABELS):
            expected_pct = float(int(label[1:]))
            assert BREAKPOINT_PERCENTILES[i] == expected_pct


# ---------------------------------------------------------------------------
# Test 5 — monotone non-decreasing breakpoints (empirical CDF invariant)
# ---------------------------------------------------------------------------


def test_breakpoints_are_monotonically_non_decreasing() -> None:
    """Empirical CDF invariant: percentile values never decrease as percentile rises."""
    for metric_id, cdf in GLOBAL_PERCENTILE_CDF.items():
        for i in range(len(cdf.breakpoints) - 1):
            assert cdf.breakpoints[i] <= cdf.breakpoints[i + 1], (
                f"{metric_id} not monotone: idx {i}={cdf.breakpoints[i]} > "
                f"idx {i + 1}={cdf.breakpoints[i + 1]}"
            )


# ---------------------------------------------------------------------------
# Test 6 — n_users is a positive integer per metric
# ---------------------------------------------------------------------------


def test_each_cdf_table_has_positive_n_users() -> None:
    """n_users is a positive integer (placeholder ≥1 until script runs)."""
    for metric_id, cdf in GLOBAL_PERCENTILE_CDF.items():
        assert isinstance(cdf.n_users, int)
        assert cdf.n_users >= 1, f"{metric_id} has n_users={cdf.n_users}"
        # snapshot_month carries the audit-trail tag even when the placeholder
        # default is used.
        assert cdf.snapshot_month == BENCHMARK_DB_SNAPSHOT_MONTH


# ---------------------------------------------------------------------------
# Test 7 — interpolate_percentile edge-clamps at p1/p99 for a registered metric
# ---------------------------------------------------------------------------


def test_interpolate_percentile_clamps_at_edges() -> None:
    """At-or-below p1 -> 0.0; at-or-above p99 -> 100.0; strictly between -> (0, 100)."""
    cdf = GLOBAL_PERCENTILE_CDF["achievable_score_gap"]
    p1_value = cdf.breakpoints[0]
    p99_value = cdf.breakpoints[-1]

    # Left-edge clamp: value <= p1 returns 0.0.
    assert interpolate_percentile("achievable_score_gap", p1_value) == 0.0
    assert interpolate_percentile("achievable_score_gap", p1_value - 1.0) == 0.0

    # Right-edge clamp: value >= p99 returns 100.0.
    assert interpolate_percentile("achievable_score_gap", p99_value) == 100.0
    assert interpolate_percentile("achievable_score_gap", p99_value + 1.0) == 100.0

    # Strictly inside the resolved range -> open interval (0, 100).
    mid_value = (p1_value + p99_value) / 2.0
    mid_pct = interpolate_percentile("achievable_score_gap", mid_value)
    assert mid_pct is not None
    assert 0.0 < mid_pct < 100.0


# ---------------------------------------------------------------------------
# Test 8 — interpolate_percentile uses linear interpolation between breakpoints
# ---------------------------------------------------------------------------


def test_interpolate_percentile_linear_between_breakpoints() -> None:
    """A 0..0.98 uniform ramp: value=0.495 sits halfway between idx 49 (p50) and idx 50 (p51) -> 50.5."""
    # Construct a synthetic 99-element table whose breakpoints[i] = i / 100.
    breakpoints: tuple[float, ...] = tuple(i / 100.0 for i in range(EXPECTED_BREAKPOINT_COUNT))
    synthetic_table = CdfTable(breakpoints=breakpoints, n_users=1)

    # 0.495 sits at the midpoint of breakpoints[49] = 0.49 and breakpoints[50] = 0.50.
    # BREAKPOINT_PERCENTILES[49] = 50.0, BREAKPOINT_PERCENTILES[50] = 51.0.
    # Linear interpolation midpoint -> 50.5.
    result = _interpolate_with_table(synthetic_table, 0.495)
    assert result is not None
    assert math.isclose(result, 50.5, abs_tol=1e-9), f"Got {result}, expected 50.5"


# ---------------------------------------------------------------------------
# Test 9 — NaN tolerance returns None
# ---------------------------------------------------------------------------


def test_interpolate_percentile_returns_none_on_nan() -> None:
    """NaN inputs return None (mirrors assign_zone NaN tolerance in endgame_zones.py)."""
    assert interpolate_percentile("score_gap", math.nan) is None


# ---------------------------------------------------------------------------
# Test 10 — module is pure (no DB / no I/O at import time)
# ---------------------------------------------------------------------------


def test_module_imports_without_db_or_io() -> None:
    """Re-importing the module must not touch asyncpg, the filesystem, or the network.

    Verified by inspecting the parsed module source for forbidden imports/calls. The
    module itself was already imported at test-module load time without raising —
    that is the primary signal — and the source-inspection adds a static defence
    against future regressions.
    """
    import importlib
    from pathlib import Path

    import app.services.global_percentile_cdf as mod

    # Reload exercises the module body a second time; if any import-time side
    # effect requires the DB or network, this raises here, not at collection.
    importlib.reload(mod)

    source = Path(mod.__file__).read_text() if mod.__file__ else ""
    forbidden_tokens = (
        "import sqlalchemy",
        "from sqlalchemy",
        "import asyncpg",
        "from app.db",
        "requests.",
        "httpx.",
    )
    for token in forbidden_tokens:
        assert token not in source, f"global_percentile_cdf.py must be pure; found {token!r}"


# ---------------------------------------------------------------------------
# Extra sanity: interpolate_percentile returns None for an unregistered metric.
# Not part of the 10 named tests but exercises the documented `None` branch
# for keys not in GLOBAL_PERCENTILE_CDF (cheap to keep alongside Test 9).
# ---------------------------------------------------------------------------


def test_interpolate_percentile_returns_none_for_unregistered_metric() -> None:
    """A MetricId outside the 16 Phase 94.3 keys returns None."""
    # `endgame_score` is a valid MetricId but is NOT chip-eligible (D-02 scope).
    assert interpolate_percentile("endgame_score", 0.5) is None


# ---------------------------------------------------------------------------
# Phase 94.3 — CdfMetricId Literal widening to 16 entries
# ---------------------------------------------------------------------------


def test_cdf_metric_id_literal_has_16_entries() -> None:
    """`CdfMetricId` Literal exposes exactly 16 string values (4 existing + 12 new)."""
    from typing import get_args

    from app.services.global_percentile_cdf import CdfMetricId

    members = set(get_args(CdfMetricId))
    assert len(members) == 16, f"Expected 16 CdfMetricId entries, got {len(members)}: {sorted(members)}"
    assert members == EXPECTED_METRIC_KEYS


def test_cdf_metric_id_includes_all_12_per_tc_entries() -> None:
    """All 12 per-(metric × TC) literals are present in `CdfMetricId`."""
    from typing import get_args

    from app.services.global_percentile_cdf import CdfMetricId

    members = set(get_args(CdfMetricId))
    expected_new = {
        f"{base}_{tc}"
        for base in ("time_pressure_score_gap", "clock_gap", "net_flag_rate")
        for tc in ("bullet", "blitz", "rapid", "classical")
    }
    assert expected_new.issubset(members), (
        f"Missing per-TC CdfMetricId members: {expected_new - members}"
    )
