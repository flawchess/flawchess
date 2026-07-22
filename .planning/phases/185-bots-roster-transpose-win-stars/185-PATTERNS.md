# Phase 185: Bots roster transpose + win stars - Pattern Map

**Mapped:** 2026-07-22
**Files analyzed:** 14 (5 new, 9 modified)
**Analogs found:** 14 / 14

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `frontend/src/components/bots/PersonaGrid.tsx` | component | transform (re-layout of already-loaded data) | itself (pre-existing, being restructured) | exact — same file, same responsibility, different iteration order |
| `frontend/src/components/bots/PersonaCard.tsx` | component | transform (display, +new prop) | itself (pre-existing, appended feature) | exact |
| `frontend/src/lib/personas/personaRegistry.ts` | utility | transform | itself (`personasForSection`, existing helper to mirror) | exact |
| `frontend/src/lib/theme.ts` | config | transform | itself (existing `*_ACCENT`/`*_ACCENT_BG` constant pairs) | exact |
| `frontend/src/hooks/useBotPersonaWins.ts` (NEW) | hook | request-response | `frontend/src/hooks/useUserProfile.ts` | exact |
| `frontend/src/hooks/useStoreBotGame.ts` | hook | request-response | itself (`toStoreRequest`, existing mapper to extend) | exact |
| `frontend/src/api/client.ts` | service (API client) | request-response | `botsApi.storeGame` (same file, `botsApi` object) | exact |
| `frontend/src/types/bots.ts` | model (TS types) | transform | `StoreBotGameRequest`/`StoreBotGameResponse` types (existing, same file) | exact |
| `frontend/src/pages/Bots.tsx` | component (page) | request-response + transform | itself (existing single `useUserProfile()` call + prop-drill to `PersonaGrid`) | exact |
| `app/models/game.py` | model | CRUD | `time_control_str`/`white_accuracy_imported` (existing nullable columns, same file) | exact |
| `app/schemas/bots.py` | model (Pydantic schema) | request-response | `StoreBotGameRequest`/`RatingSource` (same file, existing bounded-string field pattern) | exact |
| `app/routers/bots.py` | route/controller | request-response | itself (`POST /bots/games`, existing single-route file) | exact |
| `app/services/store_bot_game_service.py` | service | CRUD (post-insert UPDATE) | itself (existing `created`-gated PGN/URL stamp block) | exact |
| `app/repositories/game_repository.py` | model/repository | CRUD + aggregation | `update_bot_game_pgn_and_url` (write) + `count_games_by_platform`/`stats_repository.query_results_by_time_control` (aggregation read) | exact |
| `alembic/versions/<ts>_add_persona_id_to_games.py` (NEW) | migration | batch | `20260718_084123_60d9b72c0eaa_add_accuracy_acpl_imported_to_games.py` (structure) — but note this phase's column needs NO backfill UPDATE, unlike that analog | role-match (analog backfills; new migration must NOT) |

## Pattern Assignments

### `frontend/src/components/bots/PersonaGrid.tsx` (component, transform)

**Analog:** itself, current version (full file read above, 101 lines)

**Imports pattern** (lines 10-20):
```tsx
import type { ReactElement } from 'react';
import { PersonaCard } from '@/components/bots/PersonaCard';
import { Button } from '@/components/ui/button';
import { InfoPopover } from '@/components/ui/info-popover';
import {
  STYLE_SECTION_ORDER,
  personasForSection,
  type Persona,
} from '@/lib/personas/personaRegistry';
import type { Style } from '@/lib/engine/styleOpeningLines';
import { ATTACKER_ACCENT, TRICKSTER_ACCENT, GRINDER_ACCENT, WALL_ACCENT } from '@/lib/theme';
```
After the transpose, add `RUNGS` (or a new `personasForRung`) to the `personaRegistry` import, and keep the `STYLE_ACCENT` record (lines 25-30) verbatim — its 4 keys become header-row cells instead of `<h2>` colors.

**Current per-style-section core pattern to REPLACE** (lines 75-89):
```tsx
{STYLE_SECTION_ORDER.map((style) => (
  <section key={style} data-testid={`bots-persona-section-${style.toLowerCase()}`}>
    <h2 className="mb-2 text-sm font-semibold tracking-wide" style={{ color: STYLE_ACCENT[style] }}>
      {style}
    </h2>
    <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
      {personasForSection(style).map((persona) => (
        <PersonaCard key={persona.id} persona={persona} onSelect={onSelectPersona} />
      ))}
    </div>
  </section>
))}
```

