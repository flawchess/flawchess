# Phase 4: Frontend and Auth - Research

**Researched:** 2026-03-12
**Domain:** React + TypeScript frontend, FastAPI-Users auth, Zobrist hash JS port
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Component library & theming**
- shadcn/ui (copy-paste components on Radix UI + Tailwind) — no heavy runtime dependency
- Dark theme only — no light/dark toggle
- Responsive design: two-column on desktop (>768px), stacked vertical on mobile

**App layout**
- Single-page dashboard: board + filters + results all visible on one page
- Use React Router from the start to support future multi-page expansion
- Desktop: board and filters on the left, stats and game list on the right
- Mobile: board → filters (collapsible) → Analyze button → stats → game list (vertical stack)

**Board interaction & position input**
- Play moves from starting position — user plays both sides to define target position
- Move list panel with standard algebraic notation (1. e4 e5 2. Nf3 ...)
- Clickable moves in the list to jump to any position
- Back/forward navigation buttons + Reset to starting position
- Explicit "Analyze" button — results do NOT auto-update on each move
- Zobrist hash computed in frontend JavaScript (port Zobrist tables from Python) — no backend round-trip for hash computation

**Analysis results layout**
- W/D/L stats: horizontal stacked bar (green/gray/red) with percentages and counts
- Game list: compact table rows — Result (colored W/D/L), Opponent, Date, Time Control, Link icon
- Sorted by date (newest first) with pagination (page numbers)
- "X of Y games matched" denominator always visible

**Filter controls**
- Responsive: inline chips/toggles on desktop, collapsible behind "Filters" button on mobile
- Match side as toggle group (White / Black / Both)
- Time controls as toggle chips (multi-select)
- Rated/casual as toggle
- Recency as dropdown
- Color played as toggle

**Empty / initial states**
- Initial load: board shows starting position, results panel shows prompt "Play moves on the board and click Analyze to see your stats"
- No games imported: board interactive but results area shows "Import your games to start analyzing" with prominent Import Games button

**Import flow & progress**
- "Import Games" button in header opens a modal dialog
- Modal: platform selector (chess.com / lichess) + username field — one platform per submit for clean error handling
- Modal closes immediately after submit — import runs in background
- Progress shown as persistent toast/banner at bottom of screen — non-blocking
- Multiple concurrent imports stack in the toast area (both platforms can run simultaneously)
- Toast auto-dismisses on completion with success message
- Returning users: modal pre-fills remembered username per platform, shows last sync date, one-click "Re-sync" button

**Auth & onboarding**
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

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ANL-01 | User can specify a target position by playing moves on an interactive chess board | react-chessboard 5.x + chess.js for move handling; Zobrist hash JS port for client-side hash computation |
| AUTH-01 | User can create an account and log in | fastapi-users 15.x with BearerTransport + JWTStrategy; Google OAuth via httpx-oauth; email/password registration |
| AUTH-02 | Each user's games and analyses are isolated (row-level data scoping) | Replace user_id=1 placeholders with `Depends(current_active_user)`; games/game_positions already keyed by user_id |
</phase_requirements>

---

## Summary

Phase 4 delivers the complete user-facing application. It has three distinct work streams: (1) a React/TypeScript frontend built from scratch in a `frontend/` directory, (2) FastAPI-Users auth integration into the existing backend, and (3) a JavaScript port of the Python Zobrist hash algorithm so position hashes are computed entirely in the browser.

The frontend is a single-page dashboard using Vite 5 + React 19 + TypeScript, shadcn/ui components over Tailwind CSS, TanStack Query v5 for server state, and React Router v7 for routing. The interactive board uses react-chessboard 5.x paired with chess.js for move validation and FEN management. The Zobrist hash port must use JavaScript BigInt for 64-bit fidelity — native 32-bit JS bitwise operators will produce wrong hashes.

