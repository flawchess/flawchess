"""Unit + Sentry-mock tests for user_benchmark_percentiles_service (Phase 94.2).

Phase 94.2 (D-3a wave-1 cutover):

The 94.1 ``apply_floor`` dual-mode tests are gone — the pooled CTE has an
unconditional ≥30 HAVING clause, so the parameter no longer exists. These
tests cover the pooled-per-user compute path:

- Pure-unit tests (mocked ``session.execute``) verify the SQL shape (single
  query, no ``apply_floor`` kwarg, no ``avg(metric_value)`` wrapper) and the
  return-type widening to ``tuple[float, int] | None``.
- ``compute_stage_a`` / ``compute_stage_b`` public signatures are pinned via
  ``inspect.signature`` so the Stage A/B trigger contract stays byte-identical
  (PCTL-09).
- Stage A/B fan-out tests assert ``upsert_percentile`` is called exactly the
  right number of times and that ``n_games`` is threaded through correctly.
- The real-DB zero-canonical-games happy path is preserved (asserts NO row
  written when ``_compute_metric_for_user`` returns None).
- Sentry-mock tests confirm exceptions are swallowed and ``set_context`` is
  invoked with ``{"user_id": ..., "stage": "A" | "B"}`` (D-04, V4).

Design decisions exercised:

- D-04: Stage A/B non-blocking — exceptions swallowed, Sentry captured
- D-9-amend: ``tuple[float, int] | None`` return contract
- CLAUDE.md Sentry rules: ``set_context`` carries ``user_id``, message string
  does NOT
- V4 Information Disclosure guard: Sentry context must not leak user_id in
  message
"""

from __future__ import annotations

import inspect
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.user import User
from app.repositories.user_benchmark_percentiles_repository import fetch_for_user
from app.services import user_benchmark_percentiles_service as svc
from app.services.user_benchmark_percentiles_service import (
    STAGE_B_METRICS,
    _compute_metric_for_user,
    compute_stage_a,
    compute_stage_b,
)

# ── Module-level constants (CLAUDE.md: no magic numbers) ─────────────────────
_TEST_USER_ID: int = 99200  # unique per module to avoid FK conflicts
_SENTRY_CONTEXT_KEY: str = "percentile_compute"
_FAKE_VALUE: float = 0.05
_FAKE_N_GAMES: int = 42

# asyncio_mode = "auto" in pyproject.toml — async tests pick it up automatically.
# We avoid module-level `pytestmark = pytest.mark.asyncio` so the sync signature
# / introspection tests below do not emit "marked async but not async" warnings.


# ─────────────────────────────────────────────────────────────────────────────
# Helpers for the unit tests.
# ─────────────────────────────────────────────────────────────────────────────


def _make_mock_session_with_row(
    value: float | None, n_games: int | None
) -> tuple[MagicMock, AsyncMock]:
    """Return (session_mock, execute_mock) where session.execute returns a row.

    If ``value`` or ``n_games`` is None we return that None for the
    corresponding attribute so the helper's ``row.value is None`` /
    ``row.n_games is None`` guards exercise the early-return branch.
    """
    row = MagicMock()
    row.value = value
    row.n_games = n_games

    result = MagicMock()
    result.fetchone.return_value = row

    execute_mock = AsyncMock(return_value=result)
    session = MagicMock()
    session.execute = execute_mock
    return session, execute_mock


def _make_mock_session_with_no_row() -> tuple[MagicMock, AsyncMock]:
    """Return (session_mock, execute_mock) where session.execute returns no row."""
    result = MagicMock()
    result.fetchone.return_value = None

    execute_mock = AsyncMock(return_value=result)
    session = MagicMock()
    session.execute = execute_mock
    return session, execute_mock


# ─────────────────────────────────────────────────────────────────────────────
# Test 1 / Test 2: single query, no apply_floor / no per-cell averaging
# ─────────────────────────────────────────────────────────────────────────────


async def test_compute_metric_runs_single_query() -> None:
    """_compute_metric_for_user runs exactly one session.execute call."""
    session, execute_mock = _make_mock_session_with_row(_FAKE_VALUE, _FAKE_N_GAMES)
    await _compute_metric_for_user(session, _TEST_USER_ID, "score_gap")
    assert execute_mock.call_count == 1, (
        f"_compute_metric_for_user must run one query; got {execute_mock.call_count}"
    )


