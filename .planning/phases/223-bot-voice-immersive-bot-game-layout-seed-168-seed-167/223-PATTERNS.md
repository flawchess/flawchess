# Phase 223: Bot Voice & Immersive Bot Game Layout (SEED-168 + SEED-167) - Pattern Map

**Mapped:** 2026-09-15
**Files analyzed:** 27 (10 new source + 6 new test + 10 modified + 1 deleted pair)
**Analogs found:** 25 / 27

All analog paths below are git-TRACKED source under `frontend/src` (verified with
`git ls-files`). Frontend-only phase; no backend file is in scope.

## File Classification

### New source files

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `frontend/src/lib/botGameCopy.ts` | copy table / pure lib | transform (id → string) | `frontend/src/lib/trainBotCopy.ts` | exact |
| `frontend/src/lib/botLineTrigger.ts` | pure resolver | transform (facts → key) | `frontend/src/components/train/trainBubbleState.ts` | exact |
| `frontend/src/lib/botThreat.ts` | pure utility (chess.js) | transform (board → bool) | `frontend/src/lib/materialDiff.ts` (pure board reader); shape sketched in RESEARCH | role-match |
| `frontend/src/hooks/useBotGameVoice.ts` | hook / sub-hook of `useBotGame` | event-driven (commit + grade callbacks) | `frontend/src/hooks/useBotGameDrawOffer.ts` (the other `useBotGame` sub-hook feeding `useBotGameEngineDispatch` options) | exact |
| `frontend/src/components/bots/BotGameBubble.tsx` | presentational component | request-response (props → JSX) | `frontend/src/components/train/TrainBotBubble.tsx` (layout/tokens) + `frontend/src/components/bots/BotDrawOfferBanner.tsx` (Accept/Decline slot) | exact |
| `frontend/src/components/bots/BotGameMobileBar.tsx` | presentational component | event-driven (4 callbacks) | `frontend/src/components/bots/GameControls.tsx` (resign + confirm dialog) | role-match |
| `frontend/src/components/bots/BotClockStrip.tsx` | presentational component | request-response | `frontend/src/components/board/PlayerBar.tsx` | exact |
| `frontend/src/components/bots/BotGameMobileLayout.tsx` | layout component | request-response | `renderMobileLayout` in `frontend/src/pages/Bots.tsx:125-158` | role-match |
| `frontend/src/components/bots/BotGameDesktopLayout.tsx` | layout component | request-response | `renderDesktopLayout` in `frontend/src/pages/Bots.tsx:159-…` | role-match |
| `frontend/src/components/settings/BoardSoundsSwitch.tsx` | settings control | event-driven (localStorage store) | `Switch` call site in `frontend/src/components/train/TrainScheduleSettings.tsx:238-245` | exact |

### New test files

| New File | Role | Closest Analog | Match Quality |
|----------|------|----------------|---------------|
| `frontend/src/lib/__tests__/botGameCopy.test.ts` | test (pure table invariants) | `frontend/src/lib/__tests__/trainBotCopy.test.ts:82-120, 224-233` | exact |
| `frontend/src/lib/__tests__/botLineTrigger.test.ts` | test (pure resolver) | `frontend/src/lib/__tests__/trainBotCopy.test.ts` (fabricated-input describe blocks) | exact |
| `frontend/src/lib/__tests__/botThreat.test.ts` | test (fixed FENs) | same file's table-driven `for…of` loops | role-match |
| `frontend/src/components/bots/__tests__/BotGameBubble.test.tsx` | component test | `frontend/src/components/bots/__tests__/PersonaGrid.test.tsx:144-160` | exact |
| `frontend/src/components/bots/__tests__/BotGameMobileBar.test.tsx` | component test | `frontend/src/components/bots/__tests__/BotDrawOfferBanner.test.tsx` (callback-fires assertions; delete after copying the shape) | exact |
| `frontend/src/components/settings/__tests__/BoardSoundsSwitch.test.tsx` | component test | `frontend/src/components/bots/__tests__/PersonaGrid.test.tsx` | role-match |

### Modified files

