# Phase 170: localStorage Resume - Pattern Map

**Mapped:** 2026-07-13
**Files analyzed:** 12 (4 new lib/hook, 1 new component, 3 new test, 4 modified, 1 modified test not counted separately)
**Analogs found:** 12 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/lib/botGameSnapshot.ts` | utility (pure lib, versioned localStorage) | file-I/O (localStorage read/write) | `frontend/src/lib/welcomeDismissal.ts` + `frontend/src/hooks/useUserFlag.ts` | role-match (no existing versioned-schema analog; these two supply the guard/try-catch shape) |
| `frontend/src/lib/botPendingStore.ts` | utility (pure lib, localStorage queue) | CRUD (append/remove on an array) | `frontend/src/hooks/useUserFlag.ts` (try/catch shape) + `botGameSnapshot.ts` itself (sibling, same phase) | partial (queue-of-records has no direct precedent; compose the same guard pattern) |
| `frontend/src/hooks/useStoreBotGame.ts` | hook (TanStack mutation) | request-response | `frontend/src/hooks/useEnqueueGame.ts` (`useTier1Enqueue`) | exact (mutation shape, apiClient call, no manual Sentry capture) |
| `frontend/src/components/bots/ResumeGate.tsx` (new) | component | request-response / UI gate | `frontend/src/components/bots/GameControls.tsx` | exact (same directory, Dialog-confirm pattern, `data-testid` convention) |
| `frontend/src/lib/__tests__/botGameSnapshot.test.ts` | test | transform (pure fn tests) | `frontend/src/lib/__tests__/chessClock.test.ts` | exact (pure-module vitest shape, no fake timers needed) |
| `frontend/src/lib/__tests__/botPendingStore.test.ts` | test | CRUD | `frontend/src/lib/__tests__/chessClock.test.ts` | role-match |
| `frontend/src/hooks/__tests__/useStoreBotGame.test.ts` | test | request-response | `frontend/src/hooks/__tests__/useBotGame.test.ts` (mocking/renderHook conventions) | role-match (useBotGame.test.ts is hook-test convention source; a mutation-hook test is simpler — no fake timers needed, just `vi.mock('@/api/client')`) |
| `frontend/src/hooks/useBotGame.ts` (MODIFIED — add `resume?`, `live` gate) | hook (game-loop orchestrator) | event-driven / streaming (clock tick, effects) | itself (read in full below) | n/a — modification target |
| `frontend/src/pages/Bots.tsx` (MODIFIED — snapshot detect, gate, drain) | route/page component | request-response + event-driven | itself | n/a — modification target |
| `frontend/src/api/client.ts` (MODIFIED — add `botsApi`) | config/api-module | request-response | `feedbackApi` (client.ts:223-226) — simplest one-method precedent | exact |
| `frontend/src/lib/chessClock.ts` (MODIFIED — add fold helper) | utility (pure) | transform | itself, alongside `hasFlaggedOnDebit`/`applyIncrementMs` | n/a — modification target |
| `frontend/src/hooks/__tests__/useBotGame.test.ts` / `chessClock.test.ts` (MODIFIED — extend) | test | transform/event-driven | themselves | n/a — modification target |

## Pattern Assignments

### `frontend/src/lib/botGameSnapshot.ts` (utility, file-I/O)

**Analogs:** `frontend/src/lib/welcomeDismissal.ts` (SSR guard) + `frontend/src/hooks/useUserFlag.ts` (try/catch + corruption tolerance)

**SSR/undefined guard** (`welcomeDismissal.ts:7-10`):
```typescript
export function isWelcomeDismissed(): boolean {
  if (typeof localStorage === 'undefined') return false;
  return localStorage.getItem(WELCOME_DISMISSED_KEY) === '1';
}
```

**Try/catch read/write, degrade-to-safe-default** (`useUserFlag.ts:24-30, 43-55`):
```typescript
function readFlag(name: string, email: string | undefined | null): boolean {
  try {
    return localStorage.getItem(storageKey(name, email)) === '1';
  } catch {
    return false;
  }
}

