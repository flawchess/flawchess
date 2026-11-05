# Phase 245: Analysis Contextual Explain Bar for Flaws (SEED-208) - Research

**Researched:** 2026-11-05
**Domain:** React 19 frontend state orchestration on the /analysis page (branching move tree, TanStack Query, grafted PV sidelines)
**Confidence:** HIGH (every seam below was read in source this session; no new packages)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried forward from SEED-208 (locked in the explore session, not re-discussed)
- **D-01:** One Explain button only. No "Best" button (on the user's own flaws it duplicates Explain's first step) and no "Next" button (`useFastForward` "Jump to next key moment" already does it).
- **D-02:** No coach prose, no LLM. A guided stepper over stored PVs only.
- **D-03:** Contextual bar: under the move list on desktop, directly above the mobile footer on mobile (the footer is at its 5-column limit on a 360px phone). Shown only when the current node is an eligible flaw ply (see D-08) or inside that flaw's Explain line.
- **D-04:** Direction rule (same semantics as the tactic motif badges): the user's own flaw opens the MISSED PV forking at ply-1; the opponent's flaw opens the ALLOWED PV forking at the flaw ply. D-09 adds a fallback.
- **D-05:** Explain grafts the line and plays its first move immediately (unlike chips, which park at the fork node). For the allowed line, "first move" means the refutation: `allowed_moves[0]` is the prepended flaw move itself, which already sits on the main line.
- **D-06:** Back/Forward step through the line (`goForward` already prefers the PV child). There are no separate stepper buttons. While the board is in the line, Explain turns into "Got it", which closes the line (`deleteSubtree` + remove from `openLines`) and returns the board to the flaw move on the main line.
- **D-07:** Leaving the line any other way (move-list click, Jump, eval-chart scrub) keeps it open, like tactic chips; re-entering it shows Got it again. Chip and Explain share the `flawKey(ply, orientation)` line key, so a motif flaw never gets duplicate sidelines.

#### Inaccuracy support
- **D-08:** **Inaccuracies are dropped from scope** (this revises the SEED-208/ROADMAP "every flaw including inaccuracies" bullet). `game_flaws` holds mistakes and blunders only (`app/services/library_service.py:457`); inaccuracy markers are synthesized from evals, so `GET /library/flaws/{game_id}/{ply}/tactic-lines` returns 404 for them. The owner chose not to add a backend fallback. Eligible plies are `flaw_markers` entries with `severity` of `mistake` or `blunder`, either side (`is_user` true or false), with or without a motif. The bar is hidden on inaccuracy plies. — **Reversibility:** reversible — adding inaccuracies later means a small backend fallback in `fetch_tactic_lines` (replay `game_positions.move_san` to rebuild the board when there is no `game_flaws` row) plus widening the eligibility check.

#### Missing-PV handling
- **D-09:** **Fall back to the other line** when the direction-rule line is null. A user flaw without `missed_moves` opens the ALLOWED line (fork at the flaw ply); an opponent flaw without `allowed_moves` opens the MISSED line (fork at ply-1). The opened orientation is the one actually used, so the line key stays `flawKey(ply, <used orientation>)` and stays shared with that orientation's chip. Motivation: in dev, PV-complete games, about 20% of M/B flaws lack the missed PV, while only about 1% lack the allowed PV.
- **D-10:** **Hide the bar** when neither line exists (both PVs null; typical for games not yet PV-analyzed, where almost every flaw has neither). No disabled button and no tooltip.
- **D-11:** **Prefetch on landing.** When the board's current node is an eligible flaw ply, fire `useTacticLines(gameId, ply)` (TanStack-cached, same query key the Explain click and the chips use, so the click reuses the data). The bar appears only once the response shows at least one non-null line. Don't flash a button that might disappear: the bar stays hidden (no visible placeholder) until the data resolves. Frontend only; there is no `has_pv` flag on `FlawMarker`.

### Claude's Discretion
- Bar copy, visuals, icon, dark-theme tokens: decided in `/gsd-ui-phase 245` (UI-SPEC). The owner did not pick a headline style (e.g. "Rc5 is a blunder"); leave that to the UI-SPEC.
- Deep-link tactic auto-open (`tacticOrientationAtPly`, `initialTactic`): **keep unchanged**. A deep link to a user tactic ply still auto-opens the missed line parked at the fork. Because the board is then inside an open line, the bar naturally shows Got it there. Don't extend auto-open to non-motif flaws.
- Umami event names (follow the existing kebab-case `data-umami-event` convention in `frontend/src/lib/analytics.ts`, e.g. `analysis-explain-open` / `analysis-explain-close`) and testids (follow `frontend/CLAUDE.md`).
- What the bar shows at a missed line's fork node (ply-1, a main-line node) when the user steps Back out of the line. Follow `findFocusedFlaw` semantics unless the UI-SPEC says otherwise.
- Interaction with fast-forward (`fastForward.isRunning`): hide or ignore the bar while the Jump animation runs.

**Owner decision for this run (from the orchestrator):** there is NO UI-SPEC. Copy, visuals, icon, tokens, testids and Umami names are at Claude's discretion; concrete recommendations are in "UI Recommendations (no UI-SPEC)" below for the planner to lock.

### Deferred Ideas (OUT OF SCOPE)
- Explain for inaccuracies: needs the small `fetch_tactic_lines` fallback described in D-08. Possible follow-up seed if users ask.
- Explain for free-play / what-if moves graded live by `useLiveMoveFlaw` (no stored PV). Out of scope per ROADMAP.

#### Reviewed Todos (not folded)
- `172-deferred-review-findings.md`, `2026-03-11-bitboard-storage-for-partial-position-queries.md`, `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`, `2026-08-29-variation-tree-nested-button.md`: generic keyword matches, unrelated to this phase.
</user_constraints>

<phase_requirements>
## Phase Requirements (coverage contract = CONTEXT D-01..D-11; no REQ-IDs)

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | One Explain button, no Best/Next | Bar has exactly one button whose label swaps Explain/Got it ("UI Recommendations"). |
| D-02 | No prose, no LLM | Only stored `TacticLinesResponse` PVs are used; copy is static template text. |
| D-03 | Contextual placement + visibility | Mount points: desktop `MovesCard` footer slot, mid under board controls, mobile row above `analysis-mobile-footer` (Q5). Visibility via pure `resolveExplainBarState` (Q2/Q3). |
| D-04 | Direction rule | `chooseExplainOrientation(isUser, usable)` preferred = `is_user ? 'missed' : 'allowed'` (Q3). |
| D-05 | Graft + play first move | `pendingFlaw.enter` flag + one `goToNode(rootNodeId)` after `insertPvLine` in the existing graft effect (Q1). |
| D-06 | Back/Forward stepping; Got it closes + returns to flaw move | `goForward` PV-child preference already exists; Got it = `deleteSubtree` + `openLines.delete` + `goToNode(mainLine[ply])` (Q2). |
| D-07 | Leaving keeps line open; shared key | Explain on an already-open key navigates to its `rootNodeId` instead of grafting; key is `flawKey` (Q1/Q2). |
| D-08 | M/B only, both sides | Eligibility filters `severity === 'mistake' \|\| 'blunder'` (Q3). |
| D-09 | Fallback to the other line | `chooseExplainOrientation` fallback branch; usable-line predicates guard empty/short arrays (Q3). |
| D-10 | Hide when neither line | `chooseExplainOrientation` returns null → `hidden` (Q3). |
| D-11 | Prefetch on landing, no flash | Second `useTacticLines` observer for the landing ply, same key → TanStack dedupe/cache hit; bar `hidden` until `data` resolves (Q4). 404 hardening recommended. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Frontend rules (`frontend/CLAUDE.md`): theme colors only from `frontend/src/lib/theme.ts`; `noUncheckedIndexedAccess` is on (narrow every index access); knip runs in CI (every new export must be imported); `max-depth` 4 is a hard lint error; `npm run lint`/`npm test` do NOT type-check, run `npm run build` too.
- Minimum font size `text-sm`, never `text-xs` (popover bodies excepted). Note `Button size="sm"` uses `text-[0.8rem]` (below text-sm), so do not use `size="sm"` for this bar.
- Buttons: primary = `variant="default"`, secondary = `variant="brand-outline"`; never hand-roll colors via className; never `variant="secondary"` for secondary actions.
- Always apply changes to mobile too (desktop and mobile mount sites both).
- Every interactive element needs `data-testid` (kebab-case, `btn-{action}` for standalone action buttons); semantic `<button>`; aria-label on icon-only buttons; major containers get a testid.
- Feature analytics go through the typed `trackFeature` registry in `frontend/src/lib/analytics.ts` from the user-initiated handler only (never an effect, never mount). "Free-form events are a build error by design", reuse the 9 verbs, enumerated literals only. Skip high-frequency interactions such as move stepping.
- Do not add duplicate `Sentry.captureException` for TanStack queries (global `QueryCache.onError` already captures).
- Root CLAUDE.md: no magic numbers (named constants), explicit return types, `Literal`/literal unions instead of bare strings, comment bug fixes at the fix site, functions small and shallow (nesting depth <= 4), no scope creep beyond the phase (flag instead).
- Pre-merge gate (frontend part): `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )`.
- Project memory: heavy frontend tests had timeout flakes, fixed project-wide; never re-add per-file timeouts; hoist `await import` out of test bodies into `beforeAll`. Run `tsc -b` (`npm run build`) before integrating. Frontend has no Prettier (never run prettier --write). `cn()` uses tailwind-merge.

