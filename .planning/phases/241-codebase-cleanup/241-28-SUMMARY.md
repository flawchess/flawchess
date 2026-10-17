---
phase: 241-codebase-cleanup
plan: 28
subsystem: frontend-hooks
tags: [cleanup, comments, bot-game, hooks, typescript]

requires:
  - phase: 241-04
    provides: "cleanup.py FE support (fe_support.py / ts_scan.mjs): scan, diff and ledger for .ts/.tsx"
provides:
  - "The ten bot-game hooks (useBotGame and its nine siblings) free of planning tags and of 'moved into X / pre-split' breadcrumbs, with an empty non-comment diff against PHASE_BASE"
  - "ledgers/241-28.txt: status of all 14 INVENTORY section 6 rows in these files"
affects: [241-58]

actuals:
  tokens: 44000
  tasks: 2
  commits: 2
plan_head_before: 7dc02e259035727a1f11b80d843ca5d3dcaaedce
plan_head_after: 13117c0617c7e2dd66e7a15c7c67547b551c6cd1

tech-stack:
  added: []
  patterns:
    - "Sub-hook ownership comments name the hook that owns each ref/state (useBotGameClock, useBotGameSnapshot, useBotGameDrawOffer, ...) instead of 'stays in useBotGame.ts for now'"

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-28.txt
  modified:
    - frontend/src/hooks/useBotGame.ts
    - frontend/src/hooks/useBotGameClock.ts
    - frontend/src/hooks/useBotGameDrawOffer.ts
    - frontend/src/hooks/useBotGameEngineDispatch.ts
    - frontend/src/hooks/useBotGameMoves.ts
    - frontend/src/hooks/useBotGameSnapshot.ts
    - frontend/src/hooks/useBotGameVoice.ts
    - frontend/src/hooks/useBotPersonaWins.ts
    - frontend/src/hooks/useStoreBotGame.ts
    - frontend/src/hooks/useWinCelebrationHold.ts

key-decisions:
  - "Bug-fix comments (useStoreBotGame shouldRetryStore, the grade-continuation staleness guard, the already-hidden-tab seed) were kept as rules ('Don't return true unconditionally for a 401: ...') with the review/CR tags and the 'used to' narration dropped, per STYLE-GUIDE 2.1"
  - "FLAWCHESS-64 in useBotGameSnapshot.ts is a Sentry issue id, not a planning tag (the scan does not flag it), so it stays"

patterns-established:
  - "A comment that names an owner is re-verified against the useRef/useState declaration before it is rewritten (hasLeftBookRef and lastRootPracticalScoreRef are declared in useBotGameSnapshot, not useBotGame)"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15]

duration: 100min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 28: Bot-game hooks comment cleanup Summary

**All 318 scan matches (the plan estimated about 306) in the ten bot-game hooks are rewritten or removed (including about 30 "moved into X / pre-split" breadcrumbs in useBotGame.ts), 14 of 14 INVENTORY rows are applied after re-verification, and the token diff against PHASE_BASE is empty.**

## Performance

- **Duration:** about 100 min
- **Tasks:** 2
- **Files modified:** 10 hooks plus the new ledger

## Accomplishments

- Scan baseline: 192 tagged lines in the three Task 1 files and 126 in the seven Task 2 files; now 0 across `scopes/241-28.txt`.
- useBotGame.ts header rewritten for the sub-hook split: it names where the clock, move commit, engine dispatch, snapshot, draw-offer and voice pieces live, and the persistence paragraph says "this hook and its sub-hooks" own the four localStorage write sites (verified by grep). 22 breadcrumb comments removed, "(215-03 Task N)" stripped from the five sub-hook dividers (banners kept), three more pre-split narrations turned into present-tense rationale.
- Ownership notes fixed against the code: `hasLeftBookRef` and `lastRootPracticalScoreRef` are owned by useBotGameSnapshot, `abortControllerRef` by useBotGame (also passed to useBotGameSnapshot), `runBotTurnRef` is the only thing useBotGameEngineDispatch returns of the dispatcher.
- Content corrections found while verifying rows: `outcomeKindFor` resolves from the BOT's point of view (INV-L1162); the 'player-threat' probe is retired, so the "threat probe needs the post-move Chess" rationale in useBotGameMoves was stale (INV-L1199); `gameUuidRef` in the header is really the `gameUuid` state; `UseBotGameState.live` now also states the engine-gate case that `engineGateRequired()` produces.

