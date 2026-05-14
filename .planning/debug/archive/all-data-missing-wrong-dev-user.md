---
status: diagnosed
trigger: "Games page says 'No games imported yet' despite games existing in DB, bookmarks not displayed, usernames not displayed"
created: 2026-03-14T00:00:00Z
updated: 2026-03-14T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - dev auth bypass returns wrong user (test user with no data)
test: Queried DB directly, verified dev bypass returns user 2 instead of user 1
expecting: n/a - root cause confirmed
next_action: Report findings

## Symptoms

expected: Dashboard shows 5034 imported games, 8 bookmarks, usernames in import modal
actual: "No games imported yet", empty bookmarks, null usernames
errors: None - no errors thrown, just empty data
reproduction: Navigate to dashboard in dev mode
started: After Phase 09 tests were run against the dev database

## Eliminated

- hypothesis: Backend endpoints return wrong data
  evidence: Backend endpoints work correctly but return data for the WRONG USER (user 2 has 0 games, 0 bookmarks)
  timestamp: 2026-03-14

- hypothesis: Frontend code bug
  evidence: Frontend correctly displays what the backend returns - the problem is the backend returns data for a test user
  timestamp: 2026-03-14

## Evidence

- timestamp: 2026-03-14
  checked: Database users table
  found: 12 users exist. User 1 (aimfeld80@gmail.com) has 5034 games. Users 2-12 are test users with @example.com emails and zero games.
  implication: Test data leaked into dev database

- timestamp: 2026-03-14
  checked: _dev_bypass_user query (SELECT ... WHERE is_active = true LIMIT 1)
  found: Returns user 2 (alice_f4e5298d@example.com) instead of user 1
  implication: Without ORDER BY, PostgreSQL returns whichever row it finds first in the heap - after test user insertion, user 2 comes first

- timestamp: 2026-03-14
  checked: Games count for user 2
  found: 0 games, 0 bookmarks, null usernames
  implication: All three symptoms explained by wrong user being selected

- timestamp: 2026-03-14
  checked: Test files (test_users_router.py, test_auth.py, test_stats_router.py, test_imports_router.py)
  found: Tests use httpx.ASGITransport to call /auth/register directly, creating real users that persist (not using the db_session rollback fixture)
  implication: Running tests pollutes the dev database with test users

## Resolution

root_cause: Two interacting bugs - (1) _dev_bypass_user in app/users.py uses LIMIT 1 without ORDER BY id, making it non-deterministic; (2) Integration tests register users via the real FastAPI app without cleanup, polluting the dev database. After tests run, the dev bypass returns a test user (id=2) with no data instead of the real user (id=1).
fix:
verification:
files_changed: []
