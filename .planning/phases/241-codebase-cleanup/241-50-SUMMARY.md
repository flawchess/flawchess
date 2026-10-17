---
phase: 241-codebase-cleanup
plan: 50
subsystem: frontend-tests
tags: [cleanup, comments, test-titles, vitest, planning-tags]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff"
  - phase: 241-03
    provides: "cleanup.py codemod"
  - phase: 241-04
    provides: "TypeScript, JSX support (fe_support.py), test-title records"
provides:
  - "Page, App, API-client, root, activity and library frontend tests free of planning tags in comments and describe/it/test titles"
affects: [241-67, 241-70]

actuals:
  tokens: 27000
  tasks: 2
  commits: 2
plan_head_before: 6865064dbc2c9f18e0f750ecb8bb1fe7640d99a6
plan_head_after: 244c157dd44b696fcf8f497d9cda24111aa7904b

key-files:
  modified:
    - frontend/src/pages/__tests__/Analysis.test.tsx
    - frontend/src/pages/__tests__/Bots.test.tsx
    - frontend/src/pages/__tests__/Train.solveLoop.test.tsx
    - frontend/src/pages/__tests__/Endgames.filterVisibility.test.tsx
    - frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx
    - frontend/src/pages/__tests__/Home.redirect.test.tsx
    - frontend/src/pages/__tests__/Import.endgameOverviewInvalidation.test.ts
    - frontend/src/pages/__tests__/Import.feedbackAsk.test.tsx
    - frontend/src/pages/__tests__/Import.pasteHandoff.test.tsx
    - frontend/src/pages/__tests__/Import.queuedState.test.tsx
    - frontend/src/pages/__tests__/Import.stateMachine.test.tsx
    - frontend/src/pages/__tests__/Openings.render.test.tsx
    - frontend/src/pages/__tests__/Openings.statsBoard.test.tsx
    - frontend/src/pages/__tests__/Privacy.test.tsx
    - frontend/src/pages/__tests__/Welcome.test.tsx
    - frontend/src/pages/__tests__/Endgames.readinessGate.test.tsx
    - frontend/src/App.test.tsx
    - frontend/src/__tests__/instrument.beforeSend.test.ts
    - frontend/src/__tests__/noEndgameSkillString.test.tsx
    - frontend/src/__tests__/pushServiceWorker.test.ts
    - frontend/src/api/__tests__/client.test.ts
    - frontend/src/api/__tests__/client.unauthorized.test.ts
    - frontend/src/api/__tests__/googleAuth.test.ts
    - frontend/src/pages/library/__tests__/FlawsTab.test.tsx
    - frontend/src/pages/library/__tests__/GamesTab.test.tsx
    - frontend/src/pages/library/__tests__/LibraryPage.reroute.test.tsx

key-decisions:
  - "FLAWCHESS-NN Sentry issue ids that explain a regression (Train.solveLoop, Bots, instrument.beforeSend, Analysis FLAWCHESS-96) stay: they are bug references, not planning tags, and the plan's regex does not treat them as tags. The one title that mixed a Sentry id with SEED-148 (FLAWCHESS-24 / SEED-148 items 3) lost both."
  - "Stale scaffold narration was fixed beside the tags: Analysis.test.tsx header said 'Wave-0 test scaffold, RED in Wave 0' and carried a comment 'intentionally RED in Wave 0'; both removed because the file exists and the tests pass."

requirements-completed: [D-01, D-11, D-12, D-13, D-14, D-15]

completed: 2026-10-16
status: complete
---

# Phase 241 Plan 50: Frontend Page, App and API Test Comment Cleanup Summary

**Planning tags are gone from the comments and describe/it/test titles of 26 frontend test files (139 titles rewritten to say what they check), with identical vitest counts (241 + 175) and no assertion, mock or source-text expectation touched.**

## Performance

