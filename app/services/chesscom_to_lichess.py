"""ChessGoals chess.com ↔ Lichess + USCF/FIDE empirical rating conversion (Phase 94.4).

Snapshot source: https://chessgoals.com/rating-comparison/ (source page "Last
Updated: July 2025"; data re-fetched into this module on 2026-05-27).

Pure Python — no DB, no I/O. The two tables are the ChessGoals study output
(N=~10k profiles, per-TC empirical fit).

  * Table 1 (`CHESSCOM_INTRA_TC`):  chess.com Blitz anchor → chess.com Bullet,
    chess.com Rapid, USCF, FIDE. Used to invert chess.com Bullet / Rapid inputs
    back to a chess.com Blitz equivalent before chaining into Table 2.
  * Table 2 (`CHESSCOM_BLITZ_TO_LICHESS`): chess.com Blitz anchor → Lichess
    Bullet, Lichess Blitz, Lichess Rapid, Lichess Classical. Consumed by
    `convert_chesscom_to_lichess` (Phase 94.4 Plan 05 wires the call).

For non-Blitz chess.com inputs (Bullet, Rapid), invert Table 1 to estimate the
chess.com Blitz equivalent, then look up in Table 2. Inversion bias is
~10-30 Elo per the SEED-026 error budget — accepted as a known approximation
at the 50-Elo cohort granularity (refit-from-prod is a future trigger).

chess.com Daily has no ChessGoals mapping; conversion returns None and the
caller suppresses the chip for that (user, TC) combination (Pitfall 2).

Interpolation: bisect_left + linear interpolation between adjacent anchors;
clamp at edges (return None below min or above max — do NOT extrapolate beyond
the published 500–3000 chess.com Blitz range).

(Phase 149-04 PRUNE-02: the former Lichess-Blitz-anchored Table 3 and its two
USCF/FIDE lookups were removed as genuinely dead code — zero callers ever
consumed them.)

Phase 164 Plan 01 (SEED-093) adds the reverse Lichess-intra-TC direction:
`normalize_to_lichess_blitz` normalizes ANY (platform, source_tc) rating to
its Lichess-Blitz equivalent (Maia-3's training scale), inverting Table 2's
Bullet/Rapid/Classical columns via the new `_invert_table2_column` for
Lichess-native non-blitz inputs, and reusing `convert_chesscom_to_lichess`
for chess.com inputs. Correspondence (chess.com Daily) inputs return None
for both platforms via a caller-supplied `is_correspondence` flag, keeping
this module free of any `app.services.normalization` import.
"""

from __future__ import annotations

import bisect
from typing import Final, Literal, Mapping

from app.schemas.normalization import Platform, TimeControlBucket

# ---------------------------------------------------------------------------
# Snapshot provenance — per D-14, surfaced to user-facing tooltips downstream
# (Plan 07). Refresh tracked as a future trigger (SEED-026 §"Trigger conditions").
# ---------------------------------------------------------------------------

CHESSCOM_TO_LICHESS_TABLE_SNAPSHOT: Final[str] = "2026-05-27"
CHESSCOM_TO_LICHESS_SOURCE: Final[str] = "https://chessgoals.com/rating-comparison/"


# ---------------------------------------------------------------------------
# Type aliases — Literal over bare str per CLAUDE.md type-safety guideline.
# ---------------------------------------------------------------------------

ChessComSourceTC = Literal["bullet", "blitz", "rapid", "daily"]
LichessTC = Literal["bullet", "blitz", "rapid", "classical"]
ChessComIntraTC = Literal["bullet", "rapid", "uscf", "fide"]


# ---------------------------------------------------------------------------
# Table 1 — chess.com Blitz → chess.com Bullet / Rapid + USCF + FIDE.
# Canonical re-fetched 2026-05-27 snapshot. Supersedes the 2026-05-26 draft
# which had two errors: (1) the Bullet column was effectively the identity of
# the Blitz key on most rows (copy-paste artifact), and (2) the FIDE column
# was shifted at the low end (rows 500-900 had bogus values, rows 1000-1100
# were off by one). Re-fetched directly from the ChessGoals "Table 1" panel
# and re-verified row-by-row against the published snapshot. RESEARCH Pattern
# 8b, lines 927-960. N values from source: USCF (~130), FIDE (~85), chess.com
# Bullet (~130), chess.com Rapid (~115).
#
# FIDE is None on chess.com Blitz rows 500-900 (no published mapping; the
# ChessGoals study has no FIDE-rated profiles below the 1000 Blitz cohort).
#
# DO NOT edit numerics here. The snapshot is locked at the value level; any
# refit triggers a new module-level constant + a new module version.
# ---------------------------------------------------------------------------

