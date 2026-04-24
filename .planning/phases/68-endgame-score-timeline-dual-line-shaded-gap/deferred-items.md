# Deferred Items — Phase 68

Items discovered during Phase 68 execution that are out of scope and deferred.

## Pre-existing test failure (not introduced by Phase 68)

- **`tests/test_reclassify.py::TestBackfillGame::test_backfill_updates_null_material_count_to_nonnull`**
  - Fails with `IntegrityError: Key (user_id)=(1) is not present in table "users"` — DB fixture ordering issue, games row inserted before user row commits.
  - Confirmed pre-existing on the Phase 68 wave-3 base commit (`71b583e`) by running the test against a clean checkout.
  - Plan 01 SUMMARY already excludes this file from verification runs (`--ignore=tests/test_reclassify.py`); CLAUDE.md commands list does not include it in the default CI path either.
  - Out of scope for Phase 68; fix is a test-fixture concern unrelated to the score-timeline rework.
