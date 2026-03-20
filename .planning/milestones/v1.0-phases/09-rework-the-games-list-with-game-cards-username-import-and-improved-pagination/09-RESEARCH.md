# Phase 9: Rework Games List with Game Cards, Username Import, and Improved Pagination - Research

**Researched:** 2026-03-14
**Domain:** React UI component rework, FastAPI schema/model extension, SQLAlchemy migrations
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Game card layout:**
- Full-width card list (vertically stacked), replacing the current `<table>` in GameTable.tsx
- Each card has a colored left border accent: green for win, gray for draw, red for loss
- Cards show all current fields plus new fields:
  - Existing: result badge (W/D/L), opponent username, date, time control bucket, platform link
  - New: user rating vs opponent rating, opening name + ECO code, color indicator (white/black), platform icon (chess.com/lichess), number of moves
- Card visual hierarchy: result + opponent prominent on first line, metadata (ratings, opening, TC, date, moves) on second line

**Move count column:**
- Add `move_count: Mapped[int | None]` column to the Game model
- Alembic migration to add the column
- Backfill existing games by counting moves from stored PGN
- Populate move_count at import time for new games

**GameRecord schema expansion:**
- Add to GameRecord (backend schema + frontend type): user_rating, opponent_rating, opening_name, opening_eco, user_color, platform, move_count
- These fields already exist on the Game model — just need to be included in the response serialization

**Username storage — backend user profile:**
- Add `chess_com_username: Mapped[str | None]` and `lichess_username: Mapped[str | None]` columns to the User model
- Alembic migration for the new columns
- New endpoint: GET/PUT /users/me/profile (or extend existing user endpoint)
- Whenever an import runs, the backend auto-updates the stored username for that platform — no separate "save username" step
- Remove localStorage username storage from frontend (backend is source of truth)

**Import modal redesign:**
- Returning user (usernames set): Shows both platforms with username displayed and per-platform [Sync] buttons. One click to import — no typing needed. "Edit usernames" link to switch to input mode.
- First-time user (no usernames): Shows input fields per platform (similar to current modal). After first import, username is saved and modal switches to Sync view.
- Per-platform Sync buttons only (no "Sync All" button)
- Import still runs in background with progress toast (unchanged)

**Pagination improvements:**
- Truncated page numbers: show first/last pages + window around current page (e.g., `< 1 2 3 ... 8 9 10 ... 48 49 50 >`)
- Page size reduced from 50 to 20 (cards are taller than table rows)
- Pagination controls at bottom of list only
- "X of Y games matched" counter stays at the top
- Page change scrolls to top of the results/cards area
- Keep offset-based pagination (no cursor-based change needed)

### Claude's Discretion
- Exact card spacing, padding, typography within the card
- Platform icon implementation (SVG, emoji, or text badge)
- Color indicator visual (circle, piece icon, or text)
- Truncated pagination window size (how many pages around current to show)
- How to handle missing data in cards (null ratings, null opening, etc.)
- Backfill strategy for move_count (migration script vs management command)
- Profile endpoint design (new router vs extending FastAPI-Users)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

## Summary

Phase 9 is a focused UI/data enhancement with three parallel tracks: (1) game card visual component, (2) backend model/schema expansion, and (3) username profile storage with redesigned import modal. All required data already exists in the `Game` model — the primary backend work is adding `move_count` to the model, adding platform usernames to the `User` model, and exposing these fields in the `GameRecord` schema. No new algorithmic complexity is introduced.

The frontend work is the largest portion: replacing `GameTable.tsx` with `GameCardList.tsx` that renders rich cards, redesigning `ImportModal.tsx` to support returning vs first-time user flows, and implementing truncated pagination logic. The existing shadcn/ui `Card` component is available and suitable as a base; however the design calls for a custom left-border-accent pattern that the shadcn `Card` does not provide out of the box, requiring a plain `div` with `border-l-4` Tailwind classes.

The import modal redesign requires a new `useUserProfile` TanStack Query hook to fetch/cache the profile endpoint. The modal switches between "sync view" (usernames known) and "input view" (first time) based on whether the profile returns non-null usernames. This is a stateless read from the server — no local state management beyond the query.