CHESSCOM_INTRA_TC: Final[Mapping[int, Mapping[ChessComIntraTC, int | None]]] = {
    500: {"bullet": 445, "rapid": 735, "uscf": 715, "fide": None},
    600: {"bullet": 530, "rapid": 835, "uscf": 775, "fide": None},
    700: {"bullet": 620, "rapid": 945, "uscf": 860, "fide": None},
    800: {"bullet": 725, "rapid": 1035, "uscf": 930, "fide": None},
    900: {"bullet": 825, "rapid": 1130, "uscf": 1055, "fide": None},
    1000: {"bullet": 920, "rapid": 1230, "uscf": 1155, "fide": 1450},
    1100: {"bullet": 1020, "rapid": 1320, "uscf": 1280, "fide": 1490},
    1150: {"bullet": 1070, "rapid": 1365, "uscf": 1325, "fide": 1540},
    1200: {"bullet": 1115, "rapid": 1405, "uscf": 1350, "fide": 1555},
    1250: {"bullet": 1165, "rapid": 1450, "uscf": 1390, "fide": 1570},
    1300: {"bullet": 1205, "rapid": 1500, "uscf": 1435, "fide": 1610},
    1350: {"bullet": 1260, "rapid": 1540, "uscf": 1480, "fide": 1625},
    1400: {"bullet": 1305, "rapid": 1575, "uscf": 1530, "fide": 1650},
    1450: {"bullet": 1355, "rapid": 1610, "uscf": 1570, "fide": 1690},
    1500: {"bullet": 1400, "rapid": 1655, "uscf": 1595, "fide": 1710},
    1550: {"bullet": 1450, "rapid": 1695, "uscf": 1640, "fide": 1720},
    1600: {"bullet": 1510, "rapid": 1730, "uscf": 1675, "fide": 1735},
    1650: {"bullet": 1575, "rapid": 1780, "uscf": 1710, "fide": 1745},
    1700: {"bullet": 1615, "rapid": 1810, "uscf": 1750, "fide": 1770},
    1750: {"bullet": 1665, "rapid": 1850, "uscf": 1790, "fide": 1795},
    1800: {"bullet": 1715, "rapid": 1890, "uscf": 1815, "fide": 1810},
    1850: {"bullet": 1780, "rapid": 1940, "uscf": 1850, "fide": 1840},
    1900: {"bullet": 1825, "rapid": 1990, "uscf": 1880, "fide": 1880},
    1950: {"bullet": 1880, "rapid": 2010, "uscf": 1910, "fide": 1910},
    2000: {"bullet": 1930, "rapid": 2035, "uscf": 1940, "fide": 1925},
    2100: {"bullet": 2035, "rapid": 2080, "uscf": 2005, "fide": 1990},
    2200: {"bullet": 2155, "rapid": 2135, "uscf": 2085, "fide": 2055},
    2300: {"bullet": 2255, "rapid": 2190, "uscf": 2185, "fide": 2135},
    2400: {"bullet": 2355, "rapid": 2235, "uscf": 2210, "fide": 2210},
    2500: {"bullet": 2465, "rapid": 2290, "uscf": 2260, "fide": 2275},
    2600: {"bullet": 2570, "rapid": 2355, "uscf": 2315, "fide": 2350},
    2700: {"bullet": 2670, "rapid": 2425, "uscf": 2435, "fide": 2415},
    2800: {"bullet": 2785, "rapid": 2480, "uscf": 2500, "fide": 2470},
    2900: {"bullet": 2875, "rapid": 2545, "uscf": 2575, "fide": 2535},
    3000: {"bullet": 2985, "rapid": 2625, "uscf": 2685, "fide": 2590},
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
    2800: {"bullet": 2870, "blitz": 2695, "rapid": 2630, "classical": None},
    2900: {"bullet": 3005, "blitz": 2780, "rapid": 2705, "classical": None},
    3000: {"bullet": 3090, "blitz": 2850, "rapid": 2735, "classical": None},
}


# ---------------------------------------------------------------------------
# Anchor bounds — named constants per CLAUDE.md no-magic-numbers rule. Derived
# from the keys of the lookup tables above (kept in sync by inspection — the
# tables ARE the source of truth; these constants are convenience aliases).
# ---------------------------------------------------------------------------

_CHESSCOM_BLITZ_MIN_ANCHOR: Final[int] = 500
_CHESSCOM_BLITZ_MAX_ANCHOR: Final[int] = 3000

