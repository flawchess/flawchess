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


# --- §3.1.4 Endgame Score (per-user, EG-only) ----------------------------------

# Proportions (4 dp). Reproduces benchmarks-latest.md §3.1.4 exactly (a few marginal-SD
# displays land on the .5 ulp boundary, e.g. bullet 7.65% shows 7.6% in the prior report;
# the raw 4 dp values asserted here match).
EXPECTED_314_POOLED = {
    "n": 4616,
    "mean": 0.5144,
    "sd": 0.0868,
    "p05": 0.3826,
    "p25": 0.4605,
    "p50": 0.5101,
    "p75": 0.5645,
    "p95": 0.6652,
}
EXPECTED_314_ELO = {
    "800": (756, 0.4989, 0.0941, 0.4398, 0.4930, 0.5495),
    "1200": (1068, 0.5016, 0.0905, 0.4453, 0.4958, 0.5526),
    "1600": (1166, 0.5162, 0.0863, 0.4602, 0.5084, 0.5682),
    "2000": (1028, 0.5293, 0.0827, 0.4733, 0.5250, 0.5767),
    "2400": (598, 0.5281, 0.0699, 0.4871, 0.5268, 0.5659),
}
EXPECTED_314_TC = {
    "bullet": (1350, 0.5058, 0.0765, 0.4603, 0.5000, 0.5466),
    "blitz": (1353, 0.5171, 0.0817, 0.4623, 0.5155, 0.5653),
    "rapid": (1334, 0.5229, 0.0895, 0.4662, 0.5186, 0.5736),
    "classical": (579, 0.5086, 0.1095, 0.4394, 0.5020, 0.5788),
}
# First non-collapse verdicts in the report (review/review); code emits the d-values only.
# ELO pair corrected to (800, 2400): the deterministic max is |d|=0.34694 there, just above
# (800, 2000)'s 0.34679 — both round to 0.35 / "review". The prior report labeled the
# runner-up pair (800, 2000); a hand-computation pair-selection slip, same class as §2.1's
# (800,1200)→(800,1600). Magnitude and verdict word are unchanged.
EXPECTED_314_VERDICTS = {
    "TC": (("bullet", "rapid"), 0.21),
    "ELO": (("800", "2400"), 0.35),
}


async def test_chapter3_314_matches_report(benchmark_session: AsyncSession) -> None:
    block = await chapter3.compute_314(benchmark_session)
    _check_pooled(block, EXPECTED_314_POOLED)
    _check_marginal(block["elo_marginal"], EXPECTED_314_ELO)
    _check_marginal(block["tc_marginal"], EXPECTED_314_TC)
    _check_verdicts(block, EXPECTED_314_VERDICTS)


# --- §3.1.5 Achievable Score Gap (paired actual − expected) --------------------

# Proportions (4 dp), rendered as pp. Reproduces benchmarks-latest.md §3.1.5 exactly.
EXPECTED_315_POOLED = {
    "n": 4616,
    "mean": 0.0050,
    "sd": 0.0818,
    "p05": -0.1282,
    "p25": -0.0386,
    "p50": 0.0071,
    "p75": 0.0513,
    "p95": 0.1318,
}
EXPECTED_315_ELO = {
    "800": (756, -0.0060, 0.0927, -0.0581, -0.0044, 0.0445),
    "1200": (1068, -0.0050, 0.0856, -0.0468, -0.0031, 0.0417),
    "1600": (1166, 0.0022, 0.0785, -0.0385, 0.0043, 0.0463),
    "2000": (1028, 0.0167, 0.0764, -0.0282, 0.0172, 0.0605),
    "2400": (598, 0.0220, 0.0695, -0.0196, 0.0248, 0.0640),
}
EXPECTED_315_TC = {
    "bullet": (1350, 0.0017, 0.1096, -0.0601, 0.0071, 0.0722),
    "blitz": (1353, 0.0069, 0.0704, -0.0344, 0.0097, 0.0498),
    "rapid": (1334, 0.0086, 0.0631, -0.0270, 0.0074, 0.0439),
    "classical": (579, 0.0000, 0.0673, -0.0424, -0.0008, 0.0397),
}
# TC pair corrected to (rapid, classical): deterministic max |d|=0.134 is there, while
# the report's labeled (bullet, rapid) is only 0.08 — the report carried the right
# magnitude (0.13 / collapse) on the wrong pair label. ELO (800, 2400) 0.34 matches.
EXPECTED_315_VERDICTS = {
    "TC": (("rapid", "classical"), 0.13),
    "ELO": (("800", "2400"), 0.34),
}


