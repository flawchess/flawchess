---
phase: quick
plan: 260322-kpe
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/normalization.py
  - tests/test_normalization.py
  - CLAUDE.md
  - alembic/versions/YYYYMMDD_fix_time_control_bucket.py
autonomous: true
must_haves:
  truths:
    - "10+0 (600s) games are classified as rapid, not blitz"
    - "Existing games with time_control_str '600' have time_control_bucket updated to 'rapid'"
    - "All boundary tests pass with corrected thresholds"
  artifacts:
    - path: "app/services/normalization.py"
      provides: "Corrected time control bucketing logic"
      contains: "estimated < 600"
    - path: "tests/test_normalization.py"
      provides: "Updated boundary tests"
    - path: "alembic/versions/"
      provides: "Data migration to fix existing games"
  key_links:
    - from: "app/services/normalization.py"
      to: "games.time_control_bucket"
      via: "parse_time_control return value stored at import"
      pattern: "parse_time_control"
---

<objective>
Fix incorrect time_control_bucket assignment where 10+0 (exactly 600 seconds estimated
duration) is classified as blitz instead of rapid. The bug is in `parse_time_control()` using
`<= 600` instead of `< 600`. Also fix existing database rows and update CLAUDE.md thresholds.

Purpose: 10+0 is universally considered rapid in chess. Misclassification affects filtering
and statistics for a common time control.

Output: Corrected bucketing logic, updated tests, data migration, fixed docs.
</objective>

<execution_context>
@~/.claude/get-shit-done/workflows/execute-plan.md
@~/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@app/services/normalization.py
@tests/test_normalization.py
@CLAUDE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix bucketing logic, tests, and CLAUDE.md thresholds</name>
  <files>app/services/normalization.py, tests/test_normalization.py, CLAUDE.md</files>
  <action>
In `app/services/normalization.py` line 62, change `estimated <= 600` to `estimated < 600`
so that exactly 600s becomes rapid instead of blitz. The bullet boundary (`< 180`) is correct
-- 3+0 (180s) being blitz is standard.

Update the docstring in `parse_time_control()` (lines 35-39) to reflect the corrected thresholds:
```
    Thresholds (estimated duration):
        < 180s   -> bullet
        < 600s   -> blitz
        <= 1800s -> rapid
        else     -> classical
```

Also update the docstring example on line 27: `'600+0' -> ('rapid', 600)` (was blitz).

In `tests/test_normalization.py`:
- `test_blitz_no_increment` (line 7-11): Change assertion from `bucket == "blitz"` to
  `bucket == "rapid"` since 600+0 is now rapid. Update test name to `test_rapid_no_increment`
  and docstring accordingly.
- `test_blitz_boundary` (line 66-71): Change assertion from `bucket == "blitz"` to
  `bucket == "rapid"`. Update test name to `test_600_is_rapid` with docstring
  "Exactly 600s -> rapid (10+0 is standard rapid)."
- Add a new test `test_599_is_blitz`: asserts that `parse_time_control("599+0")` returns
  `("blitz", 599)` to verify the boundary from below.

In `CLAUDE.md`, find the line with time control bucketing thresholds
(`<=180s = bullet, <=600s = blitz, <=1800s = rapid`) and update to:
`<180s = bullet, <600s = blitz, <=1800s = rapid, else classical`
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run pytest tests/test_normalization.py -x -v</automated>
  </verify>
  <done>parse_time_control("600+0") returns ("rapid", 600). All boundary tests pass. CLAUDE.md thresholds match code.</done>
</task>

<task type="auto">
  <name>Task 2: Data migration to fix existing games with wrong bucket</name>
  <files>alembic/versions/YYYYMMDD_fix_time_control_bucket.py</files>
  <action>
Create a new Alembic migration (use `uv run alembic revision -m "fix time_control_bucket for 600s games"`)
that updates existing rows in the `games` table.

The migration should use raw SQL (via `op.execute`) to recalculate time_control_bucket for
affected rows. The logic:

In `upgrade()`:
```python
# Fix games where time_control_str is exactly '600' (10+0, no increment shown)
# These were incorrectly bucketed as 'blitz' but should be 'rapid'
op.execute(
    "UPDATE games SET time_control_bucket = 'rapid' "
    "WHERE time_control_str = '600' AND time_control_bucket = 'blitz'"
)
```

In `downgrade()`:
```python
# Revert: set them back to blitz (original incorrect behavior)
op.execute(
    "UPDATE games SET time_control_bucket = 'blitz' "
    "WHERE time_control_str = '600' AND time_control_bucket = 'rapid'"
)
```

Note: Only `time_control_str = '600'` is affected because `_normalize_tc_str` strips the
`+0` suffix. No other time_control_str values produce exactly 600 estimated seconds
(e.g., 540+1 = 580, 560+1 = 600 would have tc_str '560+1' but that also needs fixing).

Actually, we need to handle ALL cases where estimated duration equals exactly 600. The
estimated formula is `base + increment * 40`. So affected tc_str values are those where
`base + increment * 40 = 600`. Examples: '600' (600+0=600), '560+1' (560+40=600),
'520+2' (520+80=600), '480+3' (480+120=600), '440+4', '400+5', '360+6', '320+7',
'280+8', '240+9', '200+10'.

Use a more robust approach:
```python
# All time_control_str patterns where estimated = base + increment*40 = 600
# These were blitz under old logic (<=600) but should be rapid under new logic (<600)
affected_patterns = [
    "600",      # 600+0
    "560+1",    # 560+40=600
    "520+2",    # 520+80=600
    "480+3",    # 480+120=600
    "440+4",    # 440+160=600 (not realistic but correct)
    "400+5",    # 400+200=600
    "360+6",    # 360+240=600
    "320+7",    # 320+280=600
    "280+8",    # 280+320=600
    "240+9",    # 240+360=600
    "200+10",   # 200+400=600
]
placeholders = ", ".join(f"'{p}'" for p in affected_patterns)
op.execute(
    f"UPDATE games SET time_control_bucket = 'rapid' "
    f"WHERE time_control_str IN ({placeholders}) AND time_control_bucket = 'blitz'"
)
```

Use the same list reversed in `downgrade()`.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run alembic upgrade head</automated>
  </verify>
  <done>Migration runs without error. Any existing games with exactly 600s estimated duration now have time_control_bucket = 'rapid'.</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/test_normalization.py -x -v` -- all time control tests pass
- `uv run alembic upgrade head` -- migration applies cleanly
- `uv run ruff check app/services/normalization.py tests/test_normalization.py` -- no lint issues
</verification>

<success_criteria>
- parse_time_control("600+0") returns ("rapid", 600)
- parse_time_control("599+0") returns ("blitz", 599)
- parse_time_control("180+0") returns ("blitz", 180) (unchanged)
- All existing tests pass (with updated assertions)
- Data migration updates affected rows in production
- CLAUDE.md thresholds are accurate
</success_criteria>

<output>
After completion, create `.planning/quick/260322-kpe-fix-wrong-time-control-bucket-assignment/260322-kpe-SUMMARY.md`
</output>
