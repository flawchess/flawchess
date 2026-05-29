"""Tests for `app.services.chesscom_to_lichess` — Phase 94.4 Plan 01.

Pure-Python lookup module. The three lookup tables are the canonical
re-fetched ChessGoals 2025-07 snapshot (RESEARCH Pattern 8b, lines 924-1045),
which supersedes the earlier Pattern 8 draft. Snapshot is locked at the value
level; all assertions reference exact values from the dict literals shipped in
the module.

Coverage (13 behavior cases per plan):
- Test 1: chess.com Blitz → Lichess Blitz at an exact anchor row (Table 2).
- Test 2: chess.com Blitz → Lichess Blitz between two anchors (linear interp).
- Test 3: chess.com Bullet → Lichess Bullet via Table 1 inversion → Table 2.
- Test 4: chess.com Rapid → Lichess Rapid via Table 1 inversion → Table 2.
- Test 5: chess.com Daily → Lichess Rapid returns None (Pitfall 2).
- Test 6: Below-min anchor (rating < 500) returns None.
- Test 7: Above-max anchor (rating > 3000 chess.com Blitz) returns None.
- Tests 8-11: Each USCF/FIDE accessor returns the snapshot anchor value at a
  mid-range row.
- Test 12: USCF/FIDE accessors return None for below-min and above-max inputs
  (parametrized).
- Test 13: Snapshot constants are present and correct.
"""

from __future__ import annotations

import pytest

from app.services.chesscom_to_lichess import (
    CHESSCOM_BLITZ_TO_LICHESS,
    CHESSCOM_INTRA_TC,
    CHESSCOM_TO_LICHESS_SOURCE,
    CHESSCOM_TO_LICHESS_TABLE_SNAPSHOT,
    LICHESS_BLITZ_INTRA_TC,
    ChessComSourceTC,
    LichessTC,
    composed_chesscom_to_lichess_grid,
    convert_chesscom_to_lichess,
    lookup_fide_from_chesscom_blitz,
    lookup_fide_from_lichess_blitz,
    lookup_uscf_from_chesscom_blitz,
    lookup_uscf_from_lichess_blitz,
)


# -----------------------------------------------------------------------------
# Test 1: chess.com Blitz → Lichess Blitz at an exact anchor row (Table 2).
# Snapshot anchor: chess.com Blitz 1500 → Lichess Blitz 1780.
# -----------------------------------------------------------------------------
def test_chesscom_blitz_to_lichess_blitz_exact_anchor() -> None:
    result = convert_chesscom_to_lichess(1500, "blitz", "blitz")
    assert result == CHESSCOM_BLITZ_TO_LICHESS[1500]["blitz"]
    assert result == 1780


# -----------------------------------------------------------------------------
# Test 2: chess.com Blitz between two anchors → linear interpolation.
# 1525 is midway between anchors 1500 (Lichess Blitz=1780) and 1550 (1815).
# Expected midpoint ≈ (1780+1815)/2 = 1797.5 → 1797 or 1798 (int).
# -----------------------------------------------------------------------------
def test_chesscom_blitz_to_lichess_blitz_linear_interpolation() -> None:
    low = CHESSCOM_BLITZ_TO_LICHESS[1500]["blitz"]  # 1780
    high = CHESSCOM_BLITZ_TO_LICHESS[1550]["blitz"]  # 1815
    # Narrow: Lichess Blitz column has no None entries in Table 2 (only
    # `classical` does, at chess.com Blitz 2800/2900/3000).
    assert low is not None and high is not None
    result = convert_chesscom_to_lichess(1525, "blitz", "blitz")
    assert result is not None
    # Must lie strictly between the two endpoints (interpolation, not clamp).
    assert low < result < high
    # Specifically: midway is the average, rounded.
    expected = round((low + high) / 2)
    assert result == expected


