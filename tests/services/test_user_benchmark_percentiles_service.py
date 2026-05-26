"""Unit + real-DB tests for user_benchmark_percentiles_service (Phase 94.4 Plan 05b).

Phase 94.4 Plan 05b rewrites the service to consume the cohort CDF artifact
(``COHORT_PERCENTILE_CDF`` via ``interpolate_cohort_percentile``) and the
per-(user, TC) median rating anchor (``user_rating_anchors``). The post-94.3
``STAGE_B_METRICS`` 12-tuple retires; Stage B now iterates the 7-tuple
``STAGE_B_METRIC_FAMILIES`` × the user's above-floor TCs.

Test coverage (10 behaviors per Plan 05b Task 2):

  T1.  Stage A on a Lichess-only user (rapid) → anchor with
       ``source_platform='lichess'`` and ``chesscom_raw_rating=None``.
  T2.  Stage A on a chess.com-only user (blitz) → anchor with
       ``source_platform='chesscom'``, ``chesscom_raw_rating`` populated
       PRE-conversion, and ``anchor_rating`` set to the Lichess-equivalent
       (D-07 bullet 4 + D-12).
  T3.  Stage A on a mixed-platform user (rapid) → anchor with
       ``source_platform='lichess'`` (D-12 Lichess-precedence).
  T4.  Stage A on a chess.com-only Daily user (classical bucket) → NO
       classical anchor row (chess.com Daily has no ChessGoals mapping;
       convert_chesscom_to_lichess returns None, chip suppresses).
  T5.  Stage A computes score_gap percentile ONLY for TCs where an anchor
       exists.
  T6.  Stage B fans out across STAGE_B_METRIC_FAMILIES (7-tuple) × the
       user's anchored TCs.
  T7.  ``upsert_percentile`` is called with the new 3-column PK tuple
       (user_id, metric, time_control_bucket).
  T8.  When ``interpolate_cohort_percentile`` returns None (suppressed
       cell), the row still upserts with ``percentile=None`` and
       ``value`` + ``n_games`` populated.
  T9.  Sentry ``capture_exception`` fires on a metric-compute failure;
       ``set_context`` carries the variable data per CLAUDE.md.
  T10. ``chesscom_raw_rating`` round-trip — the persisted anchor's
       ``chesscom_raw_rating`` matches the chess.com median BEFORE the
       ChessGoals conversion (chess.com path) or is None (Lichess path).
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.game import Game
from app.models.user import User
from app.models.user_rating_anchors import TimeControlBucket
from app.repositories.user_rating_anchors_repository import fetch_anchors_for_user
from app.services import user_benchmark_percentiles_service as svc
from app.services.chesscom_to_lichess import convert_chesscom_to_lichess
from app.services.user_benchmark_percentiles_service import (
    STAGE_A_METRIC,
    STAGE_B_METRIC_FAMILIES,
    compute_anchors_for_user,
    compute_stage_a,
    compute_stage_b,
)

# ── Module-level constants (CLAUDE.md no-magic-numbers) ──────────────────────

_SENTRY_CONTEXT_KEY: str = "percentile_compute"
_FAKE_VALUE: float = 0.05
_FAKE_N_GAMES: int = 42

# Median-anchor floor is 30 games (MEDIAN_ANCHOR_MIN_GAMES per
# canonical_slice_sql). Seed comfortably above for the platform-mode tests.
_ANCHOR_FLOOR_GAMES: int = 35
_USER_RATING_LICHESS_RAPID: int = 1620
_USER_RATING_CHESSCOM_BLITZ: int = 1330
_OPP_RATING_OFFSET: int = 30  # within ±100 equal-footing tolerance


# ─────────────────────────────────────────────────────────────────────────────
# Test 6 / signature-preservation unit tests (no DB)
# ─────────────────────────────────────────────────────────────────────────────


def test_stage_a_metric_is_score_gap() -> None:
    """Plan 05b: STAGE_A_METRIC stays ``score_gap`` (eval-independent)."""
    assert STAGE_A_METRIC == "score_gap"


def test_stage_b_metric_families_is_7_tuple() -> None:
    """STAGE_B_METRIC_FAMILIES is the 7-tuple per CONTEXT D-13."""
    assert isinstance(STAGE_B_METRIC_FAMILIES, tuple)
    assert len(STAGE_B_METRIC_FAMILIES) == 7
    assert STAGE_B_METRIC_FAMILIES == (
        "achievable_score_gap",
        "section2_score_gap_conv",
        "section2_score_gap_parity",
        "recovery_score_gap",
        "time_pressure_score_gap",
        "clock_gap",
        "net_flag_rate",
    )


def test_stage_b_metric_families_excludes_score_gap() -> None:
    """``score_gap`` is owned by Stage A — never iterated in Stage B."""
    assert STAGE_A_METRIC not in STAGE_B_METRIC_FAMILIES


def test_legacy_stage_b_metrics_constant_removed() -> None:
    """Plan 05b retires the post-94.3 12-tuple ``STAGE_B_METRICS`` constant.

    Acceptance criterion: ``grep STAGE_B_METRICS\\b`` returns 0 hits in the
    service. Mirror the criterion at the Python level.
    """
    assert not hasattr(svc, "STAGE_B_METRICS"), (
        "Legacy STAGE_B_METRICS constant must not be re-exported by the service module"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Mocked-fan-out tests for Stage A / Stage B (Test 5, T6, T7, T8, T9).
# ─────────────────────────────────────────────────────────────────────────────


class _FakeSessionMaker:
    """Minimal async-context-manager-yielding factory.

    Returns a MagicMock session whose ``commit`` and ``execute`` are
    AsyncMocks so the production code's awaits resolve cleanly.
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


