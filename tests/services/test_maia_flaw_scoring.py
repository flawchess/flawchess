"""Tests for app/services/maia_flaw_scoring.py (Phase 247 plan 02, D-01 .. D-13).

DB-backed: games are committed through a session maker bound to the per-run test DB
(the scorer opens its own short sessions), and every game is deleted in teardown so the
global tier-3 eval lottery never sees a leaked non-guest game. Maia inference is faked
by patching ``maia_flaw_scoring.full_policy`` with ``fake_full_policy`` and presenting a
Maia session via ``maia_engine._session = object()``.
"""

from __future__ import annotations

import io
import uuid
from collections import Counter
from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Any, Literal

import chess
import chess.pgn
import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.user import User
from app.repositories.game_flaws_repository import (
    MAIA_FLAW_COLUMNS,
    MAIA_REFUTATION_COLUMNS,
    clear_maia_flaws_completed,
)
from app.services.eval_apply import _classify_and_fill_oracle
from app.services import maia_engine, maia_flaw_scoring
from app.services.best_move_candidates import pinned_elo_for_mover
from app.services.maia_flaw_scoring import (
    format_maia_backfill_reminder,
    load_game_maia_inputs,
    replay_flaw_boards,
    score_game,
    score_game_flaws_after_apply,
    write_game_maia_scores,
)
from app.services.maia_flaw_stats import MaiaReason
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

_WHITE_RATING = 1500
_BLACK_RATING = 1600

# Default flaw plies: white Nf3, black a6, white O-O (castling rights intact before it).
_FLAW_PLIES: tuple[int, ...] = (2, 5, 8)
# Legal stand-ins for Stockfish's best / second-best move at each flaw ply.
_BEST: dict[int, str] = {2: "d2d4", 5: "g8f6", 8: "d2d3", 4: "e5d6"}
_SECOND: dict[int, str] = {2: "b1c3", 5: "d7d6", 8: "c2c3", 4: "b1c3"}

_STALE_PROB = 0.999
_STALE_RANK = 7
_STALE_EFFECTIVE = 123.0
_REAL_TOLERANCE = 1e-6

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
        best: dict[int, str | None] | None = None,
        missed_pv: dict[int, list[Any]] | None = None,
        stale_plies: tuple[int, ...] = (),
        evals: dict[int, int | None] | None = None,
        user_color: str = "white",
        severities: dict[int, int] | None = None,
        pv: dict[int, str] | None = None,
    ) -> int:
        replayed = _replayed(pgn)
        best_by_ply = {**_BEST, **(best or {})}
        pv_by_ply = (
            missed_pv
            if missed_pv is not None
            else {p: [{"su": _SECOND[p]}] for p in flaw_plies if p in _SECOND}
        )
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
                        best_move=best_by_ply.get(ply),
                        pv=(pv or {}).get(ply),
                    )
                )
            await session.flush()
            for ply in flaw_plies:
                kwargs: dict[str, Any] = {}
                if ply in pv_by_ply:
                    kwargs["missed_pv_lines"] = pv_by_ply[ply]
                if ply in stale_plies:
                    kwargs.update(
                        maia_played_prob=_STALE_PROB,
                        maia_played_rank=_STALE_RANK,
                        maia_top_prob=_STALE_PROB,
                        maia_effective_moves=_STALE_EFFECTIVE,
                    )
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


async def _refutation_rows(
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
        ).scalar_one_or_none()


def _expected_refutation(
    replayed: dict[int, tuple[chess.Board, str]], ply: int, refutation_uci: str
) -> tuple[float, int]:
    """Independent (prob, rank) for the reply after the move played at `ply`."""
    pre, played = replayed[ply]
    post = pre.copy()
    post.push_uci(played)
    probs = fake_full_policy(post.fen(), 0.0)
    own = probs[refutation_uci]
    return own, 1 + sum(1 for p in probs.values() if p > own)


async def _inputs(maker: async_sessionmaker[AsyncSession], game_id: int) -> Any:
    async with maker() as session:
        return (await load_game_maia_inputs(session, [game_id]))[game_id]


def _all_null(row: dict[str, Any]) -> bool:
    return all(row[c] is None for c in MAIA_FLAW_COLUMNS)