| Modified File | Change | In-file pattern to follow |
|---------------|--------|---------------------------|
| `frontend/src/hooks/useBotGameEngineDispatch.ts` | add `onBotMoveGraded` option | the `applyDrawOfferUpdate` option (`:198-207`, destructure `:226-243`, deps `:513-534`) |
| `frontend/src/hooks/useBotGame.ts` | wire the voice sub-hook + new `UseBotGameState` field | existing sub-hook wiring for `useBotGameDrawOffer` |
| `frontend/src/hooks/useBotGameMoves.ts` | fire seam (A) from `commitMove` | the `mover === userColor && botDrawOfferRef.current` block (`:149-163`) |
| `frontend/src/lib/mobileBoardControls.ts` | optional `onReset`/`canReset`, new `onResign` | the existing `NOOP_PAYLOAD` + destructure-with-defaults (`:25-33`, `:63-71`) |
| `frontend/src/App.tsx` | `MobileBottomBar` branch on `onResign`; sound switch in `MobileMoreDrawer` + `NavHeader` | the existing `boardControls != null` branch (`:458-479`) |
| `frontend/src/components/board/PlayerBar.tsx` | additive `ratingLabel?: string` | the additive `rightSlotContent?` / `fen?` props already on it |
| `frontend/src/components/bots/PersonaGrid.tsx` | bubble replaces prose in `HumanLikeOpponentsCard` | keep the inline `InfoPopover` span and the `currentStrength !== null` rating row verbatim (`:85-135`) |
| `frontend/src/components/bots/GameControls.tsx` | strip mute + offer-draw, keep Resign + dialog | keep `:50-84` as-is, delete `:86-131` and the now-unused imports |
| `frontend/src/lib/trainBotCopy.ts` | `export` the rotation epoch (`:84`) | one-word change only |
| `frontend/src/pages/Bots.tsx` | swap render helpers for the new layout components | **no new branch** — `BotsGame` is pinned at complexity 25 |
| tests: `src/pages/__tests__/Bots.test.tsx`, `src/App.test.tsx`, `src/components/bots/__tests__/PersonaGrid.test.tsx` | extend | — |
| **delete** `components/bots/BotDrawOfferBanner.tsx` + its test | knip gate | — |

---

## Pattern Assignments

### `frontend/src/lib/botGameCopy.ts` (copy table, transform)

**Analog:** `frontend/src/lib/trainBotCopy.ts`

**Module header + pure-module convention** (lines 1-27) — no React import, header states the
locked decision and its rationale:

```ts
/**
 * trainBotCopy — Phase 222 (TRAINBOT-01..08): all bot-narrated Train copy and
 * the pure casting/resolver functions that select it. No React import
 * (mirrors `lib/trainGuessLabels.ts` / `lib/trainScore.ts`'s pure-module
 * convention) ...
 * D-06 (LOCKED): copy is authored PER OUTCOME BUCKET ... ONE scoped exception
 * (2026-09-14, owner's call): the /train LANDING greeting (`landingHost`)
 * is per-persona ...
 */
import { differenceInCalendarDays, parseISO } from 'date-fns';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';
import type { Persona, PersonaId, Temperament } from '@/lib/personas/personaRegistry';
```

Note for the planner: that "ONE scoped exception" sentence must be **updated**, not
contradicted, when this phase generalises per-persona copy.

**Exhaustive table pattern** (lines 41-78) — copy this shape for all 11 tables:

```ts
/**
 * ... `Record<PersonaId, string>` makes a missing persona a compile error,
 * so the daily rotation (`landingHost`) can never land on a bot with nothing
 * to say.
 */
export const LANDING_GREETINGS: Record<PersonaId, string> = {
  'attacker-800': 'Bzzz! Sting first, plan later. Today we sting the blunders from your own games.',
  // ... all 24 ids in style-then-rung order
  'wall-1800': "Quiet position, clear head. Let's think through the moments your games went wrong.",
};
```

**Day-index rotation** (lines 80-124) — the roster host rotation copies this verbatim minus the
`introSeenAt`/`sessionDate` Tank gates (per CONTEXT discretion), including the
`noUncheckedIndexedAccess` guard:

```ts
const LANDING_HOST_IDS: readonly PersonaId[] = Object.keys(LANDING_GREETINGS) as PersonaId[];
const LANDING_ROTATION_EPOCH = parseISO('1970-01-01');   // ← make this `export const`

export function landingHost(input: LandingHostInput): LandingHost {
  const tank: LandingHost = { persona: PERSONA_REGISTRY[TANK_ID], copy: LANDING_GREETINGS[TANK_ID] };
  if (input.introSeenAt == null) return tank;
  if (input.sessionDate === null) return tank;
  const day = differenceInCalendarDays(parseISO(input.sessionDate), LANDING_ROTATION_EPOCH);
  if (Number.isNaN(day)) return tank;
  const index = ((day % LANDING_HOST_IDS.length) + LANDING_HOST_IDS.length) % LANDING_HOST_IDS.length;
  const id = LANDING_HOST_IDS[index];
  if (id === undefined) return tank;                // ← noUncheckedIndexedAccess narrowing
  return { persona: PERSONA_REGISTRY[id], copy: LANDING_GREETINGS[id] };
}
```

