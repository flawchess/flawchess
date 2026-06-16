---
phase: 123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big
plan: 03
subsystem: worker-cli
tags: [worker, ladder, entry-ply, depth-15, worker-id, httpx, secrets, unit-tests]

# Dependency graph
requires:
  - phase: 123-02
    provides: "POST /eval/remote/entry-lease, POST /eval/remote/entry-submit, scope param on /lease, X-Worker-Id advisory header"
provides:
  - "D-06 three-rung ladder in _run_cycle: scope=explicit -> entry-lease -> scope=idle"
  - "_eval_entry_positions: depth-15 eval helper (pool.evaluate, NOT evaluate_nodes_with_pv)"
  - "--worker-id CLI flag (< 10 chars, parser.error on violation)"
  - "_generate_worker_id: random ~8-char base36 worker ID using secrets.randbelow"
  - "X-Worker-Id header set once on httpx.AsyncClient alongside X-Operator-Token"
  - "11 unit tests: worker-id generation/validation + D-06 ladder sequencing + depth-15 assertion"
affects:
  - "leased_by and entry_eval_leased_by columns: now per-worker in prod instead of always 'remote-worker'"

# Tech tracking
tech-stack:
  added:
    - "secrets module (stdlib) for cryptographically random base36 worker IDs"
  patterns:
    - "D-06 ladder: explicit -> entry-lease -> idle across three separate HTTP calls"
    - "_handle_full_ply_response / _handle_entry_ply_response: extracted helpers for clean ladder branching"
    - "X-Worker-Id set once on AsyncClient constructor, not per-call"
    - "monkeypatch sys.argv for parse_args() unit tests (function reads sys.argv directly)"
    - "AsyncMock side_effect list for sequencing mock responses in ladder tests"

key-files:
  created:
    - tests/test_remote_eval_worker.py
  modified:
    - scripts/remote_eval_worker.py

key-decisions:
  - "D-06 ladder implemented in _run_cycle with two extracted helper functions (_handle_full_ply_response, _handle_entry_ply_response) for readable branching"
  - "_eval_entry_positions uses pool.evaluate (depth-15), explicitly documented in docstring NOT to use evaluate_nodes_with_pv"
  - "WORKER_ID_MAX_LEN=9 (exclusive upper bound len < 10) matches D-10 and VARCHAR(16) constraint with headroom"
  - "Task 2 (entry-ply eval + D-06 ladder) committed in same commit as Task 1 (worker-id + header) since they were implemented together"

patterns-established:
  - "Ladder pattern: _run_cycle branches on 204 vs 200 at each rung; 200 routes to a dedicated handler that returns immediately"
  - "Test pattern: _make_response() helper for mock httpx responses with side_effect list for sequencing"

requirements-completed: ["SEED-051-D-1", "SEED-051-D-2", "D-06", "D-08", "D-10"]

# Metrics
duration: ~6min
completed: 2026-06-16
---

# Phase 123 Plan 03: Worker Ladder Summary

**D-06 three-rung ladder in `_run_cycle`, depth-15 `_eval_entry_positions` using `pool.evaluate`, `--worker-id` CLI flag with random base36 default, and `X-Worker-Id` header on the httpx client**

## Performance