def _expected_played_prob(replayed: dict[int, tuple[chess.Board, str]], ply: int) -> float:
    board, played = replayed[ply]
    return fake_full_policy(board.fen(), 0.0)[played]


# ---------------------------------------------------------------------------
# Schema (D-01, D-02, D-07)
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
        "maia_refutation_prob": "real",
        "maia_refutation_rank": "smallint",
        "maia_played_prob": "real",
        "maia_played_rank": "smallint",
        "maia_best_prob": "real",
        "maia_best_rank": "smallint",
        "maia_second_prob": "real",
        "maia_second_rank": "smallint",
        "maia_top_prob": "real",
        "maia_effective_moves": "real",
    }
    flaw_cols = {name for (table, name) in by_name if table == "game_flaws"}
    assert flaw_cols == set(expected_types), "eight D-01 columns plus the two refutation columns"
    for name, data_type in expected_types.items():
        row = by_name[("game_flaws", name)]
        assert row[2] == data_type
        assert row[3] == "YES"
        assert row[4] is None
    game_cols = sorted(c for (t, c) in by_name if t == "games")
    assert game_cols == ["maia_flaws_completed_at", "maia_refutation_completed_at"]
    for stamp_name in game_cols:
        stamp = by_name[("games", stamp_name)]
        assert stamp[2] == "timestamp with time zone"
        assert stamp[3] == "YES"
        assert stamp[4] is None


# ---------------------------------------------------------------------------
# Refutation (Phase 248)
# ---------------------------------------------------------------------------

# Black's legal reply to the post-Nf3 board (white user's ply-2 blunder).
_REPLY_AFTER_NF3 = "b8c6"


async def test_refutation_tracer_user_blunder_scored_and_both_stamps(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """One user-side blunder end to end: pair written, opponent blunder NULL, both stamps."""
    game_id = await make_game(flaw_plies=(2, 5), best={3: _REPLY_AFTER_NF3})
    replayed = _replayed(_PGN)
    assert await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )
    rows = await _refutation_rows(session_factory, game_id)
    prob, rank = _expected_refutation(replayed, 2, _REPLY_AFTER_NF3)
    assert rows[2]["maia_refutation_prob"] == pytest.approx(prob, abs=_REAL_TOLERANCE)
    assert rows[2]["maia_refutation_rank"] == rank
    assert rows[5] == {"maia_refutation_prob": None, "maia_refutation_rank": None}
    assert await _stamp(session_factory, game_id) is not None
    assert await _refutation_stamp(session_factory, game_id) is not None


_NULL_PAIR: dict[str, None] = {"maia_refutation_prob": None, "maia_refutation_rank": None}
# White's legal replies after Black's Nc6 (ply 3) and Black's Nf6 (ply 7) in _PGN.
_REPLY_AFTER_NC6 = "f1b5"
_REPLY_AFTER_NF6 = "d2d3"


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


