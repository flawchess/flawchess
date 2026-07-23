---
phase: 260723-tqn
plan: 01
subsystem: ui
tags: [bot-play, sounds, canvas-confetti, react-hooks, celebration]

requires:
  - phase: 169
    provides: sounds.ts (playSound/useMuted/setMuted mute-persistence module)
  - phase: 183
    provides: finalizeGame outcome handling in useBotGame.ts
provides:
  - Outcome-specific bot-game sound events (game-win/game-loss/game-draw playing the vendored Victory/Defeat/Draw clips)
  - confetti.ts helper (fireWinConfetti + prefersReducedMotion) wrapping canvas-confetti
  - useWinCelebrationHold hook gating the result modal open for ~1.3s on a human win
affects: [bot-play, Bots.tsx, useBotGame]

tech-stack:
  added: [canvas-confetti@1.9.4, "@types/canvas-confetti@1.9.0"]
  patterns:
    - "Single firing site: finalizeGame (useBotGame.ts) is the ONLY place that calls playSound/fireWinConfetti for a game outcome — Bots.tsx only reads the celebration-hold hook to gate UI, never re-fires sound/confetti"
    - "reduced-motion guard: prefersReducedMotion() gates both the confetti burst and the modal-open delay identically, so a reduced-motion user never sees a delay with no corresponding animation"

key-files:
  created:
    - frontend/src/lib/confetti.ts
    - frontend/src/lib/__tests__/confetti.test.ts
    - frontend/src/hooks/useWinCelebrationHold.ts
    - frontend/src/hooks/__tests__/useWinCelebrationHold.test.ts
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/src/lib/sounds.ts
    - frontend/src/lib/__tests__/sounds.test.ts
    - frontend/src/hooks/useBotGame.ts
    - frontend/src/hooks/__tests__/useBotGame.test.ts
    - frontend/src/pages/Bots.tsx
    - frontend/src/pages/__tests__/Bots.test.tsx

key-decisions:
  - "Kept the game-end SoundEvent member and its Checkmate clip mapping rather than removing it — no other call site was found to justify deletion, and finalizeGame no longer calls it (replaced by game-win/game-loss/game-draw), so it is inert but harmless"
  - "fireWinConfetti fires two angled bursts (left + right origin) using WDL_WIN plus two warm accent hex colors, rather than a single centered burst, for a more symmetric celebration read"
  - "useWinCelebrationHold tracks the outcome object reference (not just a boolean) via a ref, so a re-render with the same outcome never re-triggers the timer but a fresh outcome (including after a reset to null on a new game) always does"
  - "Mocked useWinCelebrationHold to false in Bots.test.tsx (existing real-timer UI-wiring suite) rather than switching that whole file to fake timers — the hook's actual timing behavior is proven independently by its own fake-timer unit test"

requirements-completed: [QUICK-260723-tqn]

coverage:
  - id: D1
    description: "playSound('game-win'/'game-loss'/'game-draw') dispatch the vendored Victory/Defeat/Draw clips respectively, mute-gated same as all other SoundEvents"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/sounds.test.ts#dispatches the %s asset"
        status: pass
    human_judgment: false
  - id: D2
    description: "fireWinConfetti() invokes canvas-confetti; prefersReducedMotion() correctly resolves reduce / no-preference / missing-matchMedia"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/confetti.test.ts"
        status: pass
    human_judgment: false
  - id: D3
    description: "useWinCelebrationHold holds true for WIN_CELEBRATION_HOLD_MS on a fresh human win (not reduced-motion), false for loss/draw/null/reduced-motion, clears its timer on unmount, and resets across a new game"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useWinCelebrationHold.test.ts"
        status: pass
    human_judgment: false
  - id: D4
    description: "finalizeGame selects the correct outcome sound + fires confetti on a human win only; Bots.tsx gates GameResultDialog's open prop on the celebration hold"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useBotGame.test.ts, frontend/src/pages/__tests__/Bots.test.tsx"
        status: pass
    human_judgment: true
    rationale: "The actual live-browser experience (sound timing, confetti visual timing over the board, ~1.3s modal delay feel) is a UX/feel judgment call best confirmed by a human playing a real bot game, per the plan's optional manual verification section"

duration: 25min
completed: 2026-07-23
status: complete
---

# Quick 260723-tqn: Bot-Win Celebration (Confetti + Victory Sound) Summary

**Human bot-game wins now play the vendored Victory sound and fire a two-burst confetti celebration, holding the result modal closed for ~1.3s so the confetti reads over the board first; losses/draws now play the (previously vendored but unused) Defeat/Draw clips and open the modal immediately, both gated by the OS reduced-motion preference.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-23T19:12:00Z
- **Completed:** 2026-07-23T19:37:11Z
- **Tasks:** 3
- **Files modified:** 12 (4 created, 8 modified)

