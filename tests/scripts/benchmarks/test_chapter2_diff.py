"""Numeric acceptance gate for Chapter 2 / §2.1 Middlegame-entry eval.

Runs both passes against the live benchmark DB and asserts the pass-1 baseline,
pooled centered distribution, ELO + TC marginals, and the Cohen's d verdict numbers
match `benchmarks-latest.md` (2026-05-27). Skips when the benchmark DB is unreachable.

`benchmark_session` is provided by conftest.py. See test_chapter1_diff.py for the
update protocol when the benchmark DB is intentionally re-ingested.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.benchmarks import chapter2

pytestmark = pytest.mark.asyncio

# Pass 1 — deduped symmetric baseline (report §2.1 "Pass 1" table).
EXPECTED_BASELINE = {
    "n_games": 2504885,
    "baseline_cp_white": 25.21,
    "median_white_pov": 24.0,
    "sd_white_pov": 237.2,
    "centering_cp": 25.0,
}

# Pass 2 pooled centered distribution (report shows percentiles as integer cp,
# mean/SD to 1 dp). Stored here as the SQL-computed values (mean 2 dp; percentiles 1 dp).
EXPECTED_POOLED = {
    "n": 9109,
    "mean": 3.65,  # displays half-up as +3.7
    "sd": 58.5,
    "p05": -91.9,  # -> −92
    "p25": -22.9,  # -> −23
    "p50": 5.7,  # -> +6
    "p75": 34.4,  # -> +34
    "p95": 89.2,  # -> +89
}

# ELO marginal: label -> (n, mean(2dp), sd(1dp)).
EXPECTED_ELO = {
    "800": (1541, -0.83, 87.9),
    "1200": (2140, 5.65, 69.3),
    "1600": (2290, 5.02, 49.6),
    "2000": (1988, 4.37, 35.2),
    "2400": (1150, 1.97, 27.5),
}
EXPECTED_TC = {
    "bullet": (2674, -2.54, 71.7),
    "blitz": (2665, 2.91, 45.1),
    "rapid": (2628, 8.45, 50.3),
    "classical": (1142, 8.83, 67.2),
}

# Collapse verdict numbers. NOTE: ELO pair is (800, 1600) — the deterministic max,
# correcting the prior report's (800, 1200) label.
EXPECTED_VERDICTS = {
    "TC": {"pair": ("bullet", "rapid"), "d": 0.18},
    "ELO": {"pair": ("800", "1600"), "d": 0.09},
}


async def test_chapter2_matches_report(benchmark_session: AsyncSession) -> None:
    values = await chapter2.compute(benchmark_session)

    b = values["baseline"]
    assert b["n_games"] == EXPECTED_BASELINE["n_games"]
    assert b["baseline_cp_white"] == pytest.approx(EXPECTED_BASELINE["baseline_cp_white"])
    assert b["median_white_pov"] == pytest.approx(EXPECTED_BASELINE["median_white_pov"])
    assert b["sd_white_pov"] == pytest.approx(EXPECTED_BASELINE["sd_white_pov"])
    assert b["centering_cp"] == EXPECTED_BASELINE["centering_cp"]

    pooled = values["pooled"]
    assert pooled["n"] == EXPECTED_POOLED["n"]
    for key in ("mean", "sd", "p05", "p25", "p50", "p75", "p95"):
        assert pooled[key] == pytest.approx(EXPECTED_POOLED[key]), key

    elo = {m["label"]: m for m in values["elo_marginal"]}
    assert set(elo) == set(EXPECTED_ELO)
    for label, (n, mean, sd) in EXPECTED_ELO.items():
        assert elo[label]["dist"]["n"] == n, label
        assert elo[label]["dist"]["mean"] == pytest.approx(mean), label
        assert elo[label]["dist"]["sd"] == pytest.approx(sd), label

    tc = {m["label"]: m for m in values["tc_marginal"]}
    assert set(tc) == set(EXPECTED_TC)
    for label, (n, mean, sd) in EXPECTED_TC.items():
        assert tc[label]["dist"]["n"] == n, label
        assert tc[label]["dist"]["mean"] == pytest.approx(mean), label
        assert tc[label]["dist"]["sd"] == pytest.approx(sd), label

    verdicts = {v["axis"]: v for v in values["verdicts"]}
    for axis, expected in EXPECTED_VERDICTS.items():
        assert verdicts[axis]["pair"] == expected["pair"], axis
        assert round(verdicts[axis]["max_abs_d"], 2) == expected["d"], axis
