---
phase: 237-train-reveal-chips-move-tree
verified: 2026-10-09T04:00:00Z
status: human_needed
score: 9/9 must-haves verified
covered_files:
  - .planning/phases/237-train-reveal-chips-move-tree/237-01-PLAN.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-01-SUMMARY.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-02-PLAN.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-02-SUMMARY.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-03-PLAN.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-03-SUMMARY.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-04-PLAN.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-04-SUMMARY.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-05-PLAN.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-05-SUMMARY.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-06-PLAN.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-06-SUMMARY.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-07-PLAN.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-07-SUMMARY.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-08-PLAN.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-08-SUMMARY.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-09-PLAN.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-09-SUMMARY.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-10-PLAN.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-10-SUMMARY.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-11-PLAN.md
  - .planning/phases/237-train-reveal-chips-move-tree/237-11-SUMMARY.md
  - app/schemas/train.py
  - frontend/src/App.tsx
  - frontend/src/components/train/TrainLineChips.tsx
  - frontend/src/components/train/TrainMoveTreeList.tsx
  - frontend/src/components/train/TrainReveal.tsx
  - frontend/src/components/train/TrainRevealActionBar.tsx
  - frontend/src/components/train/TrainRevealGameFooter.tsx
  - frontend/src/components/train/TrainSolveScreen.tsx
  - frontend/src/components/train/TrainVerdictDetails.tsx
  - frontend/src/components/train/TrainVerdictStrip.tsx
  - frontend/src/hooks/useTrainPuzzleTelemetry.ts
  - frontend/src/hooks/useTrainRevealTree.ts
  - frontend/src/hooks/useTrainWalkthrough.ts
  - frontend/src/hooks/useTreeMoveGrading.ts
  - frontend/src/lib/mobileBoardControls.ts
  - frontend/src/lib/trainArrows.ts
  - frontend/src/lib/trainBotCopy.ts
  - frontend/src/lib/trainRevealCache.ts
  - frontend/src/lib/trainRevealLines.ts
  - frontend/src/lib/trainTelemetry.ts
covered_digest: "v3:sha256:f0d76144e9213f1f38d3641f874da4a99aac452ac1fa8ac4523a4aca48573bbc"
behavior_unverified: 0
overrides_applied: 0
coincidental_reliance_items: []
human_verification:
  - test: "Real-phone tap leg on the Train reveal (iOS Safari + Android Chrome)"
    expected: "At 390x844-class screens the reveal fits without scrolling; the fixed bottom bar (rewind, back, forward, flip, Analyze, Next) is reachable by thumb and clears the iOS safe area; chip taps, list taps, a piece fork and the strip expand all respond to touch."
    why_human: "Thumb reach, iOS Safari dynamic toolbar and safe-area behaviour cannot be reproduced in an iframe at the same size. Deferred to the owner by design (plan 11, D-11)."
  - test: "First-reveal tour on a real small phone (375x667 class)"
    expected: "Each of the six steps keeps its bubble readable and its ringed target (chips, list) reachable by a short scroll; the final step rings the fixed bottom bar."
    why_human: "Agent UAT noted that on small phones the ringed chips or list sit a short scroll below the fixed bar on steps 1, 2 and 4. Owner judgment is pending on whether that reads badly (plan 11 'Owner judgment')."
---

# Phase 237: Train Reveal Verdict Strip, Line Chips & One Move Tree Verification Report

