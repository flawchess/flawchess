"""Unit tests for the Phase 106 library-service severity-count seam.

Wave-0 scaffold (106-01). Covers the additive `count_game_severities` kernel
helper: per-game B/M/I counts (incl. inaccuracy) restricted to the USER's moves,
gated identically to `classify_game_flaws` (>= EVAL_COVERAGE_MIN coverage,
else GameNotAnalyzed with reason="no_engine_analysis").

No DB required — GamePosition / Game objects are built in memory à la
tests/services/test_flaws_service.py.

The `chips` and `stats` placeholder classes are skipped here; they are
implemented in 106-02 (card chips) / 106-03 (stats panel).
"""

from typing import cast

import pytest

from app.models.game import Game
from app.models.game_position import GamePosition
from app.services.eval_utils import eval_cp_to_expected_score
from app.services.flaws_service import (
    BLUNDER_DROP,
    MISTAKE_DROP,
    FlawRecord,
    FlawTag,
    GameNotAnalyzed,
    SeverityCounts,
    count_game_severities,
)


def _make_flaw(tags: list[FlawTag]) -> FlawRecord:
    """Build a minimal FlawRecord carrying only the tags under test."""
    return FlawRecord(
        ply=2,
        fen="",
        side="white",
        severity="blunder",
        tags=tags,
        es_before=0.9,
        es_after=0.3,
        move_san=None,
    )


def _as_counts(result: SeverityCounts | GameNotAnalyzed) -> SeverityCounts:
    """Narrow the union to SeverityCounts (both erase to dict at runtime).

    Both TypedDicts are plain dicts at runtime, so discriminate on the
    presence of the "reason" key (RESEARCH §Code Examples note). ty cannot
    narrow a TypedDict union on key presence, so we cast after the check.
    """
    assert "reason" not in result, f"expected analyzed counts, got {result}"
    return result


def _as_not_analyzed(result: SeverityCounts | GameNotAnalyzed) -> GameNotAnalyzed:
    """Narrow the union to GameNotAnalyzed via the "reason" discriminant."""
    assert "reason" in result, f"expected GameNotAnalyzed, got {result}"
    return cast(GameNotAnalyzed, result)


# ---------------------------------------------------------------------------
# In-memory builders (mirror tests/services/test_flaws_service.py)
# ---------------------------------------------------------------------------


def _make_pos(
    ply: int,
    eval_cp: int | None = None,
    eval_mate: int | None = None,
    clock_seconds: float | None = None,
    phase: int = 1,
    move_san: str | None = None,
) -> GamePosition:
    """Build a GamePosition with eval fields for pure unit testing (no DB flush)."""
    pos = GamePosition()
    pos.ply = ply
    pos.eval_cp = eval_cp
    pos.eval_mate = eval_mate
    pos.clock_seconds = clock_seconds
    pos.phase = phase
    pos.move_san = move_san
    pos.full_hash = 0
    pos.white_hash = 0
    pos.black_hash = 0
    pos.material_count = 1000
    pos.material_signature = "KP_KP"
    pos.material_imbalance = 0
    pos.has_opposite_color_bishops = False
    pos.piece_count = 2
    pos.backrank_sparse = False
    pos.mixedness = 100
    pos.endgame_class = None
    return pos


def _make_game(
    pgn: str = "1. e4 e5 *",
    user_color: str = "white",
    result: str = "1-0",
    base_time_seconds: int | None = 600,
    increment_seconds: float | None = 0.0,
) -> Game:
    """Build a minimal Game object for unit testing (no DB flush)."""
    game = Game()
    game.pgn = pgn
    game.user_color = user_color
    game.result = result
    game.base_time_seconds = base_time_seconds
    game.increment_seconds = increment_seconds
    return game


# Centipawn deltas (white-perspective) that produce a known mover-POV ES drop.
# For a WHITE mover at ply N: ES_before = ES(eval[N-1]), ES_after = ES(eval[N]).
# A drop of `d` means ES(prev) - ES(curr) >= threshold for white.
# We search a cp pair whose white-POV ES drop sits in the target band.


def _cp_for_white_drop(drop_target: float) -> tuple[int, int]:
    """Return (prev_cp, curr_cp) so the WHITE-mover ES drop is ~drop_target.

    ES(cp, white) = sigmoid. Start from prev_cp=0 (ES=0.5) and lower curr_cp
    until the drop reaches the target band.
    """
    prev_cp = 0
    es_before = eval_cp_to_expected_score(prev_cp, "white")
    curr_cp = -10
    while es_before - eval_cp_to_expected_score(curr_cp, "white") < drop_target:
        curr_cp -= 10
    return prev_cp, curr_cp