- **Tasks:** 2
- **Files modified:** 26 (OAuthCallbackPage.test.tsx and Endgames.readinessGate.test.tsx were scanned; OAuthCallbackPage was already clean and stays untouched, readinessGate only received codemod rewrites)
- **Diff:** 469 insertions, 494 deletions, all comment lines and title literals

## Accomplishments

- First scan listed 401 matches in 27 files (about 330 after the first hand-edit batches); final `scan --gate --scope scopes/241-50.txt` lists 0.
- `cleanup.py codemod` rewrote 100 lines in 21 files; 359 hand edits went through 8 `apply-edits` batches (22, 30, 43, 30, 60, 156, 14, 4 spans) plus 3 one-line `sed` fixes for a leftover provenance phrase and a trailing-space title.
- Beyond the scanner, provenance shapes it cannot see were removed by grep: `V-04`/`V-06`/`B-1`, `190-03:`/`191-05:` title prefixes, `UAT round N`, `G-213-34`, `Task 1`, `Plan 01`, `Wave 0`, `Pitfall N`, `RESEARCH`, `163-REVIEW`, `(post-UAT)`, `(found by code review, WR-01)`.
- Where a tag stood in for a decision, the decision replaced it (Analysis sweep-demotion block rewritten as the rule: the stored-best-move gate keeps the sweep disabled for analyzed games, with the invariants covered in gemSweep.test.ts and useGemSweep.test.ts).

## Task Commits

1. **Task 1: pages/__tests__ (16 files)** - `dd1e6f22b` (`chore(comments): frontend page tests`)
2. **Task 2: App, root, API, activity and library tests (10 files with edits, 11 in scope)** - `244c157dd` (`chore(comments): frontend App, root and API tests`)

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-50.txt` | exit 0 (28 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-50.txt` | exit 0 (28 selected, 26 changed, no residue; title collisions: none) |
| `cleanup.py scan --gate frontend/src/pages/__tests__` / `diff frontend/src/pages/__tests__` | exit 0 / exit 0 |
| `npm --prefix frontend test -- src/pages/__tests__` | 17 files, 241 passed (before: 241) |
| `npm --prefix frontend test -- src/App.test src/__tests__ src/api/__tests__ src/pages/activity src/pages/library` | 11 files, 175 passed (before: 175) |
| `npm --prefix frontend run lint` | clean (baseline also clean) |
| `source_scan_tests.sh --fe` | 9 files, 131 tests passed |
| `source_scan_tests.sh` python half, run serially (no `-n 4`; first pytest command, 95 passed) | 95 passed |

Environmental note: the Python half was run serially without xdist, per the parallel-execution rule (shared dev Postgres). Only the first of its two pytest commands was run; the second (`-k` filtered library/insights/stats tests) is not affected by frontend test files, which no Python test reads.

## Rewritten test titles (old to new, D-14)

Most rewrites only drop a trailing or leading tag. All 139, as `file | old | new`:

