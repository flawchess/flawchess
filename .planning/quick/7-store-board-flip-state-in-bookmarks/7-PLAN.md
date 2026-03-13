---
phase: quick-7
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - app/models/bookmark.py
  - app/schemas/bookmarks.py
  - frontend/src/types/bookmarks.ts
  - frontend/src/pages/Dashboard.tsx
  - frontend/src/components/bookmarks/BookmarkCard.tsx
  - frontend/src/components/board/MiniBoard.tsx
  - alembic/versions/NEW_add_is_flipped_to_bookmarks.py
  - tests/test_bookmark_schema.py
autonomous: true
requirements: [quick-7]
must_haves:
  truths:
    - "Bookmark stores whether the board was flipped when created"
    - "BookmarkCard mini-board shows position flipped when bookmark was saved with flipped board"
    - "Loading a bookmark restores the flip state on the dashboard"
  artifacts:
    - path: "app/models/bookmark.py"
      provides: "is_flipped column on Bookmark"
      contains: "is_flipped"
    - path: "app/schemas/bookmarks.py"
      provides: "is_flipped in BookmarkCreate and BookmarkResponse"
    - path: "frontend/src/types/bookmarks.ts"
      provides: "is_flipped field in TS types"
    - path: "frontend/src/pages/Dashboard.tsx"
      provides: "boardFlipped passed to bookmark save, restored on bookmark load"
    - path: "frontend/src/components/bookmarks/BookmarkCard.tsx"
      provides: "is_flipped passed to navigate state and MiniBoard"
  key_links:
    - from: "Dashboard.tsx handleBookmarkSave"
      to: "BookmarkCreate.is_flipped"
      via: "boardFlipped state included in create payload"
    - from: "BookmarkCard.tsx handleLoad"
      to: "Dashboard.tsx useEffect"
      via: "navigate state includes is_flipped, useEffect reads it and calls setBoardFlipped"
    - from: "BookmarkCard.tsx"
      to: "MiniBoard"
      via: "passes flipped prop based on bookmark.is_flipped"
---

<objective>
Store the board flip state in bookmarks so that when a user creates a bookmark with a flipped board, the mini-board in the bookmark card shows the position flipped, and loading the bookmark restores the flip state.

Purpose: When studying positions as black, users flip the board. Bookmarks should remember this orientation.
Output: Updated backend model/schema, migration, and frontend components.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@app/models/bookmark.py
@app/schemas/bookmarks.py
@frontend/src/types/bookmarks.ts
@frontend/src/pages/Dashboard.tsx
@frontend/src/components/bookmarks/BookmarkCard.tsx
@frontend/src/components/board/MiniBoard.tsx
@tests/test_bookmark_schema.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add is_flipped to backend model, schemas, and migration</name>
  <files>app/models/bookmark.py, app/schemas/bookmarks.py, tests/test_bookmark_schema.py, alembic/versions/NEW_add_is_flipped_to_bookmarks.py</files>
  <action>
1. In `app/models/bookmark.py`, add column:
   `is_flipped: Mapped[bool] = mapped_column(nullable=False, default=False, server_default="false")`

2. In `app/schemas/bookmarks.py`:
   - Add `is_flipped: bool = False` to `BookmarkCreate`
   - Add `is_flipped: bool` to `BookmarkResponse` (after `match_side`)
   - In `BookmarkResponse.deserialize_moves` model_validator, add `"is_flipped": data.is_flipped` to the ORM-object dict return

3. Generate Alembic migration:
   `uv run alembic revision --autogenerate -m "add is_flipped to bookmarks"`
   Then run: `uv run alembic upgrade head`

4. Update `tests/test_bookmark_schema.py` to include `is_flipped` in test data where needed (add it to any BookmarkCreate/BookmarkResponse test dicts).
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics && uv run pytest tests/test_bookmark_schema.py -x && uv run ruff check app/models/bookmark.py app/schemas/bookmarks.py</automated>
  </verify>
  <done>Bookmark model has is_flipped column, schemas include it, migration applied, tests pass</done>
</task>

<task type="auto">
  <name>Task 2: Wire is_flipped through frontend create, display, and load</name>
  <files>frontend/src/types/bookmarks.ts, frontend/src/pages/Dashboard.tsx, frontend/src/components/bookmarks/BookmarkCard.tsx, frontend/src/components/board/MiniBoard.tsx</files>
  <action>
1. In `frontend/src/types/bookmarks.ts`:
   - Add `is_flipped: boolean;` to `BookmarkResponse` (after `match_side`)
   - Add `is_flipped: boolean;` to `BookmarkCreate` (after `match_side`)

2. In `frontend/src/pages/Dashboard.tsx`:
   - In `handleBookmarkSave`, add `is_flipped: boardFlipped` to the `data` object passed to `createBookmark.mutateAsync`
   - In the `useEffect` that hydrates from `location.state`, add `is_flipped` to the bookmark type, read `bkm.is_flipped`, and call `setBoardFlipped(bkm.is_flipped)` (note: `is_flipped` may be undefined for old bookmarks without the field, so default to false: `setBoardFlipped(bkm.is_flipped ?? false)`)

3. In `frontend/src/components/bookmarks/BookmarkCard.tsx`:
   - In `handleLoad`, add `is_flipped: bookmark.is_flipped` to the `bookmark` object in navigate state
   - Pass `flipped={bookmark.is_flipped}` prop to `<MiniBoard>`

4. In `frontend/src/components/board/MiniBoard.tsx`:
   - Add `flipped?: boolean` to `MiniBoardProps`
   - Pass `boardOrientation: flipped ? 'black' : 'white'` in the Chessboard options object
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit && npm run lint</automated>
  </verify>
  <done>Creating a bookmark captures flip state, bookmark card mini-board respects flip, loading a bookmark restores flip state on dashboard</done>
</task>

</tasks>

<verification>
1. Backend: `uv run pytest tests/test_bookmark_schema.py -x` passes
2. Frontend: `npx tsc --noEmit` and `npm run lint` pass
3. Manual: Create bookmark with flipped board, see flipped mini-board in card, load it and board flips
</verification>

<success_criteria>
- is_flipped boolean persisted in bookmarks table (default false, backward compatible)
- Bookmark save includes current boardFlipped state
- BookmarkCard mini-board renders flipped when is_flipped=true
- Loading bookmark from card sets boardFlipped on Dashboard
- All existing tests pass, no TS errors
</success_criteria>

<output>
After completion, create `.planning/quick/7-store-board-flip-state-in-bookmarks/7-SUMMARY.md`
</output>
