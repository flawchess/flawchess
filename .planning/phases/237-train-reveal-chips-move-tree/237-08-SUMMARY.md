---
phase: 237-train-reveal-chips-move-tree
plan: 08
subsystem: ui
tags: [react, train, verdict-strip, copy, umami, reveal, tests]
status: complete

requires:
  - phase: 237-07 (one action bar for the whole reveal)
    provides: "TrainRevealActionBar owns rewind/back/forward/flip/Analyze/Next; the bubble action row and VerdictActions are gone"
provides:
  - "verdictClauseParts(correctGuess, moveQuality, isBest), verdictStripLine and verdictCopy(..., isBest, rng) in lib/trainBotCopy.ts: one table, 'best move' / 'good move' / 'decent move' / 'wrong move'"
  - "TrainVerdictDetails (+ moved TrainScoreChip): verdict paragraph, Your call + points, prose, motif, Also fine; shared by the strip expansion and the desktop bubble"
  - "TrainVerdictStrip: collapsed-by-default phone strip (avatar, total pill, one clause, chevron) with the train-verdict-strip panel-open event"
  - "TrainRevealGameFooter: the game footer split out of TrainReveal"
  - "TrainReveal verdict surface props verdictBot / verdictOpening / isBest / sessionDate / expiresOn / isWarmup / audience / onStripExpand; playedIsBest in TrainSolveScreen"
affects: [237-09, 237-10, 237-11]

tech-stack:
  added: []
  patterns:
    - "One copy table drives every verdict surface; isBest selects wording only, points come from GUESS_POINTS / MOVE_TIER_POINTS (the scorePuzzle sources)"
    - "Panel-open Umami event fired from the click handler on the collapsed -> open transition only"
    - "Phone/desktop gate by useIsDesktop inside TrainReveal: strip below lg, TrainBotBubble state=verdict at the top of the right column from lg"

key-files:
  created:
    - frontend/src/components/train/TrainVerdictDetails.tsx
    - frontend/src/components/train/TrainVerdictStrip.tsx
    - frontend/src/components/train/TrainRevealGameFooter.tsx
    - frontend/src/components/train/__tests__/TrainVerdictStrip.test.tsx
  modified:
    - frontend/src/lib/trainBotCopy.ts
    - frontend/src/lib/__tests__/trainBotCopy.test.ts
    - frontend/src/lib/analytics.ts
    - frontend/src/components/train/TrainReveal.tsx
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/__tests__/TrainReveal.test.tsx
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/components/train/__tests__/revealTestUtils.ts
    - frontend/src/pages/__tests__/Train.solveLoop.test.tsx

key-decisions:
  - "Also fine sits inside the train-verdict-guess block (after prose and motif) rather than as a sibling line, so the Your-call feedback stays one block and the existing 'within the guess block' tests keep their meaning; D-07 order (verdict, call + points, prose, motif, Also fine) is unchanged"
  - "While the first-reveal walkthrough runs, Hilda's bubble stays in the left slot and the verdict surface renders as normal (collapsed strip on phones, bubble in the right column on desktop, so two bubbles are on screen on desktop); plan 10 owns moving the tour"
  - "The verdict memo keeps playedIsBest in its deps as the plan says; the opener is a random draw, so it would redraw only if the best-move flag flipped mid-reveal (key move and graded best are the same UCI, so it does not in practice)"
  - "VerdictCopy.clause (bracket text) is still produced by verdictCopy for the copy tests, but no UI reads it any more; the UI renders pills from verdictClauseParts"

patterns-established:
  - "openVerdictStrip() test helper: waits for the reveal sentinel, clicks the strip, returns the details container"

requirements-completed: [D-05, D-06, D-07, D-08, D-14]

duration: 55 min
completed: 2026-10-09
actuals:
  tokens: 31400
  tasks: 3
  commits: 3
plan_head_before: 5f0394c8c8b21c36732b420f9d8d752b66ed5d0e
plan_head_after: 5c76a7149c2a3fb3ba6158435774c99d476ca3f7
commits: 3

