---
phase: 182-style-levers
reviewed: 2026-07-22T00:00:00Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - frontend/src/hooks/__tests__/useBotGame.test.ts
  - frontend/src/hooks/useBotGame.ts
  - frontend/src/lib/botDrawGate.ts
  - frontend/src/lib/engine/botStyleBundles.ts
  - frontend/src/lib/engine/botStyle.ts
  - frontend/src/lib/engine/selectBotMove.ts
  - frontend/src/lib/engine/styleOpeningLines.ts
  - frontend/src/lib/engine/__tests__/botStyleBundles.test.ts
  - frontend/src/lib/engine/__tests__/botStyle.test.ts
  - frontend/src/lib/engine/__tests__/openingBook.test.ts
  - frontend/src/lib/engine/__tests__/selectBotMove.test.ts
  - frontend/src/lib/engine/__tests__/styleOpeningLines.test.ts
  - frontend/src/lib/engine/__tests__/treeCommon.test.ts
  - frontend/src/lib/engine/treeCommon.ts
  - frontend/src/lib/engine/types.ts
  - frontend/src/lib/__tests__/botDrawGate.test.ts
  - scripts/style-lever-measurement.mjs
findings:
  critical: 2
  warning: 3
  info: 1
  total: 6
status: issues_found
---

# Phase 182: Code Review Report

**Reviewed:** 2026-07-22T00:00:00Z
**Depth:** standard
**Files Reviewed:** 16 (`useBotGame.ts` reviewed in full; the other 15 files/tests reviewed against the `0d740201..HEAD` diff)
**Status:** issues_found

## Summary

Phase 182 layers four style levers (opening-book weighting, Maia prior reweighting, `practicalScore` shaping, draw-contempt/resign policy) over the existing bot engine. The pure-transform files (`botStyle.ts`, `botStyleBundles.ts`, `styleOpeningLines.ts`, `treeCommon.ts`'s `childScoreSpread` addition, `selectBotMove.ts`'s two style hooks) are well-structured, match their doc comments, and are well covered by unit tests that verify the D-03 "undefined style is byte-identical" invariant.

Two issues undermine the `useBotGame.ts` wiring in `botDrawGate.ts`/Plan 07, though: a sign inversion in the new `contempt` draw-accept formula that makes every style's documented draw behavior run backwards, and a stale-async-continuation bug in the new resign wiring that can spuriously end an unrelated, later game. Both are provable by tracing the math/control-flow, not speculative. The existing unit tests do not catch either, because the draw-gate contempt tests assert against the same formula the implementation uses (not against the documented behavioral intent), and there is no test that exercises a `pool.grade()` resolving after `newGame()`/`resign()`.

## Critical Issues

### CR-01: `contempt`'s sign is inverted — every style's documented draw-accept behavior runs backwards

**File:** `frontend/src/lib/botDrawGate.ts:106-119` (specifically line 114), consumed via `frontend/src/lib/engine/botStyleBundles.ts:76-77, 110-111, 143-144, 178-179` and `frontend/src/hooks/useBotGame.ts:934`

**Issue:**

`wouldBotAcceptDraw` computes:

```ts
const drawValue = 0.5 - contempt;
const isNearEqual = Math.abs(rootPracticalScore - drawValue) <= DRAW_ACCEPT_SCORE_BAND;
```

`rootPracticalScore` is the bot's own-POV expected score (`evalToExpectedScore(grade.evalCp, grade.evalMate, mover)` in `useBotGame.ts:1340` — higher is better *for the bot*). The module's own doc comment, `182-CONTEXT.md`'s D-09, and every one of `botStyleBundles.ts`'s four per-style comments state the intended behavior in plain language:

- Grinder (`contempt: 0.15`, high-positive): "wants meaningfully more than dead-equal before accepting a draw" — i.e. the bot should only accept when it is *winning* comfortably.
- Wall (`contempt: -0.08`, slightly-negative): "welcomes an early draw a bit more readily than dead-equal" — i.e. the bot should accept even when it is *slightly behind*.

But with `drawValue = 0.5 - contempt`:

- Grinder: `drawValue = 0.5 - 0.15 = 0.35`. The accept band becomes `[0.30, 0.40]` — a **losing** range. Grinder, whose defining trait is "avoids draws / keeps grinding," will happily accept a draw offer specifically when it evaluates itself as *losing* (30-40% expected score), and will *refuse* a draw offer when winning or level — the exact opposite of the documented identity.
- Wall: `drawValue = 0.5 - (-0.08) = 0.58`. The accept band becomes `[0.53, 0.63]` — a **winning** range. Wall, documented as welcoming an early draw even from a mildly worse position, will now *refuse* a dead-equal (0.5) or mildly-worse offer and only accept when clearly ahead — again the opposite of the documented identity.

