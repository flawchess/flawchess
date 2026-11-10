"""Markdown sections of the blunder-check calibration report (SEED-261108-dk0, Phase 248).

Pure functions from a ``Collection`` (see sample.py) to markdown, so the same report renders
from a live sample or from a cache file. Every share prints its n. The report contains
aggregates only (T-248-10): no user ids, usernames, emails or per-user rows.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.services.maia_flaw_stats import RANK_BASE
from scripts.blunder_check.metrics import (
    ELO_BUCKETS,
    HAZARD,
    LEAD_IN_PLIES,
    MAX_BLUNDER_POSITION,
    MAX_MISS_SHARE,
    WINDOW_LENGTHS,
    EloBucket,
    FindabilityInputs,
    MissCase,
    Provenance,
    SupplyRates,
    blunder_fits_position,
    count_herring_windows,
    estimated_user_windows,
    findable,
    hazard_position_weights,
    herring_flags,
    in_band,
    weighted_fit_share,
)
from scripts.blunder_check.oddness import OddnessRow, summarize_group, summarize_oddness
from scripts.blunder_check.sample import (
    CALIBRATION_PLATFORMS,
    BlunderRecord,
    Collection,
    GameRecord,
    group_elo_bucket,
)

# ---------------------------------------------------------------------------
# Named constants (no magic numbers)
# ---------------------------------------------------------------------------

REFUTATION_PROB_GRID: tuple[float, ...] = (0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50)
MISS_PROB_GRID: tuple[float, ...] = (0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50)
ES_BAND_CANDIDATES: tuple[tuple[float, float], ...] = (
    (0.0, 1.0),
    (0.05, 0.95),
    (0.10, 0.90),
    (0.15, 0.85),
    (0.20, 0.80),
)
# Seed starting points for the recommended constants; overridable from the CLI.
DEFAULT_REFUTATION_THRESHOLD: float = 0.20
DEFAULT_MISS_THRESHOLD: float = 0.20
DEFAULT_BAND: tuple[float, float] = (0.10, 0.90)
# Seed: users with fewer usable blunder windows than this need the similar-rating fallback.
MIN_USER_WINDOWS: int = 50

CASES: tuple[MissCase, ...] = ("allowed", "pure_miss", "mixed", "unclassified")
GRID_CASES: tuple[MissCase, ...] = ("allowed", "pure_miss", "mixed")
PERCENT: float = 100.0
FIT_POSITIONS: tuple[int, ...] = tuple(range(1, MAX_BLUNDER_POSITION + 1))
PERCENTILES: tuple[int, ...] = (10, 25, 50, 75, 90)
PROVENANCES: tuple[Provenance, ...] = ("engine", "lichess")
# Table rows: every bucket, then None for the pooled "all" row.
ROW_BUCKETS: tuple[EloBucket | None, ...] = (*ELO_BUCKETS, None)


@dataclass(frozen=True)
class ReportParams:
    """Thresholds the report evaluates its supply estimate at (recommendation only)."""

    refutation_threshold: float = DEFAULT_REFUTATION_THRESHOLD
    miss_threshold: float = DEFAULT_MISS_THRESHOLD
    band_low: float = DEFAULT_BAND[0]
    band_high: float = DEFAULT_BAND[1]
    min_user_windows: int = MIN_USER_WINDOWS
    # File name of the companion spot-check, named in the Recommended constants section.
    spot_check_file: str | None = None


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def fmt_share(numerator: int | float, denominator: int) -> str:
    """'52.3% (n=130)', or 'n/a (n=0)' when there is nothing to divide by."""
    if denominator == 0:
        return "n/a (n=0)"
    return f"{PERCENT * numerator / denominator:.1f}% (n={denominator})"


def fmt_ratio(numerator: float, denominator: int, digits: int = 3) -> str:
    """'0.412 (n=130)' for per-game rates."""
    if denominator == 0:
        return "n/a (n=0)"
    return f"{numerator / denominator:.{digits}f} (n={denominator})"


def md_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """A GitHub-flavoured markdown table."""
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(" --- " for _ in headers) + "|"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def _band_label(low: float, high: float) -> str:
    return f"[{low:.2f}, {high:.2f}]"


# ---------------------------------------------------------------------------
# Population filters
# ---------------------------------------------------------------------------


def analysis_blunders(collection: Collection) -> list[BlunderRecord]:
    """User-side blunders of rated, non-guest games (guest flaws are never Maia-scored)."""
    return [b for b in collection.blunders if not b.is_guest]


def analysis_games(collection: Collection) -> list[GameRecord]:
    """Rated, non-guest sampled games."""
    return [g for g in collection.games if not g.is_guest and g.bucket is not None]


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def section_how_to_read(collection: Collection, params: ReportParams) -> str:
    meta = collection.meta
    sample_rate = meta.permille / 1000 * 100
    return "\n".join(
        [
            "## How to read this report",
            "",
            f"- **Population:** fully evaluated games on {', '.join(CALIBRATION_PLATFORMS)} "
            "(pasted and bot games are out). Database: "
            f"`{meta.db_name}`. Run date: {meta.date}.",
            f"- **Sampling:** deterministic, {meta.permille} permille ({sample_rate:.1f}%) of games "
            "chosen by md5 residue of the game id; the same sample on every re-run"
            + (f", capped at the first {meta.limit_games} game ids." if meta.limit_games else "."),
            "- **Expected score (ES):** every ES comes from the flaw classifier's own per-ply "
            "pass (`_run_all_moves_pass`), from the mover's point of view. Pre-move ES is the ES "
            "before the user's move, `ES_played` the ES after the blunder, `ES_ref` the user's ES "
            "before the opponent's previous move (what the user would have had without the gift).",
            "- **Cases (D-13):** *allowed* = the blunder is not a miss (the opponent's previous "
            "move was not a mistake or blunder). *Pure miss* = a miss whose `ES_played` is at "
            "least `ES_ref` minus the inaccuracy drop: the user only gave back what the opponent "
            "gifted. *Mixed* = a miss that lost more than the gift. *Unclassified* = a miss "
            "without usable ES.",
            "- **Findability (D-14):** allowed blunders test Maia's probability of the "
            "refutation, pure misses Maia's probability of the best move, mixed ones pass if "
            "either does; a pair passes at threshold t when its probability is at least t or "
            "its rank is 1.",
            f"- **Hazard model (D-16):** per-move blunder hazard {HAZARD}, window length "
            f"uniform over 3 to 5 user moves, {LEAD_IN_PLIES} lead-in plies. Pure misses are "
            f"capped at {MAX_MISS_SHARE:.0%} of the blunder supply.",
            "- **Estimates:** the per-user supply uses exact per-user counts from SELECT-only "
            "aggregates times per-bucket sample rates, with rating groups approximating each "
            "game's exact Elo. It is an estimate, not an exact count.",
            f"- **Chosen values:** refutation R = {params.refutation_threshold}, "
            f"best-move X' = {params.miss_threshold}, eval band "
            f"{_band_label(params.band_low, params.band_high)}. These are a recommendation "
            "only; no constant is wired into app code in this phase.",
            "- Guest users' flaws are never Maia-scored, so guest games are excluded from every "
            "section except the sample counts.",
        ]
    )


def section_sample(collection: Collection) -> str:
    meta = collection.meta
    guests = sum(1 for g in collection.games if g.is_guest)
    games_by_cell = Counter((g.bucket, g.provenance) for g in analysis_games(collection))
    blunders_by_cell = Counter((b.bucket, b.provenance) for b in analysis_blunders(collection))
    rows = []
    for bucket in ELO_BUCKETS:
        rows.append(
            [
                bucket,
                str(games_by_cell[(bucket, "engine")]),
                str(games_by_cell[(bucket, "lichess")]),
                str(blunders_by_cell[(bucket, "engine")]),
                str(blunders_by_cell[(bucket, "lichess")]),
            ]
        )
    summary = [
        f"- Games sampled: {meta.games_sampled} ({guests} guest, excluded below)",
        f"- Games skipped for a ply gap: {meta.games_gap_skipped}",
        f"- Unrated games (no rating at game time): {meta.games_unrated}"
        f" ({meta.blunders_unrated} user-side blunders not bucketed)",
        f"- User-side blunders (rated, non-guest): {len(analysis_blunders(collection))}",
    ]
    table = md_table(
        [
            "Elo bucket",
            "games (engine)",
            "games (lichess)",
            "blunders (engine)",
            "blunders (lichess)",
        ],
        rows,
    )
    return "\n".join(["## Sample", "", *summary, "", table])


def section_control(collection: Collection) -> str:
    agree = sum(g.control_agree for g in collection.games)
    total = sum(g.control_total for g in collection.games)
    return "\n".join(
        [
            "## Control",
            "",
            "Stored `game_flaws` (ply, severity) pairs against the mistakes and blunders recomputed "
            "from the per-ply evals (all sampled games, both colors; D-13).",
            "",
            f"- Agreement: {agree} of {total} = {fmt_share(agree, total)}",
        ]
    )


def section_cases(collection: Collection) -> str:
    blunders = analysis_blunders(collection)
    counts = Counter((b.bucket, b.case) for b in blunders)
    rows = []
    for bucket in ELO_BUCKETS:
        total = sum(counts[(bucket, case)] for case in CASES)
        cells = [fmt_share(counts[(bucket, case)], total) for case in CASES]
        misses = counts[(bucket, "pure_miss")] + counts[(bucket, "mixed")]
        rows.append([bucket, str(total), *cells, fmt_share(counts[(bucket, "mixed")], misses)])
    overall_total = len(blunders)
    overall_misses = sum(1 for b in blunders if b.case in ("pure_miss", "mixed"))
    overall_mixed = sum(1 for b in blunders if b.case == "mixed")
    overall = [
        "all",
        str(overall_total),
        *[fmt_share(sum(1 for b in blunders if b.case == case), overall_total) for case in CASES],
        fmt_share(overall_mixed, overall_misses),
    ]
    table = md_table(
        ["Elo bucket", "blunders", *CASES, "mixed / (pure miss + mixed)"], [*rows, overall]
    )
    return "\n".join(["## Cases by Elo bucket", "", table])


# ---------------------------------------------------------------------------
# Selection helpers (pure)
# ---------------------------------------------------------------------------


def _label(bucket: EloBucket | None) -> str:
    return "all" if bucket is None else bucket


def _in_bucket[T: (BlunderRecord, GameRecord)](
    items: Sequence[T], bucket: EloBucket | None
) -> list[T]:
    return list(items) if bucket is None else [i for i in items if i.bucket == bucket]


def _inputs(b: BlunderRecord) -> FindabilityInputs:
    return FindabilityInputs(
        refutation_prob=b.maia_refutation_prob,
        refutation_rank=b.maia_refutation_rank,
        best_prob=b.maia_best_prob,
        best_rank=b.maia_best_rank,
    )


def is_scored(b: BlunderRecord) -> bool:
    """True when the Maia pair the case tests is stored (a NULL pair is unscored, never a fail)."""
    if b.case == "allowed":
        return b.maia_refutation_prob is not None
    if b.case == "pure_miss":
        return b.maia_best_prob is not None
    if b.case == "mixed":
        return b.maia_refutation_prob is not None or b.maia_best_prob is not None
    return False


def is_rank_one(b: BlunderRecord) -> bool:
    """Maia's top choice for the tested move (either pair for mixed)."""
    refutation_top = b.maia_refutation_rank == RANK_BASE
    best_top = b.maia_best_rank == RANK_BASE
    if b.case == "allowed":
        return refutation_top
    if b.case == "pure_miss":
        return best_top
    return refutation_top or best_top


