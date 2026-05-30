"""Numeric acceptance gate for Chapter 1 (SEED-029 Phase A regression oracle).

Runs the ported §1 queries against the live benchmark DB (localhost:5433) and
asserts every value matches `reports/benchmark/benchmarks-latest.md` (2026-05-27
snapshot). Skips when the benchmark DB is unreachable (e.g. CI, or `bin/benchmark_db.sh`
not started) — it is a local calibration-source regression check, not a unit test.

If this test fails after an intentional benchmark-DB re-ingest, update the EXPECTED_*
literals from the new report in the same commit that rotates the report.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.benchmarks import chapter1

pytestmark = pytest.mark.asyncio

# `benchmark_session` fixture lives in conftest.py (shared with the other chapter gates).

# --- expected values, transcribed from benchmarks-latest.md (2026-05-27) -------

EXPECTED_POPULATION = {"users": 4697, "games": 2767158, "positions": 190934222}

EXPECTED_EVAL = {"endgame_games": 1538585, "with_eval": 1538581}

# (elo, tc) -> completed users (selection-pool coverage grid).
EXPECTED_COVERAGE: dict[tuple[int, str], int] = {
    (elo, tc): 200
    for elo in (800, 1200, 1600, 2000, 2400)
    for tc in ("bullet", "blitz", "rapid", "classical")
}
EXPECTED_COVERAGE[(800, "classical")] = 151
EXPECTED_COVERAGE[(2400, "classical")] = 12

# (elo, tc) -> (users, games) (game-time cell sizes, post equal-footing filter).
EXPECTED_GAME_TIME: dict[tuple[int, str], tuple[int, int]] = {
    (800, "bullet"): (268, 114933),
    (1200, "bullet"): (404, 165994),
    (1600, "bullet"): (363, 165589),
    (2000, "bullet"): (334, 147313),
    (2400, "bullet"): (240, 113012),
    (800, "blitz"): (260, 115661),
    (1200, "blitz"): (423, 162443),
    (1600, "blitz"): (419, 164380),
    (2000, "blitz"): (364, 140587),
    (2400, "blitz"): (223, 89885),
    (800, "rapid"): (317, 95792),
    (1200, "rapid"): (545, 132196),
    (1600, "rapid"): (502, 134570),
    (2000, "rapid"): (399, 97751),
    (2400, "rapid"): (208, 31627),
    (800, "classical"): (222, 11609),
    (1200, "classical"): (452, 39705),
    (1600, "classical"): (423, 48763),
    (2000, "classical"): (222, 17766),
    (2400, "classical"): (10, 47),
}

# Representative status cells (C/S/F/U), incl. the pool-limited / sparse cells whose
# 'unattempted' is absent from the query result and must render as 0.
EXPECTED_STATUS: dict[tuple[int, str], dict[str, int]] = {
    (800, "bullet"): {"completed": 200, "skipped": 14, "failed": 2, "unattempted": 284},
    (800, "classical"): {"completed": 151, "skipped": 340, "failed": 9, "unattempted": 0},
    (2400, "classical"): {"completed": 12, "skipped": 8, "failed": 3, "unattempted": 0},
}


async def test_chapter1_matches_report(benchmark_session: AsyncSession) -> None:
    values = await chapter1.compute(benchmark_session)

    assert values["population"] == EXPECTED_POPULATION

    ev = values["eval_coverage"]
    assert {"endgame_games": ev["endgame_games"], "with_eval": ev["with_eval"]} == EXPECTED_EVAL
    assert round(ev["pct_with_eval"], 2) == 100.00

    coverage = {(c["elo"], c["tc"]): c["n"] for c in values["pool_coverage"]}
    assert coverage == EXPECTED_COVERAGE

    game_time = {(c["elo"], c["tc"]): (c["users"], c["games"]) for c in values["game_time_cells"]}
    assert game_time == EXPECTED_GAME_TIME

    status: dict[tuple[int, str], dict[str, int]] = {}
    for row in values["pool_status"]:
        status.setdefault((row["elo"], row["tc"]), {})[row["status"]] = row["n"]
    for cell, expected in EXPECTED_STATUS.items():
        got = status.get(cell, {})
        for code, n in expected.items():
            assert got.get(code, 0) == n, (
                f"{cell} status {code!r}: got {got.get(code, 0)}, want {n}"
            )
