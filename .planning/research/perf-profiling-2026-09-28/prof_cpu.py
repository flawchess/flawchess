"""CPU-only post-processing profile: PGN parse+zobrist+classify, tactic detector, maia."""

import asyncio
import cProfile
import csv
import io
import pstats
import random
import sys
import time

import chess
import chess.pgn

sys.path.insert(0, "/home/aimfeld/Projects/Python/flawchess")
sys.path.insert(0, "/home/aimfeld/Projects/Python/flawchess/tests/scripts/tagger")

from app.services.zobrist import process_game_pgn, compute_hashes  # noqa: E402
from app.services.position_classifier import classify_position  # noqa: E402
from app.services.tactic_detector import detect_tactic_motif  # noqa: E402
from app.services import maia_engine  # noqa: E402

REPO = "/home/aimfeld/Projects/Python/flawchess"


def load_pgns(path: str, n: int) -> list[str]:
    txt = open(path, encoding="utf-8", errors="replace").read()
    chunks = txt.split("\n[Event ")
    out = []
    for i, c in enumerate(chunks):
        s = c if i == 0 else "[Event " + c
        if " 1. " in s or "\n1. " in s:
            out.append(s)
    random.Random(1).shuffle(out)
    return out[:n]


def bench_import(pgns: list[str]) -> None:
    # 1. parse only
    t0 = time.perf_counter()
    games = [chess.pgn.read_game(io.StringIO(p)) for p in pgns]
    t_parse = time.perf_counter() - t0
    plies = sum(len(list(g.mainline_moves())) for g in games if g)
    # 2. replay only (push moves)
    t0 = time.perf_counter()
    for g in games:
        b = g.board()
        for m in g.mainline_moves():
            b.push(m)
    t_replay = time.perf_counter() - t0
    # 3. replay + san
    t0 = time.perf_counter()
    for g in games:
        b = g.board()
        for m in g.mainline_moves():
            b.san(m)
            b.push(m)
    t_san = time.perf_counter() - t0
    # 4. compute_hashes / classify per position
    boards = []
    for g in games[:100]:
        b = g.board()
        for m in g.mainline_moves():
            boards.append(b.copy(stack=False))
            b.push(m)
    t0 = time.perf_counter()
    for b in boards:
        compute_hashes(b)
    t_hash = (time.perf_counter() - t0) / len(boards)
    t0 = time.perf_counter()
    for b in boards:
        classify_position(b)
    t_cls = (time.perf_counter() - t0) / len(boards)
    # 5. full process_game_pgn
    t0 = time.perf_counter()
    for p in pgns:
        process_game_pgn(p)
    t_full = time.perf_counter() - t0
    n = len(pgns)
    print(f"[import] games={n} plies={plies} avg_plies={plies / n:.1f}")
    print(f"  read_game (parse)        {1000 * t_parse / n:7.2f} ms/game  {1e6 * t_parse / plies:6.1f} us/ply")
    print(f"  replay push only         {1000 * t_replay / n:7.2f} ms/game  {1e6 * t_replay / plies:6.1f} us/ply")
    print(f"  replay + san             {1000 * t_san / n:7.2f} ms/game  {1e6 * t_san / plies:6.1f} us/ply")
    print(f"  compute_hashes           {1e6 * t_hash:6.1f} us/pos")
    print(f"  classify_position        {1e6 * t_cls:6.1f} us/pos")
    print(f"  process_game_pgn (total) {1000 * t_full / n:7.2f} ms/game  {1e6 * t_full / plies:6.1f} us/ply")
    pr = cProfile.Profile()
    pr.enable()
    for p in pgns:
        process_game_pgn(p)
    pr.disable()
    s = io.StringIO()
    pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(14)
    print("\n".join(s.getvalue().splitlines()[:40]))


def bench_tactic() -> None:
    from conftest import build_detector_board  # type: ignore

    rows = []
    with open(f"{REPO}/fixtures/tagger/realgame_tags.csv") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    inputs = []
    for r in rows:
        pre = r["pre_flaw_fen"]
        mv = r["push_move_uci"]
        try:
            b = chess.Board(pre)
            if mv:
                b.push(chess.Move.from_uci(mv))
        except Exception:
            continue
        inputs.append((b, r["pv"]))
    t0 = time.perf_counter()
    for b, pv in inputs:
        detect_tactic_motif(b.copy(), pv)
    dt = time.perf_counter() - t0
    print(f"\n[tactic] detect_tactic_motif calls={len(inputs)} mean={1000 * dt / len(inputs):.2f} ms/call")
    pr = cProfile.Profile()
    pr.enable()
    for b, pv in inputs:
        detect_tactic_motif(b.copy(), pv)
    pr.disable()
    s = io.StringIO()
    pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(15)
    print("\n".join(s.getvalue().splitlines()[:42]))
    _ = build_detector_board


def bench_maia(pgns: list[str]) -> None:
    asyncio.run(maia_engine.start_maia())
    if not maia_engine.is_maia_available():
        print("[maia] unavailable")
        return
    fens = []
    for p in pgns[:20]:
        g = chess.pgn.read_game(io.StringIO(p))
        b = g.board()
        for m in g.mainline_moves():
            fens.append((b.fen(), m.uci()))
            b.push(m)
    fens = fens[:300]
    for fen, mv in fens[:10]:
        maia_engine.score_move(fen, 1500, mv)  # warmup
    t0 = time.perf_counter()
    for fen, mv in fens:
        maia_engine.score_move(fen, 1500, mv)
    dt = time.perf_counter() - t0
    print(f"\n[maia] score_move calls={len(fens)} mean={1000 * dt / len(fens):.2f} ms/call")
    pr = cProfile.Profile()
    pr.enable()
    for fen, mv in fens:
        maia_engine.score_move(fen, 1500, mv)
    pr.disable()
    s = io.StringIO()
    pstats.Stats(pr, stream=s).sort_stats("tottime").print_stats(8)
    print("\n".join(s.getvalue().splitlines()[:25]))


if __name__ == "__main__":
    pgns = load_pgns(f"{REPO}/temp/Games Noël.pgn", 400)
    bench_import(pgns)
    bench_tactic()
    bench_maia(pgns)