The bug is confirmed by tracing every consumer: `evalToExpectedScore` (`frontend/src/lib/liveFlaw.ts:88-103`) returns the mover's own expected score with higher = better for the mover, and nothing downstream re-inverts it before it reaches `wouldBotAcceptDraw`. The `182-CONTEXT.md` D-09 line documents the same `0.5 − contempt` formula, so the bug originated in the design and was carried through unmodified into the implementation, the style-bundle comments, and the unit tests — `botDrawGate.test.ts`'s contempt tests (`declines a level ... position it would otherwise accept` / `accepts a mildly-worse ... position`) assert against this same formula rather than against the documented *behavioral* intent, so they pass despite the inversion. `botStyleBundles.test.ts` only checks `GRINDER_STYLE.contempt > 0` / `WALL_STYLE.contempt < 0` (the raw field sign), never the resulting accept behavior, so it cannot catch this either.

**Fix:**

```ts
// botDrawGate.ts
export function wouldBotAcceptDraw(
  rootPracticalScore: number | null,
  chess: Chess,
  contempt = 0,
): boolean {
  if (rootPracticalScore === null) return false;

  // D-09: positive contempt raises the bar (must be ahead to accept);
  // negative contempt lowers it (accepts even when mildly behind).
  const drawValue = 0.5 + contempt;
  const isNearEqual = Math.abs(rootPracticalScore - drawValue) <= DRAW_ACCEPT_SCORE_BAND;
  if (!isNearEqual) return false;

  return queensAreOff(chess) || chess.moveNumber() >= DRAW_ACCEPT_MIN_FULLMOVE;
}
```

Also update the doc comment on `wouldBotAcceptDraw` and the four `contempt` comments in `botStyleBundles.ts` (they currently describe `0.5 - contempt` producing the correct-sounding-but-wrong direction) and the two `botDrawGate.test.ts` contempt assertions, which currently encode the inverted behavior as "expected."

---

### CR-02: Stale `pool.grade().then()` continuation can spuriously resign a later, unrelated game

**File:** `frontend/src/hooks/useBotGame.ts:1335-1374`

**Issue:**

After a bot move commits, `runBotTurn` fires a best-effort grade call and, inside its `.then()`, updates `lastRootPracticalScoreRef`, mutates `consecutiveLowScoreTurnsRef`, and — new in this phase — can call `finalizeGame({ reason: 'resignation', winner: settings.userColor })`:

```ts
pool
  .grade(fen, [uci])
  .then((gradeMap) => {
    const grade = gradeMap.get(uci);
    if (grade) {
      const score = evalToExpectedScore(grade.evalCp, grade.evalMate, mover);
      lastRootPracticalScoreRef.current = score;
      if (settings.style) {
        if (score <= settings.style.threshold) {
          consecutiveLowScoreTurnsRef.current += 1;
        } else {
          consecutiveLowScoreTurnsRef.current = 0;
        }
        const resigns = wouldBotResign(score, settings.style.threshold,
          consecutiveLowScoreTurnsRef.current, settings.style.hysteresisFloor,
          chessRef.current);
        if (resigns) {
          finalizeGame({ reason: 'resignation', winner: settings.userColor });
        }
      }
    }
  })
  .catch(() => {});
```

Unlike the search/`resolveMove()` path a few lines above (which explicitly checks `controller.signal.aborted` both in its `catch` and immediately after `Promise.all` resolves, per the D-17 two-signal contract documented in the module header), this continuation has **no cancellation or staleness check at all** — not `controller.signal.aborted`, not a captured `gameUuid`/turn-token comparison. `abortControllerRef.current?.abort()` (called by `resign()`, `newGame()`, and the next `runBotTurn`) aborts the *search*, but this `pool.grade()` promise is unaffected and can resolve arbitrarily late (it is a real Web Worker RPC).

