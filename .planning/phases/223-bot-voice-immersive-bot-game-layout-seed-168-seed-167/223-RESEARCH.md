# Phase 223: Bot Voice & Immersive Bot Game Layout (SEED-168 + SEED-167) - Research

**Researched:** 2026-09-15
**Domain:** React 19 + TypeScript frontend — per-persona copy tables, a bubble state machine
driven by an existing async Stockfish grade, and a two-breakpoint layout rework of `/bots`
**Confidence:** HIGH (every claim below was read out of the working tree this session; file:line
citations throughout. The only MEDIUM/LOW items are the two-line copy budget, which cannot be
measured in jsdom, and the mobile board-width outcome, which needs UAT.)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Swing signal & thresholds**

- **D-01:** The swing signal is the **existing post-bot-move Stockfish grade**. After every
  non-book bot move `useBotGameEngineDispatch.ts` already runs `pool.grade(fen, [uci])`
  and stores a bot-POV expected score (0-1) in `lastRootPracticalScoreRef` for the
  resign/draw gates. The realized swing is the **delta between consecutive post-bot-move
  scores** (i.e. over one move pair: player move + bot reply). No Maia WDL plumbing
  (`selectBotMove` returns only a UCI string and stays that way); no extra engine calls.
  Consequence accepted: no swing lines during the opening-book window (nothing is graded
  there) and none when a grade fails (best-effort, as today).
- **D-02:** Threshold is **large only, ~0.20 expected-score points** over the move pair
  (roughly a clean piece), a named constant (`BOT_LINE_SWING_THRESHOLD` or similar),
  tuned in UAT. Lines should fire a couple of times per game at most; every one must be
  obviously visible on the board.
- **D-03:** Swing in the bot's favor ≥ threshold → the **earned tease** line, regardless of
  whether the bot found the strongest punishment ("delta is delta"). No multi-candidate
  grading to check optimality.
- **D-04:** Swing against the bot ≥ threshold is **split by capture**: if the player's move
  in that pair captured material → the "you punished my mistake" line (self-deprecating);
  otherwise → the "nice move" compliment. Known imprecision accepted (a sacrifice in reply
  is also a capture).
- **D-05:** The **player-threat** line is detected with pure chess.js after the player's
  move: a bot piece is attacked and either undefended or attacked by a lower-value piece
  (hanging / under-defended). No engine involvement, so it can never announce something
  the board does not show. It fires after the bot's reply like every other line.

**Board-truth rule (from SEED-168, locked)**

- **D-06:** A line is shown **only right after the bot's own move** and only about swings
  already cashed in on the board. Never on the player's turn, never about a player blunder
  the bot did not punish, never about the bot's own mistake before the player cashed it
  in, never about a threat the bot has prepared but not executed. The game-start line is
  pure voice (it cannot reference the position).
- **D-07:** The bubble **persists until the player's next committed move**, then clears.
  No timers, no animation. Fixed two-line height on both breakpoints; a copy test rejects
  any line that overflows two lines at the 375px bubble width (the `trainBotCopy.test.ts`
  invariant pattern).

**Copy (locked)**

- **D-08:** Own voice per bot: every line table is `Record<PersonaId, string>` (or a
  per-trigger record of them) so a missing persona is a compile error, mirroring
  `LANDING_GREETINGS` in `frontend/src/lib/trainBotCopy.ts`. One variant per trigger;
  repeating a line once per game is fine. Tone: entertaining, sometimes teasing, never
  mean; the tease must read the same to an 800-rung beginner as to an 1800 player; no
  em-dashes; the `HumanLikeOpponentsCard` accuracy rule holds (16 of 24 personas never
  search, so no line may claim the bot "calculated" or "saw it coming").
  — **Reversibility:** costly — ~200+ authored lines across 24 personas; changing the
  table shape touches every entry.
- **D-09:** Copy authored in the plan is a **starting point**: messages, tone and the
  board-truth constraints are locked; the executor may tighten wording within them.

