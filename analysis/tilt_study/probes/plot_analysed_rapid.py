"""Rapid: share of streak-ending games with lichess analysis, by the streak the game completes.

Same frame as gen_story.py section 6g (hygiene, run within one session), rapid only, with a
user-bootstrap 95% interval. Writes analysis/out/tilt/analysed_rapid.png (raw rate) and
analysed_rapid_controlled.png (within-user rate at equal session depth, see report section 6a).

Run: uv run --project analysis python analysis/tilt_study/probes/plot_analysed_rapid.py
"""

import sys
from pathlib import Path

import plotly.graph_objects as go
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from story_data import OUT, USER_W, boot_mean  # noqa: E402

MAX_K = 6
DEEP_SESSION_IDX = (6, 15)  # same as gen_story.py
REPS = 500
LOSS = "#C0392B"
WIN = "#2E8B57"
DRAW = "#8A7F71"
INK = "#2b2723"
INK_2 = "#4a4540"
GRID = "#e8e3da"
ZERO = "#9a9890"

g = pl.read_parquet(OUT / "features.parquet").filter(pl.col("hygiene") & (pl.col("tc") == "rapid"))
an = (
    g.join(pl.read_parquet(OUT / "acc.parquet").select("game_id", "analyzed"), on="game_id")
    .with_columns(a=pl.col("analyzed").cast(pl.Float64))
    # user-demeaned flag: removes who reaches long streaks (rating, volume)
    .with_columns(a_dm=pl.col("a") - pl.col("a").mean().over(USER_W))
    .filter(pl.col("run_start_session") == pl.col("session_id"))
    .with_columns(xo=(pl.col("dir") * pl.col("run_len").clip(upper_bound=MAX_K)).cast(pl.Int32))
)
# equal session depth: a k-streak game sits >= k games into its session, and the analysis rate
# falls with session length whatever the result
an_deep = an.filter(pl.col("session_idx").is_between(*DEEP_SESSION_IDX))


def by_streak(df: pl.DataFrame, col: str) -> pl.DataFrame:
    rows = []
    for x in range(-MAX_K, MAX_K + 1):
        c = df.filter(pl.col("xo") == x)
        m, lo, hi = boot_mean(c, col, reps=REPS)
        rows.append({"x": x, "n": c.height, "pct": m * 100, "lo": lo * 100, "hi": hi * 100})
    return pl.DataFrame(rows)


def label(x: int) -> str:
    if x == 0:
        return "draw"
    k = abs(x)
    return f"{k}{'+' if k == MAX_K else ''} {'L' if x < 0 else 'W'}"


def bar_chart(d: pl.DataFrame, title: str, ytitle: str, yrange: list[float], out: str) -> None:
    signed = yrange[0] < 0
    fig = go.Figure(
        go.Bar(
            x=[label(x) for x in d["x"]],
            y=d["pct"],
            marker={"color": [LOSS if x < 0 else DRAW if x == 0 else WIN for x in d["x"]]},
            error_y={
                "type": "data",
                "array": (d["hi"] - d["pct"]).to_list(),
                "arrayminus": (d["pct"] - d["lo"]).to_list(),
                "thickness": 1.2,
                "color": INK_2,
            },
            text=None if signed else [f"{v:.1f}" for v in d["pct"]],
            textposition="inside",
            insidetextanchor="start",
            textfont={"size": 12, "color": "#ffffff"},
            cliponaxis=False,
        )
    )
    if signed:
        # value labels just past the far end of the interval, clear of the error bar
        for x, v, lo, hi in zip(d["x"], d["pct"], d["lo"], d["hi"], strict=True):
            fig.add_annotation(
                x=label(x),
                y=hi if v >= 0 else lo,
                text=f"{v:+.1f}",
                showarrow=False,
                yshift=12 if v >= 0 else -12,
                font={"size": 12, "color": INK_2},
            )
    fig.update_layout(
        title=title,
        xaxis_title="streak completed by this game (L = losses, W = wins)",
        yaxis_title=ytitle,
        yaxis={"range": yrange, "gridcolor": GRID, "zerolinecolor": ZERO, "zerolinewidth": 1},
        template="plotly_white",
        height=440,
        width=860,
        margin={"t": 60, "b": 60},
        showlegend=False,
        font={"color": INK},
    )
    fig.write_image(OUT / out, scale=2)
    print("wrote", OUT / out)


d = by_streak(an, "a")
d_ctrl = by_streak(an_deep, "a_dm")
print(d)
print(d_ctrl)
bar_chart(
    d,
    "Rapid: share of games with Lichess analysis, by the streak the game completes",
    "games analysed (%)",
    [0, 45],
    "analysed_rapid.png",
)
bar_chart(
    d_ctrl,
    "Rapid, controlled: analysis rate vs the player's own rate, session games 6–15 only",
    "vs player's own analysis rate (percentage points)",
    [-10, 7],
    "analysed_rapid_controlled.png",
)
