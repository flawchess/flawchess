---
phase: quick
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/board/ChessBoard.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "Rank numbers (1-8) appear outside the left edge of the board"
    - "File letters (a-h) appear outside the bottom edge of the board"
    - "Labels flip correctly when the board orientation is black (flipped)"
    - "Built-in in-square notation is hidden"
  artifacts:
    - path: "frontend/src/components/board/ChessBoard.tsx"
      provides: "Board with external coordinate labels"
  key_links:
    - from: "ChessBoard.tsx flipped prop"
      to: "coordinate label order"
      via: "ranks reversed / files reversed when flipped=true"
      pattern: "flipped.*reverse"
---

<objective>
Display chess board coordinate labels (rank numbers and file letters) outside the board boundaries rather than overlaid on the squares.

Purpose: Cleaner board appearance — labels never obscure pieces or square colors.
Output: Updated ChessBoard.tsx with external coordinate labels and built-in notation hidden.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@frontend/src/components/board/ChessBoard.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add external coordinate labels to ChessBoard</name>
  <files>frontend/src/components/board/ChessBoard.tsx</files>
  <action>
    Modify ChessBoard.tsx to render coordinate labels outside the board:

    1. Set `showNotation: false` in the `options` prop to hide the built-in in-square labels.

    2. Wrap the existing `<div ref={containerRef}>` in a new outer flex container.
       Layout: a row containing [rank-labels column] + [inner column of (board + file-labels row)].

    3. Rank labels column (left side):
       - A vertical flex column, height = boardWidth px, width ~16px
       - Contains 8 labels: when `flipped=false` show ["8","7","6","5","4","3","2","1"] top-to-bottom;
         when `flipped=true` show ["1","2","3","4","5","6","7","8"] top-to-bottom
       - Each label: `flex-1 flex items-center justify-center text-xs text-gray-400 select-none`

    4. File labels row (below board):
       - A horizontal flex row, width = boardWidth px
       - Contains 8 labels: when `flipped=false` show ["a","b","c","d","e","f","g","h"] left-to-right;
         when `flipped=true` show ["h","g","f","e","d","c","b","a"] left-to-right
       - Each label: `flex-1 flex items-center justify-center text-xs text-gray-400 select-none`
       - Row height ~16px

    5. The rank-labels column and file-labels row must both use `boardWidth` for their dimension
       so labels align perfectly with squares as the board resizes.

    6. Use `style={{ height: boardWidth }}` (inline) for the rank column to stay in sync with
       boardWidth state, and `style={{ width: boardWidth }}` for the file row.

    Do NOT use mt-/mb-/ml-/mr- Tailwind spacing that would misalign labels from board edges.
    Keep all existing props (position, boardOrientation, boardStyle, squareStyles, onPieceDrop)
    exactly as they are — only add showNotation: false and wrap with label elements.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npm run build 2>&1 | tail -5</automated>
  </verify>
  <done>
    Build passes with no TypeScript errors. Board renders with rank numbers on the left and
    file letters on the bottom, no labels inside squares, labels flip when board is flipped.
  </done>
</task>

</tasks>

<verification>
- `npm run build` exits 0 with no type errors
- Visual check: open the app, the board shows no in-square labels, rank numbers appear left of the board, file letters appear below
- Flip the board: labels reverse order correctly
</verification>

<success_criteria>
Rank numbers 1-8 and file letters a-h are displayed outside the board boundaries (left and bottom respectively), flip with board orientation, and the build is clean.
</success_criteria>

<output>
After completion, create `.planning/quick/1-can-the-coordinate-numbers-and-letters-b/1-SUMMARY.md`
</output>
