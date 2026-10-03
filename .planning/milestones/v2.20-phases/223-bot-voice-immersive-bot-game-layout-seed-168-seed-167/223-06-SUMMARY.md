---
phase: 223-bot-voice-immersive-bot-game-layout-seed-168-seed-167
plan: 06
subsystem: ui
tags: [react, desktop-layout, bot-game, bot-voice, uat, testing-library, eslint-complexity]

requires:
  - phase: 223-04
    provides: "botLineTrigger precedence chain and useBotGameVoice, which the UAT rounds re-tuned (centipawn swing, latched punish)"
  - phase: 223-05
    provides: "BotGameMobileLayout, BotDrawOfferActions and the four-action bar the desktop half mirrors"
provides:
  - "PlayerBar: additive ratingLabel, clockActive, clockUrgent props and the ClockBadge sub-component (board-colour clock badge, red on low time)"
  - "BotGameDesktopLayout.tsx: PlayerBar rows above and below the board, bubble at the top of the side column with the draw offer inside it"
  - "botPlayerRow.ts: resolvePlayerRow, the one place that turns persona/user + orientation into the two PlayerBar prop sets, shared by both breakpoints"
  - "Swing detection in bot-POV centipawns (BOT_LINE_SWING_THRESHOLD_CP = 150, clamp 1000, swing spacing 2) with a latched 'punished-mistake' / 'got-away' / 'nice-move' settle"
  - "GameResultDialog carries the persona avatar and the terminal line; useWinCelebrationHold waits out CONFETTI_DURATION_MS on a win"
  - "ROSTER_HUMAN_LIKE_LINE appended to every roster greeting; engine popover leads with what the bots are"
  - "ClockDisplay, BotClockStrip, botThreat, currentStrengthCopy and BoardSoundsSwitch deleted with their tests"
affects: []

actuals:
  tokens: 0
  tasks: 4
  commits: 10
  plan_head_before: c32af11f3bd22d94099324071752345eeecf3387

tech-stack:
  added: []
  patterns:
    - "Layout components own every layout branch (orientation ordering, guest gate, persona-less fallback) so BotsGame's body gains none: measured complexity 17 against the pinned 25."
    - "A swing against the bot LATCHES and settles on the next observable event (player capture, full recovery, no recovery) instead of speaking on the bot's own grade, so the bot never announces a blunder before the player has touched it."
    - "One shared product claim (ROSTER_HUMAN_LIKE_LINE) appended after the per-persona greeting rather than written into 24 voices."

key-files:
  created:
    - frontend/src/components/bots/BotGameDesktopLayout.tsx
    - frontend/src/components/bots/botPlayerRow.ts
  modified:
    - frontend/src/components/board/PlayerBar.tsx
    - frontend/src/components/board/__tests__/PlayerBar.test.tsx
    - frontend/src/components/board/BoardControls.tsx
    - frontend/src/components/board/MaterialDisplay.tsx
    - frontend/src/components/bots/BotGameBubble.tsx
    - frontend/src/components/bots/BotGameMobileBar.tsx
    - frontend/src/components/bots/BotGameMobileLayout.tsx
    - frontend/src/components/bots/GameControls.tsx
    - frontend/src/components/bots/GameResultDialog.tsx
    - frontend/src/components/bots/PersonaGrid.tsx
    - frontend/src/components/bots/__tests__/PersonaGrid.test.tsx
    - frontend/src/hooks/useBotGameEngineDispatch.ts
    - frontend/src/hooks/useBotGameVoice.ts
    - frontend/src/hooks/useWinCelebrationHold.ts
    - frontend/src/lib/botGameCopy.ts
    - frontend/src/lib/botLineTrigger.ts
    - frontend/src/lib/confetti.ts
    - frontend/src/lib/sounds.ts
    - frontend/src/lib/theme.ts
    - frontend/src/lib/chessClock.ts
    - frontend/src/pages/Bots.tsx
    - frontend/src/pages/__tests__/Bots.test.tsx
    - frontend/src/App.tsx
    - frontend/src/App.test.tsx
    - CHANGELOG.md
  deleted:
    - frontend/src/components/bots/ClockDisplay.tsx
    - frontend/src/components/bots/__tests__/ClockDisplay.test.tsx
    - frontend/src/components/bots/BotClockStrip.tsx
    - frontend/src/components/bots/__tests__/BotClockStrip.test.tsx
    - frontend/src/components/settings/BoardSoundsSwitch.tsx
    - frontend/src/components/settings/__tests__/BoardSoundsSwitch.test.tsx
    - frontend/src/lib/botThreat.ts
    - frontend/src/lib/__tests__/botThreat.test.ts
    - frontend/src/lib/currentStrengthCopy.ts
    - frontend/src/lib/__tests__/currentStrengthCopy.test.ts

