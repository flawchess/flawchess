import time, numpy as np, onnxruntime as ort, sys
sys.path.insert(0, "/home/aimfeld/Projects/Python/flawchess")
from app.services.maia_encoding import encode_board, elo_to_input, NUM_SQUARES, PLANES_PER_SQUARE
import chess
M = "/home/aimfeld/Projects/Python/flawchess/frontend/public/maia/maia3_simplified.onnx"
fen = chess.STARTING_FEN
tok = np.array(encode_board(fen), dtype=np.float32).reshape(1, NUM_SQUARES, PLANES_PER_SQUARE)
elo = np.array([elo_to_input(1500)], dtype=np.float32)
for threads in (0, 1, 2, 4):
    so = ort.SessionOptions()
    if threads: so.intra_op_num_threads = threads
    s = ort.InferenceSession(M, so, providers=["CPUExecutionProvider"])
    for batch in (1, 16):
        feeds = {"tokens": np.repeat(tok, batch, 0), "elo_self": np.repeat(elo, batch, 0), "elo_oppo": np.repeat(elo, batch, 0)}
        try:
            s.run(["logits_move"], feeds)
        except Exception as e:
            print("batch", batch, "fail", str(e)[:100]); continue
        t0 = time.perf_counter(); n = 20
        for _ in range(n): s.run(["logits_move"], feeds)
        dt = (time.perf_counter() - t0) / n
        print(f"threads={threads or 'default'} batch={batch}: {1000*dt:.1f} ms/run, {1000*dt/batch:.1f} ms/pos")
print([ (i.name, i.shape) for i in s.get_inputs()])
