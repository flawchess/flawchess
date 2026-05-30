"""Numeric acceptance gate for Chapter 3 / §3.1 (3.1.1 Non-EG score, 3.1.2 EG-entry
eval, 3.1.6 score gap).

Runs the shared per_user scan against the live benchmark DB and asserts the pooled +
ELO + TC marginals and the Cohen's d verdicts match benchmarks-latest.md (2026-05-27).
Skips when the benchmark DB is unreachable. `benchmark_session` is from conftest.py.

Values are the SQL-computed proportions (4 dp), or for §3.1.2 the SQL-computed cp
(mean 2 dp, SD/percentiles 1 dp). One documented correction:
  - §3.1.1 pooled SD is 0.0876 (8.8%), not the report's stated 8.3% — a transcription
    error (all percentiles, the mean, and n match; 8.3% is below every marginal SD).
§3.1.2 reproduces the report exactly (pass 1, both pooled variants, all marginals on
n/mean/SD, and both verdicts); no transcription errors found.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.benchmarks import chapter3

pytestmark = pytest.mark.asyncio

# §3.1.1 Non-EG score. pooled SD corrected to 0.0876 (report's 8.3% is a transcription error).
EXPECTED_NON_EG_POOLED = {
    "n": 4020,
    "mean": 0.5194,
    "sd": 0.0876,
    "p05": 0.3807,
    "p25": 0.4609,
    "p50": 0.5162,
    "p75": 0.5725,
    "p95": 0.6705,
}
# label -> (n, mean, sd, p25, p50, p75)
EXPECTED_NON_EG_ELO = {
    "800": (697, 0.5194, 0.0751, 0.4678, 0.5185, 0.5663),
    "1200": (968, 0.5196, 0.0849, 0.4637, 0.5130, 0.5687),
    "1600": (1016, 0.5145, 0.0919, 0.4533, 0.5120, 0.5684),
    "2000": (839, 0.5237, 0.0907, 0.4618, 0.5197, 0.5806),
    "2400": (500, 0.5217, 0.0944, 0.4639, 0.5205, 0.5800),
}
EXPECTED_NON_EG_TC = {
    "bullet": (1238, 0.5072, 0.0843, 0.4545, 0.5080, 0.5561),
    "blitz": (1228, 0.5119, 0.0802, 0.4561, 0.5102, 0.5631),
    "rapid": (1156, 0.5306, 0.0912, 0.4672, 0.5240, 0.5851),
    "classical": (398, 0.5477, 0.0987, 0.4840, 0.5448, 0.6192),
}

# §3.1.6 Endgame score gap (eg − non_eg), proportions.
EXPECTED_DIFF_POOLED = {
    "n": 4020,
    "mean": -0.0095,
    "sd": 0.1321,
    "p05": -0.2184,
    "p25": -0.0987,
    "p50": -0.0102,
    "p75": 0.0799,
    "p95": 0.2070,
}
EXPECTED_DIFF_ELO = {
    "800": (697, -0.0235, 0.1362, -0.1167, -0.0296, 0.0635),
    "1200": (968, -0.0172, 0.1363, -0.1099, -0.0210, 0.0766),
    "1600": (1016, -0.0033, 0.1391, -0.0896, -0.0032, 0.0897),
    "2000": (839, -0.0039, 0.1237, -0.0850, -0.0036, 0.0816),
    "2400": (500, 0.0031, 0.1133, -0.0712, 0.0064, 0.0780),
}
EXPECTED_DIFF_TC = {
    "bullet": (1238, -0.0038, 0.1233, -0.0899, -0.0122, 0.0776),
    "blitz": (1228, 0.0016, 0.1249, -0.0840, 0.0010, 0.0853),
    "rapid": (1156, -0.0140, 0.1362, -0.1045, -0.0099, 0.0791),
    "classical": (398, -0.0481, 0.1581, -0.1587, -0.0469, 0.0697),
}

EXPECTED_VERDICTS = {
    "non_eg": {"TC": (("bullet", "classical"), 0.46), "ELO": (("1600", "2000"), 0.10)},
    "diff": {"TC": (("blitz", "classical"), 0.37), "ELO": (("800", "2400"), 0.21)},
}


def _check_pooled(block, expected: dict) -> None:
    pooled = block["pooled"]
    assert pooled["n"] == expected["n"]
    for key in ("mean", "sd", "p05", "p25", "p50", "p75", "p95"):
        assert pooled[key] == pytest.approx(expected[key]), key


def _check_marginal(marginals, expected: dict) -> None:
    by_label = {m["label"]: m for m in marginals}
    assert set(by_label) == set(expected)
    for label, (n, mean, sd, p25, p50, p75) in expected.items():
        d = by_label[label]["dist"]
        assert d["n"] == n, label
        assert d["mean"] == pytest.approx(mean), label
        assert d["sd"] == pytest.approx(sd), label
        assert (d["p25"], d["p50"], d["p75"]) == pytest.approx((p25, p50, p75)), label


def _check_verdicts(block, expected: dict) -> None:
    by_axis = {v["axis"]: v for v in block["verdicts"]}
    for axis, (pair, d) in expected.items():
        assert by_axis[axis]["pair"] == pair, axis
        assert round(by_axis[axis]["max_abs_d"], 2) == d, axis


async def test_chapter3_matches_report(benchmark_session: AsyncSession) -> None:
    values = await chapter3.compute(benchmark_session)

    _check_pooled(values["non_eg"], EXPECTED_NON_EG_POOLED)
    _check_marginal(values["non_eg"]["elo_marginal"], EXPECTED_NON_EG_ELO)
    _check_marginal(values["non_eg"]["tc_marginal"], EXPECTED_NON_EG_TC)
    _check_verdicts(values["non_eg"], EXPECTED_VERDICTS["non_eg"])

    _check_pooled(values["diff"], EXPECTED_DIFF_POOLED)
    _check_marginal(values["diff"]["elo_marginal"], EXPECTED_DIFF_ELO)
    _check_marginal(values["diff"]["tc_marginal"], EXPECTED_DIFF_TC)
    _check_verdicts(values["diff"], EXPECTED_VERDICTS["diff"])


# --- §3.1.2 Endgame-entry eval -------------------------------------------------

# Pass 1 — deduped symmetric EG-entry baseline (report §3.1.2 "Pass 1" table).
EXPECTED_312_BASELINE = {
    "n_games": 1604885,
    "baseline_cp_white": 10.32,
    "median_white_pov": 0.0,
    "sd_white_pov": 443.8,
    "centering_cp": 10.0,
}
# Pooled (cp): mean 2 dp, SD/percentiles 1 dp. Uncentered drives the live tile.
EXPECTED_312_POOLED_UNCENTERED = {
    "n": 8322,
    "mean": 9.29,
    "sd": 119.2,
    "p05": -185.1,
    "p25": -57.3,
    "p50": 9.7,
    "p75": 77.1,
    "p95": 199.7,
}
EXPECTED_312_POOLED_CENTERED = {
    "n": 8322,
    "mean": 9.29,
    "sd": 118.6,
    "p05": -183.4,
    "p25": -57.0,
    "p50": 10.2,
    "p75": 76.2,
    "p95": 198.6,
}
# Centered marginals: label -> (n, mean(2dp), sd, p25, p50, p75).
EXPECTED_312_ELO = {
    "800": (1359, 1.71, 163.6, -101.0, 0.6, 101.6),
    "1200": (1943, 3.63, 137.4, -77.0, 3.8, 90.7),
    "1600": (2099, 15.06, 109.5, -50.9, 15.8, 81.8),
    "2000": (1817, 15.18, 86.7, -39.9, 16.3, 66.7),
    "2400": (1104, 7.88, 67.1, -36.4, 7.0, 48.5),
}
EXPECTED_312_TC = {
    "bullet": (2563, -0.05, 144.8, -79.7, 2.2, 80.6),
    "blitz": (2521, 12.26, 99.4, -46.3, 11.5, 70.0),
    "rapid": (2406, 17.09, 104.6, -42.9, 15.6, 76.9),
    "classical": (832, 6.46, 118.8, -59.9, 8.6, 75.6),
}
EXPECTED_312_VERDICTS = {
    "TC": (("bullet", "rapid"), 0.14),
    "ELO": (("800", "2000"), 0.11),
}


def _check_dist(d, expected: dict) -> None:
    assert d["n"] == expected["n"]
    for key in ("mean", "sd", "p05", "p25", "p50", "p75", "p95"):
        assert d[key] == pytest.approx(expected[key]), key


async def test_chapter3_312_matches_report(benchmark_session: AsyncSession) -> None:
    v = await chapter3.compute_312(benchmark_session)

    b = v["baseline"]
    assert b["n_games"] == EXPECTED_312_BASELINE["n_games"]
    assert b["baseline_cp_white"] == pytest.approx(EXPECTED_312_BASELINE["baseline_cp_white"])
    assert b["median_white_pov"] == pytest.approx(EXPECTED_312_BASELINE["median_white_pov"])
    assert b["sd_white_pov"] == pytest.approx(EXPECTED_312_BASELINE["sd_white_pov"])
    assert b["centering_cp"] == EXPECTED_312_BASELINE["centering_cp"]

    _check_dist(v["pooled_uncentered"], EXPECTED_312_POOLED_UNCENTERED)
    _check_dist(v["pooled_centered"], EXPECTED_312_POOLED_CENTERED)

    _check_marginal(v["elo_marginal"], EXPECTED_312_ELO)
    _check_marginal(v["tc_marginal"], EXPECTED_312_TC)

    by_axis = {ver["axis"]: ver for ver in v["verdicts"]}
    for axis, (pair, d) in EXPECTED_312_VERDICTS.items():
        assert by_axis[axis]["pair"] == pair, axis
        assert round(by_axis[axis]["max_abs_d"], 2) == d, axis


# --- §3.1.3 Achievable Score (entry_xs) ----------------------------------------

# Proportions (4 dp). Reproduces benchmarks-latest.md §3.1.3 exactly.
EXPECTED_313_POOLED = {
    "n": 4616,
    "mean": 0.5094,
    "sd": 0.0796,
    "p05": 0.3801,
    "p25": 0.4621,
    "p50": 0.5097,
    "p75": 0.5566,
    "p95": 0.6399,
}
EXPECTED_313_ELO = {
    "800": (756, 0.5049, 0.1054, 0.4386, 0.5057, 0.5703),
    "1200": (1068, 0.5066, 0.0922, 0.4476, 0.5055, 0.5657),
    "1600": (1166, 0.5139, 0.0750, 0.4653, 0.5151, 0.5623),
    "2000": (1028, 0.5126, 0.0607, 0.4738, 0.5134, 0.5495),
    "2400": (598, 0.5060, 0.0488, 0.4757, 0.5029, 0.5333),
}
EXPECTED_313_TC = {
    "bullet": (1350, 0.5041, 0.0942, 0.4469, 0.5036, 0.5619),
    "blitz": (1353, 0.5103, 0.0676, 0.4698, 0.5109, 0.5510),
    "rapid": (1334, 0.5143, 0.0720, 0.4691, 0.5121, 0.5579),
    "classical": (579, 0.5087, 0.0845, 0.4582, 0.5069, 0.5603),
}
EXPECTED_313_VERDICTS = {
    "TC": (("bullet", "rapid"), 0.12),
    "ELO": (("1600", "2400"), 0.12),
}


async def test_chapter3_313_matches_report(benchmark_session: AsyncSession) -> None:
    block = await chapter3.compute_313(benchmark_session)
    _check_pooled(block, EXPECTED_313_POOLED)
    _check_marginal(block["elo_marginal"], EXPECTED_313_ELO)
    _check_marginal(block["tc_marginal"], EXPECTED_313_TC)
    _check_verdicts(block, EXPECTED_313_VERDICTS)
