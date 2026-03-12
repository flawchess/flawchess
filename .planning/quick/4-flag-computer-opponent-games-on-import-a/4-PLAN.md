---
phase: quick-4
plan: 4
type: execute
wave: 1
depends_on: []
files_modified:
  - app/models/game.py
  - app/services/normalization.py
  - tests/test_normalization.py
  - alembic/versions/<generated>_add_is_computer_game_and_chesscom_opening_name.py
autonomous: true
requirements: [QUICK-4]

must_haves:
  truths:
    - "Games vs computer opponents are flagged with is_computer_game=True on import"
    - "chess.com games have opening_name populated from the eco URL slug"
    - "Human vs human games have is_computer_game=False"
  artifacts:
    - path: "app/models/game.py"
      provides: "is_computer_game Boolean column"
      contains: "is_computer_game"
    - path: "app/services/normalization.py"
      provides: "Computer detection + chess.com opening name parsing"
      exports: ["normalize_chesscom_game", "normalize_lichess_game"]
    - path: "alembic/versions/*_add_is_computer_game_and_chesscom_opening_name.py"
      provides: "DB migration adding is_computer_game column"
  key_links:
    - from: "app/services/normalization.py"
      to: "app/models/game.py"
      via: "is_computer_game key in returned dict"
      pattern: "is_computer_game"
---

<objective>
Flag games played against computer opponents during import and populate
chess.com opening names from the existing eco URL field.

Purpose: Users need to know which games were vs computers so they can
filter them out of opening analysis (computer games skew human results).
Opening names from chess.com are already available in the eco URL slug
with no extra API calls.

Output: New is_computer_game DB column, computer detection in both platform
normalizers, chess.com opening names derived from existing eco URL.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

Key facts:
- Game model: app/models/game.py — already has opening_name, opening_eco columns
- Normalization: app/services/normalization.py — normalize_chesscom_game sets opening_name=None,
  normalize_lichess_game reads opening.name from API response
- Tests: tests/test_normalization.py — unit tests for both normalizers

chess.com API structure (per player object):
  { "username": "...", "rating": 1500, "result": "win", "is_computer": true }

lichess API structure (per player object in NDJSON):
  { "user": { "name": "...", "title": "BOT" }, "rating": 1500 }

chess.com eco URL: "https://www.chess.com/openings/Kings-Pawn-Opening-C40"
  - Strip known ECO code suffix (letter + 2 digits at end of slug)
  - Replace remaining hyphens with spaces to get opening name
  - e.g. "Kings-Pawn-Opening-C40" -> strip "C40" -> "Kings-Pawn-Opening" -> "Kings Pawn Opening"
  - Handle edge case where slug has no ECO suffix (return slug with hyphens replaced)

Database: PostgreSQL, SQLAlchemy 2.x async + Alembic. Base class maps int -> BIGINT.
Boolean columns use `Mapped[bool]`, server_default for DB-level defaults.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add is_computer_game column to Game model and create Alembic migration</name>
  <files>app/models/game.py, alembic/versions/<timestamp>_add_is_computer_game.py</files>
  <action>
1. In app/models/game.py, add `is_computer_game` field in the "Flags" section (after `rated`):
   ```python
   is_computer_game: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
   ```

2. Generate the migration:
   ```
   uv run alembic revision --autogenerate -m "add is_computer_game to games"
   ```

3. Review the generated migration file — verify it adds a nullable=False Boolean column
   with a server_default of false (Alembic may not auto-add server_default; if missing,
   add `server_default=sa.text("false")` manually to the add_column call so existing rows
   get the correct default without a table rewrite).

