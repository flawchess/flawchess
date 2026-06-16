---
phase: 120-headless-remote-trusted-operator-eval-worker-seed-048
plan: "03"
subsystem: scripts
tags: [remote-eval, stockfish, engine-pool, cli-worker, seed-048, seed-044, operator-auth]

requires:
  - phase: 120
    plan: "01"
    provides: get_stockfish_version() + EnginePool from app/services/engine.py
  - phase: 120
    plan: "02"
    provides: POST /api/eval/remote/lease + POST /api/eval/remote/submit with X-Operator-Token auth

provides:
  - scripts/remote_eval_worker.py: headless CLI worker (lease → eval → submit loop)

affects:
  - 120-04 (D-7: weighted-random tier-3 game pick — the worker is the consumer that drains the queue)

tech-stack:
  added: []
  patterns:
    - "sys.path.insert bootstrap + ORM registry imports (noqa E402/F401) so app.* resolves in script context"
    - "asyncio.gather fan-out: evaluate_nodes_with_pv called concurrently for all leased positions"
    - "No client-side post-move shift: engine results returned UNCHANGED; server owns SEED-044 convention (D-2)"
    - "Token via CLI arg or EVAL_OPERATOR_TOKEN env; startup log prints base_url + workers only (T-120-01)"
    - "KeyboardInterrupt handled in run_worker try/except; pool.stop() guaranteed via finally"

key-files:
  created:
    - scripts/remote_eval_worker.py

key-decisions:
  - "asyncio.gather fan-out in _eval_positions uses the EnginePool — safe because EnginePool workers are independent UCI processes each with their own queue slot; no shared AsyncSession (the worker has no DB)"
  - "_run_loop exits when not loop after one lease cycle (200 or 204); loop=not args.once is the clean one-shot flag"
  - "pool started before get_stockfish_version() so both use the same process environment; pool.stop() in finally covers both KeyboardInterrupt and unexpected exceptions"
  - "ORM registry imports (app.models.oauth_account, app.models.user) included per resweep_holed_games.py pattern to prevent mapper-configure failure in script context"

metrics:
  duration: ~10 min
  completed: "2026-06-14"
  tasks: 1
  files_modified: 1
---

# Phase 120 Plan 03: Remote Eval Worker CLI Summary

**Headless CLI worker (~308 lines) that runs on a trusted off-box machine: loops lease → eval all FENs via EnginePool.evaluate_nodes_with_pv fan-out → batch-submit with sf_version; authenticates via X-Operator-Token; never logs the token; no client-side post-move shift (D-2).**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-06-14T18:12:00Z
- **Completed:** 2026-06-14T18:22:01Z
- **Tasks:** 1
- **Files modified:** 1 (created)

## Accomplishments

- Created `scripts/remote_eval_worker.py` with:
  - `DEFAULT_WORKERS = 1`, `DEFAULT_IDLE_SLEEP = 5.0`, `HTTP_TIMEOUT_S = 30.0` named constants
  - Timestamped `_log()` helper (UTC, second precision)
  - `_eval_positions(pool, positions)`: asyncio.gather fan-out over `pool.evaluate_nodes_with_pv`; results passed through UNCHANGED (no post-move shift, no transformation)
  - `_run_loop(client, pool, sf_version, idle_sleep, dry_run, loop)`: 204 → sleep + continue/return; 200 → eval → submit (unless dry_run); break after one cycle when not loop
  - `run_worker(base_url, token, workers, idle_sleep, dry_run, loop)`: EnginePool start → get_stockfish_version → httpx.AsyncClient with X-Operator-Token header → _run_loop; KeyboardInterrupt handled; pool.stop() in finally
  - `parse_args()`: --base-url (required), --token (default $EVAL_OPERATOR_TOKEN), --workers, --idle-sleep, --dry-run, --once
  - `async def main()`: token validation, Sentry init (guarded by SENTRY_DSN), startup log (base_url + workers, never token), run_worker call
  - `if __name__ == "__main__": asyncio.run(main())`

## Task Commits

1. **Task 1: Build the remote_eval_worker CLI** - `d68bf3a0` (feat)

## Files Created/Modified

- `scripts/remote_eval_worker.py` — New file: headless CLI worker (308 lines)

## Decisions Made

- `asyncio.gather` fan-out in `_eval_positions` is safe here because `EnginePool` workers are independent UCI subprocesses with their own queue slots. No `AsyncSession` is shared (the worker has no DB connection).
- `loop=not args.once` cleanly maps the `--once` flag to the internal `loop` parameter.
- ORM registry imports included (same pattern as `scripts/resweep_holed_games.py`) to prevent SQLAlchemy mapper-configure failures when `app.*` imports run in script context.
- `run_worker` starts the pool before calling `get_stockfish_version()` so both run in the same asyncio event loop context; `pool.stop()` is guaranteed via `finally` regardless of `KeyboardInterrupt` or unexpected exceptions.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. Ruff reformatted one long log string that exceeded the line limit (expected; committed as part of the initial file since `ruff format` ran before the commit).

## User Setup Required

None for local dev. To use against a deployed server:
- Set `EVAL_OPERATOR_TOKEN` in `.env` on the server (already added in Plan 120-01)
- Run: `uv run python scripts/remote_eval_worker.py --base-url https://flawchess.com --token "$EVAL_OPERATOR_TOKEN"`
- MANUAL validation (per 120-VALIDATION.md): run `--dry-run --once` first to confirm connectivity, then `--once` to confirm one game's evals land and `full_evals_completed_at` is stamped.

## Known Stubs

None — worker is fully wired to call the lease/submit endpoints.

## Threat Flags

No new threat surfaces beyond what was documented in the plan's threat model (T-120-01 through T-120-SC). All mitigations implemented:
- T-120-01: Token sent as X-Operator-Token header only; startup log explicitly omits the token value
- T-120-02: sf_version read from `get_stockfish_version()` at startup — not fabricated
- T-120-03: `_eval_positions` passes engine results through unchanged; grep confirms no `post_move` reference

## Self-Check: PASSED

- FOUND: scripts/remote_eval_worker.py (308 lines, > 90 minimum)
- FOUND: commit d68bf3a0 (Task 1)
- Functions present: parse_args, run_worker, _run_loop, _eval_positions, main
- `evaluate_nodes_with_pv` in source: YES
- `get_stockfish_version` in source: YES
- `X-Operator-Token` in source: YES
- `post_move` in source: NO (D-2 satisfied)
- `--help` exits 0: YES
- ruff check: CLEAN
- ty check: ZERO ERRORS
- test_submit_applies_post_move_shift: PASSED