**Calibrated char-budget constant** (lines 185-199) — the model for `BOT_LINE_MAX_CHARS`,
including the "guard on that calibration, not a substitute for it" caveat:

```ts
/**
 * Phone copy budget for every stepper bubble ... Calibrated in the browser at
 * 375x667 (plan 06 UAT): ... the bubble copy is 204px wide, and the phone base
 * font renders `text-sm` at 16px/24px, so a line holds ~24 characters ...
 * The budget is a guard on that calibration, not a substitute for it ...
 */
export const STEPPER_COPY_MAX_CHARS = 145;
```

---

### `frontend/src/lib/__tests__/botGameCopy.test.ts` (test)

**Analog:** `frontend/src/lib/__tests__/trainBotCopy.test.ts`

**Exhaustiveness + regex-over-every-entry loop** (lines 82-95) — the exact template for the
"no em-dash" and "never claims to calculate" invariants:

```ts
describe('LANDING_GREETINGS / landingHost', () => {
  const ALL_IDS = Object.keys(PERSONA_REGISTRY) as PersonaId[];
  // The landing bubble is the page's only explanation of what Train is, so
  // every voice must still say the puzzles come from the user's own games.
  const OWN_GAMES = /your (own )?(games|blunders|mistakes)/i;

  it('has a greeting for every registry persona that names the user\'s own games', () => {
    for (const id of ALL_IDS) {
      expect(LANDING_GREETINGS[id], id).toMatch(OWN_GAMES);
      expect(LANDING_GREETINGS[id].trim().length, id).toBeGreaterThan(0);
    }
  });
```

**Char-budget assertion** (lines 224-233):

```ts
  it('every intro step, for both sides and both session kinds, fits the phone copy budget', () => {
    for (const isWarmup of [false, true]) {
      for (const side of ['white', 'black'] as const) {
        for (const step of introSteps(side, isWarmup)) {
          expect(step.copy.length).toBeLessThanOrEqual(STEPPER_COPY_MAX_CHARS);
        }
      }
    }
  });
```

**Rotation determinism** (lines 116-120) — reuse for the "roster and Train agree for a date" test:

```ts
  it('always pairs the persona with that persona\'s own greeting', () => {
    for (let offset = 0; offset < ALL_IDS.length; offset += 1) {
      const date = new Date(Date.UTC(2026, 6, 1 + offset)).toISOString().slice(0, 10);
      const host = landingHost({ sessionDate: date, ...SEEN });
      expect(host.copy).toBe(LANDING_GREETINGS[host.persona.id]);
```

---

### `frontend/src/lib/botLineTrigger.ts` (pure resolver, transform)

**Analog:** `frontend/src/components/train/trainBubbleState.ts` (63 lines, read in full)

**Header stating the complexity rationale** (lines 1-21) — reproduce this reasoning, since
`BotsGame` sitting at its ceiling is precisely why the resolver is extracted:

```ts
/**
 * trainBubbleState — Phase 222 (D-07): resolves which state the single
 * chat-row bubble slot under the board should render. Pure, no React import
 * ... Extracting this resolution OUT of `TrainSolveScreen` (rather than
 * inlining five sibling JSX guard blocks) is the mechanism that LOWERS the
 * component's own cyclomatic complexity ...
 * Precedence (highest first): verdict > grading > move > intro > drop-nudge > prompt.
 */
```

**Discriminated union + documented input interface** (lines 24-50) — `BotLineKey` must be a
literal union, never `string` (root CLAUDE.md rule):

```ts
export type TrainBubbleState =
  | { kind: 'verdict' }
  | { kind: 'grading' }
  | { kind: 'intro'; step: IntroStep }
  | { kind: 'prompt' };

/** Inputs `resolveBubbleState` needs — already-computed booleans/values from
 * `TrainSolveScreen`'s own state, never re-derived here. */
export interface ResolveBubbleStateInput {
  hasVerdict: boolean;
  isGrading: boolean;
  /** The active first-session intro-stepper step, or `null` when ... */
  introStep: IntroStep | null;
}
```