async def test_chapter3_315_matches_report(benchmark_session: AsyncSession) -> None:
    block = await chapter3.compute_315(benchmark_session)
    _check_pooled(block, EXPECTED_315_POOLED)
    _check_marginal(block["elo_marginal"], EXPECTED_315_ELO)
    _check_marginal(block["tc_marginal"], EXPECTED_315_TC)
    _check_verdicts(block, EXPECTED_315_VERDICTS)


# --- §3.2.1 Conversion / Parity / Recovery + Endgame Skill ---------------------

# Per-user rates (proportions, 4 dp). Reproduce benchmarks-latest.md §3.2.1 exactly
# (conv/recov pooled, all marginals, and the conv/recov verdicts). The classical
# conversion mean 0.7545 displays as 75.4% (the report's 75.5% is the .5-boundary
# half-up of the same 4 dp value through render.py's float×100 — within rounding).
EXPECTED_321_CONV_POOLED = {
    "n": 4616,
    "mean": 0.7106,
    "sd": 0.1076,
    "p05": 0.5291,
    "p25": 0.6485,
    "p50": 0.7156,
    "p75": 0.7770,
    "p95": 0.8750,
}
EXPECTED_321_CONV_ELO = {
    "800": (756, 0.6783, 0.1120, 0.6131, 0.6911, 0.7500),
    "1200": (1068, 0.6999, 0.1090, 0.6375, 0.7115, 0.7684),
    "1600": (1166, 0.7171, 0.1041, 0.6571, 0.7198, 0.7826),
    "2000": (1028, 0.7254, 0.1050, 0.6667, 0.7293, 0.7902),
    "2400": (598, 0.7325, 0.0993, 0.6784, 0.7302, 0.7855),
}
EXPECTED_321_CONV_TC = {
    "bullet": (1350, 0.6519, 0.1065, 0.5882, 0.6563, 0.7188),
    "blitz": (1353, 0.7170, 0.0894, 0.6667, 0.7185, 0.7692),
    "rapid": (1334, 0.7444, 0.0938, 0.6961, 0.7464, 0.8000),
    "classical": (579, 0.7545, 0.1196, 0.6851, 0.7600, 0.8333),
}
EXPECTED_321_PAR_POOLED = {
    "n": 4616,
    "mean": 0.5069,
    "sd": 0.1280,
    "p05": 0.3016,
    "p25": 0.4402,
    "p50": 0.5000,
    "p75": 0.5734,
    "p95": 0.7143,
}
EXPECTED_321_PAR_ELO = {
    "800": (756, 0.4933, 0.1699, 0.4000, 0.5000, 0.5789),
    "1200": (1068, 0.4941, 0.1371, 0.4211, 0.5000, 0.5636),
    "1600": (1166, 0.5074, 0.1183, 0.4375, 0.5000, 0.5714),
    "2000": (1028, 0.5210, 0.1078, 0.4605, 0.5201, 0.5833),
    "2400": (598, 0.5215, 0.0920, 0.4667, 0.5196, 0.5714),
}
EXPECTED_321_PAR_TC = {
    "bullet": (1350, 0.5039, 0.1325, 0.4355, 0.5000, 0.5724),
    "blitz": (1353, 0.5078, 0.1116, 0.4477, 0.5098, 0.5688),
    "rapid": (1334, 0.5130, 0.1209, 0.4490, 0.5052, 0.5750),
    "classical": (579, 0.4977, 0.1643, 0.4043, 0.5000, 0.5909),
}
EXPECTED_321_RECOV_POOLED = {
    "n": 4616,
    "mean": 0.3081,
    "sd": 0.1117,
    "p05": 0.1429,
    "p25": 0.2397,
    "p50": 0.3000,
    "p75": 0.3696,
    "p95": 0.5000,
}
EXPECTED_321_RECOV_ELO = {
    "800": (756, 0.3129, 0.1129, 0.2389, 0.3017, 0.3729),
    "1200": (1068, 0.2991, 0.1066, 0.2333, 0.2940, 0.3600),
    "1600": (1166, 0.3030, 0.1090, 0.2336, 0.2941, 0.3636),
    "2000": (1028, 0.3099, 0.1217, 0.2364, 0.3016, 0.3750),
    "2400": (598, 0.3252, 0.1036, 0.2609, 0.3158, 0.3750),
}
EXPECTED_321_RECOV_TC = {
    "bullet": (1350, 0.3569, 0.0999, 0.2950, 0.3533, 0.4118),
    "blitz": (1353, 0.3087, 0.1008, 0.2514, 0.3000, 0.3571),
    "rapid": (1334, 0.2809, 0.1016, 0.2184, 0.2733, 0.3333),
    "classical": (579, 0.2560, 0.1368, 0.1739, 0.2353, 0.3158),
}
# conv/recov verdicts match the report exactly. Parity carries two verdict-NEUTRAL
# pair-selection slips vs the report (same class as §3.1.4/§3.1.5):
#   - TC: report labels 0.08; the true max is 0.11 (rapid vs classical). Both < 0.2 →
#     collapse. (The report's 0.08 is the blitz-vs-classical pair.)
#   - ELO: report labels (800, 2400) at 0.20; the true max is (1200, 2400) at 0.22 —
#     1200's smaller variance edges out 800. Both in [0.2, 0.5) → review.
EXPECTED_321_VERDICTS = {
    "conversion": {"TC": (("bullet", "classical"), 0.93), "ELO": (("800", "2400"), 0.51)},
    "parity": {"TC": (("rapid", "classical"), 0.11), "ELO": (("1200", "2400"), 0.22)},
    "recovery": {"TC": (("bullet", "classical"), 0.90), "ELO": (("1200", "2400"), 0.25)},
}
# Endgame Skill (composite, retracted Phase 87.4) — informational, no verdict. The report
# shows only POOLED + 800 + 2400; the generator emits full marginals (superset is fine).
EXPECTED_321_SKILL_POOLED = {
    "n": 4616,
    "mean": 0.5086,
    "sd": 0.0800,
    "p05": 0.3815,
    "p25": 0.4637,
    "p50": 0.5082,
    "p75": 0.5531,
    "p95": 0.6398,
}
EXPECTED_321_SKILL_ENDS = {
    "800": (756, 0.4948, 0.0884, 0.4474, 0.4980, 0.5462),
    "2400": (598, 0.5264, 0.0725, 0.4814, 0.5249, 0.5652),
}


