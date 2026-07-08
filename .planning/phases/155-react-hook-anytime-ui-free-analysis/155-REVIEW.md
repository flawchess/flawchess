---
phase: 155-react-hook-anytime-ui-free-analysis
reviewed: 2026-07-06T21:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - frontend/src/hooks/useFlawChessEngine.ts
  - frontend/src/components/analysis/FlawChessEngineLines.tsx
  - frontend/src/components/analysis/EngineLines.tsx
  - frontend/src/components/analysis/MaiaHumanPanel.tsx
  - frontend/src/pages/Analysis.tsx
  - frontend/src/lib/liveFlaw.ts
  - frontend/src/lib/theme.ts
  - frontend/src/components/ui/switch.tsx
findings:
  critical: 1
  warning: 4
  info: 4
  total: 9
status: resolved
resolution: Critical (CR-01) and handoff Warnings (WR-01/02/03/04) fixed in commits 9b416032, d9156866, 18b5737d, 776fb5f4. Info-level nits (IN-01..04) deferred as cosmetic. See 155-REVIEW-FIX.md.
---

# Phase 155: Code Review Report

**Reviewed:** 2026-07-06T21:00:00Z
**Depth:** standard
**Files Reviewed:** 8
**Status:** issues_found

## Summary

This phase wires `useFlawChessEngine` (the live MCTS search hook) into `/analysis`,
adds the `FlawChessEngineLines` card, a hand-rolled `Switch` primitive, an
inverse-sigmoid score converter, and a 3-toggle header refactor with eval-bar
precedence. The math (`expectedScoreToWhitePovCp`) is sound and the throttle/abort
mechanics in the hook are individually well-reasoned, but the interaction between
the new **default-on FlawChess Engine** and the **existing Stockfish card** was not
fully worked through: in the app's actual default state (both switches ON, which is
what every first-time visitor sees), the Stockfish engine card — on both desktop and
mobile — renders completely blank, with no lines, no skeleton, and no "off" message.
This is the standout finding below (Critical). A cluster of secondary issues follows
from the same root cause: `bestSan`/`engineTopLines` (feeding an existing 151.1
feature) silently go empty in the same default state, and the right eval bar ignores
the Stockfish toggle entirely once FlawChess Engine is on. The hook itself has a
missing `.catch` on its `mctsSearch(...).then(...)` chain (Warning) and an
abort-on-disable gap that is currently masked by how `Analysis.tsx` happens to wire
`fen`/`enabled` together, but would resurface for any other caller. No security
issues were found — all engine-derived strings are rendered as React children
(auto-escaped), and there is no user input reaching PGN/FEN parsing beyond the
already-guarded `?fen=` param.

## Critical Issues

### CR-01: Stockfish engine card renders completely blank in the app's default state (both switches ON)

**File:** `frontend/src/pages/Analysis.tsx:1695-1713` (desktop `analysis-engine-card` body) and `frontend/src/pages/Analysis.tsx:1459-1473` (mobile `analysis-engine-lines-mobile` strip)

**Issue:** `engineEnabled` and `flawChessEnabled` both default to `true` (lines 345,
350) — this is the state every user lands in. Under D-04's POOL-04 handoff,
`useStockfishEngine` is suppressed whenever `flawChessEnabled` is true
(`enabled: engineEnabled && !flawChessEnabled`, line ~415-417), so `engine.isReady`
never becomes `true` and `engine.pvLines`/`engine.isAnalyzing` stay at their empty
defaults for as long as FlawChess Engine is on.

The "Rule 1 bug fix" (`engineLoading = engineEnabled && !flawChessEnabled &&
!engine.isReady`, line 610) correctly stops the loading skeleton from spinning
forever, but nothing was added to cover the resulting state. The desktop card body:

```tsx
{engineLoading ? (
  <EngineLinesSkeleton testId="analysis-engine-loading" />
) : !engineEnabled ? (
  <div className="flex h-full items-center px-2 text-sm text-muted-foreground">
    Engine off
  </div>
) : (
  <EngineLines pvLines={engine.pvLines} isAnalyzing={engine.isAnalyzing} ... />
)}
```

