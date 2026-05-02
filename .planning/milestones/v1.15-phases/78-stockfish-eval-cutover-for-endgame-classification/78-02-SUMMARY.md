---
phase: 78
plan: "02"
subsystem: engine
tags: [engine, stockfish, async, lifespan, wrapper, tdd]
dependency_graph:
  requires: []
  provides: [app.services.engine, engine-start-stop-lifecycle]
  affects: [app.main, tests.conftest, tests.services.test_engine]
tech_stack:
  added: []
  patterns: [asyncio.Lock serialization, module-level process state, lifespan try/finally]
key_files:
  created:
    - app/services/engine.py
    - tests/services/test_engine.py
  modified:
    - app/main.py
    - tests/conftest.py
decisions:
  - "Idempotent start_engine() (no-op if already started) to support safe multiple calls"
  - "stop_engine() swallows EngineError/EngineTerminatedError on quit to avoid masking shutdown errors"
  - "_restart_engine() swallows restart failure so _protocol stays None and next evaluate() returns (None, None)"
  - "TestEngineNotStarted calls stop_engine() before asserting (None, None) to be resilient to session-scoped engine_started ordering"
  - "engine_started fixture in conftest.py skips start/stop when Stockfish binary is absent"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-02"
  tasks: 3
  files_touched: 4
---

# Phase 78 Plan 02: Engine Wrapper Summary

Async-friendly Stockfish wrapper with lifespan lifecycle management and Wave 0 TDD contract tests.

## What Was Built

`app/services/engine.py` (114 lines) implements:
- `start_engine()`: idempotent UCI process startup via `chess.engine.popen_uci` with `Hash=64MB, Threads=1`
- `stop_engine()`: graceful quit with swallowed EngineError/EngineTerminatedError
- `evaluate(board)`: depth-15 analysis under `asyncio.Lock` with 2.0s `asyncio.wait_for` timeout; on timeout/crash restarts engine and returns `(None, None)`
- White-perspective sign convention using `pov_score.white().score(mate_score=None)` / `.mate()` + clamp to `EVAL_CP_MAX_ABS` / `EVAL_MATE_MAX_ABS` -- byte-for-byte match with `app/services/zobrist.py:183-197`

`app/main.py` lifespan adds:
- `await start_engine()` after `get_insights_agent()` and `cleanup_orphaned_jobs()` (startup order preserved per D-22)
- `try: yield / finally: await stop_engine()` for guaranteed UCI process shutdown

`tests/services/test_engine.py`:
- 6 Stockfish-dependent tests under `@skip_if_no_stockfish` + `@pytest.mark.usefixtures("engine_started")`
- 1 not-started test independent of binary presence (tests graceful (None, None) degradation)

`tests/conftest.py`:
- Session-scoped `engine_started` fixture that starts/stops the engine once per pytest session

## ENG-03 Sign-Off

Grep gate clean: `popen_uci` and `chess.engine.Limit` appear ONLY in `app/services/engine.py`.

```
app/services/engine.py:47: _transport, _protocol = await chess.engine.popen_uci(_STOCKFISH_PATH)
app/services/engine.py:88: _protocol.analyse(board, chess.engine.Limit(depth=_DEPTH)),
```

No leakage into `scripts/`, other `app/` files, or tests.

## Stockfish Version

Stockfish binary not present on this dev machine (`which stockfish` returns not found). The engine-dependent tests (`TestEngineWrapper`) are gated by `@skip_if_no_stockfish` and were confirmed to skip cleanly. The not-started test (`TestEngineNotStarted`) ran and passed.

CI installs Stockfish via `apt-get install -y stockfish` (plan 78-01 adds this to the Dockerfile; the GitHub Actions CI workflow should mirror this for the test suite).

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED  | 0cafe85 | `test(78-02): add failing Wave 0 engine wrapper contract tests` |
| GREEN | d4f9ecc | `feat(78-02): implement Stockfish engine wrapper (ENG-02 GREEN)` |
| Lifespan | d8cc94d | `feat(78-02): wire engine start/stop into FastAPI lifespan (D-02)` |

## Deviations from Plan

None. Plan executed exactly as written with one minor implementation note:

**Deviation: `_restart_engine()` swallows restart exceptions**

The plan template's `_restart_engine()` called `stop_engine()` then `start_engine()` without exception handling on the restart attempt. Added a `try/except Exception: pass` around `start_engine()` in `_restart_engine()` so that if Stockfish cannot be restarted (e.g., binary path wrong after a failed first start), `_protocol` stays `None` and subsequent `evaluate()` calls return `(None, None)` rather than raising. This is a correctness improvement (Rule 1) aligned with D-11 "caller decides what to log."

**Deviation: `engine_started` conftest fixture skips gracefully when Stockfish absent**

The plan snippet showed a fixture that always called `start_engine()`. Added a `shutil.which("stockfish") is None` guard so the fixture is a no-op when the binary is absent, matching the `@skip_if_no_stockfish` pattern on the tests themselves.

## Threat Coverage

All mitigations from the plan's `<threat_model>` are implemented:

| Threat | Mitigation | Where |
|--------|-----------|-------|
| T-78-06 (DoS: wedged engine) | `asyncio.wait_for(..., timeout=2.0)` + restart in `evaluate()` | engine.py:87-93 |
| T-78-07 (DoS: concurrent callers) | `asyncio.Lock` serializes all `evaluate()` calls | engine.py:39, 81 |
| T-78-08 (Tampering: wrong sign) | `pov_score.white().score()/.mate()` + clamp bounds imported from zobrist.py | engine.py:105-112 |
| T-78-09 (Info disclosure) | Exceptions swallowed in wrapper; Sentry capture is call-site responsibility | engine.py:89-93 |
| T-78-10 (EoP: subprocess) | Accepted; no change | N/A |

## Known Stubs

None. This plan creates an engine wrapper with no UI or data-rendering paths.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| app/services/engine.py | FOUND |
| tests/services/test_engine.py | FOUND |
| tests/conftest.py (modified) | FOUND |
| app/main.py (modified) | FOUND |
| commit 0cafe85 (RED) | FOUND |
| commit d4f9ecc (GREEN) | FOUND |
| commit d8cc94d (lifespan) | FOUND |
