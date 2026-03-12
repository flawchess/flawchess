---
phase: 04-frontend-and-auth
plan: 03
subsystem: ui
tags: [react, chess.js, react-chessboard, tanstack-query, tailwind, shadcn, typescript, zobrist, oauth, google]

# Dependency graph
requires:
  - phase: 04-frontend-and-auth/04-02
    provides: Axios client, TypeScript API types, Zobrist hash JS port, shadcn/ui scaffold, auth hooks

provides:
  - Interactive chess board (react-chessboard v5 options API) with drag-drop move making + flip toggle + last-move highlight
  - useChessGame hook: Chess.js state, move history, ply navigation, Zobrist hash recomputation, lastMove tracking
  - MoveList component: SAN move pairs, clickable with current-ply highlight, auto-scroll
  - BoardControls: SkipBack/Back/Forward/Flip icon buttons with boundary disabling
  - FilterPanel: "Played as" first, match side toggle, time control chips, rated toggle, recency dropdown — collapsible on mobile
  - useAnalysis TanStack Query mutation for POST /analysis/positions
  - WDLBar: horizontal stacked bar (green/gray/red) with W/D/L counts and percentages
  - GameTable: result badges, paginated game list with external links
  - useImportTrigger + useImportPolling hooks — polling now correctly stops on 'completed'/'failed'
  - ImportModal: Dialog with platform toggle and username, localStorage for returning users
  - ImportProgress: fixed-position toast banners, correct error display, auto-dismiss on completion
  - Dashboard: two-column desktop / stacked mobile layout with all components assembled
  - Google OAuth: backend route (/auth/google/authorize + /auth/google/callback → frontend redirect with JWT)
  - OAuthCallbackPage: reads JWT from URL fragment, stores in localStorage, navigates to dashboard
  - GET /games/count endpoint: returns total imported game count for current user
  - Smart empty states: 0 games → import CTA; filters matched nothing → filter hint
affects: []

# Tech tracking
tech-stack:
  added:
    - httpx-oauth GoogleOAuth2 client (already in deps)
    - oauth_account DB table (new migration)
  patterns:
    - react-chessboard v5 uses options prop API (not direct props) — all board settings passed via options object
    - useChessGame uses useRef for Chess instance (avoids re-render on internal mutations), useState for derived display state
    - Move navigation via replay-from-start: goToMove creates fresh Chess(), replays history[0..ply-1] for correctness
    - Import polling stop condition: refetchInterval returns false when status === 'completed' or 'failed' (not 'done'/'error')
    - Google OAuth SPA flow: /authorize returns JSON with authorization_url; /callback redirects to FRONTEND_URL/auth/callback#token=JWT
    - OAuthCallbackPage reads token from window.location.hash fragment (avoids token appearing in server logs vs query params)

key-files:
  created:
    - frontend/src/hooks/useChessGame.ts
    - frontend/src/components/board/ChessBoard.tsx
    - frontend/src/components/board/MoveList.tsx
    - frontend/src/components/board/BoardControls.tsx
    - frontend/src/hooks/useAnalysis.ts
    - frontend/src/hooks/useImport.ts
    - frontend/src/components/filters/FilterPanel.tsx
    - frontend/src/components/results/WDLBar.tsx
    - frontend/src/components/results/GameTable.tsx
    - frontend/src/components/import/ImportModal.tsx
    - frontend/src/components/import/ImportProgress.tsx
    - frontend/src/pages/OAuthCallbackPage.tsx
    - app/models/oauth_account.py
    - alembic/versions/d809d42c7521_add_oauth_account_table.py
  modified:
    - frontend/src/pages/Dashboard.tsx (full implementation + game count + smart empty states)
    - frontend/src/types/api.ts (fixed ImportStatusResponse fields, corrected status enum)
    - frontend/src/components/auth/LoginForm.tsx (Google SSO button + divider)
    - frontend/src/components/auth/RegisterForm.tsx (Google SSO button + divider)
    - frontend/src/components/ui/input.tsx (autofill dark-theme readability fix)
    - frontend/src/App.tsx (added /auth/callback route)
    - frontend/vite.config.ts (added /games proxy)
    - app/models/user.py (added oauth_accounts relationship)
    - app/users.py (OAuth-aware SQLAlchemyUserDatabase, GoogleOAuth2 client)
    - app/routers/auth.py (Google OAuth routes — custom callback with frontend redirect)
    - app/core/config.py (added FRONTEND_URL, GOOGLE_OAUTH_CLIENT_ID/SECRET already present)
    - app/routers/analysis.py (added GET /games/count endpoint)
    - app/repositories/game_repository.py (added count_games_for_user)
    - alembic/env.py (added OAuthAccount import)

