# Deferred Items — Phase 66

## Pre-existing test isolation failure in tests/test_reclassify.py

**Discovered during:** Phase 66 Plan 01, Task 3 full-suite run
**Status:** Pre-existing (verified via `git stash`: same 8 failures on the branch before Plan 01 edits)
**Scope:** Out of scope for Phase 66

8 tests in `tests/test_reclassify.py` fail with `ForeignKeyViolationError: Key (user_id)=(1) is not present in table "users"` when the file is run in isolation or as part of the full suite. They pass when run after tests that happen to seed user_id=1.

Root cause (surface reading): these tests insert `Game` rows for user_id=1 without calling `ensure_test_user(session, 1)` first. The session-start TRUNCATE (added in Phase 61) wipes the users table, so nothing guarantees user_id=1 exists. Fix is a one-line `await ensure_test_user(session, 1)` in each test's setup (or a shared fixture).

Not touching here because:
- Unrelated to `beta_enabled` / BETA-01 surface
- Risks widening Phase 66 scope; a quick/fast task is the right home for the fix
