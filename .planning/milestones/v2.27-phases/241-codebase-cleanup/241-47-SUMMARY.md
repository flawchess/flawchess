---
phase: 241-codebase-cleanup
plan: 47
subsystem: frontend-tests
tags: [cleanup, comments, test-titles, vitest, train]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff"
  - phase: 241-03
    provides: "cleanup.py codemod"
  - phase: 241-04
    provides: "TypeScript/JSX support in cleanup.py"
provides:
  - "Train component tests (27 files in scopes/241-47.txt) free of planning tags in comments and describe/it/test titles"
affects: [241-57, 241-69]

actuals:
  tokens: 57000
  tasks: 2
  commits: 2
plan_head_before: 1cee4f3aafad21ee45340b5560864b51abf3bf69
plan_head_after: 734e62199c993399c084c57b2c6fc175a07bbdb2

tech-stack:
  added: []
  patterns:
    - "Hand edits batched through a small temp helper (temp/241-47/lib.py) that reads the old text from the file and feeds cleanup.py apply-edits, so line numbers and old text can never drift"

key-files:
  created: []
  modified:
    - frontend/src/components/train/__tests__/TrainSolveScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainReveal.test.tsx
    - frontend/src/components/train/__tests__/TrainStartScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainScheduleSettings.test.tsx
    - frontend/src/components/train/__tests__/TrainReminderButton.test.tsx
    - frontend/src/components/train/__tests__/TrainScoreScreen.test.tsx
    - frontend/src/components/train/__tests__/TrainLeaderboardCard.test.tsx
    - frontend/src/components/train/__tests__/TrainLineChips.test.tsx

key-decisions:
  - "Titles lose their tag prefix or suffix and nothing else; where the tag was the only content of a clause (for example 'Phase 203 fix (Rule 1): ... the old eight-condition cascade used to hide ...') the title was shortened to the behavior checked"
  - "Leftover provenance the scan regex cannot see ('190.1 UAT round 4', 'Sketch 004', 'quick 260814-b', 'Plan 04 UAT round 1', 'UAT item 5', 'round 7', dated '2026-08-03 fix') was removed with the tags, found by a broad grep over the scope"
  - "Bare '<file>.test.tsx.' header lines left behind by the codemod were deleted as provenance-only"

requirements-completed: [D-01, D-03, D-05, D-11, D-12, D-13, D-14, D-15]

duration: 30min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 47: Train Component Tests Summary

**All planning tags and tag-bearing test titles are gone from the 27 Train component test files, with test bodies, assertions, testids and mock factories untouched and the vitest count unchanged at 678.**

## Accomplishments

- First scan of scopes/241-47.txt: 452 matches (165 of them test titles). Final `scan --gate --advisory`: 0 matches. `cleanup.py diff --scope`: exit 0, 27 selected, 25 changed (LastWeekPodium.test.tsx and MedalTally.test.tsx were already clean and stay untouched).
- `src/components/train` vitest: 26 files, 678 tests before and after (the first baseline run hit one load-related timeout under concurrent sibling executors; rerun was 678 passed, and every later run was 678 passed).
- Codemod: 93 lines changed in 19 files (dry run read first, then written; no dangling-punctuation starts found by the `^\s*(#|//|\*)\s*[:;,.]\s` grep). Hand edits: 440 apply-edits spans in 12 batches (about 185 test/describe titles, the rest comments), including 28 comment blocks rewritten from history narration into present tense.
- Rewritten titles: 175 (listed below). `cleanup.py diff` found no duplicate-title collisions.

## Task Commits

1. **Task 1: solve screen, reveal, reveal bars, move tree, chips, verdict strip, bubble state** - `92f5d80fc` (`chore(comments): frontend Train solve and reveal tests`)
2. **Task 2: remaining Train component and medal tests** - `734e62199` (`chore(comments): frontend Train component tests (rest)`). It also carries the last leftover-provenance fixes in two Task 1 files (TrainReveal, TrainSolveScreen) and the bare-header deletions in TrainVerdictStrip and TrainRevealActionBar, found by the broad grep after Task 1 was committed.

