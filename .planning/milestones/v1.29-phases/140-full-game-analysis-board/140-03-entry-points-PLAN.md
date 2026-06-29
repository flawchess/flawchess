---
phase: 140-full-game-analysis-board
plan: 03
type: execute
wave: 3
depends_on: [140-01, 140-02]
files_modified:
  - frontend/src/components/results/LibraryGameCard.tsx
  - frontend/src/components/library/FlawCard.tsx
autonomous: true
requirements: [SC-1, SC-2, SC-5, D-4]
must_haves:
  truths:
    - "An analyzed game card shows exactly one Analyze button (Search icon, brand-outline) and no Explore or Analyze-position button"
    - "The game-card Analyze button opens /analysis?game_id={game_id}&ply={hoverPly ?? lastEvalPly ?? 0} via buildGameAnalysisUrl, on analyzed games only"
    - "Un-analyzed games still show the existing Cpu-icon Analyze button in NoAnalysisState (unchanged)"
    - "A flaw card shows exactly one Analyze button opening /analysis?game_id={flaw.game_id}&ply={flaw.ply}; the Explore + Game pair is gone"
    - "The FlawCard Game modal code path (Dialog/Drawer + inline LibraryGameCard + useLibraryGame + related imports/state/JSX) is deleted entirely"
    - "npm run knip, lint, frontend tests, and npx tsc -b all pass with no dead exports or unused dependencies"
  artifacts:
    - path: "frontend/src/components/results/LibraryGameCard.tsx"
      provides: "Unified Search-icon Analyze button (desktop + mobile), Explore/Analyze-position removed"
      contains: "btn-library-game-analyze"
    - path: "frontend/src/components/library/FlawCard.tsx"
      provides: "Unified Analyze button; Game modal path deleted"
      contains: "btn-flaw-analyze"
  key_links:
    - from: "frontend/src/components/results/LibraryGameCard.tsx"
      to: "frontend/src/lib/analysisUrl.ts"
      via: "buildGameAnalysisUrl(game.game_id, hoverPly ?? lastEvalPly ?? 0)"
      pattern: "buildGameAnalysisUrl"
    - from: "frontend/src/components/library/FlawCard.tsx"
      to: "frontend/src/lib/analysisUrl.ts"
      via: "buildGameAnalysisUrl(flaw.game_id, flaw.ply)"
      pattern: "buildGameAnalysisUrl"
---

<objective>
Collapse the two card entry points into a single Analyze button each, and delete the FlawCard Game
modal entirely. The game card (analyzed only — D-06) and the flaw card (D-09) both navigate to the
new /analysis?game_id&ply game mode shipped in 140-02. Close the phase with the full frontend gate.

Purpose: Deliver SC-1 (single Analyze button, old pairs + inline modal gone) and the button half of
SC-2, plus the SC-5 green-gate. Output: two simplified cards and a passing knip/lint/test/tsc gate.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/140-full-game-analysis-board/140-CONTEXT.md
@.planning/phases/140-full-game-analysis-board/140-RESEARCH.md
@.planning/phases/140-full-game-analysis-board/140-PATTERNS.md
@.planning/phases/140-full-game-analysis-board/140-UI-SPEC.md
@.planning/phases/140-full-game-analysis-board/140-01-SUMMARY.md
</context>

## Artifacts this phase produces (this plan)

New symbols introduced by this plan (excluded from downstream drift verification):
- testids `btn-library-game-analyze`, `btn-flaw-analyze`
- depends on 140-01 symbol `buildGameAnalysisUrl`

<tasks>