export function setUserFlag(name: string, email: string | undefined | null): void {
  const key = storageKey(name, email);
  try {
    if (localStorage.getItem(key) === '1') return;
    localStorage.setItem(key, '1');
  } catch {
    return;
  }
  listeners.forEach((l) => l());
}
```

**What to build on top (no existing analog — this is new territory per RESEARCH.md):**
- `version: 1` field + hard-drop-on-mismatch (no migration): `if (parsed.version !== CURRENT_SNAPSHOT_VERSION) return null;`
- JSON.parse failure and shape-validation failure both degrade to `null` (no resumable snapshot), matching the `useUserFlag.ts` "catch → safe default" shape, not a throw.
- **Capture-once discipline**: on first detected corruption, clear the bad key immediately (`localStorage.removeItem`) so subsequent reads on the same visit see a clean "no snapshot" state, and call `Sentry.captureException` exactly once at that clear point — mirrored from `useBotGame.ts`'s own `Sentry.captureException(err, { tags: { source: 'bot-game' } })` shape (see `useBotGame.ts:244`, `:864`, `:901`). Use the SAME `source: 'bot-game'` tag for consistency (this is client-side game state, same domain).
- Snapshot payload uses `chess.pgn()` (verified lossless round-trip, D-08 RESOLVED) — NOT SAN+clk-array. `parse`/`serialize`/`validate` are pure functions; no React import needed (mirrors `welcomeDismissal.ts`'s zero-React-import shape, not `useUserFlag.ts`'s `useSyncExternalStore` wrapper — the snapshot module itself does not need external-store subscription; `Bots.tsx` reads it once on mount via a plain effect/state, no live-subscription requirement per CONTEXT.md).

**Payload shape** (from RESEARCH.md, PGN variant — use this verbatim):
```typescript
export const CURRENT_SNAPSHOT_VERSION = 1;

export interface BotGameSnapshot {
  version: 1;
  gameUuid: string;
  settings: BotGameSettings; // import from '@/hooks/useBotGame'
  pgn: string;
  whiteClockMs: number;
  blackClockMs: number;
  movesSinceLastDecline: number;
  hasLeftBook: boolean;
  hasFiredLowTime: boolean;
  savedAt: number;
}
```

---

### `frontend/src/lib/botPendingStore.ts` (utility, CRUD queue)

**Analog:** same guard/try-catch shape as `botGameSnapshot.ts` above, applied to an array-typed key (`flawchess_bot_pending_store`, D-12 — a SEPARATE key from the in-progress snapshot). No existing queue-of-records precedent in the codebase; compose from the `useUserFlag.ts` try/catch primitives.

**Shape to build:**
```typescript
export interface PendingStoreEntry {
  gameUuid: string;
  pgn: string;
  settings: BotGameSettings;
}

export function enqueuePendingStore(entry: PendingStoreEntry): void { /* try/catch, cap-bounded push */ }
export function listPendingStore(): PendingStoreEntry[] { /* try/catch, JSON.parse, [] on failure */ }
export function removePendingStore(gameUuid: string): void { /* try/catch, filter + rewrite */ }
```
Every read/write wrapped exactly like `useUserFlag.ts:24-30/48-54` (try/catch, degrade to `[]`/no-op — never throw). The queue cap constant (`MAX_PENDING_STORE_ENTRIES` or similar) is Claude's-discretion per CONTEXT.md; extract as a named constant per CLAUDE.md no-magic-numbers.

---

### `frontend/src/hooks/useStoreBotGame.ts` (hook, request-response mutation)

**Analog:** `frontend/src/hooks/useEnqueueGame.ts` (`useTier1Enqueue`) — closest exact-shape TanStack mutation in the codebase.

**Full analog** (`useEnqueueGame.ts:1-29`):
```typescript
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { EnqueueTier1Response } from '@/types/api';

