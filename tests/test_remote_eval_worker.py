"""Unit tests for the remote eval worker CLI (Phase 123 SEED-051, Plan 03).

Covers:
- worker_id_default_length: generated default IDs are < 10 chars, base36 charset.
- worker_id_override_too_long: --worker-id >= 10 chars raises SystemExit (parser.error);
  < 10 chars accepted as-is.
- ladder_explicit_first: with /atomic-lease?scope=explicit returning 200, the cycle
  submits via /atomic-submit and does NOT call /entry-lease (busy path stays 1-2 calls).
- ladder_entry_then_idle: scope=explicit 204 -> /entry-lease 200 -> /entry-submit; on
  /entry-lease 204 falls through to scope=idle (also /atomic-lease, Phase 147 Part B).
- entry_eval_uses_depth15: _eval_entry_positions calls pool.evaluate (depth-15) and
  never calls pool.evaluate_nodes_with_pv (the 1M-node full-ply mode).
- Phase 147 SEED-074 Part B (atomic rung): _hint_flaw_plies/_build_blob_walk_targets/
  _eval_atomic_game — the local hint stays MultiPV-1 for the full-ply pass, selects
  only mistake/blunder plies, and the assembled /atomic-submit payload carries
  blob_nodes only for those hinted plies plus worker_schema_version.

All tests are unit-level -- no DB, no real Stockfish. Engine pool and httpx are mocked.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, call, patch

import chess
import pytest

# Ensure project root is importable from the test root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

from scripts.remote_eval_worker import (
    STALL_THRESHOLD_S,
    TRANSIENT_FAILURE_ALERT_S,
    _WORKER_ID_ALPHABET,
    _WORKER_ID_DEFAULT_LEN,
    HTTP_TIMEOUT_S,
    WORKER_ID_MAX_LEN,
    WORKER_SCHEMA_VERSION,
    _build_blob_walk_targets,
    _eval_atomic_game,
    _eval_entry_positions,
    _eval_flaw_blob_positions,
    _generate_worker_id,
    _handle_transient_failure,
    _Heartbeat,
    _hint_flaw_plies,
    _is_expected_transient,
    _is_stalled,
    _run_cycle,
    _worker_role,
    parse_args,
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
    """When /atomic-lease?scope=explicit returns 200, the cycle submits via
    /atomic-submit only (Phase 147 SEED-074 Part B — rung 1 upgraded).

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

    await _run_cycle(
        client=client,
        pool=pool,
        sf_version="sf16",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )

    # First call: /atomic-lease with scope=explicit
    first_call = client.post.call_args_list[0]
    assert first_call == call("/api/eval/remote/atomic-lease", params={"scope": "explicit"})

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

    await _run_cycle(
        client=client,
        pool=pool,
        sf_version="sf16",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )

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
    (also via /atomic-lease, Phase 147 SEED-074 Part B — rung 3 upgraded).
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

    await _run_cycle(
        client=client,
        pool=pool,
        sf_version="sf16",
        idle_sleep=1.0,
        dry_run=False,
        loop=False,
    )

    called_urls = [c.args[0] for c in client.post.call_args_list]
    assert called_urls[0] == "/api/eval/remote/atomic-lease"  # scope=explicit
    assert called_urls[1] == "/api/eval/remote/entry-lease"
    assert called_urls[2] == "/api/eval/remote/atomic-lease"  # scope=idle
    assert called_urls[3] == "/api/eval/remote/atomic-submit"

    # Confirm the idle atomic-lease call used scope=idle param
    idle_lease_call = client.post.call_args_list[2]
    assert idle_lease_call == call("/api/eval/remote/atomic-lease", params={"scope": "idle"})


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


# ─── Phase 147 SEED-074 Part B: atomic eval+blob rung tests ─────────────────
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

