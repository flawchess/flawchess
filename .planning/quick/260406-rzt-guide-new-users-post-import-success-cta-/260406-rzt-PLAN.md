---
phase: quick
plan: 260406-rzt
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/pages/Import.tsx
  - frontend/src/App.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/components/position-bookmarks/PositionBookmarkList.tsx
autonomous: true
must_haves:
  truths:
    - "After a successful import with games_imported > 0, user sees a CTA button linking to the Openings page"
    - "The Bookmarks tab in the Openings sidebar shows a pulsing notification dot for new users who have no bookmarks yet"
    - "The bookmarks empty state guides users to try the Suggest feature with a clear, action-oriented hint"
  artifacts:
    - path: "frontend/src/pages/Import.tsx"
      provides: "Success CTA linking to Openings page after import completes"
    - path: "frontend/src/App.tsx"
      provides: "Pulsing notification dot on desktop Bookmarks sidebar tab"
    - path: "frontend/src/pages/Openings.tsx"
      provides: "Pulsing dot on Bookmarks sidebar tab (desktop) and bookmark button (mobile)"
    - path: "frontend/src/components/position-bookmarks/PositionBookmarkList.tsx"
      provides: "Improved empty state with actionable guidance"
  key_links:
    - from: "frontend/src/pages/Import.tsx"
      to: "/openings"
      via: "react-router Link in success CTA"
      pattern: "Link.*to.*openings"
---

<objective>
Guide new users through the post-import experience: show a success CTA on the Import page linking to Openings after a successful import, add a pulsing notification dot on the Bookmarks tab to draw attention, and improve the bookmarks empty state with clearer guidance toward the Suggest feature.

Purpose: New users complete import but don't know where to go next. These three nudges create a clear path: Import success -> Openings page -> Bookmarks tab -> Suggest button.
Output: Modified Import page, Openings sidebar tabs, and bookmark list empty state.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/pages/Import.tsx
@frontend/src/pages/Openings.tsx
@frontend/src/App.tsx
@frontend/src/components/position-bookmarks/PositionBookmarkList.tsx
@frontend/src/hooks/useImport.ts
@frontend/src/hooks/usePositionBookmarks.ts
@frontend/src/types/users.ts
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add success CTA to Import page after completed import</name>
  <files>frontend/src/pages/Import.tsx</files>
  <action>
Modify the `ImportProgressBar` component to show a CTA button when `isDone && data.games_imported > 0`. Below the existing green progress bar and success text, render a Link (from react-router-dom) to `/openings` styled as a Button:

```tsx
import { Link } from 'react-router-dom';
import { BookOpenIcon, ArrowRight } from 'lucide-react';
```

After the progress bar `div` (the `h-2 w-full overflow-hidden rounded-full bg-muted` container), when `isDone && data.games_imported > 0`, render:

```tsx
{isDone && data.games_imported > 0 && (
  <div className="flex justify-center pt-2">
    <Button asChild size="sm" data-testid="btn-explore-openings">
      <Link to="/openings">
        <BookOpenIcon className="h-4 w-4" />
        Explore your openings
        <ArrowRight className="h-4 w-4" />
      </Link>
    </Button>
  </div>
)}
```

This provides a clear next step after a successful import. The CTA only shows when games were actually imported (not for "No new games found" syncs). Use the default Button variant (primary/brand) to make it visually prominent.

Import `Link` from `react-router-dom`, and add `BookOpenIcon` and `ArrowRight` to the existing lucide imports at the top of the file.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && npm run lint</automated>
  </verify>
  <done>After a successful import with games_imported > 0, a "Explore your openings" button appears below the progress bar linking to /openings. The button does not appear for zero-game syncs or failed imports.</done>
</task>

<task type="auto">
  <name>Task 2: Add pulsing dot on Bookmarks tab for users with no bookmarks</name>
  <files>frontend/src/pages/Openings.tsx</files>
  <action>
Add a pulsing notification dot to the Bookmarks sidebar tab (desktop) and the bookmark button (mobile) to draw attention when the user has no bookmarks yet.

**Desktop sidebar tab (around line 448):**
The `TabsTrigger value="bookmarks"` currently shows just the icon and "Bookmarks" text. Add a pulsing dot when `bookmarks.length === 0`:

```tsx
<TabsTrigger value="bookmarks" data-testid="sidebar-tab-bookmarks" className="flex-1 relative">
  <BookMarked className="mr-1.5 h-4 w-4" />
  Bookmarks
  {bookmarks.length === 0 && (
    <span
      className="absolute -top-0.5 -right-0.5 flex h-2.5 w-2.5"
      data-testid="bookmarks-notification-dot"
    >
      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
    </span>
  )}
</TabsTrigger>
```

