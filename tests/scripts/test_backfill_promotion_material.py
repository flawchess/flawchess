"""Tests for scripts/backfill_promotion_material.py (Phase 262 plan 04, D-06, D-07).

DB-backed: games are committed through a session maker bound to the per-run test DB (the script
opens its own short sessions) and removed in teardown, so the global tier-3 eval lottery never
sees a leaked non-guest game. Every run is scoped by ``user_id``. Expected values are computed
with the app function (``facepalm_material_inputs``), never typed by hand, except the tracer's
pinned pair (loss 5.0, missed 0.0) from plan 01.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import chess
import chess.pgn
import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.user import User
from app.services.facepalm_inputs import MaterialInputs, facepalm_material_inputs
from scripts import backfill_promotion_material as promo

# Unique to this module (grep tests/ before changing).
_TEST_USER_ID: int = 262_001

# The stored scalars are REAL (float32): compare them with a relative tolerance.
_REAL_REL_TOL = 1e-6

# Opponent pawn on c2 promotes next move; the blunderer's rook goes b1b3 and the queen stays.
_PROMO_FEN = "6k1/8/8/8/8/8/2p5/1R4K1 w - - 0 1"
_PROMO_BLUNDER = "b1b3"
_PROMO_REFUTATION = "c2c1q g1h2 g8f7 b3b7 f7e6 b7b6 e6d5 b6b5 d5c4 b5b8"
# Same position, a blunder with no promotion anywhere in its lines.
_PLAIN_BLUNDER = "g1h2"
_PLAIN_REFUTATION = "g8f7 h2g3"
# D-03 position: white promotes on a8 and the rook takes the new queen.
_PLAYED_PROMO_FEN = "1r4k1/P7/8/8/8/8/8/6K1 w - - 0 1"
_PLAYED_PROMO_MOVES = ("a7a8q", "b8a8")
# Quiet start with no material on either line: a plain blunder with a short line.
_START_FEN = chess.STARTING_FEN

# A stored pair that no replay of the fixtures can produce.
_WRONG_PAIR = (3.0, 1.0)

MakeGame = Callable[..., Awaitable[int]]
Pair = tuple[float | None, float | None]


@pytest_asyncio.fixture
async def session_factory(test_engine: Any) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(test_engine, expire_on_commit=False)


def _pgn(start_fen: str, moves: Sequence[str]) -> str:
    """A PGN with SetUp / FEN headers for a non-standard start, built from UCI moves."""
    board = chess.Board(start_fen)
    game = chess.pgn.Game()
    game.setup(board)
    node: chess.pgn.GameNode = game
    for uci in moves:
        move = chess.Move.from_uci(uci)
        node = node.add_variation(move)
    return str(game)


def _san_by_ply(start_fen: str, moves: Sequence[str]) -> dict[int, str]:
    board = chess.Board(start_fen)
    out: dict[int, str] = {}
    for ply, uci in enumerate(moves):
        move = chess.Move.from_uci(uci)
        out[ply] = board.san(move)
        board.push(move)
    return out


def _fen_before(start_fen: str, moves: Sequence[str], ply: int) -> str:
    board = chess.Board(start_fen)
    for uci in moves[:ply]:
        board.push(chess.Move.from_uci(uci))
    return board.board_fen()


@pytest_asyncio.fixture
async def make_game(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[MakeGame, None]:
    """Factory for committed games with positions and flaw rows; cleans up in teardown."""
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
                    email=f"backfill-promotion-{_TEST_USER_ID}@example.com",
                    hashed_password="x",
                )
            )
            await session.commit()

    async def _make(
        *,
        start_fen: str = _PROMO_FEN,
        moves: Sequence[str] = (_PROMO_BLUNDER, "c2c1q"),
        flaws: Mapping[int, Pair] | None = None,
        positions: Mapping[int, Mapping[str, Any]] | None = None,
        stamped: bool = True,
        severity: int = 2,
    ) -> int:
        """`moves` are UCI (a promotion carries its letter); `flaws` is ply -> stored pair.

        Defaults: the promotion tracer, one blunder at ply 0 with the stored pair (0.0, 0.0).
        `positions` maps a ply to extra GamePosition fields (pv, best_move, move_san).
        """
        flaw_pairs = {0: (0.0, 0.0)} if flaws is None else dict(flaws)
        sans = _san_by_ply(start_fen, moves)
        async with session_factory() as session:
            game = Game(
                user_id=_TEST_USER_ID,
                platform="lichess",
                platform_game_id=f"backfill-promotion-{uuid.uuid4().hex}",
                pgn=_pgn(start_fen, moves),
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
                facepalm_line_completed_at=func.now() if stamped else None,
            )
            session.add(game)
            await session.flush()
            game_id = game.id
            for ply in range(len(moves)):
                fields: dict[str, Any] = {"move_san": sans[ply]}
                fields.update((positions or {}).get(ply, {}))
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
                        **fields,
                    )
                )
            await session.flush()
            for ply, (loss, missed) in flaw_pairs.items():
                session.add(
                    GameFlaw(
                        user_id=_TEST_USER_ID,
                        game_id=game_id,
                        ply=ply,
                        severity=severity,
                        tempo=None,
                        phase=1,
                        is_miss=False,
                        is_lucky=False,
                        is_reversed=False,
                        is_squandered=False,
                        fen=_fen_before(start_fen, moves, ply),
                        material_loss=loss,
                        material_missed=missed,
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


async def _stored(
    maker: async_sessionmaker[AsyncSession], game_id: int, ply: int = 0
) -> tuple[float | None, float | None]:
    async with maker() as session:
        row = (
            await session.execute(
                select(GameFlaw.material_loss, GameFlaw.material_missed).where(
                    GameFlaw.game_id == game_id, GameFlaw.ply == ply
                )
            )
        ).one()
    return row[0], row[1]


async def _run(
    maker: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    *,
    dry_run: bool = False,
    undo: Path | None = None,
    **kwargs: Any,
) -> promo.PassReport:
    if not dry_run and undo is None:
        undo = tmp_path / "undo.tsv"
    return await promo.run_pass(
        db="dev",
        dry_run=dry_run,
        user_id=_TEST_USER_ID,
        report_dir=tmp_path,
        undo_log=undo,
        session_maker=maker,
        **kwargs,
    )


def _expected(
    start_fen: str, played: str, refutation: str | None, best: str | None
) -> MaterialInputs:
    """The app's pair for a fixture, in the 4-byte form the column stores."""
    inputs = facepalm_material_inputs(chess.Board(start_fen), played, refutation, best)
    return MaterialInputs(promo.as_real(inputs.loss), promo.as_real(inputs.missed))


