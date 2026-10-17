---
phase: 241-codebase-cleanup
plan: 30
subsystem: frontend-comments
tags: [cleanup, comments, train, push, hooks]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/codemod/diff/ledger"
  - phase: 241-04
    provides: "TypeScript token diff (ts_scan.mjs, fe_support.py)"
provides:
  - "19 Train and push hooks free of planning tags, with ledgers/241-30.txt covering all 13 INVENTORY rows"
affects: [241-57, 241-60, 241-69]

actuals:
  tokens: 30000
  tasks: 2
  commits: 2
plan_head_before: 7dc02e259035727a1f11b80d843ca5d3dcaaedce
plan_head_after: fe629ef6f4ec87612a0ad3dcf9b54b70ca1ea24b

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-30.txt
  modified:
    - frontend/src/hooks/useTrainGradingEngine.ts
    - frontend/src/hooks/trainGradingSupport.ts
    - frontend/src/hooks/useTrainSession.ts
    - frontend/src/hooks/useTrainPuzzleTelemetry.ts
    - frontend/src/hooks/useTrainRevealTree.ts
    - frontend/src/hooks/useTrainWalkthrough.ts
    - frontend/src/hooks/uciParser.ts
    - frontend/src/hooks/useTreeMoveGrading.ts
    - frontend/src/hooks/useTrainLiveAlternatives.ts
    - frontend/src/hooks/useRevealPreview.ts
    - frontend/src/hooks/useTrainSettings.ts
    - frontend/src/hooks/useTrainProgress.ts
    - frontend/src/hooks/useTrainOnboarding.ts
    - frontend/src/hooks/useTrainLeaderboard.ts
    - frontend/src/hooks/useTrainMedals.ts
    - frontend/src/hooks/useReminderResurface.ts
    - frontend/src/hooks/useDevicePushResync.ts
    - frontend/src/hooks/usePushCapability.ts
    - frontend/src/hooks/useInstallPrompt.ts

key-decisions:
  - "All seeds cited in these hooks (SEED-119, 135, 137, 192, 194, 197) are in .planning/seeds/closed/, so every reference was removed; no `(see SEED-NNN)` pointer remains"
  - "Comments that name identifiers keep current names (useTrainWalkthrough, TrainReminderButton, GradeResult.bestMoveUci/bestLine/esBefore); prose says 'tour' and 'puzzle'"

requirements-completed: [D-01, D-03, D-05, D-10, D-11, D-12, D-13, D-15]

completed: 2026-10-16
status: complete
---

# Phase 241 Plan 30: Train and push hooks comment cleanup Summary

**Planning tags, task ids, review ids and plan-by-plan history are gone from 19 Train grading, session, reveal-tree, telemetry, settings and push hooks (293 tagged lines at the start, 0 after); the non-comment token diff against PHASE_BASE is empty.**

## Accomplishments

- Task 1 (10 hooks: grading engine and support, session, telemetry, reveal tree, walkthrough, uciParser, tree move grading, live alternatives, reveal preview): commit `a66b4c79a`.
- Task 2 (9 hooks: settings, progress, onboarding, leaderboard, medals, reminder resurface, device push resync, push capability, install prompt): commit `fe629ef6f`.
- Codemod vs hand edits: `cleanup.py codemod` rewrote 114 comment lines (95 in task 1, 19 in task 2); the remaining 179 tagged lines were hand-edited in place (the codemod flagged 186 "need hand edit" lines before the multi-line rewrites collapsed some of them).
- History narration was rewritten as present-tense rules where it prevents a regression (session score must come from server `solved_results`, keepalive transport for the Next flush, synchronous page-load guard in the push resync, module-scoped captured `beforeinstallprompt` event) and deleted where it was provenance only.
- Non-inventoried fixes: `useTrainGradingEngine.ts` (removed pointers to `190-01-SUMMARY.md` and `190-RESEARCH.md`), `useTrainPuzzleTelemetry.ts` (Next-flush comment now states the rule instead of "used to go through an axios XHR"), `useInstallPrompt.ts` (three BUG FIX comments reworded to the present tense, test-suite reference kept), `useTrainRevealTree.ts` and `useRevealPreview.ts` (WR-nn review ids dropped), `useTrainOnboarding.ts` (stale "Phase 222 single-walkthrough name" sentence replaced by the server-422 fact).

## Ledger counts (ledgers/241-30.txt)

13 rows, all APPLIED: INV-L1177, L1178, L1179, L1180, L1212, L1213, L1220, L1233, L1234, L1235, L1245, L1246, L1247. Each was re-verified first (D-10); INV-L1212 (App.tsx line range now stale: redirect is at line 824) and INV-L1220 (Analysis.tsx has no `fenToPly`, its helper is `fenToRootPly`) confirmed the inventory's own corrections. INV-L1177 found `_reject_guest` already removed from `app/routers`, and the guest gate is `useUserProfile`-based (App.tsx:229, 752, 755).

## Commands and exit codes (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-30.txt` | exit 0 (19 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-30.txt` | exit 0 (19 selected, 19 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-30.txt --ledger ledgers/241-30.txt` | exit 0 |
| `npm --prefix frontend run lint` | clean |
| `npm --prefix frontend run build` | `tsc -b` + vite build pass |
| `source_scan_tests.sh` | py 95 + 5 passed, fe 9 files / 131 tests passed (same as the untouched baseline) |
| `npm --prefix frontend test -- --run src/hooks` | 51 files, 836 tests passed |

Step 0 baseline (untouched tree): lint and `source_scan_tests.sh` passed before any edit.

## Deviations from Plan

None - plan executed as written. The worktree needed `npm --prefix frontend ci` and `uv sync --group maia-inference` first (lockfile installs only, as the dispatch note said).

## Known Stubs

None.

## Threat Flags

None. The sessionStorage reveal-cache keys, telemetry field names, `GradeResult`/`TrainSessionResult` fields and push payloads are untouched; the token diff is the proof (T-241-46).

## Self-Check: PASSED

- ledgers/241-30.txt, this SUMMARY and all 19 hooks exist.
- Commits `a66b4c79a` and `fe629ef6f` are ancestors of HEAD.
- STATE.md and ROADMAP.md untouched.
