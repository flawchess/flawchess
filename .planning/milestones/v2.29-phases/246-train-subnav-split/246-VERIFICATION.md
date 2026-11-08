---
phase: 246-train-subnav-split
verified: 2026-11-06T22:10:00Z
status: passed
score: 16/16 must-haves verified
covered_files:
  - .planning/phases/246-train-subnav-split/246-01-PLAN.md
  - .planning/phases/246-train-subnav-split/246-01-SUMMARY.md
  - .planning/phases/246-train-subnav-split/246-02-PLAN.md
  - .planning/phases/246-train-subnav-split/246-02-SUMMARY.md
  - .planning/phases/246-train-subnav-split/246-03-PLAN.md
  - .planning/phases/246-train-subnav-split/246-03-SUMMARY.md
  - .planning/phases/246-train-subnav-split/246-04-PLAN.md
  - .planning/phases/246-train-subnav-split/246-04-SUMMARY.md
  - .planning/phases/246-train-subnav-split/246-05-PLAN.md
  - .planning/phases/246-train-subnav-split/246-05-SUMMARY.md
  - .planning/phases/246-train-subnav-split/246-06-PLAN.md
  - .planning/phases/246-train-subnav-split/246-06-SUMMARY.md
  - .planning/phases/246-train-subnav-split/246-07-PLAN.md
  - .planning/phases/246-train-subnav-split/246-07-SUMMARY.md
  - .planning/phases/246-train-subnav-split/246-08-PLAN.md
  - .planning/phases/246-train-subnav-split/246-08-SUMMARY.md
  - app/repositories/train_repository.py
  - app/routers/train.py
  - app/schemas/train.py
  - frontend/src/components/train/TrainArchiveTab.tsx
  - frontend/src/components/train/TrainPuzzleCard.tsx
  - frontend/src/components/train/TrainScheduleSettings.tsx
  - frontend/src/components/train/TrainStartScreen.tsx
  - frontend/src/components/train/TrainStreakCard.tsx
  - frontend/src/components/train/TrainSubnav.tsx
  - frontend/src/hooks/useTrainArchive.ts
  - frontend/src/hooks/useTrainLoop.ts
  - frontend/src/lib/analysisUrl.ts
  - frontend/src/lib/trainRoute.ts
  - frontend/src/pages/Train.tsx
covered_digest: "v4:sha256:3b5a8d1ff59b0623d07da09ae6927b55cc64b0df1e766f05e42be90ce7bcf105"
behavior_unverified: 0
overrides_applied: 0
re_verification: false
human_verification:
  - test: "IN-03: look at the Mastered / Parked pills on /train/archive/parked at desktop and 375px"
    expected: "The compact pills and the explainer sentence look right. The owner replaced the full-width group with pills on 2026-11-07 (D-04)."
    why_human: "A visual judgement for the owner."
    result: "passed, owner approved 2026-11-07 (246-UAT.md test 2)"
---

# Phase 246: Train Subnav Split Verification Report

