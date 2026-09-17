"""Robustness tables for the tilt data story (methods review 2026-09-16, priorities 1, 2, 4).

Run after gen_story.py (it reuses the cached feature frame):
    uv run --project analysis python analysis/tilt_study/robustness.py

Writes to analysis/out/tilt/story/:
    timing_diagnostics.csv   clock coverage, negative gaps, censoring, per time control
    sensitivity.csv          the headline residual under alternative session / hygiene rules
    within_player.csv        joint within-player model: streak contrasts vs exactly one loss
    within_player_swings.csv the same model's hot-minus-cold swing at 3 and 6+
    continuation.csv         P(next game within the hour) after k straight losses / wins

Every scored outcome is equal-footing. The models are descriptive, not causal: they ask
whether the same player, at a comparable moment, scores differently after a streak.
"""

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from story_data import (  # noqa: E402
    OUT,
    TC_ORDER,
    USER_W,
    boot_mean,
    cached_games,
    load_games,
)

STORY = OUT / "story"
CAL_KEYS = ["tc", "elo_bucket", "gap_bin", "user_color"]
STREAK_AXIS = list(range(-6, 7))  # -6 = 6+ losses ... 0 = draw ... +6 = 6+ wins
REFERENCE_STREAK = -1  # contrasts are relative to "exactly one loss"
SWING_STREAKS = (3, 6)
SENSITIVITY_STREAKS = [-1, -2, -3, -6, 3, 6]
MIN_CLOCK_LEVEL_GAMES = 500  # rarer exact clock settings are pooled into "other"
DEPTH_EDGES = [3, 5, 10, 20]
DEPTH_LABELS = ["2-3", "4-5", "6-10", "11-20", "21+"]
ELAPSED_EDGES = [15, 30, 60, 120]
ELAPSED_LABELS = ["0-15", "15-30", "30-60", "60-120", "120+"]
SENSITIVITY_REPS = 500
CONTINUATION_REPS = 500
Z95 = 1.96
SENSITIVITY_VARIANTS: list[tuple[str, dict[str, int | None]]] = [
    ("primary", {}),
    ("30-minute sessions", {"session_gap_min": 30}),
    ("120-minute sessions", {"session_gap_min": 120}),
    ("keep first 100 games", {"min_history": 0}),
    ("no rating-deviation filter", {"max_rating_dev": None}),
    ("neither history filter", {"min_history": 0, "max_rating_dev": None}),
    ("game end +30 s", {"end_delay_s": 30}),
]
MODELS = [
    "player + ratings + clock",
    "also session depth and elapsed time",
    "player x quarter intercepts",
]


def eligible(g: pl.DataFrame) -> pl.DataFrame:
    """The controlled streak frame: same games as the story's hero curve."""
    return g.filter(
        pl.col("equal_footing")
        & pl.col("hygiene")
        & pl.col("in_session")
        & pl.col("streak_same_session")
        & pl.col("fresh_opponent")
    )


def dense_index(df: pl.DataFrame, cols: list[str], name: str) -> pl.DataFrame:
    """Attach a 0-based dense integer id for each distinct combination of `cols`."""
    keys = df.select(cols).unique().sort(cols).with_row_index(name)
    return df.join(keys, on=cols)


# ---- headline intervals with the benchmark refitted inside each resample -------------


