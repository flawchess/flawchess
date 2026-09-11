"""Tests for scripts/opening_cache_repair.py (Phase 220, Plan 01).

These are selection/persistence-logic tests -- the engine is always stubbed
(a `_FakePool` recording every board it was asked to evaluate, keyed by FEN)
so every test is deterministic and needs no Stockfish binary. Every test that
inserts a non-guest `Game`/`User` row cleans it up in a `finally` (memory
`project_eval_lottery_test_isolation`), and every test that touches the
singleton `opening_cache_repair_progress` row resets it in a `finally` too,
since it is a genuinely global row shared by every test in this worker's DB.

Coverage:
- test_seed_is_idempotent : a second `seed` run inserts nothing more once
  every opening_position_eval row already has an audit row.
- test_seed_dry_run_writes_nothing : --dry-run counts candidates but inserts
  zero rows.
- test_screen_skips_hash_mismatched_carrier : the fake pool records NO board
  for a hash whose stored carrier replays to a different position, and the
  cache row's audit entry is left completely unchanged.
- test_screen_clean_flagged_split : a small delta lands screened_clean, a
  large delta lands flagged.
- test_screen_floor_exactly_boundary_is_clean : a delta exactly equal to
  screen_floor lands screened_clean (the comparison is `<=`).
- test_calibrate_out_of_order_refuses / test_screen_out_of_order_refuses :
  each stage refuses to run before its predecessor's finished_at is set, and
  writes nothing.
- test_screen_floor_required_refuses : `screen` refuses when screen_floor is
  still NULL even though calibrate "finished", and mutates no audit row.
- test_seed_dry_run_writes_nothing / test_calibrate_dry_run_writes_nothing :
  --dry-run changes no row count anywhere.
- test_calibrate_measures_floors : screen_floor/confirm_floor are written as
  the nearest-rank p99 of the depth-15/1M-node expected-score deltas.
- test_calibrate_fewer_than_n_uses_available : requesting more than the
  eligible population records the real (smaller) calibration_n.
- test_calibrate_zero_eligible_raises : zero eligible rows leaves both floors
  NULL and raises.
- test_calibrate_limit_zero_does_not_stamp_started_at : --limit 0 touches no
  DB row at all.
- test_screen_resume_after_cancelled_error : a `CancelledError` mid-gather
  leaves the batch's audit rows at `pending` and the cursor unchanged; a
  second run reprocesses exactly that batch (asserted from the fresh fake
  pool's recorded board list) with no duplication.
- TestReport (Phase 220 Plan 04, CACHEFIX-07) : write_repair_report is
  read-only (six table row counts identical before/after), tolerates zero
  audit rows, orders the top-30 table by carrier count DESC then full_hash
  ASC (a total order), emits no PII token, and the injected now/out_dir
  determine the filename/location.
- TestLegacySample (Phase 220 Plan 04, CACHEFIX-10, D-07) : refuses to run
  without a calibrated screen_floor, the decision rule's four corners (ratio
  exactly 2x, ratio>2x with excess just under/at/above 1.0pp), a short
  cohort uses all available games and reports the real n, a zero-eligible
  cohort raises with no verdict, a delta exactly at screen_floor agrees, and
  the stage writes nothing to game_positions/game_flaws/opening_position_eval.
"""

from __future__ import annotations

import asyncio
import datetime
import io
import math
import time
import uuid
from pathlib import Path

import chess
import chess.pgn
import pytest
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import undefer

from app.models.drill_item import DrillItem
from app.models.game import Game
from app.models.game_best_move import GameBestMove
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.herring_pool import HerringPool
from app.models.opening_cache_audit import (
    OpeningCacheAudit,
    OpeningCacheRepairGame,
    OpeningCacheRepairProgress,
    OpeningCacheRepairRow,
)
from app.models.opening_position_eval import OpeningPositionEval
from app.models.user import User
from app.repositories.game_flaws_repository import flaw_record_to_row
from app.services.eval_apply import _game_write_lock_key
from app.services.eval_utils import eval_cp_to_expected_score
from app.services.flaws_service import classify_game_flaws
from app.services.zobrist import compute_hashes
from scripts.opening_cache_repair import (
    CALIBRATION_DEFAULT_N,
    MAX_CARRIERS_PER_HASH,
    CalibrationRequiredError,
    CalibrationSampleEmptyError,
    StageOrderError,
    _apply_confirm_fields,
    _classify_legacy_sample_row,
    _collect_confirm_candidates,
    _legacy_sample_decision,
    _LegacySampleCohortResult,
    _rederive_one_game,
    run_calibrate,
    run_confirm,
    run_demote,
    run_legacy_sample,
    run_orphans,
    run_propagate,
    run_propagate_best_moves,
    run_rederive,
    run_report,
    run_screen,
    run_seed,
    write_repair_report,
)

pytestmark = pytest.mark.asyncio

# A real 6-half-move opening (Ruy Lopez) -- plies 0-5, well inside ply 1..20.
_RUY_LOPEZ_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *"
# A genuinely different opening, used to build a "wrong carrier" whose real
# replayed board differs from whatever hash a test overrides onto it.
_SICILIAN_PGN = "1. e4 c5 2. Nf3 Nc6 3. Bb5 a6 *"

_TEST_USER_ID = 88801


def _session_maker(test_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(test_engine, expire_on_commit=False)


class _FakePool:
    """Stub EnginePool. Returns scripted (cp, mate) keyed by board FEN for
    evaluate() and an optional separate scripted 4-tuple for
    evaluate_nodes_with_pv(), records every board it was asked to evaluate
    (fen strings), and can raise on the Nth evaluate() call to simulate a
    kill mid-batch (RESEARCH §Testing SIGTERM-mid-batch resume, design 1)."""

    def __init__(
        self,
        result_by_fen: dict[str, tuple[int | None, int | None]],
        full_result_by_fen: dict[str, tuple[int | None, int | None, str | None, str | None]]
        | None = None,
        raise_on_call: int | None = None,
    ) -> None:
        self._result_by_fen = result_by_fen
        self._full_result_by_fen = full_result_by_fen or {}
        self._raise_on_call = raise_on_call
        self._call_count = 0
        self.evaluated_fens: list[str] = []

    async def evaluate(self, board: chess.Board) -> tuple[int | None, int | None]:
        self._call_count += 1
        if self._raise_on_call is not None and self._call_count == self._raise_on_call:
            raise asyncio.CancelledError("simulated kill mid-batch")
        fen = board.fen()
        self.evaluated_fens.append(fen)
        return self._result_by_fen.get(fen, (None, None))

    async def evaluate_nodes_with_pv(
        self, board: chess.Board
    ) -> tuple[int | None, int | None, str | None, str | None]:
        fen = board.fen()
        if fen in self._full_result_by_fen:
            return self._full_result_by_fen[fen]
        cp, mate = self._result_by_fen.get(fen, (None, None))
        return cp, mate, None, None


def _real_hashes_by_ply(pgn: str) -> dict[int, int]:
    """Replay `pgn` with real python-chess and return {ply: real full_hash}.

    Mirrors _collect_full_ply_targets's own walk: ply k's hash is the
    position BEFORE the move played from ply k (ply 0 = starting position).
    """
    game = chess.pgn.read_game(io.StringIO(pgn))
    assert game is not None
    board = game.board()
    hashes: dict[int, int] = {}
    for ply, node in enumerate(game.mainline()):
        hashes[ply] = compute_hashes(board)[2]
        board.push(node.move)
    return hashes


async def _ensure_user(session_maker: async_sessionmaker[AsyncSession], user_id: int) -> None:
    async with session_maker() as session:
        existing = (
            (await session.execute(select(User).where(User.id == user_id)))
            .unique()
            .scalar_one_or_none()
        )
        if existing is None:
            session.add(
                User(
                    id=user_id,
                    email=f"opening-cache-repair-test-{user_id}@example.com",
                    hashed_password="fakehash",
                )
            )
            await session.commit()


async def _insert_carrier_game(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    pgn: str = _RUY_LOPEZ_PGN,
    user_id: int = _TEST_USER_ID,
    hash_overrides: dict[int, int] | None = None,
    full_evals_completed_at: datetime.datetime | None = None,
    lichess_evals_at: datetime.datetime | None = None,
) -> int:
    """Insert a Game + its GamePosition rows (plies 0..N-1) with REAL replayed
    hashes, optionally overridden per-ply via `hash_overrides` (used to build
    a deliberately wrong stored hash for the mismatch test). Passing
    full_evals_completed_at/lichess_evals_at controls calibrate's known-clean
    eligibility (seed diagnosis 5). Returns game_id."""
    real_hashes = _real_hashes_by_ply(pgn)
    overrides = hash_overrides or {}
    async with session_maker() as session:
        game = Game(
            user_id=user_id,
            platform="lichess",
            platform_game_id=str(uuid.uuid4()),
            pgn=pgn,
            result="1-0",
            user_color="white",
            rated=True,
            is_computer_game=False,
            full_evals_completed_at=full_evals_completed_at,
            lichess_evals_at=lichess_evals_at,
        )
        session.add(game)
        await session.flush()
        game_id = int(game.id)  # type: ignore[arg-type]
        for ply, real_hash in real_hashes.items():
            session.add(
                GamePosition(
                    user_id=user_id,
                    game_id=game_id,
                    ply=ply,
                    full_hash=overrides.get(ply, real_hash),
                    white_hash=0,
                    black_hash=0,
                    phase=0,
                    endgame_class=None,
                    eval_cp=None,
                    eval_mate=None,
                )
            )
        await session.commit()
    return game_id


async def _delete_games(
    session_maker: async_sessionmaker[AsyncSession], game_ids: list[int]
) -> None:
    if not game_ids:
        return
    async with session_maker() as session:
        await session.execute(delete(Game).where(Game.id.in_(game_ids)))
        await session.commit()


async def _delete_opening_cache(
    session_maker: async_sessionmaker[AsyncSession], full_hashes: list[int]
) -> None:
    if not full_hashes:
        return
    async with session_maker() as session:
        await session.execute(
            delete(OpeningPositionEval).where(OpeningPositionEval.full_hash.in_(full_hashes))
        )
        await session.execute(
            delete(OpeningCacheAudit).where(OpeningCacheAudit.full_hash.in_(full_hashes))
        )
        await session.commit()


async def _reset_progress(session_maker: async_sessionmaker[AsyncSession]) -> None:
    """The progress row (id=1) is a genuinely global singleton -- delete it so
    the next test starts from a clean slate."""
    async with session_maker() as session:
        await session.execute(delete(OpeningCacheRepairProgress))
        await session.commit()


async def _current_max_game_id(session_maker: async_sessionmaker[AsyncSession]) -> int:
    """The current max games.id -- games.id is a plain autoincrement sequence
    that never reuses a value even after a row is deleted, so seeding
    `last_game_id_walked` at this value scopes `screen`'s id-ASC walk to only
    the game(s) THIS test inserts afterward, regardless of what other tests
    in this worker's shared DB left behind (or already cleaned up)."""
    async with session_maker() as session:
        return (await session.execute(select(func.coalesce(func.max(Game.id), 0)))).scalar_one()


async def _seed_calibrate_finished(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    screen_floor: float,
    last_game_id_walked: int = 0,
) -> None:
    """Simulate `calibrate` having already finished, so `screen`'s _stage_gate
    passes -- task 1 builds `seed` and `screen` only; `calibrate` itself is
    built in a later task of this same plan. `last_game_id_walked` should be
    the max games.id BEFORE this test's own game insert (see
    _current_max_game_id) so the walk only ever sees this test's own game."""
    now = datetime.datetime.now(datetime.timezone.utc)
    async with session_maker() as session:
        row = OpeningCacheRepairProgress(
            id=1,
            seed_started_at=now,
            seed_finished_at=now,
            calibrate_started_at=now,
            calibrate_finished_at=now,
            screen_floor=screen_floor,
            confirm_floor=screen_floor,
            last_game_id_walked=last_game_id_walked,
        )
        session.add(row)
        await session.commit()


async def _seed_progress_row(
    session_maker: async_sessionmaker[AsyncSession], **fields: object
) -> None:
    """Insert the singleton progress row (id=1) with arbitrary field overrides
    (for out-of-order / floor-required gating tests, which need finer control
    than _seed_calibrate_finished's "everything up through calibrate" shape)."""
    async with session_maker() as session:
        session.add(OpeningCacheRepairProgress(id=1, **fields))  # type: ignore[arg-type]
        await session.commit()


async def _get_progress(
    session_maker: async_sessionmaker[AsyncSession],
) -> OpeningCacheRepairProgress | None:
    async with session_maker() as session:
        return await session.get(OpeningCacheRepairProgress, 1)


async def _seed_screen_finished(session_maker: async_sessionmaker[AsyncSession]) -> None:
    """Simulate `screen` having already finished, so `orphans`'s _stage_gate
    passes (orphans gates on screen_finished_at, the nearest tracked
    predecessor -- see _STAGE_ORDER's docstring)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    await _seed_progress_row(
        session_maker,
        seed_started_at=now,
        seed_finished_at=now,
        calibrate_started_at=now,
        calibrate_finished_at=now,
        screen_started_at=now,
        screen_finished_at=now,
    )


async def _seed_screen_finished_with_floor(
    session_maker: async_sessionmaker[AsyncSession], *, confirm_floor: float
) -> None:
    """Simulate `screen` having already finished with `confirm_floor` measured,
    so `confirm`'s _stage_gate passes (confirm gates on screen_finished_at,
    same skip-untracked-predecessor walk as `orphans`) and confirm_floor is
    non-NULL."""
    now = datetime.datetime.now(datetime.timezone.utc)
    await _seed_progress_row(
        session_maker,
        seed_started_at=now,
        seed_finished_at=now,
        calibrate_started_at=now,
        calibrate_finished_at=now,
        screen_started_at=now,
        screen_finished_at=now,
        confirm_floor=confirm_floor,
    )


async def _seed_confirm_finished(session_maker: async_sessionmaker[AsyncSession]) -> None:
    """Simulate `confirm` having already finished, so `propagate`'s _stage_gate
    passes."""
    now = datetime.datetime.now(datetime.timezone.utc)
    await _seed_progress_row(
        session_maker,
        seed_started_at=now,
        seed_finished_at=now,
        calibrate_started_at=now,
        calibrate_finished_at=now,
        screen_started_at=now,
        screen_finished_at=now,
        confirm_started_at=now,
        confirm_finished_at=now,
    )


async def _seed_propagate_finished(session_maker: async_sessionmaker[AsyncSession]) -> None:
    """Simulate `propagate` having already finished, so `rederive`'s
    _stage_gate passes."""
    now = datetime.datetime.now(datetime.timezone.utc)
    await _seed_progress_row(
        session_maker,
        seed_started_at=now,
        seed_finished_at=now,
        calibrate_started_at=now,
        calibrate_finished_at=now,
        screen_started_at=now,
        screen_finished_at=now,
        confirm_started_at=now,
        confirm_finished_at=now,
        propagate_started_at=now,
        propagate_finished_at=now,
    )


async def _insert_game_for_propagate(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    user_id: int = _TEST_USER_ID,
) -> int:
    """A minimal game row for `propagate` tests -- these operate purely on
    `game_positions` rows this helper's caller inserts separately (via
    `_insert_position`), never replaying the PGN, so any legal PGN suffices."""
    async with session_maker() as session:
        game = Game(
            user_id=user_id,
            platform="chess.com",
            platform_game_id=str(uuid.uuid4()),
            pgn=_RUY_LOPEZ_PGN,
            result="1-0",
            user_color="white",
            rated=True,
            is_computer_game=False,
        )
        session.add(game)
        await session.flush()
        game_id = int(game.id)  # type: ignore[arg-type]
        await session.commit()
    return game_id


async def _insert_position(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    user_id: int,
    game_id: int,
    ply: int,
    full_hash: int,
    eval_cp: int | None = None,
    eval_mate: int | None = None,
    best_move: str | None = None,
    pv: str | None = None,
) -> None:
    """Insert one `game_positions` row with explicit values -- `propagate`
    tests need per-ply control `_insert_carrier_game` (real PGN replay, always
    NULL eval_cp/eval_mate) does not provide."""
    async with session_maker() as session:
        session.add(
            GamePosition(
                user_id=user_id,
                game_id=game_id,
                ply=ply,
                full_hash=full_hash,
                white_hash=0,
                black_hash=0,
                phase=0,
                endgame_class=None,
                eval_cp=eval_cp,
                eval_mate=eval_mate,
                best_move=best_move,
                pv=pv,
            )
        )
        await session.commit()


# ---------------------------------------------------------------------------
# `rederive` fixtures -- a real 10-ply game producing a real blunder (ply 2)
# and, optionally, a real mistake (ply 4) from classify_game_flaws (the same
# fixture shape as tests/test_backfill_flaws.py's committed_analyzed_game).
# ---------------------------------------------------------------------------

_REDERIVE_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *"
_REDERIVE_CP_BLUNDER_BEFORE = 200
_REDERIVE_CP_BLUNDER_AFTER = -500
_REDERIVE_CP_MISTAKE_BEFORE = 100
_REDERIVE_CP_MISTAKE_AFTER = -50


async def _insert_rederive_game(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    user_id: int = _TEST_USER_ID,
    include_mistake: bool = True,
) -> int:
    async with session_maker() as session:
        game = Game(
            user_id=user_id,
            platform="lichess",
            platform_game_id=str(uuid.uuid4()),
            pgn=_REDERIVE_PGN,
            result="1-0",
            user_color="white",
            rated=True,
            is_computer_game=False,
        )
        session.add(game)
        await session.flush()
        game_id = int(game.id)  # type: ignore[arg-type]

        cp_values = [20] * 10
        cp_values[1] = _REDERIVE_CP_BLUNDER_BEFORE
        cp_values[2] = _REDERIVE_CP_BLUNDER_AFTER
        if include_mistake:
            cp_values[3] = _REDERIVE_CP_MISTAKE_BEFORE
            cp_values[4] = _REDERIVE_CP_MISTAKE_AFTER

        for ply in range(10):
            eval_cp = cp_values[ply] if ply < 9 else None
            session.add(
                GamePosition(
                    user_id=user_id,
                    game_id=game_id,
                    ply=ply,
                    eval_cp=eval_cp,
                    eval_mate=None,
                    phase=1,
                    full_hash=ply,
                    white_hash=ply,
                    black_hash=ply,
                    endgame_class=None,
                )
            )
        await session.commit()
    return game_id


async def _seed_flaw_rows(
    session_maker: async_sessionmaker[AsyncSession],
    game_id: int,
    user_id: int,
    *,
    plies: set[int] | None = None,
    with_blob: bool = True,
) -> None:
    """Insert `game_flaws` rows for the (subset of the) CURRENT eval data's
    real `classify_game_flaws` result. `plies=None` seeds every flaw the
    fresh classify produces; a narrower `plies` set seeds only those --
    simulating a game reclassified under an OLDER threshold/eval revision
    that had not yet discovered a ply the CURRENT one flags."""
    async with session_maker() as session:
        game = await session.get(Game, game_id)
        assert game is not None
        positions = list(
            (
                await session.execute(
                    select(GamePosition)
                    .where(GamePosition.game_id == game_id, GamePosition.user_id == user_id)
                    .order_by(GamePosition.ply)
                )
            )
            .scalars()
            .all()
        )
        flaw_result = classify_game_flaws(game, positions)
        assert isinstance(flaw_result, list) and flaw_result, "fixture must produce flaws"
        for flaw in flaw_result:
            if plies is not None and flaw["ply"] not in plies:
                continue
            row = flaw_record_to_row(user_id=user_id, game_id=game_id, flaw=flaw)
            if with_blob:
                row["allowed_pv_lines"] = [{"b": 1, "bm": None, "s": None, "sm": None, "su": ""}]
                row["missed_pv_lines"] = [{"b": 2, "bm": None, "s": None, "sm": None, "su": ""}]
                row["allowed_tactic_motif"] = 5
                row["allowed_tactic_piece"] = 1
                row["allowed_tactic_confidence"] = 90
                row["allowed_tactic_depth"] = 1
            session.add(GameFlaw(**row))
        await session.commit()


async def _seed_phantom_flaw(
    session_maker: async_sessionmaker[AsyncSession], game_id: int, user_id: int, ply: int
) -> None:
    """Insert a `game_flaws` row for `ply` that the fresh `classify_game_flaws`
    pass will NOT reproduce (the current eval data flags no drop there) --
    proves rederive's DELETE bucket fires for a ply that is no longer a flaw."""
    async with session_maker() as session:
        session.add(
            GameFlaw(
                user_id=user_id,
                game_id=game_id,
                ply=ply,
                severity=2,
                phase=1,
                is_miss=False,
                is_lucky=False,
                is_reversed=False,
                is_squandered=False,
                fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
            )
        )
        await session.commit()


