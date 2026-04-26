"""Tests for benchmark ingestion pipeline.

Phase 69 unit tests covering:
- INGEST-06 eval column wiring (this file from Task 02-01)
- INGEST-06 centipawn convention (Task 02-01)
- INGEST-01 dump scan parser (Plan 04 will add)
- INGEST-02 player bucketing (Plan 04 will add)
- INGEST-04 stub User invariants and outlier skip (Plan 05 will add)

All tests are pure unit tests, no DB, no network. Use unittest.mock for external deps.
"""

from __future__ import annotations

import io

import chess.pgn
import pytest

from app.schemas.normalization import NormalizedGame


# --- INGEST-06: eval column wiring -------------------------------------------------


def _make_lichess_game(
    game_id: str = "abc12345",
    white: str = "alice",
    black: str = "bob",
    white_elo: int = 1500,
    black_elo: int = 1500,
    pgn: str = (
        '[Event "Rated Blitz game"]\n'
        '[Site "https://lichess.org/abc12345"]\n'
        '[White "alice"]\n'
        '[Black "bob"]\n'
        '[Result "1-0"]\n'
        '[WhiteElo "1500"]\n'
        '[BlackElo "1500"]\n'
        '[TimeControl "300+0"]\n'
        '[Variant "Standard"]\n'
        '[UTCDate "2026.02.15"]\n'
        '[UTCTime "12:00:00"]\n\n'
        "1. e4 e5 2. Nf3 1-0\n"
    ),
) -> dict:
    """Minimal Lichess NDJSON game dict for normalize_lichess_game()."""
    return {
        "id": game_id,
        "rated": True,
        "variant": "standard",
        "speed": "blitz",
        "perf": "blitz",
        "createdAt": 1707998400000,  # 2024-02-15
        "lastMoveAt": 1707998700000,
        "status": "mate",
        "winner": "white",
        "players": {
            "white": {"user": {"name": white}, "rating": white_elo},
            "black": {"user": {"name": black}, "rating": black_elo},
        },
        "clock": {"initial": 300, "increment": 0, "totalTime": 300},
        "pgn": pgn,
    }


def _make_chesscom_game() -> dict:
    """Minimal chess.com game dict for normalize_chesscom_game()."""
    return {
        "uuid": "ccgame-uuid-1",
        "url": "https://chess.com/game/123",
        "pgn": (
            '[Event "Live Chess"]\n'
            '[White "alice"]\n'
            '[Black "bob"]\n'
            '[Result "1-0"]\n'
            '[WhiteElo "1500"]\n'
            '[BlackElo "1500"]\n'
            '[TimeControl "300"]\n'
            '[UTCDate "2026.02.15"]\n'
            '[UTCTime "12:00:00"]\n\n'
            "1. e4 e5 1-0\n"
        ),
        "time_control": "300",
        "time_class": "blitz",
        "rated": True,
        "rules": "chess",
        "white": {"username": "alice", "rating": 1500, "result": "win"},
        "black": {"username": "bob", "rating": 1500, "result": "checkmated"},
        "end_time": 1707998700,
    }


def test_eval_columns_lichess_sets_constant() -> None:
    """normalize_lichess_game sets eval_source_version='lichess-pgn' unconditionally."""
    from app.services.normalization import normalize_lichess_game

    game = _make_lichess_game()
    normalized = normalize_lichess_game(game, "alice", user_id=1)

    assert isinstance(normalized, NormalizedGame)
    assert normalized.eval_source_version == "lichess-pgn", (
        "Lichess imports must always tag eval_source_version='lichess-pgn'"
    )
    assert normalized.eval_depth is None, (
        "Lichess /api/games/user does not surface eval depth, must be None"
    )


def test_eval_columns_chesscom_leaves_null() -> None:
    """normalize_chesscom_game leaves both eval columns NULL (chess.com has no eval)."""
    from app.services.normalization import normalize_chesscom_game

    game = _make_chesscom_game()
    normalized = normalize_chesscom_game(game, "alice", user_id=1)

    assert isinstance(normalized, NormalizedGame)
    assert normalized.eval_source_version is None
    assert normalized.eval_depth is None


# --- INGEST-06: centipawn convention -----------------------------------------------


