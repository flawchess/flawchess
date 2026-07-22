"""calibration_anchor_fit.py — SEED-101 joint Bradley-Terry/Elo rating fit
over the anchor-ladder self-calibration game graph (Phase 173, D-05).

Reads the raw per-game TSV emitted by calibration-anchor-ladder.mjs, fits a
joint MLE rating for every anchor via Zermelo/MM iteration (RESEARCH.md
Pattern 2), fixes the scale at maia1500 := 1500 (INTERNAL SCALE — NOT human
ELO, D-13), and emits bootstrap CIs + per-pair residuals (D-06).

This is a standalone research tool (`scripts/`, not `app/`) — stdlib only
(`math`/`random`/`argparse`/`json`), no numpy/scipy (D-07), no Sentry capture
(CLAUDE.md Sentry rules apply to app/services and app/routers only).

Usage:
    uv run python scripts/calibration_anchor_fit.py \\
        --input reports/data/anchor-ladder-<ts>.tsv \\
        --out-js scripts/lib/calibration-internal-scale.mjs \\
        --out-json reports/data/anchor-ladder-internal-scale.json

    uv run python scripts/calibration_anchor_fit.py \\
        --input reports/data/anchor-ladder-<ts>.tsv \\
        --out-js scripts/lib/calibration-internal-scale.mjs \\
        --out-json reports/data/anchor-ladder-internal-scale.json \\
        --bootstrap-samples 500 --seed 7

This script does NOT run the real anchor-vs-anchor game harness — it only
fits ratings from an already-collected TSV ledger. It does NOT run against
real data as part of this phase's Wave 0 plans; that is a later plan's job.
Every output artifact carries the D-13 "internal scale, NOT human ELO" caveat.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypedDict

# --- Per-game TSV column contract (shared with the Node harness, must match exactly) ---
TSV_HEADER = (
    "pass",
    "anchor_white",
    "anchor_black",
    "result",
    "reason",
    "plies",
    "game_index",
    "opening",
    "seed",
    "git_sha",
)
RESULT_WHITE_WIN = "white_win"
RESULT_BLACK_WIN = "black_win"
RESULT_DRAW = "draw"
DRAW_SPLIT = 0.5  # D-05: draws fold to +0.5/+0.5

# --- Rating-model constants ---
RATING_SCALE = 400.0  # standard Elo/Bradley-Terry rating = 400 * log10(pi)
DEFAULT_FIT_TOL = 1e-9
DEFAULT_FIT_MAX_ITER = 10_000
DEFAULT_SCALE_PIN = "maia1500"
DEFAULT_SCALE_PIN_VALUE = 1500.0
DEFAULT_BOOTSTRAP_SAMPLES = 200
DEFAULT_BOOTSTRAP_SEED = 0
BOOTSTRAP_LOWER_PERCENTILE = 0.025
BOOTSTRAP_UPPER_PERCENTILE = 0.975

# Continuity-correction divisor (Pitfall 2), mirroring
# scripts/lib/calibration-elo.mjs's SCORE_CLAMP_EPSILON_DIVISOR pattern:
# epsilon = 1 / (SCORE_CLAMP_EPSILON_DIVISOR * games).
SCORE_CLAMP_EPSILON_DIVISOR = 2

INTERNAL_SCALE_HEADER = (
    "INTERNAL SCALE — NOT human ELO (D-13). Scale fixed arbitrarily so "
    f"{DEFAULT_SCALE_PIN} == {DEFAULT_SCALE_PIN_VALUE:.0f}; see "
    ".planning/notes/ for the compression-verdict methodology and findings."
)

# --- Bot-cell fit path (Phase 180, D-06) ---------------------------------------
# Two-sided 95% normal z used to back out a per-family standard error from a
# bootstrap CI width when inverse-CI-weighting the per-preset combined G_preset.
NORMAL_95_Z = 1.959963985
# Required columns of the harness's aggregated per-(cell, anchor) WDL TSV
# (a superset is fine — the row carries extra provenance columns). `wins`/
# `draws`/`losses` are the BOT's outcomes vs `anchor`.
BOT_TSV_REQUIRED_COLUMNS = ("bot_elo", "bot_blend", "anchor", "wins", "draws", "losses")
# Optional per-row flag (Pitfall 4): the cell landed beyond the anchor ladder.
BOT_TSV_BEYOND_LADDER_COLUMN = "beyond_ladder"
# Single source of truth for the 10 FIXED anchor ratings the bot cell is fit
# against — the JSON the anchor-ladder path writes (keeps the two in sync,
# rather than hardcoding the numbers from calibration-internal-scale.mjs).
DEFAULT_INTERNAL_SCALE_JSON = "reports/data/anchor-ladder-internal-scale.json"


def load_games(path: str) -> list[dict[str, str]]:
    """Parses the per-game TSV emitted by calibration-anchor-ladder.mjs.

    Tab-separated, one clean header row (no leading comment) matching
    TSV_HEADER exactly; `result` in {white_win, black_win, draw}.
    """
    with open(path, encoding="utf-8") as f:
        header = tuple(f.readline().rstrip("\n").split("\t"))
        if header != TSV_HEADER:
            raise RuntimeError(
                f"load_games: unexpected TSV header {header!r}, expected {TSV_HEADER!r}"
            )
        return [
            dict(zip(header, line.rstrip("\n").split("\t"), strict=False))
            for line in f
            if line.strip()
        ]


def build_win_counts(games: Iterable[dict[str, str]]) -> dict[tuple[str, str], float]:
    """Folds each game's result into win_counts[(i, j)] = i's score vs j (D-05).

    white_win -> +1 to anchor_white vs anchor_black; black_win -> +1 to
    anchor_black vs anchor_white; draw -> +DRAW_SPLIT to each side.
    """
    win_counts: dict[tuple[str, str], float] = {}
    for game in games:
        white = game["anchor_white"]
        black = game["anchor_black"]
        result = game["result"]
        if result == RESULT_WHITE_WIN:
            win_counts[(white, black)] = win_counts.get((white, black), 0.0) + 1.0
        elif result == RESULT_BLACK_WIN:
            win_counts[(black, white)] = win_counts.get((black, white), 0.0) + 1.0
        elif result == RESULT_DRAW:
            win_counts[(white, black)] = win_counts.get((white, black), 0.0) + DRAW_SPLIT
            win_counts[(black, white)] = win_counts.get((black, white), 0.0) + DRAW_SPLIT
        else:
            raise RuntimeError(f"build_win_counts: unknown result {result!r} for game {game!r}")
    return win_counts


def _clamp_win_counts(
    win_counts: dict[tuple[str, str], float], anchors: Sequence[str]
) -> dict[tuple[str, str], float]:
    """Continuity-corrects lopsided pair scores before Zermelo/MM (Pitfall 2).

    Any unordered pair whose observed score sits within epsilon of 0 or 1
    (epsilon = 1 / (SCORE_CLAMP_EPSILON_DIVISOR * games), same pattern as
    calibration-elo.mjs's SCORE_CLAMP_EPSILON_DIVISOR clamp) is clamped into
    [epsilon, 1 - epsilon] so a perfect/near-perfect sweep never drives a
    strength toward +/-infinity in the fixed-point iteration.
    """
    clamped: dict[tuple[str, str], float] = dict(win_counts)
    seen: set[frozenset[str]] = set()
    for i in anchors:
        for j in anchors:
            if i == j:
                continue
            key = frozenset((i, j))
            if key in seen:
                continue
            seen.add(key)
            games = win_counts.get((i, j), 0.0) + win_counts.get((j, i), 0.0)
            if games <= 0:
                continue
            epsilon = 1.0 / (SCORE_CLAMP_EPSILON_DIVISOR * games)
            score_i = win_counts.get((i, j), 0.0) / games
            clamped_score_i = min(1.0 - epsilon, max(epsilon, score_i))
            clamped[(i, j)] = clamped_score_i * games
            clamped[(j, i)] = (1.0 - clamped_score_i) * games
    return clamped


def fit_bradley_terry(
    win_counts: dict[tuple[str, str], float],
    anchors: Sequence[str],
    tol: float = DEFAULT_FIT_TOL,
    max_iter: int = DEFAULT_FIT_MAX_ITER,
) -> dict[str, float]:
    """Zermelo/MM joint MLE fit (RESEARCH.md Pattern 2, Hunter 2004).

    win_counts[(i, j)] is i's score vs j (wins + 0.5*draws — draws must
    already be folded via build_win_counts before calling this). Neutral
    symmetric initialization strength[a] = 1.0 for every anchor (Pitfall 3 —
    never seed from folklore SF_SKILL_ELO).

    Returns per-anchor ratings (400 * log10(pi)) on an ARBITRARY scale: the
    Bradley-Terry log-likelihood is constant along uniform rating shifts, so
    only pairwise DIFFERENCES are guaranteed to match the true model —
    apply_scale_fix pins the absolute scale afterward (D-05).
    """
    anchors = list(anchors)
    win_counts = _clamp_win_counts(win_counts, anchors)
    strength = {a: 1.0 for a in anchors}
    total_wins = {a: sum(win_counts.get((a, b), 0.0) for b in anchors if b != a) for a in anchors}

    for _ in range(max_iter):
        new_strength: dict[str, float] = {}
        for i in anchors:
            denom = sum(
                (win_counts.get((i, j), 0.0) + win_counts.get((j, i), 0.0))
                / (strength[i] + strength[j])
                for j in anchors
                if j != i and (win_counts.get((i, j), 0.0) + win_counts.get((j, i), 0.0)) > 0
            )
            new_strength[i] = total_wins[i] / denom if denom > 0 else strength[i]
        max_rel_change = max(abs(new_strength[a] - strength[a]) / strength[a] for a in anchors)
        strength = new_strength
        if max_rel_change < tol:
            break

    return {a: RATING_SCALE * math.log10(strength[a]) for a in anchors}


def apply_scale_fix(
    ratings: dict[str, float],
    pin: str = DEFAULT_SCALE_PIN,
    value: float = DEFAULT_SCALE_PIN_VALUE,
) -> dict[str, float]:
    """Shifts every rating by a constant so ratings[pin] == value EXACTLY (D-05).

    The pin anchor is assigned `value` directly (not via addition) so the
    scale-fix is exact regardless of floating-point rounding in the shift.
    """
    if pin not in ratings:
        raise RuntimeError(
            f"apply_scale_fix: pin anchor {pin!r} not present in ratings {sorted(ratings)!r}"
        )
    shift = value - ratings[pin]
    return {a: (value if a == pin else r + shift) for a, r in ratings.items()}


def check_connectivity(
    pairs: set[tuple[str, str]] | Iterable[tuple[str, str]], anchors: Sequence[str]
) -> None:
    """Fail-loud D-04 guard: every anchor reachable AND >= 2 cross-family edges.

    Runs BEFORE any fit call (both in the Node scheduler and, defensively,
    here again in main() — belt-and-suspenders per Pitfall 1: a disconnected
    or under-cross-linked graph makes the fit numerically "converge" to a
    combined table whose maia/SF offset is arbitrary, not measured).
    """
    anchors = list(anchors)
    pairs = list(pairs)
    if not anchors:
        raise RuntimeError("check_connectivity: no anchors to check")

    adjacency: dict[str, set[str]] = {a: set() for a in anchors}
    for a, b in pairs:
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)

    visited = {anchors[0]}
    frontier = [anchors[0]]
    while frontier:
        node = frontier.pop()
        for neighbor in adjacency[node] - visited:
            visited.add(neighbor)
            frontier.append(neighbor)
    if visited != set(anchors):
        unreached = set(anchors) - visited
        raise RuntimeError(f"Anchor graph is disconnected — unreached: {sorted(unreached)}")

    cross_family_edges = [(a, b) for a, b in pairs if _is_maia(a) != _is_maia(b)]
    if len(cross_family_edges) < 2:
        raise RuntimeError(
            f"D-04 violated: only {len(cross_family_edges)} cross-family link(s) "
            f"({sorted(cross_family_edges)}), need >= 2"
        )


def bootstrap_ci(
    games: Sequence[dict[str, str]],
    anchors: Sequence[str],
    n_samples: int = DEFAULT_BOOTSTRAP_SAMPLES,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
    pin: str = DEFAULT_SCALE_PIN,
    pin_value: float = DEFAULT_SCALE_PIN_VALUE,
) -> dict[str, tuple[float, float]]:
    """Nonparametric bootstrap CI per anchor (D-06; Pitfall 5 — bootstrap, not Wilson).

    Resamples `games` with replacement (same size as the input), refits via
    fit_bradley_terry + apply_scale_fix each time, and returns the empirical
    [BOOTSTRAP_LOWER_PERCENTILE, BOOTSTRAP_UPPER_PERCENTILE] interval per
    anchor across n_samples resamples.
    """
    anchors = list(anchors)
    games = list(games)
    n = len(games)
    if n == 0:
        raise RuntimeError("bootstrap_ci: no games to resample")

    rng = random.Random(seed)
    samples: dict[str, list[float]] = {a: [] for a in anchors}
    for _ in range(n_samples):
        resampled = [games[rng.randrange(n)] for _ in range(n)]
        ratings = apply_scale_fix(
            fit_bradley_terry(build_win_counts(resampled), anchors), pin=pin, value=pin_value
        )
        for a in anchors:
            samples[a].append(ratings[a])

    result: dict[str, tuple[float, float]] = {}
    for a in anchors:
        values = sorted(samples[a])
        last_index = len(values) - 1
        lo_idx = max(0, round(BOOTSTRAP_LOWER_PERCENTILE * last_index))
        hi_idx = min(last_index, round(BOOTSTRAP_UPPER_PERCENTILE * last_index))
        result[a] = (values[lo_idx], values[hi_idx])
    return result


def _expected_score(rating_i: float, rating_j: float) -> float:
    """Bradley-Terry expected score for i vs j from ratings on the 400*log10(pi) scale."""
    return 1.0 / (1.0 + 10.0 ** ((rating_j - rating_i) / RATING_SCALE))


def _is_maia(anchor: str) -> bool:
    return anchor.startswith("maia")


class ResidualRow(TypedDict):
    """One per-pair residual entry (D-06) — see compute_residuals."""

    pair: tuple[str, str]
    games: float
    observed: float
    predicted: float
    residual: float
    cross_family: bool


def compute_residuals(
    win_counts: dict[tuple[str, str], float], ratings: dict[str, float]
) -> list[ResidualRow]:
    """Observed-minus-predicted per pair, cross-family pairs flagged distinctly (D-06).

    One entry per unordered pair (i, j) with i < j (lexicographic) that has
    played games, oriented as win_counts[(i, j)] (i's observed score vs j).
    """
    anchors = sorted(ratings)
    residuals: list[ResidualRow] = []
    for idx, i in enumerate(anchors):
        for j in anchors[idx + 1 :]:
            games = win_counts.get((i, j), 0.0) + win_counts.get((j, i), 0.0)
            if games <= 0:
                continue
            observed = win_counts.get((i, j), 0.0) / games
            predicted = _expected_score(ratings[i], ratings[j])
            residuals.append(
                ResidualRow(
                    pair=(i, j),
                    games=games,
                    observed=observed,
                    predicted=predicted,
                    residual=observed - predicted,
                    cross_family=_is_maia(i) != _is_maia(j),
                )
            )
    return residuals


def _write_outputs(
    out_js: str,
    out_json: str,
    ratings: dict[str, float],
    cis: dict[str, tuple[float, float]],
    residuals: list[ResidualRow],
) -> None:
    js_lines = [
        "/**",
        f" * {INTERNAL_SCALE_HEADER}",
        " * GENERATED by scripts/calibration_anchor_fit.py — do not hand-edit.",
        " */",
        "export const INTERNAL_RATING = {",
    ]
    for anchor in sorted(ratings):
        js_lines.append(f"  {anchor}: {ratings[anchor]:.2f},")
    js_lines.append("};")
    Path(out_js).parent.mkdir(parents=True, exist_ok=True)
    Path(out_js).write_text("\n".join(js_lines) + "\n", encoding="utf-8")

    payload = {
        "_caveat": INTERNAL_SCALE_HEADER,
        "internal_rating": ratings,
        "confidence_intervals": {a: list(ci) for a, ci in cis.items()},
        "residuals": [
            {**row, "pair": list(row["pair"])} for row in residuals
        ],  # tuple -> list for JSON
    }
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _print_report(
    ratings: dict[str, float],
    cis: dict[str, tuple[float, float]],
    residuals: list[ResidualRow],
) -> None:
    print(f"# {INTERNAL_SCALE_HEADER}")
    print("\nanchor\trating\tci_low\tci_high")
    for anchor in sorted(ratings):
        lo, hi = cis.get(anchor, (float("nan"), float("nan")))
        print(f"{anchor}\t{ratings[anchor]:.2f}\t{lo:.2f}\t{hi:.2f}")
    print("\npair_a\tpair_b\tgames\tobserved\tpredicted\tresidual\tcross_family")
    for row in residuals:
        a, b = row["pair"]
        print(
            f"{a}\t{b}\t{row['games']:.1f}\t{row['observed']:.4f}\t"
            f"{row['predicted']:.4f}\t{row['residual']:+.4f}\t{row['cross_family']}"
        )


# ==============================================================================
# Bot-cell strength curves (Phase 180, D-06)
# ==============================================================================
# The anchor-ladder path above jointly fits N free anchors. This path instead
# holds those 10 anchors FIXED at their measured INTERNAL_RATING and fits ONE
# free parameter — a bot cell's own strength — TWICE per cell (once on its
# vs-Maia rows, once on its vs-SF rows). The two ratings' difference IS the
# cross-family style-inflation gap G_preset (Pitfall 3 — never average it away).


def _anchor_family(anchor: str) -> Literal["maia", "sf"]:
    """Classifies an anchor label into its engine family, fail-loud on unknown."""
    if anchor.startswith("maia"):
        return "maia"
    if anchor.startswith("sf"):
        return "sf"
    raise ValueError(f"_anchor_family: unknown anchor family for {anchor!r} (expected maia*/sf*)")


def _clamp_bot_win_counts(
    win_counts_vs_fixed: dict[str, float], games_vs_fixed: dict[str, float]
) -> dict[str, float]:
    """Continuity-corrects each bot-vs-anchor score before the single-parameter fit.

    Mirrors `_clamp_win_counts`'s epsilon formula (epsilon = 1 /
    (SCORE_CLAMP_EPSILON_DIVISOR * games)) applied per anchor: a swept bracket
    (bot wins/loses ALL games vs an anchor) would otherwise drive its strength
    to +infinity / 0 and the log10 to +/-infinity (Pitfall 4). Only anchors with
    games > 0 are returned.
    """
    clamped: dict[str, float] = {}
    for anchor, games in games_vs_fixed.items():
        if games <= 0:
            continue
        epsilon = 1.0 / (SCORE_CLAMP_EPSILON_DIVISOR * games)
        score = win_counts_vs_fixed.get(anchor, 0.0) / games
        clamped_score = min(1.0 - epsilon, max(epsilon, score))
        clamped[anchor] = clamped_score * games
    return clamped


def fit_bot_cell_rating(
    win_counts_vs_fixed: dict[str, float],
    games_vs_fixed: dict[str, float],
    fixed_ratings: dict[str, float],
    tol: float = DEFAULT_FIT_TOL,
    max_iter: int = DEFAULT_FIT_MAX_ITER,
) -> float:
    """Single-parameter pinned-anchor MLE (D-06): fit ONE bot strength, anchors fixed.

    Specializes `fit_bradley_terry` from N free anchors to a single free bot
    strength played against N FIXED opponents held at `fixed_ratings` (their
    Phase-173 measured INTERNAL_RATING). `win_counts_vs_fixed[a]` is the bot's
    folded score vs anchor `a` (wins + 0.5*draws); `games_vs_fixed[a]` its games
    vs `a`. Returns the bot's rating on the same 400*log10(pi) internal scale.

    Applies the same continuity-correction discipline as `_clamp_win_counts`
    before iterating. Seed `strength = 1.0` neutral (Pitfall 3 — NEVER seed from
    a folklore/nominal bot_elo).

    Fail-loud (STRIDE Tampering, T-180-02): raises ValueError on empty games or
    on any counted anchor label missing from `fixed_ratings` — never returns NaN
    for a corrupted/mis-keyed input consumed downstream by SEED-104.
    """
    if sum(games_vs_fixed.values()) <= 0:
        raise ValueError("fit_bot_cell_rating: no games played vs any fixed anchor")
    for anchor in set(win_counts_vs_fixed) | set(games_vs_fixed):
        if anchor not in fixed_ratings:
            raise ValueError(
                f"fit_bot_cell_rating: anchor {anchor!r} absent from fixed_ratings "
                f"{sorted(fixed_ratings)!r}"
            )

    clamped = _clamp_bot_win_counts(win_counts_vs_fixed, games_vs_fixed)
    total_wins = sum(clamped.values())
    anchor_strengths = {a: 10.0 ** (fixed_ratings[a] / RATING_SCALE) for a in clamped}
    strength = 1.0  # neutral init, same convention as fit_bradley_terry
    for _ in range(max_iter):
        denom = sum(games_vs_fixed[a] / (strength + anchor_strengths[a]) for a in clamped)
        new_strength = total_wins / denom if denom > 0 else strength
        if abs(new_strength - strength) / strength < tol:
            strength = new_strength
            break
        strength = new_strength
    return RATING_SCALE * math.log10(strength)


class BotCell(TypedDict):
    """One (bot_elo, bot_blend) cell's raw W/D/L split by anchor family."""

    bot_elo: int
    bot_blend: float
    beyond_ladder: bool
    wdl_vs_maia: dict[str, tuple[float, float, float]]  # anchor -> (wins, draws, losses)
    wdl_vs_sf: dict[str, tuple[float, float, float]]


