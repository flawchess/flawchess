---
phase: quick
plan: 260317-qsf
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/hooks/usePositionBookmarks.ts
autonomous: true
must_haves:
  truths:
    - "Deleting a bookmark removes it from the list immediately without page refresh"
    - "If the delete API call fails, the bookmark reappears in the list"
  artifacts:
    - path: "frontend/src/hooks/usePositionBookmarks.ts"
      provides: "Optimistic delete mutation for position bookmarks"
      contains: "onMutate"
  key_links:
    - from: "useDeletePositionBookmark"
      to: "TanStack Query cache"
      via: "setQueryData optimistic removal"
      pattern: "setQueryData.*position-bookmarks"
---

<objective>
Fix bookmark delete not updating the UI until page refresh.

Purpose: The `useDeletePositionBookmark` hook only calls `invalidateQueries` on success, which marks the cache stale but does not force an immediate refetch. The `PositionBookmarkList` component has local `items` state synced from the query via `useEffect`, so the bookmark stays visible until the cache actually refreshes. Adding an optimistic update (like the existing `useReorderPositionBookmarks` pattern) removes the bookmark from cache immediately on click.

Output: Updated `useDeletePositionBookmark` with optimistic cache removal and error rollback.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/hooks/usePositionBookmarks.ts
@frontend/src/components/position-bookmarks/PositionBookmarkList.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add optimistic update to useDeletePositionBookmark</name>
  <files>frontend/src/hooks/usePositionBookmarks.ts</files>
  <action>
Refactor `useDeletePositionBookmark` to use the optimistic update pattern already established by `useReorderPositionBookmarks` in the same file (lines 39-58). Specifically:

1. Define a context type for rollback: `type DeleteContext = { prev: unknown };`
2. Add `onMutate` callback:
   - `await qc.cancelQueries({ queryKey: ['position-bookmarks'] })` to prevent in-flight refetches from overwriting
   - Snapshot: `const prev = qc.getQueryData(['position-bookmarks'])`
   - Optimistically remove: `qc.setQueryData(['position-bookmarks'], (old: unknown) => (old as PositionBookmarkResponse[])?.filter((b) => b.id !== id))` where `id` is the mutation variable
   - Return `{ prev }` for rollback context
3. Add `onError` callback: restore previous data from context `qc.setQueryData(['position-bookmarks'], ctx?.prev)`
4. Replace `onSuccess` with `onSettled`: `() => qc.invalidateQueries({ queryKey: ['position-bookmarks'] })` to ensure server sync regardless of success/failure

Import `PositionBookmarkResponse` type if not already imported (it is already imported on line 3).

Follow the exact same typing pattern as `useReorderPositionBookmarks` — use explicit generic type parameters on `useMutation<void, Error, number, DeleteContext>`.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>Deleting a bookmark immediately removes it from the visible list. If the API call fails, the bookmark reappears. On settled (success or error), the cache is revalidated against the server.</done>
</task>

</tasks>

<verification>
- TypeScript compiles without errors
- Manual test: delete a bookmark and confirm it disappears instantly from the list without page refresh
</verification>

<success_criteria>
- Bookmark disappears from the list immediately on delete click (optimistic removal)
- On API error, bookmark reappears (rollback)
- Cache revalidates on settled to stay in sync with server
</success_criteria>

<output>
After completion, create `.planning/quick/260317-qsf-fix-bookmark-delete-not-updating-ui-unti/260317-qsf-SUMMARY.md`
</output>