**Target shape** (rung-major, per UI-SPEC Layout & Interaction Notes): one `grid-cols-4` header row (`data-testid="bots-persona-header-${style.toLowerCase()}"` per cell, `STYLE_ACCENT[style]` color, replacing the old `bots-persona-section-*` testid) followed by `RUNGS.map(rung => STYLE_SECTION_ORDER.map(style => <PersonaCard .../>))` with no row label. New prop `winsByPersona: Record<string, number> | undefined` (Pattern 3, RESEARCH.md) threaded straight through to each `PersonaCard` as `winsForPersona={winsByPersona?.[persona.id]}` — no `useQuery` call added to this file.

**Prop interface pattern** (lines 32-40, unchanged shape, extend with one more prop):
```tsx
export interface PersonaGridProps {
  onSelectPersona: (persona: Persona) => void;
  onSelectCustom: () => void;
  playerRating: number | null;
  // NEW: winsByPersona: Record<string, number> | undefined;
}
```

---

### `frontend/src/components/bots/PersonaCard.tsx` (component, transform)

**Analog:** itself (full file, 62 lines)

**Imports pattern** (lines 17-19):
```tsx
import type { ReactElement } from 'react';
import type { Persona } from '@/lib/personas/personaRegistry';
import { placeholderAvatarFor, resolveAvatarSrc } from '@/lib/personas/personaAvatars';
```
Add: `import { Star } from 'lucide-react';` and `import { STAR_FILLED, STAR_EMPTY } from '@/lib/theme';`

**Prop interface + core pattern to extend** (lines 21-24, 31, 58-59):
```tsx
export interface PersonaCardProps {
  persona: Persona;
  onSelect: (persona: Persona) => void;
  // NEW: winsForPersona?: number;
}
...
<span className="text-sm font-medium text-foreground">{persona.name}</span>
<span className="text-sm text-muted-foreground">{persona.calibratedLabel}</span>
{/* NEW: stars row appended here, see RESEARCH.md Code Examples for the
    PersonaStars sub-component shape (Math.min(wins, MAX_DISPLAY_STARS),
    aria-label on the wrapping <span>, 3 Star icons at size={14}) */}
```
`aria-label` on the outer `<button>` (line 39) stays persona-identity-only — do NOT append win count into that string (UI-SPEC explicitly calls for two separate `aria-label`s, one on the button, one on the stars-row `<span>`).

---

### `frontend/src/lib/personas/personaRegistry.ts` (utility, transform)

