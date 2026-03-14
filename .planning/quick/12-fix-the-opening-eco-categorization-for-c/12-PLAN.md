---
phase: quick-12
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/normalization.py
  - tests/test_normalization.py
  - scripts/backfill_eco.py
autonomous: true
requirements: [QUICK-12]
must_haves:
  truths:
    - "chess.com games get opening_eco extracted from PGN [ECO] header when URL has no ECO code"
    - "chess.com games with ECO in URL still extract ECO from URL (existing behavior preserved)"
    - "Existing imported games with null opening_eco get backfilled from their stored PGN"
  artifacts:
    - path: "app/services/normalization.py"
      provides: "_extract_eco_from_pgn helper + PGN fallback in normalize_chesscom_game"
      contains: "_extract_eco_from_pgn"
    - path: "tests/test_normalization.py"
      provides: "Tests for PGN-based ECO extraction and fallback behavior"
    - path: "scripts/backfill_eco.py"
      provides: "One-time script to backfill opening_eco for existing chess.com games"
  key_links:
    - from: "app/services/normalization.py"
      to: "normalize_chesscom_game"
      via: "_extract_eco_from_pgn fallback when _extract_chesscom_eco returns None"
      pattern: "_extract_eco_from_pgn.*pgn"
---

<objective>
Fix chess.com opening_eco being null for all imported games by extracting ECO from PGN headers as fallback.

Purpose: chess.com API eco URL field often lacks an ECO code in the URL slug. However, chess.com PGN headers reliably contain `[ECO "C40"]` tags. The current code only tries URL-based extraction. Adding PGN-based extraction as a fallback will populate opening_eco for the vast majority of chess.com games.

Output: Updated normalization with PGN fallback, tests, and a backfill script for existing games.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@app/services/normalization.py
@tests/test_normalization.py
</context>

<interfaces>
<!-- Key functions the executor needs -->

From app/services/normalization.py:
```python
def _extract_chesscom_eco(eco_url: str | None) -> str | None:
    """Extract ECO code from chess.com opening URL. Returns None if no ECO in URL."""

def normalize_chesscom_game(game: dict, username: str, user_id: int) -> dict | None:
    """Normalize chess.com game. Currently: opening_eco = _extract_chesscom_eco(eco_url)"""
```

From app/models/game.py:
```python
opening_eco: Mapped[str | None] = mapped_column(String(10))
```

