# Phase 101: Frontend Major Dependency Upgrades - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Bring the 11 majors-behind frontend deps up to latest, **one coupled cluster at a time**, ordered low-risk → high-risk so the gate signal sharpens as work proceeds. Backend needs nothing (every backend dep is already on its latest major). The clusters and ordering are fixed by ROADMAP.md / SEED-032:

1. **lucide-react** 0.577 → 1.x (prod) — icon lib, low-risk confidence-builder
2. **Vite stack** — `vite` 7 → 8 + `@vitejs/plugin-react` 5 → 6 (dev, coupled); verify `npm run build`, `vite-plugin-pwa`, `vite-prerender-plugin`
3. **Test env** — `jsdom` 25 → 29 + `@types/node` (dev); verify full Vitest suite
4. **Lint stack** — `eslint` 9 → 10 + `@eslint/js` + `globals` 16 → 17 + `eslint-plugin-react-refresh` 0.4 → 0.5 (dev, coupled)
5. **typescript** 5.9 → 6.x (dev) — compiler major; re-run `tsc -b` + `ty`, fix new type errors
6. **recharts** 2.15 → 3.x (prod) — biggest functional risk, user-facing; earns visual UAT

Scope is HOW to sequence/gate/UAT these bumps. Adding new frontend capabilities is out of scope — this is tooling maintenance.

</domain>

<decisions>
## Implementation Decisions

### recharts 3 visual UAT (criterion 4)
- **D-01:** **Human UAT, Claude prepares.** Claude gets the recharts-3 charts rendering green, then hands the user a concrete checklist plus the exact local URL/routes to eyeball on desktop and a mobile-width viewport. The user gives the verdict before the cluster merges. recharts is user-facing, so a human eyeball is the gate, not Claude judging its own screenshots. The checklist must cover: MiniBulletChart, WDLChartRow, ScoreChart, ScoreGapByTimePressureChart, the gauges, and custom tooltips/gradients.

### Peer-compat blocker policy (criterion 5)
- **D-02:** **Try overrides/workarounds briefly first, then defer.** The up-front research pass resolves whether `typescript-eslint` (+ `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`) supports BOTH TS 6 and eslint 10. If a clean bump isn't available for cluster 4 (lint) or 5 (TS 6), spend a **bounded** effort to land it — `pnpm`/`npm` `overrides` on peer ranges, a known-good intermediate version combo, a quick wait-check on a just-released compatible version. Only if that bounded effort fails do we defer the cluster and record the blocker + the version that would unblock. This is a deliberate, slightly-more-aggressive reading of the roadmap's "rather than forced": try the safe workarounds, but do not ship a fragile/over-pinned lockfile to force it.
- Pin-back escape hatch (criterion 1) still applies: any single package that can't be made green is pinned back with a documented reason (same hatch as quick task 260531-jga).

### @types/node pinning (cluster 3)
- **D-03:** **Pin `@types/node` to the Node 24 line, do NOT bump to 25.** CI runs Node 24 (`.github/workflows/ci.yml` `node-version: "24"`). `@types/node`'s major tracks the Node.js runtime line, so it stays on 24.x (currently `^24.12.4`) until CI's Node line moves. The seed's "24 → 25" note is superseded by this — record the held bump rather than taking it.

### Stragglers folded into this phase
- **D-04:** **Fold in shadcn 4.8.3 → 4.9.0** (within-major, trivial) as its own small commit. Gets the lockfile fully current; the in-major refresh missed it due to a lockfile-resolution quirk.
- **D-05:** **Revisit the globally-disabled `react-hooks/set-state-in-effect` rule** after the eslint-10 bump (cluster 4). The rule is currently `'off'` in `frontend/eslint.config.js` (intentional, for derive-from-server / filter-sync patterns). If the eslint-10 / react-hooks bump changes the rule's behavior or default, re-evaluate whether to keep the blanket `off` or move to targeted per-line disables. If behavior is unchanged, leave the blanket `off` as-is — do not churn it gratuitously.