| File | Old | New |
|---|---|---|
| App.test.tsx | `nav lock state: $name — /analysis (Phase 208)` | `nav lock state: $name — /analysis` |
| App.test.tsx | `mobile bottom bar (MobileBottomBar): renders NO analysis entry (D-09)` | `mobile bottom bar (MobileBottomBar): renders NO analysis entry` |
| App.test.tsx | `V-04: Bots renders in all three surfaces, second position (D-16)` | `Bots renders in all three surfaces, second position` |
| App.test.tsx | `190-03: Train renders in all three surfaces, correctly placed (NAV-01)` | `Train renders in all three surfaces, correctly placed` |
| App.test.tsx | `desktop and bottom-bar nav sequences agree everywhere EXCEPT /analysis (Phase 208, D-09)` | `desktop and bottom-bar nav sequences agree everywhere EXCEPT /analysis` |
| App.test.tsx | `190-03: Train gating (NAV-02)` | `Train gating` |
| App.test.tsx | `locked state: Train is exempt (Phase 224 D-01) on all three surfaces; Openings/Endgames stay locked` | `locked state: Train is exempt on all three surfaces; Openings/Endgames stay locked` |
| App.test.tsx | `190-03: empty profile does not crash and renders Train exempt` | `empty profile does not crash and renders Train exempt` |
| App.test.tsx | `all three surfaces render without throwing, Train exempt (Phase 224 D-01), with a null profile` | `all three surfaces render without throwing, Train exempt, with a null profile` |
| App.test.tsx | `190-03: Train active state (adjacency)` | `Train active state (adjacency)` |
| App.test.tsx | `190-03: mobile bottom-bar target count` | `mobile bottom-bar target count` |
| App.test.tsx | `191-05: Train waiting badge (SCHD-02/D-06..D-08)` | `Train waiting badge` |
| App.test.tsx | `waiting_count: 12, badge_visible: false -> badge absent on both surfaces (D-09 off-day)` | `waiting_count: 12, badge_visible: false -> badge absent on both surfaces (off-day)` |
| App.test.tsx | `V-06: /bots active state + mobile header title` | `/bots active state + mobile header title` |
| App.test.tsx | `Quick 260809-g0n: MobileBottomBar swaps main nav for board controls` | `MobileBottomBar swaps main nav for board controls` |
| App.test.tsx | `Phase 223 (BOTVOICE-05): MobileBottomBar swaps to the bot four-action bar` | `MobileBottomBar swaps to the bot four-action bar` |
| App.test.tsx | `Phase 237 plan 07: MobileBottomBar swaps to the Train reveal bar` | `MobileBottomBar swaps to the Train reveal bar` |
| App.test.tsx | `Quick 260824-qaz: /activity nav entry (superuser-only)` | `/activity nav entry (superuser-only)` |
| App.test.tsx | `228 settings overlay entry (D-01..D-03)` | `settings overlay entry` |
| App.test.tsx | `more drawer: ... is not a drawer-nav entry (D-02)` | `more drawer: ... is not a drawer-nav entry` |
| App.test.tsx | `mobile /analysis header: cogwheel opens the sheet in place without navigating (D-03)` | `mobile /analysis header: cogwheel opens the sheet in place without navigating` |
| App.test.tsx | `229 nav and drawer tracking` | `nav and drawer tracking` |
| App.test.tsx | `MobileMoreDrawer: superuser Admin and Activity items never send nav-click (D-14)` | `MobileMoreDrawer: superuser Admin and Activity items never send nav-click` |
| instrument.beforeSend.test.ts | `sentryBeforeSend page-URL query scrub (Phase 232 review WR-01)` | `sentryBeforeSend page-URL query scrub` |
| instrument.beforeSend.test.ts | `scrubs the query string from navigation breadcrumb from/to (gap G-232-3)` | `scrubs the query string from navigation breadcrumb from/to` |
| instrument.beforeSend.test.ts | `Sentry.init config (FLAWCHESS-24 / SEED-148 items 3)` | `Sentry.init config` |
| instrument.beforeSend.test.ts | `keeps the v10 privacy baseline under Sentry v11 (dataCollection + attachStacktrace, D-02)` | `keeps the v10 privacy baseline under Sentry v11 (dataCollection + attachStacktrace)` |
| noEndgameSkillString.test.tsx | `SC#1 (Phase 87.5) — no "Conversion ELO" string in rendered Endgames surfaces` | `no "Conversion ELO" string in rendered Endgames surfaces` |
| client.test.ts | `has_gem / has_great (FILT-01, Phase 175)` | `has_gem / has_great` |
| Analysis.test.tsx | `renders shell with required testids (ROUTE-01)` | `renders shell with required testids` |
| Analysis.test.tsx | `seeds a free-play opening main line from a valid ?line= param (ROUTE-02)` | `seeds a free-play opening main line from a valid ?line= param` |
| Analysis.test.tsx | `shows engine-loading chrome while isReady=false, board stays present (D-06 / SC#3)` | `shows engine-loading chrome while isReady=false, board stays present` |
| Analysis.test.tsx | `hides the engine-loading chrome when isReady=true (D-06)` | `hides the engine-loading chrome when isReady=true` |
| Analysis.test.tsx | `shows the standalone Stockfish top lines ... not a merged placeholder (155 UAT un-merge)` | `... not a merged placeholder` |
| Analysis.test.tsx | `Analysis page: persisted engine switches (quick 261004-nxn)` | `Analysis page: persisted engine switches` |
| Analysis.test.tsx | `Analysis page: engine readiness gate (G-213-34)` | `Analysis page: engine readiness gate` |
| Analysis.test.tsx | `cold cache mounts the gate, with no Start button of any kind (D-18: analysis auto-closes, never a click)` | `cold cache mounts the gate, with no Start button of any kind (analysis auto-closes, never a click)` |
| Analysis.test.tsx | `D-18: marking all three assets ready closes the gate on its own — no click, no button, ever present` | `marking all three assets ready closes the gate on its own — no click, no button, ever present` |
| Analysis.test.tsx | `Maia eval bar perspective (151.1 UAT regression)` | `Maia eval bar perspective` |
| Analysis.test.tsx | `FlawChess Engine card header node count (quick 260906-i5e)` | `FlawChess Engine card header node count` |
| Analysis.test.tsx | `FlawChess Engine eval-bar precedence (Phase 155)` | `FlawChess Engine eval-bar precedence` |
| Analysis.test.tsx | `shows the FlawChess eval bar in the left slot when the FlawChess Engine is enabled (DISPLAY-04)` | `... is enabled` |
| Analysis.test.tsx | `falls back to the Maia eval bar in the left slot once the FlawChess Engine is toggled off (DISPLAY-04)` | `... is toggled off` |
| Analysis.test.tsx | `renders the FlawChess card above the Maia panel by default (D-01)` | `renders the FlawChess card above the Maia panel by default` |
| Analysis.test.tsx | `Grading run gating (Phase 158, SEED-087 SC2)` | `Grading run gating` |
| Analysis.test.tsx | `excludes the free run's top-2 root SANs ... once it has committed (Phase 162 D-02/D-09)` | `... once it has committed` |
| Analysis.test.tsx | `Reconciled eval provenance (Phase 158, SEED-087)` | `Reconciled eval provenance` |
| Analysis.test.tsx | `a move graded by both the free run and the grading run displays the grading value (Phase 162 D-01 grading-first precedence)` | `... (grading-first precedence)` |
| Analysis.test.tsx | `mirror-image label case: ... the free-run bestSan is demoted (Phase 162 D-03)` | `... the free-run bestSan is demoted` |
| Analysis.test.tsx | `the verdict's FC-pick and SF-best evals both resolve through evalLookup, ... never leaks through (SC4)` | `... never leaks through` |
| Analysis.test.tsx | `shows the grading (reconciled) value for the verdict's Stockfish side ... two sources (Phase 162 D-13 provenance)` | `... two sources` |
| Analysis.test.tsx | `the Stockfish card's line 1 IS the reconciled global argmax ... never searched that move (162 UAT card re-source, supersedes D-12's accepted edge case)` | `... never searched that move` |
| Analysis.test.tsx | `the sf-0 board arrow follows the reconciled-argmax square ... is the global argmax (D-12)` | `... is the global argmax` |
| Analysis.test.tsx | `Settings drive search breadth, grading union and arrows (Phase 228, D-12/D-14/D-15)` | `Settings drive search breadth, grading union and arrows` |
| Analysis.test.tsx | `Analysis desktop layout (Phase 161, SEED-088)` | `Analysis desktop layout` |
| Analysis.test.tsx | `renders the MoveStats section in the right column ... below the eval chart (UAT 179)` | `... below the eval chart` |
| Analysis.test.tsx | `carries the desk3col 3-column grid-cols class on the grid row (D-03)` | `carries the desk3col 3-column grid-cols class on the grid row` |
| Analysis.test.tsx | `Board auto-orientation (171 UAT gap 1)` | `Board auto-orientation` |
| Analysis.test.tsx | `Gem moves (Phase 163, SEED-092)` | `Gem moves` |
| Analysis.test.tsx | `classifies a freely-played WHITE move as a gem, painting the violet board marker (D-04 white, D-05 free node, squareMarkers assembly)` | `... (white move, free node, squareMarkers assembly)` |
| Analysis.test.tsx | `LOAD-BEARING (T-219-13, Phase 219-03 D-12): an 11-rung coarse curve ...` | `LOAD-BEARING: an 11-rung coarse curve ...` |
| Analysis.test.tsx | `classifies a freely-played BLACK move as a gem (D-04 both colors)` | `classifies a freely-played BLACK move as a gem (both colors)` |
| Analysis.test.tsx | `classifies a gem on a MAINLINE game node ... (D-05 mainline coverage, unanalyzed-game fallback path)` | `... (mainline coverage, unanalyzed-game fallback path)` |
| Analysis.test.tsx | `Stored gem/great consumption (Phase 175, SEED-108 D-01/D-02b/D-03)` | `Stored gem/great consumption` |
| Analysis.test.tsx | `a mainline ply with best_move_tier=null renders NO marker ... (Pitfall 3 — row-absence is authoritative)` | `... (row-absence is authoritative)` |
| Analysis.test.tsx | `WR-05: a backend severity badge on the same square suppresses the board gem ...` | `a backend severity badge on the same square suppresses the board gem ...` |
| Analysis.test.tsx | `sticky: the move-list gem badge persists after navigating away and back (D-06)` | `sticky: the move-list gem badge persists after navigating away and back` |
| Analysis.test.tsx | `WR-04: an in-flight (still-streaming) grading pass never seeds the gem cache ...` | `an in-flight (still-streaming) grading pass never seeds the gem cache ...` |
| Analysis.test.tsx | `gem resolution is a one-way sticky latch across ELO-slider moves ... once resolved (D-06)` | `... once resolved` |
| Analysis.test.tsx | `SC3 (Phase 172, SEED-106 D-01): the ELO slider does not change an already-resolved gem's stamped rung` | `the ELO slider does not change an already-resolved gem's stamped rung` |
| Analysis.test.tsx | `Book marker on an inaccuracy-severity ply (Quick 260715-als, WR-04)` | `Book marker on an inaccuracy-severity ply` |
| Analysis.test.tsx | `Live-polling analysis board with an in-place pending pill (Quick 260714-rj5)` | `Live-polling analysis board with an in-place pending pill` |
| Analysis.test.tsx | `renders no pill and no Analyze button when active_eval_status is null (unanalyzed, unqueued) — SC4: never dispatches sweep work` | `... — never dispatches sweep work` |
| Analysis.test.tsx | `SC7 (Phase 172, SEED-106 D-03), updated for Phase 175 (SEED-108 D-01a): a bot game opened ...` | `a bot game opened ...` |
| Analysis.test.tsx | `Mobile Stats tab: present during analysis, then the MoveStats panel (quick 260719-dzh)` | `Mobile Stats tab: present during analysis, then the MoveStats panel` |
| Analysis.test.tsx | `Sweep demotion (Phase 175, SEED-108 D-01/D-01a — supersedes Phase 172 CR-02/D-05 dispatch proofs)` | `Sweep demotion` |
| Analysis.test.tsx | `never dispatches a sweep candidate ... a real D-04 candidate exists (supersedes the CR-02 yield-to-cursor wiring proof)` | `... a real candidate exists` |
| Analysis.test.tsx | `the sweep's dedicated instances stay idle ... work normally (supersedes the D-05/SC2 instance-isolation proof)` | `... work normally` |
| Analysis.test.tsx | `Analysis-board Stockfish root injection (Phase 196, INJECT-03/04/06)` | `Analysis-board Stockfish root injection` |
| Analysis.test.tsx | `stays at the sentinel ... has not committed (INJECT-04)` | `... has not committed` |
| Analysis.test.tsx | `keeps the SAME extraRootMoves reference ... (restart-storm guard, RESEARCH.md Pitfall 1)` | `... (restart-storm guard)` |
| Analysis.test.tsx | `resets to the sentinel on FEN change ... injects again (INJECT-04)` | `... injects again` |
| Analysis.test.tsx | `does NOT commit a spurious latch ... in the new position (WR-01, 196-REVIEW.md)` | `... in the new position` |
| Analysis.test.tsx | `wires the verdict's lookup to the UNSLICED rankedLines ... below the visible top 2 (INJECT-06)` | `... below the visible top 2` |
| Analysis.test.tsx | `Analysis same-page game switch (Phase 208 CR-01)` | `Analysis same-page game switch` |
| Analysis.test.tsx | `reseeds the board when navigating from one game to another (CR-01)` | `reseeds the board when navigating from one game to another` |
| Analysis.test.tsx | `reseeds even when the two games have the same move count (CR-01)` | `reseeds even when the two games have the same move count` |
| Analysis.test.tsx | `Custom-start games in game mode (Phase 210, SEED-042)` | `Custom-start games in game mode` |
| Analysis.test.tsx | `Import-tab paste handoff consume (Quick 260826-qdl)` | `Import-tab paste handoff consume` |
| Bots.test.tsx | `Bots — profile fetch failure (WR-08)` | `Bots — profile fetch failure` |
| Bots.test.tsx | `Bots — setup/resume/new-game convergence (V-11)` | `Bots — setup/resume/new-game convergence` |
| Bots.test.tsx | `renders the persona grid (not SetupScreen) when there is no snapshot (Phase 183, PERS-01)` | `... when there is no snapshot` |
| Bots.test.tsx | `selecting the Custom entry renders the unchanged SetupScreen (Phase 183, PERS-04)` | `selecting the Custom entry renders the unchanged SetupScreen` |
| Bots.test.tsx | `selecting a persona opens the detail surface, ... single handleStart entry (Phase 183, PERS-02)` | `... single handleStart entry` |
| Bots.test.tsx | `discard falls through to setup, clearing only the snapshot key (170 D-05)` | `discard falls through to setup, clearing only the snapshot key` |
| Bots.test.tsx | `new game returns to setup, not an instant restart (D-11)` | `new game returns to setup, not an instant restart` |
| Bots.test.tsx | `Bots — mobile player rows (Phase 223 UAT: same rows as the analysis board)` | `Bots — mobile player rows (same rows as the analysis board)` |
| Bots.test.tsx | `Bots — in-game bubble wiring (Phase 223, BOTVOICE-01/02)` | `Bots — in-game bubble wiring` |
| Bots.test.tsx | `Bots — bot draw-offer actions render inside the bubble (Phase 223, BOTVOICE-05, D-12)` | `Bots — bot draw-offer actions render inside the bubble` |
| Bots.test.tsx | `Bots — mobile chrome removed, back arrow wired (Phase 223, BOTVOICE-05, D-10/D-12/SC7)` | `Bots — mobile chrome removed, back arrow wired` |
| Bots.test.tsx | `Bots — mobile settings sheet (Phase 228 D-04)` | `Bots — mobile settings sheet` |
| Bots.test.tsx | `Bots — desktop layout (Phase 223, BOTVOICE-05, D-11/D-12)` | `Bots — desktop layout` |
| Bots.test.tsx | `renders no settings cogwheel in the desktop layout (D-04: desktop uses the header cogwheel)` | `renders no settings cogwheel in the desktop layout (desktop uses the header cogwheel)` |
| Bots.test.tsx | `Bots — Rematch/New opponent (Phase 183, D-06/D-08)` | `Bots — Rematch/New opponent` |
| Bots.test.tsx | `store on finish (D-21)` | `store on finish` |
| Bots.test.tsx | `POSTs exactly once when outcome transitions null -> finished, with a matching game_uuid (V-14)` | `... with a matching game_uuid` |
| Bots.test.tsx | `finish -> store succeeds -> remount does NOT re-POST (V-15, the double-POST regression)` | `finish -> store succeeds -> remount does NOT re-POST (the double-POST regression)` |
| Bots.test.tsx | `invalidates the persona-wins cache after a successful finish-time store, forcing a refetch (CR-01)` | `... forcing a refetch` |
| Bots.test.tsx | `Analyze CTA carries the played colour (171 UAT gap 1)` | `Analyze CTA carries the played colour` |
| Bots.test.tsx | `Analyze CTA — one-click tier-1 enqueue (Quick 260714-rj5)` | `Analyze CTA — one-click tier-1 enqueue` |
| Bots.test.tsx | `Bot board passes lastMove through to ChessBoard (171 UAT gap 2)` | `Bot board passes lastMove through to ChessBoard` |
| Bots.test.tsx | `BotsGame — bottom-nav clearance (171 UAT gap 3, Task 1)` | `BotsGame — bottom-nav clearance` |
| Endgames.filterVisibility.test.tsx | `Endgames filter visibility (D-02)` | `Endgames filter visibility` |
| Endgames.filterVisibility.test.tsx | `Endgames Games tab data (D-01)` | `Endgames Games tab data` |
| Endgames.filterVisibility.test.tsx | `does not fire the Games-tab stats query while the Stats tab is active (FE-IN-03)` | `... while the Stats tab is active` |
| Endgames.overallPerformance.test.tsx | `defaults to the TC with the most ranked games (D-12)` | `defaults to the TC with the most ranked games` |
| Home.redirect.test.tsx | `HomePage redirect (Phase 224 S-1)` | `HomePage redirect` |
| Home.redirect.test.tsx | `HomePage post-auth return path (quick 260926-9bg)` | `HomePage post-auth return path` |
| Import.endgameOverviewInvalidation.test.ts | `endgameOverview invalidation contract (Phase 94.1-11)` | `endgameOverview invalidation contract` |
| Import.feedbackAsk.test.tsx | `Import page feedback ask (FBASK-07, D-03)` | `Import page feedback ask` |
| Import.pasteHandoff.test.tsx | `Import tab paste entry point (Quick 260826-qdl)` | `Import tab paste entry point` |
| Import.queuedState.test.tsx | `Import page queued state (SURGE-04/D-03)` | `Import page queued state` |
| Openings.statsBoard.test.tsx | `board container has lg:hidden when activeTab is stats (D-03)` | `board container has lg:hidden when activeTab is stats` |
| Openings.statsBoard.test.tsx | `ScoreConfidencePopover trigger (score bullet, 260504-ttq)` | `ScoreConfidencePopover trigger (score bullet)` |
| Openings.statsBoard.test.tsx | `MiniBulletChart score-domain configuration (260504-ttq)` | `MiniBulletChart score-domain configuration` |
| Openings.statsBoard.test.tsx | `Score bullet isUnreliable opacity logic (260504-ttq)` | `Score bullet isUnreliable opacity logic` |
| Openings.statsBoard.test.tsx | `BulletConfidencePopover trigger (eval bullet, 260508-f9o)` | `BulletConfidencePopover trigger (eval bullet)` |
| Openings.statsBoard.test.tsx | `MiniBulletChart eval-domain configuration (260508-f9o)` | `MiniBulletChart eval-domain configuration` |
| Openings.statsBoard.test.tsx | `hasMgEval gate logic (260508-f9o)` | `hasMgEval gate logic` |
| Privacy.test.tsx | `PrivacyPage Train telemetry disclosure (D-09)` | `PrivacyPage Train telemetry disclosure` |
| Train.solveLoop.test.tsx | `resume: clicking "Resume session" ... next unsolved puzzle (190-06 UAT bug repro)` | `... next unsolved puzzle` |
| Train.solveLoop.test.tsx | `a resumed session with server-recorded solved_results ... not a restart from zero (190.1-04 D-04)` | `... not a restart from zero` |
| Train.solveLoop.test.tsx | `REGRESSION (260728-tgc): a completed session ...` | `REGRESSION: a completed session ...` |
| Train.solveLoop.test.tsx | `mounts straight into the cached solved reveal after Analyze -> back, then Next continues the resumed loop (190.1 UAT round 5)` | `... the resumed loop` |
| Welcome.test.tsx | `renders Back before Sign up free in the actions row (UAT round 1: Back left, Sign up right)` | `... (Back left, Sign up right)` |
| FlawsTab.test.tsx | `shows the no-engine-analysis state when no games are analyzed (quick-260610-vru)` | `shows the no-engine-analysis state when no games are analyzed` |
| GamesTab.test.tsx | `D-04: shared flaw filter (no URL sync)` | `shared flaw filter (no URL sync)` |
| GamesTab.test.tsx | `enables the tactic-filter section on the Games tab (Quick 260620-pza)` | `enables the tactic-filter section on the Games tab` |
| LibraryPage.reroute.test.tsx | `LibraryPage landing redirect (260606-hfy regression)` | `LibraryPage landing redirect` |

