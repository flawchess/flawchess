---
phase: quick
plan: 260317-qyx
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/pages/Openings.tsx
  - frontend/src/components/position-bookmarks/PositionBookmarkList.tsx
autonomous: true
requirements: [QUICK-260317-qyx]
must_haves:
  truths:
    - "Bookmark and Suggest buttons use dark blue (#0a3d6b) background with white text"
    - "Both buttons sit side-by-side at the top of the Position bookmarks collapsible"
    - "Suggest bookmarks button is renamed to Suggest"
    - "Subtle horizontal dividers separate sidebar sections"
  artifacts:
    - path: "frontend/src/pages/Openings.tsx"
      provides: "Restructured sidebar with buttons inside collapsible and dividers"
    - path: "frontend/src/components/position-bookmarks/PositionBookmarkList.tsx"
      provides: "Suggest button removed (moved to parent)"
  key_links:
    - from: "frontend/src/pages/Openings.tsx"
      to: "frontend/src/components/position-bookmarks/PositionBookmarkList.tsx"
      via: "PositionBookmarkList no longer renders Suggest button"
      pattern: "SuggestionsModal"
---

<objective>
Style action buttons (Bookmark, Suggest) with dark blue (#0a3d6b) background to visually separate them from filter controls, move both inside the Position bookmarks collapsible side-by-side, rename "Suggest bookmarks" to "Suggest", and add subtle horizontal dividers between sidebar sections.

Purpose: Improve visual hierarchy — action buttons should look distinct from filter controls.
Output: Updated Openings.tsx and PositionBookmarkList.tsx
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/pages/Openings.tsx
@frontend/src/components/position-bookmarks/PositionBookmarkList.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Move buttons into collapsible, style dark blue, add dividers</name>
  <files>frontend/src/pages/Openings.tsx, frontend/src/components/position-bookmarks/PositionBookmarkList.tsx</files>
  <action>
**In PositionBookmarkList.tsx:**
- Remove the "Suggest bookmarks" Button and the SuggestionsModal from this component entirely. The parent (Openings.tsx) will own them.
- Remove the `Sparkles` and `Button` imports if no longer needed (Button may still be needed — check).
- Remove `SuggestionsModal` import and `suggestionsOpen` state.
- The component should now only render the bookmark list (empty message or DndContext list), nothing else.

**In Openings.tsx:**
- Add imports: `Sparkles` from lucide-react, `SuggestionsModal` from position-bookmarks.
- Add state: `const [suggestionsOpen, setSuggestionsOpen] = useState(false);`
- Remove the standalone Bookmark button (lines ~353-365) from its current position above the collapsible.
- Inside the Position bookmarks CollapsibleContent, BEFORE the PositionBookmarkList, add a flex row with both buttons:
  ```tsx
  <div className="flex gap-2 mb-2">
    <Button
      size="lg"
      className="flex-1"
      style={{ backgroundColor: '#0a3d6b', color: 'white' }}
      onClick={openBookmarkDialog}
      data-testid="btn-bookmark"
    >
      <Bookmark className="h-4 w-4" />
      Bookmark
    </Button>
    <Button
      size="lg"
      className="flex-1"
      style={{ backgroundColor: '#0a3d6b', color: 'white' }}
      onClick={() => setSuggestionsOpen(true)}
      data-testid="btn-suggest-bookmarks"
    >
      <Sparkles className="h-4 w-4" />
      Suggest
    </Button>
  </div>
  ```
  Note: Use inline style for the dark blue color (per Claude's discretion — avoids needing to extend the button variant system for a single color). Do NOT use `variant="outline"` — the inline style overrides the background directly.

- Render `<SuggestionsModal open={suggestionsOpen} onOpenChange={setSuggestionsOpen} />` next to the existing bookmark Dialog (at the bottom of the component).

- Add subtle horizontal dividers (`<hr>` or `<div>` with border) between sidebar sections. Use `border-t border-border/40` class for subtle appearance. Add dividers between:
  1. After Board controls, before Played as / Piece filter
  2. After Played as / Piece filter, before Position bookmarks collapsible
  3. After Position bookmarks collapsible, before More filters collapsible

  Use: `<div className="border-t border-border/40" />` as the divider element.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npm run build 2>&1 | tail -5</automated>
  </verify>
  <done>
  - Bookmark and Suggest buttons are dark blue (#0a3d6b) with white text, side-by-side inside the Position bookmarks collapsible
  - "Suggest bookmarks" renamed to "Suggest"
  - Subtle dividers separate board controls, filters, bookmarks, and more-filters sections
  - PositionBookmarkList no longer renders the Suggest button
  - Build passes with no errors
  </done>
</task>

</tasks>

<verification>
- `npm run build` succeeds
- Visual check: buttons are dark blue, side-by-side, inside collapsible
- Visual check: dividers visible between sections
</verification>

<success_criteria>
- Action buttons visually distinct from filter controls via dark blue color
- Both buttons inside Position bookmarks collapsible, side-by-side, equal weight
- "Suggest" label (not "Suggest bookmarks")
- Subtle dividers between sidebar sections
- All data-testid attributes preserved
</success_criteria>

<output>
After completion, create `.planning/quick/260317-qyx-style-action-buttons-with-distinct-color/260317-qyx-SUMMARY.md`
</output>