def refit_bootstrap(g: pl.DataFrame, reps: int = 1000, seed: int = 20260916) -> pl.DataFrame:
    """User bootstrap of the streak residuals that also refits the calibration table.

    gen_story's boot_mean resamples users over already-computed residuals, which treats
    the expectation as known. Here each resample re-estimates the (tc, rating bucket,
    gap bin, colour) means from the resampled calibration frame before scoring.
    """
    cal = dense_index(
        g.filter(pl.col("equal_footing") & pl.col("hygiene") & pl.col("in_session")),
        ["user_id"],
        "u",
    )
    cal = dense_index(cal, CAL_KEYS, "c")
    n_users, n_cells = cal["u"].n_unique(), cal["c"].n_unique()  # dense 0..n-1 ids
    target = eligible(cal).with_columns(k=pl.col("x").clip(-6, 6) + 6)
    a = cal.group_by("u", "c").agg(pl.col("score").sum().alias("s"), pl.len().alias("n"))
    b = target.group_by("u", "c", "k").agg(pl.col("score").sum().alias("s"), pl.len().alias("n"))
    au, ac, a_s, a_n = (a[c].to_numpy() for c in ["u", "c", "s", "n"])
    bu, bc, bk, b_s, b_n = (b[c].to_numpy() for c in ["u", "c", "k", "s", "n"])
    n_k = len(STREAK_AXIS)
    rng = np.random.default_rng(seed)
    samples = np.empty((reps, n_k))
    for i in range(reps):
        w = np.bincount(rng.integers(n_users, size=n_users), minlength=n_users)
        cell_n = np.bincount(ac, weights=w[au] * a_n, minlength=n_cells)
        cell_s = np.bincount(ac, weights=w[au] * a_s, minlength=n_cells)
        expected = np.divide(cell_s, cell_n, out=np.zeros_like(cell_s), where=cell_n > 0)
        n = np.bincount(bk, weights=w[bu] * b_n, minlength=n_k)
        s = np.bincount(bk, weights=w[bu] * (b_s - b_n * expected[bc]), minlength=n_k)
        samples[i] = np.divide(s, n, out=np.full(n_k, np.nan), where=n > 0) * 100
    return pl.DataFrame(
        {
            "x": STREAK_AXIS,
            "resid_lo": np.nanpercentile(samples, 2.5, axis=0),
            "resid_hi": np.nanpercentile(samples, 97.5, axis=0),
        }
    )


# ---- within-player model ------------------------------------------------------------


