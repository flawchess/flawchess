# Phase 185: Bots roster transpose + win stars - Research

**Researched:** 2026-07-22
**Domain:** React grid layout refactor (frontend-only) + a small server-side aggregation feature (nullable FK-adjacent column, Alembic migration, GET aggregation endpoint, TanStack Query hook)
**Confidence:** HIGH

## Summary

This phase has no CONTEXT.md (no `/gsd-discuss-phase` has run yet) — the ROADMAP.md phase description (copied verbatim below) is the only source of locked scope. It bundles two independent, low-risk changes to the already-shipped Phase 183/184 Bots page:

1. **Grid transpose (frontend-only):** `PersonaGrid.tsx` currently renders 4 `<section>` blocks (one per style), each containing that style's 6 personas ascending by rung, in a `grid-cols-3 sm:grid-cols-6` layout with a per-section `<h2>` heading. The new layout inverts the axes: one header row of 4 style names (colored in their existing accent constants) as columns, and 6 rung rows (800 top, 1800 bottom) with no row labels — `PersonaCard`'s own tint/ELO label carries identity. This is a pure DOM/CSS re-shape of already-fetched, already-typed data (`PERSONA_REGISTRY`); no new data source.

2. **Win-star tracking (full-stack):** a new nullable `games.persona_id` column populated only when a persona game finishes (custom-mode games stay `NULL`, pre-existing games are never backfilled), a small `GET` aggregation endpoint counting wins per persona for the current user, and a frontend stars row on `PersonaCard` rendering `min(wins, 3)` gold stars plus grey-outline stars for the remainder.

Both changes build directly on shipped Phase 183/184 code (`personaRegistry.ts`, `PersonaGrid.tsx`, `PersonaCard.tsx`, `useBotGame.ts`'s existing `personaId?: PersonaId` field, `store_bot_game_service.py`, `games` table). No new library, no new architectural layer — this is a same-shape extension of the existing bot-game-storage and Bots-page-rendering code paths.

**Primary recommendation:** Do the two halves as (at least) two separate plans/waves — they touch disjoint files and have no dependency on each other. Grid transpose is frontend-test-heavy (existing `PersonaGrid.test.tsx` DOM-order assertions must be rewritten, not just extended). Win-star tracking spans migration -> schema -> service -> router -> frontend hook -> `PersonaCard`, and should follow the exact `bot_game_settings` (Phase 167) precedent for the migration/write side and the `stats_repository.py` win/draw/loss `func.count().filter(...)` precedent for the read side.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Grid transpose (rows/columns, header row) | Browser / Client | — | Pure presentational re-layout of already-loaded `PERSONA_REGISTRY` data; no data fetch involved |
| `persona_id` capture at game-finish | API / Backend | Browser / Client | Client already carries `personaId` in `BotGameSettings`/`useBotGame.ts` (Phase 183) — this phase only needs to add it to the wire request + persist it. Server remains the source of truth for what gets written (mirrors D-05/D-08 pattern: server never trusts client for rating/platform, but persona_id here IS a client-supplied value since only the client knows which persona the user picked — validate length/shape server-side, do not derive it) |
| `persona_id` schema + persistence | Database / Storage | API / Backend | Nullable column on `games`, no FK (no `personas` table exists — the registry is a frontend-only TS module); migration + model change |
| Win aggregation | API / Backend | Database / Storage | `SELECT persona_id, COUNT(*) FILTER (win_cond) GROUP BY persona_id` scoped to `user_id` — same shape as `stats_repository.query_results_by_time_control` |
| Win-count fetch (one call for the whole roster) | Browser / Client | API / Backend | One `useQuery` hook at `Bots.tsx` page level (mirrors the existing single `useUserProfile()` call pattern that already feeds `playerRating` into `PersonaGrid`) — NOT fetched per-card, to keep `PersonaCard`/`PersonaGrid` prop-driven and testable without a `QueryClientProvider` wrapper |
| Star rendering (gold/grey, cap at 3) | Browser / Client | — | Pure display logic (`Math.min(wins, 3)`) inside `PersonaCard` |

## Standard Stack

No new libraries needed for either half. Reuse:

| Library | Version (installed) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `lucide-react` | 1.21.0 [VERIFIED: node_modules/lucide-react/package.json] | `Star` icon for the stars row | Already the project's sole icon library (used throughout `components/bots/*`); has a single `Star` glyph that supports `fill="currentColor"` for filled-vs-outline via a `stroke`/`fill` prop toggle — no need for two different icon names |
| `@tanstack/react-query` | already in use | Win-count fetch hook | Matches `useUserProfile.ts`'s exact shape (`useQuery` + `apiClient.get` + `staleTime`) |
| SQLAlchemy 2.x async / Alembic | already in use | `persona_id` column + migration | Matches `bot_game_settings` (Phase 167) and `*_imported` columns (Phase 178) migration precedents |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain nullable `String` column with NO `CHECK` constraint on `games.persona_id` | A `CHECK (persona_id IN ('attacker-800', ...))` enumerating all 24 current ids | CLAUDE.md's enum-column rule favors `TEXT + CHECK` for low-cardinality domain columns, but the persona roster is a **frontend-only, milestone-evolving** registry (species/rungs can change; see Phase 183/184 history of renaming/adjusting personas) — a CHECK list would need a new migration every roster edit. Recommend a plain nullable column with a **length bound only** (Pydantic `Field(max_length=...)` on the request schema, mirroring `tc_preset`'s `_MAX_TC_PRESET_LENGTH` CR-01 precedent), not a value-enumerated CHECK. Flag this trade-off for `/gsd-discuss-phase` — it's a genuine judgment call, not a locked decision in the phase description. |
| A dedicated `bots_repository.py` / `bots_service.py` for the win-aggregation query | Add the query function to the existing `game_repository.py` (it already owns `count_games_by_platform`, an analogous per-column-value GROUP BY) | Either is defensible; `game_repository.py` already has the closest existing precedent (`count_games_by_platform`) and avoids a new near-empty file for one function. Router layer should still go through a thin service call (or, if genuinely trivial, call the repository directly per the "small aggregation endpoint" framing in the phase description) — CLAUDE.md's routers/services/repositories split still applies; a repository-only call from the router violates "no SQL in services" trivially (there's no SQL in the router either way) but the project's actual precedent (`stats.py` -> `stats_service.py` -> `stats_repository.py`) argues for keeping the thin service layer for consistency. |
| Backend caps wins at 3 via `LEAST(count, 3)` in SQL | Backend returns the raw win count; frontend applies `Math.min(wins, 3)` | The phase description says both ("3 is a display cap only (LEAST(count,3))" directly followed by "frontend renders min(wins, 3)"). Recommend returning the **raw count** from the endpoint (more future-proof — a hover tooltip or "12 wins" detail view is a one-line change later) and doing the cap in the frontend, consistent with "frontend renders min(wins, 3)". This should be confirmed at discuss/plan time since the phase text is genuinely ambiguous on which layer owns the cap. |