# ---------------------------------------------------------------------------
# TestCountGameSeverities
# ---------------------------------------------------------------------------


class TestCountGameSeverities:
    """count_game_severities: B/M/I counts (user moves only) or GameNotAnalyzed."""

    def test_no_engine_analysis_all_null_eval(self) -> None:
        """A chess.com-style all-null-eval game returns GameNotAnalyzed."""
        game = _make_game(user_color="white")
        positions = [_make_pos(ply=n) for n in range(5)]  # no evals at all
        not_analyzed = _as_not_analyzed(count_game_severities(game, positions))
        assert not_analyzed["reason"] == "no_engine_analysis"
        assert not_analyzed["eval_coverage"] == 0.0

    def test_analyzed_game_counts_all_three_tiers_user_only(self) -> None:
        """Counts include inaccuracy/mistake/blunder, restricted to user moves."""
        # White (the user) blunders at ply 2; black is clean throughout.
        prev_b, curr_b = _cp_for_white_drop(BLUNDER_DROP)
        # Build 5 plies, all with eval so coverage is 100%.
        # White moves are even plies (2, 4); black odd plies (1, 3).
        # ply0 baseline, ply1 black move (clean), ply2 white blunder, ...
        positions = [
            _make_pos(ply=0, eval_cp=prev_b),  # baseline before ply1
            _make_pos(ply=1, eval_cp=prev_b),  # black move N=1 (ES_before==ES_after -> no drop)
            _make_pos(
                ply=2, eval_cp=curr_b
            ),  # white move N=2: drop from prev_b -> curr_b = blunder
            _make_pos(ply=3, eval_cp=curr_b),  # black move N=3: clean
            _make_pos(ply=4, eval_cp=curr_b),  # white move N=4: clean
        ]
        game = _make_game(user_color="white")
        counts = _as_counts(count_game_severities(game, positions))
        assert counts["blunder"] == 1
        assert counts["mistake"] == 0
        # inaccuracy may be 0 here; the dedicated inaccuracy test below pins I>0.

    def test_inaccuracy_only_game_distinct_from_not_analyzed(self) -> None:
        """An inaccuracy-only analyzed game: inaccuracy>0, mistake=0, blunder=0.

        Proves the I count is NOT derived from the M+B FlawRecord set (Pitfall 3).
        """
        # White (user) makes a drop in [INACCURACY_DROP, MISTAKE_DROP).
        from app.services.flaws_service import INACCURACY_DROP

        # find a cp pair with drop in the inaccuracy band (>= INACCURACY_DROP, < MISTAKE_DROP)
        prev_cp = 0
        curr_cp = -10
        es_before = eval_cp_to_expected_score(prev_cp, "white")
        while es_before - eval_cp_to_expected_score(curr_cp, "white") < INACCURACY_DROP:
            curr_cp -= 5
        drop = es_before - eval_cp_to_expected_score(curr_cp, "white")
        assert INACCURACY_DROP <= drop < MISTAKE_DROP, f"drop {drop} not in inaccuracy band"

        positions = [
            _make_pos(ply=0, eval_cp=prev_cp),
            _make_pos(ply=1, eval_cp=prev_cp),  # black clean
            _make_pos(ply=2, eval_cp=curr_cp),  # white inaccuracy at N=2
            _make_pos(ply=3, eval_cp=curr_cp),  # black clean
        ]
        game = _make_game(user_color="white")
        counts = _as_counts(count_game_severities(game, positions))
        assert counts["inaccuracy"] > 0
        assert counts["mistake"] == 0
        assert counts["blunder"] == 0

    def test_opponent_moves_excluded(self) -> None:
        """A blunder by the OPPONENT (not the user) is not counted."""
        prev_b, curr_b = _cp_for_white_drop(BLUNDER_DROP)
        # user is BLACK; the white-POV drop above corresponds to a WHITE (opponent) blunder.
        positions = [
            _make_pos(ply=0, eval_cp=prev_b),
            _make_pos(ply=1, eval_cp=prev_b),  # black (user) move N=1 clean
            _make_pos(ply=2, eval_cp=curr_b),  # white (opponent) blunder N=2
            _make_pos(ply=3, eval_cp=curr_b),  # black (user) move N=3 clean
        ]
        game = _make_game(user_color="black")
        counts = _as_counts(count_game_severities(game, positions))
        assert counts["blunder"] == 0
        assert counts["mistake"] == 0
        assert counts["inaccuracy"] == 0

    def test_severity_counts_typed_shape(self) -> None:
        """The non-analyzed-positive result is a SeverityCounts with int fields."""
        positions = [_make_pos(ply=n, eval_cp=0) for n in range(5)]
        game = _make_game(user_color="white")
        counts = _as_counts(count_game_severities(game, positions))
        assert isinstance(counts["inaccuracy"], int)
        assert isinstance(counts["mistake"], int)
        assert isinstance(counts["blunder"], int)


