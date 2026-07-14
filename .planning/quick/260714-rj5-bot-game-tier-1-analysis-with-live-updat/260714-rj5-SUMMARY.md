---
phase: 260714-rj5
plan: 01
subsystem: ui
tags: [react, tanstack-query, fastapi, sqlalchemy, bot-play, library, analysis]

requires:
  - phase: 171
    provides: Bots page result surfaces (GameResultDialog/GameResultStrip) and the finish-time useStoreBotGame() POST
  - phase: 167
    provides: POST /bots/games store-on-finish endpoint
provides:
  - Unanalyzed single-game library cards carry their move list and phase_transitions (was always None)
  - Live-polling /analysis?game_id= board with an in-place Pending…/Analyzing… pill, no remount on completion
  - One-click "Analyze this game" from a finished bot game: store confirms -> tier-1 enqueue -> /analysis?game_id=X
affects: [library, analysis, bots]

tech-stack:
  added: []
  patterns:
    - "Opt-in live polling via a pure poll-interval decision function (libraryGamePollInterval) + a stall-backstop constant, mirroring GamesTab's ANALYZE_INFLIGHT_TIMEOUT_MS precedent"
    - "Mutate-time mutation variant (useTier1EnqueueForGame) alongside a hook-construction-time variant (useTier1Enqueue) sharing one request/invalidation helper, for a caller whose id only exists after an earlier async step"

key-files:
  created:
    - frontend/src/components/library/AnalysisPendingPill.tsx
  modified:
    - app/services/library_service.py
    - app/repositories/library_repository.py
    - tests/services/test_library_service.py
    - frontend/src/components/library/NoAnalysisState.tsx
    - frontend/src/hooks/useLibrary.ts
    - frontend/src/hooks/useEnqueueGame.ts
    - frontend/src/pages/Analysis.tsx
    - frontend/src/pages/Bots.tsx
    - frontend/src/components/bots/GameResultDialog.tsx
    - frontend/src/components/bots/GameResultStrip.tsx

key-decisions:
  - "get_library_game always fetches positions now (fetch_page_eval_positions renamed analyzed_game_ids -> game_ids, no analyzed-ness predicate of its own); get_library_games keeps its analyzed-only positions scope unchanged (payload-blowup guard)"
  - "_derive_phase_transitions extracted as the single derivation both _build_eval_series and the unanalyzed _build_card branch call, replacing the old inline middlegame_ply/endgame_ply tracking"
  - "evalChartReady now means 'the EVAL DATA is ready', not 'the game is ready' — an unanalyzed game-mode card carries moves+phase_transitions but null eval_series/flaw_markers, so the move list/board render immediately while the eval chart waits"
  - "Collapsed the mobile tab-strip's two near-identical Tabs branches into one, with the Tags trigger/content conditional on evalChartReady — nets negative LOC and structurally guarantees the Tabs subtree never remounts across the unanalyzed-to-analyzed transition"
  - "Bots.tsx Analyze CTA uses onSettled (not onSuccess) for the tier-1 enqueue — an enqueue failure still opens the game-mode board rather than stranding the user on the result screen"

patterns-established:
  - "Pending…/Analyzing… pill extracted to a standalone AnalysisPendingPill component, reused by both the library card (NoAnalysisState) and the Analysis page's eval-chart slot"

requirements-completed: [QUICK-260714-RJ5]