def qualifying_blunders(
    blunders: Sequence[BlunderRecord], params: ReportParams
) -> list[BlunderRecord]:
    """Blunders findable at the chosen R and X' (D-14)."""
    return [
        b
        for b in blunders
        if findable(b.case, _inputs(b), params.refutation_threshold, params.miss_threshold)
    ]


def usable_blunders(blunders: Sequence[BlunderRecord], params: ReportParams) -> list[BlunderRecord]:
    """Qualifying blunders whose pre-move ES is inside the eval band."""
    return [
        b
        for b in qualifying_blunders(blunders, params)
        if in_band(b.es_before, params.band_low, params.band_high)
    ]


def blunder_fits(b: BlunderRecord, position: int, params: ReportParams) -> bool:
    """D-16: window position `position` is satisfied by the preceding Good, in-band user moves."""
    return blunder_fits_position(
        b.preceding, b.es_before, position, params.band_low, params.band_high
    )


def fit_shares(usable: Sequence[BlunderRecord], params: ReportParams) -> dict[int, float]:
    """Share of usable blunders fitting each window position; empty when there are none."""
    if not usable:
        return {}
    return {
        k: sum(1 for b in usable if blunder_fits(b, k, params)) / len(usable) for k in FIT_POSITIONS
    }


def herring_totals(games: Sequence[GameRecord], low: float, high: float) -> dict[int, int]:
    """Disjoint herring windows summed over games, per window length (band on every judged move)."""
    totals = dict.fromkeys(WINDOW_LENGTHS, 0)
    for game in games:
        flags = herring_flags(game.judgements, low, high)
        for length in WINDOW_LENGTHS:
            totals[length] += count_herring_windows(flags, length)
    return totals


