---
phase: 140-full-game-analysis-board
plan: 02
type: execute
wave: 2
depends_on: [140-01]
files_modified:
  - frontend/src/components/analysis/VariationTree.tsx
  - frontend/src/components/analysis/VariationTree.test.tsx
  - frontend/src/pages/Analysis.tsx
autonomous: true
requirements: [SC-2, SC-3, SC-4, SC-5, D-4]
must_haves:
  truths:
    - "Loading /analysis?game_id=X&ply=Y on an analyzed game loads the full game line (ply 0 to end) and parks the board at ply Y"
    - "On desktop the eval chart with slider sits directly below the board+EvalBar; the move list height is matched to the board; BoardControls render below the move list"
    - "Clicking a main-line move syncs the board, the move-list highlight, and the eval-chart slider position"
    - "While a sideline is active the eval-chart slider is disabled/dimmed and parks at the fork ply; it re-enables on return to the main line"
    - "Flaw plies show inline missed/allowed pill chips in the desktop move list; clicking a chip fetches its stored PV and unfolds it as a Level-1 sideline at the fork"
    - "A user move within an expanded PV renders a Level-2 sub-sideline (two nesting levels), and TacticModeOverlay activates contextually for the active PV line"
    - "Non-tactic blunder vs mistake flaw plies show two visually distinct icon markers; inaccuracies show no marker; the icon has no click behavior beyond normal node navigation"
    - "Mobile renders the stacked equivalent: Board+EvalBar, EvalChart, overlay, engine, move list, controls"
  artifacts:
    - path: "frontend/src/components/analysis/VariationTree.tsx"
      provides: "Two-level nesting, inline flaw pill chips, blunder/mistake markers, new props"
      contains: "variation-pv-section"
    - path: "frontend/src/pages/Analysis.tsx"
      provides: "isGameMode fetch + board seeding + contextual overlay + layout relocation + slider parking"
      contains: "isGameMode"
    - path: "frontend/src/components/analysis/VariationTree.test.tsx"
      provides: "Two-level nesting + level-resolution render tests"
      contains: "variation-subpv-section"
  key_links:
    - from: "frontend/src/pages/Analysis.tsx"
      to: "frontend/src/hooks/useLibrary.ts"
      via: "useLibraryGame(gameId) for the game-by-id fetch (existing endpoint, no backend change — D-4)"
      pattern: "useLibraryGame"
    - from: "frontend/src/pages/Analysis.tsx"
      to: "frontend/src/hooks/useAnalysisBoard.ts"
      via: "insertPvLine/clearPvLine/isOnPvLine + pvLine drive sideline state"
      pattern: "insertPvLine|clearPvLine|isOnPvLine|pvLine"
    - from: "frontend/src/components/analysis/VariationTree.tsx"
      to: "frontend/src/lib/theme.ts"
      via: "imports TAC_MISSED_BORDER/TAC_ALLOWED_BORDER + SEV_ colors via BlunderIcon/MistakeIcon"
      pattern: "TAC_MISSED_BORDER"
    - from: "frontend/src/pages/Analysis.tsx"
      to: "frontend/src/components/library/EvalChart.tsx"
      via: "sliderDisabled (slider parking) + sliderTestId=analysis-eval-chart-slider + onPlyChange syncs board"
      pattern: "sliderDisabled"
---

<objective>
Rewire the board page for full-game analysis. Two cohesive subsystems: (1) VariationTree gains
two-level nesting, inline missed/allowed pill chips with on-demand PV fetch, and distinct
blunder/mistake markers; (2) Analysis.tsx gains the new ?game_id&ply game mode — game-by-id fetch,
board seeding, contextual TacticModeOverlay, the chess.com-style layout relocation (eval chart
below board, controls below move list), and slider parking.

Purpose: Deliver SC-2, SC-3, SC-4, and the mobile-stack half of SC-5. This is the heaviest plan;
the two tasks are split along the component/page seam so each reads and mutates one large file.
Output: a working /analysis?game_id=X&ply=Y page with inline-chip-driven PV sidelines and a
parked eval slider.
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
@.planning/notes/analysis-board-fullgame-refinement.md
@.planning/phases/140-full-game-analysis-board/140-01-SUMMARY.md
</context>

