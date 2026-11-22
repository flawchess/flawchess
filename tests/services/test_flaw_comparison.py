"""Backend tests for the per-TC flaw-comparison service.

Validation architecture:
- test_per_tc_split              : one entry per TC, fast to slow, 12 bullets each
- test_no_analyzed_games         : empty tcs, gate echoed, total_n still counts
- test_bullets_and_zone_bounds   : registry-banded bullets, no domain
- test_rates_and_pvalue          : player_rate - opp_rate == delta, p-value
- test_ci_formula                : 99% Wald-z math independent of SQL
- test_user_moves_parity         : white = ceil(ply_count/2), black = floor
- test_filter_plumbing           : filter kwargs narrow the TC list
- test_severity_filter_zones     : zones stay with severity filter
- test_zero_event_bullet         : zero-event -> delta=None

The db_session fixture wraps each test in a transaction that is always rolled
back, so seeded users and games never leak into other tests.
"""

import datetime
import math
import uuid
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.services.blunder_check_rules import FACEPALM_LIBRARY_LAMBDA, FACEPALM_STATS_MIN
from app.repositories.library_repository import (
    _analyzed_game_ids_subquery,
    count_analyzed_by_tc,
    fetch_flaw_comparison,
    fetch_recent_window_rows,
)
from app.services.flaw_delta_zones import (
    FLAW_DELTA_METRICS,
    FLAW_DELTA_ZONES,
    ZoneBand,
    flaw_delta_zone,
    tempo_phase_zone,
)
from app.services.canonical_slice_sql import RECENT_GAMES_PER_TC_CAP
from app.services.library_service import (
    FLAW_COMPARISON_GATE,
    _build_flaw_bullet,
    get_facepalm_comparison,
    get_flaw_comparison,
    recent_window_start,
    summarize_window,
)
from app.services.facepalm_score import FacepalmType
from app.services.facepalm_zones import facepalm_zone
from app.services.score_confidence import VERDICT_CI_Z_99
from tests.facepalm_seed import SEED_FACEPALM_MARGIN, facepalm_fact_columns

# ---------------------------------------------------------------------------
# Seed helpers (mirror tests/test_library_repository.py pattern)
# ---------------------------------------------------------------------------

# 258: the Library Stats snapshot ranks games inside a recent window anchored on now_utc, so a
# seed without a played_at would fall out of it. A fixed _NOW keeps the tests independent of
# the real clock.
_NOW = datetime.datetime(2026, 11, 21, 12, 0, tzinfo=datetime.timezone.utc)
_SEED_PLAYED_AT = _NOW - datetime.timedelta(days=1)


async def _ensure_user(session: AsyncSession, user_id: int) -> None:
    from sqlalchemy import select

    from app.models.user import User

    existing = (await session.execute(select(User).where(User.id == user_id))).unique()
    if existing.scalar_one_or_none() is None:
        session.add(
            User(id=user_id, email=f"flaw-cmp-test-{user_id}@example.com", hashed_password="x")
        )
        await session.flush()


async def _seed_game(
    session: AsyncSession,
    *,
    user_id: int,
    user_color: str = "white",
    ply_count: int = 40,
    platform: str = "lichess",
    time_control_bucket: str | None = "blitz",
    time_control_str: str = "600+0",
    played_at: datetime.datetime = _SEED_PLAYED_AT,
) -> Game:
    game = Game(
        user_id=user_id,
        platform=platform,
        platform_game_id=str(uuid.uuid4()),
        platform_url="https://lichess.org/test",
        pgn="1. e4 e5 *",
        result="1-0",
        user_color=user_color,
        time_control_str=time_control_str,
        time_control_bucket=time_control_bucket,
        time_control_seconds=600,
        base_time_seconds=600,
        increment_seconds=0.0,
        rated=True,
        is_computer_game=False,
        ply_count=ply_count,
        played_at=played_at,
    )
    session.add(game)
    await session.flush()
    return game


async def _seed_analyzed(session: AsyncSession, *, game: "Game") -> None:  # type: ignore[name-defined]
    """Mark the game analyzed via both gates.

    _analyzed_game_ids_subquery uses the authoritative full_evals_completed_at
    column, not a per-ply eval-coverage recompute. The
    cheap Game.is_analyzed detector (white_blunders IS NOT NULL) is seeded too, as
    a real Lichess analyzed game satisfies both.
    """
    # Cheap analyzed detector: move-quality counts present (0 = analyzed, no blunders).
    if game.white_blunders is None:
        game.white_blunders = 0

    # Authoritative analyzed gate: full_evals_completed_at IS NOT NULL.
    game.full_evals_completed_at = datetime.datetime.now(tz=datetime.timezone.utc)
    await session.flush()


async def _seed_flaw(
    session: AsyncSession,
    *,
    game: Game,
    ply: int,
    severity: int = 1,  # 1=mistake
    tempo: int | None = None,
    phase: int = 1,  # 1=middlegame
    is_miss: bool = False,
    is_lucky: bool = False,
    is_reversed: bool = False,
    is_squandered: bool = False,
    facts: dict[str, Any] | None = None,
) -> None:
    """Insert one game_flaws row; `facts` are extra GameFlaw keyword values (257 D-12).

    Facepalm reader tests pass `facepalm_fact_columns(...)` here: the score is computed at
    query time from the stored facts, never read from a stored column.
    """
    from app.repositories.game_flaws_repository import bulk_insert_game_flaws

    await bulk_insert_game_flaws(
        session,
        [
            {
                "user_id": game.user_id,
                "game_id": game.id,
                "ply": ply,
                "severity": severity,
                "tempo": tempo,
                "phase": phase,
                "is_miss": is_miss,
                "is_lucky": is_lucky,
                "is_reversed": is_reversed,
                "is_squandered": is_squandered,
                "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
                **(facts or {}),
            }
        ],
    )


_DEFAULT_FILTER_KWARGS: dict[str, Any] = dict(
    time_control=None,
    platform=None,
    rated=None,
    opponent_type="all",
    from_date=None,
    to_date=None,
    flaw_severity=None,
    opponent_gap_min=None,
    opponent_gap_max=None,
    color=None,
)


def _filters(**overrides: Any) -> dict[str, Any]:
    """Default filter kwargs with per-test overrides."""
    return {**_DEFAULT_FILTER_KWARGS, **overrides}


# User ID reserved for flaw comparison tests (no collision with other test modules)
_TEST_USER = 88888


@pytest_asyncio.fixture(autouse=True)
async def _create_test_user(db_session: AsyncSession) -> None:
    await _ensure_user(db_session, _TEST_USER)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_per_tc_split(db_session: AsyncSession) -> None:
    """25 blitz + 25 rapid analyzed games -> tcs == [blitz, rapid], 12 bullets each.

    Blitz games carry a player mistake, rapid games do not: pooling the rows would
    blur the two TCs, so the per-TC mistake events must differ.
    """
    for _ in range(25):
        g = await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket="blitz")
        await _seed_analyzed(db_session, game=g)
        await _seed_flaw(db_session, game=g, ply=2, severity=1)  # player mistake
    for _ in range(25):
        g = await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket="rapid")
        await _seed_analyzed(db_session, game=g)

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    assert [t.tc for t in result.tcs] == ["blitz", "rapid"]
    for tc_entry in result.tcs:
        assert tc_entry.analyzed_n == 25
        assert tc_entry.below_gate is False
        assert [b.tag for b in tc_entry.bullets] == list(FLAW_DELTA_METRICS)

    blitz_mistake = next(b for b in result.tcs[0].bullets if b.tag == "mistake")
    rapid_mistake = next(b for b in result.tcs[1].bullets if b.tag == "mistake")
    assert blitz_mistake.player_events == 25
    assert rapid_mistake.player_events == 0
    assert blitz_mistake.delta is not None and blitz_mistake.delta > 0
    assert rapid_mistake.delta is None


