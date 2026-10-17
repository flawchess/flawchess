---
phase: 241-codebase-cleanup
plan: 36
subsystem: frontend
tags: [cleanup, comments, typescript, jsx, train]

requires:
  - phase: 241-03
    provides: "cleanup.py codemod, decision lookup"
  - phase: 241-04
    provides: "TypeScript/JSX scan and token diff"
provides:
  - "TrainSolveScreen.tsx and TrainReveal.tsx free of planning tags and UAT/FINDING chronology, with ledgers/241-36.txt"
affects: [241-57, 241-69]

actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: 297158250c71be5ad8a6dd1953ca3946d662ba21
plan_head_after: 1991bf26c95b5f4120e8cceeea108998b4b1e44a

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-36.txt
  modified:
    - frontend/src/components/train/TrainSolveScreen.tsx
    - frontend/src/components/train/TrainReveal.tsx

key-decisions:
  - "Rewritten prose says 'tour' and 'puzzle'; comments naming an identifier keep its current name (walkthroughHideRef, useTrainWalkthrough, showResultRow) until plans 241-69 and 241-57 rename them"
  - "The comment above showResultRow got only its bare tags stripped (T-190-12, 'Phase 211'); its stale 'free-play seed memo' wording is left for 241-57 as the plan directs"

requirements-completed: [D-01, D-03, D-05, D-10, D-11, D-12, D-13, D-15]

duration: 55min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 36: Train solve screen and reveal comments Summary

**TrainSolveScreen.tsx (about 2,000 lines) and TrainReveal.tsx carry no planning tags, UAT-round notes or FINDING B labels any more, all 11 INVENTORY rows are APPLIED after re-verification, and the token diff against PHASE_BASE is empty.**

## Accomplishments

- First scan: 233 output lines for the two files (about 229 tagged lines). Final `scan --gate`: 0 matches. No open-seed pointer was needed: the only SEED tag (SEED-119) points at a closed seed, so it was dropped.
- Codemod vs hand edits: the codemod rewrote 73 lines in TrainSolveScreen.tsx and 23 in TrainReveal.tsx (all reviewed with `git diff -U0`; none reverted). It strips only parenthesised tag groups, so the 151 + 30 lines it flagged "needs hand edit" (mostly `Phase NNN:` leading prefixes) were done by hand with exact-match replace scripts (5 batches for TrainSolveScreen, 1 for TrainReveal, each asserting a single match per edit and running in `temp/241-36/`).
- Every rewrite kept the why and dropped the provenance. History narration became a rule where it prevents a regression (e.g. "Don't test `puzzle_type !== 'herring'`: a sharp filler satisfies it"; the Analyze note now says the herring game "must not" be opened in full).
- Glossary applied: "walkthrough" prose became "tour" (rows 21), "verdict bubble" became "verdict card" for the desktop surface (row 24), "free-play" in the board-row spotlight comment became "sidelines" (row 23, and it names the real tour step), "drill" became "puzzle" (row 16). No identifier was renamed.

## Ledger (ledgers/241-36.txt)

All 11 rows APPLIED, each re-verified first (D-10): INV-L864 (both sites), L867, L887, L888, L889, L914, L915, L916, L917, L937, L945.

Re-verification findings that changed the proposed text or confirmed it:
- L887: the game card is fetched by `TrainRevealGameFooter` (mounted only once the verdict exists), not by `TrainReveal` itself, and there is no tactic-lines PV fetch; the header says exactly that.
- L916: `useReminderResurrectRedirect` does not exist; `useReminderResurfaceRedirect` does (App.tsx).
- L917: `walkthroughTreeStepRef` does not exist; `walkthroughHideRef` does.
- L867: the settings sheet (`SettingsPanel.tsx`) carries the sound switch.
- L914: `showAlsoFine` and `comebackHint` no longer exist anywhere in `frontend/src`.
- L945: the eslint-disable directive head is untouched; only the description tail was shortened.

## Task Commits

1. **Task 1: TrainSolveScreen.tsx + 9 rows** - `0a260a91c` (`chore(comments): frontend TrainSolveScreen`)
2. **Task 2: TrainReveal.tsx + 2 rows + plan gates** - `1991bf26c` (`chore(comments): frontend TrainReveal`)

`commits: 2` is measured with `git rev-list --count 297158250..HEAD` before this SUMMARY commit.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-36.txt` | exit 0 (2 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-36.txt` | exit 0 (2 selected, 2 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-36.txt --ledger ledgers/241-36.txt` | exit 0 |
| `npm --prefix frontend run lint` | clean (baseline also clean) |
| `npm --prefix frontend run build` | `tsc -b` + vite build pass |
| `source_scan_tests.sh --fe` | 9 files / 131 tests passed |
| source-scan Python half, run serially (no `-n 4`) | 95 passed + 5 passed |
| `vitest run src/components/train` | 26 files / 678 tests passed |
| punctuation-start grep `^\s*(#\|//\|\*)\s*[:;,]\s` over both files | no hits |

## Deviations from Plan

### Environmental

**1. [Rule 3 - Blocking] Fresh-worktree setup and serial Python half**
- `npm --prefix frontend ci` and `uv sync --group maia-inference` (lockfile installs only) before the baseline; no tracked files changed. Baseline lint passed before any edit.
- As instructed for parallel wave-3 executors, the Python half of `source_scan_tests.sh` was run serially (same file list, no `-n 4`) to avoid xdist database-name collisions with sibling worktrees. Environmental, not a plan failure.

### Non-inventoried fixes (Rule 2, stale content, STYLE-GUIDE 2.2)

- TrainSolveScreen.tsx: `Called instead of ... Plan 05 Task 3 wires a real callback` now says Train.tsx passes the callback (verified: `onNext={handleNext}` in Train.tsx). "Rewind (the old Solution button)" and the "used to open in full / used to hide Analyze" history in the Analyze-target comment became present-tense rules. "Both used to mount (one CSS-hidden)" became "Mounting both would duplicate testids".
- TrainSolveScreen.tsx: a comment claiming the tour bubble "lives in TrainReveal" now says the tour renders as a board overlay (`TrainTourOverlay`), which is what the code does.
- TrainReveal.tsx: the header's claim that both answer-adjacent fetches are "owned" by the component was corrected (the game-card fetch lives in the footer component).
- Dropped the clause "is what makes the D-10 mutation test meaningful" (a pointer to a planning decision with no code-side meaning) rather than inventing a replacement.

**Total deviations:** 1 environmental, 4 comment-content fixes next to removed tags. No code, testid, Umami name, storage key or copy string changed (token diff empty).

## Left for other plans

- The comment above `showResultRow` still says "free-play seed memo"; 241-57 rewrites it with the `showResultRow` to `showReveal` rename (only bare tags were stripped here).
- Identifiers `walkthroughHideRef`, `useTrainWalkthrough`, `walkthroughTarget`, `WalkthroughContext` still carry the old term (241-69).
- No ledger comment lines for rows owned by other plans were needed.

## Known Stubs

None.

## Threat Flags

None. Comments only; `cleanup.py diff` confirmed JSX markup, testids and Umami attributes are token-identical to PHASE_BASE (T-241-53).

## Self-Check: PASSED

Files verified present: ledgers/241-36.txt, TrainSolveScreen.tsx, TrainReveal.tsx. Commits `0a260a91c` and `1991bf26c` are ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
