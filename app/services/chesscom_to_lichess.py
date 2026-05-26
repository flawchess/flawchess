"""ChessGoals chess.com ↔ Lichess + USCF/FIDE empirical rating conversion (Phase 94.4).

Snapshot source: https://chessgoals.com/rating-comparison/ (source page "Last
Updated: July 2025"; data re-fetched into this module on 2026-05-26).

Pure Python — no DB, no I/O. The three tables are the ChessGoals study output
(N=~10k profiles, per-TC empirical fit).

  * Table 1 (`CHESSCOM_INTRA_TC`):  chess.com Blitz anchor → chess.com Bullet,
    chess.com Rapid, USCF, FIDE. Used to invert chess.com Bullet / Rapid inputs
    back to a chess.com Blitz equivalent before chaining into Table 2.
  * Table 2 (`CHESSCOM_BLITZ_TO_LICHESS`): chess.com Blitz anchor → Lichess
    Bullet, Lichess Blitz, Lichess Rapid, Lichess Classical. Consumed by
    `convert_chesscom_to_lichess` (Phase 94.4 Plan 05 wires the call).
  * Table 3 (`LICHESS_BLITZ_INTRA_TC`): Lichess Blitz anchor → Lichess Bullet,
    Lichess Rapid, Lichess Classical, USCF, FIDE. Ships per D-14 for future
    surfaces (federation cohorts, opponent normalisation, scout view); no
    Phase 94.4 caller consumes it yet.

For non-Blitz chess.com inputs (Bullet, Rapid), invert Table 1 to estimate the
chess.com Blitz equivalent, then look up in Table 2. Inversion bias is
~10-30 Elo per the SEED-026 error budget — accepted as a known approximation
at the 50-Elo cohort granularity (refit-from-prod is a future trigger).

chess.com Daily has no ChessGoals mapping; conversion returns None and the
caller suppresses the chip for that (user, TC) combination (Pitfall 2).

Interpolation: bisect_left + linear interpolation between adjacent anchors;
clamp at edges (return None below min or above max — do NOT extrapolate beyond
the published 500–3000 chess.com Blitz / 1030-2850 Lichess Blitz range).
"""

from __future__ import annotations

import bisect
from typing import Final, Literal, Mapping

# ---------------------------------------------------------------------------
# Snapshot provenance — per D-14, surfaced to user-facing tooltips downstream
# (Plan 07). Refresh tracked as a future trigger (SEED-026 §"Trigger conditions").
# ---------------------------------------------------------------------------

CHESSCOM_TO_LICHESS_TABLE_SNAPSHOT: Final[str] = "2026-05-26"
CHESSCOM_TO_LICHESS_SOURCE: Final[str] = "https://chessgoals.com/rating-comparison/"


# ---------------------------------------------------------------------------
# Type aliases — Literal over bare str per CLAUDE.md type-safety guideline.
# ---------------------------------------------------------------------------

ChessComSourceTC = Literal["bullet", "blitz", "rapid", "daily"]
LichessTC = Literal["bullet", "blitz", "rapid", "classical"]
ChessComIntraTC = Literal["bullet", "rapid", "uscf", "fide"]
LichessIntraTC = Literal["bullet", "rapid", "classical", "uscf", "fide"]


# ---------------------------------------------------------------------------
# Table 1 — chess.com Blitz → chess.com Bullet / Rapid + USCF + FIDE.
# Canonical re-fetched 2026-05-26 snapshot (supersedes the earlier draft that
# had a copy-paste irregularity at 1050/1150). RESEARCH Pattern 8b, lines
# 927-960. N values from source: USCF (~130), FIDE (~85), chess.com Bullet
# (~130), chess.com Rapid (~115).
#
# DO NOT edit numerics here. The snapshot is locked at the value level; any
# refit triggers a new module-level constant + a new module version.
# ---------------------------------------------------------------------------

