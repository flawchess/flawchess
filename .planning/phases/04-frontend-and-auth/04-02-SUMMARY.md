---
phase: 04-frontend-and-auth
plan: 02
subsystem: ui
tags: [react, vite, typescript, shadcn, tailwind, axios, react-router, tanstack-query, chess.js, zobrist, bigint]

# Dependency graph
requires:
  - phase: 04-frontend-and-auth/04-01
    provides: FastAPI-Users JWT auth endpoints (POST /auth/register, POST /auth/jwt/login)
provides:
  - Vite+React+TypeScript frontend scaffold at frontend/
  - shadcn/ui with dark theme, all required components installed
  - Axios client with Bearer token interceptor and 401 redirect
  - TypeScript mirrors of all Pydantic backend schemas
  - Auth context (AuthProvider/useAuth) with login/register/logout
  - Login and Register forms with validation and error toasts
  - Auth page with tabbed login/register using shadcn Tabs
  - React Router with ProtectedRoute auth guard redirecting to /login
  - Dashboard placeholder page (Logout + Import Games buttons)
  - Zobrist hash JS port (whiteHash, blackHash, fullHash) using BigInt
  - Backend AnalysisRequest accepts string target_hash via field_validator
affects: [04-03, analysis-ui]

# Tech tracking
tech-stack:
  added:
    - react 19 + react-dom
    - vite 7 + @vitejs/plugin-react
    - typescript 5
    - tailwindcss v4 + @tailwindcss/vite
    - shadcn/ui (Nova preset, Radix library)
    - "@tanstack/react-query 5"
    - react-router-dom 7
    - axios 1.x
    - chess.js 1.x
    - react-chessboard 5.x
    - lucide-react
    - sonner (toast notifications, via shadcn)
    - tw-animate-css, @fontsource-variable/geist (via shadcn)
  patterns:
    - Axios instance in src/api/client.ts with request/response interceptors
    - AuthProvider context pattern with localStorage token persistence
    - ProtectedRoute component wrapping authenticated pages
    - Vite proxy forwarding /auth, /analysis, /imports, /health to localhost:8000
    - BigInt throughout Zobrist computation to avoid IEEE-754 precision loss
    - Hash sent as string in JSON body; backend validator converts str->int

key-files:
  created:
    - frontend/src/api/client.ts
    - frontend/src/types/api.ts
    - frontend/src/hooks/useAuth.ts
    - frontend/src/components/auth/LoginForm.tsx
    - frontend/src/components/auth/RegisterForm.tsx
    - frontend/src/pages/Auth.tsx
    - frontend/src/pages/Dashboard.tsx
    - frontend/src/App.tsx
    - frontend/src/lib/zobrist.ts
    - frontend/vite.config.ts
    - frontend/package.json
    - frontend/components.json
  modified:
    - app/schemas/analysis.py (added field_validator for string target_hash)
    - frontend/index.html (added class="dark", title="Chessalytics")
    - frontend/src/index.css (shadcn/ui CSS variables, Tailwind v4 import)
    - .gitignore (added !frontend/src/lib/ override for Python lib/ pattern)

key-decisions:
  - "Vite proxy for API routing: frontend uses relative URLs (/auth, /analysis, /imports) forwarded to localhost:8000 via Vite server.proxy — no hardcoded backend URL"
  - "shadcn/ui Nova preset with Radix library: dark-theme-only via <html class='dark'> — matches locked design decision from 04-CONTEXT"
  - "BigInt for Zobrist: all hash values use BigInt throughout computeHashes() — no Number() conversion until sending to API"
  - "Hash sent as decimal string in JSON: frontend sends target_hash as string to avoid IEEE-754 precision loss; backend coerce_target_hash validator converts str->int transparently"
  - "fullHash uses ZobristHasher indexing (pivot=1 for white, pivot=0 for black) plus castling/EP/turn — different from whiteHash/blackHash which use _color_hash indexing (pivot=0 for white, pivot=1 for black)"
  - "Turn hash XOR when WHITE to move: chess.polyglot.zobrist_hash XORs index 780 for white's turn (not black's) — JS port matches this"
  - "AuthProvider uses localStorage token without /auth/me validation on mount: 401 interceptor in Axios handles expired tokens lazily"

patterns-established:
  - "Separate hash indexing: whiteHash/blackHash use color-relative pivot (white=0); fullHash uses ZobristHasher absolute pivot (white=1, black=0)"
  - "Auth tab switching via URL search params (?tab=register) for bookmarkable/shareable auth page state"

requirements-completed: [AUTH-01, ANL-01]

# Metrics
duration: 15min
completed: 2026-03-12
---

# Phase 4 Plan 2: Frontend Scaffold and Auth Summary

**Vite+React+TypeScript frontend with shadcn/ui dark theme, JWT auth flow (login/register/guard), Axios client, and BigInt Zobrist hash port matching the Python backend**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-12T09:33:52Z
- **Completed:** 2026-03-12T09:48:51Z
- **Tasks:** 3
- **Files modified:** 20+

## Accomplishments

- Full frontend scaffold: Vite 7, React 19, TypeScript, shadcn/ui (Nova/Radix, dark-only), Tailwind v4
- Working auth flow: login/register forms connected to backend FastAPI-Users endpoints, AuthProvider with token management, ProtectedRoute redirecting unauthenticated users to /login
- Zobrist hash JS port: `computeHashes()` using BigInt produces `whiteHash`, `blackHash`, `fullHash` matching Python backend for all test positions; backend updated to accept string `target_hash`

## Task Commits

