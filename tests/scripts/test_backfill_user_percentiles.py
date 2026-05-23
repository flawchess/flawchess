"""Wave 0 scaffolding for backfill_user_percentiles script tests (PCTL-10 gate).

Phase 94.1 Plan 02, Task 2.

Tests cover:
- Idempotency: second run produces identical values
- --user-id filter: only processes the specified user
- --metric filter: only processes the specified metric
- --target prod refusal when tunnel is down (Pitfall 6 / SC-6)
- --target dev refusal when URL lacks port 5432
- Per-metric summary table emitted to stdout
- Zero-canonical-games user: no row written, summary reports no_canonical_games=1

Security domain V4 (Tampering — wrong DB target):
- test_backfill_target_prod_refuses_when_tunnel_down: _assert_target_safe raises
  SystemExit with message containing 'bin/prod_db_tunnel.sh' when port 15432
  has no listener.
- test_backfill_target_dev_refuses_url_without_port_5432: _assert_target_safe
  raises SystemExit with message containing '5432' for a non-5432 port URL.

Skip mechanism: pytest.importorskip on scripts.backfill_user_percentiles causes
the entire module to skip until the script is implemented in Plan 08.

Note on import strategy: _assert_target_safe is a pure function (no DB I/O)
that we import directly. The full main() function is invoked via direct call
(not subprocess) since the script lives under scripts/ and sys.path is already
configured by the test conftest.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ── Bootstrap scripts/ on sys.path if not already present ────────────────────
# The scripts/ directory lives one level above app/ — the same pattern as
# backfill_eval.py which uses `sys.path.insert(0, ...)` inside the script.
# For tests we bootstrap it here so pytest's import machinery resolves
# `scripts.backfill_user_percentiles` without needing the script's own
# sys.path insert to have run.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── Skip entire module until implementation exists ────────────────────────────
backfill_user_percentiles = pytest.importorskip("scripts.backfill_user_percentiles")

# ── Module-level constants (CLAUDE.md: no magic numbers) ─────────────────────
_TEST_USER_1_ID: int = 99206  # unique per module to avoid FK conflicts
_TEST_USER_2_ID: int = 99207
_TEST_USER_3_ID: int = 99208
_PROD_TUNNEL_PORT: int = 15432  # per CLAUDE.md / bin/prod_db_tunnel.sh
_DEV_PORT: int = 5432           # per CLAUDE.md dev DB port
_DUMMY_NON_5432_PORT: int = 99999

# Expected summary tokens per metric (from CONTEXT §Specifics backfill output shape)
_EXPECTED_METRIC_LABELS: list[str] = [
    "score_gap",
    "achievable_score_gap",
    "section2_score_gap_conv",
    "section2_score_gap_parity",
]
_EXPECTED_SUMMARY_TOKENS: list[str] = ["upserted=", "skipped="]

pytestmark = pytest.mark.asyncio


# ── Idempotency ───────────────────────────────────────────────────────────────


async def test_backfill_is_idempotent_when_run_twice(test_engine) -> None:
    """Two sequential runs of main() against the same 3-user fixture produce
    identical user_benchmark_percentiles rows.

    First run: seeds rows for all 3 users.
    Second run: values unchanged, computed_at may advance but value/percentile match.
    Row count must be the same after both runs (UPSERT idempotency per D-08).
    """
    pytest.skip("implementation pending Plan 08")


async def test_backfill_with_user_id_filter_only_processes_that_user(
    test_engine,
) -> None:
    """main() with --user-id=user_2 only touches user_2's rows.

    Asserts: computed_at advances for user_2; users 1 and 3 are unchanged
    or absent from user_benchmark_percentiles.
    """
    pytest.skip("implementation pending Plan 08")


async def test_backfill_with_metric_filter_only_processes_that_metric(
    test_engine,
) -> None:
    """main() with --metric=score_gap only writes score_gap rows.

    Asserts: other 3 metrics (achievable_score_gap, section2_*) are untouched
    (absent or computed_at unchanged if rows pre-exist).
    """
    pytest.skip("implementation pending Plan 08")


# ── Target safety guards (Pitfall 6 / SC-6 / V4 Tampering) ──────────────────


def test_backfill_target_prod_refuses_when_tunnel_down() -> None:
    """_assert_target_safe(url_with_port_15432, 'prod') raises SystemExit when
    no socket listener exists on localhost:15432.

    The error message must contain 'bin/prod_db_tunnel.sh' so the operator
    knows exactly what to run. This is the PCTL-10 safety gate against
    accidental cross-env writes (Pitfall 6 / V4 Tampering).

    Note: the test relies on no actual tunnel being active during CI. If the
    test DB also uses port 15432 by coincidence, this test would be flaky —
    but the test DB is on 5432 and the prod tunnel is always off in CI.
    """
    _assert_target_safe = backfill_user_percentiles._assert_target_safe
    url_with_prod_port = f"postgresql://user:pass@localhost:{_PROD_TUNNEL_PORT}/flawchess"
    with pytest.raises(SystemExit) as exc_info:
        _assert_target_safe(url_with_prod_port, "prod")
    # Message must reference the tunnel script for operator clarity
    assert "bin/prod_db_tunnel.sh" in str(exc_info.value), (
        "SystemExit message should mention bin/prod_db_tunnel.sh (Pitfall 6 operator guide)"
    )


def test_backfill_target_dev_refuses_url_without_port_5432() -> None:
    """_assert_target_safe(url_with_wrong_port, 'dev') raises SystemExit when
    the URL does not contain ':5432'.

    The error message must contain '5432' so the operator knows the expected port.
    Guards against a misconfigured BACKFILL_DEV_DB_URL override.
    """
    _assert_target_safe = backfill_user_percentiles._assert_target_safe
    wrong_port_url = f"postgresql://user:pass@localhost:{_DUMMY_NON_5432_PORT}/flawchess"
    with pytest.raises(SystemExit) as exc_info:
        _assert_target_safe(wrong_port_url, "dev")
    assert str(_DEV_PORT) in str(exc_info.value), (
        f"SystemExit message should mention port {_DEV_PORT} (expected dev port)"
    )


# ── Summary output ────────────────────────────────────────────────────────────


async def test_backfill_emits_per_metric_summary(
    test_engine,
    capsys,
) -> None:
    """Running backfill on a 3-user fixture emits a summary table to stdout
    containing all 4 metric labels and 'upserted=' + 'skipped=' tokens.

    Per CONTEXT §Specifics backfill output shape:
        score_gap                      upserted=X, skipped=Y (...)
        achievable_score_gap           upserted=X, skipped=Y (...)
        section2_score_gap_conv        upserted=X, skipped=Y (...)
        section2_score_gap_parity      upserted=X, skipped=Y (...)
    """
    pytest.skip("implementation pending Plan 08")


# ── Zero-canonical-games edge case ────────────────────────────────────────────


async def test_backfill_handles_user_with_zero_canonical_slice_games(
    test_engine,
    capsys,
) -> None:
    """When a user has games but all are outside the +-100 ELO opponent band
    (or otherwise excluded by the canonical-slice filter), backfill writes NO
    row for that user.

    The summary table must report no_canonical_games=1 (or equivalent token)
    for that user, not a skipped/below_floor entry.

    Per CONTEXT Claude's Discretion: 'if value itself isn't computable (zero
    games in slice), no row'.
    """
    pytest.skip("implementation pending Plan 08")