@pytest.mark.asyncio
async def test_no_analyzed_games(db_session: AsyncSession) -> None:
    """No analyzed games -> tcs == [] and analyzed_gate is the gate constant."""
    await _seed_game(db_session, user_id=_TEST_USER)  # not analyzed

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    assert result.tcs == []
    assert result.analyzed_gate == FLAW_COMPARISON_GATE
    # The unanalyzed game still counts, so the page can show "0 of 1 analyzed"
    # instead of reading as if the filters matched nothing.
    assert result.total_n == 1


@pytest.mark.asyncio
async def test_no_games_total_n_zero(db_session: AsyncSession) -> None:
    """No games at all -> tcs == [] and total_n == 0 (the true "nothing here" case)."""
    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    assert result.tcs == []
    assert result.total_n == 0


@pytest.mark.asyncio
async def test_bullets_and_zone_bounds(db_session: AsyncSession) -> None:
    """Each TC's bullets carry that TC's own band; no bullet has a domain."""
    for bucket in ("blitz", "rapid"):
        for _ in range(FLAW_COMPARISON_GATE):
            g = await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket=bucket)
            await _seed_analyzed(db_session, game=g)
            await _seed_flaw(db_session, game=g, ply=2, severity=1, tempo=1)  # hasty

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    assert [t.tc for t in result.tcs] == ["blitz", "rapid"]
    for tc_entry in result.tcs:
        hasty = next(b for b in tc_entry.bullets if b.tag == "hasty")
        own_band = flaw_delta_zone("hasty", tc_entry.tc)
        assert (hasty.zone_lo, hasty.zone_hi) == (own_band.zone_lo, own_band.zone_hi)
        assert hasty.has_zone is True
        for bullet in tc_entry.bullets:
            assert "domain" not in type(bullet).model_fields
            band = flaw_delta_zone(bullet.tag, tc_entry.tc)
            assert bullet.zone_lo == band.zone_lo, f"zone_lo mismatch for {bullet.tag}"
            assert bullet.zone_hi == band.zone_hi, f"zone_hi mismatch for {bullet.tag}"


@pytest.mark.asyncio
async def test_rates_and_pvalue(db_session: AsyncSession) -> None:
    """player_rate/opp_rate/p_value populated; player_rate - opp_rate == delta.

    Seeds 20 analyzed games each with one player mistake (ply=2, white) so the
    mistake bullet has a nonzero, significant positive delta and per-player rates.
    """
    for _ in range(FLAW_COMPARISON_GATE):
        game = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=game)
        await _seed_flaw(db_session, game=game, ply=2, severity=1)  # player mistake

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )
    mistake = next(b for b in result.tcs[0].bullets if b.tag == "mistake")

    # Per-player rates present and consistent with the delta (paired pairing).
    assert mistake.player_rate is not None
    assert mistake.opp_rate is not None
    assert mistake.delta is not None
    assert mistake.player_rate - mistake.opp_rate == pytest.approx(mistake.delta, abs=1e-9)
    # Player committed the only mistakes -> player_rate > opp_rate (== 0).
    assert mistake.player_rate > mistake.opp_rate
    # Identical positive delta across all 20 games -> highly significant.
    assert mistake.p_value is not None
    assert mistake.p_value < 0.05

    # Zero-event bullets keep all the rate fields None.
    low_clock = next(b for b in result.tcs[0].bullets if b.tag == "low_clock")
    assert low_clock.player_rate is None
    assert low_clock.opp_rate is None
    assert low_clock.p_value is None


def test_ci_formula() -> None:
    """Bullet CI = the shared paired test at 99%, verified independently of SQL.

    - n=1 -> CI None (no variance), not significant
    - n>=2 -> ci_high - mean == z99 * sample_sd / sqrt(n)  within float tolerance
    """
    # n=1 edge case: one game has no variance, so no CI and no verdict.
    single = _build_flaw_bullet("mistake", "blitz", [3.5], [3.5], [0.0], 1, 0)
    assert single.delta == 3.5
    assert single.ci_low is None
    assert single.ci_high is None
    assert single.significant is False

    # n>=2: verify the Wald-z formula explicitly
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    n = len(values)
    expected_mean = sum(values) / n  # 3.0
    sample_var = sum((v - expected_mean) ** 2 for v in values) / (n - 1)  # 2.5
    expected_half = VERDICT_CI_Z_99 * math.sqrt(sample_var / n)

    bullet = _build_flaw_bullet("mistake", "blitz", values, values, [0.0] * n, n, 0)

    assert bullet.delta is not None and bullet.ci_low is not None and bullet.ci_high is not None
    assert abs(bullet.delta - expected_mean) < 1e-10
    assert abs(bullet.ci_high - bullet.delta - expected_half) < 1e-10
    assert abs(bullet.delta - bullet.ci_low - expected_half) < 1e-10
    # 99% CI = 3.0 +/- 1.82 excludes 0 -> significant.
    assert bullet.significant is True


@pytest.mark.asyncio
async def test_user_moves_parity(db_session: AsyncSession) -> None:
    """user_moves = ceil(ply_count/2) for white, floor for black (white moves first).

    A 41-ply game has 21 white moves and 20 black moves. The anchor used to flip this.
    """
    white = await _seed_game(db_session, user_id=_TEST_USER, user_color="white", ply_count=41)
    black = await _seed_game(db_session, user_id=_TEST_USER, user_color="black", ply_count=41)
    for g in (white, black):
        await _seed_analyzed(db_session, game=g)

    rows = await fetch_flaw_comparison(
        db_session,
        _TEST_USER,
        _analyzed_game_ids_subquery(_TEST_USER),
        **_DEFAULT_FILTER_KWARGS,
    )

    user_moves = {row.game_id: int(row.user_moves) for row in rows}
    assert user_moves == {white.id: 21, black.id: 20}


@pytest.mark.asyncio
async def test_filter_plumbing(db_session: AsyncSession) -> None:
    """Filter kwargs narrow the analyzed set and the TC list.

    Seeds 20 blitz games on lichess (player mistake each) and 20 rapid games on
    chess.com (no flaws). Unfiltered: two TC entries. time_control=["blitz"]: one.
    """
    for _ in range(FLAW_COMPARISON_GATE):
        g_blitz = await _seed_game(
            db_session,
            user_id=_TEST_USER,
            user_color="white",
            platform="lichess",
            time_control_bucket="blitz",
        )
        await _seed_analyzed(db_session, game=g_blitz)
        await _seed_flaw(db_session, game=g_blitz, ply=2, severity=1)  # player mistake

    for _ in range(FLAW_COMPARISON_GATE):
        g_rapid = await _seed_game(
            db_session,
            user_id=_TEST_USER,
            user_color="white",
            platform="chess.com",
            time_control_bucket="rapid",
        )
        await _seed_analyzed(db_session, game=g_rapid)

    result_all = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )
    assert [(t.tc, t.analyzed_n) for t in result_all.tcs] == [
        ("blitz", FLAW_COMPARISON_GATE),
        ("rapid", FLAW_COMPARISON_GATE),
    ]

    result_blitz = await get_flaw_comparison(
        db_session,
        _TEST_USER,
        now_utc=_NOW,
        **_filters(time_control=["blitz"]),
    )
    assert [(t.tc, t.analyzed_n) for t in result_blitz.tcs] == [("blitz", FLAW_COMPARISON_GATE)]
    mistake_blitz = next(b for b in result_blitz.tcs[0].bullets if b.tag == "mistake")
    assert mistake_blitz.delta is not None and mistake_blitz.delta > 0


