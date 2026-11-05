# Phase 245: Analysis Contextual Explain Bar for Flaws - Pattern Map

**Mapped:** 2026-11-05
**Files analyzed:** 17 (6 new incl. tests, 11 modified)
**Analogs found:** 17 / 17 (all paths below are git-tracked; frontend-only phase)

RESEARCH.md already quotes most seams verbatim (Q1-Q8). This map points each file at its analog; line refs are to `frontend/src/`.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `lib/explainBar.ts` (NEW) | utility (pure) | transform | `lib/tacticOrientation.ts` (`tacticOrientationAtPly`) + `findFocusedFlaw` in `pages/Analysis.tsx:292-327` | exact |
| `lib/__tests__/explainBar.test.ts` (NEW) | test | transform | `lib/__tests__/tacticOrientation.test.ts` | exact |
| `hooks/analysis/useExplainBar.ts` (NEW) | hook | event-driven + request-response | `hooks/analysis/useAnalysisRouteSeeding.ts` (options-interface hook) | role-match |
| `hooks/analysis/__tests__/useExplainBar.test.ts` (NEW) | test | event-driven | `hooks/__tests__/useAnalysisBoard.test.ts` (renderHook + sounds mock) | role-match |
| `components/analysis/ExplainBar.tsx` (NEW) | component | presentational | `components/analysis/EngineUnsupportedNotice.tsx` | role-match |
| `components/analysis/__tests__/ExplainBar.test.tsx` (NEW) | test | component | `components/analysis/__tests__/AnalysisTabs.tracking.test.tsx` / `EngineUnsupportedNotice.test.tsx` | role-match |
| `lib/analysisTactics.ts` (EDIT) | utility/types | — | itself, `TacticRef` line ~28 | exact |
| `hooks/analysis/useAnalysisRouteSeeding.ts` (EDIT) | hook | event-driven | itself, graft effect ~235-260 | exact |
| `hooks/useLibrary.ts` (EDIT `useTacticLines`) | hook (query) | request-response | `hooks/useEndgameInsights.ts:53-72` | exact |
| `hooks/__tests__/useLibrary.test.ts` (EDIT) | test | request-response | `hooks/__tests__/useEndgameInsights.test.tsx:124-138` | exact |
| `hooks/analysis/useAnalysisBoardArrows.ts` (EDIT) | hook (derived) | transform | itself ~325-350 | exact |
| `hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts` (EDIT) | test | transform | itself | exact |
| `components/analysis/AnalysisDesktopCards.tsx` (EDIT `MovesCard`) | component | slot | itself 100-124 | exact |
| `components/analysis/AnalysisBoardStage.tsx` (EDIT `DesktopBoardStage`) | component | slot | itself ~155-165 | exact |
| `lib/analytics.ts` (EDIT `BOARD_TOOL_TARGETS`) | config | — | itself 361-370 | exact |
| `pages/Analysis.tsx` (EDIT) | page | wiring | `handlePvChipClick` 1776-1800, mobile footer ~2576-2598 | exact |
| `pages/__tests__/Analysis.test.tsx` (EDIT) | test | page | itself, `vi.mock('@/hooks/useLibrary')` ~318, matchMedia ~638 | exact |

## Pattern Assignments

### `lib/explainBar.ts` (utility, transform)

**Analog:** `lib/tacticOrientation.ts` + module-scope `findFocusedFlaw` (`pages/Analysis.tsx:281-327`, comment at 281-291 explains why control flow lives at module scope for the React Compiler lint).

- Imports: `import type { FlawMarker, TacticLinesResponse } from '@/types/library';` and `import { flawKey, type TacticRef, type OpenLine } from '@/lib/analysisTactics';`
- Named constants instead of magic numbers (`ALLOWED_PREPEND_LEN = 1`, `MIN_MISSED_FORK_PLY = 1`), literal unions `'missed' | 'allowed'`, explicit return types.
- Function bodies: copy the sketches in RESEARCH.md Q3 (`eligibleExplainMarker`, `usableExplainLines`, `chooseExplainOrientation`, `resolveExplainBarState` ordered rules 1-7, `ExplainBarState` discriminated union). Early returns only, no nested loops (max-depth 4).
- knip: export only what the hook/component/tests import.

### `lib/__tests__/explainBar.test.ts`

