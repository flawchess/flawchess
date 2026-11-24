"""Router tests for the foreign-blunder reveal and wire (Phase 263 plan 06: D-09, D-10, D-20, D-21).

Coverage:
- test_foreign_puzzle_wire_has_no_game_id         : compose and resume carry game_id null (D-10, D-21)
- test_reveal_foreign_reports_owner_game_move_and_type : the owner's move (SAN, UCI) and the type read
                                                    off the owner's blob, no tactic-lines pointer (D-20)
- test_reveal_foreign_game_info_names_nobody      : game_info holds neutral facts only (D-21)
- test_reveal_foreign_played_at_is_date_only      : game_info.played_at is the date, no time of day
- test_reveal_foreign_deleted_game_404_and_outcome_kept : the stranger deleting the game makes the
                                                    reveal 404 while the solve's outcome stays (D-09)
- test_reveal_foreign_facepalm_reads_owner_flaw   : the "???" flag reads the stranger's flaw row

Data isolation: the foreign draw samples every other user's games across the database, so each test
requests `real_foreign_band_draw` (the band step alone: the nearest-first step has no distance cap
and would draw any committed game left in the database, review IN-07), commits a solver (level
2600 via rated games at raw 2700, where no other test seeds) plus one stranger's game, and deletes
its sessions, games and the stranger user in `finally`.
"""

from __future__ import annotations

import datetime
import json
import uuid
from dataclasses import dataclass

import httpx
import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.main import app
from app.models.drill_solve import DrillSource
from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.user import User
from app.services.blunder_check_rules import FACEPALM_LIBRARY_LAMBDA
from app.services.tactic_detector import TacticMotifInt
from tests.blunder_check_seed import SEED_PGN, _replay_boards, delete_games
from tests.facepalm_seed import facepalm_fact_columns
from tests.routers.test_train import (
    ENDPOINT,
    _delete_sessions,
    _register_and_login,
    _reveal,
    _solve,
)
from tests.train_foreign_seed import (
    FOREIGN_KEY_UCI,
    FOREIGN_SEED_PLY,
    FOREIGN_SHARP_PV_LINES,
    add_foreign_blunder_game,
    add_rated_games,
    add_stranger,
    delete_game_row,
)

# Raw rating where no other test seeds games (the pinned Elo clamps at 2600).
_STRANGER_RATING = 2700
_SOLVER_RATED_GAMES = 3
# A facepalm score far above the 0.7 cut.
_FACEPALM_HIGH_SCORE = 0.95
_FORBIDDEN_OWNER_KEYS = ("user", "name", "email", "platform_game_id", "url")
# A start time with every time-of-day part non-zero, and the UTC midnight of its date.
_PLAYED_AT_WITH_TIME = datetime.datetime(2026, 6, 1, 17, 42, 13, 250_000, tzinfo=datetime.UTC)
_PLAYED_ON = datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC)


@dataclass
class _Scene:
    """A committed solver with no own material and one stranger's servable blunder."""

    solver_id: int
    token: str
    stranger_id: int
    stranger_email: str
    foreign_game_id: int
    solver_game_ids: list[int]
    session_ids: list[int]


async def _seed_scene(test_engine) -> _Scene:
    solver_id, token = await _register_and_login(f"fr-solver-{uuid.uuid4().hex[:8]}@example.com")
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session, session.begin():
        stranger_id = await add_stranger(session, label="fr-stranger")
        solver_game_ids = await add_rated_games(
            session, user_id=solver_id, rating=_STRANGER_RATING, count=_SOLVER_RATED_GAMES
        )
        foreign_game_id = await add_foreign_blunder_game(
            session,
            owner_id=stranger_id,
            owner_rating=_STRANGER_RATING,
            missed_pv_lines=FOREIGN_SHARP_PV_LINES,
        )
        stranger = (
            (await session.execute(select(User).where(User.id == stranger_id)))
            .unique()
            .scalar_one()
        )
        stranger_email: str = stranger.email
    return _Scene(
        solver_id=solver_id,
        token=token,
        stranger_id=stranger_id,
        stranger_email=stranger_email,
        foreign_game_id=foreign_game_id,
        solver_game_ids=solver_game_ids,
        session_ids=[],
    )