<task type="auto">
  <name>Task 1: LibraryGameCard — unified Search-icon Analyze button (desktop + mobile), drop Explore + Analyze-position</name>
  <files>frontend/src/components/results/LibraryGameCard.tsx</files>
  <read_first>
    - frontend/src/components/results/LibraryGameCard.tsx (Activity import line 4; isAnalyzed gate ~232; hoverPly ~218; lastEvalPly 249-257; renderDesktopExploreButton 896-963 incl. Button asChild + Link idiom 903-919; mobile button row 1027-1092; renderDesktopExploreButton call ~1188)
    - 140-CONTEXT.md D-06, D-07, D-08 (Search icon NOT Activity; analyzed-only; UI-SPEC testid/copy still apply)
    - 140-UI-SPEC.md "Unified Analyze button" (LibraryGameCard replacement) + Testid Map; PATTERNS.md LibraryGameCard section
  </read_first>
  <action>
    Replace BOTH the Explore button and the Analyze-position button — in renderDesktopExploreButton()
    AND in the mobile `<div className="md:hidden flex gap-2">` row (CLAUDE.md mobile-parity: apply the
    change to both renderers independently) — with a SINGLE unified Analyze button, gated on
    game.analysis_state === 'analyzed' (D-06; reuse the existing isAnalyzed derivation). Use the existing
    Button asChild + Link idiom: variant="brand-outline" (secondary — never hand-roll colors), size
    default (h-8), data-testid="btn-library-game-analyze", aria-label="Analyze game", label "Analyze",
    Search icon (lucide, Search className="h-4 w-4 mr-1"). Per D-06/D-08 the icon is Search, NOT Activity,
    and there is NO free-play fallback for un-analyzed games. Navigation:
    buildGameAnalysisUrl(game.game_id, hoverPly ?? lastEvalPly ?? 0) imported from @/lib/analysisUrl —
    hoverPly and lastEvalPly are already in scope at the button render site (no new state).

    D-07: do NOT touch NoAnalysisState.tsx — the un-analyzed Cpu-icon Analyze button
    (btn-analyze-game-{gameId}) stays exactly as-is; the new Analyze button shows only on analyzed cards,
    so the two never coexist.

    Remove the now-unused Activity icon import (D-06 — the button uses Search). Remove the old
    game-card-btn-explore and game-card-btn-analyze-position buttons and any imports/helpers that become
    dead as a result (knip will flag leftovers). Preserve all other card layout.
  </action>
  <verify>
    <automated>cd frontend && npx tsc -b && npm run lint && npm run knip && npm test -- --run LibraryGameCard</automated>
  </verify>
  <acceptance_criteria>
    - Exactly one Analyze button per analyzed card with data-testid `btn-library-game-analyze`, Search icon, brand-outline, aria-label "Analyze game"
    - Both desktop (renderDesktopExploreButton) and mobile rows updated; `game-card-btn-explore` and `game-card-btn-analyze-position` testids no longer present
    - Button shown only when `game.analysis_state === 'analyzed'`; NoAnalysisState.tsx unchanged (D-07)
    - URL built via `buildGameAnalysisUrl(game.game_id, hoverPly ?? lastEvalPly ?? 0)`
    - `Activity` import removed; `npx tsc -b`, `npm run lint`, `npm run knip` all clean (no dead export)
    - Any existing LibraryGameCard test referencing the removed `game-card-btn-explore` / `game-card-btn-analyze-position` testids is updated in THIS task (so the tree is never left in an intermediate red-test state); `npm test -- --run LibraryGameCard` green before T1 is done
  </acceptance_criteria>
  <done>LibraryGameCard exposes one Search-icon Analyze button on analyzed games (desktop + mobile); Explore/Analyze-position and the Activity import are gone.</done>
</task>

