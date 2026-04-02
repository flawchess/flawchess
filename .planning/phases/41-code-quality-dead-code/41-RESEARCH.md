# Phase 41: Code Quality & Dead Code - Research

**Researched:** 2026-04-02
**Domain:** Code quality tooling, TypeScript strictness, CI pipeline, dead code detection, naming conventions
**Confidence:** HIGH

## Summary

Phase 41 is a housekeeping phase with four concrete workstreams: (1) install and configure Knip for frontend dead export detection and add it to CI, (2) enable `noUncheckedIndexedAccess` in `tsconfig.app.json` and fix the resulting 56 type errors across 14 files, (3) add `npm run build` and `npm test` to the CI workflow, and (4) review naming consistency and extract a shared `_apply_game_filters` utility from three near-identical backend repository implementations.

The codebase is in good shape overall: ruff, ty, and ESLint all pass clean. The frontend build passes, tests pass (31/31). The main work is additive tooling plus targeted fixes. The `noUncheckedIndexedAccess` error count (56) is higher than the context estimate of 10-30 — the real count was determined by running `tsc --noUncheckedIndexedAccess` directly. The files with the most errors are `Openings.tsx` (17 errors, all `Record` key access where a filter guard already ensures the value exists) and `zobrist.ts` (11 errors, array index access in hash computation).

**Primary recommendation:** Install Knip first (Wave 1) so subsequent waves can use it to verify dead code removals. Fix `noUncheckedIndexedAccess` last (Wave 3) after the Knip report has confirmed which code is live.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Rename API endpoints freely — no external consumers exist, so update frontend calls in lockstep. No backward compatibility needed.
- **D-02:** Fix naming inconsistencies only (plural vs singular, verb vs noun mismatches). Do not restructure working paths into strict RESTful nested resources.
- **D-03:** Frontend: Add Knip (knip.dev) as a CI step. Run it, review the report, remove confirmed dead exports. Integrate into CI pipeline as a permanent check to prevent regression.
- **D-04:** Backend: Manual review + ruff for dead code detection. No additional tooling (vulture, etc.) — the backend is small enough (~12 service/repo files) for manual review.
- **D-05:** Skip Oxlint, Biome, Madge, ts-prune, eslint-plugin-react-compiler — current tooling is sufficient at this scale.
- **D-06:** Extract to existing files (lib/utils.ts, app/utils/) unless the shared logic is domain-specific enough to warrant its own module.
- **D-07:** Review internal function/variable names but only rename when genuinely confusing or inconsistent with neighboring code. Don't rename for style preference alone.
- **D-08:** Enable `noUncheckedIndexedAccess` in tsconfig.json. Fix the resulting type errors (expect 10-30 fixes, mostly adding nullish checks).
- **D-09:** Add `npm test` and `npm run build` to CI workflow. Currently only backend is tested in CI — frontend type errors and test failures can slip into main.

### Claude's Discretion

- Deduplication threshold: use judgment per case — extract when 3+ copies exist or when duplication is a maintenance risk, skip when abstraction would hurt readability (D-06 context)
- Frontend file naming: review current patterns and align outliers to majority convention (PascalCase components, camelCase hooks) if inconsistencies exist

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TOOL-03 | Evaluate and optionally integrate knip.dev (or similar) for frontend dead export detection | Knip 6.2.0 is the right tool; no barrel files present makes Knip more accurate; plugins for Vite and Vitest auto-activate from devDependencies |
| QUAL-01 | Review and improve naming across codebase (API endpoints, routes, variables) | `/games/count` is misplaced in analysis.py; router prefix inconsistency documented; `conv-recov` abbreviation reviewed |
| QUAL-02 | Identify and eliminate code duplication (DRY principle) | `_apply_game_filters` duplicated across 3 repos; filter param building duplicated 5x in `client.ts`; `recency_cutoff`/`derive_user_result` correctly in analysis_service but imported cross-service — candidate for a shared utils module |
| QUAL-03 | Identify and remove dead code across backend and frontend | Ruff passes clean; ESLint passes clean; Knip not yet run; `noUncheckedIndexedAccess` surfaced 56 latent type errors across 14 files |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| knip | 6.2.0 (latest) | Frontend dead export, unused file, and unused dependency detection | Replaces deprecated ts-prune; active project ~10.6k stars; plugins for Vite+Vitest auto-activate |
| TypeScript | ~5.9.3 (already installed) | `noUncheckedIndexedAccess` is a compiler flag, not a new dep | Part of existing toolchain |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ruff | already installed | Backend dead code detection (F401 unused imports, F811 redefinitions) | Already enforced in CI; run manually during manual review |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| knip | ts-prune | ts-prune is deprecated; knip is the successor |
| knip | eslint-plugin-unused-imports | ESLint plugin covers unused imports; Knip covers unused exports, files, and dependencies too |

