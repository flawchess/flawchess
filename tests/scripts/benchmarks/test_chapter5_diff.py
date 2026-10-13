"""Numeric acceptance gate for Chapter 5 / §5 (flaw-delta and tactic-delta zones).

Runs chapter5.compute() against the live benchmark DB and asserts, for the 12 flaw metrics,
the pooled + ELO + TC marginals and Cohen's d verdicts, and for the 38 tactic metrics the
pooled (n, p25, p50, p75) and the verdicts, plus the zone_viable set. Skips when the benchmark
DB is unreachable. `benchmark_session` is from conftest.py.

Basis (Phase 239, plan 239-06): the full-analysis lane only (classical + rapid tranches of
`benchmark_selection`, armed, full evals + PVs + blobs), 12 flaw + 38 tactic metrics.
Snapshot: 2026-10-12T21:01Z (one run of `python -m scripts.benchmarks.chapter5`; lane status at
that moment: classical 99.9% and rapid 99.9% complete; 138,104 analyzed games across 2,006
user-cells and 1,590 distinct users). The lane is still finishing a handful of stragglers (the
benchmark DB is not static), so a late-finishing game can move these numbers by a hair; if the
gate drifts by a hair after a lane refresh, re-run the fast path and regenerate this file from
the same run that the report narrates (Pitfall 5).

The EXPECTED_* dicts below use the same shape as test_chapter3_diff.py:
  - pooled: {n, mean, sd, p05, p25, p50, p75, p95}  (6 dp, proportion scale)
  - ELO/TC: label -> (n, mean, sd, p25, p50, p75)   (6 dp, proportion scale)
  - verdicts: metric -> {axis: ((a, b), max_abs_d)}
  - tactic pooled: metric -> (n, p25, p50, p75)      (6 dp, per-game count difference, NOT x100)

NOTE: Flaw values are in proportion units (NOT x100). The rendered "pp" values in the report
are these values multiplied by 100. E.g. blunder pooled p50 = -0.002134 renders as -0.21pp. The
double-x100 bug (Phase 114 fix) would cause a p50 100x larger. The render-layer guard test catches
this. Tactic values are per-game count differences; the "per 100 games" report values are x100.

All-analyzed-games basis (Phase 114 final fix): the per_game_tags CTE uses base_games LEFT JOIN
game_flaws so clean games (zero detected flaws) contribute a 0 delta.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.benchmarks import chapter5, distribution as dist

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Check helpers (verbatim from test_chapter3_diff.py)
# ---------------------------------------------------------------------------


def _check_pooled(block: chapter5.MetricBlock, expected: dict[str, Any]) -> None:
    pooled = block["pooled"]
    assert pooled["n"] == expected["n"]
    for key in ("mean", "sd", "p05", "p25", "p50", "p75", "p95"):
        assert pooled[key] == pytest.approx(expected[key]), key


def _check_marginal(marginals: list[dist.Marginal], expected: dict[str, Any]) -> None:
    by_label = {m["label"]: m for m in marginals}
    assert set(by_label) == set(expected)
    for label, (n, mean, sd, p25, p50, p75) in expected.items():
        d = by_label[label]["dist"]
        assert d["n"] == n, label
        assert d["mean"] == pytest.approx(mean), label
        assert d["sd"] == pytest.approx(sd), label
        assert (d["p25"], d["p50"], d["p75"]) == pytest.approx((p25, p50, p75)), label


def _check_verdicts(block: chapter5.MetricBlock, expected: dict[str, Any]) -> None:
    # block["verdicts"] only holds the axes whose verdict could be computed (a level below the
    # cell floor can leave an axis with fewer than two eligible levels), so look axes up by name.
    by_axis = {v["axis"]: v for v in block["verdicts"]}
    assert set(by_axis) == set(expected), "verdict axes differ from the recorded run"
    for axis, (pair, d) in expected.items():
        assert tuple(by_axis[axis]["pair"]) == pair, axis
        assert round(by_axis[axis]["max_abs_d"], 2) == d, axis


# One compute() per test session: each call scans the benchmark DB for about a minute, and the
# result is plain data that does not depend on the (function-scoped) session it was fetched with.
_VALUES_CACHE: list[chapter5.Chapter5Values] = []


async def _values(session: AsyncSession) -> chapter5.Chapter5Values:
    if not _VALUES_CACHE:
        _VALUES_CACHE.append(await chapter5.compute(session))
    return _VALUES_CACHE[0]


# ---------------------------------------------------------------------------
# Expected values, flaw metrics (12). All values are proportions: multiply by 100 for "pp".
# ---------------------------------------------------------------------------

EXPECTED_MISTAKE_POOLED = {
    "n": 2004,
    "mean": -0.001254,
    "sd": 0.009425,
    "p05": -0.015266,
    "p25": -0.006515,
    "p50": -0.001356,
    "p75": 0.003897,
    "p95": 0.013423,
}
EXPECTED_MISTAKE_ELO = {
    "800": (354, 1e-06, 0.013065, -0.007045, -0.000608, 0.006596),
    "1200": (503, -0.001457, 0.010853, -0.00792, -0.001625, 0.005187),
    "1600": (549, -0.001365, 0.00762, -0.005575, -0.001316, 0.00349),
    "2000": (436, -0.001785, 0.006938, -0.006203, -0.001513, 0.002688),
    "2400": (162, -0.001558, 0.0056, -0.005395, -0.001152, 0.001868),
}
EXPECTED_MISTAKE_TC = {
    "rapid": (1271, -0.001237, 0.008531, -0.0063, -0.0015, 0.003711),
    "classical": (733, -0.001283, 0.010806, -0.006902, -0.001055, 0.004394),
}

EXPECTED_BLUNDER_POOLED = {
    "n": 2004,
    "mean": -0.002775,
    "sd": 0.010058,
    "p05": -0.019493,
    "p25": -0.008256,
    "p50": -0.002134,
    "p75": 0.003069,
    "p95": 0.012279,
}
EXPECTED_BLUNDER_ELO = {
    "800": (354, -0.003013, 0.012521, -0.010845, -0.001627, 0.004788),
    "1200": (503, -0.003626, 0.011932, -0.010432, -0.00332, 0.003221),
    "1600": (549, -0.002112, 0.009085, -0.007237, -0.001814, 0.00344),
    "2000": (436, -0.002553, 0.007596, -0.007205, -0.002118, 0.002094),
    "2400": (162, -0.002461, 0.005468, -0.006085, -0.002144, 0.00108),
}
EXPECTED_BLUNDER_TC = {
    "rapid": (1271, -0.00224, 0.009228, -0.00778, -0.001961, 0.003107),
    "classical": (733, -0.003704, 0.0113, -0.009705, -0.002568, 0.003047),
}

EXPECTED_LOW_CLOCK_POOLED = {
    "n": 2004,
    "mean": 7.5e-05,
    "sd": 0.003237,
    "p05": -0.003847,
    "p25": -0.001177,
    "p50": 0.0,
    "p75": 0.000496,
    "p95": 0.00549,
}
EXPECTED_LOW_CLOCK_ELO = {
    "800": (354, 0.000111, 0.001922, -0.000526, 0.0, 0.0),
    "1200": (503, -3.9e-05, 0.002001, -0.000724, 0.0, 0.0),
    "1600": (549, 0.000344, 0.003426, -0.001085, -7.3e-05, 0.000621),
    "2000": (436, 6.8e-05, 0.004462, -0.002018, -0.000375, 0.001458),
    "2400": (162, -0.000542, 0.003917, -0.003025, -0.000802, 0.001528),
}
EXPECTED_LOW_CLOCK_TC = {
    "rapid": (1271, 4.3e-05, 0.003225, -0.001373, -0.000228, 0.000767),
    "classical": (733, 0.000132, 0.003259, -0.000737, 0.0, 0.0),
}

EXPECTED_HASTY_POOLED = {
    "n": 2004,
    "mean": -0.00372,
    "sd": 0.0158,
    "p05": -0.029829,
    "p25": -0.011507,
    "p50": -0.003519,
    "p75": 0.004424,
    "p95": 0.021855,
}
EXPECTED_HASTY_ELO = {
    "800": (354, -0.005808, 0.022358, -0.019961, -0.006211, 0.007651),
    "1200": (503, -0.005602, 0.019808, -0.01675, -0.007282, 0.007409),
    "1600": (549, -0.003116, 0.012573, -0.011449, -0.003246, 0.004318),
    "2000": (436, -0.001729, 0.008029, -0.006988, -0.002371, 0.002487),
    "2400": (162, -0.000722, 0.00568, -0.004714, -0.00112, 0.003066),
}
EXPECTED_HASTY_TC = {
    "rapid": (1271, -0.002494, 0.012498, -0.009644, -0.002981, 0.004335),
    "classical": (733, -0.005846, 0.020123, -0.016509, -0.004997, 0.005299),
}

EXPECTED_UNRUSHED_POOLED = {
    "n": 2004,
    "mean": -0.00038,
    "sd": 0.015172,
    "p05": -0.02308,
    "p25": -0.00939,
    "p50": -0.001016,
    "p75": 0.007331,
    "p95": 0.026525,
}
EXPECTED_UNRUSHED_ELO = {
    "800": (354, 0.002701, 0.019528, -0.008914, 0.002296, 0.013095),
    "1200": (503, 0.000571, 0.018481, -0.011468, -0.000426, 0.010961),
    "1600": (549, -0.000714, 0.013176, -0.009292, -0.000557, 0.006381),
    "2000": (436, -0.00268, 0.009738, -0.008511, -0.002037, 0.003456),
    "2400": (162, -0.002748, 0.008467, -0.007828, -0.002121, 0.002178),
}
EXPECTED_UNRUSHED_TC = {
    "rapid": (1271, -0.001009, 0.01315, -0.008602, -0.001217, 0.006639),
    "classical": (733, 0.000709, 0.018112, -0.010852, -0.000426, 0.009276),
}

EXPECTED_OPENING_POOLED = {
    "n": 2004,
    "mean": -0.002045,
    "sd": 0.010075,
    "p05": -0.018915,
    "p25": -0.005947,
    "p50": -0.001429,
    "p75": 0.002685,
    "p95": 0.012624,
}
EXPECTED_OPENING_ELO = {
    "800": (354, -0.003101, 0.01536, -0.010657, -0.00299, 0.006027),
    "1200": (503, -0.003712, 0.01231, -0.01021, -0.003226, 0.003634),
    "1600": (549, -0.001309, 0.007248, -0.004973, -0.001409, 0.002689),
    "2000": (436, -0.000503, 0.004857, -0.00314, -0.000551, 0.002011),
    "2400": (162, -0.001205, 0.003212, -0.00272, -0.000863, 0.000715),
}
EXPECTED_OPENING_TC = {
    "rapid": (1271, -0.001311, 0.008463, -0.005069, -0.00105, 0.002563),
    "classical": (733, -0.003318, 0.012285, -0.008287, -0.002278, 0.002865),
}

EXPECTED_MIDDLEGAME_POOLED = {
    "n": 2004,
    "mean": -0.001626,
    "sd": 0.007887,
    "p05": -0.014941,
    "p25": -0.006161,
    "p50": -0.001081,
    "p75": 0.003407,
    "p95": 0.010345,
}
EXPECTED_MIDDLEGAME_ELO = {
    "800": (354, -0.000205, 0.007784, -0.004459, 0.000192, 0.004862),
    "1200": (503, -0.00129, 0.008132, -0.006018, -0.000214, 0.003762),
    "1600": (549, -0.001872, 0.007959, -0.006648, -0.001458, 0.003423),
    "2000": (436, -0.002832, 0.007883, -0.007084, -0.00257, 0.002028),
    "2400": (162, -0.001693, 0.00651, -0.005421, -0.001042, 0.002409),
}
EXPECTED_MIDDLEGAME_TC = {
    "rapid": (1271, -0.001693, 0.007689, -0.006172, -0.001354, 0.003235),
    "classical": (733, -0.00151, 0.008222, -0.006054, -0.000627, 0.003684),
}

EXPECTED_ENDGAME_PHASE_POOLED = {
    "n": 2004,
    "mean": -0.000358,
    "sd": 0.003589,
    "p05": -0.006569,
    "p25": -0.002331,
    "p50": -0.000215,
    "p75": 0.001799,
    "p95": 0.005278,
}
EXPECTED_ENDGAME_PHASE_ELO = {
    "800": (354, 0.000295, 0.00299, -0.00157, 7.8e-05, 0.002025),
    "1200": (503, -8e-05, 0.003631, -0.001936, 0.000173, 0.001868),
    "1600": (549, -0.000296, 0.003555, -0.002341, -6e-05, 0.001917),
    "2000": (436, -0.001003, 0.003879, -0.003, -0.000704, 0.001372),
    "2400": (162, -0.00112, 0.003608, -0.003564, -0.001128, 0.001156),
}
EXPECTED_ENDGAME_PHASE_TC = {
    "rapid": (1271, -0.000473, 0.003602, -0.002481, -0.000358, 0.001767),
    "classical": (733, -0.000159, 0.003561, -0.002052, 0.000118, 0.001901),
}

EXPECTED_MISS_POOLED = {
    "n": 2004,
    "mean": -0.000215,
    "sd": 0.005411,
    "p05": -0.008561,
    "p25": -0.003136,
    "p50": -0.000145,
    "p75": 0.002703,
    "p95": 0.007948,
}
EXPECTED_MISS_ELO = {
    "800": (354, -0.000434, 0.008117, -0.004652, -0.000271, 0.004151),
    "1200": (503, -0.000228, 0.005991, -0.00389, -0.000324, 0.003277),
    "1600": (549, -0.000128, 0.004408, -0.002898, -8.4e-05, 0.00251),
    "2000": (436, -0.000303, 0.003499, -0.002643, -0.000132, 0.001755),
    "2400": (162, 0.000246, 0.002877, -0.001247, 9e-05, 0.001942),
}
EXPECTED_MISS_TC = {
    "rapid": (1271, -0.000255, 0.004844, -0.002896, -0.000145, 0.00257),
    "classical": (733, -0.000146, 0.006276, -0.003416, -0.000145, 0.003051),
}

EXPECTED_LUCKY_POOLED = {
    "n": 2004,
    "mean": 0.000185,
    "sd": 0.00466,
    "p05": -0.006849,
    "p25": -0.002234,
    "p50": 2.1e-05,
    "p75": 0.002509,
    "p95": 0.007363,
}
EXPECTED_LUCKY_ELO = {
    "800": (354, 0.000426, 0.007142, -0.003621, 0.000757, 0.003916),
    "1200": (503, 0.000342, 0.005295, -0.002833, 6.6e-05, 0.003344),
    "1600": (549, 4.2e-05, 0.003708, -0.002095, -8.5e-05, 0.002259),
    "2000": (436, 0.0001, 0.00256, -0.001526, -5e-05, 0.001661),
    "2400": (162, -0.000108, 0.002455, -0.001507, -0.000157, 0.001156),
}
EXPECTED_LUCKY_TC = {
    "rapid": (1271, 6.4e-05, 0.004003, -0.00224, -5.8e-05, 0.00223),
    "classical": (733, 0.000396, 0.005618, -0.002231, 0.000246, 0.002921),
}

EXPECTED_REVERSED_POOLED = {
    "n": 2004,
    "mean": -0.00014,
    "sd": 0.002512,
    "p05": -0.00421,
    "p25": -0.001157,
    "p50": -6.9e-05,
    "p75": 0.001009,
    "p95": 0.003489,
}
EXPECTED_REVERSED_ELO = {
    "800": (354, -0.000446, 0.004156, -0.002706, -0.000212, 0.001833),
    "1200": (503, -5.5e-05, 0.002855, -0.001788, -5e-05, 0.001546),
    "1600": (549, -6.3e-05, 0.0017, -0.001034, -5e-05, 0.000895),
    "2000": (436, -7.6e-05, 0.001267, -0.000766, 0.0, 0.000699),
    "2400": (162, -0.000166, 0.000897, -0.000583, -0.000118, 0.000277),
}
EXPECTED_REVERSED_TC = {
    "rapid": (1271, -0.000145, 0.002303, -0.001166, -7e-05, 0.000931),
    "classical": (733, -0.000131, 0.002841, -0.001135, -5.1e-05, 0.001111),
}

EXPECTED_SQUANDERED_POOLED = {
    "n": 2004,
    "mean": 0.000112,
    "sd": 0.003332,
    "p05": -0.005328,
    "p25": -0.001657,
    "p50": 0.000144,
    "p75": 0.0019,
    "p95": 0.005191,
}
EXPECTED_SQUANDERED_ELO = {
    "800": (354, 1.8e-05, 0.005076, -0.003043, 1.4e-05, 0.003167),
    "1200": (503, 0.000139, 0.00363, -0.002002, 0.000268, 0.002225),
    "1600": (549, 0.000148, 0.002618, -0.001375, 0.000215, 0.001839),
    "2000": (436, 0.000173, 0.002231, -0.001222, 0.000182, 0.001639),
    "2400": (162, -5.3e-05, 0.00192, -0.00098, -0.000134, 0.001032),
}
EXPECTED_SQUANDERED_TC = {
    "rapid": (1271, 0.000154, 0.003075, -0.001555, 0.000198, 0.001906),
    "classical": (733, 3.9e-05, 0.003737, -0.001846, 9.9e-05, 0.001897),
}

# Verdicts: metric -> {axis: ((level_a, level_b), max_abs_d_rounded_2dp)}
# Cohen's d is scale-invariant. The TC axis has only two levels (rapid vs classical).
EXPECTED_VERDICTS: dict[str, dict[str, tuple[tuple[str, str], float]]] = {
    "mistake": {"TC": (("rapid", "classical"), 0.0), "ELO": (("800", "2000"), 0.18)},
    "blunder": {"TC": (("rapid", "classical"), 0.15), "ELO": (("1200", "1600"), 0.14)},
    "low_clock": {"TC": (("rapid", "classical"), 0.03), "ELO": (("1600", "2400"), 0.25)},
    "hasty": {"TC": (("rapid", "classical"), 0.21), "ELO": (("1200", "2400"), 0.28)},
    "unrushed": {"TC": (("rapid", "classical"), 0.11), "ELO": (("800", "2000"), 0.36)},
    "opening": {"TC": (("rapid", "classical"), 0.2), "ELO": (("1200", "2000"), 0.33)},
    "middlegame": {"TC": (("rapid", "classical"), 0.02), "ELO": (("800", "2000"), 0.34)},
    "endgame_phase": {"TC": (("rapid", "classical"), 0.09), "ELO": (("800", "2400"), 0.44)},
    "miss": {"TC": (("rapid", "classical"), 0.02), "ELO": (("2000", "2400"), 0.16)},
    "lucky": {"TC": (("rapid", "classical"), 0.07), "ELO": (("1200", "2400"), 0.09)},
    "reversed": {"TC": (("rapid", "classical"), 0.01), "ELO": (("800", "1600"), 0.13)},
    "squandered": {"TC": (("rapid", "classical"), 0.03), "ELO": (("2000", "2400"), 0.11)},
}

# Per-metric (pooled_dict, elo_dict, tc_dict) references for the test loop.
_EXPECTED_BY_METRIC: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = {
    "mistake": (EXPECTED_MISTAKE_POOLED, EXPECTED_MISTAKE_ELO, EXPECTED_MISTAKE_TC),
    "blunder": (EXPECTED_BLUNDER_POOLED, EXPECTED_BLUNDER_ELO, EXPECTED_BLUNDER_TC),
    "low_clock": (EXPECTED_LOW_CLOCK_POOLED, EXPECTED_LOW_CLOCK_ELO, EXPECTED_LOW_CLOCK_TC),
    "hasty": (EXPECTED_HASTY_POOLED, EXPECTED_HASTY_ELO, EXPECTED_HASTY_TC),
    "unrushed": (EXPECTED_UNRUSHED_POOLED, EXPECTED_UNRUSHED_ELO, EXPECTED_UNRUSHED_TC),
    "opening": (EXPECTED_OPENING_POOLED, EXPECTED_OPENING_ELO, EXPECTED_OPENING_TC),
    "middlegame": (EXPECTED_MIDDLEGAME_POOLED, EXPECTED_MIDDLEGAME_ELO, EXPECTED_MIDDLEGAME_TC),
    "endgame_phase": (
        EXPECTED_ENDGAME_PHASE_POOLED,
        EXPECTED_ENDGAME_PHASE_ELO,
        EXPECTED_ENDGAME_PHASE_TC,
    ),
    "miss": (EXPECTED_MISS_POOLED, EXPECTED_MISS_ELO, EXPECTED_MISS_TC),
    "lucky": (EXPECTED_LUCKY_POOLED, EXPECTED_LUCKY_ELO, EXPECTED_LUCKY_TC),
    "reversed": (EXPECTED_REVERSED_POOLED, EXPECTED_REVERSED_ELO, EXPECTED_REVERSED_TC),
    "squandered": (EXPECTED_SQUANDERED_POOLED, EXPECTED_SQUANDERED_ELO, EXPECTED_SQUANDERED_TC),
}

# ---------------------------------------------------------------------------
# Expected values, tactic metrics (38 = 19 families x missed/allowed).
# Per-game count difference (player - opponent), per-user mean over >= 20 games.
# ---------------------------------------------------------------------------

EXPECTED_TACTIC_POOLED: dict[str, tuple[int, float, float, float]] = {
    "tactic_fork_missed": (2004, -0.022039, 0.0, 0.021277),
    "tactic_fork_allowed": (2004, -0.041131, 0.0, 0.032258),
    "tactic_skewer_missed": (2004, 0.0, 0.0, 0.0),
    "tactic_skewer_allowed": (2004, 0.0, 0.0, 0.0),
    "tactic_pin_missed": (2004, -0.014135, 0.0, 0.018868),
    "tactic_pin_allowed": (2004, -0.028571, 0.0, 0.020408),
    "tactic_x_ray_missed": (2004, 0.0, 0.0, 0.0),
    "tactic_x_ray_allowed": (2004, 0.0, 0.0, 0.0),
    "tactic_double_check_missed": (2004, 0.0, 0.0, 0.0),
    "tactic_double_check_allowed": (2004, 0.0, 0.0, 0.0),
    "tactic_discovered_check_missed": (2004, 0.0, 0.0, 0.0),
    "tactic_discovered_check_allowed": (2004, -0.01, 0.0, 0.01),
    "tactic_discovered_attack_missed": (2004, 0.0, 0.0, 0.0),
    "tactic_discovered_attack_allowed": (2004, -0.012346, 0.0, 0.010554),
    "tactic_trapped_piece_missed": (2004, 0.0, 0.0, 0.0),
    "tactic_trapped_piece_allowed": (2004, 0.0, 0.0, 0.0025),
    "tactic_hanging_missed": (2004, -0.011268, 0.0, 0.014761),
    "tactic_hanging_allowed": (2004, -0.05102, -0.01, 0.030303),
    "tactic_mate_missed": (2004, -0.021739, 0.0, 0.028986),
    "tactic_mate_allowed": (2004, -0.07, -0.011629, 0.040886),
    "tactic_deflection_missed": (2004, 0.0, 0.0, 0.0),
    "tactic_deflection_allowed": (2004, -0.01, 0.0, 0.01),
    "tactic_intermezzo_missed": (2004, 0.0, 0.0, 0.0),
    "tactic_intermezzo_allowed": (2004, 0.0, 0.0, 0.0),
    "tactic_interference_missed": (2004, 0.0, 0.0, 0.0),
    "tactic_interference_allowed": (2004, 0.0, 0.0, 0.0),
    "tactic_capturing_defender_missed": (2004, 0.0, 0.0, 0.0),
    "tactic_capturing_defender_allowed": (2004, 0.0, 0.0, 0.0),
    "tactic_attraction_missed": (2004, 0.0, 0.0, 0.0),
    "tactic_attraction_allowed": (2004, -0.010101, 0.0, 0.01),
    "tactic_sacrifice_missed": (2004, 0.0, 0.0, 0.0),
    "tactic_sacrifice_allowed": (2004, 0.0, 0.0, 0.0),
    "tactic_en_passant_missed": (2004, 0.0, 0.0, 0.0),
    "tactic_en_passant_allowed": (2004, 0.0, 0.0, 0.0),
    "tactic_under_promotion_missed": (2004, 0.0, 0.0, 0.0),
    "tactic_under_promotion_allowed": (2004, 0.0, 0.0, 0.0),
    "tactic_promotion_missed": (2004, 0.0, 0.0, 0.0),
    "tactic_promotion_allowed": (2004, 0.0, 0.0, 0.0),
}

# Verdicts for every tactic metric (the TC axis is rapid vs classical).
EXPECTED_TACTIC_VERDICTS: dict[str, dict[str, tuple[tuple[str, str], float]]] = {
    "tactic_fork_missed": {"TC": (("rapid", "classical"), 0.04), "ELO": (("800", "1600"), 0.05)},
    "tactic_fork_allowed": {"TC": (("rapid", "classical"), 0.01), "ELO": (("800", "2000"), 0.14)},
    "tactic_skewer_missed": {"TC": (("rapid", "classical"), 0.05), "ELO": (("800", "1600"), 0.04)},
    "tactic_skewer_allowed": {
        "TC": (("rapid", "classical"), 0.04),
        "ELO": (("1600", "2000"), 0.07),
    },
    "tactic_pin_missed": {"TC": (("rapid", "classical"), 0.04), "ELO": (("1600", "2400"), 0.08)},
    "tactic_pin_allowed": {"TC": (("rapid", "classical"), 0.05), "ELO": (("800", "1600"), 0.12)},
    "tactic_x_ray_missed": {"TC": (("rapid", "classical"), 0.02), "ELO": (("1600", "2400"), 0.1)},
    "tactic_x_ray_allowed": {"TC": (("rapid", "classical"), 0.02), "ELO": (("1200", "2400"), 0.1)},
    "tactic_double_check_missed": {
        "TC": (("rapid", "classical"), 0.06),
        "ELO": (("800", "1600"), 0.08),
    },
    "tactic_double_check_allowed": {
        "TC": (("rapid", "classical"), 0.0),
        "ELO": (("1600", "2000"), 0.11),
    },
    "tactic_discovered_check_missed": {
        "TC": (("rapid", "classical"), 0.01),
        "ELO": (("1200", "2400"), 0.12),
    },
    "tactic_discovered_check_allowed": {
        "TC": (("rapid", "classical"), 0.06),
        "ELO": (("800", "1200"), 0.06),
    },
    "tactic_discovered_attack_missed": {
        "TC": (("rapid", "classical"), 0.01),
        "ELO": (("800", "2400"), 0.09),
    },
    "tactic_discovered_attack_allowed": {
        "TC": (("rapid", "classical"), 0.01),
        "ELO": (("800", "1200"), 0.08),
    },
    "tactic_trapped_piece_missed": {
        "TC": (("rapid", "classical"), 0.06),
        "ELO": (("2000", "2400"), 0.22),
    },
    "tactic_trapped_piece_allowed": {
        "TC": (("rapid", "classical"), 0.05),
        "ELO": (("800", "2000"), 0.18),
    },
    "tactic_hanging_missed": {"TC": (("rapid", "classical"), 0.0), "ELO": (("2000", "2400"), 0.2)},
    "tactic_hanging_allowed": {
        "TC": (("rapid", "classical"), 0.05),
        "ELO": (("800", "1600"), 0.15),
    },
    "tactic_mate_missed": {"TC": (("rapid", "classical"), 0.06), "ELO": (("1600", "2000"), 0.14)},
    "tactic_mate_allowed": {"TC": (("rapid", "classical"), 0.03), "ELO": (("800", "1600"), 0.06)},
    "tactic_deflection_missed": {
        "TC": (("rapid", "classical"), 0.04),
        "ELO": (("1200", "2400"), 0.23),
    },
    "tactic_deflection_allowed": {
        "TC": (("rapid", "classical"), 0.06),
        "ELO": (("1200", "2400"), 0.23),
    },
    "tactic_intermezzo_missed": {
        "TC": (("rapid", "classical"), 0.03),
        "ELO": (("1200", "2400"), 0.15),
    },
    "tactic_intermezzo_allowed": {
        "TC": (("rapid", "classical"), 0.07),
        "ELO": (("1600", "2400"), 0.22),
    },
    "tactic_interference_missed": {
        "TC": (("rapid", "classical"), 0.09),
        "ELO": (("1600", "2400"), 0.12),
    },
    "tactic_interference_allowed": {
        "TC": (("rapid", "classical"), 0.03),
        "ELO": (("1600", "2000"), 0.15),
    },
    "tactic_capturing_defender_missed": {
        "TC": (("rapid", "classical"), 0.04),
        "ELO": (("2000", "2400"), 0.28),
    },
    "tactic_capturing_defender_allowed": {
        "TC": (("rapid", "classical"), 0.05),
        "ELO": (("1200", "2400"), 0.23),
    },
    "tactic_attraction_missed": {
        "TC": (("rapid", "classical"), 0.07),
        "ELO": (("2000", "2400"), 0.1),
    },
    "tactic_attraction_allowed": {
        "TC": (("rapid", "classical"), 0.13),
        "ELO": (("2000", "2400"), 0.11),
    },
    "tactic_sacrifice_missed": {
        "TC": (("rapid", "classical"), 0.01),
        "ELO": (("800", "2400"), 0.11),
    },
    "tactic_sacrifice_allowed": {
        "TC": (("rapid", "classical"), 0.04),
        "ELO": (("800", "2400"), 0.11),
    },
    "tactic_en_passant_missed": {
        "TC": (("rapid", "classical"), 0.01),
        "ELO": (("800", "2000"), 0.08),
    },
    "tactic_en_passant_allowed": {
        "TC": (("rapid", "classical"), 0.05),
        "ELO": (("800", "2400"), 0.24),
    },
    "tactic_under_promotion_missed": {
        "TC": (("rapid", "classical"), 0.07),
        "ELO": (("800", "2000"), 0.1),
    },
    "tactic_under_promotion_allowed": {
        "TC": (("rapid", "classical"), 0.04),
        "ELO": (("800", "1200"), 0.1),
    },
    "tactic_promotion_missed": {
        "TC": (("rapid", "classical"), 0.07),
        "ELO": (("1200", "1600"), 0.12),
    },
    "tactic_promotion_allowed": {
        "TC": (("rapid", "classical"), 0.05),
        "ELO": (("2000", "2400"), 0.09),
    },
}

# The zone_viable set (pooled IQR not degenerate AND pct_nonzero >= 50) over all 50 metrics.
# zone_viable decides has_zone for a tactic metric in the registry (plan 239-07).
EXPECTED_ZONE_VIABLE: frozenset[str] = frozenset(
    {
        "blunder",
        "endgame_phase",
        "hasty",
        "low_clock",
        "lucky",
        "middlegame",
        "miss",
        "mistake",
        "opening",
        "reversed",
        "squandered",
        "tactic_discovered_attack_allowed",
        "tactic_fork_allowed",
        "tactic_fork_missed",
        "tactic_hanging_allowed",
        "tactic_hanging_missed",
        "tactic_mate_allowed",
        "tactic_mate_missed",
        "tactic_pin_allowed",
        "tactic_pin_missed",
        "unrushed",
    }
)


async def test_chapter5_render_scale_guard(benchmark_session: AsyncSession) -> None:
    """Render-layer regression guard: catches double-x100 scaling bugs.

    The D-01 estimator emits proportion-scale values from SQL (e.g. blunder p50 = -0.002134).
    The 'pp' render unit multiplies by 100 to display per-100-moves values (e.g. -0.21pp).
    If someone re-introduces x100 in the SQL (the bug fixed in Phase 114), the rendered
    blunder pooled p50 would jump to ~-21pp or worse, which is caught here.

    Guard: blunder pooled p50 rendered as pp must be in the plausible range (-2.0, 2.0).
    """
    values = await _values(benchmark_session)
    block = values["flaw"]["blunder"]
    pooled = block["pooled"]

    # Rendered p50: proportion value x 100 (the "pp" unit scale factor).
    rendered_p50_pp = float(pooled["p50"]) * 100

    assert abs(rendered_p50_pp) < 2.0, (
        f"blunder pooled p50 rendered as {rendered_p50_pp:.4f}pp, expected < 2.0pp in abs. "
        f"Raw SQL value: {pooled['p50']}. "
        "If this is ~100x larger, the SQL-side x100 double-scaling bug was reintroduced."
    )

    # Also verify the rendered pooled table string contains a plausible 'pp' value.
    rendered_table = dist.pooled_table(pooled, "pp")
    # The table must contain a 'pp' suffix (confirms the render path was exercised).
    assert "pp" in rendered_table, "pooled_table with unit='pp' must produce 'pp'-suffixed values"


async def test_chapter5_flaw_delta(benchmark_session: AsyncSession) -> None:
    """Numeric diff gate for all 12 flaw-delta metrics.

    Asserts pooled + ELO + TC marginals and Cohen's d verdicts for every metric.
    Also checks that the viability list has one entry per metric with users_total > 0.
    """
    values = await _values(benchmark_session)
    assert set(values["flaw"]) == set(_EXPECTED_BY_METRIC)

    for metric_key, (exp_pooled, exp_elo, exp_tc) in _EXPECTED_BY_METRIC.items():
        block = values["flaw"][metric_key]
        _check_pooled(block, exp_pooled)
        _check_marginal(block["elo_marginal"], exp_elo)
        _check_marginal(block["tc_marginal"], exp_tc)
        _check_verdicts(block, EXPECTED_VERDICTS[metric_key])

    # Viability sanity: one entry per metric, all users_total > 0.
    viability = values["viability"]
    assert len(viability) == len(chapter5.FLAW_DELTA_METRICS) + len(values["tactic"])
    for row in viability:
        assert row["users_total"] > 0, f"viability users_total == 0 for metric={row['metric']}"


async def test_chapter5_tactic_delta(benchmark_session: AsyncSession) -> None:
    """Numeric diff gate for all 38 tactic metrics: pooled (n, p25, p50, p75) and verdicts."""
    values = await _values(benchmark_session)
    assert set(values["tactic"]) == set(EXPECTED_TACTIC_POOLED)

    for metric_key, (n, p25, p50, p75) in EXPECTED_TACTIC_POOLED.items():
        block = values["tactic"][metric_key]
        pooled = block["pooled"]
        assert pooled["n"] == n, metric_key
        assert (pooled["p25"], pooled["p50"], pooled["p75"]) == pytest.approx((p25, p50, p75)), (
            metric_key
        )
        if metric_key in EXPECTED_TACTIC_VERDICTS:
            _check_verdicts(block, EXPECTED_TACTIC_VERDICTS[metric_key])
        else:
            assert block["verdicts"] == [], metric_key


async def test_chapter5_zone_viable_set(benchmark_session: AsyncSession) -> None:
    """The zone_viable flags equal the recorded set (decides has_zone for tactic metrics)."""
    values = await _values(benchmark_session)
    viable = {row["metric"] for row in values["viability"] if row["zone_viable"]}
    assert viable == set(EXPECTED_ZONE_VIABLE)
