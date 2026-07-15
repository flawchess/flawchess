# Phase 169: Clocked Board + Game Loop (`useBotGame`) - Pattern Map

**Mapped:** 2026-07-12
**Files analyzed:** 12 (new) + 0 modified
**Analogs found:** 12 / 12

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|-----------------|----------------|
| `frontend/src/hooks/useBotGame.ts` | hook (orchestrator) | event-driven / request-response | `frontend/src/hooks/useChessGame.ts` (chess.js state machine) + `frontend/src/hooks/useFlawChessEngine.ts` (provider lifecycle, abort) | role-match (composite of two) |
| `frontend/src/lib/chessClock.ts` | utility (pure clock math) | transform | no direct analog — `useFlawChessEngine.ts`'s throttle/debounce timestamp-delta idiom is the closest transferable pattern | partial |
| `frontend/src/lib/sounds.ts` | utility (audio) | event-driven | `frontend/src/hooks/useUserFlag.ts` (localStorage + `useSyncExternalStore` shape, for the mute-persistence half only) | partial |
| `frontend/src/lib/botGamePgn.ts` (PGN/[%clk]/Termination builder, split out of the hook per CLAUDE.md nesting/LOC limits) | utility (transform) | transform | `frontend/src/lib/analysisUrl.ts` (standalone-module-for-unit-testability precedent); chess.js `setComment`/`setHeader`/`pgn()` API itself | partial |
| `frontend/src/components/bots/ClockDisplay.tsx` | component | request-response (props→render) | `frontend/src/components/board/PlayerBar.tsx` (player info row alongside the board) | role-match |
| `frontend/src/components/bots/GameResultDialog.tsx` | component | request-response | no existing modal/dialog component in `components/board/` — nearest is a generic UI dialog primitive (check `components/ui/`) | partial |
| `frontend/src/components/bots/GameResultStrip.tsx` | component | request-response | `frontend/src/components/board/PlayerBar.tsx` (compact inline info strip) | partial |
| `frontend/src/components/bots/MoveListPanel.tsx` | component | request-response | `frontend/src/components/board/MoveList.tsx` + `HorizontalMoveList.tsx` (SAN list, click-to-navigate, current-ply highlight) | exact |
| `frontend/src/components/bots/GameControls.tsx` | component | event-driven | `frontend/src/components/board/BoardControls.tsx` (button row acting on board/game state) | role-match |
| `frontend/src/pages/Bots.tsx` | page (route) | request-response | `frontend/src/pages/Analysis.tsx` (lazy-loaded route, deep-link param handling, `ChessBoard` + hook wiring) | role-match |
| `frontend/src/components/board/ChessBoard.tsx` (MODIFIED: add turn-gating + view-only mode) | component | event-driven | itself (existing) — see Pattern for the additive prop | exact (self) |
| `public/sound/*` (vendored assets) | config/asset | n/a | none — net-new asset directory | no analog |

## Pattern Assignments

### `frontend/src/hooks/useBotGame.ts` (hook, event-driven)

**Analogs:** `frontend/src/hooks/useChessGame.ts` (state shape / move commit) + `frontend/src/hooks/useFlawChessEngine.ts` (provider lifecycle / abort discipline)

**Chess.js state-commit pattern** (`useChessGame.ts` lines 162-203):
```typescript
const makeMove = useCallback(
  (sourceSquare: string, targetSquare: string): boolean => {
    const chess = chessRef.current;
    try {
      const result = chess.move({ from: sourceSquare, to: targetSquare, promotion: 'q' });
      if (!result) return false;
      const san = result.san;
      const from = result.from;
      const to = result.to;
      setMoveHistory((prev) => {
        const atEnd = currentPly === prev.length;
        const newHistory = atEnd ? [...prev, san] : [...prev.slice(0, currentPly), san];
        setCurrentPly(newHistory.length);
        setPosition(chess.fen());
        setLastMove({ from, to });
        return newHistory;
      });
      return true;
    } catch {
      return false;
    }
  },
  [currentPly],
);
```
`useBotGame` mirrors this shape (`chessRef`, functional `setMoveHistory` update to avoid stale closures) but ALSO must: (a) reject the move up-front if it isn't the user's turn (`chess.turn() !== userColor`), (b) call `chess.setComment('[%clk h:mm:ss]')` immediately after every `chess.move(...)` — both user and bot — per Pattern 5 below, (c) check end conditions after every move, not just on request.