_LOCK_PROBE_POLL_DEADLINE_S: float = 5.0
_LOCK_PROBE_POLL_INTERVAL_S: float = 0.05
_LOCK_RELEASE_TIMEOUT_S: float = 5.0


async def _advisory_waiter_row_visible(session: AsyncSession, lock_key: int) -> bool:
    """True iff a NOT-granted advisory lock row for `lock_key` is visible in
    pg_locks for the CURRENT database (mirrors tests/services/test_eval_apply.py's
    identical helper -- the database filter is mandatory under `-n auto`, where
    several cloned test databases coexist in the same PostgreSQL cluster)."""
    classid = lock_key >> 32
    objid = lock_key & 0xFFFFFFFF
    result = await session.execute(
        text(
            "SELECT 1 FROM pg_locks "
            "WHERE locktype = 'advisory' AND NOT granted AND objsubid = 1 "
            "AND classid = :classid AND objid = :objid "
            "AND database = (SELECT oid FROM pg_database WHERE datname = current_database())"
        ),
        {"classid": classid, "objid": objid},
    )
    return result.first() is not None


class TestSeed:
    async def test_seed_is_idempotent(self, test_engine: AsyncEngine) -> None:
        """A second `seed` run inserts nothing more once every cache row is audited."""
        session_maker = _session_maker(test_engine)
        full_hash = -900001
        try:
            async with session_maker() as session:
                session.add(OpeningPositionEval(full_hash=full_hash, eval_cp=42, eval_mate=None))
                await session.commit()

            await run_seed(db="dev", dry_run=False, limit=None, session_maker=session_maker)

            async with session_maker() as session:
                audit = await session.get(OpeningCacheAudit, full_hash)
                assert audit is not None
                assert audit.status == "pending"
                assert audit.old_cp == 42

            # Re-run: idempotent, ON CONFLICT DO NOTHING means no new row and
            # the existing row's status is untouched.
            await run_seed(db="dev", dry_run=False, limit=None, session_maker=session_maker)
            async with session_maker() as session:
                count = (
                    (
                        await session.execute(
                            select(OpeningCacheAudit).where(
                                OpeningCacheAudit.full_hash == full_hash
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(count) == 1
        finally:
            await _delete_opening_cache(session_maker, [full_hash])
            await _reset_progress(session_maker)

    async def test_seed_dry_run_writes_nothing(self, test_engine: AsyncEngine) -> None:
        """--dry-run counts candidates but inserts zero audit rows."""
        session_maker = _session_maker(test_engine)
        full_hash = -900002
        try:
            async with session_maker() as session:
                session.add(OpeningPositionEval(full_hash=full_hash, eval_cp=10, eval_mate=None))
                await session.commit()

            await run_seed(db="dev", dry_run=True, limit=None, session_maker=session_maker)

            async with session_maker() as session:
                audit = await session.get(OpeningCacheAudit, full_hash)
                assert audit is None
        finally:
            await _delete_opening_cache(session_maker, [full_hash])
            await _reset_progress(session_maker)


class TestScreen:
    async def test_screen_skips_hash_mismatched_carrier(self, test_engine: AsyncEngine) -> None:
        """A stored hash that doesn't match the replayed board is never sent to the
        engine, and the audit row is left completely unchanged."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        real_hashes = _real_hashes_by_ply(_RUY_LOPEZ_PGN)
        wrong_hash = real_hashes[2] + 12345  # deliberately wrong stored hash at ply 2
        max_game_id = await _current_max_game_id(session_maker)
        game_id = await _insert_carrier_game(session_maker, hash_overrides={2: wrong_hash})
        try:
            async with session_maker() as session:
                session.add(OpeningCacheAudit(full_hash=wrong_hash, status="pending", old_cp=15))
                await session.commit()
            await _seed_calibrate_finished(
                session_maker, screen_floor=0.05, last_game_id_walked=max_game_id
            )

            fake_pool = _FakePool(result_by_fen={})
            await run_screen(
                db="dev",
                dry_run=False,
                limit=None,
                session_maker=session_maker,
                pool=fake_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )

            assert fake_pool.evaluated_fens == []
            async with session_maker() as session:
                audit = await session.get(OpeningCacheAudit, wrong_hash)
                assert audit is not None
                assert audit.status == "pending"
                assert audit.screen_cp is None
                assert audit.screened_at is None
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [wrong_hash])
            await _reset_progress(session_maker)

    async def test_screen_reaches_terminal_position_of_short_game(
        self, test_engine: AsyncEngine
    ) -> None:
        """A cache row carried ONLY as the final position of a game that ended by
        resignation/timeout inside 20 plies must still be screened (Phase 220 dev
        smoke: 94 such rows stayed `pending` forever and `orphans` refused them)."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        game = chess.pgn.read_game(io.StringIO(_RUY_LOPEZ_PGN))
        assert game is not None
        terminal_board = game.end().board()
        terminal_ply = len(list(game.mainline_moves()))
        terminal_hash = compute_hashes(terminal_board)[2]
        max_game_id = await _current_max_game_id(session_maker)
        game_id = await _insert_carrier_game(session_maker)
        try:
            async with session_maker() as session:
                # _insert_carrier_game stores plies 0..N-1; add the terminal row N the
                # import pipeline writes for the position after the last move.
                session.add(
                    GamePosition(
                        user_id=_TEST_USER_ID,
                        game_id=game_id,
                        ply=terminal_ply,
                        full_hash=terminal_hash,
                        white_hash=0,
                        black_hash=0,
                        phase=0,
                        endgame_class=None,
                        eval_cp=None,
                        eval_mate=None,
                    )
                )
                session.add(OpeningCacheAudit(full_hash=terminal_hash, status="pending", old_cp=12))
                await session.commit()
            await _seed_calibrate_finished(
                session_maker, screen_floor=0.05, last_game_id_walked=max_game_id
            )

            fake_pool = _FakePool(result_by_fen={terminal_board.fen(): (10, None)})
            await run_screen(
                db="dev",
                dry_run=False,
                limit=None,
                session_maker=session_maker,
                pool=fake_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )

            assert fake_pool.evaluated_fens == [terminal_board.fen()]
            async with session_maker() as session:
                audit = await session.get(OpeningCacheAudit, terminal_hash)
                assert audit is not None
                assert audit.status == "screened_clean"
                assert audit.sample_game_id == game_id
                assert audit.sample_ply == terminal_ply
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [terminal_hash])
            await _reset_progress(session_maker)

    async def test_screen_clean_flagged_split(self, test_engine: AsyncEngine) -> None:
        """A small delta lands screened_clean; a large delta lands flagged."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        real_hashes = _real_hashes_by_ply(_RUY_LOPEZ_PGN)
        clean_hash = real_hashes[2]
        flagged_hash = real_hashes[4]
        max_game_id = await _current_max_game_id(session_maker)
        game_id = await _insert_carrier_game(session_maker)
        try:
            game = chess.pgn.read_game(io.StringIO(_RUY_LOPEZ_PGN))
            assert game is not None
            board = game.board()
            boards_by_ply: dict[int, chess.Board] = {}
            for ply, node in enumerate(game.mainline()):
                boards_by_ply[ply] = board.copy()
                board.push(node.move)

            # old_cp=0 (equal) for both; clean gets an engine cp close to 0
            # (tiny expected-score delta), flagged gets a large swing.
            async with session_maker() as session:
                session.add(OpeningCacheAudit(full_hash=clean_hash, status="pending", old_cp=0))
                session.add(OpeningCacheAudit(full_hash=flagged_hash, status="pending", old_cp=0))
                await session.commit()
            await _seed_calibrate_finished(
                session_maker, screen_floor=0.05, last_game_id_walked=max_game_id
            )

            fake_pool = _FakePool(
                result_by_fen={
                    boards_by_ply[2].fen(): (2, None),  # tiny delta -> clean
                    boards_by_ply[4].fen(): (600, None),  # huge delta -> flagged
                }
            )
            await run_screen(
                db="dev",
                dry_run=False,
                limit=None,
                session_maker=session_maker,
                pool=fake_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )

            async with session_maker() as session:
                clean_audit = await session.get(OpeningCacheAudit, clean_hash)
                flagged_audit = await session.get(OpeningCacheAudit, flagged_hash)
                assert clean_audit is not None and clean_audit.status == "screened_clean"
                assert flagged_audit is not None and flagged_audit.status == "flagged"
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [clean_hash, flagged_hash])
            await _reset_progress(session_maker)

    async def test_screen_floor_exactly_boundary_is_clean(self, test_engine: AsyncEngine) -> None:
        """A delta exactly equal to screen_floor lands screened_clean (`<=`, not `<`)."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        real_hashes = _real_hashes_by_ply(_RUY_LOPEZ_PGN)
        boundary_hash = real_hashes[2]
        max_game_id = await _current_max_game_id(session_maker)
        game_id = await _insert_carrier_game(session_maker)
        try:
            game = chess.pgn.read_game(io.StringIO(_RUY_LOPEZ_PGN))
            assert game is not None
            board = game.board()
            target_fen: str | None = None
            for ply, node in enumerate(game.mainline()):
                if ply == 2:
                    target_fen = board.fen()
                board.push(node.move)
            assert target_fen is not None

            # old_cp=0, engine cp=0 -> delta_score is EXACTLY 0.0, which must be
            # <= any non-negative screen_floor (use screen_floor=0.0 for the
            # tightest possible boundary).
            async with session_maker() as session:
                session.add(OpeningCacheAudit(full_hash=boundary_hash, status="pending", old_cp=0))
                await session.commit()
            await _seed_calibrate_finished(
                session_maker, screen_floor=0.0, last_game_id_walked=max_game_id
            )

            fake_pool = _FakePool(result_by_fen={target_fen: (0, None)})
            await run_screen(
                db="dev",
                dry_run=False,
                limit=None,
                session_maker=session_maker,
                pool=fake_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )

            async with session_maker() as session:
                audit = await session.get(OpeningCacheAudit, boundary_hash)
                assert audit is not None
                assert audit.delta_score == pytest.approx(0.0)
                assert audit.status == "screened_clean"
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [boundary_hash])
            await _reset_progress(session_maker)

    async def test_screen_out_of_order_refuses(self, test_engine: AsyncEngine) -> None:
        """`screen` refuses to run before `calibrate` has finished, and writes
        nothing (seed_finished_at is set, calibrate_finished_at is not)."""
        session_maker = _session_maker(test_engine)
        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            await _seed_progress_row(session_maker, seed_started_at=now, seed_finished_at=now)
            with pytest.raises(StageOrderError):
                await run_screen(db="dev", dry_run=False, limit=None, session_maker=session_maker)
            progress = await _get_progress(session_maker)
            assert progress is not None
            assert progress.screen_floor is None
        finally:
            await _reset_progress(session_maker)

    async def test_screen_floor_required_refuses(self, test_engine: AsyncEngine) -> None:
        """`screen` refuses when screen_floor is still NULL even though
        calibrate_finished_at is set, and mutates no audit row."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        now = datetime.datetime.now(datetime.timezone.utc)
        max_game_id = await _current_max_game_id(session_maker)
        full_hash = -700001
        game_id = await _insert_carrier_game(session_maker)
        try:
            async with session_maker() as session:
                session.add(OpeningCacheAudit(full_hash=full_hash, status="pending", old_cp=0))
                await session.commit()
            await _seed_progress_row(
                session_maker,
                seed_started_at=now,
                seed_finished_at=now,
                calibrate_started_at=now,
                calibrate_finished_at=now,
                screen_floor=None,
                confirm_floor=None,
                last_game_id_walked=max_game_id,
            )
            with pytest.raises(CalibrationRequiredError):
                await run_screen(db="dev", dry_run=False, limit=None, session_maker=session_maker)
            async with session_maker() as session:
                audit = await session.get(OpeningCacheAudit, full_hash)
                assert audit is not None
                assert audit.status == "pending"
                assert audit.screen_cp is None
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [full_hash])
            await _reset_progress(session_maker)

    async def test_screen_resume_after_cancelled_error(self, test_engine: AsyncEngine) -> None:
        """A CancelledError raised mid-gather leaves the batch's audit rows at
        `pending` and `last_game_id_walked` unchanged; a second run reprocesses
        exactly that batch (no duplication, no skip)."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        real_hashes = _real_hashes_by_ply(_RUY_LOPEZ_PGN)
        hash_a = real_hashes[2]
        hash_b = real_hashes[4]
        max_game_id = await _current_max_game_id(session_maker)
        game_id = await _insert_carrier_game(session_maker)
        try:
            game = chess.pgn.read_game(io.StringIO(_RUY_LOPEZ_PGN))
            assert game is not None
            board = game.board()
            boards_by_ply: dict[int, chess.Board] = {}
            for ply, node in enumerate(game.mainline()):
                boards_by_ply[ply] = board.copy()
                board.push(node.move)

            async with session_maker() as session:
                session.add(OpeningCacheAudit(full_hash=hash_a, status="pending", old_cp=0))
                session.add(OpeningCacheAudit(full_hash=hash_b, status="pending", old_cp=0))
                await session.commit()
            await _seed_calibrate_finished(
                session_maker, screen_floor=0.5, last_game_id_walked=max_game_id
            )

            result_by_fen: dict[str, tuple[int | None, int | None]] = {
                boards_by_ply[2].fen(): (5, None),
                boards_by_ply[4].fen(): (7, None),
            }
            killing_pool = _FakePool(result_by_fen=result_by_fen, raise_on_call=2)
            with pytest.raises(asyncio.CancelledError):
                await run_screen(
                    db="dev",
                    dry_run=False,
                    limit=None,
                    session_maker=session_maker,
                    pool=killing_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
                )

            # Nothing committed: both rows still pending, cursor unchanged.
            async with session_maker() as session:
                audit_a = await session.get(OpeningCacheAudit, hash_a)
                audit_b = await session.get(OpeningCacheAudit, hash_b)
                assert audit_a is not None and audit_a.status == "pending"
                assert audit_b is not None and audit_b.status == "pending"
            progress = await _get_progress(session_maker)
            assert progress is not None
            assert progress.last_game_id_walked == max_game_id

            # Second run, fresh (non-raising) pool: reprocesses exactly this batch.
            fresh_pool = _FakePool(result_by_fen=result_by_fen)
            await run_screen(
                db="dev",
                dry_run=False,
                limit=None,
                session_maker=session_maker,
                pool=fresh_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )
            assert len(fresh_pool.evaluated_fens) == 2
            async with session_maker() as session:
                audit_a = await session.get(OpeningCacheAudit, hash_a)
                audit_b = await session.get(OpeningCacheAudit, hash_b)
                assert audit_a is not None and audit_a.status != "pending"
                assert audit_b is not None and audit_b.status != "pending"
            progress = await _get_progress(session_maker)
            assert progress is not None
            assert progress.last_game_id_walked == game_id
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [hash_a, hash_b])
            await _reset_progress(session_maker)

    async def test_screen_hash_mismatch_after_three_carriers(
        self, test_engine: AsyncEngine
    ) -> None:
        """Three carriers whose replay all mismatch the stored hash escalate the
        row to hash_mismatch after MAX_CARRIERS_PER_HASH attempts; the fake pool
        never saw a board for that hash, and the cache row is untouched."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        real_hashes = _real_hashes_by_ply(_RUY_LOPEZ_PGN)
        wrong_hash = real_hashes[2] + 999_999
        max_game_id = await _current_max_game_id(session_maker)
        game_ids = [
            await _insert_carrier_game(session_maker, hash_overrides={2: wrong_hash})
            for _ in range(MAX_CARRIERS_PER_HASH)
        ]
        try:
            async with session_maker() as session:
                session.add(OpeningPositionEval(full_hash=wrong_hash, eval_cp=15, eval_mate=None))
                session.add(OpeningCacheAudit(full_hash=wrong_hash, status="pending", old_cp=15))
                await session.commit()
            await _seed_calibrate_finished(
                session_maker, screen_floor=0.05, last_game_id_walked=max_game_id
            )

            fake_pool = _FakePool(result_by_fen={})
            await run_screen(
                db="dev",
                dry_run=False,
                limit=None,
                session_maker=session_maker,
                pool=fake_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )

            assert fake_pool.evaluated_fens == []
            async with session_maker() as session:
                audit = await session.get(OpeningCacheAudit, wrong_hash)
                assert audit is not None
                assert audit.status == "hash_mismatch"
                assert audit.hash_mismatch_attempts == MAX_CARRIERS_PER_HASH
                cache_row = await session.get(OpeningPositionEval, wrong_hash)
                assert cache_row is not None
                assert cache_row.eval_cp == 15  # untouched
        finally:
            await _delete_games(session_maker, game_ids)
            await _delete_opening_cache(session_maker, [wrong_hash])
            await _reset_progress(session_maker)

    async def test_screen_carrier_retry_second_correct(self, test_engine: AsyncEngine) -> None:
        """First carrier's replay mismatches; the second (higher game_id)
        carrier replays correctly -> screened_clean with sample_game_id equal
        to the SECOND carrier."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        target_hash = _real_hashes_by_ply(_RUY_LOPEZ_PGN)[2]
        max_game_id = await _current_max_game_id(session_maker)
        # Wrong carrier first (lower game_id): a genuinely different opening
        # whose ply-2 stored hash is falsely overridden to target_hash.
        wrong_game_id = await _insert_carrier_game(
            session_maker, pgn=_SICILIAN_PGN, hash_overrides={2: target_hash}
        )
        # Correct carrier second (higher game_id): its OWN real ply-2 hash
        # naturally equals target_hash, no override needed.
        correct_game_id = await _insert_carrier_game(session_maker, pgn=_RUY_LOPEZ_PGN)
        assert wrong_game_id < correct_game_id
        try:
            game = chess.pgn.read_game(io.StringIO(_RUY_LOPEZ_PGN))
            assert game is not None
            board = game.board()
            target_fen: str | None = None
            for ply, node in enumerate(game.mainline()):
                if ply == 2:
                    target_fen = board.fen()
                board.push(node.move)
            assert target_fen is not None

            async with session_maker() as session:
                session.add(OpeningCacheAudit(full_hash=target_hash, status="pending", old_cp=0))
                await session.commit()
            await _seed_calibrate_finished(
                session_maker, screen_floor=0.5, last_game_id_walked=max_game_id
            )

            fake_pool = _FakePool(result_by_fen={target_fen: (5, None)})
            await run_screen(
                db="dev",
                dry_run=False,
                limit=None,
                session_maker=session_maker,
                pool=fake_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )

            assert fake_pool.evaluated_fens == [target_fen]
            async with session_maker() as session:
                audit = await session.get(OpeningCacheAudit, target_hash)
                assert audit is not None
                assert audit.status == "screened_clean"
                assert audit.sample_game_id == correct_game_id
        finally:
            await _delete_games(session_maker, [wrong_game_id, correct_game_id])
            await _delete_opening_cache(session_maker, [target_hash])
            await _reset_progress(session_maker)

    async def test_screen_cursor_advances_across_two_batches(
        self, test_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With SCREEN_GAMES_PER_BATCH forced to 1, two games are walked as two
        separate batches; both get screened and the cursor ends at the SECOND
        (higher) game_id, proving the walk looped past the first batch."""
        import scripts.opening_cache_repair as ocr_module

        monkeypatch.setattr(ocr_module, "SCREEN_GAMES_PER_BATCH", 1)

        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        hash_a = _real_hashes_by_ply(_RUY_LOPEZ_PGN)[2]
        hash_b = _real_hashes_by_ply(_SICILIAN_PGN)[2]
        max_game_id = await _current_max_game_id(session_maker)
        game_a = await _insert_carrier_game(session_maker, pgn=_RUY_LOPEZ_PGN)
        game_b = await _insert_carrier_game(session_maker, pgn=_SICILIAN_PGN)
        assert game_a < game_b
        try:

            def _fen_at_ply2(pgn: str) -> str:
                game = chess.pgn.read_game(io.StringIO(pgn))
                assert game is not None
                board = game.board()
                fen: str | None = None
                for ply, node in enumerate(game.mainline()):
                    if ply == 2:
                        fen = board.fen()
                    board.push(node.move)
                assert fen is not None
                return fen

            fen_a = _fen_at_ply2(_RUY_LOPEZ_PGN)
            fen_b = _fen_at_ply2(_SICILIAN_PGN)

            async with session_maker() as session:
                session.add(OpeningCacheAudit(full_hash=hash_a, status="pending", old_cp=0))
                session.add(OpeningCacheAudit(full_hash=hash_b, status="pending", old_cp=0))
                await session.commit()
            await _seed_calibrate_finished(
                session_maker, screen_floor=0.5, last_game_id_walked=max_game_id
            )

            fake_pool = _FakePool(result_by_fen={fen_a: (2, None), fen_b: (2, None)})
            await run_screen(
                db="dev",
                dry_run=False,
                limit=None,
                session_maker=session_maker,
                pool=fake_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )

            assert set(fake_pool.evaluated_fens) == {fen_a, fen_b}
            async with session_maker() as session:
                audit_a = await session.get(OpeningCacheAudit, hash_a)
                audit_b = await session.get(OpeningCacheAudit, hash_b)
                assert audit_a is not None and audit_a.status == "screened_clean"
                assert audit_b is not None and audit_b.status == "screened_clean"
            progress = await _get_progress(session_maker)
            assert progress is not None
            assert progress.last_game_id_walked == game_b
        finally:
            await _delete_games(session_maker, [game_a, game_b])
            await _delete_opening_cache(session_maker, [hash_a, hash_b])
            await _reset_progress(session_maker)

    async def test_screen_screens_every_game_in_one_batch(self, test_engine: AsyncEngine) -> None:
        """Two carrier games in the SAME batch (default SCREEN_GAMES_PER_BATCH,
        no monkeypatch) both get screened.

        Guards the batched read phase: `_collect_screen_candidates` resolves the
        page's PGNs, ply rows and pending-hash filter with one query each, so a
        scoping bug that built any of those from only the first game of the page
        would leave later games' hashes silently `pending`. The
        SCREEN_GAMES_PER_BATCH=1 sibling test cannot catch that -- it puts each
        game in its own batch, where first-game-only scoping is indistinguishable
        from correct behaviour.
        """
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        hash_a = _real_hashes_by_ply(_RUY_LOPEZ_PGN)[2]
        hash_b = _real_hashes_by_ply(_SICILIAN_PGN)[2]
        max_game_id = await _current_max_game_id(session_maker)
        game_a = await _insert_carrier_game(session_maker, pgn=_RUY_LOPEZ_PGN)
        game_b = await _insert_carrier_game(session_maker, pgn=_SICILIAN_PGN)
        assert game_a < game_b
        try:

            def _fen_at_ply2(pgn: str) -> str:
                game = chess.pgn.read_game(io.StringIO(pgn))
                assert game is not None
                board = game.board()
                fen: str | None = None
                for ply, node in enumerate(game.mainline()):
                    if ply == 2:
                        fen = board.fen()
                    board.push(node.move)
                assert fen is not None
                return fen

            fen_a = _fen_at_ply2(_RUY_LOPEZ_PGN)
            fen_b = _fen_at_ply2(_SICILIAN_PGN)

            async with session_maker() as session:
                session.add(OpeningCacheAudit(full_hash=hash_a, status="pending", old_cp=0))
                session.add(OpeningCacheAudit(full_hash=hash_b, status="pending", old_cp=0))
                await session.commit()
            await _seed_calibrate_finished(
                session_maker, screen_floor=0.5, last_game_id_walked=max_game_id
            )

            fake_pool = _FakePool(result_by_fen={fen_a: (2, None), fen_b: (2, None)})
            await run_screen(
                db="dev",
                dry_run=False,
                limit=None,
                session_maker=session_maker,
                pool=fake_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )

            # Both games sat in ONE batch (SCREEN_GAMES_PER_BATCH is 200), so a
            # first-game-only read phase would evaluate fen_a and leave hash_b pending.
            assert set(fake_pool.evaluated_fens) == {fen_a, fen_b}
            async with session_maker() as session:
                audit_a = await session.get(OpeningCacheAudit, hash_a)
                audit_b = await session.get(OpeningCacheAudit, hash_b)
                assert audit_a is not None and audit_a.status == "screened_clean"
                assert audit_b is not None and audit_b.status == "screened_clean"
                assert audit_a.sample_game_id == game_a
                assert audit_b.sample_game_id == game_b
        finally:
            await _delete_games(session_maker, [game_a, game_b])
            await _delete_opening_cache(session_maker, [hash_a, hash_b])
            await _reset_progress(session_maker)

    async def test_screen_stamps_started_and_finished_at_on_exhaustion(
        self, test_engine: AsyncEngine
    ) -> None:
        """`screen` stamps its own screen_started_at/screen_finished_at when the
        id-ASC walk exhausts (no --limit truncation) -- required for `orphans`
        and a future `confirm` stage to ever pass their own stage gate."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        full_hash = _real_hashes_by_ply(_RUY_LOPEZ_PGN)[2]
        max_game_id = await _current_max_game_id(session_maker)
        game_id = await _insert_carrier_game(session_maker)
        try:
            game = chess.pgn.read_game(io.StringIO(_RUY_LOPEZ_PGN))
            assert game is not None
            board = game.board()
            target_fen: str | None = None
            for ply, node in enumerate(game.mainline()):
                if ply == 2:
                    target_fen = board.fen()
                board.push(node.move)
            assert target_fen is not None

            async with session_maker() as session:
                session.add(OpeningCacheAudit(full_hash=full_hash, status="pending", old_cp=0))
                await session.commit()
            await _seed_calibrate_finished(
                session_maker, screen_floor=0.5, last_game_id_walked=max_game_id
            )

            fake_pool = _FakePool(result_by_fen={target_fen: (2, None)})
            await run_screen(
                db="dev",
                dry_run=False,
                limit=None,
                session_maker=session_maker,
                pool=fake_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )

            progress = await _get_progress(session_maker)
            assert progress is not None
            assert progress.screen_started_at is not None
            assert progress.screen_finished_at is not None
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [full_hash])
            await _reset_progress(session_maker)


class TestCalibrate:
    async def test_calibrate_out_of_order_refuses(self, test_engine: AsyncEngine) -> None:
        """`calibrate` refuses to run before `seed` has finished, and writes
        nothing -- the gate raises inside the same (never-committed)
        transaction that would have lazily created the progress row, so
        nothing persists at all."""
        session_maker = _session_maker(test_engine)
        try:
            with pytest.raises(StageOrderError):
                await run_calibrate(
                    db="dev", dry_run=False, limit=None, session_maker=session_maker
                )
            progress = await _get_progress(session_maker)
            assert progress is None
        finally:
            await _reset_progress(session_maker)

    async def test_calibrate_limit_zero_does_not_stamp_started_at(
        self, test_engine: AsyncEngine
    ) -> None:
        """--limit 0 touches no DB row at all -- not even the progress row."""
        session_maker = _session_maker(test_engine)
        try:
            await run_calibrate(db="dev", dry_run=False, limit=0, session_maker=session_maker)
            progress = await _get_progress(session_maker)
            assert progress is None
        finally:
            await _reset_progress(session_maker)

    async def test_calibrate_zero_eligible_raises(self, test_engine: AsyncEngine) -> None:
        """Zero eligible known-clean rows leaves both floors NULL and raises."""
        session_maker = _session_maker(test_engine)
        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            await _seed_progress_row(session_maker, seed_started_at=now, seed_finished_at=now)
            with pytest.raises(CalibrationSampleEmptyError):
                await run_calibrate(
                    db="dev", dry_run=False, limit=None, session_maker=session_maker
                )
            progress = await _get_progress(session_maker)
            assert progress is not None
            assert progress.screen_floor is None
            assert progress.confirm_floor is None
        finally:
            await _reset_progress(session_maker)

    async def test_calibrate_dry_run_writes_nothing(self, test_engine: AsyncEngine) -> None:
        """--dry-run computes and prints the sample size without writing the floors."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        now = datetime.datetime.now(datetime.timezone.utc)
        clean_after = datetime.datetime(2026, 8, 21, tzinfo=datetime.timezone.utc)
        real_hashes = _real_hashes_by_ply(_RUY_LOPEZ_PGN)
        full_hash = real_hashes[2]
        game_id = await _insert_carrier_game(
            session_maker,
            full_evals_completed_at=clean_after,
            lichess_evals_at=None,
        )
        try:
            async with session_maker() as session:
                session.add(OpeningCacheAudit(full_hash=full_hash, status="pending", old_cp=0))
                await session.commit()
            await _seed_progress_row(session_maker, seed_started_at=now, seed_finished_at=now)
            fake_pool = _FakePool(result_by_fen={})
            await run_calibrate(
                db="dev",
                dry_run=True,
                limit=None,
                session_maker=session_maker,
                pool=fake_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )
            progress = await _get_progress(session_maker)
            assert progress is not None
            assert progress.screen_floor is None
            assert progress.calibrate_finished_at is None
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [full_hash])
            await _reset_progress(session_maker)

    async def test_calibrate_measures_floors(self, test_engine: AsyncEngine) -> None:
        """screen_floor/confirm_floor are written as the nearest-rank p99 of the
        depth-15/1M-node expected-score deltas over a 2-row known-clean sample
        (n=2 -> p99 picks the larger of the two deltas)."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        now = datetime.datetime.now(datetime.timezone.utc)
        clean_after = datetime.datetime(2026, 8, 21, tzinfo=datetime.timezone.utc)
        real_hashes = _real_hashes_by_ply(_RUY_LOPEZ_PGN)
        hash_small = real_hashes[2]
        hash_large = real_hashes[4]
        game_id = await _insert_carrier_game(
            session_maker,
            full_evals_completed_at=clean_after,
            lichess_evals_at=None,
        )
        try:
            game = chess.pgn.read_game(io.StringIO(_RUY_LOPEZ_PGN))
            assert game is not None
            board = game.board()
            boards_by_ply: dict[int, chess.Board] = {}
            for ply, node in enumerate(game.mainline()):
                boards_by_ply[ply] = board.copy()
                board.push(node.move)

            async with session_maker() as session:
                session.add(OpeningCacheAudit(full_hash=hash_small, status="pending", old_cp=0))
                session.add(OpeningCacheAudit(full_hash=hash_large, status="pending", old_cp=0))
                await session.commit()
            await _seed_progress_row(session_maker, seed_started_at=now, seed_finished_at=now)

            depth_result: dict[str, tuple[int | None, int | None]] = {
                boards_by_ply[2].fen(): (5, None),
                boards_by_ply[4].fen(): (50, None),
            }
            full_result: dict[str, tuple[int | None, int | None, str | None, str | None]] = {
                boards_by_ply[2].fen(): (3, None, "e2e4", "e2e4 e7e5"),
                boards_by_ply[4].fen(): (30, None, "e2e4", "e2e4 e7e5"),
            }
            fake_pool = _FakePool(result_by_fen=depth_result, full_result_by_fen=full_result)
            await run_calibrate(
                db="dev",
                dry_run=False,
                limit=None,
                n=500,
                session_maker=session_maker,
                pool=fake_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )

            expected_screen_floor = abs(eval_cp_to_expected_score(50, "white") - 0.5)
            expected_confirm_floor = abs(eval_cp_to_expected_score(30, "white") - 0.5)
            progress = await _get_progress(session_maker)
            assert progress is not None
            assert progress.calibration_n == 2
            assert progress.screen_floor == pytest.approx(expected_screen_floor)
            assert progress.confirm_floor == pytest.approx(expected_confirm_floor)
            assert progress.calibrated_at is not None
            assert progress.engine_version is not None
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [hash_small, hash_large])
            await _reset_progress(session_maker)

    async def test_calibrate_fewer_than_n_uses_available(self, test_engine: AsyncEngine) -> None:
        """Requesting far more than the eligible population records the real
        (smaller) calibration_n rather than the requested n."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        now = datetime.datetime.now(datetime.timezone.utc)
        clean_after = datetime.datetime(2026, 8, 21, tzinfo=datetime.timezone.utc)
        real_hashes = _real_hashes_by_ply(_RUY_LOPEZ_PGN)
        full_hash = real_hashes[2]
        game_id = await _insert_carrier_game(
            session_maker,
            full_evals_completed_at=clean_after,
            lichess_evals_at=None,
        )
        try:
            game = chess.pgn.read_game(io.StringIO(_RUY_LOPEZ_PGN))
            assert game is not None
            board = game.board()
            target_fen: str | None = None
            for ply, node in enumerate(game.mainline()):
                if ply == 2:
                    target_fen = board.fen()
                board.push(node.move)
            assert target_fen is not None

            async with session_maker() as session:
                session.add(OpeningCacheAudit(full_hash=full_hash, status="pending", old_cp=0))
                await session.commit()
            await _seed_progress_row(session_maker, seed_started_at=now, seed_finished_at=now)

            fake_pool = _FakePool(
                result_by_fen={target_fen: (5, None)},
                full_result_by_fen={target_fen: (3, None, "e2e4", "e2e4 e7e5")},
            )
            await run_calibrate(
                db="dev",
                dry_run=False,
                limit=None,
                n=CALIBRATION_DEFAULT_N,
                session_maker=session_maker,
                pool=fake_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )
            progress = await _get_progress(session_maker)
            assert progress is not None
            assert progress.calibration_n == 1
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [full_hash])
            await _reset_progress(session_maker)


class TestOrphans:
    async def test_orphans_dry_run_reports_and_deletes_nothing(
        self, test_engine: AsyncEngine
    ) -> None:
        """--dry-run reports the orphan count/sample and deletes nothing."""
        session_maker = _session_maker(test_engine)
        full_hash = -800001
        try:
            async with session_maker() as session:
                session.add(OpeningPositionEval(full_hash=full_hash, eval_cp=10, eval_mate=None))
                session.add(OpeningCacheAudit(full_hash=full_hash, status="pending", old_cp=10))
                await session.commit()
            await _seed_screen_finished(session_maker)

            await run_orphans(db="dev", dry_run=True, limit=None, session_maker=session_maker)

            async with session_maker() as session:
                audit = await session.get(OpeningCacheAudit, full_hash)
                assert audit is not None
                assert audit.status == "pending"
                cache_row = await session.get(OpeningPositionEval, full_hash)
                assert cache_row is not None
        finally:
            await _delete_opening_cache(session_maker, [full_hash])
            await _reset_progress(session_maker)

    async def test_orphans_deletes_hashless_rows(self, test_engine: AsyncEngine) -> None:
        """A pending row with NO game_positions carrier anywhere is marked
        orphan and its cache row is deleted."""
        session_maker = _session_maker(test_engine)
        full_hash = -800002
        try:
            async with session_maker() as session:
                session.add(OpeningPositionEval(full_hash=full_hash, eval_cp=10, eval_mate=None))
                session.add(OpeningCacheAudit(full_hash=full_hash, status="pending", old_cp=10))
                await session.commit()
            await _seed_screen_finished(session_maker)

            await run_orphans(db="dev", dry_run=False, limit=None, session_maker=session_maker)

            async with session_maker() as session:
                audit = await session.get(OpeningCacheAudit, full_hash)
                assert audit is not None
                assert audit.status == "orphan"
                cache_row = await session.get(OpeningPositionEval, full_hash)
                assert cache_row is None
        finally:
            await _delete_opening_cache(session_maker, [full_hash])
            await _reset_progress(session_maker)

    async def test_orphans_lichess_carrier_not_orphan(self, test_engine: AsyncEngine) -> None:
        """A cache row whose ONLY carrier is a lichess game is NOT marked
        orphan -- the board is a legitimate source even though its eval is
        never read (Pitfall 6)."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        real_hashes = _real_hashes_by_ply(_RUY_LOPEZ_PGN)
        full_hash = real_hashes[2]
        game_id = await _insert_carrier_game(
            session_maker, pgn=_RUY_LOPEZ_PGN, lichess_evals_at=None
        )
        try:
            async with session_maker() as session:
                game = await session.get(Game, game_id)
                assert game is not None
                assert game.platform == "lichess"  # _insert_carrier_game's default
                session.add(OpeningCacheAudit(full_hash=full_hash, status="pending", old_cp=0))
                await session.commit()
            await _seed_screen_finished(session_maker)

            await run_orphans(db="dev", dry_run=False, limit=None, session_maker=session_maker)

            async with session_maker() as session:
                audit = await session.get(OpeningCacheAudit, full_hash)
                assert audit is not None
                assert audit.status == "pending"  # NOT orphan -- a carrier exists
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [full_hash])
            await _reset_progress(session_maker)


