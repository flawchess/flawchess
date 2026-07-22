---
phase: 183-persona-registry-bots-page
reviewed: 2026-07-22T00:00:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - frontend/src/components/bots/BotDrawOfferBanner.tsx
  - frontend/src/components/bots/ClockDisplay.tsx
  - frontend/src/components/bots/GameResultDialog.tsx
  - frontend/src/components/bots/GameResultStrip.tsx
  - frontend/src/components/bots/PersonaCard.tsx
  - frontend/src/components/bots/PersonaDetailSurface.tsx
  - frontend/src/components/bots/PersonaGrid.tsx
  - frontend/src/components/bots/__tests__/BotDrawOfferBanner.test.tsx
  - frontend/src/components/bots/__tests__/ClockDisplay.test.tsx
  - frontend/src/components/bots/__tests__/GameResultDialog.test.tsx
  - frontend/src/components/bots/__tests__/GameResultStrip.test.tsx
  - frontend/src/components/bots/__tests__/PersonaCard.test.tsx
  - frontend/src/components/bots/__tests__/PersonaDetailSurface.test.tsx
  - frontend/src/components/bots/__tests__/PersonaGrid.test.tsx
  - frontend/src/data/personaAvatarPrompts.md
  - frontend/src/hooks/useBotGame.ts
  - frontend/src/lib/__tests__/botDrawGate.test.ts
  - frontend/src/lib/__tests__/botGameEnd.test.ts
  - frontend/src/lib/__tests__/botGameSnapshot.test.ts
  - frontend/src/lib/botDrawGate.ts
  - frontend/src/lib/botGameEnd.ts
  - frontend/src/lib/personas/__tests__/botPersonaSetupSettings.test.ts
  - frontend/src/lib/personas/__tests__/personaRegistry.test.ts
  - frontend/src/lib/personas/botPersonaSetupSettings.ts
  - frontend/src/lib/personas/personaAvatars.ts
  - frontend/src/lib/personas/personaRegistry.ts
  - frontend/src/lib/theme.ts
  - frontend/src/pages/Bots.tsx
  - frontend/src/pages/__tests__/Bots.test.tsx
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 183: Code Review Report

**Reviewed:** 2026-07-22
**Depth:** standard
**Files Reviewed:** 24 (across the required-reading list; `botGameSnapshot.ts` itself is out of scope — only its test file was in the change set)
**Status:** issues_found

## Summary

Reviewed the persona registry (`personaRegistry.ts`, `personaAvatars.ts`, `botPersonaSetupSettings.ts`), the persona-first Bots page UI (`PersonaGrid`, `PersonaCard`, `PersonaDetailSurface`), the D-06/D-07 persona-aware clock/result/draw-offer surfaces, and the `useBotGame.ts`/`botDrawGate.ts` additions that back the bot's new outgoing-draw-offer feature. The registry itself is well-guarded (exhaustive `Record` types, a 24-slot test suite, sentinel-safe lookups) and the persona-detail/result-surface wiring is consistent and well-tested. No BLOCKER-tier bugs, injection vectors, or hardcoded secrets were found.

Two real WARNING-tier gaps: `finalizeGame` never clears the bot's live outgoing draw offer, so the offer banner can be left dangling after the game ends via checkmate/timeout/resignation; and `PersonaDetailSurface.handlePlay` reintroduces hardcoded `600`/`0` TC fallbacks that the sibling `SetupScreen.tsx` already factored into a named constant (`DEFAULT_BOT_SETUP_SETTINGS`). Three lower-severity Info items round out the review: a narrow stale-score race in the same draw-offer flow, an undocumented duplicate placeholder-avatar emoji, and an unguarded interaction between the user's own draw-offer button and the bot's outgoing offer.

## Warnings

### WR-01: Bot's outgoing draw offer is never cleared when the game ends by any path other than the user's next move

**File:** `frontend/src/hooks/useBotGame.ts:766-795` (`finalizeGame`)
**Issue:** `botDrawOfferRef`/`botDrawOffer` (the D-07 "bot has a live outgoing draw offer" flag) is only ever cleared in two places: `commitMove` (only when `mover === settings.userColor`, i.e. the user commits a move) and `newGame()`. `finalizeGame` — called from `flagIfOutOfTime` (timeout), `resign()`, `detectEndCondition` (checkmate/board-draw), and the resign-hysteresis branch inside the bot's own grade callback — never touches either. Concretely: if the bot raises a draw offer and the user then resigns, flags on time, or gets checkmated before making another move, `botDrawOffer` stays `true`. `Bots.tsx` renders `BotDrawOfferBanner` unconditionally whenever `game.botDrawOffer` is true (independent of `game.outcome`), so the banner keeps showing "X offers a draw" with live Accept/Decline buttons stacked above/below the `GameResultDialog` after the game has already ended. Clicking Accept/Decline is functionally harmless (`acceptBotDraw`/`declineBotDraw` — the latter has no `outcomeRef` guard at all, and the former checks `outcomeRef.current` and no-ops), but the leftover interactive banner is a confusing, provably-reachable UI bug, not merely a style nit.
**Fix:**
```ts
const finalizeGame = useCallback(
  (finished: BotGameOutcome): void => {
    if (outcomeRef.current) return;
    outcomeRef.current = finished;
    abortControllerRef.current?.abort();
    setOutcome(finished);
    setIsBotThinking(false);
    // D-07: a finished game has no live bot offer to show anymore, regardless
    // of which path ended it (checkmate/timeout/resignation/agreement).
    botDrawOfferRef.current = false;
    setBotDrawOffer(false);
    const tcStr = toBackendTcStr(settings.baseSeconds, settings.incrementSeconds);
    ...
```

