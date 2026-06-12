# Spike Conventions

Patterns and stack choices established across spike sessions. New spikes follow
these unless the question requires otherwise.

## Stack

- Benchmark/measurement spikes are CLI scripts with a JSON summary on stdout
  (these are fact-finding spikes; no UI needed).
- Dev-machine scripts run via `uv run python` (full app venv available:
  python-chess, asyncpg). Sample real data from the dev DB
  (`postgresql://flawchess:flawchess@localhost:5432/flawchess`).
- Prod-host scripts are **stdlib-only** (raw-UCI subprocess driver instead of
  python-chess) so they run with the host's bare `python3`.

## Stockfish benchmarking

- Mirror `app/services/engine.py` config exactly: Hash=32MB, Threads=1,
  SCHED_IDLE (`os.sched_setscheduler(0, os.SCHED_IDLE, ...)` at script start —
  children inherit).
- The prod Stockfish binary can be copied out of the backend container
  (`docker compose cp backend:/usr/local/bin/stockfish ...`) and runs on the
  host directly (embedded NNUE nets).
- **Never run engine benchmarks inside the backend container** — extra
  Stockfish processes count against its `mem_limit: 4g` and can OOM-restart
  the live backend. Run on the host; CPU timing is equivalent.
- Position sets: dump `game_id;ply;fen` lines from dev-DB games
  (spike 001 `--dump-fens`) so prod runs need no DB access.
- Clean up `/tmp` artifacts on the server after prod runs.

## Prod DB queries

- Read-only via the `flawchess-prod-db` MCP tool (tunnel:
  `bin/prod_db_tunnel.sh`).
- "Game has per-ply evals" proxy: `white_blunders IS NOT NULL OR
  black_blunders IS NOT NULL` (validated in Q-007).
- `users.last_activity` was backfilled ~2026-03-22 — activity windows beyond
  ~60 days are meaningless.
