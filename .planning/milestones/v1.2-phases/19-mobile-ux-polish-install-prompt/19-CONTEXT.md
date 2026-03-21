# Phase 19: Mobile UX Polish + Install Prompt - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

All app interactions work correctly on mobile touch devices. Fix chessboard touch (click-to-move and drag-and-drop), reorganize Openings page for mobile with sticky board, ensure 44px touch targets and no horizontal overflow at 375px. In-app install prompts for iOS and Android are in scope but deferred to a follow-up discussion after the user tests the UX fixes.

</domain>

<decisions>
## Implementation Decisions

### Openings page mobile layout
- Hide `MobileHeader` on the Openings page only — other pages keep the header for context
- Chessboard sticks to top of viewport on mobile (sticky positioning)
- Below the sticky board: board controls, then compact move list, then collapsible filters section, then Moves/Games/Statistics tabs with scrollable content
- Filters collapsed by default on mobile, expandable via accordion/collapsible
- Position bookmarks remain as a collapsed accordion section below filters (same pattern as now)
- Save/Suggestions buttons stay inline within the bookmarks section

### Chessboard touch interaction
- Try to fix drag-and-drop on touch devices (reversal of Phase 17 decision to disable drag) — investigate react-chessboard v5 touch support
- Fix click-to-move: tapping a square should trigger `onSquareClick` — currently not firing on touch devices
- Selected piece feedback: yellow highlight (existing `rgba(255, 255, 0, 0.5)` logic) — no additional legal move indicators needed
- If drag-and-drop fix proves infeasible, fall back to disabling drag on touch and relying on click-to-move only

### Touch targets & overflow
- Fix-as-you-go approach: address 44px touch targets and overflow issues on each page while working on other Phase 19 tasks
- No separate audit pass — fix what's encountered during chessboard and layout work
- Filter controls (toggle groups, selects): increase tap target height to min 44px on mobile, keep inline/wrapping layout (not vertical stacking)
- Baseline test width: 375px (iPhone SE)

### Claude's Discretion
- Exact sticky positioning CSS approach (sticky vs fixed + offset)
- How to conditionally hide MobileHeader on Openings page (route check vs prop)
- react-chessboard drag-and-drop fix approach — investigate what causes the black screen
- Which specific elements need 44px adjustments (discovered during implementation)
- Overflow fix specifics per component

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — UX-01 (44px targets), UX-02 (no horizontal scroll at 375px), UX-03 (chessboard touch), UX-04 (sidebar + content on mobile), PWA-04/PWA-05 (install prompts — deferred)
- `.planning/ROADMAP.md` §Phase 19 — Success criteria (375px baseline, 44px targets, click-to-click on iOS/Android, Openings layout, install prompts)

### Prior phase context
- `.planning/phases/17-pwa-foundation-dev-workflow/17-CONTEXT.md` — PWA decisions, original drag-disable decision (now reversed)
- `.planning/phases/18-mobile-navigation/18-CONTEXT.md` — Bottom bar, 640px breakpoint, safe-area insets, vaul drawer

### Key source files
- `frontend/src/pages/Openings.tsx` — Openings page layout (desktop 2-col grid, mobile single column)
- `frontend/src/components/board/ChessBoard.tsx` — Chessboard with click-to-move and drag-and-drop handlers
- `frontend/src/App.tsx` — MobileHeader, MobileBottomBar, ProtectedLayout

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MobileHeader` component in `App.tsx`: Currently renders on all pages — needs conditional hiding for Openings
- `ChessBoard` component: Already has `handleSquareClick` with yellow highlight logic and `onPieceDrop` handler
- shadcn/ui `Collapsible` component: Already used for filters and bookmarks on Openings page
- `Drawer` component (vaul): Available for any bottom sheet needs
- `ToggleGroup` / `ToggleGroupItem`: Used for filter controls — needs 44px min height on mobile

### Established Patterns
- Tailwind `sm:` breakpoint (640px) for mobile/desktop switching — `hidden sm:block` / `sm:hidden`
- `md:` breakpoint used for Openings 2-column layout — `md:grid md:grid-cols-[350px_1fr]`
- Mobile single-column: `md:hidden` div renders sidebar then tabs vertically
- `data-testid` on all interactive elements

### Integration Points
- `App.tsx` `ProtectedLayout` — renders `MobileHeader` unconditionally; needs route-aware conditional
- `Openings.tsx` line 496-546 — mobile layout section (`md:hidden`) needs restructuring for sticky board
- `ChessBoard.tsx` line 259 — `onSquareClick` handler may not be receiving touch events
- `ChessBoard.tsx` line 260 — `onPieceDrop` drag handler causes black screen on mobile

</code_context>

<specifics>
## Specific Ideas

- User wants chessboard always visible while scrolling on the Openings page — sticky at top is the key UX improvement
- The black screen on drag is a critical bug that makes the app unusable on mobile — high priority fix
- Install prompts (PWA-04, PWA-05) and action button layout discussions deferred until user tests the UX fixes

</specifics>

<deferred>
## Deferred Ideas

- **Install prompts (PWA-04, PWA-05)** — In scope for Phase 19 but discussion deferred until after user tests chessboard and layout fixes
- **Action buttons in Openings tab** — User wants to discuss layout of action buttons after testing the mobile layout changes
- **Legal move indicators on mobile** — Showing dots on legal destination squares when piece is selected; decided against for now but could revisit

</deferred>

---

*Phase: 19-mobile-ux-polish-install-prompt*
*Context gathered: 2026-03-20*
