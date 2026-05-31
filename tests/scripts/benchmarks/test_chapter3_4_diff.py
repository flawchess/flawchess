"""Numeric acceptance gate for Chapter 3 §3.4 (Endgame Type Breakdown).

Runs the §3.4 per-class scans against the live benchmark DB and asserts the values match
benchmarks-latest.md (2026-05-27). Skips when the benchmark DB is unreachable.
`benchmark_session` is from conftest.py.

Documented divergences (footnoted in chapter3_4.py — all verdict-neutral / informational):
  - §3.4.1 IQR mixed n_users: report 3,597 → deterministic 3,599 (mean + all percentiles
    exact; the SKILL query's fragment-by-exact-rating GROUP BY is a bug — the report used a
    (user, class) pooled unit, reproduced here).
  - §3.4.1 collapse d's reproduce the report verdict table EXACTLY via the §3.4.1-specific
    spread-d recipe `(max−min)/sqrt(mean variance)` (`stats.spread_d`), NOT the pairwise
    `max_abs_d` the other subchapters use.
  - §3.4.2 collapse d's use pairwise-pooled `max_abs_d` (§3.1.5 recipe); the verdict WORDS
    match the report but the magnitudes carry pair-selection slips (verdict-neutral), so the
    §3.4.2 verdict test asserts collapse/review BANDS rather than exact 2-dp d's.
  - §3.4.3: only `mixed` clears the ≥30-user joint floor (the SKILL query fragments the
    score unit by exact rating). Reproduces the report row exactly.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.benchmarks import chapter3_4

pytestmark = pytest.mark.asyncio


# --- §3.4.1 Per-class score / conversion / recovery ---------------------------

# cls -> (games, users, score, conv, conv_n, recov, recov_n)
EXPECTED_341_SUMMARY = {
    1: (187177, 3655, 0.5069, 0.7117, 64242, 0.2979, 62058),
    2: (139393, 3611, 0.5094, 0.6941, 47649, 0.3253, 46300),
    3: (74055, 3487, 0.5085, 0.7391, 28648, 0.2741, 27713),
    4: (68196, 3495, 0.5076, 0.7752, 28439, 0.2346, 27400),
    5: (1060245, 3735, 0.5055, 0.6955, 408600, 0.3106, 400758),
    6: (11690, 2723, 0.5078, 0.7925, 5064, 0.1965, 4734),
}
# cls -> (n_users, mean, p10, p25, p50, p75, p90)  [mixed n 3,599 det vs 3,597 report]
EXPECTED_341_IQR = {
    1: (3075, 0.5050, 0.3740, 0.4394, 0.5000, 0.5714, 0.6389),
    2: (2841, 0.5036, 0.3506, 0.4302, 0.5076, 0.5781, 0.6484),
    3: (2353, 0.5023, 0.3333, 0.4191, 0.5000, 0.5862, 0.6641),
    4: (2303, 0.5182, 0.3222, 0.4118, 0.5208, 0.6250, 0.7080),
    5: (3599, 0.5138, 0.4184, 0.4620, 0.5101, 0.5604, 0.6145),
    6: (243, 0.4464, 0.2113, 0.3000, 0.4167, 0.5863, 0.6864),
}
# (cls, tc) -> (conv_mean, conv_p25, conv_p75, conv_n)
EXPECTED_341_CONV_TC = {
    (1, "bullet"): (0.6502, 0.5634, 0.7500, 832),
    (1, "blitz"): (0.7337, 0.6667, 0.8182, 800),
    (1, "rapid"): (0.7584, 0.6923, 0.8333, 597),
    (1, "classical"): (0.8002, 0.7431, 0.8688, 106),
    (2, "bullet"): (0.6165, 0.5147, 0.7285, 703),
    (2, "classical"): (0.8092, 0.7500, 0.8947, 87),
    (3, "rapid"): (0.8178, 0.7454, 0.9069, 263),
    (4, "classical"): (0.9156, 0.8768, 1.0000, 30),
    (5, "bullet"): (0.6559, 0.5972, 0.7194, 990),
    (5, "classical"): (0.7607, 0.6966, 0.8261, 475),
}
# (cls, tc) -> (recov_mean, recov_p25, recov_p75, recov_n)
EXPECTED_341_RECOV_TC = {
    (1, "bullet"): (0.3444, 0.2692, 0.4279, 770),
    (1, "classical"): (0.1963, 0.1333, 0.2500, 110),
    (2, "bullet"): (0.3993, 0.2941, 0.5000, 657),
    (4, "classical"): (0.0741, 0.0000, 0.0909, 35),
    (5, "rapid"): (0.2754, 0.2258, 0.3143, 929),
}
# (cls, elo) -> (conv_mean, conv_n)
EXPECTED_341_CONV_ELO = {
    (1, "800"): (0.6802, 339),
    (1, "2400"): (0.7180, 356),
    (2, "1600"): (0.7047, 508),
    (3, "1600"): (0.7639, 331),
    (4, "1200"): (0.8033, 219),
    (5, "2400"): (0.7314, 558),
}
# (cls, elo) -> (recov_mean, recov_n)
EXPECTED_341_RECOV_ELO = {
    (1, "800"): (0.3003, 322),
    (3, "800"): (0.3578, 59),
    (4, "1200"): (0.2120, 201),
    (5, "2400"): (0.3153, 551),
}
# cls -> (conv_tc_d, conv_elo_d, recov_tc_d, recov_elo_d). §3.4.1 spread-d recipe
# `(max−min)/sqrt(mean variance)` — reproduces the report's verdict table EXACTLY.
EXPECTED_341_VERDICTS: dict[int, tuple[float, float, float, float]] = {
    1: (1.24, 0.32, 1.33, 0.20),
    2: (1.50, 0.41, 1.48, 0.31),
    3: (1.40, 0.31, 1.36, 0.65),
    4: (1.43, 0.32, 1.67, 0.31),
    5: (1.19, 0.49, 1.28, 0.22),
}


async def test_341(benchmark_session: AsyncSession) -> None:
    """§3.4.1 summary + IQR + conv/recov marginals + collapse verdicts (one compute pass)."""
    v = await chapter3_4.compute_341(benchmark_session)

    summary = {s["cls"]: s for s in v["summary"]}
    for cls, (games, users, score, conv, conv_n, recov, recov_n) in EXPECTED_341_SUMMARY.items():
        s = summary[cls]
        assert (s["games"], s["users"], s["conv_n"], s["recov_n"]) == (
            games,
            users,
            conv_n,
            recov_n,
        ), cls
        assert (s["score"], s["conv"], s["recov"]) == pytest.approx((score, conv, recov)), cls

    iqr = {i["cls"]: i for i in v["iqr"]}
    for cls, (n, mean, p10, p25, p50, p75, p90) in EXPECTED_341_IQR.items():
        i = iqr[cls]
        assert i["n_users"] == n, f"iqr {cls} n"
        got = (i["mean"], i["p10"], i["p25"], i["p50"], i["p75"], i["p90"])
        assert got == pytest.approx((mean, p10, p25, p50, p75, p90)), f"iqr {cls}"

    for (cls, tc), (mean, p25, p75, n) in EXPECTED_341_CONV_TC.items():
        rs = v["conv_tc"][cls][tc]
        assert rs["n"] == n, f"conv tc {cls} {tc} n"
        assert (rs["mean"], rs["p25"], rs["p75"]) == pytest.approx((mean, p25, p75)), (
            f"conv tc {cls} {tc}"
        )
    for (cls, tc), (mean, p25, p75, n) in EXPECTED_341_RECOV_TC.items():
        rs = v["recov_tc"][cls][tc]
        assert rs["n"] == n, f"recov tc {cls} {tc} n"
        assert (rs["mean"], rs["p25"], rs["p75"]) == pytest.approx((mean, p25, p75)), (
            f"recov tc {cls} {tc}"
        )
    for (cls, elo), (mean, n) in EXPECTED_341_CONV_ELO.items():
        rs = v["conv_elo"][cls][elo]
        assert rs["n"] == n and rs["mean"] == pytest.approx(mean), f"conv elo {cls} {elo}"
    for (cls, elo), (mean, n) in EXPECTED_341_RECOV_ELO.items():
        rs = v["recov_elo"][cls][elo]
        assert rs["n"] == n and rs["mean"] == pytest.approx(mean), f"recov elo {cls} {elo}"

    by_cls = {vd["cls"]: vd for vd in v["verdicts"]}
    for cls, (ctc, celo, rtc, relo) in EXPECTED_341_VERDICTS.items():
        vd = by_cls[cls]
        assert round(vd["conv_tc_d"], 2) == ctc, f"conv tc {cls}"
        assert round(vd["conv_elo_d"], 2) == celo, f"conv elo {cls}"
        assert round(vd["recov_tc_d"], 2) == rtc, f"recov tc {cls}"
        assert round(vd["recov_elo_d"], 2) == relo, f"recov elo {cls}"


# --- §3.4.2 Per-span ΔES Score Gap by endgame type ----------------------------

# cls -> (n_users, mean, p25, p50, p75)
EXPECTED_342_POOLED = {
    1: (2841, -0.0035, -0.0508, 0.0007, 0.0475),
    2: (2332, 0.0027, -0.0479, 0.0034, 0.0560),
    3: (1417, 0.0046, -0.0384, 0.0062, 0.0499),
    4: (1307, 0.0035, -0.0424, 0.0048, 0.0538),
    5: (4587, 0.0029, -0.0307, 0.0047, 0.0379),
    6: (12, 0.0106, -0.0105, 0.0058, 0.0379),
}
# (cls, elo) -> mean
EXPECTED_342_ELO_MEAN = {
    (1, "800"): -0.0094, (1, "2400"): 0.0048,
    (2, "800"): -0.0078, (2, "2400"): 0.0165,
    (3, "2400"): 0.0099,
    (4, "800"): 0.0130,
    (5, "800"): -0.0044, (5, "2400"): 0.0158,
}  # fmt: skip
# (cls, tc) -> mean
EXPECTED_342_TC_MEAN = {
    (1, "bullet"): -0.0066, (1, "classical"): -0.0054,
    (4, "classical"): -0.0087,
    (5, "rapid"): 0.0051,
}  # fmt: skip


async def test_342(benchmark_session: AsyncSession) -> None:
    """§3.4.2 pooled IQR + ELO/TC marginal means + collapse-verdict bands (one compute pass).

    Verdict WORDS match the report; the d magnitudes carry pair-selection slips (all
    verdict-neutral — see chapter3_4 docstring). Pairwise-pooled d (§3.1.5 recipe).
    """
    v = await chapter3_4.compute_342(benchmark_session)
    pooled = {p["cls"]: p for p in v["pooled"]}
    for cls, (n, mean, p25, p50, p75) in EXPECTED_342_POOLED.items():
        p = pooled[cls]
        assert p["n"] == n, f"pooled {cls} n"
        assert (p["mean"], p["p25"], p["p50"], p["p75"]) == pytest.approx((mean, p25, p50, p75)), (
            f"pooled {cls}"
        )
    for (cls, elo), mean in EXPECTED_342_ELO_MEAN.items():
        assert v["elo"][cls][elo]["mean"] == pytest.approx(mean), f"elo {cls} {elo}"
    for (cls, tc), mean in EXPECTED_342_TC_MEAN.items():
        assert v["tc"][cls][tc]["mean"] == pytest.approx(mean), f"tc {cls} {tc}"

    # TC axis: collapse for every class (report ≈0.18; deterministic max ≈ queen 0.198 < 0.2).
    for cls in (1, 2, 3, 4, 5):
        assert v["tc_d"][cls] < 0.2, f"tc collapse {cls} (d={v['tc_d'][cls]:.3f})"
    # ELO axis: rook/pawn/queen collapse (<0.2); minor_piece/mixed review (0.2–0.5).
    for cls in (1, 3, 4):
        assert v["elo_d"][cls] < 0.2, f"elo collapse {cls} (d={v['elo_d'][cls]:.3f})"
    for cls in (2, 5):
        assert 0.2 <= v["elo_d"][cls] < 0.5, f"elo review {cls} (d={v['elo_d'][cls]:.3f})"


# --- §3.4.3 Score vs Score-Gap redundancy -------------------------------------

# Only `mixed` clears the ≥30 joined-user floor (fragmented score unit).
EXPECTED_343 = {
    "mixed": (5274, 0.105, 0.463, 0.422, 0.090, 0.149, 0.049),
}


async def test_343_matches_report(benchmark_session: AsyncSession) -> None:
    rows = await chapter3_4.compute_343(benchmark_session)
    by_cls = {r["cls"]: r for r in rows}
    assert set(by_cls) == set(EXPECTED_343)
    for cls, (n, r, sign, strict, strong, score_sd, gap_sd) in EXPECTED_343.items():
        row = by_cls[cls]
        assert row["n_users"] == n, f"{cls} n"
        got = (
            row["pearson_r"],
            row["sign_agreement"],
            row["zone_strict"],
            row["strong_disagree"],
            row["score_stdev"],
            row["gap_stdev"],
        )
        assert got == pytest.approx((r, sign, strict, strong, score_sd, gap_sd)), cls
