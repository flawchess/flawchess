---
id: SEED-208
status: dormant
planted: 2026-11-05
planted_during: Phase 244 era, /gsd-explore session on chess.com Game Review's Explain/Best/Next bar
trigger_when: owner plans the next Analysis-page / game-review UX phase (owner wants this planned as its own phase)
scope: small-medium; one frontend phase (UI-SPEC + 1-2 plans). Reuses the tactic-chip line machinery and the existing tactic-lines endpoint; no backend or schema change expected.
priority: high user value per effort; brings chess.com's paid-tier-feeling guided review to every flaw
---

# SEED-208: Analysis page, contextual Explain bar for flaws

## Why This Matters

chess.com Game Review has a three-button bar (Explain / Best / Next) under the
move list that makes reviewing a game feel guided: one click shows the line that
explains a bad move, then you step through it. FlawChess already stores both
lines for every flaw (the better line and the refutation), but they are only
reachable through tactic motif chips, and most flaws carry no motif. An Explain
button exposes those lines for every flaw, both sides, with no new data.

## Decisions (LOCKED in the explore session)

1. **Single Explain button.** No "Best" button: with the direction rule below it
   duplicated Explain's first step on the user's own flaws, and on opponent flaws
   it showed the opponent's improvement, which teaches the user less than the
   punishment. No "Next" button: the existing "Jump to next key moment"
   (`useFastForward`) already does that.
2. **No coach prose, no LLM.** Pure guided stepper over stored PVs.
3. **Placement: contextual bar.** Under the move list on desktop, directly above
   the mobile footer on mobile (the footer Reset/Back/Forward/Jump/Flip is at its
   5-column limit on a 360px phone). Shown only when the current node is a flaw
   ply or inside that flaw's Explain line.
4. **Scope: every flaw, including inaccuracies, of both sides**, with or without a
   tactic motif.
5. **Direction rule (same semantics as the tactic motif badges):**
   - User's own flaw: open the MISSED PV (the best line instead of the mistake),
     forking at ply-1 (one move back).
   - Opponent's flaw: open the ALLOWED PV (the refutation / how to punish it),
     forking at the flaw ply (no step back).
6. **Explain plays the first move of the line immediately** (instant feedback,
   like chess.com), rather than parking at the fork node the way a chip does.
7. **Navigation inside the line uses the normal Back/Forward controls.** No
   separate stepper buttons.
8. **Explain turns into "Got it"** while the board is in the line. Got it closes
   that line (`deleteSubtree`) and returns the board to the flaw move on the main
   line.
9. **Leaving the line without Got it keeps it open** (move-list click, Jump,
   eval-chart scrub), like tactic chips. The bar shows Explain for wherever the
   board is, and Got it again on re-entry.

## Reuse (why no backend work is expected)

- `GET /library/flaws/{game_id}/{ply}/tactic-lines`
  (`app/repositories/library_repository.py:2266`) returns `missed_moves` and
  `allowed_moves` for ANY `game_flaws` row; motif fields are just null when there
  is no pattern. Lichess-imported games get the same full FlawChess analysis, so
  PVs exist for both platforms.
- `pages/Analysis.tsx`: `handlePvChipClick(nodeId, {ply, orientation})`,
  `openLines` keyed by `flawKey(ply, orientation)`, the `pendingFlaw` graft
  effect, `deleteSubtree`, `findFocusedFlaw` / `focusedPvLine`.
- `hooks/useAnalysisBoard.ts:352`: `goForward` at a fork node already prefers the
  PV child, so Forward steps into the open line instead of the game.
- A motif flaw's chip and Explain open the SAME line key, so the two entry points
  never create duplicate sidelines.
- `useFastForward` stays the "Next" equivalent.

## chess.com Reference (observed live 2026-11-05, game 186528587700, owner played black)

- Explain grafts a line into the move list, plays its first move, and swaps the
  bar to back / forward / "Got it!". Got it removes the sideline again. The coach
  bubble showed no prose on this account (per-move coach text is Diamond-only).
- Best grafts the best move one ply back, shows a star badge and the eval, and
  swaps the bar to a single "Resume" button. That sideline persists after Resume.
- Next jumps (no animation) to the next key move, skipping ordinary moves.
- Explain was not offered on the owner's own mistake 21...Rxc3?, and was offered
  on a plain "best" move (11...O-O). Rule unknown.
- Explain direction was NOT consistent by side: opponent blunder 23.Rc5?? showed
  the forward refutation (Ne4 forks rook and queen), while opponent mistake
  22.Rxc3? went back to the better line 22.Qxc3 (re-tested from a fresh page
  load). Hypotheses (tactic-driven vs severity-driven) unverified with this
  sample. FlawChess deliberately uses the simpler by-side rule in decision 5.

## Open Questions for the Phase

- Bar visuals and copy (UI-SPEC): button label/icon, whether the bar shows the
  severity + move ("Rc5 is a blunder"), dark-theme tokens, testids.
- Umami event names for Explain and Got it.
- Behaviour when a flaw has a null PV (or the final ply): hide Explain, or
  disable it with a tooltip.
- Interaction with the existing tactic-chip auto-open on deep links
  (`tacticOrientationAtPly`, missed-over-allowed precedence for the user's flaw).
- Free-play / what-if moves (live `useLiveMoveFlaw` grades) are out of scope
  unless the phase decides otherwise: they have no stored PV.

## Breadcrumbs

- `frontend/src/pages/Analysis.tsx` (handlePvChipClick ~1776, findFocusedFlaw ~292, mobile footer ~2578)
- `frontend/src/components/analysis/AnalysisTabs.tsx` (BoardControls wrapper, mobile footer)
- `frontend/src/components/board/BoardControls.tsx` (labelled 5-column footer)
- `frontend/src/hooks/useAnalysisBoard.ts` (goForward PV preference, insertPvLine, deleteSubtree)
- `frontend/src/hooks/useLibrary.ts` (`useTacticLines`)
- `frontend/src/lib/tacticOrientation.ts`
- `frontend/src/hooks/useFastForward.ts` (existing Next equivalent)
- `app/repositories/library_repository.py` (`fetch_tactic_lines`)
