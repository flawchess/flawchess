# Performance profiling scripts (2026-09-28)

Throwaway scripts behind SEED-171 (browser FlawChess engine) and SEED-172 (server analysis
pipeline). Kept so the numbers can be re-measured on an idle box. Not maintained code: they
carry absolute paths to this checkout and are excluded from ruff (`pyproject.toml`).

**Measurement caveat:** the first run was on a Ryzen 7840HS under load 14-21 (a local
`remote_eval_worker` with 8 SCHED_IDLE engines was running). Absolute timings are inflated,
especially Stockfish NPS (~500-650k single-thread vs prod's ~1M nodes/s reference). Stop any
local worker before re-running.

## Browser engine (Node, run from repo root)

All use `node --import scripts/lib/frontend-alias-hook.mjs <script>`.

| Script | What it measures |
|---|---|
| `profile_search.mjs [nodes] [conc] [maiaThreads] [stopRule 0/1]` | real `mctsSearch` with vendored SF wasm pool + ort-web wasm Maia; Maia vs SF vs JS glue split. `50 4 4 1` = bot budget, `400 4 4 0` = analysis budget |
| `run400.txt` | output of the 400-node run |
| `bench_maia.mjs [modelPath]` | Maia latency by backend (ort-web wasm / onnxruntime-node), threads, batch size |
| `bench_sf.mjs` | lite-single wasm NPS, cost vs MultiPV and depth |
| `split_root.mjs` | root candidates split across idle SF workers vs one MultiPV call |
| `bench_js.mjs` | chess.js / encoding microbenchmarks |

## Server pipeline (`uv run python <script>`)

| Script | What it measures |
|---|---|
| `prof_engine.py` | per-position SF timing and a full worker-style atomic game + `classify_game_flaws` |
| `prof_cpu.py` | import (`process_game_pgn`), tactic detector, Maia `score_move` |
| `maia_fp.py` | fp16 (shipped) vs fp32 Maia latency and output drift. Needs an fp32 copy from `to_fp32.py`; edit the `SP` path |
| `maia_threads.py` | Maia intra-op thread scaling |
| `uci_overhead.py` | python-chess UCI parsing cost per engine call |

The game sample was `temp/Games Noël.pgn` (gitignored, club level, ~83 plies) plus
`fixtures/tagger`. A re-run should use a sample of real prod games instead.