key-decisions:
  - "Swing detection moved from expected-score (sigmoid) delta to bot-POV centipawns clamped to +/-1000 (UAT, caa1208bc): the sigmoid saturates once a game is decided, so an 81-ply live game with queens hanging both ways fired zero swing lines. 150cp was calibrated on 300 analyzed dev-DB games at ~3.1 lines/game (100cp chatty, 250+ back toward silence). BOTVOICE-03's intent (never material-based, Attacker sacs safe) holds: the signal is still an eval delta over one move pair."
  - "The bot's reaction to its own blunder is deferred until the player cashes it in (UAT, 2e4663d80): the grade of the bot's own move already prices the loss, so speaking then is a spoiler and the punishing capture is an engine non-event. A swing against the bot latches and settles as 'punished-mistake' on the player's capture, 'got-away' on a full-threshold recovery, or 'nice-move' otherwise. This is BOTVOICE-02's board-truth rule applied more strictly than plan 04 managed."
  - "The 'player-threat' trigger and lib/botThreat.ts were dropped rather than fixed (UAT, 405bc5c6f): the detector ignored defender count and recapture value, so it announced 'my piece is hanging' during ordinary exchanges. Fixing it needs a static exchange evaluation; not worth the accuracy risk for one line."
  - "Mobile now renders the same PlayerBar rows as desktop and the analysis board, retiring BotClockStrip (UAT, 89115c7c6). This reverses D-11's 'no bot name, style, ELO or player name on mobile' and BOTVOICE-04's 'clock strip' wording: seeing the same row shape on every board surface won over the chess.com-style anonymous strip once both were on screen."
  - "The roster's 'Your estimated blitz rating' row is gone (UAT, 5caa0454c): a bot's calibrated ELO is measured against engines, so a human number beside it invites a comparison the two scales do not support. The in-game player row keeps the estimate. Partially reverses BOTVOICE-06."
  - "BoardSoundsSwitch is removed from both account surfaces (UAT, 5caa0454c). Sounds always play for now; a proper disable option is a later phase, so sounds.ts keeps useMuted/setMuted dormant and playSound still honours a persisted mute from before the switch left. BOTVOICE-07 is therefore unmet by owner decision, not by defect."
  - "The terminal line renders inside GameResultDialog with the persona avatar and the board-side bubble goes silent at game end, so the parting line is read rather than flashing behind the modal; the win hold waits out CONFETTI_DURATION_MS (exported from confetti.ts, replacing a guessed 1300ms)."

patterns-established:
  - "Per-breakpoint layout components (BotGameDesktopLayout / BotGameMobileLayout) share one pure row resolver (botPlayerRow.ts) so name, rating label, clock and material never diverge between breakpoints."

requirements-completed: [BOTVOICE-05]

