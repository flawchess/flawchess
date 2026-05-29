"""Unit + real-DB tests for user_benchmark_percentiles_service.

Phase 94.4 Plan 05b rewrites the service to consume the cohort CDF artifact
(``COHORT_PERCENTILE_CDF`` via ``interpolate_cohort_percentile``) and the
per-(user, TC) median rating anchor (``user_rating_anchors``). The post-94.3
``STAGE_B_METRICS`` 12-tuple retires; Stage B now iterates the 7-tuple
``STAGE_B_METRIC_FAMILIES`` × the user's above-floor TCs.

Phase 94.4 Plan 10 (D-12 Reversal Amendment) replaces T1-T4/T10 (Lichess-
precedence schema) with B1-B7 (blended-anchor schema).

Mock test coverage (T5-T9 — unchanged from Plan 05b):

  T5.  Stage A computes score_gap percentile ONLY for TCs where an anchor exists.
  T6.  Stage B fans out across STAGE_B_METRIC_FAMILIES (7-tuple) × anchored TCs.
  T7.  ``upsert_percentile`` is called with the 3-column PK tuple.
  T8.  Suppressed cohort-CDF cell still upserts with ``percentile=None``.
  T9.  Sentry ``capture_exception`` fires on a metric-compute failure.

Real-DB test coverage (B1-B7 — blended anchor, Plan 10):

  B1.  Mixed-platform user: blended anchor between per-platform medians;
       n_chesscom_games, n_lichess_games, both native medians populated.
  B2.  Pure-lichess user: anchor_rating == lichess_median_native; n_chesscom == 0;
       chesscom_median_native is None.
  B3.  Pure-chess.com user: chesscom_median_native populated; lichess_median_native
       None; anchor_rating == CHESSCOM_BLITZ_TO_LICHESS lookup result.
  B4.  chess.com Daily-only classical: no anchor row (blended SQL drops 1/% rows).
  B5.  Below MEDIAN_ANCHOR_MIN_GAMES on pooled count: no anchor row.
  B6.  Legacy assertion retirement: _user_has_lichess_games_in_tc and
       _compute_median_anchor_for_platform are gone from the service module.
  B7.  Sentry capture on anchor-stage SQL failure; set_context carries stage='anchor'.
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
        "score_gap_conv",
        "score_gap_parity",
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
    n_chesscom_games: int = 0,
    n_lichess_games: int = _ANCHOR_FLOOR_GAMES,
    chesscom_median_native: int | None = None,
    lichess_median_native: int | None = 1700,
) -> Any:
    """Construct a RatingAnchorRow with sensible defaults (blended schema, Plan 09/10)."""
    from app.repositories.user_rating_anchors_repository import RatingAnchorRow

    return RatingAnchorRow(
        anchor_rating=anchor_rating,
        n_chesscom_games=n_chesscom_games,
        n_lichess_games=n_lichess_games,
        chesscom_median_native=chesscom_median_native,
        lichess_median_native=lichess_median_native,
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


# ─────────────────────────────────────────────────────────────────────────────
# Real-DB tests for compute_anchors_for_user (B1-B7).
# D-12 Reversal Amendment — blended anchor (Plan 10).
#
# Replaces T1-T4/T10 (Lichess-precedence schema) which are retired.
# B6 (regression check) verifies that old schema fields no longer exist.
# ─────────────────────────────────────────────────────────────────────────────

# Rating constants for blended-anchor tests.
_CC_RATING_MIXED: int = 2200  # chess.com games seeded at this rating
_LI_RATING_MIXED: int = 1900  # lichess games seeded at this rating
_N_MIXED_GAMES: int = 50  # per platform; well above 30-floor
_N_PURE_GAMES: int = 100
_N_PURE_CHESSCOM: int = 100
# Native chess.com BULLET rating for the pure-chess.com bullet anchor test.
# Post quick-260529-js1 the conversion is keyed on native chess.com ratings for
# the bucket's source TC, so this is treated as a native bullet rating (inverted
# via Table 1's bullet column, then chained to lichess-equivalent).
_USER_RATING_BULLET: int = 1800
_BELOW_FLOOR_GAMES: int = 5  # pooled 5+5=10 < 30


async def test_b1_mixed_platform_user_blended_anchor(test_engine) -> None:  # noqa: ANN001
    """B1: Mixed-platform user → blended anchor between per-platform medians.

    D-12 Reversal Amendment: 50 chess.com blitz @ 2200 + 50 lichess blitz @
    1900. The blended anchor must be between 1900 and the converted chess.com
    2200, n_chesscom_games=50, n_lichess_games=50, chesscom_median_native=2200,
    lichess_median_native=1900.
    """
    from app.services.chesscom_to_lichess import CHESSCOM_BLITZ_TO_LICHESS

    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    user_id = await _create_user(test_session_maker)

    try:
        # Seed 50 chess.com blitz games at 2200.
        await _seed_anchor_games(
            test_session_maker,
            user_id=user_id,
            n_games=_N_MIXED_GAMES,
            platform="chess.com",
            time_control_bucket="blitz",
            user_rating=_CC_RATING_MIXED,
        )
        # Seed 50 lichess blitz games at 1900.
        await _seed_anchor_games(
            test_session_maker,
            user_id=user_id,
            n_games=_N_MIXED_GAMES,
            platform="lichess",
            time_control_bucket="blitz",
            user_rating=_LI_RATING_MIXED,
        )

        async with test_session_maker() as session:
            anchors = await compute_anchors_for_user(session, user_id)
            await session.commit()

        assert "blitz" in anchors, "Mixed user must have a blitz anchor"
        anchor = anchors["blitz"]

        # Per-platform game counts.
        assert anchor.n_chesscom_games == _N_MIXED_GAMES
        assert anchor.n_lichess_games == _N_MIXED_GAMES

        # Native medians (pre-conversion).
        assert anchor.chesscom_median_native == _CC_RATING_MIXED
        assert anchor.lichess_median_native == _LI_RATING_MIXED

        # Blended anchor must be between lichess native and the converted
        # chess.com 2200 (blitz column of CHESSCOM_BLITZ_TO_LICHESS[2200]).
        expected_cc_equiv = CHESSCOM_BLITZ_TO_LICHESS[2200]["blitz"]
        assert expected_cc_equiv is not None
        assert _LI_RATING_MIXED <= anchor.anchor_rating <= expected_cc_equiv, (
            f"Blended anchor {anchor.anchor_rating} must be between "
            f"{_LI_RATING_MIXED} (lichess) and {expected_cc_equiv} (converted chess.com)"
        )
    finally:
        await _delete_user(test_session_maker, user_id)


async def test_b2_pure_lichess_user_anchor(test_engine) -> None:  # noqa: ANN001
    """B2: Pure-lichess user → anchor_rating == lichess_median_native, n_chesscom == 0."""
    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    user_id = await _create_user(test_session_maker)

    try:
        await _seed_anchor_games(
            test_session_maker,
            user_id=user_id,
            n_games=_N_PURE_GAMES,
            platform="lichess",
            time_control_bucket="rapid",
            user_rating=_USER_RATING_LICHESS_RAPID,
        )

        async with test_session_maker() as session:
            anchors = await compute_anchors_for_user(session, user_id)
            await session.commit()

        assert "rapid" in anchors, "Lichess-only user must have a rapid anchor"
        anchor = anchors["rapid"]

        assert anchor.n_chesscom_games == 0
        assert anchor.n_lichess_games == _N_PURE_GAMES
        assert anchor.chesscom_median_native is None, (
            "n_chesscom_games=0 → chesscom_median_native must be NULL"
        )
        assert anchor.lichess_median_native == _USER_RATING_LICHESS_RAPID
        # Pure-lichess: anchor_rating = lichess median (no conversion involved).
        assert anchor.anchor_rating == _USER_RATING_LICHESS_RAPID

        # No chess.com games → other TCs absent.
        assert "bullet" not in anchors
        assert "blitz" not in anchors
        assert "classical" not in anchors
    finally:
        await _delete_user(test_session_maker, user_id)


async def test_b3_pure_chesscom_user_anchor(test_engine) -> None:  # noqa: ANN001
    """B3: Pure-chess.com user → chesscom_median_native populated, lichess_median_native None.

    anchor_rating is the lichess-equivalent of the chess.com median via the
    nearest-anchor lookup. Post quick-260529-js1 the lookup is keyed on NATIVE
    chess.com ratings for the bucket's source TC (bullet here), so the expected
    value is the nearest-anchor pick on the composed bullet grid (which the SQL
    LATERAL join mirrors via ORDER BY ABS(anchor - rating) LIMIT 1) — NOT the old
    blitz-keyed CHESSCOM_BLITZ_TO_LICHESS[1800]['bullet'].
    """
    from app.services.chesscom_to_lichess import composed_chesscom_to_lichess_grid

    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    user_id = await _create_user(test_session_maker)

    try:
        await _seed_anchor_games(
            test_session_maker,
            user_id=user_id,
            n_games=_N_PURE_CHESSCOM,
            platform="chess.com",
            time_control_bucket="bullet",
            user_rating=_USER_RATING_BULLET,
        )

        async with test_session_maker() as session:
            anchors = await compute_anchors_for_user(session, user_id)
            await session.commit()

        assert "bullet" in anchors, "chess.com-only user must have a bullet anchor"
        anchor = anchors["bullet"]

        assert anchor.n_chesscom_games == _N_PURE_CHESSCOM
        assert anchor.n_lichess_games == 0
        assert anchor.chesscom_median_native == _USER_RATING_BULLET
        assert anchor.lichess_median_native is None, (
            "n_lichess_games=0 → lichess_median_native must be NULL"
        )

        # anchor_rating is the lichess-equivalent of the native chess.com bullet
        # median (1800), selected via the SQL nearest-anchor rule on the composed
        # bullet grid. Read the expected value dynamically (self-updating if the
        # snapshot or grid step changes).
        bullet_grid = composed_chesscom_to_lichess_grid("bullet", "bullet")
        assert bullet_grid, "composed bullet grid must be non-empty"
        nearest_anchor, expected_bullet_equiv = min(
            bullet_grid, key=lambda row: abs(row[0] - _USER_RATING_BULLET)
        )
        assert anchor.anchor_rating == expected_bullet_equiv, (
            f"anchor_rating {anchor.anchor_rating} must equal the native-keyed "
            f"nearest-anchor lichess-equiv ({nearest_anchor} -> {expected_bullet_equiv}) "
            f"for native chess.com bullet {_USER_RATING_BULLET}"
        )
    finally:
        await _delete_user(test_session_maker, user_id)


async def test_b4_chesscom_daily_classical_suppressed(test_engine) -> None:  # noqa: ANN001
    """B4: chess.com Daily-only user in classical → NO anchor row for classical.

    The blended-mode SQL drops chess.com Daily games (time_control_str LIKE '1/%').
    With zero qualifying games, the pooled count is 0 < MEDIAN_ANCHOR_MIN_GAMES
    and no anchor row is produced for classical.
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
            "(blended SQL drops 1/% time_control_str rows; pooled count = 0)"
        )
        assert anchors == {}

        async with test_session_maker() as session:
            persisted = await fetch_anchors_for_user(session, user_id=user_id)
        assert persisted == {}
    finally:
        await _delete_user(test_session_maker, user_id)


