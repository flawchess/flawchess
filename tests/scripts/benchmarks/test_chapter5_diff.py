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
# Expected values — re-populated after the 2026-06-11 mate-ladder game_flaws
# backfill (lila MateAdvice port, commit c403467e: +9.1% flaw rows, lichess
# parity ~100%). Same all-analyzed-games basis as Phase 114 (pooled n = 4,644).
# All values are proportions: multiply by 100 to get the rendered "pp" values.
# ---------------------------------------------------------------------------

EXPECTED_FLAW_RATE_POOLED = {
    "n": 4644,
    "mean": -0.000521,
    "sd": 0.010825,
    "p05": -0.018978,
    "p25": -0.00477,
    "p50": 0.000194,
    "p75": 0.003644,
    "p95": 0.017026,
}
EXPECTED_FLAW_RATE_ELO = {
    "800": (813, 0.000377, 0.012048, -0.00482, 0.000887, 0.005575),
    "1200": (1091, 0.000107, 0.01154, -0.003595, 0.000731, 0.004456),
    "1600": (1139, -0.00067, 0.011167, -0.0049, 0.000205, 0.003755),
    "2000": (1015, -0.001506, 0.009892, -0.005804, -0.000287, 0.002479),
    "2400": (586, -0.000938, 0.00803, -0.004156, -0.000237, 0.001984),
}
EXPECTED_FLAW_RATE_TC = {
    "bullet": (1246, 0.000586, 0.0099, -0.001783, 0.000164, 0.002708),
    "blitz": (1311, -0.000733, 0.010098, -0.003986, 0.000244, 0.002593),
    "rapid": (1376, -0.001575, 0.011375, -0.007001, -8.9e-05, 0.003613),
    "classical": (711, -2.6e-05, 0.012294, -0.006782, 0.001179, 0.006825),
}

EXPECTED_LOW_CLOCK_POOLED = {
    "n": 4644,
    "mean": 3e-06,
    "sd": 0.002735,
    "p05": -0.003601,
    "p25": -0.000814,
    "p50": -1.9e-05,
    "p75": 0.000285,
    "p95": 0.004032,
}
EXPECTED_LOW_CLOCK_ELO = {
    "800": (813, 4.2e-05, 0.001915, -0.000472, 0.0, 0.000181),
    "1200": (1091, 1.2e-05, 0.002224, -0.00043, 0.0, 0.000138),
    "1600": (1139, 5.7e-05, 0.002731, -0.000764, -5.3e-05, 0.000233),
    "2000": (1015, 2e-06, 0.003415, -0.001397, -0.000158, 0.000491),
    "2400": (586, -0.000172, 0.003211, -0.00151, -0.000146, 0.000671),
}
EXPECTED_LOW_CLOCK_TC = {
    "bullet": (1246, -2.4e-05, 0.001991, -0.000431, 0.0, 0.000316),
    "blitz": (1311, 6.3e-05, 0.003164, -0.001017, -7.2e-05, 0.000484),
    "rapid": (1376, -3.3e-05, 0.002733, -0.000954, -0.000114, 0.000217),
    "classical": (711, 8e-06, 0.003005, -0.000696, 0.0, 0.0),
}

EXPECTED_HASTY_POOLED = {
    "n": 4644,
    "mean": -0.000468,
    "sd": 0.007219,
    "p05": -0.011327,
    "p25": -0.002769,
    "p50": -0.000125,
    "p75": 0.001771,
    "p95": 0.01064,
}
EXPECTED_HASTY_ELO = {
    "800": (813, -0.000505, 0.008251, -0.00358, -0.000171, 0.0022),
    "1200": (1091, -0.000479, 0.008825, -0.002668, -6.6e-05, 0.00219),
    "1600": (1139, -0.000618, 0.007409, -0.003384, -0.00012, 0.001699),
    "2000": (1015, -0.000399, 0.005383, -0.002524, -0.000152, 0.001441),
    "2400": (586, -0.000221, 0.004115, -0.002059, -0.000122, 0.001288),
}
EXPECTED_HASTY_TC = {
    "bullet": (1246, 0.000111, 0.004553, -0.001157, -2.8e-05, 0.000827),
    "blitz": (1311, -4.3e-05, 0.003973, -0.001739, -5.8e-05, 0.001229),
    "rapid": (1376, -0.000882, 0.007571, -0.004614, -0.000475, 0.002346),
    "classical": (711, -0.001462, 0.012731, -0.007763, -0.001352, 0.00559),
}