Concrete failure sequence:
1. Bot moves; `pool.grade(fen, [uci])` is issued for the OLD position/move and is still pending.
2. User calls `newGame()` — this resets `outcomeRef.current = null`, `consecutiveLowScoreTurnsRef.current = 0`, `lastRootPracticalScoreRef.current = null`, mints a new `gameUuid`, and replaces `chessRef.current` with a fresh `Chess()`. The user starts playing the new game.
3. The stale grade from step 1 finally resolves. Its `.then()` callback still runs against the *current* refs: it sets `lastRootPracticalScoreRef.current` to a score computed for a completely different (discarded) position — violating the sentinel contract this same file goes to great lengths to document elsewhere ("the bot never accepts/resigns off a score it did not compute *this game*"). If `settings.style` is set and the new game has already progressed past `RESIGN_MIN_FULLMOVE` (20) by the time the stale promise resolves (plausible under worker load, or a fast/aggressive player), `wouldBotResign` can return `true` against `chessRef.current` (the *new* game's board) and `finalizeGame({ reason: 'resignation', winner: settings.userColor })` fires — ending the new, unrelated, in-progress game with a bogus resignation attributed to stale data from a prior game.

Even without a resign, the silent corruption of `lastRootPracticalScoreRef`/`consecutiveLowScoreTurnsRef` for the new game (from an old game's grade) is itself a violation of the sentinel design this file repeatedly documents as load-bearing (see the extensive `lastRootPracticalScoreRef` doc comment a few hundred lines above).

**Fix:** capture the turn's `AbortController`/`gameUuid` and bail out of the `.then()` if it no longer matches current state, mirroring the `resolveMove()` guard:

```ts
const turnController = controller; // captured at dispatch time, same as resolveMove() above
pool
  .grade(fen, [uci])
  .then((gradeMap) => {
    if (turnController.signal.aborted) return; // stale: turn was cancelled/superseded
    const grade = gradeMap.get(uci);
    // ...unchanged...
  })
  .catch(() => {});
```

Note this alone is not quite sufficient: `newGame()` does not call `abortControllerRef.current?.abort()` for the *dispatched* turn's controller before the next bot turn creates a fresh one — check that `newGame()`'s existing `abortControllerRef.current?.abort()` line actually aborts the controller this closure captured (it should, since `runBotTurn` stores every fresh controller in `abortControllerRef.current` and `newGame()` reads that same ref) — but verify with a regression test that plays a game, leaves a `pool.grade()` promise pending, calls `newGame()`, resolves the stale promise, and asserts the new game's `outcome`/`lastRootPracticalScoreRef`-derived behavior is untouched.

## Warnings

### WR-01: Duplicated 11-line comment block in `commitMove`

**File:** `frontend/src/hooks/useBotGame.ts:805-826`

**Issue:** The "Phase 170 D-01 (primary write path)..." comment explaining the `writeSnapshot` guard is written twice, verbatim, back to back (lines 805-815 and 816-826), before the single `if (live && !outcomeRef.current) { writeSnapshot(...); }` it documents. This predates Phase 182 (not touched by the `0d740201..HEAD` diff), but it sits inside a function this phase's review scope covers in full and is a clear copy-paste artifact that degrades readability — a future editor updating the guard's rationale is likely to only fix one copy, leaving the other stale.

**Fix:** Delete one of the two identical comment blocks.

### WR-02: Misleading `scoreBonus` doc comments — it never actually reaches the resign/draw-gate score

**File:** `frontend/src/lib/engine/botStyleBundles.ts:72, 106, 139, 174` (the `scoreBonus` doc comment on all four styles, e.g. Attacker's: `"...only the resign/draw-gate consumers of practicalScore feel it"`)

**Issue:** All four `scoreBonus` comments claim the flat additive bonus is invisible to move *ranking* but is felt by "the resign/draw-gate consumers of practicalScore." In fact, `wouldBotAcceptDraw`/`wouldBotResign` never see `applyStyleScoreShaping`'s output at all: `useBotGame.ts`'s `runBotTurn` computes the resign/draw score from an entirely independent, freshly-issued `pool.grade(fen, [uci])` call (`useBotGame.ts:1335-1340`) on the move that was actually played, not from the search's shaped `RankedLine.practicalScore`. `selectBotMove` itself discards its `RankedLine[]` after picking a UCI move — the shaped scores never leave that function. So `scoreBonus`/`varianceBonus` affect *only* which move gets picked among near-tied search candidates; they have zero effect on the draw-accept/resign decision. This is a documentation-only defect, but it will mislead the next person tuning these constants (e.g. Phase 184's strength calibration) into believing a `scoreBonus` change shifts resign/draw behavior when it does not.

**Fix:** Correct the four comments to state that `scoreBonus`/`varianceBonus` affect move selection only, and that the resign/draw-gate score comes from a separate post-commit grade call.

### WR-03: `RESIGN_HYSTERESIS_TURNS` is exported but never consumed as a real default

**File:** `frontend/src/lib/botDrawGate.ts:45-52`

**Issue:** `RESIGN_HYSTERESIS_TURNS` is documented as "the shared default when a style doesn't override it," but no production call site ever reads it — `wouldBotResign` always takes an explicit `hysteresisFloor` argument, and `useBotGame.ts` always sources it from `settings.style.hysteresisFloor` inside the `if (settings.style)` guard (unstyled games never call `wouldBotResign` at all, per D-03). The only references outside its own declaration are a comment in `botStyleBundles.ts:80` and test assertions in `botDrawGate.test.ts`. It is effectively dead/vestigial production code that documents an intent ("shared default") the current wiring never realizes.

**Fix:** Either wire it in as an actual fallback (e.g. `settings.style.hysteresisFloor ?? RESIGN_HYSTERESIS_TURNS` at the `useBotGame.ts` call site, if `hysteresisFloor` is ever meant to be optional on `BotStyleParams`), or remove the "shared default" framing from its doc comment since `BotStyleParams.hysteresisFloor` is a required field on every shipped bundle and there is currently no code path that would ever fall back to it.

## Info

### IN-01: `styleNameFor` re-derives the style name via `Object.values` linear scan on every book ply

**File:** `frontend/src/hooks/useBotGame.ts:316-320`

**Issue:** `resolveBookMove` (called on every in-book ply) calls `styleNameFor(style)`, which does a linear `Object.keys(BOT_STYLE_BUNDLES).find(...)` reference-equality scan. With only 4 bundles this is negligible in practice and out of this review's stated performance scope, but it is a slightly awkward "reverse lookup by identity" pattern worth a passing note: if `BOT_STYLE_BUNDLES` grows substantially (Phase 183's persona registry), a direct `Style` field threaded alongside `BotStyleParams` (or a `WeakMap<BotStyleParams, Style>`) would avoid repeating the scan and remove the "must be reference-equal to a bundle singleton" fragility documented in the function's own comment (a cloned/spread style object silently loses its curated book).

**Fix:** No action required for this phase; flagged for awareness ahead of Phase 183's persona registry, which the function's own doc comment already anticipates.

## Fix Log

All Critical and Warning findings were fixed (Info finding IN-01 was intentionally skipped per scope — no action required for this phase, per its own **Fix:** note above).

| Finding | Status | Commit | Notes |
|---|---|---|---|
| CR-01 | fixed | `606141df`, `c1f7bb55` | `drawValue` corrected from `0.5 - contempt` to `0.5 + contempt` in `botDrawGate.ts`; updated `botDrawGate.test.ts`'s two contempt tests to assert documented behavioral intent (not the formula); synced the two `botStyleBundles.ts` contempt comments (Grinder/Wall) that cited the old formula. Revert-proofed: reintroducing the inverted sign made both updated tests fail before restoring the fix. |
| CR-02 | fixed: requires human verification | `f2450bf5` | Added `controller.signal.aborted` staleness guard to the `pool.grade().then()` continuation in `useBotGame.ts`, mirroring the `resolveMove()` path's D-17 two-signal contract. Added a regression test (`useBotGame.test.ts`, "a stale pool.grade() continuation resolving after newGame() does not mutate resign state for the new game (CR-02)") that leaves a grade promise pending across a `newGame()` call and proves the stale resolution is a no-op. Revert-proofed: removing the guard reproduced the exact spurious-resignation failure. Flagged for human verification per this async/control-flow class of fix (not purely mechanical), though both the trace and the regression test support correctness. |
| WR-01 | fixed | `1b27e755` | Deduplicated the copy-pasted 11-line "Phase 170 D-01" comment block in `commitMove` (`useBotGame.ts`). |
| WR-02 | fixed | `1806521a` | Corrected all four `scoreBonus` doc comments in `botStyleBundles.ts` to state they affect move selection only — the resign/draw-gate score comes from an independent post-commit `pool.grade()` call in `useBotGame.ts`, not from `applyStyleScoreShaping`'s output. |
| WR-03 | fixed | `f811f7e5` | Reframed `RESIGN_HYSTERESIS_TURNS`'s doc comment (and its 3 references in `botStyleBundles.ts`) from "shared default" to a hand-tuned reference magnitude — `BotStyleParams.hysteresisFloor` is a required field every shipped bundle sets explicitly, so no runtime fallback exists to wire it into. No behavior change (there was nothing to change behaviorally). |
| IN-01 | no_change_needed | — | Reviewer's own **Fix:** note states "No action required for this phase"; flagged for awareness ahead of Phase 183's persona registry. Out of `critical_warning` fix scope. |

Verification after all fixes: `npx tsc -b --noEmit` (0 errors), `npx vitest run src/lib/__tests__/botDrawGate.test.ts src/hooks/__tests__/useBotGame.test.ts src/lib/engine/` (349 tests, all passing), `npm run lint` (0 errors — 3 pre-existing warnings in unrelated `coverage/` generated files only).

---

_Reviewed: 2026-07-22T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Fixed: 2026-07-22T01:05:00Z_
_Fixer: Claude (gsd-code-fixer)_
