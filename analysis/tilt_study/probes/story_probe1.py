"""Story probe 1: control ladder for the streak curve, colour check, hygiene curve per TC/rating."""

import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import polars as pl
from story_data import OUT, TC_ORDER, MAX_STREAK, load_games, boot_mean

pl.Config.set_tbl_rows(60)
pl.Config.set_tbl_cols(30)
pl.Config.set_tbl_width_chars(240)
t0 = time.time()
cache = OUT / "features.parquet"
if cache.exists():
    g = pl.read_parquet(cache)
else:
    g = load_games()
    g.write_parquet(cache)
print("features", g.shape, f"{time.time() - t0:.0f}s")
xs = list(range(-MAX_STREAK, MAX_STREAK + 1))


def curve(df, col="score", reps=200):
    rows = []
    for x in xs:
        c = df.filter(pl.col("x") == x)
        m, lo, hi = boot_mean(c, col, reps=reps)
        rows.append(
            {"x": x, "n": c.height, col: round(m * 100, 2), "ci": round((hi - lo) / 2 * 100, 2)}
        )
    return pl.DataFrame(rows)


base = g.filter(pl.col("streak_dir").is_not_null())
print("\n=== Control ladder (raw next-game score %, pooled) ===")
L0 = base  # any opponent, any gap
L1 = base.filter(pl.col("equal_footing"))  # + scored on equal footing
L2 = L1.filter(pl.col("in_session") & pl.col("streak_same_session"))  # + tonight's streak
L3 = L2.filter(pl.col("hygiene"))  # + account hygiene
lad = (
    curve(L0)
    .rename({"score": "L0_any"})
    .join(curve(L1).select("x", pl.col("score").alias("L1_equal")), on="x")
    .join(curve(L2).select("x", pl.col("score").alias("L2_session")), on="x")
    .join(
        curve(L3).select("x", pl.col("score").alias("L3_hygiene"), pl.col("n").alias("n3")), on="x"
    )
    .join(
        curve(L3, "exp_score", reps=20).select("x", pl.col("exp_score").alias("L3_expected")),
        on="x",
    )
    .join(
        curve(L3, "resid").select(
            "x", pl.col("resid").alias("L3_resid"), pl.col("ci").alias("ci_resid")
        ),
        on="x",
    )
    .join(
        curve(L3, "resid_nocolour", reps=50).select(
            "x", pl.col("resid_nocolour").alias("resid_nocol")
        ),
        on="x",
    )
)
print(lad)
# opponent gap and colour mix after streaks (why L0 differs from L1)
print("\n=== Opponent gap / colour / rating deviation by streak (L0) ===")
print(
    base.group_by("x")
    .agg(
        pl.len().alias("n"),
        (pl.col("my_r") - pl.col("opp_r")).mean().round(1).alias("mean_gap"),
        pl.col("equal_footing").mean().round(3).alias("share_equal"),
        (pl.col("user_color") == "white").mean().round(3).alias("share_white"),
        pl.col("r_dev").mean().round(1).alias("r_minus_median"),
        pl.col("in_session").mean().round(3).alias("in_session"),
        pl.col("streak_same_session").mean().round(3).alias("same_sess"),
    )
    .sort("x")
)

print("\n=== Hygiene curve by TC (raw score / resid) ===")
for tc in TC_ORDER:
    d = L3.filter(pl.col("tc") == tc)
    c = curve(d).join(curve(d, "resid").select("x", "resid", pl.col("ci").alias("ci_r")), on="x")
    print(tc)
    print(c)
print("\n=== Hygiene curve by rating (resid) ===")
for e in (800, 1200, 1600, 2000, 2400):
    d = L3.filter(pl.col("elo_bucket") == e)
    print(e)
    print(curve(d).join(curve(d, "resid").select("x", "resid", pl.col("ci").alias("ci_r")), on="x"))
print(f"{time.time() - t0:.0f}s")