CHESSCOM_INTRA_TC: Final[Mapping[int, Mapping[ChessComIntraTC, int]]] = {
    500: {"bullet": 445, "rapid": 735, "uscf": 715, "fide": 600},
    600: {"bullet": 600, "rapid": 835, "uscf": 775, "fide": 700},
    700: {"bullet": 700, "rapid": 945, "uscf": 860, "fide": 800},
    800: {"bullet": 800, "rapid": 1035, "uscf": 930, "fide": 900},
    900: {"bullet": 900, "rapid": 1130, "uscf": 1055, "fide": 1000},
    1000: {"bullet": 1000, "rapid": 1230, "uscf": 1155, "fide": 1100},
    1100: {"bullet": 1150, "rapid": 1320, "uscf": 1280, "fide": 1450},
    1150: {"bullet": 1150, "rapid": 1365, "uscf": 1325, "fide": 1540},
    1200: {"bullet": 1200, "rapid": 1405, "uscf": 1350, "fide": 1555},
    1250: {"bullet": 1250, "rapid": 1450, "uscf": 1390, "fide": 1570},
    1300: {"bullet": 1300, "rapid": 1500, "uscf": 1435, "fide": 1610},
    1350: {"bullet": 1350, "rapid": 1540, "uscf": 1480, "fide": 1625},
    1400: {"bullet": 1400, "rapid": 1575, "uscf": 1530, "fide": 1650},
    1450: {"bullet": 1450, "rapid": 1610, "uscf": 1570, "fide": 1690},
    1500: {"bullet": 1500, "rapid": 1655, "uscf": 1595, "fide": 1710},
    1550: {"bullet": 1550, "rapid": 1695, "uscf": 1640, "fide": 1720},
    1600: {"bullet": 1600, "rapid": 1730, "uscf": 1675, "fide": 1735},
    1700: {"bullet": 1700, "rapid": 1810, "uscf": 1750, "fide": 1770},
    1800: {"bullet": 1800, "rapid": 1890, "uscf": 1815, "fide": 1810},
    1850: {"bullet": 1850, "rapid": 1940, "uscf": 1850, "fide": 1840},
    1900: {"bullet": 1900, "rapid": 1990, "uscf": 1880, "fide": 1880},
    1950: {"bullet": 1950, "rapid": 2010, "uscf": 1910, "fide": 1910},
    2000: {"bullet": 2000, "rapid": 2035, "uscf": 1940, "fide": 1925},
    2100: {"bullet": 2100, "rapid": 2080, "uscf": 2005, "fide": 1990},
    2200: {"bullet": 2200, "rapid": 2135, "uscf": 2085, "fide": 2055},
    2300: {"bullet": 2300, "rapid": 2190, "uscf": 2185, "fide": 2135},
    2400: {"bullet": 2400, "rapid": 2235, "uscf": 2210, "fide": 2210},
    2500: {"bullet": 2500, "rapid": 2290, "uscf": 2260, "fide": 2275},
    2600: {"bullet": 2600, "rapid": 2355, "uscf": 2315, "fide": 2350},
    2700: {"bullet": 2700, "rapid": 2425, "uscf": 2435, "fide": 2415},
    2800: {"bullet": 2800, "rapid": 2480, "uscf": 2500, "fide": 2470},
    2900: {"bullet": 2900, "rapid": 2545, "uscf": 2575, "fide": 2535},
    3000: {"bullet": 3000, "rapid": 2625, "uscf": 2685, "fide": 2590},
}


# ---------------------------------------------------------------------------
# Table 2 — chess.com Blitz → Lichess Bullet/Blitz/Rapid/Classical.
# Canonical re-fetched 2026-05-26 snapshot (RESEARCH Pattern 8b, lines 968-1003).
# N values from source: lichess_blitz (2489), lichess_bullet (1945),
# lichess_rapid (1344), lichess_classical (314).
#
# NOTE: Lichess Classical is None for chess.com Blitz 2900/3000 in the source
# (insufficient classical data above that rating). chess.com Daily has no
# ChessGoals mapping — convert_chesscom_to_lichess returns None for
# source_tc='daily' (Pitfall 2, no Table 2 lookup).
# ---------------------------------------------------------------------------