coverage:
  - id: F1
    description: "D-05/D-06: the clause vocabulary ('best move' only when isBest and good tier; 'good move', 'decent move', 'wrong move', 'but the best move' / 'but a good move') comes from one table and agrees across the strip line, the bracket clause and the expanded pills; points still equal scorePuzzle"
    requirement: "D-06"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/trainBotCopy.test.ts#verdictClauseParts / verdictCopy clause / verdictStripLine (Phase 237 D-05/D-06)"
        status: pass
    human_judgment: false
  - id: F2
    description: "On a phone a best-move solve shows the collapsed strip 'Right call, best move' with the +3 total, no bubble and no Your-call card; tapping it shows verdict line, then Your call, then prose, with no Analyze button"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#tracer: a best-move solve shows the collapsed strip with its total and expands to the full feedback"
        status: pass
    human_judgment: false
  - id: F3
    description: "D-08: the strip is collapsed on a fresh reveal, on a restored reveal and on the next puzzle's reveal, regardless of score. Proven by flipping the initial state to true (four tests went red), then restored"
    requirement: "D-08"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#D-08: the strip is collapsed again on the next puzzle's reveal, even after the user opened it"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#a restored reveal keeps the verdict bot recorded in the reveal cache"
        status: pass
    human_judgment: false
  - id: F4
    description: "D-14: expanding the strip sends exactly one panel-open / train-verdict-strip, via the click handler; nothing on mount, collapse, or restore; the target is registered in PANEL_TARGETS"
    requirement: "D-14"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainVerdictStrip.test.tsx"
        status: pass
    human_judgment: false
  - id: F5
    description: "Desktop keeps the full verdict bubble (data-state verdict) as the first element of the reveal column with details visible, no strip, and exactly one bubble on screen outside the walkthrough; phones show the strip instead"
    verification:
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx#desktop: the verdict is the full bubble at the top of the reveal column, details visible, no strip"
        status: pass
      - kind: unit
        ref: "frontend/src/components/train/__tests__/TrainReveal.test.tsx#phone: the strip replaces the bubble and the Your-call card, collapsed, with the isBest wording"
        status: pass
    human_judgment: false
  - id: F6
    description: "TrainReveal split along its seams: TrainVerdictDetails, TrainVerdictStrip and TrainRevealGameFooter are their own components (footer behavior and testids unchanged)"
    verification:
      - kind: command
        ref: "grep -c useLibraryGame frontend/src/components/train/TrainReveal.tsx prints 0; grep -c 'right move' frontend/src/lib/trainBotCopy.ts prints 0"
        status: pass
    human_judgment: false
  - id: F7
    description: "Full gate: lint, tsc -b build, knip, full vitest suite (320 files, 5384 tests)"
    verification:
      - kind: command
        ref: "npm run lint && npm run build && npm run knip && npm test -- --run"
        status: pass
    human_judgment: false
  - id: F8
    description: "Strip height, the one-line truncation, the chevron, and the 390x844 no-scroll first view look right on a real phone; the desktop bubble at the top of the right column aligns with the board top"
    verification:
      - kind: manual
        ref: "plan 11 browser UAT (jsdom has no layout)"
        status: pending
    human_judgment: true
---

# Phase 237 Plan 08: Verdict Strip and One Vocabulary Summary

**On phones the verdict bubble and the Your-call card are replaced by a one-line strip (bot avatar, total pill, "Right call, best move") that starts collapsed and opens to the full feedback; desktop keeps the full bubble at the top of the right column; one copy table now drives "best move" / "good move" / "decent move" / "wrong move" on every surface.**

## Performance

- **Duration:** 55 min
- **Tasks:** 3 (1 tracer, 1 auto/tdd, 1 auto), 3 commits
- **Files:** 4 created, 9 modified (frontend only)

## Accomplishments

- `trainBotCopy`: `verdictClauseParts(correctGuess, moveQuality, isBest)` implements the 8-row table (points from `GUESS_POINTS` / `MOVE_TIER_POINTS`, guard clauses, React-free); `verdictClause` is built from it; `verdictStripLine` gives `"<guess>, <move>"`; `verdictCopy` takes `isBest` before `rng`. The old "right move" wording is gone.
- `TrainVerdictDetails` holds the verdict paragraph (all `train-bot-*` testids, the return-tail rule and the Pitfall 7 missing-`source` guard unchanged), the Your-call block (`train-verdict-guess`, points chip, prose, motif, Also fine with its "e.g." comment), and the moved `TrainScoreChip`.
- `TrainVerdictStrip`: a `<button aria-expanded data-testid="train-verdict-strip">` row (avatar with `data-persona-id` / `data-persona-name`, `TrainScoreChip`, truncating `text-sm` line, rotating chevron) plus a `train-verdict-strip-details` body only while open. Fires `trackFeature('panel-open', { target: 'train-verdict-strip' })` from the click handler on collapsed -> open, then `onExpand`.
- `TrainReveal` renders the verdict surface first (`useIsDesktop`: bubble or strip), then the flaw-fixed banner, error line, chips, list and `TrainRevealGameFooter`. `TrainSolveScreen` drops its local clause helpers and bubble body (the left slot now speaks only for the walkthrough), computes `playedIsBest` (the chip-merge predicate) and passes bot, opening, schedule dates, warm-up and audience down.
- Tests: vocabulary table, strip unit test, phone and desktop reveal renders, D-08 on a following puzzle and on restore, 68 Your-call-card waits replaced by `waitForReveal()` (71 uses in the screen test), solveLoop reads the strip total and then the expanded pills.