**Phase Goal:** Split the single-column Train landing into three URL-routed tabs (Today / Leaderboard / Archive) and turn the mastered and parked counts into a browsable archive, as the base for the later Retry feature and a Stats tab.
**Verified:** 2026-11-06
**Status:** passed (human_needed on 2026-11-06; all three human items passed in 246-UAT.md by 2026-11-07, recorded below this report's original text)
**Re-verification:** No, initial verification

All locked decisions were checked against the code as it exists now, not against the SUMMARY claims. The code does what the phase set out to do. No must-have failed outright. One locked decision (D-15, tabs do not move) has a measured deviation that the owner must rule on. Two smaller items need a human look: the toggle styling (IN-03) and the draft empty-state copy.

## Goal Achievement

### Observable Truths (CONTEXT D-01 to D-16 plus the ROADMAP contract)

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| D-01 | Three URL-routed tabs at `/train`, `/train/leaderboard`, `/train/archive`; `/train` still works; `TabsList variant="brand"`, desktop and mobile | VERIFIED | `lib/trainRoute.ts` `TRAIN_TAB_PATHS` and `parseTrainRoute` (exact match, unknown paths redirect via `<Navigate>` in `Train.tsx`). `TrainSubnav.tsx` is one responsive `TabsList variant="brand"` with three triggers. `App.tsx` route is `/train/*`; nav active state uses `startsWith('/train')` (lines 178, 711) and the mobile title uses a `startsWith` lookup, so sub-paths are covered. |
| D-02 | Today: streak card + Start + rank line, full schedule card, collapsible and summary removed, "Next session" stays | VERIFIED | `TrainScheduleSettings.tsx` renders `<Card as="section">` directly (no Collapsible, `btn-train-schedule-toggle` gone). `train-next-session` line still rendered at line 584, fed by `nextSessionDate` from `TrainStartScreen` (line 439). 246-06 step 8 measured controls visible with no click. |
| D-03 | Leaderboard tab holds the existing `TrainLeaderboardCard` | VERIFIED | `Train.tsx` `route.tab === 'leaderboard'` renders `TrainLeaderboardCard` in `max-w-2xl`. The card is no longer mounted from `TrainStartScreen` (grep: only `TrainStartScreen` docstring mentions it). |
| D-04 | Archive: Mastered/Parked toggle with counts and explainer popovers, 20 per page via `Pagination`, newest first, list and page in the URL, `TrainStatsCard` replaced | VERIFIED | `TrainArchiveTab.tsx`: `ArchiveToggle` with counts from `useTrainProgress`, `InfoPopover` per side, `Pagination`, `ARCHIVE_PAGE_SIZE = 20`, list in the path (`buildArchivePath`), page in `?page=` (`parseArchivePage`, push on change, replace on over-range). `TrainStatsCard.tsx` and its test are deleted and nothing references them. |
| D-05 | New `TrainPuzzleCard` on `LazyMiniBoard`, horizontal, one column phone / two desktop, pre-mistake position, no arrows | VERIFIED | `TrainPuzzleCard.tsx` is a standalone card, flex row (board left, details right), `LazyMiniBoard` with `fen` and `lastMove` only (no `arrows`). Grid is `grid-cols-1 lg:grid-cols-2`. 246-06 step 3 measured 2 columns desktop, 1 at 375px, board left of Analyze on all 20 cards. |
| D-06 | Subnav hidden in solve/score/restored-reveal; medal host in layout; no `POST /train/sessions` and no grading engine on Leaderboard or Archive | VERIFIED | `useTrainLoop.ts`: one-way `todayVisited` latch gates both `startSession()` and `useTrainGradingEngine({ enabled })`; `resolveTrainImmersive` counts a cached reveal from first paint. `Train.tsx` renders `{!immersive && <TrainSubnav/>}` and `{!immersive && <TrainMedalDialogHost/>}`. I re-ran the page and hook suites (200 tests pass), which include the deep-link tests asserting 0 POSTs and 0 Workers; 246-02/05/08 record that mutating the latch and the gates makes them fail. 246-06 step 1 measured 0 session POSTs on a fresh `/train/archive` and exactly 1 after Today. |
| D-07 | Card shows opponent and rating, game date, time control, and status line `Mastered Oct 3, 2026` / `Parked Oct 3, 2026 · 4 misses` | VERIFIED | `TrainPuzzleCard.tsx` `statusLine()` and `opponentLabel()`; date format `MMM d, yyyy`; miss count from `fail_count`, singular handled; date is `last_solved_at` from the endpoint. |
| D-08 | No played move, motif or severity on the card or in the wire shape | VERIFIED | `TrainArchiveItem` schema has exactly 14 fields with no move/motif/severity (backend test pins the exact key set; I re-ran the archive tests, 17 pass). Card has no such text and passes no `arrows`. |
| D-09 | Per-list empty state with explainer copy and a link to Today, no import button | VERIFIED (owner chose title only) | `ArchiveEmpty` + `EMPTY_COPY`, `Go to Today` link (`btn-train-archive-today`); 246-06 step 7 measured it for a guest on both lists with no import button. Copy is marked DRAFT, see human item 3. |
| D-10 | Rank line uses the Points board only, `#N this week`, links to `/train/leaderboard` | VERIFIED | `TrainStreakCard.tsx` `TrainRankLine` reads `data.points.viewer?.rank`, never the accuracy board; a `Link` to `TRAIN_TAB_PATHS.leaderboard`. |
| D-11 | No rank shows `See this week's leaderboard`, no fallback flash while loading, guests and hidden viewers get the same line | VERIFIED | `TrainRankLine` renders a reserved non-breaking-space row while `isPending`, then the rank or the fallback. Planning's open question is closed by a test: `test_train_leaderboard.py` now asserts `guest_body["points"]["viewer"]["rank"] == 1` (guest) and the hidden-viewer test passes. |
| D-12 | `Points today: 5/9` muted line in the streak card, completed state only; `TrainStatsCard` deleted | VERIFIED | `TrainStreakCard` `pointsToday` prop, `train-points-today` span after the rank line; `TrainStartScreen` passes it only in the completed branch (line 436). |
| D-13 | Sort by latest `drill_solves.solved_at` per puzzle, newest first | VERIFIED | `_archive_page_stmt`: grouped `max(solved_at)` per `(game_id, ply)` for this user's `SR_ITEM` solves, `DESC NULLS LAST`, tiebreak `game_id DESC, ply DESC`, sorted and limited before `games` is joined (no N+1, `pgn` read for the page's rows only). Repository tests for ordering, stable tiebreak and filtering of herring/other-user solves pass; 246-01 records mutation checks. |
| D-14 | Evicted `game_flaws` rows stay listed; list length matches the toggle counts | VERIFIED | The query joins no `game_flaws` at all, which honours the outcome (stricter than the `LEFT JOIN` wording, as the plan documented). `total` comes from `_count_drill_items_by_status`, the function behind `mastered_count`/`parked_count`. Tests cover an item with no `game_flaws` row and a corrupt PGN (row kept with null FEN). |
| D-15 | Tabs span `max-w-7xl` on every tab; Today/Leaderboard in a centered `max-w-2xl` column; Archive full width; tabs do not change size or position when switching | ACCEPTED BY OWNER (2026-11-07, no shift seen, no CSS added; measured shift stays a known limitation) | Structure is right: shared `TRAIN_TAB_PAGE_CLASS` (`max-w-7xl`), `LANDING_CONTAINER_CLASS` and the Leaderboard panel are `max-w-2xl`, the Archive panel has no `max-w-*`. But 246-06 step 2 measured `left` moving 165.81 to 158.99 (6.82px) on a long Archive list because of the page scrollbar. No `scrollbar-gutter` exists anywhere in `index.css`, so any classic-scrollbar browser will show it. Width and top are stable. |
| D-16 | Tabs always show on the landing (Tank intro, no-games state); hidden only per D-06 | VERIFIED | `Train.tsx` shows the subnav whenever `!immersive`; 246-06 step 7 measured tabs present in a guest session on Today and both empty Archive lists. Tank intro and stepper outcomes are covered in `Train.subnav.test.tsx` (246-08). The only other hiding case is the transient profile-loading/error screen, which precedes any landing. |