def herring_uniform_per_game(games: Sequence[GameRecord], low: float, high: float) -> float:
    """Windows per game averaged uniformly over the window lengths; 0 for no games."""
    if not games:
        return 0.0
    totals = herring_totals(games, low, high)
    return sum(totals.values()) / len(WINDOW_LENGTHS) / len(games)


def bucket_rates(
    blunders: Sequence[BlunderRecord], params: ReportParams
) -> dict[EloBucket, SupplyRates]:
    """Per-bucket rates per user-side blunder feeding the per-user supply estimate (D-23)."""
    weights = hazard_position_weights()["normalized"]
    rates: dict[EloBucket, SupplyRates] = {}
    for bucket in ELO_BUCKETS:
        subset = _in_bucket(blunders, bucket)
        if not subset:
            continue
        usable = usable_blunders(subset, params)
        pure = sum(1 for b in usable if b.case == "pure_miss")
        rates[bucket] = SupplyRates(
            non_pure_rate=(len(usable) - pure) / len(subset),
            pure_rate=pure / len(subset),
            fit_share=weighted_fit_share(fit_shares(usable, params), weights),
        )
    return rates


def percentile(values: Sequence[float], q: int) -> float | None:
    """Linear-interpolation percentile; None for no values."""
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q / PERCENT
    low = math.floor(position)
    high = math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def user_supply(
    collection: Collection, params: ReportParams, provenance: Provenance | None
) -> list[tuple[float, float]]:
    """(usable blunder windows, herring windows) per non-guest user, from exact counts x rates."""
    blunders = [b for b in analysis_blunders(collection) if provenance in (None, b.provenance)]
    games = [g for g in analysis_games(collection) if provenance in (None, g.provenance)]
    rates = bucket_rates(blunders, params)
    herring_rate: dict[EloBucket, float] = {
        bucket: herring_uniform_per_game(
            _in_bucket(games, bucket), params.band_low, params.band_high
        )
        for bucket in ELO_BUCKETS
    }
    counts: dict[int, Counter[EloBucket]] = {}
    herring: dict[int, float] = {}
    for group in collection.user_groups:
        if provenance not in (None, group.provenance):
            continue
        bucket = group_elo_bucket(group)
        counts.setdefault(group.user_id, Counter())[bucket] += group.user_blunders
        herring[group.user_id] = (
            herring.get(group.user_id, 0.0) + group.games * herring_rate[bucket]
        )
    return [(estimated_user_windows(counts[u], rates), herring[u]) for u in sorted(counts)]


