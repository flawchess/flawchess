# Testing Patterns

**Analysis Date:** 2026-05-30

Two independent test suites: pytest for the Python backend (`tests/`, ~50 files, ~1,096 test functions) and Vitest for the React frontend (`frontend/src/**/*.test.{ts,tsx}`, ~60 spec files). Both run as required CI gates and as part of the mandatory pre-PR checklist.

## Test Framework

### Backend
**Runner:** `pytest` (>=8) with `pytest-asyncio` (>=0.23). Config in `pyproject.toml` `[tool.pytest.ini_options]`:
```toml
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
```
- **`asyncio_mode = "auto"`** means async test functions run without an explicit `@pytest.mark.asyncio` marker — just write `async def test_...`.
- Loop scope is **session** — the event loop is shared across the whole session, which is why session-scoped async fixtures (engine, Stockfish process) work.

**Assertion library:** plain `assert` (pytest rewriting).

**Coverage:** `pytest-cov` (>=7). No enforced minimum threshold. An `htmlcov/` report and `.coverage` file exist from local runs.

**Run commands:**
```bash
uv run pytest                                          # Run all tests
uv run pytest -x                                       # Stop on first failure
uv run pytest tests/test_stats_service.py::test_name   # Single test
uv run pytest --cov                                    # Coverage
```

> **Important:** the backend test suite runs against a **real PostgreSQL database** (`flawchess_test`), NOT SQLite — consistent with the project's PostgreSQL-only rule. The dev Postgres container must be running (`docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`) before `uv run pytest`. `TEST_DATABASE_URL` defaults to `postgresql+asyncpg://postgres:postgres@localhost:5432/flawchess_test` (`app/core/config.py:15`).

### Frontend
**Runner:** `vitest` (v4) with `@vitejs/plugin-react`. There is **no `vitest.config.ts` and no shared setup file** — Vitest runs via the `vitest run` npm script using its defaults plus the `@/` alias inherited from `vite.config.ts` (Vitest reads `vite.config.ts` automatically; that file has no `test:` block, so defaults apply).

**DOM environment is opt-in per file via a docblock pragma.** Tests that render React components or hooks put `// @vitest-environment jsdom` as the **first line** of the file (27 test files do this, e.g. `EndgameTypeCard.test.tsx`, `GameCard.test.tsx`, `useReadiness.test.tsx`, page-level `Endgames.*`). Pure lib/util tests omit the pragma and run in the default Node environment (`zobrist.test.ts`, `clockFormat.test.ts`, etc.). When adding a component/hook test, **remember the jsdom pragma** or `document` will be undefined.

**Assertion library:** Vitest `expect` only — `describe`, `it`, `expect`, and `vi` are **imported explicitly** from `'vitest'` (globals are NOT enabled). **`@testing-library/jest-dom` is NOT wired up** (no setup file; `toBeInTheDocument` is used nowhere). Component assertions use plain Vitest matchers against RTL queries: `.toBeTruthy()`, `.toBeNull()`:
```tsx
expect(screen.getByTestId('endgame-type-card-rook')).toBeTruthy()
expect(screen.getByText('Rook')).toBeTruthy()
expect(screen.queryByTestId('wdl-bar')).toBeNull()
```
Component/hook testing via `@testing-library/react` (`render`, `screen`, `renderHook`). Coverage via `@vitest/coverage-v8`.

**Run commands:**
```bash
npm test                    # "vitest run" — one-shot
npm run test:watch          # "vitest" — watch mode
( cd frontend && npm test -- --run )   # used in the pre-PR checklist
```

## Test File Organization

**Backend:**
- Single `tests/` directory mirroring service/router/module names: `test_stats_service.py`, `test_query_utils.py`, `test_auth.py`, `test_openings_repository.py`, `test_endgames_router.py`, `test_zobrist.py`, `test_normalization.py`, `test_main_lifespan.py`, migration tests (`test_migration_91_evals_completed_at.py`), etc.
- Naming: `test_<module>.py`; functions `test_<behavior>`. Related tests are frequently grouped into plain classes (no inheritance): `class TestRowsToWdlCategories:`, `class TestGetRatingHistory:` (`tests/test_stats_service.py`).

**Frontend:**
- Two co-location styles, both used:
  - `__tests__/` subdirectory next to the unit (most common): `src/components/charts/__tests__/EndgameTypeCard.test.tsx`, `src/hooks/__tests__/useEndgameInsights.test.tsx`, `src/pages/__tests__/Endgames.readinessGate.test.tsx`, `src/lib/__tests__/clockFormat.test.ts`.
  - Sibling file (also common for lib + a few components): `src/lib/utils.test.ts`, `src/lib/zobrist.test.ts`, `src/lib/pgn.test.ts`, `src/types/api.test.ts`, `src/components/insights/OpeningFindingCard.test.tsx`.