def test_centipawn_convention_signed_from_white() -> None:
    """[%eval 2.35] parses to +235 cp; [%eval -0.50] to -50 cp; mate stays in mate field.

    Documents the signed-from-White-POV convention used by python-chess and stored in
    game_positions.eval_cp. This is the INGEST-06 centipawn-convention verification.
    """
    pgn_text = (
        '[Event "Test"]\n'
        '[White "a"]\n'
        '[Black "b"]\n'
        '[Result "*"]\n\n'
        "1. e4 { [%eval 2.35] } e5 { [%eval -0.50] } 2. Nf3 { [%eval #4] } *\n"
    )
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    assert game is not None

    nodes = list(game.mainline())
    assert len(nodes) >= 3

    # Move 1 (1. e4): [%eval 2.35] -> 235 centipawns from White POV
    pov0 = nodes[0].eval()
    assert pov0 is not None
    assert pov0.white().score(mate_score=None) == 235

    # Move 1...e5: [%eval -0.50] -> -50 centipawns from White POV
    pov1 = nodes[1].eval()
    assert pov1 is not None
    assert pov1.white().score(mate_score=None) == -50

    # Move 2 (2. Nf3): [%eval #4] -> mate in 4 from White POV
    pov2 = nodes[2].eval()
    assert pov2 is not None
    assert pov2.white().score(mate_score=None) is None
    assert pov2.white().mate() == 4


# --- INGEST-02: player bucketing -------------------------------------------------


def test_player_bucketing_basic() -> None:
    """Median Elo + modal TC bucketing assigns each qualifying player to one cell."""
    from scripts.select_benchmark_users import bucket_players

    player_stats = {
        "alice": {
            "elos": [1450, 1500, 1550],
            "tcs": ["blitz", "blitz", "rapid"],
            "eval_count": 10,
        },
        "bob_low_eval": {
            "elos": [1500, 1500],
            "tcs": ["blitz", "blitz"],
            "eval_count": 3,
        },  # below K=5
        "carol_under_800": {
            "elos": [700, 750, 799],
            "tcs": ["blitz"] * 3,
            "eval_count": 10,
        },
        "dave_top": {
            "elos": [2500, 2600],
            "tcs": ["rapid", "rapid"],
            "eval_count": 10,
        },
    }
    out = bucket_players(player_stats, eval_threshold=5)

    # alice -> (1200, "blitz") because median(1450,1500,1550)=1500 -> bucket 1200, modal "blitz"
    assert "alice" in out.get((1200, "blitz"), [])
    # bob excluded (eval_count < 5)
    assert all("bob_low_eval" not in v for v in out.values())
    # carol excluded (median elo < 800)
    assert all("carol_under_800" not in v for v in out.values())
    # dave -> (2400, "rapid")
    assert "dave_top" in out.get((2400, "rapid"), [])


def test_player_bucketing_boundaries() -> None:
    """Bucket boundaries: 1199->800, 1200->1200, 1599->1200, 1600->1600, 2399->2000, 2400->2400."""
    from scripts.select_benchmark_users import bucket_players

    edge_cases = {
        "p_1199": {"elos": [1199], "tcs": ["blitz"], "eval_count": 5},
        "p_1200": {"elos": [1200], "tcs": ["blitz"], "eval_count": 5},
        "p_1599": {"elos": [1599], "tcs": ["blitz"], "eval_count": 5},
        "p_1600": {"elos": [1600], "tcs": ["blitz"], "eval_count": 5},
        "p_2399": {"elos": [2399], "tcs": ["blitz"], "eval_count": 5},
        "p_2400": {"elos": [2400], "tcs": ["blitz"], "eval_count": 5},
    }
    out = bucket_players(edge_cases, eval_threshold=5)
    assert "p_1199" in out.get((800, "blitz"), [])
    assert "p_1200" in out.get((1200, "blitz"), [])
    assert "p_1599" in out.get((1200, "blitz"), [])
    assert "p_1600" in out.get((1600, "blitz"), [])
    assert "p_2399" in out.get((2000, "blitz"), [])
    assert "p_2400" in out.get((2400, "blitz"), [])


# --- INGEST-01: streaming PGN-header parser --------------------------------------


