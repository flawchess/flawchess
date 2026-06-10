"""Unit tests for the Phase 106 library-service severity-count seam.

Phase 108 D-02 migration: chip curation and tag-distribution tests updated to
use the new game_flaws-backed API (_curate_chips_from_rows, _build_tag_distribution).
The _curate_chips (FlawRecord-based) and _GameFlaws/_compute_tag_distribution helpers
were retired; tests now either use GameFlaw objects (chip curation) or call
_build_tag_distribution with direct keyword aggregates (distribution unit tests).

Wave-0 scaffold (106-01). Covers the additive `count_game_severities` kernel
helper: per-game B/M/I counts (incl. inaccuracy) restricted to the USER's moves,
gated identically to `classify_game_flaws` (>= EVAL_COVERAGE_MIN coverage,
else GameNotAnalyzed with reason="no_engine_analysis").

No DB required — GamePosition / Game objects are built in memory à la
tests/services/test_flaws_service.py.
"""

from typing import cast

import pytest

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.services.eval_utils import eval_cp_to_expected_score
from app.services.flaws_service import (
    BLUNDER_DROP,
    MISTAKE_DROP,
    GameNotAnalyzed,
    SeverityCounts,
    count_game_severities,
)


def _make_game_flaw(
    *,
    user_id: int = 1,
    game_id: int = 1,
    ply: int = 2,
    severity: int = 2,  # 2=blunder
    tempo: int | None = None,
    phase: int = 1,  # 1=middlegame
    is_miss: bool = False,
    is_lucky: bool = False,
    is_reversed: bool = False,
    is_squandered: bool = False,
) -> GameFlaw:
    """Build a minimal in-memory GameFlaw object for unit testing (no DB flush)."""
    row = GameFlaw()
    row.user_id = user_id
    row.game_id = game_id
    row.ply = ply
    row.severity = severity
    row.tempo = tempo
    row.phase = phase
    row.is_miss = is_miss
    row.is_lucky = is_lucky
    row.is_reversed = is_reversed
    row.is_squandered = is_squandered
    # Phase 112 (D-07): es_before, es_after, move_san removed from game_flaws
    row.fen = ""
    return row


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
# TestCardChips (-k chips) — chip curation (106-02, D-02 updated)
# ---------------------------------------------------------------------------


class TestCardChips:
    """_curate_chips_from_rows: dedupe, phase exclusion, deterministic order.

    D-02 migration: updated from FlawRecord-based _curate_chips to GameFlaw
    row-based _curate_chips_from_rows. Phase tags (opening/middlegame/endgame)
    are excluded via the _CHIP_ORDER constant (not encoded in GameFlaw columns).
    Tempo tags come from the integer `tempo` column via _TEMPO_INT_TO_TAG lookup.
    """

    def test_chips_exclude_phase_and_dedupe(self) -> None:
        """Phase tags dropped (not in _CHIP_ORDER); one chip per tag; stable order."""
        from app.services.library_service import _curate_chips_from_rows

        # Flaw 1: reversed (phase=middlegame=1 excluded) + hasty (tempo=1)
        # Flaw 2: hasty (duplicate -> deduped) + miss
        # _TEMPO_INT: hasty=1, _CHIP_ORDER: miss < reversed < hasty
        row1 = _make_game_flaw(ply=2, phase=1, is_reversed=True, tempo=1)  # hasty
        row2 = _make_game_flaw(ply=4, phase=0, is_miss=True, tempo=1)  # hasty + miss
        chips = _curate_chips_from_rows([row1, row2])
        # Phase tags (middlegame/opening) never appear in chips (not in _CHIP_ORDER)
        assert "middlegame" not in chips
        assert "opening" not in chips
        # dedupe: hasty appears once
        assert chips.count("hasty") == 1
        # all non-phase tags present
        assert set(chips) == {"reversed", "hasty", "miss"}
        # deterministic order follows _CHIP_ORDER: miss < reversed < hasty
        assert chips == ["miss", "reversed", "hasty"]

    def test_chips_empty_when_no_flaws(self) -> None:
        """No flaw rows -> no chips."""
        from app.services.library_service import _curate_chips_from_rows

        assert _curate_chips_from_rows([]) == []

    def test_chips_only_phase_yields_empty(self) -> None:
        """A flaw row with no boolean tags and no tempo produces no chips.

        Phase is encoded as an integer column (not in chip booleans), so a
        row with all False booleans and tempo=None yields an empty chip list.
        """
        from app.services.library_service import _curate_chips_from_rows

        row = _make_game_flaw(ply=2, phase=2, tempo=None)  # endgame, no other tags
        chips = _curate_chips_from_rows([row])
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


