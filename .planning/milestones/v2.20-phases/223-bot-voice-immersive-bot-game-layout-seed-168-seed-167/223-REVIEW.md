---
phase: 223-bot-voice-immersive-bot-game-layout-seed-168-seed-167
reviewed: 2026-09-16T00:00:00Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - frontend/src/App.tsx
  - frontend/src/components/board/BoardControls.tsx
  - frontend/src/components/board/MaterialDisplay.tsx
  - frontend/src/components/board/PlayerBar.tsx
  - frontend/src/components/bots/BotDrawOfferActions.tsx
  - frontend/src/components/bots/BotGameBubble.tsx
  - frontend/src/components/bots/BotGameDesktopLayout.tsx
  - frontend/src/components/bots/BotGameMobileBar.tsx
  - frontend/src/components/bots/BotGameMobileLayout.tsx
  - frontend/src/components/bots/GameControls.tsx
  - frontend/src/components/bots/GameResultDialog.tsx
  - frontend/src/components/bots/PersonaGrid.tsx
  - frontend/src/components/bots/botPlayerRow.ts
  - frontend/src/hooks/useBotGame.ts
  - frontend/src/hooks/useBotGameEngineDispatch.ts
  - frontend/src/hooks/useBotGameMoves.ts
  - frontend/src/hooks/useBotGameVoice.ts
  - frontend/src/hooks/useWinCelebrationHold.ts
  - frontend/src/lib/botGameCopy.ts
  - frontend/src/lib/botLineTrigger.ts
  - frontend/src/lib/chessClock.ts
  - frontend/src/lib/confetti.ts
  - frontend/src/lib/mobileBoardControls.ts
  - frontend/src/lib/sounds.ts
  - frontend/src/lib/theme.ts
  - frontend/src/lib/trainBotCopy.ts
  - frontend/src/pages/Bots.tsx
findings:
  critical: 1
  warning: 2
  info: 0
  total: 3
status: issues_found
---

# Phase 223: Code Review Report

**Reviewed:** 2026-09-16
**Depth:** standard
**Files Reviewed:** 27
**Status:** issues_found

## Summary

Reviewed the full bot-voice / immersive bot-game-layout phase: the swing/regret
resolver (`botLineTrigger.ts`), the voice sub-hook (`useBotGameVoice.ts`), the
engine-dispatch sub-hook's ply-latching fix (`useBotGameEngineDispatch.ts`),
the new shared `PlayerBar`/`botPlayerRow` row resolver used by both bot-game
layouts, and the desktop/mobile layout + result-dialog components.

Orientation logic in `botPlayerRow.ts` (top/bottom row assignment vs.
`flipped`), the clock-badge colour/text-contrast logic in `PlayerBar.tsx`, and
the `BOT_LINE_PAIR_PLY_SPAN` ply-adjacency latching in
`useBotGameEngineDispatch.ts`/`useBotGameVoice.ts` all check out — no
alignment or orientation defects found there.

One genuine correctness bug was found in the swing/regret resolver: the
`BOT_LINE_SWING_SPACING_MOVES` pacing gate can silently swallow a live regret
latch's resolution (`'got-away'`/`'nice-move'`), even though the module's own
documentation states this resolution "always produces a key" and the caller
relies on that guarantee to safely clear the latch. Two lower-severity
robustness/consistency gaps are also documented below.

## Critical Issues

### CR-01 (FIXED in the follow-up commit, see below): Regret-latch resolution can be silently dropped by the swing pacing gate, contradicting the documented invariant

**File:** `frontend/src/lib/botLineTrigger.ts:136-150, 214-225`
**File:** `frontend/src/hooks/useBotGameVoice.ts:262-279`

**Issue:**

`resolveSwingKey`'s own doc comment (`botLineTrigger.ts:136-141`) states:

> A live regret latch (`recoveryCp !== null`) is resolved FIRST and always
> produces a key, because the caller clears the latch on this same grade
> either way: leaving it to fall through would drop the bot's own blunder on
> the floor unremarked.

And indeed `resolveSwingKey` always returns a non-null key when `recoveryCp
!== null`:

