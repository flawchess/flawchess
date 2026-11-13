"""Markdown sections of the blunder-check calibration report (SEED-261108-dk0, Phase 248, 250).

Pure functions from a ``Collection`` (see sample.py) to markdown, so the same report renders
from a live sample or from a cache file. Every share prints its n. The report contains
aggregates only (T-248-10): no user ids, usernames, emails or per-user rows.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal

from app.services.blunder_check_rules import (
    BLUNDER_CHECK_SESSION_WINDOWS,
    FACEPALM_SCORE_MIN,
    FOREIGN_BLUNDER_SHARE,
    FOREIGN_RATING_BAND,
    HERRING_SHARE,
    LINE_DEPTH,
    OWN_BLUNDER_SHARE,
)
from scripts.blunder_check.metrics import (
    ELO_BUCKET_EDGES,
    ELO_BUCKETS,
    HAZARD,
    LEAD_IN_PLIES,
    MAX_BLUNDER_POSITION,
    MAX_MISS_SHARE,
    WINDOW_LENGTHS,
    EloBucket,
    MissCase,
    Provenance,
    SupplyRates,
    blunder_fits_position,
    blunder_position_marginals,
    count_herring_windows,
    estimated_user_windows,
    herring_flags,
    in_band,
    weighted_fit_share,
)
from scripts.blunder_check.metrics import quartiles
from scripts.blunder_check.oddness import OddnessRow, summarize_group, summarize_oddness
from scripts.blunder_check.sample import (
    CALIBRATION_PLATFORMS,
    PERMILLE_BASE,
    BlunderRecord,
    Collection,
    GameRecord,
    group_elo_bucket,
)

# ---------------------------------------------------------------------------
# Named constants (no magic numbers)
# ---------------------------------------------------------------------------

# Facepalm-score thresholds the pass shares are printed at (the chosen threshold is added).
FACEPALM_THRESHOLD_GRID: tuple[float, ...] = (0.5, 0.6, 0.7, 0.8)
ES_BAND_CANDIDATES: tuple[tuple[float, float], ...] = (
    (0.0, 1.0),
    (0.05, 0.95),
    (0.10, 0.90),
    (0.15, 0.85),
    (0.20, 0.80),
)
# Seed starting points for the recommended constants; overridable from the CLI.
DEFAULT_FACEPALM_THRESHOLD: float = FACEPALM_SCORE_MIN
DEFAULT_BAND: tuple[float, float] = (0.10, 0.90)
# Seed: users with fewer usable blunder windows than this need the similar-rating fallback.
MIN_USER_WINDOWS: int = 50

CASES: tuple[MissCase, ...] = ("allowed", "pure_miss", "mixed", "unclassified")
PERCENT: float = 100.0
# 250 D-03 proxy: a stored line that wins at least this many material points counts as an obvious punishment.
FAIR_LOSS_MIN: int = 2
# The owner's label study (2026-11-13, 250 D-01): fair share among passers at each score threshold.
OWNER_LABEL_FAIR_SHARE: tuple[tuple[float, float], ...] = ((0.5, 0.80), (0.7, 0.89), (0.8, 0.92))
FIT_POSITIONS: tuple[int, ...] = tuple(range(1, MAX_BLUNDER_POSITION + 1))
PERCENTILES: tuple[int, ...] = (10, 25, 50, 75, 90)
PROVENANCES: tuple[Provenance, ...] = ("engine", "lichess")
NullReason = Literal["no_spread", "no_line", "line_too_short", "other"]
NULL_REASONS: tuple[NullReason, ...] = ("no_spread", "no_line", "line_too_short", "other")
NULL_REASON_LABELS: dict[NullReason, str] = {
    "no_spread": "no spread",
    "no_line": "no line",
    "line_too_short": "line too short",
    "other": "no played prob",
}
# Pinned-Elo levels of the foreign supply table (250 D-10): from below the lowest bucket edge to
# above the highest, FOREIGN_LEVEL_STEP apart.
FOREIGN_LEVEL_MIN: int = 600
FOREIGN_LEVEL_MAX: int = 2600
FOREIGN_LEVEL_STEP: int = 200
# Table rows: every bucket, then None for the pooled "all" row.
ROW_BUCKETS: tuple[EloBucket | None, ...] = (*ELO_BUCKETS, None)


@dataclass(frozen=True)
class ReportParams:
    """Thresholds the report evaluates its supply estimate at (recommendation only)."""

    facepalm_threshold: float = DEFAULT_FACEPALM_THRESHOLD
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
            "- **Facepalm score (250 D-01):** a ranking of how careless a blunder is at the "
            "mover's level, fitted on the owner's labels and stored on `game_flaws` from the "
            "played move's Maia probability, the opponent's reply spread and the material the "
            "stored engine line wins. It is not a probability and not a share of peers; a "
            "blunder qualifies when its score is at least the chosen threshold. A blunder "
            "without a score never qualifies; the Facepalm score section tells why.",
            f"- **Window mix (250 D-12):** every slot independently draws a herring "
            f"({HERRING_SHARE:.0%}), an own blunder ({OWN_BLUNDER_SHARE:.0%}) or a foreign blunder "
            f"({FOREIGN_BLUNDER_SHARE:.0%}); window length is uniform over "
            f"{WINDOW_LENGTHS[0]} to {WINDOW_LENGTHS[-1]} user moves for both kinds, a blunder's "
            f"position follows the per-move hazard {HAZARD} within that length, "
            f"{LEAD_IN_PLIES} lead-in plies. Pure misses are capped at {MAX_MISS_SHARE:.0%} of the "
            "blunder supply (report estimate only).",
            "- **Estimates:** the per-user supply uses exact per-user counts from SELECT-only "
            "aggregates times per-bucket sample rates, with rating groups approximating each "
            "game's exact Elo. It is an estimate, not an exact count.",
            f"- **Chosen values:** facepalm threshold = {params.facepalm_threshold}, eval band "
            f"{_band_label(params.band_low, params.band_high)}. These are a recommendation "
            "only; no constant is wired into app code by this report.",
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


def is_scored(b: BlunderRecord) -> bool:
    """True when the blunder has a stored facepalm score (a NULL score is unscored, never a fail)."""
    return b.facepalm_score is not None


def qualifying_blunders(
    blunders: Sequence[BlunderRecord], params: ReportParams
) -> list[BlunderRecord]:
    """Blunders whose facepalm score reaches the chosen threshold (250 D-01); NULL never qualifies."""
    return [
        b
        for b in blunders
        if b.facepalm_score is not None and b.facepalm_score >= params.facepalm_threshold
    ]


def usable_blunders(blunders: Sequence[BlunderRecord], params: ReportParams) -> list[BlunderRecord]:
    """Qualifying (facepalm) blunders whose pre-move ES is inside the eval band."""
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
    weights = blunder_position_marginals()
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


def null_reason(b: BlunderRecord) -> NullReason | None:
    """Why a blunder has no facepalm score, None when it has one (checked in this order).

    No spread: Maia has not scored the post-blunder position. No line: the game stores no
    engine line after the blunder. Line too short: a line exists but does not reach LINE_DEPTH
    plies (or cannot be replayed) and holds no early mate, so the loss is unknown. Other: the
    remaining inputs are there but the played-move probability is not.
    """
    if b.facepalm_score is not None:
        return None
    if b.maia_reply_spread is None:
        return "no_spread"
    if not b.has_line:
        return "no_line"
    if b.maia_played_prob is None:
        return "other"
    return "line_too_short"


def pass_thresholds(params: ReportParams) -> tuple[float, ...]:
    """The grid thresholds plus the chosen one, ascending."""
    return tuple(sorted({*FACEPALM_THRESHOLD_GRID, params.facepalm_threshold}))


def _facepalm_row(label: str, subset: Sequence[BlunderRecord], params: ReportParams) -> list[str]:
    scored = [b for b in subset if is_scored(b)]
    reasons = Counter(null_reason(b) for b in subset)
    scores = [b.facepalm_score for b in scored if b.facepalm_score is not None]
    passes = [
        fmt_share(sum(1 for s in scores if s >= threshold), len(scores))
        for threshold in pass_thresholds(params)
    ]
    qualifying = qualifying_blunders(subset, params)
    return [
        label,
        str(len(subset)),
        fmt_share(len(scored), len(subset)),
        *[fmt_share(reasons[reason], len(subset)) for reason in NULL_REASONS],
        *passes,
        fmt_share(len(qualifying), len(subset)),
        _quartile_cell(quartiles(scores)),
    ]


def section_facepalm_score(collection: Collection, params: ReportParams) -> str:
    """D-10: the facepalm score per Elo bucket: scored share, NULL reasons, pass shares, quartiles."""
    blunders = analysis_blunders(collection)
    rows = [
        _facepalm_row(_label(bucket), _in_bucket(blunders, bucket), params)
        for bucket in ROW_BUCKETS
    ]
    headers = [
        "Elo bucket",
        "user blunders",
        "scored",
        *[NULL_REASON_LABELS[reason] for reason in NULL_REASONS],
        *[f"pass >= {t:.2f}" for t in pass_thresholds(params)],
        f"qualifying of all (>= {params.facepalm_threshold:.2f})",
        "score q1 / median / q3",
    ]
    return "\n".join(
        [
            "## Facepalm score",
            "",
            "User-side blunders of rated, non-guest games and their stored facepalm score "
            "(250 D-01): a ranking of how careless the blunder is at the mover's level, not a "
            "share of peers. `scored` is the share with a score; the next four columns split the "
            "unscored ones by reason (shares of all user blunders): no reply spread yet, no stored "
            f"engine line, a line shorter than {LINE_DEPTH} plies without an early mate (or one that "
            "cannot be replayed), and a missing played-move probability. The `pass` columns are "
            "shares of the scored blunders at or above each threshold; `qualifying of all` is the "
            "share of every user blunder that qualifies at the chosen threshold (an unscored "
            "blunder never qualifies).",
            "",
            md_table(headers, rows),
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
            "Pre-move ES bounds (D-15), at the chosen facepalm threshold. First table: share of qualifying "
            "(facepalm) blunders whose pre-move ES is inside the band. Second table: disjoint "
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
    weights = blunder_position_marginals()
    rows = []
    for bucket in ROW_BUCKETS:
        subset = _in_bucket(usable, bucket)
        shares = fit_shares(subset, params)
        fits = [fmt_share(shares.get(k, 0.0) * len(subset), len(subset)) for k in FIT_POSITIONS]
        weighted = weighted_fit_share(shares, weights)
        rows.append(
            [
                _label(bucket),
                str(len(subset)),
                *fits,
                fmt_share(weighted * len(subset), len(subset)),
            ]
        )
    weight_rows = [[str(k), f"{weights[k]:.4f}"] for k in FIT_POSITIONS]
    headers = [
        "Elo bucket",
        "usable blunders",
        *[f"pos {k}" for k in FIT_POSITIONS],
        "window-weighted",
    ]
    return "\n".join(
        [
            "## Window fit",
            "",
            "Share of usable blunders (facepalm and pre-move ES in band) whose k-1 preceding user "
            "moves are all Good and in band, for window positions 1 to 5 (D-16). The last column "
            "weights the positions with the blunder-window position weights below.",
            "",
            md_table(headers, rows),
            "",
            f"Blunder windows (250 D-12): length uniform over {WINDOW_LENGTHS}, then the position "
            f"drawn with weight proportional to {HAZARD} * (1 - {HAZARD})^(k - 1) within that "
            "length, so the length alone never reveals the blunder. The weights below are the "
            f"marginal over the length. Herrings are not part of this table: a herring is "
            f"{HERRING_SHARE:.1%} of all slots, an independent draw.",
            "",
            md_table(["position", "P(position | blunder window)"], weight_rows),
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
            "of qualifying moves contributes floor(run / L) windows. Herrings are "
            f"{HERRING_SHARE:.1%} of the slots (250 D-12), so a session of "
            f"{BLUNDER_CHECK_SESSION_WINDOWS} windows needs about "
            f"{BLUNDER_CHECK_SESSION_WINDOWS * HERRING_SHARE:.1f} of them.",
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


def foreign_levels() -> tuple[int, ...]:
    """Pinned-Elo levels the foreign supply is estimated at, FOREIGN_LEVEL_MIN to FOREIGN_LEVEL_MAX."""
    return tuple(range(FOREIGN_LEVEL_MIN, FOREIGN_LEVEL_MAX + 1, FOREIGN_LEVEL_STEP))


def level_note(level: int) -> str:
    """Flags the rating extremes where foreign supply is thinnest (250 D-10)."""
    if level < ELO_BUCKET_EDGES[0]:
        return f"extreme: below {ELO_BUCKET_EDGES[0]}"
    if level >= ELO_BUCKET_EDGES[-1]:
        return f"extreme: {ELO_BUCKET_EDGES[-1]} and above"
    return ""


@dataclass(frozen=True)
class ForeignSupply:
    """Sample counts of other users' blunders whose mover's pinned Elo is within the band of a level."""

    level: int
    qualifying: int
    usable: int
    games: int


def foreign_supply(collection: Collection, params: ReportParams) -> list[ForeignSupply]:
    """Per level: qualifying blunders, usable ones (in band) and distinct games, mover Elo +-band.

    Sample counts; the caller scales them to the population. A foreign window comes from the
    mover's pinned Elo, so the game's Elo (not the bucket) decides membership (250 D-13).
    """
    elo_by_game = {g.game_id: g.elo for g in analysis_games(collection) if g.elo is not None}
    qualifying = [
        (elo_by_game[b.game_id], b)
        for b in qualifying_blunders(analysis_blunders(collection), params)
        if b.game_id in elo_by_game
    ]
    result = []
    for level in foreign_levels():
        near = [b for elo, b in qualifying if abs(elo - level) <= FOREIGN_RATING_BAND]
        result.append(
            ForeignSupply(
                level=level,
                qualifying=len(near),
                usable=sum(
                    1 for b in near if in_band(b.es_before, params.band_low, params.band_high)
                ),
                games=len({b.game_id for b in near}),
            )
        )
    return result


def _own_supply_block(collection: Collection, params: ReportParams) -> list[str]:
    supply = user_supply(collection, params, None)
    blunder_windows = [b for b, _ in supply]
    herring_windows = [h for _, h in supply]
    under = sum(1 for w in blunder_windows if w < params.min_user_windows)
    rows = [
        ["usable blunder windows", *_percentile_cells(blunder_windows)],
        ["herring windows", *_percentile_cells(herring_windows)],
    ]
    return [
        "### Own supply per user",
        "",
        "**Estimate** (D-16, D-23), not an exact count: exact per-user counts of user-side "
        "blunders and fully evaluated games (non-guest users, SELECT-only aggregates) times "
        "per-bucket sample rates at the chosen threshold, after the "
        f"{MAX_MISS_SHARE:.0%} cap on pure misses. Rating groups approximate each game's "
        "exact Elo.",
        "",
        f"- Non-guest users with a fully evaluated game: {len(supply)}",
        f"- Users under {params.min_user_windows} usable blunder windows (their own slots turn "
        f"into foreign ones, 250 D-15): {f'{under} of {len(supply)}'}",
        "",
        md_table(["per user", *[f"p{q}" for q in PERCENTILES]], rows),
    ]


def _foreign_supply_block(collection: Collection, params: ReportParams) -> list[str]:
    permille = max(collection.meta.permille, 1)
    scale = PERMILLE_BASE / permille
    rows = [
        [
            str(entry.level),
            f"{entry.level - FOREIGN_RATING_BAND} to {entry.level + FOREIGN_RATING_BAND}",
            str(round(entry.qualifying * scale)),
            str(round(entry.usable * scale)),
            str(round(entry.games * scale)),
            str(entry.qualifying),
            level_note(entry.level),
        ]
        for entry in foreign_supply(collection, params)
    ]
    headers = [
        "level (pinned Elo)",
        "mover Elo",
        "qualifying blunders",
        "usable (in band)",
        "games with a qualifying blunder",
        "sample n (qualifying)",
        "note",
    ]
    return [
        "### Foreign supply per rating level",
        "",
        f"Qualifying blunders of other users whose mover's pinned Elo is within "
        f"+-{FOREIGN_RATING_BAND} of the level (250 D-13: rating only, no widening). Counts are "
        f"population estimates: the sample count times {PERMILLE_BASE} / {permille} sample "
        "permille (non-guest games, so a run capped with `--limit-games` undercounts). A session "
        "takes at most one window per game, so the games column is the pool a foreign slot "
        "draws from. The rows below 800 and at 2400 and above are the extremes, where "
        "the pool is thinnest.",
        "",
        md_table(headers, rows),
    ]


def section_supply_by_origin(collection: Collection, params: ReportParams) -> str:
    """D-10, D-13: own supply per user and foreign supply per rating level, extremes called out."""
    return "\n".join(
        [
            "## Supply by origin",
            "",
            *_own_supply_block(collection, params),
            "",
            *_foreign_supply_block(collection, params),
        ]
    )


def section_provenance(collection: Collection, params: ReportParams) -> str:
    rows = []
    for provenance in PROVENANCES:
        blunders = [b for b in analysis_blunders(collection) if b.provenance == provenance]
        games = [g for g in analysis_games(collection) if g.provenance == provenance]
        usable = usable_blunders(blunders, params)
        weighted = weighted_fit_share(fit_shares(usable, params), blunder_position_marginals())
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
        "window-weighted fit",
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


def _oddness_cells(row: OddnessRow) -> list[str]:
    return [
        str(row.n_good),
        str(row.n_blunder),
        _quartile_cell(row.good_quartiles),
        _quartile_cell(row.blunder_quartiles),
        "n/a" if row.auc is None else f"{row.auc:.3f}",
    ]


def _auc_cell(auc_value: float | None) -> str:
    return "n/a" if auc_value is None else f"{auc_value:.3f}"


def _delta_cell(drill: float | None, baseline: float | None) -> str:
    return "n/a" if drill is None or baseline is None else f"{drill - baseline:+.3f}"


def _oddness_baseline_table(collection: Collection, params: ReportParams) -> str:
    """Drill AUC against the unselected baseline (SEED-261108-dk0 "match real games").

    Unselected: every scored Good move against every rated user-side blunder, no band and no
    facepalm filter, i.e. how much odder blunders look than Good moves in real games.
    Band only: both sides inside the eval band, so the band's own effect is separated from
    the facepalm selection. Drill: the main table (band + facepalm). A drill AUC well above
    the unselected one means selection widens the real-game gap and teaches a shortcut.
    """
    good_all = list(collection.oddness)
    good_band = [g for g in good_all if in_band(g.es_before, params.band_low, params.band_high)]
    rated = [b for b in analysis_blunders(collection) if b.bucket is not None]
    band_blunders = [b for b in rated if in_band(b.es_before, params.band_low, params.band_high)]
    usable = usable_blunders(rated, params)
    unselected = summarize_oddness(good_all, rated)
    band_only = summarize_oddness(good_band, band_blunders)
    drill = summarize_oddness(good_band, usable)
    pooled = (
        summarize_group(good_all, rated),
        summarize_group(good_band, band_blunders),
        summarize_group(good_band, usable),
    )
    triples: list[tuple[str, OddnessRow, OddnessRow, OddnessRow]] = [
        (bucket, unselected[bucket], band_only[bucket], drill[bucket]) for bucket in ELO_BUCKETS
    ]
    triples.append(("all", *pooled))
    rows = [
        [
            label,
            str(u.n_good),
            str(u.n_blunder),
            _auc_cell(u.auc),
            _auc_cell(b.auc),
            _auc_cell(d.auc),
            _delta_cell(d.auc, u.auc),
        ]
        for label, u, b, d in triples
    ]
    headers = [
        "Elo bucket",
        "n Good (unselected)",
        "n blunder (unselected)",
        "AUC unselected",
        "AUC band only",
        "AUC drill",
        "drill - unselected",
    ]
    return "\n".join(
        [
            "### Drill against the unselected baseline",
            "",
            "The target is not AUC 0.5: blunders looking somewhat odd is a real signal the drill "
            "should train. The target is a drill AUC close to the unselected one, i.e. selection "
            "does not widen the real-game gap. Unselected = every scored Good move against every "
            "rated user-side blunder (no band, no facepalm threshold); band only = both sides inside the "
            "eval band; drill = the table above. A clearly positive drill - unselected means "
            "flagging odd-looking arrows pays more in the drill than in games.",
            "",
            md_table(headers, rows),
        ]
    )


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
            "chosen facepalm threshold and band, with their stored played-move probability.",
            "",
            "AUC is P(Good probability > blunder probability) + 0.5 P(tie). 0.5 means the arrow's "
            "oddness leaks nothing; near 1 means blunders look odd and flagging odd-looking arrows "
            "wins without reading the position.",
            "",
            md_table(headers, rows),
            "",
            _oddness_baseline_table(collection, params),
        ]
    )


def _median_cell(values: Sequence[float], digits: int = 3) -> str:
    median = percentile(values, 50)
    return "n/a" if median is None else f"{median:.{digits}f}"


def _loses_material(b: BlunderRecord) -> bool:
    """The punishment is clear: mate within LINE_DEPTH plies or at least FAIR_LOSS_MIN points down."""
    mated = b.line_mate_ply is not None and b.line_mate_ply <= LINE_DEPTH
    return mated or (b.line_loss_3 is not None and b.line_loss_3 >= FAIR_LOSS_MIN)


def _proxy_row(
    collection: Collection,
    blunders: Sequence[BlunderRecord],
    params: ReportParams,
    threshold: float,
) -> list[str]:
    at = replace(params, facepalm_threshold=threshold)
    scored = [b for b in blunders if is_scored(b)]
    passers = qualifying_blunders(scored, at)
    probs = [b.maia_played_prob for b in passers if b.maia_played_prob is not None]
    spreads = [b.maia_reply_spread for b in passers if b.maia_reply_spread is not None]
    supply = user_supply(collection, at, None)
    windows = percentile([blunder for blunder, _ in supply], 50)
    return [
        f"{threshold:.2f}",
        fmt_share(len(passers), len(scored)),
        fmt_share(len(passers), len(blunders)),
        _median_cell(probs),
        _median_cell(spreads, 2),
        fmt_share(sum(1 for b in passers if _loses_material(b)), len(passers)),
        "n/a" if windows is None else f"{windows:.1f}",
    ]


def section_recommended_constants(collection: Collection, params: ReportParams) -> str:
    """D-18, 250 D-03: the chosen facepalm threshold and eval band, with fair-share proxies per threshold."""
    blunders = analysis_blunders(collection)
    proxy_rows = [
        _proxy_row(collection, blunders, params, threshold) for threshold in pass_thresholds(params)
    ]
    proxy_headers = [
        "threshold",
        "pass of scored",
        "pass of all",
        "median played prob",
        "median reply spread",
        f"mate or >= {FAIR_LOSS_MIN} points down",
        "median usable windows per user",
    ]
    fit_rows = []
    for bucket in ROW_BUCKETS:
        usable = usable_blunders(_in_bucket(blunders, bucket), params)
        weighted = weighted_fit_share(fit_shares(usable, params), blunder_position_marginals())
        fit_rows.append([_label(bucket), fmt_share(weighted * len(usable), len(usable))])
    supply = user_supply(collection, params, None)
    blunder_median = percentile([b for b, _ in supply], 50)
    herring_median = percentile([h for _, h in supply], 50)
    under = sum(1 for b, _ in supply if b < params.min_user_windows)
    owner_anchor = ", ".join(
        f">= {threshold:.1f}: {PERCENT * share:.0f}%" for threshold, share in OWNER_LABEL_FAIR_SHARE
    )
    lines = [
        "## Recommended constants",
        "",
        f"- Facepalm threshold **{params.facepalm_threshold}** (a user blunder qualifies at or above it).",
        f"- Eval band **{_band_label(params.band_low, params.band_high)}** on the pre-move ES.",
        "",
        "These are a recommendation only: nothing here is wired into app code, and the owner "
        "decides the final values. Re-render with another `--facepalm-threshold` from the cache "
        "to compare.",
        "",
        "Fair-share proxies per threshold (250 D-03: a false alarm is worse than a miss). The "
        "report cannot tell a fair position from an unfair one, so it prints what drives fairness "
        "among the passers: how rarely the move is played, how few replies the opponent has, and "
        "how often the stored line wins material or mates at once. The owner's labels (2026-11-13, "
        f"decided labels with a stored line, cross-validated) measured fair among passers at {owner_anchor}. "
        "Judge precision on the spot-check, not on these columns alone.",
        "",
        md_table(proxy_headers, proxy_rows),
        "",
        "Window-weighted share of usable blunders (qualifying and in band) that fit a window, "
        "at the chosen threshold:",
        "",
        md_table(["Elo bucket", "window fit (usable blunders)"], fit_rows),
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
        section_facepalm_score(collection, params),
        section_eval_band(collection, params),
        section_window_fit(collection, params),
        section_herring_supply(collection, params),
        section_supply_by_origin(collection, params),
        section_provenance(collection, params),
        section_arrow_oddness(collection, params),
        section_recommended_constants(collection, params),
    ]
    return "\n\n".join(sections) + "\n"
