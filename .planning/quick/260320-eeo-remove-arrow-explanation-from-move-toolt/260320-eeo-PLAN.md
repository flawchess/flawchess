---
phase: quick
plan: 260320-eeo
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/move-explorer/MoveExplorer.tsx
  - frontend/src/pages/Openings.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "Move tooltip only explains what the moves are (no arrow color/thickness explanation)"
    - "Info icon appears next to the opening name at bottom-right of chessboard area"
    - "Info icon tooltip explains chessboard interaction and arrow color meanings"
  artifacts:
    - path: "frontend/src/components/move-explorer/MoveExplorer.tsx"
      provides: "Shortened Move tooltip without arrow explanation"
    - path: "frontend/src/pages/Openings.tsx"
      provides: "Info icon with chessboard explanation tooltip"
  key_links:
    - from: "frontend/src/pages/Openings.tsx"
      to: "Tooltip component"
      via: "Info icon in opening name row"
      pattern: "chessboard-info"
---

<objective>
Move the arrow color/thickness explanation out of the Move column tooltip in MoveExplorer and into a new info icon placed next to the opening name below the chessboard. The Move tooltip should only explain what the listed moves represent. The new chessboard info icon explains board interaction and arrow semantics.

Purpose: The arrow explanation belongs near the board, not in the Moves tab header.
Output: Updated MoveExplorer.tsx and Openings.tsx
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/move-explorer/MoveExplorer.tsx
@frontend/src/pages/Openings.tsx
@frontend/src/components/board/ChessBoard.tsx
@frontend/src/lib/arrowColor.ts
</context>

<tasks>

<task type="auto">
  <name>Task 1: Shorten Move tooltip and add chessboard info icon</name>
  <files>frontend/src/components/move-explorer/MoveExplorer.tsx, frontend/src/pages/Openings.tsx</files>
  <action>
1. In MoveExplorer.tsx, shorten the Move tooltip (line 78-79) to remove the second paragraph about arrows. Keep only the first sentence:
   "These are the moves that occurred next in the position shown on the board, over all the games that match the current filter settings."
   Remove the `<br/><br/>` and the entire arrow explanation paragraph.

2. In Openings.tsx, modify the opening name row (lines 240-247) to add an info icon at the right end, at the same height as the opening name. The row should use `flex items-center justify-between` (or keep items-baseline for the text but add ml-auto to the icon). Structure:

   ```
   <div className="flex items-center gap-2 px-1 text-sm min-h-[1.25rem]">
     {chess.openingName ? (
       <div className="flex items-baseline gap-2">
         <span className="font-mono text-xs text-muted-foreground">{eco}</span>
         <span className="text-foreground">{name}</span>
       </div>
     ) : (
       <div />
     )}
     <TooltipProvider>
       <Tooltip>
         <TooltipTrigger asChild>
           <button type="button" className="ml-auto text-muted-foreground hover:text-foreground flex-shrink-0" aria-label="Chessboard info" data-testid="chessboard-info">
             <Info className="h-3.5 w-3.5" />
           </button>
         </TooltipTrigger>
         <TooltipContent side="top" className="max-w-xs text-sm">
           Play moves on the board by dragging pieces or clicking source and target squares.
           <br/><br/>
           The arrows show the next moves from your games. Thicker arrows mean the move occurred more frequently. Colors indicate your results: green for high win rate (60%+), red for high loss rate (60%+), and grey otherwise. Moves with fewer than 10 games are always grey.
         </TooltipContent>
       </Tooltip>
     </TooltipProvider>
   </div>
   ```

   This replaces both the opening name div (lines 240-244) and the empty-state spacer div (line 246). The info icon is always visible (even when no opening name is shown). Use `min-h-[1.25rem]` to maintain consistent height when no opening name exists (instead of the `h-5` spacer div).

   Note: Info and the Tooltip components are already imported in Openings.tsx.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>
  - Move tooltip in MoveExplorer only contains the first sentence about listed moves
  - Info icon appears at bottom-right of chessboard area (same row as opening name)
  - Info icon tooltip has two paragraphs: board interaction + arrow color explanation
  - TypeScript compiles without errors
  </done>
</task>

</tasks>

<verification>
- `cd frontend && npx tsc --noEmit` passes
- Visual check: Move tooltip is shorter, info icon visible below board
</verification>

<success_criteria>
- Arrow explanation removed from Move column tooltip in MoveExplorer
- New info icon below chessboard explains board interaction and arrow colors
- No TypeScript errors
</success_criteria>

<output>
After completion, create `.planning/quick/260320-eeo-remove-arrow-explanation-from-move-toolt/260320-eeo-SUMMARY.md`
</output>
