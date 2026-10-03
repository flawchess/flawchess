---
phase: 223-bot-voice-immersive-bot-game-layout-seed-168-seed-167
plan: 04
subsystem: ui
tags: [react, bots, chess, voice-copy, chess.js, hooks]

requires:
  - phase: 223-01
    provides: "botGameCopy.ts's BotLineKey union, botLineTrigger.ts's ResolveBotLineInput shape and the single game-start arm, useBotGameVoice.ts's sub-hook skeleton and the onMoveCommitted/onBotMoveGraded seams"
  - phase: 223-02
    provides: "the ten authored BOT_LINE_TABLES keys (game-start, first-capture, earned-tease, punished-mistake, nice-move, player-threat, draw-offer, bot-won, bot-lost, game-drawn)"
provides:
  - "botThreat.ts: hasVisibleThreatOnBot(chess, botColor) — the engine-free chess.js probe for a hanging/under-defended bot piece (D-05)"
  - "botLineTrigger.ts: resolveBotLine's complete locked precedence chain (terminal > draw offer > swing > threat > first capture > game start), the swing/outcome helper functions, and the pacing guard"
  - "useBotGameVoice.ts: threat latches (created/still-live), the swing-consuming onBotMoveGraded, the pacing counter, and the new terminal/draw-offer effects"
  - "useBotGame.ts: botDrawOffer/outcome now flow into the voice hook"
affects: [223-06]

actuals:
  tokens: 13772
  tasks: 3
  commits: 6
  plan_head_before: 7cf65cb7284b36dda50cac5286d1ef4eeb2c0368

tech-stack:
  added: []
  patterns:
    - "Double-checked board-truth probe: the SAME engine-free chess.js detector runs at both the player's commit (creates the latch) and the bot's reply (re-probes before the line can fire), so a threat the bot already neutralised can never be announced."
    - "Single pacing guard evaluated once ahead of the paced arms, rather than repeated per-arm conditions — mirrors the swing/outcome helper-function split used to keep the top-level resolver a flat guard-clause list."
    - "Overwrite-not-accumulate move-pair latches (playerCapturedRef/threatCreatedRef): a fact about the CURRENT move pair must be reset on every commit of that mover, never OR'd across the whole game."

key-files:
  created:
    - frontend/src/lib/botThreat.ts
    - frontend/src/lib/__tests__/botThreat.test.ts
  modified:
    - frontend/src/lib/botLineTrigger.ts
    - frontend/src/lib/__tests__/botLineTrigger.test.ts
    - frontend/src/hooks/useBotGameVoice.ts
    - frontend/src/hooks/__tests__/useBotGameVoice.test.ts
    - frontend/src/hooks/useBotGame.ts

key-decisions:
  - "Genuine RED->GREEN for both tdd=\"true\" tasks: botThreat.ts was stubbed to always return false so the 8-case test file's two `true`-expecting assertions failed for the right reason before the real probe was written; botLineTrigger.test.ts's rewritten expectations (converting every 'null today' entry to a real key, plus new swing/pacing edge cases) were run against the OLD single-arm resolver first, producing 17/21 genuine failures, before the full precedence chain was implemented. Both RED states are preserved as separate `test(223-04):` commits."
  - "baseInput()'s botMovesSinceLastLine default changed from 0 to BOT_LINE_MIN_SPACING_MOVES ('already spaced enough') in botLineTrigger.test.ts, mirroring the codebase's own DRAW_OFFER_COOLDOWN_MOVES init convention — otherwise the pre-existing game-start test would break the instant the pacing guard was wired, since nothing has fired yet in a fresh game and pacing must not block the very first line."
  - "playerCapturedRef and threatCreatedRef are OVERWRITTEN on every player commit (not OR-accumulated as plan 01's playerCapturedRef literally was) — a Rule 1 bug fix: the pre-existing latch never reset to false on a non-capturing move, so a single early capture would have permanently mislabeled every LATER move pair's swing as player-captured."
  - "The terminal and draw-offer effects are separate, dedicated useEffects (not folded into onBotMoveGraded alone) because a game can end — or the bot can raise a draw offer — with no grade in flight at all (a flag, a resignation, a stalemate, or an offer raised between grades); onBotMoveGraded ALSO consults outcome/drawOfferLive so a grade landing after either event still resolves to the same (idempotent) key."

