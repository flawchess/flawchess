---
phase: quick
plan: 260321-erm
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/components/results/GameCard.tsx
  - frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "On mobile, game card shows only opponent name with color icon, no player name or 'vs'"
    - "On desktop, game card still shows both players with 'vs' separator"
    - "On mobile, bookmark card shows the mini board thumbnail"
    - "On mobile, bookmark label wraps to multiple lines if needed instead of truncating"
  artifacts:
    - path: "frontend/src/components/results/GameCard.tsx"
      provides: "Mobile-optimized game card player display"
    - path: "frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx"
      provides: "Mobile-visible mini board and wrapping label"
  key_links: []
---

<objective>
Improve mobile horizontal space usage in GameCard and PositionBookmarkCard.

Purpose: Game cards waste space showing the user's own name and "vs" on mobile where horizontal space is limited. Bookmark cards hide the minimap on mobile unnecessarily.
Output: Updated GameCard.tsx and PositionBookmarkCard.tsx with mobile-specific layout tweaks.
</objective>

<execution_context>
@/home/aimfeld/.claude/get-shit-done/workflows/execute-plan.md
@/home/aimfeld/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@frontend/src/components/results/GameCard.tsx
@frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx
@frontend/src/types/api.ts
</context>

<tasks>

<task type="auto">
  <name>Task 1: Show only opponent in GameCard on mobile</name>
  <files>frontend/src/components/results/GameCard.tsx</files>
  <action>
In the player display row (lines 105-113), modify so that on mobile (below `sm:` breakpoint) only the opponent name+rating with their color icon is shown, while on desktop the full "white vs black" display remains.

The `game.user_color` field tells us which side is the user. Derive opponent name/rating/color from that:
- If user_color is 'white', opponent is black (show "opponent_name (rating)" with a black circle)
- If user_color is 'black', opponent is white (show "opponent_name (rating)" with a white circle)

Implementation approach:
1. Compute `opponentName`, `opponentRating`, `opponentColor` from `game.user_color`, `game.white_username`, `game.black_username`, etc.
2. Replace the current single `<span className="text-sm truncate">` block with two variants:
   - Mobile-only (`sm:hidden`): Show color circle icon + opponent name + rating only. Use `●` for white, `○` for black based on opponent color.
   - Desktop-only (`hidden sm:inline`): Keep the existing "● whiteName (rating) vs ○ blackName (rating)" format unchanged.
3. Keep the result badge and platform link exactly as they are.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit</automated>
  </verify>
  <done>On mobile, game card shows only opponent name with color icon. On desktop, both players with "vs" are shown as before.</done>
</task>

<task type="auto">
  <name>Task 2: Show minimap and allow label wrapping in BookmarkCard on mobile</name>
  <files>frontend/src/components/position-bookmarks/PositionBookmarkCard.tsx</files>
  <action>
Two changes:

1. Show mini board on mobile: On line 94, change `className="hidden sm:block shrink-0"` to `className="shrink-0"` (remove the `hidden sm:block` classes so the MiniBoard is always visible). Reduce the size on mobile: use a smaller size like 60 on mobile vs 80 on desktop. Use two MiniBoard renders with responsive visibility classes: one `sm:hidden` with `size={60}` and one `hidden sm:block` with `size={80}`. Or simpler: just keep one at size 60 since these are thumbnails in a list.

2. Allow label wrapping: On the bookmark label button (line 123), remove the `truncate` class so the label can wrap to multiple lines on narrow screens. Change it to `break-words` or just remove `truncate` and keep `min-w-0`. The label should wrap naturally. Also remove `truncate` behavior — replace `truncate` with `break-all` or just remove it entirely (the `min-w-0` on the parent flex child handles overflow).
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/chessalytics/frontend && npx tsc --noEmit</automated>
  </verify>
  <done>Bookmark card shows minimap on mobile (at smaller size). Bookmark label wraps instead of truncating on narrow screens.</done>
</task>

</tasks>

<verification>
- `npm run build` succeeds without errors
- Visual check: on mobile viewport, game cards show only opponent; bookmark cards show minimap and labels wrap
</verification>

<success_criteria>
- Game cards on mobile show opponent color icon + opponent name + rating only (no user name, no "vs")
- Game cards on desktop unchanged (both players with "vs")
- Bookmark cards show mini board on all screen sizes
- Long bookmark labels wrap rather than truncate on mobile
- TypeScript compiles without errors
</success_criteria>

<output>
After completion, create `.planning/quick/260321-erm-mobile-ux-hide-player-name-in-game-card-/260321-erm-SUMMARY.md`
</output>
