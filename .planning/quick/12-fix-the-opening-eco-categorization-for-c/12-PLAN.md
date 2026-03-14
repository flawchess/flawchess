---
phase: quick-12
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/data/openings.tsv
  - app/services/opening_lookup.py
  - app/services/normalization.py
  - tests/test_opening_lookup.py
  - tests/test_normalization.py
autonomous: true
requirements: [QUICK-12]
must_haves:
  truths:
    - "chess.com games get opening_eco and opening_name from longest-prefix match against openings.tsv"
    - "lichess games get opening_eco and opening_name from longest-prefix match against openings.tsv (same approach as chess.com)"
    - "The openings.tsv lookup structure is built once at module load, not per-game"
    - "URL-based ECO extraction functions are removed from normalization.py"
  artifacts:
    - path: "app/data/openings.tsv"
      provides: "Opening database accessible by backend"
    - path: "app/services/opening_lookup.py"
      provides: "Opening lookup service with trie-based longest-prefix matching"
      contains: "find_opening"
    - path: "app/services/normalization.py"
      provides: "Updated normalization using opening_lookup for both platforms"
    - path: "tests/test_opening_lookup.py"
      provides: "Tests for opening lookup module"
    - path: "tests/test_normalization.py"
      provides: "Updated tests reflecting new opening categorization"
  key_links:
    - from: "app/services/normalization.py"
      to: "app/services/opening_lookup.py"
      via: "find_opening(pgn) call in both normalize functions"
      pattern: "find_opening"
    - from: "app/services/opening_lookup.py"
      to: "app/data/openings.tsv"
      via: "TSV loaded at module init into trie"
      pattern: "openings\\.tsv"
---

<objective>
Replace URL-based opening categorization with longest-prefix matching against openings.tsv for both chess.com and lichess games.

Purpose: The current approach extracts ECO codes from chess.com URLs (unreliable, often missing) and uses lichess API opening data (inconsistent with chess.com). A unified approach using a curated openings.tsv database with longest-prefix move matching gives consistent, accurate opening classification across both platforms.

Output: New opening_lookup service, updated normalization for both platforms, removed URL-based extraction functions.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@app/services/normalization.py
@app/services/opening_lookup.py
@tests/test_normalization.py
@frontend/src/lib/openings.ts
</context>

<interfaces>
<!-- Key types and contracts the executor needs -->

From app/services/normalization.py (functions to REMOVE):
```python
def _extract_chesscom_eco(eco_url: str | None) -> str | None:
def _extract_chesscom_opening_name(eco_url: str | None) -> str | None:
```

From app/services/normalization.py (normalize functions that set opening fields):
```python
# chess.com — currently lines 188-209:
opening_eco = _extract_chesscom_eco(eco_url)
# ...
"opening_name": _extract_chesscom_opening_name(eco_url),
"opening_eco": opening_eco,

# lichess — currently lines 293-295:
opening_eco = opening.get("eco") if opening else None
opening_name = opening.get("name") if opening else None
```

From app/models/game.py:
```python
opening_name: Mapped[str | None] = mapped_column(String(200))
opening_eco: Mapped[str | None] = mapped_column(String(10))
```

openings.tsv format (tab-separated, 3641 entries + header):
```
eco	name	pgn
A00	Amar Opening	1. Nh3
B20	Sicilian Defense	1. e4 c5
C50	Italian Game	1. e4 e5 2. Nf3 Nc6 3. Bc4
```

