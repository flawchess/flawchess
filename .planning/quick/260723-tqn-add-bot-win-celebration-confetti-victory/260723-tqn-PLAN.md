---
phase: 260723-tqn
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/package.json
  - frontend/src/lib/sounds.ts
  - frontend/src/lib/__tests__/sounds.test.ts
  - frontend/src/lib/confetti.ts
  - frontend/src/lib/__tests__/confetti.test.ts
  - frontend/src/hooks/useBotGame.ts
  - frontend/src/hooks/useWinCelebrationHold.ts
  - frontend/src/hooks/__tests__/useWinCelebrationHold.test.ts
  - frontend/src/pages/Bots.tsx
autonomous: true
requirements: [QUICK-260723-tqn]
must_haves:
  truths:
    - "When the human wins a bot game, a Victory sound plays and (unless reduced-motion) confetti bursts before the result modal opens."
    - "When the human loses, a Defeat sound plays; on a draw, a Draw sound plays — both open the result modal immediately."
    - "All new outcome sounds remain mute-gated via playSound/readMuted."
    - "reduced-motion users get the sound but no confetti and no modal delay."
  artifacts:
    - frontend/src/lib/confetti.ts
    - frontend/src/hooks/useWinCelebrationHold.ts
  key_links:
    - "finalizeGame (useBotGame) selects the outcome sound and fires confetti on a human win."
    - "Bots.tsx gates GameResultDialog `open` on the celebration hold so the modal waits out the confetti on a win only."
---

<objective>
Add a bot-win celebration: on a human win in a bot game, play the vendored Victory
sound and (unless the user prefers reduced motion) fire a confetti burst, delaying
the result modal by a short window so the confetti plays over the board first.
Loss/draw now play the vendored Defeat/Draw clips (replacing the single Checkmate
clip fired for every outcome) and keep opening the modal immediately.

Purpose: reward the win moment; give losses/draws their own (already-vendored) audio.
Output: outcome-specific sound events, a confetti helper, a testable celebration-hold
hook, and the wiring in `finalizeGame` + `Bots.tsx`.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@.planning/STATE.md

@frontend/src/lib/sounds.ts
@frontend/src/lib/__tests__/sounds.test.ts
@frontend/src/lib/botGameEnd.ts
@frontend/src/hooks/useBotGame.ts
@frontend/src/pages/Bots.tsx
@frontend/src/components/bots/GameResultDialog.tsx

Key facts (verified against code):
- `finalizeGame(finished: BotGameOutcome)` at useBotGame.ts ~L766 currently ends with
  `playSound('game-end')` (~L792). `settings.userColor` and `finished.winner`/
  `finished.reason` are all in scope. Human win = decisive with `finished.winner === settings.userColor`;
  draw = `finished.reason === 'draw'`; loss = decisive with `winner !== userColor`.
- `BotGameOutcome` (botGameEnd.ts): `{ reason, winner?, drawReason? }`. `winner` omitted on draw.
- Bots.tsx: `GameResultDialog` renders when `game.outcome !== null` with `open={!dialogDismissed}`
  (~L506-520); `GameResultStrip` shows when `dialogDismissed` is true (~L433); `dialogDismissed`
  resets to false when `game.outcome === null` (~L303-306). `settings.userColor` in scope.