# Pre-sorted anchor key lists for bisect_left (module-load-time cost only).
_CHESSCOM_INTRA_KEYS: Final[list[int]] = sorted(CHESSCOM_INTRA_TC.keys())
_CHESSCOM_BLITZ_KEYS: Final[list[int]] = sorted(CHESSCOM_BLITZ_TO_LICHESS.keys())


# ---------------------------------------------------------------------------
# Native chess.com rating bounds per source TC — derived from the table
# constants (not hardcoded magic numbers), so a future snapshot refit keeps the
# composed-grid domain in sync automatically (quick-260529-js1).
#
#   * blitz  → the CHESSCOM_BLITZ_TO_LICHESS key range (native chess.com Blitz
#              is the table's own key, [500, 3000]).
#   * bullet → the min/max of the CHESSCOM_INTRA_TC `bullet` column (the native
#              chess.com Bullet ratings the Table-1 inversion can map).
#   * rapid  → the min/max of the CHESSCOM_INTRA_TC `rapid` column.
# ---------------------------------------------------------------------------


def _intra_tc_column_bounds(column: ChessComIntraTC) -> tuple[int, int]:
    """Return (min, max) of a fully-populated CHESSCOM_INTRA_TC column.

    Bullet/Rapid columns are non-None across all rows by the snapshot invariant
    (asserted in `_invert_intra_tc`), so the bounds are well-defined integers.
    """
    values = [row[column] for row in CHESSCOM_INTRA_TC.values()]
    populated = [v for v in values if v is not None]
    return min(populated), max(populated)


_CHESSCOM_BULLET_MIN_NATIVE, _CHESSCOM_BULLET_MAX_NATIVE = _intra_tc_column_bounds("bullet")
_CHESSCOM_RAPID_MIN_NATIVE, _CHESSCOM_RAPID_MAX_NATIVE = _intra_tc_column_bounds("rapid")

# Native-rating domain per source TC for the composed-grid builder.
_COMPOSED_NATIVE_BOUNDS: Final[Mapping[ChessComSourceTC, tuple[int, int]]] = {
    "blitz": (_CHESSCOM_BLITZ_MIN_ANCHOR, _CHESSCOM_BLITZ_MAX_ANCHOR),
    "bullet": (_CHESSCOM_BULLET_MIN_NATIVE, _CHESSCOM_BULLET_MAX_NATIVE),
    "rapid": (_CHESSCOM_RAPID_MIN_NATIVE, _CHESSCOM_RAPID_MAX_NATIVE),
}

# Composed-grid native-rating step. WHY 15: convert_chesscom_to_lichess is
# piecewise-linear, so a fine native grid keeps the SQL nearest-anchor
# reconstruction error vs the converter under the tolerance asserted in
# tests/services/test_chesscom_to_lichess.py (_GRID_NEAREST_TOLERANCE = 20).
# The steepest path is the bullet/rapid inversion in the high range
# (classical bucket, source_tc='rapid'): Table 1's rapid column is flat there
# (chess.com Blitz 2200->2300 moves rapid only 2135->2190, slope ~0.55), so a
# native-rapid step inverts to a ~1.8x larger Blitz step, then Table 2 amplifies
# again. Empirically a 25-pt step left a 26-pt worst-case error (over tolerance);
# a 15-pt step caps the measured worst-case error at 16 pts, comfortably inside
# the 20-pt tolerance (which itself exceeds half the max inter-grid delta).
_COMPOSED_GRID_STEP: Final[int] = 15


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
        "no published mapping in this row" — e.g. Table 2's Lichess Classical
        None rows above chess.com Blitz 2800, or Table 1's FIDE None rows
        below chess.com Blitz 1000).

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


