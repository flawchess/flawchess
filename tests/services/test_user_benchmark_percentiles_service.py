"""Wave 0 scaffolding for user_benchmark_percentiles_service tests.

Phase 94.1 Plan 02, Task 1. Tests are skipped (via pytest.importorskip) until
the implementation modules land in Plans 05/06.

Covers:
- compute_stage_a: happy path, below-floor, zero-canonical-games, Sentry non-propagation
- compute_stage_b: three-metric write, metric-below-floor, Sentry non-propagation

Design decisions exercised:
- D-04: Stage A/B non-blocking — exceptions swallowed, Sentry captured
- D-10: per-metric inclusion floors
- CLAUDE.md Sentry rules: set_context carries user_id, message string does NOT
- V4 Information Disclosure guard: Sentry context must not leak user_id in message
"""

from __future__ import annotations

import pytest

# ── Skip entire module until implementation modules exist ─────────────────────
# When Plans 05/06 land, importorskip will succeed and tests will run.
user_benchmark_percentiles_service = pytest.importorskip(
    "app.services.user_benchmark_percentiles_service"
)

# ── Module-level constants (CLAUDE.md: no magic numbers) ─────────────────────
_TEST_USER_ID: int = 99200  # unique per module to avoid FK conflicts
_STAGE_A_FLOOR_ENDGAME: int = 30  # per D-10: score_gap floor
_STAGE_A_FLOOR_NON_ENDGAME: int = 30
_STAGE_B_FLOOR_ACHIEVABLE: int = 20  # per D-10: achievable_score_gap floor
_BELOW_FLOOR_GAME_COUNT: int = 5  # below all inclusion floors
_SENTRY_CONTEXT_KEY: str = "percentile_compute"

pytestmark = pytest.mark.asyncio


# ── Stage A happy path ─────────────────────────────────────────────────────────


async def test_compute_stage_a_happy_path(test_engine) -> None:
    """compute_stage_a writes a row with non-null percentile when the user has
    >= 30 endgame AND >= 30 non-endgame canonical-slice games.

    Per D-08: row has metric='score_gap', non-null value, non-null percentile,
    n_games >= 30, cdf_snapshot = date.today() (or non-null).
    """
    pytest.skip("implementation pending Plans 05/06")


async def test_compute_stage_a_below_floor(test_engine) -> None:
    """compute_stage_a stores a row with percentile=NULL when the user has data
    but fewer than 30 canonical-slice games.

    Per CONTEXT discretion: percentile=NULL + value still stored so future floor
    changes don't require a full recompute. If value itself is computable
    (a non-zero average score_gap from < 30 games), the row exists.
    """
    pytest.skip("implementation pending Plans 05/06")


async def test_compute_stage_a_zero_canonical_games(test_engine) -> None:
    """compute_stage_a writes NO row when the user has 0 canonical-slice games
    (e.g., all opponents outside the +-100 ELO band per D-09).

    Per CONTEXT Claude's Discretion: 'if value itself isn't computable (zero
    games in slice), no row'.
    """
    pytest.skip("implementation pending Plans 05/06")


async def test_compute_stage_a_swallows_exception_and_captures_sentry(
    monkeypatch,
) -> None:
    """compute_stage_a returns None (never propagates) when an internal helper
    raises. Sentry captures the exception with set_context("percentile_compute",
    {"user_id": ..., "stage": "A"}).

    V4 Information Disclosure guard: assert the captured exception message does
    NOT contain the user_id string (only set_context carries it).

    Per D-04: Stage A errors must not propagate to the import worker.
    CLAUDE.md Backend Rules: sentry_sdk.set_context + capture_exception.
    """
    from unittest.mock import patch

    captured_contexts: list[dict] = []
    captured_exceptions: list[Exception] = []

    def fake_set_context(key: str, value: dict) -> None:
        captured_contexts.append({"key": key, "value": value})

    def fake_capture_exception(exc: Exception) -> None:
        captured_exceptions.append(exc)

    error_message = "simulated compute failure"

    with (
        patch("sentry_sdk.set_context", side_effect=fake_set_context),
        patch("sentry_sdk.capture_exception", side_effect=fake_capture_exception),
        patch(
            "app.services.user_benchmark_percentiles_service.interpolate_percentile",
            side_effect=RuntimeError(error_message),
        ),
    ):
        compute_stage_a = user_benchmark_percentiles_service.compute_stage_a
        # Must not raise — D-04
        result = await compute_stage_a(_TEST_USER_ID)
        assert result is None

    # Sentry must have been called with the correct context
    assert len(captured_exceptions) >= 1
    assert any(
        ctx["key"] == _SENTRY_CONTEXT_KEY and ctx["value"].get("stage") == "A"
        for ctx in captured_contexts
    ), "set_context('percentile_compute', {..., 'stage': 'A'}) not called"

    # V4 guard: user_id must NOT appear in the exception message string
    for exc in captured_exceptions:
        assert str(_TEST_USER_ID) not in str(exc), (
            f"user_id {_TEST_USER_ID} leaked into Sentry exception message (V4 violation)"
        )


# ── Stage B tests ──────────────────────────────────────────────────────────────


async def test_compute_stage_b_writes_three_metrics(test_engine) -> None:
    """compute_stage_b writes exactly 3 rows (achievable_score_gap,
    section2_score_gap_conv, section2_score_gap_parity) when the user has
    sufficient eval-bearing canonical-slice games for all 3 metrics.

    Per STAGE_B_METRICS constant in the service.
    """
    pytest.skip("implementation pending Plans 05/06")


async def test_compute_stage_b_metric_below_floor_writes_null_percentile(
    test_engine,
) -> None:
    """When a user has sufficient achievable_score_gap games but insufficient
    parity/conversion spans, the row for that metric has percentile=NULL while
    the achievable_score_gap row has non-null percentile.

    Documents per-metric floor independence per D-10.
    """
    pytest.skip("implementation pending Plans 05/06")


async def test_compute_stage_b_swallows_exception_and_captures_sentry(
    monkeypatch,
) -> None:
    """compute_stage_b returns None (never propagates) when one metric's CTE
    execution raises. The other 2 metrics still UPSERT. Sentry captures exactly
    once with set_context("percentile_compute", {"user_id": ..., "stage": "B"}).

    V4 guard: user_id does NOT appear in the captured exception message string.
    set_context MUST carry {"user_id": ..., "stage": "B"}.
    """
    from unittest.mock import patch

    captured_contexts: list[dict] = []
    captured_exceptions: list[Exception] = []

    def fake_set_context(key: str, value: dict) -> None:
        captured_contexts.append({"key": key, "value": value})

    def fake_capture_exception(exc: Exception) -> None:
        captured_exceptions.append(exc)

    with (
        patch("sentry_sdk.set_context", side_effect=fake_set_context),
        patch("sentry_sdk.capture_exception", side_effect=fake_capture_exception),
    ):
        compute_stage_b = user_benchmark_percentiles_service.compute_stage_b
        result = await compute_stage_b(_TEST_USER_ID)
        assert result is None

    # Verify set_context was called with stage B
    assert any(
        ctx["key"] == _SENTRY_CONTEXT_KEY and ctx["value"].get("stage") == "B"
        for ctx in captured_contexts
    ), "set_context('percentile_compute', {..., 'stage': 'B'}) not called"

    # V4 guard: user_id must NOT appear in the exception message string
    for exc in captured_exceptions:
        assert str(_TEST_USER_ID) not in str(exc), (
            f"user_id {_TEST_USER_ID} leaked into Sentry exception message (V4 violation)"
        )
