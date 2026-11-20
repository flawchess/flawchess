---
status: complete
phase: quick-261120-j5f
plan: 01
subsystem: train
tags: [bugfix, frontend, blunder-check, sentry]
key_files:
  created: []
  modified:
    - frontend/src/lib/blunderCheckDrill.ts
    - frontend/src/lib/queryClient.ts
    - frontend/src/hooks/useBlunderCheckSession.ts
    - frontend/src/components/train/blunder-check/BlunderCheckDrill.tsx
    - frontend/src/components/train/blunder-check/BlunderCheckTab.tsx
    - CHANGELOG.md
decisions:
  - Resync from GET /sessions/open rather than the compose/resume POST, so a recovery can never compose a new session by accident
  - A session that is closed, missing or replaced returns to Today instead of silently starting something else
  - The recovery callback is read through a ref so an unstable host callback cannot re-send the window requests
metrics:
  completed: "2026-11-20"
---

# Quick 261120-j5f: Blunder check cross-device resync

Fixes Sentry FLAWCHESS-DJ. A blunder-check session continued on a second device left the
first device asking for a window that had already ended (it counted `position + 1` locally).
The server's 409 `window_ended` ended the drill on the generic error screen.

## What changed

- New reducer event `SESSION_RESYNCED`: from any running drill phase, restart from the
  server's progress (the current window, or finishing when none is left).
- `recoverFromConflict` in `BlunderCheckDrill.tsx` handles a 409 from start, begin, answer
  and the stale-prompt reload: `window_ended` / `previous_window_open` re-fetch the open
  session and resync; `session_closed`, or an open session that is missing or a different
  one, resets and returns to Today. Anything else still shows the error screen.
- `useBlunderCheckSession` exposes `fetchOpenSession` (cache-bypassing).
- `lib/queryClient.ts`: mutations can declare `meta.expectedConflictDetails`; a declared 409
  is not sent to Sentry. Declared on start, begin and answer for `stale_prompt`,
  `window_ended`, `previous_window_open` and `session_closed`.

## Verification

- 7 new tab tests, 3 reducer tests, 2 query-client tests. With the recovery disabled the 7
  tab tests fail; restored, they pass.
- `npm run lint`, `npm run build`, `npm test -- --run` (6634 passed), `npm run knip`: all green.
- Not verified on real devices: the two-device sequence was reproduced only through mocked
  API responses.

## Not covered

- The better-move and solution requests keep their current failure handling. A better move
  already played on the other device (409 `better_move_done`) is not resynced.
- A window that ended on the other device is skipped without showing its solution here.

## Process note

Planned and executed inline in the worktree `../flawchess-bc-resync` (branch
`quick/blunder-check-cross-device-resync`, off `main`), not through planner and executor
subagents: the main checkout was mid-phase 257 with uncommitted work.

Commit: 4fe7eccfc