**Primary recommendation:** Implement in three focused plans: (1) backend model + schema + migrations, (2) game card component + pagination, (3) import modal redesign + profile endpoint.

---

## Standard Stack

### Core (already in use — no new installs)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy 2.x async | 2.x | ORM for model changes | Project standard |
| Alembic | current | Schema migrations | Project standard |
| FastAPI | 0.115.x | API endpoints | Project standard |
| Pydantic v2 | 2.x | Schema validation | Project standard |
| React + TypeScript | 19 | Frontend | Project standard |
| TanStack Query | 5.x | Server state | Project standard |
| Tailwind CSS | 3.x | Styling | Project standard |
| shadcn/ui | current | UI primitives | Project standard |
| python-chess | 1.10.x | PGN move counting | Project standard |

### No new packages required
All libraries needed for this phase are already installed. The move count backfill uses `chess.pgn.read_game()` (python-chess, already a dependency). Platform icons can be implemented with text badges or lucide-react icons (already installed).

**Installation:**
```bash
# No new packages needed
```

---

## Architecture Patterns

### Recommended Project Structure (additions only)
```
app/
├── models/
│   ├── game.py             # Add move_count column
│   └── user.py             # Add chess_com_username, lichess_username
├── schemas/
│   ├── analysis.py         # Expand GameRecord fields
│   └── users.py            # New: UserProfile schema
├── routers/
│   └── users.py            # New: GET/PUT /users/me/profile
├── repositories/
│   └── user_repository.py  # New: profile read/write queries
└── services/
    └── import_service.py   # Update username after import

frontend/src/
├── components/
│   ├── results/
│   │   ├── GameCardList.tsx    # New: replaces GameTable.tsx
│   │   └── GameCard.tsx        # New: single card component
│   └── import/
│       └── ImportModal.tsx     # Rework: two-mode UI
├── hooks/
│   └── useUserProfile.ts       # New: profile query + mutation
└── types/
    ├── api.ts                  # Expand GameRecord interface
    └── users.ts                # New or extend: UserProfile type
```

### Pattern 1: SQLAlchemy Mapped Column Addition
**What:** Add nullable columns to existing ORM model with `Mapped[int | None]`
**When to use:** Adding optional data columns to existing tables

```python
# Source: project pattern (app/models/game.py)
# Add to Game model:
move_count: Mapped[int | None] = mapped_column(nullable=True)

# Add to User model:
chess_com_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
lichess_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

### Pattern 2: Alembic Auto-generated Migration
**What:** Use `--autogenerate` to detect model changes and create migration
**When to use:** After updating ORM models

```bash
# Source: CLAUDE.md
uv run alembic revision --autogenerate -m "add move_count to games and usernames to users"
uv run alembic upgrade head
```

Note: Two logically related column additions can go into a single migration for this phase since they are independent tables but part of the same feature delivery.

### Pattern 3: Expanding Pydantic GameRecord
**What:** Add fields to `GameRecord` in `analysis.py` — fields already exist on the ORM model
**When to use:** Exposing existing model data through the API

```python
# Source: app/schemas/analysis.py — current GameRecord
class GameRecord(BaseModel):
    game_id: int
    opponent_username: str | None
    user_result: Literal["win", "draw", "loss"]
    played_at: datetime.datetime | None
    time_control_bucket: str | None
    platform: str
    platform_url: str | None
    # NEW additions:
    user_rating: int | None
    opponent_rating: int | None
    opening_name: str | None
    opening_eco: str | None
    user_color: str
    move_count: int | None