**Layout (locked from SEED-168; details are Claude's discretion below)**

- **D-10:** Mobile: header already suppressed via `useMarkPlayActive`; the bottom nav is
  replaced through the existing `usePublishMobileBoardControls` seam
  (`frontend/src/lib/mobileBoardControls.ts`), extended with a Resign action and without
  Reset. Exactly four actions: Resign, Back, Forward, Flip. Resign keeps its confirm
  dialog.
- **D-11:** Mobile shows no bot name/style/ELO and no player name; desktop shows both
  players via `PlayerBar` (name + ELO left, clock + material right). Bot ELO on desktop is
  the persona's `calibratedLabel`; the user's is `profile.current_strength.rating`
  (rounded, tilde-prefixed like the roster row) or omitted when null (guests).
- **D-12:** The bot's draw offer (Phase 183 D-07, `botDrawOffer`) renders inside the bubble
  with Accept / Decline buttons; `BotDrawOfferBanner` is deleted. The user-side Offer draw
  button and its cooldown UI are removed; `offerDraw` stays in the hook for now (dead
  wiring may be pruned if trivially safe).
- **D-13:** Roster page: the welcome bubble replaces the sentence in
  `HumanLikeOpponentsCard`; the `InfoPopover` engine explainer stays as an inline trigger
  at the end of the bubble copy (Train landing pattern); the estimated-rating row keeps its
  own `InfoPopover` and its `currentStrength !== null` gate.

### Claude's Discretion

- **Trigger priority & pacing.** One line per bot move, priority order: game end >
  draw offer > swing (either direction) > player threat > first capture > game start.
  First capture and game start fire once per game; swing/threat lines can repeat but with
  a minimum spacing of 3 bot moves between any two non-terminal lines so the bot is not
  chatty at low rungs. Game-end line: show it in the bubble AND keep `GameResultDialog`;
  the dialog already waits on `celebrationHold`, so the line is visible during the hold
  and stays behind the dialog afterwards (no new timing logic).
- **Sound switch home & the gear.** No settings page exists. Recommended home: a
  "Board sounds" switch in the **mobile More drawer** (`MobileMoreDrawer`, under the
  account header) and the **desktop header's account area** (next to Logout), both bound
  to the existing `useMuted`/`setMuted` in `frontend/src/lib/sounds.ts`. No new route.
  The top-right gear on the mobile game screen is therefore **dropped** (an icon with no
  sheet behind it is worse than no icon); the top bar holds only the back arrow. If the
  user prefers a gear, it should open the More drawer, not a new sheet.
- **Roster host & greeting tables.** Recommended: the roster host is Train's
  `landingHost` rotation (same bot greets on /train and /bots that day; reuse
  `LANDING_ROTATION_EPOCH` and the day index, but never the Train-specific
  `introSeenAt`/`sessionDate` gates: fall back to a plain day-index rotation with no Tank
  pin on the roster). Two separate tables: `ROSTER_GREETINGS` (welcome, may mention
  "pick an opponent") and `GAME_START_LINES` (in-game hello), since the surfaces read
  differently.
- Back arrow on mobile: navigates to the roster; a live game stays in the existing
  pending store (`botPendingStore.ts`) and `ResumeGate` handles the return, no new
  resign-on-leave logic unless research finds the pending store does not cover it.
- Avatar size constants, bubble tail/border (reuse `TRAIN_BUBBLE_BORDER`), clock strip
  layout, PlayerBar clock source (`whiteClockMs`/`blackClockMs` in seconds), test
  strategy for the trigger resolver (pure module with fabricated score sequences).

### Deferred Ideas (OUT OF SCOPE)

- A real `/settings` page (account, sounds, Train schedule in one place). This phase puts
  the sound switch in the existing account surfaces; a settings page is its own phase if
  more preferences accumulate.
- Maia-WDL-flavoured lines ("a human at your level misses that"): rejected for this phase
  in favour of the existing Stockfish signal; revisit only if the lines feel generic.

**Reviewed Todos (not folded):** WR-01 `pt-33` Train score chart; "172-deferred-review-findings",
"variation-tree-nested-button", "bitboard storage" — keyword matches only, unrelated.
</user_constraints>

---

## Summary

Everything this phase needs already exists in the tree; nothing new gets installed and no new
architectural seam has to be invented. The swing signal (D-01) is a two-line change at one exact
site — `useBotGameEngineDispatch.ts:473-477`, where a fresh bot-POV expected score is computed
and written into `lastRootPracticalScoreRef`; capturing the *previous* value of that ref before
the overwrite yields the D-01 delta with zero extra engine calls `[VERIFIED: frontend/src/hooks/useBotGameEngineDispatch.ts:458-477]`.
The move-pair facts the resolver needs (`move.captured`, `move.san`, mover color) all pass
through exactly one function, `commitMove` `[VERIFIED: frontend/src/hooks/useBotGameMoves.ts:149-151]`,
which is also where the bot's draw offer already auto-expires on the user's move — the same
place the bubble should clear (D-07).

The dominant *risk* in this phase is not the voice, it is the two hard mechanical constraints
the layout rework runs into. First, `BotsGame` is pinned at cyclomatic complexity **25**, which
is exactly its eslint ceiling (`eslint.config.js:148-154`) — a single new `if`/`&&`/`?:` inside
that function fails `npm run lint`, so the rework MUST land as new components, never as branches
in the page `[VERIFIED: measured with npx eslint --rule 'complexity:["error",1]']`. Second,
`BoardControls` is likewise pinned at **16**, its own ceiling, so the four-action mobile bar
cannot be built by adding a `showReset` prop to it; it needs its own component
`[VERIFIED: frontend/eslint.config.js:80-90 + measured]`.

Three CONTEXT/SEED assumptions are wrong against the tree and the plan must correct them:
(1) `pb-20` cannot go away on mobile — the replacement bar is still `fixed` and ~64px tall, so
clearance is still required (`App.tsx:446-448`); (2) `celebrationHold` is `true` only after a
human **win**, so a loss/draw game-end line would be covered by `GameResultDialog` immediately
(`useWinCelebrationHold.ts:24-28`); (3) `trainBubbleState.ts` lives in `components/train/`, not
`lib/`. Also, `LANDING_ROTATION_EPOCH` is module-private (`trainBotCopy.ts:84`) and there is no
width-measuring copy test anywhere — the "two lines at 375px" invariant is enforced today as a
calibrated **character budget** (`STEPPER_COPY_MAX_CHARS = 145`, `trainBotCopy.ts:199`).

**Primary recommendation:** Build four new pure modules (`botGameCopy.ts` for the
`Record<PersonaId, …>` tables, `botLineTrigger.ts` for the resolver, `botThreat.ts` for the
chess.js threat probe, `botGameVoice` as a sub-hook of `useBotGame`) plus three new components
(`BotGameBubble`, `BotGameMobileBar`, and the two replacement layout renderers), wire the swing
signal through one new `onBotMoveGraded(prevScore, newScore, ply)` option on
`useBotGameEngineDispatch`, and delete `BotDrawOfferBanner` + `GameControls`' mute and
offer-draw controls. Do not touch `BoardControls` or add branches to `BotsGame`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-persona line tables (~200 strings) | Browser / pure `lib` module | — | Static authored copy, compile-time exhaustiveness via `Record<PersonaId, string>`; no server involvement, mirrors `trainBotCopy.ts` |
| Swing detection (score delta) | Browser / existing engine worker | — | The Stockfish grade already runs in a Web Worker per bot move; this phase only reads the number that is already computed |
| Trigger resolution (which line fires) | Browser / pure `lib` module | — | Total function of (prev score, new score, move-pair facts, phase); unit-testable with fabricated sequences |
| Threat detection | Browser / chess.js | — | `attackers()` on the live board; deliberately engine-free so it can never leak engine knowledge (D-05) |
| Bubble lifecycle (set / clear on player move) | Browser / `useBotGame` sub-hook | `commitMove` seam | `commitMove` is the single commit path both movers reach — same seam `botDrawOffer` already uses |
| Mobile bottom bar takeover | Browser / `App.tsx` layout | `mobileBoardControls` store | The writer (`BotsGame`) and reader (`MobileBottomBar`) are in unrelated subtrees; a module store is the existing bridge |
| Sound preference | Browser / localStorage | — | Flat `MUTE_KEY` preference, guest-safe, no server field |
| Roster greeting rotation | Browser / pure `lib` module | `devClock` | Day-index rotation from a caller-supplied ISO date keeps the module pure and testable |
| Persisted in-progress game (back-arrow leave) | Browser / localStorage | — | `writeSnapshot` already fires on every commit; `ResumeGate` already covers the return |

---

## Standard Stack

### Core (all already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `chess.js` | 1.4.0 | Threat probe (`attackers`), capture flag (`move.captured`), piece types | Already the project's rules engine; `attackers(square, attackedBy?)` and `isAttacked(square, attackedBy)` both exist in this version `[VERIFIED: frontend/node_modules/chess.js/dist/types/chess.d.ts:130,133]` |
| `radix-ui` | ^1.4.3 | `Switch` for the "Board sounds" control | `frontend/src/components/ui/switch.tsx` already wraps it; three existing call sites to copy `[VERIFIED: frontend/src/components/ui/switch.tsx:18-38]` |
| `lucide-react` | ^1.21.0 | `ArrowLeft` (back), `Flag`/existing Resign affordance, `Volume2`/`VolumeX` | Already imported across the page and bar |
| `date-fns` | ^4.4.0 | `differenceInCalendarDays` / `parseISO` for the roster host rotation | Exactly how `landingHost` computes its day index `[VERIFIED: frontend/src/lib/trainBotCopy.ts:22,117]` |
| `vitest` + `@testing-library/react` | as installed | Unit + component tests | Project-wide; `testTimeout` 20s / `hookTimeout` 30s set globally `[VERIFIED: frontend/vite.config.ts:86-93]` |

### Supporting (in-repo modules to reuse, not rebuild)

| Module | Path | Purpose | When to Use |
|--------|------|---------|-------------|
| `TrainBotBubble` | `src/components/train/TrainBotBubble.tsx` | Avatar + speech bubble with tail, `size` `default`/`large`, `actions` slot | Use **as-is** for the roster welcome (D-13). Do NOT reuse verbatim in-game — see Pitfall 4 |
| `TRAIN_BUBBLE_BORDER` | `src/lib/theme.ts:582` | `oklch(0.55 0.02 40)` bubble border token | Share with the in-game bubble so the two surfaces read as one system |
| `PlayerBar` | `src/components/board/PlayerBar.tsx` | name + rating + material + clock row | Desktop rows (D-11). Needs one additive prop — see Pitfall 6 |
| `MaterialDisplay` | `src/components/board/MaterialDisplay.tsx` | lichess-style net surplus icons + `+N` | Mobile clock strip and both `PlayerBar` rows; already shared by `PlayerBar` and `ClockDisplay` |
| `usePublishMobileBoardControls` | `src/lib/mobileBoardControls.ts:62` | Publishes a payload the `MobileBottomBar` swaps in | The D-10 seam. Only two other consumers exist (see table below) |
| `useMarkPlayActive` | `src/lib/playActive.ts:30` | Suppresses `MobileHeader` while mounted | Already called by `BotsGame` (`Bots.tsx:260`) — nothing to change |
| `useMuted` / `setMuted` / `MUTE_KEY` | `src/lib/sounds.ts:187,195,78` | Flat, guest-safe localStorage mute preference | The SEED-167 switch binds straight to these |
| `BOT_ACTION_BUTTON_CLASS` | `src/components/bots/chipStyles.ts` | `h-12 px-4`, the ONE bot-play button height | Accept/Decline inside the bubble, Resign in the bar |
| `InfoPopover` | `src/components/ui/info-popover.tsx` | HelpCircle trigger + portal body, `text-xs` allowed inside | Roster bubble inline trigger (D-13) |
| `devClockNow` / `readDevClockOffsetMinutes` | `src/lib/devClock.ts:32,57` | Dev-only simulated clock | Compute the roster rotation's ISO day in the component, pass it into the pure module |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `BotGameMobileBar` component | Add `showReset?: boolean` to `BoardControls` | REJECTED — `BoardControls` measures complexity 16 against a ceiling of 16; one more branch fails lint (see Pitfall 1) |
| New field on `UseBotGameState` | Publish the bubble state through a second module store like `mobileBoardControls` | REJECTED — the bubble is game state, scoped to one mounted game; the module store exists only because `App.tsx` sits above the router `Outlet` |
| `onBotMoveGraded` callback option | Expose `lastRootPracticalScoreRef` upward and let the page diff it | REJECTED — a ref mutation triggers no render; the page would never see the change |
| Sibling `BotGameBubble` component | `variant` prop on `TrainBotBubble` | Sibling preferred: the in-game bubble needs a fixed two-line height, a horizontal phone layout (`TrainBotBubble` stacks the avatar ABOVE the bubble on `max-sm`, `TrainBotBubble.tsx:101,142`) and no nudge machinery. A variant prop would add branches to a shared component |

**Installation:** none. This phase adds **zero** packages.

**Version verification:** `chess.js` confirmed at 1.4.0 from the installed
`node_modules/chess.js/package.json` this session.

---

## Package Legitimacy Audit

**Not applicable — this phase installs no external packages.** Every dependency it uses is
already in `frontend/package.json` and already imported by shipped code. No `npm install` step
belongs in any plan; if one appears, it is out of scope and should be challenged.

| Package | Registry | Verdict | Disposition |
|---------|----------|---------|-------------|
| (none) | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
                        ┌──────────────────────────────────────────────┐
  player drags a piece  │            useBotGame (orchestrator)         │
  ───────────────────►  │                                              │
                        │  attemptMove ──┐                             │
                        │                ▼                             │
                        │           commitMove  ◄──┐                   │
                        │        (useBotGameMoves) │                   │
                        │        · move.san/.captured                  │
                        │        · mover color     │                   │
                        │        · clears botDrawOffer on USER move    │
                        │                │         │                   │
                        │     ┌──────────┴─────┐   │                   │
                        │     │ NEW SEAM (A)   │   │                   │
                        │     │ onMoveCommitted│   │                   │
                        │     └────────┬───────┘   │                   │
                        │              ▼           │                   │
                        │    ┌────────────────────────────┐            │
                        │    │  useBotGameVoice (NEW)     │            │
                        │    │  · first-capture latch     │            │
                        │    │  · pending threat flag     │            │
                        │    │  · last-line ply (pacing)  │            │
                        │    │  · clears on USER commit   │            │
                        │    └──────┬─────────────────────┘            │
                        │           │ calls                            │
                        │           ▼                                  │
                        │   resolveBotLine()  ◄── botThreat.ts         │
                        │   (pure, botLineTrigger.ts)                  │
                        │           │                                  │
                        │           ▼  BotLineKey | null               │
                        │   UseBotGameState.botLine  ──────────────────┼──► BotGameBubble
                        │                            │                 │    (copy from
                        │                          ▲ │                 │     botGameCopy.ts,
                        │  ┌───────────────────────┘ │                 │     keyed by PersonaId)
                        │  │ NEW SEAM (B)            │                 │
                        │  │ onBotMoveGraded(prev,new,ply)             │
                        │  └───────────┬─────────────┘                 │
                        │              │                               │
                        │  useBotGameEngineDispatch                    │
                        │   runBotTurn ──► selectBotMove (Maia/SF) ──► commitMove
                        │        └─────► pool.grade(fen,[uci]) ──► evalToExpectedScore
                        │                          │                   │
                        │                          └─► lastRootPracticalScoreRef
                        │                              (resign + draw gates, unchanged)
                        └──────────────────────────────────────────────┘
                                          │
                                          ▼
   Bots.tsx (page)  ───────────────────────────────────────────────────────────
     mobile:  [back arrow] · [avatar + BotGameBubble] · [board] · [clock strip]
              └─ usePublishMobileBoardControls({resign,back,forward,flip}) ──► App.tsx MobileBottomBar
     desktop: [PlayerBar] · [board] · [PlayerBar]   |  side col: [avatar+bubble] [move list] [Resign]
```

**Reading the diagram:** a player move enters at `attemptMove`, reaches `commitMove`, and fires
seam (A). The bot's reply reaches the same `commitMove`, then its asynchronous grade resolves
some hundreds of milliseconds later and fires seam (B). Only seam (B) can produce a swing line;
seam (A) supplies the facts (capture? threat?) that seam (B)'s resolver consumes.

### Recommended new files

```
frontend/src/
├── lib/
│   ├── botGameCopy.ts          # Record<PersonaId, string> per trigger + ROSTER_GREETINGS
│   ├── botLineTrigger.ts       # pure resolver: inputs -> BotLineKey | null
│   └── botThreat.ts            # pure chess.js threat probe (D-05)
├── hooks/
│   └── useBotGameVoice.ts      # bubble state machine, sub-hook of useBotGame
├── components/bots/
│   ├── BotGameBubble.tsx       # fixed two-line bubble + optional Accept/Decline actions
│   ├── BotGameMobileBar.tsx    # Resign / Back / Forward / Flip (NOT BoardControls)
│   ├── BotClockStrip.tsx       # mobile: white left / black right, material beside each
│   ├── BotGameMobileLayout.tsx # replaces renderMobileLayout
│   └── BotGameDesktopLayout.tsx# replaces renderDesktopLayout
└── components/settings/
    └── BoardSoundsSwitch.tsx   # one component, rendered in BOTH App.tsx surfaces
```

Deleted: `components/bots/BotDrawOfferBanner.tsx` and its test
(`components/bots/__tests__/BotDrawOfferBanner.test.tsx`, 98 lines).

### Pattern 1: Pure copy table with compile-time exhaustiveness

**What:** `Record<PersonaId, string>` per trigger, so a missing persona is a type error.
**When to use:** every authored line table in this phase (D-08).
**Example:**

```ts
// Source: frontend/src/lib/trainBotCopy.ts:52-78 (verbatim shape to mirror)
export const LANDING_GREETINGS: Record<PersonaId, string> = {
  'attacker-800': 'Bzzz! Sting first, plan later. Today we sting the blunders from your own games.',
  // ... all 24 ids; omitting one is a compile error
  'wall-1800': "Quiet position, clear head. Let's think through the moments your games went wrong.",
};
```

`PersonaId` is a template-literal union `` `${Lowercase<Style>}-${Rung}` `` over 4 styles × 6 rungs
`[VERIFIED: frontend/src/lib/personas/personaRegistry.ts:72]`, so exhaustiveness is structural,
not convention. Recommended shape for ~9 triggers × 24 personas:
`Record<BotLineKey, Record<PersonaId, string>>` — one outer key per trigger, each inner table
exhaustive. This keeps each authored block readable and makes "add a trigger" a single new block.

### Pattern 2: Pure guard-clause resolver, extracted OUT of the component

**What:** a total function of already-computed values returning a discriminated result.
**When to use:** the trigger priority chain (Claude's discretion: game end > draw offer > swing >
threat > first capture > game start).
**Example:**

```ts
// Source: frontend/src/components/train/trainBubbleState.ts:56-63 (the precedent)
export function resolveBubbleState(input: ResolveBubbleStateInput): TrainBubbleState {
  if (input.hasVerdict) return { kind: 'verdict' };
  if (input.isGrading) return { kind: 'grading' };
  if (input.guessMade) return { kind: 'move' };
  if (input.introStep !== null) return { kind: 'intro', step: input.introStep };
  if (input.nudgeActive) return { kind: 'drop-nudge' };
  return { kind: 'prompt' };
}
```

The module header there states the rationale explicitly: extracting the resolution out of the
component (rather than inlining guard blocks in JSX) is "the mechanism that LOWERS the
component's own cyclomatic complexity while adding the intro/nudge states"
`[VERIFIED: frontend/src/components/train/trainBubbleState.ts:10-14]`. That is exactly the lever
this phase needs, given `BotsGame` sits at its ceiling.

### Pattern 3: Cross-hook callback option (the seam shape already in use)

**What:** `useBotGameEngineDispatch` takes behaviour it must trigger as an option callback, and
lists it in `runBotTurn`'s dependency array.
**When to use:** seam (B), the graded-score publication.
**Example (the existing precedent, same options object):**

```ts
// Source: frontend/src/hooks/useBotGameEngineDispatch.ts:198-207
  bumpConsecutiveLowScoreTurns: (scoreAtOrBelowThreshold: boolean) => number;
  applyDrawOfferUpdate: (
    score: number,
    chess: Chess,
    style: BotStyleParams,
    gameAlreadyOver: boolean,
  ) => void;
```

Add `onBotMoveGraded: (previousScore: number | null, score: number, ply: number) => void`
alongside them, destructure it (`:226-243`), call it inside the `if (grade)` block, and add it to
the deps array (`:513-534`). The callback must be a `useCallback` in `useBotGame` so
`runBotTurn`'s identity does not churn every render.

### Pattern 4: Single-fetch-then-prop-drill

**What:** one `useUserProfile()` call in `BotsPage`, results passed down as props.
**When to use:** the desktop `PlayerBar` needs `profile.current_strength.rating` (D-11).
`BotsPage` already calls `useUserProfile()` once (`Bots.tsx:610`) and prop-drills `isGuest` and
`playerName` into `BotsGame` (`Bots.tsx:203-209`). Add `currentStrength` to
`BotsGameProps` the same way — never a second hook call
`[VERIFIED: frontend/src/pages/Bots.tsx:610-626]`.

### Anti-Patterns to Avoid

- **Adding a conditional to `BotsGame`.** It measures complexity 25 against a ceiling of 25.
  Any new `if`, `&&`, `||`, `?:` or `??` in that function body fails `npm run lint`. All new
  branching goes into new components or pure modules.
- **Adding a prop-driven branch to `BoardControls`.** Same problem: 16 against a ceiling of 16.
- **A second `pool.grade()` call** to check whether the bot found the *best* punishment. D-03
  explicitly rejects this ("delta is delta"), and the engine budget is already deadline-managed
  per move (`computeThinkDeadlineMs`, `useBotGameEngineDispatch.ts:333`).
- **Deriving material swing from `move.captured` alone.** SEED-168 rejects it: an Attacker
  persona sacrifices on purpose and would apologise for it. The capture flag is only the D-04
  *tie-breaker* within an already-detected score swing.
- **Timers or animation on the bubble.** D-07 forbids both; the `nudgeNonce` remount trick in
  `TrainBotBubble` (`:56-59,127`) exists to *replay* an animation and has no analogue here.
- **`text-xs` anywhere new.** `text-sm` is the floor (`frontend/CLAUDE.md`), and both
  `PersonaGrid.test.tsx:155` and `ClockDisplay.test.tsx:62` already assert
  `innerHTML` does not contain `text-xs`. Copy that invariant test into the new components.
- **`data-umami-event` on anything internal.** Nothing in this phase leaves flawchess.com;
  no Umami wiring belongs here (`frontend/CLAUDE.md` outbound-link section).
- **Reformatting with Prettier.** The frontend has no Prettier; ESLint only.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "Is this bot piece attacked / under-defended?" | Own attacker enumeration over the FEN | `chess.attackers(square, color)` + `chess.get(square)` | Ships in chess.js 1.4.0 `[VERIFIED: node_modules/chess.js/dist/types/chess.d.ts:130]`; handles pins-aside pseudo-attacks, pawns, en-passant geometry |
| Material point values | A second value map | `computeMaterialDiff` in `src/lib/materialDiff.ts`, via `MaterialDisplay` | Already the single arithmetic owner, shared by `PlayerBar` and `ClockDisplay` `[VERIFIED: frontend/src/components/board/MaterialDisplay.tsx:33-37]` |
| Clock formatting | `m:ss` math in the new strip | `formatClockLabel` / `isLowTime` from `src/lib/chessClock.ts` | `ClockDisplay` explicitly "never reimplements clock math or formatting (D-07/UI-SPEC)" `[VERIFIED: frontend/src/components/bots/ClockDisplay.tsx:63-66]` |
| Persisting the sound preference | A new store / user field | `setMuted` / `useMuted` / `MUTE_KEY` | Flat key, guest-safe, `useSyncExternalStore`-backed, try/caught for private mode `[VERIFIED: frontend/src/lib/sounds.ts:187-202]` |
| Board fit under the new chrome | A hard-coded `calc(100dvh - N)` | `useFitBoardToViewport` | Its own header documents why a single constant fails and measures real chrome instead `[VERIFIED: frontend/src/hooks/useFitBoardToViewport.ts:5-15]` |
| Resign confirmation | A new dialog | The existing `Dialog` block in `GameControls.tsx:60-84` (`resign-confirm-dialog`, `board-btn-resign-confirm`) | Already two-step, already testid'd, already used by tests |
| Persisting a game the user navigates away from | Resign-on-leave logic | The existing snapshot write in `commitMove` + `ResumeGate` | `writeSnapshot` runs after every committed move (`useBotGameMoves.ts:232-234`); `ResumeGate` mounts on return (`Bots.tsx:564-571`) |
| Daily host rotation | A new RNG or date scheme | The `landingHost` day-index formula | `differenceInCalendarDays(date, EPOCH) % 24`, wrapped positive `[VERIFIED: frontend/src/lib/trainBotCopy.ts:117-121]` |

**Key insight:** the `/bots` game loop was built across Phases 169-215 with a deliberate
single-seam discipline — one commit path, one grade site, one snapshot writer, one enqueue site —
and each of those seams carries a comment explaining why a second one must never be added. Every
capability this phase needs already has such a seam; the work is wiring, not inventing.

---

## Runtime State Inventory

This is a UI/layout rework, not a rename, but it touches persisted browser state — so the
five categories are answered explicitly rather than skipped.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data (localStorage) | `flawchess_bot_sound_muted` (`MUTE_KEY`, `sounds.ts:78`); `flawchess_bot_game_snapshot:<owner>` (`botGameSnapshot.ts`); `flawchess_bot_pending_store:<owner>` (`botPendingStore.ts:21`) | **None.** No key is renamed and no shape changes. The mute key keeps its exact semantics; the SEED-167 switch is a new *reader/writer* of the same key, so a user who muted from the old in-game button stays muted |
| Live service config | None — this phase touches no backend, no n8n workflow, no dashboard | None — verified: no file under `app/`, `alembic/` or `deploy/` is in scope |
| OS-registered state | None | None |
| Secrets / env vars | None | None |
| Build artifacts | `frontend/src/generated/*` is regenerated by `scripts/gen_*.py`; **none of those registries is touched** by this phase (personas come from `generated/personaCalibration.ts`, which this phase only reads) | None — do not re-run `gen_*.py` |

**The one persisted-state consequence worth naming:** an in-progress game left via the new back
arrow survives only because `writeSnapshot` already ran on the last committed move
(`useBotGameMoves.ts:232-234`) — a game with **zero** committed plies leaves no snapshot and the
user lands back on the roster with nothing to resume. That is correct behaviour, not a bug, and
it is exactly what `isStorableBotGame` already encodes server-side.

---

## Common Pitfalls

### Pitfall 1: `BotsGame` and `BoardControls` are both AT their eslint complexity ceilings
**What goes wrong:** the very first conditional added to either function fails `npm run lint`
with no obvious remedy, mid-implementation.
**Why it happens:** the Phase 215 baseline region sets each listed file's ceiling to its
*measured value at baseline time*, deliberately, so "this region only ever SHRINKS"
`[VERIFIED: frontend/eslint.config.js:68-79]`. `src/pages/Bots.tsx` is pinned at 25
(`:148-154`) and `BoardControls.tsx` at 16 (`:80-90`). Measured this session:
`BotsGame` = complexity **25**, statements **37**; `BoardControls` = complexity **16**.
**How to avoid:** every new branch lands in a NEW file (new files are governed by the global
15/4/100 rule and start from zero). Specifically: the four-action mobile bar is a new
`BotGameMobileBar`, not a `BoardControls` prop; the layout renderers become new components,
not fatter helpers; the bubble's Accept/Decline gating lives in `BotGameBubble`.
**Warning signs:** `npm run lint` reporting `Function 'BotsGame' has a complexity of 26`.
Re-measure any file with
`npx eslint --no-inline-config --rule 'complexity: ["error", 1]' <path>` (the CLI flag defeats
the baseline block). **Never widen a ceiling** — frontend/CLAUDE.md: "a new breach must be
fixed, not baselined".

### Pitfall 2: The graded score arrives AFTER the bot's move is already on the board
**What goes wrong:** the bubble appears to lag — the bot moves, a beat passes, then the line
pops in. Or worse, the plan assumes the score is available synchronously at `commitMove`.
**Why it happens:** `commitMove(move, mover, debitMs)` runs at
`useBotGameEngineDispatch.ts:443`; `pool.grade(fen, [uci])` is fired at `:459-460` and its
`.then()` resolves arbitrarily later (the comment at `:461-472` documents that it "can resolve
arbitrarily late"). The move is committed first, deliberately, so the grade never blocks it.
**How to avoid:** design the bubble as a two-step upgrade: non-swing lines (game start, first
capture, threat, draw offer, game end) resolve synchronously at seam (A); swing lines arrive at
seam (B) and *replace* the bubble content if they win the priority chain. Do not render a
placeholder/spinner — D-07 forbids transient states.
**Warning signs:** a plan task that says "compute the swing inside `commitMove`".

### Pitfall 3: The previous score must be captured BEFORE the ref is overwritten
**What goes wrong:** the delta is always zero.
**Why it happens:** the site reads and writes the same ref in consecutive statements:

```ts
// Source: frontend/src/hooks/useBotGameEngineDispatch.ts:474-477
const grade = gradeMap.get(uci);
if (grade) {
  const score = evalToExpectedScore(grade.evalCp, grade.evalMate, mover);
  lastRootPracticalScoreRef.current = score;
```

**How to avoid:** read `lastRootPracticalScoreRef.current` into a local *before* line 477, and
pass both values to `onBotMoveGraded(previous, score, ply)`.

### Pitfall 4: The delta does not always span exactly one move pair
**What goes wrong:** a swing line fires for a swing that accumulated over several moves, and the
user cannot see what the bot is talking about — a direct board-truth (D-06) violation.
**Why it happens:** three documented gaps in the grade sequence. (a) The opening-book window is
explicitly suppressed: `if (fromBook) return;` at `:458`, with the comment that
`lastRootPracticalScoreRef` "therefore stays at its not-yet-evaluated `null` sentinel for the
whole book window" (`:445-457`). (b) A failed grade is swallowed by `.catch(() => {})` at
`:535-537` — "a failed grade leaves the prior score in place". (c) The staleness guard
`if (controller.signal.aborted) return;` at `:473` discards a whole turn's grade after a
new game / resign. (d) On resume, the ref is freshly `null`
`[VERIFIED: frontend/src/hooks/useBotGameSnapshot.ts:140]`, and `newGame()` resets it to `null`
`[VERIFIED: frontend/src/hooks/useBotGame.ts:614]`.
**How to avoid:** carry the **ply at which the previous score was recorded** alongside the score,
and only fire a swing line when `currentPly - previousPly === 2`. This is one extra ref and one
extra equality check in the pure resolver; it makes "exactly one move pair" structural.
**Warning signs:** a tease firing on the first move after the book window, or right after a
resumed game's first bot reply.

### Pitfall 5: `pb-20` cannot be deleted on mobile
**What goes wrong:** the bottom of the board slides under the fixed action bar.
**Why it happens:** CONTEXT's code-insight note says the `pb-20 sm:pb-4` clearance "goes away on
mobile once the bar is the page's own". It does not: `MobileBottomBar`'s board-controls branch
uses the *same* `MOBILE_BOTTOM_BAR_CLASSES` string — `fixed bottom-0 inset-x-0 … pb-safe`
`[VERIFIED: frontend/src/App.tsx:446-448]` — and renders `BoardControls` at `flex-1 h-12` inside
`px-2 py-2` (`:460-476`), i.e. ~64px plus the safe-area inset, still `position: fixed` and still
outside the page's flow. `useFitBoardToViewport` measures only the column's own height and top
(`useFitBoardToViewport.ts:17-21`), so it cannot see a fixed element.
**How to avoid:** keep a bottom clearance on the page root equal to the bar height. Note
`ProtectedLayout` already applies `pb-16 sm:pb-0` on `<main>` (`App.tsx:738`), so the page-root
`pb-20` is partly redundant and can be trimmed — but measure, do not delete.
**Warning signs:** on a 375×667 viewport, the last rank of the board sitting behind the bar.
**The real savings** (SC4) come from deleting the two in-page 48px rows — `BoardControls size="xl"`
(`Bots.tsx:479-491`) and the `GameControls` row (`:505-519`) — plus the draw-offer banner slot
(`:550-562`), roughly 110-130px, against a new cost of one avatar+bubble row.

### Pitfall 6: `PlayerBar` cannot render `~1850`
**What goes wrong:** the bot's desktop ELO renders as `(1850)` instead of the honest
tilde-prefixed `~1850`, silently contradicting the Phase 184 calibration-honesty rule.
**Why it happens:** `PlayerBar`'s prop is `rating: number | null`, rendered as
`<span className="text-muted-foreground"> ({rating})</span>`
`[VERIFIED: frontend/src/components/board/PlayerBar.tsx:21,65]`. But
`Persona.calibratedLabel` is a *string* like `"~1850"`, and the registry is explicit that this
"is what `PersonaCard`/`PersonaDetailSurface` render — never `~${rung}`"
`[VERIFIED: frontend/src/lib/personas/personaRegistry.ts:94-97]`.
**How to avoid:** add an additive optional prop, `ratingLabel?: string`, that wins over `rating`
when present. Additive means the four existing `PlayerBar` render sites
(`Analysis.tsx`, `AnalysisPlayerBar.tsx`, `AnalysisBoardStage.tsx`, `AnalysisTabs.tsx`) and
`PlayerBar.test.tsx` all keep compiling untouched. Apply the same treatment to the user side:
`~${Math.round(currentStrength.rating)}`, matching the roster row verbatim
(`PersonaGrid.tsx:128`).

### Pitfall 7: `celebrationHold` only holds after a human WIN
**What goes wrong:** the game-end line is authored, rendered, and then instantly covered by
`GameResultDialog` for every loss and every draw — two of the three outcomes.
**Why it happens:** `useWinCelebrationHold` returns `false` immediately for
"no outcome, loss, draw, or reduced-motion win"
`[VERIFIED: frontend/src/hooks/useWinCelebrationHold.ts:24-28,31-35]`. `Bots.tsx:581` passes
`open={!celebrationHold}` to the dialog. CONTEXT's discretion note ("the dialog already waits on
`celebrationHold`, so the line is visible during the hold") is therefore only true for wins.
**How to avoid:** decide deliberately at plan time. Cheapest correct option: render the game-end
line in the bubble anyway (it is visible behind/around the dialog and on the finished board after
dismissal) and accept that it is not read *first* on a loss. The alternative — extending the hold
to losses and draws — changes shipped behaviour and is arguably out of scope; flag it rather than
doing it silently.

### Pitfall 8: `trainBotCopy.test.ts` does not measure width; it counts characters
**What goes wrong:** a plan task says "assert the line wraps to at most two lines at 375px" and
the executor discovers jsdom reports zero layout.
**Why it happens:** the shipped invariant is a calibrated character budget, not a measurement:
`STEPPER_COPY_MAX_CHARS = 145`, whose doc comment records exactly how it was derived — "Calibrated
in the browser at 375x667 (plan 06 UAT) … the bubble copy is 204px wide, and the phone base font
renders `text-sm` at 16px/24px, so a line holds ~24 characters"
`[VERIFIED: frontend/src/lib/trainBotCopy.ts:185-199]`, asserted at
`trainBotCopy.test.ts:229`.
**How to avoid:** define `BOT_LINE_MAX_CHARS` the same way, with the same "the budget is a guard
on that calibration, not a substitute for it" caveat, and calibrate the actual number during UAT
at 375px against the *in-game* bubble width (which differs from Train's: the in-game bubble sits
beside a persistent avatar on phones, not under one). The other reusable invariant from that
file is the regex-over-every-entry loop (`trainBotCopy.test.ts:89-94`) — use it to assert no
entry contains an em-dash and no entry matches `/calculat|saw it coming|knew you'd/i`.

### Pitfall 9: The "never search" copy rule covers exactly 16 personas
**What goes wrong:** a line like "I calculated that three moves ago" ships for a rung-1000 bot
that made a single Maia policy call.
**Why it happens:** it is easy to forget which rungs search. The shipped constraint is stated
verbatim in the card this phase is replacing: "16 of the 24 personas run at `HUMAN_BLEND` (rungs
800-1400), where `selectBotMove` makes exactly ONE Maia policy call and never searches. So this
copy must never claim the bots 'calculate' or 'think'"
`[VERIFIED: frontend/src/components/bots/PersonaGrid.tsx:65-71]`.
**How to avoid:** the copy test regex above, applied to **every** table, not just the roster one.
Note the rule is about *claiming calculation*, not about tone — "That knight was hanging for a
whole move, you know" is fine because it describes the board, not the bot's reasoning.

### Pitfall 10: `LANDING_ROTATION_EPOCH` is module-private
**What goes wrong:** `import { LANDING_ROTATION_EPOCH }` fails to compile.
**Why it happens:** it is declared `const`, not `export const`
`[VERIFIED: frontend/src/lib/trainBotCopy.ts:84]`. `LANDING_HOST_IDS` (`:80`) is private too.
**How to avoid:** either export the epoch from `trainBotCopy.ts` (one-word change, no behaviour
risk) or declare an identical epoch in `botGameCopy.ts`. Prefer exporting so "the same bot greets
you on /train and /bots today" stays structurally true rather than coincidentally true — and add
a test asserting the two rotations agree for a given date.

### Pitfall 11: Adding a bubble row can shrink the mobile board, not grow it
**What goes wrong:** SC4 ("the board is measurably wider than before the phase") fails.
**Why it happens:** this exact regression is already documented for Train: `useFitBoardToViewport`
gained an `enabled` flag because "on phones the Train column under the board (bot bubble, action
row) is tall enough that a height fit shrank the board to its floor and left wide empty margins
beside it"
`[VERIFIED: frontend/src/hooks/useFitBoardToViewport.ts:42-49]`. Bots currently calls it with the
fit unconditionally on (`Bots.tsx:251-257`, no `enabled` arg) and a 240px floor.
**How to avoid:** measure the board width at 375×667 BEFORE and AFTER as an explicit UAT step.
If the bubble row tips the column past the fit, the levers in order of preference are: shrink the
in-game avatar (Train's phone avatar is 55px, `TrainBotBubble.tsx:32`; `ClockDisplay`'s in-game
one is 48px, `ClockDisplay.tsx:12`), trim the page-root vertical padding, or pass `enabled={false}`
and let the page scroll (Train's own resolution).

### Pitfall 12: `npm run lint` and `npm test` do not type-check
**What goes wrong:** a changed prop type or a renamed field compiles in tests (esbuild strips
types) and fails only in CI.
**Why it happens:** `npm run build` is `tsc -b && vite build`
`[VERIFIED: frontend/package.json:9]`; nothing else runs `tsc`.
**How to avoid:** `npm run build` is a mandatory verification step in every plan that touches a
shared type — and this phase touches `UseBotGameState`, `MobileBoardControls` and `PlayerBarProps`.
This also matters for `Bots.test.tsx`'s wholesale `useBotGame` mock, which returns an untyped
object literal (`Bots.test.tsx:144-189`): adding a field to `UseBotGameState` does **not** break
that mock at compile time, it silently yields `undefined` at runtime. Add the new field to the
mock deliberately.

### Pitfall 13: Deleting UI leaves exports knip will fail CI on
**What goes wrong:** `npm run knip` fails after `BotDrawOfferBanner` loses its only consumer.
**Why it happens:** knip detects dead *exports*; CI fails on findings (frontend/CLAUDE.md).
**How to avoid:** delete the component file and its test outright (D-12 says the banner is
retired), and remove the now-unused `Volume2`/`VolumeX`/`Tooltip` imports from `GameControls.tsx`.
Note the *inverse* is safe: `game.offerDraw`, `game.canOfferDraw` and `game.drawOfferPending`
are **properties of a returned object**, not module exports, so knip cannot see them and leaving
them wired in the hook (D-12) will not fail CI — the same reasoning `Bots.tsx:266-275` records
for `newGame`.

---

## Code Examples

### The exact swing seam (verified current source)

```ts
// Source: frontend/src/hooks/useBotGameEngineDispatch.ts:458-478 (current, unmodified)
        if (fromBook) return;
        pool
          .grade(fen, [uci])
          .then((gradeMap) => {
            if (controller.signal.aborted) return;
            const grade = gradeMap.get(uci);
            if (grade) {
              const score = evalToExpectedScore(grade.evalCp, grade.evalMate, mover);
              lastRootPracticalScoreRef.current = score;
              // ← insert: capture the PREVIOUS value above this line, then
              //   onBotMoveGraded(previous, score, chessRef.current.history().length)
              if (style) { /* resign + draw-offer gates, unchanged */ }
            }
          })
          .catch(() => {
            // Best-effort only — a failed grade leaves the prior score in place.
          });