@pytest.mark.asyncio
async def test_severity_filter_zones(db_session: AsyncSession) -> None:
    """flaw_severity=[blunder] keeps all 12 bullets WITH zone bounds.

    Seeds:
    - 20 games with BOTH player mistake + player blunder -> included under both filters
    - 20 games with player mistake ONLY -> excluded under the blunder-only filter

    The blunder filter narrows the analyzed set, so analyzed_n drops from 40 to 20
    and the blunder delta (blunders only exist in the surviving games) rises.
    """
    for _ in range(FLAW_COMPARISON_GATE):
        game = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=game)
        await _seed_flaw(db_session, game=game, ply=2, severity=1)  # mistake
        await _seed_flaw(db_session, game=game, ply=4, severity=2)  # blunder

    for _ in range(FLAW_COMPARISON_GATE):
        game = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=game)
        await _seed_flaw(db_session, game=game, ply=2, severity=1)  # mistake only

    result_all = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )
    result_blunder = await get_flaw_comparison(
        db_session,
        _TEST_USER,
        now_utc=_NOW,
        **_filters(flaw_severity=["blunder"]),
    )

    assert result_all.tcs[0].analyzed_n == 2 * FLAW_COMPARISON_GATE
    blunder_tc = result_blunder.tcs[0]
    assert blunder_tc.below_gate is False
    assert blunder_tc.analyzed_n == FLAW_COMPARISON_GATE
    assert len(blunder_tc.bullets) == 12

    for bullet in blunder_tc.bullets:
        band = flaw_delta_zone(bullet.tag, blunder_tc.tc)
        assert bullet.zone_lo == band.zone_lo, f"zone_lo missing on {bullet.tag}"
        assert bullet.zone_hi == band.zone_hi, f"zone_hi missing on {bullet.tag}"

    blunder_all = next(b for b in result_all.tcs[0].bullets if b.tag == "blunder")
    blunder_filtered = next(b for b in blunder_tc.bullets if b.tag == "blunder")
    assert blunder_all.delta is not None and blunder_filtered.delta is not None
    assert blunder_filtered.delta > blunder_all.delta


@pytest.mark.asyncio
async def test_zero_event_bullet(db_session: AsyncSession) -> None:
    """Zero player AND opp events -> delta=None (not 0.0); clean game counts toward analyzed_n.

    Seeds 20 analyzed games with NO game_flaws rows (clean games).
    """
    for _ in range(FLAW_COMPARISON_GATE):
        game = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=game)
        # No flaw rows added -> clean game contributes zero-delta anchor row

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    tc_entry = result.tcs[0]
    assert tc_entry.below_gate is False
    assert tc_entry.analyzed_n == FLAW_COMPARISON_GATE, (
        f"clean games must count toward analyzed_n; got {tc_entry.analyzed_n}"
    )
    assert len(tc_entry.bullets) == 12

    for bullet in tc_entry.bullets:
        assert bullet.delta is None, (
            f"tag {bullet.tag}: zero-event bullet must have delta=None, not {bullet.delta}"
        )
        assert bullet.ci_low is None, f"tag {bullet.tag}: ci_low should be None for zero-event"
        assert bullet.ci_high is None, f"tag {bullet.tag}: ci_high should be None for zero-event"
        assert bullet.player_events == 0
        assert bullet.opp_events == 0
        band = flaw_delta_zone(bullet.tag, tc_entry.tc)
        assert bullet.zone_lo == band.zone_lo
        assert bullet.zone_hi == band.zone_hi


# ---------------------------------------------------------------------------
# Gate, filter, NULL-bucket, significance, isolation edges
# ---------------------------------------------------------------------------

_OTHER_USER = 88889
_BELOW_GATE_GAMES = 12


@pytest.mark.asyncio
async def test_below_gate_tc_keeps_bullets(db_session: AsyncSession) -> None:
    """A TC with 12 analyzed games is listed, below_gate True, with populated rates."""
    for _ in range(_BELOW_GATE_GAMES):
        g = await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket="rapid")
        await _seed_analyzed(db_session, game=g)
        await _seed_flaw(db_session, game=g, ply=2, severity=1)  # player mistake

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    assert len(result.tcs) == 1
    tc_entry = result.tcs[0]
    assert tc_entry.tc == "rapid"
    assert tc_entry.analyzed_n == _BELOW_GATE_GAMES
    assert tc_entry.below_gate is True
    assert len(tc_entry.bullets) == 12
    mistake = next(b for b in tc_entry.bullets if b.tag == "mistake")
    assert mistake.player_rate is not None and mistake.player_rate > 0
    assert mistake.opp_rate == 0.0


@pytest.mark.asyncio
async def test_tc_filter_narrows_list_and_omits_unanalyzed_tc(db_session: AsyncSession) -> None:
    """time_control narrows tcs[]; a TC with games but none analyzed is omitted."""
    for bucket in ("blitz", "rapid"):
        for _ in range(3):
            g = await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket=bucket)
            await _seed_analyzed(db_session, game=g)
    for _ in range(5):
        # classical games exist but none is analyzed
        await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket="classical")

    result_all = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )
    assert [t.tc for t in result_all.tcs] == ["blitz", "rapid"]

    result_rapid = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_filters(time_control=["rapid"])
    )
    assert [t.tc for t in result_rapid.tcs] == ["rapid"]


@pytest.mark.asyncio
async def test_null_time_control_bucket_excluded(db_session: AsyncSession) -> None:
    """A game with a NULL time_control_bucket counts nowhere."""
    for _ in range(FLAW_COMPARISON_GATE):
        g = await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket="blitz")
        await _seed_analyzed(db_session, game=g)
    for _ in range(5):
        g = await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket=None)
        await _seed_analyzed(db_session, game=g)
        await _seed_flaw(db_session, game=g, ply=2, severity=1)  # would be a player mistake

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    assert [t.tc for t in result.tcs] == ["blitz"]
    assert result.tcs[0].analyzed_n == FLAW_COMPARISON_GATE
    for bullet in result.tcs[0].bullets:
        assert bullet.player_events == 0 and bullet.opp_events == 0

    # The service also drops unknown buckets by iterating LIBRARY_TC_ORDER, so pin the
    # repository guards directly: neither the counts nor the per-game rows may carry
    # the NULL-bucket games.
    counts = await count_analyzed_by_tc(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)
    assert counts == {"blitz": FLAW_COMPARISON_GATE}
    rows = await fetch_flaw_comparison(
        db_session,
        _TEST_USER,
        _analyzed_game_ids_subquery(_TEST_USER),
        **_DEFAULT_FILTER_KWARGS,
    )
    assert {row.tc for row in rows} == {"blitz"}