# ---------------------------------------------------------------------------
# Sections (continued)
# ---------------------------------------------------------------------------


def _findability_table(
    blunders: Sequence[BlunderRecord],
    case: MissCase,
    grid: Sequence[float],
    passes: Callable[[BlunderRecord, float], bool],
) -> str:
    rows = []
    for bucket in ROW_BUCKETS:
        subset = [b for b in _in_bucket(blunders, bucket) if b.case == case]
        scored = [b for b in subset if is_scored(b)]
        cells = [fmt_share(sum(1 for b in scored if passes(b, t)), len(scored)) for t in grid]
        rank_one = fmt_share(sum(1 for b in scored if is_rank_one(b)), len(scored))
        rows.append(
            [_label(bucket), str(len(scored)), str(len(subset) - len(scored)), rank_one, *cells]
        )
    headers = [
        "Elo bucket",
        "n scored",
        "unscored (NULL pair)",
        "rank 1 only",
        *[f"{t:.2f}" for t in grid],
    ]
    return md_table(headers, rows)


def section_findability_grid(collection: Collection, params: ReportParams) -> str:
    blunders = analysis_blunders(collection)

    def allowed_passes(b: BlunderRecord, t: float) -> bool:
        return findable("allowed", _inputs(b), t, params.miss_threshold)

    def pure_passes(b: BlunderRecord, t: float) -> bool:
        return findable("pure_miss", _inputs(b), params.refutation_threshold, t)

    def mixed_passes(b: BlunderRecord, t: float) -> bool:
        return findable("mixed", _inputs(b), t, t)

    return "\n".join(
        [
            "## Findability grid",
            "",
            "Share of scored blunders passing the Maia test at each threshold t (D-14); unscored "
            "(NULL pair) blunders are counted separately and excluded from every denominator. "
            "A pair passes at t when its probability is at least t or its rank is 1; the "
            "`rank 1 only` column counts rank 1 alone.",
            "",
            "### Allowed (refutation pair, t = R)",
            "",
            _findability_table(blunders, "allowed", REFUTATION_PROB_GRID, allowed_passes),
            "",
            "### Pure miss (best-move pair, t = X')",
            "",
            _findability_table(blunders, "pure_miss", MISS_PROB_GRID, pure_passes),
            "",
            "### Mixed (either pair passes, R = X' = t)",
            "",
            _findability_table(blunders, "mixed", REFUTATION_PROB_GRID, mixed_passes),
        ]
    )