- Naming: `<Module>.test.ts` / `<Component>.test.tsx`. Descriptive multi-part names for scenario-specific suites: `MetricStatTooltip.caveat.test.tsx`, `Import.stateMachine.test.tsx`, `Endgames.readinessGate.test.tsx`.
- **Frontend testing is broad** — pure lib functions (`zobrist`, `clockFormat`, `recency`, `signedBandGradient`, `pgn`, `sanToSquares`), data hooks (`useEndgameOverview`, `useReadiness`, `useEvalCoverage`, `useOpeningInsights`), AND full component/page renders (`EndgameTypeCard`, `GameCard`, `RatingChart`, `MoveExplorer`, `PercentileChip`, page-level `Endgames.*`, `Import.*`, `Openings.*`). Component tests use React Testing Library's `render` + `screen.getByText/getByTestId/getByRole`.

## Test Structure

### Backend
Async test functions/methods taking fixtures as parameters. Module-level docstrings describe coverage intent (see the header of `tests/test_stats_service.py`). Classes group related cases:
```python
class TestGetRatingHistory:
    async def test_platform_filter_chess_com(self, db_session: AsyncSession) -> None:
        await _create_test_users(db_session)
        session.add(Game(...))            # seed inline
        response = await get_rating_history(db_session, uid, from_date=None, to_date=None)
        assert ...
```
- Service-level tests call the service directly with `db_session`; router/endpoint tests use the `seeded_user` fixture + an httpx client against the FastAPI app.

### Frontend
Explicit `vitest` imports, `describe` / `it` blocks, one `describe` per component/function:
```tsx
// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { EndgameTypeCard } from '../EndgameTypeCard'
import type { EndgameCategoryStats } from '@/types/endgames'

describe('EndgameTypeCard', () => {
  it('renders the category label', () => {
    render(<EndgameTypeCard stats={baseStats} />)
    expect(screen.getByText('Rook')).toBeTruthy()
  })
})
```
Test fixtures (e.g. `baseStats`) are defined as typed literals at the top of the file using the real domain type imported from `@/types/*`.

## Fixtures and Factories

### Backend (`tests/conftest.py` + `tests/seed_fixtures.py`)
The fixture architecture is the most important thing to understand:

- **`test_engine`** (session scope) — patches `settings.DATABASE_URL` to `TEST_DATABASE_URL`, runs `alembic upgrade head` against `flawchess_test` (schema is built by **real migrations**, not `create_all`), truncates leftover data from prior runs (`TRUNCATE ... RESTART IDENTITY CASCADE`, preserving `alembic_version` and `openings`), yields an async engine.
- **`override_get_async_session`** (session scope, **autouse**) — overrides the FastAPI `get_async_session` DI dependency AND monkeypatches `async_session_maker` in every module that imports it directly (`app.core.database`, `app.users`, `app.middleware.last_activity`, `app.repositories.llm_log_repository`) so non-DI code paths (e.g. `UserManager.on_after_login`, middleware, independent-session LLM logging) also hit the test DB.
- **`db_session`** — yields an `AsyncSession` bound to a connection inside a transaction that is **rolled back** after each test, so tests never pollute each other. Use this for service/repository tests. `expire_on_commit=False`.
- **`fresh_test_user`** — a **committed** user that survives the `db_session` rollback scope; required when the code under test opens its own session and commits independently (e.g. `create_llm_log`). Deleted on teardown (FK CASCADE cleans up child rows).
- **`seeded_user`** (`tests/seed_fixtures.py`, module scope) — registers one authoritative user with a deterministic 25-game portfolio (platforms × time controls × colors × WDL, endgame-class transitions, clock data crossing the `MIN_GAMES_FOR_CLOCK_STATS=10` threshold). Committed to `flawchess_test` so HTTP endpoints observe it through the patched session maker. Exposes an `EXPECTED` aggregates dict verified against spec at import time, so assertions reference named expectations rather than hand-counted numbers. Registered via `pytest_plugins = ["tests.seed_fixtures"]` in `conftest.py`.
- **Chess fixtures:** `starting_board`, `empty_board` (python-chess `Board`).
- **`engine_started`** (session scope) — starts Stockfish once per session; skips silently if `stockfish` is not on PATH.
- **Helpers (not fixtures):** `ensure_test_user(session, user_id)` in `conftest.py` inserts a User to satisfy FK constraints. There is **no `tests/helpers.py`** — tests build ORM rows inline with `session.add(Game(...))` / `session.add(GamePosition(...))`, or call local module-level `_create_test_*` helpers within a test file.
- **Sentry is disabled in tests** — `conftest.py` sets `SENTRY_DSN=""` before any app import so test-triggered exceptions don't leak to the real Sentry project. `PYDANTIC_AI_MODEL_INSIGHTS="test"` is also set so LLM Agent construction passes startup validation without a real API key.