CHESSCOM_BLITZ_TO_LICHESS: Final[Mapping[int, Mapping[LichessTC, int | None]]] = {
    500: {"bullet": 975, "blitz": 1030, "rapid": 1205, "classical": 1405},
    600: {"bullet": 1010, "blitz": 1075, "rapid": 1270, "classical": 1435},
    700: {"bullet": 1075, "blitz": 1145, "rapid": 1340, "classical": 1495},
    800: {"bullet": 1115, "blitz": 1200, "rapid": 1400, "classical": 1555},
    900: {"bullet": 1200, "blitz": 1335, "rapid": 1515, "classical": 1625},
    1000: {"bullet": 1295, "blitz": 1420, "rapid": 1615, "classical": 1715},
    1100: {"bullet": 1385, "blitz": 1475, "rapid": 1690, "classical": 1770},
    1150: {"bullet": 1435, "blitz": 1525, "rapid": 1730, "classical": 1795},
    1200: {"bullet": 1475, "blitz": 1565, "rapid": 1765, "classical": 1810},
    1250: {"bullet": 1530, "blitz": 1605, "rapid": 1795, "classical": 1830},
    1300: {"bullet": 1575, "blitz": 1635, "rapid": 1825, "classical": 1850},
    1350: {"bullet": 1630, "blitz": 1670, "rapid": 1850, "classical": 1855},
    1400: {"bullet": 1675, "blitz": 1705, "rapid": 1880, "classical": 1865},
    1450: {"bullet": 1720, "blitz": 1745, "rapid": 1915, "classical": 1915},
    1500: {"bullet": 1770, "blitz": 1780, "rapid": 1930, "classical": 1935},
    1550: {"bullet": 1805, "blitz": 1815, "rapid": 1965, "classical": 1935},
    1600: {"bullet": 1845, "blitz": 1850, "rapid": 1990, "classical": 1935},
    1650: {"bullet": 1895, "blitz": 1895, "rapid": 2020, "classical": 1985},
    1700: {"bullet": 1920, "blitz": 1910, "rapid": 2035, "classical": 2000},
    1750: {"bullet": 1960, "blitz": 1950, "rapid": 2055, "classical": 2010},
    1800: {"bullet": 2000, "blitz": 1970, "rapid": 2085, "classical": 2030},
    1850: {"bullet": 2040, "blitz": 2005, "rapid": 2115, "classical": 2045},
    1900: {"bullet": 2110, "blitz": 2050, "rapid": 2135, "classical": 2070},
    1950: {"bullet": 2145, "blitz": 2075, "rapid": 2155, "classical": 2095},
    2000: {"bullet": 2195, "blitz": 2100, "rapid": 2185, "classical": 2100},
    2100: {"bullet": 2255, "blitz": 2170, "rapid": 2240, "classical": 2125},
    2200: {"bullet": 2330, "blitz": 2235, "rapid": 2285, "classical": 2195},
    2300: {"bullet": 2400, "blitz": 2295, "rapid": 2330, "classical": 2245},
    2400: {"bullet": 2490, "blitz": 2370, "rapid": 2380, "classical": 2340},
    2500: {"bullet": 2560, "blitz": 2445, "rapid": 2445, "classical": 2360},
    2600: {"bullet": 2700, "blitz": 2560, "rapid": 2510, "classical": 2435},
    2700: {"bullet": 2765, "blitz": 2625, "rapid": 2595, "classical": 2500},
    2800: {"bullet": 2870, "blitz": 2695, "rapid": 2630, "classical": 2500},
    2900: {"bullet": 3005, "blitz": 2780, "rapid": 2705, "classical": None},
    3000: {"bullet": 3090, "blitz": 2850, "rapid": 2735, "classical": None},
}


# ---------------------------------------------------------------------------
# Table 3 — Lichess Blitz → Lichess Bullet/Rapid/Classical + USCF + FIDE.
# Canonical re-fetched 2026-05-26 snapshot (RESEARCH Pattern 8b, lines 1009-1044).
#
# Ships per D-14 for future surfaces (federation-specific cohort overlays,
# opponent-rating normalisation, scout view). No Phase 94.4 caller consumes
# Table 3 yet; the four module-level lookup_* helpers expose typed access.
#
# Multiple None values in source: lichess_classical None for top 3 rows
# (2695, 2780, 2850); USCF None for top row (2850); FIDE None for bottom
# 6 rows (1030..1420) AND top row (2850).
# ---------------------------------------------------------------------------

