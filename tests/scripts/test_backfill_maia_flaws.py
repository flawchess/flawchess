"""Tests for scripts/backfill_maia_flaws.py (Phase 247 plan 05, D-06, D-10, D-11, D-16).

DB-backed: games are committed through a session maker bound to the per-run test DB (the
script opens its own short sessions) and removed in teardown, so the global tier-3 eval
lottery never sees a leaked non-guest game. The selector is global, so every test scopes
its run by ``user_id`` (other modules' games leak in under -n auto). Maia inference is
faked by patching ``maia_flaw_scoring.full_policy`` and presenting a session sentinel.
"""

from __future__ import annotations

import io
import json
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
    MAIA_FLAW_COLUMNS,
    MAIA_REFUTATION_COLUMNS,
)
from app.services import maia_engine, maia_flaw_scoring
from app.services.blunder_check_rules import FACEPALM_SCORE_MIN
from app.services.line_material import line_facts
from scripts import backfill_maia_flaws as backfill
from tests.services.maia_fakes import fake_full_policy

# Unique to this module (grep tests/ before changing).
_TEST_USER_ID: int = 247_001

_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *"
_FLAW_PLIES: tuple[int, ...] = (2, 5, 8)
# Legal stand-ins for Stockfish's best / second-best move at each flaw ply.
_BEST: dict[int, str] = {2: "d2d4", 5: "g8f6", 8: "d2d3"}
_SECOND: dict[int, str] = {2: "b1c3", 5: "d7d6", 8: "c2c3"}
_RUN_STAMP = "20261108T000000Z"
# Stockfish's best reply after the white flaw at ply 2 (black, ply 3) and after black's ply 5 (white, ply 6).
_REPLY_BEST: dict[int, str] = {3: "b8c6", 6: "b1c3"}
# Distinct, non-NULL stand-ins for already-written base values (refutation mode must not touch them).
_SEEDED_BASE: dict[str, float | int] = {
    "maia_played_prob": 0.11,
    "maia_played_rank": 3,
    "maia_best_prob": 0.22,
    "maia_best_rank": 1,
    "maia_second_prob": 0.05,
    "maia_second_rank": 2,
    "maia_top_prob": 0.33,
    "maia_effective_moves": 4.5,
}

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
        best: dict[int, str] | None = None,
        base_stamped: bool = False,
        seed_base: bool = False,
        pv: dict[int, str] | None = None,
    ) -> int:
        fens = _board_fens(_PGN)
        best_by_ply = {**_BEST, **(best or {})}
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
                        best_move=best_by_ply.get(ply),
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
                        missed_pv_lines=[{"su": _SECOND[ply]}] if ply in _SECOND else None,
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


async def _refutation_values(
    maker: async_sessionmaker[AsyncSession], game_id: int
) -> dict[int, dict[str, Any]]:
    async with maker() as session:
        flaws = (
            (await session.execute(select(GameFlaw).where(GameFlaw.game_id == game_id)))
            .scalars()
            .all()
        )
    return {f.ply: {c: getattr(f, c) for c in MAIA_REFUTATION_COLUMNS} for f in flaws}


async def _refutation_stamp(maker: async_sessionmaker[AsyncSession], game_id: int) -> Any:
    async with maker() as session:
        return (
            await session.execute(
                select(Game.maia_refutation_completed_at).where(Game.id == game_id)
            )
        ).scalar_one()


def _no_pair() -> dict[str, None]:
    return {c: None for c in MAIA_REFUTATION_COLUMNS}