```ts
function resolveSwingKey(swingCp: number | null, recoveryCp: number | null): BotLineKey | null {
  if (recoveryCp !== null) {
    return recoveryCp >= BOT_LINE_SWING_THRESHOLD_CP ? 'got-away' : 'nice-move';
  }
  ...
}
```

But `resolveBotLine`, the only caller, applies the `BOT_LINE_SWING_SPACING_MOVES`
pacing gate to *that same key* without distinguishing "a positive swing that's
merely being rate-limited" from "a regret-latch resolution that must always
speak":

```ts
export function resolveBotLine(input: ResolveBotLineInput): BotLineKey | null {
  if (input.outcomeKind !== null) return resolveOutcomeKey(input.outcomeKind);
  if (input.drawOfferLive) return 'draw-offer';
  const swingKey = resolveSwingKey(input.swingCp, input.recoveryCp);
  if (swingKey !== null) {
    return input.botMovesSinceLastLine >= BOT_LINE_SWING_SPACING_MOVES ? swingKey : null;
  }
  ...
}
```

So if a regret latch resolves (`recoveryCp !== null`) while `botMovesSinceLastLine
< BOT_LINE_SWING_SPACING_MOVES` (2) — e.g. a mood line ('first-capture'/
'game-start') or 'punished-mistake' reset the counter to 0 on the bot's *prior*
move, and the very next bot move is the one that resolves the latch —
`resolveBotLine` returns `null` for this grading.

Meanwhile, the caller (`useBotGameVoice.onBotMoveGraded`) clears the latch
based on `recoveryCp !== null` alone, **not** on whether `resolveBotLine`
actually returned a line:

```ts
const line = resolveBotLine({ ... swingCp, recoveryCp, ... });
if (recoveryCp !== null) regretCpRef.current = null;   // <-- unconditional
if (isRegretSwing(swingCp)) regretCpRef.current = cp;
if (line !== null) {
  setBotLine(line);
  botMovesSinceLastLineRef.current = 0;
  ...
}
```