**Guard-clause chain** (lines 51-63) — the trigger priority (game end > draw offer > swing >
threat > first capture > game start) reads as a flat ordered list, no `else`, no nesting:

```ts
/**
 * Resolves the bubble's state from already-computed inputs. Guard-clause
 * returns only — no `else`, no nesting — so the precedence chain reads as a
 * flat, ordered list.
 */
export function resolveBubbleState(input: ResolveBubbleStateInput): TrainBubbleState {
  if (input.hasVerdict) return { kind: 'verdict' };
  if (input.isGrading) return { kind: 'grading' };
  if (input.guessMade) return { kind: 'move' };
  if (input.introStep !== null) return { kind: 'intro', step: input.introStep };
  if (input.nudgeActive) return { kind: 'drop-nudge' };
  return { kind: 'prompt' };
}
```

---

### `frontend/src/hooks/useBotGameVoice.ts` + the `onBotMoveGraded` seam

**Analog:** `frontend/src/hooks/useBotGameEngineDispatch.ts` (the `applyDrawOfferUpdate` option)

**Option-callback declaration** (lines 195-205) — add `onBotMoveGraded` right beside these, with
the same "which hook supplies it" comment:

```ts
  commitMove: (move: Move, mover: MoverColor, debitMs: number) => void;
  finalizeGame: (finished: BotGameOutcome) => void;
  /** From `useBotGameDrawOffer` — see that hook's file header for why the
   * draw-offer hook is wired before this one. */
  bumpConsecutiveLowScoreTurns: (scoreAtOrBelowThreshold: boolean) => number;
  applyDrawOfferUpdate: (
    score: number,
    chess: Chess,
    style: BotStyleParams,
    gameAlreadyOver: boolean,
  ) => void;
```

**Destructure block** (lines 226-243) — append the new callback to the same destructure:

```ts
  const {
    chessRef, outcomeRef, hasLeftBookRef, lastRootPracticalScoreRef, abortControllerRef,
    setIsBotThinking, botElo, blend, incrementSeconds, style, userColor,
    chargeableElapsedMs, flagIfOutOfTime, getClockBase, commitMove, finalizeGame,
    bumpConsecutiveLowScoreTurns, applyDrawOfferUpdate,
  } = options;
```

**Deps array with its explanatory comment** (lines 513-536) — the new callback goes in this list
and must be a `useCallback` upstream so `runBotTurn`'s identity does not churn:

```ts
    [
      botElo, blend, incrementSeconds, style, userColor, chargeableElapsedMs,
      flagIfOutOfTime, commitMove, finalizeGame, getClockBase, chessRef, outcomeRef,
      hasLeftBookRef, lastRootPracticalScoreRef,
      bumpConsecutiveLowScoreTurns, applyDrawOfferUpdate,
      // abortControllerRef/setIsBotThinking added (215-03 Task 2): ... listing
      // them changes nothing about when runBotTurn is recreated.
      abortControllerRef, setIsBotThinking,
    ],
```

**Grade continuation (the insertion point, `:458-478` per RESEARCH)** — capture the previous score
into a local BEFORE the ref overwrite (Pitfall 3), and keep the best-effort catch untouched
(no Sentry there, per the Security section):

```ts
          .catch(() => {
            // Best-effort only — a failed grade leaves the prior score in place.
          });
```

**Seam (A), `frontend/src/hooks/useBotGameMoves.ts:149-163`** — the bubble clears on exactly the
predicate the draw offer already uses:

```ts
  const commitMove = useCallback(
    (move: Move, mover: MoverColor, debitMs: number): void => {
      // D-07 (Phase 183): a bot's outgoing draw offer expires the instant the
      // USER commits their next move — checked here (not in `attemptMove`)
      // because this is the single seam both a user move AND a bot move reach
      if (mover === userColor && botDrawOfferRef.current) {
```

---

### `frontend/src/components/bots/BotGameBubble.tsx` (component, request-response)

**Analogs:** `frontend/src/components/train/TrainBotBubble.tsx` (structure + tokens),
`frontend/src/components/bots/BotDrawOfferBanner.tsx` (the Accept/Decline pair, which moves
INTO this bubble and keeps its testids)

**Header + purely-presentational contract** (TrainBotBubble lines 1-9):

```ts
/**
 * TrainBotBubble — Phase 222 (D-07): the ONE chat-row slot under the board.
 * Purely presentational: no data fetching, no Train domain logic. ...
 * `resolveBubbleState` (the caller's job) decides WHAT state is active;
 * this component only renders it.
 */
```