async def test_chapter3_321_matches_report(benchmark_session: AsyncSession) -> None:
    v = await chapter3.compute_321(benchmark_session)

    _check_pooled(v["conversion"], EXPECTED_321_CONV_POOLED)
    _check_marginal(v["conversion"]["elo_marginal"], EXPECTED_321_CONV_ELO)
    _check_marginal(v["conversion"]["tc_marginal"], EXPECTED_321_CONV_TC)
    _check_verdicts(v["conversion"], EXPECTED_321_VERDICTS["conversion"])

    _check_pooled(v["parity"], EXPECTED_321_PAR_POOLED)
    _check_marginal(v["parity"]["elo_marginal"], EXPECTED_321_PAR_ELO)
    _check_marginal(v["parity"]["tc_marginal"], EXPECTED_321_PAR_TC)
    _check_verdicts(v["parity"], EXPECTED_321_VERDICTS["parity"])

    _check_pooled(v["recovery"], EXPECTED_321_RECOV_POOLED)
    _check_marginal(v["recovery"]["elo_marginal"], EXPECTED_321_RECOV_ELO)
    _check_marginal(v["recovery"]["tc_marginal"], EXPECTED_321_RECOV_TC)
    _check_verdicts(v["recovery"], EXPECTED_321_VERDICTS["recovery"])

    _check_dist(v["skill_pooled"], EXPECTED_321_SKILL_POOLED)
    skill_elo = {m["label"]: m for m in v["skill_elo"]}
    for label, (n, mean, sd, p25, p50, p75) in EXPECTED_321_SKILL_ENDS.items():
        d = skill_elo[label]["dist"]
        assert d["n"] == n, label
        assert d["mean"] == pytest.approx(mean), label
        assert d["sd"] == pytest.approx(sd), label
        assert (d["p25"], d["p50"], d["p75"]) == pytest.approx((p25, p50, p75)), label


# --- §3.2.2 Section-2 ΔES Score Gap (per entry-eval bucket) --------------------