def section_eval_band(collection: Collection, params: ReportParams) -> str:
    qualifying = qualifying_blunders(analysis_blunders(collection), params)
    games = analysis_games(collection)
    headers = ["band", *[_label(b) for b in ROW_BUCKETS]]
    share_rows = []
    herring_rows = []
    for low, high in ES_BAND_CANDIDATES:
        shares = []
        herring = []
        for bucket in ROW_BUCKETS:
            subset = _in_bucket(qualifying, bucket)
            shares.append(
                fmt_share(sum(1 for b in subset if in_band(b.es_before, low, high)), len(subset))
            )
            bucket_games = _in_bucket(games, bucket)
            herring.append(
                f"{herring_uniform_per_game(bucket_games, low, high):.3f} (n={len(bucket_games)})"
            )
        share_rows.append([_band_label(low, high), *shares])
        herring_rows.append([_band_label(low, high), *herring])
    return "\n".join(
        [
            "## Eval band",
            "",
            "Pre-move ES bounds (D-15), at the chosen R and X'. First table: share of qualifying "
            "(findable) blunders whose pre-move ES is inside the band. Second table: disjoint "
            "herring windows per game, averaged uniformly over window lengths 3 to 5, with the "
            "band applied to every judged user move.",
            "",
            md_table(headers, share_rows),
            "",
            md_table(headers, herring_rows),
        ]
    )


