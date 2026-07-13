---
phase: 169-clocked-board-game-loop-usebotgame
reviewed: 2026-07-13T15:40:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - frontend/src/App.tsx
  - frontend/src/components/board/HorizontalMoveList.tsx
  - frontend/src/components/bots/ClockDisplay.tsx
  - frontend/src/components/bots/GameControls.tsx
  - frontend/src/components/bots/GameResultDialog.tsx
  - frontend/src/components/bots/GameResultStrip.tsx
  - frontend/src/components/bots/MoveListPanel.tsx
  - frontend/src/hooks/useBotGame.ts
  - frontend/src/hooks/__tests__/useBotGame.test.ts
  - frontend/src/lib/botDrawGate.ts
  - frontend/src/lib/botGameEnd.ts
  - frontend/src/lib/botGamePgn.ts
  - frontend/src/lib/chessClock.ts
  - frontend/src/lib/sounds.ts
  - frontend/src/lib/theme.ts
  - frontend/src/lib/engine/botBudget.ts
  - frontend/src/lib/engine/deadlineSearch.ts
  - frontend/src/lib/__tests__/botDrawGate.test.ts
  - frontend/src/lib/__tests__/botGameEnd.test.ts
  - frontend/src/lib/__tests__/botGamePgn.test.ts
  - frontend/src/lib/__tests__/chessClock.test.ts
  - frontend/src/lib/__tests__/sounds.test.ts
  - frontend/src/lib/engine/__tests__/deadlineSearch.test.ts
  - frontend/src/pages/Bots.tsx
  - tests/test_bot_pgn_clk_roundtrip.py
findings:
  critical: 0
  warning: 8
  info: 7
  total: 15
critical_resolved: 1
status: issues_found
---

# Phase 169: Code Review Report (re-review after Plan 10 gap closure)

**Reviewed:** 2026-07-13T15:40:00Z
**Depth:** standard
**Files Reviewed:** 24
**Status:** issues_found

## Summary

Third review pass on Phase 169. The first obligation was to verify — at the level of runtime
invariants, not symbol presence — that the two previous BLOCKERs (CR-01 hidden-tab pause, CR-02
never-flag clamp) are actually closed by Plan 10.

**Gate results:**

| Prior finding | Verdict | Evidence |
|---|---|---|
| **CR-02** (never-flag clamp) | **CLOSED** | `flagIfOutOfTime()` (useBotGame.ts:381-392) is called at :487 (before `chess.move()` at :491) and at :764 (before `chess.move()` at :772). `commitMove` (:414) is now a plain `clockBaseRef[mover] - debitMs` with no floor; `applyIncrementMs`'s `Math.max(0, …)` cannot forgive an overrun because a strictly-positive `remainingBeforeIncrement` is guaranteed by the caller's flag test. `commitMove` has exactly two callers (`attemptMove`, `runBotTurn`) — verified exhaustively, not by grep. Both flag before applying. |
| **CR-01** (hidden-tab pause) | **PARTIALLY OPEN** | The routing invariant holds: `useBotGame.ts` contains exactly four `Date.now()` reads (`resetTurnAnchor`, `chargeableElapsedMs`, the mount effect, the visibility handler) and **zero** raw now-minus-anchor reads. All three elapsed-time consumers — the tick's flag check (:611), the bot's committed debit (:756), the user's move debit (:486) — route through `chargeableElapsedMs()`. **But** `pausedAtRef` is only ever written from a `visibilitychange` event and is never seeded from the *initial* `document.visibilityState`, so a game that **mounts while the tab is already hidden** charges and flags on the full background wall-clock interval. Carried forward below. |