<task type="auto">
  <name>Task 2: FlawCard — unified Analyze button + full Game-modal deletion; close phase gate</name>
  <files>frontend/src/components/library/FlawCard.tsx</files>
  <read_first>
    - frontend/src/components/library/FlawCard.tsx (open state 141; useIsMobile 142; useFlawFilterStore 162; useLibraryGame 163; isTagged/ori 144-157; buttonRow 257-293; gameBody 477-493; gameCloseLabel/gameView 495-538; {gameView} ref 591; imports 11-44; MOBILE_BREAKPOINT_PX/useIsMobile 59-78)
    - 140-CONTEXT.md D-09 (delete entire Game modal path) + D-06 copy/testid
    - 140-RESEARCH.md "FlawCard.tsx — Unified Analyze + Modal Deletion" (exact delete list, lines 386-432); 140-UI-SPEC.md "FlawCard replacement"; PATTERNS.md FlawCard section
  </read_first>
  <action>
    Replace the buttonRow (Explore + Game) with a SINGLE Analyze button: Button asChild
    variant="brand-outline" className="flex-1", Link to buildGameAnalysisUrl(flaw.game_id, flaw.ply),
    data-testid="btn-flaw-analyze", aria-label="Analyze game", Search icon (h-4 w-4 mr-1), label
    "Analyze". Import buildGameAnalysisUrl from @/lib/analysisUrl.

    Delete the entire Game modal path (D-09): the open useState (141), useIsMobile (142) +
    MOBILE_BREAKPOINT_PX/useIsMobile helper (59-78), useFlawFilterStore (162) and useLibraryGame call
    (163), the isTagged check + ori derivation (144-157, no longer feeding any button), and the
    gameBody / gameCloseLabel / gameView JSX (477-538) plus the {gameView} reference (591). Remove the
    now-unused imports: Swords, Loader2, X (lucide); Dialog/DialogContent/DialogTitle; Drawer/
    DrawerContent/DrawerHeader/DrawerTitle/DrawerClose; LoadError; LibraryGameCard; useLibraryGame;
    useFlawFilterStore. Keep Search (lucide) and add buildGameAnalysisUrl. Before deleting
    useFlawFilterStore/ori, confirm they are not referenced elsewhere in the file (RESEARCH.md confirms
    ori derives from flaw + tacticOrientation prop, not flawFilter) — let knip/tsc catch any miss.

    The flaw's missed/allowed tag is now seen in the move list after the game loads (no auto-expand,
    locked decision) — the card no longer renders an inline game view.

    Phase-close gate: after the edits, run the full frontend gate and resolve every issue:
    cd frontend && npm run lint && npm test -- --run && npx tsc -b && npm run knip — all green (SC-5).
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npm test -- --run && npx tsc -b && npm run knip</automated>
  </verify>
  <acceptance_criteria>
    - FlawCard renders exactly one Analyze button, data-testid `btn-flaw-analyze`, opening `buildGameAnalysisUrl(flaw.game_id, flaw.ply)`; the old Explore + Game buttons are gone
    - `open` state, `useIsMobile`/MOBILE_BREAKPOINT_PX, `useLibraryGame`, `useFlawFilterStore`, and the gameBody/gameView JSX are all removed; no Dialog/Drawer/LoadError/LibraryGameCard imports remain
    - `grep -c "useLibraryGame" frontend/src/components/library/FlawCard.tsx` returns 0
    - `npm run lint`, `npm test -- --run`, `npx tsc -b`, and `npm run knip` are all green (no dead export, no unused dependency)
  </acceptance_criteria>
  <done>FlawCard has one Analyze button and zero Game-modal code; the full frontend gate (lint + test + tsc + knip) passes.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| card props → Link href | game.game_id / flaw.game_id / flaw.ply / hoverPly / lastEvalPly fed into buildGameAnalysisUrl |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-140-03a | Tampering | buildGameAnalysisUrl inputs | mitigate | Inputs are numeric fields from typed GameFlawCard/FlawMarker; the consumer (140-02) re-validates ply/game_id with NaN + bounds guards |
| T-140-03b | Information Disclosure | deleted Game modal leaving dead code/imports | mitigate | knip + tsc gate fails the build on any leftover dead export or unused import (D-09 completeness check) |
| T-140-SC | Tampering | npm/pip/cargo installs | accept | No new package installs in this plan |
</threat_model>

<verification>
- `cd frontend && npm run lint && npm test -- --run && npx tsc -b && npm run knip` — ALL green (phase-close gate, SC-5)
- Manual UAT (per 140-VALIDATION.md): analyzed game card shows one Search-icon Analyze; un-analyzed card still shows the Cpu Analyze; flaw card shows one Analyze; no Game modal opens anywhere; clicking Analyze loads the full game at the carried ply
</verification>

<success_criteria>
- SC-1: one Analyze button per game card + flaw card; Explore/Analyze-position + Explore/Game pairs and the inline Game modal code path gone
- SC-2 (button half): Analyze opens /analysis?game_id=X&ply=Y with the carried ply (slider ply for game card, flaw.ply for flaw card)
- SC-5: no backend change (D-4); knip + lint + tests + tsc green
</success_criteria>

<output>
Create `.planning/phases/140-full-game-analysis-board/140-03-SUMMARY.md` when done
</output>