class BotCellFit(TypedDict):
    """One fitted cell: two per-family ratings, the direct G_preset, and CIs."""

    bot_elo: int
    bot_blend: float
    rating_vs_maia: float
    rating_vs_sf: float
    g_preset: float
    ci_vs_maia: tuple[float, float]
    ci_vs_sf: tuple[float, float]
    beyond_ladder: bool


@dataclass
class _BotCellAccum:
    beyond_ladder: bool = False
    wdl_vs_maia: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    wdl_vs_sf: dict[str, tuple[float, float, float]] = field(default_factory=dict)


def load_bot_cells(path: str) -> list[BotCell]:
    """Reads the harness's aggregated per-(cell, anchor) WDL TSV into BotCells.

    Aggregates rows by (bot_elo, bot_blend), splitting each row's W/D/L into the
    Maia and SF family dicts. Fail-loud (T-180-02) on a missing required column.
    Carries the optional `beyond_ladder` per-row flag through if present.
    """
    with open(path, encoding="utf-8") as f:
        rows = [line.rstrip("\n") for line in f if line.strip()]
    if not rows:
        raise ValueError(f"load_bot_cells: {path!r} is empty")

    header = rows[0].split("\t")
    missing = [c for c in BOT_TSV_REQUIRED_COLUMNS if c not in header]
    if missing:
        raise ValueError(
            f"load_bot_cells: TSV missing required column(s) {missing!r}; header={header!r}"
        )
    idx = {c: header.index(c) for c in header}
    has_beyond = BOT_TSV_BEYOND_LADDER_COLUMN in header

    cells: dict[tuple[int, float], _BotCellAccum] = {}
    for line in rows[1:]:
        fields = line.split("\t")
        bot_elo = int(fields[idx["bot_elo"]])
        bot_blend = float(fields[idx["bot_blend"]])
        anchor = fields[idx["anchor"]]
        wdl = (
            float(fields[idx["wins"]]),
            float(fields[idx["draws"]]),
            float(fields[idx["losses"]]),
        )
        accum = cells.setdefault((bot_elo, bot_blend), _BotCellAccum())
        if _anchor_family(anchor) == "maia":
            accum.wdl_vs_maia[anchor] = wdl
        else:
            accum.wdl_vs_sf[anchor] = wdl
        if has_beyond and fields[idx[BOT_TSV_BEYOND_LADDER_COLUMN]].strip().lower() == "true":
            accum.beyond_ladder = True

    return [
        BotCell(
            bot_elo=elo,
            bot_blend=blend,
            beyond_ladder=accum.beyond_ladder,
            wdl_vs_maia=accum.wdl_vs_maia,
            wdl_vs_sf=accum.wdl_vs_sf,
        )
        for (elo, blend), accum in sorted(cells.items())
    ]