### Frontend
No shared fixture module and no setup file. Test data is defined inline per file as typed literals using real domain types from `@/types/*`.

## Mocking

### Backend
`unittest.mock` (`AsyncMock`, `MagicMock`, `patch`, `patch.object`) plus pytest `monkeypatch` — no third-party mock library. Observed usage frequency: `AsyncMock` (~377), `patch(...)` (~247), `monkeypatch` (~120), `MagicMock` (~90), `patch.object` (~3). LLM tests use pydantic-ai's `TestModel` / `FunctionModel`.

- **External HTTP** (chess.com / lichess via httpx) is mocked with `AsyncMock` / `patch`.
- **LLM calls:** the `fake_insights_agent` fixture monkeypatches `app.services.insights_llm.get_insights_agent` with a pydantic-ai `Agent(TestModel(...))` that returns a canned `EndgameInsightsReport`, and clears the `lru_cache` so cached real Agents don't leak.

**What to mock:** external network boundaries (LLM provider, chess.com / lichess HTTP), the I/O seam functions.
**What NOT to mock:** the database (use the real Postgres `db_session` / `seeded_user` fixtures), pure domain logic (Zobrist hashing, endgame classification, WDL math, normalization) — test these against real implementations.

### Frontend
Vitest `vi.mock` / `vi.fn` (`vi` imported from `'vitest'`). Hooks that call the API are tested by mocking the fetch/query layer or wrapping in a `QueryClientProvider`; pure transforms are called directly. Component tests render real components and assert on the DOM via `screen` queries + `.toBeTruthy()` / `.toBeNull()`.

## Coverage

**Requirements:** none enforced (no `--cov-fail-under`, no CI coverage gate). Coverage is opt-in.

**View coverage:**
```bash
uv run pytest --cov                       # backend (source = app)
cd frontend && npx vitest run --coverage  # frontend (v8 provider)
```

## Test Types

- **Unit tests** — pure domain logic (`test_zobrist.py`, `test_normalization.py`, `test_material_tally.py`, `test_position_classifier.py`; frontend `zobrist.test.ts`, `clockFormat.test.ts`, `recency.test.ts`).
- **Service/repository integration tests** — real services/repositories against the rollback-scoped `db_session` (`test_stats_service.py`, `test_endgame_service.py`, `test_query_utils.py`, `test_*_repository.py`).
- **Router/endpoint integration tests** — full FastAPI request path against the `seeded_user` portfolio (`test_stats_router.py`, `test_endgames_router.py`, `test_insights_router.py`, `test_integration_routers.py`, `test_auth.py`, OAuth/guest flows).
- **Migration tests** — assert specific Alembic migrations behave (`test_migration_91_evals_completed_at.py`, `test_llm_logs_migration.py`).
- **Frontend component & page tests** — RTL renders of charts, cards, popovers, hooks, and whole pages (`Endgames.*`, `Import.*`, `Openings.*`); require the `// @vitest-environment jsdom` pragma.
- **E2E:** none in-repo. Browser automation is supported via `data-testid` / semantic-HTML conventions (see CONVENTIONS.md) for external tooling, but no Playwright/Cypress suite exists.

## Common Patterns

**Async testing (backend):** `async def test_...(db_session):` with no marker (auto mode). Use `db_session` for rollback isolation; use `fresh_test_user` / `seeded_user` when commits must persist.

**Error testing (backend):** `with pytest.raises(...)` for expected exceptions (used in ~9 files, e.g. `test_zobrist.py`). For endpoint error paths, assert on `response.status_code` (400/401/404).

**FK-safe seeding:** call `ensure_test_user(db_session, uid)` before inserting any row with a `user_id` FK.

**jsdom pragma (frontend):** any test that calls `render(...)` or `renderHook(...)` MUST start with `// @vitest-environment jsdom` as line 1.

**Pre-PR test gate (`CLAUDE.md`, MANDATORY before push):**
```bash
uv run ruff format app/ tests/
uv run ruff check app/ tests/ --fix
uv run ty check app/ tests/
uv run pytest -x
( cd frontend && npm run lint && npm test -- --run )
```
CI runs the same gates. The git pre-push hook (`bin/install_pre_push_hook.sh`) runs ruff + ty but intentionally excludes pytest for speed — run pytest manually before opening a PR. Frontend CI also runs `npm run knip`.

---

*Testing analysis: 2026-05-30*
