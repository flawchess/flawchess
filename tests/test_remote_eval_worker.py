"""Unit tests for the remote eval worker CLI (Phase 123 SEED-051, Plan 03).

Covers:
- worker_id_default_length: generated default IDs are < 10 chars, base36 charset.
- worker_id_override_too_long: --worker-id >= 10 chars raises SystemExit (parser.error);
  < 10 chars accepted as-is.
- ladder_explicit_first: with /lease?scope=explicit returning 200, the cycle submits via
  /submit and does NOT call /entry-lease (busy tier-1 path stays 1-2 calls).
- ladder_entry_then_idle: scope=explicit 204 -> /entry-lease 200 -> /entry-submit; on
  /entry-lease 204 falls through to scope=idle.
- entry_eval_uses_depth15: _eval_entry_positions calls pool.evaluate (depth-15) and
  never calls pool.evaluate_nodes_with_pv (the 1M-node full-ply mode).

All tests are unit-level -- no DB, no real Stockfish. Engine pool and httpx are mocked.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call

import pytest

# Ensure project root is importable from the test root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.remote_eval_worker import (
    _WORKER_ID_ALPHABET,
    _WORKER_ID_DEFAULT_LEN,
    WORKER_ID_MAX_LEN,
    _eval_entry_positions,
    _generate_worker_id,
    _run_cycle,
    parse_args,
)

# ─── Worker-ID generation tests ──────────────────────────────────────────────


def test_worker_id_default_length() -> None:
    """Generated default worker-id is < 10 chars, base36 charset, exact expected length."""
    wid = _generate_worker_id()
    assert len(wid) == _WORKER_ID_DEFAULT_LEN
    assert len(wid) < 10  # D-10: must fit VARCHAR(16) as < 10 chars
    assert all(c in _WORKER_ID_ALPHABET for c in wid), f"Non-base36 char in {wid!r}"


def test_worker_id_uniqueness() -> None:
    """Two generated IDs are (almost certainly) distinct -- sanity for randomness."""
    ids = {_generate_worker_id() for _ in range(20)}
    assert len(ids) > 1, "All 20 generated IDs were identical -- RNG is broken"


def test_worker_id_override_too_long_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """--worker-id with >= 10 chars raises SystemExit (parser.error path, not Sentry)."""
    monkeypatch.setattr(sys, "argv", ["worker", "--worker-id", "a" * 10, "--once"])
    with pytest.raises(SystemExit):
        parse_args()


def test_worker_id_override_exactly_ten_chars_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Boundary: exactly 10 chars is rejected (must be *strictly* < 10)."""
    monkeypatch.setattr(sys, "argv", ["worker", "--worker-id", "1234567890", "--once"])
    with pytest.raises(SystemExit):
        parse_args()


def test_worker_id_override_nine_chars_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    """9-char override is accepted (< 10, satisfies VARCHAR(16) constraint)."""
    monkeypatch.setattr(sys, "argv", ["worker", "--worker-id", "a" * 9, "--once"])
    args = parse_args()
    assert args.worker_id == "a" * 9


def test_worker_id_override_short_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Short (< 9 chars) override is accepted as-is."""
    monkeypatch.setattr(sys, "argv", ["worker", "--worker-id", "box1", "--once"])
    args = parse_args()
    assert args.worker_id == "box1"


def test_worker_id_max_len_constant() -> None:
    """WORKER_ID_MAX_LEN matches the validation rule (len < 10 -> max 9)."""
    assert WORKER_ID_MAX_LEN == 9


# ─── D-06 ladder tests (mocked httpx.AsyncClient) ────────────────────────────


def _make_response(status_code: int, body: dict | None = None) -> MagicMock:
    """Create a mock httpx.Response with the given status and optional JSON body."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()  # no-op for success paths
    resp.json = MagicMock(return_value=body or {})
    return resp


async def test_ladder_explicit_first_skips_entry_lease() -> None:
    """When /lease?scope=explicit returns 200, the cycle submits via /submit only.

    It must NOT call /entry-lease (busy tier-1 path stays at 1-2 calls per D-06).
    """
    lease_body = {
        "game_id": 42,
        "positions": [
            {
                "ply": 2,
                "fen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
                "is_terminal": False,
            }
        ],
        "job_id": "job-token-abc",
    }
    submit_body = {"stamp_complete": True, "failed_ply_count": 0}

    client = AsyncMock()
    client.post = AsyncMock(
        side_effect=[
            _make_response(200, lease_body),  # /lease?scope=explicit -> 200
            _make_response(200, submit_body),  # /submit -> 200
        ]
    )

    pool = AsyncMock()
    pool.evaluate_nodes_with_pv = AsyncMock(return_value=(100, None, "e2e4", "e2e4 e7e5"))

    await _run_cycle(
        client=client,
        pool=pool,
        sf_version="sf16",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )

    # First call: /lease with scope=explicit
    first_call = client.post.call_args_list[0]
    assert first_call == call("/api/eval/remote/lease", params={"scope": "explicit"})

    # Second call: /submit
    second_call = client.post.call_args_list[1]
    assert second_call.args[0] == "/api/eval/remote/submit"

    # /entry-lease must never be called on the busy tier-1 path
    called_urls = [c.args[0] for c in client.post.call_args_list]
    assert "/api/eval/remote/entry-lease" not in called_urls


