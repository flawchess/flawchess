---
phase: 140-full-game-analysis-board
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/lib/theme.ts
  - frontend/src/lib/analysisUrl.ts
  - frontend/src/lib/analysisUrl.test.ts
  - frontend/src/components/library/EvalChart.tsx
  - frontend/src/hooks/useAnalysisBoard.ts
  - frontend/src/hooks/__tests__/useAnalysisBoard.test.ts
autonomous: true
requirements: [SC-2, SC-3, SC-4, D-4]
must_haves:
  truths:
    - "buildGameAnalysisUrl(id, ply) returns /analysis?game_id={id}&ply={ply}"
    - "TAC_MISSED_BORDER is exported from theme.ts as oklch(0.70 0.15 258 / 0.30)"
    - "EvalChart accepts sliderTestId and sliderDisabled with backward-compatible defaults (existing LibraryGameCard callers unchanged)"
    - "useAnalysisBoard exposes pvLine, insertPvLine, clearPvLine, isOnPvLine"
    - "After insertPvLine(pvSans, forkNodeId): pvLine.length === pvSans.length, every pvLine node chains back to forkNodeId, mainLine is unmutated, isOnPvLine(pvLine[0]) is true and isOnMainLine(pvLine[0]) is false"
    - "After clearPvLine(): pvLine is empty, no pvLine ids remain in nodes, currentNodeId is back on mainLine"
  artifacts:
    - path: "frontend/src/lib/theme.ts"
      provides: "TAC_MISSED_BORDER constant for the inline missed-tag chip border"
      contains: "TAC_MISSED_BORDER"
    - path: "frontend/src/lib/analysisUrl.ts"
      provides: "buildGameAnalysisUrl game-mode URL builder"
      exports: ["buildGameAnalysisUrl"]
    - path: "frontend/src/components/library/EvalChart.tsx"
      provides: "sliderTestId + sliderDisabled optional props"
      contains: "sliderDisabled"
    - path: "frontend/src/hooks/useAnalysisBoard.ts"
      provides: "pvLine state + insertPvLine/clearPvLine/isOnPvLine methods (two-level nesting primitives)"
      contains: "insertPvLine"
  key_links:
    - from: "frontend/src/components/analysis/VariationTree.tsx"
      to: "frontend/src/lib/theme.ts"
      via: "imports TAC_MISSED_BORDER for the inline chip border (consumed in 140-02)"
      pattern: "TAC_MISSED_BORDER"
    - from: "frontend/src/pages/Analysis.tsx"
      to: "frontend/src/hooks/useAnalysisBoard.ts"
      via: "calls insertPvLine/clearPvLine/isOnPvLine and reads pvLine (consumed in 140-02)"
      pattern: "insertPvLine|clearPvLine|isOnPvLine"
    - from: "frontend/src/components/results/LibraryGameCard.tsx"
      to: "frontend/src/lib/analysisUrl.ts"
      via: "imports buildGameAnalysisUrl for the unified Analyze button (consumed in 140-03)"
      pattern: "buildGameAnalysisUrl"
---

<objective>
Build the foundation primitives that the board rewiring (140-02) and entry points (140-03)
depend on: the missing theme constant, the game-mode URL builder, two backward-compatible
EvalChart props, and the two-level variation-nesting methods on useAnalysisBoard. All four are
small, additive, and free of any downstream coupling — they exist so later waves import working
symbols rather than rediscovering them.

Purpose: De-risk the heavy 140-02 plan by pre-landing every primitive it consumes, with unit
coverage on the two that carry real logic (the URL builder and the PV-nesting methods).
Output: TAC_MISSED_BORDER (theme.ts), buildGameAnalysisUrl (analysisUrl.ts), EvalChart
sliderTestId/sliderDisabled props, and useAnalysisBoard pvLine/insertPvLine/clearPvLine/isOnPvLine.
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
</context>

## Artifacts this phase produces (this plan)