# ---------------------------------------------------------------------------
# TestCardChips (-k chips) — chip curation (106-02)
# ---------------------------------------------------------------------------


class TestCardChips:
    """_curate_chips: dedupe, phase-* exclusion, deterministic order."""

    def test_chips_exclude_phase_and_dedupe(self) -> None:
        """phase-* tags dropped; one chip per remaining type; stable order."""
        from app.services.library_service import _curate_chips

        flaws = [
            _make_flaw(["from-winning", "phase-middlegame", "hasty"]),
            # duplicate hasty across flaws -> single chip; phase-opening dropped
            _make_flaw(["hasty", "phase-opening", "miss"]),
        ]
        chips = _curate_chips(flaws)
        assert "phase-middlegame" not in chips
        assert "phase-opening" not in chips
        # dedupe: hasty appears once
        assert chips.count("hasty") == 1
        # all non-phase tags present
        assert set(chips) == {"from-winning", "hasty", "miss"}
        # deterministic order follows _CHIP_ORDER: miss < from-winning < hasty
        assert chips == ["miss", "from-winning", "hasty"]

    def test_chips_empty_when_no_flaws(self) -> None:
        """No flaws -> no chips."""
        from app.services.library_service import _curate_chips

        assert _curate_chips([]) == []

    def test_chips_only_phase_tags_yields_empty(self) -> None:
        """A flaw carrying only phase-* tags produces no chips."""
        from app.services.library_service import _curate_chips

        chips = _curate_chips([_make_flaw(["phase-endgame"])])
        assert chips == []


# ---------------------------------------------------------------------------
# TestNoEngineAnalysis (-k no_engine_analysis) — service-level card state (106-02)
# ---------------------------------------------------------------------------


class TestNoEngineAnalysis:
    """get_library_games surfaces no_engine_analysis, never a false 0/0/0."""

    @pytest.mark.asyncio
    async def test_chesscom_game_card_is_no_engine_analysis(self, db_session: object) -> None:
        """A chess.com-style all-null-eval game -> no_engine_analysis card state."""
        import uuid

        from sqlalchemy.ext.asyncio import AsyncSession

        from app.models.game import Game as GameModel
        from app.models.game_position import GamePosition as PosModel
        from app.services.library_service import get_library_games
        from tests.conftest import ensure_test_user

        session = cast(AsyncSession, db_session)
        await ensure_test_user(session, 99977)

        game = GameModel(
            user_id=99977,
            platform="chess.com",
            platform_game_id=str(uuid.uuid4()),
            platform_url="https://chess.com/game/test",
            pgn="1. e4 e5 *",
            result="1-0",
            user_color="white",
            time_control_str="600+0",
            time_control_bucket="blitz",
            time_control_seconds=600,
            base_time_seconds=600,
            increment_seconds=0.0,
            rated=True,
            is_computer_game=False,
        )
        session.add(game)
        await session.flush()
        # Positions with NO eval (chess.com has no engine analysis).
        for ply in range(3):
            pos = PosModel(
                game_id=game.id,
                user_id=99977,
                ply=ply,
                full_hash=hash(f"f-{game.id}-{ply}"),
                white_hash=hash(f"w-{game.id}-{ply}"),
                black_hash=hash(f"b-{game.id}-{ply}"),
                move_san=None,
                clock_seconds=None,
                phase=1,
                eval_cp=None,
                eval_mate=None,
                piece_count=2,
                material_count=1000,
                material_signature="KP_KP",
                material_imbalance=0,
                endgame_class=None,
            )
            session.add(pos)
        await session.flush()

        resp = await get_library_games(
            session,
            user_id=99977,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            flaw_severity=None,
            offset=0,
            limit=20,
        )
        card = next(c for c in resp.games if c.game_id == game.id)
        assert card.analysis_state == "no_engine_analysis"
        assert card.severity_counts is None  # NEVER a false 0/0/0
        assert card.chips == []


