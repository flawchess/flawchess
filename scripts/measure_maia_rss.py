"""measure_maia_rss.py — steady-state backend RSS with the Maia session loaded (D-03b).

Phase 174 GEMS-03: empirically measures the resident-set-size cost of the eager
Maia-3 ONNX inference session against the 4 GB backend container budget BEFORE
enabling backend Maia in prod. Replaces the "~44 MB model file size" estimate
(Pitfall 5) with the real InferenceSession RSS, which also carries arena
allocators, the intra-op thread pool, and numpy working memory.

What it does:
  1. Read baseline process RSS (interpreter + imports, no Maia session).
  2. start_maia() — eager-load the one process-wide ONNX session; read RSS again
     (the session-load delta).
  3. Run a representative inference burst (BURST_CALLS back-to-back score_move
     calls over distinct positions — roughly one game's candidate volume per
     SEED-108); read RSS again (the post-burst delta: first-call numpy import +
     any per-inference arena growth).
  4. Print baseline / post-load / post-burst RSS and the Maia total, then sum it
     against the documented 4 GB budget alongside engine.py's existing Stockfish
     pool residency (this number is ADDED to that accounting, never treated as a
     separate line item — RESEARCH Pitfall 5).

Soft gate: exits non-zero when the measured Maia RSS delta exceeds the documented
headroom threshold OR the projected total (Stockfish pool + FastAPI + Maia)
exceeds the container budget, so a future regression (e.g. an onnxruntime bump
that balloons arena memory) is caught in CI/manual runs rather than in a prod
OOM-kill. Enabling backend Maia in prod is gated on this fitting the 4 GB budget
alongside the 6-subprocess Stockfish pool; if it does NOT fit, the documented
escape hatch (Maia-on-workers) is a HUMAN decision, not auto-taken (D-02/D-03).

Run: `uv sync --group maia-inference && uv run python scripts/measure_maia_rss.py`
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import chess

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import maia_engine  # noqa: E402
from app.services.maia_engine import score_move, start_maia, stop_maia  # noqa: E402

# ─── Budget accounting (must stay aligned with app/services/engine.py ~120-141) ──

# The prod backend container's hard memory limit (CLAUDE.md "Production Server").
CONTAINER_BUDGET_MB: int = 4096

# Prod Stockfish pool (STOCKFISH_POOL_SIZE=6) at the conservative per-worker RSS
# from engine.py's own accounting (~368 MB/worker at 1M-node / depth-15 under
# concurrent imports). This is the residency the Maia number must fit ALONGSIDE.
STOCKFISH_POOL_SIZE: int = 6
STOCKFISH_PER_WORKER_MB: int = 368
STOCKFISH_POOL_RESIDENCY_MB: int = STOCKFISH_POOL_SIZE * STOCKFISH_PER_WORKER_MB

# FastAPI/Uvicorn baseline (engine.py accounting).
FASTAPI_BASELINE_MB: int = 300

# Documented soft ceiling for the Maia session's steady-state RSS. A CPU
# onnxruntime InferenceSession over the ~44 MB vendored model, plus its arena +
# thread pool + numpy working set, is expected well under this; exceeding it
# signals a regression (Pitfall 2/5). Chosen with margin: even at this ceiling
# the projected total (2208 + 300 + 512 = 3020 MB) fits the 4 GB budget with
# headroom, so the gate flags a genuine anomaly, not a healthy measurement.
MAIA_RSS_HEADROOM_MB: int = 512

# One game's candidate volume (SEED-108: ~10-20 out-of-book best-move plies/game).
BURST_CALLS: int = 20

# A representative rating for the ELO-conditioning input; the exact value does not
# affect RSS (the tensor shape is fixed).
_SAMPLE_ELO: float = 1500.0


def _rss_mb() -> float:
    """Current process RSS in MiB. Prefers /proc/self/status VmRSS (Linux, the
    prod container platform); falls back to resource.getrusage elsewhere."""
    try:
        with open("/proc/self/status", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024.0  # kB -> MiB
    except OSError:
        pass
    import resource

    # ru_maxrss is KiB on Linux (peak, not current) — a coarse fallback only.
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def _sample_positions(n: int) -> list[tuple[str, str]]:
    """n distinct (fen, played_uci) pairs by walking the first legal move from the
    start position (deterministic; restarts on game-over). Each pair drives one
    real ONNX inference regardless of whether the move is in Maia's policy."""
    board = chess.Board()
    out: list[tuple[str, str]] = []
    for _ in range(n):
        if board.is_game_over():
            board = chess.Board()
        move = next(iter(board.legal_moves))
        out.append((board.fen(), move.uci()))
        board.push(move)
    return out


async def _measure() -> int:
    baseline = _rss_mb()

    await start_maia()
    if maia_engine._session is None:
        print(
            "ERROR: Maia session did not load — cannot measure RSS.\n"
            "  Ensure the maia-inference group is synced (uv sync --group maia-inference)\n"
            "  and the vendored model SHA-256 matches the pin. See maia_engine.start_maia."
        )
        return 2
    post_load = _rss_mb()

    for fen, played_uci in _sample_positions(BURST_CALLS):
        score_move(fen, _SAMPLE_ELO, played_uci)
    post_burst = _rss_mb()

    await stop_maia()

    load_delta = post_load - baseline
    burst_delta = post_burst - post_load
    maia_total = post_burst - baseline
    projected_total = STOCKFISH_POOL_RESIDENCY_MB + FASTAPI_BASELINE_MB + maia_total

    print("=== Maia backend RSS measurement (D-03b, Phase 174) ===")
    print(f"  baseline RSS (no session)     : {baseline:8.1f} MiB")
    print(f"  after start_maia() load       : {post_load:8.1f} MiB  (Δ {load_delta:+7.1f})")
    print(
        f"  after {BURST_CALLS}-call inference burst : {post_burst:8.1f} MiB  (Δ {burst_delta:+7.1f})"
    )
    print(f"  Maia session total RSS        : {maia_total:8.1f} MiB")
    print("  --- projected against the 4 GB container budget ---")
    print(
        f"  Stockfish pool ({STOCKFISH_POOL_SIZE}×{STOCKFISH_PER_WORKER_MB} MB): "
        f"{STOCKFISH_POOL_RESIDENCY_MB:8.1f} MiB"
    )
    print(f"  FastAPI/Uvicorn baseline      : {FASTAPI_BASELINE_MB:8.1f} MiB")
    print(f"  + Maia session total          : {maia_total:8.1f} MiB")
    print(
        f"  = projected backend total     : {projected_total:8.1f} MiB / {CONTAINER_BUDGET_MB} MiB budget"
    )
    print(f"  documented Maia headroom      : {MAIA_RSS_HEADROOM_MB} MiB")

    over_headroom = maia_total > MAIA_RSS_HEADROOM_MB
    over_budget = projected_total > CONTAINER_BUDGET_MB
    if over_headroom or over_budget:
        if over_headroom:
            print(
                f"\nFAIL: Maia RSS {maia_total:.1f} MiB exceeds the documented "
                f"{MAIA_RSS_HEADROOM_MB} MiB headroom — investigate before prod enablement."
            )
        if over_budget:
            print(
                f"\nFAIL: projected total {projected_total:.1f} MiB exceeds the "
                f"{CONTAINER_BUDGET_MB} MiB container budget — prod enablement is a HUMAN "
                "decision (escape hatch: Maia-on-workers, D-02/D-03), not auto-taken."
            )
        return 1

    print(
        f"\nOK: Maia fits the 4 GB budget alongside the {STOCKFISH_POOL_SIZE}-worker "
        "Stockfish pool with headroom."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_measure()))