**Installation:**
```bash
cd frontend && npm install -D knip
```

**Version verification:** Confirmed 6.2.0 via `npm view knip version` on 2026-04-02.

## Architecture Patterns

### Knip Configuration

Knip auto-detects Vite and Vitest from `devDependencies` — no manual plugin activation needed. The project uses Tailwind CSS v4 via `@tailwindcss/vite` (Vite plugin, no `tailwind.config.ts`) so Knip's Tailwind plugin will not activate — this is expected and fine.

The project has no barrel/index files. This is ideal for Knip: every export is tracked directly without re-export chains complicating the analysis.

**`frontend/knip.json` (minimal starting point):**
```json
{
  "$schema": "https://unpkg.com/knip@6/schema.json",
  "entry": ["src/main.tsx", "src/prerender.tsx"],
  "project": ["src/**/*.{ts,tsx}"]
}
```

**`frontend/package.json` script:**
```json
{
  "scripts": {
    "knip": "knip"
  }
}
```

**CI step (add after eslint step in `.github/workflows/ci.yml`):**
```yaml
- name: Type check (tsc)
  run: npm run build
  working-directory: frontend

- name: Run tests (vitest)
  run: npm test
  working-directory: frontend

- name: Dead code check (knip)
  run: npm run knip
  working-directory: frontend
```

Note: `npm run build` runs `tsc -b && vite build` — this catches TypeScript compilation errors including `noUncheckedIndexedAccess` once enabled. Placing build before test ensures type errors are caught first.

### `noUncheckedIndexedAccess` Fix Patterns

**Pattern 1: Record key access with prior filter guard** (17 errors in Openings.tsx)
```typescript
// Before: TS doesn't track that filter already ensured wdlStatsMap[b.id] exists
.filter((b) => wdlStatsMap[b.id] && wdlStatsMap[b.id].total > 0)
.map((b) => ({ stats: wdlStatsMap[b.id] }))  // error: possibly undefined

// After: local variable narrows the type
.filter((b) => {
  const s = wdlStatsMap[b.id];
  return s !== undefined && s.total > 0;
})
.map((b) => ({ stats: wdlStatsMap[b.id]! }))  // non-null assertion safe here
```

**Pattern 2: Array access where length is checked** (common in zobrist.ts)
```typescript
// Before
const val = arr[index];  // string | undefined
fn(val);                  // error: undefined not assignable to string

// After option A: assert (when logically guaranteed)
const val = arr[index]!;

// After option B: throw on missing (defensive)
const val = arr[index];
if (val === undefined) throw new Error(`Missing value at index ${index}`);
fn(val);
```

**Pattern 3: Array[0] where length guard exists**
```typescript
// Before
const first = dates[0];  // string | undefined

// After: use at() or guard
const first = dates[0];  // check length before access
if (dates.length === 0) return;
const first = dates[0]!;
```

**Pattern 4: `Record<string, T>` access**
```typescript
// Before
const TYPE_LABELS: Record<string, string> = { ... };
label: TYPE_LABELS[key]   // string | undefined

// After: nullish fallback
label: TYPE_LABELS[key] ?? key
```

### Backend Deduplication: `_apply_game_filters`

Three repositories each have a private `_apply_game_filters` function:

| Repository | Location | Differs by |
|------------|----------|------------|
| `analysis_repository.py` | line 244 | Has `color: str | None` parameter |
| `endgame_repository.py` | line 280 | No `color` parameter (D-02: endgames are color-agnostic) |
| `stats_repository.py` | line 164 | No `color` parameter; missing type annotation on `stmt` |

The endgame and stats versions are nearly identical. The analysis version adds a `color` filter. Decision D-06 directs extraction to `app/utils/` — but since all three are SQLAlchemy statement builders importing `Game` model, a shared `app/repositories/query_utils.py` (or `app/utils/query_filters.py`) is the right location.