## Task Commits

1. **Task 1 (tracer):** `081690ab6` (feat)
2. **Task 2: vocabulary and strip tests, game footer split:** `122506ae3` (feat)
3. **Task 3: sentinel sweep and verdict test port:** `5c76a7149` (test)

Tracer gate: the `<verify>` set (`-t "collapsed strip"` and `npm run build`) passed before the expansion work.

## Verification

- `npm run lint`, `npm run build`, `npm run knip` clean; full frontend suite 320 files, 5384 tests pass.
- Acceptance greps: `export function verdictClauseParts` / `verdictStripLine`, `export function TrainVerdictDetails` / `TrainScoreChip`, `data-testid="train-verdict-strip"`, `'train-verdict-strip'` in analytics.ts, `export function TrainRevealGameFooter` all match; `function verdictClauseParts` in TrainSolveScreen, `useLibraryGame` in TrainReveal and `right move` in trainBotCopy all print 0; `playedIsBest` appears 3 times in the screen.
- Mutation proof: initial `expanded` set to `true` turned the tracer, the strip unit test, the D-08 test and the walkthrough-strip test red; restored.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 1 commit leaves the wider suite red until Task 3**
- **Issue:** Removing the Your-call card and moving the verdict into the reveal broke the TrainReveal fixtures (new required props) and the walkthrough and solve-loop tests, which the plan ports in Task 3. Porting them inside the tracer commit would have mixed ~70 mechanical test edits into it, so the tracer commit carries only the tracer test; the suite was green again at commit `5c76a7149`.
- **Commits:** 081690ab6, 5c76a7149

**2. [Rule 1 - Bug (test)] Also fine moved inside the Your-call block**
- **Issue:** My first TrainVerdictDetails rendered Also fine as a sibling after the call block, which broke the "inside the guess block" tests and made the motif row lose its explicit `text-sm`.
- **Fix:** Also fine now sits inside `train-verdict-guess` after the motif, and prose, motif and Also fine carry an explicit `text-sm` (frontend minimum font size, independent of the container).
- **Commit:** 5c76a7149

**3. [Rule 1 - Bug (test)] Flaw-fixed banner test and the two walkthrough tests**
- The banner now follows the verdict surface (planning-note order), so its test asserts verdict bubble -> banner -> chips. The two walkthrough tests that read `train-bot-name` / `train-bot-copy` found two bubbles on desktop (Hilda's plus the verdict) and now run on a phone, where Hilda's bubble is followed by the collapsed strip.
- **Commit:** 5c76a7149

**Total deviations:** 3 auto-fixed (2 Rule 1, 1 Rule 3). **Impact:** no scope change.

### Notes

- **Desktop shows two bubbles during the first-reveal walkthrough** (Hilda in the left slot, the verdict in the right column). That matches the planning note that the tour stays in the left slot until plan 10 moves it into the reveal column.
- `VerdictCopy.clause` is now only exercised by the copy tests; if plan 10/11 wants to prune it, `verdictCopy` is the single producer.
- Strip layout is jsdom-unverified: row height, truncation of long clauses at 375px, the chevron, and the 390x844 no-scroll target belong to plan 11's browser UAT (F8, pending).

## Known Stubs

None.

## Threat Flags

None. T-237-14 holds: the strip total is `scorePuzzle(verdict.correct_guess, verdict.move_quality)`, `isBest` only picks wording, and the vocabulary tests assert the clause points equal `scorePuzzle` for all 8 rows; the Phase 236 D-09 surface test now checks the strip total and expanded pill against the server verdict. T-237-15 holds: literal `panel-open` / `train-verdict-strip`, registered in `PANEL_TARGETS`, fired only from the click handler, no verdict text in props.

## Next Phase Readiness

Plan 09 can feed the v2 telemetry off `onStripExpand` (the prop is wired and optional) and the chip select; plan 10 can move the walkthrough bubble into the reveal column and ring the strip (`train-verdict-strip` is the target); plan 11's browser UAT owns F8.

## Self-Check: PASSED

- FOUND: frontend/src/components/train/TrainVerdictDetails.tsx, TrainVerdictStrip.tsx, TrainRevealGameFooter.tsx, __tests__/TrainVerdictStrip.test.tsx
- FOUND: `export function verdictClauseParts`, `export function verdictStripLine` in trainBotCopy.ts; `'train-verdict-strip'` in analytics.ts
- FOUND commits: 081690ab6, 122506ae3, 5c76a7149
