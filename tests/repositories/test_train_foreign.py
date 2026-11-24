"""Tests for the Phase 263 foreign-blunder filler: the draw read path and its suite seam.

Coverage:
- test_draw_returns_servable_stranger_blunder   : band step returns a non-guest stranger's blunder
                                                  and never the solver's own identical game.
- test_nearest_step_reaches_outside_the_raw_band : the nearest-first step reaches a game the raw band
                                                  excludes.
- test_draw_skips_guest_strangers                : a guest's game is never drawn (D-01).
- test_conftest_stub_replaces_the_draw           : without `real_foreign_draw` the seam is stubbed.
- test_short_session_fills_with_foreign_blunder_and_grades_on_owner_key : the tracer, composition
                                                  to grading on the game owner's rows.
- test_conftest_stub_draws_no_foreign_blunder    : the same setup without the opt-in composes nothing.

Data isolation: the rolled-back `db_session` fixture, so no committed rows leak. The real draw
is global across users, so every DB test that uses it requests `real_foreign_draw`, seeds its own
strangers and pins the solver level to 2600 (raw 2700) where no other test seeds. The pin keeps
other tests' rows out of the band step only; the nearest-first step has no distance cap (review
IN-07). Composition tests that assert an exact count therefore request `real_foreign_band_draw`
(band step alone), and the direct `_draw` tests assert membership, never a total.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drill_item import DrillItem
from app.models.drill_session import DrillSession
from app.models.train_settings import TrainSettings
from app.models.drill_solve import DrillSolve, DrillSource
from app.repositories import train_repository
from app.services.train_foreign import (
    FOREIGN_FILLER_DRAW_STEPS,
    FOREIGN_FILLER_MAX_GAMES,
    FOREIGN_FILLER_RECONSTRUCT_SLACK,
    ForeignCandidate,
    ForeignDrawStep,
)
from tests.repositories.test_train_repository import (
    _USER_ID,
    _seed_first_session_material,
    _seed_herring_pool_row,
)
from tests.conftest import ensure_test_user
from tests.train_foreign_seed import (
    FOREIGN_KEY_UCI,
    FOREIGN_RUNNER_UP_UCI,
    FOREIGN_SEED_PLY,
    FOREIGN_SHARP_PV_LINES,
    FOREIGN_SOFT_PV_LINES,
    add_foreign_blunder_game,
    add_rated_games,
    add_stranger,
    delete_flaw_row,
    delete_game_row,
)

_NOW = datetime.datetime(2026, 1, 15, 12, 0, tzinfo=datetime.timezone.utc)
# Recent rated games of the solver at raw 2700: the pinned Elo clamps at 2600 (level 2600).
_SOLVER_RATED_GAMES = 3


# Raw rating where no other test seeds games (the pinned Elo clamps at 2600).
_STRANGER_RATING = 2700
# A solver level whose raw band (level +- 650) reaches the stranger's 2700.
_BAND_LEVEL = 2600.0
# A solver level whose raw band (2750 to 4050) excludes the stranger's 2700.
_FAR_LEVEL = 3400.0

_BAND_STEP = ForeignDrawStep(sample_percent=100.0, nearest=False)
_NEAREST_STEP = ForeignDrawStep(sample_percent=100.0, nearest=True)


async def _draw(
    session: AsyncSession, *, solver_id: int, step: ForeignDrawStep, level: float
) -> list[ForeignCandidate]:
    return await train_repository._draw_foreign_candidates(
        session,
        solver_id=solver_id,
        step=step,
        level=level,
        game_limit=FOREIGN_FILLER_MAX_GAMES,
    )


@pytest.mark.usefixtures("real_foreign_draw")
async def test_draw_returns_servable_stranger_blunder(db_session: AsyncSession) -> None:
    solver_id = await add_stranger(db_session, label="fd-solver")
    stranger_id = await add_stranger(db_session, label="fd-stranger")
    own_game = await add_foreign_blunder_game(
        db_session,
        owner_id=solver_id,
        owner_rating=_STRANGER_RATING,
        missed_pv_lines=FOREIGN_SHARP_PV_LINES,
    )
    foreign_game = await add_foreign_blunder_game(
        db_session,
        owner_id=stranger_id,
        owner_rating=_STRANGER_RATING,
        missed_pv_lines=FOREIGN_SHARP_PV_LINES,
    )

    candidates = await _draw(db_session, solver_id=solver_id, step=_BAND_STEP, level=_BAND_LEVEL)

    by_game = {candidate.game_id: candidate for candidate in candidates}
    assert own_game not in by_game
    drawn = by_game[foreign_game]
    assert drawn.missed_pv_lines == FOREIGN_SHARP_PV_LINES
    assert drawn.platform == "lichess"
    assert drawn.time_control_str == "300+0"
    assert drawn.owner_rating == _STRANGER_RATING


@pytest.mark.usefixtures("real_foreign_draw")
async def test_nearest_step_reaches_outside_the_raw_band(db_session: AsyncSession) -> None:
    solver_id = await add_stranger(db_session, label="fd-far-solver")
    stranger_id = await add_stranger(db_session, label="fd-far-stranger")
    foreign_game = await add_foreign_blunder_game(
        db_session, owner_id=stranger_id, owner_rating=_STRANGER_RATING
    )

    band = await _draw(db_session, solver_id=solver_id, step=_BAND_STEP, level=_FAR_LEVEL)
    nearest = await _draw(db_session, solver_id=solver_id, step=_NEAREST_STEP, level=_FAR_LEVEL)

    assert foreign_game not in {candidate.game_id for candidate in band}
    assert foreign_game in {candidate.game_id for candidate in nearest}


@pytest.mark.usefixtures("real_foreign_draw")
async def test_draw_skips_guest_strangers(db_session: AsyncSession) -> None:
    solver_id = await add_stranger(db_session, label="fd-guest-solver")
    guest_id = await add_stranger(db_session, label="fd-guest", is_guest=True)
    guest_game = await add_foreign_blunder_game(
        db_session, owner_id=guest_id, owner_rating=_STRANGER_RATING
    )

    band = await _draw(db_session, solver_id=solver_id, step=_BAND_STEP, level=_BAND_LEVEL)
    nearest = await _draw(db_session, solver_id=solver_id, step=_NEAREST_STEP, level=_BAND_LEVEL)

    assert guest_game not in {candidate.game_id for candidate in band + nearest}


async def test_conftest_stub_replaces_the_draw(db_session: AsyncSession) -> None:
    solver_id = await add_stranger(db_session, label="fd-stub-solver")
    stranger_id = await add_stranger(db_session, label="fd-stub-stranger")
    await add_foreign_blunder_game(db_session, owner_id=stranger_id, owner_rating=_STRANGER_RATING)

    candidates = await _draw(db_session, solver_id=solver_id, step=_BAND_STEP, level=_BAND_LEVEL)

    assert candidates == []


async def _seed_short_solver_and_stranger(db_session: AsyncSession) -> tuple[int, int]:
    """A solver with no own material at level 2600 and one stranger's sharp blunder at raw 2700."""
    solver_id = await add_stranger(db_session, label="tr-solver")
    stranger_id = await add_stranger(db_session, label="tr-stranger")
    await add_rated_games(
        db_session, user_id=solver_id, rating=_STRANGER_RATING, count=_SOLVER_RATED_GAMES
    )
    foreign_game = await add_foreign_blunder_game(
        db_session,
        owner_id=stranger_id,
        owner_rating=_STRANGER_RATING,
        missed_pv_lines=FOREIGN_SHARP_PV_LINES,
    )
    return solver_id, foreign_game