## Summary

Everything Explain needs already exists in the chip machinery; the phase is a thin orchestration layer plus two small hardening changes. The chip path is: `handlePvChipClick` sets `pendingFlaw` and navigates to the fork node; `fetchFlaw = pendingFlaw ?? focusedFlaw` drives `useTacticLines`; the graft effect in `useAnalysisRouteSeeding` calls `insertPvLine` (which parks at the fork), records `openLines`, and clears `pendingFlaw`. Explain differs only in that it must land on the first grafted node. The cleanest seam is an optional `enter` flag on the `pendingFlaw` state, consumed inside the existing graft effect with one extra `goToNode(rootNodeId)` call right after `insertPvLine`. Both are functional `setState` updaters in the same effect, so they batch into one commit, the fork position never paints, and chips (no flag) are unchanged.

Ply indexing is consistent end to end: a `FlawMarker.ply` P is the 0-based index of the flaw move, the flaw-move node is `mainLine[P]`, the missed fork is `mainLine[P-1]`, and the allowed fork is `mainLine[P]` itself. Eligibility (M/B, both sides), orientation (D-04 + D-09 fallback), and the bar's three states (hidden / explain / got-it) should be pure module-scope functions in a new `lib/explainBar.ts`, wired by a `useExplainBar` hook and rendered by a small `ExplainBar` component mounted at three sites (desktop MovesCard, mid board stage, mobile above the footer).

Two non-obvious issues the plan must handle. (1) Explain opens lines WITHOUT a visible tactic motif for the first time, and `useAnalysisBoardArrows` defaults null depth/ply-index to 0, so a non-motif line would render a teal/crimson "1" countdown arrow and tint the first move as if it were a one-move tactic. Gate the tactic overlay on a visible, user-scoped motif. (2) The D-11 prefetch fires `GET .../tactic-lines` on every M/B landing, but `flaw_markers` are computed live from evals while `game_flaws` rows are written at classification time. They can drift (dev DB: 290 of 13,776 games have a `game_flaws` count that differs from the oracle columns), so a prefetch can 404, which today triggers one retry and a Sentry capture. Map 404 to `null` in `useTacticLines`, following the `useCachedEndgameInsights` precedent.

**Primary recommendation:** Add `lib/explainBar.ts` (pure), `hooks/analysis/useExplainBar.ts` (prefetch + handlers), `components/analysis/ExplainBar.tsx` (UI), plus three small edits: `enter` flag in the graft effect, 404→null in `useTacticLines`, and a motif gate in `useAnalysisBoardArrows`. No backend change.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Flaw eligibility + orientation choice | Browser / Client (pure lib) | — | Derived from already-loaded `gameData.flaw_markers` + cached tactic-lines data; no server logic. |
| PV line data (missed/allowed SANs) | API / Backend (existing, unchanged) | Browser (TanStack cache) | `GET /library/flaws/{game_id}/{ply}/tactic-lines` already serves both orientations for any `game_flaws` row. |
| Line graft / delete / navigation | Browser / Client (`useAnalysisBoard`) | — | In-memory move tree, ephemeral, not URL-encoded. |
| Bar visibility state machine | Browser / Client (hook + pure fn) | — | Depends on current node, open lines, pending flaw, fast-forward run state. |
| Analytics events | Browser / Client (`trackFeature`) | Umami | Click-only events, page derived from route. |

## Standard Stack

No new libraries. Everything is in the existing frontend stack. [VERIFIED: frontend/package.json read this session]

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | ^19.2.8 | Components/hooks | Project stack |
| @tanstack/react-query | ^5.100.14 | `useTacticLines` cache, dedupe | Already the tactic-lines fetch layer |
| lucide-react | 1.63.0 installed (`^1.21.0` declared) | Icons (`Lightbulb`, `Check`) | Project icon library; both icons verified to export (`node -e` check this session) |
| chess.js | (existing) | Already used by `insertPvLine` | No new use needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| vitest | ^5.0.5 | Unit/hook/component tests | All new tests |
| @testing-library/react | ^16.3.2 | `renderHook`, `render`, `act` | Hook + component tests |

**Installation:** none.

## Package Legitimacy Audit

Not applicable: this phase installs no external packages. **Packages removed:** none. **Packages flagged:** none.

## Architecture Patterns

### System Architecture Diagram

```
 user lands on node N (move-list click / Back/Forward / Jump / eval scrub / deep link)
        │
        ▼
 currentMainlinePly (Analysis.tsx:1324)  ── -1 (sideline/root) ──┐
        │ P                                                       │
        ▼                                                         │
 eligibleExplainMarker(flaw_markers, P)  (M/B, either side)       │
        │ marker | null                                           │
        ▼                                                         │
 useTacticLines(gameId, P, enabled)   ◄── same key as chips ──►  TanStack cache
   (prefetch observer, D-11)               ['tactic-lines', gameId, ply]
        │ data | undefined(loading) | null(404 or both-null)      │
        ▼                                                         ▼
 resolveExplainBarState({ffRunning, pendingFlaw, focusedFlaw, openLines, marker, data, P})
        │
        ├─ hidden  (not game mode / ff running / unrelated pending / no marker / data not ready / no usable line)
        ├─ got-it  (focusedFlaw is an OPEN line: inside subtree OR at its fork node)
        └─ explain (marker eligible + chooseExplainOrientation → 'missed' | 'allowed')
        │
        ▼
 <ExplainBar>  (desktop MovesCard footer | mid under BoardControls | mobile above footer)
        │ click
        ├─ Explain, key already open → goToNode(openLine.rootNodeId)
        ├─ Explain, key not open     → setPendingFlaw({ply, orientation, enter:true})
        │                                   │
        │                                   ▼
        │                     graft effect (useAnalysisRouteSeeding.ts:235-260)
        │                       insertPvLine(pv, fork)  (parks at fork)
        │                       setOpenLines(+key) ; setPendingFlaw(null)
        │                       if enter → goToNode(rootNodeId)   ◄── NEW, same batch
        └─ Got it → deleteSubtree(root) ; setOpenLines(-key) ; goToNode(mainLine[ply])
```

### Recommended Project Structure
```
frontend/src/
├── lib/explainBar.ts                       # NEW pure: eligibility, usable lines, orientation, bar state
├── lib/__tests__/explainBar.test.ts        # NEW
├── hooks/analysis/useExplainBar.ts         # NEW hook: prefetch observer + onExplain/onGotIt
├── hooks/analysis/__tests__/useExplainBar.test.ts   # NEW harness test (real board + graft)
├── components/analysis/ExplainBar.tsx      # NEW presentational bar
├── components/analysis/__tests__/ExplainBar.test.tsx # NEW
├── lib/analysisTactics.ts                  # EDIT: add PendingFlaw type
├── hooks/analysis/useAnalysisRouteSeeding.ts # EDIT: enter flag in graft effect
├── hooks/useLibrary.ts                     # EDIT: 404 → null in useTacticLines
├── hooks/analysis/useAnalysisBoardArrows.ts # EDIT: motif gate for tactic overlay
├── components/analysis/AnalysisDesktopCards.tsx # EDIT: MovesCard footer slot
├── components/analysis/AnalysisBoardStage.tsx   # EDIT: mid-layout slot under BoardControls
├── lib/analytics.ts                        # EDIT: two BOARD_TOOL_TARGETS
└── pages/Analysis.tsx                      # EDIT: hook call + 3 mount sites + pendingFlaw type
```

