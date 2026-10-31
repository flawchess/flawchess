"""Which per-(user, colour) MG-entry metric separates players beyond sampling noise?

Run: uv run --with numpy python .planning/sketches/013-out-of-the-opening/analysis/analyze.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

rows = list(csv.DictReader((Path(__file__).parent / "cells.csv").open()))
n = np.array([float(r["n"]) for r in rows])
elo = np.array([int(r["elo_bucket"]) for r in rows])
tc = np.array([r["tc"] for r in rows])
col = np.array([r["user_color"] for r in rows])
f = {k: np.array([float(r[k]) for r in rows]) for k in ("mean_c", "sd_c", "mean_wc", "score", "down100", "up100", "down200", "up200")}


def noise_var(k: str) -> np.ndarray:
    if k == "mean_c":
        return f["sd_c"] ** 2 / n
    if k == "sd_c":
        return f["sd_c"] ** 2 / (2 * (n - 1))  # normal approx; heavy tails make it optimistic
    if k.startswith(("down", "up")):
        p = f[k]
        return p * (1 - p) / n
    if k == "score":
        return f[k] * (1 - f[k]) / n  # upper bound (draws lower it)
    raise KeyError(k)


def iqr(x: np.ndarray) -> float:
    q1, q3 = np.percentile(x, [25, 75])
    return float(q3 - q1)


def d(a: np.ndarray, b: np.ndarray) -> float:
    s = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2)
    return float((a.mean() - b.mean()) / s) if s > 0 else 0.0


def max_d(x: np.ndarray, groups: np.ndarray) -> float:
    keys = sorted(set(groups))
    return max(abs(d(x[groups == a], x[groups == b])) for i, a in enumerate(keys) for b in keys[i + 1 :])


METRICS = ("mean_c", "sd_c", "down100", "up100", "down200", "up200", "score")
print(f"cells={len(rows)}  median n={np.median(n):.0f}  p25 n={np.percentile(n, 25):.0f}  p75 n={np.percentile(n, 75):.0f}\n")
print("## Reliability (share of between-player variance that is real, = 1 - noise var / observed var)")
print("metric   | median | IQR    | rel all | rel n>=100 | rel n>=300 | colour d | TC max|d| | ELO max|d|")
for k in METRICS:
    x = f[k]
    rel = lambda m: 1 - noise_var(k)[m].mean() / x[m].var(ddof=1)  # noqa: E731
    print(
        f"{k:8} | {np.median(x):6.3f} | {iqr(x):6.3f} | {rel(n >= 0):7.2f} | {rel(n >= 100):10.2f} | {rel(n >= 300):10.2f}"
        f" | {d(x[col == 'white'], x[col == 'black']):8.2f} | {max_d(x, tc):9.2f} | {max_d(x, elo):9.2f}"
    )
print(f"\ncells n>=100: {(n >= 100).sum()}, n>=300: {(n >= 300).sum()}")

print("\n## ELO marginal (median [p25, p75])")
for k in ("mean_c", "sd_c", "down100", "up100", "down200"):
    cells = "  ".join(f"{e}: {np.median(f[k][elo == e]):.3f} [{np.percentile(f[k][elo == e], 25):.3f},{np.percentile(f[k][elo == e], 75):.3f}]" for e in sorted(set(elo)))
    print(f"{k:8} {cells}")

print("\n## Colour marginal (median)")
for k in ("mean_c", "sd_c", "down100", "up100", "down200", "up200"):
    print(f"{k:8} white {np.median(f[k][col == 'white']):.3f}  black {np.median(f[k][col == 'black']):.3f}")


def rank(x: np.ndarray) -> np.ndarray:
    return np.argsort(np.argsort(x)).astype(float)


print("\n## Spearman correlations (n>=100 cells)")
m = n >= 100
ks = ("mean_c", "sd_c", "down100", "up100", "down200", "score")
print("         " + " ".join(f"{k:>8}" for k in ks))
for a in ks:
    print(f"{a:8} " + " ".join(f"{np.corrcoef(rank(f[a][m]), rank(f[b][m]))[0, 1]:8.2f}" for b in ks))

# Does the downside tail predict score beyond the mean? OLS within (elo, tc) via demeaning.
print("\n## Score ~ mean_c + down100 + up100 (cells n>=100, demeaned within ELO x TC, standardized betas)")
grp = np.array([f"{e}_{t}" for e, t in zip(elo, tc)])


def demean(x: np.ndarray) -> np.ndarray:
    out = x.copy()
    for g in set(grp[m]):
        sel = m & (grp == g)
        out[sel] = x[sel] - x[sel].mean()
    return out[m]


y = demean(f["score"])
for cols in (("mean_c",), ("down100", "up100"), ("mean_c", "down100", "up100"), ("mean_c", "sd_c")):
    X = np.column_stack([demean(f[c]) / demean(f[c]).std() for c in cols])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r2 = 1 - ((y - X @ beta) ** 2).sum() / (y**2).sum()
    print(f"  {' + '.join(cols):28} R2={r2:.3f}  betas(score pp per SD)=" + ", ".join(f"{c}={b * 100:+.2f}" for c, b in zip(cols, beta)))
