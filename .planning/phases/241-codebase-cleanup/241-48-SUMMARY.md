---
phase: 241-codebase-cleanup
plan: 48
subsystem: frontend-tests
tags: [cleanup, comments, vitest, hook-tests, test-titles]

requires:
  - phase: 241-04
    provides: "cleanup.py FE support (scan/diff for .ts/.tsx incl. test-title records)"
provides:
  - "47 hook test files under frontend/src/hooks free of planning tags in comments and describe/it titles"
affects: [241-57, 241-58, 241-70]

actuals:
  tokens: 60000
  tasks: 2
  commits: 2
plan_head_before: 7c80f445b033b665489f2cd0d18319346e6e0268
plan_head_after: 210b633fc

key-files:
  modified:
    - frontend/src/hooks/__tests__/ (44 files)
    - frontend/src/hooks/analysis/__tests__/useAnalysisBoardArrows.test.ts
    - frontend/src/hooks/analysis/__tests__/useAnalysisEngineLines.test.ts
    - frontend/src/hooks/useFlawChessEngine.test.tsx

key-decisions:
  - "Sentry issue ids (FLAWCHESS-64, FLAWCHESS-7V, FLAWCHESS-96, FLAWCHESS-9P) are external issue references, not planning tags: kept"
  - "Pipeline 'Phase 1/2/3' labels in useMaiaEngine.test.ts describe the exact/coarse/fill search phases of the engine, not planning phases: kept"
  - "'REVERT PROOF #N (record in SUMMARY)' comments became 'Mutation check: ...' (the revert-and-fail instruction stays, the pointer to a planning artifact goes)"

requirements-completed: [D-01, D-11, D-12, D-13, D-14, D-15]

completed: 2026-10-16
status: complete
---

# Phase 241 Plan 48: Hook Test Comment and Title Cleanup Summary

**All 47 tagged hook test files under frontend/src/hooks now carry no planning tags in comments or describe/it titles; 169 titles were rewritten to state what is checked, with bodies, assertions, option keys and mock factories untouched.**

## Accomplishments

- Scope `scopes/241-48.txt`: 51 files, 419 matching lines at the start (156 of them test titles); `scan --gate` now reports 0 and `diff` reports no residue (51 selected, 47 changed; the 4 clean files stay untouched).
- vitest `src/hooks`: 51 files, **836 tests before and 836 after** (identical in both tasks).
- Gates on the final tree: `eslint .` clean; `source_scan_tests.sh` fe half 9 files / 131 tests passed; py half 95 + 5 passed.
- Hand-edit vs codemod: the codemod rewrote 89 lines (70 in task 1, 19 in task 2); the other ~420 edited lines were hand edits through `apply-edits` batches (318 in task 1, 102 in task 2). Rewritten comments also dropped history narration ("pre-Phase-213-03 behavior" became "ungated behavior", "Plan 10 gap closure adds a test" became a plain statement of what the tests do).

## Task Commits

1. **Task 1: bot-game, Train, engine, Maia and gem-sweep hook tests (22 files)** - `2a29f6e46`
2. **Task 2: analysis, data, filter, auth, push and other hook tests (25 files) + plan gates** - `210b633fc`

## Deviations from Plan

### Environmental (not plan failures)

