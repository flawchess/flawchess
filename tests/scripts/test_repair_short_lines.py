"""Tests for scripts/repair_short_lines.py (Phase 252 line repair).

Cases:
  (a) test_tracer_pinned_repair_end_to_end: one short stored line is re-searched by a REAL
      Stockfish pinned to its stored best move and written by the guarded UPDATE; evals and
      best_move stay unchanged, a report is written.
  (b) selection: mate exclusion (row k-1), checkmate and stalemate endings are legit_short,
      a 3+ ply pv is never selected, a row that is node0 of two lines is searched once,
      S3 `[]` sentinels at node0 ply <= DEDUP_MAX_PLY are searched and beyond it only counted,
      guest games are never selected, the work list is newest first (NULL played_at last).
  (c) write rules: D-01 pinned (best_move kept), D-02 NULL and illegal best_move (free search,
      best_move written), pin_mismatch and not-longer results are not written, the guard never
      overwrites a concurrent change.
  (d) run mechanics: resume after a completed run, dry-run writes nothing.
  (e) D-10 gates: strict-above-threshold boundaries, the pilot slice (ceil(1% of the work
      list)), a pilot whose repair does not stick exits 3 with STOP in the report, a DB error
      in the write session exits 3 and leaves the cursor at the last committed batch, the
      benchmark lane scope, the report lists every gate and the counters.

Uses session-maker injection against the per-run test DB and committed data (the script opens
its own sessions). Module user ids live in the 252_100..252_199 range. Every non-guest Game
inserted here is deleted in a finally block (eval-lottery isolation).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import chess
import sqlalchemy.exc

import pytest
import pytest_asyncio
from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.game_position import DEDUP_MAX_PLY
from app.models.user import User
from app.services.engine import _STOCKFISH_PATH, EnginePool
from app.services import eval_apply
from app.services.flaws_service import _run_all_moves_pass
from app.services.eval_apply import CACHED_PV_MIN_PLIES, pv_ply_count
from scripts import repair_short_lines as repair_module
from scripts.repair_short_lines import (
    EXIT_GATE_TRIPPED,
    MAX_COMMIT_LATENCY_RATIO,
    MAX_CONNECTION_RISE,
    MAX_LINE_REPAIR_DAYS,
    MAX_STILL_SHORT_SHARE,
    DbHealth,
    RepairStats,
    _read_state,
    _state_path,
    _write_state,
    build_work_list,
    evaluate_repair_gates,
    FEED_GATE_MIN_HOURS,
    MAX_CLASSIFICATION_FLIP_SHARE,
    FlipCounts,
    _positions_from_evals,
    count_classification_flips,
    run_measure_flips,
    FEED_MAX_EVAL_CHANGE_SHARE,
    MAX_REWALK_WEEKS,
    FeedWindowResult,
    GateResult,
    InFlightGame,
    _read_feed_state,
    _write_feed_state,
    evaluate_feed_gates,
    feed_window,
    pick_pin,
    replay_boards,
    run_status,
    run_feed,
    run_repair,
)

stockfish_missing = not (os.path.isfile(_STOCKFISH_PATH) and os.access(_STOCKFISH_PATH, os.X_OK))
skip_if_no_stockfish = pytest.mark.skipif(stockfish_missing, reason="Stockfish binary not found")

# ─── Constants ────────────────────────────────────────────────────────────────

_USER_ID = 252_100
_TEST_SEARCH_TIMEOUT_S: float = 60.0  # generous: SCHED_IDLE engines starve under -n auto
_EXIT_OK = 0

# Nine plies: 0 e4, 1 e5, 2 Nf3, 3 Nc6, 4 Bb5, 5 a6, 6 Ba4, 7 Nf6, 8 O-O.
_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *"
_FLAW_PLY = 6  # white's Ba4
# Legal in the position before ply 6 (after 3...a6) but not the move the game played.
_STORED_BEST = "b5c6"
_STORED_SHORT_PV = "b5c6"
_PRE_FLAW_EVAL_CP = 30
_FLAW_EVAL_CP = -20
_PLY_COUNT = 9


@dataclass(frozen=True)
class SeedRow:
    ply: int
    eval_cp: int | None = None
    eval_mate: int | None = None
    best_move: str | None = None
    pv: str | None = None


class Seeder:
    """Commits Users/Games/positions/flaws and deletes them again at teardown."""

    def __init__(self, maker: async_sessionmaker[AsyncSession]) -> None:
        self.maker = maker
        self.game_ids: list[int] = []
        self.user_ids: list[int] = []

    async def add_game(
        self,
        *,
        user_id: int = _USER_ID,
        is_guest: bool = False,
        pgn: str = _PGN,
        played_at: datetime | None = None,
        rows: list[SeedRow],
        flaw_plies: list[int],
        missed_blob: list[Any] | None = None,
        allowed_blob: list[Any] | None = None,
    ) -> int:
        async with self.maker() as session:
            existing = (
                (await session.execute(select(User).where(User.id == user_id)))
                .unique()
                .scalar_one_or_none()
            )
            if existing is None:
                session.add(
                    User(
                        id=user_id,
                        email=f"test-repair-{user_id}@example.com",
                        hashed_password="x",
                        is_guest=is_guest,
                    )
                )
                await session.flush()
                self.user_ids.append(user_id)
            game = Game(
                user_id=user_id,
                platform="lichess",
                platform_game_id=str(uuid.uuid4()),
                platform_url="https://lichess.org/repair-test",
                pgn=pgn,
                result="1-0",
                user_color="white",
                time_control_str="600+0",
                time_control_bucket="blitz",
                time_control_seconds=600,
                base_time_seconds=600,
                increment_seconds=0.0,
                rated=True,
                is_computer_game=False,
                played_at=played_at,
                full_pv_completed_at=datetime.now(timezone.utc),
            )
            session.add(game)
            await session.flush()
            game_id = game.id
            self.game_ids.append(game_id)
            for row in rows:
                session.add(
                    GamePosition(
                        user_id=user_id,
                        game_id=game_id,
                        ply=row.ply,
                        full_hash=row.ply + 1000,
                        white_hash=row.ply + 2000,
                        black_hash=row.ply + 3000,
                        phase=1,
                        eval_cp=row.eval_cp,
                        eval_mate=row.eval_mate,
                        best_move=row.best_move,
                        pv=row.pv,
                    )
                )
            for ply in flaw_plies:
                session.add(
                    GameFlaw(
                        user_id=user_id,
                        game_id=game_id,
                        ply=ply,
                        severity=2,
                        tempo=None,
                        phase=1,
                        is_miss=False,
                        is_lucky=False,
                        is_reversed=False,
                        is_squandered=False,
                        fen="8/8/8/8/8/8/8/8",
                        missed_pv_lines=missed_blob,
                        allowed_pv_lines=allowed_blob,
                    )
                )
            await session.commit()
        return game_id

    async def position(self, game_id: int, ply: int) -> GamePosition:
        async with self.maker() as session:
            return (
                await session.execute(
                    select(GamePosition).where(
                        GamePosition.game_id == game_id, GamePosition.ply == ply
                    )
                )
            ).scalar_one()

    async def cleanup(self) -> None:
        async with self.maker() as session:
            if self.game_ids:
                await session.execute(delete(Game).where(Game.id.in_(self.game_ids)))
            if self.user_ids:
                await session.execute(delete(User).where(User.id.in_(self.user_ids)))
            await session.commit()


@pytest_asyncio.fixture
async def session_factory(test_engine: Any) -> async_sessionmaker[AsyncSession]:  # type: ignore[type-arg]
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def seeder(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[Seeder, None]:
    seeded = Seeder(session_factory)
    try:
        yield seeded
    finally:
        await seeded.cleanup()


def _tracer_rows() -> list[SeedRow]:
    """Row N-1 carries a plain cp eval (no mate); row N is the short line with a legal pin."""
    return [
        SeedRow(ply=_FLAW_PLY - 1, eval_cp=_PRE_FLAW_EVAL_CP),
        SeedRow(
            ply=_FLAW_PLY,
            eval_cp=_FLAW_EVAL_CP,
            best_move=_STORED_BEST,
            pv=_STORED_SHORT_PV,
        ),
    ]


@skip_if_no_stockfish
async def test_tracer_pinned_repair_end_to_end(
    seeder: Seeder,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    game_id = await seeder.add_game(rows=_tracer_rows(), flaw_plies=[_FLAW_PLY])

    pool = EnginePool(size=1)
    await pool.start()
    try:
        exit_code = await run_repair(
            db="dev",
            session_maker=session_factory,
            pool=pool,
            report_dir=tmp_path,
            state_dir=tmp_path,
            search_timeout_s=_TEST_SEARCH_TIMEOUT_S,
        )
    finally:
        await pool.stop()

    assert exit_code == _EXIT_OK
    repaired = await seeder.position(game_id, _FLAW_PLY)
    assert repaired.pv is not None
    assert pv_ply_count(repaired.pv) >= CACHED_PV_MIN_PLIES
    assert repaired.pv.split()[0] == _STORED_BEST
    assert repaired.best_move == _STORED_BEST
    assert repaired.eval_cp == _FLAW_EVAL_CP and repaired.eval_mate is None
    before = await seeder.position(game_id, _FLAW_PLY - 1)
    assert before.eval_cp == _PRE_FLAW_EVAL_CP and before.eval_mate is None
    assert list(tmp_path.glob("repair-*.md"))


# ─── Fake searcher and shared helpers ─────────────────────────────────────────

_FAKE_LINE_PLIES = 6
_GUEST_USER_ID = 252_101
_STORED_ILLEGAL_BEST = "e2e4"  # the e-pawn already stands on e4 at ply 6
_MATE_SCORE = 3
_ONE_DAY = timedelta(days=1)

SearchResult = tuple[int | None, int | None, str | None, str | None]


def _legal_line(board: chess.Board, first: chess.Move | None, plies: int) -> str:
    """A deterministic legal line: `first` (else the first legal move), then first legal moves."""
    board = board.copy()
    moves: list[str] = []
    while len(moves) < plies and not board.is_game_over():
        move = first if (first is not None and not moves) else next(iter(board.legal_moves))
        moves.append(move.uci())
        board.push(move)
    return " ".join(moves)


class _FakeSearcher:
    """A LineSearcher scripted by a responder; records (fen, root_moves) of every call."""

    def __init__(
        self,
        responder: Callable[[chess.Board, Sequence[chess.Move] | None], SearchResult] | None = None,
    ) -> None:
        self.responder = responder or self._default
        self.calls: list[tuple[str, list[str] | None]] = []

    @staticmethod
    def _default(board: chess.Board, root_moves: Sequence[chess.Move] | None) -> SearchResult:
        first = root_moves[0] if root_moves else None
        return 20, None, None, _legal_line(board, first, _FAKE_LINE_PLIES)

    async def evaluate_nodes_with_pv(
        self,
        board: chess.Board,
        *,
        timeout_s: float | None = None,
        root_moves: Sequence[chess.Move] | None = None,
    ) -> SearchResult:
        self.calls.append(
            (board.fen(), [m.uci() for m in root_moves] if root_moves is not None else None)
        )
        cp, mate, _best, pv = self.responder(board, root_moves)
        return cp, mate, pv.split()[0] if pv else None, pv


async def _repair(
    maker: async_sessionmaker[AsyncSession],
    searcher: _FakeSearcher,
    tmp_path: Path,
    **kwargs: Any,
) -> tuple[int, RepairStats]:
    stats = RepairStats()
    code = await run_repair(
        db="dev",
        session_maker=maker,
        pool=searcher,
        report_dir=tmp_path,
        state_dir=tmp_path,
        stats_out=stats,
        **kwargs,
    )
    return code, stats


def _short_rows(
    *, best_move: str | None = _STORED_BEST, pv: str | None = _STORED_SHORT_PV
) -> list[SeedRow]:
    return [
        SeedRow(ply=_FLAW_PLY - 1, eval_cp=_PRE_FLAW_EVAL_CP),
        SeedRow(ply=_FLAW_PLY, eval_cp=_FLAW_EVAL_CP, best_move=best_move, pv=pv),
    ]


# ─── pick_pin ─────────────────────────────────────────────────────────────────


def test_pick_pin_returns_only_a_legal_stored_move() -> None:
    board = chess.Board()
    assert pick_pin(board, "e2e4") == chess.Move.from_uci("e2e4")
    assert pick_pin(board, "e7e5") is None  # illegal for white
    assert pick_pin(board, None) is None
    assert pick_pin(board, "") is None
    assert pick_pin(board, "zz99") is None  # unparsable


# ─── Selection ────────────────────────────────────────────────────────────────


async def test_mate_score_of_the_position_excludes_the_row(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    rows = _short_rows()
    rows[0] = SeedRow(ply=_FLAW_PLY - 1, eval_mate=_MATE_SCORE)  # row k-1: position k is mated
    game_id = await seeder.add_game(rows=rows, flaw_plies=[_FLAW_PLY])
    searcher = _FakeSearcher()

    _, stats = await _repair(session_factory, searcher, tmp_path)

    assert searcher.calls == []
    assert (await seeder.position(game_id, _FLAW_PLY)).pv == _STORED_SHORT_PV
    assert stats.selected_a == 0


async def test_checkmate_ending_is_legit_short_and_never_searched(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    # Fool's mate: ply 3 is black's Qh4#; the allowed line of the flaw at ply 2 is that mate.
    rows = [
        SeedRow(ply=2, eval_cp=-50),
        SeedRow(ply=3, eval_cp=-900, best_move="d8h4", pv="d8h4"),
    ]
    game_id = await seeder.add_game(pgn="1. f3 e5 2. g4 Qh4# 0-1", rows=rows, flaw_plies=[2])
    searcher = _FakeSearcher()

    _, stats = await _repair(session_factory, searcher, tmp_path)

    assert searcher.calls == []
    assert stats.legit_short == 1 and stats.searched == 0
    assert (await seeder.position(game_id, 3)).pv == "d8h4"


async def test_stalemate_ending_is_legit_short_and_never_searched(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    pgn = '[SetUp "1"]\n[FEN "7k/5Q2/8/8/8/8/8/K7 w - - 0 1"]\n\n1. Qg6 1/2-1/2'
    rows = [SeedRow(ply=0, eval_cp=900, best_move="f7g6", pv="f7g6")]
    await seeder.add_game(pgn=pgn, rows=rows, flaw_plies=[0])
    searcher = _FakeSearcher()

    _, stats = await _repair(session_factory, searcher, tmp_path)

    assert searcher.calls == []
    assert stats.legit_short == 1


async def test_three_ply_pv_is_never_selected(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    three_plies = "b5c6 d7c6 f3e5"
    assert pv_ply_count(three_plies) == CACHED_PV_MIN_PLIES
    await seeder.add_game(rows=_short_rows(pv=three_plies), flaw_plies=[_FLAW_PLY])
    searcher = _FakeSearcher()

    await _repair(session_factory, searcher, tmp_path)

    assert searcher.calls == []


async def test_row_that_is_node0_of_two_lines_is_searched_once(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    # Flaws at plies 5 and 6: node0 rows {5, 6} and {6, 7}; row 6 is node0 of two lines.
    await seeder.add_game(rows=_short_rows(), flaw_plies=[_FLAW_PLY - 1, _FLAW_PLY])
    searcher = _FakeSearcher()

    _, stats = await _repair(session_factory, searcher, tmp_path)

    assert len(searcher.calls) == 1
    assert stats.selected_a == 1


async def test_guest_game_is_never_selected(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    game_id = await seeder.add_game(
        user_id=_GUEST_USER_ID, is_guest=True, rows=_short_rows(), flaw_plies=[_FLAW_PLY]
    )
    searcher = _FakeSearcher()

    await _repair(session_factory, searcher, tmp_path)

    assert searcher.calls == []
    assert (await seeder.position(game_id, _FLAW_PLY)).pv == _STORED_SHORT_PV


async def test_work_list_is_newest_first_with_null_played_at_last(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    now = datetime.now(timezone.utc)
    undated = await seeder.add_game(played_at=None, rows=_short_rows(), flaw_plies=[_FLAW_PLY])
    older = await seeder.add_game(
        played_at=now - _ONE_DAY, rows=_short_rows(), flaw_plies=[_FLAW_PLY]
    )
    newest = await seeder.add_game(played_at=now, rows=_short_rows(), flaw_plies=[_FLAW_PLY])
    guest = await seeder.add_game(
        user_id=_GUEST_USER_ID,
        is_guest=True,
        played_at=now,
        rows=_short_rows(),
        flaw_plies=[_FLAW_PLY],
    )

    async with session_factory() as session:
        work_list = await build_work_list(session, "all")

    mine = [g for g in work_list if g in {undated, older, newest, guest}]
    assert mine == [newest, older, undated]


# ─── S3 sentinels ─────────────────────────────────────────────────────────────

_BEYOND_PGN = " ".join(f"{n}. Nf3 Nf6 {n + 1}. Ng1 Ng8" for n in range(1, 25, 2)) + " *"


async def test_sentinel_blob_within_dedup_ply_with_null_pv_is_searched_and_written(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    rows = [SeedRow(ply=_FLAW_PLY - 1, eval_cp=_PRE_FLAW_EVAL_CP), SeedRow(ply=_FLAW_PLY)]
    assert _FLAW_PLY <= DEDUP_MAX_PLY
    game_id = await seeder.add_game(rows=rows, flaw_plies=[_FLAW_PLY], missed_blob=[])
    searcher = _FakeSearcher()

    _, stats = await _repair(session_factory, searcher, tmp_path)

    assert stats.selected_b == 1 and stats.selected_a == 0
    written = await seeder.position(game_id, _FLAW_PLY)
    assert written.pv is not None and pv_ply_count(written.pv) >= CACHED_PV_MIN_PLIES
    assert written.best_move == written.pv.split()[0]  # D-02: NULL best_move gets the pv move


async def test_sentinel_blob_beyond_dedup_ply_is_only_counted(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    ply = DEDUP_MAX_PLY + 4
    rows = [SeedRow(ply=ply - 1, eval_cp=_PRE_FLAW_EVAL_CP), SeedRow(ply=ply)]
    game_id = await seeder.add_game(pgn=_BEYOND_PGN, rows=rows, flaw_plies=[ply], missed_blob=[])
    searcher = _FakeSearcher()

    _, stats = await _repair(session_factory, searcher, tmp_path)

    assert searcher.calls == []
    assert stats.sentinel_beyond_dedup_ply == 1 and stats.selected_b == 0
    assert (await seeder.position(game_id, ply)).pv is None


# ─── Write rules ──────────────────────────────────────────────────────────────


async def test_d01_legal_best_move_is_pinned_and_kept(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    game_id = await seeder.add_game(rows=_short_rows(), flaw_plies=[_FLAW_PLY])
    searcher = _FakeSearcher()

    _, stats = await _repair(session_factory, searcher, tmp_path)

    assert [root for _fen, root in searcher.calls] == [[_STORED_BEST]]
    after = await seeder.position(game_id, _FLAW_PLY)
    assert after.pv is not None and after.pv.split()[0] == _STORED_BEST
    assert pv_ply_count(after.pv) == _FAKE_LINE_PLIES
    assert after.best_move == _STORED_BEST
    assert stats.written == 1 and stats.best_move_written_null == 0


async def test_d02_null_best_move_searches_freely_and_writes_best_move(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    game_id = await seeder.add_game(rows=_short_rows(best_move=None), flaw_plies=[_FLAW_PLY])
    searcher = _FakeSearcher()

    _, stats = await _repair(session_factory, searcher, tmp_path)

    assert [root for _fen, root in searcher.calls] == [None]
    after = await seeder.position(game_id, _FLAW_PLY)
    assert after.pv is not None and after.best_move == after.pv.split()[0]
    assert stats.best_move_written_null == 1


async def test_d02_illegal_best_move_searches_freely_and_overwrites_best_move(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    game_id = await seeder.add_game(
        rows=_short_rows(best_move=_STORED_ILLEGAL_BEST), flaw_plies=[_FLAW_PLY]
    )
    searcher = _FakeSearcher()

    _, stats = await _repair(session_factory, searcher, tmp_path)

    assert [root for _fen, root in searcher.calls] == [None]
    after = await seeder.position(game_id, _FLAW_PLY)
    assert after.pv is not None
    assert after.best_move == after.pv.split()[0] != _STORED_ILLEGAL_BEST
    assert stats.best_move_written_illegal == 1


async def test_pin_mismatch_is_not_written(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    # Native Stockfish drops an illegal searchmoves entry and searches freely: simulate a
    # pinned search whose pv starts with another move.
    def wrong_first_move(
        board: chess.Board, root_moves: Sequence[chess.Move] | None
    ) -> SearchResult:
        return 20, None, None, "a2a3 h7h6 b2b3 h6h5"

    game_id = await seeder.add_game(rows=_short_rows(), flaw_plies=[_FLAW_PLY])

    _, stats = await _repair(session_factory, _FakeSearcher(wrong_first_move), tmp_path)

    assert stats.pin_mismatch == 1 and stats.written == 0
    assert (await seeder.position(game_id, _FLAW_PLY)).pv == _STORED_SHORT_PV


async def test_result_not_longer_than_stored_is_not_written(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    stored = "b5c6 d7c6"

    def same_length(board: chess.Board, root_moves: Sequence[chess.Move] | None) -> SearchResult:
        return 20, None, None, "b5c6 b7c6"

    game_id = await seeder.add_game(rows=_short_rows(pv=stored), flaw_plies=[_FLAW_PLY])

    _, stats = await _repair(session_factory, _FakeSearcher(same_length), tmp_path)

    assert stats.written == 0 and stats.unchanged == 1
    assert (await seeder.position(game_id, _FLAW_PLY)).pv == stored


async def test_guard_never_overwrites_a_concurrent_change(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    concurrent_pv = "b5c6 d7c6 f3e5 c6e5"
    game_id = await seeder.add_game(rows=_short_rows(), flaw_plies=[_FLAW_PLY])

    async def other_writer() -> None:
        async with session_factory() as session:
            await session.execute(
                update(GamePosition)
                .where(GamePosition.game_id == game_id, GamePosition.ply == _FLAW_PLY)
                .values(pv=concurrent_pv)
            )
            await session.commit()

    _, stats = await _repair(
        session_factory, _FakeSearcher(), tmp_path, _after_read_hook=other_writer
    )

    assert stats.concurrently_changed == 1 and stats.written == 0
    assert (await seeder.position(game_id, _FLAW_PLY)).pv == concurrent_pv


async def test_deleted_game_between_read_and_write_is_counted_game_deleted(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    game_id = await seeder.add_game(rows=_short_rows(), flaw_plies=[_FLAW_PLY])

    async def delete_game() -> None:
        async with session_factory() as session:
            await session.execute(delete(Game).where(Game.id == game_id))
            await session.commit()

    _, stats = await _repair(
        session_factory, _FakeSearcher(), tmp_path, _after_read_hook=delete_game
    )

    assert stats.game_deleted == 1 and stats.row_count_mismatch == 0


# ─── Run mechanics ────────────────────────────────────────────────────────────


async def test_second_run_after_a_completed_run_changes_nothing(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    game_id = await seeder.add_game(rows=_short_rows(), flaw_plies=[_FLAW_PLY])
    first = _FakeSearcher()
    await _repair(session_factory, first, tmp_path)
    repaired = (await seeder.position(game_id, _FLAW_PLY)).pv
    second = _FakeSearcher()

    _, stats = await _repair(session_factory, second, tmp_path)

    assert len(first.calls) == 1 and second.calls == []
    assert stats.games_done == 0
    assert (await seeder.position(game_id, _FLAW_PLY)).pv == repaired


async def test_dry_run_writes_nothing_and_leaves_the_cursor(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    game_id = await seeder.add_game(rows=_short_rows(), flaw_plies=[_FLAW_PLY])
    searcher = _FakeSearcher()

    _, stats = await _repair(session_factory, searcher, tmp_path, dry_run=True)

    assert len(searcher.calls) == 1
    assert stats.written == 0 and stats.would_write == 1
    assert (await seeder.position(game_id, _FLAW_PLY)).pv == _STORED_SHORT_PV
    assert not list(tmp_path.glob("*repair-cursor.json"))
    assert list(tmp_path.glob("repair-*.md"))


# ─── D-10 gates (pure) ────────────────────────────────────────────────────────

_SECONDS_PER_DAY = 86_400.0
_BASELINE_CONNECTIONS = 17
_BASELINE_COMMIT_S = 1.0
_LATENCY_WINDOW = repair_module.LATENCY_BASELINE_BATCHES


def _gate(gates: list[repair_module.GateResult], name: str) -> repair_module.GateResult:
    return next(g for g in gates if g.name == name)


def _evaluate(stats: RepairStats, health: DbHealth | None = None, **kwargs: Any) -> Any:
    params: dict[str, Any] = {
        "remaining_games": 0,
        "games_done": stats.games_done,
        "elapsed_s": 1.0,
    }
    params.update(kwargs)
    return evaluate_repair_gates(stats, health=health, **params)


def test_still_short_share_trips_only_strictly_above_the_threshold() -> None:
    at_limit = RepairStats(searched=100, still_short=3)  # exactly 0.03
    above = RepairStats(searched=10_000, still_short=301)  # 0.0301
    assert MAX_STILL_SHORT_SHARE == 0.03
    assert not _gate(_evaluate(at_limit), "still_short_share").tripped
    assert _gate(_evaluate(above), "still_short_share").tripped


def test_projected_days_trips_only_strictly_above_the_threshold() -> None:
    # 1 game done in one day with 1 row searched: 10 remaining games = exactly 10.0 days.
    stats = RepairStats(searched=1, games_done=1)
    at_limit = _evaluate(stats, remaining_games=10, elapsed_s=_SECONDS_PER_DAY)
    above = _evaluate(stats, remaining_games=11, elapsed_s=_SECONDS_PER_DAY)
    assert _gate(at_limit, "projected_days").value == MAX_LINE_REPAIR_DAYS
    assert not _gate(at_limit, "projected_days").tripped
    assert _gate(above, "projected_days").tripped


def test_connection_gate_boundary() -> None:
    def health(peak: int) -> DbHealth:
        return DbHealth(baseline_connections=_BASELINE_CONNECTIONS, peak_connections=peak)

    ok = _evaluate(RepairStats(), health(_BASELINE_CONNECTIONS + MAX_CONNECTION_RISE))
    over = _evaluate(RepairStats(), health(_BASELINE_CONNECTIONS + MAX_CONNECTION_RISE + 1))
    assert not _gate(ok, "connections").tripped
    assert _gate(over, "connections").tripped


def test_commit_latency_gate_boundary() -> None:
    def health(rolling: float) -> DbHealth:
        return DbHealth(
            commit_latencies_s=[_BASELINE_COMMIT_S] * _LATENCY_WINDOW + [rolling] * _LATENCY_WINDOW
        )

    ok = _evaluate(RepairStats(), health(_BASELINE_COMMIT_S * MAX_COMMIT_LATENCY_RATIO))
    over = _evaluate(RepairStats(), health(_BASELINE_COMMIT_S * MAX_COMMIT_LATENCY_RATIO + 0.1))
    assert not _gate(ok, "commit_latency").tripped
    assert _gate(over, "commit_latency").tripped


def test_mismatch_and_failed_batch_gates_trip_on_any_occurrence() -> None:
    gates = _evaluate(RepairStats(row_count_mismatch=1, failed_batches=1))
    assert _gate(gates, "row_count_mismatch").tripped and _gate(gates, "failed_batches").tripped
    assert not any(g.tripped for g in _evaluate(RepairStats()))


# ─── Pilot, failed batch, lane scope, report ──────────────────────────────────


def _worklist_path(tmp_path: Path) -> Path:
    return _state_path(tmp_path, "dev", "all", "worklist")


async def _seed_three_games(seeder: Seeder) -> list[int]:
    now = datetime.now(timezone.utc)
    return [
        await seeder.add_game(
            played_at=now - _ONE_DAY * n, rows=_short_rows(), flaw_plies=[_FLAW_PLY]
        )
        for n in range(3)
    ]


async def test_pilot_processes_ceil_of_one_percent_and_leaves_the_cursor(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    newest, middle, oldest = await _seed_three_games(seeder)
    _write_state(_worklist_path(tmp_path), {"game_ids": [newest, middle, oldest]})

    code, stats = await _repair(session_factory, _FakeSearcher(), tmp_path, pilot=True)

    assert code == 0 and stats.games_done == 1  # ceil(0.01 * 3) = 1: the newest game only
    assert (await seeder.position(newest, _FLAW_PLY)).pv != _STORED_SHORT_PV
    assert (await seeder.position(middle, _FLAW_PLY)).pv == _STORED_SHORT_PV
    cursor = _read_state(_state_path(tmp_path, "dev", "all", "repair-cursor"))
    assert cursor == {"index": 1}
    assert any("pilot" in path.name for path in tmp_path.glob("repair-*.md"))

    # A later run without --pilot continues from the cursor and repairs the rest.
    code, stats = await _repair(session_factory, _FakeSearcher(), tmp_path)
    assert code == 0 and stats.games_done == 2
    assert (await seeder.position(oldest, _FLAW_PLY)).pv != _STORED_SHORT_PV


async def test_pilot_whose_repair_does_not_stick_exits_3_with_stop_in_the_report(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    def one_ply_line(board: chess.Board, root_moves: Sequence[chess.Move] | None) -> SearchResult:
        return (
            20,
            None,
            None,
            root_moves[0].uci() if root_moves else next(iter(board.legal_moves)).uci(),
        )

    game_id = await seeder.add_game(rows=_short_rows(), flaw_plies=[_FLAW_PLY])
    _write_state(_worklist_path(tmp_path), {"game_ids": [game_id]})

    code, stats = await _repair(session_factory, _FakeSearcher(one_ply_line), tmp_path, pilot=True)

    assert code == EXIT_GATE_TRIPPED
    assert stats.still_short == 1 and stats.mate_short == 0
    report = next(tmp_path.glob("repair-*.md")).read_text()
    assert "STOP" in report and "still_short_share" in report


async def test_db_error_in_the_write_session_exits_3_with_the_cursor_at_the_last_commit(
    seeder: Seeder,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, second, third = await _seed_three_games(seeder)
    _write_state(_worklist_path(tmp_path), {"game_ids": [first, second, third]})
    monkeypatch.setattr(repair_module, "GAMES_PER_BATCH", 1)
    commits = 0

    async def fail_on_second_commit() -> None:
        nonlocal commits
        commits += 1
        if commits == 2:
            raise sqlalchemy.exc.OperationalError("UPDATE game_positions", {}, Exception("boom"))

    code, stats = await _repair(
        session_factory, _FakeSearcher(), tmp_path, _before_commit_hook=fail_on_second_commit
    )

    assert code == EXIT_GATE_TRIPPED and stats.failed_batches == 1
    assert _read_state(_state_path(tmp_path, "dev", "all", "repair-cursor")) == {"index": 1}
    assert (await seeder.position(first, _FLAW_PLY)).pv != _STORED_SHORT_PV
    assert (await seeder.position(second, _FLAW_PLY)).pv == _STORED_SHORT_PV  # rolled back
    assert (await seeder.position(third, _FLAW_PLY)).pv == _STORED_SHORT_PV  # never reached
    assert "STOP" in next(tmp_path.glob("repair-*.md")).read_text()


async def test_report_lists_every_gate_and_the_counters(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    await seeder.add_game(rows=_short_rows(), flaw_plies=[_FLAW_PLY])

    _, stats = await _repair(session_factory, _FakeSearcher(), tmp_path)

    report = next(tmp_path.glob("repair-*.md")).read_text()
    for gate in ("still_short_share", "projected_days", "row_count_mismatch", "failed_batches"):
        assert gate in report
    for counter in RepairStats().counters():
        assert f"- {counter}: " in report
    assert "PASS" in report and f"- written: {stats.written}" in report


async def test_lane_scope_selects_only_armed_classical_and_rapid_games(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], test_engine: Any
) -> None:
    from typing import cast

    from sqlalchemy import Table
    from sqlalchemy.ext.asyncio import AsyncEngine

    from app.models.benchmark_selection import BenchmarkSelection

    async with cast(AsyncEngine, test_engine).begin() as conn:
        await conn.run_sync(
            lambda sync_conn: BenchmarkSelection.metadata.create_all(
                sync_conn, tables=[cast(Table, BenchmarkSelection.__table__)], checkfirst=True
            )
        )
    now = datetime.now(timezone.utc)
    armed_classical, armed_blitz, unarmed_rapid, armed_two_tranches, unselected = [
        await seeder.add_game(
            played_at=now - _ONE_DAY * n, rows=_short_rows(), flaw_plies=[_FLAW_PLY]
        )
        for n in range(5)
    ]
    selections = [
        (armed_classical, "classical", True),
        (armed_blitz, "blitz", True),
        (unarmed_rapid, "rapid", False),
        (armed_two_tranches, "rapid", True),
        (armed_two_tranches, "classical", True),
    ]
    async with session_factory() as session:
        for game_id, tranche, armed in selections:
            session.add(
                BenchmarkSelection(
                    game_id=game_id,
                    user_id=_USER_ID,
                    tc_tranche=tranche,
                    lichess_arm=False,
                    armed=armed,
                )
            )
        await session.commit()

    async with session_factory() as session:
        lane = await build_work_list(session, "lane")

    mine = {armed_classical, armed_blitz, unarmed_rapid, armed_two_tranches, unselected}
    assert [g for g in lane if g in mine] == [armed_classical, armed_two_tranches]


async def test_lane_scope_outside_the_benchmark_db_is_a_usage_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="benchmark"):
        await run_repair(db="dev", scope="lane", pool=_FakeSearcher(), state_dir=tmp_path)
    with pytest.raises(SystemExit):
        repair_module._parse_args(["repair", "--db", "prod", "--scope", "lane"])


# ─── Feeder (D-03, D-11): tracer ──────────────────────────────────────────────

_FEED_USER_ID = 252_150
_FED_PV_PLIES = 12
_FULL_ALLOWED_PV = "e7e5 g1f3 b8c6 f1b5"  # four plies at row N + 1: a complete blob has 5 elements
_FULL_ALLOWED_BLOB: list[Any] = [{"n": i} for i in range(5)]


def _long_pv_at(ply: int, plies: int = _FED_PV_PLIES) -> str:
    """A legal `plies`-long line from the position before half-move `ply` of _PGN."""
    board = replay_boards(_PGN, [ply])[ply]
    return _legal_line(board, None, plies)


def _feed_rows(*, node0_pv: str | None = None, allowed_pv: str | None = None) -> list[SeedRow]:
    return [
        SeedRow(ply=_FLAW_PLY - 1, eval_cp=_PRE_FLAW_EVAL_CP),
        SeedRow(ply=_FLAW_PLY, eval_cp=_FLAW_EVAL_CP, pv=node0_pv or _long_pv_at(_FLAW_PLY)),
        SeedRow(
            ply=_FLAW_PLY + 1, eval_cp=_FLAW_EVAL_CP, pv=allowed_pv or _long_pv_at(_FLAW_PLY + 1, 4)
        ),
    ]


async def _mark_claimable(
    maker: async_sessionmaker[AsyncSession], game_id: int, **columns: Any
) -> None:
    """Stamp the completion columns the tier-4 lane keys on (default: engine-analysed, blobbed)."""
    now = datetime.now(timezone.utc)
    values: dict[str, Any] = {"full_evals_completed_at": now, "blobs_completed_at": now}
    values.update(columns)
    async with maker() as session:
        await session.execute(update(Game).where(Game.id == game_id).values(**values))
        await session.commit()


async def _blob_state(maker: async_sessionmaker[AsyncSession], game_id: int) -> dict[str, Any]:
    async with maker() as session:
        row = (
            await session.execute(
                text(
                    "SELECT f.ply, f.missed_pv_lines IS NULL AS missed_null,"
                    " jsonb_typeof(f.missed_pv_lines) IS NULL AS missed_sql_null,"
                    " f.allowed_pv_lines IS NULL AS allowed_null,"
                    " CAST(f.allowed_pv_lines AS text) AS allowed_text,"
                    " g.blobs_completed_at IS NULL AS stamp_cleared"
                    " FROM game_flaws f JOIN games g ON g.id = f.game_id WHERE f.game_id = :gid"
                    " ORDER BY f.ply LIMIT 1"
                ),
                {"gid": game_id},
            )
        ).one()
    return dict(row._mapping)


def _write_feed_inputs(state_dir: Path, game_ids: list[int], repair_cursor: int) -> None:
    _write_state(_state_path(state_dir, "dev", "all", "worklist"), {"game_ids": game_ids})
    _write_state(_state_path(state_dir, "dev", "all", "repair-cursor"), {"index": repair_cursor})


async def test_feed_tracer_repaired_line_leased_alone(
    seeder: Seeder,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game_id = await seeder.add_game(
        user_id=_FEED_USER_ID,
        rows=_feed_rows(),
        flaw_plies=[_FLAW_PLY],
        missed_blob=[{"n": 0}],  # the 1-element blob a 1-2 ply pv produced
        allowed_blob=_FULL_ALLOWED_BLOB,
    )
    await _mark_claimable(session_factory, game_id)
    _write_feed_inputs(tmp_path, [game_id], repair_cursor=1)

    exit_code = await run_feed(
        db="dev",
        windows=1,
        session_maker=session_factory,
        state_dir=tmp_path,
        report_dir=tmp_path,
        poll_s=0,
        _max_polls=1,  # nothing drains the fed game here: stop after the first wait
    )

    assert exit_code == _EXIT_OK
    fed = await _blob_state(session_factory, game_id)
    assert fed["missed_null"] and fed["missed_sql_null"]  # SQL NULL, not JSON null
    assert not fed["allowed_null"] and fed["allowed_text"] == (
        '[{"n": 0}, {"n": 1}, {"n": 2}, {"n": 3}, {"n": 4}]'
    )
    assert fed["stamp_cleared"]

    # The tier-4 lane now leases the missed line alone (plan 02's per-line lease).
    monkeypatch.setattr(eval_apply, "async_session_maker", session_factory)
    positions, sentinels = await eval_apply._build_flaw_blob_lease_positions(game_id)
    assert positions and not sentinels
    assert all(p.token.startswith(f"{_FLAW_PLY}:missed:") for p in positions)


# ─── Feeder: behavior (D-03, D-10, D-11, D-13, D-15) ──────────────────────────

_GUEST_FEED_USER_ID = 252_151
_BOGUS_ID_BASE = 10**12  # work-list ids that exist in no table: scanned, never fed
_ONE_HOUR_S = 3600.0


class _Clock:
    """An injectable wall clock the tests advance by hand."""

    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now

    def advance_hours(self, hours: float) -> None:
        self.now += hours * _ONE_HOUR_S


async def _seed_fed_game(
    seeder: Seeder,
    maker: async_sessionmaker[AsyncSession],
    *,
    user_id: int = _FEED_USER_ID,
    is_guest: bool = False,
    missed_blob: list[Any] | None = None,
    allowed_blob: list[Any] | None = None,
    played_at: datetime | None = None,
    **marks: Any,
) -> int:
    """A claimable, blobbed game whose flaw at _FLAW_PLY has a repaired (12-ply) missed pv."""
    game_id = await seeder.add_game(
        user_id=user_id,
        is_guest=is_guest,
        played_at=played_at,
        rows=_feed_rows(),
        flaw_plies=[_FLAW_PLY],
        missed_blob=[{"n": 0}] if missed_blob is None else missed_blob,
        allowed_blob=_FULL_ALLOWED_BLOB if allowed_blob is None else allowed_blob,
    )
    await _mark_claimable(maker, game_id, **marks)
    return game_id


async def _stamp_complete(maker: async_sessionmaker[AsyncSession], game_ids: Sequence[int]) -> None:
    """Simulate the fleet draining these games: set blobs_completed_at where still NULL."""
    async with maker() as session:
        await session.execute(
            update(Game)
            .where(Game.id.in_(game_ids), Game.blobs_completed_at.is_(None))
            .values(blobs_completed_at=datetime.now(timezone.utc))
        )
        await session.commit()


async def _count_cleared(maker: async_sessionmaker[AsyncSession], game_ids: Sequence[int]) -> int:
    async with maker() as session:
        result = await session.execute(
            text("SELECT count(*) FROM games WHERE id = ANY(:ids) AND blobs_completed_at IS NULL"),
            {"ids": list(game_ids)},
        )
        return int(result.scalar_one())


async def _missed_is_null(maker: async_sessionmaker[AsyncSession], game_id: int) -> bool:
    return bool((await _blob_state(maker, game_id))["missed_null"])


def _report_text(report_dir: Path) -> str:
    (path,) = report_dir.glob("feed-*.md")
    return path.read_text()


async def test_feed_low_water_holds_the_next_window_until_enough_games_drain(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    ids = [await _seed_fed_game(seeder, session_factory) for _ in range(6)]
    _write_feed_inputs(tmp_path, ids, repair_cursor=6)
    cleared: list[int] = []

    async def hook(poll: int) -> None:
        cleared.append(await _count_cleared(session_factory, ids))
        await _stamp_complete(session_factory, ids[:1] if poll == 1 else ids)

    exit_code = await run_feed(
        db="dev",
        batch_games=3,
        low_water=3,
        session_maker=session_factory,
        state_dir=tmp_path,
        report_dir=tmp_path,
        poll_s=0,
        clock=_Clock(),
        _after_poll_hook=hook,
        _max_polls=5,
    )

    assert exit_code == _EXIT_OK
    # Poll 1: three fed games pending, at the low water, nothing more fed. After one is
    # stamped complete the next window of three goes in: five pending at poll 2.
    assert cleared == [3, 5]


async def test_feed_windows_follow_the_work_list_and_never_pass_the_repair_cursor(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    now = datetime.now(timezone.utc)
    newest = await _seed_fed_game(seeder, session_factory, played_at=now)
    middle = await _seed_fed_game(seeder, session_factory, played_at=now - _ONE_DAY)
    beyond = await _seed_fed_game(seeder, session_factory, played_at=now - 2 * _ONE_DAY)
    async with session_factory() as session:
        work_list = [
            g for g in await build_work_list(session, "all") if g in {newest, middle, beyond}
        ]
    assert work_list == [newest, middle, beyond]
    _write_feed_inputs(tmp_path, work_list, repair_cursor=2)  # the repair has reached 2 games

    await run_feed(
        db="dev",
        batch_games=1,
        low_water=10,
        session_maker=session_factory,
        state_dir=tmp_path,
        report_dir=tmp_path,
        poll_s=0,
        clock=_Clock(),
        _max_polls=2,
    )

    assert await _missed_is_null(session_factory, newest)
    assert await _missed_is_null(session_factory, middle)
    assert not await _missed_is_null(session_factory, beyond)  # fenced by the repair cursor
    state = _read_feed_state(_state_path(tmp_path, "dev", "all", "feed-state"))
    assert state["index"] == 2
    assert [g["game_id"] for g in state["in_flight"]] == [newest, middle]


async def test_feed_window_is_idempotent_and_keeps_unmatched_games_stamped(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    matching = await _seed_fed_game(seeder, session_factory)
    unmatched = await _seed_fed_game(seeder, session_factory, missed_blob=_FULL_ALLOWED_BLOB)

    async with session_factory() as session:
        first = await feed_window(session, [matching, unmatched], dry_run=False)
    assert first.games_fed == [matching] and first.lines_nulled_missed == 1
    await _stamp_complete(session_factory, [matching])
    async with session_factory() as session:
        again = await feed_window(session, [matching, unmatched], dry_run=False)

    assert again == FeedWindowResult(0, 0, [], {})
    assert await _count_cleared(session_factory, [matching, unmatched]) == 0  # stamps survive
    async with session_factory() as session:
        assert await session.scalar(
            text("SELECT blobs_completed_at IS NOT NULL FROM games WHERE id = :i"), {"i": unmatched}
        )


async def test_feed_d03_bound_skips_node_gap_blobs_and_feeds_empty_sentinels(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    # A 5-element missed blob under a 12-ply pv is a node gap, not a repaired shape (D-03):
    # it is never fed. An `[]` allowed sentinel whose row now has a 4-ply pv is.
    game_id = await _seed_fed_game(
        seeder, session_factory, missed_blob=_FULL_ALLOWED_BLOB, allowed_blob=[]
    )

    async with session_factory() as session:
        result = await feed_window(session, [game_id], dry_run=False)

    assert (result.lines_nulled_missed, result.lines_nulled_allowed) == (0, 1)
    state = await _blob_state(session_factory, game_id)
    assert not state["missed_null"] and state["allowed_null"]


async def test_feed_never_feeds_an_unclaimable_game(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    game_id = await _seed_fed_game(seeder, session_factory, full_evals_completed_at=None)

    async with session_factory() as session:
        result = await feed_window(session, [game_id], dry_run=False)

    assert result.games_fed == []
    assert not await _missed_is_null(session_factory, game_id)


async def test_feed_never_feeds_guest_games(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    guest = await _seed_fed_game(
        seeder, session_factory, user_id=_GUEST_FEED_USER_ID, is_guest=True
    )

    async with session_factory() as session:
        assert guest not in await build_work_list(session, "all")
        # Defence in depth: even handed the id directly, the feeder leaves it alone.
        result = await feed_window(session, [guest], dry_run=False)

    assert result.games_fed == []
    assert not await _missed_is_null(session_factory, guest)


async def test_feed_gate_trips_when_nothing_drains_within_the_observation_window(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    game_id = await _seed_fed_game(seeder, session_factory)
    work_list = [game_id] + [_BOGUS_ID_BASE + i for i in range(5)]
    _write_feed_inputs(tmp_path, work_list, repair_cursor=1)
    clock = _Clock()

    async def hook(poll: int) -> None:
        clock.advance_hours(FEED_GATE_MIN_HOURS + 1)

    exit_code = await run_feed(
        db="dev",
        session_maker=session_factory,
        state_dir=tmp_path,
        report_dir=tmp_path,
        poll_s=0,
        clock=clock,
        _after_poll_hook=hook,
        _max_polls=5,
    )

    assert exit_code == EXIT_GATE_TRIPPED
    report = _report_text(tmp_path)
    assert "## Verdict: STOP" in report and "projected_weeks" in report
    assert "3.5-week" not in report  # D-15: no whole-fleet expectation is ever printed


async def test_feed_fast_drain_passes_the_gate_and_exits_ok(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    ids = [await _seed_fed_game(seeder, session_factory) for _ in range(2)]
    work_list = [*ids, *(_BOGUS_ID_BASE + i for i in range(3))]
    _write_feed_inputs(tmp_path, work_list, repair_cursor=len(work_list))
    clock = _Clock()

    async def hook(poll: int) -> None:
        clock.advance_hours(4)  # past FEED_GATE_MIN_HOURS after two polls: the gate is live
        await _stamp_complete(session_factory, ids)

    exit_code = await run_feed(
        db="dev",
        batch_games=1,
        low_water=1,
        session_maker=session_factory,
        state_dir=tmp_path,
        report_dir=tmp_path,
        poll_s=0,
        clock=clock,
        _after_poll_hook=hook,
        _max_polls=10,
    )

    assert exit_code == _EXIT_OK
    report = _report_text(tmp_path)
    assert "## Verdict: PASS" in report
    assert "games fed: 2, completed: 2, pending: 0" in report
    assert "stopped because: drained" in report  # exhausted work list, nothing in flight


async def test_feed_fingerprint_guard_trips_when_a_fed_game_eval_changes(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    game_id = await _seed_fed_game(seeder, session_factory)
    _write_feed_inputs(tmp_path, [game_id], repair_cursor=1)

    async def hook(poll: int) -> None:
        # Something re-evaluated the game while it sat in the lane (what D-12 forbids).
        async with session_factory() as session:
            await session.execute(
                update(GamePosition)
                .where(GamePosition.game_id == game_id, GamePosition.ply == _FLAW_PLY)
                .values(eval_cp=_FLAW_EVAL_CP + 1)
            )
            await session.commit()
        await _stamp_complete(session_factory, [game_id])

    exit_code = await run_feed(
        db="dev",
        session_maker=session_factory,
        state_dir=tmp_path,
        report_dir=tmp_path,
        poll_s=0,
        clock=_Clock(),
        _after_poll_hook=hook,
        _max_polls=3,
    )

    assert exit_code == EXIT_GATE_TRIPPED
    report = _report_text(tmp_path)
    assert "eval or flaw-set changed (fingerprint mismatch): 1" in report
    assert "eval_change_share" in report and "## Verdict: STOP" in report


async def test_feed_pilot_feeds_exactly_the_first_one_percent_and_exits_ok_once_drained(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    first_three = [await _seed_fed_game(seeder, session_factory) for _ in range(3)]
    fourth = await _seed_fed_game(seeder, session_factory)
    pilot_size = 3
    work_list = [*first_three, fourth, *(_BOGUS_ID_BASE + i for i in range(296))]
    assert len(work_list) == 100 * pilot_size  # ceil(1% of 300) = 3
    _write_feed_inputs(tmp_path, work_list, repair_cursor=len(work_list))
    clock = _Clock()

    async def hook(poll: int) -> None:
        clock.advance_hours(1)
        await _stamp_complete(session_factory, first_three)

    exit_code = await run_feed(
        db="dev",
        pilot=True,
        session_maker=session_factory,
        state_dir=tmp_path,
        report_dir=tmp_path,
        poll_s=0,
        clock=clock,
        _after_poll_hook=hook,
        _max_polls=5,
    )

    assert exit_code == _EXIT_OK
    assert all([await _missed_is_null(session_factory, g) for g in first_three])
    assert not await _missed_is_null(session_factory, fourth)  # past the pilot slice
    assert "feed-dev-all-pilot-" in next(tmp_path.glob("feed-*.md")).name
    assert "## Verdict: PASS" in _report_text(tmp_path)


async def test_feed_exhausted_work_list_with_nothing_to_feed_exits_ok_with_a_report(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    complete = await _seed_fed_game(seeder, session_factory, missed_blob=_FULL_ALLOWED_BLOB)
    _write_feed_inputs(tmp_path, [complete], repair_cursor=1)

    exit_code = await run_feed(
        db="dev",
        session_maker=session_factory,
        state_dir=tmp_path,
        report_dir=tmp_path,
        poll_s=0,
        clock=_Clock(),
        _max_polls=2,
    )

    assert exit_code == _EXIT_OK
    assert "games fed: 0, completed: 0, pending: 0" in _report_text(tmp_path)


async def test_feed_batch_and_low_water_flags_size_the_windows_and_the_report_has_null_windows(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    ids = [await _seed_fed_game(seeder, session_factory) for _ in range(4)]
    _write_feed_inputs(tmp_path, ids, repair_cursor=4)
    clock = _Clock()
    cleared: list[int] = []

    async def hook(poll: int) -> None:
        cleared.append(await _count_cleared(session_factory, ids))
        clock.advance_hours(2 if poll == 1 else 3)
        await _stamp_complete(session_factory, ids)

    exit_code = await run_feed(
        db="dev",
        batch_games=2,
        low_water=1,
        session_maker=session_factory,
        state_dir=tmp_path,
        report_dir=tmp_path,
        poll_s=0,
        clock=clock,
        _after_poll_hook=hook,
        _max_polls=5,
    )

    assert exit_code == _EXIT_OK
    assert cleared == [2, 2]  # two games per window
    report = _report_text(tmp_path)
    assert "window size 2 games, low water 1 games" in report
    # Fed at t=0 and drained at t=2 h (two games), then fed at t=2 h and drained at t=5 h.
    assert "p50: 2.00 h, p95: 3.00 h, max: 3.00 h" in report


async def test_feed_dry_run_writes_nothing_and_persists_no_state(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    game_id = await _seed_fed_game(seeder, session_factory)
    _write_feed_inputs(tmp_path, [game_id], repair_cursor=1)

    exit_code = await run_feed(
        db="dev",
        dry_run=True,
        windows=1,
        session_maker=session_factory,
        state_dir=tmp_path,
        report_dir=tmp_path,
        clock=_Clock(),
    )

    assert exit_code == _EXIT_OK
    assert not await _missed_is_null(session_factory, game_id)
    assert await _count_cleared(session_factory, [game_id]) == 0
    assert not _state_path(tmp_path, "dev", "all", "feed-state").exists()
    assert "lines NULLed, missed: 1" in _report_text(tmp_path)
    assert next(tmp_path.glob("feed-*.md")).name.startswith("feed-dev-all-dryrun-")


def test_feed_gates_trip_only_strictly_above_their_thresholds() -> None:

    def projection(remaining_games: int) -> list[GateResult]:
        return evaluate_feed_gates(
            lines_fed_per_game=1.0,
            remaining_games=remaining_games,
            lines_drained=6,
            elapsed_h=6.0,
            completed_games=1000,
            eval_changed=0,
        )

    # 1344 remaining lines at one line per hour is exactly MAX_REWALK_WEEKS weeks.
    at, over = projection(1344), projection(1345)
    assert at[0].value == MAX_REWALK_WEEKS and not at[0].tripped
    assert over[0].tripped
    # Not judged before FEED_GATE_MIN_HOURS of observation; zero drain after it is infinite.
    early = evaluate_feed_gates(
        lines_fed_per_game=1.0,
        remaining_games=10_000,
        lines_drained=0,
        elapsed_h=FEED_GATE_MIN_HOURS - 0.1,
        completed_games=0,
        eval_changed=0,
    )
    stalled = evaluate_feed_gates(
        lines_fed_per_game=1.0,
        remaining_games=10,
        lines_drained=0,
        elapsed_h=FEED_GATE_MIN_HOURS,
        completed_games=0,
        eval_changed=0,
    )
    assert not early[0].tripped and stalled[0].tripped
    boundary = round(FEED_MAX_EVAL_CHANGE_SHARE * 1000)
    ok = evaluate_feed_gates(
        lines_fed_per_game=0.0,
        remaining_games=0,
        lines_drained=0,
        elapsed_h=0.0,
        completed_games=1000,
        eval_changed=boundary,
    )
    bad = evaluate_feed_gates(
        lines_fed_per_game=0.0,
        remaining_games=0,
        lines_drained=0,
        elapsed_h=0.0,
        completed_games=1000,
        eval_changed=boundary + 1,
    )
    assert not ok[1].tripped and bad[1].tripped


async def test_status_prints_the_progress_and_changes_no_row(
    seeder: Seeder,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    drained = await _seed_fed_game(seeder, session_factory)
    pending = await _seed_fed_game(seeder, session_factory, blobs_completed_at=None)
    _write_feed_inputs(tmp_path, [drained, pending, _BOGUS_ID_BASE], repair_cursor=2)
    state = repair_module._new_feed_state()
    state["index"] = 2
    state["in_flight"] = [
        InFlightGame(game_id=game_id, fed_at=1.0, lines=1, eval_fp="a", flaw_fp="b")
        for game_id in (drained, pending)
    ]
    _write_feed_state(_state_path(tmp_path, "dev", "all", "feed-state"), state)
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    (report_dir / "feed-dev-all-full-20260101T0000Z.md").write_text("x")

    exit_code = await run_status(
        db="dev", session_maker=session_factory, state_dir=tmp_path, report_dir=report_dir
    )

    out = capsys.readouterr().out
    assert exit_code == _EXIT_OK
    for expected in (
        "work list size: 3",
        "repair cursor: 2",
        "feed cursor: 2",
        "in flight: 2",
        "pending (blobs_completed_at still NULL): 1",
        "feed-dev-all-full-20260101T0000Z.md",
    ):
        assert expected in out
    assert await _count_cleared(session_factory, [drained, pending]) == 1  # untouched


# ─── measure-flips (D-05, D-10) ───────────────────────────────────────────────

# Row plies 0..8 of _PGN: from ply 2 on every move swings the eval by 500 cp, so each is a
# blunder for the side that played it. Row 9 is the (unevaluated) terminal position.
_FLIP_STORED_CPS: list[int | None] = [0, 0, -500, 0, -500, 0, -500, 0, -500, None]
_FLIP_BLUNDERS = 7  # moves 2..8
_FLIP_BOARDS_PER_ARM = 9  # the board after each of the nine moves, none terminal
_FLIP_ARMS = 2
_FLIP_USER_ID = 252_120
_FLIP_GUEST_USER_ID = 252_121
_MATE_IN_THREE = 3
_MATE_IN_FIVE = 5


def _evals(*cps: int | None, mates: dict[int, int] | None = None) -> list[GamePosition]:
    mates = mates or {}
    return _positions_from_evals(
        [(None if i in mates else cp, mates.get(i)) for i, cp in enumerate(cps)]
    )


def test_flips_identical_rows_count_zero() -> None:
    rows = _evals(0, 0, -500, 0, -500)

    counts = count_classification_flips(rows, _evals(0, 0, -500, 0, -500))

    assert counts.stored_mb == 3 and counts.flips == 0 and counts.share == 0.0


def test_flips_stored_blunder_removed_by_the_exact_eval_is_one_flip_over_one_stored_mb() -> None:
    counts = count_classification_flips(_evals(0, 0, -500), _evals(0, 0, 0))

    assert counts == FlipCounts(stored_mb=1, flips=1, lost_mb=1)
    assert counts.share == 1.0


def test_flips_a_move_that_is_mistake_or_blunder_only_under_the_exact_eval_counts() -> None:
    counts = count_classification_flips(_evals(0, 0, 0), _evals(0, 0, -500))

    assert counts.flips == 1 and counts.exact_only_mb == 1
    assert counts.stored_mb == 0 and counts.share == 0.0  # no stored M/B to divide by


def test_flips_mistake_to_blunder_is_a_flip() -> None:
    # 150 cp is a mistake and 500 cp a blunder for the side to move (flaws_service bands).
    counts = count_classification_flips(_evals(0, 0, -150), _evals(0, 0, -500))

    assert counts == FlipCounts(stored_mb=1, flips=1, changed_mb_severity=1)


def test_flips_a_transition_with_a_mate_eval_follows_the_mate_ladder() -> None:
    # White has a forced mate in 3, then plays to a lost cp position: the mate ladder calls
    # that a blunder. Under the exact eval the mate persists (mate in 5): no flaw at all.
    stored = _evals(0, None, -400, mates={1: _MATE_IN_THREE})
    exact = _evals(0, None, None, mates={1: _MATE_IN_THREE, 2: _MATE_IN_FIVE})
    assert _run_all_moves_pass(stored)[2][1] == "blunder"  # what production says
    assert _run_all_moves_pass(exact)[2][1] is None

    counts = count_classification_flips(stored, exact)

    # Move 1 (black walking into the mate) is a blunder on both sides: not a flip. Move 2 is.
    assert counts == FlipCounts(stored_mb=2, flips=1, lost_mb=1)


async def _seed_flip_game(
    seeder: Seeder, maker: async_sessionmaker[AsyncSession], **kwargs: Any
) -> int:
    rows = [SeedRow(ply=i, eval_cp=cp) for i, cp in enumerate(_FLIP_STORED_CPS)]
    game_id = await seeder.add_game(rows=rows, flaw_plies=[], **kwargs)
    await _mark_claimable(maker, game_id, blobs_completed_at=None)
    return game_id


async def _position_snapshot(
    maker: async_sessionmaker[AsyncSession], game_id: int
) -> list[tuple[int, int | None, int | None, str | None]]:
    async with maker() as session:
        result = await session.execute(
            select(GamePosition.ply, GamePosition.eval_cp, GamePosition.eval_mate, GamePosition.pv)
            .where(GamePosition.game_id == game_id)
            .order_by(GamePosition.ply)
        )
        return [(r.ply, r.eval_cp, r.eval_mate, r.pv) for r in result]


def _stored_eval_searcher() -> _FakeSearcher:
    """Answers each board with the eval stored for its row (row ply = moves played - 1)."""

    def respond(board: chess.Board, _roots: Sequence[chess.Move] | None) -> SearchResult:
        return _FLIP_STORED_CPS[len(board.move_stack) - 1], None, None, None

    return _FakeSearcher(respond)


async def test_flips_sample_excludes_lichess_eval_games_and_guest_games(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    await _seed_flip_game(seeder, session_factory, user_id=_FLIP_USER_ID)
    lichess_game = await _seed_flip_game(seeder, session_factory, user_id=_FLIP_USER_ID)
    await _mark_claimable(
        session_factory, lichess_game, lichess_evals_at=datetime.now(timezone.utc)
    )
    await _seed_flip_game(seeder, session_factory, user_id=_FLIP_GUEST_USER_ID, is_guest=True)
    exact, control = _stored_eval_searcher(), _stored_eval_searcher()

    await run_measure_flips(
        db="dev",
        sample_games=50,
        session_maker=session_factory,
        pool=exact,
        control_pool=control,
        report_dir=tmp_path,
    )

    # Only the engine-evaluated non-guest game is searched, once per arm per board.
    assert len(exact.calls) == len(control.calls) == _FLIP_BOARDS_PER_ARM


async def test_flips_run_with_a_shifting_searcher_exits_3_and_writes_no_row(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    game_id = await _seed_flip_game(seeder, session_factory, user_id=_FLIP_USER_ID)
    before = await _position_snapshot(session_factory, game_id)
    flat = _FakeSearcher(lambda _board, _roots: (0, None, None, None))  # erases every swing
    flat_control = _FakeSearcher(lambda _board, _roots: (0, None, None, None))

    exit_code = await run_measure_flips(
        db="dev",
        sample_games=50,
        session_maker=session_factory,
        pool=flat,
        control_pool=flat_control,
        report_dir=tmp_path,
    )

    assert exit_code == EXIT_GATE_TRIPPED
    (report_path,) = tmp_path.glob("flips-dev-*.md")
    report = report_path.read_text()
    assert "## Verdict: STOP" in report and "classification_flip_share" in report
    assert f"stored mistakes and blunders: {_FLIP_BLUNDERS}" in report
    assert "flip share: 1.0000" in report
    assert await _position_snapshot(session_factory, game_id) == before


async def test_flips_run_returning_the_stored_evals_exits_0_and_writes_no_row(
    seeder: Seeder, session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    game_id = await _seed_flip_game(seeder, session_factory, user_id=_FLIP_USER_ID)
    before = await _position_snapshot(session_factory, game_id)

    exit_code = await run_measure_flips(
        db="dev",
        sample_games=50,
        session_maker=session_factory,
        pool=_stored_eval_searcher(),
        control_pool=_stored_eval_searcher(),
        report_dir=tmp_path,
    )

    assert exit_code == _EXIT_OK
    (report_path,) = tmp_path.glob("flips-dev-*.md")
    report = report_path.read_text()
    assert "## Verdict: PASS" in report and "flip share: 0.0000" in report
    assert f"| classification_flip_share | 0 | {MAX_CLASSIFICATION_FLIP_SHARE:g} | PASS |" in report
    assert await _position_snapshot(session_factory, game_id) == before


def test_flips_and_the_other_subcommands_parse_their_documented_flags() -> None:
    flips = repair_module._parse_args(
        ["measure-flips", "--db", "dev", "--sample-games", "3", "--engines", "2"]
    )
    assert (flips.command, flips.sample_games, flips.engines) == ("measure-flips", 3, 2)
    feed = repair_module._parse_args(
        [
            "feed",
            "--db",
            "prod",
            "--pilot",
            "--batch-games",
            "2",
            "--low-water",
            "1",
            "--windows",
            "4",
        ]
    )
    assert (feed.pilot, feed.batch_games, feed.low_water, feed.windows) == (True, 2, 1, 4)
    assert repair_module._parse_args(["status", "--db", "dev"]).command == "status"
    with pytest.raises(SystemExit):
        repair_module._parse_args(["feed", "--db", "dev", "--scope", "lane"])