## Artifacts this phase produces (this plan)

New symbols introduced by this plan (excluded from downstream drift verification):
- VariationTree props: `pvLine`, `flawMarkerByNodeId`, `onPvChipClick`, `activePvNodeId`
- new testids: `analysis-eval-chart`, `analysis-eval-chart-slider`, `variation-pv-section`,
  `variation-subpv-section`, `flaw-inline-tag-missed-{nodeId}`, `flaw-inline-tag-allowed-{nodeId}`
- Analysis.tsx state/derivations: `activePvFlaw`, `isGameMode`
- depends on 140-01 symbols: `insertPvLine`, `clearPvLine`, `isOnPvLine`, `pvLine`,
  EvalChart `sliderTestId`/`sliderDisabled`, `TAC_MISSED_BORDER`

<tasks>

<task type="auto">
  <name>Task 1: VariationTree two-level nesting + inline flaw chips + blunder/mistake markers</name>
  <files>frontend/src/components/analysis/VariationTree.tsx, frontend/src/components/analysis/VariationTree.test.tsx</files>
  <read_first>
    - frontend/src/components/analysis/VariationTree.tsx (VariationTreeProps 21-39; buildVariationChain 53-70; DesktopTree 231-344 incl. single ml-8 block 333-340; MobileTree 141-227 paren pattern; renderMoveButton 276-301; responsive split 358-367)
    - frontend/src/components/library/TacticMotifChip.tsx (chip color/border + ACTIVE_FILTER_RING_CLASS pattern — PATTERNS.md lines 230-262)
    - frontend/src/components/icons/SeverityGlyphIcon.tsx (BlunderIcon / MistakeIcon — already exist)
    - frontend/src/lib/theme.ts (TAC_MISSED/TAC_MISSED_BORDER/TAC_ALLOWED/TAC_ALLOWED_BORDER/TAC_*_BG, SEV_BLUNDER, SEV_MISTAKE, ACTIVE_FILTER_RING_CLASS)
    - frontend/src/hooks/useLibrary.ts (useTacticLines signature; FlawMarker shape) and frontend/src/types/library.ts (FlawMarker, FlawSeverity)
    - 140-RESEARCH.md "Hardest Part 1"; 140-UI-SPEC.md "Inline Flaw Tag Chip" + "VariationTree — two-level nesting" + Testid Map + Copywriting Contract; CONTEXT.md D-01..D-04
    - PATTERNS.md VariationTree + inline-chip + Tests sections
  </read_first>
  <action>
    Extend VariationTreeProps with the four new optional props (per RESEARCH.md / PATTERNS.md):
    pvLine?: NodeId[]; flawMarkerByNodeId?: Map&lt;NodeId, { missedMotif: string | null; allowedMotif:
    string | null; severity?: FlawSeverity }&gt;; onPvChipClick?: (nodeId: NodeId, flaw: { ply: number;
    orientation: 'missed' | 'allowed' }) =&gt; void; activePvNodeId?: NodeId | null. All optional so
    existing callers stay valid. (The `severity` field carries the per-node flaw severity so the tree
    can render BlunderIcon/MistakeIcon for non-tactic flaws per D-02 — import `FlawSeverity` from
    `@/types/library`.)

    Extend VariationChain to add level: 0 | 1 | 2 and extend buildVariationChain to take pvLine and
    resolve the level: 0 when currentNodeId is on mainLine (or null), 1 when the backward parentId walk
    reaches a mainLine node without passing a pvLine node (or currentNodeId is itself in pvLine), 2 when
    the walk passes a pvLine node before reaching mainLine (a user fork within the PV — D-01 ephemeral
    sub-sideline). Reuse the existing reversed-walk idiom; guard every node lookup.

    DesktopTree: promote the single ml-8 variation block to a Level-1 PV block wrapped in
    &lt;div data-testid="variation-pv-section" className="ml-8 border-l-2 border-muted/40 pl-2"&gt;, and nest
    a Level-2 block &lt;div data-testid="variation-subpv-section" className="ml-16 border-l-2
    border-muted/30 pl-2"&gt; inside it when level === 2. Level-1/2 move text is text-muted-foreground
    (level-2 adds opacity-80); active node keeps bg-primary text-primary-foreground at every level;
    main-line moves after the fork stay dimmed (text-muted-foreground), matching existing variation
    coloring. Row min-h-[28px] at all levels. Apply max-h-[480px] overflow-y-auto to match board height
    (UI-SPEC).

    Inline flaw pill chip (rendered inside renderMoveButton as a SIBLING span/button to the SAN
    &lt;button&gt;, NOT inside it — only for mainLine nodes whose flawMarkerByNodeId entry has a tactic
    motif): pill is inline-flex items-center h-5 px-1.5 rounded-full border, text-sm font-medium, label
    "Missed" (missedMotif set) or "Allowed" (allowedMotif set). Colors via inline style from theme.ts:
    missed uses TAC_MISSED text + TAC_MISSED_BG background + TAC_MISSED_BORDER border; allowed uses
    TAC_ALLOWED / TAC_ALLOWED_BG / TAC_ALLOWED_BORDER. When nodeId === activePvNodeId add
    ACTIVE_FILTER_RING_CLASS. data-testid flaw-inline-tag-missed-{nodeId} or
    flaw-inline-tag-allowed-{nodeId}. aria-label "Missed tactic: {motif}. Click to expand tactic line."
    / "Allowed tactic: {motif}. Click to expand tactic line." (active variant ends "Click to collapse
    tactic line."). On click call onPvChipClick(nodeId, { ply, orientation }). The on-demand
    tactic-lines fetch is owned by Analysis.tsx (Task 2); this chip shows a loading affordance while
    that fetch is pending and surfaces the exact copy "Tactic line not available for this flaw." on the
    isError/empty case (CLAUDE.md isError pattern) — drive both from props passed by Task 2 (e.g. a
    pending/error flag keyed to activePvNodeId). Never hard-code oklch/hex; theme.ts only.

    D-02 non-tactic markers: for mainLine nodes whose FlawMarker severity is 'blunder' or 'mistake'
    and has NO tactic motif, render a distinct marker using the existing BlunderIcon vs MistakeIcon
    (two visually distinct treatments, colored from SEV_BLUNDER / SEV_MISTAKE). D-03: inaccuracy
    severity gets NO marker. D-04: this icon has no click behavior — the row click navigates the board
    normally; the icon is presentational only (aria-hidden, with the severity conveyed via the row's
    existing aria where present).

    MobileTree: extend the single-paren Level-1 pattern to double-paren `(( ... ))` for Level-2. No
    inline pill chips on mobile (UI-SPEC) — mobile tactic access stays via the TacticModeOverlay header.
    Apply the blunder/mistake marker on mobile rows too (mobile-parity).

    Guard every new mainLine[i]/pvLine[i] index access with the `const nodeId = arr[i]; if (nodeId !==
    undefined)` template (L-8) — never a bare `arr[i]!` unless provably in-bounds. Keep DesktopTree /
    renderMoveButton within nesting (hard 4) / LOC limits; if a touched function already breaches them,
    extract a renderFlawChip / renderSeverityMarker helper rather than deepening it.

    Add VariationTree.test.tsx: render a tree with a pvLine and a level-2 fork node and assert
    buildVariationChain returns the right level; assert variation-pv-section renders for a level-1
    current node and variation-subpv-section renders for a level-2 current node; assert a
    flawMarkerByNodeId tactic entry renders flaw-inline-tag-missed-{nodeId}; assert a blunder/mistake
    severity entry renders the marker and an inaccuracy entry renders none.
  </action>
  <verify>
    <automated>cd frontend && npm test -- --run VariationTree && npx tsc -b</automated>
  </verify>
  <acceptance_criteria>
    - VariationTreeProps adds pvLine, flawMarkerByNodeId, onPvChipClick, activePvNodeId (all optional)
    - buildVariationChain returns level 0/1/2 correctly (covered by VariationTree.test.tsx)
    - DesktopTree renders `variation-pv-section` (ml-8) for Level-1 and nested `variation-subpv-section` (ml-16) for Level-2
    - Inline chip renders only on mainLine tactic-motif nodes, with testid `flaw-inline-tag-{missed|allowed}-{nodeId}`, label "Missed"/"Allowed", theme.ts colors, ring when active, and the specified aria-labels
    - On-demand fetch loading shows a chip loading affordance; error/empty shows exactly "Tactic line not available for this flaw."
    - Blunder and mistake render two distinct icon markers (SEV_BLUNDER/SEV_MISTAKE); inaccuracy renders none; marker has no onClick
    - MobileTree uses `(( ... ))` for Level-2 and shows no inline pill chips
    - No bare `mainLine[i]!`/`pvLine[i]!` except where provably in-bounds; `npx tsc -b` passes
    - VariationTree.test.tsx is green
  </acceptance_criteria>
  <done>VariationTree renders two nesting levels, inline missed/allowed chips, and distinct blunder/mistake markers; tests pass and typecheck is clean.</done>
</task>

<task type="auto">
  <name>Task 2: Analysis.tsx game mode — fetch, seeding, contextual overlay, layout relocation, slider parking</name>
  <files>frontend/src/pages/Analysis.tsx</files>
  <read_first>
    - frontend/src/pages/Analysis.tsx (URL parse 95-101; isTacticMode 95-144; useTacticLines 144; tacticPly 211; onMainLine 223; seeding effect 183-198; handleReset 356-358; board column + BoardControls 408-431; right column 434-485; overlay block 437-448)
    - frontend/src/hooks/useLibrary.ts (useLibraryGame 193-218; useTacticLines 228-240) and frontend/src/types/library.ts (GameFlawCard 58-92; FlawMarker)
    - frontend/src/components/library/EvalChart.tsx (props incl. new sliderTestId/sliderDisabled from 140-01) and frontend/src/components/board/BoardControls.tsx (presentational, infoSlot)
    - 140-RESEARCH.md "Hardest Part 2", "Hardest Part 3", "BoardControls Relocation", landmines L-1/L-2/L-3/L-5/L-8 + the two open-question resolutions; 140-UI-SPEC.md "Layout Contract" (desktop + mobile) + "EvalChart — relocated" + "Eval chart slider parked/dimmed"; CONTEXT.md D-01,D-04,D-05,D-09(context),D-4
    - 140-01-SUMMARY.md (exact insertPvLine/clearPvLine/isOnPvLine signatures + EvalChart prop names)
    - PATTERNS.md Analysis.tsx section
  </read_first>
  <action>
    Parse the new ply param with the existing NaN-guard idiom: plyRaw = searchParams.get('ply');
    initialPly = numeric-or-null; isGameMode = gameId != null && initialPly != null. L-2: isGameMode
    and isTacticMode are mutually exclusive (a URL cannot carry both ply and flaw_ply) — keep ALL
    existing isTacticMode-gated derivations exactly as-is; the backward-compat ?game_id&flaw_ply path
    is UNCHANGED. New logic gates on isGameMode.

    Fetch (D-4, no new endpoint): const { data: gameData, isError: gameError } =
    useLibraryGame(isGameMode ? gameId : null) — pass flawFilter undefined so the all-inclusive game
    is returned. This is an unconditional top-level hook call.

    Board seeding (L-1: loadMainLine resets the ENTIRE tree, so call it exactly ONCE on game-data
    arrival and NEVER on a chip click). Use the RESEARCH.md "Hardest Part 3" sequencing: one effect that
    calls loadMainLine(gameData.moves, STARTING_FEN) when isGameMode && gameData?.moves != null; and a
    SEPARATE effect watching mainLine.length > 0 that navigates to initialPly via the L-8 guard
    (`const nodeId = mainLine[initialPly ?? 0]; if (nodeId !== undefined) goToNode(nodeId)`), so it runs
    after the batched loadMainLine state lands. Guard against re-seeding (only seed once per game).

    Contextual TacticModeOverlay (L-3, Hardest Part 2): add state const [activePvFlaw, setActivePvFlaw]
    = useState&lt;{ ply: number; orientation: 'missed' | 'allowed' } | null&gt;(null). Add a SECOND
    unconditional useTacticLines call: useTacticLines(gameId, activePvFlaw?.ply ?? null, activePvFlaw !=
    null) — both useTacticLines calls stay at top level (hooks rules). The inline-chip onPvChipClick
    handler passed to VariationTree sets activePvFlaw (toggle off if the same chip is clicked again,
    calling clearPvLine). When the contextual tactic data arrives, insertPvLine(pvSans, forkNodeId) to
    graft the Level-1 PV at the clicked node and navigate to the fork; pass the chip pending/error flag
    down so VariationTree can show the loading/"Tactic line not available for this flaw." states.
    Resolve a single activeOverlayData/orientation merging the URL-tactic path and the contextual path;
    render TacticModeOverlay when either is active. For the contextual path: resolvedOrientation =
    activePvFlaw.orientation; onStoredLine = isOnPvLine(currentNodeId); currentPly = currentNodeId ===
    null ? 0 : pvLine.indexOf(currentNodeId) + 1; onMoveClick navigates pvLine[ply-1] with the L-8
    guard. Hide the overlay when activePvFlaw is null / the user returns to the main line.

    Pass flawMarkerByNodeId + activePvNodeId to VariationTree: build the Map&lt;NodeId, { missedMotif,
    allowedMotif, severity }&gt; from gameData.flaw_markers, keyed by the mainLine node at each flaw ply (L-8 guard
    on mainLine[ply]); activePvNodeId is the node whose chip is currently expanded (derive from
    activePvFlaw + mainLine). Also pass pvLine. Non-tactic blunder/mistake severities flow through the
    same Map so VariationTree renders the D-02 markers.

    Layout relocation (UI-SPEC Layout Contract): in the left board column, place the EvalChart with
    slider DIRECTLY BELOW the board+EvalBar row, wrapped in &lt;div data-testid="analysis-eval-chart"&gt;,
    passing gameId, evalSeries/flawMarkers/phaseTransitions/moves from gameData, heightClass="h-[120px]",
    initialPly, sliderTestId="analysis-eval-chart-slider", and the onPlyChange/onHoverPlyChange callback.
    Move BoardControls OUT of the board column to the BOTTOM of the right column, AFTER VariationTree
    (chess.com pattern); its infoSlot engine-toggle (btn-analysis-engine-toggle) moves with it unchanged.

    Slider parking (D-05): compute onMainLine for game mode (currentNodeId === null ||
    isOnMainLine(currentNodeId)); pass sliderDisabled={!onMainLine} to EvalChart so the slider dims +
    disables + parks at the fork while a sideline is active, re-enabling on return to main line. Open
    question resolved: wire the EvalChart onPlyChange/onHoverPlyChange to call goToNode ONLY when on the
    main line — when a sideline is active the slider is disabled/parked, so the callback must not
    navigate the board off the sideline. Main-line slider scrub syncs board + move-list highlight + slider
    (three-way).

    handleReset (L-5): add a game-mode branch that calls clearPvLine(), setActivePvFlaw(null), and
    navigates to the URL initialPly (`const nodeId = mainLine[initialPly ?? 0]; if (nodeId !== undefined)
    goToNode(nodeId)`) — resolved open question: Reset returns to the entry-point ply, not move 0. Leave
    the existing isTacticMode and default branches unchanged.

    Mobile (SC-5 stacked equivalent, UI-SPEC mobile order): Board+EvalBar, EvalChart+slider,
    TacticModeOverlay (when active), engine area, VariationTree (mobile), BoardControls. Keep the existing
    pb-20 md:pb-6 bottom padding. Apply the layout move to the mobile renderer too (mobile-parity).

    isError: render the exact copy "Failed to load game. Something went wrong. Please try again in a
    moment." on gameError (CLAUDE.md isError branch) — do not fall through to an empty "No moves yet"
    state. Watch function-size limits in Analysis.tsx; if a touched function breaches nesting/LOC, split
    along a seam (e.g. extract a useGameModeBoard data hook or a renderGameMode block) rather than
    deepening it.
  </action>
  <verify>
    <automated>cd frontend && npx tsc -b && npm run lint && npm test -- --run Analysis</automated>
  </verify>
  <acceptance_criteria>
    - isGameMode derived from game_id+ply with NaN guards; isTacticMode-gated logic and the ?game_id&flaw_ply path are unchanged (L-2)
    - useLibraryGame(isGameMode ? gameId : null) is the only data source (no new endpoint — D-4); two unconditional useTacticLines calls exist (L-3)
    - loadMainLine is called exactly once on game-data arrival (never on a chip click — L-1); a separate effect watching mainLine.length navigates to initialPly with the L-8 guard
    - EvalChart renders below the board+EvalBar wrapped in `analysis-eval-chart`, slider testid `analysis-eval-chart-slider`; BoardControls renders below VariationTree in the right column
    - sliderDisabled is true off the main line (slider dims/parks) and false on it; onPlyChange navigates the board only on the main line
    - Clicking an inline chip sets activePvFlaw, fetches the PV, and insertPvLine grafts a Level-1 sideline at the fork; clicking again collapses (clearPvLine); only one PV expanded at a time
    - TacticModeOverlay shows for both the URL-tactic and contextual paths and hides on return to main line
    - handleReset game-mode branch calls clearPvLine + setActivePvFlaw(null) + navigates to initialPly
    - gameError renders "Failed to load game. Something went wrong. Please try again in a moment."
    - Mobile stack order matches UI-SPEC; `npx tsc -b`, `npm run lint`, and `npm test -- --run Analysis` pass
  </acceptance_criteria>
  <done>/analysis?game_id=X&ply=Y loads the full game at ply Y with relocated eval chart + controls, inline-chip PV sidelines, contextual overlay, and a parking slider; typecheck/lint/tests green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| URL query string → Analysis.tsx | game_id, ply (game mode) and the unchanged flaw_ply/orientation/fen paths — all attacker-controllable |
| game-by-id response → render | server-provided SAN, motif strings, eval_series rendered in move list / chips |
| pvLine/mainLine index access → goToNode | array indices derived from ply / chip clicks |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-140-02a | Tampering | ply / game_id URL parse | mitigate | Number.isNaN guard yields null → isGameMode false; useLibraryGame gated on null so no fetch fires on garbage input |
| T-140-02b | Denial of Service | ply pointing outside mainLine (e.g. 9999) | mitigate | L-8 guard `const nodeId = mainLine[ply]; if (nodeId !== undefined) goToNode(nodeId)` — out-of-bounds returns undefined, navigation is a no-op (no crash, no off-by-one) |
| T-140-02c | Information Disclosure / XSS | server SAN/motif strings rendered in chips + move list | accept | React default JSX escaping; no dangerouslySetInnerHTML introduced — confirmed in review |
| T-140-02d | Denial of Service | insertPvLine on a stale/missing fork node | mitigate | insertPvLine (140-01) returns prev unchanged on missing forkNodeId; chip click only fires for rendered mainLine nodes |
| T-140-SC | Tampering | npm/pip/cargo installs | accept | No new package installs in this plan |
</threat_model>

<verification>
- `cd frontend && npx tsc -b && npm run lint && npm test -- --run` green
- Manual UAT (per 140-VALIDATION.md Manual-Only): load /analysis?game_id=X&ply=Y on an analyzed game with a tactic flaw — chip expands PV as indented sideline, board parks at fork, overlay appears; fork a board move inside the PV → ml-16 sub-sideline; enter a sideline → slider dims with "Return to main game line to scrub", return → re-enabled; view at <1024px → stack order Board+EvalBar → EvalChart → overlay → engine → move list → controls
</verification>

<success_criteria>
- SC-2: Analyze URL loads the full game line positioned at the carried ply
- SC-3: desktop eval-chart-below-board + matched move-list height + controls-below + 3-way slider sync + sideline parking
- SC-4: inline tags → PV sideline, sub-sideline (2 levels), contextual TacticModeOverlay
- SC-5 (partial): mobile stacked equivalent; no new backend endpoint (D-4)
</success_criteria>

<output>
Create `.planning/phases/140-full-game-analysis-board/140-02-SUMMARY.md` when done
</output>
