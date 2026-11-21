"""Tests for app/services/maia_flaw_scoring.py (Phase 247 plan 02, D-01 .. D-13).

DB-backed: games are committed through a session maker bound to the per-run test DB
(the scorer opens its own short sessions), and every game is deleted in teardown so the
global tier-3 eval lottery never sees a leaked non-guest game. Maia inference is faked
by patching ``maia_flaw_scoring.full_policy`` with ``fake_full_policy`` and presenting a
Maia session via ``maia_engine._session = object()``.
"""

from __future__ import annotations

import dataclasses
import io
import uuid
from collections import Counter
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import chess
import chess.pgn
import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy import delete, select
from sqlalchemy.dialects import postgresql
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
    clear_maia_flaws_completed,
)
from app.services.eval_apply import _classify_and_fill_oracle
from app.services import maia_engine, maia_flaw_scoring
from app.services.best_move_candidates import pinned_elo_for_mover
from app.repositories.library_repository import fetch_page_facepalm_scores
from app.services.blunder_check_rules import FACEPALM_DRILL_LAMBDA, FACEPALM_LIBRARY_LAMBDA
from app.services.facepalm_inputs import facepalm_material_inputs
from app.services.facepalm_score import (
    FacepalmFacts,
    facepalm_expr,
    facepalm_score,
    facepalm_type_expr,
)
from app.services.line_material import LineFacts, best_line_facts, line_facts
from app.services.maia_flaw_scoring import (
    best_move_uci,
    ScoringMode,
    format_maia_backfill_reminder,
    load_game_maia_inputs,
    replay_flaw_boards,
    score_game,
    score_game_flaws_after_apply,
    write_game_maia_scores,
)
from app.services.maia_flaw_stats import pre_blunder_spread, reply_spread
from tests.services.maia_fakes import fake_full_policy

# Unique to this module (grep tests/ before changing).
_TEST_USER_ID: int = 247_002

_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O *"
# PGN with a legal en-passant capture at ply 4 (exd6), castling rights intact.
_EP_PGN = "1. e4 a6 2. e5 d5 3. exd6 *"
# The last move (ply 18, Qe6) stalemates Black: the blunder leaves no legal reply.
_STALEMATE_PGN = (
    "1. e3 a5 2. Qh5 Ra6 3. Qxa5 h5 4. h4 Rah6 5. Qxc7 f6 6. Qxd7+ Kf7 7. Qxb7 Qd3 "
    "8. Qxb8 Qh7 9. Qxc8 Kg6 10. Qe6 1/2-1/2"
)
_STALEMATE_PLY = 18

# Last ply index of _PGN (nine plies, 0..8).
_PGN_LAST_PLY = 8

_WHITE_RATING = 1500
_BLACK_RATING = 1600

# Default flaw plies: white Nf3, black a6, white O-O (castling rights intact before it).
_FLAW_PLIES: tuple[int, ...] = (2, 5, 8)

_STALE_PROB = 0.999
_REAL_TOLERANCE = 1e-6
# float32 column holding a value up to a few dozen (the reply spread): compare relatively.
_REAL_RELATIVE_TOLERANCE = 1e-6

_BACKFILL_CMD_FRAGMENT = "scripts/backfill_maia_flaws.py --db prod"

MakeGame = Callable[..., Awaitable[int]]


def _replayed(pgn: str) -> dict[int, tuple[chess.Board, str]]:
    """Independent pre-push board + played UCI per ply (python-chess, not the module)."""
    parsed = chess.pgn.read_game(io.StringIO(pgn))
    assert parsed is not None
    board = parsed.board()
    out: dict[int, tuple[chess.Board, str]] = {}
    for ply, node in enumerate(parsed.mainline()):
        out[ply] = (board.copy(), node.move.uci())
        board.push(node.move)
    return out


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
                    email=f"maia-flaw-scoring-{_TEST_USER_ID}@example.com",
                    hashed_password="x",
                )
            )
            await session.commit()

    async def _make(
        *,
        pgn: str = _PGN,
        flaw_plies: tuple[int, ...] = _FLAW_PLIES,
        white_rating: int | None = _WHITE_RATING,
        black_rating: int | None = _BLACK_RATING,
        fen_override: dict[int, str] | None = None,
        stale_plies: tuple[int, ...] = (),
        evals: dict[int, int | None] | None = None,
        user_color: str = "white",
        severities: dict[int, int] | None = None,
        pv: dict[int, str] | None = None,
        best_moves: dict[int, str] | None = None,
    ) -> int:
        replayed = _replayed(pgn)
        async with session_factory() as session:
            game = Game(
                user_id=_TEST_USER_ID,
                platform="lichess",
                platform_game_id=f"maia-flaw-{uuid.uuid4().hex}",
                pgn=pgn,
                result="1-0",
                user_color=user_color,
                white_rating=white_rating,
                black_rating=black_rating,
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
                        eval_cp=(evals or {}).get(ply, 20),
                        eval_mate=None,
                        clock_seconds=None,
                        phase=1,
                        full_hash=ply,
                        white_hash=ply,
                        black_hash=ply,
                        endgame_class=None,
                        move_san=None,
                        pv=(pv or {}).get(ply),
                        best_move=(best_moves or {}).get(ply),
                    )
                )
            await session.flush()
            for ply in flaw_plies:
                kwargs: dict[str, Any] = {}
                if ply in stale_plies:
                    kwargs["maia_played_prob"] = _STALE_PROB
                fen = (fen_override or {}).get(ply)
                if fen is None:
                    fen = replayed[ply][0].board_fen()
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
                        fen=fen,
                        **kwargs,
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


async def _flaw_rows(
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
        ).scalar_one_or_none()


# The five game stamps of a full-mode pass (Phase 250 D-05, D-11; Phase 254 D-08 adds the pre stamp,
# Phase 259 D-11 the reply stamp).
_STAMP_COLUMNS: tuple[str, ...] = (
    "maia_flaws_completed_at",
    "facepalm_spread_completed_at",
    "facepalm_line_completed_at",
    "facepalm_pre_completed_at",
    "facepalm_reply_completed_at",
)


async def _facepalm_rows(
    maker: async_sessionmaker[AsyncSession], game_id: int
) -> dict[int, dict[str, Any]]:
    async with maker() as session:
        flaws = (
            (await session.execute(select(GameFlaw).where(GameFlaw.game_id == game_id)))
            .scalars()
            .all()
        )
    return {f.ply: {c: getattr(f, c) for c in FACEPALM_COLUMNS} for f in flaws}


def _fact_columns(facts: LineFacts) -> dict[str, Any]:
    """The stored fact columns of a played line (254 D-09): the signed array (None when every slot
    is unsettled, the stored shape) and the played line's mate ply."""
    material = facts.material_array()
    return {
        "played_line_material": None if all(v is None for v in material) else material,
        "line_mate_ply": facts.mate_ply,
    }


async def _stamps(maker: async_sessionmaker[AsyncSession], game_id: int) -> dict[str, Any]:
    async with maker() as session:
        row = (
            await session.execute(
                select(*[getattr(Game, c) for c in _STAMP_COLUMNS]).where(Game.id == game_id)
            )
        ).one()
    return dict(zip(_STAMP_COLUMNS, row, strict=True))


def _mainline_line(pgn: str, after_ply: int, count: int) -> str:
    """The next `count` mainline moves (UCI) after the move at `after_ply`.

    A legal stored line by construction: it is the game's own continuation.
    """
    replayed = _replayed(pgn)
    return " ".join(replayed[p][1] for p in range(after_ply + 1, after_ply + 1 + count))


async def _inputs(maker: async_sessionmaker[AsyncSession], game_id: int) -> Any:
    async with maker() as session:
        return (await load_game_maia_inputs(session, [game_id]))[game_id]


def _all_null(row: dict[str, Any]) -> bool:
    return all(row[c] is None for c in MAIA_FLAW_COLUMNS)


def _expected_played_prob(replayed: dict[int, tuple[chess.Board, str]], ply: int) -> float:
    board, played = replayed[ply]
    return fake_full_policy(board.fen(), 0.0)[played]


# ---------------------------------------------------------------------------
# Schema (D-01, D-02, D-07, 250 D-11)
# ---------------------------------------------------------------------------