# ---------------------------------------------------------------------------
# TestFlawStats (-k stats) — the stats-panel aggregate (106-03)
# ---------------------------------------------------------------------------


async def _seed_db_game(
    session: object,
    *,
    user_id: int,
    user_color: str = "white",
    result: str = "1-0",
    played_at: object = None,
    platform: str = "lichess",
) -> object:
    """Insert a Game row, returning the persisted object."""
    import datetime as _dt
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.game import Game as GameModel

    sess = cast(AsyncSession, session)
    game = GameModel(
        user_id=user_id,
        platform=platform,
        platform_game_id=str(uuid.uuid4()),
        platform_url="https://lichess.org/test",
        pgn="1. e4 e5 *",
        result=result,
        user_color=user_color,
        time_control_str="600+0",
        time_control_bucket="blitz",
        time_control_seconds=600,
        base_time_seconds=600,
        increment_seconds=0.0,
        rated=True,
        is_computer_game=False,
        played_at=played_at or _dt.datetime(2026, 1, 1, tzinfo=_dt.timezone.utc),
    )
    sess.add(game)
    await sess.flush()
    return game


async def _seed_db_pos(
    session: object,
    *,
    game: object,
    ply: int,
    eval_cp: int | None = None,
    phase: int = 1,
) -> None:
    """Insert a GamePosition row."""
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.game import Game as GameModel
    from app.models.game_position import GamePosition as PosModel

    sess = cast(AsyncSession, session)
    g = cast(GameModel, game)
    pos = PosModel(
        game_id=g.id,
        user_id=g.user_id,
        ply=ply,
        full_hash=hash(f"f-{g.id}-{ply}"),
        white_hash=hash(f"w-{g.id}-{ply}"),
        black_hash=hash(f"b-{g.id}-{ply}"),
        move_san=None,
        clock_seconds=None,
        phase=phase,
        eval_cp=eval_cp,
        eval_mate=None,
        piece_count=2,
        material_count=1000,
        material_signature="KP_KP",
        material_imbalance=0,
        endgame_class=None,
    )
    sess.add(pos)
    await sess.flush()


