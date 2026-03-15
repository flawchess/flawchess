---
phase: quick-25
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/position-bookmarks/SuggestionsModal.tsx
  - app/routers/position_bookmarks.py
  - app/schemas/position_bookmarks.py
autonomous: true
requirements: ["Remove Piece filter from suggestion modal", "Always save suggestions with match_side both"]
must_haves:
  truths:
    - "Suggestion modal no longer shows Mine/Both piece filter toggle per suggestion"
    - "Saved suggested bookmarks always have match_side 'both'"
  artifacts:
    - path: "frontend/src/components/position-bookmarks/SuggestionsModal.tsx"
      provides: "Suggestion modal without piece filter UI"
  key_links:
    - from: "SuggestionsModal.tsx handleSave"
      to: "positionBookmarksApi.create"
      via: "match_side hardcoded to 'both'"
      pattern: "match_side.*both"
---

<objective>
Remove the Piece filter (Mine/Both toggle) from the bookmark suggestion modal. All suggested bookmarks should always be created with match_side: "both". Users can change the filter later on the bookmark card itself.

Purpose: Simplify the suggestion modal UI by removing a rarely-useful choice point.
Output: Cleaner suggestion modal, bookmarks saved with "both" match_side.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/position-bookmarks/SuggestionsModal.tsx
@app/routers/position_bookmarks.py
@app/schemas/position_bookmarks.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Remove Piece filter from suggestion modal and hardcode match_side to "both"</name>
  <files>frontend/src/components/position-bookmarks/SuggestionsModal.tsx, app/routers/position_bookmarks.py, app/schemas/position_bookmarks.py</files>
  <action>
In SuggestionsModal.tsx:
1. Remove the `MatchSideChoice` type alias
2. Remove `matchSideChoices` state and `handleMatchSideChange` function
3. Remove `resolveHash` function -- no longer needed since match_side is always "both", which means always use `full_hash`
4. In `renderSuggestionCard`, remove the entire "Pieces:" row (the div containing the ToggleGroup with Mine/Both options)
5. In `handleSave`, hardcode `match_side: 'both'` and `targetHash: suggestion.full_hash` instead of computing from matchSideChoices
6. Remove unused imports: `ToggleGroup`, `ToggleGroupItem`, `resolveMatchSide`
7. Fix bookmark list refresh bug: After saving suggestions and calling `qc.invalidateQueries({ queryKey: ['position-bookmarks'] })`, also call `await qc.refetchQueries({ queryKey: ['position-bookmarks'] })` to ensure the bookmark list updates immediately without requiring a page refresh. The invalidation alone may not trigger a refetch if the modal is closing and components are unmounting.

In app/routers/position_bookmarks.py:
1. Remove the `suggest_match_side` call (lines 114-123) -- no longer needed
2. Hardcode `suggested_match_side="both"` in the PositionSuggestion constructor (or remove the field entirely if cleaner)

In app/schemas/position_bookmarks.py:
1. Keep `suggested_match_side` on `PositionSuggestion` for API compatibility but it will always be "both". Alternatively, remove it if the frontend no longer reads it (check: the frontend used `s.suggested_match_side` to initialize matchSideChoices which is being removed, so this field is no longer consumed). Remove `suggested_match_side` from `PositionSuggestion` schema.

Since suggested_match_side is removed from the schema, also remove it from the PositionSuggestion constructor call in the router.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit && cd /home/aimfeld/Projects/Python/chessalytics && uv run ruff check app/routers/position_bookmarks.py app/schemas/position_bookmarks.py</automated>
  </verify>
  <done>Suggestion modal renders without any Piece filter toggle. Saved bookmarks always use match_side "both" and full_hash as target_hash. No TypeScript or Python lint errors.</done>
</task>

</tasks>

<verification>
- Open suggestion modal: no Mine/Both toggle visible on any suggestion card
- Save a suggested bookmark: verify it appears in bookmark list with match_side "both"
- TypeScript compiles without errors
- Python linting passes
</verification>

<success_criteria>
- Piece filter toggle completely removed from suggestion modal UI
- All saved suggested bookmarks use match_side "both" and full_hash
- No dead code left (matchSideChoices state, resolveHash, suggest_match_side call)
- Frontend and backend pass lint/type checks
</success_criteria>

<output>
After completion, create `.planning/quick/25-remove-the-piece-filter-in-the-bookmark-/25-SUMMARY.md`
</output>