**Proposed shared utility:**
```python
# app/repositories/query_utils.py
from collections.abc import Sequence
import datetime
from sqlalchemy import Select
from app.models.game import Game

def apply_game_filters(
    stmt: Select,
    time_control: Sequence[str] | None,
    platform: Sequence[str] | None,
    rated: bool | None,
    opponent_type: str,
    recency_cutoff: datetime.datetime | None,
    color: str | None = None,  # None = no color filter (endgames/stats)
) -> Select:
    """Apply standard game filter WHERE clauses to a SELECT statement."""
    if time_control is not None:
        stmt = stmt.where(Game.time_control_bucket.in_(time_control))
    if platform is not None:
        stmt = stmt.where(Game.platform.in_(platform))
    if rated is not None:
        stmt = stmt.where(Game.rated == rated)
    if opponent_type == "human":
        stmt = stmt.where(Game.is_computer_game == False)  # noqa: E712
    elif opponent_type == "bot":
        stmt = stmt.where(Game.is_computer_game == True)  # noqa: E712
    if recency_cutoff is not None:
        stmt = stmt.where(Game.played_at >= recency_cutoff)
    if color is not None:
        stmt = stmt.where(Game.user_color == color)
    return stmt
```

Note: `recency_cutoff` and `derive_user_result` in `analysis_service.py` are imported by `endgame_service.py` and `stats_service.py`. They are not really analysis-specific — they are general filter/result utilities. D-06 says extract to `app/utils/` when it makes sense. Moving them to `app/utils/game_filters.py` or keeping them in analysis_service.py is a discretion call — since they're already exported and working, only move if the cross-service import feels wrong.

### Frontend Deduplication: Filter Params Builder

In `frontend/src/api/client.ts`, the endgame API functions (`getStats`, `getGames`, `getPerformance`, `getTimeline`, `getConvRecovTimeline`) each build the same params object with the same conditional spreading logic (5 copies, ~8 lines each). This is the primary frontend duplication target.

```typescript
// Extracted helper (add to client.ts or lib/utils.ts):
function buildFilterParams(params: {
  time_control?: string[] | null;
  platform?: string[] | null;
  recency?: string | null;
  rated?: boolean | null;
  opponent_type?: string;
  window?: number;
  [key: string]: unknown;
}): Record<string, unknown> {
  return {
    ...(params.time_control ? { time_control: params.time_control } : {}),
    ...(params.platform ? { platform: params.platform } : {}),
    ...(params.recency && params.recency !== 'all' ? { recency: params.recency } : {}),
    ...(params.rated !== null && params.rated !== undefined ? { rated: params.rated } : {}),
    ...(params.opponent_type && params.opponent_type !== 'all' ? { opponent_type: params.opponent_type } : {}),
    ...(params.window ? { window: params.window } : {}),
  };
}
```

Note: `statsApi.getRatingHistory` and `getGlobalStats` use a simpler pattern (`{ ...(recency ? { recency } : {}), ...}`) — these are too small to warrant extraction.

### Anti-Patterns to Avoid

- **Extracting into a new file when the shared code is small**: `_apply_game_filters` fits in a `query_utils.py` module adjacent to the repositories, not in a deeply nested utils directory.
- **Using `// @ts-ignore` instead of `!` for noUncheckedIndexedAccess**: The project uses `# ty: ignore[rule-name]` for backend suppressions. For frontend, prefer `!` (non-null assertion) or `?? fallback` — avoid `// @ts-ignore` which suppresses all errors on the line.
- **Changing naming for style preference**: D-07 is explicit — only rename when genuinely confusing or inconsistent.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dead export detection | Custom AST walker | knip | Handles re-exports, plugins, entry points correctly |
| Array bounds checking | Manual length checks everywhere | `!` assertion or `?? fallback` | noUncheckedIndexedAccess + targeted assertions is idiomatic |

## Common Pitfalls

### Pitfall 1: Knip False Positives from Vite Entry Points
**What goes wrong:** Knip may report `main.tsx`, `prerender.tsx`, or components lazy-loaded via React Router as unused.
**Why it happens:** Knip needs explicit entry points to follow the import graph.
**How to avoid:** Configure `entry` in `knip.json` to include `src/main.tsx` and `src/prerender.tsx`. If dynamic imports are used, add them to entry too.
**Warning signs:** Knip reports entire page components as unused.

### Pitfall 2: `noUncheckedIndexedAccess` on `Record<number, T>` after runtime guard
**What goes wrong:** TypeScript control flow analysis does not narrow `Record<K, V>[key]` to `V` after a truthy check — the type remains `V | undefined` even inside a `.filter()` callback.
**Why it happens:** TypeScript's flow narrowing works on local variables, not on computed property accesses.
**How to avoid:** Assign `const s = record[key]` before the check so TS can narrow `s`.
**Warning signs:** Errors like `'b.stats' is possibly 'undefined'` in lines immediately after a filter that checked `wdlStatsMap[b.id]`.