async def test_schema_maia_columns_typed_nullable(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        rows = (
            await session.execute(
                sa.text(
                    "SELECT table_name, column_name, data_type, is_nullable, column_default "
                    "FROM information_schema.columns "
                    "WHERE table_name IN ('game_flaws', 'games') AND column_name LIKE 'maia\\_%'"
                )
            )
        ).all()
    by_name = {(r[0], r[1]): r for r in rows}
    expected_types = {
        "maia_played_prob": "real",
        # Phase 250 D-05 reply spread (also matches the maia_ prefix of this schema scan).
        "maia_reply_spread": "real",
        # Phase 254 D-09 facts (the best move's probability and the pre-blunder reply spread).
        "maia_best_prob": "real",
        "maia_pre_spread": "real",
        # Phase 259 D-07: Maia's probability of the first refutation token.
        "maia_best_reply_prob": "real",
    }
    flaw_cols = {name for (table, name) in by_name if table == "game_flaws"}
    assert flaw_cols == set(expected_types), (
        "the maia_ columns are the played probability, the reply spread (250 D-05), the 254 D-09 best probability and pre-blunder spread and the 259 D-07 best-reply probability"
    )
    for name, data_type in expected_types.items():
        row = by_name[("game_flaws", name)]
        assert row[2] == data_type
        assert row[3] == "YES"
        assert row[4] is None
    game_cols = sorted(c for (t, c) in by_name if t == "games")
    assert game_cols == ["maia_flaws_completed_at"]
    for stamp_name in game_cols:
        stamp = by_name[("games", stamp_name)]
        assert stamp[2] == "timestamp with time zone"
        assert stamp[3] == "YES"
        assert stamp[4] is None


# ---------------------------------------------------------------------------
# Hook scope and inference (Phase 247 / 250)
# ---------------------------------------------------------------------------

# Scotch with early captures so the stored line has material changes: white's ply-4 d4 is the
# flaw and the ten mainline moves after it (plies 5..14) are the stored line.
_SCOTCH_PGN = (
    "1. e4 e5 2. Nf3 Nc6 3. d4 exd4 4. Nxd4 Nxd4 5. Qxd4 Qf6 6. Qxf6 Nxf6 7. Nc3 Bb4 "
    "8. Bd2 O-O 9. O-O-O d6 *"
)
_SCOTCH_FLAW_PLY = 4
_STORED_LINE_PLIES = 10


async def test_facepalm_tracer_user_blunder_scored_and_three_stamps(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """One white user blunder end to end: played prob, spread, line facts and all stamps."""
    ply = _SCOTCH_FLAW_PLY
    pv = _mainline_line(_SCOTCH_PGN, ply, _STORED_LINE_PLIES)
    game_id = await make_game(
        pgn=_SCOTCH_PGN,
        flaw_plies=(ply,),
        pv={ply + 1: pv},
    )
    assert await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )
    pre, played = _replayed(_SCOTCH_PGN)[ply]
    post = pre.copy()
    post.push_uci(played)
    facts = line_facts(pre, played, pv)
    columns = _fact_columns(facts)
    assert any(v is not None for v in columns.values()), "the fixture line must settle a depth"

    row = (await _facepalm_rows(session_factory, game_id))[ply]
    stored_prob = (await _flaw_rows(session_factory, game_id))[ply]["maia_played_prob"]
    assert row["maia_reply_spread"] == pytest.approx(
        reply_spread(fake_full_policy(post.fen(), 0.0)), rel=_REAL_RELATIVE_TOLERANCE
    )
    for column, value in columns.items():
        assert row[column] == value, column
    assert stored_prob is not None
    assert all(stamp is not None for stamp in (await _stamps(session_factory, game_id)).values())


def _assert_no_dropped_keys(row: dict[str, Any]) -> None:
    """A scored row carries no stored-score key and no key of the legacy line-loss family
    (254 D-02, D-19)."""
    assert "facepalm_score" not in row
    assert not [key for key in row if key.startswith("line_loss")]


async def test_rows_carry_facts_only(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """D-02, D-19: full, spread, line and pre rows carry no stored-score key and no legacy
    line-loss key; full rows still carry both arrays, both mate plies and the pre inputs."""
    game_id, _ = await _best_line_user_blunder(make_game)
    inputs = await _inputs(session_factory, game_id)
    rows = {mode: score_game(inputs, None, mode).rows[0] for mode in _ALL_MODES}
    for row in rows.values():
        _assert_no_dropped_keys(row)
    full = rows["full"]
    for key in (*FACEPALM_COLUMNS, *FACEPALM_PRE_COLUMNS, "maia_played_prob"):
        assert key in full, key
    assert full["played_line_material"] is not None
    assert full["best_line_material"] is not None
    assert full["maia_best_prob"] is not None
    assert full["maia_pre_spread"] is not None


_ALL_MODES: tuple[ScoringMode, ...] = ("full", "spread", "line", "pre")


async def test_scores_set_counts_in_memory(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """D-01: scores_set equals the number of in-scope rows whose facts score non-None with the
    Python twin at FACEPALM_DRILL_LAMBDA; a row whose facts do not score is not counted."""
    game_id, _ = await _best_line_user_blunder(make_game)
    inputs = await _inputs(session_factory, game_id)
    scored = score_game(inputs, None)
    flaw, row = inputs.flaws[0], scored.rows[0]
    expected = facepalm_score(
        FacepalmFacts(
            played_prob=row["maia_played_prob"],
            reply_spread=row["maia_reply_spread"],
            played_material=row["played_line_material"],
            mate_ply=row["line_mate_ply"],
            best_material=row["best_line_material"],
            best_mate_ply=row["best_line_mate_ply"],
            best_prob=row["maia_best_prob"],
            pre_spread=row["maia_pre_spread"],
        ),
        lam=FACEPALM_DRILL_LAMBDA,
    )
    assert expected is not None
    assert scored.scores_set == 1
    assert maia_flaw_scoring._row_score(flaw, row) == pytest.approx(expected)
    # Pre mode carries no line facts: nothing to score, so the count is 0 there.
    assert score_game(inputs, None, "pre").scores_set == 0
    # Without a stored line the facts do not settle: the row scores None and is not counted.
    no_line_id, _ = await _scotch_user_blunder(make_game, with_line=False)
    no_line = score_game(await _inputs(session_factory, no_line_id), None)
    assert no_line.user_blunders == 1
    assert no_line.scores_set == 0


async def test_hook_full_mode_still_stamps(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """The post-commit hook still writes the facts and stamps all five stamps."""
    game_id, _ = await _best_line_user_blunder(make_game)
    assert await _score(session_factory, game_id)
    stamps = await _stamps(session_factory, game_id)
    assert len(stamps) == 5
    assert all(stamp is not None for stamp in stamps.values())
    row = await _flaw_row_full(session_factory, game_id, _SCOTCH_FLAW_PLY)
    assert row.played_line_material is not None


# Calls for _PGN, white user, flaws (2, 5, 8): three base calls plus a post-blunder call for each
# of the three blunders (plies 2 and 8 are the user's, ply 5 the opponent's: SEED-261114-iuv Part A).
_RECORDED_CALL_COUNT_WHITE_USER = 6


def _recording_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, float]]:
    """Patch full_policy with a fake that records every (fen, elo) call."""
    calls: list[tuple[str, float]] = []

    def _spy(fen: str, elo: float) -> dict[str, float]:
        calls.append((fen, elo))
        return fake_full_policy(fen, elo)

    monkeypatch.setattr(maia_flaw_scoring, "full_policy", _spy)
    return calls


def _pinned_elo(raw: int) -> float:
    return pinned_elo_for_mover(
        raw_rating=raw, platform="lichess", time_control_bucket="blitz", is_correspondence=False
    )


async def _score(
    maker: async_sessionmaker[AsyncSession], game_id: int, *, targets: Any = None
) -> bool:
    return await score_game_flaws_after_apply(maker, game_id, targets=targets, source="backfill")


async def test_spread_scope_black_user_scores_only_own_blunders(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """D-03 for a black user: ply 3 and 7 (black blunders) get a spread; ply 4 (the opponent's
    blunder) gets the spread and its own line facts too (SEED-261114-iuv Part A)."""
    game_id = await make_game(flaw_plies=(3, 4, 7), user_color="black")
    replayed = _replayed(_PGN)
    assert await _score(session_factory, game_id)
    rows = await _facepalm_rows(session_factory, game_id)
    for ply in (3, 7):
        pre, played = replayed[ply]
        post = pre.copy()
        post.push_uci(played)
        assert rows[ply]["maia_reply_spread"] == pytest.approx(
            reply_spread(fake_full_policy(post.fen(), 0.0)), rel=_REAL_RELATIVE_TOLERANCE
        )
    _assert_opponent_blunder_facts(rows[4], 4)


@pytest.mark.parametrize(
    ("user_color", "flaw_plies", "mistake_ply", "opponent_ply", "scored_ply"),
    [
        # White user: ply 2 mistake, ply 5 black blunder, ply 4 white blunder (the only scored one).
        ("white", (2, 4, 5), 2, 5, 4),
        # Black user: ply 3 mistake, ply 4 white blunder, ply 7 black blunder (the only scored one).
        ("black", (3, 4, 7), 3, 4, 7),
    ],
)
async def test_spread_scope_mistakes_stay_null_opponent_blunder_is_scored(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    user_color: Literal["white", "black"],
    flaw_plies: tuple[int, ...],
    mistake_ply: int,
    opponent_ply: int,
    scored_ply: int,
) -> None:
    """D-03: mistakes never receive a spread; an opponent blunder gets the spread and its line
    facts (SEED-261114-iuv Part A), for both colors."""
    game_id = await make_game(
        flaw_plies=flaw_plies, user_color=user_color, severities={mistake_ply: 1}
    )
    assert await _score(session_factory, game_id)
    rows = await _facepalm_rows(session_factory, game_id)
    assert rows[mistake_ply] == _ALL_NULL_FACEPALM
    _assert_opponent_blunder_facts(rows[opponent_ply], opponent_ply)
    assert rows[scored_ply]["maia_reply_spread"] is not None


@pytest.mark.parametrize(
    ("user_color", "flaw_ply"),
    [("white", 2), ("black", 3)],
)
async def test_post_blunder_elo_is_the_blunderers_for_both_colors(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
    user_color: Literal["white", "black"],
    flaw_ply: int,
) -> None:
    """D-04: the post-blunder call is fed the blunderer's pinned Elo, never the opponent's."""
    game_id = await make_game(flaw_plies=(flaw_ply,), user_color=user_color)
    calls = _recording_policy(monkeypatch)
    assert await _score(session_factory, game_id)
    own = _pinned_elo(_WHITE_RATING if user_color == "white" else _BLACK_RATING)
    opp = _pinned_elo(_BLACK_RATING if user_color == "white" else _WHITE_RATING)
    assert own != opp, "the test needs distinct pinned Elos to be meaningful"
    assert len(calls) == 2
    pre_fen, pre_elo = calls[0]
    post_fen, post_elo = calls[1]
    # Base call: blunderer to move. Post-blunder call: opponent to move, SAME (blunderer) Elo.
    assert pre_fen.split(" ")[1] == ("w" if user_color == "white" else "b")
    assert post_fen.split(" ")[1] == ("b" if user_color == "white" else "w")
    assert pre_elo == own
    assert post_elo == own
    assert post_elo != opp


async def test_post_blunder_en_passant_board_is_exact(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-05: the post-blunder board keeps the ep square the played move created."""
    game_id = await make_game(pgn=_EP_PGN, flaw_plies=(3,), user_color="black")
    calls = _recording_policy(monkeypatch)
    assert await _score(session_factory, game_id)
    rows = await _facepalm_rows(session_factory, game_id)
    assert rows[3]["maia_reply_spread"] is not None
    assert any(" d6 " in fen for fen, _ in calls)


async def test_post_blunder_castling_board_is_exact(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-05: castling rights survive into the post-blunder board (white may still castle)."""
    game_id = await make_game(flaw_plies=(7,), user_color="black")
    calls = _recording_policy(monkeypatch)
    assert await _score(session_factory, game_id)
    post_fen, _elo = calls[1]
    assert post_fen.split(" ")[2] == "KQkq"


def test_target_boards_are_never_mutated() -> None:
    """D-05: the drain's own target boards keep their FEN and move stack after scoring."""
    replayed = _replayed(_PGN)
    boards = {ply: (board, uci) for ply, (board, uci) in replayed.items()}
    before = {ply: (b.fen(), list(b.move_stack)) for ply, (b, _) in boards.items()}
    inputs = maia_flaw_scoring.GameMaiaInputs(
        game_id=1,
        user_id=_TEST_USER_ID,
        pgn=_PGN,
        white_rating=_WHITE_RATING,
        black_rating=_BLACK_RATING,
        platform="lichess",
        time_control_bucket="blitz",
        is_correspondence=False,
        user_color="white",
        flaws=tuple(
            maia_flaw_scoring.FlawMaiaInput(
                ply=ply,
                fen=replayed[ply][0].board_fen(),
                severity=2,
                # The line walk replays the stored line on a copy of the same board.
                refutation_pv=_mainline_line(_PGN, 2, _PGN_LAST_PLY - 2) if ply == 2 else None,
                best_pv=None,
                best_move=None,
                stored_played_prob=None,
                stored_reply_spread=None,
                stored_best_prob=None,
                stored_pre_spread=None,
                stored_best_reply_prob=None,
            )
            for ply in (2, 8)
        ),
    )
    score = score_game(inputs, boards)
    assert score.rows[0]["maia_reply_spread"] is not None, "ply 2 must have been scored"
    assert score.rows[0]["line_mate_ply"] is not None or any(
        v is not None for v in score.rows[0]["played_line_material"] or []
    ), "the line walk must have run on ply 2"
    after = {ply: (b.fen(), list(b.move_stack)) for ply, (b, _) in boards.items()}
    assert after == before


async def test_blunder_that_stalemates_has_no_legal_reply(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stalemating blunder spends no post-board inference (no_legal_reply); the game is stamped."""
    final = _replayed(_STALEMATE_PGN)[_STALEMATE_PLY]
    post = final[0].copy()
    post.push_uci(final[1])
    assert post.is_stalemate(), "fixture sanity: the last move must stalemate Black"
    game_id = await make_game(pgn=_STALEMATE_PGN, flaw_plies=(_STALEMATE_PLY,))
    score = score_game(await _inputs(session_factory, game_id), None)
    assert score.reasons["no_legal_reply"] == 1
    calls = _recording_policy(monkeypatch)
    assert await _score(session_factory, game_id)
    assert len(calls) == 1
    assert (await _facepalm_rows(session_factory, game_id))[_STALEMATE_PLY][
        "maia_reply_spread"
    ] is None
    assert await _stamp(session_factory, game_id) is not None


async def test_call_count_is_base_plus_scorable_blunders(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """White user, flaws (2, 5, 8): three base calls plus a post-board call for plies 2 and 8
    (the user's blunders) and ply 5 (the opponent's blunder, SEED-261114-iuv Part A)."""
    game_id = await make_game()
    calls = _recording_policy(monkeypatch)
    assert await _score(session_factory, game_id)
    assert len(calls) == _RECORDED_CALL_COUNT_WHITE_USER


async def test_game_without_user_blunders_stamped_with_opponent_calls_only(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-09: opponent-only blunders and user mistakes still stamp the game; the only post-board
    call is the opponent blunder's (3 calls: two base, one post-blunder)."""
    game_id = await make_game(flaw_plies=(2, 5), severities={2: 1})
    calls = _recording_policy(monkeypatch)
    assert await _score(session_factory, game_id)
    assert len(calls) == 3
    rows = await _facepalm_rows(session_factory, game_id)
    assert rows[2] == _ALL_NULL_FACEPALM
    _assert_opponent_blunder_facts(rows[5], 5)
    assert all(stamp is not None for stamp in (await _stamps(session_factory, game_id)).values())


async def test_maia_absent_stamps_nothing(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game_id = await make_game()
    monkeypatch.setattr(maia_engine, "_session", None)
    assert not await _score(session_factory, game_id)
    assert all(stamp is None for stamp in (await _stamps(session_factory, game_id)).values())
    rows = await _facepalm_rows(session_factory, game_id)
    assert all(r == _ALL_NULL_FACEPALM for r in rows.values())


async def test_severity_change_is_fingerprint_changed(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """A mid-flight change of a severity writes nothing and stamps nothing."""
    game_id = await make_game(flaw_plies=(2,))
    score = score_game(await _inputs(session_factory, game_id), None)
    async with session_factory() as session:
        await session.execute(
            sa.update(GameFlaw)
            .where(GameFlaw.game_id == game_id, GameFlaw.ply == 2)
            .values(severity=1)
        )
        await session.commit()
    async with session_factory() as session:
        outcomes = await write_game_maia_scores(session, [score], require_unstamped=False)
        await session.commit()
    assert outcomes == {game_id: "fingerprint_changed"}
    rows = await _facepalm_rows(session_factory, game_id)
    assert all(r == _ALL_NULL_FACEPALM for r in rows.values())
    assert all(stamp is None for stamp in (await _stamps(session_factory, game_id)).values())


# ---------------------------------------------------------------------------
# Facepalm scope, guards and fingerprint (Phase 250 D-05 .. D-07)
# ---------------------------------------------------------------------------

_ALL_NULL_FACEPALM: dict[str, None] = dict.fromkeys(FACEPALM_COLUMNS)
# The four line-fact columns: written for blunders of either side (SEED-261114-iuv Part A step 4).
_LINE_FACT_COLUMNS: tuple[str, ...] = tuple(c for c in FACEPALM_COLUMNS if c != "maia_reply_spread")


def _expected_line_facts(
    pgn: str, ply: int, stored_line: str | None, best_line: str | None = None
) -> dict[str, Any]:
    """The four line facts the module's own derivation yields for one blunder (NULLs without lines)."""
    pre, played = _replayed(pgn)[ply]
    played_facts = line_facts(pre, played, stored_line)
    best_facts = best_line_facts(pre, best_line)
    best_material = best_facts.material_array()
    # 259 D-05: the scalars come from the one write-time function on the same board and lines.
    scalars = facepalm_material_inputs(pre, played, stored_line, best_line)
    return {
        **_fact_columns(played_facts),
        "best_line_material": None if all(v is None for v in best_material) else best_material,
        "best_line_mate_ply": best_facts.opponent_mate_ply,
        "material_loss": scalars.loss,
        "material_missed": scalars.missed,
    }


def _assert_opponent_blunder_facts(
    row: dict[str, Any], ply: int, lines: dict[int, str] | None = None, pgn: str = _PGN
) -> None:
    """An opponent blunder row: the reply spread set and the four line facts equal the derivation
    from the stored lines (`lines`, keyed by game_positions ply; NULL facts where none is stored)."""
    assert row["maia_reply_spread"] is not None
    expected = _expected_line_facts(pgn, ply, (lines or {}).get(ply + 1), (lines or {}).get(ply))
    assert {column: row[column] for column in _LINE_FACT_COLUMNS} == expected


# Exact binary fractions: the REAL columns round-trip equal.
_STALE_FACEPALM: dict[str, Any] = {
    "maia_reply_spread": 4.5,
    "line_mate_ply": 3,
    # Phase 254 D-09 fact columns (nine slots each, the stored shape).
    "played_line_material": [1, 0, -1, 2, -2, 3, 0, 1, -1],
    "best_line_material": [0, 1, 2, 3, 2, 1, 0, 1, 2],
    "best_line_mate_ply": 2,
    # Phase 259 D-05 scalars (exact binary fractions, so the REAL columns round-trip equal).
    "material_loss": 1.5,
    "material_missed": 0.5,
}


async def _scotch_user_blunder(
    make_game: MakeGame, *, with_line: bool = True, **kwargs: Any
) -> tuple[int, str | None]:
    """A Scotch game whose white ply-4 blunder carries (or lacks) its stored ten-ply line."""
    pv = _mainline_line(_SCOTCH_PGN, _SCOTCH_FLAW_PLY, _STORED_LINE_PLIES) if with_line else None
    game_id = await make_game(
        pgn=_SCOTCH_PGN,
        flaw_plies=(_SCOTCH_FLAW_PLY,),
        pv={_SCOTCH_FLAW_PLY + 1: pv} if pv is not None else None,
        **kwargs,
    )
    return game_id, pv


async def test_facepalm_scope_mistake_rows_null_blunders_of_both_sides_scored(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """D-06: a user mistake carries NULL in all eight columns (even with a stored line and stale
    values on it); an opponent blunder gets freshly derived line facts and a fresh spread, replacing
    the stale ones (SEED-261114-iuv Part A step 4); the user blunder is scored."""
    lines = {
        ply + 1: _mainline_line(_PGN, ply, _PGN_LAST_PLY - ply)
        for ply in (2, 4, 5)  # lines exist after every flaw, so a broken scope would score them
    }
    game_id = await make_game(flaw_plies=(2, 4, 5), severities={2: 1}, pv=lines)
    async with session_factory() as session:
        await session.execute(
            sa.update(GameFlaw)
            .where(GameFlaw.game_id == game_id, GameFlaw.ply.in_((2, 5)))
            .values(**_STALE_FACEPALM)
        )
        await session.commit()
    assert await _score(session_factory, game_id)
    rows = await _facepalm_rows(session_factory, game_id)
    assert rows[2] == _ALL_NULL_FACEPALM, "user mistake"
    _assert_opponent_blunder_facts(rows[5], 5, lines)
    assert rows[5]["maia_reply_spread"] != _STALE_FACEPALM["maia_reply_spread"]
    assert rows[5]["played_line_material"] != _STALE_FACEPALM["played_line_material"]
    pre, played = _replayed(_PGN)[4]
    assert rows[4]["maia_reply_spread"] is not None
    for column, value in _fact_columns(line_facts(pre, played, lines[5])).items():
        assert rows[4][column] == value, column


async def test_facepalm_no_rating_keeps_line_facts_only(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """A user blunder whose mover has no rating: line facts from the board, spread and score NULL."""
    game_id, pv = await _scotch_user_blunder(make_game, white_rating=None)
    assert await _score(session_factory, game_id)
    row = (await _facepalm_rows(session_factory, game_id))[_SCOTCH_FLAW_PLY]
    pre, played = _replayed(_SCOTCH_PGN)[_SCOTCH_FLAW_PLY]
    expected = _fact_columns(line_facts(pre, played, pv))
    assert any(v is not None for v in expected.values())
    assert {c: row[c] for c in expected} == expected
    assert row["maia_reply_spread"] is None
    assert (await _stamps(session_factory, game_id))["facepalm_line_completed_at"] is not None


async def test_facepalm_missing_line_leaves_score_null(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """No stored line: line facts NULL, the spread (Maia only) is still set, the score is NULL."""
    game_id, _ = await _scotch_user_blunder(make_game, with_line=False)
    assert await _score(session_factory, game_id)
    row = (await _facepalm_rows(session_factory, game_id))[_SCOTCH_FLAW_PLY]
    assert row["maia_reply_spread"] is not None
    assert row["played_line_material"] is None
    assert row["line_mate_ply"] is None


async def test_facepalm_line_change_is_fingerprint_changed(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """D-07: a Phase 252 repair rewrites game_positions.pv at ply + 1 and keeps its first token.

    Only the line itself tells the write that the scored line facts are stale (the repaired line
    keeps its first token). Nothing is written, no stamp set.
    """
    game_id, pv = await _scotch_user_blunder(make_game)
    assert pv is not None
    score = score_game(await _inputs(session_factory, game_id), None)
    repaired = " ".join(pv.split(" ")[:3])
    async with session_factory() as session:
        await session.execute(
            sa.update(GamePosition)
            .where(GamePosition.game_id == game_id, GamePosition.ply == _SCOTCH_FLAW_PLY + 1)
            .values(pv=repaired)
        )
        await session.commit()
    async with session_factory() as session:
        outcomes = await write_game_maia_scores(session, [score], require_unstamped=False)
        await session.commit()
    assert outcomes == {game_id: "fingerprint_changed"}
    rows = await _facepalm_rows(session_factory, game_id)
    assert all(row == _ALL_NULL_FACEPALM for row in rows.values())
    assert all(stamp is None for stamp in (await _stamps(session_factory, game_id)).values())


async def test_facepalm_full_rescore_clears_row_downgraded_from_blunder(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """A full re-score writes NULL facepalm values on a row since downgraded to a mistake."""
    game_id = await make_game(flaw_plies=(2,), severities={2: 1})
    async with session_factory() as session:
        await session.execute(
            sa.update(GameFlaw)
            .where(GameFlaw.game_id == game_id, GameFlaw.ply == 2)
            .values(**_STALE_FACEPALM)
        )
        await session.commit()
    assert (await _facepalm_rows(session_factory, game_id))[2] != _ALL_NULL_FACEPALM
    assert await _score(session_factory, game_id)
    assert (await _facepalm_rows(session_factory, game_id))[2] == _ALL_NULL_FACEPALM


async def test_facepalm_stalemating_blunder_has_null_spread(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """A blunder that leaves no legal reply: spread NULL (no_legal_reply), score NULL."""
    game_id = await make_game(pgn=_STALEMATE_PGN, flaw_plies=(_STALEMATE_PLY,))
    assert await _score(session_factory, game_id)
    row = (await _facepalm_rows(session_factory, game_id))[_STALEMATE_PLY]
    assert row["maia_reply_spread"] is None


# ---------------------------------------------------------------------------
# Spread and line modes (Phase 250 D-08, D-18)
# ---------------------------------------------------------------------------

_PK_KEYS = {"user_id", "game_id", "ply"}
# A stored played probability that no fake_full_policy call could produce for the Scotch ply-4
# move, so a score computed from it proves the stored value was read, not re-derived.
_STORED_PLAYED_PROB = 0.0123
# The Scotch blunder loses no material, so under best_prob_for_misses its score reads the best-move
# probability: a stored one keeps the row scored (254 WR-01 / 256 D-04).
_STORED_BEST_PROB = 0.3
_STORED_SPREAD = 3.5
_STORED_PRE_SPREAD = 6.5


async def _store_base_values(
    maker: async_sessionmaker[AsyncSession], game_id: int, ply: int, **values: Any
) -> None:
    async with maker() as session:
        await session.execute(
            sa.update(GameFlaw)
            .where(GameFlaw.game_id == game_id, GameFlaw.ply == ply)
            .values(**values)
        )
        await session.commit()


async def test_spread_mode_rows_carry_only_facepalm_keys(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-08: user blunders only, key set = PK + the facepalm fact columns, played prob from the
    stored value, exactly one inference per user blunder (the post-blunder position)."""
    # Ply 4 is white's blunder (user), ply 5 black's blunder (opponent), ply 2 a user mistake.
    pv = _mainline_line(_SCOTCH_PGN, _SCOTCH_FLAW_PLY, _STORED_LINE_PLIES)
    game_id = await make_game(
        pgn=_SCOTCH_PGN,
        flaw_plies=(2, _SCOTCH_FLAW_PLY, 5),
        severities={2: 1},
        pv={_SCOTCH_FLAW_PLY + 1: pv},
    )
    await _store_base_values(
        session_factory,
        game_id,
        _SCOTCH_FLAW_PLY,
        maia_played_prob=_STORED_PLAYED_PROB,
        maia_best_prob=_STORED_BEST_PROB,
    )
    calls = _recording_policy(monkeypatch)

    score = score_game(await _inputs(session_factory, game_id), None, "spread")

    assert score.mode == "spread"
    assert [row["ply"] for row in score.rows] == [_SCOTCH_FLAW_PLY]
    row = score.rows[0]
    assert set(row) == _PK_KEYS | set(FACEPALM_COLUMNS)
    pre, played = _replayed(_SCOTCH_PGN)[_SCOTCH_FLAW_PLY]
    post = pre.copy()
    post.push_uci(played)
    # One inference for the post-blunder position, none for the base position.
    assert [fen for fen, _elo in calls] == [post.fen()]
    spread = reply_spread(fake_full_policy(post.fen(), 0.0))
    assert row["maia_reply_spread"] == pytest.approx(spread)
    facts = line_facts(pre, played, pv)
    for column, value in _fact_columns(facts).items():
        assert row[column] == value, column
    _assert_no_dropped_keys(row)
    expected = facepalm_score(
        FacepalmFacts(
            played_prob=_STORED_PLAYED_PROB,
            best_prob=_STORED_BEST_PROB,
            reply_spread=spread,
            played_material=facts.material_array(),
            mate_ply=facts.mate_ply,
        ),
        lam=FACEPALM_DRILL_LAMBDA,
    )
    assert expected is not None, "the fixture line must settle the score"
    assert score.spreads_scored == 1
    assert score.scores_set == 1
    assert score.user_blunders == 1


def _expected_score_without_spread(pre: chess.Board, played: str, pv: str | None) -> float:
    """The shipped model's score of the Scotch blunder when its reply spread is unknown.

    Since the Phase 254 refit (spread form "best_prob_for_misses") the spread is read only on rows
    that lose material at depth 3; this line does not, so a NULL spread no longer unscores it.
    """
    facts = line_facts(pre, played, pv)
    assert (facts.loss_at(3) or 0) <= 0, "the fixture line must not lose material"
    score = facepalm_score(
        FacepalmFacts(
            played_prob=_STORED_PLAYED_PROB,
            best_prob=_STORED_BEST_PROB,
            reply_spread=None,
            played_material=facts.material_array(),
            mate_ply=facts.mate_ply,
        ),
        lam=FACEPALM_DRILL_LAMBDA,
    )
    assert score is not None
    return score


async def test_spread_mode_no_rating_keeps_line_facts_and_skips_inference(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A user blunder whose mover has no rating: line facts written, spread NULL, no inference."""
    pv = _mainline_line(_SCOTCH_PGN, _SCOTCH_FLAW_PLY, _STORED_LINE_PLIES)
    game_id = await make_game(
        pgn=_SCOTCH_PGN,
        flaw_plies=(_SCOTCH_FLAW_PLY,),
        white_rating=None,
        pv={_SCOTCH_FLAW_PLY + 1: pv},
    )
    await _store_base_values(
        session_factory,
        game_id,
        _SCOTCH_FLAW_PLY,
        maia_played_prob=_STORED_PLAYED_PROB,
        maia_best_prob=_STORED_BEST_PROB,
    )
    calls = _recording_policy(monkeypatch)

    score = score_game(await _inputs(session_factory, game_id), None, "spread")

    row = score.rows[0]
    assert calls == []
    assert row["maia_reply_spread"] is None
    pre, played = _replayed(_SCOTCH_PGN)[_SCOTCH_FLAW_PLY]
    # The facts still score in memory without a spread (the line loses no material).
    assert _expected_score_without_spread(pre, played, pv) is not None
    assert score.scores_set == 1
    assert row["played_line_material"] is not None
    assert score.reasons["no_rating"] == 1


# Line mode (250 D-18): the line fact keys, no Maia, no rating.
_LINE_ROW_KEYS = {c for c in FACEPALM_COLUMNS if c != "maia_reply_spread"}


async def test_line_mode_never_calls_maia_and_writes_only_line_keys(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-18: no full_policy call (a raising one proves it), no rating needed, rows are blunders of
    BOTH sides (SEED-261114-iuv Part A step 4) with PK + the line fact keys and never
    maia_reply_spread; a mistake gets no row."""
    pv = _mainline_line(_SCOTCH_PGN, _SCOTCH_FLAW_PLY, _STORED_LINE_PLIES)
    opponent_ply = _SCOTCH_FLAW_PLY + 1
    opponent_pv = _mainline_line(_SCOTCH_PGN, opponent_ply, _STORED_LINE_PLIES)
    game_id = await make_game(
        pgn=_SCOTCH_PGN,
        flaw_plies=(2, _SCOTCH_FLAW_PLY, opponent_ply),
        severities={2: 1},
        white_rating=None,
        black_rating=None,
        pv={_SCOTCH_FLAW_PLY + 1: pv, opponent_ply + 1: opponent_pv},
    )
    for stored_ply in (_SCOTCH_FLAW_PLY, opponent_ply):
        await _store_base_values(
            session_factory,
            game_id,
            stored_ply,
            maia_played_prob=_STORED_PLAYED_PROB,
            maia_reply_spread=_STORED_SPREAD,
            maia_best_prob=_STORED_BEST_PROB,
        )

    def _must_not_run(fen: str, elo: float) -> dict[str, float]:
        raise AssertionError("line mode must never run Maia")

    monkeypatch.setattr(maia_flaw_scoring, "full_policy", _must_not_run)

    score = score_game(await _inputs(session_factory, game_id), None, "line")

    assert score.mode == "line"
    assert [row["ply"] for row in score.rows] == [_SCOTCH_FLAW_PLY, opponent_ply]
    row, opponent_row = score.rows
    for each in score.rows:
        assert set(each) == _PK_KEYS | _LINE_ROW_KEYS
        assert "maia_reply_spread" not in each
        _assert_no_dropped_keys(each)
    pre, played = _replayed(_SCOTCH_PGN)[_SCOTCH_FLAW_PLY]
    facts = line_facts(pre, played, pv)
    for column, value in _fact_columns(facts).items():
        assert row[column] == value, column
    # The opponent row carries the same derivation over its own stored line.
    # (game_positions.pv at the opponent's own ply is the user's stored line, hence the best line.)
    opponent_expected = _expected_line_facts(_SCOTCH_PGN, opponent_ply, opponent_pv, pv)
    assert {c: opponent_row[c] for c in _LINE_FACT_COLUMNS} == opponent_expected
    expected = facepalm_score(
        FacepalmFacts(
            played_prob=_STORED_PLAYED_PROB,
            best_prob=_STORED_BEST_PROB,
            reply_spread=_STORED_SPREAD,
            played_material=facts.material_array(),
            mate_ply=facts.mate_ply,
        ),
        lam=FACEPALM_DRILL_LAMBDA,
    )
    assert expected is not None
    # The user counters count the user row only; the opponent row has its own counter.
    assert score.scores_set == 1
    assert score.spreads_scored == 0
    assert (score.user_blunders, score.opponent_blunders) == (1, 1)
    assert score.opponent_scores_set == 1
    assert score.opponent_spreads_scored == 0 and score.opponent_pre_scored == 0


async def test_line_mode_blunder_without_stored_spread_gets_facts_but_no_score(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """A blunder the spread pass has not reached: line facts are written, and the in-memory score
    is the shipped model's score without a spread (a spread-less row that loses no material keeps
    one)."""
    game_id, pv = await _scotch_user_blunder(make_game)
    await _store_base_values(
        session_factory,
        game_id,
        _SCOTCH_FLAW_PLY,
        maia_played_prob=_STORED_PLAYED_PROB,
        maia_best_prob=_STORED_BEST_PROB,
    )
    score = score_game(await _inputs(session_factory, game_id), None, "line")
    row = score.rows[0]
    pre, played = _replayed(_SCOTCH_PGN)[_SCOTCH_FLAW_PLY]
    assert row["played_line_material"] == line_facts(pre, played, pv).material_array()
    assert _expected_score_without_spread(pre, played, pv) is not None
    assert score.scores_set == 1


async def _write_line_scores(
    maker: async_sessionmaker[AsyncSession],
    game_id: int,
    *,
    require_unstamped: bool,
    line_cutoff: datetime | None,
) -> Any:
    score = score_game(await _inputs(maker, game_id), None, "line")
    async with maker() as session:
        outcomes = await write_game_maia_scores(
            session, [score], require_unstamped=require_unstamped, line_cutoff=line_cutoff
        )
        await session.commit()
    return outcomes


async def test_write_line_mode_needs_a_cutoff_when_require_unstamped(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    game_id, _ = await _scotch_user_blunder(make_game)
    with pytest.raises(ValueError, match="needs a cutoff"):
        await _write_line_scores(session_factory, game_id, require_unstamped=True, line_cutoff=None)


async def test_write_line_mode_cutoff_decides_already_stamped(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """A line stamp at or after the cutoff is already_stamped; an older (or NULL) one is rewritten,
    and a line write sets only the line stamp."""
    game_id, _ = await _scotch_user_blunder(make_game)
    cutoff = datetime(2026, 11, 10, tzinfo=timezone.utc)
    async with session_factory() as session:
        await session.execute(
            sa.update(Game)
            .where(Game.id == game_id)
            .values(facepalm_line_completed_at=cutoff + timedelta(days=1))
        )
        await session.commit()
    after = await _write_line_scores(
        session_factory, game_id, require_unstamped=True, line_cutoff=cutoff
    )
    assert after == {game_id: "already_stamped"}
    equal = await _write_line_scores(
        session_factory, game_id, require_unstamped=True, line_cutoff=cutoff + timedelta(days=1)
    )
    assert equal == {game_id: "already_stamped"}, "a stamp equal to the cutoff counts as done"

    stamps_before = await _stamps(session_factory, game_id)
    before = await _write_line_scores(
        session_factory,
        game_id,
        require_unstamped=True,
        line_cutoff=cutoff + timedelta(days=2),
    )
    assert before == {game_id: "stamped"}
    stamps_after = await _stamps(session_factory, game_id)
    assert stamps_after["facepalm_line_completed_at"] > stamps_before["facepalm_line_completed_at"]
    assert stamps_after["maia_flaws_completed_at"] is None
    assert stamps_after["facepalm_spread_completed_at"] is None


async def test_write_line_mode_writes_opponent_line_facts_never_maia_columns(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """A line write over an opponent blunder sets its four line facts and only the line stamp; the
    base value, the spread and both pre keys keep their stored values."""
    game_id = await _opponent_game(make_game)
    stored = {
        "maia_played_prob": _STORED_PLAYED_PROB,
        "maia_reply_spread": _STORED_SPREAD,
        "maia_best_prob": _STORED_BEST_PROB,
        "maia_pre_spread": _STORED_PRE_SPREAD,
    }
    await _store_base_values(session_factory, game_id, _OPPONENT_PLY, **stored)
    outcomes = await _write_line_scores(
        session_factory,
        game_id,
        require_unstamped=True,
        line_cutoff=datetime(2026, 11, 10, tzinfo=timezone.utc),
    )
    assert outcomes == {game_id: "stamped"}
    row = await _flaw_row_full(session_factory, game_id, _OPPONENT_PLY)
    expected = _expected_line_facts(
        _PGN, _OPPONENT_PLY, _mainline_line(_PGN, _OPPONENT_PLY, 3), _OPPONENT_BEST_MOVE
    )
    assert {c: getattr(row, c) for c in _LINE_FACT_COLUMNS} == expected
    for column, value in stored.items():
        assert getattr(row, column) == pytest.approx(value, rel=_REAL_RELATIVE_TOLERANCE), column
    stamps = await _stamps(session_factory, game_id)
    assert stamps["facepalm_line_completed_at"] is not None
    assert stamps["maia_flaws_completed_at"] is None
    assert stamps["facepalm_spread_completed_at"] is None
    assert stamps["facepalm_pre_completed_at"] is None


async def test_write_spread_mode_sets_spread_and_line_stamps_only(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    game_id, _ = await _scotch_user_blunder(make_game)
    score = score_game(await _inputs(session_factory, game_id), None, "spread")
    async with session_factory() as session:
        outcomes = await write_game_maia_scores(session, [score], require_unstamped=True)
        await session.commit()
    assert outcomes == {game_id: "stamped"}
    stamps = await _stamps(session_factory, game_id)
    assert stamps["facepalm_spread_completed_at"] is not None
    assert stamps["facepalm_line_completed_at"] is not None
    assert stamps["maia_flaws_completed_at"] is None
    async with session_factory() as session:
        again = await write_game_maia_scores(session, [score], require_unstamped=True)
    assert again == {game_id: "already_stamped"}


# Pre mode (254 D-08): the two pre-blunder keys only, one pre-blunder inference per user blunder.
_PRE_ROW_KEYS = _PK_KEYS | set(FACEPALM_PRE_COLUMNS)


def _scotch_best_move() -> str:
    """A legal move at the Scotch ply-4 decision position that is not the played move."""
    pre, played = _replayed(_SCOTCH_PGN)[_SCOTCH_FLAW_PLY]
    return next(m.uci() for m in sorted(pre.legal_moves, key=str) if m.uci() != played)


async def test_pre_mode_rows_carry_only_pre_keys(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-08: user blunders only, key set = PK + the two pre keys, exactly one inference per user
    blunder at the PRE-blunder position and the mover's pinned Elo, values as the hook derives them."""
    best = _scotch_best_move()
    # Ply 4 is white's blunder (user), ply 5 black's blunder (opponent), ply 2 a user mistake.
    game_id = await make_game(
        pgn=_SCOTCH_PGN,
        flaw_plies=(2, _SCOTCH_FLAW_PLY, 5),
        severities={2: 1},
        pv={_SCOTCH_FLAW_PLY: best},
    )
    calls = _recording_policy(monkeypatch)

    score = score_game(await _inputs(session_factory, game_id), None, "pre")

    assert score.mode == "pre"
    assert [row["ply"] for row in score.rows] == [_SCOTCH_FLAW_PLY]
    row = score.rows[0]
    assert set(row) == _PRE_ROW_KEYS
    pre, _played = _replayed(_SCOTCH_PGN)[_SCOTCH_FLAW_PLY]
    assert calls == [(pre.fen(), _pinned_elo(_WHITE_RATING))]
    probs = fake_full_policy(pre.fen(), 0.0)
    assert row["maia_best_prob"] == pytest.approx(probs[best])
    assert row["maia_pre_spread"] == pytest.approx(pre_blunder_spread(probs))
    assert score.pre_scored == 1
    assert score.user_blunders == 1
    assert not score.reasons


async def test_pre_mode_no_rating_skips_inference(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A user blunder whose mover has no rating: both pre keys NULL, no inference, reason counted."""
    game_id = await make_game(
        pgn=_SCOTCH_PGN,
        flaw_plies=(_SCOTCH_FLAW_PLY,),
        white_rating=None,
        pv={_SCOTCH_FLAW_PLY: _scotch_best_move()},
    )
    calls = _recording_policy(monkeypatch)

    score = score_game(await _inputs(session_factory, game_id), None, "pre")

    assert calls == []
    assert score.rows[0]["maia_best_prob"] is None
    assert score.rows[0]["maia_pre_spread"] is None
    assert score.reasons["no_rating"] == 1
    assert score.pre_scored == 0


async def test_pre_mode_best_move_missing_keeps_the_spread(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """No best line and no stored best move: maia_best_prob NULL, best_move_missing counted, the
    pre-blunder spread is still stored (the two inputs are independent)."""
    game_id, _ = await _scotch_user_blunder(make_game)

    score = score_game(await _inputs(session_factory, game_id), None, "pre")

    row = score.rows[0]
    assert row["maia_best_prob"] is None
    assert row["maia_pre_spread"] is not None
    assert score.reasons["best_move_missing"] == 1
    assert score.pre_scored == 1


async def test_write_pre_mode_sets_only_the_pre_stamp(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    game_id, _ = await _scotch_user_blunder(make_game)
    score = score_game(await _inputs(session_factory, game_id), None, "pre")
    async with session_factory() as session:
        outcomes = await write_game_maia_scores(session, [score], require_unstamped=True)
        await session.commit()
    assert outcomes == {game_id: "stamped"}
    stamps = await _stamps(session_factory, game_id)
    assert stamps["facepalm_pre_completed_at"] is not None
    assert stamps["maia_flaws_completed_at"] is None
    assert stamps["facepalm_spread_completed_at"] is None
    assert stamps["facepalm_line_completed_at"] is None
    async with session_factory() as session:
        again = await write_game_maia_scores(session, [score], require_unstamped=True)
    assert again == {game_id: "already_stamped"}


# ---------------------------------------------------------------------------
# Replay (D-06)
# ---------------------------------------------------------------------------


async def test_replay_castling_and_ep_fen(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The FEN handed to full_policy is the full FEN: castling field and ep square intact."""
    # Black user: the white exd6 at ply 4 is the opponent's blunder: base call plus post-board call.
    game_id = await make_game(pgn=_EP_PGN, flaw_plies=(4,), user_color="black")
    seen: list[str] = []

    def _spy(fen: str, elo: float) -> dict[str, float]:
        seen.append(fen)
        return fake_full_policy(fen, elo)

    monkeypatch.setattr(maia_flaw_scoring, "full_policy", _spy)
    assert await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )
    assert len(seen) == 2
    fields = seen[0].split(" ")
    assert fields[2] == "KQkq", "castling field must survive the replay"
    assert fields[3] == "d6", "en-passant square must survive the replay"


async def test_replay_fen_mismatch_counted(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    game_id = await make_game(fen_override={5: "8/8/8/8/8/8/8/8"})
    score = score_game(await _inputs(session_factory, game_id), None)
    assert score.reasons["fen_mismatch"] == 1
    assert await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )
    rows = await _flaw_rows(session_factory, game_id)
    assert _all_null(rows[5])
    assert not _all_null(rows[2])
    assert await _stamp(session_factory, game_id) is not None


async def test_replay_invalid_root_and_unparseable(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Kingless custom root: Board.is_valid() is False.
    invalid_pgn = '[SetUp "1"]\n[FEN "8/8/8/8/8/8/PPPPPPPP/PPPPPPPP w - - 0 1"]\n\n1. a3 *'
    boards, reason = replay_flaw_boards(invalid_pgn, {2, 5})
    assert boards == {} and reason == "invalid_root"
    boards, reason = replay_flaw_boards("", {2, 5})
    assert boards == {} and reason == "pgn_unparseable"

    # Through the scorer: every flaw is counted with the game-level reason, flaws NULL,
    # the game still stamped.
    game_id = await make_game(pgn=invalid_pgn, flaw_plies=(2, 5), fen_override={2: "x", 5: "y"})
    score = score_game(await _inputs(session_factory, game_id), None)
    assert score.reasons["invalid_root"] == 2
    assert await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )
    rows = await _flaw_rows(session_factory, game_id)
    assert all(_all_null(r) for r in rows.values())
    assert await _stamp(session_factory, game_id) is not None

    def _boom(_stream: Any) -> Any:
        raise RuntimeError("corrupt pgn")

    monkeypatch.setattr("chess.pgn.read_game", _boom)
    boards, reason = replay_flaw_boards(_PGN, {2})
    assert boards == {} and reason == "pgn_unparseable"


# ---------------------------------------------------------------------------
# Scoring and rewrite (D-08)
# ---------------------------------------------------------------------------


async def test_rescore_overwrites_surviving_and_new(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    game_id = await make_game(flaw_plies=(2, 5), stale_plies=(2,))
    replayed = _replayed(_PGN)
    assert await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )
    rows = await _flaw_rows(session_factory, game_id)
    for ply in (2, 5):
        assert rows[ply]["maia_played_prob"] == pytest.approx(
            _expected_played_prob(replayed, ply), abs=_REAL_TOLERANCE
        )
    assert rows[2]["maia_played_prob"] != pytest.approx(_STALE_PROB, abs=_REAL_TOLERANCE)


async def test_rescore_idempotent(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    game_id = await make_game()
    for _ in range(2):
        assert await score_game_flaws_after_apply(
            session_factory, game_id, targets=None, source="backfill"
        )
    first = await _flaw_rows(session_factory, game_id)
    assert await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )
    assert await _flaw_rows(session_factory, game_id) == first
    assert all(not _all_null(r) for r in first.values())
    assert await _stamp(session_factory, game_id) is not None


# ---------------------------------------------------------------------------
# Fingerprint guard, unstamped-only, deletion, batch (D-13)
# ---------------------------------------------------------------------------


async def test_fingerprint_changed_skips_write(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    game_id = await make_game()
    score = score_game(await _inputs(session_factory, game_id), None)
    # A concurrent reclassify changes a flaw's severity.
    async with session_factory() as session:
        await session.execute(
            sa.update(GameFlaw)
            .where(GameFlaw.game_id == game_id, GameFlaw.ply == 5)
            .values(severity=1)
        )
        await session.commit()
    async with session_factory() as session:
        outcomes = await write_game_maia_scores(session, [score], require_unstamped=False)
        await session.commit()
    assert outcomes == {game_id: "fingerprint_changed"}
    assert all(_all_null(r) for r in (await _flaw_rows(session_factory, game_id)).values())
    assert await _stamp(session_factory, game_id) is None


async def test_require_unstamped_skips_stamped(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    game_id = await make_game(stale_plies=(2,))
    inputs = await _inputs(session_factory, game_id)
    async with session_factory() as session:
        await session.execute(
            sa.update(Game).where(Game.id == game_id).values(maia_flaws_completed_at=sa.func.now())
        )
        await session.commit()
    async with session_factory() as session:
        outcomes = await write_game_maia_scores(
            session, [score_game(inputs, None)], require_unstamped=True
        )
        await session.commit()
    assert outcomes == {game_id: "already_stamped"}
    assert (await _flaw_rows(session_factory, game_id))[2]["maia_played_prob"] == pytest.approx(
        _STALE_PROB, abs=_REAL_TOLERANCE
    )
    async with session_factory() as session:
        outcomes = await write_game_maia_scores(
            session, [score_game(inputs, None)], require_unstamped=False
        )
        await session.commit()
    assert outcomes == {game_id: "stamped"}
    assert (await _flaw_rows(session_factory, game_id))[2]["maia_played_prob"] != pytest.approx(
        _STALE_PROB, abs=_REAL_TOLERANCE
    )


async def test_game_deleted_returns_game_missing(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    game_id = await make_game()
    score = score_game(await _inputs(session_factory, game_id), None)
    async with session_factory() as session:
        await session.execute(delete(Game).where(Game.id == game_id))
        await session.commit()
    async with session_factory() as session:
        outcomes = await write_game_maia_scores(session, [score], require_unstamped=False)
        await session.commit()
    assert outcomes == {game_id: "game_missing"}


async def test_batch_mixed_outcomes(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    ids = [await make_game(), await make_game(), await make_game()]
    scores = [score_game(await _inputs(session_factory, gid), None) for gid in ids]
    async with session_factory() as session:
        await session.execute(
            sa.update(GameFlaw)
            .where(GameFlaw.game_id == ids[1], GameFlaw.ply == 2)
            .values(severity=1)
        )
        await session.commit()
    async with session_factory() as session:
        outcomes = await write_game_maia_scores(session, scores, require_unstamped=False)
        await session.commit()
    assert outcomes == {
        ids[0]: "stamped",
        ids[1]: "fingerprint_changed",
        ids[2]: "stamped",
    }
    assert await _stamp(session_factory, ids[0]) is not None
    assert await _stamp(session_factory, ids[1]) is None
    assert await _stamp(session_factory, ids[2]) is not None


async def test_write_holds_advisory_lock_per_game(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    ids = [await make_game(), await make_game(), await make_game()]
    scores = [score_game(await _inputs(session_factory, gid), None) for gid in ids]
    async with session_factory() as session:
        await write_game_maia_scores(session, scores, require_unstamped=False)
        held = (
            await session.execute(
                sa.text(
                    "SELECT count(*) FROM pg_locks "
                    "WHERE locktype = 'advisory' AND pid = pg_backend_pid()"
                )
            )
        ).scalar_one()
        await session.rollback()
    assert held == len(ids)


async def test_write_rejects_oversized_batch(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    too_many = [
        maia_flaw_scoring.GameMaiaScore(
            game_id=i, user_id=1, fingerprint=frozenset(), rows=[], reasons=Counter()
        )
        for i in range(maia_flaw_scoring.MAX_GAMES_PER_WRITE_TXN + 1)
    ]
    async with session_factory() as session:
        with pytest.raises(ValueError):
            await write_game_maia_scores(session, too_many, require_unstamped=False)


# ---------------------------------------------------------------------------
# Stamp guardrail (D-05) and mover rating (D-03)
# ---------------------------------------------------------------------------


async def test_stamp_maia_absent_never_stamps(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game_id = await make_game()
    monkeypatch.setattr(maia_engine, "_session", None)
    assert not await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )
    assert await _stamp(session_factory, game_id) is None
    assert all(_all_null(r) for r in (await _flaw_rows(session_factory, game_id)).values())


async def test_stamp_zero_flaw_game(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    game_id = await make_game(flaw_plies=())
    assert await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="full_eval_drain"
    )
    assert await _stamp(session_factory, game_id) is not None


async def test_no_rating_flaw_null_game_stamped(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """White's rating is NULL: the white-to-move flaw is all-NULL (no_rating), Black's scores."""
    game_id = await make_game(flaw_plies=(2, 5), white_rating=None)
    score = score_game(await _inputs(session_factory, game_id), None)
    assert score.reasons["no_rating"] == 1
    assert await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )
    rows = await _flaw_rows(session_factory, game_id)
    assert _all_null(rows[2])
    assert not _all_null(rows[5])
    assert await _stamp(session_factory, game_id) is not None


async def test_mover_elo_pinned_from_board_turn(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-03: elo comes from the mover side of the pre-push board via pinned_elo_for_mover."""
    game_id = await make_game(flaw_plies=(2, 5))
    calls: list[tuple[str, float]] = []

    def _spy(fen: str, elo: float) -> dict[str, float]:
        calls.append((fen, elo))
        return fake_full_policy(fen, elo)

    monkeypatch.setattr(maia_flaw_scoring, "full_policy", _spy)
    assert await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )

    def _pinned(raw: int) -> float:
        return pinned_elo_for_mover(
            raw_rating=raw, platform="lichess", time_control_bucket="blitz", is_correspondence=False
        )

    # The pre-blunder (base) call of each flaw carries the Elo of the side to move on that board.
    # (The blunders' post-blunder calls, SEED-261114-iuv Part A, reuse the mover's Elo on the
    # opposite side to move, so they are looked up by the pre-blunder FEN.)
    replayed = _replayed(_PGN)
    by_fen = dict(calls)
    assert by_fen[replayed[2][0].fen()] == _pinned(_WHITE_RATING)
    assert by_fen[replayed[5][0].fen()] == _pinned(_BLACK_RATING)


# ---------------------------------------------------------------------------
# Write-path edges (D-01 precision, D-04, D-05 ordering, D-15 wiring)
# ---------------------------------------------------------------------------


async def test_real_precision_roundtrip(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    game_id = await make_game(flaw_plies=(2,))
    replayed = _replayed(_PGN)
    assert await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )
    stored = (await _flaw_rows(session_factory, game_id))[2]["maia_played_prob"]
    expected = _expected_played_prob(replayed, 2)
    assert stored is not None
    assert abs(stored - expected) <= _REAL_TOLERANCE


async def test_scorer_exception_leaves_unstamped(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-05 ordering: an exception anywhere in the pass leaves the game unstamped and its
    existing values untouched."""
    game_id = await make_game(stale_plies=(2, 5, 8))
    before = await _flaw_rows(session_factory, game_id)
    captured: list[int] = []

    def _boom(fen: str, elo: float) -> dict[str, float]:
        raise RuntimeError("inference blew up")

    monkeypatch.setattr(maia_flaw_scoring, "full_policy", _boom)
    monkeypatch.setattr(
        maia_flaw_scoring.sentry_sdk, "capture_exception", lambda *a, **kw: captured.append(1)
    )
    assert not await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )
    assert captured == [1], "the failure must reach Sentry exactly once"
    assert await _stamp(session_factory, game_id) is None
    assert await _flaw_rows(session_factory, game_id) == before


async def test_one_full_policy_call_per_flaw(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-04: one call per scorable flaw, zero for fen_mismatch / no_rating flaws.

    White has no rating, so plies 2 and 8 are no_rating; ply 7 (black) has a wrong stored
    fen; only ply 5 is scorable, and as an opponent blunder it adds its post-blunder call.
    """
    game_id = await make_game(
        flaw_plies=(2, 5, 7, 8), white_rating=None, fen_override={7: "8/8/8/8/8/8/8/8"}
    )
    calls: list[str] = []

    def _counting(fen: str, elo: float) -> dict[str, float]:
        calls.append(fen)
        return fake_full_policy(fen, elo)

    monkeypatch.setattr(maia_flaw_scoring, "full_policy", _counting)
    assert await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )
    assert len(calls) == 2


async def test_played_not_legal_row_all_null(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game_id = await make_game()
    replayed = _replayed(_PGN)
    bad_board, bad_played = replayed[5]

    def _omits_played(fen: str, elo: float) -> dict[str, float]:
        probs = fake_full_policy(fen, elo)
        if fen == bad_board.fen():
            probs.pop(bad_played)
        return probs

    monkeypatch.setattr(maia_flaw_scoring, "full_policy", _omits_played)
    score = score_game(await _inputs(session_factory, game_id), None)
    assert score.reasons["played_not_legal"] == 1
    assert await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )
    rows = await _flaw_rows(session_factory, game_id)
    assert _all_null(rows[5])
    assert not _all_null(rows[2]) and not _all_null(rows[8])
    assert await _stamp(session_factory, game_id) is not None


# ---------------------------------------------------------------------------
# Reminder (D-11)
# ---------------------------------------------------------------------------


def test_reminder_format() -> None:
    assert format_maia_backfill_reminder(0, "prod") is None
    line = format_maia_backfill_reminder(3, "prod")
    assert line is not None
    assert _BACKFILL_CMD_FRAGMENT in line
    assert "3" in line
    assert "—" not in line


# ---------------------------------------------------------------------------
# Reclassify without Maia (D-09): survivors keep values, new plies NULL, game unstamped
# ---------------------------------------------------------------------------

# White-perspective post-move evals for plies 0..8 of _PGN: white blunders at ply 2
# (20 -> -500) and black blunders at ply 5 (-480 -> 100). Classification therefore yields
# flaws at {2, 5}; the seeded rows sit at {2, 7} so 2 survives, 5 is new and 7 is stale.
_RECLASSIFY_EVALS: dict[int, int | None] = {
    0: 0,
    1: 20,
    2: -500,
    3: -490,
    4: -480,
    5: 100,
    6: 90,
    7: 80,
    8: 70,
}
_RECLASSIFY_SURVIVOR_PLY = 2
_RECLASSIFY_NEW_PLY = 5
_RECLASSIFY_STALE_PLY = 7
# Probabilities are exact binary fractions: the columns are REAL (float32), so decimal
# literals would not round-trip equal.
_PRIOR_MAIA: dict[str, Any] = {"maia_played_prob": 0.125}
_PRIOR_FACEPALM: dict[str, Any] = _STALE_FACEPALM
# What the fact-column reader sees of it.
_PRIOR_FACEPALM_FACTS: dict[str, Any] = {
    c: v for c, v in _STALE_FACEPALM.items() if c in FACEPALM_COLUMNS
}
# A real forcing blob (same shape the write-path golden scenarios use) so the survivor
# lands in the freshly-blobbed update bucket.
_FRESH_BLOB: list[dict[str, Any]] = [
    {"b": -800, "bm": None, "s": 0, "sm": None, "su": "b8c6"},
    {"b": 300, "bm": None, "s": 250, "sm": None, "su": "f1c4"},
    {"b": -800, "bm": None, "s": 0, "sm": None, "su": "f8c5"},
]


async def _seed_prior_maia_and_stamp(
    maker: async_sessionmaker[AsyncSession], game_id: int, plies: tuple[int, ...]
) -> None:
    """Give every listed flaw row non-NULL Maia and facepalm values; set all three stamps."""
    async with maker() as session:
        for ply in plies:
            await session.execute(
                sa.update(GameFlaw)
                .where(GameFlaw.game_id == game_id, GameFlaw.ply == ply)
                .values(**_PRIOR_MAIA, **_PRIOR_FACEPALM)
            )
        await session.execute(
            sa.update(Game)
            .where(Game.id == game_id)
            .values(**{column: sa.func.now() for column in _STAMP_COLUMNS})
        )
        await session.commit()


async def _reclassify(
    maker: async_sessionmaker[AsyncSession],
    game_id: int,
    flaw_pv_blobs: dict[int, tuple[list[Any], list[Any]]] | None = None,
) -> bool:
    async with maker() as session:
        unstamped = await _classify_and_fill_oracle(
            session, game_id, {}, flaw_pv_blobs=flaw_pv_blobs, blobs_pending=True
        )
        await session.commit()
    return unstamped


async def _assert_reclassify_outcome(
    maker: async_sessionmaker[AsyncSession], game_id: int, unstamped: bool
) -> None:
    rows = await _flaw_rows(maker, game_id)
    assert set(rows) == {_RECLASSIFY_SURVIVOR_PLY, _RECLASSIFY_NEW_PLY}, "stale ply must be gone"
    assert rows[_RECLASSIFY_SURVIVOR_PLY] == _PRIOR_MAIA, "survivor must keep its Maia values"
    assert _all_null(rows[_RECLASSIFY_NEW_PLY]), "a new flaw ply starts with NULL Maia values"
    facepalm = await _facepalm_rows(maker, game_id)
    assert facepalm[_RECLASSIFY_SURVIVOR_PLY] == _PRIOR_FACEPALM_FACTS, (
        "survivor keeps its facepalm values"
    )
    assert facepalm[_RECLASSIFY_NEW_PLY] == _ALL_NULL_FACEPALM, "a new flaw ply starts with NULLs"
    assert await _stamp(maker, game_id) is None
    assert all(stamp is None for stamp in (await _stamps(maker, game_id)).values()), (
        "all three stamps are cleared (250 D-05, D-11)"
    )
    assert unstamped is True


async def test_reclassify_without_maia_keeps_survivors_nulls_new_unstamps(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(maia_engine, "_session", None)
    game_id = await make_game(
        flaw_plies=(_RECLASSIFY_SURVIVOR_PLY, _RECLASSIFY_STALE_PLY), evals=_RECLASSIFY_EVALS
    )
    await _seed_prior_maia_and_stamp(
        session_factory, game_id, (_RECLASSIFY_SURVIVOR_PLY, _RECLASSIFY_STALE_PLY)
    )
    unstamped = await _reclassify(session_factory, game_id)
    await _assert_reclassify_outcome(session_factory, game_id, unstamped)


async def test_reclassify_freshly_blobbed_survivor_keeps_values(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(maia_engine, "_session", None)
    game_id = await make_game(
        flaw_plies=(_RECLASSIFY_SURVIVOR_PLY, _RECLASSIFY_STALE_PLY), evals=_RECLASSIFY_EVALS
    )
    await _seed_prior_maia_and_stamp(
        session_factory, game_id, (_RECLASSIFY_SURVIVOR_PLY, _RECLASSIFY_STALE_PLY)
    )
    unstamped = await _reclassify(
        session_factory, game_id, {_RECLASSIFY_SURVIVOR_PLY: (_FRESH_BLOB, [])}
    )
    await _assert_reclassify_outcome(session_factory, game_id, unstamped)
    async with session_factory() as session:
        blob = await session.scalar(
            select(GameFlaw.allowed_pv_lines).where(
                GameFlaw.game_id == game_id, GameFlaw.ply == _RECLASSIFY_SURVIVOR_PLY
            )
        )
    assert blob is not None, "the survivor must have gone through the freshly-blobbed bucket"


async def test_reclassify_not_analyzed_returns_false_keeps_stamp(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(maia_engine, "_session", None)
    game_id = await make_game(
        flaw_plies=(_RECLASSIFY_SURVIVOR_PLY,), evals={p: None for p in range(9)}
    )
    await _seed_prior_maia_and_stamp(session_factory, game_id, (_RECLASSIFY_SURVIVOR_PLY,))
    unstamped = await _reclassify(session_factory, game_id)
    assert unstamped is False
    assert all(stamp is not None for stamp in (await _stamps(session_factory, game_id)).values())
    rows = await _flaw_rows(session_factory, game_id)
    assert rows[_RECLASSIFY_SURVIVOR_PLY] == _PRIOR_MAIA
    facepalm = await _facepalm_rows(session_factory, game_id)
    assert facepalm[_RECLASSIFY_SURVIVOR_PLY] == _PRIOR_FACEPALM_FACTS


async def test_reclassify_unknown_game_returns_false(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    assert await _reclassify(session_factory, 2_000_000_000) is False


@pytest.mark.parametrize(
    "set_stamps",
    [
        pytest.param((), id="none"),
        *[pytest.param((column,), id=column) for column in _STAMP_COLUMNS],
        pytest.param(_STAMP_COLUMNS, id="all"),
    ],
)
async def test_reclassify_clear_helper_clears_all_five_stamps(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    set_stamps: tuple[str, ...],
) -> None:
    """D-08/D-22 + 250 D-05 + 254 D-08 + 259 D-11: one UPDATE clears all five stamps; True when ANY was set."""
    game_id = await make_game(flaw_plies=())
    async with session_factory() as session:
        await session.execute(
            sa.update(Game)
            .where(Game.id == game_id)
            .values(**{c: sa.func.now() if c in set_stamps else None for c in _STAMP_COLUMNS})
        )
        await session.commit()
    async with session_factory() as session:
        assert await clear_maia_flaws_completed(session, game_id) is bool(set_stamps)
        await session.commit()
    assert all(stamp is None for stamp in (await _stamps(session_factory, game_id)).values())


async def test_write_rejects_batch_mixing_full_and_spread_scores(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """Spread rows carry the facepalm keys only, full rows add the pre and reply keys: one executemany
    cannot take both."""
    full_game = await make_game()
    spread_game = await make_game()
    full = score_game(await _inputs(session_factory, full_game), None)
    spread = score_game(await _inputs(session_factory, spread_game), None, "spread")

    async with session_factory() as session:
        with pytest.raises(ValueError, match="mixing"):
            await write_game_maia_scores(session, [full, spread], require_unstamped=False)


# ---------------------------------------------------------------------------
# Best-line facts and the best-line fingerprint (Phase 254 D-09, T-254-05)
# ---------------------------------------------------------------------------

# A legal best line from the Scotch flaw position (white to move after 1. e4 e5 2. Nf3 Nc6):
# Nxe5 wins a pawn, Nxe5 recaptures the knight, then two quiet moves, so the line settles depths.
_SCOTCH_BEST_PV = "f3e5 c6e5 d2d4 e5g6 d4d5"
_SCOTCH_BEST_MOVE = "f3e5"


async def _best_line_user_blunder(
    make_game: MakeGame, *, best_pv: str | None = _SCOTCH_BEST_PV, **kwargs: Any
) -> tuple[int, str]:
    """The Scotch user blunder with a stored played line AND a best line at the flaw ply."""
    pv = _mainline_line(_SCOTCH_PGN, _SCOTCH_FLAW_PLY, _STORED_LINE_PLIES)
    game_id = await make_game(
        pgn=_SCOTCH_PGN,
        flaw_plies=(_SCOTCH_FLAW_PLY,),
        pv={_SCOTCH_FLAW_PLY + 1: pv, _SCOTCH_FLAW_PLY: best_pv}
        if best_pv
        else {_SCOTCH_FLAW_PLY + 1: pv},
        **kwargs,
    )
    return game_id, pv


async def _flaw_row_full(
    maker: async_sessionmaker[AsyncSession], game_id: int, ply: int
) -> GameFlaw:
    async with maker() as session:
        return (
            await session.execute(
                select(GameFlaw).where(GameFlaw.game_id == game_id, GameFlaw.ply == ply)
            )
        ).scalar_one()


async def test_full_mode_writes_both_line_arrays(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """D-09: the hook stores both signed 9-slot arrays and both mate plies."""
    game_id, pv = await _best_line_user_blunder(make_game)
    assert await _score(session_factory, game_id)
    pre, played = _replayed(_SCOTCH_PGN)[_SCOTCH_FLAW_PLY]
    played_facts = line_facts(pre, played, pv)
    best_facts = best_line_facts(pre, _SCOTCH_BEST_PV)
    assert any(v is not None for v in best_facts.material_array()), "the best line must settle"
    row = await _flaw_row_full(session_factory, game_id, _SCOTCH_FLAW_PLY)
    assert row.played_line_material == played_facts.material_array()
    assert row.best_line_material == best_facts.material_array()
    assert len(row.played_line_material or []) == 9
    assert len(row.best_line_material or []) == 9
    assert row.line_mate_ply == played_facts.mate_ply
    assert row.best_line_mate_ply == best_facts.opponent_mate_ply


async def test_full_mode_without_best_line_keeps_best_facts_null(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """No best pv and no best_move: the best arrays and mate ply stay NULL, the row is still scored."""
    game_id, _ = await _best_line_user_blunder(make_game, best_pv=None)
    assert await _score(session_factory, game_id)
    row = await _flaw_row_full(session_factory, game_id, _SCOTCH_FLAW_PLY)
    assert row.best_line_material is None
    assert row.best_line_mate_ply is None
    assert row.played_line_material is not None


@pytest.mark.parametrize("changed", ["pv", "best_move"])
async def test_fingerprint_includes_best_line(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, changed: str
) -> None:
    """T-254-05: a rewrite of the pv at the flaw ply (or the stored best move) between the read and
    the write is fingerprint_changed: nothing is written and no stamp is set."""
    game_id, _ = await _best_line_user_blunder(
        make_game, best_moves={_SCOTCH_FLAW_PLY: _SCOTCH_BEST_MOVE}
    )
    score = score_game(await _inputs(session_factory, game_id), None)
    new_value = "f3e5 c6e5" if changed == "pv" else "f1b5"
    async with session_factory() as session:
        await session.execute(
            sa.update(GamePosition)
            .where(GamePosition.game_id == game_id, GamePosition.ply == _SCOTCH_FLAW_PLY)
            .values(**{changed: new_value})
        )
        await session.commit()
    async with session_factory() as session:
        outcomes = await write_game_maia_scores(session, [score], require_unstamped=False)
        await session.commit()
    assert outcomes == {game_id: "fingerprint_changed"}
    row = await _flaw_row_full(session_factory, game_id, _SCOTCH_FLAW_PLY)
    assert row.best_line_material is None
    assert row.played_line_material is None
    assert all(stamp is None for stamp in (await _stamps(session_factory, game_id)).values())


async def test_in_memory_score_equals_expression(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """D-01: facepalm_expr(drill lambda) over the written facts equals the Python twin that feeds
    the backfill report's scored count; no score column is written."""
    game_id, _ = await _best_line_user_blunder(make_game)
    inputs = await _inputs(session_factory, game_id)
    score = score_game(inputs, None)
    assert score.scores_set == 1
    assert await _score(session_factory, game_id)
    async with session_factory() as session:
        from_expr = (
            await session.execute(
                select(facepalm_expr(FACEPALM_DRILL_LAMBDA)).where(GameFlaw.game_id == game_id)
            )
        ).scalar_one()
    assert from_expr is not None
    flaw = inputs.flaws[0]
    in_memory = maia_flaw_scoring._row_score(flaw, score.rows[0])
    assert in_memory == pytest.approx(from_expr, abs=_REAL_TOLERANCE)


def test_best_move_uci_fallback() -> None:
    """The first token of the best pv wins, else best_move, else None (254 Pitfall 7)."""
    assert best_move_uci("e2e4 e7e5", "d2d4") == "e2e4"
    assert best_move_uci(None, "d2d4") == "d2d4"
    assert best_move_uci("", "d2d4") == "d2d4"
    assert best_move_uci(None, None) is None
    assert best_move_uci("", "") is None


# ---------------------------------------------------------------------------
# Pre-blunder Maia inputs from the existing policy call (Phase 254 D-08)
# ---------------------------------------------------------------------------


async def test_full_mode_writes_pre_inputs(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """D-08: maia_best_prob and maia_pre_spread equal the fake policy values at the pre-blunder board."""
    game_id, _ = await _best_line_user_blunder(make_game)
    assert await _score(session_factory, game_id)
    pre, _played = _replayed(_SCOTCH_PGN)[_SCOTCH_FLAW_PLY]
    probs = fake_full_policy(pre.fen(), 0.0)
    row = await _flaw_row_full(session_factory, game_id, _SCOTCH_FLAW_PLY)
    assert row.maia_best_prob == pytest.approx(
        probs[best_move_uci(_SCOTCH_BEST_PV, None) or ""], rel=_REAL_RELATIVE_TOLERANCE
    )
    assert row.maia_pre_spread == pytest.approx(
        pre_blunder_spread(probs), rel=_REAL_RELATIVE_TOLERANCE
    )


async def test_pre_inputs_reuse_the_flaw_policy_call(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-08: the pre inputs come from the SAME full_policy call as maia_played_prob: one call at
    the flaw position plus one post-blunder call per scorable user blunder, as before this plan."""
    game_id, _ = await _best_line_user_blunder(make_game)
    calls = _recording_policy(monkeypatch)
    score = score_game(await _inputs(session_factory, game_id), None)
    pre, played = _replayed(_SCOTCH_PGN)[_SCOTCH_FLAW_PLY]
    post = pre.copy()
    post.push_uci(played)
    assert [fen for fen, _elo in calls] == [pre.fen(), post.fen()]
    assert score.rows[0]["maia_best_prob"] is not None
    assert score.rows[0]["maia_pre_spread"] is not None


async def test_best_move_missing_keeps_loss_only_score(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """No pv and no best_move at the flaw ply: best prob and best arrays NULL, reason counted, the
    pre spread is still stored. The Scotch blunder loses no material, so under best_prob_for_misses
    the row is unscored without a best-move probability (254 WR-01 / 256 D-04)."""
    game_id, _ = await _best_line_user_blunder(make_game, best_pv=None)
    score = score_game(await _inputs(session_factory, game_id), None)
    assert score.reasons["best_move_missing"] == 1
    row = score.rows[0]
    assert row["maia_best_prob"] is None
    assert row["maia_pre_spread"] is not None
    assert row["best_line_material"] is None
    assert row["best_line_mate_ply"] is None
    assert score.scores_set == 0


async def test_best_move_outside_the_policy_counts_best_move_missing(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """A stored best move the policy does not contain (not legal here) leaves best prob NULL."""
    game_id, _ = await _best_line_user_blunder(make_game, best_pv=None)
    async with session_factory() as session:
        await session.execute(
            sa.update(GamePosition)
            .where(GamePosition.game_id == game_id, GamePosition.ply == _SCOTCH_FLAW_PLY)
            .values(best_move="a1a8")
        )
        await session.commit()
    score = score_game(await _inputs(session_factory, game_id), None)
    assert score.reasons["best_move_missing"] == 1
    assert score.rows[0]["maia_best_prob"] is None


async def test_full_mode_sets_pre_stamp_with_the_others(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """D-08: full mode stamps facepalm_pre_completed_at together with the other stamps."""
    game_id, _ = await _best_line_user_blunder(make_game)
    assert await _score(session_factory, game_id)
    stamps = await _stamps(session_factory, game_id)
    assert set(stamps) == set(_STAMP_COLUMNS)
    assert stamps["facepalm_pre_completed_at"] is not None
    assert all(stamp is not None for stamp in stamps.values())


async def test_clear_maia_flaws_completed_clears_pre_stamp(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """The pre stamp alone counts as 'was stamped' and is cleared with the other three."""
    game_id = await make_game(flaw_plies=())
    async with session_factory() as session:
        await session.execute(
            sa.update(Game)
            .where(Game.id == game_id)
            .values(facepalm_pre_completed_at=sa.func.now())
        )
        await session.commit()
    async with session_factory() as session:
        assert await clear_maia_flaws_completed(session, game_id) is True
        await session.commit()
    assert (await _stamps(session_factory, game_id))["facepalm_pre_completed_at"] is None


async def test_spread_and_line_rows_never_carry_pre_inputs(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """Spread and line modes write FACEPALM_COLUMNS only: the pre keys belong to full mode."""
    game_id, _ = await _best_line_user_blunder(make_game)
    await _store_base_values(
        session_factory,
        game_id,
        _SCOTCH_FLAW_PLY,
        maia_played_prob=_STORED_PLAYED_PROB,
        maia_best_prob=_STORED_BEST_PROB,
    )
    inputs = await _inputs(session_factory, game_id)
    for mode in ("spread", "line"):
        row = score_game(inputs, None, mode).rows[0]
        assert "maia_best_prob" not in row, mode
        assert "maia_pre_spread" not in row, mode
        assert row["best_line_material"] is not None, mode


# ---------------------------------------------------------------------------
# Opponent blunders (SEED-261114-iuv Part A): the three Maia columns and, since step 4, line facts
# ---------------------------------------------------------------------------

# Ply 5 of _PGN is Black's a7a6 at the Ruy Lopez decision position; g8f6 is legal there.
_OPPONENT_PLY = 5
_OPPONENT_BEST_MOVE = "g8f6"


async def _opponent_game(make_game: MakeGame, **kwargs: Any) -> int:
    """White user, flaws 2, 5 and 8 of _PGN, stored lines after plies 2 and 5 and g8f6 as the best
    line at ply 5, stale facepalm values seeded on the opponent's ply 5."""
    lines = {3: _mainline_line(_PGN, 2, 6), 6: _mainline_line(_PGN, 5, 3)}
    lines[_OPPONENT_PLY] = _OPPONENT_BEST_MOVE
    return await make_game(pv=lines, **kwargs)


async def _seed_stale_facepalm(
    maker: async_sessionmaker[AsyncSession], game_id: int, ply: int
) -> None:
    await _store_base_values(maker, game_id, ply, **_STALE_FACEPALM)


async def test_full_mode_opponent_blunder_gets_three_maia_columns_and_line_facts(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """Stored lines and stale values are present: the opponent row gets the spread, the best
    probability and the pre spread, and its four line facts are freshly derived from the stored
    lines (the same derivation as a user blunder), replacing the stale values."""
    game_id = await _opponent_game(make_game)
    await _seed_stale_facepalm(session_factory, game_id, _OPPONENT_PLY)
    assert await _score(session_factory, game_id)
    row = await _flaw_row_full(session_factory, game_id, _OPPONENT_PLY)
    pre, played = _replayed(_PGN)[_OPPONENT_PLY]
    post = pre.copy()
    post.push_uci(played)
    pre_policy = fake_full_policy(pre.fen(), 0.0)
    assert row.maia_played_prob is not None
    assert row.maia_reply_spread == pytest.approx(
        reply_spread(fake_full_policy(post.fen(), 0.0)), rel=_REAL_RELATIVE_TOLERANCE
    )
    assert row.maia_pre_spread == pytest.approx(
        pre_blunder_spread(pre_policy), rel=_REAL_RELATIVE_TOLERANCE
    )
    assert row.maia_best_prob == pytest.approx(
        pre_policy[_OPPONENT_BEST_MOVE], rel=_REAL_RELATIVE_TOLERANCE
    )
    expected = _expected_line_facts(
        _PGN, _OPPONENT_PLY, _mainline_line(_PGN, _OPPONENT_PLY, 3), _OPPONENT_BEST_MOVE
    )
    assert any(v is not None for v in expected.values()), "the fixture lines must settle a fact"
    assert {column: getattr(row, column) for column in _LINE_FACT_COLUMNS} == expected
    assert row.played_line_material != _STALE_FACEPALM["played_line_material"]
    assert all(stamp is not None for stamp in (await _stamps(session_factory, game_id)).values())


# A legal best line at each tracer decision position: white's Nf3 / Bc4-style alternatives from the
# ply-2 position (white to move after 1. e4 e5) and Black's Nf6 line from the ply-5 position.
_TRACER_USER_PLY = 2
_TRACER_USER_BEST_PV = "g1f3 b8c6 f1b5"
_TRACER_OPPONENT_BEST_PV = "g8f6 e1g1 f6e4"


async def test_full_mode_writes_material_inputs_and_reply_prob_for_both_sides(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """259 D-05, D-07, D-10 tracer: one user blunder and one opponent blunder, each with a refutation
    line and a best line, are scored and written through the hook. Both rows carry the stored
    scalars (equal to `facepalm_material_inputs` on the same board and lines) and the best-reply
    probability (the fake policy's value of the first refutation token on the post-blunder board),
    next to the unchanged arrays."""
    refutations = {
        _TRACER_USER_PLY + 1: _mainline_line(_PGN, _TRACER_USER_PLY, 6),
        _OPPONENT_PLY + 1: _mainline_line(_PGN, _OPPONENT_PLY, 3),
    }
    best_lines = {_TRACER_USER_PLY: _TRACER_USER_BEST_PV, _OPPONENT_PLY: _TRACER_OPPONENT_BEST_PV}
    game_id = await make_game(
        flaw_plies=(_TRACER_USER_PLY, _OPPONENT_PLY), pv={**refutations, **best_lines}
    )
    assert await _score(session_factory, game_id)
    replayed = _replayed(_PGN)
    for ply in (_TRACER_USER_PLY, _OPPONENT_PLY):
        row = await _flaw_row_full(session_factory, game_id, ply)
        pre, played = replayed[ply]
        refutation, best = refutations[ply + 1], best_lines[ply]
        expected = facepalm_material_inputs(pre, played, refutation, best)
        assert expected.loss is not None, "the fixture line must settle"
        assert row.material_loss == pytest.approx(expected.loss, rel=_REAL_RELATIVE_TOLERANCE)
        assert row.material_missed == pytest.approx(expected.missed, rel=_REAL_RELATIVE_TOLERANCE)
        post = pre.copy()
        post.push_uci(played)
        reply_policy = fake_full_policy(post.fen(), 0.0)
        assert row.maia_best_reply_prob == pytest.approx(
            reply_policy[refutation.split(" ")[0]], rel=_REAL_RELATIVE_TOLERANCE
        )
        # The arrays are exactly what the live score reads today (D-11).
        assert row.played_line_material == line_facts(pre, played, refutation).material_array() or (
            row.played_line_material is None
        )
        assert row.best_line_material == best_line_facts(pre, best).material_array() or (
            row.best_line_material is None
        )


async def test_full_mode_opponent_blunder_without_rating_keeps_line_facts_only(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """Mirror of the user-side no-rating test: the opponent mover (Black) has no rating, so the
    spread and the pre keys stay NULL but the line facts come from the board and the stored lines."""
    game_id = await _opponent_game(make_game, black_rating=None)
    assert await _score(session_factory, game_id)
    row = await _flaw_row_full(session_factory, game_id, _OPPONENT_PLY)
    expected = _expected_line_facts(
        _PGN, _OPPONENT_PLY, _mainline_line(_PGN, _OPPONENT_PLY, 3), _OPPONENT_BEST_MOVE
    )
    assert any(v is not None for v in expected.values())
    assert {column: getattr(row, column) for column in _LINE_FACT_COLUMNS} == expected
    assert row.maia_reply_spread is None
    assert row.maia_best_prob is None
    assert row.maia_pre_spread is None
    inputs_score = score_game(await _inputs(session_factory, game_id), None)
    assert inputs_score.reasons["no_rating"] >= 1


async def test_full_mode_opponent_blunder_with_unrebuildable_board_is_all_null(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """A fen that does not match the replayed board: no facts of any kind, stale values cleared."""
    game_id = await _opponent_game(
        make_game, fen_override={_OPPONENT_PLY: "8/8/8/8/8/8/8/8"}, stale_plies=(_OPPONENT_PLY,)
    )
    await _seed_stale_facepalm(session_factory, game_id, _OPPONENT_PLY)
    assert await _score(session_factory, game_id)
    row = await _flaw_row_full(session_factory, game_id, _OPPONENT_PLY)
    for column in (*FACEPALM_COLUMNS, *FACEPALM_PRE_COLUMNS):
        assert getattr(row, column) is None, column


async def test_full_mode_opponent_calls_use_the_opponents_elo(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The two calls for the opponent's ply 5 are (pre board, Black's pinned Elo) and (post board,
    Black's pinned Elo): never the user's (White's) Elo."""
    game_id = await make_game(flaw_plies=(_OPPONENT_PLY,))
    calls = _recording_policy(monkeypatch)
    assert await _score(session_factory, game_id)
    pre, played = _replayed(_PGN)[_OPPONENT_PLY]
    post = pre.copy()
    post.push_uci(played)
    black = _pinned_elo(_BLACK_RATING)
    assert black != _pinned_elo(_WHITE_RATING)
    assert calls == [(pre.fen(), black), (post.fen(), black)]


@pytest.mark.parametrize(
    ("user_color", "flaw_plies", "mistake_plies"),
    [
        ("white", (2, 4, 5), (4, 5)),  # user mistake (ply 4), opponent mistake (ply 5)
        ("black", (3, 4, 5), (4, 5)),  # opponent mistake (ply 4), user mistake (ply 5)
    ],
)
async def test_full_mode_mistakes_stay_null_for_both_sides(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
    user_color: Literal["white", "black"],
    flaw_plies: tuple[int, ...],
    mistake_plies: tuple[int, ...],
) -> None:
    """Mistakes of either side carry none of the three Maia columns and none of the line facts,
    and spend no post-blunder inference."""
    game_id = await make_game(
        flaw_plies=flaw_plies,
        user_color=user_color,
        severities=dict.fromkeys(mistake_plies, 1),
    )
    calls = _recording_policy(monkeypatch)
    assert await _score(session_factory, game_id)
    for ply in mistake_plies:
        row = await _flaw_row_full(session_factory, game_id, ply)
        for column in (*FACEPALM_COLUMNS, *FACEPALM_PRE_COLUMNS):
            assert getattr(row, column) is None, (ply, column)
    # Base calls for the three flaws plus one post-blunder call for the single blunder.
    assert len(calls) == len(flaw_plies) + 1


async def test_full_mode_user_output_unchanged_by_opponent_blunders(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """With and without the opponent flaw: identical user rows and user counters; the opponent
    counters only move when the opponent blunder is present."""
    game_id = await _opponent_game(make_game)
    inputs = await _inputs(session_factory, game_id)
    without = dataclasses.replace(
        inputs, flaws=tuple(f for f in inputs.flaws if f.ply != _OPPONENT_PLY)
    )
    with_opponent = score_game(inputs, None)
    user_only = score_game(without, None)
    user_rows = lambda score: [r for r in score.rows if r["ply"] != _OPPONENT_PLY]  # noqa: E731
    assert user_rows(with_opponent) == user_rows(user_only)
    assert len(user_rows(user_only)) == 2
    for counter in ("user_blunders", "spreads_scored", "scores_set", "pre_scored"):
        assert getattr(with_opponent, counter) == getattr(user_only, counter), counter
    assert user_only.user_blunders == 2
    assert (
        user_only.opponent_blunders,
        user_only.opponent_spreads_scored,
        user_only.opponent_pre_scored,
        user_only.opponent_scores_set,
    ) == (0, 0, 0, 0)
    opponent_row = next(r for r in with_opponent.rows if r["ply"] == _OPPONENT_PLY)
    opponent_flaw = next(f for f in inputs.flaws if f.ply == _OPPONENT_PLY)
    in_memory = maia_flaw_scoring._row_score(opponent_flaw, opponent_row)
    assert in_memory is not None, "the opponent fixture row must score in memory"
    assert (
        with_opponent.opponent_blunders,
        with_opponent.opponent_spreads_scored,
        with_opponent.opponent_pre_scored,
        with_opponent.opponent_scores_set,
    ) == (1, 1, 1, 1)


async def test_facepalm_expr_scores_opponent_row_and_gated_reader_still_omits_it(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """End to end: full-mode scoring (no hand-seeded facts) leaves the opponent row with facts that
    score in SQL, while the owner-side gate of `fetch_page_facepalm_scores` still omits it."""
    game_id = await _opponent_game(make_game)
    await _seed_stale_facepalm(session_factory, game_id, _OPPONENT_PLY)
    assert await _score(session_factory, game_id)
    row = await _flaw_row_full(session_factory, game_id, _OPPONENT_PLY)
    # The fixture line must settle the depth-3 slot, or the row stays unscored by construction.
    assert row.played_line_material is not None
    assert row.played_line_material[2] is not None, "the line must settle the depth-3 slot first"

    async def _expr_by_ply(lam: float) -> dict[int, float | None]:
        async with session_factory() as session:
            rows = (
                await session.execute(
                    select(GameFlaw.ply, facepalm_expr(lam)).where(GameFlaw.game_id == game_id)
                )
            ).all()
        return {ply: value for ply, value in rows}

    drill = await _expr_by_ply(FACEPALM_DRILL_LAMBDA)
    library = await _expr_by_ply(FACEPALM_LIBRARY_LAMBDA)
    async with session_factory() as session:
        markers = await fetch_page_facepalm_scores(session, _TEST_USER_ID, [game_id])
    assert drill[_OPPONENT_PLY] is not None
    assert library[_OPPONENT_PLY] is not None
    # White user: ply 5 is Black's move, the opponent's. The owner-side reader omits it.
    assert _OPPONENT_PLY not in markers.get(game_id, {})
    scored_user_plies = {ply for ply, value in library.items() if value is not None}
    assert set(markers.get(game_id, {})) == scored_user_plies - {_OPPONENT_PLY}


# ---------------------------------------------------------------------------
# Opponent mode (SEED-261114-iuv Part A): row-selected, three Maia columns, no stamp
# ---------------------------------------------------------------------------

_OPPONENT_ROW_KEYS = _PK_KEYS | set(maia_flaw_scoring.OPPONENT_ROW_COLUMNS)


async def _opponent_mode_game(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> int:
    """White user, _PGN. Ply 1: opponent blunder without a stored played prob. Ply 2: user blunder
    (stored prob). Ply 3: opponent blunder with a stored prob AND a stored spread. Ply 5: the one
    target (stored prob, NULL spread, best pv g8f6). Ply 7: opponent mistake (stored prob)."""
    game_id = await make_game(
        flaw_plies=(1, 2, 3, 5, 7), severities={7: 1}, pv={_OPPONENT_PLY: _OPPONENT_BEST_MOVE}
    )
    for ply in (2, 5, 7):
        await _store_base_values(
            session_factory, game_id, ply, maia_played_prob=_STORED_PLAYED_PROB
        )
    await _store_base_values(
        session_factory,
        game_id,
        3,
        maia_played_prob=_STORED_PLAYED_PROB,
        maia_reply_spread=_STORED_SPREAD,
    )
    return game_id


async def test_opponent_mode_scores_only_the_pending_opponent_blunder(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game_id = await _opponent_mode_game(session_factory, make_game)
    inputs = await _inputs(session_factory, game_id)
    # Full-mode row of the same ply, for the equality check (computed before recording starts).
    full_row = next(r for r in score_game(inputs, None).rows if r["ply"] == _OPPONENT_PLY)
    calls = _recording_policy(monkeypatch)

    score = score_game(inputs, None, "opponent")

    assert score.mode == "opponent"
    assert [row["ply"] for row in score.rows] == [_OPPONENT_PLY]
    row = score.rows[0]
    assert set(row) == _OPPONENT_ROW_KEYS
    pre, played = _replayed(_PGN)[_OPPONENT_PLY]
    post = pre.copy()
    post.push_uci(played)
    black = _pinned_elo(_BLACK_RATING)
    assert calls == [(pre.fen(), black), (post.fen(), black)]
    for column in maia_flaw_scoring.OPPONENT_ROW_COLUMNS:
        assert row[column] is not None, column
        assert row[column] == full_row[column], column
    assert (score.opponent_blunders, score.opponent_spreads_scored, score.opponent_pre_scored) == (
        1,
        1,
        1,
    )
    assert (score.user_blunders, score.spreads_scored, score.scores_set, score.pre_scored) == (
        0,
        0,
        0,
        0,
    )


async def test_opponent_mode_stalemating_blunder_is_a_residue(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """White's stalemating Qe6 (ply 18) is the black user's opponent's blunder: no legal reply, so
    the spread stays NULL with its reason, the pre spread is set, one inference is spent."""
    game_id = await make_game(pgn=_STALEMATE_PGN, flaw_plies=(_STALEMATE_PLY,), user_color="black")
    await _store_base_values(
        session_factory, game_id, _STALEMATE_PLY, maia_played_prob=_STORED_PLAYED_PROB
    )
    calls = _recording_policy(monkeypatch)

    score = score_game(await _inputs(session_factory, game_id), None, "opponent")

    assert len(score.rows) == 1
    row = score.rows[0]
    assert row["maia_reply_spread"] is None
    assert row["maia_pre_spread"] is not None
    assert score.reasons["no_legal_reply"] == 1
    assert len(calls) == 1
    assert (score.opponent_blunders, score.opponent_spreads_scored) == (1, 0)


async def test_opponent_mode_user_only_blunders_yield_nothing(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game_id = await make_game(flaw_plies=(2, 8))
    for ply in (2, 8):
        await _store_base_values(
            session_factory, game_id, ply, maia_played_prob=_STORED_PLAYED_PROB
        )
    calls = _recording_policy(monkeypatch)

    score = score_game(await _inputs(session_factory, game_id), None, "opponent")

    assert score.rows == []
    assert calls == []


async def test_opponent_mode_write_sets_no_stamp_and_never_gates(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """The write reports "stamped" (rows written) with require_unstamped=True, sets none of the
    four stamps, leaves maia_played_prob alone, and a second write of the same score succeeds."""
    game_id = await _opponent_mode_game(session_factory, make_game)
    score = score_game(await _inputs(session_factory, game_id), None, "opponent")

    for _ in range(2):
        async with session_factory() as session:
            outcomes = await write_game_maia_scores(session, [score], require_unstamped=True)
            await session.commit()
        assert outcomes == {game_id: "stamped"}

    assert all(stamp is None for stamp in (await _stamps(session_factory, game_id)).values())
    row = await _flaw_row_full(session_factory, game_id, _OPPONENT_PLY)
    assert row.maia_played_prob == pytest.approx(_STORED_PLAYED_PROB)
    assert None not in (row.maia_reply_spread, row.maia_best_prob, row.maia_pre_spread)
    for column in _LINE_FACT_COLUMNS:
        assert getattr(row, column) is None, column


# ---------------------------------------------------------------------------
# Phase 259 R1: the key set of every mode, Pitfall 4 and behaviour neutrality
# ---------------------------------------------------------------------------

# Exact binary fraction: the REAL column round-trips equal.
_STORED_REPLY_PROB = 0.25


async def test_full_mode_rows_carry_the_full_key_set_and_mistakes_all_none(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """A full-mode row carries the PK plus the base key, FACEPALM_COLUMNS (with the two scalars),
    FACEPALM_PRE_COLUMNS and FACEPALM_REPLY_COLUMNS; a mistake row carries them all as None."""
    game_id = await make_game(severities={5: 1})
    score = score_game(await _inputs(session_factory, game_id), None)
    rows = {row["ply"]: row for row in score.rows}
    for row in rows.values():
        assert set(row) == _PK_KEYS | set(maia_flaw_scoring.FULL_ROW_COLUMNS)
    assert "material_loss" in rows[2]
    assert "maia_best_reply_prob" in rows[2]
    mistake = rows[5]
    for column in (*FACEPALM_COLUMNS, *FACEPALM_PRE_COLUMNS, *FACEPALM_REPLY_COLUMNS):
        assert mistake[column] is None, column


async def test_line_mode_rows_never_carry_the_reply_prob(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """Pitfall 4: line mode writes FACEPALM_COLUMNS minus the spread (so the two scalars) and
    never the reply probability, which it cannot compute without Maia."""
    game_id, _ = await _best_line_user_blunder(make_game)
    row = score_game(await _inputs(session_factory, game_id), None, "line").rows[0]
    assert set(row) == _PK_KEYS | set(maia_flaw_scoring.LINE_ROW_COLUMNS)
    assert "material_loss" in row
    assert "material_missed" in row
    assert "maia_best_reply_prob" not in row
    assert "maia_best_reply_prob" not in maia_flaw_scoring.LINE_ROW_COLUMNS
    assert "maia_best_reply_prob" not in FACEPALM_COLUMNS


async def test_line_mode_preserves_a_stored_reply_prob(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """T-259-07: a line pass over a row that already has a reply probability leaves it unchanged
    in the database while it refreshes the scalars."""
    game_id, _ = await _best_line_user_blunder(make_game)
    await _store_base_values(
        session_factory, game_id, _SCOTCH_FLAW_PLY, maia_best_reply_prob=_STORED_REPLY_PROB
    )
    outcomes = await _write_line_scores(
        session_factory,
        game_id,
        require_unstamped=False,
        line_cutoff=datetime(2026, 11, 10, tzinfo=timezone.utc),
    )
    assert outcomes == {game_id: "stamped"}
    row = await _flaw_row_full(session_factory, game_id, _SCOTCH_FLAW_PLY)
    assert row.maia_best_reply_prob == _STORED_REPLY_PROB
    assert row.material_loss is not None


async def test_reply_missing_without_a_refutation_line(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """A blunder with no stored refutation line gets maia_best_reply_prob None and the reason
    reply_missing in full mode, while its spread is still computed."""
    game_id, _ = await _scotch_user_blunder(make_game, with_line=False)
    score = score_game(await _inputs(session_factory, game_id), None)
    row = score.rows[0]
    assert row["maia_best_reply_prob"] is None
    assert row["maia_reply_spread"] is not None
    assert score.reasons["reply_missing"] == 1


async def test_reply_prob_is_none_when_the_token_is_not_in_the_policy(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """A first refutation token that is not a legal reply is absent from Maia's policy: NULL plus
    reply_missing, not an exception."""
    game_id = await make_game(
        pgn=_SCOTCH_PGN,
        flaw_plies=(_SCOTCH_FLAW_PLY,),
        pv={_SCOTCH_FLAW_PLY + 1: "a1a2"},
    )
    score = score_game(await _inputs(session_factory, game_id), None)
    assert score.rows[0]["maia_best_reply_prob"] is None
    assert score.reasons["reply_missing"] == 1


async def test_spread_and_opponent_key_sets_unchanged(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """Spread rows carry PK + FACEPALM_COLUMNS, opponent rows PK + OPPONENT_ROW_COLUMNS and pre rows
    PK + FACEPALM_PRE_COLUMNS: none of them gains the reply key."""
    game_id = await _opponent_mode_game(session_factory, make_game)
    inputs = await _inputs(session_factory, game_id)
    spread_rows = score_game(inputs, None, "spread").rows
    assert spread_rows
    for row in spread_rows:
        assert set(row) == _PK_KEYS | set(FACEPALM_COLUMNS)
    opponent_rows = score_game(inputs, None, "opponent").rows
    assert opponent_rows
    for row in opponent_rows:
        assert set(row) == _PK_KEYS | set(maia_flaw_scoring.OPPONENT_ROW_COLUMNS)
    pre_rows = score_game(inputs, None, "pre").rows
    assert pre_rows
    for row in pre_rows:
        assert set(row) == _PK_KEYS | set(FACEPALM_PRE_COLUMNS)
    for row in (*spread_rows, *opponent_rows, *pre_rows):
        assert "maia_best_reply_prob" not in row


def test_r1_score_expressions_read_no_new_column() -> None:
    """D-11: the R1 release stays behaviour-neutral, so the live score and type expressions compile
    to SQL that reads none of the three new columns."""
    for expression in (facepalm_expr(FACEPALM_DRILL_LAMBDA), facepalm_type_expr()):
        compiled = str(expression.compile(dialect=postgresql.dialect())).lower()
        for column in ("material_loss", "material_missed", "maia_best_reply_prob"):
            assert column not in compiled, column


async def test_full_mode_sets_the_reply_stamp(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """259 D-11: a full-mode pass sets the reply stamp together with the other four."""
    game_id, _ = await _best_line_user_blunder(make_game)
    assert await _score(session_factory, game_id)
    stamps = await _stamps(session_factory, game_id)
    assert stamps["facepalm_reply_completed_at"] is not None
    assert all(stamp is not None for stamp in stamps.values())


async def test_reply_mode_sets_only_the_reply_stamp_and_no_other_mode_sets_it(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """259 D-11: reply mode stamps only the reply stamp; spread, line, pre and opponent never do."""
    for mode in ("spread", "line", "pre", "opponent"):
        game_id, _ = await _scotch_user_blunder(make_game)
        score = score_game(await _inputs(session_factory, game_id), None, mode)
        async with session_factory() as session:
            await write_game_maia_scores(session, [score], require_unstamped=False)
            await session.commit()
        stamps = await _stamps(session_factory, game_id)
        assert stamps["facepalm_reply_completed_at"] is None, mode

    game_id, _ = await _scotch_user_blunder(make_game)
    await _store_base_values(
        session_factory, game_id, _SCOTCH_FLAW_PLY, maia_played_prob=_STORED_PLAYED_PROB
    )
    score = score_game(await _inputs(session_factory, game_id), None, "reply")
    async with session_factory() as session:
        outcomes = await write_game_maia_scores(session, [score], require_unstamped=True)
        await session.commit()
    assert outcomes == {game_id: "stamped"}
    stamps = await _stamps(session_factory, game_id)
    assert stamps["facepalm_reply_completed_at"] is not None
    assert all(
        stamp is None for column, stamp in stamps.items() if column != "facepalm_reply_completed_at"
    )


async def test_clear_helper_clears_five_stamps(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """259 D-11: the reply stamp alone counts as 'was stamped' and is cleared with the other four,
    so a reclassified game is re-scored by every pass."""
    game_id = await make_game(flaw_plies=())
    async with session_factory() as session:
        await session.execute(
            sa.update(Game)
            .where(Game.id == game_id)
            .values(facepalm_reply_completed_at=sa.func.now())
        )
        await session.commit()
    async with session_factory() as session:
        assert await clear_maia_flaws_completed(session, game_id) is True
        await session.commit()
    assert all(stamp is None for stamp in (await _stamps(session_factory, game_id)).values())
