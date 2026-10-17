---
phase: 241-codebase-cleanup
plan: 41
subsystem: frontend
tags: [cleanup, comments, typescript, types, api-client, pages]

requires:
  - phase: 241-04
    provides: "cleanup.py scan/diff/ledger with TypeScript, JSX and CSS support"
provides:
  - "frontend/src/types, frontend/src/api and the non-Analysis/Bots pages free of planning tags in comments, with ledgers/241-41.txt covering all 25 INVENTORY section 6 rows"
affects: [241-51, 241-63, 241-64, 241-67, 241-70]

actuals:
  tokens: 40000
  tasks: 2
  commits: 2
plan_head_before: 689a1b071ef8ce59692f1625b96ae13ed187f695
plan_head_after: e347dd4a296bb68d7a5ba3b88d80fd4a29190957

tech-stack:
  added: []
  patterns:
    - "Hand edits via an exact-substring helper (temp/241-41/subs.py, gitignored) that refuses to write unless every old string occurs the expected number of times"

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-41.txt
  modified:
    - frontend/src/types/{activity,admin,api,bots,endgames,insights,library,position_bookmarks,push,stats,train,users}.ts
    - frontend/src/api/{client,googleAuth}.ts
    - frontend/src/pages/{Admin,Endgames,GlobalStats,Home,Import,OAuthCallbackPage,Openings,Train,Welcome}.tsx
    - frontend/src/pages/activity/{ActivityPage.tsx,charts.js,render.js,styles.css}
    - frontend/src/pages/library/{FlawsTab,GamesTab,LibraryPage}.tsx
    - frontend/src/pages/openings/{GamesTab,InsightsTab,OpeningsDesktopSidebar,OpeningsFilterFields,OpeningsMobileBoardPanel,OpeningsMobileDrawers}.tsx and useOpeningsChartData.ts

key-decisions:
  - "Dividers shortened by a removed tag keep their remaining dashes as-is (no re-padding); a divider is not worth a re-wrap diff"
  - "Misplaced doc blocks were moved, not rewritten: SolveResponse (INV-L1261), TrainSettingsResponse (INV-L1262); the FlawMarker doc lost two lines that described FlawListItem's orientation columns, not a flaw marker"

requirements-completed: [D-01, D-10, D-11, D-12, D-13, D-15, D-17]

duration: ~75min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 41: Frontend types, API client and pages comment cleanup Summary

**All 322 planning-tag lines in 52 scope files (16 types/api, 36 pages) are gone, 23 INVENTORY rows applied and the two B rows left untouched, with an empty non-comment token diff against PHASE_BASE.**

## Performance

- **Duration:** ~75 min
- **Tasks:** 2 (types and api client; pages)
- **Files modified:** 37 frontend files (14 types/api, 23 pages) plus the new ledger. The other 15 scope files were already clean and stay untouched.

## Accomplishments

- First scan: 224 tagged lines in types/api, 98 in pages (322 total). Final `scan --gate` over scopes/241-41.txt: 0.
- `cleanup.py diff` over the scope: exit 0 (52 selected, 37 changed, no residue). Wire field names, API paths, URL params, storage keys and copy are untouched; the `guest_train` gap in `ActivityStatsPayload` (INV-L1281) and the `else if (mostPlayedData)` branch (INV-L1336) are not touched.
- Stale content fixed next to the tags (STYLE-GUIDE 2.2): `'error'` vs `'failed'` job status, "six request fields" (nine), `store_bot_game_service.py:76` line pointer, mobile hero section called "Opening Explorer", the filter-apply description in Openings and FlawsTab (everything stages and commits on Apply), handler names in the Endgames pulse comment, the Import "must not over-claim" rule (the copy prints the game count), `OAuthCallbackPage` redirect chain, `charts.js` path.
- Planning pointers into `.planning/` (CONTEXT, notes, PLAN, RESEARCH) deleted from comments in endgames.ts, bots.ts, client.ts, library.ts, train.ts, Import.tsx.

## Task Commits

1. **Task 1: types and api client** - `31f3aa8d5` (`chore(comments): frontend types and api client`)
2. **Task 2: pages** - `e347dd4a2` (`chore(comments): frontend pages (rest)`)

`commits: 2` is measured with `git rev-list --count 689a1b071..HEAD` before the SUMMARY commit.

## Codemod vs hand edits

| Scope | Tagged lines at start | Codemod rewrote | Hand edits (substitutions) |
|---|---|---|---|
| types + api (16 files) | 224 | 123 lines in 11 files | about 125 spans (helper scripts, 1 to 31 spans per file) |
| pages (36 files) | 98 | 34 lines in 15 files | about 90 spans |