## Package Legitimacy Audit

No new external packages are introduced by this phase. `lucide-react` is already an installed, verified dependency (1.21.0, confirmed via `node_modules/lucide-react/package.json`). No `Package Legitimacy Audit` table is needed — skip condition met (no new packages).

## Architecture Patterns

### System Architecture Diagram

```
Frontend: PersonaGrid transpose (no new data flow)
──────────────────────────────────────────────────
PERSONA_REGISTRY (personaRegistry.ts, unchanged)
        │
        ▼
PersonaGrid.tsx — re-shaped iteration: RUNGS (rows, ascending) × STYLE_SECTION_ORDER (columns)
        │            header row: 4 style names in accent colors, no row labels
        ▼
PersonaCard.tsx (per cell) — unchanged vertical stack (avatar/name/ELO) + NEW stars row


Backend: persona_id capture + win aggregation
──────────────────────────────────────────────────
Bots.tsx (setup) ──selects persona──▶ useBotGame.ts (BotGameSettings.personaId, ALREADY threaded)
        │
        ▼ (game finishes)
useStoreBotGame.ts / botPendingStore.ts
        │  toStoreRequest() — ADD persona_id: entry.settings.personaId ?? null
        ▼
POST /bots/games  (app/routers/bots.py)
        │
        ▼
store_bot_game_service.store_bot_game()
        │  after game_id resolved (mirrors the existing stamp_bot_game_headers /
        │  update_bot_game_pgn_and_url post-insert UPDATE, gated on created=True
        │  for the same D-11 idempotency reason)
        ▼
game_repository.update_bot_game_persona_id(session, game_id, persona_id)  [NEW]
        │
        ▼
games.persona_id  (NEW nullable column, Alembic migration)


Frontend: win-count fetch + star render
──────────────────────────────────────────────────
Bots.tsx ── single useQuery(['botPersonaWins']) call [NEW hook, mirrors useUserProfile.ts]
        │
        ▼
GET /bots/persona-wins  (app/routers/bots.py)  [NEW]
        │
        ▼
game_repository.count_wins_by_persona(session, user_id)  [NEW — mirrors
        │  stats_repository.query_results_by_time_control's win_cond/GROUP BY shape]
        ▼
SELECT persona_id, COUNT(*) FILTER (WHERE win_cond) AS wins
FROM games WHERE user_id = :user_id AND persona_id IS NOT NULL
GROUP BY persona_id
        │
        ▼
Bots.tsx passes winsByPersona: Record<string, number> down through
PersonaGrid -> PersonaCard (prop-drilled, NOT fetched per-card)
        │
        ▼
PersonaCard renders Math.min(wins, 3) gold Star + (3 - shown) grey outline Star
```

### Recommended Project Structure

