"""Generate every table the tilt data story (stories/tilt/) cites.

Reads the cached extracts in analysis/out/tilt/ (see story_data.py), writes one CSV per
table to analysis/out/tilt/story/ and a combined markdown dump (tables.md) that the
technical report is assembled from.

Run: uv run --project analysis python analysis/tilt_study/gen_story.py
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
from story_data import (  # noqa: E402
    ELO_ANCHORS,
    MAX_STREAK,
    OUT,
    TC_ORDER,
    USER_W,
    boot_diff,
    boot_mean,
    load_games,
    streak_label,
)

STORY = OUT / "story"
STORY.mkdir(parents=True, exist_ok=True)
REPS_HEAD = 1000
REPS = 300
XS = list(range(-MAX_STREAK, MAX_STREAK + 1))
# story axis pools 6+ (the exact-7 and 7+ cells are thin once the streak must sit in one session)
XS6 = list(range(-6, 7))
GAP_EDGES_S = [0, 60, 180, 600, 1800, 3600, 6 * 3600, 24 * 3600, 7 * 86400, 10**9]
GAP_LABELS = [
    "<1 min",
    "1-3 min",
    "3-10 min",
    "10-30 min",
    "30-60 min",
    "1-6 h",
    "6-24 h",
    "1-7 d",
    ">7 d",
]
SHORT_PLIES = 20
LONG_PLIES = 60
ENDGAME_LEAD_CP = 200
MIN_THINK_MOVES = 10
MIN_PAIRED_GAMES = 20
FAST_TC = ["bullet", "blitz", "rapid"]
DEEP_SESSION_IDX = (6, 15)  # session games used for the depth-controlled analysis rate
md: list[str] = []


def emit(title: str, df: pl.DataFrame, name: str) -> None:
    df.write_csv(STORY / f"{name}.csv")
    md.append(f"\n### {title}\n\n`{name}.csv`\n")
    cols = df.columns
    md.append("| " + " | ".join(cols) + " |")
    md.append("|" + "---|" * len(cols))
    for row in df.iter_rows():
        md.append(
            "| "
            + " | ".join(
                "" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v)) for v in row
            )
            + " |"
        )
    print(f"\n=== {title} ===")
    print(df)


def fmean(s: pl.Series) -> float:
    """Mean of a numeric Series as a float (polars types mean() as a wide literal union)."""
    v = s.mean()
    return float(v) if isinstance(v, (int, float)) else float("nan")


def fstd(s: pl.Series) -> float:
    v = s.std()
    return float(v) if isinstance(v, (int, float)) else float("nan")


def fmedian(s: pl.Series) -> float:
    v = s.median()
    return float(v) if isinstance(v, (int, float)) else float("nan")


def pct(v: float | None) -> float | None:
    return None if v is None or v != v else round(v * 100, 3)


def mean_pct(c: pl.DataFrame, col: str) -> float | None:
    return pct(fmean(c[col])) if c.height else None


def cell(df: pl.DataFrame, col: str, reps: int = REPS) -> dict:
    m, lo, hi = boot_mean(df, col, reps=reps)
    return {"n": df.height, col: pct(m), f"{col}_lo": pct(lo), f"{col}_hi": pct(hi)}


def curve(
    df: pl.DataFrame, xs: list[int], reps: int = REPS, key: str | None = None, keys=None
) -> pl.DataFrame:
    """Next-game raw score, expected score and residual per signed streak length."""
    rows = []
    xmax = max(xs)
    d = df.with_columns(xc=pl.col("x").clip(-xmax, xmax))
    for k in keys or [None]:
        dk = d if key is None else d.filter(pl.col(key) == k)
        for x in xs:
            c = dk.filter(pl.col("xc") == x)
            r = {"x": x} if key is None else {key: k, "x": x}
            r.update(cell(c, "score", reps))
            r["expected"] = mean_pct(c, "exp_score")
            r.update({k2: v for k2, v in cell(c, "resid", reps).items() if k2 != "n"})
            rows.append(r)
    return pl.DataFrame(rows)


t0 = time.time()
cache = OUT / "features.parquet"
g = pl.read_parquet(cache) if cache.exists() else load_games()
if not cache.exists():
    g.write_parquet(cache)
g = g.with_columns(streak=streak_label())
print("features", g.shape, f"{time.time() - t0:.0f}s")

# ---- population ---------------------------------------------------------------
scored = g.filter(pl.col("equal_footing"))
story = scored.filter(pl.col("hygiene"))  # the frame every story number is scored on
after = story.filter(
    pl.col("in_session") & pl.col("streak_same_session") & pl.col("streak_dir").is_not_null()
)
pop = {
    "games_total": g.height,
    "users": g["user_id"].n_unique(),
    "games_scored_equal_footing": scored.height,
    "games_scored_story_hygiene": story.height,
    "games_after_same_session_streak": after.height,
    "share_with_clock_duration": pct(fmean(g["has_clock"])),
    "first_game_at": str(g["played_at"].min()),
    "last_game_at": str(g["played_at"].max()),
}
for tc in TC_ORDER:
    pop[f"after_streak_{tc}"] = after.filter(pl.col("tc") == tc).height
(STORY / "population.json").write_text(json.dumps(pop, indent=2))
md.append("## Population\n\n```json\n" + json.dumps(pop, indent=2) + "\n```")
print(pop)

# ---- 1. control ladder --------------------------------------------------------
base = g.filter(pl.col("streak_dir").is_not_null())
L0 = base
L1 = base.filter(pl.col("equal_footing"))
L2 = L1.filter(pl.col("in_session") & pl.col("streak_same_session"))
L3 = L2.filter(pl.col("hygiene"))
lad = (
    curve(L0, XS)
    .select("x", pl.col("n").alias("n_any"), pl.col("score").alias("any_opponent"))
    .join(curve(L1, XS).select("x", pl.col("score").alias("equal_footing")), on="x")
    .join(curve(L2, XS).select("x", pl.col("score").alias("same_session")), on="x")
    .join(
        curve(L3, XS, REPS_HEAD).select(
            "x",
            pl.col("n").alias("n_controlled"),
            pl.col("score").alias("controlled"),
            "score_lo",
            "score_hi",
            "expected",
            "resid",
            "resid_lo",
            "resid_hi",
        ),
        on="x",
    )
)
emit(
    "1. Control ladder: next-game score (%) by streak just ended, -7 = 7+ losses ... +7 = 7+ wins",
    lad,
    "ladder",
)
lad6 = (
    curve(L0, XS6)
    .select("x", pl.col("n").alias("n_any"), pl.col("score").alias("any_opponent"))
    .join(curve(L1, XS6).select("x", pl.col("score").alias("equal_footing")), on="x")
    .join(curve(L2, XS6).select("x", pl.col("score").alias("same_session")), on="x")
    .join(
        curve(L3, XS6, REPS_HEAD).select(
            "x",
            pl.col("n").alias("n_controlled"),
            pl.col("score").alias("controlled"),
            "score_lo",
            "score_hi",
            "expected",
            "resid",
            "resid_lo",
            "resid_hi",
        ),
        on="x",
    )
)
emit("1a. Control ladder, story axis: -6 = 6+ losses ... +6 = 6+ wins", lad6, "ladder6")
diag = (
    base.group_by("x")
    .agg(
        pl.len().alias("n"),
        (pl.col("my_r") - pl.col("opp_r")).mean().round(1).alias("mean_rating_gap_next_game"),
        pl.col("equal_footing").mean().round(3).alias("share_equal_footing"),
        (pl.col("user_color") == "white").mean().round(3).alias("share_white"),
        pl.col("r_dev").mean().round(1).alias("rating_minus_long_run_median"),
        pl.col("in_session").mean().round(3).alias("share_next_game_in_session"),
        pl.col("streak_same_session").mean().round(3).alias("share_streak_in_one_session"),
        (pl.col("hist_idx") < 100).mean().round(3).alias("share_in_first_100_games"),
    )
    .sort("x")
)
emit(
    "1b. Why the raw curve is steep: matchmaking and account state by streak",
    diag,
    "ladder_diagnostics",
)

# ---- 2. the controlled streak curve (hero) -----------------------------------------
hero = curve(L3, XS6, REPS_HEAD)
emit("2. Controlled streak curve, pooled, -6 = 6+ losses ... +6 = 6+ wins", hero, "streak_curve")
emit(
    "2b. Controlled streak curve by time control",
    curve(L3, XS6, REPS, "tc", TC_ORDER),
    "streak_curve_tc",
)
emit(
    "2c. Controlled streak curve by rating",
    curve(L3, XS6, REPS, "elo_bucket", list(ELO_ANCHORS)),
    "streak_curve_elo",
)
# colour check: residual against a colour-blind calibration
cc = curve(L3.with_columns(resid=pl.col("resid_nocolour")), XS6, 100).select(
    "x", pl.col("resid").alias("resid_nocolour")
)
emit(
    "2d. Colour check: residual with a colour-blind expectation",
    hero.select("x", "resid").join(cc, on="x"),
    "streak_curve_colour_check",
)

# form control: 20-game trailing residual ending 4 games before, terciles
w = USER_W
fc = (
    story.sort(w + ["played_at"])
    .with_columns(
        form=pl.col("resid").shift(4).rolling_mean(window_size=20, min_samples=20).over(w)
    )
    .filter(pl.col("form").is_not_null() & pl.col("in_session") & pl.col("streak_same_session"))
)
q1, q2 = fc["form"].quantile(1 / 3), fc["form"].quantile(2 / 3)
fc = fc.with_columns(
    tercile=pl.when(pl.col("form") < q1)
    .then(pl.lit("cold form"))
    .when(pl.col("form") < q2)
    .then(pl.lit("mid form"))
    .otherwise(pl.lit("hot form"))
)
rows = []
for t in ["cold form", "mid form", "hot form"]:
    r = {
        "form_tercile": t,
        "mean_form_pp": pct(fmean(fc.filter(pl.col("tercile") == t)["form"])),
    }
    for s in ["LLL+", "L", "W", "WWW+"]:
        c = fc.filter((pl.col("tercile") == t) & (pl.col("streak") == s))
        r[s] = pct(boot_mean(c, "resid", reps=100)[0])
        r[f"{s}_n"] = c.height
    rows.append(r)
emit(
    "2e. Form control: residual after streak inside trailing-20-game form terciles",
    pl.DataFrame(rows),
    "form_control",
)
# player fixed effects: demean residual within user x TC (over all scored games)
um = scored.group_by(w).agg(pl.col("resid").mean().alias("user_mean_resid"))
fe = L3.join(um, on=w).with_columns(resid_fe=pl.col("resid") - pl.col("user_mean_resid"))
rows = []
for x in XS6:
    c = fe.with_columns(xc=pl.col("x").clip(-6, 6)).filter(pl.col("xc") == x)
    m, lo, hi = boot_mean(c, "resid_fe", reps=REPS)
    rows.append(
        {
            "x": x,
            "n": c.height,
            "resid": pct(boot_mean(c, "resid", reps=50)[0]),
            "resid_player_fe": pct(m),
            "lo": pct(lo),
            "hi": pct(hi),
            "mean_player_fe": mean_pct(c, "user_mean_resid"),
        }
    )
emit(
    "2f. Player fixed effects: residual demeaned within player",
    pl.DataFrame(rows),
    "streak_curve_player_fe",
)


# ---- 3. who tilts: 3+ streaks by rating and TC ----------------------------------
def streak_bars(df: pl.DataFrame, key: str, keys: list) -> pl.DataFrame:
    rows = []
    for k in keys:
        d = df.filter(pl.col(key) == k)
        r = {key: k}
        for lab, cond in [
            ("cold", (pl.col("streak_dir") == -1) & (pl.col("streak_len") >= 3)),
            ("hot", (pl.col("streak_dir") == 1) & (pl.col("streak_len") >= 3)),
        ]:
            c = d.filter(cond)
            m, lo, hi = boot_mean(c, "resid", reps=REPS)
            r.update(
                {
                    f"{lab}_n": c.height,
                    f"{lab}_score": mean_pct(c, "score"),
                    f"{lab}_expected": mean_pct(c, "exp_score"),
                    f"{lab}_resid": pct(m),
                    f"{lab}_lo": pct(lo),
                    f"{lab}_hi": pct(hi),
                }
            )
        rows.append(r)
    return pl.DataFrame(rows)


emit(
    "3. After 3+ losses vs 3+ wins, by rating (residual pp)",
    streak_bars(after, "elo_bucket", list(ELO_ANCHORS)),
    "streak3_by_rating",
)
emit(
    "3b. After 3+ losses vs 3+ wins, by time control",
    streak_bars(after, "tc", TC_ORDER),
    "streak3_by_tc",
)
emit(
    "3c. After 3+ losses vs 3+ wins, rating x time control",
    streak_bars(
        after.with_columns(cellk=pl.col("tc") + "-" + pl.col("elo_bucket").cast(pl.Utf8)),
        "cellk",
        [f"{tc}-{e}" for tc in TC_ORDER for e in ELO_ANCHORS],
    ),
    "streak3_by_cell",
)

# ---- 4. does a break help? -------------------------------------------------------
brk = story.filter(
    pl.col("streak_same_session")
    & (pl.col("streak_len") >= 2)
    & (pl.col("streak_dir") != 0)
    & pl.col("gap_before_s").is_not_null()
)
brk = brk.with_columns(gap_bucket=pl.col("gap_before_s").cut(GAP_EDGES_S[1:-1], labels=GAP_LABELS))
rows = []
for tc in TC_ORDER + ["all"]:
    d = brk if tc == "all" else brk.filter(pl.col("tc") == tc)
    for gb in GAP_LABELS:
        r = {"tc": tc, "break": gb}
        for lab, dirn in [("cold", -1), ("hot", 1)]:
            c = d.filter((pl.col("gap_bucket") == gb) & (pl.col("streak_dir") == dirn))
            m, lo, hi = boot_mean(c, "resid", reps=REPS)
            r.update(
                {
                    f"{lab}_n": c.height,
                    f"{lab}_score": mean_pct(c, "score") if c.height else None,
                    f"{lab}_resid": pct(m),
                    f"{lab}_lo": pct(lo),
                    f"{lab}_hi": pct(hi),
                }
            )
        cold = d.filter((pl.col("gap_bucket") == gb) & (pl.col("streak_dir") == -1))
        hot = d.filter((pl.col("gap_bucket") == gb) & (pl.col("streak_dir") == 1))
        gm, glo, ghi = boot_diff(hot, cold, "resid", reps=REPS)
        r.update({"gap_hot_minus_cold": pct(gm), "gap_lo": pct(glo), "gap_hi": pct(ghi)})
        rows.append(r)
emit(
    "4. Break test: residual after 2+ losses (cold) / 2+ wins (hot) by break before the next game",
    pl.DataFrame(rows),
    "break_test",
)
# who takes a break: share of post-streak next games by break bucket
emit(
    "4b. Break taken after 2+ losses vs 2+ wins (share of next games, %)",
    brk.group_by(["tc", "streak_dir", "gap_bucket"])
    .agg(pl.len().alias("n"))
    .with_columns(share=(pl.col("n") / pl.col("n").sum().over(["tc", "streak_dir"]) * 100).round(1))
    .sort(["tc", "streak_dir", "gap_bucket"]),
    "break_shares",
)
# stop-after-two-losses counterfactual
rows = []
for tc in TC_ORDER + ["all"]:
    d = story if tc == "all" else story.filter(pl.col("tc") == tc)
    a = d.filter(
        pl.col("in_session")
        & pl.col("streak_same_session")
        & (pl.col("streak_dir") == -1)
        & (pl.col("streak_len") >= 2)
    )
    m, lo, hi = boot_mean(a, "resid", reps=REPS)
    share = a.height / d.height
    rows.append(
        {
            "tc": tc,
            "games_after_LL_in_session": a.height,
            "share_of_games": pct(share),
            "resid_pp": pct(m),
            "lo": pct(lo),
            "hi": pct(hi),
            "score_pts_saved_per_100_games": round(share * m * 100, 3),
            "extra_losses_per_100_games": round(share * m * 100, 3),
        }
    )
emit("4c. Stop-after-two-losses counterfactual", pl.DataFrame(rows), "stop_rule")
# warm-up and fatigue
rows = []
el_edges = [0, 30, 60, 120, 240, 10**9]
el_labels = ["0-30 min", "30-60 min", "60-120 min", "2-4 h", ">4 h"]
st = story.with_columns(elapsed=pl.col("session_elapsed_min").cut(el_edges[1:-1], labels=el_labels))
for tc in TC_ORDER:
    d = st.filter(pl.col("tc") == tc)
    r = {"tc": tc}
    c = d.filter(pl.col("session_idx") == 1)
    m, lo, hi = boot_mean(c, "resid", reps=REPS)
    r.update(
        {
            "first_game_n": c.height,
            "first_game_resid": pct(m),
            "first_lo": pct(lo),
            "first_hi": pct(hi),
        }
    )
    for lab in el_labels:
        c = d.filter((pl.col("session_idx") > 1) & (pl.col("elapsed") == lab))
        r[lab] = pct(boot_mean(c, "resid", reps=100)[0])
        r[f"{lab}_n"] = c.height
    rows.append(r)
emit(
    "4d. Warm-up and fatigue: residual for the first game of a session and by time into the session",
    pl.DataFrame(rows),
    "fatigue",
)

# ---- 5. which loss tilts you ----------------------------------------------------
eg = pl.read_parquet(OUT / "endgame_entry.parquet")
pl_ = story.join(
    eg.rename({"game_id": "prev_game_id", "eg_cp": "prev_eg_cp", "eg_ply": "prev_eg_ply"}),
    on="prev_game_id",
    how="left",
)
pl_ = pl_.join(
    g.select(pl.col("game_id").alias("prev_game_id"), pl.col("user_color").alias("prev_color")),
    on="prev_game_id",
    how="left",
)
pl_ = pl_.with_columns(
    prev_eg_my=pl.when(pl.col("prev_color") == "white")
    .then(pl.col("prev_eg_cp"))
    .otherwise(-pl.col("prev_eg_cp")),
)
anat = pl_.filter(pl.col("in_session") & (pl.col("prev_score") == 0)).with_columns(
    length=pl.when(pl.col("prev_ply") <= SHORT_PLIES)
    .then(pl.lit("short (<=20 plies)"))
    .when(pl.col("prev_ply") <= LONG_PLIES)
    .then(pl.lit("mid (21-60 plies)"))
    .otherwise(pl.lit("long (>60 plies)")),
    endgame=pl.when(pl.col("prev_eg_my").is_null())
    .then(pl.lit("never reached an endgame"))
    .when(pl.col("prev_eg_my") >= ENDGAME_LEAD_CP)
    .then(pl.lit("blown: entered the endgame winning (>= +2)"))
    .when(pl.col("prev_eg_my") <= -ENDGAME_LEAD_CP)
    .then(pl.lit("entered the endgame losing (<= -2)"))
    .otherwise(pl.lit("entered the endgame balanced")),
    how=pl.when(pl.col("prev_termination") == "abandoned")
    .then(pl.lit("abandoned (disconnect)"))
    .when(pl.col("prev_termination") == "timeout")
    .then(pl.lit("on time"))
    .when(pl.col("prev_termination") == "resignation")
    .then(pl.lit("resigned"))
    .when(pl.col("prev_termination") == "checkmate")
    .then(pl.lit("checkmated"))
    .otherwise(pl.lit("other")),
)
print(
    "prev termination values:",
    anat["prev_termination"].value_counts().sort("count", descending=True),
)


def anatomy(df: pl.DataFrame, col: str, cats: list[str], name: str, title: str) -> None:
    rows = []
    for cat in cats:
        r = {"previous loss": cat}
        for tc in TC_ORDER + ["all"]:
            c = (
                df.filter(pl.col(col) == cat)
                if tc == "all"
                else df.filter((pl.col(col) == cat) & (pl.col("tc") == tc))
            )
            m, lo, hi = boot_mean(c, "resid", reps=REPS)
            r.update(
                {
                    f"{tc}_n": c.height,
                    f"{tc}_resid": pct(m),
                    f"{tc}_lo": pct(lo),
                    f"{tc}_hi": pct(hi),
                }
            )
        rows.append(r)
    emit(title, pl.DataFrame(rows), name)


anatomy(
    anat,
    "how",
    ["checkmated", "resigned", "on time", "abandoned (disconnect)"],
    "loss_by_termination",
    "5. Next-game residual after a loss, by how the loss ended",
)
anatomy(
    anat,
    "length",
    ["short (<=20 plies)", "mid (21-60 plies)", "long (>60 plies)"],
    "loss_by_length",
    "5b. ... by length of the lost game",
)
anatomy(
    anat,
    "endgame",
    [
        "never reached an endgame",
        "entered the endgame losing (<= -2)",
        "entered the endgame balanced",
        "blown: entered the endgame winning (>= +2)",
    ],
    "loss_by_endgame",
    "5c. ... by the position when the lost game entered its endgame",
)
# single-loss variant (streak_len == 1) to show the cut is not streak length in disguise
anatomy(
    anat.filter(pl.col("streak_len") == 1),
    "length",
    ["short (<=20 plies)", "mid (21-60 plies)", "long (>60 plies)"],
    "loss_by_length_single",
    "5d. Length cut, single losses only",
)
anatomy(
    anat.filter(pl.col("streak_len") == 1),
    "endgame",
    [
        "never reached an endgame",
        "entered the endgame losing (<= -2)",
        "entered the endgame balanced",
        "blown: entered the endgame winning (>= +2)",
    ],
    "loss_by_endgame_single",
    "5e. Endgame cut, single losses only",
)
# blown wins by how the blown game ended (most are flags), and the endgame cut inside long
# losses only, so the endgame state is not length in disguise
anatomy(
    anat.filter(pl.col("endgame") == "blown: entered the endgame winning (>= +2)"),
    "how",
    ["on time", "resigned", "checkmated"],
    "loss_blown_by_termination",
    "5e2. Blown wins (entered the endgame >= +2 and lost), by how the blown game ended",
)
anatomy(
    anat.filter(pl.col("length") == "long (>60 plies)"),
    "endgame",
    [
        "never reached an endgame",
        "entered the endgame losing (<= -2)",
        "entered the endgame balanced",
        "blown: entered the endgame winning (>= +2)",
    ],
    "loss_by_endgame_long",
    "5e3. Endgame cut, long losses (> 60 plies) only",
)
# mirror for wins
wins = pl_.filter(pl.col("in_session") & (pl.col("prev_score") == 1)).with_columns(
    endgame=pl.when(pl.col("prev_eg_my").is_null())
    .then(pl.lit("never reached an endgame"))
    .when(pl.col("prev_eg_my") >= ENDGAME_LEAD_CP)
    .then(pl.lit("entered the endgame winning (>= +2)"))
    .when(pl.col("prev_eg_my") <= -ENDGAME_LEAD_CP)
    .then(pl.lit("comeback: entered the endgame losing (<= -2)"))
    .otherwise(pl.lit("entered the endgame balanced")),
    length=pl.when(pl.col("prev_ply") <= SHORT_PLIES)
    .then(pl.lit("short (<=20 plies)"))
    .when(pl.col("prev_ply") <= LONG_PLIES)
    .then(pl.lit("mid (21-60 plies)"))
    .otherwise(pl.lit("long (>60 plies)")),
)
anatomy(
    wins,
    "endgame",
    [
        "never reached an endgame",
        "comeback: entered the endgame losing (<= -2)",
        "entered the endgame balanced",
        "entered the endgame winning (>= +2)",
    ],
    "win_by_endgame",
    "5f. Mirror: next-game residual after a WIN, by endgame state",
)
anatomy(
    wins,
    "length",
    ["short (<=20 plies)", "mid (21-60 plies)", "long (>60 plies)"],
    "win_by_length",
    "5g. Mirror: after a win, by length",
)
# shape of the next loss after a streak
ls = (
    after.filter(pl.col("score") == 0)
    .with_columns(
        grp=pl.when(pl.col("streak") == "LLL+")
        .then(pl.lit("after 3+ losses"))
        .when(pl.col("streak") == "WWW+")
        .then(pl.lit("after 3+ wins"))
        .otherwise(None)
    )
    .filter(pl.col("grp").is_not_null())
)
emit(
    "5h. Shape of the next loss: after 3+ losses vs after 3+ wins",
    ls.group_by(["tc", "grp"])
    .agg(
        pl.len().alias("n"),
        (pl.col("ply_count") <= SHORT_PLIES).mean().mul(100).round(1).alias("short_loss_pct"),
        (pl.col("termination") == "abandoned").mean().mul(100).round(2).alias("abandoned_pct"),
        (pl.col("termination") == "resignation").mean().mul(100).round(1).alias("resigned_pct"),
        (pl.col("termination") == "timeout").mean().mul(100).round(1).alias("flagged_pct"),
        pl.col("ply_count").mean().round(1).alias("mean_plies"),
    )
    .sort(["tc", "grp"]),
    "next_loss_shape",
)

# ---- 6. behaviour: quit, rush, revenge, speed, blunders ------------------------------
beh = g.filter(pl.col("hygiene"))  # behaviour uses every game (no equal-footing needed for a rate)
rows = []
for tc in TC_ORDER:
    d = beh.filter(pl.col("tc") == tc)
    r = {"tc": tc}
    for lab, sc in [("loss", 0.0), ("win", 1.0)]:
        c = d.filter(pl.col("score") == sc)
        m, lo, hi = boot_mean(
            c.with_columns(q=pl.col("last_of_session").cast(pl.Float64)), "q", reps=REPS
        )
        r.update(
            {
                f"quit_after_{lab}": pct(m),
                f"quit_after_{lab}_lo": pct(lo),
                f"quit_after_{lab}_hi": pct(hi),
            }
        )
        cont = c.filter(~pl.col("last_of_session"))
        m2 = boot_mean(
            cont.with_columns(q=(pl.col("gap_after_s") < 60).cast(pl.Float64)), "q", reps=100
        )[0]
        r[f"next_within_60s_after_{lab}"] = pct(m2)
        r[f"median_gap_after_{lab}_s"] = round(fmedian(cont["gap_after_s"]), 0)
        r[f"n_{lab}"] = c.height
    # sessions ending on a loss vs base loss rate
    last = d.filter(pl.col("last_of_session") & (pl.col("session_len") >= 2))
    r["sessions_ending_on_loss_pct"] = pct(fmean(last["score"] == 0))
    r["base_loss_rate_pct"] = pct(fmean(d["score"] == 0))
    rows.append(r)
emit(
    "6. Quit and rush: P(session ends after this game) and P(next game within 60 s) after a loss vs a win",
    pl.DataFrame(rows),
    "quit_rush",
)
# revenge rematch: next game vs the same opponent, in session, after a loss / after a win
rm = story.filter(pl.col("in_session") & pl.col("prev_score").is_in([0.0, 1.0]))
rows = []
for tc in TC_ORDER + ["all"]:
    d = rm if tc == "all" else rm.filter(pl.col("tc") == tc)
    r = {"tc": tc}
    for lab, sc in [("after_loss", 0.0), ("after_win", 1.0)]:
        c = d.filter(pl.col("prev_score") == sc)
        rem, fresh = c.filter(pl.col("rematch")), c.filter(~pl.col("rematch"))
        r[f"rematch_rate_{lab}"] = mean_pct(c, "rematch")
        m, lo, hi = boot_mean(rem, "resid", reps=REPS)
        r.update(
            {
                f"rematch_n_{lab}": rem.height,
                f"rematch_score_{lab}": mean_pct(rem, "score"),
                f"rematch_expected_{lab}": mean_pct(rem, "exp_score"),
                f"rematch_resid_{lab}": pct(m),
                f"rematch_lo_{lab}": pct(lo),
                f"rematch_hi_{lab}": pct(hi),
            }
        )
        m, lo, hi = boot_mean(fresh, "resid", reps=REPS)
        r.update(
            {f"fresh_resid_{lab}": pct(m), f"fresh_lo_{lab}": pct(lo), f"fresh_hi_{lab}": pct(hi)}
        )
    rows.append(r)
emit(
    "6b. Revenge rematch: residual when rematching the opponent who just beat you vs a fresh opponent (and the post-win mirror)",
    pl.DataFrame(rows),
    "revenge",
)
# first rematch of a pairing vs a later game in a series against the same opponent: the
# opponent-strength selection story (the player who just beat you is under-rated) predicts a
# symmetric bonus after wins, which only the first rematch shows
rm = rm.with_columns(prev_rematch=pl.col("rematch").shift(1).over(USER_W))
rows = []
for lab, sc in [("after_loss", 0.0), ("after_win", 1.0)]:
    for pos, cond in [
        ("first rematch", ~pl.col("prev_rematch")),
        ("later in a series", pl.col("prev_rematch")),
    ]:
        c = rm.filter((pl.col("prev_score") == sc) & pl.col("rematch") & cond.fill_null(False))
        f = rm.filter((pl.col("prev_score") == sc) & ~pl.col("rematch"))
        m, lo, hi = boot_mean(c, "resid", reps=REPS)
        dm, dlo, dhi = boot_diff(c, f, "resid", reps=REPS)
        rows.append(
            {
                "after": lab.replace("after_", "after "),
                "position": pos,
                "n": c.height,
                "rematch_resid": pct(m),
                "lo": pct(lo),
                "hi": pct(hi),
                "fresh_resid": pct(boot_mean(f, "resid", reps=50)[0]),
                "rematch_minus_fresh": pct(dm),
                "diff_lo": pct(dlo),
                "diff_hi": pct(dhi),
            }
        )
emit(
    "6b2. Revenge rematch: first rematch vs later in a series, and rematch minus fresh",
    pl.DataFrame(rows),
    "revenge_series",
)
rows = []
for e in ELO_ANCHORS:
    d = rm.filter(pl.col("elo_bucket") == e)
    r = {"elo_bucket": e}
    for lab, sc in [("after_loss", 0.0), ("after_win", 1.0)]:
        c = d.filter(pl.col("prev_score") == sc)
        rem = c.filter(pl.col("rematch"))
        m, lo, hi = boot_mean(rem, "resid", reps=REPS)
        r.update(
            {
                f"rematch_rate_{lab}": mean_pct(c, "rematch"),
                f"rematch_n_{lab}": rem.height,
                f"rematch_resid_{lab}": pct(m),
                f"lo_{lab}": pct(lo),
                f"hi_{lab}": pct(hi),
            }
        )
    rows.append(r)
emit("6c. Revenge rematch by rating", pl.DataFrame(rows), "revenge_by_rating")

# speed: think time per move (moves 3-20) after a loss vs after a win, paired per user
mf = pl.read_parquet(OUT / "move_feats.parquet")
mv = story.with_columns(side=pl.when(pl.col("user_color") == "white").then(0).otherwise(1)).join(
    mf, on=["game_id", "side"], how="left"
)
mv = mv.filter(pl.col("in_session") & (pl.col("n_think_o") >= MIN_THINK_MOVES)).with_columns(
    think=pl.col("think_o") / pl.col("n_think_o"),
    fast1=pl.col("fast1_o") / pl.col("n_think_o"),
    clk20=pl.col("clk_m20") / pl.col("base_s"),
)
rows = []
for tc in TC_ORDER:
    d = mv.filter(pl.col("tc") == tc)
    r = {"tc": tc}
    for s in ["LLL+", "L", "W", "WWW+"]:
        c = d.filter(pl.col("streak") == s)
        r[f"think_s_{s}"] = round(boot_mean(c, "think", reps=100)[0], 2)
        r[f"fast_moves_pct_{s}"] = pct(boot_mean(c, "fast1", reps=50)[0])
        r[f"n_{s}"] = c.height
    pu = (
        d.filter(pl.col("streak").is_in(["L", "W"]))
        .group_by(["user_id", "streak"])
        .agg(pl.col("think").mean().alias("m"), pl.len().alias("n"))
        .filter(pl.col("n") >= MIN_PAIRED_GAMES)
    )
    pv = pu.pivot(on="streak", index="user_id", values="m").drop_nulls()
    r.update(
        {
            "paired_users": pv.height,
            "paired_rel_change_pct": pct(fmean(pv["L"] / pv["W"] - 1)),
            "share_users_faster_after_loss": pct(fmean(pv["L"] < pv["W"])),
        }
    )
    rows.append(r)
emit(
    "6d. Speed: seconds per move (moves 3-20) and share of moves under 1 s, by streak; paired per-user change after a loss vs after a win",
    pl.DataFrame(rows),
    "speed",
)

# move quality: blunders per 100 own moves in the uniformly analysed arm (rapid/classical)
fl = pl.read_parquet(OUT / "flaws_byus.parquet").drop("tc")
bq = (
    story.join(fl, on="game_id", how="inner")
    .with_columns(
        my_bl=pl.when(pl.col("user_color") == "white")
        .then(pl.col("w_bl"))
        .otherwise(pl.col("b_bl")),
        opp_bl=pl.when(pl.col("user_color") == "white")
        .then(pl.col("b_bl"))
        .otherwise(pl.col("w_bl")),
    )
    .with_columns(
        bl100=pl.col("my_bl") / (pl.col("ply_count") / 2) * 100,
        opp_bl100=pl.col("opp_bl") / (pl.col("ply_count") / 2) * 100,
    )
)
bq = bq.filter(pl.col("in_session") & (pl.col("ply_count") >= 20))
rows = []
for tc in ["rapid", "classical", "all"]:
    d = bq if tc == "all" else bq.filter(pl.col("tc") == tc)
    r = {"tc": tc}
    for s in ["LLL+", "LL", "L", "W", "WW", "WWW+"]:
        c = d.filter(pl.col("streak") == s)
        m, lo, hi = boot_mean(c, "bl100", reps=REPS)
        r.update(
            {
                f"blunders_per_100_{s}": round(m, 2),
                f"lo_{s}": round(lo, 2),
                f"hi_{s}": round(hi, 2),
                f"opp_blunders_{s}": round(boot_mean(c, "opp_bl100", reps=50)[0], 2),
                f"n_{s}": c.height,
            }
        )
    rows.append(r)
emit(
    "6e. Move quality: blunders per 100 own moves after a streak (uniformly analysed arm, rapid/classical)",
    pl.DataFrame(rows),
    "blunders",
)

# P(loss) after k straight losses, raw
sp = after.filter(pl.col("streak_dir") == -1).with_columns(
    k=pl.col("streak_len").clip(upper_bound=6)
)
emit(
    "6f. Raw probability of losing the next game after k straight losses (pooled)",
    sp.group_by("k")
    .agg(
        pl.len().alias("n"),
        (pl.col("score") == 0).mean().mul(100).round(1).alias("p_loss_pct"),
        (pl.col("score") == 1).mean().mul(100).round(1).alias("p_win_pct"),
        pl.col("score").mean().mul(100).round(1).alias("score_pct"),
        pl.col("exp_score").mean().mul(100).round(1).alias("expected_pct"),
    )
    .sort("k"),
    "p_loss_after_k",
)

# analysis requests: was the LAST game of the streak analysed (lichess_evals_at set, i.e. either
# player requested lichess computer analysis)? Each game is the last game of its own run so far,
# so the streak here is (dir, run_len) of the game itself, not the streak before it; no
# next-game condition, because requesting analysis takes minutes and would bias "next within
# the hour". Frame: all rated games with hygiene (a rate, so no equal footing), and the run
# within one session (a 6-loss run spread over days is not a tilt state).
analyzed = pl.read_parquet(OUT / "acc.parquet").select("game_id", "analyzed")
an = (
    beh.join(analyzed, on="game_id", how="left")
    .filter(pl.col("analyzed").is_not_null())
    .with_columns(
        xo=(pl.col("dir") * pl.col("run_len").clip(upper_bound=6)).cast(pl.Int32),
        run_same_session=pl.col("run_start_session") == pl.col("session_id"),
        a=pl.col("analyzed").cast(pl.Float64),
    )
)
# user-demeaned rate: long streaks come from high-volume players, who may analyse less in
# general; subtracting each user x TC mean rate removes that composition
an = an.with_columns(a_dm=pl.col("a") - pl.col("a").mean().over(USER_W))
an_ss = an.filter(pl.col("run_same_session"))
# session-depth control: a k-streak game sits at least k games into its session, and the
# per-game analysis rate falls with session length whatever the result (rapid: 40% in
# one-game sessions, 25% at 8+). Comparing streak lengths only among games 6-15 of a session
# puts every cell at the same depth (and the same share of session-ending games).
an_deep = an_ss.filter(pl.col("session_idx").is_between(*DEEP_SESSION_IDX))
rows = []
for x in XS6:
    c = an_ss.filter(pl.col("xo") == x)
    r = {"x": x, "n": c.height}
    m, lo, hi = boot_mean(c, "a", reps=REPS)
    r.update({"analysed_pct": pct(m), "analysed_lo": pct(lo), "analysed_hi": pct(hi)})
    m, lo, hi = boot_mean(c, "a_dm", reps=REPS)
    r.update({"demeaned_pp": pct(m), "demeaned_lo": pct(lo), "demeaned_hi": pct(hi)})
    cd = an_deep.filter(pl.col("xo") == x)
    m, lo, hi = boot_mean(cd, "a_dm", reps=REPS)
    r.update({"deep_n": cd.height, "deep_pp": pct(m), "deep_lo": pct(lo), "deep_hi": pct(hi)})
    r["rapid_deep_pp"] = mean_pct(cd.filter(pl.col("tc") == "rapid"), "a_dm")
    r["analysed_pct_any_session"] = mean_pct(an.filter(pl.col("xo") == x), "a")
    r["n_any_session"] = an.filter(pl.col("xo") == x).height
    for tc in TC_ORDER:
        ct = c.filter(pl.col("tc") == tc)
        r[f"{tc}_n"] = ct.height
        r[f"{tc}_analysed_pct"] = mean_pct(ct, "a")
    rows.append(r)
emit(
    "6g. Share of streak-ending games with lichess analysis (last game of the streak), -6 = 6+ losses ... +6 = 6+ wins",
    pl.DataFrame(rows),
    "analysed_by_streak",
)

# ---- 7. trait: split-half reliability of a player's post-loss minus post-win residual -----
tr = story.filter(pl.col("in_session") & pl.col("streak_dir").is_in([-1, 1])).with_columns(
    half=(pl.col("session_id") % 2), dirn=pl.col("streak_dir")
)
pu = tr.group_by(["user_id", "tc", "half", "dirn"]).agg(
    pl.col("resid").mean().alias("m"), pl.len().alias("n")
)
pv = pu.pivot(on="dirn", index=["user_id", "tc", "half"], values="m").rename(
    {"-1": "after_loss", "1": "after_win"}
)
cnt = pu.pivot(on="dirn", index=["user_id", "tc", "half"], values="n").rename(
    {"-1": "n_loss", "1": "n_win"}
)
pv = (
    pv.join(cnt, on=["user_id", "tc", "half"])
    .filter((pl.col("n_loss") >= 25) & (pl.col("n_win") >= 25))
    .with_columns(delta=pl.col("after_loss") - pl.col("after_win"))
)
halves = pv.pivot(on="half", index=["user_id", "tc"], values="delta").drop_nulls()
d0, d1 = halves["0"].to_numpy(), halves["1"].to_numpy()
r_split = float(np.corrcoef(d0, d1)[0, 1])
# full-length delta = mean of the two halves, over the same user x TC streams the
# correlation uses (streams with only one qualifying half would inflate the SD)
full = halves.with_columns(delta=(pl.col("0") + pl.col("1")) / 2)
rel = 2 * r_split / (1 + r_split)
trait = {
    "streams_user_x_tc": halves.height,
    "users": halves["user_id"].n_unique(),
    "mean_delta_pp": pct(fmean(full["delta"])),
    "sd_delta_pp": pct(fstd(full["delta"])),
    "split_half_r": round(r_split, 3),
    "spearman_brown_reliability": round(rel, 3),
    "implied_true_sd_pp": pct(fstd(full["delta"]) * np.sqrt(max(rel, 0))),
}
(STORY / "trait.json").write_text(json.dumps(trait, indent=2))
md.append(
    "\n### 7. Trait: split-half reliability of post-loss minus post-win residual\n\n```json\n"
    + json.dumps(trait, indent=2)
    + "\n```"
)
print(trait)

(STORY / "tables.md").write_text("# Tilt story tables\n" + "\n".join(md) + "\n")
print(f"done {time.time() - t0:.0f}s -> {STORY}")