coverage:
  - id: D1
    description: "Desktop renders PlayerBar rows above and below the board (name + tilde-prefixed calibrated label left, material + board-colour clock badge right) and the bubble at the top of the side column above the move list"
    requirement: BOTVOICE-05
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#Bots — desktop layout (Phase 223, BOTVOICE-05, D-11/D-12)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/board/__tests__/PlayerBar.test.tsx"
        status: pass
    human_judgment: true
    rationale: "Owner confirmed the desktop shape by eye across the UAT rounds (2026-09-16); jsdom proves structure and testids, not the side column lining up with the board's bottom."
  - id: D2
    description: "The bot's ELO renders as the calibrated label, never a parenthesised integer or a rung number; a guest's user row shows a name and no rating"
    requirement: BOTVOICE-05
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#renders the user row with a name and no rating text for a guest (no currentStrength)"
        status: pass
      - kind: other
        ref: "grep -c rung frontend/src/components/bots/BotGameDesktopLayout.tsx == 0"
        status: pass
    human_judgment: false
  - id: D3
    description: "The bot's draw offer is accepted or declined from inside the bubble on both breakpoints, both original testids preserved"
    requirement: BOTVOICE-05
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#Bots — bot draw-offer actions render inside the bubble (Phase 223, BOTVOICE-05, D-12)"
        status: pass
    human_judgment: true
    rationale: "Not seen live: wouldBotOfferDraw needs eval within +/-0.05 of dead-equal past move 30 with a 6-move cooldown, so it did not fire in the UAT games. The wiring is unit-tested; the trigger itself is Phase 183 code, unchanged here."
  - id: D4
    description: "The retired clock card, clock strip, threat probe, rating-copy module and sounds switch are deleted with their tests; the dead-export gate is green"
    requirement: BOTVOICE-05
    verification:
      - kind: other
        ref: "npm run knip exits 0; test ! -e on all five deleted components"
        status: pass
    human_judgment: false
  - id: D5
    description: "BotsGame stays under its pinned complexity with eslint.config.js unedited; no dependency or baseline drift"
    requirement: BOTVOICE-05
    verification:
      - kind: other
        ref: "npx eslint --rule 'complexity: [\"error\", 25]' src/pages/Bots.tsx exits 0 (measured 17); git diff on package.json, package-lock.json, pyproject.toml, uv.lock, eslint.config.js against merge-base is empty"
        status: pass
    human_judgment: false
---

# Phase 223 Plan 06 Summary

**Desktop player rows and side-column bubble shipped, then six browser UAT rounds re-tuned the voice (centipawn swings, latched punish lines, threat line dropped), unified both breakpoints on the shared `PlayerBar`, and retired the roster rating row and the sounds switch; `BotsGame` measures complexity 17 against its pinned 25.**

## Performance

- **Duration:** ~11h wall clock across two sessions (2026-09-15 23:50 to 2026-09-16 10:55), most of it the owner's interactive UAT rounds
- **Completed:** 2026-09-16
- **Tasks:** 4 (3 auto + 1 human-verify checkpoint, resolved through UAT rounds rather than a single pass)
- **Files modified:** 48 (2 created, 10 deleted, 26 modified; the rest are tests)

## Accomplishments

- `PlayerBar` gained the additive `ratingLabel` prop (T-01), then `clockActive`/`clockUrgent` and a `ClockBadge` sub-component painted in the player's board colour, red on low time; material moved into the right group beside the badge. All four pre-existing render sites untouched (`git diff` on Analysis.tsx, AnalysisPlayerBar.tsx, AnalysisBoardStage.tsx, AnalysisTabs.tsx against the merge-base is empty for the T-01 commit; AnalysisTabs.tsx later gained 4 lines for the labelled mobile analysis bar, a separate UAT change).
- `BotGameDesktopLayout` replaces the page's desktop render helper: rows ordered by board orientation, the bot row from `persona.calibratedLabel`, the user row from `currentStrength`, the bubble at the top of the side column with `BotDrawOfferActions` in its actions slot. `ClockDisplay` and its test deleted; theme.ts and chessClock.ts doc comments repointed.
- Changelog carries the phase's user-facing bullets (Added / Changed / Fixed), no em-dashes, no identifiers.
- UAT rounds (all committed as `fix(223-06): UAT round …`): bubble slot reserves two mobile lines so it never grows; roster bubble without a card; mobile switched to the shared player rows; silent bubble hidden, avatar kept; clock icon marks the side to move; bigger in-game avatar; labelled icon-over-text mobile bars on both /bots and /analysis; swing lines in centipawns; punish lines latched to the player's capture; terminal line inside the result dialog after the confetti; roster rating row and sounds switch removed; "We play like humans, not like computers." appended to every roster greeting.

