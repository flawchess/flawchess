---
slug: openings-games-update-depth
status: fixed
trigger: 'Investigate FLAWCHESS-3Y — React "Maximum update depth exceeded" on /openings/games (Sentry production issue)'
created: 2026-04-27
updated: 2026-04-28
---

# Debug Session: openings-games-update-depth

## Symptoms

<DATA_START>
**Expected behavior:** /openings/games page renders normally — board, pieces, panels work without infinite re-render loop.

**Actual behavior:** Single user hit React fatal error "Maximum update depth exceeded. This can happen when a component repeatedly calls setState inside componentWillUpdate or componentDidUpdate." Caught by the app ErrorBoundary so the user got a fallback UI rather than a blank page, but page is unusable.

**Error message (verbatim):**
```
Error: Maximum update depth exceeded. This can happen when a component repeatedly calls setState inside componentWillUpdate or componentDidUpdate. React limits the number of nested updates to prevent infinite loops.
```

Sentry issue: FLAWCHESS-3Y — https://flawchess.sentry.io/issues/FLAWCHESS-3Y
- First/last seen: 2026-04-27T18:31:45Z (single occurrence)
- Environment: production
- React: 19.2.4
- Browser: Chrome 147 / Windows
- User locale: ru, timezone Europe/Budapest, geo Montenegro
- Mechanism: caught by ErrorBoundary (handled=yes)
- Trace ID: 2a8e7c6f40eb4b08a6660a6de9e42799
- transaction: /openings/games
- url: https://flawchess.com/openings/games
<DATA_END>

## Current Focus

- **hypothesis:** Two react-chessboard 5.x prop-identity issues in `ChessBoard.tsx` (the main board) and `MiniBoard.tsx` (per-game cards on /games) that recreate the `options` object — and the embedded `squareStyles`, `boardStyle`, `squareRenderer`, and inline callback objects — on every render. Combined with `/games` rendering up to 20 GameCards (each containing a LazyMiniBoard → Chessboard) plus the main board and arrows overlay, this creates ~21 chessboards in the React tree on a single tab, making it the page where react-chessboard's internal piece-animation effect can amplify a parent re-render into the 50-update React guard.
- **next_action:** present root-cause options to user.

## Evidence

