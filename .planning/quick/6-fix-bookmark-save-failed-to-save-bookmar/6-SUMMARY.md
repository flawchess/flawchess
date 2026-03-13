---
phase: quick
plan: 6
subsystem: backend/schemas
tags: [bugfix, pydantic, bookmarks]
key-files:
  modified:
    - app/schemas/bookmarks.py
  created:
    - tests/test_bookmark_schema.py
decisions:
  - "Keep field_serializer on target_hash as safety net for any remaining int-to-str serialization cases"
metrics:
  duration: 5min
  completed: "2026-03-13"
  tasks: 1
  files: 2
---

# Quick Task 6: Fix BookmarkResponse int target_hash validation error

**One-liner:** Fixed Pydantic validation error in BookmarkResponse by converting ORM int target_hash to str inside the model_validator before field validation runs.

## What Was Done

POST /bookmarks was returning 500 because `BookmarkResponse.deserialize_moves` (a `mode="before"` model_validator) was passing `data.target_hash` as an int from the SQLAlchemy ORM object, but the `target_hash` field is declared as `str`. The `field_serializer` only executes during JSON serialization output, not during `model_validate()` — so the int reached field validation and raised `ValidationError: Input should be a valid string`.

**Fix:** In `app/schemas/bookmarks.py` line 77, changed `"target_hash": data.target_hash` to `"target_hash": str(data.target_hash)` inside the `deserialize_moves` validator's dict construction.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for int target_hash validation | 29c5e77 | tests/test_bookmark_schema.py |
| 1 (GREEN) | Fix target_hash int-to-str conversion | a96293b | app/schemas/bookmarks.py |

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `uv run pytest tests/test_bookmark_schema.py -x -v` — 7 tests pass
- `uv run pytest tests/ -x` — 198 tests pass
- `uv run ruff check app/schemas/bookmarks.py` — no lint errors

## Self-Check: PASSED

- `/home/aimfeld/Projects/Python/chessalytics/app/schemas/bookmarks.py` — FOUND, contains `str(data.target_hash)`
- `/home/aimfeld/Projects/Python/chessalytics/tests/test_bookmark_schema.py` — FOUND, 7 tests
- Commit 29c5e77 — FOUND
- Commit a96293b — FOUND
