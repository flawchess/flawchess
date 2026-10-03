# Phase 228: Settings Page - Pattern Map

**Mapped:** 2026-10-03
**Files analyzed:** 24 (6 new source/test files + ~18 modified)
**Analogs found:** 24 / 24 (all paths under `frontend/src/`, all git-tracked)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `lib/engineSettings.ts` (NEW) | store | event-driven (localStorage + useSyncExternalStore) | `lib/sounds.ts` lines 80-87, 162-198 | exact |
| `lib/__tests__/engineSettings.test.ts` (NEW) | test | unit | existing sounds/useUserFlag tests | role-match |
| `components/settings/SettingsPanel.tsx` (NEW) | component | request-response (writes store, trackEvent) | `components/filters/FlawFilterControl.tsx` 593-625 (ToggleGroup) + `components/train/TrainScheduleSettings.tsx` 351-358 (Switch) | role-match |
| `components/settings/SettingsSheetButton.tsx` (NEW) | component | event-driven (open state) | `components/filters/MobileFilterDrawer.tsx` 53-86 | exact |
| `components/settings/__tests__/*.test.tsx` (NEW) | test | component | `App.test.tsx` (~74 vaul jsdom shims) | role-match |
| `pages/Settings.tsx` (NEW) | page | static shell | `pages/Privacy.tsx` (main + testid shell; no PublicHeader, it lives in ProtectedLayout) | role-match |
| `hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts` (NEW) | test | renderHook | other `hooks/analysis/__tests__/*` | role-match |
| `App.tsx` (MOD) | route/nav | — | itself: NavHeader 358-376, AnalysisMobileHeader 425-446, MobileMoreDrawer 612-620, ROUTE_TITLES 139, Routes 1036 | exact |
| `components/bots/BotGameMobileLayout.tsx` (MOD) | component | — | itself, top row line 99-108 | exact |
| `hooks/useStockfishEngine.ts` (MOD) | hook | streaming (UCI worker) | `hooks/useStockfishGradingEngine.ts:285` (per-search setoption while idle) | exact |
| `hooks/analysis/useAnalysisBoardArrows.ts` (MOD) | hook | transform | itself 60-62, 343-388 | exact |
| `hooks/analysis/useAnalysisEngineLines.ts` (MOD) | hook | transform | itself 311, 346-367 | exact |
| `pages/Analysis.tsx` (MOD) | page | — | itself 531, 931, 955-966, 1071, 1682 | exact |
| `components/analysis/EngineLines.tsx` (MOD) | component | render | itself 38, 96, 108-122, 266, 394 | exact |
| `components/analysis/FlawChessEngineLines.tsx` (MOD) | component | render | itself 48, 88, 314, 441-460 | exact |
| `components/analysis/AnalysisTabs.tsx`, `AnalysisDesktopCards.tsx` (MOD) | component | render | AnalysisTabs 441-445, 646; DesktopCards 70 | exact |
| `components/train/TrainReveal.tsx`, `TrainSolveScreen.tsx`, `hooks/useTrainFreePlay.ts`, `lib/trainArrows.ts` (MOD) | component/hook/util | transform | TrainReveal 461; TrainSolveScreen 1220, 1331-1334; useTrainFreePlay 227-263; trainArrows 154, 229 | exact |
| `lib/theme.ts` (MOD) | config | — | itself 147-151, 418-433 | exact |
| `hooks/useGameOverlay.ts` (+ test) (MOD) | hook | — | itself ~291-310; test lines 14, 91 | exact |

## Pattern Assignments

### `lib/engineSettings.ts` (store, event-driven)

**Analog:** `lib/sounds.ts`. Copy the module shape verbatim, one key per count setting (primitive snapshot, no getSnapshot caching):