LICHESS_BLITZ_INTRA_TC: Final[Mapping[int, Mapping[LichessIntraTC, int | None]]] = {
    1030: {"bullet": 975, "rapid": 1205, "classical": 1405, "uscf": 715, "fide": None},
    1075: {"bullet": 1010, "rapid": 1270, "classical": 1435, "uscf": 775, "fide": None},
    1145: {"bullet": 1075, "rapid": 1340, "classical": 1495, "uscf": 860, "fide": None},
    1200: {"bullet": 1115, "rapid": 1400, "classical": 1555, "uscf": 930, "fide": None},
    1335: {"bullet": 1200, "rapid": 1515, "classical": 1625, "uscf": 1055, "fide": None},
    1420: {"bullet": 1295, "rapid": 1615, "classical": 1715, "uscf": 1155, "fide": None},
    1475: {"bullet": 1385, "rapid": 1690, "classical": 1770, "uscf": 1280, "fide": 1490},
    1525: {"bullet": 1435, "rapid": 1730, "classical": 1795, "uscf": 1325, "fide": 1540},
    1565: {"bullet": 1475, "rapid": 1765, "classical": 1810, "uscf": 1350, "fide": 1555},
    1605: {"bullet": 1530, "rapid": 1795, "classical": 1830, "uscf": 1390, "fide": 1570},
    1635: {"bullet": 1575, "rapid": 1825, "classical": 1850, "uscf": 1435, "fide": 1610},
    1670: {"bullet": 1630, "rapid": 1850, "classical": 1855, "uscf": 1480, "fide": 1625},
    1705: {"bullet": 1675, "rapid": 1880, "classical": 1865, "uscf": 1530, "fide": 1650},
    1745: {"bullet": 1720, "rapid": 1915, "classical": 1915, "uscf": 1570, "fide": 1690},
    1780: {"bullet": 1770, "rapid": 1930, "classical": 1935, "uscf": 1595, "fide": 1710},
    1815: {"bullet": 1805, "rapid": 1965, "classical": 1935, "uscf": 1640, "fide": 1720},
    1850: {"bullet": 1845, "rapid": 1990, "classical": 1935, "uscf": 1675, "fide": 1735},
    1895: {"bullet": 1895, "rapid": 2020, "classical": 1985, "uscf": 1710, "fide": 1745},
    1910: {"bullet": 1920, "rapid": 2035, "classical": 2000, "uscf": 1750, "fide": 1770},
    1950: {"bullet": 1960, "rapid": 2055, "classical": 2010, "uscf": 1790, "fide": 1795},
    1970: {"bullet": 2000, "rapid": 2085, "classical": 2030, "uscf": 1815, "fide": 1810},
    2005: {"bullet": 2040, "rapid": 2115, "classical": 2045, "uscf": 1850, "fide": 1840},
    2050: {"bullet": 2110, "rapid": 2135, "classical": 2070, "uscf": 1880, "fide": 1880},
    2075: {"bullet": 2145, "rapid": 2155, "classical": 2095, "uscf": 1910, "fide": 1910},
    2100: {"bullet": 2195, "rapid": 2185, "classical": 2100, "uscf": 1940, "fide": 1925},
    2170: {"bullet": 2255, "rapid": 2240, "classical": 2125, "uscf": 2005, "fide": 1990},
    2235: {"bullet": 2330, "rapid": 2285, "classical": 2195, "uscf": 2085, "fide": 2055},
    2295: {"bullet": 2400, "rapid": 2330, "classical": 2245, "uscf": 2185, "fide": 2135},
    2370: {"bullet": 2490, "rapid": 2380, "classical": 2340, "uscf": 2210, "fide": 2210},
    2445: {"bullet": 2560, "rapid": 2445, "classical": 2360, "uscf": 2260, "fide": 2275},
    2560: {"bullet": 2700, "rapid": 2510, "classical": 2435, "uscf": 2315, "fide": 2350},
    2625: {"bullet": 2765, "rapid": 2595, "classical": 2500, "uscf": 2435, "fide": 2415},
    2695: {"bullet": 2870, "rapid": 2630, "classical": None, "uscf": 2575, "fide": 2535},
    2780: {"bullet": 3005, "rapid": 2705, "classical": None, "uscf": 2685, "fide": 2590},
    2850: {"bullet": 3090, "rapid": 2735, "classical": None, "uscf": None, "fide": None},
}


# ---------------------------------------------------------------------------
# Anchor bounds — named constants per CLAUDE.md no-magic-numbers rule. Derived
# from the keys of the lookup tables above (kept in sync by inspection — the
# tables ARE the source of truth; these constants are convenience aliases).
# ---------------------------------------------------------------------------

_CHESSCOM_BLITZ_MIN_ANCHOR: Final[int] = 500
_CHESSCOM_BLITZ_MAX_ANCHOR: Final[int] = 3000
_LICHESS_BLITZ_MIN_ANCHOR: Final[int] = 1030
_LICHESS_BLITZ_MAX_ANCHOR: Final[int] = 2850

# Pre-sorted anchor key lists for bisect_left (module-load-time cost only).
_CHESSCOM_INTRA_KEYS: Final[list[int]] = sorted(CHESSCOM_INTRA_TC.keys())
_CHESSCOM_BLITZ_KEYS: Final[list[int]] = sorted(CHESSCOM_BLITZ_TO_LICHESS.keys())
_LICHESS_BLITZ_KEYS: Final[list[int]] = sorted(LICHESS_BLITZ_INTRA_TC.keys())