async def _seed_db_flaw(
    session: object,
    *,
    game: object,
    ply: int,
    severity: int = 2,  # 2=blunder
    tempo: int | None = None,
    phase: int = 1,  # 1=middlegame
    is_miss: bool = False,
    is_lucky: bool = False,
    is_reversed: bool = False,
    is_squandered: bool = False,
) -> None:
    """Insert a GameFlaw row for the given game."""
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.game import Game as GameModel
    from app.models.game_flaw import GameFlaw

    sess = cast(AsyncSession, session)
    g = cast(GameModel, game)
    flaw = GameFlaw(
        user_id=g.user_id,
        game_id=g.id,
        ply=ply,
        severity=severity,
        tempo=tempo,
        phase=phase,
        is_miss=is_miss,
        is_lucky=is_lucky,
        is_reversed=is_reversed,
        is_squandered=is_squandered,
        # Phase 112 (D-07): es_before, es_after, move_san removed from game_flaws
        fen="",
    )
    sess.add(flaw)
    await sess.flush()


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
        # game_positions provide eval coverage + total_user_moves denominator.
        # game_flaws provide the M+B count for fetch_stats_aggregates (D-02).
        game = await _seed_db_game(session, user_id=99971, user_color="white")
        await _seed_db_pos(session, game=game, ply=0, eval_cp=prev_b)
        await _seed_db_pos(session, game=game, ply=1, eval_cp=prev_b)  # black clean
        await _seed_db_pos(session, game=game, ply=2, eval_cp=curr_b)  # white blunder
        for ply in range(3, 11):
            await _seed_db_pos(session, game=game, ply=ply, eval_cp=curr_b)  # flat -> clean
        # Seed one game_flaws row: blunder at ply 2 (white mover, phase=middlegame).
        await _seed_db_flaw(session, game=game, ply=2, severity=2, phase=1)

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
    async def test_reversed_rate_and_distribution(self, db_session: object) -> None:
        """1 reversed of 2 M+B flaws -> reversed_rate == 0.5."""
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.services.library_service import get_flaw_stats
        from tests.conftest import ensure_test_user

        session = cast(AsyncSession, db_session)
        await ensure_test_user(session, 99972)

        prev_b, curr_b = _cp_for_white_drop(BLUNDER_DROP)
        # Two white (user) blunders. game_positions provide eval coverage.
        # game_flaws rows carry the tag columns (is_reversed, phase).
        game = await _seed_db_game(session, user_id=99972, user_color="white", result="1-0")
        win_cp = 800  # white-POV winning ES ~ >=0.85
        await _seed_db_pos(session, game=game, ply=0, eval_cp=win_cp, phase=1)
        await _seed_db_pos(session, game=game, ply=1, eval_cp=win_cp, phase=1)  # black clean
        await _seed_db_pos(session, game=game, ply=2, eval_cp=0, phase=1)  # white blunder #1
        await _seed_db_pos(session, game=game, ply=3, eval_cp=0, phase=2)  # black clean
        await _seed_db_pos(session, game=game, ply=4, eval_cp=curr_b, phase=2)  # white blunder #2
        for ply in range(5, 11):
            await _seed_db_pos(session, game=game, ply=ply, eval_cp=curr_b, phase=2)
        # Blunder #1: phase=middlegame (1), reversed=True (was winning >=0.70, dropped to <=0.30).
        # Blunder #2: phase=endgame (2), reversed=False (already losing on both sides).
        await _seed_db_flaw(session, game=game, ply=2, severity=2, phase=1, is_reversed=True)
        await _seed_db_flaw(session, game=game, ply=4, severity=2, phase=2, is_reversed=False)

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
        # exactly one of the two blunders is reversed -> rate == 0.5
        assert resp.tag_distribution.reversed_rate == pytest.approx(0.5)
        # phase histogram: blunder #1 phase=1=middlegame, blunder #2 phase=2=endgame
        hist = resp.tag_distribution.phase_histogram
        assert hist["middlegame"] == 1
        assert hist["endgame"] == 1
        # tempo: no clock data seeded -> all tempo counts are 0
        assert sum(resp.tag_distribution.tempo.values()) == 0

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

    @pytest.mark.asyncio
    async def test_miss_rate_and_lucky_rate(self, db_session: object) -> None:
        """1 miss + 1 lucky out of 2 M+B flaws -> rates == 0.5 each.

        D-02 migration: seeds game_flaws rows directly (is_miss / is_lucky
        boolean columns) instead of calling the retired _compute_tag_distribution
        with hand-crafted FlawRecord objects. The API (get_flaw_stats) reads from
        game_flaws via fetch_stats_aggregates (COUNT(*) FILTER aggregates).
        """
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.services.library_service import get_flaw_stats
        from tests.conftest import ensure_test_user

        session = cast(AsyncSession, db_session)
        await ensure_test_user(session, 99975)

        prev_b, curr_b = _cp_for_white_drop(BLUNDER_DROP)
        # White (user) game, plies 0..10 all evaled -> full coverage -> analyzed.
        win_cp = 800
        game = await _seed_db_game(session, user_id=99975, user_color="white", result="1-0")
        await _seed_db_pos(session, game=game, ply=0, eval_cp=win_cp)
        await _seed_db_pos(session, game=game, ply=1, eval_cp=win_cp)  # black clean
        await _seed_db_pos(session, game=game, ply=2, eval_cp=0)  # white blunder #1
        await _seed_db_pos(session, game=game, ply=3, eval_cp=0)  # black clean
        await _seed_db_pos(session, game=game, ply=4, eval_cp=curr_b)  # white blunder #2
        for ply in range(5, 11):
            await _seed_db_pos(session, game=game, ply=ply, eval_cp=curr_b)

        # Seed two game_flaws rows: blunder #1 is a miss, blunder #2 is a lucky.
        await _seed_db_flaw(session, game=game, ply=2, severity=2, phase=1, is_miss=True)
        await _seed_db_flaw(session, game=game, ply=4, severity=2, phase=2, is_lucky=True)

        resp = await get_flaw_stats(
            session,
            user_id=99975,
            time_control=None,
            platform=None,
            rated=None,
            opponent_type="all",
            from_date=None,
            to_date=None,
            flaw_severity=None,
        )
        assert resp.per_severity_counts["blunder"] == 2
        assert resp.tag_distribution.miss_rate == pytest.approx(0.5)
        assert resp.tag_distribution.lucky_rate == pytest.approx(0.5)
        assert resp.tag_distribution.reversed_rate == 0.0

    def test_reversed_rate(self) -> None:
        """1 reversed of 2 M+B flaws -> reversed_rate == 0.5 (pure unit test).

        D-02 migration: calls _build_tag_distribution with direct keyword aggregates
        (from the SQL COUNT(*) FILTER scan) instead of the retired
        _compute_tag_distribution(_GameFlaws) per-game FlawRecord loop.
        """
        from app.services.library_service import _build_tag_distribution

        dist = _build_tag_distribution(
            mistake_count=0,
            blunder_count=2,
            tempo_low_clock=0,
            tempo_hasty=0,
            tempo_unrushed=0,
            is_reversed=1,
            is_miss=1,
            is_lucky=0,
            is_squandered=0,
            phase_opening=0,
            phase_middlegame=1,
            phase_endgame=1,
        )
        assert dist.reversed_rate == pytest.approx(0.5)
        assert dist.miss_rate == pytest.approx(0.5)
        assert dist.lucky_rate == 0.0

    def test_rates_zero_when_no_mb_flaws(self) -> None:
        """0 M+B flaws -> all four rates are 0.0 (no ZeroDivisionError).

        D-02 migration: calls _build_tag_distribution with all-zero aggregates
        instead of the retired _compute_tag_distribution([]).
        """
        from app.services.library_service import _build_tag_distribution

        dist = _build_tag_distribution(
            mistake_count=0,
            blunder_count=0,
            tempo_low_clock=0,
            tempo_hasty=0,
            tempo_unrushed=0,
            is_reversed=0,
            is_miss=0,
            is_lucky=0,
            is_squandered=0,
            phase_opening=0,
            phase_middlegame=0,
            phase_endgame=0,
        )
        assert dist.miss_rate == 0.0
        assert dist.lucky_rate == 0.0
        assert dist.reversed_rate == 0.0
        assert dist.squandered_rate == 0.0