```

The analysis repository's `query_matching_games` returns full `Game` ORM objects, so the serialization layer simply reads the new fields. Confirm `model_config = ConfigDict(from_attributes=True)` is set (or verify Pydantic v2 ORM mode is active for this schema).

### Pattern 4: Profile Endpoint — New Router Pattern
**What:** New `/users/me/profile` router following the project's router/service/repository layering
**When to use:** New resource following project conventions

```python
# New: app/routers/users.py
router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me/profile", response_model=UserProfileResponse)
async def get_profile(
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserProfileResponse:
    ...

@router.put("/me/profile", response_model=UserProfileResponse)
async def update_profile(
    request: UserProfileUpdate,
    user: Annotated[User, Depends(current_active_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserProfileResponse:
    ...
```

Register in `app/main.py` as `app.include_router(users_router)`.

### Pattern 5: Auto-update Username in import_service
**What:** After successful import, update the user's stored platform username
**When to use:** After `run_import` completes in `import_service.py`

The `run_import` function already holds a session and the `job.username` / `job.platform` values. The update can be performed in the same session after the job is marked completed, before `session.commit()`.

```python
# Source: app/services/import_service.py — run_import
# After bulk insert loop, before marking job complete:
await user_repository.update_platform_username(
    session, job.user_id, job.platform, job.username
)
```

### Pattern 6: GameCardList Component Structure
**What:** Full-width card list replacing `<table>` in GameTable.tsx
**When to use:** Displaying game records with rich metadata

```tsx
// Source: project frontend pattern — uses tailwind border-l-4 for accent
// GameCard uses a plain div, NOT the shadcn Card component
// (shadcn Card has rounded-xl + ring-1, not compatible with left-border accent design)

function GameCard({ game }: { game: GameRecord }) {
  return (
    <div
      data-testid={`game-card-${game.game_id}`}
      className={cn(
        "flex flex-col gap-1 rounded border border-border bg-card px-4 py-3 border-l-4",
        RESULT_BORDER[game.user_result]
      )}
    >
      {/* Line 1: result badge + opponent + color indicator + platform link */}
      {/* Line 2: ratings, opening, TC, date, moves — muted text */}
    </div>
  );
}
```

Color classes reuse RESULT_CLASSES pattern from GameTable.tsx:
- Win: `border-l-green-600`
- Draw: `border-l-gray-500`
- Loss: `border-l-red-600`

### Pattern 7: Truncated Pagination Logic
**What:** Pure function that computes visible page numbers with ellipsis markers
**When to use:** When totalPages > threshold (e.g., > 7)

```typescript
// Returns an array of (number | 'ellipsis') for rendering
// Window size = 2 pages either side of current page
function getPaginationItems(
  currentPage: number,
  totalPages: number
): (number | 'ellipsis')[] {
  if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
  const delta = 2; // pages around current
  const range: number[] = [];
  // Always include: 1, 2, (current-delta..current+delta), totalPages-1, totalPages
  // Fill gaps with 'ellipsis'
  ...
}
```

### Pattern 8: Two-Mode Import Modal
**What:** Modal with sync view (returning user) and input view (first time or edit mode)
**When to use:** Profile data loaded; determines initial render mode

```tsx
// Sync view: profile.chess_com_username && profile.lichess_username both truthy
// Input view: either is null, or user clicked "Edit usernames"
const [editMode, setEditMode] = useState(false);
const profileQuery = useUserProfile(); // new TanStack Query hook
const isFirstTime = !profileQuery.data?.chess_com_username && !profileQuery.data?.lichess_username;
const showInputView = isFirstTime || editMode;
```

### Anti-Patterns to Avoid
- **Using shadcn `Card` component for game cards:** The shadcn Card has `rounded-xl` and `ring-1 ring-foreground/10` styling that conflicts with the left-border-accent design. Use a plain `div` with Tailwind classes.
- **Rendering all page numbers:** Current GameTable.tsx renders one button per page — this explodes for users with 1000+ games (50+ pages at new page size of 20). Must use truncated pagination from the start.
- **Saving username to localStorage in the new modal:** localStorage is being removed as source of truth. New modal only reads from the profile API.
- **Blocking run_import for profile update:** The username update in import_service must be a fire-and-forget or best-effort update — a failure to save the username should not fail the import job.
- **Putting SQL in the service layer:** Username update goes in a new `user_repository` function, called from the service. Keeps the project's layering consistent.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PGN move counting for backfill | Custom parser | `chess.pgn.read_game()` + `board.fullmove_number` | python-chess already handles all PGN edge cases |
| Pagination ellipsis logic | Nothing complex | Simple pure function (15-20 lines) | Small enough to write inline; no library needed |
| Server state caching for profile | Manual fetch + useState | TanStack Query `useQuery` | Already project standard; handles loading/error/stale states |
| Alembic migration generation | Hand-written SQL | `alembic revision --autogenerate` | Detects model changes automatically; project standard |

**Key insight:** All required data already exists in the database (ratings, opening info, user_color). The only new columns are `move_count` (Game) and platform usernames (User). The bulk of the phase is wiring up and displaying existing data.

---

## Common Pitfalls

### Pitfall 1: Pydantic v2 ORM Mode Not Active on GameRecord
**What goes wrong:** Adding new fields to `GameRecord` without verifying `model_config = ConfigDict(from_attributes=True)` causes `ValidationError` when serializing ORM objects.
**Why it happens:** Pydantic v2 requires explicit `from_attributes=True` to read from ORM instances (replaces v1's `orm_mode = True`).
**How to avoid:** Check `analysis.py` — if `GameRecord` currently serializes ORM objects successfully without this config, then it's already set or the repository is constructing dicts. Verify before adding fields.
**Warning signs:** 500 errors on `/analysis/positions` after adding fields.

### Pitfall 2: Analysis Repository Returns ORM Objects vs Dicts
**What goes wrong:** `query_matching_games` may return raw tuples or dicts rather than full `Game` ORM objects, so new fields aren't accessible.
**Why it happens:** SQLAlchemy `select()` with specific columns returns `Row` objects, not ORM model instances.
**How to avoid:** Check `analysis_repository.py` — if it `select(Game)` it returns full ORM objects; if it selects individual columns, new fields need to be added to the select list.
**Warning signs:** `AttributeError` when accessing `game.user_rating` etc.

### Pitfall 3: move_count Backfill Fails on Malformed PGN
**What goes wrong:** Some stored PGNs may be malformed, causing `chess.pgn.read_game()` to return `None` or raise exceptions during backfill.
**Why it happens:** The import pipeline already wraps per-game parsing in try/except, but historical data may predate this protection.
**How to avoid:** Wrap backfill SQL/Python in try/except per game; log and skip bad PGNs, leaving `move_count = NULL` for them.
**Warning signs:** Migration fails midway or leaves partial backfill.

### Pitfall 4: Profile Endpoint Conflicts with FastAPI-Users Routes
**What goes wrong:** FastAPI-Users registers routes under `/auth` and `/users`. A new `/users/me/profile` router may conflict with FastAPI-Users' own `/users/me` endpoint.
**Why it happens:** `fastapi_users.get_users_router()` registers `GET /users/me` — if the project includes that router, adding a new `users` router with the same prefix causes route conflicts.
**How to avoid:** Check `app/main.py` and `auth.py` — the current project does NOT include `get_users_router()`, only auth and register routers. The `/users` prefix is safe to use. Use `/users/me/profile` to avoid collision with any future FastAPI-Users routes.
**Warning signs:** FastAPI raises `ValueError: Route already defined` on startup.

### Pitfall 5: Import Modal Profile Fetch Delays Modal Open
**What goes wrong:** If `useUserProfile` has no cached data, the modal opens in a loading state, causing layout shift or flash.
**Why it happens:** Profile is fetched on-demand when modal opens.
**How to avoid:** Fetch the profile eagerly on page load (not lazily on modal open) — add `useUserProfile` to `DashboardPage` with `staleTime: 300_000`. By the time the user clicks Import, the profile is already cached.
**Warning signs:** Import modal flickers between input and sync views on first open.

### Pitfall 6: Page Size Constant in Two Places
**What goes wrong:** `PAGE_SIZE = 50` is defined in `Dashboard.tsx` and also implicitly in the `AnalysisRequest` schema default (`limit: int = 50`). Changing to 20 on the frontend but not updating server-side default causes confusion.
**Why it happens:** Server default is a fallback — the frontend always sends `limit` explicitly, so server default doesn't matter for correctness, but it's misleading.
**How to avoid:** Update `PAGE_SIZE` in `Dashboard.tsx` from 50 to 20. The server schema default can stay at 50 (it's only used when `limit` is omitted, which the frontend never does).

---

## Code Examples

### Backfill move_count from PGN (Alembic data migration)

```python
# Source: python-chess docs + project import patterns (import_service.py)
import chess.pgn
import io

def count_moves_from_pgn(pgn_text: str) -> int | None:
    """Count half-moves (plies) in a PGN string. Returns None on parse failure."""
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
        if game is None:
            return None
        board = game.board()
        count = 0
        for move in game.mainline_moves():
            board.push(move)
            count += 1
        return count
    except Exception:
        return None
```

Note: `count` here is number of half-moves (plies). The context decision says "number of moves" — clarify with user whether this means half-moves (plies) or full moves. Standard chess notation uses full moves (each side plays once = 1 move). Use `(count + 1) // 2` to convert plies to full moves, or simply store plies and display as "N moves" using the full-move count. Given the display says "number of moves" next to ratings/opening, full moves (integer) is the natural display value. Store plies internally (consistent with `game_positions.ply`) and display `count // 2 + (1 if count % 2 else 0)` OR just store full_move_count directly. **Recommendation:** Store full move count (total half-moves divided by 2, rounding up) as `move_count` — matches user mental model.

### UserProfile Pydantic schemas

```python
# New: app/schemas/users.py
from pydantic import BaseModel

class UserProfileResponse(BaseModel):
    chess_com_username: str | None
    lichess_username: str | None

class UserProfileUpdate(BaseModel):
    chess_com_username: str | None = None
    lichess_username: str | None = None
```

### useUserProfile hook

```typescript
// New: frontend/src/hooks/useUserProfile.ts
// Source: project TanStack Query pattern (usePositionBookmarks.ts, useAnalysis.ts)
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/api/client';

export interface UserProfile {
  chess_com_username: string | null;
  lichess_username: string | null;
}

export function useUserProfile() {
  return useQuery<UserProfile>({
    queryKey: ['userProfile'],
    queryFn: async () => {
      const res = await apiClient.get<UserProfile>('/users/me/profile');
      return res.data;
    },
    staleTime: 300_000, // 5 minutes
  });
}

export function useUpdateUserProfile() {
  const queryClient = useQueryClient();
  return useMutation<UserProfile, Error, Partial<UserProfile>>({
    mutationFn: async (data) => {
      const res = await apiClient.put<UserProfile>('/users/me/profile', data);
      return res.data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['userProfile'], data);
    },
  });
}
```

### Truncated pagination function

```typescript
// Source: project frontend pattern — pure utility function
type PaginationItem = number | 'ellipsis-start' | 'ellipsis-end';

function getPaginationItems(currentPage: number, totalPages: number): PaginationItem[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }
  const delta = 2;
  const left = Math.max(2, currentPage - delta);
  const right = Math.min(totalPages - 1, currentPage + delta);
  const items: PaginationItem[] = [1];
  if (left > 2) items.push('ellipsis-start');
  for (let p = left; p <= right; p++) items.push(p);
  if (right < totalPages - 1) items.push('ellipsis-end');
  items.push(totalPages);
  return items;
}
```

### Vite proxy addition for /users

```typescript
// frontend/vite.config.ts — add /users to proxy
// Source: project vite.config.ts pattern
'/users': { target: 'http://localhost:8000', changeOrigin: true }
```

---

## Integration Points Checklist

The planner should verify each integration point when creating tasks:

| Component | Change | File |
|-----------|--------|------|
| Game model | Add `move_count: Mapped[int \| None]` | `app/models/game.py` |
| User model | Add `chess_com_username`, `lichess_username` | `app/models/user.py` |
| Alembic | Single migration for both model changes + backfill | `alembic/versions/` |
| GameRecord schema | Add 6 fields | `app/schemas/analysis.py` |
| UserProfile schemas | New file | `app/schemas/users.py` |
| Users router | New GET/PUT `/users/me/profile` | `app/routers/users.py` |
| User repository | New `update_platform_username` + profile read/write | `app/repositories/user_repository.py` |
| import_service | Call `update_platform_username` after import | `app/services/import_service.py` |
| main.py | Register users router + add /users to Vite proxy | `app/main.py`, `frontend/vite.config.ts` |
| analysis_repository | Verify GameRecord fields are returned | `app/repositories/analysis_repository.py` |
| GameTable.tsx | Replace with GameCardList.tsx | `frontend/src/components/results/` |
| ImportModal.tsx | Rework two-mode UI | `frontend/src/components/import/ImportModal.tsx` |
| useUserProfile.ts | New hook | `frontend/src/hooks/useUserProfile.ts` |
| api.ts | Expand GameRecord interface | `frontend/src/types/api.ts` |
| Dashboard.tsx | Change PAGE_SIZE, swap GameTable for GameCardList | `frontend/src/pages/Dashboard.tsx` |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| localStorage for username | Backend User model columns | Phase 9 | Single source of truth; works across devices/browsers |
| `<table>` with 5 columns | Full-width cards with 10+ fields | Phase 9 | Richer per-game context at a glance |
| All page numbers rendered | Truncated with ellipsis | Phase 9 | Scales to 100+ pages without UI explosion |
| PAGE_SIZE = 50 | PAGE_SIZE = 20 | Phase 9 | Cards are taller; fewer items per page improves readability |

---

## Open Questions

1. **move_count: plies vs full moves for display**
   - What we know: The decision says "number of moves" which typically means full moves in chess
   - What's unclear: Whether to store plies (consistent with game_positions.ply) or full moves
   - Recommendation: Store full move count in `move_count` column (divide pgn plies by 2, round up). Simpler for display. Plies are already stored per-position in game_positions.

2. **analysis_repository: ORM object or dict return?**
   - What we know: `query_matching_games` returns game records; current GameRecord has 7 fields
   - What's unclear: Whether it returns full `Game` ORM instances or selects specific columns
   - Recommendation: Check `app/repositories/analysis_repository.py` before writing the schema expansion plan — if columns are explicitly selected, add new ones to the select statement.

3. **Profile endpoint: new router vs. FastAPI-Users user patch**
   - What we know: FastAPI-Users has a `get_users_router()` with PATCH /users/{id} but the project does NOT include it
   - What's unclear: Whether to use a completely new `/users/me/profile` endpoint or extend with a simpler GET+PUT
   - Recommendation: New standalone router at `GET /users/me/profile` + `PUT /users/me/profile` — cleanest and avoids FastAPI-Users complexity.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pytest.ini` or `pyproject.toml` (check project root) |
| Quick run command | `uv run pytest tests/test_users_router.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| GET /users/me/profile returns username fields | unit/integration | `uv run pytest tests/test_users_router.py::test_get_profile -x` | ❌ Wave 0 |
| PUT /users/me/profile updates username fields | unit/integration | `uv run pytest tests/test_users_router.py::test_put_profile -x` | ❌ Wave 0 |
| import_service updates username after import | unit | `uv run pytest tests/test_import_service.py::test_username_saved_after_import -x` | ❌ Wave 0 (extend existing) |
| move_count populated at import time | unit | `uv run pytest tests/test_import_service.py::test_move_count_populated -x` | ❌ Wave 0 (extend existing) |
| GameRecord serialization includes new fields | unit | `uv run pytest tests/test_analysis_service.py -x` | Extend existing |
| Alembic migration up/down (structural) | manual-only | N/A | N/A |
| Frontend: GameCardList renders game cards | manual-only (no FE test infra) | N/A | N/A |
| Frontend: pagination truncation logic | unit (if extracted) | N/A | ❌ optional |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q` (stop on first failure)
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_users_router.py` — covers profile GET/PUT endpoints (new file)
- [ ] Extend `tests/test_import_service.py` — add `test_username_saved_after_import` and `test_move_count_populated`

*(Existing test infrastructure covers all other phase requirements)*

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection of `app/models/game.py`, `app/models/user.py`, `app/schemas/analysis.py`, `app/routers/imports.py`, `app/services/import_service.py`
- Direct code inspection of `frontend/src/components/results/GameTable.tsx`, `frontend/src/components/import/ImportModal.tsx`, `frontend/src/pages/Dashboard.tsx`
- Project `CLAUDE.md` — canonical stack, conventions, constraints
- Phase 9 `CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.x mapped_column nullable pattern — inferred from existing code in `app/models/game.py`
- FastAPI-Users route analysis — from `app/routers/auth.py` and `app/users.py` (no `get_users_router` included)
- TanStack Query hook pattern — from `frontend/src/hooks/useImport.ts` and `usePositionBookmarks.ts`

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all technology already in use
- Architecture: HIGH — patterns directly observed in existing codebase
- Pitfalls: HIGH — specific to this codebase's patterns (ORM mode, route ordering, profile fetch timing)
- Integration points: HIGH — mapped from direct code inspection

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable stack, no fast-moving dependencies)