async def _cleanup(test_engine, scene: _Scene) -> None:
    await _delete_sessions(test_engine, scene.session_ids)
    await delete_games(test_engine, [*scene.solver_game_ids, scene.foreign_game_id])
    maker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with maker() as session, session.begin():
        await session.execute(delete(User).where(User.id == scene.stranger_id))


async def _compose(token: str) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        return await client.post(ENDPOINT, headers={"Authorization": f"Bearer {token}"})


async def _compose_and_solve(scene: _Scene) -> dict[str, object]:
    """Compose the session (one foreign puzzle) and solve it; returns the compose body."""
    resp = await _compose(scene.token)
    assert resp.status_code == 200
    body: dict[str, object] = resp.json()
    scene.session_ids.append(int(str(body["session_id"])))
    solved = await _solve(
        scene.token,
        scene.session_ids[-1],
        0,
        guess="critical",
        played_move=FOREIGN_KEY_UCI,
        move_quality="good",
    )
    assert solved.status_code == 200
    return body


@pytest.mark.usefixtures("real_foreign_band_draw")
async def test_foreign_puzzle_wire_has_no_game_id(test_engine) -> None:
    scene = await _seed_scene(test_engine)
    try:
        first = await _compose(scene.token)
        assert first.status_code == 200
        body = first.json()
        scene.session_ids.append(int(body["session_id"]))
        assert len(body["puzzles"]) == 1
        assert body["puzzles"][0]["game_id"] is None

        # Resume (a second compose before the session is solved): same session, still no game id.
        resumed = await _compose(scene.token)
        assert resumed.status_code == 200
        assert resumed.json()["session_id"] == body["session_id"]
        assert resumed.json()["puzzles"][0]["game_id"] is None
    finally:
        await _cleanup(test_engine, scene)


@pytest.mark.usefixtures("real_foreign_band_draw")
async def test_reveal_foreign_reports_owner_game_move_and_type(test_engine) -> None:
    scene = await _seed_scene(test_engine)
    try:
        # T-263-18: the stranger's flaw carries a tactic motif, which is all an OWN puzzle needs
        # for has_tactic_lines to be True. Without it the assertion below would pass even with
        # the foreign gate removed.
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as session, session.begin():
            await session.execute(
                update(GameFlaw)
                .where(GameFlaw.game_id == scene.foreign_game_id)
                .values(missed_tactic_motif=int(TacticMotifInt.FORK))
            )
        await _compose_and_solve(scene)

        resp = await _reveal(scene.token, scene.session_ids[-1], 0)

        assert resp.status_code == 200
        body = resp.json()
        boards, moves = _replay_boards(SEED_PGN)
        expected_san = boards[FOREIGN_SEED_PLY].san(moves[FOREIGN_SEED_PLY])
        assert body["source"] == "foreign_blunder"
        assert body["played_in_game_san"] == expected_san
        assert body["played_in_game_move_uci"] == moves[FOREIGN_SEED_PLY].uci()
        # The type is read off the OWNER's blob (the solver holds no flaw rows at all).
        assert body["puzzle_type"] == "sharp"
        # No pointer at the tactic-lines endpoint although the owner's flaw has a motif.
        assert body["has_tactic_lines"] is False
    finally:
        await _cleanup(test_engine, scene)


def _assert_no_owner_identity(value: object) -> None:
    """No key anywhere in the parsed body names the owner (user, name, email, url, platform id)."""
    if isinstance(value, dict):
        for key, inner in value.items():
            assert not any(part in key for part in _FORBIDDEN_OWNER_KEYS), key
            _assert_no_owner_identity(inner)
    elif isinstance(value, list):
        for inner in value:
            _assert_no_owner_identity(inner)