The backend work is focused: add a `User` model with FastAPI-Users, create one Alembic migration, wire up auth routes, and replace two `user_id = 1` placeholders with `Depends(current_active_user)`. The existing `games.user_id` and `game_positions.user_id` columns are already in place — no schema redesign needed, only a FK constraint addition and the users table itself.

**Primary recommendation:** Stand up the Vite frontend project first, then integrate auth (backend + frontend login/register flow), then build the board + analysis UI as the last major piece.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vite | 5.x (already in CLAUDE.md) | Frontend build tool | Already established in project stack |
| React | 19.x (already in CLAUDE.md) | UI framework | Already established |
| TypeScript | 5.x | Type safety | Already established |
| react-chessboard | 5.10.0 (Feb 2026) | Interactive chess board component | Only actively maintained React chess board; supports onPieceDrop, onSquareClick, FEN-based position |
| chess.js | 1.x | Chess move validation and FEN management | Standard JS chess logic library; validates moves, generates SAN notation, tracks game history |
| TanStack Query | 5.x (already in CLAUDE.md) | Server state management | Already established; handles loading/error/caching for API calls |
| React Router | 7.x | Client-side routing | Already in CLAUDE.md; needed for auth route separation |
| Tailwind CSS | 4.x | Styling | Already in CLAUDE.md |
| shadcn/ui | latest (2025+) | Component library | Locked decision; copy-paste components, no runtime dependency |
| fastapi-users | 15.0.4 | Auth framework | Already in CLAUDE.md; now in maintenance mode — stable API |
| httpx-oauth | latest | Google OAuth client for fastapi-users | Required companion for OAuth support |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lucide-react | latest | Icon set | Used by shadcn/ui default |
| axios | 1.x | HTTP client for frontend | Simpler interceptor API than fetch for attaching auth headers; alternatively use fetch with a custom wrapper |
| sonner | latest | Toast notifications | shadcn/ui recommended toast library; replaces older react-hot-toast |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| axios | native fetch | fetch requires more boilerplate for interceptors; axios simpler for auth header injection |
| sonner | shadcn/ui built-in toast | sonner is the current shadcn/ui recommendation; built-in toast is older |
| React Router | TanStack Router | TanStack Router has better TS integration but higher learning curve; React Router 7 is simpler for this scope |

### Installation

```bash
# Create frontend project
npm create vite@latest frontend -- --template react-ts
cd frontend

# Core chess libraries
npm install react-chessboard chess.js

# State and routing
npm install @tanstack/react-query react-router-dom

# HTTP client
npm install axios

# shadcn/ui setup (Tailwind v4 included)
npx shadcn@latest init -t vite

# shadcn/ui components needed
npx shadcn@latest add button dialog input label select toggle toggle-group badge table

# Toast
npx shadcn@latest add sonner

# Icons
npm install lucide-react
```

Backend additions:
```bash
uv add "fastapi-users[sqlalchemy,oauth]"
uv add httpx-oauth
uv add python-jose[cryptography]  # or PyJWT — fastapi-users uses python-jose internally
```

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/
├── src/
│   ├── api/              # axios instance, typed API functions
│   │   ├── client.ts     # axios instance with auth interceptor
│   │   ├── analysis.ts   # POST /analysis/positions
│   │   └── imports.ts    # POST /imports, GET /imports/{job_id}
│   ├── components/
│   │   ├── board/        # ChessBoard, MoveList, BoardControls
│   │   ├── filters/      # FilterPanel, TimeControlChips, etc.
│   │   ├── results/      # WDLBar, GameTable, GameRow
│   │   ├── import/       # ImportModal, ImportProgress toast
│   │   └── auth/         # LoginForm, RegisterForm
│   ├── hooks/
│   │   ├── useAuth.ts    # current user, login, logout
│   │   ├── useAnalysis.ts # TanStack Query wrapper for analysis
│   │   └── useImport.ts  # import trigger + polling logic
│   ├── lib/
│   │   ├── zobrist.ts    # Zobrist hash port (BigInt)
│   │   └── utils.ts      # shadcn/ui utility (cn)
│   ├── pages/
│   │   ├── Dashboard.tsx # main single-page view
│   │   └── Auth.tsx      # login/register page
│   ├── types/
│   │   └── api.ts        # TypeScript mirrors of Pydantic schemas
│   ├── App.tsx           # React Router setup, QueryClientProvider
│   └── main.tsx
├── package.json
└── vite.config.ts