@pytest.mark.usefixtures("real_foreign_band_draw")
async def test_short_session_fills_with_foreign_blunder_and_grades_on_owner_key(
    db_session: AsyncSession,
) -> None:
    solver_id, foreign_game = await _seed_short_solver_and_stranger(db_session)

    composed = await train_repository.compose_and_materialize_session(
        db_session, user_id=solver_id, now_utc=_NOW
    )

    assert composed.session_id is not None
    assert len(composed.puzzles) == 1
    puzzle = composed.puzzles[0]
    # The stranger's game never reaches the wire (D-10, D-21).
    assert puzzle.game_id is None
    # Key and type come from the game OWNER's rows, not the solver's (which hold none).
    assert puzzle.key_move_uci == FOREIGN_KEY_UCI
    assert puzzle.puzzle_type == "sharp"
    assert puzzle.runner_up_uci == FOREIGN_RUNNER_UP_UCI
    row = (
        await db_session.execute(
            select(DrillSolve).where(DrillSolve.session_id == composed.session_id)
        )
    ).scalar_one()
    assert row.source == DrillSource.FOREIGN_BLUNDER
    assert row.game_id == foreign_game
    # A foreign row's identity is the stranger's (game_id, ply); no herring identity.
    assert row.herring_pool_id is None

    recorded = await train_repository.record_solve(
        db_session,
        user_id=solver_id,
        session_id=composed.session_id,
        position=0,
        guess="critical",
        played_move=FOREIGN_KEY_UCI,
        move_quality="good",
        now_utc=_NOW,
    )

    assert recorded is not None
    assert recorded.source == "foreign_blunder"
    assert recorded.puzzle_type == "sharp"
    assert recorded.item_status is None
    assert recorded.correct_guess is True
    assert recorded.session_complete is True
    drill_items = (
        await db_session.execute(
            select(func.count()).select_from(DrillItem).where(DrillItem.user_id == solver_id)
        )
    ).scalar_one()
    assert drill_items == 0


