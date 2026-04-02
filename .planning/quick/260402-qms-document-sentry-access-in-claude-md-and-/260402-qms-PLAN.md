---
phase: quick-260402-qms
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - CLAUDE.md
  - app/main.py
  - frontend/src/instrument.ts
autonomous: true
requirements: []
must_haves:
  truths:
    - "CLAUDE.md documents Sentry dashboard URL, org, project, project ID, and region"
    - "All transient DB connection errors (ConnectionDoesNotExistError, CannotConnectNowError) group into a single Sentry issue"
    - "Frontend AxiosError 500s, timeouts, and network errors group by error type instead of by endpoint"
  artifacts:
    - path: "CLAUDE.md"
      provides: "Sentry access documentation"
      contains: "flawchess.sentry.io"
    - path: "app/main.py"
      provides: "before_send hook for DB error fingerprinting"
      contains: "db-connection-lost"
    - path: "frontend/src/instrument.ts"
      provides: "beforeSend hook for HTTP error fingerprinting"
      contains: "api-server-error"
  key_links:
    - from: "app/main.py"
      to: "sentry_sdk.init"
      via: "before_send parameter"
      pattern: "before_send.*sentry_before_send"
    - from: "frontend/src/instrument.ts"
      to: "Sentry.init"
      via: "beforeSend parameter"
      pattern: "beforeSend"
---

<objective>
Document Sentry access credentials in CLAUDE.md and add custom fingerprinting hooks to both backend and frontend Sentry initialization to group transient infrastructure errors into single issues instead of fragmenting by endpoint/stack trace.

Purpose: Reduce Sentry noise from infrastructure events (DB restarts, network blips) so real application bugs are visible. Currently a single PostgreSQL restart creates 12+ separate Sentry issues.
Output: Updated CLAUDE.md, backend before_send hook, frontend beforeSend hook.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@app/main.py
@frontend/src/instrument.ts
</context>

<tasks>

<task type="auto">
  <name>Task 1: Document Sentry access in CLAUDE.md and add backend before_send fingerprinting</name>
  <files>CLAUDE.md, app/main.py</files>
  <action>
**CLAUDE.md changes:**

Add a new subsection `### Sentry Dashboard` under the existing `## Error Handling & Sentry` section (after the opening paragraph, before `### Backend Rules`). Content:

```markdown
### Sentry Dashboard

- **URL**: https://flawchess.sentry.io
- **Organization**: flawchess
- **Project**: flawchess (ID: 4508610042675280)
- **Region**: de.sentry.io
```

**app/main.py changes:**

1. Add import at top: `from asyncpg.exceptions import ConnectionDoesNotExistError, CannotConnectNowError`

2. Define a `_sentry_before_send` function BEFORE the `sentry_sdk.init()` call. The function must:
   - Extract the exception from `hint.get("exc_info")` (a 3-tuple: type, value, traceback)
   - Check if the exception value is an instance of `ConnectionDoesNotExistError` or `CannotConnectNowError`
   - If not a direct match, walk the `__cause__` chain (SQLAlchemy wraps asyncpg errors in `DBAPIError`) up to 5 levels deep
   - If any exception in the chain matches, set `event["fingerprint"] = ["db-connection-lost"]`
   - Always return the event (never drop it)

3. Add `before_send=_sentry_before_send` to the `sentry_sdk.init()` call.

Type signature: `def _sentry_before_send(event: dict, hint: dict) -> dict`

Use `from __future__ import annotations` if not already present, or use `dict` directly (Python 3.13 supports it natively).
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run ruff check app/main.py && uv run ty check app/main.py && grep -q "db-connection-lost" app/main.py && grep -q "flawchess.sentry.io" CLAUDE.md</automated>
  </verify>
  <done>
  - CLAUDE.md contains Sentry Dashboard subsection with URL, org, project, ID, and region
  - app/main.py has _sentry_before_send function that fingerprints ConnectionDoesNotExistError and CannotConnectNowError (including when wrapped in SQLAlchemy DBAPIError) as "db-connection-lost"
  - sentry_sdk.init() passes before_send=_sentry_before_send
  - ruff and ty pass on app/main.py
  </done>
</task>

<task type="auto">
  <name>Task 2: Add frontend beforeSend fingerprinting for HTTP errors</name>
  <files>frontend/src/instrument.ts</files>
  <action>
Add a `beforeSend` function to the Sentry.init() call in `frontend/src/instrument.ts`.

Define a function `sentryBeforeSend` before the `Sentry.init()` call with signature:
`function sentryBeforeSend(event: Sentry.ErrorEvent, hint: Sentry.EventHint): Sentry.ErrorEvent`

The function should:
1. Extract the original error from `hint.originalException`
2. Check if it's an AxiosError (check for `isAxiosError` property being true, or the `name` property being `"AxiosError"`)
3. Apply fingerprinting rules:
   - If `error.response?.status === 500` -> set `event.fingerprint = ["api-server-error"]`
   - If `error.code === "ECONNABORTED"` (axios timeout code) -> set `event.fingerprint = ["api-timeout"]`
   - If `error.code === "ERR_NETWORK"` (axios network error code) -> set `event.fingerprint = ["api-network-error"]`
4. Always return the event

Add `beforeSend: sentryBeforeSend` to the Sentry.init() options object.

Note: Use the `isAxiosError` property check (duck typing) rather than importing AxiosError — instrument.ts loads before the app and should not import from axios directly. The AxiosError type can be referenced via a local interface or inline type narrowing.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npx tsc --noEmit src/instrument.ts 2>&1 | head -20; grep -q "api-server-error" src/instrument.ts && grep -q "api-timeout" src/instrument.ts && grep -q "api-network-error" src/instrument.ts</automated>
  </verify>
  <done>
  - frontend/src/instrument.ts has sentryBeforeSend function
  - AxiosError with status 500 fingerprinted as "api-server-error"
  - AxiosError timeout fingerprinted as "api-timeout"
  - AxiosError network error fingerprinted as "api-network-error"
  - Sentry.init() passes beforeSend: sentryBeforeSend
  - TypeScript compiles without errors
  </done>
</task>

</tasks>

<verification>
- `uv run ruff check app/main.py` passes
- `uv run ty check app/main.py` passes
- `cd frontend && npx tsc --noEmit` passes (or at minimum `src/instrument.ts`)
- `grep "db-connection-lost" app/main.py` finds the fingerprint
- `grep "api-server-error" frontend/src/instrument.ts` finds the fingerprint
- `grep "flawchess.sentry.io" CLAUDE.md` finds the dashboard URL
</verification>

<success_criteria>
1. CLAUDE.md has a "Sentry Dashboard" subsection with all access details
2. Backend groups all transient DB connection errors into one Sentry issue via custom fingerprint
3. Frontend groups 5xx, timeout, and network errors by type rather than by endpoint
4. All linting and type checking passes
</success_criteria>

<output>
After completion, create `.planning/quick/260402-qms-document-sentry-access-in-claude-md-and-/260402-qms-SUMMARY.md`
</output>
