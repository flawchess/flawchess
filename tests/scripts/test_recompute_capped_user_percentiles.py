"""Tests for scripts/recompute_capped_user_percentiles.py (ranked-sample cap 3000 -> 1000).

DB tests run inside the rolled-back db_session, so nothing is committed. The two
``recompute_user`` tests need no DB: the stages and prunes are replaced by fakes.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

import pytest
import sentry_sdk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.models.user_benchmark_percentile import UserBenchmarkPercentile
from app.models.user_rating_anchors import UserRatingAnchor
from scripts import recompute_capped_user_percentiles as script
from scripts.recompute_capped_user_percentiles import (
    capture_failures,
    prune_stale_stage_a,
    prune_stale_stage_b,
    recompute_user,
    select_affected_users,
)
from tests.conftest import ensure_test_user

pytestmark = pytest.mark.asyncio

_USER_FULL = 99671  # reserved for this module: games above the cap
_USER_FILTERED = 99672  # at the cap once ineligible games are excluded
_USER_ANCHOR_ONLY = 99673  # no games, only a persisted over-cap anchor
_CAP = 3
_NOW = datetime.datetime.now(datetime.timezone.utc)
_SINCE = datetime.datetime(2026, 10, 31, 12, 0, tzinfo=datetime.timezone.utc)
_STALE = _SINCE - datetime.timedelta(days=1)
_FRESH = _SINCE + datetime.timedelta(minutes=1)
_SNAPSHOT = datetime.date(2026, 10, 1)
_OUTSIDE_WINDOW_DAYS = 1200  # well past the 36-month recency window


def _game(
    user_id: int,
    *,
    rated: bool = True,
    opp_rating: int = 1500,
    age_days: int = 5,
) -> Game:
    return Game(
        user_id=user_id,
        platform="lichess",
        platform_game_id=f"cap-{uuid.uuid4().hex[:12]}",
        pgn="*",
        result="1-0",
        user_color="white",
        rated=rated,
        is_computer_game=False,
        white_rating=1500,
        black_rating=opp_rating,
        time_control_bucket="blitz",
        played_at=_NOW - datetime.timedelta(days=age_days),
    )


def _pct(user_id: int, metric: str, computed_at: datetime.datetime, color: str = "all") -> Any:
    return UserBenchmarkPercentile(
        user_id=user_id,
        metric=metric,
        time_control_bucket="blitz",
        color=color,
        value=0.1,
        percentile=50.0,
        n_games=100,
        cdf_snapshot=_SNAPSHOT,
        computed_at=computed_at,
    )


def _anchor(user_id: int, computed_at: datetime.datetime, n_lichess: int = 100) -> UserRatingAnchor:
    return UserRatingAnchor(
        user_id=user_id,
        time_control_bucket="blitz",
        anchor_rating=1500,
        n_chesscom_games=0,
        n_lichess_games=n_lichess,
        lichess_median_native=1500,
        computed_at=computed_at,
    )


async def test_select_affected_users_mirrors_canonical_slice(db_session: AsyncSession) -> None:
    for uid in (_USER_FULL, _USER_FILTERED, _USER_ANCHOR_ONLY):
        await ensure_test_user(db_session, uid)
    db_session.add_all([_game(_USER_FULL) for _ in range(_CAP + 1)])
    # Exactly at the cap among eligible games; the three extras are all excluded by
    # the canonical slice (unrated, opponent 200 Elo away, outside the 36-month window).
    db_session.add_all([_game(_USER_FILTERED) for _ in range(_CAP)])
    db_session.add(_game(_USER_FILTERED, rated=False))
    db_session.add(_game(_USER_FILTERED, opp_rating=1700))
    db_session.add(_game(_USER_FILTERED, age_days=_OUTSIDE_WINDOW_DAYS))
    db_session.add(_anchor(_USER_ANCHOR_ONLY, _STALE, n_lichess=_CAP + 2))
    await db_session.flush()

    affected = await select_affected_users(db_session, cap=_CAP)

    assert _USER_FULL in affected
    assert _USER_FILTERED not in affected
    assert _USER_ANCHOR_ONLY in affected


async def test_prune_stale_stage_a_scope(db_session: AsyncSession) -> None:
    other = _USER_FILTERED
    for uid in (_USER_FULL, other):
        await ensure_test_user(db_session, uid)
    db_session.add_all(
        [
            _anchor(_USER_FULL, _STALE),
            _pct(_USER_FULL, "score_gap", _STALE),
            _pct(_USER_FULL, "clock_gap", _STALE),  # Stage B row, stale: must survive
            _anchor(other, _STALE),  # other user's stale rows: must survive
            _pct(other, "score_gap", _STALE),
        ]
    )
    await db_session.flush()

    deleted = await prune_stale_stage_a(db_session, user_id=_USER_FULL, since=_SINCE)

    assert deleted == 2
    anchors = (await db_session.execute(select(UserRatingAnchor.user_id))).scalars().all()
    assert _USER_FULL not in anchors
    assert other in anchors
    metrics = {
        (r.user_id, r.metric)
        for r in (await db_session.execute(select(UserBenchmarkPercentile))).scalars()
    }
    assert (_USER_FULL, "score_gap") not in metrics
    assert (_USER_FULL, "clock_gap") in metrics
    assert (other, "score_gap") in metrics


async def test_prune_stale_stage_a_keeps_fresh_rows(db_session: AsyncSession) -> None:
    await ensure_test_user(db_session, _USER_FULL)
    db_session.add_all([_anchor(_USER_FULL, _FRESH), _pct(_USER_FULL, "score_gap", _FRESH)])
    await db_session.flush()

    deleted = await prune_stale_stage_a(db_session, user_id=_USER_FULL, since=_SINCE)

    assert deleted == 0


async def test_prune_stale_stage_b_scope(db_session: AsyncSession) -> None:
    other = _USER_FILTERED
    for uid in (_USER_FULL, other):
        await ensure_test_user(db_session, uid)
    db_session.add_all(
        [
            _pct(_USER_FULL, "score_gap", _STALE),  # Stage A row: must survive
            _pct(_USER_FULL, "clock_gap", _STALE),
            _pct(_USER_FULL, "opening_worse_rate", _STALE, color="white"),
            _pct(_USER_FULL, "opening_worse_rate", _STALE, color="black"),
            _pct(_USER_FULL, "net_flag_rate", _FRESH),  # fresh: must survive
            _pct(other, "clock_gap", _STALE),  # other user: must survive
        ]
    )
    await db_session.flush()

    deleted = await prune_stale_stage_b(db_session, user_id=_USER_FULL, since=_SINCE)

    assert deleted == 3
    remaining = {
        (r.user_id, r.metric, r.color)
        for r in (await db_session.execute(select(UserBenchmarkPercentile))).scalars()
    }
    assert (_USER_FULL, "score_gap", "all") in remaining
    assert (_USER_FULL, "net_flag_rate", "all") in remaining
    assert (other, "clock_gap", "all") in remaining
    assert (_USER_FULL, "clock_gap", "all") not in remaining


def _install_fakes(
    monkeypatch: pytest.MonkeyPatch, calls: list[str], *, stage_a_fails: bool
) -> None:
    async def fake_a(user_id: int, *, session_maker: Any) -> None:
        calls.append("A")
        if stage_a_fails:
            sentry_sdk.capture_exception(RuntimeError("stage A boom"))

    async def fake_b(user_id: int, *, session_maker: Any) -> None:
        calls.append("B")

    async def fake_prune_a(session: Any, *, user_id: int, since: datetime.datetime) -> int:
        calls.append("pruneA")
        return 2

    async def fake_prune_b(session: Any, *, user_id: int, since: datetime.datetime) -> int:
        calls.append("pruneB")
        return 3

    async def fake_since(maker: Any) -> datetime.datetime:
        return _SINCE

    monkeypatch.setattr(script, "compute_stage_a", fake_a)
    monkeypatch.setattr(script, "compute_stage_b", fake_b)
    monkeypatch.setattr(script, "prune_stale_stage_a", fake_prune_a)
    monkeypatch.setattr(script, "prune_stale_stage_b", fake_prune_b)
    monkeypatch.setattr(script, "_read_db_now", fake_since)


class _FakeSession:
    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def commit(self) -> None:
        return None


def _dummy_maker() -> _FakeSession:
    return _FakeSession()


async def test_recompute_user_skips_prune_and_stage_b_after_stage_a_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    _install_fakes(monkeypatch, calls, stage_a_fails=True)

    with capture_failures() as failures:
        outcome = await recompute_user(_dummy_maker, 1, failures)  # ty: ignore[invalid-argument-type]  # fake maker

    assert calls == ["A"]
    assert outcome.stage_a_ok is False
    assert outcome.pruned_a == 0
    assert len(failures) == 1


async def test_recompute_user_happy_path_order(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    _install_fakes(monkeypatch, calls, stage_a_fails=False)

    with capture_failures() as failures:
        outcome = await recompute_user(_dummy_maker, 1, failures)  # ty: ignore[invalid-argument-type]  # fake maker

    assert calls == ["A", "pruneA", "B", "pruneB"]
    assert outcome.stage_a_ok and outcome.stage_b_ok
    assert (outcome.pruned_a, outcome.pruned_b) == (2, 3)
    assert failures == []
