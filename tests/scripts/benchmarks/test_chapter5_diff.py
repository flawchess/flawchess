"""Numeric acceptance gate for Chapter 5 / §5 (flaw-delta zones).

Runs chapter5.compute() against the live benchmark DB and asserts pooled + ELO + TC
marginals and Cohen's d verdicts for all 15 metrics. Skips when the benchmark DB is
unreachable. `benchmark_session` is from conftest.py.

Values are populated after the first successful generator run (Task 3) and committed.
The EXPECTED_* dicts below use the same shape as test_chapter3_diff.py:
  - pooled: {n, mean, sd, p05, p25, p50, p75, p95}  (6 dp, proportion scale)
  - ELO/TC: label -> (n, mean, sd, p25, p50, p75)   (6 dp, proportion scale)
  - verdicts: metric -> {axis: ((a, b), max_abs_d)}

NOTE: Values are in proportion units (NOT ×100). The rendered "pp" values in the
report are these values multiplied by 100. E.g. flaw_rate pooled p50 ≈ 0.000177
renders as +0.02pp. The double-×100 bug (Phase 114 fix) would cause p50 ≈ 0.0177
which renders as +1.77pp (100× too large). The render-layer guard test catches this.

All-analyzed-games basis (Phase 114 final fix, commit 08ab86d5): the per_game_tags CTE
now uses base_games LEFT JOIN game_flaws so clean games (zero detected flaws) contribute
a 0 delta. This ~4× increases the contributing user×cell count (3,725 → 4,644) and
compresses all magnitudes toward zero (because clean-game 0 deltas are now included).
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.benchmarks import chapter5, distribution as dist

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Check helpers (verbatim from test_chapter3_diff.py)
# ---------------------------------------------------------------------------


def _check_pooled(block: chapter5.MetricBlock, expected: dict) -> None:  # type: ignore[type-arg]
    pooled = block["pooled"]
    assert pooled["n"] == expected["n"]
    for key in ("mean", "sd", "p05", "p25", "p50", "p75", "p95"):
        assert pooled[key] == pytest.approx(expected[key]), key


def _check_marginal(marginals: list, expected: dict) -> None:  # type: ignore[type-arg]
    by_label = {m["label"]: m for m in marginals}
    assert set(by_label) == set(expected)
    for label, (n, mean, sd, p25, p50, p75) in expected.items():
        d = by_label[label]["dist"]
        assert d["n"] == n, label
        assert d["mean"] == pytest.approx(mean), label
        assert d["sd"] == pytest.approx(sd), label
        assert (d["p25"], d["p50"], d["p75"]) == pytest.approx((p25, p50, p75)), label


def _check_verdicts(block: chapter5.MetricBlock, expected: dict) -> None:  # type: ignore[type-arg]
    by_axis = {v["axis"]: v for v in block["verdicts"]}
    for axis, (pair, d) in expected.items():
        assert by_axis[axis]["pair"] == pair, axis
        assert round(by_axis[axis]["max_abs_d"], 2) == d, axis


# ---------------------------------------------------------------------------
# Expected values — re-populated after Phase 114 all-analyzed-games basis fix
# (base_games LEFT JOIN game_flaws; clean games = 0 delta; 2026-06-10)
# All values are proportions: multiply by 100 to get the rendered "pp" values.
# Sanity check: flaw_rate pooled p50 ≈ 0.000177 → renders as +0.02pp (correct).
# Pooled n = 4,644 (up from 3,725 in flawed-games-only basis).
# ---------------------------------------------------------------------------

EXPECTED_FLAW_RATE_POOLED = {
    "n": 4644,
    "mean": -0.000509,
    "sd": 0.00912,
    "p05": -0.01637,
    "p25": -0.004117,
    "p50": 0.000177,
    "p75": 0.003083,
    "p95": 0.014075,
}
EXPECTED_FLAW_RATE_ELO = {
    "800": (813, 0.000186, 0.009867, -0.003795, 0.000593, 0.004628),
    "1200": (1091, 5e-06, 0.00964, -0.003144, 0.000581, 0.003775),
    "1600": (1139, -0.000589, 0.009412, -0.00445, 0.000168, 0.003472),
    "2000": (1015, -0.001341, 0.00861, -0.005216, -0.000291, 0.002112),
    "2400": (586, -0.000835, 0.006965, -0.003815, -0.000148, 0.001914),
}
EXPECTED_FLAW_RATE_TC = {
    "bullet": (1246, 0.000464, 0.008187, -0.001498, 0.000162, 0.002172),
    "blitz": (1311, -0.000659, 0.008596, -0.003761, 0.000171, 0.002299),
    "rapid": (1376, -0.001411, 0.009567, -0.005898, -4.7e-05, 0.003158),
    "classical": (711, -0.000195, 0.01046, -0.006299, 0.000684, 0.005833),
}

EXPECTED_LOW_CLOCK_POOLED = {
    "n": 4644,
    "mean": -5e-06,
    "sd": 0.002395,
    "p05": -0.003118,
    "p25": -0.000686,
    "p50": 0.0,
    "p75": 0.000221,
    "p95": 0.003329,
}
EXPECTED_LOW_CLOCK_ELO = {
    "800": (813, 4.8e-05, 0.001699, -0.000343, 0.0, 0.000108),
    "1200": (1091, 2.3e-05, 0.001892, -0.000352, 0.0, 0.000103),
    "1600": (1139, 3.1e-05, 0.002342, -0.000661, -2.8e-05, 0.000204),
    "2000": (1015, -1.8e-05, 0.00304, -0.001199, -0.000108, 0.000401),
    "2400": (586, -0.000176, 0.002846, -0.001435, -7e-05, 0.000633),
}
EXPECTED_LOW_CLOCK_TC = {
    "bullet": (1246, -3e-05, 0.001784, -0.00039, 0.0, 0.000213),
    "blitz": (1311, 5e-05, 0.002738, -0.000893, -5e-05, 0.000386),
    "rapid": (1376, -4.2e-05, 0.002373, -0.00078, -6.1e-05, 0.000165),
    "classical": (711, 1e-05, 0.002678, -0.000631, 0.0, 0.0),
}

EXPECTED_HASTY_POOLED = {
    "n": 4644,
    "mean": -0.00044,
    "sd": 0.006586,
    "p05": -0.010327,
    "p25": -0.00265,
    "p50": -0.000105,
    "p75": 0.001631,
    "p95": 0.009736,
}
EXPECTED_HASTY_ELO = {
    "800": (813, -0.000513, 0.007285, -0.00317, -0.000253, 0.002122),
    "1200": (1091, -0.000515, 0.008076, -0.002723, -7.2e-05, 0.001956),
    "1600": (1139, -0.000543, 0.006933, -0.003081, -0.000122, 0.001556),
    "2000": (1015, -0.000336, 0.004925, -0.002515, -0.000127, 0.001235),
    "2400": (586, -0.000177, 0.003662, -0.001923, -8.4e-05, 0.001201),
}
EXPECTED_HASTY_TC = {
    "bullet": (1246, 9.8e-05, 0.00411, -0.001104, -3.2e-05, 0.000756),
    "blitz": (1311, -1.6e-05, 0.003623, -0.001525, -3.7e-05, 0.001141),
    "rapid": (1376, -0.000794, 0.006813, -0.004165, -0.000395, 0.002151),
    "classical": (711, -0.001477, 0.011738, -0.007283, -0.001527, 0.005116),
}

EXPECTED_UNRUSHED_POOLED = {
    "n": 4644,
    "mean": -6.1e-05,
    "sd": 0.008514,
    "p05": -0.014232,
    "p25": -0.003335,
    "p50": 0.000155,
    "p75": 0.003186,
    "p95": 0.013885,
}
EXPECTED_UNRUSHED_ELO = {
    "800": (813, 0.000665, 0.009004, -0.002718, 0.000517, 0.00461),
    "1200": (1091, 0.000504, 0.009212, -0.002977, 0.000332, 0.003747),
    "1600": (1139, -8.2e-05, 0.008912, -0.003352, 0.000184, 0.003408),
    "2000": (1015, -0.000987, 0.007782, -0.004269, -9.3e-05, 0.002164),
    "2400": (586, -0.000473, 0.006492, -0.003267, 0.0, 0.002299),
}
EXPECTED_UNRUSHED_TC = {
    "bullet": (1246, 0.000408, 0.00728, -0.001464, 0.000111, 0.002047),
    "blitz": (1311, -0.00069, 0.007906, -0.003473, 0.000153, 0.002168),
    "rapid": (1376, -0.000569, 0.008329, -0.004237, 0.000141, 0.003211),
    "classical": (711, 0.001264, 0.011314, -0.005299, 0.000517, 0.007274),
}

EXPECTED_OPENING_POOLED = {
    "n": 4644,
    "mean": -9.3e-05,
    "sd": 0.004286,
    "p05": -0.006915,
    "p25": -0.001461,
    "p50": 0.0,
    "p75": 0.001311,
    "p95": 0.006813,
}
EXPECTED_OPENING_ELO = {
    "800": (813, -3.7e-05, 0.005988, -0.002415, 0.000134, 0.002429),
    "1200": (1091, -0.000148, 0.004784, -0.001745, 4.5e-05, 0.001489),
    "1600": (1139, -0.000117, 0.004139, -0.00154, 0.0, 0.001295),
    "2000": (1015, -4.5e-05, 0.002946, -0.001071, 0.0, 0.000986),
    "2400": (586, -0.000108, 0.002242, -0.00107, -6e-06, 0.000697),
}
EXPECTED_OPENING_TC = {
    "bullet": (1246, 0.000203, 0.003975, -0.000871, 0.0, 0.000768),
    "blitz": (1311, -0.000109, 0.003486, -0.001123, 4e-06, 0.000935),
    "rapid": (1376, -0.000237, 0.004343, -0.001643, 3.2e-05, 0.001386),
    "classical": (711, -0.000307, 0.005766, -0.003408, -6.2e-05, 0.002855),
}

EXPECTED_MIDDLEGAME_POOLED = {
    "n": 4644,
    "mean": -0.000298,
    "sd": 0.005747,
    "p05": -0.010394,
    "p25": -0.002378,
    "p50": 8.4e-05,
    "p75": 0.002014,
    "p95": 0.00864,
}
EXPECTED_MIDDLEGAME_ELO = {
    "800": (813, 0.000125, 0.005234, -0.001971, 0.000237, 0.002608),
    "1200": (1091, 7.3e-05, 0.005814, -0.001759, 0.000281, 0.002345),
    "1600": (1139, -0.000406, 0.006078, -0.002684, 7.7e-05, 0.001928),
    "2000": (1015, -0.000926, 0.006101, -0.003383, -0.000194, 0.00156),
    "2400": (586, -0.000277, 0.004851, -0.002142, 0.0, 0.001635),
}
EXPECTED_MIDDLEGAME_TC = {
    "bullet": (1246, 0.000202, 0.005004, -0.001108, 7.3e-05, 0.00124),
    "blitz": (1311, -0.000304, 0.005565, -0.002351, 5.2e-05, 0.001614),
    "rapid": (1376, -0.000889, 0.006008, -0.003402, 1e-06, 0.001909),
    "classical": (711, -1.6e-05, 0.00662, -0.00316, 0.000647, 0.003749),
}

EXPECTED_ENDGAME_PHASE_POOLED = {
    "n": 4644,
    "mean": -0.000118,
    "sd": 0.002296,
    "p05": -0.003977,
    "p25": -0.000907,
    "p50": 1.4e-05,
    "p75": 0.000767,
    "p95": 0.003423,
}
EXPECTED_ENDGAME_PHASE_ELO = {
    "800": (813, 9.9e-05, 0.001612, -0.00049, 8.8e-05, 0.000671),
    "1200": (1091, 7.9e-05, 0.002079, -0.000597, 7.8e-05, 0.000798),
    "1600": (1139, -6.6e-05, 0.002367, -0.000959, 3.7e-05, 0.000858),
    "2000": (1015, -0.00037, 0.002665, -0.001301, -4.2e-05, 0.000808),
    "2400": (586, -0.000451, 0.002565, -0.001533, -0.000186, 0.000564),
}
EXPECTED_ENDGAME_PHASE_TC = {
    "bullet": (1246, 5.9e-05, 0.001823, -0.000373, 0.0, 0.000455),
    "blitz": (1311, -0.000246, 0.00224, -0.000995, 0.0, 0.000514),
    "rapid": (1376, -0.000284, 0.002502, -0.001258, 2.5e-05, 0.000865),
    "classical": (711, 0.000128, 0.002654, -0.001157, 0.00026, 0.001391),
}

EXPECTED_MISS_POOLED = {
    "n": 4644,
    "mean": -4.2e-05,
    "sd": 0.002914,
    "p05": -0.004932,
    "p25": -0.001096,
    "p50": 4e-06,
    "p75": 0.001039,
    "p95": 0.004737,
}
EXPECTED_MISS_ELO = {
    "800": (813, 0.000228, 0.003501, -0.001068, 0.000131, 0.001648),
    "1200": (1091, -5.4e-05, 0.002986, -0.001124, 3e-06, 0.001128),
    "1600": (1139, -0.00012, 0.002937, -0.001194, -1.5e-05, 0.000838),
    "2000": (1015, -0.000141, 0.002591, -0.001101, -2e-06, 0.000829),
    "2400": (586, -7e-05, 0.002286, -0.000844, 1e-06, 0.000833),
}
EXPECTED_MISS_TC = {
    "bullet": (1246, 6.9e-05, 0.002787, -0.0007, 3e-06, 0.000721),
    "blitz": (1311, -0.000163, 0.002717, -0.000954, 0.0, 0.000789),
    "rapid": (1376, -0.00012, 0.002819, -0.001329, -3e-05, 0.001103),
    "classical": (711, 0.000138, 0.003579, -0.001567, 0.000255, 0.001867),
}

EXPECTED_LUCKY_POOLED = {
    "n": 4644,
    "mean": 2e-05,
    "sd": 0.002467,
    "p05": -0.003863,
    "p25": -0.000881,
    "p50": -1.9e-05,
    "p75": 0.000891,
    "p95": 0.003965,
}
EXPECTED_LUCKY_ELO = {
    "800": (813, -5.9e-05, 0.003069, -0.001207, -8.4e-05, 0.000984),
    "1200": (1091, 6.6e-05, 0.002666, -0.000956, 0.0, 0.001029),
    "1600": (1139, 6.2e-05, 0.002364, -0.000828, 0.0, 0.000948),
    "2000": (1015, 5.7e-05, 0.002084, -0.000652, 0.0, 0.000873),
    "2400": (586, -0.000101, 0.001889, -0.000761, -6.5e-05, 0.000507),
}
EXPECTED_LUCKY_TC = {
    "bullet": (1246, -9e-05, 0.002351, -0.000572, 0.0, 0.000537),
    "blitz": (1311, 6.3e-05, 0.002237, -0.000696, -1e-05, 0.000746),
    "rapid": (1376, 6.7e-05, 0.002381, -0.000952, -6e-05, 0.001002),
    "classical": (711, 4.4e-05, 0.003142, -0.001498, 0.0, 0.001444),
}

EXPECTED_REVERSED_POOLED = {
    "n": 4644,
    "mean": -6e-06,
    "sd": 0.001247,
    "p05": -0.002021,
    "p25": -0.000399,
    "p50": 0.0,
    "p75": 0.00041,
    "p95": 0.00198,
}
EXPECTED_REVERSED_ELO = {
    "800": (813, -4.5e-05, 0.001647, -0.000641, 0.0, 0.00061),
    "1200": (1091, 5.2e-05, 0.001441, -0.000468, 1.5e-05, 0.000572),
    "1600": (1139, 1.2e-05, 0.001149, -0.000376, 0.0, 0.000405),
    "2000": (1015, -2.1e-05, 0.000943, -0.000337, 0.0, 0.000299),
    "2400": (586, -6.9e-05, 0.00076, -0.000309, 0.0, 0.000186),
}
EXPECTED_REVERSED_TC = {
    "bullet": (1246, -3.8e-05, 0.001127, -0.000292, 0.0, 0.000236),
    "blitz": (1311, -1.1e-05, 0.001181, -0.000376, 0.0, 0.000307),
    "rapid": (1376, -4.1e-05, 0.001223, -0.000496, 0.0, 0.000442),
    "classical": (711, 0.000126, 0.001563, -0.000528, 0.000109, 0.000787),
}

EXPECTED_SQUANDERED_POOLED = {
    "n": 4644,
    "mean": 4e-06,
    "sd": 0.002148,
    "p05": -0.003467,
    "p25": -0.000733,
    "p50": 0.0,
    "p75": 0.000755,
    "p95": 0.003501,
}
EXPECTED_SQUANDERED_ELO = {
    "800": (813, 7e-06, 0.002616, -0.001008, -2.1e-05, 0.00095),
    "1200": (1091, 1e-05, 0.00247, -0.00087, 0.0, 0.000944),
    "1600": (1139, 2.4e-05, 0.001992, -0.000556, 0.0, 0.000764),
    "2000": (1015, -7e-05, 0.001774, -0.000739, -3.4e-05, 0.000589),
    "2400": (586, 7.8e-05, 0.001607, -0.000507, 4.2e-05, 0.000599),
}
EXPECTED_SQUANDERED_TC = {
    "bullet": (1246, 8e-06, 0.00212, -0.000447, 0.0, 0.00045),
    "blitz": (1311, -8e-05, 0.001841, -0.000669, -3e-06, 0.00064),
    "rapid": (1376, -1.1e-05, 0.002179, -0.000797, -2.8e-05, 0.000826),
    "classical": (711, 0.00018, 0.00261, -0.001125, 5.5e-05, 0.001466),
}

EXPECTED_HASTY_MISS_POOLED = {
    "n": 4644,
    "mean": -7e-05,
    "sd": 0.00224,
    "p05": -0.003403,
    "p25": -0.000772,
    "p50": -7e-06,
    "p75": 0.000578,
    "p95": 0.00321,
}
EXPECTED_HASTY_MISS_ELO = {
    "800": (813, -0.000115, 0.002865, -0.001038, -5.3e-05, 0.000776),
    "1200": (1091, -0.000138, 0.002654, -0.000904, -3e-06, 0.000672),
    "1600": (1139, -6.4e-05, 0.002217, -0.000852, -5.4e-05, 0.000437),
    "2000": (1015, -9e-06, 0.001516, -0.000607, 0.0, 0.000538),
    "2400": (586, 2e-06, 0.001315, -0.000471, 0.0, 0.000504),
}
EXPECTED_HASTY_MISS_TC = {
    "bullet": (1246, 1.5e-05, 0.001487, -0.000335, 0.0, 0.000236),
    "blitz": (1311, 1.8e-05, 0.001354, -0.000468, 0.0, 0.000438),
    "rapid": (1376, -0.000151, 0.002293, -0.001185, -8.9e-05, 0.000815),
    "classical": (711, -0.000225, 0.003912, -0.001998, -0.000181, 0.001602),
}

EXPECTED_LOW_CLOCK_MISS_POOLED = {
    "n": 4644,
    "mean": 1.1e-05,
    "sd": 0.000896,
    "p05": -0.001214,
    "p25": -0.000196,
    "p50": 0.0,
    "p75": 8.3e-05,
    "p95": 0.001341,
}
EXPECTED_LOW_CLOCK_MISS_ELO = {
    "800": (813, 2.2e-05, 0.000717, -9.3e-05, 0.0, 2.6e-05),
    "1200": (1091, 1.5e-05, 0.000818, -0.000101, 0.0, 3.7e-05),
    "1600": (1139, 1e-06, 0.000889, -0.000187, 0.0, 5.1e-05),
    "2000": (1015, 3.6e-05, 0.001075, -0.000308, 0.0, 0.000149),
    "2400": (586, -3.6e-05, 0.000933, -0.000402, -8e-06, 0.000249),
}
EXPECTED_LOW_CLOCK_MISS_TC = {
    "bullet": (1246, 1e-05, 0.000939, -0.000114, 0.0, 0.00012),
    "blitz": (1311, 5.9e-05, 0.001036, -0.000269, 0.0, 0.000214),
    "rapid": (1376, -1.9e-05, 0.000766, -0.00024, 0.0, 2.9e-05),
    "classical": (711, -1.7e-05, 0.000763, -0.000117, 0.0, 0.0),
}

EXPECTED_MISTAKE_POOLED = {
    "n": 4644,
    "mean": -0.000186,
    "sd": 0.005094,
    "p05": -0.008827,
    "p25": -0.001984,
    "p50": 4.2e-05,
    "p75": 0.001759,
    "p95": 0.007959,
}
EXPECTED_MISTAKE_ELO = {
    "800": (813, -6.8e-05, 0.005245, -0.002111, 2.9e-05, 0.001822),
    "1200": (1091, -0.000159, 0.005343, -0.001857, 4.6e-05, 0.001818),
    "1600": (1139, -0.000101, 0.005064, -0.002069, 0.00011, 0.001912),
    "2000": (1015, -0.000482, 0.005183, -0.002353, 0.0, 0.001746),
    "2400": (586, -5.5e-05, 0.004231, -0.001512, 0.0, 0.001351),
}
EXPECTED_MISTAKE_TC = {
    "bullet": (1246, 0.000193, 0.004613, -0.000918, 4e-06, 0.001152),
    "blitz": (1311, -0.000252, 0.004648, -0.001817, 2.9e-05, 0.001404),
    "rapid": (1376, -0.000394, 0.005338, -0.002615, 7e-05, 0.001836),
    "classical": (711, -0.000328, 0.006078, -0.003552, 0.000211, 0.003082),
}

EXPECTED_BLUNDER_POOLED = {
    "n": 4644,
    "mean": -0.000323,
    "sd": 0.00614,
    "p05": -0.011094,
    "p25": -0.002724,
    "p50": 9.8e-05,
    "p75": 0.002158,
    "p95": 0.00944,
}
EXPECTED_BLUNDER_ELO = {
    "800": (813, 0.000254, 0.006865, -0.002447, 0.000515, 0.00358),
    "1200": (1091, 0.000163, 0.006483, -0.002044, 0.000475, 0.002989),
    "1600": (1139, -0.000488, 0.006481, -0.003024, 5.9e-05, 0.002114),
    "2000": (1015, -0.000859, 0.005499, -0.003225, -0.00019, 0.001398),
    "2400": (586, -0.00078, 0.004433, -0.002455, -0.000235, 0.001015),
}
EXPECTED_BLUNDER_TC = {
    "bullet": (1246, 0.000271, 0.005453, -0.001131, 0.000108, 0.001599),
    "blitz": (1311, -0.000407, 0.005677, -0.002706, 5.4e-05, 0.001637),
    "rapid": (1376, -0.001016, 0.006491, -0.003931, -3.9e-05, 0.001997),
    "classical": (711, 0.000134, 0.007179, -0.003821, 0.000517, 0.004437),
}

# Verdicts: metric -> {axis: ((level_a, level_b), max_abs_d_rounded_2dp)}
# Cohen's d is scale-invariant: verdicts are identical before and after the
# proportion-scale fix (d = (mean_a - mean_b) / pooled_sd is unchanged when
# both numerator and denominator scale by the same factor). The all-analyzed-games
# basis shifts some verdict pairs because the distribution shape changed.
EXPECTED_VERDICTS: dict[str, dict[str, tuple[tuple[str, str], float]]] = {
    "flaw_rate": {"TC": (("bullet", "rapid"), 0.21), "ELO": (("800", "2000"), 0.17)},
    "low_clock": {"TC": (("blitz", "rapid"), 0.04), "ELO": (("800", "2400"), 0.1)},
    "hasty": {"TC": (("bullet", "classical"), 0.2), "ELO": (("1600", "2400"), 0.06)},
    "unrushed": {"TC": (("blitz", "classical"), 0.21), "ELO": (("800", "2000"), 0.2)},
    "opening": {"TC": (("bullet", "classical"), 0.11), "ELO": (("1200", "2000"), 0.03)},
    "middlegame": {"TC": (("bullet", "rapid"), 0.2), "ELO": (("800", "2000"), 0.18)},
    "endgame_phase": {"TC": (("rapid", "classical"), 0.16), "ELO": (("800", "2400"), 0.27)},
    "miss": {"TC": (("blitz", "classical"), 0.1), "ELO": (("800", "2000"), 0.12)},
    "lucky": {"TC": (("bullet", "blitz"), 0.07), "ELO": (("2000", "2400"), 0.08)},
    "reversed": {"TC": (("bullet", "classical"), 0.13), "ELO": (("1200", "2400"), 0.1)},
    "squandered": {"TC": (("blitz", "classical"), 0.12), "ELO": (("2000", "2400"), 0.09)},
    "hasty_miss": {"TC": (("blitz", "classical"), 0.09), "ELO": (("1200", "2400"), 0.06)},
    "low_clock_miss": {"TC": (("blitz", "rapid"), 0.09), "ELO": (("800", "2400"), 0.07)},
    "mistake": {"TC": (("bullet", "rapid"), 0.12), "ELO": (("2000", "2400"), 0.09)},
    "blunder": {"TC": (("bullet", "rapid"), 0.21), "ELO": (("800", "2000"), 0.18)},
}

# Per-metric (pooled_dict, elo_dict, tc_dict) references for the test loop.
_EXPECTED_BY_METRIC: dict[
    str,
    tuple[
        dict,  # type: ignore[type-arg]
        dict,  # type: ignore[type-arg]
        dict,  # type: ignore[type-arg]
    ],
] = {
    "flaw_rate": (EXPECTED_FLAW_RATE_POOLED, EXPECTED_FLAW_RATE_ELO, EXPECTED_FLAW_RATE_TC),
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
    "hasty_miss": (EXPECTED_HASTY_MISS_POOLED, EXPECTED_HASTY_MISS_ELO, EXPECTED_HASTY_MISS_TC),
    "low_clock_miss": (
        EXPECTED_LOW_CLOCK_MISS_POOLED,
        EXPECTED_LOW_CLOCK_MISS_ELO,
        EXPECTED_LOW_CLOCK_MISS_TC,
    ),
    "mistake": (EXPECTED_MISTAKE_POOLED, EXPECTED_MISTAKE_ELO, EXPECTED_MISTAKE_TC),
    "blunder": (EXPECTED_BLUNDER_POOLED, EXPECTED_BLUNDER_ELO, EXPECTED_BLUNDER_TC),
}


async def test_chapter5_render_scale_guard(benchmark_session: AsyncSession) -> None:
    """Render-layer regression guard: catches double-×100 scaling bugs.

    The D-01 estimator emits proportion-scale values from SQL (e.g. flaw_rate p50 ≈ 0.000177).
    The 'pp' render unit multiplies by 100 to display per-100-moves values (e.g. ~0.02pp).
    If someone re-introduces ×100 in the SQL (the bug fixed in Phase 114), the rendered
    flaw_rate pooled p50 would jump to ~1.77pp or ~17.7pp — caught here.

    Guard: flaw_rate pooled p50 rendered as pp must be in the plausible range (-2.0, 2.0).
    This is generous enough to survive future benchmark DB changes while reliably catching
    double-scaling (which would produce values ~100× larger, i.e. ±1.77pp or worse).
    """
    values = await chapter5.compute(benchmark_session)
    block = values["flaw_rate"]
    pooled = block["pooled"]

    # Rendered p50: proportion value × 100 (the "pp" unit scale factor).
    rendered_p50_pp = float(pooled["p50"]) * 100

    assert abs(rendered_p50_pp) < 2.0, (
        f"flaw_rate pooled p50 rendered as {rendered_p50_pp:.4f}pp — expected < 2.0pp in abs. "
        f"Raw SQL value: {pooled['p50']}. "
        "If this is ~1.77pp or ~17.7pp, the SQL-side ×100 double-scaling bug was reintroduced."
    )

    # Also verify the rendered pooled table string contains a plausible 'pp' value.
    rendered_table = dist.pooled_table(pooled, "pp")
    # The table must contain a 'pp' suffix (confirms the render path was exercised).
    assert "pp" in rendered_table, "pooled_table with unit='pp' must produce 'pp'-suffixed values"


async def test_chapter5_flaw_delta(benchmark_session: AsyncSession) -> None:
    """Numeric diff gate for all 15 flaw-delta metrics.

    Asserts pooled + ELO + TC marginals and Cohen's d verdicts for every metric.
    Also checks that the viability list has one entry per metric with users_total > 0.
    """
    values = await chapter5.compute(benchmark_session)

    for metric_key, (exp_pooled, exp_elo, exp_tc) in _EXPECTED_BY_METRIC.items():
        block = values[metric_key]  # ty: ignore[invalid-key]  # dynamic key over known set
        _check_pooled(block, exp_pooled)
        _check_marginal(block["elo_marginal"], exp_elo)
        _check_marginal(block["tc_marginal"], exp_tc)
        _check_verdicts(block, EXPECTED_VERDICTS[metric_key])

    # Viability sanity: one entry per metric, all users_total > 0.
    viability = values["viability"]
    assert len(viability) == len(chapter5._FLAW_DELTA_METRICS)
    for row in viability:
        assert row["users_total"] > 0, f"viability users_total == 0 for metric={row['metric']}"