def _make_anchor_row(
    *,
    tc: TimeControlBucket = "blitz",
    anchor_rating: int = 1700,
    source_platform: str = "lichess",
    chesscom_raw_rating: int | None = None,
    n_games: int = _ANCHOR_FLOOR_GAMES,
) -> Any:
    """Construct a RatingAnchorRow with sensible defaults."""
    from app.repositories.user_rating_anchors_repository import RatingAnchorRow

    return RatingAnchorRow(
        anchor_rating=anchor_rating,
        source_platform=source_platform,  # ty: ignore[invalid-argument-type]
        chesscom_raw_rating=chesscom_raw_rating,
        n_games=n_games,
    )


async def test_compute_stage_a_score_gap_only_runs_for_anchored_tcs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T5: Stage A's score_gap percentile loop runs ONLY for TCs with anchors."""
    fake_maker = _FakeSessionMaker()
    test_user_id = 99500

    # Two anchors only — bullet + rapid (no blitz, no classical).
    fake_anchors = {
        "bullet": _make_anchor_row(tc="bullet", anchor_rating=1800),
        "rapid": _make_anchor_row(tc="rapid", anchor_rating=1700),
    }

    async def fake_compute_anchors(session: Any, user_id: int) -> dict[Any, Any]:
        return fake_anchors

    upsert_mock = AsyncMock(return_value=None)
    interp_mock = MagicMock(return_value=72.5)

    async def fake_compute_metric(
        session: Any, user_id: int, family: Any, tc: Any
    ) -> tuple[float, int]:
        return (_FAKE_VALUE, _FAKE_N_GAMES)

    monkeypatch.setattr(svc, "compute_anchors_for_user", fake_compute_anchors)
    monkeypatch.setattr(svc, "_compute_metric_for_user_per_tc", fake_compute_metric)
    monkeypatch.setattr(svc, "upsert_percentile", upsert_mock)
    monkeypatch.setattr(svc, "interpolate_cohort_percentile", interp_mock)

    await compute_stage_a(test_user_id, session_maker=fake_maker)  # ty: ignore[invalid-argument-type]

    # Exactly 2 upsert calls — one per anchored TC.
    assert upsert_mock.call_count == 2
    upserted_tcs = {call.kwargs["time_control_bucket"] for call in upsert_mock.call_args_list}
    assert upserted_tcs == {"bullet", "rapid"}
    # Every upsert is for score_gap (T7: 3-column PK tuple).
    for call in upsert_mock.call_args_list:
        assert call.kwargs["metric"] == "score_gap"
        assert call.kwargs["user_id"] == test_user_id
        assert "time_control_bucket" in call.kwargs


