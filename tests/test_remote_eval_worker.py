"""Unit tests for the remote eval worker CLI.

Covers:
- worker_id_default_length: generated default IDs are < 10 chars, base36 charset.
- worker_id_override_too_long: --worker-id >= 10 chars raises SystemExit (parser.error);
  < 10 chars accepted as-is.
- ladder_explicit_first: with /atomic-lease?scope=explicit returning 200, the cycle
  submits via /atomic-submit and does NOT call /entry-lease (busy path stays 1-2 calls).
- ladder_entry_then_idle: scope=explicit 204 -> /entry-lease 200 -> /entry-submit; on
  /entry-lease 204 falls through to scope=idle (also /atomic-lease).
- entry_eval_uses_depth15: _eval_entry_positions calls pool.evaluate (depth-15) and
  never calls pool.evaluate_nodes_with_pv (the 1M-node full-ply mode).
- Atomic rung: _hint_flaw_plies/_build_blob_walk_targets/
  _eval_atomic_game — the local hint stays MultiPV-1 for the full-ply pass, selects
  only mistake/blunder plies, and the assembled /atomic-submit payload carries
  blob_nodes only for those hinted plies plus worker_schema_version.

All tests are unit-level -- no DB, no real Stockfish. Engine pool and httpx are mocked.
"""

from __future__ import annotations

import argparse
import asyncio
import heapq
import itertools
import sys
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, call, patch

import chess
import pytest

# Ensure project root is importable from the test root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

import scripts.remote_eval_worker as worker_module
from app.routers.eval_remote import WORKER_SCHEMA_VERSION_MIN
from app.services.engine import _NODES_TIMEOUT_S
from scripts.remote_eval_worker import (
    _LANE_TASK_PREFIX,
    DEFAULT_LANES,
    ENGINES_PER_LANE,
    EVAL_RETRY_MAX_POSITIONS,
    EVAL_RETRY_TIMEOUT_S,
    STALL_THRESHOLD_S,
    TRANSIENT_FAILURE_ALERT_S,
    _WORKER_ID_ALPHABET,
    _WORKER_ID_DEFAULT_LEN,
    HTTP_TIMEOUT_S,
    WORKER_ID_MAX_LEN,
    WORKER_SCHEMA_VERSION,
    _BackendTarget,
    _build_backend_targets,
    _describe_exc,
    _resolve_fallback_token,
    _build_blob_walk_targets,
    _eval_atomic_blob_nodes,
    _eval_atomic_game,
    _eval_bestmove_positions,
    _eval_entry_positions,
    _eval_flaw_blob_positions,
    _eval_positions,
    _eval_targeted_second_best,
    _fresh_retry_budget,
    _generate_worker_id,
    _handle_transient_failure,
    _Heartbeat,
    _hint_flaw_plies,
    _is_engine_failure,
    _is_expected_transient,
    _is_stalled,
    _effective_lanes,
    _lane_schedule,
    _LaneContext,
    _log,
    _max_lanes,
    _run_async,
    _run_lane,
    _on_cycle_failure,
    _RetryBudget,
    _retry_timed_out,
    _run_cycle,
    _run_lanes,
    _run_loop,
    _TransientStreak,
    _worker_role,
    main,
    parse_args,
    run_worker,
)


def _http_status_error(code: int) -> httpx.HTTPStatusError:
    """Build an HTTPStatusError carrying a response with the given status code."""
    request = httpx.Request("GET", "https://flawchess.com/api/eval/remote/lease")
    response = httpx.Response(code, request=request)
    return httpx.HTTPStatusError(f"{code}", request=request, response=response)


# ─── Worker-ID generation tests ──────────────────────────────────────────────


def test_worker_id_default_length() -> None:
    """Generated default worker-id is < 10 chars, base36 charset, exact expected length."""
    wid = _generate_worker_id()
    assert len(wid) == _WORKER_ID_DEFAULT_LEN
    assert len(wid) < 10  # Must fit VARCHAR(16) as < 10 chars
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


# ─── Ladder tests (mocked httpx.AsyncClient) ────────────────────────────


def _make_response(status_code: int, body: dict | None = None) -> MagicMock:
    """Create a mock httpx.Response with the given status and optional JSON body."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()  # no-op for success paths
    resp.json = MagicMock(return_value=body or {})
    return resp


async def test_ladder_explicit_first_skips_entry_lease() -> None:
    """When /atomic-lease?scope=explicit returns 200, the cycle submits via
    /atomic-submit only (rung 1).

    It must NOT call /entry-lease (busy tier-1 path stays at 1-2 calls).
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
    submit_body = {"game_id": 42, "flaws_written": 0, "blobs_written": 0}

    client = AsyncMock()
    client.post = AsyncMock(
        side_effect=[
            _make_response(200, lease_body),  # /atomic-lease?scope=explicit -> 200
            _make_response(200, submit_body),  # /atomic-submit -> 200
        ]
    )

    pool = AsyncMock()
    pool.evaluate_nodes_with_pv = AsyncMock(return_value=(100, None, "e2e4", "e2e4 e7e5"))

    outcome = await _run_cycle(
        client=client,
        pool=pool,
        sf_version="sf16",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )
    assert outcome.did_work is True

    # First call: /atomic-lease with scope=explicit
    first_call = client.post.call_args_list[0]
    assert first_call == call(
        "/api/eval/remote/atomic-lease",
        params={"scope": "explicit", "worker_schema_version": WORKER_SCHEMA_VERSION},
    )

    # Second call: /atomic-submit
    second_call = client.post.call_args_list[1]
    assert second_call.args[0] == "/api/eval/remote/atomic-submit"

    # /entry-lease must never be called on the busy tier-1 path
    called_urls = [c.args[0] for c in client.post.call_args_list]
    assert "/api/eval/remote/entry-lease" not in called_urls


async def test_ladder_entry_ply_on_explicit_204() -> None:
    """When atomic-lease scope=explicit returns 204, the cycle calls /entry-lease.

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
            _make_response(204),  # /atomic-lease?scope=explicit -> 204
            _make_response(200, entry_body),  # /entry-lease -> 200
            _make_response(200, entry_submit_body),  # /entry-submit -> 200
        ]
    )

    pool = AsyncMock()
    pool.evaluate = AsyncMock(return_value=(50, None))  # depth-15 returns (cp, mate)

    outcome = await _run_cycle(
        client=client,
        pool=pool,
        sf_version="sf16",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )
    assert outcome.did_work is True

    called_urls = [c.args[0] for c in client.post.call_args_list]
    assert called_urls[0] == "/api/eval/remote/atomic-lease"
    assert called_urls[1] == "/api/eval/remote/entry-lease"
    assert called_urls[2] == "/api/eval/remote/entry-submit"

    # Must NOT call atomic-lease?scope=idle -- entry-ply was served
    lease_calls = [
        c for c in client.post.call_args_list if c.args[0] == "/api/eval/remote/atomic-lease"
    ]
    assert len(lease_calls) == 1, "scope=idle should not be called when entry-ply returned work"


async def test_ladder_falls_to_idle_when_entry_lease_204() -> None:
    """When scope=explicit 204 and /entry-lease 204, the cycle falls to scope=idle
    (also via /atomic-lease, rung 3).
    """
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
    submit_body = {"game_id": 99, "flaws_written": 0, "blobs_written": 0}

    client = AsyncMock()
    client.post = AsyncMock(
        side_effect=[
            _make_response(204),  # /atomic-lease?scope=explicit -> 204
            _make_response(204),  # /entry-lease -> 204
            _make_response(200, idle_body),  # /atomic-lease?scope=idle -> 200
            _make_response(200, submit_body),  # /atomic-submit -> 200
        ]
    )

    pool = AsyncMock()
    pool.evaluate_nodes_with_pv = AsyncMock(return_value=(0, None, "e1e2", "e1e2"))

    outcome = await _run_cycle(
        client=client,
        pool=pool,
        sf_version="sf16",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )
    assert outcome.did_work is True

    called_urls = [c.args[0] for c in client.post.call_args_list]
    assert called_urls[0] == "/api/eval/remote/atomic-lease"  # scope=explicit
    assert called_urls[1] == "/api/eval/remote/entry-lease"
    assert called_urls[2] == "/api/eval/remote/atomic-lease"  # scope=idle
    assert called_urls[3] == "/api/eval/remote/atomic-submit"

    # Confirm the idle atomic-lease call used scope=idle param
    idle_lease_call = client.post.call_args_list[2]
    assert idle_lease_call == call(
        "/api/eval/remote/atomic-lease",
        params={"scope": "idle", "worker_schema_version": WORKER_SCHEMA_VERSION},
    )


# ─── Depth-15 eval path assertion ─────────────────────────────────────────────


async def test_entry_eval_uses_depth15_not_evaluate_nodes_with_pv() -> None:
    """_eval_entry_positions calls pool.evaluate (depth-15), never evaluate_nodes_with_pv.

    Critical: mixing modes makes entry-ply 10x slower.
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


# ─── tier-4 flaw-blob drain rung tests ─────────────────────


async def test_ladder_flaw_blob_on_all_tier123_204() -> None:
    """When all tier-1/2/3 rungs return 204, the worker reaches rung 4 (flaw-blob-lease).

    On a 200 flaw-blob-lease response, the cycle evaluates at MultiPV=2 and POSTs to
    /flaw-blob-submit. Both URLs must appear in the client.post call list.
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
    # evaluate_nodes_multipv2 returns 7-tuple (blob rung keeps MultiPV-2)
    pool.evaluate_nodes_multipv2 = AsyncMock(
        return_value=(100, None, "e2e4", "e2e4 e7e5", 50, None, "d2d4")
    )

    outcome = await _run_cycle(
        client=client,
        pool=pool,
        sf_version="sf18",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )
    assert outcome.did_work is True

    called_urls = [c.args[0] for c in client.post.call_args_list]
    assert "/api/eval/remote/flaw-blob-lease" in called_urls, (
        "rung-4 /flaw-blob-lease was not called after all tier-1/2/3 returned 204"
    )
    assert (
        call(
            "/api/eval/remote/flaw-blob-lease",
            params={"worker_schema_version": WORKER_SCHEMA_VERSION},
        )
        in client.post.call_args_list
    ), "rung-4 must send worker_schema_version (server gates the lane on it)"
    assert "/api/eval/remote/flaw-blob-submit" in called_urls, (
        "/flaw-blob-submit was not POSTed after a 200 from /flaw-blob-lease"
    )


async def test_ladder_all_queues_empty_sleeps_once() -> None:
    """When all five tiers (including rung-4 flaw-blob and rung-5 bestmove) return
    204, the worker sleeps exactly once.

    Regression guard: rungs 4/5 must not introduce a double-sleep.
    """
    client = AsyncMock()
    client.post = AsyncMock(
        side_effect=[
            _make_response(204),  # /lease?scope=explicit
            _make_response(204),  # /entry-lease
            _make_response(204),  # /lease?scope=idle
            _make_response(204),  # /flaw-blob-lease
            _make_response(204),  # /bestmove-lease
        ]
    )
    pool = AsyncMock()

    with patch("scripts.remote_eval_worker.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        outcome = await _run_cycle(
            client=client,
            pool=pool,
            sf_version="sf18",
            idle_sleep=1.0,
            dry_run=False,
            loop=False,
        )
        mock_sleep.assert_awaited_once_with(1.0)
    assert outcome.did_work is False

    # Confirm rungs 4 and 5 were actually reached (not just an earlier-rung sleep)
    called_urls = [c.args[0] for c in client.post.call_args_list]
    assert "/api/eval/remote/flaw-blob-lease" in called_urls, (
        "rung-4 /flaw-blob-lease was not called — sleep may have fired from rung 3 tail"
    )
    assert "/api/eval/remote/bestmove-lease" in called_urls, (
        "rung-5 /bestmove-lease was not called — sleep may have fired from rung 4 tail"
    )


async def test_eval_flaw_blob_positions_maps_indices_correctly() -> None:
    """_eval_flaw_blob_positions maps r[0]/r[1]/r[4]/r[5]/r[6]; never r[2]/r[3].

    evaluate_nodes_multipv2 returns (eval_cp, eval_mate, best_move, pv,
    second_cp, second_mate, second_uci). Fields r[2] (best_move) and r[3] (pv)
    must NOT appear in the output dict. Token is echoed unchanged.
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


# ─── MultiPV-1 full-ply reduction + HTTP_TIMEOUT_S tests ──


def test_http_timeout_s_restored_to_30() -> None:
    """HTTP_TIMEOUT_S must be 30.0 — the former 120s stopgap is gone.

    The live /submit no longer calls any engine, so the p99 latency
    drops well below 30s. 30s provides a 10x safety margin.
    """
    assert HTTP_TIMEOUT_S == 30.0, (
        f"HTTP_TIMEOUT_S is {HTTP_TIMEOUT_S}, expected 30.0. "
        "Remove the SEED-071 stopgap comment and restore the original value."
    )


