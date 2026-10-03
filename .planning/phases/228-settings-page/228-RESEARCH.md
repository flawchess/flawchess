# Phase 228: Settings Page — Sound Toggle & Per-Engine Lines/Arrows - Research

**Researched:** 2026-10-03
**Domain:** Frontend only (React 19 + TypeScript): localStorage settings store, routing/nav entry points, Stockfish UCI MultiPV threading, engine card/arrow rendering
**Confidence:** HIGH (every claim below was read in-repo this session unless tagged otherwise)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Locked upstream in SEED-175 / ROADMAP (not re-decided):**

| Setting | Range | Default |
|---|---|---|
| Sound | on/off | on (reuses `useMuted`/`setMuted`, key `flawchess_bot_sound_muted`) |
| FlawChess engine lines | 1-5 | 2 |
| FlawChess engine arrows | 0-3 | 1 |
| Stockfish lines | 1-5 | 2 |
| Stockfish arrows | 0-3 | 1 |

- Lines and arrows are separate per engine. 0 arrows hides that engine's arrows and keeps its card.
- Settings module: typed, `useSyncExternalStore`-based, the same shape as `useMuted` in
  `lib/sounds.ts`, so a later account-sync swap touches only that module.
- Styling: primary line solid. Every non-primary line uses one translucent color per engine
  (blue for Stockfish, gold for FlawChess) on both arrows and card badges. This replaces
  `FLAWCHESS_ENGINE_BADGE_SHADES` and Stockfish's light-blue `SECOND_BEST_ARROW` badge/arrow.
  No eval-proportional transparency.
- Out of scope: search time and thread settings, board colors, piece sets, sound sets.

#### Entry placement
- **D-01:** Desktop: an icon-only cogwheel button (lucide `Settings`) in `NavHeader`'s right
  cluster, left of Logout (after the Guest badge and impersonation pill). Needs `aria-label` and
  `title`, and links to `/settings`. Not added to `NAV_ITEMS`.
- **D-02:** Mobile: a "Settings" row with a cogwheel in `MobileMoreDrawer`, above the divider and
  Logout. It links to `/settings`. No cogwheel in the generic `MobileHeader`.
- **D-03:** Mobile `/analysis`: a cogwheel in `AnalysisMobileHeader` next to the "Analysis"
  title. It opens the settings panel in a sheet over the page; it does not navigate away.
- **D-04:** Bot game page, **mobile only**: a cogwheel in the mobile bot game shell (the bottom
  nav is replaced during play), so a user can turn sound off mid-game. It opens the same sheet and
  does not navigate. Navigating away would trigger the `ResumeGate` "Resume game?" overlay on
  return. The planner picks the exact spot in the bot mobile layout. Desktop bot play relies on
  the header cogwheel only.
- **D-05:** No settings shortcut inside the engine cards. The card headers were just slimmed on
  mobile (7ed295414, b4327e5c7).
- **D-06:** The in-context sheets render the **full** `SettingsPanel`, identical to `/settings`
  (Drawer on mobile, matching the existing `components/ui/drawer` usage). There is one panel
  component and no per-surface section variants. Changes apply live underneath the sheet.

#### Page layout & controls
- **D-07:** Count inputs are segmented toggle groups (`components/ui/toggle-group`): buttons
  `1 2 3 4 5` for lines and `0 1 2 3` for arrows. The sound on/off is a `Switch`.
- **D-08:** Changes apply instantly, with no Save button. Each control writes localStorage on
  change, and subscribers update through `useSyncExternalStore`.