# -----------------------------------------------------------------------------
# Test 3: chess.com Bullet → Lichess Bullet via Table 1 inversion → Table 2.
# 2026-05-27 re-fetched Table 1: chess.com Blitz 1500 has bullet=1400. So a
# chess.com Bullet input of 1400 inverts exactly to Blitz=1500, which then
# chains into Table 2[1500]["bullet"] = 1770.
# -----------------------------------------------------------------------------
def test_chesscom_bullet_to_lichess_bullet_via_table_inversion() -> None:
    assert CHESSCOM_INTRA_TC[1500]["bullet"] == 1400
    result = convert_chesscom_to_lichess(1400, "bullet", "bullet")
    assert result == CHESSCOM_BLITZ_TO_LICHESS[1500]["bullet"]
    assert result == 1770


# -----------------------------------------------------------------------------
# Test 4: chess.com Rapid 1655 → Lichess Rapid via Table 1 inversion.
# CHESSCOM_INTRA_TC[1500]["rapid"] == 1655, so rating=1655 inverts to Blitz=1500,
# then Table 2[1500]["rapid"] = 1930.
# -----------------------------------------------------------------------------
def test_chesscom_rapid_to_lichess_rapid_via_table_inversion() -> None:
    assert CHESSCOM_INTRA_TC[1500]["rapid"] == 1655
    result = convert_chesscom_to_lichess(1655, "rapid", "rapid")
    assert result == CHESSCOM_BLITZ_TO_LICHESS[1500]["rapid"]
    assert result == 1930


# -----------------------------------------------------------------------------
# Test 5: chess.com Daily → returns None (no published mapping; Pitfall 2).
# -----------------------------------------------------------------------------
def test_chesscom_daily_returns_none() -> None:
    assert convert_chesscom_to_lichess(1500, "daily", "rapid") is None


# -----------------------------------------------------------------------------
# Test 6: Below-min anchor returns None (clamp, do not extrapolate).
# Min chess.com Blitz anchor is 500.
# -----------------------------------------------------------------------------
def test_below_min_returns_none() -> None:
    assert convert_chesscom_to_lichess(400, "blitz", "blitz") is None


# -----------------------------------------------------------------------------
# Test 7: Above-max anchor returns None (clamp, do not extrapolate).
# Max chess.com Blitz anchor is 3000.
# -----------------------------------------------------------------------------
def test_above_max_returns_none() -> None:
    assert convert_chesscom_to_lichess(3500, "blitz", "blitz") is None


# -----------------------------------------------------------------------------
# Test 8: lookup_uscf_from_chesscom_blitz at a mid-range anchor.
# Snapshot: chess.com Blitz 1500 → USCF 1595.
# -----------------------------------------------------------------------------
def test_lookup_uscf_from_chesscom_blitz_mid_range() -> None:
    result = lookup_uscf_from_chesscom_blitz(1500)
    assert result == CHESSCOM_INTRA_TC[1500]["uscf"]
    assert result == 1595


# -----------------------------------------------------------------------------
# Test 9: lookup_fide_from_chesscom_blitz at a mid-range anchor.
# Snapshot: chess.com Blitz 1500 → FIDE 1710.
# -----------------------------------------------------------------------------
def test_lookup_fide_from_chesscom_blitz_mid_range() -> None:
    result = lookup_fide_from_chesscom_blitz(1500)
    assert result == CHESSCOM_INTRA_TC[1500]["fide"]
    assert result == 1710


# -----------------------------------------------------------------------------
# Test 10: lookup_uscf_from_lichess_blitz at a mid-range anchor.
# Snapshot: Lichess Blitz 1780 → USCF 1595.
# -----------------------------------------------------------------------------
def test_lookup_uscf_from_lichess_blitz_mid_range() -> None:
    result = lookup_uscf_from_lichess_blitz(1780)
    assert result == LICHESS_BLITZ_INTRA_TC[1780]["uscf"]
    assert result == 1595