**Provider bring-up + per-turn AbortController** (`useFlawChessEngine.ts` lines 144-159, 214-230, 279-291):
```typescript
useEffect(() => {
  const pool = createWorkerPool();
  const queue = createMaiaQueue();
  poolRef.current = pool;
  queueRef.current = queue;
  return () => {
    pool.terminate();
    queue.terminate();
  };
}, []); // once per game — NOT re-run per FEN (unlike the analysis hook's `[enabled]` dep)

// Per-turn: fresh AbortController, never reused across turns
abortControllerRef.current?.abort();
const controller = new AbortController();
abortControllerRef.current = controller;

// Abort-on-unmount / abort-on-teardown guard (resign, new game, navigation)
useEffect(() => {
  return () => abortControllerRef.current?.abort();
}, []);
```
Per RESEARCH.md Pattern 1/2, do NOT copy `useFlawChessEngine`'s debounced-FEN-triggers-search `useEffect` — bot turn dispatch is an imperative async function call ("it's the bot's turn now"), not an effect keyed on `fen`. Call `selectBotMove` directly (harness-style):
```typescript
// Source: frontend/src/lib/engine/selectBotMove.ts (signature, frozen)
const uci = await selectBotMove(
  fen,
  { elo: settings.botElo, blend: settings.blend, budget: {
      maxNodes: FLAWCHESS_BOT_MAX_NODES, maxPlies: FLAWCHESS_BOT_MAX_PLIES,
      concurrency: FLAWCHESS_BOT_CONCURRENCY, stopRule: FLAWCHESS_BOT_STOP_RULE,
    } },
  { policy: queue.policy, grade: pool.grade, rng: Math.random },
  controller.signal,
);
```
Import `FLAWCHESS_BOT_*` from `@/lib/engine/botBudget` directly, NOT from `useFlawChessEngine.ts`'s re-export (that module also owns the unrelated `FLAWCHESS_ENGINE_MAX_NODES` analysis-board constants — importing through it risks touching/confusing the wrong profile, per RESEARCH.md Pitfall 6).

**Error handling pattern** (`useFlawChessEngine.ts` lines 268-276):
```typescript
.catch((err: unknown) => {
  if (controller.signal.aborted) return;
  Sentry.captureException(err, { tags: { source: 'flawchess-engine' } });
  setIsSearching(false);
});
```
Adapt tag to `{ tags: { source: 'bot-game' } }` per CLAUDE.md Sentry rules — capture on genuine rejection, never on an expected abort.

---

### `frontend/src/lib/chessClock.ts` (utility, transform)

**No direct in-repo analog** — this is genuinely new (RESEARCH.md confirms). Closest transferable idiom is the **wall-clock-delta-not-tick-count** pattern already used for a different purpose in `useFlawChessEngine.ts`'s debounce (`Date.now() - lastFenChangeAtRef.current`, lines 173-176) — same "never trust interval cadence, recompute from `Date.now()`" discipline, applied here to a live countdown display instead of a debounce window.