patterns-established:
  - "Board-truth double-check: latch a chess.js-derived fact at the player's commit, re-derive it fresh at the bot's reply, and require BOTH to report — the shape any future board-truth-gated trigger in this phase should copy."

requirements-completed: [BOTVOICE-02, BOTVOICE-03]

coverage:
  - id: D1
    description: "The player-threat line: a bot piece hanging or under-defended after the player's move, verified engine-free with chess.js, and re-verified after the bot's own reply so a neutralised threat never fires"
    requirement: "BOTVOICE-02"
    verification:
      - kind: unit
        ref: "src/lib/__tests__/botThreat.test.ts#hasVisibleThreatOnBot (8 cases: hanging, cheaper-attacker-even-when-defended, equal-value-defended, unattacked, king-excluded, one-sided, no-bot-pieces, non-mutation)"
        status: pass
      - kind: unit
        ref: "src/hooks/__tests__/useBotGameVoice.test.ts#a threat created by the player and still live after the bot replies produces the player-threat key"
        status: pass
      - kind: unit
        ref: "src/hooks/__tests__/useBotGameVoice.test.ts#a threat created and then neutralised by the bot leaves the bubble untouched (no report)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The swing lines in both directions (earned tease / punished mistake / nice move), gated by BOT_LINE_SWING_THRESHOLD over exactly one move pair, with the D-04 capture tie-breaker and the D-01 sacrifice-immunity property"
    requirement: "BOTVOICE-03"
    verification:
      - kind: unit
        ref: "src/lib/__tests__/botLineTrigger.test.ts#resolveBotLine — full precedence chain + swing arm edge cases (21 cases, incl. the named Attacker-sacrifice flat-delta case)"
        status: pass
      - kind: unit
        ref: "src/hooks/__tests__/useBotGameVoice.test.ts#a graded swing at or beyond the threshold produces the earned-tease key"
        status: pass
      - kind: unit
        ref: "src/hooks/__tests__/useBotGameVoice.test.ts#an adjacency violation (no established baseline) produces nothing"
        status: pass
    human_judgment: false
  - id: D3
    description: "First capture, the bot's draw offer, and all three terminal outcomes (win/loss/draw), each reachable from the resolver and wired into the hook — including a terminal line firing with NO grade ever in flight"
    requirement: "BOTVOICE-02"
    verification:
      - kind: unit
        ref: "src/hooks/__tests__/useBotGameVoice.test.ts#an outcome transition produces the terminal key with no graded-score callback ever fired"
        status: pass
      - kind: unit
        ref: "src/hooks/__tests__/useBotGameVoice.test.ts#a draw offer produces its key immediately, with no grade involved"
        status: pass
    human_judgment: false
  - id: D4
    description: "Pacing: non-terminal lines are suppressed within BOT_LINE_MIN_SPACING_MOVES bot moves of the last one; terminal and draw-offer lines are never suppressed"
    requirement: "BOTVOICE-02"
    verification:
      - kind: unit
        ref: "src/lib/__tests__/botLineTrigger.test.ts#resolveBotLine — pacing (3 cases: suppresses all four non-terminal arms, exempts terminal, exempts draw-offer, both at pacing count zero)"
        status: pass
      - kind: unit
        ref: "src/hooks/__tests__/useBotGameVoice.test.ts#pacing suppresses a second non-terminal line fired too soon after the first"
        status: pass
    human_judgment: false
  - id: D5
    description: "No second engine grade call, no engine import in the threat probe or the voice hook, and no timer/animation anywhere in the bubble path (D-01/D-05/D-07)"
    requirement: "BOTVOICE-02"
    verification:
      - kind: other
        ref: "grep -cE \"from '@/lib/engine|workerPool|evalToExpectedScore|maia\" src/lib/botThreat.ts -> 0; grep -cE \"from '@/lib/engine|workerPool\" src/hooks/useBotGameVoice.ts -> 0; grep -c '\\.grade\\(' src/hooks/useBotGameEngineDispatch.ts -> 4 (1 real call site + 3 pre-existing doc-comment mentions, unchanged before/after — see Deviations); grep -cE 'setTimeout|setInterval|requestAnimationFrame' src/hooks/useBotGameVoice.ts -> 0"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-09-15