key-decisions:
  - "react-chessboard v5 options API: props are passed as a single options object (not direct JSX attributes)"
  - "useChessGame replay approach: goToMove creates fresh Chess() and replays from start — chess.js has no undo API"
  - "Google OAuth SPA flow: backend /callback redirects to FRONTEND_URL/auth/callback#token=JWT, not returning JSON (browser navigates there)"
  - "ImportJobStatus values: backend uses 'completed'/'failed' not 'done'/'error' — polling was broken until type mismatch fixed"
  - "squareStyles (not customSquareStyles): react-chessboard v5 prop for per-square style overrides"
  - "GET /games/count endpoint: lightweight separate endpoint rather than special-casing analysis with null hash"

patterns-established:
  - "Move list auto-scroll: useRef on active button + scrollIntoView({ block: nearest }) in useEffect watching currentPly"
  - "OAuth SPA pattern: authorize endpoint returns JSON URL, callback endpoint issues JWT and redirects to frontend hash fragment"
  - "Import polling: refetchInterval as function returning false stops polling; correct status values are 'completed'/'failed'"

requirements-completed: [ANL-01]

# Metrics
duration: 45min (including UAT fix pass)
completed: 2026-03-12
---

# Phase 4 Plan 3: Dashboard UI Summary

**Interactive chess board with move navigation, Zobrist-based position analysis (W/D/L), paginated game table, filter panel, game import flow, Google OAuth SSO, board flip, last-move highlighting, and smart empty states — complete Chessalytics dashboard, UAT-verified and fully functional**

## Performance

- **Duration:** ~45 min total (6 min initial + 39 min UAT fixes)
- **Started:** 2026-03-12T09:55:06Z
- **Completed:** 2026-03-12 (after UAT fix pass)
- **Tasks:** 3 of 3 completed
- **Files modified:** 27 total (13 initial + 14 UAT fixes)

## Accomplishments

- Full interactive chess board using react-chessboard v5: drag-drop moves validated by chess.js, move list in SAN with clickable navigation, Back/Forward/Reset/Flip controls, last-move square highlighting
- Complete analysis workflow: FilterPanel (5 filter types, "Played as" first), Analyze button builds Zobrist hash + filters into AnalysisRequest, WDLBar renders win/draw/loss with correct proportions, GameTable with pagination and external game links
- Import flow: ImportModal (platform toggle + username with localStorage persistence), ImportProgress toast banners now correctly stop on completion and display error messages
- Google OAuth SSO: "Sign in/up with Google" button on auth forms → backend /auth/google/authorize → Google → /auth/google/callback → redirect to /auth/callback#token=JWT → frontend stores token and navigates to dashboard
- Smart empty states: 0 games imported → prominent import CTA; games exist but filters matched nothing → actionable filter hint
- Game count shown in dashboard header, updated after import completes

## Task Commits

1. **Task 1: Chess board interaction, move list, navigation, useChessGame hook** - `9ee3d15` (feat)
2. **Task 2: Filter panel, analysis hook, WDL bar, game table, import modal, import polling, Dashboard assembly** - `0e371f9` (feat)
3. **Task 3 UAT fixes:**
   - Google OAuth backend — `9cee537` (feat)
   - Google SSO frontend + input readability + OAuth callback page — `de505d7` (feat)
   - Fix import spinner and error display — `20c6e75` (fix)
   - Board flip, last-move highlight, filter reorder, game count CTA — `ae015d9` (feat)

## Files Created/Modified

### Initial (Tasks 1-2)
- `frontend/src/hooks/useChessGame.ts` - Chess.js state management with lastMove tracking
- `frontend/src/components/board/ChessBoard.tsx` - react-chessboard v5 with flip + square highlight
- `frontend/src/components/board/MoveList.tsx` - SAN move pairs, clickable, auto-scroll
- `frontend/src/components/board/BoardControls.tsx` - Navigation + flip button
- `frontend/src/hooks/useAnalysis.ts` - TanStack useMutation for POST /analysis/positions
- `frontend/src/hooks/useImport.ts` - useImportTrigger + useImportPolling (fixed status values)
- `frontend/src/components/filters/FilterPanel.tsx` - 5 filter controls, "Played as" first
- `frontend/src/components/results/WDLBar.tsx` - Horizontal stacked bar
- `frontend/src/components/results/GameTable.tsx` - Compact table with pagination
- `frontend/src/components/import/ImportModal.tsx` - Dialog with platform + username
- `frontend/src/components/import/ImportProgress.tsx` - Fixed toast banners with error display
- `frontend/src/pages/Dashboard.tsx` - Full layout with game count + smart empty states