# -----------------------------------------------------------------------------
# Test 11: lookup_fide_from_lichess_blitz at a mid-range anchor.
# Snapshot: Lichess Blitz 1780 → FIDE 1710.
# -----------------------------------------------------------------------------
def test_lookup_fide_from_lichess_blitz_mid_range() -> None:
    result = lookup_fide_from_lichess_blitz(1780)
    assert result == LICHESS_BLITZ_INTRA_TC[1780]["fide"]
    assert result == 1710


# -----------------------------------------------------------------------------
# Test 12: All four USCF/FIDE accessors return None for below-min + above-max.
# chess.com Blitz table: [500, 3000]. Lichess Blitz table: [1030, 2850].
# Plus: lookup_fide_from_lichess_blitz returns None for the 5 below-1420 rows
# where the FIDE column is None in the snapshot (Lichess Blitz 1030..1335).
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("accessor", "rating"),
    [
        # Below-min
        (lookup_uscf_from_chesscom_blitz, 400),
        (lookup_fide_from_chesscom_blitz, 400),
        (lookup_uscf_from_lichess_blitz, 900),
        (lookup_fide_from_lichess_blitz, 900),
        # Above-max
        (lookup_uscf_from_chesscom_blitz, 3500),
        (lookup_fide_from_chesscom_blitz, 3500),
        (lookup_uscf_from_lichess_blitz, 3000),
        (lookup_fide_from_lichess_blitz, 3000),
    ],
)
def test_accessors_return_none_at_edges(accessor, rating: int) -> None:
    assert accessor(rating) is None


# Snapshot-Null rows: Lichess Blitz <= 1335 has FIDE = None in the source.
def test_lookup_fide_from_lichess_blitz_returns_none_in_null_region() -> None:
    # Lichess Blitz 1030 has FIDE=None per snapshot.
    assert lookup_fide_from_lichess_blitz(1030) is None


# -----------------------------------------------------------------------------
# Test 13: Snapshot constants present and correct.
# -----------------------------------------------------------------------------
def test_snapshot_constants() -> None:
    assert CHESSCOM_TO_LICHESS_TABLE_SNAPSHOT == "2026-05-27"
    assert CHESSCOM_TO_LICHESS_SOURCE == "https://chessgoals.com/rating-comparison/"


# -----------------------------------------------------------------------------
# Additional smoke tests on parametrized accessors (one mid-range hit per
# accessor — covers the "parametrize at least one USCF + FIDE accessor" spec).
# -----------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("accessor", "rating", "expected"),
    [
        # Exact-anchor reads.
        (lookup_uscf_from_chesscom_blitz, 500, 715),
        # chess.com Blitz 1000 is the lowest FIDE-mapped row (2026-05-27 snapshot;
        # 500-900 are None).
        (lookup_fide_from_chesscom_blitz, 1000, 1450),
        # Interpolated read: Lichess Blitz 1500 sits between anchors 1475
        # (USCF=1280) and 1525 (USCF=1325). Linear interpolation: 1280 +
        # (25/50)*(1325-1280) = 1280 + 22.5 ≈ 1302 (round-half-to-even).
        (lookup_uscf_from_lichess_blitz, 1500, 1302),
    ],
)
def test_accessor_mid_range_hits(accessor, rating: int, expected: int) -> None:
    result = accessor(rating)
    # ±2 tolerance to absorb the rounding-direction ambiguity at .5 boundary.
    assert result is not None
    assert abs(result - expected) <= 2


# -----------------------------------------------------------------------------
# Snapshot-Null rows on the chess.com Blitz side: FIDE is None for the 500-900
# anchors per the 2026-05-27 re-fetch (no FIDE-rated profiles in the source
# below the 1000 cohort). USCF remains populated across the full range.
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("rating", [500, 600, 700, 800, 900])
def test_lookup_fide_from_chesscom_blitz_returns_none_in_null_region(
    rating: int,
) -> None:
    assert lookup_fide_from_chesscom_blitz(rating) is None


