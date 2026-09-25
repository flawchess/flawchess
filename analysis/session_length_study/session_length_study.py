"""Session-length study: is there an ideal number of games per sitting, per time control?

Prompted by GM Noël Studer's feedback on the tilt story (2026-09-20): he played blitz in
blocks of 6 games (quality dropped beyond that) and suggests 2-3 rapid games with short
pauses. Question: does the data show a session-position effect on performance, does it
differ by time control and rating, and is it "number of games" or "minutes at the board"?

Reuses the tilt feature frame (analysis/tilt_study/story_data.py: calibrated expected
score, sessions from the END of the previous game, 60-min session gap, equal-footing +
hygiene filters) and the cached per-game extracts in analysis/out/tilt/:
    flaws.parquet       blunders/mistakes per side from our engine (games with a full eval)
    move_feats.parquet  per-side think-time features (games with clocks)
    acc.parquet         lichess-imported ACPL (user-requested analysis only; selection-biased)

Outcome: residual = score - expected score (pp), user-cluster bootstrap CIs. Selection
handled three ways: (a) marginal curve over all games at position k, (b) "continuers":
games followed by another game in the same session (removes the quit-on-result
selection of the last game), (c) fixed cohort: sessions of >= N games, positions 1..N-1
(same sessions at every position). Plus outcome-free quality metrics (blunder rate,
think time, timeouts) that do not depend on the stopping rule.

Run:  uv run --project analysis python analysis/session_length_study/session_length_study.py
Needs: analysis/out/tilt/{features,flaws,move_feats,acc}.parquet (from the tilt study).
Writes: analysis/out/session_length/*.csv, *.png
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import polars as pl

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "analysis" / "tilt_study"))
from story_data import TC_ORDER, cached_games  # noqa: E402  # ty: ignore[unresolved-import]  (resolved via sys.path.insert above)

TILT_OUT = REPO / "analysis" / "out" / "tilt"
OUT = REPO / "analysis" / "out" / "session_length"
OUT.mkdir(parents=True, exist_ok=True)

SESSION_GAP_MIN = 60  # primary; 30 as sensitivity
MAX_POS = 20  # positions 1..20 shown individually, 21+ pooled
REPS = 300
MIN_CELL_N = 1000  # cells below this are not drawn (still in the CSVs)
SEED = 7
TC_COLOR = {"bullet": "#2a78d6", "blitz": "#eb6834", "rapid": "#1baf7a", "classical": "#eda100"}
ELO_ORDER = [800, 1200, 1600, 2000, 2400]
ELAPSED_EDGES = [0, 15, 30, 45, 60, 90, 120, 180, 240, 10**9]
ELAPSED_LABELS = [
    "0-15",
    "15-30",
    "30-45",
    "45-60",
    "60-90",
    "90-120",
    "120-180",
    "180-240",
    "240+",
]
GAP_EDGES_S = [0, 60, 180, 600, 1800, 3600]
GAP_LABELS = ["<1m", "1-3m", "3-10m", "10-30m", "30-60m"]
COHORT_MIN_LEN = {"bullet": 12, "blitz": 10, "rapid": 6, "classical": 4}
# Positions summarised as "early" (after the warm-up game) vs "late" in the headline table.
EARLY_TO = {"bullet": 5, "blitz": 5, "rapid": 5, "classical": 3}  # early = positions 2..EARLY_TO
LATE_FROM = {"bullet": 13, "blitz": 11, "rapid": 7, "classical": 4}

t0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - t0:5.0f}s] {msg}", flush=True)


# ---------------------------------------------------------------------------------
# bootstrap helpers: one group_by per table, numpy loop over cells
# ---------------------------------------------------------------------------------
def boot_cells(
    df: pl.DataFrame, keys: list[str], col: str, reps: int = REPS, seed: int = SEED
) -> pl.DataFrame:
    """Mean of `col` per cell (keys) with a user-cluster bootstrap 95% CI and n."""
    per_user = (
        df.group_by(keys + ["user_id"])
        .agg(pl.col(col).sum().alias("s"), pl.col(col).count().alias("n"))
        .sort(keys + ["user_id"])
    )
    rows = []
    for cell_key, cell in per_user.group_by(keys, maintain_order=True):
        s = cell["s"].to_numpy().astype(float)
        n = cell["n"].to_numpy().astype(float)
        rng = np.random.default_rng(seed)
        idx = rng.integers(0, len(s), size=(reps, len(s)))
        boots = s[idx].sum(1) / np.maximum(n[idx].sum(1), 1)
        rows.append(
            dict(zip(keys, cell_key, strict=True))
            | {
                "n": int(n.sum()),
                "users": len(s),
                "mean": float(s.sum() / n.sum()),
                "lo": float(np.percentile(boots, 2.5)),
                "hi": float(np.percentile(boots, 97.5)),
            }
        )
    return pl.DataFrame(rows)


def pp(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns((pl.col(c) * 100).round(2) for c in ("mean", "lo", "hi"))


def save(df: pl.DataFrame, name: str) -> pl.DataFrame:
    df.write_csv(OUT / f"{name}.csv")
    log(f"wrote {name}.csv ({df.height} rows)")
    return df


def line_fig(
    df: pl.DataFrame,
    x: str,
    title: str,
    ytitle: str,
    name: str,
    series: str = "tc",
    y0: bool = True,
) -> None:
    fig = go.Figure()
    order = TC_ORDER if series == "tc" else sorted(df[series].unique().to_list())
    for s in order:
        d = df.filter(pl.col(series) == s).sort(x)
        if "n" in d.columns:
            d = d.filter(pl.col("n") >= MIN_CELL_N)  # thin classical tail cells swamp the axis
        if d.height == 0:
            continue
        fig.add_trace(
            go.Scatter(
                x=d[x],
                y=d["mean"],
                name=str(s),
                mode="lines+markers",
                line={"color": TC_COLOR.get(s, None), "width": 2}
                if series == "tc"
                else {"width": 2},
                error_y={
                    "type": "data",
                    "array": d["hi"] - d["mean"],
                    "arrayminus": d["mean"] - d["lo"],
                    "thickness": 1,
                },
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title=x,
        yaxis_title=ytitle,
        template="plotly_white",
        height=440,
        legend={"orientation": "h", "y": -0.25},
    )
    if y0:
        fig.add_hline(y=0, line={"color": "#9a9890", "width": 1})
    fig.write_image(OUT / f"{name}.png", scale=2)


# ---------------------------------------------------------------------------------
# frame
# ---------------------------------------------------------------------------------
g = cached_games()
log(f"features {g.shape}")

W = ["user_id", "tc"]


def add_sessions(df: pl.DataFrame, gap_min: int, prefix: str = "") -> pl.DataFrame:
    """Session index/length from END-of-previous-game gaps (unknown gap = new session)."""
    new = pl.col("gap_before_s").is_null() | (pl.col("gap_before_s") >= gap_min * 60)
    df = df.sort(W + ["played_at"]).with_columns(
        new.cast(pl.Int32).cum_sum().over(W).alias(f"{prefix}sid")
    )
    s = W + [f"{prefix}sid"]
    return df.with_columns(
        (pl.int_range(pl.len()).over(s) + 1).alias(f"{prefix}pos"),
        pl.len().over(s).alias(f"{prefix}len"),
        (pl.col("played_at") - pl.col("played_at").min().over(s))
        .dt.total_minutes()
        .alias(f"{prefix}elapsed"),
        # time at the board so far INCLUDING this game (minutes), from clock durations
        (pl.col("dur_s").fill_null(0).cum_sum().over(s) / 60).alias(f"{prefix}board_min"),
    )


g = add_sessions(g, SESSION_GAP_MIN)
g = add_sessions(g, 30, prefix="s30_")
g = g.with_columns(
    posc=pl.col("pos").clip(upper_bound=MAX_POS + 1),  # 21 = "21+"
    continuer=pl.col("pos") < pl.col("len"),  # another game follows in this session
    last=pl.col("pos") == pl.col("len"),
    elapsed_bin=pl.col("elapsed").cut(ELAPSED_EDGES[1:-1], labels=ELAPSED_LABELS).cast(pl.Utf8),
    gap_bin_s=pl.col("gap_before_s")
    .cut(GAP_EDGES_S[1:], labels=GAP_LABELS + [">60m"])
    .cast(pl.Utf8),
    timeout_loss=(pl.col("termination") == "timeout") & (pl.col("score") == 0),
    win=(pl.col("score") == 1).cast(pl.Float64),
    loss=(pl.col("score") == 0).cast(pl.Float64),
)

# --- cross-TC sittings: all games of a user, any time control -----------------------
sit = (
    g.select("game_id", "user_id", "tc", "played_at", "end_at")
    .sort(["user_id", "played_at"])
    .with_columns(
        sit_gap=(pl.col("played_at") - pl.col("end_at").shift(1)).dt.total_seconds().over("user_id")
    )
    .with_columns(
        (pl.col("sit_gap").is_null() | (pl.col("sit_gap") >= SESSION_GAP_MIN * 60))
        .cast(pl.Int32)
        .cum_sum()
        .over("user_id")
        .alias("sit_id")
    )
    .with_columns(
        sit_pos=pl.int_range(pl.len()).over(["user_id", "sit_id"]) + 1,
        sit_len=pl.len().over(["user_id", "sit_id"]),
        sit_ntc=pl.col("tc").n_unique().over(["user_id", "sit_id"]),
    )
    .select("game_id", "sit_pos", "sit_len", "sit_ntc")
)
g = g.join(sit, on="game_id", how="left").with_columns(
    other_tc_before=pl.col("sit_pos") - pl.col("pos")  # games of OTHER TCs earlier in the sitting
)

# --- quality extracts --------------------------------------------------------------
flaws = pl.read_parquet(TILT_OUT / "flaws.parquet").select(
    "game_id", "w_bl", "b_bl", "w_mi", "b_mi"
)
mv = pl.read_parquet(TILT_OUT / "move_feats.parquet").select(
    "game_id", "side", "n_think", "think_all", "fast1_all", "clk_last"
)
acc = pl.read_parquet(TILT_OUT / "acc.parquet").select("game_id", "w_acpl", "b_acpl", "analyzed")
g = g.join(flaws, on="game_id", how="left").join(acc, on="game_id", how="left")
white = pl.col("user_color") == "white"
g = g.with_columns(
    side=pl.when(white).then(0).otherwise(1),
    my_bl=pl.when(white).then(pl.col("w_bl")).otherwise(pl.col("b_bl")),
    my_mi=pl.when(white).then(pl.col("w_mi")).otherwise(pl.col("b_mi")),
    my_acpl=pl.when(white).then(pl.col("w_acpl")).otherwise(pl.col("b_acpl")),
    my_moves=pl.when(white)
    .then((pl.col("ply_count") + 1) // 2)
    .otherwise(pl.col("ply_count") // 2),
)
g = g.join(mv, on=["game_id", "side"], how="left").with_columns(
    bl100=pl.when(pl.col("my_moves") >= 10).then(pl.col("my_bl") / pl.col("my_moves") * 100),
    mi100=pl.when(pl.col("my_moves") >= 10).then(pl.col("my_mi") / pl.col("my_moves") * 100),
    think_pm=pl.when(pl.col("n_think") >= 10).then(pl.col("think_all") / pl.col("n_think")),
    fast_share=pl.when(pl.col("n_think") >= 10).then(pl.col("fast1_all") / pl.col("n_think")),
    acpl=pl.when(pl.col("analyzed")).then(pl.col("my_acpl").cast(pl.Float64)),
)
# think time relative to the user's own mean in the same format (removes 3+0 vs 5+3 mix)
fmt = W + ["base_s", "inc_s"]
g = g.with_columns(
    think_rel=pl.col("think_pm") / pl.col("think_pm").mean().over(fmt),
    plies_rel=pl.col("ply_count") / pl.col("ply_count").mean().over(fmt),
)

story = g.filter(pl.col("equal_footing") & pl.col("hygiene"))
# The tilt calibration is fitted on IN-SESSION games only, so first-of-session games carry a
# TC-specific offset (classical: 69% of sessions are one game, so its zero point sits on a
# thin, atypical frame). Here every position counts, so centre the residual per TC on the
# whole story frame: the TC's mean over all positions is zero. Shapes are unchanged.
tc_offset = story.group_by("tc").agg(pl.col("resid").mean().alias("offset"))
story = story.join(tc_offset, on="tc").with_columns(
    resid_raw=pl.col("resid"), resid=pl.col("resid") - pl.col("offset")
)
save(tc_offset.with_columns((pl.col("offset") * 100).round(2)), "tbl_tc_offset")
# user-demeaned residual and quality metrics (within-user shape, immune to who plays long sessions)
story = story.with_columns(
    resid_dm=pl.col("resid") - pl.col("resid").mean().over(W),
    bl100_dm=pl.col("bl100") - pl.col("bl100").mean().over(W),
    mi100_dm=pl.col("mi100") - pl.col("mi100").mean().over(W),
    acpl_dm=pl.col("acpl") - pl.col("acpl").mean().over(W),
    fast_dm=pl.col("fast_share") - pl.col("fast_share").mean().over(fmt),
)
log(f"story frame {story.height} games, {story['user_id'].n_unique()} users")

# ---------------------------------------------------------------------------------
# 0. descriptives: how long are sessions?
# ---------------------------------------------------------------------------------
sess = g.group_by(W + ["sid"]).agg(
    pl.len().alias("games"),
    pl.col("elapsed").max().alias("span_min"),
    pl.col("board_min").max().alias("board_min"),
    pl.col("elo_bucket").first(),
)
desc = (
    sess.group_by("tc")
    .agg(
        pl.len().alias("sessions"),
        pl.col("games").mean().round(2).alias("mean_games"),
        pl.col("games").median().alias("p50_games"),
        pl.col("games").quantile(0.75).alias("p75_games"),
        pl.col("games").quantile(0.9).alias("p90_games"),
        (pl.col("games") == 1).mean().round(3).alias("share_single_game"),
        pl.col("board_min").median().round(1).alias("p50_board_min"),
        pl.col("board_min").quantile(0.9).round(1).alias("p90_board_min"),
    )
    .sort(pl.col("tc").cast(pl.Enum(TC_ORDER)))
)
save(desc, "tbl_session_desc")
desc_elo = (
    sess.group_by(["tc", "elo_bucket"])
    .agg(
        pl.len().alias("sessions"),
        pl.col("games").mean().round(2).alias("mean_games"),
        pl.col("games").median().alias("p50_games"),
        pl.col("games").quantile(0.9).alias("p90_games"),
        pl.col("board_min").median().round(1).alias("p50_board_min"),
    )
    .sort(["tc", "elo_bucket"])
)
save(desc_elo, "tbl_session_desc_elo")
# share of GAMES (story frame) played at position k
pos_share = (
    story.group_by(["tc", "posc"])
    .len()
    .with_columns(share=(pl.col("len") / pl.col("len").sum().over("tc") * 100).round(2))
    .sort(["tc", "posc"])
)
save(pos_share, "tbl_pos_share")

# ---------------------------------------------------------------------------------
# 1. residual by game number in the session, three selection treatments
# ---------------------------------------------------------------------------------
curve_all = pp(boot_cells(story, ["tc", "posc"], "resid")).with_columns(
    pl.lit("all").alias("frame")
)
curve_cont = pp(
    boot_cells(story.filter(pl.col("continuer")), ["tc", "posc"], "resid")
).with_columns(pl.lit("continuers").alias("frame"))
curve_last = pp(boot_cells(story.filter(pl.col("last")), ["tc", "posc"], "resid")).with_columns(
    pl.lit("last_game").alias("frame")
)
curve_dm = pp(boot_cells(story, ["tc", "posc"], "resid_dm")).with_columns(
    pl.lit("all_user_demeaned").alias("frame")
)
cohort_parts = []
for tc, n in COHORT_MIN_LEN.items():
    sub = story.filter((pl.col("tc") == tc) & (pl.col("len") >= n) & (pl.col("pos") < n))
    cohort_parts.append(pp(boot_cells(sub, ["tc", "posc"], "resid")))
curve_cohort = pl.concat(cohort_parts).with_columns(pl.lit("cohort_fixed").alias("frame"))
curves = pl.concat([curve_all, curve_cont, curve_last, curve_dm, curve_cohort]).sort(
    ["frame", "tc", "posc"]
)
save(curves, "tbl_curve_position")
line_fig(
    curve_all,
    "posc",
    "Residual by game number in session (all games)",
    "score − expected (pp)",
    "curve_all",
)
line_fig(
    curve_cont,
    "posc",
    "Residual by game number (continuers only)",
    "score − expected (pp)",
    "curve_continuers",
)
line_fig(
    curve_dm, "posc", "User-demeaned residual by game number", "pp vs own mean", "curve_demeaned"
)
line_fig(
    curve_cohort,
    "posc",
    "Fixed cohort: sessions of ≥ N games, positions 1..N−1",
    "score − expected (pp)",
    "curve_cohort",
)

# 30-min session sensitivity (all games)
story30 = story.with_columns(posc=pl.col("s30_pos").clip(upper_bound=MAX_POS + 1))
save(pp(boot_cells(story30, ["tc", "posc"], "resid")), "tbl_curve_position_gap30")


# ---------------------------------------------------------------------------------
# 2. early vs late summary, per TC and per (TC, rating bucket)
# ---------------------------------------------------------------------------------
def phase_col(df: pl.DataFrame) -> pl.DataFrame:
    late = pl.coalesce([pl.when(pl.col("tc") == t).then(pl.lit(v)) for t, v in LATE_FROM.items()])
    early_to = pl.coalesce(
        [pl.when(pl.col("tc") == t).then(pl.lit(v)) for t, v in EARLY_TO.items()]
    )
    return df.with_columns(
        phase=pl.when(pl.col("pos") == 1)
        .then(pl.lit("first"))
        .when(pl.col("pos").is_between(2, early_to))
        .then(pl.lit("early"))
        .when(pl.col("pos") >= late)
        .then(pl.lit("late"))
        .otherwise(pl.lit("mid"))
    )


ph = phase_col(story)
save(pp(boot_cells(ph, ["tc", "phase"], "resid")).sort(["tc", "phase"]), "tbl_phase_tc")
save(
    pp(boot_cells(ph, ["tc", "elo_bucket", "phase"], "resid")).sort(["tc", "elo_bucket", "phase"]),
    "tbl_phase_tc_elo",
)
save(
    pp(boot_cells(ph.filter(pl.col("continuer")), ["tc", "elo_bucket", "phase"], "resid")).sort(
        ["tc", "elo_bucket", "phase"]
    ),
    "tbl_phase_tc_elo_continuers",
)
# per rating bucket position curves (all games), pooled TCs and per TC
save(
    pp(boot_cells(story, ["elo_bucket", "posc"], "resid")).sort(["elo_bucket", "posc"]),
    "tbl_curve_position_elo",
)
curve_tc_elo = pp(boot_cells(story, ["tc", "elo_bucket", "posc"], "resid")).sort(
    ["tc", "elo_bucket", "posc"]
)
save(curve_tc_elo, "tbl_curve_position_tc_elo")
for tc in TC_ORDER:
    line_fig(
        curve_tc_elo.filter(pl.col("tc") == tc).with_columns(pl.col("elo_bucket").cast(pl.Utf8)),
        "posc",
        f"{tc}: residual by game number, per rating bucket",
        "score − expected (pp)",
        f"curve_elo_{tc}",
        series="elo_bucket",
    )

# ---------------------------------------------------------------------------------
# 3. games vs minutes: elapsed time into the session, and the 2-D view
# ---------------------------------------------------------------------------------
save(
    pp(boot_cells(story.filter(pl.col("pos") > 1), ["tc", "elapsed_bin"], "resid"))
    .with_columns(pl.col("elapsed_bin").cast(pl.Enum(ELAPSED_LABELS)))
    .sort(["tc", "elapsed_bin"]),
    "tbl_curve_elapsed",
)
# 2-D: position bins × elapsed bins (does the clock matter at a fixed game count?)
pos_bins = [0, 1, 3, 6, 10, 15, 10**6]
pos_labels = ["1", "2-3", "4-6", "7-10", "11-15", "16+"]
two_d = story.with_columns(
    pos_bin=pl.col("pos").cut(pos_bins[1:-1], labels=pos_labels).cast(pl.Utf8)
)
save(
    pp(boot_cells(two_d, ["tc", "pos_bin", "elapsed_bin"], "resid"))
    .filter(pl.col("n") >= 2000)
    .sort(["tc", "pos_bin", "elapsed_bin"]),
    "tbl_pos_x_elapsed",
)
# board minutes (clock time actually used, excludes pauses) vs wall-clock elapsed
board_edges = [0, 10, 20, 30, 45, 60, 90, 120, 10**9]
board_labels = ["0-10", "10-20", "20-30", "30-45", "45-60", "60-90", "90-120", "120+"]
bm = story.filter(pl.col("has_clock") & (pl.col("pos") > 1)).with_columns(
    board_bin=(pl.col("board_min") - pl.col("dur_s") / 60)
    .cut(board_edges[1:-1], labels=board_labels)
    .cast(pl.Utf8)
)
save(
    pp(boot_cells(bm, ["tc", "board_bin"], "resid"))
    .with_columns(pl.col("board_bin").cast(pl.Enum(board_labels)))
    .sort(["tc", "board_bin"]),
    "tbl_curve_board_minutes",
)

# ---------------------------------------------------------------------------------
# 4. outcome-free quality: blunders, mistakes, think time, timeouts, game length
# ---------------------------------------------------------------------------------
q_rows = []
for col, frame in (
    ("bl100", story.filter(pl.col("bl100").is_not_null())),
    ("mi100", story.filter(pl.col("mi100").is_not_null())),
    ("think_rel", story.filter(pl.col("think_rel").is_not_null())),
    ("fast_share", story.filter(pl.col("fast_share").is_not_null())),
    ("timeout_loss", story.with_columns(pl.col("timeout_loss").cast(pl.Float64))),
    ("plies_rel", story),
    ("acpl", story.filter(pl.col("acpl").is_not_null())),
    ("bl100_dm", story.filter(pl.col("bl100_dm").is_not_null())),
    ("mi100_dm", story.filter(pl.col("mi100_dm").is_not_null())),
    ("acpl_dm", story.filter(pl.col("acpl_dm").is_not_null())),
    ("fast_dm", story.filter(pl.col("fast_dm").is_not_null())),
):
    q_rows.append(boot_cells(frame, ["tc", "posc"], col).with_columns(pl.lit(col).alias("metric")))
quality = pl.concat(q_rows).sort(["metric", "tc", "posc"])
save(quality, "tbl_quality_position")
for col, title, yt in (
    ("bl100", "Blunders per 100 own moves by game number (our engine)", "blunders / 100 moves"),
    ("think_rel", "Think time per move, relative to own format mean", "ratio"),
    ("fast_share", "Share of moves played in ≤ 1 s", "share"),
    ("timeout_loss", "Share of games lost on time", "share"),
):
    line_fig(quality.filter(pl.col("metric") == col), "posc", title, yt, f"quality_{col}", y0=False)
# blunder rate: early vs late per (tc, elo)
save(
    boot_cells(
        ph.filter(pl.col("bl100").is_not_null()), ["tc", "elo_bucket", "phase"], "bl100"
    ).sort(["tc", "elo_bucket", "phase"]),
    "tbl_blunder_phase_tc_elo",
)
save(
    boot_cells(ph.filter(pl.col("bl100").is_not_null()), ["tc", "phase"], "bl100").sort(
        ["tc", "phase"]
    ),
    "tbl_blunder_phase_tc",
)

# ---------------------------------------------------------------------------------
# 5. is the late-session drop tilt or fatigue? position × previous result
# ---------------------------------------------------------------------------------
prev = story.filter(pl.col("pos") > 1).with_columns(
    prev_res=pl.when(pl.col("prev_score") == 1)
    .then(pl.lit("after_win"))
    .when(pl.col("prev_score") == 0)
    .then(pl.lit("after_loss"))
    .otherwise(pl.lit("after_draw")),
    pos_bin=pl.col("pos").cut(pos_bins[1:-1], labels=pos_labels).cast(pl.Utf8),
)
save(
    pp(
        boot_cells(
            prev.filter(pl.col("prev_res") != "after_draw"), ["tc", "prev_res", "pos_bin"], "resid"
        )
    ).sort(["tc", "prev_res", "pos_bin"]),
    "tbl_pos_x_prev_result",
)
# streak × depth: does a 2+ loss streak hurt more late in the session?
ll = story.filter(
    pl.col("in_session") & pl.col("streak_same_session") & pl.col("fresh_opponent")
).with_columns(
    st=pl.when((pl.col("streak_dir") == -1) & (pl.col("streak_len") >= 2))
    .then(pl.lit("LL+"))
    .when((pl.col("streak_dir") == 1) & (pl.col("streak_len") >= 2))
    .then(pl.lit("WW+"))
    .otherwise(pl.lit("other")),
    pos_bin=pl.col("pos").cut(pos_bins[1:-1], labels=pos_labels).cast(pl.Utf8),
)
save(
    pp(boot_cells(ll.filter(pl.col("st") != "other"), ["tc", "st", "pos_bin"], "resid")).sort(
        ["tc", "st", "pos_bin"]
    ),
    "tbl_streak_x_depth",
)

# ---------------------------------------------------------------------------------
# 6. short pauses within a session (Noël: rapid in 2-3 with short breaks)
# ---------------------------------------------------------------------------------
pause = story.filter(
    (pl.col("pos") > 1)
    & pl.col("gap_before_s").is_not_null()
    & (pl.col("gap_before_s") < SESSION_GAP_MIN * 60)
).with_columns(
    depth=pl.when(pl.col("pos") <= 3)
    .then(pl.lit("pos 2-3"))
    .when(pl.col("pos") <= 6)
    .then(pl.lit("pos 4-6"))
    .otherwise(pl.lit("pos 7+"))
)
save(
    pp(boot_cells(pause, ["tc", "gap_bin_s"], "resid"))
    .with_columns(pl.col("gap_bin_s").cast(pl.Enum(GAP_LABELS + [">60m"])))
    .sort(["tc", "gap_bin_s"]),
    "tbl_pause",
)
save(
    pp(boot_cells(pause, ["tc", "depth", "gap_bin_s"], "resid"))
    .with_columns(pl.col("gap_bin_s").cast(pl.Enum(GAP_LABELS + [">60m"])))
    .sort(["tc", "depth", "gap_bin_s"]),
    "tbl_pause_x_depth",
)
# pause after a loss vs after a win, rapid+classical focus but all TCs
pause_res = pause.with_columns(
    prev_res=pl.when(pl.col("prev_score") == 0)
    .then(pl.lit("after_loss"))
    .when(pl.col("prev_score") == 1)
    .then(pl.lit("after_win"))
    .otherwise(pl.lit("after_draw"))
)
save(
    pp(
        boot_cells(
            pause_res.filter(pl.col("prev_res") != "after_draw"),
            ["tc", "prev_res", "gap_bin_s"],
            "resid",
        )
    )
    .with_columns(pl.col("gap_bin_s").cast(pl.Enum(GAP_LABELS + [">60m"])))
    .sort(["tc", "prev_res", "gap_bin_s"]),
    "tbl_pause_x_prev_result",
)

# ---------------------------------------------------------------------------------
# 7. how do people actually stop? hazard of ending the session at position k, by result
# ---------------------------------------------------------------------------------
haz = g.filter(pl.col("next_observed") & pl.col("gap_after_s").is_not_null()).with_columns(
    stop=(pl.col("gap_after_s") >= SESSION_GAP_MIN * 60).cast(pl.Float64),
    res=pl.when(pl.col("score") == 1)
    .then(pl.lit("W"))
    .when(pl.col("score") == 0)
    .then(pl.lit("L"))
    .otherwise(pl.lit("D")),
)
hz = (
    haz.group_by(["tc", "posc", "res"])
    .agg(pl.len().alias("n"), pl.col("stop").mean().round(4).alias("p_stop"))
    .filter(pl.col("res") != "D")
    .pivot(on="res", index=["tc", "posc"], values=["n", "p_stop"])
    .sort(["tc", "posc"])
)
save(hz, "tbl_stop_hazard")
line_fig(
    haz.group_by(["tc", "posc"])
    .agg(pl.col("stop").mean().alias("mean"))
    .with_columns(lo=pl.col("mean"), hi=pl.col("mean"))
    .sort(["tc", "posc"]),
    "posc",
    "P(session ends after game k)",
    "probability",
    "stop_hazard",
    y0=False,
)

# ---------------------------------------------------------------------------------
# 8. whole-session view: mean residual of a session by its length
# ---------------------------------------------------------------------------------
len_bins = [0, 1, 2, 3, 5, 8, 12, 20, 10**6]
len_labels = ["1", "2", "3", "4-5", "6-8", "9-12", "13-20", "21+"]
sl = story.with_columns(len_bin=pl.col("len").cut(len_bins[1:-1], labels=len_labels).cast(pl.Utf8))
save(
    pp(boot_cells(sl, ["tc", "len_bin"], "resid"))
    .with_columns(pl.col("len_bin").cast(pl.Enum(len_labels)))
    .sort(["tc", "len_bin"]),
    "tbl_session_len_resid",
)
save(
    pp(boot_cells(sl.filter(pl.col("continuer")), ["tc", "len_bin"], "resid"))
    .with_columns(pl.col("len_bin").cast(pl.Enum(len_labels)))
    .sort(["tc", "len_bin"]),
    "tbl_session_len_resid_continuers",
)
# per-user habit: users' typical (median) session length vs their overall residual, per TC
habit = (
    story.group_by(W)
    .agg(
        pl.len().alias("games"),
        pl.col("resid").mean().alias("resid"),
        pl.col("bl100").mean().alias("bl100"),
    )
    .join(
        sess.group_by(W).agg(pl.col("games").median().alias("typ_len"), pl.len().alias("sessions")),
        on=W,
    )
    .filter((pl.col("games") >= 100) & (pl.col("sessions") >= 10))
    .with_columns(
        typ_bin=pl.col("typ_len")
        .cut([1, 2, 3, 5, 8, 12], labels=["1", "1-2", "2-3", "3-5", "5-8", "8-12", "12+"])
        .cast(pl.Utf8)
    )
)
save(
    habit.group_by(["tc", "typ_bin"])
    .agg(
        pl.len().alias("users"),
        (pl.col("resid").mean() * 100).round(2).alias("resid_pp"),
        pl.col("bl100").mean().round(3).alias("bl100"),
    )
    .sort(["tc", "typ_bin"]),
    "tbl_user_habit",
)

# ---------------------------------------------------------------------------------
# 9. cross-TC sittings: NOT testable. The benchmark import holds each user's main time
#    control (96% of a user's games are in one TC; 79% of users have a single TC), so a
#    sitting that mixes bullet and blitz is invisible, and a "pause" inside a session may
#    hide a game in a time control that was not imported.
# ---------------------------------------------------------------------------------
# ---------------------------------------------------------------------------------
# 10. a "stop at N" counterfactual bound: what share of a player's games are late, and
#     what would the score be if late games scored like early ones (upper bound: assumes
#     the late games would be replaced by early-quality games, which is not observed)
# ---------------------------------------------------------------------------------
late_share = (
    ph.group_by(["tc", "phase"])
    .len()
    .with_columns(share=(pl.col("len") / pl.col("len").sum().over("tc") * 100).round(2))
    .sort(["tc", "phase"])
)
save(late_share, "tbl_phase_share")

log("done")


# ---------------------------------------------------------------------------------
# 11. early vs late, joint user bootstrap of the DIFFERENCE, per TC and per (TC, rating)
# ---------------------------------------------------------------------------------
def boot_diff_cells(
    df: pl.DataFrame, keys: list[str], col: str, a: str = "late", b: str = "early", reps: int = REPS
) -> pl.DataFrame:
    """(mean in phase a) - (mean in phase b) per cell, users resampled jointly across phases."""
    per_user = (
        df.filter(pl.col("phase").is_in([a, b]))
        .group_by(keys + ["user_id", "phase"])
        .agg(pl.col(col).sum().alias("s"), pl.col(col).count().alias("n"))
        .pivot(on="phase", index=keys + ["user_id"], values=["s", "n"])
        .fill_null(0)
        .sort(keys + ["user_id"])
    )
    rows = []
    for cell_key, cell in per_user.group_by(keys, maintain_order=True):
        sa, na = cell[f"s_{a}"].to_numpy().astype(float), cell[f"n_{a}"].to_numpy().astype(float)
        sb, nb = cell[f"s_{b}"].to_numpy().astype(float), cell[f"n_{b}"].to_numpy().astype(float)
        if na.sum() == 0 or nb.sum() == 0:
            continue
        rng = np.random.default_rng(SEED)
        idx = rng.integers(0, len(sa), size=(reps, len(sa)))
        d = sa[idx].sum(1) / np.maximum(na[idx].sum(1), 1) - sb[idx].sum(1) / np.maximum(
            nb[idx].sum(1), 1
        )
        rows.append(
            dict(zip(keys, cell_key, strict=True))
            | {
                f"n_{a}": int(na.sum()),
                f"n_{b}": int(nb.sum()),
                f"mean_{b}": float(sb.sum() / nb.sum()),
                f"mean_{a}": float(sa.sum() / na.sum()),
                "diff": float(sa.sum() / na.sum() - sb.sum() / nb.sum()),
                "lo": float(np.percentile(d, 2.5)),
                "hi": float(np.percentile(d, 97.5)),
            }
        )
    return pl.DataFrame(rows)


diffs = []
for col, scale in (
    ("resid", 100),
    ("resid_dm", 100),
    ("bl100", 1),
    ("bl100_dm", 1),
    ("think_rel", 100),
    ("fast_dm", 100),
    ("acpl_dm", 1),
):
    frame = ph.filter(pl.col(col).is_not_null())
    for keys in (["tc"], ["tc", "elo_bucket"]):
        d = boot_diff_cells(frame, keys, col).with_columns(
            pl.lit(col).alias("metric"),
            *[
                (pl.col(c) * scale).round(3)
                for c in ("mean_early", "mean_late", "diff", "lo", "hi")
            ],
        )
        if "elo_bucket" not in keys:
            d = d.with_columns(pl.lit(None, dtype=pl.Int64).alias("elo_bucket"))
        diffs.append(
            d.select(
                "metric",
                "tc",
                "elo_bucket",
                "n_early",
                "n_late",
                "mean_early",
                "mean_late",
                "diff",
                "lo",
                "hi",
            )
        )
save(
    pl.concat(diffs).sort(["metric", "tc", "elo_bucket"], nulls_last=False), "tbl_late_minus_early"
)

# ---------------------------------------------------------------------------------
# 12. do marathon sessions start with a loss? P(session reaches N | first game result)
# ---------------------------------------------------------------------------------
first = (
    g.filter(pl.col("pos") == 1)
    .with_columns(
        res=pl.when(pl.col("score") == 1)
        .then(pl.lit("W"))
        .when(pl.col("score") == 0)
        .then(pl.lit("L"))
        .otherwise(pl.lit("D")),
        long=pl.coalesce(
            [pl.when(pl.col("tc") == t).then(pl.col("len") >= v) for t, v in COHORT_MIN_LEN.items()]
        ).cast(pl.Float64),
        ge3=(pl.col("len") >= 3).cast(pl.Float64),
    )
    .filter(pl.col("res") != "D")
)
first = first.with_columns(
    long_dm=pl.col("long") - pl.col("long").mean().over(W),
    ge3_dm=pl.col("ge3") - pl.col("ge3").mean().over(W),
)
mara = []
for col in ("long", "ge3", "long_dm", "ge3_dm"):
    mara.append(pp(boot_cells(first, ["tc", "res"], col)).with_columns(pl.lit(col).alias("metric")))
save(pl.concat(mara).sort(["metric", "tc", "res"]), "tbl_marathon_start")

log("done (part 2)")