`...` stands for an unchanged middle part of a long title; the exact before/after strings are in `git diff 6865064db..244c157dd`. No title now collides with a sibling in its describe block (`cleanup.py diff` reports none).

## Comment edits worth noting

- Analysis.test.tsx: header "Wave-0 test scaffold / RED in Wave 0" replaced by "Analysis page tests."; the "Sweep demotion" block (24 lines of Phase 172/175 narration) rewritten as the present-tense rule plus pointers to where the underlying invariants are tested; a stale "intentionally RED in Wave 0" import comment deleted.
- Bots.test.tsx: codemod left `//: the back arrow ...`; fixed by hand (known codemod bug).
- App.test.tsx: `V-04` cross-references became "as in the Bots order test above"; the 6-line "used to assert full equality" narration became a present-tense statement of the deliberate desktop/mobile divergence. The `totalGames` comment (~:182) was left as is (241-63 renames it).
- noEndgameSkillString.test.tsx, pushServiceWorker.test.ts, FlawsTab/GamesTab headers: plan/SC/D-NN references replaced by what the test pins.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `npm --prefix frontend ci` and `uv sync --group maia-inference` (lockfile installs only, no new packages) before the baseline; baseline lint and vitest were green before any edit.

**2. [Rule 1 - Bug] Codemod artifact `//: the back arrow ...` (Bots.test.tsx:769)**
- Found by the planned `^\s*(#|//|\*)\s*[:;,]\s` grep after the codemod; fixed in the next batch.

**3. [Plan note] OAuthCallbackPage.test.tsx is in files_modified but the scan found it clean; it stays untouched, as the plan allows.**

**Total deviations:** 1 blocking environment prep, 1 codemod-artifact fix, 1 plan note. No behavior, assertion, mock factory, source-text expectation or fixture string changed.

## Known Stubs

None.

## Threat Flags

None. Only comments and test-title literals changed; `cleanup.py diff` (token diff against PHASE_BASE with titles normalized) reports no residue, vitest counts are unchanged, and the source-scanning tests pass.

## Self-Check: PASSED

Commits `dd1e6f22b` and `244c157dd` verified as ancestors of HEAD; all 26 modified files present; scan --gate, diff, lint, vitest counts and source-scan tests green on the final tree.
