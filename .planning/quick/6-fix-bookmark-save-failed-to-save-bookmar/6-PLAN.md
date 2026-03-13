---
phase: quick
plan: 6
type: execute
wave: 1
depends_on: []
files_modified: [app/schemas/bookmarks.py]
autonomous: true
requirements: [QUICK-6]

must_haves:
  truths:
    - "POST /bookmarks returns 201 with valid BookmarkResponse JSON"
    - "BookmarkResponse.model_validate(orm_bookmark) succeeds when target_hash is int"
  artifacts:
    - path: "app/schemas/bookmarks.py"
      provides: "BookmarkResponse with int-to-str target_hash in model_validator"
      contains: "str(data.target_hash)"
  key_links:
    - from: "app/schemas/bookmarks.py"
      to: "BookmarkResponse.deserialize_moves"
      via: "model_validator converts int target_hash to str before field validation"
      pattern: "str\\(data\\.target_hash\\)"
---

<objective>
Fix BookmarkResponse validation error when creating bookmarks.

Purpose: POST /bookmarks returns 500 because the `deserialize_moves` model_validator passes `target_hash` as int from the ORM object, but the Pydantic field expects str. The `field_serializer` only runs on output, not during validation.

Output: Working bookmark creation that returns 201 with proper JSON response.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@app/schemas/bookmarks.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Fix target_hash int-to-str conversion in deserialize_moves validator</name>
  <files>app/schemas/bookmarks.py, tests/test_bookmark_schema.py</files>
  <behavior>
    - Test 1: BookmarkResponse.model_validate on a mock ORM object with int target_hash succeeds and returns str target_hash
    - Test 2: BookmarkResponse.model_validate on a dict with str target_hash still works (regression check)
  </behavior>
  <action>
In `app/schemas/bookmarks.py`, inside the `deserialize_moves` model_validator, on line 77 where the dict is constructed from ORM attributes, change:

```python
"target_hash": data.target_hash,
```
to:
```python
"target_hash": str(data.target_hash),
```

This converts the int hash from the ORM object to a string before Pydantic field validation runs. The field_serializer on target_hash is redundant after this fix but keep it for safety (it handles any remaining int-to-str cases during serialization).

Create `tests/test_bookmark_schema.py` with tests that validate BookmarkResponse.model_validate works with both ORM-like objects (int target_hash) and dict input (str target_hash).
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run pytest tests/test_bookmark_schema.py -x -v</automated>
  </verify>
  <done>BookmarkResponse.model_validate succeeds with int target_hash from ORM objects; POST /bookmarks no longer returns 500</done>
</task>

</tasks>

<verification>
- `uv run pytest tests/test_bookmark_schema.py -x -v` passes
- `uv run pytest tests/ -x` all existing tests still pass
- `uv run ruff check app/schemas/bookmarks.py` no lint errors
</verification>

<success_criteria>
BookmarkResponse correctly validates ORM Bookmark objects with integer target_hash fields. Creating a bookmark via POST /bookmarks returns 201 with valid JSON.
</success_criteria>

<output>
After completion, create `.planning/quick/6-fix-bookmark-save-failed-to-save-bookmar/6-SUMMARY.md`
</output>