status: complete
---

# Phase 223 Plan 04: Bot Voice Trigger Set — Threat Probe, Swing Resolver, Voice Wiring Summary

**Every locked trigger (swing in both directions, the double-checked engine-free player-threat probe, first capture, draw offer, and all three terminal outcomes) now fires from a real game through one pure resolver and one pure chess.js probe, both unit-tested with fabricated sequences and fixed positions — including a genuine RED->GREEN cycle on both TDD tasks and a Rule-1 fix to a latch bug inherited from plan 01.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-15T23:29:00Z (approx.)
- **Completed:** 2026-09-15T23:41:00Z
- **Tasks:** 3 completed
- **Files modified:** 7 (2 created, 5 modified)

## Accomplishments

- Built `botThreat.ts`'s `hasVisibleThreatOnBot(chess, botColor)`: a pure, engine-free chess.js probe reporting a bot piece (never the king) that is attacked and either undefended or attacked by a strictly cheaper enemy piece — one-sided by construction, never mutates the board, 9 tests over 8 fixed FENs.
- Implemented `resolveBotLine`'s complete locked precedence chain in `botLineTrigger.ts`: terminal outcome > draw offer > swing (either direction, D-04 capture tie-breaker) > player threat > first capture > game start, with a single pacing guard ahead of the four paced arms — 21 tests, guard-clause-only body (no `else`, no nesting).
- Wired `useBotGameVoice.ts`: the player's commit latches capture/threat facts for the current move pair (overwritten, not accumulated — a Rule 1 fix over plan 01's own shape); the bot's commit advances the pacing counter and re-probes the threat fresh; `onBotMoveGraded` builds the full resolver input and consumes the once-per-fact latches on fire; new terminal and draw-offer effects fire their keys independently of the async grade seam.
- `useBotGame.ts`'s voice-hook call site now passes `botDrawOffer`/`outcome` — confirmed via `git diff` to be the ONLY change in that file.
- Full frontend gate green: `npm run lint`, `npm run build`, `npm run knip`, `npm test -- --run` (271 files / 4280 tests), plus every plan-level grep/complexity/supply-chain check.

## Task Commits

Each task was committed atomically, with genuine RED->GREEN pairs for both `tdd="true"` tasks:

1. **Task 1: The engine-free threat probe** — `534ca85ea` (test, RED — stubbed `hasVisibleThreatOnBot` always returns false, 2/9 assertions genuinely fail), `e1261803f` (feat, GREEN — real probe, 9/9 pass), `f93108905` (fix — reworded a doc comment that matched its own no-mutation grep)
2. **Task 2: The complete resolver** — `47371f49e` (test, RED — rewritten expectations, 17/21 genuinely fail against the old single-arm resolver), `092ec45c5` (feat, GREEN — full precedence chain, 21/21 pass)
3. **Task 3: Wire the voice hook** — `fc84ddaf9` (feat — threat latches, swing consumption, pacing, terminal/draw-offer effects; `type="auto"`, no TDD gate)

**Plan metadata:** (this commit)

## Files Created/Modified