def _assert_pair(actual: Pair, expected: MaterialInputs) -> None:
    for got, want in zip(actual, expected, strict=True):
        if want is None:
            assert got is None
        else:
            assert got is not None
            assert got == pytest.approx(want, rel=_REAL_REL_TOL)


_TRACER_POSITIONS: dict[int, dict[str, Any]] = {1: {"pv": _PROMO_REFUTATION}}


# ---------------------------------------------------------------------------
# Tracer: one refutation-line promotion row, real run, dry run, re-run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_real_run_rewrites_the_row_and_logs_the_old_and_new_pair(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    game_id = await make_game(positions=_TRACER_POSITIONS)

    report = await _run(session_factory, tmp_path)

    assert (report.candidates, report.changed, report.guard_misses) == (1, 1, 0)
    loss, missed = await _stored(session_factory, game_id)
    assert loss == pytest.approx(5.0, rel=_REAL_REL_TOL)
    assert missed == pytest.approx(0.0, abs=_REAL_REL_TOL)
    expected = _expected(_PROMO_FEN, _PROMO_BLUNDER, _PROMO_REFUTATION, None)
    _assert_pair((loss, missed), expected)
    lines = (tmp_path / "undo.tsv").read_text().splitlines()
    assert lines[0] == promo.UNDO_LOG_HEADER
    assert len(lines) == 2
    user, game, ply, old_loss, old_missed, new_loss, new_missed = lines[1].split("\t")
    assert (int(user), int(game), int(ply)) == (_TEST_USER_ID, game_id, 0)
    assert (float(old_loss), float(old_missed)) == (0.0, 0.0)
    assert (float(new_loss), float(new_missed)) == (5.0, 0.0)
    assert report.report_path is not None and report.report_path.exists()