only shows "Engine off" when the user has *explicitly* toggled the Stockfish switch
off (`!engineEnabled`). When the switch is still ON but the search is *silently
suppressed* by FlawChess Engine (the default state), neither branch fires:
`engineLoading` is `false` (by design) and `!engineEnabled` is `false` (the switch
is visually ON) — so it falls through to `<EngineLines pvLines={[]}
isAnalyzing={false} .../>`, which renders nothing. The mobile strip has the exact
same gap (no `!engineEnabled` branch at all there, so the same empty-render path
applies). The net effect: every new visitor to `/analysis` sees a "Stockfish 18" card
with its switch ON and a permanently blank body — the core engine-analysis feature
appears broken with no indication that it has been intentionally handed off to the
FlawChess Engine.

This is confirmed by the phase's own test suite: `Analysis.test.tsx`'s "shows
engine-loading chrome while isReady=false" test explicitly clicks the FlawChess
toggle off *before* asserting the skeleton appears (`fireEvent.click(...
'btn-analysis-flawchess-toggle')`, line 228), and no test asserts what the Stockfish
card body actually contains in the untouched default state.

**Fix:** Add a third branch for the suppressed-but-not-user-disabled case, e.g.:

```tsx
{engineLoading ? (
  <EngineLinesSkeleton testId="analysis-engine-loading" />
) : !engineEnabled ? (
  <div className="flex h-full items-center px-2 text-sm text-muted-foreground">
    Engine off
  </div>
) : flawChessEnabled ? (
  <div className="flex h-full items-center px-2 text-sm text-muted-foreground">
    Merged into FlawChess Engine
  </div>
) : (
  <EngineLines pvLines={engine.pvLines} isAnalyzing={engine.isAnalyzing} ... />
)}
```

and mirror the same branch in the mobile strip at line 1459-1473.

## Warnings

### WR-01: `mctsSearch(...).then(...)` has no `.catch` — unhandled rejection, `isSearching` can get stuck `true` forever

**File:** `frontend/src/hooks/useFlawChessEngine.ts:222-233`

**Issue:**

```ts
void mctsSearch(debouncedFen, budget, providers, handleSnapshot, controller.signal).then(
  (finalSnapshot) => {
    if (controller.signal.aborted) return;
    ...
    setIsSearching(false);
  },
);
```

`setIsSearching(true)` is set unconditionally right before this call (line 221), but
`setIsSearching(false)` only runs inside the fulfillment handler. If `mctsSearch`
rejects for any reason (a worker crash, `pool.grade()`/`queue.policy()` throwing
after the pool/queue were terminated by a concurrent state change, or any bug in the
frozen search core), the rejection is never caught: it becomes an unhandled promise
rejection (never reaches Sentry via `Sentry.captureException`, per CLAUDE.md's
"manual fetch/async calls ... MUST call Sentry.captureException" rule), and
`isSearching` is left `true` indefinitely — the FlawChess card's skeleton spins
forever until the next FEN navigation restarts a fresh search. There is no test
covering this path (the test file's `mockMctsSearch` default implementation never
resolves *or* rejects — `new Promise<EngineSnapshot>(() => {})` — so a rejection is
never exercised).

**Fix:**

```ts
void mctsSearch(debouncedFen, budget, providers, handleSnapshot, controller.signal)
  .then((finalSnapshot) => {
    if (controller.signal.aborted) return;
    ...
    setSnapshot(finalSnapshot);
    setIsSearching(false);
  })
  .catch((err) => {
    if (controller.signal.aborted) return;
    Sentry.captureException(err, { tags: { source: 'flawchess-engine' } });
    setIsSearching(false);
  });
```

### WR-02: Search-trigger effect never aborts its own `AbortController` when `enabled` transitions to `false` without a FEN change

**File:** `frontend/src/hooks/useFlawChessEngine.ts:183-234` (compare to the unmount effect at `241-247`)

**Issue:** The provider-lifecycle effect (lines 113-128) tears down the pool/queue
and resets `isReady`/`isSearching` when `enabled` flips to `false`, but the
search-trigger effect that owns `abortControllerRef` (lines 183-234) has **no
cleanup function** of its own — `abortControllerRef.current?.abort()` is only
called at the *top* of the guarded effect body (line 195), which is skipped entirely
when the guard `if (!debouncedFen || !enabled || !pool || !queue) return;` (line
186) fails. So disabling the engine mid-search leaves the in-flight
`AbortController` un-aborted; the abort only actually happens the *next* time the
effect re-runs with the guard passing again (e.g., when re-enabled). Between those
two points, a stale `onSnapshot`/final-`.then` callback from the disabled search can
still fire and call `setSnapshot`/`setIsSearching` since `controller.signal.aborted`
is still `false`.