**Avatar size constant with a documented derivation** (lines 22-44) — the in-game bubble picks its
OWN size (Pitfall 11 lever) and must document the number the same way:

```ts
/**
 * Avatar size for the Train chat row — deliberately its own size, not shared
 * with PersonaCard's 58px grid-card size or ClockDisplay's 48px in-game size;
 * each surface picks the size that fits its own layout. ...
 */
const TRAIN_BOT_AVATAR_CLASS = 'size-[55px] sm:size-20';

export type TrainBotAvatarSize = 'default' | 'large';
const AVATAR_SIZE_CLASS: Record<TrainBotAvatarSize, string> = { ... };
```

**Bubble body, tail and border token** (lines 104-153) — reuse `TRAIN_BUBBLE_BORDER`; the in-game
bubble keeps the avatar BESIDE the bubble on phones (do not copy the `max-sm` stacking):

```tsx
      <div
        className={cn('relative min-w-0 flex-1 rounded-2xl border-2 bg-background px-4 py-3', ...)}
        style={{ borderColor }}
      >
        {/* Tail — a rotated square clipped to two of its borders, the classic
            CSS speech-bubble triangle, so it always tracks the bubble's
            current border color. */}
        <div
          aria-hidden="true"
          className="absolute h-3 w-3 rotate-45 bg-background max-sm:-top-[7px] max-sm:left-4 max-sm:border-l-2 max-sm:border-t-2 sm:-left-[7px] sm:top-4 sm:border-b-2 sm:border-l-2"
          style={{ borderColor }}
        />
        <div className="text-sm" data-testid="train-bot-copy">{children}</div>
        {actions !== undefined && (
          <div className="mt-2 flex flex-wrap justify-end gap-2">{actions}</div>
        )}
      </div>
```

Do NOT carry over `nudgeNonce` / `animate-train-bubble-nudge` / `prefersReducedMotion` (lines
56-59, 99-103, 127): D-07 forbids timers and animation.

**Draw-offer actions** (`BotDrawOfferBanner.tsx:33-58`) — move verbatim into the bubble's `actions`
slot, keeping both testids so existing assertions survive:

```tsx
      <span className="text-sm font-medium text-foreground">{message}</span>
        <Button variant="default" className={BOT_ACTION_BUTTON_CLASS}
          onClick={onAccept} data-testid="btn-accept-bot-draw">Accept</Button>
        <Button variant="brand-outline" className={BOT_ACTION_BUTTON_CLASS}
          onClick={onDecline} data-testid="btn-decline-bot-draw">Decline</Button>
```

Preserve the banner's documented property (lines 17-23): "Play continues underneath it — this is
deliberately NOT a Dialog", plus `aria-live="polite"` on the announcing element, and the
`personaName ?? 'The bot'` fallback for Custom games.

---

### `frontend/src/components/bots/BotGameMobileBar.tsx` (component, event-driven)

**Analog:** `frontend/src/components/bots/GameControls.tsx` (Resign trigger + confirm dialog)

**Resign + two-step confirm** (lines 43-84) — copy this whole block; all three testids are already
asserted by existing tests and must be reused:

```tsx
  const [resignDialogOpen, setResignDialogOpen] = useState(false);
  const handleConfirmResign = (): void => {
    setResignDialogOpen(false);
    onResignConfirmed();
  };
  ...
      <Button variant="brand-outline" className={cn(BOT_ACTION_BUTTON_CLASS, 'flex-1')}
        onClick={() => setResignDialogOpen(true)} data-testid="board-btn-resign">Resign</Button>
      <Dialog open={resignDialogOpen} onOpenChange={setResignDialogOpen}>
        <DialogContent data-testid="resign-confirm-dialog">
          <DialogHeader>
            <DialogTitle>Resign this game?</DialogTitle>
            <DialogDescription>You&apos;ll lose this game against the bot.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" className={BOT_ACTION_BUTTON_CLASS}
              onClick={() => setResignDialogOpen(false)}>Cancel</Button>
            <Button variant="destructive" className={BOT_ACTION_BUTTON_CLASS}
              onClick={handleConfirmResign} data-testid="board-btn-resign-confirm">Resign</Button>
```

Button-height token: `BOT_ACTION_BUTTON_CLASS = 'h-12 px-4'`
(`frontend/src/components/bots/chipStyles.ts:36-43`) — "the ONE height for every bot-play action
button", documented against the 44px WCAG 2.5.5 minimum. Use it for the bar's actions and for
the bubble's Accept/Decline.