@pytest.mark.asyncio
async def test_dry_run_writes_nothing_and_creates_no_undo_log(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    game_id = await make_game(positions=_TRACER_POSITIONS)

    report = await _run(session_factory, tmp_path, dry_run=True)

    assert (report.candidates, report.changed) == (1, 1)
    assert await _stored(session_factory, game_id) == (0.0, 0.0)
    assert report.undo_log is None
    assert not list(tmp_path.glob("*.tsv"))
    assert report.report_path is not None and "dry" in report.report_path.name


@pytest.mark.asyncio
async def test_second_real_run_changes_nothing(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    await make_game(positions=_TRACER_POSITIONS)
    first = await _run(session_factory, tmp_path)
    second = await _run(session_factory, tmp_path, undo=tmp_path / "undo-second.tsv")

    assert first.changed == 1
    assert (second.candidates, second.changed) == (1, 0)


# ---------------------------------------------------------------------------
# Token places: best line, best move, played move
# ---------------------------------------------------------------------------

_BEST_LINE_MOVES = ("g1h1", "g8f7")
_BEST_LINE_PV = "a7a8q b8a8"
_BEST_LINE_REFUTATION = "g8f7 h1g2"


async def _assert_rewritten_to_app_pair(
    maker: async_sessionmaker[AsyncSession],
    game_id: int,
    expected: MaterialInputs,
    *,
    ply: int = 0,
) -> None:
    """The row now holds the app's pair, and the test is not vacuous (the old pair differed)."""
    assert (expected.loss, expected.missed) != _WRONG_PAIR
    _assert_pair(await _stored(maker, game_id, ply), expected)


@pytest.mark.asyncio
async def test_promotion_in_the_best_line_is_a_candidate(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """p0.pv carries the promotion, the refutation line has none."""
    game_id = await make_game(
        start_fen=_PLAYED_PROMO_FEN,
        moves=_BEST_LINE_MOVES,
        flaws={0: _WRONG_PAIR},
        positions={0: {"pv": _BEST_LINE_PV}, 1: {"pv": _BEST_LINE_REFUTATION}},
    )

    report = await _run(session_factory, tmp_path)

    assert (report.candidates, report.changed) == (1, 1)
    expected = _expected(_PLAYED_PROMO_FEN, "g1h1", _BEST_LINE_REFUTATION, _BEST_LINE_PV)
    await _assert_rewritten_to_app_pair(session_factory, game_id, expected)


@pytest.mark.asyncio
async def test_promotion_as_the_best_move_with_a_null_best_line_is_a_candidate(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """p0.best_move is the promotion and p0.pv is NULL."""
    game_id = await make_game(
        start_fen=_PLAYED_PROMO_FEN,
        moves=_BEST_LINE_MOVES,
        flaws={0: _WRONG_PAIR},
        positions={0: {"best_move": "a7a8q", "pv": None}, 1: {"pv": _BEST_LINE_REFUTATION}},
    )

    report = await _run(session_factory, tmp_path)

    assert (report.candidates, report.changed) == (1, 1)
    expected = _expected(_PLAYED_PROMO_FEN, "g1h1", _BEST_LINE_REFUTATION, "a7a8q")
    await _assert_rewritten_to_app_pair(session_factory, game_id, expected)


@pytest.mark.asyncio
async def test_played_move_promotion_is_a_candidate(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """D-03 position: the blunder itself is the promotion (move_san 'a8=Q'), no token in any line."""
    refutation = "b8a8 g1h1"
    game_id = await make_game(
        start_fen=_PLAYED_PROMO_FEN,
        moves=_PLAYED_PROMO_MOVES,
        flaws={0: _WRONG_PAIR},
        positions={1: {"pv": refutation}},
    )

    report = await _run(session_factory, tmp_path)

    assert (report.candidates, report.changed) == (1, 1)
    expected = _expected(_PLAYED_PROMO_FEN, "a7a8q", refutation, None)
    await _assert_rewritten_to_app_pair(session_factory, game_id, expected)


@pytest.mark.asyncio
async def test_blunder_without_a_token_is_not_a_candidate_and_stays_untouched(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """The filter, not the compare, excludes it: its stored pair differs from its replay."""
    game_id = await make_game(
        start_fen=_PROMO_FEN,
        moves=(_PLAIN_BLUNDER, "g8f7"),
        flaws={0: _WRONG_PAIR},
        positions={1: {"pv": _PLAIN_REFUTATION}},
    )
    replay = _expected(_PROMO_FEN, _PLAIN_BLUNDER, _PLAIN_REFUTATION, None)
    assert (replay.loss, replay.missed) != _WRONG_PAIR

    report = await _run(session_factory, tmp_path)

    assert (report.candidates, report.changed) == (0, 0)
    assert await _stored(session_factory, game_id) == _WRONG_PAIR


@pytest.mark.parametrize("variant", ["unstamped_game", "mistake_severity"])
@pytest.mark.asyncio
async def test_rows_outside_the_scope_are_not_candidates(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    variant: str,
) -> None:
    """Games the line pass has not stamped and non-blunders are never selected."""
    game_id = await make_game(
        positions=_TRACER_POSITIONS,
        stamped=variant != "unstamped_game",
        severity=1 if variant == "mistake_severity" else 2,
    )

    report = await _run(session_factory, tmp_path)

    assert (report.candidates, report.changed) == (0, 0)
    assert await _stored(session_factory, game_id) == (0.0, 0.0)


# ---------------------------------------------------------------------------
# NULL rows and the float32 rule
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_null_row_whose_line_is_one_promotion_becomes_a_value(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """A short line ending on a promotion settles now, so a stored-NULL pair gets a value."""
    game_id = await make_game(
        moves=("g1h1", "c2c1q"),
        flaws={0: (None, None)},
        positions={1: {"pv": "c2c1q"}},
    )
    expected = _expected(_PROMO_FEN, "g1h1", "c2c1q", None)
    assert expected.loss is not None

    report = await _run(session_factory, tmp_path)

    assert (report.candidates, report.changed, report.null_to_value) == (1, 1, 1)
    _assert_pair(await _stored(session_factory, game_id), expected)
    undo = (tmp_path / "undo.tsv").read_text().splitlines()[1].split("\t")
    assert undo[3:5] == [promo.UNDO_NULL, promo.UNDO_NULL]


@pytest.mark.asyncio
async def test_row_already_holding_the_new_pair_is_unchanged(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    expected = _expected(_PROMO_FEN, _PROMO_BLUNDER, _PROMO_REFUTATION, None)
    game_id = await make_game(
        positions=_TRACER_POSITIONS, flaws={0: (expected.loss, expected.missed)}
    )

    report = await _run(session_factory, tmp_path)

    assert (report.candidates, report.changed) == (1, 0)
    assert not (tmp_path / "undo.tsv").exists()
    assert await _stored(session_factory, game_id) == (expected.loss, expected.missed)


# Opponent queens at ply 5 and the queen stays: the decaying mean 1.1290322580645162 is not
# representable in 4 bytes.
_NON_REAL_REFUTATION = "g8f7 h1g2 f7e6 b1b3 c2c1q b3b8 e6d5 b8b5 d5c4 b5b8"
_NON_REAL_MOVES = ("g1h1", "g8f7", "h1g2", "f7e6", "b1b3", "c2c1q")


@pytest.mark.asyncio
async def test_float32_only_difference_is_never_written(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """The stored REAL equals the replay in 4 bytes, so the row is a candidate but not a change."""
    raw = facepalm_material_inputs(chess.Board(_PROMO_FEN), "g1h1", _NON_REAL_REFUTATION, None)
    assert raw.loss is not None and promo.as_real(raw.loss) != raw.loss
    game_id = await make_game(
        moves=_NON_REAL_MOVES,
        flaws={0: (promo.as_real(raw.loss), promo.as_real(raw.missed))},
        positions={1: {"pv": _NON_REAL_REFUTATION}},
    )

    report = await _run(session_factory, tmp_path)

    assert (report.candidates, report.changed) == (1, 0)
    assert await _stored(session_factory, game_id) == (promo.as_real(raw.loss), 0.0)


def test_float32_compare_in_classify_change_uses_the_4_byte_pair() -> None:
    """Mutation anchor: comparing the float64 replay to the stored REAL reports a phantom change."""
    value = 1.4516129032258065
    row = promo.CandidateRow(1, 2, 0, "x", promo.as_real(value), 0.0, None, None, None)
    assert promo.classify_change(row, MaterialInputs(value, 0.0)) is None
    changed = promo.classify_change(row, MaterialInputs(value + 1.0, 0.0))
    assert changed is not None and changed.new_loss == promo.as_real(value + 1.0)


def test_as_real_rounds_to_a_4_byte_float() -> None:
    value = 1.4516129032258065
    assert promo.as_real(value) != value
    assert promo.as_real(promo.as_real(value)) == promo.as_real(value)
    assert promo.as_real(None) is None
    assert promo.as_real(5.0) == 5.0


# ---------------------------------------------------------------------------
# Type flips, guard misses
# ---------------------------------------------------------------------------

_QUEEN_TAKEN_REFUTATION = "g8f7 h1g2 f7e6 b1a1 c2c1q a1c1 e6d5 c1c8 d5d4 c8c1"
_QUEEN_TAKEN_MOVES = ("g1h1", "g8f7", "h1g2", "f7e6", "b1a1", "c2c1q")


@pytest.mark.asyncio
async def test_type_flips_are_counted_in_both_directions(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """Missed win to allowed loss (the tracer) and back (a promotion that nets out to no loss)."""
    await make_game(positions=_TRACER_POSITIONS)
    reverse = await make_game(
        moves=_QUEEN_TAKEN_MOVES,
        flaws={0: (2.0, 0.0)},
        positions={1: {"pv": _QUEEN_TAKEN_REFUTATION}},
    )
    expected = _expected(_PROMO_FEN, "g1h1", _QUEEN_TAKEN_REFUTATION, None)
    assert expected.loss == 0.0

    report = await _run(session_factory, tmp_path)

    assert report.changed == 2
    assert (report.type_missed_to_allowed, report.type_allowed_to_missed) == (1, 1)
    assert (report.loss_up, report.loss_down) == (1, 1)
    assert await _stored(session_factory, reverse) == (0.0, 0.0)


@pytest.mark.asyncio
async def test_guard_miss_keeps_the_concurrent_write(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A second session rewrites the pair between the read and the write: the guard misses."""
    game_id = await make_game(positions=_TRACER_POSITIONS)
    original = promo._recompute_page
    concurrent = (2.0, 2.0)

    async def recompute_then_rewrite(
        session: AsyncSession, rows: Sequence[promo.CandidateRow]
    ) -> tuple[list[promo.RowChange], int]:
        result = await original(session, rows)
        async with session_factory() as other:
            await other.execute(
                update(GameFlaw)
                .where(GameFlaw.game_id == game_id)
                .values(material_loss=concurrent[0], material_missed=concurrent[1])
            )
            await other.commit()
        return result

    monkeypatch.setattr(promo, "_recompute_page", recompute_then_rewrite)

    report = await _run(session_factory, tmp_path)

    assert (report.guard_misses, report.changed) == (1, 0)
    assert await _stored(session_factory, game_id) == concurrent
    assert not (tmp_path / "undo.tsv").exists()


# ---------------------------------------------------------------------------
# Dry-run sample check and exit code
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sample_check_flags_a_non_token_row_with_a_wrong_stored_pair(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    game_id = await make_game(
        start_fen=_PROMO_FEN,
        moves=(_PLAIN_BLUNDER, "g8f7"),
        flaws={0: _WRONG_PAIR},
        positions={1: {"pv": _PLAIN_REFUTATION}},
    )

    report = await _run(session_factory, tmp_path, dry_run=True, sample_game_modulus=1)

    assert (report.sample_checked, report.sample_mismatches) == (1, 1)
    assert report.sample_mismatch_rows == [(game_id, 0)]
    assert promo.exit_code_for(report, dry_run=True) == promo.EXIT_SAMPLE_MISMATCH
    # A real run never reads the sample, so the same report is a plain success there.
    assert promo.exit_code_for(report, dry_run=False) == promo.EXIT_OK


@pytest.mark.asyncio
async def test_sample_check_passes_when_non_token_rows_replay_to_their_stored_pair(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    replay = _expected(_PROMO_FEN, _PLAIN_BLUNDER, _PLAIN_REFUTATION, None)
    await make_game(
        start_fen=_PROMO_FEN,
        moves=(_PLAIN_BLUNDER, "g8f7"),
        flaws={0: (replay.loss, replay.missed)},
        positions={1: {"pv": _PLAIN_REFUTATION}},
    )

    report = await _run(session_factory, tmp_path, dry_run=True, sample_game_modulus=1)

    assert (report.sample_checked, report.sample_mismatches) == (1, 0)
    assert promo.exit_code_for(report, dry_run=True) == promo.EXIT_OK


@pytest.mark.asyncio
async def test_sample_check_skips_rows_with_a_promotion_token(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """Candidate rows are the pass's job, not the sample's."""
    await make_game(positions=_TRACER_POSITIONS)

    report = await _run(session_factory, tmp_path, dry_run=True, sample_game_modulus=1)

    assert (report.candidates, report.sample_checked) == (1, 0)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_exposes_the_eight_flags(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        promo._parse_args(["--help"])
    help_text = capsys.readouterr().out
    for flag in (
        "--db",
        "--dry-run",
        "--user-id",
        "--limit",
        "--throttle-ms",
        "--sample-size",
        "--report-dir",
        "--undo-log",
    ):
        assert flag in help_text


def test_cli_rejects_the_benchmark_db() -> None:
    with pytest.raises(SystemExit):
        promo._parse_args(["--db", "benchmark"])
