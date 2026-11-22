"""Tests for scripts/backfill_maia_flaws.py (Phase 247 plan 05, D-06, D-10, D-11, D-16; 250 D-11).

DB-backed: games are committed through a session maker bound to the per-run test DB (the
script opens its own short sessions) and removed in teardown, so the global tier-3 eval
lottery never sees a leaked non-guest game. The selector is global, so every test scopes
its run by ``user_id`` (other modules' games leak in under -n auto). Maia inference is
faked by patching ``maia_flaw_scoring.full_policy`` and presenting a session sentinel.
"""

from __future__ import annotations

import io
import json
import math
import signal
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import datetime, timedelta, timezone
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
from app.repositories.game_flaws_repository import (
    FACEPALM_COLUMNS,
    FACEPALM_PRE_COLUMNS,
    FACEPALM_REPLY_COLUMNS,
    MAIA_FLAW_COLUMNS,
)
from app.services import maia_engine, maia_flaw_scoring
from app.services.best_move_candidates import pinned_elo_for_mover
from app.services.blunder_check_rules import FACEPALM_DRILL_LAMBDA, FACEPALM_SCORE_MIN
from app.services.facepalm_inputs import facepalm_material_inputs
from app.services.line_material import quiet_best_line_facts, quiet_line_facts
from app.services.maia_flaw_stats import pre_blunder_spread, reply_spread
from scripts import backfill_maia_flaws as backfill
from tests.facepalm_seed import facepalm_fact_columns
from tests.services.maia_fakes import fake_full_policy

# Unique to this module (grep tests/ before changing).
_TEST_USER_ID: int = 247_001

_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *"
_FLAW_PLIES: tuple[int, ...] = (2, 5, 8)
_RUN_STAMP = "20261108T000000Z"
# Distinct, non-NULL stand-in for an already-written base value (spread mode must not touch it).
_SEEDED_BASE: dict[str, float | int] = {"maia_played_prob": 0.11}

# The stored scalars are REAL (float32): compare them with a relative tolerance.
_REAL_REL_TOL = 1e-6

MakeGame = Callable[..., Awaitable[int]]


def _board_fens(pgn: str) -> dict[int, str]:
    """Independent pre-push board_fen per ply (python-chess, not the module)."""
    parsed = chess.pgn.read_game(io.StringIO(pgn))
    assert parsed is not None
    board = parsed.board()
    out: dict[int, str] = {}
    for ply, node in enumerate(parsed.mainline()):
        out[ply] = board.board_fen()
        board.push(node.move)
    return out


@pytest_asyncio.fixture
async def session_factory(test_engine: Any) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _maia_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """Present a Maia session and fake the inference for every test in this module."""
    monkeypatch.setattr(maia_engine, "_session", object())
    monkeypatch.setattr(maia_flaw_scoring, "full_policy", fake_full_policy)


