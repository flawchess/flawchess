---
id: SEED-261122-j9p
status: dormant
planted: 2026-11-22
planted_during: /gsd-explore session during Phase 259 (facepalm first-principles refit)
trigger_when: after Phase 259 (facepalm first-principles refit) is merged to main, when planning the next Library/UI polish work
scope: small to medium. Frontend only, one phase. No backend or API change if the filter button shares the slider state
---

# SEED-261122-j9p: Facepalm as a first-class move quality (game card row, eval chart dot, Flaws filter button)

## Why This Matters

GM Noel Studer's criticism of the chess.com and lichess blunder definition is that the blunders
worth a player's attention are the ones they should have seen and avoided at their level. FlawChess
already scores that (the facepalm score) and marks those moves with a dedicated ??? icon, but the
game card's move quality table and the Flaws filter buttons still treat every blunder alike. Giving
facepalms their own slot lets a player go straight to the preventable blunders, and compare both
sides on them like on every other move quality.

## Decisions locked in the explore session (2026-11-22)

1. **Game card table (`MoveStats`, used by `LibraryGameCard` and `AnalysisTagsPanel`)**: add an
   8th two-sided row "Facepalm" with the ??? icon, as a main category like the other rows. The
   owner wants a two-sided comparison, not a user-only treatment, and rejected a nested "of which"
   presentation. Precedent: Gem and Great are already disjoint peers of Best (each ply has a single
   `best_move_tier`).
   - A facepalm is a blunder with facepalm score >= `FACEPALM_HIGH_CUTOFF` (70%), via
     `isFacepalmBlunder`. An unscored blunder is never a facepalm.
   - The Facepalm cell cycles through the facepalm plies, like the other cells.
2. **Mobile compact row**: drop Inaccuracy and Good, add Facepalm. Cells: Gem, Great, Best,
   Mistake, Blunder, Facepalm, chevron (7 cells, one fewer than today). The expanded table keeps
   all 8 rows.
3. **Terminology**: "Blunder" keeps its Lichess meaning (facepalm blunders included) across the
   app. No blanket copy change. Distinguish facepalms only in specific contexts where it is useful.
4. **Eval chart**: facepalm blunders get a dark red dot, visually distinct from the regular blunder
   dot (`SEV_BLUNDER`). Check whether the darker facepalm tone of the Flaws Timeline band can be
   reused before adding a new theme constant.
5. **Tags sidepanel, Flaws section**: add a "Facepalm" button next to Blunders and Mistakes. The
   existing Facepalm Score range filter stays.

## Open for discuss-phase

- **Does the card's Blunder row exclude facepalms?** Not answered by the owner. Claude's
  recommendation: split in the card only (Blunder row = ?? moves, Facepalm row = ??? moves),
  consistent with Best vs Gem/Great and with the markers on the chart, and state in the popover
  that Blunder plus Facepalm equals the Lichess blunder count. The alternative keeps the full
  Lichess count in the Blunder row with Facepalm as an overlapping subset, at the cost of counting
  a facepalm in two rows and the Blunder cell cycling through ??? moves too.
- **Filter button state.** Claude's recommendation, not confirmed by the owner: the Facepalm button
  is a shortcut onto the existing slider state, selected exactly when the range equals the High
  preset (70 to 100%). No new API parameter, no contradictory states (a separate flag plus the
  slider at Low would give an empty list). The Blunders button stays "all blunders".
- **Interplay with the Mistakes toggle.** A narrowed facepalm range already forces blunders-only,
  so Facepalm plus Mistakes selected together needs a visible resolution.
- **Filter emphasis in the card** (`outlinedRef`): which cells are outlined when the Blunders
  filter or the Facepalm button is active.

## When to Surface

**Trigger:** after Phase 259 (facepalm first-principles refit) is merged to main, when planning
the next Library/UI polish work.

Phase 259 changes the score model, so the 70% cut and which blunders count as facepalms should be
settled before the UI promotes them.

## Scope Estimate

**Small to medium**, frontend only, one phase. Touches the `MoveStatCategory` type and the count
derivation, the table and compact row, the eval chart dot color, the filter control, the
`MoveStatsInfo` popover (category definitions and the "match Lichess" sentence), and tests.

## Breadcrumbs

- `frontend/src/components/library/MoveStats.tsx` (7-row table, compact row, `MoveStatsInfo`)
- `frontend/src/lib/moveStatsCounts.ts` (`MoveStatCategory`, `severityCountsBySide`)
- `frontend/src/lib/facepalm.ts` (`isFacepalmBlunder`, `FACEPALM_HIGH_CUTOFF`, presets)
- `frontend/src/components/results/LibraryGameCard.tsx` (`facepalmPlies`, cell cycling)
- `frontend/src/components/library/EvalChart.tsx` (flaw dot color, `SEV_BLUNDER`)
- `frontend/src/components/filters/FlawFilterControl.tsx` (Flaws severity buttons)
- `frontend/src/components/filters/FacepalmFilter.tsx` (score range slider and presets)
- `frontend/src/lib/theme.ts` (severity colors)
- Related seed: `SEED-261121-tau-facepalm-first-principles-refit.md`

## Notes

Captured from a `/gsd-explore` session. No external research was involved.