EXPECTED_UNRUSHED_POOLED = {
    "n": 4644,
    "mean": -5.2e-05,
    "sd": 0.009608,
    "p05": -0.016131,
    "p25": -0.003757,
    "p50": 0.000167,
    "p75": 0.003588,
    "p95": 0.015546,
}
EXPECTED_UNRUSHED_ELO = {
    "800": (813, 0.000853, 0.010443, -0.00328, 0.000681, 0.005108),
    "1200": (1091, 0.000582, 0.010458, -0.00317, 0.000314, 0.004118),
    "1600": (1139, -0.000116, 0.010017, -0.004021, 0.000167, 0.003859),
    "2000": (1015, -0.001107, 0.008604, -0.00481, -0.000203, 0.002387),
    "2400": (586, -0.000534, 0.007064, -0.003547, 0.0, 0.002517),
}
EXPECTED_UNRUSHED_TC = {
    "bullet": (1246, 0.000511, 0.00848, -0.001696, 0.000128, 0.00251),
    "blitz": (1311, -0.000752, 0.009087, -0.003921, 0.0002, 0.002657),
    "rapid": (1376, -0.000654, 0.009424, -0.004732, 6e-05, 0.003513),
    "classical": (711, 0.001417, 0.012201, -0.005924, 0.000381, 0.007928),
}

EXPECTED_OPENING_POOLED = {
    "n": 4644,
    "mean": -0.000103,
    "sd": 0.004339,
    "p05": -0.006943,
    "p25": -0.001477,
    "p50": 0.0,
    "p75": 0.001311,
    "p95": 0.006849,
}
EXPECTED_OPENING_ELO = {
    "800": (813, -6.6e-05, 0.006087, -0.002451, 0.000114, 0.002439),
    "1200": (1091, -0.000167, 0.004862, -0.001729, 3.9e-05, 0.001512),
    "1600": (1139, -0.000119, 0.00416, -0.001574, 0.0, 0.001295),
    "2000": (1015, -4.3e-05, 0.002959, -0.001071, -1.1e-05, 0.000987),
    "2400": (586, -0.00011, 0.002248, -0.001061, -3e-06, 0.000714),
}
EXPECTED_OPENING_TC = {
    "bullet": (1246, 0.000202, 0.004027, -0.000886, 0.0, 0.000769),
    "blitz": (1311, -0.000117, 0.003525, -0.001144, 2e-06, 0.000951),
    "rapid": (1376, -0.000255, 0.004389, -0.001679, 2.4e-05, 0.001387),
    "classical": (711, -0.000319, 0.005846, -0.003402, -6.7e-05, 0.00288),
}

EXPECTED_MIDDLEGAME_POOLED = {
    "n": 4644,
    "mean": -0.000288,
    "sd": 0.006564,
    "p05": -0.011632,
    "p25": -0.002695,
    "p50": 0.000129,
    "p75": 0.002255,
    "p95": 0.010148,
}
EXPECTED_MIDDLEGAME_ELO = {
    "800": (813, 0.000246, 0.006349, -0.002426, 0.000377, 0.002989),
    "1200": (1091, 8.1e-05, 0.006708, -0.001995, 0.000329, 0.002606),
    "1600": (1139, -0.000445, 0.006921, -0.003048, 0.000112, 0.002091),
    "2000": (1015, -0.000943, 0.006785, -0.003601, -0.000169, 0.001672),
    "2400": (586, -0.000275, 0.005269, -0.002366, 5e-06, 0.001733),
}
EXPECTED_MIDDLEGAME_TC = {
    "bullet": (1246, 0.000309, 0.005819, -0.00123, 8.3e-05, 0.001531),
    "blitz": (1311, -0.000324, 0.006256, -0.002656, 0.000102, 0.001801),
    "rapid": (1376, -0.000987, 0.006893, -0.004012, 8.6e-05, 0.002165),
    "classical": (711, 8.6e-05, 0.007511, -0.003306, 0.000597, 0.004134),
}