def within_fit(
    y: np.ndarray, x: np.ndarray, groups: np.ndarray, clusters: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """OLS with absorbed group intercepts and a cluster-robust (CR1) covariance.

    Outcome and every regressor are demeaned within group (Frisch-Waugh-Lovell). A
    pseudoinverse tolerates redundant nuisance columns; the reported contrasts all have
    support. Normal intervals are fine with thousands of clusters.
    """
    y, x = y.copy(), x.copy()
    n, p = x.shape
    n_groups = groups.max() + 1
    counts = np.bincount(groups, minlength=n_groups)
    y -= (np.bincount(groups, weights=y, minlength=n_groups) / counts)[groups]
    for j in range(p):
        x[:, j] -= (np.bincount(groups, weights=x[:, j], minlength=n_groups) / counts)[groups]
    xtx = x.T @ x
    bread = np.linalg.pinv(xtx, rcond=1e-11)
    beta = bread @ (x.T @ y)
    residual = y - x @ beta
    n_clusters = clusters.max() + 1
    scores = np.empty((n_clusters, p))
    for j in range(p):
        scores[:, j] = np.bincount(clusters, weights=x[:, j] * residual, minlength=n_clusters)
    dof = n_clusters / (n_clusters - 1) * (n - 1) / (n - n_groups - np.linalg.matrix_rank(xtx))
    return beta, dof * bread @ (scores.T @ scores) @ bread


def model_frame(g: pl.DataFrame) -> pl.DataFrame:
    d = eligible(g).drop_nulls(["score", "my_r", "opp_r", "base_s", "inc_s", "user_color", "x"])
    d = d.with_columns(
        xc=pl.col("x").clip(-6, 6),
        clock=pl.col("base_s").cast(pl.String)
        + "+"
        + pl.col("inc_s").cast(pl.Int64).cast(pl.String),
        depth=pl.col("session_idx").cut(DEPTH_EDGES, labels=DEPTH_LABELS).cast(pl.String),
        elapsed=pl.col("session_elapsed_min")
        .cut(ELAPSED_EDGES, labels=ELAPSED_LABELS)
        .cast(pl.String),
        quarter=pl.col("played_at").dt.year() * 4 + pl.col("played_at").dt.quarter(),
    )
    d = dense_index(d, USER_W, "group")
    d = dense_index(d, USER_W + ["quarter"], "group_quarter")
    return dense_index(d, ["user_id"], "cluster")


def dummies(
    values: np.ndarray, prefix: str, drop_first: bool = True
) -> tuple[list[np.ndarray], list[str]]:
    levels = sorted(set(values.tolist()))[1 if drop_first else 0 :]
    return [(values == lv).astype(float) for lv in levels], [f"{prefix}_{lv}" for lv in levels]


def fit_models(g: pl.DataFrame) -> None:
    d = model_frame(g)
    contrasts = [k for k in STREAK_AXIS if k != REFERENCE_STREAK]
    x = d["xc"].to_numpy()
    cols = [(x == k).astype(float) for k in contrasts]
    names = [f"streak_{k}" for k in contrasts]
    gap = (d["my_r"] - d["opp_r"]).to_numpy() / 100
    cols += [
        gap,
        gap**2,
        (d["my_r"].to_numpy() - 1600) / 400,
        (d["user_color"] == "white").to_numpy().astype(float),
    ]
    names += ["gap", "gap_squared", "rating", "white"]
    common = (
        d.group_by("clock").len().filter(pl.col("len") >= MIN_CLOCK_LEVEL_GAMES)["clock"].to_list()
    )
    clock = d["clock"].to_numpy().astype(str)
    c_cols, c_names = dummies(np.where(np.isin(clock, common), clock, "other"), "clock")
    cols, names = cols + c_cols, names + c_names
    s_cols: list[np.ndarray] = []
    for key in ["depth", "elapsed"]:
        k_cols, _ = dummies(d[key].to_numpy().astype(str), key)
        s_cols += k_cols
    y, clusters = d["score"].to_numpy(), d["cluster"].to_numpy()
    rows, swings = [], []
    for model in MODELS:
        design = cols + (s_cols if model.startswith("also") else [])
        groups = d["group_quarter" if model.startswith("player x") else "group"].to_numpy()
        beta, cov = within_fit(y, np.column_stack(design), groups, clusters)
        for j, k in enumerate(contrasts):
            se = np.sqrt(max(cov[j, j], 0))
            rows.append(
                {
                    "model": model,
                    "streak": k,
                    "n": int((x == k).sum()),
                    "contrast_pp": 100 * beta[j],
                    "lo": 100 * (beta[j] - Z95 * se),
                    "hi": 100 * (beta[j] + Z95 * se),
                }
            )
        for k in SWING_STREAKS:
            i, j = contrasts.index(k), contrasts.index(-k)
            swing = beta[i] - beta[j]
            se = np.sqrt(max(cov[i, i] + cov[j, j] - 2 * cov[i, j], 0))
            swings.append(
                {
                    "model": model,
                    "streak": k,
                    "hot_minus_cold_pp": 100 * swing,
                    "lo": 100 * (swing - Z95 * se),
                    "hi": 100 * (swing + Z95 * se),
                }
            )
        print(
            "fit",
            model,
            "n",
            d.height,
            "parameters",
            len(design),
            "groups",
            groups.max() + 1,
            flush=True,
        )
    pl.DataFrame(rows).write_csv(STORY / "within_player.csv")
    pl.DataFrame(swings).write_csv(STORY / "within_player_swings.csv")
    (STORY / "within_player_design.json").write_text(
        json.dumps(
            {
                "n": d.height,
                "users": d["user_id"].n_unique(),
                "streams": d["group"].n_unique(),
                "stream_quarters": d["group_quarter"].n_unique(),
                "reference": "exactly one loss",
                "common_clocks": common,
                "nuisance": "player x time-control intercepts (or player x time-control x quarter), "
                "rating gap and its square, own rating, colour, exact clock setting "
                f"(levels under {MIN_CLOCK_LEVEL_GAMES} games pooled); optional session depth and "
                "elapsed-time categories",
            },
            indent=2,
        )
    )


# ---- sensitivity of the headline to the session and hygiene rules ----------------------


def streak_rows(d: pl.DataFrame, spec: str) -> list[dict]:
    rows = []
    for k in SENSITIVITY_STREAKS:
        c = d.filter(pl.col("x").clip(-6, 6) == k)
        m, lo, hi = boot_mean(c, "resid", reps=SENSITIVITY_REPS)
        rows.append(
            {
                "specification": spec,
                "streak": k,
                "n": c.height,
                "residual_pp": 100 * m,
                "lo": 100 * lo,
                "hi": 100 * hi,
            }
        )
    return rows


def sensitivities(g: pl.DataFrame) -> None:
    rows = []
    for name, args in SENSITIVITY_VARIANTS:
        frame = g if not args else load_games(**args)  # ty: ignore[invalid-argument-type]  (int | None per key)
        rows += streak_rows(eligible(frame), name)
        print("sensitivity", name, flush=True)
    # Zero-increment games are a timing check (their clocks are monotone); refit their benchmark.
    z = g.filter(pl.col("inc_s") == 0).drop("exp_score", "resid")
    cal = (
        z.filter(pl.col("equal_footing") & pl.col("hygiene") & pl.col("in_session"))
        .group_by(CAL_KEYS)
        .agg(pl.col("score").mean().alias("exp_score"))
    )
    z = z.join(cal, on=CAL_KEYS, how="left").with_columns(
        resid=pl.col("score") - pl.col("exp_score")
    )
    rows += streak_rows(eligible(z), "zero increment only")
    pl.DataFrame(rows).write_csv(STORY / "sensitivity.csv")


# ---- who keeps playing ------------------------------------------------------------------


def continuation(g: pl.DataFrame) -> None:
    """P(next game starts within the hour) after k straight losses / wins.

    The streak game itself must pass equal footing (its outcome conditions the rate). No
    condition on the NEXT game (fresh opponent, equal footing), which would select on the
    answer. The last game of a history is censored, not a stop.
    """
    d = g.filter(
        pl.col("equal_footing")
        & pl.col("hygiene")
        & (pl.col("run_start_session") == pl.col("session_id"))
        & pl.col("dir").is_in([-1, 1])
    ).with_columns(k=pl.col("run_len").clip(upper_bound=6))
    rows = []
    for tc in ["all", *TC_ORDER]:
        frame = d if tc == "all" else d.filter(pl.col("tc") == tc)
        for sign in [-1, 1]:
            for k in range(1, 7):
                cell = frame.filter((pl.col("dir") == sign) & (pl.col("k") == k))
                known = cell.filter(pl.col("last_of_session").is_not_null()).with_columns(
                    continues=(~pl.col("last_of_session")).cast(pl.Float64)
                )
                m, lo, hi = boot_mean(known, "continues", reps=CONTINUATION_REPS)
                cont, stop = (
                    known.filter(pl.col("continues") == 1),
                    known.filter(pl.col("continues") == 0),
                )
                rows.append(
                    {
                        "tc": tc,
                        "streak": sign * k,
                        "n": known.height,
                        "censored_or_unknown_timing": cell.height - known.height,
                        "continue_pct": 100 * m,
                        "lo": 100 * lo,
                        "hi": 100 * hi,
                        "continuer_rating": cont["my_r"].mean(),
                        "stopper_rating": stop["my_r"].mean(),
                        "continuer_session_idx": cont["session_idx"].mean(),
                        "stopper_session_idx": stop["session_idx"].mean(),
                    }
                )
    pl.DataFrame(rows).write_csv(STORY / "continuation.csv")


# ---- timing validity ------------------------------------------------------------------


def timing_diagnostics(g: pl.DataFrame) -> None:
    (
        g.group_by("tc")
        .agg(
            pl.len().alias("games"),
            pl.col("has_clock").mean().mul(100).round(2).alias("usable_clock_pct"),
            (pl.col("n_clk") == pl.col("ply_count"))
            .mean()
            .mul(100)
            .round(2)
            .alias("complete_clock_pct"),
            ((pl.col("w_first_clk") - pl.col("base_s")).abs() > 1)
            .mean()
            .mul(100)
            .round(2)
            .alias("first_clock_mismatch_pct"),
            (
                (pl.col("w_last_clk") > pl.col("w_min_clk"))
                | (pl.col("b_last_clk") > pl.col("b_min_clk"))
            )
            .mean()
            .mul(100)
            .round(1)
            .alias("last_clock_above_minimum_pct"),
            (pl.col("raw_gap_before_s") < 0).sum().alias("negative_gaps"),
            pl.col("gap_before_s").is_not_null().mean().mul(100).round(2).alias("valid_gap_pct"),
            (~pl.col("next_observed")).sum().alias("right_censored"),
        )
        .sort("tc")
        .write_csv(STORY / "timing_diagnostics.csv")
    )


def main() -> None:
    g = cached_games()
    timing_diagnostics(g)
    sensitivities(g)
    continuation(g)
    fit_models(g)
    print("done ->", STORY)


if __name__ == "__main__":
    main()