def section_window_fit(collection: Collection, params: ReportParams) -> str:
    usable = usable_blunders(analysis_blunders(collection), params)
    weights = hazard_position_weights()
    rows = []
    for bucket in ROW_BUCKETS:
        subset = _in_bucket(usable, bucket)
        shares = fit_shares(subset, params)
        fits = [fmt_share(shares.get(k, 0.0) * len(subset), len(subset)) for k in FIT_POSITIONS]
        weighted = weighted_fit_share(shares, weights["normalized"])
        rows.append(
            [
                _label(bucket),
                str(len(subset)),
                *fits,
                fmt_share(weighted * len(subset), len(subset)),
            ]
        )
    weight_rows = [
        [str(k), f"{weights['raw'][k]:.4f}", f"{weights['normalized'][k]:.4f}"]
        for k in FIT_POSITIONS
    ]
    headers = [
        "Elo bucket",
        "usable blunders",
        *[f"pos {k}" for k in FIT_POSITIONS],
        "hazard-weighted",
    ]
    return "\n".join(
        [
            "## Window fit",
            "",
            "Share of usable blunders (findable and pre-move ES in band) whose k-1 preceding user "
            "moves are all Good and in band, for window positions 1 to 5 (D-16). The last column "
            "weights the positions with the normalized hazard weights below.",
            "",
            md_table(headers, rows),
            "",
            f"Hazard {HAZARD}, window length uniform over {WINDOW_LENGTHS}; herring (no-blunder) "
            f"share {weights['herring_share']:.4f}.",
            "",
            md_table(["position", "raw P(blunder at k)", "normalized weight"], weight_rows),
        ]
    )


def section_herring_supply(collection: Collection, params: ReportParams) -> str:
    games = analysis_games(collection)
    rows = []
    for bucket in ROW_BUCKETS:
        subset = _in_bucket(games, bucket)
        totals = herring_totals(subset, params.band_low, params.band_high)
        per_game = [
            f"{totals[length] / len(subset):.3f}" if subset else "n/a" for length in WINDOW_LENGTHS
        ]
        uniform = (
            f"{herring_uniform_per_game(subset, params.band_low, params.band_high):.3f}"
            if subset
            else "n/a"
        )
        rows.append([_label(bucket), str(len(subset)), *per_game, uniform])
    headers = ["Elo bucket", "games", *[f"L={n}" for n in WINDOW_LENGTHS], "L-uniform mean"]
    return "\n".join(
        [
            "## Herring supply",
            "",
            f"Disjoint windows of L consecutive Good user moves with pre-move ES in "
            f"{_band_label(params.band_low, params.band_high)}, per sampled game. Each maximal run "
            "of qualifying moves contributes floor(run / L) windows.",
            "",
            md_table(headers, rows),
        ]
    )


def _percentile_cells(values: Sequence[float]) -> list[str]:
    cells = []
    for q in PERCENTILES:
        value = percentile(values, q)
        cells.append("n/a" if value is None else f"{value:.1f}")
    return cells


