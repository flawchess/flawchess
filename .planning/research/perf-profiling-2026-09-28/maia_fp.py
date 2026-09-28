import time, sys, io, random, numpy as np, onnxruntime as ort, chess, chess.pgn
sys.path.insert(0, "/home/aimfeld/Projects/Python/flawchess")
from app.services.maia_encoding import encode_board, elo_to_input, mask_and_softmax, NUM_SQUARES, PLANES_PER_SQUARE
SP = "/tmp/claude-1000/-home-aimfeld-Projects-Python-flawchess/fb61928c-2ebf-416a-bd29-218e8b0623b6/scratchpad"
M16 = "/home/aimfeld/Projects/Python/flawchess/frontend/public/maia/maia3_simplified.onnx"
M32 = SP + "/maia3_fp32.onnx"
txt = open("/home/aimfeld/Projects/Python/flawchess/temp/Games Noël.pgn", encoding="utf-8", errors="replace").read()
chunks = ["[Event " + c if i else c for i, c in enumerate(txt.split("\n[Event "))][:30]
fens = []
for c in chunks:
    g = chess.pgn.read_game(io.StringIO(c)); b = g.board()
    for m in g.mainline_moves():
        fens.append((b.fen(), m.uci())); b.push(m)
random.Random(3).shuffle(fens); fens = fens[:120]
def feeds(fen):
    tok = np.array(encode_board(fen), dtype=np.float32).reshape(1, NUM_SQUARES, PLANES_PER_SQUARE)
    e = np.array([elo_to_input(1500)], dtype=np.float32)
    return {"tokens": tok, "elo_self": e, "elo_oppo": e}
print("inputs16", [(i.name, i.type) for i in ort.InferenceSession(M16).get_inputs()])
res = {}
for label, path in (("fp16", M16), ("fp32", M32)):
    for th in (1, 4):
        so = ort.SessionOptions(); so.intra_op_num_threads = th
        s = ort.InferenceSession(path, so, providers=["CPUExecutionProvider"])
        for f, _ in fens[:5]: s.run(["logits_move"], feeds(f))
        t0 = time.perf_counter(); probs = []
        for f, mv in fens:
            out = s.run(["logits_move"], feeds(f))
            pol = np.asarray(out[0]).reshape(-1).astype(np.float32)
            probs.append(mask_and_softmax(pol.tolist(), f).get(mv, 0.0))
        dt = (time.perf_counter() - t0) / len(fens)
        res[label] = probs
        print(f"{label} threads={th}: {1000*dt:.1f} ms/pos (incl encode+softmax)")
d = np.abs(np.array(res["fp16"]) - np.array(res["fp32"]))
print(f"played-move prob diff fp16 vs fp32: max={d.max():.5f} mean={d.mean():.6f}")
