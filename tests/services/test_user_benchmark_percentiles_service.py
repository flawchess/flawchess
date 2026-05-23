"""Sentry-mock and zero-game tests for user_benchmark_percentiles_service.

Phase 94.1 Plan 09 (gap-closure) cleanup:

The 4 heavy-seed scaffold tests previously in this module
(`test_compute_stage_a_happy_path`, `test_compute_stage_a_below_floor`,
`test_compute_stage_b_writes_three_metrics`,
`test_compute_stage_b_metric_below_floor_writes_null_percentile`) were
`pytest.skip("implementation pending Plans 05/06")` placeholders that masked
the runtime bug closed in VERIFICATION.md gap #1. They are DELETED, not
tombstoned: the real assertions live in
`tests/services/test_user_benchmark_percentiles_service_real_data.py`, which
seeds a user with canonical-slice-qualifying games and asserts
`compute_stage_a` / `compute_stage_b` actually persist rows.

What remains here:
- Zero-canonical-games happy path (real DB, asserts NO row written)
- Stage A Sentry non-propagation (mocked)
- Stage B Sentry non-propagation (mocked)

Design decisions exercised:
- D-04: Stage A/B non-blocking — exceptions swallowed, Sentry captured
- CLAUDE.md Sentry rules: set_context carries user_id, message string does NOT
- V4 Information Disclosure guard: Sentry context must not leak user_id in message
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.user import User
from app.repositories.user_benchmark_percentiles_repository import fetch_for_user
from app.services.user_benchmark_percentiles_service import (
    compute_stage_a,
    compute_stage_b,
)

# ── Module-level constants (CLAUDE.md: no magic numbers) ─────────────────────
_TEST_USER_ID: int = 99200  # unique per module to avoid FK conflicts
_SENTRY_CONTEXT_KEY: str = "percentile_compute"

pytestmark = pytest.mark.asyncio


# ── Stage A: zero canonical games (real DB) ───────────────────────────────────


async def test_compute_stage_a_zero_canonical_games(test_engine) -> None:
    """compute_stage_a writes NO row when the user has 0 canonical-slice games.

    Per CONTEXT Claude's Discretion: "if value itself isn't computable (zero
    games in slice), no row".

    Real-DB body: builds a transactional session_maker bound to the test
    engine, creates a fresh User row with no games, calls compute_stage_a,
    asserts fetch_for_user returns an empty dict, then deletes the user.
    """
    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

    # Create a fresh user with no games. We use a unique email per test run.
    async with test_session_maker() as session:
        user = User(
            email=f"stage-a-zero-{uuid.uuid4()}@example.com",
            hashed_password="x",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    try:
        # Run Stage A — should produce no row (value is None → early exit).
        await compute_stage_a(user_id, session_maker=test_session_maker)

        async with test_session_maker() as session:
            rows = await fetch_for_user(session, user_id=user_id)
        assert rows == {}, (
            f"compute_stage_a wrote a row for a user with zero canonical-slice "
            f"games (expected empty dict, got {rows!r})"
        )
    finally:
        async with test_session_maker() as session:
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()


# ── Sentry non-propagation tests (mocked) ─────────────────────────────────────


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

    # Patch _compute_metric_for_user to return a non-None value so we reach
    # interpolate_percentile (the early-exit path otherwise short-circuits
    # before any chance of an exception). Then make interpolate_percentile
    # raise, triggering the Sentry capture path.
    async def fake_compute(*args, **kwargs):  # noqa: ANN001, ANN201, ARG001
        return (0.05, 5)

    with (
        patch("sentry_sdk.set_context", side_effect=fake_set_context),
        patch("sentry_sdk.capture_exception", side_effect=fake_capture_exception),
        patch(
            "app.services.user_benchmark_percentiles_service._compute_metric_for_user",
            side_effect=fake_compute,
        ),
        patch(
            "app.services.user_benchmark_percentiles_service.interpolate_percentile",
            side_effect=RuntimeError(error_message),
        ),
    ):
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


async def test_compute_stage_b_swallows_exception_and_captures_sentry(
    monkeypatch,
) -> None:
    """compute_stage_b returns None (never propagates) when one metric's CTE
    execution raises. Sentry captures with set_context("percentile_compute",
    {"user_id": ..., "stage": "B"}).

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

    # Same shape as Stage A: ensure we hit a meaningful exception path by
    # forcing _compute_metric_for_user to return a value, then making
    # interpolate_percentile raise. Stage B's per-metric inner try/except
    # captures + continues — every loop iteration trips the same exception
    # and emits one set_context("...", {"stage": "B", "metric": ...}) call.
    async def fake_compute(*args, **kwargs):  # noqa: ANN001, ANN201, ARG001
        return (0.05, 5)

    with (
        patch("sentry_sdk.set_context", side_effect=fake_set_context),
        patch("sentry_sdk.capture_exception", side_effect=fake_capture_exception),
        patch(
            "app.services.user_benchmark_percentiles_service._compute_metric_for_user",
            side_effect=fake_compute,
        ),
        patch(
            "app.services.user_benchmark_percentiles_service.interpolate_percentile",
            side_effect=RuntimeError("simulated stage B failure"),
        ),
    ):
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