# ---------------------------------------------------------------------------
# Generic interpolation helper.
# ---------------------------------------------------------------------------


def _interp_int_column(
    keys: list[int],
    rating: int,
    lookup: Mapping[int, int | None],
) -> int | None:
    """Linear-interpolate `rating` against `keys` using `lookup` for column values.

    Returns None when:
      * `rating` is below `keys[0]` or above `keys[-1]` (no extrapolation).
      * Either of the two anchor values flanking `rating` is None (sentinel for
        "no published mapping in this row" — Table 3 USCF/FIDE/classical
        edges).

    Returns the lookup value directly when `rating` is exactly an anchor.
    """
    if rating < keys[0] or rating > keys[-1]:
        return None
    # Exact-anchor short-circuit.
    if rating in lookup:
        value = lookup[rating]
        return value if value is not None else None
    # bisect_left returns the index where rating would be inserted; for an
    # interior point this is the index of the upper anchor.
    idx = bisect.bisect_left(keys, rating)
    lo_key = keys[idx - 1]
    hi_key = keys[idx]
    lo_val = lookup[lo_key]
    hi_val = lookup[hi_key]
    if lo_val is None or hi_val is None:
        # Cannot interpolate across a None gap — refuse rather than guess.
        return None
    span = hi_key - lo_key
    if span == 0:
        return lo_val
    frac = (rating - lo_key) / span
    return round(lo_val + frac * (hi_val - lo_val))


# ---------------------------------------------------------------------------
# chess.com → Lichess conversion (Phase 94.4 caller, Plan 05 wires Stage A).
# ---------------------------------------------------------------------------


def convert_chesscom_to_lichess(
    rating: int,
    source_tc: ChessComSourceTC,
    target_tc: LichessTC,
) -> int | None:
    """Convert a chess.com rating to a Lichess-equivalent rating.

    Algorithm (RESEARCH Pattern 8 lines 880-913):
      1. ``source_tc == 'daily'`` → return None (no published mapping;
         Pitfall 2 — caller suppresses the chip for that (user, TC)).
      2. ``source_tc == 'blitz'`` → linear-interp lookup in
         ``CHESSCOM_BLITZ_TO_LICHESS`` against ``target_tc`` column.
      3. ``source_tc in ('bullet', 'rapid')`` → invert ``CHESSCOM_INTRA_TC``
         (find chess.com Blitz equivalent of ``rating`` on the
         ``source_tc`` column), then chain into Table 2 at the recovered
         Blitz value.

    Returns None when rating falls outside the published [500, 3000] chess.com
    Blitz range, or when Table 2's ``target_tc`` column is None at the recovered
    anchor (e.g. chess.com Blitz 2900/3000 have no Lichess Classical mapping).
    """
    if source_tc == "daily":
        return None
    if source_tc == "blitz":
        return _interp_blitz_to_lichess(rating, target_tc)
    # bullet or rapid — invert Table 1 to recover chess.com Blitz equivalent.
    blitz_equiv = _invert_intra_tc(rating, source_tc)
    if blitz_equiv is None:
        return None
    return _interp_blitz_to_lichess(blitz_equiv, target_tc)


def _interp_blitz_to_lichess(blitz_rating: int, target_tc: LichessTC) -> int | None:
    """Interpolate chess.com Blitz `blitz_rating` against Table 2 `target_tc` column."""
    column: dict[int, int | None] = {
        anchor: row[target_tc] for anchor, row in CHESSCOM_BLITZ_TO_LICHESS.items()
    }
    return _interp_int_column(_CHESSCOM_BLITZ_KEYS, blitz_rating, column)