- timestamp: 2026-04-27 (manual investigation by session-manager — Task tool was unavailable in this agent's tool set, so the gsd-debugger sub-agent could not be spawned; investigation was carried out directly via Read/Bash/Grep)

### Production deploy timing (rules out Phase 71.1)

The Sentry timestamp is `2026-04-27T18:31:45Z`. Production deploys are MANUAL via `bin/deploy.sh` (see CLAUDE.md). GitHub Actions deploy timeline (UTC):
- Deploy at `2026-04-27T12:57:35Z` → SHA `a4542fc` (HEAD before bug occurred)
- Deploy at `2026-04-27T18:46:38Z` → AFTER the Sentry event by ~15 minutes

So the deployed code at the time of the bug was at commit `a4542fc`, which **includes Phase 70 + Phase 71** (5da9a3c) but **NOT Phase 71.1** (6a31423, merged 16:47Z, deployed 18:46Z).

This eliminates the original prime suspect in the prefilled symptoms: Phase 71.1 (subnav layout refactor) was not yet in production. The screenshot commit `5103f35` mentioned there is even later — it ships in a future deploy.

### Two structural identity-instability hot spots in the chessboard usage

1. `frontend/src/components/board/ChessBoard.tsx` (the main interactive board on Openings)
   - The whole `options={{ ... }}` object passed to `<Chessboard>` (lines 280-324) is a **fresh inline object on every render**. It contains:
     - `boardStyle: { width: boardWidth, height: boardWidth, borderRadius: '0.5rem' }` — fresh object
     - `squareStyles` — fresh `{}` rebuilt every render at line 261 (even when both `lastMove` and `selectedSquare` are null)
     - `squareRenderer: ({ piece, square, children }) => ...` — fresh closure
     - `onSquareClick: handleSquareClick` (memoized, OK)
     - `onPieceDrop: ({ sourceSquare, targetSquare }) => { ... onPieceDrop(...) }` — fresh inline closure each render

2. `frontend/src/components/board/MiniBoard.tsx` (used inside every GameCard via LazyMiniBoard)
   - Same anti-pattern: the entire `options={{ ... }}` is a fresh inline object every render, including `boardStyle: { width: size, height: size }`.

react-chessboard 5.x runs internal `useEffect`s keyed on prop identity for piece animation and dnd-kit setup. When all those props are new identities, those effects re-fire on every render. Each effect touches internal context state. When any parent re-render is triggered, all 21 chessboards (1 main + 20 mini) re-render and re-fire effects in the same React commit cycle, which is the worst-case for hitting the 50-update guard.

### Why /games specifically and not /explorer

GameCardList renders 20 `<GameCard>` per page (PAGE_SIZE = 20 in `pages/Openings.tsx:67`). Each GameCard renders a LazyMiniBoard which mounts a full `<Chessboard>` via `react-chessboard` once it scrolls into view (IntersectionObserver, rootMargin 200px — so most of the visible cards mount their boards almost immediately). Plus the main `<ChessBoard>` in the side column. That's ~21 Chessboard instances on /games.

/explorer has the main `<ChessBoard>` plus the `MoveExplorer` (no mini-boards). /stats and /insights have no `<Chessboard>`s in TabsContent (only MinimapPopovers, which open on demand).

The /games page is therefore by far the highest concentration of `react-chessboard` instances, which makes it the most likely place for a parent render-loop to amplify into "50 nested updates."

### What did NOT change to trigger this on 2026-04-27

- `react-chessboard` was not bumped recently (no recent `frontend/package.json` changes).
- LazyMiniBoard + MiniBoard exist before Phase 71 — Phase 71 only extracted LazyMiniBoard from inline-in-GameCard.tsx into its own file (functional no-op). Verified via `git diff 5da9a3c^..5da9a3c -- frontend/src/components/results/GameCard.tsx`.
- `ChessBoard.tsx` (`squareStyles`/options identity issue) has been like this for many phases.

The pre-existing identity instability is the structural footgun, but it apparently sat dormant until 2026-04-27 18:31Z — which is consistent with the issue being **rare and triggered by some combination of**:
1. Specific data (a particular game's result_fen, an opening name with characters that confuse a translation extension, a game count threshold).
2. Browser environment (Russian locale + Chrome 147 on Windows + likely a translation/translation-style extension that mutates DOM text inside React-rendered nodes).
3. Timing (e.g. dnd-kit gesture vs ResizeObserver vs `chess.lastMove` update racing on /games specifically).

The identity instability is necessary but not sufficient — a stable prop identity would not even allow the loop to amplify.

### Other suspected secondary contributors (lower confidence)

- `pages/Openings.tsx:449` — `chartBookmarks` is `bookmarks.filter(...)` without `useMemo`, so it is a new array identity every render. It feeds `timeSeriesRequest` (memoized but with `chartBookmarks` in deps), which is re-created every render, then passed to `useTimeSeries(req)`. TanStack Query uses structural equality for queryKeys, so this does NOT cause refetch loops, but it does mean the query reads happen on every render — extra noise but not a direct loop driver.
- `frontend/src/hooks/useChessGame.ts:142-159` — `replayTo` calls multiple setStates from inside a `setMoveHistory` updater. React allows this in production but it is a footgun under StrictMode and certain transition modes.
- `components/layout/SidebarLayout.tsx:53-68` — `ResizeObserver` writes `container.style.minHeight` directly (DOM, not React state), so it does not feed a render loop on its own.

## Eliminated

- **Phase 71.1 layout refactor (6a31423)** — was not deployed at 18:31Z when the bug fired. The prefilled symptom note mistakenly tied the bug to that PR; the actual deployed code was `a4542fc`. (See "Production deploy timing" above.)
- **Commit 5103f35 ("relocate BoardControls...")** — only modified `frontend/src/pages/Home.tsx`, not Openings. Verified via `git show 5103f35 --stat`. Never reached production before the bug fired.
- **react-chessboard library version bump** — no recent changes to `frontend/package.json` for that dep.
- **TanStack Query refetch loop on `useTimeSeries`** — queryKeys use structural equality, so unstable `req` reference does not refetch in a loop.
- **`useFilterStore` / `useUserFlag` external store loops** — both `setFilters` and `setUserFlag` short-circuit when value is unchanged (`useUserFlag.ts:49`), so external-store subscriptions do not feed a setState→subscribe→setState cycle.

## Resolution

### Root cause (high confidence on structural cause, medium on the specific trigger)

The `/openings/games` page mounts ~21 `react-chessboard` instances simultaneously (1 main board + up to 20 LazyMiniBoards in GameCards). Both `ChessBoard.tsx` and `MiniBoard.tsx` recreate the entire `options={{ ... }}` object — including nested `boardStyle`, `squareStyles`, and inline closures (`squareRenderer`, `onPieceDrop` wrappers) — on every render. react-chessboard 5.x runs internal effects keyed on those prop identities, so any parent re-render makes all 21 chessboards re-fire their effects in the same commit. Under a specific combination of user environment (Russian locale + Chrome 147 / Windows, very likely with a page-translation extension that mutates DOM nodes inside React-rendered text) and data, this amplifies into React's 50-nested-updates guard, throwing "Maximum update depth exceeded".

Why this fired only once on a single user: the prop-identity instability is necessary but not sufficient. A stable prop identity (the canonical fix) would not even allow the loop to amplify, regardless of extension/locale.

### Suggested fix direction (find_and_fix)

Stabilize the `options` object identity passed to `<Chessboard>` in both files:

1. `frontend/src/components/board/MiniBoard.tsx` — wrap the `options` object in `useMemo` keyed on `[fen, size, flipped]`. This is the bigger amplifier (×20 instances on /games).

2. `frontend/src/components/board/ChessBoard.tsx`:
   - Wrap `squareStyles` in `useMemo` keyed on `[lastMove, selectedSquare]`.
   - Move `boardStyle` into a `useMemo` keyed on `boardWidth`.
   - Wrap `squareRenderer` in `useCallback` keyed on `[squareStyles, handleSquareClick]`.
   - Wrap the inner `onPieceDrop` adapter in `useCallback` keyed on `[onPieceDrop]`.
   - Wrap the whole `options` in `useMemo` once the inner pieces are stable.

3. (Lower-priority cleanup, not part of this bug fix) `pages/Openings.tsx:449` — wrap `chartBookmarks` in `useMemo`.

Verification: TDD is not possible here without reproducing the loop, which depends on an external trigger. Recommended verification:
- Add a `useMemo`/`useCallback` stabilization, then load `/openings/games` with at least 20 GameCards and confirm React DevTools shows the Chessboard subtree skipping renders when only an unrelated state (e.g. hovering an arrow) changes.
- Frontend lint/typecheck/tests must remain green: `npm run lint && npx tsc --noEmit && npm test`.
- Smoke test: load /openings/games as a logged-in user with games, scroll through pagination, switch between explorer/games tabs — no error toast, no console "Maximum update depth" warning.

### Specialist hint

`react` (TypeScript) — typescript-expert review recommended for the memoization patches before merge.

### Fix applied (2026-04-28)

Memoization patches landed (uncommitted on `main`, awaiting user review):

- `frontend/src/components/board/MiniBoard.tsx` — `options` wrapped in `useMemo([fen, flipped, size])`. Removes the ×20 amplifier on `/openings/games`.
- `frontend/src/components/board/ChessBoard.tsx` — `squareStyles`, `boardStyle`, `showAnimations`, `squareRenderer` (typed via `Parameters<typeof Chessboard>[0]['options']['squareRenderer']`), the inner `onPieceDrop` adapter, and the top-level `options` are all memoized. `lastMove` is destructured into primitive `from`/`to` deps so a fresh-but-equal `{from, to}` object from the parent doesn't re-fire the memos.
- `frontend/src/pages/Openings.tsx:449` — `chartBookmarks` wrapped in `useMemo([bookmarks, chartEnabledMap])`.

Gates verified:
- `npm run lint` — 0 errors (3 pre-existing warnings in `coverage/` artifacts, unrelated).
- `npm run build` — clean (TypeScript via Vite/`tsc` build pipeline, all 2985 modules transformed).
- `npm test` — 152/152 passing.

Cannot deterministically reproduce the original Sentry trigger (it required an external DOM-mutating browser environment), so verification is structural: with stable prop identities, react-chessboard 5.x's internal animation/dnd effects no longer re-fire on parent re-renders that don't change board state, so even if the same external trigger recurs, the cascade can't reach React's 50-update guard.

Recommended manual smoke before merge: load `/openings/games` as a user with ≥20 imported games, page through the GameCard list, switch between explorer/games tabs, and confirm no "Maximum update depth" in console.
