# Phase 101: Frontend Major Dependency Upgrades - Research

**Researched:** 2026-05-31
**Domain:** Frontend dependency maintenance — 6 coupled upgrade clusters + 1 straggler, React/Vite/TypeScript/ESLint/recharts stack
**Confidence:** HIGH (all version numbers and peer deps verified via `npm view`; breaking-change notes cross-referenced against official docs and GitHub releases)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01 recharts visual UAT:** Human UAT, Claude prepares. Claude gets recharts-3 charts rendering green, then hands the user a concrete checklist plus the exact local URL/routes to eyeball on desktop and a mobile-width viewport. The user gives the verdict before the cluster merges.
- **D-02 Peer-compat blocker policy:** Try overrides/workarounds briefly first, then defer. Research resolves whether `typescript-eslint` supports BOTH TS 6 and ESLint 10 before planning clusters 4/5. Bounded effort only; pin-back if forced.
- **D-03 @types/node pinning:** Pin to Node 24 line. CI runs Node 24 (`node-version: "24"` in `.github/workflows/ci.yml`). Do NOT bump to 25.
- **D-04 shadcn straggler:** Fold in `shadcn` 4.8.3 → 4.9.0 as its own small commit.
- **D-05 react-hooks/set-state-in-effect:** Revisit after eslint-10 bump. If behavior unchanged, leave blanket `off` as-is.
- **D-06 Merge cadence:** Incremental — merge each green cluster to `main` independently. Sequential, not parallel. Full local gate once per cluster merge.

### Claude's Discretion
- Exact plan/file structure (one plan with strictly-ordered per-cluster waves vs one plan per cluster).
- Clusters must be **sequential**, not parallel.

### Deferred Ideas (OUT OF SCOPE)
- Backend dependency bumps (backend is already fully current on all majors).
- The two intentional backend caps (`pydantic-ai-slim<2.0`, `genai-prices<0.1.0`) are not in scope.
</user_constraints>

---

## Summary

This is a dependency-maintenance phase bringing 11 frontend packages up to their latest major versions, organized into 6 ordered clusters (low-risk to high-risk) plus one within-major straggler. The backend is untouched.

**The KEY RISK is now resolved.** The `typescript-eslint` peer dependency question was the single most likely stall: `typescript-eslint@8.60.0` (current) already supports ESLint 10 (`^8.57.0 || ^9.0.0 || ^10.0.0`) AND TypeScript 6.0.x (`>=4.8.4 <6.1.0`). TypeScript 6.0.3 satisfies `<6.1.0`, so a clean bump exists with **no npm overrides needed** for clusters 4 and 5. All 6 clusters can proceed in order as planned.

Secondary risk is recharts 3.x. The existing codebase has 5 multi-axis charts where `CartesianGrid` lacks a `yAxisId` that now must match the named axes — these will silently lose grid lines or warn in recharts 3. The `TooltipProps` → `TooltipContentProps` rename affects shadcn's `chart.tsx` indirectly. The `accessibilityLayer` default flips to `true`. These are concrete, fixable issues.

**Primary recommendation:** Execute all 6 clusters in sequence as designed. No reordering or deferrals needed based on peer-compat. Budget one debugging session for recharts CartesianGrid axis-binding and shadcn chart.tsx type alignment.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Icon library (lucide-react) | Browser / Client | — | Purely client-side SVG component rendering |
| Build tooling (Vite 8) | CDN / Static | Frontend Server (SSR via prerender) | Vite builds the static assets; vite-prerender-plugin does server-side prerendering at build time |
| Test environment (jsdom 29) | — (dev only) | — | Vitest test runner, not part of the production tier |
| Lint tooling (ESLint 10) | — (dev only) | — | Static analysis only |
| Type system (TypeScript 6) | — (dev only) | — | Compile-time only; no runtime impact |
| Chart library (recharts 3) | Browser / Client | — | React components rendered client-side; used in Endgames, Openings, Home pages |

---

## Version Snapshot (verified 2026-05-31 via `npm outdated` + `npm view`)

| Package | Current | Target | Cluster |
|---------|---------|--------|---------|
| `lucide-react` | 0.577.0 | **1.17.0** | 1 |
| `vite` | 7.3.3 | **8.0.14** | 2 |
| `@vitejs/plugin-react` | 5.2.0 | **6.0.2** | 2 |
| `jsdom` | 25.0.1 | **29.1.1** | 3 |
| `@types/node` | 24.12.4 | **24.12.4** (no bump — D-03) | 3 |
| `eslint` | 9.39.4 | **10.4.1** | 4 |
| `@eslint/js` | 9.39.4 | **10.0.1** | 4 |
| `globals` | 16.5.0 | **17.6.0** | 4 |
| `eslint-plugin-react-refresh` | 0.4.26 | **0.5.2** | 4 |
| `typescript` | 5.9.3 | **6.0.3** | 5 |
| `recharts` | 2.15.4 | **3.8.1** | 6 |
| `shadcn` | 4.8.3 | **4.9.0** | straggler (D-04) |

> Note: `@types/node` has no 24.x release beyond 24.12.4 as of this research — the current version is already the latest in the 24.x series. D-03 pin requires no version change, only keeping the `^24.12.4` range constraint. [VERIFIED: npm registry]

---

## Standard Stack

### Packages Being Upgraded (no new dependencies added)

