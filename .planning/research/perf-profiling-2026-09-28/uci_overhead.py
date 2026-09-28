import asyncio, time, chess, chess.engine, sys
SF = "/home/aimfeld/.local/stockfish/sf"
FENS = ["r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "r2q1rk1/pp2bppp/2n1pn2/3p4/3P4/2NBPN2/PP3PPP/R2Q1RK1 w - - 0 10",
        "8/5pk1/6p1/3P4/4K3/8/5PP1/8 w - - 0 45"]
async def main():
    t, p = await chess.engine.popen_uci(SF); await p.configure({"Hash": 32, "Threads": 1})
    for mpv in (None, 2):
        c0 = time.process_time(); w0 = time.perf_counter()
        for f in FENS * 3:
            b = chess.Board(f)
            await (p.analyse(b, chess.engine.Limit(nodes=1_000_000), multipv=mpv) if mpv else p.analyse(b, chess.engine.Limit(nodes=1_000_000)))
        n = len(FENS) * 3
        print(f"multipv={mpv}: parent CPU {1000*(time.process_time()-c0)/n:.1f} ms/call vs wall {1000*(time.perf_counter()-w0)/n:.0f} ms/call")
    await p.quit()
asyncio.run(main())