async def test_b5_below_floor_suppressed(test_engine) -> None:  # noqa: ANN001
    """B5: Pooled count below MEDIAN_ANCHOR_MIN_GAMES → no anchor row.

    5 chess.com blitz + 5 lichess blitz = pooled 10 < 30 = floor.
    """
    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    user_id = await _create_user(test_session_maker)

    try:
        await _seed_anchor_games(
            test_session_maker,
            user_id=user_id,
            n_games=_BELOW_FLOOR_GAMES,
            platform="chess.com",
            time_control_bucket="blitz",
            user_rating=_USER_RATING_CHESSCOM_BLITZ,
        )
        await _seed_anchor_games(
            test_session_maker,
            user_id=user_id,
            n_games=_BELOW_FLOOR_GAMES,
            platform="lichess",
            time_control_bucket="blitz",
            user_rating=1700,
        )

        async with test_session_maker() as session:
            anchors = await compute_anchors_for_user(session, user_id)
            await session.commit()

        assert "blitz" not in anchors, (
            f"Pooled count {_BELOW_FLOOR_GAMES * 2} < MEDIAN_ANCHOR_MIN_GAMES "
            "must suppress the blitz anchor"
        )
    finally:
        await _delete_user(test_session_maker, user_id)


def test_b6_legacy_assertion_retirement() -> None:
    """B6: No test references old schema fields (source_platform, chesscom_raw_rating,
    _user_has_lichess_games_in_tc, _compute_median_anchor_for_platform).

    These symbols are deleted in Plan 10. Verified at import time.
    """
    assert not hasattr(svc, "_user_has_lichess_games_in_tc"), (
        "_user_has_lichess_games_in_tc must not exist on the service module"
    )
    assert not hasattr(svc, "_compute_median_anchor_for_platform"), (
        "_compute_median_anchor_for_platform must not exist on the service module"
    )