async def test_conftest_stub_draws_no_foreign_blunder(db_session: AsyncSession) -> None:
    solver_id, _foreign_game = await _seed_short_solver_and_stranger(db_session)

    composed = await train_repository.compose_and_materialize_session(
        db_session, user_id=solver_id, now_utc=_NOW
    )

    assert composed.session_id is None
    assert composed.puzzles == []


async def _seed_two_foreign_puzzles(db_session: AsyncSession) -> tuple[int, int, int]:
    """A solver at level 2600 and one stranger owning two qualifying sharp blunder games.

    Returns (solver_id, game_a, game_b).
    """
    solver_id = await add_stranger(db_session, label="rs-solver")
    stranger_id = await add_stranger(db_session, label="rs-stranger")
    await add_rated_games(
        db_session, user_id=solver_id, rating=_STRANGER_RATING, count=_SOLVER_RATED_GAMES
    )
    game_a = await add_foreign_blunder_game(
        db_session,
        owner_id=stranger_id,
        owner_rating=_STRANGER_RATING,
        missed_pv_lines=FOREIGN_SHARP_PV_LINES,
    )
    game_b = await add_foreign_blunder_game(
        db_session,
        owner_id=stranger_id,
        owner_rating=_STRANGER_RATING,
        missed_pv_lines=FOREIGN_SHARP_PV_LINES,
    )
    return solver_id, game_a, game_b


async def _foreign_game_by_position(
    db_session: AsyncSession, *, session_id: int
) -> dict[int, int | None]:
    rows = (
        await db_session.execute(
            select(DrillSolve.position, DrillSolve.game_id).where(
                DrillSolve.session_id == session_id
            )
        )
    ).all()
    return {position: game_id for position, game_id in rows}


async def _session_status(db_session: AsyncSession, *, session_id: int) -> str:
    return (
        await db_session.execute(select(DrillSession.status).where(DrillSession.id == session_id))
    ).scalar_one()


async def _solve_position(
    db_session: AsyncSession, *, solver_id: int, session_id: int, position: int
) -> train_repository.RecordedSolve | None:
    return await train_repository.record_solve(
        db_session,
        user_id=solver_id,
        session_id=session_id,
        position=position,
        guess="critical",
        played_move=FOREIGN_KEY_UCI,
        move_quality="good",
        now_utc=_NOW,
    )


@pytest.mark.usefixtures("real_foreign_band_draw")
async def test_resume_serves_foreign_puzzle_with_owner_key(db_session: AsyncSession) -> None:
    solver_id, _game_a, _game_b = await _seed_two_foreign_puzzles(db_session)
    composed = await train_repository.compose_and_materialize_session(
        db_session, user_id=solver_id, now_utc=_NOW
    )
    assert composed.session_id is not None
    assert len(composed.puzzles) == 2

    resumed = await train_repository.compose_and_materialize_session(
        db_session, user_id=solver_id, now_utc=_NOW
    )

    assert resumed.session_id == composed.session_id
    assert len(resumed.puzzles) == 2
    for fresh, again in zip(composed.puzzles, resumed.puzzles, strict=True):
        # The stranger's game never reaches the wire, and the FEN is rebuilt from the stranger's PGN.
        assert again.game_id is None
        assert again.fen == fresh.fen
        assert again.last_move_uci == fresh.last_move_uci
        assert again.ply == FOREIGN_SEED_PLY
        # The key is read live from the OWNER's row (the solver owns no flaw rows).
        assert again.key_move_uci == FOREIGN_KEY_UCI


