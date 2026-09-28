"""Stockfish timing at production settings + full worker-style atomic game + server classify."""

import asyncio
import io
import random
import resource
import sys
import time

import chess
import chess.engine
import chess.pgn

REPO = "/home/aimfeld/Projects/Python/flawchess"
sys.path.insert(0, REPO)
sys.path.insert(0, f"{REPO}/scripts")

import app.services.engine as eng  # noqa: E402

# Run at NORMAL priority so we preempt the SCHED_IDLE worker already running on this box.
eng._engine_popen_kwargs = lambda: {}  # type: ignore[assignment]

import remote_eval_worker as rw  # noqa: E402
from app.models.game import Game  # noqa: E402
from app.models.game_position import GamePosition  # noqa: E402
from app.services.flaws_service import classify_game_flaws  # noqa: E402
from app.services.zobrist import process_game_pgn  # noqa: E402

SF = eng._STOCKFISH_PATH


def load_games(n: int, min_plies: int = 60, max_plies: int = 130) -> list[str]:
    txt = open(f"{REPO}/temp/Games Noël.pgn", encoding="utf-8", errors="replace").read()
    chunks = ["[Event " + c if i else c for i, c in enumerate(txt.split("\n[Event "))]
    random.Random(7).shuffle(chunks)
    out = []
    for c in chunks:
        g = chess.pgn.read_game(io.StringIO(c))
        if g is None:
            continue
        n_pl = len(list(g.mainline_moves()))
        if min_plies <= n_pl <= max_plies:
            out.append(c)
        if len(out) >= n:
            break
    return out


async def single_position_bench(fens: list[str]) -> None:
    transport, proto = await chess.engine.popen_uci(SF)
    await proto.configure({"Hash": eng._HASH_MB, "Threads": 1})
    for label, limit, mpv in (
        ("depth15 mpv1", chess.engine.Limit(depth=15), None),
        ("1M mpv1", chess.engine.Limit(nodes=1_000_000), None),
        ("1M mpv2", chess.engine.Limit(nodes=1_000_000), 2),
        ("1M mpv5", chess.engine.Limit(nodes=1_000_000), 5),
    ):
        times, nodes, nps = [], [], []
        for fen in fens:
            b = chess.Board(fen)
            t0 = time.perf_counter()
            if mpv:
                info = (await proto.analyse(b, limit, multipv=mpv))[0]
            else:
                info = await proto.analyse(b, limit)
            times.append(time.perf_counter() - t0)
            nodes.append(info.get("nodes", 0))
            nps.append(info.get("nps", 0))
        times.sort()
        print(
            f"[sf single] {label:13s} n={len(fens)} mean={sum(times) / len(times) * 1000:7.1f} ms "
            f"p50={times[len(times) // 2] * 1000:7.1f} p90={times[int(len(times) * 0.9)] * 1000:7.1f} "
            f"nodes_mean={sum(nodes) / len(nodes):,.0f} nps_mean={sum(nps) / len(nps):,.0f}"
        )
    await proto.quit()


def lease_positions(pgn: str) -> list[dict]:
    g = chess.pgn.read_game(io.StringIO(pgn))
    b = g.board()
    out = []
    ply = 0
    for m in g.mainline_moves():
        out.append({"ply": ply, "fen": b.fen(), "is_terminal": False, "move_uci": m.uci()})
        b.push(m)
        ply += 1
    out.append({"ply": ply, "fen": b.fen(), "is_terminal": True, "move_uci": None})
    return out


class Counter:
    def __init__(self) -> None:
        self.calls: dict[str, int] = {}
        self.secs: dict[str, float] = {}


def instrument(pool: eng.EnginePool, c: Counter) -> None:
    for name in ("evaluate_nodes_with_pv", "evaluate_nodes_multipv2"):
        orig = getattr(pool, name)

        def make(orig=orig, name=name):
            async def wrapped(board, timeout_s=None):
                t0 = time.perf_counter()
                r = await orig(board, timeout_s=timeout_s)
                c.calls[name] = c.calls.get(name, 0) + 1
                c.secs[name] = c.secs.get(name, 0.0) + time.perf_counter() - t0
                return r

            return wrapped

        setattr(pool, name, make())