`commits: 2` is measured with `git rev-list --count plan_head_before..HEAD` before this SUMMARY commit.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --advisory --scope scopes/241-47.txt` | 0 matches |
| `cleanup.py diff --scope scopes/241-47.txt` | exit 0 |
| `cleanup.py diff frontend/src/components/train/__tests__` (after Task 1) | exit 0 |
| `npm --prefix frontend test -- src/components/train` | 26 files, 678 passed (baseline 678) |
| `npm --prefix frontend run lint` | clean |
| `source_scan_tests.sh --fe` | 9 files, 131 passed |
| python half of source_scan_tests.sh, run serially without `-n 4` | 95 passed + 5 passed |

The python half was run serially because sibling executors share the dev Postgres (environmental, per the dispatch note).

## Rewritten test titles (old -> new)

**SignupAskActions.test.tsx**

- `with source="train-landing" (224 UAT round 2, guest Train landing bubble) the testids and umami source follow suit` -> `with source="train-landing" (guest Train landing bubble) the testids and umami source follow suit`

**TrainBotBubble.test.tsx**

- `re-keys on nudgeNonce so a repeated nudge remounts the bubble element (RESEARCH Pitfall 3)` -> `re-keys on nudgeNonce so a repeated nudge remounts the bubble element`

**TrainLeaderboardCard.test.tsx**

- `TrainLeaderboardCard tabs (D-07, D-09, D-10)` -> `TrainLeaderboardCard tabs`
- `D-19: a viewer with Points entries but no Accuracy entry gets the not-entered line` -> `a viewer with Points entries but no Accuracy entry gets the not-entered line`
- `TrainLeaderboardCard Umami tab-switch (Phase 229 registry)` -> `TrainLeaderboardCard Umami tab-switch`
- `TrainLeaderboardCard countdown and private rows (D-02, D-13, D-14)` -> `TrainLeaderboardCard countdown and private rows`
- `retries the rollover while the refetch still carries the old week, then stops on the new week (WR-03)` -> `retries the rollover while the refetch still carries the old week, then stops on the new week`
- `caps the rollover retries when the server keeps returning the old week (WR-03)` -> `caps the rollover retries when the server keeps returning the old week`
- `TrainLeaderboardCard last-week podium (Phase 231, D-07..D-09)` -> `TrainLeaderboardCard last-week podium`
- `renders no podium when last_week is null (D-08)` -> `renders no podium when last_week is null`
- `renders no podium when the podium is empty, even with a viewer_final_rank (D-07)` -> `renders no podium when the podium is empty, even with a viewer_final_rank`
- `renders a name containing markup as literal text (T-231-14)` -> `renders a name containing markup as literal text`
- `TrainLeaderboardCardView (Phase 231 seam)` -> `TrainLeaderboardCardView`
- `TrainLeaderboardCard lifetime medal tally (Phase 231)` -> `TrainLeaderboardCard lifetime medal tally`
- `TrainLeaderboardCard last-week finish line (Phase 231, D-03)` -> `TrainLeaderboardCard last-week finish line`

**TrainLineChips.test.tsx**

- `labels the chip eval as the graded reading (SEED-197)` -> `labels the chip eval as the graded reading`
- `hides the eval pill for an eval-less stand-in line instead of a permanent "…" (WR-01)` -> `hides the eval pill for an eval-less stand-in line instead of a permanent "…"`
- `a merged your + best chip renders ONE button labelled "Move = Best" (D-02)` -> `a merged your + best chip renders ONE button labelled "Move = Best"`
- `a merged your + game chip renders "Move = Game" (D-02)` -> `a merged your + game chip renders "Move = Game"`
- `no chip is pressed when none is active (D-04)` -> `no chip is pressed when none is active`
- `a loading chip shows a spinner instead of an eval (Phase 236 D-14)` -> `a loading chip shows a spinner instead of an eval`
- `a failed chip keeps SAN and mark but renders no eval and no spinner (Phase 236 D-15)` -> `a failed chip keeps SAN and mark but renders no eval and no spinner`

**TrainReminderButton.test.tsx**

- `Phase 203 fix (Rule 1): device already subscribed at mount now renders the confirmed span, not nothing — the old eight-condition cascade used to hide this legitimately-subscribed state entirely` -> `a device already subscribed at mount renders the confirmed span, not nothing`
- `D-05: reminder_enabled true from the server plus no local subscription still renders the button (per-device asymmetry, not a bug to reconcile)` -> `reminder_enabled true from the server plus no local subscription still renders the button (per-device asymmetry, not a bug to reconcile)`
- `pushApi.subscribe rejects: the button keeps its "Remind me" label, stays enabled, the D-13 error copy renders BELOW it, and updateSettings is never called (Plan 04 UAT round 1: deviates from D-13\'s literal "in place" wording — see TrainReminderButton.tsx module docstring)` -> `pushApi.subscribe rejects: the button keeps its "Remind me" label, stays enabled, the error copy renders BELOW it, and updateSettings is never called (see the TrainReminderButton.tsx module docstring)`
- `trainApi.updateSettings rejects after a successful subscribe: the button keeps its "Remind me" label and the D-13 error copy renders below it (never claims reminders are on when the server did not confirm)` -> `trainApi.updateSettings rejects after a successful subscribe: the button keeps its "Remind me" label and the error copy renders below it (never claims reminders are on when the server did not confirm)`
- `Standalone, subscribed: confirmed span only, neither the install offer nor the QR block (OFFER-04)` -> `Standalone, subscribed: confirmed span only, neither the install offer nor the QR block`
- `iOS tabbed, unsubscribed: nothing renders (unchanged from today; the iOS render lands in Plan 04)` -> `iOS tabbed, unsubscribed: nothing renders`
- `a failed subscribe keeps the "Remind me" label and renders the error copy below it (Plan 04 UAT round 1 deviation from D-13; unaffected by the resolver refactor)` -> `a failed subscribe keeps the "Remind me" label and renders the error copy below it`
- `desktop phone block (Phase 222 UAT round 5)` -> `desktop phone block`
- `iOS-tabbed slot (OFFER-03, D-14/D-15)` -> `iOS-tabbed slot`
- `after the tap resolves, the instructions render below the row with their own test id, and the button stays present and re-enabled (Plan 04 UAT round 2 deviation from D-15\'s "in place" wording — see TrainReminderButton.tsx module docstring)` -> `after the tap resolves, the instructions render below the row with their own test id, and the button stays present and re-enabled (see the TrainReminderButton.tsx module docstring)`
- `when the mutation rejects, the instructions body still renders (fail-open, D-15)` -> `when the mutation rejects, the instructions body still renders (fail-open)`

**TrainReminderResurfaceBanner.test.tsx**

- `renders nothing when shouldResurface is false (empty per OFFER-05/D-16)` -> `renders nothing when shouldResurface is false`
- `a dismissed subscribe prompt leaves the banner standing with no error copy (PERM-02 precedent)` -> `a dismissed subscribe prompt leaves the banner standing with no error copy`

**TrainReveal.test.tsx**

- `Phase 237 plan 10 / Phase 240 D-20: reveal tour spotlights and bubble slot` -> `reveal tour spotlights and bubble slot`
- `onGameMoveUciChange reports the resolved game-move UCI, and null on unmount (190.1-04)` -> `onGameMoveUciChange reports the resolved game-move UCI, and null on unmount`
- `onGameMoveLineStateChange reports loading, then the searched line, and idle on unmount (Phase 237)` -> `onGameMoveLineStateChange reports loading, then the searched line, and idle on unmount`
- `a game-move search that never settles stays in the loading state, and the verdict rows still render (190.1-01 Task 2)` -> `a game-move search that never settles stays in the loading state, and the verdict rows still render`
- `a rejecting game-move search reports the error state, and the other reveal blocks still render (190.1-01 Task 2)` -> `a rejecting game-move search reports the error state, and the other reveal blocks still render`
- `a tactic-tagged reveal renders NO tactic opt-in trigger (removed, UAT round 4)` -> `a tactic-tagged reveal renders NO tactic opt-in trigger`
- `an sr_item verdict with puzzle_type "sharp" (the exact literal a sharp_filler also carries) still renders all three D-19 sites — proves the predicate reads source, not puzzle_type` -> `an sr_item verdict with puzzle_type "sharp" (the exact literal a sharp_filler also carries) still renders all three own-game sites — proves the predicate reads source, not puzzle_type`
- `the guess card keeps the verdict and its score chip in the header, and only the Also fine list in the body (round 7: the herring sentence is gone)` -> `the guess card keeps the verdict and its score chip in the header, and only the Also fine list in the body (the herring sentence is gone)`
- `a confirmed disagreement names the key for both guesses, whatever the other inputs (D-15)` -> `a confirmed disagreement names the key for both guesses, whatever the other inputs`
- `a disagreement without a key SAN falls through to the existing chain (D-15)` -> `a disagreement without a key SAN falls through to the existing chain`
- `a server-confirmed disagreement renders the D-15 line naming the key SAN on the guess card (D-15)` -> `a server-confirmed disagreement renders the disagreement line naming the key SAN on the guess card`
- `a verdict without the disagreement field keeps the old copy even when a key is known (D-15)` -> `a verdict without the disagreement field keeps the old copy even when a key is known`
- `instant-path game-move search (Phase 236)` -> `instant-path game-move search`
- `the grade landing with the same best UCI does not re-dispatch the game-move search (RESEARCH Pitfall 5)` -> `the grade landing with the same best UCI does not re-dispatch the game-move search`
- `TrainReveal feature events (Phase 229)` -> `TrainReveal feature events`

**TrainScheduleSettings.test.tsx**

- `191-06 UAT bug fix: a resolved updateSettings calls onSaved exactly once` -> `a resolved updateSettings calls onSaved exactly once`
- `191-06: a rejected updateSettings never calls onSaved` -> `a rejected updateSettings never calls onSaved`
- `HANDOFF-04: on desktop, renders the qr-handoff-settings block with no dismiss control inside it` -> `on desktop, renders the qr-handoff-settings block with no dismiss control inside it`
- `HANDOFF-04: on desktop, the QR block still renders even when push is unsupported (unconditional, unlike ReminderControls)` -> `on desktop, the QR block still renders even when push is unsupported (unconditional, unlike ReminderControls)`
- `phone section platform gating (UAT item 5 regression)` -> `phone section platform gating`
- `reminder toggle and hour picker (PERM-03/PERM-04)` -> `reminder toggle and hour picker`
- `D-11 mount-time reconciliation: reminder_enabled true from the server plus permission denied never issues a PUT (render-only, no silent account-wide disable)` -> `mount-time reconciliation: reminder_enabled true from the server plus permission denied never issues a PUT (render-only, no silent account-wide disable)`
- `PERM-04: toggling off from an enabled state issues exactly one updateSettings call with reminder_enabled: false, and never touches subscribe or unsubscribe` -> `toggling off from an enabled state issues exactly one updateSettings call with reminder_enabled: false, and never touches subscribe or unsubscribe`
- `PERM-03: changing the hour issues exactly one updateSettings call whose reminder_hour is the chosen value and whose weekday_mask/puzzles_per_session are unchanged` -> `changing the hour issues exactly one updateSettings call whose reminder_hour is the chosen value and whose weekday_mask/puzzles_per_session are unchanged`
- `TrainScheduleSettings — D-13 guest visibility (Phase 224)` -> `TrainScheduleSettings — guest visibility`
- `collapsed schedule card (SEED-181)` -> `collapsed schedule card`

**TrainScoreRankLines.test.tsx**

- `TrainScoreRankLines variants (D-17, D-18, D-19)` -> `TrainScoreRankLines variants`
- `a guest reads "You\'d be #N" and the lines hold no button (D-17)` -> `a guest reads "You\'d be #N" and the lines hold no button`
- `a worse Accuracy rank shows the plain rank, never a down delta (D-18)` -> `a worse Accuracy rank shows the plain rank, never a down delta`
- `a viewer with Points but no Accuracy entry gets the not-entered line (D-19)` -> `a viewer with Points but no Accuracy entry gets the not-entered line`

**TrainScoreScreen.test.tsx**

- `TrainScoreScreen rank lines (Phase 230 D-11)` -> `TrainScoreScreen rank lines`
- `Done renders variant="default" (the brand-brown solid fill, per D-04)` -> `Done renders variant="default" (the brand-brown solid fill)`
- `below-row overflow content (Plan 04 UAT round 1)` -> `below-row overflow content`
- `confirmed-state placement — control null, Done alone spans full width (Plan 04 UAT round 3)` -> `confirmed-state placement — control null, Done alone spans full width`
- `the score bubble (D-25)` -> `the score bubble`
- `BUG FIX (UAT round 5): the first-completed copy survives the stamp writing sr_explained_at back into the settings cache` -> `the first-completed copy survives the stamp writing sr_explained_at back into the settings cache`
- `a first warm-up session carries the rationale in line 1, no return text, and stamps exactly once (D-21)` -> `a first warm-up session carries the rationale in line 1, no return text, and stamps exactly once`
- `a first perfect session carries the rationale after "Nothing got away today." and stamps exactly once (D-17, D-21)` -> `a first perfect session carries the rationale after "Nothing got away today." and stamps exactly once`
- `the guest branch (S-3, S-4, GUESTACT-05)` -> `the guest branch`
- `quick 260926-8p5: a registered zero-game warm-up renders the Import games button in the bubble, no sign-up pair` -> `a registered zero-game warm-up renders the Import games button in the bubble, no sign-up pair`

**TrainSolveScreen.test.tsx**

- `keyed puzzle: grades against the server key and the best arrow names it (Phase 235)` -> `keyed puzzle: grades against the server key and the best arrow names it`
- `keyed puzzle: an off-key move POSTs the 1.5 s phone_grade record (Phase 236 D-01/D-13)` -> `keyed puzzle: an off-key move POSTs the 1.5 s phone_grade record`
- `sharp keyed puzzle: an off-key good move is re-checked and the POST carries the record (Phase 235 D-10/D-11/D-17)` -> `sharp keyed puzzle: an off-key good move is re-checked and the POST carries the record`
- `playing the sharp runner-up posts no recheck (D-19)` -> `playing the sharp runner-up posts no recheck`
- `a soft keyed puzzle posts no recheck (D-10)` -> `a soft keyed puzzle posts no recheck`
- `an off-key inaccuracy on a soft puzzle is re-checked and upgraded to good (quick 261008-ob1)` -> `an off-key inaccuracy on a soft puzzle is re-checked and upgraded to good`
- `an off-key inaccuracy the 3 s pair still reads as inaccuracy stays inaccuracy (quick 261008-ob1)` -> `an off-key inaccuracy the 3 s pair still reads as inaccuracy stays inaccuracy`
- `keyed puzzle: playing the key POSTs phone_grade good with played == key (Phase 236 D-05)` -> `keyed puzzle: playing the key POSTs phone_grade good with played == key`
- `legacy no-key puzzle: the POST carries no phone_grade (Phase 236 D-06)` -> `legacy no-key puzzle: the POST carries no phone_grade`
- `a re-check replaces the grade but phone_grade keeps the 1.5 s reading (Phase 236 D-04)` -> `a re-check replaces the grade but phone_grade keeps the 1.5 s reading`
- `a retried keyed solve re-sends the identical payload, phone_grade included (Phase 236 D-13)` -> `a retried keyed solve re-sends the identical payload, phone_grade included`
- `a server-graded move is never re-checked: no 3 s search, no recheck in the body (Phase 236 D-11)` -> `a server-graded move is never re-checked: no 3 s search, no recheck in the body`
- `a stalled re-check falls back to the 1.5 s grade and posts no recheck (D-20)` -> `a stalled re-check falls back to the 1.5 s grade and posts no recheck`
- `the bubble reads "Taking a closer look…" while the re-check runs, then the verdict replaces it (D-12)` -> `the bubble reads "Taking a closer look…" while the re-check runs, then the verdict replaces it`
- `a retried solve re-sends the identical payload, recheck included, and never re-runs the re-check (D-17)` -> `a retried solve re-sends the identical payload, recheck included, and never re-runs the re-check`
- `board holds the played-move position through grading (no flicker/remount), then snaps back to the puzzle position once the reveal opens (190-05 D-08)` -> `board holds the played-move position through grading (no flicker/remount), then snaps back to the puzzle position once the reveal opens`
- `retrying after an onerror engine failure lets a subsequent move actually grade instead of hanging forever (WR-01)` -> `retrying after an onerror engine failure lets a subsequent move actually grade instead of hanging forever`
- `quality badges (squareMarkers) land on the board alongside the arrows once the verdict has settled (190.1 UAT)` -> `quality badges (squareMarkers) land on the board alongside the arrows once the verdict has settled`
- `quick 261009-por / SEED-197: while the live PV is shallower than the replacement depth the graded tail stays the pointer and a disagreeing engine move is a secondary arrow` -> `while the live PV is shallower than the replacement depth the graded tail stays the pointer and a disagreeing engine move is a secondary arrow`
- `SEED-197: once the live PV reaches the replacement depth it becomes the preview and the board pointer` -> `once the live PV reaches the replacement depth it becomes the preview and the board pointer`
- `D-01: tapping a chip while stepped into another line returns the board to the puzzle position with that chip\'s arrow lit` -> `tapping a chip while stepped into another line returns the board to the puzzle position with that chip\'s arrow lit`
- `D-01: tapping the chip whose own line is on the board does not move the board` -> `tapping the chip whose own line is on the board does not move the board`
- `D-02: playing the best move shows ONE chip labelled "Move = Best" and one lit arrow` -> `playing the best move shows ONE chip labelled "Move = Best" and one lit arrow`
- `the reveal opens with You lit — three arrows and three badges are drawn, only the You move is lit — and tapping Game then Best moves the light (Phase 237 dim-not-hide)` -> `the reveal opens with You lit — three arrows and three badges are drawn, only the You move is lit — and tapping Game then Best moves the light`
- `a puzzle with no played-in-game move shows two chips and draws only the your-move and best-move arrows (filler puzzles are unaffected by 260902-qf7)` -> `a puzzle with no played-in-game move shows two chips and draws only the your-move and best-move arrows (filler puzzles are unaffected)`
- `a herring puzzle with three drawn alternatives lists all three SANs in the guess card; the alternatives stay DIMMED on the board whichever chip is focused (Phase 237)` -> `a herring puzzle with three drawn alternatives lists all three SANs in the guess card; the alternatives stay DIMMED on the board whichever chip is focused`
- `VETFINE-03: the played-move badge derives from the verdict\'s graded_es_* pair even when the client engine\'s own search implies a blunder (the server override wins on the board)` -> `the played-move badge derives from the verdict\'s graded_es_* pair even when the client engine\'s own search implies a blunder (the server override wins on the board)`
- `VETFINE-03 (pre-211 cache shape): a verdict with NO vetted_moves key draws and lists only live alternatives, never a certified one (quick 261010-e5l), and nothing throws` -> `a verdict with NO vetted_moves key (a cache shape from an older bundle) draws and lists only live alternatives, never a certified one, and nothing throws`
- `ORACLE-01: playing a served "Also fine" vetted move as the FIRST free-play move is badged with the server\'s own quality, never a fresh (worse) free-play-engine search` -> `playing a served "Also fine" vetted move as the FIRST free-play move is badged with the server\'s own quality, never a fresh (worse) free-play-engine search`
- `D-04 residual (deliberate): a FIRST free-play move NOT among the mount ranks still comes from the free-play engine\'s own (worse) search` -> `deliberate residual: a FIRST free-play move NOT among the mount ranks still comes from the free-play engine\'s own (worse) search`
- `Phase 222 (D-10): the mute toggle is retired — no board-btn-mute renders once the verdict lands` -> `the mute toggle is retired — no board-btn-mute renders once the verdict lands`
- `a live 3-point solve plays the per-puzzle score-full sound and pops the "Points: +3" flash over the board (190.1 UAT round 7, SEED-119 max)` -> `a live 3-point solve plays the per-puzzle score-full sound and pops the "Points: +3" flash over the board`
- `a REMOUNT (dev-clock time travel -> new session) replays neither the previous session’s result sound nor its points flash (Phase 200 UAT round 7)` -> `a REMOUNT (dev-clock time travel -> new session) replays neither the previous session’s result sound nor its points flash`
- `a puzzle without a source game links Analyze to its position; the bar still has Next and rewind (Phase 237 plan 07)` -> `a puzzle without a source game links Analyze to its position; the bar still has Next and rewind`
- `driving one puzzle to a correct-guess good-move verdict shows the accumulated score and a max of one times TRAIN_POINTS_PER_PUZZLE (SEED-119: 3)` -> `driving one puzzle to a correct-guess good-move verdict shows the accumulated score and a max of one times TRAIN_POINTS_PER_PUZZLE (3)`
- `train-progress, train-progress-bar and train-session-score share one compact row (phase 222 UAT)` -> `train-progress, train-progress-bar and train-session-score share one compact row`
- `D-10: a restored pre-Phase-205 reveal (gradeResult carrying no rank lines) grades its root fork from the reveal engine\'s own path, never throwing` -> `a restored older reveal (gradeResult carrying no rank lines) grades its root fork from the reveal engine\'s own path, never throwing`
- `Phase 200 (D-12): the side to move follows the sideline, turn order stays fully enforced, and no move is ever auto-played onto the board` -> `the side to move follows the sideline, turn order stays fully enforced, and no move is ever auto-played onto the board`
- `SOLV-02: two post-verdict forks never reach grading or the solve POST: solvePuzzle runs once and the grading Worker is asked for no further search` -> `two post-verdict forks never reach grading or the solve POST: solvePuzzle runs once and the grading Worker is asked for no further search`
- `Stockfish arrows 0 (Phase 228 D-13): a sideline draws no live secondary arrow (only the preview pointer), yet the reveal legend arrows still draw and return after Solution` -> `Stockfish arrows 0: a sideline draws no live secondary arrow (only the preview pointer), yet the reveal legend arrows still draw and return after Solution`
- `the Analyze link href is unchanged on a sideline (EXPLORE-06)` -> `the Analyze link href is unchanged on a sideline`
- `ORACLE-02: a served vetted move replayed at ply 3 (not the root) is graded from the engine\'s own parent/child pair: a scripted bad score still badges it worse` -> `a served vetted move replayed at ply 3 (not the root) is graded from the engine\'s own parent/child pair: a scripted bad score still badges it worse`
- `D-04: a hand-played move that matches a line lights that chip without creating a sideline; a move that matches none deselects every chip and lists only the user line` -> `a hand-played move that matches a line lights that chip without creating a sideline; a move that matches none deselects every chip and lists only the user line`
- `sideline feature events (D-14)` -> `sideline feature events`
- `rewind sends exactly one train-solution action per press and nothing on render (D-14)` -> `rewind sends exactly one train-solution action per press and nothing on render`
- `forward commits the live preview (SEED-197)` -> `forward commits the live preview`
- `Phase 222: first-session intro stepper (D-05/D-12/D-22)` -> `first-session intro stepper`
- `Phase 222: drop-before-guess nudge (D-08)` -> `drop-before-guess nudge`
- `Phase 222: verdict bubble (D-03/D-10/D-15/D-16/D-23)` -> `verdict bubble`
- `D-08: the strip is collapsed again on the next puzzle\'s reveal, even after the user opened it` -> `the strip is collapsed again on the next puzzle\'s reveal, even after the user opened it`
- `Phase 240: split reveal tour` -> `split reveal tour`
- `latch (D-07): a stage write that lands mid-reveal never switches the part` -> `latch: a stage write that lands mid-reveal never switches the part`
- `a reveal restored after the Analyze round trip starts no part and stamps nothing (D-07)` -> `a reveal restored after the Analyze round trip starts no part and stamps nothing`
- `a part left on its last step (unmount) stamps nothing and replays from 1 / n on the next reveal (D-08)` -> `a part left on its last step (unmount) stamps nothing and replays from 1 / n on the next reveal`
- `the Analyze button from a middle step of a part stamps nothing (D-08)` -> `the Analyze button from a middle step of a part stamps nothing`
- `TrainSolveScreen — per-puzzle telemetry (Phase 233)` -> `TrainSolveScreen — per-puzzle telemetry`
- `telemetry (D-13): a hand-played known-line move counts as a board move, not a fork` -> `telemetry: a hand-played known-line move counts as a board move, not a fork`
- `telemetry (D-12): re-tapping the default You chip and never opening the strip sends zero chips and a closed strip` -> `telemetry: re-tapping the default You chip and never opening the strip sends zero chips and a closed strip`
- `TrainSolveScreen — restored reveal tree (Phase 237 plan 09)` -> `TrainSolveScreen — restored reveal tree`
- `TrainSolveScreen — instant server-graded path (Phase 236)` -> `TrainSolveScreen — instant server-graded path`
- `instant path: a played server-graded move POSTs at once with the payload tier, and its late reading rides the Next flush (Phase 236 D-09/D-10/D-12/D-16)` -> `instant path: a played server-graded move POSTs at once with the payload tier, and its late reading rides the Next flush`
- `instant path: playing the key keeps the graded path and its POST record (D-05/D-13)` -> `instant path: playing the key keeps the graded path and its POST record`
- `instant path: the Best chip shows the key line at once and the Move chip loads, then fills (Phase 236 D-14)` -> `instant path: the Best chip shows the key line at once and the Move chip loads, then fills`
- `D-16: the instant POST round trip shows a copy-less spinner, never "Checking your move…"` -> `the instant POST round trip shows a copy-less spinner, never "Checking your move…"`
- `D-16: before the phone grade lands the board follows the server pair and the key (never an Also fine arrow); the eval bar waits for the grade` -> `before the phone grade lands the board follows the server pair and the key (never an Also fine arrow); the eval bar waits for the grade`
- `D-09: every verdict surface renders the SolveResponse, never the payload tier` -> `every verdict surface renders the SolveResponse, never the payload tier`
- `Pitfall 1: the reveal game-move search queues behind the background grade, never stopping it` -> `the reveal game-move search queues behind the background grade, never stopping it`
- `D-15: a rejecting background grade leaves the verdict open, no grading error and no phone_grade` -> `a rejecting background grade leaves the verdict open, no grading error and no phone_grade`
- `WR-01/D-15: a grading Worker error after the instant verdict keeps the verdict bubble and its Next button` -> `a grading Worker error after the instant verdict keeps the verdict bubble and its Next button`
- `WR-02: Analyze pressed before the background grade lands still caches the solved reveal from the server pair` -> `Analyze pressed before the background grade lands still caches the solved reveal from the server pair`
- `WR-02: without a server pair on the verdict there is nothing real to cache, so Analyze caches no reveal` -> `without a server pair on the verdict there is nothing real to cache, so Analyze caches no reveal`
- `Pitfall 4: a background grade settling after the user moved on never lands on the next puzzle` -> `a background grade settling after the user moved on never lands on the next puzzle`

**TrainStartScreen.test.tsx**

- `TrainStartScreen — refetch after a schedule save (SEED-181 review)` -> `TrainStartScreen — refetch after a schedule save`
- `empty: session_id null and puzzle_count 0 renders the plain D-04 placeholder, no crash, no action button` -> `empty: session_id null and puzzle_count 0 renders the plain placeholder, no crash, no action button`
- `222 UAT round 6: Tank the Ox speaks the greeting in a bot bubble, and the old "Train" heading is gone` -> `Tank the Ox speaks the greeting in a bot bubble, and the old "Train" heading is gone`
- `D-13: the schedule settings block renders after the Start CTA in the fresh state` -> `the schedule settings block renders after the Start CTA in the fresh state`
- `quick 261004-dta: the schedule card sits above the leaderboard (fresh and completed)` -> `the schedule card sits above the leaderboard (fresh and completed)`
- `quick 261004-dta: the host bubble is phone-hidden once the intro is seen, but Tank\'s intro stays` -> `the host bubble is phone-hidden once the intro is seen, but Tank\'s intro stays`
- `Phase 240 UAT: the sign-up and import asks keep the host bubble on phones` -> `the sign-up and import asks keep the host bubble on phones`
- `191-06 UAT bug fix: a persisted schedule-settings edit calls onSettingsSaved, so the stale mount-time session gets re-fetched` -> `a persisted schedule-settings edit calls onSettingsSaved, so the stale mount-time session gets re-fetched`
- `TrainStartScreen — 224 UAT round 2: no warm-up info card, guest sign-up ask in the host bubble` -> `TrainStartScreen — no warm-up info card, guest sign-up ask in the host bubble`
- `Phase 240 UAT: guest who has not completed a session (first visit, or tour done mid-session): no sign-up sentence or buttons` -> `guest who has not completed a session (first visit, or tour done mid-session): no sign-up sentence or buttons`
- `Phase 240 D-22: no reminder sentence until the whole three-part tour is done (stage 2 is not enough)` -> `no reminder sentence until the whole three-part tour is done (stage 2 is not enough)`
- `TrainStartScreen — quick 260926-8p5: import ask for a registered zero-game account` -> `TrainStartScreen — import ask for a registered zero-game account`
- `TrainStartScreen — PROG-05/D-16 tailored cold/exhausted empty states (191-06)` -> `TrainStartScreen — tailored cold/exhausted empty states`
- `TrainStartScreen — OFFER-05/D-16 re-surface banner (additive, not a seventh state)` -> `TrainStartScreen — re-surface banner (additive, not a seventh state)`
- `shouldResurface true but the capability probe unresolved: still nothing (WR-01)` -> `shouldResurface true but the capability probe unresolved: still nothing`
- `TrainStartScreen — Phase 230 D-08: weekly leaderboard card position` -> `TrainStartScreen — weekly leaderboard card position`
- `TrainStartScreen — Phase 231 D-10: medal dialog host mount` -> `TrainStartScreen — medal dialog host mount`
- `TrainStartScreen: Phase 234 milestone feedback ask` -> `TrainStartScreen: milestone feedback ask`
- `D-04: intro done + active ask renders Hilda (large) instead of the host, visible on phones` -> `intro done + active ask renders Hilda (large) instead of the host, visible on phones`
- `SEED-191 #10: the ask outranks the reminder-install ask` -> `the ask outranks the reminder-install ask`
- `D-04: while the intro is not completed Tank still hosts and no ask renders` -> `while the intro is not completed Tank still hosts and no ask renders`

**TrainStatsCard.test.tsx**

- `jargon popovers (193 UAT round 3)` -> `jargon popovers`

**trainBubbleState.test.ts**

- `grading state carries recheck: true while the disagreement re-check runs (D-12)` -> `grading state carries recheck: true while the disagreement re-check runs`
- `submitting state while the instant solve POST is in flight (D-16)` -> `submitting state while the instant solve POST is in flight`

**MedalClaimDialog.test.tsx**

- `MedalClaimDialog Claim path (D-12, D-13)` -> `MedalClaimDialog Claim path`
- `MedalClaimDialog dismiss path (D-13)` -> `MedalClaimDialog dismiss path`
- `MedalClaimDialog medal pop (D-11)` -> `MedalClaimDialog medal pop`

**TrainMedalDialogHost.test.tsx**

- `an impersonating admin triggers no GET and shows nothing (T-231-16)` -> `an impersonating admin triggers no GET and shows nothing`


## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `npm --prefix frontend ci` and `uv sync --group maia-inference` (lockfile installs only, no new packages). No tracked files changed.

**2. [Plan note] Broader provenance sweep than the scan**
- The scan regex missed `190.1 UAT round N`, `UAT item 5`, `Sketch 004`, `quick 260814-b`, `Plan 04 UAT round N`, `round 7`, and dated "2026-08-03 fix" labels (about 30 lines). They were removed with the tags, as the toolkit notes prescribe; comment/title text only.

**3. [Plan note] Task 2 commit touches two Task 1 files**
- The broad grep ran after Task 1 was committed, so its fixes in TrainReveal.test.tsx and TrainSolveScreen.test.tsx (and the bare-header deletions in TrainVerdictStrip/TrainRevealActionBar) landed in the Task 2 commit.

**Total deviations:** 1 environment prep, 2 plan notes. No test body, assertion, testid, Umami name, mock factory or expected-copy string changed.

## Known Stubs

None.

## Threat Flags

None. Comment and title text only; T-241-65 mitigated by `cleanup.py diff` (token stream identical apart from normalized titles) and equal vitest counts.

## Self-Check: PASSED

Both task commits (`92f5d80fc`, `734e62199`) are ancestors of HEAD; all 25 changed files exist; scan and diff gates re-run clean on the final tree.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
