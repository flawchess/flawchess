"""Spike 001: Stockfish 1M-node NNUE latency benchmark (local machine).

Measures wall-clock per position at the Lichess-fishnet-parity search budget
(nodes=1_000_000, NNUE, multiPV=1, Threads=1) over representative positions
sampled from real games in the dev DB, mirroring app/services/engine.py UCI
config (Hash=32MB default, Threads=1).

Usage:
    uv run python .planning/spikes/001-sf-1m-node-latency-local/benchmark.py \
        [--hash 32] [--nodes 1000000] [--games 12] [--json-out results.json]

Hash persistence mirrors the planned drain: positions of the same game are
analysed sequentially on one engine with a shared `game=` key (hash carries
over within a game, ucinewgame between games).
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import platform
import statistics
import time

import asyncpg
import chess
import chess.engine
import chess.pgn

DEV_DB_DSN = "postgresql://flawchess:flawchess@localhost:5432/flawchess"
STOCKFISH_PATH = os.path.expanduser("~/.local/stockfish/sf")
MIN_PLIES = 40
# Sample points per game as fractions of total plies; first point fixed at
# ply 14 (just past typical book exit — the drain skips book plies).
SAMPLE_FRACTIONS = [0.25, 0.5, 0.75, 0.9]
FIXED_EARLY_PLY = 14
WARMUP_ANALYSES = 2


def bucket_for(fraction: float) -> str:
    if fraction <= 0.3:
        return "opening-exit"
    if fraction <= 0.7:
        return "middlegame"
    return "endgame"


async def fetch_games(n_games: int) -> list[tuple[int, str]]:
    conn = await asyncpg.connect(DEV_DB_DSN)
    try:
        # Spread over recent games; oversample then take every k-th so the
        # sample isn't one user's session.
        rows = await conn.fetch(
            """
            SELECT id, pgn FROM games
            WHERE ply_count >= $1
            ORDER BY id DESC
            LIMIT $2
            """,
            MIN_PLIES,
            n_games * 8,
        )
    finally:
        await conn.close()
    step = max(1, len(rows) // n_games)
    picked = rows[::step][:n_games]
    return [(r["id"], r["pgn"]) for r in picked]


def collect_positions(game_id: int, pgn_text: str) -> list[tuple[int, int, float, chess.Board]]:
    """Return (game_id, ply, fraction, board) sample points for one game."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return []
    boards: list[chess.Board] = []
    board = game.board()
    for move in game.mainline_moves():
        board.push(move)
        boards.append(board.copy())
    total = len(boards)
    if total < MIN_PLIES:
        return []
    target_plies = {FIXED_EARLY_PLY} | {max(1, int(total * f)) for f in SAMPLE_FRACTIONS}
    out = []
    for ply in sorted(target_plies):
        b = boards[ply - 1]
        if b.is_game_over():
            continue
        out.append((game_id, ply, ply / total, b))
    return out


def run_benchmark(
    positions: list[tuple[int, int, float, chess.Board]],
    hash_mb: int,
    nodes: int,
    depth: int | None = None,
) -> list[dict]:
    engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
    results: list[dict] = []
    try:
        engine.configure({"Hash": hash_mb, "Threads": 1})
        # --depth replaces the node budget with the app's current fixed-depth
        # convention (engine.py _DEPTH=15) for cost comparison.
        limit = chess.engine.Limit(depth=depth) if depth else chess.engine.Limit(nodes=nodes)
        for i in range(WARMUP_ANALYSES):
            engine.analyse(positions[i][3], limit, game=f"warmup-{i}")
        for game_id, ply, fraction, board in positions:
            t0 = time.perf_counter()
            info = engine.analyse(board, limit, game=f"g{game_id}")
            dt = time.perf_counter() - t0
            results.append(
                {
                    "game_id": game_id,
                    "ply": ply,
                    "bucket": bucket_for(fraction),
                    "seconds": round(dt, 4),
                    "nodes": info.get("nodes"),
                    "depth": info.get("depth"),
                    "nps": info.get("nps"),
                    "pv_len": len(info.get("pv") or []),
                }
            )
    finally:
        engine.quit()
    return results


def pctl(vals: list[float], p: float) -> float:
    s = sorted(vals)
    return s[min(len(s) - 1, int(len(s) * p))]


def summarize(results: list[dict], hash_mb: int, nodes: int) -> dict:
    summary: dict = {"hash_mb": hash_mb, "nodes_budget": nodes, "n_positions": len(results)}
    by_bucket: dict[str, list[dict]] = {}
    for r in results:
        by_bucket.setdefault(r["bucket"], []).append(r)
    summary["buckets"] = {}
    for bucket, rs in sorted(by_bucket.items()):
        secs = [r["seconds"] for r in rs]
        summary["buckets"][bucket] = {
            "n": len(rs),
            "p50_s": round(statistics.median(secs), 3),
            "p90_s": round(pctl(secs, 0.9), 3),
            "mean_s": round(statistics.mean(secs), 3),
            "mean_depth": round(statistics.mean(r["depth"] for r in rs), 1),
            "mean_nps": int(statistics.mean(r["nps"] for r in rs if r["nps"])),
            "mean_pv_len": round(statistics.mean(r["pv_len"] for r in rs), 1),
        }
    all_secs = [r["seconds"] for r in results]
    mean_s = statistics.mean(all_secs)
    summary["overall"] = {
        "p50_s": round(statistics.median(all_secs), 3),
        "p90_s": round(pctl(all_secs, 0.9), 3),
        "mean_s": round(mean_s, 3),
        "mean_depth": round(statistics.mean(r["depth"] for r in results), 1),
    }
    # Projections at 60 evaluated plies/game (post book/forced-move skip).
    plies_per_game = 60
    game_core_s = plies_per_game * mean_s
    summary["projections"] = {
        "core_seconds_per_game": round(game_core_s, 1),
        "games_per_day_4_workers": int(4 * 86400 / game_core_s),
        "games_per_day_6_workers": int(6 * 86400 / game_core_s),
        "tier1_wallclock_s_6_workers": round(game_core_s / 6, 1),
    }
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hash", type=int, default=32)
    ap.add_argument("--nodes", type=int, default=1_000_000)
    ap.add_argument("--games", type=int, default=12)
    ap.add_argument("--depth", type=int, default=None)
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    games = asyncio.run(fetch_games(args.games))
    positions = []
    for game_id, pgn_text in games:
        positions.extend(collect_positions(game_id, pgn_text))
    print(f"Sampled {len(positions)} positions from {len(games)} games")

    results = run_benchmark(positions, args.hash, args.nodes, args.depth)
    summary = summarize(results, args.hash, args.nodes)
    summary["machine"] = {
        "cpu_count": os.cpu_count(),
        "platform": platform.platform(),
        "cpu_model": next(
            (
                line.split(":", 1)[1].strip()
                for line in open("/proc/cpuinfo")
                if line.startswith("model name")
            ),
            "unknown",
        ),
    }
    print(json.dumps(summary, indent=2))
    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump({"summary": summary, "results": results}, f, indent=2)


if __name__ == "__main__":
    main()