app/
├── models/
│   └── user.py           # NEW: FastAPI-Users User model
├── routers/
│   ├── auth.py           # NEW: FastAPI-Users auth routes
│   ├── analysis.py       # MODIFY: replace user_id=1
│   └── imports.py        # MODIFY: replace user_id=1
└── main.py               # MODIFY: add CORS, include auth router
```

### Pattern 1: FastAPI-Users with Integer IDs and Async SQLAlchemy

FastAPI-Users defaults to UUID primary keys. This project uses BIGINT integer IDs (via `Base.type_annotation_map = {int: BIGINT}`). Use `SQLAlchemyBaseUserTable[int]` with an explicit integer `id` column.

```python
# app/models/user.py
from fastapi_users.db import SQLAlchemyBaseUserTable
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class User(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # email, hashed_password, is_active, is_superuser, is_verified
    # are inherited from SQLAlchemyBaseUserTable
```

```python
# app/users.py  (new file — UserManager + auth backend)
import uuid
from typing import Optional
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, IntegerIDMixin
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session
from app.models.user import User

SECRET = "CHANGE_THIS_IN_PRODUCTION"  # load from env settings

class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")

async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)

async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600 * 24 * 7)  # 7 days

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, int](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
```

**Source:** https://fastapi-users.github.io/fastapi-users/latest/configuration/databases/sqlalchemy/

### Pattern 2: Replacing user_id=1 in Routers

Both `analysis.py` and `imports.py` have a `TODO(phase-4)` comment at the `user_id = 1` line. Replace with:

```python
# In both routers — add import at top:
from app.users import current_active_user
from app.models.user import User

# Replace:
#   user_id = 1
# With:
async def endpoint(
    request: SomeRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> SomeResponse:
    user_id = user.id
    ...
```

### Pattern 3: CORS Middleware in main.py

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Note: `allow_credentials=True` is required for Authorization headers. Cannot combine with `allow_origins=["*"]` — must list origins explicitly.

### Pattern 4: Zobrist Hash JavaScript Port

The Python implementation uses `chess.polyglot.POLYGLOT_RANDOM_ARRAY` — a fixed array of 781 unsigned 64-bit integers. JavaScript's native bitwise operators are 32-bit only; BigInt is required for correct 64-bit XOR.

```typescript
// src/lib/zobrist.ts
// POLYGLOT_RANDOM_ARRAY must be copied verbatim from python-chess source
// as BigInt literals. The array has 781 entries.
// Source: https://github.com/niklasf/python-chess/blob/master/chess/polyglot.py

// Index formula (mirrors Python):
// index = 64 * ((pieceType - 1) * 2 + colorPivot) + square
// where colorPivot = 0 for white, 1 for black
// pieceType: 1=pawn, 2=knight, 3=bishop, 4=rook, 5=queen, 6=king

// To convert to signed int64 (matching PostgreSQL BIGINT storage):
function toSignedBigInt64(n: bigint): bigint {
  const unsigned = BigInt.asUintN(64, n);
  if (unsigned >= BigInt("9223372036854775808")) {
    return unsigned - BigInt("18446744073709551616");
  }
  return unsigned;
}

export function computeHashes(chess: Chess): {
  whiteHash: bigint;
  blackHash: bigint;
  fullHash: bigint;
} {
  // Use chess.js board() to iterate pieces
  // Apply POLYGLOT_RANDOM_ARRAY XOR for each piece
}
```

**Critical:** The `POLYGLOT_RANDOM_ARRAY` values must be copied exactly from python-chess source. The hash output must match the Python backend byte-for-byte. The final values sent to the API must be JavaScript `number` (not BigInt) because JSON does not support BigInt natively — use `Number(signedBigInt)` only after verifying the value is within the safe integer range, OR send as a string and accept `int` on the backend. Given the values are signed 64-bit, many will exceed `Number.MAX_SAFE_INTEGER`. **Recommendation:** send hashes as strings in the API request body, or use JSON serialization with BigInt. Verify this against the `AnalysisRequest.target_hash: int` field.

**Alternative approach:** Since AnalysisRequest accepts a Python `int`, send the hash as a JSON number. Python accepts large integers from JSON. JavaScript `Number` loses precision for values > 2^53. Use a custom JSON serializer or send as string with backend accepting `str` for the hash field. The simplest fix: backend accepts `target_hash: int | str` with a validator.

### Pattern 5: chess.js + react-chessboard Move Handling

```typescript
import { Chess } from 'chess.js';
import { Chessboard } from 'react-chessboard';
import { useState, useRef } from 'react';

export function ChessPositionPicker({ onAnalyze }) {
  const chess = useRef(new Chess());
  const [position, setPosition] = useState('start');
  const [moveHistory, setMoveHistory] = useState<string[]>([]);

  function onPieceDrop(sourceSquare: string, targetSquare: string): boolean {
    try {
      const move = chess.current.move({
        from: sourceSquare,
        to: targetSquare,
        promotion: 'q', // auto-queen for simplicity
      });
      if (!move) return false;
      setPosition(chess.current.fen());
      setMoveHistory(chess.current.history({ verbose: false }));
      return true;
    } catch {
      return false;
    }
  }

  function goToMove(index: number) {
    // replay from start to index
    const newChess = new Chess();
    const fullHistory = chess.current.history();
    fullHistory.slice(0, index + 1).forEach(san => newChess.move(san));
    chess.current = newChess;
    setPosition(newChess.fen());
    setMoveHistory(newChess.history({ verbose: false }));
  }

  return (
    <Chessboard
      position={position}
      onPieceDrop={onPieceDrop}
    />
  );
}
```

`chess.fen()` returns the full FEN including castling/en passant. **Do not** use this for position comparison (per CLAUDE.md: use `board.board_fen()` for matching). The Zobrist hash is computed from piece placement only, matching the Python behavior.

### Pattern 6: TanStack Query for Analysis

```typescript
// src/hooks/useAnalysis.ts
import { useMutation } from '@tanstack/react-query';

interface AnalysisRequest {
  target_hash: number;
  match_side: 'white' | 'black' | 'full';
  time_control?: string[];
  rated?: boolean;
  recency?: string;
  color?: 'white' | 'black';
  offset?: number;
  limit?: number;
}

export function useAnalysis() {
  return useMutation({
    mutationFn: (req: AnalysisRequest) =>
      apiClient.post<AnalysisResponse>('/analysis/positions', req).then(r => r.data),
  });
}
```

Analysis is a POST with a body (not a GET with query params), so `useMutation` is correct here — not `useQuery`.

### Pattern 7: Import Polling

```typescript
// src/hooks/useImport.ts
import { useMutation, useQuery } from '@tanstack/react-query';

export function useImportPolling(jobId: string | null) {
  return useQuery({
    queryKey: ['import', jobId],
    queryFn: () => apiClient.get(`/imports/${jobId}`).then(r => r.data),
    enabled: !!jobId,
    refetchInterval: (data) => {
      // Stop polling when terminal state reached
      if (data?.status === 'completed' || data?.status === 'failed') return false;
      return 2000; // poll every 2 seconds
    },
  });
}
```

### Pattern 8: Auth Token Storage

For this application (SPA with no SSR), the recommended approach is **localStorage for the JWT** with the understanding of XSS risk, OR httpOnly cookies requiring a CookieTransport on the backend. FastAPI-Users supports both `BearerTransport` (returns token in JSON response body) and `CookieTransport` (sets httpOnly cookie).

**Recommendation (Claude's discretion):** Use `BearerTransport` (Bearer token in Authorization header). Store the JWT in memory (React state/context) for the session, with localStorage as a persistence fallback on page reload. This is simpler than cookie transport for a same-origin SPA and avoids CSRF complexity. FastAPI-Users' `BearerTransport` is the more commonly documented path.

```typescript
// src/hooks/useAuth.ts
// On login: store token in localStorage + React context
// On every API call: attach via axios interceptor
// On 401: clear token + redirect to /login
```

### Anti-Patterns to Avoid

- **Using `chess.fen()` for position hash input**: Use piece placement only (white/black pieces separately). The Zobrist hash ignores castling rights and en passant.
- **Sending BigInt directly as JSON**: `JSON.stringify` throws on BigInt values. Convert to Number or string before serializing.
- **Auto-triggering analysis on every move**: The board should require an explicit "Analyze" button click (locked decision).
- **Hardcoding user_id=1 in tests**: After auth integration, tests for protected endpoints need authenticated users.
- **Missing `allow_credentials=True` on CORS**: Required for Authorization headers from the browser.
- **UUID-based User model**: FastAPI-Users defaults to UUID. This project uses integer IDs (BIGINT). Use `IntegerIDMixin` + `SQLAlchemyBaseUserTable[int]`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| User registration, login, password reset | Custom auth endpoints | fastapi-users 15.x | Handles hashing, tokens, OAuth flows, email verification |
| Chess move validation | Custom move validator | chess.js | Handles all edge cases: castling, en passant, promotion, check/stalemate |
| Chessboard rendering | Custom board component | react-chessboard 5.x | Handles drag+drop, square highlighting, responsive sizing, piece SVGs |
| UI components (buttons, dialogs, inputs) | Custom CSS components | shadcn/ui | Radix UI accessibility primitives + Tailwind; accessible keyboard navigation |
| Toast/notification system | Custom toast | sonner via shadcn | Handles stacking, auto-dismiss, animation |
| API response caching and loading states | Custom fetch with state | TanStack Query v5 | Handles deduplication, background refresh, error retry |
| Polyglot random array values | Custom hash table | Copy from python-chess source | Must be identical to backend; not regeneratable |

**Key insight:** The Zobrist hash computation is the only "port" work required. Everything else uses established libraries.

---

## Common Pitfalls

### Pitfall 1: Zobrist Hash 64-bit Precision Loss

**What goes wrong:** JavaScript `Number` type is IEEE 754 double-precision. Values above 2^53 (~9 quadrillion) lose precision when stored as `Number`. Zobrist hashes are 64-bit unsigned integers — most values exceed 2^53.

**Why it happens:** `POLYGLOT_RANDOM_ARRAY` entries are 64-bit. XOR of these values produces 64-bit results. Native JS bitwise XOR truncates to 32 bits, and storing as `Number` loses bits beyond 53.

**How to avoid:** Use BigInt throughout the Zobrist computation. Convert to signed 64-bit at the end. For JSON serialization to the backend, the safest approach is to convert to Number (which works for values within JS safe integer range) OR modify `AnalysisRequest.target_hash` to accept a string and parse on the backend. Validate with test vectors: compute hash for starting position in both Python and JS and compare.

**Warning signs:** Analysis always returns 0 results even though games were imported from the matching position.

### Pitfall 2: FastAPI-Users UUID vs Integer ID Mismatch

**What goes wrong:** Default FastAPI-Users examples use `SQLAlchemyBaseUserTableUUID` and `UUIDIDMixin`. If you follow the docs literally, you get UUID primary keys incompatible with the project's BIGINT convention and the existing `games.user_id BIGINT` foreign key.

**Why it happens:** UUID is the default in FastAPI-Users documentation.

**How to avoid:** Use `SQLAlchemyBaseUserTable[int]` and `IntegerIDMixin` explicitly. Declare `id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)`.

**Warning signs:** Alembic autogenerate creates a UUID column for users.id instead of BIGINT.

### Pitfall 3: CORS Credentials + Wildcard Origin

**What goes wrong:** `allow_origins=["*"]` with `allow_credentials=True` is rejected by browsers (CORS spec violation). The backend starts without error but the browser blocks all credentialed requests.

**Why it happens:** Security spec disallows wildcards with credentials. FastAPI does not raise an error at startup.

**How to avoid:** Always list explicit origins: `["http://localhost:5173"]` for dev, production domain for prod.

**Warning signs:** Browser console shows CORS error even though the backend has CORS middleware.

### Pitfall 4: chess.js History Replay for Back/Forward Navigation

**What goes wrong:** chess.js does not support an "undo" operation that returns to an arbitrary ply. Calling `chess.undo()` only undoes the last move.

**Why it happens:** chess.js is move-forward only internally. To jump to ply N, you must replay from ply 0.

**How to avoid:** Store the full move history as a string array. To navigate to a target ply, create a new `Chess()` instance and replay moves 0..N. The `useRef` pattern (not `useState`) for the Chess instance prevents unnecessary re-renders during replay.

**Warning signs:** Clicking an earlier move in the move list shows the wrong position.

### Pitfall 5: Missing Alembic Migration for users Table

**What goes wrong:** Running the app after adding `User` model without generating and applying a migration. The server starts but registration returns 500 because the `users` table doesn't exist.

**Why it happens:** SQLAlchemy async does not auto-create tables.

**How to avoid:** Always `uv run alembic revision --autogenerate -m "add users table"` after adding a model, then `uv run alembic upgrade head` before testing.

**Warning signs:** `asyncpg.exceptions.UndefinedTableError: relation "users" does not exist`.

### Pitfall 6: Import Router Uses asyncio.create_task Without User Dependency

**What goes wrong:** `imports.py` calls `asyncio.create_task(import_service.run_import(job_id))` which runs outside the request lifecycle. The `user_id` must be extracted from the token BEFORE spawning the task — you cannot pass a `Depends` dependency into a background task.

**Why it happens:** FastAPI `Depends()` only works within the request handler scope.

**How to avoid:** Extract `user.id` from `Depends(current_active_user)` in the route handler, pass the integer `user_id` to `import_service.create_job(user_id, ...)` before `asyncio.create_task`.

---

## Code Examples

Verified patterns from official sources:

### FastAPI-Users Router Includes

```python
# app/routers/auth.py (new file)
from fastapi import APIRouter
from app.users import fastapi_users, auth_backend
from fastapi_users import schemas

router = APIRouter()

router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_register_router(schemas.BaseUserCreate, schemas.BaseUser),
    prefix="/auth",
    tags=["auth"],
)
```

```python
# app/main.py additions
from app.routers import auth as auth_router