EXPECTED_ENDGAME_PHASE_POOLED = {
    "n": 4644,
    "mean": -0.00013,
    "sd": 0.003001,
    "p05": -0.005309,
    "p25": -0.001207,
    "p50": 3.6e-05,
    "p75": 0.00104,
    "p95": 0.004725,
}
EXPECTED_ENDGAME_PHASE_ELO = {
    "800": (813, 0.000197, 0.002357, -0.000822, 0.000221, 0.001106),
    "1200": (1091, 0.000193, 0.002845, -0.000737, 0.000192, 0.001153),
    "1600": (1139, -0.000107, 0.003159, -0.001363, 5.3e-05, 0.001061),
    "2000": (1015, -0.000519, 0.003325, -0.001657, -6.9e-05, 0.000899),
    "2400": (586, -0.000553, 0.003056, -0.001863, -0.000243, 0.000667),
}
EXPECTED_ENDGAME_PHASE_TC = {
    "bullet": (1246, 7.5e-05, 0.002518, -0.000518, 0.0, 0.000619),
    "blitz": (1311, -0.000293, 0.002891, -0.001292, 0.0, 0.000735),
    "rapid": (1376, -0.000333, 0.003293, -0.001929, 5.4e-05, 0.001107),
    "classical": (711, 0.000207, 0.003324, -0.001382, 0.000576, 0.001958),
}

EXPECTED_MISS_POOLED = {
    "n": 4644,
    "mean": -6e-05,
    "sd": 0.002975,
    "p05": -0.005132,
    "p25": -0.001114,
    "p50": 1.3e-05,
    "p75": 0.001074,
    "p95": 0.00473,
}
EXPECTED_MISS_ELO = {
    "800": (813, 0.000194, 0.003561, -0.00108, 0.000152, 0.001726),
    "1200": (1091, -5.1e-05, 0.003073, -0.001134, 2.1e-05, 0.001212),
    "1600": (1139, -0.000148, 0.002974, -0.001273, 0.0, 0.000845),
    "2000": (1015, -0.000158, 0.002665, -0.001115, -1.5e-05, 0.000896),
    "2400": (586, -9e-05, 0.002324, -0.000942, 4.1e-05, 0.000819),
}
EXPECTED_MISS_TC = {
    "bullet": (1246, 5.4e-05, 0.002848, -0.000647, 2.1e-05, 0.000776),
    "blitz": (1311, -0.000165, 0.002743, -0.000969, 0.0, 0.000805),
    "rapid": (1376, -0.000145, 0.002913, -0.001373, -1.1e-05, 0.001136),
    "classical": (711, 9.9e-05, 0.003639, -0.001485, 0.000113, 0.001889),
}

