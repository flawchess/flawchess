"""Headless remote eval worker for the trusted operator eval pipeline (Phase 120 SEED-048).

Runs on a trusted off-box machine. Loops: lease the next eval game (tier-1 > tier-2 >
tier-3) from the FlawChess API, evaluate all its FENs locally via EnginePool, and
batch-submit the results — tier-1/tier-2 claims echo a job token so the server stamps
the eval_jobs row complete on submit (Phase 121 SEED-048). The server
owns the SEED-044 storage convention (post-move shift, ply keying) — this worker passes
engine results through UNCHANGED (D-2 / pitfall 1: no client-side post-move shift).

The operator token is read from EVAL_OPERATOR_TOKEN in the environment or the .env
file (loaded via app settings); --token overrides it for one-off runs. --base-url
defaults to the production API, so with the token in .env the worker needs no flags.

Usage:
    # Connectivity test (lease + eval only, no submit):
    uv run python scripts/remote_eval_worker.py --dry-run --once

    # Single game then exit:
    uv run python scripts/remote_eval_worker.py --once

    # Continuous loop (default), against the production API:
    uv run python scripts/remote_eval_worker.py

    # Point at a local/staging server:
    uv run python scripts/remote_eval_worker.py --base-url http://localhost:8000
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import secrets
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import FrameType
from typing import Literal, cast

import chess
import httpx
import sentry_sdk

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import ORM model registry so the SQLAlchemy mapper fully configures. Required by
# any app.* import chain that transitively touches FastAPI-Users' relationship
# (User.oauth_accounts → OAuthAccount). Pattern from scripts/resweep_holed_games.py.
import app.models.oauth_account  # noqa: E402, F401
import app.models.user  # noqa: E402, F401

from app.core.config import settings  # noqa: E402
from app.models.game_position import GamePosition  # noqa: E402
from app.services.engine import PV_CAP_PLIES, EnginePool, get_stockfish_version  # noqa: E402

# Phase 147 SEED-074 Part B: worker-side hint classification + PV walk reuse the
# fat `app.*` client pattern already established for _eval_flaw_blob_positions —
# this worker imports server-internal helpers directly rather than duplicating them.
# _walk_pv_boards / _run_all_moves_pass are leading-underscore "module-private" by
# convention only; app/routers/eval_remote.py already imports _derive_atomic_sentinel_lines
# the same way (precedent), so this is consistent cross-module reuse, not a layering break.
from app.services.eval_drain import _walk_pv_boards  # noqa: E402
from app.services.flaws_service import _run_all_moves_pass  # noqa: E402

# ─── Named constants (no magic numbers) ──────────────────────────────────────

DEFAULT_BASE_URL: str = "https://flawchess.com"
DEFAULT_WORKERS: int = 4
# Lowered from 5.0 to 1.0 (Phase 121): only the empty-queue / 204 path sleeps,
# so this affects only idle-pickup latency for a freshly-enqueued tier-1 job.
# The busy path (a game was leased) is already a tight loop — unchanged.
DEFAULT_IDLE_SLEEP: float = 1.0
HTTP_TIMEOUT_S: float = 30.0
# D-10 (Phase 123 SEED-051): worker IDs must fit VARCHAR(16) on games.entry_eval_leased_by.
# Random default is ~8 base36 chars; operator override is validated < 10 chars.
WORKER_ID_MAX_LEN: int = 9  # exclusive upper bound: len < 10
_WORKER_ID_ALPHABET: str = "0123456789abcdefghijklmnopqrstuvwxyz"
_WORKER_ID_DEFAULT_LEN: int = 8

# Phase 147 SEED-074 Part B (Q5, RESEARCH.md "Claude's Discretion"): observability
# and stale-worker rejection ONLY — the server never gates correctness on this
# value, it always re-classifies authoritatively. Bump when the atomic submit
# payload shape changes in a way the server should be able to distinguish.
WORKER_SCHEMA_VERSION: int = 1

# SEED-063 D3: internal marker distinguishing the supervisor (parent, no marker) from
# the child (marker set) it spawns. NOT an argparse flag — kept out of --help (D3).
_CHILD_MARKER_ENV: str = "_FLAWCHESS_WORKER_CHILD"
_CHILD_MARKER_VALUE: str = "1"
# Fixed-small backoff before relaunching a crashed/wedged child (SEED-063: fixed, NOT
# capped-exponential -- predictable behavior for volunteers watching the logs).
SUPERVISOR_BACKOFF_S: float = 3.0


# ─── Logging helper ───────────────────────────────────────────────────────────


def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


# ─── Worker-ID helper ────────────────────────────────────────────────────────


def _generate_worker_id() -> str:
    """Generate a random ~8-char base36 worker ID for D-10 / SEED-051.

    Uses secrets.randbelow for each character to ensure cryptographic randomness.
    Result is guaranteed < 10 chars, fitting VARCHAR(16) with headroom (D-09).
    """
    return "".join(
        _WORKER_ID_ALPHABET[secrets.randbelow(len(_WORKER_ID_ALPHABET))]
        for _ in range(_WORKER_ID_DEFAULT_LEN)
    )


# ─── Eval helper ─────────────────────────────────────────────────────────────


async def _eval_positions(
    pool: EnginePool,
    positions: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Evaluate all positions from a lease response via EnginePool fan-out.

    Returns a list of eval dicts keyed by ply. Results are passed through
    UNCHANGED from the engine — NO post-move shift, NO transformation.
    The server owns the SEED-044 storage convention (D-2 / pitfall 1).

    Phase 146 D-03 consequence: reduced to MultiPV-1 (evaluate_nodes_with_pv, 4-tuple) now
    that per-ply second-best was dropped from SubmitEval. The tier-4 blob rung
    (_eval_flaw_blob_positions) still evaluates at MultiPV-2 where the blob contract
    requires second-best.

    Each position dict contains: ply, fen, is_terminal.
    Each output dict contains:  ply, eval_cp, eval_mate, best_move, pv.
    """
    boards: list[chess.Board] = [chess.Board(str(pos["fen"])) for pos in positions]
    results = await asyncio.gather(*(pool.evaluate_nodes_with_pv(b) for b in boards))
    return [
        {
            "ply": pos["ply"],
            "eval_cp": r[0],
            "eval_mate": r[1],
            "best_move": r[2],
            "pv": r[3],
        }
        for pos, r in zip(positions, results)
    ]