class TestConfirm:
    """CACHEFIX-04: `confirm` re-evaluates `flagged` rows at the drain's own
    1M-node budget and overwrites the cache row only on the `confirmed_bad`
    branch."""

    def test_confirm_boundary(self) -> None:
        """A delta exactly equal to confirm_floor is confirmed_clean (`<=`);
        the smallest float step above is confirmed_bad. Tested directly
        against `_apply_confirm_fields` (pure function) -- no DB/engine
        needed for a boundary check on the comparison itself."""
        delta = abs(eval_cp_to_expected_score(50, "white") - 0.5)

        audit_clean = OpeningCacheAudit(full_hash=1, status="flagged", old_cp=0, old_mate=None)
        is_bad = _apply_confirm_fields(
            audit_clean,
            full_cp=50,
            full_mate=None,
            full_best_move=None,
            full_pv=None,
            confirm_floor=delta,
        )
        assert is_bad is False
        assert audit_clean.status == "confirmed_clean"

        audit_bad = OpeningCacheAudit(full_hash=2, status="flagged", old_cp=0, old_mate=None)
        smaller_floor = math.nextafter(delta, -math.inf)
        is_bad2 = _apply_confirm_fields(
            audit_bad,
            full_cp=50,
            full_mate=None,
            full_best_move=None,
            full_pv=None,
            confirm_floor=smaller_floor,
        )
        assert is_bad2 is True
        assert audit_bad.status == "confirmed_bad"

    def test_confirm_mate_mismatch(self) -> None:
        """Mate on one side and cp on the other is confirmed_bad regardless
        of the delta -- a huge confirm_floor would otherwise read 'clean'."""
        audit = OpeningCacheAudit(full_hash=3, status="flagged", old_cp=0, old_mate=None)
        is_bad = _apply_confirm_fields(
            audit,
            full_cp=None,
            full_mate=5,
            full_best_move=None,
            full_pv=None,
            confirm_floor=1.0,
        )
        assert is_bad is True
        assert audit.status == "confirmed_bad"

    async def test_confirm_bad_overwrites(self, test_engine: AsyncEngine) -> None:
        """A flagged row whose 1M-node delta exceeds confirm_floor becomes
        confirmed_bad and its cache row's eval_cp/best_move are overwritten
        from the fresh 4-tuple."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        real_hashes = _real_hashes_by_ply(_RUY_LOPEZ_PGN)
        full_hash = real_hashes[2]
        game_id = await _insert_carrier_game(session_maker)
        try:
            game = chess.pgn.read_game(io.StringIO(_RUY_LOPEZ_PGN))
            assert game is not None
            board = game.board()
            target_fen: str | None = None
            for ply, node in enumerate(game.mainline()):
                if ply == 2:
                    target_fen = board.fen()
                board.push(node.move)
            assert target_fen is not None

            async with session_maker() as session:
                session.add(OpeningPositionEval(full_hash=full_hash, eval_cp=0, eval_mate=None))
                session.add(
                    OpeningCacheAudit(
                        full_hash=full_hash,
                        status="flagged",
                        old_cp=0,
                        old_mate=None,
                        sample_game_id=game_id,
                        sample_ply=2,
                    )
                )
                await session.commit()
            await _seed_screen_finished_with_floor(session_maker, confirm_floor=0.05)

            fake_pool = _FakePool(
                result_by_fen={},
                full_result_by_fen={target_fen: (600, None, "e2e4", "e2e4 e7e5")},
            )
            await run_confirm(
                db="dev",
                dry_run=False,
                limit=None,
                session_maker=session_maker,
                pool=fake_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )

            async with session_maker() as session:
                audit = await session.get(OpeningCacheAudit, full_hash)
                assert audit is not None
                assert audit.status == "confirmed_bad"
                assert audit.full_cp == 600
                cache_row = await session.get(OpeningPositionEval, full_hash)
                assert cache_row is not None
                assert cache_row.eval_cp == 600
                assert cache_row.best_move == "e2e4"
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [full_hash])
            await _reset_progress(session_maker)

    async def test_confirm_clean_untouched(self, test_engine: AsyncEngine) -> None:
        """A flagged row whose delta is within confirm_floor becomes
        confirmed_clean and its cache row is byte-identical afterwards."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        real_hashes = _real_hashes_by_ply(_RUY_LOPEZ_PGN)
        full_hash = real_hashes[2]
        game_id = await _insert_carrier_game(session_maker)
        try:
            game = chess.pgn.read_game(io.StringIO(_RUY_LOPEZ_PGN))
            assert game is not None
            board = game.board()
            target_fen: str | None = None
            for ply, node in enumerate(game.mainline()):
                if ply == 2:
                    target_fen = board.fen()
                board.push(node.move)
            assert target_fen is not None

            async with session_maker() as session:
                session.add(OpeningPositionEval(full_hash=full_hash, eval_cp=0, eval_mate=None))
                session.add(
                    OpeningCacheAudit(
                        full_hash=full_hash,
                        status="flagged",
                        old_cp=0,
                        old_mate=None,
                        sample_game_id=game_id,
                        sample_ply=2,
                    )
                )
                await session.commit()
            await _seed_screen_finished_with_floor(session_maker, confirm_floor=0.5)

            fake_pool = _FakePool(
                result_by_fen={},
                full_result_by_fen={target_fen: (2, None, None, None)},
            )
            await run_confirm(
                db="dev",
                dry_run=False,
                limit=None,
                session_maker=session_maker,
                pool=fake_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )

            async with session_maker() as session:
                audit = await session.get(OpeningCacheAudit, full_hash)
                assert audit is not None
                assert audit.status == "confirmed_clean"
                cache_row = await session.get(OpeningPositionEval, full_hash)
                assert cache_row is not None
                assert cache_row.eval_cp == 0
                assert cache_row.best_move is None
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [full_hash])
            await _reset_progress(session_maker)

    async def test_confirm_empty(self, test_engine: AsyncEngine) -> None:
        """confirm with zero flagged rows stamps confirm_finished_at and
        exits 0 (no exception)."""
        session_maker = _session_maker(test_engine)
        try:
            await _seed_screen_finished_with_floor(session_maker, confirm_floor=0.05)
            fake_pool = _FakePool(result_by_fen={})
            await run_confirm(
                db="dev",
                dry_run=False,
                limit=None,
                session_maker=session_maker,
                pool=fake_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )
            progress = await _get_progress(session_maker)
            assert progress is not None
            assert progress.confirm_finished_at is not None
        finally:
            await _reset_progress(session_maker)

    async def test_confirm_order(self, test_engine: AsyncEngine) -> None:
        """flagged rows are loaded in full_hash ASC order."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        real_hashes = _real_hashes_by_ply(_RUY_LOPEZ_PGN)
        hash_a = real_hashes[2]
        hash_b = real_hashes[4]
        game_id = await _insert_carrier_game(session_maker)
        try:
            async with session_maker() as session:
                session.add(
                    OpeningCacheAudit(
                        full_hash=hash_a,
                        status="flagged",
                        old_cp=0,
                        old_mate=None,
                        sample_game_id=game_id,
                        sample_ply=2,
                    )
                )
                session.add(
                    OpeningCacheAudit(
                        full_hash=hash_b,
                        status="flagged",
                        old_cp=0,
                        old_mate=None,
                        sample_game_id=game_id,
                        sample_ply=4,
                    )
                )
                await session.commit()

            candidates, mismatches = await _collect_confirm_candidates(session_maker, 500)
            assert mismatches == []
            ordered_hashes = [c[0] for c in candidates]
            assert ordered_hashes == sorted(ordered_hashes)
            assert set(ordered_hashes) == {hash_a, hash_b}
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [hash_a, hash_b])
            await _reset_progress(session_maker)

    async def test_confirm_dry_run(self, test_engine: AsyncEngine) -> None:
        """--dry-run writes neither an audit transition nor a cache row."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        real_hashes = _real_hashes_by_ply(_RUY_LOPEZ_PGN)
        full_hash = real_hashes[2]
        game_id = await _insert_carrier_game(session_maker)
        try:
            async with session_maker() as session:
                session.add(OpeningPositionEval(full_hash=full_hash, eval_cp=0, eval_mate=None))
                session.add(
                    OpeningCacheAudit(
                        full_hash=full_hash,
                        status="flagged",
                        old_cp=0,
                        old_mate=None,
                        sample_game_id=game_id,
                        sample_ply=2,
                    )
                )
                await session.commit()
            await _seed_screen_finished_with_floor(session_maker, confirm_floor=0.01)

            fake_pool = _FakePool(result_by_fen={})
            await run_confirm(
                db="dev",
                dry_run=True,
                limit=None,
                session_maker=session_maker,
                pool=fake_pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )

            async with session_maker() as session:
                audit = await session.get(OpeningCacheAudit, full_hash)
                assert audit is not None
                assert audit.status == "flagged"
                assert audit.confirmed_at is None
                cache_row = await session.get(OpeningPositionEval, full_hash)
                assert cache_row is not None
                assert cache_row.eval_cp == 0
            progress = await _get_progress(session_maker)
            assert progress is not None
            assert progress.confirm_started_at is None
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [full_hash])
            await _reset_progress(session_maker)