export function useTier1Enqueue(gameId: number) {
  const queryClient = useQueryClient();
  return useMutation<EnqueueTier1Response, Error, void>({
    mutationFn: async () => {
      const response = await apiClient.post<EnqueueTier1Response>(
        `/imports/eval/tier1/${gameId}`,
      );
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['imports', 'eval-coverage'] });
    },
  });
}
```

**Deviations required for `useStoreBotGame`:**
- Call `botsApi.storeGame` (client.ts addition below), not an inline `apiClient.post` — mirrors the `positionBookmarksApi`/`feedbackApi` grouped-export convention used everywhere else in `client.ts`.
- No `onSuccess` cache invalidation needed — this is a queue-drain call site, not a query-backed UI list.
- **`retry` MUST be a predicate function** (per-status differentiation, D-13) — this is new relative to `useEnqueueGame.ts` (which uses the global `retry: 1` default from `queryClient.ts:22-24`). Do NOT add a `Sentry.captureException` — the global `MutationCache.onError` (`queryClient.ts:13-19`) already captures every mutation failure with `tags: { source: 'tanstack-mutation' }`.
- Recommended retry predicate (RESEARCH.md, verbatim):
```typescript
useMutation({
  mutationFn: botsApi.storeGame,
  retry: (failureCount, error) => {
    if (!axios.isAxiosError(error)) return failureCount < MAX_STORE_RETRIES;
    const status = error.response?.status;
    if (status === 422) return false;
    if (status === 401) return true;
    return failureCount < MAX_STORE_RETRIES;
  },
});
```
- The actual "remove queue entry" decision (2xx → remove, 422 → capture-in-drain-loop + remove, 401/5xx → keep) is the DRAIN LOOP's job (in `Bots.tsx` or a small drain helper), not the mutation's own `onSuccess`/`onError` — see D-13.

---

### `frontend/src/api/client.ts` (MODIFIED — add `botsApi`)

**Analog:** `feedbackApi` (client.ts:223-226) — the simplest single-method grouped-export precedent.

```typescript
// client.ts:223-226
export const feedbackApi = {
  submit: (data: FeedbackRequest) =>
    apiClient.post<FeedbackResponse>('/feedback', data).then((r) => r.data),
};
```

**Pattern to copy exactly** (no new file — every resource lives inline in `client.ts`):
```typescript
export const botsApi = {
  storeGame: (data: StoreBotGameRequest) =>
    apiClient.post<StoreBotGameResponse>('/bots/games', data).then((r) => r.data),
};
```

**Types must mirror `app/schemas/bots.py:26-38` exactly** (read in full):
```python
class StoreBotGameRequest(BaseModel):
    game_uuid: str
    pgn: str = Field(max_length=MAX_BOT_PGN_LENGTH)
    user_color: Color
    bot_elo: int = Field(ge=_MIN_BOT_ELO, le=_MAX_BOT_ELO)
    play_style_blend: float = Field(ge=_MIN_PLAY_STYLE_BLEND, le=_MAX_PLAY_STYLE_BLEND)
    tc_preset: str = Field(max_length=_MAX_TC_PRESET_LENGTH)
