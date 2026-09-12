"""Shared feature frame for the tilt data story (stories/tilt/).

Same feature engineering as the EDA notebook (tilt_study.py), plus the story hygiene
columns from the confound probes (probes/streak_controls.py) and a colour-aware
calibration. Everything reads the cached parquet extracts in analysis/out/tilt/:

    games.parquet          rated human games, both ratings known (tilt_study.py)
    clock_ends.parquet     final clocks per side (extract_clocks.py)
    acc.parquet            user colour + lichess-imported accuracy (probes/extract_acc.py)
    move_feats.parquet     per-side think-time features (probes/extract_moves.py)
    flaws_byus.parquet     blunders/mistakes in the uniformly analysed arm (probes/extract_flaws.py)
    endgame_entry.parquet  eval at endgame entry (extract_endgame_entry.py)

Definitions (the technical report quotes these):
- Unit: consecutive rated games of one user in one time-control bucket, by start time.
- Game end = start + time used by both sides from %clk; fallback median seconds/ply.
- Session: a break of >= 60 min (from the END of the previous game) starts a new one.
- Streak: run of same-result games ending at the previous game; draws break streaks.
- Equal footing: |my rating - opponent rating| <= 100. Only such games are SCORED;
  sequence features use the full history.
- Expected score: empirical mean score in the same (TC, 400-pt rating bucket, 25-pt
  rating-gap bin, colour), fitted on equal-footing, hygiene-clean, in-session games (the
  frame the story scores, so the residual averages zero there). Residual = score - expected.
- Hygiene (story cuts): drop each user's first 100 imported games in the TC and games
  played more than 150 points from the user's long-run median rating in the TC. The
  import is the most recent 1,000 games in a 36-month window, so the first 100 are
  mostly the oldest games of an established account, not provisional ones: what they
  carry is three years of rating drift (mean |rating - median| 62 vs 36 later, residual
  +0.5 pp), plus the odd new account. The streak must lie within one session.
"""

from pathlib import Path

import numpy as np
import polars as pl

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "analysis" / "out" / "tilt"

SESSION_GAP_MIN = 60
CAL_BIN_ELO = 25
EQUAL_FOOTING_TOLERANCE = 100
ELO_ANCHORS = (800, 1200, 1600, 2000, 2400)
TC_ORDER = ["bullet", "blitz", "rapid", "classical"]
MIN_HISTORY_GAMES = 100  # hygiene C: first 100 games of a user-TC history are dropped
MAX_RATING_DEV = 150  # hygiene D: |rating - long-run median| > 150 dropped
MAX_STREAK = 7  # story axis: -7 = 7 or more losses ... +7 = 7 or more wins
# Fresh-opponent control: the next opponent must not appear in any game of the streak that just
# ended. Scanning this many games back covers every streak the story axis distinguishes; longer
# streaks are checked over their last SERIES_LOOKBACK games only.
SERIES_LOOKBACK = 12
USER_W = ["user_id", "tc"]