| Library | Target Version | Current | Cluster | Confidence |
|---------|---------------|---------|---------|------------|
| `lucide-react` | 1.17.0 | 0.577.0 | 1 | [VERIFIED: npm registry] |
| `vite` | 8.0.14 | 7.3.3 | 2 | [VERIFIED: npm registry] |
| `@vitejs/plugin-react` | 6.0.2 | 5.2.0 | 2 | [VERIFIED: npm registry] |
| `jsdom` | 29.1.1 | 25.0.1 | 3 | [VERIFIED: npm registry] |
| `eslint` | 10.4.1 | 9.39.4 | 4 | [VERIFIED: npm registry] |
| `@eslint/js` | 10.0.1 | 9.39.4 | 4 | [VERIFIED: npm registry] |
| `globals` | 17.6.0 | 16.5.0 | 4 | [VERIFIED: npm registry] |
| `eslint-plugin-react-refresh` | 0.5.2 | 0.4.26 | 4 | [VERIFIED: npm registry] |
| `typescript` | 6.0.3 | 5.9.3 | 5 | [VERIFIED: npm registry] |
| `recharts` | 3.8.1 | 2.15.4 | 6 | [VERIFIED: npm registry] |
| `shadcn` | 4.9.0 | 4.8.3 | straggler | [VERIFIED: npm registry] |

---

## Package Legitimacy Audit

All packages are well-established projects with multi-year histories on npm. slopcheck was not available (installation blocked by system policy); manual registry verification performed instead.

| Package | Registry | Age | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-------------|-----------|-------------|
| `lucide-react` | npm | 5+ yrs (2020-10-19) | github.com/lucide-icons/lucide | N/A | Approved [ASSUMED: no slopcheck] |
| `vite` | npm | 6+ yrs (2020-04-21) | github.com/vitejs/vite | N/A | Approved [ASSUMED: no slopcheck] |
| `@vitejs/plugin-react` | npm | 5+ yrs | github.com/vitejs/vite (monorepo) | N/A | Approved [ASSUMED: no slopcheck] |
| `jsdom` | npm | 14+ yrs (2011-11-21) | github.com/jsdom/jsdom | N/A | Approved [ASSUMED: no slopcheck] |
| `eslint` | npm | 12+ yrs (2013-07-04) | github.com/eslint/eslint | N/A | Approved [ASSUMED: no slopcheck] |
| `globals` | npm | 10+ yrs | github.com/sindresorhus/globals | N/A | Approved [ASSUMED: no slopcheck] |
| `eslint-plugin-react-refresh` | npm | 3+ yrs | github.com/ArnaudBarre/eslint-plugin-react-refresh | N/A | Approved [ASSUMED: no slopcheck] |
| `typescript` | npm | 13+ yrs (2012-10-01) | github.com/microsoft/TypeScript | N/A | Approved [ASSUMED: no slopcheck] |
| `recharts` | npm | 10+ yrs (2015-08-07) | github.com/recharts/recharts | N/A | Approved [ASSUMED: no slopcheck] |
| `shadcn` | npm | 2+ yrs | github.com/shadcn-ui/ui | N/A | Approved [ASSUMED: no slopcheck] |

**Packages removed due to [SLOP]:** none

**Note:** All packages are industry-standard, widely-used libraries with GitHub repositories and long publish histories. slopcheck unavailability is not a blocking concern for this set.

---

## The Key Risk: typescript-eslint Peer-Compat (D-02 resolution)

**Status: CLEAN — no overrides needed.** [VERIFIED: npm registry]

| Question | Answer |
|----------|--------|
| Current `typescript-eslint` version | 8.60.0 |
| Supported ESLint range | `^8.57.0 \|\| ^9.0.0 \|\| ^10.0.0` |
| ESLint 10 supported? | **YES** — already in the range |
| Supported TypeScript range | `>=4.8.4 <6.1.0` |
| TypeScript 6.0.3 supported? | **YES** — `6.0.3 < 6.1.0` is satisfied |
| Single combo for both TS 6 + ESLint 10? | **YES** — `typescript-eslint@8.60.0` supports both simultaneously |
| npm overrides needed? | **NO** |
| Deferrals needed? | **NO** — clusters 4 and 5 proceed as planned |