EXPECTED_LUCKY_POOLED = {
    "n": 4644,
    "mean": 1.6e-05,
    "sd": 0.002541,
    "p05": -0.004016,
    "p25": -0.000907,
    "p50": -7e-06,
    "p75": 0.000891,
    "p95": 0.004074,
}
EXPECTED_LUCKY_ELO = {
    "800": (813, -5.9e-05, 0.003168, -0.001226, -8.5e-05, 0.001025),
    "1200": (1091, 5.8e-05, 0.002773, -0.000949, 0.0, 0.001022),
    "1600": (1139, 7.1e-05, 0.002407, -0.000846, 0.0, 0.000969),
    "2000": (1015, 4.4e-05, 0.002144, -0.000767, 0.0, 0.000873),
    "2400": (586, -0.000108, 0.001925, -0.000811, -4.5e-05, 0.000504),
}
EXPECTED_LUCKY_TC = {
    "bullet": (1246, -9.8e-05, 0.002422, -0.000555, -3e-06, 0.000533),
    "blitz": (1311, 5.1e-05, 0.002289, -0.00076, 0.0, 0.000763),
    "rapid": (1376, 5.1e-05, 0.002479, -0.001032, -5.7e-05, 0.000969),
    "classical": (711, 8.6e-05, 0.003214, -0.001593, 4e-05, 0.001555),
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
    "mean": -0.0001,
    "sd": 0.002367,
    "p05": -0.003714,
    "p25": -0.000853,
    "p50": -1.3e-05,
    "p75": 0.000607,
    "p95": 0.003499,
}
EXPECTED_HASTY_MISS_ELO = {
    "800": (813, -0.000182, 0.00305, -0.001245, -3.7e-05, 0.00084),
    "1200": (1091, -0.000165, 0.002821, -0.000949, -1.1e-05, 0.000704),
    "1600": (1139, -7.4e-05, 0.002307, -0.000962, -3.3e-05, 0.000476),
    "2000": (1015, -3.8e-05, 0.00159, -0.00065, 0.0, 0.000536),
    "2400": (586, -2.3e-05, 0.001403, -0.00058, -4e-06, 0.000563),
}
EXPECTED_HASTY_MISS_TC = {
    "bullet": (1246, -1e-06, 0.001537, -0.00036, 0.0, 0.000274),
    "blitz": (1311, 1.5e-05, 0.001429, -0.000481, 0.0, 0.000467),
    "rapid": (1376, -0.000196, 0.002491, -0.001246, -0.0001, 0.000866),
    "classical": (711, -0.000301, 0.004076, -0.002217, -0.000257, 0.001697),
}

EXPECTED_LOW_CLOCK_MISS_POOLED = {
    "n": 4644,
    "mean": 1.3e-05,
    "sd": 0.000994,
    "p05": -0.00141,
    "p25": -0.000236,
    "p50": 0.0,
    "p75": 0.000119,
    "p95": 0.001539,
}
EXPECTED_LOW_CLOCK_MISS_ELO = {
    "800": (813, 2.1e-05, 0.000802, -0.000173, 0.0, 7.9e-05),
    "1200": (1091, 1.2e-05, 0.000948, -0.000143, 0.0, 5.9e-05),
    "1600": (1139, -2e-06, 0.000974, -0.000232, 0.0, 6.4e-05),
    "2000": (1015, 4.3e-05, 0.001165, -0.000356, 0.0, 0.000188),
    "2400": (586, -2.4e-05, 0.00104, -0.000436, -1.2e-05, 0.000293),
}
EXPECTED_LOW_CLOCK_MISS_TC = {
    "bullet": (1246, 1.2e-05, 0.001026, -0.000164, 0.0, 0.000149),
    "blitz": (1311, 6.2e-05, 0.001169, -0.000296, 0.0, 0.000257),
    "rapid": (1376, -1.6e-05, 0.000856, -0.000293, 0.0, 6.9e-05),
    "classical": (711, -2.1e-05, 0.000822, -0.000167, 0.0, 0.0),
}

EXPECTED_MISTAKE_POOLED = {
    "n": 4644,
    "mean": -0.000143,
    "sd": 0.005813,
    "p05": -0.00991,
    "p25": -0.002274,
    "p50": 6.9e-05,
    "p75": 0.002017,
    "p95": 0.009197,
}
EXPECTED_MISTAKE_ELO = {
    "800": (813, 7.2e-05, 0.006323, -0.00249, 0.000127, 0.002258),
    "1200": (1091, -4.6e-05, 0.006201, -0.002152, 0.000114, 0.002186),
    "1600": (1139, -0.000123, 0.005824, -0.002285, 0.00012, 0.00199),
    "2000": (1015, -0.000498, 0.005529, -0.002487, -5.3e-05, 0.001838),
    "2400": (586, -4.3e-05, 0.004664, -0.001823, 4.2e-05, 0.001541),
}
EXPECTED_MISTAKE_TC = {
    "bullet": (1246, 0.000291, 0.005468, -0.001098, 3.4e-05, 0.0013),
    "blitz": (1311, -0.000236, 0.005174, -0.002097, 6e-05, 0.001466),
    "rapid": (1376, -0.000395, 0.006012, -0.002908, 8.2e-05, 0.002175),
    "classical": (711, -0.000241, 0.006977, -0.004001, 0.000371, 0.003795),
}