### Pitfall 3: Knip reports false positives for exports used only in tests
**What goes wrong:** `tsconfig.app.json` excludes test files (`src/**/*.test.ts`). Knip may see exports used only in tests as dead.
**Why it happens:** Test files are excluded from the compilation project, so Knip's TypeScript-based analysis may not see their imports.
**How to avoid:** Verify the Vitest plugin activated (it reads test patterns from vitest config embedded in vite.config.ts). If false positives appear, add `"ignoreExportsUsedInFile": true` or list specific patterns in `knip.json`.
**Warning signs:** Knip reports functions from `arrowColor.ts` as unused (they are tested in `arrowColor.test.ts`).

### Pitfall 4: CI `npm run build` fails due to `noUncheckedIndexedAccess` if enabled before fix
**What goes wrong:** Enabling the flag in `tsconfig.app.json` before fixing all 56 errors will immediately break `npm run build` in CI.
**Why it happens:** `npm run build` calls `tsc -b && vite build`, so TypeScript errors fail the step.
**How to avoid:** Fix all `noUncheckedIndexedAccess` errors locally and verify `npm run build` passes before adding the CI step. Or add CI steps first, then enable the flag + fix errors in a single commit.
**Warning signs:** CI build step fails with `TS2532: Object is possibly 'undefined'`.

### Pitfall 5: API rename breaks existing frontend calls
**What goes wrong:** The context decision is clear (D-01: rename freely), but it's easy to miss a call site.
**Why it happens:** Frontend calls appear in both hooks (`useImport.ts`) and page files (`Import.tsx`, `Dashboard.tsx`, `Openings.tsx`) — some endpoints are called from multiple files.
**How to avoid:** After renaming an endpoint in Python, grep the frontend for the old path string before committing.
**Warning signs:** 404 errors in browser console after rename.

## Code Examples

### Knip CI Step (GitHub Actions)
```yaml
# Source: https://knip.dev/guides/using-knip-in-ci
- name: Dead code check (knip)
  run: npm run knip
  working-directory: frontend
```

Knip exits with code 1 when issues are detected, causing the CI step to fail automatically. The `--no-progress` flag activates automatically in CI environments.

### Enabling `noUncheckedIndexedAccess` in tsconfig.app.json
```json
// Source: TypeScript 5.9 docs - noUncheckedIndexedAccess
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,  // Add this line
    // ... existing options
  }
}
```

Note: `tsconfig.app.json` is the right file — it controls `src/` compilation. The root `tsconfig.json` only references `tsconfig.app.json` and `tsconfig.node.json`.