@pytest.mark.asyncio
async def test_null_or_zero_ply_count_not_counted(db_session: AsyncSession) -> None:
    """Games with ply_count NULL or 0 are not counted in analyzed_n.

    count_analyzed_by_tc must share the ply_count gate of the fetch anchors; otherwise
    a TC of such games is offered above the gate while its aggregated rows are empty.
    """
    for _ in range(FLAW_COMPARISON_GATE):
        g = await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket="blitz")
        await _seed_analyzed(db_session, game=g)
    # A rapid TC made only of games the aggregation drops (ply_count NULL / 0).
    for bad_ply_count in (None, 0):
        for _ in range(FLAW_COMPARISON_GATE):
            g = await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket="rapid")
            g.ply_count = bad_ply_count
            await _seed_analyzed(db_session, game=g)

    counts = await count_analyzed_by_tc(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)
    assert counts == {"blitz": FLAW_COMPARISON_GATE}

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )
    assert [t.tc for t in result.tcs] == ["blitz"]
    assert result.tcs[0].analyzed_n == FLAW_COMPARISON_GATE


@pytest.mark.asyncio
async def test_total_n_counts_unanalyzed_games(db_session: AsyncSession) -> None:
    """total_n is the per-TC coverage denominator: unanalyzed games count toward it only.

    The ply_count gate is shared with analyzed_n, so analyzed_n <= total_n holds and a
    NULL-ply game counts toward neither.
    """
    for _ in range(FLAW_COMPARISON_GATE):
        g = await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket="blitz")
        await _seed_analyzed(db_session, game=g)
    for _ in range(3):
        await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket="blitz")
    # Unanalyzed rapid games alone do not put rapid on the switch.
    await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket="rapid")
    g = await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket="blitz")
    g.ply_count = None
    await db_session.flush()

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    assert [(t.tc, t.analyzed_n, t.total_n) for t in result.tcs] == [
        ("blitz", FLAW_COMPARISON_GATE, FLAW_COMPARISON_GATE + 3),
    ]
    # The response-level total spans every allowed TC, unanalyzed rapid included.
    assert result.total_n == FLAW_COMPARISON_GATE + 3 + 1


async def _seed_mistake_cell(db_session: AsyncSession, *, user_id: int, total_flaws: int) -> None:
    """Seed `total_flaws` analyzed blitz games with one mistake each, alternating sides.

    White user: ply 2 (even) is the player's mistake, ply 3 (odd) is the opponent's.
    """
    for i in range(total_flaws):
        g = await _seed_game(db_session, user_id=user_id, user_color="white")
        await _seed_analyzed(db_session, game=g)
        await _seed_flaw(db_session, game=g, ply=2 if i % 2 == 0 else 3, severity=1)


# Fixture size: enough games that a one-sided cell clears the 99% CI.
_SIGNIFICANCE_GAMES = 40


@pytest.mark.asyncio
async def test_balanced_cell_is_not_significant(db_session: AsyncSession) -> None:
    """Mistakes split evenly between you and opponents: the 99% CI covers 0."""
    await _seed_mistake_cell(db_session, user_id=_TEST_USER, total_flaws=_SIGNIFICANCE_GAMES)

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    mistake = next(b for b in result.tcs[0].bullets if b.tag == "mistake")
    assert mistake.player_events == mistake.opp_events
    assert mistake.significant is False


@pytest.mark.asyncio
async def test_one_sided_cell_is_significant(db_session: AsyncSession) -> None:
    """A mistake by you in every game and none by opponents: the 99% CI excludes 0."""
    for _ in range(_SIGNIFICANCE_GAMES):
        g = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=g)
        await _seed_flaw(db_session, game=g, ply=2, severity=1)

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    mistake = next(b for b in result.tcs[0].bullets if b.tag == "mistake")
    assert mistake.opp_events == 0
    assert mistake.ci_low is not None and mistake.ci_low > 0.0
    assert mistake.significant is True


@pytest.mark.asyncio
async def test_zero_event_bullet_is_not_significant(db_session: AsyncSession) -> None:
    """A zero-event bullet has significant False and delta None."""
    for _ in range(FLAW_COMPARISON_GATE):
        g = await _seed_game(db_session, user_id=_TEST_USER)
        await _seed_analyzed(db_session, game=g)

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    for bullet in result.tcs[0].bullets:
        assert bullet.delta is None
        assert bullet.significant is False