app.include_router(auth_router.router)
```

Source: https://fastapi-users.github.io/fastapi-users/latest/configuration/full-example/

### Google OAuth Router

```python
from httpx_oauth.clients.google import GoogleOAuth2

google_oauth_client = GoogleOAuth2(
    settings.GOOGLE_OAUTH_CLIENT_ID,
    settings.GOOGLE_OAUTH_CLIENT_SECRET,
)

# In auth router:
router.include_router(
    fastapi_users.get_oauth_router(
        google_oauth_client,
        auth_backend,
        settings.SECRET,
        is_verified_by_default=True,
    ),
    prefix="/auth/google",
    tags=["auth"],
)
```

Source: https://fastapi-users.github.io/fastapi-users/latest/configuration/oauth/

### Frontend TypeScript Types (mirror of Pydantic schemas)

```typescript
// src/types/api.ts
export interface WDLStats {
  wins: number;
  draws: number;
  losses: number;
  total: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
}

export interface GameRecord {
  game_id: number;
  opponent_username: string | null;
  user_result: 'win' | 'draw' | 'loss';
  played_at: string | null;
  time_control_bucket: string | null;
  platform: string;
  platform_url: string | null;
}

export interface AnalysisResponse {
  stats: WDLStats;
  games: GameRecord[];
  matched_count: number;
  offset: number;
  limit: number;
}

