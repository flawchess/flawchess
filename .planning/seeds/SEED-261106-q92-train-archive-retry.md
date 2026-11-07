---
id: SEED-261106-q92
status: dormant
planted: 2026-11-06
planted_during: v2.27, phase 244 (/gsd-explore session)
trigger_when: once the Train subnav split / Archive tab (SEED-261106-gw8) has shipped
scope: phase (session-less solve path plus a seam in TrainSolveScreen)
depends_on: SEED-261106-gw8
---

# SEED-261106-q92: Retry a puzzle from the Train Archive

## Why This Matters

Mastered puzzles stop coming back and parked puzzles are set aside, so the Archive would otherwise be view-only. Parked puzzles are the user's hardest positions, and a retry lets them try again without disturbing their spaced-repetition schedule or competitive stats.

## When to Surface

**Trigger:** once the Train subnav split / Archive tab (SEED-261106-gw8) has shipped.

## Scope Estimate

**One phase, probably small.** The main work is a session-less solve path and a seam in `TrainSolveScreen`.

## Decisions

- **Button:** Retry on Archive puzzle cards, both Mastered and Parked.
- **Flow:** runs that single puzzle once, then returns to the Archive at the same tab and page.
- **No side effects:** no effect on spaced repetition, session stats, streak or leaderboard.
- **Status:** a parked puzzle stays parked after a successful retry and does not re-enter rotation.
- **History:** a retry leaves no record by design. Retry history would be a separate decision.

## Implementation Notes

- **Separate solve path:** solves currently go through `POST /train/sessions/{session_id}/solve`, and `drill_solves` rows require a session (primary key `session_id` + `position`). Retry needs its own session-less path that writes nothing to `drill_solves`. A row there could affect stats and the Archive's newest-first sort, which relies on the latest `drill_solves.solved_at` per puzzle.
- **Solve screen:** `TrainSolveScreen` takes the `trainSession` object as a prop and is tightly bound to it, so reusing it needs a seam for a session-less run. The reveal endpoint is also keyed by session and position.
- **Guess step (inferred from the schema, not confirmed):** each puzzle includes a guess (`drill_solves.guess`, `correct_guess`) and red herrings exist, but archive puzzles are never herrings. If the guess is about spotting herrings, it is spoiled in a retry, so retry should probably go straight to the move. Confirm what the guess asks during planning.
- **Cards:** they show the pre-mistake position and, since 2026-11-07, the played mistake (arrow, notation, severity) but never the best move, so the answer isn't given away, though a retry starts knowing which move to avoid. SEED-261106-gw8 reserves space for the button.
- **Analytics:** a retry writes no row, so unlike DB-known actions it needs a `trackFeature` event registered in `FeatureEventMap`.

## Breadcrumbs

- `app/routers/train.py`: session-keyed solve and reveal endpoints
- `app/models/drill_solve.py`: primary key and `solved_at`
- `frontend/src/components/train/TrainSolveScreen.tsx`: `trainSession` coupling
- `frontend/src/hooks/useTrainSession.ts`: session state and solve mutation
- `frontend/src/lib/analytics.ts`: `FeatureEventMap`