@pytest.mark.asyncio
async def test_classical_and_bullet_bands(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bullet reads the bullet band and classical the classical band.

    The registry is patched with four distinct bands so a lookup that falls back to another
    TC (e.g. the tactic-only ZONE_TC_FOR mapping bullet -> rapid) fails here.
    """
    monkeypatch.setitem(
        FLAW_DELTA_ZONES,
        "hasty",
        {
            "bullet": ZoneBand(zone_lo=-0.05, zone_hi=0.05),
            "blitz": ZoneBand(zone_lo=-0.20, zone_hi=0.20),
            "rapid": ZoneBand(zone_lo=-0.10, zone_hi=0.10),
            "classical": ZoneBand(zone_lo=-0.50, zone_hi=0.50),
        },
    )
    for bucket in ("bullet", "classical"):
        g = await _seed_game(db_session, user_id=_TEST_USER, time_control_bucket=bucket)
        await _seed_analyzed(db_session, game=g)

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    by_tc = {t.tc: next(b for b in t.bullets if b.tag == "hasty") for t in result.tcs}
    assert set(by_tc) == {"bullet", "classical"}
    assert (by_tc["bullet"].zone_lo, by_tc["bullet"].zone_hi) == (-0.05, 0.05)
    assert (by_tc["classical"].zone_lo, by_tc["classical"].zone_hi) == (-0.50, 0.50)


@pytest.mark.asyncio
async def test_two_user_isolation(db_session: AsyncSession) -> None:
    """Each user sees only their own analyzed_n and events."""
    await _ensure_user(db_session, _OTHER_USER)
    user_a_games, user_b_games = 4, 7
    for _ in range(user_a_games):
        g = await _seed_game(db_session, user_id=_TEST_USER)
        await _seed_analyzed(db_session, game=g)
        await _seed_flaw(db_session, game=g, ply=2, severity=1)  # A: player mistake
    for _ in range(user_b_games):
        g = await _seed_game(db_session, user_id=_OTHER_USER)
        await _seed_analyzed(db_session, game=g)
        await _seed_flaw(db_session, game=g, ply=2, severity=1)  # B: player mistake
        await _seed_flaw(db_session, game=g, ply=4, severity=1)  # B: second player mistake

    result_a = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )
    result_b = await get_flaw_comparison(
        db_session, _OTHER_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    assert result_a.tcs[0].analyzed_n == user_a_games
    assert result_b.tcs[0].analyzed_n == user_b_games
    mistake_a = next(b for b in result_a.tcs[0].bullets if b.tag == "mistake")
    mistake_b = next(b for b in result_b.tcs[0].bullets if b.tag == "mistake")
    assert mistake_a.player_events == user_a_games
    assert mistake_b.player_events == 2 * user_b_games


# ---------------------------------------------------------------------------
# tempo x phase crossed cells
# ---------------------------------------------------------------------------

# SQL ints for the seed helper (game_flaws_repository._TEMPO_INT / _PHASE_INT).
_TEMPO_LOW_CLOCK, _TEMPO_HASTY, _TEMPO_UNRUSHED = 0, 1, 2
_PHASE_OPENING, _PHASE_MIDDLEGAME, _PHASE_ENDGAME = 0, 1, 2
_CELL_COUNT = 9
_BANDED_CELL_COUNT = 7
# Crossed cells without a band in the 2026-10-14 section 5 run (not zone_viable).
_ZONELESS_CELLS = {("low_clock", "opening"), ("low_clock", "middlegame")}


def _cell(tc_entry: Any, tempo: str, phase: str) -> Any:
    return next(c for c in tc_entry.tempo_phase_cells if c.tempo == tempo and c.phase == phase)


@pytest.mark.asyncio
async def test_tempo_phase_cells_shape_and_order(db_session: AsyncSession) -> None:
    """Exactly 9 cells, phase-major, tempo order inside each phase; 7 carry the registry band.

    Every cell is a zero-event cell here, so this also proves the zero-event return path
    carries the band. low_clock x opening and low_clock x middlegame have
    none (has_zone False).
    """
    for _ in range(FLAW_COMPARISON_GATE):
        g = await _seed_game(db_session, user_id=_TEST_USER)
        await _seed_analyzed(db_session, game=g)

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    cells = result.tcs[0].tempo_phase_cells
    assert len(cells) == _CELL_COUNT
    assert [(c.phase, c.tempo) for c in cells] == [
        (phase, tempo)
        for phase in ("opening", "middlegame", "endgame_phase")
        for tempo in ("low_clock", "hasty", "unrushed")
    ]
    entry = result.tcs[0]
    banded = [c for c in cells if c.has_zone]
    assert len(banded) == _BANDED_CELL_COUNT
    for c in cells:
        band = tempo_phase_zone(c.tempo, c.phase, entry.tc)
        if band is None:
            assert (c.tempo, c.phase) in _ZONELESS_CELLS
            assert c.has_zone is False
            assert (c.zone_lo, c.zone_hi) == (0.0, 0.0)
        else:
            assert c.has_zone is True
            assert (c.zone_lo, c.zone_hi) == (band.zone_lo, band.zone_hi)


@pytest.mark.asyncio
async def test_tempo_phase_cells_count_both_sides(db_session: AsyncSession) -> None:
    """Crossed cells count flaws carrying BOTH tags, for the player and the opponent."""
    for _ in range(FLAW_COMPARISON_GATE):
        g = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=g)
        await _seed_flaw(db_session, game=g, ply=2, tempo=_TEMPO_HASTY, phase=_PHASE_MIDDLEGAME)
        await _seed_flaw(db_session, game=g, ply=3, tempo=_TEMPO_HASTY, phase=_PHASE_MIDDLEGAME)
        await _seed_flaw(db_session, game=g, ply=4, tempo=_TEMPO_HASTY, phase=_PHASE_ENDGAME)

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )
    entry = result.tcs[0]

    hasty_mid = _cell(entry, "hasty", "middlegame")
    assert hasty_mid.player_events == FLAW_COMPARISON_GATE
    assert hasty_mid.opp_events == FLAW_COMPARISON_GATE
    hasty_end = _cell(entry, "hasty", "endgame_phase")
    assert hasty_end.player_events == FLAW_COMPARISON_GATE
    assert hasty_end.opp_events == 0
    low_mid = _cell(entry, "low_clock", "middlegame")
    assert low_mid.delta is None
    assert low_mid.significant is False


@pytest.mark.asyncio
async def test_tempo_phase_cells_exclude_null_tempo(db_session: AsyncSession) -> None:
    """Flaws with NULL tempo (no clock data) land in the phase marginal but in no cell."""
    for _ in range(FLAW_COMPARISON_GATE):
        g = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=g)
        await _seed_flaw(db_session, game=g, ply=2, tempo=None, phase=_PHASE_MIDDLEGAME)

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )
    entry = result.tcs[0]

    middlegame = next(b for b in entry.bullets if b.tag == "middlegame")
    assert middlegame.player_events == FLAW_COMPARISON_GATE
    for c in entry.tempo_phase_cells:
        assert c.player_events == 0
        assert c.opp_events == 0
        assert c.delta is None


@pytest.mark.asyncio
async def test_tempo_phase_cells_marginal_sum_invariant(db_session: AsyncSession) -> None:
    """With non-NULL tempo everywhere, crossed cells sum to the matching marginal bullets."""
    # (ply, tempo, phase) spread over several combos; even ply = player, odd = opponent.
    combos = [
        (2, _TEMPO_LOW_CLOCK, _PHASE_OPENING),
        (4, _TEMPO_HASTY, _PHASE_MIDDLEGAME),
        (6, _TEMPO_UNRUSHED, _PHASE_ENDGAME),
        (8, _TEMPO_HASTY, _PHASE_ENDGAME),
        (10, _TEMPO_UNRUSHED, _PHASE_OPENING),
        (3, _TEMPO_LOW_CLOCK, _PHASE_ENDGAME),
        (5, _TEMPO_HASTY, _PHASE_OPENING),
        (7, _TEMPO_UNRUSHED, _PHASE_MIDDLEGAME),
    ]
    for _ in range(FLAW_COMPARISON_GATE):
        g = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=g)
        for ply, tempo, phase in combos:
            await _seed_flaw(db_session, game=g, ply=ply, tempo=tempo, phase=phase)

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )
    entry = result.tcs[0]
    bullets = {b.tag: b for b in entry.bullets}

    for phase in ("opening", "middlegame", "endgame_phase"):
        cells = [c for c in entry.tempo_phase_cells if c.phase == phase]
        assert sum(c.player_events for c in cells) == bullets[phase].player_events
        assert sum(c.opp_events for c in cells) == bullets[phase].opp_events
    for tempo in ("low_clock", "hasty", "unrushed"):
        cells = [c for c in entry.tempo_phase_cells if c.tempo == tempo]
        assert sum(c.player_events for c in cells) == bullets[tempo].player_events
        assert sum(c.opp_events for c in cells) == bullets[tempo].opp_events


@pytest.mark.asyncio
async def test_tempo_phase_cell_significance(db_session: AsyncSession) -> None:
    """A one-sided crossed cell clears the 99% CI and keeps player_rate - opp_rate == delta."""
    for _ in range(_SIGNIFICANCE_GAMES):
        g = await _seed_game(db_session, user_id=_TEST_USER, user_color="white")
        await _seed_analyzed(db_session, game=g)
        await _seed_flaw(db_session, game=g, ply=2, tempo=_TEMPO_HASTY, phase=_PHASE_MIDDLEGAME)

    result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    cell = _cell(result.tcs[0], "hasty", "middlegame")
    assert cell.ci_low is not None and cell.ci_low > 0.0
    assert cell.p_value is not None
    assert cell.significant is True
    assert cell.delta is not None
    assert cell.player_rate is not None and cell.opp_rate is not None
    assert cell.player_rate - cell.opp_rate == pytest.approx(cell.delta, abs=1e-9)


def test_tempo_phase_cell_field_parity() -> None:
    """TempoPhaseCell carries exactly FlawBullet's stat fields, plus tempo and phase."""
    from app.schemas.library import FlawBullet, TempoPhaseCell

    assert set(TempoPhaseCell.model_fields) - {"tempo", "phase"} == set(FlawBullet.model_fields) - {
        "tag"
    }


# ---------------------------------------------------------------------------
# 257 facepalm rows (D-12 paired per 100 user moves, D-04 typed); banded per TC by the
# provisional FACEPALM_ZONES registry (quick 261121-ha7)
# ---------------------------------------------------------------------------

_BLUNDER = 2
_MISTAKE = 1
_FACEPALM_ROWS = ("facepalm", "facepalm_missed_win", "facepalm_allowed_loss")
# One white game of 40 plies: 20 user moves, so one event is 5.0 per 100 moves.
_RATE_PER_EVENT = 5.0


def _facts(score: float | None, facepalm_type: FacepalmType | None = None) -> dict[str, Any]:
    """Facts whose library-lambda score equals `score` (None = unscored), optionally typed."""
    return facepalm_fact_columns(score, lam=FACEPALM_LIBRARY_LAMBDA, facepalm_type=facepalm_type)


def _facepalm_bullet(tc_entry: Any, tag: str) -> Any:
    return next(b for b in tc_entry.bullets if b.tag == tag)


async def _seed_facepalm_game(db_session: AsyncSession, **game_kwargs: Any) -> Game:
    game = await _seed_game(
        db_session, user_id=game_kwargs.pop("user_id", _TEST_USER), **game_kwargs
    )
    await _seed_analyzed(db_session, game=game)
    return game


@pytest.mark.asyncio
async def test_facepalm_rows_are_paired_per_100_user_moves(db_session: AsyncSession) -> None:
    """Three rows per TC; both sides divide by the user's 20 moves; types are paired by type."""
    game = await _seed_facepalm_game(db_session, user_color="white", ply_count=40)
    kinds: list[tuple[int, int, dict[str, Any]]] = [
        (2, _BLUNDER, _facts(0.8, "allowed_loss")),  # user facepalm, allowed loss
        (4, _BLUNDER, _facts(0.8, "missed_win")),  # user facepalm, missed win
        (6, _BLUNDER, _facts(0.5)),  # user blunder below the 0.7 cut
        (8, _BLUNDER, _facts(None)),  # unscored: in no count
        (12, _BLUNDER, _facts(0.5)),  # keeps the user's scored coverage at 4 of 5
        (10, _MISTAKE, _facts(0.9, "allowed_loss")),  # a mistake never counts
        (3, _BLUNDER, _facts(0.9, "allowed_loss")),  # opponent facepalm, allowed loss
    ]
    for ply, severity, facts in kinds:
        await _seed_flaw(db_session, game=game, ply=ply, severity=severity, facts=facts)

    result = await get_facepalm_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    tc_entry = result.tcs[0]
    assert [b.tag for b in tc_entry.bullets] == list(_FACEPALM_ROWS)
    expected = {
        "facepalm": (2, 1),
        "facepalm_missed_win": (1, 0),
        "facepalm_allowed_loss": (1, 1),
    }
    for tag, (player_events, opp_events) in expected.items():
        bullet = _facepalm_bullet(tc_entry, tag)
        assert (bullet.player_events, bullet.opp_events) == (player_events, opp_events)
        assert bullet.player_rate == pytest.approx(player_events * _RATE_PER_EVENT)
        assert bullet.opp_rate == pytest.approx(opp_events * _RATE_PER_EVENT)
        assert bullet.delta is not None
        assert bullet.player_rate - bullet.opp_rate == pytest.approx(bullet.delta, abs=1e-9)
    total = _facepalm_bullet(tc_entry, "facepalm")
    assert (total.player_rate, total.opp_rate, total.delta) == (10.0, 5.0, 5.0)


@pytest.mark.asyncio
async def test_facepalm_total_is_sum_of_types_per_game(db_session: AsyncSession) -> None:
    """Per game and side, the total column equals missed wins plus allowed losses."""
    from app.repositories.library_repository import fetch_facepalm_comparison

    first = await _seed_facepalm_game(db_session, user_color="white")
    second = await _seed_facepalm_game(db_session, user_color="black")
    # White user: even ply = user. Black user: odd ply = user.
    for ply, ftype in ((2, "allowed_loss"), (4, "missed_win"), (6, "missed_win")):
        await _seed_flaw(
            db_session, game=first, ply=ply, severity=_BLUNDER, facts=_facts(0.8, ftype)
        )
    await _seed_flaw(
        db_session, game=first, ply=3, severity=_BLUNDER, facts=_facts(0.8, "missed_win")
    )
    for ply, ftype in ((3, "allowed_loss"), (5, "allowed_loss")):
        await _seed_flaw(
            db_session, game=second, ply=ply, severity=_BLUNDER, facts=_facts(0.85, ftype)
        )
    for ply, ftype in ((2, "allowed_loss"), (4, "missed_win")):
        await _seed_flaw(
            db_session, game=second, ply=ply, severity=_BLUNDER, facts=_facts(0.9, ftype)
        )

    rows = await fetch_facepalm_comparison(
        db_session, _TEST_USER, _analyzed_game_ids_subquery(_TEST_USER), **_DEFAULT_FILTER_KWARGS
    )

    by_game = {row.game_id: row for row in rows}
    assert set(by_game) == {first.id, second.id}
    for row in rows:
        assert (
            row.player_facepalm == row.player_facepalm_missed_win + row.player_facepalm_allowed_loss
        )
        assert row.opp_facepalm == row.opp_facepalm_missed_win + row.opp_facepalm_allowed_loss
    one = by_game[first.id]
    assert (
        one.player_facepalm,
        one.player_facepalm_missed_win,
        one.player_facepalm_allowed_loss,
    ) == (
        3,
        2,
        1,
    )
    assert (one.opp_facepalm, one.opp_facepalm_missed_win, one.opp_facepalm_allowed_loss) == (
        1,
        1,
        0,
    )
    two = by_game[second.id]
    assert (two.player_facepalm, two.player_facepalm_allowed_loss) == (2, 2)
    assert (two.opp_facepalm, two.opp_facepalm_missed_win, two.opp_facepalm_allowed_loss) == (
        2,
        1,
        1,
    )


@pytest.mark.asyncio
async def test_facepalm_anchor_same_game_set_as_flaw_comparison(db_session: AsyncSession) -> None:
    """Both readers return the same (game_id, tc, user_moves) set from one shared anchor."""
    from app.repositories.library_repository import fetch_facepalm_comparison

    kept = await _seed_facepalm_game(db_session, ply_count=41)
    await _seed_flaw(db_session, game=kept, ply=2, severity=_BLUNDER, facts=_facts(0.8))
    await _seed_game(db_session, user_id=_TEST_USER)  # not analyzed
    null_bucket = await _seed_facepalm_game(db_session, time_control_bucket=None)
    await _seed_flaw(db_session, game=null_bucket, ply=2, severity=_BLUNDER, facts=_facts(0.8))
    zero_ply = await _seed_facepalm_game(db_session)
    zero_ply.ply_count = 0
    await db_session.flush()

    kwargs = dict(_DEFAULT_FILTER_KWARGS)
    analyzed = _analyzed_game_ids_subquery(_TEST_USER)
    facepalm_rows = await fetch_facepalm_comparison(db_session, _TEST_USER, analyzed, **kwargs)
    flaw_rows = await fetch_flaw_comparison(db_session, _TEST_USER, analyzed, **kwargs)

    def keys(rows: list[Any]) -> set[tuple[int, str, int]]:
        return {(row.game_id, row.tc, int(row.user_moves)) for row in rows}

    assert keys(facepalm_rows) == keys(flaw_rows) == {(kept.id, "blitz", 21)}


@pytest.mark.asyncio
async def test_facepalm_cut_is_the_stats_min(db_session: AsyncSession) -> None:
    """A blunder just above FACEPALM_STATS_MIN counts; one just below does not."""
    game = await _seed_facepalm_game(db_session, user_color="white")
    above = FACEPALM_STATS_MIN + SEED_FACEPALM_MARGIN
    below = FACEPALM_STATS_MIN - SEED_FACEPALM_MARGIN
    await _seed_flaw(db_session, game=game, ply=2, severity=_BLUNDER, facts=_facts(above))
    await _seed_flaw(db_session, game=game, ply=4, severity=_BLUNDER, facts=_facts(below))

    result = await get_facepalm_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    assert _facepalm_bullet(result.tcs[0], "facepalm").player_events == 1


@pytest.mark.asyncio
async def test_facepalm_rows_carry_the_tc_band_and_exist_below_the_gate(
    db_session: AsyncSession,
) -> None:
    """Three banded rows per TC, in FACEPALM_METRICS order, also for a below-gate TC.

    Each row carries its own TC's provisional band (quick 261121-ha7): blitz and rapid differ on
    the missed-win row (0.09 vs 0.08), so a builder that ignores the TC fails the per-row check.
    """
    from app.services.facepalm_zones import FACEPALM_METRICS, facepalm_zone

    for bucket in ("blitz", "rapid"):
        game = await _seed_facepalm_game(db_session, time_control_bucket=bucket)
        await _seed_flaw(db_session, game=game, ply=2, severity=_BLUNDER, facts=_facts(0.8))

    result = await get_facepalm_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )
    flaw_result = await get_flaw_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    # Same TCs as the flaw comparison, which flags both as below its gate.
    assert [t.tc for t in result.tcs] == [t.tc for t in flaw_result.tcs] == ["blitz", "rapid"]
    assert [t.below_gate for t in flaw_result.tcs] == [True, True]
    for tc_entry in result.tcs:
        assert tuple(b.tag for b in tc_entry.bullets) == FACEPALM_METRICS
        for bullet in tc_entry.bullets:
            band = facepalm_zone(bullet.tag, tc_entry.tc)
            assert bullet.has_zone is True
            assert (bullet.zone_lo, bullet.zone_hi) == (band.zone_lo, band.zone_hi)
    blitz_total = _facepalm_bullet(result.tcs[0], "facepalm")
    assert (blitz_total.zone_lo, blitz_total.zone_hi) == (-0.30, 0.30)
    rapid_missed = _facepalm_bullet(result.tcs[1], "facepalm_missed_win")
    assert (rapid_missed.zone_lo, rapid_missed.zone_hi) == (-0.08, 0.08)