@pytest.mark.usefixtures("real_foreign_band_draw")
async def test_deleted_foreign_game_dropped_and_session_completes(
    db_session: AsyncSession,
) -> None:
    solver_id, game_a, game_b = await _seed_two_foreign_puzzles(db_session)
    composed = await train_repository.compose_and_materialize_session(
        db_session, user_id=solver_id, now_utc=_NOW
    )
    assert composed.session_id is not None
    games = await _foreign_game_by_position(db_session, session_id=composed.session_id)
    position_a = next(pos for pos, gid in games.items() if gid == game_a)
    position_b = next(pos for pos, gid in games.items() if gid == game_b)

    # The stranger deletes game B: drill_solves.game_id becomes NULL (ON DELETE SET NULL).
    await delete_game_row(db_session, game_id=game_b)

    resumed = await train_repository.compose_and_materialize_session(
        db_session, user_id=solver_id, now_utc=_NOW
    )
    assert [puzzle.position for puzzle in resumed.puzzles] == [position_a]
    assert position_b not in {puzzle.position for puzzle in resumed.puzzles}

    recorded = await _solve_position(
        db_session, solver_id=solver_id, session_id=composed.session_id, position=position_a
    )

    assert recorded is not None
    assert recorded.session_complete is True
    assert await _session_status(db_session, session_id=composed.session_id) == "completed"


@pytest.mark.usefixtures("real_foreign_band_draw")
async def test_vanished_foreign_flaw_dropped_and_never_pins_session(
    db_session: AsyncSession,
) -> None:
    solver_id, game_a, game_b = await _seed_two_foreign_puzzles(db_session)
    composed = await train_repository.compose_and_materialize_session(
        db_session, user_id=solver_id, now_utc=_NOW
    )
    assert composed.session_id is not None
    games = await _foreign_game_by_position(db_session, session_id=composed.session_id)
    position_a = next(pos for pos, gid in games.items() if gid == game_a)

    # Reclassification removes the stranger's flaw row for game B; the game itself survives.
    await delete_flaw_row(db_session, game_id=game_b)

    resumed = await train_repository.compose_and_materialize_session(
        db_session, user_id=solver_id, now_utc=_NOW
    )
    assert [puzzle.position for puzzle in resumed.puzzles] == [position_a]

    recorded = await _solve_position(
        db_session, solver_id=solver_id, session_id=composed.session_id, position=position_a
    )

    assert recorded is not None
    assert recorded.session_complete is True
    assert await _session_status(db_session, session_id=composed.session_id) == "completed"


# ---------------------------------------------------------------------------
# Draw decisions (D-01, D-02, D-05, D-06, D-16, D-17)
# ---------------------------------------------------------------------------


@dataclass
class _DrawSpy:
    """Stands in for the `_draw_foreign_candidates` seam: records each call, answers from a script."""

    results: list[list[ForeignCandidate]] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def __call__(
        self,
        session: AsyncSession,
        *,
        solver_id: int,
        step: ForeignDrawStep,
        level: float,
        game_limit: int,
    ) -> list[ForeignCandidate]:
        self.calls.append(
            {"solver_id": solver_id, "step": step, "level": level, "game_limit": game_limit}
        )
        index = len(self.calls) - 1
        return list(self.results[index]) if index < len(self.results) else []


def _install_draw_spy(
    monkeypatch: pytest.MonkeyPatch, results: list[list[ForeignCandidate]] | None = None
) -> _DrawSpy:
    spy = _DrawSpy(results=results or [])
    monkeypatch.setattr(train_repository, "_draw_foreign_candidates", spy)
    return spy


def _candidate_of(game_id: int, *, missed_pv_lines: list[dict[str, object]]) -> ForeignCandidate:
    """The candidate row the draw statement would return for a game seeded by the helpers."""
    return ForeignCandidate(
        game_id=game_id,
        ply=FOREIGN_SEED_PLY,
        missed_pv_lines=list(missed_pv_lines),
        platform="lichess",
        time_control_bucket="blitz",
        time_control_str="300+0",
        owner_rating=_STRANGER_RATING,
    )


async def _compose(db_session: AsyncSession, solver_id: int) -> train_repository.ComposedSession:
    return await train_repository.compose_and_materialize_session(
        db_session, user_id=solver_id, now_utc=_NOW
    )