def build_positions_for_classify(pgn: str, evals: list[dict]) -> tuple[Game, list[GamePosition]]:
    res = process_game_pgn(pgn)
    assert res is not None
    ev = {e["ply"]: e for e in evals}
    positions = []
    for pd in res["plies"]:
        gp = GamePosition()
        gp.ply = pd["ply"]
        gp.move_san = pd["move_san"]
        gp.clock_seconds = pd["clock_seconds"]
        gp.phase = pd["phase"]
        # post-move storage convention: row P holds eval of position P+1
        nxt = ev.get(pd["ply"] + 1)
        gp.eval_cp = nxt["eval_cp"] if nxt else None
        gp.eval_mate = nxt["eval_mate"] if nxt else None
        cur = ev.get(pd["ply"])
        gp.pv = cur["pv"] if cur else None
        positions.append(gp)
    g = chess.pgn.read_game(io.StringIO(pgn))
    game = Game()
    game.pgn = pgn
    game.result = {"1-0": "1-0", "0-1": "0-1"}.get(g.headers.get("Result", "*"), "1/2-1/2")
    game.user_color = "white"
    game.base_time_seconds = 300
    game.increment_seconds = 0
    game.time_control_str = "300"
    return game, positions


async def atomic_games(pgns: list[str], pool_size: int) -> None:
    pool = eng.EnginePool(size=pool_size)
    await pool.start()
    c = Counter()
    instrument(pool, c)
    tot_wall = 0.0
    tot_plies = 0
    tot_classify = 0.0
    tot_flaws = 0
    r0 = resource.getrusage(resource.RUSAGE_SELF)
    for pgn in pgns:
        pos = lease_positions(pgn)
        t0 = time.perf_counter()
        evals, blobs, second = await rw._eval_atomic_game(pool, pos)
        wall = time.perf_counter() - t0
        tot_wall += wall
        tot_plies += len(pos) - 1
        game, gps = build_positions_for_classify(pgn, evals)
        t1 = time.perf_counter()
        fl = classify_game_flaws(game, gps, pv_by_ply={e["ply"]: e["pv"] for e in evals if e["pv"]})
        dt_cls = time.perf_counter() - t1
        nfl = len(fl) if isinstance(fl, list) else 0
        tot_classify += dt_cls
        tot_flaws += nfl
        from app.services.best_move_candidates import passes_inaccuracy_gate
        evb = {e["ply"]: e for e in evals}
        gate = sum(1 for sb in second if passes_inaccuracy_gate(evb[sb["ply"]]["eval_cp"], evb[sb["ply"]]["eval_mate"], sb["second_cp"], sb["second_mate"], "white" if sb["ply"] % 2 == 0 else "black"))
        print(f"  maia_candidates(gate-passing, incl book)={gate}")
        holes = sum(1 for e in evals if e["eval_cp"] is None and e["eval_mate"] is None)
        print(
            f"[atomic] plies={len(pos) - 1:3d} full={len(evals):3d} blob_nodes={len(blobs):3d} "
            f"second_best={len(second):3d} holes={holes} wall={wall:6.1f}s  "
            f"classify={dt_cls * 1000:6.1f} ms flaws(mistake+blunder,both sides)={nfl}"
        )
    r1 = resource.getrusage(resource.RUSAGE_SELF)
    py_cpu = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
    ch = resource.getrusage(resource.RUSAGE_CHILDREN)
    await pool.stop()
    ch2 = resource.getrusage(resource.RUSAGE_CHILDREN)
    n = len(pgns)
    print(f"\n[atomic] pool={pool_size} games={n} plies={tot_plies} wall={tot_wall:.1f}s -> {tot_wall / n:.1f} s/game wall")
    for k in c.calls:
        print(f"  {k}: calls={c.calls[k]} ({c.calls[k] / n:.1f}/game) sum_latency={c.secs[k]:.1f}s mean={c.secs[k] / c.calls[k]:.2f}s")
    total_calls = sum(c.calls.values())
    print(f"  engine calls/game={total_calls / n:.1f}  calls/ply={total_calls / tot_plies:.2f}")
    print(f"  python parent CPU (UCI I/O + hint + walk + classify) = {py_cpu:.1f}s total, {py_cpu / n:.2f}s/game")
    print(f"  stockfish children CPU (after quit) = {ch2.ru_utime + ch2.ru_stime:.1f}s")
    print(f"  classify_game_flaws: {tot_classify / n * 1000:.1f} ms/game, flaws/game={tot_flaws / n:.1f}")


async def main() -> None:
    pgns = load_games(6)[3:]
    fens = []
    for p in pgns[:3]:
        pos = lease_positions(p)
        fens += [x["fen"] for x in pos[::6]]
    fens = fens[:30]
    if '--single' in sys.argv: await single_position_bench(fens)
    pool_size = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    await atomic_games(pgns[:int(sys.argv[2]) if len(sys.argv) > 2 else 4], pool_size)


asyncio.run(main())
