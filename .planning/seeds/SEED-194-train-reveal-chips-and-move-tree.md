---
id: SEED-194
status: planted
planted: 2026-10-08
planted_during: ad-hoc reveal UX review + sketch 008 (Phase 236 in flight in another session; milestone v2.21)
trigger_when: next Train UI phase, any further change to TrainReveal / free play, or before more reveal copy work
scope: medium-large (frontend only; TrainReveal + TrainSolveScreen + useTrainFreePlay rework, no backend change expected)
---

# SEED-194: Train reveal as verdict strip + line chips + one move tree

## Why This Matters

The post-solve reveal is the teaching moment, and on a phone it barely fits. Measured on the dev
build at 390x844 (screenshots in `temp/puzzle-reveal-ux/`, 2026-10-08):

| Area | Height | Share |
|---|---|---|
| Progress row | 36px | 4% |
| Board | ~318px | 38% |
| Bot bubble (verdict + Analyze/Next) | ~190px | 23% |
| Line cards | ~200px | 24% |
| Bottom nav | 61px | 7% |

- About 1.5 of the four cards (Your move, Your call, Best move, Played in game) are visible. Each
  line card costs ~110px for a one-row horizontal scroller showing ~5 moves.
- The bubble repeats the Your-call and Your-move cards' points.
- The board already shows all three moves as arrows (✓ ★ ??), so with every arrow lit at once the
  marks compete for attention.
- Free-move mode is a second model on the same screen: the cards swap to Stockfish + Moves, the
  bottom nav turns into board controls, and a separate Solution button undoes it. Next/Analyze
  scroll away with the bubble once the board sticks.

## Proposed Direction (sketch 008 winner, owner-approved)

Sketch: `.planning/sketches/008-train-reveal-mobile-layout/` (tab "Combined", phone + desktop);
decisions recorded under **008** in `.planning/sketches/MANIFEST.md`. Live artifact:
https://claude.ai/artifact/Kgry1SU4SQuMkky78y8jvv

1. **Verdict strip** replaces the bot bubble after the reveal: avatar + total-points pill + one line
   ("Right call, right move" / "Right call, best move" / "Right call, wrong move"). Tap expands
   the full bot verdict, the Your-call feedback and the also-fine moves. The Your-call card goes.
2. **Line chips** replace the three line cards: You / Best / Game, each with its mark, SAN and eval.
   **You merges with Best or Game** into one chip ("You = Best", "You = Game") and one arrow when
   the moves coincide.
3. **Chip-driven board:** the reveal opens with **You** active. Only the active chip's arrow and
   mark are opaque; every other arrow/mark (also-fine included) fades to ~20-30%, never hidden.
   A move played from the puzzle position that matches a line activates that line's chip.
4. **One move tree:** the three lines are pre-loaded branches of the `useAnalysisBoard` tree that
   free play already uses. The list shows the active chip's line (numbered, wrapping). Moving a
   piece anywhere forks a sideline in place with × to close it. No separate free-play mode and no
   card swap. A one-line Stockfish row (expandable to the second PV) shows only while off the known
   lines. Keep useTrainFreePlay's per-move grading markers on sideline moves.
5. **Phone action bar** replaces the bottom nav for the whole reveal (today it does so only in
   free play via `usePublishMobileBoardControls`): ⏮ ‹ › ⇅ + Analyze + Next. ⏮ is the old
   Solution button and keeps the sidelines. Acceptance: the first view fits 390x844 with no scroll.
6. **Desktop:** board left with the same controls and Analyze/Next under it; right column = full
   verdict bubble (no strip) + chips + move tree + game line. ← → step, Home = puzzle position.
7. **Onboarding tour rewritten for the new screen** (in scope, not a follow-up). Hilda's
   first-reveal walkthrough (`walkthroughCopy` in `lib/trainBotCopy.ts`, D-24, six steps,
   `WalkthroughStepCopy.spotlightTarget` = `verdict | lines | board | actions`) explains the
   current screen: "the cards below or on the right", "tap a card to highlight its move", "the
   arrows inside a card play its line", and a Solution button. All of that disappears. New steps
   need new targets and copy for: the verdict strip (and that tapping it opens the full feedback),
   the chips (tap to focus a line, the faded arrows, the "You = Best" merge), stepping with the
   bottom bar or tapping moves in the list, moving pieces to fork a sideline (and ⏮ to return),
   and the action bar. Keep D-21's "understand, don't memorize" step, the phone copy budget
   (`STEPPER_COPY_MAX_CHARS` = 145, calibrated at 375x667), and the "only describe what is on
   screen" rules (`hasAnalyze`: Analyze shows only for puzzles from the user's own games, which a
   first reveal often is not; `hasSolution` goes away with ⏮). The spotlight must reach the
   bottom action bar, which today is outside the reveal component. Re-run the phone UAT of the
   tour, as Phase 222 did.

## Where It Lands

- `frontend/src/components/train/TrainReveal.tsx` (1469 lines): cards, spotlight entries,
  `ROLE_TESTIDS`, the `isExploring` swap. Over the size guidance, so the rework is the seam to split it.
- `frontend/src/components/train/TrainSolveScreen.tsx` (1993 lines): `handlePieceDrop`'s free-play
  branch, `lineStep`, `isBoardDeparted`, the Solution/Analyze/Next row, mobile board controls.
- `frontend/src/hooks/useTrainFreePlay.ts`: seed the tree with the three lines instead of starting
  empty on the first free move; the free-play engine is created only while exploring today.
- `frontend/src/components/train/TrainLineStepper.tsx`: likely retired in favour of the tree list.
- `frontend/src/lib/trainArrows.ts`: per-chip opacity instead of the current spotlight.

## Watch Out For

- **Onboarding plumbing** beyond the copy (item 7): `useTrainOnboarding` (`reveal_walkthrough`
  step), `TrainBotStepper`, the walkthrough-active state in `TrainReveal` / `TrainSolveScreen`
  (Phase 222 D-24, Phase 233 D-13 sticky flag) and the think-time telemetry that keys off it.
- **Telemetry:** card engagement (`CardEngageKind` open / hover) and `train-explore-*` Umami events
  need new equivalents (chip select, tree jump, sideline fork, strip expand) or the funnels break.
- **Test ids** (`train-line-box-your-move` etc.) and the reveal tests depend on the card structure.
- SOLV-02 guardrail: the graded first move stays the only graded attempt; forking a sideline must
  never reach the grading path (see the comment block in `handlePieceDrop`).
- Herring / server-graded verdicts and the "Also fine" list (Phase 211 D-06 vetted moves) must keep
  their own marks when they appear as chips or sideline badges.
- The restored-reveal path (Analyze → Back, `CachedTrainReveal`) must restore the active chip and tree.
