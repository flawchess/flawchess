---
status: complete
phase: 260510-p6i
plan: 01
subsystem: engine
tags: [stockfish, scheduling, sched-idle, pool, prod-config]
requires:
  - chess.engine.popen_uci preexec_fn pass-through (asyncio.create_subprocess_exec)
  - os.sched_setscheduler / os.SCHED_IDLE (Linux only)
provides:
  - Linux SCHED_IDLE Stockfish workers via app/services/engine.py
  - STOCKFISH_POOL_SIZE default 4 in docker-compose.yml + .prod.env
affects:
  - app/services/engine.py
  - docker-compose.yml
  - .prod.env (gitignored)
tech-stack:
  added: []
  patterns:
    - preexec_fn for kernel scheduling class on forked Stockfish children
    - sys.platform == "linux" guard so dev-on-macOS keeps default scheduling
key-files:
  created: []
  modified:
    - app/services/engine.py
    - docker-compose.yml
    - .prod.env
decisions:
  - Swallow OSError from sched_setscheduler — degrade to normal priority instead of crashing engine spawn if a containerised host blocks it
  - Type _engine_popen_kwargs return as dict[str, Any] (not dict[str, object]) because chess.engine.popen_uci has a typed setpgrp:bool param that ty resolves splatted kwargs against
  - Drop the # ty: ignore on os.sched_setscheduler — ty (running on Linux) already knows the symbols exist
metrics:
  duration: ~12 minutes
  completed: 2026-05-10
requirements:
  - SCHED-IDLE-01
  - POOL-SIZE-04
---

# Quick Task 260510-p6i: SCHED_IDLE Stockfish + pool=4 Summary

Apply Linux SCHED_IDLE to every Stockfish UCI subprocess spawned by `app/services/engine.py` and bump the prod pool size default from 3 to 4 so all 4 vCPUs can be saturated by import-time eval without starving Uvicorn or Postgres.

## Files Changed

| File | Change |
| --- | --- |
| `app/services/engine.py` | Added `_sched_idle_preexec` + `_engine_popen_kwargs` helpers; both `popen_uci` call sites (start + _restart_worker) now splat the kwargs dict; module docstring + `_DEFAULT_POOL_SIZE` comment updated. |
| `docker-compose.yml` | Backend service `STOCKFISH_POOL_SIZE` default `:-2` → `:-4`; comment rewritten to cite SCHED_IDLE rationale. |
| `.prod.env` (gitignored) | `STOCKFISH_POOL_SIZE=3` → `STOCKFISH_POOL_SIZE=4`; comment block expanded to document SCHED_IDLE safety + memory cost (4 × 64 MB hash = 256 MB on 7.6 GB box). |

## Pool Size Delta

Production pool size: **3 → 4** (one Stockfish worker per vCPU on the Hetzner CX32 box).

Compose default: **2 → 4** (matches prod for any host that doesn't override via `.env`).

## Platform Guard Mechanism

`_engine_popen_kwargs()` returns:

- Linux: `{"preexec_fn": _sched_idle_preexec}` — kernel runs SCHED_IDLE on the forked child before exec, so Stockfish only consumes idle CPU cycles.
- macOS / Windows: `{}` — `os.sched_setscheduler` doesn't exist there, so the helper returns no kwargs and Stockfish spawns with default scheduling. Dev-on-Mac behaviour is byte-identical to before this change.

`_sched_idle_preexec()` swallows `OSError` so a containerised host with a seccomp filter blocking `sched_setscheduler` degrades to normal priority rather than crashing engine spawn (which would break the import pipeline).

## Verification

Backend gates (run after both tasks):

```bash
uv run ruff check app/services/engine.py        # ✓ All checks passed
uv run ruff format --check app/services/engine.py # ✓ 1 file already formatted
uv run ty check app/services/engine.py          # ✓ All checks passed
uv run pytest -x -q -k "engine or eval"         # ✓ 81 passed, 6 skipped
```

Whole-app gates:

- `uv run ruff check app/`: clean.
- `uv run ty check app/ tests/`: clean.
- `uv run ruff format --check app/`: 16 pre-existing files report formatting drift. This is the carried "Project-wide ruff format drift" already documented in STATE.md deferred items — out of scope for this quick task.

## Post-Deploy Verification

Manual check after `bin/deploy.sh`:

```bash
ssh flawchess "cd /opt/flawchess && docker compose exec backend ps -eo pid,cls,pri,ni,comm | grep stockfish"
```

Expected output: 4 rows, `CLS` column showing `IDL` (SCHED_IDLE), one process per vCPU. If `CLS` shows `TS` (SCHED_OTHER) instead, the `preexec_fn` did not apply — investigate container seccomp / capabilities.

## Deviations from Plan

**1. [Rule 3 — blocking issue] `dict[str, object]` return type rejected by ty**

- **Found during:** Task 1 verification (ty check)
- **Issue:** `chess.engine.popen_uci(..., **_engine_popen_kwargs())` failed `ty check` with `Expected 'bool', found 'object'`. ty resolves splatted kwargs against the function's typed `setpgrp: bool` parameter first (before falling through to `**popen_args: Any`).
- **Fix:** Changed `_engine_popen_kwargs` return type from `dict[str, object]` to `dict[str, Any]`; added `from typing import Any`. Documented the reason in the helper's docstring so future readers don't "fix" it back.
- **Files modified:** `app/services/engine.py`
- **Commit:** `2a94734b` (rolled into Task 1 commit)

**2. [Rule 1 — bug] Plan suggested `# ty: ignore[unresolved-attribute]` on `os.SCHED_IDLE`, but ty resolves it on Linux**

- **Found during:** Task 1 verification (ty check)
- **Issue:** Initial implementation included the suppression comment proactively (since `SCHED_IDLE` is Linux-only). ty (running on Linux) flagged the suppression as unused.
- **Fix:** Dropped the `# ty: ignore[...]` line. Acceptable trade-off: ty checks run on Linux in CI and will resolve the attribute; if dev-on-macOS contributors run ty locally and hit `unresolved-attribute`, they can add the suppression back at that point.
- **Files modified:** `app/services/engine.py`
- **Commit:** `2a94734b` (rolled into Task 1 commit)

## Threat Flags

None — change is internal scheduling policy + pool-size config. No new network endpoints, auth paths, file access patterns, or schema changes.

## Known Stubs

None.

## Commits

- `2a94734b` — feat(260510-p6i): apply Linux SCHED_IDLE to Stockfish UCI subprocesses
- `5d14dc43` — chore(260510-p6i): bump STOCKFISH_POOL_SIZE default to 4 in docker-compose

`.prod.env` change is intentionally uncommitted (gitignored production secrets file).

## Self-Check: PASSED

- `app/services/engine.py` modified — FOUND (commit `2a94734b`)
- `docker-compose.yml` modified — FOUND (commit `5d14dc43`)
- `.prod.env` modified — FOUND on disk (gitignored, not in git)
- `os.SCHED_IDLE` reference present in engine.py — FOUND
- `sys.platform == "linux"` guard present — FOUND
- `STOCKFISH_POOL_SIZE=4` in `.prod.env` — FOUND
- `STOCKFISH_POOL_SIZE:-4` in docker-compose.yml — FOUND
- No stale `=3` / `:-2` / `:-3` references — CONFIRMED
- Lint, format, type checks, targeted tests all green — CONFIRMED