async def test_refutation_scope_black_user_scores_only_own_blunders(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """D-03 for a black user: ply 3 and 7 (black blunders) scored, ply 4 (white) NULL."""
    game_id = await make_game(
        flaw_plies=(3, 4, 7), user_color="black", best={4: _REPLY_AFTER_NC6, 8: _REPLY_AFTER_NF6}
    )
    replayed = _replayed(_PGN)
    assert await _score(session_factory, game_id)
    rows = await _refutation_rows(session_factory, game_id)
    for ply, reply in ((3, _REPLY_AFTER_NC6), (7, _REPLY_AFTER_NF6)):
        prob, rank = _expected_refutation(replayed, ply, reply)
        assert rows[ply]["maia_refutation_prob"] == pytest.approx(prob, abs=_REAL_TOLERANCE)
        assert rows[ply]["maia_refutation_rank"] == rank
    assert rows[4] == _NULL_PAIR


@pytest.mark.parametrize(
    ("user_color", "flaw_plies", "mistake_ply", "opponent_ply", "scored_ply", "best"),
    [
        # White user: ply 2 mistake, ply 5 black blunder (reply b5a4 at 6, so scoring it
        # would be possible), ply 4 white blunder (reply g8f6 at 5).
        ("white", (2, 4, 5), 2, 5, 4, {6: "b5a4"}),
        # Black user: ply 3 mistake, ply 4 white blunder, ply 7 black blunder (reply d2d3 at 8).
        ("black", (3, 4, 7), 3, 4, 7, {}),
    ],
)
async def test_refutation_scope_mistakes_and_opponent_stay_null(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    user_color: Literal["white", "black"],
    flaw_plies: tuple[int, ...],
    mistake_ply: int,
    opponent_ply: int,
    scored_ply: int,
    best: dict[int, str | None],
) -> None:
    """D-03: user mistakes and opponent blunders never receive a pair, for both colors."""
    game_id = await make_game(
        flaw_plies=flaw_plies, user_color=user_color, severities={mistake_ply: 1}, best=best
    )
    assert await _score(session_factory, game_id)
    rows = await _refutation_rows(session_factory, game_id)
    assert rows[mistake_ply] == _NULL_PAIR
    assert rows[opponent_ply] == _NULL_PAIR
    assert rows[scored_ply]["maia_refutation_prob"] is not None
    assert rows[scored_ply]["maia_refutation_rank"] is not None


@pytest.mark.parametrize(
    ("user_color", "flaw_ply", "reply_ply", "reply"),
    [("white", 2, 3, _REPLY_AFTER_NF3), ("black", 3, 4, _REPLY_AFTER_NC6)],
)
async def test_refutation_elo_is_the_blunderers_for_both_colors(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
    user_color: Literal["white", "black"],
    flaw_ply: int,
    reply_ply: int,
    reply: str,
) -> None:
    """D-04: the refutation call is fed the blunderer's pinned Elo, never the opponent's."""
    game_id = await make_game(
        flaw_plies=(flaw_ply,), user_color=user_color, best={reply_ply: reply}
    )
    calls = _recording_policy(monkeypatch)
    assert await _score(session_factory, game_id)
    own = _pinned_elo(_WHITE_RATING if user_color == "white" else _BLACK_RATING)
    opp = _pinned_elo(_BLACK_RATING if user_color == "white" else _WHITE_RATING)
    assert own != opp, "the test needs distinct pinned Elos to be meaningful"
    assert len(calls) == 2
    pre_fen, pre_elo = calls[0]
    post_fen, post_elo = calls[1]
    # Base call: blunderer to move. Refutation call: opponent to move, SAME (blunderer) Elo.
    assert pre_fen.split(" ")[1] == ("w" if user_color == "white" else "b")
    assert post_fen.split(" ")[1] == ("b" if user_color == "white" else "w")
    assert pre_elo == own
    assert post_elo == own
    assert post_elo != opp


async def test_refutation_en_passant_board_is_exact(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-05: the post-blunder board keeps the ep square; the reply is legal only with it."""
    game_id = await make_game(pgn=_EP_PGN, flaw_plies=(3,), user_color="black")
    calls = _recording_policy(monkeypatch)
    assert await _score(session_factory, game_id)
    rows = await _refutation_rows(session_factory, game_id)
    assert rows[3]["maia_refutation_prob"] is not None, "exd6 needs the d6 ep square"
    assert any(" d6 " in fen for fen, _ in calls)


async def test_refutation_castling_board_is_exact(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """D-05: castling rights survive into the post-blunder board; O-O is the reply."""
    game_id = await make_game(flaw_plies=(7,), user_color="black", best={8: "e1g1"})
    assert await _score(session_factory, game_id)
    rows = await _refutation_rows(session_factory, game_id)
    assert rows[7]["maia_refutation_prob"] is not None, "e1g1 needs the castling rights"


def test_refutation_target_boards_are_never_mutated() -> None:
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
                best_uci=None,
                second_uci=None,
                severity=2,
                refutation_uci=_REPLY_AFTER_NF3 if ply == 2 else None,
                refutation_from_pv=False,
            )
            for ply in (2, 8)
        ),
    )
    score = score_game(inputs, boards)
    assert score.rows[0]["maia_refutation_prob"] is not None, "ply 2 must have been scored"
    after = {ply: (b.fen(), list(b.move_stack)) for ply, (b, _) in boards.items()}
    assert after == before


async def test_refutation_pv_fallback_when_best_move_null(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """D-20: ply+1 best_move NULL falls back to the first pv token and is counted."""
    game_id = await make_game(
        flaw_plies=(2,), best={3: None}, pv={3: f"{_REPLY_AFTER_NF3} d2d4 e5d4"}
    )
    replayed = _replayed(_PGN)
    score = score_game(await _inputs(session_factory, game_id), None)
    assert score.refutations_from_pv == 1
    assert score.user_blunders == 1
    assert await _score(session_factory, game_id)
    prob, rank = _expected_refutation(replayed, 2, _REPLY_AFTER_NF3)
    row = (await _refutation_rows(session_factory, game_id))[2]
    assert row["maia_refutation_prob"] == pytest.approx(prob, abs=_REAL_TOLERANCE)
    assert row["maia_refutation_rank"] == rank


async def test_refutation_best_move_wins_over_pv(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """D-20: when best_move is present the pv token is ignored and nothing is counted."""
    game_id = await make_game(flaw_plies=(2,), best={3: _REPLY_AFTER_NF3}, pv={3: "a7a6 d2d4"})
    score = score_game(await _inputs(session_factory, game_id), None)
    assert score.refutations_from_pv == 0
    prob, rank = _expected_refutation(_replayed(_PGN), 2, _REPLY_AFTER_NF3)
    assert await _score(session_factory, game_id)
    row = (await _refutation_rows(session_factory, game_id))[2]
    assert row["maia_refutation_prob"] == pytest.approx(prob, abs=_REAL_TOLERANCE)
    assert row["maia_refutation_rank"] == rank


@pytest.mark.parametrize(
    ("best", "pv", "reason"),
    [
        (None, None, "refutation_missing"),
        ("a1a8", None, "refutation_not_legal"),
        ("zz", None, "refutation_not_legal"),
        (None, "a1a8 e2e4", "refutation_not_legal"),
    ],
)
async def test_refutation_unusable_reply_leaves_null_without_inference(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
    best: str | None,
    pv: str | None,
    reason: MaiaReason,
) -> None:
    """Missing, illegal or malformed replies: NULL pair, counted reason, no extra call."""
    game_id = await make_game(
        flaw_plies=(2,), best={3: best}, pv={3: pv} if pv is not None else None
    )
    score = score_game(await _inputs(session_factory, game_id), None)
    assert score.reasons[reason] == 1
    calls = _recording_policy(monkeypatch)
    assert await _score(session_factory, game_id)
    assert len(calls) == 1, "only the base call: the unusable reply costs no inference"
    assert (await _refutation_rows(session_factory, game_id))[2] == _NULL_PAIR
    assert await _stamp(session_factory, game_id) is not None
    assert await _refutation_stamp(session_factory, game_id) is not None


async def test_refutation_blunder_that_stalemates_has_no_legal_reply(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stalemating blunder leaves the pair NULL (no_legal_reply); the game is stamped."""
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
    assert (await _refutation_rows(session_factory, game_id))[_STALEMATE_PLY] == _NULL_PAIR
    assert await _stamp(session_factory, game_id) is not None
    assert await _refutation_stamp(session_factory, game_id) is not None


async def test_refutation_call_count_is_base_plus_scorable_user_blunders(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """White user, flaws (2, 5, 8): three base calls plus one refutation call (ply 2 only).

    Ply 5 is the opponent's blunder; ply 8's reply (ply 9) has no row (refutation_missing).
    """
    game_id = await make_game(best={3: _REPLY_AFTER_NF3})
    calls = _recording_policy(monkeypatch)
    assert await _score(session_factory, game_id)
    assert len(calls) == 4


async def test_refutation_game_without_user_blunders_stamped_without_calls(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-09: opponent-only blunders and user mistakes still stamp both columns, no extra call."""
    game_id = await make_game(flaw_plies=(2, 5), severities={2: 1})
    calls = _recording_policy(monkeypatch)
    assert await _score(session_factory, game_id)
    assert len(calls) == 2
    assert all(r == _NULL_PAIR for r in (await _refutation_rows(session_factory, game_id)).values())
    assert await _stamp(session_factory, game_id) is not None
    assert await _refutation_stamp(session_factory, game_id) is not None


async def test_refutation_maia_absent_stamps_neither(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    game_id = await make_game(best={3: _REPLY_AFTER_NF3})
    monkeypatch.setattr(maia_engine, "_session", None)
    assert not await _score(session_factory, game_id)
    assert await _stamp(session_factory, game_id) is None
    assert await _refutation_stamp(session_factory, game_id) is None
    assert all(r == _NULL_PAIR for r in (await _refutation_rows(session_factory, game_id)).values())


@pytest.mark.parametrize("change", ["ply_plus_one_best_move", "severity"])
async def test_refutation_fingerprint_changed_skips_write(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame, change: str
) -> None:
    """A mid-flight change of the ply+1 best_move or of a severity writes nothing."""
    game_id = await make_game(flaw_plies=(2,), best={3: _REPLY_AFTER_NF3})
    score = score_game(await _inputs(session_factory, game_id), None)
    async with session_factory() as session:
        if change == "ply_plus_one_best_move":
            await session.execute(
                sa.update(GamePosition)
                .where(GamePosition.game_id == game_id, GamePosition.ply == 3)
                .values(best_move="a7a6")
            )
        else:
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
    assert all(r == _NULL_PAIR for r in (await _refutation_rows(session_factory, game_id)).values())
    assert await _stamp(session_factory, game_id) is None
    assert await _refutation_stamp(session_factory, game_id) is None


async def test_refutation_full_rescore_clears_row_downgraded_from_blunder(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """D-08: a Maia-loaded full re-score writes a NULL pair on a now-out-of-scope row."""
    game_id = await make_game(flaw_plies=(2,), severities={2: 1}, best={3: _REPLY_AFTER_NF3})
    async with session_factory() as session:
        await session.execute(
            sa.update(GameFlaw)
            .where(GameFlaw.game_id == game_id, GameFlaw.ply == 2)
            .values(maia_refutation_prob=0.5, maia_refutation_rank=2)
        )
        await session.commit()
    assert (await _refutation_rows(session_factory, game_id))[2] != _NULL_PAIR
    assert await _score(session_factory, game_id)
    assert (await _refutation_rows(session_factory, game_id))[2] == _NULL_PAIR


# ---------------------------------------------------------------------------
# Replay (D-06)
# ---------------------------------------------------------------------------


async def test_replay_castling_and_ep_fen(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The FEN handed to full_policy is the full FEN: castling field and ep square intact."""
    game_id = await make_game(pgn=_EP_PGN, flaw_plies=(4,))
    seen: list[str] = []

    def _spy(fen: str, elo: float) -> dict[str, float]:
        seen.append(fen)
        return fake_full_policy(fen, elo)

    monkeypatch.setattr(maia_flaw_scoring, "full_policy", _spy)
    assert await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )
    assert len(seen) == 1
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
    assert rows[2]["maia_played_rank"] != _STALE_RANK
    assert rows[2]["maia_effective_moves"] != _STALE_EFFECTIVE


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
    # A concurrent apply rewrites game_positions.best_move at a flaw ply.
    async with session_factory() as session:
        await session.execute(
            sa.update(GamePosition)
            .where(GamePosition.game_id == game_id, GamePosition.ply == 5)
            .values(best_move="b8c6")
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
            sa.update(GamePosition)
            .where(GamePosition.game_id == ids[1], GamePosition.ply == 2)
            .values(best_move="e2e3")
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
    elos: dict[str, float] = {}

    def _spy(fen: str, elo: float) -> dict[str, float]:
        elos[fen.split(" ")[1]] = elo
        return fake_full_policy(fen, elo)

    monkeypatch.setattr(maia_flaw_scoring, "full_policy", _spy)
    assert await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )

    def _pinned(raw: int) -> float:
        return pinned_elo_for_mover(
            raw_rating=raw, platform="lichess", time_control_bucket="blitz", is_correspondence=False
        )

    assert elos == {"w": _pinned(_WHITE_RATING), "b": _pinned(_BLACK_RATING)}


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
    fen; only ply 5 is scorable.
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
    assert len(calls) == 1


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


async def test_scorer_second_pair_from_db_d15(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """D-15 wiring: the raw su and game_positions.best_move reach the pure rule unchanged."""
    # Ply 2: su equals the stored best move. Ply 5: no missed_pv_lines at all (SQL NULL).
    game_id = await make_game(flaw_plies=(2, 5), missed_pv={2: [{"su": _BEST[2]}]})
    score = score_game(await _inputs(session_factory, game_id), None)
    assert score.reasons["second_equals_best"] == 1
    assert score.reasons["second_missing"] == 1
    assert await score_game_flaws_after_apply(
        session_factory, game_id, targets=None, source="backfill"
    )
    rows = await _flaw_rows(session_factory, game_id)
    for ply in (2, 5):
        assert rows[ply]["maia_second_prob"] is None
        assert rows[ply]["maia_second_rank"] is None
        assert rows[ply]["maia_played_prob"] is not None
        assert rows[ply]["maia_top_prob"] is not None
        assert rows[ply]["maia_best_prob"] is not None


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
_PRIOR_MAIA: dict[str, Any] = {
    "maia_played_prob": 0.125,
    "maia_played_rank": 3,
    "maia_best_prob": 0.25,
    "maia_best_rank": 2,
    "maia_second_prob": 0.375,
    "maia_second_rank": 1,
    "maia_top_prob": 0.5,
    "maia_effective_moves": 5.5,
}
_PRIOR_REFUTATION: dict[str, Any] = {"maia_refutation_prob": 0.0625, "maia_refutation_rank": 2}
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
    """Give every listed flaw row non-NULL Maia values (incl. refutation) and stamp both columns."""
    async with maker() as session:
        for ply in plies:
            await session.execute(
                sa.update(GameFlaw)
                .where(GameFlaw.game_id == game_id, GameFlaw.ply == ply)
                .values(**_PRIOR_MAIA, **_PRIOR_REFUTATION)
            )
        await session.execute(
            sa.update(Game)
            .where(Game.id == game_id)
            .values(
                maia_flaws_completed_at=sa.func.now(),
                maia_refutation_completed_at=sa.func.now(),
            )
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
    refutation = await _refutation_rows(maker, game_id)
    assert refutation[_RECLASSIFY_SURVIVOR_PLY] == _PRIOR_REFUTATION, (
        "survivor keeps its pair (D-08)"
    )
    assert refutation[_RECLASSIFY_NEW_PLY] == _NULL_PAIR, "a new flaw ply starts with a NULL pair"
    assert await _stamp(maker, game_id) is None
    assert await _refutation_stamp(maker, game_id) is None, "both stamps are cleared (D-08)"
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
    assert await _stamp(session_factory, game_id) is not None
    assert await _refutation_stamp(session_factory, game_id) is not None
    rows = await _flaw_rows(session_factory, game_id)
    assert rows[_RECLASSIFY_SURVIVOR_PLY] == _PRIOR_MAIA
    refutation = await _refutation_rows(session_factory, game_id)
    assert refutation[_RECLASSIFY_SURVIVOR_PLY] == _PRIOR_REFUTATION


async def test_reclassify_unknown_game_returns_false(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    assert await _reclassify(session_factory, 2_000_000_000) is False


@pytest.mark.parametrize(
    ("base_stamp", "refutation_stamp", "expected_cleared"),
    [(True, True, True), (True, False, True), (False, True, True), (False, False, False)],
)
async def test_reclassify_clear_helper_clears_both_stamps(
    session_factory: async_sessionmaker[AsyncSession],
    make_game: MakeGame,
    base_stamp: bool,
    refutation_stamp: bool,
    expected_cleared: bool,
) -> None:
    """D-08/D-22: one UPDATE clears both stamps; True when either was set (incl. refutation-only)."""
    game_id = await make_game(flaw_plies=())
    async with session_factory() as session:
        await session.execute(
            sa.update(Game)
            .where(Game.id == game_id)
            .values(
                maia_flaws_completed_at=sa.func.now() if base_stamp else None,
                maia_refutation_completed_at=sa.func.now() if refutation_stamp else None,
            )
        )
        await session.commit()
    async with session_factory() as session:
        assert await clear_maia_flaws_completed(session, game_id) is expected_cleared
        await session.commit()
    assert await _stamp(session_factory, game_id) is None
    assert await _refutation_stamp(session_factory, game_id) is None


async def test_write_rejects_batch_mixing_full_and_refutation_scores(
    session_factory: async_sessionmaker[AsyncSession], make_game: MakeGame
) -> None:
    """Refutation rows carry two keys, full rows ten: one executemany cannot take both."""
    full_game = await make_game()
    refutation_game = await make_game()
    full = score_game(await _inputs(session_factory, full_game), None)
    refutation = score_game(await _inputs(session_factory, refutation_game), None, "refutation")

    async with session_factory() as session:
        with pytest.raises(ValueError, match="mixing"):
            await write_game_maia_scores(session, [full, refutation], require_unstamped=False)