Tooling is green (`tsc -b`: 0 errors; `eslint`: 0 errors; `knip`: clean; 86/86 tests pass across the
phase's 7 suites; no `text-xs` violations in new files). That is precisely why the remaining defects
matter — none of them are caught by an existing gate.

Beyond the carried-forward CR-01, the substantive new findings: the D-16 think deadline is
structurally **unreachable** in the `blend <= 0` regime (WR-02); `commitMove` still enforces the
CR-02 invariant by *comment* rather than *construction* (WR-01) — the exact failure mode that has
now regressed twice; the hook silently ignores post-mount `settings` changes, which Phase 171's
setup screen walks straight into (WR-03); three callbacks still gate on the `outcome` state instead
of the `outcomeRef` latch the same file introduced for exactly this reason (WR-04); and the backend
PGN "round-trip" test asserts a hand-typed literal rather than anything `botGamePgn.ts` emits (WR-06).

---

## Critical Issues

### CR-01: Hidden-tab pause is not applied when the game mounts into an already-hidden tab — RESOLVED (commit 21bdd932)

> **Resolution (2026-07-13, applied during execute-phase):** Fixed exactly as prescribed in the Fix
> section below — `pausedAtRef` is now seeded from the initial `document.visibilityState` in the
> mount effect, and the handler's `hidden` branch is idempotent. Two regression tests were added to
> `useBotGame.test.ts` (mount-into-hidden-tab, duplicate-hidden-event); both were confirmed to FAIL
> against the pre-fix code and to pass after, so neither fix can be silently reverted. Full frontend
> gate green afterwards (`tsc -b` 0 errors, eslint 0 errors, knip clean, 1900/1900 tests).
> The original finding is preserved verbatim below for the record.

**File:** `frontend/src/hooks/useBotGame.ts:229`, `:597-599`, `:654-666`

**Issue:**
`pausedAtRef` initializes to `null` and is written **only** from the `visibilitychange` listener's
`hidden` branch:

```ts
const pausedAtRef = useRef<number | null>(null);                    // :229
...
useEffect(() => { turnStartedAtRef.current = Date.now(); }, []);    // :597-599 — no visibility read
...
useEffect(() => {
  const handleVisibility = (): void => {
    if (document.visibilityState === 'hidden') {
      pausedAtRef.current = Date.now();                             // :657
    } else if (pausedAtRef.current !== null) {                      // :658
      const pausedForMs = Date.now() - pausedAtRef.current;
      turnStartedAtRef.current = shiftAnchorForPause(turnStartedAtRef.current, pausedForMs);
      pausedAtRef.current = null;
    }
  };
  document.addEventListener('visibilitychange', handleVisibility);
  ...
}, []);
```

`visibilitychange` fires only on a *transition*. If the component mounts while the document is
already hidden, no `hidden` event ever arrives, so `pausedAtRef` stays `null`. Consequences:

1. `chargeableElapsedMs()` → `computeChargeableElapsedMs(anchor, null, now)` degrades to a raw
   `now - anchor` read — the exact bypass CR-01 was created to eliminate.
2. The 100 ms tick charges the entire hidden interval to the active side and, at `remaining <= 0`
   (:633), **finalizes a timeout loss**.
3. When the tab finally becomes visible, `handleVisibility` takes the `else if` branch, sees
   `pausedAtRef.current === null`, and **does nothing** — `shiftAnchorForPause` never runs, so the
   charge is permanent and unrecoverable.

Net effect: a 5+3 game opened in a background tab (middle-click / "open link in new tab", browser
session restore, prerender, bfcache restore) and left for 5 minutes is **already lost on time before
the user ever looks at it**. This is squarely on Phase 170's path: a localStorage-resumed game mounts
on *page load*, which is exactly when a hidden document is most likely.

The Plan 10 regression tests cannot catch this — every hidden-tab test in
`useBotGame.test.ts:512-653` calls `setHidden(true)` *after* `renderHook`, i.e. all of them exercise
the transition path, which does work.

Secondary hardening in the same handler: the `hidden` branch unconditionally overwrites
`pausedAtRef.current`. Safari emits `visibilitychange` alongside `pagehide` and can re-fire on
bfcache restore; a second `hidden` write re-baselines an in-progress pause forward and silently
charges the interval between the two events.

**Fix:**

```ts
// useBotGame.ts — mount effect (:597)
useEffect(() => {
  const now = Date.now();
  turnStartedAtRef.current = now;
  // CR-01 (bug fix): `visibilitychange` fires only on a TRANSITION, so a game
  // mounting into an ALREADY-hidden tab (background-tab open, session restore,
  // prerender, Phase 170's localStorage resume on page load) never set
  // pausedAtRef — chargeableElapsedMs then degraded to a raw now-minus-anchor
  // read and the tick flagged the active side on pure background wall-clock
  // time, with the resume handler unable to undo it (its `!== null` guard
  // fails). Seed the pause from the INITIAL visibility state.
  if (document.visibilityState === 'hidden') pausedAtRef.current = now;
}, []);

// useBotGame.ts — visibility handler (:655)
const handleVisibility = (): void => {
  if (document.visibilityState === 'hidden') {
    // Idempotent: a duplicate 'hidden' event (Safari pagehide / bfcache) must
    // not re-baseline an in-progress pause forward.
    if (pausedAtRef.current === null) pausedAtRef.current = Date.now();
  } else if (pausedAtRef.current !== null) {
    // …unchanged…
  }
};
```

Regression test to add (flips visibility **before** `renderHook`, so it fails on today's code):

```ts
it('a game mounting into an already-hidden tab charges no background time and does not flag', async () => {
  setHidden(true);                                    // BEFORE renderHook
  const { result } = renderHook(() => useBotGame({ ...DEFAULT_SETTINGS, baseSeconds: 3 }));
  await advance(30_000);
  expect(result.current.outcome).toBeNull();
  expect(result.current.whiteClockMs).toBe(3000);
});
```

---

## Warnings

### WR-01: The CR-02 invariant is enforced by comment, not by construction

**File:** `frontend/src/hooks/useBotGame.ts:400-418`

**Issue:** `commitMove` documents its precondition in an 11-line comment ("Callers MUST call
`flagIfOutOfTime` before applying a move; do not reintroduce a floor here") but does nothing to
enforce it. A future call site that forgets produces a **negative** `clockBaseRef[mover]`, which
`applyIncrementMs`'s `Math.max(0, …)` then silently converts back into exactly the never-flag
behaviour D-15 deleted — no error, no test failure, no type error, and no lint warning. This is the
third review round on this one invariant; it has already regressed twice while protected only by
prose.

**Fix:** make it structural. Either fold the flag test into `commitMove` (so `commitMove` owns "can
this move be applied at all?" and returns `false` when the mover flagged), or fail loudly in dev:

```ts
const commitMove = useCallback(
  (move: Move, mover: MoverColor, debitMs: number): void => {
    const remainingBeforeIncrement = clockBaseRef.current[mover] - debitMs;
    if (import.meta.env.DEV && remainingBeforeIncrement <= 0) {
      throw new Error('commitMove reached with an overrun debit — caller skipped flagIfOutOfTime');
    }
    // …
```

### WR-02: The D-16 think deadline is structurally unreachable in the `blend <= 0` regime

**File:** `frontend/src/hooks/useBotGame.ts:205-212`, `:709-710`; `frontend/src/lib/engine/selectBotMove.ts:112-118`

**Issue:** `buildBotMoveDeps` wires `createDeadlineSearch({ deadlineMs, minNodes })` into
`deps.search`. But `selectBotMove`'s full-human regime returns *before* `deps.search` is ever
consulted:

```ts
if (blend <= 0) {
  const rawPolicy = await deps.policy(fen, settings.elo, side);   // no deps.search call
  const sampled = samplePolicy(rawPolicy, deps.rng);
  return sampled ?? fallbackMove(fen, deps.rng);
}
const search = deps.search ?? mctsSearch;   // only reached for blend > 0
```

So at `blend = 0` the bot has an **honest, flaggable clock with no pacing mechanism whatsoever** —
`computeThinkDeadlineMs` is computed, passed into `createDeadlineSearch`, and thrown away.
`BotGameSettings.blend` is a public field of the hook's contract, and Phase 171 surfaces it as a
user-facing slider, so this is a shipped-configuration hole, not a hypothetical. `Bots.tsx` hardcodes
`blend: 0.5` today, which is the only reason it does not bite yet. The comment at chessClock.ts:36-39
asserting that `deadlineSearch.ts` "enforces [the deadline] from OUTSIDE the frozen search core" is
therefore only true for `blend > 0`.

**Fix:** either (a) enforce the deadline outside `selectBotMove` as well — race the whole
`selectBotMove(...)` call against a `deadlineMs` timer that aborts the outer controller — or
(b) document the exemption explicitly on `BotGameSettings.blend` and in chessClock.ts's D-16 header,
and add a test that pins the behaviour so Phase 171 does not ship a blend=0 bot believing it is
clock-managed.

### WR-03: `useBotGame` silently ignores post-mount `settings` changes

**File:** `frontend/src/hooks/useBotGame.ts:220-222`, `:282-283`

**Issue:** the clock base is captured once, at first render:

```ts
const clockBaseRef = useRef<{white:number; black:number}>(freshClockBase(settings.baseSeconds));
const [whiteClockMs, setWhiteClockMs] = useState(settings.baseSeconds * 1000);
const [blackClockMs, setBlackClockMs] = useState(settings.baseSeconds * 1000);
```

`useRef` / `useState` initializers run only on mount. If a caller re-renders the hook with different
settings (exactly what a setup screen does unless it force-remounts), the clocks keep the **old**
base until someone calls `newGame()`. Worse, a changed `settings.userColor` takes effect
*immediately* in `attemptMove`'s turn gate (:482) and `commitMove`'s view-snap logic (:439) while the
board orientation and clock labels still reflect the old color — an incoherent mid-game state with no
error.

The module header advertises this hook as "the stable state+callbacks contract Phases 170
(localStorage resume) and 171 (setup screen) build on", so this is a trap laid directly in the next
phase's path.

**Fix:** either document that callers MUST remount (`<BotGame key={settingsKey} />`) and assert it,
or reset from settings in an effect:

```ts
const settingsKey = `${settings.baseSeconds}/${settings.incrementSeconds}/${settings.userColor}/${settings.botElo}/${settings.blend}`;
const prevSettingsKeyRef = useRef(settingsKey);
useEffect(() => {
  if (prevSettingsKeyRef.current === settingsKey) return;
  prevSettingsKeyRef.current = settingsKey;
  newGame();
}, [settingsKey, newGame]);
```

### WR-04: `attemptMove` / `resign` / `offerDraw` gate on the `outcome` state, not the `outcomeRef` latch

**File:** `frontend/src/hooks/useBotGame.ts:477`, `:529`, `:562`

**Issue:** Plan 09/10 deliberately introduced `outcomeRef` because (per its own doc comment,
:240-245) `finalizeGame` "is called from async continuations … and effects … that can run with a
stale render closure, so this must be a ref … not the `outcome` state (whose latest value those
callers cannot reliably observe)". `finalizeGame` (:360) and the draw-resolution effect (:547) honour
that. `attemptMove`, `resign`, and `offerDraw` do not — all three still read the `outcome` **state**.

The phase's own test suite proves the stale-closure pattern is reachable:
`useBotGame.test.ts:744` captures `const staleOfferDraw = result.current.offerDraw` before the game
ends, and it **does** get past `offerDraw`'s `if (outcome) return` guard — only the draw effect's
`outcomeRef` backstop saves the outcome. `attemptMove` has no such backstop: a stale `attemptMove`
closure would run `chess.move()` and `commitMove()` on an already-finalized game, mutating `chessRef`
and `moveHistory` **after** `finalizeGame` froze the exported PGN (:366). The board would then show a
move that is not in the stored PGN.

**Fix:** use the latch consistently with every other end-of-game consumer, and drop `outcome` from
the dep arrays (the callbacks get more stable as a bonus):

```ts
if (outcomeRef.current) return false;   // attemptMove (:477)
if (outcomeRef.current) return;         // resign (:529), offerDraw (:562)
```

### WR-05: `GameControls` stays live (Resign always enabled) after the game has ended

**File:** `frontend/src/pages/Bots.tsx:85`, `:96-116`; `frontend/src/components/bots/GameControls.tsx:50-57`

**Issue:** `showResultStrip = outcome !== null && dialogDismissed`. Between game end and the user
dismissing the result dialog, the **`GameControls` branch still renders**. `canOfferDraw` is correctly
false there, but the **Resign button has no disabled state at all** — it always renders enabled and
always opens the confirm dialog. Clicking it stacks a second Radix dialog with the result dialog;
confirming calls `game.resign()`, which no-ops on the outcome guard, leaving a dead-end interaction.
Separately, the mute toggle disappears entirely once `GameResultStrip` replaces the controls, so the
sound setting becomes unreachable after every game.

**Fix:** thread the game-over state in and disable the row:

```tsx
<GameControls
  disabled={game.outcome !== null}
  canOfferDraw={!game.drawOfferPending}
  drawCooldownActive={!game.canOfferDraw}
  …
/>
```
…and apply `disabled` to the Resign trigger inside `GameControls`. Keep the mute button reachable
after game end (either in `GameResultStrip` or hoisted out of both).

### WR-06: `tests/test_bot_pgn_clk_roundtrip.py` does not round-trip anything the frontend produces

**File:** `tests/test_bot_pgn_clk_roundtrip.py:27-35`

**Issue:** the docstring claims this test "keeps the PGN 'shape' this phase's frontend code produces
in lock-step with what the backend's STORE-02 `[%clk]`-presence gate + Termination/Result vocabulary
check requires". It does not. `_PHASE_169_SHAPED_PGN` is a **hand-typed string literal**. Nothing
links it to `botGamePgn.ts`'s `formatClockHms` / `annotateClock` / `finalizeBotPgn` / `toBackendTcStr`.
A regression on the TS side — dropping the `[TimeControl]` header, emitting `chessClock.ts`'s
`m:ss` display format instead of `h:mm:ss`, annotating only one color, changing the tc_str separator —
leaves this test green while breaking Phase 171's storage path. Meanwhile `botGamePgn.test.ts` never
sees the backend validator. There is therefore **no gate at all on the seam this file exists to
protect**.

(I verified the fixture is *currently* faithful — `chess.js@1.x`'s `pgn()` does emit the Seven Tag
Roster defaults, so today's header block is right. The problem is that nothing keeps it right.)

**Fix:** generate the fixture, don't type it. Mirror the existing `scripts/gen_*.py` +
CI-drift-check precedent, in reverse: a small node script imports `botGamePgn.ts`, plays a scripted
game, and writes a committed golden `tests/fixtures/bot_game_169.pgn`; this test reads that file, and
CI regenerates + diffs it. Minimum viable alternative: assert the exact
`\{\[%clk \d+:\d{2}:\d{2}\]\}` regex and the three header names, and add a TS-side test that asserts
the same regex against real `finalizeBotPgn` output so the two ends at least share one literal.

### WR-07: The `useIsDesktop` layout swap remounts the whole game subtree on any resize across 1024 px

**File:** `frontend/src/pages/Bots.tsx:48-61`, `:231-233`

**Issue:** `renderDesktopLayout` and `renderMobileLayout` produce **structurally different JSX
trees**, so toggling `isDesktop` unmounts and remounts `ChessBoard`, `GameControls`, and
`MoveListPanel` (they occupy different positions in the element tree). That silently discards:
`ChessBoard`'s in-progress click-to-move `selectedSquare` (ChessBoard.tsx:305-327 — a half-completed
tap-tap move on a tablet rotating to landscape), `GameControls`' `resignDialogOpen`, and the move
list's scroll position. The rest of the app solves this exact problem with Tailwind responsive
classes (`hidden sm:block` in App.tsx), which keeps a single tree.

**Fix:** render one tree and reorder with CSS (`flex-col lg:flex-row` plus `order-*`), or keep the
three children at stable tree positions and vary only their container classes. The state loss, not
the re-render cost, is the defect.

### WR-08: Hidden-tab pause is a user-controllable clock stop, and these games are stored with `[%clk]`

**File:** `frontend/src/hooks/useBotGame.ts:654-666`; `frontend/src/lib/botGamePgn.ts:60-62`

**Issue:** the CR-01 pause model (correctly implemented for the in-game path) means a user can
**freeze their own clock indefinitely** by switching tabs — think, or run the position through the
analysis board in another tab, and pay zero time. That is inherent to PLAY-04's client-side clock and
is acceptable for unrated local play *in isolation*. But Phase 171 stores these games with per-ply
`[%clk]` annotations into the user's real game history, and FlawChess's headline "Time Management
Stats" feature reads exactly those clock readings. Pausable clocks make those readings meaningless
for any bot game, and nothing in this phase flags that.

**Fix:** confirm — and pin with a test — that every time-management surface filters bot games out.
`app/repositories/query_utils.py:207-209` shows the `is_computer_game` filter exists, but nothing
asserts that the time-stats queries actually apply it. If any surface does not, either exclude bot
games there or omit `[%clk]` for a game whose clock was ever paused.

---

## Info

### IN-01: Duplicated audio-unlock guards fire `unlockAudio()` twice on the first move

**File:** `frontend/src/pages/Bots.tsx:166`, `:177-181`; `frontend/src/hooks/useBotGame.ts:274`, `:472-475`

**Issue:** `Bots.tsx` and `useBotGame` each keep their own `hasUnlockedAudioRef`, and they are
independent. The first board move fires the page's `onPointerDown` (unlock #1 → 6 × play+pause) and
then `attemptMove`'s own guard (unlock #2 → 6 more). Harmless, but wasteful and confusing.

**Fix:** move the guard into `sounds.ts` (`let unlocked = false;` at module scope, checked inside
`unlockAudio()`) and delete both refs.

### IN-02: `renderMobileLayout` / `renderDesktopLayout` take four positionally-identical params

**File:** `frontend/src/pages/Bots.tsx:124-158`, `:231-233`

**Issue:** `(botClock, userClock, board, panel)` — four bare `ReactElement`s. Swapping `botClock` and
`userClock` at either call site compiles cleanly and renders a game with the clocks inverted.

**Fix:** take a single props object (`{ botClock, userClock, board, panel }`).

### IN-03: The move-list arrow-key listener is global and swallows arrow keys inside dialogs

**File:** `frontend/src/components/bots/MoveListPanel.tsx:39-54`

**Issue:** the `window` keydown handler `preventDefault()`s ArrowLeft/ArrowRight whenever the target
is not an `INPUT`/`TEXTAREA`/`SELECT`. It stays armed while the resign-confirm dialog and the result
dialog are open (arrow-key navigation inside Radix dialog content is blocked, and the board scrolls
back behind the modal instead), and it does not guard `contenteditable`.

**Fix:** also bail on `(e.target as HTMLElement).isContentEditable`, and skip while a modal is open
(e.g. `document.querySelector('[role="dialog"][data-state="open"]')`, or lift the handler into
`Bots.tsx`, which already knows the dialog state).

### IN-04: `ClockDisplay`'s `aria-live` region only exists while `isThinking` is true

**File:** `frontend/src/components/bots/ClockDisplay.tsx:43-53`

**Issue:** an `aria-live` region must be present in the DOM *before* its content changes for screen
readers to announce it. Here the entire `<span className="sr-only" aria-live="polite">` mounts and
unmounts with `isThinking`, so most SRs will announce nothing. The copy "Bot is thinking" is also
hard-coded into a component that is otherwise parameterized by `sideLabel`.

**Fix:** keep the live region mounted and toggle its text:

```tsx
<span className="sr-only" aria-live="polite">{isThinking ? `${sideLabel} is thinking` : ''}</span>
```

### IN-05: `setMuted` silently no-ops with zero feedback when localStorage is unavailable

**File:** `frontend/src/lib/sounds.ts:125-132`

**Issue:** on a `setItem` throw (private mode, quota), `setMuted` `return`s **before** notifying
subscribers. `readMuted` also throws → `false`, so the state genuinely cannot change: the mute button
is simply dead, with no indication to the user. Internally consistent, but a broken control.

**Fix:** fall back to an in-memory mute flag that `readMuted` consults when storage is unavailable,
so the toggle still works for the session even if it cannot persist.

### IN-06: `deadlineSearch` records the node count *after* invoking the caller's `onSnapshot`

**File:** `frontend/src/lib/engine/deadlineSearch.ts:97-104`

**Issue:**

```ts
const wrappedOnSnapshot = (snapshot: EngineSnapshot): void => {
  onSnapshot(snapshot);                           // if this throws…
  latestNodesEvaluated = snapshot.nodesEvaluated; // …this never runs
  cutIfFloorMet();                                // …and the armed deadline cut never fires
};
```

A throwing `onSnapshot` permanently disarms the D-18-gated deadline cut, so the search runs to its
full node budget regardless of the clock. `selectBotMove` passes a no-op today
(`selectBotMove.ts:128`), so this is latent rather than live.

**Fix:** record the node count first, or wrap the forward: `try { onSnapshot(s) } finally { latestNodesEvaluated = s.nodesEvaluated; cutIfFloorMet(); }`.

### IN-07: `runBotTurn` captures `chessRef.current` while `commitMove` re-reads it

**File:** `frontend/src/hooks/useBotGame.ts:699` vs `:401`

**Issue:** `runBotTurn` captures `const chess = chessRef.current` at dispatch and applies the move to
that captured board (:772), while `commitMove` independently re-reads `chessRef.current` (:401) to
annotate the clock and detect the end condition. These must be the same object. Today they are — but
only because `newGame()` (which swaps `chessRef.current`) also aborts the controller, and the
continuation's `signal.aborted` check (:748) catches it. Two references to a board that must be
identical, kept in sync by a third, unrelated mechanism, is fragile.

**Fix:** pass the board explicitly (`commitMove(chess, move, mover, debitMs)`), or have `runBotTurn`
re-read `chessRef.current` after the abort check rather than capturing it at dispatch.

---

_Reviewed: 2026-07-13T15:40:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