def test_scan_dump_parser_extracts_headers_and_eval_flag() -> None:
    """The streaming parser yields one record per game with headers + has_eval flag.

    Operates on a synthetic decompressed text stream -- no real .zst file needed.
    """
    from scripts.select_benchmark_users import parse_pgn_stream

    pgn_text = (
        '[Event "Rated Blitz"]\n'
        '[White "alice"]\n'
        '[Black "bob"]\n'
        '[WhiteElo "1500"]\n'
        '[BlackElo "1450"]\n'
        '[TimeControl "300+0"]\n'
        '[Variant "Standard"]\n'
        "\n"
        "1. e4 { [%eval 0.20] } e5 1-0\n"
        "\n"
        '[Event "Rated Bullet"]\n'
        '[White "carol"]\n'
        '[Black "dave"]\n'
        '[WhiteElo "1800"]\n'
        '[BlackElo "1850"]\n'
        '[TimeControl "60+1"]\n'
        '[Variant "Standard"]\n'
        "\n"
        "1. e4 e5 1-0\n"
        "\n"
        '[Event "Rated Crazyhouse"]\n'
        '[White "eve"]\n'
        '[Black "frank"]\n'
        '[WhiteElo "2000"]\n'
        '[BlackElo "1950"]\n'
        '[TimeControl "300+0"]\n'
        '[Variant "Crazyhouse"]\n'
        "\n"
        "1. e4 e5 1-0\n"
        "\n"
    )

    records = list(parse_pgn_stream(io.StringIO(pgn_text)))

    # Crazyhouse must be filtered out (Standard-variant only)
    assert len(records) == 2

    r0, r1 = records
    assert r0["white"] == "alice"
    assert r0["black"] == "bob"
    assert r0["white_elo"] == 1500
    assert r0["black_elo"] == 1450
    assert r0["time_control"] == "300+0"
    assert r0["has_eval"] is True

    assert r1["white"] == "carol"
    assert r1["has_eval"] is False


# --- INGEST-04: stub User invariants, outlier skip, cell deficit ---------------------


@pytest.mark.asyncio
async def test_stub_user_invariants() -> None:
    """create_stub_user returns an int id; row passes FastAPI-Users invariants but cannot auth.

    Idempotent: calling with the same username returns the same id without inserting twice.
    """
    from unittest.mock import AsyncMock, MagicMock

    from scripts.import_benchmark_users import create_stub_user

    # First call: no existing row -> returns new id
    session = MagicMock()
    session.execute = AsyncMock()
    # Mock the SELECT for existing user to return None
    no_user_result = MagicMock()
    no_user_result.scalar_one_or_none = MagicMock(return_value=None)
    session.execute.return_value = no_user_result
    session.add = MagicMock()
    session.flush = AsyncMock()

    # Capture the User object that gets added
    from app.models.user import User as _User

    added_user: dict[str, _User] = {}

    def _capture(obj: _User) -> None:
        added_user["obj"] = obj
        # Simulate flush assigning an id
        obj.id = 42

    session.add.side_effect = _capture

    new_id = await create_stub_user(session, "alice")

    assert new_id == 42
    user_obj = added_user["obj"]
    assert user_obj.email == "lichess-alice@benchmark.flawchess.local"
    assert user_obj.lichess_username == "alice"
    assert user_obj.is_active is False
    assert user_obj.hashed_password == "!BENCHMARK_NO_AUTH"
    assert user_obj.is_guest is False


def test_outlier_hard_skip_threshold() -> None:
    """_should_hard_skip returns True at >= 20_000 games (D-14)."""
    from scripts.import_benchmark_users import _should_hard_skip

    assert _should_hard_skip(19_999) is False
    assert _should_hard_skip(20_000) is True
    assert _should_hard_skip(20_001) is True
    assert _should_hard_skip(0) is False


def test_compute_deficit_users_skips_completed_in_pool_order() -> None:
    """compute_deficit_users draws (N - completed_in_cell) usernames in pool order."""
    from scripts.import_benchmark_users import compute_deficit_users

    pool = ["u1", "u2", "u3", "u4", "u5"]
    completed = {"u1", "u2"}
    # Deficit = 3 - 2 (already completed in pool) = 1; draw next from pool skipping completed
    out = compute_deficit_users(pool=pool, completed=completed, target_n=3)
    assert out == ["u3"]

    # If target already met: empty list
    out2 = compute_deficit_users(pool=pool, completed={"u1", "u2", "u3"}, target_n=3)
    assert out2 == []

    # If pool is exhausted before target: return what is available
    out3 = compute_deficit_users(pool=["u1", "u2"], completed=set(), target_n=10)
    assert out3 == ["u1", "u2"]