class TestFlawStats:
    """get_flaw_stats: counts/rates, tag distribution, trend, denominator."""

    @pytest.mark.asyncio
    async def test_per_100_moves_and_counts(self, db_session: object) -> None:
        """1 user blunder over 5 user moves -> per_100_moves blunder == 20.0."""
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.services.library_service import get_flaw_stats
        from tests.conftest import ensure_test_user

        session = cast(AsyncSession, db_session)
        await ensure_test_user(session, 99971)

        prev_b, curr_b = _cp_for_white_drop(BLUNDER_DROP)
        # White (user) game, plies 0..10 (11 positions, all evaled -> coverage 1.0).
        # User (white) moves are even plies >= 2: 2,4,6,8,10 = 5 user moves.
        # White blunders ONLY at ply 2 (prev_b -> curr_b); the rest are flat at curr_b.
        game = await _seed_db_game(session, user_id=99971, user_color="white")
        await _seed_db_pos(session, game=game, ply=0, eval_cp=prev_b)
        await _seed_db_pos(session, game=game, ply=1, eval_cp=prev_b)  # black clean
        await _seed_db_pos(session, game=game, ply=2, eval_cp=curr_b)  # white blunder
        for ply in range(3, 11):
            await _seed_db_pos(session, game=game, ply=ply, eval_cp=curr_b)  # flat -> clean

        resp = await get_flaw_stats(
            session,
            user_id=99971,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            flaw_severity=None,
        )
        assert resp.per_severity_counts["blunder"] == 1
        assert resp.per_severity_counts["mistake"] == 0
        assert resp.analyzed_n == 1
        assert resp.total_n == 1
        assert resp.analyzed_pct == 1.0
        # 1 blunder / 5 user moves * 100 = 20.0
        assert resp.rates.per_100_moves["blunder"] == pytest.approx(20.0)
        # 1 blunder / 1 analyzed game = 1.0
        assert resp.rates.per_game["blunder"] == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_result_changing_rate_and_distribution(self, db_session: object) -> None:
        """1 result-changing of 2 M+B flaws -> result_changing_rate == 0.5."""
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.services.library_service import get_flaw_stats
        from tests.conftest import ensure_test_user

        session = cast(AsyncSession, db_session)
        await ensure_test_user(session, 99972)

        prev_b, curr_b = _cp_for_white_drop(BLUNDER_DROP)
        # Two white (user) blunders. The FIRST starts from a winning ES (>=0.85)
        # and crosses into losing -> result-changing. The SECOND is already lost
        # on both sides -> not result-changing. user_result is "win" (result 1-0).
        # We need two distinct blunder transitions on white moves (plies 2 and 4).
        game = await _seed_db_game(session, user_id=99972, user_color="white", result="1-0")
        # ply0 winning baseline; ply2 white blunder from winning -> ~even (result-changing for a win)
        win_cp = 800  # white-POV winning ES ~ >=0.85
        await _seed_db_pos(session, game=game, ply=0, eval_cp=win_cp, phase=1)
        await _seed_db_pos(session, game=game, ply=1, eval_cp=win_cp, phase=1)  # black clean
        await _seed_db_pos(session, game=game, ply=2, eval_cp=0, phase=1)  # white blunder #1
        await _seed_db_pos(session, game=game, ply=3, eval_cp=0, phase=2)  # black clean
        # ply4 white blunder #2 from even to losing
        await _seed_db_pos(session, game=game, ply=4, eval_cp=curr_b, phase=2)
        for ply in range(5, 11):
            await _seed_db_pos(session, game=game, ply=ply, eval_cp=curr_b, phase=2)

        resp = await get_flaw_stats(
            session,
            user_id=99972,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            flaw_severity=None,
        )
        assert resp.per_severity_counts["blunder"] == 2
        # exactly one of the two blunders is result-changing
        assert resp.tag_distribution.result_changing_rate == pytest.approx(0.5)
        # phase histogram: blunder #1 at ply2 (phase opening->1=middlegame),
        # blunder #2 at ply4 (phase 2=endgame). _phase_tag maps 1->middlegame, 2->endgame.
        hist = resp.tag_distribution.phase_histogram
        assert hist["middlegame"] == 1
        assert hist["endgame"] == 1
        # every flaw carries exactly one tempo tag -> tempo counts sum to total flaws
        assert sum(resp.tag_distribution.tempo.values()) == 2

    @pytest.mark.asyncio
    async def test_trend_point_date_is_window_last_game(self, db_session: object) -> None:
        """Each FlawTrendPoint.date is its rolling window's last-game date."""
        import datetime as _dt

        from sqlalchemy.ext.asyncio import AsyncSession

        from app.services.library_service import get_flaw_stats
        from app.services.openings_service import MIN_GAMES_FOR_TIMELINE
        from tests.conftest import ensure_test_user

        session = cast(AsyncSession, db_session)
        await ensure_test_user(session, 99973)

        # Seed MIN_GAMES_FOR_TIMELINE analyzed games on distinct ascending dates so
        # at least one trend point is emitted; assert its date == the last game date.
        n_games = MIN_GAMES_FOR_TIMELINE
        last_date: _dt.datetime | None = None
        for i in range(n_games):
            played = _dt.datetime(2026, 2, 1, tzinfo=_dt.timezone.utc) + _dt.timedelta(days=i)
            last_date = played
            game = await _seed_db_game(session, user_id=99973, user_color="white", played_at=played)
            # 10 plies, fully evaled, flat -> analyzed but no flaws.
            for ply in range(10):
                await _seed_db_pos(session, game=game, ply=ply, eval_cp=0)

        resp = await get_flaw_stats(
            session,
            user_id=99973,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            flaw_severity=None,
        )
        assert resp.analyzed_n == n_games
        assert len(resp.trend) >= 1
        last_point = resp.trend[-1]
        assert last_date is not None
        assert last_point.date == last_date.strftime("%Y-%m-%d")
        assert last_point.game_count >= MIN_GAMES_FOR_TIMELINE

    @pytest.mark.asyncio
    async def test_empty_analyzed_set_returns_zeros(self, db_session: object) -> None:
        """A chess.com-only (unanalyzed) filtered set -> zeros, empty trend, no raise."""
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.services.library_service import get_flaw_stats
        from tests.conftest import ensure_test_user

        session = cast(AsyncSession, db_session)
        await ensure_test_user(session, 99974)

        game = await _seed_db_game(session, user_id=99974, user_color="white", platform="chess.com")
        for ply in range(10):
            await _seed_db_pos(session, game=game, ply=ply, eval_cp=None)  # no eval

        resp = await get_flaw_stats(
            session,
            user_id=99974,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            flaw_severity=None,
        )
        assert resp.total_n == 1
        assert resp.analyzed_n == 0
        assert resp.analyzed_pct == 0.0
        assert resp.per_severity_counts["blunder"] == 0
        assert resp.rates.per_100_moves["blunder"] == 0.0
        assert resp.trend == []