@pytest.mark.usefixtures("real_foreign_draw")
async def test_draw_excludes_guest_and_solver_games(db_session: AsyncSession) -> None:
    solver_id = await add_stranger(db_session, label="d01-solver")
    guest_id = await add_stranger(db_session, label="d01-guest", is_guest=True)
    stranger_id = await add_stranger(db_session, label="d01-stranger")
    own_game = await add_foreign_blunder_game(
        db_session, owner_id=solver_id, owner_rating=_STRANGER_RATING
    )
    guest_game = await add_foreign_blunder_game(
        db_session, owner_id=guest_id, owner_rating=_STRANGER_RATING
    )
    stranger_game = await add_foreign_blunder_game(
        db_session, owner_id=stranger_id, owner_rating=_STRANGER_RATING
    )

    for step in (_BAND_STEP, _NEAREST_STEP):
        drawn = {
            candidate.game_id
            for candidate in await _draw(
                db_session, solver_id=solver_id, step=step, level=_BAND_LEVEL
            )
        }

        # The identical non-guest stranger game is the only one returned (D-01).
        assert stranger_game in drawn
        assert own_game not in drawn
        assert guest_game not in drawn


@dataclass(frozen=True)
class _LevelCase:
    rated_games: int
    stored_level: str | None
    expected_level: float


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(_LevelCase(0, "beginner", 1000.0), id="stored-level-beginner"),
        pytest.param(_LevelCase(0, None, 1500.0), id="no-level-default-1500"),
        pytest.param(_LevelCase(_SOLVER_RATED_GAMES, None, 2600.0), id="median-pinned-elo"),
    ],
)
async def test_level_passed_to_draw(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, case: _LevelCase
) -> None:
    solver_id = await add_stranger(db_session, label="d05-solver")
    if case.rated_games:
        await add_rated_games(
            db_session, user_id=solver_id, rating=_STRANGER_RATING, count=case.rated_games
        )
    await train_repository.get_or_create_settings(db_session, user_id=solver_id)
    if case.stored_level is not None:
        await db_session.execute(
            update(TrainSettings)
            .where(TrainSettings.user_id == solver_id)
            .values(blunder_check_level=case.stored_level)
        )
    spy = _install_draw_spy(monkeypatch)

    await _compose(db_session, solver_id)

    assert spy.calls, "a session with no own material must reach the foreign draw"
    assert {call["level"] for call in spy.calls} == {case.expected_level}


@dataclass(frozen=True)
class _PredicateCase:
    flaw: dict[str, Any]
    composes: bool


# Each non-control case breaks exactly one of the six shared pool predicates (D-06).
_DEAD_BAND_PV_LINES: list[dict[str, object]] = [
    {"b": 40, "bm": None, "s": -30, "sm": None, "su": FOREIGN_RUNNER_UP_UCI}
]
_STILL_WINNING_PV_LINES: list[dict[str, object]] = [
    {"b": 900, "bm": None, "s": 400, "sm": None, "su": FOREIGN_RUNNER_UP_UCI}
]
_HOPELESS_PRIOR_EVAL_CP = -800
_MISTAKE_SEVERITY = 1
_OPPONENT_PLY = 3


@pytest.mark.usefixtures("real_foreign_band_draw")
@pytest.mark.parametrize(
    "case",
    [
        pytest.param(_PredicateCase({}, True), id="control-qualifying-blunder"),
        pytest.param(_PredicateCase({"severity": _MISTAKE_SEVERITY}, False), id="mistake"),
        pytest.param(_PredicateCase({"ply": _OPPONENT_PLY}, False), id="opponents-move"),
        pytest.param(_PredicateCase({"missed_pv_lines": None}, False), id="no-blob"),
        pytest.param(_PredicateCase({"missed_pv_lines": []}, False), id="empty-blob"),
        pytest.param(
            _PredicateCase({"missed_pv_lines": _DEAD_BAND_PV_LINES}, False), id="dead-band"
        ),
        pytest.param(
            _PredicateCase({"missed_pv_lines": _STILL_WINNING_PV_LINES}, False),
            id="still-winning-second-best",
        ),
        pytest.param(
            _PredicateCase({"prior_eval_cp": _HOPELESS_PRIOR_EVAL_CP}, False), id="hopeless-prior"
        ),
    ],
)
async def test_foreign_candidate_rejects_each_pool_predicate(
    db_session: AsyncSession, case: _PredicateCase
) -> None:
    solver_id = await add_stranger(db_session, label="d06-solver")
    stranger_id = await add_stranger(db_session, label="d06-stranger")
    await add_rated_games(
        db_session, user_id=solver_id, rating=_STRANGER_RATING, count=_SOLVER_RATED_GAMES
    )
    await add_foreign_blunder_game(
        db_session, owner_id=stranger_id, owner_rating=_STRANGER_RATING, **case.flaw
    )

    composed = await _compose(db_session, solver_id)

    assert (len(composed.puzzles) == 1) is case.composes
    assert (composed.session_id is not None) is case.composes


