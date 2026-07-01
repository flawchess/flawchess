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
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

# Ensure project root is importable from the test root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.remote_eval_worker import (
    _WORKER_ID_ALPHABET,
    _WORKER_ID_DEFAULT_LEN,
    HTTP_TIMEOUT_S,
    WORKER_ID_MAX_LEN,
    _eval_entry_positions,
    _eval_flaw_blob_positions,
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


# ─── D-04 tier-4 flaw-blob drain rung tests (Phase 146) ─────────────────────


async def test_ladder_flaw_blob_on_all_tier123_204() -> None:
    """When all tier-1/2/3 rungs return 204, the worker reaches rung 4 (flaw-blob-lease).

    On a 200 flaw-blob-lease response, the cycle evaluates at MultiPV=2 and POSTs to
    /flaw-blob-submit. Both URLs must appear in the client.post call list (D-04).
    """
    blob_lease_body = {
        "game_id": 7,
        "positions": [
            {
                "token": "10:missed:0",
                "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
            }
        ],
        "leased_at": "2026-07-01T10:00:00Z",
    }
    submit_body = {"game_id": 7, "blobs_written": 1}

    client = AsyncMock()
    client.post = AsyncMock(
        side_effect=[
            _make_response(204),  # /lease?scope=explicit
            _make_response(204),  # /entry-lease
            _make_response(204),  # /lease?scope=idle
            _make_response(200, blob_lease_body),  # /flaw-blob-lease
            _make_response(200, submit_body),  # /flaw-blob-submit
        ]
    )

    pool = AsyncMock()
    # evaluate_nodes_multipv2 returns 7-tuple (D-04 blob rung keeps MultiPV-2)
    pool.evaluate_nodes_multipv2 = AsyncMock(
        return_value=(100, None, "e2e4", "e2e4 e7e5", 50, None, "d2d4")
    )

    await _run_cycle(
        client=client,
        pool=pool,
        sf_version="sf18",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )

    called_urls = [c.args[0] for c in client.post.call_args_list]
    assert "/api/eval/remote/flaw-blob-lease" in called_urls, (
        "rung-4 /flaw-blob-lease was not called after all tier-1/2/3 returned 204"
    )
    assert "/api/eval/remote/flaw-blob-submit" in called_urls, (
        "/flaw-blob-submit was not POSTed after a 200 from /flaw-blob-lease"
    )


async def test_ladder_all_queues_empty_sleeps_once() -> None:
    """When all four tiers (including rung-4 flaw-blob) return 204, the worker sleeps exactly once.

    Regression guard: rung-4 must not introduce a double-sleep (T-146-06).
    """
    client = AsyncMock()
    client.post = AsyncMock(
        side_effect=[
            _make_response(204),  # /lease?scope=explicit
            _make_response(204),  # /entry-lease
            _make_response(204),  # /lease?scope=idle
            _make_response(204),  # /flaw-blob-lease
        ]
    )
    pool = AsyncMock()

    with patch("scripts.remote_eval_worker.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await _run_cycle(
            client=client,
            pool=pool,
            sf_version="sf18",
            idle_sleep=1.0,
            dry_run=False,
            loop=False,
        )
        mock_sleep.assert_awaited_once_with(1.0)

    # Confirm rung-4 was actually reached (not just 3-rung sleep)
    called_urls = [c.args[0] for c in client.post.call_args_list]
    assert "/api/eval/remote/flaw-blob-lease" in called_urls, (
        "rung-4 /flaw-blob-lease was not called — sleep may have fired from rung 3 tail"
    )


