---
phase: quick
plan: 260319-rj3
subsystem: imports
tags: [import, persistence, ux, polling]
dependency_graph:
  requires: []
  provides: [active-job-restoration, live-game-count]
  affects: [import-page, app-routing]
tech_stack:
  added: []
  patterns: [useEffect-with-ref-guard, periodic-invalidation]
key_files:
  created: []
  modified:
    - app/services/import_service.py
    - app/routers/imports.py
    - frontend/src/hooks/useImport.ts
    - frontend/src/App.tsx
    - frontend/src/pages/Import.tsx
decisions:
  - "No DB fallback for /imports/active — only in-memory active jobs; after server restart background tasks are gone so there is nothing to restore"
  - "hasRestoredRef + restoredForTokenRef pattern: restoration runs once per login session; token change resets the guard so re-login triggers a fresh restoration"
  - "isDone/isError/isActive computed before useEffect in ImportProgressBar to avoid duplicate variable declarations"
metrics:
  duration: ~15 minutes
  completed_date: "2026-03-19"
  tasks_completed: 2
  files_modified: 5
---

# Quick Task 260319-rj3: Persist Import Job Status Across Login Summary

**One-liner:** Backend `GET /imports/active` endpoint + frontend mount-time restoration hook + periodic 5s game count invalidation during active imports.

## What Was Built

### Task 1: GET /imports/active backend endpoint

- Added `find_active_jobs_for_user(user_id: int) -> list[JobState]` to `import_service.py`. Iterates `_jobs` and returns all jobs for the given user with PENDING or IN_PROGRESS status.
- Added `GET /imports/active` endpoint to `imports.py` router, declared before `GET /{job_id}` to avoid path conflict. Requires authenticated user. Returns `list[ImportStatusResponse]` from in-memory registry only — no DB fallback (intentional: after server restart background tasks are gone).

### Task 2: Frontend restoration + live game count updates

- Added `useActiveJobs(enabled: boolean)` hook in `useImport.ts` — calls `GET /imports/active`, one-shot on mount (`staleTime: 0`, `refetchInterval: false`), gated by `!!token` to prevent 401s.
- Updated `AppRoutes` in `App.tsx`: calls `useActiveJobs`, uses `hasRestoredRef` to seed `activeJobIds` exactly once per login session. `restoredForTokenRef` tracks which token the restoration was performed for — resets the guard when token changes (re-login), ensuring fresh restoration without re-adding previously dismissed jobs.
- Added periodic game count invalidation to `ImportProgressBar` in `Import.tsx`: `setInterval` every 5 seconds while `isActive` is true, calling `queryClient.invalidateQueries` for `['userProfile']` and `['gameCount']`. Interval cleaned up on job completion or unmount.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

Files created/modified:
- `app/services/import_service.py` — MODIFIED (find_active_jobs_for_user added)
- `app/routers/imports.py` — MODIFIED (GET /imports/active added)
- `frontend/src/hooks/useImport.ts` — MODIFIED (useActiveJobs hook added)
- `frontend/src/App.tsx` — MODIFIED (restoration logic added)
- `frontend/src/pages/Import.tsx` — MODIFIED (live game count interval added)

Commits:
- `00e9567` — feat(quick-260319-rj3): add GET /imports/active endpoint for active job restoration
- `9824bf6` — feat(quick-260319-rj3): restore active import jobs on mount + live game count updates

Verification:
- `uv run python -c "from app.routers.imports import router..."` — OK: /active route exists
- `uv run ruff check app/routers/imports.py app/services/import_service.py` — All checks passed
- `npx tsc --noEmit` — No errors
- `npm run build` — Built successfully

## Self-Check: PASSED
