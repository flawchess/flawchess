---
phase: 241-codebase-cleanup
plan: 49
subsystem: frontend-tests
tags: [cleanup, comments, test-titles, vitest, d-14]

requires:
  - phase: 241-04
    provides: "cleanup.py TypeScript scan/diff support and the test-title normalization"
provides:
  - "66 frontend/src/lib test files (of 92 in scope) free of planning tags in comments and describe/it/test titles"
affects: [241-60]

actuals:
  tokens: 40000
  tasks: 2
  commits: 2
plan_head_before: 0b0eb7b64d7bcceb612c832d2acc33484cbb41b5
plan_head_after: 90f7ffcd0552ec76daa721bf4d0e3ccf598f7f58

key-files:
  created: []
  modified:
    - "frontend/src/lib/__tests__/*.test.ts (54 files)"
    - "frontend/src/lib/*.test.ts (10 files)"
    - "frontend/src/lib/personas/__tests__/*.test.ts (2 files)"

key-decisions:
  - "Tags embedded in it.each case tables ('name:' strings) and in concatenated multi-line it() titles are string tokens, not titles, to the token diff, so they are left as they are (see Known Residual below)"
  - "Sentry issue ids (FLAWCHESS-64/91/92) in comments are external-system pointers, not .planning tags, and stay"

requirements-completed: [D-01, D-03, D-11, D-12, D-13, D-14, D-15]

duration: 45min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 49: Frontend library tests comment and title cleanup Summary

**Planning tags (Phase/Plan/D-NN/WR-NN/CR-NN/quick IDs/UAT/Pitfall) are gone from comments and describe/it titles of the library tests; 66 of the 92 scope files changed, 0 matches remain, and the token diff shows only normalized title changes.**

## Accomplishments

- Task 1 (27 files matched by the Train/bot/push/persona filter, 24 changed) and Task 2 (65 files, 42 changed) both finished with `scan --gate` at 0 matches.
- `cleanup.py diff --scope scopes/241-49.txt`: exit 0, "92 files selected, 66 changed", no residue.
- Decision references were replaced by what they decided, not just dropped, where the sentence needed it (e.g. "D-05 forbids renaming or reusing them" became "renaming or reusing them is forbidden"; the `trainRevealCache` pre-211 comments were rewritten as present-tense rules about older cache entries).
- Planning-document pointers (`NNN-PLAN.md`, `RESEARCH.md`, `FINDINGS.md`, `NNN-REVIEW.md`) were removed from test header comments.

## Task Commits

1. **Task 1:** `4fef9671a` `chore(comments): frontend lib tests (Train, bot, push, personas)`
2. **Task 2:** `90f7ffcd0` `chore(comments): frontend lib tests (rest)`

## Verification (final tree)