### Merge-to-main cadence
- **D-06:** **Incremental — merge each green cluster to `main` independently.** Each cluster is its own branch → full local gate → squash-merge to `main`, then the next cluster branches off the updated `main`. This extends bisectability to `main` history and prevents a later high-risk cluster (recharts) from stranding earlier green work. Trade-off accepted: the full local gate (backend `ruff`/`ty`/`pytest` + frontend `lint`/`test`/`build`/`knip`) runs once **per cluster merge** (~6 runs), per CLAUDE.md's "full gate at every integration into main" rule. Each cluster is still one atomic commit (criterion 2), so a failure bisects to exactly one cluster.

### Claude's Discretion
- Exact plan/file structure (one plan with strictly-ordered per-cluster waves vs one plan per cluster) is a planner concern — keep clusters **sequential**, not parallel (dep bumps must not run in the same parallel wave; bisectability requires one cluster at a time).
- Whether to run `npm outdated` at planning time to refresh the exact target versions (snapshot in SEED-032 is from 2026-05-31 and will drift) — yes, re-check at planning/execution.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase definition & source
- `.planning/ROADMAP.md` § "Phase 101: Frontend Major Dependency Upgrades" — goal, the 6 clusters, low→high ordering, 5 success criteria
- `.planning/seeds/SEED-032-frontend-major-dependency-upgrades.md` — full cluster/version snapshot, ordering rationale, the peer-compat risk, per-cluster definition of done, "backend has nothing" note

### Process / gates (project rules)
- `CLAUDE.md` § "Pre-PR checklist (MANDATORY before git push)" and § "Version Control" — the full local gate definition and the local-squash-merge-to-`main` flow (D-06 depends on this)
- `CLAUDE.md` § "Frontend" — `noUncheckedIndexedAccess` is on (relevant to TS 6 cluster 5), knip-in-CI, minimum font size, theme constants — constraints any bump must keep green

### Files touched
- `frontend/package.json` — the dependency manifest being bumped
- `frontend/eslint.config.js` — lint config; line ~27 disables `react-hooks/set-state-in-effect` (D-05 revisit target)
- `.github/workflows/ci.yml` — `node-version: "24"` (D-03 pins `@types/node` to this line)

### Precedent
- Quick task `260531-jga` — the in-major refresh that preceded this; established the pin-back escape hatch and disabled the react-hooks rule

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The escape-hatch pattern from quick task 260531-jga (pin a package back with a documented reason) is the precedent for criterion 1 — reuse it verbatim when a package can't go green.

### Established Patterns
- **Full local gate before each merge to `main`** (CLAUDE.md): `ruff format/check` + `ty` + `pytest -x` (backend) and `( cd frontend && npm run lint && npm test -- --run && npm run build && npm run knip )` (frontend). recharts cluster adds visual UAT on top.
- **Sequential, not parallel** for dep bumps — GSD's parallel-within-wave default is wrong here; one cluster at a time for bisectability.
- `noUncheckedIndexedAccess` enabled — TS 6's stricter inference (cluster 5) may surface new `T | undefined` errors to fix; expect and budget for them.

### Integration Points
- recharts charts: `MiniBulletChart`, `WDLChartRow`, `ScoreChart`, `ScoreGapByTimePressureChart`, gauge components, custom tooltips/gradients — the visual-UAT surface for cluster 6.
- Vite plugins that must keep working after the Vite 8 bump: `vite-plugin-pwa`, `vite-prerender-plugin`, `@vitejs/plugin-react`, `@tailwindcss/vite`.

</code_context>

<specifics>
## Specific Ideas

- The single most likely thing to stall this work is `typescript-eslint` lagging on TS 6 / eslint 10 support (SEED-032 "Key risk"). The research pass MUST resolve this before clusters 4 and 5 are planned/landed. If it forces a reorder or defer, that's expected and acceptable (D-02).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. Backend dependency bumps are explicitly out of scope (SEED-032: backend is already fully current; the two intentional caps `pydantic-ai-slim<2.0` / `genai-prices<0.1.0` are not yet binding).

</deferred>

---

*Phase: 101-Frontend Major Dependency Upgrades*
*Context gathered: 2026-05-31*