async def test_eval_positions_uses_multipv1_no_second_best() -> None:
    """_eval_positions (full-ply pass) uses evaluate_nodes_with_pv (4-tuple, MultiPV-1).

    Second-best fields (second_cp/second_mate/second_uci) must be absent from the output
    dict — SubmitEval no longer carries them. The tier-4 blob rung
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
    # Second-best keys must be absent (SubmitEval dropped them)
    assert "second_cp" not in r, "second_cp must not appear in full-ply output (D-03)"
    assert "second_mate" not in r, "second_mate must not appear in full-ply output (D-03)"
    assert "second_uci" not in r, "second_uci must not appear in full-ply output (D-03)"


# ─── bounded worker-side retry of timed-out positions ────


def test_is_engine_failure_true_only_for_all_none_score() -> None:
    """_is_engine_failure flags a result iff BOTH eval_cp and eval_mate are None.

    A mate-scored result (eval_cp None, eval_mate set) must NEVER be treated as
    a failure — only the genuine all-None engine-failure tuple qualifies.
    """
    assert _is_engine_failure((None, None, None, None)) is True
    assert _is_engine_failure((None, None, None, None, None, None, None)) is True
    assert _is_engine_failure((100, None, "e2e4", "e2e4")) is False
    assert _is_engine_failure((None, 3, None, None)) is False, (
        "a mate-only result (eval_cp=None, eval_mate=3) must not be flagged a failure"
    )


async def test_eval_positions_no_retry_when_all_succeed() -> None:
    """All positions succeed on the first search -> exactly one engine call per
    position, and the retry pass issues ZERO extra calls."""
    pool = AsyncMock()
    pool.evaluate_nodes_with_pv = AsyncMock(
        side_effect=[(10, None, "e2e4", "e2e4"), (20, None, "d7d5", "d7d5")]
    )
    positions: list[dict[str, object]] = [
        {"ply": 0, "fen": chess.STARTING_FEN, "is_terminal": False},
        {"ply": 1, "fen": chess.STARTING_FEN, "is_terminal": False},
    ]

    results = await _eval_positions(pool, positions)

    assert pool.evaluate_nodes_with_pv.call_count == 2, "no retry calls when nothing failed"
    assert [r["eval_cp"] for r in results] == [10, 20]


async def test_eval_positions_retries_failed_position_and_uses_success() -> None:
    """A position whose first search fails (all-None) is retried once at
    EVAL_RETRY_TIMEOUT_S; a successful retry replaces the failure in the output."""
    pool = AsyncMock()
    pool.evaluate_nodes_with_pv = AsyncMock(
        side_effect=[
            (None, None, None, None),  # first pass: failure
            (50, None, "g1f3", "g1f3"),  # retry: success
        ]
    )
    positions: list[dict[str, object]] = [
        {"ply": 0, "fen": chess.STARTING_FEN, "is_terminal": False},
    ]

    results = await _eval_positions(pool, positions)

    assert pool.evaluate_nodes_with_pv.call_count == 2, "exactly one retry call"
    retry_call = pool.evaluate_nodes_with_pv.call_args_list[1]
    assert retry_call.kwargs.get("timeout_s") == EVAL_RETRY_TIMEOUT_S
    assert results[0]["eval_cp"] == 50, "the successful retry result must replace the failure"


async def test_eval_positions_retry_fails_twice_stays_a_hole() -> None:
    """A retry that also fails leaves the all-None result in place — still
    submitted as a hole (as before), never garbage, never dropped."""
    pool = AsyncMock()
    pool.evaluate_nodes_with_pv = AsyncMock(
        side_effect=[
            (None, None, None, None),  # first pass: failure
            (None, None, None, None),  # retry: also fails
        ]
    )
    positions: list[dict[str, object]] = [
        {"ply": 0, "fen": chess.STARTING_FEN, "is_terminal": False},
    ]

    results = await _eval_positions(pool, positions)

    assert pool.evaluate_nodes_with_pv.call_count == 2
    assert results[0]["eval_cp"] is None
    assert results[0]["eval_mate"] is None


async def test_eval_positions_mate_only_result_never_retried() -> None:
    """A mate-scored result (eval_cp None, eval_mate set) must never trigger a
    retry — _is_engine_failure's mate-aware guard prevents a wasted call."""
    pool = AsyncMock()
    pool.evaluate_nodes_with_pv = AsyncMock(return_value=(None, 3, "a1a8", "a1a8"))
    positions: list[dict[str, object]] = [
        {"ply": 0, "fen": chess.STARTING_FEN, "is_terminal": False},
    ]

    results = await _eval_positions(pool, positions)

    assert pool.evaluate_nodes_with_pv.call_count == 1, "a mate result must not be retried"
    assert results[0]["eval_mate"] == 3


async def test_eval_positions_retry_capped_at_budget() -> None:
    """More failed positions than the caller's remaining budget -> only
    `budget.remaining` are retried, the rest keep their all-None result, and the
    budget is fully spent (never over-spent)."""
    n_positions = EVAL_RETRY_MAX_POSITIONS + 3
    pool = AsyncMock()
    # First pass: every position fails. Retry pass: every retried position
    # succeeds, so the number of successes in the output == the number retried.
    pool.evaluate_nodes_with_pv = AsyncMock(
        side_effect=(
            [(None, None, None, None)] * n_positions
            + [(1, None, "e2e4", "e2e4")] * EVAL_RETRY_MAX_POSITIONS
        )
    )
    positions: list[dict[str, object]] = [
        {"ply": p, "fen": chess.STARTING_FEN, "is_terminal": False} for p in range(n_positions)
    ]
    budget = _RetryBudget(remaining=EVAL_RETRY_MAX_POSITIONS)

    results = await _eval_positions(pool, positions, budget)

    assert pool.evaluate_nodes_with_pv.call_count == n_positions + EVAL_RETRY_MAX_POSITIONS
    succeeded = sum(1 for r in results if r["eval_cp"] is not None)
    assert succeeded == EVAL_RETRY_MAX_POSITIONS, "only budget.remaining positions get retried"
    assert budget.remaining == 0


async def test_eval_atomic_blob_nodes_retries_failed_position() -> None:
    """The tier-4 blob rung (_eval_atomic_blob_nodes) is also retried at
    EVAL_RETRY_TIMEOUT_S on a failed position; a successful retry replaces the
    failure and the original token is preserved."""
    pool = AsyncMock()
    pool.evaluate_nodes_multipv2 = AsyncMock(
        side_effect=[
            (None, None, None, None, None, None, None),  # first pass: failure
            (10, None, "e2e4", "e2e4", 5, None, "d2d4"),  # retry: success
        ]
    )
    boards = [chess.Board()]
    tokens = ["1:missed:0"]

    results = await _eval_atomic_blob_nodes(pool, boards, tokens)

    assert pool.evaluate_nodes_multipv2.call_count == 2
    retry_call = pool.evaluate_nodes_multipv2.call_args_list[1]
    assert retry_call.kwargs.get("timeout_s") == EVAL_RETRY_TIMEOUT_S
    assert results[0]["token"] == "1:missed:0"
    assert results[0]["best_cp"] == 10


async def test_retry_timed_out_budget_shared_across_sequential_calls() -> None:
    """A single `_RetryBudget` object shared across two SEQUENTIAL `_retry_timed_out`
    calls (mirroring `_eval_atomic_game`'s three passes sharing one budget) caps
    the TOTAL retried across both calls at the budget's starting value, never per-call.
    """
    budget = _RetryBudget(remaining=EVAL_RETRY_MAX_POSITIONS)

    async def always_fails(board: chess.Board) -> tuple[None, None, None, None]:
        return (None, None, None, None)

    # Call 1: EVAL_RETRY_MAX_POSITIONS failures -- would exhaust a fresh budget.
    boards_1 = [chess.Board() for _ in range(EVAL_RETRY_MAX_POSITIONS)]
    results_1 = [(None, None, None, None)] * EVAL_RETRY_MAX_POSITIONS
    merged_1 = await _retry_timed_out(always_fails, boards_1, results_1, budget)
    assert budget.remaining == 0, "call 1 alone must exhaust the shared budget"
    assert all(_is_engine_failure(r) for r in merged_1)

    # Call 2: budget is already exhausted -- must issue ZERO engine calls.
    call_2_spy_count = 0

    async def spy_analyse(
        board: chess.Board,
    ) -> tuple[int | None, int | None, str | None, str | None]:
        nonlocal call_2_spy_count
        call_2_spy_count += 1
        return (100, None, "e2e4", "e2e4")

    boards_2 = [chess.Board()]
    results_2 = [(None, None, None, None)]
    merged_2 = await _retry_timed_out(spy_analyse, boards_2, results_2, budget)
    assert call_2_spy_count == 0, "an exhausted shared budget must issue zero retry calls"
    assert merged_2 == results_2, "results are returned unchanged when the budget is exhausted"


async def test_eval_atomic_game_passes_identical_budget_to_all_three_passes() -> None:
    """`_eval_atomic_game` constructs ONE `_RetryBudget` and passes
    the SAME object (not equal copies) to `_eval_positions`, `_eval_atomic_blob_nodes`,
    and `_eval_targeted_second_best` — the load-bearing structural guarantee behind
    the per-cycle (not per-pass) cap.
    """
    import scripts.remote_eval_worker as worker_module

    captured_budgets: list[object] = []

    async def fake_eval_positions(
        pool: object, positions: object, budget: object = None
    ) -> list[dict[str, object]]:
        captured_budgets.append(budget)
        return [{"ply": 0, "eval_cp": 0, "eval_mate": None, "best_move": None, "pv": None}]

    async def fake_eval_atomic_blob_nodes(
        pool: object, boards: object, tokens: object, budget: object = None
    ) -> list[dict[str, object]]:
        captured_budgets.append(budget)
        return []

    async def fake_eval_targeted_second_best(
        pool: object, positions: object, evals: object, budget: object = None
    ) -> list[dict[str, object]]:
        captured_budgets.append(budget)
        return []

    with (
        patch.object(worker_module, "_eval_positions", fake_eval_positions),
        patch.object(worker_module, "_hint_flaw_plies", return_value={0}),
        patch.object(
            worker_module,
            "_build_blob_walk_targets",
            return_value=([chess.Board()], ["0:missed:0"]),
        ),
        patch.object(worker_module, "_eval_atomic_blob_nodes", fake_eval_atomic_blob_nodes),
        patch.object(worker_module, "_eval_targeted_second_best", fake_eval_targeted_second_best),
    ):
        await worker_module._eval_atomic_game(AsyncMock(), [{"ply": 0, "fen": chess.STARTING_FEN}])

    assert len(captured_budgets) == 3, "all three passes must receive a budget argument"
    assert captured_budgets[0] is not None
    assert captured_budgets[0] is captured_budgets[1] is captured_budgets[2], (
        "all three passes must share the IDENTICAL budget object, not equal copies"
    )


async def test_eval_targeted_second_best_retries_before_dropping() -> None:
    """The retry runs BEFORE the drop-on-failure filter -- a
    position whose first targeted search fails but whose retry succeeds is
    INCLUDED in second_best, not dropped."""
    positions: list[dict[str, object]] = [
        {"ply": 0, "fen": chess.STARTING_FEN, "is_terminal": False, "move_uci": "e2e4"},
    ]
    evals: list[dict[str, object]] = [
        {"ply": 0, "eval_cp": 0, "eval_mate": None, "best_move": "e2e4", "pv": None},
    ]

    pool = AsyncMock()
    pool.evaluate_nodes_multipv2 = AsyncMock(
        side_effect=[
            (None, None, None, None, None, None, None),  # first targeted search: fails
            (0, None, "e2e4", "e2e4", 5, None, "d2d4"),  # retry: succeeds
        ]
    )

    second_best = await _eval_targeted_second_best(pool, positions, evals)

    assert pool.evaluate_nodes_multipv2.call_count == 2, "exactly one retry call"
    assert second_best == [{"ply": 0, "second_cp": 5, "second_mate": None, "second_uci": "d2d4"}], (
        "a retry-recovered candidate must be included, not dropped"
    )


async def test_fresh_retry_budget_seeded_from_max_positions() -> None:
    """_fresh_retry_budget() constructs a budget seeded from EVAL_RETRY_MAX_POSITIONS
    — the default a standalone caller (or a test omitting `budget`) gets."""
    budget = _fresh_retry_budget()
    assert budget.remaining == EVAL_RETRY_MAX_POSITIONS


# ─── Atomic eval+blob rung tests ─────────────────
#
# A 3-position synthetic mini-game (ply 0/1/2) used ONLY by tests that pass an
# explicit flaw_plies set directly (test_build_blob_walk_targets_*) or that
# don't inspect the hinted plies at all (test_eval_atomic_game_full_ply_pass_
# stays_multipv1). FENs are all the starting position (board legality of the
# hint/token machinery does not depend on the real game — pv=None everywhere
# keeps _walk_pv_boards' walk a single node).

_ATOMIC_POSITIONS: list[dict[str, object]] = [
    {"ply": 0, "fen": chess.STARTING_FEN, "is_terminal": False},
    {"ply": 1, "fen": chess.STARTING_FEN, "is_terminal": False},
    {"ply": 2, "fen": chess.STARTING_FEN, "is_terminal": True},
]
_ATOMIC_EVALS: list[dict[str, object]] = [
    {"ply": 0, "eval_cp": 0, "eval_mate": None, "best_move": "e2e4", "pv": None},
    {"ply": 1, "eval_cp": 600, "eval_mate": None, "best_move": "d7d5", "pv": None},
    {"ply": 2, "eval_cp": 600, "eval_mate": None, "best_move": "g1f3", "pv": None},
]