## Task Commits

1. **Task 1: useBotGame, useBotGameClock, useBotGameEngineDispatch (7 rows)** - `7de6dd769` (`chore(comments): frontend hooks useBotGame, clock, engine dispatch`)
2. **Task 2: the other seven bot-game hooks (7 rows)** - `13117c061` (`chore(comments): frontend hooks bot game (rest)`)

`commits: 2` above is measured with `git rev-list --count 7dc02e259..HEAD` before the SUMMARY commit.

## Commands and exit codes (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-28.txt` | exit 0 (10 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-28.txt` | exit 0 (10 selected, 10 changed, no residue, directive heads equal) |
| `cleanup.py ledger --scope scopes/241-28.txt --ledger ledgers/241-28.txt` | exit 0 (14 rows) |
| `npm --prefix frontend run lint` | clean |
| `source_scan_tests.sh` | py 95 + 5 passed, fe 9 files / 131 tests passed |
| `npm --prefix frontend test -- --run useBotGame useStoreBotGame useWinCelebrationHold useBotPersonaWins` | 4 files, 134 tests passed |

Step 0 baseline (untouched tree): lint and the frontend part passed; the first two Python source-scan runs hit fixture-setup errors (all 95 tests errored at setup, nothing failed an assertion) while sibling wave-3 worktrees were cloning the test database template concurrently. The same tests passed when re-run alone and the script passed on the third run, so this is environmental contention, not a pre-existing failure.

## Ledger (ledgers/241-28.txt)

All 14 rows APPLIED: INV-L1160, L1161, L1162, L1194, L1195, L1196, L1197, L1198, L1199, L1200, L1238, L1243, L1244, L1251. INV-L1243's line says 22 breadcrumb comments removed (29 lines carried a 215-03 tag), 5 divider tags stripped, 3 further narrations rewritten.

## Codemod vs hand edits

`cleanup.py codemod --dry-run` on the three Task 1 files proposed 49 mechanical line rewrites and flagged 147 lines for hand editing. The dry-run pairs were read but the codemod was not run for real: most proposed rewrites left a dangling clause (for example "(Plan 06) — never player-derived" losing its subject) and the rest of each comment had to be rewritten for the sub-hook split anyway. Every edit in both tasks was made by hand with the Edit tool, comment text only, about 150 edits in total. `apply-edits` batches were not used; each edit is verified by exact-match replacement, and `cleanup.py diff` proves the token stream is unchanged.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `npm --prefix frontend ci` and `uv sync --group maia-inference` (lockfile installs only, no new packages) before the baseline gates; no tracked files changed.

**2. [Rule 2 - stale content, STYLE-GUIDE 2.2] Non-inventoried fixes next to removed tags**
- useBotGame.ts: header said `gameUuidRef` (the identifier is `gameUuid`); the `live` and `confirmLive` docs now mention the engine-ready gate, matching `useState(() => resume === undefined && !engineGateRequired())`; the "Abort, draw-accept score, one-shot guards" divider became "Abort controller" because only the abort controller is still declared there.
- useBotGameEngineDispatch.ts: `resign()` lives in useBotGameMoves.ts, not useBotGame.ts (comment fixed).
- useBotGameDrawOffer.ts: `applyDrawOfferUpdate`/`resetDrawOfferState` docs no longer describe the replaced inline code.
- useBotGameVoice.ts: dropped the "stopped reading the board when the probe was retired" history from the `onMoveCommitted` doc.
- useStoreBotGame.ts: the "(Before CR-01 this paragraph read ...)" aside is deleted; the cost-based reason for not using `shouldRetryStore` in the drain stays.

**Total deviations:** 1 blocking env prep, 1 group of wording fixes; none touch code, directives, Umami names, storage keys or runtime strings.

## Issues Encountered

- The worktree sandbox rejects compound shell lines that mention git, so git and verification commands were issued one at a time.
- `cleanup.py scan` prints the VIRTUAL_ENV warning on every `uv run`; harmless.

## Known Stubs

None.

## Threat Flags

None. Comments only; T-241-44 mitigated by `cleanup.py diff` (zero residue, equal directive heads) and a clean lint.

## Self-Check: PASSED

Files verified present: the ten hooks and ledgers/241-28.txt. Commits `7de6dd769` and `13117c061` are ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
