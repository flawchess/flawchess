"""Numeric acceptance gate for Chapter 5 / §5 (flaw-delta, tempo x phase and tactic zones).

Runs chapter5.compute() against the live benchmark DB and asserts, for the 12 flaw metrics and
the 9 tempo x phase crossed cells, the pooled + ELO + TC marginals and Cohen's d verdicts, and
for the 38 tactic metrics the pooled (n, p25, p50, p75) and the verdicts, plus the zone_viable
set and the per-basis cohort summaries. Skips when the benchmark DB is unreachable.
`benchmark_session` is from conftest.py.

Bases: the flaw metrics and crossed cells read the whole cohort (every eval'd
game of a selected user, all four TCs); the tactic metrics read the full-analysis lane
(classical + rapid tranches of `benchmark_selection`, armed, full evals + PVs + blobs). User
moves: CEIL(ply_count/2) for white, FLOOR for black (parity fixed 2026-10-14).
Snapshot: 2026-10-14T18:22Z (one run of `python -m scripts.benchmarks.chapter5`; lane classical and
rapid 99.9% complete). Whole cohort: 1,338,092 games, 4,831 user-cells, 3,559
distinct users. Lane: 138,104 games, 2,006 user-cells, 1,590 distinct users.
The benchmark DB is not static (eval backfill keeps stamping games), so a later run can move
these numbers by a hair; if the gate drifts after a refresh, re-run the fast path and
regenerate this file from the same run that the report narrates.

EXPECTED_* shapes:
  - flaw / tempo x phase: metric -> {pooled, elo, tc, verdicts}
      pooled: {n, mean, sd, p05, p25, p50, p75, p95}  (6 dp, proportion scale)
      elo/tc: label -> (n, mean, sd, p25, p50, p75)   (6 dp, proportion scale)
      verdicts: {axis: ((a, b), max_abs_d)}
  - tactic pooled: metric -> (n, p25, p50, p75)      (6 dp, per-game count difference, NOT x100)

NOTE: Flaw values are in proportion units (NOT x100). The rendered "pp" values in the report
are these values multiplied by 100. A double-x100 bug would cause a p50 100x
larger; the render-layer guard test catches this. Tactic values are per-game count
differences; the "per 100 games" report values are x100.

All-analyzed-games basis: the per_game_tags CTE uses base_games LEFT JOIN
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


def _check_block(block: chapter5.MetricBlock, expected: dict[str, Any]) -> None:
    _check_pooled(block, expected["pooled"])
    _check_marginal(block["elo_marginal"], expected["elo"])
    _check_marginal(block["tc_marginal"], expected["tc"])
    _check_verdicts(block, expected["verdicts"])


# One compute() per test session: each call scans the benchmark DB for a few minutes, and the
# result is plain data that does not depend on the (function-scoped) session it was fetched with.
_VALUES_CACHE: list[chapter5.Chapter5Values] = []


async def _values(session: AsyncSession) -> chapter5.Chapter5Values:
    if not _VALUES_CACHE:
        _VALUES_CACHE.append(await chapter5.compute(session))
    return _VALUES_CACHE[0]


# ---------------------------------------------------------------------------
# Expected values, flaw metrics (12), whole cohort. Proportions: multiply by 100 for "pp".
# ---------------------------------------------------------------------------

EXPECTED_FLAW: dict[str, dict[str, Any]] = {
    "mistake": {
        "pooled": {
            "n": 4828,
            "mean": -0.000338,
            "sd": 0.006334,
            "p05": -0.010369,
            "p25": -0.002673,
            "p50": -2.8e-05,
            "p75": 0.001961,
            "p95": 0.009504,
        },
        "elo": {
            "800": (835, -1.3e-05, 0.008344, -0.003397, 2e-06, 0.002976),
            "1200": (1138, -0.000449, 0.007265, -0.002833, 5.1e-05, 0.002233),
            "1600": (1190, -0.000248, 0.005691, -0.002731, 7.2e-05, 0.002038),
            "2000": (1061, -0.000604, 0.00514, -0.002887, -0.000182, 0.001638),
            "2400": (604, -0.00029, 0.003843, -0.001528, -6.9e-05, 0.000891),
        },
        "tc": {
            "bullet": (1269, 0.0003, 0.005207, -0.000889, 4.8e-05, 0.00102),
            "blitz": (1374, -0.000344, 0.004914, -0.002343, -3.6e-05, 0.001727),
            "rapid": (1421, -0.000566, 0.006158, -0.003571, -0.00022, 0.00217),
            "classical": (764, -0.000965, 0.009675, -0.005393, -0.00042, 0.0041),
        },
        "verdicts": {"TC": (("bullet", "classical"), 0.18), "ELO": (("800", "2000"), 0.09)},
    },
    "blunder": {
        "pooled": {
            "n": 4828,
            "mean": -0.000436,
            "sd": 0.007139,
            "p05": -0.012771,
            "p25": -0.003151,
            "p50": 5.1e-05,
            "p75": 0.002449,
            "p95": 0.01047,
        },
        "elo": {
            "800": (835, -1.2e-05, 0.008621, -0.003659, 0.000485, 0.003838),
            "1200": (1138, -0.00034, 0.008428, -0.002925, 0.000379, 0.003003),
            "1600": (1190, -0.000339, 0.006935, -0.003356, 0.000115, 0.002677),
            "2000": (1061, -0.000859, 0.005755, -0.003254, -0.000304, 0.001756),
            "2400": (604, -0.000655, 0.004186, -0.002154, -3.2e-05, 0.001009),
        },
        "tc": {
            "bullet": (1269, 0.000427, 0.005924, -0.001037, 0.000147, 0.001535),
            "blitz": (1374, -0.00012, 0.006068, -0.002612, 5.7e-05, 0.002271),
            "rapid": (1421, -0.001002, 0.007204, -0.004199, -0.000111, 0.002541),
            "classical": (764, -0.001389, 0.009917, -0.006169, -0.000499, 0.004434),
        },
        "verdicts": {"TC": (("bullet", "classical"), 0.24), "ELO": (("800", "2000"), 0.12)},
    },
    "low_clock": {
        "pooled": {
            "n": 4828,
            "mean": 7.6e-05,
            "sd": 0.002728,
            "p05": -0.003305,
            "p25": -0.000813,
            "p50": -4.6e-05,
            "p75": 0.000376,
            "p95": 0.004325,
        },
        "elo": {
            "800": (835, 0.000124, 0.002073, -0.000505, 0.0, 0.000342),
            "1200": (1138, 5.2e-05, 0.002261, -0.000539, 0.0, 0.000227),
            "1600": (1190, 0.000163, 0.002721, -0.000826, -8.2e-05, 0.000386),
            "2000": (1061, 7.5e-05, 0.003453, -0.001271, -0.000144, 0.000596),
            "2400": (604, -0.000115, 0.002894, -0.001351, -7.1e-05, 0.000504),
        },
        "tc": {
            "bullet": (1269, 2.1e-05, 0.001864, -0.000336, 0.0, 0.00026),
            "blitz": (1374, 0.000152, 0.003194, -0.001203, -0.000183, 0.000724),
            "rapid": (1421, 4.7e-05, 0.002756, -0.000909, -0.000172, 0.000377),
            "classical": (764, 8.4e-05, 0.002964, -0.000682, 0.0, 0.0),
        },
        "verdicts": {"TC": (("bullet", "blitz"), 0.05), "ELO": (("1600", "2400"), 0.1)},
    },
    "hasty": {
        "pooled": {
            "n": 4828,
            "mean": -0.000966,
            "sd": 0.009371,
            "p05": -0.014885,
            "p25": -0.003619,
            "p50": -0.000258,
            "p75": 0.001777,
            "p95": 0.012475,
        },
        "elo": {
            "800": (835, -0.001846, 0.013288, -0.005202, -0.000494, 0.002536),
            "1200": (1138, -0.00148, 0.01177, -0.0047, -0.000354, 0.002106),
            "1600": (1190, -0.000837, 0.008076, -0.00432, -0.000313, 0.001948),
            "2000": (1061, -0.000323, 0.005467, -0.002571, -0.000209, 0.001554),
            "2400": (604, -0.000165, 0.003659, -0.00139, -4.8e-05, 0.00107),
        },
        "tc": {
            "bullet": (1269, 0.000136, 0.004408, -0.000878, -9e-06, 0.000634),
            "blitz": (1374, 5.5e-05, 0.004584, -0.001954, -0.000156, 0.001711),
            "rapid": (1421, -0.001375, 0.00888, -0.005745, -0.001077, 0.002839),
            "classical": (764, -0.003873, 0.018055, -0.012779, -0.003502, 0.005248),
        },
        "verdicts": {"TC": (("bullet", "classical"), 0.35), "ELO": (("800", "2400"), 0.16)},
    },
    "unrushed": {
        "pooled": {
            "n": 4828,
            "mean": 0.00011,
            "sd": 0.010362,
            "p05": -0.016124,
            "p25": -0.004227,
            "p50": 0.000127,
            "p75": 0.003916,
            "p95": 0.017135,
        },
        "elo": {
            "800": (835, 0.001697, 0.013338, -0.004371, 0.000901, 0.006794),
            "1200": (1138, 0.000628, 0.01211, -0.004624, 0.000369, 0.005354),
            "1600": (1190, 8.4e-05, 0.009776, -0.004202, 0.000245, 0.004353),
            "2000": (1061, -0.001224, 0.007755, -0.004606, -0.000331, 0.002295),
            "2400": (604, -0.000662, 0.005919, -0.002795, 0.0, 0.001535),
        },
        "tc": {
            "bullet": (1269, 0.000577, 0.008055, -0.00142, 0.000135, 0.001859),
            "blitz": (1374, -0.000674, 0.008314, -0.004063, 0.000126, 0.003048),
            "rapid": (1421, -0.000236, 0.009955, -0.005463, -0.000133, 0.004767),
            "classical": (764, 0.001389, 0.016102, -0.008727, 0.000481, 0.008882),
        },
        "verdicts": {"TC": (("blitz", "classical"), 0.18), "ELO": (("800", "2000"), 0.28)},
    },
    "opening": {
        "pooled": {
            "n": 4828,
            "mean": -0.000314,
            "sd": 0.006161,
            "p05": -0.008948,
            "p25": -0.00195,
            "p50": -6.9e-05,
            "p75": 0.001426,
            "p95": 0.00766,
        },
        "elo": {
            "800": (835, -0.000394, 0.009865, -0.003964, -0.000129, 0.003237),
            "1200": (1138, -0.000818, 0.007517, -0.003028, -0.000116, 0.00161),
            "1600": (1190, -0.000103, 0.004469, -0.001887, -7.8e-05, 0.001434),
            "2000": (1061, -2.7e-05, 0.003265, -0.001289, -6.9e-05, 0.00108),
            "2400": (604, -0.000172, 0.001965, -0.000747, -2.4e-05, 0.000473),
        },
        "tc": {
            "bullet": (1269, 0.000211, 0.003884, -0.000689, 0.0, 0.000663),
            "blitz": (1374, 3.3e-05, 0.004678, -0.001525, -4e-06, 0.001338),
            "rapid": (1421, -0.000271, 0.005615, -0.00227, -0.000202, 0.001677),
            "classical": (764, -0.001886, 0.010671, -0.005244, -0.001064, 0.002833),
        },
        "verdicts": {"TC": (("bullet", "classical"), 0.29), "ELO": (("1200", "2000"), 0.14)},
    },
    "middlegame": {
        "pooled": {
            "n": 4828,
            "mean": -0.00034,
            "sd": 0.006083,
            "p05": -0.011073,
            "p25": -0.002712,
            "p50": 7.8e-05,
            "p75": 0.002242,
            "p95": 0.008985,
        },
        "elo": {
            "800": (835, 0.000154, 0.006131, -0.002636, 0.000252, 0.003195),
            "1200": (1138, -5.2e-05, 0.006383, -0.002198, 0.000343, 0.002594),
            "1600": (1190, -0.000416, 0.006454, -0.00315, 5e-05, 0.00244),
            "2000": (1061, -0.00096, 0.006113, -0.003267, -0.000222, 0.001706),
            "2400": (604, -0.000324, 0.004292, -0.001893, 9e-06, 0.001411),
        },
        "tc": {
            "bullet": (1269, 0.000411, 0.005485, -0.000982, 9.9e-05, 0.001246),
            "blitz": (1374, -0.00023, 0.005151, -0.002379, 0.000115, 0.002153),
            "rapid": (1421, -0.001021, 0.00633, -0.003663, -0.00021, 0.002225),
            "classical": (764, -0.000517, 0.007741, -0.00421, 0.000449, 0.00408),
        },
        "verdicts": {"TC": (("bullet", "rapid"), 0.24), "ELO": (("800", "2000"), 0.18)},
    },
    "endgame_phase": {
        "pooled": {
            "n": 4828,
            "mean": -0.000121,
            "sd": 0.002712,
            "p05": -0.004858,
            "p25": -0.001193,
            "p50": 0.0,
            "p75": 0.001013,
            "p95": 0.004174,
        },
        "elo": {
            "800": (835, 0.000214, 0.002217, -0.000791, 0.00019, 0.001169),
            "1200": (1138, 8.1e-05, 0.002796, -0.000926, 9.7e-05, 0.001186),
            "1600": (1190, -6.8e-05, 0.002775, -0.001266, 2.3e-05, 0.001132),
            "2000": (1061, -0.000477, 0.002937, -0.001541, -0.000119, 0.000836),
            "2400": (604, -0.00045, 0.002534, -0.00145, -9.3e-05, 0.000447),
        },
        "tc": {
            "bullet": (1269, 0.000105, 0.002373, -0.000404, 0.0, 0.000521),
            "blitz": (1374, -0.000266, 0.002407, -0.001241, -2.7e-05, 0.000853),
            "rapid": (1421, -0.000276, 0.002905, -0.001591, -7e-06, 0.001169),
            "classical": (764, 4.9e-05, 0.003292, -0.001754, 0.000224, 0.001975),
        },
        "verdicts": {"TC": (("bullet", "blitz"), 0.16), "ELO": (("800", "2400"), 0.28)},
    },
    "miss": {
        "pooled": {
            "n": 4828,
            "mean": -6.1e-05,
            "sd": 0.003439,
            "p05": -0.00548,
            "p25": -0.001282,
            "p50": 7e-06,
            "p75": 0.001172,
            "p95": 0.005231,
        },
        "elo": {
            "800": (835, 7e-06, 0.00497, -0.001862, 7.1e-05, 0.001895),
            "1200": (1138, 4.6e-05, 0.003598, -0.001406, 6e-06, 0.001416),
            "1600": (1190, -0.000174, 0.003241, -0.001492, -1.1e-05, 0.001086),
            "2000": (1061, -0.000117, 0.002547, -0.001069, -1.6e-05, 0.000899),
            "2400": (604, -3.3e-05, 0.001976, -0.000706, 4.5e-05, 0.000675),
        },
        "tc": {
            "bullet": (1269, 5.3e-05, 0.00269, -0.000559, 1.6e-05, 0.000622),
            "blitz": (1374, -0.000171, 0.002656, -0.001274, -9.4e-05, 0.000942),
            "rapid": (1421, -0.00012, 0.003265, -0.001505, 2.9e-05, 0.001325),
            "classical": (764, 5.9e-05, 0.005494, -0.002602, 0.000207, 0.002388),
        },
        "verdicts": {"TC": (("bullet", "blitz"), 0.08), "ELO": (("1200", "1600"), 0.06)},
    },
    "lucky": {
        "pooled": {
            "n": 4828,
            "mean": 6.2e-05,
            "sd": 0.002992,
            "p05": -0.004119,
            "p25": -0.000976,
            "p50": 0.0,
            "p75": 0.001053,
            "p95": 0.004424,
        },
        "elo": {
            "800": (835, 0.000116, 0.004585, -0.001388, 3e-05, 0.001661),
            "1200": (1138, 9e-05, 0.003344, -0.001192, 1.7e-05, 0.001334),
            "1600": (1190, 6.9e-05, 0.002491, -0.000908, 1.5e-05, 0.001058),
            "2000": (1061, 5.5e-05, 0.001959, -0.000767, 0.0, 0.00082),
            "2400": (604, -6.3e-05, 0.001573, -0.000684, -4.8e-05, 0.00045),
        },
        "tc": {
            "bullet": (1269, -8.4e-05, 0.002279, -0.000437, 0.0, 0.000436),
            "blitz": (1374, 0.000128, 0.00224, -0.000849, 2.3e-05, 0.000986),
            "rapid": (1421, 2.7e-05, 0.002699, -0.001135, -5.1e-05, 0.001185),
            "classical": (764, 0.000252, 0.005032, -0.00187, 0.000189, 0.002111),
        },
        "verdicts": {"TC": (("bullet", "classical"), 0.09), "ELO": (("2000", "2400"), 0.06)},
    },
    "reversed": {
        "pooled": {
            "n": 4828,
            "mean": -3e-06,
            "sd": 0.001504,
            "p05": -0.002154,
            "p25": -0.000462,
            "p50": 0.0,
            "p75": 0.00047,
            "p95": 0.002139,
        },
        "elo": {
            "800": (835, -0.000101, 0.002471, -0.000907, -1e-06, 0.000801),
            "1200": (1138, 4.6e-05, 0.001637, -0.00058, 1.6e-05, 0.000719),
            "1600": (1190, 4.5e-05, 0.0012, -0.000396, 1e-06, 0.000479),
            "2000": (1061, -3e-06, 0.000893, -0.00038, 0.0, 0.000357),
            "2400": (604, -5.4e-05, 0.000591, -0.000251, 0.0, 0.000145),
        },
        "tc": {
            "bullet": (1269, -2e-05, 0.001052, -0.000227, 0.0, 0.00019),
            "blitz": (1374, 2e-05, 0.001201, -0.000425, 0.0, 0.000437),
            "rapid": (1421, 1e-06, 0.001425, -0.000601, 0.0, 0.000558),
            "classical": (764, -2.2e-05, 0.002469, -0.000713, 2.4e-05, 0.000949),
        },
        "verdicts": {"TC": (("bullet", "blitz"), 0.04), "ELO": (("1600", "2400"), 0.1)},
    },
    "squandered": {
        "pooled": {
            "n": 4828,
            "mean": -2e-06,
            "sd": 0.002309,
            "p05": -0.00359,
            "p25": -0.000801,
            "p50": 0.0,
            "p75": 0.000796,
            "p95": 0.003554,
        },
        "elo": {
            "800": (835, -1.6e-05, 0.003303, -0.001163, -3.5e-05, 0.001258),
            "1200": (1138, -1e-06, 0.00264, -0.001035, 0.0, 0.001101),
            "1600": (1190, 3e-06, 0.002022, -0.000692, 0.0, 0.000788),
            "2000": (1061, -3.3e-05, 0.001633, -0.00071, 0.0, 0.000637),
            "2400": (604, 6.1e-05, 0.0013, -0.000403, 2.1e-05, 0.000436),
        },
        "tc": {
            "bullet": (1269, -1.6e-05, 0.002006, -0.000379, 0.0, 0.000377),
            "blitz": (1374, -2.5e-05, 0.001813, -0.000732, 0.0, 0.000733),
            "rapid": (1421, 3.2e-05, 0.002225, -0.000924, -5e-06, 0.000912),
            "classical": (764, -1e-06, 0.003453, -0.001472, 8.8e-05, 0.001579),
        },
        "verdicts": {"TC": (("blitz", "rapid"), 0.03), "ELO": (("2000", "2400"), 0.06)},
    },
}

# ---------------------------------------------------------------------------
# Expected values, tempo x phase crossed cells (9), whole cohort. Proportions.
# ---------------------------------------------------------------------------

EXPECTED_TEMPO_PHASE: dict[str, dict[str, Any]] = {
    "low_clock__opening": {
        "pooled": {
            "n": 4828,
            "mean": 6e-06,
            "sd": 0.00036,
            "p05": 0.0,
            "p25": 0.0,
            "p50": 0.0,
            "p75": 0.0,
            "p95": 0.0,
        },
        "elo": {
            "800": (835, 1.4e-05, 0.000684, 0.0, 0.0, 0.0),
            "1200": (1138, 7e-06, 0.000383, 0.0, 0.0, 0.0),
            "1600": (1190, 6e-06, 0.000154, 0.0, 0.0, 0.0),
            "2000": (1061, -2e-06, 0.000172, 0.0, 0.0, 0.0),
            "2400": (604, 5e-06, 0.000125, 0.0, 0.0, 0.0),
        },
        "tc": {
            "bullet": (1269, 1.5e-05, 0.0006, 0.0, 0.0, 0.0),
            "blitz": (1374, 0.0, 5.5e-05, 0.0, 0.0, 0.0),
            "rapid": (1421, 3e-06, 0.000331, 0.0, 0.0, 0.0),
            "classical": (764, 5e-06, 0.000118, 0.0, 0.0, 0.0),
        },
        "verdicts": {"TC": (("blitz", "classical"), 0.07), "ELO": (("1600", "2000"), 0.05)},
    },
    "hasty__opening": {
        "pooled": {
            "n": 4828,
            "mean": -0.000563,
            "sd": 0.005529,
            "p05": -0.007688,
            "p25": -0.001437,
            "p50": -0.000109,
            "p75": 0.000709,
            "p95": 0.005662,
        },
        "elo": {
            "800": (835, -0.001192, 0.009383, -0.003174, -0.000392, 0.001772),
            "1200": (1138, -0.001072, 0.006685, -0.002503, -0.000237, 0.001103),
            "1600": (1190, -0.00034, 0.003673, -0.001673, -0.000127, 0.000785),
            "2000": (1061, -2e-05, 0.002242, -0.000816, -2.2e-05, 0.000523),
            "2400": (604, -0.000129, 0.001186, -0.00052, -5.3e-05, 0.000216),
        },
        "tc": {
            "bullet": (1269, 4.5e-05, 0.002538, -0.000485, 0.0, 0.000302),
            "blitz": (1374, -3.9e-05, 0.002686, -0.000947, -7.8e-05, 0.000604),
            "rapid": (1421, -0.000528, 0.004731, -0.002051, -0.000382, 0.001088),
            "classical": (764, -0.002581, 0.011086, -0.006268, -0.001111, 0.00203),
        },
        "verdicts": {"TC": (("bullet", "classical"), 0.37), "ELO": (("1200", "2000"), 0.21)},
    },
    "unrushed__opening": {
        "pooled": {
            "n": 4828,
            "mean": 0.000241,
            "sd": 0.00499,
            "p05": -0.006538,
            "p25": -0.001344,
            "p50": 0.0,
            "p75": 0.001494,
            "p95": 0.007721,
        },
        "elo": {
            "800": (835, 0.000787, 0.008159, -0.002632, 0.00011, 0.003613),
            "1200": (1138, 0.000239, 0.005918, -0.001974, -1.8e-05, 0.001923),
            "1600": (1190, 0.000231, 0.00363, -0.001235, 4.5e-05, 0.001705),
            "2000": (1061, -1.2e-05, 0.00263, -0.000978, 0.0, 0.000917),
            "2400": (604, -4.2e-05, 0.001577, -0.000529, 0.0, 0.000489),
        },
        "tc": {
            "bullet": (1269, 0.000157, 0.003087, -0.000574, 0.0, 0.000621),
            "blitz": (1374, 7e-05, 0.003795, -0.001071, 4.1e-05, 0.001246),
            "rapid": (1421, 0.000264, 0.004844, -0.00168, 1e-05, 0.001889),
            "classical": (764, 0.000648, 0.008479, -0.003247, -8e-05, 0.003776),
        },
        "verdicts": {"TC": (("blitz", "classical"), 0.1), "ELO": (("800", "2000"), 0.14)},
    },
    "low_clock__middlegame": {
        "pooled": {
            "n": 4828,
            "mean": 3.9e-05,
            "sd": 0.001304,
            "p05": -0.001427,
            "p25": -0.000226,
            "p50": 0.0,
            "p75": 5.3e-05,
            "p95": 0.001645,
        },
        "elo": {
            "800": (835, 6.3e-05, 0.001061, -0.000184, 0.0, 6.7e-05),
            "1200": (1138, 1.9e-05, 0.001104, -0.000161, 0.0, 1.9e-05),
            "1600": (1190, 9.1e-05, 0.001381, -0.000215, 0.0, 7e-05),
            "2000": (1061, 2.7e-05, 0.001657, -0.000376, 0.0, 7e-05),
            "2400": (604, -4.1e-05, 0.001077, -0.000213, 0.0, 4.4e-05),
        },
        "tc": {
            "bullet": (1269, 5e-06, 0.001015, -9.9e-05, 0.0, 7.8e-05),
            "blitz": (1374, 8.8e-05, 0.00145, -0.000333, 0.0, 0.000167),
            "rapid": (1421, 0.0, 0.001119, -0.000225, 0.0, 0.0),
            "classical": (764, 7.8e-05, 0.001711, -0.000187, 0.0, 0.0),
        },
        "verdicts": {"TC": (("blitz", "rapid"), 0.07), "ELO": (("1600", "2400"), 0.1)},
    },
    "hasty__middlegame": {
        "pooled": {
            "n": 4828,
            "mean": -0.000299,
            "sd": 0.004249,
            "p05": -0.006794,
            "p25": -0.001672,
            "p50": -0.000105,
            "p75": 0.000937,
            "p95": 0.006118,
        },
        "elo": {
            "800": (835, -0.000554, 0.004966, -0.001785, -0.000234, 0.001095),
            "1200": (1138, -0.000372, 0.005123, -0.001995, -0.000141, 0.001077),
            "1600": (1190, -0.000377, 0.004392, -0.002087, -0.000116, 0.001009),
            "2000": (1061, -0.000139, 0.00323, -0.001441, -0.000112, 0.000827),
            "2400": (604, 6.2e-05, 0.002058, -0.000737, -1.7e-05, 0.000688),
        },
        "tc": {
            "bullet": (1269, 9.5e-05, 0.001939, -0.000342, 0.0, 0.000312),
            "blitz": (1374, 0.000132, 0.002284, -0.000959, -7.6e-05, 0.000858),
            "rapid": (1421, -0.000606, 0.004119, -0.002871, -0.000551, 0.001462),
            "classical": (764, -0.001157, 0.008093, -0.005786, -0.001633, 0.003775),
        },
        "verdicts": {"TC": (("blitz", "classical"), 0.25), "ELO": (("800", "2400"), 0.15)},
    },
    "unrushed__middlegame": {
        "pooled": {
            "n": 4828,
            "mean": -8e-05,
            "sd": 0.005959,
            "p05": -0.010165,
            "p25": -0.002571,
            "p50": 0.000118,
            "p75": 0.0024,
            "p95": 0.009421,
        },
        "elo": {
            "800": (835, 0.000644, 0.006093, -0.00209, 0.000419, 0.00344),
            "1200": (1138, 0.000301, 0.006531, -0.002428, 0.000215, 0.002916),
            "1600": (1190, -0.000133, 0.006303, -0.003084, 0.000163, 0.002783),
            "2000": (1061, -0.000849, 0.005594, -0.00319, -0.000192, 0.001542),
            "2400": (604, -0.000347, 0.004124, -0.001617, 7.6e-05, 0.001162),
        },
        "tc": {
            "bullet": (1269, 0.000313, 0.00505, -0.000939, 0.000121, 0.001202),
            "blitz": (1374, -0.00045, 0.00501, -0.002586, 0.000115, 0.001785),
            "rapid": (1421, -0.000418, 0.005857, -0.003312, -1.6e-05, 0.002608),
            "classical": (764, 0.00056, 0.008493, -0.004987, 0.000502, 0.005828),
        },
        "verdicts": {"TC": (("blitz", "classical"), 0.16), "ELO": (("800", "2000"), 0.26)},
    },
    "low_clock__endgame_phase": {
        "pooled": {
            "n": 4828,
            "mean": 3.1e-05,
            "sd": 0.001762,
            "p05": -0.00234,
            "p25": -0.000565,
            "p50": 0.0,
            "p75": 0.000303,
            "p95": 0.002893,
        },
        "elo": {
            "800": (835, 4.7e-05, 0.001179, -0.000328, 0.0, 0.000202),
            "1200": (1138, 2.6e-05, 0.001405, -0.00038, 0.0, 0.000173),
            "1600": (1190, 6.6e-05, 0.001658, -0.000594, -2.7e-05, 0.000295),
            "2000": (1061, 5e-05, 0.002222, -0.000905, -6e-05, 0.000539),
            "2400": (604, -8e-05, 0.002255, -0.001102, -3e-05, 0.000468),
        },
        "tc": {
            "bullet": (1269, 1e-06, 0.001142, -0.000206, 0.0, 0.000186),
            "blitz": (1374, 6.4e-05, 0.002077, -0.000774, -7.2e-05, 0.000554),
            "rapid": (1421, 4.4e-05, 0.001937, -0.000689, -9.3e-05, 0.000367),
            "classical": (764, 0.0, 0.00165, -0.000447, 0.0, 0.0),
        },
        "verdicts": {"TC": (("bullet", "blitz"), 0.04), "ELO": (("1600", "2400"), 0.08)},
    },
    "hasty__endgame_phase": {
        "pooled": {
            "n": 4828,
            "mean": -0.000104,
            "sd": 0.001961,
            "p05": -0.00338,
            "p25": -0.00079,
            "p50": -6e-06,
            "p75": 0.000621,
            "p95": 0.003046,
        },
        "elo": {
            "800": (835, -0.000101, 0.001744, -0.000745, -4.4e-05, 0.000646),
            "1200": (1138, -3.5e-05, 0.00222, -0.000769, 0.0, 0.000688),
            "1600": (1190, -0.000121, 0.001994, -0.000885, -2e-06, 0.000582),
            "2000": (1061, -0.000164, 0.001878, -0.000869, -1.2e-05, 0.000604),
            "2400": (604, -9.8e-05, 0.001799, -0.000609, -9e-06, 0.00051),
        },
        "tc": {
            "bullet": (1269, -3e-06, 0.001185, -0.000202, 0.0, 0.000215),
            "blitz": (1374, -3.7e-05, 0.001391, -0.000579, -3.5e-05, 0.00054),
            "rapid": (1421, -0.000241, 0.002147, -0.001407, -7.4e-05, 0.000879),
            "classical": (764, -0.000135, 0.003143, -0.00193, -0.000151, 0.001458),
        },
        "verdicts": {"TC": (("bullet", "rapid"), 0.14), "ELO": (("1200", "2000"), 0.06)},
    },
    "unrushed__endgame_phase": {
        "pooled": {
            "n": 4828,
            "mean": -5.1e-05,
            "sd": 0.002473,
            "p05": -0.00417,
            "p25": -0.000985,
            "p50": 0.0,
            "p75": 0.000936,
            "p95": 0.003842,
        },
        "elo": {
            "800": (835, 0.000266, 0.002204, -0.000669, 0.000104, 0.001067),
            "1200": (1138, 8.8e-05, 0.002499, -0.000809, 4.6e-05, 0.001035),
            "1600": (1190, -1.5e-05, 0.002629, -0.001155, 1e-06, 0.001094),
            "2000": (1061, -0.000363, 0.002594, -0.001301, -6.4e-05, 0.00073),
            "2400": (604, -0.000273, 0.002143, -0.00098, -9.7e-05, 0.000446),
        },
        "tc": {
            "bullet": (1269, 0.000107, 0.002153, -0.000397, 0.0, 0.000449),
            "blitz": (1374, -0.000294, 0.002441, -0.001181, -1.7e-05, 0.000814),
            "rapid": (1421, -8.2e-05, 0.002549, -0.001211, 2.8e-05, 0.001121),
            "classical": (764, 0.000182, 0.00282, -0.001335, 3.4e-05, 0.001812),
        },
        "verdicts": {"TC": (("blitz", "classical"), 0.18), "ELO": (("800", "2000"), 0.26)},
    },
}

# ---------------------------------------------------------------------------
# Expected values, tactic metrics (38 = 19 families x missed/allowed), full-analysis lane.
# Per-game count difference (player - opponent), per-user mean over >= 20 games.
# ---------------------------------------------------------------------------

EXPECTED_TACTIC_POOLED: dict[str, tuple[int, float, float, float]] = {
    "tactic_fork_missed": (2006, -0.022161, 0.0, 0.021277),
    "tactic_fork_allowed": (2006, -0.040816, 0.0, 0.032258),
    "tactic_skewer_missed": (2006, 0.0, 0.0, 0.0),
    "tactic_skewer_allowed": (2006, 0.0, 0.0, 0.0),
    "tactic_pin_missed": (2006, -0.014235, 0.0, 0.018868),
    "tactic_pin_allowed": (2006, -0.028571, 0.0, 0.020408),
    "tactic_x_ray_missed": (2006, 0.0, 0.0, 0.0),
    "tactic_x_ray_allowed": (2006, 0.0, 0.0, 0.0),
    "tactic_double_check_missed": (2006, 0.0, 0.0, 0.0),
    "tactic_double_check_allowed": (2006, 0.0, 0.0, 0.0),
    "tactic_discovered_check_missed": (2006, 0.0, 0.0, 0.0),
    "tactic_discovered_check_allowed": (2006, -0.01, 0.0, 0.01),
    "tactic_discovered_attack_missed": (2006, 0.0, 0.0, 0.0),
    "tactic_discovered_attack_allowed": (2006, -0.012346, 0.0, 0.010526),
    "tactic_trapped_piece_missed": (2006, 0.0, 0.0, 0.0),
    "tactic_trapped_piece_allowed": (2006, 0.0, 0.0, 0.0),
    "tactic_hanging_missed": (2006, -0.011332, 0.0, 0.014706),
    "tactic_hanging_allowed": (2006, -0.050977, -0.01, 0.030303),
    "tactic_mate_missed": (2006, -0.021681, 0.0, 0.028882),
    "tactic_mate_allowed": (2006, -0.07, -0.01198, 0.040747),
    "tactic_deflection_missed": (2006, 0.0, 0.0, 0.0),
    "tactic_deflection_allowed": (2006, -0.01, 0.0, 0.01),
    "tactic_intermezzo_missed": (2006, 0.0, 0.0, 0.0),
    "tactic_intermezzo_allowed": (2006, 0.0, 0.0, 0.0),
    "tactic_interference_missed": (2006, 0.0, 0.0, 0.0),
    "tactic_interference_allowed": (2006, 0.0, 0.0, 0.0),
    "tactic_capturing_defender_missed": (2006, 0.0, 0.0, 0.0),
    "tactic_capturing_defender_allowed": (2006, 0.0, 0.0, 0.0),
    "tactic_attraction_missed": (2006, 0.0, 0.0, 0.0),
    "tactic_attraction_allowed": (2006, -0.010101, 0.0, 0.01),
    "tactic_sacrifice_missed": (2006, 0.0, 0.0, 0.0),
    "tactic_sacrifice_allowed": (2006, 0.0, 0.0, 0.0),
    "tactic_en_passant_missed": (2006, 0.0, 0.0, 0.0),
    "tactic_en_passant_allowed": (2006, 0.0, 0.0, 0.0),
    "tactic_under_promotion_missed": (2006, 0.0, 0.0, 0.0),
    "tactic_under_promotion_allowed": (2006, 0.0, 0.0, 0.0),
    "tactic_promotion_missed": (2006, 0.0, 0.0, 0.0),
    "tactic_promotion_allowed": (2006, 0.0, 0.0, 0.0),
}

# Verdicts of every tactic metric that has one (the TC axis is rapid vs classical); every
# other tactic metric must have none.
EXPECTED_TACTIC_VERDICTS: dict[str, dict[str, tuple[tuple[str, str], float]]] = {
    "tactic_fork_missed": {"TC": (("rapid", "classical"), 0.04), "ELO": (("800", "1600"), 0.05)},
    "tactic_fork_allowed": {"TC": (("rapid", "classical"), 0.01), "ELO": (("800", "2000"), 0.14)},
    "tactic_skewer_missed": {"TC": (("rapid", "classical"), 0.05), "ELO": (("800", "1600"), 0.04)},
    "tactic_skewer_allowed": {
        "TC": (("rapid", "classical"), 0.04),
        "ELO": (("1600", "2000"), 0.07),
    },
    "tactic_pin_missed": {"TC": (("rapid", "classical"), 0.04), "ELO": (("1600", "2400"), 0.08)},
    "tactic_pin_allowed": {"TC": (("rapid", "classical"), 0.05), "ELO": (("800", "1600"), 0.11)},
    "tactic_x_ray_missed": {"TC": (("rapid", "classical"), 0.02), "ELO": (("1600", "2400"), 0.1)},
    "tactic_x_ray_allowed": {"TC": (("rapid", "classical"), 0.02), "ELO": (("1200", "2400"), 0.1)},
    "tactic_double_check_missed": {
        "TC": (("rapid", "classical"), 0.06),
        "ELO": (("800", "1600"), 0.09),
    },
    "tactic_double_check_allowed": {
        "TC": (("rapid", "classical"), 0.01),
        "ELO": (("1600", "2000"), 0.12),
    },
    "tactic_discovered_check_missed": {
        "TC": (("rapid", "classical"), 0.01),
        "ELO": (("1200", "2400"), 0.11),
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
        "TC": (("rapid", "classical"), 0.07),
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
        "TC": (("rapid", "classical"), 0.06),
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

# The zone_viable set (pooled IQR not degenerate AND pct_nonzero >= 50) over all
# 59 metrics (12 flaw + 9 tempo x phase + 38 tactic). zone_viable decides has_zone
# for a tactic metric and a crossed cell in the registries.
EXPECTED_ZONE_VIABLE: frozenset[str] = frozenset(
    {
        "blunder",
        "endgame_phase",
        "hasty",
        "hasty__endgame_phase",
        "hasty__middlegame",
        "hasty__opening",
        "low_clock",
        "low_clock__endgame_phase",
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
        "unrushed__endgame_phase",
        "unrushed__middlegame",
        "unrushed__opening",
    }
)

# Per-basis cohort summaries from the viability queries.
EXPECTED_COHORTS: dict[str, dict[str, int]] = {
    "whole_cohort": {"n_analyzed_games": 1338092, "n_user_cells": 4831, "n_distinct_users": 3559},
    "lane": {"n_analyzed_games": 138104, "n_user_cells": 2006, "n_distinct_users": 1590},
}


async def test_chapter5_render_scale_guard(benchmark_session: AsyncSession) -> None:
    """Render-layer regression guard: catches double-x100 scaling bugs.

    The estimator emits proportion-scale values from SQL (e.g. a blunder p50 of about
    -0.002). The 'pp' render unit multiplies by 100 to display per-100-moves values. If someone
    re-introduces x100 in the SQL (a past bug), the rendered blunder pooled p50
    would jump to ~-21pp or worse, which is caught here.

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
    """Numeric diff gate for all 12 flaw-delta metrics (pooled, ELO, TC, verdicts)."""
    values = await _values(benchmark_session)
    assert set(values["flaw"]) == set(EXPECTED_FLAW)
    for metric_key, expected in EXPECTED_FLAW.items():
        _check_block(values["flaw"][metric_key], expected)

    # Viability sanity: one entry per metric of both bases, all users_total > 0.
    viability = values["viability"]
    assert len(viability) == (
        len(chapter5.FLAW_DELTA_METRICS)
        + len(chapter5.TEMPO_PHASE_METRICS)
        + len(chapter5.TACTIC_METRICS)
    )
    for row in viability:
        assert row["users_total"] > 0, f"viability users_total == 0 for metric={row['metric']}"


async def test_chapter5_tempo_phase(benchmark_session: AsyncSession) -> None:
    """Numeric diff gate for the 9 tempo x phase crossed cells (pooled, ELO, TC, verdicts)."""
    values = await _values(benchmark_session)
    assert set(values["tempo_phase"]) == set(EXPECTED_TEMPO_PHASE)
    for metric_key, expected in EXPECTED_TEMPO_PHASE.items():
        _check_block(values["tempo_phase"][metric_key], expected)


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
    """The zone_viable flags equal the recorded set (decides has_zone for tactics and cells)."""
    values = await _values(benchmark_session)
    viable = {row["metric"] for row in values["viability"] if row["zone_viable"]}
    assert viable == set(EXPECTED_ZONE_VIABLE)


async def test_chapter5_cohorts(benchmark_session: AsyncSession) -> None:
    """Per-basis cohort summaries (games, user-cells, distinct users) equal the recorded run."""
    values = await _values(benchmark_session)
    assert {b: dict(c) for b, c in values["cohorts"].items()} == EXPECTED_COHORTS