async def test_compute_stage_b_fans_out_across_families_and_anchored_tcs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T6: Stage B iterates STAGE_B_METRIC_FAMILIES × anchored TCs.

    Setup: 2 anchored TCs (bullet, blitz). Expected:
      len(STAGE_B_METRIC_FAMILIES) × 2 = 7 × 2 = 14 upsert calls.
    """
    fake_maker = _FakeSessionMaker()
    test_user_id = 99501

    fake_anchors = {
        "bullet": _make_anchor_row(tc="bullet", anchor_rating=1800),
        "blitz": _make_anchor_row(tc="blitz", anchor_rating=1750),
    }

    async def fake_fetch_anchors(session: Any, *, user_id: int) -> dict[Any, Any]:
        return fake_anchors

    upsert_mock = AsyncMock(return_value=None)
    interp_mock = MagicMock(return_value=50.0)

    async def fake_compute_metric(
        session: Any, user_id: int, family: Any, tc: Any
    ) -> tuple[float, int]:
        return (_FAKE_VALUE, _FAKE_N_GAMES)

    monkeypatch.setattr(svc, "fetch_anchors_for_user", fake_fetch_anchors)
    monkeypatch.setattr(svc, "_compute_metric_for_user_per_tc", fake_compute_metric)
    monkeypatch.setattr(svc, "upsert_percentile", upsert_mock)
    monkeypatch.setattr(svc, "interpolate_cohort_percentile", interp_mock)

    await compute_stage_b(test_user_id, session_maker=fake_maker)  # ty: ignore[invalid-argument-type]

    expected_calls = len(STAGE_B_METRIC_FAMILIES) * len(fake_anchors)
    assert upsert_mock.call_count == expected_calls == 14

    upserted_metrics = {call.kwargs["metric"] for call in upsert_mock.call_args_list}
    assert upserted_metrics == set(STAGE_B_METRIC_FAMILIES)

    for call in upsert_mock.call_args_list:
        assert call.kwargs["time_control_bucket"] in fake_anchors
        assert call.kwargs["n_games"] == _FAKE_N_GAMES
        assert "user_id" in call.kwargs


async def test_compute_stage_b_noop_when_no_anchors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stage B exits early when ``fetch_anchors_for_user`` returns empty dict."""
    fake_maker = _FakeSessionMaker()
    test_user_id = 99502

    async def fake_fetch_anchors(session: Any, *, user_id: int) -> dict[Any, Any]:
        return {}

    upsert_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(svc, "fetch_anchors_for_user", fake_fetch_anchors)
    monkeypatch.setattr(svc, "upsert_percentile", upsert_mock)

    await compute_stage_b(test_user_id, session_maker=fake_maker)  # ty: ignore[invalid-argument-type]

    assert upsert_mock.call_count == 0


