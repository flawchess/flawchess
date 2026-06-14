"""Headless remote eval worker for the trusted operator eval pipeline (Phase 120 SEED-048).

Runs on a trusted off-box machine. Loops: lease a tier-3 game from the FlawChess API,
evaluate all its FENs locally via EnginePool, and batch-submit the results. The server
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
import sys
from datetime import datetime, timezone
from pathlib import Path

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
from app.services.engine import EnginePool, get_stockfish_version  # noqa: E402

# ─── Named constants (no magic numbers) ──────────────────────────────────────

DEFAULT_BASE_URL: str = "https://flawchess.com"
DEFAULT_WORKERS: int = 4
DEFAULT_IDLE_SLEEP: float = 5.0
HTTP_TIMEOUT_S: float = 30.0


# ─── Logging helper ───────────────────────────────────────────────────────────


def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


# ─── Eval helper ─────────────────────────────────────────────────────────────


async def _eval_positions(
    pool: EnginePool,
    positions: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Evaluate all positions from a lease response via EnginePool fan-out.

    Returns a list of eval dicts keyed by ply. Results are passed through
    UNCHANGED from the engine — NO post-move shift, NO transformation.
    The server owns the SEED-044 storage convention (D-2 / pitfall 1).

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
    """Run one lease → eval → submit cycle. Returns True when the loop should stop.

    Returns True only in non-loop mode after a completed cycle (or an idle 204);
    in loop mode it always returns False so _run_loop keeps draining.
    """
    lease_resp = await client.post("/api/eval/remote/lease")

    if lease_resp.status_code == 204:
        _log("Queue empty (204). Sleeping...")
        await asyncio.sleep(idle_sleep)
        return not loop

    lease_resp.raise_for_status()
    data = lease_resp.json()
    game_id = data["game_id"]
    positions = data["positions"]

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
        },
    )
    submit_resp.raise_for_status()
    result = submit_resp.json()
    _log(
        f"Submitted game_id={game_id}: stamp_complete={result.get('stamp_complete')}, "
        f"failed_ply_count={result.get('failed_ply_count')}"
    )

    return not loop


# ─── Worker entrypoint ────────────────────────────────────────────────────────


async def run_worker(
    base_url: str,
    token: str,
    workers: int,
    idle_sleep: float,
    dry_run: bool,
    loop: bool,
) -> None:
    """Start an EnginePool, read the SF version, then run the lease/eval/submit loop.

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
            headers={"X-Operator-Token": token},
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


# ─── CLI ─────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Headless remote eval worker: lease tier-3 game → eval via EnginePool → "
            "batch submit (Phase 120 SEED-048)."
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
    args = parser.parse_args()
    if args.workers < 1:
        parser.error(f"--workers must be >= 1, got {args.workers}")
    if args.idle_sleep <= 0:
        parser.error(f"--idle-sleep must be > 0, got {args.idle_sleep}")
    return args


# ─── Entry point ─────────────────────────────────────────────────────────────


async def main() -> None:
    """Entry point: parse CLI args, init Sentry, run the eval worker."""
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
        sys.exit(1)

    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
        )
        sentry_sdk.set_context("worker", {"source": "remote_eval_worker"})
        sentry_sdk.set_tag("source", "remote_eval_worker")

    # Log startup info — NEVER log the token value (T-120-01).
    _log(f"Starting remote eval worker: base_url={args.base_url} workers={args.workers}")

    await run_worker(
        base_url=args.base_url,
        token=token,
        workers=args.workers,
        idle_sleep=args.idle_sleep,
        dry_run=args.dry_run,
        loop=not args.once,
    )
    _log("Done.")


if __name__ == "__main__":
    asyncio.run(main())
