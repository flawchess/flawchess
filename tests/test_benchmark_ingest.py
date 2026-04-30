"""Tests for benchmark ingestion pipeline.

Phase 69 unit tests covering:
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


# --- INGEST-02: per-TC player bucketing ------------------------------------------


def _stats(elos_by_tc: dict[str, list[int]], eval_count_by_tc: dict[str, int]) -> dict:
    """Build a PlayerStats-shaped dict for tests."""
    return {"elos_by_tc": elos_by_tc, "eval_count_by_tc": eval_count_by_tc}


def test_player_bucketing_basic() -> None:
    """Per-TC bucketing: a user qualifies for each TC where they meet the eval threshold,
    bucketed by per-TC median Elo (not a global median)."""
    from scripts.select_benchmark_users import bucket_players

    player_stats = {
        # alice: 3 blitz games (median 1500), 1 rapid game — only blitz qualifies (eval_threshold=5)
        "alice": _stats(
            {"blitz": [1450, 1500, 1550], "rapid": [1600]},
            {"blitz": 10, "rapid": 1},
        ),
        # bob: blitz eval_count below threshold — excluded entirely
        "bob_low_eval": _stats(
            {"blitz": [1500, 1500]},
            {"blitz": 3},
        ),
        # carol: per-TC median elo < 800
        "carol_under_800": _stats(
            {"blitz": [700, 750, 799]},
            {"blitz": 10},
        ),
        # dave: rapid eval games well above threshold
        "dave_top": _stats(
            {"rapid": [2500, 2600]},
            {"rapid": 10},
        ),
    }
    out = bucket_players(player_stats, eval_threshold=5)

    assert "alice" in out.get((1200, "blitz"), [])
    # alice's 1 rapid game does NOT qualify (eval_count rapid=1 < 5)
    assert "alice" not in out.get((1600, "rapid"), [])
    assert all("bob_low_eval" not in v for v in out.values())
    assert all("carol_under_800" not in v for v in out.values())
    assert "dave_top" in out.get((2400, "rapid"), [])


def test_player_bucketing_multi_tc_membership() -> None:
    """A user with sufficient eval games in two TCs qualifies for both cells,
    each bucketed by the per-TC median Elo (which can land in different ELO buckets)."""
    from scripts.select_benchmark_users import bucket_players

    # 50 blitz games at median 1900, 50 classical games at median 2200 — distinct medians
    blitz_elos = [1850 + i for i in range(50)]  # median = 1874 -> bucket 1600
    classical_elos = [2150 + i for i in range(50)]  # median = 2174 -> bucket 2000
    multi_tc_user = {
        "specialist": _stats(
            {"blitz": blitz_elos, "classical": classical_elos},
            {"blitz": 50, "classical": 50},
        ),
    }
    out = bucket_players(multi_tc_user, eval_threshold=5)

    assert "specialist" in out.get((1600, "blitz"), [])
    assert "specialist" in out.get((2000, "classical"), [])
    # Sanity: no spurious cells
    assert sum(1 for cell in out.values() if "specialist" in cell) == 2


def test_player_bucketing_boundaries() -> None:
    """Bucket boundaries: 1199->800, 1200->1200, 1599->1200, 1600->1600, 2399->2000, 2400->2400.

    With per-TC bucketing, a single-game player's median == that game's Elo.
    """
    from scripts.select_benchmark_users import bucket_players

    edge_cases = {
        "p_1199": _stats({"blitz": [1199]}, {"blitz": 5}),
        "p_1200": _stats({"blitz": [1200]}, {"blitz": 5}),
        "p_1599": _stats({"blitz": [1599]}, {"blitz": 5}),
        "p_1600": _stats({"blitz": [1600]}, {"blitz": 5}),
        "p_2399": _stats({"blitz": [2399]}, {"blitz": 5}),
        "p_2400": _stats({"blitz": [2400]}, {"blitz": 5}),
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


@pytest.mark.asyncio
async def test_persist_selection_compound_dedup() -> None:
    """persist_selection keys idempotency on (username, tc_bucket).

    A re-run with the same (user, tc) skips inserting; the same user under a
    different tc_bucket still inserts. This matches the compound unique
    constraint on benchmark_selected_users.
    """
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock, MagicMock, patch

    from scripts import select_benchmark_users

    # Existing rows: alice already selected for blitz
    existing_rows = [("alice", "blitz")]

    cell_to_users = {
        # blitz cell — alice should be skipped (already in DB), bob inserts
        (1200, "blitz"): ["alice", "bob"],
        # classical cell — alice/classical inserts (different TC, allowed)
        (2000, "classical"): ["alice"],
    }
    median_elos_by_tc = {
        ("alice", "blitz"): 1500,
        ("alice", "classical"): 2200,
        ("bob", "blitz"): 1500,
    }
    eval_counts_by_tc = {
        ("alice", "blitz"): 10,
        ("alice", "classical"): 10,
        ("bob", "blitz"): 10,
    }

    # Mock SELECT result for existing (username, tc_bucket) rows
    select_result = MagicMock()
    select_result.all = MagicMock(return_value=existing_rows)

    from app.models.benchmark_selected_user import BenchmarkSelectedUser

    added_rows: list[BenchmarkSelectedUser] = []

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=select_result)
    mock_session.add = MagicMock(side_effect=lambda obj: added_rows.append(obj))
    mock_session.commit = AsyncMock()

    @asynccontextmanager
    async def fake_session_cm():
        yield mock_session

    fake_session_maker = MagicMock(return_value=fake_session_cm())

    @asynccontextmanager
    async def fake_engine_begin():
        conn = MagicMock()
        conn.run_sync = AsyncMock()
        yield conn

    fake_engine = MagicMock()
    fake_engine.begin = MagicMock(side_effect=fake_engine_begin)
    fake_engine.dispose = AsyncMock()

    with (
        patch.object(select_benchmark_users, "create_async_engine", return_value=fake_engine),
        patch.object(select_benchmark_users, "async_sessionmaker", return_value=fake_session_maker),
    ):
        await select_benchmark_users.persist_selection(
            db_url="postgresql+asyncpg://x:y@localhost/z",
            cell_to_users=cell_to_users,
            per_cell=10,
            median_elos_by_tc=median_elos_by_tc,
            eval_counts_by_tc=eval_counts_by_tc,
            dump_month="2026-03",
        )

    inserted_keys = {(row.lichess_username, row.tc_bucket) for row in added_rows}
    assert ("alice", "blitz") not in inserted_keys, "alice/blitz should be skipped"
    assert ("alice", "classical") in inserted_keys, "alice/classical should insert"
    assert ("bob", "blitz") in inserted_keys, "bob/blitz should insert"
    assert len(added_rows) == 2
