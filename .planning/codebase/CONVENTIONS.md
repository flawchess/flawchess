# Coding Conventions

**Analysis Date:** 2026-05-30

This codebase has two stacks: a Python 3.13 / FastAPI backend in `app/` and a React 19 / TypeScript / Vite frontend in `frontend/`. Conventions below are the *observed* patterns in code, cross-referenced with the project rules in `CLAUDE.md`. Where the two diverge, that is called out explicitly.

## Naming Patterns

### Backend (Python)

**Files:**
- `snake_case.py` for all modules: `import_service.py`, `query_utils.py`, `stats_service.py`.
- Routers are named after their resource, **pluralized**, with no `_router` suffix: `app/routers/openings.py`, `stats.py`, `endgames.py`, `insights.py`, `imports.py`, `games.py`, `position_bookmarks.py`, `admin.py`, `auth.py`, `users.py`.
- Repositories use the `<domain>_repository.py` suffix: `app/repositories/stats_repository.py`, `game_repository.py`, `endgame_repository.py`, `openings_repository.py`. The shared filter module is `query_utils.py`.
- Schema modules mirror their domain: `app/schemas/stats.py`, `openings.py`, `endgames.py`, `insights.py`, `normalization.py`, `imports.py`.

**Functions:**
- `snake_case` throughout: `get_position_stats`, `apply_game_filters`, `get_rating_history`.
- Module-private helpers are prefixed with a single underscore: `_rows_to_wdl_categories`, `_call_llm`, `_create_test_users`. Pipeline orchestrators split into `_fetch` / `_classify` / `_attribute` style stage functions per `CLAUDE.md`.

**Variables:**
- `snake_case` locals; `user_id`, `session` / `db_session`, `filters` are the canonical names threaded through service/repository signatures.

**Module-level constants:**
- `UPPER_SNAKE_CASE`, underscore-prefixed when module-private: `_BATCH_SIZE`, `_HASH_MB` (`app/services/import_service.py`), `ENDGAME_PLY_THRESHOLD` (`app/repositories/endgame_repository.py`), `MIN_GAMES_FOR_CLOCK_STATS`. **No magic numbers** — thresholds, limits, and batch sizes are always extracted to a named constant (enforced by `CLAUDE.md`).

**Types:**
- Pydantic models use `PascalCase`: `GameFilters`, `PositionStatsRequest`, `PositionStatsResponse`, `EndgameInsightsReport` (`app/schemas/*`).
- `Literal` type aliases are `PascalCase` and defined at module top. **Never `str` for a fixed value set** — use `Literal[...]` in schemas, function signatures, service/repository params, and return types (enforced by `CLAUDE.md`). See `app/schemas/stats.py` for time-control / platform / color literal aliases.

### Frontend (TypeScript)

**Files:**
- React components: `PascalCase.tsx` — `EndgameTypeCard.tsx`, `RatingChart.tsx`, `GameCard.tsx`, `FilterPanel.tsx`.
- Hooks: `camelCase.ts` with `use` prefix — `useOpenings.ts`, `useStats.ts`, `useEndgames.ts`, `useReadiness.ts`, `useFilterStore.ts`, `useDebounce.ts`.
- Pure utility / lib modules: `camelCase.ts` in `src/lib/` — `zobrist.ts`, `clockFormat.ts`, `recency.ts`, `signedBandGradient.ts`, `pgn.ts`, `sanToSquares.ts`, `queryClient.ts`, `theme.ts`, `utils.ts`.
- The HTTP client is a single module: `src/api/client.ts` (there is **no per-resource `src/api/*.ts`** — resource fetching lives in the `use*` hooks, which call `client.ts`).
- shadcn/ui primitives are lowercase: `src/components/ui/button.tsx`, `card.tsx`, `select.tsx`.
- Page-local sub-hooks/helpers are co-located: `src/pages/openings/useOpeningsHandlers.ts`, `useSidebarState.ts`, `useDeepLinkHighlight.ts`.

**Functions / hooks:**
- `camelCase`. Hooks always `use` + `PascalCase`.