```typescript
// sounds.ts:82-86
export const MUTE_KEY = 'flawchess_bot_sound_muted';
const MUTED_VALUE = '1';

// sounds.ts:164-198
const listeners = new Set<() => void>();

function subscribe(callback: () => void): () => void {
  listeners.add(callback);
  return () => {
    listeners.delete(callback);
  };
}

function readMuted(): boolean {
  try {
    return localStorage.getItem(MUTE_KEY) === MUTED_VALUE;
  } catch {
    return false;
  }
}

export function useMuted(): boolean {
  return useSyncExternalStore(subscribe, readMuted, () => false);
}

export function setMuted(muted: boolean): void {
  try {
    localStorage.setItem(MUTE_KEY, muted ? MUTED_VALUE : '0');
  } catch {
    return;
  }
  listeners.forEach((listener) => listener());
}
```

Adaptation: `readCount(id)` validates `Number.isInteger(n) && min <= n <= max`, else the default (RESEARCH Pattern 1 skeleton). `resetAllSettings()` does `removeItem` on each key, calls `setMuted(false)`, and then notifies. Must live in `lib/` (eslint `react-refresh/only-export-components`). Leave `MUTE_KEY`/`useMuted`/`setMuted` in `sounds.ts`. Name constants (`DEFAULT_LINES = 2`, `DEFAULT_ARROWS = 1`, ranges).

### `components/settings/SettingsPanel.tsx` (component)

**ToggleGroup analog:** `components/filters/FlawFilterControl.tsx:593-625`:
```tsx
<ToggleGroup
  type="single"
  value={orientation}
  onValueChange={(v) => {
    // D-06: deselect guard — empty string means user tapped the active item
    if (!v) return;
    onOrientationChange?.(v as TacticOrientation);
  }}
  variant="outline"
  size="sm"
  data-testid="filter-tactic-orientation"
  className="w-full"
>
  <ToggleGroupItem value="either" data-testid="filter-tactic-orientation-either"
    className="min-h-11 sm:min-h-0 flex-1 text-sm">Either</ToggleGroupItem>
```
Use `value={String(n)}`, parse with `Number(v)`, and write only if the value changed. Then call `trackEvent('settings-change', { setting, value: String(n) })` (signature `trackEvent(name, Record<string,string>)`, `lib/analytics.ts:34`). Suggested testids: `settings-fc-lines-3`, `settings-sf-arrows-0`.

**Switch analog:** `components/train/TrainScheduleSettings.tsx:351-358`:
```tsx
<Switch
  data-testid="filter-reminder-enabled"
  aria-label="Remind me to train"
  checked={checked}
  disabled={disabled || subscribing || blocked}
  onCheckedChange={onToggle}
/>
<p className="text-sm text-muted-foreground">Remind me to train</p>
```
Sound: `checked={!useMuted()}`, `onCheckedChange={(on) => setMuted(!on)}`. The Reset button uses `<Button variant="brand-outline" data-testid="btn-settings-reset">` (frontend/CLAUDE.md secondary rule). Text is `text-sm` minimum.

### `components/settings/SettingsSheetButton.tsx` (component)

**Analog:** `components/filters/MobileFilterDrawer.tsx:3, 68-86`:
```tsx
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer';
<Drawer open={open} onOpenChange={onOpenChange} direction="right">
  <DrawerContent className={DRAWER_CONTENT_CLASS} data-testid={contentTestId}>
    <DrawerHeader className="flex flex-row items-center justify-between">
      <DrawerTitle ...>
    </DrawerHeader>
    <div className={cn('overflow-y-auto thin-scrollbar flex-1 p-4', bodyClassName)}>{children}</div>
  </DrawerContent>
</Drawer>
```
Use `direction="bottom"`. The body must scroll itself because drawer.tsx caps the content at `max-h-[80vh]`. The trigger is a ghost icon `Button` with `aria-label="Settings"` and `title="Settings"`, and its testid comes from a prop (`btn-analysis-settings`, `btn-bots-settings`). See the RESEARCH Pattern 4 skeleton.

### `pages/Settings.tsx` (page)

**Analog:** `pages/Privacy.tsx` (named export, `<main ... data-testid="privacy-page">` with `<section>` blocks). Drop `PublicHeader` and the document.title effect, because ProtectedLayout and ROUTE_TITLES handle those. Render `<main data-testid="settings-page"><SettingsPanel/></main>`.

### `App.tsx` (MOD)