No new directories. Files touched:
```
app/
├── models/game.py                          # + persona_id column
├── schemas/bots.py                         # + persona_id on StoreBotGameRequest, + PersonaWinsResponse
├── routers/bots.py                         # + GET /bots/persona-wins
├── services/store_bot_game_service.py      # thread persona_id through to the post-insert UPDATE
└── repositories/game_repository.py         # + update_bot_game_persona_id, + count_wins_by_persona

alembic/versions/
└── <timestamp>_add_persona_id_to_games.py  # new nullable column, no CHECK, no backfill

frontend/src/
├── components/bots/PersonaGrid.tsx         # transpose: rows=rungs, cols=styles, header row
├── components/bots/PersonaCard.tsx         # + stars row, + winsForPersona prop
├── components/bots/__tests__/PersonaGrid.test.tsx   # DOM-order assertions REWRITTEN (not extended)
├── components/bots/__tests__/PersonaCard.test.tsx   # + stars-row assertions
├── lib/personas/personaRegistry.ts         # + export RUNGS (or a `personasForRung(rung)` helper)
├── hooks/useBotPersonaWins.ts               # NEW — mirrors useUserProfile.ts shape
├── hooks/useStoreBotGame.ts                 # toStoreRequest(): + persona_id field
├── types/bots.ts                            # + persona_id on StoreBotGameRequest, + PersonaWinsResponse type
├── api/client.ts                            # + botsApi.getPersonaWins()
└── pages/Bots.tsx                           # + single useBotPersonaWins() call, thread winsByPersona down
```

### Pattern 1: Post-insert targeted UPDATE for a value only the client can supply, gated on `created`

**What:** `store_bot_game_service.py` already has this exact shape for `platform_url`/PGN `Site` header (quick-260714-qaj): they need the auto-increment `games.id`, which only exists post-INSERT, so they're written via a second targeted `UPDATE`, and ONLY when `created` is `True` (D-11 idempotency — a duplicate re-submit must not re-write anything).

**When to use:** `persona_id` doesn't strictly need the post-insert `id` (it's not derived from it), so it COULD instead be added directly to `NormalizedGame` and threaded through `_flush_batch`'s bulk INSERT. However, that touches `app/schemas/normalization.py`, `app/services/normalization.py` (both `normalize_flawchess_game` AND the base `NormalizedGame` model shared by chess.com/lichess normalizers, which would need a default `None` for those paths too), and `import_service._flush_batch`'s column-mapping — a much larger blast radius than a targeted single-column UPDATE scoped to the `created=True` branch that already exists for the PGN/URL stamp.

**Recommendation:** extend the EXISTING post-insert `created`-gated block in `store_bot_game_service.store_bot_game()` with one more repository call (`update_bot_game_persona_id`), rather than touching `NormalizedGame`/`_flush_batch`. Keeps the change surgical and consistent with the D-11 idempotency guard already in place.

**Example (existing code to extend, `app/services/store_bot_game_service.py`):**
```python
# Source: app/services/store_bot_game_service.py, lines 157-187 (existing, Phase 167/qaj)
if created:
    session.add(BotGameSettings(...))
    stamped_pgn = stamp_bot_game_headers(...)
    await game_repository.update_bot_game_pgn_and_url(
        session, game_id, stamped_pgn, build_bot_game_url(game_id)
    )
    # NEW (Phase 185): persist persona_id here too, same created-gate,
    # same "no data no-op on duplicate resubmit" reasoning.
    if request.persona_id is not None:
        await game_repository.update_bot_game_persona_id(session, game_id, request.persona_id)
```

### Pattern 2: Win/draw/loss via `func.count().filter(win_cond)`, GROUP BY

**What:** `stats_repository.query_results_by_time_control`/`query_results_by_color` build a `win_cond`/`draw_cond`/`loss_cond` boolean expression from `Game.result` + `Game.user_color`, then `func.count().filter(win_cond).label("wins")` in a single `GROUP BY` query.

**When to use:** identical shape for `count_wins_by_persona`, just `GROUP BY Game.persona_id` instead of `Game.time_control_bucket`, filtered to `Game.persona_id.is_not(None)` (mirrors `Game.time_control_bucket.is_not(None)` exactly) and (implicitly) `Game.platform == 'flawchess'` — though since `persona_id` is only ever set on flawchess games, the `platform` filter is likely redundant defense-in-depth, not strictly required.

**Example:**
```python
# Source: app/repositories/stats_repository.py, lines 156-179 (existing pattern to mirror)
win_cond = or_(
    and_(Game.result == "1-0", Game.user_color == "white"),
    and_(Game.result == "0-1", Game.user_color == "black"),
)
stmt = (
    select(Game.persona_id, func.count().filter(win_cond).label("wins"))
    .where(Game.user_id == user_id, Game.persona_id.is_not(None))
    .group_by(Game.persona_id)
)
```

### Pattern 3: Single-fetch-at-page-level, prop-drill down to leaf components

**What:** `Bots.tsx` already makes exactly ONE `useUserProfile()` call and derives `playerRating` (`profile?.lichess_blitz_equivalent_rating ?? null`), passed as a plain prop into `PersonaGrid`. `PersonaDetailSurface.tsx`'s own doc comment explicitly states it reads the SAME `useUserProfile()` call via a prop, "not a second hook call here."

**When to use:** the new win-count fetch MUST follow this exact convention: one `useQuery` call in `Bots.tsx`, threaded down through `PersonaGrid` -> `PersonaCard` as a plain prop (e.g. `winsByPersona: Record<string, number> | undefined`). Do NOT call `useQuery` inside `PersonaCard` itself.