@pytest.mark.usefixtures("real_foreign_band_draw")
async def test_reveal_foreign_game_info_names_nobody(test_engine) -> None:
    scene = await _seed_scene(test_engine)
    try:
        await _compose_and_solve(scene)

        resp = await _reveal(scene.token, scene.session_ids[-1], 0)

        assert resp.status_code == 200
        body = resp.json()
        assert body["game_id"] is None
        assert set(body["game_info"].keys()) == {
            "time_control_str",
            "time_control_bucket",
            "played_at",
            "mover_rating",
        }
        assert body["game_info"]["mover_rating"] == _STRANGER_RATING
        assert body["game_info"]["time_control_str"] == "300+0"
        assert body["game_info"]["time_control_bucket"] == "blitz"
        _assert_no_owner_identity(body)
        text = json.dumps(body)
        assert scene.stranger_email not in text
        assert scene.stranger_email.split("@")[0] not in text
        assert "fr-stranger" not in text
        assert set(body.keys()) == {
            "game_id",
            "ply",
            "fen",
            "played_in_game_san",
            "played_in_game_move_uci",
            "puzzle_type",
            "source",
            "has_tactic_lines",
            "game_move_facepalm",
            "game_info",
        }
    finally:
        await _cleanup(test_engine, scene)


@pytest.mark.usefixtures("real_foreign_band_draw")
async def test_reveal_foreign_played_at_is_date_only(test_engine) -> None:
    """Review WR-02 (D-21): the stranger's game is dated, never timed to the second."""
    scene = await _seed_scene(test_engine)
    try:
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as session, session.begin():
            await session.execute(
                update(Game)
                .where(Game.id == scene.foreign_game_id)
                .values(played_at=_PLAYED_AT_WITH_TIME)
            )
        await _compose_and_solve(scene)

        resp = await _reveal(scene.token, scene.session_ids[-1], 0)

        assert resp.status_code == 200
        played_at = datetime.datetime.fromisoformat(resp.json()["game_info"]["played_at"])
        # Still a timezone-aware datetime on the wire (shared GameInfo schema), date only.
        assert played_at.tzinfo is not None
        assert played_at == _PLAYED_ON
        assert played_at.timetz() == datetime.time(0, 0, tzinfo=datetime.UTC)
    finally:
        await _cleanup(test_engine, scene)


@pytest.mark.usefixtures("real_foreign_band_draw")
async def test_reveal_foreign_deleted_game_404_and_outcome_kept(test_engine) -> None:
    scene = await _seed_scene(test_engine)
    try:
        await _compose_and_solve(scene)
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as session, session.begin():
            await delete_game_row(session, game_id=scene.foreign_game_id)

        resp = await _reveal(scene.token, scene.session_ids[-1], 0)
        assert resp.status_code == 404

        # The solve's outcome stays: the completed session still lists it in solved_results.
        again = await _compose(scene.token)
        assert again.status_code == 200
        solved_results = again.json()["solved_results"]
        assert [r["source"] for r in solved_results] == ["foreign_blunder"]
        assert solved_results[0]["correct_guess"] is True
        assert int(DrillSource.FOREIGN_BLUNDER) == 3
    finally:
        await _cleanup(test_engine, scene)


@pytest.mark.usefixtures("real_foreign_band_draw")
async def test_reveal_foreign_facepalm_reads_owner_flaw(test_engine) -> None:
    scene = await _seed_scene(test_engine)
    try:
        maker = async_sessionmaker(test_engine, expire_on_commit=False)
        async with maker() as session, session.begin():
            await session.execute(
                update(GameFlaw)
                .where(GameFlaw.game_id == scene.foreign_game_id)
                .values(**facepalm_fact_columns(_FACEPALM_HIGH_SCORE, lam=FACEPALM_LIBRARY_LAMBDA))
            )
        await _compose_and_solve(scene)

        resp = await _reveal(scene.token, scene.session_ids[-1], 0)

        assert resp.status_code == 200
        assert resp.json()["game_move_facepalm"] is True
    finally:
        await _cleanup(test_engine, scene)
