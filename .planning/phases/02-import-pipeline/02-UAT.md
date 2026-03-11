---
status: complete
phase: 02-import-pipeline
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md]
started: 2026-03-11T14:00:00Z
updated: 2026-03-11T14:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server. Run `uv run alembic upgrade head` then `uv run uvicorn app.main:app --reload`. Server boots without errors, migrations complete, and GET http://localhost:8000/docs returns the Swagger UI page.
result: pass

### 2. Start Import via API
expected: POST http://localhost:8000/imports with JSON body `{"platform": "chess.com", "username": "tomatospeaksforitself"}`. Returns 201 with JSON containing `job_id` (UUID string) and `status: "pending"`.
result: issue
reported: "POST returns 201 but background job immediately crashes with JSONDecodeError when chess.com returns 410 Gone for email-format usernames. Client only handles 404, not other non-200 status codes."
severity: major

### 3. Poll Import Progress
expected: GET http://localhost:8000/imports/{job_id} returns JSON with `status`, `games_fetched`, and `games_imported` fields. Status progresses from "pending" to "in_progress" to "completed".
result: pass

### 4. Duplicate Import Prevention
expected: While import is running, POST /imports again with same platform and username returns 200 (not 201) with same job_id — no duplicate job created.
result: pass

### 5. Import Completion
expected: After import finishes, GET /imports/{job_id} shows `status: "completed"` with `games_fetched` and `games_imported` showing counts > 0.
result: pass

## Summary

total: 5
passed: 4
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Import handles invalid/email usernames gracefully with proper error response"
  status: failed
  reason: "User reported: POST returns 201 but background job crashes with JSONDecodeError when chess.com returns 410 Gone for email-format usernames"
  severity: major
  test: 2
  root_cause: "chesscom_client.py line 77 calls .json() on non-200 responses without checking status code first. Only 404 is handled; 410, 403, 500 etc. fall through to json parsing on empty/HTML body"
  artifacts:
    - path: "app/services/chesscom_client.py"
      issue: "No status code check before .json() on archives response (line 77)"
  missing:
    - "Add raise/error handling for non-200 responses after the 404 check"
    - "Consider similar hardening in individual archive fetches (line 96)"
  debug_session: ""
