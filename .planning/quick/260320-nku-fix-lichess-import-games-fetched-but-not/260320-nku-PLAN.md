---
phase: quick
plan: 260320-nku
type: execute
wave: 1
depends_on: []
files_modified:
  - alembic/versions/YYYYMMDD_HHMMSS_make_game_unique_constraint_per_user.py
  - app/models/game.py
  - app/repositories/game_repository.py
  - tests/test_game_repository.py
autonomous: true
must_haves:
  truths:
    - "Two different users can import the same lichess username and both see their games"
    - "Same user importing same game twice still deduplicates (no double-counting)"
    - "Existing single-user data is unaffected after migration"
  artifacts:
    - path: "app/models/game.py"
      provides: "Updated UniqueConstraint including user_id"
      contains: "uq_games_user_platform_game_id"
    - path: "app/repositories/game_repository.py"
      provides: "ON CONFLICT referencing new constraint name"
      contains: "uq_games_user_platform_game_id"
    - path: "alembic/versions/*make_game_unique_constraint_per_user*"
      provides: "Migration dropping old constraint and creating new one"
  key_links:
    - from: "app/repositories/game_repository.py"
      to: "app/models/game.py"
      via: "constraint name in on_conflict_do_nothing"
      pattern: "on_conflict_do_nothing.*uq_games_user_platform_game_id"
---

<objective>
Fix bug where importing a lichess username already imported by another user results in 0 games saved. The root cause is the `games` table unique constraint `(platform, platform_game_id)` is global instead of per-user. Change it to `(user_id, platform, platform_game_id)`.

Purpose: Multi-user correctness -- each user must have their own copy of games they import.
Output: Migration, updated model, updated repository, updated tests.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@app/models/game.py
@app/repositories/game_repository.py
@tests/test_game_repository.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add multi-user duplicate test, then fix constraint and repository</name>
  <files>tests/test_game_repository.py, app/models/game.py, app/repositories/game_repository.py</files>
  <behavior>
    - Test: Two users inserting the same platform_game_id both get IDs back (not deduplicated across users)
    - Test: Same user inserting the same platform_game_id twice still deduplicates (returns 0 on second insert)
  </behavior>
  <action>
    RED: Add `test_different_users_can_import_same_game` to `TestBulkInsertGames` in `tests/test_game_repository.py`:
    - User 1 inserts game with platform_game_id "shared-game-123" -> gets 1 ID
    - User 2 inserts same platform_game_id "shared-game-123" -> gets 1 ID (NOT 0)
    - Use `_make_game_row("shared-game-123", user_id=1)` and `_make_game_row("shared-game-123", user_id=2)`

    Also add `test_same_user_duplicate_still_skipped` to confirm existing dedup behavior holds with new constraint:
    - User 1 inserts game "dup-game-456" -> gets 1 ID
    - User 1 inserts same game "dup-game-456" again -> gets 0 IDs

    Run tests -- both new tests should FAIL (first one because global constraint blocks user 2).

    GREEN:
    1. In `app/models/game.py`, change `__table_args__`:
       - From: `UniqueConstraint("platform", "platform_game_id", name="uq_games_platform_game_id")`
       - To: `UniqueConstraint("user_id", "platform", "platform_game_id", name="uq_games_user_platform_game_id")`

    2. In `app/repositories/game_repository.py`, update `bulk_insert_games`:
       - From: `.on_conflict_do_nothing(constraint="uq_games_platform_game_id")`
       - To: `.on_conflict_do_nothing(constraint="uq_games_user_platform_game_id")`

    Run tests -- all tests should pass (both new and existing).
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run pytest tests/test_game_repository.py -x -v</automated>
  </verify>
  <done>All tests pass including new multi-user test. Model and repository reference new constraint name.</done>
</task>

<task type="auto">
  <name>Task 2: Create Alembic migration for constraint change</name>
  <files>alembic/versions/YYYYMMDD_HHMMSS_make_game_unique_constraint_per_user.py</files>
  <action>
    Generate an Alembic migration:
    ```
    cd /home/aimfeld/Projects/Python/chessalytics && uv run alembic revision --autogenerate -m "make game unique constraint per user"
    ```

    Review the generated migration. It should contain:
    - `upgrade()`: Drop constraint `uq_games_platform_game_id`, create constraint `uq_games_user_platform_game_id` on `(user_id, platform, platform_game_id)`
    - `downgrade()`: Reverse (drop new, recreate old)

    If autogenerate doesn't detect the change correctly (constraint renames can be tricky), write the migration manually:
    ```python
    def upgrade():
        op.drop_constraint("uq_games_platform_game_id", "games", type_="unique")
        op.create_unique_constraint("uq_games_user_platform_game_id", "games", ["user_id", "platform", "platform_game_id"])

    def downgrade():
        op.drop_constraint("uq_games_user_platform_game_id", "games", type_="unique")
        op.create_unique_constraint("uq_games_platform_game_id", "games", ["platform", "platform_game_id"])
    ```

    Run the migration against the dev database:
    ```
    uv run alembic upgrade head
    ```

    Then re-run all tests to confirm everything works end-to-end with the actual DB schema.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run alembic upgrade head && uv run pytest tests/test_game_repository.py -x -v</automated>
  </verify>
  <done>Migration applies cleanly. All repository tests pass against the migrated schema.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/test_game_repository.py -x -v` -- all tests pass
- `uv run alembic upgrade head` -- migration applies without errors
- `uv run ruff check app/models/game.py app/repositories/game_repository.py` -- no lint issues
</verification>

<success_criteria>
- Two different users can import the same platform_game_id and both get their games stored
- Same user importing the same game twice is still deduplicated
- All existing tests continue to pass
- Alembic migration is clean and reversible
</success_criteria>

<output>
After completion, create `.planning/quick/260320-nku-fix-lichess-import-games-fetched-but-not/260320-nku-SUMMARY.md`
</output>
