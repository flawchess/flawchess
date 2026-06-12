"""Spike 002: Stockfish 1M-node latency on the prod host (stdlib only).

Raw-UCI driver over subprocess — no python-chess required, so it runs with the
host's bare python3 against the Stockfish binary copied out of the backend
container. Sets SCHED_IDLE on itself (children inherit), matching how
app/services/engine.py spawns prod engine workers.

Phases:
    seq  — one engine, all positions sequentially → per-core latency.
    conc — N engines in parallel threads, positions split round-robin →
           aggregate throughput under contention (run API latency probe
           alongside from another machine).

Usage (on prod host):
    python3 prod_benchmark.py --sf /tmp/spike002/sf --fens /tmp/spike002/fens.txt --phase seq
    python3 prod_benchmark.py --sf /tmp/spike002/sf --fens /tmp/spike002/fens.txt --phase conc --workers 6
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import threading
import time

HASH_MB = 32
NODES = 1_000_000


class UciEngine:
    def __init__(self, path: str) -> None:
        self.proc = subprocess.Popen(
            [path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._cmd("uci", wait_for="uciok")
        self._send(f"setoption name Hash value {HASH_MB}")
        self._send("setoption name Threads value 1")
        self._cmd("isready", wait_for="readyok")

    def _send(self, line: str) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(line + "\n")

    def _cmd(self, line: str, wait_for: str) -> list[str]:
        self._send(line)
        out = []
        assert self.proc.stdout is not None
        while True:
            ln = self.proc.stdout.readline()
            if not ln:
                raise RuntimeError("engine died")
            out.append(ln.strip())
            if ln.startswith(wait_for):
                return out

    def new_game(self) -> None:
        self._send("ucinewgame")
        self._cmd("isready", wait_for="readyok")

    def analyse(self, fen: str, nodes: int) -> dict:
        self._send(f"position fen {fen}")
        t0 = time.perf_counter()
        lines = self._cmd(f"go nodes {nodes}", wait_for="bestmove")
        dt = time.perf_counter() - t0
        info: dict = {"seconds": round(dt, 4)}
        for ln in reversed(lines):
            if ln.startswith("info") and " depth " in ln and " nodes " in ln:
                tok = ln.split()
                for key in ("depth", "nodes", "nps"):
                    if key in tok:
                        info[key] = int(tok[tok.index(key) + 1])
                break
        return info

    def quit(self) -> None:
        try:
            self._send("quit")
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def load_fens(path: str) -> list[tuple[str, str]]:
    out = []
    for line in open(path):
        game_id, _ply, fen = line.strip().split(";", 2)
        out.append((game_id, fen))
    return out


def run_seq(sf: str, fens: list[tuple[str, str]]) -> list[dict]:
    eng = UciEngine(sf)
    results = []
    try:
        eng.analyse(fens[0][1], NODES)  # warmup, uncounted
        last_game = None
        for game_id, fen in fens:
            if game_id != last_game:
                eng.new_game()
                last_game = game_id
            r = eng.analyse(fen, NODES)
            r["game_id"] = game_id
            results.append(r)
    finally:
        eng.quit()
    return results


def run_conc(sf: str, fens: list[tuple[str, str]], workers: int) -> tuple[list[dict], float]:
    shards: list[list[tuple[str, str]]] = [fens[i::workers] for i in range(workers)]
    all_results: list[list[dict]] = [[] for _ in range(workers)]

    def work(i: int) -> None:
        eng = UciEngine(sf)
        try:
            for game_id, fen in shards[i]:
                eng.new_game()
                r = eng.analyse(fen, NODES)
                r["game_id"] = game_id
                all_results[i].append(r)
        finally:
            eng.quit()

    t0 = time.perf_counter()
    threads = [threading.Thread(target=work, args=(i,)) for i in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.perf_counter() - t0
    return [r for shard in all_results for r in shard], wall


def pctl(vals: list[float], p: float) -> float:
    s = sorted(vals)
    return s[min(len(s) - 1, int(len(s) * p))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sf", required=True)
    ap.add_argument("--fens", required=True)
    ap.add_argument("--phase", choices=["seq", "conc"], required=True)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    # SCHED_IDLE like engine.py's prod workers; children inherit.
    os.sched_setscheduler(0, os.SCHED_IDLE, os.sched_param(0))

    fens = load_fens(args.fens)
    if args.phase == "seq":
        results = run_seq(args.sf, fens)
        wall = sum(r["seconds"] for r in results)
    else:
        results, wall = run_conc(args.sf, fens, args.workers)

    secs = [r["seconds"] for r in results]
    mean_s = statistics.mean(secs)
    positions_per_s = len(results) / wall
    summary = {
        "phase": args.phase,
        "workers": args.workers if args.phase == "conc" else 1,
        "n_positions": len(results),
        "p50_s": round(statistics.median(secs), 3),
        "p90_s": round(pctl(secs, 0.9), 3),
        "mean_s": round(mean_s, 3),
        "mean_depth": round(statistics.mean(r["depth"] for r in results), 1),
        "mean_nps": int(statistics.mean(r["nps"] for r in results if r.get("nps"))),
        "wall_s": round(wall, 1),
        "aggregate_positions_per_s": round(positions_per_s, 2),
        "games_per_day_at_60_plies": int(positions_per_s * 86400 / 60),
        "cpu_count": os.cpu_count(),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
