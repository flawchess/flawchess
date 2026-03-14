---
phase: quick-16
plan: 1
type: execute
wave: 1
depends_on: []
files_modified: [frontend/src/pages/Dashboard.tsx]
autonomous: true
requirements: [QUICK-16]

must_haves:
  truths:
    - "Import button appears at the top of the games list (right column), not in the left column"
    - "The '<n> games imported' text no longer appears above the default games list"
    - "Import button still opens the ImportModal when clicked"
  artifacts:
    - path: "frontend/src/pages/Dashboard.tsx"
      provides: "Relocated Import button and removed games-imported indicator"
  key_links:
    - from: "Import button in right column"
      to: "setImportOpen(true)"
      via: "onClick handler"
      pattern: "setImportOpen.*true"
---

<objective>
Move the Import button from the left column action bar to the top of the games list in the right column. Remove the "<n> games imported" indicator text.

Purpose: Better UX — the Import button is more discoverable next to the games list it populates.
Output: Updated Dashboard.tsx with relocated Import button and removed games-imported text.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/pages/Dashboard.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Relocate Import button and remove games-imported indicator</name>
  <files>frontend/src/pages/Dashboard.tsx</files>
  <action>
In Dashboard.tsx, make the following changes:

1. **Remove the Import button from the left column action bar** (around line 399-403):
   Remove the `<Button variant="outline" ...>Import</Button>` from the `div.flex.gap-2.pt-1` container. The Filter button remains as the only button in that container. Since it is now alone, remove `flex-1` from the Filter button so it does not stretch full width — keep it as a normal-width button, or keep flex-1 if it looks better as full-width (use judgment). The `Download` icon import from lucide-react can also be removed if no longer used elsewhere.

2. **Remove the "<n> games imported" text** (around line 460-462):
   Delete the `<p>` element that displays `{defaultGames.data.matched_count.toLocaleString()} games imported`.

3. **Add Import button at the top of the right column**:
   In the `rightColumn`, add an Import button at the very top — above both the position-filtered view and the default unfiltered view. Place it as a right-aligned element:
   ```tsx
   <div className="flex justify-end">
     <Button variant="outline" size="sm" onClick={() => setImportOpen(true)} data-testid="btn-import">
       <Download className="h-4 w-4" />
       Import
     </Button>
   </div>
   ```
   This button should always be visible at the top of the right column regardless of filter state. Keep the `Download` icon import if used here.

4. **Keep the existing `importButton` variable** (lines 227-231) as-is — it is used in empty-state CTAs ("No games imported yet" sections) and serves a different purpose.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit && npm run lint</automated>
  </verify>
  <done>
    - Import button appears at the top of the right column with data-testid="btn-import"
    - Import button no longer appears in the left column action bar
    - The "<n> games imported" text is removed from the default games view
    - Filter button remains functional in the left column
    - Empty-state import CTAs still work
    - TypeScript compiles, lint passes
  </done>
</task>

</tasks>

<verification>
- `npm run lint` passes
- `npx tsc --noEmit` passes
- Visual: Import button visible at top-right of games list area
- Visual: No "games imported" text shown above game cards
- Functional: Clicking Import opens the import modal
</verification>

<success_criteria>
Import button relocated to top of right column, games-imported indicator removed, no regressions in build or lint.
</success_criteria>

<output>
After completion, create `.planning/quick/16-move-the-import-button-to-the-top-of-the/16-SUMMARY.md`
</output>
