---
phase: 120-headless-remote-trusted-operator-eval-worker-seed-048
plan: "01"
subsystem: api
tags: [stockfish, pydantic, config, engine, remote-eval, schemas]

requires:
  - phase: 117-tiered-priority-eval-queue
    provides: engine.py EnginePool, evaluate_nodes_with_pv, PV_CAP_PLIES — reused as-is

provides:
  - Settings.EVAL_OPERATOR_TOKEN + Settings.EXPECTED_SF_VERSION in app/core/config.py
  - app/schemas/eval_remote.py with 5 Pydantic v2 models (LeasePosition, LeaseResponse, SubmitEval, SubmitRequest, SubmitResponse)
  - get_stockfish_version() async helper in app/services/engine.py

affects:
  - 120-02 (eval_remote router imports these schemas + uses settings fields)
  - 120-03 (remote_eval_worker.py imports get_stockfish_version + schemas)

tech-stack:
  added: []
  patterns:
    - "New Settings fields follow EVAL_AUTO_DRAIN_ENABLED comment style — explain default + prod override, never log sensitive values"
    - "Schema file: module docstring naming the phase, one BaseModel per DTO, int|None for nullable numerics"
    - "get_stockfish_version() as a standalone async helper before EnginePool — one-shot UCI handshake, no pool instantiation"

key-files:
  created:
    - app/schemas/eval_remote.py
  modified:
    - app/core/config.py
    - app/services/engine.py

key-decisions:
  - "EVAL_OPERATOR_TOKEN defaults to empty string — empty disables both endpoints (fail-closed); prod sets a strong random secret in .env (D-6)"
  - "EXPECTED_SF_VERSION defaults to empty string — empty accepts any version in dev/CI; prod pins engine generation (D-5)"
  - "user_id threaded from LeaseResponse into SubmitRequest so the submit endpoint avoids an extra DB query to resolve user ownership"
  - "fen carries board.fen() (full FEN with turn/castling/en-passant), not board_fen() — required for accurate position replay in the worker"
  - "get_stockfish_version() uses module-level _STOCKFISH_PATH and _engine_popen_kwargs() directly — no re-resolution, no EnginePool construction"

patterns-established:
  - "Remote eval wire contract: lease returns positions list with full FEN + is_terminal flag; submit echoes game_id + user_id back"
  - "Operator token pattern: empty setting = 403 (not configured); wrong token = 401; correct token = proceed"

requirements-completed: [D-1, D-5, D-6]

duration: 15min
completed: 2026-06-14
---

# Phase 120 Plan 01: Foundation Layer (Settings + Schemas + Version Helper) Summary

**EVAL_OPERATOR_TOKEN + EXPECTED_SF_VERSION settings, five Pydantic v2 eval-remote wire schemas, and a one-shot get_stockfish_version() UCI handshake helper — the contract surface every downstream plan (120-02 endpoints, 120-03 CLI worker) consumes.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-14T17:30:00Z
- **Completed:** 2026-06-14T17:45:53Z
- **Tasks:** 2
- **Files modified:** 3 (2 modified, 1 created)

## Accomplishments

- Added `EVAL_OPERATOR_TOKEN` and `EXPECTED_SF_VERSION` to `Settings` with fail-closed defaults (empty string) and matching comment style
- Created `app/schemas/eval_remote.py` with all five Pydantic v2 models for the lease/submit wire contract
- Added `get_stockfish_version()` async helper to `engine.py` — one-shot UCI handshake, no EnginePool construction
- All changes pass `ty check`, `ruff format`, and `ruff check` with zero errors

## Task Commits

1. **Task 1: Add EVAL_OPERATOR_TOKEN + EXPECTED_SF_VERSION + get_stockfish_version()** - `1ef32746` (feat)
2. **Task 2: Create eval_remote Pydantic v2 wire schemas** - `984cacd1` (feat)
3. **Formatting fix** - `0a5754c1` (style: ruff format trailing whitespace in inline comments)

## Files Created/Modified

- `app/core/config.py` — Added `EVAL_OPERATOR_TOKEN: str = ""` and `EXPECTED_SF_VERSION: str = ""` after `EVAL_AUTO_DRAIN_ENABLED`
- `app/services/engine.py` — Added `get_stockfish_version() -> str` async helper before `class EnginePool`
- `app/schemas/eval_remote.py` — New file: `LeasePosition`, `LeaseResponse`, `SubmitEval`, `SubmitRequest`, `SubmitResponse`

## Decisions Made

- `EVAL_OPERATOR_TOKEN` empty default = fail-closed (endpoints return 403 when unconfigured), matching the security disposition from T-120-01.
- `EXPECTED_SF_VERSION` empty default = accept any version in dev/CI; the gate enforcing it lives in 120-02.
- `user_id` is threaded through `LeaseResponse` → `SubmitRequest` to avoid an extra DB query in the submit endpoint.
- `fen` uses `board.fen()` (full FEN) not `board_fen()` — includes turn/castling/en-passant needed for accurate position replay.
- `get_stockfish_version()` reuses module-level `_STOCKFISH_PATH` and `_engine_popen_kwargs()` with no EnginePool construction — it is a one-shot helper for worker startup only.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. Ruff reformatted trailing whitespace in inline comments after writing (expected; committed as a style fix).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- 120-02 (eval_remote router) can import `LeaseResponse`, `SubmitRequest`, `SubmitResponse` and `settings.EVAL_OPERATOR_TOKEN` / `settings.EXPECTED_SF_VERSION` directly.
- 120-03 (CLI worker) can import `get_stockfish_version` and all five schema models directly.
- No blockers.

---

*Phase: 120-headless-remote-trusted-operator-eval-worker-seed-048*
*Completed: 2026-06-14*