## Recorded measurements (plan `<output>`)

| Measurement | Value |
|---|---|
| `BotsGame` cyclomatic complexity | **17** (ceiling 25, `frontend/eslint.config.js` unedited) |
| 375px board width before / after | **Not measured numerically.** Owner verified by eye at 375x667 on 2026-09-16 ("looks good, I tested"). The bubble-slot fix (09abcebc1) removed the 8px slot growth that pushed the board down; the mobile rows replacing the clock strip are the same height. |
| `BOT_LINE_MAX_CHARS` | **64**, unchanged since 223-01. Two-line fit at 375px confirmed in the browser; the slot is `min-h-12` below `sm` (index.css lifts `.text-sm` to 1rem/1.5rem there), `min-h-10` above. |
| Swing threshold after play-through | `BOT_LINE_SWING_THRESHOLD_CP = 150` (bot-POV centipawns, clamp `BOT_LINE_SWING_CLAMP_CP = 1000`), `BOT_LINE_SWING_SPACING_MOVES = 2`, mood lines keep spacing 3. ~3.8 swing lines/game on the 300-game replay; 5 lines in 40 plies on the instrumented live game that fired zero before. |

## Task Commits

1. **T-223-06-01: additive `ratingLabel` prop** — `e0832b5a9` (feat)
2. **T-223-06-02: desktop layout, retired clock card deleted** — `0c93b24fa` (feat)
3. **T-223-06-03: changelog entry** — `ebda0c38f` (docs)
4. **T-223-06-04: human verification, resolved as UAT rounds** — `09abcebc1`, `89115c7c6`, `0a2e88d38`, `405bc5c6f`, `caa1208bc`, `2e4663d80`, `5caa0454c` (fix)

`4a19a5e8e` (runbook note on Cloudflare crawler settings) landed on the branch mid-UAT and is unrelated to this plan.

## Human verification checklist outcome (T-223-06-04)

| # | Item | Outcome |
|---|---|---|
| 1 | Mobile board width strictly larger | Owner-verified by eye at 375x667, no numeric before/after recorded |
| 2 | Copy budget at 375px | Two lines fit; slot growth defect found and fixed (09abcebc1); constant stays 64 |
| 3 | Mobile screen shape | Verified, with a deliberate deviation: player rows instead of the anonymous clock strip (see Deviations) |
| 4 | Desktop shape | Verified across rounds; clock badge, right-side material and bigger avatar came out of it |
| 5 | Draw offer on both breakpoints, Custom game | Not observed live; the bot's offer gate (dead-equal past move 30) did not fire. Wiring covered by unit tests on both breakpoints and the persona-less form |
| 6 | Line frequency and tone | Failed first (zero swing lines in an 81-ply game), fixed twice: centipawn swing (caa1208bc), latched punish (2e4663d80). Player-threat line retired as inaccurate |
| 7 | Roster | Bubble and popover verified; rating row removed by owner decision (guest case now trivially holds) |
| 8 | Sound switch | Switch removed by owner decision; sounds always play, disable option deferred |

## Deviations from Plan

All deviations below are owner decisions taken during the UAT rounds, recorded here so the verifier reads them as intent, not gaps.

**1. Mobile shows player rows, not an anonymous clock strip (reverses D-11 / BOTVOICE-04 wording)**
- **Found during:** UAT round 2 (89115c7c6)
- **Change:** `BotClockStrip` deleted; `BotGameMobileLayout` renders the same `PlayerBar` rows as desktop via `botPlayerRow.ts`. Bot name and calibrated label are visible on mobile.
- **Why:** with both breakpoints on screen, the same row shape everywhere (analysis board included) read better than the chess.com-style anonymous strip. Plan 05's `D2` coverage entry ("no bot name, style, ELO or player name") is superseded; its test was replaced by `Bots — mobile player rows (Phase 223 UAT: same rows as the analysis board)`.