- NavHeader right cluster (358-376): insert a cog between `<ImpersonationPill/>` and the logout button:
```tsx
<Button variant="ghost" size="sm" onClick={logout} data-testid="nav-logout">Logout</Button>
```
→ `<Button variant="ghost" size="icon" asChild><Link to="/settings" aria-label="Settings" title="Settings" data-testid="nav-settings"><Settings .../></Link></Button>`. No `data-umami-event` on the Link.
- AnalysisMobileHeader (425-446): add `<SettingsSheetButton testId="btn-analysis-settings" />` after `<span ...>Analysis</span>`, using an `h-12` tap target like `btn-analysis-back` (`className="h-12 w-16 -ml-1"`).
- MobileMoreDrawer (612): insert the row ABOVE `<div className="my-2 border-t border-border" />`, copying the `drawer-logout` row style (`flex w-full items-center gap-2 rounded-md px-3 py-2 text-base`), wrapped in `<DrawerClose asChild><Link to="/settings" data-testid="drawer-settings">`. Do NOT use the `drawer-nav-*` prefix (App.test.tsx order test, Pitfall 6).
- `ROUTE_TITLES` (line 139 `'/analysis': 'Analysis'`): add `'/settings': 'Settings'`.
- Route (line 1036 `<Route path="/analysis" element={<AnalysisRoute />} />`): add `<Route path="/settings" element={<SettingsPage />} />` alongside it, without ImportRequiredRoute.

### `components/bots/BotGameMobileLayout.tsx` (MOD, D-04)

Top row (99-108):
```tsx
<div className="flex items-center">
  <Button variant="ghost" size="icon" aria-label="Back to bot roster"
    data-testid="bots-back" onClick={onBackToRoster}>
    <ArrowLeft className="size-5" aria-hidden="true" />
  </Button>
</div>
```
Add `<SettingsSheetButton testId="btn-bots-settings" className="ml-auto" />` with the same `size="icon"` / `size-5` icon, so the row height does not change. Remove the stale comment at 34-36 ("icon with no sheet"). Do not touch `BotGameMobileBar` (its tests pin exactly 4 actions).

### `hooks/useStockfishEngine.ts` (MOD, D-12)

Current: `const MULTIPV = 2;` (45), sent once at `uciok` (501: `worker.postMessage(\`setoption name MultiPV value ${MULTIPV}\`)`). Analog for a per-search resend: `useStockfishGradingEngine.ts:285` (setoption MultiPV right before `position`, idle state only). Add a required `multiPv` option plus `multiPvRef`/`appliedMultiPvRef` (the same ref-for-latest pattern as `currentFenRef`). Resend in `analyze()`'s idle branch only when the value changed, and add an effect on `[multiPv]` that re-analyzes. Never add `multiPv` to the worker-lifecycle effect deps (~605). Callers: Analysis.tsx:531 (`max(2, sfLines, sfArrows)`), useTrainFreePlay.ts:227 (`max(sfLines, sfArrows)`), TrainSolveScreen.tsx:1220 (named constant, e.g. `TRAIN_EVAL_BAR_MULTIPV = 1`). Update the existing test near line 226 of `hooks/__tests__/useStockfishEngine.test.ts`.

### `hooks/analysis/useAnalysisBoardArrows.ts` (MOD, D-14/D-15)

Current constants 60-62: `ARROW_COUNT = 1`, `FLAWCHESS_ENGINE_ARROW_WIDTH = 1.0`, `STOCKFISH_ENGINE_ARROW_WIDTH = 0.5`. Buggy line in the loop (~349-388): `const sfUci = reconciledBestUci ?? enginePvLines[i]?.moves[0] ?? null;`. Replace the options with `stockfishArrowLines` (= reconciledPvLines), `fcArrowCount`, and `sfArrowCount`. Loop in reverse rank order (Pitfall 7). i=0 gets the primary color and i≥1 gets the `*_SECONDARY_LINE` token. Keep `layerKey` `sf-${i}`/`fc-${i}`. Counts come in as options. Do not read the store in this pure hook.

### `hooks/analysis/useAnalysisEngineLines.ts` (MOD)