async def test_upsert_called_with_3_column_pk_tuple(monkeypatch: pytest.MonkeyPatch) -> None:
    """T7: ``upsert_percentile`` invocation includes user_id + metric + time_control_bucket."""
    fake_maker = _FakeSessionMaker()
    test_user_id = 99503

    async def fake_compute_anchors(session: Any, user_id: int) -> dict[Any, Any]:
        return {"rapid": _make_anchor_row(tc="rapid", anchor_rating=1700)}

    upsert_mock = AsyncMock(return_value=None)
    interp_mock = MagicMock(return_value=50.0)

    async def fake_compute_metric(
        session: Any, user_id: int, family: Any, tc: Any
    ) -> tuple[float, int]:
        return (_FAKE_VALUE, _FAKE_N_GAMES)

    monkeypatch.setattr(svc, "compute_anchors_for_user", fake_compute_anchors)
    monkeypatch.setattr(svc, "_compute_metric_for_user_per_tc", fake_compute_metric)
    monkeypatch.setattr(svc, "upsert_percentile", upsert_mock)
    monkeypatch.setattr(svc, "interpolate_cohort_percentile", interp_mock)

    await compute_stage_a(test_user_id, session_maker=fake_maker)  # ty: ignore[invalid-argument-type]

    assert upsert_mock.call_count == 1
    kwargs = upsert_mock.call_args.kwargs
    assert kwargs["user_id"] == test_user_id
    assert kwargs["metric"] == "score_gap"
    assert kwargs["time_control_bucket"] == "rapid"
    assert kwargs["value"] == pytest.approx(_FAKE_VALUE)
    assert kwargs["n_games"] == _FAKE_N_GAMES