- **Fresh worktree prep:** `npm --prefix frontend ci` and `uv sync --group maia-inference` (lockfile installs only) before the baseline.
- **Shared Postgres:** the py half of `source_scan_tests.sh` was run serially (same file lists, no `-n 4`) because sibling executors share the dev Postgres. 95 + 5 passed.
- **Sandbox shell restrictions:** commands with `$(...)`, `$VAR` command names, compound git pipelines were refused by the worktree guard, so scope sub-lists live in `temp/241-48/t1.txt` / `t2.txt` (task 1 = the 22 files of Task 1 by the plan's grep, task 2 = the other 29) and were passed with `--scope`. The plan's literal `$(grep ...)` verify command is equivalent. Both task gates were run with `--scope` over those lists and over the full `scopes/241-48.txt`.

### Plan-text adaptations

- **Codemod leftovers:** the codemod left forms such as `Phase 196:`, `Phase 235:`, `FIX-5:` and `Plan 10 gap closure`; all were removed by hand. The scan regex also misses `G-213-*`, `FIX-N`, `Quick 260705`, `UAT round N`, `REVERT PROOF #N`, `Task N`, `Open Question N`, version-free review ids and `NNN UAT`; a broader grep (`temp/241-48/leftover.py`) was run over both scopes and every planning-provenance hit was fixed, after which only the kept items above remain.
- **Spacing artifacts:** removing `Phase NNN: ` from banner lines left double spaces after the box-drawing dashes in 5 files; collapsed (no `──  ` existed at the base).
- **Titles that named a decision:** where a tag was the subject of the sentence it was replaced by the behavior it stood for (`D-04 cooldown` became `draw-offer cooldown`, `D-12 TC` became `most-played TC`, `D-04 TC` became `most-analyzed TC`, `D-03 mechanism 1` became `this warm-up`, `the D-16 think deadline` became `the think deadline`).

No Rule 1-4 deviations; no production file touched; no test body, assertion, `renderHook` option or `vi.mock` factory changed (`cleanup.py diff` exit 0).

## Rewritten test titles (old to new, changed words only; D-14)

Each line names the file and the start of the new title, then lists the changed fragment as `old` to `new` (`∅` = removed).

- useAnalysisBoard.test.ts, "goToRoot: sets currentNodeId to null without…": `(Phase 139)` → `∅`
- useAnalysisBoard.test.ts, "useAnalysisBoard — graftLine": `(Phase 237)` → `∅`
- useBotGame.test.ts, "last-move highlight": `(171 UAT gap 2)` → `∅`
- useBotGame.test.ts, "ticks the bot clock down in real time during…": `(D-15 honest` → `(honest`
- useBotGame.test.ts, "bot clock": `(D-15/D-16/D-18, amended SC1)` → `∅`
- useBotGame.test.ts, "wires the think deadline into deps.search vi…": `D-16` → `∅`; `D-18` → `shared`
- useBotGame.test.ts, "cancel": `(D-17)` → `∅`
- useBotGame.test.ts, "four abort sites stop in-flight Stockfish wo…": `ABORT-02 (Phase 194):` → `∅`
- useBotGame.test.ts, "hidden-tab time": `(D-20/WR-02, amended SC2)` → `∅`
- useBotGame.test.ts, "a bot move committed while the tab is still …": `(WR-02)` → `∅`
- useBotGame.test.ts, "offerDraw() is blocked by the draw-offer coo…": `D-04` → `draw-offer`
- useBotGame.test.ts, "finalize idempotency": `(WR-03)` → `∅`
- useBotGame.test.ts, "the providers warm BEFORE confirmLive() on a…": `D-03 mechanism 1` → `this warm-up`
- useBotGame.test.ts, "bills the user's 40s of in-turn think time i…": `D-01:` → `∅`
- useBotGame.test.ts, "does NOT fold on the bot's turn — both bases…": `D-02:` → `∅`
- useBotGame.test.ts, "a second finalizeGame call (stale draw-accep…": `WR-03:` → `∅`
- useBotGame.test.ts, "styled resign wiring": `(STYLE-02)` → `∅`
- useBotGame.test.ts, "a stale pool.grade() continuation resolving …": `(CR-02)` → `∅`
- useBotGame.test.ts, "bot's own outgoing draw offer": `(D-07)` → `∅`
- useBotGame.test.ts, "a fresh blend-0 mount stays live:false when …": `G-213-19b` → `the gate`
- useBotGame.test.ts, "a fresh blend-0 mount starts live:true immed…": `(D-04, Phase 213-09 adds ort-runtime)` → `(ort-runtime is the third flag)`
- useBotGame.test.ts, "a fresh mount at ANY blend calls pool.warm()…": `(G-213-19b, supersedes D-03/D-06)` → `(no blend-0 skip)`
- useBotGame.test.ts, "retryEngineWarm() calls BOTH queue.warm() an…": `(G-213-19b)` → `∅`
- useBotGameVoice.test.ts, "regret latch": `(Phase 223 UAT)` → `∅`
- useDebouncedTrackFeature.test.ts, "never sends from an excluded route (at the c…": `(D-14 at` → `(at`
- useDevicePushResync.test.ts, "the same happy path never touches requestPer…": `PERM-01:` → `∅`
- useDevicePushResync.test.ts, "useDevicePushResync — fail-safe suppression …": `(D-05/D-08/D-09)` → `∅`
- useDevicePushResync.test.ts, "subscriptionKeyMatches returns false (detect…": `(D-05: detect` → `(detect`
- useDevicePushResync.test.ts, "useDevicePushResync — cadence (at most one a…": `(D-09: at` → `(at`
- useEndgameInsights.test.tsx, "POSTs to /insights/endgame with no query par…": `(filter-free, D-04)` → `(filter-free)`
- useEndgameInsights.test.tsx, "writes a successful Generate result into the…": `(FE-WR-01)` → `∅`
- useEndgameStatsTc.test.ts, "pickDefaultTc": `(D-12)` → `∅`
- useEndgameStatsTc.test.ts, "useEndgameStatsTc": `(D-13, D-14)` → `∅`
- useEndgameStatsTc.test.ts, "defaults to the most-played TC when nothing …": `D-12` → `most-played`
- useEndgameStatsTc.test.ts, "keeps the un-chosen default when a refetch m…": `(FE-IN-05)` → `∅`
- useEngineAssets.test.ts, "does NOT re-render on a byte-only progress r…": `value — G-213-35)` → `value)`
- useEvalCoverage.test.tsx, "does NOT call window.location.reload after a…": `(Phase 96 Constraint 4)` → `∅`
- useFastForward.test.ts, "no stop ahead: with empty stopPlies on a fiv…": `ahead (D-04):` → `ahead:`
- useFlawChessEngine.test.ts, "throttle: first onSnapshot commits near-inst…": `paint, DISPLAY-01)` → `paint)`
- useFlawChessEngine.test.ts, "abort: navigating to a new FEN aborts the pr…": `(DISPLAY-01 / Pitfall 1 regression` → `(regression`
- useFlawChessEngine.test.ts, "threads extraRootMoves into the SearchBudget…": `(INJECT-03)` → `∅`
- useFlawChessEngine.test.ts, "aborts the previous run immediately on a RAP…": `FIX-5:` → `∅`
- useFlawChessEngine.test.ts, "isReady reflects real asset readiness": `D-01:` → `∅`
- useFlawFilterStore.test.ts, "includes the High/full depth range {0, 11}": `(Quick 260621-sm8)` → `∅`
- useFlawFilterStore.test.ts, "includes hasGem = false and hasGreat = false": `(Phase 175, FILT-01)` → `∅`
- useFlawFilterStore.test.ts, "returns true when hasGem is true": `(Phase 175, FILT-01)` → `∅`
- useGameOverlay.test.ts, "suppresses the blue best-move arrow when Sto…": `(155 UAT)` → `∅`
- useGameOverlay.test.ts, "never draws a second-best arrow for enginePv…": `(Phase 228 retired it)` → `(that arrow was retired)`
- useGameOverlay.test.ts, "keeps the crimson allowed-tactic arrow even …": `(155 UAT)` → `∅`
- useGameOverlay.test.ts, "useGameOverlay eval-bar passthrough (off mai…": `line, Phase 162 D-08)` → `line)`
- useGemSweep.test.ts, "LOAD-BEARING (yield-to-cursor invariant): wi…": `(D-05 yield-to-cursor` → `(yield-to-cursor`
- useGemSweep.test.ts, "cheap-tier short-circuit: a candidate whose …": `short-circuit (SC1/D-04):` → `short-circuit:`
- useGemSweep.test.ts, "LOAD-BEARING: an 11-rung coarse result whose…": `LOAD-BEARING (T-219-12, Phase 219-03 D-12):` → `LOAD-BEARING:`
- useGemSweep.test.ts, "pinned rung: two candidates with different p…": `rung (SC3/D-01):` → `rung:`
- useGemSweep.test.ts, "cache bound: resolving more than 256 candida…": `bound (Pitfall 4):` → `bound:`
- useGemSweep.test.ts, "LOAD-BEARING (watchdog): a candidate whose c…": `(CR-03 watchdog):` → `(watchdog):`
- useGemSweep.test.ts, "stored-data-disables-sweep: Analysis.tsx pas…": `D-04` → `∅`; `(Phase 175, SEED-108 D-01)` → `∅`
- useGemSweep.test.ts, "unanalyzed-still-runs: with enabled: true (A…": `(D-01 fallback` → `(fallback`
- useGemSweep.test.ts, "stable-callback: resolveCandidate is a stabl…": `stable-callback (WR-06):` → `stable-callback:`; `CR-03` → `∅`
- useGemSweep.test.ts, "once every candidate is resolved the dedicat…": `WR-02:` → `∅`
- useInstallPrompt.test.ts, "event retention: dismissing keeps the captur…": `retention (INSTALL-04):` → `retention:`
- useInstallPrompt.test.ts, "isStandalone truth table": `(INSTALL-05)` → `∅`
- useInstallPrompt.test.ts, "hides the drawer once attemptCount is at the…": `(D-04)` → `∅`
- useInstallPrompt.test.ts, "shows the drawer when the handoff marker is …": `(D-11)` → `∅`
- useInstallPrompt.test.ts, "a desktop UA yields showAndroidPrompt === fa…": `(D-06)` → `∅`
- useInstallPrompt.test.ts, "cross-instance event sharing (regression)": `(CR-02 regression)` → `(regression)`
- useInstallPrompt.test.ts, "regression: "Not now" must end the handoff o…": `UAT item 3` → `∅`
- useLibrary.test.ts, "buildLibraryParams — has_gem / has_great": `(FILT-01, Phase 175)` → `∅`
- useLibraryStatsTc.test.ts, "pickDefaultLibraryTc": `(D-04)` → `∅`
- useLibraryStatsTc.test.ts, "useLibraryStatsTc": `(D-02, D-05)` → `∅`
- useLibraryStatsTc.test.ts, "defaults to the most-analyzed TC when nothin…": `D-04` → `most-analyzed`
- useLibraryStatsTc.test.ts, "keeps the un-chosen default when a refetch m…": `(FE-IN-05)` → `∅`
- useMaiaEloDefault.test.ts, "resetToDefault snaps back to the default and…": `(164 UAT)` → `∅`
- useMaiaEloDefault.test.ts, "deriveRawDefault / clampToLadderBounds (dire…": `(D-01 direct-call` → `(direct-call`
- useMaiaEloDefault.test.ts, "deriveRawDefault(white) returns white_rating…": `D-01:` → `∅`
- useMaiaEloDefault.test.ts, "the SAME gameData yields DIFFERENT rungs for…": `D-01:` → `∅`
- useMaiaEloDefault.test.ts, "regression: setSelectedElo does NOT perturb …": `D-01` → `∅`
- useMaiaEngine.test.ts, "honors priority: false (e.g. useGemSweep)": `useGemSweep, quick 260729-sod FIX 3)` → `useGemSweep)`
- useMaiaEngine.test.ts, "settled FEN fires analyze with the exact sel…": `first (quick 260906-gu2),` → `first,`; `(Phase 219-03, D-11)` → `∅`
- useMaiaEngine.test.ts, "a selectedElo that IS a ladder rung is exclu…": `D-11` → `∅`
- useMaiaEngine.test.ts, "ladderOnly + an odd-index ladder-value selec…": `(D-11 adjacency` → `(adjacency`
- useMaiaEngine.test.ts, "ladderOnly: true skips the exact-rung phase …": `(D-11, gem` → `(gem`
- useMaiaEngine.test.ts, "the coarse-pass stale-FEN discard applies in…": `(D-11)` → `∅`
- useMaiaEngine.test.ts, "the fill-pass stale-FEN discard applies inde…": `(D-11)` → `∅`
- useMaiaEngine.test.ts, "a FEN with zero legal moves still reaches a …": `(MAIAPERF-06 empty predicate)` → `∅`
- useMaiaEngine.test.ts, "a cache hit for a previously-seen FEN skips …": `(D-13)` → `∅`
- useMaiaEngine.test.ts, "resultFen reports the FEN the held curve bel…": `(163-REVIEW WR-03)` → `∅`
- useOpeningInsights.test.tsx, "POSTs to /insights/openings with color: "all…": `(D-02)` → `∅`
- usePushCapability.test.tsx, "a 404 resolves null / unavailable with no Se…": `D-12` → `∅`
- useReminderResurface.test.ts, "regression: propagates enabled: false down t…": `CR-01` → `∅`
- useReturnToTracking.test.ts, "useReturnToTracking": `(quick 260926-9bg)` → `∅`
- useRevealPreview.test.ts, "useRevealPreview keyed state": `(WR-03)` → `∅`
- useStockfishEngine.test.ts, "unmounting before the shared fetch resolves …": `Phase 213-08:` → `∅`
- useStockfishEngine.test.ts, "stops the superseded search immediately on a…": `FIX-5:` → `∅`
- useStockfishEngine.test.ts, "commits at most one pvLines snapshot per thr…": `FIX-6:` → `∅`
- useStockfishEngine.test.ts, "reports download progress and marks stockfis…": `D-01:` → `∅`
- useStockfishEngine.test.ts, "multiPv option changes": `(D-06, D-12)` → `∅`
- useStockfishEngine.test.ts, "worker.onerror is Sentry-captured and marks …": `CR-01:` → `∅`
- useStockfishGradingEngine.test.ts, "gradeMapFen reports the FEN the displayed gr…": `(163-REVIEW WR-03)` → `∅`
- useStoreBotGame.test.ts, "invalidates the botPersonaWins query cache a…": `(CR-01)` → `∅`
- useStoreBotGame.test.ts, "does NOT invalidate the botPersonaWins query…": `(CR-01)` → `∅`
- useTrainGradingEngine.test.ts, "startGrading called before the Worker report…": `(CR-01)` → `∅`
- useTrainGradingEngine.test.ts, "useTrainGradingEngine — grading contract": `(Task 2)` → `∅`
- useTrainGradingEngine.test.ts, "a trailing lowerbound/upperbound info line n…": `(190.1 UAT round 4)` → `∅`
- useTrainGradingEngine.test.ts, "a drop just under MISTAKE_DROP (inside the i…": `moveTier="inaccuracy" — SEED-119 substantive new coverage: this` → `moveTier="inaccuracy":`; `asserted` → `∅`; `∅` → `was asserted`
- useTrainGradingEngine.test.ts, "useTrainGradingEngine — startGameMoveSearch": `(190.1-01 Task 2)` → `∅`
- useTrainGradingEngine.test.ts, "useTrainGradingEngine — width-1 mount search": `(211-02 Task 1)` → `∅`
- useTrainGradingEngine.test.ts, "the mount search is width 1 and its setoptio…": `(D-05)` → `∅`
- useTrainGradingEngine.test.ts, "a played move that is NOT the top move dispa…": `(211-02)` → `∅`
- useTrainGradingEngine.test.ts, "the retired mount-rank shortcut must not res…": `(211-02 mutation` → `(mutation`
- useTrainGradingEngine.test.ts, "useTrainGradingEngine — consistent evals & d…": `(190.1 UAT round 9, narrowed by 211-02)` → `∅`
- useTrainGradingEngine.test.ts, "startGameMoveSearch resolves a game move tha…": `(211-02 consumer ledger row 4)` → `∅`
- useTrainGradingEngine.test.ts, "useTrainGradingEngine — key-anchored grading": `(Phase 235 D-01/D-08)` → `∅`
- useTrainGradingEngine.test.ts, "a keyed startGrading searches the position A…": `(D-08)` → `∅`
- useTrainGradingEngine.test.ts, "playing the key grades GOOD with no further …": `(D-01)` → `∅`
- useTrainGradingEngine.test.ts, "an off-key move runs ONE after-move search a…": `(D-01/D-09)` → `∅`
- useTrainGradingEngine.test.ts, "keeps the grading budget unchanged: no globa…": `(D-03)` → `∅`
- useTrainGradingEngine.test.ts, "useTrainGradingEngine — anchor fallbacks, te…": `(Phase 235 D-07/D-09)` → `∅`
- useTrainGradingEngine.test.ts, "a mating key is scored without a search, and…": `(T-235-05)` → `∅`
- useTrainGradingEngine.test.ts, "clamp: an off-key move whose after-search re…": `D-09` → `∅`
- useTrainGradingEngine.test.ts, "game move: a game move equal to the key reso…": `D-09` → `∅`
- useTrainGradingEngine.test.ts, "game move: a different game move posts ONE a…": `D-09` → `∅`
- useTrainGradingEngine.test.ts, "useTrainGradingEngine — disagreement re-chec…": `(Phase 235 D-11/D-13/D-16/D-20)` → `∅`
- useTrainGradingEngine.test.ts, "(d) a stalled re-check resolves null after T…": `(D-20)` → `∅`
- useTrainGradingEngine.test.ts, "(d2) a key search that lands AFTER the timeo…": `(WR-01)` → `∅`
- useTrainGradingEngine.test.ts, "useTrainGradingEngine — phone reading": `(Phase 236 D-04/D-05/D-06)` → `∅`
- useTrainGradingEngine.test.ts, "playing the key records a good tier with the…": `(D-05)` → `∅`
- useTrainGradingEngine.test.ts, "an off-key move takes the key pair from the …": `(D-04)` → `∅`
- useTrainGradingEngine.test.ts, "the legacy root anchor records nothing, for …": `(D-06)` → `∅`
- useTrainGradingEngine.test.ts, "useTrainGradingEngine: instant-path serializ…": `(Phase 236 Pitfall 1)` → `∅`
- useTrainGradingEngine.test.ts, "useTrainGradingEngine: onKeyLine": `(Phase 236 D-14)` → `∅`
- useTrainLiveAlternatives.test.ts, "useTrainLiveAlternatives": `(quick 261010-e5l)` → `∅`
- useTrainPuzzleTelemetry.test.ts, "fork: a board move that does not fork leaves…": `fork (D-13):` → `fork:`
- useTrainPuzzleTelemetry.test.ts, "fork: one forking move among non-forking one…": `fork (D-13):` → `fork:`
- useTrainPuzzleTelemetry.test.ts, "closed set: a flush body has exactly the v2 …": `(D-12)` → `∅`
- useTrainPuzzleTelemetry.test.ts, "late phone_grade record": `(Phase 236 D-12)` → `∅`
- useTrainPuzzleTelemetry.test.ts, "a record for a puzzle the user already left …": `(Pitfall 4)` → `∅`
- useTrainRevealTree.test.ts, "seeds nothing and previews nothing while the…": `(T-190-16 / T-237-04 / T-261011-lwy-01)` → `∅`
- useTrainRevealTree.test.ts, "forward at the puzzle position enters the AC…": `(Pitfall 3)` → `∅`
- useTrainRevealTree.test.ts, "useTrainRevealTree user moves": `(D-04, D-13)` → `∅`
- useTrainRevealTree.test.ts, "a root move that matches no chip forks, dese…": `(D-04)` → `∅`
- useTrainRevealTree.test.ts, "goToNode on the node the board is already on…": `(WR-04)` → `∅`
- useTrainRevealTree.test.ts, "applies nothing while inactive and rebuilds …": `(T-237-04)` → `∅`
- useTrainRevealTree.test.ts, "replays at most REVEAL_TREE_SNAPSHOT_MAX_PAT…": `(T-237-05)` → `∅`
- useTrainRevealTree.test.ts, "useTrainRevealTree: root-ply grading reads t…": `(D-06)` → `∅`
- useTrainRevealTree.test.ts, "a served vetted move forked at the ROOT ply …": `SEED-137 case 2:` → `∅`
- useTrainRevealTree.test.ts, "the DEEP best played at the root badges 'bes…": `(D-01 amendment)` → `∅`
- useTrainRevealTree.test.ts, "an OFF-key root move still grades from the e…": `(D-04 residual)` → `∅`
- useTrainRevealTree.test.ts, "rootMinMultiPv widens only the puzzle positi…": `position (quick 261010-e5l):` → `position:`
- useTrainRevealTree.test.ts, "useTrainRevealTree: onUserMove counting": `(Phase 233 D-14, Phase 237 D-13)` → `∅`
- useTrainRevealTree.test.ts, "useTrainRevealTree preview commits survive A…": `(WR-02)` → `∅`
- useTrainRevealTree.test.ts, "useTrainRevealTree commitPreview id bookkeep…": `(WR-01)` → `∅`
- useTrainSession.test.ts, "useTrainSession — sessionSolvedCount": `(190.1-04 D-04)` → `∅`
- useTrainSession.test.ts, "useTrainSession — solvedOutcomes accumulator": `(Phase 222 D-17/D-18)` → `∅`
- useTrainSession.test.ts, "useTrainSession — progress invalidation on e…": `(193 UAT)` → `∅`
- useTrainSettings.test.ts, "useTrainSettings — enabled gate (regression)": `(CR-01 regression)` → `(regression)`
- analysis/useAnalysisBoardArrows.test.ts, "useAnalysisBoardArrows — Stockfish arrows 1.…": `(D-14)` → `∅`
- analysis/useAnalysisBoardArrows.test.ts, "useAnalysisBoardArrows — FlawChess arrows": `(D-15)` → `∅`
- analysis/useAnalysisBoardArrows.test.ts, "useAnalysisBoardArrows — Stockfish arrow gra…": `(quick 261012-a6m)` → `∅`
- analysis/useAnalysisBoardArrows.test.ts, "the move-quality hover replaces the arrows a…": `D-07:` → `∅`
- analysis/useAnalysisBoardArrows.test.ts, "sfArrowCount 0 or the engine off gives no en…": `D-07:` → `∅`
- analysis/useAnalysisBoardArrows.test.ts, "FlawChess arrows get no badge; secondaries f…": `D-01:` → `∅`
- analysis/useAnalysisEngineLines.test.ts, "useAnalysisEngineLines — qualityBySanWithGem": `(Phase 219-03, D-12)` → `∅`
- analysis/useAnalysisEngineLines.test.ts, "LOAD-BEARING: an 11-rung coarse result (isLa…": `LOAD-BEARING (T-219-12):` → `LOAD-BEARING:`
- analysis/useAnalysisEngineLines.test.ts, "a DB-authoritative stored gem/great tier app…": `WR-02 fix (Phase 219 review):` → `∅`; `(Maia-independent, Phase 175)` → `(Maia-independent)`
- analysis/useAnalysisEngineLines.test.ts, "useAnalysisEngineLines — display counts foll…": `(Phase 228, D-16)` → `∅`
- useFlawChessEngine.test.tsx, "useFlawChessEngine — bot-play budget profile": `(D-07/D-09)` → `∅`
- useFlawChessEngine.test.tsx, "FLAWCHESS_BOT_MAX_PLIES matches the locked […": `default, D-07 "keep")` → `default)`
- useFlawChessEngine.test.tsx, "FLAWCHESS_BOT_CONCURRENCY is a pinned positi…": `(D-09 — never` → `(never`

## Known Stubs

None.

## Threat Flags

None. Only comments and test-title strings changed (T-241-66 mitigated: `cleanup.py diff` normalizes title literals only, vitest count 836 = 836, all tests pass).

## Self-Check: PASSED

Commits `2a29f6e46` and `210b633fc` are ancestors of HEAD; `scan --gate` and `diff` exit 0 for `scopes/241-48.txt`; vitest `src/hooks` 836 passed; lint clean.
