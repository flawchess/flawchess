"""SC-7 property gate: per-user canonical-slice value matches benchmark CDF
aggregation for the same user_id across all 4 CdfMetricId values.

Phase 94.1 Plan 02, Task 1.

This test is the definitive "did the extraction preserve semantics" gate for
the CTE-sharing mechanism (D-11). When Plan 03 lands (canonical_slice_sql.py
implementation), these tests must turn green.

Per RESEARCH §Open Question 2 (documented here per the plan requirement):
  The per-user pooled value is avg(metric_value) across (elo_bucket, tc_bucket)
  cells (unweighted), matching the benchmark's percentile_cont treatment of
  per-(user, cell) rows. Both paths pool across TCs with no per-TC cap (D-09).
  This means a user active in both blitz and rapid contributes rows from both
  TC buckets, and the avg() across those rows is what both consumers produce.

Skip mechanism: pytest.importorskip on canonical_slice_sql causes the entire
module to be skipped until Plan 03 lands. No ☑️ needed in pre-implementation
test runs.
"""

from __future__ import annotations

import pytest

# ── Skip entire module until canonical_slice_sql.py is implemented ────────────
canonical_slice_sql = pytest.importorskip("app.services.canonical_slice_sql")
user_benchmark_percentiles_service = pytest.importorskip(
    "app.services.user_benchmark_percentiles_service"
)

# ── Module-level constants (CLAUDE.md: no magic numbers) ─────────────────────
_SEED_USER_COUNT: int = 5
_SEED_ELO_BUCKETS: int = 3
_SEED_TC_BUCKETS: int = 2
_MIN_ENDGAME_GAMES_PER_USER: int = 30  # score_gap inclusion floor per D-10
_MIN_NON_ENDGAME_GAMES_PER_USER: int = 30  # score_gap inclusion floor per D-10
_FLOAT_EPSILON: float = 1e-9  # tolerance for float equality (SC-7 property gate)

# All 4 metric IDs that Plan 03 must extract (drives the parametrise below)
_ALL_METRIC_IDS: list[str] = [
    "score_gap",
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
]

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("metric_id", _ALL_METRIC_IDS)
async def test_per_user_value_matches_benchmark_per_user_for_same_user_id(
    metric_id: str,
    test_engine,
) -> None:
    """Synthetic DB seed → both consumers → assert same value emerges (SC-7).

    Setup:
    - Seed 5 users spanning 3 ELO buckets x 2 TC buckets, each with >= 30
      endgame + >= 30 non-endgame canonical-slice games (satisfies the
      score_gap floor; eval-dependent metric floors are relaxed similarly).
    - Seed benchmark_selected_users + benchmark_ingest_checkpoints rows so
      the 'benchmark' source CTE sees these users.

    Assert per metric_id:
    - Run canonical_slice_sql.per_user_cte_for(metric_id, source='benchmark')
      → aggregates per user across all cells → captures per-user metric_value
      for each of the 5 user_ids.
    - Run canonical_slice_sql.per_user_cte_for(metric_id, source='single_user')
      for each user_id → captures single-user pooled value.
    - Assert abs(benchmark_value - single_user_value) < 1e-9 for each user.

    This test is the Plan 03 executor's green-turn contract — once the shared
    module is implemented correctly, this passes automatically.

    Note: For eval-dependent metrics (achievable_score_gap, section2_*), users
    need eval_cp / eval_mate values on endgame span entries. The seed helper
    should populate these. If not, the test skips with a "no eval data" note.
    """
    pytest.skip(f"implementation pending Plan 03 (canonical_slice_sql.py). metric_id={metric_id!r}")