```
→ TypeScript:
```typescript
export interface StoreBotGameRequest {
  game_uuid: string;
  pgn: string;
  user_color: 'white' | 'black';
  bot_elo: number;
  play_style_blend: number;
  tc_preset: string; // MUST be toBackendTcStr(baseSeconds, incrementSeconds) — D-14 correction, NOT a display preset
}
export interface StoreBotGameResponse {
  game_id: number;
  created: boolean;
}
```
Place these interfaces near the other request/response types in `client.ts` (grep existing `EnqueueTier1Response` placement in `types/api.ts` for the project's actual type-location convention — confirm at plan time whether types live in `client.ts` inline or `types/api.ts`).

---

### `frontend/src/hooks/useBotGame.ts` (MODIFIED — `resume?` seam + `live` gate, D-10/D-03)

**This is a modification of an existing, heavily-annotated file — read in full (1005 lines), already loaded into context above.** Key excerpts to base the diff on:

**Refs/state block to seed from `resume`** (`useBotGame.ts:267-361`, verbatim current shape):
```typescript
export function useBotGame(settings: BotGameSettings): UseBotGameState {
  const chessRef = useRef<Chess>(new Chess());
  const clockBaseRef = useRef<{ white: number; black: number }>(
    freshClockBase(settings.baseSeconds),
  );
  const turnStartedAtRef = useRef<number>(0);
  const pausedAtRef = useRef<number | null>(null);
  const viewedPlyRef = useRef(0);
  const liveGamePlyRef = useRef(0);
  const outcomeRef = useRef<BotGameOutcome | null>(null);
  // ...
  const lastRootPracticalScoreRef = useRef<number | null>(null);
  const hasLeftBookRef = useRef(false);
  const hasFiredLowTimeRef = useRef(false);

  const [moveHistory, setMoveHistory] = useState<string[]>([]);
  const [viewedPly, setViewedPly] = useState(0);
  const [activeColor, setActiveColor] = useState<MoverColor>('white');
  const [whiteClockMs, setWhiteClockMs] = useState(settings.baseSeconds * 1000);
  const [blackClockMs, setBlackClockMs] = useState(settings.baseSeconds * 1000);
  const [movesSinceLastDecline, setMovesSinceLastDecline] = useState(DRAW_OFFER_COOLDOWN_MOVES);
```

**Exact field-by-field seed table (from RESEARCH.md Pitfall 1 — treat as the acceptance checklist, not just documentation):**

| Ref/state | Current line | Fresh default | Resume seed |
|---|---|---|---|
| `chessRef` | 270 | `new Chess()` | `new Chess(); .loadPgn(resume.pgn)` |
| `clockBaseRef` | 271-273 | `freshClockBase(...)` | `{ white: resume.whiteClockMs, black: resume.blackClockMs }` |
| `viewedPlyRef`/`viewedPly` | 285, 350 | `0` | live ply post-restore |
| `hasLeftBookRef` | 341 | `false` | `resume.hasLeftBook` |
| `hasFiredLowTimeRef` | 343 | `false` | `resume.hasFiredLowTime` |
| `lastRootPracticalScoreRef` | 332 | `null` | stays `null` (D-09 sentinel, do not seed) |
| `moveHistory` | 349 | `[]` | `new Chess().loadPgn(resume.pgn).history()` |
| `activeColor` | 351 | `'white'` | derived from `moveHistory.length` parity |
| `whiteClockMs`/`blackClockMs` | 352-353 | `settings.baseSeconds*1000` | `resume.whiteClockMs`/`resume.blackClockMs` |
| `movesSinceLastDecline` | 360 | `DRAW_OFFER_COOLDOWN_MOVES` | `resume.movesSinceLastDecline` |
| `outcomeRef`/`outcome` | 297, 354 | `null` | stays `null` (a resume is by construction unfinished) |
| `turnStartedAtRef`/`pausedAtRef` | 279-280 | `Date.now()` on mount (674-686) | NOT seeded — gated by `live` instead |

**Turn-anchor mount effect to gate on `live`** (`useBotGame.ts:674-686`):
```typescript
useEffect(() => {
  const now = Date.now();
  turnStartedAtRef.current = now;
  if (document.visibilityState === 'hidden') pausedAtRef.current = now;
}, []);
```

**Clock-tick effect to gate on `live`** (`useBotGame.ts:694-737`, dep array at 737):
```typescript
useEffect(() => {
  if (outcome) return;
  const tick = (): void => { /* ... */ };
  tick();
  const id = setInterval(tick, CLOCK_TICK_INTERVAL_MS);
  return () => clearInterval(id);
}, [activeColor, outcome, finalizeGame, settings.userColor, chargeableElapsedMs]);
```

**Bot-turn-trigger effect to gate on `live`** (`useBotGame.ts:977-981` — the effect the D-03 gap analysis flags as the sharp bug):
```typescript
useEffect(() => {
  if (outcome) return;
  if (activeColor === settings.userColor) return;
  runBotTurnRef.current?.(BOT_SEARCH_BUDGET);
}, [moveHistory, activeColor, outcome, settings.userColor]);
```
Add `if (!live) return;` as an additional guard in all three effects above. The provider bring-up effect (`useBotGame.ts:761-786`, `pool.warm()`/`queue.warm()`) MUST stay unconditional — do not gate it.

**Anti-pattern to avoid (visibilitychange effect, `useBotGame.ts:741-757`):**
```typescript
useEffect(() => {
  const handleVisibility = (): void => {
    if (document.visibilityState === 'hidden') {
      if (pausedAtRef.current === null) pausedAtRef.current = Date.now();
    } else if (pausedAtRef.current !== null) {
      const pausedForMs = Date.now() - pausedAtRef.current;
      turnStartedAtRef.current = shiftAnchorForPause(turnStartedAtRef.current, pausedForMs);
      pausedAtRef.current = null;
    }
  };
  document.addEventListener('visibilitychange', handleVisibility);
  return () => document.removeEventListener('visibilitychange', handleVisibility);
}, []);
```
This has `[]` deps intentionally (only touches refs). The NEW hide-time snapshot write needs `activeColor`/`moveHistory`/`clockBaseRef`/`hasLeftBookRef` — do NOT bolt it onto this handler's closure (stale-read bug, Phase 169 "half-invariant" shape). Add a SEPARATE effect with a correct dependency array (mirroring the clock-tick effect's dep shape), or read via refs kept fresh by a sync effect (see `liveGamePlyRef` sync pattern at `useBotGame.ts:376-378`).

**`commitMove`'s post-move clock-write site** (`useBotGame.ts:470-534`) is where the every-move snapshot write belongs (D-01 primary path) — no fold needed there (value is already settled). Call `writeSnapshot()` as the last statement, unconditional on whether `resume` was present.

**`newGame()` must additionally clear the snapshot** (`useBotGame.ts:643-665`, D-10) — add a `clearSnapshot()` call inside this callback.

**Error-report tag convention to reuse** (`useBotGame.ts:244, 864, 901`):
```typescript
Sentry.captureException(err, { tags: { source: 'bot-game' } });
```

---

### `frontend/src/lib/chessClock.ts` (MODIFIED — add clock-fold helper)

**Analog:** co-locate alongside `hasFlaggedOnDebit`/`applyIncrementMs` in the same file — this module's own stated purpose is "pure, synchronous, React-free clock and pacing math."

**Existing sibling pure functions to mirror style** (`chessClock.ts:136-138, 189-191`):
```typescript
export function applyIncrementMs(remainingMs: number, incrementMs: number): number {
  return Math.max(0, remainingMs + incrementMs);
}

export function hasFlaggedOnDebit(remainingMs: number, debitMs: number): boolean {
  return remainingMs - debitMs <= 0;
}
```

**New helper to add** (RESEARCH.md, verbatim):
```typescript
export function foldElapsedIntoClockBase(remainingMs: number, elapsedMs: number): number {
  return Math.max(0, remainingMs - elapsedMs);
}
```
Docstring must cite D-01/D-02 exactly as the file's other functions cite their governing decision letters (`chessClock.ts:180-191`'s comment style is the template).

---

### `frontend/src/pages/Bots.tsx` (MODIFIED — snapshot detection, gate, drain)

**Full file already read** (247 lines). Key excerpts:

**The D-14 stub to replace/gate** (`Bots.tsx:160-165`):
```typescript
export default function BotsPage(): ReactElement {
  const navigate = useNavigate();
  const isDesktop = useIsDesktop();
  const muted = useMuted();
  const game = useBotGame(BOT_GAME_SETTINGS);
```
Becomes: read snapshot on mount → if present, `useBotGame(BOT_GAME_SETTINGS or resume.settings, resume, ...)` with `live=false` until `confirmLive()`; render `ResumeGate` overlay; if absent, today's unconditional `useBotGame(BOT_GAME_SETTINGS)` call (D-04's "no snapshot → today's D-14 stub" branch, left AS-IS per phase boundary — 171 replaces this branch, not 170).

**Mount-effect precedent for a one-time side effect** (`Bots.tsx:169-171`, the existing dismissed-flag reset):
```typescript
useEffect(() => {
  if (game.outcome === null) setDialogDismissed(false);
}, [game.outcome]);
```
Use an analogous `useEffect(() => { /* drain queue */ }, [])` — empty-deps, mount-once — for D-13's "drain the queue on `/bots` mount, before the gate renders."

**`data-testid` convention** (`Bots.tsx:227`, `GameControls.tsx:54,71,93,105,116`):
```typescript
data-testid="bots-page"
data-testid="board-btn-resign"
data-testid="resign-confirm-dialog"
data-testid="board-btn-resign-confirm"
data-testid="board-btn-offer-draw"
data-testid="board-btn-mute"
```
Kebab-case, component-prefixed. New elements should follow: `data-testid="resume-gate"`, `data-testid="btn-resume"`, `data-testid="btn-discard"`, `data-testid="discard-confirm-dialog"`, `data-testid="btn-discard-confirm"`.

---

### `frontend/src/components/bots/ResumeGate.tsx` (NEW component)

**Analog:** `frontend/src/components/bots/GameControls.tsx` (full file read above) — same directory, same Dialog-confirm shape for the D-05 discard confirmation (mirrors the existing resign-confirm exactly).

**Imports pattern** (`GameControls.tsx:1-13`):
```typescript
import { useState } from 'react';
import type { ReactElement } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
```

**Confirm-dialog pattern to copy for Discard** (`GameControls.tsx:40-77`, resign confirm — mirror verbatim for discard):
```typescript
const [resignDialogOpen, setResignDialogOpen] = useState(false);

const handleConfirmResign = (): void => {
  setResignDialogOpen(false);
  onResignConfirmed();
};

<Button
  variant="brand-outline"
  size="sm"
  onClick={() => setResignDialogOpen(true)}
  data-testid="board-btn-resign"
>
  Resign
</Button>
<Dialog open={resignDialogOpen} onOpenChange={setResignDialogOpen}>
  <DialogContent data-testid="resign-confirm-dialog">
    <DialogHeader>
      <DialogTitle>Resign this game?</DialogTitle>
      <DialogDescription>You&apos;ll lose this game against the bot.</DialogDescription>
    </DialogHeader>
    <DialogFooter>
      <Button variant="outline" onClick={() => setResignDialogOpen(false)}>
        Cancel
      </Button>
      <Button
        variant="destructive"
        onClick={handleConfirmResign}
        data-testid="board-btn-resign-confirm"
      >
        Resign
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```
For `ResumeGate`: "Resume" is a primary CTA (`variant="default"`, per CLAUDE.md primary-button rule — NOT `brand-outline`, since this is the single high-emphasis action on the gate). "Discard" is secondary (`variant="brand-outline"`, matching the analog's `Resign` trigger), opening a confirm dialog worded per D-05: *"This game will be lost — unfinished games are never saved."* The confirm button inside the dialog uses `variant="destructive"` (matches the analog's discard-is-irreversible styling).

**Game-identity line** (D-04/D-06, no existing analog — new copy): *"Blitz 5+3 vs FlawChess Bot (1500) · 14 moves · 2 days ago"* — derive TC label from `settings.baseSeconds`/`incrementSeconds` (do NOT reuse `toBackendTcStr`'s wire format for display — that's the base-seconds string; the gate needs a human label, likely a small local formatter), move count from `resume.pgn` parsed move count or a stored ply count, and age from `Date.now() - resume.savedAt` (D-06).

---

## Shared Patterns

### localStorage guard + try/catch (ALL new lib modules)
**Source:** `frontend/src/lib/welcomeDismissal.ts:8` (SSR guard) + `frontend/src/hooks/useUserFlag.ts:24-30,43-55` (try/catch)
**Apply to:** `botGameSnapshot.ts`, `botPendingStore.ts` — every read/write.
```typescript
if (typeof localStorage === 'undefined') return <safe default>;
try {
  // localStorage.getItem/setItem/removeItem
} catch {
  return <safe default>;
}
```

### Sentry capture-once, tagged `source: 'bot-game'`
**Source:** `frontend/src/hooks/useBotGame.ts:244, 864, 901`
**Apply to:** snapshot corruption (capture once at clear point), book-fetch failure (already existing pattern), NOT to the `useStoreBotGame` mutation (global `MutationCache.onError` already covers it — do not duplicate).
```typescript
Sentry.captureException(err, { tags: { source: 'bot-game' } });
```

### TanStack mutation, grouped api-module call, no component-level Sentry
**Source:** `frontend/src/hooks/useEnqueueGame.ts` (full file) + `frontend/src/lib/queryClient.ts:13-19` (global capture)
**Apply to:** `useStoreBotGame.ts`
```typescript
export function useStoreBotGame() {
  return useMutation<StoreBotGameResponse, Error, StoreBotGameRequest>({
    mutationFn: botsApi.storeGame,
    retry: (failureCount, error) => { /* per-status predicate, D-13 */ },
  });
}
```

### Grouped api-module export (no new file per resource)
**Source:** `frontend/src/api/client.ts:223-226` (`feedbackApi`), `:107-121` (`positionBookmarksApi`)
**Apply to:** new `botsApi` block, same file.

### `data-testid` kebab-case, component-prefixed
**Source:** `frontend/src/components/bots/GameControls.tsx:54,71,93,105,116`, `frontend/src/pages/Bots.tsx:227`
**Apply to:** `ResumeGate.tsx`, any new interactive element in `Bots.tsx`.

### `Dialog` confirm-before-destructive-action
**Source:** `frontend/src/components/bots/GameControls.tsx:40-77` (resign confirm)
**Apply to:** `ResumeGate.tsx`'s Discard confirmation (D-05) — same primitive import, same open/onOpenChange local-state shape, same `variant="destructive"` on the final confirm button.

### Vitest hook-test conventions (mocking, fake timers, renderHook)
**Source:** `frontend/src/hooks/__tests__/useBotGame.test.ts` header + mocks section (`@vitest-environment jsdom` pragma at file top, `vi.mock('@/lib/engine/selectBotMove', ...)`, `renderHook`/`act` from `@testing-library/react`, `-t` filter-token doc convention listing each behavior tested)
**Apply to:** `useStoreBotGame.test.ts` (mock `@/api/client`'s `botsApi`, no fake timers needed — a mutation resolves via microtask, not wall-clock), extensions to `useBotGame.test.ts` itself (resume-seed / prewarm-gate / stable-uuid groups, matching the file's own documented token list).

### Vitest pure-module test conventions (no DOM/timers)
**Source:** `frontend/src/lib/__tests__/chessClock.test.ts:1-30`
**Apply to:** `botGameSnapshot.test.ts`, `botPendingStore.test.ts` — plain `describe`/`it`/`expect` from `vitest`, explicit millisecond/string inputs, no `@vitest-environment jsdom` pragma needed unless `localStorage` itself must be exercised (if so, add the pragma and consider `vi.stubGlobal('localStorage', ...)` or rely on jsdom's built-in `localStorage`).

## No Analog Found

None — every new file has at least a role-match or partial analog above. `botPendingStore.ts`'s queue-of-records shape is the weakest match (no existing localStorage-array precedent in the codebase); compose it from `useUserFlag.ts`'s guard primitives rather than searching further, per RESEARCH.md's explicit "no existing versioned/structured snapshot pattern to copy" finding.

## Metadata

**Analog search scope:** `frontend/src/lib/`, `frontend/src/hooks/`, `frontend/src/hooks/__tests__/`, `frontend/src/lib/__tests__/`, `frontend/src/components/bots/`, `frontend/src/pages/`, `frontend/src/api/client.ts`, `app/schemas/bots.py`
**Files scanned:** `useBotGame.ts` (full, 1005 lines), `chessClock.ts` (full, 254 lines), `botGamePgn.ts` (full, 114 lines), `welcomeDismissal.ts` (full, 22 lines), `useUserFlag.ts` (full, 55 lines), `Bots.tsx` (full, 247 lines), `GameControls.tsx` (full, 122 lines), `client.ts` (grep + targeted reads), `queryClient.ts` (full, 27 lines), `useEnqueueGame.ts` (full, 29 lines), `useBotGame.test.ts` (header), `chessClock.test.ts` (header), `app/schemas/bots.py` (targeted read)
**Pattern extraction date:** 2026-07-13