Frontend openings.ts reference (same logic needed in Python):
```typescript
// Strip move numbers: "1. e4 c6 2. d4 d5" -> "e4 c6 d4 d5"
// Longest prefix match: try full move sequence, shorten by 1 move until match found
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create opening_lookup service with trie-based longest-prefix matching</name>
  <files>app/data/openings.tsv, app/services/opening_lookup.py, tests/test_opening_lookup.py</files>
  <behavior>
    - find_opening("1. e4 e5 2. Nf3 Nc6 3. Bc4") returns ("C50", "Italian Game") or longest matching prefix
    - find_opening("1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6") matches the longest known Sicilian prefix
    - find_opening("1. e4") returns ("B00", "King's Pawn Game") or similar A/B code for 1. e4
    - find_opening("") returns (None, None)
    - find_opening(None) returns (None, None)
    - find_opening with PGN containing result markers like "1-0", "0-1", "1/2-1/2", "*" at the end still matches correctly (result markers stripped)
    - find_opening with PGN containing annotations/comments like "{...}" or "(..)" still matches (cleaned before matching)
    - The lookup structure is built once at module import, not per call
  </behavior>
  <action>
1. Copy `frontend/public/openings.tsv` to `app/data/openings.tsv`. This makes the opening database available to the backend without depending on the frontend directory.

2. Create `app/services/opening_lookup.py`:
   - Define a `_normalize_pgn_to_san_sequence(pgn: str) -> list[str]` function that:
     - Strips PGN header tags (lines starting with `[`)
     - Strips move numbers (e.g., "1.", "2.", "12.")
     - Strips result markers ("1-0", "0-1", "1/2-1/2", "*")
     - Strips annotations/comments in curly braces `{...}` and parentheses `(...)`
     - Splits remaining text into individual SAN moves (e.g., ["e4", "e5", "Nf3", "Nc6"])
     - Returns empty list for falsy/empty input
   - Build a dict-based trie at module level:
     - Read `app/data/openings.tsv` using `importlib.resources` or `pathlib.Path(__file__).parent.parent / "data" / "openings.tsv"`
     - For each entry, normalize the PGN to a SAN sequence and insert into trie
     - Trie structure: nested dicts keyed by SAN move, with `_result` key storing `(eco, name)` at terminal nodes
     - When multiple entries share the same move sequence, the last one in the file wins (more specific names tend to come later)
   - Define `find_opening(pgn: str | None) -> tuple[str | None, str | None]`:
     - Returns `(eco_code, opening_name)` or `(None, None)` if no match
     - Normalizes the game PGN to SAN sequence
     - Walks the trie move by move, tracking the last `_result` seen (longest prefix match)
     - Returns the last matched result

3. Create `tests/test_opening_lookup.py`:
   - Test `_normalize_pgn_to_san_sequence` with various PGN formats (with headers, without, with results, with annotations)
   - Test `find_opening` with known openings: Italian Game (1. e4 e5 2. Nf3 Nc6 3. Bc4), Sicilian Defense (1. e4 c5), Queen's Gambit (1. d4 d5 2. c4)
   - Test find_opening with longer game PGN that goes beyond any known opening — should match the longest known prefix
   - Test find_opening("") and find_opening(None) return (None, None)
   - Test find_opening with PGN containing result markers at end
   - Test find_opening with full PGN including headers (like chess.com games have)

NOTE: Use `pathlib.Path` relative to the module file to locate openings.tsv. Do NOT use `importlib.resources` with `__init__.py` or package data — just use `Path(__file__).resolve().parent.parent / "data" / "openings.tsv"`.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run pytest tests/test_opening_lookup.py -x -v</automated>
  </verify>
  <done>opening_lookup.py loads openings.tsv into a trie at module init. find_opening(pgn) returns (eco, name) via longest-prefix match. All tests pass.</done>
</task>

<task type="auto">
  <name>Task 2: Wire opening_lookup into normalization and remove URL-based extraction</name>
  <files>app/services/normalization.py, tests/test_normalization.py</files>
  <action>
1. In `app/services/normalization.py`:
   - Add import: `from app.services.opening_lookup import find_opening`
   - DELETE the `_extract_chesscom_eco` function (lines 98-109)
   - DELETE the `_extract_chesscom_opening_name` function (lines 112-128)
   - DELETE the `_extract_eco_from_pgn` function if it exists (it may have been added by a previous incomplete run)
   - In `normalize_chesscom_game`:
     - Remove the `eco_url = game.get("eco")` and `opening_eco = _extract_chesscom_eco(eco_url)` lines
     - Replace opening field assignment with:
       ```python
       pgn_str = game.get("pgn", "") or ""
       opening_eco, opening_name = find_opening(pgn_str)
       ```
     - Note: `pgn_str` is already defined earlier for computer detection — reuse it or move the extraction earlier. Make sure the variable is defined before both usages.
     - Update the return dict to use the new `opening_eco` and `opening_name` variables (remove `_extract_chesscom_opening_name(eco_url)` call)
   - In `normalize_lichess_game`:
     - Remove the lichess-specific opening extraction:
       ```python
       opening = game.get("opening", {})
       opening_eco = opening.get("eco") if opening else None
       opening_name = opening.get("name") if opening else None
       ```
     - Replace with:
       ```python
       pgn = game.get("pgn", "")
       opening_eco, opening_name = find_opening(pgn)
       ```
     - Note: The `pgn` variable is already defined below for the return dict. Move the opening lookup to use the same variable, or define it once before both usages.
   - Remove the `import re` if it's no longer needed (check if any remaining code uses `re`). Actually, `re` is still used for computer detection in `normalize_chesscom_game`, so keep it.

2. In `tests/test_normalization.py`:
   - DELETE the `TestExtractEcoFromPgn` class (tests for removed function)
   - DELETE the `TestNormalizeChesscomGameEcoFallback` class (tests for removed fallback behavior)
   - DELETE the `TestChesscomEcoExtraction` class (tests for `_extract_chesscom_eco` and `_extract_chesscom_opening_name`)
   - UPDATE `TestNormalizeChesscomGame`:
     - Update `_make_chesscom_game` helper: the `eco_url` parameter is no longer used for opening extraction, but the chess.com API still sends it. Keep the parameter but it won't affect opening_eco/opening_name results. The PGN field now drives opening detection.
     - Update `test_opening_eco_extracted`: Change from URL-based assertion to PGN-based. The test PGN is `'1. e4 e5 2. Nf3 *'` which should match an opening in the TSV. Assert the ECO matches what openings.tsv says for "1. e4 e5 2. Nf3" (likely "C40" or similar — check TSV). If the PGN in the test helper is too short or doesn't match, update it to use a known opening PGN like `'1. e4 e5 2. Nf3 Nc6 3. Bc4 Bc5'` (Italian Game, C50).
     - UPDATE `test_opening_name_from_eco_url` to test that opening_name comes from openings.tsv matching, not from URL slug parsing. Rename to `test_opening_name_from_pgn`.
     - REMOVE `test_opening_name_no_eco_suffix` and `test_opening_name_none_when_no_eco` — replace with:
       - `test_opening_name_from_pgn_match`: Game with known PGN moves gets correct opening_name from TSV
       - `test_opening_none_when_no_moves_in_pgn`: Game with empty/header-only PGN gets opening_name=None and opening_eco=None
   - UPDATE `TestNormalizeLichessGame`:
     - Update `test_opening_eco_and_name`: The test currently expects ECO="B20" and name="Sicilian Defense" from the lichess API `opening` field. Now it should come from PGN matching. Update the test PGN in `_make_lichess_game` to contain Sicilian moves (e.g., `'1. e4 c5 2. Nf3 *'`) and assert opening_eco/opening_name match the TSV entry for that prefix.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run pytest tests/test_normalization.py tests/test_opening_lookup.py -x -v && uv run ruff check app/services/normalization.py app/services/opening_lookup.py</automated>
  </verify>
  <done>Both normalize functions use find_opening(pgn) for opening classification. URL-based and lichess-API-based extraction removed. All tests pass, no lint errors.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/test_normalization.py tests/test_opening_lookup.py -x -v` -- all tests pass
- `uv run ruff check app/services/normalization.py app/services/opening_lookup.py` -- no lint errors
- `uv run ruff format app/services/normalization.py app/services/opening_lookup.py` -- formatted
</verification>

<success_criteria>
- Both chess.com and lichess games get opening_eco and opening_name from openings.tsv longest-prefix matching
- URL-based ECO extraction functions (_extract_chesscom_eco, _extract_chesscom_opening_name) are deleted
- Lichess API opening field is no longer used for opening categorization
- openings.tsv is loaded once at startup into a trie, not re-parsed per game
- All existing tests updated, no regressions, new opening_lookup tests pass
</success_criteria>

<output>
After completion, create `.planning/quick/12-fix-the-opening-eco-categorization-for-c/12-SUMMARY.md`
</output>
