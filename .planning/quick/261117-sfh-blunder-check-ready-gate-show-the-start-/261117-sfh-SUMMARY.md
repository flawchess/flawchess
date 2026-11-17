---
phase: quick-261117-sfh
plan: 01
subsystem: blunder-check
tags: [blunder-check, ready-gate, fastapi, react, state-machine]
status: complete
requires: []
provides:
  - "POST /blunder-check/sessions/{id}/windows/{pos}/begin"
  - "WindowStartResponse.awaiting_ready"
  - "drill phases ready_gate and beginning"
affects: [blunder-check drill, Train tab]
tech-stack:
  added: []
  patterns: ["server-side clock origin moved to a begin step (no migration)"]
key-files:
  created: []
  modified:
    - app/schemas/blunder_check.py
    - app/services/blunder_check_service.py
    - app/routers/blunder_check.py
    - tests/routers/test_blunder_check_drill.py
    - CHANGELOG.md
    - frontend/src/types/blunderCheck.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useBlunderCheckSession.ts
    - frontend/src/lib/blunderCheckDrill.ts
    - frontend/src/lib/__tests__/blunderCheckDrill.test.ts
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/lib/__tests__/trainBotCopy.test.ts
    - frontend/src/components/train/blunder-check/BlunderCheckDrill.tsx
    - frontend/src/components/train/blunder-check/BlunderCheckTab.tsx
    - frontend/src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx
key-decisions:
  - "start stamps started_at but inserts no answer row; begin inserts the first prompt row (prompted_at = begin's now_utc). Gate up == started window with no answer rows. No migration."
  - "start and begin share one _window_start payload builder so the gate and the post-Ready payload cannot drift."
  - "Ready is the single primary CTA (variant default); no Umami event (Phase 249 D-19)."
metrics:
  tasks: 3
  commits: 3
  files: 15
plan_head_before: 9251197330f0e283ef1e9528af321febde8cbf81
plan_head_after: bca5a9b4db8d5e9fb5775371b9d729b6abe5a212
actuals:
  tasks: 3
  commits: 3
completed: 2026-11-17
---

# Phase quick-261117-sfh Plan 01: Blunder-check Ready gate Summary

Every blunder-check window now opens paused on its start position with a host bubble ("Check out the position, you play white|black. It's your opponent's turn.") and a Ready button; the first prompt's server clock starts only at a new `begin` step, so studying the position can no longer burn the 10 s timer or the 15 s answer ceiling.

## Commits

- `fef91374d` feat: server Ready gate (start opens the gate, begin issues the first prompt, 7 new tests)
- `f594216c4` feat: frontend contract and reducer (`ready_gate` -> `beginning` -> `lead_in`, `beginWindow` transport)
- `bca5a9b4d` feat: Ready bubble on the board, immersive gate phases, tab tests on the gated flow

## What changed

- Backend: `start_window` no longer inserts the first prompt row; `begin_window` does (ON CONFLICT DO NOTHING, so idempotent and never re-stamps). `WindowStart.awaiting_ready` is true exactly when a started window has no answer rows. `_FULL_TIMER_MS` replaces the inline product. No migration.
- Frontend: reducer phases `ready_gate`/`beginning`, events `READY_CONFIRMED`/`WINDOW_BEGUN`, `useWindowBeginner` effect, `ReadyGateBubble` (testid `blunder-check-btn-ready`), `blunderCheckReadyCopy(side, sideToMove)` (follows the start FEN, so a 0-ply lead-in says "It's your turn."), gate phases added to `IMMERSIVE_PHASES`.
- CHANGELOG `[Unreleased]` -> Changed bullet added.

## Verification

- `uv run pytest tests/routers/test_blunder_check_drill.py tests/routers/test_blunder_check_solution.py tests/repositories/test_blunder_check_repository.py -n auto -q`: 82 passed (was 56 router tests + repository tests; 7 new gate tests).
- Mutation check: re-inserting the prompt in `start_window` made 7 tests fail (the 6 new gate tests plus the tracer test); reverted.
- `uv run ruff format --check app/ tests/`, `uv run ruff check .`, `uv run ty check app/ tests/ scripts/`, `check_function_size.py app/ --fail-over-depth 4`: clean.
- Frontend: blunderCheckDrill + trainBotCopy + blunder-check component tests: 224 passed (5 files); `npm run lint`, `npm run build`, `npm run knip` clean.
- `git status --porcelain alembic/`: empty.

## Deviations from Plan

None - plan executed as written. One test-writing slip fixed inline: the new "time never counts toward the answer ceiling" test first asserted exactly one answer row, but answering a non-final herring move creates the next prompt row; the assertion now checks the first row only.

## Known Stubs

None.

## Threat Flags

None. T-sfh-01 (IDOR) and T-sfh-02 (buying time) mitigations are covered by the extended IDOR/non-beta tests and the idempotent-begin test.

## Self-Check: PASSED

Commits `fef91374d`, `f594216c4`, `bca5a9b4d` exist on main; all listed files exist.