| Check | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-49.txt` | exit 0, 92 files, 0 matches |
| `cleanup.py diff --scope scopes/241-49.txt` | exit 0, 66 changed, no residue |
| `cleanup.py scan --gate` / `diff` on the Task 1 file subset | exit 0 each |
| vitest `src/lib` before the edits | 126 files, 2413 tests passed |
| vitest `src/lib` after Task 1 | 126 files, 2413 tests passed |
| vitest `src/lib` after Task 2 | 126 files, 2413 tests passed (count unchanged) |
| `npm --prefix frontend run lint` | clean |
| `source_scan_tests.sh --fe` | 131 passed |
| source-scan python half, run serially (no `-n 4`) | 95 passed + 5 passed |

Note: I used the whole `src/lib` directory as the single before/after vitest measurement (it contains every scope file, so a changed test count anywhere would show). The Task 1 grep filter (`train*` prefix) matches 27 files rather than the plan's 26 because it also catches `trainClockContext.test.ts` (listed in files_modified but in neither task's file list); that file has no tags and is unchanged. Similarly the Task 2 remainder is 65 files, not 46, because files_modified lists 19 more (`clockFormat`, `firstTouch`, `arrowColor`, `zobrist`, ...) that the task text omits; they were scanned and needed no change.

## Codemod vs hand edits

| | Codemod lines changed | Codemod flagged for hand edit | `apply-edits` spans |
|---|---|---|---|
| Task 1 (27 files) | 26 in 16 files | 64 | 186 spans in 6 batches (a-f), 11 of them reverted by one more batch (see Known Residual), plus 1 direct edit |
| Task 2 (65 files) | 27 in 20 files | 52 | 130 spans in 2 batches (h, i), plus 1 direct edit |

Total 53 codemod line rewrites and about 316 batch spans. Every codemod rewrite was reviewed in `git diff -U0`; codemod left partial tags in a few headers (`Phase 203 Plan 02.`, `Task 2:`), all fixed by hand. The `^\s*(#|//|\*)\s*[:;,]\s` check on the scope found nothing.

## Rewritten titles (old -> new)

Titles and parenthetical tags removed from describe/it/test strings (path relative to `frontend/src/lib/`). Entries whose only change is a dropped tag are listed in full so the title text is auditable. Comment-only rewrites are not repeated here.

| File | Old | New |
|---|---|---|
| __tests__/botDrawGate.test.ts | contempt (D-09, Phase 182) | contempt |
| __tests__/botDrawGate.test.ts | with contempt omitted, is identical to the pre-182 (no-contempt) behavior | with contempt omitted, is identical to the no-contempt behavior |
| __tests__/botDrawGate.test.ts | wouldBotResign (D-07/D-08, Phase 182) | wouldBotResign |
| __tests__/botDrawGate.test.ts | wouldBotOfferDraw (D-07, Phase 183, Plan 02) | wouldBotOfferDraw |
| __tests__/botDrawGate.test.ts | contempt shifts the offer target (mirrors wouldBotAcceptDraw D-09) | contempt shifts the offer target (mirrors wouldBotAcceptDraw) |
| __tests__/botGameCopy.test.ts | rosterHost / landingHost — shared daily rotation (223-02) | rosterHost / landingHost — shared daily rotation |
| __tests__/botGameEnd.test.ts | shows "You resigned" for a user resignation (bot never resigns, D-03) | shows "You resigned" for a user resignation (bot never resigns) |
| __tests__/botGameEnd.test.ts | shows "You won — the bot resigned" only in the (D-03-unreachable) opposite case | shows "You won — the bot resigned" only in the (unreachable) opposite case |
| __tests__/botGameEnd.test.ts | resultCopy — persona-named bot-actor copy (Phase 183, D-06) | resultCopy — persona-named bot-actor copy |
| __tests__/botGameEnd.test.ts | substitutes the persona name into the (D-03-unreachable) bot-resigned win copy | substitutes the persona name into the (unreachable) bot-resigned win copy |
| __tests__/botGameSnapshot.test.ts | round-trip (D-08 acceptance gate) | round-trip |
| __tests__/botGameSnapshot.test.ts | a stored value with a mismatched version reads back as null (silent hard drop, D-06) | a stored value with a mismatched version reads back as null (silent hard drop) |
| __tests__/botGameSnapshot.test.ts | personaId (Phase 183, PERS-02/PERS-04) | personaId |
| __tests__/botLineTrigger.test.ts | resolveBotLine — full precedence chain (BOTVOICE-02/03) | resolveBotLine — full precedence chain |
| __tests__/botLineTrigger.test.ts | resolveBotLine — swing arm edge cases (BOTVOICE-03, D-01/D-04) | resolveBotLine — swing arm edge cases |
| __tests__/botLineTrigger.test.ts | never paces the settle of a live regret latch (223-REVIEW CR-01) | never paces the settle of a live regret latch |
| __tests__/botPendingStore.test.ts | cap (T-170-03 bounded FIFO queue) | cap (bounded FIFO queue) |
| __tests__/botPendingStore.test.ts | store-once (SC2 structural invariant, D-12 separate key) | store-once (structural invariant, separate key) |
| __tests__/botPendingStore.test.ts | D-12 rationale, made concrete: a pending entry survives starting a brand-new in-progress game for the same owner | separate keys, made concrete: a pending entry survives starting a brand-new in-progress game for the same owner |
| __tests__/botSetupSettings.test.ts | key distinctness (T-171-04-03) | key distinctness |
| __tests__/botTimeControlPresets.test.ts | has exactly 9 entries (D-14 order: blitz, rapid, classical) — no bullet | has exactly 9 entries (order: blitz, rapid, classical) — no bullet |
| __tests__/botTimeControlPresets.test.ts | groups presets into blitz/rapid/classical buckets matching D-14 | groups presets into blitz/rapid/classical buckets |
| __tests__/installCooldown.test.ts | locks the D-04 values | locks the cooldown and attempt-cap values |
| __tests__/push.test.ts | ensureDeviceSubscribed — never rejects (CR-01) and reports (WR-01) | ensureDeviceSubscribed — never rejects and reports |
| __tests__/push.test.ts | does not report a dismissed prompt — a decline is not an error (PERM-02) | does not report a dismissed prompt — a decline is not an error |
| __tests__/push.test.ts | does not report a denial — a denial is not an error (D-11) | does not report a denial — a denial is not an error |
| __tests__/push.test.ts | prompt dismissed: status is "dismissed", not "denied", and no subscribe happens (PERM-02) | prompt dismissed: status is "dismissed", not "denied", and no subscribe happens |
| __tests__/push.test.ts | D4: key-mismatch repair vs key-match reuse | key-mismatch repair vs key-match reuse |
| __tests__/push.test.ts | PERM-02: no decline state is ever persisted | no decline state is ever persisted |
| __tests__/push.test.ts | a rejecting pushApi.subscribe: resolves false, reports once, and never leaks the endpoint (T-204-02) | a rejecting pushApi.subscribe: resolves false, reports once, and never leaks the endpoint |
| __tests__/trainArrows.test.ts | a sharp puzzle with four good moves returns exactly one arrow — the BLUE best move — with a best badge on its target square (190.1 UAT); alsoFineMoves is empty (D-03) | a sharp puzzle with four good moves returns exactly one arrow — the BLUE best move — with a best badge on its target square; alsoFineMoves is empty |
| __tests__/trainArrows.test.ts | a soft puzzle draws exactly ONE alternative when BOTH served entries survive the filter (client best and played move match neither) — the soft cap of 1 truncates to the FIRST entry, which best-first server order makes the STRONGEST new fine move (D-01 amendment) | a soft puzzle draws exactly ONE alternative when BOTH served entries survive the filter (client best and played move match neither) — the soft cap of 1 truncates to the FIRST entry, which best-first server order makes the STRONGEST new fine move |
| __tests__/trainArrows.test.ts | the operator's Task 3 round-2 scenario: the served su coincides with the client's best AND played move, so the deep-best entry is what keeps the \"Also fine\" row non-empty (D-01 amendment) | the served su coincides with the client's best AND played move, so the deep-best entry is what keeps the \"Also fine\" row non-empty |
| __tests__/trainArrows.test.ts | an inaccuracy-level fine move renders the SAME dark-green arrow and good badge as a clean alternative — the D-05 collapse applies to alternatives too | an inaccuracy-level fine move renders the SAME dark-green arrow and good badge as a clean alternative — the collapse applies to alternatives too |
| __tests__/trainArrows.test.ts | a herring puzzle draws up to FOUR alternatives from a five-entry vetted list (Phase 211 D-01: the ladder minus its top entry) — its own budget, no longer the soft cap | a herring puzzle draws up to FOUR alternatives from a five-entry vetted list (the ladder minus its top entry) — its own budget, no longer the soft cap |
| __tests__/trainArrows.test.ts | a played fine alternative does not consume an alternative slot — the remaining alternatives all still draw and all list (UAT round 4) | a played fine alternative does not consume an alternative slot — the remaining alternatives all still draw and all list |
| __tests__/trainArrows.test.ts | alsoFineMoves.length always equals the number of arrows whose layerKey starts with 'good-' (D-03 1:1 invariant) | alsoFineMoves.length always equals the number of arrows whose layerKey starts with 'good-' (1:1 invariant) |
| __tests__/trainArrows.test.ts | badges dedupe by target square with the played move winning (played and best land on the same square from different origins); the played inaccuracy keeps its own severity badge (quick 261008-opg) | badges dedupe by target square with the played move winning (played and best land on the same square from different origins); the played inaccuracy keeps its own severity badge |
| __tests__/trainArrows.test.ts | a played inaccuracy draws the inaccuracy-yellow arrow, not the good green (quick 261008-opg) | a played inaccuracy draws the inaccuracy-yellow arrow, not the good green |
| __tests__/trainArrows.test.ts | vettedMoveForSquares (Phase 211 D-06) | vettedMoveForSquares |
| __tests__/trainArrows.test.ts | buildTrainFreePlayOverlay (Phase 200 UAT round 5, Phase 228 D-13/D-15, quick 261012-a6m) | buildTrainFreePlayOverlay |
| __tests__/trainArrows.test.ts | buildTrainStepOverlay (quick 261009-por, quick 261012-a6m D-04/D-08) | buildTrainStepOverlay |
| __tests__/trainArrows.test.ts | maps best to the engine-blue highlight and inaccuracy to the shared yellow, not good (quick 261008-opg) | maps best to the engine-blue highlight and inaccuracy to the shared yellow, not good |
| __tests__/trainArrows.test.ts | buildChipFocusOverlay (Phase 237) | buildChipFocusOverlay |
| __tests__/trainArrows.test.ts | does not light another move’s badge when two candidate moves share a target square (WR-02) | does not light another move’s badge when two candidate moves share a target square |
| __tests__/trainArrows.test.ts | passes alsoFineMoves and markerOwners through unchanged (Phase 200 LEGEND-04: the sidebar row is never emptied by the board focus) | passes alsoFineMoves and markerOwners through unchanged (the sidebar row is never emptied by the board focus) |
| __tests__/trainArrows.test.ts | liveAlternatives (quick 261010-e5l) | liveAlternatives |
| __tests__/trainArrows.test.ts | chipArrowColor (Phase 237 UAT) | chipArrowColor |
| __tests__/trainArrows.test.ts | trainRootMultiPvFloor (quick 261010-e5l) | trainRootMultiPvFloor |
| __tests__/trainArrows.test.ts | buildTrainLiveAlternatives (quick 261010-e5l) | buildTrainLiveAlternatives |
| __tests__/trainLeaderboard.test.ts | firstUnrankedRowIndex (quick 261004-8rt) | firstUnrankedRowIndex |
| __tests__/trainLeaderboard.test.ts | parseLeaderboardTab (D-09, T-230-10) | parseLeaderboardTab |
| __tests__/trainLeaderboard.test.ts | accuracy: a specific not-on-this-board line when only the points viewer exists (D-19) | accuracy: a specific not-on-this-board line when only the points viewer exists |
| __tests__/trainLeaderboard.test.ts | copy never frames the board as ability (D-10) | copy never frames the board as ability |
| __tests__/trainLeaderboard.test.ts | remainingSeconds (D-02: server remainder minus time since fetch) | remainingSeconds (server remainder minus time since fetch) |
| __tests__/trainLeaderboard.test.ts | uses the D-13 and D-14 wording | uses the hidden-row and guest-row wording |
| __tests__/trainLeaderboard.test.ts | rankLineCopy, public viewers (D-11, D-12) | rankLineCopy, public viewers |
| __tests__/trainLeaderboard.test.ts | rankLineCopy, guest, tentative and worse-rank variants (D-11, D-17, D-18) | rankLineCopy, guest, tentative and worse-rank variants |
| __tests__/trainLeaderboard.test.ts | a guest gets the hypothetical line with no delta (D-17) | a guest gets the hypothetical line with no delta |
| __tests__/trainLeaderboard.test.ts | a worse Accuracy rank after the session shows the plain rank and never "down" (D-18) | a worse Accuracy rank after the session shows the plain rank and never "down" |
| __tests__/trainLeaderboard.test.ts | scoreRankLines, not-entered and hidden rules (D-13, D-19) | scoreRankLines, not-entered and hidden rules |
| __tests__/trainLeaderboard.test.ts | a Points viewer with no Accuracy viewer gets the not-entered line (D-19) | a Points viewer with no Accuracy viewer gets the not-entered line |
| __tests__/trainPhoneGrade.test.ts | has exactly the six wire keys and no device or engine field (D-07) | has exactly the six wire keys and no device or engine field |
| __tests__/trainPhoneGrade.test.ts | instantServerTier (Phase 236 D-09/D-10) | instantServerTier |
| __tests__/trainPhoneGrade.test.ts | is null when the played move is the key, even while the key is listed (D-13/D-05) | is null when the played move is the key, even while the key is listed |
| __tests__/trainRecheck.test.ts | shouldRecheck (D-10, D-19) | shouldRecheck |
| __tests__/trainRecheck.test.ts | shouldRecheck: inaccuracy rescue (quick 261008-ob1) | shouldRecheck: inaccuracy rescue |
| __tests__/trainRecheck.test.ts | shouldRecheck: server-graded moves are never re-checked (Phase 236 D-11) | shouldRecheck: server-graded moves are never re-checked |
| __tests__/trainRecheck.test.ts | recheckOutcome (D-13) | recheckOutcome |
| __tests__/trainRecheck.test.ts | buildRecheckPayload (D-17) | buildRecheckPayload |
| __tests__/trainRevealCache.test.ts | Phase 233: round-trips reviewTelemetry, and an entry without it still restores | round-trips reviewTelemetry, and an entry without it still restores |
| __tests__/trainRevealCache.test.ts | Phase 237: revealTree (T-237-16) | revealTree |
| __tests__/trainRevealCache.test.ts | round-trips committedPaths and tolerates their absence (WR-02) | round-trips committedPaths and tolerates their absence |
| __tests__/trainRevealCache.test.ts | SEED-119: rejects a pre-tiering cache entry whose verdict lacks move_quality | rejects a pre-tiering cache entry whose verdict lacks move_quality |
| __tests__/trainRevealCache.test.ts | D-10: a pre-211 cache entry whose gradeResult still carries the deleted rank-lines key restores, and the free-play seed\'s served-list read degrades to empty | an older cache entry whose gradeResult still carries the deleted rank-lines key restores, and the free-play seed\'s served-list read degrades to empty |
| __tests__/trainRevealCache.test.ts | RESEARCH Pitfall 1: a pre-211 cache entry (stale fine-move key on gradeResult, no vetted-move key on the verdict) is ACCEPTED, and the vetted-move read degrades to an empty list | an older cache entry (stale fine-move key on gradeResult, no vetted-move key on the verdict) is ACCEPTED, and the vetted-move read degrades to an empty list |
| __tests__/trainRevealLines.test.ts | game == best merges generically under the best key (D-02 rule, not designed around) | game == best merges generically under the best key (a general rule, not designed around) |
| __tests__/trainRevealLines.test.ts | Phase 236 instant path | instant path |
| __tests__/trainRevealLines.test.ts | reads bestMoveUci so an empty stand-in bestLine still yields the key (WR-01) | reads bestMoveUci so an empty stand-in bestLine still yields the key |
| __tests__/trainRevealLines.test.ts | no active chip (D-04): an empty main line and only the root-fork subtrees | no active chip: an empty main line and only the root-fork subtrees |
| __tests__/trainRevealLines.test.ts | persists the UCI path of each committed node, omitting the field when none (WR-02) | persists the UCI path of each committed node, omitting the field when none |
| __tests__/trainRevealLines.test.ts | round trip: grafting the paths in order rebuilds the same main line (Pitfall 1) | round trip: grafting the paths in order rebuilds the same main line |
| __tests__/trainRevealPreview.test.ts | resolvePreview minimum length (SEED-197 UAT) | resolvePreview minimum length |
| __tests__/trainScore.test.ts | SEED-119 scenario checks | move-tier scenario checks |
| personas/__tests__/personaRegistry.test.ts | every persona.botElo is a member of MAIA_ELO_LADDER (Phase 184 D-01: retargeted, no longer === rung) | every persona.botElo is a member of MAIA_ELO_LADDER (retargeted, no longer === rung) |
| personas/__tests__/personaRegistry.test.ts | no persona ships an avatarSrc yet (D-16 — placeholders only this phase) | no persona ships an avatarSrc yet (placeholders only) |
| personas/__tests__/personaRegistry.test.ts | temperament (Phase 222 D-01) | temperament |
| personas/__tests__/personaRegistry.test.ts | wall-1800 (Hilda, the fixed D-05 teacher) is 'smart' | wall-1800 (Hilda, the fixed teacher) is 'smart' |
| personas/__tests__/personaRegistry.test.ts | grinder-1600 (Tank, the D-05 intro-step-1 host) is 'stern' | grinder-1600 (Tank, the intro-step-1 host) is 'stern' |
| personas/__tests__/personaRegistry.test.ts | CAL-05 calibrated label honesty (Phase 184) | calibrated label honesty |
| personas/__tests__/personaRegistry.test.ts | every calibratedLabel is a tilde-prefixed integer, rounded to the nearest 50 (D-03) | every calibratedLabel is a tilde-prefixed integer, rounded to the nearest 50 |
| personas/__tests__/personaRegistry.test.ts | no calibratedLabel exceeds the ~1800 global ceiling (D-07) | no calibratedLabel exceeds the ~1800 global ceiling |
| personas/__tests__/personaRegistry.test.ts | every bottom-rung (800) persona carries a defined, non-blank label — the floor is acknowledged, never dropped (D-06) | every bottom-rung (800) persona carries a defined, non-blank label — the floor is acknowledged, never dropped |
| personas/__tests__/personaRegistry.test.ts | calibratedLabel is non-decreasing by rung within each style column (D-04 monotonicity spot-check) | calibratedLabel is non-decreasing by rung within each style column (monotonicity spot-check) |
| __tests__/trainBotCopy.test.ts | pickPuzzleHost (Phase 237 UAT) | pickPuzzleHost |
| __tests__/trainBotCopy.test.ts | promptCopy states the side to move and asks the D-09 vocabulary question | promptCopy states the side to move and asks the vocabulary question |
| __tests__/trainBotCopy.test.ts | GRADING_COPY is the D-22 checking-move line | GRADING_COPY is the checking-move line |
| __tests__/trainBotCopy.test.ts | introCopy / introSteps (Phase 240 D-01, D-02: two bubbles) | introCopy / introSteps (two bubbles) |
| __tests__/trainBotCopy.test.ts | verdictClauseParts / verdictCopy clause / verdictStripLine (Phase 237 D-05/D-06) | verdictClauseParts / verdictCopy clause / verdictStripLine |
| __tests__/trainBotCopy.test.ts | returnPhrase (D-15/D-16 truth table) | returnPhrase (truth table) |
| __tests__/trainBotCopy.test.ts | reveal tour parts (Phase 240) | reveal tour parts |
| __tests__/trainBotCopy.test.ts | the Analyze bubble is the D-19 sheet per analyze target and spotlights the Analyze button | the Analyze bubble is the per-analyze-target sheet and spotlights the Analyze button |
| __tests__/trainBotCopy.test.ts | scoreBubbleCopy (Phase 240 D-16..D-19) | scoreBubbleCopy |
| __tests__/trainBotCopy.test.ts | scoreBubbleCopy, D-03/S-3 games-less warm-up audience branch (Phase 224) | scoreBubbleCopy, games-less warm-up audience branch |
| __tests__/trainBotCopy.test.ts | quick 260926-8p5: a registered zero-game account gets the opener only, no reminder or sign-up line | a registered zero-game account gets the opener only, no reminder or sign-up line |
| __tests__/trainBotCopy.test.ts | quick 261015-pjr: a guest with games is never told its games will be analyzed | a guest with games is never told its games will be analyzed |
| __tests__/botGameSnapshot.test.ts | a pre-183 snapshot object with no personaId key still validates at version 1 and reads back with settings.personaId === undefined | a legacy snapshot object with no personaId key still validates at version 1 and reads back with settings.personaId === undefined |
| __tests__/botGameEnd.test.ts | returns the exact pre-183 generic strings when personaName is omitted/null/undefined (Custom game) | returns the exact generic strings when personaName is omitted/null/undefined (Custom game) |
| __tests__/trainArrows.test.ts | a sharp puzzle still draws ZERO alternatives even when the user played a fine one — the deep answer key outranks the live search (UAT round 4) | a sharp puzzle still draws ZERO alternatives even when the user played a fine one — the deep answer key outranks the live search |
| __tests__/trainArrows.test.ts | buildTrainStepArrows (190.1 UAT stepping) | buildTrainStepArrows |
| __tests__/trainArrows.test.ts | buildTrainStepMarkers (190.1 UAT round 4) | buildTrainStepMarkers |
| __tests__/trainArrows.test.ts | TRAIN_STEP_HIGHLIGHT (190.1 UAT stepping) | TRAIN_STEP_HIGHLIGHT |
| __tests__/trainBotCopy.test.ts | movePromptCopy echoes the committed call in the reveal card vocabulary (phase 222 UAT) | movePromptCopy echoes the committed call in the reveal card vocabulary |
| __tests__/trainBotCopy.test.ts | UAT 240: a guest warm-up opening skips the warm-up note; a zero-game guest gets no clause | a guest warm-up opening skips the warm-up note; a zero-game guest gets no clause |
| __tests__/trainBotCopy.test.ts | UAT 240: a zero-game guest opener never repeats the sign-up ask of line 2 | a zero-game guest opener never repeats the sign-up ask of line 2 |
| __tests__/analytics.test.ts | umamiBeforeSend after an automatic reload (Quick 261004-rmc) | umamiBeforeSend after an automatic reload |
| __tests__/analytics.test.ts | 'trackFeature sends the %s tab-switch target with page train (Phase 230)', | 'trackFeature sends the %s tab-switch target with page train', |
| __tests__/chessClock.test.ts | applyIncrementMs (PLAY-03 Fischer increment) | applyIncrementMs (Fischer increment) |
| __tests__/chessClock.test.ts | computeElapsedMs (PLAY-04 wall-clock delta) | computeElapsedMs (wall-clock delta) |
| __tests__/chessClock.test.ts | visibility pause (PLAY-04) | visibility pause |
| __tests__/chessClock.test.ts | computeThinkDeadlineMs (D-16 per-move think deadline) | computeThinkDeadlineMs (per-move think deadline) |
| __tests__/chessClock.test.ts | at a full 5+3 clock, comfortably exceeds the 168.5-04 measured ~5.4s median search | at a full 5+3 clock, comfortably exceeds the measured ~5.4s median search |
| __tests__/chessClock.test.ts | computeRevealDelayMs (D-03 reveal-delay floor) | computeRevealDelayMs (reveal-delay floor) |
| __tests__/chessClock.test.ts | computeChargeableElapsedMs (D-20 in-progress pause) | computeChargeableElapsedMs (in-progress pause) |
| __tests__/chessClock.test.ts | hasFlaggedOnDebit (D-15 honest flag) | hasFlaggedOnDebit (honest flag) |
| __tests__/chessClock.test.ts | fold (Phase 170 D-01/D-02 leave/resume clock-fold asymmetry) | fold (leave/resume clock-fold asymmetry) |
| __tests__/chessClock.test.ts | D-01: folds the elapsed think time into the active base when the user is on move (white) | folds the elapsed think time into the active base when the user is on move (white) |
| __tests__/chessClock.test.ts | D-01: folds only the active base when the user is on move as black | folds only the active base when the user is on move as black |
| __tests__/chessClock.test.ts | D-02: does NOT fold on the bot's turn — the bot's interrupted think is refunded, base written as of its last commit | does NOT fold on the bot's turn — the bot's interrupted think is refunded, base written as of its last commit |
| __tests__/chessClock.test.ts | isLowTime / formatClockLabel (D-07 low-time tenths display) | isLowTime / formatClockLabel (low-time tenths display) |
| __tests__/endgameEntryEvalZones.test.ts | centers on 0 pawns (D-07 H0) | centers on 0 pawns |
| __tests__/engineArrowGrades.test.ts | secondaryArrowAlpha (D-08) | secondaryArrowAlpha |
| __tests__/engineArrowGrades.test.ts | mergeEngineBadges (D-03) | mergeEngineBadges |
| __tests__/engineSettings.test.ts | useEngineToggles / setEngineToggle (quick 261004-nxn) | useEngineToggles / setEngineToggle |
| __tests__/formatFlawEval.test.ts | mateAtPly (Phase 135 UAT — mate count tracks the selected ply) | mateAtPly (mate count tracks the selected ply) |
| __tests__/gapBar.test.ts | gapPosition (D-00a) | gapPosition |
| __tests__/gapBar.test.ts | scales an asymmetric band by its wider side (defensive: bands are symmetric since D-15) | scales an asymmetric band by its wider side (defensive: bands are symmetric) |
| __tests__/gapBar.test.ts | gapVerdict (D-00b) | gapVerdict |
| __tests__/gapBar.test.ts | effectiveVerdict (D-11, D-14) | effectiveVerdict |
| __tests__/gapBar.test.ts | judges a zoneless cell on significance alone (D-16) | judges a zoneless cell on significance alone |
| __tests__/gapBar.test.ts | isChanceGap (D-14) | isChanceGap |
| __tests__/gemMove.test.ts | D-01: a lost-position best-try still qualifies (no still-losing exclusion) | a lost-position best-try still qualifies (no still-losing exclusion) |
| __tests__/gemMove.test.ts | D-02: qualifying inputs classify true regardless of ply — classifyGem takes no ply argument, so no opening guard can ever gate it | qualifying inputs classify true regardless of ply — classifyGem takes no ply argument, so no opening guard can ever gate it |
| __tests__/gemMove.test.ts | D-07 (Phase 172): GEM_MAIA_MAX_PROB is exactly 0.2 | GEM_MAIA_MAX_PROB is exactly 0.2 |
| __tests__/gemMove.test.ts | D-07 (Phase 172): a maiaProbability of 0.15 with a passing C2 now classifies as a gem (would have failed C1 at the old 0.1 threshold) | a maiaProbability of 0.15 with a passing C2 now classifies as a gem (would have failed C1 at the old 0.1 threshold) |
| __tests__/gemMove.test.ts | D-01: qualifying inputs in the (0.20, 0.50] band with a passing C2 margin classify as great | qualifying inputs in the (0.20, 0.50] band with a passing C2 margin classify as great |
| __tests__/gemMove.test.ts | D-04: classifies identically regardless of mover — symmetric best/second-best for white and black | classifies identically regardless of mover — symmetric best/second-best for white and black |
| __tests__/gemMove.test.ts | WR-02: skips ungraded null/null entries — a phantom 0.5 must not displace the real argmax in a lost position (D-01) | skips ungraded null/null entries — a phantom 0.5 must not displace the real argmax in a lost position |
| __tests__/gemMove.test.ts | WR-02: an ungraded entry never becomes secondBestEs in a winning position (no spurious C2 gap) | an ungraded entry never becomes secondBestEs in a winning position (no spurious C2 gap) |
| __tests__/gemMove.test.ts | WR-02: an all-ungraded map reduces to all-null fields (same as empty) | an all-ungraded map reduces to all-null fields (same as empty) |
| __tests__/gemSweep.test.ts | LOAD-BEARING (RESEARCH Pitfall 2): a SAN played move ("Nf3") whose UCI equivalent ("g1f3") matches best_move survives — a naive string compare would drop it | LOAD-BEARING: a SAN played move ("Nf3") whose UCI equivalent ("g1f3") matches best_move survives — a naive string compare would drop it |
| __tests__/gemSweep.test.ts | D-04/D-06/D-08: a ply with index < openingPlyCount is dropped even when the played move IS the best move (book gate) | a ply with index < openingPlyCount is dropped even when the played move IS the best move (book gate) |
| __tests__/gemSweep.test.ts | LOAD-BEARING (D-05 yield-to-cursor invariant): returns idle when liveBusy is true, even with unresolved candidates present and nothing in flight — deleting the liveBusy guard MUST turn this test red | LOAD-BEARING (yield-to-cursor invariant): returns idle when liveBusy is true, even with unresolved candidates present and nothing in flight — deleting the liveBusy guard MUST turn this test red |
| __tests__/gemSweep.test.ts | LOAD-BEARING (CR-01): a live null rejection wins over the sweep's gem for the SAME node/ply — the sweep is NEVER consulted once gemByNode has an answer; reverting to a `?? ` collapse MUST turn this red | LOAD-BEARING: a live null rejection wins over the sweep's gem for the SAME node/ply — the sweep is NEVER consulted once gemByNode has an answer; reverting to a `?? ` collapse MUST turn this red |
| __tests__/maiaEncoding.test.ts | matches the two-step path for a black-to-move position (mirrored vocab index, D-08 side handling) | matches the two-step path for a black-to-move position (mirrored vocab index, side handling) |
| __tests__/maiaEncoding.test.ts | spans maiachess.com\'s full 600..2600 range, step 100 (UAT quick 260705-bm3) | spans maiachess.com\'s full 600..2600 range, step 100 |
| __tests__/moveQuality.test.ts | folds a "gem"-quality move into the "good" bucket (Phase 163) — never the "pending" default | folds a "gem"-quality move into the "good" bucket — never the "pending" default |
| __tests__/moveQuality.test.ts | CUMULATIVE_MASS_THRESHOLD is 0.95 (D-02) | CUMULATIVE_MASS_THRESHOLD is 0.95 |
| __tests__/moveQuality.test.ts | CANDIDATE_HARD_CAP is 5 (D-06) | CANDIDATE_HARD_CAP is 5 |
| __tests__/moveStatsCounts.test.ts | derives side from ply parity, not is_user (D-08) | derives side from ply parity, not is_user |
| __tests__/moveStatsCounts.test.ts | counts gem/great/best/good by moverColorAtPly for BOTH sides (D-08) | counts gem/great/best/good by moverColorAtPly for BOTH sides |
| __tests__/openingStatsZones.test.ts | openingStatsZones — MG-entry calibration (D-07 / 260504-my2) | openingStatsZones — MG-entry calibration |
| __tests__/openingStatsZones.test.ts | openingStatsZones — baseline pawn fallbacks (symmetric, 260504-rvh) | openingStatsZones — baseline pawn fallbacks (symmetric) |
| __tests__/openingStatsZones.test.ts | evalZoneColor — zero-centered (260504-rvh) | evalZoneColor — zero-centered |
| __tests__/platformLinks.test.ts | flawchess bot games (quick-260714-qaj) | flawchess bot games |
| __tests__/signedBandGradient.test.ts | sign-zero-leading: [0, 0, 1, 1] → initial color is positive (Phase 68 UAT fix) | sign-zero-leading: [0, 0, 1, 1] → initial color is positive |
| __tests__/tacticComparisonMeta.test.ts | collapses every mate-family motif to "checkmate" (Quick 260620-onv) | collapses every mate-family motif to "checkmate" |
| __tests__/tacticComparisonMeta.test.ts | maps promotion (28) to a family now that D-09 is reversed | maps promotion (28) to a family |
| __tests__/tacticDepth.test.ts | DEPTH_DEFAULT_PRESET is high (full range — Quick 260621-sm8) | DEPTH_DEFAULT_PRESET is high (full range) |
| __tests__/tacticDepth.test.ts | DEFAULT_TACTIC_DEPTH_VALUE is the High/full range {0, 11} (Quick 260621-sm8) | DEFAULT_TACTIC_DEPTH_VALUE is the High/full range {0, 11} |
| engineEvalLookup.test.ts | buildEvalLookup — grading-first precedence (SEED-090, Phase 162 D-01) | buildEvalLookup — grading-first precedence |
| engineEvalLookup.test.ts | resolveReconciledBest (Phase 162 D-03) | resolveReconciledBest |
| flawChessVerdict.test.ts | computeFlawChessVerdict — D-04 aligned | computeFlawChessVerdict — aligned |
| flawChessVerdict.test.ts | computeFlawChessVerdict — D-05 safe divergence | computeFlawChessVerdict — safe divergence |
| flawChessVerdict.test.ts | computeFlawChessVerdict — D-05 sharp divergence | computeFlawChessVerdict — sharp divergence |
| flawChessVerdict.test.ts | computeFlawChessVerdict — D-06 null gate | computeFlawChessVerdict — null gate |
| flawChessVerdict.test.ts | computeFindabilityGate — D-10/D-11/D-12 | computeFindabilityGate |
| maiaWorkerErrors.test.ts | SEED-195: tags the spawn path and attaches live Stockfish worker counts | tags the spawn path and attaches live Stockfish worker counts |
| maiaWorkerErrors.test.ts | SEED-195: tags maia_spawn_path as unknown when the caller has no spawn path | tags maia_spawn_path as unknown when the caller has no spawn path |
| materialDiff.test.ts | gives only the leading side a point total on a mixed imbalance (D-06) | gives only the leading side a point total on a mixed imbalance |
| openingInsights.test.ts | shared constants — stale-constant removal (Phase 76 D-20) | shared constants — stale-constant removal |
| positionVerdict.test.ts | classifyStanding — standing-band boundaries (quick 260709-o72) | classifyStanding — standing-band boundaries |
| positionVerdict.test.ts | computePositionVerdict — standing + bestMove (quick 260709-o72) | computePositionVerdict — standing + bestMove |
| pressureBulletConfig.test.ts | PRESSURE_DELTA_DOMAIN is 0.30 (Plan 88-13 A-5: widened from 0.20 to cover real-world ±20pp+ deltas) | PRESSURE_DELTA_DOMAIN is 0.30 (wide enough to cover real-world ±20pp+ deltas) |
| __tests__/openings.test.ts | findOpening still resolves a non-null opening against the real TSV (proves Task 1s refactor did not break name lookup) | findOpening still resolves a non-null opening against the real TSV (proves the refactor did not break name lookup) |
| engineEvalLookup.test.ts | rankReconciledCandidates (162 UAT card re-source) | rankReconciledCandidates |
| __tests__/formatFlawEval.test.ts | user-POV negation (SC-6) | user-POV negation |
| __tests__/formatFlawEval.test.ts | mate sign (SC-6) | mate sign |
| flawChessVerdict.test.ts | computeFlawChessVerdict — mate scores on either side (quick 260709) | computeFlawChessVerdict — mate scores on either side |

## Known Residual (not fixed, by design of the toolkit)

- `frontend/src/lib/__tests__/botLineTrigger.test.ts` still carries tags in 9 `it.each` case-table `name:` strings (`'... (BOTVOICE-03, D-03)'`, `'... (Phase 223 UAT)'`, `(BOTVOICE-02)` ...) and in the two concatenated multi-line `it(...)` titles at lines 148 and 166 (`'(Phase 223 UAT: ...)'`, `'(D-01: ...)'`). These are runtime title strings, but the token diff does not treat them as titles (it only normalizes the first string literal of a `describe/it/test` call), so editing them is reported as residue and `diff` exits 1. I tried the edit, saw the 11 residue lines, and reverted it to keep the plan gate green. A follow-up could teach `ts_scan.mjs` about `it.each` tables and concatenated titles, or the owner can accept the 11 strings.
- Sentry issue ids (`FLAWCHESS-64`, `-91`, `-92`) in comments of `botGamePgn`, `swUpdate`, `queryClient`, `maiaWorkerErrors` tests stay: they point at Sentry, not `.planning/`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `npm --prefix frontend ci` (lockfile install only). No python install was needed for the tool runs (`uv run python` worked, stdlib only).

**2. [Plan note] Tag shapes the scanner does not match, fixed by hand**
- Found by a broad grep after the scan reached 0: `D4:` in a `describe` title (push), `pre-183` / `pre-211` / `pre-182` in titles (botGameSnapshot, botGameEnd, trainRevealCache, botDrawGate), `(190.1 UAT ...)` / `(UAT round 4)` in trainArrows titles, `UAT 240:` in trainBotCopy titles, `(SC-6)` in formatFlawEval, `(quick 260709)` in flawChessVerdict, and `Task 1's refactor` in openings. All rewritten to say what is checked.

**3. [Plan note] The 241-03 codemod left partial tags**
- e.g. `Phase 203 Plan 02.` and `Task 2:` after the first tag was removed; each was finished by hand.

None of this touched code, assertions, fixtures, expected copy strings or LOCKED wording. No `STATE.md` or `ROADMAP.md` edit.

## Environmental notes

- Sibling executors share the dev Postgres, so the python half of `source_scan_tests.sh` was run serially (same file list, no `-n 4`) as instructed; it passed (95 + 5). Not a plan failure.
- Baseline gates were run on the untouched tree for vitest (`src/lib`: 2413 tests); lint and the source-scan tests were run on the final tree only (the changed files are comment- and title-only, and the same scripts passed in the sibling plans).

## Known Stubs

None.

## Threat Flags

None. Test files only; no endpoints, auth paths or schema.

## Self-Check: PASSED

- Commits `4fef9671a` and `90f7ffcd0` are ancestors of HEAD.
- 66 changed test files confirmed present; `scan --gate` and `diff` for `scopes/241-49.txt` exit 0.
