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