```

Facts this pins down for the planner:

- `fen` is the position **before** the bot's move (`:326`), and `mover` is the bot's color
  (`:327`), so `evalToExpectedScore(..., mover)` yields a **bot-POV** value.
- `evalToExpectedScore` returns `1 / (1 + exp(-K * sign * cp))`, i.e. strictly in **(0, 1)**,
  with `0.5` returned when both `evalCp` and `evalMate` are null
  `[VERIFIED: frontend/src/lib/liveFlaw.ts:92-107]`. Mate is clamped to ±`MATE_CP_EQUIVALENT`
  *before* the sigmoid, so a mate-in-N does not produce a 0/1 discontinuity mid-scale.
- Therefore `delta = score - previous`: **positive = the bot improved** (earned tease, D-03);
  **negative and ≤ −0.20 = swing against the bot** (D-04 split by capture).
- The grade is white-POV at the pool boundary (`workerPool.ts:124-125`) and is converted to
  mover-POV by `evalToExpectedScore` — do not double-flip.

### The move-pair facts seam

```ts
// Source: frontend/src/hooks/useBotGameMoves.ts:149-163 (current, unmodified)
  const commitMove = useCallback(
    (move: Move, mover: MoverColor, debitMs: number): void => {
      const chess = chessRef.current;
      const incrementMs = incrementSeconds * 1000;

      // D-07 (Phase 183): a bot's outgoing draw offer expires the instant the
      // USER commits their next move — checked here (not in `attemptMove`)
      // because this is the single seam both a user move AND a bot move reach
      if (mover === userColor && botDrawOfferRef.current) {
        botDrawOfferRef.current = false;
        setBotDrawOffer(false);
      }
```

`move` is a full chess.js `Move`: `.captured?: PieceSymbol`, `.san`, `.from`, `.to`, `.piece`,
`.color`, plus `.before`/`.after` FENs and `isCapture()`
`[VERIFIED: frontend/node_modules/chess.js/dist/types/chess.d.ts:53-76]`. `moveHistory` on
`UseBotGameState` is `string[]` of **SAN only** (`useBotGame.ts:191`, written at
`useBotGameMoves.ts:190`) — it carries no capture flag, which is why the voice hook must read
the facts at `commitMove`, not from `moveHistory`.

The `mover === userColor` guard at `:156` is the exact predicate for "the player has committed a
move" (D-07 bubble clearing). Note it deliberately excludes the bot's own commit so a bot move
cannot clear a line it is about to set.

### The threat probe (D-05), engine-free

```ts
// New: frontend/src/lib/botThreat.ts — sketch, built on the verified chess.js 1.4.0 API
import { Chess } from 'chess.js';
import type { Color, PieceSymbol, Square } from 'chess.js';

/** Point values for the under-defended comparison only — never material scoring
 *  (that belongs to lib/materialDiff.ts). King is excluded: it is never "hanging". */
const THREAT_PIECE_VALUE: Record<Exclude<PieceSymbol, 'k'>, number> = {
  p: 1, n: 3, b: 3, r: 5, q: 9,
};

/** True when any piece of `botColor` is attacked and either undefended, or
 *  attacked by a strictly cheaper piece. Pure: reads the live board only. */
export function hasVisibleThreatOnBot(chess: Chess, botColor: Color): boolean { /* … */ }
```

The two calls it needs both exist in this version: `attackers(square, attackedBy?): Square[]` and
`get(square): Piece | undefined`
`[VERIFIED: frontend/node_modules/chess.js/dist/types/chess.d.ts:118,130]`. Iterate squares via
the exported `SQUARES` array (`:79`) or `chess.board()`. **Timing note:** D-05 says the probe runs
"after the player's move" but the line fires "after the bot's reply" — so the flag must be
computed at seam (A) on the *player's* commit and latched until seam (B). Computing it after the
bot has replied would test a different position and could announce a threat the bot just
neutralised.

### The mobile bar payload extension

```ts
// Source: frontend/src/lib/mobileBoardControls.ts:15-33 (current)
export interface MobileBoardControls {
  onBack: () => void;
  onForward: () => void;
  onReset: () => void;
  onFlip: () => void;
  canGoBack: boolean;
  canGoForward: boolean;
  canReset: boolean;
}
```

Recommended change: make `onReset`/`canReset` optional and add `onResign?: () => void`. The
`NOOP_PAYLOAD` defaults at `:25-33` and the destructure-with-defaults at `:63-71` already handle
absent fields cleanly — `usePublishMobileBoardControls` destructures every field with a NOOP
fallback precisely so a partial payload is safe. Then in `MobileBottomBar` (`App.tsx:458-479`),
branch on `boardControls.onResign != null` to render `BotGameMobileBar` instead of
`BoardControls` (`MobileBottomBar` measures complexity 2 against App.tsx's ceiling of 21, so it
has ample headroom).

**Other consumers that must keep working:** exactly one production publisher,
`TrainSolveScreen.tsx:858` (free-move mode), and one test probe, `App.test.tsx:145-158`
`[VERIFIED: grep across frontend/src]`. The test probe declares its own inline prop type with all
seven fields, so making two of them optional does not break it.

### The sound switch (SEED-167)

```tsx
// New: frontend/src/components/settings/BoardSoundsSwitch.tsx — one component, two call sites
import { Switch } from '@/components/ui/switch';
import { useMuted, setMuted } from '@/lib/sounds';

export function BoardSoundsSwitch(): ReactElement {
  const muted = useMuted();
  return (
    <div className="flex items-center justify-between px-3 py-2">
      <span className="text-sm text-foreground">Board sounds</span>
      <Switch
        checked={!muted}
        onCheckedChange={(on) => setMuted(!on)}
        aria-label="Board sounds"
        data-testid="settings-board-sounds"
      />
    </div>
  );
}
```

The `checked` / `onCheckedChange` / `aria-label` / `data-testid` quartet matches all three
existing `Switch` call sites verbatim (`TrainScheduleSettings.tsx:240-244`,
`MaiaHumanPanel.tsx:162-166`, `EngineToggleHeader.tsx:34-38`). Render it in `MobileMoreDrawer`
above the `drawer-logout` divider (`App.tsx:580-590`, complexity 10 vs ceiling 21) and in
`NavHeader`'s account `div` beside `nav-logout` (`App.tsx:352-368`, complexity 7). Note the
inversion: `useMuted()` is "muted", the switch reads "Board sounds" — get the polarity test in.

**SEED-167 completeness is confirmed:** `setMuted` has exactly **one** production call site in
the whole frontend today, `Bots.tsx:373`, reached from `GameControls`' `board-btn-mute`
(`GameControls.tsx:122-131`). Train's was already removed in Phase 222 and
`TrainSolveScreen.test.tsx:1345-1353,2626` asserts it stays gone
`[VERIFIED: grep -rn "setMuted|useMuted|board-btn-mute" frontend/src]`. So removing the Bots
button without adding the switch would leave zero ways to mute — which is precisely why the seed
is a hard prerequisite.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bot copy per outcome bucket, bot identity = face + name only | Per-persona copy where the voice is the point | Phase 222 D-06's scoped exception for `LANDING_GREETINGS` (2026-09-14); this phase generalises it | The "one exception" comment in `trainBotCopy.ts:11-14` should be updated, not contradicted |
| Bot game bottom controls: two 48px in-page rows | Fixed bar via `usePublishMobileBoardControls` | Quick 260809-g0n (Train free-move), Phase 208 (/analysis) | The takeover pattern is proven on two surfaces already |
| Draw offer as an inline sibling banner | Inside the bot's own bubble | This phase (D-12) | The banner's "deliberately NOT a Dialog, play continues underneath" property (`BotDrawOfferBanner.tsx:16-22`) must survive the move |
| Per-page mute toggles | One settings-surface switch | SEED-167 (amended 2026-09-15) | Phase 222 already removed Train's; this removes the last one |
| `~${rung}` ELO display | `calibratedLabel` from generated calibration | Phase 184 (CAL-04/05) | Never render `~${persona.rung}` in the new `PlayerBar` row |

**Deprecated / outdated:**
- `BotDrawOfferBanner` — deleted by D-12.
- `GameControls`' `muted` / `onToggleMute` / `onOfferDraw` / `canOfferDraw` / `drawCooldownActive`
  props — all five go with the removed buttons; what remains is the Resign trigger + confirm
  dialog, which arguably becomes `ResignButton` rather than `GameControls`.
- `Move.flags` (string) is deprecated in chess.js and scheduled for removal in 2.0
  `[VERIFIED: node_modules/chess.js/dist/types/chess.d.ts:60-65]` — use the descriptor methods
  (`isCapture()`) or `move.captured` instead.
- ROADMAP §Phase 223's "Swings are detected from the WDL delta" and success criterion 3's
  "swing detection is WDL-based" are **superseded by CONTEXT D-01** (Stockfish practical-score
  delta). The *intent* of criterion 3 is unchanged and still testable: an Attacker sacrifice must
  not trigger the self-deprecating line, which the score-delta signal satisfies for the same
  reason the WDL one would. The planner should restate criterion 3 in D-01's terms.

---

## Project Constraints (from CLAUDE.md)

From the root `CLAUDE.md`:

- **No magic numbers** — `BOT_LINE_SWING_THRESHOLD`, `BOT_LINE_MIN_SPACING_MOVES`,
  `BOT_LINE_MAX_CHARS`, avatar size classes, and the threat piece values must all be named
  constants with a doc comment recording how the value was chosen.
- **Never use bare `str` for a fixed set of values** (TS analogue: no loose `string` unions
  by convention) — `BotLineKey` must be a literal union / discriminated union, not `string`.
- **Nesting depth** soft 3 / hard 4; **logic LOC** soft 100 / hard 200; **cognitive complexity**
  ≤ 15 per function. The JSX return tree does not count toward logic LOC.
- **Refactor bloated code on sight** — but "don't refactor outside a GSD phase plan without
  flagging it". Splitting `BotsGame` is *in* scope (the layout rework requires it); refactoring
  `useBotGame.ts` (816 lines) is not.
- **Don't split just to fit a signature** — a context dataclass with <3 fields and one reader is
  over-engineering. The voice hook's inputs are genuinely multi-field; the layout components are
  genuinely independently readable. Both splits are justified.
- **Use em-dashes sparingly** in UI copy — and D-08 forbids them outright in the bot lines.
- **Communication style** — flag over-engineering and scope creep; disagree and commit.
- **Version control** — feature work branches off `main`, squash-merges back locally; the full
  pre-merge gate runs once before the squash-merge, not per commit.
- **Changelog is not optional** — append user-facing bullets under `## [Unreleased]` in
  `CHANGELOG.md` when the phase merges. The existing `[Unreleased]` block already has Train
  entries from Phase 222 `[VERIFIED: CHANGELOG.md:9-19]`.

From `frontend/CLAUDE.md`:

- **Theme constants in `theme.ts`** — any new semantic color goes there, never inline.
- **`noUncheckedIndexedAccess` is enabled** — `RECORD[id]` returns `T | undefined`. For an
  exhaustive `Record<PersonaId, string>` indexed by a `PersonaId`, TS still requires narrowing
  unless you use `!` or `?? fallback`; `landingHost` uses an explicit
  `if (id === undefined) return tank;` guard (`trainBotCopy.ts:120`). Copy that.
- **Knip runs in CI** — remove exports along with features (see Pitfall 13).
- **Complexity rules gate `npm run lint`** at `error`: `complexity` 15, `max-depth` 4,
  `max-statements` 100. "A new breach must be fixed, not baselined."
- **Minimum font size is `text-sm`** — including badges and metadata. Only `InfoPopover` bodies
  may use `text-xs`.
- **Always apply changes to mobile too** — search for duplicated markup before considering a
  change complete.
- **Primary vs secondary buttons** — `variant="default"` for the single primary CTA (Accept in
  the draw bubble), `variant="brand-outline"` for secondary (Decline, Resign). Never
  `variant="secondary"`.
- **`data-testid` on every interactive element**, kebab-case, component-prefixed; `aria-label`
  on every icon-only button; semantic HTML (`<button>`, `<nav>`, `<header>`).
- **Naming convention:** `btn-{action}`, `board-btn-{action}`, `{component}-{element}-{id?}`.
  Suggested new ids: `bot-bubble`, `bot-bubble-copy`, `btn-accept-bot-draw` /
  `btn-decline-bot-draw` (reuse the banner's existing ids so those assertions survive the move),
  `board-btn-resign` (reuse), `bots-back`, `bot-clock-white` / `bot-clock-black`,
  `settings-board-sounds`, `bots-welcome-bubble`.
- **Global TanStack Query errors** are already captured centrally — no `Sentry.captureException`
  in components using `useQuery`. Nothing in this phase does manual fetch, so no new Sentry
  wiring is needed.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node + npm | frontend build/test/lint | ✓ | as installed (`node_modules` present and resolvable) | — |
| `chess.js` | threat probe, capture flag | ✓ | 1.4.0 | — |
| `radix-ui` `Switch` | sound switch | ✓ | via `radix-ui` ^1.4.3, wrapped at `ui/switch.tsx` | — |
| vitest + jsdom | unit/component tests | ✓ | project-wide config in `vite.config.ts` | — |
| Backend / PostgreSQL / Docker | — | n/a | — | **Not required.** This phase touches no backend file, no migration, no API |
| A 375px-wide device or browser emulation | SC4 and the copy-budget calibration | human step | — | None — this is UAT, not automatable (memory: run human-action checkpoints yourself where possible) |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | vitest (config block in `frontend/vite.config.ts:89-94`), `@testing-library/react`, jsdom via per-file `// @vitest-environment jsdom` |
| Config file | `frontend/vite.config.ts` (`test: { testTimeout: 20_000, hookTimeout: 30_000, setupFiles: ['src/vitest.setup.ts'] }`) |
| Quick run command | `cd frontend && npm test -- --run <path>` |
| Full suite command | `cd frontend && npm test -- --run` |
| Type check (NOT covered by lint/test) | `cd frontend && npm run build` (`tsc -b && vite build`) |
| Lint (complexity gate) | `cd frontend && npm run lint` |

**Do not add per-file timeouts.** The project-wide ceilings exist specifically to end that
pattern (`vite.config.ts:76-86`), and per-file band-aids are a known recurring flake source.
Heavy page mounts (`Bots.test.tsx`) additionally raise testing-library's own `asyncUtilTimeout`
via `configure({ asyncUtilTimeout: 10000 })` (`Bots.test.tsx:44-52`) — copy that line into any
new heavy page test.

### Phase Requirements → Test Map

Requirement IDs are minted at planning time (BOTVOICE-01..); the rows below map to the ROADMAP's
success criteria 1-7.

| SC | Behavior | Test Type | Automated Command | File Exists? |
|----|----------|-----------|-------------------|--------------|
| 1 | Every persona has a line for every trigger; a missing entry is a compile error | type + unit | `npm run build` and `npm test -- --run src/lib/__tests__/botGameCopy.test.ts` | ❌ Wave 0 |
| 1 | No line exceeds the two-line character budget; no em-dash; no "calculated"/"saw it coming" | unit | `npm test -- --run src/lib/__tests__/botGameCopy.test.ts` | ❌ Wave 0 |
| 2 | Resolver never returns a swing line for a non-adjacent ply pair, during book, or on a failed grade | unit (fabricated sequences) | `npm test -- --run src/lib/__tests__/botLineTrigger.test.ts` | ❌ Wave 0 |
| 2 | Bubble clears on the player's next committed move and never renders on the player's turn | component | `npm test -- --run src/pages/__tests__/Bots.test.tsx` | ✅ extend |
| 3 | A negative delta with a player capture yields the punished-mistake key; without one, the compliment; a positive delta yields the tease; sub-threshold yields `null` | unit | `npm test -- --run src/lib/__tests__/botLineTrigger.test.ts` | ❌ Wave 0 |
| 3 | An Attacker sacrifice (bot captures nothing, loses material, score stays flat) produces no apology | unit (fabricated score sequence) | same file | ❌ Wave 0 |
| 4 | Mobile layout renders top bar, bubble, board, clock strip; publishes a 4-action payload; no main nav | component | `npm test -- --run src/pages/__tests__/Bots.test.tsx` + `src/App.test.tsx` | ✅ extend both |
| 4 | Board is measurably wider at 375×667 | **manual UAT** | — (browser, 375×667; record before/after px) | manual |
| 5 | Desktop renders two `PlayerBar` rows and the side-column bubble; Accept/Decline call through on both breakpoints | component | `npm test -- --run src/pages/__tests__/Bots.test.tsx` | ✅ extend |
| 6 | Roster shows the welcome bubble, the engine `InfoPopover` and the rating row; guests see the bubble without the row | component | `npm test -- --run src/components/bots/__tests__/PersonaGrid.test.tsx` | ✅ extend |
| 6 | Host rotation is deterministic per day and agrees with Train's for the same date | unit | `npm test -- --run src/lib/__tests__/botGameCopy.test.ts` | ❌ Wave 0 |
| 7 | Sound toggles from both settings surfaces and persists; zero mute controls remain in a game | component | `npm test -- --run src/App.test.tsx` + `src/pages/__tests__/Bots.test.tsx` | ✅ extend |
| all | No sub-`text-sm` utilities in any new component | component | per-component `innerHTML` assertion (pattern at `PersonaGrid.test.tsx:155`) | ❌ Wave 0 |
| all | Complexity gate green; types green | gate | `npm run lint` && `npm run build` | ✅ |

### Sampling Rate

- **Per task commit:** `cd frontend && npm test -- --run <the touched test file>` plus
  `npm run lint` when the change adds any branching.
- **Per wave merge:** `cd frontend && npm run lint && npm run build && npm test -- --run`.
- **Phase gate (before `/gsd-verify-work`):** the full frontend leg of the pre-merge gate —
  `cd frontend && npm run lint && npm run build && npm test -- --run` — green, plus the manual
  375×667 board-width measurement and the copy-budget calibration.

Backend gate steps (`ruff`, `ty`, `pytest`) are unaffected by this phase, but the project's
pre-merge gate runs them all before the squash-merge to `main` regardless.

### Wave 0 Gaps

- [ ] `frontend/src/lib/__tests__/botGameCopy.test.ts` — covers SC1, SC6 (exhaustiveness loop over
      `Object.keys(PERSONA_REGISTRY)`, char budget, forbidden-phrase regex, rotation determinism)
- [ ] `frontend/src/lib/__tests__/botLineTrigger.test.ts` — covers SC2, SC3 (fabricated
      `(prevScore, prevPly, score, ply, capturedByPlayer, threatPending, …)` sequences)
- [ ] `frontend/src/lib/__tests__/botThreat.test.ts` — covers D-05 (hanging piece yes/no,
      defended-by-equal no, attacked-by-cheaper yes, king excluded) from fixed FENs
- [ ] `frontend/src/components/bots/__tests__/BotGameBubble.test.tsx` — covers D-07 (fixed
      two-line height class present, draw actions render only when the offer is live, no `text-xs`)
- [ ] `frontend/src/components/bots/__tests__/BotGameMobileBar.test.tsx` — covers D-10 (exactly
      four actions, each fires its callback once, resign opens the confirm dialog)
- [ ] `frontend/src/components/settings/__tests__/BoardSoundsSwitch.test.tsx` — covers SC7
      (polarity: switch ON ⇒ `setMuted(false)`)
- [ ] Framework install: **none needed** — vitest, jsdom and testing-library are all present

**Existing tests that will need updating (not new files):**
`src/pages/__tests__/Bots.test.tsx` (1161 lines — the `bot-draw-offer-banner` block at :635-675,
the `pb-20` assertion at :1148-1161, and the `useBotGame` mock object at :164-188 which needs the
new field); `src/App.test.tsx` (the board-controls describe at :927+); `src/components/bots/__tests__/PersonaGrid.test.tsx`
(the `bots-intro-card` prose assertion at :144-153); `src/components/bots/__tests__/BotDrawOfferBanner.test.tsx`
(**delete with the component**); `src/components/bots/__tests__/ClockDisplay.test.tsx` (only if
`ClockDisplay` itself changes — it may survive untouched as the desktop side-column avatar row).

---

## Security Domain

`security_enforcement` is not set to `false` in `.planning/config.json`, so this section is
included. This is a frontend-only, copy-and-layout phase with no new network surface.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth code touched; `useAuth().logout` is only rendered beside the new switch, not modified |
| V3 Session Management | no | No token handling; the guest-refresh effect in `ProtectedLayout` is untouched |
| V4 Access Control | no | `/bots` is explicitly never nav-gated (`App.test.tsx:231-255` pins this); the roster bubble renders for guests by design (D-13) |
| V5 Input Validation | n/a (no user input) | All bot copy is **static authored strings** compiled into the bundle. There is no user-supplied text in any new render path. React escapes by default and no `dangerouslySetInnerHTML` is introduced |
| V6 Cryptography | no | None |
| V7 Error Handling & Logging | yes (unchanged) | The grade continuation's `.catch(() => {})` is intentional best-effort (`useBotGameEngineDispatch.ts:535-537`); do not add a Sentry capture there — a failed grade is an expected transient, and the file already captures genuine bugs with `tags: { source: 'bot-game' }` |
| V13 API | no | No new endpoint, no new request |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via interpolated copy | Tampering | Static `Record<PersonaId, string>` tables only; React's default escaping; no `dangerouslySetInnerHTML` (grep the new components before merge) |
| Information disclosure through the bot's voice | Information Disclosure | This is the phase's *central* threat and D-06 is its control: the board-truth rule forbids any line derived from engine knowledge not already visible. The `botLineTrigger` unit tests are the enforcement mechanism |
| localStorage tampering (a hand-edited snapshot) | Tampering | Already handled: `restoreChess` replay is wrapped per-ply in try/catch and stops at the last legal ply (`useBotGame.ts:266-280`); `isValidPendingEntry` shape-validates (`botPendingStore.ts:52-60`). Nothing in this phase weakens either |
| Guest data leakage across browser sessions | Information Disclosure | `MUTE_KEY` is a flat, non-PII preference by design ("Works for guests — the key is flat, not scoped to a user email", `sounds.ts:185-186`). The new switch does not change its scope |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ~0.20 expected-score points is the right swing threshold and fires "a couple of times per game at most" | D-02 / Pitfall 4 | Too chatty or too silent. Mitigation is already in CONTEXT: it is a named constant tuned in UAT. Not verifiable without play-testing |
| A2 | The two-line character budget lands near Train's 145, adjusted for the in-game bubble's different width | Pitfall 8 | Lines overflow to three at 375px. Must be calibrated in a real browser during UAT, exactly as `STEPPER_COPY_MAX_CHARS` was |
| A3 | Removing the two 48px rows + the banner slot nets a wider mobile board than the new bubble row costs | Pitfall 11 / SC4 | SC4 fails. Directly measurable in UAT; levers listed in Pitfall 11 |
| A4 | A minimum spacing of 3 bot moves between non-terminal lines reads as "not chatty" | Claude's discretion | Tuning knob; make it a named constant |
| A5 | Users read the same daily host on /train and /bots as a feature, not a bug | Claude's discretion | Purely cosmetic; reversible by swapping the epoch |
| A6 | Rendering the game-end line in the bubble is acceptable on a loss/draw even though `GameResultDialog` opens immediately | Pitfall 7 | The line goes unread for 2 of 3 outcomes. **Needs a user decision** — do not silently extend `celebrationHold` |
| A7 | `BotGameMobileBar` rendering inside `MobileBottomBar` (rather than the page) is the right home for the Resign action | Pattern / D-10 | Alternative is a page-owned fixed bar, duplicating `MOBILE_BOTTOM_BAR_CLASSES`. The chosen route reuses the proven seam |
| A8 | `GameControls` becomes a resign-only component rather than being deleted | State of the Art | Naming only; no behavioural risk |

---

## Open Questions

1. **The game-end line on a loss or a draw (A6).**
   - What we know: `celebrationHold` is `true` only after a human win, for
     `WIN_CELEBRATION_HOLD_MS = 1300` (`useWinCelebrationHold.ts:24-35`); `GameResultDialog`
     opens on `!celebrationHold` (`Bots.tsx:581`).
   - What's unclear: whether the owner wants the loss/draw line read before the dialog.
   - Recommendation: ship the line in the bubble unconditionally and change no timing. Surface
     this at plan review as an explicit accepted trade-off, since CONTEXT's discretion note
     assumed the hold applied to all outcomes.

2. **Whether the roster rotation should share `LANDING_ROTATION_EPOCH` or own one.**
   - What we know: the epoch and the id list are both module-private (`trainBotCopy.ts:80,84`).
   - What's unclear: whether "same bot on both pages today" is a promise worth a shared export.
   - Recommendation: export the epoch and add a cross-module test asserting agreement. One-word
     change, makes the intent structural.

3. **Does `ClockDisplay` survive?**
   - What we know: mobile drops the name/style/ELO row entirely (D-11), so the mobile clock strip
     is new. Desktop replaces the two `ClockDisplay` cards with `PlayerBar` rows (D-11) but keeps
     "its side column with the avatar" (SEED-168), which `ClockDisplay` is currently the only
     renderer of.
   - What's unclear: whether the desktop side column keeps a trimmed `ClockDisplay` (avatar +
     name, no clock) or whether the new `BotGameBubble` carries the avatar itself.
   - Recommendation: `BotGameBubble` carries the avatar (it needs one anyway for the tail to point
     at), and `ClockDisplay` is removed from the game view. Then `ClockDisplay.tsx` and its test
     become dead — delete both, or keep them only if a surviving caller is identified. Check knip.

4. **Exact trigger count and therefore the authored-line budget.**
   - What we know: SEED-168 estimates 8-10 lines per bot (~200-240 total). The locked trigger list
     is: game start, first capture, earned tease, punished mistake, nice move, player threat, draw
     offer, win, loss, draw = **10**, plus a separate `ROSTER_GREETINGS` = 11 tables × 24.
   - What's unclear: whether win/loss/draw are three tables or one with a sub-key.
   - Recommendation: 11 flat `Record<PersonaId, string>` tables. Flat beats nested for authoring
     and for the test loop. That is 264 authored strings — plan the copy authoring as its own
     plan (or two), not as a task inside a layout plan.

---

## Sources

### Primary (HIGH confidence)
All findings below were read directly from the working tree at
`/home/aimfeld/Projects/Python/flawchess` on 2026-09-15:

- `frontend/src/hooks/useBotGameEngineDispatch.ts` (557 lines) — grade continuation, options
  shape, book suppression, abort guard
- `frontend/src/hooks/useBotGame.ts` (816 lines) — `UseBotGameState` field-by-field
- `frontend/src/hooks/useBotGameMoves.ts` (337 lines) — `commitMove`, the single commit seam
- `frontend/src/hooks/useBotGameSnapshot.ts`, `useBotGameDrawOffer.ts`, `useWinCelebrationHold.ts`,
  `useFitBoardToViewport.ts`
- `frontend/src/pages/Bots.tsx` (819 lines) — both render helpers, controls row, banner slot
- `frontend/src/App.tsx` (1042 lines) — `MobileBottomBar`, `MobileMoreDrawer`, `NavHeader`,
  `ProtectedLayout`
- `frontend/src/lib/` — `mobileBoardControls.ts`, `sounds.ts`, `playActive.ts`, `liveFlaw.ts`,
  `trainBotCopy.ts`, `theme.ts`, `devClock.ts`, `botPendingStore.ts`, `botDrawGate.ts`,
  `botGameEnd.ts`, `playerName.ts`, `personas/personaRegistry.ts`
- `frontend/src/components/` — `train/TrainBotBubble.tsx`, `train/trainBubbleState.ts`,
  `train/TrainStartScreen.tsx`, `board/PlayerBar.tsx`, `board/BoardControls.tsx`,
  `board/MaterialDisplay.tsx`, `bots/ClockDisplay.tsx`, `bots/GameControls.tsx`,
  `bots/BotDrawOfferBanner.tsx`, `bots/PersonaGrid.tsx`, `bots/chipStyles.ts`,
  `bots/ResumeGate.tsx`, `ui/switch.tsx`, `ui/info-popover.tsx`
- `frontend/src/lib/engine/workerPool.ts` — `grade()` contract and white-POV convention
- `frontend/eslint.config.js` — complexity baseline region; ceilings re-measured with
  `npx eslint --no-inline-config --rule 'complexity: ["error", 1]' <path>`
- `frontend/vite.config.ts`, `frontend/package.json` — test/lint/build commands and timeouts
- `frontend/node_modules/chess.js/dist/types/chess.d.ts` + `package.json` — version 1.4.0,
  `attackers`/`isAttacked`/`Move` shape
- Existing tests read: `src/pages/__tests__/Bots.test.tsx`, `src/App.test.tsx`,
  `src/components/bots/__tests__/PersonaGrid.test.tsx`,
  `src/components/bots/__tests__/ClockDisplay.test.tsx`,
  `src/lib/__tests__/trainBotCopy.test.ts`
- Planning docs: `223-CONTEXT.md`, `SEED-168`, `SEED-167`, `ROADMAP.md §Phase 223`,
  `CLAUDE.md`, `frontend/CLAUDE.md`, `.planning/config.json`, `CHANGELOG.md`

### Secondary (MEDIUM confidence)
- None — no web research was required. Every question this phase raises is answerable from the
  repository, and no external library is being adopted.

### Tertiary (LOW confidence)
- None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — zero new packages; every module cited by path and line from the
  installed tree
- Architecture: **HIGH** — both seams (`commitMove`, the grade continuation) read in full;
  the callback-option pattern is copied from two existing options on the same interface
- Pitfalls: **HIGH** for 1-10 and 12-13 (each backed by a measured value or a quoted source
  comment); **MEDIUM** for 11 (the board-width outcome depends on final chrome heights and
  needs UAT)
- Copy budget: **MEDIUM** — the *mechanism* is verified (a calibrated char count, not a width
  test); the *number* must be re-calibrated at 375px for this bubble
- Validation architecture: **HIGH** — commands verified from `package.json` and `vite.config.ts`;
  existing test files enumerated by grep

**Research date:** 2026-09-15
**Valid until:** 2026-10-15 (30 days — in-repo findings against a stable tree; re-verify the
eslint ceilings and the `Bots.tsx` complexity measurement if any other phase touches `/bots`
first)