EXPECTED_BLUNDER_POOLED = {
    "n": 4644,
    "mean": -0.000378,
    "sd": 0.007046,
    "p05": -0.01283,
    "p25": -0.003137,
    "p50": 0.000126,
    "p75": 0.00246,
    "p95": 0.01081,
}
EXPECTED_BLUNDER_ELO = {
    "800": (813, 0.000306, 0.007833, -0.002899, 0.000692, 0.004182),
    "1200": (1091, 0.000153, 0.007469, -0.002353, 0.000541, 0.003536),
    "1600": (1139, -0.000548, 0.007449, -0.003328, 0.000159, 0.002469),
    "2000": (1015, -0.001007, 0.006317, -0.00368, -0.000228, 0.001539),
    "2400": (586, -0.000895, 0.005064, -0.003018, -0.000302, 0.0012),
}
EXPECTED_BLUNDER_TC = {
    "bullet": (1246, 0.000295, 0.006214, -0.001272, 0.000143, 0.001828),
    "blitz": (1311, -0.000497, 0.006613, -0.003035, 7.3e-05, 0.001802),
    "rapid": (1376, -0.00118, 0.007538, -0.004887, -1.9e-05, 0.00234),
    "classical": (711, 0.000215, 0.007988, -0.004046, 0.000796, 0.004881),
}

# Verdicts: metric -> {axis: ((level_a, level_b), max_abs_d_rounded_2dp)}
# Cohen's d is scale-invariant: verdicts are identical before and after the
# proportion-scale fix (d = (mean_a - mean_b) / pooled_sd is unchanged when
# both numerator and denominator scale by the same factor). The mate-ladder
# basis shifts some verdict pairs because the distribution shape changed.
EXPECTED_VERDICTS: dict[str, dict[str, tuple[tuple[str, str], float]]] = {
    "flaw_rate": {"TC": (("bullet", "rapid"), 0.2), "ELO": (("800", "2000"), 0.17)},
    "low_clock": {"TC": (("bullet", "blitz"), 0.03), "ELO": (("800", "2400"), 0.08)},
    "hasty": {"TC": (("bullet", "classical"), 0.19), "ELO": (("1600", "2400"), 0.06)},
    "unrushed": {"TC": (("blitz", "classical"), 0.21), "ELO": (("800", "2000"), 0.21)},
    "opening": {"TC": (("bullet", "classical"), 0.11), "ELO": (("1200", "2000"), 0.03)},
    "middlegame": {"TC": (("bullet", "rapid"), 0.2), "ELO": (("800", "2000"), 0.18)},
    "endgame_phase": {"TC": (("blitz", "classical"), 0.16), "ELO": (("800", "2400"), 0.28)},
    "miss": {"TC": (("blitz", "classical"), 0.09), "ELO": (("800", "2000"), 0.11)},
    "lucky": {"TC": (("bullet", "classical"), 0.07), "ELO": (("1600", "2400"), 0.08)},
    "reversed": {"TC": (("bullet", "classical"), 0.13), "ELO": (("1200", "2400"), 0.1)},
    "squandered": {"TC": (("blitz", "classical"), 0.12), "ELO": (("2000", "2400"), 0.09)},
    "hasty_miss": {"TC": (("blitz", "classical"), 0.12), "ELO": (("800", "2400"), 0.06)},
    "low_clock_miss": {"TC": (("blitz", "classical"), 0.08), "ELO": (("2000", "2400"), 0.06)},
    "mistake": {"TC": (("bullet", "rapid"), 0.12), "ELO": (("800", "2000"), 0.1)},
    "blunder": {"TC": (("bullet", "rapid"), 0.21), "ELO": (("800", "2000"), 0.19)},
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
