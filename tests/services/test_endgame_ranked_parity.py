"""DB-backed parity gate for the on-read ranked Endgame Stats.

The on-read values served by ``get_ranked_stats`` must equal what the persisted
Stage A/B CTEs compute for the same user, family and time control
(``_compute_metric_for_user_per_tc``, the oracle). The older Python aggregators
differ from the CTEs in five definitions (NULL-eval routing, sub-800 floor, 2x
clock clamp, per-span vs per-game gaps, net-flag denominator), so numeric parity
on a seeded user with every edge case is the gate, not code review.

Seed (all blitz, lichess, inside the canonical slice unless noted):
  * a block of endgame games (6-ply rook span) and a block of non-endgame games
  * rows that must NOT count: one game 37 months old, one opponent +150 Elo, one
    unrated, one computer game (each is an endgame game with a distinctive result,
    so a leak would move the numbers)

Every non-guest Game insert is cleaned up in a ``finally`` (the global eval
lottery flakes when a test leaks a non-guest needs-engine game).
"""

from __future__ import annotations

import datetime
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field

import httpx
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.game import Game
from app.models.game_position import GamePosition
from app.models.user import User
from app.repositories.endgame_ranked_repository import fetch_ranked_games
from app.repositories.user_benchmark_percentiles_repository import upsert_percentile
from app.schemas.endgames import EndgameRankedStatsResponse, RankedBucketOut, RankedTcStats
from app.services.canonical_slice_sql import TimeControlBucket
from app.services.endgame_ranked_service import get_ranked_stats
from app.services.global_percentile_cdf import CdfMetricId
from app.services.user_benchmark_percentiles_service import (
    STAGE_B_METRIC_FAMILIES,
    _compute_metric_for_user_per_tc,
)
from tests.seed_fixtures import _register_and_login

# ── Constants (CLAUDE.md no-magic-numbers) ───────────────────────────────────

_TC: TimeControlBucket = "blitz"
_USER_ELO: int = 1500
_OPP_ELO_IN_BAND: int = 1550  # within +-100
_OPP_ELO_OUT_OF_BAND: int = 1650  # +150 -> excluded by the equal-footing filter
_BASE_TIME_SECONDS: int = 180
_RECENT_DAYS_AGO: int = 30
_STALE_DAYS_AGO: int = 37 * 31  # > 36 months -> outside the recency window
_ROOK_CLASS: int = 1
_PAWN_CLASS: int = 3
_SPAN_START_PLY: int = 30
_SPAN_LEN: int = 6  # ENDGAME_PLY_THRESHOLD
_SPAN_STRIDE: int = 10  # plies between the starts of consecutive spans in one game
_LOW_CLOCK: float = 40.0  # 0.22 of the 180s base: under the 0.40 pressure threshold
_HIGH_CLOCK: float = 150.0  # 0.83 of base
_OVER_2X_CLOCK: float = 400.0  # 2.2x base
_CLOCK_TICK: float = 2.0
_OVER_2X_EVERY: int = 17
_OVER_2X_OFFSET: int = 5
_NULL_FIRST_CLOCK_EVERY: int = 13
_TIMEOUT_EVERY: int = 9
_DEFAULT_ENDGAME_GAMES: int = 40
_NON_ENDGAME_GAMES: int = 40
_PLANTED_PERCENTILE_A: float = 73.0
_PLANTED_PERCENTILE_B: float = 11.0
_ABS_TOL: float = 1e-9
_FLOOR: int = 30
_SMALL_ENDGAME_GAMES: int = 20  # below every 30-game floor
_SMALL_NON_ENDGAME_GAMES: int = 35
_ALL_FAMILIES: tuple[CdfMetricId, ...] = ("score_gap", *STAGE_B_METRIC_FAMILIES)

pytestmark = pytest.mark.asyncio


# ── Seed data model ──────────────────────────────────────────────────────────


@dataclass
class _PosSpec:
    """One game_positions row of a seeded game."""

    ply: int
    endgame_class: int | None = None
    eval_cp: int | None = None
    eval_mate: int | None = None
    clock_seconds: float | None = None