# ---------------------------------------------------------------------------
# TestGetLibraryGame (-k get_library_game) — single-game card (Plan 112-02, SC-7)
# ---------------------------------------------------------------------------


class TestGetLibraryGame:
    """get_library_game: single-game card builder with IDOR guard.

    Plan 112-02 (SC-7): GET /api/library/games/{game_id} returns one GameFlawCard
    for the authenticated user's own game, None for another user's game or a
    missing game (→ 404 at the router). No router dependency — service-level only.
    """

    @pytest.mark.asyncio
    async def test_own_game_returns_card(self, db_session: object) -> None:
        """get_library_game returns a GameFlawCard for a game owned by the user.

        Seeds user A with an analyzed game (10 positions, >=90% eval coverage)
        and one game_flaw row. Asserts the returned card has the expected game_id
        and a non-null analysis_state.
        """
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.models.game import Game as GameModel
        from app.schemas.library import GameFlawCard
        from app.services.library_service import get_library_game
        from tests.conftest import ensure_test_user

        session = cast(AsyncSession, db_session)
        await ensure_test_user(session, 99980)

        game_obj = await _seed_db_game(session, user_id=99980, user_color="white", result="1-0")
        game = cast(GameModel, game_obj)
        # Seed 10 positions, 9 with eval_cp (coverage = 9/10 = 0.9 >= EVAL_COVERAGE_MIN)
        for ply in range(9):
            await _seed_db_pos(session, game=game, ply=ply, eval_cp=0)
        # Final position: no eval (standard lichess convention)
        await _seed_db_pos(session, game=game, ply=9, eval_cp=None)
        # One blunder flaw
        await _seed_db_flaw(session, game=game, ply=2, severity=2, phase=1)

        card = await get_library_game(session, user_id=99980, game_id=game.id)

        assert card is not None, "Expected a GameFlawCard for own game, got None"
        assert isinstance(card, GameFlawCard), f"Expected GameFlawCard, got {type(card)}"
        assert card.game_id == game.id

    @pytest.mark.asyncio
    async def test_cross_user_returns_none(self, db_session: object) -> None:
        """get_library_game returns None when game belongs to a different user (IDOR guard).

        Seeds user A with a game. User B requests that game_id. Must return None
        (not the card, not a 403, not a 404 exception — the IDOR guard lives at
        the service layer; the router maps None → 404). This is the T-112-01
        mitigation: game.user_id != user_id → return None.
        """
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.models.game import Game as GameModel
        from app.services.library_service import get_library_game
        from tests.conftest import ensure_test_user

        session = cast(AsyncSession, db_session)
        await ensure_test_user(session, 99981)  # user A
        await ensure_test_user(session, 99982)  # user B

        game_obj = await _seed_db_game(session, user_id=99981, user_color="white", result="1-0")
        game_a = cast(GameModel, game_obj)

        # User B tries to fetch user A's game — must return None (IDOR guard)
        result = await get_library_game(session, user_id=99982, game_id=game_a.id)
        assert result is None, (
            f"IDOR breach: expected None for cross-user access, got game_id={getattr(result, 'game_id', result)}"
        )

    @pytest.mark.asyncio
    async def test_missing_game_returns_none(self, db_session: object) -> None:
        """get_library_game returns None for a non-existent game_id."""
        from sqlalchemy.ext.asyncio import AsyncSession

        from app.services.library_service import get_library_game
        from tests.conftest import ensure_test_user

        session = cast(AsyncSession, db_session)
        await ensure_test_user(session, 99983)

        result = await get_library_game(session, user_id=99983, game_id=999999999)
        assert result is None, f"Expected None for non-existent game_id, got {result}"
