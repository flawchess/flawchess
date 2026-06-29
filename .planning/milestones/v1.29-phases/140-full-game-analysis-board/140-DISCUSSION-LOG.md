# Phase 140: Full-Game Analysis Board - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-27
**Phase:** 140-full-game-analysis-board
**Areas discussed:** PV sideline URL state, Move-list flaw markers, Un-analyzed Analyze button, On-demand PV fetch UX

Context note: the phase arrived heavily pre-decided (`analysis-board-fullgame-refinement.md` locked
decisions + approved `140-UI-SPEC.md`). Discussion targeted only the remaining edge cases those
documents did not cover.

---

## Expanded-PV state lifetime

| Option | Description | Selected |
|--------|-------------|----------|
| Ephemeral (in-memory) | Chip expansion is transient; URL keeps game_id+ply only; refresh returns to collapsed main line | ✓ |
| URL-encoded (shareable) | Expanded PV/sub-PV path encoded in URL so a shared link reopens the sideline | |

**User's choice:** Ephemeral (in-memory)
**Notes:** `?fen=` free-play variation state stays URL-encoded as in Phase 137 — unchanged.

---

## Move-list flaw markers (tag eligibility)

| Option | Description | Selected |
|--------|-------------|----------|
| Only tactic-motif flaws | Tag renders only on plies with a tactic motif | |
| All flaws; disable if no PV | Tag on every blunder/mistake; chips without a PV disabled | |

**User's choice:** Free text — tagged flaws render the Missed/Allowed pill; ALL flaws (incl.
un-tagged) get a distinct blunder/mistake icon.
**Notes:** Drove the follow-up questions below.

### Follow-up: blunder/mistake icon interactivity

| Option | Description | Selected |
|--------|-------------|----------|
| Click jumps to ply | Icon clickable, navigates board + highlight to the flaw ply | |
| Visual marker only | Non-interactive marker; normal row-click navigation applies | |
| Try to expand PV | Click attempts tactic-lines fetch like pill chips | |

**User's choice:** Free text — no special treatment for the icon; clicking a move in the move list
navigates to that move and updates the eval-chart slider (normal node-click). Icon is purely visual.

### Follow-up: blunder/mistake distinction + inaccuracy

| Option | Description | Selected |
|--------|-------------|----------|
| Distinct blunder/mistake, no inaccuracy | Two treatments; inaccuracies get no marker | ✓ |
| One generic flaw icon, no inaccuracy | Single icon for both; no inaccuracy marker | |
| Distinct, incl. inaccuracy | Three tiers visually distinguished | |

**User's choice:** Distinct blunder/mistake, no inaccuracy

---

## Un-analyzed Analyze button

| Option | Description | Selected |
|--------|-------------|----------|
| Load PGN, no chart | Un-analyzed games open the new button into free-play over the real game | |
| Only show on analyzed games | Page-opening button suppressed for un-analyzed games | ✓ (refined) |

**User's choice:** Free text — un-analyzed games already have a `Cpu`-icon Analyze button that
requests full game analysis (existing `NoAnalysisState`); the NEW page-opening Analyze button uses
a **Search** icon and is shown only once the game is analyzed.
**Notes:** Corrects the UI-SPEC ("always enabled", `Activity` icon, free-play fallback). Grounded
against `NoAnalysisState.tsx` (`btn-analyze-game-{gameId}`) and `LibraryGameCard` (`analysis_state`).

---

## On-demand PV fetch UX

| Option | Description | Selected |
|--------|-------------|----------|
| Spinner on chip | Inline spinner/disabled-pressed during fetch, then expand; revert + error copy on failure | |
| You decide | Planner picks affordance, following existing loading/isError patterns | ✓ |

**User's choice:** You decide

---

## Claude's Discretion

- Exact loading/error affordance for the on-demand `tactic-lines` PV fetch (must show a loading
  state; error/empty follows CLAUDE.md `isError` pattern + existing "Tactic line not available"
  copy).
- Specific blunder vs mistake icon glyph/color (two distinct treatments, colors from `theme.ts`).

## Deferred Ideas

None — discussion stayed within phase scope.