**Analog:** `lib/__tests__/tacticOrientation.test.ts` lines 1-30. Copy the factory verbatim:
```typescript
import { describe, expect, it } from 'vitest';
import type { FlawMarker } from '@/types/library';

function marker(overrides: Partial<FlawMarker>): FlawMarker {
  return {
    ply: 10, severity: 'blunder', tags: [], is_user: true, move_san: 'Qh5',
    allowed_tactic_motif: null, allowed_tactic_confidence: null, allowed_tactic_depth: null,
    missed_tactic_motif: null, missed_tactic_confidence: null, missed_tactic_depth: null,
    ...overrides,
  };
}
```
No jsdom pragma needed. Add an analogous `tacticLines(overrides: Partial<TacticLinesResponse>)` factory.

### `hooks/analysis/useExplainBar.ts` (hook)

**Analog:** `hooks/analysis/useAnalysisRouteSeeding.ts` lines 1-90.
- File-header docblock explaining WHY the hook exists (keeps `Analysis()` from growing; accepted residual).
- Typed `export interface UseExplainBarOptions { ... }` grouped with `// ── Section ──` comments, setters typed `Dispatch<SetStateAction<Map<string, OpenLine>>>` exactly as seeding lines 72-73:
```typescript
import type { Dispatch, SetStateAction } from 'react';
import type { NodeId } from '@/hooks/useAnalysisBoard';
import { flawKey, type OpenLine, type PendingFlaw } from '@/lib/analysisTactics';
...
  goToNode: (id: NodeId, opts?: { silent?: boolean }) => void;
  setPendingFlaw: (flaw: PendingFlaw | null) => void;
  setOpenLines: Dispatch<SetStateAction<Map<string, OpenLine>>>;
```
- Prefetch: second observer `useTacticLines(gameId, eligiblePly, eligiblePly != null && isGameMode)` from `@/hooks/useLibrary` (do NOT route through `fetchFlaw`, Analysis.tsx:565-570).
- State: `useMemo(() => resolveExplainBarState(...), [...])` (complete deps or none, compiler lint).
- Handlers: copy RESEARCH.md "Explain handler" (`unlockAudio()` from `@/lib/sounds`, `trackFeature('board-tool', { target: 'explain-open' })`, re-entry `goToNode(existing.rootNodeId)`, else `setPendingFlaw({ ...flaw, enter: true })`) and Q2 `onGotIt` (delete-from-Map updater copied from `handlePvChipClick`, Analysis.tsx:1789-1794):
```typescript
      deleteSubtree(existing.rootNodeId);
      setOpenLines((prev) => {
        const next = new Map(prev);
        next.delete(key);
        return next;
      });
```
then `const flawNodeId = mainLine[line.ply]; if (flawNodeId !== undefined) goToNode(flawNodeId);` (noUncheckedIndexedAccess guard, same as 1803-1804).
- Do NOT reuse `handlePvChipClick` (it toggles off and navigates to the fork).

### `hooks/analysis/__tests__/useExplainBar.test.ts`

**Analog:** `hooks/__tests__/useAnalysisBoard.test.ts` (`// @vitest-environment jsdom`, `renderHook`/`act`, `vi.mock('@/lib/sounds', () => ({ playSound: vi.fn(), unlockAudio: vi.fn() }))`; existing `insertPvLine`/`deleteSubtree`/`goForward` PV tests at ~346, 384, 411). Harness: real `useAnalysisBoard` + `useAnalysisRouteSeeding` + `useExplainBar` in one `renderHook`, `vi.mock('@/hooks/useLibrary')` returning a fixture. Hoist any `await import` into `beforeAll`; no per-file timeouts.

### `components/analysis/ExplainBar.tsx` (component)

**Analog:** `components/analysis/EngineUnsupportedNotice.tsx` (docblock header, `import type { ReactElement } from 'react'`, returns `null` when nothing to show, `data-testid` on root, `text-sm` + `text-muted-foreground` tokens):
```tsx
  if (reason === null) return null;
  return (
    <div role="status" data-testid={`analysis-${card}-unsupported`}
      className="flex h-full flex-col justify-center gap-1 px-2 py-1 text-sm text-muted-foreground">
```
- Props `{ state: ExplainBarState; onExplain: () => void; onGotIt: () => void; className?: string }`, merge with `cn()` (caller className last per tailwind-merge note).
- Buttons: `Button` from `@/components/ui/button`, `variant="default" size="lg"` (Explain, `data-testid="btn-analysis-explain"`, `Lightbulb` icon) and `variant="brand-outline" size="lg"` (Got it, `btn-analysis-explain-got-it`, `Check` icon); never `size="sm"`.
- Severity glyph/colour: `SEVERITY_GLYPH` from `@/lib/severityGlyph` (use `symbol`/`color` only).
- Container attrs: `data-testid="analysis-explain-bar" data-state data-orientation`; copy constants per RESEARCH "UI Recommendations".
- Tracking lives in the hook handlers (click only), not in the component or an effect.

