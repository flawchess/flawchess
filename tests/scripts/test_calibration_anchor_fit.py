"""Anchor-ladder rating-fit tests (D-04, D-05, D-06). Phase 173 Plan 03.

Pure-function unit tests over `scripts.calibration_anchor_fit` — no DB, no
engines, no TSV files on disk (small in-memory synthetic dicts only). Mirrors
`tests/scripts/test_backfill_eval.py`'s "public API import, not CLI-only"
convention, but this module is purely synchronous (no `pytestmark =
pytest.mark.asyncio`) since the fit is pure stdlib math over static data.

Tests cover (one function per behavior):
- test_fit_converges: Zermelo/MM fit recovers known ground-truth pairwise
  rating differences from a hand-built win_counts graph (D-05).
- test_scale_fix: apply_scale_fix pins maia1500 to exactly 1500.0 and shifts
  every other anchor by the same constant (D-05).
- test_draws: build_win_counts folds a drawn game to +0.5/+0.5 — a
  one-win-each pair and a two-draws pair yield identical win_counts (D-05).
- test_connectivity: check_connectivity raises RuntimeError on a disconnected
  graph AND on a connected graph with only 1 cross-family edge, and does NOT
  raise on a connected graph with 2 cross-family edges (D-04).
- test_bootstrap: bootstrap_ci over a well-conditioned synthetic graph returns
  a finite (lo, hi) per anchor with lo <= point <= hi and a sane width (D-06).
- test_residuals: compute_residuals returns observed-minus-predicted per pair
  and flags cross-family pairs (one maia + one sf) distinctly (D-06).

This import fails until Task 2 creates scripts/calibration_anchor_fit.py —
that ModuleNotFoundError IS the intended RED state for this task.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from scripts.calibration_anchor_fit import (
    TSV_HEADER,
    apply_scale_fix,
    bootstrap_ci,
    build_win_counts,
    check_connectivity,
    compute_residuals,
    fit_bot_cell_rating,
    fit_bradley_terry,
    main,
)

# Named tolerances (no magic numbers in assertions below).
FIT_CONVERGES_TOLERANCE_RATING = 1.0  # rating points; oracle is an exact BT fixed point
SCALE_FIX_TOLERANCE = 1e-6
DRAW_TOLERANCE = 1e-9
RESIDUAL_TOLERANCE = 1e-6
BOOTSTRAP_MIN_WIDTH = 1.0  # a well-conditioned CI must not collapse to a point
BOOTSTRAP_MAX_WIDTH = 1500.0  # generous upper bound — not a runaway/degenerate CI

RATING_SCALE = 400.0  # matches the Elo/Bradley-Terry 400*log10(pi) convention

# Phase 180 (D-06) bot-cell fit tolerances.
BOT_CELL_RECOVERY_TOLERANCE = 1.0  # rating points; oracle is an exact single-param BT fixed point
G_PRESET_MIN_MAGNITUDE = 50.0  # a deliberately asymmetric fixture must yield a clearly-signed gap

# 10 FIXED anchors (mirrors the shape of reports/data/anchor-ladder-internal-scale.json's
# internal_rating block) — 5 Maia rungs + 5 Stockfish skills, held constant by the fit.
FIXED_RATINGS = {
    "maia700": 1129.29,
    "maia1100": 1373.87,
    "maia1500": 1500.0,
    "maia1900": 1626.39,
    "maia2300": 1706.49,
    "sf0": 1069.33,
    "sf3": 1363.88,
    "sf5": 1525.09,
    "sf8": 1801.10,
    "sf10": 1907.93,
}


def _expected_score(rating_i: float, rating_j: float) -> float:
    """Independent oracle for the Bradley-Terry expected score (RESEARCH.md Pattern 2)."""
    return 1.0 / (1.0 + 10.0 ** ((rating_j - rating_i) / RATING_SCALE))


def test_fit_converges() -> None:
    """Zermelo/MM fit recovers known ground-truth pairwise rating differences.

    win_counts is built from the EXACT Bradley-Terry expected scores implied
    by a known 400-point ladder (A=1000, B=1400, C=1800), so the true ratings
    are an exact fixed point of the MM iteration up to the model's inherent
    scale indeterminacy (log-likelihood is constant along uniform rating
    shifts — see 173-RESEARCH.md Pattern 2). Only pairwise DIFFERENCES are
    guaranteed invariant to that indeterminacy, so we assert differences, not
    absolute values (the absolute scale is pinned later by apply_scale_fix).
    """
    games_per_pair = 100.0
    ratings_truth = {"A": 1000.0, "B": 1400.0, "C": 1800.0}
    anchors = list(ratings_truth)

    win_counts: dict[tuple[str, str], float] = {}
    for i in anchors:
        for j in anchors:
            if i == j:
                continue
            win_counts[(i, j)] = games_per_pair * _expected_score(
                ratings_truth[i], ratings_truth[j]
            )

    fitted = fit_bradley_terry(win_counts, anchors)

    assert fitted["B"] - fitted["A"] == pytest.approx(400.0, abs=FIT_CONVERGES_TOLERANCE_RATING)
    assert fitted["C"] - fitted["B"] == pytest.approx(400.0, abs=FIT_CONVERGES_TOLERANCE_RATING)
    assert fitted["C"] - fitted["A"] == pytest.approx(800.0, abs=FIT_CONVERGES_TOLERANCE_RATING)


def test_scale_fix() -> None:
    """apply_scale_fix pins maia1500 to exactly 1500.0, preserving relative spacing."""
    ratings = {"maia1500": 1489.3, "maia1100": 1090.1, "sf5": 2200.7}
    original_gaps = {
        "maia1100": ratings["maia1100"] - ratings["maia1500"],
        "sf5": ratings["sf5"] - ratings["maia1500"],
    }

    fixed = apply_scale_fix(ratings, pin="maia1500", value=1500.0)

    assert fixed["maia1500"] == 1500.0  # exact, not approx — the whole point of the pin
    assert fixed["maia1100"] - fixed["maia1500"] == pytest.approx(
        original_gaps["maia1100"], abs=SCALE_FIX_TOLERANCE
    )
    assert fixed["sf5"] - fixed["maia1500"] == pytest.approx(
        original_gaps["sf5"], abs=SCALE_FIX_TOLERANCE
    )


def test_draws() -> None:
    """build_win_counts folds a drawn game to +0.5/+0.5 (D-05).

    A pair with one win each nets the SAME win_counts as a pair with two
    draws — both settle at 1.0/1.0 over 2 games.
    """
    one_win_each = [
        {"anchor_white": "maia1500", "anchor_black": "sf5", "result": "white_win"},
        {"anchor_white": "sf5", "anchor_black": "maia1500", "result": "white_win"},
    ]
    two_draws = [
        {"anchor_white": "maia1500", "anchor_black": "sf5", "result": "draw"},
        {"anchor_white": "sf5", "anchor_black": "maia1500", "result": "draw"},
    ]

    wc_wins = build_win_counts(one_win_each)
    wc_draws = build_win_counts(two_draws)

    assert wc_wins[("maia1500", "sf5")] == pytest.approx(1.0, abs=DRAW_TOLERANCE)
    assert wc_wins[("sf5", "maia1500")] == pytest.approx(1.0, abs=DRAW_TOLERANCE)
    assert wc_draws[("maia1500", "sf5")] == pytest.approx(
        wc_wins[("maia1500", "sf5")], abs=DRAW_TOLERANCE
    )
    assert wc_draws[("sf5", "maia1500")] == pytest.approx(
        wc_wins[("sf5", "maia1500")], abs=DRAW_TOLERANCE
    )


def test_connectivity() -> None:
    """check_connectivity enforces D-04: full reachability AND >= 2 cross-family edges."""
    anchors = ["maia1500", "maia1900", "sf5", "sf8"]

    disconnected_pairs = {("maia1500", "maia1900"), ("sf5", "sf8")}
    with pytest.raises(RuntimeError):
        check_connectivity(disconnected_pairs, anchors)

    one_cross_link_pairs = {("maia1500", "maia1900"), ("sf5", "sf8"), ("maia1500", "sf5")}
    with pytest.raises(RuntimeError):
        check_connectivity(one_cross_link_pairs, anchors)

    two_cross_link_pairs = {
        ("maia1500", "maia1900"),
        ("sf5", "sf8"),
        ("maia1500", "sf5"),
        ("maia1900", "sf8"),
    }
    check_connectivity(two_cross_link_pairs, anchors)  # must NOT raise


def test_main_single_bridge_both_orientations_fails_connectivity(tmp_path: Path) -> None:
    """CR-01 regression: one real cross-family pairing seen in BOTH color orientations is ONE link.

    Colors alternate per game, so a single real bridge appears as both (a, b)
    and (b, a) in the raw TSV. main() must canonicalize before its D-04
    re-check — without canonicalization the duplicate orientation counted as a
    second cross-family link and a non-identifiable graph passed the guard.
    """
    rows = [
        ("maia1500", "maia1900", "white_win"),
        ("maia1900", "maia1500", "white_win"),
        ("sf5", "sf8", "white_win"),
        ("sf8", "sf5", "white_win"),
        # ONE real cross-family bridge, played in both orientations:
        ("maia1500", "sf5", "white_win"),
        ("sf5", "maia1500", "white_win"),
    ]
    tsv = tmp_path / "single-bridge.tsv"
    lines: list[str] = ["\t".join(TSV_HEADER)]
    for idx, (white, black, result) in enumerate(rows):
        lines.append(
            f"measure\t{white}\t{black}\t{result}\tcheckmate\t40\t{idx}\tTest Opening\t1\tdeadbeef"
        )
    tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="cross-family"):
        main(
            [
                "--input",
                str(tsv),
                "--out-js",
                str(tmp_path / "scale.mjs"),
                "--out-json",
                str(tmp_path / "scale.json"),
            ]
        )


def _games_for_pair(a: str, b: str, a_wins: int, b_wins: int) -> list[dict[str, str]]:
    """Builds an alternating-result game list for one (a, b) pair — no draws, mixed record."""
    games = [{"anchor_white": a, "anchor_black": b, "result": "white_win"} for _ in range(a_wins)]
    games += [{"anchor_white": a, "anchor_black": b, "result": "black_win"} for _ in range(b_wins)]
    return games


def test_bootstrap() -> None:
    """bootstrap_ci returns a finite, sane-width interval per anchor for a well-conditioned graph."""
    games = (
        _games_for_pair("maia1500", "maia1900", a_wins=4, b_wins=16)
        + _games_for_pair("maia1900", "sf5", a_wins=10, b_wins=10)
        + _games_for_pair("maia1500", "sf5", a_wins=8, b_wins=12)
    )
    anchors = ["maia1500", "maia1900", "sf5"]

    point = apply_scale_fix(fit_bradley_terry(build_win_counts(games), anchors))
    cis = bootstrap_ci(games, anchors, n_samples=200, seed=42)

    assert set(cis) == set(anchors)
    for anchor in anchors:
        lo, hi = cis[anchor]
        assert math.isfinite(lo)
        assert math.isfinite(hi)
        assert lo <= point[anchor] <= hi
        width = hi - lo
        if anchor == "maia1500":
            # The pin anchor is fixed to exactly 1500.0 in EVERY resample by
            # apply_scale_fix's own definition — its CI collapses to a point,
            # by construction, not a bug.
            assert width == pytest.approx(0.0, abs=SCALE_FIX_TOLERANCE)
        else:
            assert BOOTSTRAP_MIN_WIDTH < width < BOOTSTRAP_MAX_WIDTH


def test_residuals() -> None:
    """compute_residuals returns observed-minus-predicted per pair, cross-family pairs flagged."""
    ratings = {"maia1500": 1500.0, "maia1900": 1900.0, "sf5": 1700.0}
    win_counts = {
        ("maia1500", "maia1900"): 3.0,
        ("maia1900", "maia1500"): 27.0,
        ("maia1500", "sf5"): 15.0,
        ("sf5", "maia1500"): 15.0,
    }

    residuals = compute_residuals(win_counts, ratings)
    by_pair = {row["pair"]: row for row in residuals}

    same_family = by_pair[("maia1500", "maia1900")]
    observed_same = 3.0 / 30.0
    predicted_same = _expected_score(1500.0, 1900.0)
    assert same_family["observed"] == pytest.approx(observed_same, abs=RESIDUAL_TOLERANCE)
    assert same_family["predicted"] == pytest.approx(predicted_same, abs=RESIDUAL_TOLERANCE)
    assert same_family["residual"] == pytest.approx(
        observed_same - predicted_same, abs=RESIDUAL_TOLERANCE
    )
    assert same_family["cross_family"] is False

    cross_family = by_pair[("maia1500", "sf5")]
    observed_cross = 15.0 / 30.0
    predicted_cross = _expected_score(1500.0, 1700.0)
    assert cross_family["observed"] == pytest.approx(observed_cross, abs=RESIDUAL_TOLERANCE)
    assert cross_family["predicted"] == pytest.approx(predicted_cross, abs=RESIDUAL_TOLERANCE)
    assert cross_family["residual"] == pytest.approx(
        observed_cross - predicted_cross, abs=RESIDUAL_TOLERANCE
    )
    assert cross_family["cross_family"] is True


def _synthetic_bot_counts(
    true_rating: float, fixed_ratings: dict[str, float], games_per_anchor: float
) -> tuple[dict[str, float], dict[str, float]]:
    """Builds EXACT Bradley-Terry folded win/games counts for a bot at `true_rating`.

    win_counts[a] = games * P(bot beats anchor a) at the model's expected score,
    so `true_rating` is an exact fixed point of the single-parameter MM iteration
    (up to the fit's own numerical tolerance) — the fit must recover it.
    """
    wins = {a: games_per_anchor * _expected_score(true_rating, r) for a, r in fixed_ratings.items()}
    games = {a: games_per_anchor for a in fixed_ratings}
    return wins, games


def test_fit_bot_cell_rating_synthetic_ground_truth() -> None:
    """Single-parameter pinned-anchor MLE recovers a KNOWN bot strength (D-06).

    The counts are generated at the model's exact expected scores against the 10
    fixed anchors, so the true rating is an exact fixed point — the fit must
    return it within a small tolerance while the anchors stay pinned.
    """
    true_rating = 1450.0
    wins, games = _synthetic_bot_counts(true_rating, FIXED_RATINGS, games_per_anchor=500.0)

    fitted = fit_bot_cell_rating(wins, games, FIXED_RATINGS)

    assert fitted == pytest.approx(true_rating, abs=BOT_CELL_RECOVERY_TOLERANCE)


def test_g_preset_sign() -> None:
    """g_preset = rating_vs_maia - rating_vs_sf carries the fixture's asymmetry (Pitfall 3).

    On a fabricated cell that beats the SF family HARDER than the Maia family,
    the SF-fit rating must land clearly above the Maia-fit rating, so g_preset
    (Maia - SF) is clearly NEGATIVE — the two families are fit separately and the
    gap is a real measured signal, never averaged away.
    """
    maia = {a: r for a, r in FIXED_RATINGS.items() if a.startswith("maia")}
    sf = {a: r for a, r in FIXED_RATINGS.items() if a.startswith("sf")}

    # Same games everywhere; the bot performs as a 1450-strength player vs Maia
    # but as a much stronger 1700-strength player vs SF (asymmetric by construction).
    wins_vs_maia, games_vs_maia = _synthetic_bot_counts(1450.0, maia, games_per_anchor=500.0)
    wins_vs_sf, games_vs_sf = _synthetic_bot_counts(1700.0, sf, games_per_anchor=500.0)

    rating_vs_maia = fit_bot_cell_rating(wins_vs_maia, games_vs_maia, FIXED_RATINGS)
    rating_vs_sf = fit_bot_cell_rating(wins_vs_sf, games_vs_sf, FIXED_RATINGS)
    g_preset = rating_vs_maia - rating_vs_sf

    assert rating_vs_sf > rating_vs_maia
    assert g_preset < -G_PRESET_MIN_MAGNITUDE


def test_fit_bot_cell_rating_rejects_bad_input() -> None:
    """fit_bot_cell_rating fails loud (T-180-02), never NaN, on empty/mis-keyed input."""
    # Empty games -> nothing to fit.
    with pytest.raises(ValueError):
        fit_bot_cell_rating({}, {}, FIXED_RATINGS)

    # A counted anchor label absent from fixed_ratings -> refuse to fit garbage.
    with pytest.raises(ValueError):
        fit_bot_cell_rating(
            {"maia1500": 5.0, "not_an_anchor": 3.0},
            {"maia1500": 10.0, "not_an_anchor": 10.0},
            FIXED_RATINGS,
        )