async def test_ladder_entry_ply_on_explicit_204() -> None:
    """When scope=explicit returns 204, the cycle calls /entry-lease.

    On /entry-lease 200, it evaluates at depth-15 and POSTs to /entry-submit.
    It must NOT fall through to scope=idle in this case.
    """
    entry_positions = [
        {
            "game_id": 7,
            "ply": 3,
            "fen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        },
    ]
    entry_body = {"positions": entry_positions, "leased_at": "2026-06-16T10:00:00Z"}
    entry_submit_body = {"game_ids": [7], "stamped_count": 1}

    client = AsyncMock()
    client.post = AsyncMock(
        side_effect=[
            _make_response(204),  # /lease?scope=explicit -> 204
            _make_response(200, entry_body),  # /entry-lease -> 200
            _make_response(200, entry_submit_body),  # /entry-submit -> 200
        ]
    )

    pool = AsyncMock()
    pool.evaluate = AsyncMock(return_value=(50, None))  # depth-15 returns (cp, mate)

    await _run_cycle(
        client=client,
        pool=pool,
        sf_version="sf16",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )

    called_urls = [c.args[0] for c in client.post.call_args_list]
    assert called_urls[0] == "/api/eval/remote/lease"
    assert called_urls[1] == "/api/eval/remote/entry-lease"
    assert called_urls[2] == "/api/eval/remote/entry-submit"

    # Must NOT call /lease?scope=idle -- entry-ply was served
    lease_calls = [c for c in client.post.call_args_list if c.args[0] == "/api/eval/remote/lease"]
    assert len(lease_calls) == 1, "scope=idle should not be called when entry-ply returned work"


async def test_ladder_falls_to_idle_when_entry_lease_204() -> None:
    """When scope=explicit 204 and /entry-lease 204, the cycle falls to scope=idle."""
    idle_body = {
        "game_id": 99,
        "positions": [
            {
                "ply": 5,
                "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
                "is_terminal": False,
            }
        ],
        "job_id": None,
    }
    submit_body = {"stamp_complete": True, "failed_ply_count": 0}

    client = AsyncMock()
    client.post = AsyncMock(
        side_effect=[
            _make_response(204),  # /lease?scope=explicit -> 204
            _make_response(204),  # /entry-lease -> 204
            _make_response(200, idle_body),  # /lease?scope=idle -> 200
            _make_response(200, submit_body),  # /submit -> 200
        ]
    )

    pool = AsyncMock()
    pool.evaluate_nodes_with_pv = AsyncMock(return_value=(0, None, "e1e2", "e1e2"))

    await _run_cycle(
        client=client,
        pool=pool,
        sf_version="sf16",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )

    called_urls = [c.args[0] for c in client.post.call_args_list]
    assert called_urls[0] == "/api/eval/remote/lease"  # scope=explicit
    assert called_urls[1] == "/api/eval/remote/entry-lease"
    assert called_urls[2] == "/api/eval/remote/lease"  # scope=idle
    assert called_urls[3] == "/api/eval/remote/submit"

    # Confirm the idle /lease call used scope=idle param
    idle_lease_call = client.post.call_args_list[2]
    assert idle_lease_call == call("/api/eval/remote/lease", params={"scope": "idle"})


# ─── Depth-15 eval path assertion ─────────────────────────────────────────────


async def test_entry_eval_uses_depth15_not_evaluate_nodes_with_pv() -> None:
    """_eval_entry_positions calls pool.evaluate (depth-15), never evaluate_nodes_with_pv.

    Critical: mixing modes makes entry-ply 10x slower (D-2 / RESEARCH Anti-pattern).
    """
    positions: list[dict[str, object]] = [
        {
            "game_id": 1,
            "ply": 2,
            "fen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        },
        {
            "game_id": 2,
            "ply": 4,
            "fen": "rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        },
    ]

    pool = MagicMock()
    pool.evaluate = AsyncMock(side_effect=[(100, None), (-50, None)])
    pool.evaluate_nodes_with_pv = AsyncMock(return_value=(999, None, "e2e4", "e2e4"))

    results = await _eval_entry_positions(pool, positions)

    # pool.evaluate called once per position (depth-15)
    assert pool.evaluate.call_count == 2
    # pool.evaluate_nodes_with_pv MUST NOT be called
    pool.evaluate_nodes_with_pv.assert_not_called()

    # Output shape: game_id, ply, eval_cp, eval_mate -- no best_move/pv
    assert results[0] == {"game_id": 1, "ply": 2, "eval_cp": 100, "eval_mate": None}
    assert results[1] == {"game_id": 2, "ply": 4, "eval_cp": -50, "eval_mate": None}
    for r in results:
        assert "best_move" not in r, "Entry-ply results must not contain best_move"
        assert "pv" not in r, "Entry-ply results must not contain pv"