@pytest.mark.usefixtures("real_foreign_band_draw")
async def test_foreign_never_served_twice_across_sessions(db_session: AsyncSession) -> None:
    solver_id, game_a, game_b = await _seed_two_foreign_puzzles(db_session)
    first = await _compose(db_session, solver_id)
    assert first.session_id is not None
    assert {puzzle.position for puzzle in first.puzzles} == {0, 1}
    for position in (0, 1):
        await _solve_position(
            db_session, solver_id=solver_id, session_id=first.session_id, position=position
        )
    served = set(
        (
            await db_session.execute(
                select(DrillSolve.game_id).where(DrillSolve.session_id == first.session_id)
            )
        )
        .scalars()
        .all()
    )
    assert served == {game_a, game_b}

    later = await train_repository.compose_and_materialize_session(
        db_session, user_id=solver_id, now_utc=_NOW + datetime.timedelta(days=_LATER_SESSION_DAYS)
    )

    # The pool holds only A and B, both already served: nothing is left to draw (D-17).
    assert later.session_id is None
    assert later.puzzles == []


# A later day on the same weekday, well past the first session's window.
_LATER_SESSION_DAYS = 14


@pytest.mark.usefixtures("real_foreign_band_draw")
async def test_herring_game_excluded_from_foreign_pick(db_session: AsyncSession) -> None:
    solver_id = await add_stranger(db_session, label="hc-solver")
    stranger_id = await add_stranger(db_session, label="hc-stranger")
    await add_rated_games(
        db_session, user_id=solver_id, rating=_STRANGER_RATING, count=_SOLVER_RATED_GAMES
    )
    foreign_game = await add_foreign_blunder_game(
        db_session,
        owner_id=stranger_id,
        owner_rating=_STRANGER_RATING,
        missed_pv_lines=FOREIGN_SHARP_PV_LINES,
    )
    # A herring pool row on the SAME stranger game and ply: the foreign pick on it would collide
    # on uq_drill_solves_session_puzzle.
    _game, herring_id = await _seed_herring_pool_row(
        db_session, stranger_id, "hc-herring", existing_game_id=foreign_game, ply=FOREIGN_SEED_PLY
    )

    composed = await _compose(db_session, solver_id)

    assert composed.session_id is not None
    assert [puzzle.herring_pool_id for puzzle in composed.puzzles] == [herring_id]
    sources = (
        (
            await db_session.execute(
                select(DrillSolve.source).where(DrillSolve.session_id == composed.session_id)
            )
        )
        .scalars()
        .all()
    )
    assert list(sources) == [DrillSource.RED_HERRING]


