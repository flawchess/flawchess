# Phase 50: Mobile Layout Restructuring - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-10
**Phase:** 50-mobile-layout-restructuring
**Areas discussed:** Mobile layout rethink (user-led), unified row order, collapse handle placement, Endgames consistency

---

## Opening: Gray Area Selection

Claude presented four pre-analyzed gray areas (Subtab placement, Sticky board behavior, Scope, Endgames consistency depth) and asked which to discuss.

**User response:** Redirected the discussion — declined the pre-selected areas and said: *"After introducing a shadcn sidebar with great results on desktop, I we should rethink the mobile layout from scratch. I have some ideas I want to discuss."*

Claude stepped back and asked the user to share their ideas directly.

---

## User-Proposed Mobile Layout

**User's proposal (verbatim):**
- Put the 2 drawer buttons and the player color toggle in the same row as the subtab navigation on Openings mobile.
- To make horizontal space, rework the subtab navigation (e.g., scrollable tabs or carousel). Make it left-right swipeable.
- Enlarge the board action button bar to fill up the freed vertical space.
- Advantage: the drawer buttons and player toggle remain available when the chessboard section is folded.
- Use a transparent background for the foldable chessboard section (similar to the transparent/blurred background in the sidebar content area on desktop).

---

## Claude's Pushback and Clarification Round

Claude raised six concerns before accepting the proposal:

### 1. Swipe-to-change-tab vs the locked PROJECT.md rule

Claude noted that PROJECT.md "Out of Scope" explicitly forbids swipe-to-navigate between tabs because it conflicts with chess piece dragging, and asked which of three swipe interpretations the user meant:
- (a) Scrollable tab strip (`overflow-x-auto`) — not touching the locked decision
- (b) Swipe on the tab bar itself to paginate — small target, rarely needed
- (c) Swipe on the content area to change tabs — the ruled-out case

**User's answer:** *"I meant c. There might be a fourth tab coming soon (Insights), so we probably can't fit all tabs horizontal, if the include labels like they do now. But we can cross that bridge when we get there and try without swipe/scroll-tabs/carousel for now"*

**Outcome:** User acknowledged the conflict and deferred the entire scrolling/swipe/carousel question. Phase 50 uses a plain flex TabsList. The Insights-tab pressure is acknowledged but deferred. The Out-of-Scope rule stays reaffirmed.

### 2. Horizontal space math

Claude showed that at 375px viewport, three icon buttons plus a three-tab TabsList fit comfortably in the available width — scrollable/carousel tabs may be unnecessary complexity.

**User's answer:** See item 1. Same conclusion: skip scrollable/carousel for now.

### 3. "Enlarge the board action button bar" ambiguity

Claude asked whether enlarging meant:
- (a) Making the remaining 5 buttons taller (board width unchanged) — strongly preferred
- (b) Widening the column (board shrinks, bad on 375px)

**User's answer:** *"a (more vertical space between action buttons)"*

**Outcome:** Locked as D-07. Remaining 5 buttons (back, forward, reset, flip, info) get taller / more gap. Board width stays the same.

### 4. Transparent background clarification

Claude initially suggested the user might want charcoal-texture instead of true backdrop-blur because of iOS GPU cost, and asked which of two options they had in mind.

**User's answer:** *"b. I wasn't talking about the sidebar strip, I was talking about the transparent filter/bookmarks sections when opening the sidebar"*

Claude then read `frontend/src/components/layout/SidebarLayout.tsx:112` and confirmed the desktop panel uses `bg-background/80 backdrop-blur-md border border-border rounded-r-md` — real translucent blur, not charcoal-texture. Claude dropped the charcoal-texture steer and accepted the user's preference for true backdrop-blur. D-08 through D-10 capture the effect and the shadow softening needed.

### 5. Endgames mobile scope

Claude laid out that Endgames has no board, no color toggle, no bookmarks — so most of the Openings restructuring motivation doesn't apply. Claude offered three handling options for EGAM-01:
- (a) Mark satisfied (no code changes)
- (b) Defer to a later phase (split MMOB-01 and EGAM-01)
- (c) Visual alignment only (row height, gaps, backdrop-blur, no structural change)

**User's answer:** *"The endgame tab navigation can stay as is for now"* plus the follow-up question choice *"Touch Endgames only for visual alignment"*.

**Outcome:** Locked as D-13 and D-14. Endgames receives a visual-alignment pass only.

### 6. Row placement inside the sticky wrapper

Claude asked whether the new unified row should sit inside the sticky wrapper but outside the collapse animation grid, so it stays visible when the board is collapsed.

**User's answer:** *"yes"*

**Outcome:** Locked as D-03.

---

## Final Question Round

After the pushback cleared, Claude asked three remaining questions via AskUserQuestion:

### Unified Row Order (D-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Tabs \| toggle \| filter \| bookmark | Tabs left, toggle/filter/bookmark right in that order | |
| Toggle \| filter \| bookmark \| tabs | Controls left, tabs take remaining space on the right | |
| Filter \| bookmark \| toggle \| tabs | Drawer buttons leftmost, color toggle next to tabs | |

**User's choice (free text):** *"Tabs | toggle | bookmark | filter"*

**Notes:** User wrote their own order — not one of the three Claude offered. Bookmark comes before filter (opposite of the current vertical column order where filter is above bookmark). Captured verbatim in D-02.

### Collapse Handle Placement (D-11, D-12)

| Option | Description | Selected |
|--------|-------------|----------|
| Bottom of sticky region (current) | Handle stays below the unified row | ✓ |
| Between board and unified row | Handle moves up, unified row becomes the permanent bottom strip | |

**User's choice:** *"Bottom of sticky region (current). Increase the height a bit, it's hard to tap currently"*

**Notes:** User added a touch-target complaint that was not in Claude's option description. This became D-12 — the collapse handle must be enlarged to meet the 44px touch target minimum. Captured as a real fix, not a cosmetic tweak.

### EGAM-01 Handling (D-13, D-14)

| Option | Description | Selected |
|--------|-------------|----------|
| Mark EGAM-01 satisfied | No code changes for Endgames; requirement closes in this phase | |
| Defer EGAM-01 to a later phase | Split MMOB-01 and EGAM-01 | |
| Touch Endgames only for visual alignment | Apply backdrop-blur and match row height/gaps; no structural changes | ✓ |

**User's choice:** Touch Endgames only for visual alignment

**Notes:** Locked as D-14. Endgames gets `bg-background/80 backdrop-blur-md` on its sticky row plus row height and gap matching to the new Openings unified row.

---

## Claude's Discretion (summary)

- Exact heights of the unified row, the enlarged board-action buttons, and the collapse handle (collapse handle must meet 44px touch target minimum)
- Exact gap sizing inside the unified row
- Whether to keep a subtle shadow or drop it entirely when moving to backdrop-blur
- Notification dot visual adjustment in the new row position
- Sticky wrapper `z-index` interaction with the filter/bookmark drawers
- Whether to move the info popover into the unified row if the vertical column feels unbalanced after enlargement

## Deferred Ideas (summary)

- Scrollable / swipeable / carousel subtabs — deferred until a 4th Insights tab is actually being added
- Swipe-on-content-to-change-tab — reaffirmed as out of scope per PROJECT.md
- Endgames mobile structural restructuring — deferred indefinitely
- Info popover relocation — may happen in Phase 50 at Claude's discretion during planning