In the current `Analysis.tsx` wiring this is largely masked because `fen` is passed
as `flawChessEnabled ? position : null` — disabling the switch also nulls the FEN in
the same render, which independently clears `snapshot` via the debounced-FEN effect
(lines 133-153). But this is incidental to the caller, not a guarantee the hook
itself provides: any other caller that toggles `enabled` off while leaving `fen`
non-null (e.g., a "pause without losing position" UI) would hit the stale-callback
window directly, and a future refactor of `Analysis.tsx`'s own wiring could
reintroduce it silently.

**Fix:** Move the abort call out of the guarded branch, e.g. add an effect cleanup
that always aborts the current controller regardless of whether the next run's
guard passes:

```ts
useEffect(() => {
  const pool = poolRef.current;
  const queue = queueRef.current;
  if (!debouncedFen || !enabled || !pool || !queue) return;
  ...
}, [debouncedFen, enabled, elo, handleSnapshot]);

// separate effect, or a cleanup on the above:
useEffect(() => {
  return () => abortControllerRef.current?.abort();
}, [debouncedFen, enabled]);
```

### WR-03: Right eval bar ("SF" cap) ignores the Stockfish toggle entirely while FlawChess Engine is enabled

**File:** `frontend/src/pages/Analysis.tsx:1152-1154`

**Issue:**

```ts
const rightEvalBarEvalCp = flawChessEnabled ? (topLine?.objectiveEvalCp ?? null) : gameOverlay.evalCp;
const rightEvalBarEvalMate = flawChessEnabled ? null : gameOverlay.evalMate;
const rightEvalBarDepth = flawChessEnabled ? 0 : gameOverlay.evalDepth;
```

These derivations branch solely on `flawChessEnabled` — `engineEnabled` never enters
the formula. So if a user explicitly turns the Stockfish switch OFF while leaving
FlawChess Engine ON (a perfectly reasonable thing to do given both are independent
toggles per D-03), the right eval bar keeps showing data — still capped "SF" (line
1266-1270 `evalBarCap('SF', STOCKFISH_ACCENT)` is unconditional) — sourced from the
FlawChess Engine's internal grading pool. Turning off "Stockfish" has zero visible
effect on the bar labeled "SF". This is likely to read as a bug to anyone testing
the three toggles independently, even though it's a consequence of the (otherwise
reasonable) POOL-04 handoff design.

**Fix:** Either gate the cap/label on `engineEnabled` too (e.g. show a neutral/off
state on the right bar when `!engineEnabled`, regardless of `flawChessEnabled`), or
explicitly document in the UI (tooltip/caption) that the "SF" bar reflects
FlawChess Engine's Stockfish-backed objective eval whenever FlawChess Engine is on.

### WR-04: `bestSan`/`engineTopLines` silently go empty in the default state, degrading the existing Moves-by-Rating "best move" feature

**File:** `frontend/src/pages/Analysis.tsx:633-650`

**Issue:** `bestSan` and `engineTopLines` (feeding `MaiaHumanPanel`'s
`MovesByRatingChart` best-move emphasis and the "engine-reference" tooltip header
added in Phase 151.1) are derived exclusively from `engine.pvLines`:

```ts
const bestSan = useMemo(
  () => bestSanFromPv(position, engine.pvLines[0]?.moves[0] ?? null),
  [position, engine.pvLines],
);
...
for (const line of engine.pvLines.slice(0, 2)) { ... }
```

Because `engine` (the standalone `useStockfishEngine`) is suppressed whenever
`flawChessEnabled` is true (the default), `engine.pvLines` is permanently `[]` in
that state, so `bestSan` is always `null` and `engineTopLines` is always `[]`. The
151.1 "best move" dark-green highlight on the Moves-by-Rating chart and its
engine-reference tooltip silently stop working for every default session, with no
fallback wired to `flawChessEngine.rankedLines`/`topLine`, and this isn't called out
in the plan's own "Known Gaps" section (which only lists the missing error state and
`EvalBar`'s generic aria-label).