**Rationale:** The `typescript-eslint` v8 series added ESLint 10 support progressively from ~8.57.0. TypeScript 6 support landed in 8.58.0 (issue #12123, closed). The current `^8.60.0` already satisfies both ranges. [CITED: typescript-eslint.io/users/dependency-versions/, github.com/typescript-eslint/typescript-eslint/issues/12123]

Supporting plugins:
- `eslint-plugin-react-hooks@7.1.1`: peer dep `^3.0.0 ... ^9.0.0 || ^10.0.0` — ESLint 10 is supported. No version bump needed. [VERIFIED: npm registry]
- `eslint-plugin-react-refresh@0.5.2` (target): peer dep `^9 || ^10` — ESLint 10 is supported. [VERIFIED: npm registry]

---

## Per-Cluster Breaking Changes and Migration Notes

### Cluster 1: lucide-react 0.577.0 → 1.17.0

**Risk level:** LOW — backward-compat aliases kept for all icons used in this project.

**Breaking changes in v1.0:**
- Brand icons removed (GitHub, Twitter, Instagram, etc.). None used in this project. [CITED: lucide.dev/guide/version-1]
- UMD build removed (31.3% size reduction). Project uses ESM via Vite — no impact.
- Icons now have `aria-hidden="true"` by default (accessibility improvement, not a regression).
- New `LucideProvider` context component added (additive).

**Icon renames — backward-compat aliases provided in v1:** All old names are still exported as aliases alongside the new canonical names. This was verified by inspecting the actual `lucide-react@1.17.0` ESM bundle. [VERIFIED: npm registry — direct bundle inspection]

Icons used in this project and their status:

| Old import | Alias status in 1.17.0 | New canonical name |
|------------|------------------------|-------------------|
| `AlertCircle` | Still exported (alias for `CircleAlert`) | `CircleAlert` |
| `AlertTriangle` | Still exported (alias for `TriangleAlert`) | `TriangleAlert` |
| `BarChart2` / `BarChart2Icon` | Still exported (alias for `ChartNoAxesColumn`) | `ChartNoAxesColumn` |
| `BarChart3` / `BarChart3Icon` | Still exported (alias for `ChartColumn`) | `ChartColumn` |
| `CheckCircle2` | Still exported (alias for `CircleCheck`) | `CircleCheck` |
| `ExternalLink` | Still exported | `ExternalLink` (unchanged name) |
| `HelpCircle` | Still exported (alias for `CircleHelp`) | `CircleHelp` |
| `Loader2` | Still exported (alias for `LoaderCircle`) | `LoaderCircle` |
| `Palmtree` | Still exported (alias for `TreePalm`) | `TreePalm` |
| `UserCircle2` | Still exported (alias for `CircleUserRound`) | `CircleUserRound` |
| All others (Swords, Timer, BookMarked, etc.) | Unchanged — no rename | — |

**Migration steps:**
1. `npm install lucide-react@1.17.0` in `package.json`.
2. Run `npm run build` and `npm run lint` — expect zero errors (all aliases intact).
3. Optionally update import names to canonical forms (not required for correctness, but reduces future noise). This is cosmetic — do not spend time on it unless lint warns.

**Verification:** `npm run build` passes. `npm test -- --run` passes.

---

### Cluster 2: Vite 7.3.3 → 8.0.14 + @vitejs/plugin-react 5.2.0 → 6.0.2

**Risk level:** LOW-MEDIUM — Vite 8 replaces Rollup + esbuild with Rolldown + Oxc but maintains a compatibility layer. Plugin hooks are stable.

**Vite 8 breaking changes:** [CITED: vite.dev/guide/migration]

| Change | Impact on this project |
|--------|----------------------|
| Rolldown/Oxc replace esbuild/Rollup | **Low impact** — project uses no raw esbuild or Rollup options (`rollupOptions`, `esbuildOptions` absent from `vite.config.ts`) |
| `build.rollupOptions` → `build.rolldownOptions` | **No impact** — not used |
| `esbuild` config → `oxc` config | **No impact** — not configured |
| Removed plugin hooks: `shouldTransformCachedModule`, `resolveImportMeta`, `renderDynamicImport`, `resolveFileUrl` | **No impact** — `ogImageHashPlugin` and `forceExitAfterBuild` use only `transformIndexHtml` and `closeBundle`, both still supported |
| `output.format: 'system'|'amd'` removed | **No impact** — not used |
| Non-JS load/transform hooks now need `moduleType: 'js'` | **No impact** — custom plugins don't transform non-JS content |
| Browser targets updated (Chrome 107→111 etc.) | **No impact** — project uses `vite.dev/config/` defaults |
| Node.js minimum: `^20.19.0 || >=22.12.0` | **No impact** — CI and local runs Node 24.x |

**@vitejs/plugin-react 6.0.2 peer dep:** `vite: "^8.0.0"` — requires Vite 8. Both must be bumped together. [VERIFIED: npm registry]

**Vite plugin peer compat (must all remain working):**

| Plugin | Current version | Vite 8 peer dep | Status |
|--------|----------------|-----------------|--------|
| `vite-plugin-pwa` | 1.3.0 | `^3.1.0 || ^4.0.0 || ^5.0.0 || ^6.0.0 || ^7.0.0 || ^8.0.0` | Compatible [VERIFIED: npm registry] |
| `vite-prerender-plugin` | 0.5.13 | `5.x || 6.x || 7.x || 8.x` | Compatible [VERIFIED: npm registry] |
| `@tailwindcss/vite` | 4.3.0 | `^5.2.0 || ^6 || ^7 || ^8` | Compatible [VERIFIED: npm registry] |

All three Vite plugins already declare Vite 8 support in their current installed versions. No plugin upgrades needed alongside this cluster.

**Migration steps:**
1. `npm install vite@8.0.14 @vitejs/plugin-react@6.0.2`.
2. Run `npm run build` — the main verification. vite-prerender-plugin runs a full build; if it passes, the plugin compat is confirmed.
3. Run `npm run dev` briefly to verify HMR still works.
4. Run `npm test -- --run` to confirm Vitest (which also uses Vite under the hood) still works.

---

### Cluster 3: jsdom 25.0.1 → 29.1.1 + @types/node (no change)

**Risk level:** LOW — jsdom is a Vitest test dependency; production code is unaffected.

**@types/node note (D-03):** The current `^24.12.4` is already the latest available in the 24.x series as of 2026-05-31. No version change is needed — the constraint stays `^24.12.4`. [VERIFIED: npm registry]

**jsdom 29 Node.js requirement:** `^20.19.0 || ^22.13.0 || >=24.0.0`. Node 24.x is satisfied. [VERIFIED: npm registry]

**jsdom 25 → 29 path covers 4 major versions.** Specific breaking changes affecting test behavior: [CITED: github.com/jsdom/jsdom/releases]
- jsdom 26: `querySelector` behavior changes for some CSS pseudo-selectors (e.g., `input:read-only`). The project does not use this selector in tests.
- jsdom 26–29: CSS improvements (better spec compliance), performance improvements, newer WHATWG spec alignment.
- The project's `// @vitest-environment jsdom` inline directive style is unaffected — Vitest handles the adapter.
- Tests mock `ResizeObserver` (used by recharts) inline — this pattern is stable across jsdom versions.

**Vitest peer dep:** `vitest@4.1.7` lists `jsdom: '*'` — no version constraint. Compatible. [VERIFIED: npm registry]

**Migration steps:**
1. `npm install jsdom@29.1.1`.
2. Run full Vitest suite: `npm test -- --run`. Any test that breaks due to jsdom behavior change will be visible here.
3. Confirm `@types/node` remains at `^24.12.4` (already pinned, no change needed).

---

### Cluster 4: ESLint 9.39.4 → 10.4.1 + @eslint/js 9.39.4 → 10.0.1 + globals 16.5.0 → 17.6.0 + eslint-plugin-react-refresh 0.4.26 → 0.5.2

**Risk level:** MEDIUM — ESLint 10 has meaningful breaking changes but the project's `eslint.config.js` already uses flat config, which is the only format ESLint 10 supports.

**ESLint 10 breaking changes relevant to this project:** [CITED: eslint.org/docs/latest/use/migrate-to-10.0.0]

| Change | Impact |
|--------|--------|
| Old `.eslintrc` format removed | **No impact** — project uses `eslint.config.js` (flat config) already |
| `ESLINT_USE_FLAT_CONFIG` env var removed | **No impact** — not relied upon |
| `FlatESLint`/`LegacyESLint` classes removed | **No impact** — only `ESLint` was used |
| New `eslint:recommended` rules: `no-unassigned-vars`, `no-useless-assignment`, `preserve-caught-error` | **Possible new lint errors** — codebase must be checked |
| `eslint-env` comments now trigger errors | **No impact** — zero `/* eslint-env */` comments found in `src/` |
| Node.js minimum: `^20.19.0 || ^22.13.0 || >=24` | **No impact** — Node 24 on CI and locally |
| `no-shadow-restricted-names`: now reports `globalThis` shadowing | **Low risk** — review if any file shadows `globalThis` |
| JSX references tracked (no false positives in `no-unused-vars`) | **Positive** — may resolve any false positives |
| `context.getCwd()` etc. removed | **No impact** — not a plugin author |

**globals 16 → 17 breaking change:** `audioWorklet` split from the `browser` globals set. Project uses `globals.browser` in `eslint.config.js`. If any code references `AudioWorklet`-specific globals, they now need explicit `globals.audioWorklet` entry. [CITED: github.com/sindresorhus/globals/releases/tag/v17.0.0] [ASSUMED: low impact, audio not used in this project]

**eslint-plugin-react-hooks (stays at 7.1.1):** Already supports ESLint 10 (`^3.0.0 ... ^10.0.0`). No version change needed. [VERIFIED: npm registry]

**D-05 revisit:** The `react-hooks/set-state-in-effect` rule is globally `'off'` in `eslint.config.js` with a comment explaining the rationale (derive-from-server / filter-sync patterns). Check if eslint-plugin-react-hooks 7.1.1 changes the behavior or default of this rule in the context of ESLint 10. If behavior is unchanged (likely), leave the blanket `off` as-is.

**Migration steps:**
1. `npm install eslint@10.4.1 @eslint/js@10.0.1 globals@17.6.0 eslint-plugin-react-refresh@0.5.2`.
2. Run `npm run lint`. Fix any new errors from the expanded `eslint:recommended` rules.
3. Check if `react-hooks/set-state-in-effect` behavior changed (D-05). If rule behavior is identical, no change needed.
4. Run `npm test -- --run` to confirm test files pass lint-adjacent checks.

---

### Cluster 5: typescript 5.9.3 → 6.0.3

**Risk level:** MEDIUM-HIGH — compiler major with 9 changed defaults, but the project's tsconfigs are already explicit on most critical options, limiting surprises.

**TypeScript 6.0 breaking changes:** [CITED: typescriptlang.org/docs/handbook/release-notes/typescript-6-0.html]

| Change | Default | Project impact |
|--------|---------|----------------|
| `strict: true` now default | was `false` | **No impact** — `"strict": true` already explicit in both tsconfigs |
| `types: []` now default (empty) | was all `@types/*` | **No impact** — `tsconfig.app.json` has `"types": ["vite/client"]`; `tsconfig.node.json` has `"types": ["node"]` — both explicit |
| `module` default → `esnext` | was `commonjs` | **No impact** — both tsconfigs have `"module": "ESNext"` explicit |
| `rootDir` default → `.` | was inferred | **Possible impact** — `tsconfig.json` and `tsconfig.app.json` both use `baseUrl: "."` and `include: ["src"]`. With `rootDir` defaulting to `.`, output structure may change; but since `noEmit: true` is set, this is a moot point for both tsconfigs |
| `noUncheckedSideEffectImports: true` now default | was `false` | **No impact** — already explicit in both tsconfigs |
| `baseUrl` deprecated (still works with warning) | — | **Warning expected** — `tsconfig.json` root and `tsconfig.app.json` both use `baseUrl: "."` for `paths` aliases. The `@/*` path mapping uses it. May need to add `"ignoreDeprecations": "6.0"` or migrate to `paths` without `baseUrl` (TS 4.1+ supports this) |
| `moduleResolution: classic` removed | — | **No impact** — project uses `"bundler"` |
| `module: amd/umd/systemjs/none` removed | — | **No impact** — project uses `"ESNext"` |
| `outFile` removed | — | **No impact** — not used |
| `esModuleInterop`/`allowSyntheticDefaultImports` always enabled | — | **No impact** — project already imports with default import syntax |
| `alwaysStrict` always on | — | **No impact** — `strict: true` was already set |

**noUncheckedIndexedAccess interaction:** This project has `noUncheckedIndexedAccess: true` already in `tsconfig.app.json`. TypeScript 6's stricter type narrowing may surface new `T | undefined` errors that were previously accepted. Budget time to fix any narrowing issues.

**Key action item — `baseUrl` deprecation:** Both `tsconfig.json` and `tsconfig.app.json` use `baseUrl: "."` for the `@/*` path alias. TypeScript 6 will warn on this. Options:
1. Add `"ignoreDeprecations": "6.0"` to `tsconfig.json` and `tsconfig.app.json` as a temporary measure.
2. Remove `baseUrl` from root `tsconfig.json` (it's only needed for `paths`; since TS 4.1 paths work without `baseUrl`). Keep `baseUrl: "."` only in `tsconfig.app.json` where it's paired with the `@/*` paths entry, then suppress its specific deprecation.
Option 2 is cleaner but needs Vite's path resolution to remain working. Option 1 buys time (TS 7.0 removes the escape hatch). Either is acceptable.

**Migration steps:**
1. `npm install typescript@6.0.3` (change `~5.9.3` to `~6.0.3` in `package.json`).
2. Run `npm run build` (`tsc -b && vite build`). The `tsc -b` step is the primary gate.
3. Fix any new type errors. Most likely: `T | undefined` narrowing from `noUncheckedIndexedAccess` + stricter TS 6 inference.
4. Address `baseUrl` deprecation warning (options above).
5. Run `npm run lint` to confirm typescript-eslint compat (already verified clean).

---

### Cluster 6: recharts 2.15.4 → 3.8.1

**Risk level:** HIGH — user-facing charts; substantial internal rewrite in v3. Visual UAT required (D-01).

**recharts 3.0 breaking changes:** [CITED: github.com/recharts/recharts/wiki/3.0-migration-guide, github.com/recharts/recharts/releases/tag/v3.0.0]

#### 1. CartesianGrid axis binding (HIGH — affects 4 charts)

In recharts 3, `CartesianGrid` ties to a specific axis via `xAxisId`/`yAxisId`. With multiple named axes, the grid must explicitly name which axis it binds to — otherwise grid lines may not render. Default value is `0` (unnamed/default axis).

**Charts affected (CartesianGrid without `yAxisId`, but have named YAxis):**

| Chart | Has named YAxis | CartesianGrid yAxisId | Fix needed |
|-------|----------------|----------------------|-----------|
| `EndgameEloTimelineSection.tsx` | `yAxisId="elo"` and `yAxisId="bars"` | none | Add `yAxisId="elo"` to CartesianGrid |
| `EndgameScoreOverTimeChart.tsx` | `yAxisId="value"` and `yAxisId="bars"` | none | Add `yAxisId="value"` to CartesianGrid |
| `EndgameClockDiffOverTimeChart.tsx` | `yAxisId="value"` + unnamed right axis | none | Add `yAxisId="value"` to CartesianGrid |
| `ScoreGapByTimePressureChart.tsx` | `yAxisId="value"` + `xAxisId="bleed"` (hidden) | none | Add `yAxisId="value"` to CartesianGrid |
| `ScoreChart.tsx` | single unnamed YAxis | none | No change needed (default axis) |
| `RatingChart.tsx` | single unnamed YAxis | none | No change needed |
| `EndgameClockDiffOverTimeChart.tsx` | see above | none | Add `yAxisId="value"` |

#### 2. `accessibilityLayer` default flipped to `true`

All chart components (`ComposedChart`, `LineChart`) will now have `accessibilityLayer={true}` by default. This adds keyboard controls and ARIA attributes. Impact: keyboard events no longer pass through `onMouseMove`. If any chart handler relies on this, add `accessibilityLayer={false}`. [CITED: recharts migration guide]

Assessment: project charts do not use `onMouseMove` for keyboard interaction. Low practical risk, but adds DOM nodes that may affect selector-based tests.

#### 3. `TooltipProps` renamed to `TooltipContentProps`

The `ChartTooltip` in `src/components/ui/chart.tsx` is defined as `const ChartTooltip = RechartsPrimitive.Tooltip`. The `ChartLegendContent` picks `LegendProps.payload`. These type references may generate TypeScript errors. [CITED: recharts migration guide]

Action: After bumping recharts, run `tsc -b` and fix any type errors in `chart.tsx`.

#### 4. `Legend.payload` prop removed (internal prop)

`ChartLegendContent` in `src/components/ui/chart.tsx` does `Pick<RechartsPrimitive.LegendProps, "payload" | "verticalAlign">`. If `payload` is removed from `LegendProps`, this will be a TypeScript error. Check and update the `chart.tsx` wrapper type.

#### 5. `ResponsiveContainer` — removal of `ref.current.current`

The `ChartContainer` in `chart.tsx` wraps content in `RechartsPrimitive.ResponsiveContainer`. The `ref.current.current` nested access is removed. The project does not appear to use this pattern (no direct ref access on ResponsiveContainer found). No code change needed.

Test mocks use: `vi.mock('recharts', async () => ({ ...actual, ResponsiveContainer: ... }))`. This mock pattern wraps the component inline and is unaffected by internal recharts changes.

#### 6. Z-index ordering (tooltip/legend order in JSX)

recharts 3 uses render order for SVG z-index. `ChartTooltip` should be placed below `ChartLegend` in JSX. Current placement should be checked in each chart.

#### 7. `ErrorBar` null handling changed

`ErrorBar` now ignores nullish values for domain. In `ScoreGapByTimePressureChart.tsx`, `ErrorBar` is used with `dataKey="ciError"` where `ciError` can be `undefined` (suppresses the whisker). This behavior change actually aligns with the project's intent — undefined error bars should simply not render. Verify visually.

#### 8. Removed props not used in this project

- `activeIndex` on Scatter/Bar/Pie — not used
- `alwaysShow` on Reference elements — not used
- `blendStroke` on Pie — not used
- `animateNewValues` — not used
- `Area.points`, `Scatter.points` as public props — not used directly

#### recharts 3 react-redux + immer dependency

recharts 3 introduces `react-redux` and `@reduxjs/toolkit` as production dependencies (for its internal state rewrite). These are added automatically as transitive deps — no action needed, but note the bundle size increase.

**Visual UAT checklist (D-01):**
After all TypeScript/test errors are resolved:
- Desktop viewport (`localhost:5173`):
  - [ ] Endgames page — ELO Timeline chart (3-line + signed band + volume bars)
  - [ ] Endgames page — Score Over Time chart
  - [ ] Endgames page — Clock Diff Over Time chart
  - [ ] Endgames page — Score Gap by Time Pressure chart (zone bands, dots, CI whiskers)
  - [ ] Home page — Rating Chart (line chart)
  - [ ] Openings page — Score Chart (line chart with legend)
  - [ ] All custom tooltips hover correctly
  - [ ] All chart gradients/fills visible
- Mobile viewport (375px width in DevTools):
  - [ ] All above charts — verify Y-axis label visibility rules (isMobile logic)
  - [ ] Mobile-specific layout (no horizontal scroll, no clipping)

**Migration steps:**
1. `npm install recharts@3.8.1`.
2. Run `npm run build` — TypeScript errors will surface immediately.
3. Fix `chart.tsx` type issues (`TooltipContentProps`, `LegendProps.payload`).
4. Add `yAxisId` to `CartesianGrid` in all 4 affected charts.
5. Check JSX ordering (tooltip below legend) in each chart file.
6. Run `npm test -- --run` — all recharts tests use `vi.mock('recharts', ...)` with `vi.importActual`, so they import the real recharts 3 module.
7. **Hand off to user for visual UAT** with the checklist above.

---

### Straggler: shadcn 4.8.3 → 4.9.0 (D-04)

**Risk level:** VERY LOW — within-major, patch-level bump.

**Impact:** Lockfile resolution quirk prevented this from being picked up by the in-major refresh (`260531-jga`). No API changes expected at 4.8 → 4.9.

**Migration steps:**
1. `npm install shadcn@4.9.0`.
2. Run `npm run build` and `npm run lint` to confirm nothing changed.

This can be its own commit either before cluster 1 or after cluster 6 — timing is flexible since it carries zero risk.

---

## Architecture Patterns

### Project Structure (unchanged)

```
frontend/
├── src/
│   ├── components/
│   │   ├── charts/          # recharts consumers (cluster 6 work)
│   │   └── ui/
│   │       └── chart.tsx    # shadcn recharts wrapper (cluster 6 work)
│   └── ...
├── tsconfig.json            # root (cluster 5 — baseUrl deprecation)
├── tsconfig.app.json        # app (cluster 5 — baseUrl deprecation + noUncheckedIndexedAccess)
├── tsconfig.node.json       # node (cluster 5 — unaffected)
├── vite.config.ts           # cluster 2
├── eslint.config.js         # cluster 4
└── package.json             # all clusters
```

### Sequencing Pattern

Each cluster follows the same mechanical sequence:
1. Bump version(s) in `package.json`
2. `npm install` to update `package-lock.json`
3. Fix compile errors (`tsc -b`)
4. Fix lint errors (`npm run lint`)
5. Fix test errors (`npm test -- --run`)
6. Fix build errors (`npm run build`)
7. Run `npm run knip` (no new unused exports introduced)
8. Full local gate: `( cd frontend && npm run lint && npm test -- --run && npm run build && npm run knip )` + backend gate
9. Squash-merge to `main`

Cluster 6 adds: visual UAT handoff before step 9.

### Anti-Patterns to Avoid

- **Don't run clusters in parallel** — bisectability requires one cluster per merge. GSD's parallel-within-wave default is wrong here.
- **Don't skip the backend gate** — even though backend code doesn't change, `uv run ruff format/check` + `ty check` + `pytest -n auto -x` must pass before each merge (per CLAUDE.md full local gate definition).
- **Don't chase cosmetic icon renames** — lucide-react's old names are valid aliases; do not bulk-rename imports unless a specific name stops compiling.
- **Don't use `ignoreDeprecations: "6.0"` as permanent** — if used for `baseUrl`, add a TODO comment noting it must be removed before TypeScript 7.0.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Icon rename discovery | Manual grep + rename | Lucide codemod (optional — aliases make it unnecessary) |
| Peer dep conflict resolution | npm overrides on typescript-eslint | None needed — clean compat verified |
| recharts type shim for removed types | Custom `declare module` patches | Update `chart.tsx` to use recharts 3 types directly |

---

## Common Pitfalls

### Pitfall 1: CartesianGrid silent grid line loss (recharts 3)
**What goes wrong:** After bumping recharts, all multi-axis charts lose their horizontal grid lines silently — the chart renders but looks wrong. Tests still pass because they don't assert on grid line presence.
**Why it happens:** recharts 3's `CartesianGrid` requires explicit `yAxisId` when the chart has named axes. Without it, the grid binds to the default axis (id=0), which doesn't exist when all axes are named.
**How to avoid:** Add `yAxisId="<primary-axis-id>"` to every `CartesianGrid` in: `EndgameEloTimelineSection` (`"elo"`), `EndgameScoreOverTimeChart` (`"value"`), `EndgameClockDiffOverTimeChart` (`"value"`), `ScoreGapByTimePressureChart` (`"value"`).
**Warning signs:** Chart renders but grid lines are absent or in wrong position.

### Pitfall 2: `chart.tsx` type errors after recharts 3 bump
**What goes wrong:** `tsc -b` fails on `src/components/ui/chart.tsx` with errors on `LegendProps.payload` and/or `TooltipProps`.
**Why it happens:** recharts 3 renamed `TooltipProps` to `TooltipContentProps` and removed `payload` from `LegendProps` (it was an internal prop not meant for public use).
**How to avoid:** After bumping recharts, immediately run `tsc -b` and address `chart.tsx` errors before touching any other file. The fix is to update the type references to recharts 3 exports.

### Pitfall 3: `baseUrl` deprecation in TypeScript 6
**What goes wrong:** `tsc -b` outputs warnings or errors about `baseUrl` being deprecated.
**Why it happens:** TypeScript 6 deprecated `baseUrl` when used as a root for module lookups (vs pairing with `paths`). Both `tsconfig.json` and `tsconfig.app.json` have `baseUrl: "."`.
**How to avoid:** Either add `"ignoreDeprecations": "6.0"` (temporary) or migrate `paths` to not require `baseUrl` (TS 4.1+). Either is acceptable for this phase.

### Pitfall 4: ESLint 10 new `eslint:recommended` rules cause failures
**What goes wrong:** `npm run lint` fails after the ESLint 10 bump with errors on `no-unassigned-vars`, `no-useless-assignment`, or `preserve-caught-error`.
**Why it happens:** These three rules are newly enabled in `eslint:recommended` in ESLint 10.
**How to avoid:** After bumping, run `npm run lint` immediately and address any new errors. They are real code quality issues — fix the underlying code rather than disabling the rules.

### Pitfall 5: Vite 8 build succeeds locally but vite-prerender-plugin fails
**What goes wrong:** `npm run build` succeeds on the main bundle but fails or hangs during prerendering.
**Why it happens:** `vite-prerender-plugin` dynamically imports the prerender module graph at build time. The `forceExitAfterBuild` plugin in `vite.config.ts` exists specifically to handle Node process hang — verify this still works with Vite 8/Rolldown.
**How to avoid:** Always run full `npm run build` (not just `tsc -b`) as the verification step for cluster 2. The prerender plugin will exercise the Vite 8 plugin lifecycle completely.

---

## Code Examples

### CartesianGrid fix pattern (recharts 3)

```tsx
// Source: github.com/recharts/recharts/wiki/3.0-migration-guide
// BEFORE (recharts 2 — CartesianGrid silently used default axis)
<CartesianGrid vertical={false} />
<YAxis yAxisId="value" ... />
<YAxis yAxisId="bars" orientation="right" hide ... />

// AFTER (recharts 3 — must name the axis CartesianGrid binds to)
<CartesianGrid vertical={false} yAxisId="value" />
<YAxis yAxisId="value" ... />
<YAxis yAxisId="bars" orientation="right" hide ... />
```

### TypeScript 6 baseUrl deprecation workaround

```json
// Source: typescriptlang.org/docs/handbook/release-notes/typescript-6-0.html
// In tsconfig.json and tsconfig.app.json — temporary suppression
{
  "compilerOptions": {
    "baseUrl": ".",
    "ignoreDeprecations": "6.0",  // TODO: remove before TS 7.0, migrate paths away from baseUrl
    "paths": { "@/*": ["./src/*"] }
  }
}
```

### recharts 3 TooltipContentProps (if chart.tsx needs updating)

```tsx
// Source: github.com/recharts/recharts/wiki/3.0-migration-guide
// recharts 2
import type { TooltipProps } from 'recharts';
// recharts 3
import type { TooltipContentProps } from 'recharts';
```

---

## Runtime State Inventory

Not applicable. This is a tooling/dependency maintenance phase — no stored data, live service config, OS-registered state, secrets, or build artifacts are affected by dependency version bumps.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | npm install, vite build | Yes | v24.14.0 | — |
| npm | package management | Yes | (bundled with Node) | — |
| Docker + PostgreSQL 18 | Backend test gate | Yes (docker compose) | — | Required for full gate |

Node 24.14.0 satisfies all cluster requirements:
- Vite 8: `^20.19.0 || >=22.12.0` — satisfied [VERIFIED: npm registry]
- ESLint 10: `^20.19.0 || ^22.13.0 || >=24` — satisfied [VERIFIED: npm registry]
- jsdom 29: `^20.19.0 || ^22.13.0 || >=24.0.0` — satisfied [VERIFIED: npm registry]

**Missing dependencies with no fallback:** None — all required tools are available.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.7 + @testing-library/react 16.3.2 |
| Config | Inline `// @vitest-environment jsdom` comments per test file |
| Quick run command | `npm test -- --run` (from `frontend/`) |
| Full suite command | `npm test -- --run` (same — no slow suite separation for frontend) |
| Lint | `npm run lint` |
| Build | `npm run build` (`tsc -b && vite build`) |
| Dead code | `npm run knip` |

### Per-Cluster Verification Strategy

This phase's validation is the existing full local gate per cluster, not new test infrastructure. The full gate (CLAUDE.md definition):

```bash
# Backend (untouched, but run per CLAUDE.md full gate policy)
uv run ruff format app/ tests/
uv run ruff check app/ tests/ --fix
uv run ty check app/ tests/
uv run pytest -n auto -x

# Frontend
( cd frontend && npm run lint && npm test -- --run && npm run build && npm run knip )
```

### Phase Requirements → Verification Map

| Cluster | Behavior Verified | Method | Automated |
|---------|------------------|--------|-----------|
| 1 (lucide-react) | Icons render correctly, no missing exports | `npm run build` (TypeScript) + `npm run lint` | Yes |
| 2 (Vite 8) | Build succeeds including prerender step | `npm run build` (full, includes vite-prerender-plugin) | Yes |
| 3 (jsdom 29) | All Vitest tests pass under jsdom 29 | `npm test -- --run` | Yes |
| 4 (ESLint 10) | No lint errors under ESLint 10 rules | `npm run lint` | Yes |
| 5 (TypeScript 6) | Zero type errors under TS 6 | `tsc -b` (embedded in `npm run build`) | Yes |
| 6 (recharts 3) | Charts render correctly, no visual regressions | `npm test -- --run` + **human visual UAT** | Partial |
| straggler (shadcn) | No errors from within-major bump | `npm run build` + `npm run lint` | Yes |

### Cluster 6 Visual UAT Gate (D-01)

recharts is user-facing. After automated tests pass, Claude prepares and human approves:

**Automated gate first:** `npm test -- --run` (recharts tests use `vi.mock` + `vi.importActual` — they run against real recharts 3).

**Then human visual UAT:** Claude provides exact routes and viewport sizes. User checks:
- Desktop: `http://localhost:5173/endgames` — ELO Timeline, Score Over Time, Clock Diff, Score Gap by Time Pressure
- Desktop: `http://localhost:5173/openings` — Score Chart (bookmarks tab)
- Desktop: `http://localhost:5173/` — Rating Chart (if visible on home page)
- Mobile (375px viewport in DevTools): same routes — verify Y-axis label hide logic, no clipping

**Cluster 6 does not merge to `main` until human UAT is approved** (D-01).

### Wave 0 Gaps
None — the existing test infrastructure fully covers this phase. No new test files are needed for a dependency-maintenance phase.

---

## Security Domain

No ASVS categories apply. This is a dependency-maintenance phase — no new authentication, session management, access control, input validation, or cryptography surfaces are added or changed. The npm vulnerability scan (`npm audit --audit-level=high --omit=dev`) remains part of CI and will catch any CVEs introduced by the new dep versions.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rollup + esbuild (Vite 7) | Rolldown + Oxc (Vite 8) | Vite 8.0, March 2026 | Faster builds; plugin API stable; old `rollupOptions` deprecated (not breaking for this project) |
| recharts internal state via `CategoricalChartState` | Redux-toolkit internal store, hooks-based access | recharts 3.0, 2024 | Breaking for `Customized` component users (not used here); stable for standard chart components |
| lucide-react v0 mixed naming (AlertCircle, XCircle, etc.) | v1 normalized naming (CircleAlert, CircleX) with v0 aliases | lucide-react 1.0, 2026 | Old names still exported; migration optional |
| TypeScript JS-based compiler | TypeScript 6 is last JS build; TS 7 will be Go-based | TS 6.0.3, March 2026 | No immediate impact; TS 7 will dramatically speed up type checking |
| ESLint `.eslintrc` (legacy) | Flat config `eslint.config.js` | ESLint 9+, finalized in ESLint 10 | Project already on flat config — no migration needed |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `globals` 16→17 breaking change (audioWorklet split) has no practical impact because the project uses no AudioWorklet globals | Cluster 4 | Low — worst case, need to add `globals.audioWorklet` to eslint config if a lint rule references it |
| A2 | `recharts 3 react-redux` transitive dep does not conflict with `@tanstack/react-query` (both are state managers but for different domains) | Cluster 6 | Very low — these are standard libraries with no known conflicts |
| A3 | `react-hooks/set-state-in-effect` rule behavior is unchanged in eslint-plugin-react-hooks 7.1.1 under ESLint 10 | Cluster 4 / D-05 | Low — if behavior changes, the blanket `'off'` may need per-line adjustments |

---

## Open Questions

1. **recharts `LegendProps.payload` in `chart.tsx`**
   - What we know: recharts 3 removed `payload` from the public `LegendProps` type.
   - What's unclear: Whether `ChartLegendContent`'s `Pick<RechartsPrimitive.LegendProps, "payload" | "verticalAlign">` will produce a TypeScript error or just narrow to `never`.
   - Recommendation: Run `tsc -b` immediately after bumping recharts 3 and fix whatever errors appear. Do not guess — let the compiler report.

2. **Vite 8 / vite-prerender-plugin interaction with Rolldown**
   - What we know: `vite-prerender-plugin@0.5.13` declares Vite 8 compat. The `forceExitAfterBuild` custom plugin exists to work around a process hang.
   - What's unclear: Whether the Rolldown-based build path triggers the same hang or a different one.
   - Recommendation: Run `npm run build` (full) as cluster 2 verification and observe if the process exits cleanly. If it hangs longer than before, adjust the `setTimeout` value in `forceExitAfterBuild`.

---

## Sources

### Primary (HIGH confidence)
- npm registry (`npm view`, `npm outdated`) — all version numbers and peer dependency ranges verified directly
- `lucide-react@1.17.0` ESM bundle (`/tmp/package/dist/esm/lucide-react.mjs`) — direct inspection for alias exports
- [vite.dev/guide/migration](https://vite.dev/guide/migration) — Vite 7→8 breaking changes
- [eslint.org/docs/latest/use/migrate-to-10.0.0](https://eslint.org/docs/latest/use/migrate-to-10.0.0) — ESLint 9→10 breaking changes
- [typescriptlang.org/docs/handbook/release-notes/typescript-6-0.html](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-6-0.html) — TypeScript 6.0 changes
- [recharts/recharts Wiki: 3.0 migration guide](https://github.com/recharts/recharts/wiki/3.0-migration-guide) — recharts 2→3 breaking changes

### Secondary (MEDIUM confidence)
- [typescript-eslint.io/users/dependency-versions/](https://typescript-eslint.io/users/dependency-versions/) — peer dep policy
- [typescript-eslint/typescript-eslint #12123](https://github.com/typescript-eslint/typescript-eslint/issues/12123) — TS 6 support tracking (closed)
- [lucide.dev/guide/version-1](https://lucide.dev/guide/version-1) — v1 scope and changes
- [github.com/sindresorhus/globals releases](https://github.com/sindresorhus/globals/releases/tag/v17.0.0) — globals 17.0 audioWorklet split

### Tertiary (LOW confidence)
- Web search results for per-cluster breaking changes — cross-referenced against official sources

---

## Metadata

**Confidence breakdown:**
- Peer-compat resolution (D-02): HIGH — verified via `npm view` peer deps directly
- Standard stack / target versions: HIGH — verified via `npm outdated` and `npm view`
- lucide-react backward compat: HIGH — verified by direct bundle inspection
- Vite 8 plugin compat: HIGH — all three Vite plugins declare `^8.0.0` peer dep already installed
- recharts 3 breaking changes: MEDIUM-HIGH — wiki and release notes consulted; CartesianGrid and chart.tsx issues clearly identified; some edge cases require runtime discovery
- TypeScript 6 impact: MEDIUM-HIGH — official docs consulted; `baseUrl` deprecation is clear; new type errors require runtime discovery
- ESLint 10 impact: HIGH — migration guide consulted; project already on flat config

**Research date:** 2026-05-31
**Valid until:** 2026-06-30 (npm versions drift; re-check `npm outdated` at execution time per CLAUDE.md § Claude's Discretion)