export interface AnalysisRequest {
  target_hash: number;  // see Pitfall 1 re: BigInt
  match_side: 'white' | 'black' | 'full';
  time_control?: ('bullet' | 'blitz' | 'rapid' | 'classical')[];
  rated?: boolean;
  recency?: 'week' | 'month' | '3months' | '6months' | 'year' | 'all';
  color?: 'white' | 'black';
  offset?: number;
  limit?: number;
}

export interface ImportStatusResponse {
  job_id: string;
  platform: string;
  username: string;
  status: string;
  games_fetched: number;
  games_imported: number;
  error: string | null;
}
```

### Axios Instance with Auth Interceptor

```typescript
// src/api/client.ts
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);
```

### shadcn/ui Dark Mode (Tailwind v4)

For dark-only mode, wrap `<html>` with `class="dark"` and do not add a theme toggle. shadcn/ui components read `.dark` via CSS variables. No `next-themes` needed.

```html
<!-- index.html -->
<html lang="en" class="dark">
```

Source: https://ui.shadcn.com/docs/dark-mode

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| chess.js `chess.move()` returns null on invalid | chess.js throws + returns null | v1.0 | Wrap in try/catch when calling from onPieceDrop |
| fastapi-users UUID-only IDs | `SQLAlchemyBaseUserTable[int]` + `IntegerIDMixin` for integer IDs | 10.x | Must use explicit integer base, not UUID base |
| fastapi-users v10 full example | v15.0.4 (Feb 2026) — maintenance mode | 2025-2026 | API is stable; no new features, only security patches |
| react-chessboard v4 | v5.10.0 (Feb 2026) | 2026 | Latest version; API consistent with v4 |
| TanStack Query v4 callbacks | v5 removed onSuccess/onError from useQuery | v5 | Use mutation callbacks or useEffect for side effects |

**Deprecated/outdated:**
- `fastapi-users.github.io/fastapi-users/10.x/` docs: use `latest/` URL — significant API changes between v10 and v15
- `react-chessboard` onDrop (v3 API): current API is `onPieceDrop(sourceSquare, targetSquare, piece)` returning boolean

---

## Open Questions

1. **Zobrist hash JSON serialization precision**
   - What we know: Python `int` can handle arbitrary precision; JS `Number` loses precision above 2^53
   - What's unclear: Whether all valid Zobrist hash values from the polyglot array fit in JS safe integer range (they do not — polyglot values are full 64-bit unsigned)
   - Recommendation: Modify `AnalysisRequest.target_hash` to accept `int | str` with a `@field_validator` that coerces string to int, OR send as `Number` and accept minor precision risk (hashes that collide only due to precision loss would be extremely rare but could produce wrong results). The correct solution is BigInt-to-string serialization.

2. **Google OAuth credentials for development**
   - What we know: Google OAuth requires a registered app with redirect URIs
   - What's unclear: Whether the user has/wants to set up Google Cloud Console credentials for dev
   - Recommendation: Make Google OAuth optional at init time — gate behind env vars `GOOGLE_OAUTH_CLIENT_ID` and `GOOGLE_OAUTH_CLIENT_SECRET`; skip OAuth router if not configured

3. **Vite proxy vs CORS for dev**
   - What we know: Can either add CORS to FastAPI or use Vite's `server.proxy` config to forward `/api/*` to the backend
   - What's unclear: User preference
   - Recommendation: Use Vite proxy in `vite.config.ts` for dev (cleaner, avoids `localhost:8000` hardcoding in frontend); add CORS for production deployment

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, `asyncio_mode = "auto"`) |
| Quick run command | `uv run pytest tests/test_auth.py -x` |
| Full suite command | `uv run pytest` |

No frontend test framework is currently configured. The locked decision for Phase 4 is focused on delivering a working app, not frontend unit tests. Frontend validation will be manual UAT.

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | User can register via POST /auth/register | integration | `uv run pytest tests/test_auth.py::test_register -x` | ❌ Wave 0 |
| AUTH-01 | User can login via POST /auth/jwt/login | integration | `uv run pytest tests/test_auth.py::test_login -x` | ❌ Wave 0 |
| AUTH-02 | Analysis endpoint returns 401 without token | integration | `uv run pytest tests/test_auth.py::test_analysis_requires_auth -x` | ❌ Wave 0 |
| AUTH-02 | Import endpoint returns 401 without token | integration | `uv run pytest tests/test_auth.py::test_import_requires_auth -x` | ❌ Wave 0 |
| AUTH-02 | User A cannot see User B's games in analysis | integration | `uv run pytest tests/test_auth.py::test_user_isolation -x` | ❌ Wave 0 |
| ANL-01 | Zobrist JS hash matches Python hash for starting position | manual-only | N/A — browser console test | N/A |
| ANL-01 | Zobrist JS hash matches Python hash after 1.e4 | manual-only | N/A — browser console test | N/A |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_auth.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_auth.py` — covers AUTH-01, AUTH-02 (register, login, 401 protection, user isolation)
- [ ] `tests/conftest.py` — add `create_test_user()` async fixture using fastapi-users UserManager
- [ ] Backend: `uv add "fastapi-users[sqlalchemy,oauth]" httpx-oauth` — if not yet installed

*(Existing test infrastructure in `tests/` covers phases 1-3; new `test_auth.py` needed for phase 4 auth requirements)*

---

## Sources

### Primary (HIGH confidence)
- https://fastapi-users.github.io/fastapi-users/latest/configuration/databases/sqlalchemy/ — SQLAlchemy async user model, integer ID setup
- https://fastapi-users.github.io/fastapi-users/latest/configuration/oauth/ — Google OAuth setup, httpx-oauth client
- https://fastapi-users.github.io/fastapi-users/latest/configuration/full-example/ — complete auth router setup
- https://pypi.org/project/fastapi-users/ — confirmed version 15.0.4 (Feb 2026)
- https://github.com/Clariity/react-chessboard — confirmed version 5.10.0 (Feb 2026)
- https://fastapi.tiangolo.com/tutorial/cors/ — CORSMiddleware configuration
- https://ui.shadcn.com/docs/installation/vite — shadcn/ui Vite setup

### Secondary (MEDIUM confidence)
- https://tanstack.com/query/v5/docs/framework/react/reference/useMutation — useMutation v5 API
- https://jhlywa.github.io/chess.js/ — chess.js API for move handling and FEN
- https://react-chessboard.vercel.app/ — react-chessboard component props (site returned Storybook config, not full docs)
- https://github.com/niklasf/python-chess/blob/master/chess/polyglot.py — POLYGLOT_RANDOM_ARRAY source

### Tertiary (LOW confidence)
- General pattern for BigInt Zobrist hash in JS — no authoritative source found; derived from chess programming wiki + MDN BigInt docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions confirmed via PyPI, npm, and official docs
- Architecture: HIGH — patterns derived from official FastAPI-Users docs and existing codebase
- Pitfalls: HIGH for backend (confirmed from docs); MEDIUM for Zobrist BigInt precision (derived reasoning, no direct authoritative source)
- Zobrist JS port: MEDIUM — algorithm is well-understood; exact BigInt serialization strategy needs a test vector validation step

**Research date:** 2026-03-12
**Valid until:** 2026-04-12 (fastapi-users in maintenance mode = stable; react-chessboard actively maintained but API stable)