- **D-09:** Three labeled sections, in order: **Sound**, **FlawChess engine**, **Stockfish**.
  Each section gets a short helper line where useful (e.g. "0 arrows hides this engine's arrows,
  the card stays"). One **"Reset to defaults"** button at the bottom resets all five settings
  (including sound back to on).
- **D-10:** Umami: one event per setting change, e.g. `settings-change` with `{setting, value}`,
  fired through `trackEvent()` in `lib/analytics.ts` (not `data-umami-event` on router links).
  It fires on change only, not on page view. Reset fires it once per changed setting, or as a
  single `settings-reset` event, at Claude's discretion.

#### Train free-play depth
- **D-11:** Honor the setting at the fixed `MOVETIME_MS = 1500`. Train free-play MultiPV =
  max(SF lines, SF arrows). The user trades depth for breadth by choice, as on lichess. No
  movetime scaling, since search time is out of scope.
- **D-12:** `useStockfishEngine` takes MultiPV as an option instead of the module constant
  `MULTIPV = 2`. The Train solve-screen eval-bar engine (`TrainSolveScreen.tsx` ~1220) stays
  **independent** of the setting at a fixed value, because it only feeds the eval bar. Claude's
  discretion: keep it at 2, or lower it to 1.
- **D-13:** The Stockfish arrow setting governs only the **live engine arrows** in Train
  free-play (`liveBestUci` / pvLines). The puzzle-reveal legend arrows (blue best, green "also
  fine", the game-move arrow) always draw, because they carry puzzle meaning (Phase 200
  sidebar-as-legend contract). The SF lines setting still sets the reveal and free-play
  card rows and the `EngineLinesSkeleton` row count.

#### High-count rendering
- **D-14:** On `/analysis`, Stockfish arrows 1..N come from the **same reconciled grading
  ranking** that feeds the SF card, so arrows and card rows always agree. The free-run
  `enginePvLines` serves only as the first-paint fallback before grading lands. Today's loop
  (`reconciledBestUci ?? enginePvLines[i]`) would repeat the best move for i ≥ 1 and must
  change. The free-search MultiPV on `/analysis` then matters only for that fallback.
- **D-15:** Non-primary arrows keep the per-engine width (`FLAWCHESS_ENGINE_ARROW_WIDTH = 1.0`,
  `STOCKFISH_ENGINE_ARROW_WIDTH = 0.5`) and differ only by the translucent engine color. The
  existing width-sorted draw order is unchanged.
- **D-16:** The cards render all N rows at every breakpoint, with no mobile cap. Skeletons show
  N rows.

### Claude's Discretion
- Route gating: `/settings` lives inside `ProtectedLayout` (guests have sessions), without
  `ImportRequiredRoute`. Add `'/settings': 'Settings'` to `ROUTE_TITLES`.
- Exact translucent color values and alpha for the non-primary SF blue and FC gold (UAT-tuned).
  Badge text must stay legible on the translucent fill.
- Settings storage layout: one JSON key vs. per-setting keys, validation/clamping of out-of-range
  stored values, and a fallback to defaults on parse errors. Sound must keep using the existing
  `flawchess_bot_sound_muted` key so the pre-Phase-223 persisted `'1'` values still work.
- Where the per-engine counts are read: hook calls in `useAnalysisEngineLines`,
  `useAnalysisBoardArrows`, `Analysis.tsx` (FC slice ~931), `TrainReveal`, and `useTrainFreePlay`,
  replacing the exported `MAX_LINES` and `ARROW_COUNT` constants.
- Whether `useGameOverlay`'s `SECOND_BEST_ARROW` path is still live anywhere. The 156 UAT
  comment says the analysis board no longer draws it, so retire it or restyle it accordingly.
- Bot mobile cogwheel placement (D-04) and sheet trigger component reuse between D-03 and D-04.

### Deferred Ideas (OUT OF SCOPE)
- A "search longer" Stockfish toggle, reconsidered once Phase 226's pool tuning has settled
  (already listed in SEED-175 out of scope).
- Moving the Train reminder settings (`TrainScheduleSettings`, push toggle and hour picker) onto
  the settings page. This is a natural future home, but it is new scope and was not discussed.
- Reviewed Todos (not folded): `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`,
  `172-deferred-review-findings.md`, and `2026-08-29-variation-tree-nested-button.md` are
  unrelated to settings.
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQ-IDs are mapped (ROADMAP: "Requirements: TBD"). The planner covers CONTEXT.md D-01..D-16 instead:

| Decision | Research Support |
|----|------------------|
| D-01/D-02 entry | §Entry points: `NavHeader` right cluster (App.tsx ~357-376), `MobileMoreDrawer` divider at App.tsx:612; testid naming pitfall (Pitfall 6) |
| D-03/D-04 sheets | §Sheet trigger: one `SettingsSheetButton` reused in `AnalysisMobileHeader` (App.tsx:428-446) and `BotGameMobileLayout`'s top row (BotGameMobileLayout.tsx:99), where Phase 223 originally planned "back arrow + gear on top" |
| D-06 one panel | §SettingsPanel; Drawer body needs its own `overflow-y-auto` (drawer.tsx caps at `max-h-[80vh]`) |
| D-07/D-08 controls | §Settings store (per-key primitives); ToggleGroup deselect guard (Pitfall 3) |
| D-09/D-10 layout + Umami | `trackEvent(name, Record<string,string>)` — values must be stringified |
| D-11/D-12 MultiPV | §useStockfishEngine change; mid-session MultiPV change must re-search (Pitfall 2) |
| D-13 Train | `buildTrainFreePlayArrows` is the only live-engine arrow builder in Train; reveal legend builders untouched |
| D-14 arrows | §D-14: arrows read `reconciledPvLines`; **correction:** free-run MultiPV ALSO seeds the grading union and is the SOLE source when grading is off (Pitfall 1) |
| D-15 widths/order | `arrowSortKey` puts every engine color in tier 3, so order = width desc, then stable input order (Pitfall 7) |
| D-16 N rows | Six render/skeleton/min-height sites inventoried; Tailwind cannot build `min-h-[${n}px]` at runtime (Pitfall 4) |
</phase_requirements>

## Summary

This is a frontend-only phase with no new dependencies. The settings store is a near-copy of `useMuted` (`lib/sounds.ts:183-198`): a module-level listener set plus `useSyncExternalStore`. The safest shape is **one flat localStorage key per count setting, each read as a primitive number**. That avoids the React "getSnapshot must return a cached value" trap a parsed JSON object would hit. The Sound switch just wraps the existing `useMuted`/`setMuted`. `playSound` reads the persisted flag on every call (`sounds.ts:322`), so toggling takes effect immediately everywhere, mid bot game included.

The real work is threading the counts through the engine plumbing. Three findings change the plan relative to the seed/CONTEXT assumptions:

1. **FC lines are not reliably 5.** `rankedLines` has one entry per root child. The root keeps only Maia moves up to 0.9 cumulative policy mass (`select.ts:21`, `POLICY_MASS_THRESHOLD = 0.9`), capped at 15 (`policyTemperature.ts:56`). Injected Stockfish moves are added on top. In forcing positions the FC card can therefore have 1-2 rows whatever the setting says. That is acceptable (it's a property of the engine), but skeletons sized to N rows will leave blank space after first paint.
2. **The `/analysis` free-run MultiPV matters for more than first paint (D-14 correction).** The SF card's grading ranking can only rank moves in the grading union (`unionSans`, Analysis.tsx:955-966). Today that union hard-codes only the free run's `pvLines[0]` and `pvLines[1]`. And when Maia AND FC are both off, `gradingEnabled = maiaEnabled || flawChessEnabled` (Analysis.tsx:1071) is false, so the free run is the permanent source for the SF card and arrows. So `/analysis` must run the free search at MultiPV = max(sfLines, sfArrows), with a floor of 2 (see Pitfall 1), and `unionSans` must include every free-run root move, not just two.
3. **`useStockfishEngine` sends `setoption MultiPV` once, at `uciok`** (`useStockfishEngine.ts:501`). D-06 says sheet changes apply live underneath, so a MultiPV change on an already-running engine must take effect without a worker restart. The codebase already has the pattern: `useStockfishGradingEngine` sends `setoption name MultiPV` per search, while idle, right before `position`/`go` (`useStockfishGradingEngine.ts:285`).

**Primary recommendation:** Build `lib/engineSettings.ts` (per-key primitive store plus a `useEngineDisplaySettings()` aggregate hook) and one `SettingsPanel` and one `SettingsSheetButton`. Thread `maxLines`/`rows` as **props** into the presentational card components, and the counts as **options** into the pure-transform `/analysis` hooks. Make MultiPV a per-search option in `useStockfishEngine`, re-sent only when it changes. Source `/analysis` SF arrows from `reconciledPvLines`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Settings persistence (5 values) | Browser / Client (localStorage) | — | Locked: per-device, guests included, no backend |
| Settings reactivity | Browser / Client (`useSyncExternalStore` module store) | — | Same pattern as `useMuted`/`useUserFlag` |
| `/settings` route + nav entry | Browser / Client (react-router, App.tsx) | — | SPA route inside `ProtectedLayout` |
| MultiPV / search breadth | Browser / Client (Stockfish WASM Web Worker) | — | UCI `setoption` on the free-run worker |
| Card rows / arrows / colors | Browser / Client (React components, theme.ts) | — | Pure rendering of engine state |
| Analytics events | Browser / Client → Umami | — | `trackEvent()` |
| API / Database | — | — | Not touched (frontend-only phase) |

## Project Constraints (from CLAUDE.md)

- **Frontend rules (`frontend/CLAUDE.md`):** theme colors only in `lib/theme.ts`; `data-testid` on every interactive element (kebab-case, `btn-*`, `nav-*` naming); `aria-label` on icon-only buttons; `text-sm` is the minimum font size in new code; apply changes to mobile and desktop alike; primary = `variant="default"`, secondary = `variant="brand-outline"` (the "Reset to defaults" button is secondary → `brand-outline`); never put `data-umami-event` on a router `<Link>`, call `trackEvent()` in `onClick` instead; `noUncheckedIndexedAccess` is on; knip runs in CI (remove dead exports such as `MAX_LINES`, `SECOND_BEST_*`, `FLAWCHESS_ENGINE_BADGE_SHADES`); `max-depth` 4 is a hard lint gate; `npm run build` (tsc -b) is required before integrating shared-type changes.
- **Root CLAUDE.md:** no magic numbers (named constants for ranges/defaults/row heights/alpha); explicit types, `Literal`-style unions instead of loose strings; comment bug fixes at the fix site; keep functions shallow; only work inside the phase scope; `@vitest-environment jsdom` per file; em-dashes sparingly in UI copy.
- **Pre-merge gate (frontend part):** `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )`.
- **eslint:** `react-refresh/only-export-components` is enforced outside `components/ui`, `components/filters`, `components/analysis`. So the store module must live in `lib/` (not co-exported from a page/component file). A `components/settings/*.tsx` file must export components only. [VERIFIED: frontend/eslint.config.js:33-60]
- **Memory (project):** frontend has no Prettier (ESLint only); run `npm run build` when changing shared types; browser UAT is run by the agent itself; drafts/screenshots go in repo `temp/<topic>/`.

## Standard Stack

### Core (all already installed, no new packages)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react `useSyncExternalStore` | react ^19.2.8 [VERIFIED: frontend/package.json] | Settings store subscription | House pattern (`lib/sounds.ts`, `hooks/useUserFlag.ts`, `lib/mobileBoardControls.ts`) |
| radix-ui ToggleGroup (via `components/ui/toggle-group.tsx`) | radix-ui ^1.4.3 [VERIFIED: package.json] | D-07 segmented 1-5 / 0-3 pickers | House single-select pattern (`FlawFilterControl.tsx:593-625`) |
| `components/ui/switch` | — | D-07 sound on/off | Used by `EngineToggleHeader`, `TrainScheduleSettings` |
| `components/ui/drawer` (vaul ^1.1.2) | [VERIFIED: package.json] | D-03/D-04/D-06 sheet | Used by `MobileMoreDrawer`, `MobileFilterDrawer` |
| lucide-react `Settings` icon | lucide-react 1.41.0 installed; `Settings` export present [VERIFIED: `node -e` probe printed `Settings:object`] | Cogwheel | Already the app icon library |
| `lib/analytics.ts` `trackEvent` | in-repo | D-10 | `trackEvent(eventName: string, eventData?: Record<string, string>)` [VERIFIED: lib/analytics.ts:34] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Per-key primitive store | One JSON key `flawchess_settings` | One read/write and easy account-sync, but `getSnapshot` must cache the parsed object by raw string or React loops. More code for no user-visible gain. |
| `ToggleGroup` | `ToggleChipButton` grid | `ToggleChipButton` is the house **multi**-select pattern (toggle-chip-button.tsx header); counts are single-select → ToggleGroup (D-07 locked anyway) |
| Inline `style={{ minHeight }}` for N rows | A static lookup table of Tailwind classes per N | Both fine; the lookup must list literal class strings so the Tailwind scanner sees them |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed in this phase. Every library above is already in `frontend/package.json` and `node_modules`.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 user taps control (/settings page OR Drawer sheet on /analysis / bot game)
            │
            ▼
   SettingsPanel ──trackEvent('settings-change',{setting,value})──► Umami
            │ setEngineSetting(key, n) / setMuted(bool)
            ▼
   localStorage (flat keys) ──notify listeners──► useSyncExternalStore subscribers
            │                                   (+ window 'storage' event → other tabs)
            ▼
   useEngineDisplaySettings() → { fcLines, fcArrows, sfLines, sfArrows }
            │
   ┌────────┴──────────────────────────────┬──────────────────────────────────┐
   ▼ /analysis (Analysis.tsx)              ▼ Train (TrainSolveScreen)          ▼ playSound()
   sfMultiPv = max(2, sfLines, sfArrows)   multiPv = max(sfLines, sfArrows)    reads MUTE_KEY each call
   useStockfishEngine({multiPv}) ──►       useTrainFreePlay → useStockfishEngine
     free-run pvLines (N)                   pvLines (stale-guarded)
        │                                      │
        ├─► unionSans (Maia ∪ FC top-fcLines ∪ ALL free-run roots)          ├─► EngineLines maxLines=sfLines
        │        ▼                                                          └─► buildTrainFreePlayArrows(pvLines, sfArrows)
        │   useStockfishGradingEngine (searchmoves, MultiPV=|union|)
        │        ▼
        └─► useAnalysisEngineLines ─► reconciledPvLines (ranked, sliced to max(sfLines,sfArrows))
                 │                       reconciledRankedLines (FC, sliced to fcLines)
                 ├─► EngineLines maxLines=sfLines  (desktop card + MobileEngineLines)
                 ├─► FlawChessEngineLines maxLines=fcLines
                 └─► useAnalysisBoardArrows: FC arrows = rankedLines[0..fcArrows)
                                              SF arrows = reconciledPvLines[0..sfArrows)
                                              i=0 solid color, i≥1 translucent engine color
```

### Recommended Structure
```
frontend/src/
├── lib/engineSettings.ts                      # NEW: typed store + hooks + setters + reset (no React components)
├── lib/__tests__/engineSettings.test.ts        # NEW
├── components/settings/SettingsPanel.tsx       # NEW: the one panel (D-06)
├── components/settings/SettingsSheetButton.tsx # NEW: cog icon button + Drawer + SettingsPanel (D-03/D-04)
├── components/settings/__tests__/*.test.tsx    # NEW
└── pages/Settings.tsx                          # NEW: page shell rendering <SettingsPanel/> (default or named export)
```

### Pattern 1: Settings store (per-key primitives, mirrors `useMuted`)

The `useMuted` source of truth [VERIFIED: frontend/src/lib/sounds.ts:82-198]: `export const MUTE_KEY = 'flawchess_bot_sound_muted';` (line 82), `const MUTED_VALUE = '1';` (line 86), a module `listeners` Set, `readMuted()` wrapped in try/catch returning `false` on failure, `useMuted()` = `useSyncExternalStore(subscribe, readMuted, () => false)` (line 183), and `setMuted(muted)` that writes `muted ? MUTED_VALUE : '0'` and then notifies (line 191).

```typescript
// lib/engineSettings.ts — skeleton. Key names are a NEW proposal [ASSUMED], pick and freeze them.
import { useSyncExternalStore } from 'react';
import { useMuted, setMuted } from '@/lib/sounds';

export type LineCount = 1 | 2 | 3 | 4 | 5;
export type ArrowCount = 0 | 1 | 2 | 3;
export type CountSettingId = 'fcLines' | 'fcArrows' | 'sfLines' | 'sfArrows';

interface CountSpec { key: string; min: number; max: number; fallback: number }
// Named constants, no magic numbers (CLAUDE.md).
export const MIN_LINES = 1; export const MAX_LINES_SETTING = 5;
export const MIN_ARROWS = 0; export const MAX_ARROWS_SETTING = 3;
export const DEFAULT_LINES = 2; export const DEFAULT_ARROWS = 1;

const SPECS: Record<CountSettingId, CountSpec> = {
  fcLines:  { key: 'flawchess_settings_fc_lines',  min: MIN_LINES,  max: MAX_LINES_SETTING,  fallback: DEFAULT_LINES },
  fcArrows: { key: 'flawchess_settings_fc_arrows', min: MIN_ARROWS, max: MAX_ARROWS_SETTING, fallback: DEFAULT_ARROWS },
  sfLines:  { key: 'flawchess_settings_sf_lines',  min: MIN_LINES,  max: MAX_LINES_SETTING,  fallback: DEFAULT_LINES },
  sfArrows: { key: 'flawchess_settings_sf_arrows', min: MIN_ARROWS, max: MAX_ARROWS_SETTING, fallback: DEFAULT_ARROWS },
};

const listeners = new Set<() => void>();
function notify(): void { listeners.forEach((l) => l()); }
function onStorage(e: StorageEvent): void {
  // Fires only in OTHER tabs (MDN). key === null means clear() [ASSUMED per spec].
  if (e.key === null || Object.values(SPECS).some((s) => s.key === e.key)) notify();
}
function subscribe(cb: () => void): () => void {
  if (listeners.size === 0) window.addEventListener('storage', onStorage);
  listeners.add(cb);
  return () => { listeners.delete(cb); if (listeners.size === 0) window.removeEventListener('storage', onStorage); };
}

/** Parse + validate: non-integer, out-of-range, or missing → fallback (never clamp silently into a wrong value). */
function readCount(id: CountSettingId): number {
  const spec = SPECS[id];
  try {
    const raw = localStorage.getItem(spec.key);
    if (raw === null) return spec.fallback;
    const n = Number(raw);
    return Number.isInteger(n) && n >= spec.min && n <= spec.max ? n : spec.fallback;
  } catch { return spec.fallback; }
}

export function useCountSetting(id: CountSettingId): number {
  // Primitive snapshot → referentially stable, no getSnapshot caching needed.
  return useSyncExternalStore(subscribe, () => readCount(id), () => SPECS[id].fallback);
}
export function setCountSetting(id: CountSettingId, value: number): void { /* validate, setItem(String(value)), notify(); try/catch like setMuted */ }
export function resetAllSettings(): void { /* removeItem each key; setMuted(false); notify() */ }

export interface EngineDisplaySettings { fcLines: LineCount; fcArrows: ArrowCount; sfLines: LineCount; sfArrows: ArrowCount }
export function useEngineDisplaySettings(): EngineDisplaySettings { /* four useCountSetting calls, cast after validation */ }
export { useMuted as useSoundMuted, setMuted as setSoundMuted }; // or import sounds.ts directly in the panel
```

Notes:
- Keep `MUTE_KEY`/`useMuted`/`setMuted` in `sounds.ts` (locked key). The settings module may re-export or the panel may import `sounds.ts` directly. Either way the account-sync seam is these two modules.
- Reset: removing the keys, rather than writing defaults, keeps "default" as "absent", same as the mute convention (absence = unmuted). Call `setMuted(false)` for sound (it writes `'0'`, which reads as unmuted).
- If cross-tab sync is wanted for sound too, `sounds.ts`'s `subscribe` would need the same `storage` listener. Today no store in the codebase handles `storage` events [VERIFIED: grep found no `addEventListener('storage'` in frontend/src]. That is optional, low-value polish.

### Pattern 2: `useStockfishEngine` with a MultiPV option (D-12)

Current constants [VERIFIED: frontend/src/hooks/useStockfishEngine.ts:36-45,501]: `const MOVETIME_MS = 1500;` (36), `const MAX_NODES = 2000000;` (39), `const MULTIPV = 2;` (45). MultiPV is sent **once**, in the `uciok` branch: `worker.postMessage(\`setoption name MultiPV value ${MULTIPV}\`);` (501), followed by `isready`. `analyze()` (305-343) sends `position fen …` + `go movetime ${MOVETIME_MS} nodes ${MAX_NODES}` only from the `idle` state. In `thinking` it sends `stop` and defers. In `stopping` it no-ops (FLAWCHESS-7V guard).

Callers [VERIFIED: grep]: `pages/Analysis.tsx:531` (free run), `hooks/useTrainFreePlay.ts:227` (Train free play), `components/train/TrainSolveScreen.tsx:1220` (eval bar).

Recommended change (no worker restart):
1. Add `multiPv: number` to `UseStockfishEngineOptions` as a **required** field, so every caller is explicit and tsc finds them all. Keep it in a `multiPvRef` (ref-for-latest-value, like `currentFenRef`).
2. At `uciok`, send `setoption name MultiPV value ${multiPvRef.current}` and record `appliedMultiPvRef.current`. This keeps the 155-UAT ordering fix (setoption before `isready`) and the existing test shape.
3. In `analyze()`'s idle branch, before `position fen`: if `multiPvRef.current !== appliedMultiPvRef.current`, send `setoption name MultiPV value …` and update the applied ref. The engine is idle at that point, which is the same rule `useStockfishGradingEngine.prepareSearch` follows (`useStockfishGradingEngine.ts:285`, sent right before `position`).
4. Add an effect on `[multiPv]` that, when the value changed and a `debouncedFen` exists and `isReadyRef.current` is set, calls `analyze(debouncedFen)`. The thinking branch stops the running search, and the stale-bestmove handler re-analyzes `currentFenRef.current`, which by then picks up the new width. Without this, a sheet change on `/analysis` would only apply on the next move (it breaks D-06 "changes apply live").
5. Caller values: `/analysis` → `Math.max(ANALYSIS_MIN_MULTIPV /* 2 */, sfLines, sfArrows)`; Train free play → `Math.max(sfLines, sfArrows)` (D-11); eval bar → a fixed named constant. **Recommend `TRAIN_EVAL_BAR_MULTIPV = 1`**: `resolveTrainEvalBarReading` reads only `engine.evalCp/evalMate/depth` from that engine (TrainSolveScreen.tsx:233-251), so line 2 is pure wasted depth. Stockfish's own docs say MultiPV > 1 weakens the best line [CITED: official-stockfish.github.io UCI-Protocol-and-Stockfish-Commands].

### Pattern 3: D-14 — `/analysis` SF arrows from the reconciled ranking

Current loop [VERIFIED: frontend/src/hooks/analysis/useAnalysisBoardArrows.ts:60-62,349-388]: `const ARROW_COUNT = 1;`, `const FLAWCHESS_ENGINE_ARROW_WIDTH = 1.0;`, `const STOCKFISH_ENGINE_ARROW_WIDTH = 0.5;`. The SF arrow uses `const sfUci = reconciledBestUci ?? enginePvLines[i]?.moves[0] ?? null;`, which repeats the argmax for every i ≥ 1. FC arrows use `flawChessRankedLines[i]?.rootMove` (raw `flawChessEngine.rankedLines`, Analysis.tsx:1682). That already matches the FC card's order, because the card is `rankedLines.slice(0, FC_MAX_LINES)` (useAnalysisEngineLines.ts:311).

The SF card source [VERIFIED: useAnalysisEngineLines.ts:346-367]: once `reconciledBestUci !== null`, it is `rankReconciledCandidates(evalLookup, gradedCandidateUcis, mover, reconciledTieBreakUci).slice(0, SF_MAX_LINES)`. Before that (or whenever grading is off), it is the free run's own `engine.pvLines` with reconciled evals, re-sorted by expected score (unsliced). `resolveReconciledBest` is defined as the head of that same ranking (`engineEvalLookup.ts:134-141`), so `reconciledPvLines[0]` is the argmax.

Change:
- Replace the hook options `enginePvLines` + `reconciledBestUci` with `stockfishArrowLines: PvLine[]` (= `reconciledPvLines`) plus `fcArrowCount`/`sfArrowCount`. A grep shows both old options are used only in `engineArrows`.
- In `useAnalysisEngineLines`, slice the reconciled ranking to `sfRankDepth = Math.max(sfLines, sfArrows)` (option), not `SF_MAX_LINES`, so arrows > lines works. `EngineLines` then slices to `maxLines = sfLines` for display.
- Arrow loop: `for i < count`, color `i === 0 ? BEST_MOVE_ARROW : STOCKFISH_SECONDARY_LINE` (FC: `FLAWCHESS_ENGINE_ARROW` / `FLAWCHESS_SECONDARY_LINE`), same width, `layerKey: \`sf-${i}\``.
- Keep the Analysis.test.tsx:1057 contract: the `sf-0` arrow equals the reconciled argmax, and exactly one `path[fill=BEST_MOVE_ARROW]` at default settings.

### Pattern 4: Sheet trigger reused by D-03 and D-04

```tsx
// components/settings/SettingsSheetButton.tsx — skeleton
export function SettingsSheetButton({ testId, className }: { testId: string; className?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="ghost" size="icon" aria-label="Settings" title="Settings"
              data-testid={testId} className={className} onClick={() => setOpen(true)}>
        <Settings className="size-5" aria-hidden="true" />
      </Button>
      <Drawer open={open} onOpenChange={setOpen} direction="bottom">
        <DrawerContent data-testid="settings-sheet">
          <DrawerHeader><DrawerTitle>Settings</DrawerTitle></DrawerHeader>
          {/* drawer.tsx caps bottom drawers at max-h-[80vh] with NO scroll; the body must scroll itself (MobileFilterDrawer pattern) */}
          <div className="overflow-y-auto thin-scrollbar flex-1 px-4 pb-4"><SettingsPanel /></div>
        </DrawerContent>
      </Drawer>
    </>
  );
}
```
- **D-03 placement:** `AnalysisMobileHeader` (App.tsx:428-446) is `[back button][<span>Analysis</span>]`. Put the trigger right after the title span (`btn-analysis-settings`, an `h-12 w-12` tap target to match the back button's generous footprint).
- **D-04 placement (recommended):** the **top row of `BotGameMobileLayout`** (BotGameMobileLayout.tsx:99, `<div className="flex items-center">` holding only the back arrow), with the cog at `ml-auto` on the right. Reasons: (a) Phase 223's own design was "back arrow + gear on top" (223-CONTEXT.md:19), and it dropped the gear only because "an icon with no sheet behind it is worse than no icon" (BotGameMobileLayout.tsx:34-36), so this phase supplies the missing sheet; (b) the bottom `BotGameMobileBar` is published through the `mobileBoardControls` store and its tests pin "exactly four actions" (BotGameMobileBar.test.tsx:30); (c) no new payload field is needed. Mind the vertical budget comment in Bots.tsx (~485-491): the row already exists (the back arrow is `size="icon"`), so a same-size icon on the right adds no height. The mobile layout renders below 1024px (`useIsDesktop`, `DESKTOP_BREAKPOINT_PX = 1024`), so at 640-1023px both the NavHeader cog and this cog are visible. That's fine.

### Pattern 5: Card rows and skeletons for N rows (D-16)

Every site that hard-codes 2 rows or a 2-row height [VERIFIED by reading each file]:

| Site | Current | Change |
|---|---|---|
| `EngineLines.tsx:38` `export const MAX_LINES = 2;`, used at :394 `pvLines.slice(0, MAX_LINES)` | export constant | `maxLines` prop (required); delete the export |
| `EngineLines.tsx:108,118,122` `LINES_MIN_HEIGHT = 'min-h-[60px]'`, `LINES_MIN_HEIGHT_COMPACT = 'min-h-[50px]'`, `LINES_MIN_HEIGHT_3 = 'min-h-[90px]'`; `EngineLinesSkeleton` `rows?: 2 \| 3` | fixed 2/3-row heights | `rows: number` + computed min-height from named per-row constants (~30px desktop, ~25px compact per the comments' math) |
| `FlawChessEngineLines.tsx:48` `export const MAX_LINES = 2;`, :441 slice, :455 `LINES_MIN_HEIGHT`, :460 skeleton `rows={MAX_LINES}` | export constant | `maxLines` prop |
| `AnalysisTabs.tsx:441,445` FC `CardBody className={\`${LINES_MIN_HEIGHT} p-2\`}` + skeleton `rows={2}` | hard 2 | thread `fcLines` |
| `AnalysisTabs.tsx:646` `MobileEngineLines` skeleton `compact` (default 2 rows) | 2 | thread `sfLines` |
| `AnalysisDesktopCards.tsx:70` SF `CardBody className="min-h-[78px] p-2"` + skeleton default rows | 2-row height | thread `sfLines` |
| `TrainReveal.tsx:461` `<EngineLinesSkeleton rows={MAX_LINES} />` + `EngineLines` | imports `MAX_LINES` | read `sfLines` |
| `Analysis.tsx:68,931` `FC_MAX_LINES` import + `flawChessEngine.rankedLines.slice(0, FC_MAX_LINES)` in `flawChessDisplayedSans` | export import | `fcLines` |
| `useAnalysisEngineLines.ts:65-66,311,350` both `MAX_LINES` imports | constants | options |

### Pattern 6: Translucent per-engine colors (styling lock)

Tokens being replaced [VERIFIED: frontend/src/lib/theme.ts]: `FLAWCHESS_ENGINE_BADGE_SHADES` (147-151: `'oklch(0.47 0.13 80)'`, `'oklch(0.53 0.12 80)'`, `'oklch(0.59 0.10 80)'`), `SECOND_BEST_ARROW = 'rgba(147, 197, 253, 0.85)'` (432), `SECOND_BEST_BADGE_TEXT = 'oklch(0.25 0.03 255)'` (433). Kept primaries: `BEST_MOVE_ARROW = 'rgba(37, 99, 235, 0.8)'` (418), `FLAWCHESS_ENGINE_ARROW = 'rgb(213, 152, 0)'` (426).

Recommendation:
- Add two tokens, `STOCKFISH_SECONDARY_LINE` and `FLAWCHESS_SECONDARY_LINE`, as **rgba()**: same RGB as the primary arrow, lower alpha. Starting values `rgba(37, 99, 235, 0.45)` and `rgba(213, 152, 0, 0.45)` [ASSUMED, tune in UAT]. The arrow fill must not be oklch: theme.ts:421-424 records that "oklch() does not reliably paint in the SVG `fill` presentation attribute, which left the arrow invisible".
- Use the same token for the arrow fill and the badge background (one color per engine). Badge text stays white (`BADGE_CLASS` includes `text-white`, EngineLines.tsx:96 / FlawChessEngineLines.tsx:88). On the dark card a translucent fill reads as a darker hue, so white text should stay legible. Verify at UAT.
- FC primary badge: keep a solid dark gold, renaming `FLAWCHESS_ENGINE_BADGE_SHADES[0]`'s value to e.g. `FLAWCHESS_ENGINE_BADGE_PRIMARY = 'oklch(0.47 0.13 80)'`. That way the white-text contrast stays as shipped, and the terminal `#0`/`½–½` badge (FlawChessEngineLines.tsx:447) uses it too.
- Note that ChessBoard multiplies every engine arrow by `ARROW_OPACITY = 0.75` (ChessBoard.tsx:133). A 0.45-alpha arrow renders at about 0.34 effective. Tune with that in mind.

### Pattern 7: Entry points (D-01, D-02, route)

- `NavHeader` right cluster [VERIFIED: App.tsx:357-376]: `{profile?.is_guest && <Badge …>}`, `{profile?.impersonation && <ImpersonationPill …/>}`, then `<Button variant="ghost" size="sm" onClick={logout} data-testid="nav-logout">` (372). Insert a `<Link to="/settings" aria-label="Settings" title="Settings" data-testid="nav-settings">` with a `Settings` icon between the pill and Logout. Use a `Button asChild` ghost-icon style, and give it an active style when `pathname === '/settings'`.
- `MobileMoreDrawer` [VERIFIED: App.tsx:612-616]: `<div className="my-2 border-t border-border" />` then the `drawer-logout` button. Insert a `<DrawerClose asChild><Link to="/settings" data-testid="drawer-settings">…<Settings/> Settings</Link></DrawerClose>` **above** the divider.
- Route: add `<Route path="/settings" element={<SettingsPage />} />` inside the `ProtectedLayout` block, next to `/analysis` (App.tsx:1036), with no `ImportRequiredRoute`. Add `'/settings': 'Settings'` to `ROUTE_TITLES` (App.tsx:132-141). `MobileHeader` resolves its title by `pathname.startsWith`, so `/settings` needs no other change. An eager import is fine (tiny page, no engine bundle). `IMPORT_EXEMPT_ROUTES`/`isNavLocked` apply only to NAV_ITEMS, so they need no change.

### Anti-Patterns to Avoid
- **Returning a parsed object from `getSnapshot`:** this creates a new object every call, and React throws or loops ("getSnapshot should be cached") [CITED: react.dev/reference/react/useSyncExternalStore].
- **Restarting the Stockfish worker to change MultiPV**, e.g. putting `multiPv` in the worker-lifecycle effect deps (`useStockfishEngine.ts:605`). That re-downloads/re-instantiates the WASM, flashes `isReady=false`, and re-triggers the engine asset gate. Send `setoption` while idle instead.
- **Widening the FC injection to N SF moves:** `extraRootMoves` deliberately uses only `engine.pvLines[0]` and `[1]` (Analysis.tsx:~1034-1036). A user display setting must not change what the FlawChess engine searches.
- **Reading settings inside the pure-transform `/analysis` hooks:** `useAnalysisEngineLines`/`useAnalysisBoardArrows` are documented as pure transforms of already-resolved state ("calls no engine hook of its own"). Pass counts as options from `Analysis.tsx`, which needs them anyway for `unionSans`, `flawChessDisplayedSans` and the free-run MultiPV.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bottom sheet | custom fixed overlay | `components/ui/drawer` (vaul) | Focus trap, drag-to-close, portal; jsdom shims already exist in App.test.tsx:74 |
| Segmented control | button row with manual `aria-pressed` | `ToggleGroup type="single"` | Roving focus + a11y; house pattern |
| Store reactivity | Context provider + useState | `useSyncExternalStore` module store | Works across unrelated subtrees (ProtectedLayout vs page), same as `mobileBoardControls.ts` |
| Per-search MultiPV | worker restart | `setoption` while idle (grading-engine precedent) | No WASM reload |
| Arrow colors | inline rgba in components | `lib/theme.ts` tokens | frontend/CLAUDE.md rule |

## Runtime State Inventory

Not a rename/migration phase, but one stored-data item matters:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `localStorage['flawchess_bot_sound_muted']` (`'1'` = muted) already on user devices | None. Keep the key and the `'1'` semantics (locked) |
| Live service config | None (no backend/Umami config change; a new event name simply appears) | none |
| OS-registered state | None | none |
| Secrets/env vars | None | none |
| Build artifacts | Service-worker precache serves the new bundle via `registerType: 'autoUpdate'` | none |

## Common Pitfalls

### Pitfall 1: The grading union caps the SF card at 2 rows (D-14 correction)
**What goes wrong:** With SF lines = 5, the desktop SF card still shows about 2-3 rows once grading lands, or rows/arrows vanish when Maia+FC are off.
**Why it happens:** Once `reconciledBestUci !== null`, `reconciledPvLines` ranks only `gradedCandidateUcis` (the keys of `grading.gradeMap`). `commitDisplayedGradeMap` returns exactly the requested `candidateSans` (useStockfishGradingEngine.ts:210-224). `unionSans` (Analysis.tsx:955-966) includes only `san0`/`san1` from the free run. When Maia and FC are both off, grading is disabled (`gradingEnabled = maiaEnabled || flawChessEnabled`, Analysis.tsx:1071), so the card and arrows come from free-run `pvLines` only, which today is MultiPV 2.
**How to avoid:** Set the free-run MultiPV to `max(2, sfLines, sfArrows)` on `/analysis`. Build the free-run part of `unionSans` from **all** `engine.pvLines` root moves (keep the sort+dedupe so the union key stays stable). Keep the floor at 2. At MultiPV 1, `pvLines[1]` disappears, which would silently stop the INJECT-03 second-move injection into the FC search and shrink the union. The FC engine's behavior must not depend on a display setting.
**Warning signs:** The SF card row count drops when the Maia card is switched off. A test with Maia+FC off and `sfLines=5` renders fewer than 5 rows.

### Pitfall 2: A MultiPV change doesn't apply until the next move
**What goes wrong:** On mobile `/analysis`, the user raises SF lines in the sheet and nothing changes until they move.
**Why it happens:** `setoption MultiPV` is sent only at `uciok` (useStockfishEngine.ts:501).
**How to avoid:** Pattern 2, steps 3-4 (resend while idle plus a re-analyze effect on `multiPv` change).

### Pitfall 3: ToggleGroup single-select deselect
**What goes wrong:** Tapping the already-active "2" fires `onValueChange('')`, which writes an invalid value or clears the setting.
**How to avoid:** Use the same guard as FlawFilterControl.tsx:596-601: `if (!v) return;`. Then parse with `Number(v)` and validate before writing. Fire `trackEvent` only when the value actually changes.

### Pitfall 4: Dynamic Tailwind arbitrary classes
**What goes wrong:** `` `min-h-[${rows * 30}px]` `` never ships, because Tailwind scans source for literal class strings.
**How to avoid:** Use an inline `style={{ minHeight: rows * ENGINE_LINE_ROW_PX }}` built from named constants, or a literal lookup table.

### Pitfall 5: FC card renders fewer rows than the setting
**What goes wrong:** UAT reports "FC lines = 5 shows only 2 rows" as a bug.
**Why it happens:** Root candidates are Maia moves up to 0.9 cumulative policy mass (`select.ts:21`, `export const POLICY_MASS_THRESHOLD = 0.9;`), capped by `export const ROOT_CANDIDATE_HARD_CAP = 15;` (`policyTemperature.ts:56`), plus injected SF moves. `buildRankedLines` emits one line per root child (treeCommon.ts:427-469).
**How to avoid:** Accept it and document it (helper text such as "up to N lines"). Size skeletons to N but don't treat fewer rendered rows as a failure. Optionally size the FC container's min-height to `min(N, rankedLines.length)` after first paint. That's a UAT call.

### Pitfall 6: Testid collisions with existing nav-order tests
**What goes wrong:** `App.test.tsx` collects `screen.getAllByTestId(/^drawer-nav-/)` across the whole drawer and asserts an exact list (App.test.tsx:~367-379). A `drawer-nav-settings` row breaks it.
**How to avoid:** Use `drawer-settings` (like `drawer-logout`). Desktop `nav-settings` is safe because the order test scopes to `within(navigation "Main navigation")`, and the cog sits outside that `<nav>`.

### Pitfall 7: Draw order of primary vs non-primary arrows
**What goes wrong:** A translucent rank-2 arrow sharing a start square paints over the solid primary.
**Why it happens:** `arrowSortKey` maps every engine color to tier 3 (`lib/arrowColor.ts:66-77`, `default: return 3`), and then sorts by `b.width - a.width`. Equal widths keep their input order (stable sort), so later array entries paint on top.
**How to avoid:** Push each engine's arrows in reverse rank order (N-1 … 0), so the primary is last within its width tier. This doesn't violate D-15: the width sort is unchanged.

### Pitfall 8: `getAllBy`/fill-color test pins
`Analysis.test.tsx:1057-1066` finds the SF arrow via `path[fill="${BEST_MOVE_ARROW}"]`. Non-primary SF arrows must use a different color string. `useGameOverlay.test.ts:14,91` imports `SECOND_BEST_ARROW`, so deleting the token breaks that import.

### Pitfall 9: Dead `useGameOverlay.boardArrows`
`useGameOverlay`'s only caller is `Analysis.tsx:1233`. Analysis reads only `gameOverlay.squareMarkers`, `.evalCp/.evalMate/.evalDepth` and `.lastMoveHighlightColor` (grep of `gameOverlay.` in Analysis.tsx), so the `SECOND_BEST_ARROW` block (useGameOverlay.ts:~291-310) is **dead in production**. Recommend deleting that block, its import, and the `SECOND_BEST_ARROW` assertion line in useGameOverlay.test.ts:91. The whole `boardArrows` field is also dead, but retiring it is out of scope. Leave a follow-up note.

## Code Examples

### Train free-play arrows with a count (D-13)
```typescript
// lib/trainArrows.ts — replace buildTrainFreePlayArrows(bestMoveUci) (line 229).
// Today: enginePointerArrows(bestMoveUci, 'free-best') — one TRAIN_BEST_MOVE_ARROW arrow,
// width TRAIN_BEST_MOVE_ARROW_WIDTH = 0.5 (trainArrows.ts:154), TRAIN_BEST_MOVE_ARROW = BEST_MOVE_ARROW (theme.ts:578).
export function buildTrainFreePlayArrows(pvLines: PvLine[], count: number): BoardArrow[] {
  const arrows: BoardArrow[] = [];
  for (let i = Math.min(count, pvLines.length) - 1; i >= 0; i--) {   // reverse: primary paints last (Pitfall 7)
    const squares = squaresFromUci(pvLines[i]?.moves[0] ?? null);
    if (squares === null) continue;
    arrows.push({ ...squares, color: i === 0 ? TRAIN_BEST_MOVE_ARROW : STOCKFISH_SECONDARY_LINE,
                  width: TRAIN_BEST_MOVE_ARROW_WIDTH, layerKey: `free-${i}` });
  }
  return arrows;
}
```
Inputs are `freePlay.pvLines`, which is already stale-guarded (`engineIsCurrent`, useTrainFreePlay.ts:232-233), and `sfArrows`. Memoize on `[freePlay.pvLines, sfArrows]` (TrainSolveScreen.tsx:1331-1334). `buildTrainStepArrows` and the reveal overlay builders are **not** touched (D-13). Note that `layerKey: 'free-best'` is referenced in trainArrows.test.ts:474-495, so update those tests.

### Umami
```typescript
trackEvent('settings-change', { setting: 'sfLines', value: String(n) }); // Record<string, string> only
trackEvent('settings-reset');                                             // recommended: one event for Reset
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| In-game / account-menu mute toggle | No production caller since Phase 223 (sounds.ts header) | Phase 223 | This phase gives `useMuted`/`setMuted` their caller back |
| Rank-based badge shades + light-blue 2nd-best | Solid primary + one translucent color per engine | this phase | Remove `FLAWCHESS_ENGINE_BADGE_SHADES`, `SECOND_BEST_ARROW`, `SECOND_BEST_BADGE_TEXT` (knip will flag leftovers) |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | localStorage key names `flawchess_settings_{fc,sf}_{lines,arrows}` | Pattern 1 | None functionally; just freeze them before ship (renaming later loses users' settings) |
| A2 | Starting alpha 0.45 for both translucent tokens | Pattern 6 | Visual only; UAT-tuned per CONTEXT |
| A3 | `storage` event with `key === null` signals `clear()` | Pattern 1 | Worst case a cross-tab clear isn't picked up until reload |
| A4 | UCI `setoption` must only be sent while the engine is idle (rule per the classic UCI spec; codebase follows it) | Pattern 2 | Sending mid-search could trap the WASM engine (FLAWCHESS-7V class); the recommended design only sends from the idle branch anyway |
| A5 | Translucent fill + white text is legible on the dark card | Pattern 6 | UAT; fall back to a dark-ink text token if not |

## Open Questions

1. **Desktop cog on `/analysis` navigates away and drops the free-play tree.**
   - What we know: D-01 makes the NavHeader cog a link. NavHeader is visible on `/analysis` at ≥640px, and leaving `/analysis` unmounts the page. `AnalysisRoute` is keyed by `?line`, so free-play moves are not in the URL. Game-mode position comes back via URL params, but unsaved sidelines don't.
   - Recommendation: keep D-01 as locked (it's a header link, as with any other nav item). Flag it in the plan as a known trade-off. A cheap alternative (not locked, needs user consent) is to render `SettingsSheetButton` instead of the Link when `pathname.startsWith('/analysis')`.
2. **Grading depth with a wide union.** The union can reach about 15 (Maia mass set + FC 5 + SF 5) at the fixed `GRADING_MOVETIME_SAFETY_CAP_MS = 4000` (useStockfishGradingEngine.ts:55). Phase 158 measured depth parity only for union sizes 6-8. This is a user-chosen breadth/depth trade (consistent with D-11's philosophy), so no mitigation is planned. Mention it in the Stockfish helper text if desired.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node | build/test | ✓ | v24.19.0 | — |
| npm | build/test | ✓ | 11.17.0 | — |
| vitest | tests | ✓ | 5.0.0 | — |
| Chrome (claude-in-chrome) | UAT of colors/sheets | per session | — | jsdom tests + manual UAT |

No blocking gaps. Baseline: the 7 most relevant existing test files pass (152 tests, 1.3s) [VERIFIED: `npx vitest run` this session].

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | vitest 5.0.0 + @testing-library/react, per-file `// @vitest-environment jsdom` |
| Config file | `frontend/vite.config.ts` (`test` block) + `frontend/src/vitest.setup.ts` |
| Quick run command | `cd frontend && npx vitest run <files>` |
| Full suite command | `cd frontend && npm test -- --run` (+ `npm run lint && npm run build && npm run knip`) |

### Decision → Test Map
| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| store / D-08 | defaults (2/1/2/1), round-trip, out-of-range + garbage + non-integer → default, subscribers re-render, reset clears all + unmutes, localStorage throw → defaults | unit | `npx vitest run src/lib/__tests__/engineSettings.test.ts` | ❌ Wave 0 |
| sound | Switch toggles `MUTE_KEY` `'1'`/`'0'`; a pre-existing `'1'` reads as muted | unit/component | `… src/components/settings/__tests__/SettingsPanel.test.tsx` | ❌ Wave 0 |
| D-07/D-09/D-10 | 3 sections in order; toggle items 1-5 / 0-3; re-tap of active item is a no-op; `trackEvent` called once per change with stringified value; Reset → defaults + `settings-reset` | component | same file (mock `@/lib/analytics`) | ❌ Wave 0 |
| D-01/D-02/route | `nav-settings` link → `/settings` with aria-label; `drawer-settings` above `drawer-logout`; existing order tests still pass; `/settings` title "Settings" | component | `npx vitest run src/App.test.tsx` | ✅ extend |
| D-03/D-04/D-06 | `btn-analysis-settings` / bot cog open `settings-sheet` containing the panel, no navigation | component | `… SettingsSheetButton.test.tsx` (+ a BotGameMobileLayout render test) | ❌ Wave 0 |
| D-12 | `setoption name MultiPV value N` at init uses the option; a changed option is re-sent before the next `position`, never while thinking; a change mid-search triggers stop + re-search | unit (MockWorker) | `npx vitest run src/hooks/__tests__/useStockfishEngine.test.ts` | ✅ update the line-226 test |
| D-14 | arrows: i=0 = argmax solid, i≥1 = ranks 2..N translucent, no repeated move; count 0 → no SF arrows; fallback path uses free-run lines; FC arrows rankedLines[0..n) | unit (renderHook) | `npx vitest run src/hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts` | ❌ Wave 0 (no test file exists for this hook) |
| D-14 union | `unionSans` includes all free-run roots; SF card gets N rows with Maia+FC off; free-run MultiPV floor 2 | page | `npx vitest run src/pages/__tests__/Analysis.test.tsx` | ✅ extend (it already clears localStorage) |
| D-15 | non-primary uses the engine's width and secondary token | unit | useAnalysisBoardArrows test | ❌ Wave 0 |
| D-16 / styling | `EngineLines`/`FlawChessEngineLines` render exactly `maxLines` rows (replace the pinned "exactly 2 rows" test at FlawChessEngineLines.test.tsx:119 with a default-plus-5 case); badge colors primary vs secondary token; skeleton renders `rows` | component | `npx vitest run src/components/analysis/__tests__/` | ✅ update |
| D-11/D-13 | free play passes `multiPv=max(lines,arrows)`; `buildTrainFreePlayArrows(pvLines, n)` emits n arrows, 0 → none; reveal legend arrows unaffected | unit | `npx vitest run src/lib/__tests__/trainArrows.test.ts src/hooks/__tests__/useTrainFreePlay.test.ts` | ✅ update |
| retire 2nd-best | `useGameOverlay` no longer emits a second-best arrow | unit | `npx vitest run src/hooks/__tests__/useGameOverlay.test.ts` | ✅ update line 14/91 |

### Sampling Rate
- **Per task commit:** the task's own test files (seconds).
- **Per wave merge:** `cd frontend && npm test -- --run && npm run lint && npm run build`.
- **Phase gate:** full pre-merge frontend gate incl. `npm run knip` green, then browser UAT (translucent colors, sheet on mobile /analysis + bot game, live MultiPV change).

### Wave 0 Gaps
- [ ] `src/lib/__tests__/engineSettings.test.ts`
- [ ] `src/components/settings/__tests__/SettingsPanel.test.tsx`
- [ ] `src/components/settings/__tests__/SettingsSheetButton.test.tsx` (vaul jsdom shims: copy from App.test.tsx:74)
- [ ] `src/hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts`
- Mutation-proof the D-14 fix: revert the loop to `reconciledBestUci ?? …` and confirm the new arrow test fails (project memory: "prove a gap fix by reverting it").

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | `/settings` sits behind the existing `ProtectedLayout` token check |
| V3 Session Management | no | — |
| V4 Access Control | no | No server data |
| V5 Input Validation | yes | Strict parse of localStorage values (integer and in range, else default), since localStorage is user/extension-writable |
| V6 Cryptography | no | — |

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Tampered localStorage (e.g. `sf_lines = 500`) inflating MultiPV / CPU | Denial of service (self) | Validate range on read; never pass raw storage to `setoption` |
| Analytics payload leakage | Information disclosure | Event data carries only the setting id and a small integer |

## Sources

### Primary (HIGH confidence)
- In-repo source read this session: `lib/sounds.ts`, `hooks/useUserFlag.ts`, `lib/mobileBoardControls.ts`, `hooks/useStockfishEngine.ts`, `hooks/useStockfishGradingEngine.ts`, `hooks/analysis/useAnalysisBoardArrows.ts`, `hooks/analysis/useAnalysisEngineLines.ts`, `pages/Analysis.tsx` (500-560, 880-1130, 1655-1695, 2195-2295), `lib/engineEvalLookup.ts`, `lib/engine/treeCommon.ts`, `lib/engine/select.ts`, `lib/engine/policyTemperature.ts`, `lib/engine/mctsSearch.ts`, `components/analysis/{EngineLines,FlawChessEngineLines,AnalysisTabs,AnalysisDesktopCards}.tsx`, `components/train/{TrainReveal,TrainSolveScreen}.tsx`, `hooks/useTrainFreePlay.ts`, `lib/trainArrows.ts`, `hooks/useGameOverlay.ts`, `components/board/{ChessBoard.tsx,arrowGeometry.ts}`, `lib/arrowColor.ts`, `lib/theme.ts`, `App.tsx`, `components/bots/{BotGameMobileBar,BotGameMobileLayout}.tsx`, `components/ui/{toggle-group,drawer}.tsx`, `lib/analytics.ts`, `frontend/{knip.json,eslint.config.js,vite.config.ts,package.json}`, test files listed above.
- Phase 223 CONTEXT (`milestones/v2.20-phases/223-*/223-CONTEXT.md:19,123-129`): the original "back arrow + gear on top" bot layout.

### Secondary (MEDIUM confidence)
- [react.dev useSyncExternalStore](https://react.dev/reference/react/useSyncExternalStore): getSnapshot must return a cached/immutable value; stable `subscribe`.
- [MDN Window storage event](https://developer.mozilla.org/en-US/docs/Web/API/Window/storage_event): not fired in the window that made the change.
- [Stockfish UCI & Commands](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-Protocol-and-Stockfish-Commands.html): MultiPV spin 1-500, default 1; >1 weakens the best line.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (no new deps; all components verified in-repo)
- Architecture: HIGH (every data path traced in source; D-14 correction verified at Analysis.tsx:955-966/1071)
- Pitfalls: HIGH for code-derived ones; MEDIUM for visual tuning (A2, A5)

**Research date:** 2026-10-03
**Valid until:** 2026-11-02 (stable; re-check `Analysis.tsx` line anchors if other engine work lands first)