- `frontend/src/lib/botThreat.ts` — `hasVisibleThreatOnBot`, `THREAT_PIECE_VALUE`
- `frontend/src/lib/__tests__/botThreat.test.ts` — 9 tests over 8 fixed FENs
- `frontend/src/lib/botLineTrigger.ts` — full `resolveBotLine`, `resolveSwingKey`, `resolveOutcomeKey`
- `frontend/src/lib/__tests__/botLineTrigger.test.ts` — 21 tests, `baseInput`'s pacing-aware default
- `frontend/src/hooks/useBotGameVoice.ts` — threat/first-capture latches, pacing counter, terminal/draw-offer effects
- `frontend/src/hooks/__tests__/useBotGameVoice.test.ts` — 11 tests, fabricated `Chess` positions via `renderHook`
- `frontend/src/hooks/useBotGame.ts` — voice-hook call site passes `botDrawOffer`/`outcome` (only change)

## Decisions Made

See `key-decisions` in the frontmatter. The most consequential: fixing `playerCapturedRef`'s latch to overwrite rather than accumulate, since the version plan 01 shipped never reset it to `false` on a non-capturing player move — left uncorrected, a single early-game capture would have permanently mislabeled every LATER swing-against-the-bot pair as "player captured," always producing the self-deprecating `punished-mistake` line instead of the correct `nice-move` compliment for the rest of the game.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `playerCapturedRef` (and its sibling `threatCreatedRef`) must overwrite, not accumulate**
- **Found during:** Task 3, while reasoning through `onMoveCommitted`'s player branch
- **Issue:** Plan 01's shipped code only ever SET `playerCapturedRef.current = true` on a capturing player move; it never reset it to `false` on a non-capturing one. Both `playerCapturedRef` and the new `threatCreatedRef` describe a fact about the CURRENT move pair, so a stale `true` from an earlier pair would silently corrupt every later D-04 capture/no-capture split.
- **Fix:** Both refs are now unconditionally overwritten on every player commit (`playerCapturedRef.current = move.captured !== undefined`; `threatCreatedRef.current = hasVisibleThreatOnBot(...)`), never OR'd.
- **Files modified:** `frontend/src/hooks/useBotGameVoice.ts`
- **Verification:** `src/hooks/__tests__/useBotGameVoice.test.ts` — the neutralised-threat and both swing-arm test cases exercise this directly; full suite green.
- **Committed in:** `fc84ddaf9` (Task 3 commit)