def normalize_to_lichess_blitz(
    rating: int,
    platform: Platform,
    source_tc: TimeControlBucket,
    *,
    is_correspondence: bool,
) -> int | None:
    """Normalize any (platform, source_tc) rating to its Lichess-Blitz equivalent.

    Maia-3 is trained on Lichess Blitz games, so this is the single
    model-facing conversion every rating must pass through before seating
    Maia's ELO conditioning (SEED-093). Dispatch order:

      1. ``is_correspondence`` — correspondence games (chess.com Daily; a
         Lichess correspondence TC) have no real-time-play analogue in
         either ChessGoals table. Returns None for BOTH platforms regardless
         of ``source_tc``.
      2. ``platform == 'chess.com'`` — chess.com has no native Classical TC
         in the ChessGoals tables, so a ``source_tc == 'classical'`` game
         (which reaches here only when NOT correspondence, i.e. a genuine
         long real-time game such as ``3600+45``) is treated as rapid-scale
         and mapped to Table 1's Rapid column before converting — matching
         the module's own ``_BUCKET_TO_SOURCE_TC`` convention
         (``{"classical": "rapid", ...}``) already relied on by the SQL
         composed-grid pipeline, so both code paths agree. Bullet/Blitz/Rapid
         chain through the existing ``convert_chesscom_to_lichess`` to the
         Table 2 Blitz column.
      3. ``platform == 'lichess'`` — Blitz is the identity (rating is
         already on the target scale); Bullet/Rapid/Classical invert Table 2
         (``_invert_table2_column``) to recover a chess.com Blitz anchor,
         then chain into ``_interp_blitz_to_lichess`` for the Blitz value.

    Every branch returns None rather than raising or extrapolating (refuse
    rather than guess — matches the whole module's convention) when
    ``rating`` falls outside a table's published range, or a Table 2 column
    is None at the recovered anchor.

    ``is_correspondence`` is caller-supplied (not derived here) so this
    module stays free of an ``app.services.normalization`` import — the
    caller (``library_service.py``) already computes it via
    ``is_correspondence_time_control``.
    """
    if is_correspondence:
        return None
    if platform == "chess.com":
        # chess.com has no native Classical TC in the ChessGoals tables. A
        # classical-bucketed game reaching here is already non-correspondence
        # (guarded above), i.e. a genuine long real-time game — treat it as
        # rapid-scale, matching _BUCKET_TO_SOURCE_TC's existing convention so
        # this path agrees with the SQL composed-grid pipeline.
        effective_tc: ChessComSourceTC = "rapid" if source_tc == "classical" else source_tc
        return convert_chesscom_to_lichess(rating, effective_tc, "blitz")
    # platform == "lichess"
    if source_tc == "blitz":
        return rating
    blitz_equiv = _invert_table2_column(rating, source_tc)
    if blitz_equiv is None:
        return None
    return _interp_blitz_to_lichess(blitz_equiv, "blitz")