@pytest.mark.asyncio
@pytest.mark.parametrize("unscored_side_ply", [2, 3], ids=["user_unscored", "opponent_unscored"])
async def test_facepalm_rows_are_withheld_below_the_scored_coverage(
    db_session: AsyncSession, unscored_side_ply: int
) -> None:
    """One side mostly unscored: no rows and low_coverage, never a rate against a fake zero."""
    game = await _seed_facepalm_game(db_session, user_color="white", ply_count=80)
    scored_side_ply = 5 - unscored_side_ply  # the other parity
    for step in range(5):
        await _seed_flaw(
            db_session,
            game=game,
            ply=scored_side_ply + 2 * step,
            severity=_BLUNDER,
            facts=_facts(0.8, "allowed_loss"),
        )
        # 3 of 5 scored on this side, below the 0.8 coverage floor.
        facts = _facts(0.8, "allowed_loss") if step < 3 else _facts(None)
        await _seed_flaw(
            db_session, game=game, ply=unscored_side_ply + 2 * step, severity=_BLUNDER, facts=facts
        )

    result = await get_facepalm_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    (tc_entry,) = result.tcs
    assert tc_entry.low_coverage is True
    assert tc_entry.bullets == []


@pytest.mark.asyncio
async def test_facepalm_coverage_gate_is_inclusive_and_per_side(db_session: AsyncSession) -> None:
    """4 of 5 scored on both sides sits exactly on the floor: the rows are served."""
    game = await _seed_facepalm_game(db_session, user_color="white", ply_count=80)
    for step in range(5):
        facts = _facts(0.8, "allowed_loss") if step < 4 else _facts(None)
        for first_ply in (2, 3):
            await _seed_flaw(
                db_session, game=game, ply=first_ply + 2 * step, severity=_BLUNDER, facts=facts
            )

    result = await get_facepalm_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    (tc_entry,) = result.tcs
    assert tc_entry.low_coverage is False
    total = _facepalm_bullet(tc_entry, "facepalm")
    assert (total.player_events, total.opp_events) == (4, 4)


