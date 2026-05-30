"""Numeric acceptance gate for Chapter 3 / §3.1 (3.1.1 Non-EG score, 3.1.6 score gap).

Runs the shared per_user scan against the live benchmark DB and asserts the pooled +
ELO + TC marginals and the Cohen's d verdicts match benchmarks-latest.md (2026-05-27).
Skips when the benchmark DB is unreachable. `benchmark_session` is from conftest.py.

Values are the SQL-computed proportions (4 dp). One documented correction:
  - §3.1.1 pooled SD is 0.0876 (8.8%), not the report's stated 8.3% — a transcription
    error (all percentiles, the mean, and n match; 8.3% is below every marginal SD).
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
