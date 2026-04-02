# Phase 41: Code Quality & Dead Code - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Clean up the codebase: improve naming consistency across API endpoints and internal code, eliminate significant code duplication, and remove dead code from both backend and frontend. Also fold in two high-value small items: enable `noUncheckedIndexedAccess` in tsconfig and add frontend build/test steps to CI.

</domain>

<decisions>
## Implementation Decisions

### API Naming & Breaking Changes
- **D-01:** Rename API endpoints freely — no external consumers exist, so update frontend calls in lockstep. No backward compatibility needed.
- **D-02:** Fix naming inconsistencies only (plural vs singular, verb vs noun mismatches). Do not restructure working paths into strict RESTful nested resources.

### Dead Code Strategy
- **D-03:** Frontend: Add Knip (knip.dev) as a CI step. Run it, review the report, remove confirmed dead exports. Integrate into CI pipeline as a permanent check to prevent regression.
- **D-04:** Backend: Manual review + ruff for dead code detection. No additional tooling (vulture, etc.) — the backend is small enough (~12 service/repo files) for manual review.
- **D-05:** Skip Oxlint, Biome, Madge, ts-prune, eslint-plugin-react-compiler — current tooling is sufficient at this scale.

### Deduplication
- **D-06:** Extract to existing files (lib/utils.ts, app/utils/) unless the shared logic is domain-specific enough to warrant its own module.

### Naming Scope
- **D-07:** Review internal function/variable names but only rename when genuinely confusing or inconsistent with neighboring code. Don't rename for style preference alone.

### Folded Items (outside strict phase scope but high-value)
- **D-08:** Enable `noUncheckedIndexedAccess` in tsconfig.json. Fix the resulting type errors (expect 10-30 fixes, mostly adding nullish checks).
- **D-09:** Add `npm test` and `npm run build` to CI workflow. Currently only backend is tested in CI — frontend type errors and test failures can slip into main.

### Claude's Discretion
- Deduplication threshold: use judgment per case — extract when 3+ copies exist or when duplication is a maintenance risk, skip when abstraction would hurt readability (D-06 context)
- Frontend file naming: review current patterns and align outliers to majority convention (PascalCase components, camelCase hooks) if inconsistencies exist

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Frontend tooling
- `frontend/package.json` — Current dependencies and scripts; where knip config/scripts will be added
- `frontend/tsconfig.json` — Where `noUncheckedIndexedAccess` will be enabled
- https://knip.dev — Knip documentation for configuration and CI integration

### CI pipeline
- `.github/workflows/ci.yml` — Current CI pipeline; needs knip step and frontend build/test steps

### Backend code quality
- `app/routers/` — API endpoint paths to review for naming consistency
- `app/services/` — Primary target for deduplication and dead code review
- `app/repositories/` — Secondary target for deduplication review

### Frontend code quality
- `frontend/src/lib/` — Existing shared utilities; destination for extracted duplicated logic
- `frontend/src/hooks/` — Hook files to review for naming and dead exports
- `frontend/src/components/` — Component files to review for dead exports

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Ruff already catches unused imports in backend code — extends naturally to dead code review
- ESLint 9 with react-hooks@7 already covers frontend linting
- TypeScript strict mode already enabled — `noUncheckedIndexedAccess` is an incremental addition

### Established Patterns
- Backend: `routers/` → `services/` → `repositories/` layering — check each layer for naming consistency
- Frontend: hooks follow `use{Feature}.ts` pattern, components organized by feature folder
- `frontend/src/lib/utils.ts` and `frontend/src/lib/theme.ts` are established shared module locations

### Integration Points
- CI pipeline (`.github/workflows/ci.yml`): add knip step, frontend build, frontend test
- `frontend/tsconfig.json`: enable `noUncheckedIndexedAccess`
- `frontend/package.json`: add knip as dev dependency and script
- All `app/routers/*.py` files: API path review targets

</code_context>

<specifics>
## Specific Ideas

User provided a detailed tooling evaluation with clear recommendations:
- **Knip** is the right tool for frontend dead export detection (replaces deprecated ts-prune, ~10.6k stars, plugins for Vite/Vitest/React/Tailwind/TanStack Query)
- **noUncheckedIndexedAccess** catches real bugs where array/object index access lacks bounds checks — TypeScript 5.9's default tsc --init now enables this
- **CI gap** is the highest-impact fix: frontend type errors and test failures currently can't be caught before merge
- Everything else (Oxlint, Biome, Madge) explicitly evaluated and rejected at current scale (94 files, ~13k lines)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 41-code-quality-dead-code*
*Context gathered: 2026-04-02*
