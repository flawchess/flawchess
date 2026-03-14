---
phase: quick-17
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/results/GameCardList.tsx
  - frontend/src/pages/Dashboard.tsx
autonomous: true
requirements: [quick-17]

must_haves:
  truths:
    - "Import button appears on the same row as the 'N of M games matched' indicator, right-aligned"
    - "Import button is no longer in a separate row above the games list"
    - "Both filtered (analysis) and unfiltered (default) game list views show the Import button inline"
  artifacts:
    - path: "frontend/src/components/results/GameCardList.tsx"
      provides: "Matched count row with optional action slot"
    - path: "frontend/src/pages/Dashboard.tsx"
      provides: "Import button passed into GameCardList"
  key_links:
    - from: "frontend/src/pages/Dashboard.tsx"
      to: "frontend/src/components/results/GameCardList.tsx"
      via: "headerAction prop"
      pattern: "headerAction"
---

<objective>
Move the Import button from its own row above the games list into the same row as the "N of M games matched" indicator, right-aligned.

Purpose: Cleaner layout — the Import button shares the row with the matched games count instead of taking up a separate line.
Output: Updated GameCardList with inline Import button.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/results/GameCardList.tsx
@frontend/src/pages/Dashboard.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add headerAction prop to GameCardList and move Import button inline</name>
  <files>frontend/src/components/results/GameCardList.tsx, frontend/src/pages/Dashboard.tsx</files>
  <action>
In GameCardList.tsx:
1. Add an optional `headerAction?: React.ReactNode` prop to `GameCardListProps`.
2. Change the matched count row (currently a `<p>` at line 80-83) to a flex row with `justify-between items-center`:
   - Left side: the existing "N of M games matched" text
   - Right side: render `{headerAction}` if provided
3. Add `import type { ReactNode } from 'react'` if not already imported.

In Dashboard.tsx:
1. Remove the standalone Import button div at lines 406-411 (the `<div className="flex justify-end">` containing the Import button inside `rightColumn`).
2. Pass the Import button as `headerAction` prop to both GameCardList usages (filtered at ~line 437 and unfiltered at ~line 463):
   ```tsx
   headerAction={
     <Button variant="outline" size="sm" onClick={() => setImportOpen(true)} data-testid="btn-import">
       <Download className="h-4 w-4" />
       Import
     </Button>
   }
   ```
3. Keep `data-testid="btn-import"` on the button. Remove `data-testid="btn-import-cta"` button variable (the one used in empty states) — those empty states already have their own import buttons.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit && npm run lint</automated>
  </verify>
  <done>Import button renders inline with the "N of M games matched" text, right-aligned. No standalone Import button row above the game list. Both filtered and unfiltered views show the button.</done>
</task>

</tasks>

<verification>
- `npm run build` succeeds
- Visual: Import button appears on the same line as "N of M games matched", pushed to the right
</verification>

<success_criteria>
- Import button is right-aligned on the same row as the matched games count indicator
- No layout regression — empty states still show their own import CTA
- TypeScript compiles, lint passes
</success_criteria>

<output>
After completion, create `.planning/quick/17-move-the-import-button-to-the-same-row-a/17-SUMMARY.md`
</output>