async def test_upsert_runs_with_percentile_none_for_suppressed_cell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T8: When the cohort CDF cell is absent (interpolate returns None) the row
    is still upserted with percentile=None and value + n_games populated.

    Suppression at the cohort-CDF lookup must NOT short-circuit the upsert —
    the API shaper consumes ``value`` even when no peer-relative percentile
    can be assigned.
    """
    fake_maker = _FakeSessionMaker()
    test_user_id = 99504

    async def fake_compute_anchors(session: Any, user_id: int) -> dict[Any, Any]:
        return {"blitz": _make_anchor_row(tc="blitz", anchor_rating=1750)}

    upsert_mock = AsyncMock(return_value=None)
    interp_mock = MagicMock(return_value=None)  # ← suppressed cell

    async def fake_compute_metric(
        session: Any, user_id: int, family: Any, tc: Any
    ) -> tuple[float, int]:
        return (_FAKE_VALUE, _FAKE_N_GAMES)

    monkeypatch.setattr(svc, "compute_anchors_for_user", fake_compute_anchors)
    monkeypatch.setattr(svc, "_compute_metric_for_user_per_tc", fake_compute_metric)
    monkeypatch.setattr(svc, "upsert_percentile", upsert_mock)
    monkeypatch.setattr(svc, "interpolate_cohort_percentile", interp_mock)

    await compute_stage_a(test_user_id, session_maker=fake_maker)  # ty: ignore[invalid-argument-type]

    assert upsert_mock.call_count == 1
    kwargs = upsert_mock.call_args.kwargs
    assert kwargs["percentile"] is None
    assert kwargs["value"] == pytest.approx(_FAKE_VALUE)
    assert kwargs["n_games"] == _FAKE_N_GAMES


async def test_compute_stage_a_sentry_capture_on_metric_compute_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T9: When the per-TC metric compute raises, Sentry captures with set_context.

    CLAUDE.md Sentry rules: variable data flows into set_context (user_id,
    stage, metric, tc) — NOT into the exception message string. The
    per-TC try/except catches the error and Stage A keeps processing
    other TCs.
    """
    captured_contexts: list[dict] = []
    captured_exceptions: list[Exception] = []

    def fake_set_context(key: str, value: dict) -> None:
        captured_contexts.append({"key": key, "value": value})

    def fake_capture_exception(exc: Exception) -> None:
        captured_exceptions.append(exc)

    fake_maker = _FakeSessionMaker()
    test_user_id = 99505

    async def fake_compute_anchors(session: Any, user_id: int) -> dict[Any, Any]:
        return {"blitz": _make_anchor_row(tc="blitz", anchor_rating=1750)}

    async def raising_compute_metric(
        session: Any, user_id: int, family: Any, tc: Any
    ) -> tuple[float, int]:
        raise RuntimeError("simulated per-TC compute failure")

    monkeypatch.setattr(svc, "compute_anchors_for_user", fake_compute_anchors)
    monkeypatch.setattr(svc, "_compute_metric_for_user_per_tc", raising_compute_metric)

    with (
        patch("sentry_sdk.set_context", side_effect=fake_set_context),
        patch("sentry_sdk.capture_exception", side_effect=fake_capture_exception),
    ):
        result = await compute_stage_a(test_user_id, session_maker=fake_maker)  # ty: ignore[invalid-argument-type]
        assert result is None  # never propagates

    # Sentry captured the metric-compute failure.
    assert len(captured_exceptions) >= 1
    # set_context carried the variable dimensions (stage A, metric, tc).
    assert any(
        ctx["key"] == _SENTRY_CONTEXT_KEY
        and ctx["value"].get("stage") == "A"
        and ctx["value"].get("metric") == "score_gap"
        and ctx["value"].get("tc") == "blitz"
        for ctx in captured_contexts
    ), "set_context must carry stage='A', metric='score_gap', tc='blitz'"

    # V4 guard: user_id NEVER appears inside the exception message.
    for exc in captured_exceptions:
        assert str(test_user_id) not in str(exc), (
            f"user_id {test_user_id} leaked into Sentry exception message (V4 violation)"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Real-DB tests for compute_anchors_for_user (T1, T2, T3, T4, T10).
#
# pytest-asyncio is configured in ``asyncio_mode = "auto"`` (pyproject.toml)
# so async tests pick the marker up automatically; we avoid a module-level
# ``pytestmark = pytest.mark.asyncio`` because it triggers a "marked async
# but not async" warning on the sync signature/introspection tests above.
# ─────────────────────────────────────────────────────────────────────────────


async def _create_user(session_maker: async_sessionmaker[Any]) -> int:
    """Create a fresh User with unique email; return user_id."""
    async with session_maker() as session:
        user = User(
            email=f"plan-05b-{uuid.uuid4()}@example.com",
            hashed_password="x",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.id


async def _delete_user(session_maker: async_sessionmaker[Any], user_id: int) -> None:
    """Delete a user; CASCADE wipes games, anchors, percentile rows."""
    async with session_maker() as session:
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


def _make_game_for_anchor_test(
    *,
    user_id: int,
    user_color: str,
    platform: str,
    platform_game_id: str,
    time_control_bucket: TimeControlBucket,
    user_rating: int,
    base_dt: datetime.datetime,
    minutes_offset: int,
    is_chesscom_daily: bool = False,
) -> Game:
    """Build a canonical-slice-qualifying Game row for anchor compute tests.

    The Game must satisfy ``_recent_capped_per_tc_cte`` (rated, not a
    computer game, both ratings populated, equal-footing band, within
    the recency window) for ``per_user_cte_median_anchor`` to count it.
    """
    opp_rating = user_rating + _OPP_RATING_OFFSET
    if user_color == "white":
        white_rating, black_rating = user_rating, opp_rating
        white_username, black_username = "me", "opp"
    else:
        white_rating, black_rating = opp_rating, user_rating
        white_username, black_username = "opp", "me"

    if time_control_bucket == "bullet":
        base_seconds: int = 60
    elif time_control_bucket == "blitz":
        base_seconds = 180
    elif time_control_bucket == "rapid":
        base_seconds = 600
    else:
        base_seconds = 1800

    # chess.com Daily games are bucketed `classical` by the import pipeline
    # but their time_control_str starts with "1/" (RESEARCH Pitfall 11).
    if is_chesscom_daily:
        tc_str = "1/86400"
    else:
        tc_str = f"{base_seconds}+0"

    game = Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=platform_game_id,
        pgn="1. e4 e5 *",
        result="1-0" if user_color == "white" else "0-1",
        user_color=user_color,
        time_control_str=tc_str,
        time_control_bucket=time_control_bucket,
        time_control_seconds=base_seconds,
        base_time_seconds=base_seconds,
        rated=True,
        is_computer_game=False,
        white_username=white_username,
        black_username=black_username,
        white_rating=white_rating,
        black_rating=black_rating,
    )
    game.played_at = base_dt + datetime.timedelta(minutes=minutes_offset)
    return game


async def _seed_anchor_games(
    session_maker: async_sessionmaker[Any],
    *,
    user_id: int,
    n_games: int,
    platform: str,
    time_control_bucket: TimeControlBucket,
    user_rating: int,
    is_chesscom_daily: bool = False,
) -> None:
    """Insert ``n_games`` qualifying games for the (platform, TC) cell."""
    base_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    async with session_maker() as session:
        for idx in range(n_games):
            user_color = "white" if idx % 2 == 0 else "black"
            game = _make_game_for_anchor_test(
                user_id=user_id,
                user_color=user_color,
                platform=platform,
                platform_game_id=f"{platform}-{user_id}-{time_control_bucket}-{idx}",
                time_control_bucket=time_control_bucket,
                user_rating=user_rating,
                base_dt=base_dt,
                minutes_offset=idx,
                is_chesscom_daily=is_chesscom_daily,
            )
            session.add(game)
        await session.commit()


async def test_compute_anchors_lichess_only_user_rapid(test_engine) -> None:  # noqa: ANN001
    """T1: Lichess-only user (rapid) → source_platform='lichess', chesscom_raw_rating=None."""
    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    user_id = await _create_user(test_session_maker)

    try:
        await _seed_anchor_games(
            test_session_maker,
            user_id=user_id,
            n_games=_ANCHOR_FLOOR_GAMES,
            platform="lichess",
            time_control_bucket="rapid",
            user_rating=_USER_RATING_LICHESS_RAPID,
        )

        async with test_session_maker() as session:
            anchors = await compute_anchors_for_user(session, user_id)
            await session.commit()

        assert "rapid" in anchors, "Lichess-only user must have a rapid anchor"
        anchor = anchors["rapid"]
        assert anchor.source_platform == "lichess"
        assert anchor.chesscom_raw_rating is None, (
            "Lichess-direct anchor must not carry a chesscom_raw_rating"
        )
        assert anchor.n_games >= _ANCHOR_FLOOR_GAMES
        # No chess.com games — bullet/blitz/classical have no anchor rows.
        assert "bullet" not in anchors
        assert "blitz" not in anchors
        assert "classical" not in anchors

        # Verify persistence round-trip.
        async with test_session_maker() as session:
            persisted = await fetch_anchors_for_user(session, user_id=user_id)
        assert persisted["rapid"].source_platform == "lichess"
        assert persisted["rapid"].chesscom_raw_rating is None
    finally:
        await _delete_user(test_session_maker, user_id)


async def test_compute_anchors_chesscom_only_user_blitz_captures_raw_rating(test_engine) -> None:  # noqa: ANN001
    """T2 + T10: chess.com-only user (blitz) — anchor uses Lichess-equivalent for
    anchor_rating; chesscom_raw_rating holds the PRE-conversion chess.com median
    (D-07 bullet 4 + D-12 fall-through).
    """
    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    user_id = await _create_user(test_session_maker)

    try:
        await _seed_anchor_games(
            test_session_maker,
            user_id=user_id,
            n_games=_ANCHOR_FLOOR_GAMES,
            platform="chess.com",
            time_control_bucket="blitz",
            user_rating=_USER_RATING_CHESSCOM_BLITZ,
        )

        async with test_session_maker() as session:
            anchors = await compute_anchors_for_user(session, user_id)
            await session.commit()

        assert "blitz" in anchors
        anchor = anchors["blitz"]
        assert anchor.source_platform == "chesscom"
        assert anchor.chesscom_raw_rating is not None, (
            "chess.com anchor MUST capture the raw rating per D-07 bullet 4"
        )
        # Round-trip: chesscom_raw_rating reads back as the median of the
        # seeded chess.com ratings (all rows share user_rating, so the
        # median equals user_rating).
        assert anchor.chesscom_raw_rating == _USER_RATING_CHESSCOM_BLITZ

        # anchor_rating is the Lichess-equivalent — distinct from the raw
        # chess.com median (D-12 conversion path).
        expected_lichess_equiv = convert_chesscom_to_lichess(
            _USER_RATING_CHESSCOM_BLITZ, source_tc="blitz", target_tc="blitz"
        )
        assert expected_lichess_equiv is not None
        assert anchor.anchor_rating == expected_lichess_equiv
        assert anchor.anchor_rating != anchor.chesscom_raw_rating, (
            "Lichess-equivalent must differ from raw chess.com median for this fixture"
        )

        # T10 round-trip via fetch_anchors_for_user.
        async with test_session_maker() as session:
            persisted = await fetch_anchors_for_user(session, user_id=user_id)
        assert persisted["blitz"].source_platform == "chesscom"
        assert persisted["blitz"].chesscom_raw_rating == _USER_RATING_CHESSCOM_BLITZ
    finally:
        await _delete_user(test_session_maker, user_id)


async def test_compute_anchors_mixed_user_lichess_precedence_d12(test_engine) -> None:  # noqa: ANN001
    """T3: Mixed-platform user (rapid) — Lichess precedence wins.

    Even with BOTH Lichess and chess.com games in rapid, the anchor must
    carry ``source_platform='lichess'`` and ``chesscom_raw_rating=None``
    (D-12 — Lichess wins, the chess.com pool is not consulted).
    """
    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    user_id = await _create_user(test_session_maker)

    try:
        # Both platforms have enough games to clear the anchor floor.
        await _seed_anchor_games(
            test_session_maker,
            user_id=user_id,
            n_games=_ANCHOR_FLOOR_GAMES,
            platform="lichess",
            time_control_bucket="rapid",
            user_rating=_USER_RATING_LICHESS_RAPID,
        )
        await _seed_anchor_games(
            test_session_maker,
            user_id=user_id,
            n_games=_ANCHOR_FLOOR_GAMES,
            platform="chess.com",
            time_control_bucket="rapid",
            user_rating=_USER_RATING_CHESSCOM_BLITZ + 100,
        )

        async with test_session_maker() as session:
            anchors = await compute_anchors_for_user(session, user_id)
            await session.commit()

        assert "rapid" in anchors
        anchor = anchors["rapid"]
        assert anchor.source_platform == "lichess", (
            "D-12 precedence: any Lichess games in TC must win"
        )
        assert anchor.chesscom_raw_rating is None
    finally:
        await _delete_user(test_session_maker, user_id)


async def test_compute_anchors_chesscom_daily_classical_suppressed(test_engine) -> None:  # noqa: ANN001
    """T4: chess.com Daily-only user → NO classical anchor.

    The median-anchor SQL drops chess.com Daily games (RESEARCH Pitfall 11),
    AND ``convert_chesscom_to_lichess(..., source_tc='daily')`` returns None.
    Either branch alone suppresses the anchor; both branches together make
    suppression mandatory. The chip suppresses naturally for this user.
    """
    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    user_id = await _create_user(test_session_maker)

    try:
        await _seed_anchor_games(
            test_session_maker,
            user_id=user_id,
            n_games=_ANCHOR_FLOOR_GAMES,
            platform="chess.com",
            time_control_bucket="classical",
            user_rating=1700,
            is_chesscom_daily=True,
        )

        async with test_session_maker() as session:
            anchors = await compute_anchors_for_user(session, user_id)
            await session.commit()

        assert "classical" not in anchors, (
            "chess.com Daily-only user must have NO classical anchor "
            "(per_user_cte_median_anchor drops 1/% time_control_str rows)"
        )
        # No other TC has games either.
        assert anchors == {}

        # Persistence: nothing written.
        async with test_session_maker() as session:
            persisted = await fetch_anchors_for_user(session, user_id=user_id)
        assert persisted == {}
    finally:
        await _delete_user(test_session_maker, user_id)