Result: the bot's own acknowledged blunder ("got away" / "nice move") is
silently and permanently dropped — never spoken — exactly the failure mode
the module's own comment says cannot happen ("dropped on the floor
unremarked"). This is reachable in normal play any time a mood/punish line
fired 0-1 bot moves before the regret-resolving grade lands, which the
phase's own calibration notes (~3-4 in-game lines per game, `BOT_LINE_MIN_SPACING_MOVES
= 3` reset on every mood line) make a realistic, not merely theoretical,
occurrence.

**Fix:** exempt the regret-latch resolution from the spacing gate, matching
the documented "always produces a key" contract — only gate the plain
positive-swing (`earned-tease`) case:

```ts
export function resolveBotLine(input: ResolveBotLineInput): BotLineKey | null {
  if (input.outcomeKind !== null) return resolveOutcomeKey(input.outcomeKind);
  if (input.drawOfferLive) return 'draw-offer';
  if (input.recoveryCp !== null) {
    // A live regret latch always resolves — never rate-limited, the caller
    // clears the latch unconditionally on this grade either way.
    return resolveSwingKey(input.swingCp, input.recoveryCp);
  }
  const swingKey = resolveSwingKey(input.swingCp, input.recoveryCp);
  if (swingKey !== null) {
    return input.botMovesSinceLastLine >= BOT_LINE_SWING_SPACING_MOVES ? swingKey : null;
  }
  if (input.botMovesSinceLastLine < BOT_LINE_MIN_SPACING_MOVES) return null;
  if (input.firstCapturePending) return 'first-capture';
  if (input.gameStartPending) return 'game-start';
  return null;
}
```

(Alternatively, gate the caller's `regretCpRef.current = null` clear on
`line !== null` instead — but that reintroduces the "stale latch fires late"
risk the current unconditional clear was presumably written to avoid, so
fixing the resolver side is the safer change.)

## Warnings

### WR-01 (ACCEPTED, not fixed): `useBotGame.newGame()` does not reset the Phase 223 voice-hook state

**File:** `frontend/src/hooks/useBotGame.ts:631-689`
**File:** `frontend/src/hooks/useBotGameVoice.ts:55-71, 108-165`

**Issue:** `newGame()` resets every other sub-hook's per-game state
(`resetClock()`, `resetDrawOfferState()`, `hasLeftBookRef`, `hasFiredLowTimeRef`,
`lastRootPracticalScoreRef`, `outcomeRef`, `movesSinceLastDecline`, etc.) but
never touches `useBotGameVoice`'s internal refs
(`gameStartLatchRef`, `outcomeLineLatchRef`, `regretCpRef`,
`lastGradedPlyRef`/`lastGradedCpRef`, `firstCaptureSeenRef`/
`firstCaptureAnnouncedRef`, `botMovesSinceLastLineRef`) or the `botLine`
state itself — `useBotGameVoice` exposes no reset function at all.

In production this is currently masked because the only caller of "new game"
(`BotsPage.handleStart`/`handleNewGame` in `Bots.tsx`) always bumps
`boot.nonce` and fully remounts `<BotsGame key={boot.nonce}>`, so a fresh
`useBotGameVoice` instance is created each time — `game.newGame()` itself is
documented as having "NO production caller" today. But it is retained
specifically as tested public hook API "for a future in-place 'rematch'
caller" (see the comment in `Bots.tsx` around `game.newGame`). If such a
caller is ever wired up without remounting the component, the bubble would
carry over stale state into the new game: `outcomeLineLatchRef.current`
already `true` would permanently suppress the new game's own terminal line,
`gameStartLatchRef` would suppress the new greeting, and a stale
`regretCpRef`/`lastGradedPlyRef` could produce a nonsensical swing on the
very first graded move of the new game.

**Fix:** have `useBotGameVoice` return a `resetVoiceState()` callback
(clearing all its refs and `botLine`), and call it from `useBotGame.newGame()`
alongside `resetClock()`/`resetDrawOfferState()`.

### WR-02 (FIXED in the follow-up commit): `BotGameMobileBar`'s resign-dialog Cancel button has no `data-testid`

**File:** `frontend/src/components/bots/BotGameMobileBar.tsx:88-94`

**Issue:** `frontend/CLAUDE.md`'s Browser Automation Rules require
`data-testid` on "every interactive element — buttons, links, inputs,
select triggers". The new `BotGameMobileBar` (added this phase) copies its
resign-confirm dialog from `GameControls.tsx`, but the copy carries over the
same gap: the `Cancel` button in the dialog has no `data-testid`, forcing
any automation/e2e test that needs to dismiss the dialog to fall back to
text matching instead of a stable selector.

```tsx
<Button
  variant="outline"
  className={BOT_ACTION_BUTTON_CLASS}
  onClick={() => setResignDialogOpen(false)}
>
  Cancel
</Button>
```

**Fix:** add `data-testid="board-btn-resign-cancel"` (or similar) to this
button in `BotGameMobileBar.tsx`; consider fixing the same gap in
`GameControls.tsx`'s equivalent Cancel button while in the area.

---

_Reviewed: 2026-09-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---

## Disposition (orchestrator, 2026-09-16)

- **CR-01: fixed.** `resolveBotLine` now returns the settle key of a live regret latch before the swing pacing gate; the hook comment that described a suppressed settle is rewritten. Regression test `never paces the settle of a live regret latch (223-REVIEW CR-01)` fails on the pre-fix code and passes after. Severity in practice was lower than Critical: the drop needed a mood line to fire on the same bot move that latched the blunder, and the hook comment shows the author accepted the drop to avoid a stale settle. The fix removes both.
- **WR-01: accepted.** Production always remounts `BotsGame` via `key={boot.nonce}`, so the latches are reset by construction; adding a reset seam for a caller that does not exist is the "split just to fit a signature" over-engineering CLAUDE.md warns against. Revisit if an in-place rematch is ever wired.
- **WR-02: fixed** on both resign surfaces (`board-btn-resign-cancel` in `BotGameMobileBar` and the pre-existing `GameControls` gap it copied).
