"""Run: uv run --with numpy python .planning/sketches/013-out-of-the-opening/analysis/analyze_sweep.py"""
from __future__ import annotations
import csv
from pathlib import Path
import numpy as np
from fetch_sweep import THRESHOLDS

rows = list(csv.DictReader((Path(__file__).parent / "sweep_cells.csv").open()))
n = np.array([float(r["n"]) for r in rows]); elo = np.array([int(r["elo_bucket"]) for r in rows])
tc = np.array([r["tc"] for r in rows]); col = np.array([r["user_color"] for r in rows])
F = lambda k: np.array([float(r[k]) if r[k] != "" else np.nan for r in rows])  # noqa: E731
score = F("score"); m = n >= 100
grp = np.array([f"{e}_{t}" for e, t in zip(elo, tc)])
def d(a, b): return (a.mean() - b.mean()) / np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
def maxd(x, g):
    ks = sorted(set(g)); return max(abs(d(x[g == a], x[g == b])) for i, a in enumerate(ks) for b in ks[i + 1:])
def demean(x):
    out = x.copy()
    for g in set(grp[m]):
        s = m & (grp == g); out[s] = x[s] - x[s].mean()
    return out[m]
y = demean(score)
print(f"cells={len(rows)}  ended-in-opening share median={np.median(F('ended_in_opening')):.3f}")
print("thr  side | med800 med1600 med2400 | rel n>=100 | colour d | TC d | ELO d | score pp/SD (alone) | R2")
for t in THRESHOLDS:
    for side in ("down", "up"):
        x = F(f"{side}{t}"); rel = 1 - (x * (1 - x) / n)[m].mean() / x[m].var(ddof=1)
        xd = demean(x); xs = xd / xd.std(); b = (xs @ y) / (xs @ xs); r2 = 1 - ((y - b * xs) ** 2).sum() / (y ** 2).sum()
        meds = " ".join(f"{np.median(x[elo == e]):.3f}" for e in (800, 1600, 2400))
        print(f"{t:4} {side:5}| {meds} | {rel:10.2f} | {d(x[col=='white'], x[col=='black']):8.2f} | {maxd(x, tc):4.2f} | {maxd(x, elo):5.2f} | {b*100:+19.2f} | {r2:.3f}")
mc = F("mean_c"); xd = demean(mc); xs = xd / xd.std(); b = (xs @ y) / (xs @ xs)
print(f"mean_c alone: {b*100:+.2f} pp/SD, R2={1 - ((y - b*xs)**2).sum() / (y**2).sum():.3f}")