# `evals` is POSITION-keyed (the eval OF the board
# AT a given ply), but _run_all_moves_pass — and therefore _hint_flaw_plies —
# expects ROW-keyed/POST-MOVE values: hint row `m` must hold pos_eval[m + 1],
# exactly matching the server's _post_move_eval convention
# (app/services/eval_drain.py). The fixture below is NOT arbitrary: it reuses
# the EXACT eval values from _BLUNDER_SUBMIT_EVALS_142 / _SIX_PLY_PGN_142
# (tests/test_eval_worker_endpoints.py) — a 6-ply game where /atomic-submit's
# SERVER-SIDE classify_game_flaws independently confirms a real blunder at
# ply=2 for these SAME values
# (test_atomic_submit_gates_tactic_tag_and_stamps_both_markers asserts
# flaw_ply == 2 through the authoritative server path). Reusing that
# cross-validated fixture here proves the local hint agrees with the server's
# own classify, rather than locking in whatever the local code happens to
# compute.
_HINTED_BLUNDER_POSITIONS: list[dict[str, object]] = [
    {"ply": p, "fen": chess.STARTING_FEN, "is_terminal": p == 6} for p in range(7)
]
_HINTED_BLUNDER_EVALS: list[dict[str, object]] = [
    {"ply": 0, "eval_cp": 0, "eval_mate": None, "best_move": None, "pv": None},
    {"ply": 1, "eval_cp": 20, "eval_mate": None, "best_move": "e2e4", "pv": None},
    {"ply": 2, "eval_cp": 30, "eval_mate": None, "best_move": "g1f3", "pv": None},
    {"ply": 3, "eval_cp": -500, "eval_mate": None, "best_move": "b8c6", "pv": None},
    {"ply": 4, "eval_cp": -480, "eval_mate": None, "best_move": "f1c4", "pv": None},
    {"ply": 5, "eval_cp": 60, "eval_mate": None, "best_move": "f8c5", "pv": None},
    {"ply": 6, "eval_cp": 30, "eval_mate": None, "best_move": None, "pv": None},
]


def test_hint_flaw_plies_selects_mistake_and_blunder_only() -> None:
    """_hint_flaw_plies runs _run_all_moves_pass over lightweight in-memory
    GamePosition objects, POST-MOVE shifted by one, and keeps only
    mistake/blunder plies.

    ply=2 (white, ES ~53% -> ~7%) is the real blunder in _HINTED_BLUNDER_EVALS
    — independently confirmed by the server's own classify_game_flaws for
    these same values (see the fixture's docstring above). Every other ply
    has a small or zero ES change and must be excluded.
    """
    assert _hint_flaw_plies(_HINTED_BLUNDER_EVALS) == {2}


def test_hint_flaw_plies_empty_for_no_evals() -> None:
    """An empty evals list yields an empty hint set (no crash on an empty lease)."""
    assert _hint_flaw_plies([]) == set()


def test_build_blob_walk_targets_tokens_missed_and_allowed() -> None:
    """Walks the missed line at flaw_ply and the allowed line at flaw_ply + 1,
    token-keyed per the "{flaw_ply}:{line}:{node_k}" scheme.
    """
    boards, tokens = _build_blob_walk_targets(_ATOMIC_POSITIONS, _ATOMIC_EVALS, {1})

    assert tokens == ["1:missed:0", "1:allowed:0"]
    assert len(boards) == 2
    assert all(isinstance(b, chess.Board) for b in boards)


def test_build_blob_walk_targets_skips_line_with_no_start_fen() -> None:
    """A flaw_ply at the game's last ply has no allowed-line start FEN (flaw_ply + 1
    does not exist in the lease payload) -- skipped, not crashed. The server
    independently re-derives this as a sentinel (never trusts
    which lines this worker could walk).
    """
    positions: list[dict[str, object]] = [
        {"ply": 0, "fen": chess.STARTING_FEN, "is_terminal": False},
        {"ply": 1, "fen": chess.STARTING_FEN, "is_terminal": True},
    ]
    evals: list[dict[str, object]] = [
        {"ply": 0, "eval_cp": 0, "eval_mate": None, "best_move": "e2e4", "pv": None},
        {"ply": 1, "eval_cp": 600, "eval_mate": None, "best_move": "d7d5", "pv": None},
    ]

    boards, tokens = _build_blob_walk_targets(positions, evals, {1})

    assert tokens == ["1:missed:0"]
    assert len(boards) == 1


async def test_eval_atomic_game_full_ply_pass_stays_multipv1() -> None:
    """The full-ply pass inside _eval_atomic_game uses MultiPV-1 (evaluate_nodes_with_pv),
    never MultiPV-2, for the /atomic-submit evals list (the full-ply MultiPV-1
    invariant holds under the atomic rung — mirrors
    test_eval_positions_uses_multipv1_no_second_best).
    """
    pool = AsyncMock()
    pool.evaluate_nodes_with_pv = AsyncMock(
        side_effect=[(0, None, "e2e4", None), (600, None, "d7d5", None), (600, None, "g1f3", None)]
    )
    pool.evaluate_nodes_multipv2 = AsyncMock(
        return_value=(0, None, "a2a3", "a2a3", 0, None, "b2b3")
    )

    evals, _blob_nodes, _second_best = await _eval_atomic_game(pool, _ATOMIC_POSITIONS)

    assert pool.evaluate_nodes_with_pv.call_count == 3
    for r in evals:
        assert "second_cp" not in r, "second_cp must not appear in the full-ply evals (D-03)"
        assert "second_mate" not in r, "second_mate must not appear in the full-ply evals (D-03)"
        assert "second_uci" not in r, "second_uci must not appear in the full-ply evals (D-03)"


async def test_eval_atomic_game_hints_and_blobs_flaw_plies_only() -> None:
    """_eval_atomic_game: full-ply MultiPV-1 pass -> local hint -> MultiPV-2 blobs
    only for the hinted flaw ply (mistake/blunder), token-keyed ("{flaw_ply}:{line}:{node_k}").

    Uses _HINTED_BLUNDER_POSITIONS/_HINTED_BLUNDER_EVALS (cross-validated
    fixture, see the fixture docstring): only flaw_ply=2 is hinted (the real
    blunder); every other ply has a small/zero ES change and must NOT produce
    any blob node or engine call.
    """
    pool = AsyncMock()
    pool.evaluate_nodes_with_pv = AsyncMock(
        side_effect=[
            (int(cast(int, e["eval_cp"])), None, e["best_move"], None)
            for e in _HINTED_BLUNDER_EVALS
        ]
    )
    pool.evaluate_nodes_multipv2 = AsyncMock(
        side_effect=[
            (10, None, "a2a3", "a2a3", 5, None, "b2b3"),
            (20, None, "b2b3", "b2b3", 15, None, "c2c3"),
        ]
    )

    evals, blob_nodes, _second_best = await _eval_atomic_game(pool, _HINTED_BLUNDER_POSITIONS)

    assert len(evals) == 7
    assert pool.evaluate_nodes_multipv2.call_count == 2

    tokens = [n["token"] for n in blob_nodes]
    assert tokens == ["2:missed:0", "2:allowed:0"], tokens

    missed_node = blob_nodes[0]
    assert missed_node["best_cp"] == 10
    assert missed_node["best_mate"] is None
    assert missed_node["second_cp"] == 5
    assert missed_node["second_mate"] is None
    assert missed_node["second_uci"] == "b2b3"


async def test_eval_atomic_game_no_hinted_flaws_skips_multipv2_entirely() -> None:
    """When the local hint selects zero flaw plies, evaluate_nodes_multipv2 is
    never called at all (no gather over an empty board list — cheap idle path).
    """
    flat_evals: list[dict[str, object]] = [
        {"ply": 0, "eval_cp": 0, "eval_mate": None, "best_move": "e2e4", "pv": None},
        {"ply": 1, "eval_cp": 0, "eval_mate": None, "best_move": "d7d5", "pv": None},
    ]
    positions: list[dict[str, object]] = [
        {"ply": 0, "fen": chess.STARTING_FEN, "is_terminal": False},
        {"ply": 1, "fen": chess.STARTING_FEN, "is_terminal": True},
    ]

    pool = AsyncMock()
    pool.evaluate_nodes_with_pv = AsyncMock(
        side_effect=[(e["eval_cp"], None, "e2e4", None) for e in flat_evals]
    )
    pool.evaluate_nodes_multipv2 = AsyncMock()

    evals, blob_nodes, second_best = await _eval_atomic_game(pool, positions)

    assert len(evals) == 2
    assert blob_nodes == []
    assert second_best == []
    pool.evaluate_nodes_multipv2.assert_not_called()


async def test_atomic_submit_payload_shape_and_schema_version() -> None:
    """The /atomic-submit body carries evals + blob_nodes together with
    worker_schema_version, matching the AtomicSubmitRequest schema, and
    blob_nodes contains tokens only for the hinted flaw ply.
    """
    lease_body = {
        "game_id": 55,
        "user_id": 9,
        "is_lichess_eval_game": False,
        "positions": _HINTED_BLUNDER_POSITIONS,
        "leased_at": "2026-07-01T10:00:00Z",
        "job_id": "job-atomic-1",
    }
    submit_body = {"game_id": 55, "flaws_written": 1, "blobs_written": 1}

    client = AsyncMock()
    client.post = AsyncMock(
        side_effect=[
            _make_response(200, lease_body),  # /atomic-lease
            _make_response(200, submit_body),  # /atomic-submit
        ]
    )

    pool = AsyncMock()
    pool.evaluate_nodes_with_pv = AsyncMock(
        side_effect=[
            (int(cast(int, e["eval_cp"])), None, e["best_move"], None)
            for e in _HINTED_BLUNDER_EVALS
        ]
    )
    pool.evaluate_nodes_multipv2 = AsyncMock(
        side_effect=[
            (10, None, "a2a3", "a2a3", 5, None, "b2b3"),
            (20, None, "b2b3", "b2b3", 15, None, "c2c3"),
        ]
    )

    await _run_cycle(
        client=client, pool=pool, sf_version="sf18", idle_sleep=1.0, dry_run=False, loop=False
    )

    submit_call = client.post.call_args_list[1]
    assert submit_call.args[0] == "/api/eval/remote/atomic-submit"
    body = submit_call.kwargs["json"]
    assert body["game_id"] == 55
    assert body["sf_version"] == "sf18"
    assert body["worker_schema_version"] == WORKER_SCHEMA_VERSION
    assert body["job_id"] == "job-atomic-1"
    assert len(body["evals"]) == 7
    assert [n["token"] for n in body["blob_nodes"]] == ["2:missed:0", "2:allowed:0"]
    # _HINTED_BLUNDER_POSITIONS carries no move_uci -- nothing to target.
    assert body["second_best"] == []


# ─── Version bump + targeted second-best re-search ──

_TARGETED_SECOND_BEST_POSITIONS: list[dict[str, object]] = [
    {"ply": 0, "fen": chess.STARTING_FEN, "is_terminal": False, "move_uci": "e2e4"},
    {"ply": 1, "fen": chess.STARTING_FEN, "is_terminal": False, "move_uci": "d7d5"},
    {"ply": 2, "fen": chess.STARTING_FEN, "is_terminal": True, "move_uci": None},
]


def test_worker_schema_version_is_3() -> None:
    """WORKER_SCHEMA_VERSION bumped 2 -> 3 (SEED-261112-s4v: keeps the last exact info
    line). The shipped worker must always clear the server's lease gate."""
    assert WORKER_SCHEMA_VERSION == 3
    assert WORKER_SCHEMA_VERSION >= WORKER_SCHEMA_VERSION_MIN


async def test_eval_atomic_game_targeted_second_best_only_played_best() -> None:
    """The targeted MultiPV-2 re-search runs ONLY for plies where the
    worker's own MultiPV-1 best move equals the leased `move_uci` (the move actually
    played). A played != best ply (ply 1: best "g1f3" != played "d7d5") and the
    terminal donor (ply 2: move_uci=None) produce NO second_best entry -- mirrors
    the server-side played==best gate this data feeds. The full-ply pass stays
    MultiPV-1 (unchanged).
    """
    pool = AsyncMock()
    pool.evaluate_nodes_with_pv = AsyncMock(
        side_effect=[
            (0, None, "e2e4", None),  # ply 0: best == played ("e2e4") -> candidate
            (0, None, "g1f3", None),  # ply 1: best != played ("d7d5") -> not a candidate
            (0, None, None, None),  # ply 2: terminal donor, move_uci=None -> not a candidate
        ]
    )
    pool.evaluate_nodes_multipv2 = AsyncMock(
        return_value=(0, None, "e2e4", "e2e4 d7d5", 5, None, "d2d4")
    )

    evals, blob_nodes, second_best = await _eval_atomic_game(pool, _TARGETED_SECOND_BEST_POSITIONS)

    assert pool.evaluate_nodes_with_pv.call_count == 3, "full-ply pass must stay MultiPV-1"
    assert blob_nodes == [], "zero eval deltas must not hint any flaw ply"
    assert len(evals) == 3
    assert pool.evaluate_nodes_multipv2.call_count == 1, (
        "evaluate_nodes_multipv2 must be called exactly once -- only for the played==best ply"
    )
    assert second_best == [{"ply": 0, "second_cp": 5, "second_mate": None, "second_uci": "d2d4"}]