**2. Swing detection in centipawns, not expected score (refines BOTVOICE-03)**
- **Found during:** UAT round 5 (caa1208bc)
- **Change:** `botLineTrigger.ts` measures the bot-POV eval delta in cp, clamped to +/-1000, threshold 150. Still an eval delta over one move pair, never material, so the Attacker-sacrifice guarantee holds.
- **Why:** the sigmoid saturates once a game is decided; a real game with hanging queens produced no swing lines at all.

**3. Player-threat trigger dropped (narrows the BOTVOICE-01 trigger set)**
- **Found during:** UAT round 4 (405bc5c6f)
- **Change:** `'player-threat'` and `lib/botThreat.ts` removed with their copy table and tests.
- **Why:** the detector misfired on ordinary exchanges; a correct one needs static exchange evaluation. Every remaining trigger still has all 24 lines (the invariant test guards the set that exists).

**4. Roster rating row removed (partially reverses BOTVOICE-06)**
- **Found during:** UAT round 7 (5caa0454c)
- **Change:** the "Your estimated blitz rating" line, `PersonaGrid.currentStrength` and `currentStrengthCopy.ts` are gone. The in-game user row keeps the estimate.
- **Why:** bot ELOs are calibrated against engines; a human number beside them invited a comparison the scales do not support.

**5. Sounds switch removed (BOTVOICE-07 unmet by decision)**
- **Found during:** UAT round 7 (5caa0454c)
- **Change:** `BoardSoundsSwitch` and its tests deleted, both `App.tsx` render sites and the `App.test.tsx` describe block removed, changelog bullet rewritten. `sounds.ts` keeps `useMuted`/`setMuted` and `playSound`'s mute check dormant.
- **Why:** owner decision: sounds always play for now, a proper disable option comes in a later phase. Plan 03's deliverable is therefore not in the shipped tree; SC7 does not hold and is not meant to.

**6. Item 1 board width recorded qualitatively**
- The plan asked for a numeric before/after at 375px. The owner verified the outcome by eye and did not record numbers; no automated measurement exists. Left as owner-verified rather than fabricating a figure.

## Issues Encountered

- The first UAT session left `223-06-SUMMARY.md` unwritten and the verifier never ran, which is what blocked `/gsd-ship 223` on 2026-09-16 (`PHASE_VERIFICATION_INCOMPLETE`, status `missing`). This summary closes that gap.
- `str.replace` substring trap while removing the switch from `App.tsx`: the 12-space-indented drawer line contains the 10-space header line as a substring, so a naive line replace hit both. Fixed by replacing the drawer block first with full context.

## User Setup Required

None.

## Next Phase Readiness

- Full frontend gate green at `5caa0454c`: `npm run lint`, `npm run build`, `npm run knip`, `npm test -- --run` (266 files / 4287 tests).
- Open follow-ups for a later phase, not this one: a real board-sounds disable option (SEED-167's original ask, now deferred); a numeric 375px board-width measurement if SC4 is ever re-litigated; a static-exchange-based threat detector if the player-threat line is wanted back.

## Self-Check: PASSED

- All created/modified key files present on disk; all ten deleted files absent (`ClockDisplay`, `BotClockStrip`, `BoardSoundsSwitch`, `botThreat`, `currentStrengthCopy` and their tests).
- All ten plan commits present via `git log --oneline`.
- Plan-level `<verification>` re-run at HEAD: full frontend gate exit 0; `eslint --rule 'complexity:["error",25]'` on `Bots.tsx` exit 0; baseline/lockfile diff against the merge-base empty.
- Changelog checks: `>= 4` bullets mentioning bot/sound/board under `[Unreleased]`, zero em-dashes in that section.

---
*Phase: 223-bot-voice-immersive-bot-game-layout-seed-168-seed-167*
*Completed: 2026-09-16*