async def test_b7_sentry_capture_on_anchor_stage_failure(
    monkeypatch: pytest.MonkeyPatch,
    test_engine,  # noqa: ANN001
) -> None:
    """B7: When per-TC SQL raises, Sentry captures with set_context payload.

    Verifies: set_context carries stage='anchor', tc set; no user_id in message.
    """

    captured_contexts: list[dict] = []
    captured_exceptions: list[Exception] = []

    def fake_set_context(key: str, value: dict) -> None:
        captured_contexts.append({"key": key, "value": value})

    def fake_capture_exception(exc: Exception) -> None:
        captured_exceptions.append(exc)

    def broken_text(sql: str) -> Any:
        raise RuntimeError("simulated SQL failure in anchor compute")

    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    user_id = await _create_user(test_session_maker)

    try:
        # Patch text() in the service so every TC's SQL call fails.
        monkeypatch.setattr(svc, "text", broken_text)

        with (
            patch("sentry_sdk.set_context", side_effect=fake_set_context),
            patch("sentry_sdk.capture_exception", side_effect=fake_capture_exception),
        ):
            async with test_session_maker() as session:
                anchors = await compute_anchors_for_user(session, user_id)

        # Should return empty dict (per-TC errors swallowed, not propagated).
        assert anchors == {}

        # Sentry must have fired at least once (one per-TC failure).
        assert len(captured_exceptions) >= 1

        # set_context must carry stage='anchor' and tc.
        assert any(
            ctx["key"] == _SENTRY_CONTEXT_KEY
            and ctx["value"].get("stage") == "anchor"
            and "tc" in ctx["value"]
            for ctx in captured_contexts
        ), "set_context must carry stage='anchor' and tc"

        # V4: user_id must NOT be embedded in any exception message.
        for exc in captured_exceptions:
            assert str(user_id) not in str(exc)
    finally:
        await _delete_user(test_session_maker, user_id)