async def test_eval_atomic_game_targeted_second_best_drops_failed_search() -> None:
    """A failed targeted search (engine failure -> the all-None 7-tuple) drops that
    ply from second_best rather than submitting garbage or failing the whole submit
    -- the server's own fallback covers the gap for that ply.
    """
    pool = AsyncMock()
    pool.evaluate_nodes_with_pv = AsyncMock(
        side_effect=[
            (0, None, "e2e4", None),
            (0, None, "g1f3", None),
            (0, None, None, None),
        ]
    )
    pool.evaluate_nodes_multipv2 = AsyncMock(
        return_value=(None, None, None, None, None, None, None)
    )

    _evals, _blob_nodes, second_best = await _eval_atomic_game(
        pool, _TARGETED_SECOND_BEST_POSITIONS
    )

    assert second_best == [], "a failed targeted search must drop the ply, not submit garbage"


# ─── rung-5 tier-4b best-move backfill tests ───────────


async def test_ladder_bestmove_lease_only_after_flaw_blob_204() -> None:
    """Rung 5 (/bestmove-lease) is reached ONLY after rung 4 (/flaw-blob-lease)
    returns 204 -- blob backfill (server tier 4) must always precede
    best-move backfill (server tier 5 / TIER_BESTMOVE_BACKFILL) on the worker's
    ladder, mirroring the server's own tier priority (the worker never sees tier
    numbers directly, only HTTP status codes).
    """
    bestmove_lease_body = {
        "game_id": 88,
        "positions": [
            {"ply": 4, "fen": chess.STARTING_FEN},
            {"ply": 6, "fen": chess.STARTING_FEN},
        ],
        "leased_at": "2026-07-17T10:00:00Z",
    }
    submit_body = {"game_id": 88, "rows_written": 2}

    client = AsyncMock()
    client.post = AsyncMock(
        side_effect=[
            _make_response(204),  # /atomic-lease?scope=explicit
            _make_response(204),  # /entry-lease
            _make_response(204),  # /atomic-lease?scope=idle
            _make_response(204),  # /flaw-blob-lease
            _make_response(200, bestmove_lease_body),  # /bestmove-lease
            _make_response(200, submit_body),  # /bestmove-submit
        ]
    )

    pool = AsyncMock()
    pool.evaluate_nodes_multipv2 = AsyncMock(
        return_value=(0, None, "e2e4", "e2e4", 5, None, "d2d4")
    )

    outcome = await _run_cycle(
        client=client, pool=pool, sf_version="sf18", idle_sleep=1.0, dry_run=False, loop=False
    )
    assert outcome.did_work is True

    called_urls = [c.args[0] for c in client.post.call_args_list]
    blob_idx = called_urls.index("/api/eval/remote/flaw-blob-lease")
    bestmove_idx = called_urls.index("/api/eval/remote/bestmove-lease")
    assert bestmove_idx > blob_idx, (
        "rung-5 /bestmove-lease must be called strictly after rung-4 /flaw-blob-lease"
    )
    assert "/api/eval/remote/bestmove-submit" in called_urls
    for lease_url in ("flaw-blob-lease", "bestmove-lease"):
        assert (
            call(
                f"/api/eval/remote/{lease_url}",
                params={"worker_schema_version": WORKER_SCHEMA_VERSION},
            )
            in client.post.call_args_list
        ), f"{lease_url} must send worker_schema_version"


async def test_handle_bestmove_response_submits_n_entries_no_atomic_submit() -> None:
    """A 200 /bestmove-lease with N candidate plies evaluates each at MultiPV=2 ONLY
    (no full pass, no blob walk) and POSTs exactly N per-ply runner-up entries to
    /bestmove-submit; /atomic-submit is never called.
    """
    bestmove_lease_body = {
        "game_id": 101,
        "positions": [
            {"ply": 4, "fen": chess.STARTING_FEN},
            {"ply": 8, "fen": chess.STARTING_FEN},
            {"ply": 12, "fen": chess.STARTING_FEN},
        ],
        "leased_at": "2026-07-17T10:00:00Z",
    }
    submit_body = {"game_id": 101, "rows_written": 3}

    client = AsyncMock()
    client.post = AsyncMock(
        side_effect=[
            _make_response(204),  # /atomic-lease?scope=explicit
            _make_response(204),  # /entry-lease
            _make_response(204),  # /atomic-lease?scope=idle
            _make_response(204),  # /flaw-blob-lease
            _make_response(200, bestmove_lease_body),  # /bestmove-lease
            _make_response(200, submit_body),  # /bestmove-submit
        ]
    )

    pool = AsyncMock()
    pool.evaluate_nodes_multipv2 = AsyncMock(
        side_effect=[
            (0, None, "e2e4", "e2e4", 10, None, "d2d4"),
            (0, None, "g1f3", "g1f3", 20, None, "c2c4"),
            (0, None, "b1c3", "b1c3", 30, None, "f2f4"),
        ]
    )

    await _run_cycle(
        client=client, pool=pool, sf_version="sf18", idle_sleep=1.0, dry_run=False, loop=False
    )

    submit_call = client.post.call_args_list[-1]
    assert submit_call.args[0] == "/api/eval/remote/bestmove-submit"
    body = submit_call.kwargs["json"]
    assert body["game_id"] == 101
    assert body["sf_version"] == "sf18"
    assert len(body["evals"]) == 3
    assert [e["ply"] for e in body["evals"]] == [4, 8, 12]
    assert [e["second_uci"] for e in body["evals"]] == ["d2d4", "c2c4", "f2f4"]
    assert [e["second_cp"] for e in body["evals"]] == [10, 20, 30]
    # The worker now ALSO submits its fresh best cp/mate (r[0]/r[1])
    # so the server can use our Stockfish best_cp for lichess games (was: absent).
    assert [e["best_cp"] for e in body["evals"]] == [0, 0, 0], (
        "BestMoveSubmitEval now carries the worker's fresh best_cp = r[0]"
    )
    for e in body["evals"]:
        assert "token" not in e, "the tier-4b lease is already ply-keyed, no token to echo"

    called_urls = [c.args[0] for c in client.post.call_args_list]
    assert "/api/eval/remote/atomic-submit" not in called_urls


async def test_eval_bestmove_positions_drops_failed_search() -> None:
    """Regression: a failed search (engine failure -> the all-None 7-tuple
    `evaluate_nodes_multipv2` returns) drops that ply from the returned evals
    rather than submitting an all-None (second_cp=None, second_mate=None) result
    as real data. Mirrors `test_eval_atomic_game_targeted_second_best_drops_failed_search`.

    Before the fix, the failed ply was submitted with second_cp/second_mate/
    second_uci all None. The server's second_best_map is keyed on presence,
    not on non-None values, so the fallback never fired for that ply
    -- the all-None tuple flowed into passes_inaccuracy_gate (False on any None
    eval) and the candidate was silently and permanently dropped.
    """
    pool = AsyncMock()
    pool.evaluate_nodes_multipv2 = AsyncMock(
        side_effect=[
            (0, None, "e2e4", "e2e4", 10, None, "d2d4"),  # ply 4: succeeds
            (None, None, None, None, None, None, None),  # ply 8: engine failure
            (0, None, "b1c3", "b1c3", 30, None, "f2f4"),  # ply 12: succeeds
        ]
    )
    positions: list[dict[str, object]] = [
        {"ply": 4, "fen": chess.STARTING_FEN},
        {"ply": 8, "fen": chess.STARTING_FEN},
        {"ply": 12, "fen": chess.STARTING_FEN},
    ]

    evals = await _eval_bestmove_positions(pool, positions)

    assert [e["ply"] for e in evals] == [4, 12], (
        "the failed ply (8) must be dropped, not submitted with all-None values"
    )


async def test_eval_bestmove_positions_includes_best_cp() -> None:
    """The worker submits its fresh best cp/mate
    (r[0]/r[1]) alongside the runner-up, so the server can use our Stockfish best_cp
    for lichess games instead of the stored lichess %eval. r[2]/r[3] still never leak."""
    pool = AsyncMock()
    # (best_cp=120, best_mate=None, best_move="e2e4", pv="e2e4 e7e5",
    #  second_cp=30, second_mate=None, second_uci="d2d4")
    pool.evaluate_nodes_multipv2 = AsyncMock(
        return_value=(120, None, "e2e4", "e2e4 e7e5", 30, None, "d2d4")
    )
    positions: list[dict[str, object]] = [{"ply": 6, "fen": chess.STARTING_FEN}]

    evals = await _eval_bestmove_positions(pool, positions)

    assert len(evals) == 1
    e = evals[0]
    assert e["best_cp"] == 120, "best_cp must be r[0]"
    assert e["best_mate"] is None, "best_mate must be r[1]"
    assert e["second_cp"] == 30, "second_cp must be r[4]"
    assert e["second_uci"] == "d2d4", "second_uci must be r[6]"
    assert "best_move" not in e, "r[2] (best_move) must NOT leak into the output dict"
    assert "pv" not in e, "r[3] (pv) must NOT leak into the output dict"


async def test_bestmove_lease_204_falls_to_idle_sleep_no_submit() -> None:
    """A 204 /bestmove-lease (all queues empty) results in the idle-sleep path --
    /bestmove-submit must never be called.
    """
    client = AsyncMock()
    client.post = AsyncMock(
        side_effect=[
            _make_response(204),  # /atomic-lease?scope=explicit
            _make_response(204),  # /entry-lease
            _make_response(204),  # /atomic-lease?scope=idle
            _make_response(204),  # /flaw-blob-lease
            _make_response(204),  # /bestmove-lease
        ]
    )
    pool = AsyncMock()

    with patch("scripts.remote_eval_worker.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await _run_cycle(
            client=client, pool=pool, sf_version="sf18", idle_sleep=1.0, dry_run=False, loop=False
        )
        mock_sleep.assert_awaited_once_with(1.0)

    called_urls = [c.args[0] for c in client.post.call_args_list]
    assert "/api/eval/remote/bestmove-lease" in called_urls
    assert "/api/eval/remote/bestmove-submit" not in called_urls


# ─── supervisor/child/once dispatch + watchdog stall predicate ────


def test_worker_role_once_no_marker() -> None:
    """--once with no child marker returns "once"."""
    assert _worker_role(once=True, child_marker=False) == "once"


def test_worker_role_child_marker_set() -> None:
    """No --once but the child marker is set returns "child"."""
    assert _worker_role(once=False, child_marker=True) == "child"


def test_worker_role_supervisor_default() -> None:
    """No --once and no child marker (the default, top-level invocation) returns
    "supervisor" (always supervised unless --once).
    """
    assert _worker_role(once=False, child_marker=False) == "supervisor"


def test_worker_role_once_always_wins_over_marker() -> None:
    """--once always bypasses supervision, even if the child marker is (implausibly)
    also set.
    """
    assert _worker_role(once=True, child_marker=True) == "once"


def test_is_stalled_true_when_gap_exceeds_threshold() -> None:
    """A gap strictly greater than threshold_s is a stall."""
    assert _is_stalled(now=100.0, last_progress=0.0, threshold_s=50.0) is True


def test_is_stalled_false_when_idle_but_under_threshold() -> None:
    """An idle-but-healthy gap under threshold_s is NOT a stall (a clean 204
    idle cycle counts as progress; this only guards the boundary predicate itself).
    """
    assert _is_stalled(now=40.0, last_progress=0.0, threshold_s=50.0) is False


def test_heartbeat_mark_advances_last_progress_and_writes_file(tmp_path: Path) -> None:
    """_Heartbeat.mark() advances last_progress toward "now" and freshens the
    heartbeat file's mtime with a value that parses as a float.
    """
    heartbeat_file = tmp_path / "worker.heartbeat"
    heartbeat = _Heartbeat(heartbeat_file)
    initial_progress = heartbeat.last_progress

    time.sleep(0.01)  # ensure a measurable, monotonically-increasing wall-clock gap
    heartbeat.mark()

    assert heartbeat.last_progress > initial_progress
    assert heartbeat_file.exists()
    written_value = float(heartbeat_file.read_text())
    assert written_value == heartbeat.last_progress
    # mtime is fresh (written within the last few seconds of this test running).
    assert abs(time.time() - heartbeat_file.stat().st_mtime) < 5.0


def test_heartbeat_mark_never_raises_on_write_failure(tmp_path: Path) -> None:
    """A heartbeat file write failure must never propagate -- observability-only
    (writing must never kill the worker).
    """
    # Point the heartbeat at a path whose parent directory does not exist, so the
    # write raises OSError (FileNotFoundError is an OSError subclass).
    heartbeat = _Heartbeat(tmp_path / "missing-dir" / "worker.heartbeat")
    heartbeat.mark()  # must not raise