coverage:
  - id: D1
    description: "Backend: unanalyzed single-game cards carry moves + phase_transitions; eval_series/flaw_markers stay null; the LIST endpoint's positions fetch stays scoped to the analyzed subset"
    requirement: QUICK-260714-RJ5
    verification:
      - kind: unit
        ref: "tests/services/test_library_service.py::TestGetLibraryGame::test_unanalyzed_game_with_positions_carries_moves_and_phase_transitions"
        status: pass
      - kind: unit
        ref: "tests/services/test_library_service.py::TestGetLibraryGame::test_unanalyzed_game_with_no_positions_has_none_moves"
        status: pass
      - kind: unit
        ref: "tests/services/test_library_service.py::TestGetLibraryGame::test_analyzed_game_moves_and_eval_series_unchanged"
        status: pass
      - kind: unit
        ref: "tests/services/test_library_service.py::TestNoEngineAnalysis::test_chesscom_game_card_is_no_engine_analysis"
        status: pass
    human_judgment: false
  - id: D2
    description: "/analysis?game_id=X for an unanalyzed game renders the move list, a navigable board, and the Pending…/Analyzing… pill in place of the eval chart"
    requirement: QUICK-260714-RJ5
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#Live-polling analysis board with an in-place pending pill (Quick 260714-rj5)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Analysis lands via poll -> eval chart/flaw icons/tactic badges appear with NO remount; loadMainLine fires exactly once and a user-built variation survives"
    requirement: QUICK-260714-RJ5
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Analysis.test.tsx#when the card flips from unanalyzed to analyzed with an IDENTICAL moves array, loadMainLine does not re-fire"
        status: pass
    human_judgment: false
  - id: D4
    description: "Bot game -> one click on Analyze enqueues tier-1 and opens game mode; button store-gated with a spinner; store failure falls back to ?line="
    requirement: QUICK-260714-RJ5
    verification:
      - kind: unit
        ref: "frontend/src/pages/__tests__/Bots.test.tsx#Analyze CTA — one-click tier-1 enqueue (Quick 260714-rj5)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/GameResultDialog.test.tsx#GameResultDialog — Analyze is store-gated (Quick 260714-rj5, retires V-17)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/bots/__tests__/GameResultStrip.test.tsx#GameResultStrip — Analyze is store-gated (Quick 260714-rj5, retires V-17)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Manual UAT: play a bot game to finish, click Analyze once, watch the pill turn into the eval chart in place while stepping through a sideline"
    verification: []
    human_judgment: true
    rationale: "Requires a live dev server, a real tier-1 eval job completing, and visual confirmation of the in-place transition — not reproducible in a unit test harness."

duration: 40min
completed: 2026-07-14
status: complete
---

# Quick 260714-rj5: Bot Game Tier-1 Analysis with Live Updates Summary

**One-click Analyze from a finished bot game now enqueues a tier-1 eval job and opens `/analysis?game_id=X` with a live-polling board that swaps its Pending…/Analyzing… pill for the real eval chart in place once analysis lands — no navigation, no remount, cursor and variations survive.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 3
- **Files modified:** 11 (1 created)

## Accomplishments
- Backend: `get_library_game` (single-game path) always fetches positions now, so an unanalyzed game's card carries `moves` + `phase_transitions` (derived from `game_positions.move_san`/`phase`, independent of evals) while `eval_series`/`flaw_markers` correctly stay null. The list endpoint (`get_library_games`) is untouched — its positions fetch stays scoped to the analyzed subset.
- Frontend: `useLibraryGame(gameId, { live: true })` opt-in polling (`libraryGamePollInterval`, `LIBRARY_GAME_POLL_TIMEOUT_MS` stall backstop) drives the Analysis page's game-mode card. A new `AnalysisPendingPill` component (extracted from `NoAnalysisState`) renders in the eval chart's slot while a job is pending/leased. The mobile tab strip's two near-duplicate `Tabs` branches were collapsed into one, which both de-dupes ~40 lines and structurally guarantees the `Tabs` subtree never remounts across the unanalyzed→analyzed transition.
- Bots page: `useTier1EnqueueForGame()` (a mutate-time variant of `useTier1Enqueue`) lets the Analyze CTA enqueue tier-1 analysis for a game id that only exists after the finish-time store POST resolves. The button is disabled with a spinner (`analyzeBusy`) until the store settles; a store failure falls back to the free-play `?line=` URL; a tier-1 enqueue failure still opens the game-mode board via `onSettled`.

## Task Commits

1. **Task 1: Backend — unanalyzed single-game cards carry their move list** - `d63fb5e4` (feat)
2. **Task 2: Frontend — live-polling analysis board with an in-place pending pill** - `90cb8a18` (feat)
3. **Task 3: Bots — one-click Analyze enqueues tier-1 and opens game mode** - `1f27190c` (feat)

**Post-task gate fix:** `df017086` (style: ruff format from the full pre-merge gate run)

**Plan metadata:** pre-dispatch plan committed as `3aa299da`; this SUMMARY + STATE/ROADMAP updates committed separately by the orchestrator per the docs-commit convention.