# -----------------------------------------------------------------------------
# composed_chesscom_to_lichess_grid equivalence tests (quick-260529-js1).
#
# The SQL anchor pipeline (`_chesscom_conversion_values_sql`) used to key its
# VALUES lookup on chess.com BLITZ anchors and match every game's native rating
# against them regardless of the game's actual TC. For rapid/bullet that meant
# matching a rapid/bullet native rating against blitz-scale anchors and skipping
# the intra-TC inversion the canonical converter applies, inflating rapid/
# classical anchors and deflating bullet. The fix composes the grid by calling
# `convert_chesscom_to_lichess` per native chess.com rating for the bucket's
# source TC, so the SQL nearest-anchor join becomes correct.
#
# These tests assert the grid (selected via the SQL nearest-anchor rule:
# `ORDER BY ABS(anchor - rating) LIMIT 1`) reproduces the converter within a
# named tolerance for all 4 FlawChess buckets.
# -----------------------------------------------------------------------------

# FlawChess bucket -> chess.com source TC mapping (classical->rapid: chess.com
# has no classical category; chess.com games bucketed `classical` carry rapid
# ratings, with Daily games already dropped upstream).
_BUCKET_TO_SOURCE_TC: dict[LichessTC, ChessComSourceTC] = {
    "bullet": "bullet",
    "blitz": "blitz",
    "rapid": "rapid",
    "classical": "rapid",
}

# Tolerance for the nearest-anchor reconstruction error vs the converter.
# The converter is piecewise-linear; the steepest path is the bullet/rapid
# inversion in the high range (classical bucket, source_tc='rapid'), where
# Table 1's rapid column is flat so a native-rapid grid step inverts to a larger
# chess.com Blitz step that Table 2 then amplifies. With the module's 15-pt
# native grid step (_COMPOSED_GRID_STEP) the measured worst-case nearest-anchor
# error across all 4 buckets is 16 pts; a 20-pt tolerance comfortably exceeds
# that (and exceeds half the max inter-grid converter delta). A coarser 25-pt
# grid was measured to leave a 26-pt worst-case error, which is why the module
# uses 15.
_GRID_NEAREST_TOLERANCE: int = 20

# Native-rating probe step for the equivalence sweep. 1 = exhaustive over the
# native domain (a few thousand cheap pure-Python converter calls), so the
# worst-case midpoint between grid anchors is always exercised.
_PROBE_STEP: int = 1


def _nearest_grid_equiv(grid: list[tuple[int, int]], rating: int) -> int:
    """Mimic the SQL `ORDER BY ABS(anchor - rating) LIMIT 1` nearest-anchor pick."""
    best_anchor, best_equiv = grid[0]
    best_dist = abs(best_anchor - rating)
    for anchor, equiv in grid[1:]:
        dist = abs(anchor - rating)
        if dist < best_dist:
            best_anchor, best_equiv, best_dist = anchor, equiv, dist
    return best_equiv


@pytest.mark.parametrize("bucket", ["bullet", "blitz", "rapid", "classical"])
def test_composed_grid_matches_converter_for_all_buckets(bucket: LichessTC) -> None:
    """Nearest-anchor grid selection reproduces convert_chesscom_to_lichess.

    For every native probe rating in the source-TC domain, the SQL-equivalent
    nearest-anchor pick on the composed grid must land within
    `_GRID_NEAREST_TOLERANCE` of the canonical converter output. This is the
    core correctness guarantee: the SQL path is result-equivalent to the
    Python converter for all 4 buckets.
    """
    source_tc = _BUCKET_TO_SOURCE_TC[bucket]
    grid = composed_chesscom_to_lichess_grid(source_tc, bucket)
    assert grid, f"grid empty for source_tc={source_tc!r}, target_tc={bucket!r}"
    # Probe across the grid's native domain.
    native_min = grid[0][0]
    native_max = grid[-1][0]
    checked = 0
    for probe in range(native_min, native_max + 1, _PROBE_STEP):
        expected = convert_chesscom_to_lichess(probe, source_tc, bucket)
        if expected is None:
            continue
        actual = _nearest_grid_equiv(grid, probe)
        assert abs(actual - expected) <= _GRID_NEAREST_TOLERANCE, (
            f"bucket={bucket} source_tc={source_tc} probe={probe}: "
            f"nearest-grid={actual} vs converter={expected} "
            f"exceeds tolerance {_GRID_NEAREST_TOLERANCE}"
        )
        checked += 1
    assert checked > 0, f"no valid probes for bucket={bucket}"