- `frontend/public/sound/` already ships `Victory.mp3`, `Defeat.mp3`, `Draw.mp3` (currently unused).
- No confetti lib in package.json. Theme colors live in `frontend/src/lib/theme.ts` (e.g. WDL_WIN).
- NO Prettier in this repo — ESLint only. `noUncheckedIndexedAccess` is on. `text-sm` floor.
- knip runs in CI: any new dep MUST be imported, any new export MUST be consumed.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Outcome sound events + confetti/reduced-motion helper</name>
  <files>frontend/package.json, frontend/src/lib/sounds.ts, frontend/src/lib/__tests__/sounds.test.ts, frontend/src/lib/confetti.ts, frontend/src/lib/__tests__/confetti.test.ts</files>
  <behavior>
    - sounds.ts: `playSound('game-win')` loads `/sound/Victory.mp3`; `'game-loss'` → `Defeat.mp3`; `'game-draw'` → `Draw.mp3`. Each still no-ops when muted.
    - `unlockAudio` preloads every SoundEvent including the three new ones.
    - confetti.ts: `fireWinConfetti()` invokes the mocked `canvas-confetti` default export at least once.
    - confetti.ts: `prefersReducedMotion()` returns `true` when matchMedia reports reduce, `false` when it reports no-preference, and `false` (animate) when `window.matchMedia` is undefined.
  </behavior>
  <action>
    Add `'game-win'`, `'game-loss'`, `'game-draw'` to the `SoundEvent` union in sounds.ts
    and map them in `SOUND_FILES` to `'Victory'`, `'Defeat'`, `'Draw'`. KEEP the existing
    `'game-end'` member (it is still referenced by unlockAudio's iteration and callers may
    remain) unless a repo-wide grep shows `finalizeGame` is its only call site — if so you
    may remove it and drop its `game-end`/Checkmate test row; otherwise leave it. Update the
    module doc comment noting Victory/Defeat/Draw are now live.

    Extend sounds.test.ts: add the three new events to the `it.each` asset-dispatch table
    (game-win→Victory.mp3, game-loss→Defeat.mp3, game-draw→Draw.mp3) and update the
    unlockAudio instance-count assertion to the new SoundEvent count (currently hard-coded 6).

    Add `canvas-confetti` to dependencies and `@types/canvas-confetti` to devDependencies in
    package.json (run `npm install <pkg>` so the lockfile updates). Create `frontend/src/lib/confetti.ts`
    exporting `fireWinConfetti()` (one short `confetti()` burst, or two quick calls) and
    `prefersReducedMotion()`. Pull confetti `colors` from theme.ts brand/WDL tokens (e.g. WDL_WIN),
    do NOT hardcode hex. `prefersReducedMotion` must guard `typeof window === 'undefined' || !window.matchMedia`
    and treat that as "not reduced-motion". Create `frontend/src/lib/__tests__/confetti.test.ts`
    mocking `canvas-confetti` (vi.mock) and stubbing `window.matchMedia` to cover the behaviors above.
  </action>
  <verify>
    <automated>cd frontend && npm test -- --run src/lib/__tests__/sounds.test.ts src/lib/__tests__/confetti.test.ts</automated>
  </verify>
  <done>New outcome sound events dispatch the Victory/Defeat/Draw clips (mute-gated), fireWinConfetti calls canvas-confetti, and prefersReducedMotion handles reduce / no-preference / missing-matchMedia. Both test files pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Celebration-hold hook + wire into finalizeGame and Bots.tsx</name>
  <files>frontend/src/hooks/useWinCelebrationHold.ts, frontend/src/hooks/__tests__/useWinCelebrationHold.test.ts, frontend/src/hooks/useBotGame.ts, frontend/src/pages/Bots.tsx</files>
  <behavior>
    - useWinCelebrationHold(outcome, userColor): returns `false` for null/loss/draw outcomes.
    - On a fresh human-win outcome with NOT reduced-motion: returns `true` immediately, then `false` after WIN_CELEBRATION_HOLD_MS (fake timers).
    - On a human win WITH reduced-motion: returns `false` (no hold).
    - Clears its timeout on unmount / when outcome resets to null.
  </behavior>
  <action>
    In useBotGame.ts `finalizeGame`, replace the single `playSound('game-end')` with
    outcome-based selection: human win (`finished.winner === settings.userColor`) →
    `playSound('game-win')` and, when `!prefersReducedMotion()`, call `fireWinConfetti()`;
    draw (`finished.reason === 'draw'`) → `playSound('game-draw')`; else → `playSound('game-loss')`.
    Import `fireWinConfetti`/`prefersReducedMotion` from `@/lib/confetti`. Do NOT also fire
    confetti/sound from Bots.tsx — the hook is the single firing site.

    Create `frontend/src/hooks/useWinCelebrationHold.ts` exporting `useWinCelebrationHold(outcome, userColor)`
    and a named `WIN_CELEBRATION_HOLD_MS` constant (~1300ms; a named constant, no magic number).
    It returns a boolean that is `true` only for a fresh human-win outcome while NOT reduced-motion,
    flipping to `false` after the delay via a cleared-on-cleanup `setTimeout`. Guard reduced-motion
    via `prefersReducedMotion()` so held-open never happens for reduced-motion users (and stays
    test-safe: no hold means no pending timer). Use a ref to detect the outcome transition so the
    hold fires once per game and resets when outcome goes null.

    In Bots.tsx, call the hook with `game.outcome` and `settings.userColor`, and change the
    dialog `open` prop from `!dialogDismissed` to `!dialogDismissed && !celebrationHold`. Leave
    the `dialogDismissed` reset effect and the `showResultStrip`/GameResultStrip path unchanged
    (the strip is gated on `dialogDismissed`, which is independent of the hold). Confirm no
    separate mobile result-modal path exists (same GameResultDialog serves both layouts).

    Create `frontend/src/hooks/__tests__/useWinCelebrationHold.test.ts` using `renderHook` +
    `vi.useFakeTimers()` and a stubbed `window.matchMedia` to cover the behaviors above.
  </action>
  <verify>
    <automated>cd frontend && npm test -- --run src/hooks/__tests__/useWinCelebrationHold.test.ts</automated>
  </verify>
  <done>finalizeGame plays the correct outcome sound and fires confetti on a human win only (respecting reduced-motion); the result modal is held closed for the delay window on a human win and opens immediately for loss/draw; hook test passes.</done>
</task>

<task type="auto">
  <name>Task 3: Full frontend gate (types, lint, tests, knip)</name>
  <files>frontend/</files>
  <action>
    Run the frontend pre-merge gate. A new dependency and a new SoundEvent union member are
    involved, so a type build is mandatory (esbuild strips types; lint+test do not type-check).
    Fix any drift surfaced (unused exports flagged by knip, missing `@types/canvas-confetti`,
    index-access narrowing under noUncheckedIndexedAccess). Do NOT run prettier.
  </action>
  <verify>
    <automated>cd frontend && npx tsc -b && npm run lint && npm test -- --run && npm run knip</automated>
  </verify>
  <done>tsc -b clean, ESLint clean, full frontend test suite green, knip reports no unused deps/exports.</done>
</task>

</tasks>

<verification>
- `cd frontend && npx tsc -b && npm run lint && npm test -- --run && npm run knip` all pass.
- Manual (optional): win a bot game in dev → Victory sound + confetti, modal appears after ~1.3s.
  Lose → Defeat sound, modal immediately. Draw → Draw sound, modal immediately. Mute toggle
  silences all three. OS reduced-motion → sound only, no confetti, immediate modal.
</verification>

<success_criteria>
- Outcome-specific sounds (Victory/Defeat/Draw) fire from finalizeGame, all mute-gated.
- Confetti fires on human win only, skipped under reduced-motion.
- Result modal is delayed by WIN_CELEBRATION_HOLD_MS on a win; immediate for loss/draw.
- No confetti/sound double-fire; loss/draw/new-game/result-strip paths unchanged.
- Full frontend gate green.
</success_criteria>

<output>
Create `.planning/quick/260723-tqn-add-bot-win-celebration-confetti-victory/260723-tqn-SUMMARY.md` when done.
</output>