**Core reconciliation pattern** (from RESEARCH.md Pattern 3/4 — cite directly, no repo precedent exists):
```typescript
const revealDelayMs = REVEAL_DELAY_MIN_MS + rng() * (REVEAL_DELAY_MAX_MS - REVEAL_DELAY_MIN_MS);
const turnStartedAt = Date.now();
const [uci] = await Promise.all([
  selectBotMove(fen, settings, deps, controller.signal),
  new Promise((resolve) => setTimeout(resolve, revealDelayMs)),
]);
const realElapsedMs = Date.now() - turnStartedAt;
const syntheticMs = computeSyntheticDebit(botClockRemainingMs, incrementMs);
const debitMs = Math.max(realElapsedMs, syntheticMs);
const clampedDebitMs = Math.min(debitMs, botClockRemainingMs - NEVER_FLAG_FLOOR_MS);
```
Keep this pure/sync/unit-testable in `chessClock.ts` (no React), mirroring how `useFlawChessEngine.ts` keeps FEN-debounce math inline but simple enough to reason about — here the logic is complex enough (D-05's clamp + max) to warrant full extraction, consistent with `botSampling.ts`'s precedent of splitting pure decision logic out of the impure orchestrator (`selectBotMove.ts`'s own module doc: "every actual sampling/argmax/fallback decision lives in `botSampling.ts`'s pure, sync, separately-exported helpers").

**Visibility-pause pattern** (cited from RESEARCH.md Pattern 4, MDN):
```typescript
useEffect(() => {
  const handleVisibility = () => {
    if (document.visibilityState === 'hidden') {
      pausedAtRef.current = Date.now();
    } else if (pausedAtRef.current !== null) {
      const pausedForMs = Date.now() - pausedAtRef.current;
      turnStartedAtRef.current += pausedForMs; // shift the anchor, not the elapsed total
      pausedAtRef.current = null;
    }
  };
  document.addEventListener('visibilitychange', handleVisibility);
  return () => document.removeEventListener('visibilitychange', handleVisibility);
}, []);
```

---

### `frontend/src/lib/sounds.ts` (utility, event-driven)

**Analog (mute-persistence half only):** `frontend/src/hooks/useUserFlag.ts`

**localStorage + useSyncExternalStore pattern** (full file, 42 lines — reuse the shape, NOT the email-scoping):
```typescript
// Source: frontend/src/hooks/useUserFlag.ts
const listeners = new Set<() => void>();
function subscribe(cb: () => void): () => void {
  listeners.add(cb);
  return () => { listeners.delete(cb); };
}
function readFlag(name: string): boolean {
  try { return localStorage.getItem(storageKey(name)) === '1'; } catch { return false; }
}
export function useMuted(): boolean {
  return useSyncExternalStore(subscribe, () => readFlag(), () => false);
}
export function setMuted(muted: boolean): void {
  try { localStorage.setItem(MUTE_KEY, muted ? '1' : '0'); } catch { return; }
  listeners.forEach((l) => l());
}
```
Deviate from `useUserFlag` in two ways per RESEARCH.md's own recommendation: (1) flat, non-email-scoped key (`flawchess_bot_sound_muted`) since guests need mute too; (2) real toggle semantics (both true→false and false→true), not `useUserFlag`'s one-shot set-only-to-true design. Default state is **unmuted** (D-10), the inverse of `useUserFlag`'s always-false-until-set default — invert the boolean's storage sense accordingly (`'1'` = muted, absence = unmuted).

**Audio playback (no in-repo precedent — cite RESEARCH.md directly):**
```typescript
// new Audio(url) per clip, played on demand; unlock-on-first-gesture per Pitfall 4
const audio = new Audio(`/sound/${clip}.mp3`);
void audio.play();
```

---

### `frontend/src/lib/botGamePgn.ts` (utility, transform — PGN/[%clk]/Termination builder)

**Analog:** `frontend/src/lib/analysisUrl.ts` (module-extraction-for-testability precedent) + chess.js API directly (`frontend/node_modules/chess.js/dist/types/chess.d.ts`, verified)

**Extraction rationale** (mirrors `analysisUrl.ts` module doc, lines 1-6):
```typescript
// Extracted to a standalone module so the [%clk]/Termination encoding behavior is
// directly unit-testable without rendering any page components or mounting the hook.
```

**`[%clk]` emission pattern** (Pattern 5, RESEARCH.md — cite chess.js API directly):
```typescript
chess.move({ from, to, promotion });
chess.setComment(`[%clk ${formatClockHms(remainingMsAfterIncrement)}]`);
// later: const pgnText = chess.pgn(); // comments auto-embedded as {[%clk h:mm:ss]}
```

**`[Termination]`/`[Result]` header pattern** (Pattern 6, backend contract at `app/services/normalization.py:505-511`, verified):
```typescript
chess.setHeader('Termination', outcome.reason); // 'checkmate' | 'resignation' | 'timeout' | 'draw' | 'abandoned' | 'unknown'
chess.setHeader('Result', outcome.pgnResult);   // '1-0' | '0-1' | '1/2-1/2'
```
Backend closed-vocabulary map (`app/services/normalization.py:505-512`, exact copy):
```python
_FLAWCHESS_TERMINATION_HEADER_MAP: dict[str, Termination] = {
    "checkmate": "checkmate",
    "resignation": "resignation",
    "timeout": "timeout",
    "draw": "draw",
    "abandoned": "abandoned",
    "unknown": "unknown",
}
```
stalemate/threefold/fifty-move/insufficient-material must all map to the PGN header `'draw'` (no finer-grained header exists) — keep the client-side result-dialog text specific, only the PGN header is coarsened.

**TC string format** (Pattern 7 — base+increment seconds, NOT minutes label):
```typescript
const tcStrForBackend = `${baseSeconds}+${incrementSeconds}`; // e.g. "300+3" for a 5+3 preset
```

---

### `frontend/src/components/bots/MoveListPanel.tsx` (component, request-response)

**Analog:** `frontend/src/components/board/MoveList.tsx` (full file, 31 lines) + `HorizontalMoveList.tsx`

**Full pattern to copy (near-verbatim reuse, add view-only scroll-back per D-13):**
```typescript
// Source: frontend/src/components/board/MoveList.tsx
interface MoveListProps {
  moveHistory: string[];
  currentPly: number;
  onMoveClick: (ply: number) => void;
}
export function MoveList({ moveHistory, currentPly, onMoveClick }: MoveListProps) {
  const items: HorizontalMoveItem[] = moveHistory.map((san, idx) => {
    const ply = idx + 1;
    const isWhite = idx % 2 === 0;
    const moveNumber = Math.floor(idx / 2) + 1;
    return {
      key: ply, ply,
      numberLabel: isWhite ? `${moveNumber}.` : null,
      san,
      isCurrent: currentPly === ply,
      testId: `move-${ply}`,
      ariaLabel: `Move ${moveNumber}. ${san} (${isWhite ? 'white' : 'black'})`,
    };
  });
  return <HorizontalMoveList items={items} onMoveClick={onMoveClick} />;
}
```
D-13's addition on top: `onMoveClick` must set a view-only ply pointer distinct from the live game ply (the board's `onPieceDrop` is disabled unless viewing the live position) — model as two separate numbers (`liveGamePly` vs `viewedPly`) rather than overloading `currentPly`, mirroring the two-independent-state-pieces lesson from RESEARCH.md Pitfall 5 (draw-throttle vs draw-accept-gate) applied here to viewing-vs-live state.

Arrow-key stepping precedent (`useChessGame.ts` lines 262-279) — reuse the same guard against capturing keys while typing in an input:
```typescript
const handleKeyDown = (e: KeyboardEvent) => {
  const tag = (e.target as HTMLElement).tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
  if (e.key === 'ArrowLeft') { e.preventDefault(); goBack(); }
  else if (e.key === 'ArrowRight') { e.preventDefault(); goForward(); }
};
```

---

### `frontend/src/components/bots/ClockDisplay.tsx` (component, request-response)

**Analog:** `frontend/src/components/board/PlayerBar.tsx` (adjacent-to-board info row — read for layout/spacing conventions, not reproduced here since it's a small presentational file; same directory pattern as `ChessBoard.tsx`/`BoardControls.tsx`).

**Theme sourcing requirement** (CLAUDE.md, verified against `frontend/src/lib/theme.ts`):
```typescript
// Source: frontend/src/lib/theme.ts (WDL/severity color precedent, lines 26-36)
export const WDL_WIN = 'oklch(0.50 0.14 145)';
export const WDL_LOSS = 'oklch(0.50 0.15 25)';
```
D-07's low-time red/urgent styling MUST be added as a new named constant in `theme.ts` (e.g. `CLOCK_LOW_TIME_URGENT`), never hard-coded in `ClockDisplay.tsx` — follow the existing pattern of semantic color constants defined once and imported (see `MOVE_HIGHLIGHT_SQUARE` used by `ChessBoard.tsx` line 342 as the cross-component-import precedent).

---

### `frontend/src/components/bots/GameControls.tsx` (component, event-driven)

**Analog:** `frontend/src/components/board/BoardControls.tsx` (button row acting on game/board state — read for the `Button` variant + `data-testid`/`aria-label` conventions per CLAUDE.md Browser Automation Rules). Resign/draw-offer buttons follow the same `variant="brand-outline"` (secondary) vs `variant="default"` (primary) rule from CLAUDE.md — resign/draw-offer are secondary actions.

**Confirmation-gate pattern** — no existing two-step confirm UI in `components/board/`; check `components/ui/` for a shared `AlertDialog`/confirm primitive before hand-rolling D-04's resign confirmation.

---

### `frontend/src/pages/Bots.tsx` (page, request-response)

**Analog:** `frontend/src/pages/Analysis.tsx` (deep-link param handling, lazy-loaded route, `ChessBoard` + hook wiring)

**Lazy-route registration pattern** (`App.tsx` line 42):
```typescript
const AnalysisPage = lazy(() => import('./pages/Analysis'));
```
`Bots.tsx` registers the same way, unlinked from nav per D-14 (no `nav-*` `data-testid` link added this phase).

**Deep-link precedence pattern to reuse for D-12's "Analyze this game" CTA** (`analysisUrl.ts` lines 39-52, verified):
```typescript
export function buildAnalysisLineUrl(sans: string[]): string {
  const chess = new Chess();
  const uci: string[] = [];
  for (const san of sans) {
    try {
      const move = chess.move(san);
      uci.push(`${move.from}${move.to}${move.promotion ?? ''}`);
    } catch { break; }
  }
  if (uci.length === 0) return ANALYSIS_PATH;
  return `${ANALYSIS_PATH}?${LINE_PARAM}=${uci.join(',')}`;
}
```
Call directly: `navigate(buildAnalysisLineUrl(sanMoveHistory))` on the Analyze CTA click — no new URL-building code needed, this helper already exists and is exported.

---

### `frontend/src/components/board/ChessBoard.tsx` (MODIFIED — additive turn-gating + view-only prop)

**Analog:** itself. `onPieceDrop` is currently an unconditional `(sourceSquare, targetSquare) => boolean` callback (line 63-64, `handlePieceDrop`/`handleSquareClick` at lines 309-328/360-366) — the turn-gating and view-only-disables-input logic belongs in the CALLER's `onPieceDrop` implementation (return `false` early when not the live position / not the user's turn), not as a new prop on `ChessBoard` itself, consistent with how `useChessGame.makeMove` already does its own gating (`MAX_EXPLORER_PLY` cap, lines 165-166) before ever touching the board component. Do not add a `disabled` prop to `ChessBoard` unless the click-to-select behavior (line 309-328, `handleSquareClick`) also needs to be suppressed during view-only mode — if so, mirror the existing `selectedSquare` reset-on-position-change pattern (lines 297-302) for resetting selection when snapping back to the live position.

## Shared Patterns

### Provider lifecycle + AbortController discipline
**Source:** `frontend/src/hooks/useFlawChessEngine.ts` lines 144-159 (mount-once effect), 279-291 (abort-on-disable guard), 299-304 (unmount cleanup)
**Apply to:** `useBotGame.ts` — pool/queue created once per game mount, terminated on unmount; a fresh `AbortController` per bot turn, aborted on resign/new-game/navigation/unmount (never one shared controller across turns, per RESEARCH.md Anti-Pattern).

### Sentry capture in async catch blocks
**Source:** `frontend/src/hooks/useFlawChessEngine.ts` lines 268-276
**Apply to:** `useBotGame.ts`'s `selectBotMove` await — skip capture when `signal.aborted`, capture with `{ tags: { source: 'bot-game' } }` otherwise (CLAUDE.md Sentry rules).

### Theme constants, never hard-coded colors
**Source:** `frontend/src/lib/theme.ts` (WDL_WIN/WDL_LOSS/MOVE_HIGHLIGHT_SQUARE precedent)
**Apply to:** `ClockDisplay.tsx`'s low-time red/urgent state (D-07) — add a new named constant to `theme.ts`, import from there.

### data-testid / aria-label / semantic HTML conventions
**Source:** CLAUDE.md Browser Automation Rules + `ChessBoard.tsx` lines 379, `MoveList.tsx` line 24 (`testId: 'move-${ply}'`, `ariaLabel`)
**Apply to:** every new interactive element in `components/bots/*` — `btn-resign`, `btn-draw-offer`, `btn-mute`, `board-btn-*` for board-adjacent controls, `move-${ply}` reused verbatim from `MoveList.tsx`'s existing convention.

### Standalone-module extraction for unit-testability
**Source:** `frontend/src/lib/analysisUrl.ts` module doc (lines 1-6), `frontend/src/lib/engine/botSampling.ts` (pure helpers split from `selectBotMove.ts`'s impure orchestration)
**Apply to:** `chessClock.ts` and `botGamePgn.ts` — keep clock-math and PGN-building pure/sync and importable without mounting React, exactly as RESEARCH.md's Wave-0 test plan requires (`src/lib/__tests__/chessClock.test.ts` tests clock math with zero DOM).

### Functional state updates to avoid stale closures
**Source:** `frontend/src/hooks/useChessGame.ts` lines 181-195 (`setMoveHistory((prev) => {...})`)
**Apply to:** `useBotGame.ts`'s move-commit path — the bot-turn async function reads `moveHistory`/`currentPly` after an `await`, so any state mutation must go through the functional updater form, not a captured stale value.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `public/sound/*` (vendored AGPLv3+ lila `sfx`/`piano` set) | asset | n/a | No audio assets exist anywhere in the frontend today; this is the first audio feature (RESEARCH.md confirms, Pitfall 1 license correction applies — vendor `sfx`/`piano`, NOT the non-free "standard" set D-08 names literally) |
| `frontend/src/components/bots/GameResultDialog.tsx` (the modal shell specifically, not its content) | component | request-response | No existing full-screen/overlay modal in `components/board/`; check `frontend/src/components/ui/` for a shared Dialog primitive before building one from scratch — flagged for planner to verify at plan time, not assumed absent |

## Metadata

**Analog search scope:** `frontend/src/hooks/`, `frontend/src/lib/`, `frontend/src/lib/engine/`, `frontend/src/components/board/`, `frontend/src/pages/`, `app/services/normalization.py`
**Files scanned:** ~20 read directly (useChessGame.ts, useFlawChessEngine.ts, useUserFlag.ts, selectBotMove.ts, botBudget.ts, ChessBoard.tsx, MoveList.tsx, analysisUrl.ts, normalization.py excerpt) + directory listings of hooks/, lib/engine/, components/board/
**Pattern extraction date:** 2026-07-12