# Per-span ΔES gap (proportions, 4 dp, rendered as pp). Reproduce benchmarks-latest.md
# §3.2.2 exactly (conv/recov pooled, all marginals, conv/recov verdicts).
EXPECTED_322_CONV_POOLED = {
    "n": 4138,
    "mean": -0.0617,
    "sd": 0.0955,
    "p05": -0.2473,
    "p25": -0.1101,
    "p50": -0.0481,
    "p75": 0.0019,
    "p95": 0.0690,
}
EXPECTED_322_CONV_ELO = {
    "800": (683, -0.1286, 0.0994, -0.1740, -0.1053, -0.0633),
    "1200": (973, -0.0865, 0.0929, -0.1277, -0.0652, -0.0246),
    "1600": (1048, -0.0517, 0.0857, -0.0984, -0.0384, 0.0077),
    "2000": (901, -0.0253, 0.0834, -0.0680, -0.0117, 0.0324),
    "2400": (533, -0.0117, 0.0662, -0.0518, -0.0105, 0.0354),
}
EXPECTED_322_CONV_TC = {
    "bullet": (1270, -0.1315, 0.1031, -0.1951, -0.1157, -0.0567),
    "blitz": (1254, -0.0445, 0.0754, -0.0846, -0.0403, 0.0031),
    "rapid": (1201, -0.0232, 0.0683, -0.0626, -0.0200, 0.0211),
    "classical": (413, -0.0108, 0.0709, -0.0534, -0.0010, 0.0376),
}
EXPECTED_322_PAR_POOLED = {
    "n": 3623,
    "mean": 0.0014,
    "sd": 0.0654,
    "p05": -0.1069,
    "p25": -0.0370,
    "p50": 0.0032,
    "p75": 0.0414,
    "p95": 0.1026,
}
EXPECTED_322_PAR_ELO = {
    "800": (456, -0.0067, 0.0753, -0.0559, -0.0003, 0.0451),
    "1200": (780, -0.0057, 0.0679, -0.0459, -0.0057, 0.0330),
    "1600": (948, -0.0019, 0.0655, -0.0402, -0.0014, 0.0375),
    "2000": (883, 0.0079, 0.0615, -0.0275, 0.0085, 0.0465),
    "2400": (556, 0.0134, 0.0556, -0.0203, 0.0116, 0.0477),
}
EXPECTED_322_PAR_TC = {
    "bullet": (1100, -0.0010, 0.0685, -0.0404, 0.0016, 0.0424),
    "blitz": (1163, 0.0031, 0.0617, -0.0331, 0.0043, 0.0408),
    "rapid": (1049, 0.0045, 0.0656, -0.0366, 0.0047, 0.0458),
    "classical": (311, -0.0073, 0.0659, -0.0504, -0.0042, 0.0318),
}
EXPECTED_322_RECOV_POOLED = {
    "n": 3973,
    "mean": 0.0641,
    "sd": 0.0804,
    "p05": -0.0491,
    "p25": 0.0091,
    "p50": 0.0538,
    "p75": 0.1099,
    "p95": 0.2104,
}
EXPECTED_322_RECOV_ELO = {
    "800": (670, 0.1122, 0.0854, 0.0569, 0.0950, 0.1553),
    "1200": (940, 0.0765, 0.0781, 0.0258, 0.0631, 0.1182),
    "1600": (989, 0.0518, 0.0750, -0.0011, 0.0352, 0.0938),
    "2000": (848, 0.0421, 0.0751, -0.0102, 0.0339, 0.0910),
    "2400": (526, 0.0391, 0.0638, -0.0069, 0.0357, 0.0813),
}
EXPECTED_322_RECOV_TC = {
    "bullet": (1240, 0.1294, 0.0810, 0.0739, 0.1243, 0.1770),
    "blitz": (1219, 0.0511, 0.0605, 0.0111, 0.0476, 0.0841),
    "rapid": (1123, 0.0277, 0.0552, -0.0078, 0.0260, 0.0617),
    "classical": (391, 0.0021, 0.0545, -0.0371, 0.0020, 0.0349),
}
# conv/recov verdicts match the report exactly. Parity TC carries a verdict-NEUTRAL slip:
# the report labels 0.10; the true max is 0.18 (rapid vs classical), both < 0.2 → collapse.
# Parity ELO (800, 2400) 0.31 matches the report exactly.
EXPECTED_322_VERDICTS = {
    "conversion": {"TC": (("bullet", "classical"), 1.25), "ELO": (("800", "2400"), 1.35)},
    "parity": {"TC": (("rapid", "classical"), 0.18), "ELO": (("800", "2400"), 0.31)},
    "recovery": {"TC": (("bullet", "classical"), 1.69), "ELO": (("800", "2400"), 0.95)},
}


async def test_chapter3_322_matches_report(benchmark_session: AsyncSession) -> None:
    v = await chapter3.compute_322(benchmark_session)

    _check_pooled(v["conversion"], EXPECTED_322_CONV_POOLED)
    _check_marginal(v["conversion"]["elo_marginal"], EXPECTED_322_CONV_ELO)
    _check_marginal(v["conversion"]["tc_marginal"], EXPECTED_322_CONV_TC)
    _check_verdicts(v["conversion"], EXPECTED_322_VERDICTS["conversion"])

    _check_pooled(v["parity"], EXPECTED_322_PAR_POOLED)
    _check_marginal(v["parity"]["elo_marginal"], EXPECTED_322_PAR_ELO)
    _check_marginal(v["parity"]["tc_marginal"], EXPECTED_322_PAR_TC)
    _check_verdicts(v["parity"], EXPECTED_322_VERDICTS["parity"])

    _check_pooled(v["recovery"], EXPECTED_322_RECOV_POOLED)
    _check_marginal(v["recovery"]["elo_marginal"], EXPECTED_322_RECOV_ELO)
    _check_marginal(v["recovery"]["tc_marginal"], EXPECTED_322_RECOV_TC)
    _check_verdicts(v["recovery"], EXPECTED_322_VERDICTS["recovery"])