# CR-02 fix (147-REVIEW.md): `evals` is POSITION-keyed (the eval OF the board
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
    GamePosition objects, POST-MOVE shifted by one (CR-02), and keeps only
    mistake/blunder plies (Q4/RESEARCH A2).

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
    token-keyed per the D-04a scheme ("{flaw_ply}:{line}:{node_k}").
    """
    boards, tokens = _build_blob_walk_targets(_ATOMIC_POSITIONS, _ATOMIC_EVALS, {1})

    assert tokens == ["1:missed:0", "1:allowed:0"]
    assert len(boards) == 2
    assert all(isinstance(b, chess.Board) for b in boards)


def test_build_blob_walk_targets_skips_line_with_no_start_fen() -> None:
    """A flaw_ply at the game's last ply has no allowed-line start FEN (flaw_ply + 1
    does not exist in the lease payload) -- skipped, not crashed. The server
    independently re-derives this as a D-06 sentinel (T-147-03; never trusts
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
    never MultiPV-2, for the /atomic-submit evals list (Phase 146 D-03 invariant
    still holds under the new atomic rung — mirrors
    test_eval_positions_uses_multipv1_no_second_best).
    """
    pool = AsyncMock()
    pool.evaluate_nodes_with_pv = AsyncMock(
        side_effect=[(0, None, "e2e4", None), (600, None, "d7d5", None), (600, None, "g1f3", None)]
    )
    pool.evaluate_nodes_multipv2 = AsyncMock(
        return_value=(0, None, "a2a3", "a2a3", 0, None, "b2b3")
    )

    evals, _blob_nodes = await _eval_atomic_game(pool, _ATOMIC_POSITIONS)

    assert pool.evaluate_nodes_with_pv.call_count == 3
    for r in evals:
        assert "second_cp" not in r, "second_cp must not appear in the full-ply evals (D-03)"
        assert "second_mate" not in r, "second_mate must not appear in the full-ply evals (D-03)"
        assert "second_uci" not in r, "second_uci must not appear in the full-ply evals (D-03)"


async def test_eval_atomic_game_hints_and_blobs_flaw_plies_only() -> None:
    """_eval_atomic_game: full-ply MultiPV-1 pass -> local hint -> MultiPV-2 blobs
    only for the hinted flaw ply (mistake/blunder), token-keyed per D-04a.

    Uses _HINTED_BLUNDER_POSITIONS/_HINTED_BLUNDER_EVALS (CR-02 cross-validated
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

    evals, blob_nodes = await _eval_atomic_game(pool, _HINTED_BLUNDER_POSITIONS)

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

    evals, blob_nodes = await _eval_atomic_game(pool, positions)

    assert len(evals) == 2
    assert blob_nodes == []
    pool.evaluate_nodes_multipv2.assert_not_called()


async def test_atomic_submit_payload_shape_and_schema_version() -> None:
    """The /atomic-submit body carries evals + blob_nodes together with
    worker_schema_version, matching the 147-04 AtomicSubmitRequest schema, and
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


# ─── SEED-063: supervisor/child/once dispatch + watchdog stall predicate ────


def test_worker_role_once_no_marker() -> None:
    """--once with no child marker returns "once"."""
    assert _worker_role(once=True, child_marker=False) == "once"


def test_worker_role_child_marker_set() -> None:
    """No --once but the child marker is set returns "child"."""
    assert _worker_role(once=False, child_marker=True) == "child"


def test_worker_role_supervisor_default() -> None:
    """No --once and no child marker (the default, top-level invocation) returns
    "supervisor" (SEED-063 D3: always supervised unless --once).
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
    """An idle-but-healthy gap under threshold_s is NOT a stall (SEED-063:
    a clean 204 idle cycle counts as progress; this only guards the boundary
    predicate itself).
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
    (SEED-063: writing must never kill the worker).
    """
    # Point the heartbeat at a path whose parent directory does not exist, so the
    # write raises OSError (FileNotFoundError is an OSError subclass).
    heartbeat = _Heartbeat(tmp_path / "missing-dir" / "worker.heartbeat")
    heartbeat.mark()  # must not raise


def test_stall_threshold_s_is_minutes_not_seconds() -> None:
    """STALL_THRESHOLD_S must clear the slowest legit cycle (~125s worst case) --
    regression guard against an accidental seconds-scale value (SEED-063).
    """
    assert STALL_THRESHOLD_S >= 180.0, (
        f"STALL_THRESHOLD_S is {STALL_THRESHOLD_S}, expected >= 180s (~3-4 minutes)"
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