class TestPropagate:
    """CACHEFIX-05: `propagate` rewrites only carrier `game_positions` rows
    that still hold a `confirmed_bad` audit row's exact OLD cached value, on
    the correct side of the post-move shift."""

    async def test_propagate_predicate(self, test_engine: AsyncEngine) -> None:
        """A carrier holding a different value is untouched; a matching one
        is rewritten; NULL-mate-both-sides matches; NULL-on-one-side does
        not."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        target_hash = 555_001
        mate_hash = 555_002
        game_match = await _insert_game_for_propagate(session_maker)
        game_mismatch = await _insert_game_for_propagate(session_maker)
        game_mate_match = await _insert_game_for_propagate(session_maker)
        game_mate_mismatch = await _insert_game_for_propagate(session_maker)
        try:
            # cp predicate: matching carrier rewritten, differing one untouched.
            await _insert_position(
                session_maker,
                user_id=_TEST_USER_ID,
                game_id=game_match,
                ply=2,
                full_hash=11,
                eval_cp=0,
                eval_mate=None,
            )
            await _insert_position(
                session_maker,
                user_id=_TEST_USER_ID,
                game_id=game_match,
                ply=3,
                full_hash=target_hash,
            )
            await _insert_position(
                session_maker,
                user_id=_TEST_USER_ID,
                game_id=game_mismatch,
                ply=2,
                full_hash=12,
                eval_cp=999,
                eval_mate=None,
            )
            await _insert_position(
                session_maker,
                user_id=_TEST_USER_ID,
                game_id=game_mismatch,
                ply=3,
                full_hash=target_hash,
            )

            # mate predicate: NULL-NULL matches; NULL-vs-non-NULL does not,
            # even though eval_cp alone would match.
            await _insert_position(
                session_maker,
                user_id=_TEST_USER_ID,
                game_id=game_mate_match,
                ply=2,
                full_hash=13,
                eval_cp=0,
                eval_mate=None,
            )
            await _insert_position(
                session_maker,
                user_id=_TEST_USER_ID,
                game_id=game_mate_match,
                ply=3,
                full_hash=mate_hash,
            )
            await _insert_position(
                session_maker,
                user_id=_TEST_USER_ID,
                game_id=game_mate_mismatch,
                ply=2,
                full_hash=14,
                eval_cp=0,
                eval_mate=7,
            )
            await _insert_position(
                session_maker,
                user_id=_TEST_USER_ID,
                game_id=game_mate_mismatch,
                ply=3,
                full_hash=mate_hash,
            )

            async with session_maker() as session:
                session.add(
                    OpeningCacheAudit(
                        full_hash=target_hash,
                        status="confirmed_bad",
                        old_cp=0,
                        old_mate=None,
                        full_cp=250,
                        full_mate=None,
                    )
                )
                session.add(
                    OpeningCacheAudit(
                        full_hash=mate_hash,
                        status="confirmed_bad",
                        old_cp=0,
                        old_mate=None,
                        full_cp=300,
                        full_mate=None,
                    )
                )
                await session.commit()
            await _seed_confirm_finished(session_maker)

            await run_propagate(db="dev", dry_run=False, limit=None, session_maker=session_maker)

            async with session_maker() as session:
                matched = (
                    await session.execute(
                        select(GamePosition.eval_cp).where(
                            GamePosition.game_id == game_match, GamePosition.ply == 2
                        )
                    )
                ).scalar_one()
                assert matched == 250

                unmatched = (
                    await session.execute(
                        select(GamePosition.eval_cp).where(
                            GamePosition.game_id == game_mismatch, GamePosition.ply == 2
                        )
                    )
                ).scalar_one()
                assert unmatched == 999

                mate_matched = (
                    await session.execute(
                        select(GamePosition.eval_cp).where(
                            GamePosition.game_id == game_mate_match, GamePosition.ply == 2
                        )
                    )
                ).scalar_one()
                assert mate_matched == 300

                mate_unmatched = (
                    await session.execute(
                        select(GamePosition.eval_cp).where(
                            GamePosition.game_id == game_mate_mismatch, GamePosition.ply == 2
                        )
                    )
                ).scalar_one()
                assert mate_unmatched == 0
        finally:
            await _delete_games(
                session_maker,
                [game_match, game_mismatch, game_mate_match, game_mate_mismatch],
            )
            await _delete_opening_cache(session_maker, [target_hash, mate_hash])
            await _reset_progress(session_maker)

    async def test_propagate_shift(self, test_engine: AsyncEngine) -> None:
        """The eval lands on `n.ply - 1`; `best_move` on row `n` is rewritten
        only when it equalled `old_best_move`."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        target_hash = 555_010
        game_match = await _insert_game_for_propagate(session_maker)
        game_mismatch = await _insert_game_for_propagate(session_maker)
        try:
            await _insert_position(
                session_maker,
                user_id=_TEST_USER_ID,
                game_id=game_match,
                ply=2,
                full_hash=21,
                eval_cp=0,
                eval_mate=None,
            )
            await _insert_position(
                session_maker,
                user_id=_TEST_USER_ID,
                game_id=game_match,
                ply=3,
                full_hash=target_hash,
                best_move="e2e4",
            )
            await _insert_position(
                session_maker,
                user_id=_TEST_USER_ID,
                game_id=game_mismatch,
                ply=2,
                full_hash=22,
                eval_cp=0,
                eval_mate=None,
            )
            await _insert_position(
                session_maker,
                user_id=_TEST_USER_ID,
                game_id=game_mismatch,
                ply=3,
                full_hash=target_hash,
                best_move="g1f3",
            )

            async with session_maker() as session:
                session.add(
                    OpeningCacheAudit(
                        full_hash=target_hash,
                        status="confirmed_bad",
                        old_cp=0,
                        old_mate=None,
                        full_cp=400,
                        full_mate=None,
                        old_best_move="e2e4",
                        full_best_move="d2d4",
                    )
                )
                await session.commit()
            await _seed_confirm_finished(session_maker)

            await run_propagate(db="dev", dry_run=False, limit=None, session_maker=session_maker)

            async with session_maker() as session:
                eval_match = (
                    await session.execute(
                        select(GamePosition.eval_cp).where(
                            GamePosition.game_id == game_match, GamePosition.ply == 2
                        )
                    )
                ).scalar_one()
                assert eval_match == 400  # shifted onto n.ply - 1

                bm_match = (
                    await session.execute(
                        select(GamePosition.best_move).where(
                            GamePosition.game_id == game_match, GamePosition.ply == 3
                        )
                    )
                ).scalar_one()
                assert bm_match == "d2d4"  # rewritten on row n -- old_best_move matched

                bm_mismatch = (
                    await session.execute(
                        select(GamePosition.best_move).where(
                            GamePosition.game_id == game_mismatch, GamePosition.ply == 3
                        )
                    )
                ).scalar_one()
                assert bm_mismatch == "g1f3"  # untouched -- did not match old_best_move
        finally:
            await _delete_games(session_maker, [game_match, game_mismatch])
            await _delete_opening_cache(session_maker, [target_hash])
            await _reset_progress(session_maker)

    async def test_propagate_idempotent(self, test_engine: AsyncEngine) -> None:
        """A second application of the propagate predicate over the SAME hash
        rewrites zero rows and raises no PK violation on the repair-row
        trail (ON CONFLICT DO NOTHING)."""
        from scripts.opening_cache_repair import _propagate_one_hash

        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        target_hash = 555_020
        game_id = await _insert_game_for_propagate(session_maker)
        try:
            await _insert_position(
                session_maker,
                user_id=_TEST_USER_ID,
                game_id=game_id,
                ply=2,
                full_hash=31,
                eval_cp=0,
                eval_mate=None,
            )
            await _insert_position(
                session_maker,
                user_id=_TEST_USER_ID,
                game_id=game_id,
                ply=3,
                full_hash=target_hash,
            )

            async with session_maker() as session:
                audit = OpeningCacheAudit(
                    full_hash=target_hash,
                    status="confirmed_bad",
                    old_cp=0,
                    old_mate=None,
                    full_cp=500,
                    full_mate=None,
                )
                session.add(audit)
                await session.flush()
                await _propagate_one_hash(session, audit)
                await session.commit()

            async with session_maker() as session:
                eval_after_first = (
                    await session.execute(
                        select(GamePosition.eval_cp).where(
                            GamePosition.game_id == game_id, GamePosition.ply == 2
                        )
                    )
                ).scalar_one()
                assert eval_after_first == 500

                audit2 = await session.get(OpeningCacheAudit, target_hash)
                assert audit2 is not None
                await _propagate_one_hash(session, audit2)
                await session.commit()

            async with session_maker() as session:
                eval_after_second = (
                    await session.execute(
                        select(GamePosition.eval_cp).where(
                            GamePosition.game_id == game_id, GamePosition.ply == 2
                        )
                    )
                ).scalar_one()
                assert eval_after_second == 500  # unchanged -- predicate no longer matches

                repair_row_count = (
                    await session.execute(
                        select(func.count())
                        .select_from(OpeningCacheRepairRow)
                        .where(OpeningCacheRepairRow.game_id == game_id)
                    )
                ).scalar_one()
                assert repair_row_count == 1  # no duplicate row from the second run
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [target_hash])
            await _reset_progress(session_maker)

    async def test_propagate_transitions_status_to_repaired(self, test_engine: AsyncEngine) -> None:
        """Propagate moves the audit row `confirmed_bad -> repaired` (not just a
        `repaired_at` stamp): Release 2's migration trusts `repaired` rows and must
        not demote a just-repaired position to candidate (Phase 220 dev smoke)."""
        session_maker = _session_maker(test_engine)
        target_hash = 555_035
        try:
            async with session_maker() as session:
                session.add(
                    OpeningCacheAudit(
                        full_hash=target_hash,
                        status="confirmed_bad",
                        old_cp=0,
                        old_mate=None,
                        full_cp=100,
                        full_mate=None,
                    )
                )
                await session.commit()
            await _seed_confirm_finished(session_maker)

            await run_propagate(db="dev", dry_run=False, limit=None, session_maker=session_maker)

            async with session_maker() as session:
                audit_after = await session.get(OpeningCacheAudit, target_hash)
                assert audit_after is not None
                assert audit_after.status == "repaired"
                assert audit_after.repaired_at is not None
        finally:
            await _delete_opening_cache(session_maker, [target_hash])
            await _reset_progress(session_maker)

    async def test_propagate_no_carriers(self, test_engine: AsyncEngine) -> None:
        """A confirmed_bad hash with zero matching carrier rows still gets
        repaired_at set, and writes no opening_cache_repair_rows."""
        session_maker = _session_maker(test_engine)
        target_hash = 555_030
        try:
            async with session_maker() as session:
                session.add(
                    OpeningCacheAudit(
                        full_hash=target_hash,
                        status="confirmed_bad",
                        old_cp=0,
                        old_mate=None,
                        full_cp=100,
                        full_mate=None,
                    )
                )
                await session.commit()
            await _seed_confirm_finished(session_maker)

            await run_propagate(db="dev", dry_run=False, limit=None, session_maker=session_maker)

            async with session_maker() as session:
                audit_after = await session.get(OpeningCacheAudit, target_hash)
                assert audit_after is not None
                assert audit_after.repaired_at is not None
                repair_row_count = (
                    await session.execute(
                        select(func.count())
                        .select_from(OpeningCacheRepairRow)
                        .where(OpeningCacheRepairRow.full_hash == target_hash)
                    )
                ).scalar_one()
                assert repair_row_count == 0
        finally:
            await _delete_opening_cache(session_maker, [target_hash])
            await _reset_progress(session_maker)

    async def test_propagate_dry_run(self, test_engine: AsyncEngine) -> None:
        """--dry-run rewrites no game_positions row and stamps no repaired_at."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        target_hash = 555_040
        game_id = await _insert_game_for_propagate(session_maker)
        try:
            await _insert_position(
                session_maker,
                user_id=_TEST_USER_ID,
                game_id=game_id,
                ply=2,
                full_hash=41,
                eval_cp=0,
                eval_mate=None,
            )
            await _insert_position(
                session_maker,
                user_id=_TEST_USER_ID,
                game_id=game_id,
                ply=3,
                full_hash=target_hash,
            )
            async with session_maker() as session:
                session.add(
                    OpeningCacheAudit(
                        full_hash=target_hash,
                        status="confirmed_bad",
                        old_cp=0,
                        old_mate=None,
                        full_cp=999,
                        full_mate=None,
                    )
                )
                await session.commit()
            await _seed_confirm_finished(session_maker)

            await run_propagate(db="dev", dry_run=True, limit=None, session_maker=session_maker)

            async with session_maker() as session:
                eval_cp = (
                    await session.execute(
                        select(GamePosition.eval_cp).where(
                            GamePosition.game_id == game_id, GamePosition.ply == 2
                        )
                    )
                ).scalar_one()
                assert eval_cp == 0
                audit_after = await session.get(OpeningCacheAudit, target_hash)
                assert audit_after is not None
                assert audit_after.repaired_at is None
            progress = await _get_progress(session_maker)
            assert progress is not None
            assert progress.propagate_started_at is None
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [target_hash])
            await _reset_progress(session_maker)


async def _insert_candidate(
    session_maker: async_sessionmaker[AsyncSession],
    *,
    game_id: int,
    ply: int,
    best_cp: int | None,
    second_cp: int | None,
    best_mate: int | None = None,
    second_mate: int | None = None,
    maia_prob: float = 0.3,
) -> None:
    """One `game_best_moves` (Gem/Great candidate) row with explicit evals."""
    async with session_maker() as session:
        session.add(
            GameBestMove(
                game_id=game_id,
                ply=ply,
                maia_prob=maia_prob,
                best_cp=best_cp,
                best_mate=best_mate,
                second_cp=second_cp,
                second_mate=second_mate,
            )
        )
        await session.commit()


async def _candidate(
    session_maker: async_sessionmaker[AsyncSession], game_id: int, ply: int
) -> tuple[int | None, int | None] | None:
    """(best_cp, best_mate) of a candidate row, or None when the row is gone."""
    async with session_maker() as session:
        row = await session.get(GameBestMove, (game_id, ply))
        return None if row is None else (row.best_cp, row.best_mate)


class TestPropagateBestMoves:
    """Follow-up to the prod run (2026-09-11): `game_best_moves.best_cp` is a
    copy of the position eval, so propagate must re-base the candidate at
    ply `p + 1` and drop it when the corrected margin fails the build-time
    inaccuracy gate (game 2356581 ply 6: 305 -> 10 vs second -4)."""

    async def _poisoned_game(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        *,
        target_hash: int,
        carrier_hash: int,
        old_cp: int,
        new_cp: int,
    ) -> int:
        """A game whose row 2 holds `old_cp` (the eval of the position with
        `target_hash` on row 3) and whose audit row repairs it to `new_cp`."""
        game_id = await _insert_game_for_propagate(session_maker)
        await _insert_position(
            session_maker,
            user_id=_TEST_USER_ID,
            game_id=game_id,
            ply=2,
            full_hash=carrier_hash,
            eval_cp=old_cp,
            eval_mate=None,
        )
        await _insert_position(
            session_maker, user_id=_TEST_USER_ID, game_id=game_id, ply=3, full_hash=target_hash
        )
        async with session_maker() as session:
            session.add(
                OpeningCacheAudit(
                    full_hash=target_hash,
                    status="confirmed_bad",
                    old_cp=old_cp,
                    old_mate=None,
                    full_cp=new_cp,
                    full_mate=None,
                )
            )
            await session.commit()
        return game_id

    async def test_propagate_rebases_and_prunes_candidates(self, test_engine: AsyncEngine) -> None:
        """Three candidates at the repaired ply: one whose corrected margin
        fails the gate (deleted), one that still passes (rewritten, kept),
        one whose best_cp never matched the old value (untouched)."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        hash_prune, hash_keep, hash_skip = 556_001, 556_002, 556_003
        # Ply 3 is Black to move (odd ply): mover-POV margin flips sign, so the
        # "poison" is a large NEGATIVE cp (good for Black) corrected to ~0.
        game_prune = await self._poisoned_game(
            session_maker, target_hash=hash_prune, carrier_hash=41, old_cp=-305, new_cp=-10
        )
        game_keep = await self._poisoned_game(
            session_maker, target_hash=hash_keep, carrier_hash=42, old_cp=-600, new_cp=-300
        )
        game_skip = await self._poisoned_game(
            session_maker, target_hash=hash_skip, carrier_hash=43, old_cp=-305, new_cp=-10
        )
        try:
            # prune: -305 vs 4 passes today; -10 vs 4 is ~0.01 ES -> fails.
            await _insert_candidate(
                session_maker, game_id=game_prune, ply=3, best_cp=-305, second_cp=4
            )
            # keep: -300 vs 0 is still ~0.24 ES -> passes with the corrected value.
            await _insert_candidate(
                session_maker, game_id=game_keep, ply=3, best_cp=-600, second_cp=0
            )
            # skip: candidate was built from some other value; not ours to touch.
            await _insert_candidate(
                session_maker, game_id=game_skip, ply=3, best_cp=-150, second_cp=4
            )
            await _seed_confirm_finished(session_maker)

            await run_propagate(db="dev", dry_run=False, limit=None, session_maker=session_maker)

            assert await _candidate(session_maker, game_prune, 3) is None
            assert await _candidate(session_maker, game_keep, 3) == (-300, None)
            assert await _candidate(session_maker, game_skip, 3) == (-150, None)
        finally:
            await _delete_games(session_maker, [game_prune, game_keep, game_skip])
            await _delete_opening_cache(session_maker, [hash_prune, hash_keep, hash_skip])
            await _reset_progress(session_maker)

    async def test_standalone_stage_replays_trail(self, test_engine: AsyncEngine) -> None:
        """A DB whose `propagate` ran before the candidate rewrite existed:
        the trail row is there, the candidate is stale. `propagate-best-moves`
        gates on propagate_finished_at, reports the stale count on --dry-run
        without writing, then re-bases and prunes; a second run is a no-op."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        target_hash = 556_010
        game_id = await self._poisoned_game(
            session_maker, target_hash=target_hash, carrier_hash=44, old_cp=-305, new_cp=-10
        )
        try:
            await _seed_confirm_finished(session_maker)
            with pytest.raises(StageOrderError):
                await run_propagate_best_moves(db="dev", dry_run=True, session_maker=session_maker)

            # Old-code propagate: carrier + trail written, candidate left stale.
            await run_propagate(db="dev", dry_run=False, limit=None, session_maker=session_maker)
            await _insert_candidate(
                session_maker, game_id=game_id, ply=3, best_cp=-305, second_cp=4
            )

            await run_propagate_best_moves(db="dev", dry_run=True, session_maker=session_maker)
            assert await _candidate(session_maker, game_id, 3) == (-305, None)

            await run_propagate_best_moves(db="dev", dry_run=False, session_maker=session_maker)
            assert await _candidate(session_maker, game_id, 3) is None

            await run_propagate_best_moves(db="dev", dry_run=False, session_maker=session_maker)
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [target_hash])
            await _reset_progress(session_maker)


class TestRederive:
    """CACHEFIX-06: `rederive` reclassifies every affected game under the
    per-game advisory lock, through the drain's own diff/upsert classifier,
    preserving blobs/tactic tags for every surviving flaw."""

    async def test_rederive_preserves_blobs(self, test_engine: AsyncEngine) -> None:
        """A surviving flaw's two blob columns and its tactic-tag columns are
        byte-identical after rederive (preserve-by-omission, D-03/D-04)."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        game_id = await _insert_rederive_game(session_maker, include_mistake=True)
        try:
            await _seed_flaw_rows(session_maker, game_id, _TEST_USER_ID)

            await _rederive_one_game(session_maker, game_id, _TEST_USER_ID)

            async with session_maker() as session:
                rows = (
                    (
                        await session.execute(
                            select(GameFlaw)
                            .where(GameFlaw.game_id == game_id)
                            .order_by(GameFlaw.ply)
                            .options(
                                undefer(GameFlaw.allowed_pv_lines),
                                undefer(GameFlaw.missed_pv_lines),
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(rows) >= 1
                for row in rows:
                    assert row.allowed_pv_lines == [
                        {"b": 1, "bm": None, "s": None, "sm": None, "su": ""}
                    ]
                    assert row.missed_pv_lines == [
                        {"b": 2, "bm": None, "s": None, "sm": None, "su": ""}
                    ]
                    assert row.allowed_tactic_motif == 5
        finally:
            await _delete_games(session_maker, [game_id])

    async def test_rederive_counts(self, test_engine: AsyncEngine) -> None:
        """A ply loses its flaw, another gains one, and the
        opening_cache_repair_games before/after counters and the game's
        oracle columns move accordingly."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        game_id = await _insert_rederive_game(session_maker, include_mistake=True)
        try:
            # Pre-existing state: only the blunder@2 is known (with a blob);
            # a PHANTOM flaw at ply=6 the current eval data does not support.
            await _seed_flaw_rows(session_maker, game_id, _TEST_USER_ID, plies={2})
            await _seed_phantom_flaw(session_maker, game_id, _TEST_USER_ID, ply=6)
            async with session_maker() as session:
                session.add(
                    OpeningCacheRepairGame(game_id=game_id, user_id=_TEST_USER_ID, status="pending")
                )
                await session.commit()

            await _rederive_one_game(session_maker, game_id, _TEST_USER_ID)

            async with session_maker() as session:
                flaw_plies = set(
                    (await session.execute(select(GameFlaw.ply).where(GameFlaw.game_id == game_id)))
                    .scalars()
                    .all()
                )
                assert 6 not in flaw_plies, "phantom ply=6 flaw must be removed"
                assert 4 in flaw_plies, "the mistake@4 the current data supports is inserted"
                assert 2 in flaw_plies
                # The full-game classify also independently flags plies 1 and 3
                # (adjacent "lucky"/"reversed"/"squandered" tags from the SAME
                # blunder transition, visible from the other color's mover
                # perspective) -- before={2,6}, after={1,2,3,4}: 3 added (1,3,4),
                # 1 removed (6).
                assert flaw_plies == {1, 2, 3, 4}

                repair_game = await session.get(OpeningCacheRepairGame, game_id)
                assert repair_game is not None
                assert repair_game.status == "reclassified"
                assert repair_game.flaws_added == 3
                assert repair_game.flaws_removed == 1

                game = await session.get(Game, game_id)
                assert game is not None
                assert game.white_mistakes is not None
                assert game.black_mistakes is not None
        finally:
            await _delete_games(session_maker, [game_id])

    async def test_rederive_rearm(self, test_engine: AsyncEngine) -> None:
        """`blobs_completed_at` is cleared when a new blob-less flaw appears
        (D-08/SEED-125 bidirectional re-arm)."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        game_id = await _insert_rederive_game(session_maker, include_mistake=True)
        try:
            # Only the blunder@2 known so far -- the mistake@4 the current
            # data supports will be a freshly-INSERTED, blob-less flaw.
            await _seed_flaw_rows(session_maker, game_id, _TEST_USER_ID, plies={2})
            past = datetime.datetime.now(datetime.timezone.utc)
            async with session_maker() as session:
                await session.execute(
                    update(Game).where(Game.id == game_id).values(blobs_completed_at=past)
                )
                await session.commit()

            await _rederive_one_game(session_maker, game_id, _TEST_USER_ID)

            async with session_maker() as session:
                game = await session.get(Game, game_id)
                assert game is not None
                assert game.blobs_completed_at is None, (
                    "a newly-inserted blob-less flaw must clear blobs_completed_at, "
                    "re-arming the tier-4 lottery"
                )
        finally:
            await _delete_games(session_maker, [game_id])

    async def test_rederive_drills(self, test_engine: AsyncEngine) -> None:
        """The orphaned drill_item is pruned, a still-valid one survives, and
        herring_pool rows are counted (never deleted, D-08)."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        game_id = await _insert_rederive_game(session_maker, include_mistake=True)
        try:
            await _seed_flaw_rows(session_maker, game_id, _TEST_USER_ID, plies={2})
            await _seed_phantom_flaw(session_maker, game_id, _TEST_USER_ID, ply=6)
            async with session_maker() as session:
                session.add(
                    DrillItem(
                        user_id=_TEST_USER_ID,
                        game_id=game_id,
                        ply=2,
                        due_date=datetime.date.today(),
                    )
                )
                session.add(
                    DrillItem(
                        user_id=_TEST_USER_ID,
                        game_id=game_id,
                        ply=6,
                        due_date=datetime.date.today(),
                    )
                )
                session.add(
                    HerringPool(
                        user_id=_TEST_USER_ID,
                        game_id=game_id,
                        ply=2,
                        mover_color="white",
                        fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
                        phase=1,
                        ladder=[{"cp": 0, "move": "e2e4"}] * 5,
                    )
                )
                session.add(
                    OpeningCacheRepairRow(
                        game_id=game_id,
                        ply=2,
                        full_hash=1,
                        old_cp=None,
                        old_mate=None,
                        new_cp=None,
                        new_mate=None,
                    )
                )
                await session.commit()

            await _rederive_one_game(session_maker, game_id, _TEST_USER_ID)

            async with session_maker() as session:
                surviving = (
                    await session.execute(
                        select(DrillItem).where(DrillItem.game_id == game_id, DrillItem.ply == 2)
                    )
                ).scalar_one_or_none()
                assert surviving is not None, "ply=2's still-valid drill_item must survive"

                orphaned = (
                    await session.execute(
                        select(DrillItem).where(DrillItem.game_id == game_id, DrillItem.ply == 6)
                    )
                ).scalar_one_or_none()
                assert orphaned is None, "ply=6's orphaned drill_item must be pruned"

                herring_count = (
                    await session.execute(
                        select(func.count())
                        .select_from(HerringPool)
                        .where(HerringPool.game_id == game_id)
                    )
                ).scalar_one()
                assert herring_count == 1, "herring_pool rows are counted, never deleted"
        finally:
            await _delete_games(session_maker, [game_id])

    async def test_rederive_failure(
        self, test_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An injected exception marks that game failed with an error, and
        the next game in the same run still reclassifies normally."""
        import scripts.opening_cache_repair as ocr_module

        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        failing_game_id = await _insert_rederive_game(session_maker, include_mistake=True)
        ok_game_id = await _insert_rederive_game(session_maker, include_mistake=True)
        try:
            for gid in (failing_game_id, ok_game_id):
                await _seed_flaw_rows(session_maker, gid, _TEST_USER_ID)
            async with session_maker() as session:
                session.add(
                    OpeningCacheRepairGame(
                        game_id=failing_game_id, user_id=_TEST_USER_ID, status="pending"
                    )
                )
                session.add(
                    OpeningCacheRepairGame(
                        game_id=ok_game_id, user_id=_TEST_USER_ID, status="pending"
                    )
                )
                await session.commit()
            await _seed_propagate_finished(session_maker)

            real_classify = ocr_module._classify_and_fill_oracle

            async def _classify_maybe_raise(
                session: AsyncSession, game_id: int, *args: object, **kwargs: object
            ) -> None:
                if game_id == failing_game_id:
                    raise RuntimeError("injected rederive failure")
                await real_classify(session, game_id, *args, **kwargs)  # ty: ignore[invalid-argument-type]

            monkeypatch.setattr(ocr_module, "_classify_and_fill_oracle", _classify_maybe_raise)

            await run_rederive(db="dev", dry_run=False, limit=None, session_maker=session_maker)

            async with session_maker() as session:
                failing_row = await session.get(OpeningCacheRepairGame, failing_game_id)
                assert failing_row is not None
                assert failing_row.status == "failed"
                assert failing_row.error is not None

                ok_row = await session.get(OpeningCacheRepairGame, ok_game_id)
                assert ok_row is not None
                assert ok_row.status == "reclassified"
        finally:
            await _delete_games(session_maker, [failing_game_id, ok_game_id])
            await _reset_progress(session_maker)

    async def test_rederive_idempotent(self, test_engine: AsyncEngine) -> None:
        """Running rederive twice over an unchanged game is a no-op the
        second time: equal before/after counters."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        game_id = await _insert_rederive_game(session_maker, include_mistake=True)
        try:
            await _seed_flaw_rows(session_maker, game_id, _TEST_USER_ID)
            async with session_maker() as session:
                session.add(
                    OpeningCacheRepairGame(game_id=game_id, user_id=_TEST_USER_ID, status="pending")
                )
                await session.commit()

            await _rederive_one_game(session_maker, game_id, _TEST_USER_ID)
            async with session_maker() as session:
                repair_game = await session.get(OpeningCacheRepairGame, game_id)
                assert repair_game is not None
                assert repair_game.status == "reclassified"

            async with session_maker() as session:
                repair_game = await session.get(OpeningCacheRepairGame, game_id)
                assert repair_game is not None
                repair_game.status = "pending"
                await session.commit()

            await _rederive_one_game(session_maker, game_id, _TEST_USER_ID)

            async with session_maker() as session:
                repair_game = await session.get(OpeningCacheRepairGame, game_id)
                assert repair_game is not None
                assert repair_game.status == "reclassified"
                assert repair_game.flaws_added == 0
                assert repair_game.flaws_removed == 0
        finally:
            await _delete_games(session_maker, [game_id])

    async def test_rederive_lock(self, test_engine: AsyncEngine) -> None:
        """The advisory lock is held for the duration of `_rederive_one_game`:
        a concurrent holder of the same key blocks it (mirrors
        tests/services/test_eval_apply.py's TestSameGameWriteLock technique)."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        game_id = await _insert_rederive_game(session_maker, include_mistake=True)
        holder = session_maker()
        task: asyncio.Task[None] | None = None
        try:
            lock_key = _game_write_lock_key(game_id)
            await holder.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"), {"lock_key": lock_key}
            )

            task = asyncio.create_task(_rederive_one_game(session_maker, game_id, _TEST_USER_ID))

            async with session_maker() as probe_session:
                deadline = time.monotonic() + _LOCK_PROBE_POLL_DEADLINE_S
                waiter_seen = False
                while time.monotonic() < deadline:
                    if await _advisory_waiter_row_visible(probe_session, lock_key):
                        waiter_seen = True
                        break
                    await asyncio.sleep(_LOCK_PROBE_POLL_INTERVAL_S)

            assert not task.done(), (
                "_rederive_one_game completed while another session held the "
                "per-game advisory lock -- the lock is not being taken"
            )
            assert waiter_seen, (
                "no NOT-granted advisory lock row for this game_id's key was "
                "observed in pg_locks within the probe deadline"
            )

            await holder.rollback()
            await asyncio.wait_for(task, timeout=_LOCK_RELEASE_TIMEOUT_S)
        finally:
            if task is not None and not task.done():
                task.cancel()
            await holder.close()
            await _delete_games(session_maker, [game_id])


# ---------------------------------------------------------------------------
# `demote` (Phase 220 Release 2, CACHEFIX-08 -- operator escape hatch)
# ---------------------------------------------------------------------------


class TestDemote:
    """`demote` un-confirms cache rows recorded against a named engine_version.
    NOT a pipeline stage: takes no _STAGE_ORDER gate, so no _reset_progress
    cleanup is needed (only the cache rows themselves)."""

    async def test_demote_unconfirms_named_engine_version(self, test_engine: AsyncEngine) -> None:
        """A confirmed row at the named engine_version is un-confirmed; a
        confirmed row at a DIFFERENT engine_version is left untouched."""
        session_maker = _session_maker(test_engine)
        target_hash = -910001
        other_hash = -910002
        try:
            async with session_maker() as session:
                session.add(
                    OpeningPositionEval(
                        full_hash=target_hash,
                        eval_cp=42,
                        confirmed=True,
                        n_sources=2,
                        engine_version="Stockfish 18",
                        confirmed_at=datetime.datetime.now(datetime.timezone.utc),
                    )
                )
                session.add(
                    OpeningPositionEval(
                        full_hash=other_hash,
                        eval_cp=10,
                        confirmed=True,
                        n_sources=2,
                        engine_version="Stockfish 17",
                        confirmed_at=datetime.datetime.now(datetime.timezone.utc),
                    )
                )
                await session.commit()

            await run_demote(
                db="dev",
                dry_run=False,
                limit=None,
                engine_version="Stockfish 18",
                session_maker=session_maker,
            )

            async with session_maker() as session:
                target = await session.get(OpeningPositionEval, target_hash)
                other = await session.get(OpeningPositionEval, other_hash)
            assert target is not None
            assert target.confirmed is False, "named-version row must be un-confirmed"
            assert target.n_sources == 1
            assert target.confirmed_at is None
            assert other is not None
            assert other.confirmed is True, "a different engine_version must be untouched"
            assert other.n_sources == 2
        finally:
            await _delete_opening_cache(session_maker, [target_hash, other_hash])

    async def test_demote_dry_run_writes_nothing(self, test_engine: AsyncEngine) -> None:
        """--dry-run reports the affected count and changes no row."""
        session_maker = _session_maker(test_engine)
        target_hash = -910003
        try:
            async with session_maker() as session:
                session.add(
                    OpeningPositionEval(
                        full_hash=target_hash,
                        eval_cp=5,
                        confirmed=True,
                        n_sources=2,
                        engine_version="Stockfish 18",
                        confirmed_at=datetime.datetime.now(datetime.timezone.utc),
                    )
                )
                await session.commit()

            await run_demote(
                db="dev",
                dry_run=True,
                limit=None,
                engine_version="Stockfish 18",
                session_maker=session_maker,
            )

            async with session_maker() as session:
                row = await session.get(OpeningPositionEval, target_hash)
            assert row is not None
            assert row.confirmed is True, "--dry-run must not un-confirm anything"
        finally:
            await _delete_opening_cache(session_maker, [target_hash])

    async def test_demote_only_confirmed_rows_at_version_are_counted(
        self, test_engine: AsyncEngine
    ) -> None:
        """An already-unconfirmed row at the named engine_version is a no-op
        (nothing to demote) and does not inflate the affected count."""
        session_maker = _session_maker(test_engine)
        already_candidate_hash = -910004
        try:
            async with session_maker() as session:
                session.add(
                    OpeningPositionEval(
                        full_hash=already_candidate_hash,
                        eval_cp=7,
                        confirmed=False,
                        n_sources=1,
                        engine_version="Stockfish 18",
                    )
                )
                await session.commit()

            await run_demote(
                db="dev",
                dry_run=False,
                limit=None,
                engine_version="Stockfish 18",
                session_maker=session_maker,
            )

            async with session_maker() as session:
                row = await session.get(OpeningPositionEval, already_candidate_hash)
            assert row is not None
            assert row.confirmed is False
            assert row.n_sources == 1
        finally:
            await _delete_opening_cache(session_maker, [already_candidate_hash])

    async def test_demote_limit_caps_affected_rows(self, test_engine: AsyncEngine) -> None:
        """--limit caps how many confirmed rows at the named version are un-confirmed
        this run; the rest stay confirmed for a follow-up invocation."""
        session_maker = _session_maker(test_engine)
        hashes = [-910010, -910011, -910012]
        try:
            async with session_maker() as session:
                for fh in hashes:
                    session.add(
                        OpeningPositionEval(
                            full_hash=fh,
                            eval_cp=1,
                            confirmed=True,
                            n_sources=2,
                            engine_version="Stockfish 18",
                            confirmed_at=datetime.datetime.now(datetime.timezone.utc),
                        )
                    )
                await session.commit()

            await run_demote(
                db="dev",
                dry_run=False,
                limit=1,
                engine_version="Stockfish 18",
                session_maker=session_maker,
            )

            async with session_maker() as session:
                rows = (
                    (
                        await session.execute(
                            select(OpeningPositionEval).where(
                                OpeningPositionEval.full_hash.in_(hashes)
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
            un_confirmed_count = sum(1 for r in rows if r.confirmed is False)
            assert un_confirmed_count == 1, (
                f"--limit 1 must un-confirm exactly one row, got {un_confirmed_count}"
            )
        finally:
            await _delete_opening_cache(session_maker, hashes)


# ---------------------------------------------------------------------------
# `report` fixtures (Phase 220 Plan 04, CACHEFIX-07)
# ---------------------------------------------------------------------------

_REPORT_READ_ONLY_MODELS = (
    OpeningPositionEval,
    GamePosition,
    GameFlaw,
    OpeningCacheAudit,
    OpeningCacheRepairRow,
    OpeningCacheRepairGame,
)


async def _report_read_only_table_counts(
    session_maker: async_sessionmaker[AsyncSession],
) -> tuple[int, ...]:
    counts: list[int] = []
    async with session_maker() as session:
        for model in _REPORT_READ_ONLY_MODELS:
            counts.append(
                (await session.execute(select(func.count()).select_from(model))).scalar_one()
            )
    return tuple(counts)


class TestReport:
    """CACHEFIX-07: `report` renders every audit table into a committed,
    read-only, PII-free markdown trail."""

    async def test_report_read_only(self, test_engine: AsyncEngine, tmp_path: Path) -> None:
        """The six tables' row counts are identical before and after a run."""
        session_maker = _session_maker(test_engine)
        before = await _report_read_only_table_counts(session_maker)
        await write_repair_report(
            session_maker,
            now=datetime.datetime(2026, 9, 10, tzinfo=datetime.timezone.utc),
            out_dir=tmp_path,
            db="dev",
        )
        after = await _report_read_only_table_counts(session_maker)
        assert before == after

    async def test_report_empty(self, test_engine: AsyncEngine, tmp_path: Path) -> None:
        """With zero opening_cache_audit rows, the report still renders a
        well-formed file with zero-filled tables -- no exception."""
        session_maker = _session_maker(test_engine)
        async with session_maker() as session:
            await session.execute(delete(OpeningCacheRepairRow))
            await session.execute(delete(OpeningCacheRepairGame))
            await session.execute(delete(OpeningCacheAudit))
            await session.commit()

        report_path = await write_repair_report(
            session_maker,
            now=datetime.datetime(2026, 9, 10, tzinfo=datetime.timezone.utc),
            out_dir=tmp_path,
            db="dev",
        )
        content = report_path.read_text(encoding="utf-8")
        assert "Cache status breakdown" in content
        assert "confirmed_bad" in content
        assert "No `confirmed_bad` rows." in content

    async def test_report_top30_order(self, test_engine: AsyncEngine, tmp_path: Path) -> None:
        """Two `confirmed_bad` positions with EQUAL carrier counts come out in
        `full_hash` ASC order (a total order over the top-30 table)."""
        session_maker = _session_maker(test_engine)
        await _ensure_user(session_maker, _TEST_USER_ID)
        game_id = await _insert_game_for_propagate(session_maker, user_id=_TEST_USER_ID)
        hash_a = 900_001
        hash_b = 900_002
        try:
            await _insert_position(
                session_maker, user_id=_TEST_USER_ID, game_id=game_id, ply=2, full_hash=hash_a
            )
            await _insert_position(
                session_maker, user_id=_TEST_USER_ID, game_id=game_id, ply=1, full_hash=hash_b
            )
            async with session_maker() as session:
                session.add(
                    OpeningCacheAudit(
                        full_hash=hash_b,
                        status="confirmed_bad",
                        old_cp=0,
                        full_cp=100,
                        delta_cp=100,
                    )
                )
                session.add(
                    OpeningCacheAudit(
                        full_hash=hash_a,
                        status="confirmed_bad",
                        old_cp=0,
                        full_cp=100,
                        delta_cp=100,
                    )
                )
                await session.commit()

            report_path = await write_repair_report(
                session_maker,
                now=datetime.datetime(2026, 9, 10, tzinfo=datetime.timezone.utc),
                out_dir=tmp_path,
                db="dev",
            )
            content = report_path.read_text(encoding="utf-8")
            idx_a = content.index(f"| {hash_a} |")
            idx_b = content.index(f"| {hash_b} |")
            assert idx_a < idx_b, "equal carrier counts must tie-break on full_hash ASC"
        finally:
            await _delete_games(session_maker, [game_id])
            await _delete_opening_cache(session_maker, [hash_a, hash_b])

    async def test_report_no_pii(self, test_engine: AsyncEngine, tmp_path: Path) -> None:
        """The generated file contains no `@`, `email` or `username` token --
        the per-user table is numeric ids only."""
        session_maker = _session_maker(test_engine)
        report_path = await write_repair_report(
            session_maker,
            now=datetime.datetime(2026, 9, 10, tzinfo=datetime.timezone.utc),
            out_dir=tmp_path,
            db="dev",
        )
        content = report_path.read_text(encoding="utf-8")
        assert "@" not in content
        assert "email" not in content.lower()
        assert "username" not in content.lower()

    async def test_report_filename(self, test_engine: AsyncEngine, tmp_path: Path) -> None:
        """The injected `now` determines the filename and the injected
        `out_dir` the location."""
        session_maker = _session_maker(test_engine)
        now = datetime.datetime(2026, 12, 25, tzinfo=datetime.timezone.utc)
        out_dir = tmp_path / "custom-report-dir"
        report_path = await write_repair_report(session_maker, now=now, out_dir=out_dir, db="dev")
        assert report_path == out_dir / "opening-cache-repair-2026-12-25.md"
        assert report_path.exists()

    async def test_report_partial_skips_gate(
        self, test_engine: AsyncEngine, tmp_path: Path
    ) -> None:
        """`--partial` skips the rederive_finished_at stage gate."""
        session_maker = _session_maker(test_engine)
        try:
            report_path = await run_report(
                db="dev",
                partial=True,
                session_maker=session_maker,
                out_dir=tmp_path,
                now=datetime.datetime(2026, 9, 10, tzinfo=datetime.timezone.utc),
            )
            assert report_path.exists()
        finally:
            await _reset_progress(session_maker)

    async def test_report_gate_without_partial(
        self, test_engine: AsyncEngine, tmp_path: Path
    ) -> None:
        """Without `--partial`, `report` refuses to run before
        `rederive_finished_at` is set."""
        session_maker = _session_maker(test_engine)
        try:
            with pytest.raises(StageOrderError):
                await run_report(
                    db="dev",
                    partial=False,
                    session_maker=session_maker,
                    out_dir=tmp_path,
                    now=datetime.datetime(2026, 9, 10, tzinfo=datetime.timezone.utc),
                )
        finally:
            await _reset_progress(session_maker)


# ---------------------------------------------------------------------------
# `legacy-sample` fixtures (Phase 220 Plan 04, CACHEFIX-10, D-07)
# ---------------------------------------------------------------------------


class TestLegacySample:
    """CACHEFIX-10/D-07: `legacy-sample` measures the pre-2026-06-18 legacy
    cohort's disagreement rate beyond ply 20 against a like-for-like control,
    through the same per-row test `screen` uses."""

    async def test_legacy_sample_gate(self, test_engine: AsyncEngine) -> None:
        """Refuses to run while `screen_floor` is NULL, writes nothing."""
        session_maker = _session_maker(test_engine)
        try:
            with pytest.raises(CalibrationRequiredError):
                await run_legacy_sample(db="dev", session_maker=session_maker)
            progress = await _get_progress(session_maker)
            assert progress is None or progress.legacy_sample_started_at is None
        finally:
            await _reset_progress(session_maker)

    @pytest.mark.parametrize(
        "control_disagree,control_rows,legacy_disagree,legacy_rows,expected_build",
        [
            (1000, 10_000, 2000, 10_000, False),  # ratio exactly 2x -> NO BUILD
            (5, 10_000, 95, 10_000, False),  # ratio > 2x, excess 0.90pp -> NO BUILD
            (5, 10_000, 105, 10_000, True),  # ratio > 2x, excess exactly 1.00pp -> BUILD
            (100, 10_000, 1000, 10_000, True),  # ratio > 2x, large excess -> BUILD
        ],
    )
    async def test_legacy_sample_decision_rule(
        self,
        control_disagree: int,
        control_rows: int,
        legacy_disagree: int,
        legacy_rows: int,
        expected_build: bool,
    ) -> None:
        """The 4 rule corners: ratio exactly 2x is a NO BUILD regardless of
        excess; the excess boundary is inclusive (`>=`) at 1.0pp."""
        legacy = _LegacySampleCohortResult(
            n_games=1,
            rows_le20=0,
            rows_gt20=legacy_rows,
            disagree_le20=0,
            disagree_gt20=legacy_disagree,
        )
        control = _LegacySampleCohortResult(
            n_games=1,
            rows_le20=0,
            rows_gt20=control_rows,
            disagree_le20=0,
            disagree_gt20=control_disagree,
        )
        _legacy_rate, _control_rate, build = _legacy_sample_decision(legacy, control)
        assert build is expected_build

    async def test_legacy_sample_boundary(self) -> None:
        """A row whose expected-score delta equals `screen_floor` exactly
        counts as agreeing (screen's own inclusive `<=` boundary)."""
        disagrees = _classify_legacy_sample_row(
            prev_cp=0, prev_mate=None, depth_cp=0, depth_mate=None, screen_floor=0.0
        )
        assert disagrees is False

    async def test_legacy_sample_short_cohort(
        self, test_engine: AsyncEngine, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Fewer eligible legacy games than requested (30 < 200) uses all 30
        and reports the real n in the decision line."""
        session_maker = _session_maker(test_engine)
        await _seed_calibrate_finished(session_maker, screen_floor=1.0)
        legacy_dt = datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc)
        control_dt = datetime.datetime(2026, 8, 21, tzinfo=datetime.timezone.utc)
        game_ids: list[int] = []
        try:
            for _ in range(30):
                gid = await _insert_carrier_game(
                    session_maker, full_evals_completed_at=legacy_dt, lichess_evals_at=None
                )
                game_ids.append(gid)
            control_gid = await _insert_carrier_game(
                session_maker, full_evals_completed_at=control_dt, lichess_evals_at=None
            )
            game_ids.append(control_gid)

            pool = _FakePool({})
            await run_legacy_sample(
                db="dev",
                session_maker=session_maker,
                pool=pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )

            captured = capsys.readouterr()
            assert "legacy cohort: 30 games" in captured.out
            assert "LEGACY-COHORT-DECISION" in captured.out
        finally:
            await _delete_games(session_maker, game_ids)
            await _reset_progress(session_maker)

    async def test_legacy_sample_empty_cohort(
        self, test_engine: AsyncEngine, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Zero eligible games in either cohort exits non-zero with no
        verdict line."""
        session_maker = _session_maker(test_engine)
        await _seed_calibrate_finished(session_maker, screen_floor=1.0)
        try:
            with pytest.raises(CalibrationSampleEmptyError):
                await run_legacy_sample(db="dev", session_maker=session_maker)
            captured = capsys.readouterr()
            assert "LEGACY-COHORT-DECISION" not in captured.out
        finally:
            await _reset_progress(session_maker)

    async def test_legacy_sample_read_only(self, test_engine: AsyncEngine) -> None:
        """No row is written to `game_positions`, `game_flaws` or
        `opening_position_eval`."""
        session_maker = _session_maker(test_engine)
        await _seed_calibrate_finished(session_maker, screen_floor=1.0)
        legacy_dt = datetime.datetime(2026, 5, 1, tzinfo=datetime.timezone.utc)
        control_dt = datetime.datetime(2026, 8, 25, tzinfo=datetime.timezone.utc)
        game_ids: list[int] = []
        try:
            game_ids.append(
                await _insert_carrier_game(
                    session_maker, full_evals_completed_at=legacy_dt, lichess_evals_at=None
                )
            )
            game_ids.append(
                await _insert_carrier_game(
                    session_maker, full_evals_completed_at=control_dt, lichess_evals_at=None
                )
            )

            async def _counts() -> tuple[int, int, int]:
                async with session_maker() as session:
                    gp = (
                        await session.execute(select(func.count()).select_from(GamePosition))
                    ).scalar_one()
                    gf = (
                        await session.execute(select(func.count()).select_from(GameFlaw))
                    ).scalar_one()
                    ope = (
                        await session.execute(select(func.count()).select_from(OpeningPositionEval))
                    ).scalar_one()
                    return gp, gf, ope

            before = await _counts()
            pool = _FakePool({})
            await run_legacy_sample(
                db="dev",
                session_maker=session_maker,
                pool=pool,  # ty: ignore[invalid-argument-type]  # test stub duck-types EnginePool
            )
            after = await _counts()
            assert before == after
        finally:
            await _delete_games(session_maker, game_ids)
            await _reset_progress(session_maker)


class TestPoolFromEnv:
    """Stages must size their own EnginePool from STOCKFISH_POOL_SIZE (CONTEXT.md:
    'STOCKFISH_POOL_SIZE=4 on the local box'). Regression for the hardcoded
    EnginePool(1) found during the Phase 220 dev smoke."""

    def test_honours_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scripts.opening_cache_repair import _pool_from_env

        monkeypatch.setenv("STOCKFISH_POOL_SIZE", "4")
        assert _pool_from_env().size == 4

    def test_defaults_to_one(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scripts.opening_cache_repair import _pool_from_env

        monkeypatch.delenv("STOCKFISH_POOL_SIZE", raising=False)
        assert _pool_from_env().size == 1

    def test_cli_override_beats_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from scripts.opening_cache_repair import _pool_from_env

        monkeypatch.setenv("STOCKFISH_POOL_SIZE", "4")
        assert _pool_from_env(28).size == 28

    def test_cli_flag_parses_on_engine_stages(self) -> None:
        from scripts.opening_cache_repair import build_parser

        parser = build_parser()
        for stage in ("calibrate", "screen", "confirm", "legacy-sample"):
            args = parser.parse_args([stage, "--db", "dev", "--pool-size", "28"])
            assert args.pool_size == 28
        assert parser.parse_args(["screen", "--db", "dev"]).pool_size is None