def test_composed_grid_blitz_values_equal_converter_at_grid_points() -> None:
    """Blitz grid values equal the converter exactly at each native grid point.

    Blitz is the table's native source TC: no inversion step is applied, so the
    grid value must be byte-equal to convert_chesscom_to_lichess at every native
    grid rating (this is the property that preserves correct blitz behavior).
    """
    grid = composed_chesscom_to_lichess_grid("blitz", "blitz")
    for native, equiv in grid:
        assert equiv == convert_chesscom_to_lichess(native, "blitz", "blitz"), (
            f"blitz grid point {native} -> {equiv} disagrees with converter"
        )


def test_composed_grid_omits_none_converter_rows() -> None:
    """Rows whose converter output is None are omitted from the grid.

    chess.com Blitz 2900/3000 have no Lichess Classical mapping (Table 2 None),
    so the classical grid (source_tc='rapid') must not contain any row whose
    converter output is None — every emitted equiv is a real int.
    """
    grid = composed_chesscom_to_lichess_grid("rapid", "classical")
    for native, equiv in grid:
        assert convert_chesscom_to_lichess(native, "rapid", "classical") is not None, (
            f"grid row {native} -> {equiv} maps to a None converter output"
        )


def test_composed_grid_fixes_rapid_inflation_bug() -> None:
    """Bug-repro: chess.com rapid ~1461 now maps to ~1795 lichess-rapid, not ~1915.

    OLD as-built behavior keyed the SQL lookup on chess.com BLITZ anchors and
    matched a native chess.com RAPID rating (1461) against the blitz scale: the
    nearest blitz anchor to 1461 is 1450, whose Lichess-rapid equiv is 1915 — an
    inflated, wrong-scale value. The composed grid is keyed on native chess.com
    RAPID ratings, so 1461 inverts (Table 1 rapid column) to a chess.com Blitz
    ~1300 and chains to Lichess-rapid ~1825, much closer to the converter's true
    value. The nearest-grid pick must agree with the converter (~1795), and must
    NOT be near the old inflated 1915.
    """
    probe = 1461
    converter_value = convert_chesscom_to_lichess(probe, "rapid", "rapid")
    assert converter_value is not None
    # Converter true value is well below the old blitz-keyed 1915.
    assert converter_value < 1900, (
        f"expected corrected rapid equiv well below old 1915, got {converter_value}"
    )
    grid = composed_chesscom_to_lichess_grid("rapid", "rapid")
    nearest = _nearest_grid_equiv(grid, probe)
    assert abs(nearest - converter_value) <= _GRID_NEAREST_TOLERANCE, (
        f"nearest-grid {nearest} disagrees with converter {converter_value}"
    )
    # The old blitz-keyed behavior would have returned ~1915 (Lichess-rapid at
    # chess.com Blitz anchor 1450). Assert the corrected path is clearly away
    # from that inflated value.
    old_inflated = CHESSCOM_BLITZ_TO_LICHESS[1450]["rapid"]
    assert old_inflated == 1915  # pin the old-behavior reference value
    assert abs(nearest - old_inflated) > _GRID_NEAREST_TOLERANCE, (
        f"corrected nearest-grid {nearest} is still near old inflated {old_inflated}"
    )
