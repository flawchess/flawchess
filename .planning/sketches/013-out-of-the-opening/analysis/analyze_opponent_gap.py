"""The rejected "you vs. your opponents" framing: gap = better rate − worse rate (= opponent's worse
rate − yours, since the shared centred eval mirrors exactly). Collapses on ELO/TC, but it is ONE number:
worse and better cannot both be compared to the opponent independently.
Run (after fetch_sweep.py): uv run --with numpy python .planning/sketches/013-out-of-the-opening/analysis/analyze_opponent_gap.py"""
import csv
from pathlib import Path

import numpy as np

rows = list(csv.DictReader((Path(__file__).parent / "sweep_cells.csv").open()))
n = np.array([float(r["n"]) for r in rows]); elo = np.array([int(r["elo_bucket"]) for r in rows]); tc = np.array([r["tc"] for r in rows])
dw = np.array([float(r["down100"]) for r in rows]); up = np.array([float(r["up100"]) for r in rows])
gap = up - dw
var = (up + dw - (up - dw) ** 2) / n   # per-game x in {-1, 0, 1}
m = n >= 100
print("gap pooled median %.3f IQR [%.3f, %.3f]" % (np.median(gap), *np.percentile(gap, [25, 75])))
print("reliability n>=100: %.2f  noise share of IQR: %.0f%%" % (1 - var[m].mean() / gap[m].var(ddof=1), 100 * 1.349 * np.sqrt(var.mean()) / np.subtract(*np.percentile(gap, [75, 25]))))
def d(a, b): return (a.mean() - b.mean()) / np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
for name, g in (("ELO", elo), ("TC", tc)):
    ks = sorted(set(g)); print(name, "max|d| %.2f" % max(abs(d(gap[g == a], gap[g == b])) for a in ks for b in ks if a < b))
print("per-user SE at n=200: %.3f" % np.sqrt(np.median(up + dw - (up - dw) ** 2) / 200))