**Why this matters here specifically:** `PersonaGrid.test.tsx` and `PersonaCard.test.tsx` currently render these components directly with `render(<PersonaGrid ... />)` — no `QueryClientProvider` wrapper. If either component called `useQuery` internally, every existing test would start failing with "No QueryClient set" errors. Prop-drilling avoids this entirely and keeps the components pure/testable, matching the existing test setup.

### Anti-Patterns to Avoid

- **Fetching win counts per-card:** 24 separate network calls (one per `PersonaCard`) instead of one roster-wide aggregation call. The phase description explicitly says "a small aggregation endpoint returning wins per persona" (singular, roster-wide).
- **Extending `PersonaGrid.test.tsx`'s existing DOM-order test instead of rewriting it:** the current test hard-codes `STYLE_SECTION_ORDER.flatMap(personasForSection)` as the expected DOM order (style-major). After the transpose, DOM order becomes rung-major (`RUNGS.flatMap(rung => STYLE_SECTION_ORDER.map(...))`). Patching the assertion in place, without noticing the semantic order flip, would either false-pass (if row/column iteration accidentally produces the same flat order — it won't, since 6×4 grid, not 4×6) or silently assert the WRONG order.
- **A `CHECK` constraint enumerating all 24 current persona ids on `games.persona_id`:** the persona roster is a frontend-only registry that has already been renamed/adjusted across Phases 183/184 sub-plans; a DB-level enumerated CHECK would force a migration on every roster edit. See Alternatives Considered above.
- **Trusting the client for anything OTHER than `persona_id` itself in the store-game request:** `persona_id` is a legitimate exception to the "server derives everything" pattern (D-05/D-08/D-14 in `StoreBotGameRequest`'s docstring) — the server has no independent way to know which persona a Custom-mode-free user picked. But bound its length/shape (e.g. `Field(max_length=30)`, optionally a regex like `^[a-z]+-\d{3,4}$`) so a malformed value can't overflow the column or corrupt the aggregation query the way `tc_preset`'s CR-01 bug did.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Win/draw/loss determination from `result` + `user_color` | A new ad-hoc conditional | The EXACT `win_cond` expression already defined twice in `stats_repository.py` (`or_(and_(result=="1-0", color=="white"), and_(result=="0-1", color=="black")))` | Byte-identical logic already exists and is tested; a third divergent copy risks a sign/color bug (this project has hit several color-parity bugs historically — e.g. `_clock_presence_by_color`'s `start_white_to_move` fix in `normalize_flawchess_game`) |
| Gold/grey star rendering | A custom SVG or two different icon imports for filled/outline | `lucide-react`'s single `Star` component, toggling `fill`/`className` (`fill="currentColor"` for gold, `fill="none"` + a muted stroke color for grey-outline) | One icon, two visual states via props — matches the project's existing icon-toggle patterns (e.g. `Volume2`/`VolumeX` in `GameControls.tsx` uses two icons because the glyphs genuinely differ, but a filled/outline toggle of the SAME glyph is a `fill` prop change, not a second icon) |
| Session-color constants for the stars | Inline `text-yellow-500`/hex literals in `PersonaCard.tsx` | New named constants in `frontend/src/lib/theme.ts` (CLAUDE.md: "Theme constants in theme.ts") | CLAUDE.md's theme-constant rule is explicit: win/loss-adjacent semantic colors must live in `theme.ts`. The existing `FLAWCHESS_ENGINE_ACCENT` (gold/amber, oklch hue 80) is a close visual match but carries "FlawChess engine branding" semantics, not "win indicator" — recommend a NEW pair of constants (e.g. `STAR_FILLED`/`STAR_EMPTY`) rather than reusing `FLAWCHESS_ENGINE_ACCENT` for an unrelated semantic meaning. |

**Key insight:** Every non-trivial piece of this phase (win determination, persona-id round-trip via a post-insert UPDATE, single-fetch-then-prop-drill) already has a byte-for-byte precedent shipped in Phases 167/183/184. The main risk is not "what to build" but "which existing precedent to copy exactly" and "don't let the grid-transpose test rewrite silently assert the wrong order."

## Common Pitfalls

### Pitfall 1: `RUNGS` is not exported from `personaRegistry.ts`