**Score:** 16/16 truths verified, with D-15 by owner decision. `behavior_unverified`: 0. Both behaviour-dependent invariants (latch keeps POST and Worker off other tabs; hidden landing records nothing) have a passing behavioural test that I re-ran, with recorded mutation checks.

### ROADMAP trap list

| Trap | Status | Evidence |
|------|--------|----------|
| Session POST and engine only on Today | VERIFIED | `todayVisited` latch, see D-06. Chosen design is a layout-level latch rather than moving hooks, as CONTEXT suggested. |
| Subnav hidden in solve/score/restored reveal, no flash | VERIFIED | `resolveTrainImmersive` truth table and page tests. |
| Medal host in the layout | VERIFIED | `Train.tsx` mounts `TrainMedalDialogHost` outside immersive views; it opens on a Leaderboard deep link per the 246-08 tests. |
| Sort key and status-only-changes-on-solve | VERIFIED | CONTEXT D-13 verification plus the grouped-solves query. P4 on prod: 0 mastered/parked items without an SR solve row. |
| Count mismatch from evicted flaw rows | VERIFIED | See D-14. P6 on prod: 0 evicted archive items, 0 ply-0 items. |
| Leaderboard and Archive have their own empty states | VERIFIED | Archive `ArchiveEmpty`; Leaderboard keeps its own existing states (not changed). |
| New elements have `data-testid`; toggle is URL-routed so no Umami event | VERIFIED | `train-archive-toggle-*`, `tab-train-*`, `btn-train-puzzle-analyze`, `train-rank-line` and others present; `nav-click` for the rank line goes through `trackFeature` with a registered `NAV_SOURCES` value; no `tab-switch` event by design. |
| Analyze ply off by one | VERIFIED | Shared `buildTrainPuzzleAnalysisUrl(gameId, ply)` passes `ply - 1`, now used by both the card and `TrainSolveScreen`. 246-06 step 4 compared the Analysis board square by square with the card FEN: equal (card ply 109, URL ply 108). |
| "No migration" unproven | VERIFIED (on recorded prod evidence) | Prod P1 to P6 were run during execution (246-RESEARCH.md): 19,493 `drill_solves` rows, 3.6 ms with a seq scan for the largest list (user 28), well under the 300k rows / 50 ms migration rule. I cannot re-run these (no DB access) and accept them as measured. |

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `app/routers/train.py` `GET /train/archive` | VERIFIED | `list` limited to mastered/parked (ACTIVE cannot be listed), `limit` 1..50, `offset` 0..2^31-1, user id only from `current_active_user`, Sentry capture on failure. |
| `app/repositories/train_repository.py` `get_archive_page` | VERIFIED | Substantive; wired from the router; rows and total from one function. |
| `app/schemas/train.py` `TrainArchiveItem/Response` | VERIFIED | 14 fields, no spoiler. |
| `frontend/src/lib/trainRoute.ts` | VERIFIED | Exact-match parser, `ARCHIVE_PAGE_MAX` keeps offset in the backend bound. |
| `frontend/src/hooks/useTrainLoop.ts` | VERIFIED | Latch, immersive derivation, deferred re-read; used by `Train.tsx`. |
| `frontend/src/hooks/useTrainArchive.ts` | VERIFIED | List-scoped `placeholderData`, `refetchOnMount: 'always'`; used by `TrainArchiveTab`. |
| `TrainSubnav`, `TrainArchiveTab`, `TrainPuzzleCard` | VERIFIED | All imported and rendered; knip clean per 246-07. |
| `TrainStatsCard` removed | VERIFIED | File gone; no references. |

