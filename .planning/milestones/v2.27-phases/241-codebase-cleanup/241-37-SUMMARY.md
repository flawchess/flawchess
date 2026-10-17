---
phase: 241-codebase-cleanup
plan: 37
subsystem: frontend-comments
tags: [cleanup, comments, train, planning-tags]

requires:
  - phase: 241-04
    provides: "TypeScript/JSX token diff and scan support in cleanup.py"
provides:
  - "32 Train component files under frontend/src/components/train (incl. medals/) free of planning tags and UAT-round chronology"
  - "ledgers/241-37.txt with a status line for all 32 INVENTORY section 6 rows in the scope"
affects: [241-57, 241-69]

actuals:
  tokens: 15000
  tasks: 2
  commits: 2
plan_head_before: f02d28e18faff898032f7aa1060e45900ccef16b
plan_head_after: 04a3e74fc75f81d159cb496512b4b4acbde0e46d

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-37.txt
  modified:
    - frontend/src/components/train/TrainScoreScreen.tsx
    - frontend/src/components/train/TrainReminderButton.tsx
    - frontend/src/components/train/TrainScheduleSettings.tsx
    - frontend/src/components/train/TrainStartScreen.tsx
    - "plus 28 more Train components and medals/ files (see the two task commits)"

key-decisions:
  - "Rewrote the large headers (TrainReminderButton, TrainScheduleSettings, TrainScoreScreen, TrainStartScreen) by hand as present-tense rules instead of keeping the codemod's partial output, because the codemod leaves 'Phase 222:' / 'D-13 resolver inputs' style residue and orphaned fragments on 115 of 167 flagged lines in task 1"
  - "Comments naming identifiers keep current names (shield_level, train-shield-*, btn-signup-why-*, btn-train-bot-walkthrough-next, nextTestId) per D-01/D-05; prose uses puzzle / freezes / tour"

requirements-completed: [D-01, D-03, D-05, D-10, D-11, D-12, D-13, D-15]

duration: ~85min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 37: Train components comment cleanup Summary

**All 32 Train component files now state the current UI without Phase/D-NN/SEED/UAT-round pointers; the token diff against PHASE_BASE is empty and all 32 INVENTORY rows are APPLIED.**

## Accomplishments

- Task 1 (`d082dc8a8`, `chore(comments): frontend Train score, schedule, reminder, start screen`): 9 files, 162 blocking scan matches cleared.
- Task 2 (`04a3e74fc`, `chore(comments): frontend Train components (rest)`): 23 files, 84 hand-edit matches plus 40 codemod lines cleared.
- INV-L943: TrainReminderButton's module docstring is now five numbered present-tense invariants (live-state-only resolver; slot state vs interaction state; row beside Done holds only a pressable control; iOS tap writes `reminder_intent_at` first; desktop has no Remind me and `belowRow` follows `has_mobile_subscription`), and the UAT-round body comments are rewritten.
- Complexity-cap rationales removed (INV-L861, L862, L863): TrainScoreRankLines, the Guarded* wrappers, ReminderControls, PuzzlesPerSessionControl and resolveScheduleCardVisibility no longer cite "the cap of 15".

## Ledger

32 lines in ledgers/241-37.txt, all APPLIED (0 SKIPPED, 0 MOVED, 0 LEFT, 0 DEFERRED). Every row was re-verified against the code first (D-10). Rows where re-verification changed the wording beyond the inventory's suggestion:

- INV-L880: the score screen's green sound is WinChime (via `game-win`), while the per-puzzle reveal plays `score-full`, so "reusing the exact per-puzzle mapping" was false; rewritten.
- INV-L882: `LandingState` has seven kinds, so the count "six" is dropped everywhere.
- INV-L912: the function is `_judge_one_day` (confirmed in app/services/train_scheduler.py); the comment now also names its fourth outcome, "neutral".
- INV-L911: no `TrainLineStepper` component exists any more, so the paragraph is deleted.
- INV-L875: no caller passes `nextTestId`; the dead prop stays (INVENTORY 7.1 #29), only its doc changed.

## Codemod vs hand edits

- Codemod (`cleanup.py codemod`): 52 lines in 6 files (task 1) and 40 lines in 15 files (task 2) = 92 lines. Every codemod output was reviewed with `git diff -U0`.
- Hand edits: about 40 multi-line edit batches (`temp/241-37/e_*.py`, exact-string replacement) covering the remaining 199 flagged lines plus fragments the codemod left behind.
- Codemod fix-ups: orphan fragments ("Quick" / "the schedule card now sits..."), `//, so` after a dropped `(WR-02)`, `Phase 222:` / `D-13 resolver inputs` leftovers. The `^\s*(#|//|\*)\s*[:;,]\s` grep over the scope is clean after the fixes.

## Non-inventoried fixes (STYLE-GUIDE 2.2)

- UAT-chronology comments the scanner does not tag (`193 UAT round N`, `UAT item 5 (post-review fix)`, `sketch 005/006/008`, `UI-SPEC E7`, `(UAT 2026-10-09)`) were removed or rewritten as rules in TrainScheduleSettings, TrainStartScreen, TrainStatsCard, TrainStreakCard, TrainFlawFixedBanner, TrainMoveTreeList, TrainVerdictStrip.
- TrainStartScreen: the `totalPoints` comment about a hardcoded `* 2` is now a rule ("use the shared per-puzzle max").
- TrainReminderResurfaceBanner: the WR-01 history comment became the rule that the CTA waits for the push-capability probe.
- ImportAskActions: dropped the dated prod-statistics sentence, kept the mechanism.
- TrainLeaderboardCard, MedalClaimDialog, TrainMedalDialogHost: "(locked)" decision pointers dropped.

## Verification (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-37.txt` | exit 0 (32 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-37.txt` | exit 0 (32 selected, 32 changed, no residue) |
| `cleanup.py ledger --scope ... --ledger ledgers/241-37.txt` | exit 0 |
| `npm --prefix frontend run lint` | clean |
| `npm --prefix frontend run build` | `tsc -b` + vite build pass |
| `npx vitest run src/components/train` | 26 files, 678 tests passed |
| `source_scan_tests.sh --fe` | 9 files, 131 tests passed |
| `source_scan_tests.sh` Python half, serial (no `-n 4`) | 95 passed + 5 passed |

Step 0 baseline (untouched tree): lint and `source_scan_tests.sh --fe` passed. The Python half of the source-scan tests was run serially instead of `-n 4` because sibling executors share the dev Postgres (environmental, per the dispatch note), not a plan failure.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `uv sync --group maia-inference` and `npm --prefix frontend ci` (lockfile installs only, no new packages) before the baseline gates.

**2. [Plan note] Ledger has 32 lines, split 17 + 15 across the two commits**
- INV-L942 (TrainStatsCard) is listed in task 2's read_first but TrainStatsCard is a task 1 file, so it was edited and ledgered in task 1.

No behavior, testid, Umami attribute, storage key or copy change. The non-comment token diff against PHASE_BASE is empty.

## Known Stubs

None.

## Threat Flags

None. Comments only; no new endpoints, auth paths or schema changes.

## Self-Check: PASSED

- Ledger and all 32 files present; commits `d082dc8a8` and `04a3e74fc` are ancestors of HEAD.
- `git rev-list --count f02d28e18..HEAD` = 2 before this SUMMARY commit.