### WR-02: `PersonaDetailSurface.handlePlay` reintroduces hardcoded TC fallbacks instead of the existing named default

**File:** `frontend/src/components/bots/PersonaDetailSurface.tsx:174-176`
**Issue:**
```ts
const preset = findPresetByLabel(tcLabel) ?? findPresetByLabel(DEFAULT_TC_PRESET_LABEL);
const baseSeconds = preset?.baseSeconds ?? 600;
const incrementSeconds = preset?.incrementSeconds ?? 0;
```
CLAUDE.md's Coding Guidelines explicitly ban magic numbers ("extract thresholds, limits, and configuration values into named constants"). The sibling `SetupScreen.tsx` (this component's own stated precedent — the header doc comment says it "mirrors `SetupScreen.tsx`'s handleStart") already solved this exact fallback with a named constant: `preset?.baseSeconds ?? DEFAULT_BOT_SETUP_SETTINGS.baseSeconds` / `preset?.incrementSeconds ?? DEFAULT_BOT_SETUP_SETTINGS.incrementSeconds` (`components/bots/SetupScreen.tsx:127-128`). `PersonaDetailSurface` instead duplicates the raw literals `600`/`0` directly, diverging from the pattern it claims to mirror — if `DEFAULT_BOT_SETUP_SETTINGS`'s defaults ever change, this file silently drifts out of sync.
**Fix:** Reuse the existing constant instead of re-deriving the values:
```ts
import { DEFAULT_BOT_SETUP_SETTINGS } from '@/lib/botSetupSettings';
...
const baseSeconds = preset?.baseSeconds ?? DEFAULT_BOT_SETUP_SETTINGS.baseSeconds;
const incrementSeconds = preset?.incrementSeconds ?? DEFAULT_BOT_SETUP_SETTINGS.incrementSeconds;
```

## Info

### IN-01: Narrow stale-score race in the bot's own draw-offer raise

**File:** `frontend/src/hooks/useBotGame.ts:1445-1513` (`pool.grade(fen, [uci]).then(...)`)
**Issue:** The bot's outgoing-offer decision (`resolveBotDrawOfferUpdate`, called inside the same `pool.grade().then()` continuation as the resign check) is guarded only by `controller.signal.aborted`, which is set only when a *new bot turn* starts (aborting the previous turn's controller) or on cancel/unmount. Between the user committing their reply move and the "Bot-turn trigger" effect actually invoking `runBotTurn` (which is what aborts the stale controller), there is a window in which a slow-resolving `pool.grade()` promise from the bot's *previous* turn can still fire, using `chessRef.current` (already reflecting the user's just-played move) for the `chess.moveNumber()` check inside `wouldBotOfferDraw`, while `score` reflects the position *before* that reply. In that narrow window the bot could raise/refresh a draw offer using a one-ply-stale score. This mirrors an existing, already-accepted risk shape in the `wouldBotResign` path (same callback, same guard), so it isn't a regression introduced by this phase so much as an extension of a known pattern into a second decision — but it is worth flagging since it's new surface area with real (if rare) user-visible impact (a draw banner appearing "out of sync" with the position just played).
**Fix:** Not urgent given the narrow window and the existing precedent, but consider capturing `liveGamePlyRef.current` (or the mover's ply) at dispatch time and re-checking it hasn't advanced before acting on `score`, the same way `commitMove`'s `wasLive` check anchors on refs rather than closure state.

### IN-02: Duplicate placeholder-avatar emoji not documented for the Wall style

**File:** `frontend/src/lib/personas/personaRegistry.ts:373` (`wall-1200`, 🐢) and `:413` (`wall-1800`, 🐢); `frontend/src/data/personaAvatarPrompts.md:108,114`
**Issue:** `wall-1200` (Shelly the Turtle) and `wall-1800` (Rocco the Armadillo) both use the turtle emoji 🐢 as their D-18 placeholder avatar. The registry/prompts doc explicitly calls out and justifies the *other* emoji collision in the file (`attacker-1400` Wolverine and `trickster-1600` Coyote both using 🐺, with an inline note in `personaAvatarPrompts.md` acknowledging it and instructing the future art pass to differentiate them) — but the Turtle/Armadillo 🐢 collision has no equivalent callout. Since both are in the *same* style section (Wall), they also share the same background tint, so the two cards are visually harder to tell apart at a glance than the cross-style Wolverine/Coyote case (which at least differs by tint).
**Fix:** Add the same kind of explicit callout in `personaAvatarPrompts.md`'s Wall section noting the shared 🐢 placeholder and that the future real-art pass must differentiate `wall-1200`/`wall-1800` visually — mirroring the existing Attacker/Trickster note.

### IN-03: The user's "Offer draw" button is not gated on the bot's own live outgoing offer

**File:** `frontend/src/pages/Bots.tsx:436-437`
**Issue:** `GameControls`'s `canOfferDraw` prop is computed as `!game.drawOfferPending && game.outcome === null`, with no reference to `game.botDrawOffer`. A user can click "Offer draw" while the bot's own `BotDrawOfferBanner` is already showing a live outgoing offer, starting a second, independent draw-resolution effect (`useBotGame.ts`'s `drawOfferPending` effect) concurrently with the still-open bot offer. Both paths are individually safe (each is `outcomeRef`-guarded and can only end the game once), but the UX is confusing — two simultaneous draw negotiations in opposite directions with no visual indication they're related.
**Fix:** Consider folding `!game.botDrawOffer` into `canOfferDraw` in `Bots.tsx`, or auto-accepting/hiding the bot's own offer the moment the user clicks their own "Offer draw" button.

---

_Reviewed: 2026-07-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