## Accomplishments
- `sounds.ts` gained `game-win`/`game-loss`/`game-draw` SoundEvent members mapped to the previously-unused vendored Victory/Defeat/Draw clips, replacing the single undiscriminated `game-end` (Checkmate) call in `finalizeGame`.
- New `confetti.ts` wraps `canvas-confetti` with `fireWinConfetti()` (two angled bursts using theme colors) and `prefersReducedMotion()` (reads `prefers-reduced-motion`, defaults to "animate" if `matchMedia` is unavailable).
- New `useWinCelebrationHold` hook holds a bot-game result modal closed for `WIN_CELEBRATION_HOLD_MS` (~1.3s) after a fresh human win (skipped entirely under reduced-motion), returning `false` immediately for loss/draw/no-outcome.
- `finalizeGame` (useBotGame.ts) is the single firing site for outcome sound + confetti; `Bots.tsx` only consumes the hold via `!dialogDismissed && !celebrationHold` on `GameResultDialog`'s `open` prop.

## Task Commits

Each task was committed atomically:

1. **Task 1: Outcome sound events + confetti/reduced-motion helper** - `6a962bb5` (test, RED) + `d4dcabf6` (feat, GREEN)
2. **Task 2: Celebration-hold hook + wire into finalizeGame and Bots.tsx** - `f1f079ba` (test, RED) + `7d8eea0d` (feat, GREEN)
3. **Task 3: Full frontend gate (types, lint, tests, knip)** - no commit; `tsc -b`, `eslint`, the full test suite (2538 tests), and `knip` all passed cleanly on the first run with no fixes required