`git diff -U0` was reviewed after both codemod runs. Codemod residue, all fixed by hand: tags left in `Phase 238:` / `Phase 87.1:` / `SURGE-04/D-03:` / `D-03:` shapes (the codemod only drops the parenthesized forms), a lowercase continuation after a dropped leading tag was not produced anywhere, and no line started with bare punctuation (grep of `^\s*(#|//|\*)\s*[:;,]\s` over the scope: empty).

A broad second grep (UAT, `Plan N`, `Quick N`, `D3`/`D-6`, `RESEARCH`, `v49`, `OQ3`, `Option A`, `Constraint 3`, `review fix`, `Repointed`) found shapes the scan regex misses; all fixed: `224 UAT round N` (Import.tsx, LibraryPage.tsx), `D3`/`D6`/`D-6` (activity page), `Option A` (library GamesTab), `v49 (238 UAT)` and `v9:` (insights.ts), `Quick Scan` kept (a product name), `FLAWCHESS-64` kept in Train.tsx (a Sentry issue id, not a planning tag).

## Ledger (ledgers/241-41.txt, 25 rows)

- APPLIED (23): INV-L1261, L1262, L1278, L1279, L1280, L1331, L1362, L1363, L1364, L1365, L1373 (types/api task); L1289, L1290, L1291, L1292, L1293, L1294, L1295, L1296, L1297, L1334, L1335, L1337 (pages task). Each was re-verified against the current code first (D-10); details are in the ledger lines.
- LEFT (2): INV-L1281 (types/activity.ts, B row) and INV-L1336 (useOpeningsChartData handler, B row).
- Rows that were moves rather than text fixes: L1261 and L1262 (doc block relocated above its interface), L1331, L1363, L1365, L1373 (rule kept, history dropped), L1294 (stale side of a contradiction replaced).

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-41.txt` | exit 0 (52 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-41.txt` | exit 0 (52 selected, 37 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-41.txt --ledger ledgers/241-41.txt` | exit 0 |
| `npm --prefix frontend run lint` | clean |
| `npm --prefix frontend run check:activity-layout` | OK at 320/360/390/414px |
| `npm --prefix frontend run build` | `tsc -b` and vite build pass |
| `source_scan_tests.sh --fe` | 9 files, 131 tests passed |
| source-scan Python half, run serially (same files, no `-n 4`) | 95 passed, then 5 passed (-k selection) |

Baseline (untouched tree): lint, the FE half and the serial Python half all passed before any edit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep and shared-Postgres handling**
- `npm --prefix frontend ci` and `uv sync --group maia-inference` (lockfile installs, no new packages). The Python half of `source_scan_tests.sh` was run serially without `-n`, as the parallel-execution notes require (sibling executors share the dev Postgres). Environmental, not a plan failure.

**2. [Plan note] Task 1 scope included charts.ts and feedback.ts**
- scopes/241-41.txt lists `types/charts.ts` and `types/feedback.ts` (the task file list does not). The scan found them clean, so they stay untouched. The task 1 gates ran over all 16 types/api files via a derived scope file.

**3. [Rule 2 - stale content] Small wording fixes next to removed tags**
- FlawMarker doc in library.ts carried two lines about orientation column sets that belong to FlawListItem; deleted (restates nothing about FlawMarker).
- "Lowered from 5s to halve the worst-case Quick Scan stall window" (Import.tsx) rewritten present-tense; "Corrected 2026-07-13 by 170-RESEARCH.md" chronology deleted from bots.ts, keeping the base-seconds rule.
- Push `unsubscribe` rule in client.ts restated as the rule it protects (toggle-off keeps the stored subscription row) instead of "D-07 ... PERM-04".

**Total deviations:** 1 environmental, 1 scope note, 1 wording group. No code, testid, Umami name, storage key or URL changed.

## Notes for downstream plans

- Comments here keep current identifier names (`totalGames`, `GAME_COUNT_REFRESH_INTERVAL_MS`, `justCommittedFromDrawerRef`), so the rename plans 241-63 and 241-64 need not touch them for comments. The Openings.tsx comments name `justCommittedFromDrawerRef`, `handleDesktopFiltersApply` and `handleMobileFiltersApply`; update them if those are renamed.
- No cross-plan secondary-clause ledger comments were needed.
- Suspected bugs already inventoried (not touched): `guest_train` missing from `ActivityStatsPayload` (INVENTORY 7.2 #9), dead `else if (mostPlayedData)` branch (7.2 #12).

## Known Stubs

None.

## Threat Flags

None. Comments only; the token diff against PHASE_BASE is empty (T-241-58 mitigated by `cleanup.py diff`, lint and build).

## Self-Check: PASSED

Files verified present: ledgers/241-41.txt and this SUMMARY. Commits `31f3aa8d5` and `e347dd4a2` are ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