**Phase Goal:** Make the post-solve reveal fit a phone and teach through one model instead of two (verdict strip, You/Best/Game chips, one pre-loaded move tree with in-place forks, phone action bar, desktop layout, rewritten tour). Frontend, plus the small telemetry v2 backend schema change (D-12).
**Verified:** 2026-10-09
**Status:** human_needed
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths (ROADMAP items 1-7 + guardrails, with CONTEXT D-01..D-14)

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | Verdict strip (avatar + points pill + one clause) replaces the bubble on phones; tap expands verdict + Your-call feedback + also-fine; always starts collapsed (D-05..D-08); Your-call card gone | VERIFIED | `TrainVerdictStrip.tsx` (`useState(false)`, avatar, `TrainScoreChip`, `verdictStripLine`, chevron); `TrainVerdictDetails.tsx` is the expansion child; `TrainReveal.tsx:398-411` renders the strip on phone and `TrainBotBubble` on desktop. Grep finds no `train-line-card` / Your-call card in non-test code. Umami `panel-open` fires only on the collapsed->open click. |
| 2 | One vocabulary everywhere: best / good / decent / wrong move (D-05/D-06); points from `scorePuzzle` only | VERIFIED | `trainBotCopy.ts:411-460` `verdictClauseParts(correctGuess, tier, isBest)` is the single table feeding `verdictStripLine`, expanded verdict and bubble; points read from `GUESS_POINTS`/`MOVE_TIER_POINTS`. `TrainSolveScreen.tsx:813-826` computes `isBest` from the played vs best UCI. Dead-field caveat: IN-01. |
| 3 | Chips You / Best / Game (mark, SAN, eval) replace the three line cards; coinciding roles merge ("You = Best"/"You = Game"), one arrow (D-02); loading/failed states keep Phase 236 | VERIFIED | `TrainLineChips.tsx` (label, `MoveQualityIcon`, SAN, eval pill, `pending` loading spinner / failed hides eval); `data-roles` carries merged roles; `buildChipGroups` in `trainRevealLines.ts`. `TrainLineStepper.tsx` and `useTrainFreePlay.ts` are deleted (`git diff --stat`: -323 / -493 lines) and have no non-test references. WR-01 is a restored stand-in edge case, see Review Findings. |
| 4 | Chip-driven board: reveal opens with You active; only the active chip's arrow and mark are opaque, all others (also-fine included) fade, never hidden; a line-matching move activates that chip; a non-matching root move deselects all (D-04); chip tap returns to puzzle position (D-01) | VERIFIED | `theme.ts:590-593` `TRAIN_FOCUS_ARROW_LIT 0.92 / DIM 0.22`, `BADGE_LIT 1 / DIM 0.32`; `trainArrows.ts:528-534` opacity applied per marker/arrow (dim, not removed). `useTrainRevealTree.ts`: `DEFAULT_ROOT_FOCUS`, `rootFocus` null on non-line root move, `deriveActiveChip`, `selectChip` -> root, `onChipSelect` on line-matching move. Browser UAT (11-SUMMARY item 3): active arrow 0.92, others 0.22. |
| 5 | One move tree: three lines pre-loaded (12-ply cap, D-03) as root branches of the `useAnalysisBoard` tree; list shows active line (numbered, wrapping); moving a piece forks in place with x; one-line Stockfish row (expandable to PV 2) only off known lines; per-move grading markers on sideline moves | VERIFIED | `useTrainRevealTree.ts` grafts via non-navigating `graftLine(lineUcis.slice(0, MAX_LINE_PLIES))`, derived chip ownership, `isOffLine` gate, engine (MultiPV floor `TRAIN_SF_ROW_EXPANDED_LINES = 2`); `TrainMoveTreeList.tsx` + `VariationTree` `wrap` mode; `useTreeMoveGrading.ts` (303 lines) carries grading + vetted marks. No free-play mode flag survives (`isExploring` grep empty). UAT item 5: fork shows `( h6 )`, x delete button, SF row with 2 lines, `?!` badge on h6. |
| 6 | Phone action bar rewind / back / forward / flip + Analyze + Next replaces the bottom nav for the whole reveal; rewind keeps sidelines; first view fits 390x844 with no scroll | VERIFIED | `TrainRevealActionBar.tsx` (BoardControls + Analyze Link + Next); `TrainSolveScreen.tsx:1476` `usePublishMobileBoardControls` publishes it for the whole reveal, `:1882` in-flow instance from `sm`. Agent browser UAT at 390x844: `scrollHeight 844 == innerHeight`, bar fixed, rewind kept `( h6 )` sideline. Real phone leg pending (human). |
| 7 | Desktop: board left with the same controls + Analyze/Next under it; right column = full verdict bubble (no strip) + chips + tree + game line; arrow keys step, Home = puzzle position | VERIFIED | `TrainReveal.tsx:398` `isDesktop ? TrainBotBubble : TrainVerdictStrip`; `TrainRevealGameFooter.tsx` is the game line; `useBoardNavigationInput.ts` handles Home (+131 test lines); `TrainRevealActionBar` shows the "← → Home" hint (`showKeyHint`). UAT at 1280x800: layout, ->, ->, <-, Home all confirmed. |
| 8 | Tour rewritten: six steps (strip, chips, stepping, board/fork+rewind, D-21 "understand, don't memorize", action bar), within `STEPPER_COPY_MAX_CHARS` = 145, only describes what is on screen (`hasAnalyze`, merged chip only when shown), `hasSolution` gone, spotlight reaches the bottom bar | VERIFIED | `trainBotCopy.ts:570-690` `walkthroughCopy` six steps in D-09 order; `WalkthroughContext {hasAnalyze, mergedChip, isDesktop}`; no `hasSolution` anywhere in non-test code; `STEPPER_COPY_MAX_CHARS = 145` retained (`:220`); D-21 text present (`WALKTHROUGH_UNDERSTAND`). Bubble stacked above the strip (D-10). UAT: tour at 390x844, 375x667, 1280x800, rings incl. fixed bar; one defect found and fixed (1a997e563). |
| 9 | Guardrails: SOLV-02 (fork never reaches grading); herring / server-graded verdicts and Phase 211 D-06 marks preserved; restored reveal (`CachedTrainReveal`, Analyze -> Back) restores chip + tree; telemetry v2 (D-12..D-14) and test ids moved off the card structure | VERIFIED | SOLV-02: `TrainSolveScreen.tsx:1343-1362` fork branch sits strictly after the `guess`/`moveApplied` guards, returns `revealTree.playMove` and never calls `gradeAndSolve`. Restore: `trainRevealCache.ts` shape-validated `RevealTreeSnapshot` with `rootFocus`; `useTrainRevealTree` `restored` option. Telemetry: backend `ReviewTelemetry.v: Literal[1, 2]` with `_keys_match_version` validator and separate `REVIEW_TELEMETRY_SCHEMA_VERSION = 2` (solve patch stays v1); frontend `buildReviewTelemetry` stamps v2 with chip/strip keys, D-13 `forked` semantics; Umami events limited to low-frequency actions (`train-solution` kept as the rewind target, `panel-open` for the strip). Tests re-run by the verifier, all green (below). |