**Plan metadata:** pending (this SUMMARY's commit)

_Note: Task 1 and Task 2 each follow RED (failing test) -> GREEN (implementation) per tdd="true"._

## Files Created/Modified
- `frontend/src/lib/confetti.ts` - `fireWinConfetti()` (canvas-confetti two-burst wrapper) + `prefersReducedMotion()`
- `frontend/src/lib/__tests__/confetti.test.ts` - unit tests for both exports (mocked canvas-confetti, stubbed matchMedia)
- `frontend/src/hooks/useWinCelebrationHold.ts` - `useWinCelebrationHold(outcome, userColor)` + `WIN_CELEBRATION_HOLD_MS` constant
- `frontend/src/hooks/__tests__/useWinCelebrationHold.test.ts` - fake-timer unit tests covering win/loss/draw/null/reduced-motion/unmount/reset
- `frontend/src/lib/sounds.ts` - added `game-win`/`game-loss`/`game-draw` SoundEvent members + SOUND_FILES entries (Victory/Defeat/Draw)
- `frontend/src/lib/__tests__/sounds.test.ts` - extended asset-dispatch table + unlockAudio count (6 -> 9)
- `frontend/src/hooks/useBotGame.ts` - `finalizeGame` now selects `game-win`/`game-draw`/`game-loss` and fires `fireWinConfetti()` on a human win (unless reduced-motion)
- `frontend/src/hooks/__tests__/useBotGame.test.ts` - mocked `@/lib/confetti`; updated `game-end` assertions to `game-win`/`game-loss`
- `frontend/src/pages/Bots.tsx` - calls `useWinCelebrationHold(game.outcome, settings.userColor)`; `GameResultDialog`'s `open` gated on `!dialogDismissed && !celebrationHold`
- `frontend/src/pages/__tests__/Bots.test.tsx` - mocked `useWinCelebrationHold` to `false` (its real timing is covered by its own dedicated unit test)
- `frontend/package.json` / `frontend/package-lock.json` - added `canvas-confetti` (dependencies) + `@types/canvas-confetti` (devDependencies)

## Decisions Made
- Kept the `game-end` SoundEvent member (mapped to `Checkmate.mp3`) rather than deleting it — `finalizeGame` no longer calls it, but no repo-wide justification to remove a still-exported, still-tested member was found; it's inert, not dead-code-flagged by knip since it remains in the exported `SoundEvent` union and `SOUND_FILES` map (both consumed).
- `useWinCelebrationHold` keys its "have I started a hold for this outcome" ref off the outcome object reference itself (not a derived boolean), so React re-renders with the same outcome never re-trigger the timer, while a genuinely fresh outcome (including the null -> new-win transition on a rematch/new game) always does.
- Mocked `useWinCelebrationHold` in `Bots.test.tsx` (a real-timer UI-wiring suite) instead of converting that whole suite to fake timers — its actual hold/delay behavior is proven independently and more precisely by `useWinCelebrationHold.test.ts`'s fake-timer tests.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing `useBotGame.test.ts` assertions referenced the now-unfired `game-end` sound**
- **Found during:** Task 2 (wiring `finalizeGame`'s outcome-based sound selection)
- **Issue:** Two pre-existing tests asserted `playSound` was called with `'game-end'` for a human win by resignation/checkmate. Since `finalizeGame` now calls `playSound('game-win'|'game-loss'|'game-draw')` instead, those assertions would silently pass-through-as-false-negative (checking a string that's never emitted anymore) rather than actually verifying anything.
- **Fix:** Updated the assertions to the correct new event names (`game-win` for the user-win scenarios, `game-loss` for the "no duplicate finalize" idempotency check where the user lost).
- **Files modified:** `frontend/src/hooks/__tests__/useBotGame.test.ts`
- **Verification:** `npm test -- --run src/hooks/__tests__/useBotGame.test.ts` — 72/72 pass.
- **Committed in:** `7d8eea0d` (Task 2 commit)

**2. [Rule 3 - Blocking] `Bots.test.tsx`'s result-dialog assertions timed out against the real celebration-hold delay**
- **Found during:** Task 2 (wiring `Bots.tsx`'s `GameResultDialog` `open` gate)
- **Issue:** `Bots.test.tsx` mocks `useBotGame` but not `useWinCelebrationHold`, and most of its `finishGame`-style helpers set a human-win outcome (`winner: 'white'` with the default `userColor: 'white'`). With the real hook now applied, `GameResultDialog` stayed closed for `WIN_CELEBRATION_HOLD_MS` (~1.3s) using REAL timers, exceeding `waitFor`'s default 1000ms timeout — 9 tests failed with the dialog never appearing in time.
- **Fix:** Mocked `@/hooks/useWinCelebrationHold` in `Bots.test.tsx` to always return `false` (no hold), since the hook's actual delay/reduced-motion behavior is already fully covered by its own dedicated fake-timer unit test.
- **Files modified:** `frontend/src/pages/__tests__/Bots.test.tsx`
- **Verification:** `npm test -- --run src/pages/__tests__/Bots.test.tsx` — 32/32 pass (was 9 failing before the mock).
- **Committed in:** `7d8eea0d` (Task 2 commit)

**3. [Rule 3 - Blocking] `unlockAudio` test-only Audio-instance count needed bumping for the 3 new preloaded clips**
- **Found during:** Task 1 (writing the failing sounds.test.ts extension)
- **Issue:** The plan explicitly flagged this ("update the unlockAudio instance-count assertion to the new SoundEvent count, currently hard-coded 6") as part of the RED step, not a genuine deviation, but recording it here for completeness.
- **Fix:** Bumped `toHaveLength(6)` to `toHaveLength(9)` (9 total SoundEvent members after adding game-win/game-loss/game-draw).
- **Files modified:** `frontend/src/lib/__tests__/sounds.test.ts`
- **Verification:** `npm test -- --run src/lib/__tests__/sounds.test.ts` — 13/13 pass.
- **Committed in:** `6a962bb5` (Task 1 RED commit) / `d4dcabf6` (Task 1 GREEN commit)

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking — both existing-test breakage caused by the intended new behavior, expected and anticipated by the plan)
**Impact on plan:** No scope creep. All fixes were necessary to keep the existing test suite meaningfully green after the intended sound/hold-gating behavior change; none altered the shipped feature itself.

## Issues Encountered
- `vi.advanceTimersByTime` calls in `useWinCelebrationHold.test.ts` initially didn't flush the resulting `setState` synchronously (React 19 automatic batching under fake timers) — wrapped each advance in `@testing-library/react`'s `act()`, matching the existing `useReadiness.test.tsx` precedent.

## User Setup Required
None - no external service configuration required. `canvas-confetti` is a pure client-side npm dependency, no API keys or accounts needed.

## Next Phase Readiness
- Feature is self-contained and fully wired; no follow-up work identified.
- Manual/live-browser confirmation (win a bot game -> Victory sound + confetti, modal at ~1.3s; lose -> Defeat sound, modal immediate; draw -> Draw sound, modal immediate; mute toggle silences all three; OS reduced-motion -> sound only, no confetti, immediate modal) remains optional per the plan's verification section — not required to close this quick task, but recommended before the next `bin/deploy.sh` release.

---
*Phase: 260723-tqn*
*Completed: 2026-07-23*

## Self-Check: PASSED

All created/modified files exist on disk and all 4 task commit hashes (6a962bb5, d4dcabf6, f1f079ba, 7d8eea0d) are present in git log.