**Components & props:**
- Components are `PascalCase` **named** exports (not default exports): `export function EndgameTypeCard(...)`.
- Props interfaces are `<Component>Props`.

**Types:**
- Domain types live in `src/types/` with **plural / snake-ish** filenames: `endgames.ts`, `stats.ts`, `users.ts`, `insights.ts`, `position_bookmarks.ts`, `charts.ts`, `admin.ts`, `api.ts`. `PascalCase` type names (`EndgameCategoryStats`).
- Theme/semantic constants exported `as const` for literal narrowing in `src/lib/theme.ts` (`WDL_COLORS`, gauge zone colors, glass overlays).

## Code Style

### Backend

**Formatting / Linting:** `ruff` (config in `pyproject.toml`).
- `line-length = 100`. No explicit `[tool.ruff.lint]` rule selection — ruff's **default** rule set is in effect (E/F/W + isort `I` via the formatter). Per-file ignores: `app/models/*.py = ["F821"]` (SQLAlchemy forward-ref strings in `relationship()`), `alembic/versions/*.py = ["F401"]` (auto-imported `sa`/`op`).
- Imports are auto-sorted. Run `uv run ruff format .` then `uv run ruff check . --fix`.

**Type checking:** `ty` (config `[tool.ty.rules]`: `unused-ignore-comment = "warn"` so stale ignores don't accumulate).
- All backend code MUST pass `uv run ty check app/ tests/` with **zero errors** (CI gate between ruff and pytest).
- Explicit return type annotations on all functions: `async def get_position_stats(...) -> PositionStatsResponse:`.
- Use `Sequence[str]` (covariant) not `list[str]` for params that accept `list[Literal[...]]` — `list` is invariant. Import `from collections.abc import Sequence`.
- Suppress unfixable errors with `# ty: ignore[rule-name]` (never bare `# type: ignore`), always with the rule name and a brief reason (SQLAlchemy forward refs, FastAPI-Users generics).

### Frontend

**Linting:** ESLint flat config (`frontend/eslint.config.js`).
- Extends `js.configs.recommended`, `tseslint.configs.recommended`, `reactHooks.configs.flat.recommended`, `reactRefresh.configs.vite`. Global-ignores `dist`, `dev-dist`.
- `react-refresh/only-export-components` is turned **off** for `src/components/ui/**` (shadcn primitives export variants alongside components). Run `npm run lint` (`eslint .`).

**Dead-code detection:** `knip` (`npm run knip`, config `frontend/knip.json`) runs in CI and fails on unused exports/deps. Remove exports when removing a feature; ensure new exports are imported somewhere.

**Type checking:** `tsc -b` as part of `npm run build`. Strict TS via `frontend/tsconfig.app.json`:
- `strict: true`, `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`, `noUncheckedSideEffectImports`, `erasableSyntaxOnly`.
- **`noUncheckedIndexedAccess: true`** — every array/Record index access returns `T | undefined`. Narrow before use (`const v = arr[i]; if (v) {...}`), `!` only when provably in bounds, or `?? fallback` for Records. Never `// @ts-ignore`.
- **`verbatimModuleSyntax: true`** → type-only imports MUST use `import type { ... }` (e.g. `import type { EndgameCategoryStats } from '@/types/endgames'`).

**No Prettier config file** — style is enforced by ESLint defaults. Observed: 2-space indent, single quotes, **semicolons present** in `.ts`/`.tsx` (see `src/lib/queryClient.ts`).

## Import Organization

### Backend
Ruff `I` enforces three groups (stdlib → third-party → first-party `app.`):
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.services import stats_service
```
Services are imported **as modules** and called as `stats_service.get_position_stats(...)` (observed in routers). Pure functions are sometimes imported by name in tests (`from app.services.stats_service import _rows_to_wdl_categories`).

### Frontend
**Path alias `@/` → `src/`** (declared in `tsconfig.app.json` `paths` and `vite.config.ts` `resolve.alias`). Use `@/lib/theme`, `@/types/endgames`, `@/hooks/useStats` — not deep relative paths. Co-located imports stay relative (`../EndgameTypeCard`).

Observed order: third-party (`react`, `@tanstack/react-query`, `radix-ui`, `recharts`, `vitest`/`@testing-library` in tests) → `@/` aliased internal → relative.

## Error Handling

### Backend
- **Routers** translate expected `ValueError` (user-input validation) into `HTTPException` with `from e` chaining:
  ```python
  except ValueError as e:
      raise HTTPException(status_code=400, detail=str(e)) from e
  ```
- **Sentry capture is mandatory** in every non-trivial `except` in `app/services/` and `app/routers/`:
  ```python
  sentry_sdk.set_context("import", {"job_id": str(job_id), "user_id": user_id})
  sentry_sdk.capture_exception(e)
  ```
- **Never embed variables in exception messages** (fragments Sentry grouping) — pass them via `set_context` / `set_tag`. Use `set_tag("source", ...)` for filterable dimensions (`import`, `api`, `auth`).
- **Skip trivial/expected exceptions**: `ValueError` from parsing user input, `UserAlreadyExists` from FastAPI-Users. In retry loops, capture only on the final attempt — let transient failures propagate.
- Sentry initialized in `app/main.py` (`sentry-sdk[fastapi]`).

### Frontend
- **API layer** (`src/api/client.ts`): the shared fetch wrapper throws on non-OK responses; callers handle via TanStack Query.
- **Global TanStack Query/Mutation errors** are captured once in `src/lib/queryClient.ts` (exact, verified):
  - `QueryCache.onError` → `Sentry.captureException(error, { tags: { source: 'tanstack-query' }, extra: { queryKey: query.queryKey } })`.
  - `MutationCache.onError` → `Sentry.captureException(error, { tags: { source: 'tanstack-mutation' }, extra: { mutationKey: mutation.options.mutationKey } })`.
  - **Do NOT** add duplicate `Sentry.captureException` in components using `useQuery`/`useMutation`.
- Query defaults: `retry: 1`, `staleTime: 30_000`.
- **Manual fetch/axios in catch blocks** (outside TanStack Query — auth forms, direct calls) MUST capture explicitly with a source tag: `Sentry.captureException(error, { tags: { source: 'auth' } })`. Sentry is initialized in `src/instrument.ts`.
- **Every data-loading ternary chain MUST include an `isError` branch** showing "Failed to load [X]. Something went wrong. Please try again in a moment." Never let an API error fall through to an empty-state ("No games imported yet") message.

## Logging

**Backend:** stdlib `logging`, one logger per module: `logger = logging.getLogger(__name__)`. Use `logger.info(...)` for pipeline progress. Logging is *not* a substitute for Sentry — errors must be explicitly captured.

**Frontend:** No console logging convention; errors go to Sentry. Avoid stray `console.log` in committed code.

## Comments

- **Comment bug fixes** — add a comment at the fix site explaining what broke and why (per `CLAUDE.md`). Future readers shouldn't need git blame. Observed extensively in `tests/conftest.py` and `frontend/vite.config.ts` (explaining non-obvious workarounds).
- **Docstrings** (backend): triple-quoted docstrings on public service/router functions and Pydantic models describe behavior. Test modules carry header docstrings describing coverage intent (`tests/test_stats_service.py`, `tests/seed_fixtures.py`). Frontend component test files often have a top docblock describing what is covered.
- Avoid em-dashes in prose, commit messages, PR descriptions, and user-facing UI copy (style rule in `CLAUDE.md`); a single em-dash per paragraph is the max. Code comments are exempt.

## Function Design

Limits apply to **both** stacks (`CLAUDE.md`):
- **Nesting depth:** soft 3, hard 4 inside any function body (the firm rule).
- **Logic LOC:** soft 100, hard 200 — measuring *logic* lines, excluding returned JSX trees, large literal config objects (Recharts axis/gradient configs), docstrings, and blanks.
- **Cognitive complexity:** aim ≤ 15 per function.

Common splits when exceeded:
- **Pipeline orchestrators** (import, insights, normalization): one function per stage; the top-level reads as a list of `_fetch` / `_classify` / `_attribute` / `_dedupe` / `_rank` calls.
- **React components mixing data + JSX:** extract data shaping into a `useXyz` hook (the Openings page does this via `src/pages/openings/use*.ts`); split desktop/mobile renderers when each branch exceeds ~40 LOC of logic.
- **Routers doing more than HTTP:** keep thin — validate, call service, shape response. Push branching/caching/aggregation into the service layer.
- **Don't invent context dataclasses just to fit a signature.** A bag-of-state with < 3 fields, one writer, one reader is over-engineering — pass args directly. Context types earn their keep when threaded through 3+ stages or carrying ≥ 4 fields.

**Refactor bloated code on sight** when editing a file (within GSD phase scope; flag unscoped refactors, prefer a follow-up note for `/gsd-quick` / `/gsd-fast`).

## Module Design

### Backend layered architecture (strict)
```
routers/       # HTTP only — validation, service call, response shaping. No business logic.
services/      # Business logic. No raw SQL.
repositories/  # DB access. No SQL anywhere else.
```
- **Router prefix convention:** `APIRouter(prefix="/resource", tags=["resource"])` with relative paths in decorators (`@router.post("/positions")`). Never embed the resource prefix in individual route paths.
- **Shared query filters:** `app/repositories/query_utils.py::apply_game_filters()` is the single source for time-control / platform / rated / opponent-type / recency / color filtering. All repositories import it; never duplicate filter logic.
- **Pydantic models at system boundaries** (external API I/O, request/response); `TypedDict` for internal structured data (filter params, accumulators) — see `app/schemas/normalization.py`, `app/services/stats_service.py`.

### Frontend
- **Named exports**, no default exports for components/utilities.
- **No barrel `index.ts` re-export files** — import directly from the module.
- **shadcn/ui pattern** for primitives: `cva` (class-variance-authority) variant definitions + `cn()` merge helper (`clsx` + `tailwind-merge`) from `@/lib/utils` (`src/components/ui/button.tsx`).
- **Variant semantics** (`CLAUDE.md`): primary CTA = `variant="default"`; secondary action = `variant="brand-outline"`; `variant="secondary"` is reserved for neutral gray chips only.
- **API/hook layering:** `src/api/client.ts` (shared fetch wrapper) ← `src/hooks/use*.ts` (TanStack Query wrappers that own `queryKey` arrays and `enabled` flags) ← components.

## Frontend-Specific Conventions

- **Theme constants in `src/lib/theme.ts`** — all semantic colors (WDL win/draw/loss, gauge zones, glass overlays, opacity) live here and are imported. Never hard-code semantic color values in components.
- **Minimum font size `text-sm`** — never `text-xs` or smaller in new code (readability floor), *except* hover/tap info tooltips (Radix popover bodies with the HelpCircle trigger: `MetricStatPopover`, `WdlConfidenceTooltip`, `EvalConfidenceTooltip`, `AchievableScorePopover`) which may use `text-xs`.
- **`data-testid` on every interactive element** — buttons, links, inputs, select triggers, toggles, collapsible triggers — kebab-case, component-prefixed: `btn-{action}`, `nav-{page}`, `filter-{name}`, `board-btn-{action}`, `{component}-{element}-{id}` (e.g. `endgame-type-card-rook`). Major layout containers, section headings, and modals also get `data-testid` (`dashboard-page`, `import-modal`). These IDs double as the primary handle for component tests (`screen.getByTestId`).
- **Semantic HTML** — `<button>` for clickable non-links, `<a>`/`<nav>` for navigation, `<main>`, `<form>`. Never `<div onClick>` / `<span onClick>`.
- **ARIA labels on icon-only buttons** — `aria-label` required when there is no visible text.
- **Chess board** — container has `data-testid="chessboard"` + `id="chessboard"`; supports both drag-drop and click-to-click moves.
- **Mobile parity** — when a component has separate desktop and mobile sections, apply every change (styling, added/removed elements, behavior) to both unless desktop-specific by nature.

---

*Convention analysis: 2026-05-30*