### `components/analysis/__tests__/ExplainBar.test.tsx`

**Analog:** `components/analysis/__tests__/AnalysisTabs.tracking.test.tsx` (tracking assertions) and `EngineUnsupportedNotice.test.tsx` (null-render case).

### `lib/analysisTactics.ts` (EDIT)
Next to line ~28 `export type TacticRef = { ply: number; orientation: 'missed' | 'allowed' };` add `export type PendingFlaw = TacticRef & { enter?: boolean };` with a doc comment. Update `pendingFlaw` state type in `Analysis.tsx:447-450` and seeding options lines 59/72.

### `hooks/analysis/useAnalysisRouteSeeding.ts` (EDIT)
Graft effect: insert after `insertPvLine(pvMoves, forkNodeId);` exactly the RESEARCH "Graft-effect addition" (`if (pendingFlaw.enter) goToNode(rootNodeId);` + WHY comment). Widen `contextualTacticData: TacticLinesResponse | undefined` (line ~60) to `| null | undefined`; the existing `== null` guard already handles it. No deps-array change.

### `hooks/useLibrary.ts` `useTacticLines` (EDIT)
**Analog:** `hooks/useEndgameInsights.ts:53-72`:
```typescript
  return useQuery<EndgameInsightsResponse | null>({
    queryKey: CACHED_ENDGAME_INSIGHTS_KEY,
    queryFn: async () => {
      try { ... return response.data; }
      catch (err) {
        if (axios.isAxiosError(err) && err.response?.status === 404) { return null; }
        throw err;
      }
    },
```
Constant precedent: `const HTTP_NOT_FOUND = 404;` (`hooks/usePushCapability.ts:27`). Return type becomes `useQuery<TacticLinesResponse | null>`; add bug-fix comment (marker/game_flaws drift). Keep queryKey `['tactic-lines', gameId, ply]` unchanged. Callers typed `| undefined` must widen.

### `hooks/__tests__/useLibrary.test.ts` (EDIT)
**Analog:** `hooks/__tests__/useEndgameInsights.test.tsx:124-138`:
```typescript
    const axios404 = Object.assign(new Error('404'), {
      isAxiosError: true, response: { status: 404, data: { detail: 'Flaw not found' } },
    });
    vi.mocked(apiClient.get).mockRejectedValue(axios404);
    const { result } = renderHook(() => useTacticLines(1, 10, true), { wrapper });
    await waitFor(() => { expect(result.current.isSuccess).toBe(true); });
    expect(result.current.data).toBeNull();
    expect(result.current.isError).toBe(false);
```
Plus a non-404 case still erroring (QueryClient `retry: false`).

### `hooks/analysis/useAnalysisBoardArrows.ts` (EDIT)
Add option `focusedLineHasMotif: boolean` to `UseAnalysisBoardArrowsOptions`; at ~325-328 (`resolveIdx`) and ~347-350 (`depthRaw`) branch: when false, leave `sidelineNodeColors` empty and build the next-move arrow with `isPayoff = true` (`PAYOFF_MOVE_ARROW`, theme.ts:490). Computed in Analysis.tsx from the focused line's marker: `is_user && marker[orientation === 'missed' ? 'missed_tactic_motif' : 'allowed_tactic_motif'] !== null` (mirrors `useAnalysisGemMarkers.ts:342-343`). Tests: extend `useAnalysisBoardArrows.test.ts` (plain options object to `renderHook`).