### Key Links

| From | To | Status |
|------|----|--------|
| `Train.tsx` to `useTrainLoop` | session and engine gated by `todayVisited` | WIRED |
| `TrainArchiveTab` to `useTrainArchive` to `trainApi.getArchive` to `GET /train/archive` | WIRED (246-06 step 1 saw the live call return 200) |
| `TrainPuzzleCard` to `/analysis?game_id=&ply=` | WIRED (step 4) |
| `TrainStreakCard` rank line to `/train/leaderboard` | WIRED |
| `TrainSolveScreen` to shared Analyze helper | WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
|----------|------|--------|-----------|--------|
| `TrainArchiveTab` cards | `data.items` | `drill_items` grouped with `drill_solves`, joined to `games`, PGN replayed for the FEN | Yes (live call returned the seeded rows, step 1/4) | FLOWING |
| Toggle counts | `mastered_count` / `parked_count` | `useTrainProgress` (existing endpoint) | Yes | FLOWING |
| Rank line | `points.viewer.rank` | `useTrainLeaderboard` (existing endpoint) | Yes | FLOWING |

### Behavioral Spot-Checks (run by the verifier)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Archive endpoint and repository | `uv run pytest tests/routers/test_train.py tests/repositories/test_train_repository.py -k archive -q` | 17 passed | PASS |
| Train page, loop hook, route parser, archive tab, card, streak card, start screen | `npx vitest run` on the 8 named files | 8 files, 200 tests passed | PASS |
| Debt markers (`TBD`/`FIXME`/`XXX`) in phase-touched app and frontend files | `/usr/bin/grep -nE` over the diff's files | none | PASS |

I did not re-run the full pre-merge gate; 246-07 records it green (5694 backend, 5931 frontend tests, lint, build, ty, knip).