**Mobile bookmark button (around line 919-929):**
The mobile bookmark sidebar trigger button (`btn-open-bookmark-sidebar`) also needs the dot. Wrap it similarly — add `relative` to the Button className and add the same pulsing dot span when `bookmarks.length === 0`:

```tsx
<Button
  variant="ghost"
  size="icon"
  className="h-9 w-9 bg-toggle-active text-toggle-active-foreground hover:bg-toggle-active/80 relative"
  onClick={openBookmarkSidebar}
  data-testid="btn-open-bookmark-sidebar"
  aria-label="Open bookmarks"
>
  <BookMarked className="h-4 w-4" />
  {bookmarks.length === 0 && (
    <span
      className="absolute -top-0.5 -right-0.5 flex h-2.5 w-2.5"
      data-testid="bookmarks-notification-dot-mobile"
    >
      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
    </span>
  )}
</Button>
```

The `animate-ping` class is a standard Tailwind utility that creates the pulsing effect. The dot uses `bg-primary` to match the app's brand color. It disappears automatically once the user creates any bookmark (since `bookmarks.length` becomes > 0).
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && npm run lint</automated>
  </verify>
  <done>Pulsing dot appears on the desktop Bookmarks sidebar tab and mobile bookmark button when user has zero bookmarks. Dot disappears once any bookmark is created.</done>
</task>

<task type="auto">
  <name>Task 3: Improve bookmarks empty state with actionable Suggest hint</name>
  <files>frontend/src/components/position-bookmarks/PositionBookmarkList.tsx</files>
  <action>
Update the empty state message in `PositionBookmarkList.tsx` (line 58-60) to be more action-oriented and guide users toward the Suggest feature as the quickest path to value.

Replace the current empty state paragraph:
```tsx
<p className="px-2 text-xs text-muted-foreground break-words">
  No opening bookmarks yet. Use the &apos;Save&apos; button to bookmark the current position, or use &apos;Suggest&apos; to generate opening bookmarks from your most-played openings.
</p>
```

With a more structured, visually distinct empty state. Import `Sparkles` and `Save` from lucide-react:

```tsx
import { Sparkles, Save } from 'lucide-react';
```

Then replace the empty state:
```tsx
<div className="px-2 space-y-2 text-xs text-muted-foreground" data-testid="bookmarks-empty-state">
  <p>No opening bookmarks yet.</p>
  <div className="flex items-start gap-2">
    <Sparkles className="h-3.5 w-3.5 shrink-0 mt-0.5 text-primary" />
    <p>
      Click <strong className="text-foreground">Suggest</strong> above to auto-generate bookmarks from your most-played openings — the fastest way to get started.
    </p>
  </div>
  <div className="flex items-start gap-2">
    <Save className="h-3.5 w-3.5 shrink-0 mt-0.5 text-primary" />
    <p>
      Or navigate to a position on the board and click <strong className="text-foreground">Save</strong> to bookmark it manually.
    </p>
  </div>
</div>
```

This presents Suggest first (the faster/easier path for new users) and Save second, with visual icons matching the buttons above. The `text-primary` icon color ties them visually to the action buttons.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit && npm run lint</automated>
  </verify>
  <done>Bookmarks empty state shows structured guidance with Suggest as the primary recommendation and Save as the manual alternative, with matching icons. Both desktop sidebar and mobile drawer display the same improved empty state (they share the same PositionBookmarkList component).</done>
</task>

</tasks>

<verification>
1. `cd frontend && npx tsc --noEmit` — TypeScript compiles without errors
2. `cd frontend && npm run lint` — No lint errors
3. `cd frontend && npm run build` — Production build succeeds
4. `cd frontend && npm test` — All existing tests pass
5. `cd frontend && npm run knip` — No dead exports
</verification>

<success_criteria>
- Import page shows "Explore your openings" CTA after successful import with games
- Bookmarks tab shows pulsing dot when user has no bookmarks (desktop and mobile)
- Pulsing dot disappears once user creates first bookmark
- Bookmarks empty state prioritizes Suggest as the recommended action
- All existing tests pass, no TypeScript or lint errors
- Mobile and desktop both updated consistently
</success_criteria>

<output>
After completion, create `.planning/quick/260406-rzt-guide-new-users-post-import-success-cta-/260406-rzt-SUMMARY.md`
</output>