**Analog:** itself — `personasForSection` (lines 473-474) is the exact abstraction level to mirror for the new rung-major accessor:
```ts
// Source: frontend/src/lib/personas/personaRegistry.ts, lines 473-474
export function personasForSection(style: Style): Persona[] {
  return RUNGS.map((rung) => PERSONA_REGISTRY[personaId(style, rung)]);
}
```
`RUNGS` is currently module-private (line 60: `const RUNGS: readonly Rung[] = [800, 1000, 1200, 1400, 1600, 1800];`). Add either `export const RUNGS` directly, or (mirrors `personasForSection`'s abstraction) a new `personasForRung(rung: Rung): Persona[]` returning the 4 personas at that rung in `STYLE_SECTION_ORDER` order — Pitfall 1 in RESEARCH.md. `personaId(style, rung)` (line 120) is the private helper both accessors already share.

---

### `frontend/src/lib/theme.ts` (config, transform)

**Analog:** itself — existing accent + `_BG` constant-pair convention (e.g. lines 80-85, 93-96):
```ts
// Source: frontend/src/lib/theme.ts, lines 80-85
export const MAIA_ACCENT = 'oklch(0.58 0.20 290)'; // violet
export const MAIA_ACCENT_BG = 'oklch(0.58 0.20 290 / 0.14)';
```
Add two NEW named constants (do NOT reuse `FLAWCHESS_ENGINE_ACCENT` despite the matching hue — see RESEARCH.md Don't-Hand-Roll and UI-SPEC Color section):
```ts
export const STAR_FILLED = 'oklch(0.78 0.14 80)'; // gold/amber (same hue/chroma as FLAWCHESS_ENGINE_ACCENT, deliberately independent constant)
export const STAR_EMPTY = 'oklch(0.45 0 0)'; // mid-grey outline
```

---

### `frontend/src/hooks/useBotPersonaWins.ts` (NEW hook, request-response)

**Analog:** `frontend/src/hooks/useUserProfile.ts` (full file, 14 lines) — copy verbatim shape:
```ts
// Source: frontend/src/hooks/useUserProfile.ts
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { UserProfile } from '@/types/users';

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
```
New file substitutes `queryKey: ['botPersonaWins']`, `'/bots/persona-wins'`, and a `Record<string, number>` (or typed `PersonaWinsResponse`) return type. Same 5-minute `staleTime` (win counts only change on game-finish).

---

### `frontend/src/hooks/useStoreBotGame.ts` (hook, request-response)

**Analog:** itself — `toStoreRequest` (lines 39-48), the pure mapper to extend with one line:
```ts
// Source: frontend/src/hooks/useStoreBotGame.ts, lines 39-48
export function toStoreRequest(entry: PendingStoreEntry): StoreBotGameRequest {
  return {
    game_uuid: entry.gameUuid,
    pgn: entry.pgn,
    user_color: entry.settings.userColor,
    bot_elo: entry.settings.botElo,
    play_style_blend: entry.settings.blend,
    tc_preset: toBackendTcStr(entry.settings.baseSeconds, entry.settings.incrementSeconds),
    // NEW: persona_id: entry.settings.personaId ?? null,
  };
}
```
Pitfall 3 (RESEARCH.md): do NOT tighten `isValidPendingEntry`'s shape-check to require `persona_id` — old queued localStorage entries predate the field and must still round-trip.

---

### `frontend/src/api/client.ts` (API client, request-response)

**Analog:** itself — `botsApi` object (line 231-234):
```ts
// Source: frontend/src/api/client.ts, lines 231-234
export const botsApi = {
  storeGame: (data: StoreBotGameRequest) =>
    apiClient.post<StoreBotGameResponse>('/bots/games', data).then(r => r.data),
};
```
Add a sibling method, e.g. `getPersonaWins: () => apiClient.get<PersonaWinsResponse>('/bots/persona-wins').then(r => r.data)` — same object, same `.then(r => r.data)` unwrap convention.

---

### `app/models/game.py` (model, CRUD)

**Analog:** itself — existing nullable, no-CHECK, no-default columns (lines 129, 177-180):
```python
# Source: app/models/game.py, line 129
time_control_str: Mapped[str | None] = mapped_column(String(50))  # raw string e.g. "600+0"

# Source: app/models/game.py, lines 177-180
white_accuracy_imported: Mapped[float | None] = mapped_column(REAL, nullable=True)
black_accuracy_imported: Mapped[float | None] = mapped_column(REAL, nullable=True)
```
New column: `persona_id: Mapped[str | None] = mapped_column(String(30), nullable=True)` — no `ForeignKey` (no `personas` table exists, registry is frontend-only TS per RESEARCH.md A1), no CHECK, no default.

---

### `app/schemas/bots.py` (schema, request-response)

**Analog:** itself — the `_MAX_TC_PRESET_LENGTH` length-bound pattern (lines 25-29, 44) is the EXACT precedent to copy for `persona_id`:
```python
# Source: app/schemas/bots.py, lines 25-29, 44
# CR-01: must never overflow games.time_control_str String(50) (app/models/game.py).
# tc_preset flows unmodified through normalize_flawchess_game -> NormalizedGame.time_control_str
# -> _flush_batch's INSERT; an unbounded value raises an unhandled 500 (Postgres DataError),
# not the intended 422.
_MAX_TC_PRESET_LENGTH = 50
...
tc_preset: str = Field(max_length=_MAX_TC_PRESET_LENGTH)
```
New: `_MAX_PERSONA_ID_LENGTH = 30` constant + `persona_id: str | None = Field(default=None, max_length=_MAX_PERSONA_ID_LENGTH)` on `StoreBotGameRequest`. New response schema `PersonaWinsResponse` (or a plain `dict[str, int]` response_model, matching `count_games_by_platform`'s dict-return shape) for `GET /bots/persona-wins`.

---

### `app/routers/bots.py` (router, request-response)

**Analog:** itself — the single existing route (full file, 39 lines) is the template for the new `GET /bots/persona-wins` route:
```python
# Source: app/routers/bots.py, lines 21-26 (existing POST route to mirror)
@router.post("/games", response_model=StoreBotGameResponse, status_code=200)
async def store_game(
    data: StoreBotGameRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> StoreBotGameResponse:
```
New GET route follows the identical `current_active_user` + `get_async_session` dependency pair, no `user_id` request param (V4 — user_id comes only from the JWT), thin pass-through to a service/repository call, no try/except needed for a pure read (mirrors `stats.py` router thinness).

---

### `app/services/store_bot_game_service.py` (service, CRUD)

**Analog:** itself — the existing `created`-gated post-insert block (lines 157-187) is the EXACT pattern to extend (RESEARCH.md Pattern 1):
```python
# Source: app/services/store_bot_game_service.py, lines 157-187 (existing)
if created:
    session.add(BotGameSettings(...))
    stamped_pgn = stamp_bot_game_headers(...)
    await game_repository.update_bot_game_pgn_and_url(
        session, game_id, stamped_pgn, build_bot_game_url(game_id)
    )
    # NEW (Phase 185): persist persona_id here too, same created-gate.
    if request.persona_id is not None:
        await game_repository.update_bot_game_persona_id(session, game_id, request.persona_id)
```
Same `try/except Exception: sentry_sdk.set_context(...); sentry_sdk.capture_exception(); raise` wrapper (lines 145, 188-193) already covers this new call — no new exception handling needed, it's inside the existing `try` block.

---

### `app/repositories/game_repository.py` (repository, CRUD + aggregation)

**Analog A (write):** `update_bot_game_pgn_and_url` (lines 104-125) — exact shape for the new `update_bot_game_persona_id`:
```python
# Source: app/repositories/game_repository.py, lines 104-125
async def update_bot_game_pgn_and_url(
    session: AsyncSession, game_id: int, pgn: str, platform_url: str
) -> None:
    """... Does NOT commit — the caller owns the transaction (D-10)."""
    await session.execute(
        update(Game).where(Game.id == game_id).values(pgn=pgn, platform_url=platform_url)
    )
```
New: `update_bot_game_persona_id(session, game_id, persona_id) -> None` — single-column `update(Game).where(Game.id == game_id).values(persona_id=persona_id)`, no commit.

**Analog B (aggregation read):** `count_games_by_platform` (lines 265-273, same file) is the closest same-file precedent; `stats_repository.query_results_by_time_control`'s `win_cond`/`func.count().filter(...)` (lines 156-179 of `stats_repository.py`) is the byte-identical win-condition to reuse:
```python
# Source: app/repositories/stats_repository.py, lines 156-165 (win_cond to copy verbatim)
win_cond = or_(
    and_(Game.result == "1-0", Game.user_color == "white"),
    and_(Game.result == "0-1", Game.user_color == "black"),
)

# Source: app/repositories/game_repository.py, lines 265-273 (GROUP BY shape to mirror)
async def count_games_by_platform(session: AsyncSession, user_id: int) -> dict[str, int]:
    result = await session.execute(
        select(Game.platform, func.count())
        .select_from(Game)
        .where(Game.user_id == user_id)
        .group_by(Game.platform)
    )
    return {row[0]: row[1] for row in result.all()}
```
New: `count_wins_by_persona(session, user_id) -> dict[str, int]`:
```python
win_cond = or_(
    and_(Game.result == "1-0", Game.user_color == "white"),
    and_(Game.result == "0-1", Game.user_color == "black"),
)
stmt = (
    select(Game.persona_id, func.count().filter(win_cond).label("wins"))
    .where(
        Game.user_id == user_id,
        Game.persona_id.is_not(None),
        Game.platform == "flawchess",  # defense-in-depth, Open Question 2
    )
    .group_by(Game.persona_id)
)
result = await session.execute(stmt)
return {row[0]: row[1] for row in result.all()}
```
No new index needed (Pitfall 5) — `ix_games_user_played_at (user_id, played_at DESC)` already makes the `user_id` predicate cheap at per-user scale.

---

### `alembic/versions/<timestamp>_add_persona_id_to_games.py` (migration, batch)

**Analog:** `20260718_084123_60d9b72c0eaa_add_accuracy_acpl_imported_to_games.py` (full file) — SAME `op.add_column` mechanics, but this phase's migration must be MUCH simpler: no copy-UPDATE, no null-UPDATE, no full-table rewrite (Pitfall 4).

```python
# Source: alembic/versions/20260718_084123_60d9b72c0eaa_..._to_games.py, upgrade()
# (structure to mirror, NOT the backfill logic — persona_id gets NO backfill)
def upgrade() -> None:
    op.add_column("games", sa.Column("persona_id", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("games", "persona_id")
```
No `server_default`, no `UPDATE` statement — a bare metadata-only `ADD COLUMN nullable=True` stays fast even at ~718k prod rows (Pitfall 4 is explicit: do NOT add a default or backfill out of habit).

## Shared Patterns

### Auth / user-scoping (backend)
**Source:** `app/routers/bots.py` lines 22-26, 29 (`current_active_user` dependency; user_id never taken from request body)
**Apply to:** the new `GET /bots/persona-wins` route — same dependency pair, no `user_id` query param (ASVS V4, same comment convention: "user_id is derived from the authenticated JWT — never from the request body").

### Win/draw/loss determination (backend)
**Source:** `app/repositories/stats_repository.py` lines 156-165 (`win_cond` `or_(and_(...), and_(...))` expression)
**Apply to:** `count_wins_by_persona` in `game_repository.py` — copy verbatim, do not redefine a third divergent copy of this logic (project has a history of color-parity bugs).

### Single-fetch-then-prop-drill (frontend)
**Source:** `frontend/src/pages/Bots.tsx`'s existing single `useUserProfile()` call feeding `playerRating` into `PersonaGrid` (RESEARCH.md Pattern 3, verified against `PersonaDetailSurface.tsx`'s doc comment)
**Apply to:** the new `useBotPersonaWins()` call — ONE call in `Bots.tsx`, threaded down through `PersonaGrid` → `PersonaCard` as `winsByPersona`/`winsForPersona` plain props. Do NOT call `useQuery` inside either component (breaks existing `render(<PersonaGrid .../>)` tests with no `QueryClientProvider`).

### Length-bounded client-supplied string fields (backend)
**Source:** `app/schemas/bots.py` lines 25-29, 44 (`_MAX_TC_PRESET_LENGTH` / `tc_preset: str = Field(max_length=...)`), mirrored by `MAX_BOT_PGN_LENGTH` (line 20)
**Apply to:** `persona_id: str | None = Field(default=None, max_length=_MAX_PERSONA_ID_LENGTH)` — same CR-01-motivated pattern (bound at the Pydantic boundary so a malformed value 422s instead of crashing the INSERT/UPDATE with an unhandled Postgres `DataError`).

### Post-insert targeted UPDATE gated on `created` (backend)
**Source:** `app/services/store_bot_game_service.py` lines 157-187 (existing `if created:` block wrapping the PGN/URL stamp)
**Apply to:** `persona_id` persistence — extend the SAME `if created:` block with one more repository call, preserving D-11 idempotency (a duplicate resubmit must not re-write anything).

### Named theme constants, not inline colors (frontend)
**Source:** `frontend/src/lib/theme.ts`'s existing `*_ACCENT`/`*_ACCENT_BG` constant-pair convention (e.g. `MAIA_ACCENT`/`MAIA_ACCENT_BG`, lines 80-85)
**Apply to:** `STAR_FILLED`/`STAR_EMPTY` — new, independently-declared constants (do not alias `FLAWCHESS_ENGINE_ACCENT` even though the gold value numerically matches).

## No Analog Found

None — every file in this phase's scope has a same-file or cross-file precedent already shipped in Phases 167/171/178/183/184.

## Metadata

**Analog search scope:** `frontend/src/components/bots/`, `frontend/src/hooks/`, `frontend/src/lib/`, `frontend/src/api/`, `frontend/src/pages/Bots.tsx`, `app/models/game.py`, `app/schemas/bots.py`, `app/routers/bots.py`, `app/services/store_bot_game_service.py`, `app/repositories/game_repository.py`, `app/repositories/stats_repository.py`, `alembic/versions/`
**Files scanned:** 14 target files + 5 supporting analog files (`stats_repository.py`, `useUserProfile.ts`, migration `60d9b72c0eaa`, `client.ts`, `theme.ts`)
**Pattern extraction date:** 2026-07-22