4. Apply the migration:
   ```
   uv run alembic upgrade head
   ```
  </action>
  <verify>
    <automated>uv run alembic current 2>&1 | grep "(head)"</automated>
  </verify>
  <done>Migration applied, games table has is_computer_game column, uv run alembic current shows (head)</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Update normalization to detect computer opponents and parse chess.com opening names</name>
  <files>app/services/normalization.py, tests/test_normalization.py</files>
  <behavior>
    chess.com computer detection:
    - Game where white.is_computer=True and user plays black -> is_computer_game=True
    - Game where black.is_computer=True and user plays white -> is_computer_game=True
    - Game where neither player has is_computer=True -> is_computer_game=False
    - is_computer key absent on player object -> treated as False

    chess.com opening name parsing from eco URL:
    - "https://www.chess.com/openings/Kings-Pawn-Opening-C40" -> "Kings Pawn Opening"
    - "https://www.chess.com/openings/Sicilian-Defense" -> "Sicilian Defense" (no ECO suffix)
    - None eco URL -> opening_name=None
    - ECO suffix pattern: letter A-E followed by 2 digits at end of slug segment

    lichess computer detection:
    - Opponent player object has user.title == "BOT" -> is_computer_game=True
    - user.title absent or other value -> is_computer_game=False
    - Comparison is case-insensitive ("bot" == "BOT")
  </behavior>
  <action>
1. In normalization.py, add a helper `_extract_chesscom_opening_name(eco_url: str | None) -> str | None`:
   - Return None if eco_url is None or empty
   - Split URL on "/" and take the last segment (the slug)
   - Use regex to strip a trailing ECO code: `re.sub(r"-[A-E]\d{2}$", "", slug)`
   - Replace remaining hyphens with spaces and strip
   - Return None if result is empty after stripping

2. In `normalize_chesscom_game`:
   - Detect is_computer_game: check `opponent` player object for `is_computer` truthy value
     (opponent is the player who is NOT the user)
   - Change `"opening_name": None` to `"opening_name": _extract_chesscom_opening_name(eco_url)`
   - Add `"is_computer_game": bool(opponent_player.get("is_computer", False))` to the returned dict
     where `opponent_player` is the white or black dict for the non-user player

3. In `normalize_lichess_game`:
   - After determining opponent player dict (white_player or black_player for non-user),
     check `opponent_player.get("user", {}).get("title", "").upper() == "BOT"`
   - Add `"is_computer_game": <computed bool>` to the returned dict

4. In tests/test_normalization.py, add to TestNormalizeChesscomGame:
   - `test_computer_opponent_flagged`: black.is_computer=True, user plays white -> is_computer_game=True
   - `test_computer_opponent_as_black_flagged`: white.is_computer=True, user plays black -> is_computer_game=True
   - `test_human_opponent_not_flagged`: no is_computer field -> is_computer_game=False
   - `test_opening_name_from_eco_url`: eco with C40 suffix -> opening_name="Kings Pawn Opening"
   - `test_opening_name_no_eco_suffix`: eco URL with no ECO code -> opening_name from slug
   - `test_opening_name_none_when_no_eco`: no eco field -> opening_name=None

5. Add to TestNormalizeLichessGame:
   - `test_bot_opponent_flagged`: opponent has title="BOT" -> is_computer_game=True
   - `test_human_opponent_not_flagged`: no title field -> is_computer_game=False
   - `test_bot_title_case_insensitive`: title="bot" -> is_computer_game=True

Note: The _make_chesscom_game and _make_lichess_game helpers in the test file will need
to accept new optional parameters (e.g., opponent_is_computer=False, opponent_title=None)
to support these new test cases cleanly — add those parameters while keeping existing tests unchanged.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run pytest tests/test_normalization.py -x -q</automated>
  </verify>
  <done>
All normalization tests pass including new computer-detection and opening-name tests.
normalize_chesscom_game returns is_computer_game=True when opponent has is_computer=True,
and opening_name derived from eco URL slug. normalize_lichess_game returns is_computer_game=True
when opponent has title="BOT".
  </done>
</task>

</tasks>

<verification>
uv run pytest tests/test_normalization.py -x -q
uv run alembic current
uv run ruff check app/services/normalization.py app/models/game.py
</verification>

<success_criteria>
- games table has is_computer_game column (migration applied, alembic at head)
- chess.com games vs computer opponents get is_computer_game=True
- lichess games vs BOT accounts get is_computer_game=True
- chess.com games get opening_name parsed from eco URL (e.g. "Kings Pawn Opening")
- All normalization unit tests pass
- No ruff lint errors
</success_criteria>

<output>
After completion, create `.planning/quick/4-flag-computer-opponent-games-on-import-a/4-SUMMARY.md`
</output>
