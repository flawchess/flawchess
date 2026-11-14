"""Tests for scripts/copy_line_material.py (Phase 254 plan 03, D-09, D-17, D-01, D-12).

DB-backed: games are committed through a session maker bound to the per-run test DB (the script
opens its own short sessions) and removed in teardown, so the global tier-3 eval lottery never sees
a leaked non-guest game. The copy walks every game of the (per-session cloned) test database, so
assertions are made per seeded game, never on database-wide totals that other modules could shift.
"""

from __future__ import annotations

import asyncio
import io
import json
import subprocess
import sys
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from pathlib import Path
from typing import Any

import chess
import chess.pgn
import pytest
import pytest_asyncio
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.user import User
from app.services import maia_engine, maia_flaw_scoring
from app.services.blunder_check_rules import FACEPALM_DRILL_LAMBDA, FACEPALM_SCORE_MIN, MATE_LOSS
from app.services.facepalm_score import FacepalmFacts, facepalm_score
from app.services.maia_flaw_scoring import score_game_flaws_after_apply
from scripts import copy_line_material as copy_tool
from tests.services.maia_fakes import fake_full_policy

# Unique to this module (grep tests/ before changing).
_TEST_USER_ID: int = 254_003
_RUN_STAMP = "20261114T000000Z"
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Scotch with early captures, so the stored line carries material changes (same game as the
# scoring tests): white's ply-4 d4 is the flaw, the ten mainline moves after it the stored line.
_SCOTCH_PGN = (
    "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Qf6 6. Qxf6 Nxf6 7. Nc3 Bb4 "
    "8. Bd2 O-O 9. O-O-O d6 *"
)
_FLAW_PLY = 4
_OPPONENT_PLY = 5
_STORED_LINE_PLIES = 10
# An obviously qualifying stored score, far above FACEPALM_SCORE_MIN.
_HIGH_STORED_SCORE = 0.99
_LOW_STORED_SCORE = 0.0
_PARITY_TAMPER = 0.001
# The depth-3 loss injected into the hook-scored row (the blunderer is down this much).
_INJECTED_LOSS_3 = 4

MakeGame = Callable[..., Awaitable[int]]
LineLosses = tuple[int | None, int | None, int | None, int | None, int | None]


def _losses(values: LineLosses) -> dict[str, int | None]:
    return {f"line_loss_{depth}": v for depth, v in zip((1, 3, 5, 7, 9), values, strict=True)}


def _expected_array(values: LineLosses) -> list[int | None]:
    """The 9-slot signed array the copy must write: odd slots -line_loss_N, even slots NULL."""
    out: list[int | None] = [None] * 9
    for depth, value in zip((1, 3, 5, 7, 9), values, strict=True):
        out[depth - 1] = None if value is None else -value
    return out


def _replayed(pgn: str) -> dict[int, tuple[chess.Board, str]]:
    parsed = chess.pgn.read_game(io.StringIO(pgn))
    assert parsed is not None
    board = parsed.board()
    out: dict[int, tuple[chess.Board, str]] = {}
    for ply, node in enumerate(parsed.mainline()):
        out[ply] = (board.copy(), node.move.uci())
        board.push(node.move)
    return out


@pytest_asyncio.fixture
async def session_factory(test_engine: Any) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def make_game(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[MakeGame, None]:
    """Factory for committed games with flaw rows; deletes everything in teardown."""
    created: list[int] = []
    async with session_factory() as session:
        existing = (
            (await session.execute(select(User).where(User.id == _TEST_USER_ID)))
            .unique()
            .scalar_one_or_none()
        )
        if existing is None:
            session.add(
                User(
                    id=_TEST_USER_ID,
                    email=f"copy-line-material-{_TEST_USER_ID}@example.com",
                    hashed_password="x",
                )
            )
            await session.commit()

    async def _make(
        *,
        flaw_values: dict[int, dict[str, Any]] | None = None,
        pgn: str = _SCOTCH_PGN,
        pv: dict[int, str] | None = None,
    ) -> int:
        """One game; `flaw_values` maps ply -> extra GameFlaw column values (a blunder each)."""
        replayed = _replayed(pgn)
        async with session_factory() as session:
            game = Game(
                user_id=_TEST_USER_ID,
                platform="lichess",
                platform_game_id=f"copy-line-{uuid.uuid4().hex}",
                pgn=pgn,
                result="1-0",
                user_color="white",
                white_rating=1500,
                black_rating=1600,
                time_control_str="300+0",
                time_control_bucket="blitz",
                time_control_seconds=300,
                base_time_seconds=300,
                increment_seconds=0.0,
                rated=True,
                is_computer_game=False,
            )
            session.add(game)
            await session.flush()
            game_id = game.id
            for ply in sorted(replayed):
                session.add(
                    GamePosition(
                        user_id=_TEST_USER_ID,
                        game_id=game_id,
                        ply=ply,
                        eval_cp=20,
                        eval_mate=None,
                        clock_seconds=None,
                        phase=1,
                        full_hash=ply,
                        white_hash=ply,
                        black_hash=ply,
                        endgame_class=None,
                        move_san=None,
                        pv=(pv or {}).get(ply),
                    )
                )
            await session.flush()
            for ply, values in (flaw_values or {}).items():
                session.add(
                    GameFlaw(
                        user_id=_TEST_USER_ID,
                        game_id=game_id,
                        ply=ply,
                        severity=2,
                        tempo=None,
                        phase=1,
                        is_miss=False,
                        is_lucky=False,
                        is_reversed=False,
                        is_squandered=False,
                        fen=replayed[ply][0].board_fen(),
                        **values,
                    )
                )
            await session.commit()
        created.append(game_id)
        return game_id

    yield _make

    async with session_factory() as session:
        if created:
            await session.execute(delete(Game).where(Game.id.in_(created)))
        await session.execute(delete(User).where(User.id == _TEST_USER_ID))
        await session.commit()


async def _arrays(
    maker: async_sessionmaker[AsyncSession], game_id: int
) -> dict[int, list[int | None] | None]:
    async with maker() as session:
        rows = (
            await session.execute(
                select(GameFlaw.ply, GameFlaw.played_line_material).where(
                    GameFlaw.game_id == game_id
                )
            )
        ).all()
    return {ply: array for ply, array in rows}


async def _copy(maker: async_sessionmaker[AsyncSession], tmp_path: Path, **kwargs: Any) -> Any:
    kwargs.setdefault("throttle_ms", 0)
    return await copy_tool.run_copy(
        maker, db="dev", report_dir=tmp_path, run_stamp=_RUN_STAMP, **kwargs
    )


# ---------------------------------------------------------------------------
# Copy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_copy_flips_sign_into_odd_slots(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """Positive, negative, NULL-at-deep-depths and mate-capped line_loss values become
    [-l1, NULL, -l3, NULL, -l5, NULL, -l7, NULL, -l9] and satisfy the 9-slot shape CHECK."""
    cases: dict[int, LineLosses] = {
        2: (4, -2, 3, 0, 1),
        3: (1, 2, None, None, None),
        6: (None, None, None, None, 7),
        8: (MATE_LOSS, MATE_LOSS, MATE_LOSS, MATE_LOSS, MATE_LOSS),
    }
    game_id = await make_game(
        flaw_values={ply: _losses(v) | {"line_mate_ply": 1} for ply, v in cases.items()}
    )

    report = await _copy(session_factory, tmp_path)

    assert report.rows_copied >= len(cases)
    arrays = await _arrays(session_factory, game_id)
    for ply, values in cases.items():
        assert arrays[ply] == _expected_array(values), ply
    async with session_factory() as session:
        shapes = (
            await session.execute(
                text(
                    "SELECT cardinality(played_line_material), array_lower(played_line_material, 1)"
                    " FROM game_flaws WHERE game_id = :g"
                ),
                {"g": game_id},
            )
        ).all()
    assert set(shapes) == {(9, 1)}


@pytest.mark.asyncio
async def test_copy_skips_rows_without_values_and_rows_already_written(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """All-NULL line_loss rows stay NULL; a row whose array the hook already wrote keeps it, even
    when its legacy line_loss values differ."""
    hook_array: list[int | None] = [9, 8, 7, 6, 5, 4, 3, 2, 1]
    game_id = await make_game(
        flaw_values={
            2: _losses((None, None, None, None, None)),
            5: _losses((3, 3, 3, 3, 3)) | {"played_line_material": hook_array},
            8: _losses((2, None, None, None, None)),
        }
    )

    await _copy(session_factory, tmp_path)

    arrays = await _arrays(session_factory, game_id)
    assert arrays[2] is None
    assert arrays[5] == hook_array
    assert arrays[8] == _expected_array((2, None, None, None, None))


@pytest.mark.asyncio
async def test_copy_is_idempotent_and_resumable(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """A second full run updates 0 rows; --start-after past a game skips it, below it copies it."""
    values: LineLosses = (1, 2, 3, 4, 5)
    first = await make_game(flaw_values={2: _losses(values)})
    second = await make_game(flaw_values={2: _losses(values)})
    third = await make_game(flaw_values={2: _losses(values)})
    # Start after the second game: the first and second are skipped, the third is copied.
    await _copy(session_factory, tmp_path, start_after=second, batch_games=1)
    assert (await _arrays(session_factory, first))[2] is None
    assert (await _arrays(session_factory, second))[2] is None
    assert (await _arrays(session_factory, third))[2] == _expected_array(values)

    resumed = await _copy(session_factory, tmp_path)
    assert resumed.rows_copied >= 2
    assert (await _arrays(session_factory, first))[2] == _expected_array(values)
    assert (await _arrays(session_factory, second))[2] == _expected_array(values)

    again = await _copy(session_factory, tmp_path)
    assert again.rows_copied == 0
    assert (await _arrays(session_factory, first))[2] == _expected_array(values)


@pytest.mark.asyncio
async def test_copy_batches_slices_stops_and_reports(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--limit-batches slices the walk, a stop request ends it after the current batch, and the
    JSON report carries the cursor and totals."""
    values: LineLosses = (1, None, None, None, None)
    game_ids = [await make_game(flaw_values={2: _losses(values)}) for _ in range(3)]

    sliced = await _copy(session_factory, tmp_path, batch_games=1, limit_batches=1)
    assert sliced.batches == 1
    assert sliced.games_scanned == 1

    async def _stop_during_throttle(_seconds: float) -> None:
        monkeypatch.setattr(copy_tool, "_stop_requested", True)

    monkeypatch.setattr(copy_tool.asyncio, "sleep", _stop_during_throttle)
    stopped = await _copy(
        session_factory, tmp_path, batch_games=1, throttle_ms=1, start_after=sliced.cursor
    )
    assert stopped.stopped_early
    assert stopped.batches == 1
    monkeypatch.undo()

    finished = await _copy(session_factory, tmp_path, batch_games=1)
    assert not finished.stopped_early
    for game_id in game_ids:
        assert (await _arrays(session_factory, game_id))[2] == _expected_array(values)
    saved = json.loads((tmp_path / f"copy-line-material-{_RUN_STAMP}.json").read_text())
    assert saved["cursor"] == finished.cursor
    assert saved["rows_copied"] == finished.rows_copied
    assert saved["dry_run"] is False
    assert saved["db"] == "dev"


@pytest.mark.asyncio
async def test_dry_run_counts_and_writes_nothing(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    game_id = await make_game(
        flaw_values={2: _losses((1, 2, 3, 4, 5)), 5: _losses((None, None, None, None, None))}
    )

    report = await _copy(session_factory, tmp_path, dry_run=True)

    assert report.dry_run
    assert report.rows_copied >= 1
    assert all(array is None for array in (await _arrays(session_factory, game_id)).values())


# ---------------------------------------------------------------------------
# Status and parity
# ---------------------------------------------------------------------------


async def _hook_scored_game_then_reset_to_pre_r1(
    maker: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> int:
    """A user blunder scored by the real post-commit hook, then stripped back to a pre-R1 row.

    The hook (plan 16) writes the stored score AND the new fact columns. Clearing the new fact
    columns leaves what a prod row written before R1 holds: the legacy line_loss_* columns, the
    mate ply, the spread, the played probability and the stored score. The copy must rebuild the
    array from the legacy columns alone for the expression to reproduce the stored score.
    """
    monkeypatch.setattr(maia_engine, "_session", object())
    monkeypatch.setattr(maia_flaw_scoring, "full_policy", fake_full_policy)
    pv = " ".join(
        _replayed(_SCOTCH_PGN)[ply][1]
        for ply in range(_FLAW_PLY + 1, _FLAW_PLY + 1 + _STORED_LINE_PLIES)
    )
    game_id = await make_game(
        flaw_values={_FLAW_PLY: {}, _OPPONENT_PLY: {}}, pv={_FLAW_PLY + 1: pv}
    )
    assert await score_game_flaws_after_apply(maker, game_id, targets=None, source="backfill")
    async with maker() as session:
        played_prob, spread = (
            await session.execute(
                select(GameFlaw.maia_played_prob, GameFlaw.maia_reply_spread).where(
                    GameFlaw.game_id == game_id, GameFlaw.ply == _FLAW_PLY
                )
            )
        ).one()
        # The mainline continuation nets 0 material at depth 3, which would hide a sign error in
        # the copy: give the row a real depth-3 loss and the stored score that goes with it.
        stored_score = facepalm_score(
            FacepalmFacts(
                played_prob=played_prob,
                reply_spread=spread,
                played_3=-_INJECTED_LOSS_3,
                mate_ply=None,
            ),
            lam=FACEPALM_DRILL_LAMBDA,
        )
        assert stored_score is not None
        await session.execute(
            update(GameFlaw)
            .where(GameFlaw.game_id == game_id, GameFlaw.ply == _FLAW_PLY)
            .values(
                line_loss_3=_INJECTED_LOSS_3,
                facepalm_score=stored_score,
                played_line_material=None,
                best_line_material=None,
                best_line_mate_ply=None,
            )
        )
        # The opponent's blunder carries a stored score that is NOT a user blunder's: out of scope.
        await session.execute(
            update(GameFlaw)
            .where(GameFlaw.game_id == game_id, GameFlaw.ply == _OPPONENT_PLY)
            .values(facepalm_score=_HIGH_STORED_SCORE)
        )
        await session.commit()
    return game_id


@pytest.mark.asyncio
async def test_status_and_parity(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    test_engine: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--status counts the rows still to copy and the rows holding an array; after the copy,
    --parity over the hook-scored row reports a difference below PARITY_MAX_ABS_DIFF and no row on
    a different side of FACEPALM_SCORE_MIN (the opponent's blunder is out of scope)."""
    game_id = await _hook_scored_game_then_reset_to_pre_r1(session_factory, make_game, monkeypatch)
    arrays = await _arrays(session_factory, game_id)
    assert arrays[_FLAW_PLY] is None

    async with session_factory() as session:
        before = await copy_tool.fetch_copy_status(session)
    assert before["copy_pending_rows"] >= 1

    await _copy(session_factory, tmp_path)

    async with session_factory() as session:
        after = await copy_tool.fetch_copy_status(session)
    assert after["copy_pending_rows"] == 0
    assert after["copied_rows"] >= before["copied_rows"] + 1
    assert (await _arrays(session_factory, game_id))[_FLAW_PLY] is not None
    async with session_factory() as session:
        parity = await copy_tool.fetch_parity(session)
    assert parity["both_scored"] >= 1
    assert parity["stored_scored"] >= parity["both_scored"]
    assert parity["expression_scored"] >= parity["both_scored"]
    assert parity["max_abs_diff"] is not None
    assert parity["max_abs_diff"] < copy_tool.PARITY_MAX_ABS_DIFF
    assert parity["cut_side_mismatches"] == 0
    assert copy_tool.parity_ok(parity)

    # The CLI prints the same keys from a read-only engine and exits 0.
    test_url = test_engine.url.render_as_string(hide_password=False)
    monkeypatch.setattr(copy_tool, "db_url_for_target", lambda _target: test_url)
    assert await asyncio.to_thread(copy_tool.main, ["--db", "dev", "--status"]) == copy_tool.EXIT_OK
    status_line = capsys.readouterr().out.strip().splitlines()[-1]
    assert status_line.startswith("copy_pending_rows=0 copied_rows=")
    assert await asyncio.to_thread(copy_tool.main, ["--db", "dev", "--parity"]) == copy_tool.EXIT_OK
    parity_line = capsys.readouterr().out.strip().splitlines()[-1]
    assert parity_line.startswith("stored_scored=")
    assert " cut_side_mismatches=0" in parity_line


@pytest.mark.asyncio
async def test_parity_flags_a_divergent_score_and_a_cut_side_mismatch(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    test_engine: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stored score that differs from the expression is reported, fails the check and exits
    non-zero; one that crosses FACEPALM_SCORE_MIN counts as a cut-side mismatch."""
    game_id = await _hook_scored_game_then_reset_to_pre_r1(session_factory, make_game, monkeypatch)
    await _copy(session_factory, tmp_path)
    async with session_factory() as session:
        stored = (
            await session.execute(
                select(GameFlaw.facepalm_score).where(
                    GameFlaw.game_id == game_id, GameFlaw.ply == _FLAW_PLY
                )
            )
        ).scalar_one()
        assert stored is not None
        # The value on the other side of the cut from the (matching) expression score.
        crossing = _LOW_STORED_SCORE if stored >= FACEPALM_SCORE_MIN else _HIGH_STORED_SCORE
        # A small divergence first: above the tolerance, still on the same side of the cut.
        await session.execute(
            update(GameFlaw)
            .where(GameFlaw.game_id == game_id, GameFlaw.ply == _FLAW_PLY)
            .values(facepalm_score=stored + _PARITY_TAMPER)
        )
        await session.commit()
    async with session_factory() as session:
        small = await copy_tool.fetch_parity(session)
    assert small["max_abs_diff"] is not None
    assert small["max_abs_diff"] > copy_tool.PARITY_MAX_ABS_DIFF
    assert not copy_tool.parity_ok(small)

    async with session_factory() as session:
        await session.execute(
            update(GameFlaw)
            .where(GameFlaw.game_id == game_id, GameFlaw.ply == _FLAW_PLY)
            .values(facepalm_score=crossing)
        )
        await session.commit()
    async with session_factory() as session:
        crossed = await copy_tool.fetch_parity(session)
    assert crossed["cut_side_mismatches"] >= 1

    test_url = test_engine.url.render_as_string(hide_password=False)
    monkeypatch.setattr(copy_tool, "db_url_for_target", lambda _target: test_url)
    assert (
        await asyncio.to_thread(copy_tool.main, ["--db", "dev", "--parity"])
        == copy_tool.EXIT_PARITY_FAILED
    )


@pytest.mark.asyncio
async def test_status_and_parity_transactions_are_read_only(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Both checks open their transaction read-only, so they cannot write even by accident."""
    for check in (copy_tool.fetch_copy_status, copy_tool.fetch_parity):
        async with session_factory() as session:
            await check(session)
            with pytest.raises(DBAPIError, match="read-only"):
                await session.execute(text("UPDATE game_flaws SET ply = ply WHERE false"))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_help_lists_the_operator_flags() -> None:
    proc = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "scripts" / "copy_line_material.py"), "--help"],
        capture_output=True,
        text=True,
        check=False,
        cwd=_REPO_ROOT,
    )
    assert proc.returncode == 0
    for flag in ("--start-after", "--status", "--parity", "--limit-batches", "--dry-run"):
        assert flag in proc.stdout


def test_cli_defaults_and_validation(capsys: pytest.CaptureFixture[str]) -> None:
    args = copy_tool._parse_args(["--db", "dev"])
    assert args.batch_games == copy_tool.DEFAULT_COPY_BATCH_GAMES
    assert args.throttle_ms == copy_tool.DEFAULT_COPY_THROTTLE_MS
    assert args.start_after == 0
    with pytest.raises(SystemExit):
        copy_tool._parse_args(["--db", "dev", "--status", "--parity"])
    with pytest.raises(SystemExit):
        copy_tool._parse_args(["--db", "dev", "--batch-games", "0"])
    with pytest.raises(SystemExit):
        copy_tool._parse_args(["--db", "nowhere"])
    capsys.readouterr()