@pytest.mark.asyncio
async def test_facepalm_zero_event_rows_are_neutral_placeholders(db_session: AsyncSession) -> None:
    """No facepalm on either side: delta None, significant False, the TC band still served."""
    for _ in range(FLAW_COMPARISON_GATE):
        await _seed_facepalm_game(db_session)

    result = await get_facepalm_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    for bullet in result.tcs[0].bullets:
        assert bullet.delta is None and bullet.player_rate is None and bullet.opp_rate is None
        assert bullet.significant is False
        assert (bullet.player_events, bullet.opp_events) == (0, 0)
        assert bullet.has_zone is True
        band = facepalm_zone(bullet.tag, "blitz")
        assert (bullet.zone_lo, bullet.zone_hi) == (band.zone_lo, band.zone_hi)


@pytest.mark.asyncio
async def test_facepalm_one_sided_total_is_significant(db_session: AsyncSession) -> None:
    """Significance plus the TC band now drive the verdict colour (quick 261121-ha7)."""
    for _ in range(_SIGNIFICANCE_GAMES):
        game = await _seed_facepalm_game(db_session, user_color="white")
        await _seed_flaw(db_session, game=game, ply=2, severity=_BLUNDER, facts=_facts(0.8))

    result = await get_facepalm_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    total = _facepalm_bullet(result.tcs[0], "facepalm")
    assert total.opp_events == 0
    assert total.ci_low is not None and total.ci_low > 0.0
    assert total.p_value is not None
    assert total.significant is True
    assert total.has_zone is True
    assert (total.zone_lo, total.zone_hi) == (-0.30, 0.30)