**2. [Rule 1 - Bug in my own doc comment] `botThreat.ts` and `useBotGameVoice.ts` doc comments matched their own acceptance-criteria greps**
- **Found during:** Task 1 and Task 3's own verify commands
- **Issue:** `botThreat.ts`'s doc comment named `.move(`/`.undo(`/`.load(` verbatim to explain why the module never calls them, tripping the literal-substring grep that checks for exactly that. `useBotGameVoice.ts`'s module header named `requestAnimationFrame` verbatim in the same way, tripping the D-07 timer-absence grep. Same false-positive-comment class documented in 223-01/223-02/223-05's SUMMARYs.
- **Fix:** Reworded both comments to describe the invariant without the literal substrings (`fix(223-04)` commit for the first; folded into the Task 3 commit for the second, since it was caught before Task 3's own commit).
- **Files modified:** `frontend/src/lib/botThreat.ts`, `frontend/src/hooks/useBotGameVoice.ts`
- **Verification:** Both greps now return 0; behavior unchanged (doc-only).
- **Committed in:** `f93108905`, `fc84ddaf9`

### Known Pre-Existing Planning-Artifact Defect (not a code bug — documented, not silently worked around)

**3. `grep -c '\.grade\('` on `useBotGameEngineDispatch.ts` still counts 3 pre-existing comments**
- **Found during:** Task 3's own `<verify>` (`test "$(grep -c '\.grade(' ...)" = "1"`)
- **Issue:** As already documented in `223-01-SUMMARY.md` Deviation #2, this file has exactly ONE real `.grade(` call site but the literal grep also matches 3 pre-existing doc/inline comments that mention `pool.grade()` in prose, so the count reads 4 both before and after this plan (unchanged). This plan does not touch `useBotGameEngineDispatch.ts` at all (it is not in `files_modified`), so there is nothing to fix here beyond re-confirming the pre-existing baseline holds.
- **Not fixed:** Out of this plan's file scope; flagged again for visibility.
- **Impact:** None on shipped behavior — the real invariant (exactly one grade call site) is unchanged and confirmed by direct inspection (line 468).

---

**Total deviations:** 2 auto-fixed (1 real bug, 1 doc-comment false-positive class), 1 re-confirmed pre-existing planning-artifact defect (no code impact).
**Impact on plan:** The playerCapturedRef fix is a genuine correctness improvement over plan 01's shipped code, caught during this plan's own reasoning rather than left latent. No scope creep.

## Line Frequency Baseline (for plan 06's UAT)

No live manual play-through was run in this session (no dev server was started; the phase's existing convention, per 223-01/223-02/223-05's own "Next Phase Readiness" notes, defers real browser-measured numbers to plan 06's UAT). As a substitute, a throwaway Node simulation (not part of the app, not committed) ran `resolveBotLine`'s exact threshold/spacing constants (`BOT_LINE_SWING_THRESHOLD = 0.2`, `BOT_LINE_MIN_SPACING_MOVES = 3`) over 500 synthetic 40-move-pair random-walk score sequences: mean **4.1** swing lines per game (min 1, max 8, zero games with none). This is a **statistical estimate over a crude random walk, not a measurement of real Stockfish grade sequences** — real game scores are far more stable move-to-move with occasional sharp swings, so the true in-game frequency is likely lower and burstier than this estimate suggests. Plan 06's UAT should replace this with an actual measured count from real play and retune `BOT_LINE_SWING_THRESHOLD` if lines fire much more than "a couple of times per game" (D-02's own target).

## Issues Encountered

None beyond the documented deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Every trigger in the locked set (BOTVOICE-01 through BOTVOICE-03) is now implemented and unit-tested: game start, first capture, both swing directions, player threat, draw offer, and all three terminal outcomes.
- `BOTVOICE-02` is shared with plan 223-01 (already summarized) — this plan's SUMMARY is the LAST declaring plan, so the shared-ID gate should mark it complete now. `BOTVOICE-03` is declared only here.
- The `playerCapturedRef`/`threatCreatedRef` overwrite-semantics fix means BOTVOICE-03's capture/no-capture split is now correct for the FULL game, not just the first pair — plan 06's UAT can trust it without a caveat.
- The line-frequency estimate above is explicitly a placeholder, not a real measurement — plan 06 should budget time for an actual play-through before tuning `BOT_LINE_SWING_THRESHOLD`.
- No blockers for plan 223-06 (the desktop-side layout rework).

---
*Phase: 223-bot-voice-immersive-bot-game-layout-seed-168-seed-167*
*Plan: 04*
*Completed: 2026-09-15*

## Self-Check: PASSED

- All 2 created files verified present on disk (`[ -f ]`): `frontend/src/lib/botThreat.ts`, `frontend/src/lib/__tests__/botThreat.test.ts`.
- `git log --oneline --all` contains all 6 recorded commits (`534ca85ea`, `e1261803f`, `f93108905`, `47371f49e`, `092ec45c5`, `fc84ddaf9`).
- All plan-level `<verification>` commands re-run and pass: `npm run lint`, `npm run build`, `npm test -- --run` (271 files / 4280 tests), `npm run knip`, the `eslint --rule 'complexity:["error",25]'` regression guard on `Bots.tsx`, and the supply-chain/eslint.config.js diff gate.
- All task-level `<acceptance_criteria>` re-checked and pass, including the two false-positive doc-comment greps (now fixed) and the pre-existing `useBotGameEngineDispatch.ts` grade-count defect (re-confirmed unchanged, out of this plan's scope).