@pytest_asyncio.fixture
async def make_game(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[MakeGame, None]:
    """Factory for committed games (optionally with flaw rows); cleans up in teardown."""
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
                    email=f"backfill-maia-flaws-{_TEST_USER_ID}@example.com",
                    hashed_password="x",
                )
            )
            await session.commit()

    async def _make(
        *,
        flaw_plies: tuple[int, ...] = _FLAW_PLIES,
        fen_override: dict[int, str] | None = None,
        user_color: str = "white",
        severities: dict[int, int] | None = None,
        base_stamped: bool = False,
        seed_base: bool = False,
        pv: dict[int, str] | None = None,
    ) -> int:
        fens = _board_fens(_PGN)
        async with session_factory() as session:
            game = Game(
                user_id=_TEST_USER_ID,
                platform="lichess",
                platform_game_id=f"backfill-maia-{uuid.uuid4().hex}",
                pgn=_PGN,
                result="1-0",
                user_color=user_color,
                white_rating=1500,
                black_rating=1600,
                time_control_str="300+0",
                time_control_bucket="blitz",
                time_control_seconds=300,
                base_time_seconds=300,
                increment_seconds=0.0,
                rated=True,
                is_computer_game=False,
                maia_flaws_completed_at=func.now() if base_stamped else None,
            )
            session.add(game)
            await session.flush()
            game_id = game.id
            for ply in sorted(fens):
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
            for ply in flaw_plies:
                session.add(
                    GameFlaw(
                        user_id=_TEST_USER_ID,
                        game_id=game_id,
                        ply=ply,
                        severity=(severities or {}).get(ply, 2),
                        tempo=None,
                        phase=1,
                        is_miss=False,
                        is_lucky=False,
                        is_reversed=False,
                        is_squandered=False,
                        fen=(fen_override or {}).get(ply, fens[ply]),
                        **(_SEEDED_BASE if seed_base else {}),
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


async def _run(
    maker: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    *,
    shard: int = 0,
    num_shards: int = 1,
    limit: int | None = None,
    dry_run: bool = False,
    mode: backfill.BackfillMode = "full",
    cutoff: datetime | None = None,
) -> backfill.ShardReport:
    return await backfill.run_shard(
        db="dev",
        shard=shard,
        num_shards=num_shards,
        user_id=_TEST_USER_ID,
        limit=limit,
        batch_games=backfill.DEFAULT_BATCH_GAMES,
        dry_run=dry_run,
        throttle_ms=0,
        report_dir=tmp_path,
        run_stamp=_RUN_STAMP,
        session_maker=maker,
        mode=mode,
        cutoff=cutoff,
    )


async def _flaw_values(
    maker: async_sessionmaker[AsyncSession], game_id: int
) -> dict[int, dict[str, Any]]:
    async with maker() as session:
        flaws = (
            (await session.execute(select(GameFlaw).where(GameFlaw.game_id == game_id)))
            .scalars()
            .all()
        )
    return {f.ply: {c: getattr(f, c) for c in MAIA_FLAW_COLUMNS} for f in flaws}


async def _stamp(maker: async_sessionmaker[AsyncSession], game_id: int) -> Any:
    async with maker() as session:
        return (
            await session.execute(select(Game.maia_flaws_completed_at).where(Game.id == game_id))
        ).scalar_one()


# ---------------------------------------------------------------------------
# Tracer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_shard_scores_and_stamps_user_games(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """One shard run takes a user's unstamped games with flaws end to end."""
    game_ids = [await make_game() for _ in range(3)]
    zero_flaw_game = await make_game(flaw_plies=())

    report = await _run(session_factory, tmp_path)

    for gid in game_ids:
        assert await _stamp(session_factory, gid) is not None
        values = await _flaw_values(session_factory, gid)
        assert set(values) == set(_FLAW_PLIES)
        assert all(v["maia_played_prob"] is not None for v in values.values())
    # Zero-flaw games are never selected (the go-forward scorer stamps them).
    assert await _stamp(session_factory, zero_flaw_game) is None
    assert report.games_selected == 3
    assert report.games_stamped == 3
    saved = json.loads((tmp_path / f"dev-full-{_RUN_STAMP}-shard0.json").read_text())
    assert saved["games_stamped"] == 3
    assert saved["flaws_scored"] == 9


# ---------------------------------------------------------------------------
# Sharding, rerun idempotence, replay, dry run (D-06, D-11)
# ---------------------------------------------------------------------------

_SHARD_COUNT = 3
_SHARD_GAMES = 12


@pytest.mark.asyncio
async def test_shard_partition_disjoint_exhaustive(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    game_ids = {await make_game() for _ in range(_SHARD_GAMES)}
    per_shard: list[list[int]] = []
    async with session_factory() as session:
        for shard in range(_SHARD_COUNT):
            per_shard.append(
                await backfill.select_shard_game_ids(
                    session,
                    shard=shard,
                    num_shards=_SHARD_COUNT,
                    user_id=_TEST_USER_ID,
                    limit=None,
                )
            )
    flat = [gid for ids in per_shard for gid in ids]
    assert len(flat) == len(set(flat)), "a game landed in two shards"
    assert set(flat) == game_ids


@pytest.mark.asyncio
async def test_rerun_selects_nothing_and_changes_nothing(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """D-11: the stamp is the checkpoint; a second run is a no-op."""
    game_ids = [await make_game() for _ in range(3)]
    first = await _run(session_factory, tmp_path)
    before = {gid: await _flaw_values(session_factory, gid) for gid in game_ids}
    stamps = {gid: await _stamp(session_factory, gid) for gid in game_ids}

    second = await _run(session_factory, tmp_path)

    assert first.games_stamped == 3
    assert second.games_selected == 0
    assert second.games_stamped == 0
    assert {gid: await _flaw_values(session_factory, gid) for gid in game_ids} == before
    assert {gid: await _stamp(session_factory, gid) for gid in game_ids} == stamps


@pytest.mark.asyncio
async def test_rerun_skips_game_stamped_mid_run(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A game the live lane stamps between selection and write is never overwritten."""
    raced = await make_game()
    other = await make_game()
    real_write = backfill.write_game_maia_scores

    async def _stamp_then_write(session: AsyncSession, scores: Any, **kwargs: Any) -> Any:
        # The live lane wins the race for `raced` after this run selected and scored it.
        async with session_factory() as other_session:
            await other_session.execute(
                update(Game).where(Game.id == raced).values(maia_flaws_completed_at=func.now())
            )
            await other_session.commit()
        return await real_write(session, scores, **kwargs)

    monkeypatch.setattr(backfill, "write_game_maia_scores", _stamp_then_write)

    report = await _run(session_factory, tmp_path)

    assert report.games_already_stamped == 1
    assert report.games_stamped == 1
    raced_values = await _flaw_values(session_factory, raced)
    assert all(v["maia_played_prob"] is None for v in raced_values.values())
    other_values = await _flaw_values(session_factory, other)
    assert all(v["maia_played_prob"] is not None for v in other_values.values())


@pytest.mark.asyncio
async def test_replay_fen_mismatch_counted_in_report(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """D-06: scoring replays the PGN; a corrupted game_flaws.fen is a counted reason."""
    game_id = await make_game(fen_override={5: "8/8/8/8/8/8/8/K6k"})

    report = await _run(session_factory, tmp_path)

    assert report.reasons.get("fen_mismatch") == 1
    values = await _flaw_values(session_factory, game_id)
    assert all(v is None for v in values[5].values())
    assert values[2]["maia_played_prob"] is not None
    assert values[8]["maia_played_prob"] is not None
    assert await _stamp(session_factory, game_id) is not None
    assert report.flaws_null == 1


@pytest.mark.asyncio
async def test_dry_run_writes_nothing(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    game_id = await make_game()

    report = await _run(session_factory, tmp_path, dry_run=True)

    assert report.games_scored == 1
    assert report.flaws_scored > 0
    assert report.games_stamped == 0
    assert await _stamp(session_factory, game_id) is None
    values = await _flaw_values(session_factory, game_id)
    assert all(v["maia_played_prob"] is None for v in values.values())


# ---------------------------------------------------------------------------
# CLI (D-10, D-16), Maia availability, status
# ---------------------------------------------------------------------------


def test_cli_db_choices() -> None:
    for db in ("dev", "benchmark", "prod"):
        assert backfill._parse_args(["--db", db]).db == db
    with pytest.raises(SystemExit):
        backfill._parse_args(["--db", "test"])


@pytest.mark.asyncio
async def test_resolve_url_delegates_to_db_url_for_target(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    test_engine: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-10: the engine-building path resolves --db through db_url_for_target."""
    game_id = await make_game()
    requested: list[str] = []
    test_url = test_engine.url.render_as_string(hide_password=False)

    def _record(target: str) -> str:
        requested.append(target)
        return test_url

    monkeypatch.setattr(backfill, "db_url_for_target", _record)

    report = await backfill.run_shard(
        db="benchmark",
        shard=0,
        num_shards=1,
        user_id=_TEST_USER_ID,
        limit=None,
        batch_games=backfill.DEFAULT_BATCH_GAMES,
        dry_run=False,
        throttle_ms=0,
        report_dir=tmp_path,
        run_stamp=_RUN_STAMP,
    )

    assert requested == ["benchmark"]
    assert report.games_stamped == 1
    assert await _stamp(session_factory, game_id) is not None


def test_shard_exits_when_maia_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No Maia session: exit EXIT_MAIA_UNAVAILABLE and never open a DB session."""
    import signal

    async def _noop_start(**_: Any) -> None:
        return None

    async def _must_not_run(**_: Any) -> None:
        raise AssertionError("run_shard must not run without Maia")

    monkeypatch.setattr(maia_engine, "start_maia", _noop_start)
    monkeypatch.setattr(maia_engine, "_session", None)
    monkeypatch.setattr(backfill, "run_shard", _must_not_run)
    monkeypatch.setattr(backfill.settings, "SENTRY_DSN", "")
    # _shard_process_entry installs SIGINT/SIGTERM handlers; restore the test runner's.
    old_int = signal.getsignal(signal.SIGINT)
    old_term = signal.getsignal(signal.SIGTERM)
    try:
        code = backfill._shard_process_entry(
            db="dev",
            shard=0,
            num_shards=1,
            user_id=None,
            limit=None,
            batch_games=backfill.DEFAULT_BATCH_GAMES,
            dry_run=False,
            throttle_ms=0,
            report_dir=str(tmp_path),
            run_stamp=_RUN_STAMP,
        )
    finally:
        signal.signal(signal.SIGINT, old_int)
        signal.signal(signal.SIGTERM, old_term)
    assert code == backfill.EXIT_MAIA_UNAVAILABLE


@pytest.mark.asyncio
async def test_status_counts(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    test_engine: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    for _ in range(3):
        await make_game()
    await _run(session_factory, tmp_path, limit=1)

    counts = await backfill.fetch_status(session_factory, _TEST_USER_ID)

    assert counts == {
        "stamped_games": 1,
        "unstamped_games_with_flaws": 2,
        "flaws_with_maia": 3,
        "flaws_total": 9,
    }
    # The CLI line carries the same four keys.
    test_url = test_engine.url.render_as_string(hide_password=False)
    monkeypatch.setattr(backfill, "db_url_for_target", lambda _target: test_url)
    await backfill._print_status("dev", _TEST_USER_ID)
    line = capsys.readouterr().out.strip().splitlines()[-1]
    assert line == "stamped_games=1 unstamped_games_with_flaws=2 flaws_with_maia=3 flaws_total=9"


# ---------------------------------------------------------------------------
# Selector helper and mode plumbing: full-mode default, CLI choices
# ---------------------------------------------------------------------------


async def _select(
    maker: async_sessionmaker[AsyncSession],
    mode: backfill.BackfillMode,
    *,
    shard: int = 0,
    num_shards: int = 1,
    cutoff: datetime | None = None,
) -> list[int]:
    async with maker() as session:
        return await backfill.select_shard_game_ids(
            session,
            shard=shard,
            num_shards=num_shards,
            user_id=_TEST_USER_ID,
            limit=None,
            mode=mode,
            cutoff=cutoff,
        )


@pytest.mark.asyncio
async def test_full_mode_default_writes_base_and_facepalm_values_and_all_stamps(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    game_id = await make_game()

    report = await _run(session_factory, tmp_path)

    assert report.mode == "full"
    assert report.games_stamped == 1
    assert await _stamp(session_factory, game_id) is not None
    assert all(stamp is not None for stamp in await _facepalm_stamps(session_factory, game_id))
    base = await _flaw_values(session_factory, game_id)
    assert all(v["maia_played_prob"] is not None for v in base.values())
    values = await _facepalm_values(session_factory, game_id)
    # Plies 2 and 8 are the white user's blunders; ply 5 is the opponent's (SEED-261114-iuv
    # Part A: it gets the spread, never the four line facts).
    assert values[2]["maia_reply_spread"] is not None
    assert values[8]["maia_reply_spread"] is not None
    assert values[5]["maia_reply_spread"] is not None
    assert all(v is None for c, v in values[5].items() if c != "maia_reply_spread")


def test_cli_mode_choices() -> None:
    assert backfill._parse_args(["--db", "dev"]).mode == "full"
    assert backfill._parse_args(["--db", "dev", "--mode", "spread"]).mode == "spread"
    with pytest.raises(SystemExit):
        backfill._parse_args(["--db", "dev", "--mode", "refutation"])
    with pytest.raises(SystemExit):
        backfill._parse_args(["--db", "dev", "--mode", "everything"])


# ---------------------------------------------------------------------------
# Spread mode (Phase 250 D-08)
# ---------------------------------------------------------------------------

_USER_BLUNDER_PLIES: tuple[int, ...] = (2, 8)
# Facts cannot hit the bar exactly (REAL inputs), so the status test seeds a clearly
# qualifying score instead.
_ABOVE_THE_BAR = 0.1


def _boards_by_ply(pgn: str) -> dict[int, tuple[chess.Board, str]]:
    """Independent pre-push board + played UCI per ply (python-chess, not the module)."""
    parsed = chess.pgn.read_game(io.StringIO(pgn))
    assert parsed is not None
    board = parsed.board()
    out: dict[int, tuple[chess.Board, str]] = {}
    for ply, node in enumerate(parsed.mainline()):
        out[ply] = (board.copy(), node.move.uci())
        board.push(node.move)
    return out


# Line after the ply-2 blunder: the game's own continuation (plies 3..8), legal by construction.
_LINE_AFTER_PLY_2 = " ".join(_boards_by_ply(_PGN)[ply][1] for ply in range(3, 9))


async def _facepalm_values(
    maker: async_sessionmaker[AsyncSession], game_id: int
) -> dict[int, dict[str, Any]]:
    async with maker() as session:
        flaws = (
            (await session.execute(select(GameFlaw).where(GameFlaw.game_id == game_id)))
            .scalars()
            .all()
        )
    return {f.ply: {c: getattr(f, c) for c in FACEPALM_COLUMNS} for f in flaws}


async def _facepalm_stamps(
    maker: async_sessionmaker[AsyncSession], game_id: int
) -> tuple[Any, Any]:
    """(facepalm_spread_completed_at, facepalm_line_completed_at)."""
    async with maker() as session:
        row = (
            await session.execute(
                select(Game.facepalm_spread_completed_at, Game.facepalm_line_completed_at).where(
                    Game.id == game_id
                )
            )
        ).one()
    return row[0], row[1]


@pytest.mark.asyncio
async def test_spread_mode_scores_and_stamps_base_stamped_game(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """Tracer (D-08): a base-stamped game gets exactly its user blunders' eight facepalm values and
    both facepalm stamps; the base values stay untouched; a rerun is a no-op."""
    game_id = await make_game(
        base_stamped=True,
        seed_base=True,
        pv={3: _LINE_AFTER_PLY_2},
    )
    # Ply 2 is a pure miss (no material loss): under best_prob_for_misses its score needs a stored
    # best-move probability (254 WR-01 / 256 D-04). The spread pass leaves the pre keys alone.
    await _set_flaw(session_factory, game_id, 2, maia_best_prob=_SEEDED_PRE["maia_best_prob"])
    base_before = await _flaw_values(session_factory, game_id)
    base_stamp_before = await _stamp(session_factory, game_id)

    report = await _run(session_factory, tmp_path, mode="spread")

    assert report.games_stamped == 1
    values = await _facepalm_values(session_factory, game_id)
    pre = _boards_by_ply(_PGN)[2]
    expected = _fact_columns(pre[0], pre[1], _LINE_AFTER_PLY_2)
    assert any(v is not None for v in expected.values()), "the fixture line must settle a depth"
    # Ply 2 (user blunder with a stored line): spread, line facts and score.
    assert values[2]["maia_reply_spread"] is not None
    assert {c: values[2][c] for c in expected} == pytest.approx(expected, rel=_REAL_REL_TOL)
    # Ply 8 (user blunder, no stored line after the last ply): spread only.
    assert values[8]["maia_reply_spread"] is not None
    assert all(values[8][c] is None for c in expected)
    # Ply 5 is the opponent's blunder: out of scope (D-06).
    assert all(v is None for v in values[5].values())
    # The base value and the base stamp are not this pass's business.
    assert await _flaw_values(session_factory, game_id) == base_before
    assert await _stamp(session_factory, game_id) == base_stamp_before
    spread_stamp, line_stamp = await _facepalm_stamps(session_factory, game_id)
    assert spread_stamp is not None
    assert line_stamp is not None
    saved = json.loads((tmp_path / f"dev-spread-{_RUN_STAMP}-shard0.json").read_text())
    assert saved["mode"] == "spread"
    assert saved["spreads_scored"] == len(_USER_BLUNDER_PLIES)
    assert saved["spreads_null"] == 0
    assert saved["scores_set"] == 1
    assert saved["scores_null"] == 1
    assert "refutations_scored" not in saved

    again = await _run(session_factory, tmp_path, mode="spread")

    assert again.games_selected == 0
    assert again.games_stamped == 0
    assert await _facepalm_values(session_factory, game_id) == values
    assert await _facepalm_stamps(session_factory, game_id) == (spread_stamp, line_stamp)


@pytest.mark.asyncio
async def test_spread_mode_selector_needs_base_stamp_and_no_spread_stamp(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    eligible = await make_game(base_stamped=True)
    await make_game()  # not base-stamped: no stored played prob to read
    spread_done = await make_game(base_stamped=True)
    async with session_factory() as session:
        await session.execute(
            update(Game)
            .where(Game.id == spread_done)
            .values(facepalm_spread_completed_at=func.now())
        )
        await session.commit()

    assert await _select(session_factory, "spread") == [eligible]


@pytest.mark.asyncio
async def test_spread_mode_shard_partition_disjoint_exhaustive(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    game_ids = {await make_game(base_stamped=True) for _ in range(_SHARD_GAMES)}
    per_shard = [
        await _select(session_factory, "spread", shard=shard, num_shards=_SHARD_COUNT)
        for shard in range(_SHARD_COUNT)
    ]
    flat = [gid for ids in per_shard for gid in ids]
    assert len(flat) == len(set(flat)), "a game landed in two shards"
    assert set(flat) == game_ids


@pytest.mark.asyncio
async def test_spread_mode_skips_game_spread_stamped_mid_run(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """require_unstamped checks the mode's own stamp: a game another lane stamped is not overwritten."""
    raced = await make_game(base_stamped=True)
    other = await make_game(base_stamped=True)
    real_write = backfill.write_game_maia_scores

    async def _stamp_then_write(session: AsyncSession, scores: Any, **kwargs: Any) -> Any:
        async with session_factory() as other_session:
            await other_session.execute(
                update(Game).where(Game.id == raced).values(facepalm_spread_completed_at=func.now())
            )
            await other_session.commit()
        return await real_write(session, scores, **kwargs)

    monkeypatch.setattr(backfill, "write_game_maia_scores", _stamp_then_write)

    report = await _run(session_factory, tmp_path, mode="spread")

    assert report.games_already_stamped == 1
    assert report.games_stamped == 1
    raced_values = await _facepalm_values(session_factory, raced)
    assert all(all(v is None for v in row.values()) for row in raced_values.values())
    assert (await _facepalm_values(session_factory, other))[2]["maia_reply_spread"] is not None


@pytest.mark.asyncio
async def test_spread_mode_game_without_user_blunder_stamped_without_replay_or_inference(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-09: opponent blunders and user mistakes only -> stamped, zero inference, no PGN replay."""
    game_id = await make_game(severities={2: 1, 5: 2, 8: 1}, base_stamped=True)
    policy_calls: list[str] = []
    replay_calls: list[Any] = []

    def _spy_policy(fen: str, elo: float) -> dict[str, float]:
        policy_calls.append(fen)
        return fake_full_policy(fen, elo)

    def _spy_replay(*args: Any, **kwargs: Any) -> Any:
        replay_calls.append(args)
        raise AssertionError("no PGN replay expected")

    monkeypatch.setattr(maia_flaw_scoring, "full_policy", _spy_policy)
    monkeypatch.setattr(maia_flaw_scoring, "replay_flaw_boards", _spy_replay)

    report = await _run(session_factory, tmp_path, mode="spread")

    assert report.games_stamped == 1
    assert policy_calls == []
    assert replay_calls == []
    spread_stamp, _line_stamp = await _facepalm_stamps(session_factory, game_id)
    assert spread_stamp is not None
    values = await _facepalm_values(session_factory, game_id)
    assert all(all(v is None for v in row.values()) for row in values.values())
    assert (await _select(session_factory, "spread")) == []


@pytest.mark.asyncio
async def test_spread_mode_replays_only_blunder_plies(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-05: the PGN replay is asked for the user-blunder plies only."""
    await make_game(base_stamped=True)
    wanted: list[set[int]] = []
    real_replay = maia_flaw_scoring.replay_flaw_boards

    def _spy_replay(pgn_text: str, plies: Any) -> Any:
        wanted.append(set(plies))
        return real_replay(pgn_text, plies)

    monkeypatch.setattr(maia_flaw_scoring, "replay_flaw_boards", _spy_replay)

    await _run(session_factory, tmp_path, mode="spread")

    assert wanted == [{2, 8}]


@pytest.mark.asyncio
async def test_spread_status_counts(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    test_engine: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exact spread counts after one of two games was scored: 2 user blunders each, one scored."""
    for _ in range(2):
        game_id = await make_game(base_stamped=True, seed_base=True, pv={3: _LINE_AFTER_PLY_2})
        # Ply 2 is a pure miss: its score needs a best-move probability (254 WR-01 / 256 D-04).
        await _set_flaw(session_factory, game_id, 2, maia_best_prob=_SEEDED_PRE["maia_best_prob"])
    await _run(session_factory, tmp_path, limit=1, mode="spread")
    # D-02: the pass writes facts only; the expression (the status counts) scores them.
    expression_counts = await backfill.fetch_status(session_factory, _TEST_USER_ID, "spread")
    assert expression_counts["user_blunders_with_score"] == 1
    # Make the scored game's ply-2 facts score above the bar so the qualifying count is exercised
    # (the counts read the expression over the facts, never the stored column, 254 D-01).
    async with session_factory() as session:
        await session.execute(
            update(GameFlaw)
            .where(GameFlaw.user_id == _TEST_USER_ID, GameFlaw.material_loss.is_not(None))
            .values(
                **facepalm_fact_columns(
                    FACEPALM_SCORE_MIN + _ABOVE_THE_BAR, lam=FACEPALM_DRILL_LAMBDA
                )
            )
        )
        await session.commit()

    counts = await backfill.fetch_status(session_factory, _TEST_USER_ID, "spread")

    assert counts == {
        "spread_stamped_games": 1,
        "spread_pending_games": 1,
        "user_blunders_total": 4,
        "user_blunders_with_spread": 2,
        "user_blunders_with_score": 1,
        "user_blunders_qualifying": 1,
    }
    test_url = test_engine.url.render_as_string(hide_password=False)
    monkeypatch.setattr(backfill, "db_url_for_target", lambda _target: test_url)
    await backfill._print_status("dev", _TEST_USER_ID, "spread")
    line = capsys.readouterr().out.strip().splitlines()[-1]
    assert line == (
        "spread_stamped_games=1 spread_pending_games=1 user_blunders_total=4 "
        "user_blunders_with_spread=2 user_blunders_with_score=1 user_blunders_qualifying=1"
    )


# ---------------------------------------------------------------------------
# Line mode (Phase 250 D-18)
# ---------------------------------------------------------------------------

_CUTOFF = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
_BEFORE_CUTOFF = _CUTOFF - timedelta(days=1)
_AFTER_CUTOFF = _CUTOFF + timedelta(days=1)
_STORED_SPREAD = 3.5
# The ply-2 line cut to two plies: still legal (a prefix of the game's continuation), but too short
# for the quiet walk to settle a loss, unlike the full line.
_SHORT_LINE_AFTER_PLY_2 = " ".join(_LINE_AFTER_PLY_2.split(" ")[:2])


async def _set_game(maker: async_sessionmaker[AsyncSession], game_id: int, **values: Any) -> None:
    async with maker() as session:
        await session.execute(update(Game).where(Game.id == game_id).values(**values))
        await session.commit()


async def _set_flaw(
    maker: async_sessionmaker[AsyncSession], game_id: int, ply: int, **values: Any
) -> None:
    async with maker() as session:
        await session.execute(
            update(GameFlaw)
            .where(GameFlaw.game_id == game_id, GameFlaw.ply == ply)
            .values(**values)
        )
        await session.commit()


async def _set_line(
    maker: async_sessionmaker[AsyncSession], game_id: int, ply: int, pv: str | None
) -> None:
    async with maker() as session:
        await session.execute(
            update(GamePosition)
            .where(GamePosition.game_id == game_id, GamePosition.ply == ply)
            .values(pv=pv)
        )
        await session.commit()


async def _spread_stamped_game(
    maker: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    *,
    line_stamp: datetime | None,
    pv: str | None = _LINE_AFTER_PLY_2,
) -> int:
    """A base- and spread-stamped game (as after the spread pass) with a stored spread on ply 2."""
    game_id = await make_game(base_stamped=True, seed_base=True, pv={3: pv} if pv else None)
    await _set_game(
        maker,
        game_id,
        facepalm_spread_completed_at=func.now(),
        facepalm_line_completed_at=line_stamp,
    )
    # Ply 2 is a pure miss: its score needs a best-move probability (254 WR-01 / 256 D-04).
    await _set_flaw(
        maker,
        game_id,
        2,
        maia_reply_spread=_STORED_SPREAD,
        maia_best_prob=_SEEDED_PRE["maia_best_prob"],
    )
    return game_id


def _fact_columns(pre: chess.Board, played: str, line: str | None) -> dict[str, Any]:
    """The stored fact columns of a played line alone (259 D-05): its mate ply under the quiet rule
    and the decaying-mean loss from the one write-time function (the loss needs no best line)."""
    return {
        "line_mate_ply": quiet_line_facts(pre, played, line).mate_ply,
        "material_loss": facepalm_material_inputs(pre, played, line, None).loss,
    }


def _expected_line_columns(line: str) -> dict[str, Any]:
    pre, played = _boards_by_ply(_PGN)[2]
    return _fact_columns(pre, played, line)


@pytest.mark.asyncio
async def test_line_mode_selector_rules(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """Spread-stamped games whose line stamp is NULL or older than the cutoff; nothing else."""
    null_stamp = await _spread_stamped_game(session_factory, make_game, line_stamp=None)
    old_stamp = await _spread_stamped_game(session_factory, make_game, line_stamp=_BEFORE_CUTOFF)
    await _spread_stamped_game(session_factory, make_game, line_stamp=_AFTER_CUTOFF)
    await _spread_stamped_game(session_factory, make_game, line_stamp=_CUTOFF)
    no_spread = await make_game(base_stamped=True)  # spread pass not done yet
    await make_game(flaw_plies=())  # zero flaws, never selected

    selected = await _select(session_factory, "line", cutoff=_CUTOFF)

    assert set(selected) == {null_stamp, old_stamp}
    assert no_spread not in selected


@pytest.mark.asyncio
async def test_line_mode_selector_binds_the_cutoff_never_interpolates_it(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """T-250-19: the cutoff reaches the SQL as a bound parameter, not as text."""
    await _spread_stamped_game(session_factory, make_game, line_stamp=None)
    recorded: list[tuple[str, dict[str, Any]]] = []

    class _Recorder:
        def __init__(self, session: AsyncSession) -> None:
            self._session = session

        async def execute(self, statement: Any, params: dict[str, Any]) -> Any:
            recorded.append((str(statement), params))
            return await self._session.execute(statement, params)

    async with session_factory() as session:
        await backfill.select_shard_game_ids(
            _Recorder(session),  # ty: ignore[invalid-argument-type] -- spy wrapper
            shard=0,
            num_shards=1,
            user_id=_TEST_USER_ID,
            limit=None,
            mode="line",
            cutoff=_CUTOFF,
        )

    ((sql, params),) = recorded
    assert params["cutoff"] == _CUTOFF
    assert ":cutoff" in sql
    assert _CUTOFF.isoformat() not in sql
    assert str(_CUTOFF.year) not in sql


@pytest.mark.asyncio
async def test_line_mode_selector_requires_a_cutoff(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    with pytest.raises(ValueError, match="cutoff"):
        await _select(session_factory, "line")


@pytest.mark.asyncio
async def test_line_mode_recomputes_rows_that_already_hold_values(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """D-18: a game last line-scored before the cutoff is re-scored even though its rows hold
    values; the new line's facts and score replace the old, the spread and base stay untouched."""
    game_id = await _spread_stamped_game(session_factory, make_game, line_stamp=_BEFORE_CUTOFF)
    old_facts = _expected_line_columns(_LINE_AFTER_PLY_2)
    # The scalar pair is written together (CHECK); the game has no stored best line, so missed is 0.0.
    await _set_flaw(session_factory, game_id, 2, **old_facts, material_missed=0.0)
    # A repair shortened the stored line after the last pass.
    await _set_line(session_factory, game_id, 3, _SHORT_LINE_AFTER_PLY_2)
    new_facts = _expected_line_columns(_SHORT_LINE_AFTER_PLY_2)
    assert new_facts != old_facts, "the fixture lines must settle different depths"
    base_before = await _flaw_values(session_factory, game_id)

    report = await _run(session_factory, tmp_path, mode="line", cutoff=_CUTOFF)

    assert report.games_stamped == 1
    assert report.cutoff == _CUTOFF.isoformat()
    row = (await _facepalm_values(session_factory, game_id))[2]
    assert {c: row[c] for c in new_facts} == pytest.approx(new_facts, rel=_REAL_REL_TOL)
    assert row["maia_reply_spread"] == _STORED_SPREAD
    assert row["material_loss"] != old_facts["material_loss"]
    assert await _flaw_values(session_factory, game_id) == base_before
    _, line_stamp = await _facepalm_stamps(session_factory, game_id)
    assert line_stamp >= _CUTOFF
    saved = json.loads((tmp_path / f"dev-line-{_RUN_STAMP}-shard0.json").read_text())
    assert saved["cutoff"] == _CUTOFF.isoformat()
    assert saved["mode"] == "line"
    assert saved["spreads_scored"] == 0
    assert saved["scores_set"] + saved["scores_null"] == 2


# Ply 5 is Black's a6, the opponent's blunder in the white-user fixture game; its stored line is the
# game's own continuation after it (plies 6..8).
_OPPONENT_PLY = 5
_LINE_AFTER_PLY_5 = " ".join(_boards_by_ply(_PGN)[ply][1] for ply in range(6, 9))
_OPPONENT_LINE_KEYS = (
    "line_mate_ply",
    "best_line_mate_ply",
    "material_loss",
    "material_missed",
)


def _expected_opponent_line_columns(line: str) -> dict[str, Any]:
    """The four line facts the module's own derivation yields for the opponent's ply 5 (no best line)."""
    pre, played = _boards_by_ply(_PGN)[_OPPONENT_PLY]
    scalars = facepalm_material_inputs(pre, played, line, None)
    return {
        "line_mate_ply": quiet_line_facts(pre, played, line).mate_ply,
        "best_line_mate_ply": quiet_best_line_facts(pre, None).opponent_mate_ply,
        "material_loss": scalars.loss,
        "material_missed": scalars.missed,
    }


async def _opponent_line_game(maker: async_sessionmaker[AsyncSession], make_game: MakeGame) -> int:
    """A spread-stamped game whose opponent blunder (ply 5) has a stored line and stored Maia values."""
    game_id = await _spread_stamped_game(maker, make_game, line_stamp=_BEFORE_CUTOFF)
    await _set_line(maker, game_id, _OPPONENT_PLY + 1, _LINE_AFTER_PLY_5)
    await _set_flaw(
        maker,
        game_id,
        _OPPONENT_PLY,
        maia_reply_spread=_STORED_SPREAD,
        maia_best_prob=_SEEDED_PRE["maia_best_prob"],
        maia_pre_spread=_SEEDED_PRE["maia_pre_spread"],
    )
    return game_id


@pytest.mark.asyncio
async def test_line_mode_writes_opponent_line_facts_without_maia(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEED-261114-iuv Part A step 4: the line pass also writes the opponent blunder's four line
    facts (equal to the derivation), leaves every Maia and pre value alone, moves only the line
    stamp, and never calls Maia; the user ply keeps the existing expectation."""
    game_id = await _opponent_line_game(session_factory, make_game)
    expected_opponent = _expected_opponent_line_columns(_LINE_AFTER_PLY_5)
    assert any(v is not None for v in expected_opponent.values())
    base_before = await _flaw_values(session_factory, game_id)
    pre_before = await _pre_values(session_factory, game_id)
    spread_stamp_before = (await _facepalm_stamps(session_factory, game_id))[0]

    def _must_not_infer(fen: str, elo: float) -> dict[str, float]:
        raise AssertionError("line mode must not run inference")

    monkeypatch.setattr(maia_flaw_scoring, "full_policy", _must_not_infer)
    started: list[object] = []
    monkeypatch.setattr(maia_engine, "start_maia", lambda **kw: started.append(kw))

    report = await _run(session_factory, tmp_path, mode="line", cutoff=_CUTOFF)

    assert started == []
    assert report.games_stamped == 1
    rows = await _facepalm_values(session_factory, game_id)
    assert {c: rows[_OPPONENT_PLY][c] for c in expected_opponent} == expected_opponent
    user_expected = _expected_line_columns(_LINE_AFTER_PLY_2)
    assert {c: rows[2][c] for c in user_expected} == user_expected
    # The spread, the base value and the pre keys of every row are untouched.
    assert rows[_OPPONENT_PLY]["maia_reply_spread"] == _STORED_SPREAD
    assert await _flaw_values(session_factory, game_id) == base_before
    assert await _pre_values(session_factory, game_id) == pre_before
    spread_stamp, line_stamp = await _facepalm_stamps(session_factory, game_id)
    assert spread_stamp == spread_stamp_before
    assert line_stamp >= _CUTOFF


@pytest.mark.asyncio
async def test_reports_carry_opponent_score_counters_and_keep_user_counters(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """Line run report: user counters as before (2 user blunders), the opponent blunder in its own
    opponent_scores_set / opponent_scores_null pair; the opponent spread and pre counters stay 0 in
    line mode. A full-mode report carries the same two keys."""
    await _opponent_line_game(session_factory, make_game)

    report = await _run(session_factory, tmp_path, mode="line", cutoff=_CUTOFF)

    saved = json.loads((tmp_path / f"dev-line-{_RUN_STAMP}-shard0.json").read_text())
    assert saved["scores_set"] + saved["scores_null"] == 2
    assert saved["spreads_scored"] == 0
    assert saved["opponent_scores_set"] + saved["opponent_scores_null"] == 1
    assert saved["opponent_scores_set"] == report.opponent_scores_set
    assert saved["opponent_spreads_scored"] == saved["opponent_spreads_null"] == 0
    assert saved["opponent_pre_scored"] == saved["opponent_pre_null"] == 0

    # A full-mode run (one unstamped game, one opponent blunder) carries the same two keys.
    await make_game()
    await _run(session_factory, tmp_path, mode="full")
    full = json.loads((tmp_path / f"dev-full-{_RUN_STAMP}-shard0.json").read_text())
    assert full["opponent_scores_set"] + full["opponent_scores_null"] == 1


def test_combined_total_line_includes_opponent_score_counters() -> None:
    reports = [
        {"opponent_scores_set": 2, "opponent_scores_null": 1},
        {"opponent_scores_set": 3, "opponent_scores_null": 0},
    ]
    line = backfill._combined_total_line(reports)
    assert "opponent_scores_set=5" in line
    assert "opponent_scores_null=1" in line


@pytest.mark.asyncio
async def test_line_mode_blunder_without_a_line_gets_one_later(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """A blunder that had no line (NULL facts) gets facts and a score once a line is stored."""
    game_id = await _spread_stamped_game(
        session_factory, make_game, line_stamp=_BEFORE_CUTOFF, pv=None
    )
    before = (await _facepalm_values(session_factory, game_id))[2]
    assert {c: v for c, v in before.items() if c != "maia_reply_spread"} == dict.fromkeys(
        before.keys() - {"maia_reply_spread"}
    )
    await _set_line(session_factory, game_id, 3, _LINE_AFTER_PLY_2)

    await _run(session_factory, tmp_path, mode="line", cutoff=_CUTOFF)

    row = (await _facepalm_values(session_factory, game_id))[2]
    expected = _expected_line_columns(_LINE_AFTER_PLY_2)
    assert {c: row[c] for c in expected} == pytest.approx(expected, rel=_REAL_REL_TOL)
    assert row["material_loss"] is not None


@pytest.mark.asyncio
async def test_line_mode_resumes_with_the_same_cutoff(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """The cutoff is the checkpoint: a run cut short is finished by re-running with the SAME
    cutoff, which skips what was done; a later cutoff selects everything again."""
    games = [
        await _spread_stamped_game(session_factory, make_game, line_stamp=_BEFORE_CUTOFF)
        for _ in range(3)
    ]

    first = await _run(session_factory, tmp_path, mode="line", cutoff=_CUTOFF, limit=1)
    resumed = await _run(session_factory, tmp_path, mode="line", cutoff=_CUTOFF)
    third = await _run(session_factory, tmp_path, mode="line", cutoff=_CUTOFF)

    assert first.games_stamped == 1
    assert resumed.games_selected == 2
    assert resumed.games_stamped == 2
    assert third.games_selected == 0
    for game_id in games:
        assert (await _facepalm_stamps(session_factory, game_id))[1] >= _CUTOFF
    # A new full recompute: a cutoff after every stamp selects all games again.
    later = datetime.now(timezone.utc) + timedelta(minutes=1)
    assert len(await _select(session_factory, "line", cutoff=later)) == 3


@pytest.mark.asyncio
async def test_line_mode_shard_never_starts_maia_and_exits_ok_without_it(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pitfall 4: no start_maia, no EXIT_MAIA_UNAVAILABLE gate, no inference; the work is done."""
    game_id = await _spread_stamped_game(session_factory, make_game, line_stamp=None)

    async def _must_not_start(**_: Any) -> None:
        raise AssertionError("line mode must not start Maia")

    def _must_not_infer(fen: str, elo: float) -> dict[str, float]:
        raise AssertionError("line mode must not run inference")

    monkeypatch.setattr(maia_engine, "start_maia", _must_not_start)
    monkeypatch.setattr(maia_engine, "_session", None)
    monkeypatch.setattr(maia_flaw_scoring, "full_policy", _must_not_infer)

    code = await backfill._start_maia_and_run(
        db="dev",
        shard=0,
        num_shards=1,
        user_id=_TEST_USER_ID,
        limit=None,
        batch_games=backfill.DEFAULT_BATCH_GAMES,
        dry_run=False,
        throttle_ms=0,
        report_dir=tmp_path,
        run_stamp=_RUN_STAMP,
        session_maker=session_factory,
        mode="line",
        cutoff=_CUTOFF,
    )

    assert code == backfill.EXIT_OK
    assert (await _facepalm_stamps(session_factory, game_id))[1] >= _CUTOFF


def test_line_mode_process_entry_threads_the_cutoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[dict[str, Any]] = []

    async def _record(**kwargs: Any) -> int:
        seen.append(kwargs)
        return backfill.EXIT_OK

    monkeypatch.setattr(backfill, "_start_maia_and_run", _record)
    monkeypatch.setattr(backfill.settings, "SENTRY_DSN", "")
    old_int = signal.getsignal(signal.SIGINT)
    old_term = signal.getsignal(signal.SIGTERM)
    try:
        code = backfill._shard_process_entry(
            db="dev",
            shard=0,
            num_shards=1,
            user_id=None,
            limit=None,
            batch_games=backfill.DEFAULT_BATCH_GAMES,
            dry_run=False,
            throttle_ms=0,
            report_dir=str(tmp_path),
            run_stamp=_RUN_STAMP,
            mode="line",
            cutoff=_CUTOFF,
        )
    finally:
        signal.signal(signal.SIGINT, old_int)
        signal.signal(signal.SIGTERM, old_term)
    assert code == backfill.EXIT_OK
    assert seen[0]["cutoff"] == _CUTOFF
    assert seen[0]["mode"] == "line"


def test_cli_cutoff_rules(capsys: pytest.CaptureFixture[str]) -> None:
    """--cutoff is required for line mode, must carry an offset, and is rejected elsewhere."""
    ok = backfill._parse_args(
        ["--db", "dev", "--mode", "line", "--cutoff", "2026-11-10T12:00:00+00:00"]
    )
    assert ok.cutoff == _CUTOFF
    with pytest.raises(SystemExit) as no_cutoff:
        backfill._parse_args(["--db", "dev", "--mode", "line"])
    assert no_cutoff.value.code == 2
    assert "--cutoff" in capsys.readouterr().err
    with pytest.raises(SystemExit) as naive:
        backfill._parse_args(["--db", "dev", "--mode", "line", "--cutoff", "2026-11-10T12:00:00"])
    assert naive.value.code == 2
    assert "--cutoff" in capsys.readouterr().err
    with pytest.raises(SystemExit) as garbage:
        backfill._parse_args(["--db", "dev", "--mode", "line", "--cutoff", "yesterday"])
    assert garbage.value.code == 2
    for mode in ("full", "spread"):
        with pytest.raises(SystemExit) as wrong_mode:
            backfill._parse_args(
                ["--db", "dev", "--mode", mode, "--cutoff", "2026-11-10T12:00:00+00:00"]
            )
        assert wrong_mode.value.code == 2
        assert "--cutoff" in capsys.readouterr().err


@pytest.mark.asyncio
async def test_line_status_counts(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    test_engine: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Line status: games done since the cutoff, games pending, and the score counts."""
    for _ in range(2):
        game_id = await _spread_stamped_game(session_factory, make_game, line_stamp=_BEFORE_CUTOFF)
        # A stored line after the opponent blunder (ply 5), so the run can give it line facts.
        await _set_line(session_factory, game_id, _OPPONENT_PLY + 1, _LINE_AFTER_PLY_5)
    await _run(session_factory, tmp_path, mode="line", cutoff=_CUTOFF, limit=1)

    counts = await backfill.fetch_status(session_factory, _TEST_USER_ID, "line", _CUTOFF)

    assert counts["line_done_since_cutoff"] == 1
    assert counts["line_pending_games"] == 1
    assert counts["user_blunders_total"] == 4
    assert counts["user_blunders_with_score"] == 1
    assert list(counts)[:2] == ["line_done_since_cutoff", "line_pending_games"]
    # The unchanged user keys come first, then the opponent counts (line facts of both sides).
    assert list(counts) == [
        "line_done_since_cutoff",
        "line_pending_games",
        "user_blunders_total",
        "user_blunders_with_score",
        "user_blunders_qualifying",
        "opponent_blunders_total",
        "opponent_blunders_with_material_inputs",
        "opponent_blunders_with_score",
        "user_blunders_with_material_inputs",
    ]
    # Two games with one opponent blunder (ply 5) each; the run (limit=1) covered one game, so one
    # opponent blunder holds stored material inputs. Its score is NULL here: the fixture row has no Maia values.
    assert counts["opponent_blunders_total"] == 2
    assert counts["opponent_blunders_with_material_inputs"] == 1
    assert counts["opponent_blunders_with_score"] == 0
    test_url = test_engine.url.render_as_string(hide_password=False)
    monkeypatch.setattr(backfill, "db_url_for_target", lambda _target: test_url)
    await backfill._print_status("dev", _TEST_USER_ID, "line", _CUTOFF)
    line = capsys.readouterr().out.strip().splitlines()[-1]
    assert line.startswith("line_done_since_cutoff=1 line_pending_games=1 ")


# ---------------------------------------------------------------------------
# Pre mode (Phase 254 D-08)
# ---------------------------------------------------------------------------

# The best move of the ply-2 decision position (1. e4 e5, white to move): legal, so the fake
# policy holds it. Ply 8 gets no best line, which exercises the best_move_missing reason.
_BEST_PV_AT_PLY_2 = "g1f3"
# Distinct stand-ins for values the pre pass must never touch.
_SEEDED_FACEPALM: dict[str, Any] = {
    "maia_reply_spread": 3.5,
    "material_loss": 3.5,
    "material_missed": 0.5,
}


async def _pre_values(
    maker: async_sessionmaker[AsyncSession], game_id: int
) -> dict[int, dict[str, Any]]:
    async with maker() as session:
        flaws = (
            (await session.execute(select(GameFlaw).where(GameFlaw.game_id == game_id)))
            .scalars()
            .all()
        )
    return {f.ply: {c: getattr(f, c) for c in FACEPALM_PRE_COLUMNS} for f in flaws}


async def _columns_except_pre(
    maker: async_sessionmaker[AsyncSession], game_id: int
) -> dict[int, dict[str, Any]]:
    """Every game_flaws column but the two pre keys, per ply."""
    columns = [c for c in GameFlaw.__table__.columns if c.name not in FACEPALM_PRE_COLUMNS]
    async with maker() as session:
        rows = (
            await session.execute(select(*columns).where(GameFlaw.game_id == game_id))
        ).mappings()
        return {row["ply"]: dict(row) for row in rows}


async def _pre_stamp(maker: async_sessionmaker[AsyncSession], game_id: int) -> Any:
    async with maker() as session:
        return (
            await session.execute(select(Game.facepalm_pre_completed_at).where(Game.id == game_id))
        ).scalar_one()


async def _stamps_but_pre(maker: async_sessionmaker[AsyncSession], game_id: int) -> tuple[Any, ...]:
    async with maker() as session:
        row = (
            await session.execute(
                select(
                    Game.maia_flaws_completed_at,
                    Game.facepalm_spread_completed_at,
                    Game.facepalm_line_completed_at,
                ).where(Game.id == game_id)
            )
        ).one()
    return tuple(row)


def _expected_pre_spread(fen: str) -> float:
    """2 ** Shannon entropy (bits) of the fake policy at `fen`, computed with plain math."""
    probs = fake_full_policy(fen, 1500.0).values()
    return float(2.0 ** -sum(p * math.log2(p) for p in probs))


async def _pre_game(
    maker: async_sessionmaker[AsyncSession], make_game: MakeGame, **kwargs: Any
) -> int:
    """A base-stamped game with the ply-2 best line and already written facepalm values on ply 2."""
    game_id = await make_game(
        base_stamped=True,
        seed_base=True,
        pv={2: _BEST_PV_AT_PLY_2, 3: _LINE_AFTER_PLY_2},
        **kwargs,
    )
    await _set_flaw(maker, game_id, 2, **_SEEDED_FACEPALM)
    return game_id


@pytest.mark.asyncio
async def test_pre_mode_writes_only_pre_keys_and_stamp(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tracer (D-08): one inference at each user blunder's pre-blunder board fills maia_best_prob
    and maia_pre_spread and stamps the pre stamp; every other column and stamp is untouched."""
    game_id = await _pre_game(session_factory, make_game)
    columns_before = await _columns_except_pre(session_factory, game_id)
    stamps_before = await _stamps_but_pre(session_factory, game_id)
    policy_calls: list[str] = []

    def _spy_policy(fen: str, elo: float) -> dict[str, float]:
        policy_calls.append(fen)
        return fake_full_policy(fen, elo)

    monkeypatch.setattr(maia_flaw_scoring, "full_policy", _spy_policy)

    report = await _run(session_factory, tmp_path, mode="pre")

    assert report.mode == "pre"
    assert report.games_stamped == 1
    boards = _boards_by_ply(_PGN)
    # One inference per user blunder (plies 2 and 8), each at the PRE-blunder position.
    assert policy_calls == [boards[2][0].fen(), boards[8][0].fen()]
    values = await _pre_values(session_factory, game_id)
    ply2_fen = boards[2][0].fen()
    assert values[2]["maia_best_prob"] == pytest.approx(
        fake_full_policy(ply2_fen, 1500.0)[_BEST_PV_AT_PLY_2], rel=1e-5
    )
    assert values[2]["maia_pre_spread"] == pytest.approx(_expected_pre_spread(ply2_fen), rel=1e-5)
    # Ply 8 has no best line: the best-move probability stays NULL, the spread is still stored.
    assert values[8]["maia_best_prob"] is None
    assert values[8]["maia_pre_spread"] == pytest.approx(
        _expected_pre_spread(boards[8][0].fen()), rel=1e-5
    )
    # Ply 5 is the opponent's blunder: out of scope.
    assert values[5] == {"maia_best_prob": None, "maia_pre_spread": None}
    # Nothing but the two pre keys changed, on rows or on games.
    assert await _columns_except_pre(session_factory, game_id) == columns_before
    assert await _stamps_but_pre(session_factory, game_id) == stamps_before
    assert await _pre_stamp(session_factory, game_id) is not None
    saved = json.loads((tmp_path / f"dev-pre-{_RUN_STAMP}-shard0.json").read_text())
    assert saved["mode"] == "pre"
    assert saved["pre_scored"] == 2
    assert saved["pre_null"] == 0
    assert saved["reasons"] == {"best_move_missing": 1}


@pytest.mark.asyncio
async def test_pre_mode_resumes(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """The stamp is the checkpoint: a second run selects 0 games and writes nothing; clearing the
    stamp selects the game again."""
    game_id = await _pre_game(session_factory, make_game)

    first = await _run(session_factory, tmp_path, mode="pre")
    values = await _pre_values(session_factory, game_id)
    stamp = await _pre_stamp(session_factory, game_id)
    second = await _run(session_factory, tmp_path, mode="pre")

    assert first.games_stamped == 1
    assert second.games_selected == 0
    assert second.games_stamped == 0
    assert await _pre_values(session_factory, game_id) == values
    assert await _pre_stamp(session_factory, game_id) == stamp
    await _set_game(session_factory, game_id, facepalm_pre_completed_at=None)
    assert await _select(session_factory, "pre") == [game_id]


@pytest.mark.asyncio
async def test_pre_mode_selector_needs_base_stamp_and_no_pre_stamp(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    eligible = await make_game(base_stamped=True)
    await make_game()  # not base-stamped: the hook or the full pass will fill the pre inputs
    pre_done = await make_game(base_stamped=True)
    await _set_game(session_factory, pre_done, facepalm_pre_completed_at=func.now())
    await make_game(flaw_plies=(), base_stamped=True)  # zero flaws, never selected

    assert await _select(session_factory, "pre") == [eligible]


@pytest.mark.asyncio
async def test_pre_mode_shard_partition_disjoint_exhaustive(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    game_ids = {await make_game(base_stamped=True) for _ in range(_SHARD_GAMES)}
    per_shard = [
        await _select(session_factory, "pre", shard=shard, num_shards=_SHARD_COUNT)
        for shard in range(_SHARD_COUNT)
    ]
    flat = [gid for ids in per_shard for gid in ids]
    assert len(flat) == len(set(flat)), "a game landed in two shards"
    assert set(flat) == game_ids


@pytest.mark.asyncio
async def test_pre_mode_status_counts(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    test_engine: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exact pre counts after one of two games was scored: 2 user blunders each, one scored,
    one best-move probability (ply 2) and two pre spreads on the scored game."""
    await _pre_game(session_factory, make_game)
    await _pre_game(session_factory, make_game)
    await _run(session_factory, tmp_path, limit=1, mode="pre")

    counts = await backfill.fetch_status(session_factory, _TEST_USER_ID, "pre")

    assert counts == {
        "pre_stamped_games": 1,
        "pre_pending_games": 1,
        "user_blunders_total": 4,
        "user_blunders_with_best_prob": 1,
        "user_blunders_with_pre_spread": 2,
    }
    test_url = test_engine.url.render_as_string(hide_password=False)
    monkeypatch.setattr(backfill, "db_url_for_target", lambda _target: test_url)
    await backfill._print_status("dev", _TEST_USER_ID, "pre")
    line = capsys.readouterr().out.strip().splitlines()[-1]
    assert line == (
        "pre_stamped_games=1 pre_pending_games=1 user_blunders_total=4 "
        "user_blunders_with_best_prob=1 user_blunders_with_pre_spread=2"
    )


def test_pre_mode_needs_maia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No Maia session: the pre mode exits EXIT_MAIA_UNAVAILABLE like the spread mode and never
    opens a DB session."""

    async def _noop_start(**_: Any) -> None:
        return None

    async def _must_not_run(**_: Any) -> None:
        raise AssertionError("run_shard must not run without Maia")

    monkeypatch.setattr(maia_engine, "start_maia", _noop_start)
    monkeypatch.setattr(maia_engine, "_session", None)
    monkeypatch.setattr(backfill, "run_shard", _must_not_run)
    monkeypatch.setattr(backfill.settings, "SENTRY_DSN", "")
    old_int = signal.getsignal(signal.SIGINT)
    old_term = signal.getsignal(signal.SIGTERM)
    try:
        code = backfill._shard_process_entry(
            db="dev",
            shard=0,
            num_shards=1,
            user_id=None,
            limit=None,
            batch_games=backfill.DEFAULT_BATCH_GAMES,
            dry_run=False,
            throttle_ms=0,
            report_dir=str(tmp_path),
            run_stamp=_RUN_STAMP,
            mode="pre",
        )
    finally:
        signal.signal(signal.SIGINT, old_int)
        signal.signal(signal.SIGTERM, old_term)
    assert code == backfill.EXIT_MAIA_UNAVAILABLE


def test_cli_accepts_pre_mode_and_rejects_cutoff_with_it() -> None:
    assert backfill._parse_args(["--db", "dev", "--mode", "pre"]).mode == "pre"
    assert "pre" in backfill.BACKFILL_MODE_CHOICES
    with pytest.raises(SystemExit):
        backfill._parse_args(
            ["--db", "dev", "--mode", "pre", "--cutoff", "2026-11-10T12:00:00+00:00"]
        )


# ---------------------------------------------------------------------------
# Line and spread modes carry the Phase 254 fact keys (D-09), never the pre keys (D-08)
# ---------------------------------------------------------------------------

# Best lines at the ply-2 decision position (1. e4 e5, white to move). The first is the game's own
# continuation; the second is the scholar's mate, so it settles a mate ply and a different missed gain.
_BEST_LINE_AT_PLY_2 = " ".join(_boards_by_ply(_PGN)[ply][1] for ply in range(2, 9))
_OTHER_BEST_LINE_AT_PLY_2 = "d1h5 b8c6 f1c4 g8f6 h5f7"
# Stand-ins for already written Maia values the line and spread passes must leave alone.
_SEEDED_PRE: dict[str, float] = {"maia_best_prob": 0.375, "maia_pre_spread": 4.25}
_NEW_FACT_COLUMNS: tuple[str, ...] = (
    "material_loss",
    "material_missed",
    "line_mate_ply",
    "best_line_mate_ply",
)


def _expected_new_facts(best_line: str) -> dict[str, Any]:
    """The four fact columns of the ply-2 blunder, from the module's own fact functions."""
    pre, played = _boards_by_ply(_PGN)[2]
    scalars = facepalm_material_inputs(pre, played, _LINE_AFTER_PLY_2, best_line)
    return {
        "material_loss": scalars.loss,
        "material_missed": scalars.missed,
        "line_mate_ply": quiet_line_facts(pre, played, _LINE_AFTER_PLY_2).mate_ply,
        "best_line_mate_ply": quiet_best_line_facts(pre, best_line).opponent_mate_ply,
    }


async def _fact_game(
    maker: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    *,
    line_stamp: datetime | None,
    best_line: str = _BEST_LINE_AT_PLY_2,
) -> int:
    """A base- and spread-stamped game with both stored lines, a stored spread on ply 2 and
    already written Maia values (base, spread and the two pre keys) that the passes must not touch."""
    game_id = await make_game(
        base_stamped=True,
        seed_base=True,
        pv={2: best_line, 3: _LINE_AFTER_PLY_2},
    )
    await _set_game(
        maker,
        game_id,
        facepalm_spread_completed_at=func.now(),
        facepalm_line_completed_at=line_stamp,
    )
    await _set_flaw(maker, game_id, 2, maia_reply_spread=_STORED_SPREAD, **_SEEDED_PRE)
    return game_id


async def _maia_values(maker: async_sessionmaker[AsyncSession], game_id: int) -> dict[str, Any]:
    """The four stored Maia values of the ply-2 blunder."""
    async with maker() as session:
        row = (
            await session.execute(
                select(
                    GameFlaw.maia_played_prob,
                    GameFlaw.maia_reply_spread,
                    GameFlaw.maia_best_prob,
                    GameFlaw.maia_pre_spread,
                ).where(GameFlaw.game_id == game_id, GameFlaw.ply == 2)
            )
        ).one()
    return dict(row._mapping)


@pytest.mark.asyncio
async def test_line_mode_writes_both_arrays_both_mate_plies_and_no_maia_value(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """D-09 / 259 D-05: the line pass writes material_loss, material_missed, line_mate_ply and
    best_line_mate_ply (and no legacy column, no array) from the stored lines (pv at ply + 1 and at ply),
    and no Maia value: the base value, the spread and the two pre keys keep their seeded values."""
    game_id = await _fact_game(session_factory, make_game, line_stamp=_BEFORE_CUTOFF)
    maia_before = await _maia_values(session_factory, game_id)

    report = await _run(session_factory, tmp_path, mode="line", cutoff=_CUTOFF)

    assert report.games_stamped == 1
    row = (await _facepalm_values(session_factory, game_id))[2]
    expected = _expected_new_facts(_BEST_LINE_AT_PLY_2)
    assert expected["material_missed"] is not None, "the best line must settle a depth"
    assert {c: row[c] for c in _NEW_FACT_COLUMNS} == pytest.approx(expected, rel=_REAL_REL_TOL)
    played = _expected_line_columns(_LINE_AFTER_PLY_2)
    assert {c: row[c] for c in played} == pytest.approx(played, rel=_REAL_REL_TOL)
    # No Maia value is written by the line pass.
    assert await _maia_values(session_factory, game_id) == maia_before
    assert maia_before["maia_best_prob"] == _SEEDED_PRE["maia_best_prob"]
    assert maia_before["maia_pre_spread"] == _SEEDED_PRE["maia_pre_spread"]


@pytest.mark.asyncio
async def test_line_mode_picks_up_a_changed_best_line_with_a_new_cutoff(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """A best line at the flaw ply that a repair rewrites between two line runs is picked up by
    the run with the later cutoff; the same cutoff would skip the game."""
    game_id = await _fact_game(session_factory, make_game, line_stamp=_BEFORE_CUTOFF)
    await _run(session_factory, tmp_path, mode="line", cutoff=_CUTOFF)
    first = (await _facepalm_values(session_factory, game_id))[2]
    assert first["material_missed"] == pytest.approx(
        _expected_new_facts(_BEST_LINE_AT_PLY_2)["material_missed"], rel=_REAL_REL_TOL
    )
    # A repair rewrote the best line at the flaw ply.
    await _set_line(session_factory, game_id, 2, _OTHER_BEST_LINE_AT_PLY_2)
    new_facts = _expected_new_facts(_OTHER_BEST_LINE_AT_PLY_2)
    assert new_facts["best_line_mate_ply"] != first["best_line_mate_ply"], (
        "the second best line mates, the first does not"
    )

    same_cutoff = await _run(session_factory, tmp_path, mode="line", cutoff=_CUTOFF)
    assert same_cutoff.games_selected == 0
    later = datetime.now(timezone.utc) + timedelta(minutes=1)
    rerun = await _run(session_factory, tmp_path, mode="line", cutoff=later)

    assert rerun.games_stamped == 1
    row = (await _facepalm_values(session_factory, game_id))[2]
    assert {c: row[c] for c in _NEW_FACT_COLUMNS} == pytest.approx(new_facts, rel=_REAL_REL_TOL)


@pytest.mark.asyncio
async def test_spread_mode_writes_the_facts_but_leaves_the_pre_keys_untouched(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """D-08 / D-09: the spread pass writes the reply spread, the two scalars and both mate plies,
    but never maia_best_prob, maia_pre_spread or the pre stamp."""
    game_id = await make_game(
        base_stamped=True, seed_base=True, pv={2: _BEST_LINE_AT_PLY_2, 3: _LINE_AFTER_PLY_2}
    )
    await _set_flaw(session_factory, game_id, 2, **_SEEDED_PRE)
    played_prob_before = (await _maia_values(session_factory, game_id))["maia_played_prob"]

    report = await _run(session_factory, tmp_path, mode="spread")

    assert report.games_stamped == 1
    row = (await _facepalm_values(session_factory, game_id))[2]
    assert row["maia_reply_spread"] is not None
    assert {c: row[c] for c in _NEW_FACT_COLUMNS} == pytest.approx(
        _expected_new_facts(_BEST_LINE_AT_PLY_2), rel=_REAL_REL_TOL
    )
    maia_after = await _maia_values(session_factory, game_id)
    assert maia_after["maia_best_prob"] == _SEEDED_PRE["maia_best_prob"]
    assert maia_after["maia_pre_spread"] == _SEEDED_PRE["maia_pre_spread"]
    assert maia_after["maia_played_prob"] == played_prob_before
    assert await _pre_stamp(session_factory, game_id) is None


# ---------------------------------------------------------------------------
# Opponent mode (SEED-261114-iuv Part A): row-selected, three columns, no stamp
# ---------------------------------------------------------------------------

_OPPONENT_PLY = 5
_OPPONENT_BEST_MOVE = "g8f6"
_OPPONENT_COLUMNS: tuple[str, ...] = maia_flaw_scoring.OPPONENT_ROW_COLUMNS
_FOUR_STAMPS: tuple[str, ...] = (
    "maia_flaws_completed_at",
    "facepalm_spread_completed_at",
    "facepalm_line_completed_at",
    "facepalm_pre_completed_at",
)


async def _columns_except_opponent(
    maker: async_sessionmaker[AsyncSession], game_id: int
) -> dict[int, dict[str, Any]]:
    """Every game_flaws column but the three opponent-mode keys, per ply."""
    columns = [c for c in GameFlaw.__table__.columns if c.name not in _OPPONENT_COLUMNS]
    async with maker() as session:
        rows = (
            await session.execute(select(*columns).where(GameFlaw.game_id == game_id))
        ).mappings()
        return {row["ply"]: dict(row) for row in rows}


async def _all_stamps(maker: async_sessionmaker[AsyncSession], game_id: int) -> tuple[Any, ...]:
    async with maker() as session:
        row = (
            await session.execute(
                select(*[getattr(Game, c) for c in _FOUR_STAMPS]).where(Game.id == game_id)
            )
        ).one()
    return tuple(row)


async def _opponent_values(
    maker: async_sessionmaker[AsyncSession], game_id: int
) -> dict[int, dict[str, Any]]:
    async with maker() as session:
        flaws = (
            (await session.execute(select(GameFlaw).where(GameFlaw.game_id == game_id)))
            .scalars()
            .all()
        )
    return {f.ply: {c: getattr(f, c) for c in _OPPONENT_COLUMNS} for f in flaws}


async def _opponent_game(
    maker: async_sessionmaker[AsyncSession], make_game: MakeGame, **kwargs: Any
) -> int:
    """A base-stamped game (white user, flaws 2, 5, 8) with stored played probs, the best move g8f6
    at ply 5 and already written facepalm values on the user's ply-2 blunder."""
    game_id = await make_game(
        base_stamped=True, seed_base=True, pv={_OPPONENT_PLY: _OPPONENT_BEST_MOVE}, **kwargs
    )
    await _set_flaw(maker, game_id, 2, **_SEEDED_FACEPALM)
    return game_id


def _pinned(raw: int) -> float:
    return pinned_elo_for_mover(
        raw_rating=raw, platform="lichess", time_control_bucket="blitz", is_correspondence=False
    )


@pytest.mark.asyncio
async def test_opponent_mode_writes_only_the_three_columns_and_no_stamp(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game_id = await _opponent_game(session_factory, make_game)
    columns_before = await _columns_except_opponent(session_factory, game_id)
    stamps_before = await _all_stamps(session_factory, game_id)
    calls: list[tuple[str, float]] = []

    def _spy(fen: str, elo: float) -> dict[str, float]:
        calls.append((fen, elo))
        return fake_full_policy(fen, elo)

    monkeypatch.setattr(maia_flaw_scoring, "full_policy", _spy)

    report = await _run(session_factory, tmp_path, mode="opponent")

    assert report.mode == "opponent"
    assert report.games_selected == 1
    # Exactly one pre-blunder plus one post-blunder inference, at the opponent's (black's) Elo.
    pre, played = _boards_by_ply(_PGN)[_OPPONENT_PLY]
    post = pre.copy()
    post.push_uci(played)
    black = _pinned(1600)
    assert calls == [(pre.fen(), black), (post.fen(), black)]
    values = await _opponent_values(session_factory, game_id)
    pre_policy = fake_full_policy(pre.fen(), 0.0)
    assert values[_OPPONENT_PLY]["maia_reply_spread"] == pytest.approx(
        reply_spread(fake_full_policy(post.fen(), 0.0)), rel=1e-6
    )
    assert values[_OPPONENT_PLY]["maia_best_prob"] == pytest.approx(
        pre_policy[_OPPONENT_BEST_MOVE], rel=1e-6
    )
    assert values[_OPPONENT_PLY]["maia_pre_spread"] == pytest.approx(
        pre_blunder_spread(pre_policy), rel=1e-6
    )
    # Every other column of every row (maia_played_prob 0.11 included) and all four stamps stay.
    assert await _columns_except_opponent(session_factory, game_id) == columns_before
    played_prob = (await _flaw_values(session_factory, game_id))[_OPPONENT_PLY]["maia_played_prob"]
    assert played_prob == pytest.approx(_SEEDED_BASE["maia_played_prob"], rel=1e-6)
    assert await _all_stamps(session_factory, game_id) == stamps_before
    saved = json.loads((tmp_path / f"dev-opponent-{_RUN_STAMP}-shard0.json").read_text())
    assert saved["opponent_spreads_scored"] == 1
    assert saved["opponent_pre_scored"] == 1
    assert saved["opponent_spreads_null"] == 0
    assert saved["opponent_pre_null"] == 0
    assert saved["spreads_scored"] == 0
    assert saved["pre_scored"] == 0


@pytest.mark.asyncio
async def test_opponent_mode_rerun_selects_nothing(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    game_id = await _opponent_game(session_factory, make_game)
    first = await _run(session_factory, tmp_path, mode="opponent")
    before = await _opponent_values(session_factory, game_id)

    second = await _run(session_factory, tmp_path, mode="opponent")

    assert first.games_selected == 1
    assert second.games_selected == 0
    assert await _opponent_values(session_factory, game_id) == before


@pytest.mark.asyncio
async def test_opponent_mode_dry_run_writes_nothing(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    game_id = await _opponent_game(session_factory, make_game)
    before = await _opponent_values(session_factory, game_id)

    report = await _run(session_factory, tmp_path, mode="opponent", dry_run=True)

    assert report.games_scored == 1
    assert report.opponent_spreads_scored == 1
    assert report.games_stamped == 0
    assert await _opponent_values(session_factory, game_id) == before


@pytest.mark.asyncio
async def test_opponent_mode_residue_is_counted_and_selected_again(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """A row whose board cannot be rebuilt keeps a NULL spread: counted as fen_mismatch, the run
    returns normally (no re-query loop) and the next run selects the game again."""
    game_id = await _opponent_game(
        session_factory, make_game, fen_override={_OPPONENT_PLY: "8/8/8/8/8/8/8/8"}
    )

    first = await _run(session_factory, tmp_path, mode="opponent")
    second = await _run(session_factory, tmp_path, mode="opponent")

    assert first.games_selected == 1
    assert first.reasons.get("fen_mismatch") == 1
    assert first.opponent_spreads_null == 1
    assert (await _opponent_values(session_factory, game_id))[_OPPONENT_PLY][
        "maia_reply_spread"
    ] is None
    assert second.games_selected == 1


@pytest.mark.asyncio
async def test_opponent_mode_selector_selects_by_row(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    white_user = await _opponent_game(session_factory, make_game)
    # Black user: plies 2 and 8 are White's moves, i.e. the opponent's blunders.
    black_user = await make_game(base_stamped=True, seed_base=True, user_color="black")
    no_played_prob = await make_game(base_stamped=True)
    spread_set = await _opponent_game(session_factory, make_game)
    await _set_flaw(session_factory, spread_set, _OPPONENT_PLY, maia_reply_spread=3.5)
    # Ply 5 is a mistake here; the user's blunders at plies 2 and 8 carry a played prob and a NULL
    # spread, which proves the parity and severity filters.
    opponent_mistake = await make_game(base_stamped=True, seed_base=True, severities={5: 1})

    selected = set(await _select(session_factory, "opponent"))

    assert selected == {white_user, black_user}
    assert not selected & {no_played_prob, spread_set, opponent_mistake}


@pytest.mark.asyncio
async def test_opponent_mode_needs_no_base_stamp(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """Selection is by row alone: an unstamped game with the stored values qualifies."""
    game_id = await make_game(base_stamped=False, seed_base=True)
    assert game_id in set(await _select(session_factory, "opponent"))


@pytest.mark.asyncio
async def test_opponent_mode_shards_are_disjoint_and_exhaustive(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    game_ids = {await make_game(seed_base=True) for _ in range(_SHARD_GAMES)}
    per_shard = [
        await _select(session_factory, "opponent", shard=shard, num_shards=_SHARD_COUNT)
        for shard in range(_SHARD_COUNT)
    ]
    flat = [gid for ids in per_shard for gid in ids]
    assert len(flat) == len(set(flat)), "a game landed in two shards"
    assert set(flat) == game_ids


def test_opponent_pending_clause_compiled_from_is_opponent_expr() -> None:
    assert backfill._OPPONENT_IS_MOVER_SQL == (
        "CASE WHEN (ob.ply % 2 = 0) THEN g.user_color = 'black' ELSE g.user_color = 'white' END"
    )
    assert backfill._STAMP_CLAUSE_BY_MODE["opponent"] == backfill._OPPONENT_PENDING_CLAUSE


def test_opponent_mode_needs_maia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No Maia session: the opponent mode exits EXIT_MAIA_UNAVAILABLE and never opens a DB session."""

    async def _noop_start(**_: Any) -> None:
        return None

    async def _must_not_run(**_: Any) -> None:
        raise AssertionError("run_shard must not run without Maia")

    monkeypatch.setattr(maia_engine, "start_maia", _noop_start)
    monkeypatch.setattr(maia_engine, "_session", None)
    monkeypatch.setattr(backfill, "run_shard", _must_not_run)
    monkeypatch.setattr(backfill.settings, "SENTRY_DSN", "")
    old_int = signal.getsignal(signal.SIGINT)
    old_term = signal.getsignal(signal.SIGTERM)
    try:
        code = backfill._shard_process_entry(
            db="dev",
            shard=0,
            num_shards=1,
            user_id=None,
            limit=None,
            batch_games=backfill.DEFAULT_BATCH_GAMES,
            dry_run=False,
            throttle_ms=0,
            report_dir=str(tmp_path),
            run_stamp=_RUN_STAMP,
            mode="opponent",
        )
    finally:
        signal.signal(signal.SIGINT, old_int)
        signal.signal(signal.SIGTERM, old_term)
    assert code == backfill.EXIT_MAIA_UNAVAILABLE


def test_cli_accepts_opponent_mode_and_rejects_cutoff_with_it() -> None:
    assert backfill._parse_args(["--db", "dev", "--mode", "opponent"]).mode == "opponent"
    assert "opponent" in backfill.BACKFILL_MODE_CHOICES
    with pytest.raises(SystemExit):
        backfill._parse_args(
            ["--db", "dev", "--mode", "opponent", "--cutoff", "2026-11-10T12:00:00+00:00"]
        )


@pytest.mark.asyncio
async def test_opponent_mode_status_counts(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    test_engine: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Two games with one opponent blunder each (ply 5); a limit-1 run fills one of them."""
    for _ in range(2):
        await _opponent_game(session_factory, make_game)
    await _run(session_factory, tmp_path, mode="opponent", limit=1)

    counts = await backfill.fetch_status(session_factory, _TEST_USER_ID, "opponent")

    expected = {
        "opponent_pending_games": 1,
        "opponent_blunders_total": 2,
        "opponent_blunders_with_played_prob": 2,
        "opponent_blunders_with_spread": 1,
        "opponent_blunders_with_pre_spread": 1,
        "opponent_blunders_with_best_prob": 1,
        "opponent_blunders_pending": 1,
    }
    assert counts == expected
    assert list(counts) == list(expected), "the key order is part of the printed contract"
    test_url = test_engine.url.render_as_string(hide_password=False)
    monkeypatch.setattr(backfill, "db_url_for_target", lambda _target: test_url)
    await backfill._print_status("dev", _TEST_USER_ID, "opponent")
    line = capsys.readouterr().out.strip().splitlines()[-1]
    assert line == " ".join(f"{k}={v}" for k, v in expected.items())


# ---------------------------------------------------------------------------
# Reply mode (259 D-07, D-10, D-11)
# ---------------------------------------------------------------------------

# Stand-ins for values the reply pass must never touch (every other facepalm column is written by
# other passes and has its own stored value on the seeded rows).
_SEEDED_BEFORE_REPLY: dict[str, Any] = {
    "maia_reply_spread": 3.5,
    "maia_best_prob": 0.2,
    "maia_pre_spread": 6.5,
    "material_loss": 2.0,
    "material_missed": 1.0,
}


async def _columns_except_reply(
    maker: async_sessionmaker[AsyncSession], game_id: int
) -> dict[int, dict[str, Any]]:
    """Every game_flaws column but the best-reply probability, per ply."""
    columns = [c for c in GameFlaw.__table__.columns if c.name not in FACEPALM_REPLY_COLUMNS]
    async with maker() as session:
        rows = (
            await session.execute(select(*columns).where(GameFlaw.game_id == game_id))
        ).mappings()
        return {row["ply"]: dict(row) for row in rows}


async def _reply_probs(
    maker: async_sessionmaker[AsyncSession], game_id: int
) -> dict[int, float | None]:
    async with maker() as session:
        flaws = (
            (await session.execute(select(GameFlaw).where(GameFlaw.game_id == game_id)))
            .scalars()
            .all()
        )
    return {f.ply: f.maia_best_reply_prob for f in flaws}


async def _stamps_but_reply(
    maker: async_sessionmaker[AsyncSession], game_id: int
) -> tuple[Any, ...]:
    async with maker() as session:
        row = (
            await session.execute(
                select(
                    Game.maia_flaws_completed_at,
                    Game.facepalm_spread_completed_at,
                    Game.facepalm_line_completed_at,
                    Game.facepalm_pre_completed_at,
                ).where(Game.id == game_id)
            )
        ).one()
    return tuple(row)


async def _reply_stamp(maker: async_sessionmaker[AsyncSession], game_id: int) -> Any:
    async with maker() as session:
        return (
            await session.execute(
                select(Game.facepalm_reply_completed_at).where(Game.id == game_id)
            )
        ).scalar_one()


def _post_blunder_fen(ply: int) -> str:
    """The position after the blunder at `ply` (independent python-chess replay)."""
    board, played = _boards_by_ply(_PGN)[ply]
    board.push(chess.Move.from_uci(played))
    return board.fen()


async def _reply_game(
    maker: async_sessionmaker[AsyncSession], make_game: MakeGame, **kwargs: Any
) -> int:
    """A base-stamped game with a stored played probability on every flaw (so both sides' blunders
    qualify), refutation lines for the plies 2 and 5 blunders (none for ply 8: it is the game's
    last ply) and values of the other passes seeded on every row."""
    game_id = await make_game(
        base_stamped=True,
        seed_base=True,
        pv={3: _LINE_AFTER_PLY_2, 6: _LINE_AFTER_PLY_5},
        **kwargs,
    )
    for ply in _FLAW_PLIES:
        await _set_flaw(maker, game_id, ply, **_SEEDED_BEFORE_REPLY)
    return game_id


@pytest.mark.asyncio
async def test_reply_mode_fills_both_sides_and_stamps(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tracer (D-07, D-10, D-11): one post-blunder inference per blunder of either side that has a
    refutation line fills maia_best_reply_prob and stamps the reply stamp; nothing else changes and
    a second run selects 0 games."""
    game_id = await _reply_game(session_factory, make_game)
    columns_before = await _columns_except_reply(session_factory, game_id)
    stamps_before = await _stamps_but_reply(session_factory, game_id)
    assert await _reply_stamp(session_factory, game_id) is None
    policy_calls: list[str] = []

    def _spy_policy(fen: str, elo: float) -> dict[str, float]:
        policy_calls.append(fen)
        return fake_full_policy(fen, elo)

    monkeypatch.setattr(maia_flaw_scoring, "full_policy", _spy_policy)

    report = await _run(session_factory, tmp_path, mode="reply")

    assert report.mode == "reply"
    assert report.games_stamped == 1
    # One post-blunder inference for the user blunder (ply 2) and the opponent blunder (ply 5);
    # the ply 8 blunder has no stored refutation line, so it spends none.
    assert policy_calls == [_post_blunder_fen(2), _post_blunder_fen(5)]
    probs = await _reply_probs(session_factory, game_id)
    first_reply_ply2 = _LINE_AFTER_PLY_2.split(" ")[0]
    first_reply_ply5 = _LINE_AFTER_PLY_5.split(" ")[0]
    assert probs[2] == pytest.approx(
        fake_full_policy(_post_blunder_fen(2), 1500.0)[first_reply_ply2], rel=1e-5
    )
    assert probs[5] == pytest.approx(
        fake_full_policy(_post_blunder_fen(5), 1600.0)[first_reply_ply5], rel=1e-5
    )
    assert probs[8] is None
    # Nothing but the reply key changed on rows, and no other stamp moved.
    assert await _columns_except_reply(session_factory, game_id) == columns_before
    assert await _stamps_but_reply(session_factory, game_id) == stamps_before
    stamp = await _reply_stamp(session_factory, game_id)
    assert stamp is not None
    saved = json.loads((tmp_path / f"dev-reply-{_RUN_STAMP}-shard0.json").read_text())
    assert saved["reply_probs_set"] == 2
    assert saved["reply_probs_null"] == 1
    assert saved["reasons"] == {"reply_missing": 1}

    second = await _run(session_factory, tmp_path, mode="reply")
    assert second.games_selected == 0
    assert second.games_stamped == 0
    assert await _reply_probs(session_factory, game_id) == probs
    assert await _reply_stamp(session_factory, game_id) == stamp


@pytest.mark.asyncio
async def test_reply_status_counts_and_residues(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    test_engine: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Reply status after one pass: stamp counts, both-sides blunder counts and the three residues
    the readiness gate reads, each from one seeded row."""
    game_id = await _reply_game(session_factory, make_game)
    await _run(session_factory, tmp_path, mode="reply")
    # After the pass plies 2 and 5 hold a reply probability and ply 8 (no refutation line) does not.
    # Ply 2: no material inputs yet. Ply 5: a pure miss (no loss) without a best-move probability.
    # Ply 8: a losing blunder still without a reply probability (the losing residue).
    await _set_flaw(session_factory, game_id, 2, material_loss=None, material_missed=None)
    await _set_flaw(
        session_factory, game_id, 5, material_loss=0.0, material_missed=0.0, maia_best_prob=None
    )

    counts = await backfill.fetch_status(session_factory, _TEST_USER_ID, "reply")

    expected = {
        "reply_stamped_games": 1,
        "reply_pending_games": 0,
        "blunders_total": 3,
        "blunders_with_reply_prob": 2,
        "reply_residue_losing": 1,
        "unscored_pure_miss_no_best": 1,
        "blunders_without_material_inputs": 1,
    }
    assert counts == expected
    assert list(counts) == list(expected), "the key order is part of the printed contract"
    test_url = test_engine.url.render_as_string(hide_password=False)
    monkeypatch.setattr(backfill, "db_url_for_target", lambda _target: test_url)
    await backfill._print_status("dev", _TEST_USER_ID, "reply")
    line = capsys.readouterr().out.strip().splitlines()[-1]
    assert line == " ".join(f"{k}={v}" for k, v in expected.items())
    # A reply-pending game is counted as pending until the pass stamps it.
    await _set_game(session_factory, game_id, facepalm_reply_completed_at=None)
    pending = await backfill.fetch_status(session_factory, _TEST_USER_ID, "reply")
    assert (pending["reply_stamped_games"], pending["reply_pending_games"]) == (0, 1)


@pytest.mark.asyncio
async def test_line_status_prints_material_input_counts(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    test_engine: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Line status also counts the blunders of each side whose material_loss is written (259 D-05)."""
    game_id = await _spread_stamped_game(session_factory, make_game, line_stamp=_BEFORE_CUTOFF)
    # One user blunder (ply 2) and one opponent blunder (ply 5) hold the scalar pair (CHECK: both set).
    await _set_flaw(session_factory, game_id, 2, material_loss=1.5, material_missed=0.5)
    await _set_flaw(session_factory, game_id, _OPPONENT_PLY, material_loss=2.5, material_missed=0.0)

    counts = await backfill.fetch_status(session_factory, _TEST_USER_ID, "line", _CUTOFF)

    assert counts["user_blunders_with_material_inputs"] == 1
    assert counts["opponent_blunders_with_material_inputs"] == 1
    test_url = test_engine.url.render_as_string(hide_password=False)
    monkeypatch.setattr(backfill, "db_url_for_target", lambda _target: test_url)
    await backfill._print_status("dev", _TEST_USER_ID, "line", _CUTOFF)
    line = capsys.readouterr().out.strip().splitlines()[-1]
    assert "user_blunders_with_material_inputs=1" in line
    assert "opponent_blunders_with_material_inputs=1" in line
