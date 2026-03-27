---
phase: quick
plan: 260327-mjt
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/pages/Endgames.tsx
  - frontend/src/pages/GlobalStats.tsx
autonomous: true
must_haves:
  truths:
    - "On mobile Endgames page, filter dropdown and Statistics/Games tab bar stay visible when scrolling"
    - "On mobile Statistics page, recency and platform filters stay visible when scrolling"
    - "Statistics page no longer has the redundant h1 heading"
  artifacts:
    - path: "frontend/src/pages/Endgames.tsx"
      provides: "Sticky mobile filters + tab navigation"
      contains: "sticky top-0"
    - path: "frontend/src/pages/GlobalStats.tsx"
      provides: "Sticky filters, no h1 heading"
      contains: "sticky top-0"
  key_links: []
---

<objective>
Make filter dropdowns and sub-tab navigation sticky on mobile for Endgames and Statistics pages, and remove the redundant Statistics page heading.

Purpose: On mobile, when users scroll through endgame stats or charts, the filter controls and tab navigation scroll off screen, requiring them to scroll back up to change filters or tabs. Making these sticky keeps them accessible.

Output: Updated Endgames.tsx and GlobalStats.tsx
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/pages/Endgames.tsx
@frontend/src/pages/GlobalStats.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Make Endgames mobile filters and tab bar sticky</name>
  <files>frontend/src/pages/Endgames.tsx</files>
  <action>
In the mobile section (line ~244, `md:hidden`), restructure so that the Collapsible filter, the divider, and the TabsList are all inside a sticky wrapper, while TabsContent remains below outside the sticky area.

The challenge: TabsList is currently inside the Tabs component, but we need the sticky wrapper to span across both the Collapsible and the TabsList. Solution: keep the Tabs component wrapping everything (it just provides context), but restructure the DOM so the sticky div wraps the Collapsible + divider + TabsList:

```tsx
<div className="md:hidden flex flex-col min-w-0">
  <Tabs value={activeTab} onValueChange={(val) => navigate(`/endgames/${val}`)}>
    {/* Sticky: filters + tab bar */}
    <div className="sticky top-0 z-20 bg-background pb-2 flex flex-col gap-2">
      <Collapsible ...>...</Collapsible>
      <div className="border-t border-border/40" />
      <TabsList className="w-full h-11!" data-testid="endgames-tabs-mobile">
        ...
      </TabsList>
    </div>
    <TabsContent value="statistics" className="mt-4">
      {statisticsContent}
    </TabsContent>
    <TabsContent value="games" className="mt-4">
      {gamesContent}
    </TabsContent>
  </Tabs>
</div>
```

Key details:
- Use `sticky top-0 z-20 bg-background pb-2` on the wrapper (same pattern as Openings page mobile board)
- The `bg-background` is essential so sticky content doesn't show scrolling content behind it
- Move Tabs to wrap the entire mobile section so TabsList and TabsContent share the same Tabs context
- Remove the `gap-2` from the outer div (the sticky wrapper handles its own spacing)
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>On mobile Endgames page, the filter collapsible and Statistics/Games tab bar stick to the top of the viewport when scrolling, while tab content scrolls freely below</done>
</task>

<task type="auto">
  <name>Task 2: Remove Statistics h1 and make filter section sticky</name>
  <files>frontend/src/pages/GlobalStats.tsx</files>
  <action>
Two changes to GlobalStats.tsx:

1. **Remove the h1 heading** (line 27): Delete `<h1 className="text-2xl font-semibold">Statistics</h1>`. The page title is already shown in the mobile header bar ("Statistics") and in the desktop nav tab, so the h1 is redundant.

2. **Make the filter section sticky**: Wrap the filter div (lines 30-85) in a sticky container. The header is NOT sticky (it scrolls away), so use `sticky top-0`:

```tsx
<div data-testid="global-stats-page" className="mx-auto max-w-4xl space-y-6 px-6 py-6">
  {/* Sticky filters */}
  <div className="sticky top-0 z-10 bg-background pb-2 -mx-6 px-6 pt-1">
    <div className="flex flex-wrap items-end gap-4">
      {/* Recency filter */}
      ...
      {/* Platform filter */}
      ...
    </div>
  </div>

  {isLoading ? ... : ...}
</div>
```

Key details:
- Use `sticky top-0 z-10 bg-background` so content doesn't bleed through
- Use `-mx-6 px-6` to extend the background to full width (counteract parent padding) so there's no gap at edges when scrolling
- Add `pt-1` for a small top breathing room
- Add `pb-2` for spacing below the sticky filter bar
- z-10 is sufficient (no competing z-index on this page)
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npx tsc --noEmit 2>&1 | head -20</automated>
  </verify>
  <done>Statistics page has no h1 heading; filter section sticks to top when scrolling on both mobile and desktop</done>
</task>

</tasks>

<verification>
1. `cd frontend && npx tsc --noEmit` — no TypeScript errors
2. `npm run build` — builds successfully
3. Visual check on mobile viewport: Endgames page filters + tabs stick; Statistics page filters stick; no h1 on Statistics
</verification>

<success_criteria>
- Endgames mobile: filter collapsible + divider + tab bar are sticky at viewport top when scrolling
- Statistics: h1 removed, filter bar is sticky at viewport top when scrolling
- No TypeScript or build errors
- Desktop layout unchanged
</success_criteria>

<output>
After completion, create `.planning/quick/260327-mjt-sticky-filter-dropdowns-endgame-and-stat/260327-mjt-SUMMARY.md`
</output>