def section_supply_per_user(collection: Collection, params: ReportParams) -> str:
    supply = user_supply(collection, params, None)
    blunder_windows = [b for b, _ in supply]
    herring_windows = [h for _, h in supply]
    under = sum(1 for w in blunder_windows if w < params.min_user_windows)
    rows = [
        ["usable blunder windows", *_percentile_cells(blunder_windows)],
        ["herring windows", *_percentile_cells(herring_windows)],
    ]
    return "\n".join(
        [
            "## Supply per user",
            "",
            "**Estimate** (D-16, D-23), not an exact count: exact per-user counts of user-side "
            "blunders and fully evaluated games (non-guest users, SELECT-only aggregates) times "
            "per-bucket sample rates at the chosen thresholds, after the "
            f"{MAX_MISS_SHARE:.0%} cap on pure misses. Rating groups approximate each game's "
            "exact Elo.",
            "",
            f"- Non-guest users with a fully evaluated game: {len(supply)}",
            f"- Users under {params.min_user_windows} usable blunder windows (need the "
            f"similar-rating fallback): {f'{under} of {len(supply)}'}",
            "",
            md_table(["per user", *[f"p{q}" for q in PERCENTILES]], rows),
        ]
    )


def section_provenance(collection: Collection, params: ReportParams) -> str:
    rows = []
    for provenance in PROVENANCES:
        blunders = [b for b in analysis_blunders(collection) if b.provenance == provenance]
        games = [g for g in analysis_games(collection) if g.provenance == provenance]
        usable = usable_blunders(blunders, params)
        weighted = weighted_fit_share(
            fit_shares(usable, params), hazard_position_weights()["normalized"]
        )
        supply = user_supply(collection, params, provenance)
        blunder_windows = [b for b, _ in supply]
        under = sum(1 for w in blunder_windows if w < params.min_user_windows)
        pcts = _percentile_cells(blunder_windows)
        rows.append(
            [
                provenance,
                str(len(games)),
                str(len(blunders)),
                str(len(usable)),
                fmt_share(weighted * len(usable), len(usable)),
                f"{herring_uniform_per_game(games, params.band_low, params.band_high):.3f}",
                str(len(supply)),
                f"{pcts[0]} / {pcts[2]} / {pcts[4]}",
                f"{under} of {len(supply)}",
            ]
        )
    headers = [
        "provenance",
        "games",
        "blunders",
        "usable blunders",
        "hazard-weighted fit",
        "herring windows per game",
        "users",
        "blunder windows p10 / p50 / p90",
        f"users under {params.min_user_windows}",
    ]
    return "\n".join(
        [
            "## Provenance",
            "",
            "Engine full evals against lichess `%eval` games (provenance = whether the game "
            "carries lichess evals). Rates, fit and supply are recomputed inside each provenance.",
            "",
            md_table(headers, rows),
        ]
    )


def _quartile_cell(q: tuple[float, float, float] | None) -> str:
    return "n/a" if q is None else f"{q[0]:.3f} / {q[1]:.3f} / {q[2]:.3f}"


def _share_cell(share: float | None) -> str:
    return "n/a" if share is None else f"{PERCENT * share:.1f}%"


def _oddness_cells(row: OddnessRow) -> list[str]:
    return [
        str(row.n_good),
        str(row.n_blunder),
        _quartile_cell(row.good_quartiles),
        _quartile_cell(row.blunder_quartiles),
        _share_cell(row.good_rank1_share),
        _share_cell(row.blunder_rank1_share),
        "n/a" if row.auc is None else f"{row.auc:.3f}",
    ]