**Score:** 9/9 truths verified (0 present-behavior-unverified; the on-device leg is routed to human verification)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `components/train/TrainVerdictStrip.tsx` / `TrainVerdictDetails.tsx` | strip + expansion | VERIFIED | Substantive, wired from `TrainReveal` |
| `components/train/TrainLineChips.tsx` | chips row | VERIFIED | Wired from `TrainReveal:434` |
| `components/train/TrainMoveTreeList.tsx` | tree list | VERIFIED | Wired as `treeList` slot (`TrainSolveScreen:1986`) |
| `components/train/TrainRevealActionBar.tsx` | action bar | VERIFIED | Wired in-flow and via published payload |
| `components/train/TrainRevealGameFooter.tsx` | game line | VERIFIED | Wired `TrainReveal:460` |
| `hooks/useTrainRevealTree.ts` | single reveal tree | VERIFIED | 595 lines, wired `TrainSolveScreen:909` |
| `hooks/useTreeMoveGrading.ts` | sideline grading | VERIFIED | Used by the tree hook |
| `lib/trainRevealLines.ts` | chip model, list view, snapshot | VERIFIED | 463 lines |
| `lib/trainArrows.ts`, `theme.ts` | focus opacity | VERIFIED | Constants and per-arrow opacity |
| `app/schemas/train.py` | v2 telemetry boundary | VERIFIED | Validator + separate review version constant |
| `TrainLineStepper.tsx`, `useTrainFreePlay.ts` | retired | VERIFIED (deleted) | No remaining non-test imports |
| `TrainReveal.tsx` split | 1469 -> 463 lines | VERIFIED | Seams extracted as above |

### Key Link Verification

| From | To | Via | Status |
| ---- | -- | --- | ------ |
| `TrainSolveScreen.handlePieceDrop` | `revealTree.playMove` | fork branch after SOLV-02 guards | WIRED |
| `useTrainRevealTree` | `useAnalysisBoard` (graftLine, goToNode, deleteSubtree) | tree seeding | WIRED |
| `TrainReveal` | strip / bubble / chips / footer | `isDesktop` switch | WIRED |
| `usePublishMobileBoardControls` | `MobileBottomBar` in `App.tsx` | published payload renders `TrainRevealActionBar` | WIRED (see WR-02) |
| `buildReviewTelemetry` | `ReviewTelemetry` backend schema | v2 key set, regex-parity-tested | WIRED |
| `trainRevealCache` snapshot | `useTrainRevealTree` `restored` | shape-validated replay | WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Train reveal component, hook, lib, page tests (33 files) | `npx vitest run src/components/train src/lib/__tests__/{trainArrows,trainBotCopy,trainRevealCache,trainRevealLines}.test.ts src/hooks/__tests__/{useTrainRevealTree,useTrainPuzzleTelemetry}.test.ts src/pages/__tests__/Train.solveLoop.test.tsx` | 33 files, 985 tests passed | PASS |
| Backend telemetry v1/v2 schema + CI parity | `uv run pytest tests/schemas/test_train_telemetry_parity.py tests/schemas/test_train_telemetry_schema.py` | 39 passed | PASS |
| Full gates after the last code commit (orchestrator-reported, not re-run) | frontend lint/build/vitest 5421/knip; backend ruff/ty/nesting/pytest 5448 | green | NOTED |