### Backend Router Prefix Consistency
```python
# Current inconsistency: some routers embed prefix in path strings,
# some use the APIRouter prefix= parameter
# analysis.py has no prefix on the router but hardcodes /analysis/* paths
# This is a naming review item per D-02

# Consistent pattern (follow imports.py model):
router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.post("/positions", ...)   # results in /api/analysis/positions
@router.post("/time-series", ...) # results in /api/analysis/time-series
@router.post("/next-moves", ...)  # results in /api/analysis/next-moves

# /games/count should move to a more appropriate router
# Option: keep in analysis.py but with clear naming, or move to imports.py
# since game count is import-related context
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ts-prune for dead export detection | knip | 2022 (ts-prune deprecated) | Knip handles plugins, monorepos, entry points |
| `noUncheckedIndexedAccess` as optional | Default in tsc --init (TS 5.9) | TS 5.9 (late 2025) | New projects get it by default; existing projects need opt-in |

**Deprecated/outdated:**
- `ts-prune`: Archived/deprecated, replaced by knip
- TypeScript's `noUncheckedSideEffectImports`: Already enabled in this project's `tsconfig.app.json` (line 25) — this catches side-effect-only imports; different from `noUncheckedIndexedAccess`

## Open Questions

1. **Knip false positive rate**
   - What we know: Knip 6.2.0 with Vite+Vitest plugins auto-activated; no barrel files
   - What's unclear: Whether any components are used only via dynamic imports or string-based routes
   - Recommendation: Run `knip` after install and review the report before acting on it; use `ignoreExportsUsedInFile: true` if test-only exports flag

2. **`recency_cutoff` and `derive_user_result` in analysis_service.py**
   - What we know: Both are imported by `endgame_service.py` and `stats_service.py`; D-06 says extract to `app/utils/` when warranted
   - What's unclear: Whether the planner should create `app/utils/game_filters.py` or leave them in analysis_service
   - Recommendation: Move them to `app/utils/game_filters.py` — they have no dependency on analysis logic, only on datetime and string parsing

3. **`/games/count` endpoint placement**
   - What we know: Lives in `analysis.py` with no router prefix; used by both `Dashboard.tsx` and `Openings.tsx`; returns game count for current user (import context, not analysis context)
   - What's unclear: Whether to move it to `users.py` (under `/api/users/games/count`) or `imports.py` (under `/api/imports/games/count`) or keep as-is with just a router prefix fix
   - Recommendation: Move to `users.py` alongside `/me/profile` — game count is a user account stat. New path: `/api/users/games/count`. Update both frontend call sites.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Knip, npm ci | ✓ | 24.14.0 | — |
| npm | Package install | ✓ | 11.9.0 | — |
| Python | Backend ruff/ty | ✓ | 3.13.12 | — |
| uv | Backend tooling | ✓ | 0.10.9 | — |
| knip | Dead code detection | ✗ (not installed) | — | Install: `npm install -D knip` |

**Missing dependencies with no fallback:**
- knip: must be installed before the dead code detection wave

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (frontend) | Vitest 4.1.1 |
| Config file | Embedded in `vite.config.ts` (no separate vitest.config) |
| Quick run command | `cd frontend && npm test` |
| Full suite command | `cd frontend && npm test` (only 1 test file, runs in ~130ms) |
| Framework (backend) | pytest with asyncio_mode=auto |
| Quick run command | `uv run pytest` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TOOL-03 | Knip installed and runs in CI | smoke | `cd frontend && npm run knip` | ❌ Wave 0 (knip must be installed) |
| QUAL-01 | API endpoints renamed correctly (no 404s) | integration | `uv run pytest tests/test_*_router.py` | ✅ |
| QUAL-02 | Shared `_apply_game_filters` doesn't break existing tests | integration | `uv run pytest tests/test_analysis_repository.py tests/test_endgame_repository.py tests/test_stats_repository.py` | ✅ |
| QUAL-02 | Frontend filter param builder works | — | Build passes (`npm run build`) | ✅ build test |
| QUAL-03 | Backend dead code removed (ruff clean) | lint | `uv run ruff check app/` | ✅ |
| QUAL-03 | Frontend dead exports removed (knip clean) | lint | `cd frontend && npm run knip` | ❌ Wave 0 |
| D-08 | `noUncheckedIndexedAccess` enabled, no type errors | type check | `cd frontend && npm run build` | ✅ (build includes tsc) |
| D-09 | CI catches frontend type errors | CI | Run CI workflow after PR | ✅ existing CI |

### Sampling Rate
- **Per task commit:** `uv run ruff check app/ && cd frontend && npm run build && npm test`
- **Per wave merge:** Full suite: `uv run pytest && cd frontend && npm run knip && npm run build && npm test`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `frontend/knip.json` — Knip config (needs creation before TOOL-03 can be tested)
- [ ] `npm install -D knip` — Knip package must be installed and added to `package.json`

*(All backend test infrastructure is in place. Frontend has one test file covering `arrowColor.ts`.)*

## Sources

### Primary (HIGH confidence)
- `https://knip.dev/guides/using-knip-in-ci` — CI exit codes, GitHub Actions example, `--cache` flag
- `https://knip.dev/reference/configuration` — `entry`, `project`, `ignoreExportsUsedInFile`, `ignoreIssues` options
- `https://knip.dev/reference/plugins/vite` — Vite plugin auto-activation from devDependencies
- `https://knip.dev/reference/plugins/vitest` — Vitest plugin auto-activation, test pattern detection
- Direct code inspection of all router files, repository files, `client.ts`, `tsconfig.app.json`, `ci.yml`
- `tsc --noUncheckedIndexedAccess` run on live codebase — 56 errors across 14 files (2026-04-02)
- `npm view knip version` — confirmed 6.2.0 as current release (2026-04-02)

### Secondary (MEDIUM confidence)
- TypeScript 5.9 docs on `noUncheckedIndexedAccess` — standard flag, well-documented behavior

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — knip version confirmed from npm registry; TypeScript flag behavior confirmed by live tsc run
- Architecture patterns: HIGH — all code inspection done against actual files; CI workflow read directly
- Pitfalls: HIGH — most derived from running the actual tools (tsc, ruff, eslint) rather than speculation

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable ecosystem; knip versioning is the only fast-moving item)