@dataclass
class _GameSpec:
    """One seeded game. ``outcome`` is user-perspective."""

    outcome: str  # "win" | "draw" | "loss"
    user_color: str = "white"
    positions: list[_PosSpec] = field(default_factory=list)
    user_rating: int = _USER_ELO
    opp_rating: int = _OPP_ELO_IN_BAND
    days_ago: int = _RECENT_DAYS_AGO
    rated: bool = True
    is_computer_game: bool = False
    base_time_seconds: int | None = _BASE_TIME_SECONDS
    termination: str | None = None
    in_slice: bool = True


def _result_str(outcome: str, user_color: str) -> str:
    """PGN result string for a user-perspective outcome."""
    if outcome == "draw":
        return "1/2-1/2"
    user_white = user_color == "white"
    user_won = outcome == "win"
    return "1-0" if user_white == user_won else "0-1"


def _span(
    start_ply: int,
    endgame_class: int,
    *,
    n_plies: int = _SPAN_LEN,
    entry_cp: int | None = None,
    entry_mate: int | None = None,
    user_color: str = "white",
    user_clock: float | None = None,
    opp_clock: float | None = None,
    null_first_user_clock: bool = False,
) -> list[_PosSpec]:
    """An endgame span of ``n_plies`` consecutive plies.

    ``entry_cp`` / ``entry_mate`` are USER-perspective; they are stored
    white-perspective (the column convention). Clocks: the side that moves at an even
    ply is white; each side's clock drops one tick per own move. With
    ``null_first_user_clock`` the user's first clock reading is NULL, so the entry
    clock must come from the user's NEXT same-parity ply ("first non-null" rule).
    """
    sign = 1 if user_color == "white" else -1
    span = [_PosSpec(ply=start_ply + i, endgame_class=endgame_class) for i in range(n_plies)]
    span[0].eval_cp = None if entry_cp is None else entry_cp * sign
    span[0].eval_mate = None if entry_mate is None else entry_mate * sign
    if user_clock is not None and opp_clock is not None:
        white0, black0 = (user_clock, opp_clock) if sign == 1 else (opp_clock, user_clock)
        for i, pos in enumerate(span):
            side0 = white0 if pos.ply % 2 == 0 else black0
            pos.clock_seconds = side0 - _CLOCK_TICK * (i // 2)
        if null_first_user_clock:
            user_parity = 0 if sign == 1 else 1
            span[(user_parity - start_ply) % 2].clock_seconds = None
    return span


def _outcome_cycle(idx: int, dominant: str) -> str:
    """Varied outcomes: 3/5 dominant, 1/5 draw, 1/5 the opposite of dominant."""
    mod = idx % 5
    if mod < 3:
        return dominant
    if mod == 3:
        return "draw"
    return "loss" if dominant == "win" else "win"


def _clock_pair(k: int) -> tuple[float, float]:
    """(user, opponent) endgame-entry clocks cycling through the four pressure patterns.

    Pattern 0: user pressured only; 1: opponent pressured only; 2: both pressured;
    3: neither. Every 17th game the user's clock sits above 2x the base clock while the
    opponent is pressured (the old Python path clamped these games away; the CTEs do not).
    """
    pair = (
        (_LOW_CLOCK, _HIGH_CLOCK),
        (_HIGH_CLOCK, _LOW_CLOCK),
        (_LOW_CLOCK, _LOW_CLOCK + 10.0),
        (_HIGH_CLOCK, _HIGH_CLOCK + 10.0),
    )[k % 4]
    if k % _OVER_2X_EVERY == _OVER_2X_OFFSET:
        return _OVER_2X_CLOCK, _LOW_CLOCK
    return pair


# One entry per span: (endgame_class, entry_cp, entry_mate, n_plies), user-perspective evals.
_SpanRecipe = tuple[int, int | None, int | None, int]


def _endgame_game(
    k: int,
    *,
    dominant: str,
    spans: list[_SpanRecipe],
    user_rating: int = _USER_ELO,
    opp_rating: int = _OPP_ELO_IN_BAND,
    base_time_seconds: int | None = _BASE_TIME_SECONDS,
) -> _GameSpec:
    """One endgame game: spans from ``spans``, clocks from pattern ``k``, outcome from the cycle."""
    user_color = "white" if k % 2 == 0 else "black"
    user_clock, opp_clock = _clock_pair(k)
    positions = [_PosSpec(ply=0)]
    for span_idx, (endgame_class, entry_cp, entry_mate, n_plies) in enumerate(spans):
        positions += _span(
            _SPAN_START_PLY + span_idx * _SPAN_STRIDE,
            endgame_class,
            n_plies=n_plies,
            entry_cp=entry_cp,
            entry_mate=entry_mate,
            user_color=user_color,
            user_clock=user_clock,
            opp_clock=opp_clock,
            null_first_user_clock=span_idx == 0 and k % _NULL_FIRST_CLOCK_EVERY == 3,
        )
    return _GameSpec(
        outcome=_outcome_cycle(k, dominant),
        user_color=user_color,
        positions=positions,
        # NB: k % 9 == 0 timeouts -> net_flag_rate has a non-zero numerator
        termination="timeout" if k % _TIMEOUT_EVERY == 0 else "checkmate",
        user_rating=user_rating,
        opp_rating=opp_rating,
        base_time_seconds=base_time_seconds,
    )


def _one_span(cp: int | None, mate: int | None = None) -> list[_SpanRecipe]:
    return [(_ROOK_CLASS, cp, mate, _SPAN_LEN)]


def _endgame_blocks(plain_games: int, dominant: str) -> list[_GameSpec]:
    """All endgame games of the ranked sample, in one pass so clock pattern ``k`` is global.

    Blocks (counts clear every 30-game family floor):
      conv cp x30, conv mate x3, conv cp>=2000 x3 (achievable d_i NULL, no 2000 clip in
      the gaps), parity x36, recovery cp x33, recovery mate x3, NULL entry eval x6
      (excluded from rates / bucket gaps), sub-800 user x6 (excluded from rates / bucket
      gaps but NOT from achievable), NULL base_time x6 (excluded from clock_gap /
      time_pressure but counted by net_flag_rate), 4+4-ply split-class games x4 (a game
      but no span), multi-class rook->pawn games x10 (LEAD next-span eval), rook->pawn
      with a NULL next eval x4 (terminal fallback to the game score), plus the
      ``plain_games`` knob block (parity-ish evals).
    """
    specs: list[_GameSpec] = []

    def add(
        n: int,
        recipe: Callable[[int], list[_SpanRecipe]],
        *,
        user_rating: int = _USER_ELO,
        opp_rating: int = _OPP_ELO_IN_BAND,
        base_time_seconds: int | None = _BASE_TIME_SECONDS,
    ) -> None:
        for i in range(n):
            specs.append(
                _endgame_game(
                    len(specs),
                    dominant=dominant,
                    spans=recipe(i),
                    user_rating=user_rating,
                    opp_rating=opp_rating,
                    base_time_seconds=base_time_seconds,
                )
            )

    conv_cps = (150, 250, 400)
    parity_cps = (-30, 0, 40, 90, -90)
    recov_cps = (-150, -250, -400)
    add(30, lambda i: _one_span(conv_cps[i % 3]))  # conversion by cp
    add(3, lambda i: _one_span(None, 3))  # conversion by forced mate for the user
    add(3, lambda i: _one_span(2500))  # |cp| >= 2000: achievable d_i NULL
    add(36, lambda i: _one_span(parity_cps[i % 5]))  # parity
    add(33, lambda i: _one_span(recov_cps[i % 3]))  # recovery by cp
    add(3, lambda i: _one_span(None, -4))  # recovery by forced mate against the user
    add(6, lambda i: _one_span(None))  # NULL entry eval: excluded from rates / bucket gaps
    add(6, lambda i: _one_span(250), user_rating=750, opp_rating=760)  # sub-800 user
    add(6, lambda i: _one_span(250), base_time_seconds=None)  # NULL base time
    add(  # 4 + 4 plies in two classes: an endgame game with no >= 6-ply span
        4, lambda i: [(_ROOK_CLASS, 250, None, 4), (_PAWN_CLASS, None, None, 4)]
    )
    add(  # multi-class: rook span (conv) then pawn span (recovery); LEAD supplies the exit eval
        10, lambda i: [(_ROOK_CLASS, 250, None, _SPAN_LEN), (_PAWN_CLASS, -250, None, _SPAN_LEN)]
    )
    add(  # next span has no eval: terminal fallback to the game score
        4, lambda i: [(_ROOK_CLASS, 250, None, _SPAN_LEN), (_PAWN_CLASS, None, None, _SPAN_LEN)]
    )
    plain_cps = (-20, 10)
    add(plain_games, lambda i: _one_span(plain_cps[i % 2]))  # the isolation knob block
    return specs


def _non_endgame_specs(count: int) -> list[_GameSpec]:
    """Plain non-endgame games (ply-0 position only), outcomes ~30% win / 10% draw / 60% loss."""
    specs: list[_GameSpec] = []
    for i in range(count):
        mod = i % 10
        outcome = "win" if mod < 3 else ("draw" if mod == 3 else "loss")
        specs.append(
            _GameSpec(
                outcome=outcome,
                user_color="white" if i % 2 == 0 else "black",
                positions=[_PosSpec(ply=0)],
            )
        )
    return specs


def _excluded_specs() -> list[_GameSpec]:
    """Endgame games that fail the canonical slice; a leak would visibly move the numbers."""
    return [
        _GameSpec(  # 37 months old
            outcome="win", positions=[_PosSpec(ply=0), *_span(30, _ROOK_CLASS, entry_cp=250)],
            days_ago=_STALE_DAYS_AGO, in_slice=False,
        ),
        _GameSpec(  # opponent +150 Elo
            outcome="win", positions=[_PosSpec(ply=0), *_span(30, _ROOK_CLASS, entry_cp=250)],
            opp_rating=_OPP_ELO_OUT_OF_BAND, in_slice=False,
        ),
        _GameSpec(  # unrated
            outcome="win", positions=[_PosSpec(ply=0), *_span(30, _ROOK_CLASS, entry_cp=250)],
            rated=False, in_slice=False,
        ),
        _GameSpec(  # computer opponent
            outcome="win", positions=[_PosSpec(ply=0), *_span(30, _ROOK_CLASS, entry_cp=250)],
            is_computer_game=True, in_slice=False,
        ),
    ]  # fmt: skip


def _build_specs(*, endgame_games: int, endgame_result: str) -> list[_GameSpec]:
    dominant = "win" if endgame_result == "1-0" else "loss"
    return [
        *_endgame_blocks(endgame_games, dominant),
        *_non_endgame_specs(_NON_ENDGAME_GAMES),
        *_excluded_specs(),
    ]


# ── Seed writer ──────────────────────────────────────────────────────────────


def _make_game(user_id: int, tag: str, idx: int, spec: _GameSpec, base: datetime.datetime) -> Game:
    if spec.user_color == "white":
        white_rating, black_rating = spec.user_rating, spec.opp_rating
        white_username, black_username = "me", "opp"
    else:
        white_rating, black_rating = spec.opp_rating, spec.user_rating
        white_username, black_username = "opp", "me"
    game = Game(
        user_id=user_id,
        platform="lichess",
        platform_game_id=f"rankedparity-{tag}-{user_id}-{idx}",
        pgn="1. e4 e5 *",
        result=_result_str(spec.outcome, spec.user_color),
        user_color=spec.user_color,
        termination=spec.termination,
        time_control_str=f"{_BASE_TIME_SECONDS}+0",
        time_control_bucket=_TC,
        time_control_seconds=_BASE_TIME_SECONDS,
        base_time_seconds=spec.base_time_seconds,
        rated=spec.rated,
        is_computer_game=spec.is_computer_game,
        white_username=white_username,
        black_username=black_username,
        white_rating=white_rating,
        black_rating=black_rating,
    )
    game.played_at = base - datetime.timedelta(days=spec.days_ago, minutes=idx)
    return game


async def _seed_specs(session_maker, user_id: int, specs: list[_GameSpec], tag: str) -> list[int]:
    """Insert the specs; return the ids of the games that sit inside the ranked slice."""
    base = datetime.datetime.now(datetime.timezone.utc)
    in_slice_ids: list[int] = []
    async with session_maker() as session:
        for idx, spec in enumerate(specs):
            game = _make_game(user_id, tag, idx, spec, base)
            session.add(game)
            await session.flush()
            if spec.in_slice:
                in_slice_ids.append(game.id)
            for pos in spec.positions:
                session.add(
                    GamePosition(
                        game_id=game.id,
                        user_id=user_id,
                        ply=pos.ply,
                        full_hash=1_000_000 + game.id * 100 + pos.ply,
                        white_hash=2_000_000 + game.id * 100 + pos.ply,
                        black_hash=3_000_000 + game.id * 100 + pos.ply,
                        endgame_class=pos.endgame_class,
                        eval_cp=pos.eval_cp,
                        eval_mate=pos.eval_mate,
                        clock_seconds=pos.clock_seconds,
                    )
                )
        await session.commit()
    return in_slice_ids


async def _seed_ranked_parity_user(
    session_maker,
    user_id: int,
    *,
    endgame_games: int = _DEFAULT_ENDGAME_GAMES,
    endgame_result: str = "1-0",
) -> list[int]:
    """Seed one user's blitz games; return the ids of games INSIDE the ranked slice.

    ``endgame_result`` is the user-perspective dominant result of the endgame block:
    "1-0" means the user mostly wins, "0-1" mostly loses (3/5 dominant, 1/5 draw,
    1/5 the opposite). The four excluded rows are not in the returned list.
    """
    specs = _build_specs(endgame_games=endgame_games, endgame_result=endgame_result)
    return await _seed_specs(session_maker, user_id, specs, "parity")


# ── Fixtures ─────────────────────────────────────────────────────────────────


async def _delete_users(session_maker, user_ids: list[int]) -> None:
    async with session_maker() as session:
        await session.execute(delete(User).where(User.id.in_(user_ids)))
        await session.commit()


@pytest.fixture
async def ranked_parity_user(test_engine) -> AsyncIterator[tuple[int, async_sessionmaker]]:
    """A seeded user; the user (and by CASCADE every game) is deleted in teardown."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email=f"ranked-parity-{uuid.uuid4()}@example.com", hashed_password="x")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id
    try:
        await _seed_ranked_parity_user(session_maker, user_id)
        yield user_id, session_maker
    finally:
        await _delete_users(session_maker, [user_id])


def _tc_stats(response: EndgameRankedStatsResponse, tc: TimeControlBucket) -> RankedTcStats:
    for tc_stats in response.tcs:
        if tc_stats.tc == tc:
            return tc_stats
    raise AssertionError(f"{tc} missing from ranked stats")


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("family", _ALL_FAMILIES)
async def test_on_read_value_matches_canonical_cte(ranked_parity_user, family: CdfMetricId) -> None:
    """On-read value and n equal the Stage A/B CTE for the same user and TC."""
    user_id, session_maker = ranked_parity_user
    async with session_maker() as session:
        oracle = await _compute_metric_for_user_per_tc(session, user_id, family, _TC)
        ranked = await get_ranked_stats(session, user_id=user_id)
    assert oracle is not None, f"seed must clear the {family} floor"
    metric = _tc_stats(ranked, _TC).metrics[family]
    assert metric.value == pytest.approx(oracle[0], abs=_ABS_TOL)
    assert metric.n == oracle[1]


async def test_entry_flow_actual_minus_expected_is_achievable_gap(ranked_parity_user) -> None:
    """The entry-flow card and the achievable_score_gap metric describe the same cohort."""
    user_id, session_maker = ranked_parity_user
    async with session_maker() as session:
        ranked = await get_ranked_stats(session, user_id=user_id)
    tc_stats = _tc_stats(ranked, _TC)
    flow = tc_stats.overall.entry_flow
    metric = tc_stats.metrics["achievable_score_gap"]
    assert flow.actual_score is not None and flow.expected_score is not None
    assert metric.value is not None
    assert flow.actual_score - flow.expected_score == pytest.approx(metric.value, abs=_ABS_TOL)
    assert flow.n == metric.n


async def test_bucket_wdl_consistent_with_rates(ranked_parity_user) -> None:
    """Conversion / parity / recovery rate == W/D/L-derived value of the same bucket."""
    user_id, session_maker = ranked_parity_user
    async with session_maker() as session:
        ranked = await get_ranked_stats(session, user_id=user_id)
    tc_stats = _tc_stats(ranked, _TC)
    by_bucket = {b.bucket: b for b in tc_stats.buckets}
    assert [b.bucket for b in tc_stats.buckets] == ["conversion", "parity", "recovery"]
    conv, parity, recov = by_bucket["conversion"], by_bucket["parity"], by_bucket["recovery"]
    expected_rates: list[tuple[CdfMetricId, RankedBucketOut, float]] = [
        ("conversion_rate", conv, conv.wins / conv.games),
        ("parity_rate", parity, (parity.wins + parity.draws / 2) / parity.games),
        ("recovery_rate", recov, (recov.wins + recov.draws) / recov.games),
    ]
    for metric_id, bucket, expected_rate in expected_rates:
        metric = tc_stats.metrics[metric_id]
        assert bucket.games == metric.n > 0
        assert bucket.wins + bucket.draws + bucket.losses == bucket.games
        assert metric.value == pytest.approx(expected_rate, abs=_ABS_TOL)


async def test_ranked_timelines_populated_for_seeded_tc(ranked_parity_user) -> None:
    """The seeded TC carries a Score Gap timeline and ELO combos built from ranked rows."""
    user_id, session_maker = ranked_parity_user
    async with session_maker() as session:
        ranked = await get_ranked_stats(session, user_id=user_id)
    tc_stats = _tc_stats(ranked, _TC)
    assert tc_stats.score_gap_timeline, "seeded TC must emit at least one timeline point"
    last = tc_stats.score_gap_timeline[-1]
    assert 0.0 <= last.endgame_score <= 1.0
    assert 0.0 <= last.non_endgame_score <= 1.0
    assert tc_stats.elo_timeline, "seeded TC must emit at least one ELO combo"
    assert all(combo.time_control == _TC for combo in tc_stats.elo_timeline)


async def test_ranked_curve_and_type_rows_for_seeded_tc(ranked_parity_user) -> None:
    """The seeded TC has a five-bullet pressure curve and type rows."""
    user_id, session_maker = ranked_parity_user
    async with session_maker() as session:
        ranked = await get_ranked_stats(session, user_id=user_id)
    tc_stats = _tc_stats(ranked, _TC)
    assert [b.quintile_index for b in tc_stats.time_pressure.quintiles] == [0, 1, 2, 3, 4]
    assert tc_stats.type_categories
    assert {c.endgame_class for c in tc_stats.type_categories} <= {
        "rook",
        "minor_piece",
        "pawn",
        "queen",
    }


@pytest.fixture
async def small_ranked_user(test_engine) -> AsyncIterator[tuple[int, async_sessionmaker]]:
    """A user below every 30-game floor: 20 conversion-type endgame games, 35 others."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email=f"ranked-small-{uuid.uuid4()}@example.com", hashed_password="x")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id
    try:
        specs = [
            _endgame_game(k, dominant="win", spans=_one_span(250))
            for k in range(_SMALL_ENDGAME_GAMES)
        ] + _non_endgame_specs(_SMALL_NON_ENDGAME_GAMES)
        await _seed_specs(session_maker, user_id, specs, "small")
        yield user_id, session_maker
    finally:
        await _delete_users(session_maker, [user_id])


async def test_below_floor_families_still_carry_value_and_n(small_ranked_user) -> None:
    """A family the CTE drops (below its floor) still has an on-read value with n < 30."""
    user_id, session_maker = small_ranked_user
    async with session_maker() as session:
        for family in ("score_gap", "conversion_rate", "achievable_score_gap"):
            assert await _compute_metric_for_user_per_tc(session, user_id, family, _TC) is None
        ranked = await get_ranked_stats(session, user_id=user_id)
    metrics = _tc_stats(ranked, _TC).metrics
    assert set(metrics) == set(_ALL_FAMILIES)
    for family in ("score_gap", "conversion_rate", "achievable_score_gap"):
        assert metrics[family].value is not None
        assert metrics[family].n == _SMALL_ENDGAME_GAMES < _FLOOR
    # No parity-bucket game exists: nothing to average, n is 0.
    assert metrics["parity_rate"].value is None
    assert metrics["parity_rate"].n == 0


async def test_ranked_stats_two_user_isolation(test_engine) -> None:
    """Each user's ranked stats carry only that user's games, values and percentile."""
    session_maker = async_sessionmaker(test_engine, expire_on_commit=False)
    user_ids: list[int] = []
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            id_a, _, headers_a = await _register_and_login(client)
            user_ids.append(id_a)
            id_b, _, headers_b = await _register_and_login(client)
            user_ids.append(id_b)

            slice_a = await _seed_ranked_parity_user(session_maker, id_a)
            slice_b = await _seed_ranked_parity_user(
                session_maker, id_b, endgame_games=55, endgame_result="0-1"
            )
            assert set(slice_a).isdisjoint(slice_b)

            oracle: dict[int, tuple[float, int]] = {}
            async with session_maker() as session:
                for uid, planted in ((id_a, _PLANTED_PERCENTILE_A), (id_b, _PLANTED_PERCENTILE_B)):
                    got = await _compute_metric_for_user_per_tc(session, uid, "score_gap", _TC)
                    assert got is not None
                    oracle[uid] = got
                    await upsert_percentile(
                        session,
                        user_id=uid,
                        metric="score_gap",
                        time_control_bucket=_TC,
                        value=got[0],
                        n_games=got[1],
                        percentile=planted,
                        cdf_snapshot=datetime.date.today(),
                    )
                await session.commit()

            bodies: dict[int, dict] = {}
            for uid, headers in ((id_a, headers_a), (id_b, headers_b)):
                resp = await client.get("/api/endgames/ranked-stats", headers=headers)
                assert resp.status_code == 200
                bodies[uid] = resp.json()

        # Own value / n / percentile / game count, and never the other user's.
        assert oracle[id_a][1] != oracle[id_b][1]
        assert oracle[id_a][0] != pytest.approx(oracle[id_b][0], abs=_ABS_TOL)
        expectations = (
            (id_a, slice_a, _PLANTED_PERCENTILE_A, id_b),
            (id_b, slice_b, _PLANTED_PERCENTILE_B, id_a),
        )
        for uid, own_slice, planted, other in expectations:
            blitz = next(t for t in bodies[uid]["tcs"] if t["tc"] == _TC)
            metric = blitz["metrics"]["score_gap"]
            assert blitz["ranked_games"] == len(own_slice)
            assert blitz["ranked_games"] != len(slice_a) + len(slice_b)
            assert metric["value"] == pytest.approx(oracle[uid][0], abs=_ABS_TOL)
            assert metric["n"] == oracle[uid][1]
            assert metric["value"] != pytest.approx(oracle[other][0], abs=_ABS_TOL)
            assert metric["n"] != oracle[other][1]
            assert metric["percentile"] == planted

        # Service level: fetch_ranked_games and get_ranked_stats are scoped the same way.
        async with session_maker() as session:
            fetched = await fetch_ranked_games(session, user_id=id_a, tc=_TC)
            assert sorted(g.game_id for g in fetched) == sorted(slice_a)
            assert set(g.game_id for g in fetched).isdisjoint(slice_b)
            service_a = await get_ranked_stats(session, user_id=id_a)
        assert service_a.model_dump(mode="json") == bodies[id_a]
    finally:
        await _delete_users(session_maker, user_ids)