def section_arrow_oddness(collection: Collection, params: ReportParams) -> str:
    """D-17: does the arrow's oddness (Maia probability of the played move) separate blunders from Good moves?"""
    good = [
        g for g in collection.oddness if in_band(g.es_before, params.band_low, params.band_high)
    ]
    blunders = usable_blunders(analysis_blunders(collection), params)
    by_bucket = summarize_oddness(good, blunders)
    rows = [[bucket, *_oddness_cells(by_bucket[bucket])] for bucket in ELO_BUCKETS]
    rows.append(["all", *_oddness_cells(summarize_group(good, blunders))])
    headers = [
        "Elo bucket",
        "n Good",
        "n blunder",
        "Good prob q1 / median / q3",
        "blunder prob q1 / median / q3",
        "Good rank 1",
        "blunder rank 1",
        "AUC",
    ]
    meta = collection.meta
    return "\n".join(
        [
            "## Arrow oddness",
            "",
            "Maia's probability of the move actually played, at the user's pinned Elo on the exact "
            "pre-move board (D-17). Good moves are a seeded sample of judged Good user moves "
            f"({meta.oddness_sample} per bucket requested, seed {meta.seed}, "
            f"{meta.oddness_skipped} not scorable) with pre-move ES inside "
            f"{_band_label(params.band_low, params.band_high)}. Blunders are the usable ones at the "
            "chosen R, X' and band, with their stored played-move probability.",
            "",
            "AUC is P(Good probability > blunder probability) + 0.5 P(tie). 0.5 means the arrow's "
            "oddness leaks nothing; near 1 means blunders look odd and flagging odd-looking arrows "
            "wins without reading the position.",
            "",
            md_table(headers, rows),
        ]
    )


def section_recommended_constants(collection: Collection, params: ReportParams) -> str:
    """D-18: the chosen R, X' and eval band with their pass shares and supply, as a recommendation only."""
    blunders = analysis_blunders(collection)
    rows = []
    for bucket in ROW_BUCKETS:
        subset = _in_bucket(blunders, bucket)
        cells = []
        for case in GRID_CASES:
            scored = [b for b in subset if b.case == case and is_scored(b)]
            passing = qualifying_blunders(scored, params)
            cells.append(fmt_share(len(passing), len(scored)))
        usable = usable_blunders(subset, params)
        weighted = weighted_fit_share(
            fit_shares(usable, params), hazard_position_weights()["normalized"]
        )
        rows.append([_label(bucket), *cells, fmt_share(weighted * len(usable), len(usable))])
    supply = user_supply(collection, params, None)
    blunder_median = percentile([b for b, _ in supply], 50)
    herring_median = percentile([h for _, h in supply], 50)
    under = sum(1 for b, _ in supply if b < params.min_user_windows)
    headers = [
        "Elo bucket",
        "allowed pass",
        "pure miss pass",
        "mixed pass",
        "hazard-weighted window fit (usable blunders)",
    ]
    lines = [
        "## Recommended constants",
        "",
        f"- Refutation threshold **R = {params.refutation_threshold}** (allowed blunders).",
        f"- Best-move threshold **X' = {params.miss_threshold}** (pure misses).",
        f"- Eval band **{_band_label(params.band_low, params.band_high)}** on the pre-move ES.",
        "",
        "These are a recommendation only: nothing here is wired into app code, and the owner "
        "decides the final values. Re-render with other thresholds from the cache to compare.",
        "",
        "Pass shares at these values (scored blunders only; the share in parentheses is the "
        "denominator) and the hazard-weighted share of usable blunders that fit a window:",
        "",
        md_table(headers, rows),
        "",
        f"Resulting supply per non-guest user (estimate): median "
        f"{'n/a' if blunder_median is None else f'{blunder_median:.1f}'} usable blunder windows and "
        f"{'n/a' if herring_median is None else f'{herring_median:.1f}'} herring windows; "
        f"{under} of {len(supply)} users are under {params.min_user_windows} blunder windows.",
    ]
    if params.spot_check_file:
        lines += ["", f"Read the spot-check before choosing: `{params.spot_check_file}`."]
    return "\n".join(lines)


def render_report(collection: Collection, params: ReportParams) -> str:
    """Assemble the whole dated report."""
    sections = [
        "# Blunder-check calibration report",
        section_how_to_read(collection, params),
        section_sample(collection),
        section_control(collection),
        section_cases(collection),
        section_findability_grid(collection, params),
        section_eval_band(collection, params),
        section_window_fit(collection, params),
        section_herring_supply(collection, params),
        section_supply_per_user(collection, params),
        section_provenance(collection, params),
        section_arrow_oddness(collection, params),
        section_recommended_constants(collection, params),
    ]
    return "\n\n".join(sections) + "\n"