async def test_full_own_supply_draws_no_foreign(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await ensure_test_user(db_session, _USER_ID)
    # Five own soft blunders and one herring fill the default six-puzzle session exactly.
    await _seed_first_session_material(db_session, sharp_sr=0, soft_sr=5, herrings=1)
    spy = _install_draw_spy(monkeypatch)

    composed = await _compose(db_session, _USER_ID)

    assert composed.puzzle_count == _DEFAULT_SESSION_SIZE
    assert spy.calls == []


_DEFAULT_SESSION_SIZE = 6


async def _solver_with_foreign_games(
    db_session: AsyncSession, *, games: int
) -> tuple[int, list[ForeignCandidate]]:
    """A solver at level 2600 and `games` stranger games; returns the candidate rows a draw yields."""
    solver_id = await add_stranger(db_session, label="st-solver")
    stranger_id = await add_stranger(db_session, label="st-stranger")
    await add_rated_games(
        db_session, user_id=solver_id, rating=_STRANGER_RATING, count=_SOLVER_RATED_GAMES
    )
    candidates = [
        _candidate_of(
            await add_foreign_blunder_game(
                db_session,
                owner_id=stranger_id,
                owner_rating=_STRANGER_RATING,
                missed_pv_lines=FOREIGN_SHARP_PV_LINES,
            ),
            missed_pv_lines=FOREIGN_SHARP_PV_LINES,
        )
        for _ in range(games)
    ]
    return solver_id, candidates


async def test_nearest_step_runs_only_on_short_band_step(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    solver_id, candidates = await _solver_with_foreign_games(db_session, games=1)
    spy = _install_draw_spy(monkeypatch, results=[[], candidates])

    composed = await _compose(db_session, solver_id)

    # The band step left the shortfall unfilled, so the nearest-first step ran and filled it.
    assert [call["step"].nearest for call in spy.calls] == [False, True]
    assert len(spy.calls) <= len(FOREIGN_FILLER_DRAW_STEPS)
    assert [puzzle.ply for puzzle in composed.puzzles] == [FOREIGN_SEED_PLY]


async def test_band_step_covering_the_shortfall_skips_nearest(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Shortfall plus reconstruct slack: enough band candidates that no second statement is needed.
    solver_id, candidates = await _solver_with_foreign_games(
        db_session, games=_DEFAULT_SESSION_SIZE + FOREIGN_FILLER_RECONSTRUCT_SLACK
    )
    spy = _install_draw_spy(monkeypatch, results=[candidates])

    composed = await _compose(db_session, solver_id)

    assert [call["step"].nearest for call in spy.calls] == [False]
    assert len(composed.puzzles) == _DEFAULT_SESSION_SIZE


async def test_empty_foreign_pool_composes_no_foreign_puzzle(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    solver_id = await add_stranger(db_session, label="empty-solver")
    spy = _install_draw_spy(monkeypatch)

    composed = await _compose(db_session, solver_id)

    # Both steps ran and found nothing, never more than the configured steps.
    assert len(spy.calls) == len(FOREIGN_FILLER_DRAW_STEPS)
    assert composed.session_id is None
    assert composed.puzzles == []


async def _seed_first_session_pool(db_session: AsyncSession, *, soft_games: int) -> int:
    """A solver with no own material and one sharp plus `soft_games` soft stranger blunders."""
    solver_id = await add_stranger(db_session, label="fe-solver")
    stranger_id = await add_stranger(db_session, label="fe-stranger")
    await add_rated_games(
        db_session, user_id=solver_id, rating=_STRANGER_RATING, count=_SOLVER_RATED_GAMES
    )
    for _ in range(soft_games):
        await add_foreign_blunder_game(
            db_session, owner_id=stranger_id, owner_rating=_STRANGER_RATING
        )
    await add_foreign_blunder_game(
        db_session,
        owner_id=stranger_id,
        owner_rating=_STRANGER_RATING,
        missed_pv_lines=FOREIGN_SHARP_PV_LINES,
    )
    return solver_id


@pytest.mark.usefixtures("real_foreign_band_draw")
async def test_first_ever_session_opens_on_sharp_foreign_blunder(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    solver_id = await _seed_first_session_pool(db_session, soft_games=_FIRST_SESSION_SOFT_GAMES)
    wanted: list[bool] = []
    real_backfill = train_repository._backfill_foreign_blunders

    async def recording_backfill(*args: Any, **kwargs: Any) -> Any:
        wanted.append(kwargs["want_sharp"])
        return await real_backfill(*args, **kwargs)

    monkeypatch.setattr(train_repository, "_backfill_foreign_blunders", recording_backfill)

    composed = await _compose(db_session, solver_id)

    assert wanted == [True]
    assert len(composed.puzzles) == _DEFAULT_SESSION_SIZE
    # The sharp stranger blunder opens the session: its type is read from the OWNER's blob.
    assert composed.puzzles[0].puzzle_type == "sharp"


# More soft games than the draw keeps, so the sharp one only gets in through the D-16 preference.
_FIRST_SESSION_SOFT_GAMES = 20

# Sharp games the scripted nearest step returns in the WR-01 regression test below.
_NEAREST_SHARP_GAMES = 2


async def _stranger_candidates(
    db_session: AsyncSession,
    *,
    stranger_id: int,
    games: int,
    missed_pv_lines: list[dict[str, object]],
) -> list[ForeignCandidate]:
    """Seed `games` stranger blunders with that blob; returns the rows a draw would yield."""
    return [
        _candidate_of(
            await add_foreign_blunder_game(
                db_session,
                owner_id=stranger_id,
                owner_rating=_STRANGER_RATING,
                missed_pv_lines=missed_pv_lines,
            ),
            missed_pv_lines=missed_pv_lines,
        )
        for _ in range(games)
    ]


@pytest.mark.parametrize(
    "band_soft_games",
    [
        pytest.param(_DEFAULT_SESSION_SIZE, id="band-fills-the-shortfall"),
        pytest.param(_DEFAULT_SESSION_SIZE + 1, id="band-one-short-of-the-slack"),
    ],
)
async def test_first_ever_session_keeps_sharp_pick_from_nearest_step(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch, band_soft_games: int
) -> None:
    """Review WR-01: a sharp pick found only by the nearest step survives the shortfall trim.

    Both draw steps are scripted. The band step returns only soft blunders, enough to cover the
    shortfall but not the reconstruct slack, so the nearest step still runs and returns the sharp
    ones. Before the fix they were appended behind the band picks and cut by the trim, leaving a
    first-ever session without the sharp puzzle D-16 guarantees.
    """
    solver_id = await add_stranger(db_session, label="fn-solver")
    stranger_id = await add_stranger(db_session, label="fn-stranger")
    await add_rated_games(
        db_session, user_id=solver_id, rating=_STRANGER_RATING, count=_SOLVER_RATED_GAMES
    )
    soft = await _stranger_candidates(
        db_session,
        stranger_id=stranger_id,
        games=band_soft_games,
        missed_pv_lines=FOREIGN_SOFT_PV_LINES,
    )
    sharp = await _stranger_candidates(
        db_session,
        stranger_id=stranger_id,
        games=_NEAREST_SHARP_GAMES,
        missed_pv_lines=FOREIGN_SHARP_PV_LINES,
    )
    spy = _install_draw_spy(monkeypatch, results=[soft, sharp])

    composed = await _compose(db_session, solver_id)

    # Band first, nearest only because the band step left the slack unfilled.
    assert [call["step"].nearest for call in spy.calls] == [False, True]
    assert len(composed.puzzles) == _DEFAULT_SESSION_SIZE
    assert composed.puzzles[0].puzzle_type == "sharp"
    # The trim still fills the rest from the band step and keeps one puzzle per game.
    assert [puzzle.puzzle_type for puzzle in composed.puzzles].count("soft") == (
        _DEFAULT_SESSION_SIZE - 1
    )
    served_games = (
        (
            await db_session.execute(
                select(DrillSolve.game_id).where(DrillSolve.session_id == composed.session_id)
            )
        )
        .scalars()
        .all()
    )
    assert len(set(served_games)) == _DEFAULT_SESSION_SIZE
    assert {candidate.game_id for candidate in sharp} & set(served_games)


@pytest.mark.usefixtures("real_foreign_draw")
async def test_later_session_draw_does_not_prefer_sharp(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    solver_id = await _seed_first_session_pool(db_session, soft_games=_FIRST_SESSION_SOFT_GAMES)
    db_session.add(
        DrillSession(
            user_id=solver_id,
            session_date=_NOW.date() - datetime.timedelta(days=10),
            status="expired",
            puzzle_count=1,
            expires_on=_NOW.date() - datetime.timedelta(days=9),
        )
    )
    await db_session.flush()
    wanted: list[bool] = []
    real_backfill = train_repository._backfill_foreign_blunders

    async def recording_backfill(*args: Any, **kwargs: Any) -> Any:
        wanted.append(kwargs["want_sharp"])
        return await real_backfill(*args, **kwargs)

    monkeypatch.setattr(train_repository, "_backfill_foreign_blunders", recording_backfill)

    await _compose(db_session, solver_id)

    assert wanted == [False]


@pytest.mark.usefixtures("real_foreign_draw")
async def test_composition_types_read_foreign_owner_blob(db_session: AsyncSession) -> None:
    stranger_id = await add_stranger(db_session, label="ct-stranger")
    sharp_game = await add_foreign_blunder_game(
        db_session,
        owner_id=stranger_id,
        owner_rating=_STRANGER_RATING,
        missed_pv_lines=FOREIGN_SHARP_PV_LINES,
    )
    soft_game = await add_foreign_blunder_game(
        db_session, owner_id=stranger_id, owner_rating=_STRANGER_RATING
    )

    def puzzle(game_id: int) -> train_repository._ReconstructedPuzzle:
        return train_repository._ReconstructedPuzzle(
            game_id=game_id,
            ply=FOREIGN_SEED_PLY,
            fen="",
            last_move_uci=None,
            side_to_move="white",
            source=DrillSource.FOREIGN_BLUNDER,
            herring_pool_id=None,
        )

    types = await train_repository._composition_puzzle_types(
        db_session, puzzles=[puzzle(sharp_game), puzzle(soft_game)]
    )

    assert types == ["sharp", "soft"]