def load_games() -> pl.DataFrame:
    """Full feature frame over every rated human game (not yet filtered)."""
    raw = pl.read_parquet(OUT / "games.parquet")
    clocks = pl.read_parquet(OUT / "clock_ends.parquet")
    colour = pl.read_parquet(OUT / "acc.parquet").select("game_id", "user_color")
    g = raw.join(clocks, on="game_id", how="left").join(colour, on="game_id", how="left")

    g = g.with_columns(
        dur_clk=(
            2 * pl.col("base_s").cast(pl.Float64)
            + pl.col("inc_s") * pl.col("ply_count")
            - pl.col("w_last_clk")
            - pl.col("b_last_clk")
        ).clip(lower_bound=0)
    )
    spp = (
        g.filter(pl.col("dur_clk").is_not_null() & (pl.col("ply_count") > 0))
        .group_by("tc")
        .agg((pl.col("dur_clk") / pl.col("ply_count")).median().alias("sec_per_ply"))
    )
    g = g.join(spp, on="tc").with_columns(
        dur_s=pl.coalesce(pl.col("dur_clk"), pl.col("ply_count") * pl.col("sec_per_ply")),
        has_clock=pl.col("dur_clk").is_not_null(),
    )
    g = g.with_columns(end_at=pl.col("played_at") + pl.duration(seconds=pl.col("dur_s")))

    w = USER_W
    g = g.sort(w + ["played_at"]).with_columns(
        gap_before_s=(pl.col("played_at") - pl.col("end_at").shift(1)).dt.total_seconds().over(w),
        gap_after_s=(pl.col("played_at").shift(-1) - pl.col("end_at")).dt.total_seconds().over(w),
        prev_score=pl.col("score").shift(1).over(w),
        prev_opp=pl.col("opp").shift(1).over(w),
        prev_termination=pl.col("termination").shift(1).over(w),
        prev_ply=pl.col("ply_count").shift(1).over(w),
        prev_game_id=pl.col("game_id").shift(1).over(w),
        prev_edge=(pl.col("my_r") - pl.col("opp_r")).shift(1).over(w),
        hist_idx=pl.int_range(pl.len()).over(w),
        med_r=pl.col("my_r").median().over(w),
    )
    g = g.with_columns(
        dir=pl.when(pl.col("score") == 1).then(1).when(pl.col("score") == 0).then(-1).otherwise(0)
    ).with_columns(
        run_id=(pl.col("dir") != pl.col("dir").shift(1)).cast(pl.Int32).cum_sum().over(w)
    )
    g = g.with_columns(run_len=pl.int_range(pl.len()).over(w + ["run_id"]) + 1)
    g = g.with_columns(
        streak_dir=pl.col("dir").shift(1).over(w),
        streak_len=pl.col("run_len").shift(1).over(w),
    )
    # A rematch series is not an independent draw from the pool: the same opponent carries an
    # opponent-specific mismatch the rating-gap calibration cannot see, and their state is
    # correlated with yours (they just lost to you k times). Within a rematch the streak effect
    # is about twice the fresh-opponent effect, so the streak frame requires a fresh opponent;
    # rematches are analysed on their own in section 6.
    g = g.with_columns(
        fresh_opponent=~pl.any_horizontal(
            [
                (
                    (pl.col("opp") == pl.col("opp").shift(i).over(w)) & (pl.col("streak_len") >= i)
                ).fill_null(False)
                for i in range(1, SERIES_LOOKBACK + 1)
            ]
        )
    )
    g = g.with_columns(
        new_session=pl.col("gap_before_s").is_null()
        | (pl.col("gap_before_s") >= SESSION_GAP_MIN * 60)
    ).with_columns(session_id=pl.col("new_session").cast(pl.Int32).cum_sum().over(w))
    s = w + ["session_id"]
    g = g.with_columns(
        session_idx=pl.int_range(pl.len()).over(s) + 1,
        session_len=pl.len().over(s),
        session_elapsed_min=(
            pl.col("played_at") - pl.col("played_at").min().over(s)
        ).dt.total_minutes(),
        last_of_session=pl.col("gap_after_s").is_null()
        | (pl.col("gap_after_s") >= SESSION_GAP_MIN * 60),
        run_start_session=pl.col("session_id").first().over(w + ["run_id"]),
    ).with_columns(
        # The streak that just ended lay entirely within ONE session (the previous game's).
        # Bug fixed: comparing against the CURRENT game's session made the flag false whenever
        # the next game came after a >= 60 min break, which emptied every long-break cell of the
        # break test. The previous game's session is the right anchor.
        streak_same_session=pl.col("run_start_session").shift(1).over(w)
        == pl.col("session_id").shift(1).over(w),
        in_session=pl.col("gap_before_s") < SESSION_GAP_MIN * 60,
        r_dev=pl.col("my_r") - pl.col("med_r"),
    )
    floor = ELO_ANCHORS[0]
    g = g.with_columns(
        elo_bucket=(((pl.col("my_r") - floor) // 400) * 400 + floor).clip(floor, ELO_ANCHORS[-1]),
        gap_bin=((pl.col("my_r") - pl.col("opp_r")) / CAL_BIN_ELO).floor(),
        equal_footing=(pl.col("my_r") - pl.col("opp_r")).abs() <= EQUAL_FOOTING_TOLERANCE,
        hygiene=(pl.col("hist_idx") >= MIN_HISTORY_GAMES)
        & (pl.col("r_dev").abs() <= MAX_RATING_DEV),
        score=pl.col("score").cast(pl.Float64),
    )
    cal_keys = ["tc", "elo_bucket", "gap_bin", "user_color"]
    # Calibration frame = the frame the story scores: equal footing, settled accounts, and
    # not the first game of a session. Fitting on ALL equal-footing games put the residual's
    # zero point on a population that includes the first-100 (rating-drift) games and every
    # cold-start first game of a session, which the streak cells exclude. That shifted every
    # in-session cell by a time-control-specific offset (bullet +0.4, classical -1.7 pp) and
    # made the bullet-vs-rapid comparison in section 3 mostly a warm-up artefact.
    cal_frame = g.filter(pl.col("equal_footing") & pl.col("hygiene") & pl.col("in_session"))
    cal = cal_frame.group_by(cal_keys).agg(pl.col("score").mean().alias("exp_score"))
    cal_nc = cal_frame.group_by(cal_keys[:3]).agg(
        pl.col("score").mean().alias("exp_score_nocolour")
    )
    g = (
        g.join(cal, on=cal_keys, how="left")
        .join(cal_nc, on=cal_keys[:3], how="left")
        .with_columns(
            resid=pl.col("score") - pl.col("exp_score"),
            resid_nocolour=pl.col("score") - pl.col("exp_score_nocolour"),
            rematch=pl.col("opp") == pl.col("prev_opp"),
            # signed streak length for the curve: -7 = 7+ losses ... +7 = 7+ wins, 0 = draw
            x=(pl.col("streak_dir") * pl.col("streak_len").clip(upper_bound=MAX_STREAK)).cast(
                pl.Int32
            ),
        )
        .sort(w + ["played_at"])
    )
    return g


def streak_label(d: str = "streak_dir", n: str = "streak_len") -> pl.Expr:
    dc, nc = pl.col(d), pl.col(n)
    return (
        pl.when(dc.is_null())
        .then(pl.lit("first"))
        .when(dc == 0)
        .then(pl.lit("D"))
        .when((dc == -1) & (nc >= 3))
        .then(pl.lit("LLL+"))
        .when((dc == -1) & (nc == 2))
        .then(pl.lit("LL"))
        .when(dc == -1)
        .then(pl.lit("L"))
        .when((dc == 1) & (nc >= 3))
        .then(pl.lit("WWW+"))
        .when((dc == 1) & (nc == 2))
        .then(pl.lit("WW"))
        .otherwise(pl.lit("W"))
    )


def boot_mean(
    df: pl.DataFrame, col: str, reps: int = 300, seed: int = 7
) -> tuple[float, float, float]:
    """Mean of `col` with a 95% CI from a bootstrap over users (a user's games are correlated)."""
    if df.height == 0:
        return (float("nan"), float("nan"), float("nan"))
    per_user = (
        df.group_by("user_id")
        .agg(pl.col(col).sum().alias("s"), pl.col(col).count().alias("n"))
        .sort("user_id")
    )  # group_by order is not deterministic; sort so the bootstrap is reproducible
    s = per_user["s"].to_numpy().astype(float)
    n = per_user["n"].to_numpy().astype(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(s), size=(reps, len(s)))
    boots = s[idx].sum(axis=1) / n[idx].sum(axis=1)
    return (
        float(s.sum() / n.sum()),
        float(np.percentile(boots, 2.5)),
        float(np.percentile(boots, 97.5)),
    )


def boot_diff(
    a: pl.DataFrame, b: pl.DataFrame, col: str, reps: int = 300, seed: int = 7
) -> tuple[float, float, float]:
    """Difference of means (a - b) with a user-bootstrap CI; users resampled jointly across a and b."""
    users = pl.concat([a.select("user_id"), b.select("user_id")]).unique().sort("user_id")
    ua = users.join(
        a.group_by("user_id").agg(pl.col(col).sum().alias("s"), pl.col(col).count().alias("n")),
        on="user_id",
        how="left",
    ).fill_null(0)
    ub = users.join(
        b.group_by("user_id").agg(pl.col(col).sum().alias("s"), pl.col(col).count().alias("n")),
        on="user_id",
        how="left",
    ).fill_null(0)
    sa, na = ua["s"].to_numpy().astype(float), ua["n"].to_numpy().astype(float)
    sb, nb = ub["s"].to_numpy().astype(float), ub["n"].to_numpy().astype(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(sa), size=(reps, len(sa)))
    d = sa[idx].sum(1) / np.maximum(na[idx].sum(1), 1) - sb[idx].sum(1) / np.maximum(
        nb[idx].sum(1), 1
    )
    point = sa.sum() / max(na.sum(), 1) - sb.sum() / max(nb.sum(), 1)
    return (float(point), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5)))
