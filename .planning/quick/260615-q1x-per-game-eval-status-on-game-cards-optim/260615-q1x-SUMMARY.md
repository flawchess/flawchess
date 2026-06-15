---
phase: 260615-q1x
plan: "01"
type: quick
subsystem: library
tags: [library, eval-jobs, ux, frontend, backend]
dependency_graph:
  requires: []
  provides:
    - active_eval_status field on library-games payload
    - fetch_page_active_eval_status batch repository helper
    - Three-state NoAnalysisState pill (Analyze → Pending… → Analyzing…)
  affects:
    - GET /api/library/games (GameFlawCard payload)
    - GET /api/library/games/{game_id} (GameFlawCard payload)
    - NoAnalysisState component (desktop + mobile)
tech_stack:
  added: []
  patterns:
    - Batch LEFT JOIN pattern matching fetch_page_analyzed_set
    - Optimistic UI with error rollback on enqueue mutation
key_files:
  created: []
  modified:
    - app/schemas/library.py
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - tests/test_library_repository.py
    - tests/services/test_library_service.py
    - frontend/src/types/library.ts
    - frontend/src/components/library/NoAnalysisState.tsx
    - frontend/src/components/results/LibraryGameCard.tsx
    - frontend/src/components/library/__tests__/NoAnalysisState.test.tsx
decisions:
  - "Pill shows 'Pending…' for both optimistic in-flight and activeEvalStatus='pending'; 'Analyzing…' only for 'leased'"
  - "No new endpoint or poll — rides the existing library-games poll (3s while in-flight)"
  - "Optimistic click fires onInFlightChange(true) before mutate; onError rolls back"
metrics:
  duration: "~35 minutes"
  completed: "2026-06-15"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 9
---

# Phase 260615-q1x Plan 01: Per-Game Eval Status on Game Cards Summary

Per-game eval-job status (`active_eval_status`) is now surfaced on Library game cards, giving users immediate feedback when they click "Analyze". The pill transitions optimistically from the "Analyze" button to "Pending…" on click, flips to "Analyzing…" once a worker leases the job, and clears to the analyzed view when evaluation completes.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Enrich library-games payload with active_eval_status | 51deddad | app/schemas/library.py, app/repositories/library_repository.py, app/services/library_service.py, tests/ |
| 2 | Three-state pill with optimistic click (desktop + mobile) | b20657f6, 6205fa3e | frontend/src/types/library.ts, NoAnalysisState.tsx, LibraryGameCard.tsx, test |
| - | Ruff format | 7e3d6478 | app/services/library_service.py, tests/services/test_library_service.py |

## What Was Built

### Backend (Task 1)

**`app/repositories/library_repository.py`** — `fetch_page_active_eval_status(session, user_id, game_ids)`:
- Batch helper mirroring the shape of `fetch_page_analyzed_set`.
- Queries `EvalJob.game_id, EvalJob.status` filtered to `game_ids IN (...)` AND `status IN ('pending', 'leased')`.
- The partial unique index `uq_eval_jobs_game_active` guarantees at most one active row per game, so the result is a flat `dict[int, Literal["pending", "leased"]]`.
- T-q1x-01 IDOR: game_ids are already scoped to the authenticated user before reaching this helper.

**`app/schemas/library.py`** — `GameFlawCard.active_eval_status: Literal["pending", "leased"] | None = None`

**`app/services/library_service.py`**:
- `_build_card()` gains `active_eval_status` param.
- `get_library_games()` calls `fetch_page_active_eval_status` after the existing batch fetches and passes `active_status_map.get(game.id)` to each `_build_card()`.
- `get_library_game()` does the same with `[game_id]`.
- Both are sequential on the same `AsyncSession` (no `asyncio.gather` per CLAUDE.md).

**Tests** (12 new cases):
- `tests/test_library_repository.py`: `TestFetchPageActiveEvalStatus` — pending, leased, absent, completed, empty game_ids, batch mixed status.
- `tests/services/test_library_service.py`: `TestActiveEvalStatus` — pending/leased/absent on `get_library_games`; pending and completed on `get_library_game`.

### Frontend (Task 2)

**`frontend/src/types/library.ts`** — `active_eval_status: 'pending' | 'leased' | null` added to `GameFlawCard` interface.

**`frontend/src/components/library/NoAnalysisState.tsx`**:
- New `activeEvalStatus?: 'pending' | 'leased' | null` prop.
- Shows pill when `isInFlight || activeEvalStatus === 'pending' || activeEvalStatus === 'leased'`.
- Label: `"Analyzing…"` when `activeEvalStatus === 'leased'` (worker running); `"Pending…"` otherwise.
- `data-testid={`analyzing-${gameId}`}` preserved (unchanged for test compatibility).
- Optimistic click: `onInFlightChange?.(true)` fires first, then `tier1Mutation.mutate(undefined, { onError: () => onInFlightChange?.(false) })`. No `onSuccess` needed — the optimistic call already sets in-flight.

**`frontend/src/components/results/LibraryGameCard.tsx`**:
- `activeEvalStatus={game.active_eval_status}` passed to BOTH `<NoAnalysisState>` instances: the mobile/col-3 `flawContent` branch AND the desktop col-2 analyzed-but-missing-series fallback. Mobile parity confirmed.

**`frontend/src/components/library/__tests__/NoAnalysisState.test.tsx`**:
- Updated to cover five branches: guest, button, optimistic Pending…, server Pending…, server Analyzing…, analyzed.
- Corrected the old test that expected "Analyzing" for `isInFlight=true` (now "Pending…").
- Added test verifying `onInFlightChange(true)` is called before `mutate`.

**`GamesTab.tsx`**: no change — the existing poll condition (`analyzedCount < totalCount || inFlightIds.size > 0`) already keeps the library-games poll alive while any analyze is in-flight.

## Deviations from Plan

None — plan executed exactly as written. The only non-trivial deviation was discovering that the existing frontend test expected "Analyzing" for `isInFlight=true`, which is now "Pending…" per the new three-state design. The test was updated to match the intended behavior.

## Pre-PR Gate Results

All gates green:

```
uv run ruff format app/ tests/     → 237 files unchanged (after committing style fix)
uv run ruff check app/ tests/ --fix → All checks passed
uv run ty check app/ tests/         → All checks passed
uv run pytest -n auto -x            → 2649 passed, 10 skipped
( cd frontend && npm run lint && npm test -- --run ) → 81 test files, 934 tests passed
```

## Self-Check: PASSED

- `app/repositories/library_repository.py`: fetch_page_active_eval_status present — FOUND
- `app/schemas/library.py`: active_eval_status field — FOUND
- `app/services/library_service.py`: active_status_map in get_library_games — FOUND
- `frontend/src/types/library.ts`: active_eval_status field — FOUND
- `frontend/src/components/library/NoAnalysisState.tsx`: three-state pill — FOUND
- `frontend/src/components/results/LibraryGameCard.tsx`: both NoAnalysisState instances updated — FOUND
- Commits 51deddad, b20657f6, 7e3d6478, 6205fa3e present in git log — VERIFIED
