---
phase: quick-3
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/pages/Dashboard.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "Game table shows 'N of M matched' where M is total imported games, not matched count"
    - "Clicking Reset board clears the analysis result panel back to initial state"
  artifacts:
    - path: "frontend/src/pages/Dashboard.tsx"
      provides: "Fixed totalGames source and reset handler"
  key_links:
    - from: "Dashboard.tsx GameTable"
      to: "totalGames prop"
      via: "gameCountData?.count (not analysisResult.stats.total)"
    - from: "Dashboard.tsx BoardControls onReset"
      to: "setAnalysisResult(null)"
      via: "inline handler wrapping chess.reset"
---

<objective>
Fix two bugs in Dashboard.tsx:
1. "N of M games matched" shows the wrong total — M repeats matched_count instead of total imported games.
2. Resetting the board to the starting position does not clear the analysis result panel.

Purpose: Both bugs degrade UX — the count is misleading and stale analysis lingers after board reset.
Output: Single file change to Dashboard.tsx.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@frontend/src/pages/Dashboard.tsx
@frontend/src/hooks/useChessGame.ts
@frontend/src/components/results/GameTable.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix totalGames source and board-reset clears analysis</name>
  <files>frontend/src/pages/Dashboard.tsx</files>
  <action>
Two targeted edits to Dashboard.tsx:

**Fix 1 — totalGames prop (line ~231):**
`GameTable` currently receives `totalGames={analysisResult.stats.total}`, which is the matched-position count (same as `matched_count`). Change it to use the pre-existing `totalGames` variable (from the `/games/count` query at the top of the component, line ~49). Use `totalGames ?? analysisResult.stats.total` as a safe fallback in case the count query hasn't loaded yet.

Before:
```tsx
<GameTable
  games={analysisResult.games}
  matchedCount={analysisResult.matched_count}
  totalGames={analysisResult.stats.total}
  ...
/>
```

After:
```tsx
<GameTable
  games={analysisResult.games}
  matchedCount={analysisResult.matched_count}
  totalGames={totalGames ?? analysisResult.stats.total}
  ...
/>
```

**Fix 2 — Reset clears analysis:**
The `BoardControls` `onReset` prop is currently `chess.reset`. Introduce an inline handler that also clears analysis state:

Before (line ~163):
```tsx
onReset={chess.reset}
```

After:
```tsx
onReset={() => {
  chess.reset();
  setAnalysisResult(null);
  setAnalysisOffset(0);
}}
```

No other changes. Do not touch any other file.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npm run build 2>&1 | tail -20</automated>
  </verify>
  <done>
- Build succeeds with no TypeScript errors.
- GameTable totalGames prop receives `totalGames ?? analysisResult.stats.total` (the /games/count value).
- BoardControls onReset handler calls chess.reset(), setAnalysisResult(null), and setAnalysisOffset(0).
  </done>
</task>

</tasks>

<verification>
After the build passes, manually verify:
1. Run analysis on a position — the table header shows "N of M games matched" where M equals the total games displayed in the header (not M = N).
2. Click the Reset button — the right panel returns to the "Play moves on the board and click Analyze" initial state.
</verification>

<success_criteria>
- `npm run build` exits 0 with no type errors.
- totalGames in GameTable comes from the /games/count query result, not from stats.total.
- Resetting the board sets analysisResult to null, showing the initial empty state.
</success_criteria>

<output>
After completion, create `.planning/quick/3-fix-matched-games-count-showing-wrong-to/3-SUMMARY.md`
</output>