Line 311 is `rankedLines.slice(0, FC_MAX_LINES)` and ~350 is `.slice(0, SF_MAX_LINES)`. Replace the slice args with option-passed `fcLines` and `max(sfLines, sfArrows)`, and drop the `MAX_LINES` imports at 65-66.

### `pages/Analysis.tsx` (MOD)

Read `useEngineDisplaySettings()` once here and pass the values down. Line 931 (`FC_MAX_LINES` slice) becomes `fcLines`. `unionSans` (955-966) includes all free-run `engine.pvLines` roots (sorted and deduped). Leave the `extraRootMoves` FC injection (~1034, pvLines[0..1]) unchanged.

### Card components (`EngineLines.tsx`, `FlawChessEngineLines.tsx`, `AnalysisTabs.tsx`, `AnalysisDesktopCards.tsx`, `TrainReveal.tsx`)

Replace `export const MAX_LINES = 2` (EngineLines:38, FC:48) with a required `maxLines` prop and delete the exports (knip). Change `EngineLinesSkeleton` `rows?: 2|3` to `rows: number`. Replace the min-height classes (`min-h-[60px]`/`[50px]`/`[90px]`, EngineLines 108-122; AnalysisDesktopCards:70 `min-h-[78px]`) with `style={{ minHeight: rows * ENGINE_LINE_ROW_PX }}` (Pitfall 4: no dynamic Tailwind). Badge color by rank (EngineLines ~266, FC ~314): the primary keeps its color and non-primary uses the engine's secondary token. White text stays (`BADGE_CLASS` text-white at EngineLines:96 / FC:88).

### `lib/trainArrows.ts` (MOD, D-13)

Rewrite `buildTrainFreePlayArrows(bestMoveUci)` (229) as `(pvLines, count)`. See RESEARCH "Code Examples". Width stays `TRAIN_BEST_MOVE_ARROW_WIDTH` (154). Update trainArrows.test.ts 474-495 (`'free-best'` layerKey). Do not touch the reveal/step builders.

### `lib/theme.ts` (MOD)

Remove `FLAWCHESS_ENGINE_BADGE_SHADES` (147-151), `SECOND_BEST_ARROW` (432), and `SECOND_BEST_BADGE_TEXT` (433). Add `STOCKFISH_SECONDARY_LINE = 'rgba(37, 99, 235, 0.45)'`, `FLAWCHESS_SECONDARY_LINE = 'rgba(213, 152, 0, 0.45)'`, and `FLAWCHESS_ENGINE_BADGE_PRIMARY = 'oklch(0.47 0.13 80)'`. Use rgba, not oklch, for SVG fill (comment at 421-424).

### `hooks/useGameOverlay.ts` (MOD)

Delete the dead `SECOND_BEST_ARROW` block (~291-310) and its import, plus the test import/assertion at useGameOverlay.test.ts:14, 91.

## Shared Patterns

- **Store reads:** only `Analysis.tsx`, `TrainSolveScreen`/`useTrainFreePlay`, `TrainReveal`, and `SettingsPanel` call `useEngineDisplaySettings()`. Pure hooks and presentational cards receive counts through props/options.
- **Analytics:** `trackEvent` from `@/lib/analytics` in `onChange`/`onClick`, never `data-umami-event` on `<Link>`.
- **Testids/a11y:** `nav-settings`, `drawer-settings`, `btn-analysis-settings`, `btn-bots-settings`, `settings-sheet`, `settings-page`, `btn-settings-reset`. Icon-only buttons carry `aria-label` and `title`.
- **Colors:** only through `lib/theme.ts` tokens.
- **Drawer jsdom tests:** copy the vaul shims from `App.test.tsx` ~line 74.

## No Analog Found

None. Every file has an in-repo analog. The `storage` cross-tab listener has no precedent (optional, RESEARCH Pattern 1).

## Metadata

**Analog search scope:** frontend/src/{lib,hooks,components,pages,App.tsx}. Line anchors are taken from RESEARCH.md (verified this session) and spot-checked: sounds.ts, App.tsx, BotGameMobileLayout.tsx, FlawFilterControl.tsx, MobileFilterDrawer.tsx, TrainScheduleSettings.tsx, Privacy.tsx.
**Pattern extraction date:** 2026-10-03