@pytest.mark.asyncio
async def test_facepalm_two_user_isolation(db_session: AsyncSession) -> None:
    """Another user's facepalm blunders never reach this user's rows (T-257-07)."""
    await _ensure_user(db_session, _OTHER_USER)
    mine = await _seed_facepalm_game(db_session, user_color="white")
    await _seed_flaw(db_session, game=mine, ply=2, severity=_BLUNDER, facts=_facts(0.8))
    for _ in range(3):
        theirs = await _seed_facepalm_game(db_session, user_id=_OTHER_USER, user_color="white")
        await _seed_flaw(db_session, game=theirs, ply=2, severity=_BLUNDER, facts=_facts(0.8))
        await _seed_flaw(db_session, game=theirs, ply=3, severity=_BLUNDER, facts=_facts(0.9))

    mine_result = await get_facepalm_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )
    other_result = await get_facepalm_comparison(
        db_session, _OTHER_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    total = _facepalm_bullet(mine_result.tcs[0], "facepalm")
    assert (total.player_events, total.opp_events) == (1, 0)
    other_total = _facepalm_bullet(other_result.tcs[0], "facepalm")
    assert (other_total.player_events, other_total.opp_events) == (3, 3)


def test_flaw_comparison_no_longer_carries_facepalm_rows() -> None:
    """257 D-21: the facepalm rows moved to /facepalm-comparison; /flaw-comparison never waits."""
    from app.schemas.library import FlawComparisonTc

    assert "facepalm_bullets" not in FlawComparisonTc.model_fields


def test_facepalm_bullet_field_parity() -> None:
    """FacepalmBullet carries exactly FlawBullet's fields (only the tag type differs)."""
    from app.schemas.library import FacepalmBullet, FlawBullet

    assert set(FacepalmBullet.model_fields) == set(FlawBullet.model_fields)
    assert FacepalmBullet.model_fields["has_zone"].default is True


def test_facepalm_metrics_not_in_flaw_delta_metrics() -> None:
    """The facepalm rows stay out of the 12-metric zone registry and the benchmark generator."""
    from app.services.facepalm_zones import FACEPALM_METRICS

    assert len(FACEPALM_METRICS) == 3
    assert not set(FACEPALM_METRICS) & set(FLAW_DELTA_METRICS)


@pytest.mark.asyncio
async def test_facepalm_reads_run_with_jit_off(db_session: AsyncSession) -> None:
    """257 D-21: both facepalm readers switch JIT off for their transaction."""
    from sqlalchemy import text

    from app.repositories.library_repository import fetch_facepalm_comparison, fetch_facepalm_counts

    for reader in ("comparison", "counts"):
        await db_session.execute(text("SET LOCAL jit = on"))
        if reader == "comparison":
            await fetch_facepalm_comparison(
                db_session,
                _TEST_USER,
                _analyzed_game_ids_subquery(_TEST_USER),
                **_DEFAULT_FILTER_KWARGS,
            )
        else:
            await fetch_facepalm_counts(db_session, _TEST_USER, **_DEFAULT_FILTER_KWARGS)
        assert (await db_session.execute(text("SHOW jit"))).scalar_one() == "off", reader


def test_facepalm_inputs_index_covers_every_score_input() -> None:
    """259 D-17: a score input missing from the covering index brings the heap fetches back."""
    from app.models.base import Base
    from app.models.game_flaw import GameFlaw
    from app.services.facepalm_score import _game_flaw_columns

    table = Base.metadata.tables[GameFlaw.__tablename__]
    index = next(i for i in table.indexes if i.name == "ix_game_flaws_facepalm_inputs")
    covered = {c.name for c in index.columns} | set(index.dialect_options["postgresql"]["include"])
    inputs = {column.key for column in _game_flaw_columns()}
    assert inputs | {"ply", "game_id", "user_id"} <= covered


# ---------------------------------------------------------------------------
# 258: the facepalm rows read the same recent window as the flaw rows (D-06, D-10, D-15)
# ---------------------------------------------------------------------------

_FOUR_YEARS = datetime.timedelta(days=4 * 365)


@pytest.mark.asyncio
async def test_facepalm_same_game_set_on_the_window(db_session: AsyncSession) -> None:
    """D-06: both readers aggregate the analyzed window ids only; a 4-year-old game is out."""
    from app.repositories.library_repository import fetch_facepalm_comparison

    recent = await _seed_facepalm_game(db_session, played_at=_NOW - datetime.timedelta(days=1))
    old = await _seed_facepalm_game(db_session, played_at=_NOW - _FOUR_YEARS)
    for game in (recent, old):
        await _seed_flaw(db_session, game=game, ply=2, severity=_BLUNDER, facts=_facts(0.8))

    window_rows = await fetch_recent_window_rows(
        db_session,
        _TEST_USER,
        window_start=recent_window_start(_NOW, None, None),
        **_DEFAULT_FILTER_KWARGS,
    )
    ids = list(summarize_window(window_rows, RECENT_GAMES_PER_TC_CAP)["blitz"].analyzed_ids)
    analyzed = _analyzed_game_ids_subquery(_TEST_USER, game_ids=ids)
    facepalm_rows = await fetch_facepalm_comparison(
        db_session, _TEST_USER, analyzed, **_DEFAULT_FILTER_KWARGS
    )
    flaw_rows = await fetch_flaw_comparison(
        db_session, _TEST_USER, analyzed, **_DEFAULT_FILTER_KWARGS
    )

    def keys(rows: list[Any]) -> set[tuple[int, str, int]]:
        return {(row.game_id, row.tc, int(row.user_moves)) for row in rows}

    assert keys(facepalm_rows) == keys(flaw_rows) == {(recent.id, "blitz", 20)}

    result = await get_facepalm_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )
    (tc_entry,) = result.tcs
    assert _facepalm_bullet(tc_entry, "facepalm").player_events == 1  # not 2


@pytest.mark.asyncio
async def test_facepalm_low_coverage_on_the_window(db_session: AsyncSession) -> None:
    """D-10: the coverage rule sees only window rows; old unscored blunders cannot trip it."""
    old = await _seed_facepalm_game(db_session, user_color="white", played_at=_NOW - _FOUR_YEARS)
    for step in range(5):  # five user blunders, none scored: low coverage on its own
        await _seed_flaw(
            db_session, game=old, ply=2 + 2 * step, severity=_BLUNDER, facts=_facts(None)
        )
    recent = await _seed_facepalm_game(
        db_session, user_color="white", played_at=_NOW - datetime.timedelta(days=1)
    )
    await _seed_flaw(db_session, game=recent, ply=2, severity=_BLUNDER, facts=_facts(0.8))

    result = await get_facepalm_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    (tc_entry,) = result.tcs
    assert tc_entry.low_coverage is False
    assert [b.tag for b in tc_entry.bullets] == list(_FACEPALM_ROWS)


@pytest.mark.asyncio
async def test_facepalm_lists_window_tcs(db_session: AsyncSession) -> None:
    """D-15: every TC with a window game is listed; a TC whose games are all old is absent."""
    await _seed_facepalm_game(db_session, played_at=_NOW - datetime.timedelta(days=1))
    # Recent but unanalyzed: in the window, so the Facepalm tile of rapid never waits.
    await _seed_game(
        db_session,
        user_id=_TEST_USER,
        time_control_bucket="rapid",
        played_at=_NOW - datetime.timedelta(days=2),
    )
    await _seed_facepalm_game(
        db_session, time_control_bucket="classical", played_at=_NOW - _FOUR_YEARS
    )

    result = await get_facepalm_comparison(
        db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS
    )

    assert [t.tc for t in result.tcs] == ["blitz", "rapid"]
    rapid = result.tcs[1]
    assert rapid.low_coverage is False
    assert [b.tag for b in rapid.bullets] == list(_FACEPALM_ROWS)
    for bullet in rapid.bullets:
        assert (bullet.player_events, bullet.opp_events) == (0, 0)
        assert bullet.delta is None


@pytest.mark.asyncio
async def test_facepalm_jit_is_off_before_the_window_statement(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """258 D-10: JIT is already off when the window statement runs in the facepalm transaction."""
    from sqlalchemy import text

    from app.services import library_service

    seen: list[str] = []
    real_fetch = library_service._fetch_recent_window

    async def spy(*args: Any, **kwargs: Any) -> Any:
        seen.append((await db_session.execute(text("SHOW jit"))).scalar_one())
        return await real_fetch(*args, **kwargs)

    await db_session.execute(text("SET LOCAL jit = on"))
    monkeypatch.setattr(library_service, "_fetch_recent_window", spy)
    await get_facepalm_comparison(db_session, _TEST_USER, now_utc=_NOW, **_DEFAULT_FILTER_KWARGS)
    assert seen == ["off"]