## Files Created/Modified
- `app/services/library_service.py` - `_derive_phase_transitions` extracted; unanalyzed `_build_card` branch populates `moves`/`phase_transitions` from positions
- `app/repositories/library_repository.py` - `fetch_page_eval_positions` param renamed `analyzed_game_ids` -> `game_ids`, docstring corrected (no analyzed-ness predicate)
- `tests/services/test_library_service.py` - 4 new tests covering unanalyzed-with-positions, unanalyzed-no-positions, analyzed-unchanged, and the LIST endpoint's unaffected guard; `_seed_db_pos` gained a `move_san` param
- `frontend/src/components/library/AnalysisPendingPill.tsx` - NEW: extracted pill component (verbatim markup from `NoAnalysisState`)
- `frontend/src/components/library/NoAnalysisState.tsx` - renders `AnalysisPendingPill` instead of inline pill markup
- `frontend/src/hooks/useLibrary.ts` - `LIBRARY_GAME_POLL_TIMEOUT_MS`, `libraryGamePollInterval`, `useLibraryGame`'s new `live` option
- `frontend/src/hooks/useEnqueueGame.ts` - `useTier1EnqueueForGame` added; shared request/invalidation helper factored out of both hooks
- `frontend/src/pages/Analysis.tsx` - `live: true` on `useLibraryGame`; `evalPending` gate; `evalChart()` now returns the pill while pending; mobile tab strip collapsed to one `Tabs`
- `frontend/src/pages/Bots.tsx` - `enqueueTier1`/`storedGameId`/`analyzeBusy`; rewritten `handleAnalyze`; `analyzeBusy` threaded to both result surfaces
- `frontend/src/components/bots/GameResultDialog.tsx` / `GameResultStrip.tsx` - `analyzeBusy` prop, disabled + `Loader2` spinner on the Analyze button; D-20/D-21 "never gated" comments retired and rewritten

## Decisions Made
- Kept `fetch_page_eval_positions`'s IDOR-scoping (`GamePosition.user_id == user_id`) verbatim while dropping its analyzed-ness gate — the rename to `game_ids` documents that the function was never actually gated on analyzed status, only used that way by convention.
- `evalPending` (new) is deliberately a SIBLING condition to `evalChartReady`, not folded into it — keeps the "what data do I have" and "what should I render" concerns separate at the two call sites (desktop `desktopBoardStage`, mobile `evalTab`).
- `useTier1EnqueueForGame`'s `onSuccess` invalidates `['library-game']` (prefix) in addition to the existing `['imports','eval-coverage']`/`['library-games']` invalidations, so a cached single-game card also refetches once tier-1 is enqueued.

## Deviations from Plan

None — plan executed exactly as written. All four `must_haves.truths` and all six `success_criteria` items are met; the deferred `failed`-eval-job gap was explicitly out of scope per the plan's own `<deferred_items>` section.

## Issues Encountered
- ESLint's `react-hooks/purity` rule flagged the initial `useLibraryGame` implementation for calling `Date.now()` and reading/writing a ref during render (needed for the stall-backstop's start time). Fixed by seeding/resetting the ref inside a `useEffect` instead of inline during render — `refetchInterval` is only invoked by TanStack Query's async scheduler, always after the effect has run, so this is behavior-preserving.
- Two pre-existing `Bots.test.tsx` tests (`Analyze CTA carries the played colour`) started failing after Task 3 because they clicked the Analyze button before the store mutation had settled (now disabled while busy). Fixed by waiting for the button to become enabled before clicking — a legitimate test update, not a Rule-1 bug in the shipped code.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Full pre-merge gate green: `ruff format`/`ruff check`/`ty check`/`pytest -n auto` (3279 passed) on the backend; `lint`/`knip`/`tsc -b`/`vitest` (166 files, 2176 tests) on the frontend.
- Manual UAT (D5 above) is the only remaining verification step — requires a live dev server and a real tier-1 eval job completing to visually confirm the in-place pill-to-chart transition.
- The deferred item from the plan (a `failed` eval job shows no badge/retry path) remains open and out of scope; it needs its own design decision before a future phase picks it up.

---
*Phase: 260714-rj5*
*Completed: 2026-07-14*

## Self-Check: PASSED

All 16 created/modified files verified present on disk. All 4 commits (`d63fb5e4`, `90cb8a18`, `1f27190c`, `df017086`) verified present in git history.