async def test_compute_metric_sql_omits_apply_floor_and_elo_bucket() -> None:
    """The SQL passed to session.execute contains no apply_floor / elo_bucket."""
    session, execute_mock = _make_mock_session_with_row(_FAKE_VALUE, _FAKE_N_GAMES)
    await _compute_metric_for_user(session, _TEST_USER_ID, "score_gap")

    # First positional arg to execute is the SQLAlchemy TextClause; render its text.
    call_args = execute_mock.call_args
    text_clause = call_args[0][0]
    sql_text = str(text_clause)

    assert "apply_floor" not in sql_text, "pooled compute must NOT reference apply_floor"
    # `elo_bucket` must not appear inside the per_user_values projection.
    # The pooled model groups by user_id only — any elo_bucket reference would
    # indicate a regression to the 94.1 per-cell shape.
    assert "elo_bucket" not in sql_text, (
        "pooled compute must NOT project elo_bucket inside per_user_values"
    )
    assert "avg(metric_value)" not in sql_text, (
        "pooled compute must NOT wrap metric_value in avg() — one row per user"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Test 3 / Test 4: return-type widening + None on no row
# ─────────────────────────────────────────────────────────────────────────────


async def test_compute_metric_returns_tuple_when_row_present() -> None:
    """Returns ``tuple[float, int]`` (NOT a bare float) per D-9-amend."""
    session, _ = _make_mock_session_with_row(_FAKE_VALUE, _FAKE_N_GAMES)
    result = await _compute_metric_for_user(session, _TEST_USER_ID, "score_gap")

    assert result is not None
    assert isinstance(result, tuple), f"expected tuple, got {type(result).__name__}"
    assert len(result) == 2
    value, n_games = result
    assert isinstance(value, float)
    assert isinstance(n_games, int)
    assert n_games >= 0
    assert value == pytest.approx(_FAKE_VALUE)
    assert n_games == _FAKE_N_GAMES


async def test_compute_metric_returns_none_when_no_row() -> None:
    """Returns None when the CTE emits no row (user below ≥30 pooled floor)."""
    session, _ = _make_mock_session_with_no_row()
    result = await _compute_metric_for_user(session, _TEST_USER_ID, "score_gap")
    assert result is None


async def test_compute_metric_returns_none_when_n_games_null() -> None:
    """Returns None if the CTE emits a row with NULL n_games (defensive guard)."""
    session, _ = _make_mock_session_with_row(_FAKE_VALUE, None)
    result = await _compute_metric_for_user(session, _TEST_USER_ID, "score_gap")
    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Stage A / Stage B signatures preserved byte-for-byte (PCTL-09)
# ─────────────────────────────────────────────────────────────────────────────


def test_compute_stage_a_signature_preserved() -> None:
    sig = inspect.signature(compute_stage_a)
    params = list(sig.parameters.values())
    assert params[0].name == "user_id"
    assert params[0].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params[1].name == "session_maker"
    assert params[1].kind == inspect.Parameter.KEYWORD_ONLY
    assert params[1].default is None
    assert sig.return_annotation is None or sig.return_annotation == "None"


def test_compute_stage_b_signature_preserved() -> None:
    sig = inspect.signature(compute_stage_b)
    params = list(sig.parameters.values())
    assert params[0].name == "user_id"
    assert params[0].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert params[1].name == "session_maker"
    assert params[1].kind == inspect.Parameter.KEYWORD_ONLY
    assert params[1].default is None
    assert sig.return_annotation is None or sig.return_annotation == "None"


def test_compute_metric_return_annotation_is_tuple_float_int_optional() -> None:
    """_compute_metric_for_user return annotation widened to tuple[float, int] | None."""
    sig = inspect.signature(_compute_metric_for_user)
    ann = str(sig.return_annotation)
    assert "tuple" in ann.lower() or "Tuple" in ann, (
        f"return annotation must mention tuple; got {ann!r}"
    )


def test_compute_metric_apply_floor_kwarg_is_gone() -> None:
    """Calling _compute_metric_for_user with apply_floor= raises TypeError.

    Regression guard: the 94.1 ``apply_floor`` parameter is removed.
    """
    # We invoke synchronously to inspect parameter binding — TypeError is raised
    # before any await happens because Python validates kwargs at call time.
    sig = inspect.signature(_compute_metric_for_user)
    assert "apply_floor" not in sig.parameters


# ─────────────────────────────────────────────────────────────────────────────
# Test 6 / Test 7 / Test 8: Stage A/B fan-out + n_games threading
# ─────────────────────────────────────────────────────────────────────────────


class _FakeSessionMaker:
    """Minimal async-context-manager-yielding factory for stage tests.

    Returns a MagicMock session whose ``commit`` is an AsyncMock so the
    ``await session.commit()`` in the production code resolves cleanly.
    """

    def __init__(self) -> None:
        self.session = MagicMock()
        self.session.commit = AsyncMock(return_value=None)
        self.session.execute = AsyncMock()

    def __call__(self) -> _FakeSessionMakerCM:
        return _FakeSessionMakerCM(self.session)


class _FakeSessionMakerCM:
    def __init__(self, session: MagicMock) -> None:
        self._session = session

    async def __aenter__(self) -> MagicMock:
        return self._session

    async def __aexit__(self, *args: Any) -> None:
        return None


async def test_compute_stage_a_calls_upsert_once_on_value(monkeypatch) -> None:  # noqa: ANN001
    """Stage A calls upsert_percentile exactly once when the helper returns a tuple."""
    fake_maker = _FakeSessionMaker()
    upsert_mock = AsyncMock(return_value=None)
    interp_mock = MagicMock(return_value=72.5)

    async def fake_compute(*args: Any, **kwargs: Any) -> tuple[float, int]:
        return (_FAKE_VALUE, _FAKE_N_GAMES)

    monkeypatch.setattr(svc, "_compute_metric_for_user", fake_compute)
    monkeypatch.setattr(svc, "upsert_percentile", upsert_mock)
    monkeypatch.setattr(svc, "interpolate_percentile", interp_mock)

    await compute_stage_a(_TEST_USER_ID, session_maker=fake_maker)  # ty: ignore[invalid-argument-type]  # fake_maker mirrors async_sessionmaker protocol for unit-test isolation

    assert upsert_mock.call_count == 1
    kwargs = upsert_mock.call_args.kwargs
    assert kwargs["n_games"] == _FAKE_N_GAMES, "n_games must be threaded into the UPSERT"
    assert kwargs["value"] == pytest.approx(_FAKE_VALUE)
    assert kwargs["metric"] == "score_gap"
    assert kwargs["user_id"] == _TEST_USER_ID


async def test_compute_stage_a_skips_upsert_on_none(monkeypatch) -> None:  # noqa: ANN001
    """Stage A calls upsert_percentile zero times when the helper returns None."""
    fake_maker = _FakeSessionMaker()
    upsert_mock = AsyncMock(return_value=None)

    async def fake_compute(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(svc, "_compute_metric_for_user", fake_compute)
    monkeypatch.setattr(svc, "upsert_percentile", upsert_mock)

    await compute_stage_a(_TEST_USER_ID, session_maker=fake_maker)  # ty: ignore[invalid-argument-type]  # fake_maker mirrors async_sessionmaker protocol for unit-test isolation

    assert upsert_mock.call_count == 0


async def test_compute_stage_b_calls_upsert_once_per_metric(monkeypatch) -> None:  # noqa: ANN001
    """Stage B iterates STAGE_B_METRICS and upserts each metric that returns a value.

    Also pins the per-metric isolation contract: the inner try/except is still in
    place, and a tuple-returning helper for every metric yields ``len(STAGE_B_METRICS)``
    upsert calls.
    """
    fake_maker = _FakeSessionMaker()
    upsert_mock = AsyncMock(return_value=None)
    interp_mock = MagicMock(return_value=50.0)

    async def fake_compute(*args: Any, **kwargs: Any) -> tuple[float, int]:
        return (_FAKE_VALUE, _FAKE_N_GAMES)

    monkeypatch.setattr(svc, "_compute_metric_for_user", fake_compute)
    monkeypatch.setattr(svc, "upsert_percentile", upsert_mock)
    monkeypatch.setattr(svc, "interpolate_percentile", interp_mock)

    await compute_stage_b(_TEST_USER_ID, session_maker=fake_maker)  # ty: ignore[invalid-argument-type]  # fake_maker mirrors async_sessionmaker protocol for unit-test isolation

    assert upsert_mock.call_count == len(STAGE_B_METRICS) == 3
    upserted_metrics = {call.kwargs["metric"] for call in upsert_mock.call_args_list}
    assert upserted_metrics == set(STAGE_B_METRICS)
    # Every call threads n_games through.
    for call in upsert_mock.call_args_list:
        assert call.kwargs["n_games"] == _FAKE_N_GAMES


async def test_compute_stage_b_skips_metric_returning_none(monkeypatch) -> None:  # noqa: ANN001
    """Stage B skips upsert for a metric whose helper returns None, keeps the rest."""
    fake_maker = _FakeSessionMaker()
    upsert_mock = AsyncMock(return_value=None)
    interp_mock = MagicMock(return_value=50.0)

    async def fake_compute(session: Any, user_id: int, metric_id: str) -> tuple[float, int] | None:
        if metric_id == "section2_score_gap_parity":
            return None
        return (_FAKE_VALUE, _FAKE_N_GAMES)

    monkeypatch.setattr(svc, "_compute_metric_for_user", fake_compute)
    monkeypatch.setattr(svc, "upsert_percentile", upsert_mock)
    monkeypatch.setattr(svc, "interpolate_percentile", interp_mock)

    await compute_stage_b(_TEST_USER_ID, session_maker=fake_maker)  # ty: ignore[invalid-argument-type]  # fake_maker mirrors async_sessionmaker protocol for unit-test isolation

    upserted_metrics = {call.kwargs["metric"] for call in upsert_mock.call_args_list}
    assert upserted_metrics == {"achievable_score_gap", "section2_score_gap_conv"}


# ─────────────────────────────────────────────────────────────────────────────
# Stage A: zero canonical games (real DB) — preserved from 94.1
# ─────────────────────────────────────────────────────────────────────────────


async def test_compute_stage_a_zero_canonical_games(test_engine) -> None:  # noqa: ANN001
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
        # Run Stage A — should produce no row (helper returns None → early exit).
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


# ─────────────────────────────────────────────────────────────────────────────
# Sentry non-propagation tests (mocked) — preserved from 94.1, updated for
# the tuple-return contract.
# ─────────────────────────────────────────────────────────────────────────────


async def test_compute_stage_a_swallows_exception_and_captures_sentry(
    monkeypatch,  # noqa: ANN001
) -> None:
    """compute_stage_a returns None (never propagates) when an internal helper
    raises. Sentry captures the exception with set_context("percentile_compute",
    {"user_id": ..., "stage": "A"}).

    V4 Information Disclosure guard: assert the captured exception message does
    NOT contain the user_id string (only set_context carries it).

    Per D-04: Stage A errors must not propagate to the import worker.
    CLAUDE.md Backend Rules: sentry_sdk.set_context + capture_exception.
    """
    captured_contexts: list[dict] = []
    captured_exceptions: list[Exception] = []

    def fake_set_context(key: str, value: dict) -> None:
        captured_contexts.append({"key": key, "value": value})

    def fake_capture_exception(exc: Exception) -> None:
        captured_exceptions.append(exc)

    error_message = "simulated compute failure"

    # Patch _compute_metric_for_user to return a (value, n_games) tuple so we
    # reach interpolate_percentile (the early-exit path otherwise short-circuits
    # before any chance of an exception). Then make interpolate_percentile
    # raise, triggering the Sentry capture path.
    # Phase 94.2: _compute_metric_for_user returns tuple[float, int] | None.
    async def fake_compute(*args: Any, **kwargs: Any) -> tuple[float, int]:
        return (_FAKE_VALUE, _FAKE_N_GAMES)

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
    monkeypatch,  # noqa: ANN001
) -> None:
    """compute_stage_b returns None (never propagates) when one metric's CTE
    execution raises. Sentry captures with set_context("percentile_compute",
    {"user_id": ..., "stage": "B"}).

    V4 guard: user_id does NOT appear in the captured exception message string.
    set_context MUST carry {"user_id": ..., "stage": "B"}.
    """
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
    # Phase 94.2: _compute_metric_for_user returns tuple[float, int] | None.
    async def fake_compute(*args: Any, **kwargs: Any) -> tuple[float, int]:
        return (_FAKE_VALUE, _FAKE_N_GAMES)

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
