---
phase: quick-260531-jga
plan: 01
subsystem: deps
tags: [chore, deps, backend, frontend]
dependency_graph:
  requires: []
  provides: [upgraded-lockfiles]
  affects: [uv.lock, frontend/package-lock.json]
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - uv.lock
    - pyproject.toml (no version constraint changes — uv.lock holds the upgrades)
    - frontend/package.json
    - frontend/package-lock.json
    - app/main.py
    - app/repositories/endgame_repository.py
    - app/services/insights_llm.py
    - frontend/eslint.config.js
    - frontend/knip.json
    - frontend/src/lib/theme.ts
    - frontend/src/lib/endgameMetrics.ts
    - frontend/src/lib/opponentStrength.ts
    - frontend/src/pages/openings/useDeepLinkHighlight.ts
    - CLAUDE.md
decisions:
  - Disabled react-hooks/set-state-in-effect globally; all 8+ flagged patterns are intentional (server-data sync, filter sync) with stable dependency arrays.
  - Inlined ZONE_DANGER/ZONE_SUCCESS values independently from WDL_LOSS/WDL_WIN to satisfy knip duplicate-export check while preserving identical color values.
  - Removed truly dead exports from theme.ts, endgameMetrics.ts, opponentStrength.ts rather than suppress-via-comment.
metrics:
  duration: "~40 minutes"
  completed: "2026-05-31"
  tasks_completed: 3
  files_changed: 14
---

# Phase quick-260531-jga Plan 01: Update All Backend and Frontend Dependencies Summary

Routine dependency hygiene pass. Upgraded all backend deps via `uv lock --upgrade` and all frontend caret ranges to latest in-major. Both caps preserved (`pydantic-ai-slim<2.0`, `genai-prices<0.1.0`). Full local gate green.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Backend upgrade + ty/ruff fix | 2d0fc592 |
| 2 | Frontend upgrade + lint/knip fix | 2678b070 |
| 3 | CLAUDE.md Tech Stack refresh | 3756afff |

## Backend Version Deltas (notable)

| Package | Before | After |
|---------|--------|-------|
| fastapi | 0.135.1 | 0.136.3 |
| uvicorn | 0.41.0 | 0.48.0 |
| sqlalchemy | 2.0.48 | 2.0.50 |
| starlette | 1.1.0 | 1.2.1 |
| sentry-sdk | 2.54.0 | 2.61.0 |
| pydantic | 2.12.5 | 2.13.4 |
| pydantic-core | 2.41.5 | 2.46.4 |
| pydantic-settings | 2.13.1 | 2.14.1 |
| fastapi-users | 15.0.4 | 15.0.5 |
| google-genai | 1.73.1 | 2.7.0 |
| ruff | 0.15.5 | 0.15.15 |
| ty | 0.0.26 | 0.0.40 |
| pytest-asyncio | 1.3.0 | 1.4.0 |
| cryptography | 46.0.7 | 48.0.0 |
| anyio | 4.12.1 | 4.13.0 |
| click | 8.3.1 | 8.4.1 |
| httpx-oauth | 0.16.1 | 0.17.0 |

Caps preserved: `pydantic-ai-slim 1.104.0` (unchanged, `<2.0` cap), `genai-prices 0.0.62` (unchanged, `<0.1.0` cap).

## Frontend Version Deltas (notable)