@pytest.mark.asyncio
async def test_refutation_mode_scores_and_stamps_only_the_pair(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """Tracer (D-10): a base-stamped game gets exactly its user-blunder pair and the new stamp."""
    game_id = await make_game(
        flaw_plies=(2, 5), best=_REPLY_BEST, base_stamped=True, seed_base=True
    )
    base_stamp_before = await _stamp(session_factory, game_id)
    base_before = await _flaw_values(session_factory, game_id)
    assert all(v is not None for row in base_before.values() for v in row.values())

    report = await _run(session_factory, tmp_path, mode="refutation")

    assert report.games_stamped == 1
    pairs = await _refutation_values(session_factory, game_id)
    assert pairs[2]["maia_refutation_prob"] is not None
    assert pairs[2]["maia_refutation_rank"] is not None
    assert pairs[5] == _no_pair()
    assert await _flaw_values(session_factory, game_id) == base_before
    assert await _stamp(session_factory, game_id) == base_stamp_before
    assert await _refutation_stamp(session_factory, game_id) is not None
    saved = json.loads((tmp_path / f"dev-refutation-{_RUN_STAMP}-shard0.json").read_text())
    assert saved["mode"] == "refutation"
    assert saved["refutations_scored"] == 1
    assert saved["games_stamped"] == 1


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
# Refutation mode: selector, idempotence, race, no-blunder shortcut, full-mode default, status
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


async def _set_refutation_stamp(maker: async_sessionmaker[AsyncSession], game_id: int) -> None:
    async with maker() as session:
        await session.execute(
            update(Game).where(Game.id == game_id).values(maia_refutation_completed_at=func.now())
        )
        await session.commit()


@pytest.mark.asyncio
async def test_refutation_mode_selector_needs_base_stamp_and_no_refutation_stamp(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """D-10: refutation mode takes base-stamped, refutation-unstamped games; full mode is unchanged."""
    eligible = await make_game(base_stamped=True)
    base_unstamped = await make_game()
    refutation_done = await make_game(base_stamped=True)
    await _set_refutation_stamp(session_factory, refutation_done)

    assert await _select(session_factory, "refutation") == [eligible]
    assert await _select(session_factory, "full") == [base_unstamped]


@pytest.mark.asyncio
async def test_refutation_mode_rerun_selects_nothing_and_changes_nothing(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    """The refutation stamp is the checkpoint; a second run over the same scope is a no-op."""
    game_ids = [await make_game(best=_REPLY_BEST, base_stamped=True) for _ in range(3)]
    first = await _run(session_factory, tmp_path, mode="refutation")
    before = {gid: await _refutation_values(session_factory, gid) for gid in game_ids}
    stamps = {gid: await _refutation_stamp(session_factory, gid) for gid in game_ids}

    second = await _run(session_factory, tmp_path, mode="refutation")

    assert first.games_stamped == 3
    assert second.games_selected == 0
    assert second.games_stamped == 0
    assert {gid: await _refutation_values(session_factory, gid) for gid in game_ids} == before
    assert {gid: await _refutation_stamp(session_factory, gid) for gid in game_ids} == stamps


@pytest.mark.asyncio
async def test_refutation_mode_shard_partition_disjoint_exhaustive(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    game_ids = {await make_game(base_stamped=True) for _ in range(_SHARD_GAMES)}
    per_shard = [
        await _select(session_factory, "refutation", shard=shard, num_shards=_SHARD_COUNT)
        for shard in range(_SHARD_COUNT)
    ]
    flat = [gid for ids in per_shard for gid in ids]
    assert len(flat) == len(set(flat)), "a game landed in two shards"
    assert set(flat) == game_ids


@pytest.mark.asyncio
async def test_refutation_mode_skips_game_refutation_stamped_mid_run(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """require_unstamped checks the mode's own stamp: a game another lane stamped is not overwritten."""
    raced = await make_game(best=_REPLY_BEST, base_stamped=True)
    other = await make_game(best=_REPLY_BEST, base_stamped=True)
    real_write = backfill.write_game_maia_scores

    async def _stamp_then_write(session: AsyncSession, scores: Any, **kwargs: Any) -> Any:
        await _set_refutation_stamp(session_factory, raced)
        return await real_write(session, scores, **kwargs)

    monkeypatch.setattr(backfill, "write_game_maia_scores", _stamp_then_write)

    report = await _run(session_factory, tmp_path, mode="refutation")

    assert report.games_already_stamped == 1
    assert report.games_stamped == 1
    assert all(v == _no_pair() for v in (await _refutation_values(session_factory, raced)).values())
    assert (await _refutation_values(session_factory, other))[2]["maia_refutation_prob"] is not None


@pytest.mark.asyncio
async def test_refutation_mode_game_without_user_blunder_stamped_without_replay_or_inference(
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

    report = await _run(session_factory, tmp_path, mode="refutation")

    assert report.games_stamped == 1
    assert policy_calls == []
    assert replay_calls == []
    assert await _refutation_stamp(session_factory, game_id) is not None
    assert all(
        v == _no_pair() for v in (await _refutation_values(session_factory, game_id)).values()
    )
    assert (await _select(session_factory, "refutation")) == []


@pytest.mark.asyncio
async def test_refutation_mode_replays_only_blunder_plies(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-05: the PGN replay is asked for the user-blunder plies only."""
    await make_game(best=_REPLY_BEST, base_stamped=True)
    wanted: list[set[int]] = []
    real_replay = maia_flaw_scoring.replay_flaw_boards

    def _spy_replay(pgn_text: str, plies: Any) -> Any:
        wanted.append(set(plies))
        return real_replay(pgn_text, plies)

    monkeypatch.setattr(maia_flaw_scoring, "replay_flaw_boards", _spy_replay)

    await _run(session_factory, tmp_path, mode="refutation")

    assert wanted == [{2, 8}]


@pytest.mark.asyncio
async def test_full_mode_default_writes_pair_and_both_stamps(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, tmp_path: Path
) -> None:
    game_id = await make_game(best=_REPLY_BEST)

    report = await _run(session_factory, tmp_path)

    assert report.mode == "full"
    assert report.games_stamped == 1
    assert report.refutations_scored == 1
    assert await _stamp(session_factory, game_id) is not None
    assert await _refutation_stamp(session_factory, game_id) is not None
    pairs = await _refutation_values(session_factory, game_id)
    assert pairs[2]["maia_refutation_prob"] is not None
    assert pairs[5] == _no_pair()
    base = await _flaw_values(session_factory, game_id)
    assert all(v["maia_played_prob"] is not None for v in base.values())


def test_cli_mode_choices() -> None:
    assert backfill._parse_args(["--db", "dev"]).mode == "full"
    assert backfill._parse_args(["--db", "dev", "--mode", "refutation"]).mode == "refutation"
    assert backfill._parse_args(["--db", "dev", "--mode", "spread"]).mode == "spread"
    with pytest.raises(SystemExit):
        backfill._parse_args(["--db", "dev", "--mode", "everything"])


@pytest.mark.asyncio
async def test_refutation_status_counts(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    test_engine: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exact refutation counts; the black-user game proves the user side comes from is_opponent_expr."""
    await make_game(best=_REPLY_BEST, base_stamped=True)
    await make_game(best=_REPLY_BEST, base_stamped=True)
    # Black user: of plies 2/5/8 only the black mover at ply 5 is a user blunder.
    await make_game(user_color="black")
    await _run(session_factory, tmp_path, limit=1, mode="refutation")

    counts = await backfill.fetch_status(session_factory, _TEST_USER_ID, "refutation")

    assert counts == {
        "refutation_stamped_games": 1,
        "refutation_unstamped_games_with_flaws": 1,
        "user_blunders_with_refutation": 1,
        "user_blunders_total": 5,
    }
    # The 247 status line is untouched without --mode.
    assert set(await backfill.fetch_status(session_factory, _TEST_USER_ID)) == {
        "stamped_games",
        "unstamped_games_with_flaws",
        "flaws_with_maia",
        "flaws_total",
    }
    test_url = test_engine.url.render_as_string(hide_password=False)
    monkeypatch.setattr(backfill, "db_url_for_target", lambda _target: test_url)
    await backfill._print_status("dev", _TEST_USER_ID, "refutation")
    line = capsys.readouterr().out.strip().splitlines()[-1]
    assert line == (
        "refutation_stamped_games=1 refutation_unstamped_games_with_flaws=1 "
        "user_blunders_with_refutation=1 user_blunders_total=5"
    )


# ---------------------------------------------------------------------------
# Spread mode (Phase 250 D-08)
# ---------------------------------------------------------------------------

_USER_BLUNDER_PLIES: tuple[int, ...] = (2, 8)
# facepalm_score is a REAL column: a value equal to the bar round-trips just below it, so the
# status test sets a clearly qualifying score instead.
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
    both facepalm stamps; the base values and the refutation pair stay untouched; a rerun is a no-op."""
    game_id = await make_game(
        best=_REPLY_BEST,
        base_stamped=True,
        seed_base=True,
        pv={3: _LINE_AFTER_PLY_2},
    )
    base_before = await _flaw_values(session_factory, game_id)
    base_stamp_before = await _stamp(session_factory, game_id)
    pairs_before = await _refutation_values(session_factory, game_id)

    report = await _run(session_factory, tmp_path, mode="spread")

    assert report.games_stamped == 1
    values = await _facepalm_values(session_factory, game_id)
    pre = _boards_by_ply(_PGN)[2]
    expected = line_facts(pre[0], pre[1], _LINE_AFTER_PLY_2).as_columns()
    assert any(v is not None for v in expected.values()), "the fixture line must settle a depth"
    # Ply 2 (user blunder with a stored line): spread, line facts and score.
    assert values[2]["maia_reply_spread"] is not None
    assert {c: values[2][c] for c in expected} == expected
    assert values[2]["facepalm_score"] is not None
    # Ply 8 (user blunder, no stored line after the last ply): spread only.
    assert values[8]["maia_reply_spread"] is not None
    assert values[8]["facepalm_score"] is None
    assert all(values[8][c] is None for c in expected)
    # Ply 5 is the opponent's blunder: out of scope (D-06).
    assert all(v is None for v in values[5].values())
    # Base values, the pair and the base stamp are not this pass's business.
    assert await _flaw_values(session_factory, game_id) == base_before
    assert await _refutation_values(session_factory, game_id) == pairs_before
    assert await _stamp(session_factory, game_id) == base_stamp_before
    assert await _refutation_stamp(session_factory, game_id) is None
    spread_stamp, line_stamp = await _facepalm_stamps(session_factory, game_id)
    assert spread_stamp is not None
    assert line_stamp is not None
    saved = json.loads((tmp_path / f"dev-spread-{_RUN_STAMP}-shard0.json").read_text())
    assert saved["mode"] == "spread"
    assert saved["spreads_scored"] == len(_USER_BLUNDER_PLIES)
    assert saved["spreads_null"] == 0
    assert saved["scores_set"] == 1
    assert saved["scores_null"] == 1
    assert saved["refutations_scored"] == 0

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
async def test_spread_status_counts(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    tmp_path: Path,
    test_engine: Any,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exact spread counts after one of two games was scored: 2 user blunders each, one scored."""
    await make_game(best=_REPLY_BEST, base_stamped=True, seed_base=True, pv={3: _LINE_AFTER_PLY_2})
    await make_game(best=_REPLY_BEST, base_stamped=True, seed_base=True, pv={3: _LINE_AFTER_PLY_2})
    await _run(session_factory, tmp_path, limit=1, mode="spread")
    # Make the scored game's ply-2 score exceed the bar so the qualifying count is exercised.
    async with session_factory() as session:
        await session.execute(
            update(GameFlaw)
            .where(GameFlaw.user_id == _TEST_USER_ID, GameFlaw.facepalm_score.is_not(None))
            .values(facepalm_score=FACEPALM_SCORE_MIN + _ABOVE_THE_BAR)
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
# The ply-2 line cut to four plies: still legal (a prefix of the game's continuation), but it
# settles fewer depths than the full line.
_SHORT_LINE_AFTER_PLY_2 = " ".join(_LINE_AFTER_PLY_2.split(" ")[:4])


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
    game_id = await make_game(
        best=_REPLY_BEST, base_stamped=True, seed_base=True, pv={3: pv} if pv else None
    )
    await _set_game(
        maker,
        game_id,
        facepalm_spread_completed_at=func.now(),
        facepalm_line_completed_at=line_stamp,
    )
    await _set_flaw(maker, game_id, 2, maia_reply_spread=_STORED_SPREAD)
    return game_id


def _expected_line_columns(line: str) -> dict[str, int | None]:
    pre, played = _boards_by_ply(_PGN)[2]
    return line_facts(pre, played, line).as_columns()


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
    await _set_flaw(session_factory, game_id, 2, **old_facts, facepalm_score=0.5)
    # A repair shortened the stored line after the last pass.
    await _set_line(session_factory, game_id, 3, _SHORT_LINE_AFTER_PLY_2)
    new_facts = _expected_line_columns(_SHORT_LINE_AFTER_PLY_2)
    assert new_facts != old_facts, "the fixture lines must settle different depths"
    base_before = await _flaw_values(session_factory, game_id)

    report = await _run(session_factory, tmp_path, mode="line", cutoff=_CUTOFF)

    assert report.games_stamped == 1
    assert report.cutoff == _CUTOFF.isoformat()
    row = (await _facepalm_values(session_factory, game_id))[2]
    assert {c: row[c] for c in new_facts} == new_facts
    assert row["maia_reply_spread"] == _STORED_SPREAD
    assert row["facepalm_score"] != 0.5
    assert await _flaw_values(session_factory, game_id) == base_before
    _, line_stamp = await _facepalm_stamps(session_factory, game_id)
    assert line_stamp >= _CUTOFF
    saved = json.loads((tmp_path / f"dev-line-{_RUN_STAMP}-shard0.json").read_text())
    assert saved["cutoff"] == _CUTOFF.isoformat()
    assert saved["mode"] == "line"
    assert saved["spreads_scored"] == 0
    assert saved["scores_set"] + saved["scores_null"] == 2


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
    assert {c: row[c] for c in expected} == expected
    assert row["facepalm_score"] is not None


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
    for mode in ("full", "refutation", "spread"):
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
        await _spread_stamped_game(session_factory, make_game, line_stamp=_BEFORE_CUTOFF)
    await _run(session_factory, tmp_path, mode="line", cutoff=_CUTOFF, limit=1)

    counts = await backfill.fetch_status(session_factory, _TEST_USER_ID, "line", _CUTOFF)

    assert counts["line_done_since_cutoff"] == 1
    assert counts["line_pending_games"] == 1
    assert counts["user_blunders_total"] == 4
    assert counts["user_blunders_with_score"] == 1
    assert list(counts)[:2] == ["line_done_since_cutoff", "line_pending_games"]
    test_url = test_engine.url.render_as_string(hide_password=False)
    monkeypatch.setattr(backfill, "db_url_for_target", lambda _target: test_url)
    await backfill._print_status("dev", _TEST_USER_ID, "line", _CUTOFF)
    line = capsys.readouterr().out.strip().splitlines()[-1]
    assert line.startswith("line_done_since_cutoff=1 line_pending_games=1 ")
