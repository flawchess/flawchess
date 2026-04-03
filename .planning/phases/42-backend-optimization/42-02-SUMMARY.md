---
phase: 42-backend-optimization
plan: "02"
subsystem: backend-api
tags: [pydantic, response-models, type-safety, openapi]
dependency_graph:
  requires: []
  provides: [typed-response-models-for-bare-dict-endpoints]
  affects: [openapi-schema, fastapi-routers]
tech_stack:
  added: []
  patterns: [pydantic-response-model-decorator, typed-return-annotations]
key_files:
  created:
    - app/schemas/auth.py
  modified:
    - app/schemas/users.py
    - app/schemas/imports.py
    - app/routers/users.py
    - app/routers/imports.py
    - app/routers/auth.py
decisions:
  - "New app/schemas/auth.py created alongside existing schemas files — auth router had no schema file"
  - "response= dict variable in google_authorize replaced with direct return of GoogleOAuthAuthorizeResponse"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-03"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 6
---

# Phase 42 Plan 02: Typed Response Models for Bare-Dict Endpoints Summary

Added Pydantic response models and `response_model=` decorators to 4 bare-dict endpoints across 3 routers, enabling typed OpenAPI schema generation and runtime serialization validation.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Create Pydantic response models for 4 bare-dict endpoints | 9185d59 | app/schemas/users.py, app/schemas/imports.py, app/schemas/auth.py |
| 2 | Update routers to use typed response models and fix tests | 3ef40d0 | app/routers/users.py, app/routers/imports.py, app/routers/auth.py |

## What Was Built

Four previously untyped endpoints returning bare `dict` now use proper Pydantic response models:

- `GET /users/games/count` → `GameCountResponse(count: int)`
- `DELETE /imports/games` → `DeleteGamesResponse(deleted_count: int)`
- `GET /auth/google/available` → `GoogleOAuthAvailableResponse(available: bool)`
- `GET /auth/google/authorize` → `GoogleOAuthAuthorizeResponse(authorization_url: str)`

All endpoints have both `response_model=` decorator parameter AND typed return annotation.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- app/schemas/auth.py: FOUND
- app/schemas/users.py contains GameCountResponse: FOUND
- app/schemas/imports.py contains DeleteGamesResponse: FOUND
- Commit 9185d59: FOUND
- Commit 3ef40d0: FOUND
- 485 tests pass, 0 failures
- ruff check: PASSED
- ty check: PASSED