**What goes wrong:** `PersonaGrid.tsx` needs to iterate rungs (rows) outer, styles (columns) inner. `RUNGS` (`const RUNGS: readonly Rung[] = [800, 1000, ...]`) is currently a module-private constant in `personaRegistry.ts` — only `personasForSection` and the internal `personaId()` helper use it.
**Why it happens:** Phase 183 only needed style-major iteration (`personasForSection`), so rung-major iteration was never a public seam.
**How to avoid:** Either `export const RUNGS` directly, or (cleaner, mirrors `personasForSection`'s existing abstraction level) add a new `personasForRung(rung: Rung): Persona[]` helper next to `personasForSection`, returning the 4 personas at that rung in `STYLE_SECTION_ORDER` order. The grid then does `RUNGS.map(rung => personasForRung(rung))` without ever touching `PERSONA_REGISTRY` directly.
**Warning signs:** A planner reaching for `Object.values(PERSONA_REGISTRY)` and manually filtering/sorting by rung inside `PersonaGrid.tsx` — this duplicates registry-internal ordering logic in a component, the exact anti-pattern `personasForSection` was created to prevent.

### Pitfall 2: The existing `PersonaGrid.test.tsx` DOM-order test WILL fail after the transpose, by design

**What goes wrong:** `it('renders exactly 24 persona cards, grouped into 4 sections in STYLE_SECTION_ORDER (DOM order)', ...)` asserts `actualIds` equals `STYLE_SECTION_ORDER.flatMap(personasForSection)` — i.e. all 6 Attacker cards, then all 6 Trickster cards, etc. After the transpose this is categorically wrong (DOM order becomes rung-major: row 1 = one persona per style at rung 800, row 2 = rung 1000, ...).
**Why it happens:** the test encodes the CURRENT layout's DOM order as a correctness invariant; the phase's whole point is to change that invariant.
**How to avoid:** rewrite (not patch) this test's expected-order construction to `RUNGS.flatMap(rung => STYLE_SECTION_ORDER.map(style => personaId(style, rung)))` (or via the new `personasForRung` helper). Also re-verify: `data-testid="bots-persona-section-${style}"` (currently one per style, wrapping 6 cards) has no natural equivalent in the transposed layout — decide whether style-section test-ids move to the header-row cells or are dropped in favor of column-position assertions.
**Warning signs:** Running the full suite and seeing this specific test fail is EXPECTED and does not indicate a bug — it indicates the test needs rewriting as part of this phase's own scope, not a regression to chase down separately.

### Pitfall 3: `isValidSettingsShape` in `botPendingStore.ts` doesn't validate `personaId`, so adding `persona_id` to the wire format needs care at the `toStoreRequest` mapping site, not the storage-shape validator

**What goes wrong:** `PendingStoreEntry.settings` is `BotGameSettings` (already has `personaId?: PersonaId` from Phase 183), but `isValidSettingsShape()` only checks `botElo`/`blend`/`baseSeconds`/`incrementSeconds`/`userColor` — `personaId` is optional and untyped-checked there (correctly, since it's optional). The risk is in `useStoreBotGame.ts`'s `toStoreRequest()`, which currently does NOT read `entry.settings.personaId` at all.
**Why it happens:** `toStoreRequest` was written in Phase 170, before `personaId` existed on `BotGameSettings` (added Phase 183) — it was never updated because nothing consumed it server-side until now.
**How to avoid:** add exactly one line to `toStoreRequest`: `persona_id: entry.settings.personaId ?? null`. Confirm the Pydantic schema field is `persona_id: str | None = None` (not required) so old queued `PendingStoreEntry` JSON blobs already sitting in a user's `localStorage` from BEFORE this phase (missing the field entirely, since `JSON.stringify` drops `undefined` keys) still round-trip correctly — `isValidPendingEntry`'s existing shape-check must NOT be tightened to require `persona_id`.
**Warning signs:** a returning user with a pre-existing pending-store queue entry (RESUME-02's queue, capped at 10 entries, can persist across a deploy) hitting a 422 on the next drain because the request schema suddenly requires a field their stale localStorage entry doesn't have.

### Pitfall 4: `games` table is large (~718k rows on prod) — column-add semantics matter

**What goes wrong:** Postgres `ALTER TABLE ... ADD COLUMN` with no `DEFAULT` (or a `DEFAULT NULL`) is a fast, metadata-only operation that does NOT rewrite the table — but adding a column WITH a non-null default, or immediately backfilling it with an `UPDATE`, DOES trigger a full-table rewrite (as the Phase 178 `*_imported` migration explicitly does, and calls out in its own docstring: "this is a full-table rewrite on `games` (~718k rows on prod)").
**Why it happens:** `persona_id` has no meaningful default (pre-existing games "earn nothing... no retroactive persona identity" per the phase description) — this is actually the SAFE case, not the risky one, since the column is `nullable=True` with no `server_default` and no backfill `UPDATE` is needed or wanted.
**How to avoid:** write the migration as a bare `op.add_column("games", sa.Column("persona_id", sa.String(30), nullable=True))` with NO backfill UPDATE and NO default — this stays a fast metadata-only change, unlike Phase 178's migration. Do not add a `server_default=''` or similar out of habit.
**Warning signs:** a migration that includes an `UPDATE games SET persona_id = ...` for existing rows — this would violate "pre-existing games earn nothing (no retroactive persona identity)," a locked constraint from the phase description.

### Pitfall 5: Aggregation query needs a supporting index only if the per-user row count review shows it matters

**What goes wrong:** `SELECT persona_id, COUNT(*) FILTER(...) FROM games WHERE user_id = :uid AND persona_id IS NOT NULL GROUP BY persona_id` will use the existing `ix_games_user_played_at (user_id, played_at DESC)` index for the `user_id` equality lookup (it's a leading-column match), then filter/aggregate in-memory — for a single user's bot games (almost certainly a few hundred at most, not hundreds of thousands), this is fast without any new index.
**Why it happens:** none — this is a non-issue at expected scale, called out here only so a planner doesn't over-engineer a new partial index (e.g. `WHERE persona_id IS NOT NULL`) for a per-user-scoped query that will never scan more than one user's rows.
**How to avoid:** skip adding a new index in this phase; the existing `(user_id, played_at DESC)` index already makes the `user_id` predicate cheap, and `GROUP BY persona_id` over one user's few-hundred-row bot-game slice needs no help.

## Code Examples

### Star row rendering (new, following the project's icon-toggle + theme-constant conventions)

```tsx
// Illustrative — NOT verified against an actual PersonaCard implementation,
// since the stars row does not exist yet. Follows lucide-react's documented
// fill/className toggle pattern (VERIFIED: lucide-react 1.21.0 Star component
// accepts standard SVG props including fill).
import { Star } from 'lucide-react';
import { STAR_FILLED, STAR_EMPTY } from '@/lib/theme'; // NEW constants to add

const MAX_DISPLAY_STARS = 3; // named constant, not a magic number (CLAUDE.md)

function PersonaStars({ wins }: { wins: number }): ReactElement {
  const filled = Math.min(wins, MAX_DISPLAY_STARS);
  return (
    <span className="flex gap-0.5" aria-label={`${wins} win${wins === 1 ? '' : 's'}`}>
      {Array.from({ length: MAX_DISPLAY_STARS }, (_, i) => (
        <Star
          key={i}
          size={14}
          aria-hidden="true"
          style={{ color: i < filled ? STAR_FILLED : STAR_EMPTY }}
          fill={i < filled ? 'currentColor' : 'none'}
        />
      ))}
    </span>
  );
}
```

### Win-count fetch hook (mirrors `useUserProfile.ts` exactly)

```ts
// Source pattern: frontend/src/hooks/useUserProfile.ts (existing, verbatim shape)
export function useBotPersonaWins() {
  return useQuery<Record<string, number>>({
    queryKey: ['botPersonaWins'],
    queryFn: async () => {
      const res = await apiClient.get<PersonaWinsResponse>('/bots/persona-wins');
      return res.data;
    },
    staleTime: 300_000, // 5 minutes — win counts change only on game-finish, not worth polling
  });
}
```

## State of the Art

Not applicable — this is an internal feature extension, not an area with external "current best practice" drift. No deprecated APIs involved.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `games.persona_id` should have NO `CHECK` constraint (unlike `rating_source`'s 3-value CHECK) because the persona roster is frontend-only and milestone-evolving | Standard Stack (Alternatives Considered), Pitfall 4 | If wrong (project wants a CHECK for defense-in-depth), the migration needs a CHECK list AND a documented "update this CHECK whenever the roster changes" operator policy — low risk either way, but changes the migration's shape |
| A2 | The win-count cap-at-3 (`LEAST`/`min`) should be applied in the FRONTEND, with the backend returning raw counts | Standard Stack (Alternatives Considered) | If wrong (backend must return already-capped values), the response schema changes from `wins: int` to something pre-clamped — a one-line difference, not architecturally significant either way |
| A3 | No new DB index is needed for the per-user win-aggregation query at expected scale | Pitfall 5 | If a power user accumulates enough bot games that this becomes measurably slow (unlikely — bot games are a small fraction of a user's total imported history), a follow-up index is a trivial addition, not a redesign |
| A4 | `persona_id`'s max length should be bounded (e.g. `String(30)`) rather than unbounded `Text`, mirroring `tc_preset`'s CR-01-motivated length bound | Common Pitfalls (Pitfall re: request validation) | If wrong (project prefers `Text` like `rating_source`/`tc_preset` on `bot_game_settings`), a length-bound `String` column is trivially widened later; low risk |

## Open Questions (RESOLVED)

1. **Where does the win-star row's design (spacing, size, gold/grey exact shade) get specified?**
   - What we know: `PersonaCard`'s existing vertical stack (avatar 48px circle, name, ELO label) is unchanged; the phase says the stars row is added "at the bottom."
   - What's unclear: exact icon size, gap, and whether the stars row renders even at `wins === 0` (all 3 grey-outline) or is hidden entirely for zero-win personas.
   - Recommendation: default to ALWAYS rendering 3 stars (grey-outline at 0 wins) for visual consistency across all 24 cards in the transposed grid — hiding the row conditionally would make the grid's row heights inconsistent, which matters more now that cards are column-aligned under a shared header.
   - **RESOLVED:** the approved 185-UI-SPEC.md locks the full star-row design (14px lucide `Star` icons, `gap-0.5`, `STAR_FILLED`/`STAR_EMPTY` theme constants) and adopts the always-render-3-stars zero-state; cap ownership is frontend `Math.min(wins, 3)` with the backend returning raw counts.

2. **Does the win-aggregation endpoint need to be platform-scoped, or is `persona_id IS NOT NULL` sufficient on its own?**
   - What we know: `persona_id` is only ever set on `platform='flawchess'` rows (custom-mode and any other platform never populate it).
   - What's unclear: whether to add a redundant `platform == 'flawchess'` predicate for defensive clarity/future-proofing, or rely on the invariant.
   - Recommendation: add it anyway — it's a cheap, self-documenting predicate that protects against a future bug where `persona_id` might accidentally get set on a non-flawchess path.
   - **RESOLVED:** 185-01-PLAN.md's aggregation task explicitly includes the `Game.platform == "flawchess"` predicate alongside `persona_id IS NOT NULL`.

3. **Should `StoreBotGameRequest.persona_id` be validated against a known-shape pattern (e.g. `^[a-z]+-\d{3,4}$`) or just length-bounded?**
   - What we know: the backend has zero knowledge of the frontend's 24-persona registry (by design — no shared enum).
   - What's unclear: whether a shape-regex is worth the maintenance vs. just bounding length and accepting that a malformed value only corrupts the SUBMITTING USER's OWN win-star display (low blast radius — not a cross-user security issue).
   - Recommendation: length bound only (`Field(max_length=30)`), no regex — matches the low-severity, self-scoped nature of a wrong value here (contrast with e.g. `game_uuid`, which DOES get strict UUID validation because it drives cross-request idempotency).
   - **RESOLVED:** 185-01-PLAN.md adopts `Field(max_length=30)` with no shape regex, per this recommendation.

## Environment Availability

Skip — this phase has no new external dependencies (no new package, no new external service, no new CLI tool). It uses the existing PostgreSQL dev DB, existing Alembic tooling, and existing `lucide-react`/TanStack Query already installed.

## Validation Architecture

`workflow.nyquist_validation` is `true` in `.planning/config.json` (not absent, explicitly enabled) — this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest 9.0.3 (installed, per `.pyc` cache files), async via `pytest-asyncio`, per-run cloned DB template (see `tests/conftest.py`) |
| Backend config | `pyproject.toml` (existing, no changes needed) |
| Backend quick run | `uv run pytest tests/schemas/test_bots.py tests/routers/test_bots.py tests/services/test_store_bot_game_service.py tests/repositories/test_game_repository.py -x` |
| Backend full suite | `uv run pytest -n auto` |
| Frontend framework | Vitest (via `npm test` = `vitest run`), jsdom environment per-file (`// @vitest-environment jsdom` header, as seen in `PersonaGrid.test.tsx`) |
| Frontend config | `frontend/vite.config.ts` (no dedicated `test:` block — 5s default `testTimeout` applies project-wide per known MEMORY note on CPU-bound test flakes; not expected to matter here, these are small DOM tests) |
| Frontend quick run | `cd frontend && npx vitest run src/components/bots/__tests__/PersonaGrid.test.tsx src/components/bots/__tests__/PersonaCard.test.tsx` |
| Frontend full suite | `cd frontend && npm test -- --run` |

### Phase Requirements -> Test Map

No formal REQ-IDs are mapped for this phase (REQUIREMENTS.md traceability table has no v2.7 entry for Phase 185 — it's a post-milestone follow-up, not one of the 13 tracked v2.7 requirements). Behavior-to-test mapping instead follows the phase description's 3 numbered items:

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|-------------------|-------------|
| Grid renders 6 rung rows × 4 style columns, header row of 4 style names in accent colors, no row labels | unit (jsdom) | `npx vitest run src/components/bots/__tests__/PersonaGrid.test.tsx` | ❌ Wave 0 — existing test file needs its DOM-order assertion REWRITTEN, not just extended (Pitfall 2) |
| `PersonaCard` renders `min(wins,3)` gold + grey-outline stars | unit (jsdom) | `npx vitest run src/components/bots/__tests__/PersonaCard.test.tsx` | ❌ Wave 0 — new assertions needed in existing file |
| `StoreBotGameRequest.persona_id` accepts `None` and a bounded string; rejects overlong values | unit | `uv run pytest tests/schemas/test_bots.py -x` | ❌ Wave 0 — existing file needs new test cases |
| `POST /bots/games` persists `persona_id` on create, is a no-op on idempotent resubmit (mirrors existing STORE-05 test) | integration | `uv run pytest tests/routers/test_bots.py -x` | ❌ Wave 0 — existing file needs new test cases (mirror `test_store_bot_game_idempotent_resubmit`) |
| `count_wins_by_persona` returns correct win counts, excludes draws/losses, excludes `persona_id IS NULL` rows | unit (real DB, per `tests/repositories/test_bot_game_settings_repository.py` precedent) | `uv run pytest tests/repositories/test_game_repository.py -x` | ❌ Wave 0 — new test cases |
| `GET /bots/persona-wins` returns per-user-scoped counts, requires auth (mirrors `test_store_bot_game_requires_auth`) | integration | `uv run pytest tests/routers/test_bots.py -x` | ❌ Wave 0 — new test cases |
| Alembic migration applies cleanly, `alembic-check` drift gate stays green | migration | `uv run alembic upgrade head` (auto-run by per-run test-DB template refresh) | ❌ Wave 0 — new migration file |

### Sampling Rate

- **Per task commit:** the relevant quick-run command above (scoped to the file(s) touched)
- **Per wave merge:** full backend (`uv run pytest -n auto`) + full frontend (`npm test -- --run`) suites
- **Phase gate:** both full suites green, plus `uv run ty check app/ tests/` and `npm run lint`/`npm run build` (tsc) before `/gsd-verify-work`, per CLAUDE.md's pre-merge gate

### Wave 0 Gaps

- [ ] `tests/repositories/test_game_repository.py` may not yet exist as a standalone file (repository tests for `game_repository.py` might live elsewhere — verify at plan time; `count_games_by_platform` is the closest existing precedent to locate its current test coverage)
- [ ] No shared fixture currently seeds a `games` row with `persona_id` set — plan-time task should add a small helper/fixture (likely inline, following `_make_bot_game_payload` in `tests/routers/test_bots.py`)
- [ ] Framework install: none — pytest and Vitest are both already fully configured

## Security Domain

`security_enforcement` is absent from `.planning/config.json` — treat as enabled per the default.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (existing, unchanged) | `current_active_user` dependency on both the existing `POST /bots/games` and the new `GET /bots/persona-wins` — covers guests too (D-13 precedent) |
| V4 Access Control | yes | `user_id` for both the persona_id write and the win-count read comes ONLY from `current_active_user`'s JWT-derived identity, NEVER from a request parameter — mirrors the existing `store_bot_game`'s explicit "user_id is derived from the authenticated JWT — never from the request body (ASVS V4)" comment. The new `GET /bots/persona-wins` endpoint must not accept a `user_id` query param (no cross-user win-count leakage) |
| V5 Input Validation | yes | `persona_id: str | None = Field(default=None, max_length=30)` on `StoreBotGameRequest` — bounds the same DoS/overflow surface class as `tc_preset`'s `_MAX_TC_PRESET_LENGTH` (CR-01 precedent: an unbounded value that overflows the DB column type raises an unhandled 500 instead of a 422) |
| V6 Cryptography | no | not applicable — no crypto involved |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Overlong `persona_id` string crashing the INSERT/UPDATE with an unhandled Postgres `DataError` (mirrors the historical `tc_preset` CR-01 bug and the `termination_raw` CR-02 bug, both in this exact code path's neighborhood) | Denial of Service (a crafted request 500s instead of 422ing) | Pydantic `Field(max_length=...)` at the schema boundary, validated BEFORE the value ever reaches SQL — same pattern as `_MAX_TC_PRESET_LENGTH` and `MAX_BOT_PGN_LENGTH` already in `app/schemas/bots.py` |
| A malicious/malformed `persona_id` value polluting the win-aggregation `GROUP BY` output (e.g. an XSS-shaped string echoed back verbatim in the JSON response) | Tampering / Information Disclosure (low severity — self-scoped to the submitting user's own data) | The value is only ever rendered as a dictionary KEY in a JSON response consumed by React (auto-escaped), never `dangerouslySetInnerHTML`'d or used to construct a DOM id/selector directly from server data — standard React JSX text/attribute binding is sufficient; no additional sanitization needed beyond the length bound above |

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection (Read/Grep/Bash) of: `app/models/game.py`, `app/models/bot_game_settings.py`, `app/schemas/bots.py`, `app/routers/bots.py`, `app/services/store_bot_game_service.py`, `app/services/normalization.py`, `app/repositories/game_repository.py`, `app/repositories/stats_repository.py`, `alembic/versions/20260711_185207_a07ccca76092_phase_167_bot_game_settings_table.py`, `alembic/versions/20260718_084123_60d9b72c0eaa_add_accuracy_acpl_imported_to_games.py`, `frontend/src/components/bots/PersonaGrid.tsx`, `frontend/src/components/bots/PersonaCard.tsx`, `frontend/src/lib/personas/personaRegistry.ts`, `frontend/src/lib/personas/personaAvatars.ts`, `frontend/src/hooks/useBotGame.ts`, `frontend/src/hooks/useStoreBotGame.ts`, `frontend/src/lib/botPendingStore.ts`, `frontend/src/lib/theme.ts`, `frontend/src/hooks/useUserProfile.ts`, `frontend/src/api/client.ts`, `frontend/src/pages/Bots.tsx`, `frontend/src/components/bots/__tests__/PersonaGrid.test.tsx`, `tests/routers/test_bots.py`
- `node_modules/lucide-react/package.json` — confirmed installed version 1.21.0 [VERIFIED: node_modules/lucide-react/package.json]
- `.planning/ROADMAP.md` (Phase 185 goal text, verbatim source of scope) and `.planning/REQUIREMENTS.md` (confirms no v2.7 requirement IDs map to Phase 185 — it is a post-milestone follow-up phase)
- `.planning/STATE.md` (Roadmap Evolution entry confirming Phase 185's origin from a 2026-07-22 `/gsd-explore` session)

### Secondary (MEDIUM confidence)
- None — no external web sources were needed; this phase is entirely an internal-codebase extension with no new libraries or external APIs.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; every pattern cited has a byte-identical precedent already shipped in this codebase
- Architecture: HIGH — both halves (grid transpose, win tracking) map directly onto existing, well-documented Phase 167/183/184 code paths
- Pitfalls: HIGH — all 5 pitfalls are grounded in specific, named existing code (test files, migration files, wire-format functions) inspected directly, not inferred

**Research date:** 2026-07-22
**Valid until:** 30 days (stable internal codebase, no fast-moving external dependency)