### Q1: The chip path today, and the seam for "play the first move"

Verbatim, `frontend/src/pages/Analysis.tsx:1776-1800` [VERIFIED: read this session]:
```typescript
  const handlePvChipClick = (
    nodeId: NodeId,
    flaw: { ply: number; orientation: 'missed' | 'allowed' },
  ): void => {
    const key = flawKey(flaw);
    const existing = openLines.get(key);
    if (existing != null) {
      // Same chip clicked again: collapse ONLY this line — no fetch needed.
      deleteSubtree(existing.rootNodeId);
      setOpenLines((prev) => {
        const next = new Map(prev);
        next.delete(key);
        return next;
      });
      return;
    }
    // Different/new chip: open it. insertPvLine is called by the graft effect once
    // contextualTacticData arrives; other open lines are left untouched.
    setPendingFlaw(flaw);
    // Navigate to the fork node — decision board (ply-1) for missed, flaw position (ply) for
    // allowed. Bounds guard.
    const forkNodeId = mainLine[forkPlyForOrientation(flaw.ply, flaw.orientation)];
    if (forkNodeId !== undefined) goToNode(forkNodeId);
    void nodeId; // nodeId passed for API symmetry with VariationTree; ply identifies the flaw
  };
```

Fetch wiring, `Analysis.tsx:565-570` [VERIFIED]:
```typescript
  const fetchFlaw = pendingFlaw ?? focusedFlaw;
  const {
    data: contextualTacticData,
    isFetching: contextualPending,
    isError: contextualError,
  } = useTacticLines(gameId, fetchFlaw?.ply ?? null, fetchFlaw != null && isGameMode);
```

Graft effect, `frontend/src/hooks/analysis/useAnalysisRouteSeeding.ts:235-260` [VERIFIED]:
```typescript
  useEffect(() => {
    if (!isGameMode || pendingFlaw == null || contextualTacticData == null) return;
    const key = flawKey(pendingFlaw);
    if (openLines.has(key)) return; // already recorded — guard against a stale re-run
    // ...
    const pvMoves =
      pendingFlaw.orientation === 'missed'
        ? (contextualTacticData.missed_moves ?? [])
        : (contextualTacticData.allowed_moves ?? []).slice(1);
    // Guard the fork node lookup (out-of-bounds ply).
    const forkNodeId = mainLine[forkPlyForOrientation(pendingFlaw.ply, pendingFlaw.orientation)];
    if (forkNodeId === undefined || pvMoves.length === 0) return;
    // Snapshot the line's root id BEFORE grafting — the hook assigns nextId to the first
    // grafted node (insertPvLine's batch-build loop starts at prev.nextId).
    const rootNodeId = nextId;
    insertPvLine(pvMoves, forkNodeId);
    setOpenLines((prev) => new Map(prev).set(key, { rootNodeId, ply: pendingFlaw.ply, orientation: pendingFlaw.orientation }));
    setPendingFlaw(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contextualTacticData, pendingFlaw?.ply, pendingFlaw?.orientation, isGameMode]);
```

`insertPvLine` parks at the fork: `currentNodeId: forkNodeId, // park at fork, not first PV move` (`useAnalysisBoard.ts:544`), and `goToNode`'s updater guards with `if (!prev.nodes.has(id)) return prev;` (`useAnalysisBoard.ts:396`) [VERIFIED]. Both use functional updaters, so calling `goToNode(rootNodeId)` immediately after `insertPvLine(...)` in the same effect sees the grafted nodes in the chained `prev` and batches into one commit.

**Recommended seam (prescriptive):**
1. In `lib/analysisTactics.ts` add `export type PendingFlaw = TacticRef & { enter?: boolean };` (`TacticRef` is `{ ply: number; orientation: 'missed' | 'allowed' }`, `analysisTactics.ts:28`). Use it for the `pendingFlaw` state in `Analysis.tsx:447-450` and for `pendingFlaw`/`setPendingFlaw` in `UseAnalysisRouteSeedingOptions` (`useAnalysisRouteSeeding.ts:59,72`). `findFocusedFlaw`'s `TacticRef` parameter accepts it structurally; `initialTactic` (a `TacticRef`) still assigns to `setPendingFlaw`.
2. In the graft effect, after `insertPvLine(pvMoves, forkNodeId);` add `if (pendingFlaw.enter) goToNode(rootNodeId);`, with a comment explaining why (Explain lands on the first move, D-05; chips keep parking at the fork). `goToNode` is already in the hook's options (`useAnalysisRouteSeeding.ts:67`). No dependency-array change: the flag rides with the same `pendingFlaw` object, and the existing deps already read it fresh.
3. The Explain handler does NOT navigate to the fork first (unlike the chip). If it did, the missed case would commit `mainLine[P] → mainLine[P-1]` and then `→ root` in two commits, with two move sounds and a one-frame back-step flicker. Without the fork navigation the board goes `mainLine[P] → root` in one commit. With D-11 prefetch the data is already cached, so `useTacticLines` returns it synchronously in the render where `pendingFlaw` is set, and the graft effect fires on that commit.
4. Because the handler makes no gesture-path board call, call `unlockAudio()` from `@/lib/sounds` at the top of `onExplain` (the board hook only unlocks inside gesture-path commands; `useAnalysisBoard.ts:276-289` documents the iOS/WebKit gesture requirement) [VERIFIED]. A deep link straight to a flaw ply followed by Explain as the very first tap would otherwise be silent on iOS.
5. Explain when the key is already open (D-07 re-entry): `goToNode(existing.rootNodeId)`. No graft, no toggle-off. This is the one behavioral difference from `handlePvChipClick`, which deletes on the same key.

Allowed line "first move": the graft uses `allowed_moves.slice(1)`, so `rootNodeId` is already the refutation node (D-05 satisfied by the same `goToNode(rootNodeId)`).

### Q2: "Inside the Explain line" detection, Got it, and the flaw-move node

`findFocusedFlaw` (`Analysis.tsx:292-313`) [VERIFIED] returns `pendingFlaw` when `currentNodeId` equals its fork node; otherwise, for each open line, it returns the line when `currentNodeId === mainLine[fork]` OR `isNodeInsideSubtree(nodes, currentNodeId, line.rootNodeId)` (walks `parentId` up to `rootNodeId`, `Analysis.tsx:316-327`). First open line in Map insertion order wins.

**Got-it rule (prescriptive):** bar is `got-it` iff `focusedFlaw != null && openLines.has(flawKey(focusedFlaw))`. Reuse the already-computed `focusedFlaw` memo (`Analysis.tsx:546-549`), do not recompute. This matches CONTEXT discretion ("Follow findFocusedFlaw semantics") and gives Got it at:
- any node inside the grafted subtree, including free moves the user played off a PV node (a `makeMove` child is inside the subtree even though it is not in `pvNodeIds`; `useAnalysisBoard.test.ts:523` confirms such children exist);
- the missed fork `mainLine[P-1]` after stepping Back out of the line;
- the allowed fork `mainLine[P]`, which is the flaw-move node itself, while the allowed line is open (e.g. after a chip opened it);
- a deep-link auto-opened missed line parked at its fork (CONTEXT-expected).

**Flaw-move node per orientation** (ply convention verified below): missed: fork `mainLine[P-1]`, flaw move `mainLine[P]` (main-line child of the fork). Allowed: fork = flaw move = `mainLine[P]`.

**Got it handler (prescriptive):**
```typescript
// Sketch, names proposed (not in repo yet). Values used: flawKey, deleteSubtree, goToNode, mainLine.
function onGotIt(line: OpenLine): void {
  deleteSubtree(line.rootNodeId);           // recovers currentNodeId to the fork parent if inside
  setOpenLines((prev) => { const next = new Map(prev); next.delete(flawKey(line)); return next; });
  const flawNodeId = mainLine[line.ply];    // the flaw move on the main line, both orientations
  if (flawNodeId !== undefined) goToNode(flawNodeId);
  trackFeature('board-tool', { target: 'explain-close' });  // proposed target, see analytics
}
```
`deleteSubtree`'s updater runs first (recovering to the fork), then `goToNode`'s updater moves to `mainLine[P]` (main-line nodes are never deleted). One commit. For allowed, recovery already lands on `mainLine[P]` and `goToNode` bails (`if (prev.currentNodeId === id) return prev;`, `useAnalysisBoard.ts:400`). Node ids are never reused (`deleteSubtree` does not touch `nextId`), so stale `liveFlawByNode`/`gemByNode` entries keyed by deleted ids are harmless.