- **Duration:** ~6 min
- **Completed:** 2026-06-16
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- `_generate_worker_id()`: random ~8-char base36 ID using `secrets.randbelow` per character; guaranteed < 10 chars, fits VARCHAR(16) with headroom (D-09/D-10)
- `--worker-id` CLI arg added to `parse_args()` with `parser.error()` rejection on length >= 10 chars (mirroring the `--workers`/`--idle-sleep` validation pattern)
- `X-Worker-Id` header set once on `httpx.AsyncClient(headers={"X-Operator-Token": ..., "X-Worker-Id": ...})` alongside existing operator token -- no per-call change
- `WORKER_ID_MAX_LEN`, `_WORKER_ID_ALPHABET`, `_WORKER_ID_DEFAULT_LEN` named constants (no magic numbers)
- `_eval_entry_positions(pool, positions)`: depth-15 entry-ply eval helper using `pool.evaluate(b)` (NOT `evaluate_nodes_with_pv`) -- returns `{game_id, ply, eval_cp, eval_mate}` with no best_move/pv
- D-06 ladder restructured in `_run_cycle`: `POST /lease?scope=explicit` (rung 1) -> if 204, `POST /entry-lease` (rung 2) -> if 204, `POST /lease?scope=idle` (rung 3); extracted `_handle_full_ply_response` and `_handle_entry_ply_response` helpers for clean branching
- Entry-ply always-on (D-08): no opt-in flag; the server D-5 gate makes it free when no big import
- `run_worker()` gains `worker_id: str` parameter threaded through to the httpx client
- 11 unit tests in `tests/test_remote_eval_worker.py` covering: default ID length/charset, uniqueness, `--worker-id` length boundary (8 ok, 9 ok, 10 rejected), ladder call-order for tier-1/entry-ply/idle paths, and depth-15 (not 1M-node) assertion via `evaluate_nodes_with_pv.assert_not_called()`
- Full suite: 2705 passed, 10 skipped (up from 2694 in Plan 02; +11 new worker tests)

## Task Commits

1. **Task 1+2: --worker-id, X-Worker-Id, _eval_entry_positions, D-06 ladder** -- `845cc497` (feat)
2. **Task 3: TDD tests + ruff formatting** -- `1573bc71` (test)

Note: Tasks 1 and 2 were committed together since they were implemented in a single edit session with all implementation code written before the first commit.

## Files Created/Modified

- `scripts/remote_eval_worker.py` -- `secrets` import; `WORKER_ID_MAX_LEN`/`_WORKER_ID_ALPHABET`/`_WORKER_ID_DEFAULT_LEN` constants; `_generate_worker_id()`; `_eval_entry_positions()`; D-06 ladder in `_run_cycle`; `_handle_full_ply_response` / `_handle_entry_ply_response` helpers; `run_worker()` gains `worker_id` param; `parse_args()` gains `--worker-id` with length validation; `main()` generates/logs the resolved worker_id
- `tests/test_remote_eval_worker.py` -- 11 unit tests (no DB, no Stockfish); uses `monkeypatch.setattr(sys, "argv", ...)` for parse_args tests; `AsyncMock` side_effect sequences for ladder tests

## Decisions Made

- Extracted `_handle_full_ply_response` and `_handle_entry_ply_response` as separate helpers rather than deeply nesting if/else in `_run_cycle`. This keeps each path flat (CLAUDE.md nesting depth rule) and makes the D-06 ladder order readable as a linear sequence.
- `WORKER_ID_MAX_LEN = 9` (exclusive bound: len < 10) rather than 10 to make the semantics unambiguous (the constant IS the max allowed length).
- Tasks 1 and 2 implemented together and committed as a single feat commit since they have strong coupling (the ladder uses `_eval_entry_positions`; the header wiring and ladder are tightly related in `run_worker` and `_run_cycle`).

## Deviations from Plan

None -- plan executed exactly as written. The single implementation commit for Tasks 1+2 is a sequencing deviation (they were planned as separate commits) but not a behavioral one.

## Known Stubs

None -- no stub data or placeholder values in the implementation.

## Threat Flags

None -- no new network endpoints or auth paths. The `X-Worker-Id` header is advisory only and never used for authz (RESEARCH Security V4).

## Self-Check: PASSED

Files confirmed:
- `scripts/remote_eval_worker.py`: FOUND (`_eval_entry_positions` present, `pool.evaluate` in body)
- `tests/test_remote_eval_worker.py`: FOUND (11 tests)

Commits confirmed:
- `845cc497`: FOUND (feat -- worker-id, ladder, entry-eval)
- `1573bc71`: FOUND (test -- 11 unit tests)

Suite: 2705 passed, 10 skipped -- green.

grep guard: `_eval_entry_positions` body does NOT call `evaluate_nodes_with_pv` in functional code (only in docstring comment).

---
*Phase: 123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big*
*Completed: 2026-06-16*