1. **Task 1: Vite scaffold, shadcn/ui, API types, Axios client** - `0f4260e` (feat)
2. **Task 2: Auth pages, auth hook, React Router with auth guard** - `21a2855` (feat)
3. **Task 3: Zobrist hash JS port and backend string hash validator** - `1c6b00a` (feat)

## Files Created/Modified

- `frontend/src/api/client.ts` - Axios instance with Bearer token interceptor and 401 redirect
- `frontend/src/types/api.ts` - TypeScript mirrors of all Pydantic schemas (AnalysisRequest/Response, WDLStats, GameRecord, ImportStatusResponse, UserResponse, LoginResponse)
- `frontend/src/hooks/useAuth.ts` - AuthProvider context with login/register/logout
- `frontend/src/components/auth/LoginForm.tsx` - Email+password form with sonner error toasts
- `frontend/src/components/auth/RegisterForm.tsx` - Registration with client-side validation
- `frontend/src/pages/Auth.tsx` - Tabbed auth page (login/register), redirects if already authed
- `frontend/src/pages/Dashboard.tsx` - Placeholder with header, Logout button, Import Games button
- `frontend/src/App.tsx` - QueryClientProvider + AuthProvider + React Router + ProtectedRoute + Toaster
- `frontend/src/lib/zobrist.ts` - Full POLYGLOT_RANDOM_ARRAY (781 BigInt literals) + computeHashes()
- `frontend/vite.config.ts` - Tailwind v4 plugin, @ alias, Vite proxy to backend
- `app/schemas/analysis.py` - Added `coerce_target_hash` field_validator for str->int coercion
- `.gitignore` - Added `!frontend/src/lib/` override for Python `lib/` pattern

## Decisions Made

- **Vite proxy over absolute URLs**: Frontend uses relative API paths (`/auth/jwt/login`), Vite dev proxy forwards to backend. No hardcoded `localhost:8000` in source.
- **BigInt + string transport**: Hashes computed as BigInt throughout (avoids precision loss), converted to decimal string for JSON serialization to the API.
- **Separate indexing for whiteHash/blackHash vs fullHash**: Discovered that Python `_color_hash` uses pivot=0 for white (color-relative), but `chess.polyglot.zobrist_hash` uses ZobristHasher with pivot=0 for black (occupied_co index). Both approaches are internally consistent but use different array positions. JS port replicates both exactly.
- **Turn hash on white**: `chess.polyglot.zobrist_hash` XORs index 780 when WHITE is to move (not black). Verified against backend values.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Tailwind CSS and import alias setup required before shadcn init**
- **Found during:** Task 1 (shadcn/ui initialization)
- **Issue:** `npx shadcn@latest init` failed because Tailwind v4 CSS import not in index.css, and `@/*` path alias not in root tsconfig.json (only in tsconfig.app.json which shadcn doesn't check)
- **Fix:** Added `@import "tailwindcss"` to index.css, installed `@tailwindcss/vite`, added `@types/node`, configured vite.config.ts with tailwindcss() plugin and resolve.alias, added path alias to root tsconfig.json
- **Files modified:** frontend/src/index.css, frontend/vite.config.ts, frontend/tsconfig.json, frontend/tsconfig.app.json
- **Verification:** shadcn init succeeded on retry; build passes
- **Committed in:** 0f4260e (Task 1 commit)

**2. [Rule 3 - Blocking] Root .gitignore excluded frontend/src/lib/**
- **Found during:** Task 1 (git staging)
- **Issue:** Root `.gitignore` has `lib/` as a Python packaging pattern; this blocked staging `frontend/src/lib/utils.ts`
- **Fix:** Added `!frontend/src/lib/` negation after the `lib/` pattern in root .gitignore
- **Files modified:** .gitignore
- **Verification:** `git add frontend/src/lib/` succeeded after fix
- **Committed in:** 0f4260e (Task 1 commit)

**3. [Rule 1 - Bug] Unused `Color` import in zobrist.ts**
- **Found during:** Task 3 (build verification)
- **Issue:** TypeScript strict mode (`noUnusedLocals`) flagged `Color` type imported from chess.js but not used
- **Fix:** Removed `Color` from import statement
- **Files modified:** frontend/src/lib/zobrist.ts
- **Verification:** Build passes with no TypeScript errors
- **Committed in:** 1c6b00a (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 bug)
**Impact on plan:** All fixes necessary for correct setup and TypeScript compliance. No scope creep.

## Issues Encountered

- `shadcn@latest init --yes -b radix -p nova --no-monorepo` approach worked only after Tailwind v4 CSS import was added to index.css and path alias was in root tsconfig.json
- Discovered that whiteHash/blackHash and fullHash use different array indexing schemes in the Python backend — required careful analysis of `ZobristHasher` source code to port correctly. The key insight: `enumerate(board.occupied_co)` gives pivot=0 for BLACK (occupied_co[0]) and pivot=1 for WHITE (occupied_co[1]) — opposite of what `_color_hash` uses.

## Next Phase Readiness

- Frontend builds with no TypeScript errors; auth flow is complete
- Plan 03 can build the chess board UI and analysis workflow on top of this foundation
- Dashboard placeholder ready to be replaced with interactive chess board + analysis panel
- `computeHashes()` ready for use in the position analysis component

---
*Phase: 04-frontend-and-auth*
*Completed: 2026-03-12*

## Self-Check: PASSED

- All 12 key files verified present on disk
- All 3 task commits verified in git log (0f4260e, 21a2855, 1c6b00a)
- `npm run build` succeeds with no TypeScript errors
- All 166 backend tests pass