def _invert_intra_tc(
    rating: int,
    source_tc: Literal["bullet", "rapid"],
) -> int | None:
    """Find chess.com Blitz anchor whose Table 1 `source_tc` column ≈ `rating`.

    Table 1 columns are monotone non-decreasing in chess.com Blitz (modulo the
    one tied row at 1100/1150 in the Bullet column — both equal 1150). We scan
    sorted by Blitz key and find the bracket of two adjacent rows whose
    `source_tc` values straddle `rating`, then linear-interpolate the Blitz key
    between them. Returns None outside the published range or when the column
    is non-monotone in the bracket (cannot invert deterministically).
    """
    # Build the source_tc column projected against the Blitz anchor keys.
    column_values: list[int] = [
        # Both columns ('bullet', 'rapid') are typed int in Table 1 (never None).
        # The cast below is safe because CHESSCOM_INTRA_TC's value type is
        # Mapping[..., int] (no None entries in Table 1).
        CHESSCOM_INTRA_TC[anchor][source_tc]
        for anchor in _CHESSCOM_INTRA_KEYS
    ]
    if rating < column_values[0] or rating > column_values[-1]:
        return None
    # Linear scan for the first index where column_values[i] >= rating.
    # (Monotone non-decreasing assumption; bisect_left works because Python
    # bisect handles equal-keys deterministically.)
    idx = bisect.bisect_left(column_values, rating)
    # Exact match on an anchor row.
    if idx < len(column_values) and column_values[idx] == rating:
        return _CHESSCOM_INTRA_KEYS[idx]
    # idx is the position where rating would be inserted; lo = idx-1, hi = idx.
    if idx == 0:
        # rating < column_values[0]; caught above, but defensive.
        return None
    lo_col = column_values[idx - 1]
    hi_col = column_values[idx]
    lo_blitz = _CHESSCOM_INTRA_KEYS[idx - 1]
    hi_blitz = _CHESSCOM_INTRA_KEYS[idx]
    if hi_col == lo_col:
        # Tied column values (e.g. Bullet at 1100/1150 both = 1150). Fall back
        # to the lower anchor — the inversion is ambiguous and we prefer the
        # lower Blitz reading per the SEED-026 conservative-estimate principle.
        return lo_blitz
    frac = (rating - lo_col) / (hi_col - lo_col)
    return round(lo_blitz + frac * (hi_blitz - lo_blitz))


# ---------------------------------------------------------------------------
# USCF + FIDE accessors (D-14 future-use — no Phase 94.4 caller).
# ---------------------------------------------------------------------------


def lookup_uscf_from_chesscom_blitz(rating: int) -> int | None:
    """USCF rating from a chess.com Blitz rating (Table 1 ``uscf`` column).

    Linear interpolation between adjacent anchors; returns None outside the
    [500, 3000] chess.com Blitz range. No Phase 94.4 caller (D-14 future-use).
    """
    column: dict[int, int | None] = {
        anchor: row["uscf"] for anchor, row in CHESSCOM_INTRA_TC.items()
    }
    return _interp_int_column(_CHESSCOM_INTRA_KEYS, rating, column)


def lookup_fide_from_chesscom_blitz(rating: int) -> int | None:
    """FIDE rating from a chess.com Blitz rating (Table 1 ``fide`` column).

    Linear interpolation between adjacent anchors; returns None outside the
    [500, 3000] chess.com Blitz range. No Phase 94.4 caller (D-14 future-use).
    """
    column: dict[int, int | None] = {
        anchor: row["fide"] for anchor, row in CHESSCOM_INTRA_TC.items()
    }
    return _interp_int_column(_CHESSCOM_INTRA_KEYS, rating, column)


def lookup_uscf_from_lichess_blitz(rating: int) -> int | None:
    """USCF rating from a Lichess Blitz rating (Table 3 ``uscf`` column).

    Linear interpolation between adjacent anchors; returns None outside the
    [1030, 2850] Lichess Blitz range. Top row (Lichess Blitz 2850) has
    USCF=None — interpolation refuses to cross the None gap, so ratings near
    the top edge may return None. No Phase 94.4 caller (D-14 future-use).
    """
    column: dict[int, int | None] = {
        anchor: row["uscf"] for anchor, row in LICHESS_BLITZ_INTRA_TC.items()
    }
    return _interp_int_column(_LICHESS_BLITZ_KEYS, rating, column)


def lookup_fide_from_lichess_blitz(rating: int) -> int | None:
    """FIDE rating from a Lichess Blitz rating (Table 3 ``fide`` column).

    Linear interpolation between adjacent anchors; returns None outside the
    [1030, 2850] Lichess Blitz range. The 6 lowest-rated rows
    (Lichess Blitz 1030..1420) AND the top row (2850) have FIDE=None in the
    source — interpolation refuses to cross None gaps. No Phase 94.4 caller
    (D-14 future-use).
    """
    column: dict[int, int | None] = {
        anchor: row["fide"] for anchor, row in LICHESS_BLITZ_INTRA_TC.items()
    }
    return _interp_int_column(_LICHESS_BLITZ_KEYS, rating, column)