**Fix:** When `flawChessEnabled` is true, derive `bestSan`/`engineTopLines` from
`flawChessEngine.rankedLines` (e.g. `topLine.rootMove`/`modalPath[0]` converted to
SAN, and the top 2 `rankedLines` as `engineTopLines`) instead of leaving them
permanently empty; or explicitly document the tradeoff if it's accepted.

## Info

### IN-01: Orphaned/duplicated docstring left above the new function in `liveFlaw.ts`

**File:** `frontend/src/lib/liveFlaw.ts:31-52`

**Issue:** The pre-existing docstring for `evalToExpectedScore` (lines 31-35: "Convert
a white-POV engine eval... Returns 0.5 (neutral) when no eval is available.") was not
moved when `expectedScoreToWhitePovCp` was inserted directly below it. The result is
two stacked block comments immediately above `expectedScoreToWhitePovCp` (lines
31-35 and 36-45), and `evalToExpectedScore` itself (line 53) is now left with no
docstring at all. This is confusing to a reader scanning top-to-bottom (the first
comment describes a function two declarations away) and violates the file's own
documentation quality.

**Fix:** Move the original `evalToExpectedScore` docstring back to sit directly
above its own function declaration (line 53), leaving only
`expectedScoreToWhitePovCp`'s own docstring (lines 36-45) above the new function.

### IN-02: `Switch`'s `checked` and `style` props use inconsistent fallback logic in `MaiaHumanPanel`

**File:** `frontend/src/components/analysis/MaiaHumanPanel.tsx:125-134`

**Issue:**

```tsx
const toggleSwitch = showToggle && (
  <Switch
    checked={enabled ?? true}
    onCheckedChange={onToggleEnabled}
    ...
    style={enabled ? { backgroundColor: MAIA_ACCENT } : undefined}
  />
);
```

`checked` defaults an `undefined` `enabled` to `true`, but `style` does not apply the
same fallback (`enabled ? ... : undefined` — `undefined` is falsy, so no accent is
applied). If a caller ever supplies `onToggleEnabled` without `enabled` (currently no
caller does — `Analysis.tsx` always passes both), the switch would render visually
"on" (thumb translated via Radix's `data-state=checked`) but without the violet
accent fill, falling back to the primitive's default `bg-primary`. Low risk today,
but a latent inconsistency worth aligning (`style={(enabled ?? true) ? {...} :
undefined}`) for the next caller that doesn't pass both props together.

### IN-03: Pre-existing no-op ternary left untouched in a file this phase modified

**File:** `frontend/src/components/analysis/EngineLines.tsx:297`

**Issue:** `const label = moveLabel(startPly, lineIndex === 0 ? moveIndex : moveIndex);`
— both ternary branches are identical (`moveIndex`), so the condition has no effect.
This predates Phase 155 (the 155-03 plan summary explicitly notes it was
deliberately *not* reproduced in the new `FlawChessEngineLines.tsx`), but since
`EngineLines.tsx` is a modified file in this phase's diff, it's worth cleaning up
while the file is open rather than leaving confusing dead conditional logic for the
next reader.

**Fix:** `const label = moveLabel(startPly, moveIndex);`

### IN-04: ELO slider changes bypass the FEN debounce entirely, restarting the search on every tick

**File:** `frontend/src/hooks/useFlawChessEngine.ts:183-234` (effect dependency array at line 234)

**Issue:** The search-trigger effect depends on `elo` directly with no debouncing
(`[debouncedFen, enabled, elo, handleSnapshot]`), unlike FEN navigation which goes
through the adaptive `RAPID_STEP_DEBOUNCE_MS` debounce (lines 130-153) specifically
to avoid restarting the search on rapid input. Every ELO-slider step (the ladder is
discrete, ~20 rungs from 600-2600) immediately aborts the in-flight search and
starts a new one via `budget.elo = { w: elo, b: elo }`. Impact is bounded (a full
drag triggers at most ~20 restarts, not a continuous flood), but it's an asymmetry
with the FEN-navigation debounce pattern the hook otherwise follows carefully, and
worth a similar coalescing window if slider-drag responsiveness becomes a UAT
concern.

---

_Reviewed: 2026-07-06T21:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
