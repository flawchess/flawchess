# Phase 4: Frontend and Auth - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver the complete multi-user web application: React frontend with interactive chessboard for position input, auth via FastAPI-Users, game import UI with background progress, and position-based W/D/L analysis display. Replace hardcoded user_id=1 in both import and analysis routers with real authenticated user.

Requirements: ANL-01, AUTH-01, AUTH-02

</domain>

<decisions>
## Implementation Decisions

### Component library & theming
- shadcn/ui (copy-paste components on Radix UI + Tailwind) — no heavy runtime dependency
- Dark theme only — no light/dark toggle
- Responsive design: two-column on desktop (>768px), stacked vertical on mobile

### App layout
- Single-page dashboard: board + filters + results all visible on one page
- Use React Router from the start to support future multi-page expansion
- Desktop: board and filters on the left, stats and game list on the right
- Mobile: board → filters (collapsible) → Analyze button → stats → game list (vertical stack)

### Board interaction & position input
- Play moves from starting position — user plays both sides to define target position
- Move list panel with standard algebraic notation (1. e4 e5 2. Nf3 ...)
- Clickable moves in the list to jump to any position
- Back/forward navigation buttons + Reset to starting position
- Explicit "Analyze" button — results do NOT auto-update on each move
- Zobrist hash computed in frontend JavaScript (port Zobrist tables from Python) — no backend round-trip for hash computation

### Analysis results layout
- W/D/L stats: horizontal stacked bar (green/gray/red) with percentages and counts
- Game list: compact table rows — Result (colored W/D/L), Opponent, Date, Time Control, Link icon
- Sorted by date (newest first) with pagination (page numbers)
- "X of Y games matched" denominator always visible

### Filter controls
- Responsive: inline chips/toggles on desktop, collapsible behind "Filters" button on mobile
- Match side as toggle group (White / Black / Both)
- Time controls as toggle chips (multi-select)
- Rated/casual as toggle
- Recency as dropdown
- Color played as toggle

### Empty / initial states
- Initial load: board shows starting position, results panel shows prompt "Play moves on the board and click Analyze to see your stats"
- No games imported: board interactive but results area shows "Import your games to start analyzing" with prominent Import Games button

### Import flow & progress
- "Import Games" button in header opens a modal dialog
- Modal: platform selector (chess.com / lichess) + username field — one platform per submit for clean error handling
- Modal closes immediately after submit — import runs in background
- Progress shown as persistent toast/banner at bottom of screen — non-blocking
- Multiple concurrent imports stack in the toast area (both platforms can run simultaneously)
- Toast auto-dismisses on completion with success message
- Returning users: modal pre-fills remembered username per platform, shows last sync date, one-click "Re-sync" button

### Auth & onboarding
- Email + password registration/login (FastAPI-Users built-in)
- Google OAuth as additional sign-in option
- JWT token authentication
- Auth wall: must sign up/log in before accessing any features
- New user with no games: dashboard with board visible, results area shows import CTA
- Replace hardcoded user_id=1 in import and analysis routers with authenticated user from FastAPI-Users
- Row-level data isolation: each user sees only their own games and analyses

### Claude's Discretion
- Frontend project structure and file organization
- State management approach (TanStack Query for server state, React state for UI)
- Zobrist table porting strategy (exact implementation)
- JWT storage approach (httpOnly cookie vs localStorage)
- Landing/login page design
- Loading skeletons and transition animations
- Error toast styling and positioning
- Exact responsive breakpoints beyond the 768px mobile/desktop split

</decisions>

<specifics>
## Specific Ideas

- Single-page dashboard layout inspired by the ASCII mockup: board+filters left, stats+games right
- Import modal for returning users shows both platforms with remembered usernames and re-sync buttons, plus "import new" section below
- The app should feel snappy — hash computation in JS means no waiting for the backend just to set a position

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/schemas/analysis.py`: AnalysisRequest/AnalysisResponse/WDLStats/GameRecord — frontend TypeScript types should mirror these
- `app/schemas/imports.py`: ImportRequest/ImportStartedResponse/ImportStatusResponse — frontend mirrors these too
- `app/services/zobrist.py`: Zobrist hash computation — tables and algorithm must be ported to JavaScript identically
- `app/routers/analysis.py`: POST /analysis/positions — frontend's primary API endpoint
- `app/routers/imports.py`: POST /imports + GET /imports/{job_id} — import trigger and polling endpoints

### Established Patterns
- Backend: routers/services/repositories layering (no changes needed to architecture)
- All routers have `TODO(phase-4)` comments marking where user_id=1 needs replacement
- Import job polling via GET /imports/{job_id} returns status + games_fetched count

### Integration Points
- FastAPI-Users adds auth routes (/auth/register, /auth/login, /auth/jwt/login, etc.) and current_user dependency
- Both import and analysis routers need Depends(current_active_user) replacing hardcoded user_id=1
- Frontend polls GET /imports/{job_id} for progress updates (job_id returned from POST /imports)
- CORS middleware needed on FastAPI app for frontend dev server

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-frontend-and-auth*
*Context gathered: 2026-03-12*
