"""Numeric acceptance gate for Chapter 3 §3.3 (Time Pressure).

Runs the §3.3 clock/curve/pressure-bin scans against the live benchmark DB and asserts
the values match benchmarks-latest.md (2026-05-27). Skips when the benchmark DB is
unreachable. `benchmark_session` is from conftest.py.

Documented divergences (footnoted in chapter3_3.py — all verdict-NEUTRAL or
verdict-narrative-only, the shipped bands all reproduce exactly):
  - §3.3.1 net-timeout TC: report 0.04 → deterministic 0.09 (blitz vs classical); collapse.
  - §3.3.2 per-tb TC d: report ≈0.38/≈0.13 → deterministic 0.39/0.14 (1-ulp approximations).
  - §3.3.3 per-quintile verdicts: the report's d's (≈0.18–0.46) were not computed with the
    documented per-user n/mean/var_samp recipe; the deterministic recipe gives the values
    asserted here (Q0 TC 0.75, Q0 ELO 0.56, …). The 20-cell band table matches exactly.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.benchmarks import chapter3_3

pytestmark = pytest.mark.asyncio


# --- §3.3.1 Clock pressure ----------------------------------------------------

EXPECTED_331_DIFF_POOLED = {"n": 4604, "mean": -1.12, "p25": -6.35, "p50": -0.50, "p75": 4.83}
# label -> (n, mean, p25, p50, p75)
EXPECTED_331_DIFF_ELO = {
    "800": (752, -1.00, -6.10, -0.36, 5.05),
    "1200": (1067, -1.28, -6.83, -0.47, 5.20),
    "1600": (1164, -1.82, -7.44, -1.06, 4.71),
    "2000": (1025, -0.86, -6.18, -0.56, 4.49),
    "2400": (596, -0.09, -4.56, -0.04, 4.15),
}
EXPECTED_331_DIFF_TC = {
    "bullet": (1343, -0.17, -3.96, -0.29, 3.29),
    "blitz": (1353, -0.77, -6.68, -0.29, 5.27),
    "rapid": (1334, -1.81, -8.14, -0.94, 5.21),
    "classical": (574, -2.60, -11.29, -1.21, 8.19),
}
EXPECTED_331_DIFF_VERDICTS = {
    "TC": (("bullet", "classical"), 0.24),
    "ELO": (("1600", "2400"), 0.17),
}

EXPECTED_331_GAP_POOLED = {"n": 4604, "p25": -0.0635, "p50": -0.0050, "p75": 0.0483}
EXPECTED_331_GAP_TC = {
    "bullet": (-0.0396, -0.0029, 0.0329),
    "blitz": (-0.0668, -0.0029, 0.0527),
    "rapid": (-0.0814, -0.0094, 0.0521),
    "classical": (-0.1129, -0.0121, 0.0819),
}

EXPECTED_331_NET_POOLED = {"n": 4604, "mean": 0.45, "p25": -4.46, "p50": 1.13, "p75": 6.09}
# Report shows only ELO 800/2400 and TC bullet/classical for net-timeout.
EXPECTED_331_NET_ELO = {
    "800": (-0.93, -5.89, 0.00, 4.81),
    "2400": (2.33, -3.80, 2.85, 9.29),
}
EXPECTED_331_NET_TC = {
    "bullet": (0.45, -10.95, 0.53, 11.86),
    "classical": (-0.05, 0.00, 0.00, 1.80),
}
# Report net TC labels 0.04; deterministic max is 0.09 (blitz vs classical), both collapse.
EXPECTED_331_NET_VERDICTS = {"TC": (("blitz", "classical"), 0.09), "ELO": (("800", "2400"), 0.28)}


async def test_331_matches_report(benchmark_session: AsyncSession) -> None:
    v = await chapter3_3.compute_331(benchmark_session)

    p = v["diff_pooled"]
    assert p["n"] == EXPECTED_331_DIFF_POOLED["n"]
    for k in ("mean", "p25", "p50", "p75"):
        assert p[k] == pytest.approx(EXPECTED_331_DIFF_POOLED[k]), f"diff pooled {k}"
    _check_pct_marginals(v["diff_elo"], EXPECTED_331_DIFF_ELO)
    _check_pct_marginals(v["diff_tc"], EXPECTED_331_DIFF_TC)
    _check_verdicts(v["diff_verdicts"], EXPECTED_331_DIFF_VERDICTS)

    g = v["gap_pooled"]
    assert g["n"] == EXPECTED_331_GAP_POOLED["n"]
    for k in ("p25", "p50", "p75"):
        assert g[k] == pytest.approx(EXPECTED_331_GAP_POOLED[k]), f"gap pooled {k}"
    gap_tc = {m["label"]: m["dist"] for m in v["gap_tc"]}
    for label, (p25, p50, p75) in EXPECTED_331_GAP_TC.items():
        d = gap_tc[label]
        assert (d["p25"], d["p50"], d["p75"]) == pytest.approx((p25, p50, p75)), f"gap {label}"

    n = v["net_pooled"]
    assert n["n"] == EXPECTED_331_NET_POOLED["n"]
    for k in ("mean", "p25", "p50", "p75"):
        assert n[k] == pytest.approx(EXPECTED_331_NET_POOLED[k]), f"net pooled {k}"
    _check_pct_marginals(v["net_elo"], EXPECTED_331_NET_ELO, has_n=False)
    _check_pct_marginals(v["net_tc"], EXPECTED_331_NET_TC, has_n=False)
    _check_verdicts(v["net_verdicts"], EXPECTED_331_NET_VERDICTS)


def _check_pct_marginals(marginals, expected: dict, *, has_n: bool = True) -> None:
    by_label = {m["label"]: m for m in marginals}
    for label, vals in expected.items():
        d = by_label[label]["dist"]
        if has_n:
            n, mean, p25, p50, p75 = vals
            assert d["n"] == n, label
        else:
            mean, p25, p50, p75 = vals
        assert d["mean"] == pytest.approx(mean), f"{label} mean"
        assert (d["p25"], d["p50"], d["p75"]) == pytest.approx((p25, p50, p75)), f"{label} pct"


def _check_verdicts(verdicts, expected: dict) -> None:
    by_axis = {v["axis"]: v for v in verdicts}
    for axis, (pair, d) in expected.items():
        assert by_axis[axis]["pair"] == pair, axis
        assert round(by_axis[axis]["max_abs_d"], 2) == d, axis


# --- §3.3.2 Time-pressure-vs-performance curve --------------------------------

# (tb, n_games, score)
EXPECTED_332_POOLED = [
    (0, 74569, 0.3103),
    (1, 97328, 0.4183),
    (2, 106008, 0.4898),
    (3, 125531, 0.5216),
    (4, 140322, 0.5400),
    (5, 150007, 0.5470),
    (6, 148644, 0.5433),
    (7, 128236, 0.5369),
    (8, 84609, 0.5267),
    (9, 52117, 0.5153),
]
EXPECTED_332_TC0 = {"bullet": 0.2564, "blitz": 0.3415, "rapid": 0.3466, "classical": 0.4247}
EXPECTED_332_ELO0 = {"800": 0.2679, "1200": 0.2852, "1600": 0.3108, "2000": 0.3381, "2400": 0.3368}
# Per-tb TC max |d| on per-game score. Report ≈0.38/≈0.13/0.05 (1-ulp-low approximations).
EXPECTED_332_TC_VERDICT = {0: 0.39, 5: 0.14, 9: 0.05}


async def test_332_matches_report(benchmark_session: AsyncSession) -> None:
    v = await chapter3_3.compute_332(benchmark_session)

    got = [(p["tb"], p["n"], p["score"]) for p in v["pooled"]]
    assert got == EXPECTED_332_POOLED

    for label, score in EXPECTED_332_TC0.items():
        assert v["tc"][0][label] == pytest.approx(score), f"tc tb0 {label}"
    for label, score in EXPECTED_332_ELO0.items():
        assert v["elo"][0][label] == pytest.approx(score), f"elo tb0 {label}"

    tc_by_tb = {x["tb"]: x for x in v["verdicts"] if x["axis"] == "TC"}
    for tb, d in EXPECTED_332_TC_VERDICT.items():
        assert round(tc_by_tb[tb]["max_abs_d"], 2) == d, f"tc verdict tb{tb}"
    # ELO collapses across every bucket (report ≈0.10–0.18).
    elo_max = max(x["max_abs_d"] for x in v["verdicts"] if x["axis"] == "ELO")
    assert elo_max < 0.2


# --- §3.3.3 Chess score per pressure bin --------------------------------------

# (tc, quintile) -> (n_users, p25, p50, p75). All 20 cells reproduce the report exactly.
EXPECTED_333_BANDS = {
    ("bullet", 0): (1304, 0.2747, 0.3434, 0.4193),
    ("bullet", 1): (1362, 0.4627, 0.5160, 0.5792),
    ("bullet", 2): (1356, 0.5074, 0.5620, 0.6188),
    ("bullet", 3): (1274, 0.5000, 0.5685, 0.6333),
    ("bullet", 4): (679, 0.4487, 0.5429, 0.6429),
    ("blitz", 0): (1218, 0.3066, 0.3886, 0.4760),
    ("blitz", 1): (1296, 0.4502, 0.5110, 0.5864),
    ("blitz", 2): (1341, 0.4905, 0.5476, 0.6146),
    ("blitz", 3): (1340, 0.4920, 0.5526, 0.6190),
    ("blitz", 4): (1057, 0.4545, 0.5441, 0.6250),
    ("rapid", 0): (830, 0.2969, 0.4000, 0.5000),
    ("rapid", 1): (1110, 0.4167, 0.5000, 0.5833),
    ("rapid", 2): (1297, 0.4600, 0.5385, 0.6200),
    ("rapid", 3): (1358, 0.4722, 0.5400, 0.6136),
    ("rapid", 4): (1158, 0.4565, 0.5292, 0.6150),
    ("classical", 0): (187, 0.3402, 0.4333, 0.5714),
    ("classical", 1): (263, 0.4000, 0.5000, 0.5833),
    ("classical", 2): (357, 0.4000, 0.5000, 0.6047),
    ("classical", 3): (489, 0.4000, 0.5000, 0.6111),
    ("classical", 4): (727, 0.4201, 0.5059, 0.6146),
}
# Deterministic per-user Cohen's d per quintile (NOT the report's eyeballed ≈ values).
# quintile -> {axis: (pair, d)}
EXPECTED_333_VERDICTS = {
    0: {"TC": (("bullet", "classical"), 0.75), "ELO": (("800", "2400"), 0.56)},
    1: {"TC": (("bullet", "classical"), 0.32), "ELO": (("1200", "2400"), 0.15)},
    2: {"TC": (("bullet", "classical"), 0.46), "ELO": (("1200", "2400"), 0.25)},
    3: {"TC": (("bullet", "classical"), 0.40), "ELO": (("1200", "2000"), 0.34)},
    4: {"TC": (("bullet", "classical"), 0.19), "ELO": (("800", "2400"), 0.31)},
}


async def test_333_matches_report(benchmark_session: AsyncSession) -> None:
    v = await chapter3_3.compute_333(benchmark_session)

    by_cell = {(b["tc"], b["quintile"]): b for b in v["bands"]}
    assert set(by_cell) == set(EXPECTED_333_BANDS)
    for cell, (n, p25, p50, p75) in EXPECTED_333_BANDS.items():
        b = by_cell[cell]
        assert b["n_users"] == n, cell
        assert (b["p25"], b["p50"], b["p75"]) == pytest.approx((p25, p50, p75)), cell

    by_qa = {(x["quintile"], x["axis"]): x for x in v["verdicts"]}
    for q, axes in EXPECTED_333_VERDICTS.items():
        for axis, (pair, d) in axes.items():
            assert by_qa[(q, axis)]["pair"] == pair, (q, axis)
            assert round(by_qa[(q, axis)]["max_abs_d"], 2) == d, (q, axis)
