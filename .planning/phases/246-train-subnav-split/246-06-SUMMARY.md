---
phase: 246-train-subnav-split
plan: 06
subsystem: ui
tags: [uat, browser, claude-in-chrome, react-router]
status: complete

requires:
  - phase: 246-train-subnav-split
    provides: "246-01 to 246-05 and 246-08, walked together on the running stack"
provides:
  - "Measured browser evidence for D-02, D-04, D-05, D-06, D-15 and D-16"
affects: [246-07]

actuals:
  tasks: 2
  commits: 0
---

# Phase 246 Plan 06: Browser walk of the Train subnav split

The whole phase works in the running app on desktop and at phone width, with one layout finding on D-15 left for the owner to decide. The evidence gate exits 0, and the walk needed no code changes.

## Findings for the owner

**D-15: the tabs shift 6.82px when a long Archive list brings in a page scrollbar (step 2).** `train-tabs` keeps `top` and `width` on all tabs, but `left` moves from 165.81 to 158.99 on the 25-item Parked list, because this Chrome draws a classic 14px scrollbar there. Today, Leaderboard and the short or empty Archive lists do not scroll at the 1564x1168 test viewport, so they all read 165.81. On a shorter window, Today would scroll too and the difference would shift with it. The research predicted this (Pitfall 3) and Library has the same exposure, so per the plan I added no global CSS. `scrollbar-gutter: stable` would be the fix if you want one.

**Phone cards have a narrow right column (step 3).** At 375px the board is 188px and the right column is 105.82px. Nothing overflows, but opponent names and the `Mastered Oct 27, 2026` status line wrap to two lines. `FlawCard` uses a 132px board on phones; the plan deliberately chose one horizontal tree sized by `useMiniBoardSize(200)`. This is polish, not a defect.

**Draft copy still needs your review.** The Parked empty state reads "Nothing parked" / "Puzzles you keep missing get set aside here so they stop resurfacing." It is marked DRAFT at `EMPTY_COPY` in `TrainArchiveTab.tsx`.

## How each result was measured

- **Step 1:** my first reading was invalid. Vite's module requests fill the browser's 250-entry resource timing buffer, so `train/sessions` entries were silently dropped and read as 0. I re-measured with the extension's network log (0 session requests on a fresh `/train/archive`, 4 other `/api/train` calls) and with the buffer raised to 5000 (1 POST after Today, still 1 after the round trip).
- **Step 3:** `grid-template-columns` gave 2 tracks at desktop and 1 at 375px. Lazy off-screen boards have no squares yet, so I compared each card's board box with its Analyze button instead, on all 20 cards.
- **Step 4:** card ply 109 opens `?game_id=835314&ply=108`. The Analysis board, read square by square, equals the placement of the FEN from `/api/train/archive`, with Kh2 as the arriving move and Black to move. The card's own DOM placement was checked by eye on the screenshot only, because the tool blocked that return value.
- **Step 5:** URL, toggle and page were restored on desktop (browser back) and at 375px (`btn-analysis-back`). Scroll position needed iframes, because page 2's five cards do not scroll at the full 1564x1168 viewport: 542px restored in a 1280x400 iframe and 798px restored in the 375x667 iframe. It was not measured at the top-level window.
- **Step 6:** in addition to the recorded line, the Back out of the loop fired no session POST on Archive and returning to Today fired exactly one re-read. One Back press moves one tab (Archive to Leaderboard to Today), which 246-02 asked this walk to confirm in a real browser.
- **Step 7:** in a guest session, tabs show on Today and on both empty Archive lists, each with a "Go to Today" link and no import button. No console errors appeared during the walk.
- **Step 8:** schedule controls are visible with no click and `btn-train-schedule-toggle` is gone. The QR renders as a 128px SVG. I did not separately record the chunk request Pitfall 8 expects.

## Deviations and dev state

- **Evidence gate run with GNU grep.** In this shell `grep` is a function that runs `ugrep`, which rejects the backreferences in the plan's regex. The gate text is unchanged, and it passes under `PATH=/usr/bin:/bin bash`.
- **Seeded twice.** My first seed used the wrong ply parity and picked the opponent's flaws. Those 25 rows were deleted by exact key before any step ran, and the rows used in the walk are the user's own. The `CLEANUP` line covers the second seed.
- **Left behind in the dev DB:** the walk entered a real dev session for user 28 (session 296, via Start) and created guest users. The seeded `drill_items` rows are all gone, and the owner's browser login was restored.
- **No prod data was touched by the walk.** The separate read-only P1 to P6 checks are recorded in `246-RESEARCH.md`.

## Evidence

```
API | status=200 total=0
STEP 1 | PASS | posts_on_archive=0 posts_after_today=1 posts_after_round_trip=1
STEP 2 | FINDING | today=165.81,64.9,1232.02 leaderboard=165.81,64.9,1232.02 archive_long=158.99,64.9,1232.02 archive_empty=165.81,64.9,1232.02
STEP 3 | PASS | desktop_columns=2 phone_columns=1 board_left_of_analyze=yes right_column_px=105.82 overflow=no
STEP 4 | PASS | card_placement=8/N7/6pk/2p3q1/8/2P2R1P/5P1K/8 analysis_placement=8/N7/6pk/2p3q1/8/2P2R1P/5P1K/8 side=b card_ply=109 url_ply=108
STEP 5 | PASS | url=/train/archive/parked?page=2 toggle=parked page=2 desktop_back=yes phone_back=yes scroll=restored
STEP 6 | PASS | tabs_during_solve=absent back_tabs=present back_solve_screen=absent
STEP 7 | PASS | tabs_guest_today=present tabs_archive_empty=present
STEP 8 | PASS | schedule_controls=visible qr=rendered
CLEANUP | seeded=25 deleted=25 remaining=0
```
