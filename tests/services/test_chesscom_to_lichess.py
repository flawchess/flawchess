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
    # `classical` does, at chess.com Blitz 2900/3000).
    assert low is not None and high is not None
    result = convert_chesscom_to_lichess(1525, "blitz", "blitz")
    assert result is not None
    # Must lie strictly between the two endpoints (interpolation, not clamp).
    assert low < result < high
    # Specifically: midway is the average, rounded.
    expected = round((low + high) / 2)
    assert result == expected


# -----------------------------------------------------------------------------
# Test 3: chess.com Bullet 1500 → Lichess Bullet.
# Inversion chain: find chess.com Blitz row whose bullet column ≈ 1500.
# Re-fetched Table 1: chess.com Blitz 1500 has bullet=1500 exactly (irregularity
# at 1100/1150 fixed in re-fetch). So inversion yields Blitz≈1500, then look up
# Table 2[1500]["bullet"] = 1770.
# -----------------------------------------------------------------------------
def test_chesscom_bullet_to_lichess_bullet_via_table_inversion() -> None:
    # CHESSCOM_INTRA_TC[1500]["bullet"] == 1500 (the re-fetched canonical row).
    assert CHESSCOM_INTRA_TC[1500]["bullet"] == 1500
    result = convert_chesscom_to_lichess(1500, "bullet", "bullet")
    # Chain: invert Table 1 (1500 → chesscom_blitz 1500) → Table 2[1500]["bullet"]=1770.
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
# Plus: lookup_fide_from_lichess_blitz returns None for the 6 below-1475 rows
# where the FIDE column is None in the snapshot (Lichess Blitz 1030..1420).
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


# Snapshot-Null rows: Lichess Blitz <= 1420 has FIDE = None in the source.
def test_lookup_fide_from_lichess_blitz_returns_none_in_null_region() -> None:
    # Lichess Blitz 1030 has FIDE=None per snapshot.
    assert lookup_fide_from_lichess_blitz(1030) is None


# -----------------------------------------------------------------------------
# Test 13: Snapshot constants present and correct.
# -----------------------------------------------------------------------------
def test_snapshot_constants() -> None:
    assert CHESSCOM_TO_LICHESS_TABLE_SNAPSHOT == "2026-05-26"
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
        (lookup_fide_from_chesscom_blitz, 500, 600),
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