def composed_chesscom_to_lichess_grid(
    source_tc: ChessComSourceTC,
    target_tc: LichessTC,
) -> list[tuple[int, int]]:
    """Composed (native chess.com rating → Lichess equiv) lookup grid.

    Builds a list of ``(native_chesscom_rating, lichess_equiv)`` rows for the
    given ``source_tc``, where each ``lichess_equiv`` is produced by the
    canonical :func:`convert_chesscom_to_lichess` — this is the single source of
    truth (no SQL-side reimplementation of inversion or interpolation).

    The grid is keyed on NATIVE chess.com ratings for ``source_tc``:

      * ``source_tc='blitz'`` → each value equals
        ``convert_chesscom_to_lichess(rating, 'blitz', target_tc)`` exactly (no
        inversion step; blitz is the table's native source TC). This preserves
        the existing correct blitz behavior of the SQL anchor path.
      * ``source_tc in ('bullet', 'rapid')`` → each value is the two-step
        converter output (invert the intra-TC column to recover a chess.com
        Blitz equivalent, then Table-2 to ``target_tc``).
      * ``source_tc='daily'`` → returns an empty grid (no published mapping;
        Daily games are dropped upstream by the anchor pipeline).

    The native-rating domain is derived from the lookup-table constants
    (``_COMPOSED_NATIVE_BOUNDS``) so a future snapshot refit keeps the grid in
    sync. Ratings are stepped by ``_COMPOSED_GRID_STEP`` from the per-source
    min to max inclusive, always including the exact max bound. The 15-point step
    keeps the SQL nearest-anchor reconstruction error vs the converter well under
    the test tolerance (see the comment on ``_COMPOSED_GRID_STEP`` and the
    equivalence test in tests/services/test_chesscom_to_lichess.py).

    Rows whose converter output is None (rating outside the published domain, or
    a None target column such as Lichess Classical above chess.com Blitz 2800)
    are omitted.

    Why this exists (quick-260529-js1 bug fix): the SQL anchor pipeline
    (``_chesscom_conversion_values_sql``) previously keyed its VALUES lookup on
    chess.com Blitz anchors and matched every game's native rating against them
    regardless of the game's actual TC, skipping the intra-TC inversion the
    converter applies. That inflated rapid/classical anchors and deflated bullet.
    Keying the grid on native ratings per source TC makes the nearest-anchor
    LATERAL join correct.
    """
    bounds = _COMPOSED_NATIVE_BOUNDS.get(source_tc)
    if bounds is None:
        # source_tc='daily' — no published mapping.
        return []
    native_min, native_max = bounds
    # Step from min to max inclusive, always appending the exact max bound.
    natives = list(range(native_min, native_max + 1, _COMPOSED_GRID_STEP))
    if natives[-1] != native_max:
        natives.append(native_max)
    grid: list[tuple[int, int]] = []
    for native in natives:
        equiv = convert_chesscom_to_lichess(native, source_tc, target_tc)
        if equiv is not None:
            grid.append((native, equiv))
    return grid


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

    Table 1 Bullet and Rapid columns are strictly monotone in chess.com Blitz
    (post 2026-05-27 re-fetch). We scan sorted by Blitz key and find the bracket
    of two adjacent rows whose `source_tc` values straddle `rating`, then
    linear-interpolate the Blitz key between them. Returns None outside the
    published range. Only Bullet/Rapid columns are invertible — USCF/FIDE have
    None entries at the low end (Table 1 type allows None) and are not
    supported as source_tc.
    """
    # Build the source_tc column projected against the Blitz anchor keys.
    # Bullet and Rapid columns are guaranteed non-None across all rows by the
    # snapshot invariant; assert at module-load to surface any future drift.
    column_values: list[int] = []
    for anchor in _CHESSCOM_INTRA_KEYS:
        value = CHESSCOM_INTRA_TC[anchor][source_tc]
        assert value is not None, (
            f"Table 1 column {source_tc!r} unexpectedly None at Blitz anchor "
            f"{anchor} — Bullet/Rapid columns must be fully populated."
        )
        column_values.append(value)
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
        # Defensive: the 2026-05-27 re-fetch made Bullet and Rapid columns
        # strictly monotone, so this branch is unreachable for the current
        # snapshot. Kept in case a future refit reintroduces a tied row — fall
        # back to the lower Blitz anchor per the SEED-026 conservative-estimate
        # principle.
        return lo_blitz
    frac = (rating - lo_col) / (hi_col - lo_col)
    return round(lo_blitz + frac * (hi_blitz - lo_blitz))


# ---------------------------------------------------------------------------
# Table 2 inversion — Lichess-scale column → chess.com Blitz anchor
# (Phase 164 Plan 01, Task 1). Mirror direction of `_invert_intra_tc` above,
# but over Table 2 instead of Table 1.
# ---------------------------------------------------------------------------


def _invert_table2_column(
    rating: int,
    column: Literal["bullet", "rapid", "classical"],
) -> int | None:
    """Find the chess.com Blitz anchor whose Table 2 `column` value ≈ `rating`.

    Inverts one of Table 2's Lichess-scale columns (Bullet, Rapid, Classical)
    back to the chess.com Blitz anchor that produced it — the mirror
    direction of `_invert_intra_tc` (Table 1). Two differences from that
    function, both driven by Table 2's `classical` column:

      * None-gap: `classical` is None for chess.com Blitz 2800/2900/3000 (no
        published mapping above that anchor). Rows are FILTERED OUT before
        scanning here — unlike `_invert_intra_tc`'s `assert value is not
        None` loop, which only holds for Table 1's fully-populated
        Bullet/Rapid columns and would raise against this column.
      * Reachable tie: `classical` is flat at 1935 across chess.com Blitz
        anchors 1500/1550/1600. Ties resolve to the LOWEST anchor (leftmost
        occurrence via `bisect_left`), matching the SEED-026
        conservative-estimate convention documented on `_invert_intra_tc`
        (lines 417-423) — except here the tie is genuinely reachable (not
        "unreachable for current snapshot" defensive code) and covered by a
        dedicated test.

    Returns None when `rating` is below the column's minimum or above its
    maximum published (non-None) value — no extrapolation.
    """
    pairs = [
        (anchor, value)
        for anchor, row in CHESSCOM_BLITZ_TO_LICHESS.items()
        if (value := row[column]) is not None
    ]
    anchors = [a for a, _ in pairs]
    values = [v for _, v in pairs]
    if rating < values[0] or rating > values[-1]:
        return None
    idx = bisect.bisect_left(values, rating)
    if idx < len(values) and values[idx] == rating:
        # Leftmost-tie-wins: bisect_left already returns the first matching
        # index among any duplicate values (e.g. the three 1935 classical
        # ties resolve to anchor 1500, the lowest).
        return anchors[idx]
    if idx == 0:
        return None
    lo_val, hi_val = values[idx - 1], values[idx]
    lo_anchor, hi_anchor = anchors[idx - 1], anchors[idx]
    if hi_val == lo_val:
        # Zero-width guard — falls back to the lower anchor per the
        # conservative-estimate convention rather than dividing by zero.
        return lo_anchor
    frac = (rating - lo_val) / (hi_val - lo_val)
    return round(lo_anchor + frac * (hi_anchor - lo_anchor))


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