def test_stall_threshold_s_is_minutes_not_seconds() -> None:
    """STALL_THRESHOLD_S must clear the worst legitimate cycle PLUS the full
    worker-side retry budget, derived rather than asserted against a bare literal
    (regression guard):

    - worst single-worker cycle: ~500s (--workers 1, every position times out at
      _NODES_TIMEOUT_S=5s over a ~100-position tier-1 game -- the same figure
      STALL_THRESHOLD_S's own module docstring derives).
    - plus the worst-case added retry wall clock: EVAL_RETRY_MAX_POSITIONS *
      EVAL_RETRY_TIMEOUT_S.

    STALL_THRESHOLD_S must clear that sum with the same ~100s margin the
    original 600s value held over its own ~500s worst case.
    """
    worst_single_worker_cycle_s = 500.0
    worst_case_added_retry_wall_clock_s = EVAL_RETRY_MAX_POSITIONS * EVAL_RETRY_TIMEOUT_S
    margin_s = 100.0
    derived_floor_s = worst_single_worker_cycle_s + worst_case_added_retry_wall_clock_s + margin_s

    assert STALL_THRESHOLD_S >= derived_floor_s, (
        f"STALL_THRESHOLD_S is {STALL_THRESHOLD_S}, expected >= {derived_floor_s} "
        f"(worst single-worker cycle {worst_single_worker_cycle_s}s + retry budget "
        f"{worst_case_added_retry_wall_clock_s}s + {margin_s}s margin)"
    )


# ─── Transient-failure classification / escalation tests (quota hygiene) ──────


@pytest.mark.parametrize("code", [500, 502, 503, 401, 404, 409, 425, 429])
def test_is_expected_transient_true_for_transient_http(code: int) -> None:
    """5xx and the auth/claim-race statuses are operational churn a polling daemon
    rides out silently -- they must NOT be captured per-cycle (quota drain)."""
    assert _is_expected_transient(_http_status_error(code)) is True


@pytest.mark.parametrize("code", [400, 403, 422])
def test_is_expected_transient_false_for_client_bug_http(code: int) -> None:
    """A 400/403/422 signals a real payload/permission bug -- capture immediately."""
    assert _is_expected_transient(_http_status_error(code)) is False


@pytest.mark.parametrize(
    "exc",
    [
        httpx.ConnectError("all connection attempts failed"),
        httpx.ReadError("read error"),
        httpx.ReadTimeout("read timeout"),
        httpx.ConnectTimeout("connect timeout"),
        ConnectionRefusedError(111, "Connection refused"),
    ],
)
def test_is_expected_transient_true_for_transport_errors(exc: BaseException) -> None:
    """Transport blips (httpx.TransportError family + raw ConnectionRefusedError) are
    transient and must not be captured per-cycle."""
    assert _is_expected_transient(exc) is True


@pytest.mark.parametrize("exc", [ValueError("bad FEN"), KeyError("game_id"), RuntimeError("x")])
def test_is_expected_transient_false_for_real_defects(exc: BaseException) -> None:
    """Non-network exceptions (ValidationError, bad-FEN ValueError, KeyError) are real
    defects and fall through to immediate capture."""
    assert _is_expected_transient(exc) is False


def test_handle_transient_failure_no_capture_before_threshold() -> None:
    """A short-lived transient streak (deploy/restart window) logs locally and captures
    nothing -- the whole point of the quota fix."""
    exc = _http_status_error(502)
    with patch("scripts.remote_eval_worker.sentry_sdk") as mock_sentry:
        with patch("scripts.remote_eval_worker.time.time", return_value=1000.0):
            start, alerted = _handle_transient_failure(exc, None, False)
        assert start == 1000.0
        assert alerted is False
        # Still within the alert window on a later failure.
        with patch(
            "scripts.remote_eval_worker.time.time",
            return_value=1000.0 + TRANSIENT_FAILURE_ALERT_S - 1.0,
        ):
            start, alerted = _handle_transient_failure(exc, start, alerted)
        assert alerted is False
        mock_sentry.capture_message.assert_not_called()
        mock_sentry.capture_exception.assert_not_called()


def test_handle_transient_failure_escalates_once_past_threshold() -> None:
    """A streak persisting past TRANSIENT_FAILURE_ALERT_S escalates exactly ONE Sentry
    event; further failures in the same streak stay silent."""
    exc = _http_status_error(502)
    with patch("scripts.remote_eval_worker.sentry_sdk") as mock_sentry:
        with patch("scripts.remote_eval_worker.time.time", return_value=2000.0):
            start, alerted = _handle_transient_failure(exc, None, False)
        # Cross the threshold.
        with patch(
            "scripts.remote_eval_worker.time.time",
            return_value=2000.0 + TRANSIENT_FAILURE_ALERT_S + 1.0,
        ):
            start, alerted = _handle_transient_failure(exc, start, alerted)
        assert alerted is True
        assert mock_sentry.capture_message.call_count == 1
        # message must be static (grouping); variable data goes to context, not the string.
        msg = mock_sentry.capture_message.call_args.args[0]
        assert "%" not in msg and "502" not in msg
        # A further failure in the same (still-alerted) streak captures nothing more.
        with patch(
            "scripts.remote_eval_worker.time.time",
            return_value=2000.0 + TRANSIENT_FAILURE_ALERT_S + 30.0,
        ):
            _handle_transient_failure(exc, start, alerted)
        assert mock_sentry.capture_message.call_count == 1


def test_transient_failure_alert_s_clears_deploy_window() -> None:
    """Regression guard: the escalation threshold must clear a normal deploy/restart
    window so routine deploys never escalate (they're the churn we stopped capturing)."""
    assert TRANSIENT_FAILURE_ALERT_S >= 120.0


# ─── dual-URL fallback tests ──────────────────────