chess.com PGN header format (present in most games):
```
[ECO "C40"]
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add PGN-based ECO extraction with fallback in normalize_chesscom_game</name>
  <files>app/services/normalization.py, tests/test_normalization.py</files>
  <behavior>
    - _extract_eco_from_pgn('[ECO "C40"]\n1. e4 e5') returns "C40"
    - _extract_eco_from_pgn('[ECO "B20"]\n1. e4 c5') returns "B20"
    - _extract_eco_from_pgn('[Event "Live Chess"]\n1. e4 e5') returns None (no ECO header)
    - _extract_eco_from_pgn("") returns None
    - _extract_eco_from_pgn(None) returns None
    - normalize_chesscom_game with eco URL containing ECO code still returns that ECO (URL takes priority)
    - normalize_chesscom_game with eco URL lacking ECO code but PGN containing [ECO "B20"] returns "B20"
    - normalize_chesscom_game with no eco URL and PGN containing [ECO "A45"] returns "A45"
    - normalize_chesscom_game with no eco URL and PGN without ECO header returns None
  </behavior>
  <action>
1. In `app/services/normalization.py`, add a new helper function `_extract_eco_from_pgn(pgn: str | None) -> str | None` that:
   - Returns None if pgn is falsy
   - Uses `re.search(r'\[ECO\s+"([A-E]\d{2})"\]', pgn)` to find the ECO header
   - Returns the captured group if found, None otherwise

2. In `normalize_chesscom_game`, change the ECO extraction logic (around line 188-189) from:
   ```python
   opening_eco = _extract_chesscom_eco(eco_url)
   ```
   to:
   ```python
   opening_eco = _extract_chesscom_eco(eco_url)
   if opening_eco is None:
       opening_eco = _extract_eco_from_pgn(game.get("pgn", ""))
   ```
   The PGN is already available in the `game` dict — no additional data fetching needed.

3. In `tests/test_normalization.py`, add:
   - A new test class `TestExtractEcoFromPgn` with tests for the direct helper function (standard ECO header, missing header, empty/None input, ECO code at different positions in PGN)
   - In `TestNormalizeChesscomGame`, add tests for the fallback behavior:
     - `test_opening_eco_fallback_from_pgn`: eco URL with no ECO code (e.g. "https://www.chess.com/openings/Sicilian-Defense") but PGN has `[ECO "B20"]` -> opening_eco="B20"
     - `test_opening_eco_url_takes_priority`: eco URL with ECO code still uses URL-based extraction (existing behavior)
     - `test_opening_eco_none_when_no_source`: no eco URL and PGN without ECO header -> None
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run pytest tests/test_normalization.py -x -v</automated>
  </verify>
  <done>_extract_eco_from_pgn helper exists and is tested. normalize_chesscom_game falls back to PGN ECO extraction when URL extraction returns None. All existing and new tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Create backfill script for existing chess.com games with null opening_eco</name>
  <files>scripts/backfill_eco.py</files>
  <action>
1. Create `scripts/backfill_eco.py` — a standalone async script that:
   - Imports `async_session_maker` from `app.core.database` and `_extract_eco_from_pgn` from `app.services.normalization`
   - Queries all chess.com games where `opening_eco IS NULL AND pgn IS NOT NULL`
   - For each game, calls `_extract_eco_from_pgn(game.pgn)` to extract ECO from PGN header
   - Updates games in batches of 100 using `UPDATE games SET opening_eco = :eco WHERE id = :id`
   - Prints progress: total games found, games updated, games still null (PGN has no ECO header)
   - Uses `asyncio.run()` as entry point

2. Script structure:
   ```python
   import asyncio
   import sys
   sys.path.insert(0, ".")  # Ensure app imports work from project root

   from sqlalchemy import select, update
   from app.core.database import async_session_maker
   from app.models.game import Game
   from app.services.normalization import _extract_eco_from_pgn

   async def backfill():
       async with async_session_maker() as session:
           # Select chess.com games with null opening_eco
           stmt = select(Game.id, Game.pgn).where(
               Game.platform == "chess.com",
               Game.opening_eco.is_(None),
               Game.pgn.isnot(None),
           )
           result = await session.execute(stmt)
           rows = result.fetchall()
           print(f"Found {len(rows)} chess.com games with null opening_eco")

           updated = 0
           for game_id, pgn in rows:
               eco = _extract_eco_from_pgn(pgn)
               if eco:
                   await session.execute(
                       update(Game).where(Game.id == game_id).values(opening_eco=eco)
                   )
                   updated += 1

           await session.commit()
           print(f"Updated {updated}/{len(rows)} games with ECO from PGN")
           print(f"Remaining null: {len(rows) - updated} (no ECO in PGN header)")

   if __name__ == "__main__":
       asyncio.run(backfill())
   ```

3. Make the script runnable via `uv run python scripts/backfill_eco.py`
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && python -c "import ast; ast.parse(open('scripts/backfill_eco.py').read()); print('Script parses OK')"</automated>
  </verify>
  <done>Backfill script exists at scripts/backfill_eco.py, parses correctly, and can be run with `uv run python scripts/backfill_eco.py` to update existing games. User runs it manually after deployment.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/test_normalization.py -x -v` — all normalization tests pass including new PGN ECO tests
- `uv run ruff check app/services/normalization.py scripts/backfill_eco.py` — no lint errors
</verification>

<success_criteria>
- New chess.com game imports populate opening_eco from PGN header when URL extraction returns None
- Existing URL-based extraction still works (no regression)
- Backfill script ready to run for existing games
- All tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/12-fix-the-opening-eco-categorization-for-c/12-SUMMARY.md`
</output>