### UAT fixes (Task 3)
- `frontend/src/pages/OAuthCallbackPage.tsx` - Reads JWT from URL hash after Google OAuth
- `frontend/src/components/auth/LoginForm.tsx` - Google SSO button
- `frontend/src/components/auth/RegisterForm.tsx` - Google SSO button
- `frontend/src/components/ui/input.tsx` - Autofill dark-theme readability
- `frontend/src/App.tsx` - /auth/callback route
- `frontend/src/types/api.ts` - Fixed ImportStatusResponse (error field, correct status enum)
- `app/models/oauth_account.py` - OAuthAccount model
- `app/models/user.py` - Added oauth_accounts relationship
- `app/users.py` - OAuth-aware UserDatabase + GoogleOAuth2 client
- `app/routers/auth.py` - Custom Google OAuth routes with frontend redirect
- `app/core/config.py` - Added FRONTEND_URL setting
- `app/routers/analysis.py` - GET /games/count endpoint
- `app/repositories/game_repository.py` - count_games_for_user()
- `alembic/env.py` - Added OAuthAccount import
- `alembic/versions/d809d42c7521_add_oauth_account_table.py` - oauth_account migration

## Decisions Made

- **Google OAuth SPA flow**: Custom backend route replaces FastAPI-Users built-in callback. Backend /callback issues JWT and HTTP 302-redirects to `FRONTEND_URL/auth/callback#token=JWT`. Frontend OAuthCallbackPage reads from hash fragment (secure — not logged in URLs).
- **ImportJobStatus mismatch**: Backend uses `'completed'/'failed'` but original TypeScript types had `'done'/'error'`. Root cause of both "spinner never stops" and "error never shows" bugs. Fixed in types/api.ts and all components.
- **GET /games/count**: New lightweight endpoint rather than reusing analysis endpoint with null hash — cleaner API surface, no edge cases.
- **squareStyles (not customSquareStyles)**: react-chessboard v5 uses `squareStyles` as the prop name for per-square CSS overrides. Discovered via TypeScript type inspection.

## Deviations from Plan

### Auto-fixed Issues (Initial Tasks 1-2)

**1. [Rule 1 - Bug] react-chessboard v5 uses options prop API, not flat props**
- **Found during:** Task 1
- **Fix:** `<Chessboard options={{ position, boardStyle, darkSquareStyle, onPieceDrop }} />`
- **Committed in:** 9ee3d15

**2. [Rule 2 - Missing Critical] Added games_fetched to ImportStatusResponse**
- **Found during:** Task 2
- **Fix:** Added `games_fetched: number` to TypeScript type
- **Committed in:** 0e371f9

### UAT Feedback Fixes (Task 3 checkpoint)

**3. [Rule 1 - Bug] ImportJobStatus type mismatch — backend uses 'completed'/'failed' not 'done'/'error'**
- **Found during:** UAT (Issues 4 & 5 — spinner, error display)
- **Issue:** TypeScript ImportJobStatus = `'pending'|'running'|'done'|'error'` but backend JobStatus enum = `PENDING|IN_PROGRESS|COMPLETED|FAILED`
- **Fix:** Updated type, useImportPolling refetchInterval condition, and ImportProgress status checks
- **Files modified:** `frontend/src/types/api.ts`, `frontend/src/hooks/useImport.ts`, `frontend/src/components/import/ImportProgress.tsx`

**4. [Rule 1 - Bug] ImportStatusResponse.error field mismatch — type had 'message' but backend sends 'error'**
- **Found during:** UAT (Issue 4 — error not shown)
- **Fix:** Updated ImportStatusResponse to use `error: string | null` (matching backend schema)
- **Files modified:** `frontend/src/types/api.ts`, `frontend/src/components/import/ImportProgress.tsx`

**5. [Rule 2 - Missing Critical] oauth_account migration autogenerate produced empty pass**
- **Found during:** Task 3 (Google OAuth backend)
- **Issue:** OAuthAccount model not imported in alembic/env.py → autogenerate missed the new table
- **Fix:** Added OAuthAccount import to env.py; rewrote migration with manual DDL; created table directly
- **Files modified:** `alembic/env.py`, `alembic/versions/d809d42c7521_add_oauth_account_table.py`

---

**Total deviations:** 5 (2 bugs, 2 missing critical, 1 missing critical during UAT)
**Impact on plan:** All fixes necessary for correctness. UAT feedback items were user-visible improvements and bug fixes.

## Self-Check: PASSED

All 5 key files found on disk. All 6 commits verified in git log.

---
*Phase: 04-frontend-and-auth*
*Completed: 2026-03-12*