### Probe Execution

SKIPPED: no probe scripts are declared by this phase.

### Requirements Coverage

The roadmap lists requirements as TBD; the coverage contract is CONTEXT D-01 to D-16, all accounted for in the truths table above. Plan frontmatter `requirements-completed` lists: 246-01 (D-04, D-07, D-08, D-11, D-13, D-14), 246-02 (D-01, D-03, D-06, D-15, D-16), 246-04 (D-05, D-07, D-08), 246-05 (D-01, D-04, D-05, D-06, D-09, D-15, D-16), 246-07 (D-01, D-02, D-04, D-10, D-12), 246-08 (D-03, D-06, D-16), and 246-03 covers D-02, D-10, D-12. Every D-ID appears in at least one plan. No orphaned decisions.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/components/train/TrainPuzzleCard.tsx` | 93 | `/>` on the same line after a run of spaces (IN-01) | Info | Cosmetic only; valid JSX. Still open in the disposition file. |
| `frontend/src/components/train/TrainStartScreen.tsx` | 2-4 | Docstring says `Train.tsx` fetches the session on mount; it is now `useTrainLoop` (IN-02) | Info | Stale comment. Still open. |
| `tests/routers/test_train.py` | n/a | No test for the accepting side of the `offset` bound (WR-02) | Warning | The 422 side is tested; `offset=2147483647` returning 200 with empty items is not, and the frontend's over-range redirect depends on it. Not goal-blocking. |
| `frontend/src/components/train/TrainArchiveTab.tsx` | - | Wrapped `ToggleGroupItem`s lost the joined-border styling (IN-03) | Info | Fixed in UAT, then replaced by compact pills (D-04); owner approved 2026-11-07. |

No stubs, no hollow props, no debt markers.

### Review disposition

WR-01 (no supporting index on `drill_solves`) is `deferred` with a measured reason: prod 19,493 rows, 3.6 ms for the heaviest user, below the 300k / 50 ms rule. I accept that. It does grow with the whole user base, since the scan is global rather than per user, so the 300k revisit trigger recorded in the disposition is worth keeping visible. WR-02, IN-01, IN-02 and IN-03 are still `open`; none of them blocks the goal.

### Human Verification Required

All three items below passed in 246-UAT.md (2026-11-07). IN-03 was checked against the compact pills that replaced the toggle.

1. **D-15 tab position** (see frontmatter). Decide: accept the 6.82px shift as Library-equivalent, or add `scrollbar-gutter: stable`.
2. **IN-03 toggle styling**: visual check of the Mastered/Parked toggle on desktop and 375px.
3. **Draft empty-state copy**: owner review of the two `EMPTY_COPY` strings.

Also noted by the 246-06 walk and not a defect: at 375px the card's right column is about 106px wide, so opponent names and the status line wrap to two lines. The plan deliberately chose one horizontal tree; this is polish for the owner to weigh.

### Gaps Summary

No gaps. The backend endpoint, the tab routing with its Today latch, the archive grid, the rank line, the removed collapsible and the deleted `TrainStatsCard` all exist, are wired, and pass tests I re-ran. The browser walk measured the rest on a live stack. The status is `human_needed` rather than `passed` only because D-15 has a measured deviation on a locked decision and two items (toggle styling, draft copy) need the owner's eyes.

---

_Verified: 2026-11-06_
_Verifier: Claude (gsd-verifier)_

## Changes after this report (owner UAT, 2026-11-06 and 2026-11-07)

Applied by hand on the owner's decisions; the verifier was not re-run. The full pre-merge gate was re-run afterwards.

- **D-04:** full-width joined toggle with one sentence below for the selected list, replacing the explainer popovers. Rows above that mention `InfoPopover` per side describe the earlier version.
- **D-09:** empty lists show the title and the Today link only.
- **D-11:** with no Points rank, or on a query error, the rank line is left out; `See this week's leaderboard` is removed. The D-11 row above describes the earlier version.
- **D-15:** accepted, no CSS added.
- **WR-04 (code review, 2026-11-07):** comment-only change in `TrainStreakCard.tsx`, no behaviour change. Covered digest recomputed by hand; the verifier was not re-run.