_ATOMIC_LEASE_BODY: dict[str, object] = {
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
_ATOMIC_SUBMIT_BODY: dict[str, object] = {"game_id": 42, "flaws_written": 0, "blobs_written": 0}


def _atomic_success_pool() -> AsyncMock:
    """An engine pool that succeeds a single rung-1 atomic lease+submit."""
    pool = AsyncMock()
    pool.evaluate_nodes_with_pv = AsyncMock(return_value=(100, None, "e2e4", "e2e4 e7e5"))
    return pool


def _all_204_client() -> AsyncMock:
    """A mock client whose /atomic-lease/entry-lease/flaw-blob-lease/bestmove-lease
    rungs all return 204, in ladder order."""
    client = AsyncMock()
    client.post = AsyncMock(side_effect=[_make_response(204) for _ in range(5)])
    return client


async def test_build_backend_targets_single_target_when_no_fallback() -> None:
    """With fallback_url=None, _build_backend_targets returns exactly one target --
    the byte-identical single-backend case."""
    targets = _build_backend_targets("https://flawchess.com", "primary-tok", None, None)
    assert targets == [
        _BackendTarget(base_url="https://flawchess.com", token="primary-tok", label="primary")
    ]


async def test_fallback_token_defaults_to_primary_token() -> None:
    """--fallback-token omitted (None) while --fallback-url is set: the fallback
    target's token equals the primary's resolved token (documented default)."""
    targets = _build_backend_targets(
        "https://flawchess.com", "primary-tok", "http://localhost:8001", None
    )
    assert len(targets) == 2
    assert targets[0] == _BackendTarget(
        base_url="https://flawchess.com", token="primary-tok", label="primary"
    )
    assert targets[1] == _BackendTarget(
        base_url="http://localhost:8001", token="primary-tok", label="fallback"
    )


async def test_build_backend_targets_distinct_fallback_token() -> None:
    """An explicit --fallback-token is used as-is, never overwritten by the primary."""
    targets = _build_backend_targets(
        "https://flawchess.com", "primary-tok", "http://localhost:8001", "bench-tok"
    )
    assert targets[1].token == "bench-tok"


def test_fallback_url_empty_string_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """--fallback-url "" raises SystemExit (parser.error), not a silently-empty base_url."""
    monkeypatch.setattr(sys, "argv", ["worker", "--fallback-url", "", "--once"])
    with pytest.raises(SystemExit):
        parse_args()


def test_fallback_url_whitespace_only_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """--fallback-url "   " (whitespace-only) is also rejected, not just the empty string."""
    monkeypatch.setattr(sys, "argv", ["worker", "--fallback-url", "   ", "--once"])
    with pytest.raises(SystemExit):
        parse_args()


def test_fallback_token_without_url_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """--fallback-token without --fallback-url is rejected -- a token with nowhere
    to send it is a configuration mistake, not a valid one-target run."""
    monkeypatch.setattr(sys, "argv", ["worker", "--fallback-token", "tok", "--once"])
    with pytest.raises(SystemExit):
        parse_args()


def test_fallback_url_and_token_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    """--fallback-url with --fallback-token is accepted and both values are parsed."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["worker", "--fallback-url", "http://localhost:8001", "--fallback-token", "tok", "--once"],
    )
    args = parse_args()
    assert args.fallback_url == "http://localhost:8001"
    assert args.fallback_token == "tok"


def _probe_request() -> httpx.Request:
    return httpx.Request("POST", "http://192.168.50.179:8001/api/eval/remote/atomic-lease")


def test_describe_exc_names_connect_timeout_target() -> None:
    """A ConnectTimeout has an EMPTY str() -- the exact case that produced a bare
    "Cycle failed" -- so the class name and target must still identify it."""
    out = _describe_exc(httpx.ConnectTimeout("", request=_probe_request()))
    assert "ConnectTimeout" in out
    assert "192.168.50.179:8001" in out


def test_describe_exc_surfaces_http_status_and_path() -> None:
    """403 vs 404 vs 5xx is the key discriminator (wrong token / wrong URL /
    unhealthy backend), so the status code and path must both appear."""
    req = _probe_request()
    out = _describe_exc(
        httpx.HTTPStatusError("x", request=req, response=httpx.Response(403, request=req))
    )
    assert "403" in out
    assert "/api/eval/remote/atomic-lease" in out


def test_describe_exc_keeps_connect_error_detail() -> None:
    """A ConnectError DOES carry a useful message ("Connection refused"); it must
    survive alongside the class name, not be replaced by it."""
    out = _describe_exc(
        httpx.ConnectError("[Errno 111] Connection refused", request=_probe_request())
    )
    assert "Connection refused" in out
    assert "ConnectError" in out


def test_describe_exc_survives_request_error_with_no_request() -> None:
    """httpx.RequestError.request RAISES RuntimeError when unset rather than
    returning None, so a truthiness check on it crashes the failure handler that
    is reporting the failure. Regression: this shape reaches _handle_transient_failure
    whenever a RequestError is raised outside a send."""
    out = _describe_exc(httpx.ConnectError("connection refused"))
    assert "ConnectError" in out
    assert "connection refused" in out


def test_describe_exc_handles_non_httpx_exception() -> None:
    """A non-httpx bug must not crash the failure handler that is reporting it."""
    assert _describe_exc(ValueError("some other bug")) == "ValueError: some other bug"


def test_resolve_fallback_token_cli_wins_over_env() -> None:
    """An explicit --fallback-token beats EVAL_FALLBACK_OPERATOR_TOKEN, mirroring
    how --token beats EVAL_OPERATOR_TOKEN."""
    assert _resolve_fallback_token("http://localhost:8001", "cli-tok", "env-tok") == "cli-tok"


def test_resolve_fallback_token_falls_back_to_env() -> None:
    """With --fallback-token omitted, the .env value is used -- the whole point of
    the setting: a worker box needs no token flag at all."""
    assert _resolve_fallback_token("http://localhost:8001", None, "env-tok") == "env-tok"


def test_resolve_fallback_token_empty_env_means_reuse_primary() -> None:
    """An unset (empty-string) env var resolves to None, NOT "", so
    _build_backend_targets keeps its documented reuse-the-primary-token behavior.
    An empty string would authenticate as an empty token and 403."""
    assert _resolve_fallback_token("http://localhost:8001", None, "") is None


def test_resolve_fallback_token_ignored_without_fallback_url() -> None:
    """With no --fallback-url there is no second target, so the env var is not
    consulted -- a stray value must not look meaningful when it changes nothing."""
    assert _resolve_fallback_token(None, None, "env-tok") is None


def test_env_fallback_token_reaches_the_fallback_target() -> None:
    """End to end through the pair: an env-sourced token lands on the fallback
    target and leaves the primary's token alone."""
    resolved = _resolve_fallback_token("http://localhost:8001", None, "env-tok")
    targets = _build_backend_targets(
        "https://flawchess.com", "primary-tok", "http://localhost:8001", resolved
    )
    assert [t.token for t in targets] == ["primary-tok", "env-tok"]


async def test_single_target_call_sequence_unchanged() -> None:
    """With one client (--fallback-url omitted), _run_loop's per-cycle HTTP call
    sequence is byte-identical to the single-client loop: exactly one
    _run_cycle invocation, same rung-1 lease + submit calls."""
    client = AsyncMock()
    client.post = AsyncMock(
        side_effect=[
            _make_response(200, _ATOMIC_LEASE_BODY),
            _make_response(200, _ATOMIC_SUBMIT_BODY),
        ]
    )
    pool = _atomic_success_pool()

    await _run_loop(
        clients=[client],
        pool=pool,
        sf_version="sf16",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )

    called_urls = [c.args[0] for c in client.post.call_args_list]
    assert called_urls == [
        "/api/eval/remote/atomic-lease",
        "/api/eval/remote/atomic-submit",
    ]


async def test_fallback_not_called_when_primary_rung1_works() -> None:
    """Rung 1 returns 200 on primary: the fallback client receives zero calls."""
    primary = AsyncMock()
    primary.post = AsyncMock(
        side_effect=[
            _make_response(200, _ATOMIC_LEASE_BODY),
            _make_response(200, _ATOMIC_SUBMIT_BODY),
        ]
    )
    fallback = AsyncMock()
    fallback.post = AsyncMock()
    pool = _atomic_success_pool()

    await _run_loop(
        clients=[primary, fallback],
        pool=pool,
        sf_version="sf16",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )

    fallback.post.assert_not_called()


async def test_fallback_not_called_when_primary_rung5_works() -> None:
    """Rung 5 (/bestmove-lease) returns 200 on primary after rungs 1-4 all 204:
    the fallback client still receives zero calls (whole-ladder gating, not
    per-rung)."""
    bestmove_lease_body = {
        "game_id": 88,
        "positions": [{"ply": 4, "fen": chess.STARTING_FEN}],
        "leased_at": "2026-08-22T10:00:00Z",
    }
    submit_body = {"game_id": 88, "rows_written": 1}
    primary = AsyncMock()
    primary.post = AsyncMock(
        side_effect=[
            _make_response(204),  # atomic-lease?scope=explicit
            _make_response(204),  # entry-lease
            _make_response(204),  # atomic-lease?scope=idle
            _make_response(204),  # flaw-blob-lease
            _make_response(200, bestmove_lease_body),  # bestmove-lease
            _make_response(200, submit_body),  # bestmove-submit
        ]
    )
    fallback = AsyncMock()
    fallback.post = AsyncMock()

    pool = AsyncMock()
    pool.evaluate_nodes_multipv2 = AsyncMock(
        return_value=(0, None, "e2e4", "e2e4", 5, None, "d2d4")
    )

    await _run_loop(
        clients=[primary, fallback],
        pool=pool,
        sf_version="sf18",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )

    fallback.post.assert_not_called()


async def test_fallback_fires_only_after_all_204() -> None:
    """All five primary rungs return 204: the fallback client receives its own
    rung-1 call, and the primary's five calls all precede it."""
    primary = _all_204_client()
    fallback = AsyncMock()
    fallback.post = AsyncMock(
        side_effect=[
            _make_response(200, _ATOMIC_LEASE_BODY),
            _make_response(200, _ATOMIC_SUBMIT_BODY),
        ]
    )
    pool = _atomic_success_pool()

    await _run_loop(
        clients=[primary, fallback],
        pool=pool,
        sf_version="sf16",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )

    assert primary.post.call_count == 5
    assert fallback.post.call_count == 2
    assert fallback.post.call_args_list[0].args[0] == "/api/eval/remote/atomic-lease"


async def test_ladder_never_interleaves_targets() -> None:
    """The invariant test accepted in the assumption-delta decision: the primary
    client's five calls all precede the fallback client's first call -- rungs are
    never interleaved across targets. Verified by comparing recorded call ORDER
    across the two mocks (call_args_list alone cannot show cross-mock ordering)."""
    call_order: list[str] = []
    primary_responses = [_make_response(204) for _ in range(5)]
    fallback_responses = [
        _make_response(200, _ATOMIC_LEASE_BODY),
        _make_response(200, _ATOMIC_SUBMIT_BODY),
    ]

    async def primary_post(*_args: object, **_kwargs: object) -> MagicMock:
        call_order.append("primary")
        return primary_responses.pop(0)

    async def fallback_post(*_args: object, **_kwargs: object) -> MagicMock:
        call_order.append("fallback")
        return fallback_responses.pop(0)

    primary = AsyncMock()
    primary.post = AsyncMock(side_effect=primary_post)
    fallback = AsyncMock()
    fallback.post = AsyncMock(side_effect=fallback_post)
    pool = _atomic_success_pool()

    await _run_loop(
        clients=[primary, fallback],
        pool=pool,
        sf_version="sf16",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )

    assert call_order == ["primary"] * 5 + ["fallback"] * 2


async def test_both_targets_idle_sleeps_once() -> None:
    """Both targets return all-204: asyncio.sleep(idle_sleep) is awaited exactly
    once for the whole cycle, not once per target (regression guard)."""
    primary = _all_204_client()
    fallback = _all_204_client()
    pool = AsyncMock()

    with patch("scripts.remote_eval_worker.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await _run_loop(
            clients=[primary, fallback],
            pool=pool,
            sf_version="sf18",
            idle_sleep=1.0,
            dry_run=False,
            loop=False,
        )
        mock_sleep.assert_awaited_once_with(1.0)

    assert primary.post.call_count == 5
    assert fallback.post.call_count == 5


async def test_unreachable_primary_falls_through() -> None:
    """Primary's first call raises httpx.ConnectError (unreachable): the
    fallback ladder runs in the SAME cycle rather than the exception propagating.
    The fallthrough is unconditional (not gated on `loop`), so this holds even
    for a bounded --once (loop=False) run -- there is more work left to try
    before the run can conclude."""
    primary = AsyncMock()
    primary.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
    fallback = AsyncMock()
    fallback.post = AsyncMock(
        side_effect=[
            _make_response(200, _ATOMIC_LEASE_BODY),
            _make_response(200, _ATOMIC_SUBMIT_BODY),
        ]
    )
    pool = _atomic_success_pool()

    await _run_loop(
        clients=[primary, fallback],
        pool=pool,
        sf_version="sf16",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )

    assert primary.post.call_count == 1
    assert fallback.post.call_count == 2
    assert fallback.post.call_args_list[0].args[0] == "/api/eval/remote/atomic-lease"


# ─── Lanes (--lanes) ──────────────────────────────────────────────────────────
#
# quick 261119-k9s: N concurrent lease -> eval -> submit cycles on one EnginePool. Every
# fake coroutine awaits a real asyncio.sleep so a lane can never spin without yielding.

_LANE_SLEEP_S = 0.005
_LANE_WAIT_S = 5.0
# Captured at import: tests that patch asyncio.sleep (virtual clock, mocks) still need a
# real yield to let other tasks run.
_REAL_SLEEP = asyncio.sleep
_URL_BLOB_LEASE = "/api/eval/remote/flaw-blob-lease"
_URL_BLOB_SUBMIT = "/api/eval/remote/flaw-blob-submit"
_URL_ENTRY_LEASE = "/api/eval/remote/entry-lease"
_URL_ENTRY_SUBMIT = "/api/eval/remote/entry-submit"
_MULTIPV2_RESULT = (0, None, "e2e4", "e2e4", 5, None, "d2d4")


def _lane_task_name() -> str:
    """Name of the asyncio task the caller runs in (a lane task for direct awaits)."""
    task = asyncio.current_task()
    assert task is not None
    return task.get_name()


@dataclass
class _LaneStats:
    """Observations recorded by the lane fakes, plus optional behavior hooks."""

    entry_mode: bool = False
    blob_lease_hook: Callable[[str], Awaitable[None]] | None = None
    eval_hook: Callable[[], Awaitable[None]] | None = None
    leased_ids: list[int] = field(default_factory=list)
    submits_by_task: dict[str, int] = field(default_factory=dict)
    total_submits: int = 0
    in_flight: int = 0
    max_in_flight: int = 0
    entry_outstanding: int = 0
    max_entry_outstanding: int = 0
    entry_submits: int = 0
    ids: itertools.count[int] = field(default_factory=lambda: itertools.count(1))
    progress: asyncio.Event = field(default_factory=asyncio.Event)


def _make_lane_client(stats: _LaneStats) -> AsyncMock:
    """A client whose rungs route by URL: flaw-blob (or entry-ply when entry_mode) has
    work, every other rung is 204."""

    async def post(url: str, **kwargs: object) -> MagicMock:
        await asyncio.sleep(_LANE_SLEEP_S)
        name = _lane_task_name()
        if url == _URL_BLOB_LEASE and not stats.entry_mode:
            if stats.blob_lease_hook is not None:
                await stats.blob_lease_hook(name)
            game_id = next(stats.ids)
            stats.leased_ids.append(game_id)
            positions = [{"token": "3:missed:0", "fen": chess.STARTING_FEN}]
            return _make_response(200, {"game_id": game_id, "positions": positions})
        if url == _URL_BLOB_SUBMIT:
            stats.submits_by_task[name] = stats.submits_by_task.get(name, 0) + 1
            stats.total_submits += 1
            stats.progress.set()
            return _make_response(200, {"game_id": 0, "blobs_written": 1})
        if url == _URL_ENTRY_LEASE and stats.entry_mode:
            stats.entry_outstanding += 1
            stats.max_entry_outstanding = max(stats.max_entry_outstanding, stats.entry_outstanding)
            await asyncio.sleep(_LANE_SLEEP_S)  # let sibling lanes interleave here
            positions = [{"game_id": next(stats.ids), "ply": 1, "fen": chess.STARTING_FEN}]
            return _make_response(200, {"positions": positions})
        if url == _URL_ENTRY_SUBMIT:
            stats.entry_outstanding -= 1
            stats.entry_submits += 1
            stats.total_submits += 1
            stats.progress.set()
            return _make_response(200, {"game_ids": [], "stamped_count": 0})
        return _make_response(204)

    client = AsyncMock()
    client.post = AsyncMock(side_effect=post)
    return client


def _make_lane_pool(stats: _LaneStats) -> AsyncMock:
    pool = AsyncMock()

    async def multipv2(*_args: object, **_kwargs: object) -> tuple[object, ...]:
        stats.in_flight += 1
        stats.max_in_flight = max(stats.max_in_flight, stats.in_flight)
        try:
            if stats.eval_hook is not None:
                await stats.eval_hook()
            await asyncio.sleep(_LANE_SLEEP_S)
            return _MULTIPV2_RESULT
        finally:
            stats.in_flight -= 1

    async def depth15(*_args: object, **_kwargs: object) -> tuple[int, None]:
        await asyncio.sleep(_LANE_SLEEP_S)
        return (10, None)

    pool.evaluate_nodes_multipv2 = AsyncMock(side_effect=multipv2)
    pool.evaluate = AsyncMock(side_effect=depth15)
    return pool


def _start_lanes(stats: _LaneStats, lanes: int = 3) -> asyncio.Task[None]:
    return asyncio.create_task(
        _run_lanes(
            clients=[_make_lane_client(stats)],
            pool=_make_lane_pool(stats),
            sf_version="sf18",
            idle_sleep=0.01,
            dry_run=False,
            lanes=lanes,
            heartbeat=None,
        )
    )


async def _cancel_lane_tasks(*tasks: asyncio.Task[None]) -> None:
    """Cancel the given tasks and any leaked lane task; swallow every outcome."""
    leaked = [
        t
        for t in asyncio.all_tasks()
        if t.get_name().startswith(_LANE_TASK_PREFIX) and not t.done()
    ]
    everything = [*tasks, *leaked]
    for t in everything:
        t.cancel()
    await asyncio.gather(*everything, return_exceptions=True)


def _surviving_lane_tasks() -> list[str]:
    return [
        t.get_name()
        for t in asyncio.all_tasks()
        if t.get_name().startswith(_LANE_TASK_PREFIX) and not t.done()
    ]


async def _run_worker_with_patches(lanes: int, loop: bool = True) -> tuple[MagicMock, MagicMock]:
    """Call run_worker with EnginePool/_run_loop/_run_lanes patched; return the two mocks."""
    pool = AsyncMock()
    with (
        patch("scripts.remote_eval_worker.EnginePool", MagicMock(return_value=pool)) as pool_cls,
        patch(
            "scripts.remote_eval_worker.get_stockfish_version",
            AsyncMock(return_value="sf18"),
        ),
        patch("scripts.remote_eval_worker._run_loop", new_callable=AsyncMock) as run_loop,
        patch("scripts.remote_eval_worker._run_lanes", new_callable=AsyncMock) as run_lanes,
    ):
        await run_worker(
            targets=[_BackendTarget(base_url="http://127.0.0.1:9", token="t", label="primary")],
            worker_id="wid",
            workers=6,
            idle_sleep=0.01,
            dry_run=False,
            loop=loop,
            lanes=lanes,
        )
    assert pool_cls.call_count == 1, "the EnginePool is built once however many lanes run"
    pool_cls.assert_called_once_with(6)
    return run_loop, run_lanes


def test_default_lanes_is_one() -> None:
    assert DEFAULT_LANES == 1


async def test_run_worker_single_lane_awaits_run_loop_once() -> None:
    """lanes=1 is today's path: one _run_loop with no lane context, no _run_lanes."""
    run_loop, run_lanes = await _run_worker_with_patches(lanes=1)

    run_loop.assert_awaited_once()
    assert run_loop.await_args is not None
    assert run_loop.await_args.kwargs.get("lane") is None
    run_lanes.assert_not_awaited()


async def test_run_worker_multi_lane_awaits_run_lanes_once() -> None:
    run_loop, run_lanes = await _run_worker_with_patches(lanes=3)

    run_lanes.assert_awaited_once()
    assert run_lanes.await_args is not None
    assert run_lanes.await_args.kwargs["lanes"] == 3
    run_loop.assert_not_awaited()


async def test_run_worker_multi_lane_requires_loop_mode() -> None:
    """A bounded run is a single lane by definition."""
    with pytest.raises(ValueError, match="lanes > 1 requires loop mode"):
        await _run_worker_with_patches(lanes=2, loop=False)


async def test_lanes_run_concurrently_on_one_pool() -> None:
    """Three lanes have three evaluations in flight at once, for three distinct games."""
    stats = _LaneStats()
    all_in = asyncio.Event()

    async def barrier() -> None:
        if stats.in_flight >= 3:
            all_in.set()
        await asyncio.wait_for(all_in.wait(), timeout=2)

    stats.eval_hook = barrier
    task = _start_lanes(stats, lanes=3)
    try:
        with patch("scripts.remote_eval_worker.sentry_sdk.capture_exception"):
            await asyncio.wait_for(all_in.wait(), timeout=_LANE_WAIT_S)
        assert stats.max_in_flight == 3
        assert len(set(stats.leased_ids[:3])) == 3
    finally:
        await _cancel_lane_tasks(task)


async def test_lane_exception_is_isolated_to_that_lane() -> None:
    """One lane's lease raising is captured once and absorbed by that lane's own loop;
    afterwards EVERY lane (the failing one included) still completes cycles."""
    stats = _LaneStats()
    failed = False

    async def fail_lane_one_once(name: str) -> None:
        nonlocal failed
        if name == f"{_LANE_TASK_PREFIX}1" and not failed:
            failed = True
            raise RuntimeError("boom")

    stats.blob_lease_hook = fail_lane_one_once
    task = _start_lanes(stats, lanes=3)
    expected = {f"{_LANE_TASK_PREFIX}{i}" for i in range(3)}
    try:
        with patch("scripts.remote_eval_worker.sentry_sdk.capture_exception") as capture:
            deadline = time.monotonic() + _LANE_WAIT_S
            while set(stats.submits_by_task) != expected and time.monotonic() < deadline:
                await asyncio.sleep(0.01)
                assert not task.done(), "a lane's exception must not end the lane runner"
            assert set(stats.submits_by_task) == expected
            assert failed is True
            assert capture.call_count == 1
            assert isinstance(capture.call_args.args[0], RuntimeError)
    finally:
        await _cancel_lane_tasks(task)


async def test_entry_rung_is_serialized_across_lanes() -> None:
    """/entry-submit stamps every unexpired game leased to the worker id, so at most one
    entry lease may be outstanding per process however many lanes run."""
    stats = _LaneStats(entry_mode=True)
    task = _start_lanes(stats, lanes=3)
    try:
        deadline = time.monotonic() + _LANE_WAIT_S
        while stats.entry_submits < 6 and time.monotonic() < deadline:
            await asyncio.sleep(0.01)
        assert stats.entry_submits >= 6
        assert stats.max_entry_outstanding == 1
    finally:
        await _cancel_lane_tasks(task)


async def test_cancelling_run_lanes_cancels_every_lane() -> None:
    stats = _LaneStats()
    task = _start_lanes(stats, lanes=3)
    try:
        await asyncio.wait_for(stats.progress.wait(), timeout=_LANE_WAIT_S)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert _surviving_lane_tasks() == []
    finally:
        await _cancel_lane_tasks(task)


def _parse(monkeypatch: pytest.MonkeyPatch, *argv: str) -> argparse.Namespace:
    monkeypatch.setattr(sys, "argv", ["worker", *argv])
    return parse_args()


def test_lanes_parse_defaults_to_one(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _parse(monkeypatch, "--once").lanes == 1


def test_lanes_below_one_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(SystemExit):
        _parse(monkeypatch, "--lanes", "0")


@pytest.mark.parametrize(("workers", "lanes"), [(4, 2), (11, 2), (28, 5), (8, 2), (6, 2)])
def test_lanes_above_cap_rejected(
    monkeypatch: pytest.MonkeyPatch, workers: int, lanes: int
) -> None:
    with pytest.raises(SystemExit):
        _parse(monkeypatch, "--workers", str(workers), "--lanes", str(lanes))


@pytest.mark.parametrize(
    ("workers", "lanes"), [(28, 4), (28, 3), (16, 2), (12, 2), (8, 1), (1, 1), (11, 1), (64, 10)]
)
def test_lanes_within_cap_accepted(
    monkeypatch: pytest.MonkeyPatch, workers: int, lanes: int
) -> None:
    args = _parse(monkeypatch, "--workers", str(workers), "--lanes", str(lanes))
    assert args.lanes == lanes


def test_max_lanes_is_one_lane_per_engines_per_lane() -> None:
    assert ENGINES_PER_LANE == 6
    assert [_max_lanes(w) for w in (1, 5, 6, 8, 11, 12, 16, 28)] == [1, 1, 1, 1, 1, 2, 2, 4]


def test_lanes_with_a_huge_idle_sleep_rejected_but_single_lane_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A lane's first progress mark comes after its stagger plus its idle sleep, so a huge
    --idle-sleep with several lanes could trip the stall watchdog on a healthy idle worker:
    rejected at parse time. lanes=1 is deliberately not constrained (today's behavior)."""
    with pytest.raises(SystemExit):
        _parse(monkeypatch, "--workers", "12", "--lanes", "2", "--idle-sleep", "400")
    assert _parse(monkeypatch, "--workers", "12", "--lanes", "2", "--idle-sleep", "100").lanes == 2
    assert _parse(monkeypatch, "--idle-sleep", "400").lanes == 1


def test_effective_lanes_forces_one_for_once_and_dry_run() -> None:
    assert _effective_lanes(7, once=True, dry_run=False) == 1
    assert _effective_lanes(7, once=False, dry_run=True) == 1
    assert _effective_lanes(7, once=False, dry_run=False) == 7


# Model of one atomic cycle's all-timeout worst case: three first-pass gathers (full-ply,
# blob nodes, targeted second-best), each bounded here at 100 positions, every search
# running to the engine's per-search timeout, plus the per-cycle retry budget.
_MODEL_PASSES_PER_ATOMIC_CYCLE = 3
_MODEL_POSITIONS_PER_PASS = 100
_MODEL_HTTP_CALLS_PER_CYCLE = 5


def test_lane_cap_keeps_modelled_worst_case_cycle_inside_the_stall_threshold() -> None:
    """With L = _max_lanes(W) lanes all in the all-timeout state, the last cycle finishes
    after about L x (own engine-seconds) / W; computed from the module's real constants
    (no literals), plus the HTTP time budget, it stays under STALL_THRESHOLD_S for every
    worker count where more than one lane is allowed."""
    cycle_engine_s = (
        _MODEL_PASSES_PER_ATOMIC_CYCLE * _MODEL_POSITIONS_PER_PASS * _NODES_TIMEOUT_S
        + EVAL_RETRY_MAX_POSITIONS * EVAL_RETRY_TIMEOUT_S
    )
    http_s = _MODEL_HTTP_CALLS_PER_CYCLE * HTTP_TIMEOUT_S
    for workers in range(2 * ENGINES_PER_LANE, 129):
        lanes = _max_lanes(workers)
        assert lanes >= 2
        worst_s = lanes * cycle_engine_s / workers + http_s
        assert worst_s < STALL_THRESHOLD_S, f"workers={workers} lanes={lanes} worst={worst_s}"


@pytest.mark.parametrize(
    ("exc", "is_last", "loop", "expected", "slept", "captured"),
    [
        (httpx.ConnectError("x"), False, True, "next_target", False, 0),
        (httpx.ConnectError("x"), True, True, "next_cycle", True, 0),
        (httpx.ConnectError("x"), True, False, "raise", False, 1),
        (ValueError("bug"), True, True, "next_cycle", True, 1),
        (ValueError("bug"), True, False, "raise", False, 1),
    ],
)
async def test_on_cycle_failure_decision_table(
    exc: Exception, is_last: bool, loop: bool, expected: str, slept: bool, captured: int
) -> None:
    streak = _TransientStreak()
    with (
        patch("scripts.remote_eval_worker.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        patch("scripts.remote_eval_worker.sentry_sdk.capture_exception") as capture,
    ):
        action = await _on_cycle_failure(exc, streak, is_last=is_last, loop=loop, idle_sleep=2.5)

    assert action == expected
    assert capture.call_count == captured
    if slept:
        mock_sleep.assert_awaited_once_with(2.5)
    else:
        mock_sleep.assert_not_awaited()


# ─── Lanes: per-lane watchdog, staggered idle, lane-labelled logs ─────────────


def test_heartbeat_last_progress_is_the_oldest_lane() -> None:
    heartbeat = _Heartbeat(None, lanes=3)
    initial = heartbeat.last_progress

    time.sleep(0.01)
    heartbeat.mark(1)
    time.sleep(0.01)
    heartbeat.mark(2)
    # Lane 0 never marked: healthy siblings cannot advance the minimum.
    assert heartbeat.last_progress == initial

    time.sleep(0.01)
    heartbeat.mark(0)
    # Now lane 1 holds the oldest slot.
    assert heartbeat.last_progress == heartbeat._lane_progress[1]
    assert heartbeat.last_progress > initial
    assert heartbeat.last_progress == min(heartbeat._lane_progress)


def test_heartbeat_file_is_freshened_only_by_the_oldest_lane(tmp_path: Path) -> None:
    heartbeat_file = tmp_path / "worker.heartbeat"
    heartbeat = _Heartbeat(heartbeat_file, lanes=3)
    time.sleep(0.01)
    heartbeat.mark(1)
    time.sleep(0.01)
    heartbeat.mark(2)
    time.sleep(0.01)
    heartbeat.mark(0)  # lane 1 is now the oldest, lanes 2 and 0 are fresher

    heartbeat_file.unlink()
    time.sleep(0.01)
    heartbeat.mark(0)  # lane 0 is NOT the oldest: must not recreate the file
    assert not heartbeat_file.exists()

    time.sleep(0.01)
    heartbeat.mark(1)  # lane 1 held the oldest slot: recreates it
    assert heartbeat_file.exists()
    assert float(heartbeat_file.read_text()) == heartbeat.last_progress


def test_lane_schedule_staggers_starts_and_scales_idle() -> None:
    assert _lane_schedule(3, 1.0) == [(0.0, 3.0), (1.0, 3.0), (2.0, 3.0)]
    assert _lane_schedule(1, 1.0) == [(0.0, 1.0)]


def test_lane_schedule_clamps_stagger_and_idle_below_the_watchdog() -> None:
    """The scaled idle sleep and the stagger never exceed their caps, so a large
    --idle-sleep cannot push a lane's first mark toward STALL_THRESHOLD_S; lanes=1 stays
    exactly the user's --idle-sleep, whatever its size."""
    assert _lane_schedule(3, 30.0) == [(0.0, 60.0), (30.0, 60.0), (60.0, 60.0)]
    assert _lane_schedule(4, 100.0) == [(0.0, 100.0), (60.0, 100.0), (60.0, 100.0), (60.0, 100.0)]
    assert _lane_schedule(1, 500.0) == [(0.0, 500.0)]


async def test_run_lanes_wires_schedule_and_shared_state() -> None:
    """Each lane's _run_loop gets idle_sleep x lanes, loop=True and a distinct index; the
    entry lock and the transient streak are ONE object across every lane."""
    block = asyncio.Event()

    async def lane_loop(**_kwargs: object) -> None:
        await block.wait()  # lanes are infinite loops

    with (
        patch("scripts.remote_eval_worker._run_loop", side_effect=lane_loop) as run_loop,
        patch("scripts.remote_eval_worker.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        task = asyncio.create_task(
            _run_lanes(
                clients=[AsyncMock()],
                pool=AsyncMock(),
                sf_version="sf18",
                idle_sleep=0.5,
                dry_run=False,
                lanes=3,
                heartbeat=None,
            )
        )
        try:
            for _ in range(50):
                await _REAL_SLEEP(0)
            assert run_loop.await_count == 3
            awaited_delays = sorted(c.args[0] for c in mock_sleep.await_args_list)
        finally:
            await _cancel_lane_tasks(task)

    kwargs_list = [c.kwargs for c in run_loop.await_args_list]
    assert all(k["idle_sleep"] == 1.5 and k["loop"] is True for k in kwargs_list)
    contexts = sorted((k["lane"] for k in kwargs_list), key=lambda lane: lane.index)
    assert [lane.index for lane in contexts] == [0, 1, 2]
    assert len({id(lane.entry_lock) for lane in contexts}) == 1
    assert len({id(lane.streak) for lane in contexts}) == 1
    assert awaited_delays == [0.5, 1.0]


async def test_log_carries_the_lane_label_only_inside_a_lane(
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def log_from_loop(**_kwargs: object) -> None:
        _log("hello from the loop")

    lane = _LaneContext(index=2, entry_lock=asyncio.Lock(), streak=_TransientStreak())
    with patch("scripts.remote_eval_worker._run_loop", side_effect=log_from_loop):
        # A task gets its own context copy, so the label set by _run_lane stays inside it.
        await asyncio.create_task(
            _run_lane(
                lane,
                clients=[AsyncMock()],
                pool=AsyncMock(),
                sf_version="sf18",
                start_delay_s=0.0,
                idle_sleep=1.0,
                dry_run=False,
                heartbeat=None,
            )
        )
    _log("plain line")

    out = capsys.readouterr().out
    assert "[lane 2] hello from the loop" in out
    plain = next(line for line in out.splitlines() if "plain line" in line)
    assert "[lane" not in plain


# ─── Lanes: deterministic watchdog tests on a virtual clock ───────────────────
#
# The watchdog tests must not race a wall-clock threshold against work done. A virtual clock
# replaces asyncio.sleep: time only advances when every task has settled, by jumping to the
# earliest sleeper. Progress is read from the heartbeat (injected clock) and judged with the
# same predicate the watchdog uses (`_is_stalled`).

_SETTLE_YIELDS = 20
_VIRTUAL_STALL_THRESHOLD_S = 1.0
_VIRTUAL_RUN_S = 10.0
_VIRTUAL_MAX_STEPS = 20_000


class _VirtualClock:
    def __init__(self) -> None:
        self.now = 1_000_000.0
        self._waiters: list[tuple[float, int, asyncio.Future[None]]] = []
        self._seq = itertools.count()

    def time(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        future: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        heapq.heappush(self._waiters, (self.now + max(delay, 0.0), next(self._seq), future))
        await future

    async def settle(self) -> None:
        for _ in range(_SETTLE_YIELDS):
            await _REAL_SLEEP(0)

    async def step(self) -> bool:
        """Wake the earliest live sleeper (jumping time to it), then let everything settle."""
        while self._waiters:
            wake_at, _, future = heapq.heappop(self._waiters)
            if future.done():
                continue  # a cancelled sleeper
            self.now = max(self.now, wake_at)
            future.set_result(None)
            await self.settle()
            return True
        return False


@pytest.fixture
def virtual_clock(monkeypatch: pytest.MonkeyPatch) -> _VirtualClock:
    clock = _VirtualClock()
    monkeypatch.setattr(worker_module.asyncio, "sleep", clock.sleep)
    return clock


async def _run_virtual(
    clock: _VirtualClock,
    heartbeat: _Heartbeat,
    *,
    threshold_s: float,
    run_for_s: float,
) -> bool:
    """Advance virtual time until the watchdog predicate trips or `run_for_s` elapsed.
    Returns True when it tripped."""
    start = clock.now
    await clock.settle()
    for _ in range(_VIRTUAL_MAX_STEPS):
        if _is_stalled(clock.now, heartbeat.last_progress, threshold_s):
            return True
        if clock.now - start > run_for_s or not await clock.step():
            return False
    raise AssertionError("virtual run did not finish within the step budget")


def _start_virtual_lanes(
    stats: _LaneStats, clock: _VirtualClock, *, lanes: int, idle_sleep: float, client: AsyncMock
) -> tuple[asyncio.Task[None], _Heartbeat]:
    heartbeat = _Heartbeat(None, lanes=lanes, clock=clock.time)
    task = asyncio.create_task(
        _run_lanes(
            clients=[client],
            pool=_make_lane_pool(stats),
            sf_version="sf18",
            idle_sleep=idle_sleep,
            dry_run=False,
            lanes=lanes,
            heartbeat=heartbeat,
        )
    )
    return task, heartbeat


async def test_wedged_lane_trips_the_watchdog_while_siblings_keep_working(
    virtual_clock: _VirtualClock,
) -> None:
    """A lane that never finishes keeps the oldest progress slot pinned, so the watchdog
    predicate trips even though the other lanes keep completing cycles and marking."""
    stats = _LaneStats()
    never = asyncio.Event()
    wedged = False

    async def wedge_first_search() -> None:
        nonlocal wedged
        if not wedged:
            wedged = True
            await never.wait()

    stats.eval_hook = wedge_first_search
    task, heartbeat = _start_virtual_lanes(
        stats, virtual_clock, lanes=3, idle_sleep=0.01, client=_make_lane_client(stats)
    )
    try:
        tripped = await _run_virtual(
            virtual_clock,
            heartbeat,
            threshold_s=_VIRTUAL_STALL_THRESHOLD_S,
            run_for_s=_VIRTUAL_RUN_S,
        )
        assert tripped, "a wedged lane must trip the watchdog"
        assert stats.total_submits >= 5, "the healthy lanes were working while one lane wedged"
    finally:
        await _cancel_lane_tasks(task)


async def test_healthy_lanes_never_trip_the_watchdog(virtual_clock: _VirtualClock) -> None:
    """Every lane completes cycles and marks ITS OWN slot, so the oldest slot keeps
    advancing and the watchdog never fires over many thresholds' worth of time."""
    stats = _LaneStats()
    task, heartbeat = _start_virtual_lanes(
        stats, virtual_clock, lanes=3, idle_sleep=0.01, client=_make_lane_client(stats)
    )
    try:
        tripped = await _run_virtual(
            virtual_clock,
            heartbeat,
            threshold_s=_VIRTUAL_STALL_THRESHOLD_S,
            run_for_s=_VIRTUAL_RUN_S,
        )
        assert not tripped
        assert set(stats.submits_by_task) == {f"{_LANE_TASK_PREFIX}{i}" for i in range(3)}
    finally:
        await _cancel_lane_tasks(task)


async def test_idle_lanes_with_scaled_idle_sleep_never_trip_the_watchdog(
    virtual_clock: _VirtualClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reviewer's scenario scaled down 1000x: a stall threshold of 0.72 s, an idle sleep
    of 0.06 s and 7 lanes on empty queues. Unclamped, the last lane's first mark would come
    at (2L-1) x idle = 0.78 s and trip the watchdog; the lane idle sleep and the stagger are
    clamped, so no healthy idle worker is ever killed."""
    scaled_threshold_s = 0.72
    monkeypatch.setattr(worker_module, "MAX_LANE_IDLE_SLEEP_S", 0.1)
    monkeypatch.setattr(worker_module, "MAX_LANE_STAGGER_S", 0.1)
    idle_client = AsyncMock()
    idle_client.post = AsyncMock(return_value=_make_response(204))
    task, heartbeat = _start_virtual_lanes(
        _LaneStats(), virtual_clock, lanes=7, idle_sleep=0.06, client=idle_client
    )
    try:
        tripped = await _run_virtual(
            virtual_clock, heartbeat, threshold_s=scaled_threshold_s, run_for_s=_VIRTUAL_RUN_S
        )
        assert not tripped
    finally:
        await _cancel_lane_tasks(task)


# ─── Lanes: transient streak, wiring, lane-end semantics ──────────────────────

_ALERT_S = TRANSIENT_FAILURE_ALERT_S


def _scripted_client(
    clock: dict[str, float], script: list[tuple[float, BaseException | None]]
) -> AsyncMock:
    """A client whose Nth post sets the fake wall clock, then raises the scripted exception
    or answers 204 (a fully idle ladder takes five posts)."""
    remaining = iter(script)

    async def post(*_args: object, **_kwargs: object) -> MagicMock:
        at, outcome = next(remaining)
        clock["t"] = at
        if outcome is not None:
            raise outcome
        return _make_response(204)

    client = AsyncMock()
    client.post = AsyncMock(side_effect=post)
    return client


async def _run_scripted_loop(
    client: AsyncMock, clock: dict[str, float], *, lane: _LaneContext | None = None
) -> MagicMock:
    """Run _run_loop (looping) until the script's CancelledError; return capture_message."""
    with (
        patch("scripts.remote_eval_worker.time.time", side_effect=lambda: clock["t"]),
        patch("scripts.remote_eval_worker.asyncio.sleep", new_callable=AsyncMock),
        patch("scripts.remote_eval_worker.sentry_sdk.capture_message") as capture_message,
        pytest.raises(asyncio.CancelledError),
    ):
        await _run_loop(
            clients=[client],
            pool=AsyncMock(),
            sf_version="sf18",
            idle_sleep=1.0,
            dry_run=False,
            loop=True,
            lane=lane,
        )
    return capture_message


def _idle_ladder() -> list[tuple[float, BaseException | None]]:
    return [(0.0, None)] * 5


def _transient(at: float) -> tuple[float, BaseException | None]:
    return (at, httpx.ConnectError("down"))


_STOP: tuple[float, BaseException | None] = (0.0, asyncio.CancelledError())


async def test_sustained_outage_escalates_exactly_one_event_single_loop() -> None:
    clock = {"t": 0.0}
    client = _scripted_client(
        clock, [_transient(0.0), _transient(_ALERT_S + 1), _transient(_ALERT_S + 2), _STOP]
    )
    capture_message = await _run_scripted_loop(client, clock)
    assert capture_message.call_count == 1


async def test_successful_cycle_resets_the_streak_single_loop() -> None:
    """After a success a new failure starts a NEW streak instead of continuing the old one,
    so a failure far later than the alert threshold does not escalate."""
    clock = {"t": 0.0}
    client = _scripted_client(
        clock, [_transient(0.0), *_idle_ladder(), _transient(_ALERT_S + 10), _STOP]
    )
    capture_message = await _run_scripted_loop(client, clock)
    assert capture_message.call_count == 0


async def test_lanes_share_one_streak_and_escalate_one_event() -> None:
    """Two lanes failing in turn on ONE shared streak escalate a single event; a lane with
    its own streak would restart the clock and never escalate."""
    clock = {"t": 0.0}
    streak = _TransientStreak()
    shared = {"entry_lock": asyncio.Lock(), "streak": streak}
    lane_a = _LaneContext(index=0, **shared)
    lane_b = _LaneContext(index=1, **shared)
    await _run_scripted_loop(_scripted_client(clock, [_transient(0.0), _STOP]), clock, lane=lane_a)
    capture_message = await _run_scripted_loop(
        _scripted_client(clock, [_transient(_ALERT_S + 1), _transient(_ALERT_S + 2), _STOP]),
        clock,
        lane=lane_b,
    )
    assert capture_message.call_count == 1


async def test_success_in_any_lane_resets_the_shared_streak() -> None:
    clock = {"t": 0.0}
    streak = _TransientStreak()
    shared = {"entry_lock": asyncio.Lock(), "streak": streak}
    await _run_scripted_loop(
        _scripted_client(clock, [_transient(0.0), _STOP]),
        clock,
        lane=_LaneContext(index=0, **shared),
    )
    assert streak.start is not None
    await _run_scripted_loop(
        _scripted_client(clock, [*_idle_ladder(), _STOP]),
        clock,
        lane=_LaneContext(index=1, **shared),
    )
    assert streak.start is None
    assert streak.alerted is False


def _run_async_args() -> argparse.Namespace:
    return argparse.Namespace(
        base_url="http://127.0.0.1:9",
        fallback_url=None,
        fallback_token=None,
        workers=18,
        idle_sleep=1.0,
        dry_run=False,
        once=False,
    )


@pytest.mark.parametrize("lanes", [1, 3])
async def test_run_async_builds_one_heartbeat_slot_per_lane(lanes: int) -> None:
    """A heartbeat with fewer slots than lanes would IndexError on the first mark of a
    higher lane and take the whole group down."""
    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()
    try:
        with patch(
            "scripts.remote_eval_worker.run_worker", new_callable=AsyncMock
        ) as run_worker_mock:
            await _run_async(_run_async_args(), "tok", "wid", supervised=True, lanes=lanes)
    finally:
        loop.set_exception_handler(previous_handler)

    kwargs = run_worker_mock.await_args.kwargs if run_worker_mock.await_args else {}
    assert kwargs["lanes"] == lanes
    assert len(kwargs["heartbeat"]._lane_progress) == lanes


@pytest.mark.parametrize(
    ("once", "dry_run", "expected"), [(True, False, 1), (False, True, 1), (False, False, 7)]
)
def test_main_hands_the_effective_lane_count_to_run_async(
    monkeypatch: pytest.MonkeyPatch, once: bool, dry_run: bool, expected: int
) -> None:
    args = _run_async_args()
    args.token = "tok"
    args.worker_id = "wid"
    args.lanes = 7
    args.once = once
    args.dry_run = dry_run
    monkeypatch.setenv(worker_module._CHILD_MARKER_ENV, worker_module._CHILD_MARKER_VALUE)
    fake_settings = MagicMock(
        EVAL_OPERATOR_TOKEN="tok", EVAL_FALLBACK_OPERATOR_TOKEN="", SENTRY_DSN="", ENVIRONMENT="t"
    )
    run_async_mock = AsyncMock()
    with (
        patch.object(worker_module, "parse_args", return_value=args),
        patch.object(worker_module, "settings", fake_settings),
        patch.object(worker_module, "_run_async", run_async_mock),
    ):
        assert main() == 0

    run_async_mock.assert_awaited_once()
    assert run_async_mock.await_args is not None
    assert run_async_mock.await_args.kwargs["lanes"] == expected


@pytest.mark.parametrize("ending", ["returns", "cancelled"])
async def test_run_lanes_fails_the_group_when_one_lane_ends(ending: str) -> None:
    """Lanes are infinite loops: one that returns, or ends with a CancelledError nobody
    issued (a bare TaskGroup ignores it), must take the whole group down instead of the
    process silently continuing on fewer lanes."""
    block = asyncio.Event()

    async def lane_loop(**kwargs: object) -> None:
        lane = cast(_LaneContext, kwargs["lane"])
        if lane.index == 1:
            if ending == "cancelled":
                raise asyncio.CancelledError
            return
        await block.wait()

    with patch("scripts.remote_eval_worker._run_loop", side_effect=lane_loop):
        with pytest.raises(ExceptionGroup) as info:
            await asyncio.wait_for(
                _run_lanes(
                    clients=[AsyncMock()],
                    pool=AsyncMock(),
                    sf_version="sf18",
                    idle_sleep=0.001,
                    dry_run=False,
                    lanes=3,
                    heartbeat=None,
                ),
                timeout=_LANE_WAIT_S,
            )
    assert any(isinstance(exc, RuntimeError) for exc in info.value.exceptions)
    assert _surviving_lane_tasks() == []