### `components/analysis/AnalysisDesktopCards.tsx` `MovesCard` (EDIT)
Current (lines 100-124):
```tsx
export type MovesCardProps = { onOpenPasteModal: () => void; fen: string; getPgn: () => string;
  variationTreeProps: Omit<VariationTreePanelProps, 'variant'>; };
export function MovesCard({ onOpenPasteModal, fen, getPgn, variationTreeProps }: MovesCardProps): ReactElement {
  return (
    <Card data-testid="analysis-movelist-card" className="relative flex min-h-0 flex-1 flex-col">
      <CardHeader ...>...</CardHeader>
      <VariationTreePanel variant="responsive" {...variationTreeProps} />
    </Card>
```
Add `footer?: ReactNode` (doc-commented), render `{footer}` after `<VariationTreePanel>`. Bar container itself carries `shrink-0 border-t border-border`.

### `components/analysis/AnalysisBoardStage.tsx` `DesktopBoardStage` (EDIT)
After the controls card (~162-164):
```tsx
        <Card className="w-full px-1">
          <BoardControls {...boardControlsProps} flat size="sm" />
        </Card>
```
add `{isMid && explainBar}` with a new optional `explainBar?: ReactNode` prop, wrapped per UI recs (`<Card className="w-full px-2 py-2">` or the bar's own className). Follow the existing JSX-comment style explaining placement. Flag mid placement for UAT (not in D-03).

### `lib/analytics.ts` (EDIT)
Append `'explain-open', 'explain-close'` to `BOARD_TOOL_TARGETS` (lines 361-370, after `'elo-reset'`). `analytics.test.ts` auto-covers name lengths.

### `pages/Analysis.tsx` (EDIT)
- `pendingFlaw` state typed `PendingFlaw | null` (447-450).
- Call `useExplainBar({...})` after `fastForward` (~1195) and `currentMainlinePly` (~1324-1327); pass existing `focusedFlaw` memo (546-549), never recompute.
- Mount sites: `MovesCard footer={<ExplainBar ... />}` (~2707); `DesktopBoardStage explainBar={...}` (mid, ~2454-2500); mobile: new sibling between `{analysisTabs}` (~2576) and `<div data-testid="analysis-mobile-footer" className="... border-t border-border bg-background px-2 py-2">` (~2578-2598). Never inside `MovesTab` (double-mount on mobile).
- Compute `focusedLineHasMotif` for the arrows hook.

### `pages/__tests__/Analysis.test.tsx` (EDIT)
Replace the static `useTacticLines: () => ({ data: undefined, isFetching: false, isError: false })` (~318) with a mutable fixture variable, same style as `libraryGameState`. Mobile assertions reuse the `matchMedia` override (~638). Assert bar inside `analysis-movelist-card` (desktop) and immediately before `analysis-mobile-footer` (mobile).

## Shared Patterns

### Analytics
**Source:** `lib/analytics.ts` `trackFeature`; usage e.g. `components/results/LibraryGameCard.tsx:587` `trackFeature('action', { target: 'chip-cycle' });`
**Apply to:** `useExplainBar` handlers only (click path, never effects/mount, no SAN/ply/game id).

### Out-of-bounds index guard (noUncheckedIndexedAccess)
**Source:** `Analysis.tsx:1803-1804` `const forkNodeId = mainLine[...]; if (forkNodeId !== undefined) goToNode(forkNodeId);`
**Apply to:** every `mainLine[...]` lookup in the hook.

### Functional Map updaters for `openLines`
**Source:** `Analysis.tsx:1789-1794` (delete) and seeding graft `new Map(prev).set(key, {...})`.
**Apply to:** Got it, graft.

### Theme / buttons
**Source:** `lib/theme.ts` (`SEV_BLUNDER`, `SEV_MISTAKE`, `PAYOFF_MOVE_ARROW`), `lib/severityGlyph.ts`, `components/ui/button.tsx` variants `default` / `brand-outline`, size `lg`.
**Apply to:** `ExplainBar.tsx`, arrows edit.

### Error handling
No new `Sentry.captureException` (global `QueryCache.onError` in `lib/queryClient.ts`). 404 swallowed in `queryFn` only.

## No Analog Found

None. Every new file has a role-match analog; logic bodies are specified in RESEARCH.md Q1-Q3 and "Code Examples".

## Metadata

**Analog search scope:** `frontend/src/lib`, `frontend/src/hooks`, `frontend/src/hooks/analysis`, `frontend/src/components/analysis`, `frontend/src/pages`, related `__tests__`
**Files scanned:** ~14
**Pattern extraction date:** 2026-11-05
