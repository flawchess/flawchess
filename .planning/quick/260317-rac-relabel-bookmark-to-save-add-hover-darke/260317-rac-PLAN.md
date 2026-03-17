---
phase: quick
plan: 260317-rac
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/pages/Openings.tsx
autonomous: true
must_haves:
  truths:
    - "Save button displays label 'Save' instead of 'Bookmark'"
    - "Save and Suggest buttons darken on hover"
  artifacts:
    - path: "frontend/src/pages/Openings.tsx"
      provides: "Updated button label and hover styles"
  key_links: []
---

<objective>
Relabel the "Bookmark" button to "Save" and add hover darkening effect on both action buttons in the Position bookmarks collapsible section.

Purpose: Improve button labeling clarity and add visual hover feedback.
Output: Updated Openings.tsx with renamed button and hover styles.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/pages/Openings.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Relabel Bookmark to Save and add hover darkening</name>
  <files>frontend/src/pages/Openings.tsx</files>
  <action>
1. Change the lucide-react import: replace `Bookmark` with `Save` icon (from lucide-react).

2. In the first Button (around line 375-384):
   - Change the icon from `<Bookmark className="h-4 w-4" />` to `<Save className="h-4 w-4" />`
   - Change the label text from `Bookmark` to `Save`
   - Keep `data-testid="btn-bookmark"` unchanged (avoid breaking existing test IDs)

3. For both buttons (Save and Suggest), add hover darkening:
   - Replace the inline `style={{ backgroundColor: '#0a3d6b', color: 'white' }}` with a Tailwind className approach
   - Add classes: `bg-[#0a3d6b] hover:bg-[#072d50] text-white` to each button's className (appended to existing `flex-1`)
   - Remove the inline `style` prop entirely from both buttons since Tailwind handles it

The final button className should be: `"flex-1 bg-[#0a3d6b] hover:bg-[#072d50] text-white"`
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit 2>&1 | tail -5</automated>
  </verify>
  <done>
  - Button label reads "Save" with Save icon
  - Both buttons darken from #0a3d6b to #072d50 on hover
  - No inline style props on the action buttons
  - TypeScript compiles without errors
  </done>
</task>

</tasks>

<verification>
- TypeScript compiles cleanly
- Visual check: buttons show "Save" and "Suggest" labels with hover darkening
</verification>

<success_criteria>
- "Bookmark" label replaced with "Save" and Save icon used
- Both action buttons have hover:bg-[#072d50] darkening effect
- No TypeScript errors
</success_criteria>

<output>
After completion, create `.planning/quick/260317-rac-relabel-bookmark-to-save-add-hover-darke/260317-rac-SUMMARY.md`
</output>