async def _eval_flaw_blob_positions(
    pool: EnginePool,
    positions: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Evaluate flaw-blob positions at MultiPV=2 and echo tokens (D-04a).

    Worker stays token-opaque: the token is echoed unchanged from the lease response;
    the server holds the flaw-structure reassembly map. Returns dicts with keys:
    {token, best_cp, best_mate, second_cp, second_mate, second_uci}.

    The MultiPV-2 engine call returns a 7-tuple:
        (eval_cp, eval_mate, best_move, pv, second_cp, second_mate, second_uci)
    Indices r[2] (best_move) and r[3] (pv) are intentionally NOT included in the
    output — these are PV-continuation FENs, not game plies. Indices are mapped
    explicitly to avoid off-by-one errors (RESEARCH Pitfall 3).

    asyncio.gather is safe here — no AsyncSession is open in the worker process.
    The CLAUDE.md gather rule applies to the server only (RESEARCH Pitfall 6).
    """
    boards: list[chess.Board] = [chess.Board(str(pos["fen"])) for pos in positions]
    results = await asyncio.gather(*(pool.evaluate_nodes_multipv2(b) for b in boards))
    return [
        {
            "token": str(pos["token"]),  # echoed unchanged (D-04a)
            "best_cp": r[0],
            "best_mate": r[1],
            "second_cp": r[4],
            "second_mate": r[5],
            "second_uci": r[6],
        }
        for pos, r in zip(positions, results)
    ]


# ─── Atomic eval+blob helpers (Phase 147 SEED-074 Part B) ────────────────────


def _hint_flaw_plies(evals: list[dict[str, object]]) -> set[int]:
    """LOCAL flaw-ply HINT via `_run_all_moves_pass` (mistake/blunder only).

    Builds lightweight in-memory `GamePosition` objects (never persisted — no
    session, no flush, no DB round-trip) carrying only the ply-indexed
    `eval_cp`/`eval_mate` this worker just computed in the full-ply MultiPV-1
    pass, matching the SEED-044 post-move eval convention `_run_all_moves_pass`
    expects. No PGN, no `Game` row needed (Q4/RESEARCH A2 — the narrower hint).

    This is a HINT ONLY (T-147-03): it decides which plies get a MultiPV-2
    continuation blob walked below, nothing more. The server re-runs
    `classify_game_flaws` authoritatively on its own `game_positions` and never
    trusts which plies this function returns.
    """
    eval_by_ply: dict[int, dict[str, object]] = {int(cast(int, e["ply"])): e for e in evals}
    if not eval_by_ply:
        return set()
    max_ply = max(eval_by_ply)

    # CR-02 fix: evals is POSITION-keyed (eval OF the board at `ply`), but
    # _run_all_moves_pass expects ROW-keyed / POST-MOVE values — row `m` must
    # hold pos_eval[m + 1], matching _post_move_eval (app/services/eval_drain.py).
    # Without this +1 shift, hint_positions[k] == db_row[k-1], which
    # systematically reports the flaw one ply off (see CR-02, 147-REVIEW.md).
    hint_positions: list[GamePosition] = []
    for row_ply in range(max_ply):  # one hint row per real move (0..max_ply-1)
        pos = GamePosition()
        pos.ply = row_ply
        e = eval_by_ply.get(row_ply + 1)
        pos.eval_cp = cast("int | None", e["eval_cp"]) if e is not None else None
        pos.eval_mate = cast("int | None", e["eval_mate"]) if e is not None else None
        hint_positions.append(pos)

    all_moves = _run_all_moves_pass(hint_positions)
    return {
        ply
        for ply, (_mover, severity, _es_before, _es_after) in all_moves.items()
        if severity in ("mistake", "blunder")
    }


def _build_blob_walk_targets(
    positions: list[dict[str, object]],
    evals: list[dict[str, object]],
    flaw_plies: set[int],
) -> tuple[list[chess.Board], list[str]]:
    """Walk the missed/allowed PV lines for each hinted flaw ply.

    Mirrors the server's own walk (`_derive_atomic_sentinel_lines`,
    `app/services/eval_drain.py`): missed line starts at the board for
    `flaw_ply` (the position the flaw-maker faced), allowed line starts at the
    board for `flaw_ply + 1` (the position after the flaw move — the
    refutation's starting point). D-04a token scheme reused: `"{flaw_ply}:{line}:{node_k}"`.

    A line whose start ply has no FEN in this lease payload (e.g. flaw_ply is
    the game's last ply, so flaw_ply + 1 does not exist) is simply skipped —
    the server independently re-derives sentinel status for any line this
    worker could not walk (T-147-03; never trusts which lines were sent).
    """
    fen_by_ply: dict[int, str] = {int(cast(int, p["ply"])): str(p["fen"]) for p in positions}
    pv_by_ply: dict[int, str | None] = {
        int(cast(int, e["ply"])): cast("str | None", e.get("pv")) for e in evals
    }

    boards: list[chess.Board] = []
    tokens: list[str] = []
    for flaw_ply in sorted(flaw_plies):
        for line, node0_ply in (("missed", flaw_ply), ("allowed", flaw_ply + 1)):
            start_fen = fen_by_ply.get(node0_ply)
            if start_fen is None:
                continue
            walk = _walk_pv_boards(chess.Board(start_fen), pv_by_ply.get(node0_ply), PV_CAP_PLIES)
            for k, board in enumerate(walk):
                boards.append(board)
                tokens.append(f"{flaw_ply}:{line}:{k}")
    return boards, tokens


async def _eval_atomic_blob_nodes(
    pool: EnginePool,
    boards: list[chess.Board],
    tokens: list[str],
) -> list[dict[str, object]]:
    """Evaluate walked continuation boards at MultiPV=2, echoing tokens (D-04a).

    Mirrors `_eval_flaw_blob_positions`' index mapping exactly (r[0]/r[1]/r[4]/
    r[5]/r[6]; r[2]=best_move and r[3]=pv are intentionally excluded — these are
    PV-continuation FENs, not game plies). `asyncio.gather` is safe here — no
    `AsyncSession` is open in the worker process (CLAUDE.md gather rule applies
    to the server only, RESEARCH Pitfall 6).
    """
    results = await asyncio.gather(*(pool.evaluate_nodes_multipv2(b) for b in boards))
    return [
        {
            "token": token,
            "best_cp": r[0],
            "best_mate": r[1],
            "second_cp": r[4],
            "second_mate": r[5],
            "second_uci": r[6],
        }
        for token, r in zip(tokens, results)
    ]


async def _eval_atomic_game(
    pool: EnginePool,
    positions: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Evaluate full-ply (MultiPV-1), then locally hint + blob flaw plies (Part B).

    The full-ply pass reuses `_eval_positions` UNCHANGED (MultiPV-1 — Phase 146
    D-03 invariant; MUST NOT regress to MultiPV-2, see
    `test_eval_positions_uses_multipv1_no_second_best`). The local hint
    (`_hint_flaw_plies`) is computed purely from the just-evaluated eval_cp/
    eval_mate and is NEVER submitted or trusted as authoritative (T-147-03) — it
    only decides which plies get a MultiPV-2 continuation blob walked and
    evaluated for the server to use as gate input in its own independent
    classify.

    Returns (evals, blob_nodes) — both go straight into the /atomic-submit body.
    """
    evals = await _eval_positions(pool, positions)
    flaw_plies = _hint_flaw_plies(evals)
    boards, tokens = _build_blob_walk_targets(positions, evals, flaw_plies)
    blob_nodes = await _eval_atomic_blob_nodes(pool, boards, tokens) if boards else []
    return evals, blob_nodes


async def _eval_entry_positions(
    pool: EnginePool,
    positions: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Evaluate entry-ply positions at depth-15 via EnginePool fan-out.

    CRITICAL: uses pool.evaluate (depth-15), NOT pool.evaluate_nodes_with_pv
    (the 1M-node full-ply mode). Mixing modes makes entry-ply 10x slower
    and uses the wrong eval budget (D-2 / RESEARCH Anti-pattern).

    Entry-ply carries no best_move/pv — depth-15 returns only (cp, mate).
    The server owns the SEED-044 storage convention; the worker passes
    eval_cp/eval_mate through UNCHANGED (D-2 / pitfall 1).

    Each position dict contains: game_id, ply, fen.
    Each output dict contains:  game_id, ply, eval_cp, eval_mate.
    """
    boards: list[chess.Board] = [chess.Board(str(pos["fen"])) for pos in positions]
    results = await asyncio.gather(*(pool.evaluate(b) for b in boards))
    return [
        {
            "game_id": pos["game_id"],
            "ply": pos["ply"],
            "eval_cp": r[0],
            "eval_mate": r[1],
        }
        for pos, r in zip(positions, results)
    ]


# ─── Main worker loop ─────────────────────────────────────────────────────────


async def _run_loop(
    client: httpx.AsyncClient,
    pool: EnginePool,
    sf_version: str,
    idle_sleep: float,
    dry_run: bool,
    loop: bool,
) -> None:
    """Inner lease → eval → submit loop.

    On 204 (empty queue): sleep `idle_sleep` seconds and continue if `loop`,
    else return. On 2xx lease response: evaluate all positions, then submit
    unless `dry_run`. Exits cleanly when `not loop` after one game cycle.

    Each cycle is wrapped in an exception boundary: a transient network error,
    a 5xx (raise_for_status), or a bad FEN must not kill a continuous daemon. The
    exception is Sentry-captured (CLAUDE.md rule for operational except blocks) and,
    when looping, the worker backs off `idle_sleep` and retries. When not looping the
    exception propagates so --once surfaces failures with a non-zero exit.
    """
    while True:
        try:
            if await _run_cycle(client, pool, sf_version, idle_sleep, dry_run, loop):
                return
        except (KeyboardInterrupt, asyncio.CancelledError):
            raise
        except Exception:
            # Operational failure (network blip, 5xx, bad FEN). Capture once, then
            # back off and retry if this is a continuous daemon; otherwise re-raise.
            sentry_sdk.capture_exception()
            _log("Cycle failed; see Sentry. Backing off...")
            if not loop:
                raise
            await asyncio.sleep(idle_sleep)


async def _run_cycle(
    client: httpx.AsyncClient,
    pool: EnginePool,
    sf_version: str,
    idle_sleep: float,
    dry_run: bool,
    loop: bool,
) -> bool:
    """Run one D-06 ladder cycle. Returns True when the loop should stop.

    D-06 four-rung ladder (Phase 123 SEED-051; rung 4 added Phase 146 D-04).
    Rungs 1 and 3 upgraded to the atomic (versioned) eval+blob pair in Phase 147
    SEED-074 Part B — this worker now exclusively leases/submits its full-ply
    tiers via /atomic-lease + /atomic-submit so a leased game is never written
    with a raw/ungated tactic tag (D-01). The old /lease + /submit pair stays
    live and untouched server-side for any not-yet-upgraded worker still
    running an older copy of this script during a rolling mixed-fleet deploy
    (D-02) — this file simply no longer calls it:
      1. POST /atomic-lease?scope=explicit (tier-1/2 only)
         200 → eval full-ply (MultiPV-1) + local flaw-ply hint + MultiPV-2
               blobs, submit to /atomic-submit, done.
         204 → fall to rung 2.
      2. POST /entry-lease (entry-ply, gated by D-5 backlog probe server-side)
         200 → eval at depth-15, submit to /entry-submit, done.
         204 → fall to rung 3.
      3. POST /atomic-lease?scope=idle (tier-3 only)
         200 → same atomic eval+blob+submit path as rung 1.
         204 → fall to rung 4.
      4. POST /flaw-blob-lease (tier-4 blob drain, Phase 146 D-04)
         200 → eval continuation FENs at MultiPV-2, submit to /flaw-blob-submit, done.
         204 → all queues empty; sleep idle_sleep.

    Busy paths (tier-1, entry-ply) stay at 1-2 calls. Only the fully-idle path
    makes all 4 round-trips. Entry-ply is always-on (D-08); the server D-5 gate
    makes it cost nothing when there's no big import.

    Returns True only in non-loop mode after a completed cycle (or an idle 204);
    in loop mode it always returns False so _run_loop keeps draining.
    """
    # ── Rung 1: explicit tier-1/2 (atomic eval+blob pair, Phase 147 Part B) ──
    lease_resp = await client.post("/api/eval/remote/atomic-lease", params={"scope": "explicit"})

    if lease_resp.status_code != 204:
        # Got a tier-1/2 game — eval + hint + blob + submit atomically.
        return await _handle_atomic_response(client, pool, sf_version, dry_run, loop, lease_resp)

    # ── Rung 2: entry-ply (gated by D-5 backlog probe server-side) ───────────
    entry_resp = await client.post("/api/eval/remote/entry-lease")

    if entry_resp.status_code != 204:
        # Got entry-ply positions — eval at depth-15, submit to /entry-submit.
        return await _handle_entry_ply_response(client, pool, sf_version, dry_run, loop, entry_resp)

    # ── Rung 3: idle tier-3 (atomic eval+blob pair) ──────────────────────────
    idle_resp = await client.post("/api/eval/remote/atomic-lease", params={"scope": "idle"})

    if idle_resp.status_code == 204:
        # Rung 4: tier-3 empty → try tier-4 flaw-blob drain (Phase 146 D-04).
        blob_resp = await client.post("/api/eval/remote/flaw-blob-lease")
        if blob_resp.status_code == 204:
            _log("Queue fully empty (204). Sleeping...")
            await asyncio.sleep(idle_sleep)
            return not loop
        return await _handle_flaw_blob_response(client, pool, sf_version, dry_run, loop, blob_resp)

    return await _handle_atomic_response(client, pool, sf_version, dry_run, loop, idle_resp)


async def _handle_full_ply_response(
    client: httpx.AsyncClient,
    pool: EnginePool,
    sf_version: str,
    dry_run: bool,
    loop: bool,
    lease_resp: httpx.Response,
) -> bool:
    """Handle a 200 response from /lease (full-ply path). Eval and submit.

    Phase 147 SEED-074 Part B: this rung is no longer wired into `_run_cycle`
    (rungs 1/3 now use `_handle_atomic_response` against /atomic-lease +
    /atomic-submit) but is intentionally left unmodified — the server's
    /lease + /submit pair stays live for any older, not-yet-upgraded copy of
    this script still running elsewhere during a rolling mixed-fleet deploy
    (D-02/D-05).
    """
    lease_resp.raise_for_status()
    data = lease_resp.json()
    game_id = data["game_id"]
    positions = data["positions"]
    # Opaque job token from the lease response (eval_jobs.id for tier-1/2, None for tier-3).
    # The worker stores and echoes it without interpreting it; the server uses it to stamp
    # eval_jobs.status='completed' when the submit is clean and no holes remain.
    job_id = data.get("job_id")

    _log(f"Leased game_id={game_id} ({len(positions)} positions). Evaluating...")
    evals = await _eval_positions(pool, positions)

    if dry_run:
        _log(f"--dry-run: evaluated {len(evals)} positions for game_id={game_id}; skipping submit.")
        return not loop

    submit_resp = await client.post(
        "/api/eval/remote/submit",
        json={
            "game_id": game_id,
            "sf_version": sf_version,
            "evals": evals,
            "job_id": job_id,
        },
    )
    submit_resp.raise_for_status()
    result = submit_resp.json()
    _log(
        f"Submitted game_id={game_id}: stamp_complete={result.get('stamp_complete')}, "
        f"failed_ply_count={result.get('failed_ply_count')}"
    )
    return not loop


async def _handle_atomic_response(
    client: httpx.AsyncClient,
    pool: EnginePool,
    sf_version: str,
    dry_run: bool,
    loop: bool,
    lease_resp: httpx.Response,
) -> bool:
    """Handle a 200 response from /atomic-lease (Phase 147 SEED-074 Part B).

    Evaluates full-ply at MultiPV-1 (unchanged `_eval_positions`), derives a
    LOCAL flaw-ply HINT via `_run_all_moves_pass` (mistake/blunder only —
    never trusted as authoritative, T-147-03), walks + evaluates MultiPV-2
    continuation blobs for those hinted plies, then POSTs the full-ply evals
    and blob nodes TOGETHER to /atomic-submit in one request. The server
    re-runs `classify_game_flaws` authoritatively there and writes gated
    tactic tags + both completion markers in one transaction — this rung
    closes the ungated-window gap the old /lease + /submit pair leaves open
    (D-01): this worker's hint only decides WHICH plies get blobbed, never
    WHAT gets persisted.
    """
    lease_resp.raise_for_status()
    data = lease_resp.json()
    game_id = data["game_id"]
    positions = data["positions"]
    # Opaque job token from the lease response (eval_jobs.id for tier-1/2, None for tier-3).
    # The worker stores and echoes it without interpreting it; the server uses it to stamp
    # eval_jobs.status='completed' when the submit is clean and no holes remain.
    job_id = data.get("job_id")

    _log(f"Atomic-leased game_id={game_id} ({len(positions)} positions). Evaluating...")
    evals, blob_nodes = await _eval_atomic_game(pool, positions)

    if dry_run:
        _log(
            f"--dry-run: evaluated {len(evals)} positions + {len(blob_nodes)} blob nodes "
            f"for game_id={game_id}; skipping submit."
        )
        return not loop

    submit_resp = await client.post(
        "/api/eval/remote/atomic-submit",
        json={
            "game_id": game_id,
            "sf_version": sf_version,
            "worker_schema_version": WORKER_SCHEMA_VERSION,
            "evals": evals,
            "blob_nodes": blob_nodes,
            "job_id": job_id,
        },
    )
    submit_resp.raise_for_status()
    result = submit_resp.json()
    _log(
        f"Atomic-submitted game_id={game_id}: flaws_written={result.get('flaws_written')}, "
        f"blobs_written={result.get('blobs_written')}"
    )
    return not loop


async def _handle_entry_ply_response(
    client: httpx.AsyncClient,
    pool: EnginePool,
    sf_version: str,
    dry_run: bool,
    loop: bool,
    entry_resp: httpx.Response,
) -> bool:
    """Handle a 200 response from /entry-lease (depth-15 entry-ply path)."""
    entry_resp.raise_for_status()
    data = entry_resp.json()
    positions = data["positions"]

    _log(f"Leased {len(positions)} entry-ply position(s). Evaluating at depth-15...")
    evals = await _eval_entry_positions(pool, positions)

    if dry_run:
        _log(f"--dry-run: evaluated {len(evals)} entry-ply positions; skipping submit.")
        return not loop

    submit_resp = await client.post(
        "/api/eval/remote/entry-submit",
        json={
            "sf_version": sf_version,
            "evals": evals,
        },
    )
    submit_resp.raise_for_status()
    result = submit_resp.json()
    _log(
        f"Entry-submit complete: game_ids={result.get('game_ids')}, "
        f"stamped_count={result.get('stamped_count')}"
    )
    return not loop


async def _handle_flaw_blob_response(
    client: httpx.AsyncClient,
    pool: EnginePool,
    sf_version: str,
    dry_run: bool,
    loop: bool,
    blob_lease_resp: httpx.Response,
) -> bool:
    """Handle a 200 response from /flaw-blob-lease (tier-4 blob drain path, D-04).

    Evaluates each leased FEN at MultiPV=2, then POSTs the results to
    /flaw-blob-submit. The server assembles PvNode blobs and runs the per-game
    gated retag (_classify_tactic_gated, D-07). Token is echoed unchanged (D-04a).
    """
    blob_lease_resp.raise_for_status()
    data = blob_lease_resp.json()
    game_id = data["game_id"]
    positions = data["positions"]

    # Positions are FENs expanded from each flaw's two PV walks (missed + allowed);
    # token format is "{flaw_ply}:{line}:{k}", so unique flaw plies = the flaw count
    # that blobs_written will report on submit. Log both so the counts share a frame.
    flaw_count = len({str(pos["token"]).split(":", 1)[0] for pos in positions})
    _log(
        f"Flaw-blob lease game_id={game_id} ({len(positions)} FENs across {flaw_count} flaws). "
        "Evaluating at MultiPV=2..."
    )
    evals = await _eval_flaw_blob_positions(pool, positions)

    if dry_run:
        _log(
            f"--dry-run: evaluated {len(evals)} flaw-blob positions for game_id={game_id}; skipping submit."
        )
        return not loop

    submit_resp = await client.post(
        "/api/eval/remote/flaw-blob-submit",
        json={"game_id": game_id, "sf_version": sf_version, "evals": evals},
    )
    submit_resp.raise_for_status()
    result = submit_resp.json()
    _log(f"Flaw-blob submit game_id={game_id}: blobs_written={result.get('blobs_written')}")
    return not loop


# ─── Worker entrypoint ────────────────────────────────────────────────────────


async def run_worker(
    base_url: str,
    token: str,
    worker_id: str,
    workers: int,
    idle_sleep: float,
    dry_run: bool,
    loop: bool,
) -> None:
    """Start an EnginePool, read the SF version, then run the lease/eval/submit loop.

    worker_id is sent on every request via X-Worker-Id (D-10 / SEED-051) so that
    eval_jobs.leased_by and games.entry_eval_leased_by are per-worker in prod.

    Handles KeyboardInterrupt gracefully — logs the interruption and ensures the
    pool is stopped via the finally block.
    """
    pool = EnginePool(workers)
    await pool.start()
    _log(f"EnginePool started with {workers} worker(s).")

    try:
        sf_version = await get_stockfish_version()
        _log(f"Stockfish version: {sf_version}")

        async with httpx.AsyncClient(
            base_url=base_url,
            # D-10: X-Worker-Id set once alongside X-Operator-Token — no per-call change.
            headers={"X-Operator-Token": token, "X-Worker-Id": worker_id},
            timeout=HTTP_TIMEOUT_S,
        ) as client:
            await _run_loop(
                client=client,
                pool=pool,
                sf_version=sf_version,
                idle_sleep=idle_sleep,
                dry_run=dry_run,
                loop=loop,
            )
    except KeyboardInterrupt:
        _log("Interrupted by user. Shutting down...")
    finally:
        await pool.stop()
        _log("EnginePool stopped.")


# ─── Supervisor (SEED-063: self-supervising auto-restart) ───────────────────


def _worker_role(once: bool, child_marker: bool) -> Literal["once", "supervisor", "child"]:
    """Pure dispatch predicate (SEED-063 D3).

    `--once` always bypasses supervision, regardless of the child marker. Otherwise
    the internal child-marker env var distinguishes the spawned child ("child") from
    the top-level, always-on supervisor ("supervisor").
    """
    if once:
        return "once"
    return "child" if child_marker else "supervisor"


def _run_supervisor() -> int:
    """Synchronous supervisor loop (SEED-063 D1/D3/D4/D5).

    Spawns a child copy of this script (internal marker env var, NOT an argparse
    flag) and relaunches it with a fixed backoff whenever it exits for ANY reason,
    unless the supervisor itself was asked to stop (SIGINT/SIGTERM). No max-restart
    cap -- keeps trying forever, matching Docker's `restart: unless-stopped`.

    Plain synchronous loop (subprocess + signal + time.sleep) -- NOT asyncio; there
    is no concurrent work here, only process supervision.
    """
    stop_requested = False
    child_proc: subprocess.Popen[bytes] | None = None

    def _handle_stop_signal(signum: int, frame: FrameType | None) -> None:
        nonlocal stop_requested
        stop_requested = True
        # D6 PID-1 correctness: forward SIGINT to the live child for a clean
        # EnginePool shutdown. POSIX only -- on Windows the console Ctrl-C already
        # reaches the whole process group, and Popen.send_signal(SIGINT) raises there.
        if os.name == "posix" and child_proc is not None:
            with contextlib.suppress(ProcessLookupError, OSError):
                child_proc.send_signal(signal.SIGINT)

    # NEVER loop.add_signal_handler() -- Unix-only, raises NotImplementedError on
    # Windows' ProactorEventLoop (SEED-063 resolved question).
    signal.signal(signal.SIGINT, _handle_stop_signal)
    signal.signal(signal.SIGTERM, _handle_stop_signal)

    while not stop_requested:
        child_proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
            env={**os.environ, _CHILD_MARKER_ENV: _CHILD_MARKER_VALUE},
        )
        code = child_proc.wait()  # reaps the direct child (PID-1 zombie reaping)

        if stop_requested:
            break  # intentional stop -- no relaunch

        _log(f"Child worker exited (code={code}). Relaunching in {SUPERVISOR_BACKOFF_S}s...")
        # D4: grandchild Stockfish processes are either already dead (the wedge case
        # the watchdog converts into this exit) or cleanly quit by EnginePool.stop()
        # (the graceful case) -- no broader process reaping is needed here.
        time.sleep(SUPERVISOR_BACKOFF_S)

    _log("Supervisor stopping (no relaunch).")
    return 0


# ─── CLI ─────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Headless remote eval worker: lease next game (tier-1 > tier-2 > tier-3) → "
            "eval via EnginePool → batch submit (Phase 121 SEED-048)."
        )
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        metavar="URL",
        help=f"Base URL of the FlawChess API (default {DEFAULT_BASE_URL}).",
    )
    parser.add_argument(
        "--token",
        default=None,
        metavar="TOKEN",
        help=(
            "Operator token for X-Operator-Token auth. Optional — overrides the "
            "EVAL_OPERATOR_TOKEN value from the environment or the .env file."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        metavar="N",
        help=(
            f"Number of parallel Stockfish workers (default {DEFAULT_WORKERS}). "
            "Each worker is an independent UCI process configured Threads=1."
        ),
    )
    parser.add_argument(
        "--idle-sleep",
        type=float,
        default=DEFAULT_IDLE_SLEEP,
        dest="idle_sleep",
        metavar="SECONDS",
        help=(f"Seconds to sleep when the queue is empty / 204 (default {DEFAULT_IDLE_SLEEP})."),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Lease and evaluate positions but never submit. Useful for connectivity testing.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process one game (or one idle cycle) then exit. Default loops forever.",
    )
    parser.add_argument(
        "--worker-id",
        default=None,
        dest="worker_id",
        metavar="ID",
        help=(
            "Distinctive worker identity written to leased_by / entry_eval_leased_by columns "
            "for prod observability (D-10 / SEED-051). Must be < 10 chars (fits VARCHAR(16)). "
            "Default: random ~8-char base36 generated at startup."
        ),
    )
    args = parser.parse_args()
    if args.workers < 1:
        parser.error(f"--workers must be >= 1, got {args.workers}")
    if args.idle_sleep <= 0:
        parser.error(f"--idle-sleep must be > 0, got {args.idle_sleep}")
    if args.worker_id is not None and len(args.worker_id) >= 10:
        parser.error(
            f"--worker-id must be < 10 chars, got {len(args.worker_id)} ({args.worker_id!r})"
        )
    return args


# ─── Entry point ─────────────────────────────────────────────────────────────


async def _run_async(
    args: argparse.Namespace,
    token: str,
    worker_id: str,
    supervised: bool,
) -> None:
    """Run the worker body for the "child" or "once" role.

    Task 1: a thin pass-through to `run_worker` so the file stays runnable. Task 2
    wires up the watchdog heartbeat + checker + loop exception handler for the
    `supervised=True` (child) case.
    """
    await run_worker(
        base_url=args.base_url,
        token=token,
        worker_id=worker_id,
        workers=args.workers,
        idle_sleep=args.idle_sleep,
        dry_run=args.dry_run,
        loop=not args.once,
    )


def main() -> int:
    """Entry point: parse CLI args, init Sentry, dispatch to supervisor/child/once.

    SEED-063 D3: the script is ALWAYS the supervisor unless `--once` is passed.
    Token presence is checked BEFORE role dispatch so a missing token fails fast
    (return 1) in BOTH the supervisor and the child -- a missing token must never
    become an infinite relaunch loop.
    """
    args = parse_args()

    # Token resolution: an explicit --token wins; otherwise fall back to
    # settings.EVAL_OPERATOR_TOKEN, which pydantic-settings populates from the OS
    # environment OR the .env / .prod.env file. Resolved after parse so the secret
    # is never bound as an argparse default (kept out of --help and the namespace).
    token = args.token or settings.EVAL_OPERATOR_TOKEN
    if not token:
        print(
            "ERROR: operator token is required. Pass --token <TOKEN>, or set "
            "EVAL_OPERATOR_TOKEN in the environment or the .env file.",
            file=sys.stderr,
        )
        return 1

    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
        )
        sentry_sdk.set_context("worker", {"source": "remote_eval_worker"})
        sentry_sdk.set_tag("source", "remote_eval_worker")

    role = _worker_role(
        once=args.once,
        child_marker=os.environ.get(_CHILD_MARKER_ENV) == _CHILD_MARKER_VALUE,
    )

    if role == "supervisor":
        _log("Starting remote eval worker: supervisor (auto-restart on crash/hang)")
        return _run_supervisor()

    # D-10 (Phase 123 SEED-051): generate a random worker ID at startup when none given.
    # The ID is sent via X-Worker-Id so prod can distinguish workers in leased_by columns.
    worker_id: str = args.worker_id if args.worker_id is not None else _generate_worker_id()

    # Log startup info — NEVER log the token value (T-120-01).
    _log(
        f"Starting remote eval worker: base_url={args.base_url} "
        f"workers={args.workers} worker_id={worker_id}"
    )

    asyncio.run(_run_async(args, token, worker_id, supervised=(role == "child")))
    _log("Done.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        # Ctrl-C (interactive) or SIGINT (Docker STOPSIGNAL) — run_worker's finally
        # has already stopped the EnginePool. The child is a fresh subprocess with
        # DEFAULT signal handlers, so SIGINT there raises KeyboardInterrupt straight
        # into this handler. Swallow it so the worker exits 0 without dumping a
        # traceback that reads as a crash.
        pass