def _fold_wdl(
    wdl: dict[str, tuple[float, float, float]],
) -> tuple[dict[str, float], dict[str, float]]:
    """Folds per-anchor (wins, draws, losses) to (folded_score, games) dicts (D-05)."""
    wins = {a: w + DRAW_SPLIT * d for a, (w, d, _loss) in wdl.items()}
    games = {a: w + d + loss for a, (w, d, loss) in wdl.items()}
    return wins, games


def bootstrap_bot_cell_ci(
    wdl_vs_fixed: dict[str, tuple[float, float, float]],
    fixed_ratings: dict[str, float],
    n_samples: int = DEFAULT_BOOTSTRAP_SAMPLES,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> tuple[float, float]:
    """Parametric bootstrap CI for one bot cell's rating vs one anchor family (D-06).

    Resamples each anchor's W/D/L from a multinomial at the observed rates (A3:
    the aggregate counts are sufficient since the anchors are held FIXED, not
    jointly refit — anchor uncertainty is deliberately NOT propagated, A4),
    refits `fit_bot_cell_rating` each resample, and returns the empirical
    [BOOTSTRAP_LOWER_PERCENTILE, BOOTSTRAP_UPPER_PERCENTILE] interval.
    """
    rng = random.Random(seed)
    ratings: list[float] = []
    for _ in range(n_samples):
        wins: dict[str, float] = {}
        games: dict[str, float] = {}
        for anchor, (w, d, ell) in wdl_vs_fixed.items():
            n = int(round(w + d + ell))
            if n <= 0:
                continue
            p_win = w / n
            p_draw = d / n
            r_win = r_draw = 0
            for _game in range(n):
                r = rng.random()
                if r < p_win:
                    r_win += 1
                elif r < p_win + p_draw:
                    r_draw += 1
            wins[anchor] = r_win + DRAW_SPLIT * r_draw
            games[anchor] = float(n)
        ratings.append(fit_bot_cell_rating(wins, games, fixed_ratings))

    ratings.sort()
    last_index = len(ratings) - 1
    lo_idx = max(0, round(BOOTSTRAP_LOWER_PERCENTILE * last_index))
    hi_idx = min(last_index, round(BOOTSTRAP_UPPER_PERCENTILE * last_index))
    return (ratings[lo_idx], ratings[hi_idx])


def fit_all_bot_cells(
    cells: Sequence[BotCell],
    fixed_ratings: dict[str, float],
    n_bootstrap: int = DEFAULT_BOOTSTRAP_SAMPLES,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> list[BotCellFit]:
    """Fits every cell TWICE (vs-Maia, vs-SF) against the SAME fixed anchors.

    `g_preset = rating_vs_maia - rating_vs_sf` is computed directly from the two
    separate fits — the two families are NEVER merged before fitting (Pitfall 3).
    """
    fits: list[BotCellFit] = []
    for cell in cells:
        wins_maia, games_maia = _fold_wdl(cell["wdl_vs_maia"])
        wins_sf, games_sf = _fold_wdl(cell["wdl_vs_sf"])
        rating_vs_maia = fit_bot_cell_rating(wins_maia, games_maia, fixed_ratings)
        rating_vs_sf = fit_bot_cell_rating(wins_sf, games_sf, fixed_ratings)
        ci_vs_maia = bootstrap_bot_cell_ci(cell["wdl_vs_maia"], fixed_ratings, n_bootstrap, seed)
        ci_vs_sf = bootstrap_bot_cell_ci(cell["wdl_vs_sf"], fixed_ratings, n_bootstrap, seed + 1)
        fits.append(
            BotCellFit(
                bot_elo=cell["bot_elo"],
                bot_blend=cell["bot_blend"],
                rating_vs_maia=rating_vs_maia,
                rating_vs_sf=rating_vs_sf,
                g_preset=rating_vs_maia - rating_vs_sf,
                ci_vs_maia=ci_vs_maia,
                ci_vs_sf=ci_vs_sf,
                beyond_ladder=cell["beyond_ladder"],
            )
        )
    return fits


def combine_preset_g_preset(cells_fit: Sequence[BotCellFit]) -> dict[str, dict[str, float]]:
    """Per-preset combined G_preset scalar (open-Q3): inverse-CI-weighted mean.

    Groups fitted cells by `bot_blend` (the preset key) and combines their
    per-cell `g_preset` values with the same inverse-variance weighting
    convention as combineAnchorEstimates — each cell's standard error is backed
    out of its two per-family bootstrap CI widths (se_g = sqrt(se_maia^2 +
    se_sf^2)). Falls back to an unweighted mean if every CI collapsed.
    """
    by_blend: dict[float, list[BotCellFit]] = {}
    for cell in cells_fit:
        by_blend.setdefault(cell["bot_blend"], []).append(cell)

    combined: dict[str, dict[str, float]] = {}
    for blend, group in sorted(by_blend.items()):
        weighted_sum = 0.0
        weight_total = 0.0
        for cell in group:
            se_maia = (cell["ci_vs_maia"][1] - cell["ci_vs_maia"][0]) / (2.0 * NORMAL_95_Z)
            se_sf = (cell["ci_vs_sf"][1] - cell["ci_vs_sf"][0]) / (2.0 * NORMAL_95_Z)
            se_g = math.hypot(se_maia, se_sf)
            if se_g <= 0:
                continue
            weight = 1.0 / (se_g * se_g)
            weighted_sum += weight * cell["g_preset"]
            weight_total += weight
        if weight_total > 0:
            g_combined = weighted_sum / weight_total
        else:  # every CI collapsed to a point — fall back to a plain mean
            g_combined = sum(c["g_preset"] for c in group) / len(group)
        combined[f"{blend:g}"] = {"g_preset_combined": g_combined, "n_cells": float(len(group))}
    return combined


def load_fixed_ratings(path: str) -> dict[str, float]:
    """Reads the 10 fixed anchor INTERNAL_RATING values from the anchor-ladder JSON."""
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    ratings = payload.get("internal_rating")
    if not isinstance(ratings, dict) or not ratings:
        raise ValueError(f"load_fixed_ratings: {path!r} has no non-empty 'internal_rating' object")
    return {str(a): float(r) for a, r in ratings.items()}


def _write_bot_curves(out_json: str, cells_fit: Sequence[BotCellFit]) -> None:
    """Writes the bot-curves JSON, mirroring `_write_outputs`'s caveated envelope.

    Per-cell entries carry the two per-family ratings, the direct `g_preset`,
    both CIs, and `beyond_ladder`; a `per_preset` block carries the combined
    per-blend `G_preset` scalar (open-Q3: report both). The `_caveat` is the
    INTERNAL-SCALE-NOT-human-ELO header verbatim (T-180-03).
    """
    payload = {
        "_caveat": INTERNAL_SCALE_HEADER,
        "cells": [
            {
                "bot_elo": cell["bot_elo"],
                "bot_blend": cell["bot_blend"],
                "rating_vs_maia": cell["rating_vs_maia"],
                "rating_vs_sf": cell["rating_vs_sf"],
                "g_preset": cell["g_preset"],
                "ci_vs_maia": list(cell["ci_vs_maia"]),
                "ci_vs_sf": list(cell["ci_vs_sf"]),
                "beyond_ladder": cell["beyond_ladder"],
            }
            for cell in cells_fit
        ],
        "per_preset": combine_preset_g_preset(cells_fit),
    }
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _run_bot_curves_path(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Bot-cell fit path: load_bot_cells -> fit_all_bot_cells -> _write_bot_curves."""
    try:
        fixed_ratings = load_fixed_ratings(args.internal_scale_json)
    except OSError as exc:
        parser.error(f"--internal-scale-json: cannot read {args.internal_scale_json!r}: {exc}")
    try:
        cells = load_bot_cells(args.bot_input)
    except OSError as exc:
        parser.error(f"--bot-input: cannot read {args.bot_input!r}: {exc}")
    if not cells:
        parser.error(f"--bot-input: {args.bot_input!r} contains no bot cells")

    cells_fit = fit_all_bot_cells(
        cells, fixed_ratings, n_bootstrap=args.bootstrap_samples, seed=args.seed
    )
    _write_bot_curves(args.out_bot_curves, cells_fit)
    print(f"# {INTERNAL_SCALE_HEADER}")
    print("\nbot_elo\tbot_blend\trating_vs_maia\trating_vs_sf\tg_preset\tbeyond_ladder")
    for cell in cells_fit:
        print(
            f"{cell['bot_elo']}\t{cell['bot_blend']:g}\t{cell['rating_vs_maia']:.2f}\t"
            f"{cell['rating_vs_sf']:.2f}\t{cell['g_preset']:+.2f}\t{cell['beyond_ladder']}"
        )


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Joint Bradley-Terry/Elo rating fit over the anchor-ladder game graph (D-05)."
    )
    # --- anchor-ladder mode (existing, D-05) ---
    parser.add_argument(
        "--input",
        help="Path to the raw per-game TSV emitted by calibration-anchor-ladder.mjs "
        "(anchor-ladder mode)",
    )
    parser.add_argument(
        "--out-js", help="Output path for the Node-consumable INTERNAL_RATING module"
    )
    parser.add_argument("--out-json", help="Output path for the human/Python-readable JSON sibling")
    # --- bot-curves mode (Phase 180, D-06) ---
    parser.add_argument(
        "--bot-input",
        help="Path to the harness's aggregated per-(cell, anchor) WDL TSV (bot-curves mode)",
    )
    parser.add_argument(
        "--out-bot-curves", help="Output path for the bot-curves JSON (bot-curves mode)"
    )
    parser.add_argument(
        "--internal-scale-json",
        default=DEFAULT_INTERNAL_SCALE_JSON,
        help="Path to the anchor-ladder JSON providing the 10 FIXED anchor INTERNAL_RATING "
        f"values (bot-curves mode; default {DEFAULT_INTERNAL_SCALE_JSON})",
    )
    parser.add_argument(
        "--bootstrap-samples",
        type=int,
        default=DEFAULT_BOOTSTRAP_SAMPLES,
        help="Number of bootstrap resamples",
    )
    parser.add_argument(
        "--seed", type=int, default=DEFAULT_BOOTSTRAP_SEED, help="Bootstrap RNG seed"
    )
    args = parser.parse_args(argv)

    if args.bootstrap_samples <= 0:
        parser.error(f"--bootstrap-samples must be positive, got {args.bootstrap_samples}")

    # Bot-curves mode: fit per-preset strength curves + G_preset, leave the
    # anchor-ladder path below entirely untouched.
    if args.bot_input:
        if not args.out_bot_curves:
            parser.error("--out-bot-curves is required in bot-curves mode (--bot-input)")
        _run_bot_curves_path(args, parser)
        return

    missing_flags = [
        flag
        for flag, value in (
            ("--input", args.input),
            ("--out-js", args.out_js),
            ("--out-json", args.out_json),
        )
        if not value
    ]
    if missing_flags:
        parser.error(
            f"anchor-ladder mode requires {', '.join(missing_flags)} "
            "(or use --bot-input for bot-curves mode)"
        )

    try:
        games = load_games(args.input)
    except OSError as exc:
        parser.error(f"--input: cannot read {args.input!r}: {exc}")
        return  # unreachable — parser.error exits the process
    if not games:
        parser.error(f"--input: {args.input!r} contains no games")

    anchors = sorted({g["anchor_white"] for g in games} | {g["anchor_black"] for g in games})
    # Canonicalize (sort) each pair: colors alternate per game, so raw
    # (anchor_white, anchor_black) tuples yield BOTH orientations of one real
    # pairing — check_connectivity would count a single cross-family bridge as
    # 2 links and pass a non-identifiable graph (CR-01, 173-REVIEW.md).
    pairs = {
        (g["anchor_white"], g["anchor_black"])
        if g["anchor_white"] <= g["anchor_black"]
        else (g["anchor_black"], g["anchor_white"])
        for g in games
    }

    # D-04 defensive re-check: MUST run before any fit call (belt-and-suspenders
    # against the Node scheduler — Pitfall 1).
    check_connectivity(pairs, anchors)

    win_counts = build_win_counts(games)
    ratings = apply_scale_fix(fit_bradley_terry(win_counts, anchors))
    cis = bootstrap_ci(games, anchors, n_samples=args.bootstrap_samples, seed=args.seed)
    residuals = compute_residuals(win_counts, ratings)

    _write_outputs(args.out_js, args.out_json, ratings, cis, residuals)
    _print_report(ratings, cis, residuals)


if __name__ == "__main__":
    main()