**Precedence edge (document, accept):** when the user's missed line at P is open and the board is at `mainLine[P-1]`, which can itself be an eligible opponent flaw at P-1 (the classic "opponent blunders, user misses it" pair), the bar shows Got it for P:missed, not Explain for P-1. Note that P-1's allowed PV and P's missed PV start from the same position and are usually the same moves. After Got it, the board moves to `mainLine[P]` and P-1's Explain is reachable with one Back.

### Q3: Eligibility, orientation, D-09 fallback, and ply indexing

**Ply convention (verified three ways):**
- Backend `fetch_tactic_lines`: `board_before = chess.Board(flaw.fen)`, `board_before.turn = chess.WHITE if ply % 2 == 0 else chess.BLACK`; `flaw_move_san = pos_n.move_san` (`library_repository.py:2329-2340`). So ply P is the decision position and the flaw move is the move played from it.
- Frontend: `const nodeId = mainLine[fm.ply];` in `flawMarkerByNodeId` (`useAnalysisGemMarkers.ts:337`) and the comment "0-based on moves — same convention as game_positions.ply and mainLine indexing" (`Analysis.tsx:1150-1152`).
- `forkPlyForOrientation`: `return orientation === 'allowed' ? flawPly : flawPly - 1;` (`analysisTactics.ts:41-43`).

Therefore no off-by-one: marker ply P ↔ node `mainLine[P]` ↔ `currentMainlinePly === P`. `currentMainlinePly` already exists (`Analysis.tsx:1324-1327`: `currentNodeId !== null && isOnMainLine(currentNodeId) ? mainLine.indexOf(currentNodeId) : -1`). Reuse it as the landing ply.