New symbols introduced by this plan (excluded from downstream drift verification — they are
created here, not pre-existing):
- `buildGameAnalysisUrl` — `frontend/src/lib/analysisUrl.ts`
- `TAC_MISSED_BORDER` — `frontend/src/lib/theme.ts` (theme constant)
- EvalChart props `sliderTestId`, `sliderDisabled` — `frontend/src/components/library/EvalChart.tsx`
- `pvLine` (state field), `insertPvLine`, `clearPvLine`, `isOnPvLine` — `frontend/src/hooks/useAnalysisBoard.ts`

<tasks>

<task type="auto">
  <name>Task 1: Add TAC_MISSED_BORDER theme constant + buildGameAnalysisUrl URL builder (+ test)</name>
  <files>frontend/src/lib/theme.ts, frontend/src/lib/analysisUrl.ts, frontend/src/lib/analysisUrl.test.ts</files>
  <read_first>
    - frontend/src/lib/theme.ts (existing TAC_MISSED / TAC_MISSED_BG / TAC_ALLOWED_BORDER block — RESEARCH.md theme.ts Color Audit, lines 151-158)
    - frontend/src/lib/analysisUrl.ts (existing buildAnalysisUrl + ANALYSIS_PATH/FEN_PARAM)
    - frontend/src/lib/analysisUrl.test.ts (existing test structure to copy)
    - PATTERNS.md "frontend/src/lib/theme.ts" + "frontend/src/lib/analysisUrl.ts" sections (exact lines)
    - 140-RESEARCH.md landmine L-6 / L-9 (TAC_MISSED_BORDER absence)
  </read_first>
  <action>
    In theme.ts, add the export TAC_MISSED_BORDER with value 'oklch(0.70 0.15 258 / 0.30)'
    immediately after TAC_MISSED_BG, mirroring the existing TAC_ALLOWED_BORDER (the symmetric
    missed-side constant the UI-SPEC inline-chip border requires per L-6). Do not alter any
    existing color value.

    In analysisUrl.ts, add two module-level constants GAME_ID_PARAM = 'game_id' and
    PLY_PARAM = 'ply', then export function buildGameAnalysisUrl(gameId: number, ply: number):
    string returning the template `${ANALYSIS_PATH}?${GAME_ID_PARAM}=${gameId}&${PLY_PARAM}=${ply}`.
    No URL encoding — both params are numeric (per RESEARCH.md, distinct from the fen path which
    keeps encodeURIComponent). Leave buildAnalysisUrl untouched.

    In analysisUrl.test.ts, add a describe block for buildGameAnalysisUrl asserting
    buildGameAnalysisUrl(42, 10) === '/analysis?game_id=42&ply=10' and that
    buildGameAnalysisUrl(1, 0) starts with '/analysis?game_id='. This builder is the single source
    of the D-06 game-card and flaw-card Analyze URLs (consumed in 140-03).
  </action>
  <verify>
    <automated>cd frontend && npm test -- --run analysisUrl</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "export const TAC_MISSED_BORDER" frontend/src/lib/theme.ts` returns 1, value is `'oklch(0.70 0.15 258 / 0.30)'`
    - `buildGameAnalysisUrl` is exported from analysisUrl.ts and returns exactly `/analysis?game_id={gameId}&ply={ply}` with no encoding
    - `buildAnalysisUrl` is unchanged (still encodeURIComponent on the fen path)
    - analysisUrl test suite passes including the new buildGameAnalysisUrl cases
  </acceptance_criteria>
  <done>TAC_MISSED_BORDER exists in theme.ts; buildGameAnalysisUrl exported and unit-tested green.</done>
</task>

<task type="auto">
  <name>Task 2: Add backward-compatible sliderTestId + sliderDisabled props to EvalChart</name>
  <files>frontend/src/components/library/EvalChart.tsx</files>
  <read_first>
    - frontend/src/components/library/EvalChart.tsx (props interface lines 67-127; slider input at ~line 1001 with data-testid eval-slider-${gameId})
    - 140-RESEARCH.md "EvalChart.tsx — Props Analysis" + landmine L-4
    - 140-UI-SPEC.md "Eval chart slider: parked/dimmed state" + Testid Map (analysis-eval-chart-slider)
    - PATTERNS.md "frontend/src/components/library/EvalChart.tsx" section
  </read_first>
  <action>
    Add two optional props to the EvalChart props interface: sliderTestId?: string and
    sliderDisabled?: boolean. Per L-4 these are required for the analysis-page slider testid and
    the D-05 slider-parking behavior, but must be strictly backward compatible — existing
    LibraryGameCard callers pass neither and see zero behavior change.

    Wire sliderTestId on the slider <input type="range"> data-testid, defaulting to the existing
    `eval-slider-${gameId}` when the prop is undefined (so current callers keep their testid).

    Wire sliderDisabled to gate, on the same <input>: the native disabled attribute, plus the
    classes opacity-40, cursor-not-allowed, and pointer-events-none, plus a title attribute reading
    exactly "Return to main game line to scrub" (UI-SPEC copy). When sliderDisabled is false/undefined,
    none of these apply — identical to today. Use theme.ts / Tailwind utilities only; the opacity-40
    dim is a CSS-var/utility state, not a hard-coded color. Do not change the chart-area rendering,
    only the slider input. Keep the function within the nesting/LOC limits; if the slider render
    already breaches limits, extract the class derivation into a small local helper rather than
    deepening the existing branch.
  </action>
  <verify>
    <automated>cd frontend && npx tsc -b && npm run lint</automated>
  </verify>
  <acceptance_criteria>
    - EvalChart props interface contains `sliderTestId?: string` and `sliderDisabled?: boolean`
    - Slider `<input>` data-testid resolves to `sliderTestId ?? eval-slider-${gameId}`
    - When sliderDisabled is true the input gets `disabled`, `opacity-40`, `pointer-events-none`, and title "Return to main game line to scrub"; when false/undefined it gets none of these
    - `npx tsc -b` passes; `npm run lint` passes; no LibraryGameCard caller change required
  </acceptance_criteria>
  <done>EvalChart exposes sliderTestId + sliderDisabled; existing callers compile and behave unchanged.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Add pvLine state + insertPvLine/clearPvLine/isOnPvLine to useAnalysisBoard (+ tests)</name>
  <files>frontend/src/hooks/useAnalysisBoard.ts, frontend/src/hooks/__tests__/useAnalysisBoard.test.ts</files>
  <read_first>
    - frontend/src/hooks/useAnalysisBoard.ts (AnalysisBoardState lines 33-39; AnalysisBoardReturn 42-63; makeInitialState 113-121; loadMainLine batch loop 226-252; goBack 187-194; isOnMainLine 268-270)
    - frontend/src/hooks/__tests__/useAnalysisBoard.test.ts (existing harness + invariant test structure)
    - 140-RESEARCH.md "Hardest Part 1" + "Validation Architecture" (move-tree nesting invariants)
    - 140-RESEARCH.md landmines L-1, L-7 (loadMainLine resets entire tree; makeMove batch-call limitation)
    - PATTERNS.md "frontend/src/hooks/useAnalysisBoard.ts" + Tests section
  </read_first>
  <behavior>
    - insertPvLine(pvSans, forkNodeId): pvLine.length === pvSans.length; every pvLine node's parentId chain reaches forkNodeId; mainLine array is reference-unchanged (no mutation); currentNodeId === forkNodeId after the call (fork position, NOT first PV move — no auto-expand); isOnPvLine(pvLine[0]) === true; isOnMainLine(pvLine[0]) === false
    - clearPvLine(): pvLine.length === 0; none of the prior pvLine ids remain in nodes; currentNodeId is a mainLine node (the fork or an ancestor)
    - fork within PV (makeMove while currentNodeId is a pvLine node): the new node is NOT in pvLine (level-2 sub-sideline); pvLine still holds only the original PV ids
  </behavior>
  <action>
    Add pvLine: NodeId[] to AnalysisBoardState and initialize it to [] in makeInitialState. Extend
    AnalysisBoardReturn with pvLine, insertPvLine, clearPvLine, isOnPvLine.

    Implement insertPvLine(pvSans: string[], forkNodeId: NodeId): void as a SINGLE setState((prev) =>
    {...}) updater (L-1/L-7: never call makeMove in a loop — stateRef.current syncs only after render,
    so sequential makeMove calls would graft every PV node onto the same stale parent). Inside the
    updater: copy the node map with new Map(prev.nodes) (graft, do NOT reset like loadMainLine),
    replay pvSans from new Chess(prev.nodes.get(forkNodeId).fen), allocate ids starting at prev.nextId,
    chain the first PV node's parentId to forkNodeId and each subsequent to the previous PV id, collect
    the new ids into a fresh pvLine array, leave prev.mainLine untouched, set currentNodeId to forkNodeId,
    and advance nextId. Guard the forkNodeId lookup (return prev unchanged if missing) and break the
    replay loop if chess.move returns null.

    Implement clearPvLine(): void as a single setState updater: build new Map(prev.nodes) with every
    id in prev.pvLine deleted, set pvLine: [], and recover currentNodeId by walking parentId up from
    the current node until a mainLine node is reached (fall back to null/root if none). Do not touch
    mainLine.

    Implement isOnPvLine(nodeId: NodeId): boolean as a useCallback reading
    stateRef.current.pvLine.includes(nodeId) (copy the isOnMainLine idiom exactly).

    This is the D-01 ephemeral, in-memory two-level nesting primitive — none of this state is
    URL-encoded.

    Extend useAnalysisBoard.test.ts with the three invariant tests from the behavior block above,
    using the existing renderHook/act harness. Use the noUncheckedIndexedAccess `pvLine[0]!`
    non-null assertion only inside the test where the index is provably in bounds (per L-8 the
    assertion is allowed only when provably in-bounds).
  </action>
  <verify>
    <automated>cd frontend && npm test -- --run useAnalysisBoard</automated>
  </verify>
  <acceptance_criteria>
    - AnalysisBoardState has `pvLine: NodeId[]`; makeInitialState seeds it to `[]`
    - AnalysisBoardReturn exposes `pvLine`, `insertPvLine`, `clearPvLine`, `isOnPvLine`
    - insertPvLine is implemented as one setState call (no makeMove loop) and grafts onto a copied node map without resetting mainLine
    - All three new invariant tests pass: insertPvLine chain+unmutated-mainLine, clearPvLine removal, level-2 fork-not-in-pvLine
    - `npm test -- --run useAnalysisBoard` is green
  </acceptance_criteria>
  <done>useAnalysisBoard exposes the PV-nesting API with passing invariant tests; mainLine is never mutated by PV insertion.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| caller → buildGameAnalysisUrl | numeric gameId/ply produced by callers (slider ply, flaw.ply); not yet parsed back |
| caller → useAnalysisBoard methods | forkNodeId / pvSans supplied by the page; PV strings originate from the trusted tactic-lines endpoint |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-140-01a | Tampering | insertPvLine forkNodeId lookup | mitigate | Updater returns prev unchanged when prev.nodes.get(forkNodeId) is undefined; replay loop breaks on null chess.move (no crash on bad SAN) |
| T-140-01b | Denial of Service | buildGameAnalysisUrl | accept | Pure string concat of numbers; callers guarantee numeric input. URL re-parse + NaN/bounds validation is enforced at the consumer (140-02) |
| T-140-SC | Tampering | npm/pip/cargo installs | accept | No new package installs in this plan — supply-chain surface unchanged |
</threat_model>

<verification>
- `cd frontend && npm test -- --run analysisUrl useAnalysisBoard` green (new builder + nesting invariants)
- `cd frontend && npx tsc -b && npm run lint` clean
- Manual review: existing LibraryGameCard EvalChart usage renders with no visible change (no new props passed)
</verification>

<success_criteria>
- TAC_MISSED_BORDER exported from theme.ts
- buildGameAnalysisUrl exported + unit-tested
- EvalChart accepts sliderTestId/sliderDisabled with backward-compatible defaults
- useAnalysisBoard exposes pvLine + insertPvLine/clearPvLine/isOnPvLine with passing invariant tests
</success_criteria>

<output>
Create `.planning/phases/140-full-game-analysis-board/140-01-SUMMARY.md` when done
</output>