**Bar host** — `App.tsx:449-479`, the existing takeover branch (its wrapper class and `flex-1`
comment are the pattern; branch on `boardControls.onResign != null` beside it):

```tsx
const MOBILE_BOTTOM_BAR_CLASSES =
  'fixed bottom-0 inset-x-0 flex sm:hidden z-40 bg-background border-t border-border pb-safe';
...
  if (boardControls != null) {
    return (
      <div data-testid="mobile-board-controls-bar"
        className={cn(MOBILE_BOTTOM_BAR_CLASSES, 'items-center px-2 py-2')}>
        <BoardControls ... flat
          // The bar root is a flex row, so without a width the controls shrink-wrap
          // and hug the left edge; flex-1 spreads them across the bar ...
          className="flex-1" />
```

---

### `frontend/src/lib/mobileBoardControls.ts` (modified: payload shape)

**In-file pattern** (lines 15-33, 60-79) — add `onResign?`, make `onReset`/`canReset` optional;
the NOOP defaults and the destructure-with-defaults already make a partial payload safe, and the
deps-array comment explains why the effect lists primitives, never the object:

```ts
const NOOP_PAYLOAD: MobileBoardControls = Object.freeze({
  onBack: () => {}, onForward: () => {}, onReset: () => {}, onFlip: () => {},
  canGoBack: false, canGoForward: false, canReset: false,
});
...
/**
 * Publishes `controls` for the lifetime of the calling component ... The
 * effect's dependency array lists only the destructured primitives/callbacks,
 * never `controls` itself, whose identity changes every render and would
 * otherwise loop the store write against the App re-render it triggers.
 */
export function usePublishMobileBoardControls(controls: MobileBoardControls | null): void {
  const { onBack = NOOP_PAYLOAD.onBack, /* … */ } = controls ?? {};
  const hasControls = controls != null;
  useEffect(() => {
    if (!hasControls) return;
    setPayload({ onBack, onForward, onReset, onFlip, canGoBack, canGoForward, canReset });
    return () => setPayload(null);
  }, [hasControls, onBack, onForward, onReset, onFlip, canGoBack, canGoForward, canReset]);
}
```

---

### `frontend/src/components/bots/BotClockStrip.tsx` + `PlayerBar` change

**Analog:** `frontend/src/components/board/PlayerBar.tsx` (85 lines, read in full)

**Additive-optional-prop convention** (lines 16-40) — the model for the new `ratingLabel?: string`
(Pitfall 6): every optional prop carries a doc comment naming the phase and why it is optional:

```ts
interface PlayerBarProps {
  isWhite: boolean;
  name: string | null;
  /** ELO/rating; rendered in parentheses when present. */
  rating: number | null;
  /** Mover's remaining clock at the current position (seconds); null = no %clk → clock hidden. */
  clockSeconds: number | null;
  /**
   * Phase 208 (PASTE-02 ...): optional content for the right-aligned slot,
   * rendered ONLY when clockSeconds is null — a real game's clock always wins.
   */
  rightSlotContent?: ReactNode;
  /** Quick 260809-jzz (D-05): the FEN of the position currently on the board.
   * Omitted means no material display ... */
  fen?: string;
  testId?: string;
}
```

**Row layout + `text-sm` floor + material slot** (lines 55-84) — the clock strip copies this
left/right split:

```tsx
    <div data-testid={testId}
      className="flex items-center justify-between gap-2 px-1 text-sm text-foreground">
      <span className="flex min-w-0 items-center gap-2">
        <span className="truncate min-w-0">
          {isWhite ? '■' : '□'} {name ?? '?'}
          {rating !== null && <span className="text-muted-foreground"> ({rating})</span>}
        </span>
        {fen !== undefined && (
          <MaterialDisplay fen={fen} side={isWhite ? 'white' : 'black'} className="shrink-0" />
        )}
      </span>
      {clockSeconds !== null ? (
        <span className="flex shrink-0 items-center gap-1 font-medium tabular-nums">
          <Clock className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          {formatClock(clockSeconds)}
        </span>
      ) : ( ... )}
```

