---
quick_id: 260710-wub
status: planned
---

# Quick Task 260710-wub: Openings analyze-button relocation + sideline delete fix

Two small frontend changes, executed inline (no subagents — mechanical, well-scoped).

## Task 1 — Move "Analyze position" into the sidebar (icon button)

Remove the full-width "Analyze position" `Button` currently rendered under the
board on the Openings **Moves (explorer)** tab, in both layouts:

- Desktop: `frontend/src/pages/Openings.tsx` ~L944-954 (`btn-analyze-position`)
- Mobile: `frontend/src/pages/Openings.tsx` ~L1076-1087 (`btn-analyze-position-mobile`)

Replace with a compact white Search-icon button:

- **Desktop**: add a ghost icon `Button` (lucide `Search`) into the `SidebarLayout`
  `stripExtra` slot alongside the existing played-as color toggle, gated to
  `activeTab === 'explorer'` to preserve original visibility. Tooltip "Analyze position",
  `data-testid="sidebar-strip-btn-analyze"`, `aria-label="Analyze position"`.
- **Mobile**: add a ghost icon `Button` (lucide `Search`) to the settings column
  (`openings-mobile-settings-column`) directly **under the bookmarks button**
  (before the info popover). Same styling as the other 44px column buttons.
  Tooltip "Analyze position", `data-testid="btn-analyze-position-mobile"`,
  `aria-label="Analyze position"`, gated to `activeTab === 'explorer'`.

Both call the existing `handleAnalyzePosition`. Import `Search` from lucide-react;
drop the now-unused `Microscope` import if no other usage remains.

## Task 2 — Fix non-working sideline × delete in fen (free-play) mode

`frontend/src/pages/Analysis.tsx` L2104 wires
`onDeleteLine={isGameMode ? deleteSubtree : undefined}`. In `?fen=` free-play mode
`isGameMode` is false, so the free-move sideline's × button renders (it's a
non-tactic block) but its click handler is `undefined` — nothing happens.

Fix: wire `onDeleteLine={deleteSubtree}` unconditionally. `deleteSubtree` is always
returned by `useAnalysisBoard` and correctly recovers `currentNodeId` to the fork
parent (root fen) when the deleted subtree contained the current node.

## Verify

- `cd frontend && npm run lint && npm test -- --run && npx tsc -b`
- Manual: Openings Moves tab shows Search icon in sidebar (desktop) / settings
  column under bookmarks (mobile); clicking navigates to analysis. On Analysis with
  `?fen=`, play moves → sideline appears → × removes it.