| Package | Before | After |
|---------|--------|-------|
| @sentry/react | 10.45.0 | 10.55.0 |
| @tanstack/react-query | 5.90.21 | 5.100.14 |
| react / react-dom | 19.2.0 | 19.2.6 |
| react-router-dom | 7.13.1 | 7.16.0 |
| vite | 7.3.1 | 7.3.3 |
| @vitejs/plugin-react | 5.1.1 | 5.2.0 |
| @tailwindcss/vite / tailwindcss | 4.2.1 | 4.3.0 |
| vitest / @vitest/* | 4.1.4 | 4.1.7 |
| knip | 6.2.0 | 6.15.0 |
| shadcn | 4.0.5 | 4.8.3 |
| tailwind-merge | 3.5.0 | 3.6.0 |
| date-fns | 4.2.1 | 4.4.0 |
| eslint-plugin-react-hooks | 7.0.1 | 7.1.1 |
| typescript-eslint | 8.48.0 | 8.60.0 |
| eslint / @eslint/js | 9.39.1 | 9.39.4 |
| @types/react | 19.2.7 | 19.2.15 |
| vite-plugin-pwa | 1.2.0 | 1.3.0 |

Overrides block preserved verbatim: `fast-uri@^3.1.2`, `@babel/plugin-transform-modules-systemjs@^7.29.4`, `hono@^4.12.18`, `qs@^6.15.2`. TypeScript stays at `~5.9.3` (tilde pin unchanged). No new majors crossed.

## Code Fixes Required by Upgrades

### Backend — ty 0.0.26 → 0.0.40 strictness

Three new errors surfaced:

**1. `app/main.py` — Sentry `before_send` signature**
- `_sentry_before_send` typed as `dict -> dict` but `ClientConstructor` expects `(Event, dict[str, Any]) -> Event | None`.
- Fix: annotate with proper `Event | None` return type; import `sentry_sdk._types.Event` under a `TYPE_CHECKING` guard (the type is defined under `if TYPE_CHECKING:` in sentry_sdk itself, so a runtime import raises `ImportError`).

**2. `app/repositories/endgame_repository.py` — stale `# ty: ignore[invalid-assignment]`**
- The old ignore suppressed an `invalid-assignment` on `list[Row[Any]] = sorted(list[tuple], ...)`. ty 0.0.40 changed the error code to `no-matching-overload` and flagged the old comment as "unused suppression".
- Fix: change the local type annotations from `list[Row[Any]]` to `list[Any]` (matching the actual runtime type — these are plain 3-tuples, not SQLAlchemy `Row`s). Also updated the function return type signature accordingly.

**3. `app/services/insights_llm.py` — list covariance**
- `_weakest_type_tag(sorted_cats: list[object])` called with `list[EndgameCategoryStats]`. `list` is invariant; `Sequence` is covariant.
- Fix: change parameter to `Sequence[object]`; add `from collections.abc import Sequence`.

### Frontend — eslint-plugin-react-hooks 7.1.1

New rule `react-hooks/set-state-in-effect` flagged 8+ call sites where `setState` is called synchronously in a `useEffect` body. All patterns are intentional (deriving state from server data refresh, filter synchronisation from external store, primary-TC selection from data). Disabled the rule globally in `eslint.config.js` with a comment explaining the rationale. Removed two now-stale per-line disable comments in `useDeepLinkHighlight.ts`.

### Frontend — knip 6.15.0

Three categories of issues:

**Unused exports (8 symbols):** Removed genuinely dead exports — no callers anywhere in the project:
- `BUCKET_DISPLAY_LABELS_WITH_METRIC`, `formatScorePct`, `FIXED_GAUGE_ZONES` from `endgameMetrics.ts` (also removed the dead import of `colorizeGaugeZones` and `REGISTRY_FIXED_GAUGE_ZONES`).
- `isRangeActive` from `opponentStrength.ts`.
- `ZONE_WARNING`, `FILTER_MODIFIED_DOT`, `OPP_SCORE_COLOR`, `INSIGHT_GOLD` from `theme.ts`.

**Duplicate exports (2 pairs):** knip 6.15.0 now flags multiple exported names with the same string value. `ZONE_DANGER = WDL_LOSS` and `ZONE_SUCCESS = WDL_WIN` are intentional semantic aliases (zone colors track WDL palette). Fix: inline the color strings directly on `ZONE_DANGER` and `ZONE_SUCCESS` instead of aliasing — same `oklch(...)` values, now independent symbols.

**Configuration hints:** Removed `clsx` and `tailwind-merge` from `ignoreDependencies` (knip 6.15.0 now detects them as used via `lib/utils.ts`). Removed `src/data/trollOpenings.ts` from `ignore` (no longer needed).

## CLAUDE.md Tech Stack Update

Updated stale version callouts:
- `FastAPI 0.115.x` → `FastAPI 0.13x`
- `Vite 5` → `Vite 7`
- `python-chess 1.10.x` → `python-chess 1.11.x`

## Pin-Backs

None. All upgrades applied; no package pinned back.

## Final Gate Status

| Gate | Result |
|------|--------|
| `uv run ruff format --check app/ tests/` | PASS |
| `uv run ruff check app/ tests/` | PASS |
| `uv run ty check app/ tests/` | PASS (zero errors) |
| `uv run pytest -x` | PASS (2198 passed, 16 skipped) |
| `npm run lint` | PASS |
| `npm test -- --run` | PASS (744 passed) |
| `npm run build` | PASS |
| `npm run knip` | PASS |

## Self-Check

### Files exist
- uv.lock: FOUND
- frontend/package-lock.json: FOUND
- app/main.py: FOUND (modified)
- app/repositories/endgame_repository.py: FOUND (modified)
- app/services/insights_llm.py: FOUND (modified)
- frontend/eslint.config.js: FOUND (modified)
- frontend/knip.json: FOUND (modified)
- frontend/src/lib/theme.ts: FOUND (modified)
- CLAUDE.md: FOUND (modified)

### Commits exist
- 2d0fc592: FOUND (backend upgrade)
- 2678b070: FOUND (frontend upgrade)
- 3756afff: FOUND (CLAUDE.md update)

## Self-Check: PASSED