**Data locations:** `gameData.flaw_markers: FlawMarker[] | null` from `useLibraryGame` (`Analysis.tsx:576-579`). `FlawMarker` (`types/library.ts:160-178`) [VERIFIED] has `ply: number; severity: FlawSeverity; is_user: boolean; move_san: string | null; allowed_tactic_motif: string | null; ... missed_tactic_motif: string | null; ...`. `FlawSeverity = 'inaccuracy' | 'mistake' | 'blunder'` (`types/library.ts:29`). Backend builds markers for both colours with `is_user = mover_color == game.user_color` (`library_service.py:332`). Note that `is_user` is relative to the game OWNER, not the viewer (a viewer can open another user's game). `TacticLinesResponse` (`types/library.ts:449-474`) has `missed_moves: string[] | null` and `allowed_moves: string[] | null`.

**Pure helpers (prescriptive, `lib/explainBar.ts`):**
```typescript
// Proposed module. In-repo values used: 'mistake' | 'blunder' (FlawSeverity), 'missed' | 'allowed'
// (TacticRef.orientation), missed_moves/allowed_moves (TacticLinesResponse), allowed_moves[0] = flaw move.
const ALLOWED_PREPEND_LEN = 1;      // allowed_moves[0] is the prepended flaw move
const MIN_MISSED_FORK_PLY = 1;      // missed forks at ply-1; ply 0 would fork at the root (unsupported)

export function eligibleExplainMarker(markers: FlawMarker[] | null | undefined, ply: number): FlawMarker | null {
  if (markers == null || ply < 0) return null;
  return markers.find((m) => m.ply === ply && (m.severity === 'mistake' || m.severity === 'blunder')) ?? null;
}

export function usableExplainLines(data: TacticLinesResponse, ply: number): { missed: boolean; allowed: boolean } {
  return {
    missed: ply >= MIN_MISSED_FORK_PLY && (data.missed_moves?.length ?? 0) > 0,
    allowed: (data.allowed_moves?.length ?? 0) > ALLOWED_PREPEND_LEN,
  };
}

export function chooseExplainOrientation(isUser: boolean, usable: { missed: boolean; allowed: boolean }): 'missed' | 'allowed' | null {
  const preferred = isUser ? 'missed' : 'allowed';   // D-04
  const fallback = isUser ? 'allowed' : 'missed';    // D-09
  if (usable[preferred]) return preferred;
  if (usable[fallback]) return fallback;
  return null;                                        // D-10
}
```
Why the length guards matter: the graft effect returns early when `pvMoves.length === 0` WITHOUT clearing `pendingFlaw` (`useAnalysisRouteSeeding.ts:248`), which would leave the bar stuck in its pending state. `allowed_moves` can be `[flaw]` only if the stored PV string parses to zero moves. Missed at ply 0 has no fork node (`mainLine[-1]` is undefined), which hits the same early return. Dev DB shows 0 `game_flaws` rows at ply 0, so this is a guard, not a common path.

**Bar state (prescriptive, pure, also in `lib/explainBar.ts`):**
```typescript
export type ExplainBarState =
  | { kind: 'hidden' }
  | { kind: 'explain'; flaw: TacticRef; marker: FlawMarker; pending: boolean }
  | { kind: 'got-it'; line: OpenLine; marker: FlawMarker | null };

// Order matters:
// 1. !isGameMode || fastForwardRunning                      → hidden
// 2. focusedFlaw && openLines.has(flawKey(focusedFlaw))     → got-it
// 3. pendingFlaw != null && pendingFlaw.ply !== landingPly  → hidden (an unrelated chip/deep-link open is in flight)
// 4. marker = eligibleExplainMarker(markers, landingPly); none → hidden (covers sidelines: landingPly === -1)
// 5. data === undefined (loading) or null (404 mapped)       → hidden (D-11, no placeholder)
// 6. orientation = chooseExplainOrientation(marker.is_user, usableExplainLines(data, landingPly)); null → hidden
// 7. → explain { flaw: { ply: landingPly, orientation }, marker, pending: pendingFlaw?.ply === landingPly }
```
`pending: true` renders the Explain button disabled for the at most one render between the click and the graft commit, so the bar never blinks out. Keep this whole function free of nested loops so it stays inside max-depth and the React Compiler lint.

### Q4: D-11 prefetch, query key, dedupe, and 404/null shape

`useTacticLines` (`hooks/useLibrary.ts:295-307`) [VERIFIED]:
```typescript
export function useTacticLines(
  gameId: number | null,
  ply: number | null,
  enabled: boolean,
): ReturnType<typeof useQuery<TacticLinesResponse>> {
  return useQuery<TacticLinesResponse>({
    queryKey: ['tactic-lines', gameId, ply],
    queryFn: () => libraryApi.getTacticLines(gameId!, ply!),
    enabled: enabled && gameId != null && ply != null,
    staleTime: LIBRARY_STALE_TIME_MS,
    refetchOnWindowFocus: false,
  });
}
```
`LIBRARY_STALE_TIME_MS = 5 * 60 * 1000` (`useLibrary.ts:16`). Global defaults: `retry: 1` and `QueryCache.onError` → `Sentry.captureException` (`lib/queryClient.ts`) [VERIFIED].

- **Use a second observer, not the existing one.** Call `useTacticLines(gameId, eligiblePly, eligiblePly != null && isGameMode)` inside `useExplainBar`. Do NOT fold the landing ply into `fetchFlaw`: `contextualPending` feeds `VariationTree`'s chip spinner (`isActive && pvFetchPending`, `VariationTree.tsx:615`), so a prefetch on another ply would spin an unrelated active chip.
- **Duplicates:** two observers with the same key share one Query; TanStack dedupes in-flight fetches and serves the cache within `staleTime`. When the Explain click sets `pendingFlaw` to P, `fetchFlaw`'s key becomes `['tactic-lines', gameId, P]`, which is the prefetched entry, so it is a synchronous cache hit, not a second request. [ASSUMED: TanStack v5 observer dedupe semantics, standard documented behavior, not re-fetched from docs this session]
- **Null shape:** "neither line" comes back as HTTP 200 with `missed_moves: null` and `allowed_moves: null` (`library_repository.py:2334-2352`, `pv_to_san_list` returns None for a falsy pv, `:2257-2258`). No `game_flaws` row → `fetch_tactic_lines` returns None → router raises `HTTPException(status_code=404, detail="Flaw not found")` (`app/routers/library.py:391-393`).
- **404 is reachable for M/B markers.** Markers are computed live from current evals; `game_flaws` rows are written at classify time. Dev DB probe (read-only, this session): 13,776 games with oracle columns, 290 whose `game_flaws` row count differs from `white/black_mistakes + blunders`. 163 non-full-eval games carry oracle M/B counts but zero `game_flaws` rows. That is a game-level proxy, not a ply-level proof, but 404s on prefetch are plausible at about 1-2% of games. Today each would retry once and land in Sentry.
- **Recommendation (prescriptive):** in `useTacticLines`, map 404 to `null` inside `queryFn` (type `TacticLinesResponse | null`), exactly as `useCachedEndgameInsights` does (`hooks/useEndgameInsights.ts:53-72`: `if (axios.isAxiosError(err) && err.response?.status === 404) { return null; }`). Use a named constant (precedent: `const HTTP_NOT_FOUND = 404;` in `hooks/usePushCapability.ts:27`). Widen `contextualTacticData` in `UseAnalysisRouteSeedingOptions` to `TacticLinesResponse | null | undefined` (`useAnalysisBoardArrows` already accepts `| null | undefined`, line 230). The graft effect's `== null` check already treats null as "no data". Chips only exist for `game_flaws` rows, so chip behavior is unchanged.

Dev DB PV coverage (read-only probe, this session) confirms D-09's motivation. PV-complete games: 41,018 flaws, missed null 18.1%, allowed null 1.0%, both null 0.8%. Non-PV-complete: 28,649 flaws, both null 87.8%.

### Q5: Mount points and props

Three layouts render from separate return branches of `Analysis()`; only one mounts at a time.

| Layout | Where the move list is | Recommended mount | Evidence |
|--------|------------------------|-------------------|----------|
| Desktop 3-col | `MovesCard` in the right column (`Analysis.tsx:2707`), `AnalysisDesktopCards.tsx:115-124` | New optional `footer?: ReactNode` prop on `MovesCard`, rendered after `<VariationTreePanel>` inside the Card as a `shrink-0` row. MovesCard is `flex min-h-0 flex-1 flex-col`, so the bar shrinks the tree's scroller, not the column. | MovesCard body read |
| Mid (2-col) | Right column `analysisTabs` → `MovesTab` (Moves tab only) | Optional `explainBar?: ReactNode` prop on `DesktopBoardStage`, rendered right below the `BoardControls` Card only when `isMid` (`AnalysisBoardStage.tsx:162-164`). In mid the move list is hidden on other tabs, while the board controls are always visible. | DesktopBoardStage read; mid layout `Analysis.tsx:2454-2500` |
| Mobile | `analysisTabs` (flex-1) then `analysis-mobile-footer` | New `shrink-0` sibling between `{analysisTabs}` (`Analysis.tsx:2576`) and the footer `<div data-testid="analysis-mobile-footer" ...>` (`:2578-2598`). `AnalysisTabs` root is `flex min-h-0 flex-1 flex-col` (`AnalysisTabs.tsx:833`), so it absorbs the height. `BoardControls` stays 5-column. | read |

`AnalysisTabs.tsx` is NOT the desktop move-list site. It is shared by mobile and mid, so do not put the bar inside `MovesTab`: it would double-render on mobile (above the footer and inside the tab). The mid placement is not covered by D-03 (which names desktop and mobile only). It is a discretion call; flag it for the owner in UAT.

Props today: `MovesCard({ onOpenPasteModal, fen, getPgn, variationTreeProps })`; `DesktopBoardStage` takes `boardControlsProps` and `isMid` (`AnalysisBoardStage.tsx:65-66`). Pass a prebuilt `<ExplainBar ... />` element (slot) rather than threading bar state through these components: it keeps them presentational and avoids widening `Analysis()` further.

### Q6: Interactions

- **Fast-forward:** `useFastForward` stops on `fastForwardStopPlies` = M/B (both sides) + gem/great (`Analysis.tsx:1179-1189`), which is exactly the Explain-eligible set plus gems, so Jump becomes the natural Next. Any committed navigation the hook did not command cancels a run (`useFastForward.ts` header). Hide the bar while `fastForwardRunning` (lifted state, `Analysis.tsx:434`) is true; it reappears after the run's settle delay on the landing flaw. Prefetch can stay enabled during a run because intermediate plies are by construction not stop plies.
- **Deep-link auto-open:** unchanged. The seeding effect sets `pendingFlaw = initialTactic` and `goToNode(fork, { silent: true })` (`useAnalysisRouteSeeding.ts:213-221`); `initialTactic` has no `enter` flag, so it still parks at the fork. While its fetch is pending the bar is hidden (rule 3). After the graft the board is at the fork of an open line, so the bar shows Got it (rule 2).
- **Eval-chart scrub:** `handleEvalChartPlyChange` → `goToNode(mainLine[ply], { silent: true })` (`Analysis.tsx:1806-1815`); it leaves lines open (D-07). Each landed M/B ply fires a prefetch, which is acceptable (cheap, cached 5 min). Do not track scrubs.
- **Keyboard:** arrows/wheel go through `useBoardNavigationInput` → `goBack`/`goForward` (`useAnalysisBoard.ts:787`); `goForward` prefers the lowest-id PV child at a fork (`useAnalysisBoard.ts:362-378`), so stepping works inside the line. No new shortcut (scope). The bar button is a native `<button>`, so Tab/Enter/Space work.
- **Known consequence of D-07 (existing chip behavior):** while a line stays open, stepping Forward through the game diverts into the line at its fork. Got it removes this.
- **Reset:** `handleReset` already clears `openLines`/`pendingFlaw` and all sidelines (`Analysis.tsx:1681-1690`). No change.

### Q7: React Compiler lint, max-depth, Analysis() residual

- The project's eslint uses `reactHooks.configs.flat.recommended` (react-hooks 7.1.1, compiler-derived rules: memoization preservation, refs, immutability) with `'react-hooks/set-state-in-effect': 'off'` and `'max-depth': ['error', 4]` (`frontend/eslint.config.js`) [VERIFIED]. There is no babel compiler plugin in `vite.config.ts` (`react()` only).
- Pattern to follow: control flow (loops, early returns) lives in module-scope pure functions called from `useMemo` (precedent: `findFocusedFlaw`/`buildFocusedPvLine`, `Analysis.tsx:281-291` comment). Put all branching in `lib/explainBar.ts`; the hook does `useMemo(() => resolveExplainBarState(...), [...])`.
- `useExplainBar` options (proposed): `{ isGameMode, gameId, flawMarkers, landingPly /* currentMainlinePly */, focusedFlaw, openLines, pendingFlaw, fastForwardRunning, mainLine, goToNode, deleteSubtree, setOpenLines, setPendingFlaw }`; returns `{ state: ExplainBarState; onExplain(): void; onGotIt(): void }`. Call it after `currentMainlinePly` (`Analysis.tsx:1324`) and after `fastForward` (`:1195`). `Analysis()` gains one hook call and three `<ExplainBar>` mounts. Its accepted complexity residual (memory: Analysis() 132) is not a gate; do not split `Analysis()` further in this phase.
- `ExplainBar` component: presentational, props `{ state, onExplain, onGotIt, className? }`, returns `null` for `hidden`. Exported only where imported (knip).
- Handlers in the hook are plain functions (the page passes plain handlers today, e.g. `handlePvChipClick`). Use `useCallback` only if a consumer needs stability. Under the compiler lint, manual memoization must be complete or omitted.

### Q8: Test patterns (vitest + testing-library)

- Pure lib tests: `src/lib/__tests__/tacticOrientation.test.ts` pattern, with a `marker(overrides: Partial<FlawMarker>)` factory and plain `expect`. No jsdom needed.
- Board hook tests: `src/hooks/__tests__/useAnalysisBoard.test.ts` uses `// @vitest-environment jsdom`, `renderHook`/`act`, and `vi.mock('@/lib/sounds', () => ({ playSound: vi.fn(), unlockAudio: vi.fn() }))`. It already covers `insertPvLine`, `deleteSubtree` recovery, and `goForward` PV preference (tests at lines 346, 384, 411).
- Derived-hook tests: `src/hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts` uses `renderHook` with a plain options object.
- Query hook 404 test: `src/hooks/__tests__/useEndgameInsights.test.tsx:124-138` mocks `apiClient.get` with an object carrying `isAxiosError: true, response: { status: 404 }` and a `QueryClient` with `retry: false`. Mirror it for `useTacticLines` (it calls `libraryApi.getTacticLines`, which uses `apiClient.get`, `api/client.ts:590-593`).
- Page tests: `src/pages/__tests__/Analysis.test.tsx` (3,137 lines) mocks `@/hooks/useLibrary` with `useTacticLines: () => ({ data: undefined, isFetching: false, isError: false })` (line 318) and `useLibraryGame` from a mutable `libraryGameState`. It has mobile-layout `matchMedia` overrides (line 638). Placement assertions need a mutable tactic-lines fixture added in the same style. Heavy file: no per-file timeouts (memory); hoist any `await import` into `beforeAll`.
- Verified runnable this session: `npx vitest run src/lib/__tests__/tacticOrientation.test.ts src/hooks/__tests__/useAnalysisBoard.test.ts` → 74 passed in 1.43s.

### Q9: Backend unchanged (confirmed)

- `fetch_tactic_lines` (`app/repositories/library_repository.py:2266-2399`) is not owner-scoped, loads the `game_flaws` row by `(game_id, ply)` regardless of colour, and returns both `missed_moves` (from `pos_n.pv`) and `allowed_moves` (`[flaw_move_san] + pv_to_san_list(board_after_flaw, pos_n1.pv)`) [VERIFIED]. Motif fields are null when there is no motif.
- `game_flaws` is M+B only and covers both players: `classify_game_flaws — emits FlawRecord for M+B across both players` (`app/services/eval_apply.py:1009-1010`), `# game_flaws rows are M+B-only, so inaccuracy tags never appear here.` (`library_service.py:457`) [VERIFIED].
- Null semantics: as in Q4. The PV strings for flaw plies are written by `_classify_and_fill_oracle` step 6 ("write game_positions.pv at ply N ... and N+1", `eval_apply.py:1015-1016`), which is why PV-complete games have both lines and unanalyzed games have neither.
- The only "backend-adjacent" change is client-side 404 handling. No schema, endpoint, or migration change.

### Anti-Patterns to Avoid
- **Reusing `handlePvChipClick` for Explain:** it toggles OFF on an open key (Explain must re-enter) and navigates to the fork (Explain must land on the first move).
- **Routing the prefetch through `fetchFlaw`:** spins unrelated active chips via `contextualPending`.
- **Recomputing focus:** use the existing `focusedFlaw` memo; a second containment walk can disagree with the overlays.
- **A follow-up effect that watches `openLines` to navigate after the graft:** one extra commit, fork flicker, two sounds. Use the `enter` flag in the graft effect.
- **Putting the bar in `MovesTab`:** double-mounts on mobile.
- **Free-form Umami event names (`analysis-explain-open`) via `trackEvent` or `data-umami-event`:** `frontend/CLAUDE.md` mandates `trackFeature` with registered targets; this overrides the CONTEXT naming example.
- **"Your move" copy:** `is_user` is the game owner, and viewers can open other users' games (memory: herring pool cross-user ownership bug). Use neutral copy.

## UI Recommendations (no UI-SPEC; planner should lock these)

All tokens and components below exist in the repo (read this session).

| Aspect | Recommendation | Grounding |
|--------|----------------|-----------|
| Container (desktop, in MovesCard) | `<div data-testid="analysis-explain-bar" className="flex shrink-0 items-center gap-2 border-t border-border px-2 py-2">` | MovesCard Card layout; mobile footer uses `border-t border-border bg-background px-2 py-2` (`Analysis.tsx:2580-2581`) |
| Container (mobile) | Same testid, `className="flex shrink-0 items-center gap-2 border-t border-border bg-background px-2 py-2"` directly above the footer | mirrors footer styling |
| Container (mid) | Wrap in `<Card className="w-full px-2 py-2">` under the BoardControls Card | matches `<Card className="w-full px-1">` around controls (`AnalysisBoardStage.tsx:162`) |
| Fixed height | Give the row a fixed min height equal to the button height so explain/got-it swaps never shift layout | avoids double layout shift |
| Headline (explain) | `{move_san}{glyph}` coloured by severity + ` is a blunder` / ` is a mistake`, `text-sm`, `truncate`, `min-w-0 flex-1` | `SEVERITY_GLYPH` (`lib/severityGlyph.ts:12-14`: blunder `'??'` `SEV_BLUNDER`, mistake `'?'` `SEV_MISTAKE`); `SEV_BLUNDER = 'oklch(0.58 0.19 25)'`, `SEV_MISTAKE = 'oklch(0.70 0.16 55)'` (`theme.ts:66-67`). Use only `symbol` and `color`, not the 17/19px `fontSize` (move-list glyph sizing). |
| Headline (got-it) | missed: `Better than {san}`; allowed: `Punishing {san}` (text-sm, muted foreground for the prefix) | neutral, viewer-agnostic; orientation from `line.orientation` |
| Explain button | `<Button variant="default" size="lg" data-testid="btn-analysis-explain"><Lightbulb aria-hidden="true" />Explain</Button>` (h-9, text-sm) | Primary = `default` (frontend/CLAUDE.md); `size="lg"` is `h-9 gap-1.5 px-2.5` (button.tsx); avoid `size="sm"` (`text-[0.8rem]`) |
| Got it button | `<Button variant="brand-outline" size="lg" data-testid="btn-analysis-explain-got-it"><Check aria-hidden="true" />Got it</Button>` | Secondary = `brand-outline` |
| Pending | `disabled` + `aria-busy="true"` on Explain while `state.pending` | one-render transient |
| Data attributes for tests | `data-state="explain" \| "got-it"` and `data-orientation="missed" \| "allowed"` on the container | deterministic assertions |
| Mobile tap target | `size="lg"` (h-9) is the in-app footer-row norm (`BoardControls` `md: 'h-9 w-9'`); use `h-11` via className only if UAT shows misses | BoardControls SIZE_CLASSES |
| Umami | Add `'explain-open'` and `'explain-close'` to `BOARD_TOOL_TARGETS` (`lib/analytics.ts:361-370`, siblings `'line-expand'`, `'line-delete'`). Call `trackFeature('board-tool', { target: 'explain-open' })` in `onExplain` (including re-entry) and `{ target: 'explain-close' }` in `onGotIt`. `page: 'analysis'` is added automatically by `trackFeature`. Never fire from effects. | `FeatureEventMap['board-tool']: { target: BoardToolTarget }`; analytics.test.ts already checks name lengths over `BOARD_TOOL_TARGETS` |

`BOARD_TOOL_TARGETS` verbatim (`lib/analytics.ts:361-370`): `'flip', 'paste-open', 'paste-load', 'fen-copy', 'pgn-copy', 'line-expand', 'line-delete', 'elo-reset'`.

### Tactic overlay gate for non-motif lines (must fix, part of this phase)

Verbatim `useAnalysisBoardArrows.ts:325-328` and `:347-350`:
```typescript
    const resolveIdx = isMissed
      ? (contextualTacticData.missed_tactic_ply_index ?? 0)
      : (contextualTacticData.allowed_tactic_ply_index ?? 1) - 1;
...
    const depthRaw =
      orientation === 'missed'
        ? (contextualTacticData.missed_depth ?? 0)
        : (contextualTacticData.allowed_depth ?? 0);
```
With null motif data, `resolveIdx = 0` tints the first PV move teal/crimson, and `toDisplayDepthForOrientation(0, o, false)` returns `0 + DEPTH_DISPLAY_OFFSET` (`tacticDepth.ts:68-75`). That produces a labelled tactic-colour arrow at the fork (`buildPvArrow`, `tacticArrows.ts:30-48`), i.e. a fake 1-move tactic. Even worse, `TacticLinesResponse.missed_motif/missed_depth` are returned regardless of the confidence gate, while `FlawMarker` motif fields are null below it (`types/library.ts:166-177`). The app also hides opponent motifs on the move list (`useAnalysisGemMarkers.ts:342-343`: `const missedMotif = fm.is_user ? fm.missed_tactic_motif : null;`).

**Recommendation:** pass `focusedLineHasMotif: boolean` into `useAnalysisBoardArrows`, computed as "the focused line's marker `is_user` AND `marker[orientation === 'missed' ? 'missed_tactic_motif' : 'allowed_tactic_motif'] !== null`". When false: `sidelineNodeColors` stays empty, and `pvSidelineArrows` builds the next-move arrow with `isPayoff = true` (`PAYOFF_MOVE_ARROW = 'rgba(59, 130, 246, 0.5)'`, `theme.ts:490`, no label). The user still gets a "next move" arrow while stepping. Chip-opened lines always satisfy the gate, so their overlay is unchanged.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Grafting the PV | A second graft path or `makeMove` loop | Existing graft effect + `insertPvLine` (single batched updater) | `makeMove` in a loop chains onto a stale parent (`useAnalysisBoard.ts:495-500` L-1/L-7 note) |
| Focus/containment | New subtree walk | `focusedFlaw` memo (`findFocusedFlaw`) | One source of truth with overlays |
| Removing a line | Manual node filtering | `deleteSubtree(rootId)` | Handles descendants, pvNodeIds, cursor recovery |
| PV fetching/cache | `fetch`/axios in the component | `useTacticLines` (same key) | Dedupe + 5-min cache shared with chips |
| Severity colour/glyph | Literal colours | `SEVERITY_GLYPH` / `SEV_*` from theme | frontend/CLAUDE.md theme rule |
| Event tracking | `data-umami-event` / `trackEvent` | `trackFeature('board-tool', …)` | Registry is build-checked |

**Key insight:** the move-tree hook's guarantees (single-updater grafts, recovery on delete, PV-preferring Forward) are what make Explain small. Any parallel mechanism would re-introduce the stale-parent and duplicate-sideline bugs those guarantees exist to prevent.

## Common Pitfalls

### Pitfall 1: Stuck `pendingFlaw`
**What goes wrong:** Explain on a line that grafts nothing leaves `pendingFlaw` set forever; the bar stays pending and chips read active.
**Why:** graft effect early-returns on `forkNodeId === undefined || pvMoves.length === 0` without clearing (`useAnalysisRouteSeeding.ts:248`).
**How to avoid:** `usableExplainLines` length/ply guards; never offer Explain unless the chosen line grafts at least one node.
**Warning signs:** `activePvKeys` contains a key absent from `openLines` after the data resolved.

### Pitfall 2: Fake tactic overlay on non-motif lines
See "Tactic overlay gate" above. **Warning sign:** a numbered teal/crimson arrow on a flaw that has no motif chip.

### Pitfall 3: 404 noise from prefetch
**What goes wrong:** marker/game_flaws drift → 404 → one retry + Sentry event per landing.
**How to avoid:** 404 → null in `useTacticLines`.
**Warning signs:** Sentry issues tagged `source: tanstack-query` with `queryKey ['tactic-lines', …]` and `httpStatus 404`.

### Pitfall 4: Two-commit navigation flicker
**What goes wrong:** navigating to the fork in the click handler and then to the root in an effect paints the fork for a frame and plays two sounds.
**How to avoid:** the `enter` flag + no fork navigation in `onExplain`.

### Pitfall 5: Allowed line duplicating the main line
**What goes wrong:** when the user actually played the refutation, the grafted allowed line repeats the main-line moves as a sibling sideline.
**Why:** `insertPvLine` never reuses existing children (`useAnalysisBoard.ts:507-548`). Same for chips today.
**How to avoid:** accept it (pedagogically fine, matches chips). Out of scope to change `insertPvLine`; mention in UAT notes.

### Pitfall 6: Move-list viewport shrink when the bar appears late
**What goes wrong:** on desktop the bar appears inside MovesCard after a non-cached fetch, shrinking the tree scroller; a current node at the very bottom may clip.
**How to avoid:** fixed-height row; acceptable residual. VariationTree re-scrolls only on `currentNodeId`/`topAlignSeq` change (`VariationTree.tsx:930-953`).

### Pitfall 7: Stale `nextId` snapshot (pre-existing, low)
The graft effect snapshots `rootNodeId = nextId` from render; a `graftLine` (background search) updater queued earlier in the same batch would shift ids. This is a pre-existing chip risk, not introduced here. Do not fix in this phase; if UAT shows Explain landing on a wrong node, this is the first suspect.

### Pitfall 8: Free moves inside the line get deleted by Got it
Got it deletes the whole subtree including free moves the user played off PV nodes. This matches chip toggle-off. Accept and document.

## Code Examples

### Explain handler (proposed, inside `useExplainBar`)
```typescript
// Values from repo: flawKey(...), openLines Map<string, OpenLine>, goToNode, setPendingFlaw,
// unlockAudio (lib/sounds, exported), trackFeature('board-tool', ...).
function onExplain(): void {
  if (state.kind !== 'explain' || state.pending) return;
  unlockAudio(); // gesture-path unlock; the graft effect's goToNode runs outside the gesture
  trackFeature('board-tool', { target: 'explain-open' });
  const existing = openLines.get(flawKey(state.flaw));
  if (existing != null) {
    goToNode(existing.rootNodeId); // D-07 re-entry, no second graft
    return;
  }
  setPendingFlaw({ ...state.flaw, enter: true }); // graft effect lands on rootNodeId (D-05)
}
```

### Graft-effect addition (`useAnalysisRouteSeeding.ts`)
```typescript
    const rootNodeId = nextId;
    insertPvLine(pvMoves, forkNodeId);
    // Explain (D-05) lands on the first grafted move instead of parking at the fork like a
    // chip: queued after insertPvLine's updater, so the new node exists and both commit together.
    if (pendingFlaw.enter) goToNode(rootNodeId);
    setOpenLines((prev) => new Map(prev).set(key, { rootNodeId, ply: pendingFlaw.ply, orientation: pendingFlaw.orientation }));
    setPendingFlaw(null);
```

### 404 → null (`useLibrary.ts`)
```typescript
// Precedent: hooks/useEndgameInsights.ts:53-72.
const HTTP_NOT_FOUND = 404;
queryFn: async () => {
  try {
    return await libraryApi.getTacticLines(gameId!, ply!);
  } catch (err) {
    // Bug fix: flaw_markers are computed live from evals while game_flaws rows are written at
    // classify time; they can drift, so a landing prefetch can 404. Treat it as "no lines"
    // instead of retrying and reporting to Sentry.
    if (axios.isAxiosError(err) && err.response?.status === HTTP_NOT_FOUND) return null;
    throw err;
  }
},
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Singleton `pvLine` overlay | Multi-line `openLines` + `focusedPvLine` (flat siblings) | before this phase | Explain can coexist with chip lines |
| `?flaw_ply=` tactic mode | In-tree graft via chips | before this phase | Explain reuses the in-tree path |
| Free-form `trackEvent` names | Typed `trackFeature` registry | Phase 229-era | New events are target additions, not names |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | TanStack v5 dedupes two observers on the same key into one request and serves the cache synchronously on key change within staleTime | Q4 | Low: worst case one extra request; the click still works once data lands (bar would show `pending`) |
| A2 | React batches `insertPvLine` + `goToNode` updaters from one effect into a single commit | Q1 | Low: worst case a one-frame fork flash; behavior still correct |
| A3 | Marker/game_flaws drift causes ply-level 404s at a rate worth hardening (inferred from game-level count mismatch, 290/13,776 dev games) | Q4 | Low: the 404→null change is cheap and safe even if the rate is near zero |
| A4 | Mid-layout placement under the board controls (not in D-03) is acceptable to the owner | Q5 | Low: a slot move, UAT-visible |
| A5 | Copy "X is a blunder" / "Better than X" / "Punishing X" and the Lightbulb/Check icons are acceptable without a UI-SPEC | UI Recommendations | Low: owner chose to plan without UI-SPEC; copy is a constant to tweak |

## Open Questions

1. **Tactic-overlay gate for non-motif lines.** Known: without it, Explain draws a fake "1" tactic arrow. Unclear: whether the owner wants the plain blue next-move arrow or no arrow at all. Recommendation: plain unlabeled `PAYOFF_MOVE_ARROW`, include in the plan, confirm in UAT.
2. **Mid layout placement.** Recommendation: under BoardControls in `DesktopBoardStage` when `isMid`; owner confirms in UAT.
3. **Got-it at the allowed fork (= flaw node).** With an allowed line open (chip or Explain), returning to the flaw node shows Got it, not Explain. This is consistent with `findFocusedFlaw`; the CONTEXT accepts it via the discretion bullet. No action.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | vitest/eslint/tsc | ✓ | v24.19.0 | — |
| npm | scripts | ✓ | 11.17.0 | — |
| frontend node_modules (vitest, eslint) | tests/lint | ✓ | vitest 5.0.5 | — |
| Dev Postgres (`flawchess-dev-db-1`) | Manual browser UAT only | ✓ running | 18.6 | — |

**Missing dependencies:** none. Graph context (Step 1.3) not used; no graphify query was needed for this frontend-local seam.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest 5.0.5 + @testing-library/react 16.3.2 (jsdom per file via `// @vitest-environment jsdom`) |
| Config file | `frontend/vite.config.ts` `test` block (`testTimeout` 20s, `hookTimeout` 30s, `setupFiles: ['src/vitest.setup.ts']`) |
| Quick run command | `cd frontend && npx vitest run src/lib/__tests__/explainBar.test.ts src/hooks/analysis/__tests__/useExplainBar.test.ts src/components/analysis/__tests__/ExplainBar.test.tsx` |
| Full suite command | `cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip` |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| D-08 | `eligibleExplainMarker` returns M/B either side; null for inaccuracy, missing ply, null markers | unit | `npx vitest run src/lib/__tests__/explainBar.test.ts` | ❌ Wave 0 |
| D-04/D-09/D-10 | `chooseExplainOrientation` preferred, fallback, null; `usableExplainLines` ply-0 missed false, `allowed_moves.length === 1` false | unit | same | ❌ Wave 0 |
| D-03/D-11 | `resolveExplainBarState`: hidden for not-game-mode, ff running, unrelated pending, sideline (-1), data undefined, data null; explain with `pending` when pending matches; got-it for focused open line incl. fork equality | unit | same | ❌ Wave 0 |
| D-05 | Harness (real `useAnalysisBoard` + `useAnalysisRouteSeeding` graft + `useExplainBar`, mocked `useTacticLines`): Explain on user flaw lands on node whose SAN = `missed_moves[0]`; on opponent flaw lands on SAN = `allowed_moves[1]` | hook integration | `npx vitest run src/hooks/analysis/__tests__/useExplainBar.test.ts` | ❌ Wave 0 |
| D-06 | Same harness: goBack/goForward step within the line; Got it removes subtree nodes + openLines key and lands on `mainLine[P]` for both orientations | hook integration | same | ❌ Wave 0 |
| D-07 | Same harness: navigate away, return to flaw node, Explain → navigates to existing root, node count unchanged (no duplicate graft); pre-opened chip key (same `flawKey`) → Explain re-enters, no second graft | hook integration | same | ❌ Wave 0 |
| D-05 (chips unchanged) | Graft without `enter` still parks at fork | hook integration | same (or extend existing seeding coverage) | ❌ Wave 0 |
| D-11 hardening | `useTacticLines` returns `null` on 404 with `isError` false; other errors still error | unit (query hook) | `npx vitest run src/hooks/__tests__/useLibrary.test.ts` | ✅ file exists, new cases |
| Overlay gate | Non-motif focused line: no sideline colors, unlabeled payoff arrow; motif line unchanged | unit (hook) | `npx vitest run src/hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts` | ✅ file exists, new cases |
| D-01/D-02 + UI | `ExplainBar` renders exactly one button; label/testid per state; null when hidden; `trackFeature('board-tool', {target:'explain-open'/'explain-close'})` on click only, nothing on mount | component | `npx vitest run src/components/analysis/__tests__/ExplainBar.test.tsx` | ❌ Wave 0 |
| D-03 placement | Desktop: `analysis-explain-bar` inside `analysis-movelist-card`; mobile: bar is the element right before `analysis-mobile-footer`; free play: absent | page | `npx vitest run src/pages/__tests__/Analysis.test.tsx -t "Explain"` | ✅ file exists, needs a mutable `useTacticLines` fixture in its `vi.mock('@/hooks/useLibrary')` |
| Analytics registry | New targets pass name-length checks | unit | `npx vitest run src/lib/__tests__/analytics.test.ts` | ✅ (auto-covers `BOARD_TOOL_TARGETS`) |
| Visual/UX | Real browser: Explain → line + first move, Back/Forward, Got it, Jump interplay, mobile 360px | manual (Claude-run browser UAT per memory) | — | manual |

### Sampling Rate
- **Per task commit:** the quick run command (only the touched test files).
- **Per wave merge:** `cd frontend && npm test -- --run` plus `npm run build` (type-check).
- **Phase gate:** full frontend gate (lint, build, test, knip) green before `/gsd-verify-work`. Backend is untouched, so the backend gate is only needed at squash-merge per CLAUDE.md.

### Wave 0 Gaps
- [ ] `frontend/src/lib/__tests__/explainBar.test.ts` (D-03/04/08/09/10/11 pure logic)
- [ ] `frontend/src/hooks/analysis/__tests__/useExplainBar.test.ts` (D-05/06/07 harness; mock `@/lib/sounds` and `@/hooks/useLibrary`)
- [ ] `frontend/src/components/analysis/__tests__/ExplainBar.test.tsx` (UI + tracking; spy `trackFeature` or `window.umami.track`)
- [ ] Mutable tactic-lines fixture in `Analysis.test.tsx`'s `@/hooks/useLibrary` mock (placement tests)
- No framework install needed.

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (existing `current_active_user` on the endpoint) | — |
| V3 Session Management | no | — |
| V4 Access Control | no new surface (endpoint intentionally not owner-scoped, `library.py:382-387`) | unchanged |
| V5 Input Validation | yes (rendering API strings) | React text rendering (auto-escaped); SANs are replayed through chess.js inside `insertPvLine` with try/catch (`useAnalysisBoard.ts:520-527`) |
| V6 Cryptography | no | — |

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed PV SAN crashes setState updater | Denial of service | Existing try/catch break in `insertPvLine` |
| PII in analytics | Information disclosure | Enumerated `trackFeature` targets only, no SAN/ply/game id in event data |

## Sources

### Primary (HIGH confidence, read this session)
- `frontend/src/pages/Analysis.tsx` (findFocusedFlaw 292-327, state 440-450, focus/fetch 546-570, initialTactic 790-835, fastForward 1179-1213, currentMainlinePly 1324-1327, handlers 1681-1815, render 2085-2755)
- `frontend/src/hooks/analysis/useAnalysisRouteSeeding.ts` (full), `frontend/src/hooks/useAnalysisBoard.ts` (types, goForward, goToNode, insertPvLine, deleteSubtree, sounds)
- `frontend/src/lib/analysisTactics.ts`, `frontend/src/lib/tacticOrientation.ts`, `frontend/src/hooks/useLibrary.ts`, `frontend/src/lib/queryClient.ts`, `frontend/src/hooks/useEndgameInsights.ts`
- `frontend/src/hooks/analysis/useAnalysisBoardArrows.ts` (300-375), `useAnalysisGemMarkers.ts` (325-357), `frontend/src/lib/tacticDepth.ts`, `frontend/src/lib/tacticArrows.ts`
- `frontend/src/components/analysis/AnalysisDesktopCards.tsx`, `AnalysisBoardStage.tsx`, `AnalysisTabs.tsx` (MovesTab, AnalysisTabs root), `components/ui/button.tsx`, `components/board/BoardControls.tsx`
- `frontend/src/lib/analytics.ts`, `frontend/src/lib/theme.ts`, `frontend/src/lib/severityGlyph.ts`, `frontend/src/types/library.ts`
- `app/repositories/library_repository.py` 2249-2399, `app/routers/library.py` 370-393, `app/services/library_service.py` 195-420/457, `app/services/eval_apply.py` 995-1016, `app/services/tactic_detector.py` 248-269
- Dev DB read-only probes (`BEGIN READ ONLY`): game_flaws vs oracle counts; PV null rates on game_flaws
- `frontend/CLAUDE.md`, `CLAUDE.md`, `frontend/eslint.config.js`, `frontend/vite.config.ts`, `frontend/knip.json`, existing test files listed in Q8

### Secondary / Tertiary
- None needed (no external libraries researched; TanStack dedupe semantics tagged [ASSUMED] A1).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, no new deps; versions read from package.json / node_modules.
- Architecture: HIGH, every seam quoted from source; two batching/dedupe behaviors marked ASSUMED (low risk).
- Pitfalls: HIGH for overlay gate and stuck pending (code-traced); MEDIUM for 404 rate (game-level proxy).

**Research date:** 2026-11-05
**Valid until:** 2026-12-05 (stable code area; re-check if Analysis.tsx tactic-line code changes first)