async def test_eval_flaw_blob_positions_maps_indices_correctly() -> None:
    """_eval_flaw_blob_positions maps r[0]/r[1]/r[4]/r[5]/r[6]; never r[2]/r[3].

    evaluate_nodes_multipv2 returns (eval_cp, eval_mate, best_move, pv,
    second_cp, second_mate, second_uci). Fields r[2] (best_move) and r[3] (pv)
    must NOT appear in the output dict. Token is echoed unchanged (D-04a).
    """
    pool = AsyncMock()
    # 7-tuple: (eval_cp=100, eval_mate=None, best_move="e2e4", pv="e2e4 e7e5",
    #            second_cp=50, second_mate=None, second_uci="d2d4")
    pool.evaluate_nodes_multipv2 = AsyncMock(
        return_value=(100, None, "e2e4", "e2e4 e7e5", 50, None, "d2d4")
    )

    positions: list[dict[str, object]] = [
        {
            "token": "10:missed:0",
            "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        }
    ]
    results = await _eval_flaw_blob_positions(pool, positions)

    assert len(results) == 1
    r = results[0]
    assert r["token"] == "10:missed:0", "Token must be echoed unchanged (D-04a)"
    assert r["best_cp"] == 100, "best_cp must be r[0] (eval_cp)"
    assert r["best_mate"] is None, "best_mate must be r[1] (eval_mate)"
    assert r["second_cp"] == 50, "second_cp must be r[4]"
    assert r["second_mate"] is None, "second_mate must be r[5]"
    assert r["second_uci"] == "d2d4", "second_uci must be r[6]"
    assert "best_move" not in r, "r[2] (best_move) must NOT leak into the output dict"
    assert "pv" not in r, "r[3] (pv) must NOT leak into the output dict"


# ─── MultiPV-1 full-ply reduction + HTTP_TIMEOUT_S tests (Phase 146 Task 2) ──


def test_http_timeout_s_restored_to_30() -> None:
    """HTTP_TIMEOUT_S must be 30.0 — the SEED-071 120s stopgap is removed in Phase 146.

    After Phase 146 the live /submit no longer calls any engine, so the p99 latency
    drops well below 30s. 30s provides a 10x safety margin (RESEARCH §5).
    """
    assert HTTP_TIMEOUT_S == 30.0, (
        f"HTTP_TIMEOUT_S is {HTTP_TIMEOUT_S}, expected 30.0. "
        "Remove the SEED-071 stopgap comment and restore the original value."
    )


async def test_eval_positions_uses_multipv1_no_second_best() -> None:
    """_eval_positions (full-ply pass) uses evaluate_nodes_with_pv (4-tuple, MultiPV-1).

    Second-best fields (second_cp/second_mate/second_uci) must be absent from the output
    dict — they were dropped from SubmitEval in Plan 01 (D-03). The tier-4 blob rung
    (_eval_flaw_blob_positions) keeps evaluate_nodes_multipv2; the full-ply rung does not.
    """
    from scripts.remote_eval_worker import _eval_positions

    pool = AsyncMock()
    # evaluate_nodes_with_pv returns 4-tuple (eval_cp, eval_mate, best_move, pv)
    pool.evaluate_nodes_with_pv = AsyncMock(return_value=(100, None, "e2e4", "e2e4 e7e5"))
    # evaluate_nodes_multipv2 must NOT be called on the full-ply path
    pool.evaluate_nodes_multipv2 = AsyncMock(
        return_value=(99, None, "e2e4", "e2e4", 50, None, "d2d4")
    )

    positions: list[dict[str, object]] = [
        {
            "ply": 2,
            "fen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            "is_terminal": False,
        }
    ]
    results = await _eval_positions(pool, positions)

    assert len(results) == 1
    r = results[0]
    assert r["ply"] == 2
    assert r["eval_cp"] == 100
    assert r["eval_mate"] is None
    assert r["best_move"] == "e2e4"
    assert r["pv"] == "e2e4 e7e5"
    # Second-best keys must be absent (D-03 consequence: SubmitEval dropped them)
    assert "second_cp" not in r, "second_cp must not appear in full-ply output (D-03)"
    assert "second_mate" not in r, "second_mate must not appear in full-ply output (D-03)"
    assert "second_uci" not in r, "second_uci must not appear in full-ply output (D-03)"
    # Confirm MultiPV-1 path was used (not MultiPV-2)
    pool.evaluate_nodes_with_pv.assert_called_once()
    pool.evaluate_nodes_multipv2.assert_not_called()
