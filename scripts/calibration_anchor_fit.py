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
from pathlib import Path
from typing import TypedDict

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


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Joint Bradley-Terry/Elo rating fit over the anchor-ladder game graph (D-05)."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the raw per-game TSV emitted by calibration-anchor-ladder.mjs",
    )
    parser.add_argument(
        "--out-js", required=True, help="Output path for the Node-consumable INTERNAL_RATING module"
    )
    parser.add_argument(
        "--out-json", required=True, help="Output path for the human/Python-readable JSON sibling"
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
