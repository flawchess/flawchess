---
phase: quick-260402-qms
plan: 01
subsystem: observability
tags: [sentry, error-tracking, fingerprinting, documentation]
dependency_graph:
  requires: []
  provides: [sentry-fingerprinting, sentry-access-docs]
  affects: [app/main.py, frontend/src/instrument.ts, CLAUDE.md]
tech_stack:
  added: []
  patterns: [before_send-fingerprinting, beforeSend-fingerprinting, duck-typed-axios-detection]
key_files:
  created: []
  modified:
    - CLAUDE.md
    - app/main.py
    - frontend/src/instrument.ts
decisions:
  - "Duck-typed AxiosLikeError interface in instrument.ts rather than importing axios — instrument.ts loads before the app bundle"
  - "Walk __cause__ chain up to 5 levels for DB errors — SQLAlchemy wraps asyncpg errors in DBAPIError"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-02T17:14:42Z"
  tasks_completed: 2
  files_modified: 3
---

# Phase quick-260402-qms Plan 01: Document Sentry Access and Add Error Fingerprinting Summary

**One-liner:** Sentry dashboard credentials added to CLAUDE.md; DB transient errors and frontend HTTP errors now group into single issues via custom fingerprint hooks.

## What Was Built

### Task 1: CLAUDE.md documentation and backend before_send hook

Added a `### Sentry Dashboard` subsection to CLAUDE.md under `## Error Handling & Sentry` containing the dashboard URL, organization slug, project name and ID, and region.

In `app/main.py`:
- Imported `ConnectionDoesNotExistError` and `CannotConnectNowError` from `asyncpg.exceptions`
- Defined `_sentry_before_send(event, hint)` that walks the `__cause__` chain up to 5 levels to detect asyncpg transient errors even when wrapped by SQLAlchemy's `DBAPIError`, setting `event["fingerprint"] = ["db-connection-lost"]`
- Wired `before_send=_sentry_before_send` into `sentry_sdk.init()`

### Task 2: Frontend beforeSend fingerprinting

In `frontend/src/instrument.ts`:
- Defined a duck-typed `AxiosLikeError` interface (checks `isAxiosError === true`) to avoid importing axios in the early-loading instrumentation file
- Defined `sentryBeforeSend` that applies fingerprints: `"api-server-error"` (500), `"api-timeout"` (ECONNABORTED), `"api-network-error"` (ERR_NETWORK)
- Wired `beforeSend: sentryBeforeSend` into `Sentry.init()`

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | bbfb1c1 | feat(quick-260402-qms-01): document Sentry access and add DB error fingerprinting |
| 2 | 276384e | feat(quick-260402-qms-01): add frontend Sentry beforeSend fingerprinting for HTTP errors |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- CLAUDE.md contains "flawchess.sentry.io": confirmed
- app/main.py contains "db-connection-lost": confirmed
- frontend/src/instrument.ts contains "api-server-error", "api-timeout", "api-network-error": confirmed
- ruff check app/main.py: passed
- ty check app/main.py: passed
- npx tsc --noEmit (full project): passed
- Commits bbfb1c1 and 276384e: exist in git log