The `ratingLabel` branch must win over `rating` so the bot renders `~1850` (`calibratedLabel`),
never `(1850)`. Note `PlayerBar` keeps its own local `formatClock` (lines 7-14, "Local helper,
not a shared import (D-05)") — the new clock strip should instead use `formatClockLabel` /
`isLowTime` from `src/lib/chessClock.ts`, which `ClockDisplay` already mandates.

---

### `frontend/src/components/settings/BoardSoundsSwitch.tsx` (settings control, event-driven)

**Analog:** `frontend/src/components/train/TrainScheduleSettings.tsx:233-249` (one of three
identical `Switch` call sites; the others are `MaiaHumanPanel.tsx:162-166`,
`EngineToggleHeader.tsx:34-38`)

**Call-site quartet** — `data-testid` + `aria-label` + `checked` + `onCheckedChange`, control
left, label right:

```tsx
      <div className="flex items-center gap-2">
        <Switch
          data-testid="filter-reminder-enabled"
          aria-label="Remind me to train"
          checked={checked}
          disabled={disabled || subscribing || blocked}
          onCheckedChange={onToggle}
        />
        <p className="text-sm text-muted-foreground">Remind me to train</p>
      </div>
```

The primitive itself (`frontend/src/components/ui/switch.tsx:18-38`) needs no change — it is an
unstyled `{...props}` passthrough with `cn()` merge. Watch the polarity inversion:
`useMuted()` is "muted", the switch reads "Board sounds", so `checked={!muted}` /
`onCheckedChange={(on) => setMuted(!on)}`. Render sites: `MobileMoreDrawer` above the
`drawer-logout` divider (`App.tsx:580-590`) and `NavHeader`'s account `div` beside `nav-logout`
(`App.tsx:352-368`).

---

### `frontend/src/components/bots/PersonaGrid.tsx` (modified: roster welcome bubble)

**In-file pattern** (lines 55-135) — the copy-accuracy constraint comment is the single most
important thing to carry into `botGameCopy.ts`'s header:

```ts
/**
 * Copy accuracy constraint: 16 of the 24 personas run at `HUMAN_BLEND` (rungs
 * 800-1400), where `selectBotMove` makes exactly ONE Maia policy call and never
 * searches. So this copy must never claim the bots "calculate" or "think" ...
 */
```

**Inline `InfoPopover` trigger** (lines 84-110) — keep exactly this shape at the end of the bubble
copy, including the `align-middle` note; the popover body is the only place `text-xs` is allowed:

```tsx
        <p>
          These bots are driven by the FlawChess Engine and play like
          human players, not like weakened engines.{' '}
          <span className="inline-flex align-middle">
            <InfoPopover ariaLabel="About the bot opponents" testId="bots-intro-info">
              <div className="max-w-xs space-y-2"> ... </div>
            </InfoPopover>
          </span>
        </p>
```

**Rating row + its gate** (lines 118-135) — move verbatim beneath the bubble:

```tsx
        {currentStrength !== null && (
          <div className="flex items-center gap-1 border-t border-border/40 pt-3"
            data-testid="bots-player-rating">
            <p>
              Your estimated blitz rating:{' '}
              <span className="font-semibold text-foreground">{`~${Math.round(currentStrength.rating)}`}</span>
            </p>
            <InfoPopover ariaLabel="About your estimated blitz rating" testId="bots-player-rating-info">
```

The `~${Math.round(...)}` expression is also the exact source for the user's desktop `PlayerBar`
`ratingLabel` (D-11).

---

### Component tests

**Analog:** `frontend/src/components/bots/__tests__/PersonaGrid.test.tsx:144-160`

**Guest/gated-render assertion + the `text-xs` invariant** (copy into every new component test):

```tsx
  it('renders the human-like-opponents intro card even with no rating estimate (guests need it most)', () => {
    render(<PersonaGrid onSelectPersona={vi.fn()} onSelectCustom={vi.fn()} currentStrength={null} />);
    // The card must NOT be nested inside the currentStrength guard above —
    // a guest sees no rating line, but must still see the explanation.
    const card = screen.getByTestId('bots-intro-card');
    expect(card.textContent).toContain('Human-like Opponents');
    expect(screen.getByTestId('bots-intro-info')).toBeTruthy();
  });

  it('never uses sub-text-sm font-size utilities anywhere in the grid', () => {
    render(<PersonaGrid ... currentStrength={null} />);
    const container = screen.getByTestId('bots-persona-grid');
    expect(container.innerHTML).not.toContain('text-xs');
  });
```

---

## Shared Patterns

### Pure-module discipline (copy + resolvers)
**Source:** `frontend/src/lib/trainBotCopy.ts:1-27`, `frontend/src/components/train/trainBubbleState.ts:1-21`
**Apply to:** `botGameCopy.ts`, `botLineTrigger.ts`, `botThreat.ts`
No React import; a header that names the phase, the locked decision IDs and why the module exists
outside the component; total functions of already-computed values; guard-clause returns.

### Exhaustive `Record<PersonaId, …>` tables
**Source:** `frontend/src/lib/trainBotCopy.ts:41-78`
**Apply to:** all 11 authored line tables (D-08)
`PersonaId` is a template-literal union, so a missing persona is a compile error. Under
`noUncheckedIndexedAccess`, indexing by a computed id still needs the
`if (id === undefined) return fallback;` narrowing shown at `trainBotCopy.ts:120`.

### Named constants with a documented derivation
**Source:** `frontend/src/lib/trainBotCopy.ts:185-199`, `components/bots/chipStyles.ts:36-43`,
`components/train/TrainBotBubble.tsx:22-40`
**Apply to:** `BOT_LINE_SWING_THRESHOLD`, `BOT_LINE_MIN_SPACING_MOVES`, `BOT_LINE_MAX_CHARS`,
threat piece values, every new avatar/size class.
Root CLAUDE.md forbids magic numbers; the shipped convention is a constant whose doc comment
records how the value was calibrated and what re-calibrates it.

### Cross-hook callback options
**Source:** `frontend/src/hooks/useBotGameEngineDispatch.ts:198-207, 226-243, 513-534`
**Apply to:** `onBotMoveGraded`, `onMoveCommitted`
Declare in the options interface with a "from which hook" comment, destructure in the same block,
list in the `runBotTurn` deps, and supply it as a `useCallback` from `useBotGame`.

### Single-seam discipline
**Source:** `frontend/src/hooks/useBotGameMoves.ts:149-163` ("this is the single seam both a user
move AND a bot move reach"), `useBotGameEngineDispatch.ts:458-478` (the one grade site)
**Apply to:** every new hook wiring. Never add a second grade call, a second commit path, or a
second snapshot writer.

### Testids, `text-sm` floor, button variants
**Source:** `frontend/CLAUDE.md`; live examples in `GameControls.tsx`, `BotDrawOfferBanner.tsx`,
`PersonaGrid.test.tsx:155`
**Apply to:** every new component. Kebab-case component-prefixed testids (reuse
`board-btn-resign`, `resign-confirm-dialog`, `board-btn-resign-confirm`, `btn-accept-bot-draw`,
`btn-decline-bot-draw` so existing assertions survive); `aria-label` on icon-only buttons;
`variant="default"` for the one primary CTA, `variant="brand-outline"` for secondary, never
`variant="secondary"`.

### Complexity containment
**Source:** `frontend/eslint.config.js:68-79` baseline region; `frontend/src/pages/Bots.tsx`
(`BotsGame` pinned at 25), `components/board/BoardControls.tsx` (pinned at 16)
**Apply to:** all layout work. Every new branch lands in a NEW file. Re-measure with
`npx eslint --no-inline-config --rule 'complexity: ["error", 1]' <path>`. Never widen a ceiling.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `frontend/src/lib/botThreat.ts` | pure utility | transform | No existing module calls `chess.attackers()` for a hanging/under-defended probe. Nearest conventions: `lib/materialDiff.ts` (the single owner of piece-value arithmetic — do NOT duplicate it; the threat table is a separate, comparison-only map) and `lib/liveFlaw.ts:92-107` (`evalToExpectedScore`). Use the RESEARCH sketch (§"The threat probe (D-05), engine-free") as the starting shape. |
| `frontend/src/components/bots/BotClockStrip.tsx` | component | request-response | No below-board white-left/black-right clock strip exists; it is a recomposition of `PlayerBar`'s row layout with `MaterialDisplay` plus `formatClockLabel`/`isLowTime` from `lib/chessClock.ts`. Structure-only gap, tokens all exist. |

## Metadata

**Analog search scope:** `frontend/src/{lib,hooks,components,pages}`, `frontend/eslint.config.js`
**Files read this pass:** 13 source + 2 test files (plus targeted ranges of `App.tsx`,
`useBotGameEngineDispatch.ts`, `PersonaGrid.tsx`, `trainBotCopy.ts`, `trainBotCopy.test.ts`)
**Tracked-source check:** `git ls-files` returned all 11 probed analog paths (no gitignored
mirrors involved; this repo's frontend has none)
**Pattern extraction date:** 2026-09-15