### Probe Execution

None declared (frontend UI phase); SKIPPED.

### Requirements Coverage

No REQUIREMENTS.md and no mapped IDs. Coverage source is CONTEXT D-01..D-14: D-01..D-04 (truth 4, 5), D-05..D-08 (truths 1, 2), D-09..D-11 (truth 8; agent UAT done, real-phone leg pending), D-12..D-14 (truth 9). No orphaned requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `hooks/useAnalysisBoard.ts` | 166, 183 | Comments reference deleted `TrainLineStepper` | Info | IN-02, misleading comment only |
| `lib/trainBotCopy.ts` | 447-481 | `VerdictCopy.clause` / `verdictClause` unused in production | Info | IN-01, second copy of the vocabulary (test-only) |
| `grep TBD/FIXME/XXX` on phase files | n/a | not run exhaustively; reviewer reported lint and knip clean | Info | none found by review |

### Review Findings Weighed (237-REVIEW.md, all `open`, advisory)

None blocks the goal; none makes a must-have truth false. Each is a narrow edge path:

- **WR-01** (confirmed in code: `gradeFromServerPair` returns an empty-moves `playedLine`; `revealBestUciOf` reads `bestLine.moves[0]` while `TrainSolveScreen:813` uses `bestMoveUci`): on an Analyze -> Back restore that began from the stand-in grade, a chip can show a permanent "…" eval pill and the Best chip can be missing while the clause still says "best move". This touches the restored-reveal guardrail and D-06, but only on the narrow path (Analyze clicked before the background grade lands). Recommended fix before release; classified WARNING.
- **WR-02** (confirmed: both bar instances are mounted, `hidden sm:flex` vs `sm:hidden`): duplicate `btn-train-next` / `btn-train-analyze` / `train-reveal-action-bar` testids, one `display:none`. UAT passed at every size. Risk is automation and test-id lookups resolving to the hidden copy. WARNING.
- **WR-03** (confirmed: `TrainSolveScreen:1988` passes `handleAnalyzeClick`, not the walkthrough-aware handler): leaving via the footer Analyze link skips `walkthrough.leave()`, so the tour is not stamped and replays. Minor. WARNING.
- **WR-04** (confirmed: `useTrainRevealTree.ts:482-489` has no `currentNodeId === id` guard): tapping the already-shown move inflates `review_line_steps` and advances the tour's stepping step. Minor telemetry/tour accuracy. WARNING.
- **IN-01..IN-03:** dead clause field, stale comments, unvalidated restored `rootFocus` (cosmetic, user can tap a chip). Info.

All are cheap to close (one-line guards or a handler swap). Disposition file still lists them `open`; the owner decides fix now vs defer.

### Human Verification Required

#### 1. Real-phone tap leg

**Test:** On a real iPhone (Safari) and Android phone, open Train, solve a puzzle, and use the reveal: tap a chip, tap list moves, drag a piece to fork, tap x, tap rewind, expand and collapse the strip, tap Analyze and Back, tap Next.
**Expected:** First view fits without scrolling; bar sits above the safe area; every control is thumb-reachable and responsive.
**Why human:** Hardware, iOS toolbar and safe-area behaviour. Deferred to the owner by plan.

#### 2. Tour on a small phone

**Test:** Reset `reveal_walkthrough_seen_at` and run the tour on a 375x667-class device.
**Expected:** Bubble readable on all six steps and targets reachable; decide whether the "target a short scroll below the fixed bar on steps 1, 2, 4" trade-off is acceptable, or collapse the strip feedback when leaving step 1 / put the bubble next to its target.
**Why human:** Subjective layout judgment on real hardware (plan 11 'Owner judgment (pending)').

### Gaps Summary

No gaps. Every ROADMAP item (1-7), guardrail and CONTEXT decision D-01..D-14 is implemented, wired and exercised by tests and the agent browser UAT (390x844 no-scroll, 375x667, 768x1024, 1280x800, tour). The 33-file train test sweep and the backend telemetry schema/parity tests were re-run by the verifier and pass. Status is `human_needed` solely because of the planned owner-pending real-phone legs and the small-phone tour trade-off. The four review warnings are confirmed real in code but narrow; recommend closing WR-01 (restore + D-06 consistency) and the one-line WR-03/WR-04 guards before merge, and deciding on WR-02 (single mounted bar or suffixed testids).

---

_Verified: 2026-10-09_
_Verifier: Claude (gsd-verifier)_
